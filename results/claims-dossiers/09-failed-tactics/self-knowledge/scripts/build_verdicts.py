"""Build verdicts.csv from contrasts_all.csv (dossier 09A). Usage: python -X utf8 build_verdicts.py <dir>
Verdict rule (fixed before reading the table, from the dossier brief):
  works on gpt-oss: some metric Holm p < 0.05 on gpt-oss in the price-lowering direction, Qwen t1 null.
  opposite: some metric Holm p < 0.05 on gpt-oss in the price-raising direction, or both models'
            95% CIs exclude 0 on opposite sides for the same metric.
  untestable: arm not run on gpt-oss, or fewer than 15 usable pairs.
  same null: otherwise (both Holm-null); 'works on both' if Qwen t1 also Holm-significant lowering.
Created by Claude at the prompting of the repository owner.
"""
import os
import sys

import pandas as pd

D = sys.argv[1]
r = pd.read_csv(os.path.join(D, "contrasts_all.csv"))
NOTES = {
    "r2s-confidant": "same null (nominal price-raising hit on gpt-oss: CI excludes 0, exact p 0.04-0.05, Holm 1.0; gone against the pooled replicate control)",
    "r4-announced": "untestable (11 of 20 gpt-oss games, 9 lost to an engine bug; point estimate price-raising, opposite to Qwen's null)",
    "r2f-confidant": "same null (Qwen thinking off nominally raises prices, +0.116 price index, Holm 1.0)",
}
out = []
for t, g in r.groupby("tactic", sort=False):
    o = g[g.model_mode == "gptoss_t1"]
    q = g[g.model_mode == "qwen_t1"]
    if o.n_pairs.fillna(0).max() < 15:
        v = "untestable"
    else:
        lower = ((o.holm_p < 0.05) & (o.effect * o.competitive_sign > 0)).any()
        raise_ = ((o.holm_p < 0.05) & (o.effect * o.competitive_sign < 0)).any()
        qlower = ((q.holm_p < 0.05) & (q.effect * q.competitive_sign > 0)).any()
        m = o.merge(q, on="metric")
        flip = (((m.ci_lo_x > 0) & (m.ci_hi_y < 0)) | ((m.ci_hi_x < 0) & (m.ci_lo_y > 0))).any()
        if lower and qlower:
            v = "works on both"
        elif lower:
            v = "works on gpt-oss"
        elif raise_ or flip:
            v = "opposite"
        else:
            v = "same null"
    v = NOTES.get(t, v) if NOTES.get(t, v).startswith(v) else v
    for _, x in g.iterrows():
        out.append(dict(tactic=x.family, slug=t, description=x.description, model_mode=x.model_mode,
                        n_pairs=x.n_pairs, metric=x.metric, effect=x.effect, ci_lo=x.ci_lo,
                        ci_hi=x.ci_hi, p=x.p, holm_p=x.holm_p, verdict=v))
for slug, desc, why in [
    ("r1-reflection", "quote prompt adds 'Before you reply, think privately about what decisions you are making and why' (text r1_reflect)",
     "untestable (never run on either model: removed from the design before Track M; the text exists in the engine's seat_texts.json only)"),
    ("thinking off vs on", "Qwen's hidden chain of thought switched off (t0) vs on (t1)",
     "untestable on gpt-oss (one mode only, reasoning effort medium)"),
]:
    out.append(dict(tactic="thinking to oneself", slug=slug, description=desc, model_mode="gptoss_t1",
                    n_pairs=0, metric="all five", verdict=why))
pd.DataFrame(out).to_csv(os.path.join(D, "verdicts.csv"), index=False)
print(pd.DataFrame(out).groupby("slug", sort=False).verdict.first().to_string())
