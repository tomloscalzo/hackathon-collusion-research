"""Contract tests: the trial id and directory layout between make_grid.py, run_grid.py and collect.py.

Every trial id the real design file produces must parse back, through collect.py's directory-name fallback, to the same
arm, penalty point, wording, seed and thinking mode as its grid row; the layout run_grid._run_trial writes (<out>/<arm>/<trial_id>) must be
found by collect.find_trials with no name clash; and the make_grid CLI must write the grid (exit 0) or reject a bad design
(exit 2). Run: python -X utf8 -m unittest tools/trial/test_contract_grid_ids.py
"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect  # noqa: E402
import make_grid  # noqa: E402
import run_grid  # noqa: E402

try:
    import yaml
except ImportError:  # PyYAML is needed by make_grid itself
    yaml = None

DESIGN = HERE / "design" / "trackm_design.yaml"


def real_rows(with_cell=True):
    d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    if with_cell:  # set the introspection cell so the R0-R4 arms expand too
        d["introspection_cell"] = {"point": 3, "communication": "private"}
    rows, _ = make_grid.expand(d, DESIGN)
    return rows


@unittest.skipIf(yaml is None, "PyYAML not installed")
class GridIdsRoundTrip(unittest.TestCase):
    def test_every_real_trial_id_parses_back_to_its_grid_row(self):
        rows = real_rows()
        self.assertGreater(len(rows), 100)
        for r in rows:
            meta = collect.trial_meta(Path("out") / r["arm"] / r["trial_id"], {})
            got = {k: str(meta[k]) for k in ("arm", "penalty_point", "wording", "seed")}
            self.assertEqual(got, {k: r[k] for k in ("arm", "penalty_point", "wording", "seed")}, r["trial_id"])
            self.assertEqual(meta["thinking"], {"0": "off", "1": "on"}[r["thinking"]], r["trial_id"])

    def test_params_json_values_win_over_the_directory_name(self):
        r = real_rows()[0]
        meta = collect.trial_meta(Path(r["trial_id"]), {"arm": "x", "thinking": "on" if r["thinking"] == "0" else "off"})
        self.assertEqual(meta["arm"], "x")
        self.assertNotEqual(meta["thinking"], {"0": "off", "1": "on"}[r["thinking"]])

    def test_run_grid_layout_is_found_by_collect_without_clashes(self):
        rows = real_rows()

        class WritesEvents:                    # stands in for the game: writes an empty events.jsonl where run_grid says
            def run(self, row, trial_dir, timeout=None):
                (Path(trial_dir) / "events.jsonl").write_text("", encoding="utf-8")
                return run_grid.Result(0)

        with tempfile.TemporaryDirectory() as d:
            for r in rows:
                self.assertEqual(run_grid._run_trial(r, d, WritesEvents(), None)["status"], "done")
            found = collect.find_trials(d)
            self.assertEqual([p.name for p in found], sorted(r["trial_id"] for r in rows))
            self.assertEqual({p.parent.name for p in found}, {r["arm"] for r in rows})


@unittest.skipIf(yaml is None, "PyYAML not installed")
class MakeGridCli(unittest.TestCase):
    def test_cli_writes_the_real_grid(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sub" / "grid.csv"
            err, so = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(so):
                rc = make_grid.main(["make_grid.py", str(DESIGN), str(out)])
            self.assertEqual(rc, 0)
            lines = out.read_bytes().split(b"\n")
            self.assertEqual(lines[0].decode(), ",".join(make_grid.GRID_COLS))
            self.assertNotIn(b"\r", out.read_bytes())
            self.assertEqual(len([l for l in lines[1:] if l]), len(real_rows(with_cell=False)))
            self.assertIn("introspection_cell", err.getvalue())   # the R arms are skipped with a note

    def test_cli_usage_and_bad_design_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(make_grid.main(["make_grid.py"]), 2)
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.yaml"
            bad.write_text(DESIGN.read_text(encoding="utf-8").replace("name: headline-chat,", "name: headline_chat,"), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(make_grid.main(["make_grid.py", str(bad), str(Path(d) / "g.csv")]), 2)
            self.assertIn("headline_chat", err.getvalue())
            self.assertFalse((Path(d) / "g.csv").exists())


if __name__ == "__main__":
    unittest.main()
