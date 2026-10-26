"""Arm and code labels for every figure script (reads arm_glossary.csv next to this file).

Owner's rule: every diagram has a legend table underneath defining every slug or
code shown; on big heat maps (more than about 10 labelled rows or columns) the
short description also goes INSIDE the chart, never a bare slug.

  label(slug)               -> "slug: short label"   (bare slug if unknown, with a warning)
  labels(slugs, wrap=None)  -> list of labels; wrap=N inserts a line break after N chars
  legend_table(slugs, long=None) -> Markdown table (slug | meaning), directly under a figure;
                              long=True adds the long description column (default: when
                              more than 10 slugs). Unknown slugs are listed as "(not in glossary)".
  tick_labels(slugs, wrap=34) -> labels for axis ticks (wrapped)
  plain(slug)               -> the outsider wording (plain_label column; no jargon, says WHAT differs),
                              falling back to short_label with a warning
  plain_contrast(text)      -> plain wording of a contrast "arm - control (...)" from contrast_glossary.csv
                              (the one thing that differs from the control); None if not listed
  contrast_family(text)     -> environment / priming / observation / reference / reproducibility (or None)
  For charts with plain labels and the slug as a small grey second line, see
  collusion_colors.set_plain_ticks and ci_forest.forest(..., plain=True).
  axis_legend(rows=, cols=, panels=, metric=, colour=) -> the per-figure legend grouped by
                              axis: "Rows (y-axis)", "Columns (x-axis)", optional "Panels", and
                              "Colour (metric)" with the metric's collusion direction. Owner's
                              rule: define EVERY code on BOTH axes plus the colour metric.
"""
import csv
import os
import textwrap
import warnings

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arm_glossary.csv")
_G = None


def glossary():
    """dict slug -> {family, short_label, long_description}."""
    global _G
    if _G is None:
        with open(_PATH, newline="", encoding="utf-8") as f:
            _G = {r["slug"]: r for r in csv.DictReader(f)}
    return _G


def _base(slug):
    """Strip a trailing thinking-mode suffix like '__t1' or ' t1' only if the full slug is unknown."""
    g = glossary()
    s = str(slug)
    if s in g:
        return s
    for sep in ("__", " "):
        if sep in s and s.split(sep)[0] in g:
            return s.split(sep)[0]
    return s


def label(slug):
    g = glossary()
    b = _base(slug)
    if b not in g:
        warnings.warn(f"arm_labels: '{slug}' is not in arm_glossary.csv; add it")
        return str(slug)
    return f"{slug}: {g[b]['short_label']}"


def plain(slug):
    """Outsider wording for a slug (plain_label column); short_label if the plain label is missing."""
    g = glossary()
    b = _base(slug)
    if b not in g:
        warnings.warn(f"arm_labels: '{slug}' is not in arm_glossary.csv; add it")
        return str(slug)
    return g[b].get("plain_label") or g[b]["short_label"]


_C = None


def contrast_glossary():
    """dict contrast text -> {factor_family, plain_label} (contrast_glossary.csv next to this file)."""
    global _C
    if _C is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contrast_glossary.csv")
        with open(path, newline="", encoding="utf-8") as f:
            _C = {r["contrast"]: r for r in csv.DictReader(f)}
    return _C


def plain_contrast(text):
    r = contrast_glossary().get(str(text).strip())
    return r["plain_label"] if r else None


def contrast_family(text):
    r = contrast_glossary().get(str(text).strip())
    return r["factor_family"] if r else None


def labels(slugs, wrap=None):
    out = [label(s) for s in slugs]
    return [textwrap.fill(t, wrap) for t in out] if wrap else out


def tick_labels(slugs, wrap=34):
    return labels(slugs, wrap)


def legend_table(slugs, long=None, key=False):
    """Markdown legend table for the slugs shown in a figure (de-duplicated, order kept).
    key=True adds a leading "#" column (1-based), for axes that show a numbered key."""
    g = glossary()
    seen, rows = set(), []
    for s in slugs:
        if s in seen:
            continue
        seen.add(s)
        b = _base(s)
        rows.append((s, g[b]["short_label"] if b in g else "(not in glossary)",
                     g[b]["long_description"] if b in g else ""))
    if long is None:
        long = len(rows) > 10
    esc = lambda t: str(t).replace("|", "/").replace("\n", " ")
    head = ("| # " if key else "") + "| Slug | Meaning |" + (" Description |" if long else "")
    sep = ("|---" if key else "") + "|---|---|" + ("---|" if long else "")
    body = [(f"| {i + 1} " if key else "") + f"| {esc(s)} | {esc(sh)} |" + (f" {esc(ld)} |" if long else "")
            for i, (s, sh, ld) in enumerate(rows)]
    return "\n".join([head, sep] + body) + "\n"


NL = "\n"
_DIR_TEXT = {
    "collusion": "higher = more collusive (on the red/green maps: red end)",
    "competition": "higher = more competitive (on the red/green maps: green end)",
    "neutral": "no collusion direction (neutral hue)",
}


def _direction(metric):
    try:
        from . import collusion_colors as _cc
    except ImportError:
        import collusion_colors as _cc
    return _cc.direction(metric)


def axis_legend(rows=None, cols=None, panels=None, metric=None, colour=None,
                row_name=None, col_name=None, panel_name=None, long=None, row_key=False, col_key=False):
    """Markdown legend for one figure, grouped by axis.

    rows / cols / panels: the codes shown on the y-axis, the x-axis and as panel titles
    (each a list; None or empty = section omitted). metric: the slug (or list of slugs)
    shown by colour or bar length; its glossary meaning and collusion direction are
    printed. colour: optional sentence describing the figure's actual colour scale (use it
    for pre-existing figures whose colours were not changed). *_name: the variable name
    shown in the sub-heading, e.g. row_name="arm" -> "Rows (y-axis): arm".
    row_key / col_key: True when that axis shows a numbered key (collusion_colors.set_arm_ticks fallback);
    the table then has a "#" column giving each number's code and description.
    """
    out = []

    def sec(title, name, codes, key=False):
        if not codes:
            return
        note = " (the axis shows the numbers in the # column)" if key else ""
        out.append(f"**{title}{': ' + name if name else ''}**{note}" + NL)
        out.append(legend_table(list(codes), long=True if key else long, key=key))

    sec("Rows (y-axis)", row_name, rows, row_key)
    sec("Columns (x-axis)", col_name, cols, col_key)
    sec("Panels", panel_name, panels)
    if metric is not None:
        ms = [metric] if isinstance(metric, str) else list(metric)
        g = glossary()
        out.append("**Colour / value (metric)**" + NL)
        out.append("| Metric | Meaning | Direction |" + NL + "|---|---|---|")
        for m in ms:
            b = _base(m)
            mean = g[b]["long_description"] if b in g else "(not in glossary)"
            out.append(f"| {m} | {str(mean).replace('|', '/')} | {_DIR_TEXT[_direction(m)]} |")
        out[-1] += NL
        if colour:
            out.append(f"Colour scale: {colour}" + NL)
    return NL.join(out)


if __name__ == "__main__":
    import sys
    print(legend_table(sys.argv[1:] or list(glossary())[:5]))
