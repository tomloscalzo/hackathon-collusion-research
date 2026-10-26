#!/usr/bin/env python3
"""Copy-bot control: the five standard metrics for one LLM firm against a scripted copier vs the LLM-vs-LLM headline tacit cell.
All metrics come from the `market` events (the quotes) of each trial's events.jsonl, NOT from collect.py per-round rows (blank for scripted
seats) or run_csv.py (treats a scripted seat as the n3 cheater).
Usage: python -X utf8 copybot_analysis.py --copy-trials <copybot trials dir> --headline-trials <headline-tacit trials dir>
                                          --scripted-games scripted_copybot_games.csv --out <this folder>
Pairs: (wording, seed, thinking). Paired 95% percentile bootstrap over pairs (10,000 resamples, seed 20261025); exact sign-flip test over pairs."""
import argparse, glob, itertools, json, os
from pathlib import Path
import numpy as np
import pandas as pd

EPS, S0, SBAR, Q0, N = 0.005, 1.0, 5.0, 100.0, 2
rent = lambda s: (s - S0) * Q0 * max(0.0, 1 - s / SBAR)
NASH, MONO = rent(S0) / N, rent((S0 + SBAR) / 2) / N      # per-firm profit at 1.00 and at 3.00 (same formula as baseline_bot.benchmarks)
M = [("avg_abs_spread", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
     ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
NB, SEED = 10000, 20261025


def events(d):
    m = {}
    for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
        e = json.loads(line)
        if e["kind"] == "market":
            m[e["round"]] = e
    return [m[r] for r in sorted(m)]


def seat_metrics(ev, seats):
    """Per game, pooled over the given seats (one LLM seat for a copier game, both seats for a headline game)."""
    comp = match = scored = 0
    prof = []
    for s in seats:
        for i, e in enumerate(ev):
            prof.append(e["profits"][s])
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
                competitive_share=comp / scored if scored else np.nan, matching_share=match / scored if scored else np.nan)


def parse(t):  # arm__p1__w0__s118__t0
    p = t.split("__")
    return p[0], p[2][1:], p[3][1:], p[4][1:]


def games(copy_dir, head_dir):
    rows = []
    for d in sorted(glob.glob(copy_dir + "/*/*")):
        if os.path.exists(d + "/DONE"):
            arm, w, s, t = parse(os.path.basename(d))
            rows.append(dict(kind="copier", arm=arm, wording=w, seed=s, thinking=t, **seat_metrics(events(d), ["llm1"])))
    for d in sorted(glob.glob(head_dir + "/headline-tacit__p1__*")):
        if os.path.exists(d + "/DONE"):
            arm, w, s, t = parse(os.path.basename(d))
            rows.append(dict(kind="headline", arm=arm, wording=w, seed=s, thinking=t, **seat_metrics(events(d), ["llm1", "llm2"])))
    return pd.DataFrame(rows)


def boot(x, rng):
    b = x[rng.integers(0, len(x), (NB, len(x)))].mean(1)
    return np.percentile(b, 2.5), np.percentile(b, 97.5)


def signflip(x):
    """Exact two-sided sign-flip permutation test on paired differences (enumerates 2^n sign patterns)."""
    signs = np.array(list(itertools.product([1, -1], repeat=len(x))))
    return float((np.abs((signs * x).mean(1)) >= abs(x.mean()) - 1e-12).mean())


def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); run = 0
    for r, i in enumerate(o):
        run = max(run, (len(ps) - r) * ps[i]); adj[i] = min(1, run)
    return adj


def shares(qa, qb):
    comp = match = n = 0
    for me, riv in ((qa, qb), (qb, qa)):
        for i in range(1, len(me)):
            n += 1
            if me[i] < riv[i - 1] - EPS or (riv[i - 1] <= S0 + EPS and me[i] <= S0 + EPS):
                comp += 1
            elif abs(me[i] - riv[i - 1]) <= EPS:
                match += 1
    return (comp / n, match / n) if n else (np.nan, np.nan)


def scripted(path, out):
    s = pd.read_csv(path)
    rows = []
    for _, x in s.iterrows():
        qa = [float(v) for v in str(x.quotes_A).split()]; qb = [float(v) for v in str(x.quotes_B).split()]
        cs, ms = shares(qa, qb)   # quote strings store at most the first 12 rounds
        pgi = (rent(x.mean_inside) / N - NASH) / (MONO - NASH) if x.variant == "fixed" else np.nan  # exact only when both quotes tie every round
        rows.append(dict(variant=x.variant, open_A=x.open_A, open_B=x.open_B, rounds=x.rounds, ended=int(x.status != "HORIZON"), distinct=x.n_distinct_quotes,
                         avg_abs_spread=x.mean_inside, price_index=x.price_index, profit_gain_index=pgi, competitive_share=cs, matching_share=ms))
    d = pd.DataFrame(rows)
    d["start"] = np.where(d.variant == "fixed", d.open_A.map("{:.2f}".format), "random " + d.open_A.map("{:.2f}".format) + " / " + d.open_B.map("{:.2f}".format))
    ref = d.groupby(["variant", "start"], sort=False).agg(games=("rounds", "size"), mean_rounds=("rounds", "mean"), games_one_distinct_quote=("distinct", lambda v: int((v == 1).sum())),
        games_ended_by_investigation=("ended", "sum"), avg_abs_spread=("avg_abs_spread", "mean"), price_index=("price_index", "mean"),
        profit_gain_index=("profit_gain_index", "mean"), competitive_share=("competitive_share", "mean"), matching_share=("matching_share", "mean")).reset_index()
    ref.round(4).to_csv(out / "scripted_reference.csv", index=False)
    return ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy-trials", required=True); ap.add_argument("--headline-trials", required=True)
    ap.add_argument("--scripted-games", required=True); ap.add_argument("--out", default=".")
    a = ap.parse_args(); out = Path(a.out)
    g = games(a.copy_trials, a.headline_trials)
    g.round(5).to_csv(out / "copybot_game_metrics.csv", index=False)
    rng = np.random.default_rng(SEED)
    rows = []
    for arm, t in [("copybot-o250-tacit", "0"), ("copybot-o250-tacit", "1"), ("copybot-o150-tacit", "0"), ("copybot-o150-tacit", "1")]:
        c = g[(g.arm == arm) & (g.thinking == t)].set_index(["wording", "seed"])
        h = g[(g.kind == "headline") & (g.thinking == t)].set_index(["wording", "seed"])
        for k, name in M:
            j = pd.concat([c[k].rename("c"), h[k].rename("h")], axis=1, join="inner").dropna()
            d = (j.c - j.h).values
            lo, hi = boot(d, rng)
            rows.append(dict(opening="2.50" if "o250" in arm else "1.50", thinking="on" if t == "1" else "off", metric=k, metric_name=name, n_pairs=len(d),
                             copier_mean=j.c.mean(), headline_mean=j.h.mean(), diff=d.mean(), ci_lo=lo, ci_hi=hi, p_signflip=signflip(d)))
    r = pd.DataFrame(rows)
    r["p_holm_within_metric"] = np.nan
    for k, _ in M:
        m = r.metric == k
        r.loc[m, "p_holm_within_metric"] = holm(r.loc[m, "p_signflip"].values)
    r.round(5).to_csv(out / "standard_metrics.csv", index=False)
    print(r.round(3).to_string()); print(scripted(a.scripted_games, out).round(3).to_string())


if __name__ == "__main__":
    main()
