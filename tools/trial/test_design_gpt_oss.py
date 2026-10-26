"""Unit G2: the gpt-oss-20b arms of trackm_design.yaml (static: expands the design, no Modal or LLM call)."""
import copy
import json
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_grid  # noqa: E402

DESIGN = HERE / "design" / "trackm_design.yaml"
OSS = ("oss-headline-tacit-p1", "oss-headline-chat-p1", "oss-headline-chat-p5")


def expand(design):
    rows, _ = make_grid.expand(design, str(DESIGN), {})
    return rows


class GptOssArms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
        cls.rows = expand(cls.design)

    def test_exactly_60_gpt_oss_rows(self):
        oss = [r for r in self.rows if r["model_profile"] == "gpt_oss_20b"]
        self.assertEqual(60, len(oss))
        self.assertEqual(set(OSS), {r["arm"] for r in oss})
        self.assertEqual(oss, [r for r in self.rows if r["arm"] in OSS])
        for arm in OSS:
            self.assertEqual(20, sum(1 for r in oss if r["arm"] == arm), arm)

    def test_row_settings(self):
        want = {"oss-headline-tacit-p1": ("1", "tacit", "neutral"),
                "oss-headline-chat-p1": ("1", "private", "private_chat"),
                "oss-headline-chat-p5": ("5", "private", "private_chat")}
        for r in self.rows:
            if r["arm"] not in OSS:
                continue
            pt, comm, text = want[r["arm"]]
            self.assertEqual((pt, comm), (str(r["penalty_point"]), r["communication"]), r["trial_id"])
            self.assertIn(text, r["condition_texts"], r["trial_id"])
            self.assertEqual(1, int(r["thinking"]))
            self.assertTrue(r["trial_id"].endswith("__t1"))
            self.assertEqual("neutral", r["payoff_examples"])
            self.assertEqual({"payoff_examples": "neutral"}, json.loads(r["options"]))
            self.assertEqual("gpt_oss_20b", r["model_profile"])
            self.assertEqual(16384, int(r["context_window"]))
            self.assertEqual("", r["pilot"])

    def test_same_cells_as_qwen_headline(self):
        """The 20 (wording, seed) pairs equal those of the Qwen headline arms, so the cross-model comparison pairs."""
        def pairs(arm):
            return sorted({(int(r["wording"]), int(r["seed"])) for r in self.rows if r["arm"] == arm})
        self.assertEqual(pairs("headline-tacit"), pairs("oss-headline-tacit-p1"))
        self.assertEqual(pairs("headline-chat"), pairs("oss-headline-chat-p5"))
        self.assertEqual(20, len(pairs("oss-headline-chat-p1")))

    def test_no_other_row_changes(self):
        d = copy.deepcopy(self.design)
        d["arms"] = [a for a in d["arms"] if a["name"] not in OSS]
        del d["model_profiles"]["gpt_oss_20b"]
        before = expand(d)
        after = [r for r in self.rows if r["arm"] not in OSS]
        self.assertEqual(before, after)
        self.assertEqual(len(before) + 60, len(self.rows))


if __name__ == "__main__":
    unittest.main()
