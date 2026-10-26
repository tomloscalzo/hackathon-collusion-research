# Model vs LLM: do the pre-sprint model's collusion thresholds carry over to LLM agents?

## Orientation

Two (sometimes three) LLM "market makers" play a repeated pricing game. Each round, each firm quotes a **half-spread** (the distance from the mid-price to its bid and ask) from 1.00 to 5.00 in steps ("ticks") of 0.01. 1.00 is the competitive level (costs covered, no excess profit); 3.00 is the monopoly price; 70% of customers go to the lowest quote. A regulator investigates more often when prices are higher, and the **penalty point** (p1 light to p5 heavy) sets the fine. Games last 7 to 20 rounds, and the firms are told there is about a 95% chance of another round after each one.

**Question.** Before the sprint, the owner built a model of when collusion pays (the "Layer A" solver: a profit-maximising cartel, with no LLM involved). It gave four rules: a detection × penalty threshold, a tip threshold, a patience threshold and a sustainable collusive price θ\*. This report asks whether these rules predict what LLM agents do.

**Arms compared.** We compare the same game at different fines (penalty points 1, 3, 4, 5), with two firms or three, with or without a private chat, and under three ways of showing payoffs: evenly spaced example prices (neutral), example prices that include the theory price 2.09 (anchored), and the exact profit formula with no example prices (formula).

**Data.** gpt-oss-20b is the primary evidence: 720 finished games, neutral run plus the formula arms, tier t2 table, with reasoning effort medium (its only mode). Qwen3-32B is secondary evidence, because its first implementation had known problems that the gpt-oss runs mostly fixed: 1,360 neutral games and 1,360 anchored games (thinking on and off), plus 100 formula and no-numbers games (thinking on). Cells are planned at 20 games, one per (wording, seed) pair (5 paraphrases with 4 seeds each, 20 distinct seeds); a few cells have fewer finished games (for example 17 to 19 in the three-firm and formula arms). "Tier t2" is the gpt-oss Step 1 table that includes all three replication waves. The Qwen problems that the gpt-oss runs addressed included prompt anchoring on the printed 2.09, and thinking calls truncated at the token cap. All contrasts are **exploratory**, since none of these model-versus-LLM comparisons was pre-declared in this form.

> **How to read the metrics** (all per game, averaged over the rounds played; source columns in the Step 1 run table)
>
> | Metric | Definition | Direction |
> |---|---|---|
> | Average absolute spread (`market_price_mean`) | Mean market quote (the best half-spread) in raw units, 1.00 to 5.00 | higher = more collusive |
> | Price index (`price_index`) | (market price − 1) / 2 per round, clipped to [0, 1], averaged over rounds: 0 = competitive 1.00, 1 = monopoly 3.00. Example: a game held at 2.09 has price index 0.545 | higher = more collusive |
> | Profit gain index (`profit_gain_index`) | (profit − competitive profit) / (monopoly profit − competitive profit); 0 = competitive, 1 = joint monopoly | higher = more collusive |
> | Competitive share (U16, `competitive_share`) | Share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both firms are at 1.00 | higher = more competitive |
> | Matching share (`matching_share`) | Share of firm-rounds in which the firm's quote equals the lowest rival quote of the previous round, above 1.00 (the coordination signature) | higher = more collusive |
> | θ\* (theta-star) | The model's sustainable collusive level, on the price-index scale; θ\* = 0 means a rational cartel does not collude | — |
> | s\* | The theory price: s\* = 1 + 2θ\*. It is 2.41 at p1, 2.09 at p3, 1.65 at p4 and 1.00 at p5 (two firms) | — |
> | pair, CI, sign-flip p, Holm | A **pair** is one (wording, seed) combination, meaning one of 5 paraphrases times one of 4 seeds, played under both arms of a contrast. **CI** = 95% percentile bootstrap over pairs (2,000 resamples). **p** = exact two-sided sign-flip permutation test over pairs (all 2^n sign patterns). **Holm** = step-down correction within a named family (defined in §4) | — |

## 1. Findings at a glance

The three columns are the model's prediction, Qwen3-32B (secondary) and gpt-oss-20b (primary). Price-index differences are paired and reported as mean [95% CI]. The model's predicted difference is in parentheses.

| Threshold / prediction | Model (Layer A) prediction for the LLM cells | Qwen3-32B (secondary) | gpt-oss-20b (primary) | Verdict |
|---|---|---|---|---|
| **Detection × penalty composite** C = slope × P(evidence) × fine ratio × (s̄/s₀ − 1); collude iff C < 4 | C = 0.25 / 1.25 / 2.5 / 5.0 at p1 / p3 / p4 / p5. Collusion at p1 to p4 and none at p5. Price index 0.70 → 0.55 → 0.32 → 0 | **Thinking on:** falls in the right order (Pearson 0.51 to 0.76 with θ\*). p5 − p1: chat −0.31 [−0.48, −0.14] (−0.70); no chat −0.53 [−0.66, −0.39]. Crossing the threshold without chat (p5 − p4): −0.32 [−0.44, −0.19] (−0.32), a step matching the model. **Thinking off:** the p5 − p1 chat difference is bounded between −0.10 and +0.20 (point +0.05), so the predicted −0.70 is excluded. At p5, chat still holds price index 0.54 (on) and 0.67 (off) | Falls only between p3 and p5 (there is no p4 cell). Chat p3 − p1: +0.04 [−0.02, +0.10] (−0.16), which excludes the predicted fall; p5 − p3: −0.19 [−0.30, −0.07] (−0.55); no chat p5 − p1: −0.19 [−0.31, −0.07] (−0.70). Pearson with θ\* 0.37 to 0.41. At p5, where the model says "no collusion", chat holds 0.42 and no chat 0.20 | **Direction holds; size and the zero do not.** Over p5 − p1, LLMs move 20 to 45% of the predicted distance (no chat with thinking on: 76%). Smaller steps vary: Qwen thinking on moves 52 to 70% of the predicted p3 − p1 and p4 − p1 falls; gpt-oss moves the wrong way from p1 to p3. LLMs over-collude past the threshold with printed examples |
| Same threshold, formula presentation (exact profit rule, no example prices) | As above: p1 0.70, p5 0 | p5: 0.04 (θ\* 0). p1: 0.34 (θ\* 0.70). p5 − p1 −0.29 [−0.37, −0.21] | p5: 0.06 (θ\* 0). p1: 0.27 (θ\* 0.70). p5 − p1 −0.21 [−0.36, −0.08] | **Near zero at p5, but not a threshold response.** The formula lowers prices by a similar amount at p1 (where collusion pays) and p5. Its p5 − p1 slope (30% and 42% of the predicted distance) is no more model-like than the headline arms', and with nothing printed, 1.00 is the obvious default |
| **Tip threshold** ρ_tip × P(evidence) × fine ratio > 1 removes collusion | Not testable: every LLM scenario has ρ_tip = 0, so the product is 0 in every cell | — | — | **Untested** (design gap) |
| **Patience** δ ≥ 1 − 1/N | δ = 0.95 exceeds 0.50 (N = 2) and 0.67 (N = 3); with 30% captive flow (φ = 0.3) the bar falls to 0.41 and 0.58. So N = 3 still colludes, with θ\* down from 0.546 to 0.440 (−0.106) | Thinking on: three firms − two firms −0.09 [−0.19, +0.01] (−0.11). Thinking off: −0.01 [−0.20, +0.17]. Three-firm prices stay high (0.60 to 0.68) | Three firms − two firms +0.01 [−0.08, +0.11] (−0.11); three-firm price index 0.61 | **Holds in the weak sense tested** (no collapse at N = 3). The small predicted drop is borderline for gpt-oss (just outside its CI) and consistent for Qwen thinking on. The threshold itself is never crossed: that would need N > 20 at δ = 0.95 |
| **θ\* level** (the 2.09 theory price at p3) | Prices should sit at s\* = 2.41 / 2.09 / 1.65 / 1.00 (p1 / p3 / p4 / p5) whatever the payoff presentation | Anchored table (2.09 printed in every cell): 57% of thinking-on quotes are exactly 2.09 at p1, where s\* = 2.41, and 60% at p3, where s\* = 2.09. Mean price about 1.98 at both. The anchored table lowers prices everywhere, which moves them closer to s\* at p3 to p5 and further from it at p1. Neutral: 0 to 1.6% of quotes within 2 ticks of s\* at p1 to p4; the mode is the printed 2.50 or 2.49 | Neutral: 0 to 6.5% of quotes within 2 ticks of s\* at p1 and p3 (mode 2.49, the printed example). Formula p1: 0% near 2.41 (mean quote 1.54) | **Fails.** LLM prices track printed numbers, not θ\*. The anchored run's apparent hit at 2.09 is a focal point that coincides with θ\* only at p3 |

**Bottom line.** The model's comparative statics transfer in sign: heavier expected fines lower LLM prices, and a third firm does not break collusion. Its levels and its knife-edge do not. Where the model says collusion is not sustainable (p5), LLMs given printed example prices still hold price indices of 0.2 to 0.7. Where it says collusion pays (p1), LLMs given no printed numbers barely collude (0.01 to 0.34). The missing ingredient is coordination: Layer A assumes the cartel can agree on θ\*, and LLMs coordinate on salient printed numbers instead of computing it. The formula presentation brings p5 prices near the model's zero (0.04 to 0.06), but it lowers p1 prices by a similar amount, so this does not show that the agents computed the threshold.

## 2. From an algorithmic-agent model to LLM agents (draft paper section)

**The model.** Before the sprint, the owner wrote a layered hypothesis model of collusion among AI agents (`model/MODEL_SPEC.md`). Its Layer A is the economics of the opportunity. N symmetric market makers quote half-spreads above a cost s₀. Customers' volume falls linearly to zero at a reservation spread s̄. A share φ of the flow is captive (split evenly whatever the quotes), and the rest goes to the best quote. A cartel chooses an intensity θ ∈ [0, 1] (its price, from competitive to monopoly) to maximise its per-member value W(θ) (eq. 11). W includes a regulator's screen, which starts an investigation with probability slope × (markup), a tip rate ρ_tip, a probability P(evidence) that an investigation finds proof, and a fine F. The choice is subject to the incentive constraint that no member gains from undercutting once, given grim-trigger punishment and patience δ (eq. 8′). The solution θ\* is the sustainable collusive level (eq. 12).

**What the model found.** A sweep of the solver over 1,036,800 parameter combinations found four simple rules:
1. In tick-free markets with no tips, collusion is chosen exactly when it is sustainable (the incentive constraint holds) and slope × P(evidence) × fine ratio × (s̄/s₀ − 1) < 4. The wide-grid README reports this in 98.9% of those cells and attributes the rest to knife-edge cells; we did not re-check that attribution.
2. Collusion is impossible once ρ_tip × P(evidence) × fine ratio > 1.
3. A cartel of N firms holds roughly when δ ≥ 1 − 1/N.
4. Between these limits, the expected penalty sets an interior θ\* below monopoly (MODEL_SPEC §2.7). This is our summary of the solver's regimes, not one of the executive summary's numbered items, which also include "no detection, no deterrence" and "very patient cartels collude more gently".

The first rule has a one-line derivation. With no tick, the competitive profit is zero, so collusion pays at some price only if, at small markups, the per-round profit (s − s₀)Q(s₀)/N exceeds the per-round expected fine slope × (s − s₀) × P(evidence) × F. Writing F as a multiple of one round of monopoly profit, Πᵐ = Q₀(s̄ − s₀)²/(4s̄N), gives slope × P(evidence) × fine ratio × (s̄ − s₀) < 4, with no dependence on δ or N. With the absolute-markup screen this equals the (s̄/s₀ − 1) form because s₀ = 1. Because volume falls with price, the comparison at small markups decides it at every price. The threshold is therefore myopic: a one-round comparison is enough to see it.

**What validated it.** The validation was internal consistency, not behaviour:
- **Solver checks.** The engine's unit tests re-solve each scenario's annotated θ\* to within 0.0005. An independent Python re-implementation written for this report (`layer_a.py`) reproduces all six annotated LLM-scenario values to four decimals: 0.7029, 0.6262, 0.5459, 0.3249 and 0 for two firms at fines 100 to 2000, and 0.4395 for three firms at fine 500.
- **Monte Carlo.** A Monte Carlo of scripted (non-LLM) strategies ran 5 market families × 7 strategies × 2 friction levels, with 1,000 runs per cell for the collusion statistics and 300 for profits (`results/local-mc-2026-10-22/`). It confirmed that the game engine's realised payoffs agree with the solver's classification:
  - in the ripe market, adhering to the cartel earns +209 net of fines per run, against +92 for cheating once and 0 for competing;
  - in the myopically unripe market (fine 5,000), adhering loses −1,346;
  - with four firms the collusion premium shrinks to +36.
- **Delta check.** A hand verification (`results/local-mc-2026-10-22/delta-check/`) traced the one counter-intuitive pattern in the map, collusion becoming rarer at the highest patience. It comes from a calibration choice in markets with a minimum price step, not from a coding error. That choice does not affect the tick-free LLM scenarios.

The model was therefore validated as a correct solver of its own equations. It had never been confronted with agents that must work out those equations for themselves.

**Taking it to LLMs.** The LLM game reuses the same engine and scenario files: the same payoffs, screen and fines. So the model makes a parameter-free prediction for every LLM cell (§3). The LLM design varies only the fine (penalty points), the number of firms and the communication channel, so only part of the model can be tested (§7).

## 3. Mapping the LLM game onto the model's parameters

This section sets out what each model parameter is in the LLM scenarios (scenario files `slice-m-p1` to `slice-m-p5`, `n3-group` and `n3-cheater` in the engine's scenario folder) and what the model predicts for every LLM cell.

| Model parameter | Value in the LLM scenarios | Source and meaning |
|---|---|---|
| Screen slope | 0.025, applied to the absolute markup (`LEVEL`, `ABSOLUTE_MARKUP`) | The prompt tells the firms: investigation probability = 0.025 × (best quote − 1.00), at most 1 |
| P(evidence \| investigation) | 1 (`rhoCoop: 1`, chat logs not counted as evidence: `dBarU: 0`) | Every investigation finds evidence and fines, so the expected penalty is the fine |
| Fine F (per firm) | p1 100, p2 300, p3 500, p4 1000, p5 2000 (p2 was not played) | `enforcement.fine` |
| Fine ratio F/Πᵐ | Two firms (Πᵐ = 40): 2.5, 7.5, 12.5, 25, 50. Three firms (Πᵐ = 26.7): 3.75 to 75 | Πᵐ = one round of a firm's monopoly profit = (3 − 1) × 100 × (1 − 3/5) / N |
| Tip probability ρ_tip | 0 | `rhoTip: 0` in every LLM scenario |
| Patience δ | 0.95 | Random horizon with ending hazard h = 0.05 (`delta0: 1`); the firms are told about a 95% chance of another round. The hidden cap is 40 rounds; games were pre-drawn to 7, 15, 19 or 20 rounds |
| N | 2 (all arms except the three-firm ones), 3 (n3-group, n3-ethics, n3-cheater) | `market.n` |
| Cost s₀, reservation s̄, ratio s̄/s₀ | 1.00, 5.00, so the ratio is 5 | Monopoly price (s₀ + s̄)/2 = 3.00 |
| Captive share φ | 0.3 (70% of volume goes to the best quote) | `market.phi` |
| Tick | 0 in the solver; quotes are on a 0.01 grid | `tick: 0.0`, `quoteIncrement: 0.01` |
| Punishment | Grim trigger, price war at 1.00 (k = ∞, q = 1) | `punishment: PRICE_WAR`, `punishmentLength: -1` |
| Exit | An opened investigation ends the game, so the trigger hazard equals the penalty hazard (ρ_T = ρ_E) | The prompt says "An opened investigation ends the game"; 177 of 819 finished gpt-oss games ended this way. This is the model's exit hazard in eq. (11): the lost future rents add to the fine |

**Table 3.1. The model's prediction for every LLM cell** (Layer A solver, tick-free; the predicted columns are the same for every arm within a row, because Layer A has no channel through which chat, wording, ethics rules or printed examples change payoffs)

| Penalty point, firms | Composite C | Collude? (C < 4) | θ\* (price index) | s\* (price) | Profit gain index at θ\* | Predicted competitive / matching share | LLM arms in this cell (gpt-oss; Qwen) |
|---|---|---|---|---|---|---|---|
| p1, N = 2 | 0.25 | yes | 0.703 | 2.41 | 0.912 | 0 / 1 | gpt-oss: headline (chat, tacit), formula and no-numbers arms, D set, introspection, moral primes, watchdog (445 games); Qwen: headline, D set, introspection, formula and no-numbers arms |
| p3, N = 2 | 1.25 | yes | 0.546 | 2.09 | 0.794 | 0 / 1 | headline chat, controls, ethics rule (m-asym), incentives, 5-tick start (gpt-oss 160 games; Qwen 480 per run) |
| p3, N = 3 | 1.875 | yes | 0.440 | 1.88 | 0.686 | 0 / 1 | n3-group, n3-ethics, n3-cheater (gpt-oss 55; Qwen 120) |
| p4, N = 2 | 2.5 | yes | 0.325 | 1.65 | 0.544 | 0 / 1 | Qwen headline only (120 per run) |
| p5, N = 2 | 5.0 | **no** | 0 | 1.00 | 0 | 1 / 0 | gpt-oss headline chat and tacit, formula chat (60); Qwen headline (120) and formula chat (20) |

<small>

| Term | Meaning |
|---|---|
| Composite C | slope × P(evidence) × fine ratio × (s̄/s₀ − 1) = 0.025 × 1 × (F/Πᵐ) × 4. Collusion pays at some price iff C < 4 (tick-free, no tips) |
| θ\*, s\* | The solver's constrained-optimal collusion intensity (eq. 12) and the price 1 + 2θ\* it implies; identical to the `theory-theta-star` annotation in each scenario file |
| Profit gain index at θ\* | Joint profit at s\*, (s\* − 1) × 100 × (1 − s\*/5), over the joint monopoly profit 80 |
| Predicted competitive / matching share | Stylised: a cartel holding s\* > 1.00 never undercuts (competitive share 0) and always matches (matching share 1); at θ\* = 0 both firms sit at 1.00 (competitive share 1, matching share 0) |
| headline, D set, introspection, moral primes, watchdog, ethics rule, incentives, 5-tick start | The project's arm families: the baseline chat/tacit game; reply self-scores and the reasoning-monitor threat; questions after each round; ethical role texts; a watchdog that questions firms; a 'do not coordinate prices' rule for one firm; profit targets or joint-profit goals; a round-1 price limit. None of them changes Layer A payoffs. However, the controls (told to quote 1.00, or to maximise joint profit) and the incentive arms (joint-profit goal, profit target) change the firms' objective, so the profit-maximiser's θ\* does not apply to them; they are flagged `objective_changed = 1` in `cells_theory_vs_observed.csv` and are not used in any test |
| m-asym | Two firms, private chat, p3; one firm (llm2) gets the rule 'do not coordinate prices', the other a placebo text |
| n3-group / n3-ethics / n3-cheater | Three firms, private chat, p3 / the same with one firm given the ethics rule / two LLM firms and a scripted firm that undercuts once |
| Formula / no-numbers arms (fx-, nx-) | The payoff block prints the exact profit rule as equations with no example prices / prints neither examples nor formula |

</small>

Every cell file with the observed means beside the prediction is `cells_theory_vs_observed.csv`. The theory curve at all five points for N = 2 and 3 is `theory_curve.csv`.

## 4. Test 1: does the price index fall as the composite crosses its threshold?

**What is compared.** For each communication arm, the same (wording, seed) pair is played at a heavier and a lighter penalty point. The difference is taken within the pair and averaged; the model's predicted difference is θ\*(heavier) − θ\*(lighter). The arms are:
- **headline-chat:** a private chat before each round;
- **headline-tacit:** no chat, so the firms see only past quotes and profits;
- **headline-monitored** (Qwen only): the chat plus the notice "A regulator reads all messages in this chat, as they are sent." This is text only; the investigation probability is unchanged;
- **fx-chat:** private chat with the formula payoff block and no example prices.

**Holm families** (exploratory, on each metric separately): gpt-oss penalty family = 5 contrasts (chat p3 − p1, chat p5 − p1, chat p5 − p3, tacit p5 − p1, formula p5 − p1); Qwen penalty family = 13 contrasts with thinking on (12 headline plus the formula contrast) and 12 with thinking off.

**Table 4.1. Penalty contrasts, all five metrics: paired difference [95% CI] (model's predicted difference)**

| Model | Contrast | Pairs | Average absolute spread | Price index | Profit gain index | Competitive share | Matching share | Price index p / Holm p |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | headline-chat p3 − p1 | 20 | +0.08 [−0.04, +0.20] (−0.31) | +0.04 [−0.02, +0.10] (−0.16) | +0.04 [−0.03, +0.10] (−0.12) | +0.01 [−0.12, +0.15] (+0.00) | −0.04 [−0.18, +0.10] (+0.00) | 0.238 / 0.238 |
| gpt-oss-20b | headline-chat p5 − p3 | 20 | −0.38 [−0.60, −0.15] (−1.09) | −0.19 [−0.30, −0.07] (−0.55) | −0.23 [−0.37, −0.09] (−0.79) | +0.02 [−0.07, +0.11] (+1.00) | −0.05 [−0.13, +0.04] (−1.00) | 0.006 / 0.023 |
| gpt-oss-20b | headline-chat p5 − p1 | 20 | −0.30 [−0.57, −0.02] (−1.41) | −0.15 [−0.29, −0.01] (−0.70) | −0.19 [−0.35, −0.03] (−0.91) | +0.03 [−0.09, +0.16] (+1.00) | −0.08 [−0.21, +0.03] (−1.00) | 0.049 / 0.097 |
| gpt-oss-20b | headline-tacit p5 − p1 | 20 | −0.39 [−0.63, −0.13] (−1.41) | −0.19 [−0.31, −0.07] (−0.70) | −0.30 [−0.45, −0.14] (−0.91) | −0.01 [−0.12, +0.11] (+1.00) | −0.01 [−0.11, +0.10] (−1.00) | 0.007 / 0.023 |
| gpt-oss-20b | fx-chat (formula) p5 − p1 | 19 | −0.43 [−0.72, −0.17] (−1.41) | −0.21 [−0.36, −0.08] (−0.70) | −0.26 [−0.42, −0.11] (−0.91) | +0.02 [−0.07, +0.12] (+1.00) | −0.08 [−0.18, +0.02] (−1.00) | 0.005 / 0.023 |
| Qwen3-32B t1 | headline-chat p5 − p1 | 20 | −0.62 [−0.96, −0.29] (−1.41) | −0.31 [−0.48, −0.14] (−0.70) | −0.26 [−0.42, −0.11] (−0.91) | +0.13 [+0.03, +0.26] (+1.00) | −0.15 [−0.28, −0.04] (−1.00) | 0.002 / 0.009 |
| Qwen3-32B t1 | headline-tacit p5 − p4 (the crossing step) | 20 | −0.64 [−0.88, −0.38] (−0.65) | −0.32 [−0.44, −0.19] (−0.32) | −0.47 [−0.62, −0.31] (−0.54) | +0.14 [+0.00, +0.27] (+1.00) | −0.25 [−0.38, −0.13] (−1.00) | <0.001 / 0.003 |
| Qwen3-32B t1 | headline-tacit p5 − p1 | 20 | −1.07 [−1.32, −0.78] (−1.41) | −0.53 [−0.66, −0.39] (−0.70) | −0.65 [−0.80, −0.49] (−0.91) | +0.24 [+0.07, +0.39] (+1.00) | −0.38 [−0.51, −0.24] (−1.00) | <0.001 / <0.001 |
| Qwen3-32B t1 | fx-chat (formula) p5 − p1 | 20 | −0.59 [−0.75, −0.42] (−1.41) | −0.29 [−0.37, −0.21] (−0.70) | −0.46 [−0.57, −0.34] (−0.91) | +0.62 [+0.44, +0.80] (+1.00) | −0.68 [−0.84, −0.50] (−1.00) | <0.001 / <0.001 |
| Qwen3-32B t0 | headline-chat p5 − p1 | 20 | +0.10 [−0.20, +0.40] (−1.41) | +0.05 [−0.10, +0.20] (−0.70) | +0.05 [−0.06, +0.18] (−0.91) | +0.02 [−0.14, +0.16] (+1.00) | −0.05 [−0.21, +0.11] (−1.00) | 0.559 / 1.000 |
| Qwen3-32B t0 | headline-tacit p5 − p1 | 20 | −0.11 [−0.33, +0.09] (−1.41) | −0.05 [−0.17, +0.05] (−0.70) | −0.11 [−0.25, +0.01] (−0.91) | +0.01 [−0.15, +0.22] (+1.00) | −0.01 [−0.27, +0.23] (−1.00) | 0.326 / 1.000 |

<!-- ci-forest:1 -->
![CI forest chart for the table above (4. Test 1: does the price index fall as the composite crosses its threshold?): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/MODEL_VS_LLM_ci01.png)

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

<small>

| Term | Meaning |
|---|---|
| Contrast "arm pX − pY" | For each (wording, seed) pair: the metric in the arm at penalty point X minus the same arm at point Y. Negative on the spread, price index, profit gain index and matching share, or positive on competitive share, means less collusion at the heavier fine |
| (value in parentheses) | The model's predicted difference: θ\*, s\*, profit gain index at θ\* or the stylised shares, at X minus at Y (Table 3.1) |
| Pairs | Number of (wording, seed) pairs with a finished game in both cells (19 where one formula game did not finish) |
| t1 / t0 | Qwen3-32B with thinking on / off; gpt-oss-20b has one mode (reasoning effort medium) |
| Data | gpt-oss neutral run, tier t2, done and primary games, build-bug replicate arms excluded; Qwen neutral run (headline arms) and the Qwen formula run (fx-chat, thinking on) |
| CI, p, Holm p | 95% percentile bootstrap over pairs (2,000 resamples); exact sign-flip permutation p over pairs; Holm within the penalty family of that model and metric |

</small>

The full set with all Qwen arms, the p3 and p4 steps and every metric is `contrasts_paired.csv`. **Sensitivity check:** averaging in the five gpt-oss build-bug replicate arms, which played the identical headline prompt, gives chat p5 − p1 = −0.19 [−0.28, −0.10], the same direction as the primary −0.15.

**Figure 4.1. Observed price index against the composite, with the model's θ\* curve**

![Price index vs composite](fig_price_vs_composite.png)

*Title:* observed LLM price index vs the Layer A model's θ\* by detection × penalty composite. *Left:* gpt-oss-20b, neutral run, n = 139 games (headline-chat p1, p3, p5; headline-tacit p1, p5; formula chat p1, p5). *Middle:* Qwen3-32B thinking on, neutral run, n = 280 (three headline arms at p1, p3, p4, p5, plus formula chat p1, p5 from the formula run). *Right:* Qwen3-32B thinking off, neutral run, n = 240. *Measured:* the per-game price index (`price_index`), shown as the mean over games with a 95% bootstrap CI. *x-axis:* the composite C (log scale), labelled with the penalty point and fine; points are nudged sideways so they do not overlap. *Black line:* the model's θ\* as the fine varies continuously from 0 to 2,400. *Dashed line:* the threshold C = 4, above which the model predicts no collusion. Higher = more collusive. Values are in `fig_price_vs_composite_values.csv`.

**Legend for Figure 4.1** (series labels in the chart come from `tools/analysis_style/arm_labels.py`; the meanings below are the shared glossary's short labels)

**Columns (x-axis): penalty point** (with the composite C = 0.25, 1.25, 2.5, 5.0)

| Slug | Meaning |
|---|---|
| p1 | penalty point 1: fine 100 (lightest) |
| p3 | penalty point 3: fine 500 (ripe middle point) |
| p4 | penalty point 4: fine 1000 |
| p5 | penalty point 5: fine 2000 (heaviest) |

**Rows (y-axis): price index**

| Metric | Meaning | Direction |
|---|---|---|
| price_index | (market price - 1) / 2: 0 at the competitive 1.00, 1 at the 3.00 monopoly price. Higher = more collusive. | higher = more collusive |

**Series (colour and marker)**

| Slug | Meaning |
|---|---|
| headline-chat (blue circle) | private chat, no other lever |
| headline-tacit (orange square) | no chat, no other lever |
| headline-monitored (green triangle) | chat read by the regulator |
| fx-chat-p1 / fx-chat-p5 (pink diamond) | formula, private chat, p1 / formula, private chat, heavy fine p5 |
| Layer A model (black line) | θ\*, the sustainable collusive level a profit-maximising cartel chooses |

**Panels**

| Slug | Meaning |
|---|---|
| gpt-oss-20b | gpt-oss-20b, reasoning effort medium (its only mode) |
| t1 | thinking on (Qwen3-32B) |
| t0 | thinking off (Qwen3-32B) |

**Table 4.2. Correlation of the observed per-game price index with the model's θ\* for that game's cell**

| Model | Games | n | Pearson r (permutation p) | Spearman ρ (permutation p) |
|---|---|---|---|---|
| gpt-oss-20b | headline-chat (p1, p3, p5) | 60 | 0.37 (0.003) | 0.36 (0.005) |
| gpt-oss-20b | headline-tacit (p1, p5) | 40 | 0.41 (0.010) | 0.39 (0.012) |
| gpt-oss-20b | headline chat + tacit pooled | 100 | 0.39 (<0.001) | 0.31 (0.002) |
| gpt-oss-20b | fx-chat formula (p1, p5) | 39 | 0.43 (0.003) | 0.42 (0.010) |
| Qwen3-32B t1 | headline-chat (p1, p3, p4, p5) | 80 | 0.51 (<0.001) | 0.54 (<0.001) |
| Qwen3-32B t1 | headline-tacit (p1, p3, p4, p5) | 80 | 0.76 (<0.001) | 0.68 (<0.001) |
| Qwen3-32B t1 | headline-monitored (p1, p3, p4, p5) | 80 | 0.56 (<0.001) | 0.59 (<0.001) |
| Qwen3-32B t1 | fx-chat formula (p1, p5) | 40 | 0.76 (<0.001) | 0.81 (<0.001) |
| Qwen3-32B t0 | headline-chat | 80 | −0.10 (0.38) | −0.12 (0.30) |
| Qwen3-32B t0 | headline-tacit | 80 | 0.10 (0.36) | 0.06 (0.58) |
| Qwen3-32B t0 | headline-monitored | 80 | −0.20 (0.07) | −0.20 (0.08) |

<small>

| Term | Meaning |
|---|---|
| Pearson r / Spearman ρ | Linear / rank correlation, across games, between the game's price index and θ\* of its cell (0.703, 0.546, 0.325 or 0). Positive = prices are higher where the model says collusion is more sustainable |
| permutation p | Two-sided, 5,000 random permutations of the observed values |
| n | Games (each cell has up to 20) |

</small>

**Reading.**
- **gpt-oss.** The direction is right, but below the threshold the chat p1 to p3 change is bounded between −0.02 and +0.10 (point +0.04), which excludes the predicted −0.16. The whole fall comes between p3 (C = 1.25) and p5 (C = 5): −0.19 against a predicted −0.55. That is consistent with a threshold-like response, but gpt-oss has no p4 cell, so a cliff at C = 4 cannot be told apart from a fall anywhere between 1.25 and 5.
- **Qwen thinking on.** Without chat, the step across the threshold (p4 to p5) matches the model almost exactly: −0.32 against −0.32. With chat or monitored chat, the same step is only −0.06 and −0.02, and prices at p5 stay high (0.54 and 0.58). Chat keeps collusion alive past the threshold.
- **Qwen thinking off.** Every penalty contrast's CI includes 0 and excludes the predicted fall (for example chat p5 − p1 between −0.10 and +0.20).

## 5. Test 2: does a third firm reduce collusion, as δ ≥ 1 − 1/N predicts?

**What is compared.** n3-group (three LLM firms, private chat, p3) against headline-chat (two firms, private chat, p3), paired on (wording, seed). A second, confounded contrast is n3-ethics (three firms, one told "do not coordinate prices") against m-asym (two firms, one told the same). In m-asym the bound firm is one of two; in n3-ethics it is one of three, so this contrast mixes N with the bound firm's weight. **Holm family:** these 2 contrasts, per model and metric.

**The model's prediction.** At δ = 0.95 the patience condition holds easily: δ ≥ 1 − 1/N needs 0.50 for two firms and 0.67 for three. The model's own incentive condition with 30% captive flow, (1 − φ)(N − 1) ≤ δ/(1 − δ), needs only 0.41 and 0.58. So the model predicts that three firms **still collude**. θ\* falls modestly, from 0.546 to 0.440 (price 2.09 to 1.88), but only because the fixed fine per firm is now large relative to a smaller per-firm profit (the composite rises from 1.25 to 1.875). To cross the patience threshold at δ = 0.95, the market would need more than 20 firms, or more than 28 with φ = 0.3.

**Table 5.1. Three firms minus two firms, all five metrics: paired difference [95% CI] (model's predicted difference)**

| Model | Contrast | Pairs | Average absolute spread | Price index | Profit gain index | Competitive share | Matching share | Price index p / Holm p |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | n3-group − headline-chat (p3) | 18 | +0.01 [−0.16, +0.23] (−0.21) | +0.01 [−0.08, +0.11] (−0.11) | +0.03 [−0.07, +0.16] (−0.11) | −0.00 [−0.18, +0.16] (+0.00) | −0.01 [−0.16, +0.16] (+0.00) | 0.925 / 0.925 |
| gpt-oss-20b | n3-ethics − m-asym (p3) | 17 | −0.43 [−0.71, −0.12] (−0.21) | −0.21 [−0.35, −0.06] (−0.11) | −0.24 [−0.41, −0.06] (−0.11) | +0.10 [−0.05, +0.23] (+0.00) | −0.05 [−0.20, +0.10] (+0.00) | 0.016 / 0.031 |
| Qwen3-32B t1 | n3-group − headline-chat (p3) | 20 | −0.18 [−0.39, +0.02] (−0.21) | −0.09 [−0.19, +0.01] (−0.11) | −0.04 [−0.10, +0.03] (−0.11) | −0.01 [−0.02, +0.01] (+0.00) | +0.02 [+0.00, +0.04] (+0.00) | 0.117 / 0.117 |
| Qwen3-32B t1 | n3-ethics − m-asym (p3) | 20 | −0.13 [−0.26, −0.02] (−0.21) | −0.07 [−0.13, −0.01] (−0.11) | −0.05 [−0.09, −0.01] (−0.11) | +0.04 [−0.04, +0.12] (+0.00) | −0.08 [−0.17, +0.01] (+0.00) | 0.025 / 0.050 |
| Qwen3-32B t0 | n3-group − headline-chat (p3) | 20 | −0.03 [−0.40, +0.34] (−0.21) | −0.01 [−0.20, +0.17] (−0.11) | −0.01 [−0.21, +0.19] (−0.11) | −0.11 [−0.27, +0.01] (+0.00) | +0.08 [−0.08, +0.27] (+0.00) | 0.893 / 1.000 |
| Qwen3-32B t0 | n3-ethics − m-asym (p3) | 20 | +0.10 [−0.19, +0.39] (−0.21) | +0.05 [−0.09, +0.20] (−0.11) | +0.03 [−0.15, +0.20] (−0.11) | −0.11 [−0.26, +0.03] (+0.00) | +0.20 [−0.02, +0.42] (+0.00) | 0.515 / 1.000 |

<!-- ci-forest:2 -->
![CI forest chart for the table above (5. Test 2: does a third firm reduce collusion, as δ ≥ 1 − 1/N predicts?): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/MODEL_VS_LLM_ci02.png)

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

<small>

| Term | Meaning |
|---|---|
| n3-group − headline-chat (p3) | For each (wording, seed) pair: the three-firm private-chat game minus the two-firm private-chat game, both at penalty point 3 (fine 500), same run and mode. Negative = lower prices with three firms |
| n3-ethics − m-asym (p3) | Three firms, one of them told 'Rule you must follow: do not coordinate prices', minus two firms, one of them told the same. Confounded: N and the bound firm's share (1/3 vs 1/2) both change |
| (value in parentheses) | Model's predicted difference: θ\*(N = 3) − θ\*(N = 2) at fine 500, on each metric's scale (Table 3.1) |
| Pairs | 18 and 17 for gpt-oss, where some three-firm games did not finish |
| CI, p, Holm | As in Table 4.1; Holm family = these 2 contrasts per model and metric |

</small>

**Reading.**
- **The weak prediction holds.** Three firms keep colluding in every model and mode. Three-firm price indices are 0.61 for gpt-oss and 0.60 to 0.68 for Qwen, all far above 0.
- **The small predicted drop is mixed.** Qwen thinking on matches it: −0.09 [−0.19, +0.01] against −0.11. For gpt-oss the effect is bounded between −0.08 and +0.11, which narrowly excludes the predicted −0.11.
- **The confounded contrast.** gpt-oss's larger drop in n3-ethics − m-asym (−0.21) cannot be attributed to N alone.

The patience threshold itself is never crossed in this design, so this test confirms that the model is right that N = 3 is not enough to break a patient cartel. It does not test the threshold.

## 6. Test 3: do LLM prices sit near θ\* when it is printed (anchored) and when it is not?

**What is compared.** The anchored Qwen run printed worked payoff examples at 1.00, 1.54, 2.09 and 3.00, plus an undercut example at 2.08 against 2.09. It printed them in **every** cell, although 2.09 equals s\* only at p3. The neutral run printed evenly spaced examples (1.00, 1.50, 2.00, 2.49 against 2.50, 3.00, 3.50, 4.00) and never s\*. gpt-oss has no anchored run, so for gpt-oss the test is neutral against formula. If agents compute θ\*, quotes should sit near s\* = 2.41 at p1 whatever is printed. If they copy printed numbers, anchored quotes should sit at 2.09 at p1 as well.

**Table 6.1. Share of firm-round quotes at the theory price and at printed numbers** (headline arms pooled for Qwen; per arm for gpt-oss)

| Model, payoff table, mode | Penalty point (s\*) | Quotes | Within 2 ticks of s\* | Exactly 2.09 | Exactly 2.49 / 2.50 | Mean quote |
|---|---|---|---|---|---|---|
| Qwen anchored, thinking on | p1 (2.41) | 1,480 | **0.0%** | **56.6%** | 0% / 0% | 2.00 |
| Qwen anchored, thinking on | p3 (2.09) | 1,524 | 72.2% | 59.9% | 0% / 0% | 1.97 |
| Qwen anchored, thinking on | p4 (1.65) | 1,514 | 1.2% | 45.2% | 0% / 0% | 1.81 |
| Qwen anchored, thinking on | p5 (1.00) | 1,648 | 44.5% | 15.4% | 0% / 0% | 1.40 |
| Qwen anchored, thinking off | p1 (2.41) | 1,558 | 0.0% | 33.7% | 0% / 0.3% | 1.79 |
| Qwen anchored, thinking off | p3 (2.09) | 1,534 | 38.5% | 37.1% | 0% / 0% | 1.75 |
| Qwen neutral, thinking on | p1 (2.41) | 1,192 | 1.6% | 0% | 10.5% / 44.7% | 2.58 |
| Qwen neutral, thinking on | p3 (2.09) | 1,396 | 0.0% | 0% | 5.2% / 55.8% | 2.40 |
| Qwen neutral, thinking on | p5 (1.00) | 1,470 | 33.8% | 0% | 0.7% / 23.1% | 1.76 |
| gpt-oss neutral, headline-chat | p1 (2.41) | 489 | 6.5% | 0% | 20.4% / 5.1% | 2.08 |
| gpt-oss neutral, headline-chat | p3 (2.09) | 526 | 0.0% | 0% | 24.3% / 4.0% | 2.21 |
| gpt-oss neutral, headline-chat | p5 (1.00) | 570 | 16.5% | 0% | 19.5% / 4.4% | 1.96 |
| gpt-oss formula, fx-chat | p1 (2.41) | 534 | 0.0% | 0% | 0.2% / 0% | 1.54 |
| gpt-oss formula, fx-chat | p5 (1.00) | 574 | 39.5% | 0% | 0% / 0% | 1.17 |

<small>

| Term | Meaning |
|---|---|
| Anchored / neutral / formula | Payoff table printing example prices including 2.09 / evenly spaced example prices, never 2.09 / the exact profit rule as equations, no example prices |
| Quotes | LLM firm-round quotes (Qwen: all rounds of the headline-tacit, headline-chat and headline-monitored games in that cell, from the comprehension-audit firm-round table; gpt-oss: non-imputed LLM quotes in that arm and cell, from the tier-t2 rounds table) |
| Within 2 ticks of s\* | Share of quotes with \|quote − s\*\| ≤ 0.02. At p5, s\* = 1.00, so this is the share at or within 2 ticks of the competitive floor |
| Exactly 2.09 / 2.49 / 2.50 | Share of quotes equal to that printed value |

</small>

**Paired anchored − neutral (Qwen, headline arms pooled, 60 pairs per cell, pairs = arm × wording × seed).** The gap is |game mean price − s\*|.

| Thinking | Cell (s\*) | Gap to s\*, anchored − neutral [95% CI], p | Price index, anchored − neutral [95% CI], p |
|---|---|---|---|
| on | p1 (2.41) | **+0.15 [+0.06, +0.23]**, 0.002 (anchored further from s\*) | −0.32 [−0.36, −0.28], <0.001 |
| on | p3 (2.09) | −0.26 [−0.35, −0.17], <0.001 (closer) | −0.22 [−0.26, −0.18], <0.001 |
| on | p4 (1.65) | −0.23 [−0.30, −0.16], <0.001 (closer) | −0.15 [−0.20, −0.11], <0.001 |
| on | p5 (1.00) | −0.44 [−0.60, −0.28], <0.001 (closer) | −0.22 [−0.30, −0.14], <0.001 |
| off | p1 (2.41) | +0.22 [+0.11, +0.32], <0.001 (further) | −0.18 [−0.23, −0.12], <0.001 |
| off | p3 (2.09) | −0.01 [−0.13, +0.12], 0.94 | −0.21 [−0.27, −0.14], <0.001 |
| off | p4 (1.65) | −0.32 [−0.40, −0.23], <0.001 (closer) | −0.21 [−0.27, −0.15], <0.001 |
| off | p5 (1.00) | −0.47 [−0.59, −0.34], <0.001 (closer) | −0.23 [−0.29, −0.17], <0.001 |

<!-- ci-forest:3 -->
![CI forest chart for the table above (6. Test 3: do LLM prices sit near θ\* when it is printed (anchored) and when it is not?): estimates with 95% CI bars, red = collusion-direction move, green = competition-direction move, hollow = CI crosses zero](forest/MODEL_VS_LLM_ci03.png)

*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. Source: the numbers printed in the table (committed CSV); nothing recomputed.*

<small>

**Reading the chart.** Each dot is the estimate (centroid) and the bar runs from the CI low to the CI high (the 95% interval from the table directly above; no number is recomputed). The dashed vertical line is zero (no difference). Red = a move in the collusion direction, green = a move in the competition direction (rules of `collusion_colors.direction`), blue-grey = the metric has no collusion direction. A hollow dot means the CI crosses zero, so the difference is not statistically distinguishable from zero; the nearer a bar's end is to the zero line, the more borderline the case. Panels whose scale differs by more than about 3x from the others are marked "own scale".

**Rows (y-axis):** one contrast or attribute per row, labelled as in the table above.

**Panels (x-axis = the difference in that metric):**

| Panel | Direction | Red means | Green means |
|---|---|---|---|
| Price index, anchored − neutral [95% CI], p | higher = more collusive (on the red/green maps: red end) | metric goes up (more collusive) | metric goes down (less collusive) |
| Gap to s\, anchored − neutral [95% CI], p | no collusion direction (neutral hue) | none (blue-grey: no collusion direction) | none (blue-grey: no collusion direction) |

</small>
<!-- /ci-forest -->

<small>

| Term | Meaning |
|---|---|
| Gap to s\* | \|game mean market price − s\*\|, in price units; negative difference = anchored games are closer to the theory price |
| Pairs | 60 per row: the three headline arms × 20 (wording, seed) pairs, matched across the anchored and neutral Qwen runs (same arm, cell, mode, wording and seed) |
| CI, p | 95% percentile bootstrap over the 60 pairs; two-sided sign-flip p from 100,000 random sign patterns (no Holm family: descriptive check). The other three standard metrics for these contrasts are in `qwen_anchored_minus_neutral_pooled.csv`; the profit gain index is lower under the anchored table in every row (−0.15 to −0.24); competitive and matching shares mostly have CIs including 0, except at p5 (thinking on: competitive share +0.14, matching share −0.17) |

</small>

The anchored payoff table lowers the mean price by 0.31 to 0.64 in every cell, whatever θ\* is.

**Reading.** When θ\* is printed (anchored, p3), 60% of thinking-on quotes sit on it. But the same printed 2.09 attracts 57% of quotes at p1, where the theory price is 2.41 and 2.09 is simply a number on the page. Because the anchored table lowers prices everywhere, it moves them closer to s\* wherever the neutral run sat above it (p3, p4, p5) and overshoots below s\* at p1. The movement follows the printed number, not θ\*. Without a printed θ\*, almost no quotes land near it (0 to 6.5% at p1 and p3, both models). That includes the formula arm, which gives the agents everything needed to compute θ\*: they price well below it (gpt-oss mean quote 1.54 against s\* 2.41). The 2.09 seen in the anchored run is a focal point, not evidence that the agents computed the cartel optimum.

## 7. Test 4: the tip threshold, and what the design cannot test

- **Tip threshold.** Every LLM scenario sets ρ_tip = 0, so ρ_tip × P(evidence) × fine ratio = 0 in every cell. **Untested.**
- **Screen slope and P(evidence)** are fixed at 0.025 and 1 in every cell, so the claim that "the components substitute for one another" (only their product matters) cannot be tested. Only the fine varies along the composite.
- **Patience** is fixed at 0.95 (Test 2 only checks that N = 3 is not enough to break the cartel).
- **Communication** has no role in tick-free Layer A with perfect visibility (q = 1, no communication evidence). The model therefore predicts no difference between chat, tacit and monitored chat, but LLM chat raises prices (see the communication analyses) and keeps collusion alive past the threshold (§4).
- **Presentation** (neutral, anchored, formula, none) does not change payoffs, so the model predicts identical play in all of them. The LLM data reject this most strongly. Qwen thinking on at p1 has a price index of 0.85 with printed examples and chat, 0.34 with the formula and 0.11 with no numbers. gpt-oss shows the same pattern: 0.57, 0.27 and 0.02.

## 8. Which predictions hold, which fail, and why

**Hold (in sign).**
1. **Heavier expected fines lower prices** (both models; Qwen only with thinking on).
2. **A third firm does not break collusion at δ = 0.95.**
3. **Prices are near the model's zero at p5 when payoffs are presented as a formula** (price index 0.04 to 0.06, against θ\* = 0). This holds only as a level: the formula lowers p1 prices by a similar amount, so it does not isolate a threshold response.

**Fail.**
1. **The size of the penalty response.** Over p5 − p1, LLMs move 20 to 45% of the predicted distance in most arms (Qwen thinking on without chat: 76%). Smaller steps vary: Qwen thinking on moves 52 to 70% of the p3 − p1 and p4 − p1 falls and 98% of the tacit p4 to p5 step; gpt-oss moves the wrong way from p1 to p3.
2. **The knife-edge.** With printed examples, and especially with chat, LLMs keep colluding past C = 4: this is the model's "over-collusion" failure mode.
3. **The level.** Prices do not sit at θ\*; they sit at printed numbers.
4. **Collusion where it pays but nothing is printed.** With the formula or no numbers at p1, LLMs collude far less than θ\* = 0.70.
5. **Invariance to presentation and to communication.**

**Why.**
- **Coordination is assumed in the model, not solved by the agents.** Layer A takes the cartel's ability to agree on θ\* for granted. LLMs need a coordination device. A salient printed number (2.49/2.50 neutral, 2.09 anchored) or a chat provides it. Without one (formula or no numbers) they rarely coordinate even when collusion pays. With one, they hold the focal price even when the expected fine exceeds the profit.
- **The threshold is a computation the agents mostly skip.** At p5, the expected fine per round, 0.025 × (s − 1) × 2,000 = 50(s − 1), exceeds the collusive profit per firm, 50(s − 1)(1 − s/5) ≤ 40(s − 1), at every price above 1.00. This is a one-round comparison. Agents that work with the formula make it and price near 1.00. Agents reading example tables copy a row instead.
- **Reasoning limits.** Qwen with thinking off did not compute payoffs correctly in an answer-first comprehension quiz (34% even with the formula; §9), and its penalty response is bounded near 0. Qwen with thinking on computes much better and responds partially. gpt-oss responds partially too, but we have no comprehension quiz for gpt-oss, so its computing ability is not measured directly.

## 9. Discussion: non-thinking models (draft paragraph)

The model assumes agents who compute payoffs and best responses. A direct test of that assumption on Qwen3-32B is the comprehension quiz: 23 single-call questions with known answers, 690 calls, the same server and system prompt as the experiments. Without thinking, the model answered **34%** correctly even when given the exact profit formula. It answered 39% with the anchored table and 48% with the neutral table, and the investigation-probability question, a single multiplication, scored 0 to 20%. With thinking and the formula it answered **98%**. The comprehension audit of the played games is consistent with this, though it separates the modes only partly. 88% (thinking off) and 85% (thinking on) of quotes are exactly a printed example value, so echo is common in both modes. The one-round best response is chosen in 2.1% (off) and 5.4% (on) of firm-rounds; the audit warns that holding a high mutual price can be a rational repeated-game choice, so a low best-response rate alone is not evidence of misunderstanding. The clearest mode difference is the reaction to being undercut: 18% of thinking-off firms lower their quote, against 67% with thinking. In the games, the thinking-off agents' response to a twenty-fold increase in the fine is bounded between −0.10 and +0.20 on the price index (point +0.05, with chat), while thinking-on agents respond (−0.31 [−0.48, −0.14]).

We posit, carefully, that next-token language prediction without an explicit reasoning phase is a poor substitute for the numerical and algorithmic best-response reasoning that equilibrium models assume. Note that the quiz asks for the answer before the reasoning, as the experiments' replies do, so it measures what the agents commit to, not what they could reason out given room. A medium open-weight model answering directly appears to retrieve a salient number (a printed example, the rival's last quote) rather than evaluate a payoff function. It therefore coordinates on focal points instead of computing equilibria. This is a hypothesis consistent with our evidence, not a demonstration of mechanism. It rests on one model family in two modes, one replication model, and a quiz that asks for the answer before the reasoning. Its practical implication is a measurement one: whether an LLM "colludes as theory predicts" depends on whether the prompt gives it something salient to copy, so benchmark prompts that print example prices measure echo as much as strategy.

Evidence: the comprehension quiz and comprehension audit (project working folders `comprehension/` and `comprehension_audit/`, produced on 2026-10-25; not yet in the repository); `results/ad-hoc-targeted-analysis/penalty/` (the thinking × penalty interaction); `results/ad-hoc-targeted-analysis/payoff-table-focal-points/` (printed-value shares and the formula / no-numbers arms).

## 10. Methods and limitations

- **Theory.** `layer_a.py` re-implements eqs. (4) to (12) for the tick-free core (π^N = π_post = 0, grim price war at 1.00, uniform-hazard incentive constraint). θ\* is the argmax of W over a 200,001-point grid subject to the constraint. It reproduces every annotated `theory-theta-star` to four decimals.
- **Data and filters.** gpt-oss: games with status done and in the primary set (720), with the five build-bug replicate arms excluded except in the labelled sensitivity check. Qwen neutral: done and primary (1,360). Qwen anchored: done (1,360; the anchored run is not "primary" by contract). Qwen formula run: 100 games of per-game metrics.
- **Statistics.** Unit = game; pairs on (wording, seed); 95% percentile bootstrap over pairs (2,000 resamples, seed 20261026); exact sign-flip permutation p over pairs; Holm within the named families; correlations across games with 5,000-permutation p. All comparisons with the model are **exploratory**. Nulls are reported as bounds.
- **Limited variation.** Only the fine, N and communication vary in the LLM design. Slope, P(evidence), ρ_tip, δ, φ and s̄ are fixed, so the composite is tested along one axis, with three (gpt-oss) or four (Qwen) points. gpt-oss has no p4 cell and no anchored run.
- **Model scope.** The model's p5 zero assumes the agents believe the stated investigation rule and fine, and that grim-trigger enforcement is credible. The LLMs' horizon is randomised but short (7 to 20 rounds), and end-game effects are not modelled.

**Files in this folder**

| File | What it is |
|---|---|
| `layer_a.py`, `corroborate.py`, `figure.py`, `aff.py` | The theory re-implementation, the analysis, the figure, and a CPU-affinity helper. Inputs are local Step 1 tables that are not in the repo: set `HACKATHON_DIR` |
| `cells_theory_vs_observed.csv` | Every LLM cell (model, arm, penalty point, firms, mode): composite, θ\*, s\*, prediction, and observed means of the five metrics |
| `theory_curve.csv` | θ\*, s\*, composite and thresholds at p1 to p5 for N = 2 and 3 |
| `contrasts_paired.csv` | All paired contrasts, five metrics, CI, sign-flip p, Holm p, theory difference, share of theory |
| `correlations_theta_vs_price_index.csv` | Table 4.2 |
| `quotes_at_theory_price.csv`, `qwen_anchored_minus_neutral*.csv` | Table 6.1 and the paired anchored-minus-neutral tests |
| `fig_price_vs_composite.png`, `fig_price_vs_composite_values.csv` | Figure 4.1 and its values |

Created by Claude at the prompting of the repository owner.
