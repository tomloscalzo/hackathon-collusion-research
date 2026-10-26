"""Tests for anchor_compare.py (unit N4) on synthetic tables with known gain and known shares.
Run: python -X utf8 -m unittest tools/trial/test_anchor_compare.py"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_compare as ac  # noqa: E402

BENCH = {("a", "1"): (1.0, 3.0)}   # pi^N = 1, pi^M = 3: a mean profit of 2.0 is a gain index of 0.5


def tables(games):
    """games: [(wording, seed, [(quote, profit, imputed)...])] -> collect-style tables dict (arm a, point 1, thinking off)."""
    t, r = [], []
    for w, s, rounds in games:
        tid = "a__p1__w%s__s%s__t0" % (w, s)
        t.append(dict(trial_id=tid, arm="a", thinking="off", penalty_point="1", wording=str(w), seed=str(s), status="done"))
        for i, (q, p, imp) in enumerate(rounds, 1):
            r.append(dict(trial_id=tid, round=str(i), seat="a0", quote=str(q), profit=str(p), imputed=str(imp)))
    return dict(trials=t, rounds=r)


def game(w, s, profit, quotes):
    return (w, s, [(q, profit, 0) for q in quotes])


def by_metric(rows):
    return {r["metric"]: r for r in rows}


class AnchorCompare(unittest.TestCase):
    def test_known_gain_and_shares_with_exclusions(self):
        anch = tables([game(0, 1, 2.0, [2.09, 2.09, 3.0, 1.2]),         # anchored set 3 of 4
                       game(0, 2, 2.0, [2.09, 1.54, 3.0, 2.09]),        # anchored set 4 of 4
                       game(1, 1, 2.0, [2.0, 2.0, 2.0, 2.0])])          # only in the anchored dir: unpaired
        neut = tables([game(0, 1, 2.5, [1.0, 2.0, 3.0, 3.7]),           # gain 0.75; neutral set 3 of 4
                       game(0, 2, 2.5, [1.5, 2.5, 3.5, 4.0]),           # neutral set 4 of 4
                       game(2, 1, 2.5, [2.0])])                         # only in the neutral dir: unpaired
        rows, unpaired = ac.compare(anch, neut, start=1, end=4, boot=200, bench=BENCH)
        m = by_metric(rows)
        self.assertEqual((0.5, 0.75, 0.25, 2), tuple(m["profit_gain_index"][k] for k in ("anchored", "neutral", "diff", "n_units")))
        self.assertAlmostEqual((0.75 + 1.0) / 2, m["share_neutral_set"]["neutral"], 6)
        self.assertAlmostEqual((0.75 + 1.0) / 2, m["share_anchored_set"]["anchored"], 6)
        self.assertAlmostEqual(0.125, m["share_p1.54"]["anchored"], 6)             # (0 + 1/4) / 2
        self.assertAlmostEqual(0.5, m["share_p2.09"]["anchored"], 6)               # (2/4 + 2/4) / 2
        self.assertAlmostEqual(0.25, m["share_p3.00"]["anchored"], 6)              # (1/4 + 1/4) / 2
        self.assertAlmostEqual(0.125, m["share_p1.00"]["neutral"], 6)              # (1/4 + 0) / 2
        self.assertAlmostEqual(0.0, m["share_p2.09"]["neutral"], 6)                # the neutral root never quotes 2.09 here
        self.assertEqual(["anchored", "neutral"], sorted(u["side"] for u in unpaired))
        self.assertEqual({("a", "1", "1", "1", "off"), ("a", "1", "2", "1", "off")},
                         {(u["arm"], u["cell"], u["wording"], u["seed"], u["thinking"]) for u in unpaired})
        self.assertTrue(all(u["reason"] == "missing on the other side" for u in unpaired))

    def test_corrupt_game_is_unpaired_and_excluded(self):
        anch = tables([game(0, 1, 2.0, [2.09]), game(0, 2, 2.0, [2.09])])
        neut = tables([game(0, 1, 2.0, [1.0]), game(0, 2, 2.0, [1.0])])
        neut["trials"][1]["status"] = "corrupt"
        rows, unpaired = ac.compare(anch, neut, start=1, end=1, boot=50, bench=BENCH)
        self.assertEqual(1, by_metric(rows)["profit_gain_index"]["n_units"])
        self.assertEqual(2, len(unpaired))
        self.assertIn("corrupt", " ".join(u["reason"] for u in unpaired))

    def test_imputed_quotes_are_not_counted(self):
        anch = tables([(0, 1, [(2.09, 2.0, 0), (1.2, 2.0, 1)])])
        neut = tables([(0, 1, [(1.0, 2.0, 0), (1.0, 2.0, 0)])])
        rows, _ = ac.compare(anch, neut, start=1, end=4, boot=10, bench=BENCH)
        self.assertEqual(1.0, by_metric(rows)["share_anchored_set"]["anchored"])

    def test_bootstrap_is_deterministic_and_ci_contains_true_difference(self):
        # neutral gain = anchored gain + 0.2 exactly, plus unit noise shared by both roots: pairing removes it
        noise = [0.0, 0.3, -0.2, 0.5, 0.1, -0.4, 0.2, 0.0, 0.4, -0.1, 0.25, -0.3]
        anch = tables([game(i, 1, 2.0 + n, [2.09, 3.0]) for i, n in enumerate(noise)])
        neut = tables([game(i, 1, 2.0 + n + 0.4, [1.0, 3.0]) for i, n in enumerate(noise)])   # +0.4 profit = +0.2 gain
        a = ac.compare(anch, neut, start=1, end=2, boot=2000, seed=20260101, bench=BENCH)[0]
        b = ac.compare(anch, neut, start=1, end=2, boot=2000, seed=20260101, bench=BENCH)[0]
        self.assertEqual(a, b)
        g = by_metric(a)["profit_gain_index"]
        self.assertAlmostEqual(0.2, g["diff"], 6)
        self.assertLessEqual(g["ci_low"], 0.2 + 1e-9)
        self.assertGreaterEqual(g["ci_high"], 0.2 - 1e-9)
        self.assertAlmostEqual(0.0, g["ci_high"] - g["ci_low"], 6)           # no unit noise in the difference: a zero-width CI
        self.assertAlmostEqual(-0.5, by_metric(a)["share_anchored_set"]["diff"], 6)   # 2.09 -> 1.0 moves half the anchored share

    def test_ci_has_width_when_the_difference_varies(self):
        diffs = [0.0, 0.2, 0.4, 0.6, 0.0, 0.2, 0.4, 0.6]                       # profit; true mean 0.3 profit = 0.15 gain
        anch = tables([game(i, 1, 2.0, [3.0]) for i in range(8)])
        neut = tables([game(i, 1, 2.0 + d, [3.0]) for i, d in enumerate(diffs)])
        g = by_metric(ac.compare(anch, neut, start=1, end=1, boot=2000, bench=BENCH)[0])["profit_gain_index"]
        self.assertAlmostEqual(0.15, g["diff"], 6)
        self.assertLess(g["ci_low"], 0.15)
        self.assertGreater(g["ci_high"], 0.15)
        self.assertGreater(g["ci_low"], 0.0)
        other = by_metric(ac.compare(anch, neut, start=1, end=1, boot=2000, seed=7, bench=BENCH)[0])["profit_gain_index"]
        self.assertEqual(g["diff"], other["diff"])                             # the point estimate does not depend on the seed

    def test_gain_uses_the_round_window_and_drops_games_lacking_it(self):
        anch = tables([(0, 1, [(2.0, 2.0, 0), (2.0, 2.0, 0), (2.0, 3.0, 0)]), game(0, 2, 2.0, [2.0])])
        neut = tables([(0, 1, [(2.0, 2.5, 0), (2.0, 2.5, 0), (2.0, 9.0, 0)]), game(0, 2, 2.5, [2.0])])
        g = by_metric(ac.compare(anch, neut, boot=20, bench=BENCH, start=1, end=2)[0])["profit_gain_index"]   # round 3 is outside
        self.assertEqual((1, 0.5, 0.75), (g["n_units"], g["anchored"], g["neutral"]))                          # game 2 has 1 round: dropped
        none = by_metric(ac.compare(anch, neut, boot=20, bench=BENCH)[0])["profit_gain_index"]                 # default 1..20: both drop
        self.assertEqual(0, none["n_units"])
        self.assertEqual(2, by_metric(ac.compare(anch, neut, boot=20, bench=BENCH)[0])["share_p2.00"]["n_units"])   # shares use all rounds

    def test_neutral_set_without_the_floor(self):
        anch = tables([game(0, 1, 2.0, [1.0, 3.0, 2.0, 2.0])])
        neut = tables([game(0, 1, 2.0, [1.0, 3.0, 2.0, 2.0])])
        m = by_metric(ac.compare(anch, neut, start=1, end=4, boot=5, bench=BENCH)[0])
        self.assertEqual(1.0, m["share_neutral_set"]["neutral"])
        self.assertEqual(0.75, m["share_neutral_set_no_floor"]["neutral"])

    def test_duplicate_pair_keys_are_reported_not_overwritten(self):
        anch = tables([game(0, 1, 2.0, [2.09]), game(0, 2, 2.0, [2.09])])
        neut = tables([game(0, 1, 2.0, [1.0]), game(0, 2, 2.0, [1.0])])
        dup = tables([game(0, 1, 2.0, [3.0])])
        dup["trials"][0]["trial_id"] = "a__p1__w0__s1__t0__copy"
        for r in dup["rounds"]:
            r["trial_id"] = "a__p1__w0__s1__t0__copy"
        anch["trials"] += dup["trials"]
        anch["rounds"] += dup["rounds"]
        rows, unpaired = ac.compare(anch, neut, start=1, end=1, boot=5, bench=BENCH)
        self.assertEqual(1, by_metric(rows)["profit_gain_index"]["n_units"])
        self.assertIn(("1", "anchored", "duplicate pair key"), [(u["seed"], u["side"], u["reason"].replace("unusable here: ", "")) for u in unpaired])

    def test_benchmarks_missing_and_conflicting(self):
        self.assertEqual([("a", "1")], ac.missing_benchmarks(tables([game(0, 1, 2.0, [2.0])]), {}))
        self.assertEqual([], ac.missing_benchmarks(tables([game(0, 1, 2.0, [2.0])]), BENCH))
        with tempfile.TemporaryDirectory() as td:
            dirs = []
            for name, nash in (("x", "1.0"), ("y", "1.5")):
                d = Path(td) / name
                d.mkdir()
                (d / "baseline_benchmarks.csv").write_text("arm,penalty_point,firms,profit_nash,profit_collusive,competitive_price,collusive_price\n"
                                                           "a,1,2,%s,3.0,1.0,2.0\n" % nash, encoding="utf-8")
                dirs.append(str(d))
            self.assertEqual({("a", "1"): (1.0, 3.0)}, ac.load_bench(dirs[:1], None))
            with self.assertRaises(ValueError):
                ac.load_bench(dirs, None)

    def test_cli_writes_csv_and_unpaired_and_blank_gain_without_benchmarks(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            dirs = []
            for name, tb in (("a", tables([game(0, 1, 2.0, [2.09]), game(0, 2, 2.0, [2.09])])),
                             ("n", tables([game(0, 1, 2.0, [1.0])]))):
                d = td / name
                d.mkdir()
                for fn in ("trials", "rounds"):
                    with open(d / (fn + ".csv"), "w", encoding="utf-8", newline="") as f:
                        w = csv.DictWriter(f, list(tb[fn][0]), lineterminator="\n")
                        w.writeheader()
                        w.writerows(tb[fn])
                dirs.append(str(d))
            out = td / "o" / "cmp.csv"
            self.assertEqual(0, ac.main(dirs + [str(out)]))
            with open(out, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(ac.OUT_COLS, list(rows[0]))
            self.assertEqual("", by_metric(rows)["profit_gain_index"]["diff"])
            with open(str(out) + ".unpaired.csv", encoding="utf-8") as f:
                un = list(csv.DictReader(f))
            self.assertEqual(["2"], [u["seed"] for u in un])


if __name__ == "__main__":
    unittest.main()
