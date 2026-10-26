## VERIFY: every number in the Step 4 (gpt-oss-20b) sections against the source of truth

Created by Claude at the prompting of the repository owner. Each row compares a number as written in a section file (or the header) with its value in the Step 2 / Step 3 / ad-hoc / cross-model source. **match** = identical at the printed precision; **rounding** = the printed value is the source value rounded (or a 3 dp source read at 4 dp); **mismatch fixed** = the section text was wrong and has been corrected in the text (never in the source); **not found** = no source located. Directions were checked against `out/step3/claims_ledger.csv`, and question texts against `CLONE/alignment/AREAS_TO_SPRINT_OBJECTIVES.md` (lines 18 to 20).

### Summary

| Part | Sections | Rows | match | rounding | mismatch fixed | not found |
|---|---|---|---|---|---|---|
| Header | 00_header (box, five-metric table, game lines) | 25 | 15 | 10 | 0 | 0 |
| Figures | figure data against each section's table | 10 | 10 | 0 | 0 | 0 |
| A | 1.1, 1.5, 2.1 | 65 | 59 | 3 | 3 | 0 |
| B | 1.2, 3.2 | 38 | 21 | 15 | 2 (plus 3 text fixes logged as match or rounding) | 0 |
| C | 1.3, 2.2, 1.4, 3.3 | 59 | 51 | 2 | 6 | 0 |
| D | 2.3, 3.1, 3.4 | 93 | 28 | 63 (3 of them mixed match / rounding) | 2 | 0 |
| Review round | numbers added or changed for `zz_review.md` (supersede old rows) | 42 | 14 | 27 | 0 | 1 (Qwen watchdog MDE) |
| **Total** | | **332** | **198** | **120** | **13** (16 text fixes in all) | **1** |

A row can carry several numbers (an estimate with its interval and n is one row; in 3.1 a table row covers up to 15 numbers), so about 450 individual numbers are covered.

**Fixes made in the section text:** 1.5 interval [0.46, 0.64] to [0.46, 0.63] (text and table) and Qwen profit drop -0.76 to -0.75; 1.2 sign style (-0.23, -0.30), mean LLM quote 1.99 to 1.995, and the source of the cheater-minus-chat interval; 3.2 sign style (-0.22) and an added Step 2 watchdog sentence (asks + may report minus asks: -0.06 [-0.10, -0.01] with the stratified bootstrap); 1.3 Qwen mean-quote AUC upper bound 0.95 to 0.94 and Qwen quote-features AUC lower bound 0.78 to 0.77; 2.2 Qwen AUC upper bounds 0.95 to 0.94, all-arms difference lower bound -0.03 to -0.02, Qwen both-minus-text upper bound 0.31 to 0.30; 2.3 Qwen AUC upper bound 0.95 to 0.94 (found at assembly, same source row as 1.3); 3.4 "Qwen Holm p 0.009" moved from the price index (exploratory on Qwen, BH q 0.0006) to the profit gain index; 3.1 "undercuts" reworded to the competitive-share definition. Interval-source rows were added to the Terms table of every section.

**Directions:** every section's sign agrees with the ledger (G-payoff, G-comm, G-moral, G-5tick, G-fxjoint, G-cheater, G-n3ethics, G-watchdog, G-detect-quotes, G-detect-text, G-ctl, G-repro, G-cot). One wording difference is kept on purpose: the ledger's overall verdict for G-cot is "in sign only" (its profit-gain interval includes 0), while 3.4 says "yes (sign and size)" for the price index alone and states the profit-gain caveat.

**Question texts:** all twelve (1.1 to 1.5, 2.1 to 2.3, 3.1 to 3.4) are verbatim from `AREAS_TO_SPRINT_OBJECTIVES.md`, which gives only the short Overview-tab form.

**Interval sources by section:** 1.1, 1.5, 2.1: `out/compare/lever_table.csv` (= `primed_vs_unprimed.csv`). 1.2, 3.2: `lever_table.csv` (= the ad-hoc `standard_metrics.csv`), with p, BH q and side contrasts from Step 2 `contrasts_all.csv`. 1.3, 2.2: `ad-hoc/detection-transfer/*.csv`. 2.3, 3.4: Step 2 `contrasts_all.csv` (bootstrap stratified by wording). 3.1: ad-hoc level tables (`penalty/cells.csv`, `controls/cell_means.csv`) plus `lever_table.csv`.

**Open items (not mismatches):** (1) Resolved in the review round: 1.3 and 2.3 now explain 0 of 57 (labelled games) against 0 of 60 (all headline-chat games). (2) The ledger quotes other bootstrap draws for some contrasts (G-payoff [-0.63, -0.48], G-comm [0.08, 0.29], G-moral [-0.49, -0.25]); the sections use `lever_table.csv` and say so. (3) Qwen Step 4 gives the ethics-rule interval as +0.02 [-0.07, +0.10] against `lever_table.csv` [-0.06, +0.10] (different draw; the section uses lever_table). (4) The primer link in the header is written as `../../../plans/SCOPE_AND_EXPERIMENTAL_DESIGN.md`, which assumes the file is published at `results/<run>/step4/STEP4.md`; adjust if it lands elsewhere.

### Header (00_header.md)

Sources: PVU = `out/compare/primed_vs_unprimed.csv`; LT = `out/compare/lever_table.csv`; CM = `CLONE/results/oss/ad-hoc/payoff-table-focal-points/cell_means.csv`; DT = `CLONE/results/oss/ad-hoc/detection-transfer/detection_transfer.csv` (label `c_outcome`); CA = `out_t2/step2/tables/contrasts_all.csv` (arm d-cot-monitor-a, control headline-chat p1); S2 = `out_t2/step2/REPORT.md`; Q4 = Qwen `results/trackm-neutral-2026-10-25/step4/STEP4.md`.

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| header | 819 finished games of 840 planned, 21 failed | S2 line 3 | "819 of 840 planned games DONE, 21 failed" | match |
| header | 2 firms (3 in three-firm arms), at most 20 rounds, 5 wordings x 4 seeds = 20 pairs | S2 line 5 ("7 to 20 rounds"); `contrasts_all.csv` n 20 | same | match |
| box T1 | gpt-oss -0.56 [-0.63, -0.46], 20 pairs | PVU gpt-oss "nx-chat-p1 (p1) - headline-chat (p1)" price_index | -0.5567 [-0.6347, -0.4643], 20 | match |
| box T1 | Qwen -0.74 [-0.82, -0.65], 20 pairs | LT same contrast qwen_diff/lo/hi | -0.735 [-0.816, -0.650], 20 | rounding |
| box T1 | gpt-oss 0.57 to 0.02 | CM headline-chat p1 / nx-chat-p1 price_index | 0.5735 / 0.0168 | match |
| box T2 | gpt-oss -0.01 [-0.02, +0.01], 524 games | DT "B: all non-bug chat arms", DIFF both(quotes+TF-IDF, Qwen-fitted) minus quotes | -0.0080 [-0.0249, +0.0085], 524 | rounding |
| box T2 | headline chat +0.02 [-0.03, +0.09], 57 games | DT "headline-chat (p1,p3,p5)", same detector | +0.0227 [-0.0300, +0.0882], 57 | match |
| box T2 | Qwen -0.00 [-0.03, +0.04], 145 games | DT Qwen held-out half, DIFF both(quotes+TF-IDF) minus quotes | -0.00077 [-0.0286, +0.0376], 145 | match |
| box T3 | gpt-oss -0.13 [-0.24, -0.02], 19 pairs, Holm p 0.19 | CA price est/lo/hi/n/holm_p | -0.1298 [-0.2416, -0.0237], 19, 0.1924 | rounding |
| box T3 | Qwen -0.23 [-0.29, -0.18], 20 pairs | CA price qwen_est/lo/hi/n | -0.2325 [-0.2899, -0.1751], 20 | rounding |
| box metrics T1 | spread -1.11 [-1.26, -0.94] / Qwen -1.47 [-1.62, -1.29] | PVU market_price_mean | -1.1134 [-1.2641, -0.94] / -1.4706 [-1.6237, -1.2924] | match |
| box metrics T1 | price -0.56 [-0.63, -0.46] / -0.74 [-0.82, -0.65] | PVU price_index | -0.5567 [-0.6347, -0.4643] / -0.7353 [-0.8155, -0.6504] | match |
| box metrics T1 | pgi -0.74 [-0.82, -0.63] / -0.75 [-0.83, -0.66] | PVU profit_gain_index | -0.7359 [-0.8229, -0.6338] / -0.7548 [-0.8322, -0.6626] | match |
| box metrics T1 | comp -0.20 [-0.31, -0.08] / -0.00 [-0.02, +0.02] (degenerate) | PVU competitive_share; Qwen levels 0.0075 / 0.0103 | -0.199 [-0.3144, -0.0836] / -0.0027 [-0.0249, 0.015] | match |
| box metrics T1 | match +0.14 [-0.02, +0.29] / -0.23 [-0.36, -0.10] | PVU matching_share | 0.1446 [-0.0152, 0.29] / -0.2316 [-0.3625, -0.1048] | match |
| box metrics T3 | spread -0.26 [-0.48, -0.04] / -0.47 [-0.58, -0.36] | CA spread | -0.2597 [-0.4776, -0.0438] / -0.4716 [-0.5842, -0.3565] | rounding |
| box metrics T3 | price -0.13 [-0.24, -0.02] / -0.23 [-0.29, -0.18] | CA price | as above | rounding |
| box metrics T3 | pgi -0.13 [-0.28, +0.01] / -0.14 [-0.19, -0.08] | CA pgi | -0.1319 [-0.2769, +0.0052] / -0.1353 [-0.1939, -0.0827] | rounding |
| box metrics T3 | comp +0.13 [+0.02, +0.24] / +0.32 [+0.22, +0.41] | CA comp | 0.1276 [0.0202, 0.2409] / 0.3169 [0.2187, 0.4129] | rounding |
| box metrics T3 | match -0.16 [-0.27, -0.06] / -0.43 [-0.52, -0.35] | CA match | -0.1606 [-0.2663, -0.0603] / -0.4325 [-0.5188, -0.3491] | rounding |
| box terms | Holm over 22 declared tests | CA family_m for the price row | 22 | match |
| game lines | 1.00 to 5.00, ticks 0.01, 3.00 monopoly, 70% to the lowest quote | S2 line 5 | same | match |
| game lines | 2.09 = price index 0.546 at point 3 | Q4 theta* at p3 0.546; 1 + 2 x 0.546 = 2.092 | 2.092 | rounding |
| game lines | neutral table examples 1.00 to 4.00, 2.09 never printed | S2 line 5 | same | match |
| box direction | T1 negative, T2 null, T3 negative | LED G-payoff, G-detect-quotes, G-cot | same signs | match |

### Figures (make_figures.py, data/*.csv)

Every plotted value is copied by `make_figures.py` from the named source row into `data/fig_<section>.csv` (columns `source`, `source_key`), and the figure is drawn from that copy only. The check here is that each figure's row for the section's table contrast carries the same source values as the table.

| Section | Figure | Data rows checked | Same source as the table? | Result |
|---|---|---|---|---|
| 1.1 | figures/fig_1_1.png | nx-chat-p1 row (5 metrics x 2 models) = LT, -0.557 [-0.635, -0.464] etc. | yes (lever_table) | match |
| 1.2 | figures/fig_1_2.png | n3-cheater row = LT -0.232 [-0.286, -0.173], 18 / -0.305, 20 | yes | match |
| 1.3 | figures/fig_1_3.png | AUC rows = DT (0.814, 0.910, 0.902; 0.828, 0.850; 0.535, 0.387; plus all-arm 0.900, 0.669) | yes | match |
| 1.5 | figures/fig_1_5.png | nx-chat-p1, prime B (-0.377, 19), prime A (-0.321, 19), 5-tick (-0.285) = LT | yes | match |
| 2.1 | figures/fig_2_1.png | fx-ctl-joint vs fx-chat-p1 = LT +0.338 [0.150, 0.518], 19 / +0.068 | yes | match |
| 2.2 | figures/fig_2_2.png | AUC and DIFF rows = DT (table values) | yes | match |
| 2.3 | figures/fig_2_3.png | ctl-32b-compete row = CA -0.607 [-0.667, -0.543] etc.; extra ctl-32b-joint row = CA +0.132 [0.069, 0.199] / Qwen -0.040 | yes (contrasts_all) | match |
| 3.1 | figures/fig_3_1.png | tacit p1 / p5 = PEN; compete / joint = CTL cell_means | yes | match |
| 3.2 | figures/fig_3_2.png | n3-ethics row = LT -0.223 [-0.349, -0.102], 15 (= ethics-rule/standard_metrics); watchdog rows = LT (= watchdog/standard_metrics) | yes | match |
| 3.4 | figures/fig_3_4.png | d-cot-monitor-a row = CA (table values) | yes (contrasts_all) | match |

### Review round: numbers added or changed while fixing `zz_review.md`

These rows check every number added or rewritten in the fixes for the fresh review. Where a row in Parts A to D below describes the old wording (for example the unsigned 3.1 contrast "-0.38 [0.29, 0.47]", the 3.4 "Qwen messages +2.4" comparison, the 3.2 report-threat pair, or the 1.5 single nx-chat-p1 table), the row here supersedes it. Results: 42 rows, 14 match, 27 rounding, 0 mismatch, 1 not found (the Qwen watchdog MDE, which the text says was not found).

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| header / box T2 | Qwen comparator "thinking off and on pooled, headline and monitored chat, held-out half (145 games)" | `results/oss/ad-hoc/detection-transfer/ANALYSIS.md` line 47 | "headline chat plus monitored chat, thinking on and off pooled (n = 145)" | match |
| box T2 | chat-derived label: gpt-oss -0.065 [-0.114, -0.023], Qwen +0.105 [+0.007, +0.273] | DT b_agreement DIFF both minus quotes (GB / Qh) | -0.0648 [-0.1137, -0.0230] / +0.1050 [+0.0065, +0.2726] | match |
| box T3 | matching -0.16 / -0.43 | CA match est / qwen_est | -0.1606 / -0.4325 | rounding |
| box T3 | silent high-price share -0.004 [-0.023, +0.011] | COT silent_high silent_high_round_share | -0.0040 [-0.0226, 0.0105] | rounding |
| 1.2 | market price 1.83 before, 1.00 at, 1.72 to 1.77 after the defection | `cheater/event_time_gptoss.csv` | 1.83 / 1.0 / 1.72 / 1.77 | match |
| 1.2 | LLM quotes 2.07 / 2.05 / 1.995; 16 and 13 games | same file | 2.071 / 2.051 / 1.995; 16, 13 | match |
| 1.2 | mean market quote 1.76 vs 2.22 (gpt-oss), 1.74 vs 2.35 (Qwen) | `cheater/standard_metrics.csv` market_price_mean mean_arm / mean_control | 1.7568 / 2.2200; 1.7401 / 2.3499 | rounding |
| 1.2 | gpt-oss control competitive 44%, matching 38% | same file | 0.4360 / 0.3839 | rounding |
| 1.2 | scripted firm's standing quote about 1.8 to 1.9 | `cheater/ANALYSIS.md` line 75 | 1.8 to 1.9 | match |
| 3.2 | wd-notice-only -0.02 [-0.13, +0.09] | `watchdog/standard_metrics.csv` gpt-oss price_index | -0.0220 [-0.1282, 0.0912] | rounding |
| 3.2 | wd-ask-noreport +0.04 [-0.05, +0.13] | same file | 0.0381 [-0.0529, 0.1319] | rounding |
| 3.2 | wd-noncomp vs headline-chat -0.02 [-0.12, +0.07] | CA wd-noncomp price | -0.0248 [-0.1181, 0.0692] | rounding |
| 3.2 | watchdog MDEs 0.17 / 0.14 / 0.17 / 0.13 / 0.13 | CA mde_computed (price) | 0.165 / 0.139 / 0.169 / 0.133 / 0.125 | rounding |
| 3.2 | report threat Step 2 -0.06 [-0.10, -0.01], q 0.052; pgi -0.07 [-0.12, -0.02], q 0.024 | CA wd-noncomp vs wd-ask-noreport p1 | -0.0562 [-0.0972, -0.0132], 0.0519; -0.0737 [-0.1242, -0.0222], 0.0239 | match |
| 3.2 | report threat ad hoc gpt-oss -0.06 [-0.16, +0.03]; Qwen +0.00 [-0.08, +0.08] | LT "wd-noncomp - wd-ask-noreport" price_index | -0.056 [-0.158, 0.029]; 0.001 [-0.077, 0.079] | match |
| 3.2 | Qwen watchdog MDE | searched `watchdog/`, Qwen `contrasts_all.csv` | none | not found (stated in the text) |
| 1.3 | prevalence 0.61 against 0.90 | DT prevalence Gh / Qh | 0.614 / 0.8966 | rounding |
| 1.3, 2.3 | 57 labelled, 60 in all | DT n; DFR headline-chat | 57; 60 | match |
| 2.3 | chat levels at p3: 0.61 [0.53, 0.68], Qwen 0.77 [0.69, 0.83] | PEN headline-chat p3 price_index | 0.6127 [0.5265, 0.6818]; 0.7651 [0.6934, 0.8342] | rounding |
| 1.5 | prime A minus prime B +0.04 [-0.08, +0.17], 20 pairs | LT "moral-prime - moral-prime-b" price_index oss | 0.041 [-0.080, 0.165], 20 | rounding |
| 1.5 | prime B row: -0.75 [-1.02, -0.47] / -0.64 [-0.88, -0.40]; -0.38 [-0.51, -0.24] / -0.32 [-0.44, -0.21]; -0.46 [-0.64, -0.27] / -0.25 [-0.34, -0.16]; -0.20 [-0.34, -0.04] / +0.09 [+0.02, +0.19]; +0.20 [+0.05, +0.33] / -0.10 [-0.20, -0.02] | LT "moral-prime-b - moral-placebo", five metrics | -0.754 [-1.021, -0.467] / -0.641 [-0.879, -0.395]; -0.377 [-0.510, -0.237] / -0.321 [-0.442, -0.207]; -0.460 [-0.636, -0.270] / -0.247 [-0.343, -0.157]; -0.197 [-0.341, -0.039] / 0.092 [0.019, 0.188]; 0.198 [0.050, 0.326] / -0.100 [-0.203, -0.021] | rounding |
| 1.5 | prime A row: -0.64 [-0.86, -0.42] / -0.45 [-0.70, -0.21]; -0.32 [-0.43, -0.21] / -0.22 [-0.35, -0.11]; -0.36 [-0.49, -0.21] / -0.16 [-0.28, -0.06]; -0.21 [-0.32, -0.09] / +0.09 [+0.01, +0.20]; +0.20 [+0.07, +0.32] / -0.09 [-0.21, -0.00] | LT "moral-prime - moral-placebo", five metrics | -0.641 [-0.856, -0.419] / -0.446 [-0.700, -0.208]; -0.321 [-0.432, -0.208] / -0.223 [-0.351, -0.110]; -0.357 [-0.490, -0.213] / -0.157 [-0.281, -0.061]; -0.206 [-0.315, -0.090] / 0.087 [0.006, 0.200]; 0.200 [0.071, 0.320] / -0.087 [-0.207, -0.004] | rounding |
| 1.5 | 5-tick row: -0.57 [-0.86, -0.25] / -1.09 [-1.30, -0.89]; -0.29 [-0.43, -0.13] / -0.55 [-0.65, -0.44]; -0.36 [-0.54, -0.17] / -0.60 [-0.71, -0.49]; -0.14 [-0.26, -0.03] / -0.006 [-0.025, +0.009]; -0.03 [-0.16, +0.09] / -0.62 [-0.79, -0.46] | LT "start-5tick - headline-chat (p3)", five metrics | -0.571 [-0.860, -0.250] / -1.093 [-1.296, -0.890]; -0.285 [-0.428, -0.126] / -0.546 [-0.650, -0.443]; -0.358 [-0.537, -0.169] / -0.599 [-0.709, -0.490]; -0.140 [-0.264, -0.030] / -0.006 [-0.025, 0.009]; -0.029 [-0.158, 0.086] / -0.624 [-0.791, -0.459] | rounding |
| 1.5 | nx-chat-p1 column of the compact table | as in Part A (1.1 rows) | as in Part A | match |
| 1.5 | pooled drift +0.10 [+0.05, +0.16] | LED G-repro | +0.104 [0.052, 0.156] | rounding |
| 1.1 | re-signed: -0.22 to -0.56; -0.50 to -0.74; +0.19 [+0.06, +0.32]; +0.13 [+0.06, +0.20] | as in Part A | as in Part A | rounding |
| 2.1 | Qwen fx-ctl-joint minus headline-chat p3 -0.36 [-0.45, -0.27] | PVU Qwen fxj-h3 price_index | -0.3596 [-0.4536, -0.2693] | match |
| 2.1 | like-for-like gap "nearer -0.10" | arithmetic: +0.006 minus the +0.104 drift (LED G-repro) | -0.098 | rounding (interpretation, stated as such) |
| 3.1 | no-numbers no chat -0.38 [-0.47, -0.29]; Qwen -0.70 [-0.75, -0.65] (now signed) | LT "nx-tacit-p1 (p1) - headline-tacit (p1)" price_index | -0.379 [-0.470, -0.286]; -0.698 [-0.746, -0.649] | rounding |
| 3.1 | no chat without numbers falls to 0.008 | PVU nx-tacit-p1 mean_arm | 0.0081 | rounding |
| 3.1 | point 5: 0.19 vs 0.18 | PEN headline-tacit p5 | 0.1948 / 0.1835 | rounding |
| 3.4 | silent high-price rounds 0.4% vs 0.7% | `cot-monitor-threat/ANALYSIS.md` line 98 | 0.004 / 0.007 | match |
| 3.4 | agreement games 100% to 68%, -0.32 [-0.53, -0.11] | COT channel_shift explicit_agreement_any | 1.0 / 0.684, -0.316 [-0.526, -0.105] | rounding |
| 3.4 | three flags give identical -0.32 | COT channel_shift explicit_agreement_any, explicit_proposal_any, conversation_detector_flag_any | -0.3158 each | match |
| 3.4 | agreement flag fires in 18 of 20 compete-instructed games | CA ctl-32b-compete explicit arm_mean, n 20 | 0.90 x 20 = 18 | match |
| 3.4 | agreement-round share +0.02 [+0.01, +0.03] | COT channel_shift explicit_round_share | 0.0199 [0.0077, 0.0337] | rounding |
| 3.4 | messages 13.2 vs 11.6 per round, +1.5 [0.7, 2.5] | COT channel_shift messages_per_round | 13.16 / 11.64, 1.525 [0.715, 2.538] | rounding |
| 3.4 | silent turns 2.6 vs 5.5 per game | COT channel_shift silent_turns | 2.63 / 5.47 | rounding |
| 3.4 | empty-reply drop: 10 pairs, -0.08 [-0.21, +0.02]; 9 pairs dropped | `cot-monitor-threat/sensitivity_empty_talk.csv` price_index | n 10, -0.082 [-0.208, 0.023]; 19 - 10 = 9 | rounding |
| 3.4 | Qwen pgi Holm p 0.009; Qwen price BH q 0.0006 | QCA (as in Part D) | 0.0086; 0.00064 | rounding |
| box T3 / 3.4 | Holm p 0.19 | CA price holm_p | 0.1924 | rounding |
| figures | all ten rebuilt; plotted values unchanged (labels, subtitle and margins only) | `data/fig_*.csv` | unchanged | match |

Review-round counts by row: 42 rows; match 14, rounding 27, not found 1, mismatch 0 (the figure row and the header rows are included).

---

### Part A: sections 1.1, 1.5, 2.1

Abbreviations: **LT** = `out/compare/lever_table.csv` (oss_diff/oss_lo/oss_hi, qwen_diff/qwen_lo/qwen_hi, 3 dp); **PVU** = `out/compare/primed_vs_unprimed.csv` (same contrasts, 4 dp, with mean_arm / mean_control); **CM** = `CLONE/results/oss/ad-hoc/payoff-table-focal-points/cell_means.csv`; **PBA** = `out_t2/step2/tables/payoff_block_arms.csv`; **LED** = `out/step3/claims_ledger.csv`; **RVH** = `CLONE/results/oss/ad-hoc/introspection/replicate_vs_headline_p1.csv`; **Q4** = `CLONE/results/trackm-neutral-2026-10-25/step4/STEP4.md`. "nx-chat" = contrast "nx-chat-p1 (p1) - headline-chat (p1)"; "fxj-fx" = "fx-ctl-joint (p3) - fx-chat-p1 (p1)"; "fxj-h3" = "fx-ctl-joint (p3) - headline-chat (p3)". An estimate with its interval is one row.

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| 1.1 | headline -0.56 (gpt-oss), -0.74 (Qwen) | LT nx-chat price_index oss_diff / qwen_diff | -0.557 / -0.735 | match |
| 1.1 | -0.56 [-0.63, -0.46], 20 pairs | PVU gpt-oss nx-chat price_index diff/lo/hi (LT -0.557 [-0.635, -0.464]) | -0.5567 [-0.6347, -0.4643] | match (LT's -0.635 is -0.6347 to 3 dp) |
| 1.1 | Qwen -0.74 [-0.82, -0.65], 20 pairs | PVU Qwen nx-chat price_index | -0.7353 [-0.8155, -0.6504] | match |
| 1.1 | gpt-oss level 0.02 [0.01, 0.03] | CM gpt-oss nx-chat-p1 price_index | 0.0168 [0.0109, 0.0258] | match |
| 1.1 | Qwen level 0.11 [0.06, 0.17] | CM Qwen nx-chat-p1 price_index | 0.1113 [0.0635, 0.1724] | match |
| 1.1 | five cells: 0.22 to 0.56 on gpt-oss (19 to 20 pairs) | LT payoff-table-focal-points price_index oss_diff, 5 arm-minus-headline rows | -0.302 (n 19), -0.221, -0.365, -0.557, -0.379 | match |
| 1.1 | 0.50 to 0.74 on Qwen; every CI excludes 0 | same rows qwen_diff, CIs | -0.509, -0.630, -0.496, -0.735, -0.698; all CIs < 0 | match (0.496 rounds to 0.50) |
| 1.1 | chat adds +0.19 [0.06, 0.32] gpt-oss | LT communication "chat - tacit (p1)" price_index oss | 0.186 [0.062, 0.315] | rounding (LED G-comm gives +0.19 [0.08, 0.29], the Step 2 stratified draw) |
| 1.1 | Qwen +0.13 [0.06, 0.20] | same row qwen | 0.131 [0.063, 0.204] | match |
| 1.1 | no-chat price index 0.39 (gpt-oss), 0.72 (Qwen) | CM headline-tacit p1 price_index | 0.3875 / 0.7162 | match |
| 1.1 | table spread -1.11 [-1.26, -0.94] (1.03 / 2.15), n 20 | PVU gpt-oss nx-chat market_price_mean | -1.1134 [-1.2641, -0.94]; 1.0336 / 2.147 | match |
| 1.1 | Qwen spread -1.47 [-1.62, -1.29] (1.22 / 2.69) | PVU Qwen nx-chat market_price_mean | -1.4706 [-1.6237, -1.2924]; 1.2226 / 2.6932 | match |
| 1.1 | table price levels (0.02 / 0.57), Qwen (0.11 / 0.85) | PVU mean_arm / mean_control | 0.0168 / 0.5735; 0.1113 / 0.8466 | match |
| 1.1 | pgi -0.74 [-0.82, -0.63] (0.03 / 0.77) | PVU gpt-oss nx-chat profit_gain_index | -0.7359 [-0.8229, -0.6338]; 0.033 / 0.7689 | match |
| 1.1 | Qwen pgi -0.75 [-0.83, -0.66] (0.19 / 0.95) | PVU Qwen | -0.7548 [-0.8322, -0.6626]; 0.1944 / 0.9492 | match |
| 1.1 | comp -0.20 [-0.31, -0.08] (0.23 / 0.43) | PVU gpt-oss competitive_share | -0.199 [-0.3144, -0.0836]; 0.2271 / 0.4261 | match |
| 1.1 | Qwen comp -0.00 [-0.02, +0.02] (0.01 / 0.01), degenerate | PVU Qwen competitive_share | -0.0027 [-0.0249, 0.015]; 0.0075 / 0.0103 | match |
| 1.1 | match +0.14 [-0.02, +0.29] (0.56 / 0.41) | PVU gpt-oss matching_share | 0.1446 [-0.0152, 0.29]; 0.5568 / 0.4122 | match |
| 1.1 | Qwen match -0.23 [-0.36, -0.10] (0.74 / 0.98) | PVU Qwen matching_share | -0.2316 [-0.3625, -0.1048]; 0.7444 / 0.9761 | match |
| 1.1 | firms sit at about 1.01 to 1.05 | CM nx-chat-p1 spread 1.0336 [1.022, 1.0497]; nx-tacit-p1 1.0162 [1.012, 1.022] | 1.01 to 1.05 | rounding |
| 1.1 | Step 2 matching interval [0.00, 0.27] | PBA nx-chat-p1 match_diff_ci | "0.14 [0.00, 0.27]" | match |
| 1.1 | drift about +0.10 | LED G-repro price index | +0.104 [0.052, 0.156] | match |
| 1.1 | smallest cell -0.22 about twice the drift; -0.56 five times | arithmetic on LT and LED | 0.221/0.104 = 2.1; 0.557/0.104 = 5.4 | match |
| 1.1 | game constants: 1.00 to 5.00, 0.01 ticks, 3.00 monopoly, 2.09 never printed, examples 1.00 to 4.00 | Q4 header, orientation and "game in four lines" | same | match |
| 1.5 | 0.56 [0.46, 0.64] (text) | PVU gpt-oss nx-chat price_index | -0.5567 [-0.6347, -0.4643] | **mismatch fixed** -> 0.56 [0.46, 0.63] (same as 1.1; LT shows -0.635, which is -0.6347 to 3 dp) |
| 1.5 | 20 pairs; 0.57 to 0.02 | PVU n_pairs, mean_control / mean_arm | 20; 0.5735 / 0.0168 | match |
| 1.5 | Qwen 0.74 [0.65, 0.82] | PVU Qwen | 0.7353 [0.6504, 0.8155] | match |
| 1.5 | profit drop -0.74 vs -0.76 | PVU profit_gain_index gpt-oss / Qwen | -0.7359 / -0.7548 | **mismatch fixed** -> "-0.74 vs -0.75" |
| 1.5 | prime B minus placebo 0.38 [0.24, 0.51], 19 pairs | LT moral-primes "moral-prime-b - moral-placebo" price_index oss | -0.377 [-0.510, -0.237], n 19 | match (LED gives [-0.49, -0.25], a different draw) |
| 1.5 | Qwen prime B 0.32 [0.21, 0.44] | same row qwen | -0.321 [-0.442, -0.207] | match |
| 1.5 | prime A 0.32 [0.21, 0.43] | LT "moral-prime - moral-placebo" oss | -0.321 [-0.432, -0.208] | match |
| 1.5 | Qwen prime A 0.22 [0.11, 0.35] | same row qwen | -0.223 [-0.351, -0.110] | match |
| 1.5 | 5-tick -0.29 [-0.43, -0.13] vs -0.55 [-0.65, -0.44]; "about half" | LT five-tick-start "start-5tick - headline-chat (p3)" price_index | oss -0.285 [-0.428, -0.126]; qwen -0.546 [-0.650, -0.443]; ratio 0.52 | rounding (-0.285 to -0.29) |
| 1.5 | 5-tick is the Qwen Step 4 pick | Q4 section 1.5 heading | "Capping the first quote near the floor removes the most collusion" | match |
| 1.5 | table spread -1.11 [-1.26, -0.94] (2.15 to 1.03); Qwen -1.47 [-1.62, -1.29] (2.69 to 1.22) | PVU market_price_mean | as in 1.1 | match |
| 1.5 | table price -0.56 [-0.64, -0.46] | PVU | -0.5567 [-0.6347, -0.4643] | **mismatch fixed** -> [-0.63, -0.46] |
| 1.5 | table price Qwen -0.74 [-0.82, -0.65] (0.85 to 0.11) | PVU Qwen | as in 1.1 | match |
| 1.5 | table pgi -0.74 [-0.82, -0.63] (0.77 to 0.03); Qwen -0.75 [-0.83, -0.66] (0.95 to 0.19) | PVU | as in 1.1 | match |
| 1.5 | comp -0.20 [-0.31, -0.08]; Qwen -0.00 [-0.02, +0.02], levels 0.010 and 0.008 | PVU competitive_share | as in 1.1; Qwen 0.0103 / 0.0075 | match |
| 1.5 | match +0.14 [-0.02, +0.29]; Qwen -0.23 [-0.36, -0.10] | PVU matching_share | as in 1.1 | match |
| 1.5 | gpt-oss no-numbers quotes mean 1.03 | CM nx-chat-p1 market_price_mean | 1.0336 | match |
| 1.5 | headline re-run in that root +0.07 [-0.02, +0.16] | RVH "hrep-nx-chat-p1 (headline-prompt replicate) - headline-chat (p1)" price_index | 0.067 [-0.018, 0.156] | match (source now named in the Terms table) |
| 1.5 | pooled +0.10 [0.05, 0.16] over 99 pairs | LED G-repro | +0.104 [0.052, 0.156], 99 pairs | match |
| 1.5 | fx-ctl-joint 0.62 [0.49, 0.73] | CM gpt-oss fx-ctl-joint price_index | 0.6185 [0.493, 0.7277] | match |
| 1.5 | level with headline chat +0.01 [-0.11, +0.12] | PVU gpt-oss fxj-h3 price_index | 0.0057 [-0.1096, 0.1166] | match |
| 1.5 | theory level 0.703 at p1; 2.09; example prices 1.00, 1.50 ... 4.00 | Q4 metrics box (theta* 0.703 / 0.546 / 0.325 / 0) | same | match |
| 2.1 | headline +0.34 | LT fxj-fx price_index oss | 0.338 | match |
| 2.1 | 0.22 to 0.56 / 0.50 to 0.74; chat +0.19 [0.06, 0.32] / +0.13 [0.06, 0.20] | as in 1.1 | as in 1.1 | match (chat: rounding, as in 1.1) |
| 2.1 | +0.34 [0.15, 0.52], 19 pairs | PVU gpt-oss fxj-fx price_index | 0.3383 [0.1504, 0.5179], n 19 | match |
| 2.1 | Qwen +0.07 [-0.02, +0.17], 20 pairs | PVU Qwen fxj-fx price_index | 0.0683 [-0.0248, 0.1671] | match |
| 2.1 | gpt-oss reaches 0.62 [0.49, 0.73] | CM gpt-oss fx-ctl-joint | 0.6185 [0.493, 0.7277] | match |
| 2.1 | level with p3 chat +0.01 [-0.11, +0.12] | PVU gpt-oss fxj-h3 | 0.0057 [-0.1096, 0.1166] | match |
| 2.1 | Qwen reaches 0.41 [0.31, 0.50] | CM Qwen fx-ctl-joint | 0.4055 [0.3093, 0.498] | match |
| 2.1 | Qwen 0.36 [0.27, 0.45] below its own | PVU Qwen fxj-h3 price_index | -0.3596 [-0.4536, -0.2693] | match |
| 2.1 | table spread +0.68 [+0.29, +1.05] (2.22 / 1.54), n 19 | PVU gpt-oss fxj-fx market_price_mean | 0.6766 [0.2876, 1.0454]; 2.219 / 1.5424 | match |
| 2.1 | Qwen spread +0.14 [-0.06, +0.33] (1.81 / 1.67), n 20 | PVU Qwen | 0.1365 [-0.0609, 0.331]; 1.811 / 1.6745 | match |
| 2.1 | price levels (0.61 / 0.27); Qwen (0.41 / 0.34) | PVU mean_arm / mean_control | 0.6095 / 0.2712; 0.4055 / 0.3372 | match |
| 2.1 | pgi +0.40 [+0.19, +0.61] (0.76 / 0.36) | PVU gpt-oss profit_gain_index | 0.4014 [0.1868, 0.6062]; 0.7635 / 0.3621 | match |
| 2.1 | Qwen pgi +0.07 [-0.05, +0.18] (0.60 / 0.54) | PVU Qwen | 0.0656 [-0.0485, 0.1788]; 0.6015 / 0.5359 | match |
| 2.1 | comp -0.11 [-0.19, -0.01] (0.19 / 0.30) | PVU gpt-oss competitive_share | -0.1088 [-0.1937, -0.0142]; 0.1886 / 0.2974 | match |
| 2.1 | Qwen comp -0.00 [-0.00, +0.00] (0.00 / 0.00), degenerate | PVU Qwen | -0.0013 [-0.0039, 0.0]; 0.0 / 0.0013 | match |
| 2.1 | match +0.09 [-0.01, +0.18] (0.49 / 0.40) | PVU gpt-oss matching_share | 0.0851 [-0.0094, 0.1812]; 0.4856 / 0.4006 | match |
| 2.1 | Qwen match -0.09 [-0.21, +0.01] (0.90 / 0.99) | PVU Qwen | -0.0887 [-0.2122, 0.0071]; 0.8981 / 0.9868 | match |
| 2.1 | drift +0.10, about a third of this effect | LED G-repro; 0.104 / 0.338 | 0.31 | match |
| 2.1 | theory price index 0.70 at p1, 0.55 at p3 | Q4 metrics box | 0.703 / 0.546 | match |
| 2.1 | examples 1.00 to 4.00 | Q4 | same | match |

### Part B: sections 1.2, 3.2

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| 1.2 | gpt-oss price -0.23 [-0.29, -0.17], n 18 (text + table) | lever_table.csv cheater "n3-cheater - n3-group" price_index oss_diff/lo/hi/n | -0.232 [-0.286, -0.173], 18 | match (text said "lowers by 0.23 [-0.29, -0.17]": sign style fixed to "-0.23") |
| 1.2 | Qwen price -0.30 [-0.36, -0.25], n 20 | same row qwen_* | -0.305 [-0.362, -0.248], 20; ad-hoc -0.3049 | rounding (sign style fixed as above) |
| 1.2 | Qwen matching -0.42 | same contrast matching_share qwen_diff | -0.415 (ad-hoc -0.4150) | rounding |
| 1.2 | Qwen competitive +0.31 | competitive_share qwen_diff | 0.306 | match |
| 1.2 | LLM quote 2.07 / 2.05 / 1.99, 16 games | ad-hoc cheater/event_time_gptoss.csv mean_llm_quote, n_games_llm_quote | 2.071 / 2.051 / 1.995, 16 | **mismatch fixed** (1.99 -> 1.995) |
| 1.2 | n3-group - headline p3 gpt-oss +0.01 [-0.08, +0.11], 18 | lever_table cheater "n3-group - headline-chat (p3)" price_index oss | 0.006 [-0.083, 0.107], 18 | rounding |
| 1.2 | same, Qwen -0.09 [-0.20, +0.01], 20 | same row qwen | -0.090 [-0.195, 0.008], 20 | rounding |
| 1.2 | table spread gpt-oss -0.46 [-0.57, -0.35]; Qwen -0.61 [-0.73, -0.50] | lever_table cheater n3-cheater - n3-group market_price_mean | -0.463 [-0.574, -0.350]; -0.610 [-0.730, -0.498] | match |
| 1.2 | table pgi gpt-oss -0.33 [-0.43, -0.23]; Qwen -0.44 [-0.52, -0.35] | profit_gain_index row | -0.330 [-0.429, -0.231]; -0.439 [-0.524, -0.353] | match |
| 1.2 | table comp gpt-oss -0.07 [-0.18, +0.05]; Qwen +0.31 [+0.20, +0.42] | competitive_share row | -0.067 [-0.176, 0.047]; 0.306 [0.203, 0.423] | match |
| 1.2 | table matching gpt-oss +0.06 [-0.10, +0.22]; Qwen -0.42 [-0.54, -0.29] | matching_share row | 0.059 [-0.097, 0.215]; -0.415 [-0.541, -0.294] | match / rounding |
| 1.2 | n 18 gpt-oss / 20 Qwen | lever_table oss_n / qwen_n; out/step3/missing_games.csv (2 n3-group EmptyContent: w0 s42, w2 s133) | 18 / 20; 2 rows | match |
| 1.2 | vs headline-chat p3: gpt-oss -0.23 [-0.30, -0.15], 20 pairs | lever_table cheater "n3-cheater - headline-chat (p3)" price_index oss | -0.233 [-0.299, -0.147], 20 | **mismatch fixed** (CI was attributed to contrasts_all; contrasts_all gives -0.23286 [-0.29377, -0.15777]; text now names both) |
| 1.2 | p 0.0001, BH q 0.0007, 268 tests | contrasts_all.csv n3-cheater price: p, bh_q, family_m | 9.999e-05, 0.00067, 268 | match |
| 1.2 | vs headline-chat p3 Qwen -0.40 [-0.49, -0.31] | lever_table same row qwen | -0.395 [-0.490, -0.308] | rounding |
| 1.2 | point 3 theory level 0.546 | Qwen STEP4.md metrics box (theta* p3) | 0.546 | match |
| 1.2 | direction | claims_ledger G-cheater: lower on gpt-oss, smaller than Qwen, no matching-to-undercutting switch | same | match |
| 3.2 | gpt-oss price -0.22 [-0.35, -0.10], n 15 | ethics-rule/standard_metrics.csv n3-ethics - n3-group (p3) price_index (= lever_table) | -0.2234 [-0.3486, -0.1023], 15 | match (sign style fixed: "lowers by 0.22" -> "changes by -0.22") |
| 3.2 | Qwen price +0.02 [-0.06, +0.10], 20 | same, Qwen | 0.0161 [-0.0605, 0.0975], 20 | rounding |
| 3.2 | matching -0.19 / -0.17; competitive +0.17 / +0.10 | same file matching_share / competitive_share diff | -0.1933 / -0.1750; 0.1745 / 0.0995 | rounding |
| 3.2 | table spread -0.45 [-0.71, -0.20]; Qwen +0.03 [-0.14, +0.19] | market_price_mean rows | -0.4468 [-0.7079, -0.2000]; 0.0322 [-0.1354, 0.1928] | match |
| 3.2 | table pgi -0.26 [-0.42, -0.11]; Qwen +0.01 [-0.06, +0.07] | profit_gain_index rows | -0.2629 [-0.4229, -0.1052]; 0.0075 [-0.0555, 0.0680] | rounding |
| 3.2 | table comp +0.17 [+0.06, +0.27]; Qwen +0.10 [+0.03, +0.22] | competitive_share rows | 0.1745 [0.0616, 0.2744]; 0.0995 [0.0307, 0.2155] | rounding |
| 3.2 | table matching -0.19 [-0.28, -0.12]; Qwen -0.17 [-0.29, -0.09] | matching_share rows | -0.1933 [-0.2770, -0.1151]; -0.1750 [-0.2865, -0.0858] | rounding |
| 3.2 | Replicates? share metrics "similar" | Qwen comp 0.10 inside gpt-oss [0.06, 0.27]; Qwen match -0.17 inside [-0.28, -0.12] | true | match |
| 3.2 | asks+report minus asks -0.06 [-0.16, +0.03] (ad hoc) | watchdog/standard_metrics.csv wd-noncomp - wd-ask-noreport price_index gpt-oss | -0.0562 [-0.1575, 0.0291] | match; omission fixed: Step 2 contrasts_all gives -0.056 [-0.097, -0.013] BH q 0.052 and pgi -0.074 [-0.124, -0.022] q 0.024 (ledger G-watchdog); added to text |
| 3.2 | Qwen notice-only -0.06 [-0.12, -0.001] | watchdog/standard_metrics wd-notice-only - headline-chat (p1) Qwen price_index | -0.0583 [-0.1168, -0.0014] | match |
| 3.2 | report threat adds nothing: gpt-oss -0.01 [-0.11, +0.06]; Qwen -0.01 [-0.08, +0.05] | wd-noncomp - wd-notice-only price_index | -0.0150 [-0.1055, 0.0597]; -0.0150 [-0.0824, 0.0538] (contrasts_all gpt-oss -0.014953) | rounding |
| 3.2 | gpt-oss every watchdog arm vs headline CI includes 0 | watchdog/standard_metrics notice -0.022 [-0.128, 0.091]; ask-noreport +0.038 [-0.054, 0.130]; contrasts_all wd-noncomp vs headline -0.025 [-0.118, 0.069] | all include 0 | match |
| 3.2 | n3-ethics - headline p3: -0.27 [-0.38, -0.15], 17 pairs, p 0.0001, q 0.0007, 268 | contrasts_all n3-ethics price est/lo/hi/n/p/bh_q/family_m | -0.27116 [-0.38464, -0.1539], 17, 9.999e-05, 0.00067, 268 | match |
| 3.2 | Qwen same contrast -0.07 [-0.15, +0.01] | contrasts_all qwen_est/lo/hi | -0.0741 [-0.1457, 0.0065] | rounding |
| 3.2 | Qwen n3-group matches 99%, undercuts 0.4%; gpt-oss 38% / 41% | ethics-rule/standard_metrics mean_control (matching / competitive) | 0.992 / 0.0036; 0.381 / 0.412 | match |
| 3.2 | n3-group alone: gpt-oss +0.01 [-0.08, +0.11], Qwen -0.09 [-0.20, +0.01] | lever_table cheater n3-group - headline-chat (p3) price_index | 0.006 [-0.083, 0.107]; -0.090 [-0.195, 0.008] | rounding |
| 3.2 | three n3-ethics and two n3-group games failed (empty reply) | out/step3/missing_games.csv | 3 + 2 EmptyContent rows | match |
| 3.2 | 8 of the 17 finished n3-ethics games had a truncated call | claims_ledger G-n3ethics main caveat | "8 of 17 had a truncated call" | match |
| 3.2 | MDE about 0.19 (price, 80%, n 15) | ethics-rule/mde_and_ci.csv gpt-oss price_index mde_80pct | 0.1897 | match |
| 3.2 | drop 9 empty-talk pairs: 6 pairs, -0.17 [-0.36, +0.01] | ethics-rule/sensitivity_empty_talk.csv price_index pairs_dropped/n_pairs/diff/lo/hi | 9, 6, -0.172 [-0.358, 0.011] | match |
| 3.2 | "about a fifth of the floor-to-monopoly range" | price diff -0.22 on a 0-1 index | 0.22 | match |
| 3.2 | direction | claims_ledger G-n3ethics (lowers gpt-oss, not Qwen) and G-watchdog (null vs headline; method-dependent asks+report minus asks) | same | match |

### Part C: sections 1.3, 2.2 and not addressed (1.4, 3.3)

Sources: DT = `CLONE/results/oss/ad-hoc/detection-transfer/detection_transfer.csv` (label `c_outcome` unless stated); PD = `price_detector_transfer.csv`; RF = `refit_within_gptoss_sensitivity.csv`; QL = Qwen `results/trackm-neutral-2026-10-25/step3/claims_ledger.csv`; GL = `out/step3/claims_ledger.csv`; S2 = `out_t2/step2/REPORT.md`. Populations: Qh = "Qwen headline-chat+monitored, held-out half"; Gh = "headline-chat (p1,p3,p5)"; GB = "B: all non-bug chat arms of the final data".

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| 1.3 | Mean quote AUC gpt-oss headline 0.81 [0.67, 0.93] (text, table, headline) | DT Gh, quotes: mean level, auc | 0.8136 [0.6730, 0.9311] | match |
| 1.3 | 57 games, 0.61 positive | DT Gh n / prevalence | 57 / 0.614 | match |
| 1.3 | Mean quote AUC all chat arms 0.91 [0.87, 0.94] | DT GB, quotes: mean level | 0.9104 [0.8721, 0.9420] | match |
| 1.3 | 524 games, 0.55 positive | DT GB n / prevalence | 524 / 0.5496 | match |
| 1.3 | Qwen mean quote AUC 0.90 [0.84, 0.95] (text and table) | DT Qh, quotes: mean level | 0.9018 [0.8388, 0.9449] | **mismatch fixed** (upper bound 0.95 -> 0.94) |
| 1.3 | 145 held-out games, 0.90 positive | DT Qh n / prevalence | 145 / 0.8966 | match |
| 1.3 | Frozen cut-off 0.498 | DT thr, quotes: mean level | 0.49833 | match |
| 1.3 | gpt-oss headline recall 0.71 [0.58, 0.88] | DT Gh mean level recall | 0.7143 [0.5814, 0.875] | rounding |
| 1.3 | gpt-oss headline FPR 0.18 [0.05, 0.33] | DT Gh mean level fpr | 0.1818 [0.0455, 0.3333] | match |
| 1.3 | Qwen recall 0.98 [0.95, 1.00] | DT Qh mean level recall | 0.9846 [0.9516, 1.0] | match |
| 1.3 | Qwen FPR 0.40 [0.25, 0.67] | DT Qh mean level fpr | 0.40 [0.25, 0.6667] | match |
| 1.3 | All-arm recall 0.85 [0.79, 0.89] | DT GB mean level recall | 0.8472 [0.7895, 0.8932] | match |
| 1.3 | All-arm FPR 0.14 [0.09, 0.18] | DT GB mean level fpr | 0.1356 [0.0882, 0.1782] | match |
| 1.3 | Qwen quote feats + LR AUC 0.85 [0.78, 0.91] | DT Qh quotes: quote feats + LR | 0.8503 [0.7748, 0.9122] | **mismatch fixed** (lower bound 0.78 -> 0.77) |
| 1.3 | Qwen feats + LR recall 0.93 [0.89, 0.97], FPR 0.60 [0.36, 0.90] | DT Qh same row | 0.9308 [0.8855, 0.9688]; 0.60 [0.3636, 0.90] | match |
| 1.3 | gpt-oss feats + LR AUC 0.83 [0.71, 0.94] | DT Gh quotes: quote feats + LR | 0.8279 [0.7072, 0.9369] | match |
| 1.3 | gpt-oss feats + LR recall 0.83 [0.70, 0.94], FPR 0.18 [0.05, 0.33] | DT Gh same row | 0.8286 [0.70, 0.9429]; 0.1818 [0.0476, 0.3333] | match |
| 1.3 | Qwen rules score AUC 0.39 [0.24, 0.62] | DT Qh text: rules score | 0.3874 [0.2354, 0.6206] | match |
| 1.3 | Qwen rules recall 0.72 [0.62, 0.82], FPR 0.93 [0.76, 1.00] | DT Qh same row | 0.7231 [0.6239, 0.8208]; 0.9333 [0.7647, 1.0] | match |
| 1.3 | gpt-oss rules AUC 0.54 [0.38, 0.69] | DT Gh text: rules score | 0.5351 [0.3801, 0.6900] | match |
| 1.3 | gpt-oss rules recall 1.00 [1.00, 1.00], FPR 0.95 [0.87, 1.00] | DT Gh same row | 1.0 [1.0, 1.0]; 0.9545 [0.8710, 1.0] | match |
| 1.3 | Price flag headline: 0 of 57, recall 0.00 [0.00, 0.00], FPR 0.00 [0.00, 0.00] | PD Gh c_outcome flag_rate / recall / fpr | 0.0 / 0.0 [0, 0] / 0.0 [0, 0] | match |
| 1.3 | Price flag all arms recall 0.02 [0.01, 0.04], FPR 0.004 [0.00, 0.01] | PD GB c_outcome | 0.0243 [0.0074, 0.0412]; 0.00424 [0.0, 0.0140] | match |
| 1.3 | Price flag 2 of 20 joint-profit control games | PD "flag rate in ctl-32b-joint", n 20, flag_rate | 0.1 x 20 = 2 | match |
| 1.3 | Price flag rule: level 0.8, 2 rounds, tolerance 0.25 | detection_transfer.py line 118 (level_min 0.8, window 2, tol 0.25) | same | match |
| 1.3 | Label: rounds 4 onwards, price index >= 0.5 | detection_transfer.py lines 90, 121 (late_level >= 0.5) | 0.5 | match |
| 1.3 | Bootstrap draws 2,000 (AUC), 1,000 (recall, FPR) | detection_transfer.py line 17 (B = 2000), line 81 (1000) | same | match |
| 1.3 | Qwen price flag: 0 of 20 joint-profit control games, thinking on | QL rank 9, evidence column | "0/20 (on) of the maximise-joint-profit control games" | match |
| 1.3 | Control separation AUC 1.00, 40 games (20 of each), both models | DT label a_instructed, quotes: mean level / quote feats + LR, both models | 1.0, n 40, prevalence 0.5 | match |
| 1.3 | "0.81 to 0.91 against 0.90" (why it matters) | as above | 0.81, 0.91, 0.90 | match |
| 1.3 | Chance 0.5 / perfect 1.0 (definition) | definition | n/a | match |
| 1.3 | Direction: quote detector transfers, keyword / price flag do not | GL G-detect-quotes, G-detect-text | same direction | match |
| 2.2 | Text alone gpt-oss headline AUC 0.65 [0.50, 0.79] | DT Gh text: TF-IDF + LR | 0.6545 [0.5029, 0.7870] | match |
| 2.2 | Text alone all arms 0.71 [0.66, 0.75] | DT GB text: TF-IDF + LR | 0.7069 [0.6595, 0.7513] | match |
| 2.2 | Text alone Qwen 0.71 [0.55, 0.84] | DT Qh text: TF-IDF + LR | 0.7144 [0.5463, 0.8425] | match |
| 2.2 | Quotes alone 0.81 [0.67, 0.93], 0.91 [0.87, 0.94] | DT Gh / GB mean level | as in 1.3 | match |
| 2.2 | Qwen quotes alone 0.90 [0.84, 0.95] (text and table) | DT Qh mean level | 0.9018 [0.8388, 0.9449] | **mismatch fixed** (-> [0.84, 0.94]) |
| 2.2 | Both gpt-oss headline 0.84 [0.71, 0.94] | DT Gh both: quotes + TF-IDF + LR | 0.8364 [0.7099, 0.9382] | match |
| 2.2 | Both all arms 0.90 [0.86, 0.93] | DT GB both: quotes + TF-IDF + LR | 0.9024 [0.8645, 0.9334] | match |
| 2.2 | Both Qwen 0.90 [0.84, 0.95] (table) | DT Qh both: quotes + TF-IDF + LR | 0.9010 [0.8433, 0.9449] | **mismatch fixed** (-> [0.84, 0.94]) |
| 2.2 | Both minus quotes Qwen -0.001 [-0.029, +0.038]; text -0.00 [-0.03, +0.04] | DT Qh DIFF both minus quotes | -0.00077 [-0.0286, +0.0376] | match |
| 2.2 | Both minus quotes headline +0.023 [-0.030, +0.088]; text +0.02 [-0.03, +0.09] | DT Gh DIFF ... minus quotes | +0.0227 [-0.0300, +0.0882] | match |
| 2.2 | Both minus quotes all arms -0.008 [-0.025, +0.009] (table) | DT GB DIFF ... minus quotes | -0.0080 [-0.0249, +0.0085] | match |
| 2.2 | Same, text form -0.01 [-0.03, +0.01] | DT GB DIFF ... minus quotes | -0.0080 [-0.0249, +0.0085] | **mismatch fixed** (lower bound -0.03 -> -0.02) |
| 2.2 | Both minus text Qwen +0.187 [+0.098, +0.305] (table) | DT Qh DIFF ... minus text | +0.1867 [+0.0978, +0.3048] | match |
| 2.2 | Same, text form +0.19 [+0.10, +0.31] | DT Qh DIFF ... minus text | +0.1867 [+0.0978, +0.3048] | **mismatch fixed** (upper bound +0.31 -> +0.30) |
| 2.2 | Both minus text headline +0.182 [+0.052, +0.330]; +0.18 [+0.05, +0.33] | DT Gh DIFF ... minus text | +0.1818 [+0.0517, +0.3302] | match |
| 2.2 | Both minus text all arms +0.196 [+0.145, +0.248]; +0.20 [+0.15, +0.25] | DT GB DIFF ... minus text | +0.1955 [+0.1454, +0.2477] | match |
| 2.2 | Text recall/FPR Qwen 0.65 [0.56, 0.75] / 0.33 [0.17, 0.55] | DT Qh TF-IDF recall / fpr | 0.6538 [0.5603, 0.7537] / 0.3333 [0.1667, 0.5457] | match |
| 2.2 | Text recall/FPR headline 0.11 [0.03, 0.22] / 0.00 [0.00, 0.00] | DT Gh TF-IDF | 0.1143 [0.0278, 0.2188] / 0.0 [0, 0] | match |
| 2.2 | Text recall/FPR all arms 0.11 [0.06, 0.16] / 0.02 [0.00, 0.04] | DT GB TF-IDF | 0.1076 [0.0599, 0.1579] / 0.0169 [0.0040, 0.0351] | match |
| 2.2 | Quotes recall/FPR (three populations) | DT mean level rows | as in 1.3 | match / rounding (0.875 -> 0.88) |
| 2.2 | Both recall/FPR Qwen 0.81 [0.70, 0.89] / 0.20 [0.06, 0.42] | DT Qh both TF-IDF | 0.8077 [0.6982, 0.8923] / 0.20 [0.0556, 0.4167] | match |
| 2.2 | Both recall/FPR headline 0.69 [0.53, 0.83] / 0.14 [0.00, 0.28] | DT Gh both TF-IDF | 0.6857 [0.5312, 0.8334] / 0.1364 [0.0, 0.2778] | match |
| 2.2 | Both recall/FPR all arms 0.80 [0.72, 0.86] / 0.07 [0.04, 0.10] | DT GB both TF-IDF | 0.7986 [0.7237, 0.8613] / 0.0678 [0.0381, 0.0977] | match |
| 2.2 | Games and positives 145 (0.90), 57 (0.61), 524 (0.55) | DT n / prevalence | as in 1.3 | match |
| 2.2 | Cut-off 0.498 | DT thr | 0.49833 | match |
| 2.2 | "+0.02 and -0.01, intervals within about +/- 0.09" | DT Gh / GB DIFF minus quotes | +0.023 [-0.030, +0.088]; -0.008 [-0.025, +0.009] | match |
| 2.2 | Refit: both minus mean quote headline -0.10 [-0.22, +0.01] | RF Gh, DIFF both(CV) minus quotes: mean level | -0.0955 [-0.2167, +0.0090] | match |
| 2.2 | Refit: all arms +0.01 [-0.00, +0.03] | RF GB, same row | +0.0130 [-0.0014, +0.0292] | match |
| 2.2 | Text recall 0.65 on Qwen to 0.11 on gpt-oss | DT TF-IDF recall Qh / Gh | 0.6538 / 0.1143 | match |
| 2.2 | Chat-derived label prevalence headline 0.98 | DT Gh b_agreement prevalence | 0.9825 | match |
| 2.2 | Chat label, all arms both minus quotes -0.065 [-0.114, -0.023] | DT GB b_agreement DIFF minus quotes | -0.0648 [-0.1137, -0.0230] | match |
| 2.2 | Chat label, Qwen +0.105 [+0.007, +0.273] | DT Qh b_agreement DIFF minus quotes | +0.1050 [+0.0065, +0.2726] | match |
| 2.2 | Bootstrap draws 2,000 / 1,000 | detection_transfer.py lines 17, 81 | same | match |
| 2.2 | Direction: combining adds nothing over quotes | GL G-detect-quotes ("adding the frozen text model adds nothing") | same | match |
| 1.4 | 819 completed gpt-oss games | S2 line 3 ("819 of 840 planned games DONE") | 819 | match |
| 3.3 | (no numbers besides the sub-question number) | n/a | n/a | n/a |
| all | Question texts 1.3, 2.2, 1.4, 3.3 | `CLONE/alignment/AREAS_TO_SPRINT_OBJECTIVES.md` lines 18 to 20 | verbatim short forms | match |

### Part D: sections 2.3, 3.1, 3.4

Sources: CA = `out_t2/step2/tables/contrasts_all.csv` (gpt-oss `est/lo/hi`, Qwen `qwen_est/qwen_lo/qwen_hi`); QCA = Qwen `results/trackm-neutral-2026-10-25/step2/tables/contrasts_all.csv`; CTL = `results/oss/ad-hoc/controls/`; PEN = `results/oss/ad-hoc/penalty/cells.csv`; REP = `results/oss/ad-hoc/reproducibility/`; COT = `results/oss/ad-hoc/cot-monitor-threat/`; DFR = Step 2 `tables/detector_flag_rates.csv`; DT = `results/oss/ad-hoc/detection-transfer/detection_transfer.csv`; LT = `out/compare/lever_table.csv`; PVU = `out/compare/primed_vs_unprimed.csv`; LED = `out/step3/claims_ledger.csv`.

| Section | Number in text | Source file, row/column | Source value | Result |
|---|---|---|---|---|
| 2.3 | headline 0.61 (chat above compete, gpt-oss) | CA ctl-32b-compete vs headline-chat p3, price, est | -0.60743 | rounding |
| 2.3 | headline Qwen 0.77 | CA same row, qwen_est | -0.76513 | rounding |
| 2.3 | 0.61 [0.54, 0.67], 20 pairs | CA same row est/lo/hi/n | -0.607 [-0.667, -0.543], 20 | rounding |
| 2.3 | Qwen 0.77 [0.71, 0.82] | CA same row qwen_* | -0.765 [-0.820, -0.708] | rounding |
| 2.3 | joint above compete 0.74 (Qwen 0.725) | CTL standard_metrics joint - compete, price_index | 0.739 / 0.725 | rounding / match |
| 2.3 | price flag 0 of 60 private-chat games | DFR headline-chat price_flag | 0/60 | match |
| 2.3 | price flag 2 of 20 joint-control games | DFR ctl-32b-joint | 2/20 | match |
| 2.3 | conversation flag 19 of 20 compete games | DFR ctl-32b-compete conv_flag | 19/20 | match |
| 2.3 | AUC 0.81 [0.67, 0.93], 57 games | DT quotes: mean level, headline-chat; LED G-detect-quotes | 0.81 [0.67, 0.93], 57 | match |
| 2.3 | Qwen AUC 0.90 [0.84, 0.95] | DT Qwen held-out half, quotes: mean level | 0.9018 [0.8388, 0.9449] | **mismatch fixed** at assembly (-> [0.84, 0.94], as in 1.3 and 2.2) |
| 2.3 | 1 of 99 identical | REP identity_summary ALL same_quote_sequence | 1 of 99 | match |
| 2.3 | replicates +0.10 [+0.05, +0.16] | REP ANALYSIS.md line 7; LED G-repro | +0.104 [0.052, 0.156] | rounding |
| 2.3 | chat baseline 0.61 vs Qwen 0.77 (levels) | CTL cell_means headline-chat price_index | 0.6127 / 0.7651 | rounding |
| 2.3 | spread -1.21 [-1.33, -1.08], 20 | CA compete, spread | -1.2149 [-1.3308, -1.0779] | rounding |
| 2.3 | Qwen spread -1.53 [-1.64, -1.42] | CA qwen_* | -1.5303 [-1.6421, -1.4171] | rounding |
| 2.3 | price -0.61 [-0.67, -0.54] | CA price | -0.6074 [-0.6667, -0.5427] | rounding |
| 2.3 | Qwen price -0.77 [-0.82, -0.71] | CA qwen_* | -0.7651 [-0.8202, -0.7083] | rounding |
| 2.3 | pgi -0.80 [-0.86, -0.72] | CA pgi | -0.7978 [-0.8650, -0.7169] | rounding |
| 2.3 | Qwen pgi -0.92 [-0.95, -0.88] | CA qwen_* | -0.9163 [-0.9461, -0.8836] | rounding |
| 2.3 | comp +0.55 [+0.48, +0.61] | CA comp | 0.5499 [0.4846, 0.6126] | rounding |
| 2.3 | Qwen comp +0.99 [+0.97, +1.00] | CA qwen_* | 0.9887 [0.9718, 1.0] | rounding |
| 2.3 | Qwen control 1.00 competitive, Qwen chat 0.01 | CTL cell_means Qwen compete / headline-chat competitive_share | 1.0 / 0.0113 | rounding |
| 2.3 | match -0.38 [-0.43, -0.32] | CA match | -0.3759 [-0.4304, -0.3227] | rounding |
| 2.3 | Qwen match -0.97 [-0.99, -0.95]; control matching 0.00 | CA qwen_*; CTL Qwen compete matching_share | -0.9715 [-0.9923, -0.9465]; 0.0 | rounding / match |
| 2.3 | n 20 pairs (all rows, both models) | CA n, qwen_n | 20 / 20 | match |
| 2.3 | compete level price 0.005, pgi 0.007 | CTL cell_means ctl-32b-compete | 0.00532 / 0.00668 | rounding |
| 2.3 | joint minus compete 0.74 [0.72, 0.75] | CTL standard_metrics gpt-oss price_index | 0.739 [0.723, 0.755] | rounding |
| 2.3 | Qwen 0.725 [0.69, 0.75] | CTL standard_metrics Qwen | 0.725 [0.6875, 0.75] | rounding |
| 2.3 | typical replicate gap 0.22 | REP ANALYSIS.md (pooled mean abs diff, price index) | 0.216 | rounding |
| 2.3 | correlation 0.21 | REP ANALYSIS.md line 123 | 0.21 | match |
| 2.3 | self-score mean 1.09 (about 1 of 5) | Step 2 self_scores.csv d-conflict score_mean; LED Q4-conflict | 1.091 | rounding |
| 2.3 | Qwen self-score 1.00 | Qwen step2 REPORT.md line 375 (1.004 thinking on) | 1.004 | rounding |
| 2.3 | MDE 0.12 (chat p1) to 0.20 (tacit p1; chat p5) | REP ANALYSIS.md line 7 | about 0.12 / about 0.20 | match |
| 2.3 | chat 0.13 [0.07, 0.20] below joint ceiling | CA ctl-32b-joint vs headline-chat p3, price | 0.1316 [0.0695, 0.1993] | rounding |
| 2.3 | Qwen chat at ceiling | CA same row qwen_* | -0.040 [-0.090, +0.011] (includes 0) | match |
| 2.3 | replicate offset +0.10 | as above | +0.104 | rounding |
| 2.3 | 5 paraphrases x 4 seeds = 20; at most 20 rounds; penalty 1 to 5 | design (Qwen STEP4 header) | 20 pairs, 20 rounds | match |
| 2.3 | 2.8 x SD / sqrt(20) (MDE formula) | definition | n/a | match (definition) |
| 2.3 | Replicates "in sign only" on all five, neither estimate inside the other's CI | CA rows above (checked each pair of intervals) | none inside | match |
| 2.3 | direction | LED G-ctl ("compete minus chat p3 pgi -0.80 [-0.86, -0.72]"; chat 0.13 below joint) | same sign | match |
| 3.1 | no chat p1 price 0.39 [0.29, 0.48] | PEN gpt-oss headline-tacit p1 price_index | 0.3875 [0.2897, 0.4794] | rounding |
| 3.1 | compete 0.005 [0.000, 0.016] | CTL cell_means gpt-oss ctl-32b-compete price_index | 0.00532 [0.0, 0.01596] | rounding |
| 3.1 | Qwen no chat 0.72 [0.67, 0.76] | PEN Qwen headline-tacit p1 | 0.7162 [0.6664, 0.7644] | rounding |
| 3.1 | theory sustainable 0.70 / 0.703 at p1, 0 at p5 | Qwen STEP4 header (theta*) | 0.703 / 0 | match |
| 3.1 | 68% vs 38% competitive share | PEN competitive_share gpt-oss / Qwen tacit p1 | 0.6811 / 0.3762 | rounding (wording fixed: "plays competitively", not "undercuts") |
| 3.1 | no-numbers no-chat -0.38 [0.29, 0.47] magnitude, to 0.008 | LT nx-tacit-p1 - headline-tacit, price_index oss; PVU level | -0.379 [-0.470, -0.286]; 0.0081 | rounding |
| 3.1 | Qwen -0.70 [0.65, 0.75] | LT same row qwen_* | -0.698 [-0.746, -0.649] | rounding |
| 3.1 | 20 pairs each | LT oss_n / qwen_n | 20 / 20 | match |
| 3.1 | heavy penalty 0.19 [0.11, 0.30] vs 0.18 [0.08, 0.29] | PEN headline-tacit p5 price_index | 0.1948 [0.1097, 0.3017] / 0.1835 [0.0843, 0.2944] | rounding |
| 3.1 | matching 0.16 vs 0.56 ("under a third") | PEN matching_share tacit p1 | 0.1635 / 0.5649 (ratio 0.29) | rounding |
| 3.1 | "about half Qwen's level" | 0.3875 / 0.7162 | 0.54 | match |
| 3.1 | table gpt-oss no chat: 1.78 [1.59, 1.96]; 0.39 [0.29, 0.48]; 0.57 [0.45, 0.68]; 0.68 [0.60, 0.76]; 0.16 [0.10, 0.24] | PEN gpt-oss headline-tacit p1 | 1.775 [1.5875, 1.9609]; 0.3875 [0.2897, 0.4794]; 0.571 [0.454, 0.6791]; 0.6811 [0.6028, 0.757]; 0.1635 [0.0985, 0.2445] | rounding (all 15 numbers) |
| 3.1 | table gpt-oss compete: 1.01 [1.00, 1.03]; 0.005 [0.000, 0.016]; 0.007 [0.000, 0.020]; 0.99 [0.97, 1.00]; 0.00 | CTL cell_means gpt-oss ctl-32b-compete | 1.0106 [1.0, 1.0319]; 0.00532 [0, 0.01596]; 0.00668 [0, 0.02004]; 0.9899 [0.9714, 1.0]; 0.0 | rounding (all 13 numbers) |
| 3.1 | table gpt-oss joint: 2.49 [2.46, 2.51]; 0.74 [0.73, 0.76]; 0.93 [0.93, 0.94]; 0.25 [0.17, 0.33]; 0.61 [0.51, 0.71] | CTL cell_means gpt-oss ctl-32b-joint | 2.4887 [2.4638, 2.5148]; 0.7443 [0.7319, 0.7567]; 0.9319 [0.9259, 0.9369]; 0.2493 [0.1715, 0.3296]; 0.6071 [0.5125, 0.7068] | rounding (all 15 numbers) |
| 3.1 | table Qwen no chat: 2.43 [2.34, 2.52]; 0.72 [0.67, 0.76]; 0.91 [0.88, 0.94]; 0.38 [0.26, 0.51]; 0.56 [0.43, 0.70] | PEN Qwen headline-tacit p1 | 2.4323 [2.3358, 2.5237]; 0.7162 [0.6664, 0.7644]; 0.9078 [0.8753, 0.9357]; 0.3762 [0.2574, 0.5081]; 0.5649 [0.4333, 0.6991] | rounding (all 15 numbers) |
| 3.1 | table Qwen compete: 1.00, 0.00, 0.00, 1.00, 0.00 (degenerate) | CTL cell_means Qwen ctl-32b-compete | 1.0, 0.0, 0.0, 1.0, 0.0 (zero-width CIs) | match |
| 3.1 | table Qwen joint: 2.45 [2.38, 2.50]; 0.73 [0.69, 0.75]; 0.92 [0.89, 0.94]; 0.00; 1.00 [1.00, 1.00] | CTL cell_means Qwen ctl-32b-joint | 2.45 [2.375, 2.5]; 0.725 [0.6875, 0.75]; 0.9188 [0.8906, 0.9375]; 0.0; 0.9987 [0.9961, 1.0] | rounding (all 13 numbers) |
| 3.1 | mean over 20 games, n 20 | PEN / CTL n | 20 | match |
| 3.1 | direction (tacit above compete; printed prices raise tacit prices) | LED G-comm, G-payoff | same sign | match |
| 3.4 | headline 0.13 (Qwen 0.23) | CA d-cot-monitor-a vs headline-chat p1, price | -0.1298 / -0.2325 | rounding |
| 3.4 | 0.13 [0.02, 0.24], 19 pairs | CA price est/lo/hi/n | -0.1298 [-0.2416, -0.0237], 19 | rounding |
| 3.4 | Qwen 0.23 [0.18, 0.29], 20 | CA qwen_* | -0.2325 [-0.2899, -0.1751], 20 | rounding |
| 3.4 | matching -0.16 / -0.43; comp +0.13 / +0.32 | CA match, comp | -0.1606 / -0.4325; 0.1276 / 0.3169 | rounding |
| 3.4 | channel-shift threshold 0.05 | Step 2 channel_shift definition (term table) | 0.05 | match |
| 3.4 | gpt-oss Holm p 0.192, family 22 | CA price holm_p, family_m | 0.1924, 22 | rounding |
| 3.4 | "Qwen Holm p 0.009" on the price index | QCA d-cot-monitor-a t1 price: exploratory, bh_q 0.00064, no Holm; pgi row: holm_p 0.0086, family 86 | Holm 0.009 belongs to Qwen pgi | **mismatch fixed** (text and table now: Qwen price BH q 0.0006 exploratory; Qwen pgi Holm p 0.009) |
| 3.4 | spread -0.26 [-0.48, -0.04], 19 | CA spread | -0.2597 [-0.4776, -0.0438] | rounding |
| 3.4 | Qwen spread -0.47 [-0.58, -0.36] | CA qwen_* | -0.4716 [-0.5842, -0.3565] | rounding |
| 3.4 | pgi -0.13 [-0.28, +0.01], Holm p 0.638 | CA pgi | -0.1319 [-0.2769, +0.0052], 0.638 | rounding |
| 3.4 | Qwen pgi -0.14 [-0.19, -0.08] | CA qwen_* | -0.1353 [-0.1939, -0.0827] | rounding |
| 3.4 | comp +0.13 [+0.02, +0.24], BH q 0.08 | CA comp | 0.1276 [0.0202, 0.2409], 0.0768 | rounding |
| 3.4 | Qwen comp +0.32 [+0.22, +0.41] | CA qwen_* | 0.3169 [0.2187, 0.4129] | rounding |
| 3.4 | ad-hoc comp interval [-0.00, +0.26] | COT standard_metrics competitive_share | [-0.0029, 0.2643] | rounding |
| 3.4 | match -0.16 [-0.27, -0.06], BH q 0.008 | CA match | -0.1606 [-0.2663, -0.0603], 0.0075 | rounding |
| 3.4 | Qwen match -0.43 [-0.52, -0.35] | CA qwen_* | -0.4325 [-0.5188, -0.3491] | rounding |
| 3.4 | Qwen Step 4 -0.23 [-0.31, -0.15] | Qwen STEP4 box, track 3 | -0.23 [-0.31, -0.15] | match |
| 3.4 | 268 exploratory tests | CA family_m | 268 | match |
| 3.4 | silent high-price share -0.004 [-0.023, +0.011] | COT silent_high silent_high_round_share | -0.0040 [-0.0226, 0.0105] | rounding |
| 3.4 | high-price rounds -0.31 [-0.55, -0.03] | COT silent_high high_round_share | -0.3108 [-0.5479, -0.0346] | rounding |
| 3.4 | explicit flag -0.32 [-0.53, -0.11] ad hoc | COT channel_shift explicit_agreement_any | -0.3158 [-0.5263, -0.1053] | rounding |
| 3.4 | explicit -0.58 [-0.74, -0.42] Step 2 | CA explicit | -0.5790 [-0.7368, -0.4211] | rounding |
| 3.4 | Qwen -0.45 and -0.55 | COT channel_shift Qwen explicit_agreement_any; CA qwen_est explicit | -0.45 / -0.55 | match |
| 3.4 | messages +1.5 [0.7, 2.5] | COT channel_shift messages_per_round | 1.525 [0.715, 2.538] | rounding |
| 3.4 | Qwen messages +2.4 | COT channel_shift Qwen | 2.434 | rounding (added note: different count bases, per COT ANALYSIS.md) |
| 3.4 | silent turns Qwen +4.8, gpt-oss -2.8 | COT channel_shift silent_turns | 4.8 / -2.842 | match / rounding |
| 3.4 | reasoning mentions monitor +0.022, shutdown +0.013 | COT channel_shift reasoning_mentions_* gpt-oss | 0.02205 / 0.01276 | rounding |
| 3.4 | Qwen +0.082, +0.332 | COT channel_shift Qwen | 0.0818 / 0.3323 | rounding |
| 3.4 | baseline price 0.57 vs Qwen 0.85 at p1 | PEN headline-chat p1 price_index | 0.5735 / 0.8466 | rounding |
| 3.4 | 19 pairs (one failed game) | CA n; LED G-cot | 19 | match |
| 3.4 | penalty point 1 sustainable 0.703 | Qwen STEP4 header | 0.703 | match |
| 3.4 | "three of the five metrics" exploratory | CA kind: spread, comp, match exploratory; price, pgi declared | 3 of 5 | match |
| 3.4 | Replicates column (spread, price "sign and size"; pgi no; comp, match sign only) | CA intervals (Qwen -0.47 inside [-0.48, -0.04]; -0.23 inside [-0.24, -0.02]) | consistent with the same-sign rule | match |
| 3.4 | direction | LED G-cot (price -0.13, negative; "in sign only" overall because pgi CI includes 0), G-cot-mech | same sign | match (the section's per-metric "yes" on price is consistent; the overall verdict differs only because the ledger counts pgi) |
