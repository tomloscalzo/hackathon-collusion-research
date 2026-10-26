"""Build verdicts.csv from contrasts.csv (one tactic-level verdict, repeated on each model-mode x metric row),
and the model-difference test for the explicit-agreement flag (ethics rule, CoT threat).
Usage: python -X utf8 verdicts.py  (after oversight_contrasts.py)"""
import os
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
from pathlib import Path
import numpy as np, pandas as pd
OUT = Path(__file__).resolve().parents[1]
C = pd.read_csv(OUT / "contrasts.csv")
V = {"d-cot-monitor-a": "works on Qwen only (gpt-oss same direction on all five metrics, about half the size; nominal, fails Holm)",
     "d-cot-monitor-b": "untestable on gpt-oss (arm not run); works on Qwen thinking on (price index, Holm 0.048)",
     "headline-monitored": "untestable on gpt-oss (arm not run); null on Qwen in both modes",
     "wd-notice-only": "same null",
     "wd-noncomp": "same null",
     "wd-ask-noreport": "same null (Qwen thinking off nominal -0.21 price index, fails Holm)",
     "wd-noncomp vs wd-ask-noreport": "same null (the report threat adds nothing on either model)",
     "m-asym": "same null on prices; talk differs: gpt-oss says less (explicit-agreement flag -0.50), Qwen thinking on does not"}
C["verdict"] = C.slug.map(V)
C[["tactic", "slug", "description", "model_mode", "n_pairs", "metric", "effect", "ci_lo", "ci_hi", "p", "holm_p", "verdict"]].to_csv(
    OUT / "verdicts.csv", index=False, float_format="%.4f")
# model difference on the pre-declared explicit-agreement flag
HK = Path(os.environ.get("HACKATHON_DIR", Path.home() / "hackathon")); WS = HK / "work_scratch"
def load(p):
    d = pd.read_csv(p, low_memory=False); return d[(d.status == "done") & (d.in_primary == 1)]
o = load(WS / "oss_analysis/step1/final_t2/run.csv"); q = load(WS / "analysis_final/steps/neutral/step1/run.csv")
rng = np.random.default_rng(20261025); rows = []
def pd_(df, arm, pt, th=None):
    s = df if th is None else df[df.thinking == th]
    a = s[(s.arm == arm) & (s.penalty_point == pt)]; b = s[(s.arm == "headline-chat") & (s.penalty_point == pt)]
    m = a[["wording", "seed", "explicit_agreement_flag"]].merge(b[["wording", "seed", "explicit_agreement_flag"]], on=["wording", "seed"]).dropna()
    return (m.iloc[:, 2] - m.iloc[:, 3]).values
for arm, pt in (("m-asym", 3), ("d-cot-monitor-a", 1)):
    do, dq = pd_(o, arm, pt), pd_(q, arm, pt, "on")
    obs = do.mean() - dq.mean()
    bs = do[rng.integers(0, len(do), (10000, len(do)))].mean(1) - dq[rng.integers(0, len(dq), (10000, len(dq)))].mean(1)
    allv = np.concatenate([do, dq]); R = 20000
    cnt = sum(abs((pm := rng.permutation(allv))[:len(do)].mean() - pm[len(do):].mean()) >= abs(obs) - 1e-12 for _ in range(R))
    rows.append(dict(slug=arm, measure="explicit_agreement_flag", effect_oss=do.mean(), effect_qwen_on=dq.mean(), difference=obs,
                     ci_lo=np.percentile(bs, 2.5), ci_hi=np.percentile(bs, 97.5), p=(cnt + 1) / (R + 1), n_oss=len(do), n_qwen=len(dq)))
pd.DataFrame(rows).to_csv(OUT / "model_difference_talk.csv", index=False, float_format="%.4f"); print(pd.DataFrame(rows).round(3))
