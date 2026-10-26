"""Final Holm over the family 'discovery candidates': T3 uses the unselected wording-heterogeneity
p (seed-regrouping null) instead of the post hoc exploration-pair p. Usage: holm_final.py <tables_dir>"""
import sys, os, pandas as pd
t = sys.argv[1]
f = pd.read_csv(os.path.join(t, 'holm_family.csv'))[['test', 'p']]
h = pd.read_csv(os.path.join(t, 't3_wording_heterogeneity.csv'))
p_het = h[(h.model == 'gpt-oss-20b') & (h.outcome == 'price_index')].p_heterogeneity.iloc[0]
f.loc[f.test.str.startswith('T3 '), ['test', 'p']] = ['T3 wording heterogeneity, gpt-oss price index (seed-regrouping null)', p_het]
f.loc[f.test.str.startswith('T6'), 'p'] = f.loc[f.test.str.startswith('T6'), 'p'].clip(lower=1 / 2000)  # bootstrap resolution
f.loc[f.test.str.startswith('T1 '), 'p'] = f.loc[f.test.str.startswith('T1 '), 'p'].clip(lower=1e-5)
f = f.sort_values('p').reset_index(drop=True); m = len(f); r = 0; adj = []
for i, p in enumerate(f.p):
    r = max(r, min(1, (m - i) * p)); adj.append(r)
f['holm_p'] = adj; f['family'] = 'discovery candidates (m=%d)' % m
f['note'] = ['observed statistic beyond every null draw: true p is below this resolution floor' if t.startswith(('T6', 'T1 ')) else '' for t in f.test]
f.to_csv(os.path.join(t, 'holm_family_final.csv'), index=False); print(f.to_string())
