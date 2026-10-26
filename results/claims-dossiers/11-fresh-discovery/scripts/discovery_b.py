"""Dossier 11, part B: (1) wording heterogeneity with a seed-regrouping null (no selection, and
selection-adjusted for picking the most extreme pair of wordings); (2) what the competitive
share (U16) counts in each model: one-to-five-tick undercuts at high prices vs real price cuts.
Usage: discovery_b.py <oss_run_csv> <qwen_run_csv> <rounds_dir> <out_dir>
"""
import sys, os, itertools
import numpy as np, pandas as pd

oss_run, q_run, rdir, out = sys.argv[1:5]
RNG = np.random.default_rng(7)
o = pd.read_csv(oss_run, low_memory=False); o = o[(o.in_primary == 1) & ~o.arm.str.startswith('hrep')].copy()
q = pd.read_csv(q_run, low_memory=False); q = q[q.in_primary == 1].copy()
for d in (o, q):
    d['pair'] = d.wording.astype(int).astype(str) + '_' + d.seed.astype(int).astype(str)
    d['cell'] = d.arm + '_p' + d.penalty_point.astype(int).astype(str)
pairs = sorted(o.pair.unique())
LEN = o.groupby('pair').planned_length.first()
strata = [sorted(LEN[LEN == L].index) for L in sorted(LEN.unique())]   # 4 horizons x 5 seeds
WPAIRS = list(itertools.combinations(range(5), 2))


def resid_matrix(d, met):
    dd = d.dropna(subset=[met]).copy()
    dd['res'] = dd[met] - dd.groupby('cell')[met].transform('mean')
    return dd.pivot_table(index='cell', columns='pair', values='res', aggfunc='mean').reindex(columns=pairs)


def group_stats(M, labels):
    """labels: array (len(pairs)) of group 0..4. Returns cell-averaged group means (5,)."""
    X = M.values; ok = ~np.isnan(X); X0 = np.where(ok, X, 0)
    gm = []
    for g in range(5):
        msk = labels == g
        s = X0[:, msk].sum(1); n = ok[:, msk].sum(1)
        gm.append(np.nanmean(np.where(n > 0, s / np.maximum(n, 1), np.nan)))
    return np.array(gm)


def stats(gm):
    het = np.sum((gm - gm.mean()) ** 2)
    pairfx = [abs(gm[a] + gm[b] - 2 * np.mean(np.delete(gm, [a, b]))) / 2 for a, b in WPAIRS]
    return het, max(pairfx)


obs_lab = np.array([int(p.split('_')[0]) for p in pairs])
rows = []
NMC = 20000
for nm, d in [('gpt-oss-20b', o), ('qwen3-32b thinking on', q[q.thinking == 'on']), ('qwen3-32b thinking off', q[q.thinking == 'off'])]:
    for met in ['market_price_mean', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share']:
        M = resid_matrix(d, met)
        gm = group_stats(M, obs_lab); het, mx = stats(gm)
        nh = np.empty(NMC); nmx = np.empty(NMC)
        for k in range(NMC):
            lab = np.empty(len(pairs), int)
            for st in strata:   # each pseudo-wording gets one seed of each horizon
                perm = RNG.permutation(5)
                for i, p in enumerate(st):
                    lab[pairs.index(p)] = perm[i]
            g2 = group_stats(M, lab); nh[k], nmx[k] = stats(g2)
        rows.append(dict(model=nm, outcome=met, wording_means=' '.join('%+.3f' % x for x in gm),
                         range=gm.max() - gm.min(), heterogeneity_ss=het, p_heterogeneity=float(np.mean(nh >= het - 1e-15)),
                         max_pair_effect=mx, p_max_pair_selection_adjusted=float(np.mean(nmx >= mx - 1e-15)), n_mc=NMC))
        print(rows[-1])
pd.DataFrame(rows).to_csv(os.path.join(out, 't3_wording_heterogeneity.csv'), index=False)

# ---------- (2) what the competitive share counts ----------
ro = pd.read_csv(os.path.join(rdir, 'rounds_oss.csv')); rq = pd.read_csv(os.path.join(rdir, 'rounds_qwen.csv'))


def firm_rounds(r, run):
    r = r[r.row_id.isin(run.row_id) & r.q3.isna() & r.other.isna()] if 'other' in r else r[r.row_id.isin(run.row_id) & r.q3.isna()]
    r = r.sort_values(['row_id', 'round'])
    out_ = []
    for me, rv in [('q1', 'q2'), ('q2', 'q1')]:
        x = r[['row_id', 'round', me, rv]].copy()
        x['rival_prev'] = x.groupby('row_id')[rv].shift()
        x['own'] = x[me]
        out_.append(x.dropna(subset=['rival_prev'])[['row_id', 'round', 'own', 'rival_prev']])
    f = pd.concat(out_)
    gap = (f.rival_prev - f.own).round(2)
    f['competitive'] = (gap >= 0.01) | ((f.own <= 1.0) & (f.rival_prev <= 1.0))
    f['micro_high'] = f.competitive & gap.between(0.01, 0.05) & (f.own >= 2.0)   # 1-5 tick undercut at a half-spread >= 2.00 (price index >= 0.5)
    f['near_floor'] = f.competitive & (f.own <= 1.10)
    return f.merge(run[['row_id', 'communication', 'arm']], on='row_id')


u = []
for nm, r, run in [('gpt-oss-20b', ro, o), ('qwen3-32b thinking on', rq, q[q.thinking == 'on']), ('qwen3-32b thinking off', rq, q[q.thinking == 'off'])]:
    f = firm_rounds(r, run)
    chk = f.groupby('row_id').competitive.mean().rename('mine').to_frame().join(run.set_index('row_id').competitive_share)
    for grp, g in [('all two-firm games', f), ('private chat', f[f.communication == 'private']), ('no chat (tacit)', f[f.communication == 'tacit'])]:
        c = g[g.competitive]
        u.append(dict(model=nm, games=grp, firm_rounds=len(g), competitive_share=g.competitive.mean(),
                      share_of_competitive_that_are_micro_undercuts_at_high_price=c.micro_high.mean(),
                      share_of_competitive_near_floor=c.near_floor.mean(),
                      competitive_share_excluding_micro_high=(g.competitive & ~g.micro_high).mean(),
                      check_pearson_with_run_csv=np.corrcoef(chk.dropna().mine, chk.dropna().competitive_share)[0, 1],
                      check_mean_abs_diff=(chk.mine - chk.competitive_share).abs().mean()))
U = pd.DataFrame(u); U.to_csv(os.path.join(out, 't1_competitive_share_decomposition.csv'), index=False)
pd.set_option('display.width', 250); print(U.round(3).to_string())
