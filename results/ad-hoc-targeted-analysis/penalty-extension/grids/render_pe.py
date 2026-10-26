import os as _os, pathlib as _pl; _ROOT = _os.environ.get("COLLUSION_WORK_ROOT") or next((str(q) for q in _pl.Path(__file__).resolve().parents if (q / "runs").is_dir()), "..")  # the work directory holding runs/ and work_scratch/
import csv, sys, subprocess, os, difflib, shutil
REPO=str(__import__('pathlib').Path(__file__).resolve().parents[4]).replace(chr(92),'/')+'/'  # the repository root
sys.path.insert(0, REPO+'tools/trial')
import mock_openai, make_grid
from mock_openai import MockOpenAI
REC=[]; orig=mock_openai.reply_for
def rec(body): REC.append(body); return orig(body)
mock_openai.reply_for=rec
S=_ROOT + '/work_scratch/penalty_ext/'; W=S+'mock/'; RD=S+'renders/'
FR=_ROOT + '/runs/2026-10-26_trackm_temptation_ethics/'
grid=[r for f in ('grid_o.csv','grid_ot.csv','grid_q.csv') for r in csv.DictReader(open(S+f,encoding='utf-8'))]
base=[r for r in csv.DictReader(open(_ROOT + '/runs/2026-10-26_trackm_oss_neutral/grid.csv',encoding='utf-8')) if r['trial_id'] in ('headline-chat__p5__w0__s118__t1',)]
base+=[r for r in csv.DictReader(open(_ROOT + '/runs/2026-10-25_trackm_neutral/grid.csv',encoding='utf-8')) if r['arm'] in ('headline-chat','ctl-32b-joint') and r['penalty_point'] in ('5','3') and r['thinking']=='1' and r['wording']=='0']
env=dict(os.environ,COLLUSION_VLLM_KEY='mockkey',PYTHONUTF8='1',COLLUSION_ALLOW_REMOTE='1',JAVA_HOME=os.environ.get('JAVA_HOME','')); env['PATH']=os.path.join(env['JAVA_HOME'],'bin')+os.pathsep+env['PATH']
JAR=REPO+'engine/target/collusion-engine.jar'; NL='\n'
def txt(m): return m['content'] if isinstance(m['content'],str) else ''.join(x.get('text','') for x in m['content'])
def render(row, tag):
    row=dict(row); row['pilot']=''; row={k:row.get(k,'') for k in make_grid.GRID_COLS}
    g=W+tag+'_grid.csv'
    with open(g,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=make_grid.GRID_COLS); w.writeheader(); w.writerow(row)
    shutil.rmtree(W+tag+'_trials',ignore_errors=True); REC.clear()
    with MockOpenAI() as m:
        cmd=[sys.executable,'-X','utf8',REPO+'tools/trial/run_grid.py','--grid',g,'--out',W+tag+'_trials','--config',FR+'cost.json','--max-concurrency','1','--jar',JAR,'--','python','-X','utf8','{trial_cmd}','--trial-dir','{trial_dir}','--jar','{jar}','--scenarios','{scenarios}','--base-url','qwen3_32b_fp8='+m.base_url,'--model','qwen3_32b_fp8=mockm','--base-url','gpt_oss_20b='+m.base_url,'--model','gpt_oss_20b=mockm','--api-key-env','COLLUSION_VLLM_KEY','--code-commit','abc1234','--budget-tokens','70000000','--allow-remote']
        p=subprocess.run(cmd,capture_output=True,text=True,env=env,cwd=REPO)
    systems=[]
    for b in REC:
        s=txt(b['messages'][0])
        if s not in systems: systems.append(s)
    q=[b for b in REC if 'Talk phase' not in txt(b['messages'][-1])]
    t=''.join('=== SYSTEM %d ===%s%s%s'%(i,NL,s,NL) for i,s in enumerate(systems))
    t+='=== USER (first quote call) ==='+NL+(txt(q[0]['messages'][-1]) if q else '(none)')+NL
    open(RD+tag+'.txt','w',encoding='utf-8').write(t)
    print(tag,row['trial_id'],'rc',p.returncode,len(REC),'requests',p.stderr[-400:] if p.returncode else '')
    return t
def pick(rows, arm, pt, prof):
    return [r for r in rows if r['arm']==arm and r['penalty_point']==pt and r['model_profile']==prof and r['wording']=='0'][0]
out={}
out['o_hc_p5']=render(pick(base,'headline-chat','5','gpt_oss_20b'),'o_hc_p5')
for p in ('4','25','100'): out['o_hc_p'+p]=render(pick(grid,'headline-chat',p,'gpt_oss_20b'),'o_hc_p'+p)
for a in ('ctl-32b-joint','m-inc-joint','m-inc-target'):
    for p in ('5','100'): out['o_%s_p%s'%(a,p)]=render(pick(grid,a,p,'gpt_oss_20b'),'o_%s_p%s'%(a,p))
out['q_hc_p5']=render(pick(base,'headline-chat','5','qwen3_32b_fp8'),'q_hc_p5')
out['q_hc_p25']=render(pick(grid,'headline-chat','25','qwen3_32b_fp8'),'q_hc_p25')
out['q_cj_p3']=render(pick(base,'ctl-32b-joint','3','qwen3_32b_fp8'),'q_cj_p3')
out['q_cj_p100']=render(pick(grid,'ctl-32b-joint','100','qwen3_32b_fp8'),'q_cj_p100')
pairs=[('o_hc_p5','o_hc_p4'),('o_hc_p5','o_hc_p25'),('o_hc_p5','o_hc_p100'),('o_ctl-32b-joint_p5','o_ctl-32b-joint_p100'),('o_m-inc-joint_p5','o_m-inc-joint_p100'),('o_m-inc-target_p5','o_m-inc-target_p100'),('o_ctl-32b-joint_p5','o_m-inc-joint_p5'),('q_hc_p5','q_hc_p25'),('q_cj_p3','q_cj_p100')]
for a,b in pairs:
    d=NL.join(difflib.unified_diff(out[a].splitlines(),out[b].splitlines(),a,b,n=0,lineterm=''))
    open(RD+'diff_%s__%s.txt'%(a,b),'w',encoding='utf-8').write(d)
    print('----- DIFF',a,b,'changed lines:',sum(1 for l in d.splitlines() if l[:1] in '+-' and l[:3] not in ('+++','---'))); print(d[:2500])
