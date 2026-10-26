"""Model (Layer A) vs LLM corroboration. Writes CSVs into OUT. Run: python -X utf8 corroborate.py OUT_DIR
Inputs (local, not in the repo): the gpt-oss final_t2 run.csv and tables_t2 rounds.csv; the Qwen neutral and anchored run.csv,
the Qwen formula-arm per-game metrics, and the Qwen firm-round quote tables of the comprehension audit.
"""
import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aff  # noqa: F401,E402  (CPU affinity 0xFF0)
from layer_a import solve  # noqa: E402

HK = os.environ.get("HACKATHON_DIR", os.path.join(os.path.expanduser("~"), "hackathon")).replace("\\", "/")
W = HK + "/work_scratch/"
OSS_RUN = W + "oss_analysis/step1/final_t2/run.csv"
OSS_RND = W + "oss_analysis/tables_t2/rounds.csv"
QN_RUN = W + "analysis_final/steps/neutral/step1/run.csv"
QA_RUN = W + "analysis_final/steps/anchored/step1/run.csv"
Q_FX = W + "fx_ctl_joint/final/game_metrics.csv"
Q_FR = {"neutral": W + "comprehension_audit/firmrounds_neutral.csv", "anchored": W + "comprehension_audit/firmrounds_anchored.csv"}
OUT = sys.argv[1] if len(sys.argv) > 1 else W + "model_corroboration/out"
os.makedirs(OUT, exist_ok=True)

METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share"),
           ("matching_share", "Matching share")]
FINES = {1: 100, 2: 300, 3: 500, 4: 1000, 5: 2000}
SEED, B = 20261026, 2000
rng0 = np.random.default_rng(SEED)


def theory(pp, N):
    r = solve(N=N, fine=FINES[int(pp)])
    th = r["theta_star"]
    s = r["s_star"]
    q = 100 * (1 - s / 5.0)
    pgi = (s - 1) * q / 80.0          # total profit / total monopoly profit (competitive profit 0)
    return dict(theta_star=round(th, 4), s_star=round(s, 3), fine=FINES[int(pp)], fine_ratio=r["fine_ratio"],
                composite=r["composite"], collude_pred=int(r["composite"] < 4), pgi_star=round(pgi, 4),
                delta_textbook=r["delta_textbook"], delta_phi=round(r["delta_phi"], 3), theta_hat=r["theta_hat"],
                fine_threshold=round(r["fine_threshold"], 1), pi_m=round(r["pi_m"], 3),
                comp_share_pred=0.0 if th > 0 else 1.0, match_share_pred=1.0 if th > 0 else 0.0)


def boot_ci(v, rng=None):
    rng = rng or np.random.default_rng(SEED)
    v = np.asarray(v, float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return np.nan, np.nan, np.nan, 0
    idx = rng.integers(0, len(v), (B, len(v)))
    m = v[idx].mean(1)
    return v.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5), len(v)


def paired(da, db, col):
    a = da.set_index(["wording", "seed"])[col]
    b = db.set_index(["wording", "seed"])[col]
    k = a.index.intersection(b.index)
    d = (a.loc[k].astype(float) - b.loc[k].astype(float)).values
    m, lo, hi, n = boot_ci(d)
    return m, lo, hi, n, float(a.loc[k].astype(float).mean()), float(b.loc[k].astype(float).mean())


_SIGNS = {}


def signflip_p(da, db, col):
    """Two-sided sign-flip permutation p of the mean paired difference: exact (all 2^n patterns) for n <= 20."""
    a = da.set_index(["wording", "seed"])[col]
    b = db.set_index(["wording", "seed"])[col]
    k = a.index.intersection(b.index)
    d = (a.loc[k].astype(float) - b.loc[k].astype(float)).values
    d = d[~np.isnan(d)]
    n = len(d)
    if n == 0:
        return np.nan
    obs = abs(d.mean())
    if n <= 20:
        if n not in _SIGNS:
            bits = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1).astype(np.int8)
            _SIGNS[n] = 1 - 2 * bits
        m = np.abs(_SIGNS[n] @ d) / n
        return float((m >= obs - 1e-12).mean())
    rng = np.random.default_rng(SEED)
    sg = rng.choice([-1.0, 1.0], size=(100000, n))
    return float(((np.abs(sg @ d) / n) >= obs - 1e-12).mean())


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(x, y)[0, 1])


def rank(a):
    return pd.Series(a).rank(method="average").values


def corr_with_p(x, y, nperm=5000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    rp, rs = pearson(x, y), pearson(rank(x), rank(y))
    rng = np.random.default_rng(SEED)
    cp = cs = 0
    rx = rank(x)
    for _ in range(nperm):
        yp = rng.permutation(y)
        cp += abs(pearson(x, yp)) >= abs(rp) - 1e-12
        cs += abs(pearson(rx, rank(yp))) >= abs(rs) - 1e-12
    return rp, (cp + 1) / (nperm + 1), rs, (cs + 1) / (nperm + 1), len(x)


# ------------------------------------------------------------------ load
oss = pd.read_csv(OSS_RUN, low_memory=False)
oss = oss[(oss.status == "done") & (oss.in_primary == 1)].copy()
oss_bug = oss[oss.arm_build_bug == 1].copy()
oss = oss[oss.arm_build_bug != 1].copy()
qn = pd.read_csv(QN_RUN, low_memory=False)
qn = qn[(qn.status == "done") & (qn.in_primary == 1)].copy()
qa = pd.read_csv(QA_RUN, low_memory=False)
qa = qa[qa.status == "done"].copy()   # anchored run: in_primary is 0 by contract (primary = neutral)
fx = pd.read_csv(Q_FX)
fx = fx[fx.cell.isin(["Q fx-chat-p1", "Q fx-chat-p5", "Q fx-tacit-p1", "Q nx-chat-p1", "Q nx-tacit-p1"])].copy()
fx["arm"] = fx.cell.str[2:]
fx["penalty_point"] = np.where(fx.arm.str.endswith("p5"), 5, 1)
fx["firms"] = 2
fx["thinking"] = "on"
fx = fx.rename(columns={"avg_abs_spread": "market_price_mean"})

# ------------------------------------------------------------------ 1. theory per cell (every LLM cell)
cells = []
for model, df, extra in [("gpt-oss-20b", oss, None), ("Qwen3-32B (neutral)", qn, "thinking"), ("Qwen3-32B (anchored)", qa, "thinking")]:
    g = df.groupby(["arm_family", "arm", "penalty_point", "firms", "communication", "payoff_examples"] + ([extra] if extra else []))
    for k, s in g:
        k = dict(zip(["arm_family", "arm", "penalty_point", "firms", "communication", "payoff_examples"] + ([extra] if extra else []), k))
        t = theory(k["penalty_point"], int(k["firms"]))
        row = dict(model=model, **k, n_games=len(s), **t)
        for c, _ in METRICS:
            row["obs_" + c] = s[c].astype(float).mean()
        row["gap_price_index"] = row["obs_price_index"] - t["theta_star"]
        cells.append(row)
for k, s in fx.groupby(["arm", "penalty_point"]):
    t = theory(k[1], 2)
    row = dict(model="Qwen3-32B (formula/no-numbers run)", arm_family="payoff_block", arm=k[0], penalty_point=k[1], firms=2,
               communication="tacit" if "tacit" in k[0] else "private", payoff_examples="formula" if k[0].startswith("fx") else "none",
               thinking="on", n_games=len(s), **t)
    for c, _ in METRICS:
        row["obs_" + c] = s[c].astype(float).mean()
    row["gap_price_index"] = row["obs_price_index"] - t["theta_star"]
    cells.append(row)
cells = pd.DataFrame(cells)
# arms whose instructions replace the profit objective: the profit-maximiser prediction does not apply
OBJ = {"ctl-32b-compete", "ctl-32b-joint", "ctl-14b-compete", "ctl-14b-joint", "fx-ctl-joint", "m-inc-joint", "m-inc-target"}
cells["objective_changed"] = cells.arm.isin(OBJ).astype(int)
cells.to_csv(os.path.join(OUT, "cells_theory_vs_observed.csv"), index=False)

# theory curve at all five points and N = 2, 3
tc = pd.DataFrame([dict(N=N, penalty_point=p, **theory(p, N)) for N in (2, 3) for p in (1, 2, 3, 4, 5)])
tc.to_csv(os.path.join(OUT, "theory_curve.csv"), index=False)

# ------------------------------------------------------------------ 2. contrasts with paired CIs
contr = []


def add(model, label, da, db, ta, tb, note=""):
    for c, name in METRICS:
        m, lo, hi, n, ma, mb = paired(da, db, c)
        pv = signflip_p(da, db, c)
        key = {"market_price_mean": "s_star", "price_index": "theta_star", "profit_gain_index": "pgi_star",
               "competitive_share": "comp_share_pred", "matching_share": "match_share_pred"}[c]
        contr.append(dict(model=model, contrast=label, metric=name, n_pairs=n, mean_arm=ma, mean_control=mb, diff=m, lo=lo, hi=hi, signflip_p=pv,
                          theory_arm=ta[key], theory_control=tb[key], theory_diff=ta[key] - tb[key], note=note))


def cell(df, arm, pp, thinking=None):
    s = df[(df.arm == arm) & (df.penalty_point == pp)]
    if thinking is not None:
        s = s[s.thinking == thinking]
    return s


T = {(p, N): theory(p, N) for p in (1, 3, 4, 5) for N in (2, 3)}
# gpt-oss penalty
for arm in ("headline-chat", "headline-tacit"):
    for p in (3, 5):
        if len(cell(oss, arm, p)):
            add("gpt-oss-20b", "%s p%d - p1" % (arm, p), cell(oss, arm, p), cell(oss, arm, 1), T[(p, 2)], T[(1, 2)])
add("gpt-oss-20b", "headline-chat p5 - p3", cell(oss, "headline-chat", 5), cell(oss, "headline-chat", 3), T[(5, 2)], T[(3, 2)])
add("gpt-oss-20b", "fx-chat (formula) p5 - p1", cell(oss, "fx-chat-p5", 5), cell(oss, "fx-chat-p1", 1), T[(5, 2)], T[(1, 2)])
# gpt-oss N
add("gpt-oss-20b", "n3-group - headline-chat (p3)", cell(oss, "n3-group", 3), cell(oss, "headline-chat", 3), T[(3, 3)], T[(3, 2)])
add("gpt-oss-20b", "n3-ethics - m-asym (p3)", cell(oss, "n3-ethics", 3), cell(oss, "m-asym", 3), T[(3, 3)], T[(3, 2)])
# gpt-oss sensitivity: build-bug replicates pooled (they played the headline prompt)
pool = pd.concat([oss, oss_bug.assign(arm=oss_bug.headline_replicate_of.str.split("__").str[0])])
pool5 = pool[(pool.arm == "headline-chat") & (pool.penalty_point == 5)]
pool1 = pool[(pool.arm == "headline-chat") & (pool.penalty_point == 1)]
# replicate seeds duplicate the headline (wording, seed) keys; average replicates within a key
pool5 = pool5.groupby(["wording", "seed"], as_index=False)[[c for c, _ in METRICS]].mean()
pool1 = pool1.groupby(["wording", "seed"], as_index=False)[[c for c, _ in METRICS]].mean()
add("gpt-oss-20b", "headline-chat p5 - p1 (sensitivity: build-bug replicates averaged in)", pool5, pool1, T[(5, 2)], T[(1, 2)],
    "replicates of the same (wording, seed) are averaged before pairing")
# Qwen penalty and N, per thinking mode
for th in ("on", "off"):
    for arm in ("headline-chat", "headline-tacit", "headline-monitored"):
        for p in (3, 4, 5):
            add("Qwen3-32B t%s" % ("1" if th == "on" else "0"), "%s p%d - p1" % (arm, p), cell(qn, arm, p, th), cell(qn, arm, 1, th),
                T[(p, 2)], T[(1, 2)])
        add("Qwen3-32B t%s" % ("1" if th == "on" else "0"), "%s p5 - p4" % arm, cell(qn, arm, 5, th), cell(qn, arm, 4, th), T[(5, 2)], T[(4, 2)])
    add("Qwen3-32B t%s" % ("1" if th == "on" else "0"), "n3-group - headline-chat (p3)", cell(qn, "n3-group", 3, th),
        cell(qn, "headline-chat", 3, th), T[(3, 3)], T[(3, 2)])
    add("Qwen3-32B t%s" % ("1" if th == "on" else "0"), "n3-ethics - m-asym (p3)", cell(qn, "n3-ethics", 3, th), cell(qn, "m-asym", 3, th),
        T[(3, 3)], T[(3, 2)])
add("Qwen3-32B t1", "fx-chat (formula) p5 - p1", cell(fx, "fx-chat-p5", 5), cell(fx, "fx-chat-p1", 1), T[(5, 2)], T[(1, 2)])
contr = pd.DataFrame(contr)
contr["share_of_theory"] = contr["diff"] / contr["theory_diff"].where(contr["theory_diff"].abs() > 1e-9)
# Holm within named families, per model and metric (exploratory families, see the report)
FAM = {"penalty": lambda c: (" p" in c) and ("sensitivity" not in c), "firms": lambda c: c.startswith("n3-")}
contr["family"] = [next((f for f, fn in FAM.items() if fn(c)), "sensitivity") for c in contr.contrast]
contr["holm_p"] = np.nan
for (mdl, met, fam), g in contr.groupby(["model", "metric", "family"]):
    if fam == "sensitivity":
        continue
    order = g.signflip_p.sort_values().index
    m_ = len(order)
    run = 0.0
    for i, ix in enumerate(order):
        run = max(run, min(1.0, (m_ - i) * contr.at[ix, "signflip_p"]))
        contr.at[ix, "holm_p"] = run
contr.to_csv(os.path.join(OUT, "contrasts_paired.csv"), index=False)

# ------------------------------------------------------------------ 3. correlation of observed price index with theta* across games
cor = []
def addcor(model, label, s, N=None):
    th = [theory(p, int(n))["theta_star"] for p, n in zip(s.penalty_point, s.firms)]
    rp, pp_, rs, ps, n = corr_with_p(th, s.price_index.astype(float))
    cor.append(dict(model=model, games=label, n_games=n, pearson=rp, pearson_p=pp_, spearman=rs, spearman_p=ps))

hd = oss[oss.arm.isin(["headline-chat", "headline-tacit"])]
addcor("gpt-oss-20b", "headline-chat (p1, p3, p5)", oss[oss.arm == "headline-chat"])
addcor("gpt-oss-20b", "headline-tacit (p1, p5)", oss[oss.arm == "headline-tacit"])
addcor("gpt-oss-20b", "headline chat + tacit pooled", hd)
addcor("gpt-oss-20b", "fx-chat formula (p1, p5)", oss[oss.arm.isin(["fx-chat-p1", "fx-chat-p5"])])
for th in ("on", "off"):
    for arm in ("headline-chat", "headline-tacit", "headline-monitored"):
        addcor("Qwen3-32B t%s" % ("1" if th == "on" else "0"), "%s (p1, p3, p4, p5)" % arm, qn[(qn.arm == arm) & (qn.thinking == th)])
addcor("Qwen3-32B t1", "fx-chat formula (p1, p5)", fx[fx.arm.isin(["fx-chat-p1", "fx-chat-p5"])])
cor = pd.DataFrame(cor)
cor.to_csv(os.path.join(OUT, "correlations_theta_vs_price_index.csv"), index=False)

# ------------------------------------------------------------------ 4. do quotes sit at the theory price s*?
def near(q, x, tol=0.02):
    return (np.abs(q - x) <= tol + 1e-9).mean()

near_rows = []
# Qwen anchored vs neutral, firm-round quotes, headline arms
for view, p in Q_FR.items():
    f = pd.read_csv(p, usecols=["trial", "arm", "mode", "round", "quote"])
    f = f[f.arm.isin(["headline-chat", "headline-tacit", "headline-monitored"]) & f.quote.notna()]
    f["pp"] = f.trial.str.split("__").str[1].str[1].astype(int)
    for (mode, pp), s in f.groupby(["mode", "pp"]):
        t = theory(pp, 2)
        q = s.quote.astype(float).values
        near_rows.append(dict(model="Qwen3-32B", view=view, thinking=mode, penalty_point=pp, s_star=t["s_star"], n_quotes=len(q),
                              share_within_2ticks_of_s_star=near(q, t["s_star"]), share_exact_2_09=near(q, 2.09, 0.005),
                              share_exact_2_50=near(q, 2.50, 0.005), share_exact_2_49=near(q, 2.49, 0.005),
                              share_exact_3_00=near(q, 3.00, 0.005), mean_quote=q.mean()))
# gpt-oss neutral and formula
rnd = pd.read_csv(OSS_RND, usecols=["trial_id", "seat", "quote", "imputed"])
rnd = rnd[rnd.seat.str.startswith("llm") & (rnd.imputed == 0) & rnd.quote.notna()]
idmap = dict(zip(oss.played_trial_id.fillna(oss.trial_id), zip(oss.arm, oss.penalty_point)))
rnd = rnd[rnd.trial_id.isin(idmap)]
rnd["arm"] = rnd.trial_id.map(lambda x: idmap[x][0])
rnd["pp"] = rnd.trial_id.map(lambda x: idmap[x][1])
for (arm, pp), s in rnd[rnd.arm.isin(["headline-chat", "headline-tacit", "fx-chat-p1", "fx-chat-p5", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1"])].groupby(["arm", "pp"]):
    t = theory(pp, 2)
    q = s.quote.astype(float).values
    near_rows.append(dict(model="gpt-oss-20b", view="formula" if arm.startswith("fx") else ("none" if arm.startswith("nx") else "neutral"),
                          thinking="medium", arm=arm, penalty_point=pp, s_star=t["s_star"], n_quotes=len(q),
                          share_within_2ticks_of_s_star=near(q, t["s_star"]), share_exact_2_09=near(q, 2.09, 0.005),
                          share_exact_2_50=near(q, 2.50, 0.005), share_exact_2_49=near(q, 2.49, 0.005),
                          share_exact_3_00=near(q, 3.00, 0.005), mean_quote=q.mean()))
near_df = pd.DataFrame(near_rows)
near_df.to_csv(os.path.join(OUT, "quotes_at_theory_price.csv"), index=False)

# Qwen anchored minus neutral, paired per game, headline arms: |game price - s*| and the price index
an = []
for th in ("on", "off"):
    for p in (1, 3, 4, 5):
        t = theory(p, 2)
        for arm in ("headline-chat", "headline-tacit", "headline-monitored"):
            a = cell(qa, arm, p, th).copy()
            n = cell(qn, arm, p, th).copy()
            for d_ in (a, n):
                d_["abs_gap_to_s_star"] = (d_.market_price_mean.astype(float) - t["s_star"]).abs()
            for col in ("abs_gap_to_s_star", "market_price_mean", "price_index"):
                m, lo, hi, k, ma, mb = paired(a, n, col)
                an.append(dict(thinking=th, penalty_point=p, arm=arm, s_star=t["s_star"], metric=col, n_pairs=k,
                               anchored=ma, neutral=mb, diff_anchored_minus_neutral=m, lo=lo, hi=hi))
an = pd.DataFrame(an)
an.to_csv(os.path.join(OUT, "qwen_anchored_minus_neutral.csv"), index=False)
# pooled over the three headline arms (pairs = arm x wording x seed)
pooled = []
for th in ("on", "off"):
    for p in (1, 3, 4, 5):
        t = theory(p, 2)
        a = qa[(qa.arm.str.startswith("headline")) & (qa.penalty_point == p) & (qa.thinking == th)].copy()
        n = qn[(qn.arm.str.startswith("headline")) & (qn.penalty_point == p) & (qn.thinking == th)].copy()
        for d_ in (a, n):
            d_["abs_gap_to_s_star"] = (d_.market_price_mean.astype(float) - t["s_star"]).abs()
            d_["wording"] = d_.arm + "|" + d_.wording.astype(str)
        for col in ("abs_gap_to_s_star", "market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"):
            m, lo, hi, k, ma, mb = paired(a, n, col)
            pooled.append(dict(thinking=th, penalty_point=p, s_star=t["s_star"], metric=col, n_pairs=k, anchored=ma, neutral=mb,
                               diff=m, lo=lo, hi=hi, signflip_p_mc100k=signflip_p(a, n, col)))
pd.DataFrame(pooled).to_csv(os.path.join(OUT, "qwen_anchored_minus_neutral_pooled.csv"), index=False)

with open(os.path.join(OUT, "provenance.json"), "w") as f:
    json.dump(dict(oss_run="gpt-oss Step 1 run table, tier t2 (local, not in the repo)", oss_games=len(oss), oss_bug_games=len(oss_bug), qwen_neutral_games=len(qn),
                   qwen_anchored_games=len(qa), qwen_fx_games=len(fx), seed=SEED, bootstrap=B), f, indent=1)
print("done", OUT)
