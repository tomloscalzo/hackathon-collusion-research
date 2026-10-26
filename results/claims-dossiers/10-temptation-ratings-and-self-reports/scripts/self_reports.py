"""H3/H4: the models' own 1-to-5 self-reports (temptation A/B, conflict, placebo) as signals.
 - H4: game-level and (arm, wording)-level Spearman and Pearson of the self-score with the five metrics, gpt-oss and Qwen
   (thinking on and off, neutral run); placebo as a negative control; cluster bootstrap over (wording, seed) pairs.
 - H4b: incremental value: does the early (rounds 1-3) score predict the later (rounds 4+) price index beyond the early
   price index? Partial Spearman, bootstrap over pairs.
 - H3: Claude-rated vs self-reported temptation / conflict at the prompt-text level ((arm, wording)), and the
   ethics-rule validation pair (d-conflict vs d-conflict-ethics).
Run: python -X utf8 self_reports.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(C.SEED + 1)
QWEN_ROUNDS = C.HK / "work_scratch/analysis_final/out_final/ref/neutral/tables_done/rounds.csv"

oss = C.prep(C.load_oss())
qn = C.prep(C.load_qwen("neutral"))
DATA = {"gpt-oss-20b (medium effort)": oss, "Qwen3-32B thinking on": qn[qn.thinking == "on"],
        "Qwen3-32B thinking off": qn[qn.thinking == "off"]}
SETS = {"temptation (A+B pooled)": ["d-temptation-a", "d-temptation-b"], "temptation A": ["d-temptation-a"],
        "temptation B": ["d-temptation-b"], "conflict (no rule)": ["d-conflict"],
        "conflict (ethics rule)": ["d-conflict-ethics"], "conflict (both arms)": ["d-conflict", "d-conflict-ethics"],
        "placebo (random number)": ["d-placebo"]}

rows, pts = [], []
for ds, d in DATA.items():
    for sname, arms in SETS.items():
        g = d[d.arm.isin(arms) & d.score_mean.notna()].copy()
        g["pair"] = g.wording.astype(str) + "_" + g.seed.astype(str)
        # game level
        for m in C.MCOLS:
            res = C.boot_corr(g.score_mean, g[m], g.pair, rng)
            rows.append(dict(dataset=ds, score=sname, level="game", metric=m, **res))
        # (arm, wording) level: mean over the 4 seeds
        a = g.groupby(["arm", "wording"])[C.MCOLS + ["score_mean"] + C.RCOLS].mean().reset_index()
        for m in C.MCOLS:
            res = C.boot_corr(a.score_mean, a[m], a.wording, rng)   # cluster = wording (A and B share it)
            ps, pp = C.perm_p(a.score_mean, a[m], rng)
            rows.append(dict(dataset=ds, score=sname, level="arm_wording", metric=m, perm_p_spearman=ps, perm_p_pearson=pp, **res))
        if sname in ("temptation (A+B pooled)", "conflict (both arms)", "placebo (random number)"):
            g2 = g.assign(dataset=ds, score=sname)
            pts.append(g2[["dataset", "score", "row_id", "arm", "wording", "seed", "score_mean"] + C.RCOLS + C.MCOLS])
S = pd.DataFrame(rows)
S["mde_spearman"] = 2.8 * S.sp_se
S.round(4).to_csv(OUT / "selfreport_correlations.csv", index=False, lineterminator="\n")
pd.concat(pts).round(4).to_csv(OUT / "points" / "selfreport_games.csv", index=False, lineterminator="\n")

# ---------- H3: Claude rating vs self-report at the prompt-text level
rows = []
for ds, d in DATA.items():
    for sname, arms, rc in [("temptation (A+B pooled)", ["d-temptation-a", "d-temptation-b"], "claude_temptation"),
                            ("conflict (both arms)", ["d-conflict", "d-conflict-ethics"], "claude_conflict"),
                            ("conflict (no rule)", ["d-conflict"], "claude_conflict")]:
        g = d[d.arm.isin(arms) & d.score_mean.notna()]
        a = g.groupby(["arm", "wording"])[["score_mean", rc]].mean().reset_index()
        res = C.boot_corr(a[rc], a.score_mean, a.wording, rng)
        ps, pp = C.perm_p(a[rc], a.score_mean, rng)
        rows.append(dict(dataset=ds, score=sname, claude_rating=rc, n_texts=len(a),
                         claude_min=a[rc].min(), claude_max=a[rc].max(), self_min=a.score_mean.min(), self_max=a.score_mean.max(),
                         claude_mean=a[rc].mean(), self_mean=a.score_mean.mean(), perm_p_spearman=ps, perm_p_pearson=pp, **res))
    # ethics validation: paired by (wording, seed)
    A = d[d.arm == "d-conflict-ethics"].set_index(["wording", "seed"])
    B = d[d.arm == "d-conflict"].set_index(["wording", "seed"])
    k = A.index.intersection(B.index)
    diff = (A.loc[k, "score_mean"] - B.loc[k, "score_mean"]).dropna().to_numpy()
    cdiff = (A.loc[k, "claude_conflict"] - B.loc[k, "claude_conflict"]).dropna().to_numpy()
    bs = np.array([rng.choice(diff, len(diff)).mean() for _ in range(C.NB)])
    signs = rng.choice([-1, 1], (C.NPERM, len(diff)))
    pperm = (1 + np.sum(np.abs((signs * diff).mean(1)) >= abs(diff.mean()) - 1e-12)) / (C.NPERM + 1)
    rows.append(dict(dataset=ds, score="ethics rule validation: self conflict score, rule minus no rule (paired)",
                     n_texts=len(diff), self_mean=diff.mean(), sp_lo=np.percentile(bs, 2.5), sp_hi=np.percentile(bs, 97.5),
                     claude_mean=cdiff.mean(), perm_p_spearman=pperm))
pd.DataFrame(rows).round(4).to_csv(OUT / "claude_vs_self.csv", index=False, lineterminator="\n")

# ---------- H4b: early score vs early price as predictors of the later price index
def early_later(d, rounds_path):
    r = pd.read_csv(rounds_path, usecols=["trial_id", "round", "seat", "market_price", "self_report", "self_report_name"],
                    low_memory=False)
    g = d[d.arm.isin(["d-temptation-a", "d-temptation-b"])].copy()
    key = g.played_trial_id.fillna(g.trial_id) if "played_trial_id" in g else g.trial_id
    g["tid"] = key
    r = r[r.trial_id.isin(set(g.tid))]
    r["pi"] = ((r.market_price - 1) / 2).clip(0, 1)
    r["sr"] = pd.to_numeric(r.self_report, errors="coerce").where(r.self_report_name == "temptation_score")
    out = []
    for tid, x in r.groupby("trial_id"):
        if x["round"].max() < 4:
            continue
        e, l = x[x["round"] <= 3], x[x["round"] >= 4]
        out.append(dict(tid=tid, early_score=e.sr.mean(), early_pi=e.groupby("round").pi.first().mean(),
                        later_pi=l.groupby("round").pi.first().mean()))
    o = pd.DataFrame(out).merge(g[["tid", "wording", "seed"]], on="tid")
    return o.dropna()


def partial_sp(df, x, y, z):
    rk = df[[x, y, z]].rank()
    r = rk.corr().to_numpy()
    rxy, rxz, ryz = r[0, 1], r[0, 2], r[1, 2]
    return (rxy - rxz * ryz) / np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))


rows = []
for ds, d, rp in [("gpt-oss-20b (medium effort)", oss, C.OSS_ROUNDS), ("Qwen3-32B thinking on", qn[qn.thinking == "on"], QWEN_ROUNDS),
                  ("Qwen3-32B thinking off", qn[qn.thinking == "off"], QWEN_ROUNDS)]:
    try:
        o = early_later(d, rp)
    except Exception as ex:  # noqa
        print("early/later failed", ds, ex); continue
    o["pair"] = o.wording.astype(str) + "_" + o.seed.astype(str)
    stats = {"score_vs_later": lambda q: q[["early_score", "later_pi"]].corr("spearman").iloc[0, 1],
             "early_price_vs_later": lambda q: q[["early_pi", "later_pi"]].corr("spearman").iloc[0, 1],
             "score_vs_later_given_early_price": lambda q: partial_sp(q, "early_score", "later_pi", "early_pi"),
             "score_vs_early_price": lambda q: q[["early_score", "early_pi"]].corr("spearman").iloc[0, 1]}
    pairs = o.pair.unique()
    grp = {p: x for p, x in o.groupby('pair')}
    for nm, f in stats.items():
        v0 = f(o)
        bs = []
        for _ in range(C.NB):
            pick = rng.choice(pairs, len(pairs))
            q = pd.concat([grp[p] for p in pick])
            try:
                v = f(q)
                if np.isfinite(v): bs.append(v)
            except Exception:
                pass
        rows.append(dict(dataset=ds, statistic=nm, n_games=len(o), n_pairs=len(pairs), spearman=v0,
                         lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
pd.DataFrame(rows).round(4).to_csv(OUT / "selfreport_early_prediction.csv", index=False, lineterminator="\n")
print(pd.DataFrame(rows).round(3).to_string())
print(S[(S.level == "game") & S.score.isin(["temptation (A+B pooled)", "placebo (random number)", "conflict (both arms)"])]
      [["dataset", "score", "metric", "n", "spearman", "sp_lo", "sp_hi", "pearson", "pe_lo", "pe_hi"]].round(2).to_string())
