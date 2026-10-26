"""Tests for trial_cmd.py, the Track M trial command (C14.1). Run: python -X utf8 -m unittest tools/trial/test_trial_cmd.py

Commands are built from real grid rows of tools/trial/design/trackm_design.yaml and checked against the contract
(CONTRACTS.md "The trial command") and the jar's own usage text. The end-to-end test runs two real rows through run_grid,
trial_cmd and the real jar against mock_openai.py (needs engine/target/collusion-engine.jar and a JDK; skipped without).
No network beyond 127.0.0.1, no LLM.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import make_grid  # noqa: E402
import modal_executor  # noqa: E402
import run_grid  # noqa: E402
import trial_cmd  # noqa: E402
from mock_openai import MockOpenAI  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None

DESIGN = HERE / "design" / "trackm_design.yaml"
JAR = REPO / "engine" / "target" / "collusion-engine.jar"
SCEN = REPO / "engine" / "src" / "main" / "resources" / "scenarios"
MAIN_JAVA = REPO / "engine" / "src" / "main" / "java" / "io" / "github" / "tomloscalzo" / "collusion" / "cli" / "Main.java"
URL14, URL32 = "https://ws--collusion-vllm-qwen3-14b-serve.modal.run", "https://ws--collusion-vllm-qwen3-32b-fp8-serve.modal.run"


def java_bin():
    home = os.environ.get("JAVA_HOME")
    for c in ([str(Path(home) / "bin" / "java")] if home else []) + [shutil.which("java") or ""]:
        if c and (Path(c).is_file() or Path(c + ".exe").is_file()):
            return c
    return None


def real_rows():
    d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    d["introspection_cell"] = {"point": 3, "communication": "private"}   # so the introspection arms expand too
    return {r["trial_id"]: r for r in make_grid.expand(d, DESIGN)[0]}


def args(**kw):
    a = dict(jar="/app/collusion-engine.jar", scenarios=str(SCEN), java="java",
             base_url=["qwen3_14b=" + URL14, "qwen3_32b_fp8=" + URL32, "qwen3_32b_fp8_32k=" + URL32, "gpt_oss_20b=" + URL32],
             model=["qwen3_14b=served14", "qwen3_32b_fp8=served32", "qwen3_32b_fp8_32k=served32", "gpt_oss_20b=servedoss"],
             api_key_env="COLLUSION_VLLM_KEY", code_commit="0123abcd", budget_tokens=5000000, allow_unwired=False)
    a.update(kw)
    return argparse.Namespace(**a)


def usage_flags():
    """The --flags of the jar's usage text (Main.java source), i.e. every flag the jar takes today."""
    return set(re.findall(r"--[a-z][a-z-]*", MAIN_JAVA.read_text(encoding="utf-8")))


def common(row, d, scenario, thinking):
    return ["--trial-dir", d, "--runs", "1", "--scenario", scenario, "--seed", row["seed"], "--paraphrase", row["wording"],
            "--arm", row["arm"], "--trial-id", row["trial_id"], "--penalty-point", row["penalty_point"], "--code-commit", "0123abcd",
            "--thinking", thinking]


@unittest.skipIf(yaml is None, "PyYAML not installed")
class RealRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = real_rows()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.d = str(self.tmp / "t")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tacit_thinking_off_row_gives_the_contract_argv(self):
        row = self.rows["headline-tacit__p1__w0__s91__t0"]
        argv, files, notes = trial_cmd.build(row, args(), self.d)
        d = Path(self.d)
        self.assertEqual(["java", "-jar", "/app/collusion-engine.jar", "run", "--seat", "LLM", "--multi-seat", "on"]
                         + common(row, self.d, str(SCEN) + "/slice-m-p1.yaml", "off")
                         + ["--model", "served32", "--base-url", URL32, "--api-key-env", "COLLUSION_VLLM_KEY", "--budget-tokens", "5000000",
                            "--out", str(d / "run.jsonl"), "--cache", str(d / "cache.jsonl"), "--calls", str(d / "calls.jsonl"),
                            "--temperature", "0.7", "--top-p", "0.8", "--top-k", "20", "--timeout-sec", "120", "--max-tokens", "400",
                            "--follow-redirects", "on", "--reserve-out-tokens", "max", "--context-clamp", "on", "--context-window", "16384"], argv)
        self.assertEqual([], notes)
        self.assertEqual([], list(files))     # slice-m-p1 seats llm1, llm2 as the row says: used as is, nothing written

    def test_chat_thinking_on_row_adds_talk_and_the_thinking_flags(self):
        row = self.rows["smoke-14b-chat__p3__w0__s1__t1"]
        argv, _, notes = trial_cmd.build(row, args(allow_unwired=True), self.d)
        self.assertEqual(["--multi-seat", "on", "--talk", "on", "--trial-dir"], argv[6:11])
        tail = argv[argv.index("--calls") + 2:]
        self.assertEqual(["--temperature", "0.6", "--top-p", "0.95", "--top-k", "20", "--timeout-sec", "300", "--max-tokens", "8192",
                          "--follow-redirects", "on", "--reserve-out-tokens", "max", "--context-clamp", "on", "--context-window", "16384",
                          "--call-timeout-sec", "quote=300,talk=300,question=300"], tail)
        self.assertEqual("on", argv[argv.index("--thinking") + 1])
        self.assertTrue(any("--condition-texts not applied" in n and "private_chat" in n for n in notes), notes)
        unwired = trial_cmd.build(row, args(allow_unwired=True), self.d)[1][str(Path(self.d) / "UNWIRED")]
        self.assertIn("--condition-texts", unwired)
        self.assertNotIn(str(Path(self.d) / "UNWIRED"), trial_cmd.build(self.rows["headline-tacit__p1__w0__s91__t0"], args(), self.d)[1])

    def test_three_firm_scenario_with_its_own_seats_is_used_as_is(self):
        row = self.rows["n3-cheater__p3__w0__s91__t0"]
        argv, files, _ = trial_cmd.build(row, args(allow_unwired=True), self.d)
        self.assertEqual(str(SCEN) + "/n3-cheater.yaml", argv[argv.index("--scenario") + 1])
        self.assertEqual([str(Path(self.d) / "UNWIRED")], list(files))   # no scenario.yaml: the file has its seats
        self.assertEqual(["--talk", "on"], argv[8:10])
        self.assertEqual("400", argv[argv.index("--max-tokens") + 1])   # max(talk 320, quote 400)

    def test_r2s_arm_thinking_off_quote_limit_900_passes_through(self):
        # U23: the saved-only introspection arms carry quote 900 (thinking off); the map and --max-tokens follow the grid row
        ids = [k for k in self.rows if k.startswith(("r2s-confidant", "r3s-public"))]
        self.assertTrue(ids)
        for rid in ids:
            row = self.rows[rid]
            argv, _, _ = trial_cmd.build(row, args(allow_unwired=True), self.d)
            if row["thinking"] == "0":
                self.assertEqual("900", argv[argv.index("--max-tokens") + 1], rid)
                self.assertEqual(900, trial_cmd.call_settings(row)["calls"]["quote"]["max_tokens"], rid)
                self.assertEqual(320, trial_cmd.call_settings(row)["calls"]["talk"]["max_tokens"], rid)
            else:
                self.assertEqual("8192", argv[argv.index("--max-tokens") + 1], rid)

    def test_model_profile_picks_the_server(self):
        row = self.rows["smoke-32b-tacit__p3__w0__s1__t0"]
        argv, _, _ = trial_cmd.build(row, args(), self.d)
        self.assertEqual(("served32", URL32), (argv[argv.index("--model") + 1], argv[argv.index("--base-url") + 1]))
        argv, _, _ = trial_cmd.build(row, args(base_url=["http://127.0.0.1:9"], model=["m"]), self.d)   # unkeyed = every profile
        self.assertEqual(("m", "http://127.0.0.1:9"), (argv[argv.index("--model") + 1], argv[argv.index("--base-url") + 1]))
        with self.assertRaisesRegex(ValueError, "no --base-url for model_profile 'qwen3_32b_fp8'"):
            trial_cmd.build(row, args(base_url=["qwen3_14b=" + URL14]), self.d)
        for bad in (["qwen3_32b_fp8="], [""]):                      # an unset shell variable in the runbook array
            with self.assertRaisesRegex(ValueError, "empty value"):
                trial_cmd.build(row, args(base_url=bad), self.d)

    def test_every_real_row_builds_with_flags_the_jar_takes(self):
        jar = usage_flags()
        self.assertIn("--trial-dir", jar)
        talk_arms = set()
        for tid, row in self.rows.items():
            argv, files, _ = trial_cmd.build(row, args(allow_unwired=True), self.d)
            flags = {a for a in argv if a.startswith("--")}
            self.assertLessEqual(flags, jar, tid)
            self.assertEqual(argv.count("--trial-dir"), 1)
            self.assertEqual(argv[argv.index("--thinking") + 1], {"0": "off", "1": "on"}[row["thinking"]], tid)
            self.assertEqual("--talk" in argv, row["communication"] != "tacit", tid)
            self.assertEqual("--call-timeout-sec" in argv, row["thinking"] == "1", tid)
            self.assertEqual(["on", "max"], [argv[argv.index("--follow-redirects") + 1], argv[argv.index("--reserve-out-tokens") + 1]])
            self.assertEqual(["on", "16384" if row["model_profile"] != "qwen3_32b_fp8_32k" else "32768"], [argv[argv.index("--context-clamp") + 1], argv[argv.index("--context-window") + 1]], tid)  # U2
            self.assertEqual(row["context_window"], argv[argv.index("--context-window") + 1], tid)   # U11: 32768 for the 32k profile
            for opt in ("--out", "--cache", "--calls", "--trial-dir"):
                self.assertTrue(argv[argv.index(opt) + 1].startswith(self.d), (tid, opt))
            self.assertEqual(str(Path(self.d) / "UNWIRED") in files, bool(trial_cmd.needs_wiring(row)), tid)
            self.assertNotIn(str(Path(self.d) / "scenario.yaml"), files, tid)     # the scenario file is used as is
            self.assertEqual(str(SCEN) + "/" + row["scenario_file"], argv[argv.index("--scenario") + 1], tid)
            if row["scenario_file"].startswith("slice-"):
                self.assertTrue(row["scenario_file"].startswith("slice-m-p"), tid)   # no Track M row uses the one-LLM slice files
            if row["thinking"] == "1":                              # above Modal's 150 s redirect: long calls are redirected, not timed out
                self.assertEqual("300", row["timeout_sec"], tid)
                self.assertEqual("quote=300,talk=300,question=300", argv[argv.index("--call-timeout-sec") + 1], tid)
                self.assertEqual("300", argv[argv.index("--timeout-sec") + 1], tid)
            if row["communication"] != "tacit":
                talk_arms.add(row["arm"])
        self.assertIn("headline-chat", talk_arms)

    def test_rows_needing_unwired_texts_or_options_are_refused_without_the_switch(self):
        refused = set()
        for tid, row in self.rows.items():
            need = trial_cmd.needs_wiring(row)
            try:
                trial_cmd.build(row, args(), self.d)
                self.assertEqual([], need, tid)
            except ValueError as e:
                self.assertTrue(need, tid)
                self.assertIn(need[0], str(e))
                refused.add(row["arm"])
        self.assertIn("headline-chat", refused)                     # private_chat is a real text
        self.assertIn("m-comp", refused)                            # options
        self.assertNotIn("headline-tacit", refused)                 # all:neutral is blank
        self.assertEqual(["--condition-texts", "--options"], trial_cmd.needs_wiring(self.rows["m-comp__p3__w0__s91__t0"]))

    def test_neutral_options_cell_reaches_the_engine_unchanged(self):
        row = dict(self.rows["headline-tacit__p3__w0__s91__t0"], options='{"payoff_examples":"neutral"}', payoff_examples="neutral")
        argv, _, _ = trial_cmd.build(row, args(), self.d, frozenset(trial_cmd.PENDING))
        self.assertEqual('{"payoff_examples":"neutral"}', argv[argv.index("--options") + 1])
        self.assertEqual(["--options"], trial_cmd.needs_wiring(row))

    def test_pending_flags_are_passed_once_the_jar_lists_them(self):
        row = self.rows["r2f-confidant__p3__w0__s91__t1"]
        argv, files, notes = trial_cmd.build(row, args(), self.d, frozenset(trial_cmd.PENDING))
        self.assertEqual(row["condition_texts"], argv[argv.index("--condition-texts") + 1])
        self.assertEqual(json.loads(row["options"]), json.loads(argv[argv.index("--options") + 1]))
        path = argv[argv.index("--call-settings") + 1]
        self.assertEqual(str(Path(self.d) / "call_settings.json"), path)
        m = json.loads(files[path])
        self.assertEqual({"thinking": True, "temperature": 0.6, "top_p": 0.95, "top_k": 20,
                          "calls": {"talk": {"max_tokens": 8192, "timeout_sec": 300}, "quote": {"max_tokens": 8192, "timeout_sec": 300},
                                    "question": {"max_tokens": 4096, "timeout_sec": 300}}}, m)
        self.assertEqual([], notes)

    def test_thinking_off_sampling_reaches_argv_and_call_settings(self):
        # U1b: 0.7 / 0.8 / 20 for every thinking-off row, through existing flags (no Java change) and the settings map.
        for tid, row in self.rows.items():
            if row["thinking"] != "0":
                continue
            argv, files, _ = trial_cmd.build(row, args(allow_unwired=True), self.d, frozenset(trial_cmd.PENDING))
            self.assertEqual(("0.7", "0.8", "20"), tuple(argv[argv.index(f) + 1] for f in ("--temperature", "--top-p", "--top-k")), tid)
            m = json.loads(files[argv[argv.index("--call-settings") + 1]])
            self.assertEqual((0.7, 0.8, 20), (m["temperature"], m["top_p"], m["top_k"]), tid)

    def test_bad_rows_and_options_are_errors(self):
        good = self.rows["headline-tacit__p1__w0__s91__t0"]
        for change, msg in (({"thinking": "2"}, "thinking must be 0 or 1"), ({"communication": "loud"}, "communication"),
                            ({"seed": ""}, "lacks seed"), ({"seats": "llm,scripted:grim"}, "seat 2 is LLM in the file but scripted:grim"),
                            ({"seats": "llm,llm,llm"}, "has 3 seats")):
            with self.assertRaisesRegex(ValueError, msg):
                trial_cmd.build(dict(good, **change), args(), self.d)
        for sha in ("", "$(git rev-parse HEAD)", "HEAD", "unknown"):
            with self.assertRaisesRegex(ValueError, "--code-commit"):
                trial_cmd.build(good, args(code_commit=sha), self.d)


class Seats(unittest.TestCase):
    def read(self, name):
        return (SCEN / name).read_text(encoding="utf-8")

    def test_matching_files_pass(self):
        for name, seats in (("slice-m-p3.yaml", ["llm", "llm"]), ("slice-p3.yaml", ["llm", "scripted:trigger_k"]),
                            ("n3-group.yaml", ["llm"] * 3), ("n3-cheater.yaml", ["llm", "llm", "scripted:defect_once"])):
            self.assertIsNone(trial_cmd.check_seats(self.read(name), seats, name))

    def test_disagreement_is_refused(self):
        with self.assertRaisesRegex(ValueError, "seat 1 is LLM llm in the file but llm"):
            trial_cmd.check_seats(self.read("slice-p3.yaml"), ["llm", "llm"], "slice-p3.yaml")      # the one-LLM file for a two-LLM row
        one_llm = self.read("slice-p3.yaml").replace("- id: llm" + chr(10), "- id: llm1" + chr(10))
        with self.assertRaisesRegex(ValueError, "seat 2 is TRIGGER_K partner in the file but llm"):   # seat 1 renamed so only seat 2 disagrees
            trial_cmd.check_seats(one_llm, ["llm", "llm"], "slice-p3.yaml")
        with self.assertRaisesRegex(ValueError, "seat 2 is LLM in the file but scripted:trigger_k"):
            trial_cmd.check_seats(self.read("slice-m-p3.yaml"), ["llm", "scripted:trigger_k"], "slice-m-p3.yaml")
        with self.assertRaisesRegex(ValueError, "seat 3 is DEFECT_ONCE in the file but scripted:trigger_k"):
            trial_cmd.check_seats(self.read("n3-cheater.yaml"), ["llm", "llm", "scripted:trigger_k"], "n3-cheater.yaml")
        with self.assertRaisesRegex(ValueError, "has 3 seats"):
            trial_cmd.check_seats(self.read("slice-m-p3.yaml"), ["llm"] * 3, "slice-m-p3.yaml")
        with self.assertRaisesRegex(ValueError, "no agents"):
            trial_cmd.check_seats("id: x" + chr(10) + "market: {}", ["llm"], "x.yaml")
        text = self.read("slice-m-p3.yaml").replace("  - id: llm2", "# a note" + chr(10) + "  - id: llm2")
        with self.assertRaisesRegex(ValueError, "column-0 comment"):
            trial_cmd.check_seats(text, ["llm", "llm"], "slice-m-p3.yaml")

    def test_llm_seat_must_be_called_llm_i(self):
        text = self.read("slice-m-p3.yaml").replace("id: llm2", "id: bob")
        with self.assertRaisesRegex(ValueError, "seat 2 is LLM bob in the file but llm"):
            trial_cmd.check_seats(text, ["llm", "llm"], "slice-m-p3.yaml")

    def test_build_refuses_a_row_whose_seats_disagree_with_its_file(self):
        row = dict(ROW, scenario_file="slice-p1.yaml")                     # seats llm,llm against the one-LLM Track S file
        with self.assertRaisesRegex(ValueError, "seat 1 is LLM llm in the file but llm"):
            trial_cmd.build(row, args(), "/tmp/t")


ROW = {"trial_id": "a__p1__w0__s1__t0", "arm": "a", "penalty_point": "1", "scenario_file": "slice-m-p1.yaml", "communication": "tacit",
       "firms": "2", "seats": "llm,llm", "condition_texts": "all:neutral", "wording": "0", "seed": "1", "thinking": "0",
       "model_profile": "qwen3_14b", "temperature": "0.7", "top_p": "0.8", "top_k": "20", "max_tokens_talk": "320",
       "max_tokens_quote": "400", "max_tokens_question": "400", "timeout_sec": "120", "wave": "1", "introspection": "", "options": "{}"}
TEMPLATE = ["python", "-X", "utf8", "{trial_cmd}", "--trial-dir", "{trial_dir}", "--jar", "{jar}", "--scenarios", "{scenarios}",
            "--base-url", "qwen3_14b=" + URL14, "--model", "qwen3_14b=served14", "--api-key-env", "COLLUSION_VLLM_KEY",
            "--code-commit", "0123abcd", "--budget-tokens", "5000000", "--allow-remote"]


class Executors(unittest.TestCase):
    def test_one_template_serves_the_local_and_the_modal_executor(self):
        ns = argparse.Namespace(jar=str(JAR), scenarios=str(SCEN))
        local = run_grid.LocalExecutor(TEMPLATE, run_grid.local_extras(ns))
        argv = run_grid.build_command(local.template, ROW, "D", local.extras)
        self.assertEqual(str(HERE / "trial_cmd.py"), argv[3])
        self.assertEqual((str(JAR.resolve()), str(SCEN.resolve())), (argv[7], argv[9]))
        remote = modal_executor.ModalExecutor(TEMPLATE, invoke=lambda p: None).remote_argv(ROW)   # also checks --api-key-env
        self.assertEqual(["/app/trial_cmd.py", "/app/collusion-engine.jar", "/app/scenarios"], [remote[3], remote[7], remote[9]])
        self.assertEqual("@TRIAL_DIR@", remote[5])

    def test_local_without_jar_has_only_trial_cmd_and_clashes_are_refused(self):
        self.assertEqual({"trial_cmd": str(HERE / "trial_cmd.py")}, run_grid.local_extras(argparse.Namespace(jar="", scenarios="x")))
        with self.assertRaisesRegex(ValueError, "clash"):
            run_grid.build_command(["{trial_cmd}"], dict(ROW, trial_cmd="x"), "D", {"trial_cmd": "y"})
        with self.assertRaisesRegex(ValueError, "clash"):
            modal_executor.ModalExecutor(TEMPLATE, invoke=lambda p: None).remote_argv(dict(ROW, trial_cmd="x"))

    def test_modal_image_carries_the_trial_command(self):
        src = (HERE / "modal_executor.py").read_text(encoding="utf-8")
        self.assertIn('add_local_file(str(Path(__file__).resolve().parent / "trial_cmd.py"), REMOTE_TRIAL_CMD)', src)


class Cli(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cli(self, *extra, row=ROW):
        (self.d / "grid_row.json").write_text(json.dumps(row), encoding="utf-8")
        return subprocess.run([sys.executable, "-X", "utf8", str(HERE / "trial_cmd.py"), "--trial-dir", str(self.d), "--jar", "j.jar",
                               "--base-url", "http://127.0.0.1:9", "--model", "m", "--api-key-env", "K", "--code-commit", "0123abcd"]
                              + list(extra), capture_output=True, text=True)

    def test_print_shows_the_argv_and_runs_nothing(self):
        p = self.cli("--print")
        self.assertEqual(0, p.returncode, p.stderr)
        argv = json.loads(p.stdout)
        self.assertEqual(["java", "-jar", "j.jar", "run"], argv[:4])
        self.assertEqual("slice-m-p1.yaml", argv[argv.index("--scenario") + 1])
        self.assertFalse((self.d / "scenario.yaml").exists())

    def test_bad_row_exits_2_and_a_missing_java_is_a_failure(self):
        p = self.cli("--print", row=dict(ROW, thinking="yes"))
        self.assertEqual(2, p.returncode)
        self.assertIn("thinking must be 0 or 1", p.stderr)
        p = self.cli("--java", str(self.d / "no-such-java"))
        self.assertEqual(2, p.returncode)
        self.assertIn("trial_cmd: error", p.stderr)

    def test_allow_remote_reaches_the_game_only(self):
        fake = self.d / "fakejava.py"
        fake.write_text("import os, sys\nprint('ALLOW=' + os.environ.get('COLLUSION_ALLOW_REMOTE', '-'))\n", encoding="utf-8")
        wrapper = self.d / ("fakejava.cmd" if os.name == "nt" else "fakejava.sh")
        wrapper.write_text(('@"%s" "%s" %%*\n' if os.name == "nt" else '#!/bin/sh\nexec "%s" "%s" "$@"\n') % (sys.executable, fake), encoding="utf-8")
        wrapper.chmod(0o755)
        env_before = os.environ.get("COLLUSION_ALLOW_REMOTE")
        p = self.cli("--java", str(wrapper), "--allow-remote")
        self.assertEqual(0, p.returncode, p.stderr + p.stdout)
        self.assertIn("ALLOW=1", p.stdout)
        self.assertIn("trial_cmd: ", p.stdout)
        p = self.cli("--java", str(wrapper))
        self.assertIn("ALLOW=" + (env_before or "-"), p.stdout)


@unittest.skipIf(yaml is None or not JAR.is_file() or java_bin() is None, "needs PyYAML, engine/target/collusion-engine.jar and a JDK")
class EndToEnd(unittest.TestCase):
    def test_two_real_rows_through_run_grid_trial_cmd_and_the_jar(self):
        rows = real_rows()
        pick = [rows["headline-tacit__p1__w0__s91__t0"], rows["smoke-14b-chat__p3__w0__s1__t1"]]
        tmp = Path(tempfile.mkdtemp())
        try:
            with open(tmp / "grid.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=make_grid.GRID_COLS)
                w.writeheader()
                w.writerows(pick)
            with MockOpenAI() as m:
                tmpl = [sys.executable, "-X", "utf8", "{trial_cmd}", "--trial-dir", "{trial_dir}", "--jar", "{jar}", "--scenarios", "{scenarios}",
                        "--java", java_bin(), "--base-url", "qwen3_14b=" + m.base_url, "--model", "qwen3_14b=collude",
                        "--base-url", "qwen3_32b_fp8=" + m.base_url, "--model", "qwen3_32b_fp8=collude",
                        "--api-key-env", "COLLUSION_VLLM_KEY", "--code-commit", "0123abcd", "--allow-unwired"]
                base = ["run_grid.py", "--grid", str(tmp / "grid.csv"), "--out", str(tmp / "trials"), "--jar", str(JAR), "--"]
                self.assertEqual(0, run_grid.main(base + tmpl))
                calls = m.calls
                self.assertEqual(0, run_grid.main(base + tmpl))          # rerun: DONE trials are skipped
                self.assertEqual(calls, m.calls)
            for row in pick:
                d = tmp / "trials" / row["arm"] / row["trial_id"]
                self.assertTrue((d / "DONE").exists(), (d / "console.log").read_text(encoding="utf-8", errors="replace"))
                p = json.loads((d / "params.json").read_text(encoding="utf-8"))
                self.assertEqual((row["trial_id"], row["arm"], "0123abcd", int(row["penalty_point"]), int(row["wording"]), "collude"),
                                 (p["trial"], p["arm"], p["code_commit"], p["penalty_point"], p["wording"], p["model"]))
                self.assertEqual(row["thinking"] == "1", p["thinking"])
                self.assertEqual(["llm1", "llm2"], [s["seat"] for s in p["seats"]])
                self.assertEqual({"llm"}, {s["kind"] for s in p["seats"]})
                kinds = {json.loads(l)["kind"] for l in (d / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
                self.assertEqual("talk" in kinds, row["communication"] != "tacit")
                self.assertIn("quote", kinds)
                self.assertTrue((d / "cache.jsonl").exists() and (d / "calls.jsonl").exists() and (d / "run.jsonl").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
