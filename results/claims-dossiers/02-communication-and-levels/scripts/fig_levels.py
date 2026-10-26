"""Figure: cell levels of the five metrics by penalty point, no chat vs private chat, three model-modes.
usage: python -X utf8 fig_levels.py TABLES_DIR OUT_PNG   (reads cell_levels.csv written by dossier02.py)
Created by Claude at the prompting of the repository owner."""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

c = pd.read_csv(sys.argv[1] + "/cell_levels.csv")
M = [("market_price_mean", "Average absolute spread\n(raw half-spread, 1.00 to 5.00)", "higher = more collusive"),
     ("price_index", "Price index\n(0 = floor 1.00, 1 = monopoly 3.00)", "higher = more collusive"),
     ("profit_gain_index", "Profit gain index\n(0 = competitive, 1 = monopoly profit)", "higher = more collusive"),
     ("competitive_share", "Competitive share (U16)\n(share of firm-rounds undercutting)", "higher = more competitive"),
     ("matching_share", "Matching share\n(share of firm-rounds matching rival)", "higher = more collusive")]
COL = {"gpt-oss-20b": "#1f77b4", "Qwen3-32B t1": "#d62728", "Qwen3-32B t0": "#ff9f40"}
LAB = {"gpt-oss-20b": "gpt-oss-20b (reasoning effort medium)", "Qwen3-32B t1": "Qwen3-32B thinking on (t1)", "Qwen3-32B t0": "Qwen3-32B thinking off (t0)"}
ARM = {"headline-chat": ("-", "o", "headline-chat: private chat"), "headline-tacit": ("--", "s", "headline-tacit: no chat")}
fig, axes = plt.subplots(1, 5, figsize=(22, 5.2), constrained_layout=True)
for ax, (m, title, direc) in zip(axes, M):
    for model in COL:
        for arm, (ls, mk, al) in ARM.items():
            s = c[(c.model == model) & (c.arm == arm)].sort_values("penalty_point")
            off = {"gpt-oss-20b": -0.12, "Qwen3-32B t1": 0.0, "Qwen3-32B t0": 0.12}[model] + (0.04 if arm == "headline-chat" else -0.04)
            x = s.penalty_point + off
            ax.errorbar(x, s[m], yerr=[s[m] - s[m + "_lo"], s[m + "_hi"] - s[m]], color=COL[model], ls=ls, marker=mk, ms=5, capsize=2, lw=1.6,
                        label=f"{LAB[model]}; {al}")
    ax.set_title(f"{title}\n{direc}", fontsize=10)
    ax.set_xticks([1, 3, 4, 5]); ax.set_xticklabels(["p1\nfine 100", "p3\nfine 500", "p4\nfine 1000", "p5\nfine 2000"], fontsize=9)
    ax.set_xlabel("Penalty point (regulator's fine per firm)", fontsize=9)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("Cell mean over 20 games, 95% bootstrap CI", fontsize=9)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, -0.16))
fig.suptitle("Five metrics by penalty point: no chat vs private chat, gpt-oss-20b and Qwen3-32B (neutral payoff table, 20 games per point)", fontsize=12)
fig.savefig(sys.argv[2], dpi=130, bbox_inches="tight")
print("ok")
