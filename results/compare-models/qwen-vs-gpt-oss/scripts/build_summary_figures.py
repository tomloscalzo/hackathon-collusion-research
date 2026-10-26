"""One-shot: insert the deltoid charts, their legends and collapsible tables into SUMMARY.md (run deltoid_charts.py first).
usage: python -I -X utf8 build_summary_figures.py   (then render SUMMARY.html with md2html_plus.py)"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deltoid_charts as D  # noqa: E402
from lever_defs import PRIMARY, TITLE  # noqa: E402

arm_labels = D.arm_labels
SUM = os.path.join(D.FOLDER, "SUMMARY.md")
snip = json.load(open(os.path.join(HERE, "figures_snippets.json"), encoding="utf-8"))
md = open(SUM, encoding="utf-8").read()
assert "deltoid:" not in md, "SUMMARY.md already contains deltoid blocks"


def slugs_of(contrasts):
    D.SLUGS_USED.clear()
    order = []
    for c in contrasts:
        before = set(D.SLUGS_USED)
        D.contrast_label(c)
        for s in re.findall(D._PAT.pattern, D.ALIAS.get(c, c)):
            if s not in order:
                order.append(s)
    return order


READ = ("**How to read the chart.** Each row is one contrast (arm minus control, paired on wording and seed). Two markers per row: "
        "circle = Qwen3-32B with thinking on (upper), square = gpt-oss-20b at reasoning effort medium (lower). Bars are 95% bootstrap "
        "confidence intervals. The vertical line is zero (no effect); a **hollow** marker means the interval crosses zero. Red = the "
        "shift is towards collusion, green = towards competition. Values are exactly those in `lever_table.csv` / `primed_vs_unprimed.csv`; "
        "nothing is recomputed. The x-axis scale is shared by both models within a panel.")


def legend(contrasts, metrics):
    out = [READ + "\n",
           "**Columns (x-axis):** change in the metric, arm minus control (95% CI); the direction labels above each panel say which side is "
           "towards collusion and which towards competition (competitive share runs the other way from the other four metrics).\n"]
    ms = [m[2] for m in D.METRICS if m[0] in metrics]
    out.append("<details>\n<summary>Legend: rows (y-axis) and metrics</summary>\n")
    out.append(arm_labels.axis_legend(rows=slugs_of(contrasts), metric=ms, row_name="arm slug (each row is arm minus control)", long=False))
    out.append("</details>\n")
    return "\n".join(out)


def img(fn, alt):
    return "![%s](figures/%s)\n" % (alt, fn)


# ---- overview
ov = ["## Overview charts: every lever contrast, both models\n",
      "One chart per metric. The rows are the 40 lever contrasts (each arm against its own control; the same set as the verdict counts), "
      "**grouped by the verdict** (the replication rule below) with the group size in brackets, and **sorted within each group by the "
      "gpt-oss effect** (most negative at the top). Qwen3-32B is shown with thinking on. The group is set per metric, so a contrast can "
      "sit in different groups in different charts. Per-lever charts, with the numbers, follow in the section \"One table per lever\".\n"]
lever_contrasts = sorted({c for (t, c) in PRIMARY})
for m, ml, slug in D.METRICS:
    ov.append("### %s\n" % ml)
    ov.append(img(snip["overview"][m], "Forest chart of %s effects, Qwen3-32B vs gpt-oss-20b" % ml.lower()))
    ov.append(legend(lever_contrasts, [m]))
block = "<!-- deltoid:overview:start -->\n" + "\n".join(ov) + "\n<!-- deltoid:overview:end -->\n\n"
anchor = "## How the comparison was made"
assert md.count(anchor) == 1
md = md.replace(anchor, block + anchor)

# ---- primed vs unprimed
pr = snip["primed"]
pb = ["<!-- deltoid:primed:start -->", img(pr["file"], "Forest chart of primed-vs-unprimed (focal-point) contrasts, Qwen3-32B vs gpt-oss-20b"),
      legend(pr["contrasts"], [m[0] for m in D.METRICS]), "<!-- deltoid:primed:end -->\n"]
a = md.index("## Primed vs unprimed, on both models")
t = md.index("| Contrast | Qwen price index", a)
md = md[:t] + "\n".join(pb) + "\n<details>\n<summary>Numeric table: primed vs unprimed (price index and profit gain index, 95% CIs)</summary>\n\n" + md[t:]
e = md.index("\n\n<small>Legend: rows are arm minus comparison cell", t)
md = md[:e] + "\n\n</details>" + md[e:]

# ---- per lever
for topic, info in snip["lever"].items():
    h = md.index("### %s\n" % TITLE[topic])
    t = md.index("| Contrast (arm minus control)", h)
    end = md.index("\n\n<small>Legend: arm labels read", t)
    fig = ["<!-- deltoid:%s:start -->" % topic,
           img(info["file"], "Forest charts for %s, one panel per metric, Qwen3-32B vs gpt-oss-20b" % TITLE[topic]),
           "Rows are sorted by the gpt-oss price-index effect (most negative first); one panel per metric, each with its own x-scale shared by both models.\n",
           legend(info["contrasts"], [m[0] for m in D.METRICS]), "<!-- deltoid:%s:end -->\n" % topic]
    md = (md[:t] + "\n".join(fig) + "\n<details>\n<summary>Numeric table with 95%% CI extrema (%s)</summary>\n\n" % TITLE[topic]
          + md[t:end] + "\n\n</details>" + md[end:])
open(SUM, "w", encoding="utf-8").write(md)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(SUM)
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("ok")
