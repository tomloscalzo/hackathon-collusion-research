#!/usr/bin/env python3
"""Index of the run roots in a runs directory (U5). Standard library only; no network.

Usage: python -X utf8 tools/trial/runs_registry.py [RUNS_DIR]
RUNS_DIR defaults to `runs/` next to the repository (the repo's parent directory). Writes RUNS_INDEX.csv and
RUNS_INDEX.md into RUNS_DIR: one row per root (each immediate subdirectory). Layout and conventions:
docs/runbooks/RESULTS_LAYOUT.md. Exit 0 ok, 2 when RUNS_DIR is not a directory.

Roots are read tolerantly: the standard name is `<YYYY-MM-DD>_<track>_<stage>`; older ad-hoc names (trackm-*, tracks-*,
hc) get the track and stage guessed from the name and the date from the directory's modification time. Two shapes of
content are counted:
  * Track M trial directories (hold params.json, events.jsonl, DONE or FAILED; found at any depth up to 4 below the
    root, e.g. ROOT/<arm>/<trial>/ or ROOT/trials/<arm>/<trial>/): DONE = done, FAILED = failed, neither = unfinished;
  * Track S run lines (`*.jsonl` whose first line is a run-line object with `llm` or `seed`): one done game per line;
    `*.jsonl.partial-*` files count as failed; the commit comes from the sibling `.manifest.json` (gitCommit).
Cost: the first of cost.json, meter.json, cost_meter.json, spend.json in the root, key spent_usd, total_usd, cost_usd
or spent; blank when there is none. Unreadable files are skipped, never fatal.
"""
import csv
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

COLUMNS = ["date", "track", "stage", "arms", "model", "thinking", "commits", "done", "failed", "trials", "cost_usd",
           "status", "path"]
STD = re.compile(r"^(\d{4}-\d{2}-\d{2})_([A-Za-z0-9]+)_(.+)$")
LEGACY = re.compile(r"^track([ms])[-_](.+)$", re.I)
COST_FILES = ["cost.json", "meter.json", "cost_meter.json", "spend.json"]
COST_KEYS = ["spent_usd", "total_usd", "cost_usd", "spent"]
MAX_DEPTH = 4
SIDE = (".cache.jsonl", ".calls.jsonl")


def parse_name(name):
    m = STD.match(name)
    if m:
        return m.group(1), m.group(2).lower(), m.group(3)
    m = LEGACY.match(name)
    if m:
        return "", m.group(1).lower(), m.group(2)
    return "", "", name


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def first_json_line(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            line = f.readline()
        obj = json.loads(line)
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError):
        return None


def count_games(path):
    """Lines of a run-line file that parse as JSON objects (junk or truncated lines are not games)."""
    n = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for ln in f:
                try:
                    if isinstance(json.loads(ln), dict):
                        n += 1
                except ValueError:
                    pass
    except OSError:
        pass
    return n


def thinking_word(v, name=""):
    if v in (True, 1, "on", "1", "true", "True"):
        return "on"
    if v in (False, 0, "off", "0", "false", "False"):
        return "off"
    m = re.search(r"__t([01])$", name)
    return ("on" if m.group(1) == "1" else "off") if m else ""


def cost_of(root):
    for fn in COST_FILES:
        d = load_json(root / fn)
        if isinstance(d, dict):
            for k in COST_KEYS:
                v = d.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                    return "%.2f" % v
    return ""


def is_trial(d):
    return any((d / n).exists() for n in ("params.json", "events.jsonl", "DONE", "FAILED"))


def superseded_ids(root):
    """Original trial ids listed in ROOT/superseded.csv (column original_id); empty when absent or unreadable."""
    try:
        with open(root / "superseded.csv", newline="", encoding="utf-8-sig") as f:
            return {(r.get("original_id") or "").strip() for r in csv.DictReader(f)} - {""}
    except (OSError, ValueError, csv.Error):
        return set()


def scan_root(root):
    """Returns a dict of sets/counters for one root. Finished (DONE/FAILED) trials listed in superseded.csv are not counted."""
    sup = superseded_ids(root)
    acc = {"arms": set(), "models": set(), "thinking": set(), "commits": set(), "done": 0, "failed": 0, "open": 0}
    base = str(root)
    for cur, dirs, files in os.walk(base):
        depth = cur[len(base):].count(os.sep)
        here = Path(cur)
        if depth > 0 and is_trial(here):
            dirs[:] = []
            p = load_json(here / "params.json")
            p = p if isinstance(p, dict) else {}
            if here.name in sup and ((here / "DONE").exists() or (here / "FAILED").exists()):
                continue   # a superseded original: neither done nor failed
            if (here / "DONE").exists():
                acc["done"] += 1
            elif (here / "FAILED").exists():
                acc["failed"] += 1
            else:
                acc["open"] += 1
            arm = p.get("arm") or here.parent.name
            acc["arms"].add(arm if isinstance(arm, str) else "")
            if isinstance(p.get("model"), str) and p["model"]:
                acc["models"].add(p["model"])
            t = thinking_word(p.get("thinking", (p.get("settings") or {}).get("thinking") if isinstance(p.get("settings"), dict) else None), here.name)
            if t:
                acc["thinking"].add(t)
            if isinstance(p.get("code_commit"), str) and p["code_commit"]:
                acc["commits"].add(p["code_commit"][:12])
            continue
        if depth >= MAX_DEPTH:
            dirs[:] = []
        for fn in files:
            if ".jsonl.partial-" in fn:
                acc["failed"] += 1
            elif fn.endswith(".jsonl") and not fn.endswith(SIDE):
                line = first_json_line(here / fn)
                if line is None or not ("llm" in line or "seed" in line):
                    continue
                n = count_games(here / fn)
                acc["done"] += n
                llm = line.get("llm") if isinstance(line.get("llm"), dict) else {}
                acc["arms"].add(str(line.get("arm") or llm.get("arm") or fn))
                if llm.get("model"):
                    acc["models"].add(str(llm["model"]))
                t = thinking_word(llm.get("thinking"))
                if t:
                    acc["thinking"].add(t)
                man = load_json(here / (fn + ".manifest.json"))
                if isinstance(man, dict) and man.get("gitCommit"):
                    acc["commits"].add(str(man["gitCommit"])[:12])
    return acc


def scan(runs_dir):
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        return []
    rows = []
    for root in sorted(p for p in runs_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        date, track, stage = parse_name(root.name)
        if not date:
            try:
                date = datetime.fromtimestamp(root.stat().st_mtime).strftime("%Y-%m-%d")
            except OSError:
                date = ""
        a = scan_root(root)
        total = a["done"] + a["failed"] + a["open"]
        if total == 0:
            status = "empty"
        elif a["failed"]:
            status = "has-failures"
        elif a["open"]:
            status = "incomplete"
        else:
            status = "complete"
        rows.append({"date": date, "track": track, "stage": stage, "arms": ";".join(sorted(a["arms"])),
                     "model": ";".join(sorted(a["models"])), "thinking": ";".join(sorted(a["thinking"])),
                     "commits": ";".join(sorted(a["commits"])), "done": a["done"], "failed": a["failed"],
                     "trials": total, "cost_usd": cost_of(root), "status": status, "path": root.name})
    return rows


def write(runs_dir, rows):
    runs_dir = Path(runs_dir)
    with open(runs_dir / "RUNS_INDEX.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        wr.writeheader()
        wr.writerows(rows)
    lines = ["# Runs index", "", "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in COLUMNS) + " |")
    (runs_dir / "RUNS_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_dir():
    """First existing `runs/` among the ancestors of the repository (works from a checkout and from a worktree)."""
    repo = Path(__file__).resolve().parents[2]
    for anc in repo.parents:
        if (anc / "runs").is_dir():
            return anc / "runs"
    return repo.parent / "runs"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    runs = Path(argv[0]) if argv else default_dir()
    if not runs.is_dir():
        print("runs_registry: not a directory: %s" % runs, file=sys.stderr)
        return 2
    rows = scan(runs)
    write(runs, rows)
    print("runs_registry: %d roots indexed in RUNS_INDEX.csv / RUNS_INDEX.md" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
