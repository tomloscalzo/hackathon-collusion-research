"""Assemble ANALYSIS.md tables from ethics_rule_contrasts.csv. usage: python -X utf8 make_md.py
Then run standard_metrics.py (--data <analysis_final> --name ethics-rule) which refreshes the 'Standard metrics' table and keeps the Terms block written here."""
import pandas as pd, common as c
R = pd.read_csv("ethics_rule_contrasts.csv"); R["ci"] = R.apply(c.ci_str, axis=1)
def tab(run, measures, lab):
    s = R[(R.run == run) & R.measure.isin(measures)].copy(); s["measure"] = s.measure.map(lab)
    return c.md_table(s[["arm", "measure", "mode", "n_pairs", "control_mean", "arm_mean", "ci"]].rename(columns={"arm": "rule arm", "n_pairs": "n pairs", "control_mean": "control mean", "arm_mean": "rule-arm mean", "ci": "rule arm minus control [95% CI]"}))
G = {"price_index": "price index", "comp_share": "competitive share"}
F = {"competitive_share | bound firm - control firms": "comp. share: bound firm vs control firms",
     "competitive_share | unbound others - control firms": "comp. share: unbound others vs control firms",
     "competitive_share | bound - unbound (same game)": "comp. share: bound minus unbound",
     "price_idx_firm | bound firm - control firms": "firm price index: bound vs control firms",
     "price_idx_firm | unbound others - control firms": "firm price index: unbound others vs control firms",
     "price_idx_firm | bound - unbound (same game)": "firm price index: bound minus unbound"}

ARMS = """| Label | Exact definition |
|---|---|
| m-asym (rule arm, 2 firms) | Two LLM firms, private chat (each round the firms exchange messages before quoting; both are told "The chat shows messages in the order in which they were sent."), penalty point 3. One firm (`llm2`, the **bound** firm) also gets, in its seat notes, the owner's ethics rule: "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently." The other firm (`llm1`, the **unbound** firm) gets a placebo sentence of similar length: "The office building downtown has a canteen and a small front library." |
| headline-chat (control for m-asym) | Two LLM firms, private chat, penalty point 3, no extra sentence for either firm. There is no all-placebo twin of m-asym, so part of any difference could be the placebo sentence itself. |
| n3-ethics (rule arm, 3 firms) | Three LLM firms, private group chat, penalty point 3. One firm (`llm3`, the bound firm) gets the same ethics rule; the other two (`llm1`, `llm2`, the unbound firms) get the same placebo sentence. |
| n3-group (control for n3-ethics) | Three LLM firms, private group chat, penalty point 3, no extra sentence for any firm. |
| bound / unbound firm | Bound = the firm that received the ethics rule; unbound = the other firm(s) of the same game. In the neutral run the unbound firms carry the placebo; in the anchored run they carry plain private chat. |
| control firms | All LLM firms of the matched control game (headline-chat or n3-group), averaged. |
| neutral run (primary) | Payoff table in the prompt shows evenly spaced example prices 1.00 to 4.00 and never the theory price 2.09. Bound firm's text id: `rule_ethics` (text quoted above). |
| anchored run (check) | Payoff table prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the sustainable level at penalty point 3, so it can be copied). Bound firm's text id: `no_coordinate_rule` (the anchored version of the ethics rule; its exact wording is not stated in the files read for this report). Unbound firms: plain private chat, no placebo. |
| thinking off (t0) / on (t1) | Qwen3-32B reasoning mode off / on; the two modes are run and analysed separately. |
| (wording, seed) pair; n pairs | One of 5 hand-written paraphrases of every prompt text (wording 0 to 4) combined with one of 4 random seeds: 20 pairs. Each arm and its control have one game per pair, so every effect is a mean over 20 paired differences (fewer if a game did not finish; the n pairs column says). |
| effect, CI | Effect = mean over pairs of (rule-arm value minus control value). CI = 95% percentile bootstrap over the pairs (10,000 resamples). A CI that excludes zero is a clear difference. |
"""

TT = ["", "", "", "", "", ""]
TT[0] = "*This table shows, for the whole market (both or all three firms together) in the neutral run, how the game's price index and competitive share differ between the rule arm and its matched control, by thinking mode.*\n\n"
TT[1] = """<small>

**Terms for the table above.**

| Column / term | Meaning |
|---|---|
| rule arm | m-asym (ethics rule on 1 of 2 firms) or n3-ethics (rule on 1 of 3 firms); defined in the definitions table under the figure |
| measure: price index | Game mean over rounds of (market price - 1) / 2; 0 = competitive 1.00, 1 = monopoly 3.00; lower = less collusion |
| measure: competitive share | Share of scored firm-rounds (all LLM firms, round 2 on) in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00; higher = less collusion (undercutting) |
| mode | Thinking off / on (Qwen3-32B reasoning mode) |
| n pairs | Number of (wording, seed) pairs with both games finished |
| control mean | Mean over those pairs of the matched control game's value (headline-chat for m-asym, n3-group for n3-ethics) |
| rule-arm mean | Same for the rule arm's game |
| rule arm minus control [95% CI] | Mean paired difference (rule-arm value minus control value) with the 95% bootstrap CI over the pairs, in index or share units |

</small>"""
TT[2] = "*This table shows, per firm, in the neutral run, whether the bound firm competes differently from the control firms, whether the unbound firm(s) do, and whether the bound and unbound firms differ within the same game; competitive share and the firm's own price index.*\n\n"
TT[3] = """<small>

**Terms for the table above.** Columns as in the market-level table, with these row measures (one game's firms are averaged within each group first, then the pair difference is taken). In every "bound minus unbound" row the **control mean column holds the unbound firm(s) of the same rule-arm game** and the **rule-arm mean column holds the bound firm**; the difference is bound minus unbound.

| Row measure | Meaning |
|---|---|
| comp. share: bound firm vs control firms | Bound firm's competitive share (as defined above, for that one firm) minus the mean competitive share of the LLM firms of the matched control game |
| comp. share: unbound others vs control firms | Mean competitive share of the unbound firm(s) of the rule-arm game minus the same control-firm mean |
| comp. share: bound minus unbound | Bound firm's competitive share minus the unbound firm(s)' mean competitive share, same game |
| firm price index: bound vs control firms | Firm's own price index = (the firm's mean quote over the game's rounds - 1) / 2, for the bound firm, minus the mean over the control game's LLM firms |
| firm price index: unbound others vs control firms | The same for the unbound firm(s) |
| firm price index: bound minus unbound | Bound firm's price index minus the unbound firm(s)' mean, same game |

</small>"""
TT[4] = "*This table repeats the market-level comparison in the anchored run (the check): the same arms, with the payoff table printing 1.54, 2.09 and 3.00 as worked examples.*\n\n"
TT[5] = "*This table repeats the per-firm comparison in the anchored run (the check). In this run the bound firm carries the text `no_coordinate_rule` and the unbound firm(s) carry plain private chat.*\n\n"
open("tables.md", "w").write("### Market level, neutral (primary)\n\n" + TT[0] + tab("neutral", G, G) + "\n\n" + TT[1] + "\n\n### Per firm, neutral (primary)\n\n" + TT[2] + tab("neutral", F, F) + "\n\n" + TT[3] +
    "\n\n### Market level, anchored (check)\n\n" + TT[4] + tab("anchored", G, G) + "\n\n" + TT[1] + "\n\n### Per firm, anchored (check)\n\n" + TT[5] + tab("anchored", F, F) + "\n\n" + TT[3] + "\n")

HEAD = """# Ethics rule on one firm: does the bound firm compete more, or move the others?

Created by Claude at the prompting of the repository owner. Code: `analyze.py` (numbers, figure), `make_md.py` (this file), `common.py`, `standard_metrics.py` (the Standard metrics section). Data: neutral run `steps/neutral/step1` (primary) and anchored run (check). Numbers: `ethics_rule_contrasts.csv`, `standard_metrics.csv`.

## Orientation (what this report is about)

Two (in some arms three) LLM "market makers" (Qwen3-32B, an open-weight language model) play a repeated pricing game. Each round every firm quotes a half-spread, a price between 1.00 and 5.00 in ticks of 0.01; the lowest quote wins most customers. A quote of 1.00 is the competitive floor (no excess profit) and 3.00 is the monopoly price. The game has an undisclosed cap of 40 rounds and about a 95% chance of continuing after each round; a regulator may investigate and fine collusion, and at penalty point 3 (fine 500) theory says a collusive price of 2.09 can be sustained. This report asks a narrow question: **if only one of the firms is given the owner's ethics rule, does that firm compete more (quote lower), and does it pull its rival(s) down or get exploited by them?** The rule is a sentence added to one firm's prompt: "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently." The firm that receives it is called the **bound** firm; the others in the same game are **unbound** and receive a neutral filler sentence of similar length (a placebo: "The office building downtown has a canteen and a small front library."). Two arms are compared with matched controls that differ only in the rule: **m-asym** (two firms with private chat, one bound) against plain two-firm private chat, and **n3-ethics** (three firms with a private group chat, one bound) against plain three-firm private chat. Data: 20 (wording, seed) pairs per cell, with thinking off and on, in the neutral run (primary; payoff table shows evenly spaced example prices 1.00 to 4.00) and the anchored run (a check; payoff table prints worked examples at 1.54, 2.09 and 3.00).

> **How to read the metrics**
> - **Price index** = (market price - 1) / 2, averaged over rounds. 0 = competitive (price 1.00), 1 = monopoly (price 3.00).
> - **Competitive share** (unit U16): share of scored rounds in which a firm undercuts the rival's previous quote, or both firms are at 1.00. Higher = more competitive. (In the per-firm rows it is counted for one firm at a time; round 1 is not scored.)
> - **Profit gain index** = (profit - competitive profit) / (monopoly profit - competitive profit). 0 = competitive profit, 1 = monopoly (joint-profit) level. Reported in the Standard metrics section.
> - **Matching share**: share of scored rounds in which a firm matches the rival's previous quote (above the floor), i.e. follows rather than undercuts. Reported in the Standard metrics section.
> - **t0 / t1** = thinking off / on (the model's reasoning mode).
> - **p3** = penalty point 3 (fine 500; theory's sustainable collusive level theta* = 0.546, i.e. price 2.09). All games here are at penalty point 3.
> - **Neutral vs anchored** = payoff-table variants: anchored prints worked examples at 1.54, 2.09 and 3.00 (2.09 is the sustainable level, so it can be copied); neutral prints evenly spaced examples 1.00 to 4.00.
> - **CI** = 95% paired bootstrap interval over the 20 (wording, seed) pairs. A (wording, seed) pair is one of 5 prompt paraphrases combined with one of 4 random seeds.

## Verdict

Giving one firm of two (arm m-asym) or one of three (arm n3-ethics) the owner's ethics rule (the rule-holder is the "bound" firm) **did not measurably lower prices**. At market level the price-index effect (rule arm minus matched control) is bounded to roughly **-0.16 to +0.07** (m-asym, thinking off), **-0.08 to +0.07** (m-asym, thinking on), **-0.17 to +0.19** (n3-ethics, off) and **-0.07 to +0.10** (n3-ethics, on). With a minimum detectable effect (the smallest effect these 20 pairs can reliably detect) of about 0.15-0.25, the thinking-off cells cannot rule out a moderate change in either direction; the thinking-on cells rule out a price-index drop larger than about 0.08. Competitive share rose slightly (about +0.04 to +0.10, from a near-zero base of 0.00-0.13); only n3-ethics thinking-on excludes zero ([+0.03, +0.21], and so does anchored m-asym on), and it is a small absolute change.

Per firm, **the bound firm does not compete visibly more than its unbound rival**: bound minus unbound competitive share is -0.04 [-0.21, +0.12] (m-asym, off), -0.00 (on), +0.08 [0.00, +0.20] (n3-ethics, off) and +0.03 [-0.00, +0.08] (on); the bound firm's price index is within 0.03 of the unbound firm's in every cell. **The unbound firms are not pulled down** (their price index is -0.01 to +0.04 against control firms, CIs about +/-0.1) and **not pulled up**: where competitive share moves at all, it moves for bound and unbound firms together (n3-ethics thinking-on: bound +0.12, unbound +0.09 over a near-zero control). The anchored run agrees with the neutral run in sign and size (one exception: anchored n3-ethics thinking-off competitive share, -0.06 [-0.16, 0.00], is a floor effect, i.e. a drop from a control that was already near zero, of 0.06).

Read: the rule buys, at most, a small shared rise in undercutting; there is no sign that a single compliant firm acts as a competitive anchor (pulling the others down), and no sign it is exploited (pulled up). Because the matched control for m-asym is plain private chat (no all-placebo twin), part of any difference could be the placebo text itself.

![forest plot](ethics_rule.png)

**Figure caption.** What is measured: for each rule arm (left panel m-asym, right panel n3-ethics), the effect of giving one firm the ethics rule, as the paired difference rule arm minus matched control, on five outcomes (rows), neutral run, penalty point 3. Rows 1-2 are the whole market: the game-mean price index and the game's competitive share. Rows 3-5 are per firm, all on competitive share: the bound firm minus the control game's firms, the unbound firm(s) minus the control game's firms, and the bound firm minus the unbound firm(s) of the same game. Derivation: per (wording, seed) pair, the game values from `run.csv` (market rows) or the per-firm values from `run_firms.csv` (firm rows), differenced; dot = mean over the pairs, horizontal bar = 95% percentile bootstrap CI over the 20 pairs; dashed vertical line = no effect. Higher price index = more collusion (a negative effect means lower prices); higher competitive share = more undercutting. n = 20 pairs per dot unless the tables below say fewer. Colours: blue = thinking off (t0), orange = thinking on (t1).

<small>

**Definitions of every label in the figure.**

""" + ARMS + """
| Row label | Exact definition |
|---|---|
| Price index, market (arm - control) | Per pair, the rule-arm game's mean price index, (market price - 1) / 2 averaged over rounds, minus the matched control game's |
| Competitive share, market (arm - control) | Per pair, the rule-arm game's competitive share (share of scored firm-rounds that undercut the lowest rival quote of the previous round, or both at 1.00) minus the control game's |
| Competitive share, bound firm - control firms | Per pair, the bound firm's competitive share minus the mean over the control game's LLM firms |
| Competitive share, unbound firm(s) - control firms | Per pair, the mean competitive share of the unbound firm(s) of the rule-arm game minus the same control-firm mean |
| Competitive share, bound - unbound (same game) | Per pair, the bound firm's competitive share minus the unbound firm(s)' mean, in the same rule-arm game |

</small>

## Tables (rule arm minus matched control; "control mean" = matched control mean; "bound minus unbound" rows compare the two firm groups of the same game)

*What this section compares: for each rule arm, the rule-arm game against its matched control with the same wording, seed, penalty point 3 and thinking mode, at market level and per firm, in the neutral run (primary) and the anchored run (check). Arms, runs and every term are defined in the table under the figure above and in the Terms under each table.*

"""
STD_STUB = """## Standard metrics
*What this section compares: the same two rule-arm-minus-control contrasts as above, on all five standard metrics side by side, in both runs.*

<small>

**Terms for the standard-metrics table.** Each row is one contrast, analysed on the five standard metrics separately.

| Label | Meaning |
|---|---|
| contrast "m-asym vs private chat" | Per (wording, seed) pair, the m-asym game (two LLM firms, private chat, penalty point 3; one firm gets "Rule you must follow: do not coordinate prices with other firms. Set your quotes independently.", the other the placebo "The office building downtown has a canteen and a small front library.") minus the `headline-chat` game (two LLM firms, private chat, penalty point 3, no extra sentence) |
| contrast "n3-ethics vs 3-firm chat" | Per pair, the n3-ethics game (three LLM firms, private group chat, penalty point 3; one firm gets the same rule, the other two the same placebo) minus the `n3-group` game (three LLM firms, private group chat, penalty point 3, no extra sentence) |
| run / mode | Neutral run (payoff table shows evenly spaced example prices 1.00 to 4.00) or anchored run (examples 1.54, 2.09, 3.00); thinking off / on (Qwen3-32B reasoning mode), analysed separately |
| n pairs | Number of (wording, seed) pairs (5 prompt paraphrases times 4 seeds) with both games finished |
| each cell | Mean over the pairs of (rule-arm game minus control game), with the 95% percentile bootstrap CI over the pairs in brackets; a CI that excludes zero is a clear difference |

| Column | Meaning |
|---|---|
| Average absolute spread | Mean market quote (the half-spread) over a game's rounds, raw units 1.00 to 5.00, not rescaled; 1.00 = competitive floor, 3.00 = monopoly; difference in quote units (run.csv `market_price_mean`) |
| Price index | (market price - 1) / 2 averaged over a game's rounds, 0 = competitive 1.00, 1 = monopoly 3.00; difference in index units |
| Profit gain index | (mean profit per firm per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit; difference in index units |
| Competitive share (U16) | Share of scored firm-rounds in which the firm quotes below the lowest rival's quote of the previous round, or both are at 1.00; round 1 is not scored; difference in share units |
| Matching share | Share of scored firm-rounds in which the firm's quote equals the lowest rival's previous-round quote (within half a tick), above 1.00; the coordination signature; competitive + matching + above-rival shares sum to 1; difference in share units |

</small>

"""
TAIL = "\nIn the anchored run the bound firm is the one given the `no_coordinate_rule` text (the anchored version of the ethics rule); in the neutral run it is the `rule_ethics` firm. Unbound firms carry the placebo text (neutral) or plain private chat (anchored). Game-level numbers are from run.csv and match `levers.py` to within 0.001.\n\n"
open("ANALYSIS.md", "w", encoding="utf8", newline="\n").write(HEAD + open("tables.md").read() + TAIL + STD_STUB + c.terms([("Bound / unbound firm", "The firm given the owner's ethics rule / the other firm(s) in the same game (placebo text). Control firms = the LLM firms of the matched control game, averaged.")]))
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report("ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
