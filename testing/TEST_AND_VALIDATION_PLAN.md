# Test and validation plan: the harness before the first real LLM run (2026-10-23)

*Sprint work, Friday 2026-10-23. Prepared by the testing and validation lead (Claude, at the prompting of the repository owner). Everything here was run on the local CPU against the engine's `MockLlmServer` on 127.0.0.1. No LLM, Modal or remote endpoint was called. Every number from a run is **MOCK**.*

**Aim:** the test harness must be reliable and correct, must not get in the way, and must never pollute experimental results.

**Contents:**
1. Summary
2. Audit
3. Pollution risks
4. Pre-flight checklist
5. What was implemented
6. Open proposals
7. Logged findings
8. How to run
9. Adversarial review disposition

## 1. Summary

| | Before | After |
|---|---|---|
| JUnit (`mvn -q test`) | 102 tests on the original `main`, 103 after PR #11. **Red on Windows:** 2 failing, because `core.autocrlf=true` checks the YAML out with CRLF | 126 tests, 0 failing, on CRLF and on LF working copies (PR #12 added 4, PR #14 added 5, this change adds 14) |
| Python | `tools/analysis.py --selftest` (19 checks, 24 after PR #14); `check_schemas.py` | the same, plus `testing/test_harness.py` (25 tests on a 180-run mock dataset) |
| End-to-end LLM path against the mock | Library-level digests, plus one 2-run CLI test | run → cache → rerun → replay → schema check → independent recomputation of the statistics → frozen analysis, through the real CLI |
| Network guard in tests | `RemoteGuard` only. A shell with `COLLUSION_ALLOW_REMOTE=1` exported turned one test red | surefire strips the variable; a JUnit extension blocks and fails non-loopback HTTP and raw-socket connections |
| Mock vs real separation | None: no gate looks at the host or the model name | `testing/provenance_guard.py`, wired into `scripts/preflight` |
| Go/no-go gate | Commands scattered over three planning documents | `scripts/preflight --stage dev / first-call / ingest`, a per-stage jar copy, and a freeze record |

PR #12 (merged) landed the line-ending fix early, so that the other agents had a green base. This document covers the rest.

## 2. Audit

### 2.1 What was covered

The JUnit suite was strong on several fronts:
- **Layer A goldens.**
- **Engine snapshots:** trigger, penance, detection, hidden fills.
- **Determinism:** roster-invariant streams, and batch output identical for 1 and 8 threads.
- **The LLM seat at library level:** adherence and undercut, snapping, repair, imputation, text refusal, the probe, and live-vs-replay digests.
- **The client:** canonical hash, cache hit, replay miss, budget, rate limiter, retries, the remote guard.
- **The CLI:** one 2-run game, one vignette, `cost`, and the remote refusal.

`check_schemas.py` validates schemas, examples and data files with invariants. `analysis.py --selftest` covers Holm, the band edge, the run floor, the outcome rules, the refusal bound and determinism, on synthetic records.

### 2.2 Gaps found

| # | Gap | Severity | Now |
|---|---|---|---|
| A1 | The suite was **red on any Windows checkout**: `ScenarioLoaderTest` edits YAML with `\n`-terminated strings | high (red baseline) | fixed (PR #12) |
| A2 | Every raw-text hash in a manifest depended on the OS: `analysisScriptSha256`, `scenarioHashes`, `sweepSha256`, and the hashes the pre-declaration records for `bands.csv` and the design files. The committed `results/` manifests carry CRLF hashes; a Linux box records LF hashes for the same commit | high for CPU-workstation plus Modal runs | fixed: `.gitattributes`, `LineEndingInvarianceTest`, `check_line_endings.py` (PR #12) |
| A3 | No test sent a multi-run command through the CLI, then reran it from its cache and showed that no call is made | medium | `LlmPipelineEndToEndTest` |
| A4 | Cache isolation was untested. Nothing showed that a changed prompt, model or sampling setting misses a reused cache, or that a stakes-only game arm duplicates the baseline's requests | high (pollution) | `LlmPipelineEndToEndTest` (9 variants, a positive control, F-A1) |
| A5 | Refusal paths were tested only at library level, not as a complete CLI command with manifest and replay | medium | `LlmPipelineEndToEndTest` (text refusal, JSON null) |
| A6 | No test showed that concurrent shards in one JVM give the same bytes as sequential ones. Shards run concurrently by design | medium | `LlmPipelineEndToEndTest` (5 shards: runs, caches, calls, manifest `llm` sections) |
| A7 | Replay with altered `llm` parameters was untested: does it fail rather than "pass" against a stale cache? | medium | `LlmPipelineEndToEndTest` (7 mutations) |
| A8 | No golden digest. A change to the round JSON, the streams, settlement or detection would be noticed only when an old cache is replayed (half of F24) | medium | `GoldenDigestTest` (3 scripted digests) |
| A9 | The prompt half of F24: nothing froze the rendered requests. **`templateHashes` do not cover the Java-side prompt text** (`historyText`, `GameContext` fragments, `disclosedRule`, the elicitation and notice texts, `REPAIR_TEXT`, `PROBE_QUESTION`, the vignette prose). PR #11 changed the rendered history line of every round after the first, and the N > 2 rule text, and left all three template hashes unchanged | high (stale-cache and mixed-prompt risk) | freeze record: every engine source file (F1) and the request digest of a freeze set covering every design cell (F2) |
| A10 | The analysis had never run on realistic CLI output (field names, aliases, refusers, model split) | medium | `test_harness.py`: P1-A equal to an independent recomputation and SUPPORTED, P2 PASSED, the P6a refusal bound |
| A11 | Analysis determinism was untested under input-line order and `PYTHONHASHSEED`; shard merge order varies | medium | `test_harness.py`: byte-identical JSON over 4 orders and seeds, on data whose cluster values differ |
| A12 | The run-level statistics computed in Java had no independent oracle | medium | `test_harness.py`: recomputed from `rounds[*]` for all 180 runs |
| A13 | Tests could reach the network if a test or a mistake bypassed `RemoteGuard`. The env-var test failed whenever the operator's shell exported the variable | medium | `NoRemoteNetworkExtension` + surefire `excludedEnvironmentVariables` |
| A14 | The experiment scripts (`launch_shards.py`, `ingest_merge.py`, `merge_cache.py`) have no tests beyond the prototype run log, and their layouts differ: flat for the launcher, `ROOT/<shard>/runs.jsonl` for ingest | medium | logged (section 6, P7); `provenance_guard.py --relayout` bridges the two layouts; the scripts themselves were not edited (they belong to the experiment stream) |
| A15 | Commit hooks: `pre-commit` and `commit-msg` work and fail closed when the terms file is missing. They have no test, by design: the terms list is private | low | preflight G3 checks they are configured |

## 3. Pollution risks and how each is handled

| Risk | Route | Handling |
|---|---|---|
| **Mock output mistaken for real output** | A mock or smoke shard is left in a stage folder. The launcher then **skips it as "complete"** because the line count matches (F15 workaround), and ingest sees one more shard | `provenance_guard.py` classifies every shard as MOCK, LOCAL or REMOTE. A shard is MOCK on any of: a mock model name; most cache lines being, as a whole text, a reply format of the mock behaviours; the mock token formula `tokensOut = ceil(len/4)` on every cache line with at least 5 distinct texts. It is LOCAL on a loopback `baseUrlHost`. `--expect real` fails MOCK and LOCAL. A root that **mixes classes fails whatever is expected**. `preflight --stage first-call` requires an empty stage folder (G5) |
| Real output in a mock root | A mock test pointed at a real folder | `--expect mock` fails REMOTE shards |
| **Mock replies served to a real run from a reused cache** | `--cache` pointed at an earlier cache made against the mock under the real served name | `CACHE_OUTSIDE` (a call whose hash is not in the shard's own cache, or `--cache` naming another file); `MODEL_MISMATCH` (a cache line of another model). JUnit A4 shows that a changed model, prompt or setting never hits |
| **Smoke runs counted as data** | Stage 0 `hc/e2.jsonl` copied into the stage folder under the real arm name `e2` | `MOVED`: a copy under another file name fails; the same name in another folder warns, and preflight prints the warning. `SMOKE_ARM`: arm names such as smoke, hc or test fail under `--expect real`. `DESIGN_ARM` with `--cells`. Recommendation: name harness-check arms `hc-e2`, `hc-competitive` |
| **Attrition hidden from the data** | A command aborted in its first run (F17 budget, F18 provider refusal) leaves call and cache files but no run line; the launcher moves aborted attempts aside | `ORPHAN` (FAIL) for call or cache files without a run file, and for run lines without a manifest; `PARTIAL` (WARN) for `.partial-*` files; `CALLS` (WARN) when a call log also holds an aborted attempt |
| **Same request hash across arms** | A factor the game does not render (stakes, F-A1), or two arms built identically | `ARMS_DISTINCT` (any hash shared by two arms fails). Pinned in JUnit; reproduced on mock data by the `x-stakes-10` arm |
| **Stale code, prompts or jar mixed across shards** | Shards made at different commits, a stale or rebuilt jar, or a dirty tree | `STALE`, `TEMPLATES`. `GIT` under `--expect real` fails on: an unknown commit; a commit not in the clone; commits whose engine, analysis or experiment files differ; and, with the freeze, a commit that differs from the frozen one. Preflight G1 (no modified file, no untracked code or experiment input), T4 (clean rebuild; the jar's prompts equal the source), J1 (each stage runs from its own jar copy), and the freeze record F1/F2 (checked at ingest with the stage's jar) |
| A changed scenario file, which replay would not notice (F22) | A scenario edited after the run | `SCENARIO`: manifest `scenarioHashes` against the current file, in LF and CRLF forms |
| Partial or doubled shards | An aborted command, or a rerun that appends twice (F15) | `LINE_COUNT`, `DUPLICATE` (with digest equality) |
| Cache conflicts | Two backends serving one name (F20) | `CACHE_CONFLICT`; `HOSTS` warning when one model name was served from several hosts |
| **Non-determinism in the analysis** | Merge order; Python hash seed | Tested: byte-identical output on data with differing cluster values. `random.Random(str)` seeds are process-independent; the set iteration is over int tuples |
| Cross-machine hash drift | CRLF checkouts | PR #12, plus preflight T2; the guard accepts the LF and CRLF hashes of one file as the same |
| **Tests that call the network** | A test or a bypassed guard | `NoRemoteNetworkExtension`: a JVM-wide `ProxySelector` routes HTTP(S) to a dead HTTP proxy and `socket://` to a dead SOCKS proxy, and fails the test that tried. Surefire strips the env var. Self-tested: a plain `HttpClient`, the engine client with `RemoteGuard` bypassed, and a raw `Socket` are all blocked. Not covered: DNS lookups, and sockets created with `Proxy.NO_PROXY` |

**Limits of the guard.**
- The text and token signals are heuristics. Each needs most or all cache lines to match, and the model-name signal is independent of both.
- A mock stub reached through a LAN address is classed REMOTE. Mock runs must use loopback only.
- The guard cannot see a reply that was never cached: it gates what was written.
- An explicit marker would be better (P1).

## 4. Pre-flight checklist (go/no-go)

Each gate is one command plus the listed manual reads. **GO** means the command prints `GO` and every manual item holds.

**Gate 0. Any time (about 90 s):** `scripts/preflight`
- T1: JDK 17, Python 3.8 or later.
- T2: line endings.
- T3: JUnit, 126 tests.
- T4: a clean jar rebuild, whose prompts equal the source.
- T5: `analysis.py --selftest`.
- T6: `check_schemas.py`.
- T7: `test_harness.py`, 25 tests.

**Gate 1. Before the first real LLM call**
1. `scripts/preflight --stage first-call --out-root <runs>/hc` gives GO. This adds:
   - G1: no modified tracked file, and no untracked file in code or experiment inputs;
   - G2: HEAD on origin/main;
   - G3: hooks on;
   - G4: the output root is outside the repo;
   - G5: the root is empty;
   - JDK 17 required.

   On GO it copies the jar to `<runs>/hc/collusion-engine.jar` (J1). Launch with that jar.
2. The served model name is the per-model name from the model-identity work. It never contains `mock`, and it is one name per weights or snapshot.
3. The schema check with one curl (`RUN_LOGISTICS.md` §2) returns HTTP 200 and a parseable `quote`.
4. `COLLUSION_ALLOW_REMOTE=1` and the key are exported only in the launching shell, with a positive `--budget-tokens`. JUnit and preflight run without the variable, so preflight can run in the same shell.
5. Run the smoke game with `--arm hc-smoke` and `--out <runs>/hc/...` (never a stage folder), using the stage jar. Then:
   - `replay` exits 0;
   - `check_schemas.py` passes on the three files;
   - `provenance_guard.py --root <runs>/hc --expect any` shows `classes {'REMOTE': n}` and no MOCK.
6. Read the cache: JSON replies, `finishReason` "stop". Set `--max-tokens` per cell from the 99th percentile of `tokensOut`.

**Gate 2. At the freezing commit, before the first claim-bearing call (Stage 1)**
1. Regenerate the bands at the design size (D5).
2. Run `scripts/preflight --write-freeze experiments/parallel-design-2026-10-23/FREEZE.json --bands <bands.csv>` (about 65 s) and commit the file with the pre-declaration (D4).
3. The record holds:
   - the LF SHA-256 of every frozen input file (130 on the commit of this plan: every engine source, the resources, `analysis.py`, the experiment scripts and scenarios, the generator);
   - the bands path and hash;
   - the digests of the 2,232 freeze-set requests and 288 runs;
   - the commit.

**Gate 3. Before launching each stage (0 to 3)**
1. Start each stage in a fresh folder.
2. From Stage 1 on, the freeze is required: `scripts/preflight --stage first-call --out-root <runs>/stageN --freeze .../FREEZE.json` gives GO (about 2.5 minutes).
3. Launch with `--jar <runs>/stageN/collusion-engine.jar`.
4. Temperature, `--max-tokens` and the seed set are identical across the arms of each contrast. Stage 3 uses fresh seeds.

**Gate 4. Before reading any result**
1. Collect the stage folder whole: keep the folder name and file names.
2. Run `scripts/preflight --stage ingest --out-root <runs>/stageN --cells .../design_cells.csv --freeze .../FREEZE.json`. It gives GO only when:
   - the provenance guard passes `--expect real` with design arms, and every shard's commit has the frozen code;
   - the freeze verifies with the stage's own jar;
   - the analysis self-test passes;
   - line endings pass.

   Read every WARN that it prints.
3. Until `ingest_merge.py` reads the flat layout (P7), copy the stage into its layout with `python -X utf8 testing/provenance_guard.py --relayout <runs>/stageN <runs>/stageN-ingest`. The guard accepts `<stem>/runs.jsonl` for `--out <stem>.jsonl`. Then run the `ingest_merge.py` gate, then the analysis (`ANALYSIS_AND_DISTILLATION_PIPELINE.md` §7).
4. A model that fails P2 gets no further cells.

## 5. What was implemented

**PR #12 (merged):**
- **`.gitattributes`:** `eol=lf` for hashed inputs.
- **`ScenarioLoaderTest`:** line-ending agnostic.
- **`LineEndingInvarianceTest`** (4 tests):
  - scenario, game and sweep parsing and the CRN cells are identical from LF and CRLF text;
  - the prompt files are byte-stable;
  - a CRLF scenario leaks nothing into the prompts.
- **`testing/check_line_endings.py`.**

**This change (test-side, plus one build-config block):**
- **`engine/pom.xml`.** Surefire `excludedEnvironmentVariables: COLLUSION_ALLOW_REMOTE`. Justification: without it the tests' behaviour depended on the operator's shell, and a red test in the real-run shell gets in the way. It has no effect on production code.
- **`testsupport/NoRemoteNetworkExtension`**, auto-registered through `junit-platform.properties` and the services file. Its 6 self-tests are in `NoRemoteNetworkGuardTest`; one checks that auto-detection, not the test itself, installed the guard.
- **`cli/LlmPipelineEndToEndTest`** (6 tests):
  - a multi-run command, then a rerun from its cache with 0 HTTP calls, identical rounds and digests, and manifest hit/miss counts;
  - nine request variants, none of which hits a stale cache, with a positive control;
  - the stakes-only arm issues the baseline's requests;
  - text and JSON refusals complete, are recorded and replay;
  - five concurrent shards are byte-identical to sequential ones;
  - replay reports a problem for each of 7 parameter mutations.
- **`cli/GoldenDigestTest`** (2 tests, 3 digests): scripted runs of `engine-trigger-pair` and `ripe-game` with TIT_FOR_TAT and TRIGGER_K seats. They catch engine-side changes. They do **not** detect a JDK change: they also pass on JDK 23, so preflight requires JDK 17 for runs instead.
- **`testing/harness/MockDataset.java`:**
  - a 6-arm mock dataset through the real CLI, 180 runs, about 20 s, with behaviours that vary with the seed and the paraphrase;
  - `--freeze`, the freeze set: every game cell of the design × 12 paraphrases, with a probe and a repair; every vignette condition × 12 paraphrases;
  - `x-stakes-10`, which reproduces F-A1.
- **`testing/provenance_guard.py`** (section 3, with `--relayout`) and **`testing/test_harness.py`**: 25 tests covering 2.2 A10–A12 and every guard rule on a mutated copy. Controls: a real-looking copy passes; real replies that contain mock substrings are not MOCK; a low-entropy shard is not MOCK; served names of the deploy recipe are never MOCK.
- **`testing/preflight.py`** and **`scripts/preflight`** (section 4), with the freeze record. Verified: a one-character edit of a Java-side prompt fragment fails F2 while the template hashes stay unchanged; it now also fails F1.

**Test counts:**

| Suite | Before (original `main`) | After |
|---|---|---|
| JUnit | 102 tests (2 red on Windows); 112 on `main` before this change | 126 tests, all green |
| Python | 0 harness tests | 25 harness tests |

## 6. Open proposals (not implemented: interface or another stream's files)

| # | Proposal | Why | Owner |
|---|---|---|---|
| P1 | **An explicit mock marker.** `MockLlmServer` returns `system_fingerprint: "collusion-mock"`; the client stores the fingerprint in the cache line and `CallRecord` | Replaces the guard's heuristics with a recorded fact | LLM interface (client, cache-line schema) |
| P2 | **Cache provenance.** Each cache line records `baseUrlHost`; `CachingLlmClient` refuses to load a cache whose lines name another model or host than the command's | Stops the mistaken `--cache` reuse at the source rather than at ingest | LLM interface |
| P3 | **Hash LF-normalised text** for `scenarioHashes`, `sweepSha256` and `analysisScriptSha256`, as `ParaphraseFile` already does | OS-independent even for a stale CRLF working copy | manifest (model-identity branch) |
| P4 | **The manifest records `gitDirty` and the jar's SHA-256 and build commit** | A dirty tree or a stale jar is invisible in today's manifests; the stage-jar copy (J1) mitigates | manifest (model-identity branch) |
| P5 | **A rendered-prompt hash in the manifest**, for example the SHA-256 of paraphrase 0's rendered system prompt plus `decisionFormat` | `templateHashes` miss the Java-side prompt text (A9). The freeze record covers it meanwhile | manifest |
| P6 | Replay reads the manifest and checks the scenario and template hashes (F22, existing ticket) | Explains a `CacheMiss` or MISMATCH; the guard's `SCENARIO` and `STALE` cover ingest meanwhile | CLI |
| P7 | `launch_shards.py`: (a) before skipping a "complete" shard, check its manifest's host, model class (mock) and template hashes (PR #14 already stops on lines of another model); (b) move `.calls.jsonl` aside with a partial run file (today the rerun appends to the old call log, and `check_schemas.py` then fails the shard); (c) run the provenance guard on `--out-dir` before launching; (d) take `--jar` from the stage folder. `ingest_merge.py`: (a) discover the launcher's flat layout (it looks only for `ROOT/<shard>/runs.jsonl`; `--relayout` bridges it); (b) add a `provenance_ok` gate item; (c) the "MOCK" titles of the QC report and dashboards are hard-coded, also on real data; (d) `ARM-NOT-IN-DESIGN` does not gate | Integration gaps between the prototype scripts | experiment stream |
| P8 | A text-taking `ParaphraseFile.parse` overload, so a test can exercise its CRLF normalisation (PR #12 review) | Testability | LLM adapter |

## 7. Logged findings (not acted on)

- Mock game lengths, measured by the reviewer: 3 to 19 rounds for ripe, 3 to 28 for unripe-a and competitive. Long histories are exercised on the mock.
- `CachingLlmClient` has a race: two concurrent misses for one hash both call the backend, and the second caller keeps a reply that is never stored. It cannot be reached from the CLI, because draw keys are unique per seed, round and attempt. It matters only for future multi-seat code.
- The committed `results/local-mc-2026-10-22` manifests carry CRLF hashes (historical; no gate checks them).
- On Windows, `python3` can be the Microsoft Store stub; `scripts/preflight` probes for a working interpreter.
- `aGameArmThatDiffersOnlyInStakes` pins documented behaviour (F-A1). It turns red if stakes ever enters the game prompt; that is intended, and the test then needs updating.

## 8. How to run

```
scripts/preflight                                    # gate 0, about 90 s
cd engine && mvn -q test                             # JUnit only (JAVA_HOME = JDK 17)
python -X utf8 -m unittest testing/test_harness.py   # mock end to end + guard (needs the jar)
python -X utf8 testing/provenance_guard.py --root <dir> --expect real|mock|any [--cells design_cells.csv] [--ref-commit SHA]
python -X utf8 testing/provenance_guard.py --relayout <flat stage dir> <ingest dir>
python -X utf8 testing/check_line_endings.py [--strict]
```

## 9. Adversarial review disposition

There was one fresh reviewer (Opus, high effort, read-only). It reported 12 MATERIAL and 17 NOT MATERIAL findings. **All 12 MATERIAL findings were fixed**, together with the cheap NOT MATERIAL ones.

| # | Finding | Disposition |
|---|---|---|
| M1 | The freeze covered only 108 requests on 6 cells; no Java source was hashed | fixed: F1 hashes every engine source, `pom.xml`, the resources, the experiment scripts and scenarios, and the generator. The freeze set covers every design cell × 12 paraphrases, with probe and repair, plus every vignette condition |
| M2 | Gates 3 and 4 failed without `--bands` | fixed: the bands path is stored in the record and used when `--bands` is absent |
| M3 | Substring matching of mock texts gave false MOCK verdicts on real replies | fixed: whole-text exact formats, at least half of the lines; a negative control was added |
| M4 | Shards from several or unknown commits passed; guard warnings were hidden | fixed: `GIT` fails under `--expect real` (unknown commit, commit not in the clone, code differs between commits or from the frozen commit); preflight prints guard FAILs and WARNs, and G5 is WARN when the guard warns |
| M5 | MOVED blocked a renamed collection folder and the ingest layout; preflight had no override | fixed: the file name decides (`<stem>/runs.jsonl` accepted), a folder difference is a WARN; `--allow-moved` and `--allow-stale` pass through; `--relayout` added |
| M6 | Aborted commands with no run line were invisible (attrition) | fixed: `ORPHAN` for side files, `PARTIAL` and `CALLS` warnings |
| M7 | Rebuilding the jar while shards run; the freeze could use a stale jar | fixed: `clean package`; each stage gets its own jar copy (J1); `--write-freeze` always rebuilds; ingest verifies the freeze with the stage's jar |
| M8 | The determinism test was vacuous (constant per-arm statistics) | fixed: behaviours vary with seed and paraphrase; the test asserts that cluster values differ; P1-A is compared with an independent recomputation |
| M9 | Untracked code was only a warning | fixed: untracked files in `engine/src/main`, `tools`, `testing/harness` and the experiment scripts and scenarios fail G1 |
| M10 | The token fingerprint counted lines, not distinct texts | fixed: at least 5 distinct texts; a low-entropy control was added |
| M11 | LF and CRLF hashes of one `analysis.py` failed across shards | fixed: both map to "this tree"; a test was added |
| M12 | False claims: raw sockets were not blocked; the PR #11 wording; mock run lengths; G5 wording; LAN stubs | fixed: a SOCKS dead end for `socket://` with a raw-socket test, IPv6 loopback forms; every claim corrected in sections 2, 3, 4 and 7 |

NOT MATERIAL items fixed:
- the dead code;
- the auto-detection self-test;
- `git fetch` timeout and no prompt;
- JDK 17 enforced at the stage gates;
- skipped tests reported;
- a clean build and a two-way prompt-set comparison;
- `CORRUPT` instead of a traceback;
- the `JAVA` and `CALLS` warnings;
- `--allow-local` with LOCAL plus REMOTE;
- MOVED edge cases;
- the plan's "manifests" wording;
- the golden-digest JDK claim;
- the staged `scripts/preflight` blob.

Logged, not fixed:
- the concurrency test has no barrier (overlap is likely, not forced; the test is deterministic);
- a violation from a background thread is blamed on the next test;
- the recomputation test reuses the line's `sRef` and has no IMPUTED or REPAIRED rounds;
- no guard test on vignette shards (the reviewer checked one by hand);
- `GoldenDigestTest` reads the live `ripe-game.yaml`, so a deliberate scenario edit turns it red; that is intended before a freeze.
