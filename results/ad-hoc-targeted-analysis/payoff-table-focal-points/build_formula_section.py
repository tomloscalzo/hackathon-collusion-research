"""Write formula_section.md (the main section 'Formula and no-numbers: collusion without printed prices') from the CSVs of
formula_no_numbers.py. build_md.py inserts it into ANALYSIS.md at the {{FORMULA_SECTION}} placeholder of analysis_template.md.
Run: python -X utf8 build_formula_section.py"""
import pandas as pd
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # shared glossary: every slug in a figure or table gets a legend row


def AXLEG(extra=(), **kw):
    """Figure legend grouped by axis (arm_labels.axis_legend), plus optional extra sections (title, codes)."""
    s = ("**Legend for the figure above, by axis** (generated from the shared glossary "
         "`tools/analysis_style/arm_glossary.csv`)\n\n" + arm_labels.axis_legend(**kw).rstrip("\n") + "\n")
    for title, codes in extra:
        s += "\n**" + title + "**\n\n" + arm_labels.legend_table(codes)
    return s.rstrip("\n") + "\n"


def LEG(slugs, what="table"):
    """Legend table (from tools/analysis_style/arm_glossary.csv) for the slugs a figure or table shows."""
    return ("**Legend for the " + what + " above: every slug and code it shows** (generated from the shared glossary "
            "`tools/analysis_style/arm_glossary.csv`)\n\n" + arm_labels.legend_table(slugs) + "\n")

M = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
     ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
D = pd.read_csv("formula_no_numbers_paired.csv"); V = pd.read_csv("formula_vs_none.csv"); Q = pd.read_csv("formula_no_numbers_quotes.csv")
T = pd.read_csv("formula_no_numbers_traces.csv"); S = pd.read_csv("formula_no_numbers_sensitivity.csv"); RG = pd.read_csv("formula_no_numbers_rerun_games.csv")
O = pd.read_csv("formula_no_numbers_paired_originals.csv")
NR = len(RG)


def cell(r, nd=2):
    star = "*" if r.p_holm < 0.05 else ""
    return f"{r['diff']:+.{nd}f} [{r.ci_low:+.{nd}f}, {r.ci_high:+.{nd}f}]{star}"


def get(df, metric, **eq):
    m = df.metric == metric
    for k, v in eq.items():
        m &= df[k] == v
    return df[m].iloc[0]


ARMTXT = {"fx-chat-p1": "formula, private chat, penalty point 1", "fx-tacit-p1": "formula, no chat, penalty point 1",
          "nx-chat-p1": "no numbers, private chat, penalty point 1", "nx-tacit-p1": "no numbers, no chat, penalty point 1",
          "fx-chat-p5": "formula, private chat, penalty point 5"}
out = []
w = out.append

# ---------------------------------------------------------------- headline numbers
def pi(arm, mode):
    return get(D, "price_index", arm=arm, mode=mode)

pis = D[D.metric == "price_index"]
lo_d, hi_d = pis["diff"].min(), pis["diff"].max()
w("## Formula and no-numbers: collusion without printed prices\n")
w("*What this section compares: games whose prompt prints no example prices (an exact profit formula only, or no payoff numbers at all) against the neutral control, which prints evenly spaced example prices, on all five collusion metrics, pair by pair.*\n")
w("**The game, in brief.** Two LLM \"market makers\" (Qwen3-32B) each quote a half-spread (the distance from the mid-price to the firm's bid and ask) from 1.00 to 5.00 in steps (\"ticks\") of 0.01. 1.00 is the competitive level (costs covered, no excess profit) and 3.00 is the monopoly price. 70% of customers go to the lowest quote, 30% are split evenly. A regulator investigates more often when prices are higher and fines both firms. Games last 7 to 20 rounds. "
  "**The question here:** the earlier comparison found that firms hold prices on numbers printed in the prompt (2.00, 2.50, 3.00 in the neutral run; 2.09 in the anchored run). If no example prices are printed at all, do they still collude? "
  "**The arms**, in words: *formula* (the prompt gives the exact profit rule as equations but no worked numbers) and *no numbers* (qualitative description only), each with private chat between the firms or with no chat (\"tacit\"), at penalty point 1 (a light fine, so collusion pays), with the model's hidden reasoning (\"thinking\") off or on; plus *formula, chat, penalty point 5* (a heavy fine, so collusion does not pay), thinking on only. "
  "**The data:** 180 games of one run (20 (wording, seed) pairs per cell; wording = which of five fixed rewordings of the instructions; seed = the random seed of the game), each paired with the neutral run's game of the same wording, seed, thinking mode and penalty point and the matching chat or tacit arm. The neutral run prints worked examples at 1.00, 1.50, ..., 4.00 and was run on the same model with the same wordings and seeds.\n")

w("### Terms for this section\n")
w("| Term | Definition |\n|---|---|\n"
  "| neutral control | The neutral run's headline arm with the same communication (private chat, or tacit = no chat) and the same penalty point and thinking mode. Its payoff section prints worked examples at 1.00, 1.50, ..., 4.00 (undercut example 2.49 against 2.50, investigation example at 2.00) and never 2.09. Truncation reruns of that run are included. 20 games per cell. |\n"
  "| formula arm (fx) | Same prompt as the control except the payoff section gives the exact profit rule as equations (demand Q(b) = 100 * (1 - b/5.00); 30% of customers split evenly, 70% to the lowest quote; profit per unit = quote - 1.00; investigation probability and fine) and no worked numbers. |\n"
  "| no-numbers arm (nx) | Same prompt with no examples and no formulas; the rules are described in words only. |\n"
  "| chat / tacit | Private chat between the two firms before each round / no chat; the firms see only each other's quotes. |\n"
  "| penalty point 1 / 5 | How heavy the regulator's fine is: at 1 collusion clearly pays (theory's sustainable collusive level 0.703 of the way from 1.00 to 3.00); at 5 it does not (0). |\n"
  "| thinking on / off | Whether the model reasons in a hidden chain of thought before replying. |\n"
  "| pair | One (wording, seed) combination in the arm and in its control; every difference is within a pair. |\n"
  "| truncation rerun | A rerun of a thinking-on game in which a model reply hit its token cap, replacing the truncated game. |\n")

w("> **How to read the five metrics** (each analysed separately, one value per game, then averaged over the 20 pairs)\n"
  "> - **Average absolute spread** = mean market quote over the rounds, in raw half-spread units (1.00 to 5.00). Higher = more collusive. Example: all rounds at 1.50 give 1.50.\n"
  "> - **Price index** = (market price - 1) / 2, averaged over rounds: 0 = competitive 1.00, 1 = monopoly 3.00. A market price of 1.50 gives 0.25. Higher = more collusive.\n"
  "> - **Profit gain index** = (mean firm profit per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit. Higher = more collusive.\n"
  "> - **Competitive share (U16)** = share of firm-rounds (round 2 on) in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00. Higher = more competitive.\n"
  "> - **Matching share** = share of firm-rounds in which the firm's quote equals the lowest rival quote of the previous round (within half a tick), above 1.00: the coordination signature. Higher = more coordination.\n"
  "> Unit: game (one value per game; competitive and matching share are pooled over the game's firm-rounds). Source: the per-game code of the repository's Step 1 table builder (`run.csv` columns `market_price_mean`, `price_index`, `profit_gain_index`, `competitive_share`, `matching_share`).\n")

# ---------------------------------------------------------------- verdict
w("### Verdict\n")
cp = get(D, "price_index", arm="fx-chat-p1", mode="on"); nxc = get(D, "price_index", arm="nx-chat-p1", mode="on")
w(f"**Without printed example prices, collusion largely disappears.** At penalty point 1 the price index falls from 0.47-0.85 in the controls to {pis[pis.arm != 'fx-chat-p5']['arm_mean'].min():.2f}-{pis[pis.arm != 'fx-chat-p5']['arm_mean'].max():.2f}, and the paired price-index difference is between {pis[pis.arm != 'fx-chat-p5']['diff'].max():+.2f} and {pis[pis.arm != 'fx-chat-p5']['diff'].min():+.2f} in all eight penalty-1 cells; every 95% interval lies far below zero. The average absolute spread falls from 1.9-2.7 to 1.0-1.7 and the profit gain index from 0.70-0.95 to 0.01-0.54, the same way in every cell.\n")
w("- **The five metrics, separately.** Spread, price index and profit gain index agree in every cell: lower than the control (paired differences in the first table, Holm-significant in all 9). Competitive share is higher in the thinking-off cells (+0.09 to +0.35; the interval excludes zero for formula + chat and formula + tacit) and in the penalty-5 cell (+0.47), and lower or unchanged with thinking on (-0.23 to 0.00; only no-numbers + tacit excludes zero): with thinking off the firms undercut to the floor, with thinking on undercutting is rare in both arm and control. Matching share is lower in 6 of the 9 cells (the interval excludes zero in 4) and not distinguishable from the control in the other 3, among them formula + chat + thinking on (+0.01), where the firms still match each other at 1.50 and just match at a low price.\n"
  f"- **Where the quotes cluster.** The controls sit on the printed examples (2.50 in 59% and 3.00 in 36% of thinking-on chat quotes). The formula and no-numbers arms put most quotes at 1.00-1.25. The one cell with a high held price is formula + chat + thinking on: quotes at 1.50 ({Q[(Q.arm=='fx-chat-p1')&(Q['mode']=='on')&(~Q.is_control)].iloc[0]['top_quotes'].split(';')[0]}) and 2.00, numbers the firms proposed to each other in the chat, not printed ones.\n"
  f"- **Formula versus none.** The exact profit rule matters only where the firms can talk and reason: formula + chat + thinking on has a price index {get(V,'price_index',comm='chat',mode='on',contrast='fx-chat-p1 minus nx-chat-p1')['diff']:+.2f} [{get(V,'price_index',comm='chat',mode='on',contrast='fx-chat-p1 minus nx-chat-p1').ci_low:+.2f}, {get(V,'price_index',comm='chat',mode='on',contrast='fx-chat-p1 minus nx-chat-p1').ci_high:+.2f}] above no-numbers chat. Elsewhere the formula adds at most a few hundredths (thinking-off cells: between -0.07 and 0.00).\n"
  f"- **Penalty point 5.** With the formula, chat and thinking on, the heavy fine cuts the price index to {pi('fx-chat-p5','on').arm_mean:.2f} (neutral control at the same fine: {pi('fx-chat-p5','on').control_mean:.2f}); quotes are at 1.00 in 67% of cases. Against the same formula arm at penalty point 1 the price index is {get(V,'price_index',contrast='fx-chat-p5 minus fx-chat-p1')['diff']:+.2f} [{get(V,'price_index',contrast='fx-chat-p5 minus fx-chat-p1').ci_low:+.2f}, {get(V,'price_index',contrast='fx-chat-p5 minus fx-chat-p1').ci_high:+.2f}]: the firms respond to the deterrent.\n"
  f"- **Reasoning traces show the formula being used.** In the formula arms, {T.iloc[0]['share_computes_with_formula']:.0%} (chat) and {T.iloc[1]['share_computes_with_formula']:.0%} (tacit) of thinking-on passages evaluate the printed demand formula with numbers; in the no-numbers arms and the neutral controls it is 0.0-0.7% (a keyword count, unvalidated).\n"
  f"- **Truncation sensitivity.** {NR} thinking-on games (the earlier summary said 10; a recount finds 9) had a call cut at the token limit and were rerun on the 32k-token profile; none of the reruns truncated. Every number in this section uses the reruns in place of the originals. With the originals instead, no price-index difference moves by more than 0.02 and no conclusion changes (last table).\n")
w("**Caveats.** Part of the drop with thinking off is plain competitive pricing (quotes at 1.00 to 1.05), not weaker coordination; the control is the neutral run, not an anchored run; each cell has 20 games; the penalty-5 comparison is within a single arm and the cells are exploratory, not pre-declared.\n")

# ---------------------------------------------------------------- table 1
w("### Table A. All five metrics: arm minus neutral control, paired\n")
w("*What this compares: for each arm and thinking mode, the difference (arm minus control) in each metric, over the 20 pairs. Each cell: mean paired difference [95% bootstrap CI]; an asterisk marks Holm-adjusted exact sign-flip p < 0.05. Negative = lower than the control.*\n")
rows = ["| arm (in words) | thinking | control | " + " | ".join(n for _, n in M) + " |", "|---|---|---|" + "---|" * 5]
for arm in ["fx-chat-p1", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1", "fx-chat-p5"]:
    for mode in ["off", "on"]:
        sub = D[(D.arm == arm) & (D["mode"] == mode)]
        if sub.empty:
            continue
        ctl = sub.iloc[0].control
        rows.append(f"| {arm}: {ARMTXT[arm]} | {mode} | neutral {ctl} | " + " | ".join(cell(get(sub, c)) for c, _ in M) + " |")
w("\n".join(rows) + "\n")
w("<small>\n\n**Terms for Table A.** Each cell is arm minus control, in the metric's own units (spread in half-spread units 1.00-5.00; the other four on 0-1). Arm = the arm named in the first column (fx = formula, nx = no numbers; chat = private chat, tacit = no chat; p1/p5 = penalty point), thinking = thinking off/on; control = the neutral run's headline-chat or headline-tacit arm at the same penalty point and thinking mode (payoff table printing 1.00, 1.50, ..., 4.00). n = 20 games per arm and 20 per control, 20 pairs per row. CI = 95% percentile bootstrap over the 20 pairs (10,000 resamples). Test = exact sign-flip permutation test over the 20 pairs, two-sided; multiplicity = Holm within each metric across the 9 rows (family of 9). Exploratory (the arms are not part of the pre-declared contrasts). Source: `formula_no_numbers_paired.csv` (arm and control means, p-values, Holm-adjusted p).\n\n" + LEG(['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'headline-chat', 'headline-tacit', 'neutral', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5', 't0', 't1', 'pair', 'abs_spread', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share'], 'table') + "</small>\n")

w("### Figure 1. Mean of each metric in each cell, control and arm side by side\n")
w("![Heat map of the five metrics, control and arm](fig_formula_heatmap.png)\n")
w("**Caption.** What is measured: the mean over games of each of the five metrics, for each arm (bold rows) and its neutral control (plain rows above it), thinking mode as labelled. How derived: per-game values from the Step 1 per-game code, averaged over the 20 games of the cell; the control rows are the 20 games of the control cell (the same 20 (wording, seed) pairs). Colour: green = competitive, red = collusive; for competitive share high is green, for the other four high is red. n = 20 games per row.\n")
w("<small>\n\n**Terms for Figure 1.** Rows: \"neutral control for X (thinking on/off)\" = neutral run, the headline arm with X's communication and penalty point, at that thinking mode; \"X (thinking on/off)\" = the formula or no-numbers arm X. Columns = the five metrics defined in the box above; the colour scale runs per column from its competitive end (spread 1.00, price index 0, profit gain index 0, competitive share 1, matching share 0) to its collusive end (spread 3.00, 1, 1, competitive share 0, matching share 1). Run: formula/no-numbers run and neutral run, Qwen3-32B, 2 firms.\n\n" + AXLEG(rows=['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'headline-chat', 'headline-tacit', 't0', 't1'], row_name='cell: formula / no-numbers arm and its neutral control, by thinking mode', cols=['abs_spread', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share'], col_name='metric', metric=['abs_spread', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share'], colour='each column has its own fixed scale (average absolute spread 1.00 to 3.00, the other four 0 to 1) on a green-yellow-red map: red = collusive, green = competitive; competitive share is reversed (high = green)', extra=[('Other codes (run, payoff table, communication, penalty point)', ['neutral', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5'])]) + "</small>\n")

# ---------------------------------------------------------------- quotes
w("### Table B and Figure 2. Where the quotes cluster\n")
w("*What this compares: the distribution of all firm quotes (half-spreads) in each arm and in its neutral control. Quotes are market-maker quotes in all rounds; imputed quotes (replacement values for failed replies) are removed from the control but there are none in the arm.*\n")
w("![Quote distributions](fig_formula_quotes.png)\n")
w("**Caption.** What is measured: the share of all firm quotes falling in each quote range, per cell (bars sum to 100%). Derived from the market events of each game (the two firms' quotes every round). Green = low (competitive) quotes, red = high. n = 20 games per bar (about 300-700 quotes per bar).\n")
rows = ["| cell | who | mean quote | most common quotes (share of all quotes) | at 1.00 | 1.01-1.25 | 1.26-1.50 | 1.51-2.00 | 2.01-3.00 |", "|---|---|---|---|---|---|---|---|---|"]
for _, r in Q.iterrows():
    rows.append(f"| {r.arm}, thinking {r['mode']} | {'neutral control' if r.is_control else 'arm'} | {r.mean_quote:.2f} | {r.top_quotes} | {r['share_1.00']:.2f} | {r['share_1.01-1.25']:.2f} | {r['share_1.26-1.50']:.2f} | {r['share_1.51-2.00']:.2f} | {r['share_2.01-3.00']:.2f} |")
w("\n".join(rows) + "\n")
w("<small>\n\n**Terms for Table B and Figure 2.** cell = arm (code as in Table A) and thinking mode; who = the formula/no-numbers arm, or the neutral control cell with the same communication, penalty point and thinking mode; mean quote = mean over all quotes of the two firms in 20 games, raw half-spread units; most common quotes = the four most frequent exact values with their share of all quotes in the cell; the five range columns = share of quotes in that range (the quote 1.00 is the competitive floor, 3.00 the monopoly price). Source: `formula_no_numbers_quotes.csv`. Descriptive; no test.\n\n" + AXLEG(rows=['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'headline-chat', 'headline-tacit', 't0', 't1'], row_name='cell: formula / no-numbers arm and its neutral control, by thinking mode (Figure 2 bars, Table B rows)', metric='quote_range_share', colour='six quote ranges from 1.00 (dark green) through 1.01-1.25, 1.26-1.50, 1.51-2.00, 2.01-3.00 to above 3.00 (red); greener = lower, more competitive quotes; the x-axis is the share of all firm quotes in the cell', extra=[('Other codes (run, payoff table, communication, penalty point)', ['neutral', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5'])]).replace('for the figure above, by axis', 'for the figure and table above, by axis') + "</small>\n")

# ---------------------------------------------------------------- formula vs none and p5
w("### Table C. Formula versus no numbers, and penalty point 5 versus 1\n")
w("*What this compares: within each communication and thinking cell, the formula arm minus the no-numbers arm (the effect of printing the exact profit rule), and the formula + chat arm at penalty point 5 minus the same arm at penalty point 1 (the effect of a heavy fine), over the 20 (wording, seed) pairs. Cells: mean paired difference [95% bootstrap CI]; an asterisk marks Holm-adjusted p < 0.05 within each metric across these 5 contrasts.*\n")
rows = ["| contrast | thinking | " + " | ".join(n for _, n in M) + " |", "|---|---|" + "---|" * 5]
for (c, m) in [("fx-chat-p1 minus nx-chat-p1", "off"), ("fx-chat-p1 minus nx-chat-p1", "on"), ("fx-tacit-p1 minus nx-tacit-p1", "off"), ("fx-tacit-p1 minus nx-tacit-p1", "on"), ("fx-chat-p5 minus fx-chat-p1", "on")]:
    sub = V[(V.contrast == c) & (V["mode"] == m)]
    rows.append(f"| {c} | {m} | " + " | ".join(cell(get(sub, k)) for k, _ in M) + " |")
w("\n".join(rows) + "\n")
w("<small>\n\n**Terms for Table C.** fx = formula arm, nx = no-numbers arm, chat = private chat, tacit = no chat, p1/p5 = penalty point 1 (light fine) / 5 (heavy fine); \"A minus B\" = for each (wording, seed) pair the metric in A minus the metric in B, averaged over 20 pairs (thinking mode as in the column). Same run and prompts as Table A. CI and test as in Table A; family = the 5 rows, per metric. The penalty comparison is between two arms of the same run with the same 20 pairs; it is exploratory because no matching arm with printed examples exists at both penalty points on the same footing. Source: `formula_vs_none.csv`.\n\n" + LEG(['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5', 't0', 't1', 'pair', 'abs_spread', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share'], 'table') + "</small>\n")

# ---------------------------------------------------------------- traces
w("### Table D. Do the reasoning traces use the formula? (thinking-on games, keyword count, unvalidated)\n")
w("*What this compares: the share of reasoning passages (the model's hidden reasoning before each quote, and before each chat message) in thinking-on games that match each keyword pattern, in the formula arms, the no-numbers arms and the neutral controls.*\n")
rows = ["| group | games | passages | evaluates the demand formula with numbers | mentions the demand formula | 30% / 70% flow split | profit per unit (quote - 1.00) | investigation probability |", "|---|---|---|---|---|---|---|---|"]
for _, r in T.iterrows():
    rows.append(f"| {r.group} | {r.n_games} | {r.n_passages} | {r.share_computes_with_formula:.1%} | {r['share_demand formula']:.1%} | {r['share_30/70 flow split']:.1%} | {r['share_profit per unit (quote minus 1.00)']:.1%} | {r['share_investigation probability']:.1%} |")
w("\n".join(rows) + "\n")
w("<small>\n\n**Terms for Table D.** passage = one reasoning text of one call (quote call or chat-message call) of a thinking-on game; games = the 20 games of the cell. mentions the demand formula = the passage matches `Q(` or `100 * (1 -` (the printed demand curve Q(b) = 100 * (1 - b/5.00)); evaluates it with numbers = it matches the same pattern and also contains an equals or approximately-equals sign followed by a number; 30%/70% flow split = the passage contains both a 70% (or 0.7) and a 30% (or 0.3); profit per unit = a (quote - 1) times pattern or the words \"profit per unit\"; investigation probability = the word \"investigat\" followed within 80 characters by a decimal or percentage. These are regular-expression keyword counts that were not validated against human or model labels, so they show that the formula appears in the reasoning, not that it caused the low prices. The neutral controls print worked examples (not the formula), so near-zero demand-formula use there is expected. The traces are those of the games as originally played (the nine rerun games were not re-collected). Source: `formula_no_numbers_traces.csv`.\n\n" + LEG(['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'headline-chat', 'headline-tacit', 'neutral', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5', 't1'], 'table') + "</small>\n")

# ---------------------------------------------------------------- sensitivity
w("### Table E. Truncation sensitivity: results with the original games versus with the reruns\n")
w(f"*What this compares: the arm-minus-control differences computed twice, once with all 180 games as originally played and once with the {NR} games that had a call cut at the token limit replaced by their reruns (32k-token profile, larger caps, 720-second timeout). Only thinking-on cells are affected.*\n")
rows = ["| arm | thinking | games rerun | price index: originals | price index: with reruns | spread: originals | spread: with reruns | competitive share: originals | competitive share: with reruns | matching share: originals | matching share: with reruns |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for arm in ["fx-chat-p1", "fx-tacit-p1", "nx-chat-p1", "nx-tacit-p1", "fx-chat-p5"]:
    sub = S[(S.arm == arm) & (S["mode"] == "on")]
    if sub.empty:
        continue
    def c2(metric):
        r = get(sub, metric)
        return f"{r.diff_orig:+.3f} [{r.ci_low_orig:+.2f}, {r.ci_high_orig:+.2f}]", f"{r.diff_rerun:+.3f} [{r.ci_low_rerun:+.2f}, {r.ci_high_rerun:+.2f}]"
    a, b, c, d, e, f, g, h = (*c2("price_index"), *c2("market_price_mean"), *c2("competitive_share"), *c2("matching_share"))
    rows.append(f"| {arm} | on | {int(sub.iloc[0].n_games_rerun_here)} | {a} | {b} | {c} | {d} | {e} | {f} | {g} | {h} |")
w("\n".join(rows) + "\n")
w("<small>\n\n**Terms for Table E.** Each cell is the paired difference arm minus neutral control (as in Table A) with its 95% bootstrap CI, computed with the arm's games as originally played (\"originals\") or with each truncated original replaced by its rerun (\"with reruns\"; the rerun has the same arm, wording, seed and thinking mode, a 32,768-token context, caps of 28,672 tokens for quote and chat calls and 16,384 for questions). games rerun = number of the arm's 20 thinking-on games replaced. The controls already contain their own truncation reruns. Per-game before and after values: `formula_no_numbers_rerun_games.csv`; all five metrics for both versions: `formula_no_numbers_sensitivity.csv`.\n\n" + LEG(['fx-chat-p1', 'fx-tacit-p1', 'nx-chat-p1', 'nx-tacit-p1', 'fx-chat-p5', 'headline-chat', 'headline-tacit', 'neutral', 'formula', 'none', 'chat', 'tacit', 'p1', 'p5', 't1', 'pair', 'price_index', 'abs_spread', 'competitive_share', 'matching_share'], 'table') + "</small>\n")
w("Rerun this section: `python -X utf8 formula_no_numbers.py --formula-root <formula run> --rerun-root <32k rerun root> --neutral-run <neutral step1 run.csv> --neutral-tables <collect.py tables of the neutral run> --formula-tables <collect.py tables of the formula run> --out .` then `python -X utf8 build_formula_section.py` then `python -X utf8 build_md.py`.\n")
open("formula_section.md", "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("ok")
