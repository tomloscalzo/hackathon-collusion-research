#!/usr/bin/env python3
"""Incentive texts: m-inc-target (profit target with job risk, owner's text) and m-inc-joint (maximise joint profit) vs headline-chat p3.
usage: python -X utf8 analyze.py --data <analysis_final dir> [--out .]"""
import argparse, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as c
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", default="."); A = ap.parse_args()
ARMS = ["m-inc-target", "m-inc-joint"]
MEAS = [("price_index", "Price index"), ("comp_share", "Competitive share"), ("profit_gain_index", "Profit gain index")]
rows = []
for run in ("neutral", "anchored"):
    g = c.load_games(A.data, run)
    for arm in ARMS:
        for mode in ("off", "on"):
            for col, _ in MEAS:
                rows.append(dict(run=run, arm=arm, mode=mode, measure=col, **c.contrast(g, arm, 3, "headline-chat", 3, mode, col, f"{run}{arm}{mode}{col}")))
R = pd.DataFrame(rows); R.to_csv(f"{A.out}/incentives_contrasts.csv", index=False)
# figure drawn by figures.py (re-render alone from the committed CSV with: python -X utf8 figures.py)
from figures import fig_incentives
fig_incentives(R, f"{A.out}/incentives.png")
print(R.round(3).to_string())
