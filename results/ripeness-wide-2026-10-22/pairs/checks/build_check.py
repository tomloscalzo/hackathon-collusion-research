import json, re, sys
sys.path.insert(0, r'<local>\hackathon\work_scratch\wide\pairs_out')
from analysis_src import A
D = r'<local>\hackathon\work_scratch\wide\pairs_out'
T = json.load(open(D + r'\tables.json', encoding='utf8'))
log = open(D + r'\splits_log.txt', encoding='utf8').read()
lognums = set(re.findall(r'\d+\.\d+', log))
pairs = []
for k in T:
    p = k.split('__', 1)[1]
    if p not in pairs:
        pairs.append(p)
assert set(pairs) == set(A), (set(pairs) ^ set(A))
out = {p: A[p] for p in pairs}
json.dump(out, open(D + r'\analysis.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('pairs written', len(out))
allvals = set()
for k, v in T.items():
    for row in v['values']:
        for x in row:
            allvals.add('%.3f' % x)
for p in pairs:
    own = set()
    for kind in ('share', 'theta'):
        for row in T[kind + '__' + p]['values']:
            for x in row:
                own.add('%.3f' % x)
    levels = set(T['share__' + p]['row_levels'] + T['share__' + p]['col_levels'])
    for kind in ('share', 'theta'):
        txt = out[p][kind]
        ns = len(re.findall(r'[.!?](\s|$)', txt))
        miss = []
        for n in re.findall(r'(?<![\w.])\d+\.\d+', txt):
            n3 = n if len(n.split('.')[1]) == 3 else None
            if n3 and n3 in own:
                continue
            if n3 and n3 in lognums:
                continue
            if n3 and n3 in allvals:
                miss.append(n + '(other-table)')
                continue
            if not n3:
                continue  # level values / constants, checked by eye
            miss.append(n)
        print('%-22s %-5s sentences~%d words=%d %s' % (p, kind, ns, len(txt.split()), 'UNMATCHED:' + ','.join(miss) if miss else ''))
