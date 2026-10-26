#!/usr/bin/env python3
"""Ethics rule on one firm: m-asym (1 of 2) vs headline-chat p3; n3-ethics (1 of 3) vs n3-group p3. Paired on (wording, seed).
usage: python -X utf8 analyze.py --data <analysis_final dir> [--out .]"""
import argparse, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as c
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", default="."); A = ap.parse_args()
SPEC = [("m-asym", "headline-chat", "1 of 2"), ("n3-ethics", "n3-group", "1 of 3")]
rows = []
# ---- game-level price index and competitive share (neutral = primary, anchored = check)
for run in ("neutral", "anchored"):
    g = c.load_games(A.data, run)
    for arm, carm, lab in SPEC:
        for mode in ("off", "on"):
            for col in ("price_index", "comp_share"):
                rows.append(dict(run=run, arm=arm, level="game", measure=col, mode=mode, **c.contrast(g, arm, 3, carm, 3, mode, col, f"{run}{arm}{mode}{col}")))
# ---- per-firm: bound firm, unbound others, control firms (all LLM seats)
for run in ("neutral", "anchored"):
    s = c.step(A.data, run)
    r = pd.read_csv(f"{s}/run.csv", low_memory=False)[["row_id", "arm", "thinking", "penalty_point", "wording", "seed", "status"]]
    f = pd.read_csv(f"{s}/run_firms.csv", low_memory=False)
    f = f[f.seat_kind == "llm"].merge(r, on="row_id")
    f = f[f.status == "done"]; f["rule_bound"] = ((f.rule_bound == 1) | (f.condition_text == "no_coordinate_rule")).astype(int); f["price_idx_firm"] = (f.quote_mean - 1) / 2
    for arm, carm, lab in SPEC:
        for mode in ("off", "on"):
            for col in ("competitive_share", "price_idx_firm"):
                a = f[(f.arm == arm) & (f.thinking == mode)]
                bound = a[a.rule_bound == 1].groupby(["wording", "seed"])[col].mean()
                other = a[a.rule_bound == 0].groupby(["wording", "seed"])[col].mean()
                ctl = f[(f.arm == carm) & (f.penalty_point == 3) & (f.thinking == mode)].groupby(["wording", "seed"])[col].mean()
                for nm, x, y in (("bound firm - control firms", bound, ctl), ("unbound others - control firms", other, ctl), ("bound - unbound (same game)", bound, other)):
                    j = pd.concat([x.rename("a"), y.rename("c")], axis=1, join="inner").dropna()
                    d = (j.a - j.c).to_numpy(); m, lo, hi = c.boot(d, f"{run}{arm}{mode}{col}{nm}")
                    rows.append(dict(run=run, arm=arm, level="firm", measure=f"{col} | {nm}", mode=mode, n_pairs=len(d), arm_mean=j.a.mean(), control_mean=j.c.mean(), diff=m, ci_lo=lo, ci_hi=hi))
R = pd.DataFrame(rows); R.to_csv(f"{A.out}/ethics_rule_contrasts.csv", index=False)
# ---- figure (neutral): drawn by ethics_figure.py from ethics_rule_contrasts.csv (written above), "slug: short label" titles from the shared glossary
import os, runpy, sys; sys.argv = [sys.argv[0], "--out", A.out]; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ethics_figure.py"))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
print(R.round(3).drop(columns=["level"]).to_string())
