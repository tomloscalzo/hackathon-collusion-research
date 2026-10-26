"""Tests for the Modal executor of run_grid.py (C8.3). Run: python -X utf8 -m unittest tools/trial/test_modal_executor.py

Nothing here calls Modal or the network: the remote function is replaced by a fake that runs remote_trial.remote_run in a
local temporary directory with a stub game command.
"""
import io
import json
import os
import sys
import tarfile
import tempfile
import threading
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modal_executor  # noqa: E402
import remote_trial  # noqa: E402
import run_grid  # noqa: E402

SECRET = "s3cr3t-key-value-123"
STUB = (
    "import os, sys, pathlib\n"
    "d = pathlib.Path(sys.argv[1]); tid = sys.argv[2]; keyvar = sys.argv[3]\n"
    "marker = d / 'attempts.txt'\n"
    "n = int(marker.read_text()) + 1 if marker.exists() else 1\n"
    "marker.write_text(str(n))\n"
    "print('key visible:', os.environ.get(keyvar) == %r, 'raw name hidden:', 'VLLM_API_KEY' not in os.environ)\n"
    "print('LEAK', os.environ.get(keyvar))\n"
    "if 'failonce' in tid and n == 1: sys.exit(3)\n"
    "if 'failalways' in tid: sys.exit(4)\n"
    "(d / 'events.jsonl').write_text('{\"kind\": \"quote\"}\\n')\n" % SECRET)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "stub.py").write_text(STUB, encoding="utf-8")
        self.template = [sys.executable, str(self.root / "stub.py"), "{trial_dir}", "{trial_id}", "COLLUSION_VLLM_KEY", "--api-key-env", "COLLUSION_VLLM_KEY"]
        self.payloads = []
        self.lock = threading.Lock()
        old = os.environ.get("VLLM_API_KEY")
        os.environ["VLLM_API_KEY"] = SECRET
        self.addCleanup(lambda: os.environ.pop("VLLM_API_KEY", None) if old is None else os.environ.__setitem__("VLLM_API_KEY", old))

    def fake_invoke(self, payload):
        with self.lock:
            self.payloads.append(payload)
            n = len(self.payloads)
        return remote_trial.remote_run(payload, workdir=self.root / ("remote%d" % n))

    def executor(self, **kw):
        return modal_executor.ModalExecutor(self.template, invoke=self.fake_invoke, **kw)

    def row(self, name="1"):
        return {"trial_id": "a__p1__w0__s%s__t0" % name, "arm": "a", "wave": "1"}


class RemoteRunTest(Fixture):
    def test_runs_command_returns_files_and_hides_the_key(self):
        payload = {"argv": [sys.executable, str(self.root / "stub.py"), remote_trial.TRIAL_DIR_TOKEN, "ok", "COLLUSION_VLLM_KEY"],
                   "key_env": "COLLUSION_VLLM_KEY", "files_tar": b"", "timeout": 60}
        res = remote_trial.remote_run(payload, workdir=self.root / "w")
        self.assertEqual(0, res["returncode"])
        self.assertIn("key visible: True raw name hidden: True", res["log"])      # exposed only under the jar's variable name
        self.assertNotIn(SECRET, res["log"])
        self.assertIn("LEAK ***", res["log"])                                      # a printed copy is redacted
        self.assertNotIn(SECRET.encode(), json.dumps(payload, default=str).encode())
        out = self.root / "back"
        remote_trial.unpack(res["tar"], out)
        self.assertEqual('{"kind": "quote"}\n', (out / "events.jsonl").read_text())

    def test_earlier_files_are_restored_and_failure_returns_partial_files(self):
        src = self.root / "src"
        (src / "sub").mkdir(parents=True)
        (src / "sub" / "cache.jsonl").write_text("kept")
        payload = {"argv": [sys.executable, str(self.root / "stub.py"), remote_trial.TRIAL_DIR_TOKEN, "failalways", "K"],
                   "key_env": "K", "files_tar": remote_trial.pack_dir(src), "timeout": None}
        res = remote_trial.remote_run(payload, workdir=self.root / "w2")
        self.assertEqual(4, res["returncode"])
        out = self.root / "back2"
        remote_trial.unpack(res["tar"], out)
        self.assertEqual("kept", (out / "sub" / "cache.jsonl").read_text())
        self.assertTrue((out / "attempts.txt").exists())

    def test_timeout_and_missing_program(self):
        slow = {"argv": [sys.executable, "-c", "import time; time.sleep(30)"], "key_env": "", "files_tar": b"", "timeout": 1}
        res = remote_trial.remote_run(slow, workdir=self.root / "w3")
        self.assertEqual(-1, res["returncode"])
        self.assertIn("timed out", res["log"])
        res = remote_trial.remote_run({"argv": ["/no/such/program"], "key_env": "", "files_tar": b"", "timeout": 5}, workdir=self.root / "w4")
        self.assertEqual(-1, res["returncode"])
        self.assertIn("could not start", res["log"])

    def test_missing_secret_fails_fast_without_running(self):
        os.environ.pop("VLLM_API_KEY")
        ran = self.root / "ran.txt"
        payload = {"argv": [sys.executable, "-c", "open(%r, 'w').write('x')" % str(ran)], "key_env": "K", "files_tar": b"", "timeout": 5}
        res = remote_trial.remote_run(payload, workdir=self.root / "w5")
        self.assertEqual(-1, res["returncode"])
        self.assertIn("VLLM_API_KEY", res["log"])
        self.assertFalse(ran.exists())

    def test_key_is_redacted_in_files_and_across_the_log_cut(self):
        prog = ("import os, pathlib, sys; k = os.environ['K']; pathlib.Path('calls.txt').write_text('header ' + k);"
                "sys.stdout.write('x' * (remote_trial_max - 5) + k + 'tail')")
        prog = prog.replace("remote_trial_max", str(remote_trial.MAX_LOG))
        res = remote_trial.remote_run({"argv": [sys.executable, "-c", prog], "key_env": "K", "files_tar": b"", "timeout": 20},
                                      workdir=self.root / "w6")
        self.assertEqual(0, res["returncode"])
        self.assertNotIn(SECRET[:6], res["log"])                       # not even a fragment at the cut
        remote_trial.unpack(res["tar"], self.root / "back6")
        self.assertEqual("header ***", (self.root / "back6" / "calls.txt").read_text())

    def test_unpack_refuses_unsafe_members(self):
        for name, kind in (("../evil.txt", "file"), ("/abs.txt", "file"), ("link", "symlink")):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                info = tarfile.TarInfo(name)
                if kind == "symlink":
                    info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
                    tar.addfile(info)
                else:
                    info.size = 1
                    tar.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(ValueError, msg=name):
                remote_trial.unpack(buf.getvalue(), self.root / "dest")
        self.assertFalse((self.root / "evil.txt").exists())

    def test_pack_roundtrip_skips_directories_structure_only(self):
        src = self.root / "p"
        (src / "a" / "b").mkdir(parents=True)
        (src / "a" / "b" / "f.txt").write_text("hi")
        (src / "top.txt").write_text("t")
        remote_trial.unpack(remote_trial.pack_dir(src), self.root / "q")
        self.assertEqual("hi", (self.root / "q" / "a" / "b" / "f.txt").read_text())
        self.assertEqual("t", (self.root / "q" / "top.txt").read_text())


class ModalExecutorTest(Fixture):
    def test_command_construction(self):
        ex = modal_executor.ModalExecutor(["java", "-jar", "{jar}", "--scenario", "{scenarios}/{scenario_file}", "--out", "{trial_dir}",
                                           "--api-key-env", "COLLUSION_VLLM_KEY", "--seed", "{seed}"], invoke=self.fake_invoke)
        with self.assertRaises(ValueError):                                          # grid column clashing with a placeholder
            ex.remote_argv(dict(self.row(), scenario_file="x", seed="1", jar="evil"))
        with self.assertRaises(ValueError) as cm:                                    # key variable not wired into the command
            modal_executor.ModalExecutor(["java", "-jar", "{jar}", "--api-key-env", "OTHER"], key_env="COLLUSION_VLLM_KEY").remote_argv(self.row())
        self.assertIn("--api-key-env", str(cm.exception))
        with self.assertRaises(ValueError):
            modal_executor.ModalExecutor(["java"]).remote_argv(self.row())
        argv = ex.remote_argv(dict(self.row(), scenario_file="slice-p3.yaml", seed="4"))
        self.assertEqual(["java", "-jar", "/app/collusion-engine.jar", "--scenario", "/app/scenarios/slice-p3.yaml", "--out",
                          remote_trial.TRIAL_DIR_TOKEN, "--api-key-env", "COLLUSION_VLLM_KEY", "--seed", "4"], argv)
        with self.assertRaises(ValueError):
            ex.check({"trial_id": "x", "arm": "a", "wave": "1"})                   # {scenario_file} is not a grid column here
        with self.assertRaises(ValueError):
            modal_executor.ModalExecutor(["x", "{nope}"], invoke=self.fake_invoke).check(self.row())

    def test_run_copies_the_directory_back_and_logs(self):
        ex = self.executor(key_env="COLLUSION_VLLM_KEY")
        d = self.root / "trials" / "a" / "a__p1__w0__s1__t0"
        d.mkdir(parents=True)
        (d / "cache.jsonl").write_text("previous")
        res = ex.run(self.row(), d, timeout=77)
        self.assertEqual(0, res.returncode)
        p = self.payloads[0]
        self.assertEqual(("COLLUSION_VLLM_KEY", 77), (p["key_env"], p["timeout"]))
        self.assertNotIn(SECRET, json.dumps({k: v for k, v in p.items() if k != "files_tar"}, default=str))
        self.assertEqual('{"kind": "quote"}\n', (d / "events.jsonl").read_text())       # copied back
        self.assertEqual("previous", (d / "cache.jsonl").read_text())                     # sent out and returned
        log = (d / "console.log").read_text()
        self.assertIn("key visible: True", log)
        self.assertNotIn(SECRET, log)

    def test_failure_reason_and_invoke_error(self):
        d = self.root / "t1"
        d.mkdir()
        res = self.executor().run(self.row("failalways"), d)
        self.assertEqual(4, res.returncode)
        self.assertIn("exit code 4", res.reason)

        def boom(payload):
            raise RuntimeError("modal said no")
        res = modal_executor.ModalExecutor(self.template, invoke=boom).run(self.row(), d)
        self.assertEqual(-1, res.returncode)
        self.assertIn("modal said no", res.reason)

    def test_through_run_grid_retry_reuses_files_and_marks_done(self):
        rows = [dict(self.row("failonce")), dict(self.row("2")), dict(self.row("failalways"))]
        out = self.root / "trials"
        res = run_grid.run_grid(rows, out, self.executor(), max_concurrency=2)
        self.assertEqual({"done": 2, "failed": 1}, res["counts"])
        once = out / "a" / rows[0]["trial_id"]
        self.assertTrue((once / "DONE").exists())
        self.assertEqual("2", (once / "attempts.txt").read_text())                       # the retry saw the first attempt's file
        self.assertTrue((out / "a" / rows[1]["trial_id"] / "events.jsonl").exists())
        self.assertIn("exit code 4", (out / "a" / rows[2]["trial_id"] / "FAILED").read_text())

    def test_local_run_does_not_import_modal_executor(self):
        import subprocess
        code = ("import sys, runpy; sys.path.insert(0, %r); import run_grid; "
                "assert 'modal' not in sys.modules and 'modal_executor' not in sys.modules; "
                "rc = run_grid.main(['run_grid.py', '--grid', %r, '--out', %r, '--', sys.executable, '-c', 'pass']); "
                "assert 'modal' not in sys.modules and 'modal_executor' not in sys.modules; sys.exit(rc)"
                % (str(Path(__file__).resolve().parent), str(CliTest.write_grid(self.root)), str(self.root / "o9")))
        p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr)

    def test_make_app_builds_image_function_and_lifecycle_with_a_fake_modal(self):
        calls = {}

        class Image:
            def __init__(s, steps=()): s.steps = steps
            @classmethod
            def debian_slim(cls, python_version=None): calls["py"] = python_version; return cls()
            def apt_install(s, *a): return Image(s.steps + (("apt",) + a,))
            def add_local_file(s, a, b): return Image(s.steps + (("file", a, b),))
            def add_local_dir(s, a, b): return Image(s.steps + (("dir", a, b),))
            def add_local_python_source(s, *a): return Image(s.steps + (("py",) + a,))

        class App:
            def __init__(s, name): calls["app"] = name; s.log = calls.setdefault("lifecycle", [])
            def function(s, **kw):
                calls["fn"] = kw
                def deco(f):
                    f.remote = lambda payload: ("remote", payload)
                    return f
                return deco
            def run(s):
                log = s.log
                class Ctx:
                    def __enter__(c): log.append("enter"); return c
                    def __exit__(c, *e): log.append("exit")
                return Ctx()

        fake = types.ModuleType("modal")
        fake.Image, fake.App = Image, App
        fake.Secret = types.SimpleNamespace(from_name=lambda n: ("secret", n))
        saved = sys.modules.get("modal", "absent")
        sys.modules["modal"] = fake
        try:
            ex = modal_executor.ModalExecutor(self.template, jar=self.root / "e.jar", scenarios=self.root, secret="my-secret", cpu=2.0,
                                              max_containers=7, memory=3000)
            with ex:
                self.assertEqual(("remote", {"a": 1}), ex.invoke({"a": 1}))
            self.assertEqual(["enter", "exit"], calls["lifecycle"])
        finally:
            if saved == "absent":
                del sys.modules["modal"]
            else:
                sys.modules["modal"] = saved
        kw = calls["fn"]
        self.assertEqual(([("secret", "my-secret")], 2.0, 3000, 7, True), (kw["secrets"], kw["cpu"], kw["memory"], kw["max_containers"], kw["serialized"]))
        self.assertEqual(modal_executor.GAME_TIMEOUT + modal_executor.MODAL_MARGIN, kw["timeout"])
        steps = kw["image"].steps
        self.assertEqual(("apt", "openjdk-17-jre-headless"), steps[0])
        self.assertIn(("file", str(self.root / "e.jar"), modal_executor.REMOTE_JAR), steps)
        self.assertIn(("dir", str(self.root), modal_executor.REMOTE_SCENARIOS), steps)
        self.assertEqual(("py", "remote_trial"), steps[-1])
        self.assertEqual("%d.%d" % sys.version_info[:2], calls["py"])

    def test_timeout_above_the_modal_limit_is_refused(self):
        res = self.executor().run(self.row(), self.root, timeout=modal_executor.GAME_TIMEOUT + 1)
        self.assertEqual(-1, res.returncode)
        self.assertEqual([], self.payloads)

    def test_make_app_without_modal_says_so(self):
        saved = sys.modules.get("modal", "absent")
        sys.modules["modal"] = None                      # makes "import modal" raise ImportError
        try:
            with self.assertRaises(RuntimeError) as cm:
                modal_executor.make_app("jar", "scen")
            self.assertIn("pip install modal", str(cm.exception))
        finally:
            if saved == "absent":
                del sys.modules["modal"]
            else:
                sys.modules["modal"] = saved


class CliTest(Fixture):
    @staticmethod
    def write_grid(root):
        import csv
        g = Path(root) / "grid.csv"
        rows = [{"trial_id": "a__p1__w0__s%s__t0" % n, "arm": "a", "wave": "1"} for n in ("1", "2")]
        with open(g, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator=chr(10))
            w.writeheader()
            w.writerows(rows)
        return g

    def grid(self):
        return self.write_grid(self.root)

    def test_scenarios_directory_must_exist_and_options_pass_through(self):
        out = self.root / "o3"
        base = ["run_grid.py", "--grid", str(self.grid()), "--out", str(out), "--executor", "modal", "--jar", str(self.root / "stub.py")]
        self.assertEqual(2, run_grid.main(base + ["--scenarios", str(self.root / "nodir"), "--"] + self.template))
        ns = types.SimpleNamespace(jar=str(self.root / "stub.py"), scenarios=str(self.root), key_env="KE", modal_secret="S", modal_cpu=3.0,
                                   modal_max_containers=9, modal_memory=4096)
        ex = run_grid.make_modal_executor(ns, self.template)
        self.assertEqual(("KE", "S", 3.0, 9, 4096), (ex.key_env, ex.secret, ex.cpu, ex.max_containers, ex.memory))

    def test_executor_modal_needs_a_jar_and_modal(self):
        out = self.root / "o"
        base = ["run_grid.py", "--grid", str(self.grid()), "--out", str(out), "--executor", "modal"]
        self.assertEqual(2, run_grid.main(base + ["--"] + self.template))                 # no --jar
        self.assertEqual(2, run_grid.main(base + ["--jar", str(self.root / "missing.jar"), "--"] + self.template))
        self.assertEqual(2, run_grid.main(["run_grid.py", "--grid", str(self.grid()), "--out", str(out), "--executor", "bogus", "--"] + self.template))
        self.assertFalse(out.exists())

    def test_executor_modal_runs_through_the_factory(self):
        made = {}

        def fake_factory(args, template):
            made["args"] = args
            return modal_executor.ModalExecutor(template, invoke=self.fake_invoke)
        old = run_grid.make_modal_executor
        run_grid.make_modal_executor = fake_factory
        self.addCleanup(setattr, run_grid, "make_modal_executor", old)
        out = self.root / "o2"
        code = run_grid.main(["run_grid.py", "--grid", str(self.grid()), "--out", str(out), "--executor", "modal", "--jar", "x.jar",
                              "--max-concurrency", "2", "--"] + self.template)
        self.assertEqual(0, code)
        self.assertEqual(2, len(list(out.rglob("DONE"))))
        self.assertEqual("x.jar", made["args"].jar)


if __name__ == "__main__":
    unittest.main()
