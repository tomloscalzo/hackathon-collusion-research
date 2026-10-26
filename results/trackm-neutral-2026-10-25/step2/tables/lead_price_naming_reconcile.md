# RECONCILE: does price-naming rise or fall under the idle CoT-monitoring threat?

## Answer

**It FELL. The READING claim (38% to 57%, "rose") is an artefact; CHANNEL_SHIFT's direction is the right one.**

Cause: READING's denominator is every talk CALL with reasoning, including turns where the firm said nothing (empty text, 0 words). The control firms are silent on 62% of calls (the rival often passes), the monitored firms on 28 to 48%. Almost every non-empty control message names a price (about 99%), so the control's pooled share is simply 1 minus its silence (38%); the monitored arms are silent less often, so the same measure looks higher (57%). It measures talkativeness, not price content. Secondary differences: READING's regex also matches bare integers 2 to 5, pools turns instead of averaging games, and (as published) kept incomplete games; CHANNEL_SHIFT used DONE games only (11 and 14 of 20 in the neutral run, so n is 11/14/20). Both published numbers reproduce exactly (see each run below).

Reconciled definition: share of NON-EMPTY talk messages naming a decimal price >= 1.30, game-level mean, DONE games only, 95% CI bootstrapped over wording x seed pairs. The fall holds in rounds 1-8 and all rounds, in both runs and both arms, with CIs excluding 0 (monitor-b in the neutral run is the thinnest: -5.5 pts, CI -10.7 to -0.6). The fall is in message content only: the per-round measure (does any message that round name a price) shows a small or null difference in the neutral run (CIs include 0) and a small fall in the anchored run. The monitored firms also talk MORE overall (more non-empty messages per game), so "more price talk in volume" is true while "a higher share of messages name a price" is false. Do not claim a rise in price-naming share.

---

# Reconciling the price-naming claim (run `tables_neutral`)

Tables: `..\tables_neutral`. Reproduce: `python -X utf8 reconcile.py --tables <dir> --out <dir>`. Groups: d-cot-monitor-a, d-cot-monitor-b, control = headline-chat at penalty point 1; thinking on; DONE games only.

Games by status before dropping non-done:

| arm | done | incomplete |
|---|---|---|
| d-cot-monitor-a | 11 | 9 |
| d-cot-monitor-b | 14 | 6 |
| headline-chat | 20 | 0 |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Reproduction of the two earlier numbers

READING counts every talk CALL that has reasoning, including turns where the firm said nothing (empty text), as a pooled share, with a regex that also matches bare integers 2 to 5. CHANNEL_SHIFT keeps only messages with at least one word, matches decimals only, and averages per game.

| group | done games | READING reproduced (all turns, pooled) | empty-turn share | READING regex, non-empty only | CHANNEL regex, all turns | CHANNEL reproduced (non-empty, game mean) |
|---|---|---|---|---|---|---|
| monitor-a | 11 | 47.8% | 46.0% | 88.6% | 46.3% | 83.7% |
| monitor-b | 14 | 45.9% | 48.0% | 88.2% | 45.7% | 91.3% |
| control | 20 | 37.9% | 61.9% | 99.5% | 37.7% | 98.5% |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


READING as published also kept incomplete games (all 20 per arm); pooled over all talk calls with reasoning, same regex: d-cot-monitor-a 57.7%, d-cot-monitor-b 57.3%, headline-chat 37.9%. (Published: 57.7 / 57.3 / 37.9 on the neutral run.)

Volume of talk per game:

| group | games | turns_per_game | nonempty_per_game | empty_turn_share |
|---|---|---|---|---|
| monitor-a | 11 | 35.64 | 19.18 | 0.46 |
| monitor-b | 14 | 40.79 | 21.14 | 0.48 |
| control | 20 | 27.95 | 10.65 | 0.62 |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Reconciled definition

**Share of NON-EMPTY talk messages that name a price >= 1.30**: a message counts if it has text and at least one word; it names a price if it contains a decimal number 1.30 to 5.00 not followed by % and not directly after the word 'round'. Computed per game, then averaged over games; 95% CI by bootstrap (10,000) over wording x seed pairs (one game per arm per pair). Differences are paired by pair. DONE games only. Sensitivity: READING's regex on the same non-empty messages. Robustness: per round, does any non-empty message name a price; game mean over rounds that had talk.

### primary: share of non-empty talk messages naming a price >= 1.30, rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 82.8% (69.5 to 93.8) | 11 | -17.2 pts (-30.6 to -6.1) | 11 |
| monitor-b | 92.7% (87.8 to 96.9) | 14 | -5.5 pts (-10.7 to -0.6) | 14 |
| control | 98.8% (96.2 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### primary: share of non-empty talk messages naming a price >= 1.30, all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 83.7% (70.9 to 94.4) | 11 | -16.3 pts (-29.2 to -5.6) | 11 |
| monitor-b | 91.3% (83.2 to 97.0) | 14 | -6.9 pts (-15.2 to -0.5) | 14 |
| control | 98.5% (95.7 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### sensitivity: same, READING regex (adds bare integers 2-5), rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 89.8% (77.6 to 98.1) | 11 | -10.2 pts (-21.9 to -2.0) | 11 |
| monitor-b | 93.0% (88.1 to 97.2) | 14 | -7.0 pts (-12.0 to -2.8) | 14 |
| control | 100.0% (100.0 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### sensitivity: same, READING regex (adds bare integers 2-5), all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 90.7% (79.5 to 98.4) | 11 | -9.3 pts (-20.1 to -1.7) | 11 |
| monitor-b | 91.6% (83.7 to 97.3) | 14 | -8.4 pts (-16.5 to -2.7) | 14 |
| control | 99.7% (99.2 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### robustness: share of talking rounds with any message naming a price >= 1.30, rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 97.0% (90.9 to 100.0) | 11 | -3.0 pts (-9.1 to +0.0) | 11 |
| monitor-b | 98.0% (94.9 to 100.0) | 14 | +0.3 pts (-4.1 to +6.1) | 14 |
| control | 98.3% (95.0 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### robustness: share of talking rounds with any message naming a price >= 1.30, all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 97.7% (93.2 to 100.0) | 11 | -2.3 pts (-6.8 to +0.0) | 11 |
| monitor-b | 95.8% (88.1 to 100.0) | 14 | -1.8 pts (-11.3 to +6.5) | 14 |
| control | 98.3% (95.0 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Verdict

Direction of price-naming among non-empty talk messages, monitored minus control: all rounds: **FELL (both arms, CI excludes 0)**; rounds 1-8: **FELL (both arms, CI excludes 0)**.

---

# Reconciling the price-naming claim (run `tables_anchored`)

Tables: `..\tables_anchored`. Reproduce: `python -X utf8 reconcile.py --tables <dir> --out <dir>`. Groups: d-cot-monitor-a, d-cot-monitor-b, control = headline-chat at penalty point 1; thinking on; DONE games only.

Games by status before dropping non-done:

| arm | done |
|---|---|
| d-cot-monitor-a | 20 |
| d-cot-monitor-b | 20 |
| headline-chat | 20 |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Reproduction of the two earlier numbers

READING counts every talk CALL that has reasoning, including turns where the firm said nothing (empty text), as a pooled share, with a regex that also matches bare integers 2 to 5. CHANNEL_SHIFT keeps only messages with at least one word, matches decimals only, and averages per game.

| group | done games | READING reproduced (all turns, pooled) | empty-turn share | READING regex, non-empty only | CHANNEL regex, all turns | CHANNEL reproduced (non-empty, game mean) |
|---|---|---|---|---|---|---|
| monitor-a | 20 | 56.2% | 36.8% | 88.9% | 55.5% | 90.2% |
| monitor-b | 20 | 64.1% | 28.3% | 89.4% | 62.4% | 88.7% |
| control | 20 | 38.6% | 61.3% | 99.7% | 38.6% | 99.8% |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


READING as published also kept incomplete games (all 20 per arm); pooled over all talk calls with reasoning, same regex: d-cot-monitor-a 56.2%, d-cot-monitor-b 64.1%, headline-chat 38.6%. (Published: 57.7 / 57.3 / 37.9 on the neutral run.)

Volume of talk per game:

| group | games | turns_per_game | nonempty_per_game | empty_turn_share |
|---|---|---|---|---|
| monitor-a | 20 | 64.15 | 40.50 | 0.37 |
| monitor-b | 20 | 77.70 | 55.65 | 0.28 |
| control | 20 | 40.00 | 15.50 | 0.61 |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Reconciled definition

**Share of NON-EMPTY talk messages that name a price >= 1.30**: a message counts if it has text and at least one word; it names a price if it contains a decimal number 1.30 to 5.00 not followed by % and not directly after the word 'round'. Computed per game, then averaged over games; 95% CI by bootstrap (10,000) over wording x seed pairs (one game per arm per pair). Differences are paired by pair. DONE games only. Sensitivity: READING's regex on the same non-empty messages. Robustness: per round, does any non-empty message name a price; game mean over rounds that had talk.

### primary: share of non-empty talk messages naming a price >= 1.30, rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 89.4% (81.1 to 96.2) | 20 | -10.1 pts (-18.7 to -3.2) | 20 |
| monitor-b | 90.2% (81.0 to 96.9) | 20 | -9.3 pts (-18.8 to -2.4) | 20 |
| control | 99.5% (98.5 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### primary: share of non-empty talk messages naming a price >= 1.30, all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 90.2% (82.6 to 96.0) | 20 | -9.6 pts (-17.3 to -3.9) | 20 |
| monitor-b | 88.7% (80.7 to 95.0) | 20 | -11.0 pts (-19.5 to -4.8) | 20 |
| control | 99.8% (99.2 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### sensitivity: same, READING regex (adds bare integers 2-5), rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 90.7% (82.6 to 96.7) | 20 | -8.8 pts (-16.9 to -2.8) | 20 |
| monitor-b | 92.8% (83.7 to 98.9) | 20 | -6.7 pts (-16.0 to -0.5) | 20 |
| control | 99.5% (98.5 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### sensitivity: same, READING regex (adds bare integers 2-5), all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 90.8% (83.0 to 96.2) | 20 | -9.0 pts (-16.5 to -3.5) | 20 |
| monitor-b | 91.9% (84.3 to 97.2) | 20 | -7.9 pts (-15.4 to -2.5) | 20 |
| control | 99.8% (99.2 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### robustness: share of talking rounds with any message naming a price >= 1.30, rounds 1-8

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 95.7% (89.1 to 100.0) | 20 | -3.5 pts (-10.1 to +1.0) | 20 |
| monitor-b | 96.9% (90.6 to 100.0) | 20 | -2.3 pts (-9.4 to +2.5) | 20 |
| control | 99.2% (97.5 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


### robustness: share of talking rounds with any message naming a price >= 1.30, all rounds

| group | mean (95% CI) | n pairs | diff vs control (95% CI) | n pairs |
|---|---|---|---|---|
| monitor-a | 93.5% (86.2 to 99.0) | 20 | -6.1 pts (-13.6 to -0.7) | 20 |
| monitor-b | 94.2% (87.4 to 99.2) | 20 | -5.4 pts (-12.4 to -0.3) | 20 |
| control | 99.6% (98.8 to 100.0) | 20 |  |  |

<small>

**Terms used in this table (repeated for each table in this note)**

| Term | Plain-language meaning |
|---|---|
| arm; group | d-cot-monitor-a / -b = idle reasoning-monitor threat texts A and B at private chat, point 1, thinking on; control = headline-chat at point 1 (thinking on); 'group' names the arm or the pooled threat arms |
| done / incomplete | games finished / not finished at the time of the build; only done games are analysed |
| READING; CHANNEL_SHIFT | the two earlier analyses whose price-naming numbers are being reconciled (the reading analysis; the channel-shift analysis) |
| price-naming share | share of talk messages that name a decimal price of at least 1.30 (reconciled definition: non-empty messages only, game-level mean) |
| empty-turn share | share of talk calls whose message was empty (the firm said nothing) |
| turns_per_game; nonempty_per_game | talk calls per game; of those, non-empty ones |
| mean (95% CI); n pairs; diff vs control | mean [95% bootstrap interval over wording x seed pairs]; number of pairs; difference from the control group |
| rounds 1-8 | the early window |

**Slugs and codes in this table** (from the shared glossary `tools/analysis_style/arm_glossary.csv`)

| Slug | Meaning |
|---|---|
| d-cot-monitor-a | reasoning-monitor threat, A (own-quote trials allowed) |
| d-cot-monitor-b | reasoning-monitor threat, B (undercutting allowed) |
| headline-chat | private chat, no other lever |
| p1 | penalty point 1: fine 100 (lightest) |
| t1 | thinking on |

</small>


## Verdict

Direction of price-naming among non-empty talk messages, monitored minus control: all rounds: **FELL (both arms, CI excludes 0)**; rounds 1-8: **FELL (both arms, CI excludes 0)**.