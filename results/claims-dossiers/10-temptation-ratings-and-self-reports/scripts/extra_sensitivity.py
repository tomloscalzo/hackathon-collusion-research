"""Sensitivity of the Claude-temptation correlations to the arms that simply instruct the firm what to do
(ctl-32b-compete: told to quote 1.00; ctl-32b-joint and m-inc-joint: told to maximise joint profit), and a
within-design slice: only private-chat cells at penalty point 1 (the prompts differ only by the added lever text).
Cell and (arm, wording) levels; Spearman and Pearson with cluster-bootstrap CIs (clusters = cells).
Run: python -X utf8 extra_sensitivity.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(C.SEED + 2)
oss = C.prep(C.load_oss()); oss = oss[oss.claude_temptation.notna()]
qn = C.prep(C.load_qwen("neutral"))
DATA = {"gpt-oss-20b (medium effort)": oss, "Qwen3-32B thinking on": qn[qn.thinking == "on"],
        "Qwen3-32B thinking off": qn[qn.thinking == "off"]}
INSTR = ["ctl-32b-compete", "ctl-32b-joint", "m-inc-joint", "ctl-14b-compete", "ctl-14b-joint"]
SUBSETS = {
    "all rated cells": lambda d: d,
    "without the instruction controls": lambda d: d[~d.arm.isin(INSTR)],
    "private chat, penalty point 1 only (lever text differs)": lambda d: d[(d.communication == "private") & (d.penalty_point.astype(str) == "1")],
}
rows = []
for ds, d in DATA.items():
    for sname, f in SUBSETS.items():
        s = f(d)
        for level in ("prompt", "cell"):
            a = C.aggregate(s, level)
            for r in C.RCOLS:
                for m in C.MCOLS:
                    res = C.boot_corr(a[r], a[m], a.cluster, rng)
                    rows.append(dict(dataset=ds, subset=sname, level=level, rating=r, metric=m,
                                     cells=s.cell.nunique(), **res))
T = pd.DataFrame(rows)
T.round(4).to_csv(OUT / "sensitivity_subsets.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 250)
print(T[(T.rating == "claude_temptation") & T.metric.isin(["price_index", "competitive_share", "matching_share"])]
      [["dataset", "subset", "level", "metric", "n", "spearman", "sp_lo", "sp_hi", "pearson", "pe_lo", "pe_hi"]].round(2).to_string())
