"""Shared colour convention for every heat map in the project.

Owner's rule (verbatim): "any number indicating collusion should be highlighted
reddish, and any number indicating competition should be highlighted greenish."

  collusion-direction metrics (higher = more collusive)  -> "RdYlGn_r"  (high = red)
  competition-direction metrics (higher = more competitive) -> "RdYlGn"  (high = green)
  difference maps: diverging, centred at 0, MORE collusive = red and MORE
      competitive = green (for a competition-direction metric the sign is
      flipped, which is the same as using "RdYlGn" instead of "RdYlGn_r")
  no collusion direction (rounds played, n, latency, effect sizes, correlations)
      -> a neutral hue ("Blues"; signed neutral values use NEUTRAL_DIVERGING,
      blue-white-purple), with a note on the colourbar saying so.

Every colourbar is labelled with the metric and the red/green note (or the
neutral note). Value ranges (vmin, vmax) stay with the calling script.
"""
from matplotlib.colors import LinearSegmentedColormap

COLLUSION_CMAP = "RdYlGn_r"
COMPETITION_CMAP = "RdYlGn"
NEUTRAL_CMAP = "Blues"
NEUTRAL_DIVERGING = LinearSegmentedColormap.from_list(
    "neutral_diverging", ["#2c7bb6", "#f7f7f7", "#7b3294"])

COLLUSION, COMPETITION, NEUTRAL = "collusion", "competition", "neutral"

NOTE = {
    COLLUSION: "red = more collusive / green = more competitive",
    COMPETITION: "red = more collusive / green = more competitive",
    NEUTRAL: "neutral colour: this number has no collusion direction",
}

# exact metric names whose direction the substring rules get wrong or cannot know
OVERRIDES = {
    "first_undercut_round": NEUTRAL, "score_after_first_undercut_mean": NEUTRAL,
    "score_before_first_undercut_mean": NEUTRAL, "punish_lag": NEUTRAL, "punish_round_first": NEUTRAL,
    "br_rate": COMPETITION, "br_rate_excl_floor_rounds": COMPETITION, "match_rate": COLLUSION,
    "equal_quote_share_mean": COLLUSION, "evidence_ending": COLLUSION,
    "explicit_agreement_first_round": NEUTRAL,   # a round number: later is less collusive, so no simple direction
}

# substring -> direction; first match wins (order matters)
_RULES = [
    (NEUTRAL, ("rounds_played", "rounds played", "latency", "n_games", "n games", "effect size",
               "epsilon", "cramer", "correlation", "spearman", "count of games")),
    (COMPETITION, ("competitive_share", "competitive share", "undercut", "best_response",
                   "best-response", "best response", "war_length", "war length")),
    (COLLUSION, ("price_index", "price index", "profit_gain", "profit gain", "matching",
                 "abs_spread", "absolute spread", "spread", "hold", "punish", "collusive",
                 "ended_by_evidence", "ended by evidence", "evidence_end", "ended on evidence",
                 "agreement", "collusion", "harm")),
]


def direction(metric):
    """'collusion', 'competition' or 'neutral' for a metric name or phrase."""
    m = str(metric).lower()
    if m in OVERRIDES:
        return OVERRIDES[m]
    for d, keys in _RULES:
        if any(k in m for k in keys):
            return d
    return NEUTRAL


def cmap_for(metric_or_direction, diff=False):
    """Colormap name (or object) for a metric. diff=True gives the diverging
    version (same maps: red = more collusive, green = more competitive; centre
    the norm at 0 with vmin=-R, vmax=+R)."""
    d = metric_or_direction if metric_or_direction in (COLLUSION, COMPETITION, NEUTRAL) \
        else direction(metric_or_direction)
    if d == COLLUSION:
        return COLLUSION_CMAP
    if d == COMPETITION:
        return COMPETITION_CMAP
    return NEUTRAL_DIVERGING if diff else NEUTRAL_CMAP


def cbar_label(metric_label, metric=None, diff=False, extra=None):
    """Colourbar label: the metric, then the red/green (or neutral) note."""
    d = direction(metric if metric is not None else metric_label)
    head = f"difference in {metric_label}" if diff else str(metric_label)
    if extra:
        head += f" ({extra})"
    return head + "\n" + NOTE[d]


def text_color(value, vmin, vmax):
    """Annotation colour that reads on both ends of the red-yellow-green maps
    (dark ends -> white text, pale middle -> black)."""
    rel = (value - vmin) / (vmax - vmin + 1e-12)
    return "white" if (rel > 0.85 or rel < 0.15) else "black"


MIN_ANNOT_PT = 9.5


def fit_annotations(fig, ax, nrows, ncols, texts, fs=MIN_ANNOT_PT, max_scale=3.0):
    """Owner's rule: "in heat maps, make numbers larger on large heat maps so
    they're more visible on a screen." Grows the figure (never shrinks it) until
    the longest annotation fits its cell at `fs` points (>= ~9-10 pt) and returns
    fs. `texts` is any iterable of the annotation strings (may contain newlines).
    Call after the axes position is set (e.g. after subplots_adjust) and before saving.
    If even max_scale growth cannot fit the text, the caller should drop the
    annotations, keep the colour and write a CSV of the values."""
    pos = ax.get_position()
    w, h = fig.get_size_inches()
    cw, ch = pos.width * w / max(ncols, 1), pos.height * h / max(nrows, 1)
    lines = [t.split("\n") for t in texts if t]
    if not lines:
        return fs
    need_w = max(len(s) for ls in lines for s in ls) * fs * 0.62 / 72 + 0.06
    need_h = max(len(ls) for ls in lines) * fs * 1.25 / 72 + 0.06
    scale = min(max(1.0, need_w / cw, need_h / ch), max_scale)
    if scale > 1.0:
        fig.set_size_inches(w * scale, h * scale)
    return fs


def annotations_fit(fig, ax, nrows, ncols, texts, fs=MIN_ANNOT_PT, max_scale=3.0):
    """True if fit_annotations could fit the text within max_scale growth."""
    pos = ax.get_position(); w, h = fig.get_size_inches()
    cw, ch = pos.width * w / max(ncols, 1), pos.height * h / max(nrows, 1)
    lines = [t.split("\n") for t in texts if t]
    if not lines:
        return True
    need_w = max(len(s) for ls in lines for s in ls) * fs * 0.62 / 72 + 0.06
    need_h = max(len(ls) for ls in lines) * fs * 1.25 / 72 + 0.06
    return max(1.0, need_w / cw, need_h / ch) <= max_scale


# ---- arm labels (owner's rule: never a bare slug; legend table under every figure) ----
try:
    from . import arm_labels            # package import
except ImportError:                      # script run with tools/analysis_style on sys.path
    import arm_labels

# Owner's rule (2026-10-25): "when including descriptive labels, don't use tiny text - use word wrap and
# try to get variable names and descriptions readable, but also compact enough to not distort chart sizes."
#   - tick text >= MIN_TICK_PT (never shrink to fit);
#   - code on line 1, the short description wrapped below, ~22-28 characters per line, at most 3 lines;
#   - grow the figure to the wrapped label block, but if the labels would need more than MAX_LABEL_GROWTH x the
#     plot body on that dimension, fall back to a numbered key ("1", "2", ...) on the axis, with the full text in
#     the legend table (arm_labels.axis_legend(..., row_key=True / col_key=True));
#   - build figures with constrained_layout=True so nothing overlaps.
NLC = chr(10)
ARM_LABEL_WRAP = 26
ARM_LABEL_MAX_LINES = 3
MIN_TICK_PT = 9
MAX_LABEL_GROWTH = 1.5


def _trim_words(text, width, lines):
    """Wrap text to at most `lines` lines of `width`; trim at a word boundary with an ellipsis if needed."""
    import textwrap
    w = textwrap.wrap(str(text), width)
    if len(w) <= lines:
        return w
    w = w[:lines]
    last = w[-1]
    while len(last) + 1 > width and " " in last:
        last = last.rsplit(" ", 1)[0]
    w[-1] = last.rstrip(",;:") + "…"
    return w


def tick_label(slug, wrap=ARM_LABEL_WRAP, max_lines=ARM_LABEL_MAX_LINES, short=None):
    """One tick: the code on line 1, its glossary short label wrapped below (max_lines in total).
    `short` overrides the glossary text (use an abbreviated essence, e.g. "told to maximise joint profit")."""
    g = arm_labels.glossary()
    b = arm_labels._base(slug)
    desc = short if short is not None else (g[b]["short_label"] if b in g else "")
    head = f"{slug}:" if desc else str(slug)
    if len(head) > wrap:                       # very long codes keep their own line(s)
        head_lines = _trim_words(head, wrap, 1) if " " in head else [head]
    else:
        head_lines = [head]
    body = _trim_words(desc, wrap, max(max_lines - len(head_lines), 0)) if desc else []
    return "\n".join(head_lines + body)


def arm_tick_labels(slugs, wrap=ARM_LABEL_WRAP, max_lines=ARM_LABEL_MAX_LINES, short=None):
    """Axis tick text: "code:" on line 1 and the short description wrapped below (see tick_label).
    short: optional dict slug -> abbreviated description. Follow the figure with arm_labels.axis_legend(...)."""
    short = short or {}
    return [tick_label(s, wrap, max_lines, short.get(s)) for s in slugs]


def label_block_inches(labels, fontsize=MIN_TICK_PT, rotation=0):
    """(width, height) in inches of the widest / tallest wrapped tick label (rough text metrics)."""
    if not labels:
        return 0.0, 0.0
    cw, lh = fontsize * 0.6 / 72, fontsize * 1.22 / 72
    wid = max(max(len(l) for l in str(t).split("\n")) for t in labels) * cw
    hei = max(len(str(t).split("\n")) for t in labels) * lh
    return (hei, wid) if rotation == 90 else (wid, hei)


def set_arm_ticks(ax, slugs, axis="y", wrap=ARM_LABEL_WRAP, max_lines=ARM_LABEL_MAX_LINES,
                  fontsize=MIN_TICK_PT, max_growth=MAX_LABEL_GROWTH, short=None, grow=True, rotation=None, **kw):
    """Set wrapped "code: short label" ticks on axis 'x' or 'y' (ticks at 0..n-1); never below MIN_TICK_PT.

    Grows the figure so the label block fits, but only up to max_growth x the plot body's size along the
    label direction; beyond that the axis gets a numbered key ("1", "2", ...) instead.
    Returns (labels, key): key is None, or a list of the slugs in key order (1-based) to pass to
    arm_labels.axis_legend(..., row_key=True / col_key=True) so the legend gives "1 = code: description".
    """
    fontsize = max(fontsize, MIN_TICK_PT)
    labs = arm_tick_labels(slugs, wrap, max_lines, short)
    fig = ax.figure
    W, H = fig.get_size_inches()
    pos = ax.get_position()
    body_w, body_h = pos.width * W, pos.height * H
    n = max(len(labs), 1)
    if rotation is None:            # x: horizontal when the wrapped labels fit side by side, else vertical
        if axis == "y" or not labs:
            rotation = 0
        else:
            one_w = max(len(l) for t in labs for l in t.split(NLC)) * fontsize * 0.6 / 72 + 0.08
            rotation = 0 if one_w * n <= body_w else 90
    bw, bh = label_block_inches(labs, fontsize, rotation if axis == "x" else 0)
    lh = fontsize * 1.22 / 72
    nlines = max(len(t.split("\n")) for t in labs) if labs else 1
    key = None
    if axis == "y":
        need_pitch = nlines * lh * 1.05               # vertical room each wrapped label needs
        need_h = need_pitch * n
        too_wide = bw > max_growth * body_w
        too_tall = need_h > max_growth * body_h
        if too_wide or too_tall:
            key = list(slugs); labs = [str(i + 1) for i in range(len(slugs))]
        elif grow:
            add_w = max(0.0, bw - pos.x0 * W + 0.15)
            add_h = max(0.0, need_h - body_h)
            if add_w or add_h:
                fig.set_size_inches(W + add_w, H + add_h)
        ax.set_yticks(list(range(len(labs)))); ax.set_yticklabels(labs, fontsize=fontsize, rotation=0, **kw)
    else:
        need_pitch = (bw if rotation == 90 else max(len(l) for t in labs for l in t.split("\n")) * fontsize * 0.6 / 72)
        need_w = (nlines * lh * 1.05 if rotation == 90 else need_pitch) * n
        too_tall = (bh if rotation == 90 else bh) > max_growth * body_h
        too_wide = need_w > max_growth * body_w
        if too_wide or too_tall:
            key = list(slugs); labs = [str(i + 1) for i in range(len(slugs))]; rotation = 0
        elif grow:
            add_h = max(0.0, (bh if rotation == 90 else bh) - pos.y0 * H + 0.15)
            add_w = max(0.0, need_w - body_w)
            if add_w or add_h:
                fig.set_size_inches(W + add_w, H + add_h)
        ha = "center" if rotation in (0, 90) else "right"
        ax.set_xticks(list(range(len(labs)))); ax.set_xticklabels(labs, fontsize=fontsize, rotation=rotation, ha=ha, **kw)
    return labs, key


PLAIN_SLUG_PT = 7
PLAIN_SLUG_COLOR = "#888888"


def plain_tick_pairs(codes, wrap=40):
    """(plain wording, code) pairs for codes that are glossary slugs or contrast texts."""
    out = []
    for c in codes:
        t = arm_labels.plain_contrast(c)
        if t is None:
            t = arm_labels.plain(c)
        out.append(("\n".join(__import__("textwrap").wrap(t, wrap, break_on_hyphens=False)), str(c)))
    return out


def set_plain_ticks(ax, positions, pairs, fontsize=MIN_TICK_PT, slug_fontsize=PLAIN_SLUG_PT, pad_pt=6, slug_wrap=60):
    """Y-axis labels in two styles: the plain wording (black, fontsize) above the slug or contrast code
    (small, grey) at each position. pairs = [(plain_text, code), ...] (see plain_tick_pairs); code may be ''.
    Replaces the tick labels (they are cleared); the row needs room for both lines."""
    import textwrap
    from matplotlib.transforms import blended_transform_factory
    ax.set_yticks(list(positions))
    ax.set_yticklabels([""] * len(positions))
    ax.tick_params(axis="y", length=0)
    tr = blended_transform_factory(ax.transAxes, ax.transData)
    for y, (main, code) in zip(positions, pairs):
        ax.annotate(main, xy=(0, y), xycoords=tr, xytext=(-pad_pt, 0.5 if code else 0), textcoords="offset points",
                    ha="right", va="bottom" if code else "center", fontsize=fontsize, color="#111111", linespacing=1.05,
                    annotation_clip=False)
        if code:
            ax.annotate("\n".join(textwrap.wrap(code, slug_wrap)), xy=(0, y), xycoords=tr, xytext=(-pad_pt, -0.5),
                        textcoords="offset points", ha="right", va="top", fontsize=slug_fontsize, color=PLAIN_SLUG_COLOR,
                        annotation_clip=False)
