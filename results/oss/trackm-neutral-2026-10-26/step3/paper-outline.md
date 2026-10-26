# Step C, paper kit: cross-model section (gpt-oss-20b)

All numbers come from these files: `out/compare/lever_table.csv`, `CLONE/results/oss/ad-hoc/payoff-table-focal-points/cell_means.csv` and `standard_metrics.csv`, and `out/step3/claims_ledger.csv` (rows G-payoff, G-focal, G-fxjoint, G-comm, G-ctl, G-cot, G-repro). Here "Qwen" always means Qwen3-32B with thinking on, and "gpt-oss" means gpt-oss-20b at reasoning effort medium. The CIs are 95% paired bootstrap intervals. n is the number of matched (wording, seed) pairs.

## 1. Draft subsection: Cross-model robustness (gpt-oss-20b)

We re-ran the neutral design's headline cells and lever arms with gpt-oss-20b, at reasoning effort medium on every call, and set the results beside Qwen3-32B with thinking on. Every contrast is paired over the same declared (wording, seed) pairs, 20 per arm unless stated, with 95% bootstrap intervals. gpt-oss has no thinking-off mode, so we make no thinking-mode claim for it.

**Printed numbers set the price level (sub-questions 1.1, 2.1).** We tested five cells where the payoff table showed only the formula, or no numbers, instead of printed example prices. The price index fell by 0.22 to 0.56 on gpt-oss (19 to 20 pairs) and by 0.50 to 0.74 on Qwen. With no numbers and private chat at the light penalty, both models end near the competitive floor (gpt-oss 0.02 [0.01, 0.03]; Qwen 0.11 [0.06, 0.17]). The two models anchor differently. On Qwen, 0.99 [0.98, 1.00] of headline-chat quotes sit exactly on a printed value. On gpt-oss the share is 0.40 [0.25, 0.55], and another 0.40 [0.24, 0.58] sit one to three ticks under a printed value (20 games, 489 quotes). These cells are post hoc and come from a separate rerun.

**Propensity versus capability.** We told the firms to maximise joint profit and printed only the formula. gpt-oss reached a price index of 0.62 [0.49, 0.73], level with its own headline chat (+0.01 [-0.11, 0.12]). Qwen reached 0.41 [0.31, 0.50], which is 0.36 [0.27, 0.45] below its headline chat. For gpt-oss, the printed number triggers a propensity to price high; it does not supply a capability gpt-oss lacks. For Qwen, the data are consistent with part of the drop being a capability limit (descriptive, post hoc).

**Chat raises collusion in both models (1.1).** Private chat raised the price index over no chat on gpt-oss by +0.19 [0.06, 0.32] at the light penalty and +0.23 [0.10, 0.36] at the heavy one (Holm p 0.007 and 0.002)[^ci]. The Qwen figures are +0.13 [0.06, 0.20] and +0.36 [0.18, 0.52]. The baselines differ. Without chat, gpt-oss is far more competitive than Qwen (0.39 [0.29, 0.48] against 0.72 [0.67, 0.76]). Its chat cell reaches 82% of its joint-profit control (0.61 against 0.74; gap -0.13 [-0.22, -0.07]). Qwen's chat cell sits at its control (+0.04 [-0.02, 0.10]).

**The levers transfer in sign, mostly smaller (1.5).** Every lever in Table X moved gpt-oss prices in the same direction as Qwen's (gpt-oss first, then Qwen):
- five-tick start: -0.29 [-0.43, -0.13] against -0.55;
- planted cheater: -0.23 against -0.31;
- heavier fine without chat: -0.19 against -0.53;
- reasoning-monitor threat: -0.13 [-0.25, -0.01] against -0.23. This one fails Holm on gpt-oss (19 pairs).

Only chat and the moral prime were as large or larger on gpt-oss. The prime against its placebo moved profit gain by -0.46 [-0.64, -0.27] against -0.25 (19 pairs). Qwen's chat-by-penalty interaction did not replicate (+0.04 [-0.15, 0.22] against +0.23 [0.02, 0.43]); this is inconclusive. Size comparisons are confounded with gpt-oss's lower baseline. Re-running identical prompts drifted +0.10 [0.05, 0.16] (99 pairs), so we do not interpret cross-model gaps below about 0.1.

[^ci]: All intervals in this subsection and in Table X come from `lever_table.csv`, which computes both models' intervals with one bootstrap helper. The Holm-adjusted p values are quoted from the Step 2 declared family (22 tests), whose own intervals were computed by a different method and differ slightly (for example, chat minus no chat at the light penalty: +0.19 [0.08, 0.29] in Step 2).

*(About 440 words.)*

**Terms used in this subsection**

| Term | Plain-language meaning |
|---|---|
| Price index | (market half-spread - 1) / 2, averaged over rounds. 0 is the competitive price (1.00) and 1 is the monopoly price (3.00). |
| Profit gain index | The firms' profit as a share of the way from competitive profit (0) to monopoly profit (1). |
| Half-spread, tick | The quote each firm posts: the distance from the mid-price to its bid and ask, between 1.00 and 5.00. A tick is 0.01. |
| Light / heavy penalty | Penalty point 1 / point 5, the size of the expected regulator fine. |
| Headline chat / no chat | The two firms exchange messages before each round's quotes / they see only each other's past quotes. |
| Printed examples, formula, no numbers | The payoff table shows example prices (headline) / only the profit formula / no numbers at all. |
| Joint-profit control | The firms are told to maximise their combined profit. It is the reference for what deliberate collusion looks like. |
| Five-tick start | Round-1 quotes are capped near the competitive floor. |
| Planted cheater | A third, scripted firm that defects, compared with three LLM firms. |
| Moral prime / placebo | A short moral sentence in the prompt / a neutral sentence of the same length. |
| Reasoning-monitor threat | An idle text warning that the model's reasoning is monitored; the same text also forbids coordination. |
| Holm p | A p-value adjusted for the declared family of tests (Holm step-down). |
| Pair | One (wording, seed) cell played under both arms, so the two arms can be compared directly. |
| Propensity vs capability | Whether the model *chooses* a high price when it can see one, or *cannot find* the collusive price without being shown it. |

## 2. Transfer table (Table X)

Each entry is the arm minus its comparison arm, as a difference [95% CI]. Qwen n is 20 everywhere. gpt-oss n is 20 unless shown in brackets. The verdict column copies the `replicates` field of `lever_table.csv` for the price index; a Holm note is added where it applies.

| Lever (arm minus comparison) | Qwen price index | gpt-oss price index | Qwen profit gain | gpt-oss profit gain | Replicates? |
|---|---|---|---|---|---|
| Private chat vs no chat, light penalty | +0.131 [0.063, 0.204] | +0.186 [0.062, 0.315] | +0.041 [0.005, 0.076] | +0.198 [0.049, 0.351] | yes (profit gain larger on gpt-oss) |
| Private chat vs no chat, heavy penalty | +0.355 [0.182, 0.522] | +0.228 [0.095, 0.359] | +0.438 [0.223, 0.632] | +0.300 [0.128, 0.462] | yes |
| No numbers vs printed examples (chat, light) | -0.735 [-0.816, -0.650] | -0.557 [-0.635, -0.464] | -0.755 [-0.832, -0.663] | -0.736 [-0.823, -0.634] | in sign only (price smaller on gpt-oss); post hoc |
| Formula only vs printed examples (chat, light) | -0.509 [-0.619, -0.401] | -0.302 [-0.430, -0.163] (19) | -0.413 [-0.513, -0.313] | -0.404 [-0.547, -0.254] (19) | in sign only (price smaller); post hoc |
| Joint-profit instruction: formula vs printed | -0.320 [-0.411, -0.231] | -0.126 [-0.252, -0.016] | -0.317 [-0.433, -0.213] | -0.167 [-0.293, -0.050] | in sign only (smaller) |
| Joint-profit + formula vs headline chat (capability test) | -0.360 [-0.454, -0.269] | +0.006 [-0.110, 0.117] | -0.315 [-0.426, -0.218] | -0.040 [-0.164, 0.062] | no: gpt-oss reaches its chat level |
| Heavier fine, no chat (heavy minus light) | -0.533 [-0.655, -0.394] | -0.193 [-0.309, -0.064] | -0.655 [-0.800, -0.494] | -0.295 [-0.439, -0.136] | in sign only (about a third to a half) |
| Heavier fine, chat (heavy minus light) | -0.308 [-0.485, -0.151] | -0.151 [-0.285, -0.013] | -0.259 [-0.429, -0.118] | -0.193 [-0.345, -0.036] | yes per table; fails Holm on gpt-oss (profit gain 0.154) |
| Chat x penalty interaction | +0.225 [0.024, 0.426] | +0.042 [-0.145, 0.215] | +0.397 [0.172, 0.603] | +0.102 [-0.126, 0.311] | no (gpt-oss CI includes 0; inconclusive) |
| Five-tick start vs headline chat (mid penalty) | -0.546 [-0.650, -0.443] | -0.285 [-0.428, -0.126] | -0.599 [-0.709, -0.490] | -0.358 [-0.537, -0.169] | in sign only (about half) |
| Planted cheater vs three LLM firms | -0.305 [-0.362, -0.248] | -0.232 [-0.286, -0.173] (18) | -0.439 [-0.524, -0.353] | -0.330 [-0.429, -0.231] (18) | in sign only (smaller) |
| Moral prime B vs placebo | -0.321 [-0.442, -0.207] | -0.377 [-0.510, -0.237] (19) | -0.247 [-0.343, -0.157] | -0.460 [-0.636, -0.270] (19) | yes (profit gain larger on gpt-oss) |
| Moral placebo vs headline chat | -0.047 [-0.147, 0.053] | -0.003 [-0.082, 0.081] (19) | -0.012 [-0.055, 0.035] | -0.003 [-0.095, 0.082] (19) | null on both |
| Reasoning-monitor threat A vs headline chat | -0.232 [-0.308, -0.151] | -0.130 [-0.249, -0.005] (19) | -0.135 [-0.198, -0.070] | -0.132 [-0.289, 0.025] (19) | price yes; profit gain no; fails Holm on gpt-oss |
| Three LLM firms vs two | -0.090 [-0.195, 0.008] | +0.006 [-0.083, 0.107] (18) | -0.035 [-0.099, 0.030] | +0.025 [-0.071, 0.150] (18) | null on both |
| Joint-profit control vs headline chat | -0.040 [-0.100, 0.023] | +0.132 [0.065, 0.215] | +0.002 [-0.024, 0.033] | +0.127 [0.050, 0.230] | new on gpt-oss (its chat sits below its ceiling) |
| Strict-compete control vs headline chat | -0.765 [-0.838, -0.692] | -0.607 [-0.675, -0.524] | -0.916 [-0.951, -0.875] | -0.798 [-0.875, -0.695] | in sign only (control works on both) |

The table omits these cells; the caption should say so:
- **No-numbers and formula cells.** No-numbers without chat: price -0.698 / -0.379, profit gain -0.873 / -0.555 (Qwen / gpt-oss). Formula only without chat: price -0.630 / -0.221. Formula only with chat at the heavy penalty: price -0.496 / -0.365.
- **Same-prompt replicates (gpt-oss only).** +0.104 [0.052, 0.156] (99 pairs).
- **Not in `lever_table.csv` (none of these has a Qwen row there).** Ethics rule on one of three firms (gpt-oss profit gain -0.26 [-0.42, -0.11], 15 pairs, ledger G-n3ethics), the watchdog arms, and the incentive arms.

## 3. Edits to existing paper sections

Targets are `paper/paper.md` and the Qwen kit `results/trackm-neutral-2026-10-25/step3/paper-outline.md`.

1. **Abstract.** Add one sentence after the anchoring sentence:
   > "A second model, gpt-oss-20b, replicates the direction of every main lever: removing printed example numbers lowers its price index by 0.22 to 0.56 (Qwen 0.50 to 0.74), and chat raises it by 0.19 to 0.23 (Holm p ≤ 0.007), though most lever effects are smaller and its no-chat play is far more competitive (price index 0.39 against 0.72)."

   In the same section:
   - Change "Effects are for one model and game" to "Effects are for two open-weight models in one game".
   - Change "with reasoning on or off" to say the off/on contrast is Qwen-only.
2. **Section 1 / framing.** Reframe anchoring as "printed numbers set the price level, in both models". Add the propensity-versus-capability result: with the formula only and a joint-profit instruction, gpt-oss still reaches its chat price, and Qwen does not.
3. **Section 3, design (new 3.5).** Add the gpt-oss run as a reduced grid, and name what is missing:
   - headline cells chat at points 1, 3, 5 and no chat at points 1, 5;
   - no monitored chat, no point 4, no anchored run;
   - one reasoning setting (medium);
   - the formula / no-numbers cells come from a separate rerun root;
   - the hrep-* replicates are sensitivity only (build bug).
4. **Limitations, paper.md section 8.**
   - Item 14 says "probably one or two models". Make it "two models (Qwen3-32B FP8, gpt-oss-20b), same game, same seeds; no frontier model; no claim about LLMs in general".
   - Add a limitation that cross-model magnitudes are confounded with the different baselines.
   - Add that same-prompt reruns on gpt-oss drifted +0.10 [0.05, 0.16] on the price index (99 pairs), and only 1 of 99 replicate games was identical. That puts a floor of about 0.1 under interpretable between-model and between-wave gaps.
   - Add that the keyword-rule labels (agreement, intent, candour, say-versus-do) were tuned on Qwen text and are unvalidated on gpt-oss, so no text-label claim transfers.
   - Add that empty gpt-oss chat replies are read as silence: an engine difference, used as a covariate.
5. **Limitations, Qwen kit section 5.** Replace "no transfer to other models" with "transfer tested on one second model; levers replicate in sign, not magnitude". Replace thinking-mode wording with "the thinking on/off contrast is Qwen-only; gpt-oss has no off mode (not addressed, not 'no effect')".
6. **LLM usage / disclosure (paper.md section 10).** paper.md has no "LLM usage" section, and its status line still says "No LLM run has been made". Add a paragraph that:
   - names both models as the agents under study: Qwen3-32B FP8, thinking on and off; gpt-oss-20b, reasoning effort medium on every call;
   - says both were run on rented GPUs during the sprint, with the same declared seeds and prompts;
   - keeps the existing statement that the analysis and documents were written by Claude at the owner's prompting.

   Also update the status line.
7. **Dual-use (section 9).** Add one line: the finding that printed numbers set the price level holds across two models. Evaluation designers should therefore treat payoff examples as a treatment, not as neutral scaffolding.

## 4. Figure suggestions (existing PNGs)

| # | File | Claim it carries | Caption draft | Redraw? |
|---|---|---|---|---|
| X1 | `CLONE/results/oss/ad-hoc/payoff-table-focal-points/fig_quote_histograms.png` | printed numbers set the level; gpt-oss shades under them, Qwen copies them; the capability-test row | "Share of quotes at each 0.01 tick, gpt-oss-20b (left) and Qwen3-32B (right), 20 games per panel: printed examples pull both models' quotes, Qwen onto the printed values and gpt-oss just under them; with no numbers both collapse to the floor; told to maximise joint profit with only the formula, gpt-oss reaches its usual range and Qwen does not." | Usable now: axis words already in plain English. Add n per panel and state in the caption that the y-scales differ. |
| X2 | `work_scratch/oss_analysis/out_t2/step2/figures/fig_forest_by_family.png` (gpt-oss) beside Qwen `step2/figures/fig_forest_by_family.png` | the lever set transfers in sign | "Lever forest by family, arm minus control with 95% CI, 19 to 20 pairs per row; left gpt-oss-20b, right Qwen3-32B thinking on." | Yes: no cross-model forest exists. Best option: draw a paired forest (two points per lever) from `lever_table.csv` (price index and profit gain). Until then, set the two side by side, both too large for a column. |
| X3 | Qwen `step3/figures/lead_fig4_anchoring.png` | the Qwen anchoring result (anchored vs neutral run), as context for X1 | keep the Qwen caption; add "no anchored run exists for gpt-oss" | no |
| X4 | `out_t2/step2/figures/heat_arm_levels.png` (gpt-oss) | gpt-oss levels by arm, including the lower no-chat baseline | "Five metrics by arm, gpt-oss-20b, 20 games per arm." | Check the arm codes on the axes; replace them with words. |

Table X (section 2 above) is the suggested paper table. No existing PNG shows the two baselines side by side (Qwen and gpt-oss headline cells plus joint-profit controls). That would need a small new bar chart from `cell_means.csv`; it is optional.


Created by Claude at the prompting of the repository owner.
