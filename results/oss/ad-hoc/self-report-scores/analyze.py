"""gpt-oss-20b self-report scores (d-conflict, d-temptation-a/b, d-placebo) and conflict validation (d-conflict-ethics).
Run: python -I -X utf8 analyze.py   (writes CSVs next to this file). Seed fixed (20261026)."""
import csv, os, sys, random, math
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_common"))
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
RUN = (_HK + "/work_scratch/oss_analysis/step1/final_t2/run.csv")
ROUNDS = (_HK + "/work_scratch/oss_analysis/tables_t2/rounds.csv")
QSM = os.path.join(HERE, "..", "..", "..", "ad-hoc-targeted-analysis", "conflict-score-validation", "standard_metrics.csv")
rng = random.Random(oc.SEED)
oss = oc.load_oss(RUN); qwen = oc.load_qwen()
HC = ("headline-chat", "1")
CONTR = [("d-conflict", "conflict question"), ("d-temptation-a", "temptation question a"), ("d-temptation-b", "temptation question b"), ("d-placebo", "placebo question")]
def W(p, rows):
    with open(os.path.join(HERE, p), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerows(rows)
def f(x):
    try: return float(x)
    except: return None
def spear(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
        while i < len(o):
            j = i
            while j+1 < len(o) and v[o[j+1]] == v[o[i]]: j += 1
            for k in range(i, j+1): r[o[k]] = (i+j)/2+1
            i = j+1
        return r
    a, b = rk(x), rk(y); n = len(a); ma, mb = sum(a)/n, sum(b)/n
    sa = math.sqrt(sum((u-ma)**2 for u in a)); sb = math.sqrt(sum((u-mb)**2 for u in b))
    return float("nan") if sa == 0 or sb == 0 else sum((u-ma)*(v-mb) for u, v in zip(a, b))/(sa*sb)
def boot_rho(x, y, cl, B=2000):
    if len(x) < 5: return float("nan"), float("nan"), float("nan")
    r0 = spear(x, y); groups = defaultdict(list)
    for i, c in enumerate(cl): groups[c].append(i)
    keys = list(groups); out = []
    for _ in range(B):
        idx = [i for k in (rng.choice(keys) for _ in keys) for i in groups[k]]
        r = spear([x[i] for i in idx], [y[i] for i in idx])
        if r == r: out.append(r)
    out.sort()
    if len(out) < 100: return r0, float("nan"), float("nan")
    return r0, out[int(.025*len(out))], out[int(.975*len(out))-1]
def S(v, nd=3): return "NA" if v != v else "%.*f" % (nd, v)

# ---- A. standard metrics
SM = [["model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"]]
def add(model, contrast, res):
    for col, _, _ in oc.METRICS:
        d = res[col]; SM.append([model, contrast, col, d["n_pairs"]] + [oc.fmt(d[k], 4) for k in ("mean_a", "mean_b", "diff", "lo", "hi")])
for arm, lab in CONTR:
    c = "%s - headline-chat (p1)" % arm
    add("gpt-oss-20b", c, oc.paired(oss, (arm, "1"), HC))
    add("Qwen3-32B", c, oc.paired(qwen, (arm, "1"), HC))
c = "d-conflict-ethics - d-conflict (p1)"
add("gpt-oss-20b", c, oc.paired(oss, ("d-conflict-ethics", "1"), ("d-conflict", "1")))
add("gpt-oss-20b", "d-conflict-ethics - headline-chat (p1)", oc.paired(oss, ("d-conflict-ethics", "1"), HC))
for r in csv.DictReader(open(QSM, encoding="utf-8")):
    if "neutral (d-conflict)" in r["contrast"] and r["mode"] == "on":
        for col, _, _ in oc.METRICS:
            SM.append(["Qwen3-32B", c, col, r[col+"_n"], r[col+"_arm"], r[col+"_ref"], r[col+"_diff"], r[col+"_lo"], r[col+"_hi"]])
W("standard_metrics.csv", SM)

# ---- empty_talk sensitivity
def ok0(r): return r.get("empty_talk_done_count", "0") in ("0", "")
def paired_drop(a, b):
    A = {(r["wording"], r["seed"]): r for r in oss if (r["arm"], r["penalty_point"]) == a}
    Bm = {(r["wording"], r["seed"]): r for r in oss if (r["arm"], r["penalty_point"]) == b}
    ok = [k for k in set(A) & set(Bm) if ok0(A[k]) and ok0(Bm[k])]
    return oc.paired([A[k] for k in ok] + [Bm[k] for k in ok], a, b)
ES = [["contrast", "metric", "n_pairs_all", "diff_all", "n_pairs_dropped", "diff_dropped", "lo_dropped", "hi_dropped"]]
full = {arm: ((arm, "1"), HC) for arm, _ in CONTR}
full["d-conflict-ethics"] = (("d-conflict-ethics", "1"), ("d-conflict", "1"))
for arm, (a, b) in full.items():
    r1 = oc.paired(oss, a, b); r2 = paired_drop(a, b)
    for col, _, _ in oc.METRICS:
        ES.append(["%s - %s" % (a[0], b[0]), col, r1[col]["n_pairs"], oc.fmt(r1[col]["diff"], 4), r2[col]["n_pairs"], oc.fmt(r2[col]["diff"], 4), oc.fmt(r2[col]["lo"], 4), oc.fmt(r2[col]["hi"], 4)])
W("sensitivity_empty_talk.csv", ES)
ET = [["arm", "n_games", "mean_empty_talk_done_count", "games_with_count_gt0"]]
for arm in ["headline-chat", "d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo", "d-conflict-ethics"]:
    g = [r for r in oss if r["arm"] == arm and r["penalty_point"] == "1"]
    v = [f(r["empty_talk_done_count"]) or 0 for r in g]
    ET.append([arm, len(g), "%.2f" % (sum(v)/len(v)), sum(1 for x in v if x > 0)])
W("empty_talk_by_arm.csv", ET)

# ---- B. distributions from rounds.csv
rounds = defaultdict(list)
for r in csv.DictReader(open(ROUNDS, encoding="utf-8")):
    rounds[r["trial_id"]].append(r)
def arm_games(arm): return [g for g in oss if g["arm"] == arm and g["penalty_point"] == "1"]
def scores(g): return [int(r["self_report"]) for r in rounds[g["trial_id"]] if r["self_report"] in list("12345")]
DIST = [["arm", "n_games", "n_answers", "pct_1", "pct_2", "pct_3", "pct_4", "pct_5", "mean_score", "mean_lo", "mean_hi", "games_with_varying_or_off_baseline_answers"]]
for arm in ["d-conflict", "d-conflict-ethics", "d-temptation-a", "d-temptation-b", "d-placebo"]:
    cnt = Counter(); gm = []; var = 0
    for g in arm_games(arm):
        s = scores(g); cnt.update(s)
        if s: gm.append(sum(s)/len(s))
        base = 3 if arm == "d-placebo" else 1
        if arm.startswith("d-temp"): var += 1 if len(set(s)) > 1 else 0
        elif any(x != base for x in s): var += 1
    n = sum(cnt.values())
    bs = sorted(sum(rng.choice(gm) for _ in gm)/len(gm) for _ in range(2000))
    DIST.append([arm, len(gm), n] + ["%.1f" % (100*cnt[k]/n) for k in range(1, 6)] + ["%.3f" % (sum(gm)/len(gm)), "%.3f" % bs[50], "%.3f" % bs[1949], var])
W("score_distribution.csv", DIST)

# ---- game-level table and within-game
GT = [["trial_id", "arm", "wording", "seed", "score_mean", "score_early_1_3", "price_index_r4plus", "early_price_index_1_3", "price_index", "profit_gain_index", "competitive_share", "matching_share", "market_price_mean", "claude_conflict", "claude_temptation", "claude_rating_id", "empty_talk"]]
WG = defaultdict(list)
for arm in ["d-conflict", "d-conflict-ethics", "d-temptation-a", "d-temptation-b", "d-placebo"]:
    for g in arm_games(arm):
        byr = defaultdict(dict)
        for r in rounds[g["trial_id"]]: byr[int(r["round"])][r["seat"]] = r
        R = sorted(byr)
        sc = {rr: [int(x["self_report"]) for x in byr[rr].values() if x["self_report"] in list("12345")] for rr in R}
        allv = [v for rr in R for v in sc[rr]]
        if not allv: continue
        early = [v for rr in R if rr <= 3 for v in sc[rr]]
        mp = {rr: f(next(iter(byr[rr].values()))["market_price"]) for rr in R}
        late = [(mp[rr]-1)/2 for rr in R if rr >= 4 and mp[rr] is not None]
        ear = [(mp[rr]-1)/2 for rr in R if rr <= 3 and mp[rr] is not None]
        GT.append([g["trial_id"], arm, g["wording"], g["seed"], "%.4f" % (sum(allv)/len(allv)), "%.4f" % (sum(early)/len(early)) if early else "", "%.4f" % (sum(late)/len(late)) if late else "", "%.4f" % (sum(ear)/len(ear)) if ear else "",
                   g["price_index"], g["profit_gain_index"], g["competitive_share"], g["matching_share"], g["market_price_mean"], g["claude_conflict"], g["claude_temptation"], g["claude_rating_id"], g["empty_talk_done_count"]])
        seats = defaultdict(dict)
        for rr in R:
            for s, x in byr[rr].items(): seats[s][rr] = x
        for s, d in seats.items():
            sv = [int(x["self_report"]) for x in d.values() if x["self_report"] in list("12345")]
            if len(sv) < 3: continue
            m = sum(sv)/len(sv)
            for rr, x in d.items():
                if rr == 1 or x["self_report"] not in list("12345") or (rr-1) not in byr: continue
                q = f(x["quote"]); riv = [f(y["quote"]) for t, y in byr[rr-1].items() if t != s and f(y["quote"]) is not None]
                if q is None or not riv: continue
                rv = min(riv)
                WG[arm].append((int(x["self_report"])-m, 1 if (abs(q-rv) <= .005 and q > 1.005) else 0, 1 if q < rv-.005 else 0, g["seed"]))
W("game_table.csv", GT)
rows = [dict(zip(GT[0], r)) for r in GT[1:]]

def corr_rows(sel, label):
    out = []; sub = [r for r in rows if sel(r)]
    for col in ["market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]:
        x = [float(r["score_mean"]) for r in sub]; y = [float(r[col]) for r in sub]
        rho, lo, hi = boot_rho(x, y, [r["seed"] for r in sub])
        out.append([label, col, len(sub), S(rho), S(lo), S(hi)])
    return out
CR = [["set", "outcome", "n_games", "spearman_rho", "lo", "hi"]]
for lab, sel in [("temptation a+b", lambda r: r["arm"] in ("d-temptation-a", "d-temptation-b")), ("temptation a", lambda r: r["arm"] == "d-temptation-a"),
                 ("temptation b", lambda r: r["arm"] == "d-temptation-b"), ("conflict (no rule)", lambda r: r["arm"] == "d-conflict"),
                 ("conflict (ethics rule)", lambda r: r["arm"] == "d-conflict-ethics"), ("conflict, both arms pooled", lambda r: r["arm"] in ("d-conflict", "d-conflict-ethics")),
                 ("placebo", lambda r: r["arm"] == "d-placebo")]:
    CR += corr_rows(sel, lab)
W("game_level_correlations.csv", CR)

WGO = [["set", "outcome", "n_firm_rounds", "spearman_rho", "lo", "hi"]]
for lab, arms in [("temptation a+b", ["d-temptation-a", "d-temptation-b"]), ("conflict (no rule)", ["d-conflict"]), ("conflict (ethics rule)", ["d-conflict-ethics"]), ("placebo", ["d-placebo"])]:
    d = [t for a in arms for t in WG[a]]
    for j, nm in [(1, "matches rival's previous quote"), (2, "undercuts rival's previous quote")]:
        rho, lo, hi = boot_rho([t[0] for t in d], [t[j] for t in d], [t[3] for t in d], B=500)
        WGO.append([lab, nm, len(d), S(rho), S(lo), S(hi)])
W("within_game.csv", WGO)

EP = [["set", "target", "n_games", "spearman_rho", "lo", "hi"]]
for lab, sel in [("temptation a+b", lambda r: r["arm"] in ("d-temptation-a", "d-temptation-b")), ("conflict (ethics rule)", lambda r: r["arm"] == "d-conflict-ethics")]:
    sub = [r for r in rows if sel(r) and r["score_early_1_3"] and r["price_index_r4plus"]]
    for nm, col in [("later price index (rounds 4+) vs early score (rounds 1-3)", "score_early_1_3"), ("later price index vs early price index (rounds 1-3)", "early_price_index_1_3")]:
        rho, lo, hi = boot_rho([float(r[col]) for r in sub], [float(r["price_index_r4plus"]) for r in sub], [r["seed"] for r in sub])
        EP.append([lab, nm, len(sub), S(rho), S(lo), S(hi)])
W("early_prediction.csv", EP)

# ---- Claude ratings
CL = [["arm", "n_games", "self_score_mean", "claude_rating_mean", "claude_rating_name", "market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]]
def mean(v): return sum(v)/len(v)
for arm, ck in [("d-conflict", "claude_conflict"), ("d-conflict-ethics", "claude_conflict"), ("d-temptation-a", "claude_temptation"), ("d-temptation-b", "claude_temptation"), ("d-placebo", "claude_temptation"), ("headline-chat", "claude_temptation")]:
    g = arm_games(arm); sm = [float(r["score_mean"]) for r in g if f(r["score_mean"]) is not None]
    CL.append([arm, len(g), "%.3f" % mean(sm) if sm else "", "%.3f" % mean([float(r[ck]) for r in g]), ck] + ["%.3f" % mean([float(r[c]) for r in g]) for c in ("market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share")])
W("claude_vs_self.csv", CL)
TR = [["set", "pair compared", "n_games", "n_texts", "spearman_rho", "lo", "hi"]]
for lab, arms, ck in [("temptation a+b", ("d-temptation-a", "d-temptation-b"), "claude_temptation"), ("conflict, no-rule + ethics arms", ("d-conflict", "d-conflict-ethics"), "claude_conflict")]:
    sub = [r for r in rows if r["arm"] in arms]; nt = len(set(r["claude_rating_id"] for r in sub))
    pairs = [("%s vs %s" % (ck, nm), ck, col) for nm, col in [("self-score", "score_mean"), ("price_index", "price_index"), ("competitive_share", "competitive_share"), ("matching_share", "matching_share")]]
    pairs += [("self-score vs %s" % nm, "score_mean", col) for nm, col in [("price_index", "price_index"), ("matching_share", "matching_share")]]
    for nm, a, b in pairs:
        rho, lo, hi = boot_rho([float(r[a]) for r in sub], [float(r[b]) for r in sub], [r["claude_rating_id"] for r in sub])
        TR.append([lab, nm, len(sub), nt, S(rho), S(lo), S(hi)])
W("claude_text_level_rho.csv", TR)

# ---- ethics validation
A = {(r["wording"], r["seed"]): r for r in rows if r["arm"] == "d-conflict"}
Bm = {(r["wording"], r["seed"]): r for r in rows if r["arm"] == "d-conflict-ethics"}
ks = sorted(set(A) & set(Bm))
d = [float(Bm[k]["score_mean"])-float(A[k]["score_mean"]) for k in ks]
bs = sorted(sum(rng.choice(d) for _ in d)/len(d) for _ in range(2000))
EV = [["metric", "n_pairs", "mean_no_rule", "mean_ethics", "diff", "lo", "hi"],
      ["conflict score (game mean)", len(ks), "%.4f" % mean([float(A[k]["score_mean"]) for k in ks]), "%.4f" % mean([float(Bm[k]["score_mean"]) for k in ks]), "%.4f" % mean(d), "%.4f" % bs[50], "%.4f" % bs[1949]]]
for arm in ("d-conflict", "d-conflict-ethics"):
    s = [x for g in arm_games(arm) for x in scores(g)]
    ng = sum(1 for g in arm_games(arm) if any(x > 1 for x in scores(g)))
    EV.append(["answers above 1 (%s): n answers, n above 1, games with any above 1" % arm, len(s), sum(1 for x in s if x > 1), ng])
W("conflict_validation.csv", EV)
print("done")
