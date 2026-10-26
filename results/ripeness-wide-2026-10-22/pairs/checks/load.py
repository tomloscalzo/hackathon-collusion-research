import csv, pickle, array
P = r'<local>\hackathon\work_scratch\wide\wide.csv'
LV = {"delta": [0.5, 0.7, 0.8, 0.9, 0.95, 0.99], "N": [2, 3, 4, 6, 10], "phi": [0.0, 0.3, 0.6], "tick": [0.0, 0.25, 0.5],
      "slope": [0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2], "rhoTip": [0.0, 0.01, 0.05], "pEvidence": [0.1, 0.3, 0.6, 1.0],
      "fineRatio": [0.0, 5.0, 12.5, 25.0, 50.0, 125.0, 250.0, 500.0], "sBarRatio": [2.0, 3.0, 5.0, 8.0, 12.0]}
NAMES = list(LV)
cols = {k: array.array('b') for k in NAMES}
ts, th, tp, w0, ws, ptr = (array.array('d') for _ in range(6))
reg = array.array('b')
RC = {}
errs = 0
idx = {k: {v: i for i, v in enumerate(LV[k])} for k in NAMES}
with open(P, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        for k in NAMES:
            cols[k].append(idx[k][float(r[k])])
        if r['error']:
            errs += 1
        ts.append(float(r['theta_star'] or 'nan')); th.append(float(r['theta_hat'] or 'nan'))
        tp.append(float(r['theta_star_given_participation'] or 'nan'))
        w0.append(float(r['w0'] or 'nan')); ws.append(float(r['w_star'] or 'nan'))
        ptr.append(float(r['p_trigger_star'] or 'nan'))
        reg.append(RC.setdefault(r['regime'], len(RC)))
pickle.dump({'LV': LV, 'cols': cols, 'ts': ts, 'th': th, 'tp': tp, 'w0': w0, 'ws': ws, 'ptr': ptr, 'reg': reg, 'RC': RC},
            open(r'<local>\hackathon\work_scratch\wide\pairs_out\grid.pkl', 'wb'))
print(len(ts), 'rows', errs, 'errors', RC)
