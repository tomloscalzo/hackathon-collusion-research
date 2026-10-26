"""Print markdown snippets (<!-- name --> blocks) for ANALYSIS.md from the penalty-extension CSVs."""
import csv, os
H = os.path.dirname(os.path.abspath(__file__))
def rd(f): return list(csv.DictReader(open(os.path.join(H, f), encoding='utf-8')))
FL = {'100': '100 (p1)', '300': '300 (p2)', '500': '500 (p3)', '1000': '1,000 (p4, owner\'s p10)', '2000': '2,000 (p5)', '2500': '2,500 (new, p25)', '10000': '10,000 (new, p100)'}
ARM = {'headline-chat': 'headline-chat: default objective, maximise own profit', 'ctl-32b-joint': 'ctl-32b-joint: told to maximise joint profit',
       'm-inc-joint': 'm-inc-joint: told to maximise joint profit (same prompt as ctl-32b-joint)', 'm-inc-target': 'm-inc-target: profit-target pressure'}
M = [('market_price_mean', 'spread'), ('price_index', 'price index'), ('profit_gain_index', 'profit gain'), ('competitive_share', 'competitive share'), ('matching_share', 'matching share')]
def f2(x, d=2):
    try: return ('%+.' + str(d) + 'f') % float(x)
    except: return ''
def f(x, d=2):
    try: return ('%.' + str(d) + 'f') % float(x)
    except: return ''
def ci(r, k, signed=False):
    g = f2 if signed else f
    return '%s [%s, %s]' % (g(r[k + ('_d' if signed else '_mean')]), g(r[k + '_lo']), g(r[k + '_hi']))
def fine(x): return FL.get(str(int(float(x))), x)
out = []
def block(name, text): out.append('<!-- %s -->\n%s\n' % (name, text))
th = rd('theory_by_fine.csv')
t = ['| Fine (penalty label) | Fine / p1 fine | Joint optimum s (index) | θ* sustainable (index) | One-round optimum s | Net profit per firm per round at 2.00 / 1.50 | Value per firm at 2.00 | Fine-aware best response to a rival at 2.50 |', '|---|---|---|---|---|---|---|---|']
for r in th:
    t.append('| %s | x%s | %s (%s) | %s | %s | %s / %s | %s | %s |' % (fine(r['fine']), f(r['fine_multiple_of_p1'], 0), f(r['s_joint_opt']), f(r['idx_joint_opt'], 3), f(r['theta_star_cartelsolver'], 3), f(r['s_joint_opt_myopic']),
             f(r['round_net_profit_per_firm_at_2.00']), f(r['round_net_profit_per_firm_at_1.50']), f(r['value_per_firm_at_2.00'], 0), f(r['fine_aware_br_to_2.50'])))
block('theory', '\n'.join(t))
cm = rd('cell_means.csv')
for model in ('gpt-oss-20b', 'Qwen3-32B'):
    rows = [r for r in cm if r['model'] == model]
    t = ['| Objective arm | Fine | n games (new) | ' + ' | '.join(lbl for _, lbl in M) + ' | θ* index |', '|---|---|---|' + '---|' * (len(M) + 1)]
    for r in sorted(rows, key=lambda r: (list(ARM).index(r['arm']) if r['arm'] in ARM else 9, float(r['fine']))):
        t.append('| %s | %s | %s (%s) | %s | %s |' % (ARM.get(r['arm'], r['arm']), fine(r['fine']), r['n_games'], r['new_games'], ' | '.join(ci(r, k) for k, _ in M), f(r['idx_theta_star'], 3)))
    block('cells_' + ('oss' if model.startswith('gpt') else 'qwen'), '\n'.join(t))
co = rd('contrasts.csv')
for fam, key in (('V', 'vs500'), ('S', 'steps')):
    for model in ('gpt-oss-20b', 'Qwen3-32B'):
        rows = [r for r in co if r['family'].startswith(fam) and r['model'] == model]
        t = ['| Contrast (paired on wording x seed) | n pairs | ' + ' | '.join(lbl + ' Δ [95% CI]' for _, lbl in M) + ' | θ* Δ index |', '|---|---|' + '---|' * (len(M) + 1)]
        for r in rows:
            cells = []
            for k, _ in M:
                s = ci(r, k, True)
                try:
                    if float(r[k + '_holm']) < 0.05: s = '**' + s + '**'
                except: pass
                cells.append(s)
            t.append('| %s | %s | %s | %s |' % (ARM.get(r['arm'], r['arm']).split(':')[0] + ': fine ' + fine(r['fine_hi']) + ' − ' + fine(r['fine_lo']), r['n_pairs'], ' | '.join(cells), f2(r['price_index_theory_idx_theta_star'])))
        block('con_%s_%s' % (key, 'oss' if model.startswith('gpt') else 'qwen'), '\n'.join(t))
ra = rd('rationality.csv')
BR = {str(int(float(r['fine']))): (float(r['fine_aware_br_to_2.50']) - 1) / 2 for r in th}
t = ['| Model | Objective arm | Fine | n | Observed price index [95% CI] | Point benchmark (θ* = joint optimum) | Gap to point [95% CI] | Verdict vs the rational set | Belief bound (BR to a rival at 2.50) | Verdict vs belief bound |', '|---|---|---|---|---|---|---|---|---|---|']
tally = {}
for r in ra:
    fk = str(int(float(r['fine']))); b = r['primary_used']; obs, lo, hi = float(r['price_index_obs']), float(r['obs_lo']), float(r['obs_hi']); pt = float(r[b])
    own = r['arm'] in ('headline-chat', 'm-inc-target')
    if own:   # own profit: any symmetric price in [0, theta*] is self-enforcing (theta* is the top of that range)
        v = 'within the rational range [0, θ*]' if lo <= pt + 0.05 else 'above the rational range'
    else:     # joint profit: the target is the joint optimum itself
        v = 'at the joint optimum' if (lo <= pt <= hi or abs(obs - pt) <= 0.05) else ('above the joint optimum' if obs > pt else 'below the joint optimum')
    bb = BR.get(fk)
    vb = '' if bb is None else ('above even this bound' if lo > bb + 0.05 else 'within this bound')
    biased = r['arm'] == 'm-inc-joint' and fk != '500'
    if not biased: tally[v] = tally.get(v, 0) + 1
    t.append('| %s | %s%s | %s | %s | %s [%s, %s] | %s | %s [%s, %s] | %s | %s | %s |' % (r['model'], ARM.get(r['arm'], r['arm']).split(':')[0], ' (stopped early, biased)' if biased else '', fine(r['fine']), r['n_games'],
             f(obs), f(lo), f(hi), f(pt, 3), f2(r['gap_' + b]), f2(r['gap_' + b + '_lo']), f2(r['gap_' + b + '_hi']), v, f(bb, 3) if bb is not None else '', vb))
block('rationality', chr(10).join(t) + chr(10) * 2 + 'Tally over the %d cells not biased by early stopping: %s.' % (sum(tally.values()), '; '.join('%s %d' % kv for kv in sorted(tally.items()))))
el = rd('elasticity.csv')
t = ['| Model | Objective arm | Fines used | n games | Observed slope per tenfold fine [95% CI] | θ* slope over the same fines (unweighted, descriptive only) |', '|---|---|---|---|---|---|']
for r in el:
    if r['arm'] == 'm-inc-joint': continue
    t.append('| %s | %s | %s | %s | %s [%s, %s] | %s |' % (r['model'], ARM.get(r['arm'], r['arm']).split(':')[0], r['fines'].replace(';', ', '), r['n_games'], f2(r['slope_obs'], 3), f2(r['slope_lo'], 3), f2(r['slope_hi'], 3), f2(r['slope_idx_theta_star'], 3)))
block('elasticity', '\n'.join(t))
mi = rd('missing_trials.csv') if os.path.exists(os.path.join(H, 'missing_trials.csv')) else []
block('missing_unused', 'Games planned but not in the tables: %d (listed in `missing_trials.csv`).' % len(mi))
print('\n'.join(out))
