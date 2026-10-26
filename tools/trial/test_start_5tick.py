"""Unit U17 (5-tick start control arm): the design rows, the briefing text and the lint on the real files.
Run: python -X utf8 -m unittest tools/trial/test_start_5tick.py"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_m  # noqa: E402
import make_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "tools" / "trial" / "design" / "trackm_design.yaml"
TEXTS = ROOT / "engine" / "src" / "main" / "resources" / "prompts" / "seat_texts.json"
SCEN = ROOT / "engine" / "src" / "main" / "resources" / "scenarios" / "slice-m-p3.yaml"
APPROVED = ("In round 1 only, every market maker's quote must be between 1.00 and 1.05. "
            "From round 2 on, any quote in the usual range is allowed.")


def rows():
    import yaml
    design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    out, _ = make_grid.expand(design, str(DESIGN))
    return design, [r for r in out if r["arm"] == "start-5tick"]


class StartFiveTickTest(unittest.TestCase):
    def test_design_rows(self):
        _, rs = rows()
        self.assertEqual(40, len(rs))                                           # 5 wordings x 4 seeds x 2 thinking modes
        self.assertEqual({"0", "1"}, {r["thinking"] for r in rs})
        self.assertEqual(20, len([r for r in rs if r["thinking"] == "1"]))
        for r in rs:
            self.assertEqual("3", str(r["penalty_point"]))
            self.assertEqual("private", r["communication"])
            self.assertEqual("qwen3_32b_fp8", r["model_profile"])
            self.assertEqual("", r["pilot"])                                    # a regular row
            self.assertEqual("all:private_chat", r["condition_texts"])
            self.assertEqual({"briefing_notice": "start_5tick_rule", "start_ticks": 5}, json.loads(r["options"]))

    def test_the_rule_text_is_the_approved_wording_and_matches_the_option_bounds(self):
        texts = {t["name"]: t for t in json.loads(TEXTS.read_text(encoding="utf-8-sig"))["texts"]}
        t = texts["start_5tick_rule"]
        self.assertEqual("SEAT_NOTES", t["slot"])
        self.assertEqual(APPROVED, t["text"])
        self.assertNotIn("true_statement", t)                                   # it is true: the engine enforces it
        scen = SCEN.read_text(encoding="utf-8")
        s0 = float(re.search(r"s0:\s*([0-9.]+)", scen).group(1))
        inc = float(re.search(r"quoteIncrement:\s*([0-9.]+)", scen).group(1))
        self.assertEqual("1.00", "%.2f" % s0)
        self.assertEqual("1.05", "%.2f" % (s0 + 5 * inc))                       # the numbers in the text are floor + 5 ticks

    def test_lint_accepts_the_real_design_and_texts(self):
        import yaml
        design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        texts, errs = lint_m.load_texts([TEXTS])
        self.assertEqual([], errs)
        fails, _ = lint_m.lint(texts, design, [])
        self.assertEqual([], [f for f in fails if "start_5tick" in f or "start-5tick" in f])
        self.assertEqual([], fails)


if __name__ == "__main__":
    unittest.main()
