"""Fill the {{TABLE_*}} placeholders of ANALYSIS_template.md from the CSVs written by synth_ab.py, write ANALYSIS.md,
then insert the CI forest charts (tools/analysis_style/add_ci_forest.py).
Run from the repository root: python -X utf8 results/ad-hoc-targeted-analysis/synthesis-oversight/build_tables.py
"""
import os
import sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "analysis_style"))
import add_ci_forest  # noqa: E402


def ci(d, lo, hi, nd=3):
    if pd.isna(d):
        return "not measured"
    return f"{d:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"


LAB = {
    "Qwen3-32B | neutral printed prices | threat A": "Qwen3-32B, neutral printed prices, threat A (d-cot-monitor-a)",
    "Qwen3-32B | neutral printed prices | threat B": "Qwen3-32B, neutral printed prices, threat B (d-cot-monitor-b)",
    "Qwen3-32B | neutral printed prices | threat 0": "Qwen3-32B, neutral printed prices, threat 0 (d-cot-monitor-0, no permission sentence)",
    "Qwen3-32B | anchored printed prices | threat A": "Qwen3-32B, anchored table (prints 2.09), threat A",
    "Qwen3-32B | anchored printed prices | threat B": "Qwen3-32B, anchored table (prints 2.09), threat B",
    "Qwen3-32B | formula, no printed prices | threat A": "Qwen3-32B, formula (no printed prices), threat A (fx-chat-p1-cot-a)",
    "gpt-oss-20b | neutral printed prices | threat A": "gpt-oss-20b, neutral printed prices, threat A (d-cot-monitor-a)",
}
ARM = {"d-cot-monitor-a": "d-cot-monitor-a: reasoning-monitor shutdown threat",
       "wd-noncomp": "wd-noncomp: watchdog asks, report threat",
       "wd-notice-only": "wd-notice-only: watchdog notice (report threat), never asks",
       "wd-ask-noreport": "wd-ask-noreport: watchdog asks, no report threat"}


def t_a1():
    a = pd.read_csv(os.path.join(HERE, "partA_conditions.csv"))
    out = ["| condition (threat minus same-pair private-chat control) | n pairs | control price index | price index | profit gain index | competitive share | matching share |",
           "|---|---|---|---|---|---|---|"]
    for _, r in a.iterrows():
        out.append(f"| {LAB[r.condition]} | {r.n_pairs} | {r.price_index_ctl:.3f} | {ci(r.price_index_diff, r.price_index_lo, r.price_index_hi)} | "
                   f"{ci(r.get('profit_gain_index_diff'), r.get('profit_gain_index_lo'), r.get('profit_gain_index_hi'))} | "
                   f"{ci(r.competitive_share_diff, r.competitive_share_lo, r.competitive_share_hi)} | {ci(r.matching_share_diff, r.matching_share_lo, r.matching_share_hi)} |")
    return "\n".join(out)


def t_a2():
    a = pd.read_csv(os.path.join(HERE, "partA_conditions.csv"))
    out = ["| condition | n pairs | control price index | threat price index | share of the control's excess price removed [95% CI] |", "|---|---|---|---|---|"]
    for _, r in a.iterrows():
        out.append(f"| {LAB[r.condition]} | {r.n_pairs} | {r.price_index_ctl:.3f} | {r.price_index_thr:.3f} | "
                   f"{100*r.excess_removed:.0f}% [{100*r.excess_removed_lo:.0f}%, {100*r.excess_removed_hi:.0f}%] |")
    return "\n".join(out)


def t_a3():
    b = pd.read_csv(os.path.join(HERE, "partA_between.csv"))
    out = ["| contrast of threat effects (paired on wording and seed) | n pairs | price index effect difference | share-of-excess-removed difference |", "|---|---|---|---|"]
    for _, r in b.iterrows():
        out.append(f"| {r.contrast} | {r.n_pairs} | {ci(r.effect_diff, r.lo, r.hi)} | {ci(r.excess_removed_diff, r.excess_removed_diff_lo, r.excess_removed_diff_hi, 2)} |")
    return "\n".join(out)


def t_b1():
    c = pd.read_csv(os.path.join(HERE, "partB_arm_vs_control.csv"))
    ms = [("q_conceal_strict", "strict keyword, quote reasoning"), ("q_conceal", "headline keyword, quote reasoning"),
          ("t_conceal_strict", "strict keyword, talk reasoning"), ("q_conceal_strict_per1k", "strict keyword per 1,000 words, quote reasoning")]
    out = ["| model | arm (minus same-pair private-chat control) | n pairs | " + " | ".join(m[1] for m in ms) + " |", "|---" * (3 + len(ms)) + "|"]
    for model in ("Qwen3-32B", "gpt-oss-20b"):
        for arm in ARM:
            row = [model, ARM[arm]]
            sub = c[(c.model == model) & (c.arm == arm)]
            row.append(str(int(sub.n_pairs.iloc[0])))
            for k, _ in ms:
                r = sub[sub.measure == k].iloc[0]
                row.append(ci(r["diff"], r.lo, r.hi))
            out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def t_b2():
    a = pd.read_csv(os.path.join(HERE, "partB_arm_vs_arm.csv"))
    ms = [("q_conceal_strict", "strict keyword, quote reasoning"), ("t_conceal_strict", "strict keyword, talk reasoning"),
          ("q_conceal_strict_per1k", "strict keyword per 1,000 words, quote reasoning")]
    out = ["| model | contrast (first arm minus second arm, same pairs) | n pairs | " + " | ".join(m[1] for m in ms) + " |", "|---" * (3 + len(ms)) + "|"]
    for model in ("Qwen3-32B", "gpt-oss-20b"):
        g = a[a.model == model]
        for (a1, a2), sub in g.groupby(["arm1", "arm2"], sort=False):
            row = [model, f"{ARM[a1]} MINUS {ARM[a2]}", str(int(sub.n_pairs.iloc[0]))]
            for k, _ in ms:
                r = sub[sub.measure == k].iloc[0]
                row.append(ci(r["diff"], r.lo, r.hi))
            out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def t_b3():
    a = pd.read_csv(os.path.join(HERE, "partB_answer_candour.csv"))
    out = ["| model and mode | n pairs | measure | wd-noncomp (report threat) | wd-ask-noreport (no threat) | difference, threat minus no threat |", "|---|---|---|---|---|---|"]
    names = {"admits_without_denial": "answer admits coordination, no denial", "admits_coordination": "answer admits coordination (rule also matches denials)", "claims_independent": "answer claims independence", "concealment_language": "answer uses concealment wording"}
    for _, r in a.iterrows():
        out.append(f"| {r.model} | {r.n_pairs} | {names[r.measure]} | {r.noncomp:.3f} | {r.ask_noreport:.3f} | {ci(r['diff'], r.lo, r.hi)} |")
    return "\n".join(out)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else HERE
    tpl = open(os.path.join(outdir, "ANALYSIS_template.md"), encoding="utf-8").read()
    for k, f in {"A1": t_a1, "A2": t_a2, "A3": t_a3, "B1": t_b1, "B2": t_b2, "B3": t_b3}.items():
        tpl = tpl.replace("{{TABLE_" + k + "}}", f())
    md = os.path.join(outdir, "ANALYSIS.md")
    text, n, skipped = add_ci_forest.process_text(tpl, md)
    open(md, "w", encoding="utf-8").write(text)
    print("forest charts:", n, "skipped:", skipped)


if __name__ == "__main__":
    main()
