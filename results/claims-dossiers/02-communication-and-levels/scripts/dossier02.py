"""Dossier 02: communication and baseline levels across models (independent re-derivation).

Inputs: the gpt-oss-20b game table and the Qwen3-32B neutral game table (run.csv, Step 1).
usage: python -X utf8 dossier02.py OSS_RUN_CSV QWEN_RUN_CSV OUTDIR
Unit: game. Within a model, contrasts are paired on (wording, seed); across models nothing is
paired, so cross-model differences use an unpaired game-level bootstrap (each model's 20 games
resampled independently) and an unpaired label-permutation p.
Created by Claude at the prompting of the repository owner.
"""
import os, sys, itertools
import numpy as np, pandas as pd
import warnings; warnings.filterwarnings("ignore")

def spear(a, b):
    """Spearman rho = Pearson correlation of average ranks (no scipy needed)."""
    return a.rank().corr(b.rank())


OSS, QW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
B = 10000
RNG = np.random.default_rng(20261025)
METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share"),
           ("matching_share", "Matching share")]
DECLARED = {"price_index", "profit_gain_index"}

o = pd.read_csv(OSS, low_memory=False)
o = o[(o.status == "done") & (o.in_primary == 1)]
o_all = o.copy()                                   # includes the build-bug replicate arms
o = o[o.arm_build_bug != 1]
o["model"] = "gpt-oss-20b"; o["mode"] = "medium"
q = pd.read_csv(QW, low_memory=False)
q = q[(q.run == "neutral") & (q.status == "done") & (q.in_primary == 1)].copy()
q["model"] = "Qwen3-32B"; q["mode"] = q.thinking.map({"on": "t1", "off": "t0"})
for d in (o, q, o_all):
    d["pair"] = d.wording.astype(int).astype(str) + "_" + d.seed.astype(int).astype(str)

SETS = {"gpt-oss-20b": o, "Qwen3-32B t1": q[q["mode"] == "t1"], "Qwen3-32B t0": q[q["mode"] == "t0"]}


def cell(d, arm, pt):
    s = d[(d.arm == arm) & (d.penalty_point == pt)]
    assert s.pair.is_unique, (arm, pt)
    return s.set_index("pair")


def boot_mean(x):
    x = np.asarray(x, float); i = RNG.integers(0, len(x), (B, len(x)))
    return np.percentile(x[i].mean(1), [2.5, 97.5])


def signflip(d):
    d = np.asarray(d, float); n = len(d)
    if n == 0 or np.allclose(d, 0): return 1.0
    obs = abs(d.mean())
    if n <= 20:
        tot = 0; cnt = 0
        signs_all = 1 - 2 * ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1).astype(np.int8)
        for k in range(0, 2 ** n, 1 << 16):
            s = np.abs((signs_all[k:k + (1 << 16)] * d).mean(1)); cnt += (s >= obs - 1e-12).sum(); tot += len(s)
        return cnt / tot
    s = np.abs((RNG.choice([-1, 1], (200000, n)) * d).mean(1)); return ((s >= obs - 1e-12).sum() + 1) / 200001


def holm(ps):
    ps = np.asarray(ps, float); m = len(ps); order = np.argsort(ps); adj = np.empty(m); run = 0
    for r, i in enumerate(order):
        run = max(run, (m - r) * ps[i]); adj[i] = min(1, run)
    return adj


def paired_row(model, d, a, b, label, metric):
    A = cell(d, *a)[metric]; Bc = cell(d, *b)[metric]
    k = A.dropna().index.intersection(Bc.dropna().index)
    diff = (A[k] - Bc[k]).values
    lo, hi = boot_mean(diff); se = diff.std(ddof=1) / np.sqrt(len(diff))
    return dict(model=model, contrast=label, metric=metric, n_pairs=len(diff), mean_a=A[k].mean(), mean_b=Bc[k].mean(),
                diff=diff.mean(), lo=lo, hi=hi, p_signflip=signflip(diff), se=se, mde=2.8 * se)


# ---------- 1. cell levels ----------
rows = []
for name, d in SETS.items():
    for (arm, pt), s in d[d.arm.isin(["headline-tacit", "headline-chat", "headline-monitored", "m-pub", "m-mon0"])].groupby(["arm", "penalty_point"]):
        r = dict(model=name, arm=arm, communication=s.communication.iloc[0], penalty_point=pt, n_games=len(s))
        for m, _ in METRICS:
            v = s[m].dropna(); lo, hi = boot_mean(v)
            r[m] = v.mean(); r[m + "_lo"] = lo; r[m + "_hi"] = hi
        rows.append(r)
cells = pd.DataFrame(rows)
cells.to_csv(f"{OUT}/cell_levels.csv", index=False)

# ---------- 2. chat minus tacit per point, monitored/public/unmonitored ----------
con = []
for name, d in SETS.items():
    pts = sorted(set(cell_pts := d[d.arm == "headline-tacit"].penalty_point) & set(d[d.arm == "headline-chat"].penalty_point))
    for pt in pts:
        for m, _ in METRICS:
            con.append(paired_row(name, d, ("headline-chat", pt), ("headline-tacit", pt), f"private chat minus no chat, p{pt}", m))
    if name != "gpt-oss-20b":
        for pt in pts:
            for m, _ in METRICS:
                con.append(paired_row(name, d, ("headline-monitored", pt), ("headline-chat", pt), f"monitored chat minus private chat, p{pt}", m))
                con.append(paired_row(name, d, ("headline-monitored", pt), ("headline-tacit", pt), f"monitored chat minus no chat, p{pt}", m))
        for arm, lab in (("m-pub", "public chat"), ("m-mon0", "chat said unmonitored")):
            for m, _ in METRICS:
                con.append(paired_row(name, d, (arm, 3), ("headline-chat", 3), f"{lab} minus private chat, p3", m))
                con.append(paired_row(name, d, (arm, 3), ("headline-tacit", 3), f"{lab} minus no chat, p3", m))
        # pooled over points 1,3,4,5 (average within pair), as in the frozen Qwen numbers
        for arm_a, arm_b, lab in (("headline-chat", "headline-tacit", "private chat minus no chat, pooled p1,p3,p4,p5"),
                                  ("headline-monitored", "headline-chat", "monitored chat minus private chat, pooled p1,p3,p4,p5")):
            for m, _ in METRICS:
                A = d[d.arm == arm_a].pivot_table(index="pair", columns="penalty_point", values=m)
                Bc = d[d.arm == arm_b].pivot_table(index="pair", columns="penalty_point", values=m)
                diff = (A - Bc.reindex(A.index))[[1, 3, 4, 5]].dropna().mean(1).values
                lo, hi = boot_mean(diff); se = diff.std(ddof=1) / np.sqrt(len(diff))
                con.append(dict(model=name, contrast=lab, metric=m, n_pairs=len(diff), mean_a=np.nan, mean_b=np.nan, diff=diff.mean(),
                                lo=lo, hi=hi, p_signflip=signflip(diff), se=se, mde=2.8 * se))
    else:
        # gpt-oss: pooled over its two tacit points
        for m, _ in METRICS:
            A = d[d.arm == "headline-chat"].pivot_table(index="pair", columns="penalty_point", values=m)
            Bc = d[d.arm == "headline-tacit"].pivot_table(index="pair", columns="penalty_point", values=m)
            diff = (A - Bc.reindex(A.index))[[1, 5]].dropna().mean(1).values
            lo, hi = boot_mean(diff); se = diff.std(ddof=1) / np.sqrt(len(diff))
            con.append(dict(model=name, contrast="private chat minus no chat, pooled p1,p5", metric=m, n_pairs=len(diff), mean_a=np.nan, mean_b=np.nan,
                            diff=diff.mean(), lo=lo, hi=hi, p_signflip=signflip(diff), se=se, mde=2.8 * se))
con = pd.DataFrame(con)
# Holm families (named), each within ONE model-mode (each model is its own replication):
# F1 = chat minus no chat per point, the two declared metrics (gpt-oss m=4, Qwen m=8 per mode)
# F2 = the same contrasts on the three exploratory metrics (gpt-oss m=6, Qwen m=12 per mode)
per_pt = con.contrast.str.match(r"private chat minus no chat, p\d$")
for mode in con.model.unique():
    for tag, dec, what in (("F1", True, "price and profit gain index"), ("F2", False, "spread, competitive and matching share")):
        sel = per_pt & (con.model == mode) & (con.metric.isin(DECLARED) == dec)
        con.loc[sel, "holm_family"] = f"{tag} chat-minus-tacit per point, {what}, {mode} (m={sel.sum()})"
        con.loc[sel, "p_holm"] = holm(con.loc[sel, "p_signflip"])
f3 = con.contrast.str.contains("monitored chat minus private|public chat minus private|unmonitored minus private")
for mode in ("Qwen3-32B t1", "Qwen3-32B t0"):
    sel = f3 & (con.model == mode)
    con.loc[sel, "holm_family"] = f"F3 who-reads-the-chat contrasts vs private chat, {mode}, all 5 metrics (m={sel.sum()})"
    con.loc[sel, "p_holm"] = holm(con.loc[sel, "p_signflip"])
f4 = con.contrast.str.contains("pooled")
con.loc[f4, "holm_family"] = "F4 pooled contrasts (all models, 5 metrics) (m=%d)" % f4.sum()
con.loc[f4, "p_holm"] = holm(con.loc[f4, "p_signflip"])
f5 = con.holm_family.isna()
con.loc[f5, "holm_family"] = "F5 chat-type minus no chat (Qwen, 5 metrics) (m=%d)" % f5.sum()
con.loc[f5, "p_holm"] = holm(con.loc[f5, "p_signflip"])
con.to_csv(f"{OUT}/contrasts_within_model.csv", index=False)

# ---------- 3. cross-model level differences (unpaired) ----------
def unpaired(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    bx = x[RNG.integers(0, len(x), (B, len(x)))].mean(1); by = y[RNG.integers(0, len(y), (B, len(y)))].mean(1)
    lo, hi = np.percentile(bx - by, [2.5, 97.5]); obs = x.mean() - y.mean()
    z = np.concatenate([x, y]); P = 20000
    zp = z[RNG.random((P, len(z))).argsort(1)]
    cnt = (np.abs(zp[:, :len(x)].mean(1) - zp[:, len(x):].mean(1)) >= abs(obs) - 1e-12).sum()
    se = np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))
    return obs, lo, hi, (cnt + 1) / (P + 1), se


xm = []
for qn in ("Qwen3-32B t1", "Qwen3-32B t0"):
    for arm, pt in (("headline-tacit", 1), ("headline-tacit", 5), ("headline-chat", 1), ("headline-chat", 3), ("headline-chat", 5)):
        for m, _ in METRICS:
            x = cell(o, arm, pt)[m].dropna(); y = cell(SETS[qn], arm, pt)[m].dropna()
            obs, lo, hi, p, se = unpaired(x, y)
            xm.append(dict(comparison=f"gpt-oss minus {qn}", arm=arm, penalty_point=pt, metric=m, n_oss=len(x), n_qwen=len(y),
                           oss=x.mean(), qwen=y.mean(), diff=obs, lo=lo, hi=hi, p_perm=p, mde=2.8 * se))
    # difference of chat effects (difference-in-differences across models): pairs resampled within each model independently
    for pt in (1, 5):
        for m, _ in METRICS:
            def pd_(d):
                A = cell(d, "headline-chat", pt)[m]; Bc = cell(d, "headline-tacit", pt)[m]; k = A.index.intersection(Bc.index)
                return (A[k] - Bc[k]).values
            x, y = pd_(o), pd_(SETS[qn]); obs, lo, hi, p, se = unpaired(x, y)
            xm.append(dict(comparison=f"chat effect: gpt-oss minus {qn}", arm="chat minus no chat", penalty_point=pt, metric=m,
                           n_oss=len(x), n_qwen=len(y), oss=x.mean(), qwen=y.mean(), diff=obs, lo=lo, hi=hi, p_perm=p, mde=2.8 * se))
xm = pd.DataFrame(xm)
for comp in xm.comparison.unique():
    for dec in (True, False):
        sel = (xm.comparison == comp) & (xm.metric.isin(DECLARED) == dec)
        xm.loc[sel, "holm_family"] = f"{comp}, {'price and profit gain index' if dec else 'spread, competitive and matching share'} (m={sel.sum()})"
        xm.loc[sel, "p_holm"] = holm(xm.loc[sel, "p_perm"])
xm.to_csv(f"{OUT}/cross_model_levels.csv", index=False)

# ---------- 4. A1 cell check (declared rule: rank cells by profit gain index) ----------
a1 = []
for name, d in SETS.items():
    h = d[d.arm.isin(["headline-tacit", "headline-chat", "headline-monitored"])]
    cm = h.groupby(["arm", "penalty_point"]).profit_gain_index.mean().sort_values(ascending=False)
    ranks = list(cm.index)
    chosen = ("headline-chat", 1); r = ranks.index(chosen) + 1
    comp = ranks[0] if r != 1 else ranks[1]
    row = paired_row(name, d, chosen, comp, f"chosen minus {comp[0]} p{comp[1]}", "profit_gain_index")
    lo_c, hi_c = boot_mean(cell(d, *chosen).profit_gain_index); lo_t, hi_t = boot_mean(cell(d, *comp).profit_gain_index)
    verdict = "PASS" if r == 1 else ("CLOSE" if (row["lo"] <= 0 <= row["hi"]) or abs(row["diff"]) < 0.05 else "FAIL")
    # rank by the other metrics too
    other = {}
    for m, _ in METRICS:
        s = h.groupby(["arm", "penalty_point"])[m].mean().sort_values(ascending=(m == "competitive_share"))
        other[m] = list(s.index).index(chosen) + 1
    a1.append(dict(model=name, n_cells=len(ranks), chosen_rank=r, chosen_pgi=cm[chosen], chosen_lo=lo_c, chosen_hi=hi_c,
                   comparison_cell=f"{comp[0]} p{comp[1]}", comparison_pgi=cm[comp], comp_lo=lo_t, comp_hi=hi_t,
                   diff=row["diff"], diff_lo=row["lo"], diff_hi=row["hi"], p_signflip=row["p_signflip"], verdict=verdict,
                   rank_spread=other["market_price_mean"], rank_price=other["price_index"], rank_comp=other["competitive_share"],
                   rank_match=other["matching_share"], ranking=" > ".join(f"{a.replace('headline-','')} p{p} {v:.3f}" for (a, p), v in cm.items())))
pd.DataFrame(a1).to_csv(f"{OUT}/a1_cell_check.csv", index=False)

# ---------- 5. empty talk (gpt-oss) ----------
ch = o[o.communication_group == "chat"].copy()
ch["any_empty"] = (ch.empty_talk_done_count.fillna(0) > 0).astype(int)
et = []
def corr_row(sub, lab, x="empty_talk_done_count"):
    for m, _ in METRICS:
        s = sub[[x, m, "rounds_played"]].dropna()
        et.append(dict(subset=lab, n_games=len(s), x=x, metric=m, spearman=spear(s[x], s[m]), pearson=s[x].corr(s[m]),
                       mean_none=sub.loc[sub.any_empty == 0, m].mean(), n_none=(sub.any_empty == 0).sum(),
                       mean_any=sub.loc[sub.any_empty == 1, m].mean(), n_any=(sub.any_empty == 1).sum(),
                       spearman_rounds_vs_empty=spear(s[x], s["rounds_played"]),
                       spearman_rounds_vs_metric=spear(s[m], s["rounds_played"])))
corr_row(ch, "all gpt-oss chat games (every arm)")
corr_row(ch[ch.arm == "headline-chat"], "headline private-chat games")
# partial Spearman controlling for rounds played (rank residuals)
for m, _ in METRICS:
    s = ch[["empty_talk_done_count", m, "rounds_played"]].dropna().rank()
    def res(a, b):
        bb = np.c_[np.ones(len(b)), b]; return a - bb @ np.linalg.lstsq(bb, a, rcond=None)[0]
    rx = res(s.empty_talk_done_count.values, s.rounds_played.values); ry = res(s[m].values, s.rounds_played.values)
    et.append(dict(subset="all chat games, partial Spearman given rounds played", n_games=len(s), x="empty_talk_done_count", metric=m,
                   spearman=np.corrcoef(rx, ry)[0, 1]))
# empty talk per round (rate) to remove the length mechanics
ch["empty_per_round"] = ch.empty_talk_done_count.fillna(0) / ch.rounds_played
corr_row(ch, "all chat games, empty turns per round", x="empty_per_round")
pd.DataFrame(et).to_csv(f"{OUT}/empty_talk_covariate.csv", index=False)

sens = []
def sens_rows(d, lab, drop):
    for pt in (1, 5):
        A = cell(d, "headline-chat", pt); Bc = cell(d, "headline-tacit", pt)
        keep = A.index[~drop(A)].intersection(Bc.index[~drop(Bc)])
        for m, _ in METRICS:
            diff = (A.loc[keep, m] - Bc.loc[keep, m]).dropna().values
            lo, hi = boot_mean(diff); se = diff.std(ddof=1) / np.sqrt(len(diff))
            sens.append(dict(subset=lab, penalty_point=pt, metric=m, n_pairs=len(diff), diff=diff.mean(), lo=lo, hi=hi, p_signflip=signflip(diff), mde=2.8 * se))
sens_rows(o, "all pairs", lambda s: pd.Series(False, index=s.index))
sens_rows(o, "drop pairs with any empty talk turn", lambda s: s.empty_talk_done_count.fillna(0) > 0)
sens_rows(o, "drop pairs with any truncated call", lambda s: s.truncations.fillna(0) > 0)
sens_rows(o, "drop pairs with empty talk or truncation", lambda s: (s.empty_talk_done_count.fillna(0) > 0) | (s.truncations.fillna(0) > 0))
pd.DataFrame(sens).to_csv(f"{OUT}/empty_talk_sensitivity.csv", index=False)

# Qwen analogue: silent 'done' turns (deliberate), descriptive only
qs = []
for qn in ("Qwen3-32B t1", "Qwen3-32B t0"):
    d = SETS[qn]; c = d[d.communication_group == "chat"]
    for m, _ in METRICS:
        s = c[["silent_turns", m]].dropna()
        qs.append(dict(model=qn, n_games=len(s), metric=m, spearman=spear(s.silent_turns, s[m]), pearson=s.silent_turns.corr(s[m]),
                       truncations_any=(c.truncations.fillna(0) > 0).sum()))
s = o[o.communication_group == "chat"][["silent_turns", "price_index", "profit_gain_index"]].dropna()
qs.append(dict(model="gpt-oss-20b", n_games=len(s), metric="price_index", spearman=spear(s.silent_turns, s.price_index), pearson=s.silent_turns.corr(s.price_index)))
pd.DataFrame(qs).to_csv(f"{OUT}/silent_turns_both_models.csv", index=False)

# replicates (same prompt, independent sampling) pooled sensitivity for the chat effect
rep = {"hrep-fx-chat-p1": ("headline-chat", 1), "hrep-nx-chat-p1": ("headline-chat", 1), "hrep-fx-chat-p5": ("headline-chat", 5),
       "hrep-fx-tacit-p1": ("headline-tacit", 1), "hrep-nx-tacit-p1": ("headline-tacit", 1)}
pool = o_all[o_all.arm.isin(list(rep) + ["headline-chat", "headline-tacit"])].copy()
pool["arm2"] = pool.arm.map(lambda a: rep.get(a, (a, None))[0]); pool["pt2"] = [rep.get(a, (a, p))[1] for a, p in zip(pool.arm, pool.penalty_point)]
pr = []
for pt in (1, 5):
    for m, _ in METRICS:
        A = pool[(pool.arm2 == "headline-chat") & (pool.pt2 == pt)].groupby("pair")[m].mean()
        Bc = pool[(pool.arm2 == "headline-tacit") & (pool.pt2 == pt)].groupby("pair")[m].mean()
        k = A.index.intersection(Bc.index); diff = (A[k] - Bc[k]).values; lo, hi = boot_mean(diff)
        repl = pool[(pool.arm.isin(rep)) & (pool.pt2 == pt)]
        pr.append(dict(penalty_point=pt, metric=m, n_pairs=len(diff), diff=diff.mean(), lo=lo, hi=hi, p_signflip=signflip(diff),
                       n_games_chat=int(((pool.arm2 == "headline-chat") & (pool.pt2 == pt)).sum()), n_games_tacit=int(((pool.arm2 == "headline-tacit") & (pool.pt2 == pt)).sum())))
pd.DataFrame(pr).to_csv(f"{OUT}/chat_effect_pooled_with_replicates.csv", index=False)
print("done")
