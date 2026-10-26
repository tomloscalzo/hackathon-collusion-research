"""Reliability and the join. Reads ratings_rater<k>.csv (k=1..3, all batches concatenated), PRIVATE_key.csv. Writes prompt_ratings.csv, reliability.json."""
import pandas as pd, numpy as np, json, itertools, sys
KEY = ['penalty_point', 'scenario_file', 'communication', 'firms', 'seats', 'condition_texts', 'wording', 'options', 'payoff_examples']
R = {k: pd.read_csv('ratings/ratings_rater%d.csv' % k).set_index('id') for k in (1, 2, 3)}   # run from results/prompt-ratings
ids = sorted(set.intersection(*[set(r.index) for r in R.values()]))
print('prompts rated by all 3:', len(ids))
assert all(len(r) == len(ids) for r in R.values()), 'a rater is missing prompts'
def wkappa(a, b, lo=1, hi=5):
    n = hi - lo + 1
    O = np.zeros((n, n))
    for x, y in zip(a, b): O[int(x) - lo, int(y) - lo] += 1
    O /= O.sum()
    E = np.outer(O.sum(1), O.sum(0))
    W = np.array([[(i - j) ** 2 for j in range(n)] for i in range(n)]) / (n - 1) ** 2
    return 1 - (W * O).sum() / (W * E).sum()
def icc(M):  # M: n x k ; ICC(2,1) and ICC(2,k) (two-way random, absolute agreement), Shrout-Fleiss
    n, k = M.shape
    gm = M.mean(); rm = M.mean(1); cm = M.mean(0)
    msr = k * ((rm - gm) ** 2).sum() / (n - 1)
    msc = n * ((cm - gm) ** 2).sum() / (k - 1)
    sse = ((M - rm[:, None] - cm[None, :] + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    msw = (((M - rm[:, None]) ** 2).sum()) / (n * (k - 1))
    icc1_1 = (msr - msw) / (msr + (k - 1) * msw); icc1_k = (msr - msw) / msr
    i21 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    i2k = (msr - mse) / (msr + (msc - mse) / n)
    return i21, i2k, icc1_1, icc1_k
out = {}
for sc in ('conflict', 'temptation'):
    M = np.column_stack([R[k].loc[ids, sc].astype(float).values for k in (1, 2, 3)])
    pw = {'%d-%d' % (a, b): wkappa(M[:, a - 1], M[:, b - 1]) for a, b in itertools.combinations((1, 2, 3), 2)}
    i21, i2k, i11, i1k = icc(M)
    exact = float(np.mean([len(set(r)) == 1 for r in M])); within1 = float(np.mean(M.max(1) - M.min(1) <= 1))
    out[sc] = dict(weighted_kappa_quadratic=pw, kappa_mean=float(np.mean(list(pw.values()))), icc2_1=i21, icc2_k=i2k, icc1_1=i11, icc1_k=i1k,
                   all_three_equal=exact, range_le1=within1, rater_means=[float(M[:, i].mean()) for i in range(3)],
                   dist={str(v): [int((M[:, i] == v).sum()) for i in range(3)] for v in range(1, 6)})
json.dump(out, open('reliability.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
rows = []
for i in ids:
    d = dict(id=i)
    for sc in ('conflict', 'temptation'):
        v = [float(R[k].loc[i, sc]) for k in (1, 2, 3)]
        d.update({sc + '_mean': round(float(np.mean(v)), 4), sc + '_median': float(np.median(v)), sc + '_sd': round(float(np.std(v, ddof=1)), 4),
                  sc + '_r1': v[0], sc + '_r2': v[1], sc + '_r3': v[2]})
    rows.append(d)
pr = pd.DataFrame(rows)
pr.to_csv('prompt_level_ratings.csv', index=False, lineterminator=chr(10))
key = pd.read_csv('PRIVATE_key.csv', dtype=str).fillna('')
key['payoff_examples'] = key['payoff_examples'].replace('', 'anchored')
pm = pr.set_index('id')
def agg(row):
    seats = [row['id']] + [x for x in (row['id_s2'], row['id_s3']) if x]
    out = {}
    for sc in ('conflict', 'temptation'):
        v = [pm.loc[x, sc + '_mean'] for x in seats]
        out[sc + '_mean'] = round(float(np.mean(v)), 4); out[sc + '_max'] = round(float(np.max(v)), 4)
        out[sc + '_median'] = round(float(np.mean([pm.loc[x, sc + '_median'] for x in seats])), 4)
        out[sc + '_sd'] = round(float(np.mean([pm.loc[x, sc + '_sd'] for x in seats])), 4)
    out['n_distinct_seat_prompts'] = len(set(seats))
    return pd.Series(out)
j = pd.concat([key, key.apply(agg, axis=1)], axis=1)
cols = ['id', 'id_s2', 'id_s3'] + KEY + ['arms', 'thinking_modes', 'n_distinct_seat_prompts'] + [c for c in j.columns if c.startswith(('conflict', 'temptation'))]
j[cols].to_csv('prompt_ratings.csv', index=False, lineterminator=chr(10))
print(len(j), 'key rows;', j['id'].nunique(), 'seat-1 prompts;', len(pr), 'rated prompts;', j['conflict_mean'].isna().sum(), 'unrated')
