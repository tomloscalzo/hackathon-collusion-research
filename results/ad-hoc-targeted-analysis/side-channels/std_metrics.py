"""Five standard metrics for each main contrast (paired on wording, seed; 95% percentile bootstrap over pairs)."""
import os, sys
import pandas as pd
REPO = os.environ.get("REPO_DIR")
sys.path.insert(0, os.path.join(REPO, "results", "oss", "ad-hoc", "_common"))
import oss_common as oc
OUT = os.path.dirname(os.path.abspath(__file__))
oss = oc.load_oss(); qw = oc.load_qwen(thinking="on")
C = [("oss: ethics rule on one firm (m-asym) minus headline chat, p3", oss, ("m-asym", 3), ("headline-chat", 3)),
     ("oss: reasoning-monitor threat A minus headline chat, p1", oss, ("d-cot-monitor-a", 1), ("headline-chat", 1)),
     ("oss: ethics rule under conflict prompt minus conflict prompt, p1", oss, ("d-conflict-ethics", 1), ("d-conflict", 1)),
     ("qwen t1: reasoning-monitor threat A minus headline chat, p1", qw, ("d-cot-monitor-a", 1), ("headline-chat", 1)),
     ("qwen t1: reasoning-monitor threat B minus headline chat, p1", qw, ("d-cot-monitor-b", 1), ("headline-chat", 1)),
     ("qwen t1: ethics rule on one firm (m-asym) minus headline chat, p3", qw, ("m-asym", 3), ("headline-chat", 3)),
     ("oss: no chat (tacit) minus headline chat, p1", oss, ("headline-tacit", 1), ("headline-chat", 1)),
     ("qwen t1: no chat (tacit) minus headline chat, p1", qw, ("headline-tacit", 1), ("headline-chat", 1))]
rows = []
for name, R, a, b in C:
    res = oc.paired(R, a, b)
    for col, lab, _ in oc.METRICS:
        r = res[col]; rows.append(dict(contrast=name, metric=lab, n_pairs=r["n_pairs"], treatment=r["mean_a"], control=r["mean_b"], diff=r["diff"], lo=r["lo"], hi=r["hi"]))
# agreement flags
for name, R, a, b in C[:6]:
    for col in ["explicit_agreement_flag", "explicit_agreement_any"]:
        ta = [float(x[col]) for x in R if x["arm"] == a[0] and str(x["penalty_point"]) == str(a[1]) and x[col] not in ("", None)]
        tb = [float(x[col]) for x in R if x["arm"] == b[0] and str(x["penalty_point"]) == str(b[1]) and x[col] not in ("", None)]
        rows.append(dict(contrast=name, metric=col, n_pairs=None, treatment=sum(ta)/len(ta), control=sum(tb)/len(tb), diff=sum(ta)/len(ta)-sum(tb)/len(tb), lo=None, hi=None))
df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, "standard_metrics.csv"), index=False)
print(df.round(3).to_string())
