import os
import pandas as pd
O=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv')
Q=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/analysis_final/steps/neutral/step1/run.csv')
for name,p in [("oss",O),("qwen",Q)]:
    d=pd.read_csv(p,low_memory=False)
    print(name,d.shape, d.run.unique()[:5])
    print(d.groupby(['run','status','in_primary']).size())
    arms=sorted(d.arm.dropna().unique()); print(len(arms)); print(arms)
    if 'thinking' in d: print(d.thinking.value_counts(dropna=False))
