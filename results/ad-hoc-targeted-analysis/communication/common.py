"""Shared helpers: paired bootstrap CI over pairs and exact/sampled sign-flip permutation p-value."""
import os, numpy as np, pandas as pd
DATA = os.environ.get("STEP1_DIR", "steps/neutral/step1")   # folder holding run.csv, run_firms.csv, tables/
RNG = np.random.default_rng(20261025)
def boot_ci(d, n=10000):
    d = np.asarray(d, float); d = d[~np.isnan(d)]
    m = RNG.choice(d, (n, len(d))).mean(1)
    return d.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)
def signflip_p(d, n=100000):
    d = np.asarray(d, float); d = d[~np.isnan(d)]
    obs = abs(d.mean())
    if len(d) <= 16:
        s = np.array([[1 if (i >> j) & 1 else -1 for j in range(len(d))] for i in range(2 ** len(d))])
    else:
        s = RNG.choice([-1, 1], (n, len(d)))
    return float(((np.abs((s * d).mean(1)) >= obs - 1e-12).mean()))
def holm(ps):
    ps = np.asarray(ps); o = np.argsort(ps); out = np.empty(len(ps)); run = 0
    for k, i in enumerate(o):
        run = max(run, (len(ps) - k) * ps[i]); out[i] = min(1, run)
    return out
def load_run():
    r = pd.read_csv(os.path.join(DATA, "run.csv"), low_memory=False)
    return r[(r.status == "done") & (r.in_primary == 1)].copy()
def paired(df, col, a, b, key=("wording", "seed")):
    """difference b - a per (wording, seed) pair. df has column 'cond'."""
    p = df.pivot_table(index=list(key), columns="cond", values=col, aggfunc="mean")
    return (p[b] - p[a]).dropna()
