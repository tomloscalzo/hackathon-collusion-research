#!/usr/bin/env python3
"""Run-status dashboard (U7): one self-contained HTML page from a run root and its grid.csv. Standard library only.

Usage: python -X utf8 tools/trial/status_page.py ROOT [--grid ROOT/grid.csv] [--out ROOT/status.html]
                                                  [--superseded ROOT/superseded.csv] [--rerun-root DIR ...] [--watch] [--interval 60] [--stale-seconds 900]
Writes the page once, or with --watch rewrites it every --interval seconds until interrupted. The page refreshes itself
every 60 s (meta refresh), has no external assets and follows the light/dark setting. Exit 0 ok, 2 on a missing root or grid.

The grid: one row per (arm, condition_texts), one column per (penalty point, [thinking if it varies], slice). Each cell is
a trial of grid.csv, found by its trial_id as a directory name up to 3 levels below ROOT (ROOT/<arm>/<trial_id>/ or
ROOT/trials/<arm>/<trial_id>/). Colours: white = not started (no directory), yellow = running (no DONE/FAILED marker and a
file touched within --stale-seconds), green = DONE, red = FAILED (DONE wins when both exist: a later rerun succeeded),
hatched grey = stalled (a directory without a marker and no recent activity: crashed or killed runner). Pilot rows get a
dashed border. Counts, elapsed time (first trial start to now, or to the last finish when nothing runs), cost (meter file,
same names as runs_registry.py) and token totals (sum of tokens_in/tokens_out in each trial's events.jsonl) are shown.

Other kinds of root (N5): the same command works for each.
  * Neutral twin root: same trial ids as the anchored root; the root's payoff_examples condition ("anchored" or "neutral") is
    read from the grid column payoff_examples, else the grid `options` JSON, else a trial's params.json (top level, options
    or settings), else "anchored" (the default before the option existed); shown in the sub-title and per row when mixed.
  * Truncation-rerun root: trial ids with the suffix __x32k. ROOT/superseded.csv (columns original_id,rerun_id,reason, written
    by trunc_rerun.py; --superseded FILE overrides) marks each listed original as superseded: a grey crossed cell, left out
    of the total and of finished, never counted as failed or done. A rerun cell sits in its own column ("... x32k") next to its
    original, its tooltip names the original id; a rerun id missing from grid.csv is made from the original's grid row, but
    only when its directory exists under ROOT or under a --rerun-root DIR (repeatable, same meaning as collect.py: the real
    layout keeps superseded.csv in the original root and runs the reruns in a separate root). Without that directory the
    original is shown as "superseded, rerun in other root" and no phantom not-started cell is added. A superseded original
    that is still RUNNING stays visible and counted as running. Elapsed time, game time, tokens and cost still include the
    superseded originals (the page says so).
  * Condition-text rerun root: rows are split by condition_texts as always; give the root its own grid.csv.
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import competitiveness  # noqa: E402  (U16)
import runs_registry  # noqa: E402

MARKERS = ("DONE", "FAILED")
TRIAL_FILES = ("grid_row.json", "params.json", "events.jsonl", "DONE", "FAILED")
STATES = ("done", "running", "failed", "stalled", "notstarted")
LABEL = {"done": "done", "running": "running", "failed": "failed", "stalled": "stalled", "notstarted": "not started"}
MAX_DEPTH = 3
RERUN_SUFFIX = re.compile(r"__x32k$")
SUPERSEDED_FILE = "superseded.csv"
DEFAULT_PAYOFF = "anchored"


def load_superseded(path):
    """{original_id: (rerun_id, reason)} from a superseded.csv (original_id,rerun_id,reason); {} when absent or unreadable."""
    out = {}
    try:
        for r in load_grid(path):
            o = (r.get("original_id") or "").strip()
            if o:
                out[o] = ((r.get("rerun_id") or "").strip(), (r.get("reason") or "").strip())
    except (OSError, ValueError, csv.Error):
        pass
    return out


def _payoff_from(obj):
    if isinstance(obj, dict):
        v = obj.get("payoff_examples")
        if isinstance(v, str) and v:
            return v
        for k in ("options", "settings", "market"):
            sub = obj.get(k)
            if isinstance(sub, str):
                try:
                    sub = json.loads(sub)
                except ValueError:
                    sub = None
            if isinstance(sub, dict) and isinstance(sub.get("payoff_examples"), str) and sub["payoff_examples"]:
                return sub["payoff_examples"]
    return ""


def payoff_condition(row, d):
    """payoff_examples condition of one trial: grid column, grid options JSON, the trial's params.json, else the default."""
    v = (row.get("payoff_examples") or "").strip() or _payoff_from(row)
    if not v and d is not None:
        for fn in ("params.json", "grid_row.json"):
            try:
                v = _payoff_from(json.loads((d / fn).read_text(encoding="utf-8-sig")))
            except (OSError, ValueError):
                v = ""
            if v:
                break
    return v or DEFAULT_PAYOFF


def index_dirs(root):
    """Maps directory name -> path for trial-like directories up to MAX_DEPTH below root."""
    found = {}
    base = str(root)
    for cur, dirs, files in os.walk(base):
        depth = cur[len(base):].count(os.sep)
        if depth > 0 and any(f in files for f in TRIAL_FILES):
            found.setdefault(os.path.basename(cur), Path(cur))
            dirs[:] = []
        elif depth >= MAX_DEPTH:
            dirs[:] = []
    return found


def mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return None


def latest_activity(d):
    best = 0.0
    try:
        for e in os.scandir(d):
            try:
                best = max(best, e.stat().st_mtime)
            except OSError:
                pass
    except OSError:
        pass
    return best or None


def read_tokens(d):
    tin = tout = 0
    try:
        with open(d / "events.jsonl", encoding="utf-8", errors="replace") as f:
            for ln in f:
                try:
                    ev = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(ev, dict):
                    a, b = ev.get("tokens_in"), ev.get("tokens_out")
                    if isinstance(a, (int, float)) and not isinstance(a, bool):
                        tin += int(a)
                    if isinstance(b, (int, float)) and not isinstance(b, bool):
                        tout += int(b)
    except OSError:
        pass
    return tin, tout


def classify(d, now, stale):
    if d is None:
        return "notstarted"
    if (d / "DONE").exists():
        return "done"
    if (d / "FAILED").exists():
        return "failed"
    act = latest_activity(d)
    return "running" if act is not None and now - act <= stale else "stalled"


def load_grid(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(s):
    try:
        return (0, float(s), "")
    except (TypeError, ValueError):
        return (1, 0.0, str(s))


def collect(root, grid_path, now=None, stale=900, superseded_path=None, rerun_roots=()):
    root = Path(root)
    now = time.time() if now is None else now
    rows = load_grid(grid_path)
    sup = load_superseded(Path(superseded_path) if superseded_path else root / SUPERSEDED_FILE)
    have = {r.get("trial_id", "") for r in rows}
    by_id = {r.get("trial_id", ""): r for r in rows}
    dirs = index_dirs(root)
    for rr in rerun_roots or ():
        for k, v in index_dirs(Path(rr)).items():
            dirs.setdefault(k, v)
    for o, (rid, _why) in sup.items():   # a rerun the grid does not list: made from its original's row, if it exists here
        if rid and rid not in have and o in by_id and rid in dirs:
            rows.append(dict(by_id[o], trial_id=rid))
            have.add(rid)
    rerun_of = {rid: o for o, (rid, _w) in sup.items() if rid}
    multi_think = len({r.get("thinking", "") for r in rows}) > 1
    multi_model = len({r.get("model_profile", "") for r in rows}) > 1
    cells = []
    starts, ends = [], []
    tin = tout = 0
    secs = 0.0
    firms = []
    for r in rows:
        d = dirs.get(r.get("trial_id", ""))
        tid = r.get("trial_id", "")
        state = classify(d, now, stale)
        is_sup = tid in sup and state != "running"   # a superseded original still running stays visible
        sup_running = tid in sup and state == "running"
        original = rerun_of.get(tid) or (RERUN_SUFFIX.sub("", tid) if RERUN_SUFFIX.search(tid) else "")
        payoff = payoff_condition(r, d)
        if d is not None:
            s = mtime(d / "grid_row.json") or mtime(d / "params.json")
            if s:
                starts.append(s)
            for m in MARKERS:
                e = mtime(d / m)
                if e:
                    ends.append(e)
            if state == "done" and not is_sup:
                firms += read_competitiveness(d)
            a, b = read_tokens(d)
            tin += a
            tout += b
            try:
                rs = json.loads((d / "run_stats.json").read_text(encoding="utf-8"))
                if isinstance(rs, dict) and isinstance(rs.get("seconds"), (int, float)):
                    secs += float(rs["seconds"])
            except (OSError, ValueError):
                pass
        col = "p%s" % r.get("penalty_point", "?")
        if multi_think:
            col += " t%s" % r.get("thinking", "?")
        rm = RERUN_SUFFIX.search(tid)
        rtag = rm.group(0)[2:] if rm else ""
        if r.get("slice"):
            col += " s%s" % r["slice"]
        else:  # older grids without a slice column: wording and seed identify the cell
            col += " w%s s%s" % (r.get("wording", "?"), r.get("seed", "?"))
        if rtag:
            col += " " + rtag
        cells.append({"trial_id": r.get("trial_id", ""), "arm": r.get("arm", ""),
                      "condition": r.get("condition_texts", "") + (" [%s]" % r["model_profile"] if multi_model else ""), "communication": r.get("communication", ""),
                      "col": col, "colkey": (num(r.get("penalty_point")), r.get("thinking", "") if multi_think else "",
                                             num(r.get("slice")) if r.get("slice") else (num(r.get("wording")), num(r.get("seed"))),
                                             rtag),
                      "state": state, "superseded": is_sup, "sup_running": sup_running, "other_root": tid in sup and not (sup[tid][0] and sup[tid][0] in dirs),
                      "original": original, "rerun": sup.get(tid, ("",))[0],
                      "reason": sup.get(tid, ("", ""))[1], "payoff": payoff, "pilot": r.get("pilot", "").strip().lower() == "true",
                      "wording": r.get("wording", ""), "seed": r.get("seed", ""), "thinking": r.get("thinking", "")})
    live = [c for c in cells if not c["superseded"]]   # superseded originals are neither finished nor failed
    counts = {s: sum(1 for c in live if c["state"] == s) for s in STATES}
    counts["total"] = len(live)
    payoffs = sorted({c["payoff"] for c in cells})
    cols = sorted({c["colkey"]: c["col"] for c in cells}.items(), key=lambda kv: kv[0])
    rowkeys = []
    for c in cells:
        k = (c["arm"], c["condition"] + (" {payoff_examples=%s}" % c["payoff"] if len(payoffs) > 1 else ""))
        c["rowcond"] = k[1]
        if k not in rowkeys:
            rowkeys.append(k)
    elapsed = 0.0
    if starts:
        elapsed = (now if counts["running"] else max(ends or [now])) - min(starts)
    return {"root": str(root.name), "superseded": len(cells) - len(live), "reruns": sum(1 for c in cells if c["original"]),
            "superseded_running": sum(1 for c in cells if c["sup_running"]),
            "payoff_examples": payoffs, "now": now, "cells": cells, "counts": counts, "rows": rowkeys,
            "columns": [(k, v) for k, v in cols], "elapsed_seconds": max(elapsed, 0.0), "game_seconds": secs,
            "cost_usd": runs_registry.cost_of(root), "tokens_in": tin, "tokens_out": tout,
            "competitiveness": competitiveness.cell_summary(firms)}


def read_competitiveness(d):
    """Firm rows (competitiveness.firm_rows) of a finished trial from its params.json floor and events.jsonl quotes; [] when
    the floor or the events are unreadable."""
    try:
        params = json.loads((d / "params.json").read_text(encoding="utf-8-sig"))
        floor = float(params["competitive_price"])
        tick = float((params.get("market") or {}).get("quoteIncrement") or competitiveness.DEFAULT_TICK)
        evs = [json.loads(x) for x in (d / "events.jsonl").read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []
    return competitiveness.firm_rows([e for e in evs if isinstance(e, dict) and e.get("kind") == "quote"], floor, tick)


def fmt_dur(s):
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return "%dh %02dm" % (h, m) if h else "%dm %02ds" % (m, sec)


CSS = """
:root{--bg:#fff;--fg:#1b1f23;--mut:#5b6670;--line:#c9d1d9;--card:#f6f8fa;--none:#ffffff;--run:#f5d547;--done:#2da44e;
--fail:#d1242f;--stall:#b8bec6}
@media (prefers-color-scheme: dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#9aa4af;--line:#3d444d;--card:#161b22;
--none:#0d1117;--run:#b08800;--done:#238636;--fail:#da3633;--stall:#4b525a}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:12px}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 10px;min-width:90px}
.stat b{display:block;font-size:18px}.stat span{color:var(--mut);font-size:12px}
.wrap{overflow-x:auto}table{border-collapse:separate;border-spacing:2px}
th{font-weight:normal;color:var(--mut);font-size:12px;padding:2px 4px;text-align:center;white-space:nowrap}
th.row{text-align:left;color:var(--fg);padding-right:8px}th.row small{display:block;color:var(--mut)}
.cell{width:26px;height:22px;border:1px solid var(--line);border-radius:3px}
.cell.notstarted{background:var(--none)}.cell.running{background:var(--run)}.cell.done{background:var(--done)}
.cell.failed{background:var(--fail)}
.cell.stalled{background:repeating-linear-gradient(45deg,var(--stall),var(--stall) 4px,var(--none) 4px,var(--none) 8px)}
.cell.superseded{background:repeating-linear-gradient(135deg,var(--stall),var(--stall) 2px,var(--none) 2px,var(--none) 5px);opacity:.5}
.cell.rerun{outline:2px solid var(--fg);outline-offset:-4px}
.cell.pilot{border:2px dashed var(--fg)}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0;color:var(--mut);font-size:12px}
.legend .cell{display:inline-block;width:14px;height:14px;vertical-align:middle;margin-right:4px}
"""


def render(st):
    e = html.escape
    c = st["counts"]
    finished = c["done"] + c["failed"]
    stamp = datetime.fromtimestamp(st["now"]).strftime("%Y-%m-%d %H:%M:%S")
    stats = [("%d / %d" % (finished, c["total"]), "finished"), (str(c["done"]), "done"), (str(c["running"]), "running"),
             (str(c["failed"]), "failed"), (str(c["stalled"]), "stalled"), (str(c["notstarted"]), "not started"),
             (fmt_dur(st["elapsed_seconds"]), "elapsed"), (fmt_dur(st["game_seconds"]), "game time (sum)"),
             ("$" + st["cost_usd"] if st["cost_usd"] else "n/a", "cost (meter file)"),
             ("{:,}".format(st["tokens_in"]), "tokens in"), ("{:,}".format(st["tokens_out"]), "tokens out")]
    if st["superseded"]:
        stats.insert(6, (str(st["superseded"]), "superseded originals (not counted in progress; elapsed, game time, "
                                                "tokens and cost still include them)"))
    cs = st["competitiveness"]
    if cs["firms"]:   # U16: done games only
        stats.append(("%.0f%%" % (100 * cs["always_competitive_share"]), "firms always competitive (%d firms)" % cs["firms"]))
        stats.append(("%.0f%%" % (100 * cs["mean_competitive_share"]), "mean competitive share"))
    by = {(x["arm"], x["rowcond"], x["col"]): x for x in st["cells"]}
    pay = ", ".join(st["payoff_examples"])
    if st["reruns"]:
        pay += "; %d rerun%s" % (st["reruns"], "" if st["reruns"] == 1 else "s")
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta http-equiv="refresh" content="60">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>Run status %s</title><style>%s</style></head><body>" % (e(st["root"]), CSS),
           "<h1>Run status: %s</h1><div class=\"sub\">payoff_examples: %s; updated %s; refreshes every 60 s</div>"
           % (e(st["root"]), e(pay), stamp),
           '<div class="stats">']
    out += ['<div class="stat"><b>%s</b><span>%s</span></div>' % (e(v), e(k)) for v, k in stats]
    out.append('</div><div class="legend">')
    out += ['<span><span class="cell %s"></span>%s</span>' % (s, LABEL[s]) for s in STATES]
    out.append('<span><span class="cell superseded"></span>superseded original</span>'
               '<span><span class="cell done rerun"></span>rerun</span>')
    out.append('<span><span class="cell notstarted pilot"></span>pilot</span></div><div class="wrap"><table><tr><th></th>')
    out += ["<th>%s</th>" % e(v) for _, v in st["columns"]]
    out.append("</tr>")
    for arm, cond in st["rows"]:
        out.append('<tr><th class="row">%s<small>%s</small></th>' % (e(arm), e(cond)))
        for _, col in st["columns"]:
            x = by.get((arm, cond, col))
            if x is None:
                out.append("<td></td>")
                continue
            tip = "%s (%s; wording %s, seed %s)" % (x["trial_id"], LABEL[x["state"]], x["wording"], x["seed"])
            cls = x["state"]
            if x["superseded"]:
                cls = "superseded"
                tip += "; SUPERSEDED by %s%s" % (x["rerun"] or "a rerun", " (%s)" % x["reason"] if x["reason"] else "")
                if x["other_root"]:
                    tip += "; superseded, rerun in other root"
            elif x["sup_running"]:
                tip += "; superseded, but still running"
            elif x["original"]:
                cls += " rerun"
                tip += "; rerun of %s" % x["original"]
            out.append('<td><div class="cell %s%s" title="%s"></div></td>'
                       % (cls, " pilot" if x["pilot"] else "", e(tip, quote=True)))
        out.append("</tr>")
    out.append("</table></div></body></html>")
    return "".join(out)


def write_page(root, grid_path, out, stale=900, superseded_path=None, rerun_roots=()):
    page = render(collect(root, grid_path, stale=stale, superseded_path=superseded_path, rerun_roots=rerun_roots))
    tmp = Path(str(out) + ".tmp")
    tmp.write_text(page, encoding="utf-8")
    os.replace(tmp, out)


def watch(root, grid_path, out, interval=60, stale=900, sleep=time.sleep, max_loops=None, superseded_path=None, rerun_roots=()):
    n = 0
    while True:
        try:
            write_page(root, grid_path, out, stale, superseded_path, rerun_roots)
        except (OSError, ValueError, UnicodeDecodeError) as exc:  # a file caught mid-write: try again next time
            print("status page not written: %s" % exc, file=sys.stderr)
        n += 1
        if max_loops is not None and n >= max_loops:
            return
        sleep(interval)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write a self-contained run-status HTML page for a run root.")
    ap.add_argument("root")
    ap.add_argument("--grid")
    ap.add_argument("--out")
    ap.add_argument("--rerun-root", action="append", default=[], help="a root holding the reruns (repeatable)")
    ap.add_argument("--superseded", help="superseded.csv (default ROOT/superseded.csv when present)")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=float, default=60)
    ap.add_argument("--stale-seconds", type=float, default=900)
    a = ap.parse_args(argv)
    root = Path(a.root)
    grid_path = Path(a.grid) if a.grid else root / "grid.csv"
    out = Path(a.out) if a.out else root / "status.html"
    if not root.is_dir():
        print("not a directory: %s" % root, file=sys.stderr)
        return 2
    if not grid_path.is_file():
        print("grid.csv not found: %s" % grid_path, file=sys.stderr)
        return 2
    try:
        if a.watch:
            watch(root, grid_path, out, a.interval, a.stale_seconds, superseded_path=a.superseded, rerun_roots=a.rerun_root)
        else:
            write_page(root, grid_path, out, a.stale_seconds, a.superseded, a.rerun_root)
    except KeyboardInterrupt:
        pass
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot write the page: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
