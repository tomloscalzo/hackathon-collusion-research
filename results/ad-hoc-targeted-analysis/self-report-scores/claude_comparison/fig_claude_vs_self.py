"""Re-render fig_claude_vs_self.png from the committed claude_vs_self_report_arms.csv (labels only; no number recomputed).
The drawing follows fig_self() in conflict-score-validation/claude_ratings.py, which wrote the original from the same table;
here the points are tagged with their arm slug and a key printed in the figure gives "slug: short label" from the shared
glossary (tools/analysis_style/arm_labels.py). Usage: python -X utf8 fig_claude_vs_self.py"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools" / "analysis_style"))
import arm_labels  # noqa: E402

t = pd.read_csv(HERE / "claude_vs_self_report_arms.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
col = {"off": "#1f77b4", "on": "#d95f02"}
mk = {"anchored": "o", "neutral": "s"}
plotted = []
for ax, sn, rl in zip(axes, ("conflict_score", "temptation_score"), ("conflict", "temptation")):
    d = t[t.score_name == sn]
    for _, r in d.iterrows():
        ax.scatter(r.claude_same_scale, r.self_score, c=col[r.thinking], marker=mk[r.run], s=40)
        ax.annotate(r.arm, (r.claude_same_scale, r.self_score), fontsize=7, xytext=(3, 3), textcoords="offset points")
        plotted.append((r.arm, r.run, r.thinking, r.claude_same_scale, r.self_score))
    ax.set_xlabel("Claude-rated %s of the prompt (1-5, mean over the arm's prompts)" % rl, fontsize=9)
    ax.set_ylabel("Models' self-reported %s score (1-5, mean over games)" % rl, fontsize=9)
    ax.set_title("Self-reported %s versus Claude-rated, per arm x run x thinking" % rl, fontsize=9)
    ax.grid(alpha=.2)
h = [plt.Line2D([], [], marker="o", ls="", c=col["off"], label=arm_labels.label("t0")), plt.Line2D([], [], marker="o", ls="", c=col["on"], label=arm_labels.label("t1")),
     plt.Line2D([], [], marker="o", ls="", c="grey", label=arm_labels.label("anchored") + " run"), plt.Line2D([], [], marker="s", ls="", c="grey", label=arm_labels.label("neutral") + " run")]
fig.legend(handles=h, loc="lower center", ncol=2, fontsize=8.5, bbox_to_anchor=(0.5, 0.06))
key = "Point labels (arm slugs): " + ";   ".join(arm_labels.label(a) for a in ["d-conflict", "d-temptation-a", "d-temptation-b"])
fig.text(0.5, 0.015, key, ha="center", fontsize=8)
fig.tight_layout(rect=(0, 0.17, 1, 1))
fig.savefig(HERE / "fig_claude_vs_self.png", dpi=120)
plt.close(fig)
# check (c): the plotted values are the committed CSV values
t2 = pd.read_csv(HERE / "claude_vs_self_report_arms.csv").set_index(["arm", "run", "thinking"])
for arm, run, th, x, y in plotted:
    assert (x, y) == (t2.loc[(arm, run, th), "claude_same_scale"], t2.loc[(arm, run, th), "self_score"])
print("fig_claude_vs_self.png written; plotted values equal claude_vs_self_report_arms.csv:", len(plotted), "points")
