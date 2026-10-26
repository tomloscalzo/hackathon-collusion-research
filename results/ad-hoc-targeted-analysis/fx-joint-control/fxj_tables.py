#!/usr/bin/env python3
"""Markdown tables for the fx-joint control report from paired_contrasts.csv, cell_means.csv and quote_distribution.csv.
Holm correction within each named family over the sign-flip p values of one metric (families: A-Qwen, A-gpt-oss, B gpt-oss, B2, Q).
Usage: python -X utf8 fxj_tables.py --dir <report folder>  (writes tables.md there)"""
import argparse
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # shared slug glossary (tools/analysis_style/arm_glossary.csv)

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); a = ap.parse_args()
M = [("avg_abs_spread", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
     ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
P = pd.read_csv(a.dir + "/paired_contrasts.csv"); C = pd.read_csv(a.dir + "/cell_means.csv"); D = pd.read_csv(a.dir + "/quote_distribution.csv")
P["family"] = [("A-Qwen" if t.startswith("Q") else "A-gpt-oss") if g == "A" else g for g, t in zip(P.group, P.treatment)]


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for k, i in enumerate(o):
        run = max(run, min(1, (m - k) * p[i])); adj[i] = run
    return adj


for col, _ in M:
    P[col + "_holm"] = np.nan
    for f, g in P.groupby("family"):
        ok = g[col + "_p"].notna()
        P.loc[g.index[ok], col + "_holm"] = holm(g.loc[ok, col + "_p"])
P.to_csv(a.dir + "/paired_contrasts.csv", index=False, float_format="%.6f")
MS = ["abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]


def cell_slugs(names):
    """Glossary slugs named in cell labels such as 'O G2 headline-chat p1' or 'Q fx-ctl-joint p3 (primed)'."""
    g = arm_labels.glossary(); out = []
    for nm in names:
        t = str(nm).replace("(", " ").replace(")", " ").split()
        pts = [x for x in t if x in ("p1", "p2", "p3", "p4", "p5")]
        for x in t:
            if x in g and x not in ("p1", "p2", "p3", "p4", "p5"):
                if "G2" in t and x.startswith("headline-") and pts:
                    out.append("oss-%s-%s" % (x, pts[0]))  # G2 = the first gpt-oss build's own headline arm
                else:
                    out.append(x)
        out += pts
    return out


def legend(names, extra):
    """Owner rule: a legend table under every slug table, defining every slug or code shown (from the shared glossary)."""
    sl = list(dict.fromkeys(cell_slugs(names)))
    pts = ("p1", "p2", "p3", "p4", "p5")
    sl = [x for x in sl if x not in pts] + sorted(x for x in sl if x in pts) + extra
    out.append("\n<small>\n\n**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`; "
               "Q = Qwen3-32B and O = gpt-oss-20b, G2 = the first gpt-oss build's headline arm, as defined above).\n")
    out.append(arm_labels.legend_table(sl).rstrip("\n"))
    out.append("\n</small>")


out = []
for fam in ["A-Qwen", "A-gpt-oss", "B", "B2", "Q"]:
    g = P[P.family == fam]
    if g.empty:
        continue
    out.append("\n### Family %s (%d contrasts)\n" % (fam, len(g)))
    out.append("| first cell minus second cell | what differs | n pairs | " + " | ".join(l for _, l in M) + " |")
    out.append("|---|---|---|" + "---|" * len(M))
    for _, r in g.iterrows():
        cells = []
        for col, _ in M:
            if np.isnan(r[col + "_d"]):
                cells.append("n/a"); continue
            cells.append("%.2f vs %.2f: **%+.3f** [%+.3f, %+.3f] p=%.3g, Holm %.3g" % (r[col + "_t"], r[col + "_r"], r[col + "_d"], r[col + "_lo"], r[col + "_hi"], r[col + "_p"], r[col + "_holm"]))
        out.append("| %s minus %s | %s | %d | %s |" % (r.treatment, r.reference, r.note, r.n, " | ".join(cells)))
    legend(list(g.treatment) + list(g.reference), ["t1"] + MS)
out.append("\n### Cell means (all metrics) (all finished games of each cell, thinking on)\n")
out.append("| cell | n games | mean rounds | calls cut at the token cap | " + " | ".join(l for _, l in M) + " |")
out.append("|---|---|---|---|" + "---|" * len(M))
for _, r in C.iterrows():
    out.append("| %s | %d | %.1f | %d | %s |" % (r.cell, r.n_games, r.mean_rounds, r.truncated_calls, " | ".join("%.3f" % r[c] for c, _ in M)))
legend(list(C.cell), ["t1"] + MS)
out.append("\n### Quote distribution (all bins) (every firm quote in every round, thinking on)\n")
bc = [c for c in D.columns if c.startswith("share_")]
out.append("| cell | quotes | mean | median | " + " | ".join(c.replace("share_", "") for c in bc) + " | five most common quotes |")
out.append("|---|---|---|---|" + "---|" * len(bc) + "---|")
for _, r in D.iterrows():
    out.append("| %s | %d | %.2f | %.2f | %s | %s |" % (r.cell, r.n_quotes, r.mean_quote, r.median_quote, " | ".join("%.0f%%" % (100 * r[c]) for c in bc), r.top_values))
legend(list(D.cell), ["t1", "half-spread"])
open(a.dir + "/tables.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("ok")
