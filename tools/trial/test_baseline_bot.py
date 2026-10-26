"""Tests for baseline_bot.py (U18): the scripted undercutter baseline driver on a tiny grid, the benchmark arithmetic, and
the --baseline option of analysis_m / analysis_headline. The engine is replaced by a Python model of the strategy, except in
one test that runs the real jar when it has been built (and knows UNDERCUTTER).
Run: python -X utf8 -m unittest tools/trial/test_baseline_bot.py"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline as ah  # noqa: E402
import analysis_m as am  # noqa: E402
import baseline_bot as bb  # noqa: E402

SCEN = "slice-m-p3.yaml"


def fake_run(scenario, seed, open_, step, rounds=4, floor=1.0):
    """What the engine would return for two undercutters: both quote open, then step ticks under the other's last quote."""
    recs, q = [], [open_, open_]
    for r in range(1, rounds + 1):
        if r > 1:
            q = [max(floor, round(q[1] - 0.01 * step, 2)), max(floor, round(q[0] - 0.01 * step, 2))]
        inside = min(q)
        agents = [dict(id="llm%d" % (i + 1), displayed=q[i], hiddenFill=None, excluded=False, fine=0.0, phase="UNDERCUT",
                       payoff=(q[i] - 1.0) * 100 * (1 - q[i] / 5.0) / 2 if q[i] <= inside + 1e-9 else 0.0) for i in range(2)]
        last = r == rounds
        recs.append(dict(round=r, agents=agents, insideQuote=inside,
                         detection=dict(triggered=last, evidence=last, pTrigger=0.1, pEvidence=1.0, tipActive=False)))
    return dict(rounds=recs, status="EVIDENCE")


def row(arm, point, seed, thinking="0", wording="0", scenario=SCEN, firms="2"):
    return dict(trial_id="%s__p%s__w%s__s%s__t%s" % (arm, point, wording, seed, thinking), arm=arm, penalty_point=str(point),
                scenario_file=scenario, firms=firms, seats="llm,llm", wording=wording, seed=str(seed), thinking=thinking)


GRID = [row("headline-tacit", 3, 1), row("headline-tacit", 3, 2, thinking="1"), row("headline-chat", 3, 1, wording="1")]


class Benchmarks(unittest.TestCase):
    def test_ripe_market(self):
        s_n, s_m, pi_n, pi_m = bb.benchmarks(bb.market_of(SCEN))
        self.assertEqual((s_n, s_m), (1.0, 3.0))
        self.assertAlmostEqual(pi_n, 0.0)
        self.assertAlmostEqual(pi_m, 40.0)   # (3 - 1) * 100 * (1 - 3/5) / 2

    def test_tick_market_refused(self):
        with self.assertRaises(ValueError):
            bb.benchmarks(dict(s0=1, sBar=5, q0=100, n=2, tick=0.05))

    def test_opening_cycles_by_seed(self):
        self.assertEqual([bb.opening(s) for s in (1, 2, 3, 4)], [2.09, 1.54, 2.09, 1.54])
        self.assertEqual(bb.opening("2", (1.2,)), 1.2)


class Driver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.calls = []

        def runner(sc, seed, op, st):
            cls.calls.append((sc, seed, op, st))
            return fake_run(sc, seed, op, st)

        cls.paths = bb.run_baseline(GRID, cls.out, step=1, runner=runner)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def table(self, name):
        with open(self.out / "tables" / name, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_runs_once_per_scenario_and_seed_with_the_seed_opening(self):
        self.assertEqual(self.calls, [(SCEN, 1, 2.09, 1), (SCEN, 2, 1.54, 1)])

    def test_tables_have_collect_shape(self):
        for name in ("trials.csv", "rounds.csv", "firms.csv", "messages.csv", "questions.csv", "refusals.csv", bb.BENCH_FILE):
            self.assertTrue((self.out / "tables" / name).exists(), name)
        trials = {r["trial_id"]: r for r in self.table("trials.csv")}
        self.assertEqual(sorted(trials), sorted(r["trial_id"] for r in GRID))
        t = trials["headline-tacit__p3__w0__s2__t1"]
        self.assertEqual((t["arm"], t["thinking"], t["status"], t["rounds"], t["competitive_price"], t["collusive_price"]),
                         ("headline-tacit", "on", "done", "4", "1.0", "3.0"))
        self.assertEqual(list(self.table("rounds.csv")[0]), bb.collect.ROUND_COLS)

    def test_events_follow_the_game(self):
        ev = [json.loads(l) for l in (self.out / "trials" / "headline-tacit" / "headline-tacit__p3__w0__s1__t0" / "events.jsonl").read_text("utf-8").splitlines()]
        quotes = [(e["round"], e["seat"], e["quote"]) for e in ev if e["kind"] == "quote"]
        self.assertEqual(quotes[:4], [(1, "llm1", 2.09), (1, "llm2", 2.09), (2, "llm1", 2.08), (2, "llm2", 2.08)])
        self.assertEqual([e["kind"] for e in ev if e["round"] == 4], ["quote", "quote", "market", "regulator"])
        market = next(e for e in ev if e["kind"] == "market" and e["round"] == 1)
        self.assertIsNone(market["winner"])   # a tie
        self.assertEqual(market["market_price"], 2.09)

    def test_every_firm_round_is_competitive_after_round_one(self):
        firms = self.table("firms.csv")
        self.assertTrue(firms)
        for f in firms:
            self.assertEqual((f["competitive_pct"], f["always_competitive"], f["scored_rounds"]), ("100.0", "1", "3"))

    def test_reference_rows(self):
        ref = {(r["arm"], r["thinking"], r["basis"]): r for r in bb.reference_rows(self.out / "tables", start=1, end=4)}
        r = ref[("headline-tacit", "off", "window")]    # seed 1: prices 2.09, 2.08, 2.07, 2.06 -> mean 2.075
        self.assertEqual(r["n_games"], 1)
        self.assertAlmostEqual(r["price_index"], (2.075 - 1) / 2, places=5)
        self.assertEqual(r["competitive_share"], 1.0)
        pi = r["profit_gain_index"]
        pays = [(q - 1.0) * 100 * (1 - q / 5.0) / 2 for q in (2.09, 2.08, 2.07, 2.06)]   # both firms tie: each earns this
        self.assertAlmostEqual(pi, (sum(pays) / 4 - 0.0) / 40.0, places=5)
        self.assertGreater(pi, 0.0)
        self.assertLess(pi, 1.0)
        self.assertGreater(pi, ref[("headline-tacit", "on", "window")]["profit_gain_index"])   # seed 2 opens lower: less profit
        pooled = bb.reference_rows(self.out / "tables", 1, 4, pool_label="baseline")
        self.assertEqual({x["arm"] for x in pooled}, {"baseline"})
        self.assertEqual(sum(x["n_games"] for x in pooled if x["basis"] == "window"), 3)

    def test_window_basis_drops_short_games(self):
        ref = [r for r in bb.reference_rows(self.out / "tables", start=1, end=20) if r["basis"] == "window"]
        self.assertEqual(ref, [])


class AnalysisOption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name) / "base"
        bb.run_baseline(GRID, cls.base, runner=lambda sc, seed, op, st: fake_run(sc, seed, op, st))
        cls.theory = Path(cls.tmp.name) / "theory.csv"
        cls.theory.write_text("penalty_point,expected_penalty,theory_level\n3,500,0.5\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, p):
        with open(p, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_analysis_m_adds_baseline_columns_only_with_the_flag(self):
        t = self.base / "tables"
        plain = Path(self.tmp.name) / "m0"
        am.main([str(t), str(plain), "--boot", "5", "--window-end", "4", "--no-pairing"])
        self.assertNotIn("baseline_price_index", self.read(plain / "measures_summary.csv")[0])
        self.assertFalse((plain / "baseline_reference.csv").exists())
        withb = Path(self.tmp.name) / "m1"
        am.main([str(t), str(withb), "--boot", "5", "--window-end", "4", "--no-pairing", "--baseline", str(t)])
        rows = [r for r in self.read(withb / "measures_summary.csv") if r["basis"] == "assigned" and r["refusals"] == "with"
                and r["arm"] == "headline-tacit" and r["thinking"] == "off"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["level_minus_baseline"], "0.0")   # the baseline against itself
        self.assertNotEqual(rows[0]["baseline_profit_gain_index"], "")
        self.assertEqual(rows[0]["baseline_competitive_share"], "1.0")
        self.assertTrue((withb / "baseline_reference.csv").exists())

    def test_analysis_headline_adds_baseline_rows(self):
        t = self.base / "tables"
        out = Path(self.tmp.name) / "h1"
        ah.main([str(t), str(out), "--theory", str(self.theory), "--basis", "assigned", "--baseline", str(t), "--boot", "5",
                 "--no-png", "--arms", "^headline-"])
        rows = self.read(out / "headline_data.csv")
        self.assertIn("baseline_profit_gain_index", rows[0])
        base = [r for r in rows if r["arm"] == "baseline"]
        self.assertEqual({r["thinking"] for r in base}, {"off", "on"})
        self.assertNotEqual(base[0]["profit_gain_index"], "")
        llm = [r for r in rows if r["arm"] == "headline-tacit" and r["refusals"] == "with"]
        self.assertTrue(all(r["baseline_level"] == r["level"] for r in llm))   # baseline compared with itself
        out2 = Path(self.tmp.name) / "h0"
        ah.main([str(t), str(out2), "--theory", str(self.theory), "--basis", "assigned", "--boot", "5", "--no-png"])
        self.assertNotIn("baseline_level", self.read(out2 / "headline_data.csv")[0])

    def test_level_minus_baseline_is_exact_when_the_llm_differs(self):
        t = self.base / "tables"
        llm = Path(self.tmp.name) / "llm"
        import shutil
        shutil.copytree(t, llm)
        lines = (llm / "rounds.csv").read_text("utf-8").splitlines()
        hdr = lines[0].split(",")
        i, j = hdr.index("market_price"), hdr.index("trial_id")
        out = [lines[0]] + [",".join(c if k != i else "1.0" for k, c in enumerate(l.split(","))) if l.split(",")[j].startswith("headline-tacit__p3__w0__s1__t0") else l for l in lines[1:]]
        (llm / "rounds.csv").write_text(chr(10).join(out) + chr(10), encoding="utf-8", newline="")
        o = Path(self.tmp.name) / "m2"
        am.main([str(llm), str(o), "--boot", "5", "--window-end", "4", "--no-pairing", "--baseline", str(t)])
        r = [x for x in self.read(o / "measures_summary.csv") if x["arm"] == "headline-tacit" and x["thinking"] == "off"
             and x["basis"] == "assigned" and x["refusals"] == "with"][0]
        self.assertEqual(r["level"], "0.0")   # price at the floor
        self.assertAlmostEqual(float(r["level_minus_baseline"]), -(2.075 - 1) / 2, places=5)

    def test_missing_benchmarks_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                bb.read_benchmarks(d)


JAR = bb.DEFAULT_JAR


def _jar_knows_undercutter():
    return JAR.is_file() and b"Undercutter" in JAR.read_bytes()


@unittest.skipUnless(_jar_knows_undercutter(), "engine jar with UNDERCUTTER not built")
class RealEngine(unittest.TestCase):
    def test_two_undercutters_walk_down_in_the_real_engine(self):
        run = bb.run_game(JAR, SCEN, 3, 2.09, 1)   # seed 3 plays 6 rounds in the headline slice
        q = [[round(a["displayed"], 6) for a in rec["agents"]] for rec in run["rounds"]]
        self.assertEqual(q[:3], [[2.09, 2.09], [2.08, 2.08], [2.07, 2.07]])
        step5 = bb.run_game(JAR, SCEN, 3, 2.09, 5)
        self.assertEqual([round(a["displayed"], 6) for a in step5["rounds"][1]["agents"]], [2.04, 2.04])

    def test_an_opening_at_the_floor_stays_there(self):
        a = bb.run_game(JAR, SCEN, 1, 1.0, 1)   # opening at the floor: nothing to undercut
        self.assertTrue(all(x["displayed"] == 1.0 for rec in a["rounds"] for x in rec["agents"]))


if __name__ == "__main__":
    unittest.main()
