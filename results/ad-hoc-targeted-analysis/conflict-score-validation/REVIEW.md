# Post-hoc review of the conflict-score validation

Commits 235857c and 171bef2 reached main without a pull request or review. This note records the review done afterwards. **Outcome: no blocking or material issues; no change to the analysis files.**

## What was checked

- **Numbers vs tables.** Every figure in `ANALYSIS.md` (distribution, paired differences, Spearman, round-level gap, keyword rates, rule-mention means) matches the CSVs.
- **Reproduction.** `analyze.py` was rerun on the original collect.py tables (neutral d-conflict, and the 36 completed d-conflict-ethics games). All 7 CSVs came out identical (apart from Windows line endings).
- **Pairing.** Games are joined on (wording, seed) within each thinking mode. There are no duplicate keys, each seed has one wording, and 20 off pairs and 16 on pairs are what the join yields. The four thinking-on ethics games that were not DONE are dropped, as the analysis says.
- **CI and permutation logic.** Bootstrap over pairs for the CI; paired sign-flip for the p-value; permutation Spearman. All are correct for this design. The seed is fixed, so results are repeatable.
- **Claims vs evidence.** The verdict ("low-sensitivity instrument", "supported but not proved") is consistent with the data and carries its caveats.
- **Hygiene.** No local paths, emails or forbidden names in the folder.
- **HTML twin.** `ANALYSIS.html` contains all of the text and numbers of `ANALYSIS.md`.

## Minor notes (not fixed, no effect on conclusions)

- For the thinking-off score difference, the bootstrap CI (0.002 to 0.037) just excludes zero while the sign-flip p is 0.13. The scores are nearly all exactly 1, so the bootstrap is unreliable there. The text rightly calls it essentially no response; read the p-value, not the CI.
- A dozen hypothesis tests are reported with no multiplicity correction. The two Spearman p-values near 0.03 to 0.04 should be treated as suggestive.
- The "all thinking" Spearman row pools thinking modes, which differ in both score and price.
- The rule-mention comparison (1.33 vs 1.08) is per passage, with no allowance for passages clustering within games, and is descriptive only.
- Dropping the incomplete thinking-on games could bias that arm if incompleteness relates to behaviour.
