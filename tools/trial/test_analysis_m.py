"""Tests for analysis_m.py (C10.1) against mock tables of known ground truth.
Run: python -X utf8 -m unittest tools/trial/test_analysis_m.py"""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import mock_tables as mt  # noqa: E402


def games_for(specs, start=1, end=10):
    with tempfile.TemporaryDirectory() as d:
        mt.write_tables(d, specs)
        games = am.build_games(am.load_tables(d), mt.COMP, mt.COLL)
    return games, am.game_measures(games, start, end)


def one(rows, tid_part, basis="assigned", ref="with"):
    (r,) = [r for r in rows if tid_part in r["trial_id"] and r["basis"] == basis and r["refusals"] == ref]
    return r


class MeasuresTruth(unittest.TestCase):
    def test_collusive_game(self):
        _, rows = games_for([mt.spec(arm="c", kind="collude")])
        r = one(rows, "c__")
        self.assertEqual((r["level"], r["time_to_high"], r["high_duration"], r["undercuts"], r["punishments"], r["war_length"]),
                         (1.0, 1, 10, 0, 0, 0))

    def test_competitive_and_mid_games(self):
        _, rows = games_for([mt.spec(arm="x", kind="compete"), mt.spec(arm="y", kind="mid")])
        r = one(rows, "x__")
        self.assertEqual((r["level"], r["time_to_high"], r["high_duration"]), (0.0, None, 0))
        self.assertAlmostEqual(one(rows, "y__")["level"], 0.5)

    def test_defection_and_punishment(self):
        _, rows = games_for([mt.spec(kind="collude", defect_at=4, war=2)])
        r = one(rows, "chat")
        self.assertAlmostEqual(r["level"], 0.75)  # rounds 1-3 and 7-10 at 1, round 4 at 0.5, rounds 5-6 at 0
        self.assertEqual((r["time_to_high"], r["high_duration"], r["undercuts"], r["punishments"], r["war_length"]),
                         (1, 4, 1, 1, 3))

    def test_refusal_rounds_with_and_without(self):
        _, rows = games_for([mt.spec(kind="collude", refuse_rounds=(3,), talk_refuse_rounds=(7,))])
        w, wo = one(rows, "chat"), one(rows, "chat", ref="without")
        self.assertAlmostEqual(w["level"], 0.9)  # the refused quote plays competitive, so round 3 is at 0
        self.assertEqual(wo["level"], 1.0)
        self.assertEqual((w["refusal_rounds"], w["rounds"], wo["rounds"]), (2, 10, 8))  # quote round 3 and talk round 7
        # the imputed competitive quote is not a chosen undercut; a run is not broken by a left-out round
        self.assertEqual((w["undercuts"], w["punishments"], wo["undercuts"], wo["punishments"]), (0, 0, 0, 0))
        self.assertEqual((w["time_to_high"], w["high_duration"], wo["high_duration"]), (1, 7, 8))  # runs: 1-2, then 4-10; 3 left out

    def test_events_after_a_left_out_round_are_still_seen(self):
        _, rows = games_for([mt.spec(kind="collude", defect_at=4, war=2, refuse_rounds=(3,))])
        for ref in ("with", "without"):
            r = one(rows, "chat", ref=ref)
            self.assertEqual((r["undercuts"], r["punishments"]), (1, 1), ref)  # undercut in round 4, right after the refusal
            self.assertEqual(r["undercuts_by_seat"], '{"a1":1}')
        self.assertEqual(one(rows, "chat", ref="without")["high_duration"], 4)  # rounds 7-10; 1-2 is shorter

    def test_phantom_and_post_game_refusals_do_not_change_rounds(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, [mt.spec(rounds=3)])
            q = Path(d) / "questions.csv"
            q.write_text("trial_id,round,seat,question,mode,words,answer,truncated,parse_status,refusal_kind\n"
                         "chat__p1__w0__s1,2,a0,confidant,post,1,no,0,REFUSED,MODEL_TEXT\n"
                         "chat__p1__w0__s1,9,a0,confidant,fed,1,no,0,REFUSED,MODEL_TEXT\n", encoding="utf-8", newline="")
            g = am.build_games(am.load_tables(d), 2.0, 4.0)["chat__p1__w0__s1"]
            self.assertEqual(sorted(g["rounds"]), [1, 2, 3])  # no phantom round 9
            self.assertEqual([r for r, v in g["rounds"].items() if v["refused"]], [])  # post mode and unplayed round ignored
            rows = am.game_measures({"x": g}, 1, 5)
            self.assertEqual([r["basis"] for r in rows], ["assigned", "assigned"])  # round 4-5 absent: window incomplete

    def test_window_starting_later_counts_time_from_its_start(self):
        _, rows = games_for([mt.spec(kind="collude", defect_at=4, war=2)], 4, 10)
        r = one(rows, "chat", "window")
        self.assertEqual(r["time_to_high"], 4)  # round 7 is the 4th round of the window 4..10
        self.assertEqual((r["undercuts"], r["punishments"]), (1, 0))  # the round-4 undercut is outside view, so the round-5 reply reads as an undercut

    def test_threshold_boundary_is_inclusive(self):
        games, _ = games_for([mt.spec(kind="mid")])
        self.assertEqual(am.measures(games["chat__p1__w0__s1"]["rounds"], threshold=0.5)["high_duration"], 10)
        self.assertEqual(am.measures(games["chat__p1__w0__s1"]["rounds"], threshold=0.51)["high_duration"], 0)

    def test_fixed_window_and_assigned(self):
        specs = [mt.spec(seed=1, defect_at=4, rounds=10), mt.spec(seed=2, rounds=3)]
        _, rows = games_for(specs, 1, 5)
        self.assertAlmostEqual(one(rows, "s1", "window")["level"], 0.7)  # rounds 1-5: 1,1,1,0.5,0 -> 0.7
        self.assertEqual([r for r in rows if "s2" in r["trial_id"] and r["basis"] == "window"], [])  # short game dropped
        self.assertEqual(one(rows, "s2", "assigned")["level"], 1.0)  # but reported as assigned

    def test_corrupt_trials_are_left_out(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, [mt.spec()])
            p = Path(d) / "trials.csv"
            p.write_text(p.read_text(encoding="utf-8").replace(",done,", ",corrupt,"), encoding="utf-8", newline="")
            games = am.build_games(am.load_tables(d), 2.0, 4.0)
            self.assertEqual(am.game_measures(games, 1, 10), [])
            self.assertEqual(am.exclusions(games, 1, 10), [{"trial_id": "chat__p1__w0__s1", "basis": "all", "reason": "corrupt"}])

    def test_exclusions_name_short_games(self):
        games, _ = games_for([mt.spec(seed=2, rounds=3)], 1, 5)
        self.assertEqual(am.exclusions(games, 1, 5), [{"trial_id": "chat__p1__w0__s2", "basis": "window", "reason": "incomplete_window"}])

    def test_window_summary_uses_common_seeds_only(self):
        _, rows = games_for([mt.spec(arm="chat", seed=1), mt.spec(arm="chat", seed=2), mt.spec(arm="tacit", seed=1, kind="compete")])
        self.assertEqual(am.pair_window(rows), (rows, []))  # default: the headline arms only, and these are not headline arms
        kept, dropped = am.pair_window(rows, None)  # None: pair every arm given
        self.assertEqual({r["trial_id"] for r in dropped}, {"chat__p1__w0__s2"})
        self.assertTrue(all(r["basis"] == "window" for r in dropped))
        self.assertEqual(len([r for r in kept if r["basis"] == "assigned"]), 6)  # as assigned: nothing dropped


class Bootstrap(unittest.TestCase):
    def test_stratified_by_wording_keeps_stratum_sizes(self):
        # wording A all 0, wording B all 1: every stratified resample has mean exactly 0.5 (an unstratified one would not)
        mean, lo, hi = am.bootstrap_ci({"A": [0.0, 0.0], "B": [1.0, 1.0]}, boot=500, seed=3)
        self.assertEqual((mean, lo, hi), (0.5, 0.5, 0.5))

    def test_ci_brackets_mean_and_is_deterministic(self):
        s = {"A": [0.0, 1.0, 0.0, 1.0], "B": [1.0, 1.0, 0.0, 0.0]}
        a, b = am.bootstrap_ci(s, 500, 1), am.bootstrap_ci(s, 500, 1)
        self.assertEqual(a, b)
        self.assertLess(a[1], a[0])
        self.assertGreater(a[2], a[0])

    def test_empty(self):
        self.assertEqual(am.bootstrap_ci({}), (None, None, None))

    def test_single_game_wordings_fall_back_to_a_game_level_bootstrap(self):  # quality review Q5/Q6
        s = {"0": [0.0], "1": [1.0], "2": [0.5], "3": [1.0]}
        mean, lo, hi = am.bootstrap_ci(s, 500, 0)
        self.assertEqual(mean, 0.625)
        self.assertLess(lo, mean)          # stratified, every resample would be the mean itself: (0.625, 0.625, 0.625)
        self.assertGreater(hi, mean)
        self.assertEqual(am.ci_method(s), "game")
        self.assertEqual(am.ci_method({"0": [0.0, 1.0], "1": [1.0, 1.0]}), "stratified")
        self.assertEqual(am.ci_method({"0": [0.0, 1.0], "1": [1.0]}), "game")   # one single-game wording is enough

    def test_one_game_is_not_estimable(self):
        self.assertEqual(am.bootstrap_ci({"0": [0.4]}, 100, 0), (0.4, None, None))
        self.assertEqual(am.ci_method({"0": [0.4]}), "none")
        self.assertEqual(am.ci_method({}), "none")

    def test_stratified_resampling_is_unchanged_when_every_wording_has_two_games(self):
        s = {"A": [0.0, 1.0, 0.0, 1.0], "B": [1.0, 1.0, 0.0, 0.0]}
        self.assertEqual(am.bootstrap_ci(s, 500, 1), am.stratified_ci(s, 500, 1))


class SummaryAndContrast(unittest.TestCase):
    def specs(self):
        out = []
        for w in (0, 1):
            for s in (1, 2):
                out.append(mt.spec(arm="chat", wording=w, seed=s, kind="collude"))
                out.append(mt.spec(arm="tacit", wording=w, seed=s, kind="compete"))
        out.append(mt.spec(arm="chat", wording=0, seed=99, kind="mid"))  # unpaired: no tacit twin
        return out

    def test_summary_per_wording_and_ci(self):
        _, rows = games_for(self.specs())
        s = {(r["arm"], r["basis"], r["refusals"]): r for r in am.summarize(rows, 300, 0)}
        chat = s[("chat", "assigned", "with")]
        self.assertEqual(chat["n_games"], 5)
        self.assertEqual(json.loads(chat["per_wording"]), {"0": round((1 + 1 + 0.5) / 3, 6), "1": 1.0})
        self.assertEqual(s[("tacit", "assigned", "with")]["level"], 0.0)
        self.assertEqual(s[("tacit", "assigned", "with")]["never_high"], 4)

    def test_contrast_pairs_by_wording_and_seed(self):
        specs = [mt.spec(arm="chat", wording=0, seed=1, kind="collude"), mt.spec(arm="tacit", wording=0, seed=1, kind="compete"),
                 mt.spec(arm="chat", wording=0, seed=2, kind="collude"), mt.spec(arm="tacit", wording=0, seed=2, kind="mid"),
                 mt.spec(arm="chat", wording=1, seed=1, kind="compete"), mt.spec(arm="tacit", wording=1, seed=1, kind="compete")]
        _, rows = games_for(specs)
        (c,) = [r for r in am.contrasts(rows, "chat", "tacit", 500, 0) if r["basis"] == "assigned" and r["refusals"] == "with"]
        # diffs 1.0, 0.5 (wording 0) and 0.0 (wording 1): mean 0.5; wording 1 has a single pair, so the three pairs are
        # resampled together (game level, ci_method game) rather than within wording
        self.assertEqual((c["n_pairs"], c["diff"]), (3, 0.5))
        self.assertGreater(c["diff_hi"], c["diff"])
        self.assertLess(c["diff_lo"], c["diff"])
        self.assertLessEqual(c["diff_hi"], 1.0)  # never above what the data allow
        self.assertEqual(c["ci_method"], "game")

    def test_duplicate_games_in_a_cell_raise(self):
        _, rows = games_for([mt.spec(seed=1)])
        with self.assertRaises(ValueError):
            am.contrasts(rows + [r for r in rows if r["basis"] == "assigned"], "chat", "tacit")

    def test_contrast_uses_paired_seeds_only(self):
        _, rows = games_for(self.specs())
        (c,) = [r for r in am.contrasts(rows, "chat", "tacit", 200, 0) if r["basis"] == "assigned" and r["refusals"] == "with"]
        self.assertEqual((c["n_pairs"], c["diff"], c["diff_lo"], c["diff_hi"]), (4, 1.0, 1.0, 1.0))


class WindowShareAndCiMethod(unittest.TestCase):
    def test_summary_reports_the_share_kept_by_the_window_and_the_ci_method(self):
        specs = [mt.spec(arm="chat", wording=w, seed=s, rounds=10 if (w, s) != (1, 2) else 4) for w in (0, 1) for s in (1, 2)]
        _, rows = games_for(specs)
        s = {(r["basis"], r["refusals"]): r for r in am.summarize(rows, 200, 0)}
        self.assertEqual((s[("window", "with")]["n_games"], s[("window", "with")]["games_assigned"], s[("window", "with")]["window_share"]),
                         (3, 4, 0.75))
        self.assertEqual((s[("assigned", "with")]["games_assigned"], s[("assigned", "with")]["window_share"]), (4, ""))
        self.assertEqual(s[("window", "with")]["ci_method"], "game")      # wording 1 kept one game in the window
        self.assertEqual(s[("assigned", "with")]["ci_method"], "stratified")

    def test_a_cell_whose_window_keeps_no_game_still_shows_its_share(self):
        _, rows = games_for([mt.spec(arm="short", seed=s, rounds=4) for s in (1, 2)] + [mt.spec(arm="chat")])
        s = {(r["arm"], r["basis"], r["refusals"]): r for r in am.summarize(rows, 50, 0, empty_window=True)}
        w = s[("short", "window", "without")]
        self.assertEqual((w["n_games"], w["games_assigned"], w["window_share"], w["level"], w["ci_method"]), (0, 2, 0.0, "", "none"))
        self.assertEqual(s[("chat", "window", "with")]["window_share"], 1.0)
        self.assertNotIn(("short", "window", "with"), {(r["arm"], r["basis"], r["refusals"]) for r in am.summarize(rows, 50, 0)})

    def test_cli_warns_about_the_game_level_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", [mt.spec(arm="chat", wording=w) for w in (0, 1, 2)])
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                am.main([str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4", "--window-end", "10", "--boot", "20"])
            self.assertIn("single game", err.getvalue())
            rows = list(csv.DictReader(open(Path(d) / "o" / "measures_summary.csv", encoding="utf-8")))
            self.assertEqual({r["ci_method"] for r in rows}, {"game"})
            self.assertEqual({r["window_share"] for r in rows if r["basis"] == "window"}, {"1.0"})


class Cli(unittest.TestCase):
    def test_cli_writes_deterministic_tables(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", [mt.spec(arm="chat"), mt.spec(arm="tacit", kind="compete")])
            outs = []
            for n in ("o1", "o2"):
                am.main([str(Path(d) / "t"), str(Path(d) / n), "--competitive", "2", "--collusive", "4", "--window-end", "10",
                         "--boot", "50", "--contrast", "chat:tacit"])
                outs.append({f.name: f.read_bytes() for f in (Path(d) / n).iterdir()})
            self.assertEqual(outs[0], outs[1])
            self.assertEqual(sorted(outs[0]), ["contrasts.csv", "exclusions.csv", "measures_by_game.csv", "measures_summary.csv"])
            self.assertNotIn(b"\r", outs[0]["measures_summary.csv"])
            rows = list(csv.DictReader(open(Path(d) / "o1" / "contrasts.csv", encoding="utf-8")))
            self.assertEqual(rows[0]["diff"], "1.0")

    def test_missing_required_table(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                am.load_tables(d)


class PriceDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = mt.write_tables(Path(self.tmp.name) / "t", [mt.spec(arm="a", seed=1), mt.spec(arm="a", seed=2)])

    def _set(self, comp, coll, only=None):
        f = self.dir / "trials.csv"
        rows = list(csv.DictReader(open(f, encoding="utf-8", newline="")))
        for i, r in enumerate(rows):
            r["competitive_price"], r["collusive_price"] = (comp, coll) if only is None or i == only else ("2", "4")
        with open(f, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator=chr(10))
            w.writeheader()
            w.writerows(rows)

    def test_default_from_trials_csv(self):
        self._set("2", "4")
        self.assertEqual((2.0, 4.0), am.resolve_prices(am.load_tables(self.dir)))

    def test_override_wins_and_needs_no_column(self):
        self.assertEqual((1.0, 5.0), am.resolve_prices(am.load_tables(self.dir), 1.0, 5.0))
        self._set("2", "4")
        self.assertEqual((1.0, 4.0), am.resolve_prices(am.load_tables(self.dir), 1.0, None))

    def test_missing_or_conflicting_prices_are_refused(self):
        with self.assertRaisesRegex(ValueError, "--competitive"):
            am.resolve_prices(am.load_tables(self.dir))
        self._set("3", "4", only=0)
        with self.assertRaisesRegex(ValueError, "2 competitive_price"):
            am.resolve_prices(am.load_tables(self.dir))

    def test_cli_default_equals_explicit(self):
        self._set("2", "4")
        a, b = Path(self.tmp.name) / "a", Path(self.tmp.name) / "b"
        am.main([str(self.dir), str(a), "--window-end", "10", "--boot", "20"])
        am.main([str(self.dir), str(b), "--competitive", "2", "--collusive", "4", "--window-end", "10", "--boot", "20"])
        self.assertEqual((a / "measures_by_game.csv").read_text(encoding="utf-8"), (b / "measures_by_game.csv").read_text(encoding="utf-8"))

    def test_cli_without_prices_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as cm:
            am.main([str(self.dir), str(Path(self.tmp.name) / "c")])
        self.assertEqual(2, cm.exception.code)


if __name__ == "__main__":
    unittest.main()
