import sys; sys.path.insert(0, ".")
import pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
p = pd.read_csv("../paths_by_round.csv"); p = p[p["round"] <= 14]
ms = ["gpt-oss-20b (reasoning medium)", "Qwen3-32B thinking on", "Qwen3-32B thinking off"]
fig, ax = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
for a, m in zip(ax, ms):
    for arm, col, lab in (("headline-chat", "#444444", "headline-chat: private chat, no cap"), ("start-5tick", "#1f77b4", "start-5tick: round-1 quotes capped near the floor")):
        s = p[(p.model == m) & (p.arm == arm)]
        a.plot(s["round"], s.price_index, color=col, marker="o", ms=3, label=lab)
    a.set_title(m, fontsize=10); a.set_xlabel("Round of the game (1 to 14)"); a.grid(alpha=.3); a.set_ylim(0, 1)
    a.legend(fontsize=7, loc="lower right")
ax[0].set_ylabel("Price index = (market price - 1) / 2\n(0 = competitive floor)")
fig.suptitle("Mean price index by round, 5-tick start vs matched control (penalty point 3, 20 games per line at round 1)", fontsize=11)
fig.text(0.5, 0.01, "Rounds 8-14 average only games that lasted that long (10 to 15 per line); later rounds are cut because too few games remain.", ha="center", fontsize=8)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig("../paths_by_round.png", dpi=130)
