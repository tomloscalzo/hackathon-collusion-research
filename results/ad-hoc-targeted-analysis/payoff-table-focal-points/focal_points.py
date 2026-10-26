"""Focal points on the printed payoff table: neutral (1.00,1.50,...,4.00) vs anchored (1.54, 2.09, 3.00) runs.

Usage:
  python -X utf8 focal_points.py --neutral-dir DIR --anchored-dir DIR [--formula-tables DIR] [--out DIR]

DIR (neutral/anchored) = a Step 1 folder holding run.csv and a tables/ (or equivalent) folder with rounds.csv; pass
--neutral-rounds / --anchored-rounds if rounds.csv lives elsewhere. Games join on run.csv.played_trial_id = rounds.trial_id.
--formula-tables = output of tools/trial/collect.py for the formula / no-numbers run (trials.csv, rounds.csv); optional, rerunnable.
Unit = game (LLM seats, non-imputed quotes). CIs = percentile bootstrap (10,000) over (wording, seed) pairs.
"""
import argparse, os, json, numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--neutral-dir', required=True); ap.add_argument('--anchored-dir', required=True)
ap.add_argument('--neutral-rounds'); ap.add_argument('--anchored-rounds')
ap.add_argument('--formula-tables'); ap.add_argument('--out', default='.')
a = ap.parse_args()
rng = np.random.default_rng(11)

PRINTED = {'neutral': {1.0, 1.5, 2.0, 2.49, 2.5, 3.0, 3.5, 4.0},
           'anchored': {1.0, 1.54, 2.08, 2.09, 3.0}}
PRINTED_N3_ANCH = {1.0, 1.44, 1.87, 1.88, 3.0}   # the three-firm arm's own anchored examples
HEAD = ['headline-tacit', 'headline-chat', 'headline-monitored']
def mode(t): return t.map({'off': 't0', 'on': 't1'})

def load(run, d, rp):
    r = pd.read_csv(os.path.join(d, 'run.csv'),
                    usecols=['played_trial_id', 'status', 'pair_key', 'arm', 'penalty_point', 'thinking', 'wording', 'seed',
                             'price_index', 'competitive_share', 'profit_gain_index'])
    r = r[r.status == 'done'].copy(); r['mode'] = mode(r.thinking)
    r['pair'] = r.wording.astype(str) + '_' + r.seed.astype(str)
    q = pd.read_csv(rp or os.path.join(d, 'tables', 'rounds.csv'),
                    usecols=['trial_id', 'seat', 'quote', 'imputed', 'parse_status'])
    q = q[q.seat.isin(['llm1', 'llm2', 'llm3']) & (q.imputed == 0)]
    q = q.merge(r[['played_trial_id', 'arm']], left_on='trial_id', right_on='played_trial_id')
    q['q'] = q.quote.round(2)
    ps = q.arm.map(lambda x: PRINTED_N3_ANCH if (run == 'anchored' and x == 'n3-cheater') else PRINTED[run])
    q['printed'] = [v in s for v, s in zip(q.q, ps)]
    q['floor'] = q.q == 1.0
    g = q.groupby('played_trial_id').agg(share_printed=('printed', 'mean'), share_floor=('floor', 'mean'),
                                         n_quotes=('q', 'size')).reset_index()
    r = r.merge(g, on='played_trial_id')
    r['run'] = run
    return r, q

N, QN = load('neutral', a.neutral_dir, a.neutral_rounds)
A, QA = load('anchored', a.anchored_dir, a.anchored_rounds)
os.makedirs(a.out, exist_ok=True)

# ---- 1. shares and modal quotes by arm x mode x penalty (firm-round pooled)
rows = []
for run, r, q in [('neutral', N, QN), ('anchored', A, QA)]:
    q = q.merge(r[['played_trial_id', 'mode', 'penalty_point']], on='played_trial_id')
    for (arm, m, p), s in q.groupby(['arm', 'mode', 'penalty_point']):
        vc = s.q.value_counts(normalize=True)
        top = '; '.join(f'{v:.2f} ({100*x:.0f}%)' for v, x in vc.head(3).items())
        nz = s[~s.floor]
        rows.append(dict(run=run, arm=arm, mode=m, penalty_point=p, n_games=s.played_trial_id.nunique(), n_quotes=len(s),
                         share_printed=s.printed.mean(), share_at_1_00=s.floor.mean(),
                         share_printed_excl_1_00=nz.printed.mean() if len(nz) else np.nan,
                         share_round_005=(np.abs(s.q * 20 - np.round(s.q * 20)) < 1e-6).mean(),
                         modal_quotes=top, modal_1=vc.index[0], modal_1_share=vc.iloc[0]))
S = pd.DataFrame(rows); S.to_csv(os.path.join(a.out, 'quote_shares_by_cell.csv'), index=False, float_format='%.4f')

# pooled over headline arms / penalties, by run x mode (and communication arm)
rows = []
for run, r, q in [('neutral', N, QN), ('anchored', A, QA)]:
    q = q.merge(r[['played_trial_id', 'mode', 'penalty_point']], on='played_trial_id')
    for arm in HEAD + ['ALL headline']:
        for m in ['t0', 't1']:
            s = q[(q.arm.isin(HEAD) if arm == 'ALL headline' else q.arm == arm) & (q['mode'] == m)]
            vc = s.q.value_counts(normalize=True)
            rows.append(dict(run=run, arm=arm, mode=m, n_quotes=len(s), share_printed=s.printed.mean(),
                             share_at_1_00=s.floor.mean(),
                             modal_quotes='; '.join(f'{v:.2f} ({100*x:.0f}%)' for v, x in vc.head(3).items())))
P = pd.DataFrame(rows); P.to_csv(os.path.join(a.out, 'quote_shares_pooled.csv'), index=False, float_format='%.4f')

# ---- 2. paired neutral - anchored differences (pair = same arm, penalty, mode, wording, seed)
M = N.merge(A, on=['arm', 'penalty_point', 'mode', 'pair'], suffixes=('_n', '_a'))
metrics = ['price_index', 'competitive_share', 'profit_gain_index', 'share_printed']
def boot(d):
    d = np.asarray(d, float); b = rng.choice(d, (10000, len(d))).mean(axis=1)
    return d.mean(), *np.percentile(b, [2.5, 97.5])
rows = []
for k in metrics:
    M[k + '_d'] = M[k + '_n'] - M[k + '_a']
for (arm, m), s in M[M.arm.isin(HEAD)].groupby(['arm', 'mode']):
    for k in metrics:
        pv = s.pivot_table(index='pair', columns='penalty_point', values=k + '_d')
        for p in pv.columns:
            d = pv[p].dropna()
            rows.append(dict(arm=arm, mode=m, penalty_point='p%d' % p, metric=k, n_pairs=len(d), **dict(zip(['diff', 'lo', 'hi'], boot(d)))))
        d = pv[[1, 3, 4, 5]].dropna().mean(axis=1)
        rows.append(dict(arm=arm, mode=m, penalty_point='pooled', metric=k, n_pairs=len(d), **dict(zip(['diff', 'lo', 'hi'], boot(d)))))
for m, s in M[M.arm.isin(HEAD)].groupby('mode'):
    for k in metrics:
        pv = s.pivot_table(index='pair', columns=['arm', 'penalty_point'], values=k + '_d')
        d = pv.dropna().mean(axis=1)
        rows.append(dict(arm='ALL headline', mode=m, penalty_point='pooled', metric=k, n_pairs=len(d), **dict(zip(['diff', 'lo', 'hi'], boot(d)))))
D = pd.DataFrame(rows); D.to_csv(os.path.join(a.out, 'paired_neutral_minus_anchored.csv'), index=False, float_format='%.4f')
print(D[D.penalty_point == 'pooled'].round(3).to_string())
print(P.round(3).to_string())

# ---- 3. formula / no-numbers arms (pending until games are DONE; rerunnable)
fx = None
if a.formula_tables and os.path.exists(os.path.join(a.formula_tables, 'trials.csv')):
    t = pd.read_csv(os.path.join(a.formula_tables, 'trials.csv'))
    t = t[(t.status == 'done') & t.arm.isin(['fx-chat-p1', 'fx-chat-p5', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1'])].copy()
    if len(t):
        q = pd.read_csv(os.path.join(a.formula_tables, 'rounds.csv'))
        q = q[q.trial_id.isin(t.trial_id) & (q.imputed == 0) & q.seat.isin(['llm1', 'llm2'])].copy()
        q['q'] = q.quote.round(2)
        q['on_neutral_set'] = q.q.isin(PRINTED['neutral']); q['on_anchored_set'] = q.q.isin(PRINTED['anchored'])
        q['round_005'] = np.abs(q.q * 20 - np.round(q.q * 20)) < 1e-6; q['floor'] = q.q == 1.0
        g = q.groupby('trial_id').agg(share_neutral_set=('on_neutral_set', 'mean'), share_anchored_set=('on_anchored_set', 'mean'),
                                      share_round_005=('round_005', 'mean'), share_at_1_00=('floor', 'mean'),
                                      competitive_share=('competitive_round', 'mean'), profit_per_firm_round=('profit', 'mean')).reset_index()
        g['profit_gain_index'] = g.profit_per_firm_round / 40.0   # 2-firm games: monopoly profit 40, competitive 0 (matches run.csv to 3 d.p.)
        t = t.merge(g, on='trial_id'); t['price_index'] = t.collusion_level
        t['mode'] = np.where(t.thinking.astype(str).isin(['on', '1', '1.0']), 't1', 't0')
        rows = []
        for (arm, m), s in t.groupby(['arm', 'mode']):
            qq = q.merge(s[['trial_id']], on='trial_id'); qq = qq[qq.trial_id.isin(s.trial_id)]
            tm = qq[qq.trial_id.isin(s.trial_id)]
            vc = tm.q.value_counts(normalize=True)
            rows.append(dict(arm=arm, mode=m, n_done_games=len(s), price_index=s.price_index.mean(), profit_gain_index=s.profit_gain_index.mean(),
                             competitive_share=s.competitive_share.mean(), share_on_neutral_set=tm.on_neutral_set.mean(),
                             share_on_anchored_set=tm.on_anchored_set.mean(), share_round_005=tm.round_005.mean(),
                             share_at_1_00=tm.floor.mean(),
                             modal_quotes='; '.join(f'{v:.2f} ({100*x:.0f}%)' for v, x in vc.head(3).items())))
        fx = pd.DataFrame(rows); fx.to_csv(os.path.join(a.out, 'formula_arms_done_games.csv'), index=False, float_format='%.4f')
        print(fx.round(3).to_string())

# ---- figure: share of quotes on printed values, neutral vs anchored, by arm and mode (drawn by figures.py;
#      re-render from the committed CSV alone with: python -X utf8 figures.py)
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figures import printed_share
printed_share(P, os.path.join(a.out, 'fig_printed_share.png'))
