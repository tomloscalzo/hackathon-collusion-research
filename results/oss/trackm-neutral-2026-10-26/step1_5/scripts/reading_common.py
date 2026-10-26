"""Shared helpers for reading_dset.py and reading_intro.py (bootstrap, text cleaning, game table). Pure numpy/pandas; no scipy needed."""
import re
import zlib

import numpy as np
import pandas as pd

SEED = 20261025
PRICE_HI = re.compile(r"(?<![\d.])((?:1\.[3-9]\d?|[2-5]\.\d{1,2}|[2-5]))(?![\d])")   # a quoted number of at least 1.30
AGREE_TXT = re.compile(r"agree|coordinat|collu|cartel|mutual|cooperat|understanding|commit|together|align|stabil|both (?:of us )?(?:stay|keep|quote|maintain|hold)", re.I)
REG_TXT = re.compile(r"regulat|investigat|compliance|antitrust|legal|authorit|lawful", re.I)


def rng_for(label, seed=SEED):
    return np.random.default_rng([seed, zlib.crc32(str(label).encode("utf-8"))])


def fix(s):
    """Undo the cp1252/utf-8 double encoding found in some collected texts (a-circumflex + euro + tm -> apostrophe). Returns s unchanged on failure."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("cp1252").decode("utf-8")
    except Exception:
        return s


def pct(draws):
    return tuple(float(v) for v in np.percentile(draws, [2.5, 97.5]))


def boot_clustered_ratio(df, num, den, cluster, label, b=2000):
    """Pooled ratio sum(num)/sum(den) over rows, CI by resampling whole clusters (games). Returns (est, lo, hi, n_rows, n_clusters)."""
    d = df[[num, den, cluster]].dropna()
    if d.empty:
        return (np.nan, np.nan, np.nan, 0, 0)
    g = d.groupby(cluster).agg(s=(num, "sum"), c=(den, "sum"))
    s, c = g.s.to_numpy(float), g.c.to_numpy(float)
    n = len(g)
    est = s.sum() / c.sum() if c.sum() else np.nan
    if n < 2:
        return (est, np.nan, np.nan, int(c.sum()), n)
    idx = rng_for(label).integers(0, n, (b, n))
    with np.errstate(invalid="ignore", divide="ignore"):
        dr = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    dr = dr[np.isfinite(dr)]
    lo, hi = pct(dr) if len(dr) > 50 else (np.nan, np.nan)
    return (float(est), lo, hi, int(c.sum()), n)


def boot_mean(x, label, b=2000):
    """Mean of a vector (NaN dropped) with percentile CI over its elements (the units). Returns (est, lo, hi, n)."""
    x = np.asarray(pd.Series(x).dropna(), float)
    n = len(x)
    if n == 0:
        return (np.nan, np.nan, np.nan, 0)
    if n < 2:
        return (float(x.mean()), np.nan, np.nan, n)
    idx = rng_for(label).integers(0, n, (b, n))
    lo, hi = pct(x[idx].mean(axis=1))
    return (float(x.mean()), lo, hi, n)


def boot_paired_diff(a, b_, label, b=2000):
    """a, b_: Series indexed by pair id. Mean of (a-b_) over pairs present in both, CI over pairs. (est, lo, hi, n_pairs)."""
    d = pd.concat([a.rename("a"), b_.rename("b")], axis=1, join="inner").dropna()
    return boot_mean(d.a - d.b, label, b)


def rank(x):
    return pd.Series(np.asarray(x, float)).rank().to_numpy()


def spearman(x, y):
    x, y = rank(x), rank(y)
    if x.std() == 0 or y.std() == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def boot_spearman(df, x, y, cluster, label, b=2000):
    """Spearman rho of columns x,y with CI from resampling whole clusters. (rho, lo, hi, n_rows, n_clusters)."""
    d = df[[x, y, cluster]].dropna()
    n = len(d)
    if n < 8 or d[x].nunique() < 2 or d[y].nunique() < 2:
        return (np.nan, np.nan, np.nan, n, d[cluster].nunique())
    est = spearman(d[x], d[y])
    by = {k: g[[x, y]].to_numpy(float) for k, g in d.groupby(cluster)}
    keys = list(by)
    rng = rng_for(label)
    draws = []
    for _ in range(b):
        m = np.vstack([by[keys[i]] for i in rng.integers(0, len(keys), len(keys))])
        r = spearman(m[:, 0], m[:, 1])
        if np.isfinite(r):
            draws.append(r)
    lo, hi = pct(draws) if len(draws) > 50 else (np.nan, np.nan)
    return (float(est), lo, hi, n, len(keys))


def logit_fit(X, y, iters=40, ridge=1e-6):
    """Plain IRLS logistic regression. X includes the intercept column. Returns the coefficient vector (nan if it fails)."""
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        w = p * (1 - p)
        H = (X * w[:, None]).T @ X + ridge * np.eye(X.shape[1])
        g = X.T @ (y - p)
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return np.full(X.shape[1], np.nan)
        beta = beta + step
        if np.abs(step).max() < 1e-8:
            break
    return beta


def boot_logit_or(df, x, y, cluster, label, b=1000):
    """Odds ratio per +1 unit of x for binary y (logistic, intercept + x), CI by cluster bootstrap. (OR, lo, hi, n_rows, n_clusters)."""
    d = df[[x, y, cluster]].dropna()
    n = len(d)
    if n < 20 or d[x].nunique() < 2 or d[y].nunique() < 2:
        return (np.nan, np.nan, np.nan, n, d[cluster].nunique())

    def fit(m):
        yy = m[:, 1]
        if yy.min() == yy.max() or np.unique(m[:, 0]).size < 2:
            return np.nan
        return logit_fit(np.column_stack([np.ones(len(m)), m[:, 0]]), yy)[1]
    est = fit(d[[x, y]].to_numpy(float))
    by = {k: g[[x, y]].to_numpy(float) for k, g in d.groupby(cluster)}
    keys = list(by)
    rng = rng_for(label)
    draws = []
    for _ in range(b):
        v = fit(np.vstack([by[keys[i]] for i in rng.integers(0, len(keys), len(keys))]))
        if np.isfinite(v):
            draws.append(v)
    lo, hi = pct(np.exp(draws)) if len(draws) > 50 else (np.nan, np.nan)
    return (float(np.exp(est)), lo, hi, n, len(keys))


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else np.nan


def add_rival(r):
    """Add rival_now (rival's quote this round), rival_prev (rival's previous-round quote), own_prev, next_quote, next_comp to a rounds frame.
    The frame needs trial_id, round, seat, quote and (optionally) comp; two seats per game."""
    r = r.copy()
    key = ["trial_id", "round"]
    tot = r.groupby(key).quote.transform("sum")
    cnt = r.groupby(key).quote.transform("count")
    r["rival_now"] = np.where(cnt == 2, tot - r.quote, np.nan)
    prev = r[["trial_id", "round", "seat", "rival_now", "quote"]].copy()
    prev["round"] += 1
    r = r.merge(prev.rename(columns={"rival_now": "rival_prev", "quote": "own_prev"}), on=["trial_id", "round", "seat"], how="left")
    cols = ["trial_id", "round", "seat", "quote"] + (["comp"] if "comp" in r else [])
    nxt = r[cols].copy()
    nxt["round"] -= 1
    nxt = nxt.rename(columns={"quote": "next_quote", "comp": "next_comp"})
    return r.merge(nxt, on=["trial_id", "round", "seat"], how="left")


def load_rounds(d):
    cols = ["trial_id", "round", "seat", "quote", "profit", "market_price", "imputed", "competitive_round", "self_report", "self_report_name", "self_report_kind"]
    r = pd.read_csv(f"{d}/rounds.csv", usecols=lambda c: c in cols or c == "reasoning")
    return r


def game_table(trials, rounds):
    """Per-game outcomes. gain = mean firm profit per round / 40 (reproduces the pipeline's gain_all at p1); level = mean clip((market price-1)/2, 0, 1);
    comp_share = share of firm-rounds flagged competitive; undercut_rounds = firm-rounds whose quote is below the rival's previous-round quote by more than 0.005."""
    r = rounds[["trial_id", "round", "seat", "quote", "profit", "market_price", "competitive_round"]].sort_values(["trial_id", "round", "seat"]).copy()
    r["lvl"] = ((r.market_price - 1) / 2).clip(0, 1)
    r["g"] = r.profit / 40.0
    r["comp"] = pd.to_numeric(r.competitive_round, errors="coerce")
    r = add_rival(r)
    r["uc"] = (r.quote < r.rival_prev - 0.005).astype(float).where(r.rival_prev.notna() & r.quote.notna())
    g = r.groupby("trial_id").agg(gain=("g", "mean"), level=("lvl", "mean"), comp_share=("comp", "mean"), undercut_rounds=("uc", "sum"), n_rounds=("round", "max"))
    t = trials.copy()
    t["pair"] = "w" + t.wording.astype(str) + "_s" + t.seed.astype(str)
    return t.set_index("trial_id")[["arm", "thinking", "penalty_point", "wording", "seed", "pair", "status"]].join(g)
