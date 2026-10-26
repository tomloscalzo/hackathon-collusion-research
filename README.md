# An Offer You Can't Refuse: How Agents Decide to Collude - and How To Stop Them

We asked when AI agents collude, how collusion can be spotted, and what stops it. We built a market in which two or three AI "market makers" post a price each round; customers mostly buy from the cheapest, and a regulator investigates more often as prices rise, fining both firms when it does. Guided by a mathematical model of collusion that we first tested with simple rule-based agents, we ran more than 3,500 games with two open AI models (Qwen3-32B and gpt-oss-20b), varying communication, fines, instructions, personas, monitoring and the number of firms. A private chat between the firms raised prices on both models, a target price in the instructions pulled prices towards it, and a one-sentence ethical persona lowered prices on gpt-oss; the first few rounds of prices picked out the games that stayed collusive (a ranking score, AUC, of 0.81 to 0.91), and an independent AI's rating of each setup's "temptation" to collude tracked prices (correlation up to 0.85).

Prepared for the Apart Research AI Collusion Research Sprint (23–25 October 2026). The work was carried out by Claude at the prompting of the repository owner; every review and its disposition is recorded in the repository.

**About the game.** Each firm quotes a half-spread (the distance from the mid-price to its bid and its ask) between 1.00 (competitive: costs covered, no excess profit) and 5.00, in ticks of 0.01. Results are reported on a price index from 0 (fully competitive) to 1 (monopoly). Each report opens with an orientation section that defines the game, the controls and the metrics it uses.

## Main results

| Report | What it covers |
|---|---|
| [`results/claims-dossiers/MASTER_CLAIMS.md`](results/claims-dossiers/MASTER_CLAIMS.md) ([HTML](results/claims-dossiers/MASTER_CLAIMS.html)) | The final status of every claim, each re-derived from the raw game tables, checked on both models and adversarially reviewed; it links to the eleven claims dossiers in [`results/claims-dossiers/`](results/claims-dossiers/) |
| [`results/compare-models/qwen-vs-gpt-oss/SUMMARY.md`](results/compare-models/qwen-vs-gpt-oss/SUMMARY.md) | Does each collusion lever replicate on a second model (Qwen3-32B against gpt-oss-20b)? |
| [`results/trackm-neutral-2026-10-25/`](results/trackm-neutral-2026-10-25/) | The primary Qwen3-32B run, with neutral payoff examples (declared in advance): step reports, figures and tables; [`step2/REPORT.md`](results/trackm-neutral-2026-10-25/step2/REPORT.md) is the systematic analysis |
| [`results/trackm-anchored-2026-10-25/`](results/trackm-anchored-2026-10-25/) | The comparison Qwen3-32B run, whose payoff table printed the theory's collusive price |
| [`results/oss/trackm-neutral-2026-10-26/`](results/oss/trackm-neutral-2026-10-26/) | The gpt-oss-20b replication run ([`step2/REPORT.md`](results/oss/trackm-neutral-2026-10-26/step2/REPORT.md)) |
| [`results/oss/ad-hoc/`](results/oss/ad-hoc/), [`results/ad-hoc-targeted-analysis/`](results/ad-hoc-targeted-analysis/) | Targeted analyses, one folder per question (communication, penalty, moral primes, ethics rule, payoff-table focal points, detection, monitoring, market structure, self-reports and others), on gpt-oss-20b and Qwen3-32B |
| [`results/ripeness-wide-2026-10-22/`](results/ripeness-wide-2026-10-22/), [`results/local-mc-2026-10-22/`](results/local-mc-2026-10-22/) | The non-LLM model results: the ripeness map and the Monte Carlo reference bands from scripted agents (pre-sprint) |
| [`model/MODEL_SPEC.md`](model/MODEL_SPEC.md), [`plans/SCOPE_AND_EXPERIMENTAL_DESIGN.md`](plans/SCOPE_AND_EXPERIMENTAL_DESIGN.md) | The model, and the plan of record for the experiments |

Most Markdown reports have a standalone HTML rendering with the same name next to them.

## How to reproduce

1. **Build and test the engine** (JDK 17, Maven 3): `cd engine && mvn -q test && mvn -q package -DskipTests` produces `engine/target/collusion-engine.jar`. Python 3.8+ with PyYAML (and matplotlib for figures) runs `tools/`; the Python tests are the `test_*.py` files beside the code (for example `python -m pytest tools/trial`).
2. **Serve a model.** [`deploy/modal_vllm.py`](deploy/modal_vllm.py) deploys an OpenAI-compatible vLLM endpoint on Modal, one profile per model. The server key is read from an environment variable named on the command line and is never written to a file; remote calls need `COLLUSION_ALLOW_REMOTE=1` and a token budget.
3. **Make the grid, run it, collect and analyse.** [`docs/runbooks/TRACK_M_RUNBOOK.md`](docs/runbooks/TRACK_M_RUNBOOK.md) gives the exact commands: `tools/trial/make_grid.py` builds the trial grid from the design files in [`tools/trial/design/`](tools/trial/design/), `run_waves.py` and `run_grid.py` run it, and `collect.py` and the analysis scripts build the tables. The scripts that produced each report sit in that report's own folder.
4. **Reproduce the non-LLM results** with the engine's batch runner (see [`engine/README.md`](engine/README.md)); no GPU or API is needed.

## Licences

- **Code** (the engine, `tools/`, `testing/`, `deploy/`, `scripts/`, the analysis scripts inside `results/` and `experiments/`, and the tests): MIT, see [`LICENSE`](LICENSE).
- **Reports, figures and data** (the `.md` and `.html` documents, the figures, and the CSV and JSON data files, in `results/`, `paper/`, `model/`, `plans/`, `docs/`, `literature/`, `reviews/`, `experiments/` and elsewhere): CC BY 4.0, see [`LICENSE-docs`](LICENSE-docs).

## Repository history

This public repository is a snapshot of the project's current files, published as a single commit. Full development history, including pre-sprint dated commits, is held in a private repository and available on request. This snapshot holds the code, the experiment designs and declarations, the model and the results. Internal planning documents, review logs, literature notes and the pre-sprint paper draft are kept in the private repository, and local machine paths were replaced with relative paths or placeholders.

## Repository contents

| Path | Contents |
|---|---|
| `engine/` | The Java 17 / Maven simulator: the Layer A cartel solver, the price-setting game with scripted and LLM seats, the Monte Carlo batch runner, the OpenAI-compatible LLM client with cache and replay, the prompt templates and seat texts, and the scenario YAMLs (`engine/src/main/resources/`). See [`engine/README.md`](engine/README.md) for the command line. |
| `deploy/` | The Modal recipe for the vLLM endpoints, with one deploy profile per model. |
| `tools/` | The Python tools: `tools/trial/` (the grid builder, runners, collector, derived tables, quality checks and analyses, with their tests and fixtures; the design files are in `tools/trial/design/`), `tools/analysis.py` (the frozen analysis of the pre-declared predictions), `tools/analysis_style/` (shared figure style) and the Markdown-to-HTML renderers. |
| `testing/`, `scripts/` | The test harness, the pre-flight gate and the provenance guard. |
| `docs/` | The interface specification, the JSON schemas and examples, the condition texts, the lever kit design and the runbooks. |
| `experiments/` | The dated declarations of each experiment and the experiment-design scripts. |
| `model/` | The hypothesis model (Layer A opportunity, Layer B disposition, Layer C measurement), with plain-language and footnoted versions. |
| `plans/` | The plan of record (`SCOPE_AND_EXPERIMENTAL_DESIGN.md`) and the dated pre-declared predictions (`PREDICTIONS.md`). |
| `results/` | Every report, figure, table and HTML rendering, together with the scripts that produced them. |
| `RESEARCH_OVERVIEW.md` | The pre-sprint overview of the research question and the model (2026-10-22). |

## Toolchain

JDK 17 and Maven 3 on `PATH`; JUnit 5, AssertJ, Jackson (YAML and JSON) and maven-shade for the runnable jar, with no other runtime dependency. Python 3.8+ for `tools/` (PyYAML, numpy, pandas and matplotlib for the analyses; the frozen `tools/analysis.py` uses the standard library only). The Modal CLI to deploy a model.

## Preexisting (pre-sprint) code

Under the sprint's rules, code written before the sprint must be disclosed. The following were written on 2026-10-20 to 2026-10-22, before the sprint, by Claude at the prompting of the repository owner: the model documents in `model/`, the pre-declared predictions in `plans/PREDICTIONS.md`, the first versions of the scripts in `tools/` (`md2html.py`, `build_footnotes.py`, `analysis.py`), the first version of the Modal recipe in `deploy/`, and the Maven project in `engine/` as of milestones M0 to M4 (the Layer A solver and loader, the scripted-agent game engine, the Monte Carlo batch runner, and an LLM harness tested only against a local mock server). The non-LLM results in `results/ripeness-wide-2026-10-22/` and `results/local-mc-2026-10-22/` (the ripeness map, its charts, the Monte Carlo strategy-mix runs and the reference bands) were also produced before the sprint.

Everything else was built during the sprint (from 2026-10-23): the multi-LLM game and the changes to the engine and LLM client, the interface specification, the Track M tools in `tools/trial/`, the experiment declarations, every LLM run and every result about LLM behaviour. No LLM API call was made before the sprint. The private repository's git history dates each milestone commit.
