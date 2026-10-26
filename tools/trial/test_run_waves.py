"""Tests for run_waves.py (C8.4) with a stub game command. No LLM, no Modal, no network.
Run: python -X utf8 -m unittest tools/trial/test_run_waves.py"""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_waves  # noqa: E402

# The stub logs "<wave> <trial_id>" and writes one quote event of 1,000,000 input tokens: $1 at token_price_per_million_in 1.
STUB = r'''
import sys, pathlib, json
trial_dir, trial_id, wave, log = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
open(log, "a").write(wave + " " + trial_id + "\n")
if "bad" in trial_id:
    sys.exit(3)
(trial_dir / "events.jsonl").write_text(json.dumps({"kind": "quote", "round": 1, "tokens_in": 1000000, "tokens_out": 0}) + "\n")
'''


def grid(path, spec):
    """spec: list of (arm, wave, n_trials)."""
    rows = [{"trial_id": "%s__p1__w0__s%d__t0" % (arm, i), "arm": arm, "wave": str(w), "seed": str(i), "thinking": "0"}
            for arm, w, n in spec for i in range(n)]
    with open(path, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, list(rows[0]), lineterminator=chr(10))
        wr.writeheader()
        wr.writerows(rows)


class RunWavesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r = Path(self.tmp.name)
        (r / "stub.py").write_text(STUB, encoding="utf-8")
        self.log, self.out, self.grid = r / "calls.log", r / "trials", r / "grid.csv"
        (r / "cost.json").write_text(json.dumps({"token_price_per_million_in": 1}), encoding="utf-8")
        self.cfg = str(r / "cost.json")
        self.cmd = ["--", sys.executable, str(r / "stub.py"), "{trial_dir}", "{trial_id}", "{wave}", str(self.log)]

    def go(self, *opts, spec=(("a", 2, 2), ("b", 1, 2), ("c", 0, 1))):
        if not self.grid.exists():
            grid(self.grid, spec)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_waves.main(["run_waves.py", "--grid", str(self.grid), "--out", str(self.out), "--config", self.cfg,
                                   "--max-concurrency", "1", *opts, *self.cmd])
        return code, out.getvalue(), err.getvalue()

    def waves_run(self):
        return [l.split()[0] for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_waves_run_in_ascending_order_and_all_trials_finish(self):
        code, out, _ = self.go("--stop-line", "100")
        self.assertEqual(0, code)
        self.assertEqual(["0", "1", "1", "2", "2"], self.waves_run())
        self.assertIn("all selected waves done", out)

    def test_dry_run_prints_plan_and_runs_nothing(self):
        code, out, _ = self.go("--stop-line", "100", "--dry-run")
        self.assertEqual(0, code)
        self.assertFalse(self.log.exists())
        self.assertFalse(self.out.exists())
        for w, n in ((0, 1), (1, 2), (2, 2)):
            self.assertIn("wave %d: %d trials, 0 done, %d to run" % (w, n, n), out)
        self.assertIn("projected for this wave unknown", out)

    def test_dry_run_after_a_run_shows_spend_and_projection(self):
        self.go("--stop-line", "100", "--waves", "0,1")
        code, out, _ = self.go("--stop-line", "100", "--dry-run")
        self.assertIn("wave 1: 2 trials, 2 done, 0 to run; spent so far $3.00", out)
        self.assertIn("wave 2: 2 trials, 0 done, 2 to run; spent so far $3.00, projected for this wave $2.00; ok", out)

    def test_stop_line_between_waves_stops_with_status_5(self):
        code, out, _ = self.go("--stop-line", "3.5")          # wave 0 ($1) + wave 1 ($2) = $3; wave 2 would project $2 more
        self.assertEqual(5, code)
        self.assertIn("STOP LINE before wave 2", out)
        self.assertEqual(["0", "1", "1"], self.waves_run())

    def test_dry_run_flags_the_wave_that_would_stop(self):
        self.go("--stop-line", "100", "--waves", "0,1")
        code, out, _ = self.go("--stop-line", "3.5", "--dry-run")
        self.assertEqual(0, code)
        self.assertIn("WOULD STOP", out)

    def test_raising_the_line_and_rerunning_continues_without_redoing(self):
        self.go("--stop-line", "3.5")
        code, out, _ = self.go("--stop-line", "100")
        self.assertEqual(0, code)
        self.assertEqual(["0", "1", "1", "2", "2"], self.waves_run())           # nothing run twice
        self.assertIn("wave 0: nothing to run", out)

    def test_spent_already_over_the_line_stops_before_the_first_new_wave(self):
        self.go("--stop-line", "100", "--waves", "0,1")
        code, out, _ = self.go("--stop-line", "3")
        self.assertEqual(5, code)
        self.assertIn("has reached the stop line", out)

    def test_waves_filter(self):
        self.assertEqual(0, self.go("--stop-line", "100", "--waves", "1")[0])
        self.assertEqual(["1", "1"], self.waves_run())

    def test_failed_wave_stops_the_run_with_runs_status(self):
        code, out, _ = self.go("--stop-line", "100", spec=(("a", 2, 1), ("bad", 1, 1)))
        self.assertEqual(1, code)
        self.assertEqual(["1", "1"], self.waves_run())                           # the failing trial and its retry; wave 2 never starts
        self.assertIn("wave 1 ended with run_grid status 1", out)

    def test_stage_cap_in_config_still_applies_inside_a_wave(self):
        Path(self.cfg).write_text(json.dumps({"token_price_per_million_in": 1, "stage_cap_usd": 1}), encoding="utf-8")
        code, out, _ = self.go("--stop-line", "100", spec=(("a", 1, 3),))
        self.assertEqual(3, code)                                               # run_grid's stop rule
        self.assertEqual(1, len(self.waves_run()))

    def test_stage_cap_is_checked_across_waves(self):
        Path(self.cfg).write_text(json.dumps({"token_price_per_million_in": 1, "stage_cap_usd": 2}), encoding="utf-8")
        code, out, _ = self.go("--stop-line", "100", spec=(("a", 1, 1), ("b", 2, 1), ("c", 3, 1)))
        self.assertEqual(5, code)                                               # each wave alone is under the cap; the total is not
        self.assertIn("stage cap", out)
        self.assertEqual(["1", "2"], self.waves_run())

    def test_warning_when_the_config_prices_nothing(self):
        Path(self.cfg).write_text("{}", encoding="utf-8")
        code, _, err = self.go("--stop-line", "1", "--dry-run")
        self.assertIn("spend is always $0", err)

    def test_arm_filter_limits_plan_and_run(self):
        code, out, _ = self.go("--stop-line", "100", "--arm", "b")
        self.assertEqual(0, code)
        self.assertEqual(["1", "1"], self.waves_run())

    def test_wave_and_limit_passthrough_and_unknown_wave_rejected(self):
        for extra in (("--wave", "1"), ("--limit", "1"), ("--wave=2",)):
            self.assertEqual(2, self.go("--stop-line", "1", *extra)[0], extra)
        self.assertEqual(2, self.go("--stop-line", "1", "--waves", "9")[0])
        self.assertFalse(self.log.exists())

    def test_usage_errors(self):
        self.assertEqual(2, run_waves.main(["run_waves.py", "--grid", "x", "--out", "y", "--stop-line", "1"]))
        code, _, err = self.go("--stop-line", "-1")
        self.assertEqual(2, code)
        self.assertEqual(2, self.go("--stop-line", "1", "--waves", "x")[0])


if __name__ == "__main__":
    unittest.main()
