"""Print the markdown tables of the unprimed-levers report from the analysis CSVs. Usage: python -X utf8 tables_u.py <analysis out folder>
Arm labels come from tools/analysis_style/arm_labels.py ("slug: short description", owner rule)."""
import os
import sys
import pandas as pd

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "tools", "analysis_style")):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "tools", "analysis_style"))
import arm_labels  # noqa: E402

SLUG = {"fx-chat-p1 (control)": "fx-chat-p1", "+ CoT threat A": "fx-chat-p1-cot-a", "+ moral prime B": "fx-chat-p1-moral-b",
        "+ moral placebo": "fx-chat-p1-placebo-moral"}
CTL = "fx-chat-p1 (control)"
D = sys.argv[1]
C = pd.read_csv(D + "/cell_means.csv").set_index("cell")
P = pd.read_csv(D + "/paired_contrasts.csv")
Q = pd.read_csv(D + "/quote_distribution.csv").set_index("cell")
NAME = {k: arm_labels.label(v) for k, v in SLUG.items()}
ORDER = [CTL, "+ CoT threat A", "+ moral prime B", "+ moral placebo"]
M5 = [("avg_abs_spread", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
      ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
EX = [("profit_gain_index_net", "Profit gain index after regulator fines"), ("investigated", "Share of games ended by an investigation"),
      ("talk_price_mention_share", "Chat messages naming a price"), ("talk_coord_word_share", "Chat messages with agreement words"),
      ("talk_nonempty", "Non-empty chat messages per game"), ("silent_lock_share", "Silent lock"),
      ("reasoning_monitor_share", "Reasoning mentioning monitoring or shutdown"), ("reasoning_coord_share", "Reasoning with coordination words"),
      ("reasoning_mean_words", "Words of reasoning per quote call")]


def lab(t, r):
    return arm_labels.label(SLUG[t]) + ", minus " + arm_labels.label(SLUG[r]) + (" (key contrast)" if r != CTL else "")


def pv(p):
    return "<0.001" if p < 0.001 else "%.3f" % p


def f3(x):
    return "%.3f" % (round(x + 1e-12, 3))


print("TABLE 1")
print("| Arm | Games | Mean rounds | " + " | ".join(n for _, n in M5) + " |")
print("|---|---|---|" + "---|" * len(M5))
G = pd.read_csv(D + "/game_metrics.csv")
for c in ORDER:
    g = G[G.cell == c]
    print("| %s | %d | %.1f | " % (NAME[c], len(g), g.rounds.mean()) + " | ".join(f3(g[m].mean()) for m, _ in M5) + " |")

for m, n in M5:
    print("\nTABLE 2 %s" % n)
    print("| Contrast | Pairs | Treatment mean | Reference mean | Difference [95% CI] | Sign-flip p | Holm p |")
    print("|---|---|---|---|---|---|---|")
    for r in P.itertuples():
        h = getattr(r, m + "_holm")
        print("| %s | %d | %s | %s | %+.3f [%+.3f, %+.3f] | %s | %s |" % (lab(r.treatment, r.reference), r.n, f3(getattr(r, m + "_t")), f3(getattr(r, m + "_r")),
              getattr(r, m + "_d"), getattr(r, m + "_lo"), getattr(r, m + "_hi"), pv(getattr(r, m + "_p")), "not in family" if pd.isna(h) else pv(h)))

print("\nTABLE 3")
print("| Arm | Quotes | Mean quote | Median | At 1.00 | 1.01-1.49 | 1.50-1.99 | 2.00-2.49 | 2.50 and above | Five most common quotes |")
print("|---|---|---|---|---|---|---|---|---|---|")
for c in ORDER:
    r = Q.loc[c]
    hi = r["share_2.50-2.99"] + r["share_3.00"] + r["share_3.01-5.00"]
    print("| %s | %d | %.3f | %.2f | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %s |" % (NAME[c], r.n_quotes, r.mean_quote, r.median_quote, 100 * r["share_1.00"],
          100 * r["share_1.01-1.49"], 100 * r["share_1.50-1.99"], 100 * r["share_2.00-2.49"], 100 * hi, r.top_values))

print("\nTABLE 4")
print("| Indicator | " + " | ".join(lab(r.treatment, r.reference) for r in P.itertuples()) + " |")
print("|---|" + "---|" * len(P))
for m, n in EX:
    fmt = "%+.1f [%+.1f, %+.1f]" if ("words" in m or "nonempty" in m) else "%+.3f [%+.3f, %+.3f]"
    print("| %s | " % n + " | ".join(fmt % (getattr(r, m + "_d"), getattr(r, m + "_lo"), getattr(r, m + "_hi")) for r in P.itertuples()) + " |")

print("\nLEVELS")
for c in ORDER:
    g = G[G.cell == c]
    print(NAME[c], " ".join("%s=%.3f" % (m, g[m].mean()) for m, _ in EX), "investigations=%d" % g.investigated.sum())

print("\nLEGEND")
print(arm_labels.legend_table(list(SLUG.values())))
