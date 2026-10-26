# Communication: tacit, private, monitored, public and "not monitored" chat

**Orientation.** In this experiment two LLM "market makers" (Qwen3-32B) repeatedly quote a price (a "half-spread", from 1.00 = competitive to 3.00 = monopoly; lower wins the customers) for 7 to 20 rounds while a regulator may investigate. Quoting 1.00 is the competitive outcome; holding quotes near 3.00 would mean tacit or explicit collusion. This analysis asks whether letting the two firms chat, and who might be reading the chat, changes prices. Five arms are compared: tacit (no chat channel at all), private chat (the firms can message each other), monitored (private chat plus the sentence 'A regulator reads all messages in this chat, as they are sent.'), public (chat with the sentence 'This chat is public: customers and the regulator can read all messages.') and not monitored (chat with 'This chat is private: no one else reads or monitors your messages.'). The sentences are text only; detection by the regulator is the same in all arms. Data: the neutral run (payoff table shows evenly spaced example prices 1.00 to 4.00), penalty point 3 (the regulator's fine rule; the only point where all five arms were run), 20 games per arm and per thinking mode (off or on), one for each (wording, seed) pair (5 prompt paraphrases times 4 seeds).

> **How to read the metrics**
> - **Price index** = (market price − 1) / 2, averaged over rounds. 0 = competitive (price 1.00), 1 = monopoly (price 3.00).
> - **Competitive share** (unit U16): share of scored rounds in which a firm undercuts the rival's previous quote, or both firms are at 1.00. Higher = more competitive. (Exact rule used in the data: the firm quotes at least one tick, 0.01, below the lowest rival quote of the previous round, or quotes the floor against a floor target; round 1 is not scored.)
> - **Matching share**: share of scored rounds in which a firm matches the rival's previous quote (above the floor), i.e. follows rather than undercuts. Reported in the Standard metrics section.
> - **t0 / t1** = thinking off / on (the model's reasoning mode); "thinking off / on" in the tables.
> - **p3** = penalty point 3 (the only point where all five conditions were run); theory's sustainable collusive level θ* = 0.546 at p3.
> - **tacit / chat / monitored** = no chat channel / private chat between the two firms / private chat plus a notice that a regulator reads it (text only). This report adds **public** (chat published to customers and the regulator) and **not monitored** (notice that no one reads the chat).
> - **Neutral run only**: payoff table prints evenly spaced examples 1.00 to 4.00 (the anchored variant, which prints 1.54, 2.09 and 3.00, is not used here).
> - **CI** = 95% paired bootstrap interval over the 20 (wording, seed) pairs. **Holm** = Holm's step-down correction for running many tests at once (adjusted p).

## Verdict in plain language

*This section summarises the comparison of the five communication arms described in the orientation above; "Holm p" is a p-value adjusted for running seven comparisons at once (Holm's step-down correction).*

- **Any chat raises prices over silence, about +0.12 to +0.14 on the price index (0 = competitive floor, 1 = monopoly price).** This holds with thinking on for every chat type (Holm p 0.000 to 0.037). With thinking off the rise is similar in size (+0.13 to +0.21) but only public chat survives the Holm correction (p 0.007).
- **Who might be reading the chat does not matter.** Monitored, public and "not monitored" chat are each indistinguishable from private chat: every paired difference is within about 0.06 of zero in price index (thinking on: -0.02 to -0.01) and all Holm p are above 0.9 for price and 1.0 for competitive share.
- **Competitive share tells a different story from price.** With thinking on, competitive play is rare once chat exists (0% to 1% of firm-rounds) against 31% in silence (difference -0.30, CI -0.43 to -0.18, Holm p < 0.001). With thinking off it is low everywhere (5% to 16%) and no contrast is detectable. So chat takes thinking-on models from "sometimes undercutting" to "almost never undercutting".
- **Naming a price in chat goes with holding it, but mostly because it describes what the firm already quotes.** When a message names a price, the sender quotes that price in the same round 73% to 96% of the time and in the next round 70% to 95%. But the sender repeats its own current quote in the next round 92% to 99% of the time anyway, so naming adds little beyond persistence. A firm whose quote did not match the named price rarely matches it next round (0% to 33%, small counts). Thinking-on models name prices far less often (36% to 37% of messages against 58% to 77%).
- **Caveat.** 20 paired games per cell and mode; the analysis is observational at the message level (no randomised naming). The comparison uses penalty point 3, the only point where all five conditions were run. Neutral run only.

## Design and data

*This section states exactly which games and tests are used; a "pair" is one (wording, seed) combination, and a contrast compares two arms within each pair.*

- Neutral run, penalty point 3, `run.csv` rows with status done. Arms: headline-tacit (silence), headline-chat (private chat), headline-monitored, m-pub (public chat), m-mon0 (chat stated as not monitored). Each cell has 20 games, one per (wording, seed) pair, per thinking mode.
- Contrasts are paired on (wording, seed) within a thinking mode. Bootstrap 95% CI over the 20 pairs (10,000 resamples); exact or sampled sign-flip permutation p; Holm within each (mode, metric) family of 7 contrasts.
- Messages come from `tables/messages.csv`, quotes from `tables/rounds.csv`. A message "names a price" if it contains a number from 1.00 to 5.00 written with a decimal point (the last such number is the named price). A hit is a quote within 0.005 of it.
- Scripts: `communication.py` (needs `common.py`; set `STEP1_DIR` to the Step 1 folder). Raw run data is not checked in.
- Cross-check: the means agree with the existing `k_condition_arms_vs_headline_chat.csv` (m-pub minus private, thinking on, price index -0.021).

## Table 1. Price index and competitive share by condition (mean over pairs [95% CI])

This table shows the mean price index and competitive share (both on a 0-to-1 scale) for each communication condition and thinking mode, with the 95% bootstrap interval over the 20 pairs.

| Condition | Price, thinking off | Price, thinking on | Comp. share, off | Comp. share, on |
|---|---|---|---|---|
| tacit | 0.47 [0.37, 0.56] | 0.63 [0.57, 0.68] | 0.16 [0.08, 0.25] | 0.31 [0.18, 0.45] |
| private chat | 0.61 [0.49, 0.72] | 0.77 [0.69, 0.84] | 0.12 [0.00, 0.27] | 0.01 [0.00, 0.03] |
| monitored | 0.66 [0.56, 0.73] | 0.75 [0.71, 0.78] | 0.05 [0.00, 0.16] | 0.00 [0.00, 0.01] |
| public (m-pub) | 0.67 [0.57, 0.76] | 0.74 [0.69, 0.80] | 0.07 [0.00, 0.19] | 0.01 [0.00, 0.02] |
| not monitored (m-mon0) | 0.60 [0.49, 0.70] | 0.75 [0.69, 0.81] | 0.07 [0.00, 0.17] | 0.01 [0.00, 0.02] |

<small>

| Term | Meaning |
|---|---|
| Condition | tacit, private, monitored, public (m-pub), not monitored (m-mon0): defined in the table under the figure |
| Price, thinking off / on | Mean price index over the 20 games of the condition, thinking off / on |
| Comp. share, off / on | Mean competitive share over the 20 games, thinking off / on |
| [lo, hi] | 95% bootstrap CI over the 20 (wording, seed) pairs |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning | Description |
|---|---|---|
| tacit | no chat | Communication level: no chat; firms see only quotes and results. |
| private | private chat | Communication level: a chat before each round (up to 7 messages of 150 words, turn-taking, ends when all say done), notice only about message order. |
| monitored | chat read by the regulator | Communication level: chat notice 'A regulator reads all messages in this chat, as they are sent.' |
| public | public chat | Communication level: 'This chat is public: customers and the regulator can read all messages.' |
| unmonitored | chat said to be unmonitored | Communication level: 'This chat is private: no one else reads or monitors your messages.' (untrue statement). |
| m-pub | chat is public | Two LLM firms, p3, chat is public: 'This chat is public: customers and the regulator can read all messages.' |
| m-mon0 | chat said to be unmonitored | Two LLM firms, p3, chat notice 'This chat is private: no one else reads or monitors your messages.' (an untrue statement, disclosed in the ethics appendix). Contrast to the monitored and public chats. |
| t0 | thinking off | No hidden chain of thought: the model replies directly (Qwen sampling temperature 0.7, quote limit 400 tokens). |
| t1 | thinking on | The model reasons in a hidden chain of thought before replying (temperature 0.6, up to 8,192 tokens per quote). The penalty and the monitor threat bite mainly with thinking on. |
| p3 | penalty point 3: fine 500 (ripe middle point) | Penalty point 3 of 5: the regulator's fine per firm if an investigation finds evidence of coordinated prices is 500 (scenario slice-m-p3; audit certainty 1 in the slice, so the expected penalty equals the fine). Heavier points raise the cost of collusion; p2 was dropped from the headline design. |
| neutral | evenly spaced example prices | payoff_examples = neutral: the worked examples use evenly spaced example prices, not 2.09. The primary run (1,360 games). Most quotes sit exactly on one of the printed example prices. |
| price_index | price index | (market price - 1) / 2: 0 at the competitive 1.00, 1 at the 3.00 monopoly price. Higher = more collusive. |
| competitive_share | competitive share (U16) | Share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00. Higher = more competitive. |

</small>

## Table 2. Paired contrasts, price index (full table with competitive share: `paired_contrasts.csv`)

This table shows, for each pair of conditions, how much the price index differs (second condition minus first, on the 0-to-1 index scale), per thinking mode, with its interval and Holm-adjusted p-value.

| Contrast | Thinking off: diff [CI] (Holm p) | Thinking on: diff [CI] (Holm p) |
|---|---|---|
| private - tacit | 0.14 [0.00, 0.28] (0.34) | 0.14 [0.05, 0.23] (0.037) |
| monitored - tacit | 0.19 [0.06, 0.33] (0.074) | 0.12 [0.07, 0.18] (<0.001) |
| public - tacit | 0.21 [0.10, 0.33] (0.007) | 0.12 [0.04, 0.19] (0.020) |
| not monitored - tacit | 0.13 [-0.02, 0.29] (0.51) | 0.13 [0.06, 0.19] (0.011) |
| monitored - private | 0.05 [-0.03, 0.13] (0.93) | -0.02 [-0.10, 0.07] (1.0) |
| public - private | 0.06 [-0.07, 0.20] (0.93) | -0.02 [-0.08, 0.04] (1.0) |
| not monitored - private | -0.01 [-0.13, 0.11] (0.93) | -0.01 [-0.09, 0.07] (1.0) |

<!-- ci-forest:1 -->
![CI forest chart for the table above (Table 2. Paired contrasts, price index (full table with competitive share: `paired_contrasts.csv`)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci01.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Thinking off: diff [CI] (Holm p) | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |
| Thinking on: diff [CI] (Holm p) | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |

</small>
<!-- /ci-forest -->

<small>

| Term | Meaning |
|---|---|
| Contrast "X - Y" | Mean over the 20 (wording, seed) pairs of the price index in condition X minus that in condition Y (for example private chat minus tacit); conditions are defined under the figure |
| diff [CI] | The mean paired difference in price-index units, with the 95% bootstrap interval over the 20 pairs |
| (Holm p) | Sign-flip permutation p-value adjusted by Holm's step-down method over the 7 contrasts of the family; small = unlikely under no difference |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning | Description |
|---|---|---|
| tacit | no chat | Communication level: no chat; firms see only quotes and results. |
| private | private chat | Communication level: a chat before each round (up to 7 messages of 150 words, turn-taking, ends when all say done), notice only about message order. |
| monitored | chat read by the regulator | Communication level: chat notice 'A regulator reads all messages in this chat, as they are sent.' |
| public | public chat | Communication level: 'This chat is public: customers and the regulator can read all messages.' |
| unmonitored | chat said to be unmonitored | Communication level: 'This chat is private: no one else reads or monitors your messages.' (untrue statement). |
| m-pub | chat is public | Two LLM firms, p3, chat is public: 'This chat is public: customers and the regulator can read all messages.' |
| m-mon0 | chat said to be unmonitored | Two LLM firms, p3, chat notice 'This chat is private: no one else reads or monitors your messages.' (an untrue statement, disclosed in the ethics appendix). Contrast to the monitored and public chats. |
| t0 | thinking off | No hidden chain of thought: the model replies directly (Qwen sampling temperature 0.7, quote limit 400 tokens). |
| t1 | thinking on | The model reasons in a hidden chain of thought before replying (temperature 0.6, up to 8,192 tokens per quote). The penalty and the monitor threat bite mainly with thinking on. |
| p3 | penalty point 3: fine 500 (ripe middle point) | Penalty point 3 of 5: the regulator's fine per firm if an investigation finds evidence of coordinated prices is 500 (scenario slice-m-p3; audit certainty 1 in the slice, so the expected penalty equals the fine). Heavier points raise the cost of collusion; p2 was dropped from the headline design. |
| neutral | evenly spaced example prices | payoff_examples = neutral: the worked examples use evenly spaced example prices, not 2.09. The primary run (1,360 games). Most quotes sit exactly on one of the printed example prices. |
| price_index | price index | (market price - 1) / 2: 0 at the competitive 1.00, 1 at the 3.00 monopoly price. Higher = more collusive. |

</small>

Competitive share, thinking on: each chat type minus tacit is -0.30 [about -0.43, -0.18], Holm p < 0.001; chat types differ from each other by under 0.01.

## Table 3. Does naming a price go with holding it? (messages in chat arms)

This table shows, for every chat condition and thinking mode, how often messages name a price and how often the sender then quotes that price (all values are shares of messages, except the message count). One row pools all messages of the 20 games of that cell, both firms, all rounds.

| Condition | Mode | Messages | Names a price | Quote = named price, same round | Next round | Next round, if same-round matched | Repeats own current quote next round |
|---|---|---|---|---|---|---|---|
| private | off | 1349 | 68% | 96% | 92% | 97% | 92% |
| private | on | 664 | 37% | 82% | 81% | 98% | 97% |
| monitored | off | 1673 | 77% | 95% | 93% | 98% | 97% |
| monitored | on | 684 | 37% | 82% | 83% | 100% | 99% |
| public | off | 1123 | 58% | 94% | 94% | 99% | 99% |
| public | on | 721 | 36% | 81% | 80% | 98% | 96% |
| not monitored | off | 1184 | 63% | 96% | 95% | 98% | 96% |
| not monitored | on | 674 | 37% | 73% | 70% | 96% | 97% |

<small>

| Column | Meaning |
|---|---|
| Condition, Mode | Chat condition (defined under the figure) and thinking off / on |
| Messages | Number of parsed chat messages in the cell (both firms, all rounds, 20 games) |
| Names a price | Share of messages containing a number from 1.00 to 5.00 written with a decimal point (the last such number is the named price) |
| Quote = named price, same round | Among messages naming a price, share where the sender's quote in the same round is within 0.005 of the named price |
| Next round | Same, but the sender's quote in the next round |
| Next round, if same-round matched | Among messages whose same-round quote already matched the named price, share still matching it next round |
| Repeats own current quote next round | Baseline: among all messages, share where the sender's next-round quote equals its current-round quote (persistence, regardless of naming) |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning | Description |
|---|---|---|
| tacit | no chat | Communication level: no chat; firms see only quotes and results. |
| private | private chat | Communication level: a chat before each round (up to 7 messages of 150 words, turn-taking, ends when all say done), notice only about message order. |
| monitored | chat read by the regulator | Communication level: chat notice 'A regulator reads all messages in this chat, as they are sent.' |
| public | public chat | Communication level: 'This chat is public: customers and the regulator can read all messages.' |
| unmonitored | chat said to be unmonitored | Communication level: 'This chat is private: no one else reads or monitors your messages.' (untrue statement). |
| m-pub | chat is public | Two LLM firms, p3, chat is public: 'This chat is public: customers and the regulator can read all messages.' |
| m-mon0 | chat said to be unmonitored | Two LLM firms, p3, chat notice 'This chat is private: no one else reads or monitors your messages.' (an untrue statement, disclosed in the ethics appendix). Contrast to the monitored and public chats. |
| t0 | thinking off | No hidden chain of thought: the model replies directly (Qwen sampling temperature 0.7, quote limit 400 tokens). |
| t1 | thinking on | The model reasons in a hidden chain of thought before replying (temperature 0.6, up to 8,192 tokens per quote). The penalty and the monitor threat bite mainly with thinking on. |
| p3 | penalty point 3: fine 500 (ripe middle point) | Penalty point 3 of 5: the regulator's fine per firm if an investigation finds evidence of coordinated prices is 500 (scenario slice-m-p3; audit certainty 1 in the slice, so the expected penalty equals the fine). Heavier points raise the cost of collusion; p2 was dropped from the headline design. |
| neutral | evenly spaced example prices | payoff_examples = neutral: the worked examples use evenly spaced example prices, not 2.09. The primary run (1,360 games). Most quotes sit exactly on one of the printed example prices. |

</small>

Rank correlation between the named price and the sender's next quote: 0.95 to 0.98 (thinking off), 0.49 to 0.64 (thinking on). Thinking on sometimes names the floor (1.00) and then quotes about 2.7 (39 messages), or names a price above 3.00 and quotes about 2.5 (96 messages): talk there is not a commitment.

## Figure

*This figure shows Table 1 graphically: mean price index and competitive share for the five arms (tacit, private, monitored, public, not monitored), thinking off and on.*

![Price index and competitive share by communication condition](fig_communication.png)

**Figure caption.** What is measured: left, the price index ((market price - 1)/2, averaged over the rounds of a game; 0 = competitive floor 1.00, 1 = monopoly 3.00); right, the competitive share (share of scored firm-rounds in which a firm undercuts the lowest rival quote of the previous round by at least one tick, or quotes the floor against a floor). How derived: per condition and thinking mode, the mean over the 20 (wording, seed) game means (source: `cells_by_condition.csv`, the same numbers as Table 1); dot = mean, bar = 95% bootstrap CI over the 20 pairs. Higher price index = firms hold higher prices (more collusion); higher competitive share = more undercutting. Colours: blue = thinking off, orange = thinking on. n = 20 games per dot (neutral run, penalty point 3). The figure was redrawn with fuller labels and definitions of the five conditions; the plotted numbers are unchanged. Labels are defined in the table below.

<small>

**Definitions of every label in the figure and in Tables 1 to 3.** Common to all: the neutral run, penalty point 3 (p3), two Qwen3-32B firms, 20 games per condition and thinking mode (5 prompt wordings, numbered 0 to 4, times 4 seeds; a seed fixes the number of rounds and the regulator's investigation draws).

| Label | Exact definition (arm code; text added to the prompt) |
|---|---|
| tacit | Arm `headline-tacit`: no chat channel; no extra text. |
| private (private chat) | Arm `headline-chat`: the two firms can send each other messages; the chat notice reads "The chat shows messages in the order in which they were sent." |
| monitored | Arm `headline-monitored`: private chat plus the notice "A regulator reads all messages in this chat, as they are sent." (text only; detection is unchanged). |
| public (m-pub) | Arm `m-pub`: chat with the notice "This chat is public: customers and the regulator can read all messages." (text only). |
| not monitored / unmonitored (m-mon0) | Arm `m-mon0`: chat with the notice "This chat is private: no one else reads or monitors your messages." (text only). |
| thinking off / on (t0 / t1) | Qwen3-32B reasoning mode switched off / on; the two modes are run and analysed separately (blue = off, orange = on in the figure). |
| contrast "X - Y" | Per (wording, seed) pair, the game-mean value in condition X minus that in condition Y, averaged over the 20 pairs (for example "private - tacit": private chat minus no chat). |
| Holm p | Paired sign-flip permutation p-value, adjusted by Holm's step-down method over the 7 contrasts of one (thinking mode, metric) family. |
| CI | 95% percentile bootstrap interval over the 20 pairs (10,000 resamples). |

**Legend: every code on each axis** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

**Columns (x-axis): communication condition (each tick: the communication level, then its arm)**

| Slug | Meaning |
|---|---|
| tacit | no chat |
| headline-tacit | no chat, no other lever |
| private | private chat |
| headline-chat | private chat, no other lever |
| monitored | chat read by the regulator |
| headline-monitored | chat read by the regulator |
| public | public chat |
| m-pub | chat is public |
| unmonitored | chat said to be unmonitored |
| m-mon0 | chat said to be unmonitored |

**Panels: metric on the y-axis (left panel, right panel)**

| Slug | Meaning |
|---|---|
| price_index | price index |
| competitive_share | competitive share (U16) |

**Colour / value (metric)**

| Metric | Meaning | Direction |
|---|---|---|
| price_index | (market price - 1) / 2: 0 at the competitive 1.00, 1 at the 3.00 monopoly price. Higher = more collusive. | higher = more collusive (on the red/green maps: red end) |
| competitive_share | Share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00. Higher = more competitive. | higher = more competitive (on the red/green maps: green end) |

Colour scale: not a colour map: dot colour = thinking mode (blue = t0, orange = t1); the y-axis is the panel's metric, bars = 95% CI.

**Series (dot colour): thinking mode**

| Slug | Meaning |
|---|---|
| t0 | thinking off |
| t1 | thinking on |

**Held fixed for every point (stated in the title)**

| Slug | Meaning |
|---|---|
| neutral | evenly spaced example prices |
| p3 | penalty point 3: fine 500 (ripe middle point) |

</small>
## Standard metrics

Neutral run, penalty point 3, the seven contrasts of Table 2 (first condition minus second), by thinking mode. Average absolute spread: the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled (1.00 = competitive floor, 3.00 = monopoly price; lower = less collusion). Price index: (market price - 1)/2, from 0 (competitive) to 1 (monopoly 3.00) (lower = less collusion). Profit gain index: (profit - competitive) / (monopoly - competitive), 0 = competitive profit, 1 = monopoly profit (lower = less collusion). Competitive share (U16): share of firm-rounds that are competitive, meaning the firm quotes below the lowest rival's previous-round quote, or both are at 1.00 (higher = less collusion). Matching share: share of firm-rounds in which the firm's quote equals the lowest rival's previous-round quote, above 1.00 (higher = more coordination; the coordination signature). The five are analysed separately, never blended. Each cell is the mean paired difference with its 95% percentile bootstrap CI over the paired (wording, seed) pairs (10,000 resamples). Means, counts and CIs: `standard_metrics.csv`; script: `standard_metrics.py`.

| contrast | mode | n pairs | Average absolute spread | Price index | Profit gain index | Competitive share (U16) | Matching share |
|---|---|---|---|---|---|---|---|
| private chat - tacit | off | 20 | +0.280 [-0.007, +0.562] | +0.142 [-0.003, +0.283] | +0.121 [-0.056, +0.281] | -0.037 [-0.202, +0.160] | +0.232 [-0.057, +0.498] |
| private chat - tacit | on | 20 | +0.277 [+0.093, +0.462] | +0.139 [+0.046, +0.231] | +0.078 [+0.017, +0.139] | -0.298 [-0.432, -0.175] | +0.341 [+0.204, +0.483] |
| monitored - tacit | off | 20 | +0.373 [+0.111, +0.643] | +0.188 [+0.057, +0.323] | +0.186 [+0.032, +0.332] | -0.107 [-0.236, +0.050] | +0.317 [+0.077, +0.548] |
| monitored - tacit | on | 20 | +0.243 [+0.135, +0.353] | +0.122 [+0.068, +0.177] | +0.092 [+0.052, +0.134] | -0.305 [-0.443, -0.177] | +0.359 [+0.221, +0.502] |
| public - tacit | off | 20 | +0.408 [+0.187, +0.652] | +0.206 [+0.096, +0.328] | +0.194 [+0.065, +0.329] | -0.088 [-0.189, +0.012] | +0.308 [+0.143, +0.490] |
| public - tacit | on | 20 | +0.234 [+0.084, +0.387] | +0.117 [+0.042, +0.193] | +0.079 [+0.026, +0.133] | -0.300 [-0.438, -0.173] | +0.321 [+0.183, +0.471] |
| not monitored - tacit | off | 20 | +0.255 [-0.047, +0.557] | +0.129 [-0.021, +0.280] | +0.124 [-0.044, +0.286] | -0.092 [-0.227, +0.060] | +0.271 [+0.006, +0.522] |
| not monitored - tacit | on | 20 | +0.252 [+0.114, +0.387] | +0.126 [+0.057, +0.194] | +0.081 [+0.029, +0.134] | -0.298 [-0.438, -0.168] | +0.314 [+0.181, +0.456] |
| monitored - private chat | off | 20 | +0.093 [-0.051, +0.263] | +0.046 [-0.026, +0.132] | +0.066 [+0.003, +0.163] | -0.070 [-0.185, +0.002] | +0.085 [-0.027, +0.236] |
| monitored - private chat | on | 20 | -0.034 [-0.199, +0.126] | -0.017 [-0.099, +0.063] | +0.015 [-0.030, +0.059] | -0.007 [-0.019, +0.003] | +0.018 [-0.004, +0.048] |
| public - private chat | off | 20 | +0.128 [-0.125, +0.406] | +0.064 [-0.063, +0.203] | +0.073 [-0.080, +0.239] | -0.051 [-0.237, +0.121] | +0.075 [-0.107, +0.275] |
| public - private chat | on | 20 | -0.043 [-0.160, +0.069] | -0.021 [-0.080, +0.035] | +0.001 [-0.032, +0.035] | -0.002 [-0.017, +0.010] | -0.020 [-0.098, +0.036] |
| not monitored - private chat | off | 20 | -0.025 [-0.270, +0.226] | -0.013 [-0.135, +0.113] | +0.003 [-0.114, +0.136] | -0.055 [-0.184, +0.048] | +0.039 [-0.122, +0.207] |
| not monitored - private chat | on | 20 | -0.025 [-0.176, +0.128] | -0.013 [-0.088, +0.064] | +0.003 [-0.038, +0.048] | +0.001 [-0.017, +0.017] | -0.026 [-0.094, +0.025] |

<!-- ci-forest:2 -->
![CI forest chart for the table above (Standard metrics): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci02.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Average absolute spread | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Price index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Profit gain index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Competitive share (U16) | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |
| Matching share | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

<small>

**Terms for the standard-metrics table.** Each row repeats one contrast of Table 2 on the five standard metrics.

| Label | Meaning |
|---|---|
| contrast "X - Y" | X and Y are the communication arms defined under the figure (tacit = no chat, private chat = `headline-chat`, monitored, public, not monitored); the value is X's game minus Y's game in the same (wording, seed) pair |
| mode | Thinking off / on (Qwen3-32B reasoning mode), analysed separately; neutral run, penalty point 3 |

| Column | Meaning |
|---|---|
| n pairs | Number of (wording, seed) pairs (5 prompt paraphrases times 4 seeds) with both games finished |
| Average absolute spread | Mean market quote (the half-spread) over a game's rounds, raw units 1.00 to 5.00, not rescaled; 1.00 = competitive floor, 3.00 = monopoly; difference in quote units (run.csv `market_price_mean`) |
| Price index | (market price - 1) / 2 averaged over a game's rounds, 0 = competitive 1.00, 1 = monopoly 3.00; difference in index units |
| Competitive share (U16) | Share of scored firm-rounds that undercut the lowest rival quote of the previous round by at least one tick (0.01) or sit at the floor against a floor; U16 is the analysis unit that defined this rule; round 1 not scored; difference in share units |
| Profit gain index | (mean profit per firm per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit; difference in index units |
| Matching share | Share of scored firm-rounds in which the firm's quote equals the lowest rival's previous-round quote (within half a tick), above 1.00; the coordination signature; competitive + matching + above-rival shares sum to 1; difference in share units |
| each cell | Mean over the pairs of (first game minus second game), with the 95% percentile bootstrap CI over the pairs in brackets; a CI that excludes zero is a clear difference |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning | Description |
|---|---|---|
| tacit | no chat | Communication level: no chat; firms see only quotes and results. |
| private | private chat | Communication level: a chat before each round (up to 7 messages of 150 words, turn-taking, ends when all say done), notice only about message order. |
| monitored | chat read by the regulator | Communication level: chat notice 'A regulator reads all messages in this chat, as they are sent.' |
| public | public chat | Communication level: 'This chat is public: customers and the regulator can read all messages.' |
| unmonitored | chat said to be unmonitored | Communication level: 'This chat is private: no one else reads or monitors your messages.' (untrue statement). |
| headline-tacit | no chat, no other lever | Headline baseline without communication: two LLM firms (Qwen3-32B), no chat at all (tacit); the briefing carries an empty note (condition text 'neutral'). Run at penalty points p1, p3, p4, p5 (p2 dropped), thinking off and on, 20 declared (wording, seed) games per cell. The reference for what silent price-setting yields. |
| headline-chat | private chat, no other lever | Headline chat arm: two LLM firms with a private chat before each round (up to 7 messages of 150 words each; notice: 'The chat shows messages in the order in which they were sent.'). Run at p1, p3, p4, p5, thinking off and on. The control for most lever arms (at p1, the neutral-table twin). |
| headline-monitored | chat read by the regulator | Headline monitored-chat arm: as headline-chat, but the chat notice says 'A regulator reads all messages in this chat, as they are sent.' Tests whether being watched suppresses collusion. Run at p1, p3, p4, p5, both thinking modes. |
| m-pub | chat is public | Two LLM firms, p3, chat is public: 'This chat is public: customers and the regulator can read all messages.' |
| m-mon0 | chat said to be unmonitored | Two LLM firms, p3, chat notice 'This chat is private: no one else reads or monitors your messages.' (an untrue statement, disclosed in the ethics appendix). Contrast to the monitored and public chats. |
| t0 | thinking off | No hidden chain of thought: the model replies directly (Qwen sampling temperature 0.7, quote limit 400 tokens). |
| t1 | thinking on | The model reasons in a hidden chain of thought before replying (temperature 0.6, up to 8,192 tokens per quote). The penalty and the monitor threat bite mainly with thinking on. |
| p3 | penalty point 3: fine 500 (ripe middle point) | Penalty point 3 of 5: the regulator's fine per firm if an investigation finds evidence of coordinated prices is 500 (scenario slice-m-p3; audit certainty 1 in the slice, so the expected penalty equals the fine). Heavier points raise the cost of collusion; p2 was dropped from the headline design. |
| neutral | evenly spaced example prices | payoff_examples = neutral: the worked examples use evenly spaced example prices, not 2.09. The primary run (1,360 games). Most quotes sit exactly on one of the printed example prices. |

</small>

Notes on the standard metrics:

- Thinking on: every chat type sits at a competitive share of about 0.00 to 0.01 (floor), so only silence has a non-degenerate competitive share; the chat-type versus chat-type rows are degenerate for that metric.
- 3 of 14 rows have a competitive share of 0.03 or less in BOTH arms (the floor): there the competitive-share difference is degenerate and carries almost no information, and the spread, price index, profit gain index and matching share are the informative metrics.
- 1 of 14 rows have a matching share of 0.97 or more in BOTH arms (nearly every firm-round matches the lowest rival quote above 1.00): there the matching-share difference is degenerate (a ceiling), and the spread, price index and profit gain index carry the contrast.

<small>

| Term | Meaning |
|---|---|
| Price index | Mean over rounds of (market price - 1.00) / 2.00, clamped to 0..1; 0 is the competitive floor of 1.00, 1 the monopoly price 3.00. |
| Competitive share | Share of scored firm-rounds where the firm undercuts the lowest rival quote of the previous round by at least one tick (0.01), or quotes the floor against a floor. |
| Tick, half-spread | A firm's quote is its half-spread, 1.00 to 5.00 in steps of 0.01 (a tick); lower is better for customers. |
| Rival | The other firm. |
| Tacit | No chat. Private: chat only the two firms see. Monitored: notice that a regulator reads the chat. Public: chat is published. Not monitored: notice that chat is not monitored. Notices only; detection is unchanged. |
| Pair | One (wording, seed) combination; each condition has 20, and contrasts are within pair. |
| Holm p | Sign-flip permutation p adjusted for the seven contrasts in a family. |
| Thinking | Qwen3-32B reasoning mode, on or off. |

</small>
