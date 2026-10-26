"""Print markdown tables of contrasts_all.csv for ANALYSIS.md. Usage: python -X utf8 make_tables_md.py <dir>
Created by Claude at the prompting of the repository owner."""
import os, sys
import pandas as pd
D = sys.argv[1]
r = pd.read_csv(os.path.join(D, "contrasts_all.csv"))
lab = {"gptoss_t1": "gpt-oss (medium effort)", "qwen_t1": "Qwen thinking on", "qwen_t0": "Qwen thinking off"}
for t in r.tactic.unique():
    g = r[r.tactic == t]
    print(f"\n**{t}: {g.description.iloc[0]}** (arm minus headline-chat p1, paired on wording and seed)\n")
    print("| Metric | " + " | ".join(f"{lab[m]} (n {int(g[g.model_mode==m].n_pairs.iloc[0])})" for m in lab) + " |")
    print("|---|---|---|---|")
    for met in g.metric.unique():
        cells = []
        for m in lab:
            x = g[(g.model_mode == m) & (g.metric == met)].iloc[0]
            cells.append(f"{x.effect:+.3f} [{x.ci_lo:+.3f}, {x.ci_hi:+.3f}]; p {x.p:.3f}; Holm {x.holm_p:.2f}; MDE {x.mde:.3f}")
        print(f"| {met} | " + " | ".join(cells) + " |")
