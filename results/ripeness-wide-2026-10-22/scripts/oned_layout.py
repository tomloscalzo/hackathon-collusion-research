"""One-input (1-D) chart pages: for each input, two line charts side by side (share where collusion is chosen; mean theta*),
each with two lines (all markets; markets with no minimum price step), then a terms table, a bold Interpretation and Details.
Usage: python -X utf8 oned_layout.py <oned_tables.json> <out_dir> [<findings_html_fragment>]"""
import html, json, os, sys

T = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]
FINDINGS = open(sys.argv[3], encoding="utf-8").read() if len(sys.argv) > 3 else ""
os.makedirs(os.path.join(OUT, "charts"), exist_ok=True)
FONT = "Helvetica,Arial,sans-serif"
ORDER = ["fineRatio", "slope", "rhoTip", "N", "delta", "pEvidence", "tick", "phi", "sBarRatio"]
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
MEAS = [("—", "Share where collusion is chosen", "The fraction of model scenarios (all combinations of the other eight inputs) in "
         "which a profit-maximising cartel chooses to collude at all.", "left chart"),
        ("θ*", "Chosen collusion intensity", "How far above the competitive spread the cartel sets prices, from 0 (competitive) to 1 "
         "(monopoly), averaged over scenarios; scenarios with no collusion count as 0.", "right chart")]
INTERP = {
    "fineRatio": "It appears that a higher fine ratio (the fine as a multiple of one round of a firm's full-collusion profit) is the "
                 "single strongest force against collusion, cutting both how often and how hard firms collude, with large effects even "
                 "at moderate fines. It most likely works only through detection: the fine is paid only if an investigation starts and "
                 "finds evidence, so fines combined with a sensitive regulator screen or frequent tips are far more effective than fines "
                 "alone. The pattern is the same in markets with and without a minimum price step.",
    "slope": "It appears that a steeper regulator screen slope (how strongly wide spreads trigger an investigation) makes collusion "
             "steadily rarer and, even more strongly, gentler. Because the screen reacts to how wide the spread is, cartels that still "
             "collude most likely lower their prices to stay below its notice, which is why intensity falls faster than how often they "
             "collude. The pattern is the same in markets with and without a minimum price step.",
    "rhoTip": "It appears that a higher tip probability (the chance each round that an investigation starts from a tip, whatever the "
              "prices) makes collusion less common and less intense. Unlike the regulator screen, tips cannot be avoided by pricing more "
              "gently, so they mostly shorten the cartel's expected life; combined with a heavy enough fine and a high enough chance of "
              "a guilty finding, they appear to remove collusion altogether.",
    "N": "It appears that more market makers make collusion both rarer and gentler, in all markets and in markets with no minimum price "
         "step. Each firm's share of the cartel profit shrinks as firms are added, while undercutting the others still wins most of the "
         "market for a round, so firms need more patience to resist cheating.",
    "delta": "It appears that more patience (the chance the market continues for another round) makes collusion more common and more "
             "intense, because future cartel profits are worth protecting and the threat of a price war carries more weight. In markets "
             "with no minimum price step, how often firms collude keeps rising and then levels off, while intensity peaks at high "
             "patience and eases slightly at the very top, most likely because very patient cartels choose gentler prices to avoid "
             "investigations. Across all markets both measures drop at the highest patience; that drop appears to come from a modelling "
             "simplification in markets with a minimum price step (an investigation that finds nothing is treated as worse for firms "
             "than a conviction).",
    "pEvidence": "It appears that a higher P(evidence | investigation) (the chance an investigation produces a guilty finding and a "
                 "fine) makes collusion rarer and gentler, because the fine becomes more likely to be paid; it therefore matters only "
                 "when there is a fine. The effect is clearest in markets with no minimum price step. Across all markets it flattens at "
                 "the top, which appears to come from a modelling simplification in markets with a minimum price step (an investigation "
                 "that finds nothing is treated as worse for firms than a conviction).",
    "tick": "It appears that a larger tick size (the minimum price step) makes collusion less common and less intense. Part of this is "
            "most likely real: with a price step, ordinary competition already earns a small profit, so colluding gains less over "
            "competing, and the cartel cannot fine-tune a modest price. Part appears to come from a modelling simplification in these "
            "markets (an investigation that finds nothing is treated as worse for firms than a conviction), which makes any "
            "investigation more costly.",
    "phi": "It appears that a larger preferenced volume share (orders split evenly among firms whatever the price) makes collusion "
           "slightly more common and slightly more intense. Because undercutting cannot win that protected volume, cheating pays less, "
           "so the cartel is easier to hold together. The effect is small compared with the enforcement inputs.",
    "sBarRatio": "The reservation spread ratio (the room between cost and the spread at which customers stop trading) appears to have a "
                 "small effect. In markets with no minimum price step, more room makes collusion steadily rarer and gentler, most likely "
                 "because the wider spreads a cartel would charge are more visible to the regulator screen and the fine looms larger "
                 "against the profit from a small markup. Across all markets both measures first rise and then fall, most likely because "
                 "markets with a price step need some room above normal prices before a cartel can raise prices at all.",
}
NOTES = {
    "fineRatio": "Combined lever: in markets with no price step and no tips, collusion is chosen almost exactly when regulator screen "
                 "slope × P(evidence | investigation) × fine ratio × (reservation spread ratio − 1) < 4 (98.9% of those scenarios), so "
                 "the four inputs substitute for each other. With a regulator screen slope of 0 and no tips, the fine never binds.",
    "slope": "Intensity responds more than frequency (largest share of variance explained of any input for θ*). With a fine ratio "
             "≥ 125, a slope ≥ 0.05 leaves 1.1% of scenarios colluding; at slope 0.01 with fine ratio 125, 22% still collude.",
    "rhoTip": "Hard threshold: collusion is impossible once tip probability × P(evidence | investigation) × fine ratio exceeds 1. At "
              "the ripe baseline a 5% tip probability removes collusion entirely (fig4 E).",
    "N": "Textbook threshold: a cartel of N firms holds roughly when patience δ ≥ 1 − 1/N (about 0.5 for 2 firms, 0.75 for 4, 0.9 for "
         "10); preferenced volume lowers it slightly. See the Patience × Number of market makers pair chart.",
    "delta": "Markets with no price step: how often firms collude rises 0.12 → 0.51 and levels off from δ 0.95; θ* peaks at 0.34 "
             "(δ 0.95). The all-markets dip at δ 0.99 disappears when every investigation ends in a conviction (P(evidence) = 1), "
             "which confirms it is the modelling simplification.",
    "pEvidence": "With no fine, P(evidence | investigation) has no effect in markets without a price step (share 0.741 at every level) "
                 "and raises collusion in markets with a price step (the modelling simplification).",
    "tick": "At P(evidence | investigation) = 1, where the simplification has no effect, larger tick sizes still lower how often "
            "firms collude (for example N = 2: 0.349 → 0.279 → 0.195), so part of the effect is real.",
    "phi": "Preferenced volume matters mainly through the incentive to cheat: among 10-firm markets the sustainable share rises "
           "0.388 → 0.679 across φ.",
    "sBarRatio": "In markets with no price step, the reservation spread ratio acts as a multiplier on the regulator screen: slope 0.1 "
                 "at s̄/s₀ 2, 0.05 at 3 and 0.025 at 5 all give the same share (0.419) and θ* (0.282).",
}
CSS = (f"body{{font-family:{FONT};color:#222;background:#fff;margin:0}}.page{{width:1180px;padding:20px 20px 28px}}"
       "h1{font-size:18px;margin:0 0 2px;text-align:center}.sub{font-size:12px;color:#555;text-align:center;margin-bottom:10px}"
       ".figs{display:flex;flex-wrap:wrap;gap:16px;justify-content:center}.fig{text-align:center}.ft{font-weight:bold;font-size:13px}"
       "table.terms{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0 4px}"
       "table.terms th,table.terms td{border:1px solid #ccc;padding:5px 7px;text-align:left;vertical-align:top}"
       "table.terms th{background:#f2f4f7}table.terms td:nth-child(1),table.terms td:nth-child(2){font-weight:bold}"
       ".ih,.dh{font-weight:bold;text-decoration:underline;font-size:14px;margin:28px 0 16px}"
       ".interp{font-weight:bold;font-size:13px;line-height:1.5}.det{font-size:12px;line-height:1.5}.det p{margin:4px 0}"
       ".findings{font-size:13px;line-height:1.5}.findings table{border-collapse:collapse;font-size:12px;margin:8px 0}"
       ".findings th,.findings td{border:1px solid #ccc;padding:4px 6px;text-align:left;vertical-align:top}.findings th{background:#f2f4f7}")


def line_svg(o, key, var):
    lv = o["levels"]; W, H = 540, 320; L, R, Tp, B = 56, 20, 30, 76
    ymax = 0.8
    X = lambda i: L + 24 + (W - L - R - 48) * (i / (len(lv) - 1) if len(lv) > 1 else 0.5)
    Y = lambda v: Tp + (H - Tp - B) * (1 - v / ymax)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">']
    for k in range(0, 9):
        v = k / 10
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#eee"/>')
        s.append(f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" font-size="10" text-anchor="end">{v:.1f}</text>')
    for i, l in enumerate(lv):
        s.append(f'<text x="{X(i):.1f}" y="{H - B + 16}" font-size="10" text-anchor="middle">{float(l):g}</text>')
    s.append(f'<text x="{(L + W - R) / 2}" y="{H - B + 34}" font-size="12" text-anchor="middle">'
             f'{html.escape(TERMS[var][1])} ({html.escape(TERMS[var][0])}) · levels evenly spaced</text>')
    series = [(o[f"{key}_all"], "#08519c", "", "All markets")]
    if var != "tick":
        series.append((o[f"{key}_tick0"], "#d95f02", ' stroke-dasharray="6 4"', "Markets with no minimum price step"))
    for si, (vals, col, dash, _) in enumerate(series):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"{dash}/>')
        for i, v in enumerate(vals):
            if v is not None:
                s.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.5" fill="{col}"/>')
                other = series[1 - si][0][i] if len(series) > 1 else None
                below = other is not None and (v < other or (v == other and si == 1))
                s.append(f'<text x="{X(i):.1f}" y="{Y(v) + (15 if below else -7):.1f}" font-size="9" text-anchor="middle" fill="{col}">{v:.2f}</text>')
    for n, (_, col, dash, lab) in enumerate(series):
        y = H - 8; x = L + n * 200
        s.append(f'<line x1="{x}" x2="{x + 26}" y1="{y - 4}" y2="{y - 4}" stroke="{col}" stroke-width="2.5"{dash}/>'
                 f'<text x="{x + 32}" y="{y}" font-size="11">{lab}</text>')
    s.append("</svg>")
    return "\n".join(s)


def trend(vals):
    a, b = vals[0], vals[-1]; m = max(vals); k = vals.index(m)
    if 0 < k < len(vals) - 1 and m - max(a, b) > 0.01:
        return f"peaks at {m:.2f} in the middle of the range ({a:.2f} at the lowest level, {b:.2f} at the highest)"
    return f"{'rises' if b > a else 'falls'} from {a:.2f} to {b:.2f}"


def page(var):
    o = T[var]; lv = o["levels"]
    figs = "".join(f"<div class='fig'><div class='ft'>{t}</div>{line_svg(o, k, var)}</div>"
                   for k, t in (("share", "Share of scenarios where collusion is chosen"), ("theta", "Mean chosen collusion intensity θ*")))
    rows = [TERMS[var] + ("horizontal axis (both charts)",)] + [m for m in MEAS]
    tbl = ("<table class='terms'><tr><th>Symbol</th><th>Term</th><th>Plain-English meaning</th><th>Shown as</th></tr>" +
           "".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td><td>{d}</td></tr>" for a, b, c, d in rows)
           + "</table>")
    det = [f"Range shown: {html.escape(TERMS[var][1])} from {float(lv[0]):g} to {float(lv[-1]):g}; each point averages every combination "
           "of the other eight inputs in the wide grid."]
    for k, lab in (("share", "Share where collusion is chosen"), ("theta", "Chosen collusion intensity θ*")):
        txt = f"{lab}: all markets {trend(o[k + '_all'])}"
        if var != "tick":
            txt += f"; markets with no minimum price step {trend([v for v in o[k + '_tick0']])}"
        det.append(txt + ".")
    det.append(f"Share of the variation across the whole grid explained by this input alone: {o['eta2_share']:.3f} for how often, "
               f"{o['eta2_theta']:.3f} for how hard (the rest comes from the other inputs and their combinations).")
    det.append(NOTES[var])
    body = (f"<h1>{html.escape(TERMS[var][1])} ({html.escape(TERMS[var][0])})</h1><div class='sub'>Wide grid (1,036,800 scenarios), "
            "averaged over the other eight inputs · model-generated, no LLM</div>"
            f"<div class='figs'>{figs}</div>{tbl}<div class='ih'>Interpretation</div><div class='interp'>{html.escape(INTERP[var])}</div>"
            "<div class='dh'>Details</div><div class='det'>" + "".join(f"<p>{html.escape(d)}</p>" for d in det) + "</div>")
    return body


sizes, bodies = [], []
for v in ORDER:
    b = page(v); bodies.append((v, b))
    open(os.path.join(OUT, "charts", f"oned__{v}.html"), "w", encoding="utf-8").write(
        f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='page'>{b}</div></body></html>")
    sizes.append({"file": f"oned__{v}", "W": 1220, "H": 1500})
json.dump(sizes, open(os.path.join(OUT, "charts", "_sizes.json"), "w"))
nav = " · ".join(f"<a href='#{v}'>{html.escape(TERMS[v][1])}</a>" for v in ORDER)
doc = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
       f"<title>Ripeness one-input charts</title><style>{CSS}body{{max-width:1220px;margin:0 auto;padding:0 12px}}"
       ".page{width:auto;border-bottom:2px solid #ddd}svg{max-width:100%;height:auto}nav{font-size:13px;line-height:1.8}</style></head><body>",
       "<h1 style='font-size:22px;margin-top:20px'>Ripeness map: one input at a time</h1>"
       "<p style='font-size:13px'>Each section shows how one input moves how often a profit-maximising cartel colludes (left) and how "
       "hard (right), averaged over all combinations of the other eight inputs in the wide grid. The solid line is all markets; the "
       "dashed line is markets with no minimum price step, which are free of the tick-market modelling simplification. Inputs are "
       "ordered by impact. Two-input charts: <a href='../pairs/pair_charts.html'>pair_charts.html</a>.</p>",
       FINDINGS, f"<nav><b>Inputs:</b> {nav}</nav>"]
doc += [f"<div class='page' id='{v}'>{b}</div>" for v, b in bodies]
doc.append("</body></html>")
open(os.path.join(OUT, "oned_charts.html"), "w", encoding="utf-8").write("\n".join(doc))
print("pages", len(bodies))
