"""Unit E1 (owner-approved, gpt-oss only): the trial command sets empty_talk_as_done for gpt_oss_20b rows only, and collect counts the
empty_reply_as_done events (trials.csv empty_talk_done_count, present only when some trial used the option).
Run: python -X utf8 -m unittest tools/trial/test_empty_talk_done.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import test_trial_cmd as ttc  # noqa: E402
import trial_cmd  # noqa: E402


@unittest.skipIf(ttc.yaml is None, "PyYAML not installed")
class TrialCmdGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = ttc.real_rows()

    def opts(self, tid):
        argv, _, _ = trial_cmd.build(self.rows[tid], ttc.args(), "/tmp/x", supported=frozenset(trial_cmd.PENDING))
        return json.loads(argv[argv.index("--options") + 1]) if "--options" in argv else None

    def test_oss_rows_get_the_option_and_keep_their_own(self):
        for tid, r in self.rows.items():
            if r["model_profile"] == "gpt_oss_20b":
                o = self.opts(tid)
                self.assertEqual("on", o["empty_talk_as_done"], tid)
                self.assertEqual("neutral", o["payoff_examples"], tid)

    def test_other_profiles_get_the_grid_cell_untouched(self):
        n = 0
        for tid, r in self.rows.items():
            if r["model_profile"] != "gpt_oss_20b":
                n += 1
                self.assertEqual(r.get("options") or "{}", trial_cmd.effective_options(r), tid)
                self.assertNotIn("empty_talk_as_done", trial_cmd.effective_options(r))
        self.assertGreater(n, 100)


class CollectCount(unittest.TestCase):
    def trial(self, root, name, on, n_events):
        d = Path(root) / name
        d.mkdir()
        (d / "params.json").write_text(json.dumps({"arm": "a", "trial_id": name, **({"empty_talk_as_done": True} if on else {})}), encoding="utf-8")
        ev = [{"seq": i, "kind": "empty_reply_as_done", "round": 2 + i, "seat": "llm1", "turn": 1, "draw_key": "talk|x|s1|llm1|r%d|t1|a0" % (2 + i)}
              for i in range(n_events)]
        ev.append({"seq": 99, "kind": "talk", "round": 2, "turn": 1, "seat": "llm1", "outcome": "OK", "parsed": {"message": "", "done": True}})
        (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\n", encoding="utf-8")
        return d

    def test_count_and_conditional_column(self):
        with tempfile.TemporaryDirectory() as t:
            d = self.trial(t, "with", True, 3)
            self.assertEqual(3, collect.trial_rows(d)[0]["empty_talk_done_count"])
            d0 = self.trial(t, "zero", True, 0)
            self.assertEqual(0, collect.trial_rows(d0)[0]["empty_talk_done_count"])
            d1 = self.trial(t, "off", False, 0)
            self.assertNotIn("empty_talk_done_count", collect.trial_rows(d1)[0])


if __name__ == "__main__":
    unittest.main()
