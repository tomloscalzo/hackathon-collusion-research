"""Dossier 06: 5-tick start. Independent re-derivation: whole-game five metrics, windows, mechanism diagnostics.
Run: bash aff.sh -X utf8 main.py   (writes CSVs to ../)"""
import sys; sys.path.insert(0, ".")
from common import *
OUT = ".."
rng = np.random.default_rng(20261025)
METS = [("spread", "Average absolute spread (raw 1.00-5.00)"), ("price_index", "Price index"), ("pgi", "Profit gain index"),
        ("comp", "Competitive share"), ("match", "Matching share")]
def boot(d, B=10000):
    d = np.asarray(d, float); n = len(d)
    idx = rng.integers(0, n, (B, n)); m = d[idx].mean(1)
    return np.percentile(m, [2.5, 97.5])
_SG = {}
def signflip_p(d):
    d = np.asarray(d, float); n = len(d); obs = abs(d.mean())
    if n <= 20:
        if n not in _SG:
            bits = np.arange(2 ** n, dtype=np.int64)
            _SG[n] = (1 - 2 * ((bits[:, None] >> np.arange(n)) & 1)).astype(np.float32)
        return float((np.abs(_SG[n] @ d.astype(np.float32)) / n >= obs - 1e-6).mean())
    sg = rng.choice([-1, 1], (200000, n)); return ((np.abs((sg * d).mean(1)) >= obs - 1e-12).sum() + 1) / 200001
def holm(ps):
    ps = np.array(ps); o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for rank_, i in enumerate(o):
        run = max(run, (m - rank_) * ps[i]); adj[i] = min(1, run)
    return adj
def summarize(a, c, label, extra):
    d = a - c; n = len(d); lo, hi = boot(d); se = d.std(ddof=1) / np.sqrt(n)
    return dict(extra, quantity=label, n_pairs=n, arm_mean=a.mean(), control_mean=c.mean(), diff=d.mean(), ci_lo=lo, ci_hi=hi,
                p_signflip=signflip_p(d), se=se, mde_2p8se=2.8 * se)
# ---------- per-game table ----------
games = []; frs = {}
for m in SRC:
    r, rd = load(m); f = firm_rounds(rd); f["model"] = m; frs[m] = f
    r = r.copy(); r["model"] = m
    r["spread"] = r.market_price_mean  # standard definition: mean MARKET price (lowest quote of the round)
    r["pgi"] = r.profit_gain_index; r["comp"] = r.competitive_share; r["match"] = r.matching_share
    r["pair"] = r.wording.astype(int).astype(str) + "_" + r.seed.astype(int).astype(str)
    games.append(r[["model", "arm", "pair", "trial_id", "rounds_played", "spread", "price_index", "pgi", "comp", "match", "round1_quote_mean"]])
G = pd.concat(games, ignore_index=True); G.to_csv(f"{OUT}/per_game_metrics.csv", index=False)
# ---------- whole-game contrasts ----------
rows = []
for m in SRC:
    g = G[G.model == m]; a = g[g.arm == ARM].set_index("pair"); c = g[g.arm == CTL].set_index("pair"); ps = sorted(set(a.index) & set(c.index))
    for k, lab in METS:
        rows.append(summarize(a.loc[ps, k].values, c.loc[ps, k].values, lab, dict(model=m, metric=k, window="all rounds")))
W = pd.DataFrame(rows)
W["holm_p_famA15"] = holm(W.p_signflip.values)   # family A: 5 metrics x 3 model-modes = 15 whole-game tests
W.to_csv(f"{OUT}/whole_game_contrasts.csv", index=False)
# ---------- windows from round records ----------
WIN = [("round 1", 1, 1), ("rounds 2-5 (early)", 2, 5), ("rounds 6-10 (middle)", 6, 10), ("rounds 11+ (late)", 11, 99), ("rounds 2+ (excl. round 1)", 2, 99)]
def win_metrics(f, lo, hi):
    x = f[(f["round"] >= lo) & (f["round"] <= hi)]
    out = {}
    out["spread"] = x.groupby("trial_id").mp.mean()
    out["price_index"] = x.groupby("trial_id").price_index_fr.mean()
    out["pgi"] = x.groupby("trial_id").profit.mean() / 40.0
    xp = x[x.has_prev]
    out["comp"] = xp.groupby("trial_id").comp.mean(); out["match"] = xp.groupby("trial_id").match.mean()
    return pd.DataFrame(out)
wrows = []
for m in SRC:
    f = frs[m]; g = G[G.model == m]; tid = g.set_index("trial_id")
    for wl, lo, hi in WIN:
        wm = win_metrics(f, lo, hi); wm["arm"] = tid.arm.reindex(wm.index); wm["pair"] = tid.pair.reindex(wm.index)
        for k, lab in METS:
            a = wm[wm.arm == ARM].set_index("pair")[k].dropna(); c = wm[wm.arm == CTL].set_index("pair")[k].dropna()
            ps = sorted(set(a.index) & set(c.index))
            if len(ps) < 5: continue
            wrows.append(summarize(a.loc[ps].values, c.loc[ps].values, lab, dict(model=m, metric=k, window=wl)))
WW = pd.DataFrame(wrows)
mask = WW.window.isin(["rounds 2-5 (early)", "rounds 6-10 (middle)", "rounds 11+ (late)"])
WW["holm_p_famB"] = np.nan; WW.loc[mask, "holm_p_famB"] = holm(WW.loc[mask, "p_signflip"].values)  # family B: early/middle/late x 5 metrics x 3 models (exploratory)
print("family B size", int(mask.sum()))
WW.to_csv(f"{OUT}/window_contrasts.csv", index=False)
# ---------- paths by round ----------
prow = []
for m in SRC:
    f = frs[m]; g = G[G.model == m].set_index("trial_id")
    x = f.groupby(["trial_id", "round"]).agg(pi=("price_index_fr", "mean"), q=("q", "mean"), atfl=("at_floor", "mean")).reset_index()
    x["arm"] = g.arm.reindex(x.trial_id).values
    for (arm, rnd), s in x.groupby(["arm", "round"]):
        prow.append(dict(model=m, arm=arm, round=rnd, n_games=len(s), price_index=s.pi.mean(), mean_quote=s.q.mean(), share_firms_at_floor_le_1p05=s.atfl.mean()))
pd.DataFrame(prow).to_csv(f"{OUT}/paths_by_round.csv", index=False)
# ---------- mechanism diagnostics (firm-rounds from round 2) ----------
mrows = []; gm = []
for m in SRC:
    f = frs[m]; g = G[G.model == m].set_index("trial_id")
    x = f[f.has_prev].copy()
    x["below"] = x.q < x.riv_prev - 1e-9; x["equal"] = (x.q - x.riv_prev).abs() < 1e-9; x["above"] = x.q > x.riv_prev + 1e-9
    x["eq_floor"] = x.equal & (x.q <= 1.0 + 1e-9); x["eq_above_floor"] = x.equal & (x.q > 1.0 + 1e-9)
    x["near_floor"] = x.q <= 1.05 + 1e-9
    x["own_raise"] = x.q > x.own_prev + 1e-9
    x["jump_from_floor"] = (x.own_prev <= 1.05 + 1e-9) & (x.q > 1.05 + 1e-9)
    gg = x.groupby("trial_id")
    d = pd.DataFrame({"share_below_rival": gg.below.mean(), "share_equal_rival_any_level": gg.equal.mean(), "share_equal_at_exact_floor": gg.eq_floor.mean(),
                      "share_equal_above_floor_(matching)": gg.eq_above_floor.mean(), "share_above_rival": gg.above.mean(), "share_firmrounds_le_1p05": gg.near_floor.mean(),
                      "share_raise_vs_own_prev": gg.own_raise.mean()})
    ab = x[x.q > 1.05 + 1e-9].groupby("trial_id")
    d["matching_among_above_floor_quotes"] = ab.eq_above_floor.mean()
    d["undercut_among_above_floor_quotes"] = ab.below.mean()
    fl = x[x.own_prev <= 1.05 + 1e-9].groupby("trial_id")
    d["escape_prob_per_floor_firm_round"] = fl.jump_from_floor.mean(); d["n_floor_firm_rounds"] = fl.size()
    mk = f.groupby(["trial_id", "round"]).price_index_fr.mean().reset_index()
    def first_reach(t, th):
        s = mk[(mk.trial_id == t) & (mk["round"] >= 2) & (mk.price_index_fr >= th)]
        return s["round"].min() if len(s) else np.nan
    for th in (0.25, 0.5):
        d[f"first_round_pi_ge_{th}"] = [first_reach(t, th) for t in d.index]
    d["peak_pi_after_r1"] = mk[mk["round"] >= 2].groupby("trial_id").price_index_fr.max()
    d["r2_mean_quote"] = f[f["round"] == 2].groupby("trial_id").q.mean()
    d["pi_rounds3plus"] = f[f["round"] >= 3].groupby("trial_id").price_index_fr.mean()
    d["arm"] = g.arm.reindex(d.index); d["pair"] = g.pair.reindex(d.index); d["model"] = m; gm.append(d.reset_index())
    for k in [c for c in d.columns if c not in ("arm", "pair", "model", "trial_id", "n_floor_firm_rounds") and not c.startswith("first_round")]:
        a = d[d.arm == ARM].set_index("pair")[k]; c = d[d.arm == CTL].set_index("pair")[k]
        ps = sorted(set(a.dropna().index) & set(c.dropna().index))
        if len(ps) < 5: continue
        mrows.append(summarize(a.loc[ps].values, c.loc[ps].values, k, dict(model=m, metric=k, window="rounds 2+", note="pairs with defined values on both sides")))
GM = pd.concat(gm, ignore_index=True); GM.to_csv(f"{OUT}/per_game_mechanism.csv", index=False)
pd.DataFrame(mrows).to_csv(f"{OUT}/mechanism_contrasts.csv", index=False)
crow = []
for m in SRC:
    d = GM[GM.model == m]
    for arm in (ARM, CTL):
        s = d[d.arm == arm]
        crow.append(dict(model=m, arm=arm, n_games=len(s), share_games_ever_pi_ge_0p25=s["first_round_pi_ge_0.25"].notna().mean(),
                         share_games_ever_pi_ge_0p5=s["first_round_pi_ge_0.5"].notna().mean(), median_first_round_pi_ge_0p5=s["first_round_pi_ge_0.5"].median(),
                         mean_peak_pi_after_r1=s.peak_pi_after_r1.mean(), mean_r2_quote=s.r2_mean_quote.mean(),
                         mean_escape_prob=s.escape_prob_per_floor_firm_round.mean(), share_games_pi_rounds3plus_lt_0p1=(s.pi_rounds3plus < 0.1).mean(),
                         share_firmrounds_le_1p05=s.share_firmrounds_le_1p05.mean(), matching_above_floor_mean=s["matching_among_above_floor_quotes"].mean()))
pd.DataFrame(crow).to_csv(f"{OUT}/climb_summary.csv", index=False)
# ---------- correlations (Spearman AND Pearson) ----------
def rank(x): return pd.Series(x).rank().values
def corr(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    return dict(n=len(x), pearson=np.corrcoef(x, y)[0, 1], spearman=np.corrcoef(rank(x), rank(y))[0, 1])
cr = []
for m in SRC:
    g = G[G.model == m]; a = g[g.arm == ARM].set_index("pair"); c = g[g.arm == CTL].set_index("pair"); ps = sorted(set(a.index) & set(c.index))
    dd = (a.loc[ps, ["price_index", "comp", "match"]] - c.loc[ps, ["price_index", "comp", "match"]])
    for k in ("comp", "match"):
        cr.append(dict(model=m, what=f"across pairs: change in price index vs change in {k}", **corr(dd.price_index, dd[k])))
    s = GM[(GM.model == m) & (GM.arm == ARM)]
    cr.append(dict(model=m, what="across 5-tick games: round-2 mean quote vs price index rounds 3+", **corr(s.r2_mean_quote, s.pi_rounds3plus)))
    cr.append(dict(model=m, what="across 5-tick games: matching-above-floor share vs price index rounds 3+", **corr(s["share_equal_above_floor_(matching)"], s.pi_rounds3plus)))
pd.DataFrame(cr).to_csv(f"{OUT}/correlations.csv", index=False)
# ---------- cross-model comparison ----------
cm = []
def pairdiff(m, k):
    g = G[G.model == m]; a = g[g.arm == ARM].set_index("pair")[k]; c = g[g.arm == CTL].set_index("pair")[k]; ps = sorted(set(a.index) & set(c.index)); return (a.loc[ps] - c.loc[ps]).values, c.loc[ps].values
for k in ("price_index", "pgi", "spread", "comp", "match"):
    do, co = pairdiff("gpt-oss-20b (reasoning medium)", k); dq, cq = pairdiff("Qwen3-32B thinking on", k)
    B = 10000; bo = rng.integers(0, 20, (B, 20)); bq = rng.integers(0, 20, (B, 20))
    eo = do[bo].mean(1); eq = dq[bq].mean(1)
    dif = eo - eq; rel_o = eo / co[bo].mean(1); rel_q = eq / cq[bq].mean(1)
    rd_ = rel_o - rel_q
    ok = k in ("price_index", "pgi", "spread"); rat = eo / eq
    cm.append(dict(metric=k, effect_oss=do.mean(), effect_qwen_on=dq.mean(), diff_oss_minus_qwen=dif.mean(), diff_ci_lo=np.percentile(dif, 2.5), diff_ci_hi=np.percentile(dif, 97.5),
                   ratio_oss_over_qwen=do.mean() / dq.mean(), ratio_ci_lo=np.percentile(rat, 2.5) if ok else np.nan, ratio_ci_hi=np.percentile(rat, 97.5) if ok else np.nan,
                   relative_effect_oss=do.mean() / co.mean(), relative_oss_ci_lo=np.percentile(rel_o, 2.5), relative_oss_ci_hi=np.percentile(rel_o, 97.5),
                   rel_diff_oss_minus_qwen=rd_.mean(), rel_diff_ci_lo=np.percentile(rd_, 2.5), rel_diff_ci_hi=np.percentile(rd_, 97.5), relative_effect_qwen=dq.mean() / cq.mean(), relative_qwen_ci_lo=np.percentile(rel_q, 2.5), relative_qwen_ci_hi=np.percentile(rel_q, 97.5)))
pd.DataFrame(cm).to_csv(f"{OUT}/cross_model.csv", index=False)
print("done")
