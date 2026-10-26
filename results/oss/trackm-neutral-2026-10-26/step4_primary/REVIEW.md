# Step 4 (gpt-oss-20b as primary model): reviewer pass

*A fresh adversarial reviewer who had not seen the drafting checked this page against the sources, following the "Reviewer pass" in `prompt-library/analysis/step4-strongest-evidence.md`. Created by Claude at the prompting of the repository owner.*

**Sources checked:** `results/claims-dossiers/MASTER_CLAIMS.md`; dossiers 01 to 11 (`ANALYSIS.md` and their CSVs); `results/oss/trackm-neutral-2026-10-26/step3/SUMMARY.md`; `results/oss/ad-hoc/detection-transfer/`; and `alignment/AREAS_TO_SPRINT_OBJECTIVES.md` for the question text.

## (a) Numbers re-checked

**The three-number box.** Every number was checked, and all match the source. The only problems were in the wording and the status lines (findings R5 and R6).

| Track | What was checked | Source |
|---|---|---|
| 1 | -0.30 [-0.43, -0.16], 19 pairs, and its five metrics; the supporting -0.22, -0.37 [-0.44, -0.28], -0.38 and -0.56 | dossier 01, Table 1a |
| 2 | AUC 0.81 [0.67, 0.93] (57 games) and 0.91 [0.87, 0.94] (524 games); text minus quotes -0.01 [-0.02, +0.01]; 19 of 20 | dossier 07 |
| 3 | +0.21 [0.11, 0.29], 20 pairs; all five pooled metrics with intervals; 0.39; 0.13 [0.06, 0.22]; Holm 0.020 / 0.016 (pooled 0.009) | dossier 02, `tables/contrasts_within_model.csv`; dossier 04 |

**About a third of the body numbers.** These match:
- the penalty rows (dossier 03, Table 1);
- the control ladder levels and contrasts, the replicate drift +0.104 and the 0.22 gap (dossier 04 CSVs);
- n3-ethics, the cheater's mechanical part and residual, the seat-level falls, the truncation counts 8/17 and 5/18, and the waves (dossier 08);
- the moral primes and their Holm values (dossier 05);
- the 5-tick start, Holm 0.0201 (MASTER gives 0.018; the dossier value stands);
- the watchdog, reasoning-monitor threat and mechanism rows (dossier 09 oversight CSVs);
- the focal-point shares (dossier 01);
- the detector flag counts, hard cases, early-to-late correlation and the label's five metrics (dossier 07);
- the tick-churn shares (dossier 11);
- the design-adjusted ratings (dossier 10);
- the noise floor 0.12 to 0.20 (Step 3);
- the gpt-oss refit, +0.003 [-0.005, +0.012] (ad-hoc detection-transfer).

**Mismatches found:** the text-model recall interval and false-positive rate (R10); the report-threat interval, which differed between sections (R11); and "1 of 99 games", which should be pairs (R12).

**Other checks:** every question is quoted verbatim, and the page contains no local paths, person names or emails.

## (b) Read as a judge

- **Impact Potential & Innovation:** strong and well aimed. The prompt-artefact (focal-point) result, "audit actions, not words" and suppression-not-hiding are the results the target audience cares about.
- **Execution Quality:** good. Pairing, frozen detectors, controls, MDEs and Holm are stated consistently. The weak points were keyword-led headlines (2.2, 3.4) and over-strong wording ("alone" in 3.1, "do not respond" in 1.2, "only one moved prices" in 3.2).
- **Presentation & Clarity:** this was the main weakness.
  - Headlines run 40 to 60 words.
  - "What we observed" runs well past the spec's 2 to 3 sentences.
  - The formula and no-numbers result was restated in full in 1.1, 1.5, 2.1 and 3.1.

## (c) Caveats and rules

- The replicate band, cross-wave, later-build and one-reasoning-mode caveats are stated at the top and in most sections.
- Missing keyword caveats in 1.3, 1.4 and 2.2 were added.
- Two headlines (2.2, 3.4) rested on keyword features and were rewritten.
- Qwen appeared outside a "Second model:" line once (3.2); this was fixed.
- One Second-model line had the wrong direction (1.5); this was fixed.
- Every table has a legend; two lacked numbered captions (fixed).

## Disposition

| Fix | Section | Finding | Applied | Note |
|---|---|---|---|---|
| R1 | 3.2 | A comparison with the second model sat outside the Second-model line | yes | Reworded with no model reference |
| R2 | 1.5 | Second-model line said Qwen's moral-prime effect was larger, but it is smaller | yes | Marked larger / smaller per lever |
| R3 | 2.2 | "Talk is uninformative" rested on a keyword say-do rate; a refit shows text alone reaches AUC 0.87 | yes | Headline and the Execution sentence revised; the refit comes from the ad-hoc detection-transfer analysis |
| R4 | 3.4 | Headline led by an unvalidated keyword agreement flag | yes | Headline now uses price, high-price rounds and silent rounds; the body adds "any agreement" -0.32 and messages per round +1.5 |
| R5 | Box, Track 3 | Called the 0.39 no-chat level "competitive"; per-point Holm given for a pooled number | yes | "Well above the floor"; pooled Holm 0.009 added |
| R6 | Box, Track 2 | Missing MASTER's "relabelled as a trajectory forecast" | yes | |
| R7 | 2.1 | Pooled intervals said to be unavailable, but they exist | yes | Intervals added for all five metrics; legend corrected |
| R8 | 1.5 | "Six restrictions" but seven table rows | yes | Clarified in the text and the caption |
| R9 | 1.5 | Called the end of the interval inside the band the "lower" end | yes | Now "CI end nearest 0 (-0.005)" |
| R10 | 1.3 | Text recall interval [0.20, 0.37] and false-positive rate 0.08 | yes | Now [0.21, 0.37] and 0.09, as in dossier 07 |
| R11 | 3.2, 3.4 | Report-threat interval differed between sections; the metric was not named | yes | MASTER's -0.07 [-0.19, +0.02] on profit gain used in both; price index added in 3.4 |
| R12 | 2.3 | "1 of 99 games" | yes | Now "pairs" |
| R13 | 1.2 | "LLM firms do not respond" (their own quotes fall by 0.17); seat unit missing | yes | "Reaction leaves the market price unchanged"; round-1 presence noted; seat falls labelled as mean quote |
| R14 | 3.2 | "Only one moved prices" contradicted the cheater result | yes | Now "only one changed how the firms priced" |
| R15 | 3.1 | "Printed prices alone" over-claimed (controls at another point; the no-numbers arm also removes market information; the formula arm is still at 0.17) | yes | Headline and body softened |
| R16 | Header | Primer link would break at the final location | yes | Path set for `results/oss/trackm-neutral-2026-10-26/step4_primary/` |
| R17 | 3.4 | "Falls by 0.13" next to a negative interval | yes | Now "changes by -0.13 [...]" (three places) |
| R18 | 1.5 | Watchdog listed as a bound, but its status is inconclusive | yes | |
| R19 | 1.3 | Keyword caveat missing | yes | Added as caveat (4) |
| R20 | 1.5 | Cross-wave caveat for moral prime A missing | yes | Same-wave control -0.37 added |
| R21 | 2.1 | Unclear headline ending | yes | Now "a choice, not an inability" |
| O1 | 1.3, 3.4 | Numbered table captions missing | yes | |
| O2 | All | Provenance notes on the question text are not uniform | no | Not requested this round; cosmetic |
| O3 | All | Mixed plus-minus notation | yes | "+-" used throughout |
| O4 | Header | "Not a bias of known sign" conflicts with the +0.10 drift | yes | Reworded |
| O5 | 1.1 | Row labels "Printed numbers, ..." describe formula rows | yes | Labels and legend changed |
| O6 | 2.3 | Second-model line said Qwen "agrees in size"; Qwen's ordinary chat already sits at its joint-profit level | yes | |
| O7 | 3.4 | One-of-two ethics interval differed from 1.2 and 3.2 | yes | Dossier 08's -0.02 [-0.12, +0.09] used |
| O8 | 2.2 | Explicit-agreement label result comes from a keyword label and an ad-hoc source | yes | Flagged in the text |
| O9 | 1.4 | Say-do rates rest on a keyword measure | yes | Flagged |
| O10 | 3.1 terms | "Theory's sustainable price index is 0.70 at p1" was not found in any source | yes | Dropped; kept "at p5 theory sustains no collusion" |
| O11 | 1.1 | "Closest to necessary" pushes against MASTER's warning | yes | Now "the largest lever" |
| Trim | 1.5, 2.1, 3.1 | Full restatements of the formula and no-numbers result | yes | Each replaced by one sentence plus "see 1.1"; the numbers in each section's own table are kept |
| Length | All | Headlines and "What we observed" are longer than the spec allows | partly | Only the cheap trims were made; headlines are still long |
