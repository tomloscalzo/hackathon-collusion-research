#!/usr/bin/env python3
"""fx-joint control: the joint-profit instruction under the formula payoff block (no printed example prices), Qwen3-32B and gpt-oss-20b,
plus the corrected gpt-oss formula / no-numbers arms (the formula-fix rerun), all thinking on.
All five standard metrics come from the `market` events of each trial's events.jsonl (same code as the copy-bot analysis):
  avg_abs_spread    mean market quote (best quote), raw units 1.00-5.00
  price_index       mean of clip((market price - 1)/2, 0, 1)
  profit_gain_index (mean per-firm profit per round - 1.00 profit) / (3.00 profit - 1.00 profit), from the engine's per-round profits
  competitive_share share of firm-rounds (round 2 on) below the lowest rival's previous quote, or both at 1.00
  matching_share    share of firm-rounds (round 2 on) equal (half a tick) to the lowest rival's previous quote, above 1.00
Pairs: (wording, seed). Paired 95% percentile bootstrap over pairs (10,000 resamples, seed 20261025); exact sign-flip test over pairs
when n <= 20 (else 200,000 random flips).
Usage: python -X utf8 fxj_analysis.py --runs <runs dir> --out <folder>"""
import argparse, collections, glob, itertools, json, os
import numpy as np
import pandas as pd

EPS, S0, SBAR, Q0, N = 0.005, 1.0, 5.0, 100.0, 2
rent = lambda s: (s - S0) * Q0 * max(0.0, 1 - s / SBAR)
NASH, MONO = rent(S0) / N, rent((S0 + SBAR) / 2) / N
M = [("avg_abs_spread", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
     ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
NB, SEED = 10000, 20261025

# cell name -> (run root relative to --runs, arm dir, trial-id prefix filter)
CELLS = {
    "Q fx-ctl-joint p3":        ("2026-10-25_trackm_fx_ctl_joint", "fx-ctl-joint", "fx-ctl-joint__p3__"),
    "Q ctl-32b-joint p3 (primed)": ("2026-10-25_trackm_neutral", "ctl-32b-joint", "ctl-32b-joint__p3__"),
    "Q fx-chat-p1":             ("2026-10-25_trackm_formula", "fx-chat-p1", "fx-chat-p1__p1__"),
    "Q headline-chat p3":       ("2026-10-25_trackm_neutral", "headline-chat", "headline-chat__p3__"),
    "O fx-ctl-joint p3":        ("2026-10-26_trackm_oss_fx_ctl_joint", "fx-ctl-joint", "fx-ctl-joint__p3__"),
    "O ctl-32b-joint p3 (primed)": ("2026-10-26_trackm_oss_neutral", "ctl-32b-joint", "ctl-32b-joint__p3__"),
    "O headline-chat p3":       ("2026-10-26_trackm_oss_neutral", "headline-chat", "headline-chat__p3__"),
    "O headline-chat p1":       ("2026-10-26_trackm_oss_neutral", "headline-chat", "headline-chat__p1__"),
    "O headline-tacit p1":      ("2026-10-26_trackm_oss_neutral", "headline-tacit", "headline-tacit__p1__"),
    "O headline-chat p5":       ("2026-10-26_trackm_oss_neutral", "headline-chat", "headline-chat__p5__"),
    "O G2 headline-chat p1":    ("2026-10-25_trackm_oss", "oss-headline-chat-p1", "oss-headline-chat-p1__p1__"),
    "O G2 headline-tacit p1":   ("2026-10-25_trackm_oss", "oss-headline-tacit-p1", "oss-headline-tacit-p1__p1__"),
    "O G2 headline-chat p5":    ("2026-10-25_trackm_oss", "oss-headline-chat-p5", "oss-headline-chat-p5__p5__"),
}
for a, p in (("fx-chat-p1", 1), ("fx-tacit-p1", 1), ("fx-chat-p5", 5), ("nx-chat-p1", 1), ("nx-tacit-p1", 1)):
    CELLS["O " + a] = ("2026-10-26_trackm_oss_formula_fix", a, "%s__p%d__" % (a, p))
# Qwen formula / no-numbers arms (from the formula run) for the cross-model view
for a, p in (("fx-tacit-p1", 1), ("fx-chat-p5", 5), ("nx-chat-p1", 1), ("nx-tacit-p1", 1)):
    CELLS["Q " + a] = ("2026-10-25_trackm_formula", a, "%s__p%d__" % (a, p))
CELLS["Q headline-chat p1"] = ("2026-10-25_trackm_neutral", "headline-chat", "headline-chat__p1__")
CELLS["Q headline-tacit p1"] = ("2026-10-25_trackm_neutral", "headline-tacit", "headline-tacit__p1__")
CELLS["Q headline-chat p5"] = ("2026-10-25_trackm_neutral", "headline-chat", "headline-chat__p5__")

X32K = {"2026-10-25_trackm_neutral": ["2026-10-25_trackm_neutral_x32k", "2026-10-25_trackm_neutral_x32k_b2"],
        "2026-10-25_trackm_formula": ["2026-10-25_trackm_formula_x32k"],
        "2026-10-25_trackm_fx_ctl_joint": ["2026-10-25_trackm_fx_ctl_joint_x32k"]}

CONTRASTS = [  # (group, treatment, reference, mismatch note)
    ("A", "Q fx-ctl-joint p3", "Q ctl-32b-joint p3 (primed)", "payoff block only (formula vs neutral example prices)"),
    ("A", "Q fx-ctl-joint p3", "Q fx-chat-p1", "joint-profit note added; penalty p3 (500) vs p1 (100); both formula, private chat"),
    ("A", "Q fx-ctl-joint p3", "Q headline-chat p3", "joint note added AND formula vs example prices; same point p3, private chat"),
    ("A", "O fx-ctl-joint p3", "O ctl-32b-joint p3 (primed)", "payoff block only (formula vs neutral example prices)"),
    ("A", "O fx-ctl-joint p3", "O fx-chat-p1", "joint-profit note added; penalty p3 (500) vs p1 (100); both formula (corrected rerun), private chat"),
    ("A", "O fx-ctl-joint p3", "O headline-chat p3", "joint note added AND formula vs example prices; same point p3, private chat"),
    ("B", "O fx-chat-p1", "O headline-chat p1", "payoff block: formula vs neutral example prices"),
    ("B", "O nx-chat-p1", "O headline-chat p1", "payoff block: none vs neutral example prices"),
    ("B", "O fx-tacit-p1", "O headline-tacit p1", "payoff block: formula vs neutral example prices"),
    ("B", "O nx-tacit-p1", "O headline-tacit p1", "payoff block: none vs neutral example prices"),
    ("B", "O fx-chat-p5", "O headline-chat p5", "payoff block: formula vs neutral example prices"),
    ("B2", "O fx-chat-p1", "O G2 headline-chat p1", "as B, against the first gpt-oss build's headline cell"),
    ("B2", "O nx-chat-p1", "O G2 headline-chat p1", "as B, against the first gpt-oss build's headline cell"),
    ("B2", "O fx-tacit-p1", "O G2 headline-tacit p1", "as B, against the first gpt-oss build's headline cell"),
    ("B2", "O nx-tacit-p1", "O G2 headline-tacit p1", "as B, against the first gpt-oss build's headline cell"),
    ("B2", "O fx-chat-p5", "O G2 headline-chat p5", "as B, against the first gpt-oss build's headline cell"),
    ("Q", "Q fx-chat-p1", "Q headline-chat p1", "Qwen reference: formula vs neutral example prices"),
    ("Q", "Q nx-chat-p1", "Q headline-chat p1", "Qwen reference: none vs neutral example prices"),
    ("Q", "Q fx-tacit-p1", "Q headline-tacit p1", "Qwen reference"),
    ("Q", "Q nx-tacit-p1", "Q headline-tacit p1", "Qwen reference"),
    ("Q", "Q fx-chat-p5", "Q headline-chat p5", "Qwen reference"),
]


def events(d):
    m = {}
    trunc = 0
    for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
        e = json.loads(line)
        if e.get("kind") == "market":
            m[e["round"]] = e
        elif e.get("finish_reason") == "length":
            trunc += 1
    return [m[r] for r in sorted(m)], trunc


def game_metrics(ev, seats=("llm1", "llm2")):
    comp = match = scored = 0
    prof, quotes = [], []
    for s in seats:
        for i, e in enumerate(ev):
            prof.append(e["profits"][s]); quotes.append(e["prices"][s])
            if i == 0:
                continue
            q = e["prices"][s]
            tgt = min(v for k, v in ev[i - 1]["prices"].items() if k != s)
            scored += 1
            if q < tgt - EPS or (tgt <= S0 + EPS and q <= S0 + EPS):
                comp += 1
            elif abs(q - tgt) <= EPS:
                match += 1
    mp = [e["market_price"] for e in ev]
    return dict(rounds=len(ev), avg_abs_spread=np.mean(mp), price_index=np.mean([min(1, max(0, (p - 1) / 2)) for p in mp]),
                profit_gain_index=(np.mean(prof) - NASH) / (MONO - NASH),
                competitive_share=comp / scored if scored else np.nan, matching_share=match / scored if scored else np.nan), quotes


def load(runs):
    rows, Q = [], {}
    for cell, (root, arm, pre) in CELLS.items():
        qs = []
        for d in sorted(glob.glob(os.path.join(runs, root, "trials", arm, pre + "*"))):
            b = os.path.basename(d); p = b.split("__")
            if len(p) != 5 or p[4] != "t1" or not os.path.exists(d + "/DONE"):
                continue
            src = d; sup = ""
            for xr in X32K.get(root, []):   # 32k-cap supersession: a DONE __x32k rerun replaces the truncated original
                xd = os.path.join(runs, xr, "trials", arm, b + "__x32k")
                if os.path.exists(xd + "/DONE"):
                    src = xd; sup = xr
            ev, tr = events(src)
            m, q = game_metrics(ev)
            rows.append(dict(cell=cell, trial_id=b, wording=p[2][1:], seed=p[3][1:], truncated_calls=tr, superseded_by=sup, **m)); qs += q
        Q[cell] = qs
    return pd.DataFrame(rows), Q


def signflip(x, rng):
    n = len(x)
    if n <= 20:
        s = np.array(list(itertools.product([1, -1], repeat=n)))
    else:
        s = rng.choice([1, -1], size=(200000, n))
    return float((np.abs((s * x).mean(1)) >= abs(x.mean()) - 1e-12).mean())


def contrast(G, t, r):
    a = G[G.cell == t].set_index(["wording", "seed"]); b = G[G.cell == r].set_index(["wording", "seed"])
    idx = a.index.intersection(b.index)
    out = dict(n=len(idx))
    rng = np.random.default_rng(SEED)
    for col, _ in M:
        x = (a.loc[idx, col] - b.loc[idx, col]).dropna().to_numpy()
        if len(x) < 2:
            out.update({col + k: np.nan for k in ("_t", "_r", "_d", "_lo", "_hi", "_p")}); continue
        bm = x[rng.integers(0, len(x), (NB, len(x)))].mean(1)
        out.update({col + "_t": a.loc[idx, col].mean(), col + "_r": b.loc[idx, col].mean(), col + "_d": x.mean(),
                    col + "_lo": np.percentile(bm, 2.5), col + "_hi": np.percentile(bm, 97.5), col + "_p": signflip(x, rng) if len(x) <= 20 else signflip(x, rng)})
    return out


def dist(qs):
    if not qs:
        return {}
    c = collections.Counter(round(q, 2) for q in qs); n = len(qs)
    bins = [("1.00", 1.0, 1.0), ("1.01-1.49", 1.01, 1.49), ("1.50-1.99", 1.5, 1.99), ("2.00-2.49", 2.0, 2.49), ("2.50-2.99", 2.5, 2.99),
            ("3.00", 3.0, 3.0), ("3.01-5.00", 3.01, 5.0)]
    d = dict(n_quotes=n, mean_quote=float(np.mean(qs)), median_quote=float(np.median(qs)))
    for name, lo, hi in bins:
        d["share_" + name] = sum(v for k, v in c.items() if lo - 1e-9 <= k <= hi + 1e-9) / n
    d["share_on_0.50_steps"] = sum(v for k, v in c.items() if abs(k * 2 - round(k * 2)) < 1e-9) / n
    d["share_on_0.10_steps"] = sum(v for k, v in c.items() if abs(k * 10 - round(k * 10)) < 1e-9) / n
    d["top_values"] = "; ".join("%.2f (%.0f%%)" % (k, 100 * v / n) for k, v in c.most_common(5))
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    G, Q = load(a.runs)
    G.to_csv(os.path.join(a.out, "game_metrics.csv"), index=False, float_format="%.6f")
    cells = G.groupby("cell").agg(n_games=("trial_id", "size"), truncated_calls=("truncated_calls", "sum"),
                                  mean_rounds=("rounds", "mean"), **{c: (c, "mean") for c, _ in M}).reset_index()
    cells.to_csv(os.path.join(a.out, "cell_means.csv"), index=False, float_format="%.4f")
    rows = []
    for g, t, r, note in CONTRASTS:
        rows.append(dict(group=g, treatment=t, reference=r, note=note, **contrast(G, t, r)))
    pd.DataFrame(rows).to_csv(os.path.join(a.out, "paired_contrasts.csv"), index=False, float_format="%.6f")
    pd.DataFrame([dict(cell=c, **dist(Q[c])) for c in CELLS if Q.get(c)]).to_csv(os.path.join(a.out, "quote_distribution.csv"), index=False, float_format="%.4f")
    print(cells.to_string())


if __name__ == "__main__":
    main()
