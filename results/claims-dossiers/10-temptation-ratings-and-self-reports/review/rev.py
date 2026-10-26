import os, numpy as np, pandas as pd
os.environ["OMP_NUM_THREADS"]="2"
HK=os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/')
d=pd.read_csv(HK+"oss_analysis/step1/final_t2/run.csv",low_memory=False)
d=d[d.status=="done"]
pl=pd.read_csv(HK+"prompt_ratings/prompt_level_ratings.csv")
pr=pd.read_csv(HK+"prompt_ratings/prompt_ratings.csv")
print("run.csv rows done",len(d),"rated",d.claude_temptation.notna().sum())
print(d[d.claude_temptation.isna()].arm.value_counts().to_dict())
# own join: claude_rating_id -> prompt_ratings temptation_mean
j=d.merge(pr[["id","temptation_mean","conflict_mean"]].drop_duplicates("id"),left_on="claude_rating_id",right_on="id",how="left")
print("join match temptation:",np.nanmax(np.abs(j.temptation_mean-j.claude_temptation)), "n joined",j.temptation_mean.notna().sum())
# multi-seat check vs prompt_level
pp=pl.set_index("id").temptation_mean
pr["t_seat_avg"]=pr.apply(lambda r: np.nanmean([pp.get(x,np.nan) for x in [r.id,r.id_s2,r.id_s3] if isinstance(x,str)]),axis=1)
print("prompt_ratings temptation_mean vs seat avg of prompt_level:",np.nanmax(np.abs(pr.t_seat_avg-pr.temptation_mean)))
g=j[j.temptation_mean.notna() & ~j.arm.str.startswith("hrep")].copy()
g["T"]=g.temptation_mean
print("games",len(g))
g["cell"]=g.arm+"@p"+g.penalty_point.astype(str)
M=["price_index","competitive_share","matching_share","profit_gain_index","market_price_mean"]
c=g.groupby("cell").agg(T=("T","mean"),comm=("communication","first"),pen=("penalty_point","first"),firms=("firms","first"),arm=("arm","first"),**{m:(m,"mean") for m in M}).reset_index()
print("cells",len(c))
def sp(x,y):
    x=pd.Series(np.asarray(x,float)); y=pd.Series(np.asarray(y,float))
    return x.rank().corr(y.rank()), x.corr(y)
rng=np.random.default_rng(1)
def bootcell(df,x,y,nb=2000):
    s=[];p=[]
    n=len(df)
    for _ in range(nb):
        b=df.iloc[rng.integers(0,n,n)]
        if b[x].std()==0: continue
        a=sp(b[x],b[y]); s.append(a[0]); p.append(a[1])
    return np.percentile(s,[2.5,97.5]).round(2), np.percentile(p,[2.5,97.5]).round(2)
for m in M: print("cell",m,np.round(sp(c["T"],c[m]),3), bootcell(c,"T",m) if m=="price_index" else "")
print("game price",np.round(sp(g["T"],g.price_index),3))
# design residualisation at cell level
def resid(df,col,des):
    X=pd.get_dummies(df[des].astype(str),drop_first=True).astype(float); X.insert(0,"k",1.)
    b=np.linalg.lstsq(X.values,df[col].values.astype(float),rcond=None)[0]; return df[col].values-X.values@b
ctl=["ctl-32b-compete","ctl-32b-joint","m-inc-joint"]
c["ctl"]=c.arm.map(lambda a:"compete" if a=="ctl-32b-compete" else ("joint" if a in ctl else "none"))
for des in [["comm","pen","firms"],["comm","pen","firms","ctl"]]:
    rx=resid(c,"T",des); ry=resid(c,"price_index",des)
    cc=pd.DataFrame({"x":rx,"y":ry}); print("cell partial",des,np.round(sp(rx,ry),3),bootcell(cc,"x","y"))
# strata: same comm, pen, firms
for k,s in c.groupby(["comm","pen","firms"]):
    if len(s)>=5: print("stratum",k,len(s),np.round(sp(s["T"],s.price_index),3),"no-ctl:",np.round(sp(s[s.ctl=="none"]["T"],s[s.ctl=="none"].price_index),3) if (s.ctl=="none").sum()>=5 else "")
s=c[(c.comm=="private")&(c.pen==1)&(c.firms==2)]
s2=s[~s.arm.str.startswith("moral-prime")]
print("p1 private minus moral primes",len(s2),np.round(sp(s2["T"],s2.price_index),3), bootcell(s2,"T","price_index"))
s3=s2[s2.arm!="d-cot-monitor-a"]; print("also minus cot-monitor",len(s3),np.round(sp(s3["T"],s3.price_index),3))
nc=c[c.ctl=="none"]
for m in M[:3]: print("no ctl",m,np.round(sp(nc["T"],nc[m]),3))
# within-cell paraphrase test: wording-level demeaned within cell
w=g.groupby(["cell","wording"]).agg(T=("T","mean"),y=("price_index","mean")).reset_index()
w["Td"]=w["T"]-w.groupby("cell")["T"].transform("mean"); w["yd"]=w.y-w.groupby("cell").y.transform("mean")
w2=w[w.groupby("cell")["T"].transform("std")>0]
print("within-cell paraphrase: n texts",len(w2),"cells with rating variation",w2.cell.nunique(),"Td sd",w2.Td.std().round(3),np.round(sp(w2.Td,w2.yd),3))
# cluster boot within-cell
cells=w2.cell.unique(); ss=[];pp_=[]
for _ in range(2000):
    b=pd.concat([w2[w2.cell==k] for k in rng.choice(cells,len(cells))])
    a=sp(b.Td,b.yd); ss.append(a[0]); pp_.append(a[1])
print("  CI",np.percentile(ss,[2.5,97.5]).round(2),np.percentile(pp_,[2.5,97.5]).round(2))
# fraction of rating variance between strata
c["strat"]=c.comm+c.pen.astype(str)+c.firms.astype(str)
print("R2 of T on comm+pen+firms:",1-np.var(resid(c,"T",["comm","pen","firms"]))/np.var(c["T"]))
print("R2 of T on comm+pen+firms+ctl:",1-np.var(resid(c,"T",["comm","pen","firms","ctl"]))/np.var(c["T"]))
print(c.sort_values("T")[["cell","T","price_index","competitive_share"]].round(3).to_string())
# LOO design-model screen
def loo(df,des,y="price_index"):
    out=[]
    for i in range(len(df)):
        tr=df.drop(df.index[i]); X=pd.get_dummies(df[des].astype(str),drop_first=True).astype(float); X.insert(0,"k",1.)
        b=np.linalg.lstsq(X.drop(df.index[i]).values,tr[y].values,rcond=None)[0]; out.append(X.loc[df.index[i]].values@b)
    return np.array(out)
for des in [["comm","pen","firms"],["comm","pen","firms","ctl"]]:
    print("LOO design screen",des,np.round(sp(loo(c,des),c.price_index),3))
c["chat"]=(c.comm!="tacit").astype(int)
# rating + design: does rating add over design LOO?  
# Qwen t1 cell check
qr=pd.read_csv(HK+"prompt_ratings/run_csv_rated/run.csv",low_memory=False)
qr=qr[(qr.status=="done")&(qr.run=="neutral")][["row_id","claude_rating_id"]]
q=pd.read_csv(HK+"analysis_final/steps/neutral/step1/run.csv",low_memory=False); q=q[q.status=="done"]
q=q.merge(qr,on="row_id",how="left").merge(pr[["id","temptation_mean"]].drop_duplicates("id"),left_on="claude_rating_id",right_on="id",how="left")
for t in ["on","off"]:
    qq=q[(q.thinking==t)&q.temptation_mean.notna()].copy(); qq["cell"]=qq.arm+"@p"+qq.penalty_point.astype(str)
    qc=qq.groupby("cell").agg(T=("temptation_mean","mean"),y=("price_index","mean"),comm=("communication","first"),pen=("penalty_point","first"),firms=("firms","first"),arm=("arm","first"))
    print("qwen",t,len(qq),len(qc),np.round(sp(qc["T"],qc.y),3))
    qc=qc.reset_index(); qc["ctl"]=qc.arm.map(lambda a:"compete" if a=="ctl-32b-compete" else ("joint" if a in ctl else "none"))
    print("  partial design+ctl",np.round(sp(resid(qc,"T",["comm","pen","firms","ctl"]),resid(qc,"y",["comm","pen","firms","ctl"])),3))
    qq["Td"]=qq.temptation_mean; ww=qq.groupby(["cell","wording"]).agg(T=("Td","mean"),y=("price_index","mean")).reset_index()
    ww["Td"]=ww["T"]-ww.groupby("cell")["T"].transform("mean"); ww["yd"]=ww.y-ww.groupby("cell").y.transform("mean")
    print("  within-cell paraphrase",np.round(sp(ww.Td,ww.yd),3), len(ww))
dup=pr[pr.id.duplicated(keep=False)][["id","arms","penalty_point","temptation_mean","id_s2","id_s3"]]; print(dup.to_string())
