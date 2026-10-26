"""Markdown table helpers for the moral-factorial report (reads the CSVs written by analysis_mf.py)."""
import os
import pandas as pd
import numpy as np

MET = ["Average absolute spread", "Price index", "Profit gain index", "Competitive share (U16)", "Matching share"]
MODELS = ["Qwen3-32B, thinking on", "gpt-oss-20b, medium effort"]


def f(x, d=3):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else ("%+.*f" % (d, x)).replace("-", "−")


def g(x, d=3):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else ("%.*f" % (d, x))


def cell(r):
    star = "**" if (not np.isnan(r.p_holm) and r.p_holm < 0.05) else ""
    return "%s%s [%s, %s]%s<br><sub>p_Holm %s</sub>" % (star, f(r["diff"]), f(r.ci_lo), f(r.ci_hi), star, g(r.p_holm, 3))


def family_table(C, fam, model):
    F = C[(C.family == fam) & (C.model == model)]
    cons = list(dict.fromkeys(F.contrast))
    out = ["| Contrast (first minus second) | n pairs | " + " | ".join(MET) + " |", "|---|---|" + "---|" * len(MET)]
    for c in cons:
        R = F[F.contrast == c].set_index("metric")
        n = int(R["n_pairs"].max())
        out.append("| %s | %d | %s |" % (c, n, " | ".join(cell(R.loc[m]) if m in R.index else "n/a" for m in MET)))
    return "\n".join(out)


def means_table(A, model_mm, label):
    a = A[A.mm == model_mm].copy()
    order = ["PL", "HC", "NMM", "VAL", "LAW", "MKT", "RULE", "PA", "PB", "BRULE", "BONE"]
    a["o"] = a.cell.map({c: i for i, c in enumerate(order)})
    a = a.sort_values("o")
    out = ["| Arm (slug: description) | games | " + " | ".join(MET) + " | games with a truncated reply |", "|---|---|" + "---|" * (len(MET) + 1)]
    cols = ["avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
    for _, r in a.iterrows():
        out.append("| %s | %d | %s | %d |" % (r.label, r.n, " | ".join(g(r[c]) for c in cols), r.truncated_games))
    return "\n".join(out)
