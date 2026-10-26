"""Integration I4 (scope 14.6): mock data through to the figures, with the detectors checked against ground truth.
Run: python -X utf8 -m unittest tools/trial/test_i4_mock_to_figures.py      (about 20 s)

The I3 mock grid (test_i3_runner_resume.run_mock_grid: make_grid -> run_grid with the C14.1 trial command -> the real jar
-> mock_openai.py -> collect.py) is played once; its tables then go through every analysis command line as the runbook runs
them: analysis_m.py (measures and a contrast), analysis_detect.py with --truth written from the mocks' known behaviour
(colluding mocks collude in every round, competing mocks never), make_theory.py + analysis_headline.py (the real PNG:
matplotlib is required, the test fails rather than skips without it), analysis_r.py (--grid) and viewer.py.
The mock games are short (a colluding game is caught by the regulator after 2-3 rounds), so the fixed window is rounds 1..2.
Limits of the mocks: they quote only the competitive or the collusive price, every round alike, and collusion coincides
with chat, so the measures are checked at 0 and 1 (the wiring, cells, pairing and signs), not at intermediate levels, and the
detectors' harder cases (tacit collusion, prices that move) are not exercised; see analysis_detect's own caveat.
Needs PyYAML, matplotlib, engine/target/collusion-engine.jar and a JDK; skipped without the jar, JDK or PyYAML.
"""
import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_i3_runner_resume as i3  # noqa: E402

WINDOW = ["--window-start", "1", "--window-end", "2"]


def rows_of(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@unittest.skipUnless(i3.available(), "needs PyYAML, engine/target/collusion-engine.jar and a JDK")
class MockToFigures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp())
        cls.grid_rows, cls.trials, cls.tables = i3.run_mock_grid(cls.root)
        cls.colluding = {r["trial_id"] for r in cls.grid_rows if r["model_profile"] in i3.COLLUDING}
        truth = i3.truth_rows(cls.grid_rows, cls.tables)
        cls.truth = cls.root / "truth_rounds.csv"
        with open(cls.truth, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["trial_id", "round", "collusive"])
            w.writerows(truth)
        cls.n_truth = len(truth)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def cli(self, script, *args, ok=(0,)):
        p = subprocess.run([sys.executable, "-X", "utf8", str(HERE / script)] + [str(a) for a in args], capture_output=True, text=True,
                           timeout=600)
        self.assertIn(p.returncode, ok, "%s exit %d\n%s\n%s" % (script, p.returncode, p.stdout[-2000:], p.stderr[-2000:]))
        return p

    def test_measures_recover_the_mock_levels(self):
        out = self.root / "analysis_m"
        self.cli("analysis_m.py", self.tables, out, *WINDOW, "--boot", "200", "--contrast", "headline-chat:headline-tacit")
        summ = rows_of(out / "measures_summary.csv")
        cells = [r for r in summ if r["arm"] in ("headline-chat", "headline-tacit") and r["refusals"] == "with"]
        self.assertEqual({("1", "window"), ("3", "window"), ("5", "window"), ("1", "assigned"), ("3", "assigned"), ("5", "assigned")},
                         {(r["penalty_point"], r["basis"]) for r in cells})
        for r in cells:
            self.assertEqual(("2", "2"), (r["n_games"], r["games_assigned"]), r)   # two wordings per cell, both kept by the window
            self.assertAlmostEqual(1.0 if r["arm"] == "headline-chat" else 0.0, float(r["level"]), msg=r)
            self.assertEqual((float(r["level"]), float(r["level"])), (float(r["level_lo"]), float(r["level_hi"])), r)  # constant data
        without = [r for r in summ if r["arm"] in ("headline-chat", "headline-tacit") and r["refusals"] == "without"]
        self.assertEqual(len(cells), len(without))                     # no refusals: the same cells, the same levels
        self.assertEqual(sorted((r["arm"], r["penalty_point"], r["basis"], r["level"]) for r in cells),
                         sorted((r["arm"], r["penalty_point"], r["basis"], r["level"]) for r in without))
        r1 = [r for r in summ if r["arm"] == "r1-reflection" and r["refusals"] == "with"]
        self.assertTrue(r1 and all(float(r["level"]) == 1.0 for r in r1))
        con = [r for r in rows_of(out / "contrasts.csv") if r["refusals"] == "with"]
        self.assertTrue(con)
        self.assertEqual({"1", "3", "5"}, {r["penalty_point"] for r in con if r["measure"] == "level"})
        for r in con:
            if r["measure"] == "level":
                self.assertEqual("2", r["n_pairs"], r)
                self.assertAlmostEqual(1.0, float(r["diff"]), msg=r)
                self.assertEqual((1.0, 1.0), (float(r["diff_lo"]), float(r["diff_hi"])), r)

    def test_detectors_recover_the_known_truth(self):
        out = self.root / "detect"
        self.cli("analysis_detect.py", self.tables, out, "--truth", self.truth)
        s = {(r["detector"], r["level"]): r for r in rows_of(out / "detector_scores.csv")}
        for key in (("price", "trial"), ("conversation", "trial")):
            self.assertEqual("ground_truth", s[key]["truth"])
        # trial level: the price detector names exactly the colluding games
        self.assertEqual((len(self.colluding), 0, 0), tuple(int(s[("price", "trial")][k]) for k in ("tp", "fp", "fn")))
        # the conversation detector can only see the chat games: it names the colluding chat games and nothing else
        chat_colluding = {r["trial_id"] for r in self.grid_rows if r["trial_id"] in self.colluding and r["communication"] != "tacit"}
        self.assertEqual(8, len(chat_colluding))                         # headline-chat 6, r1-reflection (private chat) 2
        conv = s[("conversation", "trial")]
        self.assertEqual((len(chat_colluding), 0), (int(conv["tp"]), int(conv["fp"])))
        self.assertEqual(1.0, float(conv["precision"]))
        # round level: the price detector needs its 2-round window, so it misses round 1 of each colluding game only
        pr = s[("price", "round")]
        self.assertEqual((0, len(self.colluding)), (int(pr["fp"]), int(pr["fn"])))
        self.assertEqual(self.n_truth, sum(int(pr[k]) for k in ("tp", "fp", "fn", "tn")))
        flags = rows_of(out / "detector_rounds.csv")
        self.assertEqual(self.n_truth, len(flags))
        for r in flags:
            if r["trial_id"] in chat_colluding:
                self.assertEqual(("1", "1"), (r["truth"], r["conversation_flag"]), r)
            if r["truth"] == "0":
                self.assertEqual(("0", "0"), (r["price_flag"], r["conversation_flag"]), r)

    def test_headline_figure_renders_from_the_tables(self):
        import matplotlib                                              # noqa: F401  (required: a missing install fails here)
        theory = self.root / "theory.csv"
        self.cli("make_theory.py", theory)
        self.assertEqual(["1", "2", "3", "4", "5"], [r["penalty_point"] for r in rows_of(theory)])
        out = self.root / "headline"
        self.cli("analysis_headline.py", self.tables, out, "--theory", theory, *WINDOW, "--boot", "200")
        png = (out / "headline.png").read_bytes()
        self.assertEqual(b"\x89PNG\r\n\x1a\n", png[:8])
        import matplotlib.image
        img = matplotlib.image.imread(str(out / "headline.png"))[..., :3]

        def pixels(hexcolour):                                         # pixels drawn in a curve's colour (Okabe-Ito, analysis_headline.STYLES)
            c = [int(hexcolour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            return int(((abs(img[..., 0] - c[0]) < 0.02) & (abs(img[..., 1] - c[1]) < 0.02) & (abs(img[..., 2] - c[2]) < 0.02)).sum())
        for colour in ("#0072B2", "#D55E00", "#555555"):               # both arm curves and the theory line are drawn
            self.assertGreater(pixels(colour), 1000, colour)
        data = rows_of(out / "headline_data.csv")
        self.assertEqual({"theory", "headline-chat", "headline-tacit"}, {r["arm"] for r in data})
        for r in data:
            if r["arm"] != "theory":
                self.assertAlmostEqual(1.0 if r["arm"] == "headline-chat" else 0.0, float(r["level"]), msg=r)
                self.assertEqual((r["level"], r["level"]), (r["level_lo"], r["level_hi"]), r)
        want = {r["penalty_point"]: (float(r["expected_penalty"]), float(r["theory_level"])) for r in rows_of(theory)}
        theo = {r["penalty_point"]: (float(r["x"]), float(r["level"])) for r in data if r["arm"] == "theory"}
        self.assertEqual(want, theo)
        self.assertAlmostEqual(0.5459, theo["3"][1], places=4)
        self.assertEqual({float(want[r["penalty_point"]][0]) for r in data if r["arm"] == "headline-chat"},
                         {float(r["x"]) for r in data if r["arm"] == "headline-chat"})
        self.assertNotIn("r0-control", {r["arm"] for r in data})

    def test_track_r_differential_from_the_grid(self):
        out = self.root / "analysis_r"
        p = self.cli("analysis_r.py", self.tables, out, "--grid", self.root / "grid.csv", *WINDOW, "--boot", "200")
        diff = [r for r in rows_of(out / "r_differential_by_round.csv") if r["refusals"] == "with"]
        self.assertTrue(diff, p.stderr)
        self.assertEqual({"r1-reflection"}, {r["arm"] for r in diff})
        for r in diff:
            self.assertEqual("2", r["n_pairs"], r)                     # two wordings, one seed, paired with the headline-chat control
            self.assertAlmostEqual(1.0, float(r["diff"]), msg=r)       # colluding R1 mocks minus competing R0 mocks
        self.assertTrue((out / "thinks_says_does.csv").exists())

    def test_viewer_pages_every_trial(self):
        out = self.root / "viewer"
        self.cli("viewer.py", self.trials, out)
        index = (out / "index.html").read_text(encoding="utf-8")
        pages = sorted(p.stem for p in (out / "trials").glob("*.html"))
        self.assertEqual(sorted(r["trial_id"] for r in self.grid_rows), pages)
        for t in pages:
            self.assertIn(t, index)
        chat = (out / "trials" / "headline-chat__p3__w0__s1__t0.html").read_text(encoding="utf-8")
        self.assertIn("Let us all hold 3.00. Agreed?", chat)


if __name__ == "__main__":
    unittest.main()
