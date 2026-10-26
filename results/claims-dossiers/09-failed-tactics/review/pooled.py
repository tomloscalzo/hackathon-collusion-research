import os
import pandas as pd, numpy as np
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
o0=pd.read_csv(O,low_memory=False)
print(o0[(o0.arm=='r4-announced')&(o0.status!='done')][['status_description','failure_reason']].drop_duplicates().to_string()[:600])
cols=[c for c in ['source_root','model_profile','code_commit','context_window','supersession'] if c in o0]
print(o0[o0.in_primary==1].groupby('arm')[cols].agg(lambda s: '|'.join(sorted(map(str,s.unique())))[:90]).loc[['headline-chat','hrep-fx-chat-p1','hrep-nx-chat-p1','d-cot-monitor-a','r2s-confidant','r2f-confidant','wd-noncomp','d-placebo','m-asym']].to_string())
o=o0[o0.in_primary==1]
rng=np.random.default_rng(5)
hc=o[(o.arm=='headline-chat')&(o.penalty_point==1)].set_index(['wording','seed'])
r1=o[o.arm=='hrep-fx-chat-p1'].set_index(['wording','seed']); r2=o[o.arm=='hrep-nx-chat-p1'].set_index(['wording','seed'])
for k in ['price_index','profit_gain_index']:
    pool=pd.concat([hc[k],r1[k],r2[k]],axis=1).mean(1)
    for arm in ['d-cot-monitor-a','wd-notice-only','wd-noncomp','wd-ask-noreport','r2s-confidant','r2f-confidant']:
        a=o[o.arm==arm].set_index(['wording','seed'])[k]
        d=(a-pool).dropna().values; bs=rng.choice(d,(20000,len(d))).mean(1)
        fl=rng.choice([-1,1],(100000,len(d))); p=(np.abs((fl*d).mean(1))>=abs(d.mean())-1e-12).mean()
        print(k,arm,'vs pooled ctl n',len(d),round(d.mean(),3),np.percentile(bs,[2.5,97.5]).round(3),'p',round(p,3))
print('pooled control PI', pd.concat([hc.price_index,r1.price_index,r2.price_index],axis=1).mean(1).mean().round(3))
