"""Shared loaders and statistics for dossier 10 (third-party prompt ratings and self-reports as collusion signals).

Independent re-derivation from the Step 1 game tables (run.csv). numpy + pandas only.
Environment: HACKATHON_DIR (default ~/hackathon) is the parent of work_scratch/.
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd

try:
    import psutil
    psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
os.environ.setdefault("OMP_NUM_THREADS", "2")

HK = Path(os.environ.get("HACKATHON_DIR", Path.home() / "hackathon"))
OSS_RUN = HK / "work_scratch/oss_analysis/step1/final_t2/run.csv"
OSS_ROUNDS = HK / "work_scratch/oss_analysis/tables_t2/rounds.csv"
QWEN_RUN = HK / "work_scratch/analysis_final/steps/neutral/step1/run.csv"
# Qwen Step 1 table rebuilt with --prompt-ratings (anchored + neutral); used only for the rating columns (joined by row_id)
# and for the anchored run (secondary).
QWEN_RATED = HK / "work_scratch/prompt_ratings/run_csv_rated/run.csv"

METRICS = [("market_price_mean", "Average absolute spread (half-spread, 1.00-5.00)", "abs_spread"),
           ("price_index", "Price index (0 = 1.00 competitive, 1 = 3.00 monopoly)", "price_index"),
           ("profit_gain_index", "Profit gain index (0 = competitive, 1 = monopoly profit)", "profit_gain_index"),
           ("competitive_share", "Competitive share U16 (higher = more competitive)", "competitive_share"),
           ("matching_share", "Matching share (higher = more coordinated)", "matching_share")]
MCOLS = [m[0] for m in METRICS]
MSHORT = {"market_price_mean": "avg abs spread", "price_index": "price index", "profit_gain_index": "profit gain index",
          "competitive_share": "competitive share", "matching_share": "matching share"}
RCOLS = ["claude_temptation", "claude_conflict"]
SEED = 20261025
NB = 2000
NPERM = 10000
HREP_TWIN = {"hrep-fx-chat-p1": "headline-chat", "hrep-nx-chat-p1": "headline-chat", "hrep-fx-chat-p5": "headline-chat",
             "hrep-fx-tacit-p1": "headline-tacit", "hrep-nx-tacit-p1": "headline-tacit"}
KEEP = ["row_id", "run", "arm", "penalty_point", "communication", "firms", "wording", "seed", "thinking", "score_name",
        "score_mean"] + MCOLS


def load_oss():
    d = pd.read_csv(OSS_RUN, low_memory=False)
    d = d[d.status == "done"].copy()
    d["model"] = "gpt-oss-20b"
    return d


def load_qwen(run="neutral"):
    """Qwen games of one run with the Claude rating columns. Neutral: metrics from the final neutral table (7 truncation
    reruns differ from the rated build), ratings joined by row_id (ratings are per prompt text, unaffected by reruns)."""
    r = pd.read_csv(QWEN_RATED, low_memory=False)
    r = r[(r.status == "done") & (r.run == run)]
    rat = r[["row_id"] + RCOLS + ["claude_rating_id"]]
    if run == "neutral":
        q = pd.read_csv(QWEN_RUN, low_memory=False)
        q = q[q.status == "done"].copy()
        q = q.merge(rat, on="row_id", how="left", validate="1:1")
    else:
        q = r.copy()
    q["model"] = "Qwen3-32B"
    return q


def prep(d, drop_hrep=True):
    d = d.copy()
    if drop_hrep:
        d = d[~d.arm.isin(HREP_TWIN)]
    else:
        d["arm"] = d.arm.replace(HREP_TWIN)
    d["cell"] = d.arm.astype(str) + "@p" + d.penalty_point.astype(str)
    d["prompt"] = d.cell + "@w" + d.wording.astype(str)
    return d


def aggregate(d, level, extra=()):
    """level: 'game' (rows), 'prompt' ((arm, penalty, wording) means over seeds), 'cell' ((arm, penalty) means),
    'text' (distinct rated prompt text, claude_rating_id)."""
    cols = MCOLS + RCOLS + list(extra)
    if level == "game":
        out = d.copy()
        out["cluster"] = out.cell
        return out
    key = {"prompt": "prompt", "cell": "cell", "text": "claude_rating_id"}[level]
    g = d.groupby(key)
    out = g[cols].mean()
    out["n_games"] = g.size()
    for c in ("communication", "penalty_point", "firms", "cell", "arm", "wording"):
        if c != key:
            out[c] = g[c].first()
    out = out.reset_index()
    out["cluster"] = out.cell if level in ("prompt", "text") else out[key]
    return out


def _rank(a):
    return pd.DataFrame(a).rank(axis=0).to_numpy()


def _corr_cols(x, y):
    """column-wise Pearson of two (n, B) arrays"""
    x = x - x.mean(0)
    y = y - y.mean(0)
    with np.errstate(all="ignore"):
        return (x * y).sum(0) / np.sqrt((x * x).sum(0) * (y * y).sum(0))


def corr_pair(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 4 or x.std() == 0 or y.std() == 0:
        return np.nan, np.nan, len(x)
    p = float(np.corrcoef(x, y)[0, 1])
    s = float(np.corrcoef(_rank(x[:, None])[:, 0], _rank(y[:, None])[:, 0])[0, 1])
    return s, p, len(x)


def boot_corr(x, y, cluster, rng, nb=NB):
    """Spearman and Pearson with 95% percentile CIs from resampling whole clusters (re-ranked in every resample)."""
    x = np.asarray(x, float); y = np.asarray(y, float); cl = np.asarray(cluster)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, cl = x[ok], y[ok], cl[ok]
    s, p, n = corr_pair(x, y)
    res = dict(n=n, n_clusters=len(set(cl)), spearman=s, pearson=p)
    if np.isnan(s) or len(set(cl)) < 5:
        res.update(sp_lo=np.nan, sp_hi=np.nan, pe_lo=np.nan, pe_hi=np.nan, sp_se=np.nan, pe_se=np.nan)
        return res
    codes, uniq = pd.factorize(cl)
    members = [np.where(codes == k)[0] for k in range(len(uniq))]
    k = len(members)
    sp, pe = [], []
    for start in range(0, nb, 250):
        b = min(250, nb - start)
        draws = rng.integers(0, k, (b, k))
        idx = [np.concatenate([members[j] for j in row]) for row in draws]
        for i in idx:
            xs, ys = x[i], y[i]
            if xs.std() == 0 or ys.std() == 0:
                continue
            pe.append(np.corrcoef(xs, ys)[0, 1])
            rx = pd.Series(xs).rank().to_numpy(); ry = pd.Series(ys).rank().to_numpy()
            sp.append(np.corrcoef(rx, ry)[0, 1])
    sp, pe = np.array(sp), np.array(pe)
    res.update(sp_lo=np.percentile(sp, 2.5), sp_hi=np.percentile(sp, 97.5), sp_se=sp.std(ddof=1),
               pe_lo=np.percentile(pe, 2.5), pe_hi=np.percentile(pe, 97.5), pe_se=pe.std(ddof=1))
    return res


def perm_p(x, y, rng, nperm=NPERM):
    """Two-sided Monte-Carlo permutation p for Spearman and Pearson (x permuted across the independent units)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    s0, p0, n = corr_pair(x, y)
    if np.isnan(s0):
        return np.nan, np.nan
    rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
    P = np.argsort(rng.random((nperm, n)), axis=1)
    sp = _corr_cols(rx[P].T, np.repeat(ry[:, None], nperm, 1))
    pe = _corr_cols(x[P].T, np.repeat(y[:, None], nperm, 1))
    ps = (1 + np.sum(np.abs(sp) >= abs(s0) - 1e-12)) / (nperm + 1)
    pp = (1 + np.sum(np.abs(pe) >= abs(p0) - 1e-12)) / (nperm + 1)
    return float(ps), float(pp)


def holm(ps):
    ps = np.asarray(ps, float)
    out = np.full(len(ps), np.nan)
    ok = np.where(np.isfinite(ps))[0]
    order = ok[np.argsort(ps[ok])]
    m = len(order); run = 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (m - i) * ps[j]))
        out[j] = run
    return out


def eta2(d, metric, key):
    """share of game-level variance of metric explained by the grouping key (ceiling on |r|^2 of any key-level predictor)"""
    x = d[[metric, key]].dropna()
    tot = ((x[metric] - x[metric].mean()) ** 2).sum()
    gm = x.groupby(key)[metric].transform("mean")
    return float(((gm - x[metric].mean()) ** 2).sum() / tot) if tot > 0 else np.nan


def residualise(df, col, design):
    """OLS residual of col on dummy-coded design columns (with intercept)."""
    X = pd.get_dummies(df[design].astype(str), drop_first=True).astype(float)
    X.insert(0, "const", 1.0)
    y = df[col].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X.to_numpy(), y, rcond=None)
    return y - X.to_numpy() @ beta
