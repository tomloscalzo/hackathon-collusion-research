"""Introspection arms: say-vs-do candour, effect of asking, short vs long.
Usage: python introspection_analysis.py STEPS_DIR READING_OUT_DIR OUT_DIR
STEPS_DIR: analysis_final/steps (neutral|anchored/step1/run.csv); READING_OUT_DIR: analysis_final/extra_reading
(out_intro_<run>/intro_answers_classified.csv, produced by reading_intro.py - the keyword say-vs-do classifier, UNVALIDATED on anchored text)."""
import sys, numpy as np, pandas as pd
steps, rd, out = sys.argv[1:4]
rng = np.random.default_rng(7)
ARMS = ['r2f-confidant','r3f-public','r2s-confidant','r3s-public','r4-announced']
KIND = {'r2f-confidant':'fed back, confidant','r3f-public':'fed back, public','r2s-confidant':'saved only, confidant',
        'r3s-public':'saved only, public','r4-announced':'announced, public (post-game)'}
def boot(x, B=5000):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    m = rng.choice(x, (B, len(x))).mean(1); return x.mean(), *np.percentile(m, [2.5, 97.5])
def game_share(df, col, val):
    """share of answers equal to val, CI by resampling games"""
    g = df.groupby('trial_id')[col].agg(lambda s: (s==val).sum()), df.groupby('trial_id').size()
    k, n = g; idx = np.arange(len(k)); est = k.sum()/n.sum()
    m = []
    for _ in range(3000):
        s = rng.choice(idx, len(idx)); m.append(k.values[s].sum()/n.values[s].sum())
    return est, *np.percentile(m, [2.5, 97.5])
f = lambda t, pct=False, d=1: (f"{100*t[0]:.{d}f}% ({100*t[1]:.{d}f} to {100*t[2]:.{d}f})" if pct else f"{t[0]:+.3f} ({t[1]:.3f} to {t[2]:.3f})")
sd, rows_len, rows_aud, rows_beh, rows_run = [], [], [], [], []
for run in ['neutral','anchored']:
    c = pd.read_csv(f'{rd}/out_intro_{run}/intro_answers_classified.csv', usecols=['trial_id','arm','mode_t','cls','words_ans','candid'])
    c['short'] = c.words_ans < 60
    for arm in ARMS:
        a = c[c.arm==arm]
        row = dict(run=run, arm=arm, kind=KIND[arm], answers=len(a), games=a.trial_id.nunique(), mean_words=round(a.words_ans.mean(),1))
        for k in ['consistent','understated','overstated','evasive']:
            row[k] = f(game_share(a, 'cls', k), True)
        sd.append(row)
        for m, s in a.groupby('mode_t'):
            rows_len.append(dict(run=run, arm=arm, thinking={'t0':'off','t1':'on'}[m], answers=len(s), mean_words=round(s.words_ans.mean(),1),
                evasive=f(game_share(s,'cls','evasive'),True), consistent=f(game_share(s,'cls','consistent'),True)))
    c['length'] = np.where(c.arm.isin(['r2s-confidant','r3s-public']), 'short (about 30 words, saved only)', 'long (about 100 words)')
    for l, s in c.groupby('length'):
        rows_aud.append(dict(run=run, cut='length', group=l, answers=len(s), evasive=f(game_share(s,'cls','evasive'),True), consistent=f(game_share(s,'cls','consistent'),True)))
    fed = c[c.arm.isin(['r2f-confidant','r3f-public'])]; sp = c[c.arm.isin(['r2s-confidant','r3s-public'])]
    for nm, s in [('confidant (r2f)', c[c.arm=='r2f-confidant']), ('public (r3f)', c[c.arm=='r3f-public']), ('confidant (r2s)', c[c.arm=='r2s-confidant']), ('public (r3s)', c[c.arm=='r3s-public'])]:
        rows_aud.append(dict(run=run, cut='audience', group=nm, answers=len(s), evasive=f(game_share(s,'cls','evasive'),True), consistent=f(game_share(s,'cls','consistent'),True)))
    # run.csv: arm vs control on the price index (delta_price_index, paired on wording+seed+mode with headline-chat p1)
    r = pd.read_csv(f'{steps}/{run}/step1/run.csv', low_memory=False); r = r[(r.status=='done')]
    for arm in ARMS:
        a = r[r.arm==arm]
        for m in ['off','on','pooled']:
            s = a if m=='pooled' else a[a.thinking==m]
            d = s.delta_price_index.dropna()
            if m=='pooled':  # mean per pair across the two modes
                d = s.dropna(subset=['delta_price_index']).groupby(['wording','seed']).delta_price_index.mean()
            e = boot(d)
            rows_beh.append(dict(run=run, arm=arm, thinking=m, pairs=len(d), price_index_arm_minus_control=f(e), est=e[0], lo=e[1], hi=e[2]))
        # UNVALIDATED keyword candour columns
        for who in ['confidant','public']:
            col = f'candour_{who}'
            if a[col].notna().any():
                rows_run.append(dict(run=run, arm=arm, audience=who, games=int(a[col].notna().sum()),
                  mentions_coordination_when_truth_is_coordination=f(boot(a[col].dropna()),True),
                  mentions_coordination_when_none=f(boot(a[f'invented_confession_{who}'].dropna()),True) if a[f'invented_confession_{who}'].notna().sum()>2 else 'n/a (<3 games)'))
    # all-five pooled
    p = r[r.arm.isin(ARMS)].dropna(subset=['delta_price_index'])
    for m in ['off','on']:
        d = p[p.thinking==m].groupby(['wording','seed']).delta_price_index.mean(); e = boot(d)
        rows_beh.append(dict(run=run, arm='all five arms', thinking=m, pairs=len(d), price_index_arm_minus_control=f(e), est=e[0], lo=e[1], hi=e[2]))
for n, rows in [('saydo_by_arm', sd), ('length_by_mode', rows_len), ('length_and_audience', rows_aud), ('arm_vs_control_price_index', rows_beh), ('runcsv_keyword_candour_UNVALIDATED', rows_run)]:
    pd.DataFrame(rows).to_csv(f'{out}/{n}.csv', index=False)
    print('==', n); print(pd.DataFrame(rows).drop(columns=[c for c in ['est','lo','hi'] if c in pd.DataFrame(rows).columns]).to_string())
