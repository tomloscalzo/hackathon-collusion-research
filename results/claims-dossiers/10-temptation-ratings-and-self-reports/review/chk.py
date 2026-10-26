import os
import pandas as pd, numpy as np
HK=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/')
d=pd.read_csv(HK+"oss_analysis/step1/final_t2/run.csv",low_memory=False)
print(d.status.value_counts().to_dict())
d=d[d.status=="done"]
pr=pd.read_csv(HK+"prompt_ratings/prompt_ratings.csv")
j=d.merge(pr[["id","temptation_mean"]],left_on="claude_rating_id",right_on="id",how="left")
x=j[j.temptation_mean.notna()&j.claude_temptation.isna()]
print(len(x), x.arm.value_counts().to_dict(), x[["arm","penalty_point","wording","claude_rating_id","temptation_mean"]].drop_duplicates(["arm","wording"]).to_string())
print(j[j.claude_rating_id.isna()].arm.value_counts().to_dict())
print(d.claude_rating_id.notna().sum())
