import csv, collections, random, statistics as st
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
R=(_HK + "/work_scratch/oss_analysis/")
OUT=(_REPO + "/results/oss/ad-hoc/cheater/")
run=[r for r in csv.DictReader(open(R+"step1/final_t2/run.csv",encoding="utf-8")) if r["status"]=="done" and r["in_primary"]=="1"]
ch={r["trial_id"]:r for r in run if r["arm"]=="n3-cheater"}
gr={r["trial_id"]:r for r in run if r["arm"]=="n3-group"}
rd=collections.defaultdict(lambda: collections.defaultdict(dict))
for x in csv.DictReader(open(R+"tables_t2/rounds.csv",encoding="utf-8")):
    t=x["trial_id"]
    if t in ch or t in gr:
        try: rd[t][int(x["round"])][x["seat"]]=(float(x["quote"]),float(x["market_price"]))
        except: pass
def win(t,dr,lo,hi,llm=True):
    v=[]
    for k in range(lo,hi+1):
        d=rd[t].get(dr+k)
        if not d: continue
        if llm: v+= [q for s,(q,m) in d.items() if s in("llm1","llm2")]
        else: v.append(list(d.values())[0][1])
    return sum(v)/len(v) if v else None
rows=[]
for lab,lo,hi in(("pre (k -3..-1)",-3,-1),("defect round (k 0)",0,0),("post 1-3",1,3),("post 4-8",4,8)):
    q=[];m=[]
    for t,r in ch.items():
        if not r["defect_round"]: continue
        dr=int(r["defect_round"])
        a=win(t,dr,lo,hi); b=win(t,dr,lo,hi,False)
        if a is not None: q.append(a)
        if b is not None: m.append(b)
    rows.append([lab,len(q),sum(q)/len(q),len(m),sum(m)/len(m)])
    print(rows[-1])
with open(OUT+"event_time_gptoss.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["window","n_games_llm_quote","mean_llm_quote","n_games_market","mean_market_price"])
    for r in rows: w.writerow([r[0],r[1],round(r[2],3),r[3],round(r[4],3)])
lags=[int(r["punish_lag"]) for r in ch.values() if r["punish_lag"]!=""]
dg=[r for r in ch.values() if r["defect_round"]]
print("defect games",len(dg),"lag<=3",sum(1 for l in lags if l<=3),"lags",sorted(lags),"median",st.median(lags),"coalition_punished",sum(1 for r in dg if r["coalition_punished"]=="1"))
