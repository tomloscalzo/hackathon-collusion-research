"""Step 1 for the neutral run: filter A1's run.csv to run == neutral and run the Step 1 validation checks on the filtered set.
Inputs: analysis_final/run_csv (PROVISIONAL), steps/neutral/step1/tables (own collect.py tables with supersession applied),
view_neutral/superseded.csv."""
import pandas as pd, numpy as np, json, re, os

W = os.environ['ANALYSIS_FINAL_DIR'].rstrip('/') + '/'  # the scratch analysis folder (not in git)
RUNS = os.environ['RUNS_DIR'].rstrip('/') + '/'  # the runs folder next to the checkout
O = W + 'steps/neutral/step1/'
r = pd.read_csv(W + 'run_csv/run.csv', low_memory=False)
f = pd.read_csv(W + 'run_csv/run_firms.csv', low_memory=False)
n = r[r.run == 'neutral'].copy()
nf = f[f.row_id.isin(n.row_id)].copy()
sup = pd.read_csv(W + 'run_csv/run_superseded.csv', low_memory=False)
sup = sup[sup.run == 'neutral']
unp = pd.read_csv(W + 'run_csv/run_unpaired.csv')
t = pd.read_csv(O + 'tables/trials.csv')
mine = pd.read_csv(W + 'view_neutral/superseded.csv')
grid = pd.read_csv(RUNS + '2026-10-25_trackm_neutral/grid.csv')
n.to_csv(O + 'run.csv', index=False, lineterminator='\n')
nf.to_csv(O + 'run_firms.csv', index=False, lineterminator='\n')
sup.to_csv(O + 'run_superseded.csv', index=False, lineterminator='\n')
unp[unp.row_id.isin(n.row_id)].to_csv(O + 'run_unpaired.csv', index=False, lineterminator='\n')
res = []


def chk(i, name, exp, obs, ok):
    res.append({'id': i, 'check': name, 'expected': exp, 'observed': obs, 'pass': 'PASS' if ok else 'FAIL'})


d = n[n.status == 'done']
npl = int((~grid.pilot.fillna(0).astype(str).str.lower().isin(['1', '1.0', 'true'])).sum())
chk(1, 'Row count equals non-pilot rows of the neutral grid.csv; row_id and pair_key unique', npl,
    '%d rows; row_id unique %s; pair_key unique %s' % (len(n), n.row_id.is_unique, n.pair_key.is_unique),
    len(n) == npl and n.row_id.is_unique and n.pair_key.is_unique)
dup = int(d.played_trial_id.duplicated().sum())
chk(2, 'One counted game per planned trial; no game counted twice; counted games = my own collect tables',
    '0 duplicates; sets equal',
    '%d duplicate counted; %d in my tables but not counted; %d counted but not in my tables' % (
        dup, len(set(t.trial_id) - set(d.played_trial_id)), len(set(d.played_trial_id) - set(t.trial_id))),
    dup == 0 and set(t.trial_id) == set(d.played_trial_id))
orig = set(sup.trial_id)
reruns = set(d.played_trial_id[d.played_trial_id.str.endswith('__x32k')])
chk(3, 'Supersession: originals absent from run.csv; no chains; no placeholder source; counted reruns vs my superseded.csv (trunc_rerun.py supersede)',
    '0 overlap; 0 chains; 0 placeholder rows',
    '%d originals counted; %d chained; %d placeholder-source rows; %d counted reruns (mine at my build: %d); %d reruns counted but absent from my list' % (
        len(orig & set(d.played_trial_id)), sum(x.endswith('__x32k__x32k') for x in reruns),
        int((n.condition_text_source == 'placeholder').sum()), len(reruns), len(mine), len(reruns - set(mine.rerun_id))),
    not (orig & set(d.played_trial_id)) and not (n.condition_text_source == 'placeholder').any())
decl = n[n.arm_family.ne('smoke_14b_32b') & ~n.arm.str.startswith('ctl-14b')]
bad = decl[decl.on_declared_seed_set != 1]
cs = d.groupby(['arm', 'penalty_point', 'thinking']).size()
chk(5, 'Seed set: every main-arm (wording, seed) is one of the 20 declared pairs; 20 counted games per cell and mode',
    '0 off-set; every cell 20', '%d off-set rows; cell sizes %s' % (len(bad), {int(k): int(v) for k, v in cs.value_counts().items()}),
    len(bad) == 0 and set(cs.unique()) == {20})
m = d.merge(t, left_on='played_trial_id', right_on='trial_id', suffixes=('', '_t'))
diffs = {a: int(((m[a].astype(float) - m[b].astype(float)).abs() > 1e-5).sum()) for a, b in [
    ('rounds_played', 'rounds'), ('undercut_count', 'undercuts'), ('profit_total', 'profit_total'),
    ('refusals', 'refusals'), ('truncations', 'truncations'), ('price_index', 'collusion_level')]}
chk(6, 'Agreement with collect.py (my independent collect run, supersession applied)', '0 differences',
    '%d games compared; differences %s' % (len(m), diffs), sum(diffs.values()) == 0)
v = []
if not d.price_index.between(0, 1).all():
    v.append('price_index range')
s = d.competitive_share + d.matching_share + d.above_share
if (abs(s[s.notna()] - 1) > 1e-4).any():
    v.append('shares sum')
ps = nf.groupby('row_id').profit_total.sum()
dd = d.set_index('row_id').profit_total
if (abs(ps.reindex(dd.index) - dd) > 1e-3 * (1 + abs(dd))).any():
    v.append('profit_total vs firms')
chk(7, 'Identities: 0<=price_index<=1; shares sum to 1; profit_total = sum of firm profits', '0 violations',
    str(v or '0 violations'), not v)
v = []
off = d[d.thinking == 'off']
if off.reasoning_words_total.fillna(0).gt(0).any():
    v.append('thinking-off rows with reasoning words')
if (d.cot_threat == 1).where(d.thinking == 'off', False).any():
    v.append('cot_threat on thinking off')
if d[d.communication == 'tacit'].messages.fillna(0).gt(0).any():
    v.append('tacit rows with messages')
chk(9, 'Mode logic: thinking-off rows have no reasoning words; cot_threat only thinking on; tacit rows have no messages',
    '0 violations', str(v or '0 violations'), not v)
on = d[d.thinking == 'on']
unexp = on[(on.truncated_calls_original.fillna(0) > 0) & (on.supersession != 'truncation_rerun') & (on.primary_flagged != 1)]
nr = int((on.supersession == 'truncation_rerun').sum())
nfl = int(on.primary_flagged.sum())
chk(10, 'Truncation: every thinking-on counted row never truncated, a truncation rerun, or flagged', '0 unexplained rows',
    'never truncated %d; truncation rerun %d; flagged (rerun missing or truncated again) %d; unexplained %d' % (len(on) - nr - nfl, nr, nfl, len(unexp)),
    len(unexp) == 0)
c = d[d.control_row_id.notna()]
k = n.set_index('row_id').reindex(c.control_row_id)
vio = int(((k.wording.values != c.wording.values) | (k.seed.values != c.seed.values) |
           (k.thinking.values != c.thinking.values) | (k.run.values != c.run.values)).sum())
chk(11, 'Controls: every control_row_id exists in the same run, wording, seed and thinking', '0 violations',
    '%d with a control; %d violations' % (len(c), vio), vio == 0)
emp = {x: int(d[x].isna().sum()) for x in d.columns if x.endswith('_description') and x != 'score_description' and d[x].isna().any()}
emp.update({'score_description (rows with a score field)': int(d[d.score_name.notna()].score_description.isna().sum())} if d[d.score_name.notna()].score_description.isna().any() else {})
chk(12, 'Descriptions: every description column non-empty in every counted row (score_description only where a score field exists)', '0 empty', str(emp or '0 empty columns'), not emp)
dic = pd.read_csv(W + 'run_csv/data_dictionary.csv')
chk(13, 'Dictionary completeness: every run.csv/run_firms.csv column has a dictionary row', 'exact match',
    'run.csv %d cols, run_firms.csv %d cols; dictionary rows %d' % (n.shape[1], nf.shape[1], len(dic)), len(dic) >= n.shape[1])
txt = ''.join(open(O + x, encoding='utf-8').read() for x in ['run.csv', 'run_firms.csv'])
hits = len(re.findall(r'[A-Za-z]:.Users|@[A-Za-z0-9-]+[.](?:com|org)|sk-[A-Za-z0-9]{20}', txt))
chk(16, 'Hygiene: no local path, email, key in run.csv / run_firms.csv', '0 findings', '%d findings' % hits, hits == 0)
chk('S1', 'Neutral rows: payoff_examples is neutral for every row', 'all neutral', str(n.payoff_examples.value_counts().to_dict()),
    (n.payoff_examples == 'neutral').all())
chk('S2', 'Neutral status counts (28 never_started = 14b smoke/control arms not in the queue)', '1360 done',
    str(n.status.value_counts().to_dict()), int((n.status == 'done').sum()) == 1360)
g1 = d.groupby('arm').prompt_fingerprint.nunique()
g2 = d.groupby('arm').code_commit.nunique()
chk('S3', 'One fingerprint and one code_commit per arm in the neutral run', '1 each',
    '%d arms with >1 fingerprint; %d with >1 commit' % (int((g1 > 1).sum()), int((g2 > 1).sum())), (g1 == 1).all() and (g2 == 1).all())
miss = n[n.supersession == 'rerun_missing']
chk('S4', 'Pending truncation reruns are flagged rerun_missing (final refresh needed)', 'flagged and listed',
    '%d rows: %s' % (len(miss), ', '.join(miss.trial_id)), True)
pd.DataFrame(res).to_csv(O + 'checks.csv', index=False, lineterminator='\n')
L = ['# Validation of the neutral run.csv (Step 1)', '',
     '**PROVISIONAL** (built from the games DONE at the time of the provisional A1 build; pending truncation reruns are in check S4). '
     '`run.csv` here is the Step 1 builder\'s `run.csv` filtered to `run == neutral` (%d rows, %d columns); `run_firms.csv` filtered the same way (%d rows). '
     'Checks 4 (pairing), 8 (fingerprints across runs), 14 (heuristic validation) and 15 (determinism) concern both runs or the generator and are read from the builder\'s own validation (`A1_VALIDATION.md`); '
     'the other numbered checks are re-run here on the neutral subset, with check 6 compared against an independent `collect.py` run with supersession applied by `trunc_rerun.py supersede`.' % (len(n), n.shape[1], len(nf)),
     '', '| id | check | expected | observed | result |', '|---|---|---|---|---|']
for x in res:
    L.append('| %s | %s | %s | %s | %s |' % (x['id'], x['check'], x['expected'], str(x['observed']).replace('|', '/'), x['pass']))
L += ['', '## Heuristic columns (carried from the builder)', '',
      'The explicit-agreement, intent-class, detector, candour and say-versus-do columns are keyword-rule labels with **no blind hand-labelled held-out sample**: they are **unvalidated**, and every claim built on them carries that caveat. '
      'The only hand-labelled sample is for the monitor/shutdown mention rule (neutral: agreement 64/66, Wilson 0.90 to 0.99; anchored: 36/58, 0.49 to 0.73, so the error differs between runs). '
      'Frozen parameters: detector level_min 0.8, window 2, tol 0.25; intent min_share 0.1, max_competitive_share 0.5; none tuned on these runs.', '',
      'Created by Claude at the prompting of the repository owner.']
open(O + 'VALIDATION.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(O + 'VALIDATION.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print(pd.DataFrame(res)[['id', 'pass']].to_string())
print(*[x['observed'] for x in res if x['pass'] == 'FAIL'], sep='\n')
