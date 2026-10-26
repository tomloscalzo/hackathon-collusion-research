"""Headline-chat p1 vs its headline-prompt replicate fx-chat-p1 (build bug), paired; disclosed sensitivity."""
import sys, csv
sys.path.insert(0, "../_common"); import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
P = (_HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv")
al = oc.load_oss(P, include_bug=True)
rows=[]
for A in ("hrep-fx-chat-p1","hrep-nx-chat-p1"):
  res = oc.paired(al, (A, 1), ("headline-chat", 1))
  rows += [dict(contrast=A+" (headline-prompt replicate) - headline-chat (p1)", metric=m, n_pairs=r["n_pairs"], mean_arm=oc.fmt(r["mean_a"]), mean_control=oc.fmt(r["mean_b"]), diff=oc.fmt(r["diff"]), lo=oc.fmt(r["lo"]), hi=oc.fmt(r["hi"])) for m, r in res.items()]
for r in rows: print(r)
with open("replicate_vs_headline_p1.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# for r in al if r["arm"] == "fx-chat-p1"}, {r["context_window"] for r in al if r["arm"] == "fx-chat-p1"})
