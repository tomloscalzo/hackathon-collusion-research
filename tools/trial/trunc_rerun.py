#!/usr/bin/env python3
"""Rerun the thinking-on games that hit a token limit, at larger caps on the 32k profile (unit N3; standard library only).

Owner's rule: any thinking-on game in which ANY call hit its max_tokens (finish_reason "length", for any call type: quote,
talk or question) is rerun in full with larger caps on the 32k profile. The truncated original is kept, marked superseded
(<root>/superseded.csv), and left out of the primary analysis; the rerun takes its place under the original's cell.
A thinking-off game is never rerun, whatever it truncated.

Usage:
  python -X utf8 tools/trial/trunc_rerun.py scan ROOT
  python -X utf8 tools/trial/trunc_rerun.py grid ROOT --out GRID [--source-grid GRID0]
  python -X utf8 tools/trial/trunc_rerun.py supersede ROOT RERUN_ROOT

ROOT is a trials root, as run_grid.py writes it: <ROOT>/<arm>/<trial_id>/ with grid_row.json (the trial's grid row, written
first by run_grid.py), params.json, events.jsonl, calls.jsonl, DONE or FAILED.

scan       list the affected trials (thinking on, and at least one call that stopped at the token limit) with the number of such
           calls per call type. A call "hit its limit" when a record says finish_reason "length" (also spelt finishReason):
           in calls.jsonl (any line; kind game counts as quote, talk, question; probes and vignettes are not game calls) and in
           events.jsonl (kind quote, talk, question, or an attempt event with its call type in `of`; post-game questions are written to the
           same events.jsonl and so counted). The per-type count is the larger of
           the two sources (the engine's calls.jsonl rows carry no finish reason in the written schema, so events.jsonl is
           the usual source). A call skipped by the context clamp (context_clamp_skipped) is NOT a truncation here: only a reply that
           really stopped at the token limit counts. Trials whose id already ends __x32k are listed too, marked, but never chained (see grid).
grid       write the rerun grid. The authoritative original row is the trial's own <trial_dir>/grid_row.json (the exact row
           run_grid.py ran, so it cannot drift from a later grid.csv); --source-grid GRID0 is used for a trial without one.
           Each rerun row is a copy of that row with: trial_id + "__x32k", model_profile qwen3_32b_fp8_32k, context_window
           32768, max_tokens_quote and max_tokens_talk 28672, max_tokens_question 16384. Every other column (arm, seed,
           wording, thinking, options, wave, slice, pilot, timeout_sec ...) is copied unchanged. A trial whose id already ends
           __x32k is skipped with a warning (no chaining). Run it with run_grid.py/run_waves.py into a separate rerun root.
supersede  write ROOT/superseded.csv (header original_id,rerun_id,reason) for the affected originals whose rerun is DONE
           in RERUN_ROOT (found by directory name at any depth). Reruns missing or unfinished are listed on stderr and get no
           row. Idempotent: rows already in the file are kept, the file is rewritten sorted, so a second run changes nothing.
           collect.py reads the file (see its docstring: --rerun-root, --include-superseded).

Exit status: 0 ok, 1 a trial could not be handled (no grid row), 2 usage error.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_grid  # noqa: E402  (GRID_COLS only)

SUFFIX = "__x32k"
PROFILE = "qwen3_32b_fp8_32k"
CONTEXT_WINDOW = 32768
CAPS = {"max_tokens_quote": 28672, "max_tokens_talk": 28672, "max_tokens_question": 16384}
SUPERSEDED = "superseded.csv"
SUP_COLS = ["original_id", "rerun_id", "reason"]
TYPES = ("quote", "talk", "question")
_KIND_TYPE = {"quote": "quote", "game": "quote", "talk": "talk", "question": "question"}


def _jsonl(path):
    """The JSON objects of a jsonl file; unreadable files and bad lines are skipped (a scan must not crash on one bad trial)."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return
    for line in text.splitlines():
        if line.strip():
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if isinstance(o, dict):
                yield o


def _finish(o):
    for k in ("finish_reason", "finishReason"):
        if isinstance(o.get(k), str):
            return o[k]
    return None


def find_trial_dirs(root):
    """Trial directories under root (a directory with grid_row.json, events.jsonl or calls.jsonl), sorted by name."""
    seen = {}
    for pat in ("grid_row.json", "events.jsonl", "calls.jsonl"):
        for p in Path(root).rglob(pat):
            seen[p.parent] = None
    return sorted(seen, key=lambda p: (p.name, str(p)))


def grid_row(trial):
    """The trial's own grid_row.json as a dict of strings, or None."""
    try:
        row = json.loads((Path(trial) / "grid_row.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return {k: ("" if v is None else str(v)) for k, v in row.items()} if isinstance(row, dict) else None


def thinking_on(trial, row=None):
    """True when the game ran with thinking on: grid row thinking (1|0), else params.json thinking, else the id's __t1 / __t0 suffix."""
    row = row if row is not None else grid_row(trial)
    v = (row or {}).get("thinking", "")
    if str(v).strip() == "":
        try:
            p = json.loads((Path(trial) / "params.json").read_text(encoding="utf-8-sig"))
            v = p.get("thinking", (p.get("settings") or {}).get("thinking") if isinstance(p.get("settings"), dict) else "")
        except (OSError, ValueError, AttributeError):
            v = ""
    s = str(v).strip().lower()
    if s in ("1", "true", "on"):
        return True
    if s in ("0", "false", "off"):
        return False
    name = Path(trial).name
    base = name[:-len(SUFFIX)] if name.endswith(SUFFIX) else name
    return base.endswith("__t1")


def truncated_calls(trial):
    """({call type: calls that stopped at the token limit}, source note). Larger of the calls.jsonl and events.jsonl counts."""
    from_calls, from_events = {}, {}
    for o in _jsonl(Path(trial) / "calls.jsonl"):
        t = _KIND_TYPE.get(o.get("kind"))
        if t is None and isinstance(o.get("clamp"), dict):
            t = o["clamp"].get("callType")
        if t in TYPES and _finish(o) == "length":
            from_calls[t] = from_calls.get(t, 0) + 1
    for o in _jsonl(Path(trial) / "events.jsonl"):
        k = o.get("kind")
        t = k if k in TYPES else (o.get("of") if k == "attempt" and o.get("of") in TYPES else None)   # attempt events name the call type in "of"
        if t is not None and _finish(o) == "length":
            from_events[t] = from_events.get(t, 0) + 1
    out = {t: max(from_calls.get(t, 0), from_events.get(t, 0)) for t in TYPES}
    src = "+".join(n for n, d in (("calls", from_calls), ("events", from_events)) if d)
    return {t: n for t, n in out.items() if n}, src


def is_32b(row):
    """True when the row's model_profile is a 32B profile (qwen3_32b...): only those have a 32k twin. A row without a profile is not 32B."""
    return str((row or {}).get("model_profile", "")).startswith("qwen3_32b")


def affected(root):
    """Rows (dict) for the thinking-on trials under root with any truncated call: trial, trial_id, counts, source, rerun_id (bool)."""
    out = []
    for d in find_trial_dirs(root):
        counts, src = truncated_calls(d)
        if counts and thinking_on(d):
            out.append({"trial": d, "trial_id": d.name, "counts": counts, "source": src, "is_rerun": d.name.endswith(SUFFIX), "not_32b": grid_row(d) is not None and not is_32b(grid_row(d)),
                        "status": "failed" if (d / "FAILED").exists() else "done" if (d / "DONE").exists() else "incomplete"})
    return out


def _reason(counts, again=None):
    r = "finish_reason length (%s); rerun at 32k caps" % ", ".join("%s %d" % (t, counts[t]) for t in TYPES if t in counts)
    return r + ("; rerun also truncated (%s)" % ", ".join("%s %d" % (t, again[t]) for t in TYPES if t in again) if again else "")


# ---- scan ----
def cmd_scan(a):
    rows = affected(a.root)
    off = sum(1 for d in find_trial_dirs(a.root) if truncated_calls(d)[0] and not thinking_on(d))
    print("trial_id\tstatus\tquote\ttalk\tquestion\ttotal\tsource\tnote")
    for r in rows:
        c = r["counts"]
        print("\t".join([r["trial_id"], r["status"]] + [str(c.get(t, 0)) for t in TYPES] +
                        [str(sum(c.values())), r["source"], "already a rerun (not chained)" if r["is_rerun"] else "not a 32B profile (grid skips it)" if r["not_32b"] else ""]))
    n_orig = sum(1 for r in rows if not r["is_rerun"])
    print("%d affected thinking-on trial(s) (%d original, %d already reruns); calls: %s" % (
        len(rows), n_orig, len(rows) - n_orig, ", ".join("%s %d" % (t, sum(r["counts"].get(t, 0) for r in rows)) for t in TYPES)))
    if off:
        print("note: %d thinking-off trial(s) with truncated calls are not selected (thinking-off games are never rerun)" % off, file=sys.stderr)
    return 0


# ---- grid ----
MIN_TIMEOUT = 720   # seconds: a 28,672-token reply at about 40 tokens/s


def rerun_row(orig, timeout_sec=None):
    """A rerun grid row: the original's columns unchanged except the id suffix, the profile, the window and the three caps."""
    row = dict(orig)
    row.update(trial_id=orig["trial_id"] + SUFFIX, model_profile=PROFILE, context_window=str(CONTEXT_WINDOW))
    row.update({k: str(v) for k, v in CAPS.items()})
    if timeout_sec is not None:
        row["timeout_sec"] = str(timeout_sec)
    return row


def _source_rows(path):
    if not path:
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["trial_id"]: r for r in csv.DictReader(f)}


def cmd_grid(a):
    src = _source_rows(a.source_grid)
    rows, bad = [], 0
    for r in affected(a.root):
        if r["is_rerun"]:
            print("warning: %s is already a rerun (id ends %s); not rerun again (no chaining)" % (r["trial_id"], SUFFIX), file=sys.stderr)
            continue
        orig = grid_row(r["trial"]) or ({k: "" if v is None else str(v) for k, v in src[r["trial_id"]].items()} if r["trial_id"] in src else None)
        if orig is None or "trial_id" not in orig:
            print("error: no grid row for %s (no grid_row.json; pass --source-grid)" % r["trial_id"], file=sys.stderr)
            bad += 1
            continue
        if not is_32b(orig):
            print("warning: %s has model_profile %r, not a 32B profile; skipped (the 32k twin is a different model; the lead must decide)"
                  % (r["trial_id"], orig.get("model_profile", "")), file=sys.stderr)
            continue
        rows.append(rerun_row(orig, a.timeout_sec))
    short = sorted({r["timeout_sec"] for r in rows if not r["timeout_sec"].strip().isdigit() or int(r["timeout_sec"]) < MIN_TIMEOUT})
    if short:
        print("WARNING: rerun rows have timeout_sec %s, below %d s (28,672 tokens at ~40 tok/s): long replies may time out and fail. "
              "The grid keeps the original value by default; the lead must decide (grid --timeout-sec N overrides it)."
              % (", ".join(short), MIN_TIMEOUT), file=sys.stderr)
    extra = sorted({k for r in rows for k in r} - set(make_grid.GRID_COLS))
    cols = [c for c in make_grid.GRID_COLS if any(c in r for r in rows)] + extra
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols or make_grid.GRID_COLS, lineterminator="\n", restval="")
        w.writeheader()
        w.writerows(rows)
    print("%d rerun trial(s) -> %s" % (len(rows), a.out))
    return 1 if bad else 0


# ---- supersede ----
def read_superseded(root):
    """The rows of <root>/superseded.csv (dicts), [] when the file is absent."""
    p = Path(root) / SUPERSEDED
    if not p.is_file():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("original_id") and r.get("rerun_id")]


def write_superseded(root, rows):
    with open(Path(root) / SUPERSEDED, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, SUP_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(({c: r[c] for c in SUP_COLS} for r in rows), key=lambda r: r["original_id"]))


def cmd_supersede(a):
    reruns = {d.name: d for d in find_trial_dirs(a.rerun_root)}
    rows = {r["original_id"]: r for r in read_superseded(a.root)}
    missing = []
    for r in affected(a.root):
        if r["is_rerun"]:
            continue
        rid = r["trial_id"] + SUFFIX
        d = reruns.get(rid)
        if d is None or not (d / "DONE").exists():
            missing.append("%s (%s)" % (rid, "not found" if d is None else "not DONE"))
            continue
        again = truncated_calls(d)[0]
        rows[r["trial_id"]] = {"original_id": r["trial_id"], "rerun_id": rid, "reason": _reason(r["counts"], again)}
        if again:
            print("warning: rerun %s is itself truncated at 32k caps (kept; not chained)" % rid, file=sys.stderr)
    write_superseded(a.root, list(rows.values()))
    if missing:
        print("missing reruns (original stays in the primary analysis): " + ", ".join(missing), file=sys.stderr)
    print("%d superseded -> %s" % (len(rows), Path(a.root) / SUPERSEDED))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trunc_rerun.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="list thinking-on trials with a call that hit its token limit")
    s.add_argument("root")
    s.set_defaults(fn=cmd_scan)
    g = sub.add_parser("grid", help="write the rerun grid (32k profile, larger caps, ids + %s)" % SUFFIX)
    g.add_argument("root")
    g.add_argument("--out", required=True)
    g.add_argument("--source-grid", help="grid.csv to take the original row from for a trial without grid_row.json")
    g.add_argument("--timeout-sec", type=int, help="set timeout_sec on every rerun row (default: the original's value, copied unchanged)")
    g.set_defaults(fn=cmd_grid)
    u = sub.add_parser("supersede", help="write ROOT/superseded.csv for originals whose rerun is DONE in RERUN_ROOT")
    u.add_argument("root")
    u.add_argument("rerun_root")
    u.set_defaults(fn=cmd_supersede)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
