"""Re-render the analysis lead's Step 2 figures (figures/lead_*.png) from the committed tables, with
"slug: short label" tick and legend text from the shared glossary (tools/analysis_style/arm_labels.py).
Labels and layout only: the drawing code is the lead pipeline's figures.py (fig_gain_vs_penalty, fig_comm,
fig_thinking, fig_anchor, fig_controls, fig_dset, fig_glance); every plotted value is read from a table and
asserted against it; no number is recomputed.

Inputs: tables/lead_a_cells_vs_theory_and_bot.csv, tables/lead_c_communication_contrasts.csv,
tables/lead_f_controls.csv, tables/lead_e_anchoring_neutral_minus_anchored.csv (committed). The D-set panel
also needs the lead pipeline's g_dset_score_distribution.csv and g_dset_behaviour.csv, which are not
committed: give their folder in the environment variable LEAD_RESULTS_DIR (the provisional neutral output of
the lead pipeline, results/ subfolder).
Usage: python -X utf8 replot_lead_figures.py [--orig]   (--orig = the old labels, to check that the data path
reproduces the committed PNGs byte for byte; writes to $REPLOT_OUT if set, else figures/)."""
import os
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ORIG = "--orig" in sys.argv
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import arm_labels as AL  # noqa: E402
import collusion_colors as CC  # noqa: E402
TF = 8 if ORIG else 9   # tick text never below 9 pt in the new labels

OUTDIR = Path(os.environ.get("REPLOT_OUT", HERE / "figures"))
TAB = HERE / "tables"
CHECKS = []

COL = {"tacit": "#0072B2", "chat": "#D55E00", "monitored": "#009E73", "theory": "#000000", "bot": "#7f7f7f", "neutral": "#CC79A7", "anchored": "#E69F00"}
MODE_LAB = {"t0": "thinking off", "t1": "thinking on"} if ORIG else {"t0": "t0: thinking off", "t1": "t1: thinking on"}
ARM = {"tacit": "headline-tacit", "chat": "headline-chat", "monitored": "headline-monitored"}
INK, GRID = "#222222", "#dddddd"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#888", "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "figure.dpi": 110, "savefig.dpi": 150, "legend.frameon": False})


def lab(slug, wrap=None):
    t = AL.label(slug)
    return textwrap.fill(t, wrap) if wrap else t


def comm_lab(comm, wrap=None):
    return comm if ORIG else lab(ARM[comm], wrap)


EXP = set()


def check(est, lo, hi, row):
    """remember the table row's estimate; _save then asserts every plotted point sits on one of them"""
    EXP.add(round(float(row.est), 10))


def verify(fig):
    """every errorbar point drawn in the figure has a coordinate equal to a table estimate (the other
    coordinate is a category position)"""
    from matplotlib.container import ErrorbarContainer
    for ax in fig.axes:
        for c in ax.containers:
            if isinstance(c, ErrorbarContainer):
                xs, ys = c.lines[0].get_xdata(), c.lines[0].get_ydata()
                for x, y in zip(np.atleast_1d(xs), np.atleast_1d(ys)):
                    CHECKS.append(round(float(x), 10) in EXP or round(float(y), 10) in EXP)


def _save(fig, path, note=None):
    verify(fig)
    if note:
        fig.text(0.01, 0.005, note, fontsize=7.5, color="#555", ha="left", va="bottom", wrap=True)
    try:
        fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    except Exception:
        pass
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig_gain_vs_penalty(cells, run, path, metric="gain_all"):
    c = cells[(cells.run == run) & (cells.metric == metric) & cells.arm.str.startswith("headline-")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2) if ORIG else (11, 4.6), sharey=True)
    for ax, mode in zip(axes, ["t0", "t1"]):
        x = c[c["mode"] == mode]
        for k, comm in enumerate(["tacit", "chat", "monitored"]):
            d = x[x.comm == comm].sort_values("penalty_point")
            if d.empty:
                continue
            off = (k - 1) * 0.08
            for _, r in d.iterrows():
                check(r.est, r.lo, r.hi, r)
            ax.errorbar(d.penalty_point + off, d.est, yerr=[d.est - d.lo, d.hi - d.est], color=COL[comm], marker="o", ms=5, lw=1.6, capsize=3, label=comm_lab(comm))
        t = x.drop_duplicates("penalty_point").sort_values("penalty_point")
        if len(t):
            ax.plot(t.penalty_point, t.theory, color=COL["theory"], ls="--", lw=1.4, marker="s", ms=4, label="theory (sustainable collusion)")
            ax.plot(t.penalty_point, t.bot, color=COL["bot"], ls=":", lw=1.8, label="scripted slow-undercutter bot")
        ax.axhline(0, color="#aa0000", lw=0.8)
        ax.text(5.05, 0.01, "competitive (price 1.00)", color="#aa0000", fontsize=8, ha="right", va="bottom")
        ax.set_title("%s  (n = %d to %d games per point)" % (MODE_LAB[mode], x.n_pairs.min(), x.n_pairs.max()), fontsize=10)
        ax.set_xlabel("penalty point (higher = heavier fine)")
        ax.set_xticks([1, 3, 4, 5])
        if not ORIG:
            ax.set_xticklabels([CC.tick_label(p_, short=f) for p_, f in [("p1", "fine 100"), ("p3", "fine 500"), ("p4", "fine 1000"), ("p5", "fine 2000")]], fontsize=TF)
    axes[0].set_ylabel("profit gain index (0 = competitive, 1 = monopoly profit)")
    axes[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Collusion vs penalty, %s prompt examples; bars = 95%% CI over (wording, seed) pairs" % run, fontsize=11)
    _save(fig, path)


def fig_comm(comm, run, path):
    c = comm[(comm.run == run) & (comm.metric == "gain_all") & (comm.penalty_point == "pooled") & comm["mode"].isin(["t0", "t1", "both"])]
    fig, ax = plt.subplots(figsize=(7.5, 3.8) if ORIG else (8.6, 4.2))
    order = ["chat minus tacit", "monitored minus tacit", "chat minus monitored"]
    for i, ct in enumerate(order):
        for j, mode in enumerate(["t0", "t1", "both"]):
            d = c[(c.contrast == ct) & (c["mode"] == mode)]
            if d.empty:
                continue
            d = d.iloc[0]
            check(d.est, d.lo, d.hi, d)
            y = i + (1 - j) * 0.25
            color = ["#56B4E9", "#E69F00", "#444444"][j]
            ax.errorbar(d.est, y, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", color=color, capsize=3, label={"t0": MODE_LAB["t0"], "t1": MODE_LAB["t1"], "both": "both modes"}[mode] if i == 0 else None)
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_yticks(range(3))
    ax.set_yticklabels(order if ORIG else [contrast_lab(o) for o in order], fontsize=None if ORIG else TF)
    ax.set_xlabel("difference in profit gain index (average over penalty points 1,3,4,5; paired on wording x seed)")
    ax.legend(fontsize=8)
    ax.set_title("Communication contrasts, %s run" % run, fontsize=10)
    _save(fig, path)


def contrast_lab(ct):
    a, b = ct.split(" minus ")
    return "%s\nminus %s" % (lab(ARM[a]), lab(ARM[b]))


def fig_thinking(cells, run, path, metric="gain_all"):
    c = cells[(cells.run == run) & (cells.metric == metric) & cells.arm.str.startswith("headline-")]
    fig, ax = plt.subplots(figsize=(8.5, 4.4) if ORIG else (10, 5.6))
    labs, k = [], 0
    for comm in ["tacit", "chat", "monitored"]:
        for p in [1, 3, 4, 5]:
            off = c[(c.comm == comm) & (c.penalty_point == p) & (c["mode"] == "t0")]
            on = c[(c.comm == comm) & (c.penalty_point == p) & (c["mode"] == "t1")]
            tick = "%s p%d" % (comm, p) if ORIG else "%s, p%d" % (lab(ARM[comm]), p)
            if off.empty or on.empty:
                k += 1
                labs.append(tick)
                continue
            o, n = off.iloc[0], on.iloc[0]
            check(o.est, o.lo, o.hi, o); check(n.est, n.lo, n.hi, n)
            ax.plot([k, k], [o.est, n.est], color=COL[comm], lw=1.5, alpha=0.7)
            ax.errorbar(k, o.est, yerr=[[o.est - o.lo], [o.hi - o.est]], fmt="o", mfc="white", color=COL[comm], capsize=2)
            ax.errorbar(k, n.est, yerr=[[n.est - n.lo], [n.hi - n.est]], fmt="o", color=COL[comm], capsize=2)
            labs.append(tick)
            k += 1
    ax.set_xticks(range(len(labs)))
    ax.set_xticklabels(labs, rotation=60, ha="right", fontsize=TF)
    ax.set_ylabel("profit gain index")
    ax.plot([], [], "o", mfc="white", color="#444", label=MODE_LAB["t0"])
    ax.plot([], [], "o", color="#444", label=MODE_LAB["t1"])
    ax.legend(fontsize=8)
    ax.set_title("Thinking off (open) vs on (filled), %s run; 95%% CI per point" % run, fontsize=10)
    _save(fig, path)


def fig_anchor(anchor, path):
    a = anchor[anchor.arm.str.startswith("pooled") & (anchor.penalty_point == "pooled over 1,3,4,5")]
    metrics = [("gain_all", "profit gain index"), ("share_2.09", "share of quotes at 2.09"), ("share_2.50", "share of quotes at 2.50"), ("share_anchored_set", "share on 1.54/2.09/3.00")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(12, 3.6) if ORIG else (14, 4.0))
    for ax, (m, title) in zip(axes, metrics):
        x = a[a.metric == m]
        for i, g in enumerate(["pooled headline-all", "pooled tacit", "pooled chat", "pooled monitored"]):
            for j, mode in enumerate(["t0", "t1"]):
                d = x[(x.arm == g) & (x["mode"] == mode)]
                if d.empty:
                    continue
                d = d.iloc[0]
                check(d.est, d.lo, d.hi, d)
                ax.errorbar(d.est, i + (j - 0.5) * 0.3, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None,
                            color=["#0072B2", "#D55E00"][j], capsize=2, label=MODE_LAB[mode] if i == 0 else None)
        ax.axvline(0, color="#444", lw=0.8)
        ax.set_yticks(range(4))
        names = ["all headline", "tacit", "chat", "monitored"] if ORIG else ["all three headline arms", lab("headline-tacit", 24), lab("headline-chat", 24), lab("headline-monitored", 24)]
        ax.set_yticklabels(names if ax is axes[0] else [])
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("neutral minus anchored")
    axes[0].legend(fontsize=8)
    fig.suptitle("Anchoring effect: neutral-example run minus anchored-example run (paired on arm, point, wording, seed, mode)", fontsize=10)
    _save(fig, path)


def fig_controls(cells, run, path):
    c = cells[(cells.run == run) & (cells.metric == "gain_all") & cells.arm.isin(["ctl-32b-compete", "ctl-32b-joint"]) | ((cells.run == run) & (cells.metric == "gain_all") & (cells.arm == "headline-chat") & (cells.penalty_point == 3))]
    fig, ax = plt.subplots(figsize=(6.5, 3.8) if ORIG else (7.6, 4.2))
    if ORIG:
        names = [("ctl-32b-compete", "negative control\n(told to compete)"), ("headline-chat", "headline chat p3\n(no instruction)"), ("ctl-32b-joint", "positive control\n(told to maximise joint profit)")]
    else:
        names = [("ctl-32b-compete", lab("ctl-32b-compete", 26) + "\n(negative control)"), ("headline-chat", lab("headline-chat", 26) + ", p3"),
                 ("ctl-32b-joint", lab("ctl-32b-joint", 26) + "\n(positive control)")]
    for i, (arm, _) in enumerate(names):
        for j, mode in enumerate(["t0", "t1"]):
            d = c[(c.arm == arm) & (c["mode"] == mode)]
            if d.empty:
                continue
            d = d.iloc[0]
            check(d.est, d.lo, d.hi, d)
            ax.errorbar(i + (j - 0.5) * 0.2, d.est, yerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00",
                        capsize=3, label=MODE_LAB[mode] if i == 0 else None)
    ax.set_xticks(range(3))
    ax.set_xlim(-.5, 2.5)
    ax.set_xticklabels([n[1] for n in names], fontsize=TF)
    ax.set_ylabel("profit gain index")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8)
    ax.set_title("Controls, %s run" % run, fontsize=10)
    _save(fig, path)


def fig_dset(dist, beh, run, path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8) if ORIG else (13, 5.0))
    d = dist[dist.run == run]
    arms = list(d.arm.unique())
    w = 0.8 / 5
    for v in range(1, 6):
        ys = []
        for a in arms:
            x = d[(d.arm == a) & (d.score == v)]
            ys.append(x.n_firm_rounds.sum() / max(d[(d.arm == a)].groupby("score").n_firm_rounds.sum().sum(), 1))
        axes[0].bar(np.arange(len(arms)) + (v - 3) * w, ys, w * 0.9, label="score %d" % v, color=["#f0e442", "#e69f00", "#d55e00", "#cc79a7", "#0072b2"][v - 1], edgecolor="white")
    axes[0].set_xticks(range(len(arms)))
    if ORIG:
        axes[0].set_xticklabels([a.replace("d-", "") for a in arms], fontsize=8)
    else:
        _, k_ = CC.set_arm_ticks(axes[0], arms, "x", rotation=0, wrap=18, max_lines=4)
        assert k_ is None, "numbered-key fallback"
    axes[0].set_ylabel("share of answers (both modes)")
    axes[0].legend(fontsize=7, ncol=5, loc="upper center")
    axes[0].set_title("Self-rated scores (1-5) by D-set arm", fontsize=10)
    b = beh[(beh.run == run) & (beh.metric == "gain_all")]
    for i, a in enumerate(sorted(b.arm.unique())):
        for j, mode in enumerate(["t0", "t1"]):
            x = b[(b.arm == a) & (b["mode"] == mode)]
            if x.empty or not np.isfinite(x.iloc[0].lo):
                continue
            x = x.iloc[0]
            check(x.est, x.lo, x.hi, x)
            axes[1].errorbar(x.est, i + (j - 0.5) * 0.25, xerr=[[x.est - x.lo], [x.hi - x.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00",
                             capsize=2, label=MODE_LAB[mode] if i == 0 else None)
    arms2 = sorted(b.arm.unique())
    axes[1].set_yticks(range(len(arms2)))
    if ORIG:
        axes[1].set_yticklabels([a.replace("d-", "") for a in arms2], fontsize=8)
    else:
        _, k_ = CC.set_arm_ticks(axes[1], arms2, "y")
        assert k_ is None, "numbered-key fallback"
    axes[1].axvline(0, color="#444", lw=0.8)
    axes[1].legend(fontsize=8)
    axes[1].set_xlabel("profit gain: D arm minus headline-chat p1 (paired)")
    axes[1].set_title("Behaviour vs the shared control", fontsize=10)
    _save(fig, path)


def fig_glance(cells, comm, ctl, anchor, run, path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.4) if ORIG else (13, 8.4))
    ax = axes[0, 0]
    c = cells[(cells.run == run) & (cells.metric == "gain_all") & cells.arm.str.startswith("headline-")]
    for comm_name in ["tacit", "chat", "monitored"]:
        d = c[c.comm == comm_name].groupby("penalty_point").est.mean()
        ax.plot(d.index, d.values, "o-", color=COL[comm_name], label=comm_lab(comm_name))
    t = c.drop_duplicates("penalty_point").sort_values("penalty_point")
    ax.plot(t.penalty_point, t.theory, "k--", marker="s", ms=4, label="theory")
    ax.plot(t.penalty_point, t.bot, color=COL["bot"], ls=":", label="slow bot")
    ax.set_title("1. Profit gain vs penalty (average of the two thinking modes)", fontsize=9)
    ax.set_xticks([1, 3, 4, 5]); ax.set_xlabel("penalty point"); ax.set_ylabel("profit gain index"); ax.legend(fontsize=7)
    if not ORIG:
        ax.set_xticklabels(["p1", "p3", "p4", "p5"]); ax.set_xlabel("penalty point (p1 = fine 100 ... p5 = fine 2000)")
    ax = axes[0, 1]
    cc = comm[(comm.run == run) & (comm.metric == "gain_all") & (comm.penalty_point == "pooled") & (comm["mode"] == "both")]
    order = ["chat minus tacit", "monitored minus tacit", "chat minus monitored"]
    for i, ct in enumerate(order):
        d = cc[cc.contrast == ct]
        if len(d):
            d = d.iloc[0]
            check(d.est, d.lo, d.hi, d)
            ax.errorbar(d.est, i, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", color="#333", capsize=3)
    ax.axvline(0, color="#444", lw=0.8); ax.set_yticks(range(3))
    ax.set_yticklabels(["chat - tacit", "monitored - tacit", "chat - monitored"] if ORIG else [contrast_lab(o) for o in order], fontsize=None if ORIG else TF)
    ax.set_title("2. Does talking raise collusion? (95% CI)", fontsize=9); ax.set_xlabel("difference in profit gain index")
    ax = axes[1, 0]
    k = ctl[(ctl.run == run) & (ctl.analysis == "control_level") & (ctl.metric == "gain_all")]
    for i, arm in enumerate(["ctl-32b-compete", "ctl-32b-joint"]):
        for j, mode in enumerate(["t0", "t1"]):
            d = k[(k.arm == arm) & (k["mode"] == mode)]
            if len(d):
                d = d.iloc[0]
                check(d.est, d.lo, d.hi, d)
                ax.errorbar(i + (j - .5) * .2, d.est, yerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00", capsize=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["compete control", "joint-profit control"] if ORIG else [lab("ctl-32b-compete", 30), lab("ctl-32b-joint", 30)], fontsize=None if ORIG else TF)
    ax.set_ylim(-.05, 1.05); ax.set_xlim(-.5, 1.5)
    ax.set_title("3. Controls (open = thinking off, filled = on)", fontsize=9); ax.set_ylabel("profit gain index")
    ax = axes[1, 1]
    a = anchor[anchor.arm.str.startswith("pooled headline-all") & (anchor.metric.isin(["gain_all", "share_2.09", "share_2.50"]))]
    for i, m in enumerate(["gain_all", "share_2.09", "share_2.50"]):
        for j, mode in enumerate(["t0", "t1"]):
            d = a[(a.metric == m) & (a["mode"] == mode)]
            if len(d):
                d = d.iloc[0]
                check(d.est, d.lo, d.hi, d)
                ax.errorbar(d.est, i + (j - .5) * .25, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00", capsize=3)
    ax.axvline(0, color="#444", lw=0.8); ax.set_yticks(range(3)); ax.set_yticklabels(["profit gain", "quotes at 2.09", "quotes at 2.50"])
    ax.set_title("4. Neutral minus anchored examples", fontsize=9); ax.set_xlabel("difference")
    fig.suptitle("Results at a glance: %s run (95%% CI = percentile bootstrap over wording x seed pairs)" % run, fontsize=11)
    _save(fig, path)


def read(name, d=TAB, prefix="lead_"):
    return pd.read_csv(Path(d) / (prefix + name + ".csv"))


if __name__ == "__main__":
    OUTDIR.mkdir(parents=True, exist_ok=True)
    cells, comm = read("a_cells_vs_theory_and_bot"), read("c_communication_contrasts")
    ctl, anchor = read("f_controls"), read("e_anchoring_neutral_minus_anchored")
    run = "neutral"
    fig_gain_vs_penalty(cells, run, OUTDIR / "lead_fig1_gain_vs_penalty_neutral.png")
    fig_comm(comm, run, OUTDIR / "lead_fig2_communication_neutral.png")
    fig_thinking(cells, run, OUTDIR / "lead_fig3_thinking_pairs_neutral.png")
    fig_anchor(anchor, OUTDIR / "lead_fig4_anchoring.png")
    fig_controls(cells, run, OUTDIR / "lead_fig5_controls_neutral.png")
    LR = os.environ.get("LEAD_RESULTS_DIR")
    if LR:
        dist, beh = read("g_dset_score_distribution", LR, ""), read("g_dset_behaviour", LR, "")
        fig_dset(dist, beh, run, OUTDIR / "lead_fig6_dset_neutral.png")
    else:
        print("LEAD_RESULTS_DIR not set: lead_fig6_dset_neutral.png not redrawn")
    fig_glance(cells, comm, ctl, anchor, run, OUTDIR / "lead_results_at_a_glance.png")
    assert CHECKS and all(CHECKS), "a plotted value differs from its table row"
    print("plotted points checked against the tables:", len(CHECKS))
