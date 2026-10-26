#!/usr/bin/env python3
"""Pick the strongly colluding cell for the follow-on pilots from slice 1 of the headline private-chat arm (U6; scope decision 9).

Usage: python -X utf8 tools/trial/pick_cell.py --grid grid.csv --trials <trials_root> --out cell.json
           [--arm headline-chat] [--slice 1] [--allow-incomplete] [--rerun-root DIR]... [--include-superseded]

Looks at the grid rows of --arm (default headline-chat, the private-chat headline arm) in --slice (default 1: first wording + first
seed) whose communication is private, reads each finished trial with collect.py's own summary, and takes the trial with the highest
collusion_level (derive.build_summary / trials.csv: the mean over rounds of (market price - competitive) / (collusive - competitive),
clamped to 0..1). Ties go to the smaller trial_id, so the choice is deterministic. Every selected trial must be DONE with a collusion
level, else exit 1 (--allow-incomplete picks among the finished ones and says so on stderr). Writes cell.json:
  {"point": <penalty point>, "communication": "private", "source_trial": ..., "collusion_level": ..., "arm": ..., "slice": ..., "thinking": ...,
   "candidates": [{"trial_id", "collusion_level"}, ...]}
A candidate listed in <trials_root>/superseded.csv (a truncation rerun, trunc_rerun.py) is read from its rerun instead, found under
--rerun-root (repeatable) at <root>/<arm>/<original_id>__x32k, when that rerun is DONE; --include-superseded reads the truncated original.
make_grid.py design.yaml grid.csv --cell-file cell.json then runs the arms with `cell_from: introspection_cell` (and the D-set, B and C
pilot arms that use it) at that cell. Exit status: 0 written, 1 nothing to pick from / incomplete, 2 usage error.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import run_grid  # noqa: E402
import trunc_rerun  # noqa: E402


def pick(rows, trials_root, arm="headline-chat", slice_no=1, allow_incomplete=False, rerun_roots=(), include_superseded=False):
    """(cell dict, notes). ValueError when there is nothing to pick or a selected trial is unfinished."""
    chosen = [r for r in run_grid.slice_filter(rows, {slice_no}) if r["arm"] == arm and r["communication"] == "private"]
    if not chosen:
        raise ValueError("no private-chat rows of arm %s in slice %d in the grid" % (arm, slice_no))
    cands, missing = [], []
    pair = {} if include_superseded else {r["original_id"]: r["rerun_id"] for r in trunc_rerun.read_superseded(trials_root)}
    for r in sorted(chosen, key=lambda r: r["trial_id"]):
        d = Path(trials_root) / r["arm"] / r["trial_id"]
        level = ""
        found = False
        for rr in rerun_roots if r["trial_id"] in pair else ():
            if (Path(rr) / r["arm"] / pair[r["trial_id"]] / "DONE").exists():
                d = Path(rr) / r["arm"] / pair[r["trial_id"]]
                found = True
                break
        if r["trial_id"] in pair and not found:
            print("warning: %s is superseded (truncated) but its rerun %s is not DONE under --rerun-root; using the truncated original"
                  % (r["trial_id"], pair[r["trial_id"]]), file=sys.stderr)
        if (d / "DONE").exists() and (d / "events.jsonl").exists():
            level = collect.trial_rows(d)[0].get("collusion_level", "")
        try:
            cands.append((float(level), r))
        except (TypeError, ValueError):
            missing.append(r["trial_id"])
    if missing and not allow_incomplete:
        raise ValueError("%d of %d trials are not finished or have no collusion level (e.g. %s); wait, or pass --allow-incomplete"
                         % (len(missing), len(chosen), missing[0]))
    if not cands:
        raise ValueError("no finished trial with a collusion level among %d" % len(chosen))
    top = max(c[0] for c in cands)
    level, best = top, min((r for c, r in cands if c == top), key=lambda r: r["trial_id"])
    cell = {"point": int(best["penalty_point"]), "communication": best["communication"], "source_trial": best["trial_id"],
            "collusion_level": level, "arm": arm, "slice": slice_no, "thinking": best.get("thinking", ""),
            "candidates": [{"trial_id": r["trial_id"], "collusion_level": c} for c, r in cands]}
    return cell, (["%d trial(s) unfinished and ignored: %s" % (len(missing), ", ".join(missing))] if missing else [])


def main(argv):
    ap = argparse.ArgumentParser(prog="pick_cell.py")
    ap.add_argument("--grid", required=True)
    ap.add_argument("--trials", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", default="headline-chat")
    ap.add_argument("--slice", type=int, default=1)
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--rerun-root", action="append", default=[], help="root of the truncation reruns (trunc_rerun.py); repeatable")
    ap.add_argument("--include-superseded", action="store_true", help="read the truncated originals, not their reruns")
    a = ap.parse_args(argv[1:])
    try:
        cell, notes = pick(run_grid.load_grid(a.grid), a.trials, a.arm, a.slice, a.allow_incomplete, a.rerun_root, a.include_superseded)
    except (ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    for n in notes:
        print("warning: " + n, file=sys.stderr)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(cell, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("cell: point %d, %s (trial %s, collusion level %.4f) -> %s" % (cell["point"], cell["communication"], cell["source_trial"], cell["collusion_level"], a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
