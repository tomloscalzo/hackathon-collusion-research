"""Window-basis pairing is scoped to the comparison being made (quality review Q1).

The tables come from the real design file (trackm_design.yaml, with the introspection cell set to point 3, so the Track R
arms are expanded too): point 3 then holds the headline arms plus the smoke, control, side and R arms, each with its own
wordings and seeds. The headline pairs seeds only across the headline arms (tacit, private chat, monitored chat);
analysis_m pairs the headline arms only, and a contrast pairs only its two arms.
Run: python -X utf8 -m unittest tools/trial/test_pairing_scope.py"""
import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_headline as ah  # noqa: E402
import analysis_m as am  # noqa: E402
import make_grid  # noqa: E402

DESIGN = Path(__file__).resolve().parent / "design" / "trackm_design.yaml"
HEADLINE = ("headline-chat", "headline-monitored", "headline-tacit")
THEORY = {ah._key(str(p)): (float(p), 0.5) for p in range(1, 6)}


def design_grid():
    d = yaml.safe_load(DESIGN.read_text(encoding="utf-8"))
    d["introspection_cell"] = {"point": 3, "communication": "private"}
    rows, notes = make_grid.expand(d)
    assert not notes, notes
    return [r for r in rows if r["thinking"] == "0"]


def tables(grid, drop=()):
    """Every grid trial plays rounds 1..20 at the collusive price (level 1); trial ids in `drop` are left out."""
    trials, rounds = [], []
    for g in grid:
        if g["trial_id"] in drop:
            continue
        trials.append(dict(trial_id=g["trial_id"], arm=g["arm"], thinking="off", penalty_point=g["penalty_point"],
                           wording=g["wording"], seed=g["seed"], status="done", competitive_price="1", collusive_price="2"))
        for r in range(1, 21):
            for seat in ("llm1", "llm2"):
                rounds.append(dict(trial_id=g["trial_id"], round=str(r), seat=seat, quote="2", market_price="2",
                                   imputed="0", refusal_kind="", parse_status="OK"))
    return {"trials": trials, "rounds": rounds, "messages": [], "questions": [], "refusals": []}


def write_tables(d, t):
    for name in ("trials", "rounds"):
        with open(Path(d) / (name + ".csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, list(t[name][0]), lineterminator="\n")
            w.writeheader()
            w.writerows(t[name])


def cell(rows, arm, point, refusals="with"):
    return [r["n_games"] for r in rows if r["arm"] == arm and str(r["penalty_point"]) == str(point) and r["refusals"] == refusals]


class DesignAtPointThree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid = design_grid()
        arms3 = {g["arm"] for g in cls.grid if g["penalty_point"] == "3"}
        # the point-3 mix the review found: smoke, controls, side arms and Track R arms beside the headline arms
        for a in ("smoke-14b-tacit", "ctl-14b-joint", "m-pub", "n3-group", "r2s-confidant", "r4-announced") + HEADLINE:
            assert a in arms3, a
        cls.tables = tables(cls.grid)

    def test_headline_keeps_20_games_per_cell_and_draws_only_headline_arms(self):
        rows = ah.headline_rows(self.tables, 1.0, 2.0, THEORY, boot=20)
        for arm in HEADLINE:
            for p in (1, 3, 4, 5):
                self.assertEqual(cell(rows, arm, p), [20], (arm, p))
                self.assertEqual(cell(rows, arm, p, "without"), [20], (arm, p))
        self.assertEqual({r["arm"] for r in rows}, set(HEADLINE) | {"theory"})

    def test_headline_still_pairs_within_the_headline_arms(self):
        drop = {"headline-monitored__p3__w2__s174__t0"}
        rows = ah.headline_rows(tables(self.grid, drop), 1.0, 2.0, THEORY, boot=20)
        for arm in HEADLINE:
            self.assertEqual(cell(rows, arm, 3), [19], arm)   # w2 s174 is gone from every headline arm at point 3
            self.assertEqual(cell(rows, arm, 1), [20], arm)   # other points untouched
        asg = ah.headline_rows(tables(self.grid, drop), 1.0, 2.0, THEORY, basis="assigned", boot=20)
        self.assertEqual(cell(asg, "headline-chat", 3), [20])

    def test_headline_arm_selection(self):
        rows = ah.headline_rows(self.tables, 1.0, 2.0, THEORY, boot=20, arms=r"^headline-(tacit|chat)$")
        self.assertEqual({r["arm"] for r in rows}, {"headline-tacit", "headline-chat", "theory"})
        with self.assertRaises(ValueError):
            ah.headline_rows(self.tables, 1.0, 2.0, THEORY, boot=20, arms=r"^nothing$")

    def test_analysis_m_pairing_drops_nothing_when_every_headline_seed_is_there(self):
        rows = am.game_measures(am.build_games(self.tables, 1.0, 2.0), 1, 20)
        kept, dropped = am.pair_window(rows)
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), len(rows))

    def test_analysis_m_pairs_headline_arms_only_and_never_side_arms(self):
        drop = {"headline-monitored__p3__w2__s174__t0", "m-pub__p3__w0__s91__t0"}
        rows = am.game_measures(am.build_games(tables(self.grid, drop), 1.0, 2.0), 1, 20)
        kept, dropped = am.pair_window(rows)
        self.assertEqual(sorted({r["trial_id"] for r in dropped}),
                         ["headline-chat__p3__w2__s174__t0", "headline-tacit__p3__w2__s174__t0"])
        self.assertTrue(all(r["basis"] == "window" for r in dropped))
        # every other arm keeps all its games (m-pub's missing seed removes nothing elsewhere)
        n = lambda arm: len({r["trial_id"] for r in kept if r["arm"] == arm and r["basis"] == "window"})
        self.assertEqual((n("m-pub"), n("r2s-confidant"), n("smoke-14b-tacit"), n("n3-group")), (19, 20, 2, 20))
        _, all_dropped = am.pair_window(rows, None)   # arms=None: pair across every arm given (the old rule)
        self.assertGreater(len(all_dropped), len(dropped))

    def test_cli_contrast_pairs_only_its_two_arms(self):
        drop = {"headline-monitored__p3__w2__s174__t0"}
        with tempfile.TemporaryDirectory() as d:
            write_tables(Path(d) / ".", tables(self.grid, drop))
            with redirect_stdout(io.StringIO()):
                am.main([d, str(Path(d) / "o"), "--boot", "20", "--contrast", "headline-chat:m-pub",
                         "--contrast", "headline-chat:headline-tacit"])
            with open(Path(d) / "o" / "contrasts.csv", encoding="utf-8") as f:
                c = {(r["contrast"], r["basis"], r["refusals"]): r for r in csv.DictReader(f) if r["penalty_point"] == "3"}
            with open(Path(d) / "o" / "measures_summary.csv", encoding="utf-8") as f:
                s = {(r["arm"], r["basis"], r["refusals"]): r for r in csv.DictReader(f) if r["penalty_point"] == "3"}
            with open(Path(d) / "o" / "exclusions.csv", encoding="utf-8") as f:
                ex = {r["trial_id"] for r in csv.DictReader(f) if r["reason"] == "unpaired_seed"}
        self.assertEqual(c[("headline-chat-m-pub", "window", "with")]["n_pairs"], "20")
        self.assertEqual(c[("headline-chat-headline-tacit", "window", "with")]["n_pairs"], "20")
        self.assertEqual(s[("headline-chat", "window", "with")]["n_games"], "19")   # the summary pairs the headline arms
        self.assertEqual(s[("m-pub", "window", "with")]["n_games"], "20")
        self.assertEqual(ex, {"headline-chat__p3__w2__s174__t0", "headline-tacit__p3__w2__s174__t0"})

    def test_cli_pair_arms_switch(self):
        drop = {"m-pub__p3__w0__s91__t0"}
        with tempfile.TemporaryDirectory() as d:
            write_tables(Path(d) / ".", tables(self.grid, drop))
            with redirect_stdout(io.StringIO()):
                am.main([d, str(Path(d) / "o"), "--boot", "20", "--pair-arms", r"^(m-pub|headline-chat)$"])
            with open(Path(d) / "o" / "measures_summary.csv", encoding="utf-8") as f:
                s = {(r["arm"], r["basis"], r["refusals"]): r for r in csv.DictReader(f) if r["penalty_point"] == "3"}
        self.assertEqual((s[("headline-chat", "window", "with")]["n_games"], s[("headline-tacit", "window", "with")]["n_games"]),
                         ("19", "20"))

    def test_headline_cli_default_draws_and_pairs_the_headline_arms(self):
        with tempfile.TemporaryDirectory() as d:
            write_tables(Path(d) / ".", tables(self.grid, {"m-pub__p3__w0__s91__t0", "headline-tacit__p4__w1__s47__t0"}))
            (Path(d) / "theory.csv").write_text("penalty_point,expected_penalty,theory_level\n" +
                                                "".join("%d,%d,0.5\n" % (p, p) for p in range(1, 6)), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                code = ah.main([d, str(Path(d) / "o"), "--theory", str(Path(d) / "theory.csv"), "--no-png", "--boot", "20"])
            with open(Path(d) / "o" / "headline_data.csv", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(code, 0)
        self.assertEqual({r["arm"] for r in rows}, set(HEADLINE) | {"theory"})
        for arm in HEADLINE:
            self.assertEqual(cell(rows, arm, 3), ["20"], arm)
            self.assertEqual(cell(rows, arm, 4), ["19"], arm)   # paired across the headline arms: tacit lacks w1 s2

    def test_headline_pairs_whatever_arms_are_drawn(self):
        drop = {"m-pub__p3__w0__s91__t0"}
        rows = ah.headline_rows(tables(self.grid, drop), 1.0, 2.0, THEORY, boot=20, arms=r"^(m-pub|headline-chat)$")
        self.assertEqual((cell(rows, "headline-chat", 3), cell(rows, "m-pub", 3)), ([19], [19]))
        self.assertEqual(cell(rows, "headline-chat", 1), [20])

    def test_headline_cli_fails_when_no_arm_matches(self):
        with tempfile.TemporaryDirectory() as d:
            write_tables(Path(d) / ".", self.tables)
            (Path(d) / "theory.csv").write_text("penalty_point,expected_penalty,theory_level\n" +
                                                "".join("%d,%d,0.5\n" % (p, p) for p in range(1, 6)), encoding="utf-8")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
                ah.main([d, str(Path(d) / "o"), "--theory", str(Path(d) / "theory.csv"), "--no-png", "--boot", "20",
                         "--arms", "^nothing$"])
            self.assertEqual(e.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
