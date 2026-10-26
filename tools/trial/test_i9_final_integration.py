"""Integration I9 (unit U9, the last one): ONE mock end-to-end run over every arm family of trackm_design.yaml, then every
reporting command on its output.
Run: python -X utf8 -m unittest tools/trial/test_i9_final_integration.py      (about 2 min)

The real design file is the source: its arms headline-tacit/-chat/-monitored, n3-group, n3-cheater, start-5tick, the D set
(d-cot-monitor-a/b, d-conflict, d-temptation-a/b, d-placebo), the Track R arms (r2f-confidant, r3f-public, r2s-confidant,
r3s-public, r4-announced) and ctl-32b-joint / ctl-32b-compete are kept with their own options and condition texts; only the
sampling (two wordings, one seed, point 3), the model profiles (mock ones) and the thinking set are changed, and one throwaway
pilot arm is added. Flow, as the runbook runs it:
  1. make_grid (the cell-free design) -> run_waves --slice 1 (slice 1 = first wording of each arm; the cell_from arms are not yet in the grid);
  2. pick_cell.py picks the cell from headline-chat slice 1 -> cell.json;
  3. make_grid --cell-file -> run_grid --slice 1 (the cell_from arms' slice 1; the rest is skipped as DONE), then --exclude-slice 1 (the rest);
  4. collect (pilot rows left out by default, kept by --include-pilot), then qc_report, status_page, runs_registry (on a temporary runs
     directory), intent_classes, baseline_bot (--limit 2), make_theory, analysis_m / analysis_headline / analysis_r on the tables.
The mock LLM is tools/trial/mock_openai.py (mock_collude quotes the monopoly margin; mock_compete the competitive margin;
mock_declineq as collude but declines every question call). The 'tiny' profile has context_window 4,000, so the U2 context clamp binds
(clamp.csv rows, run_stats). No Modal, no network beyond 127.0.0.1.
Needs PyYAML, matplotlib, engine/target/collusion-engine.jar and a JDK; skipped without the jar, JDK or PyYAML.
"""
import copy
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collect  # noqa: E402
import make_grid  # noqa: E402
import stop_rules  # noqa: E402
import test_i3_runner_resume as i3  # noqa: E402
from mock_openai import MockOpenAI  # noqa: E402

if i3.yaml is not None:
    yaml = i3.yaml

KEEP = ["headline-tacit", "headline-chat", "headline-monitored", "n3-group", "n3-cheater", "start-5tick",
        "d-cot-monitor-a", "d-cot-monitor-b", "d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo",
        "r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced", "ctl-32b-joint", "ctl-32b-compete"]
D_SCORE = ["d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo"]
PROFILE = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "timeout_sec": 60, "max_tokens": {"talk": 320, "quote": 400, "question": 400}}
TINY_WINDOW = 4000
PROFILE_OF = {"headline-tacit": "mock_compete", "ctl-32b-compete": "mock_compete", "r2f-confidant": "mock_tiny",
              "r3f-public": "mock_declineq"}            # every other arm: mock_collude
PROFILE_T1 = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "timeout_sec": 60, "max_tokens": {"talk": 4096, "quote": 8192, "question": 4096}}
SEED = 104
WINDOW = ["--window-start", "1", "--window-end", "2"]


def rows_of(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def events(trial):
    return [json.loads(l) for l in (Path(trial) / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def design():
    """The real design's KEEP arms on mock profiles, two wordings, one seed, point 3 (+ the throwaway pilot arm)."""
    real = yaml.safe_load((HERE / "design" / "trackm_design.yaml").read_text(encoding="utf-8"))
    by = {a["name"]: a for a in real["arms"]}
    missing = [n for n in KEEP if n not in by]
    assert not missing, "arms gone from trackm_design.yaml: %s" % missing
    arms = []
    for n in KEEP:
        a = copy.deepcopy(by[n])
        a.update({"wordings": [0, 1], "seeds": [SEED], "model_profile": PROFILE_OF.get(n, "mock_collude")})
        if n == "headline-chat":
            a["thinking"] = [0, 1]        # the control of r2f-confidant, which runs thinking on only
        if n == "r2f-confidant":
            a["thinking"] = [1]           # thinking-off calls ask 400 tokens, so a binding clamp would skip them (min_tokens 1024); thinking-on asks 8,192 and is lowered
        if a.get("points"):
            a["points"] = [3]
        a["wave"] = {"t0": 1, "t1": 2}
        arms.append(a)
    pilot = copy.deepcopy(by["d-placebo"])                      # cell_from without pilot: false = a throwaway pilot row
    pilot.update({"name": "pilot-probe", "wordings": [0, 1], "seeds": [SEED], "model_profile": "mock_collude", "wave": {"t0": 1, "t1": 2}})
    del pilot["pilot"]
    arms.append(pilot)
    prof = {"t0": PROFILE, "t1": PROFILE_T1}
    return {"version": 1, "points": {3: real["points"][3]},
            "model_profiles": {"mock_collude": prof, "mock_compete": prof, "mock_declineq": prof,
                               "mock_tiny": dict(prof, context_window=TINY_WINDOW)},
            "introspection_cell": {"point": None, "communication": None},
            "defaults": {"model_profile": "mock_collude", "firms": 2, "seats": ["llm", "llm"], "communication": "tacit",
                         "condition_texts": {"all": "neutral"}, "wordings": [0, 1], "seeds": [SEED], "thinking": [0],
                         "wave": {"t0": 1, "t1": 2}},
            "arms": arms}


def runner(script, grid, out, base_url, *extra):
    """run_grid.py / run_waves.py with the C14.1 trial command (the mock profiles map to the mock server's models)."""
    tmpl = [sys.executable, "-X", "utf8", "{trial_cmd}", "--trial-dir", "{trial_dir}", "--jar", "{jar}", "--scenarios", "{scenarios}",
            "--java", i3.java_bin(), "--base-url", base_url, "--model", "mock_collude=collude", "--model", "mock_compete=compete",
            "--model", "mock_tiny=collude", "--model", "mock_declineq=collude_declineq",
            "--api-key-env", "COLLUSION_VLLM_KEY", "--code-commit", "0123abcd", "--budget-tokens", "70000000"]
    return [sys.executable, "-X", "utf8", str(HERE / script), "--grid", str(grid), "--out", str(out), "--jar", str(i3.JAR),
            "--max-concurrency", "4"] + list(extra) + ["--"] + tmpl


def sh(cmd, timeout=1500):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise AssertionError("exit %d: %s\n%s\n%s" % (p.returncode, " ".join(map(str, cmd[:6])), p.stdout[-3000:], p.stderr[-3000:]))
    return p


@unittest.skipUnless(i3.available(), "needs PyYAML, engine/target/collusion-engine.jar and a JDK")
class FinalIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = root = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, root, True)
        cls.design = design()
        cls.design_path = root / "design.yaml"
        cls.design_path.write_text(yaml.safe_dump(cls.design, sort_keys=False), encoding="utf-8")
        cls.trials = root / "trials"
        with MockOpenAI() as m:
            # 1. the cell-free grid, slice 1 through run_waves
            g0 = root / "grid0.csv"
            sh([sys.executable, "-X", "utf8", str(HERE / "make_grid.py"), str(cls.design_path), str(g0)])
            cls.rows0 = rows_of(g0)
            cls.wave_out = sh(runner("run_waves.py", g0, cls.trials, m.base_url, "--stop-line", "1000", "--slice", "1")).stdout
            cls.done_after_slice1 = {(r["trial_id"], r["slice"]) for r in cls.rows0 if (cls.trials / r["arm"] / r["trial_id"] / "DONE").exists()}
            # 2. pick the cell from headline-chat slice 1
            cls.cell = root / "cell.json"
            sh([sys.executable, "-X", "utf8", str(HERE / "pick_cell.py"), "--grid", str(g0), "--trials", str(cls.trials), "--out", str(cls.cell)])
            # 3. the grid with the cell: its slice 1, then the rest
            cls.grid = root / "grid.csv"
            sh([sys.executable, "-X", "utf8", str(HERE / "make_grid.py"), str(cls.design_path), str(cls.grid), "--cell-file", str(cls.cell)])
            cls.rows = rows_of(cls.grid)
            cls.slice1_out = sh(runner("run_grid.py", cls.grid, cls.trials, m.base_url, "--slice", "1")).stdout
            cls.rest_out = sh(runner("run_grid.py", cls.grid, cls.trials, m.base_url, "--exclude-slice", "1")).stdout
        for r in cls.rows:
            sh([sys.executable, "-X", "utf8", str(HERE / "derive.py"), str(cls.trials / r["arm"] / r["trial_id"])], timeout=600)
        cls.tables = root / "tables"
        collect.collect(str(cls.trials), str(cls.tables))                       # default: pilot rows left out
        cls.tables_all = root / "tables_all"
        collect.collect(str(cls.trials), str(cls.tables_all), include_pilot=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def cli(self, script, *args, ok=(0,)):
        p = subprocess.run([sys.executable, "-X", "utf8", str(HERE / script)] + [str(a) for a in args], capture_output=True, text=True,
                           timeout=900)
        self.assertIn(p.returncode, ok, "%s exit %d\n%s\n%s" % (script, p.returncode, p.stdout[-2000:], p.stderr[-2000:]))
        return p

    def trial_dir(self, row):
        return self.trials / row["arm"] / row["trial_id"]

    def arm_rows(self, arm):
        return [r for r in self.rows if r["arm"] == arm]

    # ---- the run ----
    def test_slices_and_the_cell(self):
        non_cell0 = {r["arm"] for r in self.rows0}
        self.assertFalse({a for a in non_cell0 if a.startswith(("d-", "r2", "r3", "r4", "pilot"))})    # no cell yet: those arms are skipped
        self.assertEqual({"1"}, {sl for _, sl in self.done_after_slice1})
        self.assertEqual(len([r for r in self.rows0 if r["slice"] == "1"]), len(self.done_after_slice1))
        self.assertTrue(any(r["slice"] == "2" for r in self.rows0))
        self.assertIn("wave 1: running", self.wave_out)
        cell = json.loads(self.cell.read_text(encoding="utf-8"))
        self.assertEqual((3, "private"), (cell["point"], cell["communication"]))
        self.assertTrue({"d-conflict", "r4-announced", "pilot-probe"} <= {r["arm"] for r in self.rows})
        for r in self.rows:
            d = self.trial_dir(r)
            self.assertTrue((d / "DONE").exists() and not (d / "FAILED").exists(), r["trial_id"])
        arms = {r["arm"] for r in self.rows}
        self.assertEqual(set(KEEP) | {"pilot-probe"}, arms)                    # every arm family is in the grid
        self.assertEqual({r["introspection"] for r in self.rows} - {""}, {"R2f", "R3f", "R2s", "R3s", "R4"})

    # ---- collect ----
    def test_arm_families_present_and_pilot_excluded_by_default(self):
        trials = rows_of(self.tables / "trials.csv")
        self.assertEqual(set(KEEP), {t["arm"] for t in trials})
        self.assertNotIn("pilot-probe", {t["arm"] for t in trials})
        in_rounds = {r["trial_id"] for r in rows_of(self.tables / "rounds.csv")}
        self.assertFalse({r["trial_id"] for r in self.arm_rows("pilot-probe")} & in_rounds)
        allt = rows_of(self.tables_all / "trials.csv")
        pil = [t for t in allt if t["arm"] == "pilot-probe"]
        self.assertEqual(2, len(pil))
        self.assertEqual({"1"}, {t["pilot"] for t in pil})
        self.assertEqual({""}, {t["pilot"] for t in allt if t["arm"] != "pilot-probe"})
        self.assertEqual(len(self.rows) - 2, len(trials))
        d_thinking = {t["thinking"] for t in trials if t["arm"].startswith("d-cot-monitor")}
        self.assertTrue(d_thinking and all(x in ("1", "on", "True") for x in d_thinking), d_thinking)

    def test_clamp_records_appear(self):
        clamp = rows_of(self.tables / "clamp.csv")
        self.assertTrue(clamp, "the tiny window must make the U2 clamp bind at least once")
        tiny = {r["trial_id"] for r in self.arm_rows("r2f-confidant")}
        self.assertTrue({c["trial_id"] for c in clamp} & tiny)
        self.assertEqual({str(TINY_WINDOW)}, {t["context_window"] for t in rows_of(self.tables / "trials.csv") if t["arm"] == "r2f-confidant"})
        self.assertTrue(any(int(t["clamped_calls"] or 0) + int(t["skipped_calls"] or 0) > 0
                            for t in rows_of(self.tables / "trials.csv") if t["arm"] == "r2f-confidant"))
        self.assertTrue(rows_of(self.tables / "clamp_summary.csv"))
        # the arms on the standard window are untouched
        self.assertEqual(set(), {c["trial_id"] for c in clamp} & {r["trial_id"] for r in self.arm_rows("headline-chat")})

    def test_dset_self_report_and_question_modes(self):
        rounds = rows_of(self.tables / "rounds.csv")
        self.assertIn("self_report", rounds[0])
        by_trial = {}
        for r in rounds:
            by_trial.setdefault(r["trial_id"], []).append(r)
        for arm in D_SCORE:
            for g in self.arm_rows(arm):
                rs = by_trial[g["trial_id"]]
                self.assertTrue(rs and all(x["self_report"] != "" for x in rs), g["trial_id"])      # an integer score every round
                self.assertTrue(all(x["self_report_kind"] == "integer" and 1 <= int(x["self_report"]) <= 5 for x in rs), g["trial_id"])
        for arm in ["headline-chat", "d-cot-monitor-a", "d-cot-monitor-b"]:
            for g in self.arm_rows(arm):
                self.assertTrue(all(x["self_report"] == "" for x in by_trial[g["trial_id"]]), g["trial_id"])
        for arm, notice in (("d-cot-monitor-a", "cot_monitor_threat_a"), ("d-cot-monitor-b", "cot_monitor_threat_b")):
            for g in self.arm_rows(arm):
                p = json.loads((self.trial_dir(g) / "params.json").read_text(encoding="utf-8"))
                self.assertIn(notice, json.dumps(p.get("condition_texts")), g["trial_id"])
        trials_arm = {t["trial_id"]: t["arm"] for t in rows_of(self.tables / "trials.csv")}
        got = {(trials_arm[q["trial_id"]], q["mode"]) for q in rows_of(self.tables / "questions.csv")}
        self.assertTrue({("r2f-confidant", "fed"), ("r3f-public", "fed"), ("r2s-confidant", "inreply"), ("r3s-public", "inreply"),
                         ("r4-announced", "post")} <= got, got)
        self.assertTrue({m for _, m in got} >= {"fed", "inreply", "post"})

    def test_start_5tick_round_1_violations_handled(self):
        for g in self.arm_rows("start-5tick"):
            ev = events(self.trial_dir(g))
            viol = [e for e in ev if e.get("kind") == "quote" and e.get("round") == 1 and "start_range_violation" in json.dumps(e)]
            self.assertTrue(viol, "the colluding mock quotes 3.00 in round 1, outside the 5-tick range: %s" % g["trial_id"])
            quotes = [e for e in ev if e.get("kind") == "quote"]
            self.assertTrue(quotes and all(e["round"] == 1 or "start_range_violation" not in json.dumps(e) for e in quotes))
            self.assertTrue(any(e.get("kind") == "market" for e in ev))        # the game went on after the imputed round 1
            p = json.loads((self.trial_dir(g) / "params.json").read_text(encoding="utf-8"))
            self.assertIn("start_5tick_rule", json.dumps(p.get("condition_texts")))
        t = [x for x in rows_of(self.tables / "trials.csv") if x["arm"] == "start-5tick"]
        self.assertEqual(2, len(t))
        self.assertEqual({"0"}, {x["refusals"] for x in t})                      # a range violation is a parse failure, not a refusal

    def test_question_declines_do_not_count_toward_the_pause(self):
        trials = [t for t in rows_of(self.tables / "trials.csv") if t["arm"] == "r3f-public"]
        self.assertEqual(2, len(trials))
        self.assertTrue(all(int(t["question_declines"]) > 0 for t in trials))
        self.assertEqual({"0"}, {t["refusals"] for t in trials})
        ref = rows_of(self.tables / "refusals.csv")
        qd = [r for r in ref if r["arm"] == "r3f-public" and r["kind"] == "question"]
        self.assertEqual(1, len(qd))
        self.assertEqual(qd[0]["calls"], qd[0]["refusals"])                             # every question call declined, still tabled
        self.assertGreater(int(qd[0]["calls"]), 0)
        self.assertEqual("0", qd[0]["counts_toward_pause"])                             # ... and none counted toward the pause
        #                                     # still tabled as refusals of the question call
        self.assertEqual({"1"}, {r["counts_toward_pause"] for r in ref if r["arm"] == "r3f-public" and r["kind"] != "question"})
        mon = stop_rules.Monitor(out=lambda *_: None)
        for _ in range(3):                                                        # six done games of the arm
            for g in self.arm_rows("r3f-public"):
                mon.record(stop_rules.measure(self.trial_dir(g), "done", 1.0, "r3f-public"))
        self.assertNotIn("r3f-public", mon.paused)
        ctl = stop_rules.Monitor(out=lambda *_: None)                              # positive control: the same games with quote refusals do pause
        for _ in range(3):
            for g in self.arm_rows("r3f-public"):
                m = stop_rules.measure(self.trial_dir(g), "done", 1.0, "r3f-public")
                m["refusals"] = 1
                ctl.record(m)
        self.assertIn("r3f-public", ctl.paused)

    def test_every_trial_has_chat_where_it_should(self):
        for r in self.rows:
            ev = events(self.trial_dir(r))
            talk = [e for e in ev if e.get("kind") == "talk"]
            self.assertEqual(r["communication"] != "tacit", bool(talk), r["trial_id"])
            self.assertTrue(any(e.get("kind") == "market" for e in ev), r["trial_id"])
        self.assertEqual({"llm,llm,llm"}, {r["seats"] for r in self.arm_rows("n3-group")})
        self.assertEqual({"llm,llm,scripted:defect_once"}, {r["seats"] for r in self.arm_rows("n3-cheater")})

    # ---- the reporting commands ----
    def test_qc_report_status_page_and_registry(self):
        qc = self.root / "qc.md"
        self.cli("qc_report.py", self.tables, "--out", qc)
        text = qc.read_text(encoding="utf-8")
        for arm in ("r2f-confidant", "headline-chat", "d-placebo"):
            self.assertIn(arm, text)
        self.assertIn("clamp", text.lower())
        self.assertTrue(qc.with_suffix(".html").exists())
        page = self.root / "status.html"
        self.cli("status_page.py", self.trials, "--grid", self.grid, "--out", page)
        html = page.read_text(encoding="utf-8")
        self.assertTrue(all(a in html for a in ("headline-chat", "n3-cheater", "d-conflict")))
        runs = self.root / "runs"
        shutil.copytree(self.trials, runs / "2026-10-24_trackm_final" / "trials")
        self.cli("runs_registry.py", runs)
        idx = rows_of(runs / "RUNS_INDEX.csv")
        self.assertEqual(1, len(idx))
        self.assertEqual(str(len(self.rows)), idx[0]["done"])
        self.assertEqual("0", idx[0]["failed"])
        self.assertTrue((runs / "RUNS_INDEX.md").exists())

    def test_intent_classes_and_baseline_bot(self):
        out = self.root / "intent"
        self.cli("intent_classes.py", self.tables, "--out", out, "--grid", self.grid)
        self.assertTrue(any(out.iterdir()))
        base = self.root / "baseline"
        self.cli("baseline_bot.py", "--design", self.design_path, "--out", base, "--jar", i3.JAR, "--limit", "2")
        self.assertTrue(list((base / "tables").glob("*.csv")))
        self.assertTrue((base / "tables" / "baseline_benchmarks.csv").exists())
        out2 = self.root / "intent_b"
        self.cli("intent_classes.py", self.tables, "--out", out2, "--grid", self.grid, "--baseline", "0.1")
        self.assertTrue(any(out2.iterdir()))

    def test_analysis_commands(self):
        m = self.root / "analysis_m"
        self.cli("analysis_m.py", self.tables, m, *WINDOW, "--boot", "100", "--contrast", "headline-chat:headline-tacit")
        summ = rows_of(m / "measures_summary.csv")
        arms = {r["arm"] for r in summ}
        self.assertTrue({"headline-chat", "headline-tacit", "headline-monitored", "n3-group", "d-conflict", "r4-announced"} <= arms, arms)
        self.assertNotIn("pilot-probe", arms)
        chat = [r for r in summ if r["arm"] == "headline-chat" and r["refusals"] == "with" and r["basis"] == "assigned"]
        self.assertTrue(chat and all(abs(float(r["level"]) - 1.0) < 1e-9 for r in chat))
        theory = self.root / "theory.csv"
        self.cli("make_theory.py", theory)
        h = self.root / "headline"
        self.cli("analysis_headline.py", self.tables, h, "--theory", theory, *WINDOW, "--boot", "100")
        self.assertEqual(b"\x89PNG\r\n\x1a\n", (h / "headline.png").read_bytes()[:8])
        self.assertEqual({"theory", "headline-chat", "headline-tacit", "headline-monitored"}, {r["arm"] for r in rows_of(h / "headline_data.csv")})
        r = self.root / "analysis_r"
        self.cli("analysis_r.py", self.tables, r, "--grid", self.grid, *WINDOW, "--boot", "100")
        diff = rows_of(r / "r_differential_by_round.csv")
        self.assertTrue({"r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"} <= {x["arm"] for x in diff})
        self.assertTrue(any(p.name.startswith("d_differential") for p in r.iterdir()))
        # the baseline tables feed the other two commands
        base = self.root / "baseline"
        if not base.exists():
            self.cli("baseline_bot.py", "--design", self.design_path, "--out", base, "--jar", i3.JAR, "--limit", "2")
        self.cli("analysis_m.py", self.tables, self.root / "analysis_mb", *WINDOW, "--boot", "50", "--baseline", base / "tables")


if __name__ == "__main__":
    unittest.main()
