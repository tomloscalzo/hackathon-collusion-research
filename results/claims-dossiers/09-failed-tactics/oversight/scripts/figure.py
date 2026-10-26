"""Forest plot: price index and profit gain index, tactic arm minus matched control, by model and mode.
Usage: python -X utf8 figure.py  (after oversight_contrasts.py)"""
import sys
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
from pathlib import Path
OUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools" / "analysis_style"))
import arm_labels
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, pandas as pd, numpy as np
C = pd.read_csv(OUT / "contrasts.csv")
order = ["d-cot-monitor-a", "d-cot-monitor-b", "headline-monitored", "wd-notice-only", "wd-noncomp", "wd-ask-noreport",
         "wd-noncomp vs wd-ask-noreport", "m-asym"]
short = {"wd-noncomp vs wd-ask-noreport": "report threat increment: asks + may report minus asks only"}
def tick(s):
    if s in short: return "\n".join(__import__("textwrap").wrap(short[s], 30))
    return "\n".join(__import__("textwrap").wrap(arm_labels.label(s), 30))
modes = [("gpt-oss medium", "#1f77b4", "o", "gpt-oss-20b, reasoning effort medium"),
         ("Qwen thinking on", "#d62728", "s", "Qwen3-32B, thinking on"),
         ("Qwen thinking off", "#7f7f7f", "^", "Qwen3-32B, thinking off")]
fig, axes = plt.subplots(1, 2, figsize=(12, 9), sharey=True, constrained_layout=True)
for ax, met in zip(axes, ["Price index", "Profit gain index"]):
    for k, (mo, col, mk, lab) in enumerate(modes):
        for i, s in enumerate(order):
            r = C[(C.slug == s) & (C.model_mode == mo) & (C.metric == met)]
            if r.empty: continue
            r = r.iloc[0]; y = i + (k - 1) * 0.25
            ax.errorbar(r.effect, y, xerr=[[r.effect - r.ci_lo], [r.ci_hi - r.effect]], fmt=mk, color=col,
                        mfc=col if r.holm_p < 0.05 else "white", ms=7, capsize=3, label=lab if i == 0 or (s == "headline-monitored" and k == 1) else None)
    ax.axvline(0, color="0.4", lw=1)
    ax.set_xlabel(f"{met}: tactic arm minus matched control\n(paired mean, 95% bootstrap CI; negative = less collusive)", fontsize=10)
    ax.set_title(f"{met} (0 = competitive, 1 = monopoly)", fontsize=11)
    ax.grid(axis="x", alpha=.3)
axes[0].set_yticks(range(len(order))); axes[0].set_yticklabels([tick(s) for s in order], fontsize=9)
axes[0].invert_yaxis()
from matplotlib.lines import Line2D
hs = [Line2D([], [], color=c, marker=m, ls="-", mfc="white", ms=7) for _, c, m, _ in modes]
fig.legend(hs, [l for *_, l in modes], loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=10,
           title="Model and mode (filled marker = Holm p < 0.05 within that model-mode's oversight family; hollow = not)")
fig.suptitle("Oversight tactics on gpt-oss-20b vs Qwen3-32B: paired effect on price and profit (neutral run; n = 19 to 20 pairs per row, 80 for monitored chat)", fontsize=12)
fig.savefig(OUT / "fig_oversight_forest.png", dpi=130, bbox_inches="tight")
print(arm_labels.legend_table([s for s in order if " vs " not in s]))
