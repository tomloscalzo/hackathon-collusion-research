"""Payoff-table focal points, gpt-oss-20b (reasoning effort medium) beside Qwen3-32B (thinking on).
Inputs are frozen CSVs; outputs are CSVs and one figure in this folder. Run: python -I -X utf8 focal_points_oss.py
Standard library + numpy + matplotlib. Fixed seed (oss_common)."""
import csv, os, sys, random, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_common"))
import oss_common as oc

import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
W = (_HK + "/work_scratch/")
OSS_RUN = W + "oss_analysis/step1/final_t1/run.csv"
OSS_RND = W + "oss_analysis/tables_t1/rounds.csv"
# Qwen quote tables: the neutral run, then the formula / no-numbers run (reruns substituted) and the fx-ctl-joint run, re-collected with tools/trial/collect.py
Q_RND = [W + "analysis_final/steps/neutral/step1/tables/rounds.csv", W + "oss_analysis/adhoc_focal/tables_qwen_formula/rounds.csv",
         W + "oss_analysis/adhoc_focal/tables_qwen_fxctl/rounds.csv"]
Q_GM = W + "fx_ctl_joint/final/game_metrics.csv"   # Qwen formula / no-numbers / fx-ctl-joint per-game metrics (thinking on)
PRINTED = [1.0, 1.5, 2.0, 2.49, 2.5, 3.0, 3.5, 4.0]


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8", newline="")))


def ptof(a, default):
    for k in ("p1", "p5"):
        if a.endswith(k):
            return k[1]
    return default


# ---------- games
oss_all = oc.load_oss(OSS_RUN, include_bug=True)
oss = [r for r in oss_all if r["arm_build_bug"] != "1"]
hrep = [r for r in oss_all if r["arm_build_bug"] == "1"]
qwen = oc.load_qwen()
qrows = []
for r in rd(Q_GM):
    if not r["cell"].startswith("Q "):
        continue
    a = r["cell"][2:].split(" ")[0]
    if a.startswith(("fx-", "nx-")):
        qrows.append(dict(arm=a, penalty_point=ptof(a, "3"), wording=r["wording"], seed=r["seed"], trial_id=r["trial_id"], thinking="on",
                          market_price_mean=r["avg_abs_spread"], price_index=r["price_index"], profit_gain_index=r["profit_gain_index"],
                          competitive_share=r["competitive_share"], matching_share=r["matching_share"]))
qall = [r for r in qwen if r["thinking"] == "on"] + qrows


def tid(r):
    return r.get("played_trial_id") or r["trial_id"]


def load_quotes(paths, keep):
    q = collections.defaultdict(list)
    for p in paths:
        for r in rd(p):
            if r["trial_id"] in keep and r["seat"].startswith("llm") and r["imputed"] == "0" and r["quote"] not in ("", None):
                q[r["trial_id"]].append(round(float(r["quote"]), 2))
    return q


Qoss = load_quotes([OSS_RND], {tid(r) for r in oss})
Qq = load_quotes(Q_RND, {tid(r) for r in qall})


def classify(v):
    ex = any(abs(v - p) < 0.005 for p in PRINTED)
    d = [round((p - v) * 100) for p in PRINTED]   # ticks under each printed value
    u = {k: (not ex) and (k in d) for k in (1, 2, 3)}
    above1 = (not ex) and any(round((v - p) * 100) == 1 for p in PRINTED)
    return ex, u, above1


def game_shares(quotes):
    n = len(quotes)
    c = collections.Counter()
    for v in quotes:
        ex, u, ab = classify(v)
        c["exact"] += ex; c["under1"] += u[1]; c["under2"] += u[2]; c["under3"] += u[3]; c["above1"] += ab; c["floor"] += (v == 1.0)
    out = {k: c[k] / n for k in ("exact", "under1", "under2", "under3", "above1", "floor")}
    out["within1"] = out["exact"] + out["under1"] + out["above1"]       # exact, or one tick either side of a printed value
    out["under1to3"] = out["under1"] + out["under2"] + out["under3"]
    out["exact_or_under1to3"] = out["exact"] + out["under1to3"]
    out["off_grid"] = 1 - out["exact_or_under1to3"] - out["above1"]
    out["n"] = n
    return out


def boot(vals, B=2000):
    rng = random.Random(oc.SEED)
    n = len(vals)
    ms = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return ms[int(.025 * B)], ms[int(.975 * B) - 1]


def wcsv(name, rows, cols=None):
    cols = cols or list(rows[0].keys())
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        [w.writerow(r) for r in rows]


CELLS = [("headline-chat", "1"), ("headline-chat", "3"), ("headline-chat", "5"), ("headline-tacit", "1"), ("headline-tacit", "5"),
         ("fx-chat-p1", "1"), ("fx-tacit-p1", "1"), ("fx-chat-p5", "5"), ("nx-chat-p1", "1"), ("nx-tacit-p1", "1"),
         ("ctl-32b-joint", "3"), ("fx-ctl-joint", "3")]
KEYS = ["exact", "within1", "under1", "under2", "under3", "under1to3", "exact_or_under1to3", "floor", "off_grid"]
share_rows = []
gshare = {}
for model, rows, Q in (("gpt-oss-20b", oss, Qoss), ("Qwen3-32B", qall, Qq)):
    for arm, pt in CELLS:
        gs = {}
        for r in rows:
            if r["arm"] != arm or str(r["penalty_point"]) != pt:
                continue
            k = tid(r)
            if k in Q and Q[k]:
                gs[(r["wording"], r["seed"])] = game_shares(Q[k])
        if not gs:
            continue
        gshare[(model, arm, pt)] = gs
        row = dict(model=model, arm=arm, penalty_point=pt, n_games=len(gs), n_quotes=sum(g["n"] for g in gs.values()))
        for k in KEYS:
            v = [g[k] for g in gs.values()]
            lo, hi = boot(v)
            row[k] = round(sum(v) / len(v), 4); row[k + "_lo"] = round(lo, 4); row[k + "_hi"] = round(hi, 4)
        share_rows.append(row)
wcsv("quote_shares_by_arm.csv", share_rows)

# ---------- paired quote-share contrasts
PAIRS = [("fx-chat-p1", "1", "headline-chat", "1"), ("fx-tacit-p1", "1", "headline-tacit", "1"), ("fx-chat-p5", "5", "headline-chat", "5"),
         ("nx-chat-p1", "1", "headline-chat", "1"), ("nx-tacit-p1", "1", "headline-tacit", "1"), ("fx-ctl-joint", "3", "ctl-32b-joint", "3")]


def cname(a, pa, b, pb):
    return f"{a} (p{pa}) - {b} (p{pb})"


sp = []
for model in ("gpt-oss-20b", "Qwen3-32B"):
    for a, pa, b, pb in PAIRS:
        A = gshare.get((model, a, pa)); Bm = gshare.get((model, b, pb))
        if not A or not Bm:
            continue
        ks = sorted(set(A) & set(Bm))
        for k in ("exact", "within1", "under1to3"):
            d = [A[x][k] - Bm[x][k] for x in ks]
            lo, hi = boot(d)
            sp.append(dict(model=model, contrast=cname(a, pa, b, pb), measure=k, n_pairs=len(ks),
                           mean_arm=round(sum(A[x][k] for x in ks) / len(ks), 4), mean_control=round(sum(Bm[x][k] for x in ks) / len(ks), 4),
                           diff=round(sum(d) / len(d), 4), lo=round(lo, 4), hi=round(hi, 4)))
wcsv("quote_share_paired.csv", sp)

# ---------- histograms
BINS = [("1.00", 1.0, 1.0), ("1.01-1.25", 1.005, 1.255), ("1.26-1.49", 1.255, 1.495), ("1.50", 1.495, 1.505), ("1.51-1.99", 1.505, 1.995),
        ("2.00", 1.995, 2.005), ("2.01-2.47", 2.005, 2.475), ("2.48", 2.475, 2.485), ("2.49", 2.485, 2.495), ("2.50", 2.495, 2.505),
        ("2.51-2.99", 2.505, 2.995), ("3.00", 2.995, 3.005), ("3.01-3.49", 3.005, 3.495), ("3.50", 3.495, 3.505), ("3.51-3.99", 3.505, 3.995),
        ("4.00", 3.995, 4.005), ("above 4.00", 4.005, 99)]
raw_hist = {}
hist = []
for model, rows, Q in (("gpt-oss-20b", oss, Qoss), ("Qwen3-32B", qall, Qq)):
    for arm, pt in CELLS:
        ks = [tid(r) for r in rows if r["arm"] == arm and str(r["penalty_point"]) == pt and tid(r) in Q and Q[tid(r)]]
        vals = [v for k in ks for v in Q[k]]
        if not vals:
            continue
        raw_hist.setdefault((model, arm), vals)   # first cell wins: headline-chat -> p1, ctl-32b-joint -> p3
        row = dict(model=model, arm=arm, penalty_point=pt, n_games=len(ks), n_quotes=len(vals))
        for nm, lo, hi in BINS:
            row[nm] = round(sum(abs(v - 1.0) < 1e-9 for v in vals) / len(vals), 4) if nm == "1.00" else round(sum(lo < v < hi for v in vals) / len(vals), 4)
        c = collections.Counter(vals)
        row["top_quotes"] = "; ".join(f"{v:.2f} ({100 * n / len(vals):.0f}%)" for v, n in c.most_common(5))
        hist.append(row)
wcsv("quote_histogram_bins.csv", hist)

# ---------- standard metrics
CON = [("fx-chat-p1", "1", "headline-chat", "1"), ("fx-tacit-p1", "1", "headline-tacit", "1"), ("fx-chat-p5", "5", "headline-chat", "5"),
       ("nx-chat-p1", "1", "headline-chat", "1"), ("nx-tacit-p1", "1", "headline-tacit", "1"),
       ("fx-ctl-joint", "3", "ctl-32b-joint", "3"), ("fx-ctl-joint", "3", "fx-chat-p1", "1"), ("fx-ctl-joint", "3", "headline-chat", "3"),
       ("fx-chat-p1", "1", "nx-chat-p1", "1")]
std = []
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qall)):
    for a, pa, b, pb in CON:
        res = oc.paired(rows, (a, pa), (b, pb))
        for col, lab, _ in oc.METRICS:
            x = res[col]
            if x["n_pairs"] == 0:
                continue
            std.append(dict(model=model, contrast=cname(a, pa, b, pb), metric=col, n_pairs=x["n_pairs"], mean_arm=round(x["mean_a"], 4),
                            mean_control=round(x["mean_b"], 4), diff=round(x["diff"], 4), lo=round(x["lo"], 4), hi=round(x["hi"], 4)))
wcsv("standard_metrics.csv", std, ["model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"])


# ---------- empty_talk sensitivity (gpt-oss)
def etc(r):
    try:
        return float(r.get("empty_talk_done_count") or 0)
    except ValueError:
        return 0.0


et_rows = []
for arm, pt in CELLS:
    sub = [r for r in oss if r["arm"] == arm and str(r["penalty_point"]) == pt]
    if sub:
        et_rows.append(dict(arm=arm, penalty_point=pt, n_games=len(sub), mean_empty_talk_done_count=round(sum(etc(r) for r in sub) / len(sub), 3),
                            games_with_count_gt0=sum(etc(r) > 0 for r in sub)))
wcsv("empty_talk_by_arm.csv", et_rows)
clean = [r for r in oss if etc(r) == 0]
sens = []
for a, pa, b, pb in CON[:6]:
    for tag, rows in (("all games", oss), ("games with empty_talk_done_count = 0", clean)):
        res = oc.paired(rows, (a, pa), (b, pb))
        for col in ("price_index", "profit_gain_index"):
            x = res[col]
            if x["n_pairs"]:
                sens.append(dict(contrast=cname(a, pa, b, pb), subset=tag, metric=col, n_pairs=x["n_pairs"], diff=round(x["diff"], 4), lo=round(x["lo"], 4), hi=round(x["hi"], 4)))
wcsv("empty_talk_sensitivity.csv", sens)

# ---------- hrep sensitivity: control = mean of the headline game and its hrep replicate(s) per (wording, seed)
HREP = {("fx-chat-p1", "1"): ("headline-chat", "1", ["hrep-fx-chat-p1", "hrep-nx-chat-p1"]),
        ("fx-chat-p5", "5"): ("headline-chat", "5", ["hrep-fx-chat-p5"]),
        ("fx-tacit-p1", "1"): ("headline-tacit", "1", ["hrep-fx-tacit-p1", "hrep-nx-tacit-p1"]),
        ("nx-chat-p1", "1"): ("headline-chat", "1", ["hrep-fx-chat-p1", "hrep-nx-chat-p1"]),
        ("nx-tacit-p1", "1"): ("headline-tacit", "1", ["hrep-fx-tacit-p1", "hrep-nx-tacit-p1"])}
hs = []
for (a, pa), (b, pb, reps) in HREP.items():
    base = {(r["wording"], r["seed"]): r for r in oss if r["arm"] == b and str(r["penalty_point"]) == pb}
    pool = collections.defaultdict(list)
    for k, r in base.items():
        pool[k].append(r)
    for r in hrep:
        if r["arm"] in reps and (r["wording"], r["seed"]) in base:
            pool[(r["wording"], r["seed"])].append(r)
    pooled = []
    for k, rs in pool.items():
        d = dict(base[k]); d["arm"] = "pooled-control"; d["penalty_point"] = pb
        for col, _, _ in oc.METRICS:
            vals = [float(x[col]) for x in rs if x.get(col) not in ("", None)]
            d[col] = sum(vals) / len(vals) if vals else ""
        d["n_games_in_cell"] = len(rs)
        pooled.append(d)
    for tag, ctl, rows in (("headline game only", (b, pb), oss), ("headline + hrep replicates averaged", ("pooled-control", pb), oss + pooled)):
        res = oc.paired(rows, (a, pa), ctl)
        for col, _, _ in oc.METRICS:
            x = res[col]
            if x["n_pairs"]:
                hs.append(dict(contrast=cname(a, pa, b, pb), control=tag, metric=col, n_pairs=x["n_pairs"], mean_arm=round(x["mean_a"], 4),
                               mean_control=round(x["mean_b"], 4), diff=round(x["diff"], 4), lo=round(x["lo"], 4), hi=round(x["hi"], 4)))
wcsv("hrep_sensitivity.csv", hs)

# ---------- cell means
cm = []
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qall)):
    for arm, pt in CELLS:
        res = oc.cell_means(rows, arm, pt)
        if res["price_index"]["n"]:
            row = dict(model=model, arm=arm, penalty_point=pt, n=res["price_index"]["n"])
            for col, _, _ in oc.METRICS:
                row[col] = round(res[col]["mean"], 4); row[col + "_lo"] = round(res[col]["lo"], 4); row[col + "_hi"] = round(res[col]["hi"], 4)
            cm.append(row)
wcsv("cell_means.csv", cm)


# ---------- pooled firm-round extras: share at 2.49 (the only printed value that is not a multiple of 0.5), share exact among non-floor quotes
ex = []
for model, rows, Q in (("gpt-oss-20b", oss, Qoss), ("Qwen3-32B", qall, Qq)):
    for arm, pt in CELLS:
        vals = [v for r in rows if r["arm"] == arm and str(r["penalty_point"]) == pt for v in Q.get(tid(r), [])]
        if not vals:
            continue
        nf = [v for v in vals if abs(v - 1.0) > 1e-9]
        ex.append(dict(model=model, arm=arm, penalty_point=pt, n_quotes=len(vals), pooled_exact=round(sum(classify(v)[0] for v in vals) / len(vals), 4),
                       n_non_floor=len(nf), exact_among_non_floor=round(sum(classify(v)[0] for v in nf) / len(nf), 4) if nf else "",
                       share_2_49=round(sum(abs(v - 2.49) < 1e-9 for v in vals) / len(vals), 4),
                       share_multiple_of_0_5=round(sum(abs(v * 2 - round(v * 2)) < 1e-9 for v in vals) / len(vals), 4),
                       mean_quote=round(sum(vals) / len(vals), 3)))
wcsv("quote_shares_extras.csv", ex)

# ---------- figure
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ARMS = [("headline-chat", "headline-chat (p1): neutral prompt, chat; example prices printed"),
        ("fx-chat-p1", "fx-chat-p1: chat; formula printed, no example prices"),
        ("nx-chat-p1", "nx-chat-p1: chat; no payoff numbers at all"),
        ("ctl-32b-joint", "ctl-32b-joint (p3): told to maximise joint profit; example prices printed"),
        ("fx-ctl-joint", "fx-ctl-joint (p3): told to maximise joint profit; formula, no example prices")]
fig, axs = plt.subplots(len(ARMS), 2, figsize=(11, 10), sharex=True)
for i, (arm, lab) in enumerate(ARMS):
    for j, model in enumerate(("gpt-oss-20b", "Qwen3-32B")):
        ax = axs[i, j]
        v = raw_hist.get((model, arm))
        # raw_hist is keyed by arm only; the penalty point is fixed by the arm choice above except headline-chat (first cell, p1)
        if v:
            h, e = np.histogram(v, bins=np.arange(0.995, 5.015, 0.01))
            ax.bar(e[:-1] + 0.005, 100 * h / len(v), width=0.01, color="#1f6f8b" if j == 0 else "#a65e2e")
        for p in PRINTED:
            ax.axvline(p, color="grey", lw=0.5, ls=":")
        ax.set_title(f"{model}: {lab}", fontsize=8); ax.set_ylabel("% of quotes", fontsize=7); ax.tick_params(labelsize=7)
        ax.set_xlim(0.98, 4.1)
for ax in axs[-1]:
    ax.set_xlabel("quote (half-spread), one bar per 0.01 tick; dotted lines = values printed in the neutral payoff table", fontsize=7)
fig.suptitle("Share of firm quotes at each 0.01 tick, by arm (2 firms; gpt-oss medium effort / Qwen thinking on)", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "fig_quote_histograms.png"), dpi=130)
print("done", len(std), len(share_rows))
