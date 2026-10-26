"""make_grid --model-profile / --exclude-arms: retarget the whole design to one profile (static, no Modal or LLM call)."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_grid  # noqa: E402

DESIGN = HERE / "design" / "trackm_design.yaml"


class ModelProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        cls.new, cls.notes = make_grid.retarget(cls.design, "gpt_oss_20b")
        cls.rows, _ = make_grid.expand(cls.new, str(DESIGN), {})

    def test_every_row_is_oss_thinking_on(self):
        self.assertTrue(self.rows)
        self.assertEqual({"gpt_oss_20b"}, {r["model_profile"] for r in self.rows})
        self.assertEqual({"1"}, {r["thinking"] for r in self.rows})
        self.assertTrue(all(r["trial_id"].endswith("__t1") for r in self.rows))
        self.assertEqual({"8192"}, {r["max_tokens_quote"] for r in self.rows})
        self.assertEqual({"16384"}, {r["context_window"] for r in self.rows})

    def test_skips_noted(self):
        arms = {r["arm"] for r in self.rows}
        for gone in ("smoke-14b-chat", "ctl-14b-joint", "r2f-confidant", "r3f-public", "oss-headline-chat-p1"):
            self.assertNotIn(gone, arms)
            self.assertTrue(any("arm %s skipped" % gone in n for n in self.notes), gone)
        for kept in ("headline-chat", "headline-tacit", "ctl-32b-compete", "wd-ask-noreport", "fx-chat-p5", "n3-cheater", "moral-prime-b"):
            self.assertIn(kept, arms)

    def test_t1_rows_match_the_original_t1_rows(self):
        orig, _ = make_grid.expand(self.design, str(DESIGN), {})
        by_id = {r["trial_id"]: r for r in orig}
        for r in self.rows:
            o = by_id[r["trial_id"]]
            for k in ("arm", "penalty_point", "communication", "seats", "condition_texts", "wording", "seed", "options", "wave", "slice"):
                self.assertEqual(o[k], r[k], (r["trial_id"], k))

    def test_errors_and_cli(self):
        with self.assertRaises(ValueError):
            make_grid.retarget(self.design, "nope")
        with self.assertRaises(ValueError):
            make_grid.retarget(self.design, "gpt_oss_20b", ("no-such-arm",))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "g.csv"
            self.assertEqual(0, make_grid.main(["x", str(DESIGN), str(out), "--model-profile", "gpt_oss_20b", "--exclude-arms", "m-pub,m-mon0"]))
            arms = {r["arm"] for r in csv.DictReader(open(out, encoding="utf-8"))}
            self.assertNotIn("m-pub", arms)
            self.assertIn("headline-chat", arms)
            self.assertEqual(2, make_grid.main(["x", str(DESIGN), str(out), "--exclude-arms", "m-pub"]))
            self.assertEqual(2, make_grid.main(["x", str(DESIGN), str(out), "--model-profile"]))
            self.assertEqual(2, make_grid.main(["x", str(DESIGN), str(out), "--model-profile", "bad"]))

    def test_oss_32k_keeps_only_the_fed_arms(self):
        new, _ = make_grid.retarget(self.design, "gpt_oss_20b_32k")
        self.assertEqual(["r2f-confidant", "r3f-public"], [a["name"] for a in new["arms"]])
        new["introspection_cell"] = {"point": 1, "communication": "private"}
        rows, _ = make_grid.expand(new, str(DESIGN), {})
        self.assertEqual(40, len(rows))
        self.assertEqual({"gpt_oss_20b_32k"}, {r["model_profile"] for r in rows})
        self.assertEqual({"32768"}, {r["context_window"] for r in rows})

    def test_default_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            make_grid.main(["x", str(DESIGN), str(a)])
            rows, _ = make_grid.expand(self.design, str(DESIGN), None)
            make_grid.write_grid(rows, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
