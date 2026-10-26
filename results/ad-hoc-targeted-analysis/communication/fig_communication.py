#!/usr/bin/env python3
"""Figure for the communication report, drawn only from the committed cells_by_condition.csv (no raw run data needed).
Tick labels read "condition / arm slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv).
Usage (from this folder): python -X utf8 fig_communication.py   (communication.py calls it after writing the CSV)"""
import sys
import textwrap
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import arm_labels  # noqa: E402

ARMS = {"tacit": "headline-tacit", "private": "headline-chat", "monitored": "headline-monitored", "public": "m-pub", "unmonitored": "m-mon0"}
MODES = {"thinking off": "t0", "thinking on": "t1"}
cells = pd.read_csv(HERE / "cells_by_condition.csv")
order = list(ARMS)
cols = {"thinking off": "#1f77b4", "thinking on": "#d95f02"}
# tick: the communication level (slug: label), then the arm slug: label, wrapped
W = lambda t: textwrap.fill(t, 19, break_on_hyphens=False, break_long_words=False)
XT = {o: W(arm_labels.label(o)) + "\n" + W("(arm " + arm_labels.label(ARMS[o]) + ")") for o in order}
fig, ax = plt.subplots(1, 2, figsize=(13, 6.6))
plotted = []
for k, m in enumerate(MODES):
    for i, met in enumerate(["price_index", "competitive_share"]):
        d = cells[(cells["mode"] == m) & (cells.metric == met)].set_index("condition").loc[order]
        ax[i].errorbar(np.arange(5) + (k - .5) * .2, d["mean"], yerr=[d["mean"] - d.lo, d.hi - d["mean"]], fmt="o", color=cols[m],
                       label=arm_labels.label(MODES[m]) + " (Qwen3-32B reasoning mode)", capsize=3)
        plotted.append((m, met, d))
for i, (t, yl) in enumerate([("Price index, by communication condition", "price index = mean of (market price - 1) / 2" + chr(10) + "(0 = competitive floor 1.00, 1 = monopoly 3.00)"),
                             ("Competitive share, by communication condition", "competitive share" + chr(10) + "(share of scored firm-rounds that undercut or sit at the floor)")]):
    ax[i].set_xticks(range(5)); ax[i].set_xticklabels([XT[o] for o in order], rotation=0, fontsize=7); ax[i].set_title(t, fontsize=10); ax[i].grid(alpha=.3)
    ax[i].set_ylabel(yl, fontsize=8); ax[i].set_xlabel("communication condition (neutral run, penalty point p3)", fontsize=8)
ax[0].legend(fontsize=7.5, loc="lower right")
fig.suptitle("Price index and competitive share by communication condition: mean over the 20 (wording, seed) pairs per cell; bars = 95% bootstrap CI over the 20 pairs", fontsize=9)
plt.tight_layout(rect=[0, 0, 1, .95])
# check: the plotted points are the committed CSV values (no number changes)
ref = pd.read_csv(HERE / "cells_by_condition.csv")
for m, met, d in plotted:
    r = ref[(ref["mode"] == m) & (ref.metric == met)].set_index("condition").loc[order]
    assert np.array_equal(d["mean"].to_numpy(), r["mean"].to_numpy()) and np.array_equal(d.lo.to_numpy(), r.lo.to_numpy()) and np.array_equal(d.hi.to_numpy(), r.hi.to_numpy())
for i, met in enumerate(["price_index", "competitive_share"]):
    ys = [c.lines[0].get_ydata() for c in ax[i].containers]   # the data line of each errorbar series
    exp = [ref[(ref["mode"] == m) & (ref.metric == met)].set_index("condition").loc[order]["mean"].to_numpy() for m in MODES]
    assert len(ys) == 2 and all(np.allclose(np.asarray(y, float), e, rtol=0, atol=0) for y, e in zip(ys, exp)), "plotted means differ from CSV"
plt.savefig(HERE / "fig_communication.png", dpi=130)
print("fig_communication.png written; plotted values equal cells_by_condition.csv")
