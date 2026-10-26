# Track M: the high-collusion cell (pre-declared)

**Chosen:** 2026-10-24 at about 20:50 EDT, from the slice-1 pilot. **Recorded here:** 2026-10-25 at about 00:45 EDT, after the main queue had started but before any main-run result was analysed (no main-run table or transcript had been read).

## The cell

**Private chat at penalty point 1** (two firms, Qwen3-32B-FP8). The design file and every run read it from `cell.json` (written by `pick_cell.py`). These arms run only at this cell:

- the introspection variants R2f, R3f, R2s, R3s and R4;
- the D set: the monitoring threat (A and B), and the conflict, temptation (A and B) and placebo scores.

Their control is the headline private-chat games at the same cell, on the same 20 (wording, seed) pairs (see `../trackm-seeds-2026-10-24/SEED_DECLARATION.md`), in the thinking modes each arm runs: both modes for most arms, thinking-on only for the two monitoring-threat arms.

## Why this cell

**What the pilot measured.** The pilot played one game per A1 cell (wording 0, seed 1; seed 1 is not in the declared set, so no main-run game was used to choose). The selection tool (`pick_cell.py`) ranks games by their collusion level: the mean over rounds of the market price's share of the way from the competitive level to the collusive reference level, clamped to 0–1. This is a price measure, not the profit gain index used below. A game that holds 2.09 in every round scores 0.545, so the tie at that value means those games held 2.09 throughout. Five games, in three cells, tied at the top value of 0.545, and a sixth (p5, thinking on) was just below it:

| Cell | Thinking off | Thinking on |
|---|---|---|
| p1, private chat | 0.545 | 0.545 |
| p3, private chat | 0.545 | 0.545 |
| p4, private chat | 0.27 | 0.545 |
| p5, private chat | 0.25 | 0.5433 |

**How the tie was broken.** The tool breaks ties by the smaller trial ID, which picked p1 ("headline-chat__p1" sorts before "headline-chat__p3"). That mechanical rule happens to agree with the design's prior, and the prior is the reason the choice was kept: Penalty point 1 is the mildest penalty: the theory's sustainable collusive level is highest there (0.703 of the way from the competitive level, 1.00, to the monopoly level). Private chat is the strongest communication condition. One pilot game at p1 (thinking on) contained explicit price-fixing in the chat ("Let's agree to quote 2.09 each round"); the same proposal also appears in a p3 game, so it does not separate p1 from p3.

**The evidence is thin.** It is one game per cell and mode, the measure is coarse, and the top cells were tied. The choice therefore rests mainly on the design's prior.

## Verification (declared now, run after the main queue)

After the A1 headline games finish, a check ranks the 12 A1 cells (3 communication conditions × 4 penalty points) in each thinking mode by the **profit gain index**. The index measures how far profit rises above the competitive level toward the monopoly level.

**Unit and resampling.** Each game gives one value: its mean index over the rounds it played. A cell's value is the mean over its 20 games. Confidence intervals come from a bootstrap that resamples the 20 (wording, seed) pairs (10,000 resamples). Differences between two cells are paired on (wording, seed).

**Views.** The verdict uses the **all-rounds view** (every round of every game), because it uses all 20 games. Two secondary views are reported alongside without a verdict: the early window (rounds 1 to min(8, L)) and the games that reach round 20.

**What the check reports, per mode:**

- the chosen cell's rank;
- its mean and 95% CI;
- the comparison cell's mean and CI;
- the paired difference, chosen minus comparison, with its 95% CI.

The comparison cell is the top-ranked cell, or the second-ranked cell when the chosen cell is first.

**Verdict per mode, checked in this order:**

1. **PASS:** the chosen cell ranks 1st by its mean.
2. **CLOSE:** it is not 1st, but the 95% CI of the paired difference includes 0, or the difference is smaller than 0.05 on the index.
3. **FAIL:** otherwise.

The check is reported as is. It is **never** used to re-pick the cell or to rerun arms. If it fails, the paper reports this as a limitation of the cell-dependent arms.

Created by Claude at the prompting of the repository owner.
