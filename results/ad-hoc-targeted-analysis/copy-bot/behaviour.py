import csv, random, statistics as st
R=list(csv.DictReader(open('copybot_llm_games.csv')))
def path(x): return [float(v) for v in x['q_path'].split()]
def dif(x): p=path(x); return [p[i]-p[i-1] for i in range(1,len(p))]
out=[]
groups=sorted({x['group'] for x in R})
for g in groups:
  for th in '01':
    v=[x for x in R if x['group']==g and x['thinking']==th]; n=len(v)
    f=lambda c: round(sum(any(c(d) for d in dif(x)) for x in v)/n,2)
    out.append(dict(group=g,thinking=th,seat_games=n,any_raise_ge5c=f(lambda d:d>=0.05),any_cut=f(lambda d:d<=-0.005),any_1_2c_undercut=f(lambda d:-0.0201<=d<=-0.005),any_cut_ge30c=f(lambda d:d<=-0.30),
      q1_eq_250=round(sum(abs(float(x['q1'])-2.5)<.005 for x in v)/n,2),q1_eq_150=round(sum(abs(float(x['q1'])-1.5)<.005 for x in v)/n,2),q1_eq_100=round(sum(abs(float(x['q1'])-1)<.005 for x in v)/n,2),
      mean_q1=round(st.mean(float(x['q1']) for x in v),3),
      frozen_whole_game=round(sum(x['frozen']=='1' for x in v)/n,2),mean_final=round(st.mean(float(x['q_last']) for x in v),3)))
for o in out: print(o)
w=csv.DictWriter(open('copybot_behaviour.csv','w',newline=''),fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
random.seed(1)
res=[]
for g in groups:
  if g.startswith('head'): continue
  for th in '01':
    a=[float(x['price_index']) for x in R if x['group']==g and x['thinking']==th]
    h={x['trial']:float(x['price_index']) for x in R if x['group'].startswith('head') and x['thinking']==th}
    b=list(h.values()); d=st.mean(a)-st.mean(b); pool=a+b; c=0
    for _ in range(20000):
        random.shuffle(pool); c+= abs(st.mean(pool[:len(a)])-st.mean(pool[len(a):]))>=abs(d)
    res.append(dict(group=g,thinking=th,n_copy=len(a),price_index_copy=round(st.mean(a),3),n_headline=len(b),price_index_headline=round(st.mean(b),3),diff=round(d,3),perm_p=c/20000)); print(res[-1])
w=csv.DictWriter(open('copybot_vs_headline_tests.csv','w',newline=''),fieldnames=list(res[0])); w.writeheader(); w.writerows(res)
