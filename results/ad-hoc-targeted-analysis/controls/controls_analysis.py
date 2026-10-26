"""Strict-compete and joint-profit control check. Usage: python controls_analysis.py STEPS_DIR OUT_DIR
STEPS_DIR holds neutral/step1 and anchored/step1 (run.csv); round quotes come from the sibling tables_<run>_final/rounds.csv."""
import sys, numpy as np, pandas as pd
steps, out = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(1)
def ci(x, B=10000):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x)==0: return (np.nan,)*3
    m = rng.choice(x, (B, len(x))).mean(1)
    return x.mean(), *np.percentile(m, [2.5, 97.5])
fmt = lambda t, d=3: f"{t[0]:.{d}f} ({t[1]:.{d}f} to {t[2]:.{d}f})"
rows_mode, rows_run, rows_pair, rows_dist = [], [], [], []
for run in ['neutral', 'anchored']:
    r = pd.read_csv(f'{steps}/{run}/step1/run.csv', low_memory=False)
    r = r[(r.status=='done') & r.arm.isin(['ctl-32b-compete','ctl-32b-joint','headline-chat']) & (r.penalty_point==3)]
    q = pd.read_csv(f'{steps}/../tables_{run}_final/rounds.csv', low_memory=False)
    q = q[q.trial_id.isin(r.trial_id)].merge(r[['trial_id','arm','thinking','wording','seed']], on='trial_id')
    q['imp'] = q.imputed.fillna(0).astype(int)
    q = q[q.imp==0]  # drop imputed (failed-parse) quotes
    q['mode'] = q.thinking
    g = q.groupby(['arm','mode','trial_id']).agg(mean_q=('quote','mean'), floor=('quote', lambda s:(s<=1.0+1e-9).mean()),
          ge2=('quote', lambda s:(s>=2.0).mean()), at3=('quote', lambda s:(s>=3.0-1e-9).mean()), n=('quote','size')).reset_index()
    g = g.merge(r[['trial_id','wording','seed']], on='trial_id')
    g['run'] = run
    for (arm, mode), s in g.groupby(['arm','mode']):
        qq = q[(q.arm==arm)&(q['mode']==mode)].quote
        rows_mode.append(dict(run=run, arm=arm, mode=mode, games=len(s), firm_rounds=len(qq),
            mean_quote=qq.mean(), min_quote=qq.min(), share_at_1_00=(qq<=1+1e-9).mean(), share_ge_2_00=(qq>=2).mean(),
            share_at_3_00=(qq>=3-1e-9).mean(), games_all_at_floor=int((s['floor']==1).sum()), games_ge2_every_round=int((s.ge2==1).sum()),
            gap_to_monopoly_mean=(3-qq).mean(),
            mean_quote_game_ci=fmt(ci(s.mean_q)), share_ge2_game_ci=fmt(ci(s.ge2))))
    for arm, s in g.groupby('arm'):
        qq = q[q.arm==arm].quote
        rows_run.append(dict(run=run, arm=arm, firm_rounds=len(qq), mean_quote=qq.mean(), share_at_1_00=(qq<=1+1e-9).mean(),
            share_ge_2_00=(qq>=2).mean(), share_at_3_00=(qq>=3-1e-9).mean()))
    # per-round distribution (binned)
    q['bin'] = pd.cut(q.quote, [0,1.0+1e-9,1.5,2.0-1e-9,2.5,2.99,3.0+1e-9,99], labels=['1.00','1.01-1.50','1.51-1.99','2.00-2.50','2.51-2.99','3.00','>3.00'], right=True)
    q['bin'] = pd.cut(q.quote, [0,1+1e-9,1.5,2-1e-9,2.5,3-1e-9,3+1e-9,99], labels=['1.00','1.01-1.50','1.51-1.99','2.00-2.50','2.51-2.99','3.00','>3.00'])
    d = q.groupby(['arm','mode','bin'], observed=False).size().rename('firm_rounds').reset_index(); d['run']=run
    d['share'] = d.firm_rounds / d.groupby(['arm','mode']).firm_rounds.transform('sum'); rows_dist.append(d)
    # paired over wording x seed x mode
    pv = g.pivot_table(index=['wording','seed','mode'], columns='arm', values=['mean_q','floor','ge2'])
    for mode in ['off','on']:
        p = pv.xs(mode, level='mode').dropna(subset=[('mean_q','ctl-32b-joint'),('mean_q','ctl-32b-compete')])
        for nm, a, b in [('joint minus strict-compete','ctl-32b-joint','ctl-32b-compete'), ('joint minus headline-chat (p3 private chat)','ctl-32b-joint','headline-chat'), ('strict-compete minus headline-chat','ctl-32b-compete','headline-chat')]:
            pp = pv.xs(mode, level='mode'); pp = pp.dropna(subset=[('mean_q',a),('mean_q',b)])
            dd = pp[('mean_q',a)] - pp[('mean_q',b)]
            rows_pair.append(dict(run=run, mode=mode, contrast=nm, pairs=len(pp), mean_quote_diff=fmt(ci(dd))))
        # monopoly gap among joint games
    gg = g[g.arm=='ctl-32b-joint']; 
    for mode, s in gg.groupby('mode'):
        rows_pair.append(dict(run=run, mode=mode, contrast='joint: distance below monopoly 3.00 (per game mean)', pairs=len(s), mean_quote_diff=fmt(ci(3-s.mean_q))))
    g.to_csv(f'{out}/control_games_{run}.csv', index=False)
pd.DataFrame(rows_mode).to_csv(f'{out}/controls_by_mode.csv', index=False)
pd.DataFrame(rows_run).to_csv(f'{out}/controls_by_run.csv', index=False)
pd.DataFrame(rows_pair).to_csv(f'{out}/controls_paired.csv', index=False)
pd.concat(rows_dist).to_csv(f'{out}/controls_quote_distribution.csv', index=False)
print(pd.DataFrame(rows_mode).T.to_string()); print(pd.DataFrame(rows_run).to_string()); print(pd.DataFrame(rows_pair).to_string())
