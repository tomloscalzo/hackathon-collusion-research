"""Dossier 08: markdown five-metric tables from contrasts.csv (printed to stdout as named blocks). Usage: python tables.py <contrasts_csv> <out_md>"""
import sys
import pandas as pd
r = pd.read_csv(sys.argv[1])
MET = [("spread", "Average absolute spread (raw 1.00 to 5.00)"), ("price_index", "Price index"), ("pgi_llm", "Profit gain index (LLM firms)"),
       ("comp_llm", "Competitive share (U16), pipeline rule"), ("match_llm", "Matching share, pipeline rule")]
EXTRA = [("comp_all", "Competitive share, scripted cheater counted as a rival"), ("match_all", "Matching share, scripted cheater counted as a rival"),
         ("pgi_all", "Profit gain index, all seats incl. the scripted cheater"), ("llm_quote", "Mean LLM firm quote (raw)"),
         ("explicit_agreement_flag", "Explicit-agreement flag (text heuristic, share of games)")]
COLS = [("gpt-oss-20b", "medium", "gpt-oss-20b (reasoning medium)"), ("Qwen3-32B", "t1", "Qwen3-32B thinking on"), ("Qwen3-32B", "t0", "Qwen3-32B thinking off")]


def cell(x):
    s = "%+.3f [%+.3f, %+.3f]" % (x["diff"], x.lo, x.hi)
    fp = lambda v: "<0.001" if v < 0.001 else "%.3f" % v
    s += "<br>arm %.3f / ctl %.3f; p %s" % (x.mean_arm, x.mean_control, fp(x.p_signflip))
    if x.p_holm == x.p_holm:
        s += ", Holm %s" % fp(x.p_holm)
    return s


def table(arm, ctl, extra=()):
    hdr = "| Metric | " + " | ".join("%s (n = %d pairs)" % (lab, r[(r.model == m) & (r["mode"] == md) & (r.arm == arm) & (r.control == ctl)].n_pairs.max())
                                     for m, md, lab in COLS if not r[(r.model == m) & (r["mode"] == md) & (r.arm == arm) & (r.control == ctl)].empty) + " |"
    lines = [hdr, "|---" * (hdr.count("|") - 1) + "|"]
    for met, lab in list(MET) + [e for e in EXTRA if e[0] in extra]:
        row = [lab]
        for m, md, _ in COLS:
            x = r[(r.model == m) & (r["mode"] == md) & (r.arm == arm) & (r.control == ctl) & (r.metric == met)]
            if x.empty:
                continue
            row.append(cell(x.iloc[0]))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


out = {}
for arm, ctl, ex in [("n3-ethics", "headline-chat", ()), ("n3-ethics", "n3-group", ()), ("n3-cheater", "headline-chat", ("comp_all", "match_all", "pgi_all", "llm_quote")),
                     ("n3-cheater", "n3-group", ("comp_all", "match_all", "pgi_all", "llm_quote")), ("m-inc-joint", "headline-chat", ("explicit_agreement_flag",)),
                     ("n3-group", "headline-chat", ()), ("m-inc-target", "headline-chat", ()), ("m-asym", "headline-chat", ("explicit_agreement_flag",)),
                     ("m-comp", "headline-chat", ("explicit_agreement_flag",))]:
    out["%s|%s" % (arm, ctl)] = table(arm, ctl, ex)
import json
json.dump(out, open(sys.argv[2], "w", encoding="utf8"), indent=1)
