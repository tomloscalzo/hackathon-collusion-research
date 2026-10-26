#!/usr/bin/env python3
"""Market structure: 3-firm chat (n3-group) vs 2-firm chat (headline-chat), and the planted cheater (n3-cheater) vs n3-group, all at p3.
The cheater is a scripted third firm that quotes below the two LLM firms and then, in its defect round, drops once (see ANALYSIS.md).
usage: python -X utf8 analyze.py --data <analysis_final dir> [--out .]"""
import argparse, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as c
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", default="."); A = ap.parse_args()
rows = []
for run in ("neutral", "anchored"):
    g = c.load_games(A.data, run)
    for arm, carm, lab in (("n3-group", "headline-chat", "3 firms vs 2 firms"), ("n3-cheater", "n3-group", "cheater vs 3-firm chat")):
        for mode in ("off", "on"):
            for col in ("price_index", "comp_share"):
                rows.append(dict(run=run, contrast=lab, mode=mode, measure=col, **c.contrast(g, arm, 3, carm, 3, mode, col, f"{run}{arm}{mode}{col}")))
G = pd.DataFrame(rows); G.to_csv(f"{A.out}/market_structure_contrasts.csv", index=False)
# ---- punishment of the defector (run.csv), both runs
P = []
for run in ("neutral", "anchored"):
    g = c.load_games(A.data, run); k = g[(g.arm == "n3-cheater") & (g.penalty_point == 3)]
    for mode in ("off", "on"):
        s = k[k.thinking == mode]; d = s[s.defect_round.notna()]
        P.append(dict(run=run, mode=mode, games=len(s), games_with_defection=len(d), median_defect_round=d.defect_round.median(),
                      punished_within_3=int((d.coalition_punished == 1).sum()), share_punished_within_3=(d.coalition_punished == 1).mean(),
                      ever_punished=int(d.punish_round_first.notna().sum()), median_lag_if_punished=d.punish_lag.median()))
P = pd.DataFrame(P); P.to_csv(f"{A.out}/punishment.csv", index=False)
# ---- paths (neutral rounds table)
rd = c.load_rounds(A.data); rd["idx"] = (rd.market_price - 1) / 2; rd["qi"] = (rd.quote - 1) / 2
mkt = rd.drop_duplicates(["trial_id", "round"]).set_index(["trial_id", "round"]).idx
llm = rd[rd.seat.str.startswith("llm")].groupby(["trial_id", "round"]).qi.mean()
tr = pd.read_csv(f"{c.step(A.data,'neutral')}/run.csv", low_memory=False)
tr = tr[tr.status == "done"][["trial_id", "arm", "thinking", "penalty_point", "wording", "seed", "defect_round"]]
tr = tr[tr.penalty_point == 3]
def path_by_round(arm, mode, series):
    ids = tr[(tr.arm == arm) & (tr.thinking == mode)].trial_id
    s = series[series.index.get_level_values(0).isin(ids)].groupby(level=1).agg(["mean", "count"]); return s
paths = []
for arm in ("headline-chat", "n3-group", "n3-cheater"):
    for mode in ("off", "on"):
        for nm, ser in (("market_price_index", mkt), ("llm_quote_index", llm)):
            s = path_by_round(arm, mode, ser).reset_index(); s.insert(0, "arm", arm); s.insert(1, "mode", mode); s.insert(2, "series", nm); paths.append(s)
pd.concat(paths).rename(columns={"mean": "value", "count": "n_games"}).to_csv(f"{A.out}/paths_by_round.csv", index=False)
# event time: cheater games with a defection vs matched n3-group game at the same absolute round
ch = tr[(tr.arm == "cheater_dummy") | ((tr.arm == "n3-cheater") & tr.defect_round.notna())]
ctl = tr[tr.arm == "n3-group"].set_index(["wording", "seed", "thinking"]).trial_id
EV = []
for _, r in ch.iterrows():
    cid = ctl.get((r.wording, r.seed, r.thinking))
    for k in range(-5, 11):
        rr = int(r.defect_round) + k
        for nm, ser in (("market_price_index", mkt), ("llm_quote_index", llm)):
            a = ser.get((r.trial_id, rr), np.nan); b = ser.get((cid, rr), np.nan) if cid is not None else np.nan
            EV.append(dict(trial_id=r.trial_id, mode=r.thinking, wording=r.wording, seed=r.seed, k=k, series=nm, cheater=a, control=b))
EV = pd.DataFrame(EV); EV.to_csv(f"{A.out}/event_time_by_game.csv", index=False)
S = EV.dropna(subset=["cheater", "control"]).groupby(["mode", "series", "k"]).agg(cheater=("cheater", "mean"), control=("control", "mean"), n_games=("cheater", "size")).reset_index()
S.to_csv(f"{A.out}/event_time_paths.csv", index=False)
# before/after summary: LLM quote index, window means, paired difference-in-differences vs matched n3-group
W = {"pre (k -3..-1)": (-3, -1), "defection round (k 0)": (0, 0), "post 1-3": (1, 3), "post 4-8": (4, 8)}
out = []
for mode in ("off", "on"):
    for ser in ("llm_quote_index", "market_price_index"):
        e = EV[(EV["mode"] == mode) & (EV.series == ser)]
        def win(lo, hi, col):
            x = e[(e.k >= lo) & (e.k <= hi)].groupby("trial_id")[col].mean(); return x
        pre_a, pre_c = win(-3, -1, "cheater"), win(-3, -1, "control")
        for wn, (lo, hi) in W.items():
            a, b = win(lo, hi, "cheater"), win(lo, hi, "control")
            j = pd.concat([a.rename("a"), b.rename("c")], axis=1).dropna()
            m, l, h = c.boot((j.a - j.c).to_numpy(), f"ev{mode}{ser}{wn}")
            did = pd.concat([(a - pre_a).rename("a"), (b - pre_c).rename("c")], axis=1).dropna()
            m2, l2, h2 = c.boot((did.a - did.c).to_numpy(), f"did{mode}{ser}{wn}")
            out.append(dict(mode=mode, series=ser, window=wn, n_games=len(j), cheater=j.a.mean(), control=j.c.mean(), diff=m, ci_lo=l, ci_hi=h,
                            change_vs_pre_diff=m2, change_ci_lo=l2, change_ci_hi=h2))
O = pd.DataFrame(out); O.to_csv(f"{A.out}/event_time_windows.csv", index=False)
# ---- figure: left = market price index by round, 3 arms; right = LLM quote index in event time vs matched control
#      (drawn by figures.py from the CSVs just written; re-render alone with: python -X utf8 figures.py)
from figures import fig_market_structure
fig_market_structure(pd.read_csv(f"{A.out}/paths_by_round.csv"), pd.read_csv(f"{A.out}/event_time_paths.csv"), f"{A.out}/market_structure.png")
pd.set_option("display.width", 250)
print(G.round(3).to_string()); print(P.round(3).to_string()); print(O.round(3).to_string()); print(S[S.series=="llm_quote_index"].round(3).to_string())
