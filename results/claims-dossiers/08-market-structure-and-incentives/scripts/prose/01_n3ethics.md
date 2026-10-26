## 1. G-n3ethics: one firm in three told not to coordinate

**What is compared.** `n3-ethics: three firms, one told not to coordinate` is compared with two controls. In the arm there are three LLM firms; seat 3, the **bound** firm, gets "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently.", and the two **unbound** firms get a placebo sentence about the office canteen. The controls are `n3-group: three firms, private chat` (the clean control: the same market with no text) and `headline-chat: private chat, no other lever` (two firms). Neutral run, private chat, penalty point 3. Pairs are (wording, seed).

**The claim as now stated.** On gpt-oss-20b, giving one of three firms an ethics rule lowers the whole market's price by about a third: the price index falls by 0.22 against three-firm chat and by 0.27 against two-firm chat. The bound firm does not drive it; all three firms come down together. On Qwen3-32B the price does not move (thinking on: +0.016, CI -0.069 to +0.097), although on Qwen thinking on the ethics rule does shift conduct from matching to undercutting.

**Re-derived (match: yes).** The ledger's gpt-oss values are reproduced to the third decimal: against two-firm chat (n 17), pgi -0.30 [-0.45, -0.17] and price -0.27 [-0.38, -0.15]; against three-firm chat (n 15), pgi -0.26 and price -0.22; competitive share +0.16. So are the Qwen thinking-on values (pgi -0.028 and +0.008). The CIs differ only in the last digit (different bootstrap draws).

**Against three-firm chat (`n3-group`), all five metrics:**

{{TABLE:n3-ethics|n3-group}}

**Against two-firm chat (`headline-chat`), all five metrics:**

{{TABLE:n3-ethics|headline-chat}}

{{TERMS_CELL}}

**Robustness (gpt-oss).**

| Check | Price index, n3-ethics minus control [95% CI] | n pairs |
|---|---|---|
| against two-firm chat, all games | -0.271 [-0.390, -0.155] | 17 |
| against two-firm chat, only games with no truncated model call | -0.230 [-0.404, -0.076] (p 0.023) | 9 |
| against two-firm chat, the 3 failed games filled in as "no effect" (diff 0) | -0.230 [-0.340, -0.124] | 20 |
| against two-firm chat, the 3 failed games filled in with the least favourable observed diff | -0.221 [-0.336, -0.110] | 20 |
| against three-firm chat, only games with no truncated call | -0.216 [-0.392, -0.054] (p 0.043) | 9 |

<small>

| Term | Meaning |
|---|---|
| truncated call | a model reply that hit its token cap (8 of the 17 gpt-oss n3-ethics games had at least one) |
| failed games | 3 gpt-oss n3-ethics games (wording 1 seed 47, wording 2 seed 174, wording 3 seed 115) did not finish; the game table records the reason as a timeout (the earlier ad hoc report called them EmptyContent failures) |
| least favourable fill | each missing pair's difference set to the largest (least negative) difference observed, +0.05 |
| p | exact sign-flip permutation p over pairs |

</small>

**The 3 failed games.** The three timeouts fall on pairs whose n3-group control priced *above* the n3-group average (price index 0.50, 0.70 and 0.71, against a mean of 0.605). Their partial logs priced lower than those controls (paired differences of about -0.2 to -0.3), so the missing games point the same way as the observed ones (reviewer's check of the partial logs).

**Who moves.** Within each gpt-oss game, the bound firm's mean quote minus the unbound firms' mean quote is -0.019 [-0.067, +0.029] (17 games), and the bound firm is the strictly lowest quote in only 15% of rounds. So the rule's effect spreads to the whole table, most plausibly through the group chat. The adversarial reviewer's seat-level check agrees: each seat's mean quote falls by about the same amount against the same seat in n3-group (seat 1 -0.39 [-0.66, -0.14], seat 2 -0.38, seat 3, the bound firm, -0.42). On Qwen the bound firm quotes 0.011 below the others with thinking on, and 0.050 below with thinking off (CI -0.121 to 0.000).

**Evidence across both models.**
- *Supporting (gpt-oss):* every price and profit metric falls against both controls, with Holm p from 0.003 to 0.023 in the 8-contrast family. The fall survives dropping the truncated games and filling in the missing ones.
- *Contrary or limiting:* n is only 15 to 17, and the analysis is exploratory. Truncated calls are unbalanced: 8 of the 17 n3-ethics games had one, against 5 of the 18 n3-group games, which is why the no-truncation check above matters. The arm also differs from n3-group by more than the rule: the two unbound seats get a canteen placebo sentence that n3-group lacks. The three cells compared here ran in the same block of waves (n3-ethics and n3-group in waves 101 to 110, the two-firm chat control at p3 in waves 107 to 112), so a drift between early and late waves cannot explain the gap. The effect reaches the whole table rather than the bound firm, so on gpt-oss "an ethics rule on one firm" works as a market-wide signal, not as one honest competitor.
- *Qwen thinking on:* the price index changes by +0.016 [-0.069, +0.097] against three-firm chat (MDE 0.12), so a fall as large as gpt-oss's -0.22 is ruled out. But matching falls by 0.175 [0.082, 0.288] and the competitive share rises by 0.100 [0.029, 0.209] (Holm 0.003 and 0.012) with no change in price, because Qwen's undercuts are single ticks at a high price.
- *Qwen thinking off:* null on every metric, with wide intervals (price MDE 0.27).

**Strength.** Exploratory: there is no pre-declared prediction, and the ethics-rule ad hoc report says so. Unit: game, paired on (wording, seed). n is 15 (against n3-group) and 17 (against headline-chat) on gpt-oss, and 20 on Qwen. Effect on gpt-oss against n3-group: price index -0.223 [-0.359, -0.098], sign-flip p 0.0045, Holm 0.022 (family: the 8 price-index contrasts of this dossier on gpt-oss); profit gain index -0.263 [-0.422, -0.111], Holm 0.023.

**Proposed status: confirmed** (exploratory, moderate strength). Sub-questions 1.5 (a cheap restriction), 1.2 (robustness to replacing a participant) and 3.2 (one trusted participant).

**Main-text sentence.** On gpt-oss-20b, telling just one of three firms "do not coordinate prices" lowered the whole market's price index by about a third (-0.22, 95% CI -0.36 to -0.10, 15 pairs), with all three firms coming down together; on Qwen3-32B prices did not move (+0.02, CI -0.07 to +0.10).

**Appendix sentence.** Against three-firm chat, gpt-oss's n3-ethics arm lowers the spread by 0.45 [0.19, 0.71], the price index by 0.22 [0.10, 0.36] and the profit gain index by 0.26 [0.11, 0.42]. It also raises the competitive share by 0.17 and cuts matching by 0.19 (exact sign-flip p 0.0006 to 0.008; Holm within the dossier's 8 contrasts 0.004 to 0.056). The result holds on the 9 games with no truncated call (-0.22) and with the 3 failed games filled in least favourably (-0.22). The bound firm itself prices no lower than the others (-0.02 [-0.07, +0.03]). On Qwen thinking on, the same rule cuts matching (-0.18) without moving price (+0.02 [-0.07, +0.10]).
