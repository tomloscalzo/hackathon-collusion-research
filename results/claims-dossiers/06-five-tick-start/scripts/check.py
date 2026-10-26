import sys; sys.path.insert(0, ".")
from common import *
for m in SRC:
    r, rd = load(m); f = firm_rounds(rd)
    g = f.groupby("trial_id")
    d = pd.DataFrame({"pi": f.groupby("trial_id").price_index_fr.mean(),
        "cs_a": f[f.has_prev].groupby("trial_id").comp.mean(), "cs_b": f[f.has_prev].groupby("trial_id").undercut.mean(),
        "ms": f[f.has_prev].groupby("trial_id").match.mean(), "pf": f.groupby("trial_id").profit.mean()}).reset_index()
    x = r.merge(d, on="trial_id")
    print(m, len(r), len(x))
    for a, b in (("price_index","pi"),("competitive_share","cs_a"),("competitive_share","cs_b"),("matching_share","ms")):
        print(a,b,"maxabs",(x[a]-x[b]).abs().max(), "n>1e-3",((x[a]-x[b]).abs()>1e-3).sum())
    # profit calibration
    A = np.polyfit(x.pf, x.profit_gain_index, 1); res = x.profit_gain_index - np.polyval(A, x.pf)
    print("pgi~profit/firm-round fit", A, "maxres", res.abs().max())
