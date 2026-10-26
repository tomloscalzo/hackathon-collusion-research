import pandas as pd, numpy as np, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'analysis_style'))
import arm_labels  # shared glossary: legend tables of every slug or code shown under each figure and slug table
T='tables/'
def r(x,n=2): return '' if pd.isna(x) else f'{x:.{n}f}'
def ci(e,l,h,n=2): return f'{e:+.{n}f} ({l:+.{n}f} to {h:+.{n}f})'
def md(df): 
    return '| '+' | '.join(df.columns)+' |\n|'+'---|'*len(df.columns)+'\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in df.values)
# headline curve
a=pd.read_csv(T+'a_cells_vs_theory_and_bot.csv'); a=a[(a.run=='anchored')&(a.metric=='gain_all')&a.arm.isin(['headline-tacit','headline-chat','headline-monitored'])]
rows=[]
for (arm,pt),g in a.groupby(['arm','penalty_point']):
    d={'communication':{'headline-tacit':'no chat','headline-chat':'private chat','headline-monitored':'chat, regulator-read notice'}[arm],'penalty point':pt}
    for m in ['t0','t1']:
        x=g[g['mode']==m].iloc[0]; d['thinking '+('off' if m=='t0' else 'on')]=f'{x.est:.2f} ({x.lo:.2f} to {x.hi:.2f})'
    d['theory']=r(g.theory.iloc[0]); d['bot (t0)']=r(g[g['mode']=='t0'].bot.iloc[0]); rows.append(d)
curve=pd.DataFrame(rows); curve['o']=curve.communication.map({'no chat':0,'private chat':1,'chat, regulator-read notice':2}); curve=curve.sort_values(['o','penalty point']).drop(columns='o')
# communication contrasts (pooled)
c=pd.read_csv(T+'c_communication_contrasts.csv'); c=c[(c.run=='anchored')&(c.metric=='gain_all')&(c.penalty_point=='pooled')]
cc=pd.DataFrame([{ 'contrast':x.contrast,'thinking':x['mode'],'n pairs':x.n_pairs,'difference in profit gain index (95% CI)':ci(x.est,x.lo,x.hi)} for _,x in c.iterrows()])
# anchoring
an=pd.read_csv(T+'e_anchoring_neutral_minus_anchored.csv'); an=an[an.arm.isin(['headline-tacit','headline-chat','headline-monitored'])]
rows=[]
for (arm,m),g in an[an.metric=='gain_all'].groupby(['arm','mode']):
    rows.append({'communication':arm.replace('headline-',''),'thinking':'off' if m=='t0' else 'on','anchored mean (4 pts)':r(g.mean_anchored.mean()),'neutral mean (interim)':r(g.mean_neutral.mean()),'mean neutral minus anchored':r(g.est.mean()),'cells with CI above 0':f'{(g.lo>0).sum()} of {len(g)}'})
anc=pd.DataFrame(rows)
# levers
lv=pd.read_csv(T+'levers_anchored.csv'); lv=lv[lv.outcome=='price_index']
names={'tacit':'No chat vs private chat (p3)','monitored':'Chat with regulator-read notice vs private chat (p3)','p5':'Penalty point 5 vs 1 (private chat)','cot-a':'Idle reasoning-monitor threat A vs private chat (p1)','cot-b':'Idle reasoning-monitor threat B vs private chat (p1)','pub':'Published chat (p3)','mon0':'"Your chat is not monitored" (p3)','asym':'Ethics rule on one of two firms (p3)','n3eth':'Ethics rule on one of three firms vs 3-firm chat (p3)','5tick':'5-tick start rule (p3)','comp':'Compliance reminder (p3)','target':'Incentive text: reach a profit target (p3)','joint':'Incentive text: joint profit (p3)','n3':'Three firms vs two (p3)','cheater':'Planted cheater vs 3-firm chat (p3)'}
rows=[]
for _,x in lv.iterrows():
    if x.id not in names: continue
    rows.append({'lever':names[x.id],'thinking':'off' if x['mode']=='off' else 'on','status':'declared' if x.tier=='H' else 'exploratory','n pairs':x.n_pairs,'price index change (95% CI)':ci(x['diff'],x.ci_lo,x.ci_hi),'Holm p (exploratory family of 11)':'' if pd.isna(x.p_holm) else f'{x.p_holm:.3f}'})
lvt=pd.DataFrame(rows)
# dset / intro
g=pd.read_csv(T+'g_dset_behaviour.csv'); g=g[(g.run=='anchored')&(g.metric=='gain_all')]
h=pd.read_csv(T+'h_intro_behaviour.csv'); h=h[(h.run=='anchored')&(h.metric=='gain_all')]
dh=pd.concat([g,h]); dh=pd.DataFrame([{'arm':x.arm,'thinking':'off' if x['mode']=='t0' else 'on','n pairs':x.n_pairs,'profit gain index, arm minus private-chat control at p1 (95% CI)':ci(x.est,x.lo,x.hi),'arm mean':r(x.mean_arm) if 'mean_arm' in x else ''} for _,x in dh.iterrows()])
# design
da=pd.read_csv(T+'design_check_arms.csv')[['arm_family','arm','planned','done','never_started','truncation_rerun_counted','placeholder_replaced']]
# quote shares
q=pd.read_csv(T+'e_quote_shares_by_run.csv'); q=q[(q.group=='headline-all')]
def qs(run,m,mode): 
    x=q[(q.run==run)&(q.metric==m)&(q['mode']==mode)].iloc[0]; return f'{100*x.est:.0f}% ({100*x.lo:.0f} to {100*x.hi:.0f})'
qt=pd.DataFrame([{'quotes on':lab,'thinking':('off' if md_=='t0' else 'on'),'anchored run':qs('anchored',m,md_),'neutral run (interim)':qs('neutral',m2,md_)} for lab,m,m2 in [('2.09 (anchored example, theory level)','share_2.09','share_2.09'),('3.00','share_3.00','share_3.00'),('neutral example points other than 1.00','share_neutral_nofloor','share_neutral_nofloor'),('the 1.00 floor','share_floor','share_floor')] for md_ in ['t0','t1']])
# finalstats
f=pd.read_csv(T+'finalstats.csv'); f=f[(f.run=='anchored')&(f.metric=='gain_all')]
ft=pd.DataFrame([{'contrast':x.contrast,'n':x.n,'difference (95% CI)':ci(x['diff'],x.lo,x.hi),'sign-flip p':f'{x.p_signflip:.3f}','Holm p within its own list':f'{x.p_holm:.3f}','status':'declared metric, no declared test' if x.declared else 'exploratory'} for _,x in f.iterrows()])
S=open('report_template.txt',encoding='utf-8').read()
for k,v in dict(CURVE=md(curve),COMM=md(cc),ANCHOR=md(anc),QUOTES=md(qt),LEVERS=md(lvt),DSET=md(dh),DESIGN=md(da),FINALSTATS=md(ft)).items(): S=S.replace('@@'+k+'@@',v)
# legend tables generated from tools/analysis_style/arm_glossary.csv (never retyped):
# @@LEGEND_FIG:a;b@@ sits inside a figure's existing <small> Terms block; @@LEGEND_TAB:a;b@@ follows a slug table
def legend(kind, slugs):
    t = arm_labels.legend_table(slugs.split(';'))
    src = ' (from the shared glossary `tools/analysis_style/arm_glossary.csv`)'
    if kind == 'FIG': return '**Slugs and codes shown in this figure**' + src + '\n\n' + t
    return '<small>\n\n**Slugs and codes in the table above**' + src + '\n\n' + t + '\n</small>\n'
S = re.sub(r'@@LEGEND_(FIG|TAB):([^@]+)@@\n', lambda m: legend(m.group(1), m.group(2)), S)
# @@AXES:{json}@@ = one figure's legend grouped by axis (rows = y-axis, columns = x-axis, panels, colour metric),
# via arm_labels.axis_legend; "extra" adds sections for legend series, column groups or cell labels
import json
def axes(spec):
    d = json.loads(spec); extra = d.pop('extra', [])
    out = '**Codes on each axis of this figure** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)\n\n' + arm_labels.axis_legend(**d)
    for e in extra:
        out += '\n**' + e['title'] + '**\n\n' + arm_labels.legend_table(e['codes'])
    return out
S = re.sub(r'@@AXES:(\{.*?\})@@\n', lambda m: axes(m.group(1)), S)
assert '@@' not in S
open('REPORT.md','w',encoding='utf-8',newline='\n').write(S)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report('REPORT.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
