# Track M seed declaration (game lengths chosen before any game with these seeds)

**Status:** written and committed **before** any agent (LLM) game with any of the seeds below has run (only the scripted verification games described below were run). Revised 2026-10-24 20:55 EDT (2026-10-25 00:55 UTC), on top of `main` at commit `a73d781`. The commit that carries this revision is the one that adds it (its own hash cannot be written inside it; see the pull request merge for the hash).

**Revision note.** An earlier version of this file (merged 2026-10-24 20:37 EDT, `main` at `4842953`) declared four seeds, 91, 42, 226 and 118, one per length. No agent game had run. It is replaced because the regulator's investigation draws are also fixed by the seed, so four seeds would stamp the same few detection times on every collusive game. Those four seeds remain, as the wording-0 seeds below.

## What was decided

The owner chose four game lengths, **7, 15, 19 and 20 rounds**, to give mostly long games (three of the four within five rounds of the stated 20-round mean; the planned lengths average 15.25; continuation 0.95, hidden cap 40 rounds).

To vary the investigation timing across games while keeping those lengths and the pairing, there are **20 seeds, 5 per length, and each of the 5 prompt wordings gets its own seed of each length** (wording w uses the w-th seed of each length). Every arm uses the same 20 (wording, seed) pairs, so comparisons stay paired.

| Wording | 7 rounds | 15 rounds | 19 rounds | 20 rounds |
|---|---|---|---|---|
| 0 | 91 | 42 | 226 | 118 |
| 1 | 94 | 47 | 227 | 171 |
| 2 | 133 | 55 | 259 | 174 |
| 3 | 136 | 115 | 261 | 193 |
| 4 | 151 | 126 | 273 | 218 |

## How the seeds were selected

- Only by their pre-computed horizon length, never by any outcome and without looking at the investigation draws. A game's maximum length is fixed by its seed: round t draws `uHor` from `SeedPolicy(seed).stream("horizon")`, and the game ends at the first t with `uHor < 0.05`, or at the 40-round cap.
- Method: scan seeds 1 to 10,000, exclude seeds 1 to 12 (already used in other runs), and for each length take the five smallest seeds whose planned length is exactly that length, in increasing order; the w-th goes to wording w.
- Each of the 20 seeds was verified through the engine jar with one scripted-only game per scenario (a scripted always-compete seat, scenarios `slice-p1` and `slice-p3`): every one ended by `HORIZON` at exactly the planned round.

## How they are used

- Agents are told only the true 95% continuation odds ("about 20 rounds on average") and never their game's length.
- The same 20 (wording, seed) pairs are used in every Track M arm (paired); a cell is 20 games. The introspection (R1 to R4, and the saved-only and 32k variants) and D-set arms use the same 20 pairs too; their control (R0) is the headline game of the chosen cell's communication, with the same seat texts (no duplicate control games), so they pair with the headline.
- Regulator investigations can still end games earlier, so actual lengths are reported beside planned ones.
- The hidden 40-round cap is unchanged.
