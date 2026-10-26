"""Tests for collect.py (C9.1, C9.2). Run: python -X utf8 -m unittest tools/trial/test_collect.py"""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "collect"
TRIALS, EXPECTED = FIX / "trials", FIX / "expected"
NAMES = ("trials.csv", "rounds.csv", "messages.csv", "questions.csv", "refusals.csv", "clamp.csv", "clamp_summary.csv")


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class SelfReportTest(unittest.TestCase):
    """U8: rounds.csv carries the seat's extra-field answer (events: self_report, self_report_name, self_report_kind)."""

    def test_self_report_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp) / "trials" / "d-conflict__p1__w0__s1__t0"
            t.mkdir(parents=True)
            (t / "params.json").write_text(json.dumps({"arm": "d-conflict", "thinking": "off"}), encoding="utf-8")
            evs = [{"kind": "quote", "round": 1, "seat": "a0", "quote": 2.4, "outcome": "OK", "self_report": 4,
                    "self_report_name": "conflict_score", "self_report_kind": "integer", "self_report_valid": True},
                   {"kind": "quote", "round": 1, "seat": "a1", "quote": 2.4, "outcome": "OK", "self_report": None,
                    "self_report_name": "conflict_score", "self_report_kind": "integer", "self_report_valid": False},
                   {"kind": "quote", "round": 2, "seat": "a0", "quote": 2.4, "outcome": "OK", "self_report": "unsure",
                    "self_report_name": "feeling", "self_report_kind": "text"},
                   {"kind": "quote", "round": 2, "seat": "a1", "quote": 2.4, "outcome": "OK"}]
            (t / "events.jsonl").write_text("".join(json.dumps(e) + chr(10) for e in evs), encoding="utf-8")
            (t / "DONE").write_text("attempts 1", encoding="utf-8")
            out = Path(tmp) / "out"
            collect.collect(Path(tmp) / "trials", out)
            r = rows(out / "rounds.csv")
            self.assertIn("self_report", collect.ROUND_COLS)
            self.assertEqual([("4", "conflict_score", "integer"), ("", "conflict_score", "integer"), ("unsure", "feeling", "text"),
                              ("", "", "")], [(x["self_report"], x["self_report_name"], x["self_report_kind"]) for x in r])


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        collect.collect(TRIALS, self.out)

    def test_matches_expected_tables(self):
        for n in NAMES:  # read_text translates CRLF from an autocrlf checkout
            self.assertEqual((EXPECTED / n).read_text(encoding="utf-8"), (self.out / n).read_text(encoding="utf-8"), n)

    def test_trials_row_per_trial_with_hand_computed_measures(self):
        t = {r["trial_id"]: r for r in rows(self.out / "trials.csv")}
        self.assertEqual(2, len(t))
        a = t["tacit__p1__w0__s1"]
        self.assertEqual(("tacit", "off", "Qwen3-14B", "1", "0", "1", "done"),
                         (a["arm"], a["thinking"], a["model"], a["penalty_point"], a["wording"], a["seed"], a["status"]))
        self.assertEqual(("0.5", "1", "4.9", "1"), (a["collusion_level"], a["time_to_high_price"], a["profit_total"], a["refusals"]))
        b = t["chat__p1__w0__s2"]
        self.assertEqual(("on", "3", "1", "1", "1"), (b["thinking"], b["messages"], b["truncated_talk"], b["imputed"], b["refusals"]))  # the refused question is a question decline, apart (U15)
        self.assertEqual(("1", "0"), (b["parse_failures"], b["truncations"]))  # the UNPARSEABLE quote is imputed, not refused (Q3)
        self.assertEqual("", b["time_to_high_price"])

    def test_competitive_round_flag_and_firms_table(self):   # U16: floor = competitive_price 2.0, tick 0.01 (default)
        r = {(x["trial_id"], x["round"], x["seat"]): x["competitive_round"] for x in rows(self.out / "rounds.csv")}
        self.assertEqual("", r[("tacit__p1__w0__s1", "1", "a0")])      # round 1 is not scored
        self.assertEqual("0", r[("tacit__p1__w0__s1", "2", "a0")])     # 2.4 against a1's 2.4
        self.assertEqual("1", r[("tacit__p1__w0__s1", "2", "a1")])     # 2.0 undercuts a0's 2.4
        f = {(x["trial_id"], x["seat"]): x for x in rows(self.out / "firms.csv")}
        self.assertEqual(("0", "2", "above_floor"), (f[("tacit__p1__w0__s1", "a0")]["always_competitive"], f[("tacit__p1__w0__s1", "a0")]["first_stop_round"], f[("tacit__p1__w0__s1", "a0")]["round1_class"]))
        self.assertEqual("floor", f[("chat__p1__w0__s2", "a1")]["round1_class"])

    def test_rounds_carry_profit_and_parse_status(self):
        r = [x for x in rows(self.out / "rounds.csv") if x["trial_id"].startswith("chat") and x["round"] == "1" and x["seat"] == "a1"][0]
        self.assertEqual(("2.0", "2.5", "IMPUTED", "UNPARSEABLE", "1"), (r["quote"], r["profit"], r["parse_status"], r["refusal_kind"], r["imputed"]))

    def test_messages_turn_words_truncated_and_position_fallback(self):
        m = [x for x in rows(self.out / "messages.csv")]
        self.assertEqual(3, len(m))
        self.assertEqual(("1", "3", "1"), (m[1]["turn"], m[1]["words"], m[1]["truncated"]))
        self.assertEqual("0", m[2]["turn"])  # the round-2 talk has no turn field: position in the round
        self.assertEqual("REFUSED", m[2]["parse_status"])

    def test_deterministic_lf_and_rerun_identical(self):
        again = Path(self.tmp.name) / "again"
        collect.collect(TRIALS, again)
        for n in NAMES:
            raw = (self.out / n).read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertEqual(raw, (again / n).read_bytes())

    def test_metadata_falls_back_to_dir_name_and_marks_status(self):
        root = Path(self.tmp.name) / "t" / "wild__p3__w2__s9"
        root.mkdir(parents=True)
        (root / "events.jsonl").write_text('{"kind":"market","round":1,"market_price":2.0,"profits":{}}\n', encoding="utf-8")
        (root / "FAILED").write_text("x", encoding="utf-8")
        collect.collect(root.parent, Path(self.tmp.name) / "o2")
        r = rows(Path(self.tmp.name) / "o2" / "trials.csv")[0]
        self.assertEqual(("wild", "3", "2", "9", "failed", ""), (r["arm"], r["penalty_point"], r["wording"], r["seed"], r["status"], r["thinking"]))

    def test_corrupt_trial_is_kept_with_status_and_does_not_abort(self):
        d = Path(self.tmp.name) / "c"
        shutil.copytree(TRIALS, d)
        bad = d / "bad__p1__w0__s3"
        bad.mkdir()
        (bad / "events.jsonl").write_text('{"kind":"talk","round":1}' + chr(10) + '{"kind":"qu', encoding="utf-8")
        collect.collect(d, Path(self.tmp.name) / "oc")
        t = {r["trial_id"]: r for r in rows(Path(self.tmp.name) / "oc" / "trials.csv")}
        self.assertEqual(3, len(t))
        self.assertEqual(("corrupt", "bad", ""), (t["bad__p1__w0__s3"]["status"], t["bad__p1__w0__s3"]["arm"], t["bad__p1__w0__s3"]["rounds"]))
        self.assertEqual("done", t["chat__p1__w0__s2"]["status"])

    def test_duplicate_trial_names_raise(self):
        d = Path(self.tmp.name) / "dup"
        shutil.copytree(TRIALS / "tacit__p1__w0__s1", d / "x" / "tacit__p1__w0__s1")
        shutil.copytree(TRIALS / "tacit__p1__w0__s1", d / "y" / "tacit__p1__w0__s1")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            collect.collect(d, Path(self.tmp.name) / "od")

    def test_round_values_are_rounded(self):
        d = Path(self.tmp.name) / "r" / "a__p1__w0__s1"
        d.mkdir(parents=True)
        (d / "events.jsonl").write_text('{"kind":"quote","round":1,"seat":"a0","quote":2.0}' + chr(10)
                                        + '{"kind":"market","round":1,"market_price":2.0,"profits":{"a0":0.30000000000000004}}' + chr(10), encoding="utf-8")
        collect.collect(d.parent, Path(self.tmp.name) / "or")
        self.assertEqual("0.3", rows(Path(self.tmp.name) / "or" / "rounds.csv")[0]["profit"])

    def test_questions_table_name_mode_answer_and_draw_key_fallback(self):
        q = rows(self.out / "questions.csv")
        self.assertEqual(2, len(q))
        self.assertEqual(("confidant", "fed", "7", "a0"), (q[0]["question"], q[0]["mode"], q[0]["words"], q[0]["seat"]))
        self.assertEqual(("public", "post", "REFUSED", "MODEL_TEXT"), (q[1]["question"], q[1]["mode"], q[1]["parse_status"], q[1]["refusal_kind"]))
        self.assertEqual("I can't answer that.", q[1]["answer"])

    def test_refusal_table_every_arm_mode_kind_with_rates_and_patterns(self):
        t = {(r["arm"], r["thinking"], r["kind"]): r for r in rows(self.out / "refusals.csv")}
        self.assertEqual(6, len(t))  # 2 arms x 3 kinds, zeros included
        c = t[("chat", "on", "talk")]
        self.assertEqual(("3", "1", "0.333333", '{"MODEL_TEXT":1}', '{"i can\'t":1}'), (c["calls"], c["refusals"], c["refusal_rate"], c["by_refusal_kind"], c["patterns"]))
        q = t[("chat", "on", "quote")]  # its only failed quote is UNPARSEABLE: a parse failure, not a refusal (Q3)
        self.assertEqual(("0", "1", "0", "", ""), (q["refusals"], q["parse_failures"], q["truncations"], q["by_refusal_kind"], q["patterns"]))
        self.assertEqual(("2", "1", "0.5"), tuple(t[("chat", "on", "question")][k] for k in ("calls", "refusals", "refusal_rate")))
        z = t[("tacit", "off", "talk")]
        self.assertEqual(("0", "0", ""), (z["calls"], z["refusals"], z["refusal_rate"]))  # no calls: rate empty, row kept
        self.assertEqual('{"i won\'t":1}', t[("tacit", "off", "quote")]["patterns"])

    def _copy(self, name):
        d = Path(self.tmp.name) / name
        shutil.copytree(TRIALS, d)
        return d

    def _clone(self, d, new, **params):
        shutil.copytree(d / "chat__p1__w0__s2", d / new)
        f = d / new / "params.json"
        j = json.loads(f.read_text(encoding="utf-8"))
        j.update(params)
        f.write_text(json.dumps(j), encoding="utf-8")

    def test_mixed_fingerprint_or_commit_in_an_arm_is_refused_and_nothing_written(self):
        for key in ("prompt_fingerprint", "code_commit"):
            d = self._copy("m_" + key)
            self._clone(d, "chat__p1__w0__s3", **{key: "other"})
            out = Path(self.tmp.name) / ("o_" + key)
            with self.assertRaisesRegex(collect.MixedFingerprintError, key):
                collect.collect(d, out)
            self.assertFalse(out.exists())
            self.assertEqual(1, collect.main(["collect.py", str(d), str(out)]))

    def test_missing_fingerprint_counts_as_different_but_other_arms_may_differ(self):
        d = self._copy("m3")
        self._clone(d, "chat__p1__w0__s3", prompt_fingerprint="")
        with self.assertRaises(collect.MixedFingerprintError):
            collect.collect(d, Path(self.tmp.name) / "o4")
        ok = self._copy("m4")  # tacit and chat already differ in fingerprint: separate arms, fine
        self._clone(ok, "chat__p1__w0__s3")
        collect.collect(ok, Path(self.tmp.name) / "o5")
        t = rows(Path(self.tmp.name) / "o5" / "trials.csv")
        self.assertEqual({"fp-chat", "fp-tacit"}, {r["prompt_fingerprint"] for r in t})

    def test_same_fingerprint_across_thinking_modes_is_one_arm(self):
        d = self._copy("m5")
        self._clone(d, "chat__p1__w0__s3", thinking="off")
        collect.collect(d, Path(self.tmp.name) / "o6")
        t = rows(Path(self.tmp.name) / "o6" / "refusals.csv")
        self.assertEqual({("chat", "on"), ("chat", "off"), ("tacit", "off")}, {(r["arm"], r["thinking"]) for r in t})

    def test_refused_outcome_without_kind_counts_and_patterns_with_separators_stay_parseable(self):
        d = Path(self.tmp.name) / "q" / "a__p1__w0__s1"
        d.mkdir(parents=True)
        (d / "params.json").write_text(json.dumps({"thinking": "on"}), encoding="utf-8")
        ev = [{"kind": "talk", "round": 1, "seat": "a0", "outcome": "REFUSED", "refusal_pattern": "sorry: i can't; no"},
              {"kind": "talk", "round": 1, "seat": "a1", "outcome": "OK"}]
        (d / "events.jsonl").write_text(chr(10).join(json.dumps(e) for e in ev) + chr(10), encoding="utf-8")
        collect.collect(d.parent, Path(self.tmp.name) / "oq")
        r = [x for x in rows(Path(self.tmp.name) / "oq" / "refusals.csv") if x["kind"] == "talk"][0]
        self.assertEqual(("2", "1"), (r["calls"], r["refusals"]))
        self.assertEqual({"(none)": 1}, json.loads(r["by_refusal_kind"]))
        self.assertEqual({"sorry: i can't; no": 1}, json.loads(r["patterns"]))

    def test_empty_root_gives_header_only_tables(self):
        e = Path(self.tmp.name) / "empty"
        e.mkdir()
        collect.collect(e, Path(self.tmp.name) / "o3")
        for n in NAMES:
            self.assertEqual(1, len((Path(self.tmp.name) / "o3" / n).read_text(encoding="utf-8").splitlines()))

    def test_reasoning_column_in_rounds_messages_questions_on_one_line(self):
        msg = {(r["round"], r["turn"]): r["reasoning"] for r in rows(self.out / "messages.csv")}
        self.assertEqual("Propose 2.40 to test willing partner.", msg[("1", "0")])   # the fixture text holds a newline
        self.assertEqual("", msg[("1", "1")])
        q = {(r["round"], r["seat"]): r["reasoning"] for r in rows(self.out / "questions.csv")}
        self.assertEqual({("1", "a0"): "They asked why; be honest.", ("2", "a1"): ""}, q)
        rd = {(r["trial_id"], r["round"], r["seat"]): r["reasoning"] for r in rows(self.out / "rounds.csv")}
        self.assertEqual("Hold the agreed price.", rd[("chat__p1__w0__s2", "1", "a0")])
        self.assertEqual({v for k, v in rd.items() if k != ("chat__p1__w0__s2", "1", "a0")}, {""})
        for n in ("rounds", "messages", "questions"):
            self.assertEqual("reasoning", rows(self.out / (n + ".csv"))[0] and list(rows(self.out / (n + ".csv"))[0])[-1])

    def test_prices_carried_from_params_and_blank_when_absent(self):
        t = {r["trial_id"]: r for r in rows(self.out / "trials.csv")}
        self.assertEqual(("2.0", "2.4"), (t["tacit__p1__w0__s1"]["competitive_price"], t["tacit__p1__w0__s1"]["collusive_price"]))
        d = Path(self.tmp.name) / "np" / "a__p1__w0__s1"
        d.mkdir(parents=True)
        (d / "params.json").write_text(json.dumps({"thinking": "on", "competitive_price": "x", "collusive_price": float("nan")}), encoding="utf-8")
        (d / "events.jsonl").write_text(json.dumps({"kind": "market", "round": 1, "prices": {}}) + chr(10), encoding="utf-8")
        collect.collect(d.parent, Path(self.tmp.name) / "onp")
        (r,) = rows(Path(self.tmp.name) / "onp" / "trials.csv")
        self.assertEqual(("", ""), (r["competitive_price"], r["collusive_price"]))   # non-numbers are not carried

    def test_collected_tables_feed_analysis_without_price_arguments(self):
        import analysis_m
        import analysis_r
        o = Path(self.tmp.name) / "an"
        self.assertEqual(0, analysis_m.main([str(self.out), str(o), "--window-end", "2", "--boot", "20"]))
        o2 = Path(self.tmp.name) / "an2"
        self.assertEqual(1, analysis_r.main([str(self.out), str(o2), "--window-end", "2", "--boot", "20"]))  # no Track R arms here
        filled = [r for r in rows(o2 / "thinks_says_does.csv") if r["reasoning"]]
        self.assertTrue(any("Hold the agreed price." in r["reasoning"] for r in filled))

    def test_cli(self):
        o = Path(self.tmp.name) / "cli"
        self.assertEqual(0, collect.main(["collect.py", str(TRIALS), str(o)]))
        self.assertTrue((o / "trials.csv").exists())
        self.assertEqual(2, collect.main(["collect.py"]))


class ModelColumn(unittest.TestCase):
    """trials.csv `model`: params.json model/model_name (the C4.3 writer sets model), else the LLM seats'
    model.served_name, else grid_row.json model_profile (corrupt or param-less trials)."""
    def meta(self, params, grid_row=None):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "a__p3__w0__s1__t0"
            t.mkdir()
            if grid_row is not None:
                (t / "grid_row.json").write_text(json.dumps(grid_row), encoding="utf-8")
            return collect.trial_meta(t, params)["model"]

    def test_sources_in_order(self):
        seats = [{"seat": "llm1", "kind": "llm", "model": {"served_name": "Qwen/Qwen3-14B", "model_id": "Qwen/Qwen3-14B"}},
                 {"seat": "llm2", "kind": "llm", "model": {"served_name": "Qwen/Qwen3-14B"}},
                 {"seat": "s3", "kind": "scripted", "rule": "defect_once"}]
        self.assertEqual(self.meta({"model": "M", "seats": seats}), "M")
        self.assertEqual(self.meta({"model_name": "N"}), "N")
        self.assertEqual(self.meta({"seats": seats}, {"model_profile": "qwen3_14b"}), "Qwen/Qwen3-14B")
        mixed = seats[:1] + [{"seat": "llm2", "kind": "llm", "model": {"served_name": "Qwen--Qwen3-32B-FP8--%s+vllm0.9.2" % ("a" * 40)}}]
        self.assertEqual(self.meta({"seats": mixed}), "Qwen--Qwen3-32B-FP8--%s+vllm0.9.2 | Qwen/Qwen3-14B" % ("a" * 40))
        self.assertEqual(self.meta({"model": "served-1", "seats": mixed}, {"model_profile": "qwen3_14b"}), "served-1")  # as C4.3 writes
        self.assertEqual(self.meta({"seats": seats[2:]}, {"model_profile": "qwen3_32b_fp8"}), "qwen3_32b_fp8")
        self.assertEqual(self.meta({}, {"model_profile": "qwen3_14b"}), "qwen3_14b")
        self.assertEqual(self.meta({}), "")
        self.assertEqual(self.meta({"seats": "junk"}, ["not", "a", "dict"]), "")

    def test_unreadable_grid_row_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "a__p3__w0__s1__t0"
            t.mkdir()
            (t / "grid_row.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(collect.trial_meta(t, {})["model"], "")


class TalkDoneCountTest(unittest.TestCase):
    def test_done_turns_are_rows_but_not_messages(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "chat__p1__w0__s9"
            d.mkdir()
            ev = [{"seq": 1, "kind": "talk", "round": 1, "turn": 0, "seat": "a", "outcome": "OK",
                   "parsed": {"message": "Hold 2.40?", "done": False}},
                  {"seq": 2, "kind": "talk", "round": 1, "turn": 1, "seat": "b", "outcome": "OK",
                   "parsed": {"message": "", "done": True}},
                  {"seq": 3, "kind": "talk", "round": 1, "turn": 2, "seat": "a", "outcome": "REFUSED",
                   "refusal_kind": "MODEL_TEXT", "refusal_pattern": "i can't", "parsed": {"message": "", "done": True}}]
            (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\n", encoding="utf-8")
            row, _, messages, _, calls, refusals, _ = collect.trial_rows(d)
            self.assertEqual(1, row["messages"])
            self.assertEqual(3, len(messages))
            self.assertEqual(["Hold 2.40?", "", ""], [m["text"] for m in messages])
            self.assertEqual(3, calls["talk"])
            self.assertEqual([("talk", "MODEL_TEXT", "i can't")], refusals)


if __name__ == "__main__":
    unittest.main()
