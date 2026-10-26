"""Dossier 07 review checks: duplicate round rows, same-round say-do rates, hard-case text minus early mean.
usage: python -X utf8 d07_review_checks.py HACKATHON_DIR OUTDIR. Created by Claude at the prompting of the repository owner."""
import sys, numpy as np, pandas as pd
HK, OUT = sys.argv[1], sys.argv[2]; RNG = np.random.default_rng(5)
res = []
for model, t in (("gpt-oss-20b", HK + "/work_scratch/oss_analysis/tables_t2"), ("Qwen3-32B", HK + "/work_scratch/analysis_final/tables_neutral_final")):
    R = pd.read_csv(t + "/rounds.csv", usecols=["trial_id", "round", "seat", "quote"])
    d = R[R.duplicated(["trial_id", "round", "seat"], keep=False)]
    print(model, "duplicate round rows:", len(d), sorted(d.trial_id.unique()))
    R = R.drop_duplicates(["trial_id", "round", "seat"])
    q = R.set_index(["trial_id", "round", "seat"]).quote
    F = pd.read_csv(OUT + "/say_do_firm_rounds.csv.gz"); F = F[(F.model == model) & (F.arm == "headline-chat")]
    riv = []
    for tid, r, s in zip(F.tid, F["round"], F.seat):
        o = [v for (ss, v) in q.loc[(tid, r)].items() if ss != s]; riv.append(min(o) if o else np.nan)
    F = F.assign(rival_now=riv, own=[q.loc[(a, b, c)] for a, b, c in zip(F.tid, F["round"], F.seat)])
    F["undercut_now"] = (F.own < F.rival_now - 0.005).astype(int)
    F["rival_matched_or_lower"] = (F.rival_now <= F.own + 0.005).astype(int)
    for md, g in F.groupby("mode"):
        for cond, gg in (("after agreement", g[g.agreed == 1]), ("no agreement", g[g.agreed == 0])):
            idx = [x.index.values for _, x in gg.groupby("pair")]; v = gg.undercut_now
            bs = [v.loc[np.concatenate([idx[j] for j in RNG.integers(0, len(idx), len(idx))])].mean() for _ in range(2000)]
            u = gg[gg.undercut == 1]
            res.append(dict(model=model, mode=md, condition=cond, firm_rounds=len(gg), undercut_vs_rival_same_round=v.mean(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5),
                            prevround_undercuts=len(u), share_prevround_undercuts_where_rival_same_or_lower_now=u.rival_matched_or_lower.mean() if len(u) else np.nan))
X = pd.DataFrame(res); X.to_csv(OUT + "/say_do_same_round.csv", index=False); print(X.round(3).to_string())
# hard cases: text minus early mean AUC below threshold
G = pd.read_csv(OUT + "/game_scores.csv"); thr = 0.49833333333333335
def auc(s, y):
    y = np.asarray(y) == 1; r = pd.Series(s).rank().values; n1 = y.sum(); n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan
hc = []
for p in ("O-A", "O-B0", "O-B"):
    g = G[(G["pop"] == p) & (G.early_mean < thr)].reset_index(drop=True); y = g.y.values; t = g["text: TF-IDF + LR"].values; e = g.early_mean.values
    idx = [x.index.values for _, x in g.groupby("pair")]; bs = []
    for _ in range(2000):
        ii = np.concatenate([idx[j] for j in RNG.integers(0, len(idx), len(idx))]); a = auc(t[ii], y[ii]) - auc(e[ii], y[ii])
        if not np.isnan(a): bs.append(a)
    hc.append(dict(pop=p, n=len(g), risers=int(y.sum()), text_auc=auc(t, y), early_mean_auc=auc(e, y), diff=auc(t, y) - auc(e, y), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
H = pd.DataFrame(hc); H.to_csv(OUT + "/hard_cases_text_minus_early.csv", index=False); print(H.round(3).to_string())
