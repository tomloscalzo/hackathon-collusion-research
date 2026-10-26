#!/usr/bin/env python3
"""Two figures from data/contrasts.csv and data/game_metrics.csv. Usage: python -X utf8 make_figures.py DATA_DIR OUT_DIR"""
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "analysis_style"))
import arm_labels  # shared glossary: "slug: short label" on every arm tick

data, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = list(csv.DictReader(open(data / "contrasts.csv", encoding="utf8")))
LAB = {"prime_vs_placebo": "Moral prime vs placebo", "primeb_vs_placebo": "Moral prime B vs placebo",
       "placebo_vs_headline": "Placebo vs headline chat (check)", "threat0_vs_headline": "Threat-0 vs headline chat",
       "threat0_vs_a": "Threat-0 vs threat-A (permission)", "threat0_vs_b": "Threat-0 vs threat-B (permission)"}
# treatment and reference arm of each contrast, for "slug: short label" tick text
PAIR = {"prime_vs_placebo": ("moral-prime", "moral-placebo"), "primeb_vs_placebo": ("moral-prime-b", "moral-placebo"),
        "placebo_vs_headline": ("moral-placebo", "headline-chat"), "threat0_vs_headline": ("d-cot-monitor-0", "headline-chat"),
        "threat0_vs_a": ("d-cot-monitor-0", "d-cot-monitor-a"), "threat0_vs_b": ("d-cot-monitor-0", "d-cot-monitor-b")}


def clab(c, n):
    a, b = PAIR[c]
    return f"{LAB[c]} (n={n})\n" + textwrap.fill(arm_labels.label(a), 44, break_on_hyphens=False) + "\nminus " + textwrap.fill(arm_labels.label(b), 40, break_on_hyphens=False)


from matplotlib.lines import Line2D
from matplotlib.patches import Patch
fig, axes = plt.subplots(1, 2, figsize=(15, 7.2), sharex=True)
plotted = []
for ax, mode, title in zip(axes, ["off", "on"], ["Thinking off (t0)", "Thinking on (t1)"]):
    rs = [r for r in rows if r["metric"] == "price_index" and r["mode"] == mode]
    for i, r in enumerate(rs):
        d, lo, hi = float(r["diff"]), float(r["ci_lo"]), float(r["ci_hi"])
        ax.plot([lo, hi], [i, i], color="#1f4e79", lw=2)
        ax.plot(d, i, "o", color="#1f4e79")
        plotted.append((r["contrast"], mode, d, lo, hi))
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([clab(r["contrast"], r["n_pairs"]) for r in rs], fontsize=7.5)
    ax.invert_yaxis()
    ax.axvline(0, color="grey", lw=1)
    ax.axvspan(-0.2, 0.2, color="grey", alpha=0.12)
    ax.set_title(title)
    ax.set_xlabel("Change in price index (treatment minus reference)\nnegative = treatment lowered prices", fontsize=8)
fig.suptitle("Wave A, Qwen3-32B, private chat, penalty point 1, neutral payoff table: paired change in game-mean price index, (market price - 1)/2", fontsize=10)
fig.legend(handles=[Line2D([0], [0], marker="o", color="#1f4e79", lw=2, label="mean paired difference with 95% bootstrap CI over n (wording, seed) pairs"),
                    Line2D([0], [0], color="grey", lw=1, label="zero = no effect"),
                    Patch(color="grey", alpha=0.12, label="grey band = minimum detectable effect, about +/-0.2 (an effect inside the band cannot be ruled out)")],
           loc="lower center", ncol=1, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, 0.1, 1, 0.95))
fig.savefig(out / "fig1_price_index_effects.png", dpi=130, bbox_inches="tight")

gm = list(csv.DictReader(open(data / "game_metrics.csv", encoding="utf8")))
arms = ["headline-chat", "moral-placebo", "moral-prime", "moral-prime-b", "d-cot-monitor-0", "d-cot-monitor-a", "d-cot-monitor-b"]
fig, axes = plt.subplots(1, 2, figsize=(15, 7.4), sharey=True)
plotted2 = []
for ax, mode, title in zip(axes, ["off", "on"], ["Thinking off (t0)", "Thinking on (t1)"]):
    labs = []
    for i, arm in enumerate(arms):
        v = [float(g["price_index"]) for g in gm if g["arm"] == arm and g["thinking"] == mode and g["price_index"]]
        labs.append(textwrap.fill(arm_labels.label(arm), 30, break_on_hyphens=False) + (f" (n={len(v)})" if v else " (not run)"))
        plotted2.append((arm, mode, sorted(v)))
        if not v:
            continue
        for j, x in enumerate(sorted(v)):
            ax.plot(i + (j - len(v) / 2) * 0.012, x, "o", color="#9bb7d4", ms=3)
        ax.plot([i - 0.3, i + 0.3], [sum(v) / len(v)] * 2, color="#1f4e79", lw=3)
    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels(labs, rotation=45, ha="right", fontsize=7.5)
    ax.set_xlabel("Arm (definitions in the table under the figure); n = games plotted", fontsize=9)
    ax.set_title(title)
axes[0].set_ylabel("Game-mean price index = (market price - 1)/2\n0 = competitive floor (1.00), 1 = monopoly (3.00)")
fig.suptitle("Wave A, Qwen3-32B, private chat, penalty point 1, neutral payoff table: price index of every game, by arm", fontsize=10)
fig.legend(handles=[Line2D([0], [0], marker="o", color="#9bb7d4", lw=0, ms=4, label="one game (one (wording, seed) pair)"),
                    Line2D([0], [0], color="#1f4e79", lw=3, label="arm mean over its games")], loc="lower center", ncol=2, fontsize=8, frameon=False)
fig.tight_layout(rect=(0, 0.06, 1, 0.95))
fig.savefig(out / "fig2_price_index_by_arm.png", dpi=130)

# check (c): the plotted values are exactly the committed CSV values
chk = {(r["contrast"], r["mode"]): r for r in csv.DictReader(open(data / "contrasts.csv", encoding="utf8")) if r["metric"] == "price_index"}
for c, mode, d, lo, hi in plotted:
    r = chk[(c, mode)]
    assert (d, lo, hi) == (float(r["diff"]), float(r["ci_lo"]), float(r["ci_hi"]))
gm2 = list(csv.DictReader(open(data / "game_metrics.csv", encoding="utf8")))
for arm, mode, v in plotted2:
    assert v == sorted(float(g["price_index"]) for g in gm2 if g["arm"] == arm and g["thinking"] == mode and g["price_index"])
print("figures written; plotted values equal the CSVs:", len(plotted), "contrast points,", sum(len(v) for _, _, v in plotted2), "games")
