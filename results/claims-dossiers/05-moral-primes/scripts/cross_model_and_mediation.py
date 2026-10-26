"""Dossier 05: (1) is the prime effect different between models (pair-level difference of differences)?
(2) talk route: pair-level prime-minus-placebo effect on the proposed price, agreement share, and on the price index."""
import os
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np, pandas as pd
OUT = ".."
ALL = pd.read_csv(f"{OUT}/game_table_used.csv")
D = pd.read_csv(f"{OUT}/game_mechanism_table.csv")
NB = 10000
def pair(df, model, th, arm, col):
    return df[(df.model == model) & (df.thinking == th) & (df.arm == arm)].set_index(["wording", "seed"])[col]
def boot(d, seed=20261025):
    d = np.asarray(d); n = len(d); rng = np.random.default_rng(seed)
    bm = d[rng.integers(0, n, (NB, n))].mean(axis=1)
    idx = np.arange(2 ** n) if n <= 20 else None
    signs = 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)
    p = float((np.abs((signs * d).mean(axis=1)) >= abs(d.mean()) - 1e-12).mean())
    return d.mean(), np.percentile(bm, 2.5), np.percentile(bm, 97.5), p, n
# (1) cross-model difference of effects, on the same 20 (wording, seed) pairs
rows = []
mets = ["market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
for ctrl in ["moral-placebo", "headline-chat"]:
    for arm, lab in [("moral-prime", "A"), ("moral-prime-b", "B")]:
        for qth in ["on", "off"]:
            for m in mets:
                src = ALL
                eg = (pair(src, "gptoss", "on", arm, m) - pair(src, "gptoss", "on", ctrl, m))
                eq = (pair(src, "qwen", qth, arm, m) - pair(src, "qwen", qth, ctrl, m))
                j = pd.concat([eg.rename("g"), eq.rename("q")], axis=1).dropna()
                dm, lo, hi, p, n = boot(j.g - j.q)
                rows.append(dict(effect=f"{lab} minus {ctrl}", qwen_mode=qth, metric=m, n=n, gptoss_effect=j.g.mean(), qwen_effect=j.q.mean(), gptoss_minus_qwen=dm, lo=lo, hi=hi, p_signflip=p))
X = pd.DataFrame(rows); X.to_csv(f"{OUT}/cross_model_effect_differences.csv", index=False, float_format="%.4f")
pd.set_option("display.width", 250)
print(X[X.metric.isin(["price_index", "profit_gain_index"])].round(3).to_string())
# (2) talk route, pair level
rows = []
cols = ["mean_proposed_price", "share_msgs_agree", "share_msgs_eth", "round1_quote", "price_index", "mean_abs_gap", "share_rounds_with_priced_talk", "words_per_msg", "n_msgs"]
for model, th in [("gptoss", "on"), ("qwen", "on"), ("qwen", "off")]:
    for arm, lab in [("moral-prime", "A"), ("moral-prime-b", "B")]:
        for ctrl in ["moral-placebo"]:
            for c in cols:
                e = pair(D, model, th, arm, c) - pair(D, model, th, ctrl, c)
                dm, lo, hi, p, n = boot(e.dropna())
                rows.append(dict(model=model, thinking=th, effect=f"{lab} minus {ctrl}", quantity=c, n=n, diff=dm, lo=lo, hi=hi, p_signflip=p))
    # placebo vs headline for talk
M = pd.DataFrame(rows); M.to_csv(f"{OUT}/talk_route_effects.csv", index=False, float_format="%.4f")
print(M.round(3).to_string())
# implied price-index change if quotes simply equal proposals: (delta proposed price)/2 vs actual delta price index; pair-level correlation
rows = []
for model, th in [("gptoss", "on"), ("qwen", "on"), ("qwen", "off")]:
    for arm in ["moral-prime", "moral-prime-b"]:
        dp = (pair(D, model, th, arm, "mean_proposed_price") - pair(D, model, th, "moral-placebo", "mean_proposed_price"))
        di = (pair(D, model, th, arm, "price_index") - pair(D, model, th, "moral-placebo", "price_index"))
        j = pd.concat([dp.rename("dp"), di.rename("di")], axis=1).dropna()
        rows.append(dict(model=model, thinking=th, arm=arm, n=len(j), mean_delta_proposed_price=j.dp.mean(), implied_delta_price_index=j.dp.mean() / 2, actual_delta_price_index=j.di.mean(),
                         share_of_effect_carried_by_proposal=(j.dp.mean() / 2) / j.di.mean(), pair_spearman=j.dp.rank().corr(j.di.rank()), pair_pearson=j.dp.corr(j.di)))
Y = pd.DataFrame(rows); Y.to_csv(f"{OUT}/proposal_carries_effect.csv", index=False, float_format="%.4f"); print(Y.round(3).to_string())
# round-1 first-look: quote of round 1 relative to the control, pooled by model
