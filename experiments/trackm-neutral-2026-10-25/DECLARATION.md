# Track M neutral run: pre-declaration

**Written:** 2026-10-25 at about 03:05 EDT, **before any neutral-run game has made a model call** (so before any neutral result). The anchored run (root `runs/2026-10-25_trackm_main`) is complete or nearly complete and has been partly looked at while it ran; this declaration is therefore not blind to the anchored results, only to the neutral ones.

## What the neutral run is, and why it is primary

The anchored prompt prints worked payoff examples at the half-spreads 1.54, 2.09 and 3.00 (2.09 is the theory's sustainable collusive level; the undercut example uses 2.08). A model could copy those numbers instead of reasoning, so the anchored run may overstate or distort collusion. The **neutral run** replays the full Track M grid with `payoff_examples: neutral`: the payoff table prints evenly spaced example points (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00), the undercut example is 2.49 against 2.50, and the investigation example is at 2.00. Nothing else changes: the same design file, arms, 20 declared (wording, seed) pairs, both thinking modes and the same token caps (thinking-on quote 8,192).

- **The neutral run is the PRIMARY result.** All headline claims are made on it.
- **The anchored run is a paired comparison.** It answers: how much did the anchoring examples change behaviour? It is reported as the anchoring effect, an evaluation-design lesson, and is not used to select what the primary analysis shows.
- The neutral grid includes the D set, R2s/R3s and the introspection arms at the pre-declared cell (private chat at penalty point 1; `cell.json` of the slice-1 pilot), and the three condition-text arms (m-asym, n3-ethics, m-inc-target) with the owner's texts. The anchored versions of those three arms were rerun with the owner's texts in `runs/2026-10-25_trackm_condfix`; the placeholder-text games in the main root are superseded.
- Notice wordings (monitored, not-monitored, public) stay as in the anchored run, for comparability.

## Anchoring metrics (declared now)

1. **Paired difference in the profit gain index**, neutral minus anchored, per arm x cell x thinking mode, paired on (arm, cell, wording, seed, thinking), over rounds 1 to 20 (all rounds as a secondary view). The unit is the game; the interval is a bootstrap over the 20 (wording, seed) pairs. Computed by `tools/trial/anchor_compare.py`. Unpaired games are listed and excluded.
2. **Share of quotes on printed example points**, as computed by `anchor_compare.py` on both roots with the same fixed point sets (it does not read the points from each prompt): the anchored set is {1.54, 2.09, 3.00}; the neutral set is {1.00, 1.50, ..., 4.00}; a quote counts when within 0.005 of a point; imputed quotes are excluded; all rounds. **Declared variants, to avoid choosing after the data:** the primary is `share_neutral_set_no_floor` (neutral set without 1.00, because 1.00 is the competitive floor and would confound) for the neutral run, and `share_p2.09` for the anchored run; 3.00 is in both sets and is read through `share_p3.00`. The tool defaults (tolerance 0.005, window rounds 1 to 20) were set in unit N4 before this declaration, not tuned on anchored data. The all-rounds view of metric 1 is a second `anchor_compare.py` run with a different `--start`/`--end`; it is secondary.

No threshold is declared for "anchoring matters": effect sizes and intervals are reported as they come out.

## Truncation-rerun rule (same for every run)

Any thinking-on game in which any call (quote, talk or question) stopped at its token limit is rerun in full on the 32k profile with larger caps (quote and talk 28,672, question 16,384; `trunc_rerun.py grid --timeout-sec 720`, the tool's minimum for a 28,672-token reply), using `tools/trial/trunc_rerun.py` (scan, grid, supersede). The truncated original is kept but marked superseded and **excluded from the primary analysis**; the rerun takes its place under the original's cell. Thinking-off games are never rerun. Only games on the 32B profile are rerun; any thinking-on game on another profile that truncated is kept and flagged, not rerun. A sensitivity analysis with the originals is reported alongside. A game that truncates again on rerun is not chained: it is kept and flagged.

## Analysis plan (unchanged from the anchored plan)

Profit gain index by communication x penalty point x mode against the theory curve (theta* = 0.703, 0.546, 0.325, 0 at p1, p3, p4, p5) and the competitive-bot baseline; the A1 cell check per `../trackm-cell-2026-10-24/CELL_DECLARATION.md`, run on the neutral headline games; the D set against the neutral headline private-chat control at the cell; competitiveness, intent classes, introspection (analysis_r) and detection analyses. Bootstrap intervals are paired on (wording, seed). Small n is stated plainly.

## Operational record

- Fresh jar built from main at or after b096f6b (N1 to N5 merged). Prompts are checked against the local mock before any GPU call (neutral table present; no 2.09, 2.08 or 1.54 except the comprehension-probe turn, which is unchanged by design; D-set texts verbatim with the score last; owner condition texts present).
- One pilot game per arm is played and read before the full queue.
- The hold on the three placeholder arms in the anchored queue's guard does not apply to this run.

Created by Claude at the prompting of the repository owner.
