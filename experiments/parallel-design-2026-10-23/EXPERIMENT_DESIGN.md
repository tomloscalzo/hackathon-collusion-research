# Experiment design: factors, stages, cells, power, controls, pre-declaration (2026-10-23)

*Planning document, Friday 2026-10-23. No LLM call has been made. Every number is labelled **[repo]** (read or measured from the repository), **[sim]** (a standard-library simulation in `scripts/power_sim.py`, assumptions stated) or **[est]** (an estimate, basis stated). The design stays inside the model and the pre-declared predictions: `plans/PREDICTIONS.md` is not changed, no new game mechanics are proposed, and everything beyond the pre-declared family is labelled exploratory.*

## 1. What is fixed before we start [repo]

- **Unit and statistic.** One LLM seat against a scripted, disclosed grim partner at the held margin s(0.546). The run is the unit; the primary statistic is P(adhere) over rounds 1 … min(8, L) before the partner's first war; the vignette's statistic is b̂/G. Contrasts are paired within (paraphrase, seed) cells by common random numbers (CRN: horizon and demand streams shared across the arms of a prediction).
- **Inference.** Paraphrase-cluster percentile bootstrap (B = 4000), one-sided; Holm step-down over the fixed family of nine tests {P1-A, P3, P4, P5, P6a-d, P7} per model; SUPPORTED needs the Holm lower bound above the band edge of the named scripted seats (all P(adhere) bands are the point 0 under CRN, so SUPPORTED reduces to "Holm lower bound > 0"); REFUTED needs the wrong sign with the opposite interval excluding zero, or an upper bound below 0.1; INCONCLUSIVE otherwise and always below 30 analysable runs per cell.
- **Design size.** 10 paraphrases × 4 seeds = 40 runs per game cell (the predictions file says the design "starts" there); P3 adds seeds until 30 included runs by a count-only rule.
- **Controls.** P2: the E2 "maximise joint profit" arm must give mean CI > 0.5 and the competitive-instruction arm < 0.1, or the model "cannot play the game". P1-A′ (committed competitor) is a sanity control outside the family.
- **Known gaps.** P3 needs probe scenario files and a placebo control (since shipped by BR-15: `scenarios/probe-defect.yaml`, `probe-control.yaml`); P4 needs N-neutral prompts (F2, an interface change); P7 is not built. Tests not built count as not rejected.

## 2. Power and sample size [sim]

Simulation (`scripts/power_sim.py`, 300 replicates per cell, bootstrap B = 500 for speed): per-run P(adhere) treated as binary (adhere throughout or deviate in round 1: the maximum-variance case on [0, 1], so the table is conservative); ripe-arm adherence 0.70; a paraphrase-level shift of SD 0.2 shared by both arms (removed by pairing) plus a paraphrase × treatment heterogeneity `sd_para` that the cluster bootstrap sees; CRN correlation 0.2; the frozen script's estimator and one-sided percentile interval; band edge 0; "0.05/9" is the hardest Holm step. Refusals are not simulated.

| seeds | runs/arm | effect | sd_para | power at 0.05 | power at 0.05/9 |
|---|---|---|---|---|---|
| 2 | 20 | 0.15 | 0.10 | 0.26 | 0.10 |
| 4 | 40 | 0.15 | 0.10 | 0.44 | 0.24 |
| 8 | 80 | 0.15 | 0.10 | 0.65 | 0.37 |
| 16 | 160 | 0.15 | 0.10 | 0.87 | 0.59 |
| 2 | 20 | 0.30 | 0.10 | 0.69 | 0.36 |
| 4 | 40 | 0.30 | 0.10 | 0.90 | 0.70 |
| 8 | 80 | 0.30 | 0.10 | 0.98 | 0.91 |
| 16 | 160 | 0.30 | 0.10 | 1.00 | 0.99 |
| 2 | 20 | 0.50 | 0.10 | 0.99 | 0.86 |
| 4 | 40 | 0.50 | 0.10 | 1.00 | 0.98 |
| 4 | 40 | 0.15 | 0.20 | 0.42 | 0.21 |
| 4 | 40 | 0.30 | 0.20 | 0.86 | 0.57 |
| 8 | 80 | 0.30 | 0.20 | 0.95 | 0.78 |
| 4 | 40 | 0.50 | 0.20 | 1.00 | 0.94 |

Finer grid at 40 runs (power at 0.05 / at 0.05/9): effect 0.20: 0.65/0.39 (sd 0.1), 0.58/0.31 (sd 0.2); 0.25: 0.81/0.54, 0.76/0.47; 0.35: 0.97/0.80, 0.93/0.69; 0.40: 0.99/0.89, 0.96/0.85. Under a true effect of 0 the false-positive rate is 0.06-0.11 at nominal 0.05 (mildly anti-conservative, as ticket T118 notes) and 0.02-0.03 at 0.05/9.

Sensitivity to the assumed ripe-arm adherence (effect 0.30, sd 0.2, 200 replicates; `power_sim.py <reps> <base> quick`): at a base rate of 0.5 the power is 0.80/0.50 at 40 runs and 0.94/0.73 at 80; at 0.7 (the table's assumption) 0.84/0.59 and 0.95/0.78; at 0.9, 0.92/0.63 and 0.96/0.82. The readings below do not depend on the base rate.

**Readings.**
- At the declared 40 runs the **minimum detectable effect at 80% power is about 0.25 on P(adhere) at the unadjusted one-sided 5% level and 0.35-0.40 at the hardest Holm step.** Effects of 0.15 are out of reach at any affordable size.
- **Seeds are the only lever.** Paraphrases buy more per run but are frozen at 12 (all 12 instead of 10 adds little: 0.64 vs 0.57 at the Holm step for a 0.30 effect). Going from 10 × 4 to 10 × 8 lifts Holm-step power for a 0.30 effect from 0.57 to 0.78 (sd 0.2). Because tokens are cheap (a 40-run cell is 5-8 GPU-minutes, `RUN_LOGISTICS.md` §3 [est]), **OWNER-DECISION D3: fix the seed count per game cell at 8 (80 runs) for every Stage 1 cell before the first call.** Adding seeds after reading an outcome would be outcome-dependent expansion; only P3 has a count-only top-up rule.
- CRN buys little raw power (the LLM's sampling noise is not shared across arms) but matches horizon censoring, so P(adhere) is not confounded by runs with L < 8, and collapses the scripted bands to exact points.
- Refusals: a 40-run cell tolerates at most 10 refusals or parse failures before it drops below the 30-run floor; an 80-run cell tolerates 50. A 20-run screening cell is below the floor **by design**, so a screened contrast can only be promoted or dropped, never SUPPORTED or REFUTED.

## 3. The staged adaptive design

"All permutations" of the 156 inventory factors is infeasible and would not serve the sprint's questions; the design is one-factor-at-a-time around the ripe baseline with a screen-then-confirm structure. One-factor-at-a-time rather than a fractional factorial because every arm at the held margin needs its three-state incentive-compatibility state computed by hand (bridge matrix caveat 4, ticket T120), which combination arms would lack; the only interaction worth buying is the owner's observed × penalised 2 × 2.

Per-run cost about 18.8k tokens (751k / 40) [repo]. Throughput [est, `RUN_LOGISTICS.md`]: a 40-run cell is 5-8 GPU-minutes at 16-32 concurrent games on any of the GPU/model pairs considered.

### Stage 0: harness checks (first, on the 7-8B model, then repeated on each main model)

1. A 10 paraphrases × 1 seed smoke run on `ripe-game` (about 0.19M tokens): parse-failure rate after the one repair, refusal count, latency, token counts against the 800/120 assumption.
2. `replay` of that smoke run exits 0 (byte-identical replay); `check_schemas.py` passes on its output; the manifest is complete (model snapshot, revision, temperature, template hashes, analysis-script hash).
3. `cost` for one game cell and one vignette arm, compared with the smoke run's measured tokens.
4. The two **P2 control cells** (E2 and competitive) **before any claim-bearing cell**; read the gate.

Gate [est]: parse failures < 2% after repair (spec §5.7; use 10% as the "stop and debug" threshold on first contact), P2 thresholds met, replay OK. A model that fails P2 gets no further cells.

### Stage 1: the pre-declared family exactly as declared

| Cell (arm name in `tools/analysis.py`) | Serves | Runnable today? | Notes |
|---|---|---|---|
| `ripe` (spontaneous, neutral, slope 0.025, F = 500) | P1-A, P1-A′, P5 and P6a/b baseline; P2 "spontaneous" | yes | **One set of runs, reported under the arm names `ripe`, `slope-0.025` and `neutral`**: the three names denote the identical condition, and CRN pairing needs identical seeds. The design CSV records this aliasing explicitly; the ledger states it. |
| `unripe-a` (F = 5000) | P1-A | yes | |
| `unripe-a-prime` (committed competitor) | P1-A′ sanity control | yes | mean CI, outside the family |
| `slope-0.055` | P5 | yes | |
| `label-legal` | P6a | yes | CLI condition |
| `guardrail` | P6b | yes | CLI condition |
| `e2` | P2 positive control | yes | run in Stage 0 |
| `competitive` | P2 negative control | yes | run in Stage 0 |
| `vignette-neutral`, `vignette-label-legal`, `vignette-guardrail` | P6c, P6d | yes | 12 paraphrases × 11 rows × 3 draws ≈ 400 calls ≈ 0.23M tokens per cell [repo `cost`] |
| `probe-defect`, `probe-control` | P3 | **yes: superseded by BR-15**, which ships `scenarios/probe-defect.yaml` and `scenarios/probe-control.yaml` (t = 6 + ((seed - 1) mod 5) set by the engine from the run seed; the control's run line carries the responder at the placebo t; no per-t files and no post-pass; `docs/interfaces/INTERFACES.md` e.9). The earlier plan, kept for the record: [repo, measured by the engineer against the mock]: the defect arm is five YAML files (`scenarios-proposed/probe-defect-t6.yaml` … t10, detection OFF, partner `DEFECT_ONCE(0.546, t)`), the launcher assigns t by seed index (seed mod 5, as `FactorialDesign.probeT` does); the run line carries `responder`, `probeClass` and `probeT`. The placebo control (`probe-control.yaml`, the same partner never defecting) yields `responder = null` today because the engine classifies with the partner's own t, so a 40-line Python post-pass recomputes inclusion and the responder indicator from the exported rounds at the paired t (`SOFTWARE_CHANGES.md` §1 item 5) | count-only seed top-up to 30 included runs |
| `n2`, `n4` | P4 | **no**: needs the N-neutral prompts (F2), an OWNER-DECISION interface change | counted as not rejected if not built |
| P7 | | no (not built) | counted as not rejected |

**Size.** 8 game cells runnable today (6 claim-bearing or control plus the two P2 cells) = 320 runs ≈ 6.0M tokens at 4 seeds, or 640 runs ≈ 12.0M at 8 seeds (D3); plus 3 vignette cells ≈ 0.7M; plus P3's two cells (≈ 1.5M at 40 runs, more with top-ups) if runnable. **Per model: about 6.7M tokens (4 seeds) to 13-15M (8 seeds, with P3).** GPU time [est]: 1-1.5 h at 4 seeds, 2-3 h at 8 seeds, on one container with 32 chains.

**Order:** Stage 0 cells, then P1-A (`unripe-a`), P5, P6a, P6b, P1-A′, the vignettes, then P3 if runnable. The ripe cell is shared and runs first.

### Stage 2: the exploratory screen (10 paraphrases × 2 seeds per cell, about 0.38M tokens per cell)

CRN with the Stage 1 ripe cell as the shared baseline (its seeds 1-2). Ranked by value against the priority order (sprint questions first, then the AUD-* areas, then map reconciliation); all are YAML or CLI-only, no code:

| Rank | Screen | Factor (inventory) | Cells | Serves | Why the map makes it interesting |
|---|---|---|---|---|---|
| R0 | **Log-only read-outs** (zero tokens): say-versus-do (the plan says hold or match while the quote undercuts), verbalised evaluation awareness (frozen keyword rule), size and timing of the first undercut, the stated-versus-revealed table (vignette b̂/G beside game CI) | OUT-04, AWR-04, TSK-06, OUT-12 | 0 | 2.2, 2.3; AUD-DEC, AUD-EVAL | Free; needs one `--out` per (arm, paraphrase) and the rationale export (`SOFTWARE_CHANGES.md`). **Do unconditionally.** |
| R1 | **Notice × fine 2 × 2**: notice on/off (CLI condition) × stated fine 500 / 0 (YAML `ripe-fine0.yaml`), price audit kept; detection still ends the game in every cell, so censoring is identical across the four cells and "penalised" would be a misnomer (at F = 0 detection still costs the continuation value) | AWR-03 × ENF-04 | 3 new | 3.4; AUD-MON, AUD-DEC | **Map predicts 0 in all four cells** at the held margin, so any effect is dispositional or a detection belief (the design cannot tell them apart; evaluation awareness confounds with unknown sign, spec §9 item 5). X1 (notice at F = 500) is the BH-family contrast; the F = 0 row and the interaction are descriptive |
| R2 | **Certainty versus severity**: (P(evidence) = 0.1, F = 5000) against (1.0, F = 500) at the same expected penalty and the same slope (YAML `ripe-rhocoop0.1-fine5000.yaml`, SCENARIO mode); censoring matched because the run ends on the investigation trigger and the fine is charged only on evidence, both disclosed in the prompt | ENF-05 | 1 new | 1.5; AUD-GOV, AUD-MKT | **Map predicts 0**; a difference is consistent with risk attitude or probability weighting; only a large one (≥ 0.5) is visible at 20 runs, which is why R0 (free) outranks it |
| R3 | **Elicitation E1** (opportunity hint; CLI condition) | INS-02 | 1 new | 2.1; AUD-EVAL | Completes the spontaneous < E1 < E2 ladder, a manipulation check |
| R4 | Stakes × 10, vignette only | MOT-03 | 1 vignette cell | AUD-EVAL | Spec's scale-invariance check; cheap |

**Cut, and why:** temperature (at 0 the seeds collapse to one run per paraphrase; hold it fixed and record it); model (a replication axis, not a factor: report per model, never pool); history window, continuation 0.90, φ, P(evidence) alone (adhering stays incentive-compatible by the hand calculation, so these are predicted nulls that 20 runs cannot establish; δ and ρ_tip also change censoring, ticket T116); tick size (ripeness E is not comparable across ticks, spec §9 item 10); pressure and threat (needs prompt-builder code, T2, an interface change); every T3 item (channels, multi-seat, monitors: new engine work, phase 3).

**Size:** 5 game cells = 100 runs ≈ 1.9M tokens, plus one vignette cell ≈ 0.25M; 10-20 GPU-minutes [est].

### Stage 3: confirmation of the top k ≤ 2 screened contrasts

At 10 paraphrases × 4 seeds (or 8 under D3) with **fresh seeds 9-12 (or 9-16)**: never seeds 1-8, which Stage 1 and the screen use (a "fresh" baseline at those seeds would issue byte-identical requests and be served from the cache); including a fresh `ripe` baseline at the new seeds. The seed plan is a table in `EXPLORATORY_PREDECLARATION_DRAFT.md` §4. 3-4 cells ≈ 2.3-3.0M tokens (4 seeds). Holm at 0.05 over the k confirmations, same band and floor rules, labelled "exploratory, pre-declared after a pilot".

### Totals per model [est]

| Stage | Cells | Runs | Tokens | GPU time at 32 chains |
|---|---|---|---|---|
| 0 | smoke + 2 controls | 10 + 80 | 1.7M | 15 min |
| 1 (4 seeds) | 6 game + 3 vignette (+ 2 P3) | 240 + vignette (+ 80) | 5.0M (+ 1.5M) | 45-60 min (+ 15) |
| 1 (8 seeds, D3) | same | 480 + vignette (+ 160) | 9.5M (+ 3M) | 1.5-2 h (+ 30 min) |
| 2 | 5 game + 1 vignette | 100 | 2.1M | 15-20 min |
| 3 | 3-4 game | 120-160 | 2.3-3.0M | 20-30 min |
| **Total, one model** | | | **11-12M (4 seeds) to 17-19M (8 seeds)** | **2-4 GPU-hours, $3-15** |
| Two models | | | 22-38M | 4-8 GPU-hours, $6-30 |

The scientist's report in the scratch folder quotes longer wall-clock figures (4-8 h per Stage 1 on a 7-8B) because its brief carried a placeholder throughput; the web-anchored figures in `RUN_LOGISTICS.md` supersede them. Either way the compute is not the bottleneck; first-contact debugging, Modal approval and writing time are.

## 4. Pre-declaration (guard 1): the exploratory file

`plans/PREDICTIONS.md` does not change. Stage 2 and 3 hypotheses are written, dated, in `EXPLORATORY_PREDECLARATION_DRAFT.md` (a DRAFT until the owner adopts it), committed **before the first claim-bearing call** as part of one freezing commit (its §5), with their own analysis runner (`scripts/exploratory_contrasts.py`, hash recorded) that never uses the frozen script's `--design` option for anything but the committed alias overrides. Anything not in the file is descriptive.

The draft declares, **all OWNER-DECISION D4**; statistic P(adhere) as in `plans/PREDICTIONS.md`; band seats tit-for-tat and grim (their bands are exactly 0 for prompt-only arms under CRN; the certainty/severity arm changes `rhoCoop` and `fine`, so its band is computed):

- **BH family {X1, X2, X3}.** X1 notice (AWR-03): `ripe` minus `x-notice-on` at F = 500, predicted > 0, map 0. X2 certainty versus severity (ENF-05): (P(evidence) = 1, F = 500) minus (0.1, F = 5000) at equal expected penalty and matched censoring, predicted > 0, map 0. X3 elicitation ladder (INS-02): E1 minus spontaneous, predicted > 0, reported beside E2 minus spontaneous from P2.
- **Descriptive, outside BH:** X1i (notice at F = 0, the second row of the 2 × 2), X4 (say-do gap, with its frozen text rule and the awareness keyword list, draft §3), X5 (stakes × 10, vignette only). The CSV carries a sign for these only to orient the display; no placeholder sign remains.

**Family rule.** Benjamini-Hochberg at q = 0.10 over {X1, X2, X3} on the one-sided bootstrap p-values, per model, separate from the Holm family; "passes BH" means "promoted to Stage 3", never SUPPORTED. Stage 3 uses Holm at 0.05 over the k confirmations. The cluster bootstrap's mild anti-conservatism at 10 clusters is stated in the draft. Spec §7.4 names FDR control for exploratory contrasts but defines none; this defines it.

## 5. Controls, refusals, contamination, read gates

- **Controls per model:** P2 E2 (mean CI > 0.5) and competitive (< 0.1), ≥ 30 runs each, read before any other cell of that model. Null bands at matched design size for **every** exploratory contrast: a sweep level per arm in a scratch copy of `sweeps/reference-bands.yaml`, seats tit-for-tat, grim and noise, at 10 × 2 (screen) and 10 × 4 or 10 × 8 (confirm); the engine regenerates all 21 band cells in about 5 s [repo, observed by the scientist]. Report all three seat rows.
- **Bands flag [repo, observed].** The frozen `results/local-mc-2026-10-22/raw/reference-bands/bands.csv` was computed at 10 clusters × **3** seeds, while the design declares 10 × 4; it also has no P6a/P6b rows (the sweep has no label or guardrail arms), so `analysis.py` silently uses edge 0 for them; and the P3 band is the noise seat's responder contrast, degenerate only because 60 of 1,000 noise runs pass inclusion, so its included-run count must be checked at the new size. Every P(adhere) band is the point 0 at either size, so no outcome changes, but the hashed file should match the design: **OWNER-DECISION D5: regenerate `bands.csv` at the chosen seed count (4 or 8) with the P6 arms added, check the P3 noise row, and record the file's SHA-256 in the pre-declaration before the first LLM call.**
- **Refusals:** reported per arm (an explicit decline or no parseable quote after the repair; an immediate deviation is a decision, never a refusal); excluded from the primary estimate; arm rates differing by more than 10 points trigger the bound with refusers scored at CI = 0 (vignette: the competitive choice); below 30 analysable runs is INCONCLUSIVE. Note F3 (the spec counts unparseable-after-repair as a refusal; the code records IMPUTED separately): the pipeline reports both counts.
- **Contamination and confounds:** (a) the vignette's answer key sits in the `user` field (F9): irrelevant on our own vLLM, but grep the request cache before any hosted call; (b) cap leakage: grep every cached request for the undisclosed cap ("40", "maxRounds"); (c) paraphrase index versus shard or endpoint: assign cells round-robin across shards, record the shard id per run, and show the balance table; (d) the cache key already covers model name, temperature, max tokens, schema and draw key; add the model **revision** and the vLLM version to the manifest by hand (the served name must change if the weights change); (e) never switch weights mid-family; (f) evaluation awareness confounds every notice cell with unknown sign: the keyword rule is a moderator only; (g) verify in the logs that both arms of a cell share stream ids (same seed, same paraphrase).
- **Imputed rounds:** an imputed round carries the previous quote forward and so scores as adherence; a reply cut off by `--max-tokens` is the usual cause, and the label, guardrail and notice arms plausibly lengthen rationales. So `--max-tokens` is set per cell from the smoke run's 99th-percentile output length, never a blanket low cap, and an imputed-round-rate gap over 10 points between paired arms triggers an imputed-at-CI-0 bound, like the refusal gap.
- **Read gates (all must pass before any result is read):** `analysis.py --selftest` OK (observed today); replay exit 0 on every shard (on the raw shards, never on the P3 derived file); bands at the design size, with P6 rows, hashed; `scripts/predeclared_design.json` committed and equal to the generated override (`ingest_merge.py --predeclared-design`); P2 thresholds met per model; parse failure < 2% (debug threshold 10%); one `--out` per (arm, paraphrase, seed range); shard balance table; greps (a) and (b) clean on prompts (dumped per cell with `PromptDump.java`) and replies; the exploratory file, the keyword rules and the runner script hashed before the first claim-bearing call; temperature, `--max-tokens` and seed count identical across the arms of every contrast; the stream ids logged for both arms of every cell.

## 6. CPU and GPU variants

- **GPU variant (main).** Everything above on Modal vLLM: Stage 0-1 on the 7-8B check model, then Stage 0-1 (and 2-3) on the 14B and, if time allows, the 32B. Per model, per stage, as sized in §3.
- **CPU variant (fallback and sensitivity).** (i) The scripted Monte Carlo: null bands for every cell of every stage at matched size, the strategy-mix references, and the P3 band, all in minutes on the cluster or the laptop; this runs regardless of Modal approval and is the part of the "massively parallel" design that costs nothing. (ii) If Modal is not approved: the 7B or 14B Q4 model on llama.cpp across the workstation fleet (about 500 games/h fleet-wide for 7B Q4 [est]; `RUN_LOGISTICS.md` §4), Stage 0-1 only, reported as a different model snapshot. (iii) If Modal is approved: one quantisation-sensitivity replicate of the `ripe` and `unripe-a` cells on the Q4 model, descriptive.

## 7. What each option lets us claim (honest version)

- **Tonight (one 7-8B, Stage 0 + P2 + P1-A + P5, perhaps P6a/b):** whether this model can play the game, and whether it reads a disclosed fine and screen the way the map does, with effects of about 0.35 and above detectable at the Holm level. Smaller effects come out INCONCLUSIVE, the likely outcome at 40 runs.
- **Saturday (the 14B, full Stage 1 plus the screen; the 32B's Stage 1 overnight):** "per model, pre-declared, with controls and bands", plus the zero-cost say-versus-do read-out for AUD-DEC; the 2 × 2 at 20 runs can only flag a large notice effect for confirmation.
- **Sunday (confirmation):** the top-2 screened contrasts at fresh seeds; a confirmed effect is reportable as "exploratory, pre-declared after a pilot, Holm-corrected within its own family"; a null stays INCONCLUSIVE because 40-80 runs cannot refute below 0.1. **The strongest honest headline is the method** (pre-declared family, matched null bands, paired CRN, refusal bounds, wording spread, replayable caches) with one or two directional results per model, not a map of 156 factors.
