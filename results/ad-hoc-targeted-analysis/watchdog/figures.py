"""Draws fig_contrasts.png and fig_trigger_rate.png from contrasts.csv and trigger_rate_by_round.csv (the committed outputs of
analyze.py). analyze.py calls draw_contrasts / draw_trigger with its in-memory tables; run this file alone to re-render the two
figures from the CSVs without touching any CSV. Arm labels are "slug: short label" from the shared glossary (arm_labels.py).
Run: python figures.py"""
import limits  # noqa: F401  (CPU rule)
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import arm_labels  # noqa: E402

SLUG = {"control": "headline-chat", "notice-only": "wd-notice-only", "noncomp": "wd-noncomp", "ask-noreport": "wd-ask-noreport"}
CON = [("notice-only minus control", "notice-only", "control"), ("noncomp minus notice-only", "noncomp", "notice-only"),
       ("noncomp minus ask-noreport", "noncomp", "ask-noreport"), ("ask-noreport minus control", "ask-noreport", "control")]
METS = ["mean_quote", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
COL = {"thinking off": "#1f5fa8", "thinking on": "#c0562b"}
MODELAB = {"thinking off": "thinking off (t0)", "thinking on": "thinking on (t1)"}


def contrast_label(a, b):
    return arm_labels.label(SLUG[a]) + "\nminus " + arm_labels.label(SLUG[b])


def draw_contrasts(C, out):
    fig, ax = plt.subplots(1, 5, figsize=(20, 5.2), sharey=True)
    names = [c[0] for c in CON]
    plotted = []
    for k, m in enumerate(METS):
        for mi, mode in enumerate(["thinking off", "thinking on"]):
            for i, nme in enumerate(names):
                r = C[(C["mode"] == mode) & (C.contrast == nme) & (C.metric == m)].iloc[0]
                y = i + (mi - .5) * .3
                ax[k].errorbar(r["diff"], y, xerr=[[r["diff"] - r.ci_lo], [r.ci_hi - r["diff"]]], fmt="o" if mode == "thinking off" else "s",
                               color=COL[mode], capsize=3, label=MODELAB[mode] if i == 0 else None)
                plotted.append((mode, nme, m, r["diff"], r.ci_lo, r.ci_hi))
        ax[k].axvline(0, color="grey", lw=.8)
        ax[k].set_title({"mean_quote": "Average spread", "price_index": "Price index", "competitive_share": "Competitive share", "profit_gain_index": "Profit gain index", "matching_share": "Matching share"}[m], fontsize=10)
        ax[k].set_xlabel("first arm minus second arm\n(" + {"mean_quote": "half-spread units", "price_index": "index units, 0-1 scale", "competitive_share": "share units", "profit_gain_index": "index units, 0-1 scale", "matching_share": "share units"}[m] + ")", fontsize=8)
        ax[k].set_yticks(range(4)); ax[k].invert_yaxis()
    ax[0].set_yticklabels([contrast_label(a, b) for _, a, b in CON], fontsize=8)
    h, l = ax[0].get_legend_handles_labels(); fig.legend(h, l, fontsize=8, loc="lower center", ncol=2)
    fig.suptitle("Watchdog arms, paired differences (first arm minus second arm), neutral run, penalty point 1, 20 (wording, seed) pairs (19 where wave-B thinking on is involved); dot = mean, bar = 95% bootstrap CI over pairs, grey line = no difference", fontsize=8.5)
    plt.tight_layout(rect=(0, 0.07, 1, 0.94)); plt.savefig(out, dpi=130); plt.close()
    return plotted


def draw_trigger(RB, out):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    plotted = []
    for k, mode in enumerate(["thinking off", "thinking on"]):
        for lab, c, ls in [("noncomp", "#1f5fa8", "-"), ("ask-noreport", "#c0562b", "--")]:
            s = RB[(RB.label == lab) & (RB["mode"] == mode)]
            ax[k].plot(range(len(s)), s.rate, ls, marker="o", color=c, label=arm_labels.label(SLUG[lab]) + " (asked)")
            ax[k].plot(range(len(s)), s.triggered_share, ":", marker="x", color=c, label=arm_labels.label(SLUG[lab]) + " (rule says ask)")
            plotted.append((lab, mode, list(s.rate), list(s.triggered_share)))
        ax[k].set_xticks(range(len(s))); ax[k].set_xticklabels(s.rounds); ax[k].set_xlabel("round of the game"); ax[k].set_title(MODELAB[mode], fontsize=10); ax[k].set_ylim(0, 1)
    ax[0].set_ylabel("share of eligible firm-rounds\n(asked / eligible, or rule says ask / eligible)")
    h, l = ax[0].get_legend_handles_labels(); fig.legend(h, l, fontsize=8, loc="lower center", ncol=2, frameon=False)
    fig.suptitle("Watchdog trigger rate by round bin, penalty point 1, neutral run, private chat (20 games per arm thinking off, 19 thinking on); eligible = firm-round from round 2", fontsize=8.5)
    plt.tight_layout(rect=(0, 0.13, 1, 0.93)); plt.savefig(out, dpi=130); plt.close()
    return plotted


if __name__ == "__main__":
    C = pd.read_csv(HERE / "contrasts.csv"); RB = pd.read_csv(HERE / "trigger_rate_by_round.csv", dtype={"rounds": str})
    pc = draw_contrasts(C, HERE / "fig_contrasts.png")
    pt = draw_trigger(RB, HERE / "fig_trigger_rate.png")
    # check (c): every plotted value equals the committed CSV value
    C2 = pd.read_csv(HERE / "contrasts.csv").set_index(["mode", "contrast", "metric"])
    for mode, nme, m, d, lo, hi in pc:
        assert np.allclose([d, lo, hi], C2.loc[(mode, nme, m), ["diff", "ci_lo", "ci_hi"]].astype(float).values, rtol=0, atol=0)
    R2 = pd.read_csv(HERE / "trigger_rate_by_round.csv")
    for lab, mode, rate, trig in pt:
        s = R2[(R2.label == lab) & (R2["mode"] == mode)]
        assert list(s.rate) == rate and list(s.triggered_share) == trig
    print("figures re-rendered; plotted values equal the CSVs:", len(pc), "contrast points,", sum(len(p[2]) for p in pt), "trigger points per series set")
