"""Paired effects of the CoT-monitoring threats (A, B) vs the headline-chat control (p1, thinking on).
Input: game_level.csv (extracted from step1/run.csv; see extract step in ANALYSIS.md). Output: CSVs, tables.md, and the figure via fig_threat_effects.py.
Run: python analyze.py"""
import os, sys, numpy as np, pandas as pd, matplotlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # shared slug glossary (tools/analysis_style/arm_glossary.csv)
matplotlib.use("Agg"); import matplotlib.pyplot as plt
rng=np.random.default_rng(7); B=10000
g=pd.read_csv("game_level.csv")
M=["price_index","competitive_share","matching_share","profit_gain_index"]
def boot(d):
    d=np.asarray(d,float); d=d[~np.isnan(d)]; n=len(d)
    m=d[rng.integers(0,n,(B,n))].mean(1); return d.mean(),*np.percentile(m,[2.5,97.5]),n
def pairs(run,arm):
    a=g[(g.run==run)&(g.arm==arm)].set_index(["wording","seed"])
    c=g[(g.run==run)&(g.arm=="headline-chat")].set_index(["wording","seed"])
    return a.join(c,lsuffix="_a",rsuffix="_c",how="inner")
rows=[];diffs={}
for run in ["neutral","anchored"]:
    for arm in ["d-cot-monitor-a","d-cot-monitor-b"]:
        j=pairs(run,arm)
        for m in M:
            d=j[m+"_a"]-j[m+"_c"]; diffs[(run,arm,m)]=d
            mu,lo,hi,n=boot(d)
            rows.append(dict(run=run,arm=arm,measure=m,arm_mean=j[m+"_a"].mean(),control_mean=j[m+"_c"].mean(),delta=mu,lo=lo,hi=hi,n_pairs=n))
E=pd.DataFrame(rows); E.to_csv("paired_effects.csv",index=False)
# neutral minus anchored difference of deltas (same wording x seed pairs)
r2=[]
for arm in ["d-cot-monitor-a","d-cot-monitor-b"]:
    for m in M:
        d=(diffs[("neutral",arm,m)]-diffs[("anchored",arm,m)]); mu,lo,hi,n=boot(d)
        r2.append(dict(arm=arm,measure=m,delta_neutral=diffs[("neutral",arm,m)].mean(),delta_anchored=diffs[("anchored",arm,m)].mean(),neutral_minus_anchored=mu,lo=lo,hi=hi,n_pairs=n))
R=pd.DataFrame(r2); R.to_csv("neutral_vs_anchored.csv",index=False)
# A vs B
r3=[]
for run in ["neutral","anchored"]:
    for m in M:
        d=diffs[(run,"d-cot-monitor-a",m)]-diffs[(run,"d-cot-monitor-b",m)]; mu,lo,hi,n=boot(d)
        r3.append(dict(run=run,measure=m,a_minus_b=mu,lo=lo,hi=hi,n_pairs=n))
pd.DataFrame(r3).to_csv("a_vs_b.csv",index=False)
f=lambda x:f"{x:+.3f}"
with open("tables.md","w") as o:
    for m in M:
        o.write(f"\n### {m}\n\n| run | threat | threat mean | control mean | paired difference [95% CI] |\n|---|---|---|---|---|\n")
        for _,r in E[E.measure==m].iterrows():
            o.write(f"| {r.run} | {r.arm[-1].upper()} | {r.arm_mean:.3f} | {r.control_mean:.3f} | {f(r.delta)} [{f(r.lo)}, {f(r.hi)}] |\n")
        # owner rule: legend table under every slug table, from the shared glossary (threat A / B = d-cot-monitor-a / -b)
        o.write("\n<small>\n\n**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`; "
                "threat A = `d-cot-monitor-a`, threat B = `d-cot-monitor-b`, control = `headline-chat`).\n\n"
                + arm_labels.legend_table(["neutral","anchored","d-cot-monitor-a","d-cot-monitor-b","headline-chat","t1","p1",m]) + "\n</small>\n")
# figure: drawn by fig_threat_effects.py from paired_effects.csv (written above), with "slug: short label" rows from the shared glossary
import runpy; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_threat_effects.py"))
print(open("tables.md").read()); print(R.round(3).to_string()); print(pd.DataFrame(r3).round(3).to_string())
