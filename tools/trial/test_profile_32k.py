"""Unit U11: the 32k-context profile for the fed-back introspection arms (static: nothing is deployed, no Modal or LLM call)."""
import ast
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect  # noqa: E402
import make_grid  # noqa: E402
import qc_report  # noqa: E402
import trial_cmd  # noqa: E402
from test_clamp_qc import clamp_ev, quote, write_trial  # noqa: E402

DEPLOY = HERE.parents[1] / "deploy" / "modal_vllm.py"
DESIGN = HERE / "design" / "trackm_design.yaml"
FED = ("r2f-confidant", "r3f-public", "wd-noncomp", "wd-ask-noreport")     # unit U10: R2f / R3f; unit W2: the watchdog arms (fed answers too); the saved-only R2s / R3s stay on the 16,384 window


def profiles():
    """PROFILES from the deploy module, read without importing it (importing needs modal)."""
    for node in ast.parse(DEPLOY.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PROFILES":
            return {ast.literal_eval(k): {kw.arg: ast.literal_eval(kw.value) for kw in v.keywords}
                    for k, v in zip(node.value.keys, node.value.values)}
    raise AssertionError("no PROFILES in deploy/modal_vllm.py")


class DeployProfile(unittest.TestCase):
    def test_same_model_and_vllm_larger_window_fewer_inputs(self):
        p, base = profiles()["qwen3_32b_fp8_32k"], profiles()["qwen3_32b_fp8"]
        for k in ("model", "revision", "vllm", "reasoning", "scaledown", "max_containers"):
            self.assertEqual(base[k], p[k], k)
        self.assertEqual("H200", p["gpu"])   # owner 2026-10-25: faster GPUs for new work (same Hopper FP8 path as H100)
        self.assertEqual("0.9.2", p["vllm"])
        self.assertEqual("collusion-vllm-qwen3-32b-fp8-32k", p["app"])
        self.assertEqual((16384, 32768), (base["max_model_len"], p["max_model_len"]))
        self.assertEqual(8, p["max_inputs"])
        self.assertLess(p["max_inputs"], base["max_inputs"])

    def test_app_names_are_unique(self):
        apps = [v["app"] for v in profiles().values()]
        self.assertEqual(len(apps), len(set(apps)))

    def test_serve_command_uses_the_profile_window(self):
        src = DEPLOY.read_text(encoding="utf-8")
        self.assertRegex(src, r'"--max-model-len",\s*str\(MAX_MODEL_LEN\)')
        self.assertIn('MAX_MODEL_LEN = PROFILE["max_model_len"]', src)


class DesignAndCommand(unittest.TestCase):
    def setUp(self):
        self.design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        self.design["introspection_cell"] = {"point": 3, "communication": "private"}   # the real file leaves the cell open
        self.by_arm = {}
        for r in make_grid.expand(self.design)[0]:
            self.by_arm.setdefault(r["arm"], []).append(r)

    def test_design_profile_is_a_twin_with_a_window(self):
        mp = self.design["model_profiles"]
        self.assertEqual(32768, mp["qwen3_32b_fp8_32k"]["context_window"])
        self.assertEqual(mp["qwen3_32b_fp8"], {k: v for k, v in mp["qwen3_32b_fp8_32k"].items() if k != "context_window"})
        self.assertNotIn("context_window", mp["qwen3_32b_fp8"])
        self.assertLessEqual(set(mp), set(profiles()), "every design profile is a deploy profile")

    def test_only_the_fed_back_arms_use_it(self):
        for arm in FED:
            if arm in ("wd-noncomp", "wd-ask-noreport"):   # owner decision: the watchdog arms run on the 16,384 window like their headline-chat control
                self.assertEqual({"qwen3_32b_fp8"}, {r["model_profile"] for r in self.by_arm[arm]}, arm)
                self.assertEqual({"16384"}, {str(r["context_window"]) for r in self.by_arm[arm]}, arm)
            else:
                self.assertEqual({"qwen3_32b_fp8_32k"}, {r["model_profile"] for r in self.by_arm[arm]}, arm)
                self.assertEqual({"32768"}, {str(r["context_window"]) for r in self.by_arm[arm]}, arm)
            self.assertEqual({"fed"}, {json.loads(r["options"])["question_mode"] for r in self.by_arm[arm]})
        for arm, rs in self.by_arm.items():
            if arm not in FED:
                self.assertEqual({"16384"}, {str(r["context_window"]) for r in rs}, arm)
                self.assertNotEqual("qwen3_32b_fp8_32k", rs[0]["model_profile"], arm)

    def test_introspection_answers_are_not_capped_by_the_profile(self):
        for t in ("0", "1"):
            r2 = next(r for r in self.by_arm["r2f-confidant"] if str(r["thinking"]) == t)
            twin = next(r for r in self.by_arm["r2s-confidant"] if str(r["thinking"]) == t)
            for c in ("max_tokens_talk", "max_tokens_quote", "max_tokens_question"):
                if (t, c) == ("0", "max_tokens_quote"):
                    self.assertEqual(("400", "900"), (str(r2[c]), str(twin[c])))   # U23: r2s/r3s thinking-off quote 900
                else:
                    self.assertEqual(twin[c], r2[c], c)

    def _build(self, row):
        a = type("A", (), dict(java="java", jar="x.jar", scenarios="", code_commit="abcdef1", api_key_env="K", budget_tokens=0,
                               model=["qwen3_32b_fp8=m16", "qwen3_32b_fp8_32k=m32"],
                               base_url=["qwen3_32b_fp8=http://a", "qwen3_32b_fp8_32k=http://b"], allow_unwired=True))
        return trial_cmd.build({k: str(v) for k, v in row.items()}, a, "/t")[0]

    def test_trial_cmd_window_and_server_per_profile(self):
        a2, a0 = self._build(self.by_arm["r2f-confidant"][0]), self._build(self.by_arm["r2s-confidant"][0])
        self.assertEqual("32768", a2[a2.index("--context-window") + 1])
        self.assertEqual("16384", a0[a0.index("--context-window") + 1])
        self.assertEqual(("m32", "http://b"), (a2[a2.index("--model") + 1], a2[a2.index("--base-url") + 1]))
        self.assertEqual(("m16", "http://a"), (a0[a0.index("--model") + 1], a0[a0.index("--base-url") + 1]))
        self.assertEqual("on", a2[a2.index("--context-clamp") + 1])

    def test_old_grid_without_the_column_and_a_bad_value(self):
        row = dict(self.by_arm["r2s-confidant"][0])
        del row["context_window"]
        argv = self._build(row)
        self.assertEqual("16384", argv[argv.index("--context-window") + 1])
        row["context_window"] = "lots"
        with self.assertRaisesRegex(ValueError, "context_window"):
            self._build(row)


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def with_window(root, arm, thinking, events, window):
    d = write_trial(root, arm, 3, thinking, events)
    (d / "grid_row.json").write_text(json.dumps({"context_window": window}), encoding="utf-8")


class QcPerArmWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "trials"
        # P1 peaks at 20,000 (above 16,384 but inside its 32,768), P2 at 33,000 (overflows 32,768), P3 has a clamped call
        with_window(self.root, "P1", "on", [quote(1, "q1", 20000)], 32768)
        with_window(self.root, "P2", "on", [quote(1, "q1", 33000)], 32768)
        with_window(self.root, "P3", "on", [clamp_ev(1, "a0", "quote", "q1", 8192, 5000, 27000), quote(1, "q1", 27200)], 32768)
        with_window(self.root, "S", "on", [quote(1, "q1", 20000)], 16384)    # a standard arm: 20,000 overflows its own window
        self.out = Path(self.tmp.name) / "out"
        collect.collect(self.root, self.out)
        self.md = qc_report.build(self.out)             # no --window: the per-arm window comes from the grid

    def tearDown(self):
        self.tmp.cleanup()

    def test_trials_csv_carries_the_window(self):
        t = {r["arm"]: r for r in rows(self.out / "trials.csv")}
        self.assertEqual(["32768", "32768", "32768", "16384"], [t[a]["context_window"] for a in ("P1", "P2", "P3", "S")])
        self.assertEqual("33000", t["P2"]["max_prompt_tokens"])

    def test_overflow_is_judged_against_each_trials_own_window(self):
        part = self.md.split("## Trials with clamped or skipped calls")[1].split("## Arms with an extended")[0]
        self.assertIn("### Arm S", part)
        self.assertIn("yes (window 16384)", part)
        self.assertIn("### Arm P2", part)
        self.assertIn("yes (window 32768)", part)
        self.assertNotIn("### Arm P1", part)

    def test_extended_window_section_lists_every_trial_explicitly(self):
        sec = self.md.split("## Arms with an extended context window")[1].split("## Competitiveness")[0]
        for tid in ("P1__p3", "P2__p3", "P3__p3"):
            self.assertIn(tid, sec)
        self.assertNotIn("S__p3", sec)
        self.assertEqual(1, sec.count("| OVERFLOW |"))
        self.assertRegex(sec, r"Arm P3: 1 trial\(s\), 1 with an overflow, clamped or skipped call")
        self.assertRegex(sec, r"Arm P1: 1 trial\(s\), 0 with")
        self.assertIn("5000", self.md.split("### Arm P3")[1])          # the clamped call itself is listed

    def test_no_extended_arm_says_so_and_cli_window_overrides(self):
        d = Path(self.tmp.name) / "plain"
        write_trial(d / "trials", "A", 1, "off", [quote(1, "q1", 700)])
        collect.collect(d / "trials", d / "out")
        md = qc_report.build(d / "out")
        self.assertIn("No trial ran with a window above 16384", md)
        self.assertIn("yes (window 500)", qc_report.build(d / "out", window=500))     # explicit --window overrides
        # and it overrides a trial's own grid window too: P1 (20,000, window 32,768) overflows --window 10000
        self.assertIn("yes (window 10000)", qc_report.build(self.out, window=10000).split("### Arm P1")[1].split("###")[0])


if __name__ == "__main__":
    unittest.main()
