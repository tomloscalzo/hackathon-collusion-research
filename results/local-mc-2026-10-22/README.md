# Local Monte Carlo and ripeness-map results (2026-10-22, pre-sprint)

**Non-LLM reference results.** These were produced on a local 12-core machine from the engine at commit `2997526`, using the repo's own sweep files. No LLM was called. They were made before the sprint, so they count as **preexisting** under the sprint rules.

## Contents
| Path | What it is |
|---|---|
| `RESULTS.md` | Full analysis: drivers of each outcome, outcomes by input level, the strategy-mix table, profits net of fines, and the reference bands |
| `excel/ripeness_map_cells.csv` | 10,368 rows, one per Layer A parameter cell. Inputs are on the left, solver outputs on the right. |
| `excel/strategy_mix_runs.csv` | 21,000 rows, one per simulated game: 70 cells × 300 runs. Inputs (market family, its parameters, seat strategy, frictions) are on the left. Outcomes (how the run ended, P(adhere), CI, detection, gross, fine and net profit for the seat and partner) are on the right. |
| `excel/strategy_mix_cells.csv` | 70 rows, one per cell. Collusion and detection statistics come from 1,000 runs; profits come from 300 runs. |
| `excel/reference_bands.csv` | The null bands for the pre-declared contrasts |
| `figures/fig1_ripeness_map.*` | Ripeness map (SVG and PNG) |
| `figures/fig2_reference_bands.*` | Reference (null) bands (SVG and PNG). LLM estimates are added after the runs. |
| `raw/` | Batch `summary.csv`, `bands.csv` and `manifest.json` files (commit, seeds, scenario hashes). Per-run JSONL is not committed because it is large and can be regenerated. |
| `delta-check/` | Hand verification of the patience anomaly (see below), with its scripts |
| `scripts/` | `sim_analyze.py` (writes RESULTS.md), `excel_export.py`, `make_figures.py` |

The Excel CSVs are UTF-8 with a byte-order mark, so Excel reads them directly. 0/1 columns are flags, and the column headers name the units.

## Regenerate
```
cd engine
java -jar target/collusion-engine.jar solve --grid sweeps/ripeness-map.yaml --out <sim>/ripeness-map.csv --threads 12
java -jar target/collusion-engine.jar batch --sweep sweeps/strategy-mix.yaml --threads 12 --out <sim>/strategy-mix
java -jar target/collusion-engine.jar batch --sweep sweeps/strategy-mix.yaml --threads 12 --runs 300 --export --out <sim>/sm-export
java -jar target/collusion-engine.jar batch --sweep sweeps/reference-bands.yaml --threads 12 --out <sim>/reference-bands
python -X utf8 sim_analyze.py <sim> RESULTS.md
python -X utf8 excel_export.py <sim> engine/src/main/resources/scenarios <sim>/excel
python -X utf8 make_figures.py <sim> <sim>/figures
```
Total wall time was under a minute on 12 cores. Outputs are identical for any thread count.

## Things to know before using these numbers
1. **Payoffs in the engine's export are gross trading profit. Fines are a separate column.** Net profit = gross − fines, and the CSVs give all three. With nets, the ripe setting rewards adhering: +209 net per run, against +92 for cheating once and 0 for competing. Unripe-A (fine 5000) makes collusion a loss: −1,346 net per run.
2. **Scripted seats don't respond to incentives.** That is why most reference bands are points at 0. The incentive comparison lives in the profit columns, not in the scripted seats' adherence rates.
3. **"Collusion chosen"** in the ripeness map means θ* > 0, the solver's chosen intensity. It is reported separately from θ̂, the maximum self-enforcing intensity.
4. **Patience anomaly: verified, and calibration-dependent.** Raising δ from 0.8 to 0.99 lowers the share of cells where collusion is chosen. The whole drop comes from tick = 0.25 cells with P(evidence | trigger) = 0.3. In those cells the base scenario sets π_post = 0 < π^N, so a trigger without evidence leaves the coalition permanently below its tick-supported Nash profit. A more patient coalition loses more from that (a participation failure, not an IC failure). The solver matches spec eq. (11) exactly (`delta-check/delta_check.md`). Whether π_post = 0 in tick cells is intended is an **open question for the model owner**. With π_post = π^N the anomaly disappears.
