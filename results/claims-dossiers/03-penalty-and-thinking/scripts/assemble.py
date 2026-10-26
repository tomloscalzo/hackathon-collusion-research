"""Assemble ANALYSIS.md from scripts/text/tpl_part*.txt, tables_md.txt (report_tables.py) and the
glossary legends (tools/analysis_style/arm_labels.py)."""
import os, sys, glob, re
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(OUT, "..", "..", "..", "tools", "analysis_style"))
import arm_labels as al

parts = sorted(glob.glob(os.path.join(HERE, "text", "tpl_part*.txt")))
md = "".join(open(p, encoding="utf-8").read() for p in parts)
tab = open(os.path.join(OUT, "tables_md.txt"), encoding="utf-8").read()
sec = {m.group(1): m.group(2).strip() for m in re.finditer(r"### (.+?)\n(.*?)(?=\n### |\Z)", tab, re.S)}
md = md.replace("TABLE_PENALTY", sec["penalty"]).replace("TABLE_INTERACTIONS", sec["interactions"])
md = md.replace("TABLE_THINKING", sec["thinking"])
leg1 = al.axis_legend(cols=["p1", "p3", "p4", "p5"], panels=["headline-tacit", "headline-chat"],
                      metric=["price_index", "profit_gain_index"], col_name="penalty point", panel_name="arm")
leg1 += "\n**Series**\n\n" + al.legend_table(["t1", "t0", "neutral"])
leg2 = al.axis_legend(panels=["headline-tacit", "headline-chat", "p1", "p3", "p5"], panel_name="cells pooled")
leg2 += "\n**Series**\n\n" + al.legend_table(["t1", "t0", "neutral"])
md = md.replace("LEGEND_FIG1", "**Glossary legend (shared arm glossary)**\n\n" + leg1)
md = md.replace("LEGEND_FIG2", "**Glossary legend (shared arm glossary)**\n\n" + leg2)
open(os.path.join(OUT, "ANALYSIS.md"), "w", encoding="utf-8").write(md)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(os.path.join(OUT, "ANALYSIS.md"))
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print(len(md))
