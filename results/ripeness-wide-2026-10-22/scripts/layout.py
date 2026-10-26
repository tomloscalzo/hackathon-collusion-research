"""Lay out the 72 pair charts as standalone HTML pages (heat map, terms table, Interpretation, details) plus one combined page.
Reads tables.json (values + factual text), interp.json (qualitative interpretation) and analysis.json (detailed analysis).
Usage: python -X utf8 layout.py <pairs_out dir>"""
import html, json, os, sys

D = sys.argv[1]
T = json.load(open(os.path.join(D, "tables.json"), encoding="utf-8"))
A = json.load(open(os.path.join(D, "analysis.json"), encoding="utf-8"))
I = json.load(open(os.path.join(D, "interp.json"), encoding="utf-8"))
os.makedirs(os.path.join(D, "charts"), exist_ok=True)

TERMS = {
    "delta": ("δ", "Patience", "The chance the market continues for another round. High patience means firms care a lot about future "
              "profits; the expected number of rounds is 1 ÷ (1 − δ)."),
    "N": ("N", "Number of market makers", "How many firms quote prices in the market."),
    "phi": ("φ", "Preferenced volume share", "The share of customer orders split evenly among all firms no matter who quotes the "
            "best price. Undercutting cannot win this volume."),
    "tick": ("ι", "Tick size", "The minimum price step. With a coarse tick, prices sit on a grid, firms cannot undercut by tiny "
             "amounts, and competition stops a step or two above cost."),
    "slope": ("slope", "Regulator screen slope", "How sensitive the regulator's automated screen is to wide spreads. A steeper "
              "slope means more collusive prices are more likely to trigger an investigation."),
    "rhoTip": ("ρ_tip", "Tip probability", "The chance each round that an investigation starts from a tip (for example a "
               "whistleblower or a customer complaint), whatever the prices."),
    "pEvidence": ("P(evidence)", "P(evidence | investigation)", "The chance that an investigation, once started, finds enough "
                  "evidence for a guilty finding and a fine."),
    "fineRatio": ("F ratio", "Fine ratio", "The fine, measured as a multiple of one round of a firm's full-collusion (monopoly) profit."),
    "sBarRatio": ("s̄/s₀", "Reservation spread ratio", "How much room there is between the cheapest sustainable spread (cost, s₀) "
                  "and the spread at which customers stop trading (s̄). More room means bigger potential cartel profits."),
}
MEASURE = {
    "share": ("—", "Share where collusion is chosen", "The fraction of model scenarios (all combinations of the other seven inputs) "
              "in which a profit-maximising cartel chooses to collude at all."),
    "theta": ("θ*", "Chosen collusion intensity", "How far above the competitive spread the cartel sets prices, from 0 "
              "(competitive) to 1 (monopoly), averaged over scenarios; scenarios with no collusion count as 0."),
}
TITLE = {"share": "Share of scenarios where collusion is chosen", "theta": "Mean chosen collusion intensity θ*"}
FONT = "Helvetica,Arial,sans-serif"
CSS = (f"body{{font-family:{FONT};color:#222;background:#fff;margin:0}}.page{{width:720px;padding:20px 20px 28px}}"
       "h1{font-size:17px;margin:0 0 2px;text-align:center}.sub{font-size:12px;color:#555;text-align:center;margin-bottom:10px}"
       "table.terms{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0 4px}"
       "table.terms th,table.terms td{border:1px solid #ccc;padding:5px 7px;text-align:left;vertical-align:top}"
       "table.terms th{background:#f2f4f7}table.terms td:nth-child(1),table.terms td:nth-child(2){font-weight:bold}.ih{font-weight:bold;text-decoration:underline;font-size:14px;margin:28px 0 16px}"
       ".interp{font-weight:bold;font-size:13px;line-height:1.45}.dh{font-weight:bold;text-decoration:underline;font-size:14px;margin:28px 0 16px}"
       ".det{font-size:12px;line-height:1.45}.det p{margin:4px 0}")


def colour(v):
    v = max(0.0, min(1.0, v)); a, b = (247, 251, 255), (8, 69, 148)
    return "rgb(%d,%d,%d)" % tuple(int(a[k] + (b[k] - a[k]) * v) for k in range(3))


def fmt(v):
    return f"{float(v):g}"


def heat_svg(t, a, b):
    rv, cv, M = t["row_levels"], t["col_levels"], t["values"]
    cw, ch = min(62, 380 / len(cv)), 30
    left, top = 190, 40
    W, H = left + len(cv) * cw + 20, top + len(rv) * ch + 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">']
    for j, c in enumerate(cv):
        s.append(f'<text x="{left + j * cw + cw / 2}" y="{top - 8}" font-size="11" text-anchor="middle">{fmt(c)}</text>')
    for i, r in enumerate(rv):
        s.append(f'<text x="{left - 8}" y="{top + i * ch + ch / 2 + 4}" font-size="11" text-anchor="end">{fmt(r)}</text>')
        for j, _ in enumerate(cv):
            v = M[i][j]
            s.append(f'<rect x="{left + j * cw}" y="{top + i * ch}" width="{cw - 1}" height="{ch - 1}" fill="{colour(v)}"/>')
            s.append(f'<text x="{left + j * cw + cw / 2}" y="{top + i * ch + ch / 2 + 4}" font-size="11" text-anchor="middle" '
                     f'fill="{"white" if v > 0.55 else "#222"}">{v:.2f}</text>')
    s.append(f'<text x="{left + len(cv) * cw / 2}" y="{top + len(rv) * ch + 24}" font-size="12" text-anchor="middle">'
             f'{html.escape(TERMS[b][1])} ({html.escape(TERMS[b][0])})</text>')
    s.append(f'<text x="{left - 8}" y="14" font-size="11" font-weight="bold" text-anchor="end">'
             f'Rows: {html.escape(TERMS[a][1])} ↓</text>')
    s.append("</svg>")
    return "\n".join(s), H


def pair_block(a, b):
    svgs, hs = [], []
    for key in ("share", "theta"):
        svg, h = heat_svg(T[f"{key}__{a}__{b}"], a, b)
        svgs.append(f"<div class='fig'><div class='ft'>{html.escape(TITLE[key])}</div>{svg}</div>")
        hs.append(h)
    rows = [TERMS[a] + ("rows (both charts)",), TERMS[b] + ("columns (both charts)",),
            MEASURE["share"] + ("cell values, left chart",), MEASURE["theta"] + ("cell values, right chart",)]
    tbl = ("<table class='terms'><tr><th>Symbol</th><th>Term</th><th>Plain-English meaning</th><th>Shown as</th></tr>" +
           "".join(f"<tr><td>{html.escape(sy)}</td><td>{html.escape(n)}</td><td>{html.escape(d)}</td><td>{w}</td></tr>"
                   for sy, n, d, w in rows) + "</table>")
    it = I.get(f"{a}__{b}", {})
    interp = (f"<div class='interp'><p>Whether firms collude: {html.escape(it.get('share', ''))}</p>"
              f"<p>How hard they collude: {html.escape(it.get('theta', ''))}</p></div>")
    det = ""
    words = len(it.get("share", "").split()) + len(it.get("theta", "").split())
    for key, lab in (("share", "Share where collusion is chosen (left chart)"), ("theta", "Chosen collusion intensity θ* (right chart)")):
        t = T[f"{key}__{a}__{b}"]
        det += f"<div class='dsub'>{lab}</div>" + "".join(f"<p>{html.escape(x)}</p>" for x in t["auto_text"])
        ana = A.get(f"{a}__{b}", {}).get(key)
        if ana:
            det += f"<p><em>Mechanism detail:</em> {html.escape(ana)}</p>"
        words += sum(len(x.split()) for x in t["auto_text"]) + (len(ana.split()) if ana else 0)
    body = (f"<h1>{html.escape(TERMS[a][1])} × {html.escape(TERMS[b][1])}</h1><div class='sub'>Wide grid, averaged over the other "
            "seven inputs · model-generated, no LLM</div>"
            f"<div class='figs'>{''.join(svgs)}</div>{tbl}"
            f"<div class='ih'>Interpretation</div>{interp}"
            f"<div class='dh'>Details</div><div class='det'>{det}</div>")
    est = 80 + max(hs) + 260 + int(words / 22) * 18 + 500
    return body, est


CSS = CSS.replace(".page{width:720px;padding:20px 20px 28px}", ".page{width:1260px;padding:20px 20px 28px}") + (
    ".figs{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}.fig{text-align:center}"
    ".ft{font-weight:bold;font-size:13px;margin-bottom:2px}.interp p{margin:4px 0}.dsub{font-weight:bold;font-size:12px;margin-top:8px}")

pages, sizes = [], []
for k in T:
    if not k.startswith("share__"):
        continue
    _, a, b = k.split("__")
    body, est = pair_block(a, b)
    name = f"pair__{a}__{b}"
    open(os.path.join(D, "charts", name + ".html"), "w", encoding="utf-8").write(
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='page'>{body}</div></body></html>")
    pages.append((a, b, name, body))
    sizes.append({"file": name, "W": 1300, "H": est})
json.dump(sizes, open(os.path.join(D, "charts", "_sizes.json"), "w"))

nav = " · ".join(f"<a href='#{n}'>{TERMS[a][0]} × {TERMS[b][0]}</a>" for a, b, n, _ in pages)
out = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
       f"<title>Ripeness pair charts</title><style>{CSS}body{{max-width:1300px;margin:0 auto;padding:0 12px}}"
       ".page{width:auto;border-bottom:2px solid #ddd}nav{font-size:12px;line-height:1.8}svg{max-width:100%;height:auto}</style></head><body>",
       "<h1 style='font-size:22px;margin-top:20px'>Ripeness map: every pair of inputs</h1>"
       "<p style='font-size:13px'>Layer A solver over the wide grid (1,036,800 parameter cells; non-LLM, model-generated). For each "
       "pair of inputs: the share of scenarios where collusion is chosen (left) and the mean chosen collusion intensity (right), each "
       "averaged over the other seven inputs; a table of terms; a plain-language <b><u>Interpretation</u></b>; and details with "
       "numbers.</p>", f"<nav>{nav}</nav>"]
out += [f"<div class='page' id='{n}'>{body}</div>" for a, b, n, body in pages]
out.append("</body></html>")
open(os.path.join(D, "pair_charts.html"), "w", encoding="utf-8").write(chr(10).join(out))

md = ["# Ripeness map: every pair of inputs", "", "Open `pair_charts.html` for the formatted version. Each PNG in `charts/` "
      "shows one pair: both charts side by side, the terms table, the **Interpretation** and the details.", ""]
for a, b, n, _ in pages:
    it = I.get(f"{a}__{b}", {})
    md += [f"## {TERMS[a][1]} × {TERMS[b][1]}", "", f"![{n}](charts/{n}.png)", "", "<u>**Interpretation**</u>", "",
           "**Whether firms collude: " + it.get("share", "") + "**", "", "**How hard they collude: " + it.get("theta", "") + "**", ""]
open(os.path.join(D, "PAIR_CHARTS.md"), "w", encoding="utf-8").write(chr(10).join(md))
print("pairs", len(pages))
