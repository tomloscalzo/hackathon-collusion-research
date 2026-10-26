"""CI forest charts for paired_deltas.csv (tools/analysis_style/ci_forest.py is not on main, so this is a small local forest).
Usage: python -X utf8 figures.py"""
import sys, textwrap
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import arm_labels as AL
d = pd.read_csv(HERE / "paired_deltas.csv")
ARMS = ["wd-notice-only", "wd-noncomp", "wd-ask-noreport", "d-cot-monitor-a"]
COL = {"wd-notice-only": "#1b6ca8", "wd-noncomp": "#d9822b", "wd-ask-noreport": "#3a9a5b", "d-cot-monitor-a": "#8c8c8c"}
MODELS = ["gpt-oss-20b", "Qwen3-32B (thinking on)"]
FIGS = {
 "fig_forest_behaviour": ("Behaviour: five standard metrics (arm minus headline-chat control)", ["avg_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]),
 "fig_forest_cot": ("Reasoning content: watchdog mentions and EXPLICIT / STRATEGIC-UNNAMED shares (arm minus control)",
                    ["q_watchdog", "t_watchdog", "q_explicit_share", "q_strategic_share", "t_explicit_share", "t_strategic_share"]),
 "fig_forest_conceal": ("Concealment / appearance keyword (UNVALIDATED; arm minus control)", ["q_conceal", "q_conceal_strict", "t_conceal", "t_conceal_strict"]),
 "fig_forest_other": ("Length, rival-reaction reasoning and chat agreement words (arm minus control)", ["q_words", "t_words", "q_rival_react", "agree_share", "agree_per_msg"]),
}
for name, (title, meas) in FIGS.items():
    fig, axes = plt.subplots(len(meas), 1, figsize=(11, 3.3 * len(meas) + 1.0), constrained_layout=True)
    for ax, m in zip(axes, meas):
        lab = d[d.measure == m].label.iloc[0]
        y = 0; ticks = []; tl = []
        for mod in MODELS:
            for arm in ARMS:
                r = d[(d.measure == m) & (d.model == mod) & (d.arm == arm)]
                if r.empty or pd.isna(r.delta.iloc[0]): y += 1; continue
                r = r.iloc[0]
                ax.errorbar(r.delta, y, xerr=[[r.delta - r.ci_lo], [r.ci_hi - r.delta]], fmt="o" if mod == MODELS[0] else "s", color=COL[arm], capsize=3, ms=6, mfc=("white" if r.ci_lo <= 0 <= r.ci_hi else COL[arm]))
                ticks.append(y); tl.append(textwrap.fill("%s | %s" % ("gpt-oss" if mod == MODELS[0] else "Qwen3", AL.label(arm)), 46)); y += 1
            y += 0.6
        ax.axvline(0, color="k", lw=0.8, ls="--"); ax.set_yticks(ticks); ax.set_yticklabels(tl, fontsize=9); ax.invert_yaxis()
        ax.set_title(lab + " (own x-scale)", fontsize=10, loc="left"); ax.tick_params(axis="x", labelsize=9)
        ax.set_xlabel("difference, arm minus control (95% bootstrap CI over pairs)", fontsize=9)
    fig.suptitle(title, fontsize=11)
    fig.savefig(HERE / (name + ".png"), dpi=110); plt.close(fig)
print("ok")
