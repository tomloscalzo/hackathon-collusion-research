#!/usr/bin/env python3
"""Forest plot for the ethics-rule report, drawn only from the committed ethics_rule_contrasts.csv (analyze.py calls it after writing it).
Panel titles and legend read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv).
usage: python -X utf8 ethics_figure.py [--out .]"""
import argparse, os, sys, textwrap
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=HERE); A, _ = ap.parse_known_args()
R = pd.read_csv(os.path.join(A.out, "ethics_rule_contrasts.csv"))
SPEC = [("m-asym", "headline-chat", "1 of 2"), ("n3-ethics", "n3-group", "1 of 3")]
meas = ["price_index", "comp_share", "competitive_share | bound firm - control firms", "competitive_share | unbound others - control firms", "competitive_share | bound - unbound (same game)"]
N = R[(R.run == "neutral") & R.measure.isin(meas)]
names = ["Price index, market\n(arm - control)", "Competitive share, market\n(arm - control)", "Competitive share,\nbound firm - control firms", "Competitive share,\nunbound firm(s) - control firms", "Competitive share,\nbound - unbound (same game)"]
W = lambda t: textwrap.fill(t, 52, break_on_hyphens=False, break_long_words=False)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
drawn = []
for ax, (arm, carm, lab) in zip(axes, SPEC):
    for i, m in enumerate(meas):
        for mode, off, col in (("off", -.15, "#1f77b4"), ("on", .15, "#d95f02")):
            s = N[(N.arm == arm) & (N.measure == m) & (N["mode"] == mode)].iloc[0]
            l1, = ax.plot([s.ci_lo, s.ci_hi], [i + off] * 2, color=col, lw=2); l2, = ax.plot(s["diff"], i + off, "o", color=col)
            drawn.append((l1, l2, s))
    ax.axvline(0, color="#444", ls="--", lw=1)
    ax.set_title(W("%s (rule on %s firms)" % (arm_labels.label(arm), lab)) + "\n" + W("control = " + arm_labels.label(carm)), fontsize=8.5)
    ax.set_yticks(range(5)); ax.set_yticklabels(names); ax.set_ylim(4.6, -.6); ax.grid(axis="x", alpha=.25)
    ax.set_xlabel("effect = rule arm minus control (index or share units)\ndot = mean, bar = 95% bootstrap CI over 20 pairs", fontsize=8)
axes[0].plot([], [], "o-", color="#1f77b4", label=arm_labels.label("t0")); axes[0].plot([], [], "o-", color="#d95f02", label=arm_labels.label("t1")); fig.legend(loc="lower center", ncol=2, fontsize=8)
fig.suptitle("Ethics rule on one firm, neutral run, penalty point p3: rule arm minus matched control, paired on 20 (wording, seed) pairs.\nRows 1-2 = whole market; rows 3-5 = per firm (competitive share). Negative price index = prices lowered; positive competitive share = more undercutting. Dashed line = no effect.", fontsize=8.5)
fig.tight_layout(rect=(0, 0.05, 1, 0.92))
# check: every plotted mean and CI equals the committed CSV value (no number changes)
assert len(drawn) == 20
for l1, l2, s in drawn:
    assert list(np.asarray(l1.get_xdata(), float)) == [s.ci_lo, s.ci_hi] and float(np.asarray(l2.get_xdata(), float)[0]) == s["diff"]
fig.savefig(os.path.join(A.out, "ethics_rule.png"), dpi=130)
print("ethics_rule.png written; plotted values equal ethics_rule_contrasts.csv")
