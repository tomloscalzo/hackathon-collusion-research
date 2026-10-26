import numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_channel import load_games, cmi, within_perm
from price_codes_v2 import transitions2, zk
g = load_games()[("gpt-oss-20b", "d-placebo", "on", 1)]
T = np.vstack([transitions2("oss|d-placebo|p1", x, i) for i, x in enumerate(g)])
rng = np.random.default_rng(1)
def bc(T):
    z = zk(T, "S_game"); o = cmi(T[:, 0], T[:, 8], z)
    return o - np.mean([cmi(T[:, 0], within_perm(T[:, 8], z, rng), z) for _ in range(300)])
full = bc(T); print("full", round(full, 4))
loo = [(i, round(full - bc(T[T[:, 10] != i]), 4)) for i in range(len(g))]
print(sorted(loo, key=lambda x: -x[1])[:5])
i = sorted(loo, key=lambda x: -x[1])[0][0]
print(g[i]["tid"]); print(g[i]["q"].T.to_string())
d = T[T[:, 10] == i]; print(pd.crosstab([d[:, 8]], d[:, 0]))
