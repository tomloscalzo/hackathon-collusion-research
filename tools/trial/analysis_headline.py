#!/usr/bin/env python3
"""Track M analysis, part 3 (C10.3): the headline figure (scope sections 4.1, 4.5; standard library, matplotlib for the PNG).

Usage: python -X utf8 tools/trial/analysis_headline.py <tables_dir> <out_dir> [--competitive P] [--collusive P] --theory FILE
           [--window-start 1] [--window-end 20] [--basis window|assigned] [--boot 2000] [--seed 0] [--no-png]
           [--arms REGEX] [--baseline DIR]
Collusion level against expected penalty: the theory curve plus one curve per communication condition (the arm), one panel
per thinking mode. Each LLM curve carries its bootstrap band (by game, stratified by wording, or across wordings when a
wording has a single game: column ci_method, see analysis_m.ci_method; no band at a point with fewer than 2 games) and its refusal
rate (all talk, quote and question calls of that arm and thinking mode, from refusals.csv), in the legend and in a note on
the panel (an overall rate: all rounds and penalty points, all call kinds), because refusals are reported prominently (scope 4.5). The figure shows results with refusal rounds; the data
file also holds the results without them.
Writes headline_data.csv (always) and headline.png (needs matplotlib; --no-png skips it; without matplotlib the CSV is
still written and the exit code is 3). The data file has one row per thinking x arm x penalty_point x refusals:
thinking, arm, penalty_point, x, basis, refusals (with|without), n_games, level, level_lo, level_hi, per_wording,
refusal_count, refusal_calls, refusal_rate, imputed_rounds, played_rounds, imputed_round_share (over every round the arm's
games played, all points; shown next to the refusal rate in the legend and note), ci_method. Theory rows have arm `theory` and are repeated for each thinking mode.
--theory is a CSV with columns penalty_point, expected_penalty, theory_level (the x position and theory level of each
point of the slice). Only the headline arms are drawn: --arms (a regular expression, default ^headline-, i.e.
headline-tacit, headline-chat, headline-monitored); a selection that matches no arm, or a penalty point missing from --theory, is an error (exit 2). Basis `window`
(default) is the fixed window on seeds common to the drawn arms at each thinking mode and point (gotcha 13); the other
arms in the tables (smoke, controls, side arms, Track R) neither appear nor take part in the pairing. When the basis keeps
no game (e.g. every game shorter than the window), the tool exits 2 with a hint (--basis assigned or a shorter window).
(U18) --baseline DIR (the tables dir of baseline_bot.py: the scripted undercutter on the same scenarios and seeds) adds, per
thinking mode, rows of arm `baseline` (the baseline pooled over the drawn arms: level = its price index, competitive_share,
profit_gain_index; drawn as a dotted grey line), and the columns baseline_level, baseline_competitive_share,
baseline_profit_gain_index and level_minus_baseline on the LLM rows (matched on thinking, penalty point and basis, not on seeds: prefer --basis assigned for a like-for-like comparison). Without it the CSV and figure are unchanged.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402

COLS = ["thinking", "arm", "penalty_point", "x", "basis", "refusals", "n_games", "level", "level_lo", "level_hi",
        "per_wording", "refusal_count", "refusal_calls", "refusal_rate", "imputed_rounds", "played_rounds", "imputed_round_share",
        "ci_method", "competitive_share", "always_competitive_share"]
STYLES = [("#0072B2", "o", "-"), ("#D55E00", "s", "-"), ("#009E73", "^", "-"), ("#CC79A7", "D", "-")]  # Okabe-Ito, fixed order


def _key(pt):
    """Penalty-point keys compare as numbers when they are numbers ("1" == "1.0"), else as text."""
    try:
        return repr(float(pt))
    except (TypeError, ValueError):
        return str(pt)


def read_theory(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {_key(r["penalty_point"]): (float(r["expected_penalty"]), float(r["theory_level"])) for r in csv.DictReader(f)}


def pct(rate):
    """A rate as a percentage that never reads as zero when refusals happened."""
    return "n/a" if rate == "" else "0%" if rate == 0 else "<0.1%" if rate < 0.001 else "%.1f%%" % (100 * rate)


def refusal_rates(refusals):
    """(arm, thinking) -> (refusals, calls), summed over all kinds in refusals.csv."""
    out = {}
    for r in refusals:
        k = (r["arm"], r["thinking"])
        a, b = out.get(k, (0, 0))
        out[k] = (a + int(r["refusals"] or 0), b + int(r["calls"] or 0))
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return x


def headline_rows(tables, competitive, collusive, theory, start=1, end=20, basis="window", boot=2000, seed=0,
                  arms=am.HEADLINE_ARMS):
    """The headline data rows for the arms matching `arms` (regex; None = every arm). ValueError when none matches."""
    games = am.build_games(tables, competitive, collusive)
    drawn = am.arm_matcher(arms)
    rows = [r for r in am.game_measures(games, start, end) if drawn(r["arm"])]
    if not rows:
        raise ValueError("no measured game belongs to an arm matching %r (arms in the tables: %s)" % (
            arms, ", ".join(sorted({str(g["meta"]["arm"]) for g in games.values()})) or "none"))
    imputed = {}   # (arm, thinking) -> (imputed rounds, played rounds): every round each game played, all points
    for r in rows:
        if r["basis"] == "assigned" and r["refusals"] == "with":
            a, b = imputed.get((r["arm"], r["thinking"]), (0, 0))
            imputed[(r["arm"], r["thinking"])] = (a + r["imputed_rounds"], b + r["played_rounds"])
    if basis == "window":
        rows, _ = am.pair_window(rows, None)   # the drawn arms are the comparison: pair across them only
    rates = refusal_rates(tables.get("refusals", []))
    out = []
    for s in am.summarize([r for r in rows if r["basis"] == basis], boot, seed):
        n_ref, n_calls = rates.get((s["arm"], s["thinking"]), (0, 0))
        n_imp, n_played = imputed.get((s["arm"], s["thinking"]), (0, 0))
        pt = str(s["penalty_point"])
        if _key(pt) not in theory:
            raise ValueError("penalty point %r is not in the theory file (points there: %s)" % (pt, ", ".join(sorted(theory))))
        out.append(dict(thinking=s["thinking"], arm=s["arm"], penalty_point=pt, x=theory[_key(pt)][0],
                        basis=basis, refusals=s["refusals"], n_games=s["n_games"], level=s["level"], level_lo=s["level_lo"],
                        level_hi=s["level_hi"], per_wording=s["per_wording"], refusal_count=n_ref, refusal_calls=n_calls,
                        refusal_rate=n_ref / n_calls if n_calls else "", imputed_rounds=n_imp, played_rounds=n_played,
                        imputed_round_share=n_imp / n_played if n_played else "", ci_method=s["ci_method"],
                        competitive_share=s["competitive_share"], always_competitive_share=s["always_competitive_share"]))
    if not out:
        raise ValueError("no game of the drawn arms has a %s row: every game is shorter than the window %d..%d or "
                         "unpaired; use --basis assigned or a shorter window (--window-end N)" % (basis, start, end)
                         if basis == "window" else "no game of the drawn arms has an %s row" % basis)
    for th in sorted({r["thinking"] for r in out}):
        for ref in am.REFUSALS:
            for pt, (x, lv) in sorted(theory.items(), key=lambda kv: kv[1][0]):
                out.append(dict({c: "" for c in COLS}, thinking=th, arm="theory", penalty_point=pt[:-2] if pt.endswith(".0") else pt, x=x, basis=basis, refusals=ref, level=lv))
    return sorted(out, key=lambda r: (str(r["thinking"]), r["arm"] == "theory", str(r["arm"]), str(r["refusals"]), float(r["x"]) if r["x"] != "" else 0))


BASELINE_COLS = ["profit_gain_index", "baseline_level", "baseline_competitive_share", "baseline_profit_gain_index", "level_minus_baseline"]


def add_baseline(rows, baseline_dir, theory, start=1, end=20, basis="window", arms=am.HEADLINE_ARMS):
    """(U18) rows plus, per thinking mode and penalty point, an arm `baseline` row (the undercutter baseline pooled over the
    drawn arms) and the baseline columns on the LLM rows. The baseline is scripted: its thinking label only mirrors the grid row, so each mode is compared with the same games."""
    import baseline_bot
    pooled = {(r["thinking"], r["penalty_point"]): r for r in baseline_bot.reference_rows(baseline_dir, start, end, arms=arms, pool_label="baseline")
              if r["basis"] == basis}
    blank = {c: "" for c in COLS + BASELINE_COLS}
    out = []
    for r in rows:
        b = pooled.get((r["thinking"], str(r["penalty_point"])))
        out.append(dict(blank, **r, baseline_level=b["price_index"] if b else "",
                        baseline_competitive_share=b["competitive_share"] if b else "",
                        baseline_profit_gain_index=b["profit_gain_index"] if b else "",
                        level_minus_baseline=am._r(r["level"] - b["price_index"]) if b and r["arm"] != "theory" and r["level"] != ""
                        and b["price_index"] != "" else ""))
    for (th, pt), b in sorted(pooled.items()):
        if _key(pt) in theory:
            out.append(dict(blank, thinking=th, arm="baseline", penalty_point=pt, x=theory[_key(pt)][0], basis=basis,
                            refusals="with", n_games=b["n_games"], level=b["price_index"], competitive_share=b["competitive_share"],
                            always_competitive_share=b["always_competitive_share"], profit_gain_index=b["profit_gain_index"]))
    return out


def draw(rows, out_png, plt=None, y="level"):
    """y="competitive_share" draws the U16 variant (mean competitive share of firm-rounds, no theory curve, no band). One panel per thinking mode; theory dashed, one curve + band per arm, refusal rate in the legend and a note."""
    if plt is None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    modes = sorted({r["thinking"] for r in rows})
    arms = sorted({r["arm"] for r in rows if r["arm"] not in ("theory", "baseline")})
    fig, axes = plt.subplots(1, len(modes), sharey=True, figsize=(5.5 * len(modes), 4.6), squeeze=False)
    for ax, th in zip(axes[0], modes):
        mine = [r for r in rows if r["thinking"] == th and r["refusals"] == "with"]
        theory = sorted((r for r in mine if r["arm"] == "theory"), key=lambda r: r["x"]) if y == "level" else []
        if theory:
            ax.plot([r["x"] for r in theory], [r["level"] for r in theory], color="#555555", linestyle="--", linewidth=2, label="theory")
        base = sorted((r for r in mine if r["arm"] == "baseline" and r[y] != ""), key=lambda r: r["x"])
        if base:
            ax.plot([r["x"] for r in base], [r[y] for r in base], color="#888888", linestyle=":", linewidth=2, marker="x", label="undercutter baseline")
        notes = []
        for i, arm in enumerate(arms):
            pts = sorted((r for r in mine if r["arm"] == arm and r[y] != ""), key=lambda r: r["x"])
            if not pts:
                continue
            color, marker, ls = STYLES[i % len(STYLES)]
            rate, share = pts[0]["refusal_rate"], pts[0]["imputed_round_share"]
            tag = "refusals %s, imputed rounds %s" % (pct(rate), pct(share))
            xs = [r["x"] for r in pts]
            ax.plot(xs, [r[y] for r in pts], color=color, marker=marker, linestyle=ls, linewidth=2, markersize=8,
                    label="%s (%s)" % (arm, tag))
            ok = [r["level_lo"] != "" and r["level_hi"] != "" for r in pts]   # no band where the interval is not estimable
            if any(ok) and y == "level":
                ax.fill_between(xs, [r["level_lo"] if k else r["level"] for r, k in zip(pts, ok)],
                                [r["level_hi"] if k else r["level"] for r, k in zip(pts, ok)], where=ok, color=color, alpha=0.15, linewidth=0)
            notes.append("%s %s / %s" % (arm, pct(rate), pct(share)))
        ax.set_title("thinking %s" % th)
        ax.set_xlabel("expected penalty")
        ax.set_ylabel("collusion level (0 = competitive, 1 = collusive)" if y == "level" else "share of firm-rounds competitive (undercut the best rival, or at the floor)")
        ax.set_ylim(-0.05, 1.05)
        ax.legend(loc="best", fontsize=8)
        ax.text(0.02, 0.02, "Refusal rate (talk+quote+question calls) / imputed-round share (rounds with a truncated or unparseable "
                "call, played as imputed); overall: all rounds, all penalty points: " + "; ".join(notes), transform=ax.transAxes,
                fontsize=8, va="bottom", wrap=True)
    fig.suptitle("Collusion level against expected penalty (refusal rounds included, played at the competitive price; imputed rounds included;\nbands: bootstrap by game, stratified by wording, or across wordings where a wording has one game)")
    fig.savefig(str(out_png), dpi=150, bbox_inches="tight")
    return fig


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tables_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--competitive", type=float, help="override; default trials.csv competitive_price")
    ap.add_argument("--collusive", type=float, help="override; default trials.csv collusive_price")
    ap.add_argument("--theory", required=True)
    ap.add_argument("--window-start", type=int, default=1)
    ap.add_argument("--window-end", type=int, default=20)
    ap.add_argument("--basis", choices=am.BASES, default="window")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--baseline", metavar="DIR", help="tables dir written by baseline_bot.py: add the undercutter baseline rows and columns")
    ap.add_argument("--arms", default=am.HEADLINE_ARMS, metavar="REGEX",
                    help="arms drawn and paired (default %(default)s: the tacit, private chat and monitored chat arms)")
    a = ap.parse_args(argv)
    tables = am.load_tables(a.tables_dir)
    try:
        competitive, collusive = am.resolve_prices(tables, a.competitive, a.collusive)
    except ValueError as e:
        ap.error(str(e))
    try:
        rows = headline_rows(tables, competitive, collusive, read_theory(a.theory), a.window_start,
                             a.window_end, a.basis, a.boot, a.seed, a.arms)
    except (ValueError, re.error) as e:
        ap.error(str(e))   # exit 2 (an empty window basis included: never a matplotlib crash)
    cols = COLS
    if a.baseline:
        try:
            rows = add_baseline(rows, a.baseline, read_theory(a.theory), a.window_start, a.window_end, a.basis, a.arms)
        except (OSError, ValueError, KeyError) as e:
            ap.error("--baseline %s: %s" % (a.baseline, e))
        cols = COLS + BASELINE_COLS
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    am.write_csv(out / "headline_data.csv", rows, cols)
    am.warn_ci_methods([r for r in rows if r["arm"] not in ("theory", "baseline")], "headline cells")
    print(out / "headline_data.csv")
    if a.no_png:
        return 0
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("error: matplotlib is not installed; headline_data.csv was written, headline.png was not", file=sys.stderr)
        return 3
    draw(rows, out / "headline.png")
    draw(rows, out / "headline_competitive.png", y="competitive_share")   # U16 variant, blank without competitive_round
    print(out / "headline.png")
    print(out / "headline_competitive.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
