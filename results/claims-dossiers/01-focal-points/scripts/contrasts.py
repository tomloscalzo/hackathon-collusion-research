"""Dossier 01 (focal points): paired contrasts, quote shares, confound checks.
Input: data/games.csv and data/quotes_long.csv.gz written by extract_games.py (validated against run.csv).
Output: CSVs in tables/. Usage: python -X utf8 contrasts.py <dossier_dir>
Correlations: Spearman and Pearson with two-sided permutation p (10,000 shuffles).
Statistics: unit = game, paired on (wording, seed); 95% percentile bootstrap over pairs (10,000 resamples, seed 20261025);
exact sign-flip permutation p over pairs (all 2^n sign patterns, n <= 20); Holm within named families; MDE = 2.8 x SE.
"""
import os, sys, itertools
try:
    import psutil
    psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np, pandas as pd


def _rank(x):
    return pd.Series(x).rank().values


def _r(x, y):
    x = x - x.mean(); y = y - y.mean()
    den = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / den) if den > 0 else np.nan


def _perm_p(x, y, r, B=10000):
    rng = np.random.default_rng(7)
    c = np.array([_r(x, rng.permutation(y)) for _ in range(B)])
    return float((np.sum(np.abs(c) >= abs(r) - 1e-12) + 1) / (B + 1))

D = sys.argv[1]
G = pd.read_csv(os.path.join(D, "data", "games.csv"))
T = os.path.join(D, "tables"); os.makedirs(T, exist_ok=True)
MET = ["avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
RNG = np.random.default_rng(20261025)
OSS, QW = "gpt-oss-20b", "Qwen3-32B"
G = G[~((G.model == OSS) & (G.arm.isin(["n3-cheater"])))]
_SIGNS = {}


def signs(n):
    if n not in _SIGNS:
        _SIGNS[n] = np.array(list(itertools.product([1.0, -1.0], repeat=n)), dtype=np.float32)
    return _SIGNS[n]


def exact_p(d):
    d = np.asarray(d, float)
    n = len(d)
    if n == 0 or np.allclose(d, 0):
        return 1.0
    obs = abs(d.mean())
    s = signs(n)
    m = np.abs(s @ d.astype(np.float32)) / n
    return float(np.mean(m >= obs - 1e-9))


def boot(d, B=10000):
    d = np.asarray(d, float)
    idx = RNG.integers(0, len(d), (B, len(d)))
    ms = d[idx].mean(1)
    return np.percentile(ms, 2.5), np.percentile(ms, 97.5)


def holm(ps):
    ps = np.asarray(ps, float); n = len(ps); o = np.argsort(ps); adj = np.empty(n); run = 0
    for i, k in enumerate(o):
        run = max(run, min(1, (n - i) * ps[k])); adj[k] = run
    return adj


def sel(model, arm, pp, th, run=None):
    s = G[(G.model == model) & (G.arm == arm) & (G.penalty_point == pp) & (G.thinking == th)]
    if run:
        s = s[s.run == run]
    return s.set_index(["wording", "seed"])


def paired(model, a, b, family, label, pool=False):
    """a, b = (arm, pp, thinking[, run]); pool = list of penalty points to average within pair first."""
    out = []
    if pool:
        A = pd.concat([sel(model, a[0], p, a[2], a[3] if len(a) > 3 else None)[MET] for p in pool]).groupby(level=[0, 1]).mean()
        Bq = pd.concat([sel(model, b[0], p, b[2], b[3] if len(b) > 3 else None)[MET] for p in pool]).groupby(level=[0, 1]).mean()
    else:
        A = sel(model, *a)[MET]; Bq = sel(model, *b)[MET]
    j = A.join(Bq, lsuffix="_a", rsuffix="_b", how="inner")
    for m in MET:
        d = (j[m + "_a"] - j[m + "_b"]).dropna().values
        lo, hi = boot(d)
        se = d.std(ddof=1) / np.sqrt(len(d))
        out.append(dict(family=family, model=model, contrast=label, metric=m, n_pairs=len(d), mean_arm=j[m + "_a"].mean(),
                        mean_control=j[m + "_b"].mean(), diff=d.mean(), lo=lo, hi=hi, p_exact=exact_p(d), mde=2.8 * se))
    return out


rows = []
# ---- Family A (G-payoff, H1): no printed example prices vs printed (neutral table), per model and thinking mode
for th in ("on",):
    for arm, ctl, pp in (("fx-chat-p1", "headline-chat", 1), ("fx-tacit-p1", "headline-tacit", 1), ("nx-chat-p1", "headline-chat", 1),
                         ("nx-tacit-p1", "headline-tacit", 1), ("fx-chat-p5", "headline-chat", 5)):
        rows += paired(OSS, (arm, pp, th, "2026-10-26_trackm_oss_formula_fix"), (ctl, pp, th), "A-oss", f"{arm} - {ctl} p{pp}")
for th in ("on", "off"):
    for arm, ctl, pp in (("fx-chat-p1", "headline-chat", 1), ("fx-tacit-p1", "headline-tacit", 1), ("nx-chat-p1", "headline-chat", 1),
                         ("nx-tacit-p1", "headline-tacit", 1), ("fx-chat-p5", "headline-chat", 5)):
        if arm == "fx-chat-p5" and th == "off":
            continue
        rows += paired(QW, (arm, pp, th, "2026-10-25_trackm_formula"), (ctl, pp, th, "qwen_neutral"), "A-qwen", f"{arm} - {ctl} p{pp} (thinking {th})")
# ---- A-drift (sensitivity): against the same-day replicate of the printed-number cell (hrep = neutral table, played later)
for arm, pp in (("fx-chat-p1", 1), ("fx-tacit-p1", 1), ("nx-chat-p1", 1), ("nx-tacit-p1", 1), ("fx-chat-p5", 5)):
    rows += paired(OSS, (arm, pp, "on", "2026-10-26_trackm_oss_formula_fix"), ("hrep-" + arm, pp, "on"), "A-oss-vs-replicate", f"{arm} - hrep-{arm} (printed-number replicate)")
for arm, pp in (("fx-chat-p1", 1), ("fx-tacit-p1", 1), ("nx-chat-p1", 1), ("nx-tacit-p1", 1), ("fx-chat-p5", 5)):
    ctl = "headline-chat" if "chat" in arm else "headline-tacit"
    rows += paired(OSS, ("hrep-" + arm, pp, "on"), (ctl, pp, "on"), "R-oss-drift", f"hrep-{arm} - {ctl} p{pp} (same prompt, same time, replicate)")
# ---- formula vs none (exploratory)
rows += paired(OSS, ("fx-chat-p1", 1, "on"), ("nx-chat-p1", 1, "on"), "F-oss", "fx-chat-p1 - nx-chat-p1")
rows += paired(OSS, ("fx-tacit-p1", 1, "on"), ("nx-tacit-p1", 1, "on"), "F-oss", "fx-tacit-p1 - nx-tacit-p1")
for th in ("on", "off"):
    rows += paired(QW, ("fx-chat-p1", 1, th), ("nx-chat-p1", 1, th), "F-qwen", f"fx-chat-p1 - nx-chat-p1 (thinking {th})")
    rows += paired(QW, ("fx-tacit-p1", 1, th), ("nx-tacit-p1", 1, th), "F-qwen", f"fx-tacit-p1 - nx-tacit-p1 (thinking {th})")
# ---- Family J (G-fxjoint): capability check, thinking on
for model, ctl_run in ((OSS, None), (QW, "qwen_neutral")):
    fam = "J-oss" if model == OSS else "J-qwen"
    rows += paired(model, ("fx-ctl-joint", 3, "on"), ("fx-chat-p1", 1, "on"), fam, "fx-ctl-joint p3 - fx-chat-p1 p1")
    rows += paired(model, ("fx-ctl-joint", 3, "on"), ("headline-chat", 3, "on", ctl_run), fam, "fx-ctl-joint p3 - headline-chat p3")
    rows += paired(model, ("fx-ctl-joint", 3, "on"), ("ctl-32b-joint", 3, "on", ctl_run), fam, "fx-ctl-joint p3 - ctl-32b-joint p3")
# ---- Family N (Q2-anchor, H3): Qwen neutral minus anchored, pooled over penalty points 1,3,4,5 within pair
for th in ("off", "on"):
    for arm in ("headline-tacit", "headline-chat", "headline-monitored"):
        rows += paired(QW, (arm, 0, th, "qwen_neutral"), (arm, 0, th, "qwen_anchored"), "N-qwen", f"{arm} neutral - anchored (thinking {th})", pool=[1, 3, 4, 5])
R = pd.DataFrame(rows)
R["p_holm"] = np.nan
for (fam, m), idx in R.groupby(["family", "metric"]).groups.items():
    R.loc[idx, "p_holm"] = holm(R.loc[idx, "p_exact"].values)
R["family_size"] = R.groupby(["family", "metric"]).contrast.transform("count")
R.to_csv(os.path.join(T, "paired_contrasts.csv"), index=False, float_format="%.4f")

# ---- cell means (all five metrics)
cm = G.groupby(["model", "run", "arm", "penalty_point", "thinking"])[MET + ["prompt_tokens_r1"]].agg(["mean", "count"])
cm.columns = ["%s_%s" % c for c in cm.columns]
cm.reset_index().to_csv(os.path.join(T, "cell_means.csv"), index=False, float_format="%.4f")

# ---- quote shares (G-focal, H2), per game then mean over games with bootstrap over games
QS = [c for c in G.columns if c.startswith("q_") and c != "q_n_quotes"]


def gmean(s):
    v = s.dropna().values
    lo, hi = boot(v) if len(v) > 1 else (np.nan, np.nan)
    return v.mean(), lo, hi


srows = []
cells = [(OSS, None, a, p) for a, p in (("headline-chat", 1), ("headline-chat", 3), ("headline-chat", 5), ("headline-tacit", 1), ("headline-tacit", 5),
                                         ("ctl-32b-joint", 3), ("fx-chat-p1", 1), ("fx-tacit-p1", 1), ("fx-chat-p5", 5), ("nx-chat-p1", 1), ("nx-tacit-p1", 1), ("fx-ctl-joint", 3))]
for th in ("on", "off"):
    for run in ("qwen_neutral", "qwen_anchored"):
        for a in ("headline-chat", "headline-tacit", "headline-monitored"):
            for p in (1, 3, 4, 5):
                cells.append((QW, run, a, p, th))
    for a, p in (("fx-chat-p1", 1), ("fx-tacit-p1", 1), ("nx-chat-p1", 1), ("nx-tacit-p1", 1), ("fx-chat-p5", 5), ("fx-ctl-joint", 3), ("ctl-32b-joint", 3)):
        cells.append((QW, "qwen_neutral" if a == "ctl-32b-joint" else None, a, p, th))
for c in cells:
    model, run, a, p = c[:4]; th = c[4] if len(c) > 4 else "on"
    s = G[(G.model == model) & (G.arm == a) & (G.penalty_point == p) & (G.thinking == th)]
    if model == OSS and a.startswith(("fx-chat", "fx-tacit", "nx-")):
        s = s[s.run == "2026-10-26_trackm_oss_formula_fix"]
    if run:
        s = s[s.run == run]
    if s.empty:
        continue
    r = dict(model=model, run=run or s.run.iloc[0], arm=a, penalty_point=p, thinking=th, n_games=len(s), n_quotes=int(s.q_n_quotes.sum()))
    for k in QS:
        m_, lo, hi = gmean(s[k]); r[k[2:]] = m_; r[k[2:] + "_lo"] = lo; r[k[2:] + "_hi"] = hi
    srows.append(r)
S = pd.DataFrame(srows)
S.to_csv(os.path.join(T, "quote_shares_by_cell.csv"), index=False, float_format="%.4f")
# pooled headline shares (the "about 80%" figure): Qwen neutral headline arms, all points, by mode and both modes
pool = []
for model, run, ths in ((QW, "qwen_neutral", ("on", "off")), (QW, "qwen_anchored", ("on", "off")), (OSS, "2026-10-26_trackm_oss_neutral", ("on",))):
    for th in list(ths) + ["both"]:
        s = G[(G.model == model) & (G.run == run) & G.arm.str.startswith("headline")]
        if th != "both":
            s = s[s.thinking == th]
        if s.empty:
            continue
        for k in ("q_exact", "q_under1to3", "q_at_2.09", "q_at_2.50", "q_at_2.49", "q_at_2.00", "q_at_3.00", "q_floor", "q_mult05"):
            m_, lo, hi = gmean(s[k])
            Q = (s[k] * s.q_n_quotes).sum() / s.q_n_quotes.sum()
            pool.append(dict(model=model, run=run, thinking=th, share=k[2:], mean_of_games=m_, lo=lo, hi=hi, pooled_over_quotes=Q, n_games=len(s), n_quotes=int(s.q_n_quotes.sum())))
pd.DataFrame(pool).to_csv(os.path.join(T, "quote_shares_pooled.csv"), index=False, float_format="%.4f")

# ---- paired quote-share contrasts: oss no-numbers / formula minus printed, and oss vs Qwen descriptive
qrows = []
for arm, ctl, pp in (("nx-chat-p1", "headline-chat", 1), ("fx-chat-p1", "headline-chat", 1), ("nx-tacit-p1", "headline-tacit", 1), ("fx-tacit-p1", "headline-tacit", 1)):
    A = sel(OSS, arm, pp, "on", "2026-10-26_trackm_oss_formula_fix"); B = sel(OSS, ctl, pp, "on")
    j = A.join(B, lsuffix="_a", rsuffix="_b", how="inner")
    for k in ("q_exact", "q_under1to3", "q_within1"):
        d = (j[k + "_a"] - j[k + "_b"]).dropna().values
        lo, hi = boot(d)
        qrows.append(dict(model=OSS, contrast=f"{arm} - {ctl} p{pp}", share=k[2:], n_pairs=len(d), diff=d.mean(), lo=lo, hi=hi, p_exact=exact_p(d)))
Qd = pd.DataFrame(qrows); Qd["p_holm"] = holm(Qd.p_exact.values); Qd["family_size"] = len(Qd)
Qd.to_csv(os.path.join(T, "quote_share_paired.csv"), index=False, float_format="%.4f")

# ---- most common quotes per key cell (from the long quote table)
L = pd.read_csv(os.path.join(D, "data", "quotes_long.csv.gz"))
top = []
for (model, run, arm, pp, th), s in L.groupby(["model", "run", "arm", "penalty_point", "thinking"]):
    vc = s.quote.round(2).value_counts(normalize=True).head(6)
    top.append(dict(model=model, run=run, arm=arm, penalty_point=pp, thinking=th, n_quotes=len(s),
                    top_quotes="; ".join("%.2f (%.0f%%)" % (k, 100 * v) for k, v in vc.items())))
pd.DataFrame(top).to_csv(os.path.join(T, "top_quotes.csv"), index=False)

# ---- chance baseline for 'one to three ticks under': the same rule against a shifted, unprinted grid (+0.25)
SHIFT = [1.25, 1.75, 2.25, 2.74, 2.75, 3.25, 3.75]
def under_grid(v, grid):
    if any(abs(v - g) < 0.005 for g in grid):
        return False
    return any(round((g - v) * 100) in (1, 2, 3) for g in grid)
cb = []
for (model, run, arm, pp, th), s in L.groupby(["model", "run", "arm", "penalty_point", "thinking"]):
    if arm not in ("headline-chat", "headline-tacit", "nx-chat-p1", "nx-tacit-p1", "fx-chat-p1", "fx-tacit-p1"):
        continue
    if run == "qwen_anchored":
        continue
    v = s.quote.round(2).values
    cb.append(dict(model=model, run=run, arm=arm, penalty_point=pp, thinking=th, n_quotes=len(v),
                   on_shifted_grid=np.mean([any(abs(x - g) < 0.005 for g in SHIFT) for x in v]),
                   under1to3_shifted_grid=np.mean([under_grid(x, SHIFT) for x in v])))
pd.DataFrame(cb).to_csv(os.path.join(T, "under_ticks_chance_baseline.csv"), index=False, float_format="%.4f")

# ---- confound: prompt length (round-1 quote prompt, input tokens) by arm; correlation with price index
pl = G.groupby(["model", "arm", "penalty_point", "thinking"]).agg(prompt_tokens_mean=("prompt_tokens_r1", "mean"), prompt_tokens_min=("prompt_tokens_r1", "min"),
                                                                 prompt_tokens_max=("prompt_tokens_r1", "max"), price_index=("price_index", "mean"), n=("price_index", "size")).reset_index()
pl = pl[pl.arm.isin(["headline-chat", "headline-tacit", "fx-chat-p1", "fx-tacit-p1", "fx-chat-p5", "nx-chat-p1", "nx-tacit-p1", "fx-ctl-joint", "ctl-32b-joint"])]
pl.to_csv(os.path.join(T, "prompt_length_by_arm.csv"), index=False, float_format="%.2f")
cor = []
def corr(x, y, label, model):
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    rx, ry = _rank(x), _rank(y)
    rs = _r(rx, ry); rp = _r(x, y); ps = _perm_p(rx, ry, rs); pp_ = _perm_p(x, y, rp)
    cor.append(dict(model=model, what=label, n=len(x), spearman=rs, spearman_p=ps, pearson=rp, pearson_p=pp_))
for model in (OSS, QW):
    # within the printed-number control cells: does a longer prompt (wording) go with a different price?
    s = G[(G.model == model) & G.arm.isin(["headline-chat", "headline-tacit"]) & (G.penalty_point == 1) & (G.thinking == "on")]
    if model == QW:
        s = s[s.run == "qwen_neutral"]
    for arm, ss in s.groupby("arm"):
        corr(ss.prompt_tokens_r1.values.astype(float), ss.price_index.values, f"{arm} p1: prompt tokens vs price index, across games (wording varies)", model)
    # across the no-printed-number and printed cells at p1: prompt tokens vs price index
    s2 = G[(G.model == model) & G.arm.isin(["headline-chat", "headline-tacit", "fx-chat-p1", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1"]) & (G.penalty_point == 1) & (G.thinking == "on")]
    s2 = s2[s2.run.isin(["qwen_neutral", "2026-10-25_trackm_formula", "2026-10-26_trackm_oss_neutral", "2026-10-26_trackm_oss_formula_fix"])]
    s2 = s2[~s2.arm.str.startswith("hrep")]
    corr(s2.prompt_tokens_r1.values.astype(float), s2.price_index.values, "p1 printed / formula / none cells pooled: prompt tokens vs price index", model)
    # game-level: share of quotes exactly on a printed number vs price index, printed-number headline games
    s3 = G[(G.model == model) & G.arm.str.startswith("headline") & (G.thinking == "on")]
    if model == QW:
        s3 = s3[s3.run == "qwen_neutral"]
    corr(s3.q_exact.values, s3.price_index.values, "headline games (printed numbers): share of quotes exactly on a printed number vs price index", model)
    corr(s3.q_exact.values, s3.profit_gain_index.values, "headline games (printed numbers): share exactly on a printed number vs profit gain index", model)
    corr(s3.q_exact.values, s3.competitive_share.values, "headline games (printed numbers): share exactly on a printed number vs competitive share", model)
pd.DataFrame(cor).to_csv(os.path.join(T, "correlations.csv"), index=False, float_format="%.4f")

# ---- reasoning passages that evaluate the demand formula with numbers (keyword count, unvalidated)
fr = G[G.thinking == "on"].groupby(["model", "arm", "penalty_point"]).apply(
    lambda s: pd.Series(dict(n_games=len(s), passages=s.reasoning_passages.sum(), formula_eval=s.formula_eval_passages.sum(),
                             share=s.formula_eval_passages.sum() / max(1, s.reasoning_passages.sum())))).reset_index()
fr = fr[fr.arm.isin(["headline-chat", "headline-tacit", "fx-chat-p1", "fx-tacit-p1", "fx-chat-p5", "nx-chat-p1", "nx-tacit-p1", "fx-ctl-joint", "ctl-32b-joint"])]
fr.to_csv(os.path.join(T, "formula_use_in_reasoning.csv"), index=False, float_format="%.4f")
print(R[R.metric.isin(["price_index", "profit_gain_index"])][["family", "model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi", "p_exact", "p_holm", "mde"]].to_string())

# ---- build-uncertainty checks (gpt-oss): arm minus the MEAN of both printed-number controls (headline cell and its
# same-time replicate hrep-*), and the same excluding games with any truncated call (truncations > 0) in arm or controls
rb = []
O = G[G.model == OSS]
for arm, ctl, pp in (("fx-tacit-p1", "headline-tacit", 1), ("fx-chat-p1", "headline-chat", 1), ("fx-chat-p5", "headline-chat", 5),
                     ("nx-tacit-p1", "headline-tacit", 1), ("nx-chat-p1", "headline-chat", 1)):
    for notr in (False, True):
        A = O[(O.arm == arm) & (O.run == "2026-10-26_trackm_oss_formula_fix")]
        C1 = O[(O.arm == ctl) & (O.penalty_point == pp)]
        C2 = O[O.arm == "hrep-" + arm]
        if notr:
            A, C1, C2 = A[A.truncations == 0], C1[C1.truncations == 0], C2[C2.truncations == 0]
        A, C1, C2 = [x.set_index(["wording", "seed"]) for x in (A, C1, C2)]
        for label, Cx in (("mean of both printed controls", None), ("headline control only", C1)):
            for m in MET:
                if Cx is None:
                    j = A[[m]].join(C1[[m]].rename(columns={m: "c1"}), how="inner").join(C2[[m]].rename(columns={m: "c2"}), how="inner")
                    d = (j[m] - (j.c1 + j.c2) / 2).values
                else:
                    j = A[[m]].join(Cx[[m]].rename(columns={m: "c1"}), how="inner"); d = (j[m] - j.c1).values
                if len(d) < 2:
                    continue
                lo, hi = boot(d)
                rb.append(dict(arm=arm, control=label, excl_truncated=notr, metric=m, n_pairs=len(d), diff=d.mean(), lo=lo, hi=hi, p_exact=exact_p(d)))
pd.DataFrame(rb).to_csv(os.path.join(T, "build_uncertainty_checks.csv"), index=False, float_format="%.4f")
