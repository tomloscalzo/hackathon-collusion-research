#!/usr/bin/env python3
"""Figures for the copy-bot analysis. Usage: python -X utf8 copybot_figures.py (reads standard_metrics.csv and copybot_game_metrics.csv in this folder)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
from collusion_colors import COLLUSION_CMAP  # red = more collusive, green = more competitive

r = pd.read_csv(HERE / "standard_metrics.csv", dtype={"opening": str})
M = [("avg_abs_spread", "Average absolute\nspread (quote units)", 1.0, 1), ("price_index", "Price index\n(0-1)", 0.5, 1), ("profit_gain_index", "Profit gain index\n(0-1)", 0.5, 1),
     ("competitive_share", "Competitive share\n(U16, share)", 0.3, -1), ("matching_share", "Matching share\n(share)", 0.4, 1)]
cells = [("2.50", "off"), ("2.50", "on"), ("1.50", "off"), ("1.50", "on")]
Z = np.zeros((4, 5)); lab = [[""] * 5 for _ in range(4)]
for i, (o, t) in enumerate(cells):
    for j, (k, _, sc, sign) in enumerate(M):
        x = r[(r.opening == o) & (r.thinking == t) & (r.metric == k)].iloc[0]
        Z[i, j] = np.clip(sign * x["diff"] / sc, -1, 1)
        lab[i][j] = "%+.2f\n[%+.2f, %+.2f]" % (x["diff"], x.ci_lo, x.ci_hi)
fig, ax = plt.subplots(figsize=(13.5, 6.2))
im = ax.imshow(Z, cmap=COLLUSION_CMAP, vmin=-1, vmax=1, aspect="auto")
for i in range(4):
    for j in range(5):
        ax.text(j, i, lab[i][j], ha="center", va="center", fontsize=13, fontweight="bold")
ax.set_xticks(range(5)); ax.set_xticklabels([m[1] for m in M], fontsize=11)
ax.set_yticks(range(4)); ax.set_yticklabels(["copier opens 2.50,\nthinking off", "copier opens 2.50,\nthinking on", "copier opens 1.50,\nthinking off", "copier opens 1.50,\nthinking on"], fontsize=11)
ax.set_xlabel("standard metric (each analysed separately; cell = mean paired difference, [95% bootstrap CI over 20 pairs])", fontsize=10)
ax.set_ylabel("cell: LLM vs copier, copier opening quote, thinking mode", fontsize=10)
ax.set_title("Figure 1. LLM-vs-copier minus LLM-vs-LLM headline, tacit, penalty point 1, neutral table (20 pairs per cell)", fontsize=11)
cb = fig.colorbar(im, ax=ax, ticks=[-1, 0, 1]); cb.ax.set_yticklabels(["more competitive\n(green)", "0 = same as\nheadline", "more collusive\n(red)"])
cb.set_label("difference as a fraction of a fixed scale per metric\nred = more collusive / green = more competitive", fontsize=9, labelpad=8)
fig.tight_layout(); fig.savefig(HERE / "copybot_fig1_difference_map.png", dpi=130)

g = pd.read_csv(HERE / "copybot_game_metrics.csv", dtype={"wording": str, "seed": str, "thinking": str})
h = g[g.kind == "headline"].set_index(["wording", "seed", "thinking"]).price_index
fig, axs = plt.subplots(1, 4, figsize=(14, 4.2), sharex=True, sharey=True)
for a, (o, t) in zip(axs, cells):
    arm = "copybot-o250-tacit" if o == "2.50" else "copybot-o150-tacit"; tt = "0" if t == "off" else "1"
    c = g[(g.arm == arm) & (g.thinking == tt)].set_index(["wording", "seed", "thinking"]).price_index
    j = pd.concat([h.rename("h"), c.rename("c")], axis=1, join="inner")
    a.plot([0, 1], [0, 1], color="grey", ls=":", label="same index in both games")
    a.scatter(j.h, j.c, s=30, color="#1b6ca8", alpha=.75, label="one dot = one (wording, seed) pair")
    a.set_title("copier opens %s, thinking %s (n = %d)" % (o, t, len(j)), fontsize=10); a.set_xlabel("price index, LLM-vs-LLM headline game", fontsize=9)
axs[0].set_ylabel("price index, LLM-vs-copier game", fontsize=9); axs[0].legend(fontsize=8, loc="upper left")
fig.suptitle("Figure 2. Price index per pair: LLM vs copier (vertical) against the matching LLM-vs-LLM headline game (horizontal); tacit, penalty point 1, neutral table", fontsize=10)
fig.tight_layout(rect=[0, 0, 1, .93]); fig.savefig(HERE / "copybot_fig2_pairs.png", dpi=130)
