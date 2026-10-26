import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
# power of the wording test (5 wordings x 4 pairs, F test) : Cohen f giving 80% power, simulated; then in pgi units for gpt-oss
rng = np.random.default_rng(3)
def F(x, l):
    g = [x[l == w] for w in range(5)]; gm = x.mean()
    return (sum(4 * (a.mean() - gm) ** 2 for a in g) / 4) / (sum(((a - a.mean()) ** 2).sum() for a in g) / 15)
lab = np.repeat(np.arange(5), 4)
null = np.array([F(rng.standard_normal(20), lab) for _ in range(20000)]); crit = np.quantile(null, 0.95)
res = []
for f in np.arange(0.4, 1.31, 0.05):
    # equally spaced wording effects scaled so that sqrt(mean(delta^2)) = f
    d = np.array([-2, -1, 0, 1, 2], float); d = d / np.sqrt((d ** 2).mean()) * f
    pw = np.mean([F(rng.standard_normal(20) + d[lab], lab) > crit for _ in range(4000)])
    res.append((f, f * f / (1 + f * f), pw))
R = pd.DataFrame(res, columns=['cohen_f', 'eta2', 'power']); print(R.round(3).to_string())
f80 = R[R.power >= 0.8].iloc[0]; print('f for 80% power', f80.cohen_f, 'eta2', f80.eta2)
# gpt-oss within-wording sd of pair means (cell-adjusted) for pgi, price index
o = load('oss'); D = o[o.arm.isin(['headline-chat', 'headline-tacit'])].copy(); D['cell'] = D.arm + D.penalty_point.astype(str)
out = []
for m in MCOLS:
    D['adj'] = D[m] - D.groupby('cell')[m].transform('mean'); pm = D.groupby('pair').agg(adj=('adj', 'mean'), w=('wording', 'first'))
    sw = np.sqrt(sum(((g.adj - g.adj.mean()) ** 2).sum() for _, g in pm.groupby('w')) / 15)
    out.append(dict(metric=MNAME[m], within_wording_sd_of_pair_means=sw, detectable_sd_of_wording_means_80pct=f80.cohen_f * sw,
                    detectable_range_max_minus_min_approx=f80.cohen_f * sw * (4 / np.sqrt(((np.array([-2, -1, 0, 1, 2]) ** 2).mean()))) , f_for_80=f80.cohen_f, eta2_for_80=f80.eta2))
pd.DataFrame(out).to_csv(OUT + '/q14_wording_power.csv', index=False, float_format='%.4f'); print(pd.DataFrame(out).round(3).to_string())
