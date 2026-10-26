# Checks behind analysis.json

The analyses were written by an analysis agent on 2026-10-22, and the main session spot-checked them against `tables.json`. Every 3-decimal number cited in `analysis.json` traces to its own pair table or to `splits_log.txt`. `build_check.py` rebuilds `analysis.json` from `analysis_src.py` and checks the cited numbers. Splits were computed from `wide.csv` (1,036,800 cells, 0 errors) with `load.py` / `q.py`. `wide.csv` is not committed; regenerate it with `grids/wide.yaml`.

## Model facts checked in the code
- s₀ = 1; tick sizes are absolute. The screen hazard is slope × (s − s^N), in absolute markup.
- The punishment is a price war at s₀ (π_p = 0); q = 1, k = ∞.
- **fineRatio = F / π_c(1)**: the fine divided by one round of a firm's full-collusion (monopoly) profit (`RipenessGrid.java`, the `fineRatio` branch). Earlier labels saying "competitive profit" were wrong and have been corrected everywhere.
- pEvidence = ρ_coop at d̄u = 0.
- Without a tick, Z = Z_post = 0, so collusion pays exactly when π_c > ρ_E·F at some θ. That involves neither δ nor φ, and N only scales both sides by 1/N. All three matter only through the incentive constraint.
- With a tick, the artifact term δ(ρ_T − ρ_E)π^N/(1−δ) drops out when P(evidence) = 1.

## Splits (key numbers)
1. δ×N share, N = 2 by δ: tick-free 0.408, then 0.511 flat; tick cells 0.355 → 0.128. Tick-free θ* at δ 0.99 by N: 0.302, 0.302, 0.302, 0.301, 0.293.
2. Knife-edge cells: 1,230 cells have 0 < θ* < 0.001, at (δ 0.5, N 2, φ 0) and (δ 0.9, N 10, φ 0). Excluding them would move the share 0.319 → 0.266 and 0.254 → 0.201. They are kept, as in the tables.
3. P(evidence) = 1, tick share at δ 0.9 → 0.99: tick 0.25 goes 0.290 → 0.293 (all P(evidence): 0.380 → 0.188); tick 0.5 goes 0.202 → 0.205 (0.241 → 0.110). θ* at tick 0.25: 0.222 → 0.202.
4. Zero fine, share by P(evidence): tick 0 is flat at 0.741; tick cells rise 0.555 → 0.780.
5. δ×P(evidence) at δ 0.99: tick-free 0.705 → 0.360; tick cells 0.114, 0.108, 0.124, 0.249.
6. P(evidence)×F product rule (tick 0): pEv 0.1 × fine 125 equals pEv 1.0 × fine 12.5 (share 0.380, θ* 0.264); 0.3 × 25 equals 0.6 × 12.5 (0.493).
7. Screen scaling (tick 0): slope 0.1 at s̄/s₀ 2, 0.05 at 3 and 0.025 at 5 all give share 0.419 and θ* 0.282. At slope 0 the share is 0.593 for every s̄/s₀; at fine 0 it is 0.741 for every s̄/s₀.
8. Participation rule (tick 0, no tip): collusion is chosen iff sustainable and slope × P(evidence) × fineRatio × (s̄/s₀ − 1) < 4. It holds in 113,790 of 115,020 cells, with 180 cells at K exactly 4 skipped; the exceptions are knife-edge cells with θ* < 0.001. Slope × fine products 0.01 × 500, 0.1 × 50 and 0.2 × 25 all give 0.272.
9. Tip floor: if ρ_tip × pEv × fineRatio > 1, collusion is impossible; a 5% tip gives 0.000 at fines ≥ 250.
10. At fine 500, 68.1% of colluders have no screen and no tip. The share is 0.787 in those cells and 0.016 elsewhere.
11. j*: φ raises it only at N ≤ 3 (N = 2, tick 0.25: 1 → 2–3). Tick 0.5 with s̄/s₀ 2 leaves 0 collusive steps; tick 0.25 with s̄/s₀ 2, and tick 0.5 with s̄/s₀ 3, leave 1.
12. Sustainable share (θ̂ > 0) by tick 0 / 0.25 / 0.5: N = 10 is 0.465 / 0.628 / 0.473; φ = 0 is 0.625 / 0.790 / 0.615.
13. N×tick share at P(evidence) = 1: N = 2 is 0.349, 0.279, 0.195; N = 10 is 0.177, 0.183, 0.126.
14. θ* among colluders by tip (0, 0.01, 0.05):
    - δ 0.9: 0.693, 0.733, 0.749
    - δ 0.99: 0.589, 0.659, 0.733
    - tick-free, slope 0.01: 0.703, 0.824, 0.897
    - tick-free, slope 0: 1.000 at every tip level
15. Tick-free θ* among colluders by δ 0.5 → 0.99: 0.713, 0.741, 0.723, 0.702, 0.677, 0.588; with slope > 0, 0.643 → 0.489.
16. Tick-free δ×slope θ*: at slope 0.01, 0.529 → 0.464 from δ 0.95 to 0.99. At slope 0, θ* equals the share; CORNER_ONE is 51.2% of slope-0 cells.
17. δ×tip: the tick-free share with no tip is 0.605; with a 5% tip it is 0.409 at δ 0.99. Tick cells: 0.416 → 0.248 with no tip, 0.057 with a 5% tip.
18. δ×φ:
    - tick-free at δ 0.5: share 0.040, 0.102, 0.204; θ* 0.008, 0.080, 0.159
    - at δ 0.99: tick cells 0.156, 0.148, 0.142; tick-free 0.509–0.511
19. N×φ, N = 2: tick-free 0.459, 0.511, 0.511; tick cells 0.312, 0.262, 0.253; tick 0.25 only 0.375, 0.321, 0.310. Sustainable share at N = 10 by φ: 0.388 → 0.679.
20. Sustainable share at N = 10: 0.541 → 0.481 across slopes and 0.546 → 0.479 across tips. At N = 2: 0.915–0.921.
21. N×P(evidence), tick-free: N = 2 0.681 → 0.349; N = 10 0.338 → 0.177.
22. Tick×slope at P(evidence) 1 and no tip, at slope 0.2: share 0.156, 0.127, 0.084; θ* 0.059, 0.060, 0.042.
23. Tick×tip at P(evidence) 1: 0.365 → 0.172, 0.351 → 0.154, 0.240 → 0.111.
24. Tick-free share falling across s̄/s₀ 2 → 12:

    | Condition | Share at s̄/s₀ 2 → 12 |
    |---|---|
    | δ 0.99 | 0.642 → 0.390 |
    | N = 2 | 0.621 → 0.377 |
    | φ 0.6 | 0.545 → 0.331 |
    | no tip | 0.614 → 0.346 |
    | pEv 0.1 | 0.616 → 0.427 |
    | fine 25 | 0.606 → 0.255 |

    Tick-free θ* at fine 0 falls 0.619 → 0.375. Tick cells at δ 0.99 rise 0.064 → 0.184.
25. Slope 0.2 by P(evidence): tick-free 0.385 → 0.141; tick cells 0.124, 0.083, 0.075, 0.101.
26. Tick-free, 5% tip, P(evidence) 0.6 → 1.0: 0.225 → 0.172.
27. Share of cells in the interior regime where the incentive constraint binds: by φ 0.066, 0.061, 0.046; by δ 0.108 → 0.005.

## Fixes made in the agent's self-check
- delta__N share: corrected the range and the δ row it refers to.
- delta__slope: "row maxima" changed to "column peaks"; "≥¾" changed to "⅔–⅘".
- delta__sBarRatio θ: the 0.25-tick case at s̄/s₀ 2 is θ* = 0 or 1, not near zero.
- N__tick θ: removed the span-normalisation claim.
- slope__fineRatio θ: removed the unverified product rule.
- slope__pEvidence: named the P(evidence) range for the tick-cell rise.
- Split four single-sentence texts into two.
- Marked mechanisms that have no split of their own as "likely".
