"""Review follow-ups: sign-flip p for the standard metrics; blind-reader random-item breakdown and bounds."""
import os, sys, random
import numpy as np, pandas as pd
REPO = os.environ["REPO_DIR"]
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
rng = np.random.default_rng(20261026); rows = []
for name, R, a, b in C:
    for col, lab, _ in oc.METRICS:
        A = {(r["wording"], r["seed"]): float(r[col]) for r in R if r["arm"] == a[0] and str(r["penalty_point"]) == str(a[1]) and r[col] not in ("", None)}
        B = {(r["wording"], r["seed"]): float(r[col]) for r in R if r["arm"] == b[0] and str(r["penalty_point"]) == str(b[1]) and r[col] not in ("", None)}
        d = np.array([A[k] - B[k] for k in sorted(set(A) & set(B))])
        obs = abs(d.mean()); sims = np.abs((d[None, :] * rng.choice([-1, 1], size=(20000, len(d)))).mean(1))
        rows.append(dict(contrast=name, metric=lab, n_pairs=len(d), diff=d.mean(), signflip_p=(1 + (sims >= obs - 1e-12).sum()) / 20001))
S = pd.read_csv(os.path.join(OUT, "standard_metrics.csv"))
P = pd.DataFrame(rows); S = S.merge(P[["contrast", "metric", "signflip_p"]], on=["contrast", "metric"], how="left")
S.to_csv(os.path.join(OUT, "standard_metrics.csv"), index=False); print(P.round(4).to_string())
B = pd.read_csv(os.path.join(OUT, "blind_merged.csv"))
print(pd.crosstab([B.stratum, B.model, B.arm], B.label1))
n = len(B); nr = (B.stratum == "random").sum()
print("one-sided 95% upper bound on ENCODED rate: all items", 1 - 0.05 ** (1 / n), " random items", 1 - 0.05 ** (1 / nr), n, nr)
K = pd.read_csv(os.path.join(OUT, "keyword_rates.csv")); print("max code rate", K.code.max(), K.loc[K.code.idxmax()].to_dict())
