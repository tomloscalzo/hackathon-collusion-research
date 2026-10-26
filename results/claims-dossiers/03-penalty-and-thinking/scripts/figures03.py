"""Dossier 03 figures: (1) penalty dose-response vs theory, (2) strategic signatures.
Reads cells-level game rows from run.csv (via common03) and strategic_by_group.csv."""
import os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common03 import *

COL = {"qwen_t1": "#2a78d6", "qwen_t0": "#eb6834", "oss_t1": "#1baf7a"}
MK = {"qwen_t1": "o", "qwen_t0": "s", "oss_t1": "^"}
NAME = {"qwen_t1": "Qwen3-32B, thinking on (t1)", "qwen_t0": "Qwen3-32B, thinking off (t0)",
        "oss_t1": "gpt-oss-20b, reasoning effort medium"}
q = headline("qwen"); o = headline("oss")
h = pd.concat([q, o]); h["grp"] = h.model + "_" + h["mode"]

fig, axes = plt.subplots(2, 2, figsize=(10, 7.6), constrained_layout=True, sharex=True)
for r, (m, lab, th) in enumerate([("price_index", "Price index ((price - 1) / 2)", THETA),
                                  ("profit_gain_index", "Profit gain index", THEORY_GAIN)]):
    for c, comm in enumerate(["tacit", "chat"]):
        ax = axes[r, c]
        pts = [1, 3, 4, 5]
        ax.plot(pts, [th[p] for p in pts], ls="--", color="#777777", lw=2, label="theory: sustainable collusive level")
        for g in ["qwen_t1", "qwen_t0", "oss_t1"]:
            s = h[(h.grp == g) & (h.comm == comm)]
            xs, ys, lo, hi = [], [], [], []
            for p, gg in s.groupby("penalty_point"):
                v = gg[m].dropna().values
                bm = v[RNG.integers(0, len(v), (4000, len(v)))].mean(1)
                xs.append(p); ys.append(v.mean()); lo.append(v.mean() - np.percentile(bm, 2.5)); hi.append(np.percentile(bm, 97.5) - v.mean())
            off = {"qwen_t1": -0.08, "qwen_t0": 0.0, "oss_t1": 0.08}[g]
            ax.errorbar(np.array(xs) + off, ys, yerr=[lo, hi], color=COL[g], marker=MK[g], ms=8, lw=2, capsize=3, label=NAME[g])
        ax.set_ylim(-0.03, 1.03); ax.set_xticks(pts); ax.grid(axis="y", color="#e6e6e6")
        ax.set_title(f"{'No chat (tacit)' if comm == 'tacit' else 'Private chat'}: {lab}", fontsize=11)
        if c == 0:
            ax.set_ylabel(lab + "\n0 = competitive, 1 = monopoly", fontsize=10)
        if r == 1:
            ax.set_xlabel("Penalty point (1 = light fine 100 ... 5 = heavy fine 2000)", fontsize=10)
axes[0, 0].legend(fontsize=9, loc="lower left")
fig.suptitle("Penalty dose-response vs theory, neutral run, headline arms (20 games per point; 95% bootstrap CI over games)", fontsize=11)
fig.savefig(f"{OUT}/fig_penalty_curve.png", dpi=150)

# figure 2: strategic signatures, pooled over the five cells both models played
s = pd.read_csv(f"{OUT}/strategic_by_group.csv")
s = s[s.comm == "chat+tacit (5 common cells)"].set_index("grp")
b = pd.read_csv(f"{OUT}/strategic_baselines_pooled.csv").set_index("grp")
items = [("punish_rate", "Cuts own\nquote after\nbeing undercut"), ("cut_baseline", "Cuts own\nquote when\nNOT undercut"),
         ("retaliate_rate", "Undercuts the\nrival back after\nbeing undercut"), ("reward_rate", "Raises own\nquote after\nrival raised"),
         ("return_rate", "Back to pre-cut\nquote within 3\nrounds of a\npunishing cut"), ("hold_share", "Holds own\nquote\nunchanged"),
         ("on_printed_share", "Quote is a\nprinted\nexample price")]
fig, ax = plt.subplots(figsize=(13, 5.8), constrained_layout=True)
x = np.arange(len(items)); w = 0.26
for k, g in enumerate(["qwen_t1", "qwen_t0", "oss_t1"]):
    vals = [s.loc[g, it] for it, _ in items]
    ax.bar(x + (k - 1) * w, vals, w - 0.02, color=COL[g], label=NAME[g])
    for xi, v in zip(x + (k - 1) * w, vals):
        ax.text(xi, v + 0.01, f"{v:.2f}", ha="center", fontsize=8, color="#333333")
ax.set_xticks(x); ax.set_xticklabels([l for _, l in items], fontsize=9)
ax.set_ylabel("Share of firm-rounds (0 to 1)", fontsize=10); ax.set_ylim(0, 1.05)
ax.grid(axis="y", color="#e6e6e6"); ax.legend(fontsize=9, loc="upper left")
ax.set_title("Strategic vs outcome signatures, firm-round rates pooled over chat p1/p3/p5 and no-chat p1/p5 (neutral run)\n"
             "n = 100 games per series (5 cells x 20 games); firm-rounds: Qwen on %d, Qwen off %d, gpt-oss %d" % (s.loc["qwen_t1","n_firm_rounds"], s.loc["qwen_t0","n_firm_rounds"], s.loc["oss_t1","n_firm_rounds"]), fontsize=11)
fig.savefig(f"{OUT}/fig_strategic_signatures.png", dpi=150)
print("ok")
