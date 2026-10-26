"""Tests for U6: grid slices, run_grid/run_waves --slice/--exclude-slice, pick_cell.py, pilot rows and collect's pilot exclusion.
Run: python -X utf8 -m unittest tools/trial/test_slices_pick_cell.py. Stub game command, no LLM, no network."""
import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import make_grid  # noqa: E402
import pick_cell  # noqa: E402
import run_grid  # noqa: E402
import run_waves  # noqa: E402

DESIGN = """
version: 1
points: {1: slice-p1.yaml, 3: slice-p3.yaml}
model_profiles:
  m:
    t1:  {temperature: 0.6, top_p: 0.95, top_k: 20, timeout_sec: 300, max_tokens: {talk: 4096, quote: 8192, question: 3072}}
    t0:  {temperature: 0.7, top_p: 0.8, top_k: 20, timeout_sec: 120, max_tokens: {talk: 320, quote: 400, question: 400}}
introspection_cell: {point: null, communication: null}
defaults: {model_profile: m, firms: 2, seats: [llm, llm], communication: private, condition_texts: {all: private_chat},
           wordings: [0, 1], seeds: [7, 8, 9], thinking: [0], wave: {t0: 1, t1: 2}}
arms:
  - {name: headline-chat, points: [1, 3]}
  - {name: r0, cell_from: introspection_cell, introspection: R0}
  - {name: r1, cell_from: introspection_cell, introspection: R1, pilot: false}
  - {name: side, points: [3], pilot: true}
"""


def expand(text=DESIGN, cell=None):
    d = yaml.safe_load(text)
    if cell:
        d["introspection_cell"] = cell
    return make_grid.expand(d)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class SliceGridTest(unittest.TestCase):
    def test_slice_is_wording_fastest_and_shared_across_points(self):
        rows, _ = expand()
        chat = [r for r in rows if r["arm"] == "headline-chat"]
        by = {(r["penalty_point"], r["wording"], r["seed"]): r["slice"] for r in chat}
        self.assertEqual("1", by[("1", "0", "7")])
        self.assertEqual("1", by[("3", "0", "7")])
        self.assertEqual("2", by[("1", "1", "7")])
        self.assertEqual("3", by[("1", "0", "8")])
        self.assertEqual("6", by[("3", "1", "9")])
        self.assertEqual({"1", "2", "3", "4", "5", "6"}, {r["slice"] for r in chat})

    def test_pilot_flag_defaults(self):
        rows, notes = expand(cell={"point": 3, "communication": "private"})
        flag = {r["arm"]: r["pilot"] for r in rows}
        self.assertEqual({"headline-chat": "", "r0": "true", "r1": "", "side": "true"}, flag)
        self.assertEqual([], notes)

    def test_pilot_must_be_boolean(self):
        with self.assertRaises(ValueError):
            expand(DESIGN.replace("pilot: true", "pilot: maybe"))

    def test_real_design_rows_have_slice_and_pilot_columns(self):
        d = yaml.safe_load((Path(__file__).resolve().parent / "design" / "trackm_design.yaml").read_text(encoding="utf-8"))
        rows, _ = make_grid.expand(d)
        self.assertTrue(all(r["slice"].isdigit() for r in rows))
        head = [r for r in rows if r["arm"] == "headline-chat" and r["slice"] == "1"]
        self.assertTrue(head and all(r["wording"] == "0" and r["seed"] == "91" for r in head))
        self.assertEqual({""}, {r["pilot"] for r in rows if r["arm"].startswith("headline-")})

    def test_cell_file_cli_runs_the_cell_arms(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "d.yaml").write_text(DESIGN, encoding="utf-8")
            (t / "cell.json").write_text(json.dumps({"point": 3, "communication": "monitored"}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, make_grid.main(["mg", str(t / "d.yaml"), str(t / "g.csv"), "--cell-file", str(t / "cell.json")]))
                self.assertEqual(0, make_grid.main(["mg", str(t / "d.yaml"), str(t / "g0.csv")]))
            r0 = [r for r in read_csv(t / "g.csv") if r["arm"] == "r0"]
            self.assertEqual(6, len(r0))
            self.assertEqual({("3", "monitored", "true")}, {(r["penalty_point"], r["communication"], r["pilot"]) for r in r0})
            self.assertFalse([r for r in read_csv(t / "g0.csv") if r["arm"] == "r0"])      # no cell file: skipped as before
            (t / "bad.json").write_text(json.dumps({"point": 3, "communication": "nope"}), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, make_grid.main(["mg", str(t / "d.yaml"), str(t / "g.csv"), "--cell-file", str(t / "bad.json")]))
                self.assertEqual(2, make_grid.main(["mg", str(t / "d.yaml"), str(t / "g.csv"), "--cell-file", str(t / "missing.json")]))


STUB = "import sys, pathlib\npathlib.Path(sys.argv[1], 'events.jsonl').write_text('{}\\n')\n"


class SliceRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "stub.py").write_text(STUB, encoding="utf-8")
        self.cmd = [sys.executable, str(self.root / "stub.py"), "{trial_dir}"]
        rows, _ = expand()
        self.rows = [r for r in rows if r["arm"] == "headline-chat"]                      # 2 points x 2 wordings x 3 seeds = 12
        make_grid.write_grid(self.rows, self.root / "grid.csv")

    def done(self, out):
        return sorted(p.parent.name for p in Path(out).rglob("DONE"))

    def run_main(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()):
            return run_grid.main(["rg", "--grid", str(self.root / "grid.csv"), "--out", str(self.root / "trials")] + list(extra) + ["--"] + self.cmd)

    def test_slice_then_exclude_slice_completes_the_grid_without_rerunning(self):
        self.assertEqual(0, self.run_main("--slice", "1"))
        first = self.done(self.root / "trials")
        self.assertEqual(["headline-chat__p1__w0__s7__t0", "headline-chat__p3__w0__s7__t0"], first)
        self.assertEqual(0, self.run_main("--exclude-slice", "1"))
        self.assertEqual(len(self.rows), len(self.done(self.root / "trials")))
        self.assertEqual("attempts 1\n", (self.root / "trials" / "headline-chat" / first[0] / "DONE").read_text())   # not rerun

    def test_select_filters(self):
        out = self.root / "x"
        todo, _, _ = run_grid.select(self.rows, out, slices={2, 3})
        self.assertEqual({"2", "3"}, {r["slice"] for r in todo})
        todo, _, _ = run_grid.select(self.rows, out, exclude_slices={1, 2})
        self.assertEqual(8, len(todo))
        self.assertNotIn("1", {r["slice"] for r in todo})
        self.assertEqual(12, len(run_grid.select(self.rows, out)[0]))

    def test_grid_without_slice_column_is_refused_only_when_asked(self):
        rows = [{k: v for k, v in r.items() if k != "slice"} for r in self.rows]
        with self.assertRaises(ValueError):
            run_grid.slice_filter(rows, {1})
        self.assertEqual(len(rows), len(run_grid.slice_filter(rows)))

    def test_run_waves_plan_counts_only_selected_slices(self):
        steps = run_waves.plan(self.rows, self.root / "o", {}, 100.0, slices={1})
        self.assertEqual([(1, 2)], [(s["wave"], s["total"]) for s in steps])
        steps = run_waves.plan(self.rows, self.root / "o", {}, 100.0, exclude_slices={1})
        self.assertEqual([(1, 10)], [(s["wave"], s["total"]) for s in steps])

    def test_run_waves_passes_slice_to_run_grid(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = run_waves.main(["rw", "--grid", str(self.root / "grid.csv"), "--out", str(self.root / "w"), "--stop-line", "10",
                                 "--slice", "2", "--"] + self.cmd)
        self.assertEqual(0, rc)
        self.assertEqual(["headline-chat__p1__w1__s7__t0", "headline-chat__p3__w1__s7__t0"], self.done(self.root / "w"))


def trial(root, arm, tid, prices, row=None, done=True, commit="c"):
    """A finished trial directory: two seats quoting the same price each round (collusion level = mean of (p - 2.0) / 0.4, clamped)."""
    d = Path(root) / arm / tid
    d.mkdir(parents=True)
    ev, seq = [], 0
    for rnd, p in enumerate(prices, 1):
        for seat in ("a0", "a1"):
            seq += 1
            ev.append({"seq": seq, "kind": "quote", "round": rnd, "seat": seat, "outcome": "OK", "quote": p})
        seq += 1
        ev.append({"seq": seq, "kind": "market", "round": rnd, "prices": {"a0": p, "a1": p}, "winner": None,
                   "profits": {"a0": 1.0, "a1": 1.0}, "market_price": p})
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev), encoding="utf-8")
    (d / "params.json").write_text(json.dumps({"arm": arm, "thinking": "off", "competitive_price": 2.0, "collusive_price": 2.4,
                                               "prompt_fingerprint": "f", "code_commit": commit}), encoding="utf-8")
    if row is not None:
        (d / "grid_row.json").write_text(json.dumps(row), encoding="utf-8")
    if done:
        (d / "DONE").write_text("attempts 1\n", encoding="utf-8")
    return d


def tid(p, w=0):
    return "headline-chat__p%d__w%d__s7__t0" % (p, w)


class PickCellTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        rows, _ = expand()
        base = [r for r in rows if r["arm"] == "headline-chat" and r["slice"] == "1"]          # p1 and p3, w0, s7
        self.rows = base + [dict(base[0], trial_id=tid(4), penalty_point="4"),
                            dict(base[0], trial_id=tid(5), penalty_point="5", communication="monitored"),
                            dict(base[0], trial_id=tid(3, 1), penalty_point="3", slice="2")]

    def test_picks_highest_collusion_private_chat_trial_of_slice_1(self):
        trial(self.root, "headline-chat", tid(1), [2.0, 2.2])           # level 0.5
        trial(self.root, "headline-chat", tid(3), [2.4, 2.4])           # level 1.0
        trial(self.root, "headline-chat", tid(4), [2.2, 2.2])           # 0.5
        trial(self.root, "headline-chat", tid(5), [2.4, 2.4])           # monitored: ignored
        trial(self.root, "headline-chat", tid(3, 1), [2.4, 2.4])        # slice 2: ignored
        cell, notes = pick_cell.pick(self.rows, self.root)
        self.assertEqual((3, "private", tid(3), 1.0), (cell["point"], cell["communication"], cell["source_trial"], cell["collusion_level"]))
        self.assertEqual(3, len(cell["candidates"]))
        self.assertEqual([], notes)

    def test_slice_option_and_tie_break(self):
        for p in (1, 3, 4):
            trial(self.root, "headline-chat", tid(p), [2.4, 2.4])
        self.assertEqual(1, pick_cell.pick(self.rows, self.root)[0]["point"])          # tie: smaller trial_id
        trial(self.root, "headline-chat", tid(3, 1), [2.4])
        self.assertEqual(3, pick_cell.pick(self.rows, self.root, slice_no=2)[0]["point"])

    def test_unfinished_trial_blocks_unless_allowed(self):
        trial(self.root, "headline-chat", tid(1), [2.4, 2.4])
        trial(self.root, "headline-chat", tid(3), [2.4, 2.4], done=False)
        with self.assertRaises(ValueError):
            pick_cell.pick(self.rows, self.root)
        cell, notes = pick_cell.pick(self.rows, self.root, allow_incomplete=True)
        self.assertEqual(1, cell["point"])
        self.assertTrue(any(tid(3) in n or "unfinished" in n for n in notes))

    def test_nothing_finished_or_no_rows(self):
        with self.assertRaises(ValueError):
            pick_cell.pick(self.rows, self.root, allow_incomplete=True)
        with self.assertRaises(ValueError):
            pick_cell.pick(self.rows, self.root, arm="no-such-arm")

    def test_cli_writes_cell_file_that_make_grid_reads(self):
        for p in (1, 3, 4):
            trial(self.root, "headline-chat", tid(p), [2.0 + 0.1 * p, 2.0 + 0.1 * p])
        make_grid.write_grid([dict({c: "" for c in make_grid.GRID_COLS}, **r) for r in self.rows], self.root / "grid.csv")
        out = self.root / "sub" / "cell.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, pick_cell.main(["pc", "--grid", str(self.root / "grid.csv"), "--trials", str(self.root), "--out", str(out)]))
        self.assertEqual({"point": 4, "communication": "private"}, make_grid.read_cell(out))
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, pick_cell.main(["pc", "--grid", str(self.root / "grid.csv"), "--trials", str(self.root / "none"),
                                                "--out", str(self.root / "cell2.json")]))
        self.assertFalse((self.root / "cell2.json").exists())


class PilotCollectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "trials"
        trial(self.root, "headline-chat", tid(3), [2.4, 2.4], row={"pilot": ""})
        trial(self.root, "r0", "r0__p3__w0__s7__t0", [2.4, 2.4], row={"pilot": "true"})
        trial(self.root, "old", "old__p3__w0__s7__t0", [2.4, 2.4])                        # no grid_row.json: not a pilot
        self.out = Path(self.tmp.name) / "out"

    def tables(self, **kw):
        with contextlib.redirect_stderr(io.StringIO()):
            collect.collect(self.root, self.out, **kw)
        return {n: read_csv(self.out / n) for n in ("trials.csv", "rounds.csv")}

    def test_pilot_excluded_by_default_and_flag_includes(self):
        t = self.tables()
        self.assertEqual({tid(3), "old__p3__w0__s7__t0"}, {r["trial_id"] for r in t["trials.csv"]})
        self.assertNotIn("r0__p3__w0__s7__t0", {r["trial_id"] for r in t["rounds.csv"]})
        t = self.tables(include_pilot=True)
        by = {r["trial_id"]: r for r in t["trials.csv"]}
        self.assertEqual(3, len(by))
        self.assertEqual(("1", ""), (by["r0__p3__w0__s7__t0"]["pilot"], by[tid(3)]["pilot"]))
        self.assertIn("r0__p3__w0__s7__t0", {r["trial_id"] for r in t["rounds.csv"]})

    def test_excluded_pilot_does_not_trip_the_fingerprint_guard(self):
        trial(self.root, "r0", "r0__p3__w1__s7__t0", [2.4], row={"pilot": "true"}, commit="other")
        self.tables()
        with self.assertRaises(collect.MixedFingerprintError):
            self.tables(include_pilot=True)

    def test_cli_flag(self):
        o1, o2 = str(Path(self.tmp.name) / "o1"), str(Path(self.tmp.name) / "o2")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(0, collect.main(["c", str(self.root), o1]))
            self.assertEqual(0, collect.main(["c", str(self.root), o2, "--include-pilot"]))
        self.assertEqual((2, 3), (len(read_csv(Path(o1) / "trials.csv")), len(read_csv(Path(o2) / "trials.csv"))))


if __name__ == "__main__":
    unittest.main()
