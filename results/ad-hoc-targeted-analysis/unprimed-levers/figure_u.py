"""Figure: paired differences (treatment minus reference) with 95% bootstrap CIs, one panel per standard metric.
Usage: python -X utf8 figure_u.py <paired_contrasts.csv> <out.png>"""
import os, sys
_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "tools", "analysis_style")):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "tools", "analysis_style"))
import arm_labels  # noqa: E402  (glossary labels "slug: short description", owner rule)
SLUG = {"fx-chat-p1 (control)": "fx-chat-p1", "+ CoT threat A": "fx-chat-p1-cot-a", "+ moral prime B": "fx-chat-p1-moral-b", "+ moral placebo": "fx-chat-p1-placebo-moral"}
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

P = pd.read_csv(sys.argv[1])
NL = chr(10)
M = [("avg_abs_spread", "Average absolute spread" + NL + "(price units, 1.00-5.00)"), ("price_index", "Price index" + NL + "(0 = 1.00, 1 = 3.00)"),
     ("profit_gain_index", "Profit gain index" + NL + "(0 = competitive, 1 = monopoly)"), ("competitive_share", "Competitive share" + NL + "(share of firm-rounds)"),
     ("matching_share", "Matching share" + NL + "(share of firm-rounds)")]
def contrast_label(t, r):
    key = " (key contrast)" if r != "fx-chat-p1 (control)" else ""
    return arm_labels.label(SLUG[t]) + NL + "minus " + arm_labels.label(SLUG[r]) + key


COL = ["#2a78d6", "#eb6834", "#1baf7a", "#c98500"]
rows = [(contrast_label(r.treatment, r.reference), r) for r in P.itertuples()]
fig, axes = plt.subplots(1, 5, figsize=(19, 5.2), sharey=True)
for ax, (m, title) in zip(axes, M):
    for i, (lab, r) in enumerate(rows):
        y = len(rows) - 1 - i
        d, lo, hi = getattr(r, m + "_d"), getattr(r, m + "_lo"), getattr(r, m + "_hi")
        ax.plot([lo, hi], [y, y], color=COL[i], lw=2, solid_capstyle="round")
        ax.plot([d], [y], "o", ms=8, color=COL[i], mec="white", mew=2, label=lab)
    ax.axvline(0, color="#888", lw=1, ls="--")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Paired difference, mean over pairs" + NL + "(metric units; dashed line = 0)", fontsize=9)
    ax.grid(axis="x", color="#ddd", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].set_yticks(range(len(rows)))
axes[0].set_yticklabels([lab for lab, _ in rows][::-1], fontsize=8.5)
n = int(P["n"].min())
fig.suptitle("Unprimed levers (formula payoff block, no example prices printed): paired differences with 95% bootstrap CIs." + NL +
             "Qwen3-32B, thinking on, private chat, penalty point 1, n = %d (wording, seed) pairs per contrast. EXPLORATORY." % n, fontsize=10.5)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, [x.replace(NL, " ") for x in l], loc="lower center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.12, 1, 0.92))
fig.savefig(sys.argv[2], dpi=150, bbox_inches="tight")
