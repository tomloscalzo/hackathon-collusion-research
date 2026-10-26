"""Penalty extension: the rational benchmarks per fine F for the two-firm slice-m market (slice-m-p*.yaml).

Market (engine PayoffEngine, tick 0): customer volume Q(s) = 100 (1 - s/5) at the best (lowest) quote s; 70% of the flow
(contestable) goes to the lowest quote, 30% (preferenced) is split equally and also trades at the lowest quote (price matching).
Cost 1.00. Each round the regulator opens an investigation with probability h = min(1, 0.025 (best quote - 1.00)); it finds
evidence for sure (rhoCoop 1), every firm pays F, and the game ends. Otherwise the game continues with probability delta = 0.95.

Benchmarks (all on a 0.01 grid of half-spreads s in [1.00, 5.00]; price index = (market price - 1.00) / 2.00):
  1. joint optimum s_joint: the symmetric price both firms would quote every round to maximise each firm's expected value
     V(s) = (pi(s) - h(s) F) / (1 - delta (1 - h(s))), pi(s) = (s - 1) Q(s) / 2  (= penalty-gradients joint_optimum.csv).
  2. sustainable cartel price theta*: the Layer A CartelSolver (layer_a.solve, a re-implementation of MODEL_SPEC eqs 4-13): the same
     V maximised subject to the incentive constraint that undercutting by one tick for one round and then facing a permanent price
     war at 1.00 does not pay. In this tick-free market the constraint is 0.7 <= delta(1-h)/(1-delta(1-h)), which holds for every
     h <= about 0.53, so theta* equals the joint optimum here (a continuous-grid value; the scenario files print it).
  3. one-shot (stage) best response to a rival at r, ignoring the fine and the future: undercut by one tick (r - 0.01) when r is
     above the monopoly-undercut point, else ... computed numerically; the static Nash (stage-game equilibrium) is 1.00
     (1.01 is also an equilibrium on the 0.01 grid: matching at 1.01 earns a tiny positive amount, undercutting to 1.00 earns 0).
  4. fine-aware stationary best response to a rival who keeps quoting r: argmax_x (pi_i(x, r) - h(min(x, r)) F) / (1 - delta (1 - h)).
Usage: python -X utf8 theory_pe.py [out.csv]
"""
import os as _os, pathlib as _pl; _ROOT = _os.environ.get("COLLUSION_WORK_ROOT") or next((str(q) for q in _pl.Path(__file__).resolve().parents if (q / "runs").is_dir()), "..")  # the work directory holding runs/ and work_scratch/
import csv, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WT = str(__import__('pathlib').Path(__file__).resolve().parents[3])  # the repository root
sys.path.insert(0, WT + '/results/ad-hoc-targeted-analysis/model-vs-llm')
from layer_a import solve  # noqa: E402

SCEN = WT + '/engine/src/main/resources/scenarios'
DELTA, PHI, SLOPE, Q0, SBAR, S0 = 0.95, 0.3, 0.025, 100.0, 5.0, 1.0
S = np.round(np.arange(1.0, 5.0001, 0.01), 2)


def Q(s): return Q0 * np.maximum(0.0, 1.0 - s / SBAR)
def h(s): return np.minimum(1.0, SLOPE * np.maximum(0.0, s - S0))
def idx(s): return (s - S0) / 2.0


def pi_i(x, r):
    """Stage profit of a firm quoting x against a rival quoting r (both trade at the lowest quote)."""
    p = np.minimum(x, r); base = (p - S0) * Q(p)
    share = np.where(np.isclose(x, r), 0.5, np.where(x < r, (1 - PHI) + PHI / 2, PHI / 2))
    return base * share


def V_joint(s, F, delta=DELTA):
    hh = h(s); return ((s - S0) * Q(s) / 2 - hh * F) / (1 - delta * (1 - hh))


def stage_br(r):
    v = pi_i(S, r); return float(S[int(np.argmax(v))])


def fine_br(r, F, delta=DELTA):
    hh = h(np.minimum(S, r)); v = (pi_i(S, r) - hh * F) / (1 - delta * (1 - hh)); return float(S[int(np.argmax(v))])


def fines():
    out = []
    for f in sorted(os.listdir(SCEN)):
        m = re.fullmatch(r'slice-m-p(\d+)\.yaml', f)
        if not m: continue
        t = open(os.path.join(SCEN, f), encoding='utf-8').read()
        F = float(re.search(r'^\s*fine:\s*([\d.]+)', t, re.M).group(1))
        th = re.search(r'^#\s*theory-theta-star:\s*([\d.]+)', t, re.M).group(1)
        out.append((int(m.group(1)), F, float(th)))
    return sorted(out, key=lambda x: x[1])


def main(path):
    rows = []
    for p, F, th_file in fines():
        V = V_joint(S, F); i = int(np.argmax(V)); sj = float(S[i])
        if V[i] <= 0: sj = 1.0
        la = solve(fine=F, delta=DELTA)
        r = dict(fine=int(F), penalty_label='p%d' % p, fine_multiple_of_p1=F / 100.0,
                 s_joint_opt=sj, idx_joint_opt=idx(sj), pi_joint_opt=float(V[i]) if V[i] > 0 else 0.0,
                 theta_star_cartelsolver=th_file, s_cartel_sustainable_theta=1.0 + 2.0 * th_file,
                 theta_star_layer_a=round(la['theta_star'], 4), idx_theta_star=th_file,
                 s_static_nash=1.00, idx_static_nash=0.0,
                 s_joint_opt_myopic=float(S[int(np.argmax(V_joint(S, F, 0.0)))]))
        for s in (3.00, 2.50, 2.09, 2.00, 1.50, 1.20):
            hh = h(np.array(s)); r['round_net_profit_per_firm_at_%.2f' % s] = float((s - 1) * Q(np.array(s)) / 2 - hh * F)
            r['value_per_firm_at_%.2f' % s] = float(V_joint(np.array(s), F))
        for rv in (3.00, 2.50, 2.00, 1.50):
            r['stage_br_to_%.2f' % rv] = stage_br(rv); r['fine_aware_br_to_%.2f' % rv] = fine_br(rv, F)
        rows.append(r)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows: w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    # verification against penalty-gradients joint_optimum.csv
    jo = list(csv.DictReader(open(WT + '/results/ad-hoc-targeted-analysis/penalty-gradients/joint_optimum.csv')))
    # match = the csv's s_opt attains the maximum value on the grid (F=500, delta=0 has an exact tie between 2.37 and 2.38)
    ok = True
    for x in jo:
        V = V_joint(S, float(x['fine']), float(x['continuation'])); j = int(np.argmin(abs(S - float(x['s_opt']))))
        ok &= bool(V.max() - V[j] < 1e-9)
    print('verification vs penalty-gradients/joint_optimum.csv (all 10 rows; the delta 0.95 rows match exactly):', 'MATCH' if ok else 'MISMATCH')
    return rows


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'theory_by_fine.csv')
    for r in main(out):
        print({k: r[k] for k in ('fine', 'penalty_label', 's_joint_opt', 'idx_joint_opt', 'pi_joint_opt', 'theta_star_cartelsolver', 'theta_star_layer_a',
                                 'round_net_profit_per_firm_at_3.00', 'round_net_profit_per_firm_at_2.50', 'round_net_profit_per_firm_at_2.00', 'round_net_profit_per_firm_at_1.50',
                                 'stage_br_to_2.50', 'fine_aware_br_to_2.50', 'fine_aware_br_to_2.00', 'fine_aware_br_to_1.50')})
