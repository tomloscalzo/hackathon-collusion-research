import os
import pandas as pd, numpy as np
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
o=pd.read_csv(O,low_memory=False); o=o[o.in_primary==1]
a=o[(o.arm=='wd-noncomp')]; c=o[o.arm=='wd-ask-noreport']
m=a.merge(c,on=['wording','seed'],suffixes=('_a','_c'))
rng=np.random.default_rng(3)
for k in ['profit_gain_index','price_index']:
    m['d']=m[k+'_a']-m[k+'_c']
    g=m.groupby('wording').d.agg(['mean','std','size']); print(k); print(g.round(3))
    v=m.d.values; w=m.wording.values
    # within-wording residual variance vs total
    resid=m.d-m.groupby('wording').d.transform('mean')
    print(' total sd %.3f within-wording sd %.3f'%(v.std(ddof=1), resid.std(ddof=1)))
    B=20000
    strata=[np.where(w==s)[0] for s in np.unique(w)]
    sb=np.concatenate([v[ix][rng.integers(0,len(ix),(B,len(ix)))] for ix in strata],1).mean(1)
    pb=v[rng.integers(0,len(v),(B,len(v)))].mean(1)
    print(' stratified CI', np.percentile(sb,[2.5,97.5]).round(3), 'pair CI', np.percentile(pb,[2.5,97.5]).round(3))
    wm=g['mean'].values; se=wm.std(ddof=1)/np.sqrt(5); print(' wording-level mean %.3f se %.3f t-CI [%.3f, %.3f]'%(wm.mean(),se,wm.mean()-2.776*se,wm.mean()+2.776*se))
    # stratified sign flip
    fl=rng.choice([-1,1],(200000,len(v))); print(' sign-flip p', ((np.abs((fl*v).mean(1))>=abs(v.mean())-1e-12).mean()).round(3))
