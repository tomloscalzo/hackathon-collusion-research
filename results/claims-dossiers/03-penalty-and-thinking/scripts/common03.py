"""Shared loaders and paired statistics for dossier 03 (penalty, thinking mode,
outcome vs strategic collusion). Independent of the earlier ad hoc scripts.

Inputs (read-only), set by environment variables:
  QWEN_RUN  Qwen3-32B neutral run.csv (Step 1 game table)
  OSS_RUN   gpt-oss-20b neutral run.csv (Step 1 game table)
  RUNS_DIR  folder holding the raw game folders (<source_root>/trials/<arm>/<played_trial_id>/events.jsonl)
"""
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
QWEN_RUN = os.environ["QWEN_RUN"]  # Qwen neutral Step 1 run.csv
OSS_RUN = os.environ["OSS_RUN"]  # gpt-oss neutral Step 1 run.csv
RUNS_DIR = os.environ["RUNS_DIR"]  # folder with the raw run roots

# the five standard metrics, run.csv columns; direction +1 = higher is more collusive
METRICS = [
    ("market_price_mean", "Average absolute spread (1.00-5.00)", +1),
    ("price_index", "Price index", +1),
    ("profit_gain_index", "Profit gain index", +1),
    ("competitive_share", "Competitive share (U16)", -1),
    ("matching_share", "Matching share", +1),
]
THETA = {1: 0.7029, 3: 0.5459, 4: 0.3249, 5: 0.0}          # theory price index (run.csv theory_theta_star)
THEORY_GAIN = {1: 0.912, 3: 0.794, 4: 0.544, 5: 0.000}     # theory profit gain index (FINAL_NUMBERS 'theory' column)
B = 10000
RNG = np.random.default_rng(20261025)


def load(model):
    path = QWEN_RUN if model == "qwen" else OSS_RUN
    d = pd.read_csv(path, low_memory=False)
    d = d[(d.in_primary == 1) & (d.run == "neutral")].copy()
    d["model"] = model
    d["pair"] = d.wording.astype(int).astype(str) + "_" + d.seed.astype(int).astype(str)
    d["comm"] = d.arm.map({"headline-tacit": "tacit", "headline-chat": "chat", "headline-monitored": "monitored"})
    d["mode"] = d.thinking.map({"on": "t1", "off": "t0"})
    return d


def headline(model, include_hrep=False):
    d = load(model)
    h = d[d.arm.isin(["headline-tacit", "headline-chat", "headline-monitored"])].copy()
    if include_hrep:
        r = d[d.arm.str.startswith("hrep-")].copy()
        r["comm"] = np.where(r.arm.str.contains("chat"), "chat", "tacit")
        h = pd.concat([h, r])
    return h


def cell_wide(h, metric, comm, mode):
    """pair x penalty_point table of a metric for one comm and mode."""
    s = h[(h.comm == comm) & (h["mode"] == mode)]
    return s.pivot_table(index="pair", columns="penalty_point", values=metric, aggfunc="mean")


# ---------- paired statistics ----------
_SIGNS = {}

def _signs(n):
    if n not in _SIGNS:
        if n <= 22:
            k = np.arange(2 ** n, dtype=np.int64)[:, None]
            _SIGNS[n] = (1 - 2 * ((k >> np.arange(n)) & 1)).astype(np.int8)
        else:
            _SIGNS[n] = None
    return _SIGNS[n]


def signflip_p(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x)
    if n == 0:
        return np.nan
    obs = abs(x.mean())
    S = _signs(n)
    if S is None:
        S = RNG.choice([-1, 1], size=(200000, n))
    m = np.abs((S * x).mean(axis=1))
    return float((m >= obs - 1e-12).mean())


def boot(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan
    idx = RNG.integers(0, n, size=(B, n))
    bm = x[idx].mean(axis=1)
    return float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5)), float(bm.std(ddof=1))


def summarise(x, **lab):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    lo, hi, se = boot(x)
    return dict(lab, n_pairs=len(x), effect=float(x.mean()) if len(x) else np.nan,
                ci_lo=lo, ci_hi=hi, se_boot=se, mde=2.8 * se if se == se else np.nan,
                p_signflip=signflip_p(x))


def holm(df, pcol="p_signflip", by=None, out="p_holm"):
    df = df.copy()
    groups = [df] if by is None else [g for _, g in df.groupby(by, sort=False)]
    res = pd.Series(index=df.index, dtype=float)
    fam = pd.Series(index=df.index, dtype=float)
    for g in groups:
        p = g[pcol].values; order = np.argsort(p); m = len(p)
        adj = np.empty(m); run = 0
        for r, i in enumerate(order):
            run = max(run, (m - r) * p[i]); adj[i] = min(1.0, run)
        res[g.index] = adj; fam[g.index] = m
    df[out] = res; df["holm_family_size"] = fam.astype(int)
    return df


def _rank(a):
    return pd.Series(a).rank().values


def corr_both(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    if len(x) < 3:
        return np.nan, np.nan, len(x)
    pe = float(np.corrcoef(x, y)[0, 1]); sp = float(np.corrcoef(_rank(x), _rank(y))[0, 1])
    return sp, pe, len(x)


def fmt(e, lo, hi, nd=3):
    return f"{e:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"
