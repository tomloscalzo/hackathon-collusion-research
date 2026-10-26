"""Figure of the incentives analysis, drawn from the committed incentives_contrasts.csv only.
analyze.py calls fig_incentives(R); re-render alone with: python -X utf8 figures.py
Labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv via arm_labels);
colours and scales are unchanged. Returns the plotted values; __main__ checks them against the CSV."""
import os, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
ARMS = ["m-inc-target", "m-inc-joint"]
MEAS = [("price_index", "Price index"), ("comp_share", "Competitive share")]


def fig_incentives(R, path="incentives.png"):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    N = R[R.run == "neutral"]; plotted = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, (col, nm) in zip(axes, MEAS):
        for i, arm in enumerate(ARMS):
            for mode, off, cl in (("off", -.15, "#1f77b4"), ("on", .15, "#d95f02")):
                s = N[(N.arm == arm) & (N.measure == col) & (N["mode"] == mode)].iloc[0]
                plotted.append((arm, col, mode, s["diff"], s.ci_lo, s.ci_hi))
                ax.plot([s.ci_lo, s.ci_hi], [i + off] * 2, color=cl, lw=2); ax.plot(s["diff"], i + off, "o", color=cl)
        ax.axvline(0, color="#444", ls="--", lw=1); ax.set_title(f"{nm} (arm minus headline-chat)" + ("\n(market price - 1)/2" if col == "price_index" else "\nshare of firm-rounds undercutting or at floor"), fontsize=8)
        ax.set_yticks(range(2)); ax.set_yticklabels(arm_labels.labels(ARMS, wrap=24), fontsize=9); ax.set_ylim(1.6, -.6); ax.grid(axis="x", alpha=.25)
        ax.set_xlabel("paired difference, arm minus headline-chat\n(dot = mean of 20 pairs; bar = 95% bootstrap CI)", fontsize=8)
    axes[0].plot([], [], "o-", color="#1f77b4", label=arm_labels.label("t0") + " (Qwen3-32B reasoning mode switched off)"); axes[0].plot([], [], "o-", color="#d95f02", label=arm_labels.label("t1") + " (reasoning mode switched on)"); fig.legend(loc="lower center", ncol=2, fontsize=8)
    fig.suptitle("Effect of two incentive texts versus the private-chat control headline-chat: private chat, no other lever (neutral run, penalty point p3,\nQwen3-32B, 2 firms, 20 (wording, seed) pairs per mode). Price index up / competitive share down = more collusion", fontsize=8)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95)); fig.savefig(path, dpi=130); plt.close(fig)
    return plotted


if __name__ == "__main__":
    os.chdir(HERE)
    R = pd.read_csv("incentives_contrasts.csv")
    got = fig_incentives(R)
    for arm, col, mode, d, lo, hi in got:
        s = R[(R.run == "neutral") & (R.arm == arm) & (R.measure == col) & (R["mode"] == mode)].iloc[0]
        assert (d, lo, hi) == (s["diff"], s.ci_lo, s.ci_hi), (arm, col, mode)
    assert len(got) == 8
    print("incentives: incentives.png re-rendered; plotted values equal incentives_contrasts.csv")
