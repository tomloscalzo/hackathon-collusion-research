"""Scatter plots for dossier 10 (owner observation 10: full game-level and (arm, wording)-level scatters, both models).
Reads ../points/*.csv written by ratings_vs_behaviour.py and self_reports.py. Run: python -X utf8 figures.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C

OUT = Path(__file__).resolve().parents[1]
P = OUT / "points"
FIG = OUT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.titlesize": 10, "axes.labelsize": 10})
COMM = {"tacit": ("#2a78d6", "tacit: no chat"), "private": ("#eb6834", "private: private chat"),
        "monitored": ("#1baf7a", "monitored: chat read by the regulator"), "public": ("#eda100", "public: public chat"),
        "unmonitored": ("#e87ba4", "unmonitored: chat said to be unmonitored")}
ROWS = [("oss", "gpt-oss-20b, medium effort (neutral run)"), ("qwen_t1", "Qwen3-32B, thinking on (neutral run)"),
        ("qwen_t0", "Qwen3-32B, thinking off (neutral run)")]
YL = {"market_price_mean": "Avg abs spread\n(half-spread, 1.00-5.00)", "price_index": "Price index\n(0 comp. - 1 monopoly)",
      "profit_gain_index": "Profit gain index\n(0 comp. - 1 monopoly)", "competitive_share": "Competitive share U16\n(higher = more competitive)",
      "matching_share": "Matching share\n(higher = more coordinated)"}
rng = np.random.default_rng(1)


def scatter_grid(rating, level, fname, xlabel, title):
    fig, axes = plt.subplots(3, 5, figsize=(18.5, 10.5), constrained_layout=True)
    for i, (tag, rlabel) in enumerate(ROWS):
        d = pd.read_csv(P / f"{tag}_{level}.csv")
        for j, m in enumerate(C.MCOLS):
            ax = axes[i, j]
            x = d[rating].to_numpy(float)
            if level == "game":
                x = x + rng.uniform(-0.06, 0.06, len(x))
            for comm, (col, _) in COMM.items():
                s = d.communication == comm
                if s.any():
                    ax.scatter(x[s], d.loc[s, m], s=10 if level == "game" else 22, c=col, alpha=0.45 if level == "game" else 0.8,
                               edgecolors="white", linewidths=0.4)
            sp, pe, n = C.corr_pair(d[rating], d[m])
            ax.set_title(f"Spearman {sp:+.2f}, Pearson {pe:+.2f}, n = {n}")
            ax.set_xlim(0.8, 5.2); ax.grid(alpha=0.25)
            if j == 0:
                ax.set_ylabel(f"{rlabel.split(' (')[0]}\n{YL[m]}")
            else:
                ax.set_ylabel(YL[m])
            if i == 2:
                ax.set_xlabel(xlabel)
    handles = [Line2D([], [], marker="o", ls="", color=c, label=l, markersize=7) for c, l in COMM.values()]
    fig.legend(handles=handles, loc="outside lower center", ncol=5, title="Point colour: communication condition of the prompt")
    fig.suptitle(title, fontsize=12)
    fig.savefig(FIG / fname, dpi=110)
    plt.close(fig)


unit = {"prompt": "one point = one (arm, penalty point, wording) prompt text, mean over its seeds (about 4 games)",
        "game": "one point = one game (x jittered by up to 0.06 for visibility)"}
for rating, rl in (("claude_temptation", "temptation"), ("claude_conflict", "conflict")):
    for level in ("prompt", "game"):
        scatter_grid(rating, level, f"fig_{rl}_{level}.png",
                     f"Claude-rated {rl} of the prompt\n(1 to 5, mean of 3 outcome-blind raters)",
                     f"Claude-rated {rl} vs the five collusion metrics, gpt-oss-20b and Qwen3-32B (neutral run); {unit[level]}")

# ---- self-reports, game level: the temptation self-score (A circle, B square) and the placebo (grey) vs the five metrics
S = pd.read_csv(P / "selfreport_games.csv")
MODELS = [("gpt-oss-20b (medium effort)", "gpt-oss-20b, medium effort"), ("Qwen3-32B thinking on", "Qwen3-32B, thinking on"),
          ("Qwen3-32B thinking off", "Qwen3-32B, thinking off")]
fig, axes = plt.subplots(3, 5, figsize=(18.5, 10.5), constrained_layout=True)
for i, (ds, rl) in enumerate(MODELS):
    t = S[(S.dataset == ds) & (S.score == "temptation (A+B pooled)")]
    pl = S[(S.dataset == ds) & (S.score == "placebo (random number)")]
    for j, m in enumerate(C.MCOLS):
        ax = axes[i, j]
        for arm, mk in (("d-temptation-a", "o"), ("d-temptation-b", "s")):
            s = t[t.arm == arm]
            ax.scatter(s.score_mean, s[m], marker=mk, s=28, c="#eb6834", edgecolors="white", linewidths=0.4, alpha=0.85)
        ax.scatter(pl.score_mean, pl[m], marker="^", s=26, c="#8c8c8c", alpha=0.7, edgecolors="white", linewidths=0.4)
        sp, pe, n = C.corr_pair(t.score_mean, t[m])
        sp2, pe2, n2 = C.corr_pair(pl.score_mean, pl[m])
        ax.set_title(f"temptation: S {sp:+.2f}, P {pe:+.2f}, n {n}\nplacebo: S {sp2:+.2f}, P {pe2:+.2f}, n {n2}" if np.isfinite(sp2)
                     else f"temptation: S {sp:+.2f}, P {pe:+.2f}, n {n}\nplacebo: constant (no correlation)")
        ax.set_xlim(0.8, 5.2); ax.grid(alpha=0.25)
        ax.set_ylabel((rl + "\n" if j == 0 else "") + YL[m])
        if i == 2:
            ax.set_xlabel("Game-mean self-reported score\n(1 to 5, typed by the firm after each quote)")
h = [Line2D([], [], marker="o", ls="", color="#eb6834", label="d-temptation-a: self-rated temptation, version A"),
     Line2D([], [], marker="s", ls="", color="#eb6834", label="d-temptation-b: self-rated temptation, version B"),
     Line2D([], [], marker="^", ls="", color="#8c8c8c", label="d-placebo: 'a whole number from 1 to 5, chosen at random'")]
fig.legend(handles=h, loc="outside lower center", ncol=3, title="Marker: which self-report question (all private chat, penalty point 1)")
fig.suptitle("Self-reported scores vs the five collusion metrics, one point per game (S = Spearman, P = Pearson)", fontsize=12)
fig.savefig(FIG / "fig_selfreport_game.png", dpi=110); plt.close(fig)

# ---- self-reports vs Claude ratings, (arm, wording) level
fig, axes = plt.subplots(2, 3, figsize=(14, 8.5), constrained_layout=True)
for j, (ds, rl) in enumerate(MODELS):
    for i, (score, rc, arms) in enumerate([("temptation (A+B pooled)", "claude_temptation", {"d-temptation-a": ("o", "#eb6834"), "d-temptation-b": ("s", "#eb6834")}),
                                            ("conflict (both arms)", "claude_conflict", {"d-conflict": ("o", "#2a78d6"), "d-conflict-ethics": ("D", "#1baf7a")})]):
        ax = axes[i, j]
        g = S[(S.dataset == ds) & (S.score == score)].groupby(["arm", "wording"])[["score_mean", rc]].mean().reset_index()
        for arm, (mk, col) in arms.items():
            s = g[g.arm == arm]
            ax.scatter(s[rc], s.score_mean, marker=mk, c=col, s=40, edgecolors="white", linewidths=0.5)
        ax.plot([1, 5], [1, 5], ls=":", c="#8c8c8c", lw=1)
        sp, pe, n = C.corr_pair(g[rc], g.score_mean)
        if g.score_mean.max() - g.score_mean.min() < 0.05:   # self-score constant at about 1.00: no meaningful correlation
            ax.set_title(f"{rl}\nSpearman and Pearson n/a (constant), n = {n}")
        else:
            ax.set_title(f"{rl}\nSpearman {sp:+.2f}, Pearson {pe:+.2f}, n = {n} texts" if np.isfinite(sp) else f"{rl}\nn = {n} texts (too few to correlate)")
        ax.set_xlim(0.8, 5.2); ax.set_ylim(0.8, 5.2); ax.grid(alpha=0.25)
        ax.set_xlabel(f"Claude-rated {score.split(' ')[0]} of the prompt text (1 to 5)")
        ax.set_ylabel(f"Self-reported {score.split(' ')[0]} score\n(mean over the text's games, 1 to 5)")
h = [Line2D([], [], marker="o", ls="", color="#eb6834", label="d-temptation-a: temptation question A"),
     Line2D([], [], marker="s", ls="", color="#eb6834", label="d-temptation-b: temptation question B"),
     Line2D([], [], marker="o", ls="", color="#2a78d6", label="d-conflict: conflict question, no rule"),
     Line2D([], [], marker="D", ls="", color="#1baf7a", label="d-conflict-ethics: conflict question + 'do not coordinate' rule (gpt-oss only)"),
     Line2D([], [], ls=":", color="#8c8c8c", label="equality line (the two 1-5 scales are not calibrated)")]
fig.legend(handles=h, loc="outside lower center", ncol=3)
fig.suptitle("Claude's outcome-blind rating of each prompt text vs the firms' own self-report, one point per (arm, wording) text", fontsize=12)
fig.savefig(FIG / "fig_claude_vs_self.png", dpi=110); plt.close(fig)
# ---- cell level: Claude-rated temptation vs price index, one panel per model mode, key arms labelled "slug: short label"
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "analysis_style"))
import arm_labels  # noqa: E402  shared glossary
import textwrap  # noqa: E402
KEY = ["ctl-32b-compete", "ctl-32b-joint", "m-inc-joint", "moral-prime", "moral-prime-b", "moral-placebo",
       "wd-noncomp", "wd-ask-noreport", "wd-notice-only", "d-cot-monitor-a", "d-cot-monitor-b"]
fig, axes = plt.subplots(1, 3, figsize=(23, 8), constrained_layout=True)
shown = set()
for ax, (tag, rlabel) in zip(axes, ROWS):
    d = pd.read_csv(P / f"{tag}_cell.csv")
    for comm, (col, _) in COMM.items():
        s = d.communication == comm
        if s.any():
            ax.scatter(d.loc[s, "claude_temptation"], d.loc[s, "price_index"], s=46, c=col, edgecolors="white", linewidths=0.6)
    sp, pe, n = C.corr_pair(d.claude_temptation, d.price_index)
    ax.set_title(f"{rlabel}\nSpearman {sp:+.2f}, Pearson {pe:+.2f}, n = {n} cells")
    k = d[d.arm.isin(KEY)].sort_values("price_index").reset_index(drop=True)
    for i, r in k.iterrows():
        shown.add(r.arm)
        num = KEY.index(r.arm) + 1   # numbered key (labels would overlap); the key is printed beside the panels
        ax.scatter([r.claude_temptation], [r.price_index], s=90, facecolors="none", edgecolors="#333333", linewidths=1.0)
        ax.annotate(str(num), (r.claude_temptation, r.price_index), xytext=(6, [6, -12][i % 2]), textcoords="offset points",
                    fontsize=10, fontweight="bold", color="#222222")
    ax.set_xlim(0.6, 5.4); ax.set_ylim(-0.08, 1.08); ax.grid(alpha=0.25)
    ax.set_xlabel("Claude-rated temptation of the cell's prompts\n(1 to 5, mean of 3 outcome-blind raters, cell mean)")
    ax.set_ylabel("Price index, mean of the cell's games\n(0 = 1.00 competitive, 1 = 3.00 monopoly)")
handles = [Line2D([], [], marker="o", ls="", color=c, label=l, markersize=8) for c, l in COMM.values()]
fig.legend(handles=handles, loc="outside lower center", ncol=5, title="Point colour: communication condition of the cell")
keytxt = "Numbered (circled) cells\n\n" + "\n".join(
    textwrap.fill(f"{KEY.index(s) + 1}  {arm_labels.label(s)}", 34, subsequent_indent="    ") for s in KEY if s in shown)
fig.legend(handles=[Line2D([], [], ls="", label=keytxt)], loc="outside right center", handlelength=0, fontsize=9.5,
           frameon=True)
fig.suptitle("Claude-rated temptation vs price index, one point per (arm, penalty point) cell, neutral run; "
             "labelled: instruction controls, moral primes, watchdog and reasoning-monitor arms", fontsize=11.5)
fig.savefig(FIG / "fig_temptation_cell.png", dpi=110); plt.close(fig)
with open(FIG / "fig_temptation_cell_legend.md", "w", encoding="utf-8") as f:
    f.write(arm_labels.legend_table([s for s in KEY if s in shown]))
print("figures written:", sorted(p.name for p in FIG.glob("*.png")))
