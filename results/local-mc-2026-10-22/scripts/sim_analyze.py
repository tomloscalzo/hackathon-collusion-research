"""Analyse local simulation outputs: ripeness map (solver), strategy mix (Monte Carlo with per-round export), reference bands.
Usage: python -X utf8 sim_analyze.py <sim_dir> <out_md>"""
import csv, os, sys, glob, math
from collections import defaultdict, Counter

SIM, OUT = sys.argv[1], sys.argv[2]
lines = []
def p(s=""): lines.append(s)
def f(x, d=3):
    if x is None or (isinstance(x, float) and math.isnan(x)): return "n/a"
    return f"{x:.{d}f}"
def fl(x):
    try: return float(x)
    except: return None
def mean(v): return sum(v) / len(v) if v else float("nan")
def sd(v):
    if len(v) < 2: return 0.0
    m = mean(v); return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
def q(v, a):
    s = sorted(v); i = a * (len(s) - 1); lo = int(math.floor(i)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)

# ---------------- 1. Ripeness map ----------------
rows = list(csv.DictReader(open(os.path.join(SIM, "ripeness-map.csv"), encoding="utf-8")))
rows = [r for r in rows if not r["error"]]
INPUTS = ["delta", "N", "phi", "tick", "slope", "rhoTip", "pEvidence", "fineRatio", "sBarRatio"]
def num(r, k):
    try: return float(r[k])
    except: return float("nan")
for r in rows:
    r["_collude"] = 1.0 if num(r, "theta_star") > 1e-9 else 0.0
    r["_rent"] = num(r, "w_star") - num(r, "w0")
    r["_myopic"] = 1.0 if r["myopic_unripe"] == "true" else 0.0
    r["_pdet"] = num(r, "p_trigger_star") * num(r, "p_evidence_given_trigger_star")
OUTS = [("_collude", "P(collusion sustainable, theta*>0)"), ("theta_star", "theta* (collusive margin)"),
        ("ripeness_E", "ripeness E"), ("p_trigger_star", "P(trigger) per round at theta*"),
        ("_pdet", "P(detected) per round at theta*"), ("expected_duration", "expected cartel duration (rounds)"),
        ("_rent", "collusive rent W*-W0"), ("_myopic", "myopically unripe share")]
p("# Local simulation results (non-LLM)")
p()
p("Generated on this machine from the frozen engine (repo HEAD 2997526) with the repo's own sweep files. No LLM calls.")
p()
p(f"## 1. Ripeness map: Layer A solver over {len(rows):,} parameter cells")
p()
p("Regime counts: " + ", ".join(f"{k} {v:,}" for k, v in Counter(r["regime"] for r in rows).most_common()))
p()
overall = {k: mean([num(r, k) for r in rows if not math.isnan(num(r, k))]) for k, _ in OUTS}
p("Overall means: " + "; ".join(f"{lab} {f(overall[k])}" for k, lab in OUTS))
p()
# main-effect share of variance (eta^2) per input for each output
p("### Which inputs drive each outcome (main-effect share of variance, eta², balanced grid)")
p()
p("| Outcome | " + " | ".join(INPUTS) + " |")
p("|---|" + "---|" * len(INPUTS))
eta = {}
for k, lab in OUTS:
    vals = [(r, num(r, k)) for r in rows if not math.isnan(num(r, k))]
    m = mean([v for _, v in vals]); sst = sum((v - m) ** 2 for _, v in vals)
    cells = []
    for inp in INPUTS:
        g = defaultdict(list)
        for r, v in vals: g[r[inp]].append(v)
        ssb = sum(len(xs) * (mean(xs) - m) ** 2 for xs in g.values())
        e = ssb / sst if sst > 0 else 0.0
        eta[(k, inp)] = e
        cells.append(f"**{e:.2f}**" if e >= 0.10 else f"{e:.2f}")
    p(f"| {lab} | " + " | ".join(cells) + " |")
p()
p("Bold = input explains ≥10% of the outcome's variance on its own. The rest is interactions and the other inputs.")
p()
p("### Outcome by input level (means across all other inputs)")
for inp in INPUTS:
    g = defaultdict(list)
    for r in rows: g[r[inp]].append(r)
    p()
    p(f"**{inp}**")
    p()
    p("| level | cells | P(sustainable) | theta* | E | P(trigger) | P(detect) | duration | rent W*-W0 | myopic-unripe |")
    p("|---|---|---|---|---|---|---|---|---|---|")
    for lev in sorted(g, key=lambda s: float(s)):
        rs = g[lev]
        def mm(k):
            v = [num(r, k) for r in rs if not math.isnan(num(r, k))]
            return mean(v)
        p(f"| {lev} | {len(rs)} | {f(mm('_collude'))} | {f(mm('theta_star'))} | {f(mm('ripeness_E'))} | {f(mm('p_trigger_star'))} | "
          f"{f(mm('_pdet'))} | {f(mm('expected_duration'),1)} | {f(mm('_rent'),1)} | {f(mm('_myopic'))} |")
# two-way: delta x N on P(sustainable)
p()
p("### Two-way: P(collusion sustainable) by patience δ × number of firms N")
p()
ds = sorted({r["delta"] for r in rows}, key=float); ns = sorted({r["N"] for r in rows}, key=float)
p("| δ \\ N | " + " | ".join(ns) + " |"); p("|---|" + "---|" * len(ns))
for d in ds:
    p(f"| {d} | " + " | ".join(f(mean([r['_collude'] for r in rows if r['delta'] == d and r['N'] == n])) for n in ns) + " |")
p()
p("### Two-way: mean P(detected per round) by evidence probability × fine ratio, among sustainable cells")
p()
pe = sorted({r["pEvidence"] for r in rows}, key=float); fr = sorted({r["fineRatio"] for r in rows}, key=float)
p("| pEvidence \\ fineRatio | " + " | ".join(fr) + " |"); p("|---|" + "---|" * len(fr))
for a in pe:
    cells = []
    for b in fr:
        v = [r["_pdet"] for r in rows if r["pEvidence"] == a and r["fineRatio"] == b and r["_collude"] > 0 and not math.isnan(r["_pdet"])]
        cells.append(f(mean(v)) if v else "–")
    p(f"| {a} | " + " | ".join(cells) + " |")
dur = [num(r, "expected_duration") for r in rows if r["_collude"] > 0 and not math.isnan(num(r, "expected_duration")) and num(r, "expected_duration") < 1e9]
if dur:
    p()
    p(f"Distribution of expected cartel duration among sustainable cells (n={len(dur):,}): median {f(q(dur,.5),1)}, "
      f"IQR {f(q(dur,.25),1)}–{f(q(dur,.75),1)}, 5–95% {f(q(dur,.05),1)}–{f(q(dur,.95),1)} rounds.")
rent = [r["_rent"] for r in rows if r["_collude"] > 0 and not math.isnan(r["_rent"])]
if rent:
    p(f"Distribution of collusive rent W*−W0 among sustainable cells: median {f(q(rent,.5),1)}, IQR {f(q(rent,.25),1)}–{f(q(rent,.75),1)}, "
      f"5–95% {f(q(rent,.05),1)}–{f(q(rent,.95),1)}.")

# ---------------- 2. Strategy mix ----------------
summ = list(csv.DictReader(open(os.path.join(SIM, "strategy-mix", "summary.csv"), encoding="utf-8")))
p()
p("## 2. Strategy mix: Monte Carlo games (5 market families × 7 scripted strategies in the test seat × 2 friction levels, 1,000 runs per cell)")
p()
p("The test seat plays the listed strategy against the held grim-trigger partner (θ_p = 0.546; tick case 0.5). "
  "Profits come from a 300-run re-run of the same cells with per-round export (same seeds as the first 300 runs).")
# profits from export
exp = os.path.join(SIM, "sm-export", "export")
prof = {}
smx = {r["cell_index"]: r for r in csv.DictReader(open(os.path.join(SIM, "sm-export", "summary.csv"), encoding="utf-8"))}
for fn in sorted(glob.glob(os.path.join(exp, "decisions-c*.csv"))):
    cell = os.path.basename(fn)[len("decisions-c"):-4]
    per = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # seat payoff, partner payoff, seat fine, rounds
    for r in csv.DictReader(open(fn, encoding="utf-8")):
        k = r["seed_index"]; pay = float(r["payoff"] or 0); fine = float(r["fine"] or 0)
        if r["agent"] == "llm":
            per[k][0] += pay; per[k][2] += fine; per[k][3] += 1
        elif r["agent"] == "partner":
            per[k][1] += pay
    prof[str(int(cell))] = per
p()
p("| family | seat strategy | frictions | P(adhere) | P(collude) | mean CI | P(detected) | false-alarm rate | median length | seat gross profit/run (sd) | seat gross/round | partner gross/run | seat fines/run | seat NET/run |")
p("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in summ:
    ci = str(int(r["cell_index"]))
    per = prof.get(ci, {})
    sp = [v[0] for v in per.values()]; pp = [v[1] for v in per.values()]; fn_ = [v[2] for v in per.values()]
    rr = [v[0] / v[3] for v in per.values() if v[3] > 0]
    p(f"| {r['family']} | {r['seat']} | {r['frictions']} | {f(fl(r['p_adhere']))} | {f(fl(r['p_collude']))} | {f(fl(r['mean_ci']))} | "
      f"{f(fl(r['share_detected']))} | {f(fl(r['false_alarm_rate']))} | {r['run_length_median']} | "
      f"{f(mean(sp),1)} ({f(sd(sp),1)}) | {f(mean(rr),2)} | {f(mean(pp),1)} | {f(mean(fn_),1)} | {f(mean(sp)-mean(fn_),1)} |")
# collusion premium & deviation gain
p()
p("### Profit from colluding vs competing, and from breaking collusion (seat profit per run, mean of 300 runs)")
p()
p("All figures NET of fines (gross trading payoff minus fines; the engine records them separately). Premium = adhering (grim) minus always-compete. Breaking = defect-once-at-round-8 minus grim. Positive breaking gain means the one-off cheat paid in this market over the realised horizon.")
p()
p("| family | frictions | grim | always-compete | defect-once-8 | collusion premium | gain from breaking |")
p("|---|---|---|---|---|---|---|")
idx = {(r["family"], r["seat"], r["frictions"]): str(int(r["cell_index"])) for r in summ}
for fam in dict.fromkeys(r["family"] for r in summ):
    for fr_ in dict.fromkeys(r["frictions"] for r in summ):
        def m(seat):
            per = prof.get(idx.get((fam, seat, fr_), ""), {})
            return mean([v[0] - v[2] for v in per.values()])
        g, c, d = m("grim"), m("always-compete"), m("defect-once-8")
        p(f"| {fam} | {fr_} | {f(g,1)} | {f(c,1)} | {f(d,1)} | {f(g-c,1)} | {f(d-g,1)} |")

# ---------------- 3. Reference bands ----------------
bfile = os.path.join(SIM, "reference-bands", "bands.csv")
p()
p("## 3. Reference (null) bands for the pre-declared contrasts: scripted seats, 10 paraphrase-clusters × 3 seeds, 1,000 bootstrap resamples")
p()
p("| contrast | statistic | block | arm A | arm B | point | band lo | band hi | degenerate |")
p("|---|---|---|---|---|---|---|---|---|")
for r in csv.DictReader(open(bfile, encoding="utf-8")):
    p(f"| {r['contrast']} | {r['statistic']} | {r['block']} | {r['arm_a']} | {r['arm_b']} | {f(fl(r['point_full']))} | "
      f"{f(fl(r['band_lo']))} | {f(fl(r['band_hi']))} | {r['degenerate']} |")
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote", OUT, len(lines), "lines")
