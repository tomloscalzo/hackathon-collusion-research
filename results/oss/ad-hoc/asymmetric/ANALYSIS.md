# Asymmetric ethics rule on gpt-oss-20b: does binding one of two firms change prices?

**Verdict.** Giving one of two firms the rule "do not coordinate prices" (the other an unrelated placebo) changed nothing detectable on gpt-oss-20b (reasoning effort medium): price index -0.018 [-0.118, 0.089], 20 pairs, a bound of roughly +/-0.1. The rule-bound seat behaved like its unbound rival (mean quote difference +0.008 [-0.044, 0.058]).

## Orientation
Two firms quote a half-spread (1.00 competitive floor to 5.00; 3.00 monopoly; 2.09 the theory's sustainable collusive level at penalty point 3, never printed in the neutral run). The lowest quote wins 70% of customers; a tick is 0.01; planned 15 rounds. gpt-oss runs at one reasoning effort (medium). The *bound* firm gets the rule sentence; the *rival* gets a placebo about a canteen.

## Question, arms, pairing
Does one rule-bound firm drag its rival down or get exploited? Paired on (wording, seed), 20 pairs, p3, exploratory.

| Arm | Description |
|---|---|
| m-asym: two firms, one bound by the ethics rule, the other a placebo | private chat; rule on one seat, placebo text on the other |
| headline-chat: two firms, private chat, no extra text (control) | the p3 headline cell; no placebo, so a placebo effect cannot be separated out |

## Standard metrics (m-asym minus headline-chat)
| metric | gpt-oss-20b diff [CI] (arm / control) |
|---|---|
| Average absolute spread | -0.036 [-0.227, 0.201] (2.189 / 2.226) |
| Price index | -0.018 [-0.118, 0.089] (0.595 / 0.613) |
| Profit gain index | -0.018 [-0.122, 0.100] (0.786 / 0.804) |
| Competitive share | +0.008 [-0.119, 0.117] (0.448 / 0.440) |
| Matching share | -0.046 [-0.168, 0.094] (0.329 / 0.376) |

<!-- ci-forest:1 -->
![CI forest chart for the table above (Standard metrics (m-asym minus headline-chat)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci01.png)

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
| Competitive share | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |
| Matching share | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

All are nulls.

## Per-seat (gpt-oss, 20 pairs)
| comparison | competitive share diff [CI] | mean quote diff [CI] | profit gain diff [CI] |
|---|---|---|---|
| bound minus unbound | +0.097 [-0.028, 0.239] | +0.008 [-0.044, 0.058] | +0.092 [-0.023, 0.212] |
| bound minus control firms | +0.056 [-0.105, 0.189] | +0.014 [-0.146, 0.218] | +0.028 [-0.098, 0.175] |
| unbound minus control firms | -0.041 [-0.170, 0.073] | +0.006 [-0.170, 0.218] | -0.064 [-0.183, 0.087] |

<!-- ci-forest:2 -->
![CI forest chart for the table above (Per-seat (gpt-oss, 20 pairs)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci02.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| competitive share diff [CI] | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |
| mean quote diff [CI] | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |
| profit gain diff [CI] | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

| Term | Meaning |
|---|---|
| Bound / unbound | seat with the rule / seat with the placebo |
| Metrics | spread = mean half-spread; price index = (price-1)/2; profit gain = share of the way from competitive to monopoly profit; competitive share = firm-rounds undercutting or at 1.00; matching share = firm-rounds matching the rival's previous quote above the floor |

## Empty-talk covariate
Mean "done"-read empty talk count: headline-chat 0.40 (6 of 20 games), m-asym 0.50 (6). Dropping those pairs leaves 12: price index -0.056 [-0.176, 0.048]; competitive share +0.109 [0.006, 0.198]; matching share -0.177 [-0.268, -0.087]. Same sign as the full sample; the shift toward undercutting is small and appears only in this subset (exploratory).

## Limits
MDE (80% power, price index) about 0.15 on gpt-oss; an effect smaller than that could hide. Per-seat differences use 20 pairs and are inconclusive.

## Sub-question
1.5: a single rule-bound firm of two is not a lever. (Contrast with ethics-rule, where one of three lowered gpt-oss prices.)

## Comparison with Qwen3-32B
How the second model compares. Qwen3-32B (thinking on) is null too. gpt-oss medium reasoning effort is compared with Qwen thinking on; these are not the same axis, and magnitudes are confounded with baseline level.

Standard metrics, m-asym minus headline-chat, Qwen3-32B thinking on (same metric definitions as the legend below):

| metric | Qwen3-32B thinking on diff [CI] |
|---|---|
| Average absolute spread | -0.014 [-0.157, 0.146] |
| Price index | -0.007 [-0.084, 0.074] |
| Profit gain index | +0.021 [-0.015, 0.062] |
| Competitive share | +0.053 [-0.007, 0.129] |
| Matching share | -0.072 [-0.159, 0.007] |

<!-- ci-forest:3 -->
![CI forest chart for the table above (Comparison with Qwen3-32B): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci03.png)

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
| Competitive share | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |
| Matching share | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

Replicates? Price and matching: sign same, magnitude similar. Competitive share: sign same, smaller on gpt-oss (Qwen near zero base). All are nulls.

Per-seat: Qwen bound minus unbound competitive share: -0.004 [-0.158, 0.142].

Power: MDE (80% power, price index) is 0.11 on Qwen, against about 0.15 on gpt-oss; an effect smaller than that could hide.

| Term | Meaning |
|---|---|
| Bound / unbound | seat with the rule / seat with the placebo |
| Metrics | spread = mean half-spread; price index = (price-1)/2; profit gain = share of the way from competitive to monopoly profit; competitive share = firm-rounds undercutting or at 1.00; matching share = firm-rounds matching the rival's previous quote above the floor |

Created by Claude at the prompting of the repository owner.
