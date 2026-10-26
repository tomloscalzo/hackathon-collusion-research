"""Anonymise rendered prompts: P001.. files, a private key, batches. Run after render_all.py."""
import json, glob, hashlib, random, os, re
import pandas as pd
import os
RUNS = os.environ['RUNS_DIR'].rstrip('/') + '/'   # folder holding the run roots
RUNLIST = ['2026-10-25_trackm_main', '2026-10-25_trackm_neutral', '2026-10-25_trackm_dset', '2026-10-25_trackm_condfix',
           '2026-10-25_trackm_newarms_A', '2026-10-25_trackm_newarms_drift', '2026-10-25_trackm_oss',
           '2026-10-25_trackm_watchdog', '2026-10-25_trackm_pilots']
KEY = ['penalty_point', 'scenario_file', 'communication', 'firms', 'seats', 'condition_texts', 'wording', 'options', 'payoff_examples']
rs = [json.load(open(f)) for f in sorted(glob.glob('raw/K*.json'))]
for r in rs:
    if r['row']['payoff_examples'] == '': r['row']['payoff_examples'] = 'anchored'
bad = [r['k'] for r in rs if not r['quote']]
print(len(rs), 'rendered; missing quote:', bad)
# thinking modes and arms per key over all grids
g = []
for r in RUNLIST:
    d = pd.read_csv(RUNS + r + '/grid.csv', dtype=str).fillna('')
    if 'payoff_examples' not in d: d['payoff_examples'] = ''
    d['payoff_examples'] = d['payoff_examples'].replace('', 'anchored'); d['run'] = r; g.append(d)
g = pd.concat(g)
g['kk'] = g[KEY].agg('\x1f'.join, axis=1)
modes = g.groupby('kk')['thinking'].apply(lambda s: '+'.join(sorted(set(s)))).to_dict()
arms = g.groupby('kk')['arm'].apply(lambda s: ';'.join(sorted(set(s)))).to_dict()
def strip(t):
    return re.sub(r'\r', '', t or '').strip()
def body(r):
    q = r['quote']; out = ['## SYSTEM PROMPT (price-quote call)\n', strip(q['system']), '\n## USER TURN (round 1, price-quote call)\n', strip(q['user'])]
    if r.get('talk'):
        out += ['\n## TALK-PHASE SYSTEM PROMPT\n', strip(r['talk']['system']), '\n## TALK-PHASE USER TURN (round 1)\n', strip(r['talk']['user'])]
    if r.get('question'):
        out += ['\n## POST-ROUND QUESTION CALL, SYSTEM PROMPT\n', strip(r['question']['system']), '\n## POST-ROUND QUESTION CALL, USER TURN\n', strip(r['question']['user'])]
    return '\n'.join(out) + '\n'
def body_of(q, tk, qq=None):
    return body({'quote': q, 'talk': tk, 'question': qq})
# persistent ids: existing prompt files keep their id (hash of the text after the header)
old = {}
for f in sorted(glob.glob('prompts/P*.txt')):
    t = open(f, encoding='utf-8').read().split(chr(10)*2, 1)[1]
    old[hashlib.sha256(t.encode()).hexdigest()] = os.path.basename(f)[:-4]
next_id = max([int(v[1:]) for v in old.values()] + [0]) + 1
os.makedirs('prompts', exist_ok=True)
newids = []
def pid_of(text):
    global next_id
    h = hashlib.sha256(text.encode()).hexdigest()
    if h not in old:
        pid = 'P%03d' % next_id; next_id += 1; old[h] = pid; newids.append(pid)
        open('prompts/%s.txt' % pid, 'w', encoding='utf-8', newline=chr(10)).write('# Prompt %s' % pid + chr(10)*2 + text)
    return old[h]
key = []
for r in rs:
    if not r['quote']: continue
    ids = [pid_of(body(r))]
    for sd in ('llm2', 'llm3'):
        o = (r.get('other_seats') or {}).get(sd)
        same = o and o['quote']['system'] == r['quote']['system'] and (o['talk'] or {}).get('system') == (r['talk'] or {}).get('system')
        ids.append(ids[0] if same else (pid_of(body_of(o['quote'], o['talk'])) if o else ''))
    kk = chr(31).join(r['row'][k] for k in KEY)
    key.append(dict(id=ids[0], id_s2=ids[1] or ids[0] if int(r['row']['firms']) >= 2 else '', id_s3=(ids[2] or ids[0]) if int(r['row']['firms']) >= 3 else '',
                    **{k: r['row'][k] for k in KEY}, arms=arms.get(kk, ''), thinking_modes=modes.get(kk, ''), first_run=r['row']['run']))
pd.DataFrame(key).to_csv('PRIVATE_key.csv', index=False)
print(len(key), 'keys;', len(set(old.values())), 'prompt texts; new:', newids)
# leakage check
pat = re.compile(r'headline|\bm-comp|n3-|trial|\barm\b|d-conflict|p[1-5]\b', re.I)
for f in glob.glob('prompts/*.txt'):
    t = open(f, encoding='utf-8').read()
    if pat.search(t): print('LEAK?', f, pat.search(t).group(0))
