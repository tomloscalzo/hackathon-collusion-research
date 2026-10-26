import os
import pandas as pd, numpy as np
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
o=pd.read_csv(O,low_memory=False); o=o[o.in_primary==1]
f=o[o.supersession=='original_kept_flagged']
print(f.supersession_description.iloc[0]); print(f.supersession_reason.value_counts().to_dict())
print(f.groupby('arm').size().to_dict())
ok=o[o.supersession!='original_kept_flagged']
for arm,ctl in [('d-cot-monitor-a','headline-chat'),('r2s-confidant','headline-chat'),('wd-noncomp','wd-ask-noreport')]:
    a=ok[(ok.arm==arm)&(ok.penalty_point==1)]; c=ok[(ok.arm==ctl)&(ok.penalty_point==1)]
    m=a.merge(c,on=['wording','seed']); d=(m.price_index_x-m.price_index_y)
    print(arm,'excl flagged n',len(d),round(d.mean(),3))
