"""Figures for the penalty-gradients report (reads the CSVs written by pg_analysis.py).

  fig_penalty_curves.png      price index and profit gain index by penalty point, per model and mode
  fig_forest_<table>.png      a CI forest chart under every table of deltas: centroid + 95% CI per
                              contrast and metric, one shared x-scale for the four 0-1 metrics, a zero line
Run from this folder: python pg_figures.py
"""
import os
import sys
import re
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
import collusion_colors as cc  # noqa: E402

METRICS = [("market_price_mean", "Average absolute\nspread (quote units)"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share\n(U16)"),
           ("matching_share", "Matching share")]
THETA = {1: 0.7029, 3: 0.5459, 4: 0.3249, 5: 0.0}
PGI = {1: 0.9117, 3: 0.7938, 4: 0.5442, 5: 0.0}
RED, GREEN, GREY = "#c0392b", "#1e8449", "#555555"
plt.rcParams.update({"font.size": 10})


def colour(m, d, lo, hi, holm=None):
    """Shared ci_forest convention: red = collusion direction, green = competition direction."""
    if d == 0:
        return GREY
    dm = cc.direction("abs_spread" if m == "market_price_mean" else m)
    more_collusive = d > 0 if dm == "collusion" else d < 0
    return RED if more_collusive else GREEN


def forest(df, labels, fname, title, theory=True, metrics=METRICS, xlab_idx="difference (index units, 0-1 scale)", neutral=False):
    n = len(df)
    wrapped = ["\n".join(textwrap.wrap(t, 58)[:5]) for t in labels]
    h = max(3.0, 0.78 * n + 1.8)
    fig, axes = plt.subplots(1, len(metrics), figsize=(5.5 + 2.6 * len(metrics), h), sharey=True,
                             constrained_layout=True)
    idx_cols = [m for m, _ in metrics if m != "market_price_mean"]
    lo_all = min(df[f"{m}_lo"].min() for m in idx_cols)
    hi_all = max(df[f"{m}_hi"].max() for m in idx_cols)
    for m in idx_cols:
        if theory and f"{m}_theory" in df:
            lo_all = min(lo_all, df[f"{m}_theory"].min(skipna=True) if df[f"{m}_theory"].notna().any() else lo_all)
            hi_all = max(hi_all, df[f"{m}_theory"].max(skipna=True) if df[f"{m}_theory"].notna().any() else hi_all)
    pad = 0.05 * (hi_all - lo_all)
    y = np.arange(n)[::-1]
    for ax, (m, name) in zip(axes, metrics):
        for yi, (_, r) in zip(y, df.iterrows()):
            if pd.isna(r[f"{m}_d"]):
                continue
            c = "#2c7bb6" if neutral else colour(m, r[f"{m}_d"], r[f"{m}_lo"], r[f"{m}_hi"], r.get(f"{m}_holm"))
            ax.plot([r[f"{m}_lo"], r[f"{m}_hi"]], [yi, yi], color=c, lw=2.2)
            hollow = r[f"{m}_lo"] <= 0 <= r[f"{m}_hi"]
            ax.plot(r[f"{m}_d"], yi, "o", color=c, ms=7, mfc="white" if hollow else c, mew=1.8)
            holm_v = r.get(f"{m}_holm")
            if holm_v is not None and pd.notna(holm_v) and holm_v < 0.05 and not neutral:
                ax.plot(r[f"{m}_hi"], yi, marker="*", color="black", ms=7, lw=0)
            if theory and f"{m}_theory" in r and pd.notna(r[f"{m}_theory"]):
                ax.plot(r[f"{m}_theory"], yi, "D", mfc="none", mec="black", ms=7)
        ax.axvline(0, color="black", lw=1, ls="--")
        ax.set_title(name, fontsize=10)
        ax.grid(axis="x", alpha=0.3)
        if m == "market_price_mean":
            a = df[f"{m}_lo"].min(); b = df[f"{m}_hi"].max()
            if theory and f"{m}_theory" in df and df[f"{m}_theory"].notna().any():
                a = min(a, df[f"{m}_theory"].min()); b = max(b, df[f"{m}_theory"].max())
            a, b = min(a, 0), max(b, 0)
            p = 0.05 * (b - a)
            ax.set_xlim(a - p, b + p)
            ax.set_xlabel("own scale: difference\n(quote units, 1.00-5.00 scale)", fontsize=9)
        else:
            ax.set_xlim(min(lo_all, 0) - pad, max(hi_all, 0) + pad)
            ax.set_xlabel(xlab_idx.replace(" (", "\n("), fontsize=9)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(wrapped, fontsize=9)
    from matplotlib.lines import Line2D
    hs = ([Line2D([], [], color="#2c7bb6", marker="o", lw=2, label="estimate and 95% CI (neutral colour: a coefficient, no collusion direction)")]
          if neutral else
          [Line2D([], [], color=RED, marker="o", lw=2, label="move in the collusion direction"),
           Line2D([], [], color=GREEN, marker="o", lw=2, label="move in the competition direction"),
           Line2D([], [], color="black", marker="o", mfc="white", lw=0, label="hollow = 95% CI crosses zero"),
           Line2D([], [], color="black", marker="*", lw=0, label="* = Holm p < 0.05 (bold in the table)")])
    if theory:
        hs.append(Line2D([], [], color="black", marker="D", mfc="none", lw=0, label="pre-sprint model's prediction"))
    fig.legend(handles=hs, loc="outside lower center", ncol=len(hs), fontsize=9, frameon=False)
    fig.suptitle(title, fontsize=11)
    fig.savefig(os.path.join(HERE, fname), dpi=130)
    plt.close(fig)


SLUGS = ["headline-monitored", "headline-tacit", "headline-chat", "fx-ctl-joint", "fx-chat-p1", "fx-chat-p5", "fx-chat",
         "ctl-32b-joint", "ctl-32b-compete", "m-inc-joint", "m-inc-target"]


def short(slug):
    g = arm_labels.glossary()
    t = g[slug]["short_label"] if slug in g else ""
    return t.split(";")[0].split(" (")[0]


def describe(text):
    def rep(mo):
        sl, anch = mo.group(1), mo.group(2)
        return f"{sl} [{short(sl)}{', anchored table' if anch else ''}]"
    pat = r"(" + "|".join(re.escape(x) for x in SLUGS) + r")(@anchored)?(?![\w-])"
    return re.sub(pat, rep, text)


def row_label(r):
    return f"{r['model']} {r['mode']}: " + describe(r["contrast"])


def curves():
    c = pd.read_csv(os.path.join(HERE, "cell_means.csv"))
    G = pd.read_csv(os.path.join(HERE, "games_used.csv"))
    panels = [("Qwen3-32B", "t0"), ("Qwen3-32B", "t1"), ("gpt-oss-20b", "t1")]
    series = [("headline-tacit", "#7d3c98", "s", ["headline-tacit"]),
              ("headline-chat", "#1f77b4", "o", ["headline-chat"]),
              ("headline-monitored", "#e67e22", "^", ["headline-monitored"]),
              ("fx-chat", "#16a085", "v", ["fx-chat-p1", "fx-chat-p5"])]
    objs = [("ctl-32b-joint", "#c0392b", "*"), ("m-inc-joint", "#e74c3c", "P"), ("m-inc-target", "#8e44ad", "X"),
            ("fx-ctl-joint", "#27ae60", "*")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.6), sharex=True, sharey="row", constrained_layout=True)
    for row, (m, th, yl) in enumerate([("price_index", THETA, "Price index\n(0 = competitive 1.00, 1 = monopoly 3.00)"),
                                       ("profit_gain_index", PGI, "Profit gain index\n(0 = competitive, 1 = monopoly profit)")]):
        for col, (model, mode) in enumerate(panels):
            ax = axes[row, col]
            ax.plot(list(th), list(th.values()), "k--", lw=1.5, label="pre-sprint model: sustainable level θ*")
            for name, colr, mk, arms in series:
                d = G[(G.model == model) & (G["mode"] == mode) & G.arm.isin(arms) & (G.payoff_examples != "anchored")]
                if d.empty:
                    continue
                g = d.groupby("penalty_point")[m]
                mean = g.mean(); se = g.std() / np.sqrt(g.count())
                ax.errorbar(mean.index, mean.values, yerr=1.96 * se.values, color=colr, marker=mk, ms=7, capsize=3,
                            lw=1.8, label=arm_labels.label(name.split(" ")[0]))
                if model.startswith("Qwen") and name in ("headline-tacit", "headline-chat"):
                    da = G[(G.model == model) & (G["mode"] == mode) & (G.arm == name) & (G.payoff_examples == "anchored")]
                    ga = da.groupby("penalty_point")[m].mean()
                    ax.plot(ga.index, ga.values, color=colr, marker=mk, ms=5, lw=1.2, ls=":", mfc="white",
                            label=arm_labels.label(name) + " [anchored table, prints 2.09]")
            for k, (arm, colr, mk) in enumerate(objs):
                d = G[(G.model == model) & (G["mode"] == mode) & (G.arm == arm) & (G.payoff_examples != "anchored")]
                if d.empty:
                    continue
                xm = 3 + 0.12 * (k - 1.5)
                v = d[m]
                ax.errorbar([xm], [v.mean()], yerr=[1.96 * v.std() / np.sqrt(len(v))], color=colr, marker=mk, ms=11,
                            capsize=3, lw=0, elinewidth=1.5, label=arm_labels.label(arm) + " (p3 only)")
            ax.set_ylim(-0.02, 1.02)
            ax.set_xticks([1, 3, 4, 5])
            ax.set_xticklabels(["p1\nfine 100\nθ* 0.70", "p3\nfine 500\nθ* 0.55", "p4\nfine 1000\nθ* 0.32",
                                "p5\nfine 2000\nθ* 0.00"], fontsize=9)
            ax.grid(alpha=0.3)
            if row == 0:
                ax.set_title(f"{model}, {'thinking on' if mode == 't1' else 'thinking off'} ({mode})"
                             + (" - no p4 run" if model.startswith("gpt") else ""), fontsize=10)
            if col == 0:
                ax.set_ylabel(yl, fontsize=9)
    h, l = [], []
    for ax in axes.flat:
        for hh, ll in zip(*ax.get_legend_handles_labels()):
            if ll not in l:
                h.append(hh); l.append(ll)
    axes[1, 1].set_xlabel("Penalty point (regulator's fine per firm; θ* = the pre-sprint model's sustainable price index)", fontsize=10)
    fig.legend(h, l, loc="outside lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Penalty gradients: cell means (95% CI = 1.96 x SE over 20 games) by penalty point, model and thinking mode;\n"
                 "neutral, anchored (dotted) and formula payoff blocks, two firms, 20 (wording, seed) games per cell", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_penalty_curves.png"), dpi=120)
    plt.close(fig)


def main():
    R = pd.read_csv(os.path.join(HERE, "contrasts.csv"))
    curves()
    S = R[R.family == "S: p5 - p1 slopes"]
    forest(S, [row_label(r) for _, r in S.iterrows()], "fig_forest_slopes.png",
           "Penalty slope p5 - p1 (heavy minus light fine), paired over (wording, seed); 95% bootstrap CI; n = 19-20 pairs per row")
    St = R[R.family == "S-steps: adjacent-step slopes"]
    forest(St, [row_label(r) for _, r in St.iterrows()], "fig_forest_steps.png",
           "Penalty slope by adjacent step (p1->p3, p3->p4, p4->p5; gpt-oss p1->p3, p3->p5); 95% bootstrap CI; 20 pairs per row")
    I = R[R.family == "I: slope interactions"]
    forest(I, [row_label(r) for _, r in I.iterrows()], "fig_forest_interactions.png",
           "Slope interactions: difference between two penalty slopes, within pair; 95% bootstrap CI; n = 19-20 pairs per row",
           theory=False, xlab_idx="difference of slopes (index units)")
    O = R[R.family.str.startswith("O")].sort_values(["model", "mode"], kind="stable")
    forest(O, [row_label(r) for _, r in O.iterrows()], "fig_forest_objective.png",
           "Objective arms (run at p3 only) against the default arm; 95% bootstrap CI; n = 19-20 pairs per row", theory=False)
    C = R[R.family.str.startswith("C")]
    forest(C, [row_label(r) for _, r in C.iterrows()], "fig_forest_compose.png",
           "Does the joint-profit instruction add the same amount with and without example prices? (difference in differences)",
           theory=False, xlab_idx="difference of differences (index units)")
    H = pd.read_csv(os.path.join(HERE, "heed_coefficients.csv"))
    hb = pd.DataFrame({
        "price_index_d": H.beta_price_index, "price_index_lo": H.beta_price_index_lo, "price_index_hi": H.beta_price_index_hi,
        "profit_gain_index_d": H.beta_profit_gain_index, "profit_gain_index_lo": H.beta_profit_gain_index_lo,
        "profit_gain_index_hi": H.beta_profit_gain_index_hi,
        "matching_share_d": H.prop, "matching_share_lo": H.prop_lo, "matching_share_hi": H.prop_hi,
        "competitive_share_d": H.heed_late_minus_early, "competitive_share_lo": H.heed_late_minus_early_lo,
        "competitive_share_hi": H.heed_late_minus_early_hi})
    hb["price_index_theory"] = 1.0
    hb["profit_gain_index_theory"] = 0.9117 / 0.7029
    hb["matching_share_theory"] = 1.0
    hb["competitive_share_theory"] = np.where(H.heed_late_minus_early.notna(), 0.0, np.nan)
    labs = [f"{r.model} {r['mode']}: " + describe(r.chain) + f" ({r.payoff}, {r.communication}), {r.points}"
            + ("" if pd.notna(r.heed_late_minus_early) else " [two points: no step test]") for _, r in H.iterrows()]
    forest(hb, labs, "fig_forest_heed.png",
           "Heed coefficients: within-pair slope of each metric on θ* (theory = 1 for the price index), the share of the p1 price removed by p5, and the per-unit step test",
           metrics=[("price_index", "β: price index on θ*"), ("profit_gain_index", "β: profit gain index on θ*"),
                    ("matching_share", "proportional response\n1 - PI(p5) / PI(p1)"),
                    ("competitive_share", "per-unit response:\nlast step - first step")],
           xlab_idx="coefficient (theory 1 = full heed)", neutral=True)
    print("figures written")


if __name__ == "__main__":
    main()
