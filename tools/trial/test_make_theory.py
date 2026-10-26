"""Tests for make_theory.py (C1.4). Run: python -X utf8 -m unittest tools/trial/test_make_theory.py"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline  # noqa: E402
import make_theory  # noqa: E402


def cfg(fine=500, slope=0.025, rho_coop=1.0, rho_tip=0.0, d_bar_u=0.0, s0=1.0, s_bar=5.0, tick=0.0, scale="ABSOLUTE_MARKUP", kind="LEVEL"):
    return {"market": {"s0": s0, "sBar": s_bar, "tick": tick},
            "enforcement": {"screen": {"kind": kind, "scale": scale, "slope": slope}, "rhoTip": rho_tip, "rhoCoop": rho_coop, "fine": fine},
            "aggregates": {"dBarU": d_bar_u}}


class ExpectedPenalty(unittest.TestCase):
    def test_hand_calculation_ripe_baseline(self):
        # MODEL_SPEC worked baseline: rho_screen = 0.025 * (3 - 1) = 0.05 at theta 1, evidence 1, so rho F = 0.05 * 500 = 25.
        self.assertAlmostEqual(make_theory.expected_penalty(cfg()), 25.0)

    def test_hand_calculation_other_fine(self):
        self.assertAlmostEqual(make_theory.expected_penalty(cfg(fine=2000)), 100.0)

    def test_evidence_and_tip(self):
        # screen 0.05; tip 0.1 -> trigger 1-0.95*0.9 = 0.145; evidence 1-(1-0.2)(1-0.5) = 0.6; fine 1000 -> 87.0
        self.assertAlmostEqual(make_theory.expected_penalty(cfg(fine=1000, rho_tip=0.1, rho_coop=0.5, d_bar_u=0.2)), 87.0)

    def test_ci_scale_and_cap(self):
        self.assertAlmostEqual(make_theory.expected_penalty(cfg(scale="CI", slope=0.5, fine=10)), 5.0)
        self.assertAlmostEqual(make_theory.expected_penalty(cfg(slope=5.0, fine=10)), 10.0)  # min(1, 5 * 2)

    def test_default_scale_and_other_span(self):
        c = cfg(s0=2.0, s_bar=10.0, fine=100)  # margin above Nash (2+10)/2 - 2 = 4, rho_screen 0.1
        self.assertAlmostEqual(make_theory.expected_penalty(c), 10.0)
        del c["enforcement"]["screen"]["scale"]
        self.assertAlmostEqual(make_theory.expected_penalty(c), 10.0)
        del c["aggregates"]
        self.assertAlmostEqual(make_theory.expected_penalty(c), 10.0)

    def test_unsupported(self):
        with self.assertRaises(ValueError):
            make_theory.expected_penalty(cfg(tick=0.1))
        with self.assertRaises(ValueError):
            make_theory.expected_penalty(cfg(kind="CHANGE"))


class Files(unittest.TestCase):
    def test_real_slice_files(self):
        rows = make_theory.theory_rows()
        self.assertEqual([r["penalty_point"] for r in rows], [1, 2, 3, 4, 5])
        self.assertEqual([float(r["expected_penalty"]) for r in rows], [5.0, 15.0, 25.0, 50.0, 100.0])
        self.assertEqual([r["theory_level"] for r in rows], ["0.7029", "0.6262", "0.5459", "0.3249", "0.0000"])

    def test_track_m_twins_give_the_same_rows(self):
        self.assertEqual(make_theory.theory_rows(), make_theory.theory_rows(prefix="slice-m-p"))
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            self.assertEqual(make_theory.main(["make_theory.py", str(a)]), 0)
            self.assertEqual(make_theory.main(["make_theory.py", str(b), "--prefix", "slice-m-p"]), 0)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(make_theory.main(["make_theory.py", str(b), "--prefix", "other"]), 2)
            self.assertEqual(make_theory.main(["make_theory.py", str(b), "--prefix"]), 2)

    def test_cli_output_feeds_headline_reader(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "theory.csv"
            self.assertEqual(make_theory.main(["make_theory.py", str(out)]), 0)
            raw = out.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertEqual(next(csv.reader(raw.decode().splitlines())), ["penalty_point", "expected_penalty", "theory_level"])
            theory = analysis_headline.read_theory(str(out))
            self.assertEqual(theory[analysis_headline._key("3")], (25.0, 0.5459))
            self.assertEqual(theory[analysis_headline._key("5")], (100.0, 0.0))

    def test_bad_usage_and_missing_dir(self):
        self.assertEqual(make_theory.main(["make_theory.py"]), 2)
        self.assertEqual(make_theory.main(["make_theory.py", "x.csv", "--scenarios"]), 2)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(make_theory.main(["make_theory.py", str(Path(d) / "t.csv"), "--scenarios", str(Path(d) / "none")]), 2)


if __name__ == "__main__":
    unittest.main()
