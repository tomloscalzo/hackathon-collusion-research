"""Tests for competitiveness.py (U16) with hand-built 2- and 3-firm fixtures where targets differ per firm.
Run: python -X utf8 -m unittest tools/trial/test_competitiveness.py"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import collect  # noqa: E402
import status_page  # noqa: E402
import competitiveness as cp  # noqa: E402

FLOOR, TICK = 1.0, 0.01


def rows(table):
    """{round: {seat: quote}} -> round rows."""
    return [{"round": r, "seat": s, "quote": q} for r, qs in table.items() for s, q in qs.items()]


TWO = rows({1: {"A": 2.00, "B": 2.00}, 2: {"A": 1.99, "B": 2.00}, 3: {"A": 1.99, "B": 1.98}, 4: {"A": 1.98, "B": 2.10}})
THREE = rows({1: {"A": 3.00, "B": 2.50, "C": 2.00},
              2: {"A": 2.00, "B": 1.99, "C": 2.00},      # targets 2.00 / 2.00 / 2.50: A matched, B and C competitive
              3: {"A": 1.00, "B": 1.99, "C": 1.99},      # targets 1.99 / 2.00 / 1.99: A, B undercut; C matched B
              4: {"A": 1.00, "B": 1.00, "C": 1.00},      # B's target is A's floor quote and B quotes the floor
              5: {"A": 1.00, "B": 1.01}})                # C has no quote; B above a floor target


class CompetitivenessTest(unittest.TestCase):
    def flags(self, r):
        return {k: v for k, v in cp.classify(r, FLOOR, TICK)[0].items()}

    def test_two_firms_targets_differ_per_firm(self):
        f = self.flags(TWO)
        self.assertEqual({(2, "A"): True, (2, "B"): False, (3, "A"): True, (3, "B"): True, (4, "A"): False, (4, "B"): False}, f)

    def test_three_firms_each_firm_has_its_own_best_rival(self):
        f = self.flags(THREE)
        self.assertEqual({(2, "A"): False, (2, "B"): True, (2, "C"): True,
                          (3, "A"): True, (3, "B"): True, (3, "C"): False,
                          (4, "A"): True, (4, "B"): True, (4, "C"): True,
                          (5, "A"): True, (5, "B"): False}, f)   # (5, C) unscored: no quote

    def test_own_quote_is_excluded_from_the_target(self):
        # A alone at 2.00 the round before would be its own target; with only B at 3.00 the target is 3.00.
        f = self.flags(rows({1: {"A": 2.00, "B": 3.00}, 2: {"A": 2.50, "B": 3.00}}))
        self.assertTrue(f[(2, "A")])     # 2.50 < B's 3.00 (A's own 2.00 does not count)
        self.assertFalse(f[(2, "B")])    # 3.00 vs target A's 2.00

    def test_floor_rule_and_tick_boundaries(self):
        self.assertTrue(cp.is_competitive(1.00, 1.00, FLOOR, TICK))      # floor against a floor target
        self.assertFalse(cp.is_competitive(1.01, 1.00, FLOOR, TICK))     # above a floor target
        self.assertTrue(cp.is_competitive(1.99, 2.00, FLOOR, TICK))      # one tick below
        self.assertFalse(cp.is_competitive(2.00, 2.00, FLOOR, TICK))     # matched
        self.assertFalse(cp.is_competitive(1.50, 1.50, FLOOR, TICK))
        self.assertTrue(cp.is_competitive(1.5899999999999999, 1.60, FLOOR, TICK))   # logged float noise
        self.assertFalse(cp.is_competitive(1.60000000001, 1.60, FLOOR, TICK))
        self.assertTrue(cp.is_competitive(1.00, 1.50, FLOOR, TICK))                 # floor undercuts a high target

    def test_round1_is_reported_separately(self):
        flags, r1 = cp.classify(rows({1: {"A": 1.00, "B": 2.00}, 2: {"A": 1.00, "B": 1.00}}), FLOOR, TICK)
        self.assertEqual({"A": "floor", "B": "above_floor"}, r1)
        self.assertTrue(all(r >= 2 for r, _ in flags))

    def test_firm_rows_two_firms(self):
        by = {r["seat"]: r for r in cp.firm_rows(TWO, FLOOR, TICK, "g")}
        a, b = by["A"], by["B"]
        self.assertEqual((3, 2, 1, 66.6667, 33.3333, 0, 4, "above_floor"),
                         (a["scored_rounds"], a["competitive_rounds"], a["noncompetitive_rounds"], a["competitive_pct"], a["noncompetitive_pct"],
                          a["always_competitive"], a["first_stop_round"], a["round1_class"]))
        self.assertEqual((1, 2, 2), (b["competitive_rounds"], b["noncompetitive_rounds"], b["first_stop_round"]))

    def test_firm_rows_three_firms_and_always_competitive(self):
        by = {r["seat"]: r for r in cp.firm_rows(THREE, FLOOR, TICK)}
        self.assertEqual((3, 4, 2), (by["A"]["competitive_rounds"], by["A"]["scored_rounds"], by["A"]["first_stop_round"]))
        self.assertEqual((3, 4, 5), (by["B"]["competitive_rounds"], by["B"]["scored_rounds"], by["B"]["first_stop_round"]))
        self.assertEqual((2, 3, 3), (by["C"]["competitive_rounds"], by["C"]["scored_rounds"], by["C"]["first_stop_round"]))
        steady = cp.firm_rows(rows({1: {"A": 2.0, "B": 2.0}, 2: {"A": 1.9, "B": 1.9}, 3: {"A": 1.0, "B": 1.0}, 4: {"A": 1.0, "B": 1.0}}), FLOOR, TICK)
        self.assertEqual([1, 1], [f["always_competitive"] for f in steady])   # both undercut the 2.0 pair, then reach and hold the floor
        self.assertEqual(["", ""], [f["first_stop_round"] for f in steady])

    def test_cell_summary(self):
        s = cp.cell_summary(cp.firm_rows(TWO, FLOOR, TICK) + cp.firm_rows(THREE, FLOOR, TICK))
        self.assertEqual(5, s["firms"])
        self.assertEqual(0.0, s["always_competitive_share"])
        self.assertAlmostEqual((2 / 3 + 1 / 3 + 3 / 4 + 3 / 4 + 2 / 3) / 5, s["mean_competitive_share"], places=5)
        solo = cp.cell_summary(cp.firm_rows(rows({1: {"A": 2.0, "B": 2.0}, 2: {"A": 2.0, "B": 1.9}}), FLOOR, TICK))
        self.assertEqual(0.5, solo["always_competitive_share"])   # A matched B: not competitive; B undercut
        win = cp.cell_summary(cp.firm_rows(rows({1: {"A": 2.0, "B": 2.1}, 2: {"A": 1.9, "B": 1.99}}), FLOOR, TICK))
        self.assertEqual(1.0, win["always_competitive_share"])    # A undercuts 2.1; B 1.99 undercuts A's 2.0

    def test_missing_data_is_unscored(self):
        self.assertEqual({}, cp.classify(rows({1: {"A": 2.0}, 2: {"A": 1.0}}), FLOOR, TICK)[0])   # no rival
        r = rows({1: {"A": 2.0, "B": ""}, 2: {"A": 1.0, "B": 1.0}})
        self.assertEqual({(2, "B"): True}, cp.classify(r, FLOOR, TICK)[0])

    def test_analysis_m_hook_uses_the_flags(self):
        flags = cp.classify(THREE, FLOOR, TICK)[0]
        rounds = {r: {"competitive": {s: v for (rr, s), v in flags.items() if rr == r}} for r in range(2, 6)}
        m = am.competitive_measures(rounds, sorted(rounds))
        self.assertAlmostEqual(8 / 11, m["competitive_share"])
        self.assertEqual(0.0, m["always_competitive_share"])
        self.assertIsNone(am.competitive_measures({1: {"competitive": {}}}, [1])["competitive_share"])
        masked = am.competitive_measures(rounds, sorted(rounds), masked={2})
        self.assertAlmostEqual(6 / 8, masked["competitive_share"])

    def test_collect_to_analysis_m_and_status_page(self):
        trials = Path(__file__).resolve().parent / "fixtures" / "collect" / "trials"
        with tempfile.TemporaryDirectory() as tmp:
            collect.collect(trials, Path(tmp) / "t")
            self.assertEqual(0, am.main([str(Path(tmp) / "t"), str(Path(tmp) / "m"), "--boot", "20", "--no-pairing", "--window-end", "2"]))
            with open(Path(tmp) / "m" / "measures_by_game.csv", encoding="utf-8", newline="") as f:
                g = {(r["trial_id"], r["basis"], r["refusals"]): r for r in csv.DictReader(f)}
            t = g[("tacit__p1__w0__s1", "assigned", "with")]   # a0 matched (not competitive), a1 undercut
            self.assertEqual(("0.5", "0.5"), (t["competitive_share"], t["always_competitive_share"]))
            with open(Path(tmp) / "m" / "measures_summary.csv", encoding="utf-8", newline="") as f:
                self.assertIn("competitive_share", next(csv.reader(f)))
            d = trials / "tacit__p1__w0__s1"
            self.assertEqual(2, len(status_page.read_competitiveness(d)))

    def test_imputed_quote_counts_as_played_and_tick_is_a_parameter(self):
        r = rows({1: {"A": 2.0, "B": 2.0}, 2: {"A": 1.0, "B": 2.0}, 3: {"A": 1.0, "B": 1.0}})
        self.assertEqual({(2, "A"): True, (2, "B"): False, (3, "A"): True, (3, "B"): True}, cp.classify(r, 1.0, 0.01)[0])
        r = rows({1: {"A": 2.0, "B": 2.0}, 2: {"A": 1.9, "B": 2.0}})
        self.assertEqual({(2, "A"): False, (2, "B"): False}, cp.classify(r, 1.0, 0.5)[0])

    def test_no_floor_gives_blank_flags_and_no_firm_rows(self):
        import json
        trials = Path(__file__).resolve().parent / "fixtures" / "collect" / "trials"
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "in" / "x__p1__w0__s1"
            d.mkdir(parents=True)
            (d / "events.jsonl").write_text((trials / "tacit__p1__w0__s1" / "events.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
            (d / "params.json").write_text(json.dumps({"arm": "x"}), encoding="utf-8")
            collect.collect(Path(tmp) / "in", Path(tmp) / "out")
            with open(Path(tmp) / "out" / "rounds.csv", encoding="utf-8", newline="") as f:
                self.assertEqual({""}, {x["competitive_round"] for x in csv.DictReader(f)})
            with open(Path(tmp) / "out" / "firms.csv", encoding="utf-8", newline="") as f:
                self.assertEqual([], list(csv.DictReader(f)))

    def test_section_text(self):
        t = cp.competitiveness_section({"g1": TWO, "g2": THREE}, FLOOR, TICK)
        self.assertIn("g1: firms 2", t)
        self.assertIn("all: firms 5, always competitive 0.0", t)


if __name__ == "__main__":
    unittest.main()
