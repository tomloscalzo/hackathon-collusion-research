import os as _os, pathlib as _pl; _ROOT = _os.environ.get("COLLUSION_WORK_ROOT") or next((str(q) for q in _pl.Path(__file__).resolve().parents if (q / "runs").is_dir()), "..")  # the work directory holding runs/ and work_scratch/
import csv, json, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[4] / 'tools' / 'trial'))  # the repository's tools/trial
import make_grid
R = _ROOT + '/runs/'
TH = {'4': '0.3249', '5': '0.0000', '25': '0.0000', '100': '0.0000'}
SC = {'4': 'slice-m-p4.yaml', '5': 'slice-m-p5.yaml', '25': 'slice-m-p25.yaml', '100': 'slice-m-p100.yaml'}
def rows(run, arm):
    r = [x for x in csv.DictReader(open(R + run + '/grid.csv', encoding='utf-8')) if x['arm'] == arm and x['penalty_point'] == '3' and x['thinking'] == '1' and x.get('payoff_examples') == 'neutral']
    assert len(r) == 20, (run, arm, len(r)); return r
def make(run, arm, pts):
    out = []
    for x in rows(run, arm):
        for p in pts:
            y = dict(x); y['penalty_point'] = p; y['scenario_file'] = SC[p]; y['theory_theta_star'] = TH[p]; y['wave'] = '301'; y['pilot'] = ''
            y['trial_id'] = '%s__p%s__w%s__s%s__t%s' % (arm, p, x['wording'], x['seed'], x['thinking'])
            out.append({k: y.get(k, '') for k in make_grid.GRID_COLS})
    return out
def write(fn, rs):
    with open(fn, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=make_grid.GRID_COLS); w.writeheader(); w.writerows(rs)
    print(fn, len(rs), len({r['trial_id'] for r in rs}))
O = _ROOT + '/runs/2026-10-26_trackm_oss_neutral'.split('/')[-1]
# highest fine first within a seed is arbitrary; "longest first": the joint-profit objectives (long negotiated games) first
write('grid_o.csv', make(O, 'ctl-32b-joint', ['4', '5', '25', '100']) + make(O, 'm-inc-joint', ['4', '5', '25', '100']) + make(O, 'headline-chat', ['4', '25', '100']))
write('grid_ot.csv', make(O, 'm-inc-target', ['4', '5', '25', '100']))
write('grid_q.csv', make('2026-10-25_trackm_neutral', 'ctl-32b-joint', ['25', '100']) + make('2026-10-25_trackm_neutral', 'headline-chat', ['25', '100']))
