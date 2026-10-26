"""Extract firm-round table from raw events.jsonl of a run. usage: extract.py <trials_dir> <label>"""
import json, sys, os, re, glob
import pandas as pd
# gpt-oss adaptation: argv[1] is a folder of <arm>/<trial> game folders (a collect view or a root's trials folder); outputs go to the cwd.
run, label = sys.argv[1], sys.argv[2]
rows = []; texts = []
for tdir in sorted(glob.glob(os.path.join(run, '*', '*'))):
    if not os.path.exists(os.path.join(tdir, 'DONE')): continue
    tid = os.path.basename(tdir); arm = os.path.basename(os.path.dirname(tdir))
    mode = 'think' if tid.endswith('t1') else 'nothink'
    P = json.load(open(os.path.join(tdir, 'params.json'), encoding='utf8'))
    mk = P['market']['scenario']['market']; fine = P['market']['scenario']['enforcement']['fine']
    quotes = {}; market = {}; printed = None; llm = set()
    for l in open(os.path.join(tdir, 'events.jsonl'), encoding='utf8'):
        e = json.loads(l)
        if e['kind'] == 'quote':
            llm.add(e['seat'])
            if printed is None:
                s = e['prompt']; i = s.find('Profit per round'); j = s.find('How the other')
                seg = s[i:j]
                printed = sorted({float(x) for x in re.findall(r'(\d+\.\d\d)', seg)} - {0.0})
                printed = [x for x in printed if 1.0 <= x <= 5.0]
            texts.append(dict(trial=tid, arm=arm, mode=mode, round=e['round'], seat=e['seat'], quote=e.get('quote'),
                reasoning=e.get('reasoning') or '', reply=e.get('reply') or ''))
        elif e['kind'] == 'market':
            market[e['round']] = e
    for r, m in market.items():
        for seat, q in m['prices'].items():
            rows.append(dict(run=label, trial=tid, arm=arm, mode=mode, round=r, seat=seat, quote=q,
                profit=m['profits'].get(seat), is_llm=seat in llm, n=mk['n'], phi=mk['phi'], fine=fine,
                printed=json.dumps(printed)))
pd.DataFrame(rows).to_csv(f'fr_{label}.csv', index=False)
pd.DataFrame(texts).to_json(f'texts_{label}.jsonl', orient='records', lines=True, force_ascii=False)
print(label, len(rows), len(texts))
