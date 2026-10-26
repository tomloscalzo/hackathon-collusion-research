"""The 150-word talk cut is not a token-limit truncation (quality review Q9).

The 5% truncation stop is for replies cut at the token limit (finish_reason "length", or an imputed TRUNCATED reply).
A talk message cut by WordCap (logged with word_capped: true, or with truncated: true and a finish_reason other than
"length") is counted apart, as word_capped, in stop_rules and in collect's tables.
Run: python -X utf8 -m unittest tools/trial/test_wordcap_not_truncation.py"""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import derive  # noqa: E402
import stop_rules  # noqa: E402

WORD_CAP = {"kind": "talk", "round": 1, "seat": "llm1", "outcome": "OK", "truncated": True, "finish_reason": "stop",
            "parsed": {"message": "long talk"}}
WORD_CAP_FLAG = {"kind": "talk", "round": 1, "seat": "llm2", "outcome": "OK", "word_capped": True, "finish_reason": "stop",
                 "parsed": {"message": "long talk"}}
TOKEN_LIMIT = {"kind": "talk", "round": 2, "seat": "llm1", "outcome": "OK", "truncated": True, "finish_reason": "length",
               "parsed": {"message": "cut"}}
IMPUTED_CUT = {"kind": "quote", "round": 2, "seat": "llm2", "outcome": "IMPUTED", "refusal_kind": "TRUNCATED",
               "finish_reason": "length", "imputed": True, "quote": 1.0}
OLD_RECORD = {"kind": "talk", "round": 3, "seat": "llm1", "outcome": "TRUNCATED", "truncated": True, "parsed": {"message": "x"}}
PLAIN = {"kind": "quote", "round": 1, "seat": "llm1", "outcome": "OK", "quote": 2.0, "finish_reason": "stop"}


class Classify(unittest.TestCase):
    def test_token_limit_and_word_cap(self):
        f = derive.cut_kinds
        self.assertEqual(f(WORD_CAP), (False, True))
        self.assertEqual(f(WORD_CAP_FLAG), (False, True))
        self.assertEqual(f(TOKEN_LIMIT), (True, False))
        self.assertEqual(f(IMPUTED_CUT), (True, False))
        self.assertEqual(f(OLD_RECORD), (True, False))       # no finish_reason: the old flags still count
        self.assertEqual(f(PLAIN), (False, False))
        self.assertEqual(f(dict(TOKEN_LIMIT, word_capped=True)), (True, True))
        self.assertEqual(f(dict(WORD_CAP, finish_reason="")), (False, True))     # empty finish_reason: still a word cap
        self.assertEqual(f({"kind": "quote", "outcome": "IMPUTED", "refusal_kind": "TRUNCATED"}), (True, False))
        self.assertEqual(f({"kind": "talk", "word_capped": True, "truncated": True}), (False, True))   # no finish_reason key
        self.assertEqual(f({"kind": "attempt", "truncated": True, "finish_reason": ""}), (True, False))
        self.assertEqual(f({"kind": "talk", "truncated": "false", "finish_reason": "stop"}), (False, False))

    def test_transcript_marks(self):
        md = derive.render_transcript([WORD_CAP, TOKEN_LIMIT, dict(OLD_RECORD, round=1, seat="llm2")])
        self.assertIn("[WORD CAP]", md)
        self.assertIn("[TRUNCATED]", md)
        self.assertNotIn("[TRUNCATED; WORD CAP]", md)
        md2 = derive.render_transcript([{"kind": "talk", "round": 1, "seat": "llm1", "outcome": "TRUNCATED", "finish_reason": "stop",
                                         "parsed": {"message": "long"}}])
        self.assertIn("[WORD CAP]", md2)
        self.assertNotIn("TRUNCATED", md2)


class StopRule(unittest.TestCase):
    def write(self, d, events):
        (Path(d) / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    def test_measure_counts_them_apart(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, [WORD_CAP, WORD_CAP_FLAG, TOKEN_LIMIT, IMPUTED_CUT, OLD_RECORD, PLAIN])
            m = stop_rules.measure(d, "done", 1, "a")
        self.assertEqual((m["calls"], m["truncated"], m["word_capped"]), (6, 3, 2))

    def test_chatty_models_do_not_stop_the_wave(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, [WORD_CAP] * 5 + [PLAIN] * 5)      # half the calls word-capped, none token-limited
            mon = stop_rules.Monitor(out=lambda s: None, every=1)
            lines = []
            mon.out = lines.append
            for _ in range(3):
                mon.record(stop_rules.measure(d, "done", 1, "a"))
        self.assertIsNone(mon.stop_reason)
        self.assertIn("word-capped 15", lines[-1])
        with tempfile.TemporaryDirectory() as d:
            self.write(d, [TOKEN_LIMIT] + [PLAIN] * 9)       # 10% token-limited: the stop fires
            mon = stop_rules.Monitor(out=lambda s: None)
            for _ in range(3):
                mon.record(stop_rules.measure(d, "done", 1, "a"))
        self.assertIn("truncated", mon.stop_reason)


class CollectTables(unittest.TestCase):
    def test_messages_and_trials_report_word_caps_apart(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "trials" / "a__p3__w0__s1__t0"
            t.mkdir(parents=True)
            (t / "events.jsonl").write_text("\n".join(json.dumps(e) for e in [WORD_CAP, WORD_CAP_FLAG, TOKEN_LIMIT, OLD_RECORD]) + "\n",
                                            encoding="utf-8")
            (t / "params.json").write_text(json.dumps({"arm": "a", "thinking": False}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                collect.collect(Path(d) / "trials", Path(d) / "out")
            msgs = list(csv.DictReader(open(Path(d) / "out" / "messages.csv", encoding="utf-8")))
            (row,) = list(csv.DictReader(open(Path(d) / "out" / "trials.csv", encoding="utf-8")))
        self.assertEqual([(m["truncated"], m["word_capped"]) for m in msgs], [("0", "1"), ("0", "1"), ("1", "0"), ("1", "0")])
        self.assertEqual((row["truncated_talk"], row["word_capped_talk"]), ("2", "2"))

    def test_questions_use_the_same_rule(self):
        q = {"kind": "question", "round": 1, "seat": "llm1", "name": "confidant", "mode": "fed", "reply": "x"}
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "trials" / "a__p3__w0__s1__t0"
            t.mkdir(parents=True)
            (t / "events.jsonl").write_text("\n".join(json.dumps(e) for e in [dict(q, finish_reason="length"), dict(q, truncated="false")]) + "\n",
                                            encoding="utf-8")
            (t / "params.json").write_text(json.dumps({"arm": "a", "thinking": False}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                collect.collect(Path(d) / "trials", Path(d) / "out")
            qs = list(csv.DictReader(open(Path(d) / "out" / "questions.csv", encoding="utf-8")))
        self.assertEqual([r["truncated"] for r in qs], ["1", "0"])


if __name__ == "__main__":
    unittest.main()
