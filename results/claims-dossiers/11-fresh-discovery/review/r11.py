"""Independent re-check of dossier 11 (reviewer). Usage: python r11.py"""
import os, itertools
import numpy as np, pandas as pd
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
pd.set_option('display.width', 250)
R = np.random.default_rng(11)
OS = os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/')
QS = os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/analysis_final/steps/neutral/step1/')
o = pd.read_csv(OS + 'step1/final_t2/run.csv', low_memory=False); o = o[o.in_primary == 1].copy()
q = pd.read_csv(QS + 'run.csv', low_memory=False); q = q[q.in_primary == 1].copy()
uc = ['trial_id', 'round', 'seat', 'quote', 'market_price']
ro = pd.read_csv(OS + 'tables_t2/rounds.csv', usecols=uc)
rq = pd.read_csv(QS + 'tables/rounds.csv', usecols=uc)

# ---- data trap: tables_t2 fx/nx ids vs run.csv ----
mp = ro.groupby(['trial_id', 'round']).market_price.first().groupby('trial_id').mean()
for lab, sub in [('neutral root', o[o.source_root == '2026-10-26_trackm_oss_neutral']),
                 ('fx/nx rows', o[o.arm.str.startswith(('fx', 'nx'))])]:
    x = sub.set_index('trial_id').market_price_mean.to_frame().join(mp.rename('t2'))
    print('TRAP', lab, 'n', len(x), 'found', x.t2.notna().sum(), 'mean|diff|', (x.market_price_mean - x.t2).abs().mean().round(4),
          'share diff>0.01', ((x.market_price_mean - x.t2).abs() > 0.01).mean().round(3))

o = o[~o.arm.str.startswith(('hrep', 'fx', 'nx'))]
q1 = q[q.thinking == 'on']


def dyn(r, run):
    r = r[r.trial_id.isin(run.trial_id)]
    m = r.groupby(['trial_id', 'round']).market_price.first().reset_index().sort_values(['trial_id', 'round'])
    m['d'] = m.groupby('trial_id').market_price.diff().round(2)
    m['prev'] = m.groupby('trial_id').market_price.shift()
    s = m.dropna(subset=['d'])
    g = s.groupby('trial_id')
    out = pd.DataFrame({'ero': g.d.apply(lambda d: d.between(-0.05, -0.01).mean()), 'move': g.d.apply(lambda d: (d != 0).mean())})
    out['r1'] = m[m['round'] == 1].set_index('trial_id').market_price
    out['rest'] = m[m['round'] >= 2].groupby('trial_id').market_price.mean()
    return out, s


do, so = dyn(ro, o); dq, sq = dyn(rq, q1)
oc = o[o.communication == 'private']; qc = q1[q1.communication == 'private']
arms = sorted((set(oc.arm) & set(qc.arm)) - {'ctl-32b-compete'})
A = oc[oc.arm.isin(arms)][['trial_id', 'arm', 'wording', 'seed', 'penalty_point']].join(do, on='trial_id')
B = qc[qc.arm.isin(arms)][['trial_id']].assign(tid=lambda x: x.trial_id).join(dq, on='trial_id')
B['trial_id'] = B.trial_id.str.replace('__t1$', '__t1', regex=True)
M = A.merge(B, on='trial_id', suffixes=('_o', '_q'))
M['pair'] = M.wording.astype(str) + '_' + M.seed.astype(str)
print('\nD11-1 matched games', len(M), 'arms', M.arm.nunique(), 'pairs', M.pair.nunique())


def pairstat(v):
    v = v.values; bs = v[R.integers(0, len(v), (10000, len(v)))].mean(1)
    sf = (R.choice([-1, 1], (100000, len(v))) * v).mean(1)
    return round(v.mean(), 4), np.percentile(bs, [2.5, 97.5]).round(4), (np.abs(sf) >= abs(v.mean())).mean()


for k in ['ero', 'move', 'r1', 'rest']:
    print(k, 'oss', M[k + '_o'].mean().round(3), 'qwen', M[k + '_q'].mean().round(3), pairstat((M[k + '_o'] - M[k + '_q']).groupby(M.pair).mean()))
pa = M.groupby('arm')[['ero_o', 'ero_q']].mean(); print('arms oss>qwen', (pa.ero_o > pa.ero_q).sum(), '/', len(pa))
spearmanr=lambda a,b:(np.corrcoef(pd.Series(a).rank(),pd.Series(b).rank())[0,1],)
pearsonr=lambda a,b:(np.corrcoef(a,b)[0,1],)
for nm, d in [('oss', M[['arm', 'penalty_point', 'r1_o', 'rest_o']].set_axis(['arm', 'pp', 'r1', 'rest'], axis=1)),
              ('qwen', M[['arm', 'penalty_point', 'r1_q', 'rest_q']].set_axis(['arm', 'pp', 'r1', 'rest'], axis=1))]:
    d = d.dropna().copy(); c = d.arm + d.pp.astype(str)
    for col in ['r1', 'rest']: d[col] = d[col] - d.groupby(c)[col].transform('mean')
    print('lock-in matched chat', nm, 'spearman', round(spearmanr(d.r1, d.rest)[0], 3), 'pearson', round(pearsonr(d.r1, d.rest)[0], 3))

# ---- is erosion a level / noise artefact? condition on previous best-quote band ----
print('\nErosion conditional on previous best quote band (matched chat games, rounds 2+)')
for nm, s, ids in [('oss', so, M.trial_id), ('qwen', sq, M.trial_id)]:
    s = s[s.trial_id.isin(ids)].copy()
    s['band'] = pd.cut(s.prev, [0.99, 1.05, 1.5, 2.0, 2.5, 3.0, 5.0])
    t = s.groupby('band', observed=True).d.agg(ero=lambda d: d.between(-0.05, -0.01).mean(), move=lambda d: (d != 0).mean(), n='size')
    print(nm); print(t.round(3).to_string())
# tick granularity of quotes: share of quotes on the 0.05 grid
for nm, r, run in [('oss', ro, o), ('qwen on', rq, q1)]:
    x = r[r.trial_id.isin(run.trial_id) & r.quote.notna()].quote
    print(nm, 'quotes on 0.05 grid', ((x * 100).round() % 5 == 0).mean().round(3), 'on 0.10 grid', ((x * 100).round() % 10 == 0).mean().round(3))

# ---- D11-2 threshold sensitivity ----
print('\nD11-2 sensitivity: share of competitive firm-rounds that are small undercuts at high price (private chat, 2-firm)')


def firm(r, run):
    r = r[r.trial_id.isin(run.trial_id) & r.seat.isin(['llm1', 'llm2'])]
    n = r.groupby('trial_id').seat.nunique(); three = r[~r.seat.isin(['llm1', 'llm2'])]
    w = r.pivot_table(index=['trial_id', 'round'], columns='seat', values='quote').reset_index().sort_values(['trial_id', 'round'])
    out = []
    for me, rv in [('llm1', 'llm2'), ('llm2', 'llm1')]:
        x = pd.DataFrame({'trial_id': w.trial_id, 'own': w[me], 'rp': w.groupby('trial_id')[rv].shift()})
        out.append(x.dropna())
    f = pd.concat(out); f['gap'] = (f.rp - f.own).round(2)
    f['comp'] = (f.gap >= 0.01) | ((f.own <= 1.0) & (f.rp <= 1.0))
    return f


ok2o = o[(o.communication == 'private') & (o.seats == 2) if 'seats' in o else (o.communication == 'private')]
two_o = o[(o.communication == 'private') & (o.firms == 2)]; two_q = q1[(q1.communication == 'private') & (q1.firms == 2)]
fo, fq = firm(ro, two_o), firm(rq, two_q)
print('comp share oss', fo.comp.mean().round(3), 'qwen', fq.comp.mean().round(3))
for tk in [1, 2, 3, 5, 10]:
    for lv in [1.5, 2.0, 2.5]:
        row = []
        for f in (fo, fq):
            mh = f.comp & f.gap.between(0.01, tk / 100 + 1e-9) & (f.own >= lv)
            row += [round(mh[f.comp].mean(), 3), round((f.comp & ~mh).mean(), 3)]
        print(f'ticks<= {tk:2d} price>={lv}: oss frac {row[0]} resid {row[1]} | qwen frac {row[2]} resid {row[3]} | gap after {row[1]-row[3]:.3f}')

# ---- D11-3 wording: nested F test on pair means and stratified permutation; headline-only ----
print('\nD11-3 wording')
for nm, d in [('oss', o), ('qwen on', q1)]:
    for lab, dd in [('all cells', d), ('headline only', d[d.arm.isin(['headline-chat', 'headline-tacit'])])]:
        dd = dd.dropna(subset=['price_index']).copy(); c = dd.arm + dd.penalty_point.astype(str)
        dd['res'] = dd.price_index - dd.groupby(c).price_index.transform('mean')
        pm = dd.groupby(['wording', 'seed']).res.mean().reset_index()
        pm['h'] = pm.seed.map(o.groupby('seed').planned_length.first())
        wm = pm.groupby('wording').res.mean(); obs = wm.var()
        # stratified: within horizon, permute wording labels across the 5 seeds
        null = []
        for _ in range(10000):
            lab2 = pm.groupby('h').wording.transform(lambda s: R.permutation(s.values))
            null.append(pm.res.groupby(lab2.values).mean().var())
        # nested F (wording vs seed-within-wording), horizon-adjusted residuals
        pm['r2'] = pm.res - pm.groupby('h').res.transform('mean')
        ssw = ((pm.r2 - pm.groupby('wording').r2.transform('mean')) ** 2).sum(); ssb = 4 * ((pm.groupby('wording').r2.mean() - pm.r2.mean()) ** 2).sum()
        F = (ssb / 4) / (ssw / 12)
        print(nm, lab, 'n games', len(dd), 'wording means', wm.round(3).tolist(), 'range', round(wm.max() - wm.min(), 3),
              'perm p', np.mean(np.array(null) >= obs - 1e-15), 'nested F(4,12)', round(F, 2), )
