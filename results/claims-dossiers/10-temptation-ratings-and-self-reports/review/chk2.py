import os
import pandas as pd
HK=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/')
d=pd.read_csv(HK+"oss_analysis/step1/final_t2/run.csv",low_memory=False); d=d[d.status=="done"]
x=d[d.arm.isin(["n3-ethics","n3-group","m-asym","headline-chat","wd-notice-only","wd-noncomp"])]
print(x.groupby(["arm","penalty_point","wording","claude_rating_id"]).claude_temptation.agg(["first","size"]).to_string())
q=pd.read_csv(HK+"analysis_final/steps/neutral/step1/run.csv",low_memory=False)
print(q.thinking.unique()[:5], q.status.unique())
qr=pd.read_csv(HK+"prompt_ratings/run_csv_rated/run.csv",low_memory=False)
print(qr.run.unique(), qr.claude_rating_id.notna().sum())
x=qr[qr.arm.isin(["n3-ethics","n3-group","m-asym"])&(qr.run=="neutral")]
print(x.groupby(["arm","wording","claude_rating_id"]).claude_temptation.agg(["first","size"]).to_string())
