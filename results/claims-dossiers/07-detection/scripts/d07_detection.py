"""Dossier 07, part 1: detection from quotes vs text, re-derived independently (both models).

usage: python -X utf8 d07_detection.py HACKATHON_DIR REPO_DIR OUTDIR
Reads the per-round tables (rounds.csv, messages.csv) and the Step 1 game tables (run.csv) of
Qwen3-32B (neutral run) and gpt-oss-20b (final build). Re-implements, without importing the
earlier detection code: the late-outcome label, the early quote features, TF-IDF + L2 logistic
regression, the Qwen fit/test pair split, the frozen Youden thresholds, pair-cluster bootstraps
and pair-level sign-flip permutation tests.
Unit: game. Cluster: (wording, seed) pair. Created by Claude at the prompting of the repository owner.
"""
import os, sys, re, json
import numpy as np, pandas as pd
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass

HK, REPO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
B = 2000; BOP = 1000; NPERM = 5000
RNG = np.random.default_rng(7072026)
EARLY = 3

QRUN = HK + "/work_scratch/analysis_final/steps/neutral/step1/run.csv"
QTAB = HK + "/work_scratch/analysis_final/tables_neutral_final"
ORUN = HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv"
OTAB = HK + "/work_scratch/oss_analysis/tables_t2"


# ------------------------------------------------------------------ data
def load(run_csv, tdir, model):
    run = pd.read_csv(run_csv, low_memory=False)
    run = run[(run.status == "done") & (run.in_primary == 1)]
    if "arm_build_bug" in run:
        run = run[run.arm_build_bug != 1]
    run = run.copy(); run["tid"] = run.played_trial_id.fillna(run.trial_id)
    R = pd.read_csv(tdir + "/rounds.csv", usecols=["trial_id", "round", "seat", "quote", "market_price"], low_memory=False)
    R = R[R.trial_id.isin(run.tid)]
    M = pd.read_csv(tdir + "/messages.csv", usecols=["trial_id", "round", "turn", "seat", "text", "refusal_kind"], low_memory=False)
    M = M[M.trial_id.isin(run.tid) & M.refusal_kind.isna() & M.text.notna()]
    R["lvl"] = ((R.market_price - 1.0) / 2.0).clip(0, 1)
    per = R.groupby(["trial_id", "round"]).agg(lvl=("lvl", "first"), qmin=("quote", "min"), qmax=("quote", "max")).reset_index()
    per["match"] = ((per.qmax - per.qmin) <= 0.005).astype(float)
    docs = M[M["round"] <= EARLY].sort_values(["trial_id", "round", "turn"]).groupby("trial_id").text.apply(lambda s: " ".join(s.astype(str)))
    rows = []
    for tid, g in per.groupby("trial_id"):
        g = g.sort_values("round"); e = g[g["round"] <= EARLY]; l = g[g["round"] > EARLY]
        if len(e) == 0:
            continue
        lv = e.lvl.values
        rows.append(dict(tid=tid, early_mean=lv.mean(), early_first=lv[0], early_sd=lv.std(), early_match=e.match.mean(), early_qmin=e.qmin.mean(),
                         early_trend=(lv[-1] - lv[0]) if len(lv) > 1 else 0.0, early_stab=np.mean(np.abs(np.diff(lv, prepend=lv[0])) <= 0.01),
                         late_mean=l.lvl.mean() if len(l) else np.nan, n_late=len(l)))
    F = pd.DataFrame(rows)
    keep = ["tid", "trial_id", "arm", "thinking", "wording", "seed", "penalty_point", "communication", "market_price_mean", "price_index",
            "profit_gain_index", "competitive_share", "matching_share", "price_detector_flag_any", "conversation_detector_flag_any"]
    G = run[keep].merge(F, on="tid", how="inner")
    G["doc"] = G.tid.map(docs).fillna("")
    G["model"] = model; G["pair"] = G.wording.astype(int).astype(str) + "_" + G.seed.astype(int).astype(str)
    G["y"] = (G.late_mean >= 0.5).astype(float)
    return G, R, M, run


QK = ["early_mean", "early_first", "early_sd", "early_match", "early_qmin", "early_trend", "early_stab"]


# ------------------------------------------------------------------ minimal ML (own implementation)
TOK = re.compile(r"[a-z0-9\.]+")


def grams(d):
    t = TOK.findall(d.lower()); return t + [a + "_" + b for a, b in zip(t, t[1:])]


class Tfidf:
    def fit(self, docs, max_features=500, min_df=3):
        df = {}
        for d in docs:
            for w in set(grams(d)):
                df[w] = df.get(w, 0) + 1
        voc = [w for w, c in sorted(df.items(), key=lambda kv: (-kv[1], kv[0])) if c >= min_df][:max_features]
        self.ix = {w: i for i, w in enumerate(voc)}
        self.idf = np.log((1 + len(docs)) / (1 + np.array([df[w] for w in voc], float))) + 1 if voc else np.zeros(0)
        return self

    def tx(self, docs):
        X = np.zeros((len(docs), len(self.ix)))
        for i, d in enumerate(docs):
            for w in grams(d):
                j = self.ix.get(w)
                if j is not None:
                    X[i, j] += 1
        X = np.log1p(X) * self.idf; n = np.linalg.norm(X, axis=1, keepdims=True); n[n == 0] = 1
        return 3.0 * X / n


def lr_fit(X, y, lam=1.0):
    Z = np.c_[np.ones(len(X)), X]; w = np.zeros(Z.shape[1]); P = lam * np.eye(Z.shape[1]); P[0, 0] = 0
    for _ in range(25):
        mu = 1 / (1 + np.exp(-np.clip(Z @ w, -30, 30)))
        H = (Z * (mu * (1 - mu))[:, None]).T @ Z + P + 1e-8 * np.eye(len(w))
        st = np.linalg.solve(H, Z.T @ (mu - y) + P @ w); w -= st
        if np.abs(st).max() < 1e-7:
            break
    return w


class Model:
    """kind: 'text' (TF-IDF), 'quotes' (7 standardised quote features), 'both' (both blocks)."""
    def __init__(self, kind): self.kind = kind

    def _X(self, d, fit=False):
        parts = []
        if self.kind in ("quotes", "both"):
            Q = d[QK].values.astype(float)
            if fit:
                self.mu = Q.mean(0); self.sd = Q.std(0); self.sd[self.sd == 0] = 1
            parts.append((Q - self.mu) / self.sd)
        if self.kind in ("text", "both"):
            if fit:
                self.tf = Tfidf().fit(d.doc.tolist())
            parts.append(self.tf.tx(d.doc.tolist()))
        return np.hstack(parts)

    def fit(self, d):
        y = d.y.values
        if y.min() == y.max():
            self.const = True; return self
        self.const = False; self.w = lr_fit(self._X(d, True), y); return self

    def score(self, d):
        if self.const:
            return np.zeros(len(d))
        return np.c_[np.ones(len(d)), self._X(d)] @ self.w


def oof(kind, d, k=5):
    """out-of-fold scores, folds grouped by pair (pairs dealt round-robin after a fixed shuffle)."""
    up = np.array(sorted(d.pair.unique())); np.random.default_rng(1).shuffle(up)
    fid = d.pair.map({p: i % k for i, p in enumerate(up)}).values; s = np.zeros(len(d))
    for f in range(k):
        tr, te = fid != f, fid == f
        s[te] = Model(kind).fit(d[tr]).score(d[te])
    return s


def youden(s, y):
    c = np.unique(s); best, bt = -9, c[0]
    for t in c:
        p = s >= t; j = p[y == 1].mean() - p[y == 0].mean()
        if j > best:
            best, bt = j, t
    return bt


def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y) == 1; n1 = y.sum(); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = pd.Series(s).rank().values
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def ops(s, y, t):
    p = s >= t; y1 = y == 1
    tp = (p & y1).sum(); fp = (p & ~y1).sum()
    return dict(recall=tp / max(y1.sum(), 1), fpr=fp / max((~y1).sum(), 1), precision=tp / (tp + fp) if tp + fp else np.nan, flags=int(p.sum()))


def cluster_index(pairs):
    up = sorted(set(pairs)); arr = np.asarray(pairs); return [np.where(arr == u)[0] for u in up]


def boot(fn, idx, n=B, unit="pair"):
    v = []
    for _ in range(n):
        if unit == "pair":
            ii = np.concatenate([idx[j] for j in RNG.integers(0, len(idx), len(idx))])
        else:
            m = sum(len(x) for x in idx); ii = RNG.integers(0, m, m)
        x = fn(ii)
        if x is not None and not np.isnan(x):
            v.append(x)
    v = np.array(v)
    return (np.percentile(v, 2.5), np.percentile(v, 97.5), v.std()) if len(v) else (np.nan, np.nan, np.nan)


def perm_auc_vs_half(s, y, idx, n=NPERM):
    """label permutation within the population (game level); two-sided p for AUC != 0.5."""
    a0 = abs(auc(s, y) - 0.5); c = 0
    for _ in range(n):
        c += abs(auc(s, RNG.permutation(y)) - 0.5) >= a0 - 1e-12
    return (c + 1) / (n + 1)


def perm_diff(s1, s2, y, idx, n=NPERM):
    """sign-flip over pairs: within each pair swap the (rank-normalised) scores of the two detectors."""
    r1 = pd.Series(s1).rank(pct=True).values; r2 = pd.Series(s2).rank(pct=True).values
    d0 = abs(auc(r1, y) - auc(r2, y)); c = 0
    for _ in range(n):
        a, b = r1.copy(), r2.copy()
        for ix in idx:
            if RNG.random() < 0.5:
                a[ix], b[ix] = r2[ix], r1[ix]
        c += abs(auc(a, y) - auc(b, y)) >= d0 - 1e-12
    return (c + 1) / (n + 1)


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for k, i in enumerate(o):
        run = max(run, min(1, (m - k) * ps[i])); adj[i] = run
    return adj


# ------------------------------------------------------------------ build
Q, QR, QM, Qrun = load(QRUN, QTAB, "Qwen3-32B")
O, OR_, OM, Orun = load(ORUN, OTAB, "gpt-oss-20b")
Q["mode"] = Q.thinking.map({"on": "t1", "off": "t0"}); O["mode"] = "medium"
print("games built: Qwen", len(Q), "gpt-oss", len(O), flush=True)
QT = Q[Q.arm.isin(["headline-chat", "headline-monitored"]) & (Q.n_late >= 2)].reset_index(drop=True)
pairs = sorted(set(zip(Q.wording.astype(int), Q.seed.astype(int))))
perm = np.random.default_rng(20261025).permutation(len(pairs))
fitp = {"%d_%d" % pairs[i] for i in perm[:10]}; testp = {"%d_%d" % pairs[i] for i in perm[10:]}
QF = QT[QT.pair.isin(fitp)].reset_index(drop=True); QX = QT[QT.pair.isin(testp)].reset_index(drop=True)
print("Qwen talk fit n", len(QF), "test n", len(QX), "prev test", round(QX.y.mean(), 3), flush=True)

# frozen detectors
DET = {}
thr = {"quotes: early mean level": youden(QF.early_mean.values, QF.y.values)}
for kind, nm in (("text", "text: TF-IDF + LR"), ("quotes", "quotes: quote features + LR"), ("both", "both: quote features + TF-IDF + LR")):
    thr[nm] = youden(oof(kind, QF), QF.y.values); DET[nm] = Model(kind).fit(QF)
print("frozen thresholds", {k: round(v, 3) for k, v in thr.items()}, flush=True)


def scores(d):
    S = {"quotes: early mean level": d.early_mean.values}
    for nm, m in DET.items():
        S[nm] = m.score(d)
    return S


OCHAT = sorted(set(O[O.communication == "private"].arm) - {"ctl-32b-joint", "ctl-32b-compete", "fx-ctl-joint"})
B0 = ["headline-chat", "moral-prime", "moral-prime-b", "moral-placebo", "d-cot-monitor-a", "start-5tick", "fx-chat-p1", "fx-chat-p5", "nx-chat-p1"]
QCHAT = sorted(set(Q[Q.communication.isin(["private", "monitored", "public", "unmonitored"])].arm) - {"ctl-32b-joint", "ctl-32b-compete"})
POPS = [
    ("Q-test", "Qwen3-32B: headline + monitored chat, held-out 10 pairs, thinking on and off pooled (as published)", QX),
    ("Q-test-t1", "Qwen3-32B: same held-out games, thinking on only", QX[QX.thinking == "on"]),
    ("Q-test-t0", "Qwen3-32B: same held-out games, thinking off only", QX[QX.thinking == "off"]),
    ("Q-allchat-test-t1", "Qwen3-32B: every chat arm except controls, held-out 10 pairs, thinking on", Q[Q.arm.isin(QCHAT) & (Q.n_late >= 2) & Q.pair.isin(testp) & (Q.thinking == "on")]),
    ("O-A", "gpt-oss-20b: headline-chat (headline prompt with private chat), p1/p3/p5 pooled", O[(O.arm == "headline-chat") & (O.n_late >= 2)]),
    ("O-B0", "gpt-oss-20b: 9 main chat arms (headline, moral primes x3, reasoning-monitor threat, 5-tick start, formula/no-numbers chat)", O[O.arm.isin(B0) & (O.n_late >= 2)]),
    ("O-B", "gpt-oss-20b: every private-chat arm except the instructed controls", O[O.arm.isin(OCHAT) & (O.n_late >= 2)]),
]
POPS = [(a, b, c.reset_index(drop=True)) for a, b, c in POPS]

rows, diffs, gamescores = [], [], []
for code, desc, d in POPS:
    y = d.y.values; S = scores(d); idx = cluster_index(d.pair.tolist())
    for nm, s in S.items():
        lo, hi, se = boot(lambda ii: auc(s[ii], y[ii]), idx)
        glo, ghi, _ = boot(lambda ii: auc(s[ii], y[ii]), idx, 1000, unit="game")
        o = ops(s, y, thr[nm])
        ci = {m: boot(lambda ii, m=m: ops(s[ii], y[ii], thr[nm])[m], idx, BOP)[:2] for m in ("recall", "fpr", "precision")}
        p = perm_auc_vs_half(s, y, idx, 2000)
        rows.append(dict(pop=code, population=desc, n=len(d), n_pairs=len(idx), n_pos=int(y.sum()), prevalence=y.mean(), detector=nm, auc=auc(s, y), auc_lo=lo, auc_hi=hi,
                         auc_se=se, auc_lo_gameboot=glo, auc_hi_gameboot=ghi, p_vs_chance=p, threshold=thr[nm], **o,
                         recall_lo=ci["recall"][0], recall_hi=ci["recall"][1], fpr_lo=ci["fpr"][0], fpr_hi=ci["fpr"][1], precision_lo=ci["precision"][0], precision_hi=ci["precision"][1]))
    bt = S["both: quote features + TF-IDF + LR"]
    for nm in ("quotes: early mean level", "text: TF-IDF + LR", "quotes: quote features + LR"):
        ot = S[nm]; est = auc(bt, y) - auc(ot, y); lo, hi, se = boot(lambda ii: auc(bt[ii], y[ii]) - auc(ot[ii], y[ii]), idx)
        diffs.append(dict(pop=code, population=desc, n=len(d), n_pairs=len(idx), contrast="both minus " + nm, diff=est, lo=lo, hi=hi, se=se, mde=2.8 * se,
                          p_signflip=perm_diff(bt, ot, y, idx, 2000)))
    gs = d[["model", "trial_id", "arm", "mode", "pair", "y", "early_mean", "late_mean"]].copy(); gs["pop"] = code
    for nm, s in S.items():
        gs[nm] = s
    gamescores.append(gs)
    print("done", code, len(d), flush=True)

A = pd.DataFrame(rows); D = pd.DataFrame(diffs)
# Holm family: the 4 headline detection tests (quotes vs chance, text vs chance, both-minus-quotes, both-minus-text) in 3 populations (Q-test, O-A, O-B) = 12
fam = []
for code in ("Q-test", "O-A", "O-B"):
    for nm in ("quotes: early mean level", "text: TF-IDF + LR"):
        fam.append(("auc", code, nm, A[(A["pop"] == code) & (A.detector == nm)].p_vs_chance.iloc[0]))
    for nm in ("both minus quotes: early mean level", "both minus text: TF-IDF + LR"):
        fam.append(("diff", code, nm, D[(D["pop"] == code) & (D.contrast == nm)].p_signflip.iloc[0]))
adj = holm([f[3] for f in fam])
H = pd.DataFrame([dict(kind=f[0], pop=f[1], test=f[2], p=f[3], p_holm=a) for f, a in zip(fam, adj)])
A.to_csv(OUT + "/detector_auc.csv", index=False); D.to_csv(OUT + "/detector_auc_diff.csv", index=False); H.to_csv(OUT + "/holm_detection_family.csv", index=False)
pd.concat(gamescores).to_csv(OUT + "/game_scores.csv", index=False)

# ------------------------------------------------------------------ Qwen: 30 random 10/10 pair splits (does text add on average?)
rs = []
rr = np.random.default_rng(99)
for i in range(30):
    pr = rr.permutation(len(pairs)); f = {"%d_%d" % pairs[j] for j in pr[:10]}
    df_ = QT[QT.pair.isin(f)].reset_index(drop=True); dt = QT[~QT.pair.isin(f)].reset_index(drop=True)
    sb = Model("both").fit(df_).score(dt); st = Model("text").fit(df_).score(dt)
    rs.append(dict(split=i, n_test=len(dt), auc_quotes=auc(dt.early_mean.values, dt.y.values), auc_text=auc(st, dt.y.values), auc_both=auc(sb, dt.y.values)))
RS = pd.DataFrame(rs); RS["both_minus_quotes"] = RS.auc_both - RS.auc_quotes; RS.to_csv(OUT + "/qwen_random_splits.csv", index=False)
print("random splits: mean both-quotes %.3f, share>0 %.2f" % (RS.both_minus_quotes.mean(), (RS.both_minus_quotes > 0).mean()), flush=True)

# ------------------------------------------------------------------ circularity checks
circ = []
for code, desc, d in POPS:
    e, l = d.early_mean.values, d.late_mean.values
    circ.append(dict(pop=code, n=len(d), pearson_early_late=np.corrcoef(e, l)[0, 1], spearman_early_late=np.corrcoef(pd.Series(e).rank().values, pd.Series(l).rank().values)[0, 1]))
    S = scores(d); y = d.y.values; t = thr["quotes: early mean level"]
    for side, m in (("early below threshold", e < t), ("early at or above threshold", e >= t)):
        sub = d[m].reset_index(drop=True); ys = sub.y.values
        if len(sub) < 6 or ys.min() == ys.max():
            circ.append(dict(pop=code, subset=side, n=len(sub), n_pos=int(ys.sum()), note="one class or too few")); continue
        idx = cluster_index(sub.pair.tolist()); st = S["text: TF-IDF + LR"][m]
        lo, hi, _ = boot(lambda ii: auc(st[ii], ys[ii]), idx, 1000)
        circ.append(dict(pop=code, subset=side, n=len(sub), n_pos=int(ys.sum()), text_auc_within=auc(st, ys), lo=lo, hi=hi,
                         early_mean_auc_within=auc(sub.early_mean.values, ys)))
pd.DataFrame(circ).to_csv(OUT + "/circularity_checks.csv", index=False)

# instructed label (joint vs compete): independent of both feature sets; frozen on the Qwen fit-half controls
QC = Q[Q.arm.isin(["ctl-32b-joint", "ctl-32b-compete"])].copy(); QC["y"] = (QC.arm == "ctl-32b-joint").astype(float)
qcf = QC[QC.pair.isin(fitp)].reset_index(drop=True)
OC = O[O.arm.isin(["ctl-32b-joint", "ctl-32b-compete"])].copy(); OC["y"] = (OC.arm == "ctl-32b-joint").astype(float); OC = OC.reset_index(drop=True)
ins = []
for nm, s_f, s_o in (("quotes: early mean level", qcf.early_mean.values, OC.early_mean.values),
                     ("text: TF-IDF + LR", oof("text", qcf), Model("text").fit(qcf).score(OC)),
                     ("both: quote features + TF-IDF + LR", oof("both", qcf), Model("both").fit(qcf).score(OC))):
    t = youden(s_f, qcf.y.values); ins.append(dict(population="gpt-oss-20b joint-profit vs strict-compete controls", n=len(OC), detector=nm, auc=auc(s_o, OC.y.values), **ops(s_o, OC.y.values, t)))
pd.DataFrame(ins).to_csv(OUT + "/instructed_label.csv", index=False)

# five metrics: label-positive vs label-negative games (what the label means), per population
FM = [("market_price_mean", "average absolute spread"), ("price_index", "price index"), ("profit_gain_index", "profit gain index"),
      ("competitive_share", "competitive share"), ("matching_share", "matching share")]
fm = []
for code, desc, d in POPS:
    for col, lab in FM:
        a = d[d.y == 1][col].values; b = d[d.y == 0][col].values
        idx = cluster_index(d.pair.tolist()); v = d[col].values; yy = d.y.values
        lo, hi, _ = boot(lambda ii: np.nanmean(v[ii][yy[ii] == 1]) - np.nanmean(v[ii][yy[ii] == 0]) if (yy[ii] == 1).any() and (yy[ii] == 0).any() else np.nan, idx, 1000)
        fm.append(dict(pop=code, metric=lab, n_pos=len(a), n_neg=len(b), mean_pos=np.nanmean(a), mean_neg=np.nanmean(b) if len(b) else np.nan,
                       diff=np.nanmean(a) - np.nanmean(b) if len(b) else np.nan, lo=lo, hi=hi))
pd.DataFrame(fm).to_csv(OUT + "/label_five_metrics.csv", index=False)
json.dump({k: float(v) for k, v in thr.items()}, open(OUT + "/frozen_thresholds.json", "w"), indent=1)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(A[["pop", "n", "n_pairs", "prevalence", "detector", "auc", "auc_lo", "auc_hi", "auc_lo_gameboot", "auc_hi_gameboot", "p_vs_chance", "recall", "fpr", "precision", "flags"]].round(3).to_string())
print(D.round(3).drop(columns=["population"]).to_string()); print(H.round(4).to_string())
print(pd.DataFrame(circ).round(3).to_string()); print(pd.DataFrame(ins).round(3).to_string()); print(pd.DataFrame(fm).round(3).to_string())
