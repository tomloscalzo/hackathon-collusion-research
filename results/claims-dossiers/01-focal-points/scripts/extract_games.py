"""Dossier 01 (focal points): independent per-game extraction from the raw game logs.

For every game used in this dossier, read the trial's events.jsonl and compute, with this file's own code:
  the five standard metrics (average absolute spread, price index, profit gain index, competitive share, matching share),
  per-quote focal-point shares (exact on a printed example price, 1 to 3 ticks under one, etc.),
  the first quote prompt's input-token count (prompt-length confound),
  and a keyword count of reasoning passages that evaluate the demand formula with numbers (unvalidated).
The game lists come from the frozen Step 1 tables (run.csv) of each run; the formula / no-numbers and fx-ctl-joint games of
Qwen3-32B, which are not in the Qwen run.csv, are read from their own run roots (32k truncation reruns substitute their
originals as listed in the root's superseded.csv).
Usage: python -X utf8 extract_games.py <hackathon_dir> <out_dir>
"""
import csv, json, os, re, sys, collections
try:
    import psutil
    psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
import pandas as pd

HK, OUT = sys.argv[1], sys.argv[2]
RUNS = os.path.join(HK, "runs")
WS = os.path.join(HK, "work_scratch")
OSS_RUN = os.path.join(WS, "oss_analysis", "step1", "final_t2", "run.csv")
FINAL_RUN = os.path.join(WS, "analysis_final", "run_csv", "run.csv")   # the FINAL Qwen table (neutral and anchored rows)

NEUTRAL_PRINTED = [1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50, 4.00]
ANCHORED_PRINTED = [1.00, 1.54, 2.08, 2.09, 3.00]
FLOOR, TICK, EPS = 1.0, 0.01, 1e-9
FORMULA_RE = re.compile(r"1\s*[-−]\s*\d+(?:\.\d+)?\s*/\s*5|100\s*[*×x]\s*\(\s*1\s*[-−]\s*\d")


def monopoly_profit(m):
    s0, sbar, q0, n = float(m["s0"]), float(m["sBar"]), float(m["q0"]), int(m["n"])
    sm = (s0 + sbar) / 2
    return (sm - s0) * q0 * max(0.0, 1 - sm / sbar) / n, s0


def game(d):
    params = json.load(open(os.path.join(d, "params.json"), encoding="utf-8"))
    mono, s0 = monopoly_profit(params["market"]["scenario"]["market"])
    market, quotes = {}, {}
    prompt_tok, n_reason, n_formula = None, 0, 0
    outcomes = collections.Counter()
    for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
        e = json.loads(line)
        k = e.get("kind")
        if k == "market":
            market[int(e["round"])] = e          # keep the last event of each round
        elif k == "quote":
            outcomes[e.get("outcome")] += 1
            imp = bool(e.get("imputed")) or e.get("outcome") not in ("OK",)
            quotes[(int(e["round"]), e["seat"])] = (e.get("quote"), imp)
            if prompt_tok is None and int(e["round"]) == 1:
                prompt_tok = e.get("tokens_in")
            rs = e.get("reasoning")
            if isinstance(rs, str) and rs.strip():
                n_reason += 1
                n_formula += bool(FORMULA_RE.search(rs))
    rounds = sorted(market)
    mp = [float(market[r]["market_price"]) for r in rounds]
    seats = sorted(market[rounds[0]]["prices"])
    prof = [float(market[r]["profits"][s]) for r in rounds for s in seats]
    comp = match = scored = 0
    for i, r in enumerate(rounds[1:], 1):
        prev = market[rounds[i - 1]]["prices"]
        for s in seats:
            q = float(market[r]["prices"][s])
            tgt = min(float(v) for k2, v in prev.items() if k2 != s)
            scored += 1
            if q <= tgt - TICK + EPS or (q <= FLOOR + EPS and tgt <= FLOOR + EPS):
                comp += 1
            elif abs(q - tgt) < TICK / 2 and q > FLOOR + EPS:
                match += 1
    qv = [round(float(v), 2) for (v, imp) in quotes.values() if not imp and v is not None]
    return dict(rounds=len(rounds), avg_abs_spread=sum(mp) / len(mp),
                price_index=sum(min(1, max(0, (x - 1) / 2)) for x in mp) / len(mp),
                profit_gain_index=(sum(prof) / len(prof) - 0.0) / mono,
                competitive_share=comp / scored if scored else None, matching_share=match / scored if scored else None,
                prompt_tokens_r1=prompt_tok, reasoning_passages=n_reason, formula_eval_passages=n_formula,
                imputed_quotes=sum(1 for v in quotes.values() if v[1])), qv


def classify(v, printed):
    ex = any(abs(v - p) < 0.005 for p in printed)
    under = {t: (not ex) and any(round((p - v) * 100) == t for p in printed) for t in (1, 2, 3)}
    under_any = (not ex) and any(1 <= round((p - v) * 100) <= 3 for p in printed)   # counted once per quote
    above1 = (not ex) and any(round((v - p) * 100) == 1 for p in printed)
    return ex, under, above1, under_any


def shares(qv, printed):
    n = len(qv)
    if not n:
        return {}
    c = collections.Counter()
    for v in qv:
        ex, u, ab, ua = classify(v, printed)
        c["under1to3"] += ua
        c["exact"] += ex; c["under1"] += u[1]; c["under2"] += u[2]; c["under3"] += u[3]; c["above1"] += ab
        c["floor"] += abs(v - 1.0) < 0.005
        for x in (2.47, 2.48, 2.49, 2.50, 2.00, 3.00, 2.09, 1.54, 1.50):
            c["at_%.2f" % x] += abs(v - x) < 0.005
        c["mult05"] += abs(round(v * 20) - v * 20) < 1e-6
    o = {k: c[k] / n for k in c}
    for k in ("exact", "under1", "under2", "under3", "above1", "floor"):
        o.setdefault(k, 0.0)
    o.setdefault("under1to3", 0.0)   # 1 to 3 ticks below SOME printed price, each quote counted once
    o["within1"] = o["exact"] + o["under1"] + o["above1"]
    o["n_quotes"] = n
    return o


rows, allq = [], []


def add(model, run, arm, pp, thinking, wording, seed, tid, d, printed, extra=None):
    m, qv = game(d)
    r = dict(model=model, run=run, arm=arm, penalty_point=int(pp), thinking=thinking, wording=int(wording), seed=int(seed), trial_id=tid)
    r.update(m)
    r.update({"q_" + k: v for k, v in shares(qv, printed).items()})
    if extra:
        r.update(extra)
    rows.append(r)
    for v in qv:
        allq.append((model, run, arm, int(pp), thinking, tid, v))


# gpt-oss: every primary game of the final run.csv (one mode: reasoning effort medium = thinking on)
o = pd.read_csv(OSS_RUN, low_memory=False)
o = o[o.in_primary == 1]
for _, r in o.iterrows():
    d = os.path.join(RUNS, r.source_root, "trials", r.played_trial_id.split("__")[0], r.played_trial_id)
    printed = NEUTRAL_PRINTED   # formula / none arms print none; the neutral list is the counterfactual reference
    add("gpt-oss-20b", r.source_root, r.arm, r.penalty_point, "on", r.wording, r.seed, r.trial_id, d, printed,
        dict(rc_avg_abs_spread=r.market_price_mean, rc_price_index=r.price_index, rc_profit_gain_index=r.profit_gain_index,
             rc_competitive_share=r.competitive_share, rc_matching_share=r.matching_share, payoff_examples=r.payoff_examples,
             arm_build_bug=r.arm_build_bug, wave=r.wave, truncations=r.truncations, code_commit=r.code_commit))

# Qwen neutral run: headline arms and the printed-number joint control
QF = pd.read_csv(FINAL_RUN, low_memory=False)
for tab, run, printed in (("neutral", "qwen_neutral", NEUTRAL_PRINTED), ("anchored", "qwen_anchored", ANCHORED_PRINTED)):
    q = QF[QF.run == tab]
    # neutral: the primary games; anchored (never flagged primary): every DONE game (run.csv already resolves truncation reruns)
    keep = (q.in_primary == 1) if run == "qwen_neutral" else (q.status == "done")
    q = q[keep & (q.arm.isin(["headline-chat", "headline-tacit", "headline-monitored", "ctl-32b-joint"]))]
    for _, r in q.iterrows():
        d = os.path.join(RUNS, r.source_root, "trials", r.played_trial_id.split("__")[0], r.played_trial_id)
        add("Qwen3-32B", run, r.arm, r.penalty_point, r.thinking, r.wording, r.seed, r.trial_id, d, printed,
            dict(rc_avg_abs_spread=r.market_price_mean, rc_price_index=r.price_index, rc_profit_gain_index=r.profit_gain_index,
                 rc_competitive_share=r.competitive_share, rc_matching_share=r.matching_share, payoff_examples=r.payoff_examples))

# Qwen formula / no-numbers run (with 32k reruns substituted) and the Qwen fx-ctl-joint run: not in the Qwen run.csv
sup = {}
sp = os.path.join(RUNS, "2026-10-25_trackm_formula", "superseded.csv")
for r in csv.DictReader(open(sp, encoding="utf-8")):
    sup[r["original_id"]] = r["rerun_id"]
for root in ("2026-10-25_trackm_formula", "2026-10-25_trackm_fx_ctl_joint"):
    for arm in sorted(os.listdir(os.path.join(RUNS, root, "trials"))):
        for tid in sorted(os.listdir(os.path.join(RUNS, root, "trials", arm))):
            d = os.path.join(RUNS, root, "trials", arm, tid)
            if not os.path.exists(os.path.join(d, "DONE")):
                continue
            used = d
            if tid in sup:
                used = os.path.join(RUNS, root + "_x32k", "trials", arm, sup[tid])
                if not os.path.exists(os.path.join(used, "DONE")):
                    used = d
            g = json.load(open(os.path.join(d, "grid_row.json"), encoding="utf-8"))
            add("Qwen3-32B", root, arm, g["penalty_point"], "on" if str(g["thinking"]) == "1" else "off", g["wording"], g["seed"], tid, used,
                NEUTRAL_PRINTED, dict(payoff_examples=g.get("payoff_examples"), rerun_used=int(used != d)))

os.makedirs(OUT, exist_ok=True)
G = pd.DataFrame(rows)
G.to_csv(os.path.join(OUT, "games.csv"), index=False, float_format="%.6f")
pd.DataFrame(allq, columns=["model", "run", "arm", "penalty_point", "thinking", "trial_id", "quote"]).to_csv(
    os.path.join(OUT, "quotes_long.csv.gz"), index=False, compression="gzip")
# validation against run.csv where both exist
v = G.dropna(subset=["rc_price_index"])
out = []
for m in ("avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"):
    diff = (v[m] - v["rc_" + m]).abs()
    out.append(dict(metric=m, n_games=int(diff.notna().sum()), max_abs_diff=diff.max(), n_over_0_001=int((diff > 0.001).sum())))
pd.DataFrame(out).to_csv(os.path.join(OUT, "validation_vs_runcsv.csv"), index=False)
print(pd.DataFrame(out).to_string())
print(G.groupby(["model", "run", "arm", "penalty_point", "thinking"]).size().to_string())
