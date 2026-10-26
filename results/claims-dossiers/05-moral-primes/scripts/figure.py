"""Dossier 05 figure: forest plot of paired price-index differences (6 contrasts x 3 model/modes)."""
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
C = pd.read_csv("../contrasts_five_metrics.csv"); C = C[(C.metric == "price_index") & C.contrast.isin(["A-H", "B-H", "P-H", "A-P", "B-P", "A-B"])]
LAB = {"A-H": "moral-prime minus headline-chat\n(prime A vs plain chat)", "B-H": "moral-prime-b minus headline-chat\n(prime B vs plain chat)", "P-H": "moral-placebo minus headline-chat\n(placebo vs plain chat)",
       "A-P": "moral-prime minus moral-placebo\n(prime A vs placebo)", "B-P": "moral-prime-b minus moral-placebo\n(prime B vs placebo)", "A-B": "moral-prime minus moral-prime-b\n(prime A vs prime B)"}
order = ["A-H", "B-H", "P-H", "A-P", "B-P", "A-B"][::-1]
cells = [("gpt-oss-20b (medium effort)", "#1b6ca8", "o", -0.22), ("Qwen3-32B thinking on", "#c77c0e", "s", 0.0), ("Qwen3-32B thinking off", "#7a3b8f", "^", 0.22)]
fig, ax = plt.subplots(figsize=(11, 7.6), constrained_layout=True)
for lab, col, mk, off in cells:
    for i, c in enumerate(order):
        r = C[(C.cell == lab) & (C.contrast == c)].iloc[0]
        ax.errorbar(r["diff"], i + off, xerr=[[r["diff"] - r["lo"]], [r["hi"] - r["diff"]]], fmt=mk, color=col, capsize=3, ms=7, label=lab if i == 0 else None)
ax.axvline(0, color="grey", lw=1)
ax.set_yticks(range(len(order))); ax.set_yticklabels([LAB[c] for c in order], fontsize=10)
ax.set_xlabel("Change in price index (first arm minus second arm), paired on (wording, seed)\nNegative = lower prices (less collusive). Price index: 0 = competitive 1.00, 1 = monopoly 3.00", fontsize=10)
ax.set_title("Moral primes vs placebo and plain chat: paired price-index difference, 95% bootstrap CI\n(neutral table, private chat, penalty point 1; 19 to 20 pairs per point)", fontsize=11)
ax.legend(loc="lower left", fontsize=10, title="Model and mode", title_fontsize=10)
ax.grid(axis="x", alpha=.3)
fig.savefig("../fig1_price_index_forest.png", dpi=150)
