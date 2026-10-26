"""gpt-oss-20b penalty ad-hoc: headline chat p3/p5 vs p1, tacit p5 vs p1, comm x penalty interaction; Qwen3-32B thinking on beside."""
import sys, csv, random
sys.path.insert(0, "../_common")
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
OSS = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
oss = oc.load_oss(OSS); qw = oc.load_qwen()
M = [m[0] for m in oc.METRICS]
CT = [("chat p5 - p1", ("headline-chat", 5), ("headline-chat", 1)),
      ("chat p3 - p1", ("headline-chat", 3), ("headline-chat", 1)),
      ("tacit p5 - p1", ("headline-tacit", 5), ("headline-tacit", 1))]
def f(x):
    try: return float(x)
    except: return None
def pairs(rows, a, b, drop_empty=False):
    A = {(r["wording"], r["seed"]): r for r in rows if r["arm"] == a[0] and r["penalty_point"] == str(a[1])}
    B = {(r["wording"], r["seed"]): r for r in rows if r["arm"] == b[0] and r["penalty_point"] == str(b[1])}
    ks = sorted(set(A) & set(B))
    if drop_empty:
        ks = [k for k in ks if not (int(f(A[k].get("empty_talk_done_count")) or 0) or int(f(B[k].get("empty_talk_done_count")) or 0))]
    return ks, A, B
def boot(d):
    rng = random.Random(oc.SEED); n = len(d)
    ms = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(oc.B))
    return ms[int(.025 * oc.B)], ms[int(.975 * oc.B) - 1]
def slope(rows, a, b, m, drop=False):
    ks, A, B = pairs(rows, a, b, drop)
    d = [f(A[k][m]) - f(B[k][m]) for k in ks]
    return ks, d, [f(A[k][m]) for k in ks], [f(B[k][m]) for k in ks]
out = []; sens = []; inter = []
def row(model, rows, name, a, b, drop=False, into=out):
    for m in M:
        ks, d, va, vb = slope(rows, a, b, m, drop)
        lo, hi = boot(d)
        into.append(dict(model=model, contrast=name, metric=m, n_pairs=len(d), mean_arm=sum(va)/len(va), mean_control=sum(vb)/len(vb), diff=sum(d)/len(d), lo=lo, hi=hi))
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
    for name, a, b in CT:
        row(model, rows, name, a, b)
    # interaction: (chat p5-p1) - (tacit p5-p1) on (wording,seed)
    for m in M:
        _, dc, _, _ = slope(rows, *CT[0][1:], m); kc = pairs(rows, *CT[0][1:])[0]
        kt = pairs(rows, *CT[2][1:])[0]
        dt = dict(zip(kt, slope(rows, *CT[2][1:], m)[1])); dcd = dict(zip(kc, dc))
        ks = sorted(set(dt) & set(dcd)); d = [dcd[k] - dt[k] for k in ks]; lo, hi = boot(d)
        out.append(dict(model=model, contrast="interaction: (chat p5-p1) - (tacit p5-p1)", metric=m, n_pairs=len(d), mean_arm=sum(dcd[k] for k in ks)/len(ks), mean_control=sum(dt[k] for k in ks)/len(ks), diff=sum(d)/len(d), lo=lo, hi=hi))
# empty-talk sensitivity (gpt-oss)
for name, a, b in CT:
    row("gpt-oss-20b", oss, name + " (games with empty_talk_done_count>0 dropped)", a, b, True, sens)
cols = ["model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"]
for fn, rs in (("standard_metrics.csv", out), ("sensitivity_empty_talk.csv", sens)):
    with open(fn, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader()
        for r in rs: w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
# cell means + empty-talk means
with open("cells.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["model", "arm", "penalty_point", "n", "metric", "mean", "lo", "hi", "mean_empty_talk_done_count"])
    for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
        for arm, pts in (("headline-chat", (1, 3, 5)), ("headline-tacit", (1, 5))):
            for p in pts:
                cm = oc.cell_means(rows, arm, p)
                sub = [r for r in rows if r["arm"] == arm and r["penalty_point"] == str(p)]
                e = [f(r.get("empty_talk_done_count")) or 0 for r in sub] if model == "gpt-oss-20b" else [None]
                for m in M:
                    c = cm[m]; w.writerow([model, arm, p, c["n"], m, round(c["mean"], 4), round(c["lo"], 4), round(c["hi"], 4), "" if e[0] is None else round(sum(e)/len(e), 3)])
print("ok")
