"""Dossier 03, part 2: outcome vs strategic collusion. Rebuilds every counted
headline game's quote sequence from the raw events.jsonl (market events, last
event per round kept), then measures per firm-round:

  rival_undercut  rival's previous quote < own previous quote - 0.005 (the rival undercut me last round)
  rival_raise     rival's previous quote > rival's quote two rounds back + 0.005
  cut / raise     own quote below / above own previous quote by more than 0.005
  hold            own quote within 0.005 of own previous quote
  on_printed      own quote within 0.005 of a printed neutral example price (1.00 1.50 2.00 2.49 2.50 3.00 3.50 4.00)

Strategic signatures (per firm-game pooled to (model, mode, comm, pair); rounds 2+ for the
undercut measures, rounds 3+ for the raise measures):
  punish_rate     P(cut | rival undercut)              -- punishment / retaliation
  cut_baseline    P(cut | no rival undercut)
  reactivity      punish_rate - cut_baseline           -- conditional punishment beyond background cutting
  reward_rate     P(raise | rival raised)              -- reward / following a rival's price rise
  raise_baseline  P(raise | rival did not raise)
  reward_gap      reward_rate - raise_baseline
  return_rate     among firm-games that cut after a rival undercut: share whose quote later (within 3
                  rounds of the cut) returns to at least the pre-cut level -- the return path
Outcome-collusion signatures: hold share, share of quotes on a printed example price, price index.
Writes firmrounds_rebuilt.csv (one row per firm-round), strategic_by_cell.csv, strategic_contrasts.csv,
strategic_game_level.csv, strategic_corr.csv."""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common03 import *

PRINTED = np.array([1.0, 1.5, 2.0, 2.49, 2.5, 3.0, 3.5, 4.0])
TOL = 0.005


def events(row):
    p = os.path.join(RUNS_DIR, row.source_root, "trials", row.played_trial_id.split("__")[0], row.played_trial_id, "events.jsonl")
    rounds = {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            if '"kind":"market"' not in line and '"kind": "market"' not in line:
                continue
            e = json.loads(line)
            if e.get("kind") == "market":
                rounds[int(e["round"])] = e["prices"]
    return rounds


def build():
    rows = []
    for model in ["qwen", "oss"]:
        h = headline(model, include_hrep=(model == "oss"))
        for r in h.itertuples():
            ev = events(r)
            seats = sorted({s for pr in ev.values() for s in pr if s.startswith("llm")})
            rr = sorted(ev)
            for s in seats:
                riv = [x for x in seats if x != s][0]
                for k, t in enumerate(rr):
                    rows.append((model, r.mode, r.comm, r.arm, int(r.penalty_point), r.pair, r.trial_id, s, t,
                                 float(ev[t][s]), float(ev[t][riv])))
    fr = pd.DataFrame(rows, columns=["model", "mode", "comm", "arm", "penalty_point", "pair", "trial_id", "seat", "round", "quote", "rival_quote"])
    fr = fr.sort_values(["model", "trial_id", "seat", "round"]).reset_index(drop=True)
    g = fr.groupby(["model", "trial_id", "seat"])
    fr["own_prev"] = g.quote.shift(1); fr["riv_prev"] = g.rival_quote.shift(1); fr["riv_prev2"] = g.rival_quote.shift(2)
    fr["rival_undercut"] = fr.riv_prev < fr.own_prev - TOL
    fr["rival_raise"] = fr.riv_prev > fr.riv_prev2 + TOL
    fr["cut"] = fr.quote < fr.own_prev - TOL
    fr["raise_"] = fr.quote > fr.own_prev + TOL
    fr["hold"] = (fr.quote - fr.own_prev).abs() <= TOL
    fr["on_printed"] = (np.abs(fr.quote.values[:, None] - PRINTED[None, :]) <= TOL).any(1)
    for c in ["rival_undercut", "rival_raise", "cut", "raise_", "hold", "on_printed"]:
        fr[c] = fr[c].astype(float)
    fr.loc[fr.own_prev.isna(), ["rival_undercut", "cut", "raise_", "hold"]] = np.nan
    fr.loc[fr.riv_prev2.isna(), ["rival_raise"]] = np.nan
    # return path: after a punishing cut at round t (cut & rival_undercut), does own quote come back to >= own_prev(t) within 3 rounds?
    fr["ret"] = np.nan
    for key, gg in fr.groupby(["model", "trial_id", "seat"]):
        q = gg.quote.values; op = gg.own_prev.values; pun = (gg.cut.values == 1) & (gg.rival_undercut.values == 1)
        idx = gg.index.values
        for i in np.where(pun)[0]:
            if i + 1 < len(q):
                fut = q[i + 1:i + 4]
                fr.loc[idx[i], "ret"] = float((fut >= op[i] - TOL).any())
    return fr


fr = build()
fr.to_csv(f"{OUT}/firmrounds_rebuilt.csv.gz", index=False, compression="gzip")


def rates(g):
    def cp(a, b):
        b = b == 1
        return np.nan if b.sum() == 0 else float((a[b] == 1).mean())
    s = g[g.own_prev.notna()]
    out = dict(n_firm_rounds=len(s),
               n_undercut_events=int((s.rival_undercut == 1).sum()),
               punish_rate=cp(s.cut, s.rival_undercut), cut_baseline=cp(s.cut, s.rival_undercut == 0),
               retaliate_rate=cp((s.quote < s.riv_prev - TOL).astype(float), s.rival_undercut),
               follow_rate=cp(((s.quote - s.riv_prev).abs() <= TOL).astype(float), s.rival_undercut),
               hold_share=float((s.hold == 1).mean()) if len(s) else np.nan,
               on_printed_share=float(g.on_printed.mean()))
    s3 = g[g.riv_prev2.notna()]
    out.update(n_raise_events=int((s3.rival_raise == 1).sum()),
               reward_rate=cp(s3.raise_, s3.rival_raise), raise_baseline=cp(s3.raise_, s3.rival_raise == 0))
    r = g.ret.dropna()
    out.update(n_punish_cuts=len(r), return_rate=float(r.mean()) if len(r) else np.nan)
    out["reactivity"] = out["punish_rate"] - out["cut_baseline"] if out["punish_rate"] == out["punish_rate"] else np.nan
    out["reward_gap"] = out["reward_rate"] - out["raise_baseline"] if out["reward_rate"] == out["reward_rate"] else np.nan
    return pd.Series(out)


fr["grp"] = fr.model + "_" + fr["mode"]
COMMON = [("chat", 1), ("chat", 3), ("chat", 5), ("tacit", 1), ("tacit", 5)]
fr["common_cell"] = [(c, p) in COMMON for c, p in zip(fr.comm, fr.penalty_point)]
fr_main = fr[~fr.arm.str.startswith("hrep-")]

# by cell (pooled over pairs): descriptive
bycell = fr_main.groupby(["grp", "comm", "penalty_point"]).apply(rates, include_groups=False).reset_index()
bycell.to_csv(f"{OUT}/strategic_by_cell.csv", index=False)
# by group, pooled over the five common cells (descriptive)
bygrp = fr_main[fr_main.common_cell].groupby(["grp", "comm"]).apply(rates, include_groups=False).reset_index()
bygrp_all = fr_main[fr_main.common_cell].groupby(["grp"]).apply(rates, include_groups=False).reset_index()
bygrp_all["comm"] = "chat+tacit (5 common cells)"
pd.concat([bygrp_all, bygrp]).to_csv(f"{OUT}/strategic_by_group.csv", index=False)

# pair-level (5 common cells pooled within pair) for paired contrasts
pp = fr_main[fr_main.common_cell].groupby(["grp", "pair"]).apply(rates, include_groups=False).reset_index()
pp.to_csv(f"{OUT}/strategic_by_pair.csv", index=False)
SIG = ["punish_rate", "cut_baseline", "reactivity", "retaliate_rate", "follow_rate", "reward_rate", "raise_baseline", "reward_gap", "return_rate", "hold_share", "on_printed_share"]
con = []
W = {m: pp.pivot(index="pair", columns="grp", values=m) for m in SIG}
for m in SIG:
    w = W[m]
    for a, b, fam in [("qwen_t1", "qwen_t0", "qwen on - off"), ("oss_t1", "qwen_t1", "oss - qwen on"), ("oss_t1", "qwen_t0", "oss - qwen off")]:
        con.append(summarise((w[a] - w[b]).dropna().values, contrast=f"{a} minus {b}", family=fam, metric=m,
                             mean_a=w[a].mean(), mean_b=w[b].mean()))
    for g in ["oss_t1", "qwen_t1", "qwen_t0"]:
        if m in ("reactivity", "reward_gap"):
            con.append(summarise(W[m][g].dropna().values, contrast=f"{g}: {m} vs 0", family="vs zero", metric=m, mean_a=W[m][g].mean(), mean_b=0.0))
# Qwen only, all 12 headline cells pooled within pair (the thinking-mode ad hoc's pooling), on - off
pq = fr_main[fr_main.model == "qwen"].groupby(["grp", "pair"]).apply(rates, include_groups=False).reset_index()
pq.to_csv(f"{OUT}/strategic_by_pair_qwen12.csv", index=False)
for m in SIG:
    w = pq.pivot(index="pair", columns="grp", values=m)
    con.append(summarise((w.qwen_t1 - w.qwen_t0).dropna().values, contrast="qwen_t1 minus qwen_t0 (12 cells)", family="qwen on - off, 12 cells", metric=m,
                         mean_a=w.qwen_t1.mean(), mean_b=w.qwen_t0.mean()))
con = holm(pd.DataFrame(con), by=["family"])
con.to_csv(f"{OUT}/strategic_contrasts.csv", index=False)

# game-level: does strategic reactivity go with higher prices? (Spearman and Pearson, per group)
gl = fr_main.groupby(["grp", "comm", "penalty_point", "pair", "trial_id"]).apply(rates, include_groups=False).reset_index()
runs = pd.concat([headline("qwen"), headline("oss")])
runs["grp"] = runs.model + "_" + runs["mode"]
runs = runs[["grp", "trial_id", "price_index", "profit_gain_index", "competitive_share", "matching_share", "market_price_mean"]]
gl = gl.merge(runs, on=["grp", "trial_id"], how="left", validate="one_to_one")
gl.to_csv(f"{OUT}/strategic_game_level.csv", index=False)
cr = []
for g, s in gl.groupby("grp"):
    for xv in ["reactivity", "punish_rate", "on_printed_share", "hold_share"]:
        for yv in ["price_index", "profit_gain_index"]:
            sp, pe, n = corr_both(s[xv], s[yv])
            cr.append(dict(grp=g, x=xv, y=yv, spearman=sp, pearson=pe, n_games=n))
pd.DataFrame(cr).to_csv(f"{OUT}/strategic_corr.csv", index=False)
print(pd.concat([bygrp_all, bygrp]).round(3).to_string())
print(con[["contrast", "metric", "n_pairs", "mean_a", "mean_b", "effect", "ci_lo", "ci_hi", "p_holm"]].round(3).to_string())
print(pd.DataFrame(cr).round(3).to_string())
