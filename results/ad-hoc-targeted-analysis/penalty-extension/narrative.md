<!-- data_summary -->
**230 new games** (run 2026-10-26, 01:22 to 02:47 ET), all with private chat, the neutral payoff table, reasoning on and 20 (wording, seed) pairs per cell. The pairs are the same as the control cells':
- **gpt-oss-20b, 150 games:**
  - headline-chat at fines 1,000 / 2,500 / 10,000 (59 of 60 planned);
  - ctl-32b-joint at 1,000 / 2,000 / 2,500 / 10,000 (78 of 80);
  - 13 m-inc-joint games.
- **Qwen3-32B, 80 games:** headline-chat and ctl-32b-joint at 2,500 and 10,000 (80 of 80).

**260 existing control games** fill in the other fines:
- gpt-oss: headline-chat at 100 / 500 / 2,000; ctl-32b-joint, m-inc-joint and m-inc-target at 500;
- Qwen, thinking on: headline-chat at 100 / 500 / 1,000 / 2,000; ctl-32b-joint, m-inc-joint and m-inc-target at 500.

**Not run, and why:**
- **gpt-oss m-inc-target** was not launched. The $60 GPU cap could not cover it, and the owner's rule was to drop it first.
- **gpt-oss m-inc-joint** was stopped at 01:42 ET after 13 games, to stay under the cap. Its prompt is identical to ctl-32b-joint, so it only added replicates.
- **Qwen m-inc-joint and m-inc-target** were out of the design.

**Lost games:** 3 gpt-oss games failed twice on an empty model reply (a known gpt-oss serving fault, unrelated to the fine). All are listed in `missing_trials.csv`; none is imputed.

<!-- findings -->
1. **What is rational at heavy fines.** Prices are set by the rules printed in the prompt (continuation 0.95, investigation chance 0.025 x (best quote - 1.00), certain evidence, the game ends, fine F).
   - **A pair quoting the same price** earns about 40 x (s - 1) per firm a round just above cost, and pays an expected fine of 0.025 x (s - 1) x F. Once F is at least about 1,600, every common price above 1.00 loses money in every round, at any patience. So θ* and the fine-aware joint optimum are 0 (price 1.00) at fines of 2,000, 2,500 and 10,000. They are 0.325 (1.65) at 1,000 and 0.545 (2.09) at 500. Patience is never the binding constraint: θ* equals the joint optimum.
   - **An own-profit firm facing a high rival** can still gain by undercutting. Taking 85% of the flow, its per-round margin is positive below 5 x (1 - F/3,400), which is 2.06 at F = 2,000 and 1.32 at F = 2,500. Its fine-aware best response to a rival at 2.50 (or 3.00) is 1.48 at 2,000, 1.16 at 2,500 and 1.00 at 10,000.
   - The undercutting chain leaves 1.00 as the only equilibrium price at these fines. A firm that believes its rival will stay high could rationally quote up to that best response: a price index of 0.24 at 2,000, 0.08 at 2,500 and 0 at 10,000. We call this the **belief bound**.
   - At light fines, every common price from 1.00 up to θ* is self-enforcing, so θ* is the top of a **rational range**, not a single point.
2. **Under the default objective ("Earn as much cumulative profit as you can"), both models are under-responsive at heavy fines, even against the belief bound.**
   - gpt-oss-20b: 0.42 [0.34, 0.50] at 2,000, 0.28 [0.18, 0.39] at 2,500 and 0.33 [0.26, 0.41] at 10,000, against bounds of 0.24, 0.08 and 0.
   - Qwen3-32B: 0.54 [0.41, 0.67], 0.59 [0.45, 0.71] and 0.47 [0.33, 0.61].
   - No adjacent step from 2,000 to 10,000 survives Holm. gpt-oss shows a nominal -0.14 [-0.26, -0.02] from 2,000 to 2,500 that does not continue to 10,000.
   - In the new own-profit games at 10,000, 21% (gpt-oss) and 30% (Qwen) of games end with every firm paying the fine.
   - Per tenfold rise in the fine, the price index falls by 0.16 (gpt-oss) and 0.20 (Qwen). This is a descriptive slope; θ* is kinked (it reaches 0 at 2,000), so the slope is not a test against theory.
   - At light fines the picture differs by model:
     - gpt-oss's default arm is inside the rational range at 100, 500 and 1,000;
     - Qwen is above θ* at every fine (by +0.14 to +0.28), and above even the belief bound at 100 and 500.
3. **Told to maximise joint profit, both models respond strongly and end near, but still above, the rational 1.00.**
   - gpt-oss ctl-32b-joint goes from 0.74 at 500 to 0.26 [0.16, 0.37] at 2,000, 0.17 [0.11, 0.25] at 2,500 and 0.10 [0.05, 0.14] at 10,000. The paired change from 500 to 10,000 is -0.65 [-0.69, -0.60] (Holm p < 0.001).
   - Qwen goes from 0.72 to 0.21 [0.11, 0.32] at 2,500 and 0.12 [0.03, 0.23] at 10,000; the paired change is -0.60 [-0.70, -0.49].
   - At 10,000, 55% (gpt-oss) and 70% (Qwen) of the joint-profit games have a price index of at most 0.05, a mean market price within 0.10 of 1.00.
   - At 500 and 1,000 the same arm prices above the joint optimum (gpt-oss +0.20 and +0.31).
4. **The owner's question: are the reactions rational given the parameters (patience, and so on)?**
   - **No.** Of the 24 cells not biased by early stopping, 21 are above the rational benchmark: 11 own-profit cells above the range [0, θ*] and 10 joint-profit cells above the joint optimum. The 3 exceptions are gpt-oss's default arm at the light fines (100, 500 and 1,000), which sits inside the rational range.
   - The conclusion is robust where θ* = 0 (fines of 2,000 or more). There, under the default objective, both models also exceed the belief bound, so no belief about the rival rationalises the observed prices.
   - At a benchmark of 0 a mean price index can only be at or above it. So the informative quantities are the size of the gap and the share of games at the rational price, both shown, not the CI test.
   - The size of the error depends mainly on the **objective sentence**: the own-profit framing ignores most of a heavy fine, and the joint-profit framing heeds most of it. A plausible reading is that "joint profit" makes the shared fine part of the quantity being maximised. That reading is not tested here.
5. **The agents notice the fine, but misweigh it.**
   - In every cell in the table of section 7, 96% to 100% of quote rationales mention the fine, the investigation or the regulator.
   - Of the rationales attached to quotes of 1.50 or more, 10% to 22% call the risk small ("negligible", "minimal", "low risk"), even though at 2,000 or more such quotes lose money in expectation.
   - The examples reason about the investigation *probability* (2.5% to 4% a round), not the expected *cost*. For example, a gpt-oss firm at fine 10,000 proposes "keep regulator risk below 4%" at 2.48. That is an expected fine of about 370 a round, against about 38 of profit.
6. **The five metrics agree.**
   - In the joint-profit arm, heavier fines raise the competitive share and lower the matching share (Qwen 500 to 10,000: competitive +0.77, matching -0.78).
   - In the own-profit arm these shares hardly move (gpt-oss 500 to 10,000: competitive -0.04, matching -0.02). The high prices that remain under the default objective are still coordinated: the firms match.

<!-- text -->
| Model | Objective arm | Fine | n games | Chat messages that mention the fine, investigation or regulator | Quote rationales that mention them | Rationales with a quote of 1.50 or more that mention them and call the risk small (n such rationales) |
|---|---|---|---|---|---|---|
| gpt-oss-20b | headline-chat | 1,000 | 20 | 0.74 | 0.96 | 0.14 (403) |
| gpt-oss-20b | headline-chat | 2,500 | 20 | 0.73 | 0.98 | 0.14 (254) |
| gpt-oss-20b | headline-chat | 10,000 | 19 | 0.67 | 0.97 | 0.12 (292) |
| gpt-oss-20b | ctl-32b-joint | 1,000 | 20 | 0.72 | 0.97 | 0.14 (436) |
| gpt-oss-20b | ctl-32b-joint | 2,000 | 19 | 0.70 | 0.97 | 0.11 (250) |
| gpt-oss-20b | ctl-32b-joint | 2,500 | 19 | 0.79 | 0.98 | 0.21 (219) |
| gpt-oss-20b | ctl-32b-joint | 10,000 | 20 | 0.75 | 0.98 | 0.17 (139) |
| Qwen3-32B | headline-chat | 2,500 | 20 | 0.94 | 0.98 | 0.20 (379) |
| Qwen3-32B | headline-chat | 10,000 | 20 | 0.90 | 0.99 | 0.12 (251) |
| Qwen3-32B | ctl-32b-joint | 2,500 | 20 | 0.95 | 0.99 | 0.22 (244) |
| Qwen3-32B | ctl-32b-joint | 10,000 | 20 | 0.97 | 1.00 | 0.10 (90) |

<small>Shares over all chat messages, or all quote rationales, of the new games in the cell (source `text_mentions_cells.csv`; the biased m-inc-joint rows are in the CSV only). The last column counts only the rationales of quotes of 1.50 or more, where the risk is not small at these fines. The keyword lists are in `pe_text.py`: "fine" is matched only as "the fine", "fine of" or "fines". Sampled quotes, with their trial ids, are in `text_examples.md`.</small>

The agents almost always mention the fine. The failure is in weighing it, not in noticing it. Three examples:
- gpt-oss at fine 10,000 (`headline-chat__p100__w2__s174__t1`): "Let's both quote 2.48 to split volume and keep regulator risk below 4%."
- Qwen at fine 2,500 (`headline-chat__p25__w1__s94__t1`): "Agreed to maintain 2.50. Mutual cooperation ensures 37.50 per round with minimal regulatory risk." At 2.50 the expected fine is 0.0375 x 2,500, about 94 a round, against 37.50 of profit.
- Some compute correctly. Qwen, told to maximise joint profit, at 10,000 (`ctl-32b-joint__p100__w1__s47__t1`): "Maintaining 1.00 eliminates the risk of regulatory investigations, which carry a 10000 penalty if triggered."

<!-- methods -->
- **Design.** The new games copy the control cells' grid rows: the same arm, condition texts, wording, seed, sampling (temperature 0.6, top-p 0.95, top-k 20), token caps and 16,384-token context window. Only the penalty point, the scenario file and θ* differ. The fine 1,000 cells reuse the existing `slice-m-p4.yaml`.
- **Render check.** For every arm and new fine, the prompt was rendered with a mock model and diffed against p5 (or p3) (`render_check/`). The only changed line is "every market maker pays a penalty of F".
- **Models.** These were served on new H200 apps with the same weights revision, vLLM version and served name as the controls. The gpt-oss twin allows 32 concurrent requests per container (16 for the controls).
- **Statistics.** These are the penalty-gradients methods: paired on (wording, seed), percentile bootstrap (10,000 resamples), exact sign-flip test, and Holm within families. The elasticity is the OLS slope of the game price index on log10(fine), with a pair-clustered bootstrap CI. It is descriptive only: θ* is kinked, and the arms use different sets of fines.
- **Rationality verdicts** (section 6). They use the risk-neutral expected-value benchmarks of section 2.
  - Own-profit arms are compared with the rational range [0, θ*]: inside if the cell-mean CI reaches θ* + 0.05.
  - Joint-profit arms are compared with the joint optimum: at it if the CI covers it or the mean is within ±0.05.
  - The belief bound is each firm's fine-aware best response to a rival who stays at 2.50. It is meaningful for the own-profit arms and is shown for the joint arms for reference only.
  - Risk attitudes are not modelled. A game-by-game best-response test against the rival's actual previous quote was not run, for lack of time.
- **Limitations.**
  - (i) Truncated replies. Some new games had a reply cut at its token cap (up to 8 of 19 games per cell). They were not rerun with a 32k window, but the control tables apply that rerun, so old and new cells differ in truncation handling. Dropping the truncated new games moves no cell mean by more than 0.081 (Qwen headline-chat at 2,500: 0.587 to 0.668; `sensitivity_truncation.csv`). No verdict changes.
  - (ii) Run confound. Each new cell comes from a different run (2026-10-26, new apps) than the control cells. No control cell was rerun as an anchor, so a run or batch effect is folded into contrasts between control and new cells. This includes the 2,000 to 2,500 step.
  - (iii) gpt-oss m-inc-joint. Its 13 games at the new fines are the ones that had finished before the stop at 01:42 ET: they are short (4 to 5 rounds against 11 to 15 elsewhere) and often end in a fine. They are biased by early stopping, shown for completeness only, and excluded from the tallies and the elasticity table. `missing_trials.csv` lists the 67 stopped trials and the 3 failed ones separately.
  - (iv) One run per cell, with 20 pairs; nothing was pre-declared. m-inc-target and Qwen m-inc-joint have no heavy-fine cells.
  - (v) The 3 games that failed on an empty reply might be longer than average; this is unlikely to matter.
  - (vi) GPU spend was about $54 of the $60 cap (metered estimate).