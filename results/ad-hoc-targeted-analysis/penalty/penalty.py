"""Targeted analysis 2: penalty slope (point 5 minus point 1) by thinking mode and communication, neutral run.
Usage: STEP1_DIR=<step1 folder> python penalty.py"""
import numpy as np, pandas as pd
from common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
r = load_run()
r = r[r.arm.isin(["headline-tacit", "headline-chat", "headline-monitored"])].copy()
r["cond"] = r.arm.map({"headline-tacit": "tacit", "headline-chat": "chat", "headline-monitored": "monitored"})
r["mode"] = r.thinking.map({"off": "t0", "on": "t1"})
THETA = {1: 0.7029, 3: 0.5459, 4: 0.3249, 5: 0.0}      # sustainable price index (theory curve)
THEORY_GAIN = {1: 0.912, 3: 0.794, 4: 0.544, 5: 0.0}   # same curve on the profit gain index (from FINAL_NUMBERS.md)
def slope(g, col):
    p = g.pivot_table(index=["wording", "seed"], columns="penalty_point", values=col, aggfunc="mean")
    return (p[5] - p[1]).dropna()
# 1. cell means by penalty point
rows = []
for (c, m, pp), g in r.groupby(["cond", "mode", "penalty_point"]):
    for col in ["profit_gain_index", "price_index"]:
        mu, lo, hi = boot_ci(g.groupby(["wording", "seed"])[col].mean())
        rows.append(dict(cond=c, mode=m, penalty_point=pp, metric=col, n=len(g), mean=mu, lo=lo, hi=hi,
                         theory=THEORY_GAIN[pp] if col == "profit_gain_index" else THETA[pp]))
cells = pd.DataFrame(rows); cells.to_csv("cells_by_penalty_point.csv", index=False)
# 2. slopes
rows = []; S = {}
for col in ["profit_gain_index", "price_index"]:
    th = (0 - THEORY_GAIN[1]) if col == "profit_gain_index" else (0 - THETA[1])
    for (c, m), g in r.groupby(["cond", "mode"]):
        d = slope(g, col); S[(col, c, m)] = d; mu, lo, hi = boot_ci(d)
        rows.append(dict(metric=col, cond=c, mode=m, n_pairs=len(d), slope_p5_minus_p1=mu, lo=lo, hi=hi,
                         p_signflip=signflip_p(d), theory_slope=th))
sl = pd.DataFrame(rows); sl.to_csv("slopes.csv", index=False); print(sl.round(3).to_string())
# 3. interactions (thinking on - off of the slope), gain index, Holm over the declared family of four
rows = []
for c in ["tacit", "chat", "monitored"]:
    d = (S[("profit_gain_index", c, "t1")] - S[("profit_gain_index", c, "t0")]).dropna()
    mu, lo, hi = boot_ci(d); rows.append(dict(contrast=f"(p5-p1) x thinking, {c}", n_pairs=len(d), diff=mu, lo=lo, hi=hi, p_signflip=signflip_p(d)))
# monitoring x thinking (family member in FINAL_NUMBERS): (monitored - chat) pooled over points, on minus off
def mon_eff(m):
    g = r[r["mode"] == m].pivot_table(index=["wording", "seed"], columns="cond", values="profit_gain_index", aggfunc="mean")
    return g["monitored"] - g["chat"]
d = (mon_eff("t1") - mon_eff("t0")).dropna(); mu, lo, hi = boot_ci(d)
rows.append(dict(contrast="monitoring x thinking (pooled points)", n_pairs=len(d), diff=mu, lo=lo, hi=hi, p_signflip=signflip_p(d)))
ia = pd.DataFrame(rows); ia["p_holm"] = holm(ia.p_signflip.values)
# price-index version (exploratory, no Holm)
for c in ["tacit", "chat", "monitored"]:
    d = (S[("price_index", c, "t1")] - S[("price_index", c, "t0")]).dropna(); mu, lo, hi = boot_ci(d)
    ia.loc[len(ia)] = dict(contrast=f"price index: (p5-p1) x thinking, {c}", n_pairs=len(d), diff=mu, lo=lo, hi=hi, p_signflip=signflip_p(d), p_holm=np.nan)
ia.to_csv("interactions.csv", index=False); print(ia.round(3).to_string())
# 4. figure: gain index by penalty point vs theory curve (drawn by figures.py from the CSV just written;
#    re-render alone with: python -X utf8 figures.py)
from figures import fig_penalty
fig_penalty(pd.read_csv("cells_by_penalty_point.csv"))
