"""Detection transfer: apply the Qwen3-32B FROZEN detectors (detect_frozen.py, final neutral run, primary seed split) to gpt-oss-20b games.
Nothing is refit on gpt-oss for the main results: the Qwen fit half supplies thresholds and the fitted text / quote models; gpt-oss games are test data.
Run: python -I -X utf8 detection_transfer.py   (numpy + pandas only)"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np, pandas as pd
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
AF = Path((_HK + "/work_scratch/analysis_final"))
sys.path.insert(0, str(AF / "detect_frozen")); sys.path.insert(0, str(AF / "extra_detect"))
import detect2 as d2, detect_frozen as df_
OSS = Path((_HK + "/work_scratch/oss_analysis"))
OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(20261025); B = 2000

# ---- Qwen: rebuild and take the frozen fit half (same pairs as final_neutral/results.csv, split seed-primary)
Q = d2.build(AF / "tables_neutral_final", "neutral")
pairs = sorted(set(zip(Q.wording, Q.seed))); perm = np.random.default_rng(20261025).permutation(len(pairs))
fit = {pairs[i] for i in perm[:10]}; test = {pairs[i] for i in perm[10:]}


def lab(D, which):
    d = df_.make_label(D, which); d["pair"] = list(zip(d.wording, d.seed)); return d


def op_all(s, y, t):
    p = s >= t; tp = (p & (y == 1)).sum(); fp = (p & (y == 0)).sum()
    return dict(acc=(p == (y == 1)).mean(), recall=tp / max((y == 1).sum(), 1), fpr=fp / max((y == 0).sum(), 1), precision=tp / (tp + fp) if tp + fp else np.nan)


def cboot(fn, pair_arr, n=B):
    up = list(dict.fromkeys(pair_arr)); pa = np.array([hash(p) for p in pair_arr]); idx = {u: np.where(pa == hash(u))[0] for u in up}
    v = []
    for _ in range(n):
        ii = np.concatenate([idx[up[j]] for j in rng.integers(0, len(up), len(up))])
        x = fn(ii)
        if not np.isnan(x): v.append(x)
    return (np.percentile(v, 2.5), np.percentile(v, 97.5)) if v else (np.nan, np.nan)


run = pd.read_csv(OSS / "step1/final_t2/run.csv", low_memory=False)
ok = run[(run.status == "done") & (run.arm_build_bug == 0)]
ok_ids = set(ok.trial_id)
CHAT_T1 = ["headline-chat", "moral-prime", "moral-prime-b", "moral-placebo", "d-cot-monitor-a", "start-5tick", "fx-chat-p1", "fx-chat-p5", "nx-chat-p1"]
ALLCHAT = sorted(set(ok[ok.communication == "private"].arm) - {"ctl-32b-joint", "ctl-32b-compete", "fx-ctl-joint"})
d2.TALK = sorted(set(CHAT_T1) | set(ALLCHAT) | {"headline-tacit", "fx-tacit-p1", "nx-tacit-p1"})
G = d2.build(OSS / "tables_t2", "oss"); G = G[G.trial_id.isin(ok_ids)].reset_index(drop=True)
G["pair"] = list(zip(G.wording, G.seed))
d2.TALK = ["headline-chat", "headline-monitored"]   # Qwen talk population; gpt-oss populations are chosen below
G = G.merge(pd.read_csv(OSS / "tables_t2/trials.csv")[["trial_id", "empty_talk_done_count"]], on="trial_id", how="left")
G["price_det"] = G.trial_id.map(ok.set_index("trial_id")["price_detector_flag_any"])
print("gpt-oss games built:", len(G), flush=True)

rows = []


def population(name, arms, extra=None):
    g = G[G.arm.isin(arms) & (G.n_late >= 2)].copy()
    if extra is not None: g = extra(g)
    return name, g.reset_index(drop=True)


POPS = [population("headline-chat (p1,p3,p5)", ["headline-chat"]),
        population("headline-chat p1 only", ["headline-chat"], lambda g: g[g.penalty_point == 1]),
        population("B: all non-bug chat arms of the final data", ALLCHAT),
        population("headline-chat, games with no empty-talk done turns", ["headline-chat"], lambda g: g[g.empty_talk_done_count.fillna(0) == 0]),
        population("B0: narrower arm list (headline, moral x3, cot-monitor, 5-tick, formula/no-numbers chat)", CHAT_T1)]
QPOP = "Qwen headline-chat+monitored, held-out half (frozen, as published)"
FROZEN = {}
for labname in ("c_outcome", "b_agreement"):
    qd = lab(Q, labname); qf = qd[qd.pair.isin(fit)].reset_index(drop=True); qt = qd[qd.pair.isin(test)].reset_index(drop=True)
    gf = np.array([hash(p) for p in qf.pair]); yf = qf.y.values
    SQ = df_.score_all(qf, qt, "early", gf)
    thr = {k: df_.thresholds(SQ[k][0], yf)["youden"] for k in df_.DETS}; FROZEN[labname] = (qf, gf, thr)
    y = qt.y.values
    for k in df_.DETS:
        s = SQ[k][1]; a = d2.auc(s, y); lo, hi = cboot(lambda ii: d2.auc(s[ii], y[ii]), list(qt.pair))
        ci = {m: cboot(lambda ii, m=m: op_all(s[ii], y[ii], thr[k])[m], list(qt.pair), 1000) for m in ("recall", "fpr", "precision", "acc")}
        o = op_all(s, y, thr[k])
        rows.append(dict(model="Qwen3-32B", population=QPOP, label=labname, detector=k, n=len(qt), prevalence=y.mean(), auc=a, auc_lo=lo, auc_hi=hi, thr=thr[k], **o,
                         recall_lo=ci["recall"][0], recall_hi=ci["recall"][1], fpr_lo=ci["fpr"][0], fpr_hi=ci["fpr"][1], precision_lo=ci["precision"][0], precision_hi=ci["precision"][1], acc_lo=ci["acc"][0], acc_hi=ci["acc"][1]))
    bt = SQ["both: quotes + TF-IDF + LR"][1]
    for nm in ("quotes: mean level", "text: TF-IDF + LR"):
        ot = SQ[nm][1]; lo, hi = cboot(lambda ii: d2.auc(bt[ii], y[ii]) - d2.auc(ot[ii], y[ii]), list(qt.pair))
        rows.append(dict(model="Qwen3-32B", population=QPOP, label=labname, detector="DIFF both(quotes+TF-IDF) minus " + nm, n=len(qt), prevalence=y.mean(), auc=d2.auc(bt, y) - d2.auc(ot, y), auc_lo=lo, auc_hi=hi))
    for pname, g in POPS:
        dg = g.copy(); dg["y"] = (dg.late_level >= 0.5).astype(int) if labname == "c_outcome" else (dg.late_rule_flag == 1).astype(int)
        y = dg.y.values
        if len(set(y)) < 2:
            rows.append(dict(model="gpt-oss-20b", population=pname, label=labname, detector="(one class only)", n=len(dg), prevalence=y.mean())); continue
        S = df_.score_all(qf, dg, "early", gf)
        for k in df_.DETS:
            s = S[k][1]; a = d2.auc(s, y); lo, hi = cboot(lambda ii: d2.auc(s[ii], y[ii]), list(dg.pair))
            o = op_all(s, y, thr[k]); ci = {m: cboot(lambda ii, m=m: op_all(s[ii], y[ii], thr[k])[m], list(dg.pair), 1000) for m in ("recall", "fpr", "precision", "acc")}
            rows.append(dict(model="gpt-oss-20b", population=pname, label=labname, detector=k, n=len(dg), prevalence=y.mean(), auc=a, auc_lo=lo, auc_hi=hi, thr=thr[k], **o,
                             recall_lo=ci["recall"][0], recall_hi=ci["recall"][1], fpr_lo=ci["fpr"][0], fpr_hi=ci["fpr"][1], precision_lo=ci["precision"][0], precision_hi=ci["precision"][1], acc_lo=ci["acc"][0], acc_hi=ci["acc"][1]))
        bt = S["both: quotes + TF-IDF + LR"][1]
        for nm in ("quotes: mean level", "text: TF-IDF + LR"):
            ot = S[nm][1]; lo, hi = cboot(lambda ii: d2.auc(bt[ii], y[ii]) - d2.auc(ot[ii], y[ii]), list(dg.pair))
            rows.append(dict(model="gpt-oss-20b", population=pname, label=labname, detector="DIFF both(quotes+TF-IDF, Qwen-fitted) minus " + nm, n=len(dg), prevalence=y.mean(), auc=d2.auc(bt, y) - d2.auc(ot, y), auc_lo=lo, auc_hi=hi))

# ---- instructed label (joint vs compete controls), frozen on the Qwen controls
qd = lab(Q, "a_instructed"); qf = qd[qd.pair.isin(fit)].reset_index(drop=True); qt = qd[qd.pair.isin(test)].reset_index(drop=True); gf = np.array([hash(p) for p in qf.pair])
SQ = df_.score_all(qf, qt, "early", gf); thrI = {k: df_.thresholds(SQ[k][0], qf.y.values)["youden"] for k in df_.DETS}
for k in df_.DETS:
    s = SQ[k][1]; y = qt.y.values
    rows.append(dict(model="Qwen3-32B", population="Qwen joint vs compete controls, held-out half", label="a_instructed", detector=k, n=len(qt), prevalence=y.mean(), auc=d2.auc(s, y), thr=thrI[k], **op_all(s, y, thrI[k])))
g = G[G.arm.isin(["ctl-32b-joint", "ctl-32b-compete"])].reset_index(drop=True); g["y"] = (g.arm == "ctl-32b-joint").astype(int); y = g.y.values
S = df_.score_all(qf, g, "early", gf)
for k in df_.DETS:
    s = S[k][1]; lo, hi = cboot(lambda ii: d2.auc(s[ii], y[ii]), list(g.pair))
    rows.append(dict(model="gpt-oss-20b", population="joint-profit vs strict-compete control", label="a_instructed", detector=k, n=len(g), prevalence=y.mean(), auc=d2.auc(s, y), auc_lo=lo, auc_hi=hi, thr=thrI[k], **op_all(s, y, thrI[k])))
R = pd.DataFrame(rows); R.to_csv(OUT / "detection_transfer.csv", index=False)

# ---- price detector (frozen level_min 0.8, window 2, tol 0.25; run.csv price_detector_flag_any) vs the late-outcome label
pr = []
for pname, g in POPS[:3] + POPS[4:]:
    y = (g.late_level >= 0.5).astype(int).values; s = g.price_det.fillna(0).astype(float).values
    o = op_all(s, y, 0.5); ci = {m: cboot(lambda ii, m=m: op_all(s[ii], y[ii], 0.5)[m], list(g.pair), 1000) for m in ("recall", "fpr", "precision")}
    pr.append(dict(model="gpt-oss-20b", population=pname, label="c_outcome", n=len(g), prevalence=y.mean(), flag_rate=s.mean(), **o, recall_lo=ci["recall"][0], recall_hi=ci["recall"][1],
                   fpr_lo=ci["fpr"][0], fpr_hi=ci["fpr"][1], precision_lo=ci["precision"][0], precision_hi=ci["precision"][1]))
for a_ in ("ctl-32b-joint", "ctl-32b-compete", "headline-tacit"):
    gg = G[G.arm == a_]; pr.append(dict(model="gpt-oss-20b", population="flag rate in " + a_, label="price_detector_flag_any", n=len(gg), flag_rate=gg.price_det.fillna(0).mean()))
pd.DataFrame(pr).to_csv(OUT / "price_detector_transfer.csv", index=False)

# ---- quotes-only on tacit games (no text exists), same frozen threshold
qf, gf, thrC = FROZEN["c_outcome"]; tq = df_.thresholds(qf["early_q_mean"].values, qf.y.values)["youden"]
tac = G[G.arm.isin(["headline-tacit", "fx-tacit-p1", "nx-tacit-p1"]) & (G.n_late >= 2)].reset_index(drop=True); tac["y"] = (tac.late_level >= 0.5).astype(int)
tr = []
for nm, g in (("tacit arms (headline-tacit, formula/no-numbers tacit)", tac), ("headline-tacit only", tac[tac.arm == "headline-tacit"].reset_index(drop=True))):
    y = g.y.values; s = g.early_q_mean.values
    if len(set(y)) < 2: tr.append(dict(population=nm, n=len(g), prevalence=y.mean(), note="one class only")); continue
    lo, hi = cboot(lambda ii: d2.auc(s[ii], y[ii]), list(g.pair)); tr.append(dict(population=nm, n=len(g), prevalence=y.mean(), auc=d2.auc(s, y), auc_lo=lo, auc_hi=hi, thr=tq, **op_all(s, y, tq)))
pd.DataFrame(tr).to_csv(OUT / "tacit_quotes_only.csv", index=False)

# ---- sensitivity: refit INSIDE gpt-oss (5-fold CV grouped by seed). This is NOT the frozen rule.
sens = []
for pname, g in POPS[:3]:
    y = (g.late_level >= 0.5).astype(int).values
    if len(set(y)) < 2: continue
    Qm = np.column_stack([g["early_%s" % k].values for k in d2.QKEYS]).astype(float); docs = g.early_doc.tolist(); sd = g.seed.values
    sc = {"quotes: mean level (no fit)": g.early_q_mean.values, "text: TF-IDF+LR (CV in gpt-oss)": d2.cv_scores(None, y, sd, docs=docs),
          "quotes: feats+LR (CV in gpt-oss)": d2.cv_scores(Qm, y, sd), "both: quotes+TF-IDF+LR (CV in gpt-oss)": d2.cv_scores(Qm, y, sd, docs=docs)}
    for k, s in sc.items():
        lo, hi = cboot(lambda ii: d2.auc(s[ii], y[ii]), list(g.pair), 1000); sens.append(dict(population=pname, detector=k, n=len(g), prevalence=y.mean(), auc=d2.auc(s, y), auc_lo=lo, auc_hi=hi))
    b = sc["both: quotes+TF-IDF+LR (CV in gpt-oss)"]
    for nm in ("quotes: feats+LR (CV in gpt-oss)", "quotes: mean level (no fit)"):
        o = sc[nm]; lo, hi = cboot(lambda ii: d2.auc(b[ii], y[ii]) - d2.auc(o[ii], y[ii]), list(g.pair), 1000)
        sens.append(dict(population=pname, detector="DIFF both(CV in gpt-oss) minus " + nm, n=len(g), prevalence=y.mean(), auc=d2.auc(b, y) - d2.auc(o, y), auc_lo=lo, auc_hi=hi))
pd.DataFrame(sens).to_csv(OUT / "refit_within_gptoss_sensitivity.csv", index=False)

desc = G[G.n_late >= 2].assign(hi=lambda d: d.late_level >= .5).groupby("arm").agg(n=("trial_id", "count"), prevalence_late_ge_0_5=("hi", "mean"), early_q_mean=("early_q_mean", "mean"),
                                                                                    late_level=("late_level", "mean"), price_det=("price_det", "mean")).reset_index()
desc.to_csv(OUT / "arm_label_prevalence.csv", index=False)
pd.set_option("display.width", 250)
print(R[R.label == "c_outcome"][["model", "population", "detector", "n", "prevalence", "auc", "auc_lo", "auc_hi", "recall", "fpr", "precision"]].round(3).to_string())
print(R[R.label == "a_instructed"][["model", "detector", "n", "auc", "recall", "fpr"]].round(3).to_string())
print(pd.read_csv(OUT / "price_detector_transfer.csv").round(3).to_string()); print(pd.read_csv(OUT / "tacit_quotes_only.csv").round(3).to_string())
print(pd.DataFrame(sens).round(3).to_string()); print(desc.round(3).to_string())
print("thr c_outcome:", {k: round(v, 3) for k, v in thrC.items()})
