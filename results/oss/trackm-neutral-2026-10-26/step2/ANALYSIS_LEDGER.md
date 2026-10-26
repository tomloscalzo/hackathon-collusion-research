# Analysis ledger: gpt-oss-20b neutral run, Step 2

**Status: final for this run.** 819 of 840 planned games DONE, 21 failed, 0 not finished (listed in the completion table).

Written from the existing declarations (`experiments/trackm-neutral-2026-10-25/DECLARATION.md`, `experiments/trackm-cell-2026-10-24/CELL_DECLARATION.md`) and the gpt-oss plan (`work_scratch` plan, section 2 rules: the oss Step 2 keeps its own Holm families; the only cross-model rule is the pre-declared same-sign comparison G2, done in `results/compare-models/`). The declarations predate every gpt-oss game.

| family | analyses | correction |
|---|---|---|
| declared | private chat minus no chat at points 1 and 5; point steps 3-1, 5-3, 5-1 in private chat and 5-1 in no chat; the D set (reasoning-monitor threat A, conflict, temptation A and B, placebo scores) against headline private chat at point 1; on the price index and profit gain index (22 tests) | Holm, alpha 0.05 |
| exploratory | every other arm and metric: side arms and controls at point 3, introspection, moral primes, watchdog, d-conflict-ethics, the direct contrasts, the average absolute spread, competitive share, matching share and the flag rates (268 tests) | BH, q reported (0.10 threshold) |
| not tested | headline cell levels, the A1 cell ranking (descriptive here: 5 cells), detection rates, say versus do, introspection, payoff block arms | intervals only |

**Not addressed (no thinking-off mode):** every thinking-on minus thinking-off contrast and the penalty x thinking interaction; these are not addressed on gpt-oss, which is different from no effect. **Dropped:** anchoring (no anchored gpt-oss run); monitored chat and point 4 (not in the gpt-oss grid).

**Post hoc additions (2026-10-25, looks so far: 1 partial look):** the five build-bug arms as a pooled sensitivity; the empty-talk covariate; the payoff block arms (descriptive). The formula / no-numbers cells (the build-bug arms) were looked at during the design check before this ledger was written, so anything about them is post hoc.

**How the numbers are computed.** The tool outputs (competitiveness, intent classes, detectors, the scripted-bot baseline) enter through the Step 1 builder run_csv.py, which imports collect.py, derive.py, competitiveness.py, analysis_m.py, analysis_detect.py, intent_classes.py and baseline_bot.py; Step 2 reads run.csv and run_firms.csv and does not rerun night/analysis/pipeline.py (whose figures assume two thinking modes and an anchored run).

Created by Claude at the prompting of the repository owner.