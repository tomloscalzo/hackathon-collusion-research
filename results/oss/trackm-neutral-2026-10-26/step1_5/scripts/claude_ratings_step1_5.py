#!/usr/bin/env python3
"""Step 1.5 add-on: heat maps and correlation maps of Claude's outcome-blind prompt ratings (claude_conflict, claude_temptation), and the key
comparisons with the models' self-reports and with behaviour. Writes figures/C*.png and tables/claude_*.csv under --out, and replaces the
'External prompt ratings (Claude)' section of STEP1_5.md in place.
gpt-oss-20b adaptation: one model at reasoning effort medium (no thinking-off mode), the five build-bug arms (arm_build_bug = 1) left out.
Usage: python -X utf8 claude_ratings_step1_5.py --run-csv RUN.csv --run neutral|anchored --out STEP1_5_DIR --repo REPO_ROOT"""
import argparse
import sys
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[3] / "_common"))
from oss_arm_labels import maybe as ARMLAB
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--run-csv", required=True)
ap.add_argument("--run", required=True, choices=["neutral", "anchored"])
ap.add_argument("--out", required=True)
ap.add_argument("--repo", required=True)
A = ap.parse_args()
REPO = Path(A.repo)
OUT = Path(A.out)
sys.path.insert(0, str(REPO / "tools"))
from analysis_style import collusion_colors as cc  # noqa: E402

RATINGS = [("claude_conflict", "Claude-rated conflict"), ("claude_temptation", "Claude-rated temptation")]
OUTCOMES = [("market_price_mean", "average spread", cc.COLLUSION), ("price_index", "price index", cc.COLLUSION), ("profit_gain_index", "profit gain index", cc.COLLUSION),
            ("competitive_share", "competitive share", cc.COMPETITION), ("matching_share", "matching share", cc.COLLUSION),
            ("undercut_count", "undercuts (count)", cc.COMPETITION), ("rounds_played", "rounds played", cc.NEUTRAL)]
INPUTS = [("communication", "communication"), ("penalty_point", "penalty point"), ("arm_family", "arm family"), ("arm", "arm"), ("wording", "wording"),
          ("firms", "number of firms")]

df = pd.read_csv(A.run_csv, low_memory=False)
df = df[(df.run == A.run) & (df.status == "done") & df.claude_conflict.notna()].copy()
if "model_label" in df.columns and df.model_label.nunique() != 1:
    raise SystemExit("error: more than one model in run.csv")
if "arm_build_bug" in df.columns:
    df = df[df.arm_build_bug.fillna(0).astype(int) == 0].copy()   # headline-cell replicates of the build bug are not their own arms
RUNLBL = "gpt-oss-20b, reasoning effort medium, neutral"
for c in ("penalty_point", "wording", "firms"):
    df[c] = df[c].astype(int)
(OUT / "figures").mkdir(exist_ok=True)
(OUT / "tables").mkdir(exist_ok=True)
N = len(df)
print(A.run, N, "games")


def order(col):
    if col == "communication":
        return [x for x in ("tacit", "private", "monitored", "public", "unmonitored") if x in set(df[col])]
    return sorted(df[col].unique())


def heat_by_input(col, label, fname):
    levels = order(col)
    M = np.array([[df[df[col] == l][rc].mean() for l in levels] for rc, _ in RATINGS])
    n = np.array([[int((df[col] == l).sum()) for l in levels]] * 2)
    w = max(6.5, 0.62 * len(levels) + 2.5)
    fig, ax = plt.subplots(figsize=(w, 3.4))
    im = ax.imshow(M, cmap=cc.NEUTRAL_CMAP, vmin=1, vmax=5, aspect="auto")
    for i in range(2):
        for j in range(len(levels)):
            ax.text(j, i, "%.2f\nn=%d" % (M[i, j], n[i, j]), ha="center", va="center", fontsize=9 if len(levels) < 15 else 7,
                    color="white" if M[i, j] > 3.6 else "black")
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels([ARMLAB(str(l)) for l in levels], rotation=90 if len(levels) > 8 else 0, fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["conflict", "temptation"], fontsize=10)
    ax.set_xlabel(label)
    ax.set_title("Claude-rated conflict and temptation: mean by %s (%s run)" % (label, RUNLBL), fontsize=10)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("rating, 1 to 5\n(neutral colour, no collusion direction)", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figures" / fname, dpi=110)
    plt.close(fig)
    rows = [dict(variable=col, level=l, rating=rc, mean=M[i, j], n_games=int(n[i, j])) for i, (rc, _) in enumerate(RATINGS) for j, l in enumerate(levels)]
    return rows


tabs = []
figs = []
for k, (col, label) in enumerate(INPUTS):
    fn = "C%02d_claude_by_%s.png" % (k + 1, col)
    tabs += heat_by_input(col, label, fn)
    figs.append((fn, "mean by %s" % label))
pd.DataFrame(tabs).round(4).to_csv(OUT / "tables" / "claude_ratings_means_1var.csv", index=False, lineterminator="\n")

# 2-variable: communication x penalty point
rows2 = []
for rc, rl in RATINGS:
    cm = order("communication")
    pp = order("penalty_point")
    M = np.full((len(cm), len(pp)), np.nan)
    n = np.zeros((len(cm), len(pp)), int)
    for i, a in enumerate(cm):
        for j, b in enumerate(pp):
            d = df[(df.communication == a) & (df.penalty_point == b)]
            n[i, j] = len(d)
            if len(d):
                M[i, j] = d[rc].mean()
            rows2.append(dict(rating=rc, communication=a, penalty_point=b, mean=M[i, j], n_games=n[i, j]))
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    cmap = plt.get_cmap(cc.NEUTRAL_CMAP).copy()
    cmap.set_bad("#dddddd")
    im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=1, vmax=5, aspect="auto")
    for i in range(len(cm)):
        for j in range(len(pp)):
            if n[i, j]:
                ax.text(j, i, "%.2f\nn=%d" % (M[i, j], n[i, j]), ha="center", va="center", fontsize=9, color="white" if M[i, j] > 3.6 else "black")
    ax.set_xticks(range(len(pp)))
    ax.set_xticklabels(["p%d" % x for x in pp])
    ax.set_yticks(range(len(cm)))
    ax.set_yticklabels(cm)
    ax.set_xlabel("penalty point (1 = lightest fine)")
    ax.set_ylabel("communication")
    ax.set_title("%s: mean by communication x penalty point (%s run)" % (rc, RUNLBL), fontsize=10)
    fig.colorbar(im, ax=ax).set_label("rating, 1 to 5\n(neutral colour, no collusion direction)", fontsize=8)
    fig.tight_layout()
    fn = "C%02d_claude_%s_comm_x_point.png" % (len(INPUTS) + 1 + (rc == "claude_temptation"), rc.split("_")[1])
    fig.savefig(OUT / "figures" / fn, dpi=110)
    plt.close(fig)
    figs.append((fn, "%s by communication x penalty point" % rl))
pd.DataFrame(rows2).round(4).to_csv(OUT / "tables" / "claude_ratings_means_2var.csv", index=False, lineterminator="\n")


# correlation map with outcomes
def spear(x, y):
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 8:
        return np.nan, len(d)
    return d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank()), len(d)


splits = [("pooled", df), ("chat arms", df[df.communication_group == "chat"]), ("tacit (no chat)", df[df.communication_group == "tacit"])]
crow = []
fig, axs = plt.subplots(1, 4, figsize=(19, 3.9))
axes = axs.ravel()
for ax, (sn, d) in zip(axes, splits):
    M = np.zeros((2, len(OUTCOMES)))
    for i, (rc, _) in enumerate(RATINGS):
        for j, (oc, ol, _) in enumerate(OUTCOMES):
            r, n = spear(d[rc], d[oc])
            M[i, j] = r
            crow.append(dict(split=sn, rating=rc, outcome=oc, spearman=r, n_games=n))
    im = ax.imshow(M, cmap=cc.NEUTRAL_DIVERGING, vmin=-1, vmax=1, aspect="auto")
    for i in range(2):
        for j in range(len(OUTCOMES)):
            ax.text(j, i, "" if np.isnan(M[i, j]) else "%+.2f" % M[i, j], ha="center", va="center", fontsize=11)
    ax.set_xticks(range(len(OUTCOMES)))
    ax.set_xticklabels([o[1] for o in OUTCOMES], rotation=45, ha="right", fontsize=9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["conflict", "temptation"], fontsize=10)
    ax.set_title("%s (n=%d games)" % (sn, len(d)), fontsize=10)
for _ax in axes[len(splits):]:
    _ax.axis("off")
cax = axes[-1]
cb = fig.colorbar(im, ax=cax, orientation="horizontal", fraction=0.5, pad=0.0)
cb.set_label("Spearman rho, -1 to +1\n(neutral colour, no collusion direction)", fontsize=9)
fig.suptitle("Spearman correlation: Claude-rated conflict and temptation vs outcomes (%s run)" % A.run, fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fcor = "C%02d_claude_correlation_with_outcomes.png" % (len(INPUTS) + 3)
fig.savefig(OUT / "figures" / fcor, dpi=110)
plt.close(fig)
pd.DataFrame(crow).round(4).to_csv(OUT / "tables" / "claude_ratings_correlations.csv", index=False, lineterminator="\n")

# key comparisons: self-report arms
s = df[df.score_name.isin(["conflict_score", "temptation_score"]) & df.score_mean.notna()].copy()
s["claude_same"] = np.where(s.score_name == "conflict_score", s.claude_conflict, s.claude_temptation)
t = s.groupby(["arm", "score_name", "thinking"]).agg(n_games=("row_id", "size"), self_score=("score_mean", "mean"), claude_same_scale=("claude_same", "mean"),
                                                    market_price_mean=("market_price_mean", "mean"), price_index=("price_index", "mean"),
                                                    profit_gain_index=("profit_gain_index", "mean"), competitive_share=("competitive_share", "mean"),
                                                    matching_share=("matching_share", "mean")).reset_index()
t.round(4).to_csv(OUT / "tables" / "claude_vs_self_report.csv", index=False, lineterminator="\n")
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
col = {"off": "#1f77b4", "on": "#d95f02"}   # every gpt-oss game is "on" (reasoning effort medium)
for ax, sn, nm in zip(axes, ("conflict_score", "temptation_score"), ("conflict", "temptation")):
    for _, r in t[t.score_name == sn].iterrows():
        ax.scatter(r.claude_same_scale, r.self_score, c=col[r.thinking], s=50)
        ax.annotate(r.arm.replace("d-", ""), (r.claude_same_scale, r.self_score), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlim(1, 5)
    ax.set_ylim(1, 5)
    ax.plot([1, 5], [1, 5], color="#999999", lw=.8, ls="--")
    ax.set_xlabel("Claude-rated %s of the prompts (1-5)" % nm)
    ax.set_ylabel("Models' self-reported %s score (1-5)" % nm)
    ax.set_title("Self-reported vs Claude-rated %s: per arm (%s run)" % (nm, RUNLBL), fontsize=9)
    ax.grid(alpha=.2)
fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", c=col["on"], label="gpt-oss-20b, reasoning effort medium"),
                    plt.Line2D([], [], ls="--", c="#999999", label="equal scores")], loc="lower center", ncol=3, fontsize=8)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fself = "C%02d_claude_vs_self_report.png" % (len(INPUTS) + 4)
fig.savefig(OUT / "figures" / fself, dpi=110)
plt.close(fig)

# cell-level scatter vs behaviour, both ratings
cells = df.groupby(["arm", "penalty_point", "thinking"])[[r for r, _ in RATINGS] + [o[0] for o in OUTCOMES[:5]]].mean().reset_index()
fig, axes = plt.subplots(2, 5, figsize=(19, 7))
for i, (rc, rl) in enumerate(RATINGS):
    for j, (oc, ol, _) in enumerate(OUTCOMES[:5]):
        ax = axes[i, j]
        for th, d in cells.groupby("thinking"):
            ax.scatter(d[rc], d[oc], c=col[th], s=18, alpha=.7, edgecolors="none")
        r, n = spear(cells[rc], cells[oc])
        ax.set_title("%s vs %s\nSpearman %+.2f, %d cells" % (rl.replace("Claude-rated ", ""), ol, r, n), fontsize=8)
        ax.set_xlabel(rl + " (1-5)", fontsize=8)
        ax.set_ylabel(ol, fontsize=8)
        ax.grid(alpha=.2)
fig.legend(handles=[plt.Line2D([], [], marker="o", ls="", c=col["on"], label="gpt-oss-20b, reasoning effort medium")],
           loc="lower center", ncol=1, fontsize=9)
fig.suptitle("Claude-rated conflict and temptation vs behaviour, one point per cell (arm x penalty point, %s run)" % A.run, fontsize=11)
fig.tight_layout(rect=(0, 0.04, 1, 0.96))
fscat = "C%02d_claude_vs_behaviour_cells.png" % (len(INPUTS) + 5)
fig.savefig(OUT / "figures" / fscat, dpi=110)
plt.close(fig)
cells.round(4).to_csv(OUT / "tables" / "claude_ratings_cells.csv", index=False, lineterminator="\n")

# ---------------------------------------------------------------- the section
cr = pd.DataFrame(crow)
cp = cr[cr.split == "pooled"].pivot(index="outcome", columns="rating", values="spearman")
L = []
a = L.append
a("## External prompt ratings (Claude)")
a("")
a("Three independent Claude raters scored the text of every distinct prompt, blind to arm names and results, on two 1-to-5 scales (rubric and procedure: `results/prompt-ratings/README.md`): **conflict** = how far the prompt's own instructions disagree with each other (1 consistent, 5 directly contradictory); **temptation** = how far it makes coordinating on high prices attractive, salient or easy (1 no pull, 5 very strong pull). Agreement between raters: weighted kappa 0.82 (conflict) and 0.87 (temptation). The ratings are in `run.csv` as `claude_conflict` and `claude_temptation` (mean of the raters; where the firms see different texts, the mean over the firms), constant across seeds of one prompt (the same ratings as for Qwen3-32B: the prompt texts are model-independent). They are not keyword-based, so they carry no UNVALIDATED mark; their check is the rater agreement. Cell values below are means over the counted games of the %s run (%d games) and are raw means with no tests." % (RUNLBL, N))
a("")
a("**1-variable heat maps (mean rating by input).** Neutral-hue scale 1 to 5 (the ratings have no collusion direction); each cell shows the mean and the number of games.")
a("")
for fn, ttl in figs[:len(INPUTS)]:
    a("![Claude-rated conflict and temptation, %s, %s run](figures/%s)" % (ttl, RUNLBL, fn))
    a("")
a("**2-variable heat maps.**")
a("")
for fn, ttl in figs[len(INPUTS):]:
    a("![%s, %s run](figures/%s)" % (ttl, RUNLBL, fn))
    a("")
a("**Correlation heat map with the outcomes.** Spearman rank correlation of each rating with each outcome over counted games (neutral diverging colours centred on 0, limits -1 to 1; cells annotated with rho; n in each panel title). A rating is constant within a prompt text, so games of one text are not independent: read the coefficients as descriptive. The average spread, price index and profit gain index are rescalings of one another, so their coefficients are (almost) identical.")
a("")
a("![Spearman correlation of Claude-rated conflict and temptation with outcomes, %s run](figures/%s)" % (RUNLBL, fcor))
a("")
a("Pooled: Claude-rated temptation correlates %+.2f with the price index, %+.2f with the profit gain index, %+.2f with the competitive share and %+.2f with the matching share; Claude-rated conflict correlates %+.2f, %+.2f, %+.2f and %+.2f. Source: `tables/claude_ratings_correlations.csv`." % (
    cp.loc["price_index", "claude_temptation"], cp.loc["profit_gain_index", "claude_temptation"], cp.loc["competitive_share", "claude_temptation"], cp.loc["matching_share", "claude_temptation"],
    cp.loc["price_index", "claude_conflict"], cp.loc["profit_gain_index", "claude_conflict"], cp.loc["competitive_share", "claude_conflict"], cp.loc["matching_share", "claude_conflict"]))
a("")
a("**Key comparison 1: Claude-rated versus the models' own self-reported scores.** Only the D-set arms ask for a score (`d-conflict`: conflict; `d-temptation-a`, `d-temptation-b`: temptation). Each point is one arm (all at reasoning effort medium); the dashed line marks equal scores.")
a("")
a("![Self-reported versus Claude-rated scores, %s run](figures/%s)" % (RUNLBL, fself))
a("")
a("| Arm | Reasoning | Games | Self-reported score | Claude-rated (same scale) | Average spread | Price index | Profit gain index | Competitive share | Matching share |")
a("|---|---|---|---|---|---|---|---|---|---|")
for _, r in t.iterrows():
    a("| %s | %s | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f |" % (r.arm, "medium", r.n_games, r.self_score, r.claude_same_scale, r.market_price_mean, r.price_index, r.profit_gain_index, r.competitive_share, r.matching_share))
a("")
_sr = t.groupby("score_name").agg(self_score=("self_score", "mean"), claude=("claude_same_scale", "mean"))
if len(_sr):
    a("On gpt-oss-20b (game-weighted means over the arms of each score): " + "; ".join("%s self-reported %.2f vs Claude-rated %.2f on the same prompts" % (k.replace("_score", ""), v.self_score, v.claude) for k, v in _sr.iterrows()) + ". Self-report scores are the model's text, not evidence of an internal state. Qwen3-32B comparison: `results/ad-hoc-targeted-analysis/conflict-score-validation` section 5 and `self-report-scores` section 6.")
else:
    a("No D-set score games are done yet.")
a("")
if False: a("The self-reported conflict is 1.00 where Claude rates the prompt as consistent; the self-reported temptation (about 2.2 to 2.7) is well below Claude's rating of the same prompts (about 4). Claude reads a stronger pull in the text than the models report. Self-report scores are the models' text, not evidence of an internal state. Full analysis: `results/ad-hoc-targeted-analysis/conflict-score-validation` section 5 and `self-report-scores` section 6.")
a("")
a("**Key comparison 2: Claude-rated versus behaviour.** One point per cell (arm x penalty point; every cell at reasoning effort medium), each of the five behaviour metrics shown separately.")
a("")
a("![Claude-rated conflict and temptation versus behaviour per cell, %s run](figures/%s)" % (RUNLBL, fscat))
a("")
a("<small>")
a("")
a("**Terms for the external-rating figures.**")
a("")
a("| Label | Precise definition |")
a("|---|---|")
a("| Claude-rated conflict / temptation | Mean of three independent Claude raters' 1-to-5 scores of the prompt text (see above); run.csv `claude_conflict`, `claude_temptation`. |")
a("| Cell (heat maps, n) | Counted games of the %s run (payoff table: %s) with that input level; n = number of games. |" % (A.run, "evenly spaced examples 1.00 to 4.00" if A.run == "neutral" else "worked examples 1.54, 2.09 and 3.00"))
a("| Communication | tacit = no chat; private chat; monitored = a regulator reads the chat; public = chat is published; unmonitored = chat stated not monitored. |")
a("| Penalty point (p1 to p5) | How heavy the regulator's fine is; 1 = collusion clearly pays, 5 = clearly does not. |")
a("| Reasoning effort medium | gpt-oss-20b always reasons before replying, at effort medium; it has no thinking-off mode, so there is no thinking contrast. The rating does not depend on it. |")
a("| Build-bug arms | The five planned formula / no-numbers arms (fx-*, nx-*) of this run played the neutral headline prompt (a grid override); they are left out of these maps. |")
a("| Average spread | Mean best quote over rounds, raw half-spread units, 1.00 competitive to 5.00. |")
a("| Price index | (market price - 1)/2 averaged over rounds; 0 competitive, 1 monopoly. |")
a("| Profit gain index | (mean profit - competitive profit)/(monopoly profit - competitive profit). |")
a("| Competitive share (U16) | Share of firm-rounds undercutting the lowest rival quote of the previous round, or both at 1.00; higher = more competitive. |")
a("| Matching share | Share of firm-rounds matching the lowest rival quote of the previous round above the floor; the coordination signature. |")
a("| Spearman rho | Rank correlation, -1 to +1; no confidence interval at this stage (descriptive). |")
a("| Self-reported score | The firm's own integer 1 to 5 answer after its quote, averaged over rounds and firms (D-set arms only). |")
a("")
a("</small>")
a("")
sec = "\n".join(L) + "\n"
p = OUT / "STEP1_5.md"
t0 = p.read_text(encoding="utf-8")
i = t0.index("## External prompt ratings (Claude)")
j = t0.index("## Most striking patterns")
p.write_text(t0[:i] + sec + t0[j:], encoding="utf-8", newline="\n")
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(p)
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("section written")
