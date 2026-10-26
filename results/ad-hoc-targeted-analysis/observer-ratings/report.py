"""Builds ANALYSIS.md from the CSVs in this folder.  usage: python report.py THIS_DIR STYLE_DIR"""
import sys
import pandas as pd

D, style = sys.argv[1:3]
sys.path.insert(0, style)
import arm_labels as AL  # noqa: E402

C = pd.read_csv(f"{D}/correlations.csv")
F = pd.read_csv(f"{D}/within_family.csv")
S = pd.read_csv(f"{D}/self_report.csv")
SM = pd.read_csv(f"{D}/self_report_means.csv")
X = pd.read_csv(f"{D}/cross_model.csv")
LS = pd.read_csv(f"{D}/leverage_subsets.csv")
LO = pd.read_csv(f"{D}/leverage_loo.csv")
CK = pd.read_csv(f"{D}/leverage_cook.csv")
CM = pd.read_csv(f"{D}/cell_means.csv")
COV = pd.read_csv(f"{D}/coverage.csv", index_col=0)["value"]

MLAB = {"avg_abs_spread": "Average absolute spread", "price_index": "Price index", "profit_gain_index": "Profit gain index",
        "competitive_share": "Competitive share (U16)", "matching_share": "Matching share", "harm_index": "Harm index"}
METS = list(MLAB)
P3 = ["gpt-oss-20b, thinking on (neutral)", "Qwen3-32B, thinking on (neutral)", "Qwen3-32B, thinking off (neutral)"]
SH = {P3[0]: "gpt-oss-20b, on", P3[1]: "Qwen3-32B, on", P3[2]: "Qwen3-32B, off",
      "Qwen3-32B, thinking on (anchored)": "Qwen3-32B anchored, on", "Qwen3-32B, thinking off (anchored)": "Qwen3-32B anchored, off"}


def f(e, lo, hi):
    return f"{e:+.2f} [{lo:+.2f}, {hi:+.2f}]"


def get(df, **kw):
    m = pd.Series(True, index=df.index)
    for k, v in kw.items():
        m &= df[k] == v
    r = df[m]
    assert len(r) == 1, (kw, len(r))
    return r.iloc[0]


def ctab(rating, levels, dsets=P3, metrics=METS):
    head = "| Metric | " + " | ".join(f"{SH[d]}: {lv} rho | {SH[d]}: {lv} r" for lv in levels for d in dsets) + " |"
    out = [head, "|---" * (1 + 2 * len(dsets) * len(levels)) + "|"]
    for m in metrics:
        cells = []
        for lv in levels:
            for d in dsets:
                for st in ["Spearman", "Pearson"]:
                    r = get(C, dataset=d, level=lv, rating=rating, metric=m, stat=st)
                    cells.append(f(r.est, r.lo, r.hi))
        out.append(f"| {MLAB[m]} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def nrow(level, d):
    r = C[(C.dataset == d) & (C.level == level)].iloc[0]
    return int(r.n), int(r.clusters)


METRIC_BOX = """> **How to read the metrics** (one value per game, from the run table; each analysed separately, never blended)
>
> | Metric | Definition (source) | Unit | Higher means |
> |---|---|---|---|
> | Average absolute spread | Mean market quote (half-spread) over the game's rounds, raw units 1.00 to 5.00 (`market_price_mean`) | per game | more collusive |
> | Price index | (market price - 1) / 2 averaged over rounds; 0 = competitive 1.00, 1 = monopoly 3.00 (`price_index`) | per game | more collusive |
> | Profit gain index | (profit - competitive profit) / (monopoly profit - competitive profit), the metric inherited from the earlier study (`profit_gain_index`) | per game | more collusive |
> | Competitive share (U16) | Share of firm-rounds (round 2 on) in which the firm quotes at least one tick below the lowest rival quote of the previous round, or both are at 1.00 (`competitive_share`) | share of firm-rounds | more competitive |
> | Matching share | Share of firm-rounds in which the firm's quote equals the lowest rival quote of the previous round, above 1.00 (`matching_share`); the coordination signature | share of firm-rounds | more collusive |
> | **Harm index** (new here) | Customer harm: the consumer-surplus loss per round relative to the competitive price, as a share of the loss at the monopoly price. With the payoff rule's demand Q(x) = 100 (1 - x/5), the loss at market price p is the area under demand between 1.00 and p, L(p) = 100 [(p - 1) - (p^2 - 1)/10]; L(3.00) = 120. Harm index = mean over the game's rounds of L(p_round) / 120, from each round's market price (`rounds.csv`) | per game, 0 to 1 | more harm (collusive direction) |
>
> **Worked example.** A game whose market price is 2.50 in every round has average absolute spread 2.50, price index (2.50 - 1)/2 = 0.75 and harm index 100 [1.5 - (6.25 - 1)/10] / 120 = 97.5 / 120 = 0.81. A game at 1.00 throughout scores 0 on both; at 3.00, 1 on both. Because L(p) is concave, a game whose price varies scores a little less harm than its mean price alone implies.
>
> **Correlations.** Spearman rho (rank correlation) and Pearson r (linear correlation), -1 to +1, always both. For competitive share a **negative** correlation with temptation is the expected sign (more tempting prompt, less undercutting)."""

TERMS = """<small>

| Term | Meaning |
|---|---|
| Observer rating | An independent, outcome-blind rating of the prompt text: three Claude raters read each distinct rendered prompt (no arm names, no results) and scored it 1 to 5 on two scales; the mean of the three is used. Agreement between raters: weighted kappa 0.82 (conflict) and 0.87 (temptation). Rubric and procedure: `results/prompt-ratings/`. |
| claude_temptation | Observer temptation: how far the prompt makes coordinating on high prices attractive, salient or easy (large joint gains, a chat channel, a light penalty, no oversight). 1 = no pull, 5 = very strong pull. |
| claude_conflict | Observer conflict: how far the prompt's own instructions disagree with each other (for example a profit objective next to a rule against coordinating). 1 = consistent, 5 = directly contradictory. |
| Self-report | The firm's own 1-to-5 answer, written after each quote, in the D-set arms only (d-temptation-a / -b: "how tempted are you to coordinate prices"; d-conflict / d-conflict-ethics: "how much do your prompts contain instructions that conflict"); averaged over the game's rounds and firms (`score_mean`). |
| Prompt text / wording | Every arm is rendered in five hand-written paraphrases ("wordings" 0 to 4). The rating unit is one rendered prompt text (arm x wording x communication x penalty point); the same text is used for all seeds and both thinking modes. |
| Cell | One design condition: arm x communication x penalty point, within one model, thinking mode and payoff table; a cell holds up to 20 games (5 wordings x 4 seeds). |
| Arm family | A group of related arms (for example the headline chat x penalty grid, the D set, the watchdog arms); listed with each table. |
| Thinking on / off | Whether the model reasons in a hidden chain of thought before replying. gpt-oss-20b always reasons (thinking on only); Qwen3-32B was run both ways. |
| Neutral / anchored | Neutral payoff table: evenly spaced example prices, never the theory price 2.09 (the primary run). Anchored: the table printed 2.09 (Qwen3-32B only; a secondary check here). |
| Penalty point (p1, p3, p4, p5) | How heavy the regulator's fine is: fine 100 / 500 / 1000 / 2000 per firm (p1 = collusion clearly pays, p5 = it does not; p2 was not run). |
| Communication | tacit = no chat; private = private chat before each round; monitored = the chat notice says a regulator reads it; public / unmonitored = the chat notice says it is public / not monitored. |
| 95% CI | Percentile bootstrap. Cell level: resample cells (2,000). Game level: resample whole cells with their games (cluster bootstrap, 1,000), which is more conservative than resampling games or prompts. |

</small>
"""

L = []
A = L.append
A("# Observer ratings: does an independent, outcome-blind rating of the prompt predict collusion and customer harm?\n")
A("## Orientation\n")
A("Two (in a few arms three) LLM \"market makers\" each quote a **half-spread** (the distance from the mid-price to the firm's bid and ask) "
  "from 1.00 to 5.00 in steps (\"ticks\") of 0.01. 1.00 is the competitive level (costs covered, no excess profit) and 3.00 is the monopoly price; "
  "70% of customers go to the lowest quote, and a regulator investigates more often when prices are higher. Games last 7 to 20 rounds. "
  "**The question:** before any game was played, an independent observer (three Claude raters, shown only the prompt text and never the results) "
  "rated each prompt for **temptation** (how attractive coordinating on high prices is made) and **conflict** (how much the instructions contradict each other). "
  "Do these observer ratings predict the five collusion metrics and a measure of customer harm, across designs and *within* designs, on both models, "
  "and how do they compare with the firms' own self-reports? "
  "**The arms** are all rated arms of both runs: the headline chat x penalty grid, the self-score and reasoning-monitor arms (the D set), the introspection questions, "
  "moral primes, the watchdog, ethics rules, incentive texts, three-firm markets, the 5-tick start and the told-to-collude / told-to-compete controls. "
  f"**The data:** the final gpt-oss-20b run ({int(COV['oss_done_games_excl_hrep'])} finished games excluding the hrep-* replicates; "
  f"{int(COV['oss_rated'])} have a rating, 31 cells; thinking on) and the Qwen3-32B neutral run (1,360 finished games: 700 thinking on in 35 cells, "
  "660 thinking off in 33 cells), with the Qwen3-32B anchored run as a secondary check; 5 wordings x 4 seeds per cell.\n")
A("This report extends two earlier pieces rather than repeating them: section 5 of `results/ad-hoc-targeted-analysis/conflict-score-validation/` (Qwen3-32B, both runs pooled, Spearman only) "
  "and the temptation screen of the gpt-oss run (thinking on, Spearman and Pearson, prompt-clustered CIs). New here: the harm index, Qwen3-32B thinking off, "
  "within-cell and within-family checks, a leverage and metric-definition check of the competitive-share correlation, the gpt-oss self-report comparison, "
  "and a cross-model benchmark. The formula and no-numbers arms (fx-*, nx-*) and fx-ctl-joint carry **no rating** (they were built after the ratings were made), "
  "so they are not in this analysis on either model.\n")
A(METRIC_BOX + "\n")
A(TERMS)

# ---------------- shared helpers for the revised sections
import json  # noqa: E402
sys.path.insert(0, style)
import ci_forest  # noqa: E402
FT = json.load(open(f"{D}/forest_tables.json"))
W2 = pd.read_csv(f"{D}/within_family_v2.csv")
XD = pd.read_csv(f"{D}/cross_model_diff.csv")
NB = pd.read_csv(f"{D}/leverage_noise_band.csv")
WS = pd.read_csv(f"{D}/within_cell_spread.csv")


def forest_legend(name):
    return ci_forest.legend_md(FT[name])


def w2(d, m, st):
    r = get(W2, dataset=d, metric=m, stat=st)
    return f(r.est, r.lo, r.hi)


def ctab2(rating, levels, dsets=P3, metrics=METS):
    """As ctab, but 'within family' comes from the revised within-family check."""
    head = "| Metric | " + " | ".join(f"{SH[d]}: {lv} rho | {SH[d]}: {lv} r" for lv in levels for d in dsets) + " |"
    out = [head, "|---" * (1 + 2 * len(dsets) * len(levels)) + "|"]
    for m in metrics:
        cells = []
        for lv in levels:
            for d in dsets:
                for st in ["Spearman", "Pearson"]:
                    if lv == "within family":
                        cells.append(w2(d, m, st))
                    else:
                        r = get(C, dataset=d, level=lv, rating=rating, metric=m, stat=st)
                        cells.append(f(r.est, r.lo, r.hi))
        out.append(f"| {MLAB[m]} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


t = lambda d, lv, m, st, r="claude_temptation": get(C, dataset=d, level=lv, rating=r, metric=m, stat=st)
T = lambda *a, **k: f(*t(*a, **k)[["est", "lo", "hi"]])
g0, q1, q0 = P3
LG = lambda sub, m, st, d="gpt-oss-20b, thinking on": get(LS, dataset=d, subset=sub, metric=m, stat=st)
LF = lambda *a, **k: f(*LG(*a, **k)[["est", "lo", "hi"]])
nb = NB.set_index("dataset")
wsd = {r.dataset: r for r in WS.itertuples()}
ws_o = WS.iloc[0]; ws_q = WS[WS.dataset.str.contains("thinking on") & WS.dataset.str.startswith("Qwen")].iloc[0]

# ---------------- findings
A("## 1. Findings at a glance\n")
A(f"- **The observer's temptation rating predicts collusion and harm across designs on both models.** Cell level, price index: gpt-oss-20b rho {T(g0,'cell','price_index','Spearman')}, r {T(g0,'cell','price_index','Pearson')}; "
  f"Qwen3-32B thinking on rho {T(q1,'cell','price_index','Spearman')}; thinking off rho {T(q0,'cell','price_index','Spearman')}. "
  f"Harm index: gpt-oss r {T(g0,'cell','harm_index','Pearson')}, Qwen on r {T(q1,'cell','harm_index','Pearson')}. "
  "The harm index ranks games almost exactly like the price index (it is a concave function of the per-round price), so it adds a customer-side unit, not new information.")
A(f"- **At game level the association is about two thirds as strong** (gpt-oss price index rho {T(g0,'game','price_index','Spearman')}; Qwen on {T(q1,'game','price_index','Spearman')}; Qwen off {T(q0,'game','price_index','Spearman')}), "
  "with CIs that resample whole cells.")
A("- **On Qwen3-32B the rating tracks thinking-on games better than thinking-off ones** (cell price index rho +0.73 vs +0.44; inside the headline chat x penalty grid +0.90 vs +0.08). "
  "This is consistent with, though it does not by itself show, the separate penalty analysis (`results/ad-hoc-targeted-analysis/penalty/`), in which only thinking-on Qwen lowers prices as the fine rises: the observer rates a heavy fine as less tempting, and only the reasoning mode's prices follow.")
A(f"- **Within families, yes; within a cell, almost nothing (a low-variance test).** Excluding the control family and one-cell families, and recomputing the family means inside each bootstrap resample, the within-family price index correlation is "
  f"gpt-oss r {w2(g0,'price_index','Pearson')} / rho {w2(g0,'price_index','Spearman')}; Qwen on r {w2(q1,'price_index','Pearson')}; Qwen off r {w2(q0,'price_index','Pearson')} (not distinguishable from zero). "
  f"Competitive share within family: gpt-oss r {w2(g0,'competitive_share','Pearson')}, rho {w2(g0,'competitive_share','Spearman')}. "
  f"Inside one cell, where the rating varies only with the prompt's wording, the price index rho is {T(g0,'within cell','price_index','Spearman')} (gpt-oss), {T(q1,'within cell','price_index','Spearman')} (Qwen on) and {T(q0,'within cell','price_index','Spearman')} (Qwen off, small but above zero). "
  f"The within-cell test has little variance to work with: the rating's within-cell SD is {ws_o.within_cell_sd:.2f} on gpt-oss and {ws_q.within_cell_sd:.2f} on Qwen (against about 1.0 overall), and {int(ws_o.cells_constant_rating)} cells per model have a constant rating. "
  "The observer reads the design levers (chat, penalty, objective, primes); whether it can tell which paraphrase of a design will collude more is not established either way.")
A(f"- **Conflict predicts nothing.** Every cell- and game-level conflict CI includes zero on every model and metric (for example gpt-oss price index rho {T(g0,'cell','price_index','Spearman','claude_conflict')}).")
A(f"- **The gpt-oss competitive-share result: a stable Pearson-Spearman gap, and an association that rests on a few cells.** Temptation vs competitive share gives r {LF('all cells','competitive_share','Pearson')} and rho {LF('all cells','competitive_share','Spearman')}. "
  "The gap (r minus rho) stays at about -0.25 whatever cells are removed (-0.27 all cells, -0.25 without the controls, -0.24 also without m-inc-joint, -0.19 also without the no-chat cells). "
  f"It persists because the {int(nb.loc['gpt-oss-20b, thinking on','n_band'])} middle cells (competitive share 0.25 to 0.50) differ from each other by about as much as sampling noise (between-cell SD {nb.loc['gpt-oss-20b, thinking on','sd_between_cells_in_band']:.3f}, median within-cell SE {nb.loc['gpt-oss-20b, thinking on','median_cell_se_in_band']:.3f}): "
  "their ranks are noise, which Spearman weights fully, while Pearson draws on the six cells with real spread (the told-to-compete control at 0.99, the two no-chat headline cells, n3-ethics, d-conflict-ethics, d-cot-monitor-a). "
  "That partly supports the owner's point that the share is a weak measure on gpt-oss. But the association itself, under either statistic, rests on those few cells: without the controls, m-inc-joint and the no-chat cells it is r -0.26 [-0.65, +0.25], rho -0.07 [-0.50, +0.42]. "
  "Neither the tick-adjusted floor (r -0.69, rho -0.39) nor any threshold changes this; the strict-undercut part of the share has no relation to temptation (rho +0.02). "
  "Level-based measures (the share of quotes at or below 1.01, 1.02, 1.05 or 1.10) give rho -0.77 to -0.79 and r -0.70 to -0.73 with no gap, but they are largely the price level again (r -0.85 with the price index). On Qwen3-32B there is no gap (thinking on rho -0.76, r -0.69) and the association survives removing the controls.")
xp = get(XD, subset="all 24 shared cells", metric="price_index", stat="Spearman"); xpr = get(XD, subset="all 24 shared cells", metric="price_index", stat="Pearson")
A(f"- **Cross-model benchmark: not distinguishable.** On the 24 cells both models played, the observer's rating and Qwen3-32B's same-cell behaviour rank gpt-oss cells about equally well: observer minus Qwen, price index rho {f(xp['diff'], xp.lo, xp.hi)}, r {f(xpr['diff'], xpr.lo, xpr.hi)}; no metric's difference excludes zero with or without the controls (except matching share Pearson without controls, +0.18 [+0.01, +0.37]).")
A("- **Observer vs self-report.** The firms' temptation self-report co-varies with the observer's rating in direction on Qwen thinking on (rho +0.58 [+0.03, +0.81] across 10 prompt texts, which take only 4 distinct observer values); on gpt-oss +0.21 [-0.27, +0.65]. "
  "Within the temptation arms the gpt-oss self-report, written during play, co-varies with the game's own behaviour (price index rho +0.43 [+0.17, +0.63]; competitive share -0.61 [-0.74, -0.40]) where the observer's wording-level rating does not. "
  "Conflict: gpt-oss reports almost no conflict even under the ethics rule (self-report 1.04, observer 4.00).")
A("- **Status.** Exploratory: no pre-declared hypothesis and no multiplicity correction; correlations across designs are not causal (the rating summarises the lever that defines each arm).\n")

# ---------------- design
A("## 2. Design and data\n")
A("*What this section covers: which games, which ratings and which statistics lie behind every number below.*\n")
A("| Item | gpt-oss-20b | Qwen3-32B |\n|---|---|---|")
A("| Run | Final gpt-oss run, neutral payoff table, status done, hrep-* replicates excluded | Track M neutral run (primary) and anchored run (secondary), status done, smoke and 14B pilot arms excluded |")
A(f"| Games with a rating | {int(COV['oss_rated'])} of {int(COV['oss_done_games_excl_hrep'])} (unrated arms: {COV['oss_unrated_arms'].replace(';', ', ')}) | all 2,720 (neutral 1,360, anchored 1,360) |")
A("| Thinking | on only (reasoning effort medium) | off (660 games per run) and on (700 per run), analysed separately |")
A("| Cells | 31 (arm x communication x penalty point) | 35 thinking on, 33 thinking off, per run |")
A("| Harm index | from each round's market price in the run's round table (all games found; the mean price agrees with the run table to 5e-6) | from the round tables of both runs; 8 games in all (7 neutral, 1 anchored) are missing from the round tables and use their game-mean price instead |\n")
A("**Statistics.** Spearman and Pearson for every row. Cell level: one point per cell (mean rating, mean metric), 95% percentile bootstrap over cells (2,000 resamples). "
  "Game level: one point per game; 95% bootstrap resampling whole cells with all their games (1,000 resamples), because games of a cell share the design and most of the prompt. "
  "Within cell: each game's rating and metric minus its cell mean (the remaining rating variation comes from the five wordings only), same cell-cluster bootstrap. "
  "Within family: each cell's mean minus the mean of its arm family's cells, after excluding the control family (told to collude / told to compete) and families with a single cell; cells are resampled within each family and the family means are recomputed inside every resample (2,000). "
  "Exploratory throughout; no multiplicity correction. "
  "The game-level CIs here are wider than in the temptation screen, which resampled prompt texts rather than whole cells. The gpt-oss point estimates reproduce the screen (cell price index rho +0.79, r +0.85; game rho +0.55); the Qwen3-32B values differ slightly (cell rho +0.73 here vs +0.75) because the screen pooled the anchored and neutral runs. "
  "Note also that the screen described claude_conflict as how much the prompt 'pushes toward conflict or competition'; the rubric used by the raters, and this report, define it as how far the prompt's instructions contradict each other.\n")

# ---------------- section 3
A("## 3. Temptation rating vs collusion and harm, across designs\n")
A("*What this section compares: the observer's temptation rating of each prompt against each of the six outcome metrics, cell by cell and game by game, on the neutral payoff table, for gpt-oss-20b (thinking on) and Qwen3-32B (thinking on and off).*\n")
A("![Scatter of temptation rating against price, harm and competitive share](fig1_scatter_cells.png)\n")
A("**Figure 1.** One point per cell (arm x communication x penalty point), neutral payoff table. x = the observer's temptation rating of the cell's prompts (1 to 5, mean over the cell's games); "
  "y = the cell mean of the price index (top), the harm index (middle) and the competitive share (bottom). Columns: gpt-oss-20b thinking on (31 cells, 601 games), Qwen3-32B thinking on (35 cells, 700 games), Qwen3-32B thinking off (33 cells, 660 games). "
  "**Each column has its own y-range** (the x-axis is shared). Colour = arm family. Higher and to the right = a more tempting prompt and more collusive prices or more harm; the bottom row should fall from left to right. Source: `cell_means.csv`.\n")
A("<small>\n\n**Legend for Figure 1, by axis** (generated from the shared glossary `tools/analysis_style/arm_glossary.csv`)\n")
fams = sorted(CM[CM.dataset.isin(P3)].arm_family.unique())
A(AL.axis_legend(rows=["price_index", "harm_index", "competitive_share"], cols=["claude_temptation"], panels=["gpt-oss-20b", "Qwen3-32B", "t1", "t0", "neutral"],
                 row_name="metric (one row of panels each; y-axis)", col_name="observer rating (x-axis)", panel_name="model, thinking mode, payoff table (columns)"))
A("**Point colour: arm family**\n")
A(AL.legend_table(fams, long=True))
A("\n</small>\n")
n0 = nrow("game", g0); n1 = nrow("game", q1); n2 = nrow("game", q0)
A(f"**Table 1. Temptation rating vs each metric, cell level and game level** (neutral payoff table; cell n = 31 / 35 / 33 cells; game n = {n0[0]} / {n1[0]} / {n2[0]} games in {n0[1]} / {n1[1]} / {n2[1]} cells). Each entry: correlation [95% CI].\n")
A(ctab("claude_temptation", ["cell", "game"]))
A("<small>\n\n| Label | Precise definition |\n|---|---|")
A("| gpt-oss-20b, on | gpt-oss-20b, final run, neutral payoff table, thinking on, all rated arms (hrep-* excluded). |")
A("| Qwen3-32B, on / off | Qwen3-32B, Track M neutral run, thinking on / off, all arms except smoke and 14B pilots. |")
A("| cell | One design condition: arm x communication x penalty point (within one model and thinking mode); its value is the mean over its games (up to 20: 5 wordings x 4 seeds). |")
A("| game | One finished game (7 to 20 rounds); its rating is that of its own prompt text. |")
A("| rho / r | Spearman rank correlation / Pearson correlation. Cell-level CI = 2,000 bootstrap resamples of cells; game-level CI = 1,000 resamples of whole cells with their games. |")
A("| Metrics | As in the box at the top; harm index = mean per-round consumer-surplus loss over the loss at 3.00. Expected sign: positive, except competitive share (negative). |\n\n</small>\n")
A("![Forest chart of Table 1](fig2_forest_temptation.png)\n")
A("**Figure 2.** Forest chart of Table 1 (shared helper `ci_forest.py`). One panel per metric on the same -1 to +1 scale; one row per model, thinking mode, level (cell or game) and statistic (rho or r); dot = correlation, bar = 95% bootstrap CI, dashed line = zero. "
  "Red = the correlation points in the collusion direction (more temptation, more collusion: positive for price, profit, matching and harm, negative for competitive share), green = the competition direction; hollow = the CI crosses zero. Source: `correlations.csv`.\n")
A(forest_legend("fig2_forest_temptation.png"))
A("<small>\n\n**Rows (y-axis), codes:** gpt-oss-20b / Qwen3-32B = model; on / off = thinking mode; cell = correlation over cell means (cell = arm x communication x penalty point); game = correlation over individual games; rho = Spearman, r = Pearson.\n\n" + AL.legend_table(["gpt-oss-20b", "Qwen3-32B", "t1", "t0", "cell", "spearman_rho", "pearson", "claude_temptation"]) + "\n</small>\n")
A("**Reading.** All five collusion metrics and the harm index move with the temptation rating, in the expected direction, on both models; the thinking-off Qwen correlations are the weakest. "
  "Spearman and Pearson agree within about 0.1 except for gpt-oss competitive share (rho -0.38, r -0.65) and matching share (rho +0.53, r +0.69); section 6 examines the competitive-share gap.\n")

# ---------------- section 4
A("## 4. Conflict rating vs collusion and harm\n")
A("*What this section compares: the observer's conflict rating (how far the prompt's own instructions contradict each other) against the same six metrics, same data and statistics as section 3.*\n")
A("**Table 2. Conflict rating vs each metric, cell level and game level** (neutral payoff table; n as in Table 1). Each entry: correlation [95% CI].\n")
A(ctab("claude_conflict", ["cell", "game"]))
A("<small>\n\nLabels as in Table 1, with claude_conflict (observer conflict rating, 1 = consistent, 5 = directly contradictory) in place of temptation. No direction is expected a priori.\n\n</small>\n")
A("![Forest chart of Table 2](fig3_forest_conflict.png)\n")
A("**Figure 3.** Forest chart of Table 2, same layout, scale and colour rule as Figure 2. Source: `correlations.csv`.\n")
A(forest_legend("fig3_forest_conflict.png"))
A("<small>\n\n**Rows (y-axis), codes:** model, thinking mode, level (cell = over cell means, cell = arm x communication x penalty point; game = over individual games), statistic (rho = Spearman, r = Pearson). **Panels (x-axis):** the metric correlated with the conflict rating.\n\n" + AL.legend_table(["gpt-oss-20b", "Qwen3-32B", "t1", "t0", "cell", "spearman_rho", "pearson", "claude_conflict"]) + "\n</small>\n")
A("**Reading.** Every CI includes zero. Conflict rated 3.5 or more occurs in only a few arms (an ethics rule, the told-to-compete control, the reasoning-monitor notices), so the rating has little spread, and where it is high the arms go both ways.\n")

# ---------------- section 5
A("## 5. Within-design checks: does the rating predict collusion inside a design, not only across designs?\n")
A("*What this section compares: two stricter versions of the section 3 correlations. **Within cell**: each game's rating and metric minus its cell's mean, so only the five prompt wordings of one design vary. "
  "**Within family**: each cell's mean minus the mean of its arm family, so the comparison is between designs of the same family (for example penalty points and chat settings in the headline grid); the control family and one-cell families are excluded, and family means are recomputed in every bootstrap resample.*\n")
w2n = {d: get(W2, dataset=d, metric="price_index", stat="Spearman") for d in P3}
A(f"**Table 3. Temptation rating, within cell and within family** (neutral payoff table; within cell n = 601 / 700 / 660 games in 31 / 35 / 33 cells; within family n = {int(w2n[g0].n_cells)} / {int(w2n[q1].n_cells)} / {int(w2n[q0].n_cells)} cells in {int(w2n[g0].n_families)} / {int(w2n[q1].n_families)} / {int(w2n[q0].n_families)} families). Each entry: correlation [95% CI].\n")
A(ctab2("claude_temptation", ["within cell", "within family"]))
A("<small>\n\n| Label | Precise definition |\n|---|---|")
A("| within cell rho / r | Correlation of (game rating - cell mean rating) with (game metric - cell mean metric); CI = 1,000 resamples of whole cells. Tests whether the wording-level rating tracks wording-level behaviour. |")
A(f"| within family rho / r | Correlation of (cell mean - family mean) for rating and metric, families: gpt-oss {w2n[g0].families.replace(';', ', ')}; Qwen {w2n[q1].families.replace(';', ', ')}. Excluded: the control family and one-cell families (start_rule). CI = 2,000 resamples of cells within each family, family means recomputed in each. |\n\n</small>\n")
A("![Forest chart of Table 3](fig4_forest_within.png)\n")
A("**Figure 4.** Forest chart of Table 3 (same scale and colour rule as Figure 2; rows = model, thinking mode, level, statistic). Source: `correlations.csv` (within cell), `within_family_v2.csv` (within family).\n")
A(forest_legend("fig4_forest_within.png"))
A("<small>\n\n" + AL.legend_table(["within-cell", "within-family", "spearman_rho", "pearson", "gpt-oss-20b", "Qwen3-32B", "t1", "t0"]) + "\n</small>\n")
A(f"**Rating spread inside a cell.** gpt-oss: within-cell SD of the rating {ws_o.within_cell_sd:.2f} (overall {ws_o.total_sd:.2f}), {int(ws_o.cells_constant_rating)} of {int(ws_o.n_cells)} cells constant; Qwen thinking on: {ws_q.within_cell_sd:.2f} (overall {ws_q.total_sd:.2f}), {int(ws_q.cells_constant_rating)} of {int(ws_q.n_cells)} cells constant (`within_cell_spread.csv`). The within-cell test therefore has little rating variation to work with.\n")
A("**Table 3b. Conflict rating, within cell** (same data).\n")
A(ctab("claude_conflict", ["within cell"]))
A("![Forest chart of Table 3b](fig5_forest_within_conflict.png)\n")
A("**Figure 5.** Forest chart of Table 3b (same scale and colour rule as Figure 2). Source: `correlations.csv`.\n")
A(forest_legend("fig5_forest_within_conflict.png"))
A("<small>\n\n**Rows (y-axis):** model, thinking mode, level (within cell), statistic (rho = Spearman, r = Pearson). **Panels (x-axis):** the metric correlated with the conflict rating.\n\n" + AL.legend_table(["within-cell", "spearman_rho", "pearson", "gpt-oss-20b", "Qwen3-32B", "t1", "t0", "claude_conflict"]) + "\n</small>\n")
A("**Table 4. Temptation vs metric inside each arm family with at least 5 cells** (cell level). With 5 or 6 cells a bootstrap CI is unreliable, so the table gives the point estimate and a permutation p (exact over all orderings for up to 8 cells; 20,000 random orderings for the 12-cell headline family); the CIs are kept in the chart only, flagged as unreliable.\n")
A("| Model, mode | Arm family (arms) | Cells | Temptation range | Metric | Spearman rho (p) | Pearson r (p) |\n|---|---|---|---|---|---|---|")
ff = F[F.dataset.isin(P3) & F.metric.isin(["price_index", "competitive_share"])]
for (d, fam, m), g in ff.groupby(["dataset", "arm_family", "metric"], sort=False):
    sp = g[g.stat == "Spearman"].iloc[0]; pe = g[g.stat == "Pearson"].iloc[0]
    A(f"| {SH[d]} | {fam} ({sp.arms.replace(';', ', ')}) | {int(sp.n_cells)} | {sp.temptation_range} | {MLAB[m]} | {sp.est:+.2f} (p {sp.perm_p:.3f}) | {pe.est:+.2f} (p {pe.perm_p:.3f}) |")
A("\n![Forest chart of Table 4](fig6_forest_families.png)\n")
A("**Figure 6.** Forest chart of Table 4 (price index, competitive share and harm index panels; dot = correlation, bar = bootstrap 95% CI over the family's cells, **unreliable with 5 or 6 cells**; the printed p is the permutation p). Source: `within_family.csv`.\n")
A(forest_legend("fig6_forest_families.png"))
A("<small>\n\n" + AL.legend_table(["dset", "headline", "introspection", "gpt-oss-20b", "Qwen3-32B", "t1", "t0", "spearman_rho", "pearson"], long=True) + "\n</small>\n")
A("**Reading.** With the controls excluded, the observer still ranks designs inside families on gpt-oss and on Qwen thinking on (price index r about +0.74 to +0.81), but not on Qwen thinking off. "
  "In the headline chat x penalty grid the rating falls with the fine and without chat, and prices fall with it for the reasoning models (Qwen on rho +0.90, permutation p < 0.001; gpt-oss +0.80 over only 5 cells), but not for Qwen thinking off (+0.08). "
  "In the introspection family the rating hardly varies (3.53 to 4.00) and predicts nothing. Inside a cell the rating carries little or no information (|rho| 0.11 or less on every model; only Qwen thinking off has a CI excluding zero, +0.11 [+0.03, +0.18]), but the rating barely varies there, so this is a weak test, not a demonstrated null.\n")

# ---------------- section 6 leverage
A("## 6. Robustness: the gpt-oss Pearson-Spearman gap for competitive share, leverage cells, and the metric's definition\n")
A("*What this section asks: on gpt-oss-20b, temptation vs competitive share gives Spearman -0.38 but Pearson -0.65. Is the Pearson figure driven by a few cells, and does a different definition of the share change the gap? "
  "The owner raised the possibility, aware of the confirmation-bias risk, that Pearson may be the more valid statistic here because of measurement weaknesses in the competitive share: a one-tick undercut at a high price counts as competitive, and matching at 1.01 counts as non-competitive. "
  "We test (1) both statistics with and without the control arms and other leverage cells, (2) leave-one-cell-out Pearson and Cook's distance, (3) a noise check of the middle cells, and (4) seven definitions of the share recomputed from the firm-rounds, on both models.*\n")
A("| Definition | Rule (firm-round, round 2 on; target = lowest quote of the other firms in the previous round) |\n|---|---|")
A("| U16 as reported | Quote at least one tick below the target, or quote and target both at 1.00 (the run table's `competitive_share`; recomputed values match it, correlation 0.9999). |")
A("| U16, floor <= 1.01 | As U16, but holding at 1.01 or less against a target at 1.01 or less also counts (the tick-adjusted floor). |")
A("| strict undercut only | Quote at least one tick below the target; floor holds do not count. |")
A("| quotes <= 1.01 / 1.02 / 1.05 / 1.10 | Share of firm-rounds with a quote at or below that level: level-based measures of competitive pricing, blind to who undercuts whom. The thresholds are post hoc; four are shown to expose sensitivity. These are largely the price level again (cell-level r with the price index: gpt-oss -0.85, Qwen on -0.80, off -0.83 for 1.05). |\n")
A("**Table 5. Temptation vs competitive-share definitions, cell level, by subset of cells** (neutral payoff table; CI = 2,000 bootstrap resamples of cells).\n")
A("| Model, mode | Definition | Subset | Cells | Spearman rho | Pearson r | r minus rho |\n|---|---|---|---|---|---|---|")
DSH = {"gpt-oss-20b, thinking on": "gpt-oss-20b, on", "Qwen3-32B, thinking on": "Qwen3-32B, on", "Qwen3-32B, thinking off": "Qwen3-32B, off"}
DEF = {"competitive_share": "U16 as reported", "u16_floor101": "U16, floor <= 1.01", "strict_undercut": "strict undercut only", "q_le_101": "quotes <= 1.01",
       "q_le_102": "quotes <= 1.02", "near_floor_quote": "quotes <= 1.05", "q_le_110": "quotes <= 1.10"}
for d in DSH:
    for m in DEF:
        for sub in ["all cells", "without the two control arms", "without controls and m-inc-joint", "without controls and no-chat cells"]:
            sp = get(LS, dataset=d, metric=m, subset=sub, stat="Spearman"); pe = get(LS, dataset=d, metric=m, subset=sub, stat="Pearson")
            A(f"| {DSH[d]} | {DEF[m]} | {sub} | {int(sp.n_cells)} | {f(sp.est, sp.lo, sp.hi)} | {f(pe.est, pe.lo, pe.hi)} | {pe.est - sp.est:+.2f} |")
A("\n<small>\n\n| Label | Precise definition |\n|---|---|")
A("| the two control arms | ctl-32b-compete (told to quote exactly 1.00) and ctl-32b-joint (told to maximise joint profit), private chat, p3. |")
A("| m-inc-joint | The incentive arm with the same joint-profit instruction as ctl-32b-joint; removed in the third subset because it is the other instructed extreme. |")
A("| no-chat cells | headline-tacit cells (no chat), removed in the fourth subset with the controls, because tacit play produces undercut-and-climb rounds that score as competitive at high prices. |")
A("| r minus rho | Pearson minus Spearman; negative = Pearson shows the stronger negative association. |\n\n</small>\n")
A("![Forest chart of Table 5](fig10_forest_leverage.png)\n")
A("**Figure 10.** Forest chart of Table 5 for six of the seven definitions (quotes <= 1.02 is in the table only): panels = definition (same -1 to +1 scale), rows = model, subset of cells and statistic; dot = correlation, bar = 95% CI, dashed line = zero; red = more temptation goes with less competitive pricing (negative correlation), green = the reverse; hollow = CI crosses zero. Source: `leverage_subsets.csv`.\n")
A(forest_legend("fig10_forest_leverage.png"))
A("<small>\n\n**Rows (y-axis), codes:** no controls = without ctl-32b-compete and ctl-32b-joint; no m-inc-joint = also without m-inc-joint; no tacit cells = also without the headline-tacit cells.\n\n" + AL.legend_table(["ctl-32b-compete", "ctl-32b-joint", "m-inc-joint", "headline-tacit", "gpt-oss-20b", "Qwen3-32B", "t1", "t0", "spearman_rho", "pearson"]) + "\n</small>\n")
A("**Table 6. Leave-one-cell-out (LOO) correlations, all cells** (U16 as reported, and the price index for comparison).\n")
A("| Model, mode | Metric | Cells | Pearson r, all cells | LOO r min / median / max | Spearman rho, all cells | LOO rho min / max | Most influential cell (Cook's D) |\n|---|---|---|---|---|---|---|---|")
for _, r in LO.iterrows():
    A(f"| {DSH[r.dataset]} | {MLAB[r.metric]} | {int(r.n_cells)} | {r.pearson_full:+.2f} | {r.loo_pearson_min:+.2f} / {r.loo_pearson_median:+.2f} / {r.loo_pearson_max:+.2f} | {r.spearman_full:+.2f} | {r.loo_spearman_min:+.2f} / {r.loo_spearman_max:+.2f} | {r.most_influential_cell} ({r.max_cook:.2f}) |")
A("\n**Table 7. The three most influential cells for temptation vs competitive share** (Cook's distance of the straight-line fit of the cell mean on the rating; above about 4/n, here 0.11 to 0.13, is commonly read as influential).\n")
A("| Model, mode | Cell (arm, communication, penalty point) | Temptation | Competitive share | Cook's D | Leverage | Pearson r without it | Spearman rho without it |\n|---|---|---|---|---|---|---|---|")
for d in DSH:
    for _, r in CK[(CK.dataset == d) & (CK.metric == "competitive_share")].head(3).iterrows():
        A(f"| {DSH[d]} | {r.cell} | {r.temptation:.2f} | {r.value:.2f} | {r.cook_d:.2f} | {r.leverage:.2f} | {r.pearson_without_cell:+.2f} | {r.spearman_without_cell:+.2f} |")
A("\n**Table 7b. Noise check of the middle cells** (`leverage_noise_band.csv`).\n")
A("| Model, mode | Cells with competitive share 0.25 to 0.50 | SD between those cells | Median within-cell SE (those cells) | SD between all cells | Cells with competitive share 0.55 or more |\n|---|---|---|---|---|---|")
for _, r in NB.iterrows():
    sdb = "n/a" if pd.isna(r.sd_between_cells_in_band) else f"{r.sd_between_cells_in_band:.3f}"
    A(f"| {DSH[r.dataset]} | {int(r.n_band)} | {sdb} | {r.median_cell_se_in_band:.3f} | {r.sd_between_all_cells:.3f} | {str(r.cells_with_cs_ge_055).replace(';', '; ')} |")
A("\n<small>\n\nWithin-cell SE = the SD of the game-level competitive share in the cell divided by the square root of its number of games. When the between-cell SD is no larger than the typical SE, the cells' order is mostly sampling noise.\n\n</small>\n")
A("![Leave-one-cell-out Pearson against Cook's distance](fig11_loo_cook.png)\n")
A("**Figure 11.** Each point is one cell: x = its Cook's distance (influence on the fitted line of competitive share on temptation), y = the Pearson r with that cell left out; the dashed line is r with all cells. The three most influential cells are named (arm, communication, penalty point). Panels: gpt-oss-20b thinking on (31 cells), Qwen3-32B thinking on (35) and off (33). Source: `leverage_cells_*_competitive_share.csv`.\n")
A("<small>\n\n" + AL.axis_legend(rows=["pearson"], cols=["competitive_share"], panels=["gpt-oss-20b", "Qwen3-32B", "t1", "t0"], row_name="leave-one-out Pearson r (y-axis)",
                              col_name="Cook's distance of the cell for this metric (x-axis)", panel_name="model and thinking mode")
  + "**Named cells**\n\n" + AL.legend_table(["ctl-32b-compete", "moral-prime-b", "m-inc-joint", "headline-monitored", "headline-tacit", "private", "monitored", "tacit", "p1", "p3", "p4", "p5"]) + "\n</small>\n")
A("**What the robustness checks show.** (1) **The gap is stable, not a single-cell artefact.** On gpt-oss, r minus rho is -0.27 with all cells, -0.25 without the controls, -0.24 also without m-inc-joint and -0.19 also without the no-chat cells. "
  "The told-to-compete control is by far the most influential single cell (Cook's D 1.24, about ten times the usual threshold; LOO r -0.72 to -0.54), but removing it does not close the gap. "
  f"(2) **Why the gap persists.** The {int(nb.loc['gpt-oss-20b, thinking on','n_band'])} middle cells (competitive share 0.25 to 0.50) differ by about as much as their sampling noise (SD {nb.loc['gpt-oss-20b, thinking on','sd_between_cells_in_band']:.3f} against a median SE of {nb.loc['gpt-oss-20b, thinking on','median_cell_se_in_band']:.3f}), so their ranks are noise. Spearman gives that noisy band full weight; Pearson is carried by the six cells with real spread "
  "(ctl-32b-compete 0.99; headline-tacit p1 and p5 about 0.68; n3-ethics, d-conflict-ethics and d-cot-monitor-a about 0.55 to 0.60). In that sense Pearson is the better summary of a metric that is noisy in its middle range, which partly supports the owner's argument. "
  "(3) **But the association rests on those few cells under either statistic.** Without the controls, m-inc-joint and the no-chat cells neither is distinguishable from zero (r -0.26 [-0.65, +0.25], rho -0.07 [-0.50, +0.42]). "
  "(4) **The named measurement weaknesses do not create the gap.** The tick-adjusted floor changes almost nothing (r -0.69, rho -0.39), and the strict-undercut part of the share has no relation to temptation on gpt-oss (rho +0.02 [-0.42, +0.44]): what association there is comes from cells where both firms sit at 1.00. "
  "Level-based measures (quotes at or below 1.01 to 1.10) give rho -0.77 to -0.79 and r -0.70 to -0.73 at every threshold, with no gap and with or without the controls, but they mostly restate the price level (r -0.85 with the price index). "
  "On Qwen3-32B there is no gap to explain (thinking on rho -0.76, r -0.69) and both statistics survive removing the controls (rho -0.72, r -0.68).\n")

# ---------------- section 7 self-report
A("## 7. Observer rating vs the firms' self-report\n")
A("*What this section compares: in the D-set arms that ask each firm for a 1-to-5 score after every quote, the firm's own average score set beside the observer's rating of the same prompt and beside behaviour. "
  "Temptation arms: d-temptation-a and d-temptation-b (two wordings of the question, 40 games, 10 prompt texts per model and mode; the observer gives these 10 texts only 4 distinct values, 3.33 to 4.33). Conflict arms: d-conflict (no rule) and, on gpt-oss only, d-conflict-ethics (both firms also told 'do not coordinate prices with other firms'). "
  "The self-report is written during play, after each quote, so it is concurrent with behaviour, not a prediction of it.*\n")
A("**Table 8. Mean self-report, observer rating and behaviour per arm, gpt-oss-20b** (neutral payoff table; 20 games per row). The Qwen3-32B rows are in `results/ad-hoc-targeted-analysis/conflict-score-validation/` section 5.3 and are not repeated here (also in `self_report_means.csv`).\n")
A("| Arm | Self-report (mean) | Observer rating, same scale | Price index | Competitive share | Harm index |\n|---|---|---|---|---|---|")
for _, r in SM.iterrows():
    if not r.dataset.startswith("gpt-oss"):
        continue
    A(f"| {AL.label(r.arm)} | {r.self_report:.2f} | {r.claude:.2f} | {r.price_index:.2f} | {r.competitive_share:.2f} | {r.harm_index:.2f} |")
A("\n**Table 9. Correlations of self-report, observer rating and behaviour** (game level; pooled over the arms, and within arm = each game minus its arm's mean; CI = 1,000 bootstrap resamples of prompt texts). The Qwen3-32B conflict rows are omitted: its conflict self-report is 1.00 in nearly every round, so they are degenerate.\n")
A("| Scale | Model, mode | Pair | Pooled rho | Pooled r | Within-arm rho | Within-arm r | Games (prompts) |\n|---|---|---|---|---|---|---|---|")
pairs = ["self-report vs observer", "self-report vs price_index", "observer vs price_index", "self-report vs competitive_share", "observer vs competitive_share", "self-report vs harm_index", "observer vs harm_index"]
for kind in ["temptation", "conflict"]:
    for d in P3:
        if kind == "conflict" and d.startswith("Qwen"):
            continue
        for p in pairs:
            sub = S[(S.dataset == d) & (S.kind == kind) & (S.pair == p)]
            if sub.empty:
                continue
            g = lambda sc, st: sub[(sub.scope == sc) & (sub.stat == st)].iloc[0]
            a, b, c_, e = g("pooled arms", "Spearman"), g("pooled arms", "Pearson"), g("within arm", "Spearman"), g("within arm", "Pearson")
            A(f"| {kind} | {SH[d]} | {p.replace('_', ' ')} | {f(a.est, a.lo, a.hi)} | {f(b.est, b.lo, b.hi)} | {f(c_.est, c_.lo, c_.hi)} | {f(e.est, e.lo, e.hi)} | {int(a.n_games)} ({int(a.n_prompts)}) |")
A("\n<small>\n\n| Label | Precise definition |\n|---|---|")
A("| Self-report | The firm's own score (`score_mean`: mean over rounds and firms of the 1-to-5 answer), temptation_score in d-temptation-a/b, conflict_score in d-conflict and d-conflict-ethics. |")
A("| Observer | claude_temptation or claude_conflict of the game's prompt text (constant within a text; varies across the 5 wordings and between the arms). |")
A("| Pooled / within arm | Pooled: games of both arms together. Within arm: every variable minus its arm mean, so the arm difference cannot drive the correlation. |\n\n</small>\n")
A("![Forest chart of Table 9](fig7_forest_self_report.png)\n")
A("**Figure 7.** Forest chart of Table 9 (selected pairs; Qwen conflict omitted): panels = pair, rows = scale, model, scope and statistic; dot = correlation, bar = 95% CI, dashed line = zero; red / green = collusion / competition direction for pairs with a behaviour metric, blue-grey for self-report vs observer (no direction). Source: `self_report.csv`.\n")
A(forest_legend("fig7_forest_self_report.png"))
A("<small>\n\n" + AL.legend_table(["d-temptation-a", "d-temptation-b", "d-conflict", "d-conflict-ethics", "temptation_score", "conflict_score", "claude_temptation", "claude_conflict", "gpt-oss-20b", "Qwen3-32B", "t1", "t0"], long=True) + "\n</small>\n")
A("**Reading.** Temptation: the firms rate their own temptation lower than the observer does (2.2 to 2.9 vs 3.9 to 4.1) but co-vary with it in direction across prompt texts on Qwen thinking on; with only 4 distinct observer values over 10 texts this is a coarse comparison. "
  "Inside these two arms the gpt-oss self-report co-varies with the game's own behaviour (it is written during the game, after seeing the market) while the observer's wording-level rating does not; this is consistent with the weak within-cell test of section 5. "
  "Conflict: gpt-oss's own conflict score stays at about 1 whether or not the ethics rule is added (1.09 vs 1.04), while the observer moves from 1.53 to 4.00; the self-report does not register the conflict that the observer sees, and across the two arms the two even correlate negatively (rho -0.35 [-0.53, -0.07]).\n")

# ---------------- section 8 cross model
A("## 8. Benchmark: the observer versus running the other model\n")
A("*What this section compares: on the 24 cells (arm x communication x penalty point) that both models played on the neutral table with thinking on, how well two predictors rank gpt-oss-20b's cell means: the observer's temptation rating, and Qwen3-32B's own cell mean on the same metric. The test is the paired bootstrap difference (observer minus Qwen) of the two correlations, resampling the same cells for both.*\n")
A("**Table 10. Predicting gpt-oss-20b cell means: observer rating vs Qwen3-32B same-cell behaviour** (CI = 2,000 paired bootstrap resamples of cells). The observer's correlation is sign-aligned (multiplied by -1 for competitive share) so that a larger value always means a better predictor.\n")
A("| Subset | gpt-oss metric | Statistic | Observer | Qwen3-32B same cell | Observer minus Qwen [95% CI] |\n|---|---|---|---|---|---|")
for _, r in XD.iterrows():
    A(f"| {r.subset} ({int(r.n_cells)} cells) | {MLAB[r.metric]} | {r.stat} | {r.observer:+.2f} | {r.qwen:+.2f} | {f(r['diff'], r.lo, r.hi)} |")
A("\n![Forest chart of Table 10](fig8_forest_cross_model.png)\n")
A("**Figure 8.** Forest chart of the paired differences in Table 10: panels = gpt-oss metric, rows = subset and statistic; dot = observer minus Qwen, bar = 95% CI, dashed line = zero (equal predictive strength). The colour is the helper's metric-direction colour and carries no meaning for a difference in correlations; read only the position relative to zero. Source: `cross_model_diff.csv`.\n")
A(forest_legend("fig8_forest_cross_model.png"))
A("<small>\n\n" + AL.legend_table(["claude_temptation", "gpt-oss-20b", "Qwen3-32B", "t1", "spearman_rho", "pearson"]) + "\n</small>\n")
A("**Reading.** The prompt-only rating and the other model's behaviour are **not distinguishable** as predictors of gpt-oss designs: every difference's CI includes zero, with or without the controls, except matching share by Pearson without the controls (+0.18 [+0.01, +0.37]). The data do not show that one is better.\n")

# ---------------- section 9 anchored
A("## 9. Secondary check: the anchored payoff table (Qwen3-32B)\n")
A("*What this section compares: the same correlations on Qwen3-32B's anchored run, whose payoff table printed the theory price 2.09 (games 1,360; 35 cells thinking on, 33 off).*\n")
A("**Table 11. Temptation rating, anchored run** (price index, competitive share and harm index; each entry correlation [95% CI]; within family as revised in section 5).\n")
AN = ["Qwen3-32B, thinking on (anchored)", "Qwen3-32B, thinking off (anchored)"]
A(ctab("claude_temptation", ["cell", "game"], AN, ["price_index", "competitive_share", "harm_index"]))
A(ctab2("claude_temptation", ["within cell", "within family"], AN, ["price_index", "competitive_share", "harm_index"]))
A("![Forest chart of Table 11](fig9_forest_anchored.png)\n")
A("**Figure 9.** Forest chart of Table 11 (rows = mode, level and statistic; panels = metric; same scale and colour rule as Figure 2). Source: `correlations.csv`, `within_family_v2.csv`.\n")
A(forest_legend("fig9_forest_anchored.png"))
A("<small>\n\n" + AL.legend_table(["anchored", "Qwen3-32B", "t1", "t0", "within-cell", "within-family", "spearman_rho", "pearson"]) + "\n</small>\n")
A("**Reading.** The anchored run reproduces the neutral pattern: strong cell-level and within-family association with thinking on, weaker with thinking off, little within a cell.\n")

# ---------------- limits
A("## 10. Limits\n")
A("- The rating describes the prompt text, and across designs it summarises the lever that defines each arm; the cross-design correlations are not causal and say that the observer reads the levers in the right direction, not that its rating adds information beyond the design.")
A("- Within a cell the rating varies only with wording (SD about 0.25 to 0.33 on a 1-to-5 scale; 3 cells per model constant), so the within-cell result is a weak test; the within-cell price-index rho lies between -0.09 and +0.18 (the union of the 95% CIs) on every model and mode of the neutral run.")
A("- The formula and no-numbers arms, the strongest levers in the project, have no rating; a test of whether the observer would have predicted their low prices remains to be done (it needs new ratings, an LLM step not run here).")
A("- The observer is one model family (Claude), with three raters that may share blind spots; agreement is not validity.")
A("- The harm index uses the market (lowest) price per round; it ignores that customers who buy from the higher-priced firm pay more, so it understates the customer cost in rounds where the two quotes differ. It is not capped above 3.00 (1.33 at 5.00).")
A("- Exploratory throughout; no multiplicity correction. Cell-level CIs treat cells as independent although thinking-on and thinking-off cells of one arm share prompt texts.\n")
A("## Files\n")
A("`observer.py` (correlations, harm index, within-design checks, self-report, cross-model), `leverage.py` (section 6), `extra.py` (revised within-family check, permutation p, paired cross-model difference, within-cell spread), `figures.py`, `report.py` (this page). "
  "CSVs: `correlations.csv`, `cell_means.csv`, `within_family.csv`, `within_family_v2.csv`, `self_report.csv`, `self_report_means.csv`, `cross_model.csv`, `cross_model_diff.csv`, `leverage_subsets.csv`, `leverage_loo.csv`, `leverage_cook.csv`, `leverage_noise_band.csv`, `leverage_cells_*.csv`, `within_cell_spread.csv`, `coverage.csv`; `forest_tables.json` (the rows drawn in each forest chart). "
  "The raw run tables are not checked in; the scripts take their locations as arguments.\n")
A("*Created by Claude at the prompting of the repository owner.*\n")
open(f"{D}/ANALYSIS.md", "w", encoding="utf-8").write("\n".join(L))
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(f"{D}/ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("written", len(L))
