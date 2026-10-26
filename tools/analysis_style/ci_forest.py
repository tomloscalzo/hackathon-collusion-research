"""Forest chart of deltas and confidence intervals (shared helper).

Owner's rule (2026-10-25, verbatim): "For all adhoc charts, when reporting deltas and confidence
intervals, can you also include the CI chart below the table (showing centroids and CI high and low
bars for each attribute and metric)? That helps visualize borderline cases which aren't
statistically significant, but are close."

forest(table, out_png, title=...) draws one panel per metric, one row per contrast/attribute:
  - point = the estimate (centroid); horizontal bar = the CI (low to high); dashed line at 0;
  - red = a move in the COLLUSION direction, green = a move in the COMPETITION direction (the
    direction rules of collusion_colors.direction: e.g. +price index is red, +competitive share is
    green); a neutral blue-grey for metrics with no collusion direction or an estimate of exactly 0;
  - HOLLOW marker = the CI crosses zero (not statistically distinguishable from no change);
    filled marker = the CI excludes zero;
  - panels share one x-axis range where the metrics' scales are within about 3x of each other
    (comparable axes); a panel with a much larger scale gets its own range, flagged "own scale";
  - row labels are "slug: short label" via arm_labels when the label starts with a glossary slug,
    otherwise the table's own contrast text; wrapped, at least 9 pt.

`table` = list of dicts or a pandas DataFrame with columns
  label, metric, estimate, lo, hi   and optionally   p (a p-value, e.g. Holm-adjusted).
`legend_md(table)` returns the legend for the chart (rows via arm_labels.legend_table).
`from_markdown_table(header, rows)` parses a Markdown table whose cells read "est [lo, hi]".
"""
import math
import re
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

try:
    from . import arm_labels as AL, collusion_colors as CC
except ImportError:  # run with tools/analysis_style on sys.path
    import arm_labels as AL, collusion_colors as CC

RED, GREEN, GREY = "#c0392b", "#1e8449", "#5d7a99"
MIN_PT = 9
MAX_ROWS = 26          # longer tables are split over several charts
_NUM = r"[+\-−]?\s?\d*\.?\d+(?:[eE][+\-]?\d+)?"
_CI = re.compile(r"(" + _NUM + r")\s*(%|pp)?\s*(?:\*+)?\s*\[\s*(" + _NUM + r")\s*%?\s*(?:,|;|\bto\b)\s*(" + _NUM + r")\s*%?\s*\]")


def _f(s):
    return float(str(s).replace("−", "-").replace(" ", "").replace("+", ""))


def _rows(table):
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    return list(table)


def _slug_of(text):
    g = AL.glossary()
    m = re.match(r"^([^\s:(]+)\s*(?::|\(|$)", str(text).strip())   # "slug", "slug: ...", "slug (...)"
    first = m.group(1) if m else None
    return first if first and (first in g or AL._base(first) in g) else None


def row_label(text, wrap=30):
    """'slug: short label' when the text starts with a glossary slug; else the text. Wrapped."""
    text = str(text).strip()
    s = _slug_of(text)
    if s:
        short = AL.glossary()[AL._base(s)]["short_label"]
        rest = text[len(s):].strip(" :")
        text = f"{s}: {short}" + (f" ({rest})" if rest else "")
    return textwrap.fill(text, wrap)


def slugs_in(labels):
    out = []
    for t in labels:
        s = _slug_of(t)
        if s and s not in out:
            out.append(s)
    return out


def _color(metric, est):
    if est == 0 or est is None:
        return GREY
    d = CC.direction(metric)
    if d == CC.NEUTRAL:
        return GREY
    return RED if (est > 0) == (d == CC.COLLUSION) else GREEN


def forest(table, out_png, title=None, dpi=110, sharex=True, xlabel=None, plain=False):
    """Draw the forest chart(s); returns the list of PNG paths written (split if > MAX_ROWS rows).
    plain=True: rows show the outsider wording (arm_labels.plain / plain_contrast) with the slug or contrast
    text as a small grey second line, instead of "slug: short label"."""
    rows = _rows(table)
    labels = list(dict.fromkeys(r["label"] for r in rows))
    metrics = list(dict.fromkeys(r["metric"] for r in rows))
    chunks = [labels[i:i + MAX_ROWS] for i in range(0, len(labels), MAX_ROWS)] or [[]]
    paths = []
    for k, chunk in enumerate(chunks):
        p = out_png if len(chunks) == 1 else out_png.replace(".png", f"_part{k + 1}.png")
        t = title if len(chunks) == 1 else f"{title} (part {k + 1} of {len(chunks)})"
        _draw([r for r in rows if r["label"] in chunk], chunk, metrics, p, t, dpi, sharex, xlabel, plain)
        paths.append(p)
    return paths


def _draw(rows, labels, metrics, out_png, title, dpi, sharex, xlabel=None, plain=False):
    nm, nr = len(metrics), len(labels)
    half = {}
    for m in metrics:
        vals = [abs(v) for r in rows if r["metric"] == m for v in (r["lo"], r["hi"], r["estimate"])]
        half[m] = max(vals) if vals and max(vals) > 0 else 1.0
    ref = sorted(half.values())[len(half) // 2]
    own = {m: (not sharex) or half[m] > 3 * ref or half[m] * 3 < ref for m in metrics}
    shared = max([half[m] for m in metrics if not own[m]] or [ref])
    fig_h = max(2.8, (0.62 if plain else 0.5) * nr + 2.2)
    fig, axes = plt.subplots(1, nm, figsize=(max(7.5, 3.0 + 2.5 * nm), fig_h), sharey=True,
                             constrained_layout=True, squeeze=False)
    axes = axes[0]
    ys = {l: nr - 1 - i for i, l in enumerate(labels)}
    for ax, m in zip(axes, metrics):
        h = half[m] if own[m] else shared
        ax.set_xlim(-h * 1.12, h * 1.12)
        ax.axvline(0, color="black", ls="--", lw=1)
        for r in (r for r in rows if r["metric"] == m):
            y, est, lo, hi = ys[r["label"]], r["estimate"], r["lo"], r["hi"]
            c = _color(m, est)
            ax.plot([lo, hi], [y, y], color=c, lw=2.2, solid_capstyle="butt")
            ax.plot([lo, lo], [y - .12, y + .12], color=c, lw=1.5)
            ax.plot([hi, hi], [y - .12, y + .12], color=c, lw=1.5)
            hollow = lo <= 0 <= hi
            ax.plot([est], [y], "o", ms=7.5, mfc="white" if hollow else c, mec=c, mew=1.8, zorder=3)
            p = r.get("p")
            if p is not None and not (isinstance(p, float) and math.isnan(p)):
                ax.annotate(f"p={p:.3g}", (min(hi, h * 1.1), y), xytext=(4, 0), textcoords="offset points",
                            fontsize=MIN_PT, va="center", color="#444")
        ax.set_title(textwrap.fill(str(m), 22) + ("\n(own scale)" if own[m] and sharex and nm > 1 else ""),
                     fontsize=10)
        ax.set_ylim(-0.7, nr - 0.3)
        if plain and ax is axes[0]:
            pairs = CC.plain_tick_pairs(list(reversed(labels)), wrap=34)   # contrast text first, then slug
            CC.set_plain_ticks(ax, range(nr), pairs, fontsize=MIN_PT)
        elif not plain:
            ax.set_yticks(range(nr))
            ax.set_yticklabels([row_label(l) for l in reversed(labels)], fontsize=MIN_PT)
        ax.tick_params(axis="x", labelsize=MIN_PT)
        ax.grid(axis="x", alpha=.25)
        ax.set_xlabel(xlabel or "difference: estimate and 95% CI", fontsize=MIN_PT)
    handles = [Line2D([], [], marker="o", ls="", mfc=RED, mec=RED, label="collusion-direction move, CI excludes 0"),
               Line2D([], [], marker="o", ls="", mfc=GREEN, mec=GREEN, label="competition-direction move, CI excludes 0"),
               Line2D([], [], marker="o", ls="", mfc="white", mec="#444", label="hollow = CI crosses 0 (not significant)"),
               Line2D([], [], marker="o", ls="", mfc=GREY, mec=GREY, label="no collusion direction")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, fontsize=MIN_PT, frameon=False)
    if title:
        fig.suptitle(textwrap.fill(title, max(40, int(fig.get_figwidth() * 8))), fontsize=11)
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def legend_md(table):
    """Markdown legend under a forest chart: both axes (rows = contrasts, panels = metrics) and markers."""
    rows = _rows(table)
    labels = list(dict.fromkeys(r["label"] for r in rows))
    metrics = list(dict.fromkeys(r["metric"] for r in rows))
    out = ["<small>", "",
           "**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high "
           "(the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero "
           "(no difference). Red = a move in the collusion direction, green = a move in the competition direction "
           "(rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. "
           "A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; "
           "the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs "
           "by more than about 3x from the others are marked \"own scale\".", "",
           "**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above"
           + (" (a glossary slug is expanded to \"slug: short label\")." if slugs_in(labels) else "."), ""]
    sl = slugs_in(labels)
    if sl:
        out += [AL.legend_table(sl)]
    out += ["**Panels (x-axis = the difference in that metric):**", "",
            "| Panel | Direction | Red means | Green means |", "|---|---|---|---|"]
    for m in metrics:
        d = CC.direction(m)
        if d == CC.COLLUSION:
            a, b = "metric goes up (more collusive)", "metric goes down (less collusive)"
        elif d == CC.COMPETITION:
            a, b = "metric goes down (less competitive)", "metric goes up (more competitive)"
        else:
            a = b = "none (blue-grey: no collusion direction)"
        out.append(f"| {str(m).replace('|', '/')} | {AL._DIR_TEXT[d]} | {a} | {b} |")
    out += ["", "</small>"]
    return "\n".join(out) + "\n"


def from_markdown_table(header, body):
    """Parse a Markdown table (lists of cell strings). Cells 'est [lo, hi]' become points; the leading
    non-CI, non-numeric cells form the row label; a later column headed Holm / p gives p.
    Returns a list of dicts (label, metric, estimate, lo, hi, p)."""
    recs = []
    for cells in body:
        lab, pts, pval = [], [], None
        for j, c in enumerate(cells):
            cc = re.sub(r"\*+", "", c).strip()
            m = _CI.match(cc)
            if m and len(cc) > m.end() + 30:      # a CI buried in a prose cell is not a table of deltas
                m = None
            h = header[j] if j < len(header) else ""
            if m:
                pts.append((h, _f(m.group(1)), _f(m.group(3)), _f(m.group(4))))
            elif not pts:
                t = re.sub(r"[*_`]", "", c).strip()
                if t and re.search(r"[A-Za-z]", t) and not re.fullmatch(_NUM + r"%?", t):
                    lab.append(t)
            elif re.search(r"holm|\bp\b|p-value|adj", h, re.I):
                mm = re.search(r"\d*\.?\d+(?:e[+\-]?\d+)?", c)
                if mm:
                    pval = float(mm.group(0))
        for h, e, lo, hi in pts:
            hh = re.sub(r"[*_`]", "", h).strip()
            mlab = [x for x in lab if CC.direction(x) != CC.NEUTRAL]
            if CC.direction(hh) == CC.NEUTRAL and mlab:      # metrics are the rows: "arm / metric | diff [CI]"
                hh = mlab[-1]
                rest = [x for x in lab if x is not mlab[-1]]
                label = " / ".join(rest) if rest else "(all)"
            else:
                label = " / ".join(lab) if lab else "(row)"
            recs.append(dict(label=label, metric=hh, estimate=e, lo=lo, hi=hi, p=pval))
    return recs
