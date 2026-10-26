"""Tests for make_grid.py (C1.1, C1.2). Run: python -X utf8 -m unittest tools/trial/test_make_grid.py"""
import csv
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import make_grid  # noqa: E402

DESIGN = Path(__file__).resolve().parent / "design" / "trackm_design.yaml"
ID_RE = re.compile(r"^[a-z0-9-]+__p\d+__w\d+__s\d+__t[01]$")

SMALL = """
version: 1
points: {1: slice-p1.yaml, 2: slice-p2.yaml}
model_profiles:
  m:
    t1:  {temperature: 0.6, top_p: 0.95, top_k: 20, timeout_sec: 300, max_tokens: {talk: 4096, quote: 8192, question: 3072}}
    t0:  {temperature: 0.7, top_p: 0.8, top_k: 20, timeout_sec: 120, max_tokens: {talk: 320, quote: 400, question: 400}}
introspection_cell: {point: null, communication: null}
defaults: {model_profile: m, firms: 2, seats: [llm, llm], communication: tacit, condition_texts: {all: neutral},
           wordings: [0, 1], seeds: [1, 2, 3], thinking: [0, 1], wave: {t0: 1, t1: 2}}
arms:
  - {name: a, points: [1, 2]}
  - {name: r, cell_from: introspection_cell, introspection: R1}
"""


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


RAMP = ("smoke-14b-tacit", "smoke-14b-chat", "smoke-32b-tacit", "smoke-32b-chat",
        "ctl-14b-joint", "ctl-14b-compete", "ctl-32b-joint", "ctl-32b-compete")


# Unit M2 arms (private chat, point 1, neutral table declared in the design; covered by test_moral_priming.py)
M2_ARMS = {"moral-prime", "moral-prime-b", "moral-placebo", "d-cot-monitor-0", "wd-notice-only", "d-conflict-ethics",
           "d-temptation-ethics"}   # d-temptation-ethics: d-conflict-ethics with the temptation score (test_moral_priming.py)
MF_ARMS = {"mf-values", "mf-law", "mf-market", "mf-neutral-mm", "mf-b-rule", "mf-rule", "mf-b-one-l1", "mf-b-one-l2", "mf-ctl-b", "mf-ctl-placebo"}   # moral factorial; test_moral_priming.py
M2_ARMS = M2_ARMS | MF_ARMS
OSS_ARMS = {"oss-headline-tacit-p1", "oss-headline-chat-p1", "oss-headline-chat-p5"}   # G2: gpt-oss-20b, neutral, thinking on; test_design_gpt_oss.py
WD_ARMS = {"wd-noncomp", "wd-ask-noreport"}   # unit W2: neutral, 16k profile (owner: same as the headline-chat control); test_watchdog_w2.py
M2_ARMS = M2_ARMS | OSS_ARMS | WD_ARMS   # they also declare neutral payoff examples themselves
FX_ARMS = {"fx-chat-p1", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1", "fx-chat-p5"}
FX_ARMS = FX_ARMS | {"fx-ctl-joint", "fx-chat-p1-cot-a", "fx-chat-p1-moral-b", "fx-chat-p1-placebo-moral"}   # PR #246 and the unprimed levers; test_formula_arms.py
M2_ARMS = M2_ARMS | FX_ARMS   # formula-only check: declare their own payoff_examples; test_formula_arms.py

class MakeGridTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def small(self, text=SMALL):
        p = self.dir / "d.yaml"
        p.write_text(text, encoding="utf-8")
        return make_grid.expand(yaml.safe_load(text), p)

    def test_expansion_count_ids_and_parameters(self):
        rows, notes = self.small()
        self.assertEqual(2 * 2 * 3 * 2, len(rows))            # points x wordings x seeds x thinking; pending arm skipped
        self.assertEqual(1, len(notes))
        self.assertIn("r", notes[0])
        self.assertEqual("a__p1__w0__s1__t0", rows[0]["trial_id"])
        self.assertEqual(len(rows), len({r["trial_id"] for r in rows}))
        r = {x["trial_id"]: x for x in rows}["a__p2__w1__s3__t1"]
        self.assertEqual(("a", "2", "slice-p2.yaml", "tacit", "2", "llm,llm", "all:neutral", "1", "3", "1", "m", "2"),
                         tuple(r[k] for k in ("arm", "penalty_point", "scenario_file", "communication", "firms", "seats",
                                              "condition_texts", "wording", "seed", "thinking", "model_profile", "wave")))
        self.assertEqual(("0.6", "0.95", "20", "4096", "8192", "3072", "300"),   # distinct values: a column swap fails
                         tuple(r[k] for k in ("temperature", "top_p", "top_k", "max_tokens_talk", "max_tokens_quote",
                                              "max_tokens_question", "timeout_sec")))
        off = {x["trial_id"]: x for x in rows}["a__p2__w1__s3__t0"]
        self.assertEqual(("0.7", "400", "1"), (off["temperature"], off["max_tokens_quote"], off["wave"]))

    def test_deterministic_and_lf(self):
        a, b = self.dir / "a.csv", self.dir / "b.csv"
        d = yaml.safe_load(SMALL)
        for out in (a, b):
            rows, _ = make_grid.expand(d, self.dir / "d.yaml")
            make_grid.write_grid(rows, out)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertNotIn(b"\r", a.read_bytes())

    def test_introspection_arms_included_once_cell_is_set(self):
        rows, notes = self.small(SMALL.replace("{point: null, communication: null}", "{point: 2, communication: private}"))
        r = [x for x in rows if x["arm"] == "r"]
        self.assertEqual(2 * 3 * 2, len(r))
        self.assertEqual({"2"}, {x["penalty_point"] for x in r})
        self.assertEqual({"private"}, {x["communication"] for x in r})
        self.assertEqual({"R1"}, {x["introspection"] for x in r})
        self.assertEqual([], notes)

    def test_validation_errors(self):
        for bad, msg in ((SMALL.replace("seats: [llm, llm]", "seats: [llm]"), "seats"),
                         (SMALL.replace("points: [1, 2]", "points: [1, 9]"), "point 9"),
                         (SMALL.replace("  - {name: r,", "  - {name: a, points: [1]}\n  - {name: r,"), "duplicate"),
                         (SMALL.replace("thinking: [0, 1]", "thinking: [0, 2]"), "thinking"),
                         (SMALL.replace("model_profile: m,", "model_profile: zz,"), "model profile")):
            with self.assertRaises(ValueError, msg=msg) as cm:
                self.small(bad)
            self.assertIn(msg, str(cm.exception))

    def test_seeds_by_wording_map(self):
        base = SMALL.replace("wordings: [0, 1], seeds: [1, 2, 3],", "wordings: [0, 1], seeds_by_wording: {0: [7, 8], 1: [9, 10]},")
        rows, _ = self.small(base)
        a = [r for r in rows if r["arm"] == "a" and r["penalty_point"] == "1" and r["thinking"] == "0"]
        self.assertEqual([("0", "7", "1"), ("0", "8", "3"), ("1", "10", "4"), ("1", "9", "2")],
                         sorted((r["wording"], r["seed"], r["slice"]) for r in a))
        bad = base.replace("{0: [7, 8], 1: [9, 10]}", "{0: [7, 8]}")
        with self.assertRaises(ValueError) as cm:
            self.small(bad)
        self.assertIn("no seeds for wordings [1]", str(cm.exception))
        with self.assertRaises(ValueError):
            self.small(base.replace("1: [9, 10]", "1: [9]"))
        own = base.replace("{name: a, points: [1, 2]}", "{name: a, points: [1, 2], seeds: [5]}")   # an arm's own seeds win
        self.assertEqual({"5"}, {r["seed"] for r in self.small(own)[0] if r["arm"] == "a"})

    def test_real_design_file(self):
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        rows, notes = make_grid.expand(d, DESIGN)
        by_arm = {}
        for r in rows:
            by_arm.setdefault(r["arm"], []).append(r)
        for arm in ("headline-tacit", "headline-chat", "headline-monitored"):     # 4 points (p2 dropped) x 20 games x 2 modes
            self.assertEqual(4 * 20 * 2, len(by_arm[arm]), arm)
            self.assertEqual({"1", "3", "4", "5"}, {x["penalty_point"] for x in by_arm[arm]}, arm)
        self.assertEqual({"tacit", "private", "monitored"},
                         {by_arm[a][0]["communication"] for a in ("headline-tacit", "headline-chat", "headline-monitored")})
        # declared seed set (experiments/trackm-seeds-2026-10-24): 20 seeds, 5 per planned length 7/15/19/20, one per wording
        decl = {0: ["91", "42", "226", "118"], 1: ["94", "47", "227", "171"], 2: ["133", "55", "259", "174"],
                3: ["136", "115", "261", "193"], 4: ["151", "126", "273", "218"]}
        pairs = {a: {(r["wording"], r["seed"]) for r in by_arm[a]} for a in by_arm if not a.startswith(("smoke-", "ctl-", "r0-", "r1-", "r2-", "r3-", "r4-"))}
        want = {(str(w), s) for w, ss in decl.items() for s in ss}
        self.assertEqual(20, len(want))
        self.assertTrue(pairs)
        for a, got in pairs.items():
            self.assertEqual(want, got, a)                       # the same 20 (wording, seed) pairs in every arm
        self.assertEqual(3 * 4 * 20, len({(r["arm"], r["penalty_point"], r["wording"], r["seed"]) for r in rows
                                          if r["arm"].startswith("headline")}))
        for arm in ("n3-group", "n3-cheater", "m-pub", "m-mon0", "n3-ethics", "m-asym", "m-comp",
                    "m-inc-target", "m-inc-joint"):
            self.assertEqual(40, len(by_arm[arm]), arm)
            self.assertEqual({"3"}, {r["penalty_point"] for r in by_arm[arm]})
        self.assertEqual("llm,llm,llm", by_arm["n3-group"][0]["seats"])
        self.assertEqual("llm,llm,scripted:defect_once", by_arm["n3-cheater"][0]["seats"])
        self.assertEqual("n3-cheater.yaml", by_arm["n3-cheater"][0]["scenario_file"])
        self.assertEqual("all:private_chat;llm1:placebo_ethics;llm2:placebo_ethics;llm3:rule_ethics", by_arm["n3-ethics"][0]["condition_texts"])
        self.assertFalse([a for a in by_arm if a.startswith("r")])                # introspection waits for decision 9
        self.assertNotIn("m-comp-neutral", by_arm)             # identical to headline-chat (blank control)
        self.assertFalse([a for a in by_arm if a.startswith("d-") and a not in M2_ARMS])   # the D-set arms wait for the same cell (M2 arms sit at the fixed p1 cell)
        self.assertEqual(11, len(notes))                                         # 5 introspection (R2f R3f R2s R3s R4; the control is the headline) + 6 D-set arms skipped
        self.assertTrue(all(ID_RE.match(r["trial_id"]) for r in rows))
        main = [r for r in rows if r["arm"] not in RAMP and r["arm"] != "fx-ctl-joint"]   # fx-ctl-joint: a wave-0 control (PR #246)
        self.assertEqual({"1", "2", "5", "6"}, {r["wave"] for r in main})
        self.assertEqual({"1"}, {r["wave"] for r in main if r["thinking"] == "0"})  # thinking off is always wave 1
        self.assertEqual({"2"}, {r["wave"] for r in rows if r["thinking"] == "1" and r["arm"].startswith("headline")})
        for pt in "12345":                                                          # every scenario file exists
            self.assertTrue((make_grid.SCENARIOS / ("slice-p%s.yaml" % pt)).exists())
            self.assertTrue((make_grid.SCENARIOS / ("slice-m-p%s.yaml" % pt)).exists())
        for r in rows:
            self.assertTrue((make_grid.SCENARIOS / r["scenario_file"]).exists(), r["scenario_file"])

    def test_32b_comparison_cells(self):
        """C1.3: smoke (2 tacit + 2 chat) and pilot controls on both models and both modes, paired seeds, wave 0."""
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        rows, _ = make_grid.expand(d, DESIGN)
        ramp = [r for r in rows if r["arm"] in RAMP]
        self.assertEqual(16 + 12 + 80, len(ramp))   # smoke 16; ctl-14b 12; ctl-32b 2 arms x 20 games x 2 modes
        self.assertEqual(16, len([r for r in ramp if r["arm"].startswith("smoke")]) )
        self.assertEqual(80, len([r for r in ramp if r["arm"].startswith("ctl-32b")]))                                   # smoke 4 arms x 2 wordings x 2 modes; 14B controls 2 x 3 x 2; 32B controls 2 x 20 x 2
        self.assertEqual({"0"}, {r["wave"] for r in ramp})
        by = {}
        for r in ramp:
            by.setdefault(r["arm"], []).append(r)
        for model, tag in (("qwen3_14b", "14b"), ("qwen3_32b_fp8", "32b")):
            for arm in ("smoke-%s-tacit" % tag, "smoke-%s-chat" % tag):
                self.assertEqual({model}, {r["model_profile"] for r in by[arm]}, arm)
                self.assertEqual(4, len(by[arm]))
                self.assertEqual({"0", "1"}, {r["thinking"] for r in by[arm]})
            for kind in ("joint", "compete"):
                self.assertEqual({model}, {r["model_profile"] for r in by["ctl-%s-%s" % (tag, kind)]})
                self.assertEqual(6 if tag == "14b" else 40, len(by["ctl-%s-%s" % (tag, kind)]))
        self.assertEqual("tacit", by["smoke-32b-tacit"][0]["communication"])
        self.assertEqual("private", by["smoke-32b-chat"][0]["communication"])
        self.assertIn("llm1:maximise_joint_profit;llm2:maximise_joint_profit", by["ctl-32b-joint"][0]["condition_texts"])
        self.assertIn("llm1:compete_strict_instruction;llm2:compete_strict_instruction", by["ctl-32b-compete"][0]["condition_texts"])
        self.assertIn("llm1:compete_instruction;", by["ctl-14b-compete"][0]["condition_texts"] + ";")   # the 14B smoke control is unchanged
        # U20: the 32B controls use the declared 20 (wording, seed) pairs at point 3, private chat, both modes
        decl = {(w, str(s)) for w, ss in d["defaults"]["seeds_by_wording"].items() for s in ss}
        for arm in ("ctl-32b-joint", "ctl-32b-compete"):
            self.assertEqual(20, len(decl))
            self.assertEqual(decl, {(int(r["wording"]), r["seed"]) for r in by[arm] if r["thinking"] == "1"}, arm)
            self.assertEqual(decl, {(int(r["wording"]), r["seed"]) for r in by[arm] if r["thinking"] == "0"}, arm)
            self.assertEqual({"3"}, {r["penalty_point"] for r in by[arm]})
            self.assertEqual({"private"}, {r["communication"] for r in by[arm]})
            self.assertEqual({"0", "1"}, {r["thinking"] for r in by[arm]})
            self.assertNotIn("seeds", next(a for a in d["arms"] if a["name"] == arm))
        # (U20: the 14B smoke controls keep seed 1; they no longer pair with the 32B controls, which use the declared seeds)
        # the profile comes from the design's model_profiles; both names are deploy profile names
        self.assertEqual({"qwen3_14b", "qwen3_32b_fp8", "qwen3_32b_fp8_32k"}, set(d["model_profiles"]) - {"gpt_oss_20b", "gpt_oss_20b_32k"})   # U11 adds the 32k twin; G2 adds gpt_oss_20b and its 32k twin
        self.assertEqual("qwen3_32b_fp8", d["defaults"]["model_profile"])   # owner: 32B is the main model
        for r in rows:
            if not r["arm"].startswith(("smoke-14b", "ctl-14b")) and r["arm"] not in OSS_ARMS | WD_ARMS:   # the watchdog arms are now on qwen3_32b_fp8 too
                self.assertEqual("qwen3_32b_fp8", r["model_profile"], r["arm"])
        for r in ramp:
            self.assertEqual(d["model_profiles"][r["model_profile"]]["t" + r["thinking"]]["max_tokens"]["quote"], int(r["max_tokens_quote"]))

    def test_design_token_limits_smoke_informed(self):
        # fix-thinking_token_limits: the first live smoke truncated 96-97% of 14B and ~50% of 32B thinking-on calls at
        # talk 1,024 / quote 2,560.  Thinking on: quote 8,192, talk 8,192 (owner, U1), question 4,096, timeout 300 s (> Modal's 150 s
        # redirect; 8k tokens at ~40 tok/s is ~200 s).  Thinking off unchanged.  The pilot sets the final caps (decision 13).
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        for name in ("qwen3_14b", "qwen3_32b_fp8"):
            p = d["model_profiles"][name]
            self.assertEqual({"talk": 8192, "quote": 8192, "question": 4096}, p["t1"]["max_tokens"], name)
            self.assertEqual(300, p["t1"]["timeout_sec"], name)
            self.assertEqual({"talk": 320, "quote": 400, "question": 400}, p["t0"]["max_tokens"], name)
            self.assertEqual(120, p["t0"]["timeout_sec"], name)
            self.assertEqual((0.6, 0.95, 20), (p["t1"]["temperature"], p["t1"]["top_p"], p["t1"]["top_k"]), name)
            self.assertEqual((0.7, 0.8, 20), (p["t0"]["temperature"], p["t0"]["top_p"], p["t0"]["top_k"]), name)
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("smoke", text)
        self.assertIn("decision 13", text)
        d["introspection_cell"] = {"point": 3, "communication": "private"}
        rows, _ = make_grid.expand(d, DESIGN)
        on = [r for r in rows if r["thinking"] == "1"]
        off = [r for r in rows if r["thinking"] == "0"]
        self.assertTrue(on and off)
        self.assertEqual({("8192", "8192", "4096", "300")},
                         {(r["max_tokens_talk"], r["max_tokens_quote"], r["max_tokens_question"], r["timeout_sec"]) for r in on})
        # U23: only the saved-only introspection arms r2s/r3s raise the thinking-off quote limit (the in-reply answer), to 900
        self.assertEqual({("320", "400", "400", "120")},
                         {(r["max_tokens_talk"], r["max_tokens_quote"], r["max_tokens_question"], r["timeout_sec"]) for r in off
                          if r["arm"] not in ("r2s-confidant", "r3s-public")})
        s_off = [r for r in off if r["arm"] in ("r2s-confidant", "r3s-public")]
        self.assertEqual({"r2s-confidant", "r3s-public"}, {r["arm"] for r in s_off})
        self.assertEqual({("320", "900", "400", "120")},
                         {(r["max_tokens_talk"], r["max_tokens_quote"], r["max_tokens_question"], r["timeout_sec"]) for r in s_off})
        self.assertEqual({("8192", "8192", "4096", "300")},
                         {(r["max_tokens_talk"], r["max_tokens_quote"], r["max_tokens_question"], r["timeout_sec"])
                          for r in on if r["arm"] in ("r2s-confidant", "r3s-public")})

    def test_arm_max_tokens_override_validated_and_scoped(self):
        d = yaml.safe_load(SMALL)
        d["arms"][0]["max_tokens"] = {"t0": {"quote": 900}}
        rows, _ = make_grid.expand(d, self.dir / "d.yaml")
        got = {(r["thinking"], r["max_tokens_quote"], r["max_tokens_talk"]) for r in rows if r["arm"] == d["arms"][0]["name"]}
        self.assertEqual({("0", "900", "320"), ("1", "8192", "4096")}, got)
        for bad in ({"t2": {"quote": 9}}, {"t0": {"quote": 0}}, {"t0": {"bogus": 9}}, {"t0": {"quote": "9"}}, [900]):
            d["arms"][0]["max_tokens"] = bad
            with self.assertRaises(ValueError):
                make_grid.expand(d, self.dir / "d.yaml")

    def test_every_row_has_explicit_sampling_off_07_08_20_on_06_095_20(self):
        # U1b (owner): thinking-off rows carry Qwen's recommended non-thinking sampling explicitly; thinking-on rows keep 0.6/0.95/20.
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        d["introspection_cell"] = {"point": 3, "communication": "private"}
        rows, _ = make_grid.expand(d, DESIGN)
        self.assertGreater(len(rows), 50)
        for r in rows:
            got = (r["temperature"], r["top_p"], r["top_k"])
            self.assertEqual(("0.7", "0.8", "20") if r["thinking"] == "0" else ("0.6", "0.95", "20"), got, r["trial_id"])

    def test_per_arm_table(self):
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        d["introspection_cell"] = {"point": 4, "communication": "private"}
        rows, _ = make_grid.expand(d, DESIGN)
        first = {}
        for r in rows:
            if r["thinking"] == "1":
                first.setdefault(r["arm"], r)
        # arm: (wave t1, communication, firms, scenario, condition_texts)
        table = {
            "headline-tacit": ("2", "tacit", "2", "slice-m-p1.yaml", "all:neutral"),
            "headline-chat": ("2", "private", "2", "slice-m-p1.yaml", "all:private_chat"),
            "headline-monitored": ("2", "monitored", "2", "slice-m-p1.yaml", "all:regulator_reads"),
            "n3-group": ("5", "private", "3", "n3-group.yaml", "all:private_chat"),
            "n3-cheater": ("5", "private", "3", "n3-cheater.yaml", "all:private_chat"),
            "m-pub": ("5", "public", "2", "slice-m-p3.yaml", "all:chat_published"),
            "m-mon0": ("5", "unmonitored", "2", "slice-m-p3.yaml", "all:chat_not_monitored"),
            "n3-ethics": ("6", "private", "3", "n3-group.yaml", "all:private_chat;llm1:placebo_ethics;llm2:placebo_ethics;llm3:rule_ethics"),
            "m-asym": ("6", "private", "2", "slice-m-p3.yaml", "all:private_chat;llm1:placebo_ethics;llm2:rule_ethics"),
            "m-comp": ("6", "private", "2", "slice-m-p3.yaml", "all:private_chat"),
            "m-inc-target": ("6", "private", "2", "slice-m-p3.yaml", "all:private_chat;llm1:pressure_target;llm2:pressure_target"),
            "m-inc-joint": ("6", "private", "2", "slice-m-p3.yaml", "all:private_chat;llm1:maximise_joint_profit;llm2:maximise_joint_profit"),
            "start-5tick": ("6", "private", "2", "slice-m-p3.yaml", "all:private_chat"),   # U17
            "d-cot-monitor-a": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),   # D-set factor (U8) at the introspection cell
            "d-cot-monitor-b": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "d-temptation-b": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "d-conflict": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "d-temptation-a": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "d-placebo": ("6", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "r2f-confidant": ("4", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "r3f-public": ("4", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "r2s-confidant": ("4", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "r3s-public": ("4", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
            "r4-announced": ("4", "private", "2", "slice-m-p4.yaml", "all:private_chat"),
        }
        self.assertEqual(set(RAMP), {a for a in first if a in RAMP})
        first = {a: r for a, r in first.items() if a not in RAMP and a not in M2_ARMS}   # M2 arms: test_moral_priming.py
        self.assertEqual(set(table), set(first))
        for arm, want in table.items():
            r = first[arm]
            self.assertEqual(want, (r["wave"], r["communication"], r["firms"], r["scenario_file"], r["condition_texts"]), arm)
        opts = {a: first[a]["options"] for a in first}
        self.assertEqual('{"round_reminder":"compliance_reminder"}', opts["m-comp"])
        self.assertEqual('{"history_cap":10,"question":"confidant","question_mode":"fed"}', opts["r2f-confidant"])
        self.assertEqual('{"history_cap":10,"question":"public","question_mode":"fed"}', opts["r3f-public"])
        self.assertEqual('{"reply_extra":{"kind":"text","max_chars":600,"name":"confidant_answer","text":"confidant_inreply"}}', opts["r2s-confidant"])
        self.assertEqual('{"reply_extra":{"kind":"text","max_chars":600,"name":"public_answer","text":"public_inreply"}}', opts["r3s-public"])
        self.assertEqual('{"briefing_notice":"r4_explain","post_game_question":"public"}', opts["r4-announced"])
        self.assertEqual('{"briefing_notice":"cot_monitor_threat_a"}', opts["d-cot-monitor-a"])
        self.assertEqual('{"briefing_notice":"cot_monitor_threat_b"}', opts["d-cot-monitor-b"])
        for arm, name, text in (("d-conflict", "conflict_score", "score_conflict"), ("d-temptation-a", "temptation_score", "score_temptation_a"),
                                ("d-temptation-b", "temptation_score", "score_temptation_b"),
                                ("d-placebo", "placebo_score", "score_placebo")):
            self.assertEqual('{"reply_extra":{"kind":"integer","max":5,"min":1,"name":"%s","position":"last","text":"%s"}}' % (name, text), opts[arm])

    def test_dset_arms(self):
        """U8: the D-set arms run at the introspection (high-collusion) cell; the threat only with thinking on; the others in both modes."""
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        d["introspection_cell"] = {"point": 3, "communication": "private"}
        rows, _ = make_grid.expand(d, DESIGN)
        by = {}
        for r in rows:
            by.setdefault(r["arm"], []).append(r)
        for arm in ("d-cot-monitor-a", "d-cot-monitor-b"):
            self.assertEqual({"1"}, {r["thinking"] for r in by[arm]}, arm)
        for arm in ("d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo"):
            self.assertEqual({"0", "1"}, {r["thinking"] for r in by[arm]}, arm)
        for arm in ("d-cot-monitor-a", "d-cot-monitor-b", "d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo"):
            self.assertEqual({("3", "private")}, {(r["penalty_point"], r["communication"]) for r in by[arm]}, arm)
            self.assertEqual(20, len({(r["wording"], r["seed"]) for r in by[arm]}), arm)
            self.assertEqual({""}, {r["pilot"] for r in by[arm]}, arm)          # real arms, not throwaway pilot rows
        # the shared null control runs the same games: headline-chat has the same (wording, seed, thinking) triples at that point
        ctl = {(r["wording"], r["seed"], r["thinking"]) for r in rows if r["arm"] == "headline-chat" and r["penalty_point"] == "3"}
        self.assertTrue({(r["wording"], r["seed"], r["thinking"]) for r in by["d-conflict"]} <= ctl)
        d["introspection_cell"] = {"point": None, "communication": None}
        rows, notes = make_grid.expand(d, DESIGN)
        self.assertFalse([r for r in rows if r["arm"].startswith("d-") and r["arm"] not in M2_ARMS])
        self.assertTrue([n for n in notes if "d-cot-monitor-a" in n and "introspection_cell" in n])

    def test_more_validation(self):
        base = SMALL
        cases = ((base.replace("thinking: [0, 1]", "thinking: [false, true]"), "integers"),
                 (base.replace("communication: tacit,", "communication: bogus,"), "communication"),
                 (base.replace("condition_texts: {all: neutral}", "condition_texts: {llm9: neutral}"), "llm9"),
                 (base.replace("seeds: [1, 2, 3]", "seeds: [1, 1]"), "duplicate values"),
                 (base.replace("{name: a,", "{name: a__b,"), "arm name"),
                 (base.replace("wave: {t0: 1, t1: 2}", "wave: {t0: 1}"), "wave"),
                 (base.replace("cell_from: introspection_cell", "cell_from: nope"), "cell_from"),
                 (base.replace("seats: [llm, llm]", "seats: [llm, robot]"), "seat"))
        for bad, msg in cases:
            with self.assertRaises(ValueError, msg=msg) as cm:
                self.small(bad)
            self.assertIn(msg, str(cm.exception))

    def test_theory_join(self):
        rows, _ = make_grid.expand(yaml.safe_load(DESIGN.read_text(encoding="utf-8")), DESIGN)
        want = {"1": "0.7029", "2": "0.6262", "3": "0.5459", "4": "0.3249", "5": "0.0000"}
        for r in rows:
            if r["scenario_file"].startswith("slice-m-p"):
                self.assertEqual(want[r["penalty_point"]], r["theory_theta_star"], r["trial_id"])
            elif r["scenario_file"] == "n3-cheater.yaml":
                self.assertEqual("0.4395", r["theory_theta_star"], r["trial_id"])   # the N=3 theta* (U13)
            else:
                self.assertEqual("", r["theory_theta_star"])        # other multi-firm files carry no two-firm theory
        self.assertEqual("0.0000", [r for r in rows if r["penalty_point"] == "5"][0]["theory_theta_star"])
        # the value is read from the file itself, not a table in the tool
        self.assertEqual("0.5459", make_grid.theory_theta_star("slice-p3.yaml"))
        self.assertEqual("0.5459", make_grid.theory_theta_star("slice-m-p3.yaml"))
        self.assertEqual({"slice-m-p%d.yaml" % p for p in (1, 3, 4, 5)}, {r["scenario_file"] for r in rows if r["arm"].startswith("headline")})
        self.assertEqual("", make_grid.theory_theta_star("n3-group.yaml", required=False))
        with self.assertRaises(ValueError):
            make_grid.theory_theta_star("n3-group.yaml")

    def _fake_scenarios(self, files):
        d = Path(self.tmp.name) / "sc"
        d.mkdir(exist_ok=True)
        for name, text in files.items():
            (d / name).write_text(text, encoding="utf-8")
        orig = make_grid.SCENARIOS
        make_grid.SCENARIOS = d
        self.addCleanup(setattr, make_grid, "SCENARIOS", orig)

    def test_override_arm_scenario_theory_is_optional_but_read_when_present(self):
        nl = chr(10)
        self._fake_scenarios({"slice-p1.yaml": "# theory-theta-star: 0.25" + nl, "slice-p2.yaml": "# theory-theta-star: 0.5" + nl,
                              "own.yaml": "# theory-theta-star: 0.125" + nl, "bare.yaml": "id: z" + nl})
        text = SMALL.replace("  - {name: r, cell_from", "  - {name: o, points: [1], scenario: own.yaml}" + nl + "  - {name: b, points: [1], scenario: bare.yaml}" + nl + "  - {name: r, cell_from")
        rows, _ = self.small(text)
        got = {r["arm"]: r["theory_theta_star"] for r in rows}
        self.assertEqual({"a": "0.5", "o": "0.125", "b": ""}, {"a": got["a"], "o": got["o"], "b": got["b"]})   # a: last row is point 2

    def test_malformed_theory_value_is_an_error(self):
        nl = chr(10)
        for bad in ("abc", "1e-3", "-0.5", "5.", ""):
            self._fake_scenarios({"slice-p1.yaml": "# theory-theta-star: " + bad + nl, "slice-p2.yaml": "# theory-theta-star: 0.5" + nl})
            with self.assertRaises(ValueError, msg=bad) as cm:
                self.small()
            self.assertIn("malformed", str(cm.exception))

    def test_missing_theory_line_is_an_error(self):
        orig = make_grid.SCENARIOS
        d = Path(self.tmp.name) / "sc"
        d.mkdir()
        (d / "slice-p1.yaml").write_text("id: x" + chr(10), encoding="utf-8")
        (d / "slice-p2.yaml").write_text("# theory-theta-star: 0.5" + chr(10) + "id: y" + chr(10), encoding="utf-8")
        make_grid.SCENARIOS = d
        self.addCleanup(setattr, make_grid, "SCENARIOS", orig)
        with self.assertRaises(ValueError) as cm:
            self.small()
        self.assertIn("slice-p1.yaml", str(cm.exception))

    def test_introspection_arms_with_cell(self):
        """U10: shared control (headline-chat) + R2f, R3f, R2s, R3s, R4 at the cell, 20 games per arm and mode, paired with the control."""
        d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        d["introspection_cell"] = {"point": 4, "communication": "private"}
        rows, notes = make_grid.expand(d, DESIGN)
        r = [x for x in rows if x["introspection"]]
        self.assertEqual(5 * 20 * 2, len(r))
        self.assertEqual({"R2f", "R3f", "R2s", "R3s", "R4"}, {x["introspection"] for x in r})
        self.assertFalse([x for x in rows if x["arm"] in ("r0-control", "r1-reflection")])   # the control is headline-chat
        self.assertEqual({"4"}, {x["wave"] for x in r})
        self.assertEqual(20, len({x["seed"] for x in r}))   # the declared seed set (one seed per wording and length)
        for arm in ("r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"):
            mine = [x for x in r if x["arm"] == arm]
            self.assertEqual(40, len(mine), arm)
            self.assertEqual({""}, {x["pilot"] for x in mine}, arm)
            self.assertEqual({"all:private_chat"}, {x["condition_texts"] for x in mine}, arm)
            ctl = {(x["wording"], x["seed"], x["thinking"]) for x in rows if x["arm"] == "headline-chat" and x["penalty_point"] == "4"}
            self.assertEqual(ctl, {(x["wording"], x["seed"], x["thinking"]) for x in mine}, arm)   # same games: the arm pairs
        self.assertEqual({"qwen3_32b_fp8_32k": "32768"}, {x["model_profile"]: x["context_window"] for x in r if x["arm"] in ("r2f-confidant", "r3f-public")})
        self.assertEqual({"qwen3_32b_fp8": "16384"}, {x["model_profile"]: x["context_window"] for x in r if x["arm"] in ("r2s-confidant", "r3s-public", "r4-announced")})
        self.assertEqual(0, len(notes))
        self.assertIn('"question":"confidant"', [x for x in r if x["introspection"] == "R2f"][0]["options"])
        self.assertNotIn("question", [x for x in r if x["introspection"] == "R2s"][0]["options"].replace("confidant_inreply", ""))

    def test_trial_ids_parse_in_collect(self):
        """The id's thinking suffix must not leak into the seed that collect reads from the directory name."""
        m = collect.NAME_RE.match("headline-chat__p3__w2__s4__t1")
        self.assertEqual(("headline-chat", "3", "2", "4", "1"),
                         (m["arm"], m["penalty_point"], m["wording"], m["seed"], m["thinking_suffix"]))
        m = collect.NAME_RE.match("tacit__p1__w0__s1")
        self.assertEqual(("1", None), (m["seed"], m["thinking_suffix"]))
        meta = collect.trial_meta(self.dir / "a__p1__w0__s7__t0", {})
        self.assertEqual(("7", "off"), (meta["seed"], meta["thinking"]))
        meta = collect.trial_meta(self.dir / "a__p1__w0__s7__t1", {})
        self.assertEqual("on", meta["thinking"])
        for name, seed in (("a__p1__w0__s1_2__t1", "1_2"), ("a__p1__w0__s1__t1__t0", "1__t1")):
            self.assertEqual(seed, collect.trial_meta(self.dir / name, {})["seed"])
        self.assertEqual("on", collect.trial_meta(self.dir / "a__p1__w0__s1__t0", {"settings": {"thinking": True}})["thinking"])
        meta = collect.trial_meta(self.dir / "a__p1__w0__s7__t1", {"thinking": "off"})   # params.json wins
        self.assertEqual("off", meta["thinking"])

    def test_payoff_examples_column_defaults_to_anchored_and_options_unchanged(self):
        text = SMALL.replace("{name: a, points: [1, 2]}", "{name: a, points: [1, 2], options: {zeta: 1, alpha: true}}")
        rows, _ = self.small(text)
        self.assertEqual({"anchored"}, {r["payoff_examples"] for r in rows})
        self.assertEqual(make_grid.GRID_COLS[-1], "payoff_examples")
        self.assertEqual({'{"alpha":true,"zeta":1}'}, {r["options"] for r in rows})   # no payoff_examples key added

    def test_global_option_neutral_merges_into_every_row_and_ids_are_identical(self):
        text = SMALL.replace("{name: a, points: [1, 2]}", "{name: a, points: [1, 2], options: {zeta: 1, alpha: true}}")
        d = yaml.safe_load(text)
        anchored, _ = make_grid.expand(d, None)
        neutral, _ = make_grid.expand(d, None, make_grid.parse_global_options("payoff_examples=neutral"))
        self.assertEqual([r["trial_id"] for r in anchored], [r["trial_id"] for r in neutral])
        self.assertEqual({"neutral"}, {r["payoff_examples"] for r in neutral})
        self.assertEqual({'{"alpha":true,"payoff_examples":"neutral","zeta":1}'}, {r["options"] for r in neutral})
        for a, n in zip(anchored, neutral):   # nothing but options and payoff_examples differs
            self.assertEqual({k: v for k, v in a.items() if k not in ("options", "payoff_examples")},
                             {k: v for k, v in n.items() if k not in ("options", "payoff_examples")})

    def test_parse_global_options(self):
        g = make_grid.parse_global_options("payoff_examples=neutral,n=3,flag=true,name=abc")
        self.assertEqual({"payoff_examples": "neutral", "n": 3, "flag": True, "name": "abc"}, g)
        self.assertEqual({}, make_grid.parse_global_options(None))
        for bad in ("payoff_examples=weird", "novalue", "=x"):
            with self.assertRaises(ValueError, msg=bad):
                make_grid.parse_global_options(bad)

    def test_parse_global_options_top_level_commas_and_non_finite(self):
        g = make_grid.parse_global_options('a=[1,2],b={"x":1,"y":2},c="p,q",d=plain')
        self.assertEqual({"a": [1, 2], "b": {"x": 1, "y": 2}, "c": "p,q", "d": "plain"}, g)
        for bad in ("a=NaN", "a=Infinity", "a=-Infinity", "a=[1,2", 'a="x'):
            with self.assertRaises(ValueError, msg=bad):
                make_grid.parse_global_options(bad)

    def test_explicit_anchored_drops_the_key_and_is_digest_identical(self):
        text = SMALL.replace("{name: a, points: [1, 2]}", "{name: a, points: [1, 2], options: {zeta: 1, alpha: true}}")
        d = yaml.safe_load(text)
        default, _ = make_grid.expand(d, None)
        explicit, _ = make_grid.expand(d, None, make_grid.parse_global_options("payoff_examples=anchored"))
        self.assertEqual(default, explicit)
        self.assertEqual({"anchored"}, {r["payoff_examples"] for r in explicit})
        self.assertTrue(all("payoff_examples" not in r["options"] for r in explicit))
        arm_neutral = yaml.safe_load(text.replace("alpha: true}", "alpha: true, payoff_examples: neutral}"))
        r, _ = make_grid.expand(arm_neutral, None)
        self.assertEqual({"neutral"}, {x["payoff_examples"] for x in r})
        r, _ = make_grid.expand(arm_neutral, None, {"payoff_examples": "anchored"})   # the global option wins
        self.assertEqual(default, r)

    def test_anchored_grid_is_the_previous_bytes_plus_the_new_last_column(self):
        text = SMALL.replace("{name: a, points: [1, 2]}", "{name: a, points: [1, 2], options: {zeta: 1, alpha: true}}")
        rows, _ = self.small(text)
        out = self.dir / "g.csv"
        make_grid.write_grid(rows, out)
        lines = out.read_bytes().decode().split("\n")
        self.assertEqual("payoff_examples", lines[0].rsplit(",", 1)[1])
        self.assertEqual({"anchored"}, {ln.rsplit(",", 1)[1] for ln in lines[1:] if ln})
        old = "\n".join(ln.rsplit(",", 1)[0] if ln else ln for ln in lines).encode()
        # sha256 of the grid written by make_grid.py at 8bfe366 (before payoff_examples) for this design
        self.assertEqual("029ee01065932266869d1c79679e8698b89b4fcd31a5cdcf9761fcd18bd264c0", hashlib.sha256(old).hexdigest())

    def test_cli_global_options_and_real_design_twin(self):
        a, n = self.dir / "a.csv", self.dir / "n.csv"
        design = str(DESIGN)
        cell = self.dir / "cell.json"
        cell.write_text('{"point": 3, "communication": "private"}', encoding="utf-8")
        self.assertEqual(0, make_grid.main(["x", design, str(a), "--cell-file", str(cell)]))
        self.assertEqual(0, make_grid.main(["x", design, str(n), "--cell-file", str(cell), "--global-options", "payoff_examples=neutral"]))
        ra, rn = read(a), read(n)
        self.assertEqual({"neutral"}, {r["payoff_examples"] for r in ra if r["arm"] in M2_ARMS - FX_ARMS})   # they declare neutral themselves
        ra, rn = [r for r in ra if r["arm"] not in M2_ARMS], [r for r in rn if r["arm"] not in M2_ARMS]
        self.assertEqual([r["trial_id"] for r in ra], [r["trial_id"] for r in rn])
        self.assertEqual({"anchored"}, {r["payoff_examples"] for r in ra})
        self.assertEqual({"neutral"}, {r["payoff_examples"] for r in rn})
        self.assertTrue(all("payoff_examples" not in r["options"] for r in ra))
        self.assertTrue(all(json.loads(r["options"])["payoff_examples"] == "neutral" for r in rn))
        for x, y in zip(ra, rn):   # the rest of each options cell is untouched
            o = json.loads(y["options"])
            del o["payoff_examples"]
            self.assertEqual(json.loads(x["options"]), o)
        self.assertEqual(2, make_grid.main(["x", design, str(self.dir / "b.csv"), "--global-options", "payoff_examples=bad"]))
        self.assertEqual(2, make_grid.main(["x", design, str(self.dir / "b.csv"), "--global-options"]))


if __name__ == "__main__":
    unittest.main()
