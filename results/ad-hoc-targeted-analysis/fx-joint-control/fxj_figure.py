#!/usr/bin/env python3
"""Difference heat map for the fx-joint control report: rows = paired contrasts, columns = the five standard metrics (each its own panel,
fixed scale, centred at 0; red = more collusive in the first-named cell, green = more competitive). Colours from collusion_colors.py.
Usage: python -X utf8 fxj_figure.py --repo <repo root> --dir <report folder>"""
import argparse, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--dir", required=True)
a = ap.parse_args()
sys.path.insert(0, a.repo + "/tools/analysis_style")
import collusion_colors as cc

M = [("avg_abs_spread", "Average absolute spread", 2.0, "quote units"), ("price_index", "Price index", 1.0, "index units"),
     ("profit_gain_index", "Profit gain index", 1.0, "index units"), ("competitive_share", "Competitive share (U16)", 1.0, "share"),
     ("matching_share", "Matching share", 1.0, "share")]
P = pd.read_csv(a.dir + "/paired_contrasts.csv")
P = P[P.group.isin(["A", "B"])].reset_index(drop=True)
LAB = {"Q fx-ctl-joint p3": "Qwen joint+formula", "Q ctl-32b-joint p3 (primed)": "Qwen joint+examples", "Q fx-chat-p1": "Qwen formula chat p1",
       "Q headline-chat p3": "Qwen examples chat p3", "O fx-ctl-joint p3": "gpt-oss joint+formula", "O ctl-32b-joint p3 (primed)": "gpt-oss joint+examples",
       "O fx-chat-p1": "gpt-oss formula chat p1", "O headline-chat p3": "gpt-oss examples chat p3", "O headline-chat p1": "gpt-oss examples chat p1",
       "O nx-chat-p1": "gpt-oss no-numbers chat p1", "O fx-tacit-p1": "gpt-oss formula tacit p1", "O nx-tacit-p1": "gpt-oss no-numbers tacit p1",
       "O headline-tacit p1": "gpt-oss examples tacit p1", "O fx-chat-p5": "gpt-oss formula chat p5", "O headline-chat p5": "gpt-oss examples chat p5"}
import arm_labels  # shared slug glossary: row ticks read "slug: short label" (owner rule for maps with more than ~10 rows)


def slug_label(cell):
    """'Q fx-ctl-joint p3 (primed)' -> 'Qwen fx-ctl-joint p3: told to maximise joint profit; ...' (model, slug and point kept)."""
    model, slug, *rest = cell.split()
    pt = " ".join(x for x in rest if not x.startswith("("))
    ex = " (example prices)" if slug.startswith(("headline-", "ctl-32b-")) else ""   # the neutral payoff table, "examples" in the report
    return "%s %s%s: %s%s" % ({"Q": "Qwen", "O": "gpt-oss"}[model], slug, (" " + pt) if pt and pt not in slug else "", arm_labels.glossary()[slug]["short_label"], ex)


rows = ["%s\nminus %s  (n=%d)" % (slug_label(t), slug_label(r), n) for t, r, n in zip(P.treatment, P.reference, P.n)]
assert all(LAB[t] and LAB[r] for t, r in zip(P.treatment, P.reference))   # every row is a known cell
fig, axes = plt.subplots(1, 5, figsize=(24, 0.85 * len(rows) + 2.8), sharey=True)
fig.subplots_adjust(left=0.36, right=0.99, top=0.85, bottom=0.15, wspace=0.08)
for k, (ax, (col, lab, R, unit)) in enumerate(zip(axes, M)):
    v = P[col + "_d"].to_numpy(float)[:, None]
    im = ax.imshow(v, cmap=cc.cmap_for(col, diff=True), norm=TwoSlopeNorm(0, -R, R), aspect="auto")
    for i, x in enumerate(v[:, 0]):
        if np.isnan(x):
            continue
        lo, hi = P.loc[i, col + "_lo"], P.loc[i, col + "_hi"]
        ax.text(0, i, "%+.2f\n[%+.2f, %+.2f]" % (x, lo, hi), ha="center", va="center", fontsize=10,
                color=cc.text_color(x if cc.direction(col) == cc.COLLUSION else -x, -R, R))
    ax.set_xticks([0]); ax.set_xticklabels([lab], fontsize=11); ax.set_yticks(range(len(rows)))
    if k == 0:
        ax.set_yticklabels(rows, fontsize=9.5)
    for y in np.where(P.group.ne(P.group.shift()).to_numpy())[0][1:]:
        ax.axhline(y - 0.5, color="black", lw=2)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.03, fraction=0.05, ticks=[-R / 2, 0, R / 2])
    cb.set_label(cc.cbar_label(unit, metric=col, diff=True).replace(" / ", " /" + chr(10)), fontsize=9)
    ax.xaxis.tick_top()
fig.suptitle("Paired differences (first cell minus second), five standard metrics, thinking on, mean over (wording, seed) pairs [95% bootstrap CI]\n"
             "Top block: the joint-profit instruction under the formula payoff block (Qwen3-32B, gpt-oss-20b). Bottom block: corrected gpt-oss formula / no-numbers arms vs the example-price headline cells",
             fontsize=12)
# check: every plotted cell value and printed CI equals the committed paired_contrasts.csv (no number changes)
ref = pd.read_csv(a.dir + "/paired_contrasts.csv"); ref = ref[ref.group.isin(["A", "B"])].reset_index(drop=True)
for ax, (col, lab, R, unit) in zip(axes, M):
    img = ax.get_images()[0].get_array()
    assert np.array_equal(np.asarray(img, float)[:, 0], ref[col + "_d"].to_numpy(float), equal_nan=True)
    txt = [t.get_text() for t in ax.texts]
    exp = ["%+.2f\n[%+.2f, %+.2f]" % (x, lo, hi) for x, lo, hi in zip(ref[col + "_d"], ref[col + "_lo"], ref[col + "_hi"]) if not np.isnan(x)]
    assert txt == exp
fig.savefig(a.dir + "/fxj_fig1_difference_map.png", dpi=110)
print("ok")
