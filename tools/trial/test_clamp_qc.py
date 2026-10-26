"""Unit U3: clamp.csv / clamp_summary.csv / trials.csv clamp columns from collect.py, and qc_report.py."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import qc_report  # noqa: E402


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def clamp_ev(r, seat, kind, key, req, granted, est, attempt=0, skipped=False):
    return {"kind": "context_clamp", "round": r, "seat": seat, "trial": "t", "arm": "a", "call_type": kind, "attempt": attempt,
            "est_prompt_tokens": est, "requested_max_tokens": req, "granted_max_tokens": granted, "skipped": skipped,
            "window": 16384, "margin": 256, "min_tokens": 1024, "draw_key": key}


def write_trial(root, arm, point, thinking, events, mark="DONE"):
    d = Path(root) / (arm + "__p%s__w0__s1__t%d" % (point, 1 if thinking == "on" else 0))
    d.mkdir(parents=True)
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    (d / "params.json").write_text(json.dumps({"arm": arm, "thinking": thinking, "penalty_point": point, "prompt_fingerprint": "f", "code_commit": "c"}), encoding="utf-8")
    (d / mark).write_text("x", encoding="utf-8")
    return d


def quote(r, key, tin, **kw):
    return dict({"kind": "quote", "round": r, "seat": "a0", "quote": 2.0, "tokens_in": tin, "tokens_out": 5, "draw_key": key, "outcome": "OK"}, **kw)


class ClampTables(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "trials"
        # arm A, point 1, thinking on: 4 quote calls, one clamped (8192 -> 6000), one skipped
        write_trial(self.root, "A", 1, "on", [
            quote(1, "q1", 900), quote(2, "q2", 15000),
            clamp_ev(3, "a0", "quote", "q3", 8192, 6000, 10000), quote(3, "q3", 10100),
            clamp_ev(4, "a0", "quote", "q4", 8192, 0, 15900, skipped=True),
            quote(4, "q4", 0, outcome="TRUNCATED", refusal_kind="TRUNCATED", imputed=True, context_clamp_skipped=True)])
        # arm B: clean
        write_trial(self.root, "B", 1, "off", [quote(1, "q1", 700), quote(2, "q2", 800)])
        self.out = Path(self.tmp.name) / "out"
        collect.collect(self.root, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clamp_csv_has_one_row_per_clamp_event_with_reduction_and_real_tokens(self):
        c = rows(self.out / "clamp.csv")
        self.assertEqual(2, len(c))
        a, b = c
        self.assertEqual(("A", "on", "1", "3", "quote", "2192", "False", "10100"),
                         (a["arm"], a["thinking"], a["penalty_point"], a["round"], a["call_type"], a["reduction"], a["skipped"], a["real_tokens_in"]))
        self.assertEqual(("8192", "True", "0"), (b["reduction"], b["skipped"], b["real_tokens_in"]))

    def test_summary_per_arm_cell_mode(self):
        s = {(r["arm"], r["thinking"]): r for r in rows(self.out / "clamp_summary.csv")}
        self.assertEqual(2, len(s))
        a = s[("A", "on")]
        self.assertEqual(("1", "4", "2", "0.5", "1", "2192", "2192"),
                         (a["trials"], a["calls"], a["clamped"], a["clamp_share"], a["skipped"], a["median_reduction"], a["worst_reduction"]))
        self.assertEqual("15900", a["max_prompt_tokens"])
        self.assertEqual("1", a["trials_affected"])
        b = s[("B", "off")]
        self.assertEqual(("0", "0", ""), (b["clamped"], b["skipped"], b["median_reduction"]))

    def test_trials_csv_gains_prompt_and_clamp_columns(self):
        t = {r["arm"]: r for r in rows(self.out / "trials.csv")}
        self.assertEqual(("15900", "2", "1"), (t["A"]["max_prompt_tokens"], t["A"]["clamped_calls"], t["A"]["skipped_calls"]))
        self.assertEqual(("800", "0", "0"), (t["B"]["max_prompt_tokens"], t["B"]["clamped_calls"], t["B"]["skipped_calls"]))

    def test_repair_and_probe_clamps_do_not_inflate_the_share_and_join_by_attempt(self):
        root = Path(self.tmp.name) / "rr"
        write_trial(root, "R", 1, "off", [
            clamp_ev(1, "a0", "quote", "k", 4096, 3000, 9000, attempt=1), quote(1, "k", 111, kind="attempt"), quote(1, "k", 222),
            clamp_ev(1, "a0", "probe", "p", 100, 50, 9000)])
        collect.collect(root, Path(self.tmp.name) / "orr")
        c = rows(Path(self.tmp.name) / "orr" / "clamp.csv")
        self.assertEqual("222", [x for x in c if x["call_type"] == "quote"][0]["real_tokens_in"])
        (s,) = rows(Path(self.tmp.name) / "orr" / "clamp_summary.csv")
        self.assertEqual(("1", "1"), (s["calls"], s["clamped"]))

    def test_a_skipped_flag_without_a_clamp_event_is_still_listed(self):
        root = Path(self.tmp.name) / "r2"
        write_trial(root, "C", 2, "off", [quote(1, "q1", 0, outcome="TRUNCATED", context_clamp_skipped=True)])
        collect.collect(root, Path(self.tmp.name) / "o2")
        (c,) = rows(Path(self.tmp.name) / "o2" / "clamp.csv")
        self.assertEqual(("C", "True", "quote"), (c["arm"], c["skipped"], c["call_type"]))

    def test_no_clamp_events_gives_header_only_and_zero_columns(self):
        root = Path(self.tmp.name) / "r3"
        write_trial(root, "D", 1, "off", [quote(1, "q1", 500)])
        collect.collect(root, Path(self.tmp.name) / "o3")
        self.assertEqual([], rows(Path(self.tmp.name) / "o3" / "clamp.csv"))
        self.assertEqual("0", rows(Path(self.tmp.name) / "o3" / "clamp_summary.csv")[0]["clamped"])

    def test_rerun_is_byte_identical(self):
        again = Path(self.tmp.name) / "again"
        collect.collect(self.root, again)
        for n in ("clamp.csv", "clamp_summary.csv", "trials.csv"):
            self.assertEqual((self.out / n).read_bytes(), (again / n).read_bytes())


class QcReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "trials"
        write_trial(self.root, "A", 1, "on", [quote(1, "q1", 900), clamp_ev(2, "a0", "quote", "q2", 8192, 6000, 10000), quote(2, "q2", 10100)])
        write_trial(self.root, "B", 1, "off", [quote(r, "q%d" % r, 700) for r in range(1, 41)] + [clamp_ev(41, "a0", "talk", "t1", 4096, 3000, 9000)])
        write_trial(self.root, "C", 1, "off", [quote(r, "q%d" % r, 700) for r in range(1, 41)])
        self.out = Path(self.tmp.name) / "out"
        collect.collect(self.root, self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_severity_threshold_and_skipped_rule(self):
        # arm A: 1 of 2 calls clamped = 50% -> severe; arm B: 1 of 40 quotes (2.5%) -> not severe at 5%; C clean
        md = qc_report.build(self.out, 0.05)
        sev = md.split("## Severity flags")[1].split("## Failures")[0]
        self.assertIn("| A |", sev)
        self.assertNotIn("| B |", sev)
        self.assertNotIn("| C |", sev)
        sev2 = qc_report.build(self.out, 0.02).split("## Severity flags")[1].split("## Failures")[0]
        self.assertIn("| B |", sev2)

    def test_any_skipped_call_is_severe_even_below_threshold(self):
        write_trial(self.root, "E", 1, "off", [quote(r, "q%d" % r, 700) for r in range(1, 200)] + [
            clamp_ev(200, "a0", "quote", "z", 8192, 0, 15900, skipped=True), quote(200, "z", 0, outcome="TRUNCATED", context_clamp_skipped=True)])
        collect.collect(self.root, self.out)
        sev = qc_report.build(self.out, 0.9).split("## Severity flags")[1].split("## Failures")[0]
        self.assertIn("| E |", sev)
        self.assertNotIn("| A |", sev)   # 50% < 0.5 is false: A is exactly at the threshold, so it is severe; see next line

    def test_explicit_affected_trial_list_names_each_call(self):
        md = qc_report.build(self.out, 0.05)
        part = md.split("## Trials with clamped or skipped calls")[1]
        self.assertIn("### Arm A: 1 trial(s) affected", part)
        self.assertIn("### Arm B: 1 trial(s) affected", part)
        self.assertNotIn("### Arm C", part)
        self.assertIn("8192 -> 6000", part)
        self.assertIn("4096 -> 3000", part)

    def test_window_overflow_is_recorded(self):
        md = qc_report.build(self.out, 0.05, window=10050)
        part = md.split("## Trials with clamped or skipped calls")[1]
        self.assertIn("yes", part)
        self.assertIn("10050 tokens", part)

    def test_failures_table_counts_statuses(self):
        write_trial(self.root, "F", 1, "off", [quote(1, "q1", 700)], mark="FAILED")
        collect.collect(self.root, self.out)
        md = qc_report.build(self.out, 0.05)
        line = [x for x in md.split("\n") if x.startswith("| F |")][0]
        self.assertEqual(["F", "1", "0", "1", "0", "0"], [c.strip() for c in line.strip("|").split("|")][:6])

    def test_cli_writes_md_and_html_twin_with_lf(self):
        self.assertEqual(0, qc_report.main(["qc_report.py", str(self.out)]))
        raw = (self.out / "qc_report.md").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertIn(b"# Quality check report", raw)
        self.assertTrue((self.out / "qc_report.html").is_file())
        self.assertEqual(2, qc_report.main(["qc_report.py", str(Path(self.tmp.name) / "nope")]))

    def test_old_tables_without_clamp_files_still_report(self):
        (self.out / "clamp.csv").unlink()
        (self.out / "clamp_summary.csv").unlink()
        md = qc_report.build(self.out, 0.05)
        self.assertIn("absent or empty", md)

    def test_competitiveness_section_is_appended_per_arm(self):
        root = Path(self.tmp.name) / "rc"
        d = write_trial(root, "G", 1, "off", [quote(1, "q1", 5), quote(2, "q2", 5)])
        params = json.loads((d / "params.json").read_text(encoding="utf-8"))
        params["competitive_price"] = 2.0
        (d / "params.json").write_text(json.dumps(params), encoding="utf-8")
        write_trial(root, "H", 1, "off", [quote(1, "q1", 5)])        # no competitive_price: named, not scored
        out = Path(self.tmp.name) / "oc"
        collect.collect(root, out)
        md = qc_report.build(out, 0.05)
        self.assertIn("## Competitiveness (unit U16)", md)
        self.assertIn("Arm G (target = lowest rival quote", md)
        self.assertIn("Not scored (no competitive_price in params.json): H__p1__w0__s1__t0", md)


if __name__ == "__main__":
    unittest.main()
