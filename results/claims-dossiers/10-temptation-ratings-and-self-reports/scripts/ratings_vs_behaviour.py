"""H1/H2: do Claude's outcome-blind prompt ratings (temptation, conflict) track the five collusion metrics, on gpt-oss-20b
and on Qwen3-32B? Three levels of aggregation (game, (arm, penalty, wording) prompt, (arm, penalty) cell), Spearman and
Pearson, 95% cluster-bootstrap CIs (clusters = cells), Monte-Carlo permutation p at cell level (the independent unit),
Holm within each (dataset) family of 10 tests (5 metrics x 2 ratings). Also: matched cells across models, design-adjusted
(partial) correlations, the variance ceiling, leave-one-cell-out ranges, naive design screens.
Run: python -X utf8 ratings_vs_behaviour.py  (writes CSVs to ../)"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(C.SEED)

oss = C.prep(C.load_oss())
qn = C.prep(C.load_qwen("neutral"))
qa = C.prep(C.load_qwen("anchored"))
DATA = {
    "gpt-oss-20b (medium effort), neutral run": oss[oss.claude_temptation.notna()],
    "Qwen3-32B thinking on, neutral run": qn[qn.thinking == "on"],
    "Qwen3-32B thinking off, neutral run": qn[qn.thinking == "off"],
    "Qwen3-32B thinking on, anchored run": qa[qa.thinking == "on"],
    "Qwen3-32B thinking off, anchored run": qa[qa.thinking == "off"],
}
for k, d in DATA.items():
    assert d.claude_temptation.notna().all(), k

# ---------- 1. main correlation table
rows = []
for ds, d in DATA.items():
    for level in ("game", "prompt", "cell"):
        a = C.aggregate(d, level)
        for r in C.RCOLS:
            for m in C.MCOLS:
                res = C.boot_corr(a[r], a[m], a.cluster, rng)
                ps = pp = np.nan
                if level == "cell":
                    ps, pp = C.perm_p(a[r], a[m], rng)
                rows.append(dict(dataset=ds, level=level, rating=r, metric=m, perm_p_spearman=ps, perm_p_pearson=pp,
                                 distinct_rating_values=a[r].round(3).nunique(), **res))
T = pd.DataFrame(rows)
for ds in DATA:
    for col in ("perm_p_spearman", "perm_p_pearson"):
        sel = (T.dataset == ds) & (T.level == "cell")
        T.loc[sel, col.replace("perm_p", "holm")] = C.holm(T.loc[sel, col].to_numpy())
T["mde_spearman"] = 2.8 * T.sp_se
T["mde_pearson"] = 2.8 * T.pe_se
T.round(4).to_csv(OUT / "rating_correlations.csv", index=False, lineterminator="\n")

# ---------- 2. matched cells: gpt-oss vs Qwen thinking on (neutral) on the (arm, penalty) cells both models played
common = sorted(set(DATA["gpt-oss-20b (medium effort), neutral run"].cell) & set(DATA["Qwen3-32B thinking on, neutral run"].cell))
rows = []
for ds in ["gpt-oss-20b (medium effort), neutral run", "Qwen3-32B thinking on, neutral run", "Qwen3-32B thinking off, neutral run"]:
    d = DATA[ds]; d = d[d.cell.isin(common)]
    for level in ("prompt", "cell"):
        a = C.aggregate(d, level)
        for r in C.RCOLS:
            for m in C.MCOLS:
                res = C.boot_corr(a[r], a[m], a.cluster, rng)
                rows.append(dict(dataset=ds, level=level, rating=r, metric=m, cells=";".join(common), **res))
pd.DataFrame(rows).round(4).to_csv(OUT / "matched_cells_correlations.csv", index=False, lineterminator="\n")

# ---------- 3. design-adjusted (partial) correlation at prompt level: residualise rating and metric on
# communication + penalty point + number of firms (the design levers a rater could read off directly)
rows = []
for ds, d in DATA.items():
    a = C.aggregate(d, "prompt")
    design = [c for c in ("communication", "penalty_point", "firms") if a[c].nunique() > 1]
    for r in C.RCOLS:
        for m in C.MCOLS:
            sub = a.dropna(subset=[m])
            rr = C.residualise(sub, r, design); mm = C.residualise(sub, m, design)
            res = C.boot_corr(rr, mm, sub.cluster, rng)
            rows.append(dict(dataset=ds, level="prompt", rating=r, metric=m, adjusted_for="+".join(design), **res))
pd.DataFrame(rows).round(4).to_csv(OUT / "design_adjusted_correlations.csv", index=False, lineterminator="\n")

# ---------- 4. variance ceiling: share of game-level variance explained by prompt text and by cell
rows = []
for ds, d in DATA.items():
    for m in C.MCOLS:
        rows.append(dict(dataset=ds, metric=m, n_games=int(d[m].notna().sum()), eta2_prompt=C.eta2(d, m, "prompt"),
                         eta2_cell=C.eta2(d, m, "cell"), ceiling_r_game=np.sqrt(C.eta2(d, m, "prompt"))))
pd.DataFrame(rows).round(4).to_csv(OUT / "variance_ceiling.csv", index=False, lineterminator="\n")

# ---------- 5. leave-one-cell-out range (cell level) and naive design screens
rows = []
for ds, d in DATA.items():
    a = C.aggregate(d, "cell")
    a["chat"] = (a.communication != "tacit").astype(float)
    a["neg_penalty"] = -a.penalty_point.astype(float)
    for m in C.MCOLS:
        loo = [C.corr_pair(a.drop(i).claude_temptation, a.drop(i)[m])[0] for i in a.index]
        s, p, n = C.corr_pair(a.claude_temptation, a[m])
        sc, pc, _ = C.corr_pair(a.chat, a[m]) if a.chat.nunique() > 1 else (np.nan, np.nan, 0)
        sn, pn, _ = C.corr_pair(a.neg_penalty, a[m]) if a.neg_penalty.nunique() > 1 else (np.nan, np.nan, 0)
        rows.append(dict(dataset=ds, metric=m, n_cells=n, spearman_temptation=s, pearson_temptation=p,
                         loo_spearman_min=min(loo), loo_spearman_max=max(loo),
                         spearman_chat_indicator=sc, pearson_chat_indicator=pc,
                         spearman_minus_penalty=sn, pearson_minus_penalty=pn))
pd.DataFrame(rows).round(4).to_csv(OUT / "cell_robustness.csv", index=False, lineterminator="\n")

# ---------- 6. sensitivity: duplicate-text replicate arms merged into their twin, distinct-text level (gpt-oss)
o2 = C.prep(C.load_oss(), drop_hrep=False)
o2 = o2[o2.claude_temptation.notna()]
rows = []
for level in ("text", "cell"):
    a = C.aggregate(o2, level)
    for r in C.RCOLS:
        for m in C.MCOLS:
            rows.append(dict(dataset="gpt-oss-20b, replicate arms merged", level=level, rating=r, metric=m,
                             **C.boot_corr(a[r], a[m], a.cluster, rng)))
pd.DataFrame(rows).round(4).to_csv(OUT / "sensitivity_merged_replicates.csv", index=False, lineterminator="\n")

# ---------- 7. the point tables used for the scatter plots
for ds, d in DATA.items():
    tag = ds.split(",")[0].split(" ")[0].replace("Qwen3-32B", "qwen") + ("_t1" if "on" in ds.split(",")[0] else "_t0" if "off" in ds else "") + ("_anch" if "anchored" in ds else "")
    tag = "oss" if ds.startswith("gpt-oss") else tag
    for level in ("game", "prompt", "cell"):
        a = C.aggregate(d, level)
        keep = [c for c in ["row_id", "prompt", "cell", "arm", "penalty_point", "communication", "firms", "wording", "seed",
                            "n_games"] + C.RCOLS + C.MCOLS if c in a.columns]
        a[keep].round(4).to_csv(OUT / "points" / f"{tag}_{level}.csv", index=False, lineterminator="\n") if (OUT / "points").exists() else None

print("rows per dataset:", {k: len(v) for k, v in DATA.items()})
print("common cells:", len(common))
print(T[(T.level != "game") & (T.rating == "claude_temptation") & (T.metric.isin(["price_index", "competitive_share", "matching_share"]))]
      [["dataset", "level", "metric", "n", "spearman", "sp_lo", "sp_hi", "pearson", "pe_lo", "pe_hi"]].round(2).to_string())
