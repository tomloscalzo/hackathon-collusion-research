"""Integration I3 (scope 14.6): a mock grid through the runner, killed and resumed: identical tables.
Run: python -X utf8 -m unittest tools/trial/test_i3_runner_resume.py      (about 70 s)

A small Track M design (headline-tacit, headline-chat, r0-control, r1-reflection) goes through the real chain:
make_grid.py -> grid.csv -> run_grid.py with the C14.1 trial command (trial_cmd.py) -> the real jar -> mock_openai.py
(served model `collude` or `compete`, picked by the grid's model_profile) -> collect.py. One uninterrupted run is the
reference. A second run is killed hard (the runner's whole process tree) after half the trials are DONE and while the next
game is part-way (its cache holds calls but it has no marker), then resumed with the same command; collect.py must give
byte-identical tables. The killed trial must have replayed its cache on resume.

Needs PyYAML, engine/target/collusion-engine.jar and a JDK (JAVA_HOME or java on PATH); skipped without. No network
beyond 127.0.0.1, no LLM. run_mock_grid() is shared with test_i4_mock_to_figures.py.
"""
import copy
import csv
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import collect  # noqa: E402
import make_grid  # noqa: E402
from mock_openai import MockOpenAI  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None

JAR = REPO / "engine" / "target" / "collusion-engine.jar"
PROFILE = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "timeout_sec": 60, "max_tokens": {"talk": 320, "quote": 400, "question": 400}}
DESIGN = {
    "version": 1,
    "points": {1: "slice-m-p1.yaml", 3: "slice-m-p3.yaml", 5: "slice-m-p5.yaml"},
    "model_profiles": {"mock_collude": {"t0": PROFILE, "t1": PROFILE}, "mock_compete": {"t0": PROFILE, "t1": PROFILE}},
    "introspection_cell": {"point": 3, "communication": "private"},
    "defaults": {"model_profile": "mock_compete", "firms": 2, "seats": ["llm", "llm"], "communication": "tacit",
                 "condition_texts": {"all": "neutral"}, "wordings": [0, 1], "seeds": [1], "thinking": [0], "wave": {"t0": 1, "t1": 2}},
    "arms": [
        {"name": "headline-tacit", "points": [1, 3, 5], "communication": "tacit", "model_profile": "mock_compete"},
        {"name": "headline-chat", "points": [1, 3, 5], "communication": "private", "model_profile": "mock_collude"},
        {"name": "r0-control", "cell_from": "introspection_cell", "seeds": [101], "introspection": "R0",
         "model_profile": "mock_compete", "wave": {"t0": 4, "t1": 4}},
        {"name": "r1-reflection", "cell_from": "introspection_cell", "seeds": [101], "introspection": "R1",
         "options": {"quote_instruction": "r1_reflect", "reply_field": False}, "model_profile": "mock_collude", "wave": {"t0": 4, "t1": 4}},
    ],
}
COLLUDING = {"mock_collude"}          # ground truth: these trials collude in every round (mock_openai.py behaviours)
TABLES = ("trials.csv", "rounds.csv", "messages.csv", "questions.csv", "refusals.csv")


def java_bin():
    home = os.environ.get("JAVA_HOME")
    for c in ([str(Path(home) / "bin" / "java")] if home else []) + [shutil.which("java") or ""]:
        if c and (Path(c).is_file() or Path(c + ".exe").is_file()):
            return c
    return None


def available():
    return yaml is not None and JAR.is_file() and java_bin() is not None


def write_grid(root):
    rows, _ = make_grid.expand(copy.deepcopy(DESIGN), None)
    path = Path(root) / "grid.csv"
    make_grid.write_grid(rows, path)
    return path, rows


def runner_cmd(grid, out, base_url, concurrency):
    """The run_grid.py command line with the C14.1 trial command as the game command (local executor)."""
    tmpl = [sys.executable, "-X", "utf8", "{trial_cmd}", "--trial-dir", "{trial_dir}", "--jar", "{jar}", "--scenarios", "{scenarios}",
            "--java", java_bin(), "--base-url", base_url, "--model", "mock_collude=collude", "--model", "mock_compete=compete",
            "--api-key-env", "COLLUSION_VLLM_KEY", "--code-commit", "0123abcd", "--allow-unwired"]
    return [sys.executable, "-X", "utf8", str(HERE / "run_grid.py"), "--grid", str(grid), "--out", str(out), "--jar", str(JAR),
            "--max-concurrency", str(concurrency), "--"] + tmpl


def truth_rows(rows, root):
    """trial_id,round,collusive for every round each trial played (the mocks' known truth), from rounds.csv."""
    profile = {r["trial_id"]: r["model_profile"] for r in rows}
    with open(Path(root) / "rounds.csv", encoding="utf-8", newline="") as f:
        played = sorted({(r["trial_id"], int(r["round"])) for r in csv.DictReader(f)})
    return [(t, rnd, 1 if profile[t] in COLLUDING else 0) for t, rnd in played]


def run_mock_grid(root, concurrency=4):
    """Make the grid, run it uninterrupted against the mock, collect: returns (grid rows, trials dir, tables dir)."""
    root = Path(root)
    grid, rows = write_grid(root)
    with MockOpenAI() as m:
        p = subprocess.run(runner_cmd(grid, root / "trials", m.base_url, concurrency), capture_output=True, text=True)
    if p.returncode != 0:
        raise AssertionError("run_grid exit %d:\n%s\n%s" % (p.returncode, p.stdout[-3000:], p.stderr[-3000:]))
    collect.collect(str(root / "trials"), str(root / "tables"), include_pilot=True)
    return rows, root / "trials", root / "tables"


def _kill_hard(p, vdir):
    """Kill the runner and its game at once, as a crash or a closed terminal would; returns the kill command's status."""
    if os.name == "nt":                     # the whole process tree: runner, trial_cmd, java
        rc = subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        p.wait(timeout=60)
        return rc
    p.send_signal(signal.SIGKILL)           # POSIX: the games run in their own sessions, so kill the game by its trial dir
    p.wait(timeout=60)
    if vdir is None:
        return 0
    return 0 if subprocess.run(["pkill", "-KILL", "-f", str(vdir)]).returncode in (0, 1) else 1


@unittest.skipUnless(available(), "needs PyYAML, engine/target/collusion-engine.jar and a JDK")
class RunnerKilledAndResumed(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_killed_and_resumed_run_gives_byte_identical_tables(self):
        rows, _, ref_tables = run_mock_grid(self.root / "ref")
        n = len(rows)
        self.assertEqual(16, n)                                  # 2 headline arms x 3 points x 2 wordings + 2 R arms x 2 wordings

        run = self.root / "run"
        grid, _ = write_grid(run)
        out = run / "trials"
        order = sorted(rows, key=lambda r: int(r["wave"]))      # run_grid's order with --max-concurrency 1
        with MockOpenAI(delay=0.1) as m:
            p = subprocess.Popen(runner_cmd(grid, out, m.base_url, 1), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}))
            victim, deadline = None, time.time() + 600
            try:
                while time.time() < deadline and p.poll() is None:
                    done = [r for r in order if (out / r["arm"] / r["trial_id"] / "DONE").exists()]
                    if len(done) >= n // 2:
                        nxt = order[len(done)]
                        cache = out / nxt["arm"] / nxt["trial_id"] / "cache.jsonl"
                        if cache.exists() and cache.stat().st_size > 0 and not (cache.parent / "DONE").exists():
                            victim = nxt
                            break
                    time.sleep(0.02)
            finally:
                vdir = out / victim["arm"] / victim["trial_id"] if victim else None
                kill_rc = _kill_hard(p, vdir)
            self.assertIsNotNone(victim, "the runner finished or stalled before it could be killed mid-game")
            self.assertEqual(0, kill_rc, "the kill command failed")
            time.sleep(1)
            cache_size = (vdir / "cache.jsonl").stat().st_size
            time.sleep(1)
            self.assertEqual(cache_size, (vdir / "cache.jsonl").stat().st_size, "the killed game is still writing")
            self.assertFalse((vdir / "DONE").exists() or (vdir / "FAILED").exists())
            done_before = sum((out / r["arm"] / r["trial_id"] / "DONE").exists() for r in rows)
            self.assertGreaterEqual(done_before, n // 2)
            self.assertLess(done_before, n)
            cached_lines = len((vdir / "cache.jsonl").read_text(encoding="utf-8").splitlines())
            self.assertGreater(cached_lines, 0)
            calls_before = m.calls
            done_dirs = [out / r["arm"] / r["trial_id"] for r in rows if (out / r["arm"] / r["trial_id"] / "DONE").exists()]
            untouched = {d: ((d / "console.log").read_bytes(), (d / "events.jsonl").read_bytes(), (d / "DONE").read_bytes())
                         for d in done_dirs}

            p2 = subprocess.run(runner_cmd(grid, out, m.base_url, 2), capture_output=True, text=True)
            self.assertEqual(0, p2.returncode, p2.stdout[-2000:] + p2.stderr[-2000:])
            self.assertIn("already done %d\n" % done_before, p2.stdout)
            for d, before in untouched.items():                  # a DONE trial is not played again
                self.assertEqual(before, ((d / "console.log").read_bytes(), (d / "events.jsonl").read_bytes(), (d / "DONE").read_bytes()), d)
            resumed = [out / r["arm"] / r["trial_id"] for r in rows if out / r["arm"] / r["trial_id"] not in untouched]
            fresh = sum(1 for d in resumed for l in (d / "events.jsonl").read_text(encoding="utf-8").splitlines()
                        if l.strip() and json.loads(l).get("cache_hit") is False)
            self.assertEqual(fresh, m.calls - calls_before, "server calls on resume = the resumed trials' uncached calls")
        collect.collect(str(out), str(run / "tables"), include_pilot=True)
        for name in TABLES:
            self.assertEqual((ref_tables / name).read_bytes(), (run / "tables" / name).read_bytes(), name)

        events = [json.loads(l) for l in (vdir / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        hits = [e for e in events if e.get("cache_hit")]
        self.assertGreater(len(hits), 0, "the resumed game did not replay its cache")
        self.assertEqual(cached_lines, len(hits), "every call cached before the kill is replayed, no more")
        with open(run / "tables" / "trials.csv", encoding="utf-8", newline="") as f:
            trials = list(csv.DictReader(f))
        self.assertEqual(n, len(trials))
        self.assertEqual({"done"}, {t["status"] for t in trials})
        self.assertTrue(all(int(t["rounds"]) > 0 for t in trials))
        level = {t["trial_id"]: float(t["collusion_level"]) for t in trials}
        for r in rows:                                            # the mocks' behaviour reaches the tables
            self.assertEqual(1.0 if r["model_profile"] in COLLUDING else 0.0, level[r["trial_id"]], r["trial_id"])


if __name__ == "__main__":
    unittest.main()
