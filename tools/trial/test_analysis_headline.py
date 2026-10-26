"""Tests for analysis_headline.py (C10.3) on mock tables of known ground truth.
Run: python -X utf8 -m unittest tools/trial/test_analysis_headline.py"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline as ah  # noqa: E402
import analysis_m as am  # noqa: E402
import mock_tables as mt  # noqa: E402

KINDS = {1: "collude", 2: "mid", 3: "compete"}  # level 1.0, 0.5, 0.0 along the penalty axis
THEORY = [("1.0", 0.1, 0.9), ("2", 0.2, 0.6), ("3", 0.3, 0.1)]  # "1.0" in the file matches penalty point "1"
ARMS = "^(chat|tacit)$"  # the mock arms stand in for the headline arms (default ^headline-)


def specs():
    out = []
    for th in ("off", "on"):
        for p in (1, 2, 3):
            for w in (0, 1):
                out.append(mt.spec(arm="chat", thinking=th, point=p, wording=w, seed=1 if th == "off" else 2, kind=KINDS[p],
                                   refuse_rounds=(3,) if (th == "on" and p == 1 and w == 0) else ()))
                out.append(mt.spec(arm="tacit", thinking=th, point=p, wording=w, seed=1 if th == "off" else 2, kind="compete"))
    return out


def write_theory(path):
    path.write_text("penalty_point,expected_penalty,theory_level\n" + "".join("%s,%s,%s\n" % t for t in THEORY),
                    encoding="utf-8", newline="")


class Fake:
    """Records every call so the drawing code can be checked without matplotlib."""
    def __init__(self, calls):
        self.calls = calls

    def __getattr__(self, name):
        def call(*a, **k):
            self.calls.append((name, a, k))
            if name == "subplots":
                n = k.get("ncols", a[1] if len(a) > 1 else 1)
                return Fake(self.calls), [[Fake(self.calls) for _ in range(n)]]
            return Fake(self.calls)
        return call


class Data(unittest.TestCase):
    def rows(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, specs())
            write_theory(Path(d) / "theory.csv")
            tables = am.load_tables(d)
            return ah.headline_rows(tables, mt.COMP, mt.COLL, ah.read_theory(Path(d) / "theory.csv"), 1, 10, boot=100, arms=ARMS)

    def test_levels_and_axis(self):
        rows = {(r["thinking"], r["arm"], r["penalty_point"], r["refusals"]): r for r in self.rows()}
        for th in ("off", "on"):
            self.assertEqual([rows[(th, "chat", str(p), "without")]["level"] for p in (1, 2, 3)], [1.0, 0.5, 0.0])
            self.assertEqual([rows[(th, "tacit", str(p), "with")]["level"] for p in (1, 2, 3)], [0.0, 0.0, 0.0])
            self.assertEqual([rows[(th, "chat", str(p), "with")]["x"] for p in (1, 2, 3)], [0.1, 0.2, 0.3])
            self.assertEqual([rows[(th, "theory", str(p), "with")]["level"] for p in (1, 2, 3)], [0.9, 0.6, 0.1])

    def test_with_and_without_refusal_rounds(self):
        rows = {(r["thinking"], r["arm"], r["penalty_point"], r["refusals"]): r for r in self.rows()}
        # thinking on, point 1: one of two games has a refused quote in round 3 (played at the competitive price)
        self.assertAlmostEqual(rows[("on", "chat", "1", "with")]["level"], 0.95)
        self.assertEqual(rows[("on", "chat", "1", "without")]["level"], 1.0)

    def test_refusal_rate_is_per_arm_and_thinking(self):
        rows = {(r["thinking"], r["arm"], r["penalty_point"], r["refusals"]): r for r in self.rows()}
        on = rows[("on", "chat", "1", "with")]
        self.assertEqual((on["refusal_count"], on["refusal_calls"]), (1, 120))  # 6 games x 20 quote calls
        self.assertAlmostEqual(on["refusal_rate"], 1 / 120)
        self.assertEqual(rows[("off", "chat", "1", "with")]["refusal_rate"], 0.0)
        self.assertEqual(rows[("on", "chat", "3", "with")]["refusal_rate"], on["refusal_rate"])  # one rate per curve
        self.assertEqual(rows[("on", "tacit", "1", "with")]["refusal_rate"], 0.0)
        self.assertEqual(rows[("on", "theory", "1", "with")]["refusal_rate"], "")


class Edges(unittest.TestCase):
    def test_refusal_rate_sums_every_kind(self):
        rows = [dict(arm="a", thinking="on", kind=k, refusals=str(n), calls=str(c)) for k, n, c in (("talk", 1, 10), ("quote", 2, 20), ("question", 0, 10))]
        self.assertEqual(ah.refusal_rates(rows), {("a", "on"): (3, 40)})

    def test_point_missing_from_theory_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, specs())
            with self.assertRaises(ValueError):
                ah.headline_rows(am.load_tables(d), mt.COMP, mt.COLL, {"1.0": (0.1, 0.9)}, 1, 10, boot=20, arms=ARMS)

    def test_assigned_basis_keeps_unpaired_games_and_no_refusals_table_gives_na(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, specs() + [mt.spec(arm="chat", thinking="off", point=1, wording=5, seed=7, kind="compete", rounds=3)])
            (Path(d) / "refusals.csv").unlink()
            tables = am.load_tables(d)
            TH = {ah._key(p): (x, lv) for p, x, lv in THEORY}
            win = ah.headline_rows(tables, mt.COMP, mt.COLL, TH, 1, 10, boot=20, arms=ARMS)
            asg = ah.headline_rows(tables, mt.COMP, mt.COLL, TH, 1, 10, basis="assigned", boot=20, arms=ARMS)
        n = lambda rows: [r["n_games"] for r in rows if (r["arm"], r["thinking"], r["penalty_point"], r["refusals"]) == ("chat", "off", "1", "with")]
        self.assertEqual((n(win), n(asg)), ([2], [3]))  # the short unpaired game only enters "as assigned"
        self.assertEqual([r["refusal_rate"] for r in asg if r["arm"] == "chat"][0], "")

    def test_percent_never_reads_zero_when_refusals_happened(self):
        self.assertEqual((ah.pct(0), ah.pct(0.0004), ah.pct(0.025), ah.pct("")), ("0%", "<0.1%", "2.5%", "n/a"))


class CiMethod(unittest.TestCase):
    def test_headline_rows_carry_ci_method_and_the_band_skips_points_without_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, specs())   # one game per wording and cell: the game-level fallback
            write_theory(Path(d) / "theory.csv")
            rows = ah.headline_rows(am.load_tables(d), mt.COMP, mt.COLL, ah.read_theory(Path(d) / "theory.csv"), 1, 10, boot=50, arms=ARMS)
        self.assertEqual({r["ci_method"] for r in rows if r["arm"] != "theory"}, {"game"})
        for r in rows:   # make one point of chat (thinking off) not estimable
            if (r["arm"], r["thinking"], r["penalty_point"]) == ("chat", "off", "2"):
                r["level_lo"] = r["level_hi"] = ""
        calls = []
        ah.draw(rows, "out.png", plt=Fake(calls))
        bands = [c for c in calls if c[0] == "fill_between"]
        self.assertEqual(len(bands), 4)                 # the arm keeps its band, with a gap at that point
        self.assertIn([True, False, True], [list(c[2].get("where", [])) for c in bands])


class Drawing(unittest.TestCase):
    def test_draw_with_a_recording_stand_in(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(d, specs())
            write_theory(Path(d) / "theory.csv")
            rows = ah.headline_rows(am.load_tables(d), mt.COMP, mt.COLL, ah.read_theory(Path(d) / "theory.csv"), 1, 10, boot=50, arms=ARMS)
        calls = []
        ah.draw(rows, "out.png", plt=Fake(calls))
        names = [c[0] for c in calls]
        self.assertEqual(names.count("plot"), 6)  # per panel: theory, chat, tacit; two panels (thinking off, on)
        self.assertEqual(names.count("fill_between"), 4)  # a band for each LLM curve
        plots = [c for c in calls if c[0] == "plot"]
        chat_on = next(c for c in plots if list(c[1][1]) == [0.95, 0.5, 0.0])
        self.assertEqual(list(chat_on[1][0]), [0.1, 0.2, 0.3])
        self.assertEqual(list(chat_on[1][1]), [0.95, 0.5, 0.0])
        self.assertIn("refusals 0.8%", chat_on[2]["label"])
        self.assertTrue(any(c[0] == "subplots" and c[2].get("squeeze") is False and c[2].get("sharey") for c in calls))
        self.assertTrue(any(c[0] == "text" and "transform" in c[2] for c in calls))
        self.assertTrue(any("thinking on" in str(c[1]) for c in calls if c[0] == "set_title"))
        notes = [str(c[1]) for c in calls if c[0] == "text"]
        self.assertTrue(any("Refusal rate" in n and "chat 0.8%" in n for n in notes), notes)
        self.assertEqual([c[1][0] for c in calls if c[0] == "savefig"], ["out.png"])

    def test_real_matplotlib_writes_a_png(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib is not installed")
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", specs())
            write_theory(Path(d) / "theory.csv")
            ah.main([str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4", "--theory",
                     str(Path(d) / "theory.csv"), "--window-end", "10", "--boot", "50", "--arms", ARMS])
            self.assertEqual((Path(d) / "o" / "headline.png").read_bytes()[:4], b"\x89PNG")


class Cli(unittest.TestCase):
    def test_csv_is_written_even_without_matplotlib(self):
        with tempfile.TemporaryDirectory() as d:
            mt.write_tables(Path(d) / "t", specs())
            write_theory(Path(d) / "theory.csv")
            args = [str(Path(d) / "t"), str(Path(d) / "o"), "--competitive", "2", "--collusive", "4", "--theory",
                    str(Path(d) / "theory.csv"), "--window-end", "10", "--boot", "50", "--arms", ARMS]
            code = ah.main(args + ["--no-png"])
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in (Path(d) / "o").iterdir()), ["headline_data.csv"])
            rows = list(csv.DictReader(open(Path(d) / "o" / "headline_data.csv", encoding="utf-8")))
            self.assertTrue(any(r["arm"] == "theory" and r["thinking"] == "on" for r in rows))
            self.assertNotIn(b"\r", (Path(d) / "o" / "headline_data.csv").read_bytes())


if __name__ == "__main__":
    unittest.main()
