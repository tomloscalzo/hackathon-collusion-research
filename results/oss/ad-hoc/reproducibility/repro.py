"""Reproducibility of gpt-oss-20b headline cells: hrep-* replicates vs their headline cells. Run: python -I -X utf8 repro.py"""
import csv, json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_common"))
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
RUN = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
TR = (_HK + "/runs/2026-10-26_trackm_oss_neutral/trials/")
rows = oc.load_oss(RUN, include_bug=True)
M = [m[0] for m in oc.METRICS]
REPS = {  # replicate arm -> (headline arm, pt, raw dir)
 "hrep-fx-chat-p1": ("headline-chat", 1, "fx-chat-p1"), "hrep-nx-chat-p1": ("headline-chat", 1, "nx-chat-p1"),
 "hrep-fx-tacit-p1": ("headline-tacit", 1, "fx-tacit-p1"), "hrep-nx-tacit-p1": ("headline-tacit", 1, "nx-tacit-p1"),
 "hrep-fx-chat-p5": ("headline-chat", 5, "fx-chat-p5")}
f = lambda x: float(x) if x not in (None, "") else None
idx = {}
for r in rows: idx.setdefault((r["arm"], r["penalty_point"]), {})[(r["wording"], r["seed"])] = r

def raw(dirarm, tid):
    p = TR + dirarm + "/" + tid + "/"
    d = json.loads(open(p + "run.jsonl", encoding="utf-8").readline())
    q = [[a["displayed"] for a in rd["agents"]] for rd in d["rounds"]]
    calls = [json.loads(l) for l in open(p + "calls.jsonl", encoding="utf-8")]
    first = tuple(sorted(c["requestHash"] for c in calls if c["kind"] == "talk" and c["index"] == 1))
    return d["replayDigest"], q, first

def sd(v):
    m = sum(v) / len(v); return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
def corr(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    a = sum((i - mx) * (j - my) for i, j in zip(x, y)); b = math.sqrt(sum((i - mx) ** 2 for i in x) * sum((j - my) ** 2 for j in y))
    return a / b if b else float("nan")
def boot(v, seed=oc.SEED):
    rng = random.Random(seed); n = len(v)
    ms = sorted(sum(v[rng.randrange(n)] for _ in range(n)) / n for _ in range(2000))
    return ms[49], ms[1949]

pairs = []
for rep, (hl, pt, rd) in REPS.items():
    H = idx[(hl, str(pt))]; R = idx[(rep, str(pt))]
    for k in sorted(set(H) & set(R), key=lambda k: (int(k[0]), int(k[1]))):
        h, r = H[k], R[k]
        hd, hq, hf = raw(hl, h["trial_id"]); rdg, rq, rf = raw(rd, r["trial_id"])
        o = dict(rep_arm=rep, headline_arm=hl, pt=pt, wording=k[0], seed=k[1], wave=h["wave"], rounds_h=h["rounds_played"], rounds_r=r["rounds_played"],
                 planned_h=h["planned_length"], planned_r=r["planned_length"],
                 same_digest=int(hd == rdg), same_quotes=int(hq == rq), same_first_prompts=int(hf == rf),
                 empty_h=h["empty_talk_done_count"], empty_r=r["empty_talk_done_count"])
        o["same_metrics"] = int(all(h[m] == r[m] for m in M))
        for m in M:
            o[m + "_h"], o[m + "_r"], o[m + "_d"] = f(h[m]), f(r[m]), f(r[m]) - f(h[m])
        pairs.append(o)
def wcsv(name, rows_, cols=None):
    w = csv.DictWriter(open(HERE + "/" + name, "w", newline="", encoding="utf-8"), cols or list(rows_[0])); w.writeheader(); w.writerows(rows_)
wcsv("pairs.csv", pairs)

def summ(sub, label):
    out = []
    for m in M:
        d = [p[m + "_d"] for p in sub]; lo, hi = boot(d)
        out.append(dict(group=label, metric=m, n_pairs=len(d), mean_h=sum(p[m + "_h"] for p in sub) / len(d), mean_r=sum(p[m + "_r"] for p in sub) / len(d),
                        mean_diff=sum(d) / len(d), lo=lo, hi=hi, mean_abs_diff=sum(abs(x) for x in d) / len(d), sd_diff=sd(d),
                        max_abs_diff=max(abs(x) for x in d), share_exact_equal=sum(1 for x in d if x == 0) / len(d),
                        corr_h_r=corr([p[m + "_h"] for p in sub], [p[m + "_r"] for p in sub]),
                        corr_diff_wave=corr([float(p["wave"]) for p in sub], d), corr_diff_seed=corr([float(p["seed"]) for p in sub], d)))
    return out
S = []
for rep in REPS: S += summ([p for p in pairs if p["rep_arm"] == rep], rep)
S += summ(pairs, "ALL five arms pooled")
S += summ([p for p in pairs if p["empty_h"] == "0" and p["empty_r"] == "0"], "ALL pooled, pairs with empty_talk_done_count = 0 in both")
S += summ([p for p in pairs if p["rep_arm"] != "hrep-fx-chat-p5"], "p1 arms pooled (4)")
wcsv("replicate_summary.csv", S)

ident = []
for rep in list(REPS) + ["ALL"]:
    sub = [p for p in pairs if rep == "ALL" or p["rep_arm"] == rep]
    ident.append(dict(group=rep, n_pairs=len(sub), same_first_round_prompts=sum(p["same_first_prompts"] for p in sub), same_digest=sum(p["same_digest"] for p in sub),
        same_quote_sequence=sum(p["same_quotes"] for p in sub), same_all_five_metrics=sum(p["same_metrics"] for p in sub),
        same_rounds_played=sum(p["rounds_h"] == p["rounds_r"] for p in sub), pairs_with_empty_talk=sum(1 for p in sub if p["empty_h"] != "0" or p["empty_r"] != "0")))
wcsv("identity_summary.csv", ident)

cp = []
for a, b, lab in [("hrep-fx-chat-p1", "hrep-nx-chat-p1", "chat p1"), ("hrep-fx-tacit-p1", "hrep-nx-tacit-p1", "tacit p1")]:
    for m in M:
        r_ = oc.paired(rows, (a, 1), (b, 1))[m]
        d = [abs(float(idx[(a, "1")][k][m]) - float(idx[(b, "1")][k][m])) for k in set(idx[(a, "1")]) & set(idx[(b, "1")])]
        cp.append(dict(cell=lab, metric=m, n_pairs=r_["n_pairs"], mean_diff_fx_minus_nx=r_["diff"], lo=r_["lo"], hi=r_["hi"], mean_abs_diff=sum(d) / len(d)))
wcsv("replicate_vs_replicate.csv", cp)

BC = [("headline-chat", 5, "headline-chat", 1), ("headline-chat", 3, "headline-chat", 1), ("headline-tacit", 1, "headline-chat", 1),
      ("headline-tacit", 5, "headline-chat", 5), ("headline-tacit", 5, "headline-tacit", 1)]
bc = []
for a, pa, b, pb in BC:
    r_ = oc.paired(rows, (a, pa), (b, pb))
    for m in M:
        x = r_[m]; bc.append(dict(contrast="%s (p%d) - %s (p%d)" % (a, pa, b, pb), metric=m, n_pairs=x["n_pairs"], diff=x["diff"], lo=x["lo"], hi=x["hi"]))
wcsv("between_condition_effects.csv", bc)

sm = []
for rep, (hl, pt, rd) in REPS.items():
    r_ = oc.paired(rows, (rep, pt), (hl, pt))
    for m in M:
        x = r_[m]; sm.append(dict(model="gpt-oss-20b", contrast="%s - %s (p%d)" % (rep, hl, pt), metric=m, n_pairs=x["n_pairs"], mean_arm=x["mean_a"], mean_control=x["mean_b"], diff=x["diff"], lo=x["lo"], hi=x["hi"]))
for s in [s for s in S if s["group"] == "ALL five arms pooled"]:
    sm.append(dict(model="gpt-oss-20b", contrast="all five hrep arms pooled - their headline cells", metric=s["metric"], n_pairs=s["n_pairs"], mean_arm=s["mean_r"], mean_control=s["mean_h"], diff=s["mean_diff"], lo=s["lo"], hi=s["hi"]))
wcsv("standard_metrics.csv", sm, ["model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"])

print("IDENT"); [print(i) for i in ident]
print("SUMMARY")
for s in S: print(s["group"][:28].ljust(28), s["metric"].ljust(18), s["n_pairs"], "h %.3f r %.3f d %+.3f [%+.3f,%+.3f] MAD %.3f sd %.3f eq %.2f r %.2f cw %.2f cs %.2f" % (s["mean_h"], s["mean_r"], s["mean_diff"], s["lo"], s["hi"], s["mean_abs_diff"], s["sd_diff"], s["share_exact_equal"], s["corr_h_r"], s["corr_diff_wave"], s["corr_diff_seed"]))
print("REP-REP"); [print(c) for c in cp]
print("BETWEEN"); [print(c["contrast"], c["metric"], c["n_pairs"], round(c["diff"], 3), round(c["lo"], 3), round(c["hi"], 3)) for c in bc]

# ---- de-duplicated drift test: average the replicate copies per headline game (60 independent headline games)
from collections import defaultdict
g = defaultdict(list)
for p in pairs: g[(p["headline_arm"], p["pt"], p["wording"], p["seed"])].append(p)
ded = []
for k, v in g.items():
    o = dict(headline_arm=k[0], pt=k[1], wording=k[2], seed=k[3], n_copies=len(v))
    for m in M:
        o[m + "_h"] = v[0][m + "_h"]; o[m + "_r_mean"] = sum(x[m + "_r"] for x in v) / len(v); o[m + "_d"] = o[m + "_r_mean"] - o[m + "_h"]
    ded.append(o)
wcsv("pairs_per_headline_game.csv", ded)
DS = []
for lab, sub in [("all 60 headline games (copies averaged)", ded)] + [("%s p%d (n copies avg)" % (a, pt), [o for o in ded if o["headline_arm"] == a and o["pt"] == pt]) for a, pt in [("headline-chat", 1), ("headline-tacit", 1), ("headline-chat", 5)]]:
    for m in M:
        d = [o[m + "_d"] for o in sub]; lo, hi = boot(d)
        DS.append(dict(group=lab, metric=m, n_headline_games=len(d), mean_h=sum(o[m + "_h"] for o in sub) / len(d), mean_r=sum(o[m + "_r_mean"] for o in sub) / len(d), mean_diff=sum(d) / len(d), lo=lo, hi=hi, sd_diff=sd(d), share_positive=sum(1 for x in d if x > 0) / len(d)))
wcsv("drift_dedup.csv", DS)
print("DEDUP"); [print(s["group"][:34].ljust(34), s["metric"].ljust(18), s["n_headline_games"], "h %.3f r %.3f d %+.3f [%+.3f,%+.3f] sd %.3f pos %.2f" % (s["mean_h"], s["mean_r"], s["mean_diff"], s["lo"], s["hi"], s["sd_diff"], s["share_positive"])) for s in DS]

# ---- pooled-cell sensitivity: headline + copies pooled per (wording, seed); contrasts between cells
def pooled_cell(a, pt):
    out = {}
    cells = [(a, str(pt))] + [(r, str(pt)) for r, (h, p_, _) in REPS.items() if h == a and p_ == pt]
    for k in idx[(a, str(pt))]:
        out[k] = {m: sum(float(idx[c][k][m]) for c in cells if k in idx[c]) / sum(1 for c in cells if k in idx[c]) for m in M}
    return out, len([c for c in cells if c in idx])
PC = []
for (a, pa), (b, pb) in [(("headline-chat", 5), ("headline-chat", 1)), (("headline-tacit", 1), ("headline-chat", 1)), (("headline-tacit", 5), ("headline-chat", 5)), (("headline-tacit", 5), ("headline-tacit", 1))]:
    A_, na = pooled_cell(a, pa); B_, nb = pooled_cell(b, pb)
    ks = sorted(set(A_) & set(B_))
    for m in M:
        d = [A_[k][m] - B_[k][m] for k in ks]; lo, hi = boot(d)
        PC.append(dict(contrast="%s (p%d) - %s (p%d), pooled cells (%d and %d copies)" % (a, pa, b, pb, na, nb), metric=m, n_pairs=len(d), diff=sum(d) / len(d), lo=lo, hi=hi))
wcsv("pooled_cell_sensitivity.csv", PC)
print("POOLED"); [print(c["contrast"], c["metric"], c["n_pairs"], round(c["diff"], 3), round(c["lo"], 3), round(c["hi"], 3)) for c in PC]
