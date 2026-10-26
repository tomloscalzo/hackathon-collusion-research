import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HEADQ = ['headline-chat', 'headline-tacit', 'headline-monitored']
def kw_eps2(vals, labs):
    lv = np.unique(labs); n = len(vals)
    r = pd.Series(vals).rank().values; H = 0
    for l in lv:
        k = labs == l; H += r[k].sum() ** 2 / k.sum()
    Hs = 12 / (n * (n + 1)) * H - 3 * (n + 1)
    return max(0, Hs / ((n * n - 1) / (n + 1)))   # definition used by the Step 2 screen (no tie correction)
def perm_pairs(vals, pairs, wording_of_pair, B=9999, seed=11):
    """permute the wording label over the 20 (wording, seed) pairs (keeps the games of a pair together)."""
    rng = np.random.default_rng(seed); up = np.array(sorted(wording_of_pair)); w0 = np.array([wording_of_pair[p] for p in up])
    idx = {p: i for i, p in enumerate(up)}; pi = np.array([idx[p] for p in pairs])
    obs = kw_eps2(vals, w0[pi]); cnt = 0
    for _ in range(B):
        w = rng.permutation(w0); cnt += kw_eps2(vals, w[pi]) >= obs - 1e-12
    return obs, (cnt + 1) / (B + 1)
rows = []
for model, which, think in [('Qwen3-32B thinking off', 'qwen', 't0'), ('Qwen3-32B thinking on', 'qwen', 't1'), ('gpt-oss-20b (reasoning medium)', 'oss', 't1')]:
    d = load(which); d = d[d.think == think]
    if which == 'qwen': D = d[d.arm.isin(HEADQ)].copy()
    else: D = d[((d.arm == 'headline-chat') | (d.arm == 'headline-tacit'))].copy()
    D['cell'] = D.arm + '_p' + D.penalty_point.astype(str)
    wop = D.groupby('pair').wording.first().astype(int).to_dict()
    for m in MCOLS:
        # A: pooled game-level, as in the Step 2 screen
        v = D[m].values.astype(float); ok = ~np.isnan(v)
        e_pool, p_pool = perm_pairs(v[ok], D.pair.values[ok], wop)
        gm = D.assign(v=v).groupby('wording').v.mean(); mm_pool = gm.max() - gm.min()
        # B: cell-adjusted, pair-level means (20 units: 5 wordings x 4 seeds)
        D['adj'] = D[m] - D.groupby('cell')[m].transform('mean')
        pm = D.groupby('pair').adj.mean(); wl = np.array([wop[p] for p in pm.index])
        e_pair, p_pair = perm_pairs(pm.values, pm.index.values, wop, seed=13)
        def Fst(x, l):
            g = [x[l == w] for w in np.unique(l)]; n = len(x); k = len(g); gm_ = x.mean()
            return (sum(len(a) * (a.mean() - gm_) ** 2 for a in g) / (k - 1)) / (sum(((a - a.mean()) ** 2).sum() for a in g) / (n - k))
        F = Fst(pm.values, wl); rngf = np.random.default_rng(17); cf = 0
        for _ in range(9999): cf += Fst(pm.values, rngf.permutation(wl)) >= F - 1e-12
        pF = (cf + 1) / 10000
        # eta^2 of wording on the pair means (parametric), bootstrap of seeds within wording
        gmean = pm.mean(); ssb = sum(((pm.values[wl == w].mean() - gmean) ** 2) * (wl == w).sum() for w in np.unique(wl)); sst = ((pm.values - gmean) ** 2).sum()
        rng = np.random.default_rng(5); bs = []
        for _ in range(2000):
            xs = []; ls = []
            for w in np.unique(wl):
                x = pm.values[wl == w]; xs.append(x[rng.integers(0, len(x), len(x))]); ls.append(np.full(len(x), w))
            xv = np.concatenate(xs); lv = np.concatenate(ls); bs.append(kw_eps2(xv, lv))
        wm = pd.Series(pm.values).groupby(wl).mean()
        rows.append(dict(model=model, metric=MNAME[m], n_games=int(ok.sum()), n_pairs=len(pm), eps2_pooled=e_pool, root_eps2_pooled=np.sqrt(e_pool), p_pooled_pairperm=p_pool, wording_max_minus_min_pooled=mm_pool,
                         eps2_pair_cell_adj=e_pair, p_pair_cell_adj=p_pair, eps2_pair_ci_lo=np.percentile(bs, 2.5), eps2_pair_ci_hi=np.percentile(bs, 97.5), eta2_pair=ssb / sst, F_pair=F, p_F_pair=pF,
                         wording_max_minus_min_pair=wm.max() - wm.min()))
R = pd.DataFrame(rows)
R['p_holm_pooled_5metrics'] = np.nan; R['p_holm_pair_5metrics'] = np.nan
for mo in R.model.unique():
    k = R.model == mo
    R.loc[k, 'p_holm_pooled_5metrics'] = holm(R.loc[k, 'p_pooled_pairperm'].values); R.loc[k, 'p_holm_pair_5metrics'] = holm(R.loc[k, 'p_pair_cell_adj'].values)
R.to_csv(OUT + '/q14_wording_effect.csv', index=False, float_format='%.5g')
pd.set_option('display.width', 300)
print(R.drop(columns=['eps2_pair_ci_lo', 'eps2_pair_ci_hi']).round(4).to_string())
# per-wording means for the story (profit gain index, pair-level, cell-adjusted)
out = []
for model, which, think in [('Qwen3-32B thinking off', 'qwen', 't0'), ('Qwen3-32B thinking on', 'qwen', 't1'), ('gpt-oss-20b (reasoning medium)', 'oss', 't1')]:
    d = load(which); d = d[d.think == think]; D = d[d.arm.isin(HEADQ)] if which == 'qwen' else d[d.arm.isin(['headline-chat', 'headline-tacit'])]
    for m in ['profit_gain_index', 'price_index']:
        g = D.groupby('wording')[m].agg(['mean', 'count']).reset_index(); g['model'] = model; g['metric'] = MNAME[m]; out.append(g)
pd.concat(out).to_csv(OUT + '/q14_wording_means.csv', index=False, float_format='%.4f'); print(pd.concat(out).round(3).to_string())
