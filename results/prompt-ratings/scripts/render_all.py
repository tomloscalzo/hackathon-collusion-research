"""Render the first-round prompts of every unique text-changing grid combination against a local mock (no GPU, no network)."""
import json, os, sys, subprocess, threading, hashlib, time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pandas as pd
import os
REPO = os.environ.get('REPO', '.')   # a checkout of the repository
RUNS = os.environ['RUNS_DIR'].rstrip('/') + '/'   # folder holding the run roots
OUT = os.environ.get('OUT_DIR', 'raw').rstrip('/') + '/'
sys.path.insert(0, REPO + '/tools/trial')
import mock_openai
RUNLIST = ['2026-10-25_trackm_main', '2026-10-25_trackm_neutral', '2026-10-25_trackm_dset', '2026-10-25_trackm_condfix',
           '2026-10-25_trackm_newarms_A', '2026-10-25_trackm_newarms_drift', '2026-10-25_trackm_oss',
           '2026-10-25_trackm_watchdog', '2026-10-25_trackm_pilots']
KEY = ['penalty_point', 'scenario_file', 'communication', 'firms', 'seats', 'condition_texts', 'wording', 'options', 'payoff_examples']
os.makedirs(OUT, exist_ok=True)
rows = []
for r in RUNLIST:
    d = pd.read_csv(RUNS + r + '/grid.csv', dtype=str).fillna('')
    d['run'] = r
    if 'payoff_examples' not in d: d['payoff_examples'] = ''
    d['payoff_examples'] = d['payoff_examples'].replace('', 'anchored')
    rows.append(d)
d = pd.concat(rows)
d = d.sort_values(['thinking']).drop_duplicates(KEY)   # prefer thinking 0
d = d.reset_index(drop=True)
print(len(d), 'unique combos', flush=True)

def txt(m):
    c = m['content']
    return c if isinstance(c, str) else ''.join(x.get('text', '') for x in c)

class Srv:
    def __init__(self):
        self.rec = []
        outer = self
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                n = int(self.headers.get('Content-Length') or 0)
                body = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
                outer.rec.append(body)
                content, reasoning = mock_openai.reply_for(body)
                msg = {'role': 'assistant', 'content': content}
                out = json.dumps({'id': 'm', 'object': 'chat.completion', 'choices': [{'index': 0, 'finish_reason': 'stop', 'message': msg}],
                                  'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out))); self.end_headers(); self.wfile.write(out)
        class S(ThreadingHTTPServer):
            def handle_error(self, *a): pass
        self.s = S(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:%d' % self.s.server_address[1]
        threading.Thread(target=self.s.serve_forever, daemon=True).start()
    def close(self): self.s.shutdown(); self.s.server_close()

env = dict(os.environ, COLLUSION_VLLM_KEY='mockkey', PYTHONUTF8='1', COLLUSION_ALLOW_REMOTE='1')
def one(i):
    if os.path.exists(OUT + 'K%03d.json' % i): return 'skip', 0, True
    row = d.iloc[i].to_dict()
    pid = 'K%03d' % i
    td = OUT + 'trials/' + pid
    os.makedirs(td, exist_ok=True)
    row['payoff_examples'] = '' if row['payoff_examples'] == 'anchored' else row['payoff_examples']
    row['thinking'] = '0'
    json.dump(row, open(td + '/grid_row.json', 'w'))
    s = Srv()
    jar = RUNS + row['run'] + '/collusion-engine.jar'
    cmd = [sys.executable, '-X', 'utf8', REPO + '/tools/trial/trial_cmd.py', '--trial-dir', td, '--jar', jar, '--scenarios', REPO + '/engine/src/main/resources/scenarios', '--base-url', s.url,
           '--model', 'mockm', '--api-key-env', 'COLLUSION_VLLM_KEY', '--code-commit', 'abc1234', '--budget-tokens', '70000000', '--allow-remote']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    t0 = time.time()
    while proc.poll() is None and time.time() - t0 < 400:
        time.sleep(0.3)
        us = [str(b.get('user', '')) for b in list(s.rec)]
        hq = any(u.startswith('game|') and '|llm1|' in u and '|r1|' in u for u in us)
        ht = any(u.startswith('talk|') and '|llm1|' in u and '|r1|' in u for u in us)
        hqq = any(u.startswith('question|') for u in us)
        if hq and (ht or row['communication'] == 'tacit') and (hqq or not ('"question"' in row['options'] and 'fed' in row['options'])):
            break
    if proc.poll() is None:
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
        p = None
        proc.wait()
    else:
        p = proc
        p.stderr = ''; p.stdout = proc.stdout.read()
    rec = s.rec
    s.close()
    res = {'k': pid, 'row': {k: row[k] for k in KEY + ['run', 'arm']}, 'rc': 0 if p is None else p.returncode, 'n_req': len(rec)}
    def first(prefix):
        for b in rec:
            u = str(b.get('user', ''))
            if u.startswith(prefix) and '|llm1|' in u and '|r1|' in u:
                ms = b['messages']
                return {'system': txt(ms[0]) if ms[0]['role'] == 'system' else '', 'user': txt(ms[-1]),
                        'schema': ((b.get('response_format') or {}).get('json_schema') or {}).get('schema')}
        return None
    res['quote'] = first('game|'); res['talk'] = first('talk|')
    qs = [b for b in rec if str(b.get('user', '')).startswith('question|')]
    if qs:
        ms = qs[0]['messages']; res['question'] = {'system': txt(ms[0]), 'user': txt(ms[-1])}
    if p is not None and p.returncode:
        res['err'] = (p.stderr or p.stdout)[-500:]
    json.dump(res, open(OUT + pid + '.json', 'w'))
    return pid, res['rc'], res['quote'] is not None
t = time.time()
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(one, range(len(d))):
        if r[1] != 0 or not r[2]: print('PROBLEM', r, flush=True)
d.to_csv(OUT + 'combos.csv', index=False)
print('done', time.time() - t)
