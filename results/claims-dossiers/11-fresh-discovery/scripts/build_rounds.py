"""Build an independent round-level table for gpt-oss-20b from the raw game logs.

One row per (game, round): each seat's quote, the market price (best quote), profits.
Reads the counted game of every primary run.csv row (source_root + played_trial_id),
which avoids the trial-id collision between the formula-fix games and the build-bug
replicates. Qwen3-32B rounds come from its own Step 1 rounds table (no collision there).
Usage: build_rounds.py <runs_dir> <oss_run_csv> <qwen_run_csv> <qwen_rounds_csv> <out_dir>
"""
import json, sys, os, glob
import pandas as pd

runs, oss_run, q_run, q_rounds, out = sys.argv[1:6]
d = pd.read_csv(oss_run, low_memory=False)
d = d[d.in_primary == 1]
rows = []
for _, g in d.iterrows():
    arm_dir = g.played_trial_id.split('__')[0]
    f = os.path.join(runs, g.source_root, 'trials', arm_dir, g.played_trial_id, 'events.jsonl')
    if not os.path.exists(f):
        hits = glob.glob(os.path.join(runs, g.source_root, 'trials', '*', g.played_trial_id, 'events.jsonl'))
        f = hits[0]
    seen = set()
    for line in open(f, encoding='utf8'):
        e = json.loads(line)
        if e.get('kind') != 'market' or e['round'] in seen:
            continue
        seen.add(e['round'])
        pr = e['prices']
        llm = {k: v for k, v in pr.items() if k.startswith('llm')}
        rows.append(dict(model='gpt-oss-20b', row_id=g.row_id, arm=g.arm, round=e['round'],
                         market_price=e['market_price'], n_seats=len(pr),
                         q1=llm.get('llm1'), q2=llm.get('llm2'), q3=llm.get('llm3'),
                         other=pr.get('cheater'),
                         profit_sum=sum(e['profits'].values())))
oss = pd.DataFrame(rows)
oss.to_csv(os.path.join(out, 'rounds_oss.csv'), index=False)

q = pd.read_csv(q_run, low_memory=False)
q = q[q.in_primary == 1]
qr = pd.read_csv(q_rounds, usecols=['trial_id', 'round', 'seat', 'quote', 'market_price'])
qr = qr[qr.trial_id.isin(q.played_trial_id)]
w = qr.pivot_table(index=['trial_id', 'round'], columns='seat', values='quote', aggfunc='first').reset_index()
mp = qr.groupby(['trial_id', 'round']).market_price.first().reset_index()
w = w.merge(mp, on=['trial_id', 'round'])
w = w.merge(q[['played_trial_id', 'row_id', 'arm']], left_on='trial_id', right_on='played_trial_id')
w = w.rename(columns={'llm1': 'q1', 'llm2': 'q2', 'llm3': 'q3'})
w['model'] = 'qwen3-32b'
cols = ['model', 'row_id', 'arm', 'round', 'market_price', 'q1', 'q2'] + (['q3'] if 'q3' in w else [])
w[cols].to_csv(os.path.join(out, 'rounds_qwen.csv'), index=False)
print(len(oss), oss.row_id.nunique(), len(w), w.row_id.nunique())
