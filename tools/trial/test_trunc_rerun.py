"""Unit N3: truncation reruns (trunc_rerun.py scan/grid/supersede) and collect.py / pick_cell.py honouring superseded.csv.
Synthetic trial roots only; no model or Modal call. Run: python -X utf8 -m unittest tools/trial/test_trunc_rerun.py"""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import pick_cell  # noqa: E402
import trunc_rerun as tr  # noqa: E402

BASE_ROW = {"trial_id": "", "arm": "headline-chat", "penalty_point": "3", "scenario_file": "p3.yaml", "communication": "private",
            "firms": "2", "seats": "llm,llm", "condition_texts": "all:neutral", "wording": "2", "seed": "55", "thinking": "1",
            "model_profile": "qwen3_32b_fp8", "temperature": "0.6", "top_p": "0.95", "top_k": "20", "max_tokens_talk": "8192",
            "max_tokens_quote": "8192", "max_tokens_question": "4096", "timeout_sec": "300", "wave": "2", "introspection": "",
            "options": '{"a":1}', "theory_theta_star": "0.5", "slice": "2", "pilot": "", "context_window": "16384"}


def make_trial(root, tid, arm="headline-chat", thinking=1, trunc=(), done=True, seed=55, source="events", level=2.0, row_file=True):
    """A trial dir <root>/<arm>/<tid> with 3 rounds; trunc lists call types cut at the token limit (finish_reason length)."""
    d = Path(root) / arm / tid
    d.mkdir(parents=True)
    row = dict(BASE_ROW, trial_id=tid, arm=arm, thinking=str(thinking), seed=str(seed))
    if row_file:
        (d / "grid_row.json").write_text(json.dumps(row, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    (d / "params.json").write_text(json.dumps({"arm": arm, "thinking": bool(thinking), "wording": 2, "seed": seed, "penalty_point": 3,
                                              "competitive_price": 1.0, "collusive_price": 3.0, "prompt_fingerprint": "f", "code_commit": "c"}),
                                  encoding="utf-8")
    evs = []
    for r in (1, 2, 3):
        for seat in ("llm1", "llm2"):
            evs.append({"kind": "quote", "round": r, "seat": seat, "quote": level, "outcome": "OK",
                        "finish_reason": "length" if (r == 1 and seat == "llm1" and "quote" in trunc and source == "events") else "stop"})
        if r == 1 and "talk" in trunc:
            evs.append({"kind": "talk", "round": 1, "seat": "llm1", "turn": 0, "outcome": "OK",
                        "finish_reason": "length" if source == "events" else "stop", "parsed": {"message": "hi", "done": False}})
        if r == 2 and "question" in trunc:
            evs.append({"kind": "question", "round": 2, "seat": "llm1", "name": "confidant", "mode": "fed", "outcome": "OK",
                        "finish_reason": "length" if source == "events" else "stop", "reply": "x"})
        evs.append({"kind": "market", "round": r, "prices": {"llm1": level, "llm2": level}, "profits": {"llm1": 1, "llm2": 1},
                    "winner": None, "market_price": level})
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in evs), encoding="utf-8")
    if source == "calls":   # calls.jsonl rows carry the finish_reason; events.jsonl says stop everywhere
        kinds = {"quote": "game", "talk": "talk", "question": "question"}
        (d / "calls.jsonl").write_text("".join(json.dumps({"kind": kinds[t], "runKey": "x|s1", "index": 1, "finish_reason": "length"}) + "\n" for t in trunc)
                                       + json.dumps({"kind": "game", "runKey": "x|s1", "index": 2, "finish_reason": "stop"}) + "\n", encoding="utf-8")
    if done:
        (d / "DONE").write_text("attempts 1\n", encoding="utf-8")
    return d


def run(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn(*args)
    return rc, out.getvalue(), err.getvalue()


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "trials"
        self.addCleanup(self.tmp.cleanup)

    def test_clean_root_selects_nothing(self):
        make_trial(self.root, "headline-chat__p3__w2__s55__t1")
        rc, out, _ = run(tr.main, ["scan", str(self.root)])
        self.assertEqual(0, rc)
        self.assertIn("0 affected", out)
        self.assertEqual([], tr.affected(self.root))

    def test_thinking_off_truncated_game_not_selected(self):
        make_trial(self.root, "headline-chat__p3__w2__s55__t0", thinking=0, trunc=("quote",))
        self.assertEqual([], tr.affected(self.root))
        rc, out, err = run(tr.main, ["scan", str(self.root)])
        self.assertIn("thinking-off", err)
        self.assertIn("0 affected", out)

    def test_quote_talk_and_question_truncation_selected_with_counts(self):
        make_trial(self.root, "a__p3__w2__s1__t1", arm="a", trunc=("quote",), seed=1)
        make_trial(self.root, "b__p3__w2__s2__t1", arm="b", trunc=("talk",), seed=2)
        make_trial(self.root, "c__p3__w2__s3__t1", arm="c", trunc=("question",), seed=3)
        make_trial(self.root, "d__p3__w2__s4__t1", arm="d", trunc=("quote", "talk", "question"), seed=4)
        got = {r["trial_id"]: r["counts"] for r in tr.affected(self.root)}
        self.assertEqual({"a__p3__w2__s1__t1": {"quote": 1}, "b__p3__w2__s2__t1": {"talk": 1}, "c__p3__w2__s3__t1": {"question": 1},
                          "d__p3__w2__s4__t1": {"quote": 1, "talk": 1, "question": 1}}, got)
        rc, out, _ = run(tr.main, ["scan", str(self.root)])
        self.assertIn("4 affected", out)
        self.assertIn("quote 2, talk 2, question 2", out)

    def test_calls_jsonl_finish_reason_is_read(self):
        make_trial(self.root, "a__p3__w2__s1__t1", arm="a", trunc=("talk",), seed=1, source="calls")
        got = tr.affected(self.root)
        self.assertEqual([{"talk": 1}], [r["counts"] for r in got])
        self.assertEqual("calls", got[0]["source"])

    def test_thinking_from_id_suffix_when_row_and_params_silent(self):
        d = make_trial(self.root, "a__p3__w2__s1__t1", arm="a", trunc=("quote",), seed=1, row_file=False)
        (d / "params.json").write_text("{}", encoding="utf-8")
        self.assertTrue(tr.thinking_on(d))

    def test_existing_rerun_is_reported_but_marked(self):
        make_trial(self.root, "a__p3__w2__s1__t1__x32k", arm="a", trunc=("quote",), seed=1)
        rc, out, _ = run(tr.main, ["scan", str(self.root)])
        self.assertIn("already a rerun", out)

    def test_attempt_event_uses_of_and_post_question_counts(self):
        d = make_trial(self.root, "a__p3__w2__s1__t1", arm="a", seed=1)
        with open(d / "events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "attempt", "round": 1, "seat": "llm1", "of": "talk", "attempt": 0, "finish_reason": "length"}) + chr(10))
            f.write(json.dumps({"kind": "question", "round": 3, "seat": "llm1", "name": "q", "mode": "post", "finish_reason": "length"}) + chr(10))
            f.write(json.dumps({"kind": "quote", "round": 3, "seat": "llm1", "context_clamp_skipped": True, "finish_reason": "stop"}) + chr(10))
        self.assertEqual([{"talk": 1, "question": 1}], [r["counts"] for r in tr.affected(self.root)])


class GridTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "trials"
        self.addCleanup(self.tmp.cleanup)

    def test_row_copy_is_exact_except_the_five_changes(self):
        make_trial(self.root, "headline-chat__p3__w2__s55__t1", trunc=("talk",))
        make_trial(self.root, "headline-chat__p3__w2__s56__t1", trunc=(), seed=56)
        out = Path(self.tmp.name) / "g" / "rerun.csv"
        rc, _, _ = run(tr.main, ["grid", str(self.root), "--out", str(out)])
        self.assertEqual(0, rc)
        got = rows(out)
        self.assertEqual(1, len(got))
        want = dict(BASE_ROW, trial_id="headline-chat__p3__w2__s55__t1__x32k", model_profile="qwen3_32b_fp8_32k", context_window="32768",
                    max_tokens_quote="28672", max_tokens_talk="28672", max_tokens_question="16384")
        self.assertEqual(want, got[0])
        with open(out, encoding="utf-8", newline="") as f:
            self.assertEqual(list(BASE_ROW), next(csv.reader(f)))

    def test_no_chaining(self):
        make_trial(self.root, "a__p3__w2__s1__t1__x32k", arm="a", trunc=("quote",), seed=1)
        out = Path(self.tmp.name) / "rerun.csv"
        rc, _, err = run(tr.main, ["grid", str(self.root), "--out", str(out)])
        self.assertEqual(0, rc)
        self.assertIn("no chaining", err)
        self.assertEqual([], rows(out))

    def test_source_grid_used_when_no_grid_row_json(self):
        make_trial(self.root, "a__p3__w2__s1__t1", arm="a", trunc=("quote",), seed=1, row_file=False)
        src = Path(self.tmp.name) / "grid.csv"
        with open(src, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list(BASE_ROW), lineterminator="\n")
            w.writeheader()
            w.writerow(dict(BASE_ROW, trial_id="a__p3__w2__s1__t1", arm="a", seed="1"))
        out = Path(self.tmp.name) / "rerun.csv"
        self.assertEqual(1, run(tr.main, ["grid", str(self.root), "--out", str(out)])[0])   # no row: error, exit 1
        rc, _, _ = run(tr.main, ["grid", str(self.root), "--out", str(out), "--source-grid", str(src)])
        self.assertEqual(0, rc)
        self.assertEqual("a__p3__w2__s1__t1__x32k", rows(out)[0]["trial_id"])

    def test_timeout_warning_and_override(self):
        make_trial(self.root, "a__p3__w2__s1__t1", arm="a", trunc=("quote",), seed=1)
        out = Path(self.tmp.name) / "rerun.csv"
        _, _, err = run(tr.main, ["grid", str(self.root), "--out", str(out)])
        self.assertIn("WARNING", err)
        self.assertIn("lead must decide", err)
        self.assertEqual("300", rows(out)[0]["timeout_sec"])   # default: unchanged copy
        _, _, err = run(tr.main, ["grid", str(self.root), "--out", str(out), "--timeout-sec", "900"])
        self.assertNotIn("WARNING", err)
        self.assertEqual("900", rows(out)[0]["timeout_sec"])

    def test_non_32b_profile_skipped_with_warning_and_flagged_by_scan(self):
        d = make_trial(self.root, "s__p3__w2__s1__t1", arm="s", trunc=("quote",), seed=1)
        row = json.loads((d / "grid_row.json").read_text(encoding="utf-8"))
        row["model_profile"] = "qwen3_14b"
        (d / "grid_row.json").write_text(json.dumps(row), encoding="utf-8")
        out = Path(self.tmp.name) / "rerun.csv"
        rc, _, err = run(tr.main, ["grid", str(self.root), "--out", str(out)])
        self.assertEqual(0, rc)
        self.assertIn("not a 32B profile", err)
        self.assertEqual([], rows(out))
        self.assertIn("not a 32B profile", run(tr.main, ["scan", str(self.root)])[1])


class SupersedeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.rr = Path(self.tmp.name) / "trials", Path(self.tmp.name) / "rerun"
        self.addCleanup(self.tmp.cleanup)
        self.o1, self.o2 = "a__p3__w2__s1__t1", "b__p3__w2__s2__t1"
        make_trial(self.root, self.o1, arm="a", trunc=("quote", "talk"), seed=1)
        make_trial(self.root, self.o2, arm="b", trunc=("talk",), seed=2)

    def test_only_completed_reruns_listed_missing_on_stderr_and_idempotent(self):
        make_trial(self.rr, self.o1 + tr.SUFFIX, arm="a", seed=1)
        make_trial(self.rr, self.o2 + tr.SUFFIX, arm="b", seed=2, done=False)
        rc, _, err = run(tr.main, ["supersede", str(self.root), str(self.rr)])
        self.assertEqual(0, rc)
        self.assertIn(self.o2 + tr.SUFFIX, err)
        got = rows(self.root / "superseded.csv")
        self.assertEqual([(self.o1, self.o1 + tr.SUFFIX)], [(r["original_id"], r["rerun_id"]) for r in got])
        self.assertIn("quote 1", got[0]["reason"])
        first = (self.root / "superseded.csv").read_bytes()
        self.assertTrue(first.startswith(b"original_id,rerun_id,reason\n"))
        run(tr.main, ["supersede", str(self.root), str(self.rr)])
        self.assertEqual(first, (self.root / "superseded.csv").read_bytes())
        (self.rr / "b" / (self.o2 + tr.SUFFIX) / "DONE").write_text("x", encoding="utf-8")   # the missing one finishes: added, first kept
        run(tr.main, ["supersede", str(self.root), str(self.rr)])
        self.assertEqual([self.o1, self.o2], [r["original_id"] for r in rows(self.root / "superseded.csv")])

    def test_no_reruns_at_all(self):
        self.rr.mkdir()
        rc, _, err = run(tr.main, ["supersede", str(self.root), str(self.rr)])
        self.assertEqual(0, rc)
        self.assertIn("missing reruns", err)
        self.assertEqual([], rows(self.root / "superseded.csv"))

    def test_rerun_also_truncated_is_noted_in_reason(self):
        make_trial(self.rr, self.o1 + tr.SUFFIX, arm="a", seed=1, trunc=("talk",))
        run(tr.main, ["supersede", str(self.root), str(self.rr)])
        reason = rows(self.root / "superseded.csv")[0]["reason"]
        self.assertIn("rerun also truncated (talk 1)", reason)
        self.assertEqual(tr.SUP_COLS, list(rows(self.root / "superseded.csv")[0]))


class CollectTest(unittest.TestCase):
    """collect.py: superseded originals out, reruns in under the original's cell, --include-superseded the other way round."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.root, self.rr = self.t / "trials", self.t / "rerun"
        self.addCleanup(self.tmp.cleanup)
        self.o = "headline-chat__p3__w2__s55__t1"
        make_trial(self.root, self.o, trunc=("quote",), level=1.5)
        make_trial(self.root, "headline-chat__p3__w2__s56__t1", seed=56, level=2.5)
        make_trial(self.rr, self.o + tr.SUFFIX, level=2.0)
        self.orig_ids = ["headline-chat__p3__w2__s55__t1", "headline-chat__p3__w2__s56__t1"]
        self.rerun_ids = ["headline-chat__p3__w2__s55__t1__x32k", "headline-chat__p3__w2__s56__t1"]

    def collect(self, name, **kw):
        out = self.t / name
        with contextlib.redirect_stderr(io.StringIO()):
            collect.collect(self.root, out, **kw)
        return out

    def supersede(self):
        run(tr.main, ["supersede", str(self.root), str(self.rr)])

    def ids(self, out):
        return sorted(r["trial_id"] for r in rows(out / "trials.csv"))

    def test_without_superseded_csv_nothing_changes(self):
        out = self.collect("plain")
        self.assertEqual(self.orig_ids, self.ids(out))
        out2 = self.collect("plain_flags", include_superseded=True)   # the flag alone changes nothing either
        for n in ("trials.csv", "rounds.csv", "refusals.csv"):
            self.assertEqual((out / n).read_bytes(), (out2 / n).read_bytes())

    def test_superseded_original_excluded_rerun_included_under_the_originals_cell(self):
        self.supersede()
        out = self.collect("primary", rerun_roots=[self.rr])
        self.assertEqual(self.rerun_ids, self.ids(out))
        re_ = [r for r in rows(out / "trials.csv") if r["trial_id"].endswith(tr.SUFFIX)][0]
        self.assertEqual(("headline-chat", "3", "2", "55", "on"), (re_["arm"], re_["penalty_point"], re_["wording"], re_["seed"], re_["thinking"]))
        self.assertEqual("0.5", re_["collusion_level"])   # the rerun's own play (price 2.0), not the truncated original's (1.5 -> 0.25)
        self.assertEqual({r["trial_id"] for r in rows(out / "rounds.csv")}, set(self.ids(out)))

    def test_name_fallback_strips_the_suffix(self):
        d = make_trial(self.t / "n", "headline-chat__p3__w2__s9__t1" + tr.SUFFIX, seed=9)
        (d / "params.json").write_text("{}", encoding="utf-8")
        m = collect.trial_meta(d, {})
        self.assertEqual(("headline-chat", "3", "2", "9", "on"), (m["arm"], m["penalty_point"], m["wording"], m["seed"], m["thinking"]))

    def test_include_superseded_sensitivity_counts_each_game_once(self):
        self.supersede()
        out = self.collect("sens", rerun_roots=[self.rr], include_superseded=True)
        self.assertEqual(self.orig_ids, self.ids(out))
        ts = rows(out / "trials.csv")
        self.assertEqual(len(ts), len({(r["arm"], r["wording"], r["seed"]) for r in ts}))

    def test_rerun_found_when_nested_in_the_root(self):
        self.supersede()
        self.rr.rename(self.root / "rerun_x32k")
        out = self.collect("nested")
        self.assertEqual(self.rerun_ids, self.ids(out))

    def test_original_stays_when_its_rerun_is_not_collected_or_not_done(self):
        self.supersede()
        out = self.collect("norerun")   # rerun root not given
        self.assertEqual(self.orig_ids, self.ids(out))
        (self.rr / "headline-chat" / (self.o + tr.SUFFIX) / "DONE").unlink()
        out = self.collect("notdone", rerun_roots=[self.rr])
        self.assertEqual(self.orig_ids, self.ids(out))

    def test_unlisted_rerun_is_left_out(self):
        self.supersede()
        make_trial(self.rr, "headline-chat__p3__w2__s56__t1" + tr.SUFFIX, seed=56)
        out = self.collect("unlisted", rerun_roots=[self.rr])
        self.assertEqual(self.rerun_ids, self.ids(out))

    def test_cli_flags(self):
        self.supersede()
        out, out2 = self.t / "cli", self.t / "cli2"
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, collect.main(["collect.py", str(self.root), str(out), "--rerun-root", str(self.rr)]))
            self.assertEqual(2, collect.main(["collect.py", str(self.root)]))
            self.assertEqual(0, collect.main(["collect.py", str(self.root), str(out2), "--rerun-root", str(self.rr), "--include-superseded"]))
        self.assertEqual(self.rerun_ids, self.ids(out))
        self.assertEqual(self.orig_ids, self.ids(out2))

    def test_analysis_tables_hold_one_game_per_cell(self):
        import analysis_m as am
        self.supersede()
        out = self.collect("pair", rerun_roots=[self.rr])
        keys = [(t["arm"], t["wording"], t["seed"]) for t in rows(out / "trials.csv")]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(hasattr(am, "main"))

    def test_stray_rerun_dir_warned_and_skipped_even_without_superseded_csv(self):
        make_trial(self.root, "headline-chat__p3__w2__s57__t1" + tr.SUFFIX, seed=57)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            collect.collect(self.root, self.t / "stray")
        self.assertIn("not listed", err.getvalue())
        self.assertEqual(self.orig_ids, self.ids(self.t / "stray"))

    def test_duplicate_names_give_a_clean_exit_2(self):
        make_trial(self.rr, self.orig_ids[1], seed=56, arm="headline-chat")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = collect.main(["collect.py", str(self.root), str(self.t / "dup"), "--rerun-root", str(self.rr)])
        self.assertEqual(2, rc)
        self.assertIn("duplicate trial directory names", err.getvalue())


class PickCellTest(unittest.TestCase):
    def test_superseded_candidate_read_from_its_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            root, rr = t / "trials", t / "rerun"
            a, b = "headline-chat__p3__w2__s1__t1", "headline-chat__p3__w2__s2__t1"
            make_trial(root, a, seed=1, trunc=("quote",), level=3.0)    # truncated original: level 1.0 (the collusive price)
            make_trial(root, b, seed=2, level=2.0)                      # level 0.5
            make_trial(rr, a + tr.SUFFIX, seed=1, level=1.0)            # rerun: level 0.0
            run(tr.main, ["supersede", str(root), str(rr)])
            grid = [dict(BASE_ROW, trial_id=a, seed="1", slice="1"), dict(BASE_ROW, trial_id=b, seed="2", slice="1", penalty_point="4")]
            cell, _ = pick_cell.pick(grid, root, rerun_roots=[rr])
            self.assertEqual(b, cell["source_trial"])
            cell, _ = pick_cell.pick(grid, root, rerun_roots=[rr], include_superseded=True)
            self.assertEqual(a, cell["source_trial"])
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                pick_cell.pick(grid, root)   # no --rerun-root: falls back to the truncated original, loudly
            self.assertIn("using the truncated original", err.getvalue())


if __name__ == "__main__":
    unittest.main()
