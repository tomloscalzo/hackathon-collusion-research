# VERIFY: gpt-oss-20b primary Step 4 (STEP4.md) against the source of truth

*Every number token in `STEP4.md` was extracted by script with its line and section, then looked up in the source file(s) cited for that part (`results/claims-dossiers/MASTER_CLAIMS.md`, the dossier `ANALYSIS.md` files and CSVs, `results/oss/ad-hoc/*`, `results/oss/trackm-neutral-2026-10-26/step2` to `step4`). Every value written as `x [lo, hi]` was also checked as a unit: all three numbers had to appear in order on one source row. Then every interval was re-checked against the full-precision CSV row, and every candidate mismatch, every interval method and the whole three-number box were checked by hand. Created by Claude at the prompting of the repository owner.*

## 1. Summary

Number tokens checked: **2070**.

| Result | Count | Meaning |
|---|---|---|
| match | 1143 | The value appears as written in the assigned source |
| rounding | 416 | The source has more decimals and rounds (half up) to the value in the text |
| definition | 498 | Structural number: sub-question id, section cross-reference, the 1.00 floor, 3.00 monopoly, 5.00 cap, 0.01 tick, 2.09 level (0.546), fines 100 / 500 / 2,000, 70% / 30%, printed example prices, single-digit counts (rounds, points, list items) |
| **mismatch** | 13 | The text differs from the source; correct value and fix below |
| not found | 0 | No source value found (none remain after hand-checking) |

Plus **2 interval-method mismatches** (wording, not numbers) and several **source conflicts** where two source files disagree (section 4); these need a decision, not a correction.

<small>

**How to read the per-number check column.** *value + CI on one source row*: the estimate and both interval ends were found together, in order, on one row of the source (the strongest automatic check). *value in assigned source*: the single number was found in the file assigned to that line; a short number such as 0.22 occurs in many places, so this check is weak on its own, and every such number that carries an effect, a count or a p-value was also read in context by hand (sections 3 and 5). *hand-checked against full-precision csv*: compared with the unrounded CSV value. *structural*: a definition, not a result.

</small>

## 2. Mismatches: correct value and exact fix list

Each fix is an exact string replacement in `STEP4.md` (old string occurs exactly once unless stated). Fix the text, never the source.

| # | Section, line | Old string | New string | Correct value and source |
|---|---|---|---|---|
| 1 | Preamble, 3 | `detector AUCs carry 95% bootstrap intervals over games` | `detector AUCs carry 95% bootstrap intervals over (wording, seed) pairs` | Interval method: `results/claims-dossiers/07-detection/ANALYSIS.md` line 99 ("95% CIs bootstrap over pairs (2,000 draws); a game-level bootstrap is given for comparison"); `out/detector_auc.csv` auc_lo 0.674 (pairs) vs auc_lo_gameboot 0.660 |
| 2 | Box legend, 38 | `95% percentile bootstrap interval over (wording, seed) pairs (Tracks 1 and 3) or over games (Track 2 AUC)` | `95% percentile bootstrap interval over (wording, seed) pairs (Tracks 1 and 3, and the Track 2 AUC)` | Same source as above |
| 3 | 1.1 Table 1.1, 76 | `-0.39 [-0.62, -0.14]` | `-0.39 [-0.62, -0.13]` | Heavy fine, no chat, spread: -0.3853 [-0.6169, -0.1346], `results/claims-dossiers/03-penalty-and-thinking/penalty_contrasts.csv` line 167 (dossier text -0.135 was rounded twice) |
| 4 | 1.2 Table 1.2, 128; 1.5 Table 1.5, 273; 3.2 Table 3.2, 551 | `-0.19 [-0.27, -0.12]` | `-0.19 [-0.27, -0.11]` | n3-ethics minus n3-group matching share: -0.1933 [-0.2733, -0.1149], `results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv` line 215. **Occurs 3 times: replace all** (line 551 is inside `**...**`) |
| 5 | 1.2 Table 1.2, 128 | `-0.01 [-0.16, +0.16]` | `-0.01 [-0.16, +0.15]` | n3-group minus headline-chat matching share: -0.0066 [-0.1591, +0.1547], `contrasts.csv` line 259 of dossier 08 (dossier text +0.155 rounded twice) |
| 6 | 1.5 Table 1.5, 275 | `-0.16 [-0.28, -0.05]` | `-0.16 [-0.28, -0.04]` | d-cot-monitor-a matching share: -0.1605 [-0.2767, -0.0447], `results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv` line 6; Table 3.4 already prints -0.04 |
| 7 | 2.2 Table 2.2, 382 | `0.29 [0.21, 0.37]` | `0.29 [0.20, 0.37]` | All-chat text detector recall: 0.288 [0.2047, 0.3688], `results/claims-dossiers/07-detection/out/detector_auc.csv` line 27 (dossier text prints 0.21); Section 1.3 already prints 0.20 |
| 8 | 2.3 Table 2.3, 432 | `\| 2.225 \|` | `\| 2.226 \|` | headline-chat p3 spread: 2.2255085, `results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv` line 3 (dossier 06 prints 2.226) |
| 9 | 3.1 Table 3.1, 496 | `\| 1.78 [1.59, 1.96] \|` | `\| 1.77 [1.59, 1.96] \|` | headline-tacit p1 spread: 1.7749585, `cell_levels.csv` line 5 of dossier 02 (the dossier text and `results/oss/ad-hoc/penalty/cells.csv` print 1.78 / 1.775, a double rounding); the price index 0.39 is unaffected |
| 10 | 3.4 Also tested, 644 | `Threatening to report added -0.07 [-0.19, +0.02], p 0.22.` | `Threatening to report added -0.06 [-0.15, +0.03] on the price index (p 0.27) and -0.07 [-0.18, +0.02] on profit gain (p 0.22).` | Report-threat increment, `results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv` lines 23 and 24 (the values used in Section 3.2). The old string is MASTER_CLAIMS G-watchdog's profit-gain figure (-0.074 [-0.186, +0.020], a different bootstrap), shown without its metric inside a price-index sentence |

<small>

**Terms.** *Double rounding*: a dossier printed a value to three decimals ending in 5 (for example -0.135) and the draft rounded that again to two decimals (-0.14); the unrounded value (-0.1346) rounds to -0.13. *Interval method*: how the 95% interval was computed (here: percentile bootstrap resampling whole (wording, seed) pairs versus resampling single games).

</small>

## 3. Hand checks of interval methods, signs, statuses and question texts

| Item | What the text says | What the source says | Result |
|---|---|---|---|
| Paired effects, Sections 1.1, 1.2, 1.5, 2.1, 3.1, 3.2, 3.4 | 95% percentile bootstrap over (wording, seed) pairs; exact sign-flip p; Holm in the dossier family | Dossiers 01, 02, 08, 09: percentile bootstrap over pairs, 10,000 resamples; 03 and the ad-hoc controls: 2,000 draws; exact sign-flip tests | match |
| Detector AUCs, Sections 1.3 and 2.2 | Section 1.3 and 2.2 terms: bootstrap over whole pairs, 2,000 draws | 07-detection/ANALYSIS.md line 99: pairs, 2,000 draws | match (but preamble line 3 and box legend line 38 say "over games": fixes 1 and 2) |
| Flag counts, Section 1.3 | Exact binomial (Clopper-Pearson) intervals | 07-detection section 4: 19/20 [0.75, 1.00], 0/20 [0.00, 0.17]; frozen_operating_points.csv recall 0.00 [0.00, 0.100] for 0 of 35 | match |
| Same-round undercut, 1.4 and 2.2 | 0.23 [0.20, 0.26] vs 0.25 [0.21, 0.28] | 07-detection ANALYSIS line 286, ratio estimator, pair bootstrap 2,000 draws | match |
| Cell levels, Table 3.1 | 95% bootstrap over games | One game per pair per cell, so over games = over pairs (fig_3_1.csv from ad-hoc penalty/cells.csv and controls/cell_means.csv, 2,000 draws) | match |
| Step 2 intervals | Preamble says the exact paired dossier intervals are used, not the narrower Step 2 stratified ones | MASTER_CLAIMS caveats: Step 2 stratified bootstrap about half the honest width | match; the watchdog report-threat interval in 3.2 is the exact paired one |
| Signs of headline effects | 1.1/1.5/2.1 formula and no-numbers lower prices; chat raises; p5 lowers; n3-ethics lowers; cheater lowers (mechanical); threat lowers | MASTER_CLAIMS G-payoff, G-comm, G-penalty, G-n3ethics, G-cheater, G-cot: same signs | match |
| Statuses | Confirmed (strong) G-payoff; confirmed G-comm, G-penalty (rephrased), G-moral, G-5tick, G-n3ethics (exploratory, moderate), G-fxjoint (moderate), G-ctl (rephrased), G-repro (moderate), G-detect-quotes (relabelled), Q9-frozen, G-cot-mech, D11-1, D11-2, D11-3; downgraded G-detect-text, G-cheater, G-watchdog, Q10-saydo (gpt-oss); bounded nulls G-interaction, G-null-struct, G-intro-null; dropped G-r2s; G-cot confirmed as stated, unresolved; G-asym-talk suggestive | MASTER_CLAIMS section 3 and the ledger table | match |
| Question texts | Twelve sub-question texts | `alignment/AREAS_TO_SPRINT_OBJECTIVES.md` line 18 to 20 | match, verbatim for all twelve |
| Second-model lines | Qwen numbers in the one-line notes | MASTER_CLAIMS G-payoff (-0.63 / -0.51, -0.70), G-comm (+0.17 [0.12, 0.22]), G-fxjoint (-0.36), G-n3ethics (+0.016 [-0.069, +0.097], matching -0.175), G-cheater (-0.041), Q-AUC (0.90 [0.84, 0.95], -0.00 [-0.03, +0.04], +0.04), Q9-frozen (15/20), G-moral (-0.22 / -0.32), Q-5tick (-0.546), G-cot (-0.232 [-0.308, -0.152], Holm 0.002, -27%), G-cot-mech (flag -0.55), Q4-conflict (1.00), H1 (+0.14 / +0.40), dossier 04 (-0.77 [-0.84, -0.69], +0.72) | match |

## 4. Source conflicts (no correction required; the lead should choose one value)

| Section, line | Text value | Source A | Source B | Recommendation |
|---|---|---|---|---|
| 1.5 Table 1.5, 272 | 5-tick Holm 0.020 | 06-five-tick-start whole_game_contrasts.csv and ANALYSIS.md: Holm 0.0201 (family 15) | MASTER_CLAIMS G-5tick: Holm 0.018 (family 15) | Brief says MASTER wording wins; either value supports the claim. Optional: `Holm 0.020; -0.25` -> `Holm 0.018; -0.25` |
| 1.3 Why it matters, 220 | hard cases -0.01 [-0.12, +0.09] (252 games, 44 risers) | 07-detection out/hard_cases_text_minus_early.csv row O-B: -0.0134 [-0.1174, +0.0918] | MASTER_CLAIMS G-detect-text: -0.02 [-0.12, +0.08] (population not named) | Keep the csv value: it is the row whose n (252, 44) the text quotes |
| 3.4 Also tested, 644 vs 1.2 / 1.5 / 3.2 | m-asym price -0.02 [-0.11, +0.09] (3.4) and -0.02 [-0.12, +0.09] (elsewhere) | 09 oversight contrasts.csv: -0.0181 [-0.1148, +0.0918] | 08 contrasts.csv and MASTER G-null-struct: -0.018 [-0.117, +0.091] | Both correct for their source; for one number across the page use `-0.02 [-0.12, +0.09]` in 3.4 too (old `price index -0.02 [-0.11, +0.09], MDE 0.15` -> `price index -0.02 [-0.12, +0.09], MDE 0.15`) |
| 3.4 Also tested, 644 | watchdog -0.02 to +0.04 | 09 oversight contrasts.csv: -0.022, +0.038, -0.0249 | MASTER G-watchdog: -0.03 to +0.04 | Keep: the unrounded -0.0249 rounds to -0.02 |
| 2.1 Table 2.1 legend, 340 | pooled spread, profit gain and share values are point estimates (no CI in source) | 02 tables/contrasts_within_model.csv has pooled CIs: +0.41 [+0.22, +0.59], +0.25 [+0.13, +0.36], -0.24 [-0.33, -0.14], +0.21 [+0.11, +0.30] (used in the box and Table 1.1) | 02 ANALYSIS.md section 2 prints them without CIs | Optional: add the CIs to the chat column of Table 2.1 and drop the legend sentence |
| 2.1 What we observed, 319 | 0.40 to 0.47 exactly on a printed value; 0.24 to 0.28 under | 01 Table 2a: chat p1 0.40 / 0.28; pooled 100 games 0.47 / 0.24 | Per-cell range is 0.37 to 0.63 exact (p5 cells higher) | Acceptable as the chat-p1 and pooled values; say so if precision matters |
| 1.2 Table 1.2, 124 and 128; 3.2, 551 | +0.23, +0.04 | 08 contrasts.csv +0.2250 and +0.0350 (4 decimals) | - | Borderline half-up rounding; no change |

## 5. The three-number box, checked in full by hand

| Box number | Text | Source value | Source | Result |
|---|---|---|---|---|
| Track 1 headline | -0.30 [-0.43, -0.16], 19 pairs | -0.3016 [-0.4346, -0.1588], n 19 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv (fx-chat-p1 - headline-chat p1); ANALYSIS.md Table 1a | rounding |
| Track 1 cells | -0.22 / -0.30 / -0.37; no numbers -0.38 / -0.56 | -0.2212 / -0.3016 / -0.3654; -0.3794 / -0.5567 | 01 paired_contrasts.csv | rounding |
| Track 1 capability | joint-profit with formula reaches printed level | +0.01 [-0.11, +0.11], 20 pairs | 01 Table 3a; MASTER G-fxjoint | match |
| Track 1 status | Post hoc; confirmed (strong) | Confirmed (strong), post hoc | MASTER G-payoff | match |
| Track 2 headline | AUC 0.81 [0.67, 0.93] (57 games) to 0.91 [0.87, 0.94] (524 games) | 0.8136 [0.6744, 0.9286]; 0.9104 [0.8701, 0.9401] | results/claims-dossiers/07-detection/out/detector_auc.csv rows O-A, O-B | rounding |
| Track 2 text gain | -0.01 [-0.02, +0.01] (524 games) | -0.0082 [-0.0246, +0.0084] | 07 out/detector_auc_diff.csv O-B | rounding |
| Track 2 keyword rule | 19 of 20 told-to-compete games | 19/20 [0.75, 1.00] | 07 ANALYSIS line 201; MASTER Q9-frozen | match |
| Track 2 status | Exploratory, frozen parameters; confirmed | Confirmed, relabelled (G-detect-quotes); Q9-frozen confirmed | MASTER | match |
| Track 3 headline | +0.21 [0.11, 0.29], 20 pairs, pooled p1 and p5 | +0.2069 [+0.1139, +0.2942], n 20 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv line 13; MASTER G-comm | rounding |
| Track 3 baseline | no-chat price index 0.39 at point 1 | 0.38748 | 02 cell_levels.csv line 5 | rounding |
| Track 3 waves | chat waves 7 to 12, no chat 13 to 16 | same | MASTER section 2 caveats | match |
| Track 3 joint gap | 0.13 below joint-profit control (0.13 [0.06, 0.22]) | +0.1316 [+0.0610, +0.2175] | 04 g_ctl_contrasts.csv line 6; MASTER G-ctl | rounding |
| Track 3 status | Declared; confirmed (Holm p 0.020 at point 1, 0.016 at point 5) | Declared; p1 Holm 0.020, p5 0.016 | MASTER G-comm; 02 ANALYSIS lines 116-117 | match |
| Five-metric table, Track 1 | -0.60 [-0.87, -0.32]; -0.30 [-0.43, -0.16]; -0.40 [-0.55, -0.25]; -0.13 [-0.24, -0.03]; -0.01 [-0.15, +0.13] | same | 01 ANALYSIS Table 1a line 66 | match |
| Five-metric table, Track 3 | +0.41 [+0.22, +0.59]; +0.21 [+0.11, +0.29]; +0.25 [+0.13, +0.36]; -0.24 [-0.33, -0.14]; +0.21 [+0.11, +0.30] | +0.4137 [0.2221, 0.5878]; +0.2069 [0.1139, 0.2942]; +0.2491 [0.1269, 0.3589]; -0.2362 [-0.3279, -0.1372]; +0.2097 [0.1115, 0.2997] | 02 contrasts_within_model.csv lines 12-16 | rounding |
| Box legend [a, b] | Track 2 AUC interval over games | over (wording, seed) pairs | 07 ANALYSIS line 99 | **MISMATCH** (fix 2) |

## 6. Every number in STEP4.md

*Columns: section; line in `STEP4.md`; the number as written; the source value found (blank for structural numbers); the source file and line (repo-relative); the result; the kind of check; a note where needed. Signs are compared by hand for effects (sign-agnostic lookup).* 

| Section | Line | Number in text | Source value | Source file | Result | Check | Note |
|---|---|---|---|---|---|---|---|
| Preamble | 3 | AUC interval method | auc_lo/auc_hi are the pair bootstrap (0.674 / 0.929); the game bootstrap is a separate column (0.660 / 0.927) | results/claims-dossiers/07-detection/out/detector_auc.csv:18; 07-detection/ANALYSIS.md:99 | **MISMATCH** (method) | hand-checked | text says AUC intervals are over games; they are over (wording, seed) pairs, 2,000 draws |
| Three-number box | 38 | [a, b] legend | as above | results/claims-dossiers/07-detection/ANALYSIS.md:99 | **MISMATCH** (method) | hand-checked | legend says Track 2 AUC interval is over games; it is over pairs |
| Preamble | 1 | 4 |  |  | definition | structural |  |
| Preamble | 3 | 2.09 |  |  | definition | structural |  |
| Preamble | 3 | 2 |  |  | definition | structural |  |
| Preamble | 3 | 3 |  |  | definition | structural |  |
| Preamble | 3 | 7 |  |  | definition | structural |  |
| Preamble | 3 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Preamble | 3 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Preamble | 3 | 95% |  |  | definition | structural |  |
| Preamble | 3 | 95% |  |  | definition | structural |  |
| Preamble | 5 | 2 |  |  | definition | structural |  |
| Preamble | 8 | 1 |  |  | definition | structural |  |
| Preamble | 8 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| Preamble | 8 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| Preamble | 8 | +0.05 | 0.05 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| Preamble | 8 | +0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| Preamble | 8 | 99 | 99 | results/claims-dossiers/MASTER_CLAIMS.md:99 | match | value in assigned source |  |
| Preamble | 8 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| Preamble | 9 | 2 |  |  | definition | structural |  |
| Preamble | 9 | 1 |  |  | definition | structural |  |
| Preamble | 9 | 5 |  |  | definition | structural |  |
| Preamble | 9 | 7 |  |  | definition | structural |  |
| Preamble | 9 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Preamble | 9 | 13 | 13 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Preamble | 9 | 16 | 16 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Preamble | 9 | 3 |  |  | definition | structural |  |
| Preamble | 9 | 107 | 107 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Preamble | 9 | 112 | 112 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Preamble | 10 | 3 |  |  | definition | structural |  |
| Preamble | 10 | +-0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| Three-number box | 16 | 95% |  |  | definition | structural |  |
| Three-number box | 18 | 1 |  |  | definition | structural |  |
| Three-number box | 18 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| Three-number box | 18 | -0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| Three-number box | 18 | -0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value in assigned source |  |
| Three-number box | 18 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| Three-number box | 18 | 1 |  |  | definition | structural |  |
| Three-number box | 18 | 1 |  |  | definition | structural |  |
| Three-number box | 18 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| Three-number box | 18 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| Three-number box | 18 | -0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value in assigned source |  |
| Three-number box | 18 | 5 |  |  | definition | structural |  |
| Three-number box | 18 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| Three-number box | 18 | -0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| Three-number box | 18 | 1.00 |  |  | definition | structural |  |
| Three-number box | 19 | 2 |  |  | definition | structural |  |
| Three-number box | 19 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| Three-number box | 19 | 0.67 | 0.67 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| Three-number box | 19 | 0.93 | 0.93 | results/claims-dossiers/MASTER_CLAIMS.md:98 | match | value in assigned source |  |
| Three-number box | 19 | 57 | 57 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| Three-number box | 19 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| Three-number box | 19 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| Three-number box | 19 | 0.94 | 94% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| Three-number box | 19 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| Three-number box | 19 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| Three-number box | 19 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| Three-number box | 19 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| Three-number box | 19 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| Three-number box | 19 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| Three-number box | 19 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Three-number box | 20 | 3 |  |  | definition | structural |  |
| Three-number box | 20 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| Three-number box | 20 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| Three-number box | 20 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| Three-number box | 20 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Three-number box | 20 | 1 |  |  | definition | structural |  |
| Three-number box | 20 | 5 |  |  | definition | structural |  |
| Three-number box | 20 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| Three-number box | 20 | 1 |  |  | definition | structural |  |
| Three-number box | 20 | 7 |  |  | definition | structural |  |
| Three-number box | 20 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Three-number box | 20 | 13 | 13 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Three-number box | 20 | 16 | 16 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| Three-number box | 20 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| Three-number box | 20 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| Three-number box | 20 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| Three-number box | 20 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| Three-number box | 20 | 0.020 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| Three-number box | 20 | 1 |  |  | definition | structural |  |
| Three-number box | 20 | 0.016 | 0.016 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| Three-number box | 20 | 5 |  |  | definition | structural |  |
| Three-number box | 22 | 95% |  |  | definition | structural |  |
| Three-number box | 22 | 2 |  |  | definition | structural |  |
| Three-number box | 24 | 1 |  |  | definition | structural |  |
| Three-number box | 24 | 1 |  |  | definition | structural |  |
| Three-number box | 24 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| Three-number box | 24 | 3 |  |  | definition | structural |  |
| Three-number box | 24 | 1 |  |  | definition | structural |  |
| Three-number box | 24 | 5 |  |  | definition | structural |  |
| Three-number box | 24 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Three-number box | 26 | 1.00 |  |  | definition | structural |  |
| Three-number box | 26 | 5.00 |  |  | definition | structural |  |
| Three-number box | 26 | -0.60 | 0.60 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 26 | -0.87 | 0.87 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 26 | -0.32 | 0.32 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 26 | +0.41 | 0.41 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| Three-number box | 26 | +0.22 | 0.22 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| Three-number box | 26 | +0.59 | 0.59 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| Three-number box | 27 | 0 |  |  | definition | structural |  |
| Three-number box | 27 | 1 |  |  | definition | structural |  |
| Three-number box | 27 | -0.30 | 0.30 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 27 | -0.43 | 0.43 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 27 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 27 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| Three-number box | 27 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| Three-number box | 27 | +0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| Three-number box | 28 | 0 |  |  | definition | structural |  |
| Three-number box | 28 | 1 |  |  | definition | structural |  |
| Three-number box | 28 | -0.40 | 0.40 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 28 | -0.55 | 0.55 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 28 | -0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 28 | +0.25 | 0.25 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| Three-number box | 28 | +0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| Three-number box | 28 | +0.36 | 0.36 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| Three-number box | 29 | -0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 29 | -0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 29 | -0.03 | 0.03 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 29 | -0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 29 | -0.33 | 0.33 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| Three-number box | 29 | -0.14 | 0.14 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| Three-number box | 30 | -0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 30 | -0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 30 | +0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| Three-number box | 30 | +0.21 | 0.21 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| Three-number box | 30 | +0.11 | 0.11 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| Three-number box | 30 | +0.30 | 0.30 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| Three-number box | 38 | 95% |  |  | definition | structural |  |
| Three-number box | 38 | 1 |  |  | definition | structural |  |
| Three-number box | 38 | 3 |  |  | definition | structural |  |
| Three-number box | 38 | 2 |  |  | definition | structural |  |
| Three-number box | 39 | - 1.00 |  |  | definition | structural |  |
| Three-number box | 39 | 2.00 |  |  | definition | structural |  |
| Three-number box | 39 | 0 |  |  | definition | structural |  |
| Three-number box | 39 | 1.00 |  |  | definition | structural |  |
| Three-number box | 39 | 1 |  |  | definition | structural |  |
| Three-number box | 39 | 3.00 |  |  | definition | structural |  |
| Three-number box | 40 | 0.5 |  |  | definition | structural |  |
| Three-number box | 42 | 1.00 |  |  | definition | structural |  |
| Three-number box | 42 | 4.00 |  |  | definition | structural |  |
| Three-number box | 44 | 1 |  |  | definition | structural |  |
| Game in four lines | 53 | 1.00 |  |  | definition | structural |  |
| Game in four lines | 53 | 5.00 |  |  | definition | structural |  |
| Game in four lines | 53 | 0.01 |  |  | definition | structural |  |
| Game in four lines | 54 | 1.00 |  |  | definition | structural |  |
| Game in four lines | 54 | 3.00 |  |  | definition | structural |  |
| Game in four lines | 54 | 3 |  |  | definition | structural |  |
| Game in four lines | 54 | 2.09 |  |  | definition | structural |  |
| Game in four lines | 54 | 0.546 |  |  | definition | structural |  |
| Game in four lines | 55 | - 70% |  |  | definition | structural |  |
| Game in four lines | 55 | 100 |  |  | definition | structural |  |
| Game in four lines | 55 | 2000 |  |  | definition | structural |  |
| Game in four lines | 56 | 0 |  |  | definition | structural |  |
| Game in four lines | 56 | 1.00 |  |  | definition | structural |  |
| Game in four lines | 56 | 1 |  |  | definition | structural |  |
| Game in four lines | 56 | 3.00 |  |  | definition | structural |  |
| Game in four lines | 58 | 4 |  |  | definition | structural |  |
| Game in four lines | 58 | 01 | 1.00 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| Game in four lines | 58 | 11 | 11 | results/claims-dossiers/MASTER_CLAIMS.md:55 | match | value in assigned source |  |
| Game in four lines | 58 | 2 |  |  | definition | structural |  |
| Game in four lines | 58 | 4 |  |  | definition | structural |  |
| 1.1 | 62 | 1.1 |  |  | definition (section id) | structural |  |
| 1.1 | 62 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.1 | 62 | -0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value in assigned source |  |
| 1.1 | 62 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 62 | -0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 62 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 1.1 | 64 | 1.1 | 1.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.1 | 66 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.1 | 66 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 66 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.004 | 0.004 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 66 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 66 | 0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 66 | 0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 1.1 | 66 | 1.00 |  |  | definition | structural |  |
| 1.1 | 66 | 0 |  |  | definition | structural |  |
| 1.1 | 66 | +-0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.1 | 66 | 0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.41 | 0.41 | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.54 | 54% | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.28 | 0.28 | results/claims-dossiers/01-focal-points/ANALYSIS.md:416 | match | value + CI on one source row |  |
| 1.1 | 66 | 100 |  |  | definition | structural |  |
| 1.1 | 66 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 1.1 | 66 | 1 |  |  | definition | structural |  |
| 1.1 | 66 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.44 | 44% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 66 | -0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value + CI on one source row |  |
| 1.1 | 66 | +0.31 | 0.31 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value + CI on one source row |  |
| 1.1 | 66 | 0.31 | 0.31 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value + CI on one source row |  |
| 1.1 | 66 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 66 | -0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 66 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 66 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 68 | 1.1 | 1.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.1 | 68 | 95% |  |  | definition | structural |  |
| 1.1 | 72 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 72 | -0.44 | 44% | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.69 | 0.69 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.22 | 0.22 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.09 | 0.09 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.51 | 0.51 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.27 | 0.27 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.37 | 0.37 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | -0.17 | 0.17 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | +0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | +0.05 | 0.05 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 72 | +0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.1 | 73 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.1 | 73 | -0.60 | 0.60 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.87 | 0.87 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.32 | 0.32 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.30 | 0.30 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.43 | 0.43 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.40 | 0.40 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.55 | 0.55 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.03 | 0.03 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | -0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 73 | +0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.1 | 74 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 74 | -1.11 | 1.11 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -1.27 | 1.27 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.94 | 94% | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.56 | 0.56 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.64 | 0.64 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.74 | 0.74 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.82 | 0.82 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.63 | 0.63 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.20 | 20% | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.32 | 0.32 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.08 | 0.08 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | +0.14 | 0.14 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | -0.02 | 0.020 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 74 | +0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.1 | 75 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 75 | +0.41 | 0.41 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.22 | 0.22 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.59 | 0.59 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 75 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 75 | +0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 75 | +0.25 | 0.25 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.36 | 0.36 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 1.1 | 75 | -0.24 | 0.24 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 1.1 | 75 | -0.33 | 0.33 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 1.1 | 75 | -0.14 | 0.14 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 1.1 | 75 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 75 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 75 | +0.30 | 0.30 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| 1.1 | 76 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 76 | -0.39 | 0.39 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.62 | 0.62 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.14 | -0.1346 (ci_hi) | results/claims-dossiers/03-penalty-and-thinking/penalty_contrasts.csv:167 | **MISMATCH** | hand-checked against full-precision csv | double rounding of -0.135; correct -0.13 |
| 1.1 | 76 | -0.19 | 0.19 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.31 | 0.31 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.07 | 0.07 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.44 | 44% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.14 | 0.14 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.01 | 0.01 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.12 | 0.12 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | +0.11 | 0.11 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.01 | 0.01 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | -0.11 | 0.11 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 76 | +0.10 | 0.10 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.1 | 77 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 77 | -0.30 | 0.30 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.58 | 0.58 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.03 | 0.03 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.15 | 0.15 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.29 | 0.29 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.02 | 0.020 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.1 | 77 | +0.03 | 0.03 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.10 | 0.10 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | +0.15 | 0.15 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.08 | 0.08 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | -0.21 | 0.21 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 77 | +0.04 | 4% | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.1 | 78 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 78 | +0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.23 | 0.23 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.23 | 0.23 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.04 | 4% | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.06 | 0.060 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.26 | 0.26 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.34 | 0.34 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | -0.18 | 0.18 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.02 | 0.020 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 1.1 | 78 | +0.21 | 0.21 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 1.1 | 79 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.1 | 79 | +0.68 | 68% | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.28 | 0.28 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +1.04 | 1.04 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.34 | 0.34 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.52 | 0.52 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.40 | 0.40 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.61 | 0.61 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | -0.11 | 0.11 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | -0.20 | 20% | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | -0.02 | 0.020 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.09 | 0.09 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | -0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 79 | +0.18 | 0.18 | results/claims-dossiers/01-focal-points/ANALYSIS.md:560 | match | value + CI on one source row |  |
| 1.1 | 83 | 1.1 | 1.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.1 | 83 | 01 | 1.00 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 83 | 5 |  |  | definition | structural |  |
| 1.1 | 83 | 0.004 | 0.004 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 83 | -0.38 | 0.38 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.1 | 83 | -0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.1 | 83 | -0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.1 | 83 | -0.37 | 0.37 | results/claims-dossiers/01-focal-points/ANALYSIS.md:70 | match | value + CI on one source row |  |
| 1.1 | 83 | -0.44 | 44% | results/claims-dossiers/01-focal-points/ANALYSIS.md:70 | match | value + CI on one source row |  |
| 1.1 | 83 | -0.28 | 0.28 | results/claims-dossiers/01-focal-points/ANALYSIS.md:70 | match | value + CI on one source row |  |
| 1.1 | 83 | 02 | 2 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 1.1 | 83 | 25 | 25 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.1 | 83 | 0.009 | 0.009 | results/claims-dossiers/MASTER_CLAIMS.md:138 | match | value in assigned source |  |
| 1.1 | 83 | 03 | 3.00 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 83 | 1 |  |  | definition | structural |  |
| 1.1 | 83 | 4 |  |  | definition | structural |  |
| 1.1 | 83 | 0.008 | 0.008 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.1 | 83 | 0.060 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.1 | 83 | 01 | 1.00 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 83 | 1.01 | 1.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:169 | match | value in assigned source |  |
| 1.1 | 83 | 1.05 | 1.05 | results/claims-dossiers/MASTER_CLAIMS.md:152 | match | value in assigned source |  |
| 1.1 | 87 | 1.00 |  |  | definition | structural |  |
| 1.1 | 87 | 5.00 |  |  | definition | structural |  |
| 1.1 | 88 | - 1 |  |  | definition | structural |  |
| 1.1 | 88 | 2 |  |  | definition | structural |  |
| 1.1 | 88 | 0 |  |  | definition | structural |  |
| 1.1 | 88 | 1.00 |  |  | definition | structural |  |
| 1.1 | 88 | 1 |  |  | definition | structural |  |
| 1.1 | 88 | 3.00 |  |  | definition | structural |  |
| 1.1 | 90 | 1.00 |  |  | definition | structural |  |
| 1.1 | 91 | 1.00 |  |  | definition | structural |  |
| 1.1 | 92 | 70 | 70 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.1 | 92 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 93 | 100 |  |  | definition | structural |  |
| 1.1 | 93 | 500 |  |  | definition | structural |  |
| 1.1 | 93 | 2000 |  |  | definition | structural |  |
| 1.1 | 95 | 2.8 |  |  | definition | structural |  |
| 1.1 | 95 | 80% |  |  | definition | structural |  |
| 1.1 | 99 | +-0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.1 | 99 | 11 | 11 | results/claims-dossiers/MASTER_CLAIMS.md:55 | match | value in assigned source |  |
| 1.1 | 99 | -0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.1 | 99 | -0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.1 | 99 | +0.00 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.1 | 101 | -0.63 | 0.63 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.1 | 101 | -0.51 | 0.51 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.1 | 101 | +0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 101 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 101 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 1.1 | 101 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.1 | 109 | +-0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.1 | 110 | 7 |  |  | definition | structural |  |
| 1.1 | 110 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 1.1 | 110 | 13 | 13 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 1.1 | 110 | 16 | 16 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 1.2 | 114 | 1.2 |  |  | definition (section id) | structural |  |
| 1.2 | 114 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 114 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 114 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 114 | 0.22 | 0.22 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 114 | 0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 114 | 0.36 | 0.36 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 116 | 1.2 | 1.2 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.2 | 118 | 3 |  |  | definition | structural |  |
| 1.2 | 118 | 0.22 | 0.22 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 0.36 | 0.36 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.2 | 118 | 0.022 | 0.022 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 1.2 | 118 | 0.26 | 0.26 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 0.42 | 0.42 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.2 | 118 | -0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 1.2 | 118 | -0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 1.2 | 118 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 1.2 | 118 | +0.03 | 0.03 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 1.88 |  |  | definition | structural |  |
| 1.2 | 118 | 1.00 |  |  | definition | structural |  |
| 1.2 | 118 | 0.23 | 0.23 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:86 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 0.17 | 0.17 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:86 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 0.29 | 0.29 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:86 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.2 | 118 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.2 | 118 | -0.27 | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.2 | 118 | -0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.2 | 118 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 118 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 118 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 0.03 | 0.03 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 1.2 | 118 | 0.17 | 0.17 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:86 | rounding | value + CI on one source row |  |
| 1.2 | 118 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 118 | -0.08 | 0.08 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 118 | +0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 1.2 | 118 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.2 | 120 | 1.2 | 1.2 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.2 | 120 | 3 |  |  | definition | structural |  |
| 1.2 | 120 | 95% |  |  | definition | structural |  |
| 1.2 | 122 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.2 | 122 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.2 | 122 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.2 | 124 | 1.00 |  |  | definition | structural |  |
| 1.2 | 124 | 5.00 |  |  | definition | structural |  |
| 1.2 | 124 | -0.45 | 0.45 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.71 | 71% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.46 | 0.46 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.57 | 0.57 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.35 | 0.35 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 1.2 | 124 | +0.01 | 0.01 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:361 | rounding | value + CI on one source row |  |
| 1.2 | 124 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:361 | rounding | value + CI on one source row |  |
| 1.2 | 124 | +0.23 | 0.23 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:361 | rounding | hand-checked | source +0.2250 at 4 decimals: borderline half-up rounding |
| 1.2 | 125 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.23 | 0.23 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.29 | 0.29 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.27 | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.2 | 125 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 125 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 125 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 1.2 | 125 | -0.08 | 0.08 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 125 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.26 | 0.26 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.42 | 0.42 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.33 | 0.33 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.43 | 0.43 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.24 | 0.24 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 1.2 | 126 | +0.03 | 0.03 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:355 | rounding | value + CI on one source row |  |
| 1.2 | 126 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:355 | rounding | value + CI on one source row |  |
| 1.2 | 126 | +0.15 | 0.15 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:355 | rounding | value + CI on one source row |  |
| 1.2 | 127 | +0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.2 | 127 | +0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.2 | 127 | +0.27 | 0.27 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.18 | 0.18 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 1.2 | 127 | +0.05 | 0.05 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.29 | 0.29 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.00 | 0 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:364 | rounding | value + CI on one source row |  |
| 1.2 | 127 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:364 | rounding | value + CI on one source row |  |
| 1.2 | 127 | +0.16 | 0.16 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:364 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.27 | 0.27 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.12 | -0.1149 (hi) | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:215 | **MISMATCH** | hand-checked against full-precision csv | double rounding of -0.115; correct -0.11 |
| 1.2 | 128 | +0.06 | 0.060 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 1.2 | 128 | +0.22 | 0.22 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.24 | 0.24 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:197 | rounding | value + CI on one source row |  |
| 1.2 | 128 | +0.04 | 4% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:197 | rounding | hand-checked | source +0.0350 at 4 decimals: borderline |
| 1.2 | 128 | -0.01 | 0.01 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:365 | rounding | value + CI on one source row |  |
| 1.2 | 128 | -0.16 | 0.16 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:365 | rounding | value + CI on one source row |  |
| 1.2 | 128 | +0.16 | +0.1547 (hi) | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:259 | **MISMATCH** | hand-checked against full-precision csv | double rounding of +0.155; correct +0.15 |
| 1.2 | 133 | 1.2 | 1.2 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.2 | 133 | 08 | 08 | results/claims-dossiers/MASTER_CLAIMS.md:58 | match | value in assigned source |  |
| 1.2 | 133 | 1 |  |  | definition | structural |  |
| 1.2 | 133 | 2 |  |  | definition | structural |  |
| 1.2 | 133 | 4 |  |  | definition | structural |  |
| 1.2 | 133 | 8 |  |  | definition | structural |  |
| 1.2 | 133 | 101 | 101 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:164 | match | value in assigned source |  |
| 1.2 | 133 | 110 | 110 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:164 | match | value in assigned source |  |
| 1.2 | 133 | 1 |  |  | definition | structural |  |
| 1.2 | 133 | 10 | 10 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.2 | 133 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.2 | 133 | 3 |  |  | definition | structural |  |
| 1.2 | 133 | 2 |  |  | definition | structural |  |
| 1.2 | 133 | 8 |  |  | definition | structural |  |
| 1.2 | 133 | 17 | 17 | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 1.2 | 133 | 5 |  |  | definition | structural |  |
| 1.2 | 133 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.2 | 133 | 9 |  |  | definition | structural |  |
| 1.2 | 133 | -0.22 | 0.22 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.2 | 133 | -0.39 | 0.39 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.2 | 133 | -0.05 | 0.05 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.2 | 137 | 3 |  |  | definition | structural |  |
| 1.2 | 137 | 1 |  |  | definition | structural |  |
| 1.2 | 137 | 2 |  |  | definition | structural |  |
| 1.2 | 138 | 1.88 |  |  | definition | structural |  |
| 1.2 | 138 | 1.00 |  |  | definition | structural |  |
| 1.2 | 138 | 6 |  |  | definition | structural |  |
| 1.2 | 138 | 10 | 10 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.2 | 142 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.2 | 146 | 1 |  |  | definition | structural |  |
| 1.2 | 146 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.2 | 146 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 146 | -0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 146 | +0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.2 | 148 | +0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 148 | -0.07 | 0.07 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 148 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.2 | 148 | 0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.2 | 148 | -0.04 | 4% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 1.2 | 148 | -0.08 | 0.08 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 1.2 | 148 | -0.01 | 0.01 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 1.2 | 154 | 1 |  |  | definition | structural |  |
| 1.2 | 155 | 1.00 |  |  | definition | structural |  |
| 1.2 | 155 | 1.88 |  |  | definition | structural |  |
| 1.3 | 164 | 1.3 |  |  | definition (section id) | structural |  |
| 1.3 | 164 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 164 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 166 | 1.3 | 1.3 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.3 | 168 | 1 |  |  | definition | structural |  |
| 1.3 | 168 | 3 |  |  | definition | structural |  |
| 1.3 | 168 | 0.498 | 0.498 | results/claims-dossiers/07-detection/ANALYSIS.md:24 | match | value in assigned source |  |
| 1.3 | 168 | 4 |  |  | definition | structural |  |
| 1.3 | 168 | 0.50 |  |  | definition | structural |  |
| 1.3 | 168 | 2.00 |  |  | definition | structural |  |
| 1.3 | 168 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 0.67 | 0.67 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 0.93 | 0.93 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 57 | 57 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 168 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 168 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 0.94 | 94% | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 168 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 168 | 0.71 | 71% | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value in assigned source |  |
| 1.3 | 168 | 0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 168 | +0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 168 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 168 | +0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 168 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 168 | 0.8 |  |  | definition | structural |  |
| 1.3 | 168 | 0 |  |  | definition | structural |  |
| 1.3 | 168 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 168 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 168 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 168 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 168 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 168 | 1.00 |  |  | definition | structural |  |
| 1.3 | 170 | 95% |  |  | definition | structural |  |
| 1.3 | 170 | 57 | 57 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 170 | 0.61 | 0.61 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value in assigned source |  |
| 1.3 | 170 | 95% |  |  | definition | structural |  |
| 1.3 | 170 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 170 | 0.55 | 0.55 | results/claims-dossiers/MASTER_CLAIMS.md:110 | match | value in assigned source |  |
| 1.3 | 172 | 1 |  |  | definition | structural |  |
| 1.3 | 172 | 3 |  |  | definition | structural |  |
| 1.3 | 172 | 0.498 | 0.498 | results/claims-dossiers/07-detection/ANALYSIS.md:24 | match | value in assigned source |  |
| 1.3 | 172 | 1 |  |  | definition | structural |  |
| 1.3 | 172 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 172 | 0.67 | 0.67 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 172 | 0.93 | 0.93 | results/claims-dossiers/MASTER_CLAIMS.md:98 | match | value in assigned source |  |
| 1.3 | 172 | 0.71 | 71% | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.58 | 0.58 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.86 | 0.86 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.18 | 0.18 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.05 | 0.05 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.35 | 0.35 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 172 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 172 | 0.94 | 94% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 1.3 | 172 | 0.85 | 0.85 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.79 | 0.79 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.89 | 0.89 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.14 | 0.14 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 172 | 0.18 | 0.18 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 1.3 | 173 | 1 |  |  | definition | structural |  |
| 1.3 | 173 | 0.65 | 0.65 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.50 | 0.50 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.79 | 0.79 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.29 | 0.29 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.11 | 0.11 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.46 | 0.46 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 1.3 | 173 | 0.71 | 71% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.66 | 0.66 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.75 | 75% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.29 | 0.29 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.20 | 20% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value + CI on one source row |  |
| 1.3 | 173 | 0.08 | 0.08 | results/claims-dossiers/MASTER_CLAIMS.md:109 | match | value in assigned source |  |
| 1.3 | 174 | 7 |  |  | definition | structural |  |
| 1.3 | 174 | 1 |  |  | definition | structural |  |
| 1.3 | 174 | 0.84 | 0.84 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.72 | 0.72 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.94 | 94% | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.69 | 0.69 | results/claims-dossiers/07-detection/ANALYSIS.md:78 | match | value in assigned source |  |
| 1.3 | 174 | 0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 174 | 0.90 | 0.90 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.86 | 0.86 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.93 | 0.93 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 1.3 | 174 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 174 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 1.3 | 175 | +0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 175 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 175 | +0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 175 | 0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 175 | 1.00 |  |  | definition | structural |  |
| 1.3 | 175 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 175 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 175 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 1.3 | 175 | 0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 1.3 | 175 | 1.00 |  |  | definition | structural |  |
| 1.3 | 176 | 2 |  |  | definition | structural |  |
| 1.3 | 176 | 0.8 |  |  | definition | structural |  |
| 1.3 | 176 | 0.25 |  |  | definition | structural |  |
| 1.3 | 176 | 0 |  |  | definition | structural |  |
| 1.3 | 176 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 176 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 176 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 176 | 0.10 | 0.10 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 176 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 176 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 176 | 10 | 10 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.3 | 176 | 580 | 580 | results/claims-dossiers/07-detection/ANALYSIS.md:202 | match | value in assigned source |  |
| 1.3 | 177 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 177 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 1.3 | 177 | 1.00 |  |  | definition | structural |  |
| 1.3 | 177 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 177 | 0.00 | 0 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 177 | 0.15 | 0.15 | results/claims-dossiers/07-detection/ANALYSIS.md:223 | match | value + CI on one source row |  |
| 1.3 | 177 | 1.00 |  |  | definition | structural |  |
| 1.3 | 177 | 1.00 |  |  | definition | structural |  |
| 1.3 | 177 | 556 | 556 | results/claims-dossiers/07-detection/ANALYSIS.md:202 | match | value in assigned source |  |
| 1.3 | 177 | 580 | 580 | results/claims-dossiers/07-detection/ANALYSIS.md:202 | match | value in assigned source |  |
| 1.3 | 183 | 4 |  |  | definition | structural |  |
| 1.3 | 183 | 0.50 |  |  | definition | structural |  |
| 1.3 | 183 | 2.00 |  |  | definition | structural |  |
| 1.3 | 183 | 2 |  |  | definition | structural |  |
| 1.3 | 184 | - 1.00 |  |  | definition | structural |  |
| 1.3 | 184 | 2.00 |  |  | definition | structural |  |
| 1.3 | 184 | 0 |  |  | definition | structural |  |
| 1.3 | 184 | 1.00 |  |  | definition | structural |  |
| 1.3 | 184 | 1 |  |  | definition | structural |  |
| 1.3 | 184 | 3.00 |  |  | definition | structural |  |
| 1.3 | 185 | 0.5 |  |  | definition | structural |  |
| 1.3 | 185 | 1 |  |  | definition | structural |  |
| 1.3 | 186 | 1 |  |  | definition | structural |  |
| 1.3 | 188 | 1 |  |  | definition | structural |  |
| 1.3 | 188 | 3 |  |  | definition | structural |  |
| 1.3 | 188 | 5 |  |  | definition | structural |  |
| 1.3 | 189 | 28 | 28 | results/claims-dossiers/07-detection/ANALYSIS.md:66 | match | value in assigned source |  |
| 1.3 | 190 | 1.00 |  |  | definition | structural |  |
| 1.3 | 191 | 5 |  |  | definition | structural |  |
| 1.3 | 191 | 4 |  |  | definition | structural |  |
| 1.3 | 191 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 191 | 95% |  |  | definition | structural |  |
| 1.3 | 191 | 2,000 |  |  | definition | structural |  |
| 1.3 | 192 | 2.8 |  |  | definition | structural |  |
| 1.3 | 193 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 1.3 | 198 | 35 | 35 | results/claims-dossiers/MASTER_CLAIMS.md:177 | match | value in assigned source |  |
| 1.3 | 198 | 22 | 22 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 1.3 | 198 | 288 | 288 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value in assigned source |  |
| 1.3 | 198 | 236 | 236 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value in assigned source |  |
| 1.3 | 202 | 1.00 |  |  | definition | structural |  |
| 1.3 | 202 | 5.00 |  |  | definition | structural |  |
| 1.3 | 202 | 2.31 | 2.31 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value in assigned source |  |
| 1.3 | 202 | 1.64 | 1.64 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value in assigned source |  |
| 1.3 | 202 | 2.35 | 2.35 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value in assigned source |  |
| 1.3 | 202 | 1.49 | 1.49 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value in assigned source |  |
| 1.3 | 203 | 0.65 | 0.65 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 203 | 0.32 | 0.32 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.3 | 203 | 0.68 | 68% | results/claims-dossiers/MASTER_CLAIMS.md:120 | match | value in assigned source |  |
| 1.3 | 203 | 0.24 | 0.24 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 1.3 | 204 | 0.85 | 0.85 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 1.3 | 204 | 0.48 | 0.48 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.3 | 204 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 1.3 | 204 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 205 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 1.3 | 205 | 0.52 | 0.52 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 1.3 | 205 | -0.13 | 0.13 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 205 | -0.23 | 0.23 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 205 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 205 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 1.3 | 205 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 1.3 | 205 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 205 | -0.08 | 0.08 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 1.3 | 205 | +0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 1.3 | 206 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 1.3 | 206 | 0.28 | 0.28 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 1.3 | 206 | +0.14 | 0.14 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 206 | +0.05 | 0.05 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 206 | +0.24 | 0.24 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value + CI on one source row |  |
| 1.3 | 206 | 0.44 | 44% | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 1.3 | 206 | 0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 206 | +0.08 | 0.08 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 1.3 | 206 | +0.04 | 4% | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 1.3 | 206 | +0.13 | 0.13 | results/claims-dossiers/07-detection/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 1.3 | 212 | 1.00 |  |  | definition | structural |  |
| 1.3 | 212 | 5.00 |  |  | definition | structural |  |
| 1.3 | 212 | 0.01 |  |  | definition | structural |  |
| 1.3 | 213 | 0 |  |  | definition | structural |  |
| 1.3 | 213 | 1 |  |  | definition | structural |  |
| 1.3 | 214 | 1.00 |  |  | definition | structural |  |
| 1.3 | 215 | 1.00 |  |  | definition | structural |  |
| 1.3 | 220 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 220 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.3 | 220 | 1.00 |  |  | definition | structural |  |
| 1.3 | 220 | 1.00 |  |  | definition | structural |  |
| 1.3 | 220 | 40 | 40 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.3 | 220 | 252 | 252 | results/claims-dossiers/07-detection/ANALYSIS.md:73 | match | value in assigned source |  |
| 1.3 | 220 | 44 | 44 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 1.3 | 220 | -0.01 | 0.01 | results/claims-dossiers/07-detection/ANALYSIS.md:73 | match | hand-checked | csv row O-B (252 games, 44 risers) gives -0.013 [-0.117, +0.092]; MASTER_CLAIMS G-detect-text prints -0.02 [-0.12, +0.08] |
| 1.3 | 220 | -0.12 | 0.12 | results/claims-dossiers/07-detection/ANALYSIS.md:73 | match | value + CI on one source row |  |
| 1.3 | 220 | +0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:73 | match | value + CI on one source row |  |
| 1.3 | 220 | 0.8 |  |  | definition | structural |  |
| 1.3 | 220 | 2.31 | 2.31 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value in assigned source |  |
| 1.3 | 220 | 1.00 |  |  | definition | structural |  |
| 1.3 | 220 | 7 |  |  | definition | structural |  |
| 1.3 | 220 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 220 | 99.3% | 99.3% | results/claims-dossiers/07-detection/ANALYSIS.md:227 | match | value in assigned source |  |
| 1.3 | 220 | 1.00 |  |  | definition | structural |  |
| 1.3 | 220 | 1 |  |  | definition | structural |  |
| 1.3 | 220 | 0.85 | 0.85 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 1.3 | 220 | 2 |  |  | definition | structural |  |
| 1.3 | 220 | 3 |  |  | definition | structural |  |
| 1.3 | 222 | 1 |  |  | definition | structural |  |
| 1.3 | 222 | 5 |  |  | definition | structural |  |
| 1.3 | 222 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 1.3 | 222 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.3 | 222 | 0.48 | 0.48 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.3 | 222 | 35% | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 222 | 0.05 |  |  | definition | structural |  |
| 1.3 | 222 | 0.41 | 0.41 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 222 | 13,486 | 13,486 | results/claims-dossiers/11-fresh-discovery/ANALYSIS.md:76 | match | value in assigned source |  |
| 1.3 | 222 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 1.3 | 222 | 1 |  |  | definition | structural |  |
| 1.3 | 222 | 5 |  |  | definition | structural |  |
| 1.3 | 222 | 2.00 |  |  | definition | structural |  |
| 1.3 | 222 | 70% |  |  | definition | structural |  |
| 1.3 | 222 | 4 |  |  | definition | structural |  |
| 1.3 | 222 | 10 | 10 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 1.3 | 222 | 5 |  |  | definition | structural |  |
| 1.3 | 224 | 0.90 | 0.90 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | 0.84 | 0.84 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | 0.95 | 95% | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | -0.00 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 1.3 | 224 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.3 | 224 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.3 | 224 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.3 | 230 | 0.01 |  |  | definition | structural |  |
| 1.3 | 231 | 1.00 |  |  | definition | structural |  |
| 1.3 | 232 | 3.00 |  |  | definition | structural |  |
| 1.3 | 232 | 1 |  |  | definition | structural |  |
| 1.3 | 234 | 1.00 |  |  | definition | structural |  |
| 1.3 | 235 | 5 |  |  | definition | structural |  |
| 1.4 | 240 | 1.4 |  |  | definition (section id) | structural |  |
| 1.4 | 242 | 1.4 | 1.4 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.4 | 244 | 0.65 | 0.65 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.4 | 244 | 0.71 | 71% | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value in assigned source |  |
| 1.4 | 244 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.4 | 244 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.4 | 244 | 0.23 | 0.23 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 0.20 | 20% | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 0.26 | 0.26 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 0.25 | 0.25 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 0.21 | 0.21 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 0.28 | 0.28 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 1.4 | 244 | 720 | 720 | results/claims-dossiers/07-detection/ANALYSIS.md:3 | match | value in assigned source |  |
| 1.4 | 244 | 1.3 |  |  | definition (cross-reference) | structural |  |
| 1.5 | 259 | 1.5 |  |  | definition (section id) | structural |  |
| 1.5 | 259 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.5 | 259 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.5 | 259 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 259 | -0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 259 | -0.32 | 0.32 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.5 | 259 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 261 | 1.5 | 1.5 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.5 | 263 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.5 | 263 | 0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value + CI on one source row |  |
| 1.5 | 263 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.5 | 263 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 263 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.5 | 263 | 0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 1.5 | 263 | 0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.5 | 263 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 263 | 0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 263 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 263 | 0 |  |  | definition | structural |  |
| 1.5 | 263 | ±0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.5 | 263 | 0.32 | 0.32 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.5 | 263 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 263 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 263 | 0.003 | 0.003 | results/claims-dossiers/MASTER_CLAIMS.md:109 | match | value in assigned source |  |
| 1.5 | 263 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.5 | 263 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.5 | 263 | 5 |  |  | definition | structural |  |
| 1.5 | 263 | -0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 1.5 | 263 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 263 | 5 |  |  | definition | structural |  |
| 1.5 | 263 | 1 |  |  | definition | structural |  |
| 1.5 | 263 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 1.5 | 263 | 0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 1.5 | 263 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 1.5 | 265 | 1.5 | 1.5 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.5 | 265 | 95% |  |  | definition | structural |  |
| 1.5 | 265 | 2.1 | 2.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 1.5 | 267 | 95% |  |  | definition | structural |  |
| 1.5 | 267 | 95% |  |  | definition | structural |  |
| 1.5 | 269 | -0.56 | 0.56 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.64 | 0.64 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.38 | 0.38 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.74 | 0.74 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.82 | 0.82 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.63 | 0.63 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.55 | 0.55 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.67 | 0.67 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.44 | 44% | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | +0.14 | 0.14 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | -0.02 | 0.020 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | +0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | +0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:68 | match | value + CI on one source row |  |
| 1.5 | 269 | +0.21 | 0.21 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | +0.38 | 0.38 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 1.5 | 269 | 1.00 |  |  | definition | structural |  |
| 1.5 | 269 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 269 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 269 | 70 | 70 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 269 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 270 | -0.30 | 0.30 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.43 | 0.43 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.22 | 0.22 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.09 | 0.09 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.40 | 0.40 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.55 | 0.55 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.51 | 0.51 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | -0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | +0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 1.5 | 270 | +0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | +0.05 | 0.05 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | +0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 1.5 | 270 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 270 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 270 | ±0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 1.5 | 270 | 2.1 |  |  | definition (cross-reference) | structural |  |
| 1.5 | 271 | 50 | 50 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:38 | match | value in assigned source |  |
| 1.5 | 271 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.51 | 0.51 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.23 | 0.23 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.32 | 0.32 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.46 | 0.46 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | -0.64 | 0.64 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | -0.27 | 0.27 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.49 | 0.49 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.5 | 271 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 1.5 | 271 | +0.20 | 20% | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | +0.06 | 0.060 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | +0.33 | 0.33 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | +0.20 | 20% | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | +0.08 | 0.08 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:362 | rounding | value + CI on one source row |  |
| 1.5 | 271 | +0.33 | 0.33 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 1.5 | 271 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 271 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 271 | 0.003 | 0.003 | results/claims-dossiers/MASTER_CLAIMS.md:109 | match | value in assigned source |  |
| 1.5 | 271 | 0.002 | 0.002 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 1.5 | 271 | 50 | 50 | results/claims-dossiers/05-moral-primes/ANALYSIS.md:38 | match | value in assigned source |  |
| 1.5 | 272 | 1.00 |  |  | definition | structural |  |
| 1.5 | 272 | 1.05 | 1.05 | results/claims-dossiers/MASTER_CLAIMS.md:152 | match | value in assigned source |  |
| 1.5 | 272 | -0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.36 | 0.36 | results/claims-dossiers/06-five-tick-start/ANALYSIS.md:44 | rounding | value + CI on one source row |  |
| 1.5 | 272 | -0.53 | 53% | results/claims-dossiers/06-five-tick-start/ANALYSIS.md:44 | rounding | value + CI on one source row |  |
| 1.5 | 272 | -0.16 | 0.16 | results/claims-dossiers/06-five-tick-start/ANALYSIS.md:44 | rounding | value + CI on one source row |  |
| 1.5 | 272 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:118 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:118 | match | value + CI on one source row |  |
| 1.5 | 272 | +0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:118 | match | value + CI on one source row |  |
| 1.5 | 272 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 272 | 0.020 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | hand-checked | dossier 06 Holm 0.0201; MASTER_CLAIMS G-5tick prints Holm 0.018 (family 15): source conflict, lead to choose |
| 1.5 | 272 | -0.25 | 0.25 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.40 | 0.40 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 272 | -0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value + CI on one source row |  |
| 1.5 | 273 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.26 | 0.26 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.42 | 0.42 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.27 | 0.27 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.12 | -0.1149 (hi) | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:215 | **MISMATCH** | hand-checked against full-precision csv | double rounding of -0.115; correct -0.11 |
| 1.5 | 273 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 1.5 | 273 | 3 |  |  | definition | structural |  |
| 1.5 | 273 | 0.022 | 0.022 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 1.5 | 273 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.5 | 273 | -0.12 | 0.12 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 1.5 | 273 | +0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 1.5 | 274 | 5 |  |  | definition | structural |  |
| 1.5 | 274 | 1 |  |  | definition | structural |  |
| 1.5 | 274 | 2,000 |  |  | definition | structural |  |
| 1.5 | 274 | 100 |  |  | definition | structural |  |
| 1.5 | 274 | -0.19 | 0.19 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.31 | 0.31 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.07 | 0.07 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.15 | 0.15 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.29 | 0.29 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.02 | 0.020 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.44 | 44% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | 0.008 | 0.008 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.5 | 274 | -0.19 | 0.19 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | 0.060 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.5 | 274 | -0.01 | 0.01 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.11 | 0.11 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | +0.10 | 0.10 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.08 | 0.08 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.21 | 0.21 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | +0.04 | 4% | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 274 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 1.5 | 274 | +0.04 | 4% | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 1.5 | 274 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:87 | rounding | value + CI on one source row |  |
| 1.5 | 274 | +0.10 | 0.10 | results/claims-dossiers/03-penalty-and-thinking/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 1.5 | 274 | 0.58 | 0.58 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.5 | 275 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.25 | 0.25 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.08 | 0.08 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.28 | 0.28 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:308 | rounding | value + CI on one source row |  |
| 1.5 | 275 | +0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:308 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.16 | 0.16 | results/claims-dossiers/06-five-tick-start/ANALYSIS.md:467 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.28 | 0.28 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:308 | rounding | value + CI on one source row |  |
| 1.5 | 275 | -0.05 | -0.0447 (ci_hi) | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:6 | **MISMATCH** | hand-checked against full-precision csv | double rounding of -0.045; correct -0.04 (as in Section 3.4) |
| 1.5 | 275 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 1.5 | 275 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 1.5 | 275 | 0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 1.5 | 275 | 1.0 |  |  | definition | structural |  |
| 1.5 | 275 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 1.5 | 281 | 1.00 |  |  | definition | structural |  |
| 1.5 | 281 | 5.00 |  |  | definition | structural |  |
| 1.5 | 281 | 0.01 |  |  | definition | structural |  |
| 1.5 | 282 | 1.00 |  |  | definition | structural |  |
| 1.5 | 282 | 3.00 |  |  | definition | structural |  |
| 1.5 | 282 | 1.00 |  |  | definition | structural |  |
| 1.5 | 282 | 3.00 |  |  | definition | structural |  |
| 1.5 | 283 | - 1.00 |  |  | definition | structural |  |
| 1.5 | 283 | 2.00 |  |  | definition | structural |  |
| 1.5 | 283 | 0 |  |  | definition | structural |  |
| 1.5 | 283 | 1.00 |  |  | definition | structural |  |
| 1.5 | 283 | 1 |  |  | definition | structural |  |
| 1.5 | 283 | 3.00 |  |  | definition | structural |  |
| 1.5 | 285 | 1.00 |  |  | definition | structural |  |
| 1.5 | 287 | 100 |  |  | definition | structural |  |
| 1.5 | 287 | 500 |  |  | definition | structural |  |
| 1.5 | 287 | 2,000 |  |  | definition | structural |  |
| 1.5 | 289 | 1.00 |  |  | definition | structural |  |
| 1.5 | 289 | 1.50 |  |  | definition | structural |  |
| 1.5 | 289 | 4.00 |  |  | definition | structural |  |
| 1.5 | 289 | 2.49 |  |  | definition | structural |  |
| 1.5 | 289 | 2.09 |  |  | definition | structural |  |
| 1.5 | 290 | 95% |  |  | definition | structural |  |
| 1.5 | 293 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:53 | match | value in assigned source |  |
| 1.5 | 293 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 1.5 | 297 | 09 | 09 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 1.5 | 297 | 2.1 |  |  | definition (cross-reference) | structural |  |
| 1.5 | 299 | -0.63 | 0.63 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.5 | 299 | -0.51 | 0.51 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.5 | 299 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 1.5 | 299 | -0.32 | 0.32 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 1.5 | 299 | 5 |  |  | definition | structural |  |
| 1.5 | 299 | -0.55 | 0.55 | results/claims-dossiers/MASTER_CLAIMS.md:110 | match | value in assigned source |  |
| 1.5 | 299 | +0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 299 | -0.07 | 0.07 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 299 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 1.5 | 307 | 100 |  |  | definition | structural |  |
| 1.5 | 307 | 1 |  |  | definition | structural |  |
| 1.5 | 307 | 5.00 |  |  | definition | structural |  |
| 1.5 | 307 | - 1.00 |  |  | definition | structural |  |
| 1.5 | 307 | 30% |  |  | definition | structural |  |
| 1.5 | 307 | 70% |  |  | definition | structural |  |
| 2.1 | 315 | 2.1 |  |  | definition (section id) | structural |  |
| 2.1 | 315 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 2.1 | 315 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 2.1 | 315 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 317 | 2.1 | 2.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 2.1 | 319 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 2.1 | 319 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.1 | 319 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.35 | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value + CI on one source row |  |
| 2.1 | 319 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 319 | 0.40 | 0.40 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 319 | 0.47 | 0.47 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 319 | 0.24 | 0.24 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 319 | 0.28 | 0.28 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 319 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 319 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 319 | 1 |  |  | definition | structural |  |
| 2.1 | 319 | 5 |  |  | definition | structural |  |
| 2.1 | 319 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 319 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 2.1 | 319 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 2.1 | 319 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 2.1 | 319 | -0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 2.1 | 319 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 319 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 319 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 2.1 | 319 | 37 | 37 | results/claims-dossiers/MASTER_CLAIMS.md:179 | match | value in assigned source |  |
| 2.1 | 319 | 0.0001 | 0.0001 | results/claims-dossiers/MASTER_CLAIMS.md:179 | match | value in assigned source |  |
| 2.1 | 319 | 31 | 31 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 2.1 | 319 | +0.79 | 0.79 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 2.1 | 319 | +0.58 | 0.58 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 2.1 | 321 | 2.1 | 2.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 2.1 | 321 | 95% |  |  | definition | structural |  |
| 2.1 | 323 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.1 | 323 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 323 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 323 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.1 | 325 | -0.60 | 0.60 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.87 | 0.87 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.32 | 0.32 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.44 | 44% | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.69 | 0.69 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 325 | +0.41 | 0.41 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 2.1 | 325 | +0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 325 | -0.23 | 0.23 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 325 | +0.23 | 0.23 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.30 | 0.30 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.43 | 0.43 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 326 | 0.27 | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 2.1 | 326 | 0.57 | 0.57 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value in assigned source |  |
| 2.1 | 326 | -0.22 | 0.22 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.09 | 0.09 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 326 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 2.1 | 326 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 2.1 | 326 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.19 | 0.19 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.06 | 0.060 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.31 | 0.31 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.23 | 0.23 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.10 | 0.10 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.35 | 0.35 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 2.1 | 326 | -0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value + CI on one source row |  |
| 2.1 | 326 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 326 | 0.62 | 0.62 | results/claims-dossiers/MASTER_CLAIMS.md:118 | match | value in assigned source |  |
| 2.1 | 326 | 0.61 | 0.61 | results/claims-dossiers/01-focal-points/ANALYSIS.md:114 | match | value in assigned source |  |
| 2.1 | 327 | -0.40 | 0.40 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.55 | 0.55 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.51 | 0.51 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.19 | 0.19 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 327 | +0.25 |  |  | definition | structural |  |
| 2.1 | 327 | +0.20 | 20% | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:73 | rounding | value + CI on one source row |  |
| 2.1 | 327 | +0.05 | 0.05 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:73 | rounding | value + CI on one source row |  |
| 2.1 | 327 | +0.35 | 0.35 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:73 | rounding | value + CI on one source row |  |
| 2.1 | 327 | +0.30 | 0.30 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 327 | +0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 327 | +0.46 | 0.46 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.04 | 4% | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 327 | -0.16 | 0.16 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 327 | +0.06 | 0.060 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.03 | 0.03 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.27 | 0.27 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.37 | 0.37 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.17 | 0.17 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.24 | 0.24 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.26 | 0.26 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.34 | 0.34 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 328 | -0.18 | 0.18 | results/claims-dossiers/01-focal-points/ANALYSIS.md:561 | match | value + CI on one source row |  |
| 2.1 | 329 | -0.01 | 0.01 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 329 | -0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.13 | 0.13 | results/claims-dossiers/01-focal-points/ANALYSIS.md:66 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.15 | 0.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.05 | 0.05 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.25 | 0.25 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.21 | 0.21 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.11 | 0.11 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.02 | 0.020 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 2.1 | 329 | +0.21 | 0.21 | results/claims-dossiers/01-focal-points/ANALYSIS.md:178 | match | value + CI on one source row |  |
| 2.1 | 330 | 0.05 |  |  | definition | structural |  |
| 2.1 | 330 | 5 |  |  | definition | structural |  |
| 2.1 | 330 | 0.05 |  |  | definition | structural |  |
| 2.1 | 330 | 0.020 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 330 | 0.016 | 0.016 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 330 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 2.1 | 338 | 2 |  |  | definition | structural |  |
| 2.1 | 338 | 1.00 |  |  | definition | structural |  |
| 2.1 | 339 | 1.00 |  |  | definition | structural |  |
| 2.1 | 341 | 7 |  |  | definition | structural |  |
| 2.1 | 341 | 13 | 13 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 2.1 | 341 | 107 | 107 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 2.1 | 342 | ±0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 2.1 | 343 | 2.8 |  |  | definition | structural |  |
| 2.1 | 348 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 2.1 | 348 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 348 | -0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:179 | match | value + CI on one source row |  |
| 2.1 | 348 | -0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:179 | match | value + CI on one source row |  |
| 2.1 | 348 | -0.07 | 0.07 | results/claims-dossiers/MASTER_CLAIMS.md:179 | match | value + CI on one source row |  |
| 2.1 | 348 | +0.58 | 0.58 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 2.1 | 348 | +0.66 | 0.66 | results/claims-dossiers/MASTER_CLAIMS.md:167 | match | value in assigned source |  |
| 2.1 | 348 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 350 | -0.63 | 0.63 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 2.1 | 350 | -0.51 | 0.51 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 2.1 | 350 | +0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 350 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 350 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 2.1 | 350 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 2.1 | 350 | +0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 350 | +0.40 | 0.40 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.1 | 357 | 2.09 |  |  | definition | structural |  |
| 2.1 | 357 | 0.546 |  |  | definition | structural |  |
| 2.1 | 358 | 0.01 |  |  | definition | structural |  |
| 2.1 | 358 | 0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.1 | 358 | 2.48 | 2.48 | results/claims-dossiers/01-focal-points/ANALYSIS.md:21 | match | value in assigned source |  |
| 2.1 | 358 | 2.47 | 2.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:21 | match | value in assigned source |  |
| 2.1 | 358 | 2.49 |  |  | definition | structural |  |
| 2.1 | 358 | 2.50 |  |  | definition | structural |  |
| 2.1 | 360 | 1 |  |  | definition | structural |  |
| 2.1 | 360 | 5 |  |  | definition | structural |  |
| 2.1 | 362 | -1 |  |  | definition | structural |  |
| 2.1 | 362 | +1 |  |  | definition | structural |  |
| 2.2 | 367 | 2.2 |  |  | definition (section id) | structural |  |
| 2.2 | 367 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.2 | 367 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.2 | 367 | 0 |  |  | definition | structural |  |
| 2.2 | 369 | 2.2 | 2.20 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 2.2 | 371 | 0.50 | 0.50 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 371 | 4 |  |  | definition | structural |  |
| 2.2 | 371 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.67 | 0.67 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.93 | 0.93 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 57 | 57 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 2.2 | 371 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.2 | 371 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.94 | 94% | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 2.2 | 371 | 0.65 | 0.65 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.50 | 0.50 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.79 | 0.79 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.71 | 71% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.66 | 0.66 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.75 | 75% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 371 | +0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 371 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 371 | +0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 371 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 371 | 1.00 |  |  | definition | structural |  |
| 2.2 | 371 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 2.2 | 371 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 2.2 | 371 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.2 | 371 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.2 | 371 | 99% | 0.99 | results/claims-dossiers/07-detection/ANALYSIS.md:106 | match | value in assigned source |  |
| 2.2 | 371 | 1.00 |  |  | definition | structural |  |
| 2.2 | 371 | 0.23 | 0.23 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.20 | 20% | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.26 | 0.26 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.25 | 0.25 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.21 | 0.21 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | 0.28 | 0.28 | results/claims-dossiers/07-detection/ANALYSIS.md:286 | match | value + CI on one source row |  |
| 2.2 | 371 | +0.46 | 0.46 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value in assigned source |  |
| 2.2 | 371 | 40 | 40 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 2.2 | 371 | +0.05 | 0.05 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.2 | 371 | -0.25 | 0.25 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.2 | 371 | +0.33 | 0.33 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.2 | 371 | 35 | 35 | results/claims-dossiers/MASTER_CLAIMS.md:177 | match | value in assigned source |  |
| 2.2 | 373 | 2.2 | 2.20 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 2.2 | 375 | 1 |  |  | definition | structural |  |
| 2.2 | 375 | 3 |  |  | definition | structural |  |
| 2.2 | 375 | 57 | 57 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 2.2 | 375 | 0.61 | 0.61 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value in assigned source |  |
| 2.2 | 375 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 2.2 | 375 | 0.55 | 0.55 | results/claims-dossiers/MASTER_CLAIMS.md:110 | match | value in assigned source |  |
| 2.2 | 377 | 0.65 | 0.65 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 377 | 0.50 | 0.50 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 377 | 0.79 | 0.79 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 377 | 0.71 | 71% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 377 | 0.66 | 0.66 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 377 | 0.75 | 75% | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.67 | 0.67 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.93 | 0.93 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.87 | 0.87 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 378 | 0.94 | 94% | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.84 | 0.84 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.72 | 0.72 | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.94 | 94% | results/claims-dossiers/07-detection/ANALYSIS.md:107 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.90 | 0.90 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.86 | 0.86 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 379 | 0.93 | 0.93 | results/claims-dossiers/07-detection/ANALYSIS.md:109 | match | value + CI on one source row |  |
| 2.2 | 380 | +0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 380 | -0.03 | 0.03 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 380 | +0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 380 | 0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 380 | 1.00 |  |  | definition | structural |  |
| 2.2 | 380 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 380 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 380 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value + CI on one source row |  |
| 2.2 | 380 | 0.02 | 0.020 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 380 | 1.00 |  |  | definition | structural |  |
| 2.2 | 381 | +0.19 | 0.19 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 381 | +0.06 | 0.060 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 381 | +0.34 | 0.34 | results/claims-dossiers/07-detection/ANALYSIS.md:146 | match | value + CI on one source row |  |
| 2.2 | 381 | 0.063 | 0.063 | results/claims-dossiers/07-detection/ANALYSIS.md:144 | match | value in assigned source |  |
| 2.2 | 381 | +0.20 | 20% | results/claims-dossiers/07-detection/ANALYSIS.md:148 | match | value + CI on one source row |  |
| 2.2 | 381 | +0.14 | 0.14 | results/claims-dossiers/07-detection/ANALYSIS.md:148 | match | value + CI on one source row |  |
| 2.2 | 381 | +0.25 | 0.25 | results/claims-dossiers/07-detection/ANALYSIS.md:148 | match | value + CI on one source row |  |
| 2.2 | 381 | 0.006 | 0.006 | results/claims-dossiers/MASTER_CLAIMS.md:140 | match | value in assigned source |  |
| 2.2 | 382 | 0.29 | 0.29 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 2.2 | 382 | 0.11 | 0.11 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 2.2 | 382 | 0.46 | 0.46 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 2.2 | 382 | 0.29 | 0.29 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 2.2 | 382 | 0.21 | 0.2047 (recall_lo) | results/claims-dossiers/07-detection/out/detector_auc.csv:27 | **MISMATCH** | hand-checked against full-precision csv | dossier text prints 0.21; csv value rounds to 0.20 (as in Section 1.3) |
| 2.2 | 382 | 0.37 | 0.37 | results/claims-dossiers/07-detection/ANALYSIS.md:188 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.71 | 71% | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.58 | 0.58 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.86 | 0.86 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.18 | 0.18 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.05 | 0.05 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.35 | 0.35 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.85 | 0.85 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.79 | 0.79 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.89 | 0.89 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.14 | 0.14 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.09 | 0.09 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 383 | 0.18 | 0.18 | results/claims-dossiers/07-detection/ANALYSIS.md:138 | match | value + CI on one source row |  |
| 2.2 | 391 | 0.5 |  |  | definition | structural |  |
| 2.2 | 391 | 1.0 |  |  | definition | structural |  |
| 2.2 | 392 | 4 |  |  | definition | structural |  |
| 2.2 | 392 | 0.50 |  |  | definition | structural |  |
| 2.2 | 392 | 2.00 |  |  | definition | structural |  |
| 2.2 | 392 | - 1 |  |  | definition | structural |  |
| 2.2 | 392 | 2 |  |  | definition | structural |  |
| 2.2 | 392 | 0 |  |  | definition | structural |  |
| 2.2 | 392 | 1.00 |  |  | definition | structural |  |
| 2.2 | 392 | 1 |  |  | definition | structural |  |
| 2.2 | 392 | 3.00 |  |  | definition | structural |  |
| 2.2 | 394 | 1 |  |  | definition | structural |  |
| 2.2 | 394 | 3 |  |  | definition | structural |  |
| 2.2 | 395 | 1 |  |  | definition | structural |  |
| 2.2 | 395 | 3 |  |  | definition | structural |  |
| 2.2 | 395 | 0.498 | 0.498 | results/claims-dossiers/07-detection/ANALYSIS.md:24 | match | value in assigned source |  |
| 2.2 | 396 | 2,000 |  |  | definition | structural |  |
| 2.2 | 397 | 2.8 |  |  | definition | structural |  |
| 2.2 | 398 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 2.2 | 398 | 07 | 7 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.2 | 400 | 1 |  |  | definition | structural |  |
| 2.2 | 400 | 3 |  |  | definition | structural |  |
| 2.2 | 400 | 5 |  |  | definition | structural |  |
| 2.2 | 404 | +0.01 |  |  | definition | structural |  |
| 2.2 | 404 | +0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 2.2 | 404 | 7 |  |  | definition | structural |  |
| 2.2 | 404 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.2 | 404 | 2.00 |  |  | definition | structural |  |
| 2.2 | 404 | 99.3% | 99.3% | results/claims-dossiers/07-detection/ANALYSIS.md:227 | match | value in assigned source |  |
| 2.2 | 404 | 1.00 |  |  | definition | structural |  |
| 2.2 | 404 | +0.003 | 0.003 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | -0.005 | 0.005 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | +0.012 | 0.012 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | +0.00 | 0 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | -0.05 | 0.05 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | +0.06 | 0.060 | results/oss/ad-hoc/detection-transfer/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 2.2 | 404 | -0.065 | 0.06506789608942444 | results/oss/ad-hoc/detection-transfer/detection_transfer.csv:82 | rounding | value + CI on one source row |  |
| 2.2 | 404 | -0.114 | 0.11440677966101695 | results/oss/ad-hoc/detection-transfer/detection_transfer.csv:82 | rounding | value + CI on one source row |  |
| 2.2 | 404 | -0.023 | 0.023 | results/oss/ad-hoc/detection-transfer/detection_transfer.csv:82 | rounding | value + CI on one source row |  |
| 2.2 | 404 | 524 | 524 | results/claims-dossiers/MASTER_CLAIMS.md:127 | match | value in assigned source |  |
| 2.2 | 406 | 0.90 | 0.90 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.2 | 406 | -0.00 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 2.2 | 406 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 2.2 | 406 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 2.2 | 406 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:126 | match | value + CI on one source row |  |
| 2.2 | 406 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 2.2 | 406 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 2.2 | 406 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.2 | 406 | 2% | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.2 | 414 | 1.00 |  |  | definition | structural |  |
| 2.2 | 414 | 3 |  |  | definition | structural |  |
| 2.2 | 415 | 0.01 |  |  | definition | structural |  |
| 2.2 | 416 | 1 |  |  | definition | structural |  |
| 2.2 | 416 | 5 |  |  | definition | structural |  |
| 2.2 | 418 | 0 |  |  | definition | structural |  |
| 2.3 | 422 | 2.3 |  |  | definition (section id) | structural |  |
| 2.3 | 422 | 0.61 | 0.610 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:75 | match | value in assigned source |  |
| 2.3 | 424 | 2.3 | 2.3 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 2.3 | 426 | 3 |  |  | definition | structural |  |
| 2.3 | 426 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 426 | 0.61 | 0.610 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 0.52 | 0.52 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 0.68 | 68% | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 426 | -0.80 | 0.80 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 426 | -0.88 | 0.88 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 426 | -0.69 | 0.69 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 426 | +0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 0.05 | 0.05 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.23 | 0.23 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.74 | 0.74 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.72 | 0.72 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.75 | 75% | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 2.3 | 426 | 0.008 | 0.008 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 2.3 | 426 | 1 |  |  | definition | structural |  |
| 2.3 | 426 | 99 | 99 | results/claims-dossiers/MASTER_CLAIMS.md:99 | match | value in assigned source |  |
| 2.3 | 426 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 426 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| 2.3 | 426 | +0.05 | 0.05 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 426 | +0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| 2.3 | 426 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 426 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.3 | 426 | 1 |  |  | definition | structural |  |
| 2.3 | 426 | 0.20 | 20% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 2.3 | 426 | 1 |  |  | definition | structural |  |
| 2.3 | 426 | 5 |  |  | definition | structural |  |
| 2.3 | 428 | 2.3 | 2.3 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 2.3 | 428 | 3 |  |  | definition | structural |  |
| 2.3 | 428 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 430 | 95% |  |  | definition | structural |  |
| 2.3 | 430 | 95% |  |  | definition | structural |  |
| 2.3 | 432 | 1.00 |  |  | definition | structural |  |
| 2.3 | 432 | 5.00 |  |  | definition | structural |  |
| 2.3 | 432 | 1.011 | 1.011 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:57 | match | value in assigned source |  |
| 2.3 | 432 | 2.225 | 2.2255085 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | **MISMATCH** | hand-checked against full-precision csv | correct 2.226 (dossier 06 prints 2.226) |
| 2.3 | 432 | 2.489 | 2.489 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:58 | match | value in assigned source |  |
| 2.3 | 432 | -1.21 | 1.21 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 432 | -1.36 | 1.36 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 432 | -1.04 | 1.04 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 432 | +0.26 | 0.26 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 432 | +0.12 | 0.12 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 432 | +0.43 | 0.43 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 433 | 0 |  |  | definition | structural |  |
| 2.3 | 433 | 1 |  |  | definition | structural |  |
| 2.3 | 433 | 0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 2.3 | 433 | 0.613 | 0.613 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:59 | match | value in assigned source |  |
| 2.3 | 433 | 0.744 | 0.744 | results/claims-dossiers/MASTER_CLAIMS.md:98 | match | value in assigned source |  |
| 2.3 | 433 | -0.61 | 0.610 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 433 | -0.68 | 68% | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 433 | -0.52 | 0.52 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 433 | +0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 433 | +0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 433 | +0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 2.3 | 434 | 0.007 | 0.007 | results/claims-dossiers/MASTER_CLAIMS.md:78 | match | value in assigned source |  |
| 2.3 | 434 | 0.804 | 0.804 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:59 | match | value in assigned source |  |
| 2.3 | 434 | 0.932 | 0.932 | results/claims-dossiers/MASTER_CLAIMS.md:98 | match | value in assigned source |  |
| 2.3 | 434 | -0.80 | 0.80 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 434 | -0.88 | 0.88 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 434 | -0.69 | 0.69 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 434 | +0.13 | 0.13 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 434 | +0.05 | 0.05 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 434 | +0.23 | 0.23 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 435 | 0.990 | 0.990 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:57 | match | value in assigned source |  |
| 2.3 | 435 | 0.440 | 44% | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 2.3 | 435 | 0.249 | 0.249 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 2.3 | 435 | +0.55 | 0.55 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 435 | +0.46 | 0.46 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 435 | +0.64 | 0.64 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 435 | -0.19 | 0.19 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 435 | -0.30 | 0.30 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 435 | -0.08 | 0.08 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 436 | 0.000 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 2.3 | 436 | 0.376 | 0.376 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:59 | match | value in assigned source |  |
| 2.3 | 436 | 0.607 | 0.607 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:58 | match | value in assigned source |  |
| 2.3 | 436 | -0.38 | 0.38 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 436 | -0.48 | 0.48 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 436 | -0.29 | 0.29 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:81 | match | value + CI on one source row |  |
| 2.3 | 436 | +0.23 | 0.23 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 436 | +0.08 | 0.08 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 436 | +0.37 | 0.37 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:82 | match | value + CI on one source row |  |
| 2.3 | 444 | 1.00 |  |  | definition | structural |  |
| 2.3 | 445 | 3 |  |  | definition | structural |  |
| 2.3 | 446 | 2.49 |  |  | definition | structural |  |
| 2.3 | 446 | 3.00 |  |  | definition | structural |  |
| 2.3 | 447 | 1.00 |  |  | definition | structural |  |
| 2.3 | 447 | 5.00 |  |  | definition | structural |  |
| 2.3 | 448 | - 1 |  |  | definition | structural |  |
| 2.3 | 448 | 2 |  |  | definition | structural |  |
| 2.3 | 448 | 0 |  |  | definition | structural |  |
| 2.3 | 448 | 1.00 |  |  | definition | structural |  |
| 2.3 | 448 | 1 |  |  | definition | structural |  |
| 2.3 | 448 | 3.00 |  |  | definition | structural |  |
| 2.3 | 449 | 0 |  |  | definition | structural |  |
| 2.3 | 449 | 1 |  |  | definition | structural |  |
| 2.3 | 450 | 1.00 |  |  | definition | structural |  |
| 2.3 | 451 | 1.00 |  |  | definition | structural |  |
| 2.3 | 452 | 95% |  |  | definition | structural |  |
| 2.3 | 452 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 452 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 2.3 | 452 | 3 |  |  | definition | structural |  |
| 2.3 | 452 | 5 |  |  | definition | structural |  |
| 2.3 | 458 | 1 |  |  | definition | structural |  |
| 2.3 | 458 | 0.81 | 0.81 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.3 | 458 | 0.91 | 0.91 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.3 | 458 | 2.2 |  |  | definition (cross-reference) | structural |  |
| 2.3 | 458 | 2.60 |  |  | definition | structural |  |
| 2.3 | 458 | 0 |  |  | definition | structural |  |
| 2.3 | 458 | 60 | 60 | results/claims-dossiers/MASTER_CLAIMS.md:129 | match | value in assigned source |  |
| 2.3 | 458 | 2 |  |  | definition | structural |  |
| 2.3 | 458 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 458 | 2.31 | 2.31 | results/claims-dossiers/07-detection/ANALYSIS.md:80 | match | value in assigned source |  |
| 2.3 | 459 | 2 |  |  | definition | structural |  |
| 2.3 | 459 | 0.61 | 0.610 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 459 | 0.52 | 0.52 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 459 | 0.68 | 68% | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:3 | rounding | value + CI on one source row |  |
| 2.3 | 459 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 2.3 | 460 | 3 |  |  | definition | structural |  |
| 2.3 | 460 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.3 | 460 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 2.3 | 460 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| 2.3 | 460 | +0.05 | 0.05 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| 2.3 | 460 | +0.16 | 0.16 | results/claims-dossiers/MASTER_CLAIMS.md:99 | rounding | value + CI on one source row |  |
| 2.3 | 460 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 461 | 4 |  |  | definition | structural |  |
| 2.3 | 461 | 0 |  |  | definition | structural |  |
| 2.3 | 461 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 2.3 | 461 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 461 | 0.23 | 0.23 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 2.3 | 461 | 0.25 |  |  | definition | structural |  |
| 2.3 | 462 | 5 |  |  | definition | structural |  |
| 2.3 | 462 | 1.09 | 1.09 | results/claims-dossiers/MASTER_CLAIMS.md:152 | match | value in assigned source |  |
| 2.3 | 462 | 5 |  |  | definition | structural |  |
| 2.3 | 462 | 1.05 | 1.05 | results/claims-dossiers/MASTER_CLAIMS.md:152 | match | value in assigned source |  |
| 2.3 | 462 | +0.05 | 0.05 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.3 | 462 | -0.25 | 0.25 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.3 | 462 | +0.33 | 0.33 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value + CI on one source row |  |
| 2.3 | 462 | +0.62 | 0.62 | results/claims-dossiers/MASTER_CLAIMS.md:118 | match | value in assigned source |  |
| 2.3 | 463 | 6 |  |  | definition | structural |  |
| 2.3 | 463 | 31 | 31 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 2.3 | 463 | +0.58 | 0.58 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | 0.29 | 0.29 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | 0.76 | 0.76 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | +0.66 | 0.66 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | 0.41 | 0.41 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | 0.81 | 0.81 | results/claims-dossiers/10-temptation-ratings-and-self-reports/ANALYSIS.md:439 | match | value + CI on one source row |  |
| 2.3 | 463 | +0.79 | 0.79 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 2.3 | 463 | +0.85 | 0.85 | results/claims-dossiers/MASTER_CLAIMS.md:43 | match | value in assigned source |  |
| 2.3 | 463 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.3 | 464 | 7 |  |  | definition | structural |  |
| 2.3 | 464 | 0.71 | 71% | results/claims-dossiers/MASTER_CLAIMS.md:117 | match | value in assigned source |  |
| 2.3 | 464 | 0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 2.3 | 464 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 2.3 | 464 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.3 | 464 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 2.3 | 464 | 60% | 0.60 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 2.3 | 466 | 0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 2.3 | 466 | 0.744 | 0.744 | results/claims-dossiers/MASTER_CLAIMS.md:98 | match | value in assigned source |  |
| 2.3 | 466 | +0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 2.3 | 466 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:53 | match | value in assigned source |  |
| 2.3 | 466 | 1 |  |  | definition | structural |  |
| 2.3 | 466 | 5 |  |  | definition | structural |  |
| 2.3 | 466 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 468 | -0.77 | 0.77 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 2.3 | 468 | -0.84 | 0.84 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 2.3 | 468 | -0.69 | 0.69 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 2.3 | 468 | +0.72 | 0.72 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 2.3 | 468 | 1 |  |  | definition | structural |  |
| 2.3 | 468 | 5 |  |  | definition | structural |  |
| 2.3 | 468 | 1.00 |  |  | definition | structural |  |
| 2.3 | 468 | +0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.3 | 468 | +0.40 | 0.40 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 2.3 | 476 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 2.3 | 477 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 2.3 | 477 | 80% |  |  | definition | structural |  |
| 2.3 | 477 | 5% | 0.05 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 2.3 | 478 | 1 |  |  | definition | structural |  |
| 2.3 | 478 | 5 |  |  | definition | structural |  |
| 2.3 | 480 | 1 |  |  | definition | structural |  |
| 2.3 | 480 | 5 |  |  | definition | structural |  |
| 3.1 | 486 | 3.1 |  |  | definition (section id) | structural |  |
| 3.1 | 486 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.1 | 486 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.1 | 486 | 0 |  |  | definition | structural |  |
| 3.1 | 486 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.1 | 488 | 3.1 | 3.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.1 | 490 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | +0.25 | 0.25 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.36 | 0.36 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 490 | 0.009 | 0.009 | results/claims-dossiers/MASTER_CLAIMS.md:138 | match | value in assigned source |  |
| 3.1 | 490 | 0.39 | 0.39 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.48 | 0.48 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 3.1 | 490 | 0.008 | 0.008 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.1 | 490 | -0.38 | 0.38 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 3.1 | 490 | -0.47 | 0.47 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 3.1 | 490 | -0.29 | 0.29 | results/claims-dossiers/01-focal-points/ANALYSIS.md:69 | match | value + CI on one source row |  |
| 3.1 | 490 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 490 | -0.22 | 0.22 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 3.1 | 490 | -0.35 | 0.35 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 3.1 | 490 | -0.09 | 0.09 | results/claims-dossiers/01-focal-points/ANALYSIS.md:67 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value in assigned source |  |
| 3.1 | 490 | 0.28 | 0.28 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.1 | 490 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.00 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 3.1 | 490 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 490 | 0.30 | 0.30 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 3.1 | 490 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:98 | rounding | value + CI on one source row |  |
| 3.1 | 492 | 3.1 | 3.1 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.1 | 492 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 492 | 95% |  |  | definition | structural |  |
| 3.1 | 492 | 3 |  |  | definition | structural |  |
| 3.1 | 494 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 496 | 1.00 | 1.00 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:22 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 5.00 |  |  | definition | structural |  |
| 3.1 | 496 | 1.01 | 1.01 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:22 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 1.00 | 1.00 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:22 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 1.03 | 1.03 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:22 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 1.02 | 1.02 | results/claims-dossiers/01-focal-points/ANALYSIS.md:19 | match | value in assigned source |  |
| 3.1 | 496 | 1.78 | 1.7749585 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | **MISMATCH** | hand-checked against full-precision csv | correct 1.77; dossier 02 text and ad-hoc cells.csv (1.775) round twice |
| 3.1 | 496 | 1.59 | 1.5894533000000002 | results/oss/ad-hoc/penalty/cells.csv:17 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 1.96 | 1.9624856249999996 | results/oss/ad-hoc/penalty/cells.csv:17 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 2.15 | 2.15 | results/claims-dossiers/01-focal-points/ANALYSIS.md:764 | match | value in assigned source |  |
| 3.1 | 496 | 2.49 | 2.49 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:32 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 2.46 | 2.463777 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:32 | rounding | value + CI on one source row |  |
| 3.1 | 496 | 2.51 | 2.5050114999999997 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:32 | rounding | value + CI on one source row |  |
| 3.1 | 496 | +0.41 | 0.41 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 3.1 | 496 | +0.22 | 0.22 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 3.1 | 496 | +0.59 | 0.59 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:12 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0 |  |  | definition | structural |  |
| 3.1 | 497 | 1 |  |  | definition | structural |  |
| 3.1 | 497 | 0.005 | 0.005 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:8 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.000 | 0 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:8 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.016 | 0.016 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:8 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.008 | 0.008 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.1 | 497 | 0.39 | 0.39 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.29 | 0.29 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.48 | 0.48 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.57 | 0.57 | results/claims-dossiers/MASTER_CLAIMS.md:88 | match | value in assigned source |  |
| 3.1 | 497 | 0.74 | 0.74 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:33 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.73 | 0.73 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:33 | rounding | value + CI on one source row |  |
| 3.1 | 497 | 0.76 | 0.76 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:33 | rounding | value + CI on one source row |  |
| 3.1 | 497 | +0.21 | 0.21 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 497 | +0.11 | 0.11 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 497 | +0.29 | 0.29 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0 |  |  | definition | structural |  |
| 3.1 | 498 | 1 |  |  | definition | structural |  |
| 3.1 | 498 | 0.007 | 0.007 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.000 | 0 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.020 | 0.020 | results/claims-dossiers/01-focal-points/tables/quote_shares_by_cell.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.016 | 0.016 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.1 | 498 | 0.57 | 0.57 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.45 | 0.45 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.68 | 68% | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.77 | 0.77 | results/claims-dossiers/MASTER_CLAIMS.md:167 | match | value in assigned source |  |
| 3.1 | 498 | 0.93 | 0.93 | results/claims-dossiers/04-controls-and-reproducibility/g_ctl_contrasts.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.93 | 0.93 | results/claims-dossiers/04-controls-and-reproducibility/g_ctl_contrasts.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | 0.94 | 94% | results/claims-dossiers/04-controls-and-reproducibility/g_ctl_contrasts.csv:10 | rounding | value + CI on one source row |  |
| 3.1 | 498 | +0.25 | 0.25 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 498 | +0.13 | 0.13 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 498 | +0.36 | 0.36 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:14 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.99 | 0.99 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 3.1 | 499 | 0.97 | 0.97 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 3.1 | 499 | 1.00 | 1.00 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:113 | match | value + CI on one source row |  |
| 3.1 | 499 | 0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 3.1 | 499 | 0.68 | 68% | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.60 | 0.60 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.76 | 0.76 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.1 | 499 | 0.25 | 0.25 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:35 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.17 | 0.17 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:35 | rounding | value + CI on one source row |  |
| 3.1 | 499 | 0.33 | 0.33 | results/oss/trackm-neutral-2026-10-26/step4/data/fig_3_1.csv:35 | rounding | value + CI on one source row |  |
| 3.1 | 499 | -0.24 | 0.24 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 3.1 | 499 | -0.33 | 0.33 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 3.1 | 499 | -0.14 | 0.14 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:15 | rounding | value + CI on one source row |  |
| 3.1 | 500 | 0.00 | 0 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 3.1 | 500 | 0 |  |  | definition | structural |  |
| 3.1 | 500 | 0.46 | 0.46 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value in assigned source |  |
| 3.1 | 500 | 0.16 | 0.16 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 500 | 0.10 | 0.10 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 500 | 0.24 | 0.24 | results/claims-dossiers/02-communication-and-levels/tables/cell_levels.csv:5 | rounding | value + CI on one source row |  |
| 3.1 | 500 | 0.41 | 0.41 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.1 | 500 | 0.61 | 0.61 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 3.1 | 500 | 0.51 | 0.51 | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 3.1 | 500 | 0.71 | 71% | results/claims-dossiers/04-controls-and-reproducibility/ANALYSIS.md:83 | match | value + CI on one source row |  |
| 3.1 | 500 | +0.21 | 0.21 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| 3.1 | 500 | +0.11 | 0.11 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| 3.1 | 500 | +0.30 | 0.30 | results/claims-dossiers/02-communication-and-levels/tables/contrasts_within_model.csv:16 | rounding | value + CI on one source row |  |
| 3.1 | 504 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 504 | 95% |  |  | definition | structural |  |
| 3.1 | 504 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 504 | 10,000 | 10,000 | results/claims-dossiers/01-focal-points/ANALYSIS.md:49 | match | value in assigned source |  |
| 3.1 | 504 | 1 |  |  | definition | structural |  |
| 3.1 | 504 | 5 |  |  | definition | structural |  |
| 3.1 | 504 | 25 | 25 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 3.1 | 504 | 02 | 2 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 3.1 | 504 | 0.009 | 0.009 | results/claims-dossiers/MASTER_CLAIMS.md:138 | match | value in assigned source |  |
| 3.1 | 504 | +0.19 | 0.19 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 3.1 | 504 | 0.06 | 0.060 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 3.1 | 504 | 0.31 | 0.31 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:116 | match | value + CI on one source row |  |
| 3.1 | 504 | +0.23 | 0.23 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 3.1 | 504 | 0.10 | 0.10 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 3.1 | 504 | 0.35 | 0.35 | results/claims-dossiers/02-communication-and-levels/ANALYSIS.md:117 | match | value + CI on one source row |  |
| 3.1 | 504 | 1.00 |  |  | definition | structural |  |
| 3.1 | 504 | +-0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 3.1 | 504 | -0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.1 | 504 | 01 | 1.00 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 504 | 02 | 2 | results/claims-dossiers/MASTER_CLAIMS.md:9 | match | value in assigned source |  |
| 3.1 | 508 | 0.48 | 0.48 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.1 | 508 | 0.29 | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.1 | 508 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 3.1 | 508 | 35% | 0.35 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.1 | 508 | 0.05 |  |  | definition | structural |  |
| 3.1 | 508 | 2.07 | 2.07 | results/claims-dossiers/11-fresh-discovery/ANALYSIS.md:43 | match | value in assigned source |  |
| 3.1 | 508 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.1 | 508 | 2.00 |  |  | definition | structural |  |
| 3.1 | 508 | 11 | 11 | results/claims-dossiers/MASTER_CLAIMS.md:55 | match | value in assigned source |  |
| 3.1 | 510 | 0.39 | 0.39 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.1 | 512 | +0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 512 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 512 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value + CI on one source row |  |
| 3.1 | 512 | 0.70 |  |  | definition | structural |  |
| 3.1 | 518 | 1.00 |  |  | definition | structural |  |
| 3.1 | 518 | 5.00 |  |  | definition | structural |  |
| 3.1 | 518 | 0.01 |  |  | definition | structural |  |
| 3.1 | 518 | 3.00 |  |  | definition | structural |  |
| 3.1 | 519 | 0.01 |  |  | definition | structural |  |
| 3.1 | 520 | - 1 |  |  | definition | structural |  |
| 3.1 | 520 | 2 |  |  | definition | structural |  |
| 3.1 | 520 | 0 |  |  | definition | structural |  |
| 3.1 | 520 | 1.00 |  |  | definition | structural |  |
| 3.1 | 520 | 1 |  |  | definition | structural |  |
| 3.1 | 520 | 3.00 |  |  | definition | structural |  |
| 3.1 | 521 | 1.00 |  |  | definition | structural |  |
| 3.1 | 521 | 1.50 |  |  | definition | structural |  |
| 3.1 | 521 | 2.00 |  |  | definition | structural |  |
| 3.1 | 521 | 2.49 |  |  | definition | structural |  |
| 3.1 | 521 | 2.50 |  |  | definition | structural |  |
| 3.1 | 521 | 3.00 |  |  | definition | structural |  |
| 3.1 | 521 | 3.50 |  |  | definition | structural |  |
| 3.1 | 521 | 4.00 |  |  | definition | structural |  |
| 3.1 | 522 | 7 |  |  | definition | structural |  |
| 3.1 | 522 | 150 |  |  | definition | structural |  |
| 3.1 | 523 | 70 | 70 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.1 | 523 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.1 | 525 | 3 |  |  | definition | structural |  |
| 3.1 | 526 | 0.70 |  |  | definition | structural |  |
| 3.1 | 526 | 0 |  |  | definition | structural |  |
| 3.1 | 527 | 1.00 |  |  | definition | structural |  |
| 3.1 | 528 | 1.00 |  |  | definition | structural |  |
| 3.1 | 529 | 1 |  |  | definition | structural |  |
| 3.1 | 529 | 3 |  |  | definition | structural |  |
| 3.1 | 529 | 1.00 |  |  | definition | structural |  |
| 3.1 | 529 | 0.01 |  |  | definition | structural |  |
| 3.1 | 529 | 0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.2 | 537 | 3.2 |  |  | definition (section id) | structural |  |
| 3.2 | 537 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 3.2 | 539 | 3.2 | 3.2 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.2 | 541 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.26 | 0.26 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.42 | 0.42 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 541 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 3.2 | 541 | 0.022 | 0.022 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.2 | 541 | 8 |  |  | definition | structural |  |
| 3.2 | 541 | -0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 3.2 | 541 | +0.03 | 0.03 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 3.2 | 541 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.2 | 541 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.2 | 541 | 3 |  |  | definition | structural |  |
| 3.2 | 541 | 9 |  |  | definition | structural |  |
| 3.2 | 541 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:160 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.15 | 0.15 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 541 | +0.08 | 0.08 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 541 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.2 | 541 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.2 | 541 | 1.88 |  |  | definition | structural |  |
| 3.2 | 541 | 0.23 | 0.23 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.2 | 541 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 541 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 541 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 543 | 3.2 | 3.2 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.2 | 543 | 95% |  |  | definition | structural |  |
| 3.2 | 543 | 10,000 | 10,000 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:54 | match | value in assigned source |  |
| 3.2 | 545 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 3.2 | 545 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.2 | 545 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 3.2 | 547 | 1.00 |  |  | definition | structural |  |
| 3.2 | 547 | 5.00 |  |  | definition | structural |  |
| 3.2 | 547 | -0.45 | 0.45 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.71 | 71% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:86 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.05 | 0.05 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:482 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.29 | 0.29 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:482 | rounding | value + CI on one source row |  |
| 3.2 | 547 | +0.18 | 0.18 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:482 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.46 | 0.46 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.57 | 0.57 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 3.2 | 547 | -0.35 | 0.35 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:191 | rounding | value + CI on one source row |  |
| 3.2 | 548 | 0 |  |  | definition | structural |  |
| 3.2 | 548 | 1 |  |  | definition | structural |  |
| 3.2 | 548 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 548 | 0.022 | 0.022 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.2 | 548 | -0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.15 | 0.15 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 548 | +0.08 | 0.08 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 548 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.2 | 548 | -0.23 | 0.23 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.29 | 0.29 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.27 | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value + CI on one source row |  |
| 3.2 | 548 | -0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:192 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 548 | -0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 548 | +0.01 | 0.01 | results/claims-dossiers/MASTER_CLAIMS.md:138 | rounding | value + CI on one source row |  |
| 3.2 | 549 | 0 |  |  | definition | structural |  |
| 3.2 | 549 | 1 |  |  | definition | structural |  |
| 3.2 | 549 | -0.26 | 0.26 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.42 | 0.42 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.11 | 0.11 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:88 | rounding | value + CI on one source row |  |
| 3.2 | 549 | 0.023 | 0.023 | results/claims-dossiers/MASTER_CLAIMS.md:79 | match | value in assigned source |  |
| 3.2 | 549 | -0.04 | 4% | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:484 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.19 | 0.19 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:484 | rounding | value + CI on one source row |  |
| 3.2 | 549 | +0.09 | 0.09 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:484 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.33 | 0.33 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.43 | 0.43 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 3.2 | 549 | -0.24 | 0.24 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:193 | rounding | value + CI on one source row |  |
| 3.2 | 550 | +0.17 | 0.17 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 3.2 | 550 | +0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 3.2 | 550 | +0.27 | 0.27 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:89 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.05 | 0.05 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:485 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.22 | 0.22 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:485 | rounding | value + CI on one source row |  |
| 3.2 | 550 | +0.11 | 0.11 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:485 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.18 | 0.18 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 3.2 | 550 | +0.05 | 0.05 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:194 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.29 | 0.29 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 3.2 | 550 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:196 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.19 | 0.19 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.27 | 0.27 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:90 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.12 | -0.1149 (hi) | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:215 | **MISMATCH** | hand-checked against full-precision csv | double rounding of -0.115; correct -0.11 |
| 3.2 | 551 | +0.01 | 0.01 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:486 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.17 | 0.17 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:486 | rounding | value + CI on one source row |  |
| 3.2 | 551 | +0.18 | 0.18 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:486 | rounding | value + CI on one source row |  |
| 3.2 | 551 | +0.06 | 0.060 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 3.2 | 551 | +0.22 | 0.22 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.10 | 0.10 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:195 | rounding | value + CI on one source row |  |
| 3.2 | 551 | -0.24 | 0.24 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:197 | rounding | value + CI on one source row |  |
| 3.2 | 551 | +0.04 | 4% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:197 | rounding | hand-checked | source +0.0350 at 4 decimals: borderline |
| 3.2 | 555 | 8 |  |  | definition | structural |  |
| 3.2 | 555 | 08 | 08 | results/claims-dossiers/MASTER_CLAIMS.md:58 | match | value in assigned source |  |
| 3.2 | 555 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.2 | 555 | 1.0 |  |  | definition | structural |  |
| 3.2 | 555 | 2.8 |  |  | definition | structural |  |
| 3.2 | 555 | 80% |  |  | definition | structural |  |
| 3.2 | 555 | 08 | 08 | results/claims-dossiers/MASTER_CLAIMS.md:58 | match | value in assigned source |  |
| 3.2 | 555 | 09 | 09 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 3.2 | 559 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:38 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.14 | 0.14 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:38 | rounding | value + CI on one source row |  |
| 3.2 | 559 | +0.09 | 0.09 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:38 | rounding | value + CI on one source row |  |
| 3.2 | 559 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.2 | 559 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.2 | 559 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:38 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.15 | 0.15 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 559 | +0.08 | 0.08 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 559 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.2 | 559 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.2 | 559 | +0.04 | 4% | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:468 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.06 | 0.060 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:468 | rounding | value + CI on one source row |  |
| 3.2 | 559 | +0.13 | 0.13 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:468 | rounding | value + CI on one source row |  |
| 3.2 | 559 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.2 | 559 | 0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.2 | 559 | -0.06 | 0.060 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:468 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.15 | 0.15 | results/claims-dossiers/08-market-structure-and-incentives/contrasts.csv:145 | rounding | value + CI on one source row |  |
| 3.2 | 559 | +0.03 | 0.03 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:41 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.07 | 0.07 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 3.2 | 559 | -0.18 | 0.18 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 3.2 | 559 | +0.02 | 0.020 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 3.2 | 559 | 0.27 | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 3.2 | 559 | 0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 3.2 | 559 | 0 |  |  | definition | structural |  |
| 3.2 | 559 | 3 |  |  | definition | structural |  |
| 3.2 | 559 | 4 |  |  | definition | structural |  |
| 3.2 | 559 | -0.08 | 0.08 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:133 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.18 | 0.18 | results/claims-dossiers/08-market-structure-and-incentives/ANALYSIS.md:174 | match | value + CI on one source row |  |
| 3.2 | 559 | +0.01 | 0.01 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:133 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.09 | 0.09 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:133 | rounding | value + CI on one source row |  |
| 3.2 | 559 | -0.19 | 0.19 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:133 | rounding | value + CI on one source row |  |
| 3.2 | 559 | +0.00 | 0 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:133 | rounding | value + CI on one source row |  |
| 3.2 | 559 | 103 | 103 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:111 | match | value in assigned source |  |
| 3.2 | 559 | 7 |  |  | definition | structural |  |
| 3.2 | 559 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 3.2 | 561 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.2 | 561 | 15 | 15 | results/claims-dossiers/MASTER_CLAIMS.md:35 | match | value in assigned source |  |
| 3.2 | 561 | 8 |  |  | definition | structural |  |
| 3.2 | 561 | 17 | 17 | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 3.2 | 561 | 5 |  |  | definition | structural |  |
| 3.2 | 561 | 18 | 18 | results/claims-dossiers/MASTER_CLAIMS.md:107 | match | value in assigned source |  |
| 3.2 | 561 | -0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 3.2 | 561 | -0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 3.2 | 561 | +0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:140 | rounding | value + CI on one source row |  |
| 3.2 | 563 | +0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 563 | -0.07 | 0.07 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 563 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:137 | rounding | value + CI on one source row |  |
| 3.2 | 563 | -0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.2 | 563 | -0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.2 | 563 | -0.08 | 0.08 | results/claims-dossiers/MASTER_CLAIMS.md:109 | match | value in assigned source |  |
| 3.2 | 563 | -0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value in assigned source |  |
| 3.2 | 570 | 3 |  |  | definition | structural |  |
| 3.2 | 570 | 1 |  |  | definition | structural |  |
| 3.2 | 570 | 2 |  |  | definition | structural |  |
| 3.2 | 571 | 1.88 |  |  | definition | structural |  |
| 3.2 | 571 | 1.00 |  |  | definition | structural |  |
| 3.2 | 571 | 6 |  |  | definition | structural |  |
| 3.2 | 571 | 10 | 10 | results/claims-dossiers/MASTER_CLAIMS.md:3 | match | value in assigned source |  |
| 3.3 | 586 | 3.3 |  |  | definition (section id) | structural |  |
| 3.3 | 588 | 3.3 | 3.3 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.3 | 590 | 1.2 |  |  | definition (cross-reference) | structural |  |
| 3.4 | 602 | 3.4 |  |  | definition (section id) | structural |  |
| 3.4 | 602 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 604 | 3.4 | 3.4 | results/claims-dossiers/MASTER_CLAIMS.md:29 | match | value in assigned source |  |
| 3.4 | 606 | 1 |  |  | definition | structural |  |
| 3.4 | 606 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 606 | 1.00 |  |  | definition | structural |  |
| 3.4 | 606 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.4 | 606 | -0.58 | 0.58 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.79 | 0.79 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 606 | 0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 606 | 24 | 24 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 606 | 2.00 |  |  | definition | structural |  |
| 3.4 | 606 | 0.31 | 0.31 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:294 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.56 | 0.56 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:294 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.05 | 0.05 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:294 | match | value + CI on one source row |  |
| 3.4 | 606 | 0.7% | 0.007 | results/claims-dossiers/MASTER_CLAIMS.md:78 | match | value in assigned source |  |
| 3.4 | 606 | 0.4% | 0.004 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 606 | -0.004 | 0.004 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.023 | 0.023 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 606 | +0.011 | 0.011 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 606 | 0.13 | 0.13 | results/oss/ad-hoc/cot-monitor-threat/ANALYSIS.md:7 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.25 | 0.25 | results/oss/ad-hoc/cot-monitor-threat/ANALYSIS.md:7 | match | value + CI on one source row |  |
| 3.4 | 606 | -0.005 | 0.005 | results/oss/ad-hoc/cot-monitor-threat/ANALYSIS.md:7 | match | value + CI on one source row |  |
| 3.4 | 606 | 0.59 | 0.59 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.4 | 606 | 0.46 | 0.46 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value in assigned source |  |
| 3.4 | 606 | 22% | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 3.4 | 606 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.4 | 606 | 0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 3.4 | 606 | 0.18 | 0.18 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:193 | rounding | value + CI on one source row |  |
| 3.4 | 606 | -0.29 | 0.29 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:193 | rounding | value + CI on one source row |  |
| 3.4 | 606 | -0.08 | 0.08 | results/claims-dossiers/01-focal-points/tables/paired_contrasts.csv:193 | rounding | value + CI on one source row |  |
| 3.4 | 606 | 0.003 | 0.003 | results/claims-dossiers/MASTER_CLAIMS.md:109 | match | value in assigned source |  |
| 3.4 | 606 | 29% | 0.29 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 608 | 1 |  |  | definition | structural |  |
| 3.4 | 610 | 95% |  |  | definition | structural |  |
| 3.4 | 612 | 1.00 |  |  | definition | structural |  |
| 3.4 | 612 | 5.00 |  |  | definition | structural |  |
| 3.4 | 612 | 2.18 | 2.176 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:123 | rounding | value in assigned source |  |
| 3.4 | 612 | 1.92 | 1.92 | results/oss/trackm-neutral-2026-10-26/step2/REPORT.md:99 | match | value in assigned source |  |
| 3.4 | 612 | -0.26 | 0.26 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 3.4 | 612 | -0.51 | 0.51 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 3.4 | 612 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:123 | rounding | value + CI on one source row |  |
| 3.4 | 612 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 612 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.4 | 612 | 1.00 |  |  | definition | structural |  |
| 3.4 | 612 | 0.36 | 0.36 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 613 | 0 |  |  | definition | structural |  |
| 3.4 | 613 | 1 |  |  | definition | structural |  |
| 3.4 | 613 | 0.59 | 0.59 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.4 | 613 | 0.46 | 0.46 | results/claims-dossiers/MASTER_CLAIMS.md:171 | match | value in assigned source |  |
| 3.4 | 613 | -0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 3.4 | 613 | -0.25 | 0.25 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 3.4 | 613 | -0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | rounding | value + CI on one source row |  |
| 3.4 | 613 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 613 | 0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.4 | 613 | 1.00 |  |  | definition | structural |  |
| 3.4 | 613 | 0.19 | 0.19 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 3.4 | 613 | 0.18 | 0.18 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 614 | 0.78 | 0.78 | results/claims-dossiers/07-detection/ANALYSIS.md:78 | match | value in assigned source |  |
| 3.4 | 614 | 0.65 | 0.65 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 614 | -0.13 | 0.13 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 3.4 | 614 | -0.28 | 0.28 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 3.4 | 614 | +0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:125 | rounding | value + CI on one source row |  |
| 3.4 | 614 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 614 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 614 | 1.00 |  |  | definition | structural |  |
| 3.4 | 614 | 0.23 | 0.23 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 615 | 0.43 | 0.43 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.4 | 615 | 0.56 | 0.56 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 615 | +0.13 | 0.13 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:126 | rounding | value + CI on one source row |  |
| 3.4 | 615 | -0.01 | 0.01 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:126 | rounding | value + CI on one source row |  |
| 3.4 | 615 | +0.26 | 0.26 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:126 | rounding | value + CI on one source row |  |
| 3.4 | 615 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 615 | 0.09 | 0.09 | results/claims-dossiers/MASTER_CLAIMS.md:76 | match | value in assigned source |  |
| 3.4 | 615 | 1.00 |  |  | definition | structural |  |
| 3.4 | 615 | 0.20 | 20% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 3.4 | 616 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.4 | 616 | 0.26 | 0.26 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.4 | 616 | -0.16 | 0.16 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:127 | rounding | value + CI on one source row |  |
| 3.4 | 616 | -0.28 | 0.28 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:127 | rounding | value + CI on one source row |  |
| 3.4 | 616 | -0.04 | 4% | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:127 | rounding | value + CI on one source row |  |
| 3.4 | 616 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 616 | 0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 616 | 0.54 | 54% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 3.4 | 616 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.4 | 617 | 1.00 |  |  | definition | structural |  |
| 3.4 | 617 | 0.42 | 0.42 | results/claims-dossiers/MASTER_CLAIMS.md:137 | match | value in assigned source |  |
| 3.4 | 617 | -0.58 | 0.58 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 617 | -0.79 | 0.79 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 617 | -0.37 | 0.37 | results/claims-dossiers/MASTER_CLAIMS.md:157 | match | value + CI on one source row |  |
| 3.4 | 617 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 617 | 0.001 | 0.001 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.4 | 617 | 0.02 | 0.020 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 618 | 2.00 |  |  | definition | structural |  |
| 3.4 | 618 | 0.70 |  |  | definition | structural |  |
| 3.4 | 618 | 0.38 | 0.38 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 618 | -0.31 | 0.31 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 3.4 | 618 | -0.56 | 0.56 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 3.4 | 618 | -0.05 | 0.05 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:235 | rounding | value + CI on one source row |  |
| 3.4 | 618 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 618 | 0.03 | 0.03 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 618 | 0.53 | 53% | results/claims-dossiers/MASTER_CLAIMS.md:69 | match | value in assigned source |  |
| 3.4 | 619 | 0.007 | 0.007 | results/claims-dossiers/MASTER_CLAIMS.md:78 | match | value in assigned source |  |
| 3.4 | 619 | 0.004 | 0.004 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 619 | -0.004 | 0.004 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 619 | -0.023 | 0.023 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 619 | +0.011 | 0.011 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:236 | match | value + CI on one source row |  |
| 3.4 | 619 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 619 | 1.00 |  |  | definition | structural |  |
| 3.4 | 619 | 1.00 |  |  | definition | structural |  |
| 3.4 | 627 | 1 |  |  | definition | structural |  |
| 3.4 | 629 | 1.00 |  |  | definition | structural |  |
| 3.4 | 629 | 5.00 |  |  | definition | structural |  |
| 3.4 | 629 | 0.01 |  |  | definition | structural |  |
| 3.4 | 629 | 1.00 |  |  | definition | structural |  |
| 3.4 | 629 | 3.00 |  |  | definition | structural |  |
| 3.4 | 630 | 1.00 |  |  | definition | structural |  |
| 3.4 | 630 | 5.00 |  |  | definition | structural |  |
| 3.4 | 631 | - 1.00 |  |  | definition | structural |  |
| 3.4 | 631 | 2.00 |  |  | definition | structural |  |
| 3.4 | 631 | 0 |  |  | definition | structural |  |
| 3.4 | 631 | 1.00 |  |  | definition | structural |  |
| 3.4 | 631 | 1 |  |  | definition | structural |  |
| 3.4 | 631 | 3.00 |  |  | definition | structural |  |
| 3.4 | 632 | 0 |  |  | definition | structural |  |
| 3.4 | 632 | 1 |  |  | definition | structural |  |
| 3.4 | 633 | 1.00 |  |  | definition | structural |  |
| 3.4 | 634 | 1.00 |  |  | definition | structural |  |
| 3.4 | 635 | 1 |  |  | definition | structural |  |
| 3.4 | 636 | 2.00 |  |  | definition | structural |  |
| 3.4 | 637 | 95% |  |  | definition | structural |  |
| 3.4 | 637 | 10,000 | 10,000 | results/claims-dossiers/09-failed-tactics/oversight/ANALYSIS.md:168 | match | value in assigned source |  |
| 3.4 | 637 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 638 | 30 | 30 | results/claims-dossiers/MASTER_CLAIMS.md:66 | match | value in assigned source |  |
| 3.4 | 638 | 24 | 24 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 638 | 22 | 22 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 3.4 | 639 | 2.8 |  |  | definition | structural |  |
| 3.4 | 640 | 0.07 | 0.07 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 640 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 644 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:28 | rounding | hand-checked | watchdog arms -0.022, +0.038, -0.0249 (oversight contrasts.csv); MASTER prints -0.03 to +0.04 (it rounds -0.025) |
| 3.4 | 644 | +0.06 | 0.060 | results/claims-dossiers/MASTER_CLAIMS.md:87 | match | value in assigned source |  |
| 3.4 | 644 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.4 | 644 | 1.0 |  |  | definition (cross-reference) | structural |  |
| 3.4 | 644 | 0.13 | 0.13 | results/claims-dossiers/MASTER_CLAIMS.md:91 | match | value in assigned source |  |
| 3.4 | 644 | +0.105 | 0.105 | results/claims-dossiers/MASTER_CLAIMS.md:149 | match | value in assigned source |  |
| 3.4 | 644 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:28 | rounding | value + CI on one source row |  |
| 3.4 | 644 | +0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value in assigned source |  |
| 3.4 | 644 | 0.14 | 0.14 | results/claims-dossiers/MASTER_CLAIMS.md:67 | match | value in assigned source |  |
| 3.4 | 644 | 0.17 | 0.17 | results/claims-dossiers/MASTER_CLAIMS.md:68 | match | value in assigned source |  |
| 3.4 | 644 | -0.07 | -0.0562 price / -0.0737 profit gain | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:23-24 | **MISMATCH** | hand-checked against full-precision csv | metric not named; on the price index (the metric of the surrounding sentences) the value is -0.06 [-0.15, +0.03], p 0.27; -0.07 is profit gain |
| 3.4 | 644 | -0.19 | -0.1538 price / -0.1841 profit gain | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:23-24 | **MISMATCH** | hand-checked against full-precision csv | MASTER_CLAIMS G-watchdog prints -0.074 [-0.186, +0.020] (profit gain, other bootstrap); Section 3.2 uses -0.07 [-0.18, +0.02] |
| 3.4 | 644 | +0.02 | +0.0303 price / +0.0208 profit gain | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:23-24 | **MISMATCH** | hand-checked against full-precision csv | see -0.07 on this line |
| 3.4 | 644 | 0.22 | 0.2677 price / 0.2166 profit gain | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:23-24 | **MISMATCH** | hand-checked against full-precision csv | see -0.07 on this line |
| 3.4 | 644 | 3 |  |  | definition | structural |  |
| 3.4 | 644 | -0.02 | 0.020 | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:28 | rounding | value + CI on one source row |  |
| 3.4 | 644 | -0.11 | 0.11 | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:28 | rounding | hand-checked | oversight csv -0.1148; dossier 08 / MASTER G-null-struct give -0.117 (other bootstrap), used as [-0.12, +0.09] in 1.2, 1.5, 3.2 |
| 3.4 | 644 | +0.09 | 0.09 | results/claims-dossiers/09-failed-tactics/oversight/contrasts.csv:28 | rounding | value + CI on one source row |  |
| 3.4 | 644 | 0.15 | 0.15 | results/claims-dossiers/MASTER_CLAIMS.md:45 | match | value in assigned source |  |
| 3.4 | 644 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.4 | 644 | -0.50 | 0.50 | results/claims-dossiers/MASTER_CLAIMS.md:161 | match | value + CI on one source row |  |
| 3.4 | 644 | -0.70 | 0.70 | results/claims-dossiers/MASTER_CLAIMS.md:161 | match | value + CI on one source row |  |
| 3.4 | 644 | -0.30 | 0.30 | results/claims-dossiers/MASTER_CLAIMS.md:161 | match | value + CI on one source row |  |
| 3.4 | 644 | 0.04 | 4% | results/claims-dossiers/MASTER_CLAIMS.md:92 | match | value in assigned source |  |
| 3.4 | 646 | -0.005 | 0.005 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 3.4 | 646 | 0 |  |  | definition | structural |  |
| 3.4 | 646 | -0.22 | 0.22 | results/claims-dossiers/MASTER_CLAIMS.md:37 | match | value in assigned source |  |
| 3.4 | 646 | 12 | 12 | results/claims-dossiers/MASTER_CLAIMS.md:52 | match | value in assigned source |  |
| 3.4 | 646 | 19 | 19 | results/claims-dossiers/MASTER_CLAIMS.md:41 | match | value in assigned source |  |
| 3.4 | 646 | 20 | 20 | results/claims-dossiers/MASTER_CLAIMS.md:5 | match | value in assigned source |  |
| 3.4 | 648 | -0.23 | 0.23 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:35 | rounding | value + CI on one source row |  |
| 3.4 | 648 | -0.31 | 0.31 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:35 | rounding | value + CI on one source row |  |
| 3.4 | 648 | -0.15 | 0.15 | results/claims-dossiers/09-failed-tactics/ANALYSIS.md:35 | rounding | value + CI on one source row |  |
| 3.4 | 648 | 0.002 | 0.002 | results/claims-dossiers/MASTER_CLAIMS.md:156 | match | value in assigned source |  |
| 3.4 | 648 | 27% | 0.27 | results/claims-dossiers/MASTER_CLAIMS.md:70 | match | value in assigned source |  |
| 3.4 | 648 | -0.55 | 0.55 | results/claims-dossiers/MASTER_CLAIMS.md:110 | match | value in assigned source |  |
| 3.4 | 655 | +0.10 | 0.10 | results/claims-dossiers/MASTER_CLAIMS.md:53 | match | value in assigned source |  |
| 3.4 | 655 | 0.12 | 0.12 | results/claims-dossiers/MASTER_CLAIMS.md:77 | match | value in assigned source |  |
| 3.4 | 657 | 1 |  |  | definition | structural |  |
| 3.4 | 657 | 3 |  |  | definition | structural |  |

<small>

**Terms used on this page.** *match*: same value as the source. *rounding*: the source value, rounded half up to the text's decimals, equals the text value. *definition*: a structural number of the game or the document, not a result. *mismatch*: the text differs from the source after rounding. *not found*: no source value. *Holm*: multiplicity correction within the family named in the dossier. *MDE*: minimum detectable effect, 2.8 x standard error. *Pair*: one (wording, seed) combination played under both arms.

</small>


## 7. Disposition (applied after this check)

This check ran on the draft before the reviewer's fixes (REVIEW.md). Both sets of fixes were then applied to STEP4.md:

| VERIFY fix | Applied | Note |
|---|---|---|
| 1, 2 (interval method for detector AUCs) | yes | now "over (wording, seed) pairs" in the preamble and the box legend |
| 3 to 6, 8, 9 (double-rounding slips) | yes | all occurrences replaced (fix 4 in three places) |
| 7 (text-detector recall lower end 0.20) | yes, in 1.3 and 2.2 | the reviewer's R10 had changed 1.3 to the dossier prose values (0.21 / 0.09); the full-precision CSV values (0.20 / 0.08) are used in both sections |
| 10 (report threat in 3.4) | yes, via the reviewer's R11 | 3.4 now names both metrics: profit gain -0.07 [-0.19, +0.02] (MASTER_CLAIMS bootstrap) and price index -0.06 [-0.15, +0.03]; 3.2 gives the same pair |
| Source conflict: one-of-two ethics rule interval | yes | -0.02 [-0.12, +0.09] (dossier 08 and MASTER_CLAIMS) used throughout |
| Source conflict: Table 2.1 pooled CIs | yes, via the reviewer's R7 | pooled CIs from dossier 02 `tables/contrasts_within_model.csv` added |
| Source conflicts: 5-tick Holm, hard cases, watchdog range, 0.40 to 0.47, borderline roundings | kept as written | both values are correct for their source; the text cites the dossier row it quotes |

Numbers introduced by the reviewer's edits (R7 pooled CIs, R3 refit text AUC 0.87 [0.84, 0.90], R4 and R20 additions) were taken from the files named in REVIEW.md and checked there.
