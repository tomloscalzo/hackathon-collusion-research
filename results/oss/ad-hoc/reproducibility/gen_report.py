import csv, math, os
H = os.path.dirname(os.path.abspath(__file__))
R = lambda n: list(csv.DictReader(open(H + "/" + n, encoding="utf-8")))
LAB = {"market_price_mean": "Average absolute spread", "price_index": "Price index", "profit_gain_index": "Profit gain index", "competitive_share": "Competitive share", "matching_share": "Matching share"}
M = list(LAB)
f3 = lambda x: "%.3f" % float(x)
sm, rs, idn, rr, bc, ded, pc, pairs = R("standard_metrics.csv"), R("replicate_summary.csv"), R("identity_summary.csv"), R("replicate_vs_replicate.csv"), R("between_condition_effects.csv"), R("drift_dedup.csv"), R("pooled_cell_sensitivity.csv"), R("pairs.csv")
def sd(v):
    m = sum(v) / len(v); return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
def rep(x):
    lo, hi = float(x["lo"]), float(x["hi"]); return "excludes 0" if lo > 0 or hi < 0 else "includes 0"
T = []
T.append("| Contrast (replicate - headline) | Metric | n pairs | Mean replicate | Mean headline | Diff | 95% CI | CI vs 0 |\n|---|---|---|---|---|---|---|---|")
for x in sm: T.append("| %s | %s | %s | %s | %s | %+.3f | [%+.3f, %+.3f] | %s |" % (x["contrast"], LAB[x["metric"]], x["n_pairs"], f3(x["mean_arm"]), f3(x["mean_control"]), float(x["diff"]), float(x["lo"]), float(x["hi"]), rep(x)))
std = "\n".join(T)
I = ["| Group | Pairs | Identical quote sequence | Identical all five metrics | Identical replay digest | Same rounds played | Pairs with empty_talk_done_count > 0 |\n|---|---|---|---|---|---|---|"]
for x in idn: I.append("| %s | %s | %s | %s | %s | %s | %s |" % (x["group"], x["n_pairs"], x["same_quote_sequence"], x["same_all_five_metrics"], x["same_digest"], x["same_rounds_played"], x["pairs_with_empty_talk"]))
ident = "\n".join(I)
A = ["| Group | Metric | n | Mean abs diff | SD of diff | Max abs diff | Share exactly equal | Corr(headline, replicate) |\n|---|---|---|---|---|---|---|---|"]
for x in rs:
    if x["group"] in ("ALL five arms pooled", "p1 arms pooled (4)", "hrep-fx-chat-p1", "hrep-nx-chat-p1", "hrep-fx-tacit-p1", "hrep-nx-tacit-p1", "hrep-fx-chat-p5"):
        A.append("| %s | %s | %s | %s | %s | %s | %.2f | %.2f |" % (x["group"], LAB[x["metric"]], x["n_pairs"], f3(x["mean_abs_diff"]), f3(x["sd_diff"]), f3(x["max_abs_diff"]), float(x["share_exact_equal"]), float(x["corr_h_r"])))
absd = "\n".join(A)
D = ["| Group | Metric | n headline games | Mean headline | Mean replicate copies | Diff | 95% CI | Share of games with replicate higher |\n|---|---|---|---|---|---|---|---|"]
for x in ded: D.append("| %s | %s | %s | %s | %s | %+.3f | [%+.3f, %+.3f] | %.2f |" % (x["group"], LAB[x["metric"]], x["n_headline_games"], f3(x["mean_h"]), f3(x["mean_r"]), float(x["mean_diff"]), float(x["lo"]), float(x["hi"]), float(x["share_positive"])))
drift = "\n".join(D)
E = ["| Group | Metric | n | Diff | 95% CI |\n|---|---|---|---|---|"]
for x in rs:
    if x["group"].startswith("ALL pooled"): E.append("| pairs with empty_talk_done_count = 0 in both games | %s | %s | %+.3f | [%+.3f, %+.3f] |" % (LAB[x["metric"]], x["n_pairs"], float(x["mean_diff"]), float(x["lo"]), float(x["hi"])))
for x in rs:
    if x["group"] == "ALL five arms pooled": E.append("| all pairs | %s | %s | %+.3f | [%+.3f, %+.3f] |" % (LAB[x["metric"]], x["n_pairs"], float(x["mean_diff"]), float(x["lo"]), float(x["hi"])))
emp = "\n".join(E)
RR = ["| Cell | Metric | n | fx minus nx | 95% CI | Mean abs diff |\n|---|---|---|---|---|---|"]
for x in rr: RR.append("| %s | %s | %s | %+.3f | [%+.3f, %+.3f] | %s |" % (x["cell"], LAB[x["metric"]], x["n_pairs"], float(x["mean_diff_fx_minus_nx"]), float(x["lo"]), float(x["hi"]), f3(x["mean_abs_diff"])))
rrt = "\n".join(RR)
# MDE
grp = {"chat p1 (fx+nx, 40 pairs)": ["hrep-fx-chat-p1", "hrep-nx-chat-p1"], "tacit p1 (fx+nx, 40 pairs)": ["hrep-fx-tacit-p1", "hrep-nx-tacit-p1"], "chat p5 (19 pairs)": ["hrep-fx-chat-p5"]}
MD = ["| Cell type | Metric | SD of a paired difference | 95% CI half-width at n = 20 | Minimum detectable effect (80% power, n = 20) |\n|---|---|---|---|---|"]
for g, arms in grp.items():
    for m in M:
        v = [float(p[m + "_d"]) for p in pairs if p["rep_arm"] in arms]; s = sd(v)
        MD.append("| %s | %s | %.3f | %.3f | %.3f |" % (g, LAB[m], s, 1.96 * s / math.sqrt(20), 2.8 * s / math.sqrt(20)))
mde = "\n".join(MD)
B = ["| Between-condition contrast | Metric | n | Diff | 95% CI |\n|---|---|---|---|---|"]
for x in bc: B.append("| %s | %s | %s | %+.3f | [%+.3f, %+.3f] |" % (x["contrast"], LAB[x["metric"]], x["n_pairs"], float(x["diff"]), float(x["lo"]), float(x["hi"])))
bct = "\n".join(B)
P = ["| Contrast, pooled cells (headline plus its replicate copies) | Metric | n | Diff | 95% CI |\n|---|---|---|---|---|"]
for x in pc: P.append("| %s | %s | %s | %+.3f | [%+.3f, %+.3f] |" % (x["contrast"], LAB[x["metric"]], x["n_pairs"], float(x["diff"]), float(x["lo"]), float(x["hi"])))
pct = "\n".join(P)
tpl = open(H + "/template.md", encoding="utf-8").read()
for k, v in dict(STD=std, IDENT=ident, ABSD=absd, DRIFT=drift, EMP=emp, RR=rrt, MDE=mde, BC=bct, PC=pct).items(): tpl = tpl.replace("{{%s}}" % k, v)
open(H + "/ANALYSIS.md", "w", encoding="utf-8").write(tpl)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(H + "/ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
