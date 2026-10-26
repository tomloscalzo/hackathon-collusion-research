# Run logistics: models, deployment, sharding, cost, time, failure handling (2026-10-23)

*Planning document, prepared Friday 2026-10-23 about 13:00 ET. Nothing here has been run: no LLM call has been made and nothing has been deployed. Every number is labelled **[web]** (retrieved 2026-10-23 from the URL given), **[est]** (an estimate, basis stated) or **[repo]** (read from the repository or measured with the engine's `cost` command). Verify the [est] figures in the first fifteen minutes of real use (§7) and replace them.*

*Note, 2026-10-23 evening: the plan of record is `plans/SCOPE_AND_EXPERIMENTAL_DESIGN.md` version 5.2. It supersedes this file's "Not this weekend: Qwen3" (section 2) and the 4,096-token window: the main model is now Qwen3-14B with thinking on for quote and question calls, and the window is 16,384 (decisions 6 and 10). `transformers` is pinned at 4.51.3, because vLLM 0.8.5 crashes with transformers 5.x. The rest of this file is not updated.*

*Updated later on 2026-10-23 for D17 (model identity): the recipe facts and the commands below describe the changed recipe, which derives the served name from the weights and their pinned commit and already contains the B8 edits.*

## 1. Hard facts from the repository [repo]

- The harness makes **one call per round, sequentially within a game**; different games are independent, so parallelism is the number of concurrent games (processes). One game is about 20 calls (cap 40). Each call is about 800 prompt tokens [est: prompt characters / 4 from the `cost` command, not a tokenizer count; verify from `tokensIn` in the first smoke run] with a near-identical prefix across calls (so prefix caching helps), and about 120 completion tokens (`--max-tokens` 400; set per cell from the smoke run's 99th-percentile output length, see `SOFTWARE_CHANGES.md` §0).
- `cost` (prompt characters / 4, no call made): a **40-run × 20-round game cell = 816 calls, 653k prompt + 98k completion ≈ 751k tokens**; one vignette pass (11 rows) = 11 calls ≈ 6.4k tokens.
- The client sends `model, messages, temperature, max_tokens, seed, user` and `response_format {type: json_schema, json_schema: {name: "decision", schema}}` with no `strict` field. Any HTTP status other than 429 or 5xx aborts the run. Rate limiter: `--rate-per-sec r` (burst 4). The provider label is hard-coded (F20), so two backends serving the same `--model` string share cache keys: give a quantised model its own `--model` name and its own cache.
- `deploy/modal_vllm.py`: vLLM 0.8.5, `max-model-len 4096`, prefix caching on, `max_inputs=32`, `max_containers=1`, scale-to-zero after 300 s idle, GPU string `"A10"`. The served name is derived from the weights, their pinned commit and the vLLM version, `<org>--<name>--<40-hex revision>+vllm<version>` (for example `Qwen--Qwen2.5-7B-Instruct--<commit>+vllm0.8.5`), and the recipe refuses to load until `MODEL_REVISION` is a commit hash. vLLM answers 404 to any other `model`, so `--model` must be exactly that name, which then labels every cache key, run line, manifest and analysis group: two models, two revisions of one model, or one revision under two vLLM versions never share a cache entry or an analysis group (INTERFACES.md f.1). Another dtype for the same weights needs `SERVED_VARIANT` set by hand.

## 2. Model choices

| Role | Model | Why | GPU |
|---|---|---|---|
| Harness check (first contact) | `Qwen/Qwen2.5-7B-Instruct` (already named in the recipe) | Apache-2.0, ungated (no HF token secret), bf16 about 15 GB, no thinking tokens, supported by vLLM 0.8.5 | A10 (24 GB) |
| Main candidate 1 (run first) | `Qwen/Qwen2.5-14B-Instruct`, bf16 (about 29.5 GB [est: 14.7B × 2 bytes]) | Same family and chat template as the 7B check, so harness fixes carry over; cheapest GPU-hour among main-run sizes | L40S (48 GB) or A100-40GB |
| Main candidate 2 | `Qwen/Qwen2.5-32B-Instruct`, bf16 (about 65 GB) | The roadmap's 32B target; at `max-model-len 4096` and utilisation 0.90 roughly 7 GB of KV room, enough for 16-32 concurrent 1k-token requests [est: 64 layers × 8 KV heads × 128 × 2 × 2 bytes ≈ 262 KB per token] | A100-80GB or H100 |
| Screening-only third model (optional) | `Mistral-Small-24B-Instruct` | Apache-2.0; needs `--tokenizer-mode mistral` | L40S / A100 |

Not this weekend: Qwen3 hybrid models (non-thinking mode needs `chat_template_kwargs enable_thinking=false`, which the client cannot send without an interface change; the Instruct-2507 variants need a vLLM version bump); Gemma-3-27B (gated licence); Llama-3.1-70B (does not fit one 80 GB card in bf16); Llama-3.1-8B (gated: token secret and licence click for no gain over Qwen2.5-7B). An AWQ 32B build (about 19 GB) would fit an L40S, but it is a different model snapshot (own `--model` name, own cache) and a vLLM forum thread reports no throughput gain from AWQ at batch on A100 [web https://discuss.vllm.ai/t/no-throughput-improvement-for-quantized-qwen-2-5-7b-instruct/1901]; prefer bf16 on H100.

**The owner's teammate doing model selection** should treat this table as a starting list, not a decision: anything that speaks the OpenAI-compatible API, accepts the request fields above, and returns JSON reliably will work.

**Guided decoding.** vLLM's OpenAI server accepts `response_format json_schema` and enables structured outputs by default with backend `auto` (xgrammar first) [web https://docs.vllm.ai/en/v0.9.1/features/structured_outputs.html; the 0.8.5-specific behaviour is from memory and must be verified]. Risk: xgrammar rejects some schema keywords (numeric `minimum`/`maximum`, `pattern`) with HTTP 400, which aborts a run. Five-minute check with one curl against the deployed URL, sending the exact `DECISION_SCHEMA` from `PromptBuilder` (dump it with `docs/interfaces/harness/PromptDump.java` or copy it from `docs/interfaces/schemas/llm_game_reply.schema.json`):

```
URL=https://<workspace>--<APP_NAME>-serve.modal.run    # APP_NAME: collusion-vllm (Qwen2.5-7B), collusion-vllm-qwen3-14b, collusion-vllm-qwen3-32b-fp8
KEY=<the VLLM_API_KEY value of the Modal secret>      # the same value as COLLUSION_VLLM_KEY in §8
# warm-up and served name: no container runs before the first request (min_containers=0); a cold start takes minutes,
# and Modal answers a request still pending after 150 s with a 303 redirect, which curl -L follows (the Java client
# does not, so never let java make the first call). data[0].id of the reply is the served name, --model later.
SERVED=$(curl -fsSL --max-time 1200 "$URL/v1/models" -H "Authorization: Bearer $KEY" | python -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")
curl -s $URL/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"'"$SERVED"'","messages":[{"role":"user","content":"Quote a half-spread. Reply as JSON."}],
       "temperature":0.7,"max_tokens":400,"seed":1,"user":"probe",
       "response_format":{"type":"json_schema","json_schema":{"name":"decision","schema":<DECISION_SCHEMA>}}}'
```

Pass: HTTP 200 and a parseable object with `quote`. A 400 that mentions the schema means a schema keyword is unsupported: the fix is a server flag (`--guided-decoding-backend outlines`), never a schema edit (the schema is hashed into every cache key; changing it is an interface change).

## 3. Modal vLLM: prices, throughput, cold starts

**Prices [web https://modal.com/pricing, per-second billing × 3600]:** A10 $1.10/h, L4 $0.80/h, L40S $1.95/h, A100-40GB $2.10/h, A100-80GB $2.50/h, H100 $3.95/h; CPU $0.047/core/h; volumes 1 TiB-month free.

Two deploy-time gotchas [web https://modal.com/docs/guide/gpu]: the docs list the GPU string **`"A10"`, not `"A10G"`** (the recipe now uses `"A10"`); and "GPUs require a valid payment method on file": **confirm before 2 pm that the $250 credit is usable without a card.**

**Throughput reference points [web]:** databasemart benchmarks (16-bit, 100 in / 600 out, 50 concurrent): A40 7B 1,095 output tok/s at 38 ms per token, A40 14B 530 tok/s [https://databasemart.com/blog/vllm-gpu-benchmark-a40]; A100-40 7B 2,091 tok/s (53 per user), 14B 575 tok/s (24 per user), TTFT 0.65 s [https://www.databasemart.com/blog/vllm-gpu-benchmark-a100-40gb]; A100-80 32B-class 470-520 tok/s (17-19 per user), TTFT 1.3 s [https://www.databasemart.com/blog/vllm-gpu-benchmark-a100-80gb]. Batch-1 Qwen2.5 on A100-80, vLLM 0.6.3: 7B 84 tok/s, 14B 46, 32B 22 [https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html].

**Estimates for our workload at 16-32 concurrent games [est, scaled from the above by memory bandwidth: A10 600 GB/s vs A40 696; L4 300 GB/s; H100 about 1.6 × A100-80]:**

| GPU, model | $/h | per-stream tok/s | s per call | s per 20-call game | games/h at 16 chains | aggregate tok/s | $ per 1M tokens | wall-clock for 5M / 10M / 30M tokens (one container) |
|---|---|---|---|---|---|---|---|---|
| A10, 7B bf16 | 1.10 | 25-30 | 4.5-5 | ~100 | ~550 | ~2,800 | ~$0.11 | 0.5 / 1.0 / 3.0 h |
| L4, 7B bf16 | 0.80 | 12-15 | ~9 | ~190 | ~300 | ~1,500 | ~$0.15 | 0.9 / 1.9 / 5.6 h |
| L40S or A100-40, 14B bf16 | 1.95-2.10 | 20-24 | ~6 | ~125 | ~450 | ~2,300 | ~$0.25 | 0.6 / 1.2 / 3.6 h |
| A100-80, 32B bf16 | 2.50 | 15-18 | ~8 | ~165 | ~350 | ~1,800 | ~$0.39 | 0.8 / 1.5 / 4.6 h |
| H100, 32B bf16 | 3.95 | 25-30 | ~5 | ~105 | ~550 | ~2,800 | ~$0.39 | 0.5 / 1.0 / 3.0 h |

Reading: **a 40-run cell takes 5-8 GPU-minutes at 16 concurrent games; the pre-declared set for one model (8-11 cells plus vignettes, 7-9M tokens) is 1-1.5 GPU-hours, $1.5-6 of GPU time.** Tokens are not the budget problem. Idle containers, cold starts, unplanned scale-out and first-contact debugging are.

**Saturation.** Decode is bandwidth-bound, so aggregate throughput rises almost linearly with concurrency up to about 32-64 [est]. 16 chains half-use the server; 32 is the sweet spot. Each chain is one JVM process waiting on HTTP, so 32 processes on the laptop are fine.

**Scale-out trap.** Without `max_containers`, a request beyond `max_inputs` would start a second GPU container, billed twice. The recipe now sets `max_containers=1` and `max_inputs=32`, so extra requests queue instead; still keep the chain count at or below 32, or queued calls run into the client's 120 s timeout.

**Cold start [est, from Modal and vLLM experience]:** first image build 8-15 min (CPU-billed); weight download 7B 2-4 min, 14B 4-6 min, 32B 8-15 min the first time, about 1 min from the volume afterwards; vLLM start 2-4 min (GPU-billed). A warm-volume cold start is 3-6 min, $0.06 (A10) to $0.40 (H100). Each scale-to-zero wastes the 300 s idle window, $0.09-0.33.

**Recipe changes for a 14B or 32B run (owner-approved, not interface changes):** `MODEL_NAME`, `MODEL_REVISION` (the commit hash of that repository; the recipe refuses to load without one, and the check in step 2 of §8 catches a wrong one), `GPU` (`"L40S"` or `"A100-40GB"` for 14B; `"H100"` or `"A100-80GB"` for 32B; tensor parallel not needed on one 80 GB card); `max_inputs` 32 and `max_containers` 1 are already set; `startup_timeout` 15 min is enough. The served name follows from `MODEL_NAME` and `MODEL_REVISION`, so each model's cache entries and analysis group stay distinct without further care. Redeploying under the same `APP_NAME` replaces the running model (requests that still name the old model then get 404); give each model its own `APP_NAME` only to keep two models up at once; its URL is then `https://<workspace>--<APP_NAME>-serve.modal.run`, and each app is stopped by its own name (§8).

**Budget split of the $250 credit (if approved) [est]:** harness checks on 7B/A10 $10; pre-declared set on 14B $15 and on 32B $25 (each including 3-4 cold starts and idle); screening (3-5 × the pre-declared set) on one model $50; **reserve $150** for the two real risks: a forgotten container (an idle H100 is about $95 per day; always stop every running app after each batch, §8 step 8) and unplanned scale-out.

## 4. CPU workstations with llama.cpp

Assumption (unverified): about 15 Linux boxes of 16-32 cores with 100-200 GB/s memory bandwidth, install rights available.

Reference points [web]: dual EPYC 9334, 24 threads: 20-28 generation tok/s for Q4 7-20B models, 8B at 27.8 tok/s [https://blog.leaseweb.com/2026/04/05/amd-epyc-llm-inference-benchmark-cpu-vs-gpu/]; an older llama-bench table for 7B Q4_0 at 16 threads gives prompt processing 33 tok/s and generation 15 tok/s (prompt processing is much faster on current AVX-512 CPUs; unmeasured).

Estimates per 16-32-core box [est]: 7B Q4_K_M prompt 150-400 tok/s, generation 12-25 tok/s single stream; 14B Q4_K_M prompt 80-200, generation 6-12. With `llama-server --cache-reuse` and the shared prefix, about 300 new prompt tokens per call: a 7B call 7-12 s, a game 150-250 s, 15-24 games/h single stream; with `-np 4` parallel slots about 2 × aggregate, so **30-45 games/h per box for 7B, 15-20 for 14B, 5-8 for 32B Q4**. A fleet of 15: 7B about 500 games/h (a pre-declared set in 1-1.5 h); 14B about 250 games/h (2-3 h); 32B about 90 games/h (about 6 h). Setup is 1-3 h of human time (install llama.cpp, copy a 9-20 GB GGUF to each box).

**Verdict.** A fallback for 7-14B only if Modal is refused (decide at a fixed time, Saturday 09:00, because the fleet costs 1-3 hours of the same person and a 7B Q4 model may well fail the P2 controls), and otherwise a cheap **quantisation-sensitivity replicate** of one or two cells (ripe and unripe-A) once the GPU result exists; never the main-run path. A Q4 model is a different snapshot: give it a name of the same form that names the file, for example `--model Qwen--Qwen2.5-14B-Instruct-GGUF--<commit>+llamacpp-q4_k_m`, and its own `--cache` and `--out`, never the bf16 cache (F20). `llama-server` ignores the request's model name, so nothing checks this name: it is the only record of which weights answered. `llama-server` accepts `response_format json_schema` and `seed` [est]; verify with the same curl as §2. **The cluster's real job is the engine's scripted Monte Carlo** (10k games in about 1.5-2 s on 8 threads [repo]): every null band and every screening sweep at `batch --threads 200` takes minutes, and it needs no model at all.

## 5. Sharding, collection, failure handling

- **Shard** = (arm, paraphrase, seed range), one JVM process per shard, each with its own `--out` (the run file, `.calls.jsonl`, `.cache.jsonl` and `.manifest.json` beside it). Never point two processes at one cache file. Example: 12 arms × 10 paraphrases = 120 shards of 4 seeds, 16-32 in flight at a time. The launcher pattern, the balancing of paraphrase across endpoints and the merge are in `SOFTWARE_CHANGES.md` and `ANALYSIS_AND_DISTILLATION_PIPELINE.md`.
- **Collection:** rsync/scp or a shared folder; replay each shard's digest before merging (`replay --cache ... --run ...`).
- **Failure handling:** the cache is client-side, so a container restart or a killed shard loses nothing; rerunning the same shard command replays the finished calls from the cache at no cost and continues (the CLI does not skip finished runs, F15, so the launcher gives shards small seed ranges and checks line counts before relaunching; see `SOFTWARE_CHANGES.md`). A mid-game failure costs one call. A changed prompt or scenario file silently causes cache misses (F22): freeze the prompt directory before the first call and record its hashes.
- **Egress from the cluster:** each client box needs outbound HTTPS to `*.modal.run` and DNS, a proxy that passes `Authorization` headers, nothing inbound; test with the curl of §2. If the cluster has no egress, drive Modal from the laptop (32 JVMs waiting on HTTP are fine there) and use the cluster for Monte Carlo only.
- **Rate limiting:** a sequential chain issues about 0.2 requests per second; set `--rate-per-sec 2` per process as a guard, keep chains ≤ `max_inputs`; vLLM queues rather than returning 429.

## 6. Timelines (ET; costs [est] at the prices above)

**(a) Tonight, from the approval time T (the 14:00 approval the first draft assumed has passed).** T to T + 20 min: secret, deploy, image build; T + 20 to T + 40: 7B download and first cold start; T + 40 to T + 60: curl schema check and a 3-run smoke game; T + 1 h to T + 2 h: harness check and the first bug round (parse failures, F17 aborts, refusal counting), and the per-cell `--max-tokens` from the smoke run's 99th-percentile output length; T + 2 h to T + 2.75 h: P2 controls on the 7B (80 games, about 10-15 GPU-minutes); T + 2.75 h to T + 3.5 h: switch to the 14B (edit, redeploy, download, cold start); T + 3.5 h to T + 4 h: P2 on the 14B and the freezing commit (D4); then Stage 1 at 8 seeds launched overnight at 32 chains (2-3 GPU-hours); keep the 14B app warm across Stage 0 and 1 and stop it once at the end. **Cost $10-20. Tonight's deliverable: the harness check and P2 on two models. Main risk: the harness has never met a real model; the first 90 minutes may be all bug-fixing. The distilled sheet is a Saturday product; the 32B is not realistic tonight.**

**(b) Saturday noon.** (a) plus the 32B on an H100 (P2 + Stage 1, 1.5-2 GPU-hours, $8-12), P3 seed top-ups to 30 included runs, the Stage 2 screen on the 14B, and the analysis. Cumulative $30-50. Risk: overnight idle or scale-out; `max_containers=1`; stop each app once its batch is done.

**(c) Sunday noon.** (b) plus the Stage 2 screen (3-5 × the pre-declared set, $30-60) on the better-behaved model, a Q4 CPU replicate of the ripe and unripe-A cells, Mistral-Small if time allows. Cumulative $80-150. Risk: cells under 30 analysable runs through refusals or parse failures; writing time.

## 7. Verification in the first fifteen minutes

- **Price:** Modal dashboard → app → usage shows GPU-seconds and dollars per container; compare with the $/h above after 10 minutes; confirm there is no second container.
- **Throughput and latency:** `curl $URL/metrics` (with and without the Bearer header): `vllm:num_requests_running` (near the chain count), `vllm:time_per_output_token_seconds` (expect 30-60 ms), prefix-cache hit rate (> 70% after the first game), `vllm:generation_tokens_total` rate. Client side: the `latency` field of `<out>.calls.jsonl`, median × 20 = game time; `tokens in/out` confirm the 800/120 assumption; the parse-status counts flag guided-decoding trouble at once.
- **Cold start:** container log timestamps from start to "Uvicorn running"; the second start must show no download.
- **CPU:** `llama-bench -m model.gguf -p 512 -n 128 -t <cores>` on one box gives prompt and generation rates in two minutes before touching the fleet.

## 8. Runbook (condensed)

1. Owner approves Modal; confirm the credit works without a card; `modal secret create collusion-vllm-api-key VLLM_API_KEY=<random>`.
2. Set `MODEL_REVISION` to the model's commit hash (the recipe refuses to load otherwise; `max_containers=1` and `max_inputs=32` are already set) and check the pasted value: `python -c "from huggingface_hub import model_info; print(model_info('<MODEL_NAME>', revision='<hash>').sha)"` must print the same hash (a wrong but well-formed hash passes the recipe's check, and vLLM would then fail inside a billed container for up to the 15-minute `startup_timeout`). `modal deploy deploy/modal_vllm.py`, then warm up and read the served name `$SERVED` with the `/v1/models` command of §2 (the deploy starts no container; "Uvicorn running" appears in the container log only after that first request). Put the exact served names into the `models` column of `scripts/design_cells.csv` (in place of `MODEL_A`, `MODEL_B`), or every shard is flagged `MODEL!=DESIGN`. The container scales to zero after 300 s idle: repeat the warm-up before any batch that follows a pause.
3. Curl schema check (§2). Then `export COLLUSION_ALLOW_REMOTE=1 COLLUSION_VLLM_KEY=<random>`; smoke game: `run --seat LLM --scenario scenarios/ripe-game.yaml --base-url $URL --model $SERVED --api-key-env COLLUSION_VLLM_KEY --budget-tokens 200000 --paraphrase 0 --seed 1 --runs 3 --arm smoke --out out/smoke.jsonl`; `replay`; `check_schemas.py out/`.
4. Harness check: parse-failure rate < 2% after repair, byte-identical replay, refusal counts sane (Stage 0 in `EXPERIMENT_DESIGN.md`).
5. P2 controls (e2, competitive) at 40 runs each; read the gate before anything else.
6. Launch the Stage 1 shards (16-32 chains); watch `/metrics` and the Modal dashboard for a second container.
7. Collect, replay, merge, analyse (`ANALYSIS_AND_DISTILLATION_PIPELINE.md`).
8. After every batch: `modal app list`, then `modal app stop <APP_NAME> --yes` for every app still running (`collusion-vllm` for the Qwen2.5-7B profile, `collusion-vllm-qwen3-14b` and `collusion-vllm-qwen3-32b-fp8` for the Qwen3 profiles).
