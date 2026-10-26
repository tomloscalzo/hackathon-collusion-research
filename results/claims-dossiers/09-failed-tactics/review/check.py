import os
import pandas as pd, numpy as np
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
Q=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/analysis_final/steps/neutral/step1/run.csv')
o=pd.read_csv(O,low_memory=False); q=pd.read_csv(Q,low_memory=False)
print("oss failed by arm:\n", o[o.status!='done'].groupby(['arm','penalty_point']).size())
print("oss failure reasons", o[o.status!='done'].failure_reason.value_counts())
print("supersession oss", o.supersession.value_counts(dropna=False).to_dict())
print("supersession qwen", q.supersession.value_counts(dropna=False).to_dict())
print("qwen not started by arm", q[q.status!='done'].groupby(['arm','thinking']).size().to_dict())
o=o[o.in_primary==1]; q=q[q.in_primary==1]
rng=np.random.default_rng(1)
M=['market_price_mean','price_index','profit_gain_index','competitive_share','matching_share']
def con(d,arm,apt,ctl,cpt,th=None,metrics=M):
    a=d[(d.arm==arm)&(d.penalty_point==apt)]; c=d[(d.arm==ctl)&(d.penalty_point==cpt)]
    if th: a=a[a.thinking==th]; c=c[c.thinking==th]
    assert not a.duplicated(['wording','seed']).any() and not c.duplicated(['wording','seed']).any()
    m=a.merge(c,on=['wording','seed'],suffixes=('_a','_c'))
    out={}
    for k in metrics:
        x=(m[k+'_a']-m[k+'_c']).dropna().values; n=len(x)
        bs=rng.choice(x,(20000,n)).mean(1)
        fl=rng.choice([-1,1],(200000,n)); p=(np.abs((fl*x).mean(1))>=abs(x.mean())-1e-12).mean()
        se=x.std(ddof=1)/np.sqrt(n)
        out[k]=(n,round(x.mean(),3),round(np.percentile(bs,2.5),3),round(np.percentile(bs,97.5),3),round(p,3),'MDE',round(2.8*se,3))
    return out,len(a),len(c)
def show(lbl,r):
    print('==',lbl,'arm n',r[1],'ctl n',r[2])
    for k,v in r[0].items(): print('   ',k,v)
show('oss cot-a',con(o,'d-cot-monitor-a',1,'headline-chat',1))
show('qwen t1 cot-a',con(q,'d-cot-monitor-a',1,'headline-chat',1,'on'))
show('qwen t1 cot-b',con(q,'d-cot-monitor-b',1,'headline-chat',1,'on',['price_index']))
show('oss r2s',con(o,'r2s-confidant',1,'headline-chat',1))
show('oss r4',con(o,'r4-announced',1,'headline-chat',1,None,['price_index']))
show('oss r2f',con(o,'r2f-confidant',1,'headline-chat',1,None,['price_index','profit_gain_index']))
show('oss wd increment',con(o,'wd-noncomp',1,'wd-ask-noreport',1))
show('oss wd-noncomp',con(o,'wd-noncomp',1,'headline-chat',1,None,['price_index','profit_gain_index']))
show('oss m-asym p3',con(o,'m-asym',3,'headline-chat',3))
show('oss m-asym vs p1 (wrong ctl)',con(o,'m-asym',3,'headline-chat',1,None,['price_index']))
show('oss hrep-fx vs hc',con(o,'hrep-fx-chat-p1',1,'headline-chat',1,None,['price_index']))
show('oss hrep-nx vs hc',con(o,'hrep-nx-chat-p1',1,'headline-chat',1,None,['price_index']))
for a in ['d-conflict','d-conflict-ethics','d-temptation-a','d-temptation-b','d-placebo']:
    s=o[o.arm==a].score_mean
    print('oss',a,'n',s.notna().sum(),'mean',round(s.mean(),3),'min',s.min(),'max',s.max(), 'share<=1.1', round((s<=1.1).mean(),2))
    for th in ['on','off']:
        s=q[(q.arm==a)&(q.thinking==th)].score_mean
        if len(s): print('   qwen',th,'n',s.notna().sum(),'mean',round(s.mean(),3),'min',s.min(),'max',s.max())
# control levels
for th in [None]:
    hc=o[(o.arm=='headline-chat')&(o.penalty_point==1)]
    print('oss hc p1 price_index', hc.price_index.mean().round(3), len(hc))
hq=q[(q.arm=='headline-chat')&(q.penalty_point==1)&(q.thinking=='on')]
print('qwen t1 hc p1 PI', hq.price_index.mean().round(3), 'matching', hq.matching_share.mean().round(3), 'comp', hq.competitive_share.mean().round(3))
# check control_row_id usage for cot
a=o[o.arm=='d-cot-monitor-a'][['wording','seed','control_row_id','control_basis']]; print(a.head(3).to_string())
print(o[o.arm=='m-asym'][['control_basis']].drop_duplicates())
