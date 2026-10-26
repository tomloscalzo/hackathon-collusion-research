#!/usr/bin/env python3
"""Anchored-versus-neutral payoff examples: paired comparison of two Track M runs (unit N4; standard library only, no numpy).

Usage: python -X utf8 tools/trial/anchor_compare.py <anchored_tables_dir> <neutral_tables_dir> <out.csv>
           [--grid grid.csv] [--start 1] [--end 20] [--seed 20260101] [--boot 2000]

The two dirs are the collect.py tables (trials.csv, rounds.csv) of the same grid played twice: once with the anchored payoff
examples (the default; the examples the prompt prints are 1.54, 2.09 and 3.00) and once with `payoff_examples=neutral` (make_grid.py
--global-options payoff_examples=neutral; the examples are 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00). Trial ids are identical across the two
grids, so a game is paired on (arm, cell, wording, seed, thinking), where the cell is the penalty point. A game that exists on only one side, is
corrupt, or has no rounds is UNPAIRED: it is listed (stdout and <out>.unpaired.csv) and left out of everything.

Per group (arm x cell x thinking) it reports, for the neutral root minus the anchored root, over the paired (wording, seed) units:
  profit_gain_index   the existing definition (baseline_bot.reference_rows): (mean profit per firm per round - pi^N) / (pi^M - pi^N), over the
                      round window --start..--end (default 1..20, the same window and rule as analysis_m's window basis: a game that lacks any
                      round of the window has no gain and drops out of that metric's n_units), with pi^N and
                      pi^M the per-firm Nash and monopoly profit of the cell's scenario. They come from baseline_benchmarks.csv in a tables dir if
                      one has it (baseline_bot.py writes it), else from --grid (grid.csv: arm, penalty_point, scenario_file, via baseline_bot.benchmarks)
  share_anchored_set, share_neutral_set   the share of quotes lying on any point of the anchored set (1.54, 2.09, 3.00) or of the neutral set
                      (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00); share_neutral_set_no_floor is the neutral set without 1.00. The sets are not
                      symmetric: 1.00 is the competitive floor (a firm quotes it for competitive reasons, not because the example is printed) and 3.00 is
                      in BOTH sets, so read share_p3.00 and share_neutral_set_no_floor for the anchoring effect. Shares use all rounds of the
                      game (no window). share_p<point> the share on each single point. Both point sets are computed for
                      both roots. A quote is on a point if it is within 0.005 of it (quotes move in ticks of 0.01). Imputed quote rows (a refused
                      or unparseable reply played at a fallback) are not counted as quotes.
Each game gives one number per metric (gain over its rows; share of its quotes); the group's anchored and neutral values are the means over its
units, `diff` = neutral - anchored. CI: paired bootstrap, B resamples (default 2000) of the (wording, seed) UNITS with replacement (not rows), the
same resample for both roots and all metrics, percentile 95% interval of the mean diff. Deterministic given --seed (default 20260101); a group with
fewer than 2 units has blank bounds.
"""
import argparse
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402
import baseline_bot  # noqa: E402

ANCHORED_POINTS = (1.54, 2.09, 3.00)
NEUTRAL_POINTS = (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00)
NEUTRAL_NO_FLOOR = tuple(p for p in NEUTRAL_POINTS if p != 1.00)
TOL = 0.005
OUT_COLS = ["arm", "cell", "thinking", "metric", "n_units", "anchored", "neutral", "diff", "ci_low", "ci_high"]
UNPAIRED_COLS = ["arm", "cell", "wording", "seed", "thinking", "side", "reason"]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _on(q, p):
    return abs(q - p) <= TOL


def metric_names():
    return (["profit_gain_index", "share_anchored_set", "share_neutral_set", "share_neutral_set_no_floor"]
            + ["share_p%.2f" % p for p in sorted(set(ANCHORED_POINTS) | set(NEUTRAL_POINTS))])


def game_stats(tables, bench, start=1, end=20):
    """{pair key: {metric: value or None}} per usable game, and {pair key: reason} for the unusable ones.
    bench: {(arm, str(penalty_point)): (pi_n, pi_m)}."""
    profit, quotes, played = {}, {}, {}
    for r in tables["rounds"]:
        tid = r["trial_id"]
        p, q = _num(r.get("profit")), _num(r.get("quote"))
        rd = _num(r.get("round"))
        if rd is not None:
            played.setdefault(tid, set()).add(int(rd))
        if p is not None and rd is not None and start <= rd <= end:
            profit.setdefault(tid, []).append(p)
        if q is not None and r.get("imputed") not in ("1", "True"):
            quotes.setdefault(tid, []).append(q)
    stats, bad, dup = {}, {}, set()
    for t in tables["trials"]:
        key = (t["arm"], str(t["penalty_point"]), str(t["wording"]), str(t["seed"]), str(t["thinking"]))
        if t.get("status") == "corrupt":
            bad[key] = "corrupt"
            continue
        if key in stats or key in bad:
            dup.add(key)
            continue
        if t["trial_id"] not in played:
            bad[key] = "no rounds"
            continue
        row = {}
        b = bench.get((t["arm"], str(t["penalty_point"])))
        pr = profit.get(t["trial_id"]) if set(range(start, end + 1)) <= played[t["trial_id"]] else None   # window rule of analysis_m.select
        row["profit_gain_index"] = ((sum(pr) / len(pr) - b[0]) / (b[1] - b[0])
                                    if pr and b and b[1] != b[0] else None)
        qs = quotes.get(t["trial_id"], [])
        share = lambda pts: sum(1 for q in qs if any(_on(q, p) for p in pts)) / len(qs) if qs else None
        row["share_anchored_set"], row["share_neutral_set"] = share(ANCHORED_POINTS), share(NEUTRAL_POINTS)
        row["share_neutral_set_no_floor"] = share(NEUTRAL_NO_FLOOR)
        for p in sorted(set(ANCHORED_POINTS) | set(NEUTRAL_POINTS)):
            row["share_p%.2f" % p] = share((p,))
        stats[key] = row
    for key in dup:   # the same pair key twice on one side: ambiguous, so neither copy is used
        stats.pop(key, None)
        bad[key] = "duplicate pair key"
    return stats, bad


def load_bench(dirs, grid):
    """Per-firm (Nash, monopoly) profit by (arm, penalty_point): baseline_benchmarks.csv of a dir, else computed from the grid."""
    bench = {}
    for d in dirs:
        f = Path(d) / baseline_bot.BENCH_FILE
        if f.exists():
            for k, v in baseline_bot.read_benchmarks(d).items():
                if k in bench and bench[k] != v:
                    raise ValueError("baseline_benchmarks.csv of %s disagrees with another dir for %s" % (d, k))
                bench[k] = v
    if grid:
        with open(grid, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                k = (r["arm"], str(r["penalty_point"]))
                if k not in bench:
                    b = baseline_bot.benchmarks(baseline_bot.market_of(r["scenario_file"]))
                    bench[k] = (b[2], b[3])
    return bench


def _mean(v):
    return sum(v) / len(v)


def missing_benchmarks(tables, bench):
    """The (arm, penalty_point) cells of the tables that have no benchmark entry."""
    return sorted({(t["arm"], str(t["penalty_point"])) for t in tables["trials"]} - set(bench))


def compare(anch, neut, boot=2000, seed=20260101, bench=None, start=1, end=20):
    """(rows, unpaired): rows keyed by OUT_COLS, unpaired keyed by UNPAIRED_COLS. anch, neut: collect tables dicts."""
    bench = bench or {}
    sa, ba = game_stats(anch, bench, start, end)
    sn, bn = game_stats(neut, bench, start, end)
    unpaired = []
    for side, mine, other, mybad, otherbad in (("anchored", sa, sn, ba, bn), ("neutral", sn, sa, bn, ba)):
        for key in sorted(set(mine) | set(mybad)):
            if key in mine and key in other:
                continue
            if key in mybad:
                why = "unusable here: " + mybad[key]
            elif key in otherbad:
                why = "unusable on the other side: " + otherbad[key]
            else:
                why = "missing on the other side"
            unpaired.append(dict(zip(UNPAIRED_COLS[:5], key), side=side, reason=why))
    groups = {}
    for key in sorted(set(sa) & set(sn)):
        groups.setdefault((key[0], key[1], key[4]), []).append(key)
    rng = random.Random(seed)
    rows = []
    for g in sorted(groups):
        keys = sorted(groups[g], key=lambda k: (k[2], k[3]))     # the (wording, seed) units
        n = len(keys)
        idx = [[rng.randrange(n) for _ in range(n)] for _ in range(boot)] if n >= 2 else []
        for m in metric_names():
            d = [None if sa[k][m] is None or sn[k][m] is None else sn[k][m] - sa[k][m] for k in keys]
            ok = [i for i, x in enumerate(d) if x is not None]
            if not ok:
                rows.append(dict(arm=g[0], cell=g[1], thinking=g[2], metric=m, n_units=0, anchored="", neutral="", diff="", ci_low="", ci_high=""))
                continue
            a = _mean([sa[keys[i]][m] for i in ok])
            b = _mean([sn[keys[i]][m] for i in ok])
            lo = hi = ""
            if len(ok) >= 2:
                ds = []
                for s_ in idx:
                    v = [d[i] for i in s_ if d[i] is not None]
                    if v:
                        ds.append(_mean(v))
                ds.sort()
                lo, hi = ds[int(0.025 * len(ds))], ds[min(len(ds) - 1, int(0.975 * len(ds)))]
            rows.append(dict(arm=g[0], cell=g[1], thinking=g[2], metric=m, n_units=len(ok), anchored=round(a, 6), neutral=round(b, 6),
                             diff=round(b - a, 6), ci_low="" if lo == "" else round(lo, 6), ci_high="" if hi == "" else round(hi, 6)))
    return rows, unpaired


def write_csv(path, cols, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def format_table(rows):
    cells = [OUT_COLS] + [[str(r[c]) for c in OUT_COLS] for r in rows]
    width = [max(len(r[i]) for r in cells) for i in range(len(OUT_COLS))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, width)).rstrip() for r in cells)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("anchored")
    ap.add_argument("neutral")
    ap.add_argument("out")
    ap.add_argument("--grid", help="grid.csv, for the Nash and monopoly profit when no baseline_benchmarks.csv is in a tables dir")
    ap.add_argument("--start", type=int, default=1, help="first round of the profit gain window (default 1)")
    ap.add_argument("--end", type=int, default=20, help="last round of the profit gain window (default 20)")
    ap.add_argument("--seed", type=int, default=20260101)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args(argv)
    try:
        bench = load_bench([a.anchored, a.neutral], a.grid)
        ta, tn = am.load_tables(a.anchored), am.load_tables(a.neutral)
        rows, unpaired = compare(ta, tn, a.boot, a.seed, bench, a.start, a.end)
    except (FileNotFoundError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    miss = sorted(set(missing_benchmarks(ta, bench)) | set(missing_benchmarks(tn, bench)))
    if miss:
        print("warning: no benchmarks for %s (baseline_benchmarks.csv or --grid): profit_gain_index is blank there"
              % ", ".join("%s p%s" % m for m in miss), file=sys.stderr)
    print("profit_gain_index window: rounds %d..%d (games lacking part of it drop out of that metric); shares use all rounds" % (a.start, a.end))
    write_csv(a.out, OUT_COLS, rows)
    write_csv(str(a.out) + ".unpaired.csv", UNPAIRED_COLS, unpaired)
    print(format_table(rows))
    for u in unpaired:
        print("unpaired (excluded): %(arm)s p%(cell)s w%(wording)s s%(seed)s thinking %(thinking)s, %(side)s side: %(reason)s" % u)
    print("%d rows -> %s; %d unpaired -> %s.unpaired.csv" % (len(rows), a.out, len(unpaired), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
