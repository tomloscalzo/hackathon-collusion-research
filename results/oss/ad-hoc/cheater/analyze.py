import sys, csv, random, collections
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
sys.path.insert(0, (_REPO + "/results/oss/ad-hoc/_common"))
import oss_common as oc
OUT = (_REPO + "/results/oss/ad-hoc/cheater/")
oss = oc.load_oss((_HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv"))
qw = oc.load_qwen()
C = ("n3-cheater", "3"); G = ("n3-group", "3"); H = ("headline-chat", "3")
contrasts = [("n3-cheater - n3-group", C, G), ("n3-cheater - headline-chat (p3)", C, H), ("n3-group - headline-chat (p3)", G, H)]
rows = []
for name, a, b in contrasts:
    for model, d in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
        p = oc.paired(d, a, b)
        for col, _, _ in oc.METRICS:
            x = p[col]
            rows.append([model, name, col, x["n_pairs"], x["mean_a"], x["mean_b"], x["diff"], x["lo"], x["hi"]])
with open(OUT + "standard_metrics.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("model,contrast,metric,n_pairs,mean_arm,mean_control,diff,lo,hi".split(","))
    for r in rows: w.writerow([oc.fmt(v, 4) if isinstance(v, float) else v for v in r])
for r in rows: print(r[0], r[1], r[2], r[3], *[oc.fmt(v) for v in r[4:]])
# sensitivity: empty_talk_done_count
def f(x):
    try: return float(x)
    except: return None
print("empty_talk mean per arm")
for arm in (C, G, H):
    s = [f(r["empty_talk_done_count"]) or 0 for r in oc._pick(oss, *arm)]
    print(arm, len(s), sum(s)/len(s), sum(1 for v in s if v > 0))
bad = {(r["wording"], r["seed"]) for r in oss if r["empty_talk_done_count"] not in ("", "0", "0.0") and f(r["empty_talk_done_count"]) > 0}
oss2 = [r for r in oss if (r["wording"], r["seed"]) not in bad]
oss3 = [r for r in oss if f(r["empty_talk_done_count"] or 0) in (0, None)]
print("sens: drop whole pair if any game in the pair-key has count>0 (any arm)")
sens = []
for name, a, b in contrasts[:2]:
    A = {(r["wording"], r["seed"]): r for r in oc._pick(oss, *a)}
    B = {(r["wording"], r["seed"]): r for r in oc._pick(oss, *b)}
    keep = [k for k in set(A) & set(B) if not (f(A[k]["empty_talk_done_count"]) or 0) and not (f(B[k]["empty_talk_done_count"]) or 0)]
    kr = [r for r in oss if (r["wording"], r["seed"]) in set(keep) and (r["arm"], r["penalty_point"]) in (a, b)]
    p = oc.paired(kr, a, b)
    for col, _, _ in oc.METRICS:
        x = p[col]; print(name, col, x["n_pairs"], oc.fmt(x["diff"]), oc.fmt(x["lo"]), oc.fmt(x["hi"]))
        sens.append([name, col, x["n_pairs"], x["diff"], x["lo"], x["hi"]])
with open(OUT + "sensitivity_empty_talk.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow("contrast,metric,n_pairs,diff,lo,hi".split(","))
    for r in sens: w.writerow([oc.fmt(v, 4) if isinstance(v, float) else v for v in r])
# reaction measures
def react(d, label):
    sub = oc._pick(d, *C)
    n = len(sub)
    dr = [r for r in sub if r.get("defect_round") not in ("", None)]
    print(label, "games", n, "with defect_round", len(dr))
    for col in ("defect_round", "punish_round_first", "punish_lag", "coalition_punished", "war_length", "war_after_first_undercut", "undercut_count", "punishment_count"):
        v = [f(r.get(col)) for r in sub]; vv = [x for x in v if x is not None]
        print(" ", col, "non-missing", len(vv), "mean", (sum(vv)/len(vv) if vv else None), "sum", sum(vv) if vv else None, collections.Counter(r.get(col) for r in sub).most_common(5) if col in ("coalition_punished","war_after_first_undercut") else "")
    return sub
react(oss, "OSS cheater"); react(qw, "QWEN cheater")
for arm in (G,):
    print("n3-group controls", arm)
    for col in ("war_length", "undercut_count", "punishment_count"):
        for lab, d in (("oss", oss), ("qwen", qw)):
            for a in (C, G):
                v = [f(r.get(col)) for r in oc._pick(d, *a)]; vv = [x for x in v if x is not None]
                print(lab, a[0], col, len(vv), sum(vv)/len(vv) if vv else None)
