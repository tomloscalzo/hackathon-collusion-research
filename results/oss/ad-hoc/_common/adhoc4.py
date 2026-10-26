"""Shared driver for the four small-n topics (ethics-rule, incentives, asymmetric, market-structure). Run: python -I -X utf8 adhoc4.py"""
import csv, os, sys, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
OSS = (_HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv")
QW = oc.QWEN_RUN
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
oss = oc.load_oss(OSS); qw = oc.load_qwen(QW)
def rd(p): return list(csv.DictReader(open(p, encoding="utf-8", newline="")))
fo = rd(OSS.replace("run.csv", "run_firms.csv")); fq = rd(QW.replace("run.csv", "run_firms.csv"))
TOP = {
 "ethics-rule": [(("n3-ethics",3),("n3-group",3),"n3-ethics - n3-group (p3)")],
 "incentives": [(("m-inc-joint",3),("headline-chat",3),"m-inc-joint - headline-chat (p3)"),
                (("m-inc-target",3),("headline-chat",3),"m-inc-target - headline-chat (p3)"),
                (("m-inc-joint",3),("m-inc-target",3),"m-inc-joint - m-inc-target (p3)")],
 "asymmetric": [(("m-asym",3),("headline-chat",3),"m-asym - headline-chat (p3)")],
 "market-structure": [(("n3-group",3),("headline-chat",3),"n3-group - headline-chat (p3)")],
}
SEAT = [("competitive_share","competitive share"),("matching_share","matching share"),("quote_mean","mean quote"),("profit_gain_index","profit gain index")]
f = lambda x: oc._f(x)
def pairmap(rows, arm, pt): return {(r["wording"], r["seed"]): r for r in oc._pick(rows, arm, pt)}
def drop_et(rows, a, b):
    A = pairmap(rows, *a); B = pairmap(rows, *b)
    bad = {k for k in set(A)&set(B) if (f(A[k].get("empty_talk_done_count")) or 0) > 0 or (f(B[k].get("empty_talk_done_count")) or 0) > 0}
    return [r for r in rows if (r["wording"], r["seed"]) not in bad], len(bad)
def mde(d):  # 80% power, 5% two-sided: 2.8 * SD(diff)/sqrt(n)
    return 2.8*st.stdev(d)/len(d)**.5 if len(d) > 2 else None
def pdiffs(rows, a, b, col):
    A = pairmap(rows, *a); B = pairmap(rows, *b); d=[]
    for k in sorted(set(A)&set(B)):
        x, y = f(A[k].get(col)), f(B[k].get(col))
        if x is not None and y is not None: d.append(x-y)
    return d
def boot(d):
    rng = random.Random(oc.SEED); return oc._boot(d, rng)
sm = []; sens = []; mdes = []; cellm = []
for top, cons in TOP.items():
    for a, b, name in cons:
        for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
            res = oc.paired(rows, a, b)
            for col, lab, _ in oc.METRICS:
                r = res[col]
                if not r["n_pairs"]: continue
                sm.append(dict(topic=top, model=model, contrast=name, metric=col, n_pairs=r["n_pairs"], mean_arm=r["mean_a"], mean_control=r["mean_b"], diff=r["diff"], lo=r["lo"], hi=r["hi"]))
                d = pdiffs(rows, a, b, col)
                mdes.append(dict(topic=top, model=model, contrast=name, metric=col, n_pairs=len(d), sd_pair_diff=st.stdev(d), mde_80pct=mde(d), ci_halfwidth=(r["hi"]-r["lo"])/2))
        rows2, nd = drop_et(oss, a, b); res = oc.paired(rows2, a, b); res0 = oc.paired(oss, a, b)
        for col, lab, _ in oc.METRICS:
            r = res[col]
            if r["n_pairs"]: sens.append(dict(topic=top, contrast=name, metric=col, pairs_dropped=nd, n_pairs=r["n_pairs"], diff=r["diff"], lo=r["lo"], hi=r["hi"], diff_all=res0[col]["diff"], n_all=res0[col]["n_pairs"]))
    for arm in sorted({x[0][0] for x in cons} | {x[1][0] for x in cons}):
        c = oc.cell_means(oss, arm, 3)
        rr = oc._pick(oss, arm, 3); et = [f(r.get("empty_talk_done_count")) or 0 for r in rr]
        cellm.append(dict(topic=top, arm=arm, n=len(rr), empty_talk_mean=sum(et)/len(et), games_with_empty_talk=sum(1 for e in et if e>0), **{col: c[col]["mean"] for col,_,_ in oc.METRICS}))
def wr(path, rows):
    if not rows: return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
rnd = lambda r: {k: (round(v,5) if isinstance(v,float) else v) for k,v in r.items()}
for top in TOP:
    d = os.path.join(OUT, top)
    wr(os.path.join(d, "standard_metrics.csv"), [rnd({k:v for k,v in r.items() if k!="topic"}) for r in sm if r["topic"]==top])
    for nm, src in (("mde_and_ci.csv", mdes), ("sensitivity_empty_talk.csv", sens), ("cell_means_gptoss.csv", cellm)):
        wr(os.path.join(d, nm), [rnd(r) for r in src if r["topic"]==top])
def seat_tables(top, arm, ctrl, model, rows, frows):
    idx = {}
    for r in frows:
        if r["seat_kind"] == "llm": idx.setdefault(r["row_id"], []).append(r)
    runrows = {(r["wording"], r["seed"]): r for r in oc._pick(rows, arm, 3)}
    ctrlrows = {(r["wording"], r["seed"]): r for r in oc._pick(rows, ctrl, 3)}
    out = []
    for col, lab in SEAT:
        dbu, dbc, duc, vb, vu, vc = [], [], [], [], [], []
        for k in sorted(set(runrows)&set(ctrlrows)):
            fs = idx.get(runrows[k]["row_id"], []); cs = idx.get(ctrlrows[k]["row_id"], [])
            b = [f(x[col]) for x in fs if f(x["rule_bound"])==1.0 and f(x[col]) is not None]
            u = [f(x[col]) for x in fs if f(x["rule_bound"])!=1.0 and f(x[col]) is not None]
            c = [f(x[col]) for x in cs if f(x[col]) is not None]
            if not (b and u and c): continue
            B, U, C = sum(b)/len(b), sum(u)/len(u), sum(c)/len(c)
            vb.append(B); vu.append(U); vc.append(C); dbu.append(B-U); dbc.append(B-C); duc.append(U-C)
        for nm, d, v1, v2 in (("bound minus unbound (same game)", dbu, vb, vu), ("bound minus control firms", dbc, vb, vc), ("unbound minus control firms", duc, vu, vc)):
            if len(d) < 2: continue
            lo, hi = boot(d)
            out.append(dict(topic=top, model=model, arm=arm, comparison=nm, measure=lab, n_pairs=len(d), mean_first=sum(v1)/len(v1), mean_second=sum(v2)/len(v2), diff=sum(d)/len(d), lo=lo, hi=hi))
    return out
seat = []
fq1 = [r for r in fq if r["row_id"].endswith("__t1")]
for top, arm, ctrl in (("ethics-rule","n3-ethics","n3-group"),("asymmetric","m-asym","headline-chat")):
    seat += seat_tables(top, arm, ctrl, "gpt-oss-20b", oss, fo)
    seat += seat_tables(top, arm, ctrl, "Qwen3-32B", qw, fq1)
for top in ("ethics-rule","asymmetric"):
    wr(os.path.join(OUT, top, "per_seat.csv"), [rnd({k:v for k,v in r.items() if k!="topic"}) for r in seat if r["topic"]==top])
extra = []
for top, cons in TOP.items():
    for arm in sorted({x[0][0] for x in cons} | {x[1][0] for x in cons}):
        for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
            rr = oc._pick(rows, arm, 3)
            if not rr: continue
            def m(c):
                g = [f(r.get(c)) for r in rr if f(r.get(c)) is not None]
                return sum(g)/len(g) if g else None
            extra.append(dict(topic=top, model=model, arm=arm, n=len(rr), explicit_agreement_any=m("explicit_agreement_any"), explicit_round_share=m("explicit_round_share"), messages_per_round=m("messages_per_round"), war_after_first_undercut=m("war_after_first_undercut"), rounds_played=m("rounds_played"), fined=m("fined")))
for top in TOP: wr(os.path.join(OUT, top, "descriptives_both_models.csv"), [rnd({k:v for k,v in r.items() if k!="topic"}) for r in extra if r["topic"]==top])
print("ok")
