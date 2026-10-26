"""Tests for analysis_r.py (C10.4) on mock tables of known ground truth.
Run: python -X utf8 -m unittest tools/trial/test_analysis_r.py"""
import csv
import yaml
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import analysis_r as ar  # noqa: E402
import mock_tables as mt  # noqa: E402


def specs():
    out = []
    for seed in (1, 2):
        out.append(mt.spec(arm="R0", seed=seed, kind="collude"))
        out.append(mt.spec(arm="R1", seed=seed, kind="mid"))
        out.append(mt.spec(arm="R2", seed=seed, kind="collude", defect_at=4, war=2, questions=("confidant",), question_from=3))
        out.append(mt.spec(arm="R3", seed=seed, kind="collude", questions=("public",), refuse_rounds=(3,) if seed == 1 else ()))
    out.append(mt.spec(arm="R2", seed=3, kind="collude", defect_at=4, war=2))  # no R0 twin: unpaired
    return out


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "t"
        mt.write_tables(self.dir, specs())
        self.tables = am.load_tables(self.dir)
        self.games = am.build_games(self.tables, mt.COMP, mt.COLL)


class Differential(Fixture):
    def rows(self, arm, refusals="with"):
        return [r for r in ar.round_differential(self.games, self.tables, "R0", arm, boot=100) if r["refusals"] == refusals]

    def test_r2_per_round_differential_and_first_question_flag(self):
        rows = self.rows("R2")
        self.assertEqual([r["diff"] for r in rows], [0.0, 0.0, 0.0, -0.5, -1.0, -1.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual({r["n_pairs"] for r in rows}, {2})  # the unpaired seed 3 game is not used
        self.assertEqual([r["round"] for r in rows if r["after_first_question"]], [4, 5, 6, 7, 8, 9, 10])  # first question: round 3

    def test_arm_without_questions_counts_after_the_first_round(self):
        rows = self.rows("R1")
        self.assertEqual({r["diff"] for r in rows}, {-0.5})
        self.assertEqual([r["round"] for r in rows if not r["after_first_question"]], [])  # the intervention acts from round 1

    def test_without_refusal_rounds_drops_the_refused_round(self):
        with_, without = self.rows("R3"), self.rows("R3", "without")
        self.assertAlmostEqual([r for r in with_ if r["round"] == 3][0]["diff"], -0.5)  # seed 1 refused: level 0 vs 1, seed 2 equal
        self.assertEqual([r for r in without if r["round"] == 3][0]["n_pairs"], 1)  # the refused pair is left out of the round
        self.assertEqual([r for r in without if r["round"] == 3][0]["diff"], 0.0)

    def test_phase_summary_before_and_after_the_first_question(self):
        s = {(r["arm"], r["phase"], r["refusals"]): r for r in ar.phase_summary(self.games, self.tables, "R0", ["R1", "R2"], boot=100)}
        self.assertEqual(s[("R2", "before", "with")]["diff"], 0.0)
        self.assertAlmostEqual(s[("R2", "after", "with")]["diff"], -2.5 / 7, places=5)
        self.assertEqual(s[("R2", "after", "with")]["n_pairs"], 2)
        self.assertEqual(s[("R1", "after", "with")]["diff"], -0.5)
        self.assertEqual((s[("R1", "before", "with")]["n_pairs"], s[("R1", "before", "with")]["diff"]), (0, ""))

    def test_game_level_contrasts(self):
        rows = ar.game_contrasts(self.games, "R0", ["R2"], 1, 10, boot=50)
        got = {r["measure"]: r for r in rows if r["basis"] == "assigned" and r["refusals"] == "with"}
        self.assertEqual({r["phase"] for r in rows}, {"all"})
        self.assertAlmostEqual(got["level"]["diff"], -0.25)  # 0.75 vs 1.0
        self.assertEqual(got["punishments"]["diff"], 1.0)
        self.assertEqual(got["time_to_high"]["diff"], 0.0)

    def test_game_contrasts_split_at_the_first_question(self):
        rows = ar.game_contrasts(self.games, "R0", ["R2"], 1, 10, boot=50, tables=self.tables)
        got = {(r["phase"], r["measure"]): r for r in rows if r["refusals"] == "with"}
        # first question round 3: before = rounds 1-3 (no defection yet), after = rounds 4-10 (undercut in 4, punishment in 5)
        self.assertEqual((got[("before", "undercuts")]["diff"], got[("before", "punishments")]["diff"]), (0.0, 0.0))
        # the round-4 undercut sits on the window edge, outside view, so the round-5 reply reads as an undercut (documented in analysis_m)
        self.assertEqual((got[("after", "undercuts")]["diff"], got[("after", "punishments")]["diff"]), (1.0, 0.0))
        self.assertAlmostEqual(got[("after", "level")]["diff"], -2.5 / 7, places=5)  # rounds 4-10: (0.5+0+0+4)/7 = 4.5/7 against 1.0
        self.assertEqual(got[("before", "level")]["diff"], 0.0)

    def test_duplicate_pairing_keys_raise(self):
        dup = dict(self.games)
        dup["copy"] = dict(self.games["R2__p1__w0__s1"], meta=dict(self.games["R2__p1__w0__s1"]["meta"], trial_id="copy"))
        with self.assertRaises(ValueError):
            ar.round_differential(dup, self.tables, "R0", "R2")

    def test_missing_control_is_an_error(self):
        with self.assertRaises(ValueError):
            ar.round_differential(self.games, self.tables, "nope", "R2")


class ThinksSaysDoes(Fixture):
    def test_row_per_round_and_seat(self):
        rows = ar.thinks_says_does(self.tables)
        r = [x for x in rows if x["trial_id"] == "R2__p1__w0__s1" and x["round"] == 3 and x["seat"] == "a1"][0]
        self.assertEqual((r["confidant"], r["public"], r["quote"], r["chat"]), ("CONFIDANT-3-a1", "", 4.0, ""))
        r0 = [x for x in rows if x["trial_id"] == "R2__p1__w0__s1" and x["round"] == 3 and x["seat"] == "a0"][0]
        self.assertEqual(r0["chat"], "keep going")
        self.assertEqual([x["confidant"] for x in rows if x["trial_id"] == "R2__p1__w0__s1" and x["round"] == 2 and x["seat"] == "a0"], [""])
        pub = [x for x in rows if x["trial_id"] == "R3__p1__w0__s2" and x["round"] == 1 and x["seat"] == "a0"][0]
        self.assertEqual(pub["public"], "PUBLIC-1-a0")
        self.assertEqual(len([x for x in rows if x["trial_id"] == "R0__p1__w0__s1"]), 20)  # 10 rounds x 2 seats

    def test_post_game_answers_are_kept_apart(self):
        q = self.dir / "questions.csv"
        with open(q, "a", encoding="utf-8", newline="") as f:
            f.write("R3__p1__w0__s2,1,a0,public,post,1,POST-PUBLIC,0,OK,\nR3__p1__w0__s2,99,a0,public,post,1,LATE,0,OK,\n")
        rows = ar.thinks_says_does(am.load_tables(self.dir))
        r = [x for x in rows if x["trial_id"] == "R3__p1__w0__s2" and x["round"] == 1 and x["seat"] == "a0"][0]
        self.assertEqual((r["public"], r["post_public"]), ("PUBLIC-1-a0", "POST-PUBLIC"))
        late = [x for x in rows if x["round"] == 99][0]
        self.assertEqual((late["post_public"], late["quote"]), ("LATE", ""))  # not lost: a row of its own

    def test_imputed_and_refused_flags(self):
        r = [x for x in ar.thinks_says_does(self.tables) if x["trial_id"] == "R3__p1__w0__s1" and x["round"] == 3 and x["seat"] == "a1"][0]
        self.assertEqual((r["refused"], r["imputed"], r["quote"]), (1, 1, 2.0))

    def test_reasoning_column_is_used_when_present(self):
        p = self.dir / "rounds.csv"
        with open(p, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["reasoning"] = "think-%s-%s" % (r["round"], r["seat"]) if r["trial_id"] == "R0__p1__w0__s1" else ""
        am.write_csv(p, rows, list(rows[0]))
        out = ar.thinks_says_does(am.load_tables(self.dir))
        r = [x for x in out if x["trial_id"] == "R0__p1__w0__s1" and x["round"] == 2 and x["seat"] == "a1"][0]
        self.assertEqual(r["reasoning"], "think-2-a1")

    def test_without_a_reasoning_column_the_cell_is_blank(self):
        self.assertEqual({x["reasoning"] for x in ar.thinks_says_does(self.tables)}, {""})


class RefusalTable(Fixture):
    def test_rates_sorted_with_all_rows(self):
        rows = ar.refusal_table(self.tables["refusals"])
        top = rows[0]
        self.assertEqual((top["arm"], top["kind"], top["refusals"], top["calls"]), ("R3", "all", 1, 40))  # highest rate first, pooled row first
        self.assertEqual((rows[1]["arm"], rows[1]["kind"]), ("R3", "quote"))
        self.assertEqual(top["refusal_rate"], "2.5%")
        allrows = [r for r in rows if r["kind"] == "all"]
        self.assertEqual({r["arm"] for r in allrows}, {"R0", "R1", "R2", "R3"})
        self.assertEqual([r for r in rows if r["arm"] == "R0" and r["kind"] == "all"][0]["refusal_rate"], "0%")
        self.assertEqual([r for r in rows if r["arm"] == "R2" and r["kind"] == "all"][0]["calls"], 60)  # 3 games x 20 calls

    def test_empty_rate_when_no_calls(self):
        rows = ar.refusal_table([{"arm": "X", "thinking": "on", "kind": "talk", "trials": "1", "calls": "0", "refusals": "0",
                                  "by_refusal_kind": "", "patterns": "", "trials_with_refusal": "0"}])
        self.assertEqual(rows[0]["refusal_rate"], "")

    def test_html_is_prominent_and_escaped(self):
        rows = ar.refusal_table(self.tables["refusals"])
        rows[0]["patterns"] = "<b>i can't</b>"
        html = ar.refusal_html(rows)
        self.assertIn("<table", html)
        self.assertIn("Refusals", html)
        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<b>i can", html)


class Cli(Fixture):
    def test_cli_writes_all_outputs(self):
        out = Path(self.tmp.name) / "o"
        ar.main([str(self.dir), str(out), "--competitive", "2", "--collusive", "4", "--window-end", "10", "--boot", "50", "--control", "R0", "--arms", "R1,R2,R3"])
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["r_differential_by_round.csv", "r_differential_competitive_by_round.csv",
                                                                  "r_differential_games.csv", "r_differential_phases.csv", "refusal_table.csv",
                                                                  "refusal_table.html", "thinks_says_does.csv"])
        self.assertNotIn(b"\r", (out / "thinks_says_does.csv").read_bytes())

    def test_cli_is_deterministic(self):
        outs = []
        for n in ("a", "b"):
            ar.main([str(self.dir), str(Path(self.tmp.name) / n), "--competitive", "2", "--collusive", "4", "--window-end", "10", "--boot", "50", "--control", "R0", "--arms", "R1,R2,R3"])
            outs.append({f.name: f.read_bytes() for f in (Path(self.tmp.name) / n).iterdir()})
        self.assertEqual(outs[0], outs[1])


def design_specs():
    """Arms named as in trackm_design.yaml (unit U10: the shared control headline-chat and the arms r2f-confidant, r3f-public,
    r2s-confidant, r3s-public, r4-announced; only three of them have run, one of them saved-only)."""
    out = []
    for w in (0, 1):
        out.append(mt.spec(arm="headline-chat", wording=w, seed=101, kind="collude"))
        out.append(mt.spec(arm="r2s-confidant", wording=w, seed=101, kind="mid", questions=("confidant",), question_mode="inreply"))
        out.append(mt.spec(arm="r2f-confidant", wording=w, seed=101, kind="compete", questions=("confidant",), question_from=3))
        out.append(mt.spec(arm="d-conflict", wording=w, seed=101, kind="mid", competitive_flags=True))
        out.append(mt.spec(arm="headline-tacit", wording=w, seed=1, kind="collude"))     # a headline arm of another cell: never the control
    return out


class DesignArmNames(unittest.TestCase):
    """The default control and arms come from the design file's (or grid's) introspection column (quality review Q4)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_cli(self, specs, *flags):
        mt.write_tables(self.root / "t", specs)
        err = io.StringIO()
        d = yaml.safe_load(ar.DESIGN.read_text(encoding="utf-8"))
        d["introspection_cell"] = {"point": 4, "communication": "private"}     # the cell is chosen: R0 = headline-chat
        (self.root / "design.yaml").write_text(yaml.safe_dump(d), encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = ar.main([str(self.root / "t"), str(self.root / "o"), "--competitive", "2", "--collusive", "4",
                            "--window-end", "10", "--boot", "50", "--design", str(self.root / "design.yaml")] + list(flags))
        return code, err.getvalue()

    def read(self, name):
        with open(self.root / "o" / name, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_control_is_the_headline_arm_of_the_cell_communication(self):
        self.assertEqual({"tacit": "headline-tacit", "private": "headline-chat", "monitored": "headline-monitored"}, ar.HEADLINE_OF)
        with tempfile.TemporaryDirectory() as td:
            for comm, want in (("private", "headline-chat"), ("tacit", "headline-tacit"), (None, None)):
                d = yaml.safe_load(ar.DESIGN.read_text(encoding="utf-8"))
                d["introspection_cell"] = {"point": 4, "communication": comm}
                f = Path(td) / "d.yaml"
                f.write_text(yaml.safe_dump(d), encoding="utf-8")
                self.assertEqual(want, ar.headline_control(None, f), comm)
        levels = {"r1-reflection": "R1"}                                      # no R0 arm: the headline arm is the control
        self.assertEqual("headline-chat", ar.select_arms(levels, {"headline-chat", "r1-reflection"}, None, None, "headline-chat")[0])
        with self.assertRaises(ValueError):
            ar.select_arms(levels, {"headline-tacit", "r1-reflection"})       # no cell, no R0, no headline-chat (unit U10 fallback): an error

    def test_default_run_uses_the_design_names(self):
        code, err = self.run_cli(design_specs())
        self.assertEqual(code, 0)
        rows = self.read("r_differential_by_round.csv")
        self.assertEqual({(r["arm"], r["control"]) for r in rows}, {("r2s-confidant", "headline-chat"), ("r2f-confidant", "headline-chat")})
        r1 = [r for r in rows if r["arm"] == "r2s-confidant" and r["refusals"] == "with" and r["round"] == "2"][0]
        self.assertEqual((r1["n_pairs"], r1["diff"]), ("2", "-0.5"))
        self.assertIn("r3f-public", err)   # the design arms with no trials are named in a warning
        self.assertIn("r4-announced", err)

    def test_differential_files_name_the_bootstrap_method(self):
        code, err = self.run_cli(design_specs())   # one seed (101) per wording: the game-level fallback
        self.assertEqual(code, 0)
        self.assertIn("ci_method game", err)
        for n in ar.R_FILES[:3]:
            self.assertEqual({r["ci_method"] for r in self.read(n) if r["n_pairs"] == "2"}, {"game"}, n)

    def test_grid_introspection_column(self):
        specs = [mt.spec(arm=a, wording=w, seed=5, kind=k) for w in (0, 1) for a, k in (("x-ctl", "collude"), ("x-arm", "compete"))]
        with open(self.root / "grid.csv", "w", encoding="utf-8", newline="") as f:
            f.write("trial_id,arm,introspection\n")
            for sp in specs:
                f.write("%s,%s,%s\n" % (mt.trial_id(sp), sp["arm"], "R0" if sp["arm"] == "x-ctl" else "R3"))
            f.write("h__p1__w0__s1__t0,headline-chat,\n")
        code, _ = self.run_cli(specs, "--grid", str(self.root / "grid.csv"))
        self.assertEqual(code, 0)
        self.assertEqual({(r["arm"], r["control"]) for r in self.read("r_differential_by_round.csv")}, {("x-arm", "x-ctl")})

    def test_no_track_r_trials_fails_loudly_but_keeps_the_refusal_table(self):
        code, err = self.run_cli([mt.spec(arm="headline-chat", seed=s) for s in (1, 2)])
        self.assertNotEqual(code, 0)
        self.assertIn("r2f-confidant", err)
        names = sorted(p.name for p in (self.root / "o").iterdir())
        self.assertEqual(names, ["refusal_table.csv", "refusal_table.html", "thinks_says_does.csv"])

    def test_old_default_names_on_design_tables_fail_loudly(self):
        code, err = self.run_cli(design_specs(), "--control", "R0")
        self.assertNotEqual(code, 0)
        self.assertIn("R0", err)
        code, err = self.run_cli(design_specs(), "--arms", "R1,R2")
        self.assertNotEqual(code, 0)
        self.assertIn("R1", err)

    def test_explicit_flags_still_win(self):
        code, _ = self.run_cli(design_specs(), "--control", "headline-chat", "--arms", "r2f-confidant")
        self.assertEqual(code, 0)
        self.assertEqual({r["arm"] for r in self.read("r_differential_by_round.csv")}, {"r2f-confidant"})

    def test_unreadable_design_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as e:
            self.run_cli(design_specs(), "--design", str(self.root / "missing.yaml"))
        self.assertEqual(e.exception.code, 2)


    def grid(self, rows):
        g = self.root / "grid.csv"
        g.write_text("".join(",".join(r) + "\n" for r in rows), encoding="utf-8")
        return str(g)

    def test_spaces_in_the_lists_are_ignored(self):
        code, err = self.run_cli(design_specs(), "--control", " headline-chat", "--arms", "r2s-confidant, r2f-confidant")
        self.assertEqual(code, 0)
        self.assertNotIn("has no trial", err)
        self.assertNotIn("pairs with", err)
        self.assertEqual({r["arm"] for r in self.read("r_differential_by_round.csv")}, {"r2s-confidant", "r2f-confidant"})

    def test_a_failed_run_removes_stale_differential_files(self):
        self.assertEqual(self.run_cli(design_specs())[0], 0)
        code, _ = self.run_cli(design_specs(), "--control", "R0")
        self.assertEqual(code, 1)
        self.assertFalse(any((self.root / "o" / n).exists() for n in ar.R_FILES))

    def test_no_pairable_game_fails_loudly(self):
        specs = [mt.spec(arm="headline-chat", wording=w, seed=101, thinking="off") for w in (0, 1)]
        specs += [mt.spec(arm="r2s-confidant", wording=w, seed=101, thinking="on") for w in (0, 1)]
        code, err = self.run_cli(specs)
        self.assertEqual(code, 1)
        self.assertIn("no game of arm r2s-confidant pairs", err)

    def test_grid_validation(self):
        two_controls = self.grid([("trial_id", "arm", "introspection"), ("t1", "a", "R0"), ("t2", "b", "R0"), ("t3", "c", "R1")])
        self.assertEqual(self.run_cli(design_specs(), "--grid", two_controls)[0], 1)
        for rows in ([("trial_id", "arm")], [("trial_id", "arm", "introspection"), ("t1", "a", "R0"), ("t2", "a", "R1")],
                     [("trial_id", "arm", "introspection")]):
            with self.assertRaises(SystemExit) as e:
                self.run_cli(design_specs(), "--grid", self.grid(rows + [("x", "y", "")] if len(rows[0]) == 2 else rows))
            self.assertEqual(e.exception.code, 2, rows)

    def test_design_validation_and_missing_pyyaml(self):
        bad = self.root / "bad.yaml"
        bad.write_text("arms: [plain-string]\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as e:
            self.run_cli(design_specs(), "--design", str(bad))
        self.assertEqual(e.exception.code, 2)
        saved = sys.modules.get("yaml")
        sys.modules["yaml"] = None
        try:
            with self.assertRaises(SystemExit) as e:
                self.run_cli(design_specs())
            self.assertEqual(e.exception.code, 2)
            self.assertEqual(self.run_cli(design_specs(), "--control", "headline-chat", "--arms", "r2s-confidant")[0], 0)
        finally:
            if saved is None:
                del sys.modules["yaml"]
            else:
                sys.modules["yaml"] = saved

    def test_corrupt_control_counts_as_absent(self):
        mt.write_tables(self.root / "t", design_specs())
        f = self.root / "t" / "trials.csv"
        lines = f.read_text(encoding="utf-8").splitlines()
        f.write_text("\n".join(l.replace(",done,", ",corrupt,") if l.startswith("headline-chat") else l for l in lines) + "\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = ar.main([str(self.root / "t"), str(self.root / "o"), "--competitive", "2", "--collusive", "4", "--boot", "20"])
        self.assertEqual(code, 1)


class InReplyAndCompetitive(unittest.TestCase):
    """Unit U10: inreply question rows (R2s/R3s) like fed ones with a `mode` column; the shared control; the competitive_share
    per-round differential and the D-set differential (the unit U16 leftovers)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_cli(self, specs, *flags):
        mt.write_tables(self.root / "t", specs)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = ar.main([str(self.root / "t"), str(self.root / "o"), "--competitive", "2", "--collusive", "4",
                            "--window-end", "10", "--boot", "50"] + list(flags))
        return code, err.getvalue()

    def read(self, name):
        with open(self.root / "o" / name, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def specs(self):
        out = []
        for seed in (1, 2):
            out.append(mt.spec(arm="headline-chat", seed=seed, kind="collude", competitive_flags=True))
            out.append(mt.spec(arm="r2s-confidant", seed=seed, kind="mid", competitive_flags=True, questions=("confidant",), question_mode="inreply"))
            out.append(mt.spec(arm="r2f-confidant", seed=seed, kind="compete", competitive_flags=True, questions=("confidant",), question_from=3))
            out.append(mt.spec(arm="d-conflict", seed=seed, kind="compete", competitive_flags=True))
            out.append(mt.spec(arm="d-placebo", seed=seed, kind="collude", competitive_flags=True))
        return out

    def test_inreply_rows_count_as_in_game_questions_and_the_mode_column_splits_them(self):
        tables = am.load_tables(self._tables())
        self.assertEqual({"r2s-confidant": 1, "r2f-confidant": 3}, ar.first_question_rounds(tables))
        post = dict(tables["questions"][0], mode="post", trial_id=tables["questions"][0]["trial_id"])
        tables["questions"].append(post)
        self.assertEqual(1, ar.first_question_rounds(tables)["r2s-confidant"])   # a post-game answer sets no first round
        rows = ar.thinks_says_does(am.load_tables(self._tables()))
        self.assertIn("mode", rows[0])
        by_mode = {}
        for r in rows:
            by_mode.setdefault(r["mode"], []).append(r)
        self.assertEqual({"", "fed", "inreply"}, set(by_mode))
        self.assertTrue(all(r["confidant"].startswith("CONFIDANT-") for r in by_mode["inreply"] + by_mode["fed"]))
        self.assertTrue(all(r["trial_id"].startswith("r2s-") for r in by_mode["inreply"]))
        self.assertTrue(all(r["trial_id"].startswith("r2f-") for r in by_mode["fed"]))

    def _tables(self):
        mt.write_tables(self.root / "t", self.specs())
        return self.root / "t"

    def test_shared_control_and_inreply_arm_in_the_differential(self):
        code, err = self.run_cli(self.specs())
        self.assertEqual(0, code, err)
        rows = [r for r in self.read("r_differential_by_round.csv") if r["refusals"] == "with"]
        self.assertEqual({("r2s-confidant", "headline-chat"), ("r2f-confidant", "headline-chat")}, {(r["arm"], r["control"]) for r in rows})
        s = [r for r in rows if r["arm"] == "r2s-confidant"]
        self.assertEqual({"-0.5"}, {r["diff"] for r in s})
        self.assertEqual(["1"], [r["round"] for r in s if not int(r["after_first_question"])])   # the first answer is in round 1
        self.assertEqual("2", [r for r in s if r["round"] == "1"][0]["n_pairs"])

    def test_competitive_share_per_round_differential(self):
        code, err = self.run_cli(self.specs())
        self.assertEqual(0, code, err)
        rows = [r for r in self.read("r_differential_competitive_by_round.csv") if r["refusals"] == "with"]
        self.assertEqual({"competitive_share"}, {r["measure"] for r in rows})
        f = [r for r in rows if r["arm"] == "r2f-confidant"]
        self.assertEqual([""], sorted({r["diff"] for r in f if r["round"] == "1"}))            # round 1 is never scored
        self.assertEqual({"1.0"}, {r["diff"] for r in f if r["round"] != "1"})                  # compete (all competitive) minus collude (none)
        m = [r for r in rows if r["arm"] == "r2s-confidant"]
        self.assertEqual({"0.0"}, {r["diff"] for r in m if r["round"] != "1"})                  # mid is above the floor: not competitive: same as collude

    def test_d_set_differential_against_the_shared_control(self):
        code, err = self.run_cli(self.specs())
        self.assertEqual(0, code, err)
        by_round = self.read("d_differential_by_round.csv")
        self.assertEqual({("d-conflict", "headline-chat"), ("d-placebo", "headline-chat")}, {(r["arm"], r["control"]) for r in by_round})
        self.assertEqual({"level", "competitive_share"}, {r["measure"] for r in by_round})
        c = [r for r in by_round if r["arm"] == "d-conflict" and r["measure"] == "competitive_share" and r["refusals"] == "with" and r["round"] == "4"][0]
        self.assertEqual(("1.0", "2", "1"), (c["diff"], c["n_pairs"], c["after_first_question"]))     # every round counts: the arm acts from round 1
        l = [r for r in by_round if r["arm"] == "d-placebo" and r["measure"] == "level" and r["refusals"] == "with"]
        self.assertEqual({"0.0"}, {r["diff"] for r in l})
        games = self.read("d_differential_games.csv")
        self.assertIn("competitive_share", {r["measure"] for r in games})
        self.assertEqual({"all"}, {r["phase"] for r in games})
        row = [r for r in games if r["contrast"].startswith("d-conflict") and r["measure"] == "competitive_share" and r["refusals"] == "with"][0]
        self.assertEqual("1.0", row["diff"])

    def test_d_set_files_are_written_without_a_track_r_arm_and_removed_when_stale(self):
        specs = [s for s in self.specs() if not s["arm"].startswith("r")]
        code, err = self.run_cli(specs)
        self.assertEqual(1, code)                                    # no Track R arm: the run still fails loudly
        self.assertTrue((self.root / "o" / "d_differential_by_round.csv").exists())
        specs = [s for s in self.specs() if not s["arm"].startswith("d-")]
        self.assertEqual(0, self.run_cli(specs)[0])
        self.assertFalse((self.root / "o" / "d_differential_by_round.csv").exists())   # no D arm: no stale file left
        code, err = self.run_cli([s for s in self.specs() if s["arm"] != "headline-chat" and not s["arm"].startswith("r")], "--control", "d-placebo", "--arms", "d-conflict")
        self.assertIn("no D-set differential", err)                  # the D-set control is absent


if __name__ == "__main__":
    unittest.main()
