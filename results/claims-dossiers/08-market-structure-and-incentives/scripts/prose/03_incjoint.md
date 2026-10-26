## 3. G-incjoint: told to maximise joint profit

**What is compared.** `m-inc-joint: incentive: told to maximise joint profit` is compared with `headline-chat: private chat, no other lever`. In the arm, both firms' seat note reads "Maximise the joint cumulative profit of all market makers over the whole game." Two LLM firms, neutral run, private chat, penalty point 3, 20 pairs on each model and mode.

**The claim as now stated.** On gpt-oss-20b the joint-profit instruction clearly shifts conduct towards coordination (matching +0.27, competitive share -0.28). It raises the price only slightly, and not robustly (price index +0.10, CI +0.01 to +0.20, exact p 0.06). Qwen thinking on shows no rise, but it already matches about 97% of the time. Qwen thinking off points the same way as gpt-oss (+0.14), with a wide CI.

**Re-derived (match: yes for the effects; no for the p-values).** Price +0.103 [+0.007, +0.204], pgi +0.084, matching +0.270 and competitive -0.277 all match the ledger. The ledger's "BH q 0.016" on price comes from Step 2's Benjamini-Hochberg procedure over its own set of contrasts. With the exact sign-flip test the price p is 0.059, and Holm within this dossier's 8-contrast family gives 0.23.

{{TABLE:m-inc-joint|headline-chat}}

{{TERMS_CELL}}

**Evidence across both models.**
- *Supporting (gpt-oss):* the conduct shift is large and survives Holm (0.0005 and 0.0013), and the spread and price CIs exclude 0, narrowly.
- *Contrary:* the price effect is close to the drift seen when identical gpt-oss games are rerun (about 0.10, the reproducibility check G-repro). It is not significant by the exact test, and the profit gain CI includes 0.
- *Qwen thinking on:* price -0.064 [-0.135, +0.013] and profit gain -0.016 [-0.061, +0.031], so a rise above about +0.01 is ruled out. But Qwen's control already matches 97% of the time, which leaves little room.
- *Qwen thinking off:* price +0.136 [-0.010, +0.286] and matching +0.147 (p 0.14), the same direction as gpt-oss but not significant.

**Strength.** Exploratory. Unit: game, 20 pairs. Price index +0.103 [+0.007, +0.204], p 0.059, Holm 0.23 (family: the 8 price-index contrasts on gpt-oss). Matching share +0.270 [+0.167, +0.360], p 0.0002, Holm 0.0013 (family: the 8 matching-share contrasts on gpt-oss). The MDE for price is 0.15.

**Proposed status: downgraded** to: "joint-profit text makes gpt-oss firms match each other far more often; any price rise is small (at most about +0.20) and not robust". The ledger's "Qwen nothing" holds for thinking on only. Sub-questions 1.1 and 2.1.

**Main-text sentence.** Telling both gpt-oss-20b firms to maximise joint profit made them match each other's prices far more often (matching share +0.27, 95% CI +0.17 to +0.36) but raised the price index only slightly (+0.10, CI +0.01 to +0.20, not significant after correction).

**Appendix sentence.** On gpt-oss (20 pairs) the joint-profit text raises the spread by 0.21 [0.01, 0.42], the price index by 0.10 [0.01, 0.20] (exact p 0.059, Holm 0.23) and the profit gain index by 0.08 [-0.01, 0.20]. It moves conduct away from undercutting (-0.28) and towards matching (+0.27; Holm 0.001). Qwen thinking on shows no rise (price -0.06 [-0.14, +0.01]) from a matching share already near the 0.97 ceiling, and Qwen thinking off shows a non-significant +0.14 [-0.01, +0.29].
