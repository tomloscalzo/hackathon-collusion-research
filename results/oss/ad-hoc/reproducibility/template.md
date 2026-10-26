# Reproducibility of the gpt-oss-20b headline cells (headline-cell replicates vs their headline games)

*Model: gpt-oss-20b, reasoning effort medium (no thinking-off mode exists, so there is no t0/t1 contrast). Data: the frozen t1 tier. Declared analysis, sub-question 2.3 (what counts as convincing evidence) and the evidence standards.*

## Verdict

Replaying the same prompt with an independent sample does not reproduce a game: of 99 headline/replicate pairs only one has an identical quote sequence (a 2-round game that ended at once), and the typical gap between two games on the same (wording, seed) is large (mean absolute difference 0.22 on the price index, 0.43 on the average absolute spread). The replicates also ran systematically higher than the headline games: price index +0.10 on average (95% CI +0.05 to +0.16 over all 99 pairs; +0.03 to +0.16 after averaging the copies per headline game), the same sign in all five replicate arms and in all three headline cells, though only two of the three headline cells have a CI that excludes zero. Competitive share and matching share move less and their CIs include zero. With 20 pairs a cell, the smallest cell difference we can reliably see (80% power) is about 0.12 on the price index for chat at p1 and about 0.20 for tacit at p1 and chat at p5; the headline effects of chat versus tacit (-0.19) and p5 versus p1 (-0.15) sit right at that limit, and the p3 versus p1 difference (+0.04) is inside the noise. This topic has no Qwen counterpart.

## Orientation for a new reader

| Term | Meaning |
|---|---|
| Game | Two LLM market makers each quote a half-spread (the price they charge, from 1.00 to 5.00 in 0.01 ticks) for 7 to 20 rounds; 70% of customers go to the lower quote. |
| Half-spread, tick | The quote itself; a tick is the smallest step, 0.01. |
| 1.00 floor | The competitive quote: zero margin. 3.00 is the monopoly (fully collusive) quote. The 2.09 level is the theory price that the older anchored run printed in its payoff table; the neutral run, analysed here, prints evenly spaced example prices instead. |
| Rival | The other market maker in the game. |
| Headline cell | A fixed condition: headline-chat (the firms may chat) or headline-tacit (no chat), at penalty point p1, p3 or p5 (p1 = light fine, p5 = heavy). |
| Control / comparison here | Each replicate game is compared with the headline game of the same wording and seed, so the "control" is the headline game. |
| Replicate | A second (or third) independent sampling of the same prompt; the seed fixes the game plan and wording but the model's text sampling is not replayed. |

**The five standard metrics**, each analysed on its own: the average absolute spread (mean quoted half-spread over the game, 1.00 to 5.00, higher is more collusive); the price index (the average quote placed between competitive 0 and monopoly 1, so 0.46 is about a third of the way up from the floor to the monopoly price); the profit gain index (profit between the competitive and the monopoly profit, 0 to 1); the competitive share (share of firm-rounds in which the firm undercuts the lowest rival quote of the previous round by at least one tick, or both firms are at 1.00; higher is more competitive); the matching share (share of firm-rounds in which the firm matches the lowest rival quote of the previous round, within half a tick, above 1.00). Both are read from the run.csv columns competitive_share and matching_share.

## The question, arms, pairing

Does the same prompt give the same result when run again? Five arms were planned as formula / no-numbers conditions (fx-chat-p1, fx-tacit-p1, fx-chat-p5, nx-chat-p1, nx-tacit-p1), but because of a build bug (a global grid override replaced their payoff block) they played the neutral headline prompt. The prompt fingerprint and code commit of every replicate game match the headline games, so they are valid same-prompt replicates, labelled "hrep-*" here; the correct formula / no-numbers games live in a separate run. Replicate arm to headline cell: hrep-fx-chat-p1 and hrep-nx-chat-p1 to headline-chat p1; hrep-fx-tacit-p1 and hrep-nx-tacit-p1 to headline-tacit p1; hrep-fx-chat-p5 to headline-chat p5. Pairing is on (wording, seed). Because two arms copy each of the first two headline cells, the 99 pairs are not independent (59 distinct headline games); a de-duplicated check is given below. n is 20 pairs per arm, 19 for hrep-fx-chat-p5 (one game failed with EmptyContent and was not retried, so the arm has 19 completed games). The replicates and the headline games ran in the same session (overlapping in time), so time of day is not a confound. No Qwen3-32B replicate exists, so there are no Qwen rows.

## Standard metrics

Contrast is replicate minus headline, per cell, with a 95% percentile bootstrap CI over pairs. Positive means the replicate was higher. For the competitive share a positive difference means more competitive.

{{STD}}

**Replicates?** (here this means: does the replicate game reproduce the headline game's number). Sign and magnitude, price index: all five arms same sign (replicate higher), magnitudes +0.05 to +0.15; the individual CIs exclude zero for hrep-fx-chat-p1 and hrep-fx-tacit-p1 only. The competitive share has a mixed sign and no CI excludes zero (it shifts by -0.07 to 0.00 in the replicate arms). The matching share is small and positive in all arms, excluding zero only for hrep-nx-tacit-p1. Overall: the level of the headline cells is reproduced to within roughly +/-0.15 on the price index, but the replicate mean is reliably higher in the pooled data.

| Term | Definition |
|---|---|
| Diff | Mean over pairs of (replicate value minus headline value) for that metric. |
| 95% CI | 2.5th to 97.5th percentile of 2000 bootstrap resamples of the pair differences (fixed seed 20261026). |
| CI vs 0 | Whether that interval contains zero; if it excludes zero the replicate mean differs from the headline mean beyond sampling noise. |

## Share of identical games and mean absolute differences

{{IDENT}}

Only one of 99 pairs is identical (hrep-fx-chat-p1, wording 0 seed 226: a 2-round game; the headline copy of the same seed ended after 2 rounds too). No pair has the same replay digest. The 12 pairs whose number of rounds differs (87 of 99 are equal) mostly come from games that ended early on the evidence rule in one copy and not the other, so a part of the replicate noise is whether and when a game stops. (Note: the "identical first prompts" check in pairs.csv is not used: in the chat arms the stored request hash of the first call differs between arms for a reason not investigated here, and tacit games have no chat call; the prompt fingerprints in run.csv are identical across all these arms.)

{{ABSD}}

Reading the table: the mean absolute difference (average size of the gap between replicate and headline for the same pair, ignoring sign) is 0.43 on the average spread, 0.22 on the price index, 0.24 on the profit gain index, 0.20 on the competitive share and 0.19 on the matching share when all pairs are pooled. It is smallest in headline-chat at p1 (price index 0.14) and about double that in tacit and p5 cells (0.25 to 0.29). The correlation between a headline game and its replicate is low (0.21 for the price index pooled; 0.55 and 0.29 for the two chat-p1 arms; around zero for tacit and p5), meaning that pairing on (wording, seed) removes very little noise: the seed fixes the setup but not the model's sampled text.

| Term | Definition |
|---|---|
| Mean abs diff | Mean over pairs of the absolute value of (replicate minus headline). |
| SD of diff | Standard deviation across pairs of (replicate minus headline); the noise scale of one paired comparison. |
| Share exactly equal | Share of pairs with the identical metric value (mostly games at the same boundary value, such as a share of 0 or 1). |
| Corr | Pearson correlation across pairs between the headline game's value and its replicate's value. |

## Systematic drift (are replicates higher than headline games?)

Pooled over all 99 pairs the replicate minus headline difference is +0.209 on the average spread, +0.104 on the price index (CI +0.052 to +0.156) and +0.110 on the profit gain index. The pooled CI treats 99 pairs as independent although the two chat-p1 copies and the two tacit-p1 copies share a headline game. The de-duplicated table averages the copies per headline game (59 headline games):

{{DRIFT}}

The replicate is above the headline game in about 60% of headline games. Drift does not depend on the wave or the seed: the correlation of the pair difference with wave and with seed is within -0.31 to +0.36 in every arm and metric, and about 0 pooled (see replicate_summary.csv). Two replicates of the same cell agree much better with each other than either does with the headline (for chat p1 the fx-minus-nx price index difference is +0.05, CI -0.03 to +0.15; for tacit p1 +0.02, CI -0.07 to +0.11), which fits with the headline cells being a little low by chance (3 headline cells, all low, probability 1/8 if direction were random) rather than with the replicates being biased; we cannot tell these apart with this design, and calling it "drift" would overreach. The prompt fingerprint, the code commit and the run window were the same, so no known cause exists.

{{RR}}

| Term | Definition |
|---|---|
| fx minus nx | The hrep-fx arm minus the hrep-nx arm for the same headline cell, paired on (wording, seed): replicate against replicate. |

## What difference is distinguishable from replicate noise?

The spread of a paired difference between two independent games of the same prompt is the noise floor for any cell-to-cell comparison with 20 pairs. The 95% CI half-width is 1.96 times the SD divided by the square root of 20; the minimum detectable effect at 80% power and a 5% two-sided level is 2.8 times that SD over the square root of 20.

{{MDE}}

On the price index the minimum detectable effect is about 0.12 for headline-chat p1 and about 0.19 to 0.20 for tacit p1 and chat p5; for the competitive share and matching share it is about 0.16 to 0.19. For comparison, the between-condition effects in the headline cells (same pairing, headline games only):

{{BC}}

Penalty p5 versus p1 in chat (-0.15 on the price index) and tacit versus chat at p1 (-0.19) and at p5 (-0.23) are of the same order as the minimum detectable effect (0.12 to 0.20), so they are visible but not far above the noise; the tacit cells have the largest noise. The p3 versus p1 difference (+0.04) and the matching share contrast p5 versus p1 are smaller than the noise floor and should be reported as "not distinguishable" and not as bounded nulls of precision. The replicate offset (+0.10) is of the same size as these effects, so one 20-pair cell is not a reliable reading of a cell's true level. Sensitivity: when each headline cell is pooled with its replicate copies (the right-hand mean of up to 3 games per wording and seed) the signs are unchanged and the effects are mostly of similar or larger size:

{{PC}}

| Term | Definition |
|---|---|
| Minimum detectable effect | The smallest true difference a paired 20-pair comparison detects with 80% power at a two-sided 5% level, here 2.8 x SD / sqrt(20). |
| Pooled cell | For each (wording, seed), the average over the headline game and its replicate copies. |

## Empty-talk sensitivity

empty_talk_done_count is the number of talk turns whose empty reply was read as "done". It occurs only in chat arms. Mean per arm: headline-chat p1 0.80, p3 0.40, p5 0.40; hrep-fx-chat-p1 0.50, hrep-nx-chat-p1 0.80, hrep-fx-chat-p5 0.63; every tacit arm 0.00 (by-arm numbers with the number of affected games are in empty_talk_by_arm.csv). 29 of the 99 pairs have a count above 0 in at least one game. Dropping those pairs leaves 70 pairs and the contrast changes little: the price index difference is +0.114 (CI +0.047 to +0.181) against +0.104; the matching share difference rises to +0.089 (CI +0.026 to +0.155) against +0.045.

{{EMP}}

## Limits

- Three headline cells only (chat p1, tacit p1, chat p5), 19 to 20 games each; the 99 pairs are not independent. The strongest honest statement is about those three cells and the 59 distinct headline games.
- The replicates share the headline's seed and wording, but the model's text sampling is not reproducible, so "replicate noise" here is the noise of an independent sample for a given setup.
- We cannot separate chance from a hidden systematic difference between the replicate and headline runs; no cause was found.
- Minimum detectable effects use the observed SD of paired differences in 19 to 40 pairs, which is itself uncertain.
- No Qwen3-32B counterpart exists; the comparison to Qwen is not available.

## Which sub-question this addresses

Sub-question 2.3 (what should count as convincing evidence) and the evidence standards: a single 20-game cell has a price index uncertainty of about +/-0.1, replication within a prompt does not reproduce individual games, and effects below about 0.12 to 0.2 on the price index cannot be told apart from replicate noise at this n.

## Files

standard_metrics.csv, replicate_summary.csv, identity_summary.csv, pairs.csv, pairs_per_headline_game.csv, drift_dedup.csv, replicate_vs_replicate.csv, between_condition_effects.csv, pooled_cell_sensitivity.csv, empty_talk_by_arm.csv; scripts repro.py (computation) and gen_report.py with template.md (this report).
