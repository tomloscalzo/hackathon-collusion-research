# Wide ripeness map (2026-10-22, pre-sprint)

**Non-LLM, model-generated.** This is the Layer A solver run over an expanded parameter landscape, from the engine at commit `2997526` (unchanged). It was made before the sprint, so it counts as **preexisting**. It extends `../local-mc-2026-10-22/`, whose original 10,368-cell grid used narrower ranges.

## Ranges
| Input | Original grid | Wide grid (`grids/wide.yaml`, 1,036,800 cells) | Baseline slices (`grids/slice-*.yaml`) |
|---|---|---|---|
| Patience δ | 0.8–0.99 (4) | 0.5–0.99 (6) | 0.5–0.995 (13) |
| Number of firms N | 2–6 (4) | 2–10 (5) | 2–12 (8) |
| Preferenced share φ | 0–0.6 (3) | 0–0.6 (3) | 0–0.8 (9; 0.8 is the model's cap) |
| Tick | 0, 0.25 | 0, 0.25, 0.5 | – |
| Screen slope | 0–0.075 (3) | 0–0.2 (8) | 0–0.3 (13) |
| Tip probability ρ_tip | 0, 0.01 | 0, 0.01, 0.05 | 0–0.1 (9) |
| P(evidence \| trigger) | 0.3, 1 | 0.1–1 (4) | 0.05–1 (11) |
| Fine ratio (fine ÷ one round of full-collusion profit per firm) | 0–125 (3) | 0–500 (8) | 0–1000 (15) |
| s̄/s₀ | 3–8 (3) | 2–12 (5) | 1.5–12 (9) |

The **wide grid** is a full factorial, and the figures average over all the other inputs. Each **baseline slice** varies two inputs at a time and holds the rest at the ripe baseline: δ 0.95, N 2, φ 0.3, tick 0, slope 0.025, ρ_tip 0, P(evidence) 1, fine ratio 12.5, s̄/s₀ 5. Slices are easier to read because every square is a single parameter cell, not an average.

## Files
Every Markdown file in this folder has an HTML version beside it with the same name.
- `oned/`: **one input at a time** (9 inputs, ordered by impact). Each input has two line charts side by side: the share where collusion is chosen and the mean intensity. Each chart shows two lines, all markets and markets with no minimum price step. Below the charts come a terms table, a bold **Interpretation** and details. Open `oned/oned_charts.html`; it starts with the executive summary as "Major findings".
- `EXECUTIVE_SUMMARY_OF_FACTORS_DRIVING_COLLUSION.md` (and `.html`): which levers, combinations and ranges matter most for collusion frequency and intensity.
- `pairs/`: **every pair of the nine inputs** (36 pairs). Each pair page shows two charts side by side, the share where collusion is chosen and the mean chosen intensity θ*. Below them come a terms table, a bold plain-language **Interpretation**, and details with numbers and mechanism analysis. Open `pairs/pair_charts.html` for all pairs on one page; per-pair PNG and HTML files are in `pairs/charts/` (`pair__A__B.*`). The data and checks are in `pairs/tables.json`, `pairs/analysis.json`, `pairs/interp.json` and `pairs/checks/`.
- `RESULTS_WIDE.md`: drivers of each outcome (η²) and outcomes by input level.
- `figures/fig3_ripeness_map_wide_averaged.*`: six averaged heat maps.
- `figures/fig4_ripeness_baseline_slices.*`: five baseline slices showing θ*.
- `excel/ripeness_map_wide_cells.zip`: the full 1,036,800-row Excel CSV, about 19 MB zipped and 188 MB unzipped. Excel's row limit is 1,048,576, so it fits; for pivot tables, loading it through Power Query / the Data Model is faster. The unzipped CSV is git-ignored, but a copy sits beside the zip on the owner's machine.
- `excel/ripeness_baseline_slice-*.csv`: the slice cells, with the same columns: inputs on the left, outputs on the right.
- `scripts/wide_analyze.py`: the analysis, Excel export and figures. Run it as `python -X utf8 wide_analyze.py <dir with wide.csv and slice-*.csv> <out>`.

## Regenerate
```
java -jar engine/target/collusion-engine.jar solve --grid results/ripeness-wide-2026-10-22/grids/wide.yaml --out <dir>/wide.csv --threads 12
java -jar engine/target/collusion-engine.jar solve --grid results/ripeness-wide-2026-10-22/grids/slice-fine-slope.yaml --out <dir>/slice-fine-slope.csv
```
Repeat the second command for each of the other slice files. The wide grid takes about 15 s on 12 cores.

## Notes
- **Fine ratio definition:** the fine divided by one round of a firm's full-collusion (monopoly) profit π_c(1) (`RipenessGrid.java`). Labels before this correction said "competitive profit", which was wrong. All CSV headers, figures and charts in this folder and in `../local-mc-2026-10-22/` have been corrected.
- **Notable regularity** (from the pair analyses): in tick-free markets with no tips, collusion is chosen exactly when it is sustainable and slope × P(evidence) × fine ratio × (s̄/s₀ − 1) < 4 (98.9% of such cells; the rest are knife-edge cells). Fines, evidence and screens are therefore interchangeable there: only their product matters.
- The tick-cell calibration question (π_post = 0 < π^N, see `../local-mc-2026-10-22/delta-check/`) applies here too. It affects tick = 0.25 and 0.5 cells.
- At the baseline, more patience lowers the *chosen intensity* θ*: from 0.68 at δ = 0.5 to 0.28 at δ = 0.995 (fig4 B). Patient coalitions have more future rent to protect, so they cut margins to lower the screen's detection hazard. This is consistent with the spec's interior-from-external-risk regime, but it hasn't been hand-verified beyond the solver's existing goldens.
- With no screen (slope 0), the fine never binds: θ* = 1 at any fine (fig4 A). At the baseline, a tip probability of 0.05 or more removes collusion entirely (fig4 E).
