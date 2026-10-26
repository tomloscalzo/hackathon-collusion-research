"""Wide ripeness map: streaming analysis, Excel CSVs and figures (no numpy / matplotlib).
Usage: python -X utf8 wide_analyze.py <dir with wide.csv and slice-*.csv> <out_dir>"""
import csv, glob, math, os, sys
from collections import defaultdict

SRC, OUT = sys.argv[1], sys.argv[2]
for d in ("excel", "figures"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)
INPUTS = ["delta", "N", "phi", "tick", "slope", "rhoTip", "pEvidence", "fineRatio", "sBarRatio"]
LABEL = {"delta": "Patience δ (continuation probability)", "N": "Number of market makers N",
         "phi": "Preferenced volume share φ", "tick": "Price tick size", "slope": "Regulator screen slope",
         "rhoTip": "Tipping probability per round ρ_tip", "pEvidence": "P(evidence | investigation)",
         "fineRatio": "Fine ratio (fine ÷ one round of full-collusion profit per firm)", "sBarRatio": "Reservation spread ratio s̄/s₀"}
XH = ["Cell ID", "Patience: continuation probability delta", "Number of market makers N",
      "Preferenced (non-contestable) volume share phi", "Price tick size",
      "Regulator screen slope (detection sensitivity to margin)", "Tipping (whistleblower) probability per round rho_tip",
      "P(evidence | triggered investigation)", "Fine ratio (fine / one round of full-collusion profit per firm)",
      "Reservation spread ratio (sBar / s0)", "Solver regime", "Collusion chosen (theta* > 0) [1=yes]",
      "Myopically unripe (penalty exceeds gain) [1=yes]", "Max sustainable collusion intensity theta-hat",
      "Chosen collusion intensity theta*", "theta* given participation", "Ripeness index E", "Collusive half-spread s*",
      "Overcharge vs competitive spread", "Collusion intensity index CI at theta*", "P(trigger) per round at theta*",
      "P(evidence | trigger) at theta*", "P(detected with evidence) per round at theta*", "Expected cartel duration (rounds)",
      "Cartel value per member W*", "Competitive value per member W0", "Collusive rent per member (W* - W0)",
      "Multiple stage Nash equilibria [1=yes]", "Solver error"]


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def derive(r):
    ts, pt, pe, ws, w0 = fl(r["theta_star"]), fl(r["p_trigger_star"]), fl(r["p_evidence_given_trigger_star"]), fl(r["w_star"]), fl(r["w0"])
    return {"_c": None if ts is None else float(ts > 1e-9), "_t": ts, "_E": fl(r["ripeness_E"]), "_pt": pt,
            "_pd": None if pt is None or pe is None else pt * pe, "_dur": fl(r["expected_duration"]),
            "_rent": None if ws is None or w0 is None else ws - w0, "_my": float(r["myopic_unripe"] == "true")}


BASE = {"delta": "0.95", "N": "2.0", "phi": "0.3", "tick": "0.0", "slope": "0.025", "rhoTip": "0.0", "pEvidence": "1.0",
        "fineRatio": "12.5", "sBarRatio": "5.0"}


def xrow(r, d):
    r = {**BASE, **r}
    return [r["cell"], r["delta"], r["N"], r["phi"], r["tick"], r["slope"], r["rhoTip"], r["pEvidence"], r["fineRatio"],
            r["sBarRatio"], r["regime"], "" if d["_c"] is None else int(d["_c"]), int(d["_my"]), r["theta_hat"],
            r["theta_star"], r["theta_star_given_participation"], r["ripeness_E"], r["s_star"], r["overcharge"], r["ci_star"],
            r["p_trigger_star"], r["p_evidence_given_trigger_star"], "" if d["_pd"] is None else d["_pd"],
            r["expected_duration"], r["w_star"], r["w0"], "" if d["_rent"] is None else d["_rent"],
            int(r["multiple_stage_nash"] == "true"), r["error"]]


def convert(src, dst):
    n = 0
    with open(src, encoding="utf-8") as fi, open(dst, "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(XH)
        for r in csv.DictReader(fi):
            w.writerow(xrow(r, derive(r)))
            n += 1
    print("wrote", dst, n, "rows")


# ---------- Excel CSVs ----------
if os.environ.get("SKIP_EXCEL") != "1": convert(os.path.join(SRC, "wide.csv"), os.path.join(OUT, "excel", "ripeness_map_wide_cells.csv"))
for fn in sorted(glob.glob(os.path.join(SRC, "slice-*.csv"))):
    convert(fn, os.path.join(OUT, "excel", "ripeness_baseline_" + os.path.basename(fn)))

# ---------- streaming aggregates over the wide grid ----------
OUTS = [("_c", "P(collusion chosen, θ*>0)"), ("_t", "θ* (chosen intensity)"), ("_E", "Ripeness E"),
        ("_pt", "P(trigger)/round"), ("_pd", "P(detected)/round"), ("_dur", "Expected duration (rounds)"),
        ("_rent", "Collusive rent W*−W0"), ("_my", "Myopically unripe share")]
tot = {k: [0, 0.0, 0.0] for k, _ in OUTS}
lev = {(i, k): defaultdict(lambda: [0, 0.0]) for i in INPUTS for k, _ in OUTS}
PAIRS = [("fineRatio", "slope"), ("delta", "N"), ("pEvidence", "fineRatio"), ("sBarRatio", "phi"), ("rhoTip", "delta"),
         ("tick", "delta")]
two = {pr: defaultdict(lambda: [0, 0.0, 0.0]) for pr in PAIRS}
regimes = defaultdict(int)
ncell = 0
for r in csv.DictReader(open(os.path.join(SRC, "wide.csv"), encoding="utf-8")):
    if r["error"]:
        continue
    ncell += 1
    d = derive(r)
    regimes[r["regime"]] += 1
    for k, _ in OUTS:
        v = d[k]
        if v is None or (k == "_dur" and v > 1e9):
            continue
        t = tot[k]; t[0] += 1; t[1] += v; t[2] += v * v
        for i in INPUTS:
            a = lev[(i, k)][r[i]]; a[0] += 1; a[1] += v
    for a, b in PAIRS:
        c = two[(a, b)][(r[a], r[b])]
        c[0] += 1; c[1] += d["_c"] or 0.0; c[2] += d["_t"] or 0.0


def f(x, n=3):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


L = ["# Wide ripeness map: Layer A solver over the expanded parameter landscape", "",
     f"{ncell:,} cells; non-LLM, model-generated. Regimes: " + ", ".join(f"{k} {v:,}" for k, v in sorted(regimes.items(), key=lambda x: -x[1])), "",
     "## Which inputs drive each outcome (main-effect share of variance, eta²)", "",
     "| Outcome | " + " | ".join(INPUTS) + " |", "|---|" + "---|" * len(INPUTS)]
for k, lab in OUTS:
    n, s, ss = tot[k]
    m = s / n; sst = ss - n * m * m
    cells = []
    for i in INPUTS:
        ssb = sum(c * (sv / c - m) ** 2 for c, sv in lev[(i, k)].values())
        e = ssb / sst if sst > 0 else 0.0
        cells.append(f"**{e:.2f}**" if e >= 0.10 else f"{e:.2f}")
    L.append(f"| {lab} | " + " | ".join(cells) + " |")
L += ["", "Bold = explains ≥10% of the variance on its own.", "", "## Outcome by input level (means over all other inputs)"]
for i in INPUTS:
    L += ["", f"**{LABEL[i]}**", "", "| level | " + " | ".join(lab for _, lab in OUTS) + " |", "|---|" + "---|" * len(OUTS)]
    for lv in sorted(lev[(i, "_c")], key=float):
        L.append(f"| {lv} | " + " | ".join(f(lev[(i, k)][lv][1] / lev[(i, k)][lv][0], 1 if k in ("_dur", "_rent") else 3)
                                           if lev[(i, k)][lv][0] else "n/a" for k, _ in OUTS) + " |")
open(os.path.join(OUT, "RESULTS_WIDE.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote RESULTS_WIDE.md")

# ---------- figures ----------
FONT = 'font-family="Helvetica,Arial,sans-serif"'


def colour(v):
    v = max(0.0, min(1.0, v))
    a, b = (247, 251, 255), (8, 69, 148)
    return "rgb(%d,%d,%d)" % tuple(int(a[j] + (b[j] - a[j]) * v) for j in range(3))


def text(x, y, s, size=11, anchor="middle", weight="normal", fill="#222", rot=None):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" {FONT}{t}>{s}</text>'


def heat(ox, oy, title, rv, cv, val, rlab, clab, cw, ch, fs=9):
    """rv rows (top = first), cv columns; val(r, c) -> value in [0,1] or None."""
    s = [text(ox + len(cv) * cw / 2, oy - 30, title, 12, weight="bold")]
    for j, c in enumerate(cv):
        s.append(text(ox + j * cw + cw / 2, oy - 6, f"{float(c):g}", fs))
    s.append(text(ox + len(cv) * cw / 2, oy + len(rv) * ch + 18, clab, 11))
    for i, r_ in enumerate(rv):
        s.append(text(ox - 6, oy + i * ch + ch / 2 + 3, f"{float(r_):g}", fs, anchor="end"))
        for j, c in enumerate(cv):
            v = val(r_, c)
            if v is None:
                continue
            s.append(f'<rect x="{ox + j * cw:.1f}" y="{oy + i * ch:.1f}" width="{cw - 1}" height="{ch - 1}" fill="{colour(v)}"/>')
            s.append(text(ox + j * cw + cw / 2, oy + i * ch + ch / 2 + 3, f"{v:.2f}", fs, fill="white" if v > 0.55 else "#222"))
    s.append(text(ox - 44, oy + len(rv) * ch / 2, rlab, 11, rot=-90))
    return s


def svg_write(name, W, H, body, title, notes):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="white"/>', text(W / 2, 26, title, 16, weight="bold")] + body
    for k, n in enumerate(notes):
        s.append(text(W / 2, H - 14 - 16 * (len(notes) - 1 - k), n, 11, fill="#555"))
    s.append("</svg>")
    open(os.path.join(OUT, "figures", name), "w", encoding="utf-8").write("\n".join(s))
    print("wrote", name, W, H)


# Figure 3: wide grid, averaged
def avg_panel(a, b, key):
    g = two[(a, b)]
    rv = sorted({x for x, _ in g}, key=float); cv = sorted({y for _, y in g}, key=float)
    idx = 1 if key == "_c" else 2
    return rv, cv, (lambda r_, c: g[(r_, c)][idx] / g[(r_, c)][0] if g[(r_, c)][0] else None)


body = []
specs = [("A. Share where collusion is chosen", "fineRatio", "slope", "_c"),
         ("B. Mean chosen intensity θ*", "fineRatio", "slope", "_t"),
         ("C. Share where collusion is chosen", "delta", "N", "_c"),
         ("D. Share where collusion is chosen", "pEvidence", "fineRatio", "_c"),
         ("E. Share where collusion is chosen", "sBarRatio", "phi", "_c"),
         ("F. Share where collusion is chosen", "rhoTip", "delta", "_c")]
cw, ch = 50, 30
for n, (t, a, b, k) in enumerate(specs):
    rv, cv, val = avg_panel(a, b, k)
    ox = 110 + (n % 2) * 540; oy = 90 + (n // 2) * 330
    body += heat(ox, oy, t, rv, cv, val, LABEL[a], LABEL[b], cw, ch)
svg_write("fig3_ripeness_map_wide_averaged.svg", 1080, 90 + 3 * 330 + 30, body,
          f"Wide ripeness map: {ncell:,} cells, each square averages all other inputs",
          ["Model-generated (Layer A solver, no LLM). Darker = more collusion. Raw cells: excel/ripeness_map_wide_cells.csv."])

# Figure 4: baseline slices (all other inputs at the ripe baseline: δ 0.95, N 2, φ 0.3, tick 0, slope 0.025, ρ_tip 0, P(ev) 1, fine ratio 12.5, s̄/s₀ 5)
def slice_panel(name, a, b):
    rows = list(csv.DictReader(open(os.path.join(SRC, f"slice-{name}.csv"), encoding="utf-8")))
    m = {(r[a], r[b]): fl(r["theta_star"]) for r in rows}
    rv = sorted({r[a] for r in rows}, key=float); cv = sorted({r[b] for r in rows}, key=float)
    return rv, cv, (lambda r_, c: m.get((r_, c)))


body = []
sl = [("fine-slope", "fineRatio", "slope"), ("delta-N", "delta", "N"), ("evidence-fine", "pEvidence", "fineRatio"),
      ("sbar-phi", "sBarRatio", "phi"), ("tip-delta", "rhoTip", "delta")]
cw, ch = 40, 22
panels = [slice_panel(nm, a, b) + (nm, a, b) for nm, a, b in sl]
left_w = max(len(p_[1]) for k_, p_ in enumerate(panels) if k_ % 2 == 0) * cw
right_w = max(len(p_[1]) for k_, p_ in enumerate(panels) if k_ % 2 == 1) * cw
oy = 90
prev_h = 0
for n, (rv, cv, val, nm, a, b) in enumerate(panels):
    ox = 120 if n % 2 == 0 else 120 + left_w + 140
    if n % 2 == 0 and n:
        oy += prev_h
        prev_h = 0
    body += heat(ox, oy, f"{'ABCDE'[n]}. θ* vs {a} × {b}", rv, cv, val, LABEL[a], LABEL[b], cw, ch, fs=8)
    prev_h = max(prev_h, len(rv) * ch + 90)
FIG4_W = 120 + left_w + 140 + right_w + 40
svg_write("fig4_ripeness_baseline_slices.svg", FIG4_W, oy + prev_h + 40, body,
          "Chosen collusion intensity θ* along two inputs at a time, all others at the ripe baseline",
          ["Baseline: δ 0.95, N 2, φ 0.3, tick 0, slope 0.025, ρ_tip 0, P(evidence) 1, fine ratio 12.5, s̄/s₀ 5. θ* = 0 means no collusion.",
           "Model-generated (Layer A solver, no LLM). Raw cells: excel/ripeness_baseline_slice-*.csv."])
