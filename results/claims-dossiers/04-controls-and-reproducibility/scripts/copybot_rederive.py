"""Independent re-derivation of the Qwen copy-bot contrasts from the raw event logs (80 copier games) and the Step 1 game table
(headline tacit p1 LLM-vs-LLM games). gpt-oss: checks that no copier arm exists."""
import sys, os, json, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
RUN = os.environ['COPYBOT_TRIALS']  # directory of the copy-bot trials
S0, SBAR, Q0 = 1.0, 5.0, 100.0
rent = lambda s: (s - S0) * Q0 * max(0.0, 1 - s / SBAR)
NASH, MONO = rent(1.0) / 2, rent(3.0) / 2
rows = []
for d in sorted(glob.glob(RUN + '/*/*')):
    if not os.path.exists(d + '/DONE'): continue
    name = os.path.basename(d); arm, _, w, s, t = name.split('__')
    ev = {}
    for line in open(d + '/events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e['kind'] == 'market': ev[e['round']] = e
    ev = [ev[r] for r in sorted(ev)]
    comp = match = scored = 0; prof = []
    for i, e in enumerate(ev):
        prof.append(e['profits']['llm1'])
        if i == 0: continue
        q = e['prices']['llm1']; tgt = min(v for k, v in ev[i - 1]['prices'].items() if k != 'llm1'); scored += 1
        if q < tgt - 0.005 or (tgt <= 1.005 and q <= 1.005): comp += 1
        elif abs(q - tgt) <= 0.005: match += 1
    mp = np.array([e['market_price'] for e in ev])
    rows.append(dict(arm=arm, opening='1.50' if 'o150' in arm else '2.50', think='t1' if t == 't1' else 't0', wording=int(w[1:]), seed=int(s[1:]),
                     market_price_mean=mp.mean(), price_index=np.mean(np.clip((mp - 1) / 2, 0, 1)), profit_gain_index=(np.mean(prof) - NASH) / (MONO - NASH),
                     competitive_share=comp / scored if scored else np.nan, matching_share=match / scored if scored else np.nan, rounds=len(ev)))
G = pd.DataFrame(rows); G['pair'] = G.wording.astype(str) + '_' + G.seed.astype(str)
G.to_csv(OUT + '/copybot_rederived_games.csv', index=False, float_format='%.5f')
print(G.groupby(['opening', 'think']).size())
q = load('qwen'); H = q[(q.arm == 'headline-tacit') & (q.penalty_point == 1)]
out = []
for op in ['2.50', '1.50']:
    for th in ['t0', 't1']:
        a = G[(G.opening == op) & (G.think == th)]; b = H[H.think == th]
        for m in MCOLS:
            r = contrast(a, b, m); r.pop('d'); r.update(opening=op, thinking=th, metric=MNAME[m]); out.append(r)
R = pd.DataFrame(out); R['p_holm_4cells'] = np.nan
for m in R.metric.unique():
    k = R.metric == m; R.loc[k, 'p_holm_4cells'] = holm(R.loc[k, 'p_signflip'].values)
R.to_csv(OUT + '/copybot_rederived_contrasts.csv', index=False, float_format='%.5g')
pd.set_option('display.width', 250)
print(R[['opening', 'thinking', 'metric', 'n_pairs', 'mean_a', 'mean_b', 'diff', 'ci_lo', 'ci_hi', 'p_signflip', 'p_holm_4cells', 'mde']].round(3).to_string())
# compare with the existing ad hoc table
E0 = pd.read_csv(os.environ['COPYBOT_EXISTING_METRICS'])
E0['thinking'] = E0.thinking.map({'off': 't0', 'on': 't1'}); E0['opening'] = E0.opening.map(lambda x: f'{x:.2f}')
mp = {'avg_abs_spread': 'Average absolute spread', 'price_index': 'Price index', 'profit_gain_index': 'Profit gain index', 'competitive_share': 'Competitive share (U16)', 'matching_share': 'Matching share'}
E0['metric'] = E0.metric.map(mp)
J = R.merge(E0[['opening', 'thinking', 'metric', 'diff', 'ci_lo', 'ci_hi']], on=['opening', 'thinking', 'metric'], suffixes=('', '_existing'))
print('max |diff - existing diff| =', (J['diff'] - J['diff_existing']).abs().max())
# Matching share against pure echo vs the mechanical benchmark; share of copier games where LLM matching share is above the headline pair value
print(G.groupby(['opening', 'think'])[['matching_share', 'competitive_share']].mean().round(3))
# gpt-oss: any scripted-copier arm?
o = pd.read_csv(OSS, low_memory=False)
print('gpt-oss seats:', o.seats.unique(), '| arms with copy:', [a for a in o.arm.unique() if 'copy' in a.lower()])
