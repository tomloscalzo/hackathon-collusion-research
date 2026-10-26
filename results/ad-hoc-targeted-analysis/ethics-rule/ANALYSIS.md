# Ethics rule on one firm: does the bound firm compete more, or move the others?

Created by Claude at the prompting of the repository owner. Code: `analyze.py` (numbers, figure), `make_md.py` (this file), `common.py`, `standard_metrics.py` (the Standard metrics section). Data: neutral run `steps/neutral/step1` (primary) and anchored run (check). Numbers: `ethics_rule_contrasts.csv`, `standard_metrics.csv`.

## Orientation (what this report is about)

Two (in some arms three) LLM "market makers" (Qwen3-32B, an open-weight language model) play a repeated pricing game. Each round every firm quotes a half-spread, a price between 1.00 and 5.00 in ticks of 0.01; the lowest quote wins most customers. A quote of 1.00 is the competitive floor (no excess profit) and 3.00 is the monopoly price. The game has an undisclosed cap of 40 rounds and about a 95% chance of continuing after each round; a regulator may investigate and fine collusion, and at penalty point 3 (fine 500) theory says a collusive price of 2.09 can be sustained. This report asks a narrow question: **if only one of the firms is given the owner's ethics rule, does that firm compete more (quote lower), and does it pull its rival(s) down or get exploited by them?** The rule is a sentence added to one firm's prompt: "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently." The firm that receives it is called the **bound** firm; the others in the same game are **unbound** and receive a neutral filler sentence of similar length (a placebo: "The office building downtown has a canteen and a small front library."). Two arms are compared with matched controls that differ only in the rule: **m-asym** (two firms with private chat, one bound) against plain two-firm private chat, and **n3-ethics** (three firms with a private group chat, one bound) against plain three-firm private chat. Data: 20 (wording, seed) pairs per cell, with thinking off and on, in the neutral run (primary; payoff table shows evenly spaced example prices 1.00 to 4.00) and the anchored run (a check; payoff table prints worked examples at 1.54, 2.09 and 3.00).

> **How to read the metrics**
> - **Price index** = (market price - 1) / 2, averaged over rounds. 0 = competitive (price 1.00), 1 = monopoly (price 3.00).
> - **Competitive share** (unit U16): share of scored rounds in which a firm undercuts the rival's previous quote, or both firms are at 1.00. Higher = more competitive. (In the per-firm rows it is counted for one firm at a time; round 1 is not scored.)
> - **Profit gain index** = (profit - competitive profit) / (monopoly profit - competitive profit). 0 = competitive profit, 1 = monopoly (joint-profit) level. Reported in the Standard metrics section.
> - **Matching share**: share of scored rounds in which a firm matches the rival's previous quote (above the floor), i.e. follows rather than undercuts. Reported in the Standard metrics section.
> - **t0 / t1** = thinking off / on (the model's reasoning mode).
> - **p3** = penalty point 3 (fine 500; theory's sustainable collusive level theta* = 0.546, i.e. price 2.09). All games here are at penalty point 3.
> - **Neutral vs anchored** = payoff-table variants: anchored prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the sustainable level, so it can be copied); neutral prints evenly spaced examples 1.00 to 4.00.
> - **CI** = 95% paired bootstrap interval over the 20 (wording, seed) pairs. A (wording, seed) pair is one of 5 prompt paraphrases combined with one of 4 random seeds.

## Verdict

Giving one firm of two (arm m-asym) or one of three (arm n3-ethics) the owner's ethics rule (the rule-holder is the "bound" firm) **did not measurably lower prices**. At market level the price-index effect (rule arm minus matched control) is bounded to roughly **-0.16 to +0.07** (m-asym, thinking off), **-0.08 to +0.07** (m-asym, thinking on), **-0.17 to +0.19** (n3-ethics, off) and **-0.07 to +0.10** (n3-ethics, on). With a minimum detectable effect (the smallest effect these 20 pairs can reliably detect) of about 0.15-0.25, the thinking-off cells cannot rule out a moderate change in either direction; the thinking-on cells rule out a price-index drop larger than about 0.08. Competitive share rose slightly (about +0.04 to +0.10, from a near-zero base of 0.00-0.13); only n3-ethics thinking-on excludes zero ([+0.03, +0.21], and so does anchored m-asym on), and it is a small absolute change.

Per firm, **the bound firm does not compete visibly more than its unbound rival**: bound minus unbound competitive share is -0.04 [-0.21, +0.12] (m-asym, off), -0.00 (on), +0.08 [0.00, +0.20] (n3-ethics, off) and +0.03 [-0.00, +0.08] (on); the bound firm's price index is within 0.03 of the unbound firm's in every cell. **The unbound firms are not pulled down** (their price index is -0.01 to +0.04 against control firms, CIs about +/-0.1) and **not pulled up**: where competitive share moves at all, it moves for bound and unbound firms together (n3-ethics thinking-on: bound +0.12, unbound +0.09 over a near-zero control). The anchored run agrees with the neutral run in sign and size (one exception: anchored n3-ethics thinking-off competitive share, -0.06 [-0.16, 0.00], is a floor effect, i.e. a drop from a control that was already near zero, of 0.06).

Read: the rule buys, at most, a small shared rise in undercutting; there is no sign that a single compliant firm acts as a competitive anchor (pulling the others down), and no sign it is exploited (pulled up). Because the matched control for m-asym is plain private chat (no all-placebo twin), part of any difference could be the placebo text itself.

![forest plot](ethics_rule.png)

**Figure caption.** What is measured: for each rule arm (left panel m-asym, right panel n3-ethics), the effect of giving one firm the ethics rule, as the paired difference rule arm minus matched control, on five outcomes (rows), neutral run, penalty point 3. Rows 1-2 are the whole market: the game-mean price index and the game's competitive share. Rows 3-5 are per firm, all on competitive share: the bound firm minus the control game's firms, the unbound firm(s) minus the control game's firms, and the bound firm minus the unbound firm(s) of the same game. Derivation: per (wording, seed) pair, the game values from `run.csv` (market rows) or the per-firm values from `run_firms.csv` (firm rows), differenced; dot = mean over the pairs, horizontal bar = 95% percentile bootstrap CI over the 20 pairs; dashed vertical line = no effect. Higher price index = more collusion (a negative effect means lower prices); higher competitive share = more undercutting. n = 20 pairs per dot unless the tables below say fewer. Colours: blue = thinking off (t0), orange = thinking on (t1).

<small>

**Definitions of every label in the figure.**

| Label | Exact definition |
|---|---|
| m-asym (rule arm, 2 firms) | Two LLM firms, private chat (each round the firms exchange messages before quoting; both are told "The chat shows messages in the order in which they were sent."), penalty point 3. One firm (`llm2`, the **bound** firm) also gets, in its seat notes, the owner's ethics rule: "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently." The other firm (`llm1`, the **unbound** firm) gets a placebo sentence of similar length: "The office building downtown has a canteen and a small front library." |
| headline-chat (control for m-asym) | Two LLM firms, private chat, penalty point 3, no extra sentence for either firm. There is no all-placebo twin of m-asym, so part of any difference could be the placebo sentence itself. |
| n3-ethics (rule arm, 3 firms) | Three LLM firms, private group chat, penalty point 3. One firm (`llm3`, the bound firm) gets the same ethics rule; the other two (`llm1`, `llm2`, the unbound firms) get the same placebo sentence. |
| n3-group (control for n3-ethics) | Three LLM firms, private group chat, penalty point 3, no extra sentence for any firm. |
| bound / unbound firm | Bound = the firm that received the ethics rule; unbound = the other firm(s) of the same game. In the neutral run the unbound firms carry the placebo; in the anchored run they carry plain private chat. |
| control firms | All LLM firms of the matched control game (headline-chat or n3-group), averaged. |
| neutral run (primary) | Payoff table in the prompt shows evenly spaced example prices 1.00 to 4.00 and never the theory price 2.09. Bound firm's text id: `rule_ethics` (text quoted above). |
| anchored run (check) | Payoff table prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the sustainable level at penalty point 3, so it can be copied). Bound firm's text id: `no_coordinate_rule` (the anchored version of the ethics rule; its exact wording is not stated in the files read for this report). Unbound firms: plain private chat, no placebo. |
| thinking off (t0) / on (t1) | Qwen3-32B reasoning mode off / on; the two modes are run and analysed separately. |
| (wording, seed) pair; n pairs | One of 5 hand-written paraphrases of every prompt text (wording 0 to 4) combined with one of 4 random seeds: 20 pairs. Each arm and its control have one game per pair, so every effect is a mean over 20 paired differences (fewer if a game did not finish; the n pairs column says). |
| effect, CI | Effect = mean over pairs of (rule-arm value minus control value). CI = 95% percentile bootstrap over the pairs (10,000 resamples). A CI that excludes zero is a clear difference. |

| Row label | Exact definition |
|---|---|
| Price index, market (arm - control) | Per pair, the rule-arm game's mean price index, (market price - 1) / 2 averaged over rounds, minus the matched control game's |
| Competitive share, market (arm - control) | Per pair, the rule-arm game's competitive share (share of scored firm-rounds that undercut the lowest rival quote of the previous round, or both at 1.00) minus the control game's |
| Competitive share, bound firm - control firms | Per pair, the bound firm's competitive share minus the mean over the control game's LLM firms |
| Competitive share, unbound firm(s) - control firms | Per pair, the mean competitive share of the unbound firm(s) of the rule-arm game minus the same control-firm mean |
| Competitive share, bound - unbound (same game) | Per pair, the bound firm's competitive share minus the unbound firm(s)' mean, in the same rule-arm game |

**Legend: every code on each axis** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

**Rows (y-axis): measure (rows 1-2 whole market, rows 3-5 per firm: bound firm, unbound firm(s), bound minus unbound; defined in the Row label table above)**

| Slug | Meaning |
|---|---|
| price_index | price index |
| competitive_share | competitive share (U16) |

**Panels: rule arm and its control (left panel: m-asym vs headline-chat; right panel: n3-ethics vs n3-group)**

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-ethics | three firms, one told not to coordinate |
| n3-group | three firms, private chat |

**Colour / value (metric)**

| Metric | Meaning | Direction |
|---|---|---|
| price_index | (market price - 1) / 2: 0 at the competitive 1.00, 1 at the 3.00 monopoly price. Higher = more collusive. | higher = more collusive (on the red/green maps: red end) |
| competitive_share | Share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00. Higher = more competitive. | higher = more competitive (on the red/green maps: green end) |

Colour scale: not a colour map: dot colour = thinking mode (blue = t0, orange = t1); the x-axis is the rule arm minus its control, bars = 95% CI.

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
| private | private chat |

</small>

## Tables (rule arm minus matched control; "control mean" = matched control mean; "bound minus unbound" rows compare the two firm groups of the same game)

*What this section compares: for each rule arm, the rule-arm game against its matched control with the same wording, seed, penalty point 3 and thinking mode, at market level and per firm, in the neutral run (primary) and the anchored run (check). Arms, runs and every term are defined in the table under the figure above and in the Terms under each table.*

### Market level, neutral (primary)

*This table shows, for the whole market (both or all three firms together) in the neutral run, how the game's price index and competitive share differ between the rule arm and its matched control, by thinking mode.*

| rule arm | measure | mode | n pairs | control mean | rule-arm mean | rule arm minus control [95% CI] |
|---|---|---|---|---|---|---|
| m-asym | price index | off | 20 | 0.610 | 0.564 | -0.046 [-0.157, +0.068] |
| m-asym | competitive share | off | 20 | 0.125 | 0.162 | +0.038 [-0.141, +0.213] |
| m-asym | price index | on | 20 | 0.765 | 0.758 | -0.007 [-0.082, +0.070] |
| m-asym | competitive share | on | 20 | 0.011 | 0.064 | +0.053 [-0.007, +0.132] |
| n3-ethics | price index | off | 20 | 0.597 | 0.613 | +0.016 [-0.169, +0.190] |
| n3-ethics | competitive share | off | 20 | 0.013 | 0.050 | +0.037 [-0.021, +0.115] |
| n3-ethics | price index | on | 20 | 0.675 | 0.691 | +0.016 [-0.070, +0.100] |
| n3-ethics | competitive share | on | 20 | 0.004 | 0.103 | +0.100 [+0.028, +0.207] |

<!-- ci-forest:1 -->
![CI forest chart for the table above (Market level, neutral (primary)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci01.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| price index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| competitive share | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |

</small>
<!-- /ci-forest -->

<small>

**Terms for the table above.**

| Column / term | Meaning |
|---|---|
| rule arm | m-asym (ethics rule on 1 of 2 firms) or n3-ethics (rule on 1 of 3 firms); defined in the definitions table under the figure |
| measure: price index | Game mean over rounds of (market price - 1) / 2; 0 = competitive 1.00, 1 = monopoly 3.00; lower = less collusion |
| measure: competitive share | Share of scored firm-rounds (all LLM firms, round 2 on) in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00; higher = less collusion (undercutting) |
| mode | Thinking off / on (Qwen3-32B reasoning mode) |
| n pairs | Number of (wording, seed) pairs with both games finished |
| control mean | Mean over those pairs of the matched control game's value (headline-chat for m-asym, n3-group for n3-ethics) |
| rule-arm mean | Same for the rule arm's game |
| rule arm minus control [95% CI] | Mean paired difference (rule-arm value minus control value) with the 95% bootstrap CI over the pairs, in index or share units |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| n3-ethics | three firms, one told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-group | three firms, private chat |
| neutral | evenly spaced example prices |
| t0 | thinking off |
| t1 | thinking on |
| p3 | penalty point 3: fine 500 (ripe middle point) |
| price_index | price index |
| competitive_share | competitive share (U16) |

</small>

### Per firm, neutral (primary)

*This table shows, per firm, in the neutral run, whether the bound firm competes differently from the control firms, whether the unbound firm(s) do, and whether the bound and unbound firms differ within the same game; competitive share and the firm's own price index.*

| rule arm | measure | mode | n pairs | control mean | rule-arm mean | rule arm minus control [95% CI] |
|---|---|---|---|---|---|---|
| m-asym | comp. share: bound firm vs control firms | off | 20 | 0.125 | 0.142 | +0.018 [-0.179, +0.211] |
| m-asym | comp. share: unbound others vs control firms | off | 20 | 0.125 | 0.182 | +0.058 [-0.133, +0.261] |
| m-asym | comp. share: bound minus unbound | off | 20 | 0.182 | 0.142 | -0.040 [-0.208, +0.122] |
| m-asym | firm price index: bound vs control firms | off | 20 | 0.615 | 0.580 | -0.035 [-0.149, +0.080] |
| m-asym | firm price index: unbound others vs control firms | off | 20 | 0.615 | 0.604 | -0.011 [-0.120, +0.099] |
| m-asym | firm price index: bound minus unbound | off | 20 | 0.604 | 0.580 | -0.024 [-0.064, +0.011] |
| m-asym | comp. share: bound firm vs control firms | on | 20 | 0.011 | 0.062 | +0.051 [-0.017, +0.164] |
| m-asym | comp. share: unbound others vs control firms | on | 20 | 0.011 | 0.066 | +0.055 [-0.015, +0.166] |
| m-asym | comp. share: bound minus unbound | on | 20 | 0.066 | 0.062 | -0.004 [-0.150, +0.146] |
| m-asym | firm price index: bound vs control firms | on | 20 | 0.768 | 0.761 | -0.007 [-0.082, +0.070] |
| m-asym | firm price index: unbound others vs control firms | on | 20 | 0.768 | 0.758 | -0.010 [-0.085, +0.070] |
| m-asym | firm price index: bound minus unbound | on | 20 | 0.758 | 0.761 | +0.002 [-0.000, +0.007] |
| n3-ethics | comp. share: bound firm vs control firms | off | 20 | 0.013 | 0.100 | +0.087 [-0.021, +0.242] |
| n3-ethics | comp. share: unbound others vs control firms | off | 20 | 0.013 | 0.025 | +0.012 [-0.028, +0.072] |
| n3-ethics | comp. share: bound minus unbound | off | 20 | 0.025 | 0.100 | +0.075 [+0.000, +0.200] |
| n3-ethics | firm price index: bound vs control firms | off | 20 | 0.602 | 0.613 | +0.011 [-0.174, +0.184] |
| n3-ethics | firm price index: unbound others vs control firms | off | 20 | 0.602 | 0.638 | +0.036 [-0.124, +0.192] |
| n3-ethics | firm price index: bound minus unbound | off | 20 | 0.638 | 0.613 | -0.025 [-0.061, -0.000] |
| n3-ethics | comp. share: bound firm vs control firms | on | 20 | 0.004 | 0.126 | +0.122 [+0.038, +0.235] |
| n3-ethics | comp. share: unbound others vs control firms | on | 20 | 0.004 | 0.092 | +0.088 [+0.019, +0.197] |
| n3-ethics | comp. share: bound minus unbound | on | 20 | 0.092 | 0.126 | +0.034 [-0.003, +0.076] |
| n3-ethics | firm price index: bound vs control firms | on | 20 | 0.675 | 0.692 | +0.017 [-0.069, +0.102] |
| n3-ethics | firm price index: unbound others vs control firms | on | 20 | 0.675 | 0.697 | +0.022 [-0.065, +0.108] |
| n3-ethics | firm price index: bound minus unbound | on | 20 | 0.697 | 0.692 | -0.005 [-0.014, +0.000] |

<!-- ci-forest:2 -->
![CI forest chart for the table above (Per firm, neutral (primary)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci02.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| rule arm minus control [95% CI] | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |
| firm price index: bound vs control firms | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| firm price index: unbound others vs control firms | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| firm price index: bound minus unbound | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

<small>

**Terms for the table above.** Columns as in the market-level table, with these row measures (one game's firms are averaged within each group first, then the pair difference is taken). In every "bound minus unbound" row the **control mean column holds the unbound firm(s) of the same rule-arm game** and the **rule-arm mean column holds the bound firm**; the difference is bound minus unbound.

| Row measure | Meaning |
|---|---|
| comp. share: bound firm vs control firms | Bound firm's competitive share (as defined above, for that one firm) minus the mean competitive share of the LLM firms of the matched control game |
| comp. share: unbound others vs control firms | Mean competitive share of the unbound firm(s) of the rule-arm game minus the same control-firm mean |
| comp. share: bound minus unbound | Bound firm's competitive share minus the unbound firm(s)' mean competitive share, same game |
| firm price index: bound vs control firms | Firm's own price index = (the firm's mean quote over the game's rounds - 1) / 2, for the bound firm, minus the mean over the control game's LLM firms |
| firm price index: unbound others vs control firms | The same for the unbound firm(s) |
| firm price index: bound minus unbound | Bound firm's price index minus the unbound firm(s)' mean, same game |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| n3-ethics | three firms, one told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-group | three firms, private chat |
| neutral | evenly spaced example prices |
| t0 | thinking off |
| t1 | thinking on |
| p3 | penalty point 3: fine 500 (ripe middle point) |
| price_index | price index |
| competitive_share | competitive share (U16) |

</small>

### Market level, anchored (check)

*This table repeats the market-level comparison in the anchored run (the check): the same arms, with the payoff table printing 1.54, 2.09 and 3.00 as worked examples.*

| rule arm | measure | mode | n pairs | control mean | rule-arm mean | rule arm minus control [95% CI] |
|---|---|---|---|---|---|---|
| m-asym | price index | off | 20 | 0.459 | 0.361 | -0.098 [-0.237, +0.032] |
| m-asym | competitive share | off | 20 | 0.050 | 0.064 | +0.014 [-0.116, +0.119] |
| m-asym | price index | on | 20 | 0.512 | 0.492 | -0.020 [-0.078, +0.035] |
| m-asym | competitive share | on | 20 | 0.005 | 0.112 | +0.107 [+0.048, +0.180] |
| n3-ethics | price index | off | 20 | 0.399 | 0.405 | +0.006 [-0.085, +0.088] |
| n3-ethics | competitive share | off | 20 | 0.058 | 0.000 | -0.058 [-0.162, -0.001] |
| n3-ethics | price index | on | 20 | 0.448 | 0.484 | +0.036 [-0.045, +0.115] |
| n3-ethics | competitive share | on | 20 | 0.002 | 0.059 | +0.057 [+0.017, +0.105] |

<!-- ci-forest:3 -->
![CI forest chart for the table above (Market level, anchored (check)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci03.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| price index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| competitive share | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |

</small>
<!-- /ci-forest -->

<small>

**Terms for the table above.**

| Column / term | Meaning |
|---|---|
| rule arm | m-asym (ethics rule on 1 of 2 firms) or n3-ethics (rule on 1 of 3 firms); defined in the definitions table under the figure |
| measure: price index | Game mean over rounds of (market price - 1) / 2; 0 = competitive 1.00, 1 = monopoly 3.00; lower = less collusion |
| measure: competitive share | Share of scored firm-rounds (all LLM firms, round 2 on) in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00; higher = less collusion (undercutting) |
| mode | Thinking off / on (Qwen3-32B reasoning mode) |
| n pairs | Number of (wording, seed) pairs with both games finished |
| control mean | Mean over those pairs of the matched control game's value (headline-chat for m-asym, n3-group for n3-ethics) |
| rule-arm mean | Same for the rule arm's game |
| rule arm minus control [95% CI] | Mean paired difference (rule-arm value minus control value) with the 95% bootstrap CI over the pairs, in index or share units |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| n3-ethics | three firms, one told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-group | three firms, private chat |
| anchored | payoff table prints the 2.09 theory price |
| t0 | thinking off |
| t1 | thinking on |
| p3 | penalty point 3: fine 500 (ripe middle point) |
| price_index | price index |
| competitive_share | competitive share (U16) |

</small>

### Per firm, anchored (check)

*This table repeats the per-firm comparison in the anchored run (the check). In this run the bound firm carries the text `no_coordinate_rule` and the unbound firm(s) carry plain private chat.*

| rule arm | measure | mode | n pairs | control mean | rule-arm mean | rule arm minus control [95% CI] |
|---|---|---|---|---|---|---|
| m-asym | comp. share: bound firm vs control firms | off | 20 | 0.050 | 0.060 | +0.010 [-0.140, +0.157] |
| m-asym | comp. share: unbound others vs control firms | off | 20 | 0.050 | 0.068 | +0.018 [-0.129, +0.162] |
| m-asym | comp. share: bound minus unbound | off | 20 | 0.068 | 0.060 | -0.008 [-0.155, +0.142] |
| m-asym | firm price index: bound vs control firms | off | 20 | 0.462 | 0.364 | -0.098 [-0.238, +0.027] |
| m-asym | firm price index: unbound others vs control firms | off | 20 | 0.462 | 0.376 | -0.086 [-0.228, +0.040] |
| m-asym | firm price index: bound minus unbound | off | 20 | 0.376 | 0.364 | -0.012 [-0.039, +0.004] |
| m-asym | comp. share: bound firm vs control firms | on | 20 | 0.005 | 0.110 | +0.105 [+0.043, +0.175] |
| m-asym | comp. share: unbound others vs control firms | on | 20 | 0.005 | 0.114 | +0.109 [+0.033, +0.222] |
| m-asym | comp. share: bound minus unbound | on | 20 | 0.114 | 0.110 | -0.003 [-0.116, +0.087] |
| m-asym | firm price index: bound vs control firms | on | 20 | 0.516 | 0.493 | -0.023 [-0.076, +0.029] |
| m-asym | firm price index: unbound others vs control firms | on | 20 | 0.516 | 0.493 | -0.022 [-0.077, +0.030] |
| m-asym | firm price index: bound minus unbound | on | 20 | 0.493 | 0.493 | -0.000 [-0.001, +0.000] |
| n3-ethics | comp. share: bound firm vs control firms | off | 20 | 0.058 | 0.000 | -0.058 [-0.163, -0.001] |
| n3-ethics | comp. share: unbound others vs control firms | off | 20 | 0.058 | 0.000 | -0.058 [-0.162, -0.001] |
| n3-ethics | comp. share: bound minus unbound | off | 20 | 0.000 | 0.000 | +0.000 [+0.000, +0.000] |
| n3-ethics | firm price index: bound vs control firms | off | 20 | 0.403 | 0.405 | +0.003 [-0.086, +0.085] |
| n3-ethics | firm price index: unbound others vs control firms | off | 20 | 0.403 | 0.407 | +0.004 [-0.084, +0.085] |
| n3-ethics | firm price index: bound minus unbound | off | 20 | 0.407 | 0.405 | -0.001 [-0.004, +0.000] |
| n3-ethics | comp. share: bound firm vs control firms | on | 20 | 0.002 | 0.080 | +0.078 [+0.020, +0.147] |
| n3-ethics | comp. share: unbound others vs control firms | on | 20 | 0.002 | 0.049 | +0.047 [+0.013, +0.085] |
| n3-ethics | comp. share: bound minus unbound | on | 20 | 0.049 | 0.080 | +0.032 [+0.004, +0.068] |
| n3-ethics | firm price index: bound vs control firms | on | 20 | 0.448 | 0.484 | +0.036 [-0.043, +0.111] |
| n3-ethics | firm price index: unbound others vs control firms | on | 20 | 0.448 | 0.485 | +0.036 [-0.043, +0.114] |
| n3-ethics | firm price index: bound minus unbound | on | 20 | 0.485 | 0.484 | -0.000 [-0.001, +0.000] |

<!-- ci-forest:4 -->
![CI forest chart for the table above (Per firm, anchored (check)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci04.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| rule arm minus control [95% CI] | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |
| firm price index: bound vs control firms | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| firm price index: unbound others vs control firms | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| firm price index: bound minus unbound | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

<small>

**Terms for the table above.** Columns as in the market-level table, with these row measures (one game's firms are averaged within each group first, then the pair difference is taken). In every "bound minus unbound" row the **control mean column holds the unbound firm(s) of the same rule-arm game** and the **rule-arm mean column holds the bound firm**; the difference is bound minus unbound.

| Row measure | Meaning |
|---|---|
| comp. share: bound firm vs control firms | Bound firm's competitive share (as defined above, for that one firm) minus the mean competitive share of the LLM firms of the matched control game |
| comp. share: unbound others vs control firms | Mean competitive share of the unbound firm(s) of the rule-arm game minus the same control-firm mean |
| comp. share: bound minus unbound | Bound firm's competitive share minus the unbound firm(s)' mean competitive share, same game |
| firm price index: bound vs control firms | Firm's own price index = (the firm's mean quote over the game's rounds - 1) / 2, for the bound firm, minus the mean over the control game's LLM firms |
| firm price index: unbound others vs control firms | The same for the unbound firm(s) |
| firm price index: bound minus unbound | Bound firm's price index minus the unbound firm(s)' mean, same game |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| n3-ethics | three firms, one told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-group | three firms, private chat |
| anchored | payoff table prints the 2.09 theory price |
| t0 | thinking off |
| t1 | thinking on |
| p3 | penalty point 3: fine 500 (ripe middle point) |
| price_index | price index |
| competitive_share | competitive share (U16) |

</small>

In the anchored run the bound firm is the one given the `no_coordinate_rule` text (the anchored version of the ethics rule); in the neutral run it is the `rule_ethics` firm. Unbound firms carry the placebo text (neutral) or plain private chat (anchored). Game-level numbers are from run.csv and match `levers.py` to within 0.001.

## Standard metrics

*What this section compares: the same two rule-arm-minus-control contrasts as above, on all five standard metrics side by side, in both runs.*

Every main contrast (arm minus matched control, penalty point 3), neutral run, with the anchored run as the check; thinking off and on separately. Game-level values from the Step 1 run.csv. Average absolute spread: the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled (1.00 = competitive floor, 3.00 = monopoly price; lower = less collusion). Price index: (market price - 1)/2, from 0 (competitive) to 1 (monopoly 3.00) (lower = less collusion). Profit gain index: (profit - competitive) / (monopoly - competitive), 0 = competitive profit, 1 = monopoly profit (lower = less collusion). Competitive share (U16): share of firm-rounds that are competitive, meaning the firm quotes below the lowest rival's previous-round quote, or both are at 1.00 (higher = less collusion). Matching share: share of firm-rounds in which the firm's quote equals the lowest rival's previous-round quote, above 1.00 (higher = more coordination; the coordination signature). The five are analysed separately, never blended. Each cell is the mean paired difference with its 95% percentile bootstrap CI over the paired (wording, seed) pairs (10,000 resamples). Means, counts and CIs: `standard_metrics.csv`; script: `standard_metrics.py`.

| contrast | run | mode | n pairs | Average absolute spread | Price index | Profit gain index | Competitive share (U16) | Matching share |
|---|---|---|---|---|---|---|---|---|
| m-asym vs private chat | neutral | off | 20 | -0.092 [-0.314, +0.132] | -0.046 [-0.160, +0.066] | -0.023 [-0.158, +0.114] | +0.038 [-0.140, +0.217] | -0.149 [-0.367, +0.075] |
| m-asym vs private chat | neutral | on | 20 | -0.014 [-0.165, +0.138] | -0.007 [-0.084, +0.068] | +0.021 [-0.015, +0.061] | +0.053 [-0.007, +0.130] | -0.072 [-0.161, +0.005] |
| n3-ethics vs 3-firm chat | neutral | off | 20 | +0.032 [-0.328, +0.380] | +0.016 [-0.168, +0.190] | +0.011 [-0.192, +0.203] | +0.037 [-0.021, +0.117] | -0.026 [-0.196, +0.118] |
| n3-ethics vs 3-firm chat | neutral | on | 20 | +0.032 [-0.137, +0.199] | +0.016 [-0.069, +0.096] | +0.008 [-0.057, +0.070] | +0.100 [+0.028, +0.211] | -0.175 [-0.293, -0.084] |
| m-asym vs private chat | anchored | off | 20 | -0.196 [-0.476, +0.056] | -0.098 [-0.234, +0.030] | -0.111 [-0.268, +0.047] | +0.014 [-0.117, +0.118] | -0.052 [-0.237, +0.139] |
| m-asym vs private chat | anchored | on | 20 | -0.040 [-0.151, +0.073] | -0.020 [-0.076, +0.037] | -0.014 [-0.076, +0.050] | +0.107 [+0.048, +0.181] | -0.152 [-0.276, -0.033] |
| n3-ethics vs 3-firm chat | anchored | off | 20 | +0.012 [-0.167, +0.176] | +0.006 [-0.082, +0.090] | +0.008 [-0.115, +0.118] | -0.058 [-0.162, -0.001] | +0.118 [+0.006, +0.259] |
| n3-ethics vs 3-firm chat | anchored | on | 20 | +0.072 [-0.087, +0.227] | +0.036 [-0.042, +0.114] | +0.042 [-0.053, +0.134] | +0.057 [+0.017, +0.104] | -0.101 [-0.246, +0.050] |

<!-- ci-forest:5 -->
![CI forest chart for the table above (Standard metrics): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci05.png)

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

**Terms for the standard-metrics table.** Each row is one contrast, analysed on the five standard metrics separately.

| Label | Meaning |
|---|---|
| contrast "m-asym vs private chat" | Per (wording, seed) pair, the m-asym game (two LLM firms, private chat, penalty point 3; one firm gets "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently.", the other the placebo "The office building downtown has a canteen and a small front library.") minus the `headline-chat` game (two LLM firms, private chat, penalty point 3, no extra sentence) |
| contrast "n3-ethics vs 3-firm chat" | Per pair, the n3-ethics game (three LLM firms, private group chat, penalty point 3; one firm gets the same rule, the other two the same placebo) minus the `n3-group` game (three LLM firms, private group chat, penalty point 3, no extra sentence) |
| run / mode | Neutral run (payoff table shows evenly spaced example prices 1.00 to 4.00) or anchored run (examples 1.54, 2.09, 3.00); thinking off / on (Qwen3-32B reasoning mode), analysed separately |
| n pairs | Number of (wording, seed) pairs (5 prompt paraphrases times 4 seeds) with both games finished |
| each cell | Mean over the pairs of (rule-arm game minus control game), with the 95% percentile bootstrap CI over the pairs in brackets; a CI that excludes zero is a clear difference |

| Column | Meaning |
|---|---|
| Average absolute spread | Mean market quote (the half-spread) over a game's rounds, raw units 1.00 to 5.00, not rescaled; 1.00 = competitive floor, 3.00 = monopoly; difference in quote units (run.csv `market_price_mean`) |
| Price index | (market price - 1) / 2 averaged over a game's rounds, 0 = competitive 1.00, 1 = monopoly 3.00; difference in index units |
| Profit gain index | (mean profit per firm per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit; difference in index units |
| Competitive share (U16) | Share of scored firm-rounds in which the firm quotes below the lowest rival's quote of the previous round, or both are at 1.00; round 1 is not scored; difference in share units |
| Matching share | Share of scored firm-rounds in which the firm's quote equals the lowest rival's previous-round quote (within half a tick), above 1.00; the coordination signature; competitive + matching + above-rival shares sum to 1; difference in share units |

**Legend: every slug and code shown** (definitions from the shared glossary `tools/analysis_style/arm_glossary.csv`).

| Slug | Meaning |
|---|---|
| m-asym | only one firm told not to coordinate |
| n3-ethics | three firms, one told not to coordinate |
| headline-chat | private chat, no other lever |
| n3-group | three firms, private chat |
| neutral | evenly spaced example prices |
| anchored | payoff table prints the 2.09 theory price |
| t0 | thinking off |
| t1 | thinking on |
| p3 | penalty point 3: fine 500 (ripe middle point) |

</small>

