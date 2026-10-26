"""Robustness of the cell-level temptation vs competitive-share correlation (leverage, definitions).

usage: python leverage.py OSS_RUN_CSV QWEN_RUN_CSV OUTDIR OSS_ROUNDS QWEN_NEUTRAL_ROUNDS

(1) Pearson and Spearman with and without the instructed-objective control arms;
(2) leave-one-cell-out Pearson and Cook's distance of each cell;
(3) four competitive-share definitions recomputed from the firm-rounds.
Neutral payoff table; gpt-oss-20b (thinking on) and Qwen3-32B (thinking on, thinking off). Exploratory.
"""
import sys
import numpy as np
import pandas as pd

oss_p, qw_p, out, r_oss, r_qn = sys.argv[1:6]
rng = np.random.default_rng(7)
B = 2000
CELL = ["arm", "communication", "penalty_point"]
TICK = 0.005  # half-tick tolerance, as in the engine's competitive flag


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


def ci(x, y, pearson):
    n = len(x); v = []
    for _ in range(B):
        i = rng.integers(0, n, n); v.append(corr(x[i], y[i], pearson))
    return np.nanpercentile(v, 2.5), np.nanpercentile(v, 97.5)


def firm_round_defs(rounds_path, keep):
    """Per-game shares under four definitions, from firm-rounds (round >= 2; target = lowest OTHER quote of round r-1)."""
    r = pd.read_csv(rounds_path, usecols=["trial_id", "round", "seat", "quote"])
    r = r[r.trial_id.isin(keep)].dropna(subset=["quote"])
    prev = r.assign(round=r["round"] + 1)
    m = r.merge(prev, on=["trial_id", "round"], suffixes=("", "_o"))
    m = m[m.seat != m.seat_o]
    tgt = m.groupby(["trial_id", "round", "seat"]).quote_o.min().rename("target").reset_index()
    f = r.merge(tgt, on=["trial_id", "round", "seat"])
    q, t = f.quote, f.target
    under = q < t - TICK
    f["u16"] = (under | ((t <= 1.0 + 1e-9) & (q <= 1.0 + 1e-9))).astype(float)
    f["u16_floor101"] = (under | ((t <= 1.01 + 1e-9) & (q <= 1.01 + 1e-9))).astype(float)
    f["strict_undercut"] = under.astype(float)
    for thr, nm in [(1.01, "q_le_101"), (1.02, "q_le_102"), (1.05, "near_floor_quote"), (1.10, "q_le_110")]:
        f[nm] = (q <= thr + 1e-9).astype(float)
    return f.groupby("trial_id")[["u16", "u16_floor101", "strict_undercut", "q_le_101", "q_le_102", "near_floor_quote", "q_le_110"]].mean()


def load(p, oss, rounds_path):
    d = pd.read_csv(p, low_memory=False)
    d = d[d.status == "done"]
    if oss:
        d = d[~d.arm.str.startswith("hrep-")].assign(run="neutral")
    else:
        d = d[(d.run == "neutral") & ~d.arm.str.startswith(("smoke-", "ctl-14b"))]
    d = d[d.price_index.notna() & d.claude_temptation.notna()].copy()
    d["key"] = d.played_trial_id.where(d.played_trial_id.notna(), d.trial_id)
    defs = firm_round_defs(rounds_path, set(d.key))
    d = d.join(defs, on="key")
    print("games", len(d), "with firm-round defs", int(d.u16.notna().sum()),
          "corr(recomputed U16, run.csv competitive_share) =", round(d[["u16", "competitive_share"]].corr().iloc[0, 1], 4),
          "max abs diff", round((d.u16 - d.competitive_share).abs().max(), 4), flush=True)
    return d


O = load(oss_p, True, r_oss)
Qa = load(qw_p, False, r_qn)
DS = [("gpt-oss-20b, thinking on", O), ("Qwen3-32B, thinking on", Qa[Qa.thinking == "on"]),
      ("Qwen3-32B, thinking off", Qa[Qa.thinking == "off"])]
CTRL = ["ctl-32b-compete", "ctl-32b-joint"]
INSTR = CTRL + ["m-inc-joint"]
DEFS = {"competitive_share": "U16 as reported (run.csv)", "u16_floor101": "U16 with tick-adjusted floor (<= 1.01)",
        "strict_undercut": "strict undercut share (floor holds not counted)", "q_le_101": "share of quotes at 1.01 or less",
        "q_le_102": "share of quotes at 1.02 or less", "near_floor_quote": "share of quotes at 1.05 or less", "q_le_110": "share of quotes at 1.10 or less",
        "price_index": "price index (reference)"}

rows, loo_rows, cook_rows = [], [], []
for name, d in DS:
    c = d.groupby(CELL)[["claude_temptation"] + list(DEFS)].mean().reset_index()
    c["n"] = d.groupby(CELL).size().values
    variants = {"all cells": c, "without the two control arms": c[~c.arm.isin(CTRL)],
                "without controls and m-inc-joint": c[~c.arm.isin(INSTR)],
                "without controls and no-chat cells": c[~c.arm.isin(CTRL) & (c.communication != "tacit")]}
    for vn, cc in variants.items():
        for m, ml in DEFS.items():
            x, y = cc.claude_temptation.values, cc[m].values
            for pear in (False, True):
                lo, hi = ci(x, y, pear)
                rows.append(dict(dataset=name, subset=vn, metric=m, definition=ml, stat="Pearson" if pear else "Spearman",
                                 est=corr(x, y, pear), lo=lo, hi=hi, n_cells=len(cc)))
    # leave-one-cell-out and Cook's distance, all cells, U16 as reported
    for m in ["competitive_share", "price_index"]:
        x, y = c.claude_temptation.values, c[m].values
        full = corr(x, y, True); fs = corr(x, y, False)
        loo = np.array([corr(np.delete(x, i), np.delete(y, i), True) for i in range(len(x))])
        loos = np.array([corr(np.delete(x, i), np.delete(y, i), False) for i in range(len(x))])
        X = np.c_[np.ones(len(x)), x]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        e = y - X @ beta
        h = np.einsum("ij,jk,ik->i", X, np.linalg.inv(X.T @ X), X)
        s2 = (e ** 2).sum() / (len(x) - 2)
        cook = e ** 2 / (2 * s2) * h / (1 - h) ** 2
        lab = c.arm + ", " + c.communication + ", p" + c.penalty_point.astype(int).astype(str)
        loo_rows.append(dict(dataset=name, metric=m, n_cells=len(x), pearson_full=full, spearman_full=fs,
                             loo_pearson_min=loo.min(), loo_pearson_median=np.median(loo), loo_pearson_max=loo.max(),
                             loo_spearman_min=loos.min(), loo_spearman_max=loos.max(),
                             most_influential_cell=lab.iloc[int(np.argmax(cook))], max_cook=cook.max()))
        for i in np.argsort(-cook)[:5]:
            cook_rows.append(dict(dataset=name, metric=m, cell=lab.iloc[i], temptation=x[i], value=y[i], cook_d=cook[i],
                                  leverage=h[i], pearson_without_cell=loo[i], spearman_without_cell=loos[i], games=int(c.n.iloc[i])))
        c.assign(cook_d=cook, loo_pearson=loo, label=lab).to_csv(
            f"{out}/leverage_cells_{name.split(',')[0]}_{name.split()[-1]}_{m}.csv", index=False, float_format="%.4f")

noise = []
for name, d in DS:
    g = d.groupby(CELL)
    c = g.agg(cs=("competitive_share", "mean"), sd=("competitive_share", "std"), n=("competitive_share", "size"),
              pi=("price_index", "mean"), nf=("near_floor_quote", "mean")).reset_index()
    c["se"] = c.sd / np.sqrt(c.n)
    mid = c[(c.cs >= 0.25) & (c.cs <= 0.50)]
    noise.append(dict(dataset=name, n_cells=len(c), band="cells with competitive share 0.25 to 0.50", n_band=len(mid),
                      sd_between_cells_in_band=mid.cs.std(), median_cell_se_in_band=mid.se.median(), median_cell_se_all=c.se.median(),
                      sd_between_all_cells=c.cs.std(),
                      r_nearfloor_vs_price_index=np.corrcoef(c.nf, c.pi)[0, 1],
                      cells_with_cs_ge_055=";".join(c[c.cs >= 0.55].arm + " " + c[c.cs >= 0.55].communication + " p" + c[c.cs >= 0.55].penalty_point.astype(int).astype(str))))
pd.DataFrame(noise).to_csv(f"{out}/leverage_noise_band.csv", index=False, float_format="%.4f")
print(pd.DataFrame(noise).round(3).to_string())
pd.DataFrame(rows).to_csv(f"{out}/leverage_subsets.csv", index=False, float_format="%.4f")
pd.DataFrame(loo_rows).to_csv(f"{out}/leverage_loo.csv", index=False, float_format="%.4f")
pd.DataFrame(cook_rows).to_csv(f"{out}/leverage_cook.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 250)
R = pd.DataFrame(rows)
print(R[R.subset.eq("all cells")].pivot_table(
    index=["dataset", "subset", "metric"], columns="stat", values="est").round(2).to_string())
print(pd.DataFrame(loo_rows).round(3).to_string())
print(pd.DataFrame(cook_rows).round(3).to_string())
