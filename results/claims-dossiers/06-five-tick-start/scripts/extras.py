"""Dossier 06 extras: climb slopes after the cap, and early-vs-late effect on the SAME pairs (fixes the changing-sample problem)."""
import sys; sys.path.insert(0, ".")
from common import *
OUT = ".."
rng = np.random.default_rng(7)
out = []; same = []
for m in SRC:
    r, rd = load(m); f = firm_rounds(rd)
    r["pair"] = r.wording.astype(int).astype(str) + "_" + r.seed.astype(int).astype(str)
    tid = r.set_index("trial_id")
    mk = f.groupby(["trial_id", "round"]).price_index_fr.mean().reset_index()
    # per-game OLS slope of market price index on round, rounds 2-8 (needs >= 5 rounds)
    sl = {}
    for t, s in mk[(mk["round"] >= 2) & (mk["round"] <= 8)].groupby("trial_id"):
        if len(s) >= 5: sl[t] = np.polyfit(s["round"], s.price_index_fr, 1)[0]
    sl = pd.Series(sl)
    for arm in (ARM, CTL):
        v = sl[[t for t in sl.index if tid.arm[t] == arm]].values
        bs = rng.choice(v, (10000, len(v))).mean(1)
        out.append(dict(model=m, arm=arm, n_games=len(v), mean_slope_price_index_per_round_r2_to_r8=v.mean(), ci_lo=np.percentile(bs, 2.5), ci_hi=np.percentile(bs, 97.5),
                        share_games_slope_positive=(v > 0.005).mean()))
    # same-pairs early vs late
    def wm(lo, hi):
        x = mk[(mk["round"] >= lo) & (mk["round"] <= hi)].groupby("trial_id").price_index_fr.mean(); return x
    e, l = wm(2, 5), wm(11, 99)
    pairs = {}
    for t in l.index:
        pairs.setdefault(tid.pair[t], {})[tid.arm[t]] = t
    ps = [p for p, d in pairs.items() if ARM in d and CTL in d]
    de = np.array([e[pairs[p][ARM]] - e[pairs[p][CTL]] for p in ps]); dl = np.array([l[pairs[p][ARM]] - l[pairs[p][CTL]] for p in ps])
    dd = dl - de; B = rng.integers(0, len(ps), (10000, len(ps)))
    same.append(dict(model=m, n_pairs_reaching_round11=len(ps), early_effect_same_pairs=de.mean(), late_effect_same_pairs=dl.mean(), late_minus_early=dd.mean(),
                     lme_ci_lo=np.percentile(dd[B].mean(1), 2.5), lme_ci_hi=np.percentile(dd[B].mean(1), 97.5),
                     late_ci_lo=np.percentile(dl[B].mean(1), 2.5), late_ci_hi=np.percentile(dl[B].mean(1), 97.5), share_of_early_effect_remaining=dl.mean() / de.mean()))
pd.DataFrame(out).to_csv(f"{OUT}/climb_slopes.csv", index=False)
pd.DataFrame(same).to_csv(f"{OUT}/early_vs_late_same_pairs.csv", index=False)
print(pd.DataFrame(out).round(4).to_string()); print(pd.DataFrame(same).round(3).T.to_string())
