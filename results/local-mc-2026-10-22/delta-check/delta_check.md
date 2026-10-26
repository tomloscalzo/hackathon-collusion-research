# Delta check: why sustainability falls from delta 0.8 to 0.99

**Verdict: EXPECTED.** The solver matches spec eq. (11) exactly. The effect comes from one calibration choice, flagged at the end.

**Where it happens.** 239 cells are sustainable at 0.8 and CORNER_ZERO at 0.99. All 239 have tick = 0.25 and pEvidence = 0.3. Sustainable share by block, delta 0.8 -> 0.99:

| block | 0.8 | 0.99 |
|---|---|---|
| tick 0, pEv 0.3 | 0.795 | 0.815 |
| tick 0, pEv 1.0 | 0.654 | 0.667 |
| tick 0.25, pEv 0.3 | 0.785 | **0.420** |
| tick 0.25, pEv 1.0 | 0.617 | 0.619 |

So the whole aggregate drop is in one block. Everywhere else, patience helps a little, as textbook intuition says.

**Mechanism.** With a tick, the static-Nash margin is s^N = s0 + j\*·tick, so the Nash profit pi^N is positive. The base scenario keeps pi_post = 0, so Z_post = 0 while Z = pi^N/(1 - delta). By eq. (11), a trigger without evidence (probability 0.7 of triggers here) sends the coalition below static Nash forever. That costs (Z - Z_post) = pi^N/(1 - delta), which grows 20-fold from delta 0.8 to 0.99. The IC constraint is not the problem: theta_hat = 1 and theta_star_given_participation > 0 in these cells. What fails is participation, because W(theta) < W(0) = Z.

**Worked numbers** (N = 2, phi = 0, s0 = 1, s̄ = 3, Q0 = 100, j\* = 1, s^N = 1.25, pi^N = 7.292, theta grid {0, 1/3, 2/3, 1}; reproduced by `hand.py`, which matches the CSV w_star/w0):

- Cells 162/7938 (slope 0.025, rhoTip 0.01, F = 0):
  - delta 0.8: W = 36.46 / 59.36 / 72.61 / **75.91**, so theta\* = 1 (CSV 75.910).
  - delta 0.99: W = **729.17** / 614.99 / 636.70 / 597.03, so theta\* = 0 (CSV 729.167).
  - Counterfactual with pi_post = pi^N at 0.99: W(2/3) = 988.36 > 729.17, so it is sustainable again.
- Cells 150/7926 (slope 0.025, rhoTip 0, F = 2083):
  - delta 0.8: W(1/3) = **42.19** > Z = 36.46 (CSV 42.1875).
  - delta 0.99: W(1/3) = 614.50 < Z = 729.17, so theta\* = 0.
  - Counterfactual with pi_post = pi^N: W(1/3) = 809.60, so it is sustainable.

There is no fine in the first pair, so the effect is not a fine scaled by 1/(1 - delta). It is the absorbing post-trigger state.

**Sentence for the paper:** "When a trigger that yields no evidence permanently pushes the market below its tick-supported non-cooperative profit, a more patient coalition has more of that baseline profit stream to lose, so collusion fails the participation constraint at high delta even though it remains self-enforcing."

**Caveat (calibration, not code).** In tick cells, pi_post = 0 < pi^N, which the spec allows (pi_post ≤ pi^N). It makes a no-evidence trigger worse for continuation value than an evidence trigger, since evidence returns the coalition to Z. Two readings:
- Intended: the post-trigger reform removes the tick rent. Then the result stands, with the sentence above.
- Not intended: pi_post should default to pi^N, and the anomaly disappears.

The spec author should state which reading is meant.
