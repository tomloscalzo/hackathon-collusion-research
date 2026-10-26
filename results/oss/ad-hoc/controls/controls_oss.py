"""gpt-oss-20b controls analysis (tier t1). Run: python -I -X utf8 controls_oss.py"""
import sys, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, "../_common")
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
OSS = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
oss = oc.load_oss(OSS); qw = oc.load_qwen()
J, C, H = ("ctl-32b-joint", "3"), ("ctl-32b-compete", "3"), ("headline-chat", "3")
CON = [("joint-profit control - headline-chat (p3)", J, H), ("strict-compete control - headline-chat (p3)", C, H),
       ("joint-profit control - strict-compete control", J, C)]
out = []; sens = []
def rows_of(rows, contrast, a, b, model, tag=""):
    p = oc.paired(rows, a, b)
    for col, _, _ in oc.METRICS:
        d = p[col]
        out.append(dict(model=model, contrast=contrast, metric=col, n_pairs=d["n_pairs"], mean_arm=d["mean_a"], mean_control=d["mean_b"], diff=d["diff"], lo=d["lo"], hi=d["hi"]))
for c, a, b in CON:
    rows_of(oss, c, a, b, "gpt-oss-20b"); rows_of(qw, c, a, b, "Qwen3-32B")
with open("standard_metrics.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
# empty_talk sensitivity: drop games with count>0
def drop(rows): return [r for r in rows if float(r.get("empty_talk_done_count") or 0) == 0]
o2 = drop(oss)
for c, a, b in CON:
    p = oc.paired(o2, a, b)
    for col, _, _ in oc.METRICS:
        d = p[col]; sens.append(dict(contrast=c, metric=col, n_pairs=d["n_pairs"], diff=d["diff"], lo=d["lo"], hi=d["hi"]))
with open("empty_talk_sensitivity.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(sens[0])); w.writeheader(); w.writerows(sens)
# cell means and extras
cm = []
for model, rows, cells in [("gpt-oss-20b", oss, [J, C, H, ("fx-ctl-joint", "3")]), ("Qwen3-32B", qw, [J, C, H])]:
    for a, pt in cells:
        sub = [r for r in rows if r["arm"] == a and r["penalty_point"] == pt]
        m = oc.cell_means(rows, a, pt)
        e = [float(r.get("empty_talk_done_count") or 0) for r in sub] if model.startswith("gpt") else [None]
        cm.append(dict(model=model, arm=a, n=len(sub), evidence_ended=sum(r["end_reason"] == "EVIDENCE" for r in sub),
                       rounds_mean=sum(float(r["rounds_played"]) for r in sub) / len(sub),
                       empty_talk_mean=(sum(e) / len(e)) if e[0] is not None else "", empty_talk_games_gt0=sum(x > 0 for x in e) if e[0] is not None else "",
                       **{k + "_mean": m[k]["mean"] for k, _, _ in oc.METRICS}, **{k + "_lo": m[k]["lo"] for k, _, _ in oc.METRICS}, **{k + "_hi": m[k]["hi"] for k, _, _ in oc.METRICS}))
with open("cell_means.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cm[0])); w.writeheader(); w.writerows(cm)
# extra: formula joint control vs standard joint control (exploratory, different payoff block)
for lab, a, b in [("fx-ctl-joint (formula block) - headline-chat (p3)", ("fx-ctl-joint", "3"), H)]:
    p = oc.paired(oss, a, b)
    print(lab, {k: (v["n_pairs"], round(v["diff"], 3), round(v["lo"], 3), round(v["hi"], 3)) for k, v in p.items()})
# quote distribution from rounds.csv if available
for r in out: print(r["model"][:4], r["contrast"][:30], r["metric"], r["n_pairs"], *(("%.3f" % r[k]) for k in ("mean_arm", "mean_control", "diff", "lo", "hi")))
print("SENS");
for s in sens: print(s["contrast"][:30], s["metric"], s["n_pairs"], "%.3f %.3f %.3f" % (s["diff"], s["lo"], s["hi"]))
for c in cm: print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if not k.endswith(("_lo", "_hi"))})
