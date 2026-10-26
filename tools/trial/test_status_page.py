"""Tests for status_page.py (U7). Run: python -X utf8 -m unittest tools/trial/test_status_page.py"""
import csv
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import status_page as sp  # noqa: E402

COLS = ["trial_id", "arm", "penalty_point", "condition_texts", "communication", "wording", "seed", "thinking",
        "slice", "pilot", "options"]


def w(path, text="", obj=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if obj is not None else text, encoding="utf-8")


def grid(root, rows):
    with open(root / "grid.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        wr.writeheader()
        for r in rows:
            wr.writerow({c: r.get(c, "") for c in COLS})
    return root / "grid.csv"


def row(arm, p, s, t=0, cond="all:neutral", pilot=""):
    return {"trial_id": "%s__p%s__w0__s%s__t%s" % (arm, p, s, t), "arm": arm, "penalty_point": p,
            "condition_texts": cond, "communication": "private", "wording": 0, "seed": s, "thinking": t,
            "slice": s, "pilot": pilot}


def tdir(root, r, marker=None, age=0, layout="arm"):
    d = (root / r["arm"] / r["trial_id"]) if layout == "arm" else (root / "trials" / r["arm"] / r["trial_id"])
    w(d / "grid_row.json", obj=r)
    if marker:
        w(d / marker, "attempts 1")
    if age:
        old = time.time() - age
        for p in d.iterdir():
            os.utime(p, (old, old))
    return d


class Classify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_four_states_and_stalled(self):
        rows = [row("a", 1, s) for s in range(1, 6)]
        gp = grid(self.root, rows)
        tdir(self.root, rows[0], "DONE")
        tdir(self.root, rows[1], "FAILED")
        tdir(self.root, rows[2])                      # running, fresh
        tdir(self.root, rows[3], age=7200)            # no marker, old: stalled
        st = sp.collect(self.root, gp, now=time.time())
        got = [c["state"] for c in st["cells"]]
        self.assertEqual(got, ["done", "failed", "running", "stalled", "notstarted"])
        self.assertEqual(st["counts"], {"done": 1, "failed": 1, "running": 1, "stalled": 1, "notstarted": 1,
                                        "total": 5})

    def test_trials_subdir_layout(self):
        r = row("a", 1, 1)
        gp = grid(self.root, [r])
        tdir(self.root, r, "DONE", layout="trials")
        self.assertEqual(sp.collect(self.root, gp)["cells"][0]["state"], "done")

    def test_done_wins_over_failed_marker_order(self):
        r = row("a", 1, 1)
        gp = grid(self.root, [r])
        d = tdir(self.root, r, "FAILED")
        w(d / "DONE", "attempts 2")                   # a rerun succeeded later
        self.assertEqual(sp.collect(self.root, gp)["cells"][0]["state"], "done")

    def test_pilot_flag_kept(self):
        r = row("a", 1, 1, pilot="true")
        gp = grid(self.root, [r])
        self.assertTrue(sp.collect(self.root, gp)["cells"][0]["pilot"])


class Totals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_tokens_cost_seconds(self):
        r1, r2 = row("a", 1, 1), row("a", 1, 2)
        gp = grid(self.root, [r1, r2])
        d = tdir(self.root, r1, "DONE")
        w(d / "events.jsonl", '{"kind":"talk","tokens_in":100,"tokens_out":10}\n'
                              'garbage\n{"kind":"quote","tokens_in":50,"tokens_out":5}\n{"kind":"market"}\n')
        w(d / "run_stats.json", obj={"status": "done", "seconds": 120.5, "attempts": 1})
        d2 = tdir(self.root, r2)
        w(d2 / "events.jsonl", '{"kind":"talk","tokens_in":1,"tokens_out":2}\n')
        w(self.root / "cost.json", obj={"spent_usd": 3.456})
        st = sp.collect(self.root, gp)
        self.assertEqual(st["tokens_in"], 151)
        self.assertEqual(st["tokens_out"], 17)
        self.assertEqual(st["cost_usd"], "3.46")
        self.assertAlmostEqual(st["game_seconds"], 120.5)

    def test_no_meter_blank_cost(self):
        r = row("a", 1, 1)
        gp = grid(self.root, [r])
        self.assertEqual(sp.collect(self.root, gp)["cost_usd"], "")

    def test_elapsed_from_grid_rows(self):
        r = row("a", 1, 1)
        gp = grid(self.root, [r])
        d = tdir(self.root, r, "DONE")
        t0 = time.time() - 3600
        os.utime(d / "grid_row.json", (t0, t0))
        st = sp.collect(self.root, gp, now=time.time())
        self.assertGreaterEqual(st["elapsed_seconds"], 3500)


class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_page(self):
        rows = [row("a&b", p, s, t) for p in (1, 2) for s in (1, 2) for t in (0, 1)] + [row("c", 1, 1)]
        gp = grid(self.root, rows)
        tdir(self.root, rows[0], "DONE")
        tdir(self.root, rows[1], "FAILED")
        tdir(self.root, rows[2])
        html = sp.render(sp.collect(self.root, gp))
        self.assertIn('http-equiv="refresh" content="60"', html)
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertNotIn("a&b", html)                      # escaped
        self.assertIn("a&amp;b", html)
        for cls in ("done", "failed", "running", "notstarted"):
            self.assertIn('class="cell %s"' % cls, html)
        self.assertEqual(html.count('<div class="cell '), len(rows))
        self.assertNotIn("http://", html.replace("http-equiv", ""))
        self.assertNotIn("https://", html)
        self.assertNotIn("src=", html)

    def test_rows_split_by_condition(self):
        rows = [row("a", 1, 1, cond="all:x"), row("a", 1, 2, cond="all:y")]
        gp = grid(self.root, rows)
        st = sp.collect(self.root, gp)
        self.assertEqual(len(st["rows"]), 2)

    def test_empty_grid(self):
        gp = grid(self.root, [])
        html = sp.render(sp.collect(self.root, gp))
        self.assertIn("0 / 0", html)


class Collisions(unittest.TestCase):
    def test_every_grid_row_has_a_cell_without_slice_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for wd in (0, 1, 3):
                r = row("a", 1, 1)
                r["wording"] = wd
                r["slice"] = ""
                r["trial_id"] = "a__p1__w%d__s1__t0" % wd
                rows.append(r)
            gp = grid(root, rows)
            tdir(root, rows[0], "DONE")
            html = sp.render(sp.collect(root, gp))
            self.assertEqual(html.count('<div class="cell '), 3)
            self.assertEqual(html.count('<div class="cell done'), 1)
            self.assertEqual(html.count('<div class="cell notstarted"'), 2)


class RunRoots(unittest.TestCase):
    """N5: neutral twin, truncation-rerun and condition-text rerun roots."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def sup(self, rows):
        with open(self.root / "superseded.csv", "w", newline="", encoding="utf-8") as f:
            f.write("original_id,rerun_id,reason\n")
            for o, r, why in rows:
                f.write("%s,%s,%s\n" % (o, r, why))

    def test_payoff_condition_sources(self):
        r = row("a", 1, 1)
        self.assertEqual(sp.payoff_condition(r, None), "anchored")                      # default
        self.assertEqual(sp.payoff_condition(dict(r, payoff_examples="neutral"), None), "neutral")   # column
        self.assertEqual(sp.payoff_condition(dict(r, options='{"payoff_examples":"neutral"}'), None), "neutral")
        d = self.root / "t"
        w(d / "params.json", obj={"options": {"payoff_examples": "neutral"}})
        self.assertEqual(sp.payoff_condition(r, d), "neutral")

    def test_neutral_twin_root_shows_condition(self):
        rows = [dict(row("a", 1, s), options='{"payoff_examples":"neutral"}') for s in (1, 2)]
        gp = grid(self.root, rows)
        tdir(self.root, rows[0], "DONE")
        st = sp.collect(self.root, gp)
        self.assertEqual(st["payoff_examples"], ["neutral"])
        self.assertIn("payoff_examples: neutral", sp.render(st))

    def test_mixed_payoff_splits_rows(self):
        rows = [row("a", 1, 1), row("a", 1, 2)]
        w(self.root / "a" / rows[1]["trial_id"] / "params.json", obj={"payoff_examples": "neutral"})
        gp = grid(self.root, rows)
        st = sp.collect(self.root, gp)
        self.assertEqual(len(st["rows"]), 2)
        self.assertIn("payoff_examples=neutral", sp.render(st))

    def test_superseded_not_counted_and_rerun_linked(self):
        o1, o2 = row("a", 1, 1), row("a", 1, 2)
        r1 = dict(o1, trial_id=o1["trial_id"] + "__x32k")
        gp = grid(self.root, [o1, o2, r1])
        tdir(self.root, o1, "FAILED")            # truncated original: must not count as a failure
        tdir(self.root, o2, "DONE")
        tdir(self.root, r1, "DONE")
        self.sup([(o1["trial_id"], r1["trial_id"], "truncated")])
        st = sp.collect(self.root, gp)
        self.assertEqual(st["counts"]["failed"], 0)
        self.assertEqual(st["counts"]["done"], 2)
        self.assertEqual(st["counts"]["total"], 2)
        self.assertEqual(st["superseded"], 1)
        page = sp.render(st)
        self.assertEqual(page.count('class="cell superseded"'), 2)   # legend swatch + the cell
        self.assertEqual(page.count('class="cell done rerun"'), 2)   # one legend swatch + one cell
        self.assertIn("rerun of " + o1["trial_id"], page)
        self.assertIn("SUPERSEDED by " + r1["trial_id"], page)
        self.assertIn("<b>2 / 2</b>", page)

    def test_rerun_missing_from_grid_made_from_original(self):
        o = row("a", 1, 1)
        rid = o["trial_id"] + "__x32k"
        gp = grid(self.root, [o])
        tdir(self.root, o, "FAILED")
        w(self.root / "a" / rid / "DONE", "ok")
        self.sup([(o["trial_id"], rid, "truncated")])
        st = sp.collect(self.root, gp)
        self.assertEqual([c["state"] for c in st["cells"]], ["failed", "done"])
        self.assertEqual(st["cells"][1]["original"], o["trial_id"])
        self.assertEqual(st["counts"]["total"], 1)
        self.assertEqual(len(st["columns"]), 2)           # the rerun has its own column

    def test_no_superseded_file_means_no_change(self):
        o = row("a", 1, 1)
        gp = grid(self.root, [o])
        tdir(self.root, o, "FAILED")
        st = sp.collect(self.root, gp)
        self.assertEqual((st["counts"]["failed"], st["superseded"]), (1, 0))

    def test_malformed_superseded_is_ignored(self):
        (self.root / "superseded.csv").write_bytes(bytes([255, 254]) + b" junk")
        self.assertEqual(sp.load_superseded(self.root / "superseded.csv"), {})

    def test_condition_text_rerun_root_rows(self):
        rows = [row("m-asym", 1, 1, cond="new-asym"), row("n3-ethics", 1, 1, cond="new-ethics"),
                row("m-inc-target", 1, 1, cond="new-inc")]
        gp = grid(self.root, rows)
        tdir(self.root, rows[0], "DONE")
        st = sp.collect(self.root, gp)
        self.assertEqual([k[1] for k in st["rows"]], ["new-asym", "new-ethics", "new-inc"])
        self.assertEqual(st["counts"]["done"], 1)

    def test_separate_rerun_root_no_phantom_cell(self):
        o = row("a", 1, 1)
        rid = o["trial_id"] + "__x32k"
        gp = grid(self.root, [o])
        tdir(self.root, o, "FAILED")
        self.sup([(o["trial_id"], rid, "truncated")])
        st = sp.collect(self.root, gp)
        self.assertEqual(len(st["cells"]), 1)
        self.assertEqual((st["counts"]["notstarted"], st["counts"]["total"], st["superseded"]), (0, 0, 1))
        page = sp.render(st)
        self.assertIn("rerun in other root", page)
        self.assertIn("<b>0 / 0</b>", page)
        self.assertIn("still include them", page)
        # with the rerun root given, the rerun cell appears
        rr = self.root / "rr"
        w(rr / "a" / rid / "DONE", "ok")
        st = sp.collect(self.root, gp, rerun_roots=[rr])
        self.assertEqual((st["counts"]["done"], st["counts"]["total"]), (1, 1))
        self.assertEqual(st["cells"][1]["original"], o["trial_id"])
        out = self.root / "p.html"
        self.assertEqual(sp.main([str(self.root), "--rerun-root", str(rr), "--out", str(out)]), 0)
        self.assertIn("rerun of", out.read_text(encoding="utf-8"))

    def test_superseded_but_running_stays_visible(self):
        o = row("a", 1, 1)
        gp = grid(self.root, [o])
        tdir(self.root, o)                      # fresh, no marker: running
        self.sup([(o["trial_id"], o["trial_id"] + "__x32k", "truncated")])
        st = sp.collect(self.root, gp)
        self.assertEqual((st["counts"]["running"], st["counts"]["total"], st["superseded"]), (1, 1, 0))
        self.assertIn("superseded, but still running", sp.render(st))

    def test_only_x32k_suffix_is_a_rerun(self):
        o = row("a", 1, 1)
        other = dict(o, trial_id=o["trial_id"] + "__x64k")
        gp = grid(self.root, [o, other])
        st = sp.collect(self.root, gp)
        self.assertEqual([c["original"] for c in st["cells"]], ["", ""])

    def test_rerun_plural(self):
        o = row("a", 1, 1)
        gp = grid(self.root, [o, dict(o, trial_id=o["trial_id"] + "__x32k")])
        self.assertIn("1 rerun;", sp.render(sp.collect(self.root, gp)) + ";")
        self.assertNotIn("1 reruns", sp.render(sp.collect(self.root, gp)))

    def test_cli_superseded_option(self):
        o = row("a", 1, 1)
        gp = grid(self.root, [o])
        tdir(self.root, o, "FAILED")
        other = self.root / "elsewhere.csv"
        other.write_text("original_id,rerun_id,reason\n%s,,why\n" % o["trial_id"], encoding="utf-8")
        out = self.root / "s.html"
        self.assertEqual(sp.main([str(self.root), "--superseded", str(other), "--out", str(out)]), 0)
        self.assertIn('class="cell superseded"', out.read_text(encoding="utf-8"))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_once_writes_file_and_exit_codes(self):
        gp = grid(self.root, [row("a", 1, 1)])
        out = self.root / "status.html"
        self.assertEqual(sp.main([str(self.root), "--grid", str(gp), "--out", str(out)]), 0)
        self.assertIn("refresh", out.read_text(encoding="utf-8"))
        self.assertEqual(sp.main([str(self.root / "nope"), "--out", str(out)]), 2)
        self.assertEqual(sp.main([str(self.root), "--grid", str(self.root / "missing.csv"), "--out", str(out)]), 2)

    def test_watch_loops(self):
        gp = grid(self.root, [row("a", 1, 1)])
        out = self.root / "status.html"
        n = []
        sp.watch(self.root, gp, out, interval=60, sleep=lambda s: n.append(s), max_loops=3)
        self.assertEqual(n, [60, 60])
        self.assertTrue(out.exists())

    def test_default_grid_and_out(self):
        grid(self.root, [row("a", 1, 1)])
        self.assertEqual(sp.main([str(self.root)]), 0)
        self.assertTrue((self.root / "status.html").exists())


if __name__ == "__main__":
    unittest.main()
