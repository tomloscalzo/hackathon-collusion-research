"""gpt-oss-20b communication ad-hoc: chat vs tacit at p1, p5; chat p3 vs controls. Run: python -I -X utf8 communication.py"""
import sys, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_common"))
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
T1 = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
oss = oc.load_oss(T1)
oss_all = oc.load_oss(T1, include_bug=True)
qw = oc.load_qwen()
def f(x):
    try: return float(x)
    except: return None
std, extra = [], []
def add(model, name, rows, a, b):
    res = oc.paired(rows, a, b)
    for k, _, _ in oc.METRICS:
        r = res[k]
        std.append([model, name, k, r["n_pairs"], r["mean_a"], r["mean_b"], r["diff"], r["lo"], r["hi"]])
    return res
C = [("headline-chat", 1, "headline-tacit", 1, "chat - tacit (p1)"), ("headline-chat", 5, "headline-tacit", 5, "chat - tacit (p5)")]
for a, pa, b, pb, nm in C:
    for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
        add(model, nm, rows, (a, pa), (b, pb))
# gpt-oss only: chat p3 vs joint / compete controls
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qw)):
    for ctl, nm in (("ctl-32b-joint", "joint-profit control"), ("ctl-32b-compete", "strict-compete control")):
        if any(r["arm"] == ctl for r in rows):
            add(model, "headline-chat (p3) - %s (p3)" % nm, rows, ("headline-chat", 3), (ctl, 3))
# sensitivity: drop empty_talk_done_count>0 games
ok = [r for r in oss if (f(r.get("empty_talk_done_count")) or 0) == 0]
sens = []
for a, pa, b, pb, nm in C:
    for lab, rows in (("all games", oss), ("empty_talk_done_count==0 only", ok)):
        res = oc.paired(rows, (a, pa), (b, pb))
        for k, _, _ in oc.METRICS:
            r = res[k]; sens.append([nm, lab, k, r["n_pairs"], r["diff"], r["lo"], r["hi"]])
# headline-cell replicates pooled (build-bug arms played headline prompt)
rep = {"hrep-fx-chat-p1": ("headline-chat", 1), "hrep-nx-chat-p1": ("headline-chat", 1), "hrep-fx-chat-p5": ("headline-chat", 5),
       "hrep-fx-tacit-p1": ("headline-tacit", 1), "hrep-nx-tacit-p1": ("headline-tacit", 1)}
pool = []
for r in oss_all:
    if r["arm"] in ("fx-chat-p1","fx-chat-p5","fx-tacit-p1","nx-chat-p1","nx-tacit-p1"): continue  # corrected formula/no-numbers games, not replicates
    if r["arm"] in rep:
        r = dict(r); r["arm"], r["penalty_point"] = rep[r["arm"]][0], str(rep[r["arm"]][1])
    pool.append(r)
# pooled pairs: duplicate keys possible; average within key
def dedup(rows):
    g = {}
    for r in rows: g.setdefault((r["arm"], r["penalty_point"], r["wording"], r["seed"]), []).append(r)
    out = []
    for k, v in g.items():
        m = dict(v[0])
        for col, _, _ in oc.METRICS:
            xs = [f(x.get(col)) for x in v if f(x.get(col)) is not None]
            m[col] = sum(xs) / len(xs) if xs else ""
        out.append(m)
    return out
pooled = dedup(pool)
pool_rows = []
for a, pa, b, pb, nm in C:
    res = oc.paired(pooled, (a, pa), (b, pb))
    for k, _, _ in oc.METRICS:
        r = res[k]; pool_rows.append([nm, k, r["n_pairs"], r["diff"], r["lo"], r["hi"]])
# cell means and covariates
cells = []
for arm, pt in (("headline-tacit", 1), ("headline-chat", 1), ("headline-chat", 3), ("headline-tacit", 5), ("headline-chat", 5), ("ctl-32b-joint", 3), ("ctl-32b-compete", 3)):
    sub = [r for r in oss if r["arm"] == arm and r["penalty_point"] == str(pt)]
    cm = oc.cell_means(oss, arm, pt)
    e = [f(r["empty_talk_done_count"]) or 0 for r in sub]
    ex = [f(r["explicit_agreement_any"]) for r in sub if f(r["explicit_agreement_any"]) is not None]
    mp = [f(r["messages_per_round"]) for r in sub if f(r["messages_per_round"]) is not None]
    row = [arm, pt, len(sub)]
    for k, _, _ in oc.METRICS: row += [cm[k]["mean"], cm[k]["lo"], cm[k]["hi"]]
    row += [sum(e)/len(e), sum(1 for x in e if x > 0), sum(ex)/len(ex) if ex else "", sum(mp)/len(mp) if mp else ""]
    cells.append(row)
def w(name, hdr, rows):
    with open(name, "w", newline="", encoding="utf-8") as fh:
        c = csv.writer(fh); c.writerow(hdr)
        for r in rows: c.writerow([("%.4f" % x if isinstance(x, float) else x) for x in r])
w("standard_metrics.csv", ["model","contrast","metric","n_pairs","mean_arm","mean_control","diff","lo","hi"], std)
w("sensitivity_empty_talk.csv", ["contrast","subset","metric","n_pairs","diff","lo","hi"], sens)
w("sensitivity_pooled_replicates.csv", ["contrast","metric","n_pairs","diff","lo","hi"], pool_rows)
hdr = ["arm","penalty_point","n"]
for k, _, _ in oc.METRICS: hdr += [k+"_mean", k+"_lo", k+"_hi"]
hdr += ["empty_talk_done_mean","n_games_empty_talk_gt0","explicit_agreement_any_share","messages_per_round_mean"]
w("cell_means.csv", hdr, cells)
