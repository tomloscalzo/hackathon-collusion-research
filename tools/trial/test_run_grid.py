"""Tests for run_grid.py (C8.1; later C8.2, C8.3). Run: python -X utf8 -m unittest tools/trial/test_run_grid.py

The game command is a stub: a small Python program that appends a line to a log, writes events.jsonl and obeys per-trial
instructions in the trial id (FAILONCE: fail on the first call; FAILALWAYS: always fail). No LLM, no network.
"""
import csv
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid  # noqa: E402

STUB = r'''
import sys, pathlib, os
trial_dir, trial_id, log = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
with open(log, "a") as f:
    f.write(trial_id + "\n")
n = sum(1 for l in open(log) if l.strip() == trial_id)
if "failalways" in trial_id or ("failonce" in trial_id and n == 1):
    print("boom for " + trial_id, file=sys.stderr)
    sys.exit(3)
(trial_dir / "events.jsonl").write_text("{}\n")
print("secret-free output")
'''


def make_rows(*specs):
    """specs: (arm, wave, name) -> grid rows with the columns the runner needs."""
    return [{"trial_id": "%s__p1__w0__s%s__t0" % (arm, name), "arm": arm, "wave": str(wave), "seed": name, "thinking": "0"}
            for arm, wave, name in specs]


class RunGridTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.stub = self.root / "stub.py"
        self.stub.write_text(STUB, encoding="utf-8")
        self.log = self.root / "calls.log"
        self.out = self.root / "trials"
        self.cmd = [sys.executable, str(self.stub), "{trial_dir}", "{trial_id}", str(self.log)]

    def calls(self):
        return self.log.read_text().split() if self.log.exists() else []

    def run_it(self, rows, **kw):
        kw.setdefault("max_concurrency", 2)
        return run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd), **kw)

    def tdir(self, row):
        return self.out / row["arm"] / row["trial_id"]

    def test_success_writes_done_row_and_log(self):
        rows = make_rows(("a", 1, "1"), ("b", 1, "2"))
        res = self.run_it(rows)
        self.assertEqual({"done": 2}, res["counts"])
        for r in rows:
            d = self.tdir(r)
            self.assertTrue((d / "DONE").exists() and not (d / "FAILED").exists())
            self.assertEqual(r["trial_id"], json.loads((d / "grid_row.json").read_text())["trial_id"])
            self.assertIn("secret-free output", (d / "console.log").read_text())
            self.assertTrue((d / "events.jsonl").exists())

    def test_one_retry_then_done(self):
        rows = make_rows(("a", 1, "failonce"))
        res = self.run_it(rows)
        self.assertEqual({"done": 1}, res["counts"])
        self.assertEqual(2, len(self.calls()))
        self.assertEqual(2, res["results"][0]["attempts"])
        self.assertFalse((self.tdir(rows[0]) / "FAILED").exists())

    def test_failure_after_one_retry_writes_failed_with_reason(self):
        rows = make_rows(("a", 1, "failalways"))
        res = self.run_it(rows)
        self.assertEqual({"failed": 1}, res["counts"])
        self.assertEqual(2, len(self.calls()))                 # exactly one retry
        d = self.tdir(rows[0])
        self.assertFalse((d / "DONE").exists())
        reason = (d / "FAILED").read_text()
        self.assertIn("exit code 3", reason)
        self.assertIn("boom for", reason)

    def test_resume_skips_done_and_reruns_the_rest(self):
        rows = make_rows(("a", 1, "1"), ("a", 1, "failalways"), ("a", 1, "3"))
        self.run_it(rows, max_concurrency=1)
        first = self.calls()
        self.assertEqual(4, len(first))                         # 1, 3 once; failalways twice
        incomplete = self.tdir(rows[2])                          # simulate a kill: no marker on trial 3
        (incomplete / "DONE").unlink()
        res = self.run_it(rows, max_concurrency=1)
        again = self.calls()[len(first):]
        self.assertEqual(sorted([rows[1]["trial_id"]] * 2 + [rows[2]["trial_id"]]), sorted(again))
        self.assertEqual({"done": 1, "failed": 1}, res["counts"])
        self.assertEqual(1, res["skipped"])
        self.assertTrue((incomplete / "DONE").exists())

    def test_waves_and_order(self):
        rows = make_rows(("a", 2, "1"), ("a", 1, "2"), ("a", 1, "3"))
        self.run_it(rows, waves={1}, max_concurrency=1)
        self.assertEqual([rows[1]["trial_id"], rows[2]["trial_id"]], self.calls())
        self.assertFalse(self.tdir(rows[0]).exists())
        self.run_it(rows, max_concurrency=1)                    # wave 2 now; the wave 1 trials are skipped
        self.assertEqual(rows[0]["trial_id"], self.calls()[-1])
        self.assertEqual(3, len(self.calls()))

    def test_arm_filter_and_limit(self):
        rows = make_rows(("a", 1, "1"), ("b", 1, "2"), ("b", 1, "3"))
        self.run_it(rows, arms={"b"}, limit=1, max_concurrency=1)
        self.assertEqual([rows[1]["trial_id"]], self.calls())

    def test_concurrency_never_exceeds_max(self):
        live, peak, lock = [0], [0], threading.Lock()

        class Slow:
            def run(self, row, trial_dir, timeout=None):
                with lock:
                    live[0] += 1
                    peak[0] = max(peak[0], live[0])
                time.sleep(0.05)
                with lock:
                    live[0] -= 1
                return run_grid.Result(0, "")

        rows = make_rows(*[("a", 1, str(i)) for i in range(8)])
        res = run_grid.run_grid(rows, self.out, Slow(), max_concurrency=3)
        self.assertEqual({"done": 8}, res["counts"])
        self.assertEqual(3, peak[0])

    def test_command_construction_has_no_shell_and_fills_columns(self):
        row = {"trial_id": "a b__p1", "arm": "a", "wave": "1", "model_profile": "m;rm -rf x"}
        argv = run_grid.build_command(["game", "--p", "{model_profile}", "{trial_dir}/x"], row, Path("T"))
        self.assertEqual(["game", "--p", "m;rm -rf x", "T/x"], argv)       # one argument each, never a shell string
        with self.assertRaises(ValueError):
            run_grid.build_command(["{nope}"], row, Path("T"))

    def test_bad_template_fails_up_front_without_running_anything(self):
        rows = make_rows(("a", 1, "1"), ("a", 1, "2"))
        for tmpl in (["x", "{nope}"], ["x", "{}"], ["x", "{0}"], ["x", "{seed.real}"], ["x", "{"], ["x", '{"a": 1}']):
            with self.assertRaises(ValueError, msg=str(tmpl)):
                run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(tmpl), max_concurrency=1)
        self.assertFalse(self.out.exists())
        self.assertEqual(["x", '{"a": 1}'], run_grid.build_command(["x", '{{"a": 1}}'], rows[0], Path("T")))

    def test_grid_validation(self):
        good = make_rows(("a", 1, "1"))
        cases = [good + good]
        for key, val in (("trial_id", "../x"), ("arm", "a/b"), ("wave", ""), ("wave", "x"), ("arm", "")):
            r = dict(good[0])
            r[key] = val
            cases.append([r])
        for rows in cases:
            with self.assertRaises(ValueError):
                run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd))
        self.assertFalse(self.out.exists())

    def test_stale_markers_are_cleared_and_done_records_attempts(self):
        rows = make_rows(("a", 1, "1"))
        d = self.tdir(rows[0])
        d.mkdir(parents=True)
        (d / "FAILED").write_text("old")
        self.run_it(rows)
        self.assertFalse((d / "FAILED").exists())
        self.assertEqual("attempts 1", (d / "DONE").read_text().strip())

    def test_retry_runs_in_the_same_directory_and_keeps_files(self):
        rows = make_rows(("a", 1, "failonce"))
        d = self.tdir(rows[0])
        d.mkdir(parents=True)
        (d / "cache.jsonl").write_text("kept")
        self.run_it(rows)
        self.assertEqual("kept", (d / "cache.jsonl").read_text())

    def test_metacharacters_reach_the_process_as_one_argument(self):
        rows = make_rows(("a", 1, "1"))
        rows[0]["model_profile"] = "x; echo pwned & y"
        dump = self.root / "argv.txt"
        prog = "import sys; open(sys.argv[1], 'w').write(sys.argv[2])"
        run_grid.run_grid(rows, self.out, run_grid.LocalExecutor([sys.executable, "-c", prog, str(dump), "{model_profile}"]), max_concurrency=1)
        self.assertEqual("x; echo pwned & y", dump.read_text())

    def test_timeout_kills_grandchildren(self):
        flag = self.root / "grandchild.txt"
        child = "import time; time.sleep(3); open(%r, 'w').write('alive')" % str(flag)
        parent = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', %r]); time.sleep(30)" % child
        res = run_grid.run_grid(make_rows(("a", 1, "1")), self.out, run_grid.LocalExecutor([sys.executable, "-c", parent]),
                                max_concurrency=1, timeout=1)
        self.assertEqual({"failed": 1}, res["counts"])
        time.sleep(4)
        self.assertFalse(flag.exists())

    def test_load_grid_and_cli(self):
        rows = make_rows(("a", 1, "1"), ("a", 1, "2"))
        grid = self.root / "grid.csv"
        with open(grid, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        self.assertEqual(rows, run_grid.load_grid(grid))
        grid.write_bytes(b"\xef\xbb\xbf" + grid.read_bytes())                          # a BOM (Excel) does not rename the first column
        self.assertEqual(rows, run_grid.load_grid(grid))
        self.assertEqual(2, run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out)]))   # no command
        code = run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--max-concurrency", "2", "--"] + self.cmd)
        self.assertEqual(0, code)
        self.assertEqual(2, len(list(self.out.rglob("DONE"))))
        bad = make_rows(("a", 1, "failalways"))
        with open(grid, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(bad[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(bad)
        self.assertEqual(1, run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--"] + self.cmd))

    def test_timeout_is_a_failure(self):
        sleeper = [sys.executable, "-c", "import time; time.sleep(30)"]
        res = run_grid.run_grid(make_rows(("a", 1, "1")), self.out, run_grid.LocalExecutor(sleeper), max_concurrency=1, timeout=1)
        self.assertEqual({"failed": 1}, res["counts"])
        self.assertIn("timed out", (self.out / "a" / "a__p1__w0__s1__t0" / "FAILED").read_text())


if __name__ == "__main__":
    unittest.main()
