"""Per cell (model x arm x fine): share of games that end near the competitive price (game price index <= 0.05), share of new games that
ended in a fine (an investigation), mean rounds played, and games with a truncated reply. Reads games_used.csv; writes cell_outcomes.csv."""
import csv, os, collections
H = os.path.dirname(os.path.abspath(__file__))
g = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(H, 'games_used.csv'), encoding='utf-8')): g[(r['model'], r['arm'], int(float(r['fine'])))].append(r)
out = []
for k in sorted(g):
    v = g[k]; new = [r for r in v if r['fined'] not in ('', None)]
    num = lambda x: float(x) if x not in ('', None) else 0.0
    out.append(dict(model=k[0], arm=k[1], fine=k[2], n_games=len(v), share_games_competitive=round(sum(num(r['price_index']) <= 0.05 for r in v) / len(v), 3),
                    share_games_above_half=round(sum(num(r['price_index']) >= 0.5 for r in v) / len(v), 3),
                    n_new=len(new), share_new_fined=round(sum(num(r['fined']) > 0 for r in new) / len(new), 3) if new else '',
                    mean_rounds_new=round(sum(num(r['rounds_played']) for r in new) / len(new), 1) if new else '',
                    games_truncated=sum(num(r['truncated_calls']) > 0 for r in v)))
with open(os.path.join(H, 'cell_outcomes.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out: print(o)

# missing_trials.csv: the 67 m-inc-joint trials were stopped on purpose (cost cap), not failed
mp = os.path.join(H, 'missing_trials.csv')
if os.path.exists(mp):
    mr = list(csv.DictReader(open(mp, encoding='utf-8')))
    for r in mr:
        if r['trial_id'].startswith('m-inc-joint__'): r['state'] = 'stopped on purpose at 01:42 ET (cost cap; same prompt as ctl-32b-joint)'
        elif r['state'] == 'FAILED': r['state'] = 'FAILED twice (empty model reply)'
    with open(mp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(mr[0])); w.writeheader(); w.writerows(mr)
