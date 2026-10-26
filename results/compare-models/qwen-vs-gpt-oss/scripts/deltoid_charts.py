"""Paired-model forest ("deltoid") charts for the Qwen3-32B vs gpt-oss-20b comparison.

Reads lever_table.csv and primed_vs_unprimed.csv (no recomputation, no rounding: every plotted
number is read back from the drawn artists and asserted equal to the CSV value) and writes
PNG figures to ../figures/ plus a markdown snippet file (figures_snippets.json) used by
build_summary_figures.py.

usage: python -I -X utf8 deltoid_charts.py     (run from anywhere; paths are relative to this file)
"""
import csv
import json
import os
import re
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(FOLDER, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import arm_labels  # noqa: E402
import collusion_colors  # noqa: E402
from lever_defs import ALIAS, DROP, ORDER, PRIMARY, TITLE  # noqa: E402

FIG = os.path.join(FOLDER, "figures")
os.makedirs(FIG, exist_ok=True)

RED, GREEN, GREY = "#c0392b", "#1e8449", "#555555"
MODELS = [("qwen", "Qwen3-32B (thinking on)", "o", +1), ("oss", "gpt-oss-20b (reasoning medium)", "s", -1)]
METRICS = [("price_index", "Price index", "price_index"),
           ("profit_gain_index", "Profit gain index", "profit_gain_index"),
           ("competitive_share", "Competitive share", "competitive_share"),
           ("matching_share", "Matching share", "matching_share"),
           ("market_price_mean", "Average spread", "abs_spread")]
# collusion direction per CSV metric (higher = more collusive?)
HIGHER_IS_COLLUSIVE = {"price_index": True, "profit_gain_index": True, "matching_share": True,
                       "market_price_mean": True, "competitive_share": False}
GROUPS = [("Replicates in sign and magnitude", lambda r: r.startswith("yes")),
          ("Sign only (same sign, size differs)", lambda r: r.startswith("in sign only")),
          ("Not detected on gpt-oss (Qwen CI excludes 0)", lambda r: r.startswith("no (gpt-oss")),
          ("New on gpt-oss (Qwen CI includes 0)", lambda r: r.startswith("new on")),
          ("Null on both (both CIs include 0)", lambda r: r.startswith("not on Qwen")),
          ("Opposite sign on the two models", lambda r: r.startswith("no (opposite"))]

# ---------------------------------------------------------------- labels
_G = arm_labels.glossary()
_KEYS = sorted(_G, key=len, reverse=True)
_PAT = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in _KEYS) + r")(?![\w-])")
SLUGS_USED = set()


# PLAIN = True: row labels are the outsider wording of each contrast (tools/analysis_style/contrast_glossary.csv,
# via arm_labels.plain_contrast) with the contrast code as a small grey second line (collusion_colors.set_plain_ticks).
# PLAIN = False restores the earlier "slug: short label" rows.
PLAIN = True
CODE_OF = {}   # wrapped plain label -> contrast code (the grey second line)


def contrast_label(c):
    raw = c
    c = ALIAS.get(c, c)

    def sub(m):
        SLUGS_USED.add(m.group(1))
        return arm_labels.label(m.group(1))
    slug_text = _PAT.sub(sub, c)
    if PLAIN:
        t = arm_labels.plain_contrast(raw)
        assert t, "no plain label for contrast %r (add it to contrast_glossary.csv)" % raw
        return t
    return slug_text


def wrap(t, width, code=None):
    out = "\n".join(textwrap.fill(p, width, break_long_words=False, break_on_hyphens=False) for p in t.split("\n"))
    return out


# ---------------------------------------------------------------- data
def fnum(x):
    return None if x in ("", None) else float(x)


def load_levers():
    rows = list(csv.DictReader(open(os.path.join(FOLDER, "lever_table.csv"), encoding="utf-8")))
    return [r for r in rows if r["topic"] != "reproducibility" and (r["topic"], r["contrast"]) not in DROP]


def load_primed():
    rows = list(csv.DictReader(open(os.path.join(FOLDER, "primed_vs_unprimed.csv"), encoding="utf-8")))
    out = {}
    for r in rows:
        out.setdefault((r["contrast"], r["metric"]), {})["qwen" if r["model"].startswith("Qwen") else "oss"] = r
    return out


# ---------------------------------------------------------------- drawing
RECORD = []   # (key, model, diff, lo, hi) as read back from the drawn artists


def colour_for(metric, diff):
    if diff == 0:
        return GREY
    toward_collusion = (diff > 0) == HIGHER_IS_COLLUSIVE[metric]
    return RED if toward_collusion else GREEN


def draw_point(ax, y, metric, model, diff, lo, hi, key, src):
    """Draw one marker + CI bar; read the values back from the artists for the assert."""
    _, _, marker, sgn = next(m for m in MODELS if m[0] == model)
    yy = y - 0.15 * sgn   # qwen above (smaller y), gpt-oss below (axis is inverted)
    col = colour_for(metric, diff)
    hollow = lo <= 0 <= hi
    bar = ax.hlines(yy, lo, hi, color=col, lw=1.6, zorder=2)
    pt, = ax.plot([diff], [yy], marker=marker, ms=7.5, mfc="white" if hollow else col, mec=col, mew=1.6, ls="none", zorder=3)
    seg = bar.get_segments()[0]
    RECORD.append((key, model, float(pt.get_xdata()[0]), float(seg[0][0]), float(seg[1][0]), src))


def forest_panel(ax, items, metric, header_rows=None, total=None, xlabel=True):
    """items: list of dict(y, label, qwen=(d,lo,hi) or None, oss=(d,lo,hi), key). Axis y is in inches (inverted)."""
    lo_all = [v for it in items for m in ("qwen", "oss") if it.get(m) for v in it[m][1:]]
    lo_all += [v for it in items for m in ("qwen", "oss") if it.get(m) for v in it[m][:1]]
    xmin, xmax = min(lo_all + [0]), max(lo_all + [0])
    pad = 0.06 * (xmax - xmin or 1)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.axvline(0, color="black", lw=1.0, zorder=1)
    for it in items:
        for m in ("qwen", "oss"):
            if it.get(m):
                d, lo, hi = it[m]
                draw_point(ax, it["y"], metric, m, d, lo, hi, it["key"] + (metric,), it["src"][m])
    for (y0, y1, text) in (header_rows or []):
        ax.axhspan(y0, y1, color="#e4e7eb", zorder=0)
        ax.text(0.01, (y0 + y1) / 2, text, transform=ax.get_yaxis_transform(), va="center", ha="left",
                fontsize=9.5, fontweight="bold", color="#222222")
    ax.set_ylim(total, 0)
    ax.set_yticks([it["y"] for it in items])
    if PLAIN:
        collusion_colors.set_plain_ticks(ax, [it["y"] for it in items], [(it["label"], CODE_OF.get(it["label"], "")) for it in items],
                                         fontsize=9, slug_fontsize=7)
    else:
        ax.set_yticklabels([it["label"] for it in items], fontsize=9, linespacing=1.05)
    ax.tick_params(axis="x", labelsize=9.5)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#dddddd", lw=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ml = dict((m[0], m[1]) for m in METRICS)[metric]
    hi_dir = HIGHER_IS_COLLUSIVE[metric]
    left_txt, right_txt = ("towards competition", "towards collusion") if hi_dir else ("towards collusion", "towards competition")
    lc, rc = (GREEN, RED) if hi_dir else (RED, GREEN)
    ax.set_xlabel("arm minus control: change in %s, 95%% CI" % ml.lower(), fontsize=9.5)
    ax.text(0.0, 1.0, "<- " + left_txt, transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color=lc, fontweight="bold")
    ax.text(1.0, 1.0, right_txt + " ->", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=rc, fontweight="bold")


def marker_legend(fig, loc="lower center", ncol=3, y=0.0):
    h = [Line2D([], [], marker="o", color=GREY, mfc=GREY, ls="none", ms=8, label="Qwen3-32B (thinking on): circle, upper of each pair"),
         Line2D([], [], marker="s", color=GREY, mfc=GREY, ls="none", ms=8, label="gpt-oss-20b (reasoning medium): square, lower of each pair"),
         Line2D([], [], marker="o", color=GREY, mfc="white", mew=1.6, ls="none", ms=8, label="hollow = 95% CI crosses 0"),
         Patch(color=RED, label="red = shifts towards collusion"), Patch(color=GREEN, label="green = shifts towards competition")]
    fig.legend(handles=h, loc=loc, ncol=ncol, fontsize=9, frameon=False, bbox_to_anchor=(0.5, y))


def row_height(label):
    return max(0.55, 0.155 * (label.count("\n") + 1) + 0.2 + (0.12 if PLAIN else 0.0))


def lever_items(rows, metric, order_by="price_index"):
    out = []
    for r in rows:
        if r["metric"] != metric:
            continue
        out.append(r)
    return out


def as_item(r, width):
    q = (fnum(r["qwen_diff"]), fnum(r["qwen_lo"]), fnum(r["qwen_hi"])) if r["qwen_diff"] != "" else None
    o = (fnum(r["oss_diff"]), fnum(r["oss_lo"]), fnum(r["oss_hi"]))
    src = {"qwen": ("lever_table.csv", r["topic"], r["contrast"], r["metric"], "qwen"), "oss": ("lever_table.csv", r["topic"], r["contrast"], r["metric"], "oss")}
    lab = wrap(contrast_label(r["contrast"]), width)
    CODE_OF[lab] = r["contrast"]
    return dict(label=lab, qwen=q, oss=o, key=(r["topic"], r["contrast"]), src=src, verdict=r["replicates"])


# ---- overview: one figure per metric, rows = lever contrasts, grouped by verdict, sorted by gpt-oss effect
def overview_figure(rows, metric, fname):
    lev = [r for r in rows if r["metric"] == metric and (r["topic"], r["contrast"]) in PRIMARY]
    items, headers, y = [], [], 0.0
    for gname, test in GROUPS:
        g = [as_item(r, 50) for r in lev if test(r["replicates"])]
        if not g:
            continue
        g.sort(key=lambda it: it["oss"][0])
        headers.append((y, y + 0.36, "%s  (%d)" % (gname, len(g))))
        y += 0.36
        for it in g:
            h = row_height(it["label"])
            it["y"] = y + h / 2
            y += h
            items.append(it)
        y += 0.12
    assert len(items) == len(lev), (metric, len(items), len(lev))
    ml = dict((m[0], m[1]) for m in METRICS)[metric]
    fig = plt.figure(figsize=(10.6, y + 2.2))
    ax = fig.add_axes([4.6 / 10.6, 1.25 / (y + 2.2), 5.7 / 10.6, y / (y + 2.2)])
    forest_panel(ax, items, metric, headers, y)
    fig.suptitle("%s: effect of each collusion lever on Qwen3-32B and gpt-oss-20b (%d lever contrasts)" % (ml, len(items)),
                 fontsize=11, fontweight="bold", x=0.02, ha="left", y=1 - 0.12 / (y + 2.2))
    marker_legend(fig, ncol=2, y=0.004)
    fig.savefig(os.path.join(FIG, fname), dpi=100)
    plt.close(fig)
    return [it["key"] for it in items]


# ---- per-lever: stacked panels, one per metric, rows = that lever's contrasts, sorted by gpt-oss price-index effect
def lever_figure(rows, topic, fname):
    rr = [r for r in rows if r["topic"] == topic]
    contrasts = []
    for r in rr:
        if r["contrast"] not in contrasts:
            contrasts.append(r["contrast"])
    pi = {r["contrast"]: float(r["oss_diff"]) for r in rr if r["metric"] == "price_index"}
    contrasts.sort(key=lambda c: pi[c])
    ys, y = {}, 0.0
    heights = {}
    for c in contrasts:
        lab = wrap(contrast_label(c), 50)
        CODE_OF[lab] = c
        heights[c] = row_height(lab)
    panel_h = sum(heights.values())
    top, bot, gap = 0.55, 0.55, 0.85
    H = len(METRICS) * (panel_h + top + bot) + 1.0
    fig = plt.figure(figsize=(10.6, H))
    keys = []
    for i, (m, ml, _) in enumerate(METRICS):
        items, y = [], 0.0
        for c in contrasts:
            r = next(r for r in rr if r["contrast"] == c and r["metric"] == m)
            it = as_item(r, 50)
            it["y"] = y + heights[c] / 2
            y += heights[c]
            items.append(it)
            keys.append(it["key"])
        y0 = H - (i * (panel_h + top + bot) + top + panel_h)
        ax = fig.add_axes([4.6 / 10.6, y0 / H, 5.7 / 10.6, panel_h / H])
        forest_panel(ax, items, m, None, panel_h)
        ax.set_title(ml, fontsize=10.5, fontweight="bold", loc="center", pad=16)
    marker_legend(fig, ncol=2, y=0.002)
    fig.savefig(os.path.join(FIG, fname), dpi=100)
    plt.close(fig)
    return contrasts


# ---- primed vs unprimed
def primed_figure(primed, fname):
    contrasts = []
    for (c, m) in primed:
        if c not in contrasts:
            contrasts.append(c)
    contrasts.sort(key=lambda c: float(primed[(c, "price_index")]["oss"]["diff"]))
    labs = {c: wrap(contrast_label(c), 50) for c in contrasts}
    CODE_OF.update({labs[c]: c for c in contrasts})
    hs = {c: row_height(labs[c]) for c in contrasts}
    panel_h = sum(hs.values())
    top, bot = 0.55, 0.55
    H = len(METRICS) * (panel_h + top + bot) + 1.0
    fig = plt.figure(figsize=(10.6, H))
    for i, (m, ml, _) in enumerate(METRICS):
        items, y = [], 0.0
        for c in contrasts:
            d = primed[(c, m)]
            def tr(r):
                return (float(r["diff"]), float(r["lo"]), float(r["hi"]))
            it = dict(label=labs[c], y=y + hs[c] / 2, key=("primed", c),
                      qwen=tr(d["qwen"]) if "qwen" in d else None, oss=tr(d["oss"]),
                      src={"qwen": ("primed_vs_unprimed.csv", c, m, "qwen"), "oss": ("primed_vs_unprimed.csv", c, m, "oss")})
            y += hs[c]
            items.append(it)
        y0 = H - (i * (panel_h + top + bot) + top + panel_h)
        ax = fig.add_axes([4.6 / 10.6, y0 / H, 5.7 / 10.6, panel_h / H])
        forest_panel(ax, items, m, None, panel_h)
        ax.set_title(ml, fontsize=10.5, fontweight="bold", pad=16)
    marker_legend(fig, ncol=2, y=0.002)
    fig.savefig(os.path.join(FIG, fname), dpi=100)
    plt.close(fig)
    return contrasts


# ---------------------------------------------------------------- verification against the CSVs
def verify(rows, primed):
    lt = {(r["topic"], r["contrast"], r["metric"]): r for r in csv.DictReader(open(os.path.join(FOLDER, "lever_table.csv"), encoding="utf-8"))}
    pv = {}
    for r in csv.DictReader(open(os.path.join(FOLDER, "primed_vs_unprimed.csv"), encoding="utf-8")):
        pv[(r["model"], r["contrast"], r["metric"])] = r
    n = 0
    for key, model, d, lo, hi, src in RECORD:
        if src[0] == "lever_table.csv":
            r = lt[(src[1], src[2], src[3])]
            exp = tuple(float(r["%s_%s" % (model, f)]) for f in ("diff", "lo", "hi"))
        else:
            r = pv[("Qwen3-32B" if model == "qwen" else "gpt-oss-20b", src[1], src[2])]
            exp = (float(r["diff"]), float(r["lo"]), float(r["hi"]))
        assert (d, lo, hi) == exp, (key, model, (d, lo, hi), exp)
        n += 1
    return n


def pin_cpu(mask=0xFF0):
    """Analysis jobs keep vCore 0 free (affinity 0xFF0); no-op off Windows."""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetProcessAffinityMask(k.GetCurrentProcess(), mask)
    except Exception:
        pass


def main():
    pin_cpu()
    rows = load_levers()
    primed = load_primed()
    snippets = {"overview": {}, "lever": {}, "primed": None}
    for m, ml, _ in METRICS:
        fn = "overview_%s.png" % m
        overview_figure(rows, m, fn)
        snippets["overview"][m] = fn
    for t in ORDER:
        if any(r["topic"] == t for r in rows):
            fn = "lever_%s.png" % t
            cs = lever_figure(rows, t, fn)
            snippets["lever"][t] = dict(file=fn, contrasts=cs)
    pc = primed_figure(primed, "primed_vs_unprimed.png")
    snippets["primed"] = dict(file="primed_vs_unprimed.png", contrasts=pc)
    n = verify(rows, primed)
    print("verified %d plotted (model, diff, lo, hi) triples equal the CSV values exactly" % n)
    json.dump(snippets, open(os.path.join(HERE, "figures_snippets.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
