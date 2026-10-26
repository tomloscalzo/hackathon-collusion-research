"""Figures for the observer-ratings analysis.  usage: python figures.py CSV_DIR OUT_DIR STYLE_DIR

Forest charts use the shared helper tools/analysis_style/ci_forest.py (red / green by collusion direction,
hollow marker = CI crosses zero, dashed zero line). Writes forest_tables.json: the rows drawn in each chart,
so that report.py can print the matching legend (ci_forest.legend_md)."""
import json
import sys
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv, out, style = sys.argv[1:4]
sys.path.insert(0, style)
import arm_labels  # noqa: E402
import ci_forest  # noqa: E402

MLAB = {"avg_abs_spread": "Average absolute spread", "price_index": "Price index", "profit_gain_index": "Profit gain index",
        "competitive_share": "Competitive share (U16)", "matching_share": "Matching share", "harm_index": "Harm index"}
METS = list(MLAB)
DSHORT = {"gpt-oss-20b, thinking on (neutral)": "gpt-oss-20b, on",
          "Qwen3-32B, thinking on (neutral)": "Qwen3-32B, on", "Qwen3-32B, thinking off (neutral)": "Qwen3-32B, off",
          "Qwen3-32B, thinking on (anchored)": "Qwen3-32B anchored, on", "Qwen3-32B, thinking off (anchored)": "Qwen3-32B anchored, off"}
PRIMARY = ["gpt-oss-20b, thinking on (neutral)", "Qwen3-32B, thinking on (neutral)", "Qwen3-32B, thinking off (neutral)"]
ANCH = ["Qwen3-32B, thinking on (anchored)", "Qwen3-32B, thinking off (anchored)"]
STS = {"Spearman": "rho", "Pearson": "r"}
XL = "correlation, 95% CI"
plt.rcParams.update({"font.size": 10})
TABLES = {}

C = pd.read_csv(f"{csv}/correlations.csv")
W2 = pd.read_csv(f"{csv}/within_family_v2.csv")


def draw(name, rows, title, xlabel=XL):
    df = pd.DataFrame(rows)
    ci_forest.forest(df, f"{out}/{name}", title=title, xlabel=xlabel)
    TABLES[name] = df.to_dict("records")


def corr_rows(dsets, rating, levels, metrics=METS):
    rows = []
    for lv in levels:
        for d in dsets:
            for st in STS:
                for m in metrics:
                    if lv == "within family":
                        r = W2[(W2.dataset == d) & (W2.metric == m) & (W2.stat == st)]
                    else:
                        r = C[(C.dataset == d) & (C.level == lv) & (C.rating == rating) & (C.metric == m) & (C.stat == st)]
                    if r.empty:
                        continue
                    r = r.iloc[0]
                    rows.append(dict(label=f"{DSHORT[d]}, {lv}, {STS[st]}", metric=MLAB[m], estimate=r.est, lo=r.lo, hi=r.hi))
    return rows


draw("fig2_forest_temptation.png", corr_rows(PRIMARY, "claude_temptation", ["cell", "game"]),
     "Fig. 2. Observer temptation rating vs each metric (Table 1): correlation and 95% bootstrap CI, neutral payoff table")
draw("fig3_forest_conflict.png", corr_rows(PRIMARY, "claude_conflict", ["cell", "game"]),
     "Fig. 3. Observer conflict rating vs each metric (Table 2): correlation and 95% bootstrap CI, neutral payoff table")
draw("fig4_forest_within.png", corr_rows(PRIMARY, "claude_temptation", ["within cell", "within family"]),
     "Fig. 4. Within-design checks, temptation rating (Table 3): within cell and within family (controls and one-cell families excluded)")
draw("fig5_forest_within_conflict.png", corr_rows(PRIMARY, "claude_conflict", ["within cell"]),
     "Fig. 5. Within-cell check, conflict rating (Table 3b): correlation and 95% bootstrap CI")
draw("fig9_forest_anchored.png", corr_rows(ANCH, "claude_temptation", ["cell", "game", "within cell", "within family"],
                                           ["price_index", "competitive_share", "harm_index"]),
     "Fig. 9. Anchored payoff table (Qwen3-32B), temptation rating (Table 11): correlation and 95% bootstrap CI")

# per-family (Table 4)
F = pd.read_csv(f"{csv}/within_family.csv")
F = F[F.dataset.isin(PRIMARY) & F.metric.isin(["price_index", "competitive_share", "harm_index"])]
rows = [dict(label=f"{r.arm_family}: {DSHORT[r.dataset]}, {STS[r.stat]} ({int(r.n_cells)} cells)", metric=MLAB[r.metric],
             estimate=r.est, lo=r.lo, hi=r.hi, p=r.perm_p) for r in F.sort_values(["arm_family", "dataset", "stat"]).itertuples()]
draw("fig6_forest_families.png", rows,
     "Fig. 6. Temptation vs metric inside each arm family with at least 5 cells (Table 4); p = exact permutation p; CIs over 5-6 cells are unreliable")

# self-report (Table 9), Qwen conflict rows dropped (self-report near-constant)
S = pd.read_csv(f"{csv}/self_report.csv")
S = S[S.dataset.isin(PRIMARY) & ~((S.kind == "conflict") & S.dataset.str.startswith("Qwen"))]
PAIRS = {"self-report vs observer": "self-report vs observer rating", "self-report vs price_index": "self-report vs price index",
         "observer vs price_index": "observer vs price index", "self-report vs competitive_share": "self-report vs competitive share",
         "observer vs competitive_share": "observer vs competitive share"}
S = S[S.pair.isin(PAIRS)]
rows = [dict(label=f"{r.kind}: {DSHORT[r.dataset]}, {r.scope}, {STS[r.stat]}", metric=PAIRS[r.pair], estimate=r.est, lo=r.lo, hi=r.hi)
        for r in S.sort_values(["kind", "dataset", "scope", "stat"], ascending=[False, True, True, True]).itertuples()]
draw("fig7_forest_self_report.png", rows, "Fig. 7. Self-report and observer rating vs each other and vs behaviour (Table 9), D-set arms, game level")

# cross-model paired difference (Table 10)
X = pd.read_csv(f"{csv}/cross_model_diff.csv")
rows = [dict(label=f"{r.subset}, {STS[r.stat]}", metric=MLAB[r.metric], estimate=r["diff"], lo=r.lo, hi=r.hi) for _, r in X.iterrows()]
draw("fig8_forest_cross_model.png", rows,
     "Fig. 8. Observer rating minus Qwen3-32B same-cell behaviour as a predictor of gpt-oss-20b cell means (Table 10): paired difference in correlation",
     xlabel="observer minus Qwen, 95% CI")

# leverage / definitions (Table 5)
LV = pd.read_csv(f"{csv}/leverage_subsets.csv")
DSH = {"gpt-oss-20b, thinking on": "gpt-oss-20b, on", "Qwen3-32B, thinking on": "Qwen3-32B, on", "Qwen3-32B, thinking off": "Qwen3-32B, off"}
DEFS = {"competitive_share": "competitive share: U16 as reported", "u16_floor101": "competitive share: U16, floor <= 1.01",
        "strict_undercut": "competitive share: strict undercut only", "q_le_101": "competitive share: quotes <= 1.01",
        "near_floor_quote": "competitive share: quotes <= 1.05", "q_le_110": "competitive share: quotes <= 1.10"}
SUBS = {"all cells": "all cells", "without the two control arms": "no controls", "without controls and m-inc-joint": "no controls, no m-inc-joint",
        "without controls and no-chat cells": "no controls, no tacit cells"}
rows = [dict(label=f"{DSH[r.dataset]}, {SUBS[r.subset]}, {STS[r.stat]}", metric=DEFS[r.metric], estimate=r.est, lo=r.lo, hi=r.hi)
        for r in LV[LV.metric.isin(DEFS)].itertuples()]
draw("fig10_forest_leverage.png", rows,
     "Fig. 10. Temptation rating vs six competitive-share measures, cell level, with high-leverage cells removed (Table 5)",
     xlabel="correlation, 95% CI")

# LOO chart (Fig. 11)
fig, axs = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True, sharey=True)
for ax, (nm, tag) in zip(axs, [("gpt-oss-20b, thinking on", "gpt-oss-20b_on"), ("Qwen3-32B, thinking on", "Qwen3-32B_on"), ("Qwen3-32B, thinking off", "Qwen3-32B_off")]):
    c = pd.read_csv(f"{csv}/leverage_cells_{tag}_competitive_share.csv")
    full = np.corrcoef(c.claude_temptation, c.competitive_share)[0, 1]
    ax.scatter(c.cook_d, c.loo_pearson, s=40, color="#1f4e9c", label="one cell left out")
    ax.axhline(full, color="#d95f02", lw=1.2, ls="--", label=f"Pearson r with all cells ({full:+.2f})")
    xmax = c.cook_d.max()
    ax.set_xlim(-0.05 * xmax, 1.15 * xmax)
    for _, r in c.sort_values("cook_d", ascending=False).head(3).iterrows():
        right = r.cook_d > 0.6 * xmax
        ax.annotate(textwrap.fill(r.label, 24), (r.cook_d, r.loo_pearson), fontsize=9, xytext=(-6 if right else 6, 6),
                    textcoords="offset points", ha="right" if right else "left")
    ax.set_title(f"{nm}: {len(c)} cells", fontsize=10)
    ax.set_xlabel("Cook's distance of the cell (influence on the straight-line fit)", fontsize=9)
    ax.grid(alpha=.3)
axs[0].set_ylabel(textwrap.fill("Pearson r (temptation vs competitive share) with this one cell left out", 36), fontsize=9)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h[:1], l[:1], loc="outside lower center", fontsize=9, frameon=False)
for ax in axs:
    hh, ll = ax.get_legend_handles_labels()
    ax.legend(hh[1:], ll[1:], fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.13), frameon=False)
fig.suptitle("Fig. 11. Leave-one-cell-out Pearson r against each cell's influence (Cook's distance), competitive share (U16), neutral table", fontsize=11)
fig.savefig(f"{out}/fig11_loo_cook.png", dpi=130)
plt.close(fig)

# scatter: cell level (Fig. 1)
M = pd.read_csv(f"{csv}/cell_means.csv")
fams = sorted(M[M.dataset.isin(PRIMARY)].arm_family.unique())
cmap = plt.get_cmap("tab20")
fc = {f: cmap(i % 20) for i, f in enumerate(fams)}
fig, axs = plt.subplots(3, 3, figsize=(15, 13), constrained_layout=True, sharex=True)
for j, ds in enumerate(PRIMARY):
    c = M[M.dataset == ds]
    for i, (m, lab) in enumerate([("price_index", "Price index (0 = competitive 1.00, 1 = monopoly 3.00)"),
                                  ("harm_index", "Harm index: customer surplus loss / loss at monopoly (0-1)"),
                                  ("competitive_share", "Competitive share (U16): share of firm-rounds undercutting the rival, or both at 1.00")]):
        ax = axs[i, j]
        for f in fams:
            cc = c[c.arm_family == f]
            if len(cc):
                ax.scatter(cc.claude_temptation, cc[m], color=fc[f], s=55, alpha=.85, edgecolor="k", lw=.4, label=f)
        ax.grid(alpha=.3)
        if j == 0:
            ax.set_ylabel(textwrap.fill(lab, 34), fontsize=10)
        if i == 0:
            ax.set_title(f"{ds}: {len(c)} cells", fontsize=10)
        if i == 2:
            ax.set_xlabel("Observer temptation rating of the prompt (1-5; cell mean)", fontsize=10)
seen = {}
for a in axs.flat:
    hh, ll = a.get_legend_handles_labels()
    seen.update(dict(zip(ll, hh)))
fig.legend([seen[f] for f in fams], [arm_labels.label(f) for f in fams], loc="outside lower center", ncol=3, fontsize=9,
           title="Point colour = arm family")
fig.suptitle("Fig. 1. Observer temptation rating vs price, harm and competitive share: one point per cell (arm x communication x penalty point), neutral payoff table\n"
             "(each column has its own y-range)", fontsize=11)
fig.savefig(f"{out}/fig1_scatter_cells.png", dpi=120)
json.dump(TABLES, open(f"{out}/forest_tables.json", "w"), indent=0, default=float)
print("figures done")
