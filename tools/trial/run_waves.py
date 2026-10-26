#!/usr/bin/env python3
"""Run a grid wave by wave in the spending order, with a spend check between waves (C8.4; scope sections 7 and 14.4).

Usage: python -X utf8 tools/trial/run_waves.py --grid grid.csv --out <trials_root> --config cost.json --stop-line USD
           [--waves 0,1,2] [--dry-run] [run_grid.py options ...] -- <game command with {placeholders}>

The waves are the distinct `wave` numbers of grid.csv (0 = the smoke and pilot-control ramp arms, 1-6 = scope section 7), run
in ascending order, each as one `run_grid.py --wave N` call. Every run_grid.py option (--max-concurrency, --arm, --timeout,
--executor modal --jar ..., ...) is passed through unchanged, and so is --config, so the stop rules and the stage cap
(`stage_cap_usd`, counted per wave call) stay on inside each wave. This script adds:
  * the spend check: before each wave the money spent so far (all DONE trials of the grid under --out, priced with the
    --config rates as run_grid does) is compared with --stop-line. The wave does not start when spent >= stop line, or when
    spent plus the wave's projected cost (trials still to run x the mean cost of a done game so far; no projection before the
    first done game) would pass the line. Exit status 5, with the numbers printed; raise the line and rerun to continue
    (DONE trials are skipped).
  * the stage cap: run_grid applies stage_cap_usd inside each wave call (its count starts from that wave's DONE trials); here the
    cap is also checked against the spend over ALL waves before each wave starts (exit 5).
  * the projection is the mean cost of all done games so far times the trials to run: early cheap waves under-project later ones.
  * a wave that ends with a non-zero run_grid status (1 failures, 3 stop rule, 4 arm paused) ends the run with that status.
  * --dry-run prints the plan (waves, trials to run, already done, spend so far, projected cost and the check result per wave)
    and runs nothing: no process, no Modal call, nothing written under --out.
Exit status: 0 all selected waves done, 2 usage error, 5 stop line, else run_grid.py's status.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid  # noqa: E402
import stop_rules  # noqa: E402

STOP_LINE_EXIT = 5


def trial_dir(out, row):
    return Path(out) / row["arm"] / row["trial_id"]


def spent_so_far(rows, out, cfg):
    """(spent USD, number of done games): the DONE trials of rows, priced as run_grid's monitor prices them."""
    total, n = 0.0, 0
    for r in rows:
        d = trial_dir(out, r)
        if (d / "DONE").exists():
            try:
                secs = float(json.loads((d / "run_stats.json").read_text(encoding="utf-8")).get("seconds", 0.0))
            except (OSError, ValueError):
                secs = 0.0
            total += stop_rules.trial_cost(stop_rules.measure(d, "done", secs, r["arm"]), cfg)
            n += 1
    return total, n


def plan(rows, out, cfg, stop_line, waves=None, arms=None, slices=None, exclude_slices=None):
    """One dict per wave, in order: wave, total, done, todo, spent, projected, ok (the spend check), reason."""
    spent, n_done = spent_so_far(rows, out, cfg)
    rows = run_grid.slice_filter(rows, slices, exclude_slices)
    mean = spent / n_done if n_done else None
    steps = []
    for w in sorted({int(r["wave"]) for r in rows}):
        if waves and w not in waves:
            continue
        mine = [r for r in rows if int(r["wave"]) == w and (not arms or r["arm"] in arms)]
        todo = [r for r in mine if not (trial_dir(out, r) / "DONE").exists()]
        projected = len(todo) * mean if mean is not None else None
        ok, reason = True, ""
        cap = cfg.get("stage_cap_usd")
        if todo and cap and spent >= float(cap):
            ok, reason = False, "spent $%.2f has reached the stage cap $%.2f (counted over all waves here)" % (spent, float(cap))
        elif todo and spent >= stop_line:
            ok, reason = False, "spent $%.2f has reached the stop line $%.2f" % (spent, stop_line)
        elif todo and projected is not None and spent + projected > stop_line:
            ok, reason = False, "spent $%.2f + projected $%.2f for %d trials is over the stop line $%.2f" % (spent, projected, len(todo), stop_line)
        steps.append({"wave": w, "total": len(mine), "done": len(mine) - len(todo), "todo": len(todo), "spent": spent,
                      "projected": projected, "ok": ok, "reason": reason})
    return steps


def describe(steps, stop_line):
    lines = ["stop line $%.2f" % stop_line]
    for s in steps:
        proj = "unknown" if s["projected"] is None else "$%.2f" % s["projected"]
        lines.append("wave %d: %d trials, %d done, %d to run; spent so far $%.2f, projected for this wave %s; %s" % (
            s["wave"], s["total"], s["done"], s["todo"], s["spent"], proj, "ok" if s["ok"] else "WOULD STOP: " + s["reason"]))
    return lines


def _ints(s):
    return {int(x) for x in s.split(",")} if s else None


def main(argv):
    if "--" not in argv:
        print("usage: run_waves.py --grid grid.csv --out DIR --stop-line USD [--config cost.json] [--dry-run] [run_grid options] -- <game command>", file=sys.stderr)
        return 2
    i = argv.index("--")
    ap = argparse.ArgumentParser(prog="run_waves.py", allow_abbrev=False)
    ap.add_argument("--grid", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="")
    ap.add_argument("--stop-line", type=float, required=True, help="USD; no wave starts if the spend would pass it")
    ap.add_argument("--waves", default="", help="comma list of waves to run (default: all in the grid)")
    ap.add_argument("--arm", default="", help="comma list of arms (passed on to run_grid.py; the plan counts only these)")
    ap.add_argument("--slice", default="", help="comma list of grid slices to run (passed on to run_grid.py; the plan counts only these)")
    ap.add_argument("--exclude-slice", default="", help="comma list of grid slices to leave out (passed on; the plan skips them)")
    ap.add_argument("--dry-run", action="store_true")
    a, passthrough = ap.parse_known_args(argv[1:i])
    template = argv[i + 1:]
    if not template:
        print("error: no game command after --", file=sys.stderr)
        return 2
    try:
        rows = run_grid.load_grid(a.grid)
        run_grid.validate_grid(rows)
        run_grid.slice_filter(rows, _ints(a.slice), _ints(a.exclude_slice))      # fails early on a grid without slices
        cfg = json.loads(Path(a.config).read_text(encoding="utf-8-sig")) if a.config else {}
        stop_rules.check_config(cfg)
        if a.stop_line < 0:
            raise ValueError("--stop-line must not be negative")
        waves = _ints(a.waves)
        arms = set(a.arm.split(",")) if a.arm else None
        bad = [x for x in passthrough if x.split("=")[0] in ("--wave", "--limit")]
        if bad:
            raise ValueError("%s is not allowed here (waves come from the grid; use --waves, and no --limit across waves)" % bad[0])
        unknown = sorted((waves or set()) - {int(r["wave"]) for r in rows})
        if unknown:
            raise ValueError("wave(s) %s not in the grid" % ", ".join(map(str, unknown)))
    except (ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if not (float(cfg.get("rate_per_hour") or 0) > 0 or cfg.get("token_price_per_million_in") or cfg.get("token_price_per_million_out")):
        print("warning: --config has no rate_per_hour or token prices, so spend is always $0 and the stop line cannot fire", file=sys.stderr)
    slices, excl = _ints(a.slice), _ints(a.exclude_slice)
    steps = plan(rows, a.out, cfg, a.stop_line, waves, arms, slices, excl)
    if a.dry_run:
        print("dry run: nothing is started")
        print("\n".join(describe(steps, a.stop_line)))
        return 0
    for s in steps:
        if not s["todo"]:
            print("wave %d: nothing to run (%d done)" % (s["wave"], s["done"]), flush=True)
            continue
        s = plan(rows, a.out, cfg, a.stop_line, {s["wave"]}, arms, slices, excl)[0]           # re-priced after the earlier waves
        if not s["ok"]:
            print("STOP LINE before wave %d: %s" % (s["wave"], s["reason"]), flush=True)
            return STOP_LINE_EXIT
        print("wave %d: running %d trials (spent so far $%.2f)" % (s["wave"], s["todo"], s["spent"]), flush=True)
        args = ["run_grid.py", "--grid", a.grid, "--out", a.out, "--wave", str(s["wave"])] + (["--config", a.config] if a.config else []) + (["--arm", a.arm] if a.arm else []) + (["--slice", a.slice] if a.slice else []) + (["--exclude-slice", a.exclude_slice] if a.exclude_slice else []) + passthrough + ["--"] + template
        rc = run_grid.main(args)
        if rc != 0:
            print("wave %d ended with run_grid status %d: stopping" % (s["wave"], rc), flush=True)
            return rc
    print("all selected waves done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
