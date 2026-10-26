"""Figure: observed price index vs the detection x penalty composite, with the Layer A theta* curve.
Run: python -X utf8 figure.py OUT_DIR   (inputs: the same local run tables as corroborate.py)"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aff  # noqa: F401,E402
from layer_a import solve  # noqa: E402
REPO = os.environ.get("REPO_DIR", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import arm_labels  # noqa: E402

HK = os.environ.get("HACKATHON_DIR", os.path.join(os.path.expanduser("~"), "hackathon")).replace("\\", "/")
W = HK + "/work_scratch/"
OUT = sys.argv[1] if len(sys.argv) > 1 else W + "model_corroboration/out"
FINES = {1: 100, 3: 500, 4: 1000, 5: 2000}
COMP = {p: solve(fine=f)["composite"] for p, f in FINES.items()}
rng = np.random.default_rng(20261026)


def ci(v):
    v = np.asarray(v, float)
    m = v[rng.integers(0, len(v), (2000, len(v)))].mean(1)
    return v.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


oss = pd.read_csv(W + "oss_analysis/step1/final_t2/run.csv", low_memory=False)
oss = oss[(oss.status == "done") & (oss.in_primary == 1) & (oss.arm_build_bug != 1)]
qn = pd.read_csv(W + "analysis_final/steps/neutral/step1/run.csv", low_memory=False)
qn = qn[(qn.status == "done") & (qn.in_primary == 1)]
fx = pd.read_csv(W + "fx_ctl_joint/final/game_metrics.csv")
fx = fx[fx.cell.isin(["Q fx-chat-p1", "Q fx-chat-p5"])].assign(arm="fx-chat", penalty_point=lambda d: np.where(d.cell.str.endswith("p5"), 5, 1))
oss = oss.assign(arm=oss.arm.replace({"fx-chat-p1": "fx-chat", "fx-chat-p5": "fx-chat"}))

SER = [("headline-chat", arm_labels.label("headline-chat"), "#0072B2", "o"),
       ("headline-tacit", arm_labels.label("headline-tacit"), "#E69F00", "s"),
       ("headline-monitored", arm_labels.label("headline-monitored"), "#009E73", "^"),
       ("fx-chat", arm_labels.label("fx-chat-p1").replace(", p1", "") + " (p1 and p5)", "#CC79A7", "D")]
panels = [("gpt-oss-20b (reasoning effort medium)", oss), ("Qwen3-32B, thinking on (t1)", pd.concat([qn[qn.thinking == "on"], fx])),
          ("Qwen3-32B, thinking off (t0)", qn[qn.thinking == "off"])]

# theory curve over the composite
fs = np.linspace(0, 2400, 241)
tc = [(solve(fine=f)["composite"], solve(fine=f, grid=20001)["theta_star"]) for f in fs]
tc = np.array(tc)

fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharey=True, constrained_layout=True)
rows = []
for ax, (title, df) in zip(axes, panels):
    ax.plot(tc[:, 0], tc[:, 1], color="#222222", lw=2, label="Layer A model: sustainable collusive level θ* (price index)")
    ax.axvline(4, color="#777777", ls="--", lw=1.2)
    ax.text(4.08, 0.97, "threshold = 4\n(no collusion above)", fontsize=9, color="#444444", va="top")
    off = {"headline-chat": -0.03, "headline-tacit": 0.0, "headline-monitored": 0.03, "fx-chat": 0.06}
    n_tot = 0
    for arm, lab, col, mk in SER:
        s = df[df.arm == arm]
        if not len(s):
            continue
        xs, ys, lo, hi = [], [], [], []
        for p in sorted(s.penalty_point.unique()):
            v = s[s.penalty_point == p].price_index.astype(float).dropna()
            m, l, h = ci(v)
            xs.append(COMP[int(p)] * (1 + off[arm])); ys.append(m); lo.append(m - l); hi.append(h - m)
            rows.append(dict(panel=title, arm=arm, penalty_point=int(p), composite=COMP[int(p)], n_games=len(v), mean=m, lo=l, hi=h))
            n_tot += len(v)
        ax.errorbar(xs, ys, yerr=[lo, hi], color=col, marker=mk, ms=8, lw=2, capsize=3, label=lab)
    ax.set_xscale("log")
    ax.set_xticks([0.25, 1.25, 2.5, 5.0])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xticklabels(["0.25\np1\nfine 100", "1.25\np3\nfine 500", "2.5\np4\nfine 1000", "5.0\np5\nfine 2000"], fontsize=9)
    ax.set_xlim(0.18, 7)
    ax.set_ylim(-0.02, 1.0)
    sub = "neutral payoff table" if "off" in title else "neutral payoff table; fx-chat: formula payoff block"
    ax.set_title("%s\n%s, n = %d games" % (title, sub, n_tot), fontsize=10)
    ax.grid(alpha=0.25)
axes[0].set_ylabel("Price index (0 = competitive 1.00, 1 = monopoly 3.00)\nmean over games, 95% bootstrap CI", fontsize=10)
fig.supxlabel("Detection × penalty composite = screen slope × P(evidence) × fine ratio × (s̄/s₀ − 1)   (log scale; tick labels give the penalty point and the fine)", fontsize=10)
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=9, frameon=False)
fig.suptitle("Observed LLM price index vs the Layer A model's θ*, by detection × penalty composite (exploratory)", fontsize=12)
fig.savefig(os.path.join(OUT, "fig_price_vs_composite.png"), dpi=130, bbox_inches="tight")
pd.DataFrame(rows).to_csv(os.path.join(OUT, "fig_price_vs_composite_values.csv"), index=False)
print("ok")
