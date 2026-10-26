"""Tests for stop_rules.py and its wiring into run_grid.py (C8.2). Run: python -X utf8 -m unittest tools/trial/test_stop_rules.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid  # noqa: E402
import stop_rules  # noqa: E402


def info(status="done", arm="a", seconds=0.0, calls=10, refusals=0, truncated=0, max_prompt=1000, tin=0, tout=0, rounds=10, talks=0):
    return {"status": status, "arm": arm, "seconds": seconds, "calls": calls, "refusals": refusals, "truncated": truncated,
            "max_prompt_tokens": max_prompt, "tokens_in": tin, "tokens_out": tout, "rounds": rounds, "talks": talks}


class MonitorTest(unittest.TestCase):
    def mon(self, **cfg):
        self.lines = []
        return stop_rules.Monitor(cfg, total=100, out=self.lines.append)

    def feed(self, m, infos):
        reasons = [m.record(i) for i in infos]
        return [r for r in reasons if r]

    def test_three_failures_in_a_row(self):
        m = self.mon()
        self.assertEqual([], self.feed(m, [info("failed"), info("failed"), info("done"), info("failed"), info("failed")]))
        r = self.feed(m, [info("failed")])
        self.assertEqual(1, len(r))
        self.assertIn("3 failed trials in a row", r[0])
        self.assertEqual(r[0], m.stop_reason)

    def test_failure_rate_over_last_20(self):
        m = self.mon()
        pattern = ["done"] * 17 + ["failed"] + ["done"] + ["failed"]      # 2 of 20 = 10%: not "more than"
        self.assertEqual([], self.feed(m, [info(s) for s in pattern]))
        m = self.mon()
        pattern = ["done", "failed", "done", "done", "failed", "done", "done", "failed"] + ["done"] * 12   # 3 of 20, never 3 in a row
        r = self.feed(m, [info(s) for s in pattern])
        self.assertEqual(1, len(r))
        self.assertIn("more than 10%", r[0])

    def test_failure_rate_needs_a_full_window_of_20(self):
        m = self.mon()
        self.assertEqual([], self.feed(m, [info("failed"), info("done"), info("failed"), info("done"), info("failed"), info("done")]))

    def test_old_failures_leave_the_window(self):
        m = self.mon()
        pattern = ["failed", "done", "failed", "done", "done"] + ["done"] * 30 + ["failed", "done", "failed"]
        self.assertEqual([], self.feed(m, [info(s) for s in pattern]))

    def test_cost_from_container_time_and_token_fallback(self):
        cfg = {"rate_per_hour": 4.0, "games_per_container": 20, "token_price_per_million_in": 0.5, "token_price_per_million_out": 2.0}
        self.assertAlmostEqual(3600 * 4.0 / 3600 / 20, stop_rules.trial_cost(info(seconds=3600), cfg))      # 0.20 dollars
        self.assertAlmostEqual(0.5 + 2.0, stop_rules.trial_cost(info(seconds=0, tin=1_000_000, tout=1_000_000), cfg))
        no_rate = dict(cfg, rate_per_hour=0)
        self.assertAlmostEqual(0.5, stop_rules.trial_cost(info(seconds=3600, tin=1_000_000), no_rate))
        self.assertEqual(0.0, stop_rules.trial_cost(info(), {}))

    def test_rolling_cost_over_twice_the_pilot(self):
        m = self.mon(pilot_cost_per_game=0.10, rate_per_hour=1.0, games_per_container=1)
        cheap = info(seconds=360)             # 0.10 dollars
        self.assertEqual([], self.feed(m, [cheap] * 10))
        r = self.feed(m, [info(seconds=1800)] * 10)       # 0.50 dollars each pulls the rolling mean over 0.20
        self.assertTrue(r)
        self.assertIn("rolling cost per game", r[0])

    def test_rolling_cost_needs_five_games(self):
        m = self.mon(pilot_cost_per_game=0.01, rate_per_hour=1.0, games_per_container=1)
        self.assertEqual([], self.feed(m, [info(seconds=3600)] * 4))
        self.assertTrue(self.feed(m, [info(seconds=3600)]))

    def test_stage_cap(self):
        m = self.mon(stage_cap_usd=1.0, rate_per_hour=1.0, games_per_container=1)
        self.assertEqual([], self.feed(m, [info(seconds=1800)]))           # 0.50
        r = self.feed(m, [info(seconds=1800)])                              # reaches 1.00
        self.assertIn("stage cap", r[0])

    def test_prompt_over_90_percent_of_window(self):
        m = self.mon(context_window=10000)
        self.assertEqual([], self.feed(m, [info(max_prompt=9000)]))         # exactly 90%: not above
        r = self.feed(m, [info(max_prompt=9001)])
        self.assertIn("90% of the window", r[0])

    def test_truncation_over_5_percent_of_calls(self):
        m = self.mon()
        self.assertEqual([], self.feed(m, [info(calls=100, truncated=5)]))
        r = self.feed(m, [info(calls=100, truncated=6)])        # 11 of 200 = 5.5%
        self.assertIn("5% of replies", r[0])

    def test_truncation_needs_a_sample(self):
        m = self.mon()
        self.assertEqual([], self.feed(m, [info(calls=5, truncated=2)]))     # fewer than 20 calls so far: no verdict

    def test_arm_pause_over_40_percent_of_games_with_refusals(self):
        m = self.mon()
        five = [info(arm="x", refusals=1)] * 2 + [info(arm="x")] * 3        # 2 of 5 = 40%: not more
        self.assertEqual([], self.feed(m, five))
        self.assertNotIn("x", m.paused)
        self.feed(m, [info(arm="x", refusals=1)])                            # 3 of 6 = 50%
        self.assertIn("x", m.paused)
        self.assertIsNone(m.stop_reason)                                      # pauses the arm only
        self.assertTrue(any("arm x paused" in l for l in self.lines))
        self.assertEqual([], self.feed(m, [info(arm="y")] * 6))
        self.assertNotIn("y", m.paused)

    def test_status_line_every_10_trials(self):
        m = self.mon(rate_per_hour=3.6, games_per_container=1)
        self.feed(m, [info(seconds=100, calls=10, refusals=1, truncated=0, rounds=5, talks=10)] * 9)
        self.assertEqual([], [l for l in self.lines if l.startswith("[")])
        self.feed(m, [info("failed", seconds=100, rounds=5, talks=10)])
        status = [l for l in self.lines if l.startswith("[")]
        self.assertEqual(1, len(status))
        s = status[0]
        for part in ("[10/100]", "done 9", "failed 1", "refusals 9", "truncated 0", "msgs/round 2.0", "$1.00"):
            self.assertIn(part, s)
        self.feed(m, [info()] * 10)
        self.assertEqual(2, len([l for l in self.lines if l.startswith("[")]))


class BoundaryTest(unittest.TestCase):
    def test_pilot_cost_exactly_twice_does_not_fire(self):
        m = stop_rules.Monitor({"pilot_cost_per_game": 0.25, "rate_per_hour": 1.0, "games_per_container": 1}, out=lambda s: None)
        self.assertEqual([None] * 10, [m.record(info(seconds=1800)) for _ in range(10)])        # 0.50 = exactly 2 x 0.25

    def test_failure_rate_waits_for_20_trials(self):
        m = stop_rules.Monitor({}, out=lambda s: None)
        pattern = ["failed", "done", "done", "failed", "done", "done", "failed", "done", "done", "failed",
                   "done", "done", "failed", "done", "done", "failed", "done", "done", "done"]        # 6 of 19, never 3 in a row
        self.assertEqual([None] * 19, [m.record(info(s)) for s in pattern])
        self.assertIn("more than 10%", m.record(info("done")))

    def test_rolling_cost_uses_only_the_last_20_done_games(self):
        m = stop_rules.Monitor({"pilot_cost_per_game": 0.10, "rate_per_hour": 1.0, "games_per_container": 1}, out=lambda s: None)
        for _ in range(4):
            m.record(info(seconds=360))
        for _ in range(20):                                       # 0.12 each: under 2 x 0.10; the early cheap ones must age out too
            self.assertIsNone(m.record(info(seconds=432)))

    def test_config_is_validated(self):
        for bad in ({"stage_cap_usd": "x"}, {"nope": 1}, {"rate_per_hour": -1}, {"rate_per_hour": True}, [1]):
            with self.assertRaises(ValueError):
                stop_rules.Monitor(bad)
        stop_rules.Monitor({"stage_cap_usd": 5, "context_window": 16384})


class MeasureTest(unittest.TestCase):
    def test_measure_reads_events(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            ev = [{"kind": "talk", "round": 1, "tokens_in": 100, "tokens_out": 10},
                  {"kind": "talk", "round": 1, "refusal_kind": "MODEL_TEXT", "tokens_in": 300, "tokens_out": 5},
                  {"kind": "quote", "round": 1, "tokens_in": 200, "tokens_out": 20, "truncated": True},
                  {"kind": "quote", "round": 2, "outcome": "REFUSED", "tokens_in": 150, "tokens_out": 1},
                  {"kind": "quote", "round": 2, "outcome": "TRUNCATED", "tokens_in": 120, "tokens_out": 2},
                  {"kind": "market", "round": 2, "prices": [1, 1]}]
            (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\nnot json\n", encoding="utf-8")
            m = stop_rules.measure(d, "done", 12.5, "a")
            self.assertEqual(("done", "a", 12.5), (m["status"], m["arm"], m["seconds"]))
            self.assertEqual((5, 2, 2, 300, 2), (m["calls"], m["refusals"], m["truncated"], m["max_prompt_tokens"], m["rounds"]))
            self.assertEqual((870, 38), (m["tokens_in"], m["tokens_out"]))
            self.assertEqual(2, m["talks"])
            # C4.3: a repaired first reply (attempt) and a probe are model calls too: counted, with their tokens
            more = ev + [{"kind": "attempt", "of": "quote", "round": 2, "tokens_in": 400, "tokens_out": 50, "truncated": True},
                         {"kind": "probe", "round": 2, "tokens_in": 90, "tokens_out": 9}]
            (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in more) + "\n", encoding="utf-8")
            m2 = stop_rules.measure(d, "done", 1.0, "a")
            self.assertEqual((7, 3, 400, 1360, 97), (m2["calls"], m2["truncated"], m2["max_prompt_tokens"], m2["tokens_in"],
                                                     m2["tokens_out"]))
            # C5.6: a talk message cut at 150 words is not a truncated reply, a done turn is not a message;
            # a reply cut at the token limit (finish_reason length) is truncated whatever its kind
            talk = [{"kind": "talk", "round": 1, "word_capped": True, "finish_reason": "stop", "parsed": {"message": "w", "done": False}},
                    {"kind": "talk", "round": 1, "parsed": {"message": "", "done": True}, "outcome": "REFUSED"},
                    {"kind": "talk", "round": 1, "finish_reason": "length", "parsed": {"message": "x", "done": False}}]
            (d / "events.jsonl").write_text("\n".join(json.dumps(e) for e in talk) + "\n", encoding="utf-8")
            m3 = stop_rules.measure(d, "done", 1.0, "a")
            self.assertEqual((3, 2, 1, 1, 1), (m3["calls"], m3["talks"], m3["truncated"], m3["refusals"], m3["word_capped"]))
            empty = stop_rules.measure(d / "nothing", "failed", 1.0, "a")
            self.assertEqual((0, 0, 0, 0), (empty["calls"], empty["refusals"], empty["truncated"], empty["max_prompt_tokens"]))


class RunnerIntegrationTest(unittest.TestCase):
    STUB = (
        "import sys, json, pathlib\n"
        "d = pathlib.Path(sys.argv[1]); tid = sys.argv[2]\n"
        "ev = [{'kind': 'quote', 'round': 1, 'tokens_in': 100, 'tokens_out': 10}]\n"
        "if 'refuse' in tid: ev[0]['refusal_kind'] = 'MODEL_TEXT'\n"
        "(d / 'events.jsonl').write_text(json.dumps(ev[0]) + '\\n')\n"
        "sys.exit(3 if 'bad' in tid else 0)\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "stub.py").write_text(self.STUB, encoding="utf-8")
        self.cmd = [sys.executable, str(root / "stub.py"), "{trial_dir}", "{trial_id}"]
        self.out = root / "trials"

    def rows(self, names, arm="a"):
        return [{"trial_id": "%s__p1__w0__s%s__t0" % (arm, n), "arm": arm, "wave": "1", "seed": n} for n in names]

    def test_three_bad_trials_in_a_row_stop_the_run_and_skip_the_rest(self):
        rows = self.rows(["bad1", "bad2", "bad3"] + ["ok%d" % i for i in range(6)])
        lines = []
        mon = stop_rules.Monitor({}, total=len(rows), out=lines.append)
        res = run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd), max_concurrency=1, monitor=mon)
        self.assertIn("3 failed trials in a row", res["stopped"])
        self.assertEqual(3, res["counts"]["failed"])
        self.assertEqual(6, res["not_started"])
        self.assertFalse(list(self.out.rglob("ok0*/DONE")))
        self.assertTrue(any("STOP" in l for l in lines))

    def test_refusing_arm_is_paused_other_arm_continues(self):
        rows = self.rows(["refuse%d" % i for i in range(5)] + ["x1", "x2"], arm="r") + self.rows(["f%d" % i for i in range(3)], arm="f")
        mon = stop_rules.Monitor({}, total=len(rows), out=lambda l: None)
        res = run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd), max_concurrency=1, monitor=mon)
        self.assertIsNone(res["stopped"])
        self.assertIn("r", mon.paused)
        self.assertEqual(2, res["counts"]["paused"])                  # r's last two trials were skipped
        self.assertEqual(3, len(list(self.out.glob("f/*/DONE"))))
        self.assertFalse(list(self.out.glob("r/*x1*")))

    def test_stage_cap_with_parallel_workers_and_resume_remembers_spend(self):
        cfg = {"token_price_per_million_in": 10000, "token_price_per_million_out": 0, "stage_cap_usd": 5.5}   # each trial: 100 tokens in = $1
        rows = self.rows(["ok%d" % i for i in range(12)])
        mon = stop_rules.Monitor(cfg, total=12, out=lambda s: None)
        res = run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd), max_concurrency=3, monitor=mon)
        self.assertIn("stage cap", res["stopped"])
        ran = res["counts"]["done"]
        self.assertTrue(6 <= ran <= 8, ran)                       # up to 2 more may already have been running when it fired
        self.assertEqual(12, ran + res["not_started"])
        again = stop_rules.Monitor(cfg, total=12, out=lambda s: None)
        res2 = run_grid.run_grid(rows, self.out, run_grid.LocalExecutor(self.cmd), max_concurrency=1, monitor=again)
        self.assertAlmostEqual(float(ran), sum(again.costs[:ran]))                       # the earlier spend was preloaded
        self.assertIn("stage cap", res2["stopped"])
        self.assertEqual(1, res2["counts"]["done"])                # one trial runs, tips the preloaded spend over the cap, and stops

    def test_paused_arm_gives_exit_status_4(self):
        import csv
        root = Path(self.tmp.name)
        grid = root / "grid.csv"
        rows = self.rows(["refuse%d" % i for i in range(5)] + ["x1"], arm="r")
        with open(grid, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator=chr(10))
            w.writeheader()
            w.writerows(rows)
        code = run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--max-concurrency", "1", "--"] + self.cmd)
        self.assertEqual(4, code)
        self.assertEqual(2, run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--config", str(root / "missing.json"),
                                           "--"] + self.cmd))

    def test_without_monitor_nothing_changes(self):
        res = run_grid.run_grid(self.rows(["bad1", "bad2", "bad3", "bad4", "ok"]), self.out, run_grid.LocalExecutor(self.cmd), max_concurrency=1)
        self.assertEqual({"failed": 4, "done": 1}, res["counts"])
        self.assertIsNone(res["stopped"])

    def test_cli_exit_code_and_config(self):
        import csv
        root = Path(self.tmp.name)
        grid = root / "grid.csv"
        rows = self.rows(["bad1", "bad2", "bad3", "ok"])
        with open(grid, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        cfg = root / "cfg.json"
        cfg.write_text(json.dumps({"stage_cap_usd": 5}), encoding="utf-8")
        code = run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--max-concurrency", "1",
                              "--config", str(cfg), "--"] + self.cmd)
        self.assertEqual(3, code)
        cfg.write_text("{not json", encoding="utf-8")
        self.assertEqual(2, run_grid.main(["run_grid.py", "--grid", str(grid), "--out", str(self.out), "--config", str(cfg), "--"] + self.cmd))


if __name__ == "__main__":
    unittest.main()
