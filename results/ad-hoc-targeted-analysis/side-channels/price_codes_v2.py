"""Price-channel code tests, version 2 (after adversarial review).

Changes from price_channel.py:
  - transitions never span a missing round (consecutive round numbers required);
  - code-test p-values use 2000 within-stratum permutations, refined to 20000 when p < 0.01
    (smallest possible p 1/20001), so a Holm-surviving result is possible;
  - three conditioning sets: S (price-following state incl. focal-price flags, as in v1),
    S_nofocal (focal flags removed, so round-number codes are not absorbed), and S_game (S plus the game id,
    with the permutation done within game, so a game-specific code mapping is not cancelled by pooling);
  - the Holm family is every (cell, feature, conditioning set) in non-degenerate LLM-LLM cells
    (cells whose next-move target or odd/even feature is constant are excluded and listed);
  - power: planted codes in every treatment cell: a global parity mapping (tested with S), a per-game random
    parity mapping and a per-game random last-digit mapping (both tested with S_game);
  - arm-swap sign-flip permutation tests (within pair, 2000 draws) for the treatment-minus-control statistics.
"""
import os, sys
import numpy as np
import pandas as pd
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from price_channel import load_games, directions, cmi, within_perm, FOCAL, FEATS, CELLS, CONTRASTS

OUT = os.path.dirname(os.path.abspath(__file__))
MODES = ["S", "S_nofocal", "S_game"]
FCOL = dict(zip(FEATS, [6, 7, 8, 9]))


def transitions2(key, game, gid=0):
    rows = []
    q = game["q"]; rnd = q.index.to_numpy()
    for a, b in directions(key, game):
        A = q[a].to_numpy(); B = q[b].to_numpy()
        for t in range(1, len(A) - 1):
            if not (rnd[t] - rnd[t - 1] == 1 and rnd[t + 1] - rnd[t] == 1):
                continue
            dA = A[t] - A[t - 1]; dB = B[t] - B[t - 1]; dB1 = B[t + 1] - B[t]; mv = abs(dA)
            rows.append((int(np.sign(dB1)) + 1, int(np.sign(dA)) + 1, int(np.sign(dB)) + 1, int(np.sign(A[t] - B[t])) + 1,
                         int(A[t] in FOCAL), int(B[t] in FOCAL), int(A[t] % 2), int(A[t] % 10), int(A[t] % 5 == 0),
                         0 if mv == 0 else (1 if mv == 1 else (2 if mv <= 5 else 3)), gid))
    return np.array(rows, dtype=np.int64).reshape(-1, 11)


def zk(T, mode):
    base = T[:, 3] * 9 + T[:, 1] * 3 + T[:, 2]
    if mode == "S":
        return base * 4 + T[:, 4] * 2 + T[:, 5]
    if mode == "S_nofocal":
        return base
    return (base * 4 + T[:, 4] * 2 + T[:, 5]) * 64 + T[:, 10]


def ptest(T, f, mode, rng, n0=2000, n1=20000):
    y = T[:, 0]; x = T[:, FCOL[f]]; z = zk(T, mode)
    obs = cmi(y, x, z)
    null = np.array([cmi(y, within_perm(x, z, rng), z) for _ in range(n0)])
    p = (1 + (null >= obs - 1e-12).sum()) / (1 + n0)
    if p < 0.01:
        null = np.concatenate([null, [cmi(y, within_perm(x, z, rng), z) for _ in range(n1 - n0)]])
        p = (1 + (null >= obs - 1e-12).sum()) / (1 + n1)
    return obs, obs - null.mean(), null.std(), p, len(null)


def cell_job(args):
    key, gs, seed = args
    rng = np.random.default_rng(seed)
    T = np.vstack([transitions2(key, g, i) for i, g in enumerate(gs)])
    te = cmi(T[:, 0], T[:, 1], T[:, 2])
    tnull = np.array([cmi(T[:, 0], T[rng.permutation(len(T)), 1], T[:, 2]) for _ in range(2000)])
    degenerate = bool(len(np.unique(T[:, 0])) < 2 or len(np.unique(T[:, 6])) < 2)
    out = []
    for mode in MODES:
        for f in FEATS:
            obs, bc, sd, p, n = ptest(T, f, mode, rng)
            out.append(dict(cell=key, mode=mode, feature=f, n_trans=len(T), obs=obs, bc=bc, null_sd=sd, p=p, n_perm=n,
                            degenerate=degenerate, te_bc=te - tnull.mean(), te_p=(1 + (tnull >= te).sum()) / 2001))
    return out


def plant(T, f, rng, kind):
    T = T.copy(); k = rng.random(len(T)) < f
    if kind == "parity_global":
        T[k, 0] = np.where(T[k, 6] == 1, 2, 0)
    elif kind == "parity_pergame":
        flip = rng.random(T[:, 10].max() + 1) < 0.5
        T[k, 0] = np.where((T[k, 6] == 1) ^ flip[T[k, 10]], 2, 0)
    else:
        G = T[:, 10].max() + 1; M = rng.integers(0, 3, size=(G, 10))
        T[k, 0] = M[T[k, 10], T[k, 7]]
    return T


def power_job(args):
    key, gs, seed = args
    rng = np.random.default_rng(seed)
    T0 = np.vstack([transitions2(key, g, i) for i, g in enumerate(gs)])
    out = []
    for kind, f_, mode in [("parity_global", "parity", "S"), ("parity_pergame", "parity", "S_game"), ("digit_pergame", "digit", "S_game")]:
        for fr in [0.05, 0.1, 0.15, 0.2, 0.3]:
            det = 0; bits = []
            for _ in range(40):
                T = plant(T0, fr, rng, kind); y = T[:, 0]; x = T[:, FCOL[f_]]; z = zk(T, mode)
                obs = cmi(y, x, z); null = np.array([cmi(y, within_perm(x, z, rng), z) for _ in range(200)])
                det += (1 + (null >= obs).sum()) / 201 < 0.05; bits.append(obs - null.mean())
            out.append(dict(cell=key, planted=kind, test_mode=mode, fraction=fr, power=det / 40, mean_bc_bits=np.mean(bits)))
    return out


def stat_set(Ts):
    T = np.vstack(Ts); o = {"te": cmi(T[:, 0], T[:, 1], T[:, 2])}
    for f in FEATS:
        o["cmi_" + f] = cmi(T[:, 0], T[:, FCOL[f]], zk(T, "S"))
    return o


def contrast_job(args):
    name, tk, ck, gt, gc, seed = args
    rng = np.random.default_rng(seed)
    pairs = sorted(set(gt) & set(gc))
    Tt = {p: transitions2(tk, gt[p], i) for i, p in enumerate(pairs)}; Tc = {p: transitions2(ck, gc[p], i) for i, p in enumerate(pairs)}
    a = stat_set([Tt[p] for p in pairs]); b = stat_set([Tc[p] for p in pairs]); obs = {k: a[k] - b[k] for k in a}
    cnt = {k: 0 for k in obs}; N = 2000
    for _ in range(N):
        sw = rng.random(len(pairs)) < 0.5
        A_ = [Tc[p] if s else Tt[p] for p, s in zip(pairs, sw)]; B_ = [Tt[p] if s else Tc[p] for p, s in zip(pairs, sw)]
        a2 = stat_set(A_); b2 = stat_set(B_)
        for k in obs:
            cnt[k] += abs(a2[k] - b2[k]) >= abs(obs[k]) - 1e-12
    return [dict(contrast=name, metric=k, raw_diff=obs[k], perm_p_two_sided=(1 + cnt[k]) / (1 + N), n_pairs=len(pairs)) for k in obs]


if __name__ == "__main__":
    games = load_games()
    cg = {c[0]: games.get((c[1], c[2], c[3], c[4]), []) for c in CELLS}
    gaps = sum(1 for gs in cg.values() for g in gs if (np.diff(g["q"].index.to_numpy()) != 1).any())
    print("games with a missing round:", gaps, flush=True)
    with Pool(6) as pool:
        C = pd.DataFrame([r for part in pool.map(cell_job, [(k, cg[k], 100 + i) for i, k in enumerate(cg)]) for r in part])
        fam = C[(~C.cell.str.contains("copybot")) & (~C.degenerate)]
        ps = fam.p.to_numpy(); order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
        for rank, j in enumerate(order):
            run = max(run, min(1, (m - rank) * ps[j])); adj[j] = run
        C.loc[fam.index, "p_holm"] = adj
        C["holm_family_size"] = m
        C.to_csv(os.path.join(OUT, "price_codes_v2.csv"), index=False)
        print("family", m, "excluded degenerate:", sorted(set(C[C.degenerate].cell)), flush=True)
        print(C.sort_values("p").head(14)[["cell", "mode", "feature", "bc", "p", "n_perm", "p_holm"]].to_string(), flush=True)
        jobs = []
        for i, (name, tk, ck, fam_) in enumerate(CONTRASTS):
            gt = {g["pair"]: g for g in cg[tk]}; gc = {g["pair"]: g for g in cg[ck]}
            jobs.append((name, tk, ck, gt, gc, 500 + i))
        K = pd.DataFrame([r for part in pool.map(contrast_job, jobs) for r in part])
        K.to_csv(os.path.join(OUT, "price_contrast_perm_v2.csv"), index=False)
        print(K.round(4).to_string(), flush=True)
        treat = [c[0] for c in CELLS if c[5] == "treatment"]
        P = pd.DataFrame([r for part in pool.map(power_job, [(k, cg[k], 300 + i) for i, k in enumerate(treat)]) for r in part])
        P.to_csv(os.path.join(OUT, "price_power_v2.csv"), index=False)
        print(P.pivot_table(index=["cell", "planted"], columns="fraction", values="power").to_string(), flush=True)