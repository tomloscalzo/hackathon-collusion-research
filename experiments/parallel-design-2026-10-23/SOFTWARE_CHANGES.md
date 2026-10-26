# Software changes for the parallel experiments (2026-10-23)

*Planning document. Everything below was established on Friday 2026-10-23 against the local mock server only (`llm.MockLlmServer` on 127.0.0.1); no remote call was made, nothing was deployed, and no repository file outside this folder was changed. "Measured" means measured on the mock on the 12-core laptop; "estimate" means an estimate with its basis stated. The LLM interface (prompts, reply schema, `LlmAgent`, client behaviour, `docs/interfaces`) is change-controlled: items that touch it are listed as OWNER-DECISION proposals, with their impact on the owner's teammate who is doing model selection.*

## 0. What the harness does today, measured

- **`run --seat LLM` is strictly sequential:** a plain loop over seeds, one game at a time, one HTTP call at a time. On a 200 ms-latency mock, 43 calls took 11.4 s wall for `--runs 2`; two one-seed processes in parallel took 9.1 s (bounded by the longer game). **Throughput scales only by OS processes.**
- **Per-process overhead is negligible:** JVM start plus `cost` 0.55 s; a 6-call shard 2.1 s (about 1.5 s fixed); about 50 ms per call beyond backend latency. One process per shard is fine against a real model at 1-5 s per call.
- **Caches merge by concatenation:** cache lines are self-contained JSON (hash, text, tokens, finishReason, modelSnapshot, drawKey) and `CacheFile.load` keeps the first line per hash. Measured: two shard caches plus a duplicate copy (21 lines, 15 unique) replayed 4/4 OK; an 8-shard merged cache (74 lines) with a merged run file replayed 16/16 OK.
- **A shared cache file across concurrent processes works by luck, not by design** (measured once: 44 lines, replay 2/2 OK), because a process only knows entries present at its start and interleaved appends are not guaranteed atomic. Rule: **one cache per shard, merge afterwards.**
- **No resume (F15):** rerunning an identical command appends duplicate run lines (2 → 4) with every call served from cache; an aborted command leaves the completed run lines and the cache, writes no manifest, exits 1.
- **Failure handling:** 429, 5xx and any IOException (connect, the 120 s request timeout, a non-JSON 200 body) are retried 3 times with 50/100 ms back-off (0.3 s total) and then abort the command. On HTTP 500 (measured) the finished seed's run line is kept, no manifest, exit 1. The 0.3 s window cannot cover a Modal cold start (minutes) or a queueing timeout: send one warm-up call before launching shards, and let the launcher's rerun-partial-shard rule be the real retry.
- **BudgetExceeded (F17):** every command reserves 1.25 × (800 in + 120 out) × 40 rounds × runs; replies averaging over about 150 output tokens abort the shard after the overrunning call and lose that reply (F8). Mitigation today: short shards, and `--max-tokens` set **per cell from the smoke run's 99th-percentile output length** (review finding 6): a blanket low cap such as 150 would turn cut-off replies into repaired or imputed rounds, an imputed round carries the previous quote forward and scores as adherence, and the label, guardrail and notice arms plausibly lengthen rationales, so the artefact would be treatment-correlated. The pipeline reports imputed-round rates per arm and applies an imputed-at-CI-0 bound when paired arms differ by more than 10 points. A thinking-mode model counts its reasoning as completion tokens: avoid such models or disable thinking in the chat template.
- **F18 (provider refusal field)** does not apply to vLLM, which never emits `message.refusal`. **F19** (curly apostrophes) applies to any model and shifts refusals into IMPUTED: report refused and imputed together.
- **`check_schemas.py`** groups calls by `runKey` across every call file it is given, so check one shard at a time (8/8 PASS measured; a combined check gave spurious `tokensIn` failures).
- **`response_format json_schema`** on vLLM 0.8.x is believed supported through guided decoding, not verified here; a 400 at the first call aborts the run immediately, so the harness check (§3) catches it.

## 1. No-interface-change items (do these; all outside the engine)

| # | Item | Status | Hours [est] | Risk |
|---|---|---|---|---|
| 1 | **Parallel runner** `scripts/launch_shards.py`: shards a design by arm × paraphrase × seed range, one `java -jar … run --seat LLM` process per shard with its own `--out` (and so its own cache, calls and manifest), round-robin over any list of `--base-url` endpoints, N jobs at a time; seeds identical across arms (paired design); skips a shard whose `--out` already has the expected line count (the F15 workaround); a partial shard is moved aside and rerun, its cache replaying the finished calls free. Measured: 8 shards × 2 seeds over two mock endpoints, 4 jobs, 4.9 s; the second invocation skipped 4/4 complete shards. | done (prototype, 87 lines) | 1 to harden: automatic rerun of partial shards, per-endpoint job caps, a design-CSV input instead of `--arm` flags | low |
| 2 | **Cache merge and de-duplication** `scripts/merge_cache.py`: concatenates caches, keeps the first line per hash, flags same-hash-different-text conflicts, and with `--runs` drops duplicate run lines on (arm, paraphrase, seed, scenarioId, `llm.provider`, `llm.model`, `llm.condition`), so lines of two models are never duplicates of each other (the model was added with D17). Measured as above. | done (prototype, 60 lines) | 0.5 | low (first-wins matches `CacheFile`) |
| 3 | **Rationale export** (F5): a Python script joining `<out>.calls.jsonl` (requestHash, runKey, index, attempt) to the cache (hash → text) and extracting `plan` and `rationale` per round. The rationale is the only free-text outcome we have and feeds the say-versus-do, notice and awareness read-outs. An aborted shard's calls exist without a run line: join on runKey and arm from the run file. | to write | 1-2 | low |
| 4 | **Endpoint discipline for F20**: the provider label is hard-coded, so the cache key is (model name, prompt, temperature, max tokens, schema, draw key). Endpoints serving the same `--model` with the same weights, dtype and vLLM version are interchangeable draws and their caches merge correctly; anything that changes the output distribution (quantisation, dtype, vLLM version) **must** use a different `--model` string, or merged caches silently mix populations and replay cannot tell. Since D17 the Modal recipe derives the served name from the weights, their pinned commit and the vLLM version (`<org>--<name>--<commit>+vllm<version>`), so a different model, revision or vLLM version gets a different name by construction; another dtype for the same weights and version needs `SERVED_VARIANT` set by hand, and a hand-named backend such as `llama-server`, which ignores the name, needs a distinct name by hand (for example `...--<commit>+llamacpp-q4_k_m`). The launcher takes one `--model` per invocation and stops when an `--out-dir` already holds run lines of another model (shard file names do not carry the model): use one `--out-dir` per model. | rule + launcher check; recipe part done (D17) | 0.5 | low if followed |
| 5 | **Superseded by BR-15 (2026-10-23):** the engine now ships `scenarios/probe-defect.yaml` and `scenarios/probe-control.yaml`, sets t = 6 + ((seed - 1) mod 5) from the run seed, and writes the control's responder at the placebo t in its run line, so neither the per-t files nor this post-pass is needed (`docs/interfaces/INTERFACES.md` e.9). The earlier plan, for the record: **P3 placebo post-pass**: the defect arm is YAML-only (measured: a copy of `ripe-game.yaml` with `detection.mode: "OFF"` and partner `{kind: DEFECT_ONCE, config: {theta: 0.546, t: 6}}` loads from a path, runs with the LLM seat, the run line carries `responder` 1/0, `probeClass` and `probeT = 6`, and replays 3/3 OK). The round t comes from the YAML, so there is one file per t (`scenarios-proposed/probe-defect-t6.yaml` … `t10`, distinct ids) and the launcher assigns t by seed index (seed mod 5, as `FactorialDesign.probeT` does). The placebo control (`probe-control.yaml`, the same partner with `t = 0`, never defecting) gives `responder = null` / `EXCLUDED_NOT_INCLUDED` on every run (measured 3/3) because `LlmGame.summary` classifies with the partner's own t. Fix: a Python post-pass that recomputes `Metrics.included`, `longEnough` and `responder` from the exported `rounds` (ownCi, displayed quotes) at the paired t and writes a derived run file for `tools/analysis.py` (about 40 lines). This is what spec §5.6 asks for (a placebo t in control runs) and adds no bias provided three rules hold: the launcher and the post-pass take t from **one shared function** of the seed; replay runs on the **raw** shards, never on the derived file; and the five scenario ids are checked not to alter the shared horizon stream (the stream ids are logged for both arms, read gate (g)). The alternative, a `--probe-t` CLI option, is OWNER-DECISION (item B5). | to write | 1-2 | low |
| 5b | **The committed alias overrides** `scripts/predeclared_design.json` (P5, P6a, P6b and, if built, P4 take `ripe` as their a-arm). `ingest_merge.py --predeclared-design` fails the gate (`predeclared_design_matches`) if the override it generates from the design CSV differs from the committed file, because `analysis.py --design` applies `dict.update` and could otherwise be fed any key at analysis time. Tested on the mock: PASS with the committed file, FAIL with a tampered copy. | done | 0 | none |
| 6 | **Design CSV** as the single source of truth for launcher and analysis (`ANALYSIS_AND_DISTILLATION_PIPELINE.md` §1): cell id, arm, scenario, condition, factor levels, stage, family, predicted sign, band seats, alias (for the shared `ripe` cell). | to write | 1 | low |
| 7 | **Null-band regeneration** for every exploratory arm: a scratch copy of `sweeps/reference-bands.yaml` with one level per new arm; the engine's `batch` regenerates all 21 band cells in about 5 s (measured by the scientist). Output goes beside the design CSV. | scratch YAML exists (`bands10x4.yaml` in the scientist's scratch) | 0.5 | low |

Total: about 5-8 hours of scripting, none of it in the engine, none touching the interface, all testable on the mock.

## 2. OWNER-DECISION items (interface or change-controlled behaviour)

| # | Item | Hours [est] | What it buys | Impact on the model-selection teammate | Risk |
|---|---|---|---|---|---|
| B1 | **F2 N-neutral prompts** for P4: new template file or items and versioned `disclosedRule`, elicitation, vignette and fallback texts behind a new optional replay parameter (today's text stays the default). | 3-5 plus review | P4 (members) becomes runnable | Every `n4` cache made before the change must be rerun; N = 2 arms are unaffected if the default stays today's text. `n4-variant` today renders "exactly one other market maker" beside three partner rules, so **P4 data gathered now is probably unusable: P4 waits or is dropped.** | medium |
| B2 | **Multi-seat support (i.1)**: per-seat `GameContext`, per-seat `SeatFactory`, a `Result` map, one run line per seat or a `seats` array, `--seat-config` per seat, replay reading `llm.seats`. | 6-10 plus tests | LLM-against-LLM tacit collusion (sprint 1.1, 3.x; AUD-MAS). But the i.2 prompt gap (no disclosed rule, the `s_p` fallback, the stray war-level line) also needs new template items, and the predictions and bands are all single-seat. | New optional run-line fields and replay parameters; phase-1 hashes unchanged (the draw key already carries the seat id). | **high for this weekend**; start only after one-seat data exists |
| B3 | **`--provider` flag** (F20): `LlmSettings` label from an option, default unchanged. | 0.5-1 | Separate cache populations for two backends serving one model name | Runs made with a non-default label are a separate cache population; runs made before the flag keep the default label and still replay. | low |
| B4 | **F15 resume in the CLI**: `LlmCommands.run` skips seeds already in `--out`. No request, hash, digest or field changes, but INTERFACES.md h.1 documents today's behaviour. | 1-2 with a test | Not needed if the launcher is used | none | low |
| B5 | (Superseded by BR-15, see item 5.) **`--probe-t` option** for the P3 placebo (alternative to item 5 above). | 1 | A cleaner placebo | none (a new optional parameter) | low |
| B6 | **F17 reservation on localhost** (settle against the limit when the host is local, or a `--reserve-factor` option). Changes no hash. Does not apply to Modal (remote); use `--max-tokens` there. | 0.5 | CPU-fleet runs with verbose models | none | low |
| B7 | **F18 refusal field → DECLINED text; F19 apostrophe normalisation** (the latter changes digests of affected cached replies, so it needs a replay parameter). Neither is needed for vLLM this weekend. | 0.5 + 1 | Correct refusal counts on hosted providers and for curly-apostrophe refusals | F19 changes outcomes of some cached runs; select by replay parameter | low |
| B8 | **Recipe edits in `deploy/modal_vllm.py`** (not the LLM interface, but change-controlled by the no-deployment rule): GPU string `"A10"` if `"A10G"` is rejected, `max_containers=1`, `max_inputs=32`, `MODEL_NAME` and pinned `MODEL_REVISION` per model, one app per model. **Done with D17**: `"A10"`, `max_containers=1`, `max_inputs=32`, a served name derived from `MODEL_NAME` and `MODEL_REVISION`, and a refusal to load until `MODEL_REVISION` is a commit hash (the owner pastes it before deploying); a separate `APP_NAME` is needed only to keep two models up at once. | 0.5 | Prevents double-billing scale-out; pins the snapshot | The served name and revision go into every manifest | low |
| B9 | **Regenerate `bands.csv` at the design's seed count** (4 or 8) before the first call; the frozen file was computed at 10 × 3. Values are identical (all P(adhere) bands are the point 0), so this is bookkeeping, but the hashed file should match the design. | 0.1 | Consistency | none | none |

**Recommendation:** approve B8 and B9 now (minutes, no interface change); approve B3 if two backends will serve the same model name; defer B1 (P4) unless a 4-hour slot exists before Saturday noon; **do not start B2 this weekend**. Everything else in §1 needs no approval.

## 3. Harness check against the first real endpoint (run first; about 60 calls, about 50k tokens [est])

```
export COLLUSION_ALLOW_REMOTE=1 COLLUSION_VLLM_KEY=...
KEY=$COLLUSION_VLLM_KEY
SERVED=$(curl -fsSL --max-time 1200 "$URL/v1/models" -H "Authorization: Bearer $KEY" | python -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")   # warm-up and served name (RUN_LOGISTICS.md §2)
J="java -jar engine/target/collusion-engine.jar"
C="--base-url $URL --model $SERVED --api-key-env COLLUSION_VLLM_KEY --budget-tokens 300000 --temperature 0.7 --max-tokens 400"
# keep the default 400 for the smoke run; then set the per-cell --max-tokens from the 99th percentile of tokensOut in hc/*.calls.jsonl
$J run --scenario scenarios/ripe-game.yaml --seat LLM $C --seed 1 --runs 1 --paraphrase 0 --arm smoke --out hc/smoke.jsonl
   # read hc/smoke.jsonl.cache.jsonl: JSON replies? finishReason "stop", not "length"?
$J run --scenario scenarios/ripe-game.yaml --seat LLM $C --condition elicitation=E2 --arm e2 --seed 1 --runs 2 --paraphrase 0 --out hc/e2.jsonl
$J run --scenario scenarios/ripe-game.yaml --seat LLM $C --condition elicitation=COMPETITIVE --arm competitive --seed 1 --runs 2 --paraphrase 0 --out hc/competitive.jsonl
   # P2 smell test at 2 runs: meanCi > 0.5 for e2, < 0.1 for competitive
$J replay --cache hc/e2.jsonl.cache.jsonl --run hc/e2.jsonl        # "0 problem(s)" = byte-identical replay
python -X utf8 docs/interfaces/check_schemas.py hc/e2.jsonl hc/e2.jsonl.calls.jsonl hc/e2.jsonl.cache.jsonl
# parse-failure rate from hc/*.calls.jsonl: (REPAIR_NEEDED + PARSE_FAIL) / attempt-0 calls < 2%;
# also tokensOut per call (the F17 margin), repairedRounds, imputedRounds, offGridQuotes.
$J vignette --scenario scenarios/ripe-game.yaml --rows 11 --draws 1 $C --paraphrase 0 --seed 1 --out hc/vig.jsonl ; $J replay --cache hc/vig.jsonl.cache.jsonl --run hc/vig.jsonl
```

## 4. End-to-end shard verification on the mock (measured 2026-10-23)

```
java -jar engine/target/collusion-engine.jar run --scenario scenarios/ripe-game.yaml --seat LLM --base-url http://127.0.0.1:<port> \
   --model mock-model-1 --seed 1 --runs 2 --paraphrase 3 --condition elicitation=SPONTANEOUS --arm ripe --out <scratch>/shard_ripe_p3_s1.jsonl
   # seed 1: 3 rounds, EVIDENCE, pAdhere 1.0; seed 2: 3 rounds, HORIZON; 2.1 s; 2 run lines, 6 cache lines, 6 call lines, manifest
java -jar engine/target/collusion-engine.jar replay --cache <scratch>/shard_ripe_p3_s1.jsonl.cache.jsonl --run <scratch>/shard_ripe_p3_s1.jsonl
   # "2 line(s) replayed, 0 problem(s)", exit 0
python -X utf8 docs/interfaces/check_schemas.py <scratch>/shard_ripe_p3_s1.jsonl <...>.calls.jsonl <...>.cache.jsonl
   # call_record 6, cacheLine 6, llmRunLine 2, invariants 2+1: RESULT PASS
```

A vignette (`--rows 11 --draws 1`) gave bHat 0.2 and replayed 1/1 OK. Mock games are short (3-6 rounds), so the 20-round case is not measured here.

**Runnable today with no code change:** P1-A, P1-A′, P2, P5, P6a-d (game conditions and vignettes), P3 (planned then as YAML files plus the post-pass; BR-15 has since added the engine change that makes it runnable: the shipped `scenarios/probe-defect.yaml` and `probe-control.yaml`, no post-pass). **P4 only after B1.** P7 not built.

## 5. The launcher pattern (for reference)

```
python -X utf8 experiments/parallel-design-2026-10-23/scripts/launch_shards.py \
   --jar engine/target/collusion-engine.jar --out-dir out/stage1 --model $SERVED \
   --base-url https://<workspace>--<APP_NAME>-serve.modal.run \
   --arm ripe=scenarios/ripe-game.yaml --arm unripe-a=scenarios/unripe-a.yaml \
   --arm e2=scenarios/ripe-game.yaml@elicitation=E2 --arm competitive=scenarios/ripe-game.yaml@elicitation=COMPETITIVE \
   --paraphrases 0,1,2,3,4,5,6,7,8,9 --seed0 1 --seeds-per-shard 4 --shards 1 --jobs 32 \
   --extra "--temperature 0.7 --max-tokens 200 --api-key-env COLLUSION_VLLM_KEY --budget-tokens 400000"
```

Files per shard: `out/stage1/<arm>_p<para>_s<seed0>.jsonl` plus `.cache.jsonl`, `.calls.jsonl`, `.manifest.json`. Keep `--jobs` ≤ `max_inputs` × containers, or calls hit the 120 s client timeout. With `--seeds-per-shard 4` and 10 paraphrases, one Stage 1 arm is 10 shards of about 80 calls each; a lost shard costs at most one game's calls.
