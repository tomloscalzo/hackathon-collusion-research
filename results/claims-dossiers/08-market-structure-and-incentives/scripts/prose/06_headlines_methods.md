## 6. The Qwen headline claims in this area

This section checks the headline claims from the frozen Qwen numbers that touch this dossier's arms, against both models.

| Headline claim (frozen Qwen numbers) | Re-derived on Qwen | On gpt-oss | Proposed wording |
|---|---|---|---|
| "A planted cheater lowers prices with no price war" | price index -0.395 against two-firm chat and -0.305 against three-firm chat (thinking on); -0.22 and -0.21 (thinking off) | -0.233 and -0.232 | "A scripted firm that undercuts at a fixed price lowers the market price, mostly by taking the business itself; in the market price the LLM firms add little (-0.04 on Qwen thinking on, -0.01 on gpt-oss), though their own quotes fall (-0.34 and -0.17), and there is no price war." |
| "Incentives are about 0 (bounded nulls)" | thinking on: joint profit -0.064 [-0.135, +0.013], profit target -0.017 [-0.098, +0.060]; thinking off: +0.136 and +0.089, wide | profit target +0.036 [-0.046, +0.133]; joint profit +0.103 [+0.007, +0.204], with matching +0.27 | Confirmed for Qwen thinking on. Add: "on gpt-oss the joint-profit text makes firms match far more often." |
| "3 vs 2 firms is about 0 (bounded null)" | thinking on -0.090 [-0.194, +0.013]; thinking off -0.013 [-0.202, +0.175] | +0.006 [-0.083, +0.108] | Confirmed on both models, as a bound of about ±0.1 to ±0.2 in price index. |
| "The ethics rule is about 0" (three-firm and two-firm, on price) | three-firm +0.016 [-0.069, +0.097] (thinking on); two-firm -0.007 | three-firm **-0.223 [-0.359, -0.098]**; two-firm -0.018 | Confirmed for Qwen on price; on gpt-oss the three-firm ethics rule is a real price lever. |

<small>

| Term | Meaning |
|---|---|
| values | paired price-index differences, arm minus control, with 95% bootstrap CIs over 20 (wording, seed) pairs (18 or 15 where gpt-oss games failed); neutral run, penalty point 3, private chat |
| three-firm ethics rule | n3-ethics minus n3-group; two-firm ethics rule: m-asym minus headline-chat |

</small>

## 7. Data, methods and issues found

- **Data.** The neutral-run game tables for gpt-oss-20b (reasoning medium; 840 planned games) and Qwen3-32B (both thinking modes), restricted to the arms above at penalty point 3 with status done. For each counted game, the raw round-by-round log of the game actually played, so truncation reruns replace the originals. 455 games in all.
- **Re-derivation.** An independent script recomputes all five metrics from each game's per-round quotes and payoffs. On all 455 games the spread, price index, profit gain index, competitive share and matching share equal the game-table values (the largest absolute difference is 0.00005, from rounding).
- **Statistics.** Pairs are (wording, seed). CIs are 95% percentile bootstraps over pairs (10,000 resamples, fixed seed). Tests are exact two-sided sign-flips over all 2^n sign patterns. Holm is applied within each model, mode and metric over this dossier's 8 contrasts. MDE = 2.8 x SE. Everything here is exploratory.
- **Issues found.**
  1. The pipeline's competitive and matching shares never count the scripted cheater as a rival (owner observation 12). In cheater games this reverses the sign of gpt-oss's competitive-share change (section 2).
  2. The arm glossary (now corrected in this branch) and the game table described the scripted firm as one that "undercuts once and otherwise holds its quote", which understated it. It holds a fixed 1.88, below the LLM firms from round 1, and drops to 1.00 once, so it undercuts them every round.
  3. The game table records the 3 failed gpt-oss n3-ethics games as timeouts; the ethics-rule ad hoc report and the ledger call them EmptyContent failures.
  4. Several ledger q-values come from Step 2's Benjamini-Hochberg procedure and do not survive the exact paired test with Holm used here: the m-inc-joint price effect, and the Qwen thinking-off explicit-talk arms.
- **Files.**
  - `scripts/derive_games.py`: the per-game re-derivation; writes `games_rederived.csv`.
  - `scripts/contrasts.py`: the paired contrasts; writes `contrasts.csv`.
  - `scripts/extras.py`: the robustness checks, the mechanical counterfactual and the correlations; writes `extras.csv`.
  - `scripts/tables.py`, `scripts/figure.py`, `scripts/build_md.py` and `scripts/prose/`: the report tables, the figure and the assembly of this report.
