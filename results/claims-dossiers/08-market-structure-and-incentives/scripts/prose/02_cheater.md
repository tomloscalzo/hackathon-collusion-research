## 2. G-cheater: the planted cheater, and the cheater-as-rival issue

**What is compared.** `n3-cheater: three firms, third plays a planted cheater` is compared with `n3-group: three firms, private chat` (three LLM firms) and with `headline-chat: private chat, no other lever` (two LLM firms). The scripted firm is not an LLM. It quotes a fixed **1.88** every round (1 + 0.4395 x 2, the theory's three-firm collusive margin) and drops to **1.00 once**, in round 6 to 10 depending on the seed. It never reacts to anyone. The LLM firms typically quote 2.2 to 2.5, so the scripted firm is the lowest quote from round 1 and takes most customers. Neutral run, private chat, penalty point 3.

**The claim as now stated.** The scripted firm lowers the market price on both models, but almost entirely by construction. Adding its fixed quotes to the three-LLM games, with the LLM quotes left as played, already reproduces most of the fall in the price index: -0.22 of the -0.23 fall on gpt-oss, and -0.26 of the -0.31 fall on Qwen thinking on. In the market price the LLM firms barely react; their own quotes fall by 0.17 on gpt-oss (where they mostly stay above the cheater) and by 0.34 on Qwen thinking on (where the competitive share also rises). There is no price war: the market returns to the scripted 1.88 the round after its single drop.

**Re-derived (match: yes, for the pipeline definitions).**
- gpt-oss against n3-group (n 18): price -0.232, pgi -0.330, competitive share -0.067 and matching +0.059, as in the ledger and the cheater ad hoc report.
- Qwen thinking on: pgi -0.439 (against n3-group) and -0.473 (against headline-chat), competitive share +0.306 and matching -0.415, as in the ledger.
- The frozen Qwen numbers file gives -0.424 for the n3-cheater minus n3-group gain index (thinking on). That is 0.015 smaller than the value re-derived here and in the ledger. A separate script built that file from an earlier table, and the difference changes no conclusion.

**Against three-firm chat (`n3-group`), all five metrics plus the corrected versions:**

{{TABLE:n3-cheater|n3-group}}

**Against two-firm chat (`headline-chat`):**

{{TABLE:n3-cheater|headline-chat}}

{{TERMS_CELL}}

**How much of the price fall is mechanical.** Each three-LLM (`n3-group`) game was replayed on paper with the paired cheater game's scripted quotes added as an extra quote. The paired game has the same seed, so the drop falls in the same round. The LLM quotes were left as they were played. The fall in this counterfactual is the part caused by the scripted quote alone; the rest is the LLM firms' reaction. This check is close to tautological: with a fixed 1.88 quote in the market, the price index is capped at about 0.44, so the residual can only register LLM undercutting below 1.88, not the LLM firms' movements above it. Their own quotes (the 'Mean LLM firm quote' row above) are the better measure of their reaction.

| Model and mode | n3-group as played | n3-group + scripted quotes (no reaction) | n3-cheater as played | Mechanical part [95% CI] | Behavioural residual [95% CI] (p) |
|---|---|---|---|---|---|
| gpt-oss-20b (reasoning medium), 18 pairs | 0.610 | 0.388 | 0.378 | -0.222 [-0.270, -0.172] | -0.009 [-0.029, +0.009] (0.37) |
| Qwen3-32B thinking on, 20 pairs | 0.675 | 0.411 | 0.370 | -0.264 [-0.314, -0.211] | -0.041 [-0.078, -0.011] (0.013) |
| Qwen3-32B thinking off, 20 pairs | 0.597 | 0.354 | 0.387 | -0.243 [-0.309, -0.175] | +0.033 [-0.011, +0.088] (0.24) |

<small>

| Term | Meaning |
|---|---|
| values | mean price index over games (market quote = the lowest quote of the round over all seats) |
| mechanical part | paired mean of (the n3-group game with the scripted quotes added) minus (the same game as played) |
| behavioural residual | paired mean of (n3-cheater as played) minus (n3-group with the scripted quotes added); negative = the LLM firms priced lower than a market with no reaction would have; sign-flip p over pairs |
| CI | 95% percentile bootstrap over (wording, seed) pairs, 10,000 resamples |

</small>

This also explains why the frozen Qwen numbers show a much smaller cheater effect in the anchored run (gain index -0.114 against n3-group, thinking on). In that run the coalition already sat near 2.09, close to the scripted 1.88, so a fixed 1.88 quote takes less off the price.

**The cheater-as-rival issue (owner observation 12) and the five metrics in three-firm games.** The scripted seat has no quote row in the pipeline's tables, so the competitiveness code scores each LLM firm only against the other LLM firm. The effect on each metric:

| Metric | Affected? | Effect in `n3-cheater` games |
|---|---|---|
| (a) average absolute spread | no | the market quote already includes the scripted firm |
| (b) price index | no | as for (a) |
| (c) profit gain index | definitional | it averages the LLM firms only. Counting all seats (the market's total profit), the fall is -0.22 on gpt-oss instead of -0.33, and -0.30 on Qwen thinking on instead of -0.44; both clearly negative |
| (d) competitive share | **yes** | with the scripted firm as a rival, gpt-oss's competitive share *falls* by 0.19 [0.10, 0.29] (pipeline: -0.07, null); Qwen thinking on's rises by 0.17 [0.08, 0.27] (pipeline: +0.31) |
| (e) matching share | **yes** | with the scripted firm as a rival: gpt-oss -0.10 [-0.24, +0.04] (pipeline +0.06); Qwen thinking on -0.53 (pipeline -0.42); Qwen thinking off -0.87 (pipeline 0.00), because thinking-off Qwen firms keep matching each other far above the cheater |
| all five, in `n3-group` and `n3-ethics` games | no | every seat is an LLM, so the two definitions agree exactly |

With the corrected rival set the model contrast gets sharper, not weaker. gpt-oss's LLM firms mostly let the cheater undercut them (41% of their rounds are above 1.88) and become the lowest quote *less* often. Qwen thinking-on firms partly chase it down (33% of rounds above 1.88), and Qwen thinking-off firms ignore it (90% above).

**Evidence across both models.**
- *Supporting:* the price fall is large and certain on both models (Holm < 0.001).
- *Contrary or limiting:* the fall is almost all by construction, so it is not evidence that LLM coalitions break. The firms are responding to a scripted defector that never reacts, and the arm adds a firm and a rule at once. On gpt-oss, n3-cheater ran in earlier waves (1 to 10) than n3-group (101 to 110), so a drift between waves is not excluded from the n3-cheater vs n3-group contrast.
- *Reaction measures:* the cheater ad hoc report found a rival undercut within 3 rounds of the drop in 11 of 16 gpt-oss games and 9 of 16 Qwen games. These rest on 16 games each.

**Strength.** Exploratory. The cheater ad hoc report lists n3-cheater minus n3-group and minus headline-chat as its declared contrasts, but the run declaration has no prediction for them. Unit: game, paired on (wording, seed); n is 18 or 20 on gpt-oss and 20 on Qwen. Price index -0.232 [-0.286, -0.172] on gpt-oss and -0.305 [-0.363, -0.245] on Qwen thinking on, Holm < 0.001 (family: the 8 price-index contrasts per model and mode). The behavioural residual on gpt-oss is -0.009 [-0.029, +0.009], with an MDE of about 0.03.

**Proposed status: downgraded** to: "a scripted low-price firm lowers the market price by construction; in the market price the LLM firms barely react (residual -0.01 on gpt-oss, -0.04 on Qwen thinking on), and their own quotes fall by 0.17 on gpt-oss and 0.34 on Qwen thinking on". The part "without Qwen's switch from matching to undercutting" is **confirmed and sharpened** under the corrected rival set. Sub-questions 1.2, 3.2 and 2.3 (the metric definition matters).

**Main-text sentence.** A scripted firm that undercuts at a fixed price lowers the market price on both models, but almost entirely by taking the business itself: the LLM firms barely react in the market price (-0.01 on gpt-oss-20b, -0.04 on Qwen3-32B thinking on), while their own quotes fall by 0.17 and 0.34, and there is no price war.

**Appendix sentence.** Against three-LLM chat, the cheater arm lowers the price index by 0.23 on gpt-oss (18 pairs) and by 0.31 on Qwen thinking on (20 pairs). Adding the scripted quotes to the three-LLM games, with no change in LLM behaviour, reproduces 0.22 and 0.26 of those falls. The pipeline does not count the scripted firm as a rival; when it is counted, gpt-oss's competitive share falls by 0.19, while Qwen thinking on's rises by 0.17 and its matching falls by 0.53. So gpt-oss firms let the cheater undercut them, whereas Qwen firms partly chase it down.
