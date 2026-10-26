# Track M runbook: exact commands

One page, in the order of a run. Run everything from the repository root in a POSIX shell (Git Bash on Windows). Money is spent by the warm-up in step 3 (the first request starts a billed GPU container) and by a non-dry run in step 5 (GPU calls, plus Modal CPU containers if you use the Modal executor). Steps 1, 2, 4, 6 and 7 are free.

Prerequisites: Python 3.8+ with PyYAML (make_grid, lint_m, analysis_r without --grid); matplotlib for the headline PNG; for Modal, `pip install modal`, `modal setup` (login), and the secret `collusion-vllm-api-key` already created (`modal secret create collusion-vllm-api-key VLLM_API_KEY=<the key>`, typed into the owner's own terminal, not into a script or a log).

`"${TRIAL[@]}"` stands for the single-trial game command (C14.1, `tools/trial/trial_cmd.py`: one grid row into its trial directory), defined once in step 3b. It contains `--api-key-env COLLUSION_VLLM_KEY` (see "Keys").

## Keys (read this first)

- The server key is a long random string, stored once in the Modal secret `collusion-vllm-api-key` under the key `VLLM_API_KEY` (the vLLM server reads it from that environment variable, never from its command line, which vLLM logs), and handed to the game only through an environment variable, here `COLLUSION_VLLM_KEY`.
- Never type the key on a command line, never `echo` it, never put it in a file in the repository, a grid, a config or a log. Commands take the **name** of the variable (`--api-key-env COLLUSION_VLLM_KEY`, `--key-env COLLUSION_VLLM_KEY`), never the value.
- Set the variable without printing it: `read -rs COLLUSION_VLLM_KEY; export COLLUSION_VLLM_KEY` (type or paste, press Enter, nothing is shown). Close the shell when done.
- `console.log` in each trial directory is kept, so the game must not print the key. The Modal executor also redacts the key from output and from files the game writes.

## 1. Build and check (free)

```sh
export JAVA_HOME=/c/java/jdk17; export PATH=/c/java/jdk17/bin:/c/maven/bin:$PATH
(cd engine && mvn -q -DskipTests package)          # jar: engine/target/collusion-engine.jar
scripts/preflight --stage dev                        # must say GO (it rebuilds the jar itself; a WARN about the missing freeze is fine)
# before the first paid call: scripts/preflight --stage first-call --out-root out/preflight   (copies the jar there; pass that copy as --jar)
python -X utf8 -m unittest discover -s tools/trial -p "test_*.py"
python -X utf8 testing/check_line_endings.py        # PASS
```

## 2. Make the grid and lint it (free)

```sh
mkdir -p out
python -X utf8 tools/trial/make_grid.py tools/trial/design/trackm_design.yaml out/grid.csv
python -X utf8 tools/trial/lint_m.py --texts <seat_texts.json> --design tools/trial/design/trackm_design.yaml --grid out/grid.csv
```

`lint_m.py` exits non-zero on any failure (placebo length, banned words, cap leakage, the untrue-notice flag, undefined condition texts). `<seat_texts.json>` is the named seat-texts data file (format in the docstring of `lint_m.py`). Do not go on until it prints PASS; a "no tokenizer available" warning means token-length parity was NOT checked (it needs the Qwen3 tokenizer in the local Hugging Face cache), only word parity. Wave 0 holds the smoke and the pilot controls on both models; waves 1 to 6 follow the spending order of the scope document, section 7.

## 3. Deploy a model profile (billed GPU on first request)

One profile per Modal app. `COLLUSION_DEPLOY_PROFILE` is `qwen3_14b`, `qwen3_32b_fp8` or `qwen3_32b_fp8_32k` (the 32k app for the fed-back introspection arms only, below; the same names as `model_profile` in the grid). `COLLUSION_MAX_CONTAINERS` only lowers the cap (never above the profile's 50). Context windows: 16k (16,384) is the default for every profile except `qwen3_32b_fp8_32k`, which serves 32k (32,768) and is used only by the fed-back arms r2f/r3f.

```sh
COLLUSION_DEPLOY_PROFILE=qwen3_14b COLLUSION_MAX_CONTAINERS=50 modal deploy deploy/modal_vllm.py
COLLUSION_DEPLOY_PROFILE=qwen3_32b_fp8 COLLUSION_MAX_CONTAINERS=30 modal deploy deploy/modal_vllm.py   # the main 32B app: deploy ONCE with 30 containers (queue RAMP_PLAN: about 16 games per container; 300+ games need about 20); do not redeploy mid-run
COLLUSION_DEPLOY_PROFILE=qwen3_32b_fp8_32k COLLUSION_MAX_CONTAINERS=4 modal deploy deploy/modal_vllm.py   # 32k window, only for the fed-back arms r2f/r3f (U11); deploy it with 4 containers (owner decision; the main 32B app stays at 30)
```

**Token limits (current).** Thinking on: talk 8,192, quote 8,192, question 4,096 (timeout 300 s). Thinking off: talk 320, quote 400, question 400; the saved-only introspection arms `r2s-confidant` and `r3s-public` have quote 900 when thinking is off (the in-reply answer field is limited to 600 characters, on top of the normal quote, plan and rationale); thinking-on rows of those arms are unchanged. The per-arm override is the design arm key `max_tokens: {t0: {quote: 900}}`.

**The 32k app (unit U11).** `qwen3_32b_fp8_32k` is the same pinned model and vLLM 0.9.2 as `qwen3_32b_fp8` with `--max-model-len 32768` and 8 concurrent requests per container (app `collusion-vllm-qwen3-32b-fp8-32k`, its own URL and served-name check; deploy it only before the Track R fed-back arms, warm it up like the others, and `modal app stop collusion-vllm-qwen3-32b-fp8-32k --yes` afterwards). The design gives the fed-back arms (`r2f-confidant`, `r3f-public`: R2f/R3f; the saved-only `r2s-confidant`, `r3s-public` stay on the 16,384 window) `model_profile: qwen3_32b_fp8_32k`; make_grid writes the profile's `context_window` (32768; 16384 for every other profile) into a grid column, the trial command passes it to `--context-window` for the context clamp, and collect.py copies it into trials.csv. Introspection answers are not capped. If even 32k overflows, the call is clamped or skipped and recorded: clamp.csv lists every clamped or skipped call, trials.csv has `max_prompt_tokens`, and `qc_report.py` judges each trial against its own window (no `--window` needed) and has a section, "Arms with an extended context window", that lists every trial of these arms with its longest prompt and any overflow, clamped or skipped call. Pass the 32k server to the trial command too: add `--base-url "qwen3_32b_fp8_32k=$URL32K" --model "qwen3_32b_fp8_32k=$SERVED32K"` to the template in step 3b (a row whose profile has no pair fails with exit 2). A cost config `context_window` (stop rule) is one number for the whole run: leave it out for waves that include the 32k arms, or run them on their own with 32768.

Warm up before any run (this is the first billed step). A cold start takes minutes, and Modal redirects a request pending over 150 s (the trial command turns on `--follow-redirects`, but curl here needs its own long `--max-time`). `<workspace>` is the Modal workspace name; the app names are `collusion-vllm-qwen3-14b` and `collusion-vllm-qwen3-32b-fp8`. Set the key first (see "Keys"): an unset variable sends an empty bearer token and fails with 401. The curl header carries the key in the process list for the length of the call; that is the accepted trade-off on a private machine.

```sh
export COLLUSION_ALLOW_REMOTE=1          # local shell only; see the Modal note in step 5
URL14=https://<workspace>--collusion-vllm-qwen3-14b-serve.modal.run
SERVED14=$(curl -fsSL --max-time 1200 "$URL14/v1/models" -H "Authorization: Bearer $COLLUSION_VLLM_KEY" \
    | python -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")
echo "$SERVED14"        # the served name: the game's --model for qwen3_14b
# the same for the 32B app: URL32=https://<workspace>--collusion-vllm-qwen3-32b-fp8-serve.modal.run, SERVED32=...
```

Warm up again after any pause longer than the profile's idle window (120 s).

Two models, two servers: the 32B app has its own URL and its own served name, and must be warmed up separately. The grid's `model_profile` column (`qwen3_14b` or `qwen3_32b_fp8`) says which server a trial uses; the trial command picks `--base-url` and `--model` by that profile. Wave 0 (smoke and pilot controls) needs both servers. To run one model only, leave the other's pair out and pass `--arm` with that model's arms (a trial whose profile has no `--base-url` fails with exit 2).

## 3b. The trial command (free to define)

```sh
SHA=$(git rev-parse HEAD)            # the commit the jar was built from; recorded in every params.json (collect.py guards it per arm)
TRIAL=(python -X utf8 {trial_cmd} --trial-dir {trial_dir} --jar {jar} --scenarios {scenarios}
       --base-url "qwen3_14b=$URL14" --model "qwen3_14b=$SERVED14"
       --base-url "qwen3_32b_fp8=$URL32" --model "qwen3_32b_fp8=$SERVED32"
       --api-key-env COLLUSION_VLLM_KEY --code-commit "$SHA" --budget-tokens 70000000 --allow-remote)
# check one row without running it:  python -X utf8 tools/trial/trial_cmd.py --print --trial-dir <a trial dir with grid_row.json> ...
```

The same array serves both executors: `{trial_cmd}`, `{jar}` and `{scenarios}` are filled by `run_grid.py` (locally `tools/trial/trial_cmd.py`, the `--jar` you pass and the repo's scenario directory; on Modal `/app/trial_cmd.py`, `/app/collusion-engine.jar`, `/app/scenarios`). So pass `--jar engine/target/collusion-engine.jar` to `run_waves.py`/`run_grid.py` for the local executor too. Per row, `trial_cmd.py` reads `{trial_dir}/grid_row.json` and runs `java -jar {jar} run --seat LLM --multi-seat on [--talk on] --trial-dir {trial_dir} --runs 1 --scenario ... --seed --paraphrase --arm --trial-id --penalty-point --code-commit --thinking on|off --model --base-url --api-key-env --budget-tokens`, the out, cache and call log inside the trial directory, the row's sampling, timeout and token limit, `--follow-redirects on --reserve-out-tokens max`, and on thinking-on rows `--call-timeout-sec quote=s,talk=s,question=s` (the design's thinking-on `timeout_sec` is 300, above Modal's 150 s redirect, so a long call is redirected rather than timed out); it prints that argv to `console.log` first. The scenario file is used as is: the Track M headline and two-LLM arms use `slice-m-p1..p5.yaml` (the slice files with two LLM seats `llm1`, `llm2`; `slice-p1..p5.yaml` keep one LLM and a scripted partner, for Track S), and a row whose seat list disagrees with its file's seats is refused (exit 2). `--allow-remote` sets `COLLUSION_ALLOW_REMOTE=1` for the game only (the container does not inherit your shell). `--budget-tokens` is a per-trial hard cap on the reservation (a worst case, not spend): with the smoke-informed thinking-on limits (quote 8,192, talk 4,096, question 4,096 tokens; `tools/trial/design/trackm_design.yaml`) a two-firm thinking-on chat game reserves about 12.7M tokens, a three-firm one about 23.7M, the fed-question arms R2/R3 about 58.9M (R4 13.8M, tacit 2.6M), and the game refuses to start below that (console.log says by how much); hence 70M here. Real spend is watched by the cost config.

The condition texts (`--condition-texts`, C11.2) and the arm options (`--options`, questions and reminders, C13.3 onward) are passed to the jar when its usage text lists them, which a current jar does. Only the per-call settings map (`--call-settings`, C12b.2) is sent once the jar lists it; until then the token limit is one value per game (the largest of the quote and, with talk, talk limits). With an older jar a row that needs condition texts other than `neutral`, or arm options, is refused (exit 2, so the trial is marked FAILED); `--allow-unwired` runs such rows without them (a WARNING line in `console.log` and an `UNWIRED` file in the trial directory), which is only acceptable for a plumbing smoke, never for data: give such a run its own `--out` (for example `out/plumbing`), because `DONE` trials are never replayed.

## 4. Dry run of the plan (free)

```sh
python -X utf8 tools/trial/run_waves.py --grid out/grid.csv --out out/trials --config cost.json --stop-line 120 --dry-run \
    --jar engine/target/collusion-engine.jar -- "${TRIAL[@]}"
```

`cost.json` example: `{"rate_per_hour": 3.95, "games_per_container": 20, "pilot_cost_per_game": 0.5, "stage_cap_usd": 100, "context_window": 16384}` (values are placeholders; without `rate_per_hour` or token prices the spend is always $0 and the stop line cannot fire, and `run_waves.py` warns). vLLM refuses with HTTP 400 any call whose prompt plus `max_tokens` exceeds the served window (16,384 tokens by default, 32,768 on the 32k app); the client does not retry a 400. The context clamp (`--context-clamp on --context-window`, passed by the trial command from the grid's `context_window`) lowers a call's `max_tokens` to fit or skips the call and records it (clamp.csv), so a long game is no longer lost, but a clamped thinking reply has less room. With 8,192 output tokens a thinking-on quote prompt should stay under 8,192 tokens on the 16k window. In the first smoke the thinking-off two-firm chat prompts reached about 4,400 tokens by round 9 (the chat part plateaus; the history adds about 50 a round), so two firms should stay near 5,800 at round 40, but three-firm and fed-question (R2/R3) arms may reach about 8,000 late in long games. Check clamp.csv and `max_prompt_tokens` for those arms before trusting them. The prompt-size stop (`context_window`) is only a late signal: it is checked after a trial finishes; `"context_window": 9000` would flag a prompt above 8,100 tokens, but use it only in a cost config for thinking-on waves run on their own (it would also stop on harmless thinking-off or talk prompts above 8,100). It holds the rate and caps (`rate_per_hour`, `games_per_container`, `token_price_per_million_in/out`, `pilot_cost_per_game`, `stage_cap_usd`, `context_window`; see `tools/trial/stop_rules.py`). The dry run prints each wave's trial count, spend so far, projected cost and whether the stop line would stop it. It starts nothing.

## 5. Run

Local executor (game processes on this machine, calls go to the deployed server):

```sh
python -X utf8 tools/trial/run_waves.py --grid out/grid.csv --out out/trials --config cost.json --stop-line 120 \
    --max-concurrency 8 --jar engine/target/collusion-engine.jar -- "${TRIAL[@]}"
```

Modal executor (each trial in a Modal CPU container; the key is read there from the Modal secret):

```sh
python -X utf8 tools/trial/run_waves.py --grid out/grid.csv --out out/trials --config cost.json --stop-line 120 \
    --executor modal --jar engine/target/collusion-engine.jar --key-env COLLUSION_VLLM_KEY --modal-max-containers 50 \
    -- "${TRIAL[@]}"        # contains --api-key-env COLLUSION_VLLM_KEY, as the Modal executor requires
```

Modal notes. (1) In the container, `{trial_cmd}` is `/app/trial_cmd.py`, `{jar}` is `/app/collusion-engine.jar`, `{scenarios}` is `/app/scenarios` and `{trial_dir}` is the working directory; the `TRIAL` array uses only these placeholders, so it needs no change. (2) The container does not inherit your shell: `--allow-remote` in the array sets `COLLUSION_ALLOW_REMOTE=1` for the game, and `--budget-tokens` is in it too. (3) The key is read in the container from the Modal secret, so `COLLUSION_VLLM_KEY` need not be set locally for Modal runs (it is for warm-up). (4) Modal CPU containers are billed on top of the GPU.

One wave or one arm only: add `--waves 0` or `--arm smoke-14b-chat`. Run a single grid without the wave loop with `tools/trial/run_grid.py --grid ... --out ... [--wave N] --jar engine/target/collusion-engine.jar -- "${TRIAL[@]}"` (same options).

Exit codes of `run_waves.py`: 0 all selected waves done; 1 a trial failed; 2 usage error; 3 a stop rule fired (3 failures in a row, over 10% failures, rolling cost, stage cap, prompt near the window, over 5% truncated at the token limit, word caps not counted); 4 an arm was paused for refusals; 5 the stop line. Any non-zero status from a wave ends the run (later waves do not start). After 1, 3 or 5: fix the cause or raise the line, then run the same command again; failed trials are retried and finished (`DONE`) trials are skipped, so nothing is paid for twice. After 4 a plain rerun pauses the same arm again at once (the pause is re-derived from the finished games): leave that arm out with `--arm` (list the others) or accept it as paused and report it.

## 6. Collect and analyse (free)

```sh
python -X utf8 tools/trial/collect.py out/trials out/tables      # trials, rounds, messages, questions, refusals CSVs
python -X utf8 tools/trial/analysis_m.py        out/tables out/analysis_m [--contrast A:B]
python -X utf8 tools/trial/analysis_detect.py   out/tables out/analysis_detect [--truth truth_rounds.csv]
python -X utf8 tools/trial/make_theory.py out/theory.csv        # the 5 slice points: expected penalty and theory level
python -X utf8 tools/trial/analysis_headline.py out/tables out/analysis_headline --theory out/theory.csv
python -X utf8 tools/trial/analysis_r.py        out/tables out/analysis_r --grid out/grid.csv   # Track R arms = the grid's introspection R2f R3f R2s R3s R4, control = headline-chat; also the D-set differential; exit 1 if none ran
```

`out/theory.csv` is written by `make_theory.py` from `slice-p1..p5.yaml` (`--prefix slice-m-p` reads the two-LLM twins, which state the same values; columns `penalty_point, expected_penalty, theory_level`; `theory_level` is the `# theory-theta-star:` line, `expected_penalty` is the per-period penalty hazard at full collusion times the fine, rho_E(1)*F = 5, 15, 25, 50, 100: the penalty per period at full collusion, a ceiling, not what each pair faced at its own margin; label the figure axis that way). Exit 2 on a missing or malformed scenario file or an unsupported market (tick above 0, non-LEVEL screen). The two market prices come from `trials.csv` (`competitive_price`, `collusive_price`, written from each trial's `params.json`); `--competitive P --collusive P` override them. `collect.py` refuses to merge an arm whose trials differ in prompt fingerprint or code commit (exit 1). `analysis_headline.py` needs matplotlib for the PNG (exit 3 if missing; the CSV is still written).

Pairing (window basis) is scoped to the comparison: `analysis_headline.py` draws and pairs only the headline arms (`--arms`, a regular expression, default `^headline-`: tacit, private chat, monitored chat; no match = exit 2), so the smoke, control, side and Track R arms collected from the same `out/trials` neither appear nor cut the headline seeds; `analysis_m.py` pairs the headline arms in its summary (`--pair-arms`, same default; other arms are summarised unpaired), and each `--contrast A:B` pairs only its own two arms. `measures_summary.csv` shows, per cell, `games_assigned` and `window_share` (the share of games the window keeps, default rounds 1..20, after pairing unless `--no-pairing`; a cell whose window keeps no game shows `n_games` 0 and `window_share` 0: read it before trusting a window-basis level) and `ci_method`: a wording with a single game makes the bootstrap resample games across wordings (`game`, with a warning on stderr) instead of within wording, and fewer than 2 games leave the bounds blank (`none`). `headline_data.csv` and the Track R differential files carry the same `ci_method` column, and the headline draws no band at a point with blank bounds.

Imputed rounds (a truncated or unparseable reply, played as imputed; never refusals) are shown next to the refusals: `imputed_round_share` in `refusals.csv` (per call kind), `measures_summary.csv`, `headline_data.csv` and the headline legend and note, and `refusal_table.csv`/`.html`. The text of an imputed talk turn or question answer (which can hold the model's private `<think>` reasoning) is never put in a table, transcript or viewer page: a placeholder such as `[imputed: truncated thinking]` is shown (the raw reply stays in `events.jsonl`). If the window basis keeps no game (every game shorter than `--window-end`, e.g. a smoke), `analysis_headline.py` exits 2 with a hint: pass `--basis assigned` or a shorter window.

## 6b. Rerun the truncated thinking-on games (free to plan, billed to run)

Rule: any thinking-on game in which any call (quote, talk or question) stopped at its token limit (`finish_reason` "length") is rerun in full on the 32k profile with larger caps (quote and talk 28,672 tokens, question 16,384; context window 32,768). The truncated original is kept but marked superseded and left out of the primary analysis. Thinking-off games are never rerun. Reruns get the id of the original plus `__x32k` and the same arm, wording, seed and options, so they take the original's place in its cell.

```sh
python -X utf8 tools/trial/trunc_rerun.py scan out/trials                          # which games, which call types, how many calls
python -X utf8 tools/trial/trunc_rerun.py grid out/trials --out out/grid_x32k.csv  # rerun grid: copies of the original grid_row.json rows
# run it like any grid, into a separate root (section 5): run_waves.py / run_grid.py --grid out/grid_x32k.csv --out out/trials_x32k ...
python -X utf8 tools/trial/trunc_rerun.py supersede out/trials out/trials_x32k     # writes out/trials/superseded.csv (original_id,rerun_id,reason)
python -X utf8 tools/trial/collect.py out/trials out/tables --rerun-root out/trials_x32k                       # primary: originals out, reruns in
python -X utf8 tools/trial/collect.py out/trials out/tables_sens --rerun-root out/trials_x32k --include-superseded   # sensitivity: originals in, reruns out
```

`supersede` lists only reruns that are `DONE`; missing ones go to stderr and their originals stay in the primary analysis. It can be run again as reruns finish (it only adds rows). A rerun is never rerun again (a game that still truncates at 32k is reported by `scan`, not chained). `--include-superseded` counts every game once: the truncated originals replace their reruns. Without `superseded.csv` nothing changes. `grid` copies `timeout_sec` unchanged (300 s for thinking-on), which is too short for a 28,672-token reply at about 40 tokens/s (about 720 s): `grid` prints a loud warning and the lead must decide; `grid --timeout-sec N` sets it on every rerun row. `grid` skips, with a warning, originals on a non-32B profile (e.g. `qwen3_14b`): the 32k profile is a different model, so they are never moved silently (`scan` flags them). `scan` counts only replies that really stopped at the token limit, not calls skipped by the context clamp. A `__x32k` directory that is not listed in `superseded.csv` is always left out of `collect.py` with a warning.

## 6c. Anchored versus neutral payoff examples (free to define)

The prompt prints worked payoff examples at a few example half-spreads (the half-spread is the margin a firm adds above its cost; prices move in ticks of 0.01, and 1.00 is the floor, the competitive price). The default `anchored` examples are at 1.54, 2.09 and 3.00, which can pull quotes toward those numbers (2.09 is the opening level). The `neutral` examples are an evenly spaced set, 1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00, with no anchor. To test whether the printed numbers move behaviour, play the same grid twice. The trial ids are identical in the two grids (the grid root, not the id, identifies the condition), so keep them in separate roots. The options cell of every anchored row is unchanged (no `payoff_examples` key, so the engine digests are unchanged); the neutral grid adds `payoff_examples=neutral` to every row's options (an explicit `--global-options payoff_examples=anchored` drops the key again, so it is digest-identical to the default grid), and every row has a `payoff_examples` column (`anchored` or `neutral`). The trial command passes the options cell to the engine's `--options` unchanged.

```sh
# anchored grid: exactly the command of section 2
python -X utf8 tools/trial/make_grid.py tools/trial/design/trackm_design.yaml out/grid.csv
# neutral twin: the same command plus the global option
python -X utf8 tools/trial/make_grid.py tools/trial/design/trackm_design.yaml out-neutral/grid.csv --global-options payoff_examples=neutral
```

Run and collect each grid into its own root (section 5 and 6), then compare the two tables dirs (pairs on arm, cell, wording, seed, thinking; unpaired games are listed and excluded):

```sh
python -X utf8 tools/trial/anchor_compare.py out/tables out-neutral/tables out/anchor_compare.csv --grid out/grid.csv [--start 1 --end 20]
```

It prints and writes, per arm x cell x thinking, the neutral-minus-anchored profit gain index (the share of the monopoly profit gain over the Nash profit, as in `baseline_bot.py`, over rounds `--start`..`--end`, default 1..20, the same window as `analysis_m.py`; a game lacking part of the window drops out of that metric, and the window is printed with the table) and the share of quotes (all rounds) on the anchored points and on the neutral points (`share_neutral_set`, and `share_neutral_set_no_floor` without 1.00), each with a paired bootstrap 95% interval over (wording, seed) units (`--seed` 20260101, 2000 resamples). Read the two sets with care: 1.00 is the competitive floor, where a firm quotes for competitive reasons whether or not it is printed, and 3.00 is in both sets, so `share_p3.00` and `share_neutral_set_no_floor` are cleaner readings of the anchoring effect than the whole-set shares. Games dropped for pairing (including a pair key that occurs twice on one side) are in `out/anchor_compare.csv.unpaired.csv`.

## 7. Read the transcripts (free)

```sh
python -X utf8 tools/trial/viewer.py out/trials out/viewer       # open out/viewer/index.html in a browser
```

Read every smoke transcript before spending on the next stage. Refusals are listed, not dropped.

## 8. Stop billing

```sh
modal app list
modal app stop collusion-vllm-qwen3-14b --yes
modal app stop collusion-vllm-qwen3-32b-fp8 --yes
```

Check `modal app list` again: no app should be left running. Containers also scale to zero after the idle window, but stop the apps when a session ends.
