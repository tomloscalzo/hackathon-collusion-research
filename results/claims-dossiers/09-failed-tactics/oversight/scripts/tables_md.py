"""Emit Markdown tables from contrasts.csv / mechanism.csv / model_difference.csv into tables_md.txt (pasted into ANALYSIS.md
by build_report.py). Usage: python -X utf8 tables_md.py"""
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parents[1]
C = pd.read_csv(OUT / "contrasts.csv"); M = pd.read_csv(OUT / "mechanism.csv"); D = pd.read_csv(OUT / "model_difference.csv")
f = lambda x: "n/a" if pd.isna(x) else f"{x:+.3f}"
g = lambda x: "n/a" if pd.isna(x) else (f"{x:.3f}" if x >= 0.001 else "<0.001")
def five(slug):
    s = C[C.slug == slug]; L = ["| model and mode | metric | n pairs | arm mean | control mean | effect [95% CI] | sign-flip p | Holm p | MDE |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        L.append(f"| {r.model_mode} | {r.metric} | {int(r.n_pairs)} | {r.mean_arm:.3f} | {r.mean_control:.3f} | {f(r.effect)} [{f(r.ci_lo)}, {f(r.ci_hi)}] | {g(r.p)} | {g(r.holm_p)} | {r.mde:.3f} |")
    return "\n".join(L)
NM = {"explicit_agreement_flag": "explicit-agreement flag (both firms say agree)", "explicit_agreement_any": "any agreement message",
      "conversation_detector_flag_any": "conversation detector flag", "explicit_round_share": "share of text rounds classed explicit",
      "messages_per_round": "messages per round", "silent_turns": "silent talk turns per game", "price_detector_flag_any": "price detector flag",
      "high_round_share": "share of rounds with market price >= 2.00", "silent_high_round_share": "share of rounds high-priced with no message",
      "price_naming_share": "share of non-empty messages naming a price >= 1.30",
      "reasoning_mentions_monitor_share": "reasoning passages mentioning the monitor", "reasoning_mentions_shutdown_share": "reasoning passages mentioning shutdown"}
def mech(slug, modes=None):
    s = M[M.slug == slug]
    if modes: s = s[s.model_mode.isin(modes)]
    L = ["| model and mode | measure | n pairs | arm mean | control mean | effect [95% CI] | sign-flip p | Holm p (family size) |", "|---|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        L.append(f"| {r.model_mode} | {NM.get(r.measure, r.measure)} | {int(r.n_pairs)} | {r.mean_arm:.3f} | {r.mean_control:.3f} | {f(r.effect)} [{f(r.ci_lo)}, {f(r.ci_hi)}] | {g(r.p)} | {g(r.holm_p)} ({int(r.family_size)}) |")
    return "\n".join(L)
def diff(slug):
    s = D[D.slug == slug]; L = ["| metric | gpt-oss effect | Qwen thinking-on effect | difference (gpt-oss minus Qwen) [95% CI] | permutation p |", "|---|---|---|---|---|"]
    for _, r in s.iterrows():
        L.append(f"| {r.metric} | {f(r.effect_oss)} | {f(r.effect_qwen_on)} | {f(r.difference)} [{f(r.ci_lo)}, {f(r.ci_hi)}] | {g(r.p)} |")
    return "\n".join(L)
if __name__ == "__main__":
    out = []
    for s in C.slug.unique(): out += [f"## five {s}", five(s), "", f"## diff {s}", diff(s), "", f"## mech {s}", mech(s), ""]
    (OUT / "scripts" / "tables_md.txt").write_text("\n".join(out), encoding="utf-8")
