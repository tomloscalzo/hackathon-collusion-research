"""Figure of the penalty analysis, drawn from the committed cells_by_penalty_point.csv only.
penalty.py calls fig_penalty(cells); re-render alone with: python -X utf8 figures.py
Labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv via arm_labels);
colours and scales are unchanged. Returns the plotted values; __main__ checks them against the CSV."""
import os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
L = arm_labels.label
THETA = {1: 0.7029, 3: 0.5459, 4: 0.3249, 5: 0.0}      # sustainable price index (theory curve)
THEORY_GAIN = {1: 0.912, 3: 0.794, 4: 0.544, 5: 0.0}   # same curve on the profit gain index (from FINAL_NUMBERS.md)
ARM = {"tacit": "headline-tacit", "chat": "headline-chat", "monitored": "headline-monitored"}


def fig_penalty(cells, path="fig_penalty.png"):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 5.8), sharey=True)
    col = {"tacit": "#7570b3", "chat": "#1b9e77", "monitored": "#d95f02"}
    LEG = {c: f"{L(ARM[c])} (= {c} in the tables)" for c in col}
    pts = [1, 3, 4, 5]; plotted = []
    for k, m in enumerate(["t0", "t1"]):
        for c in col:
            d = cells[(cells.cond == c) & (cells["mode"] == m) & (cells.metric == "profit_gain_index")].set_index("penalty_point").loc[pts]
            x = np.arange(4) + (list(col).index(c) - 1) * .08
            plotted.append((c, m, list(d["mean"]), list(d.lo), list(d.hi)))
            ax[k].errorbar(x, d["mean"], yerr=[d["mean"] - d.lo, d.hi - d["mean"]], fmt="o-", color=col[c], label=LEG[c], capsize=2)
        ax[k].plot(range(4), [THEORY_GAIN[p] for p in pts], "k--", label="theory: sustainable collusive profit gain index")
        ax[k].set_xticks(range(4)); ax[k].set_xticklabels([arm_labels.labels([f"p{p}"], wrap=22)[0] + f"\n(theta* {THETA[p]:.2f})" for p in pts], fontsize=8)
        ax[k].set_title(L(m), fontsize=10); ax[k].grid(alpha=.3)
        ax[k].set_xlabel("Penalty point p1, p3, p4, p5 (p1 = collusion clearly pays, p5 = clearly does not);\ntheta* = theory's sustainable collusive price index", fontsize=8)
    ax[0].set_ylabel("Profit gain index (0 = competitive profit, 1 = monopoly profit)\nmean over 20 games; bars = 95% bootstrap CI over the 20 pairs", fontsize=8)
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=8, frameon=False)
    fig.suptitle("Neutral run, Qwen3-32B: profit gain index by penalty point, communication arm and thinking mode (20 games per point)", fontsize=10)
    plt.tight_layout(rect=(0, 0.12, 1, 0.95)); plt.savefig(path, dpi=130); plt.close(fig)
    return plotted


if __name__ == "__main__":
    os.chdir(HERE)
    cells = pd.read_csv("cells_by_penalty_point.csv")
    got = fig_penalty(cells)
    for c, m, mu, lo, hi in got:
        d = cells[(cells.cond == c) & (cells["mode"] == m) & (cells.metric == "profit_gain_index")].set_index("penalty_point").loc[[1, 3, 4, 5]]
        assert mu == list(d["mean"]) and lo == list(d.lo) and hi == list(d.hi), (c, m)
    assert len(got) == 6
    print("penalty: fig_penalty.png re-rendered; plotted values equal cells_by_penalty_point.csv")
