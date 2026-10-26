# External, outcome-blind ratings of every prompt: conflict and temptation

In the study, two or three language-model "market makers" repeatedly quote a **half-spread** (a price margin from 1.00 to 5.00 in steps of 0.01) against each other. 1.00 is the competitive level where a firm earns nothing extra; higher prices earn more for everyone, but a regulator investigates more often as the best quote rises, and a finding of coordination costs every firm a fine. Some arms let the firms chat, and some add rules or notices to the firms' instructions. This report asks a measurement question: **how much conflict (instructions that disagree with each other) and how much temptation (pull toward coordinating on high prices) does each complete prompt contain, as judged by independent Claude raters who see only the prompt text and never an arm name or a result?** The ratings were made before anyone compared them with behaviour. They are joined into the analysis table as `claude_conflict` and `claude_temptation` and set beside the models' own self-reported scores and the measured prices.

**Data.** 421 distinct prompt-text combinations (arm, penalty point, communication, number of firms, condition texts, wording 0 to 4, options, payoff-example style) across the anchored and neutral runs, the condition-text rerun, the D-set, and the new-arm runs (watchdog, gpt-oss, moral priming, controls). 444 distinct texts were rated: a firm that is given a different rule from its rival (arms m-asym and n3-ethics) sees a different text, so those cells have one text per distinct seat. Thinking on or off does not change the text, so one rating covers both modes. Not rated: the copy-bot arm and the payoff-formula arms (no grid exists for them yet).

## How to read the metrics

| Term | Meaning |
|---|---|
| Conflict (1 to 5) | How far the prompt's own instructions are mutually incompatible, so following one breaks another. 1 = fully consistent, 5 = directly contradictory. |
| Temptation (1 to 5) | How far the prompt makes coordinating on supra-competitive prices attractive, salient or easy (incentives, numbers, channel, penalty, partner description). 1 = no pull, 5 = very strong pull. |
| Rater | One fresh, independent Claude sub-agent given only the rubric and prompt files. Each prompt was rated by three raters; reported values are the mean of the three. |
| Cell rating | For cells where firms see different texts, the mean over the seats' texts of the prompt-level mean; the `_max` columns give the highest seat. |
| Weighted kappa | Agreement between two raters on the 1 to 5 scale, penalising a disagreement by the square of its size; 1 = perfect, 0 = chance. |
| ICC(2,1) / ICC(2,3) | Intraclass correlation: the share of rating variance due to real differences between prompts; (2,1) for a single rater, (2,3) for the mean of the three. |
| Anchored / neutral | Whether the prompt's worked payoff examples print the theory price 2.09 (anchored) or evenly spaced example prices (neutral). |
| Penalty point | How heavy the regulator's fine is, 1 (lightest, collusion clearly pays) to 5 (heaviest). |

The rubric is in `RUBRIC.md` (anchors for 1 to 5 on each scale). The raters saw nothing else.

## Procedure

1. Enumerate the unique text-changing combinations from the grids; the seed and the thinking mode do not change the text.
2. Render the real first-round prompts with each run's own engine jar against a local mock model (no network, no GPU): the price-quote system prompt and first user turn, for chat arms the talk-phase system prompt and first talk turn, and for fed-question arms the first question call. The user turn contains the mock's stand-in chat lines, which the rubric tells raters to ignore.
3. Save each distinct text as `P001`... in a random order, with no arm names or results; keep the key private until rating is finished.
4. Three fresh raters per prompt, in six batches (five of 82 to 83 prompts, one of 30); each batch-rater was a separate agent and wrote `id, conflict, temptation, justification`.
5. Reliability, then the per-prompt mean and median, then the join through the key to every grid combination (`prompt_ratings.csv`).

## Results

**Distribution of the 444 prompt means (rounded to the nearest integer).**

| Score | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Conflict | 125 | 221 | 50 | 48 | 0 |
| Temptation | 39 | 111 | 142 | 139 | 13 |

The mean is 2.00 for conflict (SD 0.88) and 2.96 for temptation (SD 1.00). Most prompts have little internal conflict; the conflict-4 prompts are those that carry an explicit "do not coordinate" rule, a competition-only instruction, or a monitored-reasoning shutdown notice next to the profit objective. Across prompts the two scales are weakly negatively related (Spearman -0.25): prompts with a rule against coordinating also have less pull toward it.

**Reliability (all 444 prompts, three raters).**

| Scale | Weighted kappa, pairs 1-2 / 1-3 / 2-3 | Mean kappa | ICC(2,1) | ICC(2,3) | All three equal | Within 1 point |
|---|---|---|---|---|---|---|
| Conflict | 0.78 / 0.89 / 0.80 | 0.82 | 0.83 | 0.93 | 57% | 99% |
| Temptation | 0.87 / 0.87 / 0.86 | 0.87 | 0.87 | 0.95 | 58% | 99% |

Agreement is high. Because each batch used three different agents, "rater 1" is a slot, not one person, so the slots are exchangeable; the one-way ICC(1,1) and ICC(1,3) equal the two-way values to three decimals (0.825 / 0.934 conflict, 0.867 / 0.951 temptation). Rater-slot means are 2.02, 2.00 and 1.99 (conflict) and 2.97, 3.03 and 2.88 (temptation), so no slot has a large offset.

**Mean rating by input (over the 421 combinations).**

| Input | Level | Conflict | Temptation |
|---|---|---|---|
| Communication | tacit (no chat) | 1.43 | 1.70 |
| | private chat | 2.07 | 3.20 |
| | monitored chat (regulator reads) | 1.88 | 2.15 |
| | public chat | 1.80 | 2.37 |
| | chat "not monitored" | 1.27 | 4.17 |
| Penalty point | 1 | 2.05 | 3.39 |
| | 3 | 2.01 | 2.91 |
| | 4 | 1.56 | 1.93 |
| | 5 | 1.57 | 1.42 |
| Payoff examples | anchored | 1.88 | 3.03 |
| | neutral | 2.04 | 2.90 |

Temptation falls steeply with the penalty, is lowest without chat and highest when chat is stated to be unmonitored, as the rubric intends. The five wordings of the same condition differ little (typical SD within a cell about 0.3 points), so the ratings follow content, not paraphrase. `ratings_by_arm.csv` gives means per arm.

## Caveats

- These are one rater panel's reading of the text, from one model family, not ground truth, and may share that family's blind spots.
- The rated text is the first round's prompt. Later rounds add history, which is not rated.
- A rating is constant within a prompt text, so any association with behaviour is at cell level and is confounded with arm, communication and penalty (the prompt content is what defines them).
- Process deviations: a rater could not be technically prevented from opening other files (each was instructed not to; none reported doing so). One rater of the last batch reported printing files through a script that compressed repeated boilerplate before reading them; its ratings agree with the others.
- The seat-specific texts of m-asym and n3-ethics were rated afterwards, as batch 6, by three further fresh raters.
- Fifteen prompts (P082, P108, P166, P173, P379, P425–P430, P439, P442–P444) come from early runs that still used placeholder pressure or ethics texts, marked "PLACEHOLDER (C11.3, ...)" in the prompt. Those texts were never reviewed, and later runs replaced them with the final texts. The placeholder label was shortened in these files after rating; the rated wording is otherwise unchanged.

## Files

| File | Content |
|---|---|
| `RUBRIC.md` | the rubric exactly as given to raters |
| `prompts/` | the 444 anonymised prompt texts |
| `ratings/ratings_rater1.csv` to `ratings_rater3.csv` | each rater slot's id, conflict, temptation, justification |
| `prompt_level_ratings.csv` | per prompt: mean, median, SD and the three ratings |
| `prompt_ratings.csv` | per text-changing combination; the join file for `run_csv.py --prompt-ratings` |
| `ratings_by_arm.csv`, `reliability.json` | summaries |
| `scripts/` | render, anonymise and reliability scripts |
