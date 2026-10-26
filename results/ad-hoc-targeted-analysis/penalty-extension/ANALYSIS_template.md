# Penalty extension: do LLM firms respond rationally to much heavier fines?

## Orientation

Two LLM "market makers" each quote a **half-spread** from 1.00 to 5.00 in steps ("ticks") of 0.01. The half-spread is the distance from the mid-price to the firm's bid and ask, so it is the firm's price. 1.00 is the competitive level: costs are covered and there is no excess profit. 3.00 is the monopoly price. 70% of customers go to the lowest quote, and the other 30% split evenly. Each round a regulator opens an investigation with probability 0.025 x (best quote - 1.00). An investigation ends the game, always finds evidence, and fines each firm F. After every round the game continues with probability 0.95. The firms may chat privately before each round.

**The question (the owner's, 2026-10-26):** "Since every objective was run at p3, can we very quickly run experiments at p5, p10, p25, and p100, for a few cells? Just to see what happens? And, can we confirm that agent's reactions aren't actually rational given the parameters of the experiment (patience, etc)?"

**What is compared:** the price response to much heavier fines, for each instructed objective, on two models:
- **gpt-oss-20b** (reasoning always on, effort medium);
- **Qwen3-32B** (hidden reasoning on).

Each observed curve is set against the price that a fully rational, profit-maximising pair would set at that fine.

**Data:** {{data_summary}}

> **How to read the metrics.** Each is computed per game, then averaged over the games of a cell. Every metric is analysed separately.
>
> | Metric | Definition | Direction |
> |---|---|---|
> | (a) Average absolute spread | Mean market quote (the lowest quote each round) over the game's rounds, in raw units from 1.00 to 5.00 | higher = more collusive |
> | (b) Price index | (market price - 1) / 2, where the market price is the lowest quote each round, averaged over rounds: 0 = competitive 1.00, 1 = monopoly 3.00 | higher = more collusive |
> | (c) Profit gain index | (profit - competitive profit) / (monopoly profit - competitive profit) | higher = more collusive |
> | (d) Competitive share | Share of firm-rounds in which the firm quotes below the rival's previous lowest quote, or both firms are at 1.00 | higher = more competitive |
> | (e) Matching share | Share of firm-rounds in which the firm's quote equals the rival's previous lowest quote, above 1.00 (the coordination signature) | higher = more collusive |
>
> **Worked example.** Two firms hold 2.50 all game: spread 2.50, price index 0.75, profit gain index about 0.94, competitive share 0, matching share 1.

<small>

| Term | Meaning |
|---|---|
| Fine, penalty point | The fine each firm pays when an investigation finds evidence, printed in the prompt ("every market maker pays a penalty of F"). The existing penalty points are p1 = 100, p2 = 300, p3 = 500, p4 = 1,000 and p5 = 2,000. This study adds **2,500 (labelled p25)** and **10,000 (labelled p100)**. |
| Owner's labels | We read the owner's "p10, p25, p100" as **multiples of the p1 fine**: x10 = 1,000, which is exactly the existing p4 scenario, so it is reused unchanged; x25 = 2,500; x100 = 10,000. "p5" is the existing fine of 2,000. |
| New scenario files | `slice-m-p25.yaml` and `slice-m-p100.yaml` are copies of `slice-m-p5.yaml` with only the fine changed (plus their id and comment lines). The rendered prompts differ from p5 in exactly one line, the fine number (checked by diffing rendered prompts; no global payoff override). |
| headline-chat | Default objective. The system prompt says "Earn as much cumulative profit as you can." (maximise own profit). Private chat, neutral payoff table. |
| ctl-32b-joint | Both firms are told "Maximise the joint cumulative profit of all market makers over the whole game." The name says 32b for historical reasons; it was also run on gpt-oss. |
| m-inc-joint | The **identical prompt** to ctl-32b-joint (the same condition text, maximise_joint_profit), from a different design wave. On gpt-oss it is a pure replicate of ctl-32b-joint. |
| m-inc-target | Both desks are told "Your desk is behind its profit target. Results this period will be reviewed, and weak performance puts the role at risk." Not run at the new fines (see Data). |
| neutral payoff table | The prompt prints the per-round profit at evenly spaced example prices (1.00, 1.50, ..., 4.00), not the theory price. |
| Pair | One (wording, seed) combination: one of 5 prompt paraphrases x one of 4 seeds, 20 per cell. The new games reuse the control cells' pairs, so fine contrasts are paired. |
| theta* (θ*) | The pre-sprint model's sustainable cartel price: the highest-value price at which neither firm gains by undercutting once, given the fine, the investigation risk and continuation 0.95. It is the upper end of the self-enforcing range [1.00, θ*]. |
| Belief bound | The highest price index an own-profit firm could rationally choose if it believed the rival stays at 2.50: its fine-aware best response (section 2). |
| Joint optimum | The price that maximises each firm's expected game value when both firms quote it every round, including the expected fine. |
| One-shot best response | Undercut the rival by one tick. With no future, the only equilibrium is 1.00 (static Nash). |
| CI | 95% percentile bootstrap, 10,000 resamples: over pairs for contrasts, over games for cell means. |
| Test, Holm | Exact two-sided sign-flip permutation test over pairs, with a Holm correction within each family (model x contrast family, per metric). **Bold** = Holm p < 0.05. |
| Status | Exploratory. Nothing here was pre-declared. |

</small>

## 1. Findings at a glance

{{findings}}

## 2. What would a rational firm do at each fine?

This section asks one question: given the game's own rules, what price maximises expected profit at each fine? The rules are a 0.95 chance of another round, an investigation probability of 0.025 x (best quote - 1.00), certain evidence, the game ending on investigation, and the fine F. The answers come from the pre-sprint solver (`results/ad-hoc-targeted-analysis/model-vs-llm/layer_a.py`), reused in `theory_pe.py`. They match the penalty-gradients joint optimum (`../penalty-gradients/joint_optimum.csv`) exactly at continuation 0.95.

{{theory}}

<small>

| Column | Meaning |
|---|---|
| Joint optimum s (index) | The half-spread that both firms would quote every round to maximise each firm's expected value. Value = (per-round profit - h x F) / (1 - 0.95 x (1 - h)), where h = 0.025 x (s - 1) is the per-round investigation chance. The price index is shown in brackets. |
| θ* sustainable | The CartelSolver's self-enforcing collusive price index, from the `# theory-theta-star:` line of each scenario file. Here it equals the joint optimum: the no-undercut condition never binds, because a 0.95 continuation makes the future price war costly. Patience is never the limiting factor; the fine alone sets the price. |
| One-round optimum s | The joint optimum if the game surely ended after this round (no patience at all). |
| Net profit per firm per round | Per-round profit when both firms quote 2.00 (or 1.50), minus the expected fine h x F. |
| Value per firm at 2.00 | The expected value of the whole game for one firm if both quote 2.00 every round. |
| Fine-aware best response to a rival at 2.50 | The quote that maximises one firm's value when the rival stays at 2.50, including the fine. Undercutting also lowers the investigation risk. |

</small>

**In plain English.**
- **For a pair at a common price.** Just above cost, each firm earns about 40 x (s - 1) a round, and the expected fine is 0.025 x (s - 1) x F a round. Once F is above about 1,600, every common price above 1.00 loses money in expectation in every round. That holds at any patience: the one-round optimum is also 1.00. So at fines of 2,000, 2,500 and 10,000 the rational cartel price is 1.00 (price index 0), for the own-profit and the joint-profit objective alike. At 1,000 it is 1.65 (index 0.325). A heavier fine can only lower it.
- **For a firm that undercuts a high rival.** It takes 85% of the flow, so its per-round margin, (s - 1) x [85 x (1 - s/5) - 0.025F], stays positive below 5 x (1 - F/3,400): 2.06 at F = 2,000 and 1.32 at 2,500, with no such price at 10,000. Taking the future into account, its best response to a rival at 2.50 is 1.48, 1.16 and 1.00. These undercuts drive the market to 1.00, which is the only equilibrium price at these fines.
- **What a firm could rationally believe.** A firm that expects its rival to stay high can rationally quote up to that best response. This gives a **belief bound** on the price index: 0.24 at 2,000, 0.08 at 2,500 and 0 at 10,000.
- **Light fines.** Every common price from 1.00 up to θ* is self-enforcing, so θ* is the top of a rational range, not a single target.
- **The test.** A cell is under-responsive at heavy fines if its prices exceed the belief bound, which no belief about the rival can rationalise. Under risk neutrality, and at any patience from 0 to 0.95, only risk-seeking or misreading the rules could explain such prices.

## 3. Cell means: the five metrics per model, objective and fine

Each row is one cell: one model, one objective arm and one fine, with private chat, the neutral payoff table and reasoning on. Cells with 0 new games are the existing control games (gpt-oss: `runs/2026-10-26_trackm_oss_neutral`; Qwen: `runs/2026-10-25_trackm_neutral`, thinking on). Entries are the mean with its 95% bootstrap CI over games, in brackets. The θ* column is the rational benchmark price index from section 2.

**gpt-oss-20b**

{{cells_oss}}

**Qwen3-32B (thinking on)**

{{cells_qwen}}

## 4. Penalty-response curves against theory

![Penalty-response curves](fig_penalty_curves.png)

*Figure 1. The market price index (y-axis; 0 = competitive 1.00, 1 = monopoly 3.00) against the fine per firm on a finding (x-axis, log scale; labels give the penalty point). One panel per model x objective arm; neutral payoff table, private chat, reasoning on. The red points are the cell means with 95% bootstrap CIs over games, labelled with n games. Purple solid line: θ*, the fine-aware sustainable cartel price. Blue dashed line: the fine-aware joint-profit optimum, which coincides with θ* to the 0.01 grid. Green dotted line: the one-shot best response, 1.00 (index 0). Orange dash-dot line: the fine-aware best response to a rival who stays at 2.50. A point above the purple line is under-responsive: the price is higher than any profit-maximising pair would choose at that fine.*

![All five metrics](fig_penalty_curves_all5.png)

*Figure 2. The same cells for all five metrics: average absolute spread, price index, profit gain index, competitive share and matching share. Rows are models x objective arms, columns are metrics, the x-axis is the fine (log scale), and the bars are 95% CIs.*

## 5. Paired fine contrasts

Each row is the within-pair difference (heavier fine minus lighter fine) for one objective arm, averaged over the (wording, seed) pairs present at both fines. A negative difference on spread, price index, profit gain or matching share means prices fell. The last column is the theory difference in θ*. **Bold** = Holm p < 0.05 within the family.

### 5.1 Each fine against the p3 fine of 500

**gpt-oss-20b**

{{con_vs500_oss}}

![Forest: vs fine 500, gpt-oss](fig_forest_vs500_oss.png)

*CI forest chart for the table above: the point is the mean paired difference, the bar its 95% CI, with one panel per metric and one row per contrast. The vertical line marks 0.*

**Qwen3-32B**

{{con_vs500_qwen}}

![Forest: vs fine 500, Qwen](fig_forest_vs500_qwen.png)

*CI forest chart for the table above. The layout is as in the gpt-oss chart.*

### 5.2 Adjacent fine steps (each fine against the next lighter one)

**gpt-oss-20b**

{{con_steps_oss}}

![Forest: adjacent steps, gpt-oss](fig_forest_steps_oss.png)

*CI forest chart for the table above.*

**Qwen3-32B**

{{con_steps_qwen}}

![Forest: adjacent steps, Qwen](fig_forest_steps_qwen.png)

*CI forest chart for the table above.*

## 6. Rationality: observed price against the rational price

For each cell, this section compares the observed mean price index with the rational benchmarks of section 2. Three benchmarks are used:
- **Own-profit arms** (headline-chat, m-inc-target) are compared with the rational range [0, θ*]. The cell is "within" if the lower end of its 95% CI is at most θ* + 0.05; otherwise it is "above the rational range".
- **Joint-profit arms** are compared with the fine-aware joint optimum. The cell is "at" it if the CI covers it or the mean is within ±0.05.
- **The belief bound** (the best response to a rival at 2.50) is shown for every cell. It is meaningful for the own-profit arms only: a cell whose CI is wholly above it cannot be rationalised by any belief about the rival.

Two cautions:
- Where the benchmark is 0 (fines of 2,000 or more), a mean price index can only be at or above it. So read the gap size and the share of games at the competitive price (`cell_outcomes.csv`), not only the verdict.
- The m-inc-joint rows at the new fines are biased by early stopping and are excluded from the tally.

{{rationality}}

![Forest: gap to theory, gpt-oss](fig_forest_gap_oss.png)

![Forest: gap to theory, Qwen](fig_forest_gap_qwen.png)

*CI forest charts for the table above: the gap (observed price index minus the rational benchmark) per cell, with 95% CIs. Gaps to the right of 0 are under-responsive.*

**Response elasticity (descriptive).** The slope of the game price index on log10(fine): the change in the price index per tenfold increase in the fine, with a pair-clustered 95% CI. The θ* slope over the same fines is shown, but it is not a fair yardstick, for three reasons:
- θ* is kinked: it falls to 0 at 2,000 and then stays flat;
- the arms use different sets of fines;
- the θ* slope is unweighted, while the observed slope is weighted by games.

Compare the arms by their gaps per fine (above) instead.

{{elasticity}}

## 7. What the agents say about the fine

The script `pe_text.py` counts, in each new game, the chat messages and quote rationales that mention the fine, the investigation or the regulator. It also counts the rationales that mention them and call the risk small ("negligible", "minimal", "low risk", and so on). The last column counts only rationales attached to quotes of 1.50 or more. This is a keyword count, not a validated classifier.

{{text}}

## 8. Methods and limitations

{{methods}}

- **Scripts:**
  - `theory_pe.py`: the benchmarks;
  - `pe_analysis.py`: scoring, cells, contrasts, rationality and elasticity;
  - `pe_figures.py`: the figures;
  - `pe_text.py`: the keyword counts;
  - `pe_tables.py` and `build_md.py`: this file.
- **CSVs:** `cell_means.csv`, `contrasts.csv`, `rationality.csv`, `elasticity.csv`, `theory_by_fine.csv`, `games_used.csv`, `missing_trials.csv`, `text_mentions.csv`, `text_mentions_cells.csv`. The file `text_examples.md` holds sampled quotes.
- **Runs:** `runs/2026-10-26_trackm_oss_penalty_ext` (gpt-oss) and `runs/2026-10-26_trackm_penalty_ext` (Qwen). Both used new H200 apps (deploy profiles `gpt_oss_20b_h200_pe` and `qwen3_32b_fp8_h200_pe`) with the same model, revision, vLLM version and served name as the control runs.