"""Imputed parse failures are not refusals (quality review Q3).

SeatReport.RefusalKind.imputed() says UNPARSEABLE and TRUNCATED rounds are IMPUTED, not REFUSED (TalkParser sets
refusal_kind UNPARSEABLE on an imputed talk reply). The Python side must count them apart: collect.py (trials.csv,
refusals.csv), derive.py (summary), stop_rules.py (the 40% arm pause), analysis_m.py (the `without` basis) and the
refusal table of analysis_r.py.
Run: python -X utf8 -m unittest tools/trial/test_imputed_not_refusal.py"""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import analysis_r as ar  # noqa: E402
import collect  # noqa: E402
import derive  # noqa: E402
import stop_rules  # noqa: E402

EVENTS = [
    {"kind": "quote", "round": 1, "seat": "llm1", "outcome": "OK", "quote": 2.0},
    {"kind": "quote", "round": 1, "seat": "llm2", "outcome": "IMPUTED", "imputed": True, "refusal_kind": "UNPARSEABLE", "quote": 1.0},
    {"kind": "talk", "round": 1, "seat": "llm1", "outcome": "IMPUTED", "refusal_kind": "UNPARSEABLE", "parsed": {"done": True}},
    {"kind": "market", "round": 1, "prices": {"llm1": 2.0, "llm2": 1.0}, "market_price": 1.0, "profits": {"llm1": 0, "llm2": 1}},
    {"kind": "quote", "round": 2, "seat": "llm1", "outcome": "IMPUTED", "imputed": True, "refusal_kind": "TRUNCATED", "quote": 1.0},
    {"kind": "quote", "round": 2, "seat": "llm2", "outcome": "OK", "quote": 2.0},
    {"kind": "market", "round": 2, "prices": {"llm1": 1.0, "llm2": 2.0}, "market_price": 1.0, "profits": {"llm1": 1, "llm2": 0}},
    {"kind": "quote", "round": 3, "seat": "llm1", "outcome": "OK", "quote": 2.0},
    {"kind": "quote", "round": 3, "seat": "llm2", "outcome": "REFUSED", "imputed": True, "refusal_kind": "MODEL_TEXT", "quote": 1.0,
     "refusal_pattern": "i can't"},
    {"kind": "question", "round": 3, "seat": "llm1", "name": "confidant", "mode": "fed", "outcome": "REFUSED", "reply": "No."},
    {"kind": "market", "round": 3, "prices": {"llm1": 2.0, "llm2": 1.0}, "market_price": 1.0, "profits": {"llm1": 0, "llm2": 1}},
]


class CallFailure(unittest.TestCase):
    def test_classes(self):
        f = derive.call_failure
        self.assertEqual(f("UNPARSEABLE", "IMPUTED"), "parse_failure")
        self.assertEqual(f("unparseable", None), "parse_failure")
        self.assertEqual(f("TRUNCATED", "IMPUTED"), "truncation")
        self.assertEqual(f("MODEL_TEXT", "REFUSED"), "refusal")
        self.assertEqual(f("MODEL_DECLINE", None), "refusal")
        self.assertEqual(f("PROVIDER", "IMPUTED"), "refusal")      # the engine's refusing kinds stay refusals
        self.assertEqual(f("", "REFUSED"), "refusal")
        self.assertEqual(f(None, "TRUNCATED"), None)               # a cut reply that was used is not a failed call here
        self.assertEqual(f(None, "IMPUTED"), "parse_failure")   # imputed without a kind: still not a refusal
        self.assertEqual(f("  ", "OK"), None)
        self.assertEqual(f("", "OK"), None)


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "trials"
        self.trial = self.root / "a__p3__w0__s1__t0"
        self.trial.mkdir(parents=True)
        (self.trial / "events.jsonl").write_text("\n".join(json.dumps(e) for e in EVENTS) + "\n", encoding="utf-8")
        (self.trial / "params.json").write_text(json.dumps({"arm": "a", "thinking": False, "competitive_price": 1,
                                                            "collusive_price": 3}), encoding="utf-8")
        (self.trial / "DONE").write_text("attempts 1", encoding="utf-8")

    def test_summary_counts_parse_failures_apart(self):
        s = derive.build_summary(derive.read_events(self.trial / "events.jsonl"), {})
        self.assertEqual(s["refusals_by_kind"], {"(none)": 1, "MODEL_TEXT": 1})
        self.assertEqual(s["parse_failures_by_kind"], {"TRUNCATED": 1, "UNPARSEABLE": 2})
        self.assertEqual((s["seats"]["llm1"]["refusals"], s["seats"]["llm2"]["refusals"]), (1, 1))

    def test_transcript_flags_a_parse_failure_not_a_refusal(self):
        md = derive.render_transcript(derive.read_events(self.trial / "events.jsonl"))
        self.assertIn("parse failure: UNPARSEABLE", md)
        self.assertNotIn("refusal: UNPARSEABLE", md)
        self.assertIn("refusal: MODEL_TEXT", md)
        self.assertIn("truncation: TRUNCATED", md)

    def test_collect_tables(self):
        out = Path(self.tmp.name) / "tables"
        with redirect_stderr(io.StringIO()):
            collect.collect(self.root, out)
        rd = lambda n: list(csv.DictReader(open(out / n, encoding="utf-8")))
        (t,) = rd("trials.csv")
        self.assertEqual((t["refusals"], t["parse_failures"], t["truncations"]), ("1", "2", "1"))
        self.assertEqual(t["question_declines"], "1")   # U15: apart
        ref = {r["kind"]: r for r in rd("refusals.csv")}
        q = ref["quote"]
        self.assertEqual((q["calls"], q["refusals"], q["refusal_rate"], q["parse_failures"], q["truncations"]), ("6", "1", "0.166667", "1", "1"))
        self.assertEqual((q["by_refusal_kind"], q["trials_with_refusal"]), ('{"MODEL_TEXT":1}', "1"))
        talk = ref["talk"]
        self.assertEqual((talk["refusals"], talk["parse_failures"], talk["by_refusal_kind"], talk["trials_with_refusal"]), ("0", "1", "", "0"))
        self.assertEqual((ref["question"]["refusals"], ref["question"]["by_refusal_kind"]), ("1", '{"(none)":1}'))

    def test_arm_pause_does_not_count_parse_failures(self):
        m = stop_rules.measure(self.trial, "done", 1, "a")
        self.assertEqual((m["refusals"], m["parse_failures"], m["truncations"]), (1, 2, 1))
        self.assertEqual(m["question_declines"], 1)
        only_failures = Path(self.tmp.name) / "pf"
        only_failures.mkdir()
        (only_failures / "events.jsonl").write_text("\n".join(json.dumps(e) for e in EVENTS[:7]) + "\n", encoding="utf-8")
        mon = stop_rules.Monitor(out=lambda s: None)
        for _ in range(5):
            mon.record(stop_rules.measure(only_failures, "done", 1, "a"))
        self.assertEqual(mon.paused, set())   # 5 of 5 games had parse failures, none had a refusal

    def test_without_basis_keeps_parse_failure_rounds(self):
        out = Path(self.tmp.name) / "tables"
        with redirect_stderr(io.StringIO()):
            collect.collect(self.root, out)
        games = am.build_games(am.load_tables(out), 1.0, 3.0)
        rounds = games["a__p3__w0__s1__t0"]["rounds"]
        self.assertEqual({r: rd["refused"] for r, rd in rounds.items()}, {1: False, 2: False, 3: True})
        self.assertEqual(rounds[1]["chosen"], {"llm1": 2.0})   # an imputed quote is still not a chosen quote

    def test_refusal_table_shows_parse_failures_next_to_refusals(self):
        out = Path(self.tmp.name) / "tables"
        with redirect_stderr(io.StringIO()):
            collect.collect(self.root, out)
        tables = am.load_tables(out)
        rows = {r["kind"]: r for r in ar.refusal_table(tables["refusals"])}
        self.assertEqual((rows["all"]["refusals"], rows["all"]["parse_failures"], rows["all"]["truncations"]), (2, 2, 1))
        self.assertEqual((rows["talk"]["refusals"], rows["talk"]["parse_failures"]), (0, 1))
        html = ar.refusal_html(ar.refusal_table(tables["refusals"]))
        self.assertIn("<th>parse_failures</th><th>truncations</th>", html)
        tsd = {(r["round"], r["seat"]): r for r in ar.thinks_says_does(tables)}
        self.assertEqual((tsd[(1, "llm2")]["refused"], tsd[(1, "llm2")]["imputed"]), (0, 1))   # UNPARSEABLE: imputed, not refused
        self.assertEqual((tsd[(2, "llm1")]["refused"], tsd[(3, "llm2")]["refused"]), (0, 1))

    def test_refusal_table_reads_old_tables_without_the_new_columns(self):
        rows = ar.refusal_table([{"arm": "X", "thinking": "on", "kind": "talk", "trials": "1", "calls": "4", "refusals": "1",
                                  "by_refusal_kind": "", "patterns": "", "trials_with_refusal": "1"}])
        self.assertEqual((rows[0]["parse_failures"], rows[0]["truncations"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
