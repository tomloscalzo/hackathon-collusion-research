"""Dossier 03, part 3: specificity baselines for the strategic signatures, from
firmrounds_rebuilt.csv.gz (written by strategic_signatures.py).
  retaliate_baseline   P(quote below rival's previous quote | rival did NOT undercut me) -- unprovoked undercutting
  retaliate_gap        retaliate_rate - retaliate_baseline
  return_baseline      after an UNPROVOKED cut, share returning to >= the pre-cut quote within 3 rounds
  return_gap           return_rate (after a punishing cut) - return_baseline
Per (model-mode, pair), pooled over the five cells both models played (chat p1/p3/p5, tacit p1/p5).
Writes strategic_baselines.csv (pair level) and strategic_baseline_contrasts.csv."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common03 import *
TOL = 0.005
fr = pd.read_csv(f"{OUT}/firmrounds_rebuilt.csv.gz")
fr = fr[~fr.arm.str.startswith("hrep-")]
fr["grp"] = fr.model + "_" + fr["mode"]
COMMON = {("chat", 1), ("chat", 3), ("chat", 5), ("tacit", 1), ("tacit", 5)}
fr = fr[[(c, p) in COMMON for c, p in zip(fr.comm, fr.penalty_point)]].copy()
fr["below_rival"] = (fr.quote < fr.riv_prev - TOL).astype(float)
fr.loc[fr.riv_prev.isna(), "below_rival"] = np.nan
# return after any cut, labelled provoked / unprovoked
fr["ret_any"] = np.nan
for _, g in fr.groupby(["model", "trial_id", "seat"]):
    q = g.quote.values; op = g.own_prev.values; cut = g.cut.values == 1; idx = g.index.values
    for i in np.where(cut)[0]:
        if i + 1 < len(q):
            fr.loc[idx[i], "ret_any"] = float((q[i + 1:i + 4] >= op[i] - TOL).any())

def r(g):
    s = g[g.own_prev.notna()]
    u = s.rival_undercut == 1; nu = s.rival_undercut == 0
    def m(x):
        x = x.dropna(); return x.mean() if len(x) else np.nan
    return pd.Series(dict(
        retaliate_rate=m(s.below_rival[u]), retaliate_baseline=m(s.below_rival[nu]),
        return_rate=m(s.ret_any[u & (s.cut == 1)]), return_baseline=m(s.ret_any[nu & (s.cut == 1)]),
        n_unprovoked_cuts=int((nu & (s.cut == 1)).sum())))

pp = fr.groupby(["grp", "pair"]).apply(r, include_groups=False).reset_index()
pp["retaliate_gap"] = pp.retaliate_rate - pp.retaliate_baseline
pp["return_gap"] = pp.return_rate - pp.return_baseline
pp.to_csv(f"{OUT}/strategic_baselines.csv", index=False)
pooled = fr.groupby("grp").apply(r, include_groups=False)
print(pooled.round(3).to_string())
rows = []
for m in ["retaliate_gap", "return_gap", "retaliate_baseline", "return_baseline"]:
    w = pp.pivot(index="pair", columns="grp", values=m)
    for g in ["oss_t1", "qwen_t1", "qwen_t0"]:
        if m.endswith("gap"):
            rows.append(summarise(w[g].dropna().values, contrast=f"{g}: {m} vs 0", metric=m, family="baseline gaps vs 0", mean=w[g].mean()))
    for a, b in [("qwen_t1", "qwen_t0"), ("oss_t1", "qwen_t1")]:
        rows.append(summarise((w[a] - w[b]).dropna().values, contrast=f"{a} minus {b}", metric=m, family="baseline gap contrasts", mean=np.nan))
out = holm(pd.DataFrame(rows), by=["family"])
out.to_csv(f"{OUT}/strategic_baseline_contrasts.csv", index=False)
print(out[["contrast", "metric", "n_pairs", "effect", "ci_lo", "ci_hi", "p_holm"]].round(3).to_string())
pooled.reset_index().to_csv(f"{OUT}/strategic_baselines_pooled.csv", index=False)
