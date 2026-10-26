#!/usr/bin/env python3
"""Price-path figure for the 5-tick-start report, drawn only from the committed paths_by_round.csv (analyze.py calls it after writing it).
Legend and panel titles read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv).
usage: python -X utf8 five_tick_figure.py [--out .]"""
import argparse, os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=HERE); A, _ = ap.parse_known_args()
PB = pd.read_csv(os.path.join(A.out, "paths_by_round.csv"))
ARM, CTL = "start-5tick", "headline-chat"
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
drawn = []
for ax, mode in zip(axes, ("off", "on")):
    for arm, cl, lb in ((ARM, "#d95f02", arm_labels.label(ARM)), (CTL, "#1f77b4", arm_labels.label(CTL) + " (control)")):
        s = PB[(PB.arm == arm) & (PB.thinking == mode) & (PB.n_games >= 8)]
        ln, = ax.plot(s["round"], s.price_index, color=cl, marker="o", ms=3, label=lb)
        drawn.append((ln, arm, mode))
    t = "t0" if mode == "off" else "t1"
    ax.set_title(f"{arm_labels.label(t)} (Qwen3-32B reasoning mode {mode})", fontsize=10); ax.set_xlabel("round number (drawn only where at least 8 games reached it)", fontsize=8); ax.grid(alpha=.25); ax.set_ylim(0, 0.9)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
axes[0].set_ylabel("market price index = (market price - 1) / 2" + chr(10) + "mean over games (0 = competitive floor 1.00, 1 = monopoly 3.00)", fontsize=8); axes[0].legend(fontsize=8, loc="center right")
fig.suptitle("Market price index by round: 5-tick start vs private-chat control (neutral run, penalty point p3, mean over up to 20 games per arm and mode)", fontsize=9)
fig.tight_layout(rect=[0, 0, 1, .95])
# check: every plotted point equals the committed CSV value (no number changes)
ref = pd.read_csv(os.path.join(A.out, "paths_by_round.csv"))
for ln, arm, mode in drawn:
    s = ref[(ref.arm == arm) & (ref.thinking == mode) & (ref.n_games >= 8)]
    assert np.array_equal(np.asarray(ln.get_xdata()), s["round"].to_numpy()) and np.array_equal(np.asarray(ln.get_ydata(), float), s.price_index.to_numpy())
fig.savefig(os.path.join(A.out, "five_tick.png"), dpi=130)
print("five_tick.png written; plotted values equal paths_by_round.csv")
