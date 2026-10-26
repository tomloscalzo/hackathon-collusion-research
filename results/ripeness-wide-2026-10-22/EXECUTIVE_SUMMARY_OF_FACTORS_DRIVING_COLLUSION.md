# Executive summary of factors driving collusion in the model (2026-10-22)

**Source.** The Layer A solver over 1,036,800 parameter combinations (the wide grid), plus the one-input charts (`oned/`) and the 36 two-input pair charts (`pairs/`). The results are model-generated, not LLM results: they describe what a profit-maximising cartel would do, which is the reference map that the LLM experiments will be compared against. Each number below is an average over all the other inputs.

## Terms
| Symbol | Term | Plain-English meaning |
|---|---|---|
| — | **Share where collusion is chosen** ("how often") | The fraction of scenarios in which a profit-maximising cartel chooses to collude at all |
| θ* | **Chosen collusion intensity** ("how hard") | How far above the competitive spread the cartel prices, from 0 (competitive) to 1 (monopoly) |
| δ | **Patience** | The chance the market continues for another round. High patience means firms care about future profits. |
| N | **Number of market makers** | How many firms quote prices |
| φ | **Preferenced volume share** | The share of orders split evenly among firms whatever the price. Undercutting cannot win it. |
| ι | **Tick size** | The minimum price step |
| slope | **Regulator screen slope** | How strongly wide spreads trigger an investigation by the regulator's automated screen |
| ρ_tip | **Tip probability** | The chance each round that an investigation starts from a tip (whistleblower, complaint), whatever the prices |
| P(evidence) | **P(evidence \| investigation)** | The chance an investigation produces a guilty finding and a fine |
| F ratio | **Fine ratio** | The fine as a multiple of one round of a firm's full-collusion (monopoly) profit |
| s̄/s₀ | **Reservation spread ratio** | The room between cost (s₀) and the spread at which customers stop trading (s̄) |

## 1. The inputs, ranked by impact
| Rank | Input | How often (lowest → highest value) | How hard (θ*) | What it means |
|---|---|---|---|---|
| 1 | **Fine ratio** | 0.67 → 0.05 (fine ratio 0 → 500) | 0.45 → 0.04 | The strongest single force against collusion, but only when something can start an investigation |
| 2 | **Regulator screen slope** | 0.55 → 0.14 (slope 0 → 0.2) | 0.53 → 0.06 | The strongest force on intensity: cartels lower their prices to stay below the screen's notice |
| 3 | **Tip probability** | 0.38 → 0.20 (0 → 5% per round) | 0.25 → 0.14 | Works even when prices look normal, and has a hard cut-off (§2) |
| 4 | **Number of market makers** | 0.35 → 0.19 (N 2 → 10) | 0.27 → 0.12 | More firms need much more patience to hold a cartel together |
| 5 | **Patience** | Rises, then dips at the top (0.17 at δ 0.5, peak 0.37 at 0.9, 0.27 at 0.99) | Same shape | Necessary but not sufficient. In markets with no minimum price step, how often firms collude keeps rising (0.12 → 0.51); the dip comes from markets with a price step (caveats). |
| 6 | **P(evidence \| investigation)** | 0.39 → 0.23 (0.1 → 1) | 0.26 → 0.17 | Works by making the fine likely to be paid, so it matters only alongside a fine |
| 7 | **Tick size** | 0.38 → 0.20 (0 → 0.5) | 0.26 → 0.14 | Partly real (competition already earns a little; the cartel cannot fine-tune its price), partly the modelling simplification (caveats) |
| 8 | Preferenced volume share | 0.26 → 0.33 | 0.17 → 0.24 | Small: protected volume makes cheating pay less, so collusion is slightly easier |
| 9 | Reservation spread ratio | Peaks in the middle (tick-free: falls 0.48 → 0.29) | Peaks in the middle (tick-free: falls) | Small. With no price step, more room makes cartel spreads more visible to the screen and the fine larger relative to a small markup. |

## 2. The combinations that matter most
1. **Detection × penalty is one lever, not four.** In markets with no minimum price step and no tips, collusion is chosen almost exactly when **regulator screen slope × P(evidence | investigation) × fine ratio × (reservation spread ratio − 1)** is below 4. This holds in 98.9% of those scenarios. The inputs substitute for each other: a 10% chance of evidence with a fine ratio of 125 deters exactly as much as certain evidence with a fine ratio of 12.5. For policy and for AI oversight, this means the cheapest component can be scaled up instead of all of them.
2. **No detection, no deterrence.** With a regulator screen slope of 0 and no tips, collusion runs at full intensity whatever the fine; even a fine ratio of 1,000 does nothing.
3. **A sensitive screen with a heavy fine removes collusion.** With a regulator screen slope ≥ 0.05 and a fine ratio ≥ 125, collusion is chosen in 1.1% of scenarios. A gentle screen is not enough on its own: at slope 0.01 with a fine ratio of 125, 22% still collude.
4. **Tips have a hard threshold.** Collusion becomes impossible once tip probability × P(evidence | investigation) × fine ratio exceeds 1. At the ripe baseline, a 5% per-round tip probability removes collusion.
5. **Patience × number of market makers follows the textbook threshold.** A cartel of N firms holds roughly when patience δ ≥ 1 − 1/N. That means about 0.5 for 2 firms, 0.75 for 4 and 0.9 for 10. Impatient markets with many firms almost never collude. Once patience is high, the number of firms stops mattering.
6. **Very patient cartels collude more gently.** They have more future profit to lose to an investigation, so they choose lower, less conspicuous prices: how often they collude stays high while intensity eases.

## 3. Ranges to remember
- **Most collusion-prone:** regulator screen slope 0, no tips, fine ratio ≤ 5, 2–4 market makers, patience 0.8–0.9, no minimum price step. Every one of these 720 scenarios colludes, at full (monopoly) intensity.
- **Near collusion-proof:** regulator screen slope ≥ 0.05 with a fine ratio ≥ 125, where 1.1% collude. Alternatively, a 5% tip probability once the fine ratio exceeds 20 ÷ P(evidence | investigation).
- **Borderline (where LLM behaviour is most informative):** a moderate regulator screen slope (0.025–0.05), a moderate fine ratio (12.5–25) and patience 0.9–0.95. Small changes in the inputs flip whether a rational cartel colludes, so an LLM's departures from the rational choice are easiest to see. Our ripe baseline sits here.

## 4. Caveats
- **Modelling simplification in markets with a minimum price step.** There, an investigation that finds nothing is treated as worse for firms than a conviction: post-investigation profit is set to zero, while ordinary competition still earns a small profit. This drives the dip at the highest patience, part of the tick-size effect, and the rise of collusion with P(evidence | investigation) when there is no fine. It is a recorded limitation (FUTURE_DIRECTIONS §6). None of the findings for markets with no price step depend on it.
- **Detection ends collusion permanently.** Re-formation and repeat offending are not modelled, so the map is conservative about how often collusion pays.
- **Prisoner's-dilemma-style collusion only.** Every finding on patience, number of market makers and preferenced volume share comes from each firm's temptation to break ranks. They do not apply to shared-objective coordination (all agents pursuing one goal, as in the Hugging Face incident), which has different incentives and is not modelled.
- **Averaging.** The averages depend on the grid's ranges. The directions and the product rule do not.
- **Theory map, not LLM data.**
