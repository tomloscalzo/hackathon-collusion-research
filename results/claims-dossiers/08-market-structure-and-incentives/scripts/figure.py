"""Dossier 08 figure: forest plot of the paired price-index differences (arm minus control, 95% bootstrap CI over (wording, seed) pairs)
for the dossier's 8 contrasts, gpt-oss-20b (reasoning medium) vs Qwen3-32B thinking on and off. Usage: python figure.py <contrasts_csv> <out_png>"""
import sys
from pathlib import Path
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "analysis_style"))
import arm_labels  # noqa: E402

ORDER = [("n3-ethics", "headline-chat"), ("n3-ethics", "n3-group"), ("n3-cheater", "headline-chat"), ("n3-cheater", "n3-group"),
         ("m-inc-joint", "headline-chat"), ("n3-group", "headline-chat"), ("m-inc-target", "headline-chat"), ("m-asym", "headline-chat")]
SER = [("gpt-oss-20b", "medium", "gpt-oss-20b (reasoning medium)", "#1f4e79", "o"), ("Qwen3-32B", "t1", "Qwen3-32B thinking on", "#c55a11", "s"),
       ("Qwen3-32B", "t0", "Qwen3-32B thinking off", "#7f7f7f", "^")]


def short(slug):
    return "%s: %s" % (slug, arm_labels.label(slug).split(": ", 1)[-1])


r = pd.read_csv(sys.argv[1]); r = r[r.metric == "price_index"]
fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)
ylabels = []
for i, (a, c) in enumerate(ORDER):
    ylabels.append("%s\nminus %s" % (short(a), short(c)))
    for j, (m, md, lab, col, mk) in enumerate(SER):
        x = r[(r.model == m) & (r["mode"] == md) & (r.arm == a) & (r.control == c)]
        if x.empty:
            continue
        x = x.iloc[0]; y = i + (j - 1) * 0.25
        ax.errorbar(x["diff"], y, xerr=[[x["diff"] - x.lo], [x.hi - x["diff"]]], fmt=mk, color=col, capsize=3, ms=6,
                    label=lab if i == 0 else None)
        ax.text(x.hi + 0.01, y, "n=%d" % x.n_pairs, va="center", fontsize=9, color=col)
ax.axvline(0, color="black", lw=0.8)
ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(ylabels, fontsize=9); ax.invert_yaxis()
ax.set_xlabel("Paired difference in price index, arm minus control\n(price index = (market price - 1.00) / 2; negative = lower prices, more competitive)")
ax.set_xlim(-0.52, 0.36)
ax.set_title("Price-index effect of market-structure, ethics-rule and incentive arms\nneutral run, penalty point 3, private chat\n"
             "mean paired difference over (wording, seed) pairs with 95% bootstrap CI (n = pairs)", fontsize=10)
fig.legend(loc="outside lower center", ncol=3, fontsize=9, title="Model and mode")
fig.savefig(sys.argv[2], dpi=150)
