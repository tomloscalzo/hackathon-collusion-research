"""Two report figures as standalone SVG (no plotting library needed).
Usage: python -X utf8 make_figures.py <sim_dir> <out_dir>"""
import csv, os, sys
from collections import defaultdict

SIM, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
FONT = 'font-family="Helvetica,Arial,sans-serif"'


def colour(v):
    """0 -> pale, 1 -> deep blue."""
    v = max(0.0, min(1.0, v))
    a, b = (247, 251, 255), (8, 69, 148)
    return "rgb(%d,%d,%d)" % tuple(int(a[i] + (b[i] - a[i]) * v) for i in range(3))


def text(x, y, s, size=12, anchor="middle", weight="normal", fill="#222", rot=None):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" {FONT}{t}>{s}</text>'


# ---------------- Figure 1: ripeness map ----------------
rows = list(csv.DictReader(open(os.path.join(SIM, "ripeness-map.csv"), encoding="utf-8")))
rows = [r for r in rows if not r["error"]]
for r in rows:
    r["_c"] = 1.0 if float(r["theta_star"]) > 1e-9 else 0.0
    r["_t"] = float(r["theta_star"])
FR = sorted({r["fineRatio"] for r in rows}, key=float)
SL = sorted({r["slope"] for r in rows}, key=float)
DE = sorted({r["delta"] for r in rows}, key=float)
NN = sorted({r["N"] for r in rows}, key=float)


def grid(rk, ck, rv, cv, key):
    g = defaultdict(list)
    for r in rows:
        g[(r[rk], r[ck])].append(r[key])
    return {(a, b): sum(g[(a, b)]) / len(g[(a, b)]) for a in rv for b in cv}


panels = [
    ("A. Share of cells where collusion is chosen (θ* > 0)", "fineRatio", "slope", FR, SL, "_c",
     "Fine ratio (fine ÷ one round of full-collusion profit per firm)", "Regulator screen slope"),
    ("B. Mean chosen collusion intensity θ*", "fineRatio", "slope", FR, SL, "_t",
     "Fine ratio (fine ÷ one round of full-collusion profit per firm)", "Regulator screen slope"),
    ("C. Share of cells where collusion is chosen (θ* > 0)", "delta", "N", DE, NN, "_c",
     "Patience δ (continuation probability)", "Number of market makers N"),
]
cw, ch = 70, 46
W, H = 1080, 420
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="white"/>',
       text(W / 2, 26, "Ripeness map: Layer A solver over 10,368 parameter cells (means over all other inputs)", 16, weight="bold")]
for pi, (title, rk, ck, rv, cv, key, rlab, clab) in enumerate(panels):
    ox, oy = 110 + pi * 340, 90
    g = grid(rk, ck, rv, cv, key)
    svg.append(text(ox + len(cv) * cw / 2, oy - 34, title, 12, weight="bold"))
    for j, c in enumerate(cv):
        svg.append(text(ox + j * cw + cw / 2, oy - 8, c, 11))
    svg.append(text(ox + len(cv) * cw / 2, oy + len(rv) * ch + 26, clab, 11))
    for i, rlv in enumerate(rv):
        svg.append(text(ox - 8, oy + i * ch + ch / 2 + 4, rlv, 11, anchor="end"))
        for j, c in enumerate(cv):
            v = g[(rlv, c)]
            svg.append(f'<rect x="{ox + j * cw}" y="{oy + i * ch}" width="{cw - 2}" height="{ch - 2}" fill="{colour(v)}"/>')
            svg.append(text(ox + j * cw + cw / 2 - 1, oy + i * ch + ch / 2 + 4, f"{v:.2f}", 12,
                            fill="white" if v > 0.55 else "#222"))
    svg.append(text(ox - 52, oy + len(rv) * ch / 2, rlab, 11, rot=-90))
svg.append(text(W / 2, H - 40, "Each square averages every combination of the other seven inputs in the grid. Darker = more collusion.", 11, fill="#555"))
svg.append(text(W / 2, H - 22, "Model-generated reference map (no LLM). Source: sweeps/ripeness-map.yaml; raw cells in excel/ripeness_map_cells.csv.", 11, fill="#555"))
svg.append("</svg>")
open(os.path.join(OUT, "fig1_ripeness_map.svg"), "w", encoding="utf-8").write("\n".join(svg))

# ---------------- Figure 2: reference (null) bands ----------------
bands = list(csv.DictReader(open(os.path.join(SIM, "reference-bands", "bands.csv"), encoding="utf-8")))
items = [(f'{b["contrast"]}: {b["arm_a"]} − {b["arm_b"]} ({b["statistic"]})', b["block"].strip("{}").replace("seat=", ""),
          float(b["point_full"]), float(b["band_lo"]), float(b["band_hi"])) for b in bands]
lo, hi = -1.05, 1.05
W, rowh, top = 1000, 22, 80
H = top + len(items) * rowh + 90
x0, x1 = 470, 940
X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
SEATC = {"grim": "#08519c", "tit-for-tat": "#238b45", "noise": "#a50f15"}
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="white"/>',
       text(W / 2, 26, "Reference (null) bands for the pre-declared contrasts, scripted seats", 16, weight="bold"),
       text(W / 2, 46, "Point = contrast with all runs; bar = bootstrap band at the LLM design size (10 paraphrase clusters × seeds). LLM estimates are added after the runs.", 11, fill="#555")]
for v in [-1, -0.5, 0, 0.5, 1]:
    svg.append(f'<line x1="{X(v)}" y1="{top - 8}" x2="{X(v)}" y2="{top + len(items) * rowh}" stroke="{"#999" if v == 0 else "#e5e5e5"}" stroke-width="1"/>')
    svg.append(text(X(v), top + len(items) * rowh + 16, f"{v:g}", 11))
svg.append(text((x0 + x1) / 2, top + len(items) * rowh + 34, "Contrast (arm A minus arm B, statistic units)", 11))
for i, (lab, seat, pt, bl, bh) in enumerate(items):
    y = top + i * rowh + rowh / 2
    c = SEATC.get(seat, "#444")
    svg.append(text(x0 - 120, y + 4, lab, 11, anchor="end"))
    svg.append(text(x0 - 110, y + 4, seat, 11, anchor="start", fill=c))
    svg.append(f'<line x1="{X(bl)}" y1="{y}" x2="{X(bh)}" y2="{y}" stroke="{c}" stroke-width="6" stroke-opacity="0.35" stroke-linecap="round"/>')
    svg.append(f'<circle cx="{X(pt)}" cy="{y}" r="4" fill="{c}"/>')
svg.append(text(W / 2, H - 30, "Most bands are points at 0 because scripted seats do not respond to the economic incentives; P1-A′ is non-zero because its partner is a committed competitor.", 11, fill="#555"))
svg.append(text(W / 2, H - 14, "Source: sweeps/reference-bands.yaml (1,000 runs per cell). Model-generated, no LLM.", 11, fill="#555"))
svg.append("</svg>")
open(os.path.join(OUT, "fig2_reference_bands.svg"), "w", encoding="utf-8").write("\n".join(svg))
print("figures written to", OUT)
