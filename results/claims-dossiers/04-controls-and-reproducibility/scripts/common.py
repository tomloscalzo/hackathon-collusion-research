"""Shared helpers for dossier 04 (independent re-derivation from the run.csv game tables)."""
import os, numpy as np, pandas as pd
OSS = os.environ.get('OSS_RUN_CSV')    # gpt-oss Step 1 run.csv (set the environment variable)
QWEN = os.environ.get('QWEN_RUN_CSV')  # final Qwen Step 1 run.csv (neutral rows are used)
if not OSS or not QWEN: raise SystemExit('set OSS_RUN_CSV and QWEN_RUN_CSV')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
METRICS = [('market_price_mean', 'Average absolute spread'), ('price_index', 'Price index'),
           ('profit_gain_index', 'Profit gain index'), ('competitive_share', 'Competitive share (U16)'),
           ('matching_share', 'Matching share')]
MCOLS = [m for m, _ in METRICS]; MNAME = dict(METRICS)
NB = 10000

def load(which):
    d = pd.read_csv(OSS if which == 'oss' else QWEN, low_memory=False)
    d = d[d.run == 'neutral']
    d = d[d.status == 'done'].copy()
    d['pair'] = d.wording.astype(int).astype(str) + '_' + d.seed.astype(int).astype(str)
    if which == 'oss': d['think'] = 't1'
    else: d['think'] = np.where(d.thinking == 'on', 't1', 't0')
    return d

def sel(d, arm, p=None, think=None):
    x = d[d.arm == arm]
    if p is not None: x = x[x.penalty_point == p]
    if think is not None: x = x[x.think == think]
    return x

def pairdiff(a, b, m):
    """paired difference a-b over (wording,seed); each side averaged within pair (one game per pair here)."""
    sa = a.groupby('pair')[m].mean(); sb = b.groupby('pair')[m].mean()
    j = pd.concat([sa, sb], axis=1, keys=['a', 'b']).dropna()
    return j.index.values, j.a.values, j.b.values

def boot_ci(x, seed=20261025):
    rng = np.random.default_rng(seed)
    b = x[rng.integers(0, len(x), (NB, len(x)))].mean(1)
    return np.percentile(b, 2.5), np.percentile(b, 97.5)

def signflip_p(x, mc=400000, seed=7):
    """Exact two-sided sign-flip permutation p for n<=20, Monte Carlo (400k) otherwise."""
    x = np.asarray(x, float); n = len(x); obs = abs(x.sum())
    if n == 0: return np.nan
    tol = 1e-9 * max(1.0, obs)
    if n <= 20:
        cnt = 0; tot = 2 ** n; chunk = 1 << 17
        for s in range(0, tot, chunk):
            idx = np.arange(s, min(tot, s + chunk), dtype=np.int64)
            bits = ((idx[:, None] >> np.arange(n)) & 1) * 2 - 1
            cnt += int((np.abs(bits @ x) >= obs - tol).sum())
        return cnt / tot
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(mc // 50000):
        sg = rng.integers(0, 2, (50000, n)) * 2 - 1
        cnt += int((np.abs(sg @ x) >= obs - tol).sum())
    return (cnt + 1) / (mc // 50000 * 50000 + 1)

def holm(ps):
    ps = np.asarray(ps, float); n = len(ps); o = np.argsort(ps); adj = np.empty(n); run = 0
    for r, i in enumerate(o):
        run = max(run, (n - r) * ps[i]); adj[i] = min(1, run)
    return adj

def contrast(a, b, m):
    ix, va, vb = pairdiff(a, b, m); d = va - vb; n = len(d)
    lo, hi = boot_ci(d) if n > 1 else (np.nan, np.nan)
    se = d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return dict(n_pairs=n, mean_a=va.mean(), mean_b=vb.mean(), diff=d.mean(), ci_lo=lo, ci_hi=hi,
                p_signflip=signflip_p(d), se=se, mde=2.8 * se, d=d)

def fmt(r, k=3):
    return f"{r['diff']:+.{k}f} [{r['ci_lo']:+.{k}f}, {r['ci_hi']:+.{k}f}]"
