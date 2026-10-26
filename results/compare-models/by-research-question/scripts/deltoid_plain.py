"""Paired-model forest ("deltoid") charts with plain-English row labels (shared by build_movers.py and build_addendum.py).

Every row is one contrast (arm minus its control, paired on wording and seed). Two markers per row:
circle = Qwen3-32B with thinking on (upper), square = gpt-oss-20b at reasoning effort medium (lower).
Bars are 95% bootstrap CIs; hollow = the CI crosses the reference line; red = towards collusion, green =
towards competition (by the metric's collusion direction). Row labels: the plain wording (black) with the
contrast code small and grey underneath (collusion_colors.set_plain_ticks).

Values are read from lever_table.csv / primed_vs_unprimed.csv / the dossier CSVs as strings and converted
with float() only; every drawn (estimate, lo, hi) is read back from the matplotlib artists and asserted equal
to the source CSV value (verify_records). Nothing is recomputed.
"""
import csv
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)                                   # results/compare-models/by-research-question
REPO = os.path.abspath(os.path.join(FOLDER, "..", "..", ".."))
CMP = os.path.join(REPO, "results", "compare-models", "qwen-vs-gpt-oss")
DOSS = os.path.join(REPO, "results", "claims-dossiers")
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import arm_labels  # noqa: E402
import collusion_colors as CC  # noqa: E402

RED, GREEN, GREY, BLUE = "#c0392b", "#1e8449", "#555555", "#2c5d8f"
QWEN_NAME = "Qwen3-32B, thinking on"
OSS_NAME = "gpt-oss-20b, reasoning medium"
MODELS = {"qwen": ("o", -1), "oss": ("s", +1)}       # marker, vertical offset sign (axis inverted: qwen above)
METRICS = [("price_index", "Price index", "0 = cost, 1 = monopoly price"),
           ("profit_gain_index", "Profit index", "share of the possible extra profit"),
           ("competitive_share", "Competitive share", "share of rounds undercutting the rival"),
           ("matching_share", "Matching share", "share of rounds copying the rival's price"),
           ("market_price_mean", "Market price", "lowest quote, 1.00 to 5.00")]
HIGHER_IS_COLLUSIVE = {"price_index": True, "profit_gain_index": True, "matching_share": True,
                       "market_price_mean": True, "competitive_share": False}
FAMILY_TITLE = {
    "environment": "A. Market conditions (\"ripeness\"): fine level, chat, number of firms",
    "priming": "B. Priming and tendencies: printed prices, start rule, personas, incentives, ethics rules",
    "observation": "C. Observation and control: reasoning monitor, watchdog, questions, self-ratings",
    "reference": "Reference (calibration, not levers): firms told outright to collude or compete",
    "reproducibility": "Reference: the identical prompt re-run (gpt-oss only)",
}
RECORD = []          # (source, key, model, metric, est, lo, hi) read back from the artists


def pin_cpu(mask=0xFF0):
    """Analysis jobs keep vCore 0 free (affinity 0xFF0); no-op off Windows."""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetProcessAffinityMask(k.GetCurrentProcess(), mask)
    except Exception:
        pass


# ------------------------------------------------------------------ data
def lever_rows():
    """dict (topic, contrast, metric) -> row of lever_table.csv (strings)."""
    with open(os.path.join(CMP, "lever_table.csv"), encoding="utf-8") as f:
        return {(r["topic"], r["contrast"], r["metric"]): r for r in csv.DictReader(f)}


def lever_item(L, topic, contrast, metric):
    """One row's (est, lo, hi) per model from lever_table.csv; None for a missing model."""
    r = L[(topic, contrast, metric)]
    q = None if r["qwen_diff"].strip() == "" else (float(r["qwen_diff"]), float(r["qwen_lo"]), float(r["qwen_hi"]))
    o = None if r["oss_diff"].strip() == "" else (float(r["oss_diff"]), float(r["oss_lo"]), float(r["oss_hi"]))
    return dict(qwen=q, oss=o, src=("lever_table.csv", (topic, contrast, metric)), verdict=r["replicates"], row=r)


# ------------------------------------------------------------------ drawing
def _colour(metric, est, neutral=False):
    if neutral:
        return BLUE
    if est == 0:
        return GREY
    return RED if (est > 0) == HIGHER_IS_COLLUSIVE[metric] else GREEN


def _point(ax, y, metric, model, tri, src, ref=0.0, neutral=False, ms=7.0):
    marker, sgn = MODELS[model]
    est, lo, hi = tri
    yy = y + 0.11 * sgn * ROW_UNIT
    col = _colour(metric, est - ref, neutral)
    hollow = lo <= ref <= hi
    bar = ax.hlines(yy, lo, hi, color=col, lw=1.6, zorder=2)
    pt, = ax.plot([est], [yy], marker=marker, ms=ms, mfc="white" if hollow else col, mec=col, mew=1.5, ls="none", zorder=3)
    seg = bar.get_segments()[0]
    RECORD.append((src[0], src[1], model, metric, float(pt.get_xdata()[0]), float(seg[0][0]), float(seg[1][0])))


ROW_UNIT = 1.0


def layout(groups, label_wrap, fs, slug_fs, header_h=0.30, gap=0.10, min_row=0.42):
    """groups: [(title or None, [item...])]; each item has 'plain' and 'code'. Sets item['y'] (inches from top),
    returns (total height in inches, header bands [(y0, y1, title)])."""
    lh, sh = fs * 1.22 / 72, slug_fs * 1.25 / 72
    y, bands = 0.0, []
    for title, items in groups:
        if title:
            bands.append((y, y + header_h, title))
            y += header_h
        for it in items:
            it["plain_wrapped"] = "\n".join(textwrap.wrap(it["plain"], label_wrap, break_on_hyphens=False))
            n = it["plain_wrapped"].count("\n") + 1
            h = max(min_row, n * lh + (sh * (it["code"].count("\n") + 1) if it.get("code") else 0) + 0.12)
            it["y"] = y + h / 2
            y += h
        y += gap
    return y, bands


def panel(ax, items, metric, total_h, bands, title=None, ref=0.0, neutral=False, xlabel=None, show_labels=True,
          fs=9, slug_fs=7, dir_labels=True, xlim=None, ms=7.0):
    vals = [v for it in items for m in ("qwen", "oss") if it.get(m) for v in it[m]] + [ref]
    lo, hi = (min(vals), max(vals)) if xlim is None else xlim
    pad = 0.06 * (hi - lo or 1)
    ax.set_xlim(lo - pad, hi + pad) if xlim is None else ax.set_xlim(*xlim)
    ax.set_ylim(total_h, 0)
    ax.axvline(ref, color="black", lw=1.0, zorder=1)
    for (y0, y1, t) in bands:
        ax.axhspan(y0, y1, color="#e6e9ee", zorder=0, lw=0)
        if show_labels:
            ax.annotate(t, xy=(0, (y0 + y1) / 2), xycoords=("axes fraction", "data"), xytext=(-LABEL_IN * 72 + 4, 0),
                        textcoords="offset points", ha="left", va="center", fontsize=fs, fontweight="bold",
                        color="#1a1a1a", annotation_clip=False)
    for it in items:
        for m in ("qwen", "oss"):
            if it.get(m):
                _point(ax, it["y"], metric, m, it[m], it["src"], ref=ref, neutral=neutral, ms=ms)
    if show_labels:
        CC.set_plain_ticks(ax, [it["y"] for it in items], [(it["plain_wrapped"], it.get("code", "")) for it in items],
                           fontsize=fs, slug_fontsize=slug_fs)
    else:
        ax.set_yticks([it["y"] for it in items])
        ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=fs - 0.5)
    ax.grid(axis="x", color="#dddddd", lw=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if title:
        ax.set_title(title, fontsize=fs + 0.5, fontweight="bold", pad=14)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fs - 0.5)
    if dir_labels and not neutral:
        up = HIGHER_IS_COLLUSIVE[metric]
        narrow = ax.get_position().width * ax.figure.get_figwidth() < 3.0
        w = "" if narrow else "more "
        lt, rt = ("< %scompetitive" % w, "%scollusive >" % w) if up else ("< %scollusive" % w, "%scompetitive >" % w)
        lc, rc = (GREEN, RED) if up else (RED, GREEN)
        ax.text(0.0, 1.0, lt, transform=ax.transAxes, ha="left", va="bottom", fontsize=fs - 1, color=lc, fontweight="bold")
        ax.text(1.0, 1.0, rt, transform=ax.transAxes, ha="right", va="bottom", fontsize=fs - 1, color=rc, fontweight="bold")


LABEL_IN = 3.0


def marker_legend(fig, y, fs=8.5, neutral=False, ref_text="0", ncol=3):
    h = [Line2D([], [], marker="o", color=GREY, mfc=GREY, ls="none", ms=7, label="circle = %s" % QWEN_NAME),
         Line2D([], [], marker="s", color=GREY, mfc=GREY, ls="none", ms=7, label="square = %s" % OSS_NAME),
         Line2D([], [], marker="o", color=GREY, mfc="white", mew=1.5, ls="none", ms=7, label="hollow = 95%% CI crosses %s" % ref_text)]
    if not neutral:
        h += [Patch(color=RED, label="red = more collusive"), Patch(color=GREEN, label="green = more competitive")]
    fig.legend(handles=h, loc="lower center", ncol=ncol, fontsize=fs, frameon=False, bbox_to_anchor=(0.5, y),
               handletextpad=0.4, columnspacing=1.2)


# ------------------------------------------------------------------ verification
def verify_records(extra_sources=None):
    """Assert every drawn triple equals the source CSV value. extra_sources: dict name -> callable(key, model, metric)
    returning the expected (est, lo, hi) from that CSV."""
    L = lever_rows()
    n = 0
    for src, key, model, metric, est, lo, hi in RECORD:
        if src == "lever_table.csv":
            r = L[key]
            exp = tuple(float(r["%s_%s" % (model, f)]) for f in ("diff", "lo", "hi"))
        else:
            exp = extra_sources[src](key, model, metric)
        assert (est, lo, hi) == exp, (src, key, model, metric, (est, lo, hi), exp)
        n += 1
    return n


def fmt_ci(tri, nd=3):
    if tri is None:
        return "not run"
    e, lo, hi = tri
    return "%+.*f [%+.*f, %+.*f]" % (nd, e, nd, lo, nd, hi)
