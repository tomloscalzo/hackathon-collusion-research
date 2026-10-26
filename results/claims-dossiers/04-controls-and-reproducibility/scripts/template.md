# Dossier 04: controls, wording spread and reproducibility (gpt-oss-20b and Qwen3-32B)

*Created by Claude at the prompting of the repository owner. Independent re-derivation of the claims G-ctl, G-repro and Q14-wording from the Step 1 game tables, plus the copy-bot control. All statistics are recomputed here by new scripts (`scripts/`), not copied from earlier reports.*

## Orientation

In this game two or three LLM "market makers" each quote a **half-spread** (the distance from the mid-price to the firm's bid and ask) from 1.00 to 5.00 in steps ("ticks") of 0.01. 1.00 is the competitive level (costs covered, no excess profit), 3.00 is the monopoly price, 70% of customers go to the lowest quote, a regulator investigates more often when prices are higher, and games last 7 to 20 rounds. This dossier asks four questions about the evidence standards of the study. (1) Do the two **control instructions** (one tells both firms to quote exactly 1.00, the other tells them to maximise joint profit) bracket the ordinary chat game as they should? (2) Does re-running the **same prompt** reproduce a game, and how large is the gap compared with the lever effects we report? (3) Does the **wording** of the prompt (five hand-written paraphrases) move the outcome? (4) Can a **high matching share** alone tell coordination from mere echoing (the copy-bot control)? The data are the neutral-table run (the payoff table prints evenly spaced example prices, not the theory price 2.09): gpt-oss-20b (one mode only, reasoning effort "medium", which corresponds to Qwen's thinking on; 840 planned games, 819 finished) and Qwen3-32B (thinking off and on; 1,388 planned games, 1,360 finished), 20 (wording, seed) pairs per cell, plus 80 Qwen copy-bot games from the raw event logs. Because gpt-oss has one mode, every gpt-oss versus Qwen comparison uses Qwen thinking on and carries a model confound (different model, different serving) in addition to the mode confound.

> **How to read the metrics.** Each is computed per game, then averaged over (wording, seed) pairs.
>
> | Metric | Definition (source column of the Step 1 game table) | Higher means | Worked example |
> |---|---|---|---|
> | Average absolute spread | mean market quote (the lowest quote each round) in raw units, 1.00 to 5.00 (`market_price_mean`) | higher prices (more collusive) | a game at 2.50 every round: 2.50 |
> | Price index | (market price - 1) / 2 averaged over rounds, 0 (1.00) to 1 (3.00) (`price_index`) | more collusive | 2.50 gives 0.75 |
> | Profit gain index | (profit - competitive profit) / (monopoly profit - competitive profit) per firm-round (`profit_gain_index`); can exceed 1 when one firm out-earns an equal split | more collusive | a tie at 2.50 earns 0.94 |
> | Competitive share (U16) | share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00 (`competitive_share`) | more competitive | quote 1.99 after the rival's 2.00: competitive |
> | Matching share | share of firm-rounds in which the firm's quote equals the lowest rival quote of the previous round, above 1.00 (`matching_share`); the coordination signature | more lock-step | quote 2.00 after the rival's 2.00: matching |
>
> The five are always reported separately. Competitive share, matching share and the share of rounds quoting above the rival sum to 1.

<small>

| Term | Definition |
|---|---|
| pair | one (wording, seed) combination; 5 wordings x 4 seeds = 20 pairs; a contrast is the within-pair difference between two arms |
| wording | one of five hand-written paraphrases of every prompt text; each seed is used with exactly one wording, so wording and seed-within-wording are nested and cannot be separated |
| control (instruction) arms | `ctl-32b-compete` ("strict-compete": both firms told their only objective is to quote exactly 1.00) and `ctl-32b-joint` ("joint-profit": both firms told to maximise the joint cumulative profit of all market makers); both with private chat, penalty point 3. The "32b" in the names is historical: the gpt-oss games use the same arm names |
| headline-chat p3 | the ordinary private-chat game with no extra instruction, penalty point 3 (the control for the two arms above) |
| penalty point p1 / p3 / p5 | how heavy the regulator's fine is (p1 light: collusion clearly pays; p3 intermediate; p5 heavy) |
| thinking on / off (t1 / t0) | whether the model reasons in a hidden chain of thought before replying; gpt-oss has only its "medium" reasoning mode |
| run root, submission batch (wave) | a run root is one launch directory of games; the game table records a wave number per game (waves 1 to 16 and 101 to 112 here); the within-day running order is not recorded |
| hrep arms | headline replicates: five arms (`hrep-fx-chat-p1`, `hrep-nx-chat-p1`, `hrep-fx-tacit-p1`, `hrep-nx-tacit-p1`, `hrep-fx-chat-p5`) that were meant to be formula or no-numbers conditions but, because of a build bug, played the ordinary neutral headline prompt (identical prompt fingerprint and code version); they are valid same-prompt replicates of the headline cells |
| Holm | the multiplicity correction applied within a named family of tests (family stated at each use) |
| CI | 95% percentile bootstrap over pairs (10,000 resamples); p = exact two-sided sign-flip permutation over pairs (all 2^20 flips for 20 pairs; 400,000 Monte-Carlo flips beyond that); MDE = 2.8 x the standard error of the paired difference (about 80% power at the 5% level) |

</small>

## Summary of findings

| Claim | Proposed status | One-line reason |
|---|---|---|
| G-ctl (controls bracket the chat game) | confirmed, rephrase; the "chat below the joint-profit control" part is downgraded to moderate | strict-compete is 0.007 profit gain (not exactly 0); the joint-profit control reaches 0.93 profit gain but only 2.49 on spread; gpt-oss chat is {{CTL_JC_P}} on the price index below the joint control (Holm {{CTL_JC_PH}}), Qwen thinking on is not, but Qwen thinking off looks like gpt-oss; the control and the headline game sit in different submission batches and the gap is as large as the replicate offset |
| G-repro (same prompt does not reproduce a game; replicates ran higher) | confirmed, moderate; the "later wave" explanation is wrong | price index {{PRICE_POOL}} over 99 pairs, {{PRICE_DD}} de-duplicated over 59 headline games; competitive and matching shares not detectably different; replicates ran in the same waves as the headline games, so the cause is unidentified; the gap is comparable to {{NCOMP}} of the {{NSIG}} lever effects whose CI excludes zero |
| Q14-wording (wording moves profit gain with thinking off) | confirmed on Qwen with a label fix (root eps-sq 0.347 is eps-sq 0.120); gpt-oss: testable, inconclusive | Qwen thinking off: Holm 0.001; Qwen thinking on: none on price or profit, strong on shares; gpt-oss: no detectable wording effect, but the test could only see a range of about {{PW_PGI}} in profit gain |
| Copy-bot (matching alone cannot separate coordination from echo) | confirmed as an inference, exploratory; gpt-oss untestable | the LLM matches a scripted echoer no more than it matches another LLM (bounds are wide, up to 0.38); one profit-gain exception loses its Holm significance on the counted-game reference |

## 1. G-ctl: do the control instructions calibrate the metrics?

**What this compares.** In the private-chat, penalty point 3 cell, three arms with the same 20 (wording, seed) pairs: the ordinary chat game (`headline-chat` p3), the strict-compete control (both firms told their only objective is to quote exactly 1.00) and the joint-profit control (both told to maximise joint cumulative profit). Models: gpt-oss-20b (reasoning medium) and Qwen3-32B thinking on, with Qwen thinking off as an extra. Unit: game, 20 pairs per contrast. CI, p and Holm as in the Terms table; **Holm family: 3 contrasts x 5 metrics = 15 tests per model.** Status: the control arms were part of the design; no prediction was declared for gpt-oss, so every gpt-oss contrast here is **exploratory** (the earlier ad hoc report says the same).

**Arm levels (mean over 20 games).**

gpt-oss-20b (reasoning medium):

{{LEV_GO}}

Qwen3-32B thinking on:

{{LEV_Q1}}

Qwen3-32B thinking off:

{{LEV_Q0}}

**Paired contrasts, gpt-oss-20b** (first arm minus second; difference [95% CI]; sign-flip p; Holm within the 15):

{{CTL_GO}}

**Paired contrasts, Qwen3-32B thinking on:**

{{CTL_Q1}}

**Paired contrasts, Qwen3-32B thinking off:**

{{CTL_Q0}}

<small>

| Label | Precise definition |
|---|---|
| compete - chat | strict-compete control minus `headline-chat` p3: neutral run, private chat, penalty point 3, same wording and seed; negative spread, price and profit values and positive competitive share mean the instruction pushed play to competition |
| joint - chat | joint-profit control minus `headline-chat` p3; positive on spread, price and profit means the joint-profit instruction produces higher prices than the ordinary chat game |
| joint - compete | joint-profit control minus strict-compete control; the span of the instrument |
| cells | each cell shows difference [95% bootstrap CI over 20 pairs]; p = exact sign-flip; Holm over the 15 tests of that model; n = 20 pairs everywhere |

</small>

**Each metric separately.**

- **Strict-compete is about 0, not exactly 0 on gpt-oss.** Price index 0.005, profit gain index 0.007, spread 1.011, competitive share 0.99, matching share 0.00. One of 20 gpt-oss games has a profit gain above 0.02 (maximum 0.134, spread up to 1.21); on Qwen all 20 games sit exactly at 1.00 in both modes. Compete minus chat on gpt-oss: profit gain {{CTL_CC_PGI}} (Holm < 0.0001). Re-derivation matches the earlier report (it gives -0.798 [-0.876, -0.695]).
- **The joint-profit control is high but not at the monopoly price.** gpt-oss: profit gain 0.932, price index 0.744, spread 2.49 (the monopoly quote is 3.00), the highest single game price index is 0.84. Qwen: 0.919, 0.725, 2.45. So "near monopoly" is accurate for profit (0.93 of the way) and for the profit ceiling that regulators allow, not for the price, which stops about three quarters of the way up the scale; both models stop short because the regulator investigates more at high prices.
- **Joint minus chat.** gpt-oss: price index {{CTL_JC_P}}, profit gain {{CTL_JC_PGI}}; competitive share and matching share move in the same direction (joint has less undercutting, more matching). Qwen thinking on: price index {{CTL_JC_Q1}}, indistinguishable from zero (MDE about 0.09 on the price index). Qwen thinking off: price index {{CTL_JC_Q0}} (Holm {{CTL_JC_Q0P}}), the same size and sign as gpt-oss, though with the wider thinking-off noise it is not significant after correction. So **"unlike Qwen" is true only against Qwen thinking on**; thinking-off Qwen chat also sits below the joint-profit control.
- **Spread, price and profit all agree on the direction; the two share metrics are ceiling-limited on Qwen** (competitive share 0.00 to 0.01 and matching share 0.97 to 1.00 in Qwen thinking-on joint and chat cells), which is why the Qwen share contrasts have degenerate CIs.

**Caveats.** (a) The two control arms were launched in waves 7 to 12 and the gpt-oss `headline-chat` p3 games in waves 107, 108, 109 and 112 (the 100-series batch), a different submission batch, so the joint-minus-chat contrast is not a same-batch comparison (Qwen's are also in different waves: controls wave 0, headline chat waves 1 and 2). (b) The gpt-oss joint-minus-chat gap (+0.13 on the price index) is the same size as the replicate offset in section 2 (+0.10), and the offset was measured at p1 and p5, not p3, so we cannot say how much of the gap is real. (c) The formula-block joint-profit control (`fx-ctl-joint`, a separate run root, no printed example prices) is lower than the ordinary joint control by {{FXJ_PRICE}} on the price index and {{FXJ_PGI}} on the profit gain index (n = 20 pairs; exploratory). (d) The 15-test Holm family is our choice; with no correction the conclusions are the same.

**Proposed status: confirmed, rephrased.** Split it: calibration (compete about 0, joint high) is strong and replicates in sign and magnitude on both models; "gpt-oss chat sits clearly below its joint-profit control, unlike Qwen" is **moderate** (exploratory, cross-batch, equal in size to the unexplained replicate offset, and Qwen thinking off resembles gpt-oss). Sub-questions 2.3, 1.2.

- **Main text:** "Both control instructions behave as intended on gpt-oss-20b (strict-compete: profit gain 0.007; joint-profit: 0.93), and gpt-oss's ordinary chat game sits 0.13 on the price index below its joint-profit control, a gap Qwen3-32B with thinking on does not show."
- **Appendix:** "gpt-oss-20b, neutral run, penalty point 3, 20 pairs: strict-compete control price index 0.005 and profit gain 0.007; joint-profit control 0.744 and 0.932 (spread 2.49, not 3.00); joint minus ordinary chat +0.132 [+0.061, +0.217] on the price index (Holm over 15 tests {{CTL_JC_PH}}). Qwen3-32B thinking on: -0.040 [-0.102, +0.020]; thinking off: {{CTL_JC_Q0}}. The control games ran in a different submission batch from the ordinary chat games."

## 2. G-repro: does re-running the same prompt reproduce a game?

**What this compares.** Five replicate arms (the "hrep" arms, defined in the Terms table above) each play the same prompt, the same code version and the same 20 (wording, seed) pairs as a headline cell: two copies of `headline-chat` p1, two of `headline-tacit` p1 and one of `headline-chat` p5 (19 pairs: one replicate game failed with a timeout). Contrast: replicate minus headline game of the same pair; positive = replicate higher. Unit: game, pair; n = 99 pairs (59 distinct headline games, because two arms copy each of the first two cells). gpt-oss-20b only; no Qwen replicate exists, so there is no Qwen row. **Holm family: the five replicate arms within each metric (size 5)**; the pooled and de-duplicated rows are single extra tests. Status: **post hoc**: the replicates are an accident of a build bug, not a designed replication (the earlier ad hoc report headed this "declared analysis"; the claims ledger says post hoc, which is correct).

**The replicate-minus-headline gap on the five metrics** (difference [95% CI]; exact sign-flip p; Holm across the five arms; spread in raw units):

{{RR_ROWS}}

<small>

| Label | Precise definition |
|---|---|
| hrep-fx-chat-p1 | replicate of `headline-chat` p1 (private chat, penalty point 1), gpt-oss-20b, neutral run, 20 pairs; labelled "formula" in the grid but built with the headline prompt |
| hrep-nx-chat-p1 | second replicate of `headline-chat` p1 (grid label "no numbers"), 20 pairs |
| hrep-fx-tacit-p1, hrep-nx-tacit-p1 | two replicates of `headline-tacit` p1 (no chat, penalty point 1), 20 pairs each |
| hrep-fx-chat-p5 | replicate of `headline-chat` p5 (heavy fine), 19 pairs |
| pooled | all 99 replicate-headline pairs in one sample; not independent (59 headline games), so its p and CI are too narrow |
| de-duplicated | the copies of each headline game averaged first, then 59 differences; the honest single estimate |
| Diff | mean over pairs of replicate minus headline; positive means the replicate was higher |
| MDE of the pooled price index | {{MDE_PRICE_POOL}} (99 pairs, treated as independent) and {{MDE_PRICE_DD}} (de-duplicated) |

</small>

**Each metric separately.**

- **Average absolute spread:** pooled {{SPREAD_POOL}} (de-duplicated {{SPREAD_DD}}, p {{P_SPREAD_DD}}): replicates quote about 0.2 higher.
- **Price index:** pooled {{PRICE_POOL}}, de-duplicated {{PRICE_DD}} (p {{P_PRICE_DD}}). Same sign in all five replicate arms; the per-arm CI excludes 0 only for `hrep-fx-chat-p1` and `hrep-fx-tacit-p1`, and after Holm across the five arms only the first (0.014). Re-derivation matches the earlier report (+0.104 [0.052, 0.156] there).
- **Profit gain index:** pooled {{PGI_POOL}}, de-duplicated {{PGI_DD}} (p {{P_PGI_DD}}).
- **Competitive share:** pooled {{COMP_POOL}}, de-duplicated {{COMP_DD}}: a small shift towards less undercutting; CI includes 0.
- **Matching share:** pooled {{MATCH_POOL}}, de-duplicated {{MATCH_DD}}: CI includes 0 (the pooled lower bound is -0.007).

**How far apart are two games on the same pair?** The typical gap is large. Pooled over the 99 pairs (difference replicate minus headline):

| Metric | Mean gap (drift) | SD of the gap | Mean absolute gap | Drift in SDs |
|---|---|---|---|---|
{{GAP_ROWS}}

The mean absolute gap on the price index is 0.22; only 1 of 99 pairs has an identical quote sequence (a 2-round game). The drift is about 0.35 to 0.39 SD of the gap on the three price-and-profit metrics and under 0.2 SD on the shares.

**Correlation between a headline game and its replicate** (99 pairs; Spearman and Pearson; the last two columns centre each cell on its mean first so that differences between cells do not inflate the correlation):

| Metric | Pearson | Spearman | Pearson, cell-centred | Spearman, cell-centred |
|---|---|---|---|---|
{{COR_ROWS}}

Pairing on (wording, seed) therefore removes very little noise: within a cell, the headline game predicts its own replicate poorly (cell-centred correlation 0.04 to 0.09 on price and profit, 0.3 on matching share). The seed fixes the plan and the regulator's draws, not the sampled text.

**Where does the offset come from? What we can and cannot say.**

- *Not the wave.* The claims ledger says the replicates "ran in a later wave". The game table shows otherwise: `hrep-*-chat` games sit in waves 7, 8, 9 and 12, exactly the waves of their `headline-chat` p1 and p5 games, and `hrep-*-tacit` games in waves 13 to 16, exactly the waves of `headline-tacit`. The prompt fingerprint and code version are identical. So run date and submission batch do not explain the offset (the within-day order is not recorded, so a short-lived serving drift cannot be excluded). The ledger caveat should be reworded to "cause not identified".
- *What the replicates cannot test.* The replicates only compare games within the same waves and the same penalty points (p1 and p5). They say nothing about gaps between waves, such as the wave-107-series games (`headline-chat` p3 and most lever arms) against the wave 7 to 16 games, or any other cross-wave gap, and there is no replicate at p3. Drift at p3, and between waves, is therefore **unmeasured**, not shown to be absent.
- *Visible from round 1.* The first-round quote, which has no game history, is also higher in the replicates: {{R1_POOL}} pooled, {{R1_DD}} de-duplicated (raw units, 1.00 to 5.00). The gap is therefore at the level of sampling, not only of game dynamics.
- *The two replicate copies agree with each other.* Fx copy minus nx copy of the same headline game (difference [95% CI], price index; profit gain):

| Contrast | Price index | Profit gain index |
|---|---|---|
{{RV_ROWS}}

  The two copies differ by far less than either differs from the headline game, so the headline games look low relative to both copies, but with 20 pairs per copy this is also what a chance low draw would produce.
- *Placebo arms as a second yardstick.* Two arms that add only a placebo sentence should sit at the headline-chat p1 level. They do not sit at the replicate level:

| Placebo arm minus `headline-chat` p1 | Price index [95% CI] | Profit gain index [95% CI] |
|---|---|---|
{{PL_ROWS}}

  Their mean (about +0.03) lies between zero and the +0.10 offset, and their CIs cover both. This does not identify a cause. It does suggest that the offset is at most partly a general "headline cells are low" effect.

**How many lever effects is the gap comparable to?** Figure 1 puts the gap (grey band, +/-0.104 on the price index) next to all {{NTOT}} gpt-oss arm-versus-control price-index contrasts we can form from the game table (including the five headline contrasts and the formula-minus-no-numbers contrast; the control is the shared control of the design, listed in `g_repro_lever_effects.csv`).

![Lever effects on the gpt-oss price index against the replicate gap](fig1_lever_effects_vs_replicate_gap.png)

*Figure 1. Change in the price index (arm minus its control, paired on wording and seed) with its 95% bootstrap CI, one row per contrast; red marks more collusive, green more competitive; the grey band is the pooled replicate-minus-headline gap (+0.104). Derived from the column `price_index` of the gpt-oss game table, n = 11 to 20 pairs per row; filled markers have CIs that exclude 0; squares are contrasts whose control sits in a different run root (the formula and no-numbers arms). Higher = more collusive.*

<small>

| Label | Precise definition |
|---|---|
| rows (y-axis) | one contrast each, "slug: short description (vs control)"; slugs are defined in the legend table below; "chat p5 - tacit p5" etc. are the headline contrasts (chat versus tacit, penalty p5 versus p1) within the headline cells |
| x-axis | change in price index (units of the index, 0 to 1 scale; 0.1 is 0.2 of a quote unit); positive = arm higher than its control |
| grey band | replicate-minus-headline price index gap, +0.104 (pooled 99 pairs) |
| marker fill / shape | filled = CI excludes 0; open = CI includes 0; circle = control in the same run root; square = control in a different run root |
| run, table, mode | neutral run, gpt-oss-20b, reasoning medium, penalty point as stated in each row's control |

</small>

{{FIG1_LEGEND}}

Counts, price index: of the {{NTOT}} contrasts, {{NLE}} have an absolute effect no larger than the gap (0.104); {{NSIG}} have a CI that excludes zero; of those {{NSIG}}, only 2 are no larger than the gap and {{NCOMP}} are no larger than twice the gap (0.209); after moving each effect by 0.104 towards zero, {{NROB}} of the {{NSIG}} still exclude zero; with Holm over all {{NTOT}} (an exploratory family we define here) {{NHOLM}} contrasts pass at 0.05. The CI-excluding effects that are within twice the gap:

{{CMP_ROWS}}

**Which other claims this threatens.** The caveat applies to any contrast whose size is under about 0.2 on the price index, and to every null whose MDE is about 0.1.

| Claim (ledger id) | Size on gpt-oss | Threat |
|---|---|---|
| G-incjoint (joint-profit incentive text raises prices) | +0.103 [+0.008, +0.208], p 0.058 | high: equal to the gap, control at p3 |
| G-r2s (saved-only confidant question raises profit) | +0.105 [+0.014, +0.210], p 0.051; Holm over 38: 1.0 | high: equal to the gap; and its "twin" contrast inherits it |
| G-r4 (appendix only) | +0.096 on 11 pairs | high |
| G-cot (reasoning-monitor threat lowers prices) | -0.130 [-0.250, -0.008], p 0.059 | medium: sign survives, size within 25% of the gap |
| G-ctl joint versus chat | +0.132 | medium (section 1) |
| G-fxjoint (formula joint control is lower than the ordinary one) | {{FXJ_PRICE}}, cross-root | medium |
| G-penalty (p5 below p1) | -0.151 chat, -0.193 tacit | medium: the p1 cell is a headline cell with a measured offset; the shift towards p1 being low would make the penalty effect larger, not smaller |
| G-comm (chat above tacit) | +0.186 at p1, +0.228 at p5 | low: both cells have replicates and the offsets are similar (+0.09 and +0.14 de-duplicated), so the difference between cells largely cancels |
| G-levels (headline levels, versus Qwen) | levels, not contrasts | the level of any headline cell is uncertain by about +/-0.1; the gaps to Qwen (0.28 to 0.33 at p1) are larger |
| Null claims (G-dset-null, G-intro-null, G-null-struct, G-watchdog, G-r2f and the placebos) | CI half-widths of 0.09 to 0.14 | the nulls are bounds of about +/-0.1, the size of the offset; a real effect of 0.1 is not excluded |
| G-payoff (formula and no-numbers lower prices; separate run root) | -0.22 to -0.56 | low: effects are two to five times the gap; the smallest, formula tacit at p1 (-0.221), loses its CI separation from zero if shifted by the full gap |
| Moral primes, planted cheater, three-firm ethics rule, 5-tick start, strict-compete | -0.23 to -0.61 | none: far larger than the gap |

Qwen's results have no replicate-based offset estimate, so nothing is established for them; the gpt-oss offset threatens only the gpt-oss side of any Qwen versus gpt-oss comparison.

**Proposed status: confirmed, moderate** (not "strong": the pooled CI is not independent; the de-duplicated p is 0.007, and Holm across the five arms leaves one arm). Correct the ledger caveat: the replicates were in the same waves as the headline games. Sub-questions 2.3, 1.2.

- **Main text:** "Re-running the identical gpt-oss prompt does not reproduce a game (a typical pair differs by 0.22 on the price index) and the replicates ran about +0.10 higher than the headline games, so effects of that size on gpt-oss should be read with caution."
- **Appendix:** "99 replicate-headline pairs (59 distinct headline games, penalty points 1 and 5, same wording, seed, prompt and code): price index {{PRICE_POOL}} pooled and {{PRICE_DD}} after averaging copies per headline game; profit gain index {{PGI_DD}}; competitive share {{COMP_DD}} and matching share {{MATCH_DD}} with CIs including 0; replicates and headline games ran in the same waves, cause unidentified. Of {{NTOT}} lever contrasts, {{NLE}} are no larger than the gap."

## 3. Q14-wording: does prompt wording move the outcome?

**What this compares.** The five prompt wordings (hand-written paraphrases of every prompt text, four seeds each, so 20 pairs). The test asks whether the headline games differ by wording. The claim being re-derived: with thinking off (Qwen), profit gain differs by wording, "root epsilon-squared 0.35". Unit: games for the pooled test (240 per Qwen mode: three communication conditions x four penalty points x 20 pairs; 100 for gpt-oss: private chat at p1, p3, p5 and no chat at p1, p5, which is all the headline cells it has) and pairs (20) for the pair-mean test. **Holm family: the five standard metrics within each model and mode.** Status: **exploratory** (the Qwen screen was a descriptive Step 2 screen; the ledger marks it exploratory; no gpt-oss wording test was declared). Two tests per metric: (A) the Step 2 screen: a Kruskal-Wallis epsilon-squared of wording on the pooled game values, with the p taken from permuting the wording label across the 20 pairs (9,999 shuffles, so p cannot go below 0.0001), which keeps the games of a pair together; (B) a pair-mean test: each pair's games averaged after subtracting their cell mean (20 numbers, 4 per wording), eta-squared and an F permutation p (9,999 shuffles).

**Re-derivation of the Qwen claim.** Thinking off, profit gain index: pooled epsilon-squared **0.1203**, root epsilon-squared **0.3468**, p 0.0002 (Holm over five metrics 0.0010). This matches the Step 2 table exactly (0.1203 and 0.3468). **The ledger says "epsilon-squared 0.35"; 0.35 is the square root. The epsilon-squared is 0.12** (the Step 2 heat map plots the root, which is why it was reported that way). The BH q of 0.005 in the ledger is over seven outcomes within the mode; our Holm family of five gives 0.001 to 0.045 across metrics, with the same ordering.

**Qwen3-32B, thinking off (n = 240 games, 20 pairs):**

{{W_Q0}}

**Qwen3-32B, thinking on:**

{{W_Q1}}

**gpt-oss-20b (reasoning medium; 100 games, 20 pairs):**

{{W_GO}}

<small>

| Label | Precise definition |
|---|---|
| eps-sq (pooled games) | Kruskal-Wallis epsilon-squared (the H statistic divided by (n squared - 1) / (n + 1), no tie correction, floored at 0) of wording on all headline games of the mode; the Step 2 screen definition; 0 = none, 1 = all rank variance; not corrected for the number of levels |
| root eps-sq | its square root; the quantity quoted as "0.35" in the ledger; has no collusion direction |
| p (pair permutation) | share of 9,999 shuffles of the wording label across the 20 (wording, seed) pairs with an epsilon-squared at least as large (+1 in numerator and denominator) |
| max minus min of wording means | highest minus lowest wording mean over the pooled games, in the metric's own units |
| eta-sq (20 pair means) | share of variance of the 20 cell-adjusted pair means explained by wording (between-wording sum of squares over total), pairs = 5 wordings x 4 seeds |
| p (pair-mean F permutation) | F ratio of wording over seed-within-wording, permuted over pairs |
| cells | headline games: Qwen = tacit, private chat and monitored chat at p1, p3, p4, p5; gpt-oss = private chat at p1, p3, p5 and tacit at p1, p5 |

</small>

![Profit gain by wording](fig2_wording_profit_gain.png)

*Figure 2. Profit gain index by prompt wording, one grey dot per (wording, seed) pair (pair mean of its headline games after subtracting each cell's mean), blue bar = wording mean; left Qwen thinking off, middle Qwen thinking on, right gpt-oss. Source: `profit_gain_index` in the game tables; n = 20 pairs per panel (240, 240 and 100 games). Higher = more collusive; a flat row of bars means wording does not matter.*

<small>

| Label | Precise definition |
|---|---|
| x-axis: wording 0 to 4 | the five hand-written paraphrases of every prompt text; four seeds each (the seeds are tied to a wording) |
| y-axis | pair mean profit gain index minus the cell mean, so 0 is the average pair; units are profit gain index points |
| grey dot | one (wording, seed) pair |
| blue bar | mean of the four pairs of that wording |
| panels | Qwen3-32B thinking off (12 headline cells), Qwen3-32B thinking on (12 cells), gpt-oss-20b reasoning medium (5 cells); neutral run |

</small>

**Each metric separately.**

- **Profit gain index and price index, spread.** Qwen thinking off: wording explains a large share (eta-sq 0.73 to 0.77 of the pair-mean variance; Holm 0.0025 to 0.010). Wordings 3 and 4 run about +0.08 above the cell mean and wordings 0 and 2 about 0.06 to 0.10 below; the range of wording means is 0.19 on profit gain and 0.17 on the price index. Qwen thinking on: no wording effect on any of the three (p 0.31 to 0.95; Holm 0.74 to 1).
- **Competitive share and matching share.** Wording matters in both Qwen modes, and more with thinking on (eta-sq 0.69 and 0.78; Holm 0.0005) than off (0.59 and 0.66; Holm 0.023 and 0.010). So "wording moves profit gain with thinking off" is true but incomplete: with thinking on wording moves how the firms play (undercut versus match) without moving where prices end up.
- **gpt-oss-20b, headline cells only: no detectable wording effect on any metric (inconclusive; see dossier 11).** Profit gain: epsilon-squared 0.036 (root 0.19), p 0.172, pair-mean eta-sq 0.31, p 0.218; price index p 0.154 and 0.194; competitive share p 0.103 and 0.213; matching share is the closest (p 0.041 and 0.049, Holm 0.21 and 0.32). The wording means for profit gain range from 0.49 (wording 1) to 0.66 (wording 3), a range of 0.16.
- **This is a null with little power, not evidence of no effect.** With five wordings of four pairs each, the pair-mean test has about 80% power only for a wording effect with eta-sq of about 0.45 (Cohen's f 0.9). In gpt-oss units that is a range between the lowest and highest wording mean of about {{PW_PGI}} on profit gain and {{PW_PRICE}} on the price index (simulated, `q14_wording_power.csv`). The observed range (0.16 and 0.14) is below that, and the Qwen thinking-off effect (range 0.19 on profit gain) is within what gpt-oss could not have seen.

**Consistency with the pooled test (dossier 11, fresh discovery).** That dossier pools all 37 gpt-oss cells and finds a significant wording effect (seed-regrouping p 0.0001, range 0.15 on the price index). The two are consistent: the headline-cells test here (100 games, five cells) is underpowered, so it is **inconclusive on the headline cells alone; see dossier 11 for the pooled test**. Read the gpt-oss paragraph above as a power statement, not as evidence that wording does not matter on gpt-oss.

**Confounds.** (a) Wording and seed are nested: every seed is used with one wording, so "wording" is wording plus its four seeds (the planned game length, which a seed fixes, is balanced across wordings: one seed each at 7, 15, 19 and 20 rounds). (b) The gpt-oss headline cells (five cells, 100 games) are fewer than Qwen's (12 cells, 240 games), so the gpt-oss pair means are noisier. (c) gpt-oss has one mode, so the comparison is with Qwen thinking on, where Qwen also has no wording effect on price and profit; the two are consistent on price and profit and the shares are the only place where Qwen thinking on shows wording sensitivity that gpt-oss does not detectably show (at this power).

**Proposed status.** *Qwen claim:* confirmed, exploratory, with the label fixed (root eps-sq 0.35 = eps-sq 0.12). *gpt-oss side:* the ledger's "not testable" should become "tested, inconclusive (underpowered)"; nothing in the gpt-oss data supports or refutes a wording effect of the Qwen thinking-off size. Sub-question 2.3.

- **Main text:** "Prompt wording moved Qwen's profit gain with thinking off (a rank effect size of 0.12, 0.35 on the square-root scale) but not with thinking on, and we could not detect a wording effect on gpt-oss-20b, a test that only had power for large effects."
- **Appendix:** "Five wordings x four seeds (20 pairs), headline cells, neutral run. Qwen thinking off, profit gain: epsilon-squared 0.120 (root 0.347), permutation p 0.0002, Holm over five metrics 0.001; thinking on: 0.0013, p 0.947. gpt-oss-20b (100 games): epsilon-squared 0.036, p 0.172 (pair-mean eta-squared 0.31, p 0.218); 80% power needs eta-squared of about 0.45. Wording and seed are nested."

## 4. Copy-bot: can a high matching share separate coordination from echo?

**What this compares.** One Qwen3-32B firm plays a **scripted copier** (a mechanical firm: it opens at a fixed quote, then quotes exactly the rival's quote from the previous round, never below 1.00; its rule is not disclosed). Four cells: the copier opens at 2.50 or at 1.50, with Qwen's thinking off or on; tacit (no chat), penalty point 1, neutral table, 20 (wording, seed) pairs per cell, 80 games. The reference is the ordinary LLM-versus-LLM headline tacit p1 game of the same pairs and mode (both firms pooled; the counted games of the Step 1 table, which replace three truncated thinking-on games with their longer-context reruns). Contrast: copier game minus headline game, paired on (wording, seed). **Holm family: the four cells within each metric (size 4).** Status: **exploratory** (the design was fixed before the games were run, the metric comparison was not declared). Metrics were recomputed here from the raw event logs (every market round's quotes and profits), not from the earlier CSVs.

**Result (copier mean vs headline mean; difference [95% CI]; Holm within metric across the four cells):**

{{CB_ROWS}}

<small>

| Label | Precise definition |
|---|---|
| copier opens at 2.50 / 1.50 | the scripted copier's round-1 quote; `copybot-o250-tacit`, `copybot-o150-tacit`; neutral run, tacit, p1, Qwen3-32B |
| off / on | thinking off (t0) / on (t1) |
| copier mean vs headline mean | mean over the 20 pairs of the LLM firm's own metrics against the copier, and the pooled two-firm metrics of the headline tacit p1 game of the same pairs and mode; shares of firm-rounds, spread in quote units |
| difference | copier minus headline; positive spread, price, profit and matching = higher than against an LLM |

</small>

**Each metric separately.**

- **Average absolute spread and price index.** Against a copier opening at 2.50 the market looks like the LLM-versus-LLM headline game in both modes (spread +0.06 off, -0.03 on; price +0.03 and -0.01; bounds about -0.19 to +0.24 spread, -0.09 to +0.12 price). Against a copier opening at 1.50 the result depends on the mode: off, no difference (+0.03, bounds -0.10 to +0.15); on, prices fall a long way (-0.95 on spread, -0.48 on the price index): the thinking-on firm undercuts the copier by a cent and follows it down.
- **Profit gain index.** The same, except two cells: copier 1.50 with thinking on earns 0.43 less (the price collapse), and copier 2.50 with thinking on earns **more** (+0.105 [+0.011, +0.195], p 0.040, Holm 0.121). The earlier ad hoc report gave +0.13 with Holm 0.039; the difference is the headline reference (three truncated games replaced by reruns in the counted table). On the counted-game reference **this exception does not survive the four-cell Holm correction**.
- **Competitive share.** No cell differs detectably; bounds run from -0.22 to +0.32 across the cells.
- **Matching share.** The key metric for the claim. Against a pure echoer the LLM's matching share is 0.77 (off) and 0.54 (on) for the 2.50 copier and 0.56 and 0.45 for the 1.50 copier, against 0.63 and 0.57 in LLM-versus-LLM games. It is not detectably higher against a copier than against an LLM in any cell (differences +0.14, -0.02, -0.07, -0.11), but the bounds are wide: the 95% intervals run from about -0.29 to +0.38, and the MDE is 0.26 to 0.36. The data are consistent with a difference of up to about 0.38 in either direction.
- **The mechanical benchmark.** Two scripted copiers playing each other (340 games, no LLM) freeze at their opening quote with matching share 1.00 and competitive share 0.00 at any start above 1.00. A matching share of 1.00 is therefore what pure echo produces; the observed LLM matching shares (0.45 to 0.77 here, up to 0.97 in Qwen chat cells) are not separable from it by that metric alone.

**Reading.** The control does not show that the LLM firms are copiers: the LLM is not a pure echoer and does not exploit one (it neither follows a high copier up nor holds a high level against a low one with thinking on). What it shows is narrower and is the claim as stated: the LLM's matching share when playing a mechanical echoer is no lower than its matching share against another LLM, so a high matching share cannot, by itself, tell coordination from following. Matching has to be read with the price level and with what the firm does when the rival moves (the rival-response measures).

**gpt-oss-20b: untestable.** No gpt-oss copier arm exists: the gpt-oss game table has only LLM-versus-LLM games (and one three-firm arm with a scripted one-shot defector, `n3-cheater`, which is not a copier); the engine refuses a scripted partner in the chat phase, and the copier games ran tacit only. For orientation only, gpt-oss's own matching shares are much lower than Qwen's thinking-on levels (no chat p1: 0.16 against 0.57 for Qwen; private chat p1: 0.41), so the echo ambiguity is quantitatively smaller on gpt-oss at the headline cells, but that is a level observation, not a test. A gpt-oss copier cell (about 80 games, tacit) would test it.

**Proposed status: confirmed as an inference, exploratory** (the Qwen contrasts replicate the earlier numbers; the single significant exception softens under Holm on the counted-game reference). Frame it as "matching share alone is ambiguous", not as "the models are not coordinating". gpt-oss: untestable (no arm). Sub-questions 2.3, 3.1.

- **Main text:** "A scripted copier shows that a high matching share alone cannot tell coordination from echo: Qwen3-32B matched a mechanical echoer no less than it matched another LLM, so we read matching alongside the price level and the response to rival moves."
- **Appendix:** "Qwen3-32B, tacit, penalty point 1, neutral run, 80 games against a scripted copier (opening 2.50 or 1.50, thinking off or on; 20 pairs per cell) versus the LLM-versus-LLM headline game: matching share 0.77 / 0.54 / 0.56 / 0.45 against 0.63 / 0.57 / 0.63 / 0.57; differences +0.14, -0.02, -0.07, -0.11, 95% CIs spanning -0.29 to +0.38. Two copiers playing each other freeze at matching share 1.00. No gpt-oss copier arm exists."

## What changed from the ledger and the earlier ad hoc reports

- G-ctl: "unlike Qwen" holds against Qwen thinking on only; Qwen thinking off also sits below its joint control (+0.16 on the price index, not significant after Holm). The joint control reaches 0.93 profit gain but only 2.49 on the spread. The control and the headline game are in different submission batches.
- G-repro: the replicates ran in the same waves as the headline games (the ledger says "a later wave"); the cause is unidentified; the placebo arms sit between zero and the offset.
- Q14: "epsilon-squared 0.35" is the root; epsilon-squared is 0.12. Thinking on has no wording effect on price or profit but a strong one on both shares. A gpt-oss test was possible and is inconclusive.
- Copy-bot: the single profit-gain exception (copier 2.50, thinking on) does not survive Holm on the counted-game reference.

## Files

`scripts/common.py` (loaders, exact sign-flip, bootstrap, Holm), `g_ctl.py`, `g_repro.py`, `g_repro_corr.py`, `g_repro_levers.py`, `q14_wording.py`, `q14_power.py`, `copybot_rederive.py`, `figures.py`, `build_md.py`; outputs `g_ctl_*.csv`, `g_repro_*.csv`, `q14_*.csv`, `copybot_rederived_*.csv`.
