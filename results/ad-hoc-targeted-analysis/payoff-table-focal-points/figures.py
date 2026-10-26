"""Figures of the payoff-table focal-points analysis, drawn from the committed CSVs only.

  fig_printed_share.png   <- quote_shares_pooled.csv            (focal_points.py calls printed_share)
  fig_formula_heatmap.png <- formula_no_numbers_paired.csv      (formula_no_numbers.py calls heat)
  fig_formula_quotes.png  <- formula_no_numbers_quotes.csv      (formula_no_numbers.py calls quotes_fig)

Arm and condition labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv,
via arm_labels); colours and colour scales are unchanged from the original figures.
Re-render all three from the CSVs in this folder: python -X utf8 figures.py
Each function returns the values it plotted; __main__ checks them against the CSVs."""
import os
import sys
import textwrap

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402

METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
           ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
ARMS = ["fx-chat-p1", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1", "fx-chat-p5"]
HEAD = ["headline-tacit", "headline-chat", "headline-monitored"]
BINS = ["1.00", "1.01-1.25", "1.26-1.50", "1.51-2.00", "2.01-3.00", "above 3.00"]
MODE = {"off": "t0", "on": "t1"}
L = arm_labels.label


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _ctl_slug(control):
    """'headline-chat p1' or 'neutral headline-chat p1' -> 'headline-chat'."""
    return [w for w in str(control).split() if w.startswith("headline-")][0]


def printed_share(P, path):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 5.6)); labs = []; x = 0; plotted = []
    for arm in HEAD:
        for m in ["t0", "t1"]:
            for i, (run, c) in enumerate([("neutral", "#1f77b4"), ("anchored", "#d95f02")]):
                v = P[(P.run == run) & (P.arm == arm) & (P["mode"] == m)].share_printed.iloc[0]
                plotted.append((run, arm, m, v))
                ax.bar(x + 0.2 * (2 * i - 1), v, 0.38, color=c, label=("neutral: evenly spaced example prices (printed examples 1.00 to 4.00)" if run == "neutral" else "anchored: payoff table prints the 2.09 theory price (printed examples 1.54, 2.09, 3.00)") if x == 0 else None)
            labs.append(textwrap.fill(L(arm), 22) + "\n" + L(m)); x += 1
    ax.set_xticks(range(x)); ax.set_xticklabels(labs, fontsize=7.5); ax.set_ylabel("share of quotes on a printed value")
    ax.set_ylim(0, 1); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=1, fontsize=8, title="Bar colour = which payoff-table variant the prompt printed", title_fontsize=8); ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("communication arm (headline-tacit = no chat, headline-chat = private chat, headline-monitored = chat a regulator reads) and thinking mode (t0 / t1)", fontsize=8)
    ax.set_title("Share of firm quotes that equal a number printed in the prompt " + "\n" + "(Qwen3-32B, 2 firms, 4 penalty points pooled, 20 games per penalty point)", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
    return plotted


def heat(D, path):
    plt = _plt()
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("gr", ["#1a9850", "#fee08b", "#d73027"])   # green = competitive, red = collusive
    rng = {"market_price_mean": (1, 3, False), "price_index": (0, 1, False), "profit_gain_index": (0, 1, False), "competitive_share": (0, 1, True), "matching_share": (0, 1, False)}
    labels, rows, keys = [], [], []
    for arm in ARMS:
        for mode in ("off", "on"):
            sub = D[(D.arm == arm) & (D["mode"] == mode)]
            if sub.empty:
                continue
            ctrl = [sub[sub.metric == c].control_mean.iloc[0] for c, _ in METRICS]
            val = [sub[sub.metric == c].arm_mean.iloc[0] for c, _ in METRICS]
            cs = _ctl_slug(sub.iloc[0].control)
            labels += [f"{L(cs)}\n(neutral control for {arm}; {L(MODE[mode])})", f"{L(arm)}\n({L(MODE[mode])})"]
            rows += [ctrl, val]; keys += [(arm, mode, "control_mean"), (arm, mode, "arm_mean")]
    fig, ax = plt.subplots(figsize=(14.5, 0.62 * len(rows) + 2.4))
    for i, r in enumerate(rows):
        for j, ((c, nm), v) in enumerate(zip(METRICS, r)):
            lo, hi, rev = rng[c]
            x = (v - lo) / (hi - lo)
            x = 1 - x if rev else x
            ax.add_patch(plt.Rectangle((j, i), 1, 1, color=cmap(min(max(x, 0), 1)), ec="white", lw=1.5 if i % 2 else 0.5))
            ax.text(j + .5, i + .5, f"{v:.2f}", ha="center", va="center", fontsize=10, fontweight="bold" if i % 2 else "normal")
    ax.set_xlim(0, 5); ax.set_ylim(len(rows), 0)
    ax.set_xticks(np.arange(5) + .5); ax.set_xticklabels([n.replace(" (", "\n(") for _, n in METRICS], fontsize=9.5)
    ax.xaxis.tick_top(); ax.set_yticks(np.arange(len(rows)) + .5); ax.set_yticklabels(labels, fontsize=8.5)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    sm = plt.cm.ScalarMappable(cmap=cmap); sm.set_array([0, 1])
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, ticks=[0, 1]); cb.ax.set_yticklabels(["competitive\n(green)", "collusive\n(red)"], fontsize=8.5)
    ax.set_title("Mean of each metric per cell: neutral control (even rows) and formula / no-numbers arm (bold rows)\n"
                 "Colour = how collusive the value is (green competitive, red collusive); competitive share is coloured with high = green", fontsize=9.5, pad=40)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)
    return list(zip(keys, rows))


def quotes_fig(Q, path):
    plt = _plt()
    cols = ["#1a9850", "#91cf60", "#d9ef8b", "#fee08b", "#fc8d59", "#d73027"]   # low quotes green, high quotes red
    cells = [(a, m) for a in ARMS for m in ("off", "on") if ((Q.arm == a) & (Q["mode"] == m)).any()]
    fig, ax = plt.subplots(figsize=(13.5, 0.5 * 2 * len(cells) + 2.2))
    y = 0; yt, yl, plotted = [], [], []
    for a, m in cells:
        for _, r in Q[(Q.arm == a) & (Q["mode"] == m)].sort_values("is_control", ascending=False).iterrows():
            left = 0
            for nm, c in zip(BINS, cols):
                w = r["share_" + nm]
                plotted.append((a, m, bool(r.is_control), nm, w))
                ax.barh(y, w, left=left, color=c, ec="white", lw=.5, label=nm if y == 0 else None)
                if w >= .07:
                    ax.text(left + w / 2, y, f"{w:.0%}", ha="center", va="center", fontsize=7.5)
                left += w
            if r.is_control:
                yl.append(f"{L(_ctl_slug(r.who))}\n(neutral control for {a}; {L(MODE[m])})")
            else:
                yl.append(f"{L(a)}\n({L(MODE[m])})")
            yt.append(y); y += 1
        y += .6
    ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=7.5); ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.set_xlabel("share of all firm quotes in the cell (each bar sums to 100%)")
    ax.legend(title="quote (half-spread) range", ncol=6, fontsize=7.5, title_fontsize=8, loc="lower center", bbox_to_anchor=(.5, 1.0))
    ax.set_title("Where the quotes sit: neutral control vs formula / no-numbers arm", fontsize=9.5, pad=40)
    fig.tight_layout(); fig.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.15); plt.close(fig)
    return plotted


def _check(cond, msg):
    if not cond:
        raise AssertionError(msg)


if __name__ == "__main__":
    os.chdir(HERE)
    P = pd.read_csv("quote_shares_pooled.csv")
    got = printed_share(P, "fig_printed_share.png")
    for run, arm, m, v in got:
        _check(v == P[(P.run == run) & (P.arm == arm) & (P["mode"] == m)].share_printed.iloc[0], (run, arm, m))
    _check(len(got) == 12, "printed_share bars")
    D = pd.read_csv("formula_no_numbers_paired.csv")
    got = heat(D, "fig_formula_heatmap.png")
    for (arm, mode, col), row in got:
        exp = [D[(D.arm == arm) & (D["mode"] == mode) & (D.metric == c)][col].iloc[0] for c, _ in METRICS]
        _check(row == exp, (arm, mode, col))
    _check(len(got) == 18, "heat rows")
    Q = pd.read_csv("formula_no_numbers_quotes.csv")
    got = quotes_fig(Q, "fig_formula_quotes.png")
    for a, m, ctl, nm, w in got:
        _check(w == Q[(Q.arm == a) & (Q["mode"] == m) & (Q.is_control == ctl)]["share_" + nm].iloc[0], (a, m, ctl, nm))
    _check(len(got) == 18 * 6, "quote segments")
    print("payoff-table-focal-points: 3 figures re-rendered; plotted values equal the CSVs")
