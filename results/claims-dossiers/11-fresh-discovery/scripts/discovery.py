"""Dossier 11: fresh discovery on the gpt-oss-20b data (exploratory, post hoc).

Independent of the Step 2 pipeline. Inputs: the two game tables (run.csv) and the round
tables written by build_rounds.py. Every test below is one member of the family
"discovery candidates" (Holm over all of them, including the rejected ones).
Usage: discovery.py <oss_run_csv> <qwen_run_csv> <rounds_dir> <out_dir>
"""
import sys, os, itertools
import numpy as np, pandas as pd

oss_run, q_run, rdir, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
RNG = np.random.default_rng(20261025)
B = 10000
MET = [('market_price_mean', 'Average absolute spread (1.00 to 5.00)'),
       ('price_index', 'Price index'), ('profit_gain_index', 'Profit gain index'),
       ('competitive_share', 'Competitive share (U16)'), ('matching_share', 'Matching share')]

o = pd.read_csv(oss_run, low_memory=False); o = o[o.in_primary == 1].copy()
q = pd.read_csv(q_run, low_memory=False); q = q[q.in_primary == 1].copy()
for d in (o, q):
    d['pair'] = d.wording.astype(int).astype(str) + '_' + d.seed.astype(int).astype(str)
    d['cell'] = d.arm + '_p' + d.penalty_point.astype(int).astype(str)


# ---------- per-game round dynamics (own definitions) ----------
def per_game(r):
    r = r.sort_values(['row_id', 'round']).copy()
    r['d'] = r.groupby('row_id').market_price.diff().round(2)
    r['tie'] = (r.q1 - r.q2).abs() < 0.005
    r['tie_prev'] = r.groupby('row_id').tie.shift().fillna(False).astype(bool)
    s = r.dropna(subset=['d']).copy()
    s['er'] = s.d.between(-0.05, -0.01)          # best quote falls by 1 to 5 ticks
    s['st'] = s.d == 0
    s['ri'] = s.d > 0
    s['dr'] = s.d < -0.05                        # falls by more than 5 ticks
    s['lk'] = s.er & s.tie & s.tie_prev          # both firms tied, both step down together
    g = s.groupby('row_id')
    res = pd.DataFrame({'scored_rounds': g.size(), 'erosion_share': g.er.mean(), 'stable_share': g.st.mean(),
                        'rise_share': g.ri.mean(), 'drop_share': g.dr.mean(), 'lockstep_share': g.lk.mean()})
    r1 = r[r['round'] == 1].set_index('row_id').market_price.rename('r1_price')
    rest = r[r['round'] >= 2].groupby('row_id').market_price.mean().rename('rest_price')
    return res.join(r1, how='outer').join(rest, how='outer').reset_index()


ro = pd.read_csv(os.path.join(rdir, 'rounds_oss.csv'))
rq = pd.read_csv(os.path.join(rdir, 'rounds_qwen.csv'))
o = o.merge(per_game(ro), on='row_id', how='left')
q = q.merge(per_game(rq), on='row_id', how='left')
q1 = q[q.thinking == 'on'].copy()
q0 = q[q.thinking == 'off'].copy()
oN = o[~o.arm.str.startswith('hrep')].copy()   # build-bug replicates left out of discovery tests


# ---------- helpers ----------
def boot_ci(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    idx = RNG.integers(0, len(v), (B, len(v)))
    m = v[idx].mean(1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5), v.std(ddof=1) / np.sqrt(len(v))


def signflip_p(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    n = len(v); obs = abs(v.mean())
    if n <= 16:
        signs = np.array(list(itertools.product([1, -1], repeat=n)))
    else:
        signs = RNG.choice([1, -1], (100000, n))
    null = np.abs((signs * v).mean(1))
    return float(np.mean(null >= obs - 1e-12))


def summarise(test, outcome, v, unit):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    lo, hi, se = boot_ci(v)
    return dict(test=test, outcome=outcome, unit=unit, n=len(v), est=v.mean(), ci_lo=lo, ci_hi=hi,
                p_perm=signflip_p(v), mde=2.8 * se)


def corr(a, b):
    a = pd.Series(np.asarray(a, float)); b = pd.Series(np.asarray(b, float)); m = a.notna() & b.notna()
    a, b = a[m], b[m]
    return np.corrcoef(a.rank(), b.rank())[0, 1], np.corrcoef(a, b)[0, 1], int(m.sum())


rows = []        # all contrasts (primary + secondary)
primary = {}     # test -> p for the Holm family

# ===== T1: gpt-oss vs Qwen (thinking on) erosion in matched chat games =====
EXCL = {'ctl-32b-compete'}  # forced to 1.00 in both models
chat_arms = sorted((set(oN[(oN.communication == 'private') & ~oN.arm.str.startswith(('fx', 'nx'))].arm)
                    & set(q1[q1.communication == 'private'].arm)) - EXCL)
DYN = ['erosion_share', 'stable_share', 'lockstep_share', 'drop_share', 'rise_share', 'r1_price', 'rest_price']
cols = ['trial_id', 'pair', 'arm', 'cell'] + DYN + [m for m, _ in MET]
m1 = oN[oN.arm.isin(chat_arms)][cols].merge(q1[cols], on=['trial_id', 'pair', 'arm', 'cell'], suffixes=('_o', '_q'))
m1.to_csv(os.path.join(out, 't1_matched_chat_games.csv'), index=False)
for met in DYN + [m for m, _ in MET]:
    v = (m1[met + '_o'] - m1[met + '_q']).groupby(m1.pair).mean()
    rows.append(summarise('T1 gpt-oss minus Qwen (thinking on), matched private-chat games', met, v.values,
                          '(wording, seed) pairs; %d matched games in %d arms' % (len(m1), m1.arm.nunique())))
    if met == 'erosion_share':
        primary['T1 erosion: gpt-oss minus Qwen (on), chat games'] = rows[-1]['p_perm']
lv = [dict(model='gpt-oss-20b', games=len(m1), **{k: m1[k + '_o'].mean() for k in DYN}),
      dict(model='qwen3-32b thinking on', games=len(m1), **{k: m1[k + '_q'].mean() for k in DYN})]
q0k = q0.copy(); q0k['trial_id'] = q0k.trial_id.str.replace('__t0', '__t1')
m10 = oN[oN.arm.isin(chat_arms)][cols].merge(q0k[cols], on=['trial_id', 'pair', 'arm', 'cell'], suffixes=('_o', '_q'))
v = (m10.erosion_share_o - m10.erosion_share_q).groupby(m10.pair).mean()
rows.append(summarise('T1b gpt-oss minus Qwen (thinking off), matched private-chat games', 'erosion_share', v.values,
                      '(wording, seed) pairs; %d matched games' % len(m10)))
lv.append(dict(model='qwen3-32b thinking off', games=len(m10), **{k: m10[k + '_q'].mean() for k in DYN}))
pd.DataFrame(lv).to_csv(os.path.join(out, 't1_erosion_levels.csv'), index=False)
# per-arm erosion, both models (descriptive)
pa = m1.groupby('arm')[['erosion_share_o', 'erosion_share_q', 'price_index_o', 'price_index_q']].mean()
pa['games'] = m1.groupby('arm').size(); pa.to_csv(os.path.join(out, 't1_erosion_by_arm.csv'))

cor_rows = []
for nm, d in [('gpt-oss-20b', oN), ('qwen3-32b thinking on', q1), ('qwen3-32b thinking off', q0)]:
    d = d.dropna(subset=['erosion_share']).copy()
    for c in ['erosion_share', 'price_index', 'r1_price', 'rest_price']:
        d[c + '_res'] = d[c] - d.groupby('cell')[c].transform('mean')
    s, p, n = corr(d.erosion_share_res, d.price_index_res)
    cor_rows.append(dict(model=nm, x='erosion share (within cell)', y='price index (within cell)', spearman=s, pearson=p, n=n))
    s, p, n = corr(d.r1_price_res, d.rest_price_res)
    cor_rows.append(dict(model=nm, x='round-1 best quote (within cell)', y='mean best quote, rounds 2+ (within cell)', spearman=s, pearson=p, n=n))
    a = d.groupby('arm')[['erosion_share', 'price_index']].mean()
    s, p, n = corr(a.erosion_share, a.price_index)
    cor_rows.append(dict(model=nm, x='erosion share (arm mean)', y='price index (arm mean)', spearman=s, pearson=p, n=n))


# ===== T2: chat x model interaction on erosion (headline cells, points 1 and 5) =====
def chat_effect(d):
    keep = ['pair', 'penalty_point', 'erosion_share'] + [m for m, _ in MET]
    t = d[(d.arm == 'headline-tacit') & d.penalty_point.isin([1, 5])][keep]
    c = d[(d.arm == 'headline-chat') & d.penalty_point.isin([1, 5])][keep]
    return t.merge(c, on=['pair', 'penalty_point'], suffixes=('_tacit', '_chat'))


eo, eq, eq0 = chat_effect(oN), chat_effect(q1), chat_effect(q0)
t2_levels = []
for nm, e in [('gpt-oss-20b', eo), ('qwen3-32b thinking on', eq), ('qwen3-32b thinking off', eq0)]:
    t2_levels.append(dict(model=nm, games_per_arm=len(e), erosion_no_chat=e.erosion_share_tacit.mean(), erosion_chat=e.erosion_share_chat.mean()))
    for met in ['erosion_share'] + [m for m, _ in MET]:
        v = (e[met + '_chat'] - e[met + '_tacit']).groupby(e.pair).mean()
        rows.append(summarise('T2 chat minus no chat, headline points 1 and 5: ' + nm, met, v.values, '(wording, seed) pairs'))
pd.DataFrame(t2_levels).to_csv(os.path.join(out, 't2_erosion_chat_levels.csv'), index=False)
j = eo.merge(eq, on=['pair', 'penalty_point'], suffixes=('_o', '_q'))
v = ((j.erosion_share_chat_o - j.erosion_share_tacit_o) - (j.erosion_share_chat_q - j.erosion_share_tacit_q)).groupby(j.pair).mean()
rows.append(summarise('T2 interaction: chat effect on erosion, gpt-oss minus Qwen (thinking on)', 'erosion_share', v.values,
                      '(wording, seed) pairs; %d matched (point, pair) cells' % len(j)))
primary['T2 erosion: chat x model interaction'] = rows[-1]['p_perm']

# ===== T3: exploration framing (wordings 2 and 4) vs the other wordings =====
EXPLORE = {2, 4}
LEN_OF = o.groupby('pair').planned_length.first().to_dict()


def explore_stat(d, met, explore_pairs):
    d = d.dropna(subset=[met]).copy()
    d['res'] = d[met] - d.groupby('cell')[met].transform('mean')
    d['ex'] = d.pair.isin(explore_pairs)
    cm = d.groupby(['cell', 'ex']).res.mean().unstack().dropna()
    return cm[True] - cm[False]


pairs = sorted(o.pair.unique())
ex_pairs = [p for p in pairs if int(p.split('_')[0]) in EXPLORE]
by_len = {}
for p in pairs:
    by_len.setdefault(LEN_OF[p], []).append(p)
# exact stratified regrouping null: within each planned horizon choose 2 of its 5 seeds as "explore" (10^4 groupings)
groupings = [sum(c, []) for c in itertools.product(*[[list(x) for x in itertools.combinations(sorted(v), 2)] for v in by_len.values()])]
# wording-block null: any 2 of the 5 wordings (10 groupings)
wblocks = [[p for p in pairs if int(p.split('_')[0]) in set(c)] for c in itertools.combinations(range(5), 2)]


def fast_null(d, met, groups):
    """Vectorised regrouping null: cell x pair residual matrix, then group means per grouping."""
    dd = d.dropna(subset=[met]).copy()
    dd['res'] = dd[met] - dd.groupby('cell')[met].transform('mean')
    M = dd.pivot_table(index='cell', columns='pair', values='res', aggfunc='mean').reindex(columns=pairs)
    X = M.values; ok = ~np.isnan(X); X0 = np.where(ok, X, 0.0)
    out_ = []
    for g in groups:
        msk = np.isin(pairs, g)
        se = (X0[:, msk]).sum(1); ne = ok[:, msk].sum(1)
        so = (X0[:, ~msk]).sum(1); no = ok[:, ~msk].sum(1)
        good = (ne > 0) & (no > 0)
        out_.append(np.mean(se[good] / ne[good] - so[good] / no[good]))
    return np.array(out_)


t3_rows = []
for nm, d in [('gpt-oss-20b', oN), ('qwen3-32b thinking on', q1), ('qwen3-32b thinking off', q0)]:
    for met, lab in MET + [('erosion_share', 'Erosion share')]:
        cdiff = explore_stat(d, met, ex_pairs)
        obs = cdiff.mean()
        lo, hi, se = boot_ci(cdiff.values)
        dd = d.dropna(subset=[met]).copy(); dd['res'] = dd[met] - dd.groupby('cell')[met].transform('mean')
        pm = dd.groupby('pair').res.mean()
        e_v = pm[pm.index.isin(ex_pairs)].values; n_v = pm[~pm.index.isin(ex_pairs)].values
        bs = e_v[RNG.integers(0, len(e_v), (B, len(e_v)))].mean(1) - n_v[RNG.integers(0, len(n_v), (B, len(n_v)))].mean(1)
        null = fast_null(d, met, groupings)
        wnull = fast_null(d, met, wblocks)
        t3_rows.append(dict(model=nm, outcome=met, est=obs,
                            ci_lo_pairs=np.percentile(bs, 2.5), ci_hi_pairs=np.percentile(bs, 97.5),
                            ci_lo_cells=lo, ci_hi_cells=hi, n_cells=len(cdiff), share_cells_negative=float((cdiff < 0).mean()),
                            p_seed_regroup=float(np.mean(np.abs(null) >= abs(obs) - 1e-12)), n_regroupings=len(groupings),
                            p_wording_block=float(np.mean(np.abs(wnull) >= abs(obs) - 1e-12)), n_wording_blocks=len(wblocks),
                            mde_pairs=2.8 * np.std(bs, ddof=1)))
        if nm == 'gpt-oss-20b' and met == 'price_index':
            primary['T3 exploration framing, gpt-oss price index'] = t3_rows[-1]['p_seed_regroup']
t3 = pd.DataFrame(t3_rows); t3.to_csv(os.path.join(out, 't3_explore_framing.csv'), index=False)
wrows = []
for nm, d in [('gpt-oss-20b', oN), ('qwen3-32b thinking on', q1), ('qwen3-32b thinking off', q0)]:
    for met, lab in MET + [('erosion_share', 'Erosion share')]:
        dd = d.dropna(subset=[met]).copy(); dd['res'] = dd[met] - dd.groupby('cell')[met].transform('mean')
        cw = dd.groupby(['cell', 'wording']).res.mean().unstack()
        for w in range(5):
            wrows.append(dict(model=nm, outcome=met, wording=w, resid_mean=cw[w].mean(),
                              share_cells_above=float((cw[w] > 0).mean()), n_cells=int(cw[w].notna().sum())))
pd.DataFrame(wrows).to_csv(os.path.join(out, 't3_wording_residuals.csv'), index=False)
# T3b: framing x model, common cells
common = sorted(set(oN.cell) & set(q1.cell))
oc, qc = oN[oN.cell.isin(common)], q1[q1.cell.isin(common)]
nulla = fast_null(oc, 'price_index', groupings); nullb = fast_null(qc, 'price_index', groupings)
cd = (explore_stat(oc, 'price_index', ex_pairs) - explore_stat(qc, 'price_index', ex_pairs)).dropna()
obs = cd.mean()
null = nulla - nullb
lo, hi, se = boot_ci(cd.values)
p3b = float(np.mean(np.abs(null) >= abs(obs) - 1e-12))
rows.append(dict(test='T3b exploration framing x model: gpt-oss minus Qwen (thinking on), common cells', outcome='price_index',
                 unit='cells (arm x penalty point) common to both models; p from the seed-regrouping null', n=len(cd), est=obs,
                 ci_lo=lo, ci_hi=hi, p_perm=p3b, mde=2.8 * se))
primary['T3b exploration framing x model'] = p3b
rel = []
for nm, d in [('gpt-oss-20b', oN), ('qwen3-32b thinking on', q1), ('qwen3-32b thinking off', q0)]:
    dd = d.copy(); dd['res'] = dd.price_index - dd.groupby('cell').price_index.transform('mean')
    cw = dd.groupby(['cell', 'wording']).res.mean().unstack().dropna()
    rs = []
    for _ in range(2000):
        idx = RNG.permutation(len(cw)); a = cw.iloc[idx[:len(cw) // 2]].mean(); b = cw.iloc[idx[len(cw) // 2:]].mean()
        rs.append(np.corrcoef(a, b)[0, 1])
    rel.append(dict(model=nm, split_half_r_median=np.median(rs), q025=np.percentile(rs, 2.5), q975=np.percentile(rs, 97.5),
                    wording_effect_range=cw.mean().max() - cw.mean().min(), n_cells=len(cw)))
pd.DataFrame(rel).to_csv(os.path.join(out, 't3_split_half.csv'), index=False)

# ===== T4: game length (planned horizon 19-20 vs 7 rounds) =====
for nm, d in [('gpt-oss-20b', oN), ('qwen3-32b thinking on', q1), ('qwen3-32b thinking off', q0)]:
    for met, lab in MET:
        dd = d.dropna(subset=[met]).copy(); dd['res'] = dd[met] - dd.groupby('cell')[met].transform('mean')
        cl = (dd[dd.planned_length >= 19].groupby('cell').res.mean() - dd[dd.planned_length == 7].groupby('cell').res.mean()).dropna()
        r = summarise('T4 planned horizon 19-20 minus 7 rounds: ' + nm, met, cl.values, 'cells (arm x penalty point), within-cell residuals')
        rows.append(r)
        if nm == 'gpt-oss-20b' and met == 'price_index':
            primary['T4 game length, gpt-oss price index'] = r['p_perm']


# ===== T5: end-game (last round of a random-stop game vs the 3 rounds before) =====
def endgame(r, run):
    rr = r.merge(run[['row_id', 'end_reason', 'rounds_played']], on='row_id')
    h = rr[(rr.end_reason == 'HORIZON') & (rr.rounds_played >= 4)]
    last = h[h['round'] == h.rounds_played].set_index('row_id').market_price
    prev = h[(h['round'] < h.rounds_played) & (h['round'] >= h.rounds_played - 3)].groupby('row_id').market_price.mean()
    dd = (last - prev).rename('d').reset_index().merge(run[['row_id', 'pair']], on='row_id')
    return dd.groupby('pair').d.mean().values, len(dd)


for nm, r, d in [('gpt-oss-20b', ro, oN), ('qwen3-32b thinking on', rq, q1), ('qwen3-32b thinking off', rq, q0)]:
    v, ng = endgame(r[r.row_id.isin(d.row_id)], d)
    rows.append(summarise('T5 end-game: last-round best quote minus mean of the 3 rounds before (random-stop games): ' + nm,
                          'best quote (raw half-spread)', v, '(wording, seed) pairs over %d games' % ng))
    if nm == 'gpt-oss-20b':
        primary['T5 end-game, gpt-oss'] = rows[-1]['p_perm']


# ===== T6: round-1 lock-in, gpt-oss vs Qwen (within-cell Spearman of round-1 vs rounds 2+) =====
def r1res(d):
    d = d.dropna(subset=['r1_price', 'rest_price']).copy()
    for c in ['r1_price', 'rest_price']:
        d[c] = d[c] - d.groupby('cell')[c].transform('mean')
    return d


do_, dq_ = r1res(oN), r1res(q1)
gro, grq = dict(tuple(do_.groupby('pair'))), dict(tuple(dq_.groupby('pair')))
po = sorted(gro); bs = []
for _ in range(2000):
    s = RNG.choice(po, len(po))
    a = pd.concat([gro[p] for p in s]); b = pd.concat([grq[p] for p in s])
    bs.append(corr(a.r1_price, a.rest_price)[0] - corr(b.r1_price, b.rest_price)[0])
bs = np.array(bs)
obs = corr(do_.r1_price, do_.rest_price)[0] - corr(dq_.r1_price, dq_.rest_price)[0]
p6 = float(min(1.0, 2 * min(np.mean(bs <= 0), np.mean(bs >= 0))))
rows.append(dict(test='T6 round-1 lock-in: within-cell Spearman (round-1 vs rounds 2+), gpt-oss minus Qwen (thinking on)',
                 outcome='Spearman rho difference', unit='(wording, seed) pairs (cluster bootstrap; p = 2 x bootstrap tail)',
                 n=len(po), est=obs, ci_lo=np.percentile(bs, 2.5), ci_hi=np.percentile(bs, 97.5), p_perm=p6, mde=2.8 * bs.std()))
primary['T6 round-1 lock-in, model difference'] = p6

# ===== Holm over the family "discovery candidates" =====
fam = pd.DataFrame({'test': list(primary), 'p': list(primary.values())}).sort_values('p').reset_index(drop=True)
m = len(fam); adj = []; run_max = 0
for i, p in enumerate(fam.p):
    run_max = max(run_max, min(1, (m - i) * p)); adj.append(run_max)
fam['holm_p'] = adj; fam['family'] = 'discovery candidates (m=%d)' % m
fam.to_csv(os.path.join(out, 'holm_family.csv'), index=False)
pd.DataFrame(rows).to_csv(os.path.join(out, 'contrasts.csv'), index=False)
pd.DataFrame(cor_rows).to_csv(os.path.join(out, 'correlations.csv'), index=False)
keep = ['row_id', 'arm', 'cell', 'pair', 'wording', 'seed', 'planned_length', 'communication'] + DYN + ['scored_rounds']
o[keep].to_csv(os.path.join(out, 'pergame_dynamics_oss.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 100)
print(fam.to_string()); print(pd.DataFrame(rows).round(4).to_string()); print(t3.round(4).to_string())
print(pd.DataFrame(rel).round(3).to_string()); print(pd.DataFrame(cor_rows).round(3).to_string())
print(pd.DataFrame(lv).round(3).to_string()); print(pd.DataFrame(t2_levels).round(3).to_string()); print(pa.round(3).to_string())
