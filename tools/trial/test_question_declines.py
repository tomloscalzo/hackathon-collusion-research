"""U15: introspection-question declines never count toward the 40% arm pause; quote/talk refusals do.
Run: python -X utf8 -m unittest tools/trial/test_question_declines.py"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import derive  # noqa: E402
import stop_rules  # noqa: E402


def events(question_declines=0, quote_refusals=0):
    ev = [{"kind": "quote", "round": 1, "seat": "llm1", "outcome": "OK", "quote": 2.0, "tokens_in": 10, "tokens_out": 5},
          {"kind": "market", "round": 1, "prices": {"llm1": 2.0}, "market_price": 2.0, "profits": {"llm1": 1}}]
    for i in range(question_declines):
        ev.append({"kind": "question", "round": 1, "seat": "llm1", "name": "confidant", "mode": "fed", "outcome": "REFUSED",
                   "refusal_kind": "MODEL_TEXT", "refusal_pattern": "i can't", "reply": "I can't say."})
    for i in range(quote_refusals):
        ev.append({"kind": "quote", "round": 2 + i, "seat": "llm1", "outcome": "REFUSED", "refusal_kind": "MODEL_TEXT", "quote": 1.0})
    return ev


def trial(root, arm, n, ev):
    d = Path(root) / arm / ("%s__p1__w0__s%d__t0" % (arm, n))
    d.mkdir(parents=True)
    (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\n", encoding="utf-8")
    (d / "params.json").write_text(json.dumps({"arm": arm, "thinking": "off", "model": "m"}), encoding="utf-8")
    (d / "DONE").write_text("attempts 1", encoding="utf-8")
    return d


class Pause(unittest.TestCase):
    def run_arm(self, **kw):
        mon = stop_rules.Monitor(out=lambda *_: None)
        with tempfile.TemporaryDirectory() as root:
            for n in range(6):
                d = trial(root, "a", n, events(**kw))
                mon.record(stop_rules.measure(d, "done", 1.0, "a"))
        return mon

    def test_many_question_declines_not_paused(self):
        mon = self.run_arm(question_declines=5)
        self.assertNotIn("a", mon.paused)
        self.assertTrue(all(i["refusals"] == 0 and i["question_declines"] == 5 for i in mon.infos))

    def test_quote_refusals_pause(self):
        self.assertIn("a", self.run_arm(quote_refusals=1).paused)

    def test_preload_also_exempt(self):
        mon = stop_rules.Monitor(out=lambda *_: None)
        with tempfile.TemporaryDirectory() as root:
            for n in range(6):
                mon.preload(stop_rules.measure(trial(root, "a", n, events(question_declines=3)), "done", 1.0, "a"))
        self.assertNotIn("a", mon.paused)

    def test_mixed_below_threshold_not_paused(self):
        mon = stop_rules.Monitor(out=lambda *_: None)
        with tempfile.TemporaryDirectory() as root:
            for n in range(5):   # 2 of 5 games (40%, not more than 40%) have a quote refusal; all have question declines
                mon.record(stop_rules.measure(trial(root, "a", n, events(question_declines=4, quote_refusals=int(n < 2))), "done", 1.0, "a"))
        self.assertNotIn("a", mon.paused)

    def test_refused_without_kind_is_a_decline(self):
        with tempfile.TemporaryDirectory() as root:
            ev = events() + [{"kind": "question", "round": 1, "seat": "llm1", "outcome": "REFUSED"}]
            m = stop_rules.measure(trial(root, "a", 0, ev), "done", 1.0, "a")
        self.assertEqual((m["refusals"], m["question_declines"]), (0, 1))

    def test_helper(self):
        self.assertTrue(derive.is_question_decline("question", "MODEL_TEXT"))
        self.assertTrue(derive.is_question_decline("question", None, "REFUSED"))
        self.assertFalse(derive.is_question_decline("question", "UNPARSEABLE"))
        self.assertFalse(derive.is_question_decline("quote", "MODEL_TEXT"))


class Tables(unittest.TestCase):
    def test_collect_reports_apart(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            trial(root, "a", 0, events(question_declines=2, quote_refusals=1))
            collect.collect(Path(root), Path(out))
            t = list(csv.DictReader(open(Path(out) / "trials.csv", encoding="utf-8")))[0]
            self.assertEqual((t["refusals"], t["question_declines"]), ("1", "2"))
            rows = {r["kind"]: r for r in csv.DictReader(open(Path(out) / "refusals.csv", encoding="utf-8"))}
            self.assertEqual((rows["question"]["refusals"], rows["question"]["counts_toward_pause"]), ("2", "0"))
            self.assertEqual((rows["quote"]["refusals"], rows["quote"]["counts_toward_pause"]), ("1", "1"))
            self.assertEqual(rows["talk"]["counts_toward_pause"], "1")


if __name__ == "__main__":
    unittest.main()
