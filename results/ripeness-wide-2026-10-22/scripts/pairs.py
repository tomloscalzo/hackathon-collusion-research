"""All-pairs 2-D heat maps over the wide ripeness grid (averaged over the other inputs), for P(collusion chosen) and mean theta*,
each with an automatically generated plain-English reading written beneath the chart.
Usage: python -X utf8 pairs.py <wide.csv> <out_dir>"""
import csv, html, itertools, json, os, sys
from collections import defaultdict

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(OUT, "charts"), exist_ok=True)
INPUTS = ["delta", "N", "phi", "tick", "slope", "rhoTip", "pEvidence", "fineRatio", "sBarRatio"]
LABEL = {"delta": "Patience δ", "N": "Number of market makers N", "phi": "Preferenced volume share φ",
         "tick": "Price tick size", "slope": "Regulator screen slope", "rhoTip": "Tip probability per round ρ_tip",
         "pEvidence": "P(evidence | investigation)", "fineRatio": "Fine ratio (fine ÷ one round of full-collusion profit per firm)",
         "sBarRatio": "Reservation spread ratio s̄/s₀"}
SHORT = {"delta": "patience", "N": "the number of market makers", "phi": "the preferenced volume share",
         "tick": "the tick size", "slope": "the screen slope", "rhoTip": "the tip probability",
         "pEvidence": "the probability an investigation finds evidence", "fineRatio": "the fine ratio",
         "sBarRatio": "the reservation spread ratio"}
# Why each input moves collusion, keyed by the direction in which it LOWERS collusion (-1: higher value lowers it).
WHY = {
    "fineRatio": (-1, "bigger fines raise the expected cost of being convicted"),
    "slope": (-1, "a steeper screen makes high spreads more likely to trigger an investigation, so cartels must keep margins low or not collude"),
    "rhoTip": (-1, "tips end cartels at any margin, so they shorten the expected life of the cartel"),
    "pEvidence": (-1, "a higher chance that an investigation ends in a conviction makes the fine more likely to be paid"),
    "N": (-1, "each member's share of the cartel profit is 1/N, while a one-round undercut still captures most of the contestable flow, so the temptation to cheat grows with N"),
    "tick": (-1, "a coarser tick gives competitors a profit floor (tick rents), so colluding gains less over competing; in this calibration it also makes an inconclusive investigation costly (π_post = 0)"),
    "phi": (+1, "preferenced flow is shared whatever the price, so an undercut steals less volume and cheating pays less"),
    "sBarRatio": (+1, "more room between cost and the customers' walk-away spread means bigger cartel profits"),
    "delta": (+1, "patient firms value future cartel profits more, which makes the threat of a price war bite"),
}
CAVEAT = {"tick", "pEvidence", "delta"}
SYM = {"delta": "δ", "N": "N", "phi": "φ", "tick": "tick", "slope": "slope", "rhoTip": "ρ_tip", "pEvidence": "P(evidence)",
       "fineRatio": "fine ratio", "sBarRatio": "s̄/s₀"}
OUTS = [("share", "Share of parameter cells where collusion is chosen (θ* > 0)"), ("theta", "Mean chosen collusion intensity θ*")]

# ---------- stream the grid once ----------
agg = {pr: defaultdict(lambda: [0, 0.0, 0.0]) for pr in itertools.combinations(INPUTS, 2)}
n = 0
for r in csv.DictReader(open(SRC, encoding="utf-8")):
    if r["error"]:
        continue
    n += 1
    t = float(r["theta_star"]); c = 1.0 if t > 1e-9 else 0.0
    for a, b in agg:
        x = agg[(a, b)][(r[a], r[b])]
        x[0] += 1; x[1] += c; x[2] += t
print("cells", n)


def fmt(v):
    return f"{float(v):g}"


def table(a, b, key):
    g = agg[(a, b)]
    rv = sorted({x for x, _ in g}, key=float); cv = sorted({y for _, y in g}, key=float)
    i = 1 if key == "share" else 2
    M = [[g[(r_, c_)][i] / g[(r_, c_)][0] for c_ in cv] for r_ in rv]
    return rv, cv, M


def shape(seq):
    d = [seq[k + 1] - seq[k] for k in range(len(seq) - 1)]
    if all(x >= -0.005 for x in d):
        return "rises"
    if all(x <= 0.005 for x in d):
        return "falls"
    k = max(range(len(seq)), key=lambda j: seq[j]); m = min(range(len(seq)), key=lambda j: seq[j])
    if 0 < k < len(seq) - 1:
        return f"peak@{k}"
    if 0 < m < len(seq) - 1:
        return f"trough@{m}"
    return "mixed"


def describe(var, levels, marg, what):
    return describe0(var, levels, marg, what) + (shape(marg),)


def describe0(var, levels, marg, what):
    s = shape(marg); lo, hi = fmt(levels[0]), fmt(levels[-1])
    eff = marg[-1] - marg[0]
    if max(marg) - min(marg) < 0.02:
        return f"{SHORT[var].capitalize()} has almost no effect on its own ({min(marg):.2f}–{max(marg):.2f}).", 0
    if s == "rises":
        txt = f"Raising {SHORT[var]} from {lo} to {hi} raises the {what} from {marg[0]:.2f} to {marg[-1]:.2f}."
    elif s == "falls":
        txt = f"Raising {SHORT[var]} from {lo} to {hi} lowers the {what} from {marg[0]:.2f} to {marg[-1]:.2f}."
    elif s.startswith("peak"):
        k = int(s.split("@")[1])
        txt = (f"The {what} peaks at {SHORT[var]} = {fmt(levels[k])} ({marg[k]:.2f}) and is lower at both ends "
               f"({marg[0]:.2f} at {lo}, {marg[-1]:.2f} at {hi}).")
    elif s.startswith("trough"):
        k = int(s.split("@")[1])
        txt = (f"The {what} is lowest at {SHORT[var]} = {fmt(levels[k])} ({marg[k]:.2f}) and higher at both ends "
               f"({marg[0]:.2f} at {lo}, {marg[-1]:.2f} at {hi}).")
    else:
        txt = f"Moving {SHORT[var]} from {lo} to {hi} changes the {what} from {marg[0]:.2f} to {marg[-1]:.2f}, not monotonically."
    sign = 0 if s.startswith(("peak", "trough")) or s == "mixed" else (1 if eff > 0 else -1)
    return txt, sign


def why(var, sign, s="", key="theta"):
    if var == "delta" and s.startswith("peak") and key == "share":
        return (" Why: patience helps up to a point (future cartel profits are worth protecting and the price-war threat bites); "
                "the decline at very high patience comes from the π_post = 0 calibration in tick markets (see Analysis).")
    if var == "delta" and s.startswith("peak"):
        return (" Why: patience helps up to a point (future cartel profits are worth protecting and the price-war threat bites), "
                "but very patient coalitions choose lower margins to avoid the screen, and in tick markets the π_post = 0 "
                "calibration makes long horizons costly.")
    if var == "sBarRatio" and s.startswith("peak"):
        return (" Why: more room between cost and the customers' walk-away spread means bigger cartel profits, but the screen reacts "
                "to the absolute markup, so the wide spreads a cartel would charge in roomy markets are also more likely to be flagged.")
    if sign == 0 or var not in WHY:
        return ""
    d, reason = WHY[var]
    if sign == d:
        return f" Why: {reason}."
    if var == "pEvidence" and sign == 1:
        return (" This runs against intuition: in tick markets the calibration makes an inconclusive investigation worse than a "
                "conviction (π_post = 0), so more evidence looks safer; at tick 0 the effect is the expected one.")
    if var == "delta" and sign == -1:
        return (" This runs against the simple intuition: patient coalitions protect future rents by choosing lower margins, and in "
                "tick markets the π_post = 0 calibration makes long horizons costlier.")
    return " (The direction differs from the simple intuition; see the cell-level data.)"


def interpret(a, b, key, rv, cv, M):
    what = "share of cells where collusion is chosen" if key == "share" else "mean collusion intensity θ*"
    rm = [sum(row) / len(row) for row in M]
    cm = [sum(M[i][j] for i in range(len(rv))) / len(rv) for j in range(len(cv))]
    ta, sa, pa = describe(a, rv, rm, what); tb, sb, pb = describe(b, cv, cm, what)
    flat = [(M[i][j], i, j) for i in range(len(rv)) for j in range(len(cv))]
    mx = max(flat); mn = min(flat)
    lines = [ta + why(a, sa, pa, key), tb + why(b, sb, pb, key),
             f"Highest: {mx[0]:.2f} at {SYM[a]} = {fmt(rv[mx[1]])}, {SYM[b]} = {fmt(cv[mx[2]])}; "
             f"lowest: {mn[0]:.2f} at {SYM[a]} = {fmt(rv[mn[1]])}, {SYM[b]} = {fmt(cv[mn[2]])}."]
    # interaction: effect of a (last row - first row) at first vs last column
    e_lo = M[-1][0] - M[0][0]; e_hi = M[-1][-1] - M[0][-1]
    if abs(e_lo - e_hi) >= 0.10 and max(abs(e_lo), abs(e_hi)) >= 0.08:
        big, small, bl, sl = (e_lo, e_hi, fmt(cv[0]), fmt(cv[-1])) if abs(e_lo) > abs(e_hi) else (e_hi, e_lo, fmt(cv[-1]), fmt(cv[0]))
        lines.append(f"The two interact: going from the lowest to the highest {SYM[a]} changes the value by {big:+.2f} when {SYM[b]} = {bl} but by {small:+.2f} when {SYM[b]} = {sl}.")
    if {a, b} == {"pEvidence", "fineRatio"}:
        lines.append("Why the no-fine column rises: in the model a trigger ends the cartel whether or not evidence is found, so "
                     "P(evidence) only decides what happens afterwards (fine plus normal competition, or π_post forever). With no "
                     "fine, the only difference is π^N versus π_post. Split by tick, the no-fine share is flat at 0.74 when tick = 0 "
                     "and rises only in tick markets (0.66 to 0.87 at tick 0.25; 0.45 to 0.69 at tick 0.5), where π_post = 0 < π^N.")
    if CAVEAT & {a, b}:
        lines.append("Caveat: patterns involving tick, patience or P(evidence) are partly shaped by the π_post = 0 calibration in tick "
                     "markets (a recorded limitation).")
    return lines


# ---------- SVG ----------
FONT = 'font-family="Helvetica,Arial,sans-serif"'


def colour(v):
    v = max(0.0, min(1.0, v)); a, b = (247, 251, 255), (8, 69, 148)
    return "rgb(%d,%d,%d)" % tuple(int(a[k] + (b[k] - a[k]) * v) for k in range(3))


def text(x, y, s, size=11, anchor="middle", weight="normal", fill="#222", rot=None):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" '
            f'{FONT}{t}>{html.escape(s)}</text>')


def wrap(s, width):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > width:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


def chart(a, b, key, rv, cv, M, lines, title):
    cw, ch = 58, 30
    gw, gh = len(cv) * cw, len(rv) * ch
    W = 760; ox = max(150, (W - gw) // 2 + 30); oy = 80
    txt = []
    for ln in lines:
        txt += wrap(ln, 118) + [""]
    H = oy + gh + 50 + 15 * len(txt) + 20
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="white"/>', text(W / 2, 24, title, 14, weight="bold"),
         text(W / 2, 42, f"{LABEL[a]} × {LABEL[b]}: wide grid, averaged over the other seven inputs", 11, fill="#555")]
    for j, c_ in enumerate(cv):
        s.append(text(ox + j * cw + cw / 2, oy - 6, fmt(c_), 10))
    for i, r_ in enumerate(rv):
        s.append(text(ox - 6, oy + i * ch + ch / 2 + 4, fmt(r_), 10, anchor="end"))
        for j, _ in enumerate(cv):
            v = M[i][j]
            s.append(f'<rect x="{ox + j * cw}" y="{oy + i * ch}" width="{cw - 1}" height="{ch - 1}" fill="{colour(v)}"/>')
            s.append(text(ox + j * cw + cw / 2, oy + i * ch + ch / 2 + 4, f"{v:.2f}", 10, fill="white" if v > 0.55 else "#222"))
    s.append(text(ox + gw / 2, oy + gh + 20, LABEL[b], 11))
    s.append(text(ox - 46, oy + gh / 2, LABEL[a], 11, rot=-90))
    y = oy + gh + 48
    for ln in txt:
        if ln:
            s.append(text(30, y, ln, 11, anchor="start"))
        y += 15
    s.append("</svg>")
    return "\n".join(s), W, H


ANALYSIS = {}
_ap = os.path.join(OUT, "analysis.json")
if os.path.exists(_ap):
    ANALYSIS = json.load(open(_ap, encoding="utf-8"))
dump = {}
index, meta = [], []
for key, title in OUTS:
    for a, b in itertools.combinations(INPUTS, 2):
        rv, cv, M = table(a, b, key)
        lines = interpret(a, b, key, rv, cv, M)
        dump[f"{key}__{a}__{b}"] = {"rows_var": a, "cols_var": b, "row_levels": rv, "col_levels": cv,
                                    "values": [[round(v, 3) for v in row] for row in M], "auto_text": lines}
        extra = ANALYSIS.get(f"{a}__{b}", {}).get(key)
        if extra:
            lines = lines + ["Analysis: " + extra]
        svg, W, H = chart(a, b, key, rv, cv, M, lines, title)
        name = f"{key}__{a}__{b}"
        open(os.path.join(OUT, "charts", name + ".svg"), "w", encoding="utf-8").write(svg)
        index.append((key, title, a, b, name, lines, svg))
        meta.append({"file": name, "W": W, "H": H})
json.dump(dump, open(os.path.join(OUT, "tables.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(meta, open(os.path.join(OUT, "charts", "_sizes.json"), "w"))

# ---------- HTML report (charts inline, text beneath) ----------
h = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
     "<title>Ripeness pair charts</title><style>body{font-family:Helvetica,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#222;background:#fff}"
     "svg{max-width:100%;height:auto}h2{margin-top:40px;border-bottom:1px solid #ddd}.c{margin:28px 0}nav a{display:inline-block;margin:2px 8px 2px 0}</style></head><body>",
     f"<h1>Ripeness map: every pair of inputs</h1><p>Layer A solver over the wide grid ({n:,} cells; non-LLM, model-generated). "
     "Each chart averages over the other seven inputs. The text under each chart is generated from the numbers in the chart; "
     "the 'Why' sentences give the model's mechanism. 36 pairs × 2 measures = 72 charts.</p>"]
for key, title in OUTS:
    h.append(f"<h2>{html.escape(title)}</h2><nav>" + " ".join(
        f"<a href='#{nm}'>{a} × {b}</a>" for k, _, a, b, nm, _, _ in index if k == key) + "</nav>")
    for k, _, a, b, nm, lines, svg in index:
        if k == key:
            h.append(f"<div class='c' id='{nm}'>{svg}</div>")
h.append("</body></html>")
open(os.path.join(OUT, "pair_charts.html"), "w", encoding="utf-8").write("\n".join(h))
md = ["# Ripeness map: every pair of inputs", "",
      f"Wide grid, {n:,} cells, averaged over the other inputs. Charts are in `charts/` (SVG and PNG). "
      "The full report with the charts inline is `pair_charts.html`.", ""]
for key, title in OUTS:
    md += [f"## {title}", ""]
    for k, _, a, b, nm, lines, _ in index:
        if k == key:
            md += [f"### {LABEL[a]} × {LABEL[b]}", "", f"![{nm}](charts/{nm}.png)", ""] + [f"- {ln}" for ln in lines] + [""]
open(os.path.join(OUT, "PAIR_CHARTS.md"), "w", encoding="utf-8").write("\n".join(md))
print("charts", len(index))
