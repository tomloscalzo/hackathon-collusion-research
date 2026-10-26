# Knife-edge check: cells counted as colluding (theta*>1e-9) with negligible theta* (<1e-3), by (delta, N, phi).
import pickle
from collections import defaultdict
G = pickle.load(open(r'<local>\hackathon\work_scratch\wide\pairs_out\grid.pkl', 'rb'))
LV, c, ts = G['LV'], G['cols'], G['ts']
d = defaultdict(lambda: [0, 0, 0])
tot = 0
for i in range(len(ts)):
    k = (LV['delta'][c['delta'][i]], LV['N'][c['N'][i]], LV['phi'][c['phi'][i]])
    d[k][0] += 1
    if ts[i] > 1e-9:
        d[k][1] += 1
        if ts[i] < 1e-3:
            d[k][2] += 1; tot += 1
print('total tiny-theta colluding cells', tot)
for k, v in sorted(d.items()):
    if v[2]:
        print(k, 'cells', v[0], 'share', round(v[1] / v[0], 3), 'tiny', v[2], 'share excl tiny', round((v[1] - v[2]) / v[0], 3))
