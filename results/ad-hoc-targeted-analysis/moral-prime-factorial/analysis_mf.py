#!/usr/bin/env python3
"""Moral-prime factorial (EXPLORATORY, owner-approved 2026-10-26).  Qwen3-32B thinking on (qwen-t1) and gpt-oss-20b medium (oss-t1).
Cells: the new arms (VAL, LAW, MKT, NMM, RULE, BRULE, BONE = mf-b-one-l1 + -l2, CTLB, CTLP: concurrent re-runs of prime B and the placebo)
and the historical controls on the same (wording, seed) pairs (PB moral-prime-b, PA moral-prime, PL moral-placebo, HC headline-chat p1).
Five metrics per game from the market events (analysis_te.game_metrics; price index = market price = lowest quote, 0..1).
Paired on (wording, seed) within a model; 95% percentile bootstrap over pairs (10,000, seed 20261025); exact sign-flip p; Holm within each
named family, per model and metric.  Truncation reruns (superseded.csv) replace originals as in analysis_te.
Usage: python -X utf8 analysis_mf.py --runs <runs dir> --out <folder>"""
import argparse, glob, json, os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "temptation-ethics"))
import analysis_te as T   # noqa: E402

M = T.M
NQ, NO = "2026-10-26_trackm_moral_factorial", "2026-10-26_trackm_oss_moral_factorial"
OLDQ, OLDO = "2026-10-25_trackm_newarms_A", "2026-10-26_trackm_oss_neutral"
HCQ = "2026-10-25_trackm_neutral"
LABEL = {
    "VAL": "mf-values: values clause only", "LAW": "mf-law: law clause only", "MKT": "mf-market: market words only",
    "NMM": "mf-neutral-mm: neutral market-maker persona", "RULE": "mf-rule: ethics rule only", "BRULE": "mf-b-rule: prime B plus ethics rule",
    "BONE": "mf-b-one: prime B on one firm (other firm placebo)", "CTLB": "mf-ctl-b: prime B, concurrent re-run",
    "CTLP": "mf-ctl-placebo: garden placebo, concurrent re-run", "PB": "moral-prime-b: prime B, both firms (earlier run)",
    "PA": "moral-prime: prime A, both firms (earlier run)", "PL": "moral-placebo: garden placebo, both firms (earlier run)",
    "HC": "headline-chat: no seat note (earlier run)"}
SHORT = {"VAL": "values only", "LAW": "law only", "MKT": "market words only", "NMM": "neutral market maker", "RULE": "rule only",
         "BRULE": "prime B + rule", "BONE": "prime B on one firm", "CTLB": "prime B (concurrent)", "CTLP": "placebo (concurrent)",
         "PB": "prime B", "PA": "prime A", "PL": "placebo", "HC": "no seat note"}
SLUG = {"VAL": "mf-values", "LAW": "mf-law", "MKT": "mf-market", "NMM": "mf-neutral-mm", "RULE": "mf-rule", "BRULE": "mf-b-rule",
        "BONE": "mf-b-one", "CTLB": "mf-ctl-b", "CTLP": "mf-ctl-placebo", "PB": "moral-prime-b", "PA": "moral-prime", "PL": "moral-placebo",
        "HC": "headline-chat"}
MODEL = {"qwen-t1": "Qwen3-32B, thinking on", "oss-t1": "gpt-oss-20b, medium effort"}
SRC = {}
for mm, new, old, hc in (("qwen-t1", NQ, OLDQ, HCQ), ("oss-t1", NO, OLDO, OLDO)):
    for c, arm in (("VAL", "mf-values"), ("LAW", "mf-law"), ("MKT", "mf-market"), ("NMM", "mf-neutral-mm"), ("RULE", "mf-rule"),
                   ("BRULE", "mf-b-rule"), ("CTLB", "mf-ctl-b"), ("CTLP", "mf-ctl-placebo")):
        SRC[(mm, c)] = [(new, arm)]
    SRC[(mm, "BONE")] = [(new, "mf-b-one-l1"), (new, "mf-b-one-l2")]
    SRC[(mm, "PB")] = [(old, "moral-prime-b")]
    SRC[(mm, "PA")] = [(old, "moral-prime")]
    SRC[(mm, "PL")] = [(old, "moral-placebo")]
    SRC[(mm, "HC")] = [(hc, "headline-chat")]
FAMILIES = {
    "A. Each persona against the garden placebo": [("VAL", "PL"), ("LAW", "PL"), ("MKT", "PL"), ("NMM", "PL"), ("PB", "PL"), ("PA", "PL")],
    "B. Each single clause against full prime B": [("VAL", "PB"), ("LAW", "PB"), ("MKT", "PB"), ("NMM", "PB")],
    "C. Persona, rule, or both": [("RULE", "PL"), ("BRULE", "PL"), ("PB", "RULE"), ("BRULE", "PB"), ("BRULE", "RULE"),
                                  ("BRULE-PB", "RULE-PL")],
    "D. Dose: 0, 1 or 2 firms primed": [("BONE", "PL"), ("PB", "BONE")],
    "E. Within the new run, against the neutral market-maker persona": [("VAL", "NMM"), ("LAW", "NMM"), ("MKT", "NMM"), ("RULE", "NMM"),
                                                                         ("BRULE", "NMM"), ("BONE", "NMM")],
}


def load(runs):
    rows, seat_rows = [], []
    for (mm, cell), srcs in SRC.items():
        for root, arm in srcs:
            sup = T.supersessions(runs, root)
            for d in sorted(glob.glob(os.path.join(runs, root, "trials", arm, arm + "__p1__*__t1"))):
                b = os.path.basename(d); p = b.split("__")
                src = sup.get(b, d)
                if not os.path.exists(src + "/DONE"):
                    rows.append(dict(mm=mm, cell=cell, arm=arm, trial_id=b, status="not done")); continue
                ev, sr, tr, nq = T.events(src)
                m, _ = T.game_metrics(ev)
                par = json.load(open(os.path.join(src, "params.json"), encoding="utf-8"))
                rows.append(dict(mm=mm, cell=cell, arm=arm, trial_id=b, status="done", wording=p[2][1:], seed=p[3][1:], truncated_calls=tr,
                                 superseded=b in sup, model=par.get("model"), payoff_examples=par.get("payoff_examples"), **m))
                if cell == "BONE":
                    primed = "llm1" if arm.endswith("l1") else "llm2"
                    other = "llm2" if primed == "llm1" else "llm1"
                    q = {s: np.mean([e["prices"][s] for e in ev]) for s in (primed, other)}
                    seat_rows.append(dict(mm=mm, trial_id=b, wording=p[2][1:], seed=p[3][1:], primed_seat=primed,
                                          primed_quote=q[primed], unprimed_quote=q[other],
                                          primed_profit=np.mean([e["profits"][primed] for e in ev]),
                                          unprimed_profit=np.mean([e["profits"][other] for e in ev]),
                                          rounds_primed_above=sum(e["prices"][primed] > e["prices"][other] + 1e-9 for e in ev),
                                          rounds_primed_below=sum(e["prices"][primed] < e["prices"][other] - 1e-9 for e in ev),
                                          rounds_equal=sum(abs(e["prices"][primed] - e["prices"][other]) <= 1e-9 for e in ev)))
    return pd.DataFrame(rows), pd.DataFrame(seat_rows)


def run(G, mm, a, b, col):
    if "-" in a:
        t, r = a.split("-"); c, d = b.split("-")
        return T.contrast(G, mm, t, r, col, did=(c, d))
    return T.contrast(G, mm, a, b, col)


def lab(a, b):
    if "-" in a:
        return "interaction: (prime B + rule minus prime B) minus (rule only minus placebo)"
    return "%s: %s, minus %s: %s" % (SLUG[a], SHORT[a], SLUG[b], SHORT[b])


def boot_diff(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2:
        return len(x), np.nan, np.nan, np.nan, np.nan
    rng = np.random.default_rng(T.SEED); bm = x[rng.integers(0, len(x), (T.NB, len(x)))].mean(1)
    return len(x), x.mean(), np.percentile(bm, 2.5), np.percentile(bm, 97.5), T.signflip(x)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", required=True); ap.add_argument("--out", required=True)
    o = ap.parse_args(); os.makedirs(o.out, exist_ok=True)
    G, S = load(o.runs)
    G.to_csv(os.path.join(o.out, "game_level.csv"), index=False, float_format="%.6f")
    S.to_csv(os.path.join(o.out, "one_firm_seats.csv"), index=False, float_format="%.6f")
    D = G[G.status == "done"]
    summ = D.groupby(["mm", "cell"]).agg(n=("trial_id", "size"), truncated_games=("truncated_calls", lambda s: int((s > 0).sum())),
                                         **{c: (c, "mean") for c, _ in M}).reset_index()
    summ["label"] = summ.cell.map(LABEL)
    nd = G[G.status != "done"].groupby(["mm", "cell"]).size().rename("not_done").reset_index()
    summ = summ.merge(nd, how="left", on=["mm", "cell"]).fillna({"not_done": 0})
    summ.to_csv(os.path.join(o.out, "arm_means.csv"), index=False, float_format="%.4f")
    out = []
    for fam, cs in FAMILIES.items():
        for mm in MODEL:
            for col, cname in M:
                res = [(a, b, run(D, mm, a, b, col)) for a, b in cs]
                adj = T.holm([r["p"] if not np.isnan(r["p"]) else 1.0 for _, _, r in res])
                for (a, b, r), pa in zip(res, adj):
                    out.append(dict(family=fam, model=MODEL[mm], mm=mm, metric=cname, col=col, contrast=lab(a, b), a=a, b=b,
                                    n_pairs=r["n"], mean_a=r["t"], mean_b=r["r"], diff=r["d"], ci_lo=r["lo"], ci_hi=r["hi"],
                                    p_signflip=r["p"], p_holm=pa if not np.isnan(r["p"]) else np.nan))
    C = pd.DataFrame(out); C.to_csv(os.path.join(o.out, "paired_contrasts.csv"), index=False, float_format="%.4f")
    # one-firm arm: primed seat against the unprimed seat in the same game
    srows = []
    for mm in MODEL:
        s = S[S.mm == mm] if len(S) else S
        for k, name in (("quote", "mean quote (half-spread)"), ("profit", "mean profit per round")):
            n, d, lo, hi, p = boot_diff((s["primed_" + k] - s["unprimed_" + k]).to_numpy()) if len(s) else (0, np.nan, np.nan, np.nan, np.nan)
            srows.append(dict(model=MODEL[mm], quantity=name, n_games=n, primed_mean=s["primed_" + k].mean() if len(s) else np.nan,
                              unprimed_mean=s["unprimed_" + k].mean() if len(s) else np.nan, diff=d, ci_lo=lo, ci_hi=hi, p_signflip=p))
    pd.DataFrame(srows).to_csv(os.path.join(o.out, "one_firm_seat_contrast.csv"), index=False, float_format="%.4f")
    # prime B minus placebo on each new arm's own pairs (so "a fraction of prime B" compares like with like)
    rows = []
    for mm in MODEL:
        for c in ("VAL", "LAW", "MKT", "NMM", "RULE", "BRULE", "BONE"):
            keys = set(map(tuple, D[(D.mm == mm) & (D.cell == c)][["wording", "seed"]].astype(str).values))
            Dk = D[D[["wording", "seed"]].astype(str).apply(tuple, axis=1).isin(keys)]
            arm = T.contrast(Dk, mm, c, "PL", "price_index"); pb = T.contrast(Dk, mm, "PB", "PL", "price_index")
            rows.append(dict(model=MODEL[mm], arm=LABEL[c], n_pairs=arm["n"], arm_minus_placebo=arm["d"], primeB_minus_placebo_same_pairs=pb["d"],
                             pb_lo=pb["lo"], pb_hi=pb["hi"], ratio=arm["d"] / pb["d"] if pb["d"] else np.nan))
    pd.DataFrame(rows).to_csv(os.path.join(o.out, "primeB_on_same_pairs.csv"), index=False, float_format="%.4f")
    # sensitivity: drop every game with a truncated reply (finish_reason length)
    Dn = D[D.truncated_calls == 0]
    rows = []
    for fam, cs in FAMILIES.items():
        for mm in MODEL:
            for a_, b_ in cs:
                r = run(Dn, mm, a_, b_, "price_index")
                rows.append(dict(family=fam, model=MODEL[mm], contrast=lab(a_, b_), n_pairs=r["n"], diff=r["d"], ci_lo=r["lo"], ci_hi=r["hi"]))
    pd.DataFrame(rows).to_csv(os.path.join(o.out, "sensitivity_no_truncated.csv"), index=False, float_format="%.4f")
    # game length against price (why a stop that drops long games biases prices)
    rows = []
    for mm in MODEL:
        x = D[D.mm == mm]
        rows.append(dict(model=MODEL[mm], n_games=len(x), spearman_rounds_vs_price_index=x.rounds.rank().corr(x.price_index.rank())))
    pd.DataFrame(rows).to_csv(os.path.join(o.out, "length_vs_price.csv"), index=False, float_format="%.4f")
    # one-firm arm: how often the primed firm quotes above / below / equal to its rival (round by round)
    forest(C, o.out)
    print(summ.to_string()); print(pd.DataFrame(srows).to_string())


def forest(C, out):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "analysis_style"))
    import ci_forest
    for fam in FAMILIES:
        for mm in MODEL:
            F = C[(C.family == fam) & (C.mm == mm)]
            if F["diff"].isna().all():
                continue
            t = [dict(label=r.contrast, metric=r.metric, estimate=r["diff"], lo=r.ci_lo, hi=r.ci_hi, p=r.p_holm) for _, r in F.iterrows()
                 if not np.isnan(r["diff"])]
            fn = os.path.join(out, "forest_%s_%s.png" % (fam.split(".")[0], mm))
            ci_forest.forest(t, fn, title="%s. %s, private chat, penalty point 1, neutral payoff table; paired over (wording, seed); 95%% bootstrap CI"
                             % (fam, MODEL[mm]), xlabel="difference, first minus second")


if __name__ == "__main__":
    main()
