"""Figure 1 of the CoT-monitor-threat report, drawn only from the committed paired_effects.csv (analyze.py calls it after writing it).
Rows read "run slug: label / arm slug: label" from the shared glossary (tools/analysis_style/arm_glossary.csv).
Run (from this folder): python -X utf8 fig_threat_effects.py"""
import os, sys, textwrap
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
E = pd.read_csv(os.path.join(HERE, "paired_effects.csv"))
XL = {"price_index": "paired difference in price index" + chr(10) + "(negative = threat lowered prices)",
      "competitive_share": "paired difference in competitive share" + chr(10) + "(positive = more undercutting)",
      "matching_share": "paired difference in matching share" + chr(10) + "(negative = less following)"}
TT = {m: arm_labels.label(m) + "; threat minus control" for m in ("price_index", "competitive_share", "matching_share")}
ROWS = [(r, a) for r in ["neutral", "anchored"] for a in ["d-cot-monitor-a", "d-cot-monitor-b"]]
W = lambda t: textwrap.fill(t, 34, break_on_hyphens=False, break_long_words=False)
YT = ["%s run, threat %s\n%s" % (r, a[-1].upper(), W(arm_labels.label(a))) for r, a in ROWS]
fig, ax = plt.subplots(1, 3, figsize=(13, 5.4))
for k, m in enumerate(["price_index", "competitive_share", "matching_share"]):
    for i, (run, arm) in enumerate(ROWS):
        r = E[(E.run == run) & (E.arm == arm) & (E.measure == m)].iloc[0]
        ax[k].errorbar(r.delta, i, xerr=[[r.delta - r.lo], [r.hi - r.delta]], fmt="o", color="#1f5fa8" if run == "neutral" else "#c0562b", capsize=3)
    ax[k].axvline(0, color="grey", lw=.8); ax[k].set_yticks(range(4)); ax[k].set_yticklabels(YT if k == 0 else [], fontsize=8)
    ax[k].set_title(TT[m], fontsize=9); ax[k].invert_yaxis(); ax[k].set_xlabel(XL[m], fontsize=8)
fig.suptitle("Effect of the idle chain-of-thought (CoT) monitoring threat vs the headline-chat control (headline-chat: private chat, no other lever;" + chr(10)
             + "t1: thinking on, private chat, p1: penalty point 1; 20 (wording, seed) pairs per row)", fontsize=9)
fig.legend(handles=[Line2D([0], [0], marker="o", color="#1f5fa8", label=arm_labels.label("neutral") + " (1.00-4.00)"),
                    Line2D([0], [0], marker="o", color="#c0562b", label=arm_labels.label("anchored") + " (examples at 1.54, 2.09, 3.00)"),
                    Line2D([0], [0], color="grey", lw=.8, label="zero line = no difference from control")], loc="lower center", ncol=3, fontsize=8, frameon=False)
fig.text(.5, .075, "dot = mean paired difference; bar = 95% percentile bootstrap CI over the 20 pairs (10,000 resamples). Threat A / B = the two permission wordings (see table under the figure).", ha="center", fontsize=7.5)
plt.tight_layout(rect=[0, .11, 1, .93])
# check: plotted points and bars equal the committed CSV values (no number changes)
for k, m in enumerate(["price_index", "competitive_share", "matching_share"]):
    for c, (run, arm) in zip(ax[k].containers, ROWS):
        r = E[(E.run == run) & (E.arm == arm) & (E.measure == m)].iloc[0]
        assert np.asarray(c.lines[0].get_xdata(), float)[0] == r.delta
        seg = c.lines[2][0].get_segments()[0][:, 0]
        assert np.allclose(seg, [r.lo, r.hi], rtol=0, atol=1e-12)
plt.savefig(os.path.join(HERE, "fig_threat_effects.png"), dpi=130)
print("fig_threat_effects.png written; plotted values equal paired_effects.csv")
