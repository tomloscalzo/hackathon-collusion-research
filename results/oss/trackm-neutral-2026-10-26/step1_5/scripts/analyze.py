import pandas as pd, numpy as np, json, sys
label = sys.argv[1]
d = pd.read_csv(f'fr_{label}.csv')
d = d.sort_values(['trial', 'round', 'seat'])
GRID = np.round(np.arange(100, 501) / 100, 2)
def prof(a, others, n=2, phi=0.3):
    """Engine PayoffEngine/PayoffFunctions: Q(s)=100(1-s/5); contestable (1-phi)Q(pc) to lowest, pref phi*Q(inside)/n each, profit=(price-1)*vol."""
    a = np.asarray(a, float); b = min(others)
    k_oth_tied = sum(1 for o in others if abs(o - b) < 1e-9)
    inside = np.minimum(a, b)
    Q = lambda s: 100 * np.maximum(0, 1 - s / 5)
    win = np.where(a < b - 1e-9, 1.0, np.where(abs(a - b) < 1e-9, 1.0 / (1 + k_oth_tied), 0.0))
    return ((1 - phi) * Q(inside) * win + phi * Q(inside) / n) * (inside - 1)
def best_response(b0, n, phi):
    others = [b0] * (n - 1)
    p = prof(GRID, others, n, phi)
    m = p.max()
    return GRID[p >= m - 1e-9], m
rows = []
for tid, g in d.groupby('trial'):
    piv = g.pivot(index='round', columns='seat', values='quote')
    llm = sorted(g[g.is_llm].seat.unique()); n = int(g.n.iloc[0]); phi = g.phi.iloc[0]; fine = g.fine.iloc[0]
    printed = set(json.loads(g.printed.iloc[0]))
    rds = sorted(piv.index)
    for s in llm:
        oth = [c for c in piv.columns if c != s]
        for r in rds:
            a = piv.at[r, s]; o_cur = piv.loc[r, oth].min()
            rec = dict(trial=tid, arm=g.arm.iloc[0], mode=g['mode'].iloc[0], seat=s, round=r, quote=a, rival_cur=o_cur, n=n,
                       is_printed=int(round(a, 2) in printed))
            if r >= 2 and r - 1 in piv.index:
                a0 = piv.at[r - 1, s]; b0 = piv.loc[r - 1, oth].min()
                rec.update(own_prev=a0, rival_prev=b0)
                if r >= 3:
                    rec['own_prev2'] = piv.at[r - 2, s]; rec['rival_prev2'] = piv.loc[r - 2, oth].min()
                brs, bp = best_response(b0, n, phi)
                p_act = float(prof(a, [b0] * (n - 1), n, phi))
                rec.update(br_lo=brs.min(), br_hi=brs.max(), br_profit=bp, profit_vs_prev=p_act, regret=bp - p_act)
                # with expected fine: P(inv)=0.025*(best-1), every firm pays 'fine'
                pf = prof(GRID, [b0] * (n - 1), n, phi) - 0.025 * (np.minimum(GRID, b0) - 1) * fine
                brf = GRID[pf >= pf.max() - 1e-9]
                rec.update(brf_lo=brf.min(), brf_hi=brf.max(),
                           at_brf=int(brf.min() - 0.0051 <= a <= brf.max() + 0.0051))
                # ex post best response to actual current rival quote
                brs2, bp2 = best_response(o_cur, n, phi)
                rec['at_br_expost'] = int(brs2.min() - 0.0051 <= a <= brs2.max() + 0.0051)
                rec['regret_expost'] = bp2 - float(prof(a, [o_cur] * (n - 1), n, phi))
                # classification vs prev rival quote
                tol = 0.0051
                if b0 <= 1.0 + 1e-9:
                    cat = 'rival_at_floor_quote_floor' if a <= 1.0 + 1e-9 else 'rival_at_floor_quote_above(dominated)'
                elif brs.min() - tol <= a <= brs.max() + tol:
                    cat = 'best_response'
                elif a > b0 + tol:
                    cat = 'above_rival(dominated)'
                elif abs(a - b0) <= tol:
                    cat = 'collusive_hold' if abs(a0 - b0) <= tol else 'match_rival'
                elif a < b0:
                    cat = 'other_undercut_not_BR'
                rec['cat'] = cat
            rows.append(rec)
f = pd.DataFrame(rows)
f.to_csv(f'firmrounds_{label}.csv', index=False)
print(f.shape)
