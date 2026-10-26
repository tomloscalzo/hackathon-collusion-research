"""Tests for runs_registry.py (U5). Run: python -X utf8 -m unittest tools/trial/test_runs_registry.py"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runs_registry as rr  # noqa: E402


def w(path, text="", obj=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if obj is not None else text, encoding="utf-8")


def trial(root, arm, name, marker=None, thinking=False, commit="abc1234", model="m1"):
    d = root / arm / name
    w(d / "params.json", obj={"arm": arm, "thinking": thinking, "model": model, "code_commit": commit})
    if marker:
        w(d / marker, "attempts 1" if marker == "DONE" else "boom")
    return d


class NameParsing(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(rr.parse_name("2026-10-24_m_pilot"), ("2026-10-24", "m", "pilot"))
        self.assertEqual(rr.parse_name("2026-10-24_s_stage0-big"), ("2026-10-24", "s", "stage0-big"))

    def test_legacy(self):
        self.assertEqual(rr.parse_name("trackm-smoke-t1b"), ("", "m", "smoke-t1b"))
        self.assertEqual(rr.parse_name("tracks-myopic-t1-32b"), ("", "s", "myopic-t1-32b"))
        self.assertEqual(rr.parse_name("hc"), ("", "", "hc"))


class Scan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_superseded_originals_not_counted(self):
        root = self.runs / "2026-10-25_m_orig"
        trial(root, "a1", "a1__p3__w0__s1__t0", "FAILED")
        trial(root, "a1", "a1__p3__w0__s2__t0", "DONE")
        w(root / "superseded.csv", "original_id,rerun_id,reason" + chr(10) + "a1__p3__w0__s1__t0,a1__p3__w0__s1__t0__x32k,truncated" + chr(10))
        r = rr.scan(self.runs)[0]
        self.assertEqual((r["done"], r["failed"], r["trials"], r["status"]), (1, 0, 1, "complete"))

    def test_track_m_root(self):
        root = self.runs / "2026-10-24_m_pilot"
        trial(root, "a1", "a1__p3__w0__s1__t0", "DONE", False, "c1", "mod")
        trial(root, "a1", "a1__p3__w0__s2__t1", "DONE", True, "c2", "mod")
        trial(root, "a2", "a2__p3__w0__s1__t1", "FAILED", True, "c2", "mod2")
        trial(root, "a2", "a2__p3__w0__s2__t1", None, True, "c2", "mod2")  # unfinished
        w(root / "cost.json", obj={"spent_usd": 12.5})
        rows = rr.scan(self.runs)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["date"], r["track"], r["stage"]), ("2026-10-24", "m", "pilot"))
        self.assertEqual(r["arms"], "a1;a2")
        self.assertEqual(r["model"], "mod;mod2")
        self.assertEqual(r["thinking"], "off;on")
        self.assertEqual(r["commits"], "c1;c2")
        self.assertEqual((r["done"], r["failed"], r["trials"]), (2, 1, 4))
        self.assertEqual(r["cost_usd"], "12.50")
        self.assertEqual(r["status"], "has-failures")
        self.assertEqual(r["path"], "2026-10-24_m_pilot")

    def test_complete_and_failed_status(self):
        a = self.runs / "2026-10-24_m_a"
        trial(a, "x", "x__1", "DONE")
        b = self.runs / "2026-10-24_m_b"
        trial(b, "x", "x__1", "DONE")
        trial(b, "x", "x__2", "FAILED")
        c = self.runs / "2026-10-24_m_c"
        trial(c, "x", "x__1", "DONE")
        trial(c, "x", "x__2")
        st = {r["stage"]: r["status"] for r in rr.scan(self.runs)}
        self.assertEqual(st, {"a": "complete", "b": "has-failures", "c": "incomplete"})

    def test_trials_subdir_layout(self):
        root = self.runs / "trackm-smoke"
        trial(root / "trials", "smoke-a", "smoke-a__p3__w0__s1__t0", "DONE")
        w(root / "grid.csv", "x\n")
        w(root / "tables" / "trials.csv", "x\n")
        r = rr.scan(self.runs)[0]
        self.assertEqual((r["track"], r["stage"], r["done"], r["arms"]), ("m", "smoke", 1, "smoke-a"))

    def test_track_s_root(self):
        root = self.runs / "tracks-t0"
        line = {"arm": "competitive", "seed": 1, "llm": {"arm": "competitive", "model": "mm", "thinking": False}}
        w(root / "stage0" / "competitive_p0_s1.jsonl", json.dumps(line) + "\n" + json.dumps(dict(line, seed=2)) + "\n")
        w(root / "stage0" / "competitive_p0_s1.jsonl.cache.jsonl", "{}\n")
        w(root / "stage0" / "competitive_p0_s1.jsonl.manifest.json", obj={"gitCommit": "deadbee"})
        w(root / "stage0" / "other_p0_s1.jsonl.partial-123", "x")
        w(root / "stage0" / "collusion-engine.jar", "bin")
        r = rr.scan(self.runs)[0]
        self.assertEqual((r["track"], r["stage"]), ("s", "t0"))
        self.assertEqual((r["done"], r["failed"]), (2, 1))
        self.assertEqual((r["arms"], r["model"], r["thinking"], r["commits"]), ("competitive", "mm", "off", "deadbee"))

    def test_tolerant_of_junk(self):
        w(self.runs / "hc_models.json", "{}")
        w(self.runs / "hc_deploy.log", "x")
        (self.runs / "empty").mkdir()
        w(self.runs / "bad" / "t" / "t1" / "params.json", "{not json")
        w(self.runs / "bad" / "t" / "t1" / "DONE", "x")
        w(self.runs / "bad" / "cost.json", "garbage")
        rows = rr.scan(self.runs)
        self.assertEqual({r["path"] for r in rows}, {"empty", "bad"})
        bad = [r for r in rows if r["path"] == "bad"][0]
        self.assertEqual((bad["done"], bad["cost_usd"]), (1, ""))
        self.assertEqual([r for r in rows if r["path"] == "empty"][0]["status"], "empty")

    def test_missing_dir(self):
        self.assertEqual(rr.scan(self.runs / "nope"), [])

    def test_write_files_and_cost_variants(self):
        root = self.runs / "2026-10-24_m_x"
        trial(root, "x", "x__1", "DONE")
        w(root / "meter.json", obj={"total_usd": 3})
        rr.write(self.runs, rr.scan(self.runs))
        with open(self.runs / "RUNS_INDEX.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["cost_usd"], "3.00")
        self.assertEqual(list(rows[0]), rr.COLUMNS)
        md = (self.runs / "RUNS_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("2026-10-24_m_x", md)
        # rerun does not treat its own output as a root, and is stable
        self.assertEqual(len(rr.scan(self.runs)), 1)

    def test_main_exit_codes(self):
        self.assertEqual(rr.main([str(self.runs)]), 0)
        self.assertTrue((self.runs / "RUNS_INDEX.csv").exists())
        self.assertEqual(rr.main([str(self.runs / "nope")]), 2)

    def test_corrupt_bytes_and_junk_lines(self):
        root = self.runs / "tracks-bad"
        good = json.dumps({"seed": 1, "llm": {}}).encode()
        (root / "s").mkdir(parents=True)
        (root / "s" / "a.jsonl").write_bytes(good + b"\n\xff\xfe junk\n{trunc\n" + good + b"\n")
        w(root / "cost.json", obj={"spent_usd": float("inf")})
        r = rr.scan(self.runs)[0]
        self.assertEqual((r["done"], r["cost_usd"]), (2, ""))

    def test_non_string_params_and_name_thinking_fallback(self):
        root = self.runs / "2026-10-24_m_odd"
        d = root / "x" / "x__s1__t1"
        w(d / "params.json", obj={"arm": ["l"], "model": {"a": 1}, "code_commit": ["x"]})
        w(d / "DONE", "x")
        r = rr.scan(self.runs)[0]
        self.assertEqual((r["model"], r["commits"], r["thinking"]), ("", "", "on"))

    def test_default_dir_finds_runs_above(self):
        self.assertTrue(rr.default_dir().name == "runs")


if __name__ == "__main__":
    unittest.main()
