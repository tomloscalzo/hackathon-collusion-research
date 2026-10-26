#!/usr/bin/env python3
"""5-tick start (start-5tick: round-1 quotes capped at 1.00-1.05) vs private chat (headline-chat), both at p3.
usage: python -X utf8 analyze.py --data <analysis_final dir> [--out .]"""
import argparse, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as c
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", default="."); A = ap.parse_args()
ARM, CTL = "start-5tick", "headline-chat"
rd = c.load_rounds(A.data); rd["idx"] = (rd.market_price - 1) / 2
mkt = rd.drop_duplicates(["trial_id", "round"]).set_index(["trial_id", "round"]).idx
run = pd.read_csv(f"{c.step(A.data,'neutral')}/run.csv", low_memory=False)
run = run[(run.status == "done") & (run.penalty_point == 3) & run.arm.isin([ARM, CTL])][["trial_id", "arm", "thinking", "wording", "seed", "price_index", "rounds_played"]]
M = mkt.reset_index().merge(run, on="trial_id")
# ---- price paths by round
PB = M.groupby(["arm", "thinking", "round"]).idx.agg(["mean", "count"]).reset_index().rename(columns={"mean": "price_index", "count": "n_games"})
PB.to_csv(f"{A.out}/paths_by_round.csv", index=False)
# ---- windows, paired (wording, seed); a pair needs both games to have a round in the window
WIN = {"all rounds": (1, 99), "excluding round 1": (2, 99), "rounds 5+": (5, 99), "rounds 10+": (10, 99)}
rows = []
for mode in ("off", "on"):
    for wn, (lo, hi) in WIN.items():
        g = M[(M["round"] >= lo) & (M["round"] <= hi)].groupby(["arm", "thinking", "wording", "seed"]).idx.mean().reset_index()
        g = g[g.thinking == mode]
        a = g[g.arm == ARM].set_index(["wording", "seed"]).idx; b = g[g.arm == CTL].set_index(["wording", "seed"]).idx
        j = pd.concat([a.rename("a"), b.rename("c")], axis=1, join="inner").dropna()
        m, l, h = c.boot((j.a - j.c).to_numpy(), f"5t{mode}{wn}")
        rows.append(dict(run="neutral", mode=mode, window=wn, n_pairs=len(j), arm_mean=j.a.mean(), control_mean=j.c.mean(), diff=m, ci_lo=l, ci_hi=h))
# anchored: all-rounds only from run.csv (no rounds table); windows from the provisional extras file
ga = c.load_games(A.data, "anchored")
for mode in ("off", "on"):
    x = c.contrast(ga, ARM, 3, CTL, 3, mode, "price_index", f"5tanch{mode}")
    rows.append(dict(run="anchored", mode=mode, window="all rounds", **x))
pv = pd.read_csv(f"{A.out}/fivetick_provisional.csv"); pv = pv[pv.run == "anchored"]
for _, r in pv[pv.window != "all rounds"].iterrows():
    rows.append(dict(run="anchored (provisional file)", mode={"t0": "off", "t1": "on"}[r["mode"]], window=r.window, n_pairs=r.n, arm_mean=r.arm_mean, control_mean=r.control_mean, diff=r["diff"], ci_lo=r.lo, ci_hi=r.hi))
W = pd.DataFrame(rows); W.to_csv(f"{A.out}/five_tick_windows.csv", index=False)
# ---- do firms climb back up? per game, 5-tick arm vs control
CL = []
llm = rd[rd.seat.str.startswith("llm")].copy(); llm["qi"] = (llm.quote - 1) / 2
firm = llm.merge(run[["trial_id", "arm", "thinking"]], on="trial_id")
for mode in ("off", "on"):
    for arm in (ARM, CTL):
        ids = run[(run.arm == arm) & (run.thinking == mode)].trial_id; n = len(ids)
        gm = mkt[mkt.index.get_level_values(0).isin(ids)].reset_index()
        r1 = gm[gm["round"] == 1].set_index("trial_id").idx; late = gm[gm["round"] >= 2].groupby("trial_id").idx
        mx = late.max(); first_half = gm[(gm["round"] >= 2) & (gm["round"] <= 5)].groupby("trial_id").idx.mean(); lh = gm[gm["round"] >= 6].groupby("trial_id").idx.mean()
        f = firm[(firm.arm == arm) & (firm.thinking == mode) & (firm["round"] >= 2)]
        fm = f.groupby("trial_id").qi.max()
        # first round a market price index >= 0.5 (price >= 2.00) is reached
        fr = gm[gm.idx >= 0.5].groupby("trial_id")["round"].min()
        CL.append(dict(mode=mode, arm=arm, games_with_rounds=len(r1), round1_price_index=r1.mean(),
                       share_games_market_ever_ge_0_5=(mx >= 0.5).sum() / len(mx), share_games_market_ever_ge_0_8=(mx >= 0.8).sum() / len(mx),
                       share_games_any_firm_quote_ge_0_5_after_r1=(fm >= 0.5).sum() / len(fm),
                       share_firm_rounds_ge_0_5_after_r1=(f.qi >= 0.5).mean(), median_first_round_ge_0_5=fr.median(),
                       rounds2to5_mean_index=first_half.mean(), rounds6plus_mean_index=lh.mean(), mean_of_game_max_after_r1=mx.mean()))
CL = pd.DataFrame(CL); CL.to_csv(f"{A.out}/climb_back.csv", index=False)
# ---- figure: drawn by five_tick_figure.py from paths_by_round.csv (written above), "slug: short label" legend from the shared glossary
import os, runpy, sys; sys.argv = [sys.argv[0], "--out", A.out]; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "five_tick_figure.py"))
