"""Formula-only check (engine option payoff_examples formula | none): the four design arms and their pairing with the neutral controls.
Run: python -X utf8 -m unittest tools/trial/test_formula_arms.py"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "tools" / "trial" / "design" / "trackm_design.yaml"
ARMS = {"fx-chat-p1": ("formula", "private", "headline-chat"), "fx-tacit-p1": ("formula", "tacit", "headline-tacit"),
        "nx-chat-p1": ("none", "private", "headline-chat"), "nx-tacit-p1": ("none", "tacit", "headline-tacit")}


def rows_of(global_options=None):
    import yaml
    design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    rows, _ = make_grid.expand(design, str(DESIGN), global_options)
    return rows


class FormulaArmsTest(unittest.TestCase):
    def test_arms_options_and_counts(self):
        rows = rows_of()
        for arm, (mode, comm, _ctl) in ARMS.items():
            mine = [r for r in rows if r["arm"] == arm]
            self.assertEqual(40, len(mine), arm)
            self.assertEqual({"0", "1"}, {str(r["thinking"]) for r in mine})
            self.assertEqual({mode}, {r["payoff_examples"] for r in mine})
            self.assertEqual({'{"payoff_examples":"%s"}' % mode}, {r["options"] for r in mine})
            self.assertEqual({"qwen3_32b_fp8"}, {r["model_profile"] for r in mine})
            self.assertEqual({comm}, {r["communication"] for r in mine})
        self.assertEqual(160, sum(1 for r in rows if r["arm"] in ARMS))

    def test_same_20_pairs_as_the_controls(self):
        rows = rows_of()
        key = lambda r: (r["wording"], r["seed"], r["thinking"])  # noqa: E731
        for arm, (_m, _c, ctl) in ARMS.items():
            mine = {key(r) for r in rows if r["arm"] == arm}
            ctrl = {key(r) for r in rows if r["arm"] == ctl and str(r["penalty_point"]) == "1"}
            self.assertEqual(ctrl, mine, arm)
            self.assertEqual(40, len(mine))

    def test_texts_match_the_controls_apart_from_the_option(self):
        rows = rows_of()
        for arm, (_m, _c, ctl) in ARMS.items():
            a = next(r for r in rows if r["arm"] == arm)
            c = next(r for r in rows if r["arm"] == ctl and str(r["penalty_point"]) == "1")
            for k in ("condition_texts", "communication", "scenario_file", "model_profile", "seats", "firms", "temperature", "top_p", "top_k", "max_tokens_talk", "max_tokens_quote", "timeout_sec", "context_window", "wave"):
                if k in a:
                    self.assertEqual(c.get(k), a.get(k), (arm, k))

    def test_other_rows_unchanged_by_the_new_values(self):
        for v in ("formula", "none"):
            self.assertEqual(v, make_grid.parse_global_options("payoff_examples=" + v)["payoff_examples"])
        with self.assertRaises(ValueError):
            make_grid.expand(__import__("yaml").safe_load(DESIGN.read_text(encoding="utf-8")), str(DESIGN),
                             {"payoff_examples": "bogus"})




class FormulaP5Test(unittest.TestCase):
    def test_fx_chat_p5(self):
        rows = rows_of()
        mine = [r for r in rows if r["arm"] == "fx-chat-p5"]
        ctl = [r for r in rows if r["arm"] == "headline-chat" and str(r["penalty_point"]) == "5" and r["thinking"] == "1"]
        self.assertEqual(20, len(mine))
        self.assertEqual({"1"}, {r["thinking"] for r in mine})
        self.assertEqual({"5"}, {r["penalty_point"] for r in mine})
        self.assertEqual({'{"payoff_examples":"formula"}'}, {r["options"] for r in mine})
        self.assertEqual({(r["wording"], r["seed"]) for r in ctl}, {(r["wording"], r["seed"]) for r in mine})
        self.assertEqual(ctl[0]["condition_texts"], mine[0]["condition_texts"])


class UnprimedLeversTest(unittest.TestCase):
    """The three exploratory unprimed-lever arms: fx-chat-p1 t1 plus exactly one existing seat text."""
    ARMS = {"fx-chat-p1-cot-a": ("all:private_chat", '{"briefing_notice":"cot_monitor_threat_a","payoff_examples":"formula"}'),
            "fx-chat-p1-moral-b": ("all:private_chat;llm1:moral_prime_b;llm2:moral_prime_b", '{"payoff_examples":"formula"}'),
            "fx-chat-p1-placebo-moral": ("all:private_chat;llm1:placebo_moral;llm2:placebo_moral", '{"payoff_examples":"formula"}')}

    def test_rows_equal_fx_chat_p1_t1_but_the_added_text(self):
        rows = rows_of()
        ctl = {(r["wording"], r["seed"]): r for r in rows if r["arm"] == "fx-chat-p1" and r["thinking"] == "1"}
        self.assertEqual(20, len(ctl))
        for arm, (ct, opts) in self.ARMS.items():
            mine = [r for r in rows if r["arm"] == arm]
            self.assertEqual(20, len(mine), arm)
            self.assertEqual(set(ctl), {(r["wording"], r["seed"]) for r in mine}, arm)
            for r in mine:
                self.assertEqual((ct, opts, "formula"), (r["condition_texts"], r["options"], r["payoff_examples"]), arm)
                c = ctl[(r["wording"], r["seed"])]
                diff = {k for k in r if r[k] != c[k]} - {"trial_id", "arm", "condition_texts", "options"}
                self.assertEqual(set(), diff, arm)


if __name__ == "__main__":
    unittest.main()
