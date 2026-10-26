# Tick-0 participation rule check: with tick=0 and rhoTip=0, collusion (theta*>0) should occur iff IC is feasible
# (theta_hat>0) and K = slope*pEv*fineRatio*(sBar-1) < 4.  Also: decomposition of high-fine collusion.
import pickle
from collections import defaultdict
G = pickle.load(open(r'<local>\hackathon\work_scratch\wide\pairs_out\grid.pkl', 'rb'))
LV, c = G['LV'], G['cols']
ts, th = G['ts'], G['th']
n = len(ts)
agree = dis = 0
ex = []
fine500 = defaultdict(lambda: [0, 0])
floor = defaultdict(lambda: [0, 0])
for i in range(n):
    tick = LV['tick'][c['tick'][i]]; rt = LV['rhoTip'][c['rhoTip'][i]]; sl = LV['slope'][c['slope'][i]]
    fr = LV['fineRatio'][c['fineRatio'][i]]; pe = LV['pEvidence'][c['pEvidence'][i]]; sb = LV['sBarRatio'][c['sBarRatio'][i]]
    col = ts[i] > 1e-9
    if tick == 0 and rt == 0:
        K = sl * pe * fr * (sb - 1)
        if abs(K - 4) < 1e-9:
            continue
        pred = th[i] > 1e-9 and K < 4
        if pred == col: agree += 1
        else:
            dis += 1
            if len(ex) < 5: ex.append((i, K, th[i], ts[i]))
    if fr == 500.0:
        key = 'noHazard(slope0,tip0)' if (sl == 0 and rt == 0) else 'other'
        fine500[key][0] += 1; fine500[key][1] += col
    if fr >= 250 and pe == 1.0:
        key = ('noHazard' if (sl == 0 and rt == 0) else 'other', tick)
        floor[key][0] += 1; floor[key][1] += col
print('K-rule (tick=0, rhoTip=0): agree', agree, 'disagree', dis, ex)
tot = sum(v[1] for v in fine500.values())
for k, v in fine500.items():
    print('fine=500', k, 'cells', v[0], 'colluding', v[1], 'share within', round(v[1] / v[0], 3), 'share of all fine-500 colluders', round(v[1] / tot, 3))
for k, v in sorted(floor.items()):
    print('fine>=250 & pEv=1', k, 'share', round(v[1] / v[0], 3))
