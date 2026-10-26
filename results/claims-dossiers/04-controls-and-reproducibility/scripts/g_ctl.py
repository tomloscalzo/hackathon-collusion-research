import sys; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from common import *
rows = []; lev = []
for model, which, think in [('gpt-oss-20b (reasoning medium)', 'oss', 't1'), ('Qwen3-32B thinking on', 'qwen', 't1'), ('Qwen3-32B thinking off', 'qwen', 't0')]:
    d = load(which)
    comp = sel(d, 'ctl-32b-compete', 3, think); joint = sel(d, 'ctl-32b-joint', 3, think); chat = sel(d, 'headline-chat', 3, think)
    for m in MCOLS:
        for lab, a, b in [('compete - chat', comp, chat), ('joint - chat', joint, chat), ('joint - compete', joint, comp)]:
            r = contrast(a, b, m); r.pop('d'); r.update(model=model, contrast=lab, metric=MNAME[m]); rows.append(r)
    for arm, g in [('strict-compete control', comp), ('joint-profit control', joint), ('headline-chat p3', chat)]:
        lev.append(dict(model=model, arm=arm, n=len(g), **{MNAME[m]: g[m].mean() for m in MCOLS},
                        **{MNAME[m] + ' min': g[m].min() for m in ['profit_gain_index']}, **{MNAME[m] + ' max': g[m].max() for m in ['profit_gain_index','price_index']}))
R = pd.DataFrame(rows)
# Holm: family = 3 contrasts x 5 metrics = 15 per model
R['p_holm'] = np.nan
for mod in R.model.unique():
    k = R.model == mod; R.loc[k, 'p_holm'] = holm(R.loc[k, 'p_signflip'].values)
R.to_csv(OUT + '/g_ctl_contrasts.csv', index=False, float_format='%.5g')
L = pd.DataFrame(lev); L.to_csv(OUT + '/g_ctl_levels.csv', index=False, float_format='%.4f')
print(L.to_string()); print(R[['model','contrast','metric','diff','ci_lo','ci_hi','p_signflip','p_holm','mde','n_pairs']].to_string())
# waves of the compared arms (gpt-oss)
o = load('oss')
print(o[o.arm.isin(['ctl-32b-compete','ctl-32b-joint','headline-chat','fx-ctl-joint'])&(o.penalty_point==3)].groupby('arm').wave.agg(lambda s: sorted(set(s))))
q = load('qwen'); print(q[q.arm.isin(['ctl-32b-compete','ctl-32b-joint','headline-chat'])&(q.penalty_point==3)].groupby(['arm','think']).wave.agg(lambda s: sorted(set(s))))
# fx-ctl-joint vs ctl-32b-joint (gpt-oss)
fx = sel(o,'fx-ctl-joint',3); jt = sel(o,'ctl-32b-joint',3); rr = []
for m in MCOLS:
    r = contrast(fx, jt, m); r.pop('d'); r.update(metric=MNAME[m], contrast='fx-ctl-joint - ctl-32b-joint'); rr.append(r)
pd.DataFrame(rr).to_csv(OUT + '/g_ctl_fx_joint.csv', index=False, float_format='%.5g'); print(pd.DataFrame(rr)[['metric','diff','ci_lo','ci_hi','p_signflip']])
# compete: how far from 0 exactly
for nm, dd in [('oss', o), ('qwen t1', q[q.think=='t1'])]:
    c = sel(dd, 'ctl-32b-compete', 3); print(nm, 'compete games with pgi>0.02:', int((c.profit_gain_index>0.02).sum()), 'of', len(c), c.profit_gain_index.describe()[['mean','max']].to_dict(), 'spread max', c.market_price_mean.max())
