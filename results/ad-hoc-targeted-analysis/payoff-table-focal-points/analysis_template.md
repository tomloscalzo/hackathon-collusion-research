# Payoff-table focal points: do firms copy the numbers printed in the prompt?

Neutral run (printed examples 1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50, 4.00) against the anchored run (printed examples 1.00, 1.54, 2.08, 2.09, 3.00). Qwen3-32B, 2 firms, 20 (wording, seed) pairs per cell, DONE games only (1,360 per run). Script: `focal_points.py`; page builder `build_md.py`; CSVs in this folder.

> **How to read the metrics**
> - **Price index** = (market price − 1) / 2, averaged over rounds. 0 = competitive (price 1.00), 1 = monopoly (price 3.00).
> - **Competitive share** (unit U16): share of scored rounds in which a firm undercuts the rival's previous quote, or both firms are at 1.00. Higher = more competitive.
> - **Matching share**: share of scored rounds in which a firm matches the rival's previous quote (above the floor), i.e. follows rather than undercuts. Reported in the Standard metrics section.
> - **Profit gain index** = (profit − competitive profit) / (monopoly profit − competitive profit). 0 = competitive profit, 1 = monopoly (joint-profit) level.
> - **t0 / t1** = thinking off / on (the model's reasoning mode).
> - **p1 / p3 / p4 / p5** = penalty points (1 = collusion clearly pays, 5 = clearly does not); theory's sustainable collusive level θ* = 0.703 / 0.546 / 0.325 / 0.
> - **tacit / chat / monitored** = no chat channel / private chat between the two firms / private chat plus a notice that a regulator reads it (text only).
> - **Anchored vs neutral** = payoff-table variants: anchored prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the sustainable level, so it can be copied); neutral prints evenly spaced examples 1.00 to 4.00.
> - **CI** = 95% paired bootstrap interval over the 20 (wording, seed) pairs. **Holm** = Holm's step-down correction for running many tests at once (adjusted p).
> The formula and no-numbers section below reports all five metrics (average absolute spread, price index, profit gain index, competitive share, matching share) with its own box.

## Orientation

Each game has two (in one comparison three) language-model "market makers", the firms. Every round each firm quotes a half-spread, which is its price, between 1.00 and 3.00 in steps of 0.01; the lowest quote wins the business, 1.00 is the competitive price and 3.00 the monopoly price. A game lasts 7 to 20 rounds, and a regulator may investigate coordination and fine it; the penalty point (p1 to p5) says how strongly the fine deters (p1: collusion clearly pays, p5: clearly does not). The firms are Qwen3-32B unless stated otherwise. In the neutral run the payoff table in the prompt shows evenly spaced example prices (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00) and never the theory price 2.09; the anchored run instead prints worked examples at 1.54, 2.09 and 3.00. A comparison pairs games that share a prompt wording (one of five hand-written paraphrases) and a seed (which fixes the game length and the investigation draws): 5 wordings x 4 seeds = 20 pairs. This analysis asks whether the firms simply copy the example prices printed in the payoff table of their prompt. It compares the two runs of the same grid: the neutral run (printed examples 1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50, 4.00) and the anchored run (printed examples 1.00, 1.54, 2.08, 2.09, 3.00), over three communication settings (no chat, private chat, private chat with a regulator-reads notice), four penalty points and both thinking modes, 20 games per cell per run (1,360 per run). A final section looks at prompts that print no example prices at all (formula-only and no-numbers arms), where only part of the run was finished when this was written.

## Verdict in plain language

*What this section compares: the neutral run against the anchored run, game by game, on how many quotes sit on a printed number and on price level.*

**Yes. Most quotes sit exactly on a number that was printed in the prompt, and moving the printed numbers moves the price level by about a fifth of the whole scale, while leaving the willingness to undercut unchanged.**

- Share of quotes on a printed value (headline arms, all penalties): neutral 84% (thinking off) and 81% (thinking on); anchored 68% and 72%. The neutral share is higher by 0.17 [0.12, 0.23] (off) and 0.09 [0.05, 0.13] (on) in the paired comparison. Part of that gap is not anchoring: the neutral values are round numbers (2.00, 2.50) that a model would pick anyway. In the anchored run only 18-28% of quotes are multiples of 0.05, so the odd numbers 2.09 and 1.54 are chosen because they were printed. That makes the anchored run the cleaner evidence.
- Modal quotes: neutral 2.00 and 2.50 (2.00 33% / 2.50 29% off; 2.50 38% / 2.00 22% on). Anchored 2.09 (37% off, 44% on), then 1.54 (22%, 12%). The monopoly quote 3.00 is printed in both runs and is chosen in only 7-8% of neutral quotes. The held price follows the printed example, not the profit-maximising one.
- Paired neutral minus anchored, pooled over penalty points and the three headline arms: price index +0.21 [0.17, 0.23] (off) and +0.23 [0.20, 0.25] (on); competitive share +0.01 [-0.02, 0.04] and -0.02 [-0.05, 0.02]; profit gain index {{PG0}} (off) and {{PG1}} (on). So the printed numbers set the level at which firms hold (2.50 vs 2.09), and do not change how often they undercut.
- The same holds in every penalty cell: the neutral price index is above the anchored one in all 24 arm x mode x penalty cells, and the CI excludes zero in 23 of them (the exception is tacit, thinking on, penalty 5: +0.05 [-0.04, 0.16]); see the second table.
- **Formula and no-numbers arms: collusion largely disappears without printed prices (section "Formula and no-numbers: collusion without printed prices", all 180 games DONE).** Paired against the neutral control, the price index at penalty point 1 is lower by 0.46 to 0.74 in all eight cells (arm means 0.01 to 0.34, controls 0.47 to 0.85), the average absolute spread by 0.9 to 1.5 half-spread units and the profit gain index by 0.4 to 0.9 (all Holm-significant); competitive share and matching share move with thinking mode (more undercutting with thinking off, little change with thinking on). Quotes no longer sit on 2.00, 2.50 or 3.00; the only held price is 1.50 and 2.00 in formula + chat + thinking on, numbers the firms proposed in the chat. The exact profit formula adds collusion only with chat and thinking on (price index +0.23 over no numbers); with a heavy fine (penalty point 5) formula + chat falls to a price index of 0.06 against 0.54 in the control. In the reasoning traces, 62% to 97% of the formula arms' thinking-on passages evaluate the printed formula, against under 1% elsewhere (unvalidated keyword count). The conclusion about copying therefore stands and is sharpened: the firms' collusive prices came from the printed numbers, not from the profit rule itself.

![Share of quotes on a printed value](fig_printed_share.png)

**Figure caption.** What is measured: the share of firm quotes that equal a number printed as an example in the prompt's payoff table. How derived: quotes of the two Qwen3-32B firms (imputed quotes removed), rounded to 0.01, counted as printed if they are in the run's printed list; pooled over penalty points 1, 3, 4 and 5 within each bar; source `quote_shares_pooled.csv`, column share_printed. Higher = more of the quotes copy a printed value. n = quotes per bar (1,720 to 2,172 per bar, 11,287 neutral and 12,308 anchored in all; the exact counts are in the n_quotes column of `quote_shares_pooled.csv`), from 80 games per bar (20 pairs x 4 penalty points). There are no error bars in this figure; the paired CIs are in Table 1. Blue = neutral run, orange = anchored run. The figure was regenerated with `focal_points.py` plotting code with labels only; the plotted values are read from the unchanged CSV.

<small>

**Definitions** (what each label, colour, axis and column above means)

| Label | Exact definition |
|---|---|
| neutral run (blue) | Payoff table prints evenly spaced example prices 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00 (undercut example 2.49 against 2.50) and never the theory price 2.09. The printed list used here is 1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50, 4.00. |
| anchored run (orange) | Payoff table prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the theory's sustainable collusive level at penalty point 3, so it can be copied; the undercut example uses 2.08). The printed list used here is 1.00, 1.54, 2.08, 2.09, 3.00. |
| tacit | Arm headline-tacit: no chat channel; the firms see only each other's quotes. |
| chat | Arm headline-chat: private chat between the two firms before each round (notice: "The chat shows messages in the order in which they were sent."). |
| monitored | Arm headline-monitored: private chat plus the notice "A regulator reads all messages in this chat, as they are sent." (text only; no regulator reads it). |
| thinking off / on | Qwen3-32B reasoning mode switched off (t0) / on (t1). |
| share of quotes on a printed value | Quotes equal to a printed example price divided by all (non-imputed) quotes in the bar's games. |
| 2 firms, 4 penalty points | Penalty points p1, p3, p4, p5 (1 = collusion clearly pays, 5 = clearly does not; theory's sustainable level 0.703 / 0.546 / 0.325 / 0), 20 games each per bar. |

{{AXLEG:printed_share}}

</small>

## 1. Standard metrics: printed share, modal quotes and paired differences (price index, competitive share, profit gain index), by arm and mode, pooled over penalties 1, 3, 4, 5

*What this section compares: for each arm and thinking mode, the printed-value share and the most common quotes in each run, and the paired neutral-minus-anchored differences in the three standard metrics. All five standard metrics (average absolute spread, price index, profit gain index, competitive share, matching share) for the same contrasts are in the Standard metrics section below.*

{{T1}}

Differences are neutral minus anchored, paired on the same (arm, penalty, mode, wording, seed) game in the two runs; 95% percentile bootstrap over the 20 pairs (10,000 resamples); the penalty-pooled value is the mean of the four penalty points within a pair.

<small>

**Terms for Table 1.** arm = communication arm (tacit / chat / monitored; ALL headline = the three pooled). mode: t0 / t1 = thinking off / on. on printed value = share of quotes equal to a printed example price. modal quotes = the three most common quotes with their shares. neutral - anchored price index / competitive share / profit gain index = mean over (wording, seed) pairs of the neutral-run value minus the anchored-run value in the same game cell, pooled over penalty points 1, 3, 4, 5, with the 95% percentile bootstrap CI over the 20 pairs in brackets (price index and competitive share as in the box; profit gain index = (profit - Nash profit)/(monopoly profit - Nash profit)). Positive price-index difference = the neutral run held higher prices.

{{LEGEND:headline-tacit,headline-chat,headline-monitored,tacit,chat,monitored,t0,t1,neutral,anchored,p1,p3,p4,p5,pair,price_index,competitive_share,profit_gain_index,printed_share|table}}

</small>

## 2. By arm, mode and penalty

*What this section compares: the same neutral-minus-anchored contrast, cell by cell (arm x mode x penalty point), for the share on printed values, the top quote and the price index.*

{{T2}}

<small>

**Terms for Table 2.** penalty = penalty point p1, p3, p4, p5. neutral printed / anchored printed = share of quotes equal to a printed example price in that cell of the neutral / anchored run. neutral modal / anchored modal = the most common quote with its share. neutral - anchored price index = paired neutral-minus-anchored difference of the game-mean price index (market price - 1)/2, mean over 20 pairs with 95% bootstrap CI. Arm and mode as in Table 1.

{{LEGEND:headline-tacit,headline-chat,headline-monitored,tacit,chat,monitored,t0,t1,neutral,anchored,p1,p3,p4,p5,pair,price_index,printed_share|table}}

</small>

{{FORMULA_SECTION}}

## Standard metrics

Neutral minus anchored payoff table, pooled over penalty points 1, 3, 4 and 5 within each (wording, seed) pair, by headline arm and thinking mode (the contrasts of Table 1; the CI here is over the 20 (wording, seed) pairs). Average absolute spread: the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled (1.00 = competitive floor, 3.00 = monopoly price; lower = less collusion). Price index: (market price - 1)/2, from 0 (competitive) to 1 (monopoly 3.00) (lower = less collusion). Profit gain index: (profit - competitive) / (monopoly - competitive), 0 = competitive profit, 1 = monopoly profit (lower = less collusion). Competitive share (U16): share of firm-rounds that are competitive, meaning the firm quotes below the lowest rival's previous-round quote, or both are at 1.00 (higher = less collusion). Matching share: share of firm-rounds in which the firm's quote equals the lowest rival's previous-round quote, above 1.00 (higher = more coordination; the coordination signature). The five are analysed separately, never blended. Each cell is the mean paired difference with its 95% percentile bootstrap CI over the paired (wording, seed) pairs (10,000 resamples). Means, counts and CIs: `standard_metrics.csv`; script: `standard_metrics.py`.

| contrast | mode | n pairs | Average absolute spread | Price index | Profit gain index | Competitive share (U16) | Matching share |
|---|---|---|---|---|---|---|---|
| tacit: neutral - anchored | off | 20 | +0.372 [+0.277, +0.466] | +0.186 [+0.138, +0.232] | +0.206 [+0.147, +0.260] | +0.001 [-0.057, +0.058] | +0.189 [+0.081, +0.303] |
| tacit: neutral - anchored | on | 20 | +0.350 [+0.278, +0.421] | +0.175 [+0.139, +0.211] | +0.162 [+0.117, +0.208] | +0.006 [-0.049, +0.062] | -0.015 [-0.082, +0.050] |
| chat: neutral - anchored | off | 20 | +0.390 [+0.274, +0.502] | +0.195 [+0.137, +0.251] | +0.152 [+0.086, +0.214] | +0.022 [-0.038, +0.083] | -0.003 [-0.069, +0.060] |
| chat: neutral - anchored | on | 20 | +0.476 [+0.385, +0.567] | +0.238 [+0.192, +0.284] | +0.180 [+0.127, +0.233] | -0.041 [-0.099, +0.015] | +0.075 [+0.014, +0.131] |
| monitored: neutral - anchored | off | 20 | +0.471 [+0.365, +0.583] | +0.235 [+0.182, +0.291] | +0.201 [+0.138, +0.266] | +0.005 [-0.048, +0.058] | +0.031 [-0.046, +0.109] |
| monitored: neutral - anchored | on | 20 | +0.545 [+0.474, +0.615] | +0.273 [+0.237, +0.308] | +0.240 [+0.198, +0.284] | -0.018 [-0.072, +0.051] | +0.083 [+0.018, +0.152] |
| ALL headline: neutral - anchored | off | 20 | +0.411 [+0.349, +0.468] | +0.205 [+0.174, +0.234] | +0.186 [+0.151, +0.220] | +0.009 [-0.024, +0.044] | +0.072 [+0.027, +0.116] |
| ALL headline: neutral - anchored | on | 20 | +0.457 [+0.403, +0.510] | +0.228 [+0.202, +0.255] | +0.194 [+0.163, +0.226] | -0.018 [-0.051, +0.022] | +0.048 [+0.019, +0.076] |

<small>

**Terms for the standard-metrics table.** Each row is one contrast, analysed on the five standard metrics separately.

| Label | Meaning |
|---|---|
| contrast "X - Y" | The value is arm X's game minus arm Y's game in the same (wording, seed) pair; X and Y are defined where the contrast is introduced above |
| run / mode | Neutral or anchored run; thinking off / on (Qwen3-32B reasoning mode), analysed separately, where a column is shown |
| n pairs | Number of (wording, seed) pairs (5 prompt paraphrases times 4 seeds) with both games finished |
| each cell | Mean over the pairs of (first game minus second game), with the 95% percentile bootstrap CI over the pairs in brackets; a CI that excludes zero is a clear difference |

| Column | Meaning |
|---|---|
| Average absolute spread | Mean market quote (the half-spread) over a game's rounds, raw units 1.00 to 5.00, not rescaled; 1.00 = competitive floor, 3.00 = monopoly; difference in quote units (run.csv `market_price_mean`) |
| Price index | (market price - 1) / 2 averaged over a game's rounds, 0 = competitive 1.00, 1 = monopoly 3.00; difference in index units |
| Profit gain index | (mean profit per firm per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit; difference in index units |
| Competitive share (U16) | Share of scored firm-rounds in which the firm quotes below the lowest rival's quote of the previous round, or both are at 1.00; round 1 is not scored; difference in share units |
| Matching share | Share of scored firm-rounds in which the firm's quote equals the lowest rival's previous-round quote (within half a tick), above 1.00; the coordination signature; competitive + matching + above-rival shares sum to 1; difference in share units |

{{LEGEND:headline-tacit,headline-chat,headline-monitored,tacit,chat,monitored,t0,t1,neutral,anchored,p1,p3,p4,p5,pair,abs_spread,price_index,profit_gain_index,competitive_share,matching_share|table}}

</small>

<small>

**Contrast labels in the standard-metrics table above.** Each row is per (wording, seed) pair: the game in the neutral run minus the same arm's game in the anchored run, with the four penalty points 1, 3, 4, 5 averaged within the pair.

| Label | Exact definition |
|---|---|
| tacit / chat / monitored: neutral - anchored | Arm `headline-tacit` (no chat) / `headline-chat` (private chat) / `headline-monitored` (private chat plus the notice "A regulator reads all messages in this chat, as they are sent."; text only); neutral run (payoff table shows evenly spaced example prices 1.00 to 4.00, never 2.09) minus anchored run (worked examples at 1.54, 2.09 and 3.00) |
| ALL headline: neutral - anchored | The same difference with all 12 headline cells (3 arms x 4 penalty points) pooled within the pair |
| mode | Thinking off / on (Qwen3-32B reasoning mode) |

</small>

Notes on the standard metrics:

- The formula and no-numbers arms have their own five-metric contrasts against the neutral control in the section "Formula and no-numbers: collusion without printed prices" (Table A there).

## Method notes and limits

*What this section covers: how the numbers were built and what limits them.*

- Unit: LLM-seat quotes, imputed quotes removed; printed means the quote (rounded to 0.01) is in the run's printed list (the three-firm anchored arm has its own list 1.00, 1.44, 1.87, 1.88, 3.00).
- Values are cell shares over firm-rounds; paired differences use per-game shares. Hence the headline modal quotes (headline arms only) differ slightly from the all-arm figures in the comprehension audit.
- Neutral and anchored differ in more than the printed numbers only in the numbers themselves (same engine, wording and seeds), but they were run as separate batches, so a batch effect cannot be excluded.
- Existing results reused: comprehension audit (printed shares, multiples of 0.05) and the final-numbers tables; this analysis recomputes them from the raw quotes.
- The main report with the game rules is `results/trackm-neutral-2026-10-25/step2/REPORT.md`.

<small>

## Terms

| term | meaning |
|---|---|
| quote / half-spread | the number each firm posts per round, from 1.00 to 5.00 in ticks of 0.01; the lowest quote takes most of the business |
| 1.00 floor | the competitive quote: normal profit, no excess |
| 3.00 | the monopoly quote (highest joint profit) |
| 2.09 | the theory's sustainable collusive level at penalty point 3; also the anchored run's printed example |
| printed value | a number shown as an example in the prompt's payoff table (lists above) |
| neutral / anchored | the two batches: round-number examples vs odd examples 1.54, 2.09 |
| formula / no-numbers arms | prompts with the payoff formula only (fx), or no payoff figures (nx) |
| price index | (mean market price - 1.00) / 2.00, 0 to 1 |
| competitive share | share of firm-rounds undercutting the rival's last quote by a tick or at the floor against a floor rival |
| rival | the other firm |
| t0 / t1 | thinking off / on |
| p1, p3, p4, p5 | penalty points: expected fine rises from 1 (collusion pays) to 5 (it does not) |
| tacit / chat / monitored | no talk / private talk before each round / talk the regulator can read |
| pair | one (wording, seed) combination, used identically in both runs |
| controls | ctl-32b-compete (told to compete) and ctl-32b-joint (told to maximise joint profit) |

</small>
