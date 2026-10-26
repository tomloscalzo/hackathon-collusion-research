"""Usage: python q.py ROWVAR COLVAR STAT [var=level ...]
STAT: share | theta | thetap (theta given participation, among theta*>0) | that (theta_hat>0 share) | reg:NAME | w0pos
Filters: var=level or var=lv1,lv2 (level values as in LV)."""
import pickle, sys
G = pickle.load(open(r'<local>\hackathon\work_scratch\wide\pairs_out\grid.pkl', 'rb'))
LV, cols = G['LV'], G['cols']
rv, cv, stat = sys.argv[1], sys.argv[2], sys.argv[3]
filt = {}
for a in sys.argv[4:]:
    k, v = a.split('=')
    filt[k] = {LV[k].index(float(x)) for x in v.split(',')}
n = len(G['ts'])
R = cols[rv] if rv != '-' else None
C = cols[cv] if cv != '-' else None
nr = len(LV[rv]) if R else 1
nc = len(LV[cv]) if C else 1
num = [[0.0] * nc for _ in range(nr)]
den = [[0] * nc for _ in range(nr)]
ts, th, w0, reg = G['ts'], G['th'], G['w0'], G['reg']
RC = G['RC']
fl = [(cols[k], s) for k, s in filt.items()]
for i in range(n):
    ok = True
    for c, s in fl:
        if c[i] not in s:
            ok = False
            break
    if not ok:
        continue
    a = R[i] if R else 0
    b = C[i] if C else 0
    t = ts[i]
    if stat == 'share':
        x = 1.0 if t > 1e-9 else 0.0
    elif stat == 'theta':
        x = t
    elif stat == 'thetap':
        if t <= 1e-9:
            continue
        x = t
    elif stat == 'that':
        x = 1.0 if th[i] > 1e-9 else 0.0
    elif stat == 'w0pos':
        x = 1.0 if w0[i] > 1e-9 else 0.0
    elif stat.startswith('reg:'):
        x = 1.0 if reg[i] == RC[stat[4:]] else 0.0
    num[a][b] += x
    den[a][b] += 1
print('#', ' '.join(sys.argv[1:]))
print('%-10s' % (rv + '\\' + cv), ' '.join('%7s' % v for v in (LV[cv] if C else ['all'])))
for a in range(nr):
    print('%-10s' % (LV[rv][a] if R else 'all'), ' '.join('%7.3f' % (num[a][b] / den[a][b]) if den[a][b] else '    nan' for b in range(nc)))
