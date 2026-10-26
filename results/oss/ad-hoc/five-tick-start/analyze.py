import sys, csv, random, collections
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
sys.path.insert(0, (_REPO + "/results/oss/ad-hoc/_common"))
import oss_common as oc
OSS = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
RND = (_HK + "/work_scratch/oss_analysis/tables_t1/rounds.csv")
ARM, CTL = ("start-5tick", "3"), ("headline-chat", "3")
oss = oc.load_oss(OSS); qw = oc.load_qwen()
CON = "start-5tick - headline-chat (p3)"
out = []
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
    p = oc.paired(rows, ARM, CTL)
    for m, _, _ in oc.METRICS:
        x = p[m]; out.append(dict(model=model, contrast=CON, metric=m, n_pairs=x["n_pairs"], mean_arm=x["mean_a"], mean_control=x["mean_b"], diff=x["diff"], lo=x["lo"], hi=x["hi"]))
# empty-talk sensitivity
et = {}
for r in oss:
    if r["arm"] in ("start-5tick", "headline-chat") and r["penalty_point"] == "3":
        et.setdefault(r["arm"], []).append(float(r["empty_talk_done_count"] or 0))
sens = []
drop = [r for r in oss if float(r.get("empty_talk_done_count") or 0) == 0]
p = oc.paired(drop, ARM, CTL)
for m, _, _ in oc.METRICS:
    x = p[m]; sens.append(dict(model="gpt-oss-20b (empty_talk=0 games only)", contrast=CON, metric=m, n_pairs=x["n_pairs"], mean_arm=x["mean_a"], mean_control=x["mean_b"], diff=x["diff"], lo=x["lo"], hi=x["hi"]))
# bug-replicate pool sensitivity: headline-chat p3 cell has no bug replicates (p1,p5 only) -> not applicable
cols = ["model","contrast","metric","n_pairs","mean_arm","mean_control","diff","lo","hi"]
def w(fn, rows):
    with open(fn, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(cols)
        for r in rows: wr.writerow([r[c] if not isinstance(r[c], float) else "%.6f" % r[c] for c in cols])
w("standard_metrics.csv", out); w("sensitivity_empty_talk.csv", sens)
print("empty_talk means", {k: sum(v)/len(v) for k, v in et.items()}, {k: sum(1 for x in v if x > 0) for k, v in et.items()})
# windows
def load_rounds(path, ids):
    d = collections.defaultdict(dict)
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["trial_id"] in ids and r["seat"].startswith("llm"):
            d[r["trial_id"]][int(r["round"])] = float(r["market_price"])
    return d
meta = {r["trial_id"]: r for r in oss if (r["arm"], r["penalty_point"]) in (ARM, CTL)}
R = load_rounds(RND, set(meta))
idx = {t: {k: (v - 1) / 2 for k, v in rr.items()} for t, rr in R.items()}
WIN = [("all rounds", 1, 99), ("round 1 only", 1, 1), ("excluding round 1", 2, 99), ("rounds 2-5", 2, 5), ("rounds 5+", 5, 99), ("rounds 10+", 10, 99)]
def gm(t, lo, hi):
    v = [x for k, x in idx.get(t, {}).items() if lo <= k <= hi]
    return sum(v) / len(v) if v else None
rng = random.Random(oc.SEED); wrows = []
for wn, lo, hi in WIN:
    A, C = {}, {}
    for t, r in meta.items():
        v = gm(t, lo, hi)
        if v is None: continue
        (A if r["arm"] == "start-5tick" else C)[(r["wording"], r["seed"])] = v
    ks = sorted(set(A) & set(C)); d = [A[k] - C[k] for k in ks]
    lo_, hi_ = oc._boot(d, rng) if d else (None, None)
    wrows.append(dict(window=wn, n_pairs=len(ks), arm_mean=sum(A[k] for k in ks)/len(ks), control_mean=sum(C[k] for k in ks)/len(ks), diff=sum(d)/len(d), lo=lo_, hi=hi_))
with open("windows.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(wrows[0])); wr.writeheader(); wr.writerows(wrows)
# paths by round, climb-back
maxr = max(max(v) for v in idx.values()); paths = []
for arm in ("start-5tick", "headline-chat"):
    ts = [t for t, r in meta.items() if r["arm"] == arm]
    for k in range(1, maxr + 1):
        v = [idx[t][k] for t in ts if t in idx and k in idx[t]]
        if v: paths.append(dict(arm=arm, round=k, price_index=sum(v)/len(v), n_games=len(v)))
with open("paths_by_round.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(paths[0])); wr.writeheader(); wr.writerows(paths)
cb = []
for arm in ("start-5tick", "headline-chat"):
    ts = [t for t, r in meta.items() if r["arm"] == arm and t in idx]
    mx = [max([v for k, v in idx[t].items() if k >= 2] or [0]) for t in ts]
    r1 = [idx[t].get(1) for t in ts]
    cb.append(dict(arm=arm, games=len(ts), round1_index=sum(r1)/len(r1), share_ever_ge_0_5=sum(m>=.5 for m in mx)/len(mx), share_ever_ge_0_8=sum(m>=.8 for m in mx)/len(mx), mean_game_max_after_r1=sum(mx)/len(mx),
        rounds2to5=sum(gm(t,2,5) or 0 for t in ts)/len(ts), rounds6plus=(lambda L: sum(L)/len(L))([gm(t,6,99) for t in ts if gm(t,6,99) is not None])))
with open("climb_back.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(cb[0])); wr.writeheader(); wr.writerows(cb)
for r in out + sens: print(r["model"], r["metric"], r["n_pairs"], *("%.3f" % r[k] for k in ("mean_arm","mean_control","diff","lo","hi")))
for r in wrows + cb: print(r)
for r in paths:
    if r["round"] in (1,2,3,5,8,10,15): print(r)
