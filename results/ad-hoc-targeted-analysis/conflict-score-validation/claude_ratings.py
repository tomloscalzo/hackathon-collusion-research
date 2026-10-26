#!/usr/bin/env python3
"""How Claude's outcome-blind prompt ratings (claude_conflict, claude_temptation) relate to measured behaviour and to the models'
own self-reported scores. Reads the Step 1 run.csv (built with --prompt-ratings). Standard library + numpy + pandas + matplotlib.

Usage: python -I -X utf8 claude_ratings.py --run-csv RUN.csv --out DIR [--ethics-games game_level.csv --ratings prompt_ratings.csv]

Metrics (each analysed separately; one game = one row of run.csv, status done):
  market_price_mean  average absolute spread: mean best quote over rounds, raw half-spread units 1.00 to 5.00
  price_index        (price - 1)/2 averaged over rounds, clamped 0..1
  profit_gain_index  (profit - competitive) / (monopoly - competitive)
  competitive_share  share of firm-rounds that are competitive under U16
  matching_share     share of firm-rounds in which the firm matched the lowest rival quote of the previous round
Outputs: claude_game_spearman.csv, claude_cell_spearman.csv, claude_cells.csv, claude_vs_self_report.csv, claude_ethics_arm.csv,
fig_claude_conflict_vs_metrics.png, fig_claude_temptation_vs_metrics.png, fig_claude_vs_self.png.
Confidence intervals: 95% percentile bootstrap resampling whole prompt texts (the rating is constant within a text, so games of one
text are not independent); 2000 resamples, seed 20261025; ranks fixed on the full sample."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
import textwrap
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "analysis_style"))
import arm_labels  # shared slug glossary: legends and point labels read "slug: short label"

L = arm_labels.label
MSLUG = {"market_price_mean": "abs_spread"}   # run.csv column -> glossary slug

METRICS = [("market_price_mean", "Average spread (half-spread units)"), ("price_index", "Price index (0-1)"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share (U16)"),
           ("matching_share", "Matching share")]
RATINGS = [("claude_conflict", "Claude-rated conflict"), ("claude_temptation", "Claude-rated temptation")]
NB, SEED = 2000, 20261025


def rank(a):
    return pd.Series(a).rank(method="average").to_numpy()


def spear(x, y):
    if len(x) < 4:
        return np.nan
    rx, ry = rank(x), rank(y)
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def cluster_boot(df, xc, yc, cl, rng):
    """Spearman with a percentile CI from resampling whole clusters. The ranks are computed once on the full sample and the
    Pearson correlation of those ranks is recomputed on each resample (fast; the usual approximation to re-ranking)."""
    d = df[[xc, yc, cl]].dropna()
    n = len(d)
    rho = spear(d[xc].to_numpy(), d[yc].to_numpy())
    if n < 8 or np.isnan(rho):
        return rho, np.nan, np.nan, n
    rx, ry = rank(d[xc].to_numpy()), rank(d[yc].to_numpy())
    code = pd.factorize(d[cl])[0]
    k = code.max() + 1
    if k < 4:
        return rho, np.nan, np.nan, n
    S = np.zeros((k, 6))
    for col, v in enumerate((np.ones(n), rx, ry, rx * rx, ry * ry, rx * ry)):
        S[:, col] = np.bincount(code, weights=v, minlength=k)
    idx = rng.integers(0, k, (NB, k))
    T = S[idx].sum(axis=1)
    num = T[:, 5] / T[:, 0] - (T[:, 1] / T[:, 0]) * (T[:, 2] / T[:, 0])
    den = np.sqrt((T[:, 3] / T[:, 0] - (T[:, 1] / T[:, 0]) ** 2) * (T[:, 4] / T[:, 0] - (T[:, 2] / T[:, 0]) ** 2))
    with np.errstate(all="ignore"):
        vals = num / den
    vals = vals[np.isfinite(vals)]
    return rho, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), n


def load(path):
    df = pd.read_csv(path, low_memory=False)
    df = df[(df.status == "done") & df.claude_conflict.notna()].copy()
    df["cell"] = df.run + "|" + df.arm + "|p" + df.penalty_point.astype(str) + "|" + df.thinking
    return df


def game_level(df, rng):
    rows = []
    subsets = [("all games", lambda d: d), ("chat arms only", lambda d: d[d.communication_group == "chat"]),
               ("tacit (no chat) only", lambda d: d[d.communication_group == "tacit"])]
    for run in ("anchored", "neutral", "both"):
        for th in ("off", "on", "both"):
            d0 = df
            if run != "both":
                d0 = d0[d0.run == run]
            if th != "both":
                d0 = d0[d0.thinking == th]
            for sname, f in subsets:
                d = f(d0)
                for rc, rl in RATINGS:
                    for mc, ml in METRICS:
                        rho, lo, hi, n = cluster_boot(d, rc, mc, "claude_rating_id", rng)
                        rows.append(dict(run=run, thinking=th, subset=sname, rating=rc, metric=mc, spearman=rho, ci_lo=lo, ci_hi=hi, n_games=n,
                                         n_texts=d.claude_rating_id.nunique()))
    return pd.DataFrame(rows)


def cell_table(df):
    mets = [m for m, _ in METRICS]
    g = df.groupby(["run", "thinking", "cell", "arm", "penalty_point", "communication"])[["claude_conflict", "claude_temptation"] + mets].mean().reset_index()
    g["n_games"] = df.groupby("cell").size().reindex(g.cell).to_numpy()
    return g


def cell_level(cells, rng):
    rows = []
    for run in ("anchored", "neutral", "both"):
        for th in ("off", "on", "both"):
            d = cells
            if run != "both":
                d = d[d.run == run]
            if th != "both":
                d = d[d.thinking == th]
            for rc, rl in RATINGS:
                for mc, ml in METRICS:
                    rho, lo, hi, n = cluster_boot(d.assign(cl=d.cell), rc, mc, "cl", rng)
                    rows.append(dict(run=run, thinking=th, rating=rc, metric=mc, spearman=rho, ci_lo=lo, ci_hi=hi, n_cells=n))
    return pd.DataFrame(rows)


def legend_handles(col):
    return [plt.Line2D([], [], marker="o", ls="", c=col["off"], label=L("t0")), plt.Line2D([], [], marker="o", ls="", c=col["on"], label=L("t1")),
            plt.Line2D([], [], marker="o", ls="", c="grey", label=L("anchored") + " (circle)"),
            plt.Line2D([], [], marker="s", ls="", c="grey", label=L("neutral") + " (square)")]


def scatter(cells, rc, rl, out, rho_given=None):
    """rho_given: {metric: Spearman} to print in the titles instead of recomputing (figures-only mode, from claude_cell_spearman.csv)."""
    fig, axes = plt.subplots(1, 5, figsize=(20, 4.4))
    col = {"off": "#1f77b4", "on": "#d95f02"}
    mk = {"anchored": "o", "neutral": "s"}
    rng = np.random.default_rng(1)
    for ax, (mc, ml) in zip(axes, METRICS):
        for (run, th), d in cells.groupby(["run", "thinking"]):
            sc = ax.scatter(d[rc] + rng.normal(0, 0.03, len(d)), d[mc], c=col[th], marker=mk[run], s=22, alpha=.7, edgecolors="none")
            assert np.array_equal(np.asarray(sc.get_offsets(), float)[:, 1], d[mc].to_numpy(float), equal_nan=True)   # plotted = table values
        x = cells[[rc, mc]].dropna()
        rho = spear(x[rc].to_numpy(), x[mc].to_numpy()) if rho_given is None else rho_given[mc]
        ax.set_title("%s: %s\nSpearman %.2f, %d cells" % (MSLUG.get(mc, mc), ml, rho, len(x)), fontsize=9)
        ax.set_xlabel(rl + " (1-5, cell mean)")
        ax.set_ylabel(ml)
        ax.grid(alpha=.2)
    fig.legend(handles=legend_handles(col), loc="lower center", ncol=4, fontsize=9)
    fig.suptitle("%s versus measured behaviour: one point per cell (run x arm x penalty point x thinking)" % rl, fontsize=11)
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(out, dpi=120)
    plt.close(fig)


SCORE_PAIRS = {"conflict_score": "claude_conflict", "temptation_score": "claude_temptation"}


def self_report(df, rng):
    s = df[df.score_name.isin(list(SCORE_PAIRS)) & df.score_mean.notna()].copy()
    s["claude_same_scale"] = np.where(s.score_name == "conflict_score", s.claude_conflict, s.claude_temptation)
    t = s.groupby(["arm", "score_name", "run", "thinking"]).agg(
        n_games=("row_id", "size"), self_score=("score_mean", "mean"), claude_conflict=("claude_conflict", "mean"), claude_temptation=("claude_temptation", "mean"),
        claude_same_scale=("claude_same_scale", "mean"), market_price_mean=("market_price_mean", "mean"), price_index=("price_index", "mean"),
        profit_gain_index=("profit_gain_index", "mean"), competitive_share=("competitive_share", "mean"), matching_share=("matching_share", "mean")).reset_index()
    rows = []
    for sn, rc in SCORE_PAIRS.items():
        d = s[s.score_name == sn]
        for th in ("off", "on", "both"):
            dd = d if th == "both" else d[d.thinking == th]
            for mc, ml in METRICS:
                a = cluster_boot(dd.assign(cl=dd.claude_rating_id), rc, mc, "cl", rng)
                b = cluster_boot(dd.assign(cl=dd.claude_rating_id), "score_mean", mc, "cl", rng)
                rows.append(dict(score=sn, thinking=th, metric=mc, claude_vs_metric=a[0], claude_lo=a[1], claude_hi=a[2], self_vs_metric=b[0], self_lo=b[1],
                                 self_hi=b[2], n_games=a[3]))
            r, lo, hi, n = cluster_boot(dd.assign(cl=dd.claude_rating_id), rc, "score_mean", "cl", rng)
            rows.append(dict(score=sn, thinking=th, metric="(self-report itself)", claude_vs_metric=r, claude_lo=lo, claude_hi=hi, self_vs_metric=np.nan,
                             self_lo=np.nan, self_hi=np.nan, n_games=n))
    return t, pd.DataFrame(rows)


def fig_self(t, out):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
    col = {"off": "#1f77b4", "on": "#d95f02"}
    mk = {"anchored": "o", "neutral": "s"}
    drawn = []
    for ax, sn, rl in zip(axes, ("conflict_score", "temptation_score"), ("conflict", "temptation")):
        d = t[t.score_name == sn].sort_values("self_score", ascending=False)
        lo, hi = d.claude_same_scale.min(), d.claude_same_scale.max(); pad = (hi - lo) * 0.12 + 0.005
        ax.set_xlim(lo - pad, hi + (hi - lo + 2 * pad) * 1.25)   # the right part of the panel holds the point labels
        ylo, yhi = d.self_score.min(), d.self_score.max(); yp = (yhi - ylo) * 0.08 + 0.0003
        ax.set_ylim(ylo - yp, yhi + yp)
        ys = np.linspace(0.95, 0.05, len(d)) if len(d) > 1 else [0.5]
        for (_, r), yt in zip(d.iterrows(), ys):
            sc = ax.scatter(r.claude_same_scale, r.self_score, c=col[r.thinking], marker=mk[r.run], s=40, zorder=3)
            drawn.append((sc, r.claude_same_scale, r.self_score))
            # point label (callout, stacked in the order of the points' heights): full arm slug with its short label,
            # plus the run and thinking slugs of this point
            txt = "%s\n(%s, %s)" % (L(r.arm), L(r.run).split(":")[0], L("t1" if r.thinking == "on" else "t0"))
            ax.annotate(txt, (r.claude_same_scale, r.self_score), xytext=(0.43, yt), textcoords="axes fraction", fontsize=7, va="center",
                        arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6, shrinkA=2, shrinkB=4))
        ax.set_xlabel(textwrap.fill("Claude-rated %s of the prompt (1-5, mean over the arm's prompts)" % rl, 50), fontsize=9)
        ax.set_ylabel(textwrap.fill("Models' self-reported %s score (%s; 1-5, mean over games)" % (rl, L(sn)), 50), fontsize=9)
        ax.set_title("Self-reported %s versus Claude-rated, per arm x run x thinking" % rl, fontsize=10)
        ax.grid(alpha=.2)
    fig.legend(handles=legend_handles(col), loc="lower center", ncol=4, fontsize=9)
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=3)
    for sc, x, y in drawn:   # check: plotted positions are the table values
        assert tuple(np.asarray(sc.get_offsets(), float)[0]) == (float(x), float(y))
    fig.savefig(out, dpi=120)
    plt.close(fig)


def ethics_arm(path, ratings_path):
    """d-conflict (neutral) vs d-conflict-ethics (wave A): Claude's rating of the prompt, the self-reported score, price index, competitive share."""
    g = pd.read_csv(path)
    pr = pd.read_csv(ratings_path, keep_default_na=False)
    pr = pr.assign(arm=pr.arms.str.split(";")).explode("arm")
    pr = pr[pr.arm.isin(["d-conflict", "d-conflict-ethics"]) & (pr.payoff_examples == "neutral")]
    pr["wording"] = pr.wording.astype(int)
    pr = pr.groupby(["arm", "wording"])[["conflict_mean", "temptation_mean"]].mean().reset_index()
    g = g.merge(pr, on=["arm", "wording"], how="left")
    t = g.groupby(["arm", "thinking"]).agg(n_games=("trial_id", "size"), claude_conflict=("conflict_mean", "mean"), claude_temptation=("temptation_mean", "mean"),
                                           self_conflict_score=("score", "mean"), price_index=("collusion_level", "mean"), competitive_share=("comp", "mean")).reset_index()
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ethics-games")
    ap.add_argument("--ratings")
    ap.add_argument("--figures-only", action="store_true", help="redraw the three figures from the committed CSVs in --out; writes no CSV")
    a = ap.parse_args()
    out = Path(a.out)
    if a.figures_only:
        cells = pd.read_csv(out / "claude_cells.csv")
        cs = pd.read_csv(out / "claude_cell_spearman.csv")
        cs = cs[(cs.run == "both") & (cs.thinking == "both")]
        for rc, rl in RATINGS:
            given = cs[cs.rating == rc].set_index("metric").spearman.to_dict()
            # titles print the committed rho (computed on unrounded cell means). Recomputing it from the 4-decimal claude_cells.csv
            # creates rank ties and shifts it by up to about 0.01, so it is only checked loosely here.
            for mc, _ in METRICS:
                x = cells[[rc, mc]].dropna()
                assert abs(spear(x[rc].to_numpy(), x[mc].to_numpy()) - given[mc]) < 0.02, (rc, mc)
            scatter(cells, rc, rl, out / ("fig_%s_vs_metrics.png" % rc), rho_given=given)
        fig_self(pd.read_csv(out / "claude_vs_self_report_arms.csv"), out / "fig_claude_vs_self.png")
        print("figures redrawn from the committed CSVs")
        return
    if not a.run_csv:
        ap.error("--run-csv is required unless --figures-only")
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    df = load(a.run_csv)
    print(len(df), "games with ratings;", df.claude_rating_id.nunique(), "texts")
    gl = game_level(df, rng)
    gl.round(4).to_csv(out / "claude_game_spearman.csv", index=False, lineterminator="\n")
    cells = cell_table(df)
    cells.round(4).to_csv(out / "claude_cells.csv", index=False, lineterminator="\n")
    cell_level(cells, rng).round(4).to_csv(out / "claude_cell_spearman.csv", index=False, lineterminator="\n")
    for rc, rl in RATINGS:
        scatter(cells, rc, rl, out / ("fig_%s_vs_metrics.png" % rc))
    t, sr = self_report(df, rng)
    t.round(4).to_csv(out / "claude_vs_self_report_arms.csv", index=False, lineterminator="\n")
    sr.round(4).to_csv(out / "claude_vs_self_report.csv", index=False, lineterminator="\n")
    fig_self(t, out / "fig_claude_vs_self.png")
    if a.ethics_games and a.ratings:
        ethics_arm(a.ethics_games, a.ratings).round(4).to_csv(out / "claude_ethics_arm.csv", index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
