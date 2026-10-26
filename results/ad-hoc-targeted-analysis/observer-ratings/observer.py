"""Observer ratings vs collusion and harm (ad hoc, post-processing only).

usage: python observer.py OSS_RUN_CSV QWEN_RUN_CSV OUTDIR OSS_ROUNDS QWEN_NEUTRAL_ROUNDS QWEN_ANCHORED_ROUNDS PART
  PART = 0..4 computes the correlations of one dataset; PART = merge computes the rest from the saved cell means.
  *_ROUNDS: the per-round tables (rounds.csv, one row per firm-round with the round's market_price) of the runs.

OSS_RUN_CSV : final gpt-oss-20b run.csv (claude_* columns joined); hrep-* arms are dropped.
QWEN_RUN_CSV: rated Qwen3-32B run.csv (anchored + neutral Track M runs).
Writes CSVs into OUTDIR. Exploratory; no multiplicity correction.
"""
import sys
import numpy as np
import pandas as pd


def rankdata(a):
    """Average ranks with ties (as scipy.stats.rankdata)."""
    a = np.asarray(a)
    o = np.argsort(a, kind="mergesort")
    sa = a[o]
    first = np.r_[True, sa[1:] != sa[:-1]]
    gid = np.cumsum(first) - 1
    starts = np.flatnonzero(first)
    ends = np.r_[starts[1:], len(a)]
    avg = (starts + ends - 1) / 2.0 + 1
    r = np.empty(len(a))
    r[o] = avg[gid]
    return r

oss_p, qw_p, out, r_oss, r_qn, r_qa, PART = sys.argv[1:8]
rng = np.random.default_rng(20261025)
B_CELL, B_GAME = 2000, 1000

METS = ["avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share", "harm_index"]
RAT = ["claude_temptation", "claude_conflict"]
CELL = ["arm", "communication", "penalty_point"]


def harm(p):
    """Consumer-surplus loss per round at market price p, relative to the competitive price 1.00, as a share of
    the loss at the monopoly price 3.00.  Demand Q(x) = 100 (1 - x/5); loss = integral_1^p Q = 100[(p-1) - (p^2-1)/10];
    at p = 3 the loss is 120 per round, so harm_index = loss / 120 (0 = competitive, 1 = monopoly)."""
    return ((p - 1) - (p ** 2 - 1) / 10) / 1.2


def round_harm(paths):
    """Exact per-game harm: the mean over rounds of the per-round loss at that round's market price."""
    out = {}
    for p in paths:
        r = pd.read_csv(p, usecols=["trial_id", "round", "market_price"]).drop_duplicates(["trial_id", "round"])
        r["h"] = harm(r.market_price)
        g = r.groupby("trial_id")
        out.update(dict(zip(g.h.mean().index, zip(g.h.mean().values, g.market_price.mean().values))))
    return out


def load(p, oss):
    d = pd.read_csv(p, low_memory=False)
    d = d[d.status == "done"]
    if oss:
        d = d[~d.arm.str.startswith("hrep-")].assign(run="neutral")
    else:
        d = d[~d.arm.str.startswith(("smoke-", "ctl-14b"))]
    d = d[d.price_index.notna()].copy()
    d["avg_abs_spread"] = d.market_price_mean
    H = round_harm([r_oss] if oss else [r_qn, r_qa])
    key = d.played_trial_id.where(d.played_trial_id.notna(), d.trial_id)
    if not oss:  # the two Qwen runs share trial ids; keep the per-run table
        H = {}
        for run, rp in [("neutral", r_qn), ("anchored", r_qa)]:
            hh = round_harm([rp])
            m = d.run == run
            d.loc[m, "harm_index"] = key[m].map(lambda t: hh.get(t, (np.nan, np.nan))[0])
            d.loc[m, "_mp_check"] = key[m].map(lambda t: hh.get(t, (np.nan, np.nan))[1])
    else:
        d["harm_index"] = key.map(lambda t: H.get(t, (np.nan, np.nan))[0])
        d["_mp_check"] = key.map(lambda t: H.get(t, (np.nan, np.nan))[1])
    miss = d.harm_index.isna()
    print("harm: games without per-round prices:", int(miss.sum()), "max |mean market price - run.csv|:",
          float((d._mp_check - d.market_price_mean).abs().max()), flush=True)
    d.loc[miss, "harm_index"] = harm(d.market_price_mean[miss])  # fallback: game-mean price (none expected)
    d["model"] = "gpt-oss-20b" if oss else "Qwen3-32B"
    return d


O, Q = load(oss_p, True), load(qw_p, False)
unrated = sorted(O[O.claude_temptation.isna()].arm.unique())
cov = dict(oss_done_games_excl_hrep=len(O), oss_rated=int(O.claude_temptation.notna().sum()), oss_unrated_arms=";".join(unrated),
           qwen_games=len(Q), qwen_rated=int(Q.claude_temptation.notna().sum()))
O = O[O.claude_temptation.notna()]
Q = Q[Q.claude_temptation.notna()]

# datasets: (label, frame)
DS = [("gpt-oss-20b, thinking on (neutral)", O)]
for run in ["neutral", "anchored"]:
    for th in ["on", "off"]:
        DS.append((f"Qwen3-32B, thinking {th} ({run})", Q[(Q.run == run) & (Q.thinking == th)]))


def corr(x, y, pearson):
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    if len(x) < 4 or x.std() == 0 or y.std() == 0:
        return np.nan
    if not pearson:
        x, y = rankdata(x), rankdata(y)
    return np.corrcoef(x, y)[0, 1]


def boot_ci(x, y, groups, B, pearson, strata=None):
    """Percentile CI; resample whole groups (clusters) with replacement, within strata if given."""
    ug = pd.unique(groups)
    idx = {g: np.flatnonzero(groups == g) for g in ug}
    if strata is None:
        strat = {0: ug}
    else:
        s = pd.Series(strata, index=groups).groupby(level=0).first()
        strat = {k: v.index.values for k, v in s.groupby(s)}
    vals = []
    for _ in range(B):
        sel = []
        for gs in strat.values():
            pick = gs[rng.integers(0, len(gs), len(gs))]
            sel.extend(idx[g] for g in pick)
        sel = np.concatenate(sel)
        vals.append(corr(x[sel], y[sel], pearson))
    return np.nanpercentile(vals, 2.5), np.nanpercentile(vals, 97.5)


def cellmeans(d):
    g = d.groupby(CELL)
    c = g[METS + RAT].mean()
    c["n"] = g.size()
    c["arm_family"] = g.arm_family.first()
    return c.reset_index()


if PART != "merge":
  DS = [DS[int(PART)]]
  rows = []
  cells_out = []
  for name, d in DS:
      c = cellmeans(d)
      c.insert(0, "dataset", name)
      cells_out.append(c)
      d = d.copy()
      d["cell"] = d[CELL].astype(str).agg("|".join, axis=1)
      # within-cell deviations (wording-level variation inside one design cell)
      dm = d.copy()
      for v in METS + RAT:
          dm[v] = d[v] - d.groupby("cell")[v].transform("mean")
      # within-family deviations at cell level
      cf = c.copy()
      for v in METS + RAT:
          cf[v] = c[v] - c.groupby("arm_family")[v].transform("mean")
      cid = np.arange(len(c))
      for r in RAT:
          for m in METS:
              for pear in (False, True):
                  stat = "Pearson" if pear else "Spearman"
                  # cell level
                  x, y = c[r].values, c[m].values
                  lo, hi = boot_ci(x, y, cid, B_CELL, pear)
                  rows.append(dict(dataset=name, level="cell", rating=r, metric=m, stat=stat, est=corr(x, y, pear), lo=lo, hi=hi,
                                   n=len(c), clusters=len(c)))
                  # game level, clustered by cell
                  x, y = d[r].values, d[m].values
                  lo, hi = boot_ci(x, y, d.cell.values, B_GAME, pear)
                  rows.append(dict(dataset=name, level="game", rating=r, metric=m, stat=stat, est=corr(x, y, pear), lo=lo, hi=hi,
                                   n=len(d), clusters=d.cell.nunique()))
                  # within cell (game level, demeaned by cell), clustered by cell
                  x, y = dm[r].values, dm[m].values
                  lo, hi = boot_ci(x, y, d.cell.values, B_GAME, pear)
                  rows.append(dict(dataset=name, level="within cell", rating=r, metric=m, stat=stat, est=corr(x, y, pear), lo=lo, hi=hi,
                                   n=len(d), clusters=d.cell.nunique()))
                  # within arm family (cell level, demeaned by family), stratified bootstrap over cells
                  x, y = cf[r].values, cf[m].values
                  lo, hi = boot_ci(x, y, cid, B_CELL, pear, strata=c.arm_family.values)
                  rows.append(dict(dataset=name, level="within family", rating=r, metric=m, stat=stat, est=corr(x, y, pear), lo=lo, hi=hi,
                                   n=len(c), clusters=len(c)))
      print(name, len(d), "games", len(c), "cells", flush=True)

  res = pd.DataFrame(rows)
  res.to_csv(f"{out}/correlations_{PART}.csv", index=False, float_format="%.4f")
  cells = pd.concat(cells_out)
  cells.to_csv(f"{out}/cell_means_{PART}.csv", index=False, float_format="%.4f")

  sys.exit(0)

import glob
res = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{out}/correlations_[0-9].csv"))])
res.to_csv(f"{out}/correlations.csv", index=False, float_format="%.4f")
cells = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{out}/cell_means_[0-9].csv"))])
cells.to_csv(f"{out}/cell_means.csv", index=False, float_format="%.4f")

# per-family cell-level Spearman for families with >= 5 cells (price index and competitive share, temptation)
fam_rows = []
for name, d in DS:
    c = cells[cells.dataset == name]
    for fam, cc in c.groupby("arm_family"):
        if len(cc) < 5:
            continue
        for m in ["price_index", "competitive_share", "harm_index"]:
            for pear in (False, True):
                x, y = cc.claude_temptation.values, cc[m].values
                lo, hi = boot_ci(x, y, np.arange(len(cc)), B_CELL, pear)
                fam_rows.append(dict(dataset=name, arm_family=fam, n_cells=len(cc), arms=";".join(sorted(cc.arm.unique())), metric=m,
                                     stat="Pearson" if pear else "Spearman", est=corr(x, y, pear), lo=lo, hi=hi,
                                     temptation_range=f"{cc.claude_temptation.min():.2f}-{cc.claude_temptation.max():.2f}"))
pd.DataFrame(fam_rows).to_csv(f"{out}/within_family.csv", index=False, float_format="%.4f")

# observer vs self-report (D-set arms that ask for a score)
SR = {"temptation": ["d-temptation-a", "d-temptation-b"], "conflict": ["d-conflict", "d-conflict-ethics"]}
sr_rows, sr_means = [], []
for name, d in DS:
    for kind, arms in SR.items():
        s = d[d.arm.isin(arms) & d.score_mean.notna()].copy()
        if len(s) < 10:
            continue
        rat = f"claude_{kind}"
        g = s.groupby("arm")
        mm = g.agg(games=("score_mean", "size"), self_report=("score_mean", "mean"), claude=(rat, "mean"),
                   price_index=("price_index", "mean"), competitive_share=("competitive_share", "mean"), harm_index=("harm_index", "mean"))
        mm.insert(0, "kind", kind); mm.insert(0, "dataset", name)
        sr_means.append(mm.reset_index())
        # demean within arm so that the arm difference does not drive the correlation
        sw = s.copy()
        for v in ["score_mean", rat] + METS:
            sw[v] = s[v] - s.groupby("arm")[v].transform("mean")
        for frame, scope in [(s, "pooled arms"), (sw, "within arm")]:
            pairs = [("self-report vs observer", "score_mean", rat)] + \
                    [(f"self-report vs {m}", "score_mean", m) for m in METS] + [(f"observer vs {m}", rat, m) for m in METS]
            for lab, a, b in pairs:
                for pear in (False, True):
                    x, y = frame[a].values, frame[b].values
                    lo, hi = boot_ci(x, y, s.claude_rating_id.values, B_GAME, pear)
                    sr_rows.append(dict(dataset=name, kind=kind, scope=scope, pair=lab, stat="Pearson" if pear else "Spearman",
                                        est=corr(x, y, pear), lo=lo, hi=hi, n_games=len(s), n_prompts=s.claude_rating_id.nunique(),
                                        arms=";".join(arms)))
pd.DataFrame(sr_rows).to_csv(f"{out}/self_report.csv", index=False, float_format="%.4f")
pd.concat(sr_means).to_csv(f"{out}/self_report_means.csv", index=False, float_format="%.4f")

# cross-model benchmark: does Qwen's behaviour in the same cell predict gpt-oss better than the observer does?
co = cells[cells.dataset.str.startswith("gpt-oss")].set_index(CELL)
cq = cells[cells.dataset == "Qwen3-32B, thinking on (neutral)"].set_index(CELL)
j = co.join(cq, lsuffix="_oss", rsuffix="_qwen", how="inner")
xm = []
for m in METS:
    for pear in (False, True):
        for lab, a in [("Qwen3-32B same cell (thinking on, neutral)", f"{m}_qwen"), ("observer temptation", "claude_temptation_oss")]:
            x, y = j[a].values, j[f"{m}_oss"].values
            lo, hi = boot_ci(x, y, np.arange(len(j)), B_CELL, pear)
            xm.append(dict(predictor=lab, target=f"gpt-oss {m}", stat="Pearson" if pear else "Spearman", est=corr(x, y, pear), lo=lo, hi=hi, n_cells=len(j)))
pd.DataFrame(xm).to_csv(f"{out}/cross_model.csv", index=False, float_format="%.4f")
pd.Series(cov | {"cross_model_cells": len(j)}).to_csv(f"{out}/coverage.csv", header=["value"])
print(cov, "cross cells", len(j))
