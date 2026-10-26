import os
import pandas as pd
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
o=pd.read_csv(O,low_memory=False); o=o[o.in_primary==1]
tc=[c for c in o.columns if any(s in c.lower() for s in ['time','date','wave','started','bug','replicate_of'])]
print(tc)
arms=['headline-chat','hrep-fx-chat-p1','hrep-nx-chat-p1','d-cot-monitor-a','r2s-confidant','r2f-confidant','wd-noncomp','d-placebo','r4-announced']
x=o[o.arm.isin(arms)&(o.penalty_point==1)]
for c in tc: print(c, x.groupby('arm')[c].agg(lambda s: str(sorted(map(str,s.dropna().unique()))[:2])[:120]).to_dict())
