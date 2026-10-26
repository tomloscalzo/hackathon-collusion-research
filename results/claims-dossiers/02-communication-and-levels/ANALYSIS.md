# Dossier 02: communication and baseline levels across models

*Rigorous ad hoc stage, claims dossiers. Compiled by the coordinator from the dossier agent's verified findings; the tables are in `tables/` and the scripts in `scripts/`.*

**Orientation.** In this game two LLM "market makers" each quote a **half-spread** (the distance from the mid-price to their bid and ask) from 1.00 (competitive: costs covered, no excess profit) to 5.00, in 0.01 ticks; 3.00 is the monopoly price, 70% of customers go to the lowest quote, a regulator investigates more often at higher prices (penalty points p1 light to p5 heavy), and games last 7 to 20 rounds. This dossier asks four things: how collusive each model is in the basic cells (communication x penalty point); whether private chat raises prices on both models; whether the cell chosen in advance for the side arms really is the most collusive; and whether empty chat replies on gpt-oss distort the chat effect. The arms are the two headline conditions, no chat and private chat (plus, on Qwen only, chat that the regulator reads, public chat, and chat described as unmonitored). Data: the neutral run (evenly spaced example prices); gpt-oss-20b 100 headline games, Qwen3-32B 480 headline games plus 80 notice-arm games; 20 (wording, seed) pairs per cell.

> **How to read the metrics** (per game; source columns in the game table).
> - **Average absolute spread** (`market_price_mean`): the mean market quote, 1.00 to 5.00. Higher = more collusive.
> - **Price index** (`price_index`) = (market price - 1) / 2; 0 = competitive, 1 = monopoly. Example: a market price of 2.00 every round gives (2.00 - 1) / 2 = 0.50. Higher = more collusive.
> - **Profit gain index** (`profit_gain_index`) = (profit - competitive profit) / (monopoly profit - competitive profit). Higher = more collusive.
> - **Competitive share, U16** (`competitive_share`): share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00. Higher = more competitive.
> - **Matching share** (`matching_share`): share of firm-rounds in which the firm quotes exactly the lowest rival quote of the previous round, above 1.00. Higher = more collusive.

<small>

| Term | Plain-English definition |
|---|---|
| headline-tacit: no chat | Two firms, no messages between rounds |
| headline-chat: private chat | Two firms exchange up to 7 private messages of up to 150 words per round |
| headline-monitored: chat read by the regulator | As private chat, plus a notice that the regulator reads the messages (Qwen only) |
| m-pub: public chat | Chat said to be published to customers and the regulator (Qwen only, p3) |
| m-mon0: chat said to be unmonitored | Chat with the notice "no one monitors your messages" (Qwen only, p3) |
| p1 / p3 / p4 / p5 | Penalty points: fine 100 / 500 / 1000 / 2000; theory's sustainable collusive level theta* 0.703 / 0.546 / 0.325 / 0 |
| t1 / t0: thinking on / off | Whether Qwen reasons in a hidden chain of thought before replying; gpt-oss runs only at medium reasoning effort, so model and mode are confounded in every cross-model comparison |
| cell | One (communication, penalty point) combination in one model mode |
| pair | One (wording, seed) combination run in both cells being compared |
| unpaired across models | Cross-model differences resample each model's games independently (a game-level bootstrap), with a label-permutation p |
| CI, p, Holm, MDE | 95% percentile bootstrap (10,000 draws) over pairs (within model) or games (across models); exact sign-flip p over all 2^20 sign patterns; Holm within the named family; minimum detectable effect = 2.8 x SE |
| truncation rerun | A rerun of a game in which a model reply hit its token cap, replacing the truncated original |

</small>

## 0. Data note: a provisional Qwen table

The Qwen game table first used in this stage (the Step 1 neutral build) is provisional: four of its thinking-on no-chat games (p3 to p5) are still the truncated originals, flagged `rerun_missing`. The later final build has those reruns and reproduces the frozen numbers exactly (pooled chat minus no chat, thinking on, profit gain index +0.148 [0.099, 0.196] against the frozen +0.148 [0.100, 0.195]). This dossier uses the final build; the provisional one is kept as a sensitivity (`tables_sensitivity_qwen_step1_table/`). The two differ only in the Qwen thinking-on no-chat cells at p3 to p5, by 0.01 to 0.03. **Three Qwen ledger values came from the provisional build and are corrected here:** pooled chat effect on profit gain (thinking on) +0.165 becomes **+0.148**; the p5 chat effect on profit gain +0.438 becomes **+0.408**; the p5 chat effect on price index +0.355 becomes **+0.335**. The two gpt-oss builds (`final_t1`, `final_t2`) are identical on all five metrics.

## 1. Levels by cell (G-levels)

**Claim, restated.** With Qwen thinking on as the comparator, gpt-oss-20b prices well below Qwen3-32B at the light penalty, both without and with chat; without chat at p5 the two are indistinguishable. gpt-oss undercuts far more and matches far less in every cell except no-chat p5.

![fig: levels by penalty point](fig_levels_by_penalty.png)

*Figure 1. Cell means of each of the five metrics (one panel per metric) by penalty point, neutral run, n = 20 games per point; bars are 95% game-bootstrap intervals. Colour = model and mode (blue gpt-oss-20b medium effort, red Qwen3-32B thinking on, orange Qwen3-32B thinking off); solid circles = private chat, dashed squares = no chat; points are offset slightly sideways. gpt-oss has no p3/p4 no-chat or p4 chat cells, so its dashed line joins p1 to p5 directly: the line between p1 and p5 is an interpolation, not data. Red here marks a model series, not collusion (this is not a heat map).*

<small>

| Axis / element | Codes and meaning |
|---|---|
| Columns (x-axis) | Penalty point p1 / p3 / p4 / p5 = fine 100 / 500 / 1000 / 2000 |
| Rows (y-axis), one panel per metric | Average absolute spread (1.00 to 5.00), price index (0 to 1), profit gain index, competitive share, matching share; for competitive share higher = more competitive, for the others higher = more collusive |
| Series colour | gpt-oss-20b (medium effort); Qwen3-32B thinking on (t1); Qwen3-32B thinking off (t0) |
| Series style | headline-chat: private chat (solid, circles); headline-tacit: no chat (dashed, squares) |

</small>

**Cell levels** (spread / price index / profit gain index / competitive share / matching share; 20 games each):

| Cell | gpt-oss | Qwen thinking on | Qwen thinking off |
|---|---|---|---|
| headline-tacit: no chat, p1 | 1.78 / 0.39 / 0.57 / 0.68 / 0.16 | 2.43 / 0.72 / 0.91 / 0.38 / 0.56 | 1.95 / 0.47 / 0.70 / 0.23 / 0.63 |
| headline-tacit: no chat, p5 | 1.39 / 0.19 / 0.28 / 0.67 / 0.16 | 1.41 / 0.20 / 0.28 / 0.64 / 0.19 | 1.84 / 0.42 / 0.59 / 0.25 / 0.62 |
| headline-chat: private chat, p1 | 2.15 / 0.57 / 0.77 / 0.43 / 0.41 | 2.69 / 0.85 / 0.95 / 0.01 / 0.98 | 2.24 / 0.62 / 0.80 / 0.05 / 0.94 |
| headline-chat: private chat, p3 | 2.23 / 0.61 / 0.80 / 0.44 / 0.38 | 2.53 / 0.77 / 0.92 / 0.01 / 0.97 | 2.22 / 0.61 / 0.78 / 0.13 / 0.84 |
| headline-chat: private chat, p5 | 1.85 / 0.42 / 0.58 / 0.46 / 0.33 | 2.08 / 0.54 / 0.69 / 0.14 / 0.83 | 2.34 / 0.67 / 0.86 / 0.07 / 0.88 |

**gpt-oss minus Qwen thinking on** (unpaired game bootstrap; Holm family = 10 price and profit-gain tests per comparator):

| Cell | Price index | Profit gain index | Competitive share | Matching share |
|---|---|---|---|---|
| No chat p1 | -0.33 [-0.43, -0.22], Holm 0.001 | -0.34 [-0.46, -0.22], Holm 0.001 | +0.31 [+0.15, +0.45] | -0.40 [-0.55, -0.25] |
| Chat p1 | -0.27 [-0.39, -0.17] | -0.18 [-0.28, -0.09] | (large, see levels) | (large) |
| Chat p3 | -0.15 [-0.26, -0.05], Holm 0.044 | | | |
| No chat p5 | -0.01 [-0.15, +0.14] (MDE 0.21) | | | |
| Chat p5 | -0.12 [-0.27, +0.04] (unresolved) | | | |

<!-- ci-forest:1 -->
![CI forest chart for the table above (1. Levels by cell (G-levels)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci01.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Price index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Profit gain index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Competitive share | higher = more competitive (on the red/green maps: green end) | metric goes down (less competitive) | metric goes up (more competitive) |
| Matching share | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

**Against Qwen thinking off** the p1 price gaps are not resolved and are bounded below about 0.20 in size (no chat -0.09 [-0.20, +0.03]; chat -0.05 [-0.18, +0.08]); at p5 gpt-oss is lower than thinking off (no chat -0.224 [-0.38, -0.07], p 0.028; chat -0.25, Holm 0.004). A version paired across models on (wording, seed), which share horizons and investigation draws, gives the same no-chat p1 gap (-0.329 [-0.427, -0.227]). Confounds: Qwen's thinking modes also differ in temperature (0.6 on / 0.7 off) and token cap (8,192 / 400), and the two models are served differently. The competitive-share and matching-share gaps stay large against both modes (+0.31 to +0.45 and -0.40 to -0.60) in 9 of the 10 cell comparisons, the exception being no-chat p5 against thinking on. gpt-oss's price level sits between Qwen's two modes, so the thinking-mode confound is real.

The ledger's narrower gpt-oss intervals ([0.32, 0.46] against [0.29, 0.48] here) come from Step 2's bootstrap stratified by wording; the pair bootstrap here is the honest width.

**Strength.** Declared cells; the cross-model gap is descriptive and exploratory. **Status: confirmed, with a narrowed scope** (revised after adversarial review). "Far more competitive at p1" is confirmed against thinking on, and on the behaviour shares against both modes; "meet at the heavy penalty" is downgraded to "indistinguishable without chat, against thinking on (bound about +-0.15)". Sub-questions 1.2, 1.1.

- **Main text:** "Under the same prompts, gpt-oss-20b set lower prices than Qwen3-32B (thinking on) at the light penalty, with or without chat (no-chat price index 0.39 against 0.72), and undercut its rival far more often; at the heavy penalty the two models' no-chat prices were indistinguishable."
- **Appendix:** "Unpaired game bootstrap, 20 games per cell: price index -0.33 [-0.43, -0.22] without chat and -0.27 [-0.39, -0.17] with chat at p1, and -0.01 [-0.15, 0.14] without chat at p5. Against Qwen thinking off the p1 gaps are -0.09 and -0.05 (CIs include 0), so the comparison depends on reasoning mode, which is confounded with model."

## 2. Private chat raises prices (G-comm and the Qwen headline)

**Claim, restated.** Private chat raises prices, profit and matching, and lowers undercutting, on both models. The gpt-oss effect is not detectably larger than Qwen's, except that chat raises matching much less on gpt-oss.

Chat minus no chat, paired on (wording, seed), n = 20 pairs. Holm families: F1 = price and profit gain index per model mode (gpt-oss m = 4, Qwen m = 8); F2 = the other three metrics (m = 6 / 12).

| Model, penalty point | Spread | Price index | Profit gain index | Competitive share | Matching share |
|---|---|---|---|---|---|
| gpt-oss p1 | +0.37 | +0.19 [0.06, 0.31], Holm 0.020 | +0.20 [0.05, 0.35], Holm 0.021 | -0.25 | +0.25 |
| gpt-oss p5 | +0.46 | +0.23 [0.10, 0.35], Holm 0.016 | +0.30 [0.13, 0.46], Holm 0.016 | -0.22 | +0.17 |
| gpt-oss pooled p1, p5 | +0.41 | +0.21 [0.11, 0.29] | +0.25 | -0.24 | +0.21 |

<!-- ci-forest:2 -->
![CI forest chart for the table above (2. Private chat raises prices (G-comm and the Qwen headline)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci02.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Price index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Profit gain index | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |

</small>
<!-- /ci-forest -->

Every gpt-oss CI excludes 0. The raw sign-flip p values are higher than Step 2's (0.010 against 0.0004 for price at p1) because 5 of 20 pairs are negative (down to -0.43); they still pass Holm.

- **Qwen thinking on:** price index +0.13 / +0.13 / +0.08 / +0.34 at p1 / p3 / p4 / p5; profit gain +0.04 (Holm 0.15, near the ceiling) / +0.06 / +0.08 / +0.41; competitive share -0.31 to -0.50 and matching share +0.35 to +0.64, all Holm < 0.001. Pooled: profit gain **+0.148 [0.099, 0.196]**, price index +0.17 [0.12, 0.22].
- **Qwen thinking off:** resolved at p4 and p5 (price +0.25, Holm <= 0.017); p1 (+0.15, Holm 0.12) and p3 (+0.14, Holm 0.21) unresolved; pooled profit gain +0.189 [0.110, 0.272].

**Cross-model difference of chat effects.** The pooled numbers above cover different points (gpt-oss has no-chat cells only at p1 and p5). On the same points (p1 and p5), Qwen thinking on's chat effect is +0.233 [0.152, 0.316], and the difference paired across models, gpt-oss minus Qwen thinking on, is **-0.026 [-0.14, +0.09]** (against thinking off +0.007 [-0.15, +0.15]): the chat effect is the same size on both models within about +-0.14 price index. Unpaired, at p1 alone: price +0.06 [-0.09, 0.20], profit gain +0.16 [0.003, 0.31] (p 0.063, Holm 0.25, family F4 of 25 cross-model tests); at p5, matching -0.47 [-0.68, -0.24] (Holm 0.002), so chat raises matching much less on gpt-oss.

**Cross-wave caveat (gpt-oss).** gpt-oss private chat at p1 and p5 ran in submission waves 7-12, no chat in waves 13-16, and private chat at p3 in waves 107-112, so every gpt-oss chat-minus-no-chat contrast compares different waves. The same-prompt replicate offsets are similar for chat and no chat (dossier 04), so a prompt-build offset roughly cancels, but that offset was measured within waves and cannot rule out an effect of the wave itself.

**Robustness (gpt-oss), price index p1 / p5:** pooled with the same-prompt replicates +0.15 [0.09, 0.22] / +0.25; without pairs that contain empty replies +0.24 (11 pairs) / +0.24 (14); without truncated pairs +0.12 [0.02, 0.23] (13) / +0.24; without both +0.11 / +0.18, CIs including 0 (7 and 9 pairs, MDE about 0.26 to 0.31).

**Who reads the chat (Qwen only).** It made no detectable difference. Thinking on, pooled monitored minus private: price +0.007 [-0.037, 0.052], profit gain +0.022 [-0.026, 0.068]; at p3, public minus private -0.02 [-0.08, 0.04] and unmonitored minus private -0.01 [-0.09, 0.07]; all Holm 1.00 (family of 35 per mode). Thinking off, pooled monitored minus private +0.010 [-0.031, 0.051]. At p3 every chat type is above no chat (thinking on, price +0.10 to +0.13; competitive share -0.30, Holm <= 0.001). p3 levels, thinking on (price / competitive share): private 0.77 / 0.01, monitored 0.75 / 0.01, public 0.74 / 0.01, unmonitored 0.75 / 0.01, no chat 0.64 / 0.32.

**Strength.** Declared (the neutral-run communication x penalty curve and the frozen declared communication contrasts). **Status:** confirmed that chat raises prices and profit on both models; "by more at p1 on gpt-oss" downgraded to "no evidence of a difference" (same-point paired difference -0.026 [-0.14, +0.09]). Sub-questions 1.1, 3.1, 1.2; the monitored and public arms address 3.4.

- **Main text:** "Letting the two firms chat privately raised prices on both models (gpt-oss-20b price index +0.21 [0.11, 0.29], Qwen3-32B thinking on +0.17 [0.12, 0.22], pooled over penalty points), while telling Qwen that the regulator or the public could read the chat changed nothing detectable."
- **Appendix:** "gpt-oss-20b, 20 pairs: price index +0.19 [0.06, 0.31] at p1 and +0.23 [0.10, 0.35] at p5 (Holm 0.02, 0.016); profit gain +0.20 / +0.30; competitive share -0.25 / -0.22; matching share +0.25 / +0.17. Qwen thinking on +0.08 to +0.34 on price at every point. The effect survives pooling with same-prompt replicates and dropping empty-reply or truncated games; the chat effect is the same size on both models within about +-0.14 price index (gpt-oss minus Qwen thinking on, same penalty points, -0.03 [-0.14, +0.09]). gpt-oss chat and no-chat games ran in different submission waves."

## 3. The pre-declared cell (Q12-A1)

**Declared rule** (cell declaration recorded 2026-10-25 about 00:45 ET, before main-run analysis): rank the cells by profit gain; PASS if the chosen cell (private chat, p1) is first; CLOSE if the paired difference to the top cell has a CI including 0 or is below 0.05.

| Model, mode | Rank of chosen cell | Top cell (profit gain) | Chosen minus top [95% CI] | Verdict |
|---|---|---|---|---|
| gpt-oss (5 cells) | 2 | headline-chat: private chat p3, 0.804 (chosen 0.769) | -0.036 [-0.099, 0.023] | CLOSE |
| Qwen thinking on (12 cells) | 2 | headline-monitored: chat read by the regulator, p1, 0.959 (chosen 0.949) | -0.010 [-0.046, 0.031] | CLOSE |
| Qwen thinking off (12 cells) | 6 | headline-monitored: chat read by the regulator, p5, 0.899 (chosen 0.803) | -0.095 [-0.217, +0.001] | CLOSE |

<!-- ci-forest:3 -->
![CI forest chart for the table above (3. The pre-declared cell (Q12-A1)): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/ANALYSIS_ci03.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Chosen minus top [95% CI] | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |

</small>
<!-- /ci-forest -->

The thinking-off verdict is CLOSE only because the CI's upper end is +0.001: "close, not best". On gpt-oss the chosen cell (p1, waves 7-12) and the top cell (p3, waves 107-112) ran in different waves. On matching share the chosen cell ranks first for gpt-oss and for Qwen thinking off.

**Status: confirmed, as a stated limitation.** Sub-question 1.1. Other pre-declarations: the only dated pre-declarations for this design are this cell rule and the neutral-run analysis plan (the declared curve and contrasts). The scope document says "a few directional expectations are written down and dated before the first Track M run", but no such document was found.

- **Main text:** "The cell chosen in advance for the introspection arms ranked second (gpt-oss-20b, Qwen thinking on) or sixth (thinking off) by profit gain, within the declared 'close' margin."

## 4. Empty chat replies on gpt-oss (G-emptytalk)

Some gpt-oss chat turns come back empty and are read as silence. Across 640 gpt-oss chat games (every arm, excluding the replicate cells), the empty-reply count correlates weakly with less collusive play on every metric (Spearman / Pearson; source `tables/empty_talk_covariate.csv`):

| Metric | Spearman | Pearson | Partial Spearman given rounds played |
|---|---|---|---|
| Price index | -0.149 | -0.110 | -0.117 |
| Profit gain index | -0.143 | -0.079 | -0.110 |
| Competitive share (higher = more competitive) | +0.166 | +0.142 | +0.152 |
| Matching share | -0.215 | -0.208 | -0.203 |

- Mean price index 0.52 with no empty reply (n 414) against 0.46 with any (n 226).
- Empty-reply counts rise with rounds played (Spearman +0.14), and longer games price lower (-0.26), hence the partial correlations.
- Headline private chat only (60 games): price index Spearman -0.24, Pearson -0.26.
- Qwen has no empty-reply artefact, but its deliberate silent "done" turns show the same pattern (thinking on Spearman -0.23 / Pearson -0.21; thinking off Spearman -0.09), so "less talk, lower prices" is not specific to the artefact.
- Dropping the affected pairs does not weaken the chat effect (section 2).

**Strength.** Post hoc covariate, not randomised. **Status: confirmed as a robustness note (suggestive).** Sub-question 2.3.

- **Appendix:** "Across 640 gpt-oss chat games the empty-reply count correlates weakly with lower prices (price index Spearman -0.15, Pearson -0.11; partial given rounds played -0.12), like Qwen's deliberate silent turns (thinking on, Spearman -0.23); dropping affected pairs leaves the chat effect intact (+0.24 [0.07, 0.43] at p1, 11 pairs)."

## 5. Adversarial review

A fresh reviewer re-derived the headline numbers with independent scripts (all match) and asked for these changes, all made above: the empty-talk correlations are now quoted metric by metric on the 640-game set (the earlier summary's -0.165 was a mix of sets and metrics); "chat helps gpt-oss more" is restated as a bounded null on the same penalty points; the gpt-oss-below-Qwen-thinking-off result at no-chat p5 is reported; the cross-wave caveat is added for every gpt-oss chat-minus-no-chat and A1 contrast; the figure caption says the dashed gpt-oss line interpolates p3 and p4.

## 6. Files

| File | Contents |
|---|---|
| scripts/dossier02.py | Independent re-derivation of all levels and contrasts |
| scripts/fig_levels.py | Figure 1 |
| tables/cell_levels.csv | Five metrics by cell and model mode |
| tables/contrasts_within_model.csv | Chat minus no chat and other within-model contrasts with Holm families |
| tables/cross_model_levels.csv | gpt-oss minus Qwen, unpaired |
| tables/a1_cell_check.csv | Pre-declared cell rank check |
| tables/empty_talk_covariate.csv, empty_talk_sensitivity.csv, silent_turns_both_models.csv | Empty-reply and silence analyses |
| tables/chat_effect_pooled_with_replicates.csv | Chat effect pooled with the same-prompt replicates |
| tables_sensitivity_qwen_step1_table/ | The same outputs on the provisional Qwen table |
