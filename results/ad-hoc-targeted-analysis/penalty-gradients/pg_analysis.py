"""Penalty gradients: does the fine's effect depend on model, thinking, communication,
payoff block and objective, and do the levers compose additively?

Post-processing only. Inputs (paths passed on the command line, not stored here):
  --oss   gpt-oss-20b Step 1 run.csv (neutral wave set; hrep-* rows are excluded)
  --qwen  Qwen3-32B rated run.csv (neutral run rows are used)
  --fxj   results/ad-hoc-targeted-analysis/fx-joint-control/game_metrics.csv
          (Qwen formula cells fx-chat-p1, fx-chat-p5, fx-ctl-joint, thinking on,
          with the 32k-cap supersession already applied)
  --out   output folder for the CSVs

Every contrast is paired on (wording, seed): 95% percentile bootstrap over pairs
(10,000 resamples) and an exact two-sided sign-flip test (all 2^n patterns for n <= 20).
Holm is applied within each named family, separately per metric.
"""
import argparse
import itertools
import os

import numpy as np
import pandas as pd

METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share (U16)"),
           ("matching_share", "Matching share")]
MK = [m for m, _ in METRICS]
NB, SEED = 10000, 20261025
# pre-sprint model (results/ad-hoc-targeted-analysis/model-vs-llm/theory_curve.csv, N = 2)
THETA = {1: 0.7029, 2: 0.6262, 3: 0.5459, 4: 0.3249, 5: 0.0}
SSTAR = {1: 2.406, 2: 2.252, 3: 2.092, 4: 1.650, 5: 1.0}
PGI = {1: 0.9117, 2: 0.8603, 3: 0.7938, 4: 0.5442, 5: 0.0}
CSH = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.0}
MSH = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 0.0}
THEORY = {"market_price_mean": SSTAR, "price_index": THETA, "profit_gain_index": PGI,
          "competitive_share": CSH, "matching_share": MSH}

OBJ = {"ctl-32b-joint": "joint", "m-inc-joint": "joint-inc", "m-inc-target": "target", "fx-ctl-joint": "joint",
       "ctl-32b-compete": "compete"}


def load(a):
    o = pd.read_csv(a.oss, low_memory=False)
    o = o[(o.status == "done") & ~o.arm.str.startswith("hrep-")].copy()
    o["model"], o["mode"] = "gpt-oss-20b", "t1"
    q = pd.read_csv(a.qwen, low_memory=False)
    q = q[q.run.isin(["neutral", "anchored"]) & (q.status == "done")].copy()
    q["payoff_examples"] = q.run  # neutral or anchored example table
    q["model"] = "Qwen3-32B"
    q["mode"] = q.thinking.map({"on": "t1", "off": "t0"})
    keep = ["model", "mode", "arm", "payoff_examples", "communication", "penalty_point", "wording", "seed"] + MK
    G = pd.concat([o[keep], q[keep]], ignore_index=True)
    f = pd.read_csv(a.fxj)
    f = f[f.cell.isin(["Q fx-chat-p1", "Q fx-chat-p5", "Q fx-ctl-joint p3"])].copy()
    f["arm"] = f.cell.str.split().str[1]
    f["penalty_point"] = f.arm.map({"fx-chat-p1": 1, "fx-chat-p5": 5, "fx-ctl-joint": 3})
    f["model"], f["mode"], f["payoff_examples"], f["communication"] = "Qwen3-32B", "t1", "formula", "private"
    f = f.rename(columns={"avg_abs_spread": "market_price_mean"})
    G = pd.concat([G, f[keep]], ignore_index=True)
    G["objective"] = G.arm.map(OBJ).fillna("default")
    G["chain"] = G.arm.replace({"fx-chat-p1": "fx-chat", "fx-chat-p5": "fx-chat"})
    an = G.payoff_examples.eq("anchored")
    G.loc[an, "chain"] = G.loc[an, "chain"] + "@anchored"
    G["pair"] = G.wording.astype(int).astype(str) + "_" + G.seed.astype(int).astype(str)
    return G


def cell(G, model, mode, chain, pp):
    d = G[(G.model == model) & (G["mode"] == mode) & (G.chain == chain) & (G.penalty_point == pp)]
    return d.set_index("pair")[MK]


_SIGNS = {}


def signflip(x):
    n = len(x)
    if n not in _SIGNS:
        _SIGNS[n] = np.array(list(itertools.product([1.0, -1.0], repeat=n)), dtype=np.float64)
    s = _SIGNS[n]
    x = np.asarray(x, dtype=np.float64)
    obs = abs(x.sum())
    # float64 with a relative tolerance, so the observed sign pattern always counts (min p = 2 / 2^n)
    return float((np.abs(s @ x) >= obs * (1 - 1e-9) - 1e-12).mean())


def boot(x, rng):
    idx = rng.integers(0, len(x), size=(NB, len(x)))
    m = x[idx].mean(1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def contrast(parts, rng):
    """parts: list of (weight, DataFrame indexed by pair). Returns per-metric stats on the
    pair-wise linear combination sum(w * cell)."""
    common = sorted(set.intersection(*[set(p.index) for _, p in parts]))
    out = {"n_pairs": len(common)}
    for m in MK:
        x = sum(w * p.loc[common, m].values for w, p in parts)
        lo, hi = boot(x, rng)
        out.update({f"{m}_d": x.mean(), f"{m}_lo": lo, f"{m}_hi": hi, f"{m}_p": signflip(x)})
    return out


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, (len(p) - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def add_holm(df):
    for fam, idx in df.groupby("family").groups.items():
        for m in MK:
            df.loc[idx, f"{m}_holm"] = holm(df.loc[idx, f"{m}_p"].values)
    return df


def theory_diff(m, parts_pp):
    return sum(w * THEORY[m][pp] for w, pp in parts_pp)


CHAINS = [  # (model, mode, chain arm, payoff, communication, points)
    ("Qwen3-32B", "t0", "headline-tacit", "neutral", "no chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "headline-tacit", "neutral", "no chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t0", "headline-chat", "neutral", "private chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "headline-chat", "neutral", "private chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t0", "headline-monitored", "neutral", "monitored chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "headline-monitored", "neutral", "monitored chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "fx-chat", "formula", "private chat", [1, 5]),
    ("gpt-oss-20b", "t1", "headline-tacit", "neutral", "no chat", [1, 5]),
    ("gpt-oss-20b", "t1", "headline-chat", "neutral", "private chat", [1, 3, 5]),
    ("gpt-oss-20b", "t1", "fx-chat", "formula", "private chat", [1, 5]),
    ("Qwen3-32B", "t0", "headline-tacit@anchored", "anchored", "no chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "headline-tacit@anchored", "anchored", "no chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t0", "headline-chat@anchored", "anchored", "private chat", [1, 3, 4, 5]),
    ("Qwen3-32B", "t1", "headline-chat@anchored", "anchored", "private chat", [1, 3, 4, 5]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oss", required=True)
    ap.add_argument("--qwen", required=True)
    ap.add_argument("--fxj", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    G = load(a)
    os.makedirs(a.out, exist_ok=True)

    # cell means
    cm = (G.groupby(["model", "mode", "arm", "payoff_examples", "communication", "objective", "penalty_point"])[MK]
          .agg(["mean", "count"]))
    cm.columns = [f"{m}_{s}" for m, s in cm.columns]
    cm = cm.reset_index()
    cm["theta_star"] = cm.penalty_point.map(THETA)
    cm.to_csv(os.path.join(a.out, "cell_means.csv"), index=False, float_format="%.4f")

    rows = []

    def add(family, label, model, mode, parts, parts_pp, note=""):
        r = contrast(parts, rng)
        r.update(family=family, contrast=label, model=model, mode=mode, note=note)
        for m in MK:
            r[f"{m}_theory"] = theory_diff(m, parts_pp) if parts_pp else np.nan
        rows.append(r)

    # Family S: penalty slopes (steps and p5 - p1) per chain
    for model, mode, ch, pay, comm, pts in CHAINS:
        C = {pp: cell(G, model, mode, ch, pp) for pp in pts}
        steps = list(zip(pts[:-1], pts[1:]))
        if (1, 5) not in steps:
            steps.append((1, 5))
        for lo_, hi_ in steps:
            fam = "S: p5 - p1 slopes" if (lo_, hi_) == (1, 5) else "S-steps: adjacent-step slopes"
            add(fam, f"{ch} ({pay}, {comm}): p{hi_} - p{lo_}", model, mode,
                [(1, C[hi_]), (-1, C[lo_])], [(1, hi_), (-1, lo_)])

    # Family I: interactions (difference in the p5 - p1 slope), within pair
    def sl(model, mode, ch, hi_=5, lo_=1):
        return [(1, cell(G, model, mode, ch, hi_)), (-1, cell(G, model, mode, ch, lo_))]

    def neg(parts):
        return [(-w, p) for w, p in parts]

    for ch in ["headline-tacit", "headline-chat", "headline-monitored"]:
        add("I: slope interactions", f"thinking x penalty, {ch}: slope(t1) - slope(t0)", "Qwen3-32B", "t1-t0",
            sl("Qwen3-32B", "t1", ch) + neg(sl("Qwen3-32B", "t0", ch)), None)
    for model, mode in [("Qwen3-32B", "t0"), ("Qwen3-32B", "t1"), ("gpt-oss-20b", "t1")]:
        add("I: slope interactions", "chat x penalty: slope(headline-chat) - slope(headline-tacit)", model, mode,
            sl(model, mode, "headline-chat") + neg(sl(model, mode, "headline-tacit")), None)
    for mode in ["t0", "t1"]:
        add("I: slope interactions", "monitoring notice x penalty: slope(headline-monitored) - slope(headline-chat)",
            "Qwen3-32B", mode, sl("Qwen3-32B", mode, "headline-monitored") + neg(sl("Qwen3-32B", mode, "headline-chat")), None)
    for model in ["Qwen3-32B", "gpt-oss-20b"]:
        add("I: slope interactions", "formula x penalty: slope(fx-chat) - slope(headline-chat)", model, "t1",
            sl(model, "t1", "fx-chat") + neg(sl(model, "t1", "headline-chat")), None)
    for mode in ["t0", "t1"]:
        for ch in ["headline-tacit", "headline-chat"]:
            add("I: slope interactions", f"anchored table x penalty, {ch}: slope(anchored) - slope(neutral)", "Qwen3-32B", mode,
                sl("Qwen3-32B", mode, ch + "@anchored") + neg(sl("Qwen3-32B", mode, ch)), None)
    for ch in ["headline-tacit", "headline-chat", "fx-chat"]:
        add("I: slope interactions", f"model x penalty, {ch}: slope(gpt-oss) - slope(Qwen t1)", "gpt-oss - Qwen", "t1",
            sl("gpt-oss-20b", "t1", ch) + neg(sl("Qwen3-32B", "t1", ch)), None)
    add("I: slope interactions", "model x penalty, headline-chat p3 - p1: gpt-oss - Qwen t1", "gpt-oss - Qwen", "t1",
        sl("gpt-oss-20b", "t1", "headline-chat", 3, 1) + neg(sl("Qwen3-32B", "t1", "headline-chat", 3, 1)), None)

    # Family O: objectives at p3 (the only penalty point at which they were run)
    for model, mode in [("Qwen3-32B", "t0"), ("Qwen3-32B", "t1"), ("gpt-oss-20b", "t1")]:
        d3 = cell(G, model, mode, "headline-chat", 3)
        d1 = cell(G, model, mode, "headline-chat", 1)
        for arm in ["ctl-32b-joint", "m-inc-joint", "m-inc-target", "ctl-32b-compete"]:
            t = cell(G, model, mode, arm, 3)
            add("O: objective vs default", f"{arm} p3 - headline-chat p3", model, mode, [(1, t), (-1, d3)], None)
            if arm != "ctl-32b-compete":
                add("O1: objective at p3 vs default at p1", f"{arm} p3 - headline-chat p1", model, mode, [(1, t), (-1, d1)], None)
    for mode in ["t0", "t1"]:   # anchored table (prints 2.09): exact p3 contrasts, no bracket needed
        da3 = cell(G, "Qwen3-32B", mode, "headline-chat@anchored", 3)
        for arm in ["ctl-32b-joint", "m-inc-joint", "m-inc-target"]:
            ta = cell(G, "Qwen3-32B", mode, arm + "@anchored", 3)
            add("O-anch: objective vs default, anchored table", f"{arm} p3 - headline-chat p3 (anchored table)", "Qwen3-32B", mode,
                [(1, ta), (-1, da3)], None)
        j, d3 = cell(G, "Qwen3-32B", mode, "ctl-32b-joint", 3), cell(G, "Qwen3-32B", mode, "headline-chat", 3)
        ja = cell(G, "Qwen3-32B", mode, "ctl-32b-joint@anchored", 3)
        add("C: joint x payoff block", "(ctl-32b-joint - headline-chat p3) anchored - (same) neutral", "Qwen3-32B", mode,
            [(1, ja), (-1, da3), (-1, j), (1, d3)], None, "exact: both tables have p3 default cells")
    for model in ["Qwen3-32B", "gpt-oss-20b"]:
        t = cell(G, model, "t1", "fx-ctl-joint", 3)
        f1, f5 = cell(G, model, "t1", "fx-chat", 1), cell(G, model, "t1", "fx-chat", 5)
        add("O: objective vs default", "fx-ctl-joint p3 - fx-chat-p1 (bracket: lighter fine)", model, "t1", [(1, t), (-1, f1)], None)
        add("O: objective vs default", "fx-ctl-joint p3 - fx-chat-p5 (bracket: heavier fine)", model, "t1", [(1, t), (-1, f5)], None)
        j, d3 = cell(G, model, "t1", "ctl-32b-joint", 3), cell(G, model, "t1", "headline-chat", 3)
        # composability of the joint instruction with the formula block (bracketed, see report)
        add("C: joint x payoff block", "(fx-ctl-joint - fx-chat-p1) - (ctl-32b-joint - headline-chat p3)", model, "t1",
            [(1, t), (-1, f1), (-1, j), (1, d3)], None, "lower bound of the joint effect under formula if p3 lies between p1 and p5")
        add("C: joint x payoff block", "(fx-ctl-joint - fx-chat-p5) - (ctl-32b-joint - headline-chat p3)", model, "t1",
            [(1, t), (-1, f5), (-1, j), (1, d3)], None, "upper bound")

    R = add_holm(pd.DataFrame(rows))
    R.to_csv(os.path.join(a.out, "contrasts.csv"), index=False, float_format="%.6g")

    # Heed coefficients: within-pair OLS of each metric on theta*(penalty point), per chain
    hrows = []
    for model, mode, ch, pay, comm, pts in CHAINS:
        C = {pp: cell(G, model, mode, ch, pp) for pp in pts}
        common = sorted(set.intersection(*[set(c.index) for c in C.values()]))
        x = np.array([THETA[pp] for pp in pts])
        xc = x - x.mean()
        r = dict(model=model, mode=mode, chain=ch, payoff=pay, communication=comm,
                 points="/".join(f"p{p}" for p in pts), n_pairs=len(common))
        for m in MK:
            Y = np.column_stack([C[pp].loc[common, m].values for pp in pts])
            b_pair = (Y - Y.mean(1, keepdims=True)) @ xc / (xc @ xc)
            lo, hi = boot(b_pair, rng)
            r.update({f"beta_{m}": b_pair.mean(), f"beta_{m}_lo": lo, f"beta_{m}_hi": hi})
        # proportional response: 1 - PI(p5) / PI(p1), ratio of pair means, bootstrap over pairs
        p1, p5 = C[1].loc[common, "price_index"].values, C[5].loc[common, "price_index"].values
        idx = rng.integers(0, len(common), size=(NB, len(common)))
        rb = 1 - p5[idx].mean(1) / p1[idx].mean(1)
        r.update(prop=1 - p5.mean() / p1.mean(), prop_lo=np.percentile(rb, 2.5), prop_hi=np.percentile(rb, 97.5))
        # per-step response per unit of theory price index (first vs last step)
        st = list(zip(pts[:-1], pts[1:]))
        if len(st) >= 2:
            (a0, a1), (b0, b1) = st[0], st[-1]
            e = (C[a1].loc[common, "price_index"].values - C[a0].loc[common, "price_index"].values) / (THETA[a1] - THETA[a0])
            l_ = (C[b1].loc[common, "price_index"].values - C[b0].loc[common, "price_index"].values) / (THETA[b1] - THETA[b0])
            for nm, v in (("early", e), ("late", l_), ("late_minus_early", l_ - e)):
                lo, hi = boot(v, rng)
                r.update({f"heed_{nm}": v.mean(), f"heed_{nm}_lo": lo, f"heed_{nm}_hi": hi})
            r["heed_late_minus_early_p"] = signflip(l_ - e)
            r["early_step"], r["late_step"] = f"p{a0}->p{a1}", f"p{b0}->p{b1}"
        hrows.append(r)
    pd.DataFrame(hrows).to_csv(os.path.join(a.out, "heed_coefficients.csv"), index=False, float_format="%.4f")

    # joint-profit optimum check: value of quoting s every round, both firms, net of the
    # expected fine and the game-ending risk (continuation 0.95), per firm
    s = np.round(np.arange(1.0, 5.0001, 0.01), 2)
    jr = []
    for F in [0, 100, 500, 1000, 2000]:
        for dlt in [0.0, 0.95]:
            h = np.minimum(1, 0.025 * (s - 1))
            V = ((s - 1) * 50 * (1 - s / 5) - h * F) / (1 - dlt * (1 - h))
            i = int(V.argmax())
            jr.append(dict(fine=F, continuation=dlt, s_opt=s[i], price_index_opt=(s[i] - 1) / 2))
    pd.DataFrame(jr).to_csv(os.path.join(a.out, "joint_optimum.csv"), index=False, float_format="%.4f")
    used = {c[2] for c in CHAINS} | set(OBJ)
    G[G.chain.isin(used)].to_csv(os.path.join(a.out, "games_used.csv"), index=False, float_format="%.6f")
    print(len(G), "games;", len(R), "contrasts")


if __name__ == "__main__":
    main()
