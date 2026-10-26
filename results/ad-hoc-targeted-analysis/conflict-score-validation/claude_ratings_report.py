#!/usr/bin/env python3
"""Writes section 5 of ANALYSIS.md (Claude's outcome-blind ratings versus collusion and versus the self-report) from the tables in
claude_ratings_out/ (made by claude_ratings.py), replacing the old placeholder section 5 in place. Regenerate ANALYSIS.html afterwards.
Usage: python -X utf8 claude_ratings_report.py"""
import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import arm_labels  # shared slug glossary (tools/analysis_style/arm_glossary.csv)
O = HERE / "claude_ratings_out"
MET = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
       ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
RAT = [("claude_conflict", "Claude-rated conflict"), ("claude_temptation", "Claude-rated temptation")]


def f(x, d=2):
    return "" if pd.isna(x) else ("%+.*f" % (d, x))


def ci(r):
    return "%s [%s, %s]" % (f(r.spearman), f(r.ci_lo), f(r.ci_hi))


g = pd.read_csv(O / "claude_game_spearman.csv")
c = pd.read_csv(O / "claude_cell_spearman.csv")
sa = pd.read_csv(O / "claude_vs_self_report_arms.csv")
sr = pd.read_csv(O / "claude_vs_self_report.csv")
et = pd.read_csv(O / "claude_ethics_arm.csv")
cells = pd.read_csv(O / "claude_cells.csv")
nall = g[(g.run == "both") & (g.thinking == "both") & (g.subset == "all games")].iloc[0]

L = []
a = L.append
MS = ["abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]


def legend(slugs, block=False):
    """Owner rule: a legend table under every figure and slug table, defining every slug or code shown (from the shared glossary)."""
    if block:
        a("<small>")
        a("")
    a("**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).")
    a("")
    a(arm_labels.legend_table(slugs).rstrip("\n"))
    a("")
    if block:
        a("</small>")
        a("")


AXHEAD = "**Legend: every code on each axis** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`)."


def axis_legend(extra=(), **kw):
    """Owner rule for figures: the legend defines every code on BOTH axes (rows, columns, panels), the plotted metric with its
    direction, and the legend series (extra = [(heading, slugs)])."""
    a(AXHEAD)
    a("")
    a(arm_labels.axis_legend(**kw).rstrip("\n"))
    for head, slugs in extra:
        a("")
        a("**%s**" % head)
        a("")
        a(arm_labels.legend_table(slugs).rstrip("\n"))
    a("")


SCATTER_NOTE = "not a colour map: point colour = thinking mode (blue = t0, orange = t1), marker = run (circle = anchored, square = neutral)"
SERIES = [("Series (point colour and marker): thinking mode and run", ["t0", "t1", "anchored", "neutral"])]


a("## 5. Claude's outcome-blind ratings of every prompt versus collusion, across all arms")
a("")
a("**What this section asks.** The sections above test the models' own conflict score in one pair of arms. Here the question is wider: across **every** arm and cell, does the amount of *conflict* and of *temptation* that an independent Claude panel finds in a prompt (rated from the prompt text alone, blind to arm names and results) go with how much the firms actually collude, and how do those external ratings compare with what the models say about themselves? Three Claude raters scored each distinct prompt text from 1 to 5 on two scales (rubric and procedure: `results/prompt-ratings/README.md`; inter-rater agreement: weighted kappa 0.82 conflict and 0.87 temptation).")
a("")
a("> **How to read this section**")
a("> - **Claude-rated conflict (1 to 5)**: how far the prompt's own instructions disagree with each other, e.g. a profit objective next to a rule against coordinating. 1 = consistent, 5 = directly contradictory. The mean of three raters; for cells where the two firms see different texts, the mean over the firms.")
a("> - **Claude-rated temptation (1 to 5)**: how far the prompt makes coordinating on high prices attractive, salient or easy (large joint gains, a chat channel, a light penalty, no oversight). 1 = no pull, 5 = very strong pull.")
a("> - **The five behaviour metrics**, each analysed separately, one value per game: **average absolute spread** = the mean best quote over rounds in raw half-spread units (1.00 competitive, 3.00 monopoly, up to 5.00); **price index** = (market price - 1)/2 averaged over rounds (0 competitive, 1 monopoly); **profit gain index** = (mean profit - competitive profit)/(monopoly profit - competitive profit); **competitive share (U16)** = share of firm-rounds in which a firm undercuts the lowest rival quote of the previous round, or both sit at 1.00 (higher = more competitive); **matching share** = share of firm-rounds in which the firm matches the lowest rival quote of the previous round above the floor (the coordination signature).")
a("> - **Spearman rank correlation** (rho): +1 = the ratings and the metric rise together, -1 = one rises as the other falls, 0 = no monotone relation. Because the average absolute spread is a straight-line rescaling of the price index, their rank correlations are identical by construction, and the profit gain index nearly so; they are listed separately as requested.")
a("> - **Cell** = one combination of run (anchored or neutral payoff-example table), arm, penalty point and thinking mode (off or on); a cell-level point is the mean of its games. **Thinking on/off** = whether the model reasons in a hidden chain of thought before replying. **Anchored / neutral** = whether the prompt's worked payoff examples print the theory price 2.09 or evenly spaced prices.")
a("> - **CI** = 95% percentile bootstrap that resamples whole prompt texts (games share a text, so they are not independent), 2,000 resamples; for cell-level correlations the cells are resampled. Exploratory throughout: no multiplicity correction and no pre-declared hypothesis.")
a("")
a("### 5.1 Game level: do the ratings track behaviour?")
a("")
a("Data: %d finished games from the anchored and neutral Track M runs (%d distinct prompt texts, every arm with a finished game, including the two-firm, three-firm and control arms pooled together; thinking on and off pooled). Unit of analysis: the game. Not paired. Exploratory." % (nall.n_games, nall.n_texts))
a("")
a("| Behaviour metric | Spearman with Claude-rated conflict [95% CI] | Spearman with Claude-rated temptation [95% CI] |")
a("|---|---|---|")
b = g[(g.run == "both") & (g.thinking == "both") & (g.subset == "all games")]
for m, ml in MET:
    r1 = b[(b.metric == m) & (b.rating == "claude_conflict")].iloc[0]
    r2 = b[(b.metric == m) & (b.rating == "claude_temptation")].iloc[0]
    a("| %s | %s | %s |" % (ml, ci(r1), ci(r2)))
a("")
a("*Caption.* Rank correlation between each game's metric (source: run.csv columns `market_price_mean`, `price_index`, `profit_gain_index`, `competitive_share`, `matching_share`) and the rating of that game's prompt (run.csv `claude_conflict`, `claude_temptation`). n = %d games (%d for the two shares, where one game has no value)." % (nall.n_games, nall.n_games - 1))
a("")
a("**Reading (associations across designs, not causal).** Claude-rated **temptation** goes with collusion: games whose prompts were rated more tempting have higher prices and profits and more matching, and fewer undercutting rounds (CIs exclude zero). Claude-rated **conflict** shows essentially no relation to behaviour across all arms (all CIs include zero). The two dials are not the same thing. Plausibly (not tested here) temptation follows the design levers that move prices (penalty point, chat channel; see the per-input and per-arm means in `results/prompt-ratings/README.md` and `ratings_by_arm.csv`), while conflict is rated 3.5 or higher only in the few arms that add a rule, a competition-only instruction or a monitored-reasoning notice, too few to move a pooled correlation.")
a("")
a("**By run and thinking mode (game level).** Spearman rho, same data split.")
a("")
a("| Run | Thinking | Rating | Avg spread | Price index | Profit gain | Competitive share | Matching share |")
a("|---|---|---|---|---|---|---|---|")
for run in ("anchored", "neutral"):
    for th in ("off", "on"):
        for rc, rl in RAT:
            x = g[(g.run == run) & (g.thinking == th) & (g.subset == "all games") & (g.rating == rc)].set_index("metric")
            a("| %s | %s | %s | %s |" % (run, th, rl.replace("Claude-rated ", ""), " | ".join(f(x.loc[m, "spearman"]) for m, _ in MET)))
a("")
a("**With the design levers held roughly fixed.** Chat arms only (private, monitored, public or unmonitored chat) and no-chat (tacit) games only, both runs and modes pooled:")
a("")
a("| Subset | Rating | Avg spread | Price index | Profit gain | Competitive share | Matching share | n games |")
a("|---|---|---|---|---|---|---|---|")
for sname in ("chat arms only", "tacit (no chat) only"):
    for rc, rl in RAT:
        x = g[(g.run == "both") & (g.thinking == "both") & (g.subset == sname) & (g.rating == rc)].set_index("metric")
        a("| %s | %s | %s | %d |" % (sname, rl.replace("Claude-rated ", ""), " | ".join(f(x.loc[m, "spearman"]) for m, _ in MET), x.iloc[0].n_games))
a("")
a("Within the chat arms, temptation keeps a positive relation with prices (rho about +0.3) and conflict is weakly related to the two shares (rho +0.21 with the competitive share and -0.13 [-0.21, -0.04] with the matching share): among chat games, prompts rated as having more internal conflict go with somewhat more undercutting. This is a design-level association confounded with arm, and the evidence is weak. Full table with CIs: `claude_ratings_out/claude_game_spearman.csv`.")
a("")
a("<small>")
a("")
a("**Terms for the game-level tables.**")
a("")
a("| Label | Precise definition |")
a("|---|---|")
a("| Game | One finished Track M game (run.csv row with status done, replaced reruns resolved), both firms or all three firms LLM-played, thinking off or on; the anchored run (prompt prints 2.09) and the neutral run (evenly spaced payoff examples) both included unless a row says otherwise. |")
a("| Rating of a game | The rating of that game's own prompt text (its wording, penalty point, communication, rules and notices), same for all seeds and both thinking modes. |")
a("| Chat arms / tacit | Chat arms: the firms may talk before quoting (private, monitored, public or stated-unmonitored chat). Tacit: no talking. |")
a("| Spearman [CI] | Rank correlation with the 95% prompt-text-clustered bootstrap interval in brackets. |")
a("| Standard metrics | As in the box above; the average absolute spread, price index and profit gain index are in the 'higher = more collusive' direction, competitive share in the opposite direction, matching share is the coordination signature. |")
a("")
legend(["anchored", "neutral", "t0", "t1", "tacit", "private", "monitored", "public", "unmonitored"] + MS)
a("</small>")
a("")
a("### 5.2 Cell level: scatter plots by thinking mode and run")
a("")
cb = c[(c.run == "both") & (c.thinking == "both")]
a("Unit of analysis: the cell (%d cells = run x arm x penalty point x thinking mode; each point is the mean of its 20 games, 5 wordings x 4 seeds). Cell-level Spearman, both runs and modes pooled:" % cb.n_cells.iloc[0])
a("")
a("| Behaviour metric | Conflict rho [95% CI] | Temptation rho [95% CI] |")
a("|---|---|---|")
for m, ml in MET:
    r1 = cb[(cb.metric == m) & (cb.rating == "claude_conflict")].iloc[0]
    r2 = cb[(cb.metric == m) & (cb.rating == "claude_temptation")].iloc[0]
    a("| %s | %s | %s |" % (ml, ci(r1), ci(r2)))
a("")
a("Cell-level correlations for temptation are stronger than at game level (matching share about +0.64, competitive share about -0.63) because averaging removes game-to-game noise. Conflict stays near zero. By thinking mode, the correlation of temptation with prices is stronger with thinking on (rho about +0.5 pooled, +0.7 to +0.8 within a run) than off (about +0.35 pooled, +0.4 to +0.5 within a run); this is an association across cells, not a mechanism. The cell CIs resample cells independently although the thinking-on and thinking-off cells of one arm share a prompt text, so they are somewhat too narrow. Table: `claude_ratings_out/claude_cell_spearman.csv`.")
a("")
for rc, rl in RAT:
    a("![%s versus the five behaviour metrics, per cell](claude_ratings_out/fig_%s_vs_metrics.png)" % (rl, rc))
    a("")
    a("*Figure. %s (horizontal axis, 1 to 5, cell mean) against each behaviour metric (vertical axis), one point per cell. Blue = thinking off, orange = thinking on; circle = anchored run, square = neutral run. Panel titles give the Spearman correlation over all cells. Source: `claude_ratings_out/claude_cells.csv`, built from run.csv. n = %d cells.*" % (rl, len(cells)))
    a("")
    a("<small>")
    a("")
    a("| Label | Precise definition |")
    a("|---|---|")
    a("| Horizontal axis | The mean, over the games of the cell, of the %s of each game's prompt (three raters, 1 to 5). |" % rl.lower())
    a("| Vertical axes | Cell means of: average absolute spread (raw half-spread units); price index (0 to 1); profit gain index; competitive share (U16); matching share. |")
    a("| Thinking off / on | Blue / orange: whether the model reasons before replying. |")
    a("| Anchored / neutral | Circle / square: anchored run (prompt prints 2.09) / neutral run (evenly spaced payoff examples). |")
    a("| Cell | One run x arm x penalty point x thinking mode; n games per cell shown in `claude_cells.csv`. Points are jittered horizontally by a small amount for visibility. |")
    a("")
    axis_legend(cols=[rc], col_name="%s of the cell's prompts (1 to 5, cell mean)" % rl, panels=MS,
                panel_name="behaviour metric on the y-axis of each panel (left to right)", metric=MS, colour=SCATTER_NOTE,
                extra=SERIES + [("Unit (one point)", ["cell"])])
    a("</small>")
    a("")
a("### 5.3 Claude-rated versus self-reported scores")
a("")
a("Only some arms ask the models for a score: the D-set arms `d-conflict` (self-reported conflict, 1 to 5, written after the quote) and `d-temptation-a` / `d-temptation-b` (self-reported temptation, 1 to 5; the two differ in the wording of the question). In the neutral and anchored runs, the Claude rating of the same prompt can be set beside the self-report of the games played under it.")
a("")
a("| Arm | Run | Thinking | Games | Self-reported score (mean) | Claude-rated, same scale (mean) | Avg spread | Price index | Profit gain | Competitive share | Matching share |")
a("|---|---|---|---|---|---|---|---|---|---|---|")
for _, r in sa.iterrows():
    a("| %s | %s | %s | %d | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f |" % (r.arm, r.run, r.thinking, r.n_games, r.self_score, r.claude_same_scale, r.market_price_mean, r.price_index,
                                                                                    r.profit_gain_index, r.competitive_share, r.matching_share))
a("")
legend(["d-conflict", "d-temptation-a", "d-temptation-b", "anchored", "neutral", "t0", "t1"] + MS, block=True)
a("The self-reported conflict is 1.00 in every `d-conflict` cell, where Claude rates the prompt 1.5 (low): the two agree in direction, though a constant 1.00 is also a floor effect. The self-reported temptation is between 2.2 and 2.7 while Claude's temptation rating of the same prompts is around 4: the rating of the text is higher than the models' own score. The two are differently worded 1-to-5 instruments and are not calibrated to each other, so only direction and ordering are comparable; the models' answers are the models' text, not evidence of an internal state.")
a("")
a("![Self-reported versus Claude-rated scores per arm, run and thinking mode](claude_ratings_out/fig_claude_vs_self.png)")
a("")
a("*Figure. Horizontal: Claude-rated conflict (left) or temptation (right) of the arm's prompts, mean of the three raters, 1 to 5. Vertical: the models' self-reported score on the same scale, mean over games. One point per arm x run x thinking mode (12 points). Source: `claude_ratings_out/claude_vs_self_report_arms.csv`.*")
a("")
a("<small>")
a("")
a("| Label | Precise definition |")
a("|---|---|")
a("| Self-reported score | Each firm's own integer 1 to 5 answer, written after the quote, plan and rationale, to a question asking how much conflict (`d-conflict`) or temptation (`d-temptation-a/b`) it perceives in its prompts; game value = mean over rounds and firms; 'no one will see this answer'. |")
a("| Claude-rated, same scale | Mean of the three raters' score of the arm's prompt texts on the same scale (conflict for the conflict question, temptation for the temptation questions); an arm has five prompt texts, one per wording. |")
a("| d-conflict | Neutral-set arm: private chat, penalty point 1, no extra rule; firms also report a conflict score. |")
a("| d-temptation-a / b | The same game; firms report a temptation score, two wordings of the question (a, b). |")
a("| Run, thinking, metrics | As in the box above. n games = 20 per row (5 wordings x 4 seeds). |")
a("")
axis_legend(rows=["conflict_score", "temptation_score"], row_name="models' self-reported score (left panel, right panel)",
            cols=["claude_conflict", "claude_temptation"], col_name="Claude rating of the arm's prompts, same scale (left panel, right panel)",
            extra=SERIES + [("Point labels: arm", ["d-conflict", "d-temptation-a", "d-temptation-b"])])
a("</small>")
a("")
a("**Within the D-set, game level** (the prompt text varies only by wording and run, so these correlations ask whether wordings rated as more tempting or conflicted draw different self-reports or behaviour; thinking modes pooled, 95% prompt-text-clustered bootstrap CI):")
a("")
a("| Score question | Games | Claude rating vs self-report | Claude rating vs avg spread / price index / profit gain | Claude rating vs competitive share | Claude rating vs matching share | Self-report vs avg spread / price index / profit gain | Self-report vs competitive share | Self-report vs matching share |")
a("|---|---|---|---|---|---|---|---|---|")
for sn in ("conflict_score", "temptation_score"):
    x = sr[(sr.score == sn) & (sr.thinking == "both")].set_index("metric")
    a("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
        sn, x.iloc[0].n_games,
        "%s [%s, %s]" % (f(x.loc["(self-report itself)", "claude_vs_metric"]), f(x.loc["(self-report itself)", "claude_lo"]), f(x.loc["(self-report itself)", "claude_hi"])),
        "%s [%s, %s]" % (f(x.loc["price_index", "claude_vs_metric"]), f(x.loc["price_index", "claude_lo"]), f(x.loc["price_index", "claude_hi"])),
        "%s [%s, %s]" % (f(x.loc["competitive_share", "claude_vs_metric"]), f(x.loc["competitive_share", "claude_lo"]), f(x.loc["competitive_share", "claude_hi"])),
        "%s [%s, %s]" % (f(x.loc["matching_share", "claude_vs_metric"]), f(x.loc["matching_share", "claude_lo"]), f(x.loc["matching_share", "claude_hi"])),
        "%s [%s, %s]" % (f(x.loc["price_index", "self_vs_metric"]), f(x.loc["price_index", "self_lo"]), f(x.loc["price_index", "self_hi"])),
        "%s [%s, %s]" % (f(x.loc["competitive_share", "self_vs_metric"]), f(x.loc["competitive_share", "self_lo"]), f(x.loc["competitive_share", "self_hi"])),
        "%s [%s, %s]" % (f(x.loc["matching_share", "self_vs_metric"]), f(x.loc["matching_share", "self_lo"]), f(x.loc["matching_share", "self_hi"]))))
a("")
legend(["conflict_score", "temptation_score", "d-conflict", "d-temptation-a", "d-temptation-b"] + MS, block=True)
a("Within the temptation arms, the prompt texts Claude rates as more tempting are also those whose self-reported temptation is higher (rho +0.49, CI excludes zero; 20 texts), whereas the self-reported temptation itself shows no relation to price (rho about 0.0) and a small negative one to matching share. For the conflict question the self-report is almost constant at 1.00 (mostly tied ranks, 10 texts), so its correlations and CIs, including -0.34 with matching share, rest on a handful of answers above 1 and are unstable; the rating-vs-self-report rho of +0.10 likewise rests on those few answers. Claude's rating of the prompt and the model's self-report agree on direction but neither explains the price level within one arm. The average absolute spread and profit gain index columns equal the price index column in rank terms (see the box). Full table: `claude_ratings_out/claude_vs_self_report.csv`.")
a("")
a("### 5.4 The ethics-rule arm: the clearest case of conflict")
a("")
a("The `d-conflict-ethics` arm adds to both firms 'Rule you must follow: do not coordinate prices with other firms. Set your quotes independently.' next to 'earn as much cumulative profit as you can'. Claude rates this as high conflict, and the models' own score hardly moves (wave-A run, neutral payoff table, private chat, penalty point 1; price index and competitive share from `game_level.csv`):")
a("")
a("| Arm | Thinking | Games | Claude-rated conflict | Claude-rated temptation | Self-reported conflict (mean) | Price index | Competitive share (U16) |")
a("|---|---|---|---|---|---|---|---|")
for _, r in et.iterrows():
    a("| %s | %s | %d | %.2f | %.2f | %.3f | %.3f | %.3f |" % (r.arm, "on" if str(r.thinking) in ("on", "1") else "off", r.n_games, r.claude_conflict, r.claude_temptation, r.self_conflict_score,
                                                                  r.price_index, r.competitive_share))
a("")
a("*Caption.* Arm means; Claude ratings are over the arm's five wordings (mean of three raters); the self-reported score is the per-game mean of the firms' 1 to 5 answers. The average absolute spread, profit gain index and matching share are in the section 'Standard metrics' below for the paired contrast (the wave-A games are not in run.csv).")
a("")
a("Claude's conflict rating of the rule prompt is high (4.0 against 1.5 for the plain arm) where the models' own conflict score barely moves (1.00 to 1.02 with thinking off, 1.19 with thinking on). The rule also changes Claude's temptation rating (3.93 for the plain arm, 2.93 with the rule), and the thinking-on price index in this table (0.861 against 0.741) is the arm mean over 20 and 16 games, not the paired estimate of section 2 (0.842 against 0.741 over 16 pairs, difference -0.101). Prices fall only with thinking on. This is consistent with the verdict that the self-reported conflict score is a low-sensitivity instrument; the external rating is higher for the rule prompt, which is one contrast and does not show it is a better instrument, nor does it measure what the model experiences.")
a("")
a("<small>")
a("")
a("| Label | Precise definition |")
a("|---|---|")
a("| d-conflict | Neutral-set arm: private chat, penalty point 1, firms report a conflict score; no rule. |")
a("| d-conflict-ethics | The same game with the rule above given to both firms. |")
a("| Games | 20 per row, except the thinking-on ethics row: 16 (4 games did not finish). |")
a("| Price index, competitive share | As in the box above. |")
a("")
legend(["d-conflict", "d-conflict-ethics", "t0", "t1", "p1", "private", "price_index", "competitive_share"])
a("</small>")
a("")
a("### 5.5 Limits")
a("")
a("- The ratings describe the first-round prompt text; the behaviour is the whole game. A rating is constant within a text, so its association with behaviour is at the level of designs, and is confounded with the lever that defines each arm (penalty point, chat channel, notices).")
a("- The panel is one model family and may share blind spots; the agreement among the three raters is high but is not validity. The ratings were made before they were compared with behaviour.")
a("- The self-report arms are a small corner of the design: 12 cells, 5 prompt texts per arm. The comparison with the self-report is suggestive only, and the conflict self-report is nearly constant.\n- Cell-level CIs resample cells independently although thinking-on and thinking-off cells of one arm share a prompt text, so they are somewhat too narrow.")
a("- Exploratory throughout; no pre-declared hypothesis, no multiplicity correction.")
a("- Files: `claude_ratings_out/` (all tables and figures), `claude_ratings.py` (analysis), `claude_ratings_report.py` (this section).")
a("")

sec = "\n".join(L) + "\n"
p = HERE / "ANALYSIS.md"
t = p.read_text(encoding="utf-8")
i = t.index("## 5. Claude's outcome-blind")
j = t.index("## Standard metrics")
p.write_text(t[:i] + sec + t[j:], encoding="utf-8", newline="\n")
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(p)
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("section 5 written, %d lines" % len(L))
