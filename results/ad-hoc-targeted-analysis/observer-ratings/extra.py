"""Review follow-ups computed from cell_means.csv (and the run tables for within-cell spread and the self-report prompts).

usage: python extra.py THIS_DIR OSS_RUN_CSV QWEN_RUN_CSV

(a) within-family correlation without the control family and single-cell families, family means
    recomputed inside every bootstrap resample (cells resampled within each family);
(b) per-family correlations with an exact permutation p (5 or 6 cells: all orderings);
(c) cross-model: paired bootstrap of (observer correlation, sign-aligned) minus (Qwen same-cell correlation);
(d) within-cell rating spread and the number of cells with a constant rating;
(e) distinct observer ratings among the D-set temptation prompts.
"""
import itertools
import sys
import numpy as np
import pandas as pd

D, oss_p, qw_p = sys.argv[1:4]
rng = np.random.default_rng(11)
B = 2000
METS = ["avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share", "harm_index"]
CELL = ["arm", "communication", "penalty_point"]
CM = pd.read_csv(f"{D}/cell_means.csv")


def rankdata(a):
    a = np.asarray(a); o = np.argsort(a, kind="mergesort"); sa = a[o]
    first = np.r_[True, sa[1:] != sa[:-1]]; gid = np.cumsum(first) - 1
    st = np.flatnonzero(first); en = np.r_[st[1:], len(a)]
    r = np.empty(len(a)); r[o] = ((st + en - 1) / 2.0 + 1)[gid]; return r


def corr(x, y, pearson):
    m = ~(np.isnan(x) | np.isnan(y)); x, y = x[m], y[m]
    if len(x) < 4 or x.std() == 0 or y.std() == 0:
        return np.nan
    if not pearson:
        x, y = rankdata(x), rankdata(y)
    return np.corrcoef(x, y)[0, 1]


def demean(c, cols):
    c = c.copy()
    for v in cols:
        c[v] = c[v] - c.groupby("arm_family")[v].transform("mean")
    return c


# (a) within family v2
import os
SKIP_A = os.path.exists(f"{D}/within_family_v2.csv") and "--redo" not in sys.argv
rows = []
for ds, c in ([] if SKIP_A else CM.groupby("dataset")):
    k = c.groupby("arm_family").size()
    keep = k[(k >= 2)].index.difference(["control"])
    c = c[c.arm_family.isin(keep)].reset_index(drop=True)
    fam_idx = {f: np.flatnonzero(c.arm_family.values == f) for f in keep}
    for m in METS:
        for pear in (False, True):
            obs = demean(c, ["claude_temptation", m])
            est = corr(obs.claude_temptation.values, obs[m].values, pear)
            bs = []
            for _ in range(B):
                sel = np.concatenate([ix[rng.integers(0, len(ix), len(ix))] for ix in fam_idx.values()])
                b = demean(c.iloc[sel].reset_index(drop=True), ["claude_temptation", m])
                bs.append(corr(b.claude_temptation.values, b[m].values, pear))
            rows.append(dict(dataset=ds, metric=m, stat="Pearson" if pear else "Spearman", est=est,
                             lo=np.nanpercentile(bs, 2.5), hi=np.nanpercentile(bs, 97.5), n_cells=len(c), n_families=len(keep),
                             families=";".join(keep)))
if not SKIP_A:
    pd.DataFrame(rows).to_csv(f"{D}/within_family_v2.csv", index=False, float_format="%.4f")

# (b) per-family exact permutation p
F = pd.read_csv(f"{D}/within_family.csv")
out = []
for (ds, fam, m, st), g in F.groupby(["dataset", "arm_family", "metric", "stat"]):
    c = CM[(CM.dataset == ds) & (CM.arm_family == fam)]
    x, y = c.claude_temptation.values, c[m].values
    pear = st == "Pearson"
    e = corr(x, y, pear)
    if len(y) <= 8:   # exact: all orderings
        perms = [corr(x, y[list(p)], pear) for p in itertools.permutations(range(len(y)))]
    else:             # Monte Carlo, 20,000 random orderings
        perms = [corr(x, rng.permutation(y), pear) for _ in range(20000)]
    p = np.mean([abs(v) >= abs(e) - 1e-12 for v in perms])
    r = g.iloc[0].to_dict(); r["perm_p"] = p; r["n_perms"] = len(perms); r["perm_kind"] = "exact" if len(y) <= 8 else "Monte Carlo"; out.append(r)
pd.DataFrame(out).to_csv(f"{D}/within_family.csv", index=False, float_format="%.4f")

# (c) cross-model paired difference
o = CM[CM.dataset.str.startswith("gpt-oss")].set_index(CELL)
q = CM[CM.dataset == "Qwen3-32B, thinking on (neutral)"].set_index(CELL)
j = o.join(q, lsuffix="_oss", rsuffix="_qwen", how="inner").reset_index()
xr = []
for sub, jj in [("all 24 shared cells", j), ("without the two control arms", j[~j.arm.isin(["ctl-32b-compete", "ctl-32b-joint"])])]:
    jj = jj.reset_index(drop=True)
    for m in METS:
        sign = -1 if m == "competitive_share" else 1
        for pear in (False, True):
            def d(ix):
                a = sign * corr(jj.claude_temptation_oss.values[ix], jj[f"{m}_oss"].values[ix], pear)
                b = corr(jj[f"{m}_qwen"].values[ix], jj[f"{m}_oss"].values[ix], pear)
                return a, b, a - b
            a, b, e = d(np.arange(len(jj)))
            bs = [d(rng.integers(0, len(jj), len(jj)))[2] for _ in range(B)]
            xr.append(dict(subset=sub, metric=m, stat="Pearson" if pear else "Spearman", observer=a, qwen=b, diff=e,
                           lo=np.nanpercentile(bs, 2.5), hi=np.nanpercentile(bs, 97.5), n_cells=len(jj)))
pd.DataFrame(xr).to_csv(f"{D}/cross_model_diff.csv", index=False, float_format="%.4f")

# (d) within-cell rating spread, (e) distinct observer values in the temptation self-report arms
sp = []
for lab, p, oss in [("gpt-oss-20b, thinking on (neutral)", oss_p, True), ("Qwen3-32B (neutral)", qw_p, False)]:
    d = pd.read_csv(p, low_memory=False)
    d = d[(d.status == "done") & d.claude_temptation.notna()]
    if oss:
        d = d[~d.arm.str.startswith("hrep-")]
    else:
        d = d[(d.run == "neutral") & ~d.arm.str.startswith(("smoke-", "ctl-14b"))]
    for th, dd in d.groupby("thinking"):
        key = dd[CELL].astype(str).agg("|".join, axis=1)
        w = dd.claude_temptation - dd.groupby(key).claude_temptation.transform("mean")
        sdc = dd.groupby(key).claude_temptation.std()
        t = dd[dd.arm.isin(["d-temptation-a", "d-temptation-b"])]
        sp.append(dict(dataset=f"{lab}, thinking {th}", within_cell_sd=w.std(ddof=1), total_sd=dd.claude_temptation.std(),
                       n_cells=key.nunique(), cells_constant_rating=int((sdc.fillna(0) == 0).sum()),
                       temptation_prompts=t.claude_rating_id.nunique(), distinct_observer_values=t.claude_temptation.round(4).nunique(),
                       observer_values=";".join(f"{v:.2f}" for v in sorted(t.claude_temptation.unique()))))
pd.DataFrame(sp).to_csv(f"{D}/within_cell_spread.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 250)
for f in ["within_family_v2", "cross_model_diff", "within_cell_spread"]:
    x = pd.read_csv(f"{D}/{f}.csv")
    print(f); print(x.round(3).to_string())
print(pd.DataFrame(out)[["dataset", "arm_family", "metric", "stat", "est", "perm_p", "n_perms"]].round(3).to_string())
