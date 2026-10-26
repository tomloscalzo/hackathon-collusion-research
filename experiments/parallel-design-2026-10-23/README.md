# Parallel experiment design (2026-10-23): folder guide

> **Track S only.** This folder describes the sharded Track S runs. Track M uses the grid runner in `plans/SCOPE_AND_EXPERIMENTAL_DESIGN.md` §14.1, and the scope document (version 5.3) wins any conflict. See `BUILD_AND_RUN_START_HERE.md` at the repository root.

*Planning prototype prepared during the sprint on Friday 2026-10-23. No LLM call has been made and nothing has been deployed; every script was tested only on scripted Monte Carlo or mock-server output. Nothing in this folder changes the model, the engine, the LLM interface, `plans/PREDICTIONS.md` or existing results.*

| File | What it is | Read it if you are |
|---|---|---|
| `EXECUTIVE_SUMMARY_OF_PARALLEL_EXPERIMENT_PLAN.md` | The 1-2 page decision document: feasibility verdict for "results tonight", three options with time and cost, the recommendation, the owner decisions D1-D6 | the owner, deciding |
| `EXPERIMENT_DESIGN.md` | Factors and levels, the four-stage adaptive design, cells, runs, power table, controls, the exploratory pre-declaration draft, CPU versus GPU variants | the chief scientist |
| `RUN_LOGISTICS.md` | Models, Modal vLLM GPUs and prices, throughput and cold-start estimates, CPU fleet, sharding, failure handling, timelines, verification, runbook | whoever launches the runs |
| `ANALYSIS_AND_DISTILLATION_PIPELINE.md` | The post-run pipeline: design CSV, ingestion and validation, cache merge, contrasts, dashboards, triage, sanity gate, findings ledger, one-page summary with number checker, ROI next steps; the mock test log | whoever writes up the results |
| `SOFTWARE_CHANGES.md` | What the harness does today (measured on the mock), the no-interface-change items, the OWNER-DECISION items with hours, risk and teammate impact, the harness-check commands | the engineer |
| `EXPLORATORY_PREDECLARATION_DRAFT.md` | The draft exploratory pre-declaration (OWNER-DECISION D4): the BH family, the descriptive read-outs, the frozen text rules, the seed plan, and the freeze list for the one commit that must precede the first claim-bearing call | the owner and the chief scientist |
| `REVIEW_LOG.md` | The adversarial feasibility review and the disposition of each finding | anyone checking the plan |
| `scripts/` | Prototypes: `launch_shards.py` (parallel runner), `merge_cache.py`, `make_shard_plan.py`, `ingest_merge.py`, `exploratory_contrasts.py`, `ledger.py`, `summarize.py`, `run_pipeline.sh`, `power_sim.py`; `design_cells.csv` and `design_contrasts.csv` (the real plan), `predeclared_design.json` (the committed alias overrides), `*.MOCK.csv` (the prototype test design); `mock/ShardHarness.java` and `mock/bands_MOCK_with_P6.csv` for the regression test | the engineer and the analyst |
| `scenarios-proposed/` | Proposed game YAML files, **not** installed in `engine/src/main/resources`: `ripe-fine0.yaml` and `ripe-rhocoop0.1-fine5000.yaml` for the Stage 2 screen. (The earlier P3 files `probe-defect-t6..t10.yaml` and `probe-control.yaml` were removed: BR-15 ships `scenarios/probe-defect.yaml` and `scenarios/probe-control.yaml` in the engine instead.) Each loads with the engine's `cost` command (checked 2026-10-23) | the engineer |

Every `.md` file has an `.html` rendering beside it.
