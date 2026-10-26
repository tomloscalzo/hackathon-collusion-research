import os
import pandas as pd, numpy as np
OS=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/')
o=pd.read_csv(OS+'step1/final_t2/run.csv',low_memory=False); o=o[o.in_primary==1]
ro=pd.read_csv(OS+'tables_t2/rounds.csv',usecols=['trial_id','round','market_price'])
ev=pd.read_csv(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/claims_dossiers/11-fresh-discovery/rounds_oss.csv'))
t2=ro.groupby(['trial_id','round']).market_price.first().groupby('trial_id').agg(['mean','size'])
e=ev.groupby('row_id').market_price.agg(['mean','size'])
x=o.set_index('row_id')[['trial_id','played_trial_id','arm','source_root','market_price_mean','rounds_played']].join(e.rename(columns={'mean':'ev','size':'ev_n'}))
x=x.join(t2.rename(columns={'mean':'t2','size':'t2_n'}),on='trial_id')
x['bad_t2']=(x.t2-x.market_price_mean).abs()>0.01; x['bad_ev']=(x.ev-x.market_price_mean).abs()>0.01
print(x.groupby('source_root')[['bad_t2','bad_ev']].mean())
print(x[x.bad_t2].arm.value_counts().head(20))
print((x.trial_id!=x.played_trial_id).groupby(x.bad_t2).mean())
print(x[x.bad_t2][['trial_id','played_trial_id','market_price_mean','ev','t2','rounds_played','t2_n']].head())
print('t2 has ids like', [i for i in t2.index if i.startswith(('fx','nx'))][:3], sum(i.startswith(('fx','nx')) for i in t2.index))
