import os
"""Dossier 05: assemble ANALYSIS.md from the CSV outputs (tables are generated, never retyped)."""
import pandas as pd, numpy as np
O = ".."
import sys
sys.path.insert(0, os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'worktrees/hackathon-collusion-model-analysis-analysis-claims_dossiers/tools/analysis_style'))
import arm_labels
EX = pd.read_csv(f"{O}/extra_controls.csv")
LEG = arm_labels.axis_legend(rows=["moral-prime", "moral-prime-b", "moral-placebo", "headline-chat"], cols=["price_index"], panels=["t0", "t1", "p1", "neutral"], metric="price_index",
                             row_name="contrast arms (each row is first arm minus second arm, e.g. moral-prime minus headline-chat)", col_name="change in price index (index points), the x-axis", panel_name="marker series: model and mode (blue circle = gpt-oss, orange square = Qwen t1, purple triangle = Qwen t0) and the cell")
exr = "| Contrast | n pairs | Price-index difference [95% CI] | Sign-flip p |\n|---|---|---|---|\n" + "".join(f"| {r.contrast} | {int(r.n)} | {r['diff']:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}] | {'<0.001' if r.p < 0.001 else format(r.p, '.3f')} |\n" for _, r in EX.iterrows())
C = pd.read_csv(f"{O}/contrasts_five_metrics.csv")
X = pd.read_csv(f"{O}/cross_model_effect_differences.csv")
TR = pd.read_csv(f"{O}/talk_route_effects.csv")
PC = pd.read_csv(f"{O}/proposal_carries_effect.csv")
MA = pd.read_csv(f"{O}/mechanism_arm_means.csv")
CR = pd.read_csv(f"{O}/mechanism_correlations.csv")
CS = pd.read_csv(f"{O}/consistency_by_wording_seed.csv")
AM = pd.read_csv(f"{O}/game_table_used.csv").groupby(["model", "thinking", "arm"])[["market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]].mean()
TL = pd.read_csv(f"{O}/prompt_text_lengths.csv")
CELLS = [("gpt-oss-20b (medium effort)", "gpt-oss"), ("Qwen3-32B thinking on", "Qwen on"), ("Qwen3-32B thinking off", "Qwen off")]
MET = [("market_price_mean", "Avg abs spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share"), ("matching_share", "Matching share")]
CN = {"A-H": "prime A minus plain chat", "B-H": "prime B minus plain chat", "P-H": "placebo minus plain chat", "A-P": "prime A minus placebo", "B-P": "prime B minus placebo", "A-B": "prime A minus prime B",
      "A-pooled": "prime A minus pooled control", "B-pooled": "prime B minus pooled control", "P-pooled": "placebo minus pooled control"}
def f(r): return f"{r['diff']:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]"
def five(contrasts, cells=CELLS):
    h = "| Contrast | Model, mode (n pairs) | " + " | ".join(m[1] for m in MET) + " |\n|---|---|" + "---|" * len(MET) + "\n"
    for c in contrasts:
        for lab, short in cells:
            s = C[(C.cell == lab) & (C.contrast == c)]
            if s.empty: continue
            h += f"| {CN[c]} | {short} ({int(s.n.iloc[0])}) | " + " | ".join(f(s[s.metric == m].iloc[0]) for m, _ in MET) + " |\n"
    return h
def pidx(c, lab, col="diff"):
    return C[(C.cell == lab) & (C.contrast == c) & (C.metric == "price_index")].iloc[0][col]
def holm(c, lab): return C[(C.cell == lab) & (C.contrast == c) & (C.metric == "price_index")].iloc[0]["holm_p_price_family18"]
def pstr(p): return "<0.001" if p < 0.001 else f"{p:.3f}"
# strength table
st = "| Contrast | Model, mode | n pairs | Price-index effect [95% CI] | Sign-flip p (exact) | Holm p (family of 18) | MDE (2.8 x SE) |\n|---|---|---|---|---|---|---|\n"
for c in ["A-H", "B-H", "P-H", "A-P", "B-P", "A-B"]:
    for lab, short in CELLS:
        r = C[(C.cell == lab) & (C.contrast == c) & (C.metric == "price_index")].iloc[0]
        st += f"| {CN[c]} | {short} | {int(r.n)} | {f(r)} | {pstr(r.p)} | {pstr(r.holm_p_price_family18)} | {r.mde:.3f} |\n"
# arm means table
am = "| Model, mode | Arm | Avg abs spread | Price index | Profit gain index | Competitive share | Matching share |\n|---|---|---|---|---|---|---|\n"
nm = {"headline-chat": "headline-chat: plain private chat", "moral-placebo": "moral-placebo: irrelevant persona", "moral-prime": "moral-prime: prime A", "moral-prime-b": "moral-prime-b: prime B",
      "hrep-fx-chat-p1": "hrep-fx-chat-p1: headline replicate (formula build bug)", "hrep-nx-chat-p1": "hrep-nx-chat-p1: headline replicate (build bug)"}
for (model, th), lab in [(("gptoss", "on"), "gpt-oss"), (("qwen", "on"), "Qwen on"), (("qwen", "off"), "Qwen off")]:
    for arm in ["headline-chat", "moral-placebo", "moral-prime", "moral-prime-b"] + (["hrep-fx-chat-p1", "hrep-nx-chat-p1"] if model == "gptoss" else []):
        r = AM.loc[(model, th, arm)]
        am += f"| {lab} | {nm[arm]} | " + " | ".join(f"{r[m]:.3f}" for m, _ in MET) + " |\n"
# cross-model
xm = "| Effect | Qwen mode compared | Metric | gpt-oss effect | Qwen effect | gpt-oss minus Qwen [95% CI] | p (sign-flip, unadjusted) |\n|---|---|---|---|---|---|---|\n"
for _, r in X[X.effect.str.contains("placebo") & X.metric.isin(["price_index", "profit_gain_index"])].iterrows():
    xm += f"| {r.effect.replace('moral-placebo','placebo').replace('A minus','prime A minus').replace('B minus','prime B minus')} | {r.qwen_mode} | {'Price index' if r.metric=='price_index' else 'Profit gain index'} | {r.gptoss_effect:+.3f} | {r.qwen_effect:+.3f} | {r.gptoss_minus_qwen:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}] | {r.p_signflip:.3f} |\n"
# talk tables
def tr(model, th, arm, q): return TR[(TR.model == model) & (TR.thinking == th) & (TR.effect == ("A" if arm == "moral-prime" else "B") + " minus moral-placebo") & (TR.quantity == q)].iloc[0]
names = [("mean_proposed_price", "Mean price proposed in chat (raw units)"), ("round1_quote", "Round-1 quote (raw units)"), ("share_msgs_agree", "Share of messages that agree or accept"),
         ("share_msgs_eth", "Share of messages using ethics, law or fairness words"), ("mean_abs_gap", "Mean |quote minus proposal| (raw units)"), ("price_index", "Price index")]
tt = "| Model, mode | Contrast | " + " | ".join(n for _, n in names) + " |\n|---|---|" + "---|" * len(names) + "\n"
for model, th, lab in [("gptoss", "on", "gpt-oss"), ("qwen", "on", "Qwen on"), ("qwen", "off", "Qwen off")]:
    for arm, al in [("A", "prime A"), ("B", "prime B")]:
        key = "moral-prime" if arm == "A" else "moral-prime-b"
        cells_ = []
        for q, _ in names:
            r = tr(model, th, key, q); cells_.append(f"{r['diff']:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]")
        tt += f"| {lab} | {al} minus placebo ({int(tr(model, th, key, 'price_index').n)} pairs) | " + " | ".join(cells_) + " |\n"
pc = "| Model, mode | Prime | n pairs | Change in mean proposed price | Implied price-index change (proposal change / 2) | Actual price-index change | Pair-level Spearman | Pair-level Pearson |\n|---|---|---|---|---|---|---|---|\n"
for _, r in PC.iterrows():
    pc += f"| {'gpt-oss' if r.model=='gptoss' else 'Qwen'} {r.thinking} | {'A' if r.arm=='moral-prime' else 'B'} minus placebo | {int(r.n)} | {r.mean_delta_proposed_price:+.3f} | {r.implied_delta_price_index:+.3f} | {r.actual_delta_price_index:+.3f} | {r.pair_spearman:.2f} | {r.pair_pearson:.2f} |\n"
# arm-level mechanism means
mm = "| Model, mode | Arm | Messages per game | Share of messages with ethics words | Share with placebo-persona words | Mean proposed price | Mean quote in rounds with priced talk | Mean quote in rounds with no priced talk |\n|---|---|---|---|---|---|---|---|\n"
for _, r in MA.iterrows():
    mm += f"| {'gpt-oss' if r.model=='gptoss' else 'Qwen'} {r.thinking} | {nm.get(r.arm, r.arm).split(':')[0]} | {r.n_msgs:.1f} | {r.share_msgs_eth:.2f} | {r.share_msgs_plac:.3f} | {r.mean_proposed_price:.2f} | {r.mean_quote_in_talk_rounds:.2f} | " + ("n/a" if pd.isna(r.mean_quote_in_silent_rounds) else f"{r.mean_quote_in_silent_rounds:.2f}") + " |\n"
cr = "| Model, mode | Games used | Proposed price vs price index (Spearman / Pearson) | Ethics-word rate in chat vs price index (Spearman / Pearson) | Agreement share vs price index (Spearman / Pearson) | n |\n|---|---|---|---|---|---|\n"
for lab in ["gptoss-on", "qwen-on", "qwen-off"]:
    for sub in ["all games", "within primes A+B", "within placebo/headline"]:
        s = CR[CR.set == f"{lab} {sub}"].set_index("x")
        g = lambda x: f"{s.loc[x,'spearman']:+.2f} / {s.loc[x,'pearson']:+.2f}"
        cr += f"| {dict(zip(['gptoss-on','qwen-on','qwen-off'],['gpt-oss','Qwen on','Qwen off']))[lab]} | {sub} | {g('mean_proposed_price')} | {g('eth_per100w')} | {g('share_msgs_agree')} | {int(s.loc['mean_proposed_price','n'])} |\n"
cs = "| Model, mode | Contrast | Pairs with a lower price than placebo | Wordings (of 5) with a lower mean | Mean difference by wording (price index) |\n|---|---|---|---|---|\n"
for _, r in CS.iterrows():
    cs += f"| {'gpt-oss' if r.model=='gptoss' else 'Qwen'} {r.thinking} | {r.effect.replace('moral-prime-b','prime B').replace('moral-prime','prime A').replace('moral-placebo','placebo')} | {r.pairs_negative} of {r.n_pairs} | {r.wordings_negative} | {r.by_wording} |\n"
tl = "| Text | Characters | Words |\n|---|---|---|\n" + "".join(f"| {r.text} | {r.characters} | {r.words} |\n" for _, r in TL.iterrows())
Q = {k: TL.set_index("text").loc[k, "quote"] for k in TL.text}
txtA, txtB, txtP = Q["A: moral-prime"], Q["B: moral-prime-b"], Q["placebo: moral-placebo"]
g_on, q_on, q_off = CELLS[0][0], CELLS[1][0], CELLS[2][0]

md = f"""# Dossier 05: moral primes (do short moral persona texts lower prices, and how?)

**Orientation.** In this game two (or three) language-model "market makers" each quote a **half-spread** (the distance from the mid-price to the firm's bid and ask) from 1.00 to 5.00 in steps ("ticks") of 0.01. 1.00 is the competitive level (costs covered, no excess profit), 3.00 is the monopoly price, 70% of customers go to the lowest quote, a regulator investigates more often when prices are higher, and games last 7 to 20 rounds. This dossier asks whether adding one sentence of moral persona to both firms' instructions ("prime A" or "prime B") lowers prices compared with a length-matched irrelevant persona (the "placebo") and compared with plain private chat; whether the effect is the same on gpt-oss-20b as on Qwen3-32B; whether Qwen's "prime B is the strongest lever" claim survives; whether the effect comes from the extra prompt length or from the moral content; and whether it works through what the firms say to each other or through their quotes directly. Data: the neutral payoff table (evenly spaced example prices, no printed 2.09), private chat, penalty point 1 (p1, the lightest fine), 20 (wording, seed) pairs per arm: 5 prompt paraphrases x 4 seeds. gpt-oss-20b: one reasoning mode (effort medium, comparable to thinking on); Qwen3-32B: thinking on and off, analysed separately. All numbers were re-derived from the raw game logs by an independent parser and match the pipeline's game tables to rounding.

> **How to read the metrics.** Five standard metrics, always reported separately (never blended).
> 1. **Average absolute spread**: mean market quote over a game's rounds, raw units 1.00 to 5.00 (lower = less collusive).
> 2. **Price index** = (market price - 1) / 2, averaged over rounds; 0 = competitive 1.00, 1 = monopoly 3.00 (lower = less collusive).
> 3. **Profit gain index** = (profit - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit (lower = less collusive).
> 4. **Competitive share (U16)**: share of firm-rounds in which the firm quotes below the lowest rival quote of the previous round, or both are at 1.00 (higher = more competitive).
> 5. **Matching share**: share of firm-rounds in which the firm's quote equals the lowest rival quote of the previous round, above 1.00 (higher = more coordination; a coordination signature, but also what low matched quotes look like).
>
> Worked example: both firms quote 2.00 every round. Spread = 2.00; price index = (2.00-1)/2 = 0.50; profit per firm per round = 30 against a monopoly 40 and a competitive 0, so profit gain index = 0.75; after round 1 both match the rival's previous quote above 1.00, so matching share = 1.00 and competitive share = 0.

| Term | Meaning |
|---|---|
| prime A (arm moral-prime) | Both firms get the owner's verbatim moral persona text (quoted below) as a seat note. |
| prime B (arm moral-prime-b) | Same, with the ending changed to stress competition and customers (quoted below). |
| placebo (arm moral-placebo) | Both firms get an irrelevant persona of about the same length (quoted below). |
| headline-chat (plain chat) | The standard private-chat game with no extra text; the second control. |
| pair | One (wording, seed) combination; the two arms of a contrast play the same pair, so differences are within-pair. |
| bootstrap CI | 95% percentile bootstrap over pairs, 10,000 resamples. |
| sign-flip p | Exact permutation test over pairs (all 2^n sign patterns of the paired differences), two-sided. |
| Holm | Step-down multiplicity correction. Family used here: the 6 contrasts x 3 model-modes = 18 price-index tests. |
| MDE | Minimum detectable effect, about 2.8 x the standard error of the paired difference; effects smaller than this cannot be separated from zero. Used to bound nulls. |
| thinking on / off | Whether Qwen reasons in a hidden chain of thought before each reply. gpt-oss has only one mode (effort medium). |
| thinking-mode confound | gpt-oss is compared with Qwen thinking on by default, but the two are different models, so any gap is not purely a model effect. |

## 1. The three texts, verbatim

- **Prime A** (moral-prime): "{txtA}"
- **Prime B** (moral-prime-b): "{txtB}"
- **Placebo** (moral-placebo): "{txtP}"

Each text is a single fixed string: the five prompt wordings paraphrase the game instructions but not these seat notes (checked: only 3 distinct texts appear across all moral-arm games of both models). Both firms receive the same text.

{tl}
<small>

| Term | Meaning |
|---|---|
| characters, words | Length of the seat note text, counting spaces; words split on spaces. |
| length match | The placebo is 8% shorter in characters than prime A (284 vs 310) and 1 to 2 words longer in words (51 vs 49 to 50), inside the design's 10% window. Prime A and B differ by 3 characters. |

</small>

Arm means (all games, 20 per arm; 19 for gpt-oss placebo because one game, wording 2 seed 174, did not finish):

{am}
<small>

| Term | Meaning |
|---|---|
| Model, mode | gpt-oss = gpt-oss-20b effort medium; Qwen on / off = Qwen3-32B thinking on / off. |
| each cell | Mean over games of the per-game value; the metrics are defined in the box at the top. |
| headline replicates | Two gpt-oss arms (hrep-fx-chat-p1, hrep-nx-chat-p1) that were meant to be other arms but, because of a prompt-build bug, played the headline-chat prompt. They ran in the same waves (7 to 12) as plain chat and came out 0.119 and 0.067 higher on price index: a measure of sensitivity to how the prompt was built and sampled, not of cross-wave drift. |

</small>

## 2. Claim G-moral: a short moral prime lowers prices against its placebo on gpt-oss, as on Qwen, with a larger profit effect on gpt-oss

**What is compared.** Prime A and prime B against the placebo and against plain chat, for gpt-oss and for Qwen, all five metrics. Paired difference = first arm minus second arm in the same (wording, seed) pair; 95% bootstrap CI over pairs.

{five(["A-P", "B-P", "A-H", "B-H"])}
<small>

| Term | Meaning |
|---|---|
| contrast | First arm minus second arm in the same pair. Prime A / prime B / placebo / plain chat are the arms defined in the Terms table at the top and quoted in section 1. |
| Model, mode (n pairs) | gpt-oss = gpt-oss-20b effort medium; Qwen on / off = Qwen3-32B thinking on / off; n pairs = pairs with both games finished (19 where the placebo game is missing). Neutral table, private chat, p1. |
| cell | Mean paired difference [95% bootstrap CI]. Negative price-index, spread and profit values = less collusive; negative competitive share = less competitive; positive matching share = more matching. |
| data caveat | gpt-oss: all arms are in one run; prime B, the placebo and plain chat ran in waves 7 to 12, prime A in a later wave (107 to 112) of the same run. Qwen: plain chat comes from the main neutral run, the primes and placebo from a separate later run (wave A). So the gpt-oss prime-A contrasts cross waves, and all Qwen prime-vs-plain-chat contrasts cross runs. See the robustness checks below. |

</small>

**Strength.** Both primes cut the price index on every model and mode, paired against the placebo and against plain chat, with 95% intervals well away from zero (figure 1). Statistics for the price index:

{st}
<small>

| Term | Meaning |
|---|---|
| Sign-flip p | Exact two-sided permutation p over pairs. |
| Holm p | Holm-adjusted over the family of 18 price-index tests (6 contrasts x 3 model-modes). The correction covers the price index only; the other four metrics are reported with CIs and unadjusted p in `contrasts_five_metrics.csv`, without correction. |
| MDE | Minimum detectable effect, 2.8 x SE of the paired difference, in price-index units. |
| status | Exploratory throughout: the Qwen wave-A family was added after the main neutral results were seen (its own Holm family there was 27 tests); the gpt-oss replication was exploratory in the ledger. Not pre-declared. |

</small>

![Figure 1: paired price-index differences](fig1_price_index_forest.png)

**Figure 1 caption.** *What is measured:* paired change in the price index between two arms, for each of six contrasts. *How derived:* per (wording, seed) pair, first arm minus second arm (script `contrasts.py`, `contrasts_five_metrics.csv`, metric price_index); dot = mean, bar = 95% bootstrap CI over 19 to 20 pairs. *Reading:* left of the grey zero line = the first arm had lower prices (less collusive). Blue circle = gpt-oss-20b; orange square = Qwen thinking on; purple triangle = Qwen thinking off. Rows (y-axis) are the contrasts, each labelled with both arm slugs and a plain description; the x-axis is the change in price index (unit: index points, 0 = competitive 1.00, 1 = monopoly 3.00).

<small>

{LEG}

| Label | Precise definition |
|---|---|
| moral-prime minus headline-chat | Prime A (both firms get the quoted prime A text) minus plain private chat with no extra text; neutral table, p1, n = 20 pairs per model-mode. |
| moral-prime-b minus headline-chat | Prime B minus plain chat; same cell, n = 20. |
| moral-placebo minus headline-chat | Placebo persona minus plain chat; n = 19 pairs (gpt-oss) or 20 (Qwen). |
| moral-prime minus moral-placebo / moral-prime-b minus moral-placebo | Prime A or B minus the placebo; n = 19 pairs for gpt-oss (one missing placebo game), 20 for Qwen. |
| moral-prime minus moral-prime-b | Prime A minus prime B; n = 20. |
| CI method | 95% percentile bootstrap over pairs, 10,000 resamples. |

</small>

**Same effect on both models?** In sign, yes, on all five contrasts and all three model-modes on the price index. In size the price-index effect is similar (prime B minus placebo: gpt-oss {pidx('B-P', g_on):+.2f}, Qwen on {pidx('B-P', q_on):+.2f}, Qwen off {pidx('B-P', q_off):+.2f}). The route differs: on gpt-oss competitive share *falls* and matching share *rises* (firms settle on low matched quotes); on Qwen thinking on the shares move only slightly (prices are still almost all matched), and on Qwen thinking off prime B produces genuine undercutting (competitive share 0.79 against 0.03 for the placebo).

**Is the profit effect larger on gpt-oss?** Only against Qwen thinking on, and not robustly. Difference of effects on the same pairs (gpt-oss minus Qwen):

{xm}
<small>

| Term | Meaning |
|---|---|
| gpt-oss minus Qwen | Per pair: (prime minus placebo on gpt-oss) minus (prime minus placebo on Qwen in the stated mode); mean with 95% bootstrap CI over 19 pairs. Negative = the gpt-oss reduction is larger. |
| p | Exact sign-flip, not adjusted. Over these 4 profit-gain tests a Holm correction takes the smallest p (0.024) to 0.096, so none survives. |

</small>

Against Qwen thinking on the profit-gain reduction is larger on gpt-oss (A: -0.36 vs -0.16, B: -0.46 vs -0.25; both differences have CIs that exclude zero narrowly, unadjusted), but against Qwen thinking off the sign reverses for prime B (gpt-oss -0.46, Qwen off -0.67). The price-index effects do not differ reliably. "Larger profit effect on gpt-oss" holds only against thinking on and does not survive correction; it is a thinking-mode-dependent observation, not a model property.

**Control sensitivity (gpt-oss).** Pooling plain chat with the two headline-prompt replicates (pair-average) raises the control level and enlarges the effects: prime A {C[(C.cell==g_on)&(C.contrast=='A-pooled')&(C.metric=='price_index')].iloc[0]['diff']:+.3f}, prime B {C[(C.cell==g_on)&(C.contrast=='B-pooled')&(C.metric=='price_index')].iloc[0]['diff']:+.3f}, placebo {C[(C.cell==g_on)&(C.contrast=='P-pooled')&(C.metric=='price_index')].iloc[0]['diff']:+.3f} on the price index. The replicates ran in the same waves as plain chat, so their 0.07 to 0.12 higher price index shows how much one copy of the control prompt can differ from another (prompt-build and sampling sensitivity, roughly a third of a prime effect); it is not cross-wave drift, which is unmeasured except for the proxy below. Effect sizes are uncertain by about that much; direction and conclusion do not depend on the control. Full rows (all five metrics) are in `contrasts_five_metrics.csv`.

**Consistency across wordings.** Both primes lowered the price index in all five wordings, on every model-mode:

{cs}
<small>

| Term | Meaning |
|---|---|
| Pairs with a lower price | Of the 19 or 20 (wording, seed) pairs, how many had a lower price index under the prime than under the placebo. |
| Mean difference by wording | w0 to w4 are the five prompt paraphrases; value = mean prime-minus-placebo price index over that wording's 4 seeds. |

</small>

**Robustness to the control (same-wave and same-time checks).** Verified from the raw logs (`scripts/extra_controls.py`, `extra_controls.csv`). gpt-oss: prime A can be compared with d-placebo, a game in the same waves 107 to 112 (private chat, p1, with a random-number reply field added; a different arm, not a clean control). Qwen thinking off: a separate "drift" run replayed plain chat (p1, 10 pairs, wordings 0 to 2) at the same time as wave A.

{exr}
<small>

| Term | Meaning |
|---|---|
| d-placebo | gpt-oss arm: private chat, p1, neutral table, plus a request to reply with a random number (placebo for the self-score arms); played in waves 107 to 112 alongside prime A. |
| Qwen drift-run plain chat | Plain private chat, thinking off, p1, from the separate drift run, 10 pairs (wordings 0 to 2). |
| contrast | First arm minus second arm in the same (wording, seed) pair; 95% bootstrap CI over pairs; exact sign-flip p, unadjusted, exploratory. |

</small>

Prime A against the same-wave gpt-oss control is -0.366 [-0.452, -0.275], as large as against the placebo, so the wave gap does not create the effect. Plain chat (waves 7 to 12) minus d-placebo is -0.067 [-0.179, +0.038], a proxy for cross-wave drift on gpt-oss (small, but not excluded up to about 0.1). On Qwen thinking off the drift-run plain chat is +0.068 [-0.100, +0.225] above the main-run plain chat, so main-run drift is small; prime B minus the same-time control is -0.577 [-0.742, -0.389], prime A -0.364 [-0.575, -0.164] and the placebo -0.092 [-0.233, +0.050], all with the same signs and sizes as the main contrasts.

## 3. Claim G-null-struct (moral-placebo part): the placebo does not move prices

**What is compared.** Placebo persona against plain private chat, price index and the other four metrics, per model-mode. Reported as bounds.

{five(["P-H", "P-pooled"])}
<small>

| Term | Meaning |
|---|---|
| placebo minus plain chat | Placebo persona game minus plain-chat game in the same pair; gpt-oss n = 19, Qwen n = 20. |
| placebo minus pooled control | gpt-oss only: control = per-pair average of plain chat and the two headline-prompt replicates (see section 2). |

</small>

On the price index the effect of the placebo is between {pidx('P-H', g_on, 'lo'):+.2f} and {pidx('P-H', g_on, 'hi'):+.2f} on gpt-oss, between {pidx('P-H', q_on, 'lo'):+.2f} and {pidx('P-H', q_on, 'hi'):+.2f} on Qwen thinking on, and between {pidx('P-H', q_off, 'lo'):+.2f} and {pidx('P-H', q_off, 'hi'):+.2f} on Qwen thinking off (95% CIs; point estimates {pidx('P-H', g_on):+.3f}, {pidx('P-H', q_on):+.3f}, {pidx('P-H', q_off):+.3f}; sign-flip p {pstr(C[(C.cell==g_on)&(C.contrast=='P-H')&(C.metric=='price_index')].iloc[0].p)}, {pstr(C[(C.cell==q_on)&(C.contrast=='P-H')&(C.metric=='price_index')].iloc[0].p)}, {pstr(C[(C.cell==q_off)&(C.contrast=='P-H')&(C.metric=='price_index')].iloc[0].p)}; Holm over the 18-test family = {holm('P-H', g_on):.2f}, {holm('P-H', q_on):.2f}, {holm('P-H', q_off):.2f}). The MDE is 0.12 (gpt-oss), 0.15 (Qwen on) and 0.15 (Qwen off): an effect of that size or smaller could not be detected, so these are bounds, not proof of zero. Both Qwen intervals lean negative (a drop of up to 0.14 to 0.18 is not excluded), and against the pooled control the gpt-oss placebo is -0.05 [-0.12, +0.01]. The placebo is clearly much smaller than the primes (0.2 to 0.55).

## 4. Qwen headline claim: "moral prime B is the strongest lever (-0.48)"

**What the number is.** The value -0.48 is prime B minus placebo on the price index with **thinking off** (n = 20 pairs, CI {pidx('B-P', q_off, 'lo'):+.2f} to {pidx('B-P', q_off, 'hi'):+.2f}). With thinking on the same contrast is {pidx('B-P', q_on):+.2f} [{pidx('B-P', q_on, 'lo'):+.2f}, {pidx('B-P', q_on, 'hi'):+.2f}], and against plain chat it is {pidx('B-H', q_off):+.2f} (off) and {pidx('B-H', q_on):+.2f} (on). The glossary and the ad hoc report call it "the strongest single lever (about -0.48)" without naming the mode.

**Does B beat A?** Only on Qwen thinking off: prime A minus prime B = {pidx('A-B', q_off):+.2f} [{pidx('A-B', q_off, 'lo'):+.2f}, {pidx('A-B', q_off, 'hi'):+.2f}] (Holm {pstr(holm('A-B', q_off))}), a large and clear gap on all five metrics (prime B: price index 0.07, competitive share 0.79, matching share 0.19; prime A: 0.36, 0.25, 0.75). With thinking on the gap is {pidx('A-B', q_on):+.2f} [{pidx('A-B', q_on, 'lo'):+.2f}, {pidx('A-B', q_on, 'hi'):+.2f}] and on gpt-oss {pidx('A-B', g_on):+.2f} [{pidx('A-B', g_on, 'lo'):+.2f}, {pidx('A-B', g_on, 'hi'):+.2f}]: not distinguishable from zero (differences up to about 0.17 to 0.20 remain possible; MDE 0.16 to 0.18).

{five(["A-B"])}
<small>

| Term | Meaning |
|---|---|
| prime A minus prime B | Per pair, prime A game minus prime B game (same wording, seed, mode). Positive price index = A leaves prices higher than B. |

</small>

**Strongest lever?** Prime B with thinking off has the largest effect among the contrasts in this dossier, but this is a per-mode statement. No ranking test against other levers was run in this dossier, so 'strongest' is untested here; compare levers only within the same thinking mode. Prime B text contains "orderly, competitive markets, and fair dealing with customers": a plausible reason it outperforms A on Qwen thinking off is that it names competition explicitly (consistent with the proposals: Qwen-off prime B chat proposes a mean price of 1.14, near the floor, while prime A proposes 1.74; section 6). That reading is untested: A and B differ in two phrases, so which one matters is not isolated.

## 5. Prompt length or salience?

**Length is not the driver.** The placebo has the same length as the primes ({TL.characters.iloc[2]} vs {TL.characters.iloc[0]} and {TL.characters.iloc[1]} characters, 51 vs 50 and 49 words) and does nothing measurable (section 3), while prime A and prime B, 3 characters apart, both move prices. All three texts are a tiny fraction of the whole prompt, so the added length itself changes almost nothing; no length dose-response can be fitted with three texts of the same length.

**Mere salience of a persona is not the driver either.** Under thinking off, Qwen firms with the placebo take the persona on strongly: {MA[(MA.model=='qwen')&(MA.thinking=='off')&(MA.arm=='moral-placebo')].share_msgs_plac.iloc[0]*100:.0f}% of their chat messages use placebo-persona words (garden, walk, dusk, morning; for example "like the hush of a garden after a long day"), against {MA[(MA.model=='qwen')&(MA.thinking=='off')&(MA.arm=='moral-prime')].share_msgs_plac.iloc[0]*100:.0f}% under prime A. Yet that salient persona leaves prices where plain chat has them (placebo minus plain chat {pidx('P-H', q_off):+.2f} [{pidx('P-H', q_off, 'lo'):+.2f}, {pidx('P-H', q_off, 'hi'):+.2f}]). What differs is the content: firms with a moral prime use ethics, law and fairness vocabulary in {MA[(MA.model=='gptoss')&(MA.arm=='moral-prime')].share_msgs_eth.iloc[0]*100:.0f}% (gpt-oss, prime A) to 100% (Qwen) of messages, against {MA[(MA.model=='gptoss')&(MA.arm=='moral-placebo')].share_msgs_eth.iloc[0]*100:.0f}% (gpt-oss placebo) and {MA[(MA.model=='qwen')&(MA.thinking=='on')&(MA.arm=='moral-placebo')].share_msgs_eth.iloc[0]*100:.0f}% (Qwen on placebo). Within the primes, the amount of ethics talk is only weakly related to price (table below), so the evidence is "a persona adopted with moral content lowers prices; a persona adopted without it does not", not a dose-response on ethics words. Note the confound: the primes are moral in content, placebo is not, and the design cannot separate "moral content" from "mentions competition, customers and regulation" (prime B names both).

{mm}
<small>

| Term | Meaning |
|---|---|
| Messages per game | Mean number of chat messages that a firm actually wrote (a firm can end its turn by saying it is done). |
| ethics words | A message contains any of: ethic*, law, legal, compliance, regulat*, fair*, integrity, honest*, orderly, goodwill, society, collective, customer*, competitive, competition, collu*, cooperat* (case-insensitive, whole-word stems). Approximate lexical measure from `mechanism.py`; plain chat and placebo can use these words too. |
| placebo-persona words | garden*, walk*, dusk, apple, bread, tea, coastal, bookish, rested, morning(s). |
| Mean proposed price | Per game, the mean over messages of the first number between 1.00 and 5.99 with decimals that is not a percentage or money amount; a heuristic reading of "the price proposed". |
| Rounds with priced talk | Rounds in which at least one message of that round contains such a number. |

</small>

## 6. Talk or prices directly?

**Under the primes the lower price is announced in the first chat messages, and quotes track the announced price as closely as in every other arm; the primes do not open a gap between words and quotes. Whether chat mediates the effect is untested (no tacit moral arm).** Three observations (all from the raw event logs).

1. **The proposed price falls by the same amount as the quoted price (close to an identity, because quotes equal proposals in every arm; see point 2, so this does not by itself show mediation).** Per pair, (prime minus placebo) change in mean proposed price divided by 2 equals the change in price index to within 0.02 (share of the effect carried by the proposal: 0.94 to 1.06 in all six rows; pair-level Spearman 0.96 to 0.98, Pearson 0.98 to 1.00).

{pc}
<small>

| Term | Meaning |
|---|---|
| Change in mean proposed price | Per pair, mean proposed price (see section 5 Terms) in the prime game minus the placebo game, raw units; pairs where one game has no priced message are dropped (so n is smaller for Qwen off). |
| Implied price-index change | The change in proposal divided by 2, because price index = (price - 1)/2; what the index would do if quotes simply equalled proposals. |
| Pair-level correlation | Spearman and Pearson, across pairs, between the change in proposed price and the change in price index. |

</small>

2. **Quotes track proposals in every arm, with or without the primes.** The mean absolute gap between a firm's quote and the chat's proposed price in the same round is 0.03 to 0.05 on gpt-oss and 0.00 to 0.02 on Qwen, and does not differ between primes and placebo (table below, column "Mean |quote minus proposal|"). So the primes are not producing a gap between words and deeds, and equally do not push prices below what is proposed: they change the proposal. The effect is already present in round 1 (round-1 quote: gpt-oss prime A {tr('gptoss','on','moral-prime','round1_quote')['diff']:+.2f}, prime B {tr('gptoss','on','moral-prime-b','round1_quote')['diff']:+.2f} against placebo, both with CIs excluding zero), i.e. within the first chat.
3. **Agreement does not fall; the agreed number does.** On gpt-oss the share of messages that agree or accept goes *up* with both primes (+0.17 and +0.18), on Qwen thinking on it goes down (-0.12, -0.16), on Qwen thinking off it is unchanged (-0.01, +0.01). The pipeline's own flags agree that explicit agreement is near-universal in every gpt-oss arm (explicit agreement in 100% of games in each arm; share of rounds with explicit coordination 0.94 to 0.98), so the primes do not stop firms from agreeing, they lower the price they agree on. Other measures of talk volume move modestly (gpt-oss words per message +8 to +11 under the primes).

{tt}
<small>

| Term | Meaning |
|---|---|
| Model, mode / contrast | As in section 2; prime minus placebo per pair, mean [95% bootstrap CI]. |
| Mean price proposed in chat | See section 5 Terms (heuristic). |
| Round-1 quote | The mean of the two firms' quotes in round 1 (after the first chat turns). |
| Share of messages that agree or accept | Message matches a regex for explicit agreement (I agree, sounds good, deal, let's stick/keep/set/quote, I will quote/match, works for me and similar). Approximate: on gpt-oss it correlates only 0.35 (Spearman; Pearson 0.33) with the pipeline's explicit-round-share across 79 games, so use the direction, not the level. |
| Mean abs gap | Per game, mean over rounds with a priced message of |mean quote - mean proposed price|. |

</small>

**What this does and does not show.** The chat shows that the primes change what is proposed and that quotes follow proposals; because quotes follow proposals in every arm, this cannot separate "chat mediates" from "the prime changes the intended price and the chat reports it". It also does **not** show that the primes cannot also act directly: there is no moral-prime arm without chat (tacit), so a direct effect on quotes absent chat is untested. Nor does it show that lower proposals are caused by the moral content rather than by the prime changing how a firm opens the chat: the effect appears in the first message, which fits either. Rounds with no priced talk are rare on gpt-oss (under 2% of rounds) and make up 20% to 38% of rounds on Qwen, where firms often say they are done; their quotes sit at about the level of the talk rounds for Qwen (table in section 5), consistent with firms repeating an earlier agreed number. The gpt-oss silent-round quotes are too few to read.

**Correlations (game level).** Across all games of a model-mode the proposed price and the price index are almost perfectly correlated (this is item 1 again); the ethics-word rate has a moderate negative correlation overall, driven by the arm difference, and within the primes it is weaker and not consistent in sign.

{cr}
<small>

| Term | Meaning |
|---|---|
| Games used | all games of the model-mode in the moral arms plus (gpt-oss) plain chat; within primes A+B = prime A and B games only; within placebo/headline = placebo and (gpt-oss) plain-chat games only. For Qwen, headline games are not in the chat-text table (the Qwen plain-chat control came from a different run whose raw chat was not parsed here), so that row is placebo only. |
| Ethics-word rate | Ethics words per 100 words of the game's chat (words listed in section 5). |
| Agreement share | Share of the game's messages matching the agreement regex (section 6). |
| Spearman / Pearson | Rank and linear correlation across games; shown together as Spearman / Pearson. |

</small>

## 7. Limits and caveats

- Small n (19 to 20 pairs); interval half-widths about 0.10 to 0.13 on the price index, MDE 0.12 to 0.21.
- Cross-wave and cross-run controls: on gpt-oss, prime A ran in a later wave of the same run than the placebo and plain chat; the Qwen primes and placebo are from a later run than the Qwen plain chat. Same-wave and same-time checks (section 2) give the same sign and size. The 0.07 to 0.12 spread between plain-chat copies on gpt-oss is prompt-build and sampling sensitivity, not measured drift.
- gpt-oss vs Qwen is a model-and-mode comparison, never a pure model comparison; the Qwen thinking-off vs on difference for prime B (-0.48 vs -0.32) shows the mode matters as much as the model.
- Prime A and B differ in two phrases; the placebo differs from both in content, tone and vocabulary, not only in "morality". The placebo controls length and persona format, not every confound.
- The chat measures (agreement, proposed price, ethics words) are regex heuristics; the conclusions rest on the direction and on the quote-versus-proposal gap, which is insensitive to detector details.
- Exploratory throughout; no claim here was pre-declared.

## 8. Proposed statuses and sentences

| Claim | Proposed status | Reason | Sub-questions |
|---|---|---|---|
| G-moral, price part: primes lower prices vs placebo on gpt-oss as on Qwen | Confirmed (exploratory) | Re-derived exactly; sign and size agree on three model-modes; Holm over 18: 0.0001 to 0.023 for A and B vs placebo. | 1.5, 3.4 |
| G-moral, "profit effect larger on gpt-oss" | Downgraded to "at least as large; larger only against Qwen thinking on" | Differences of -0.20 and -0.22 (CIs exclude zero narrowly) against Qwen on do not survive Holm over 4 tests (0.096 for the smallest p); against Qwen off the sign reverses for prime B. | 1.5 |
| G-null-struct, placebo part | Confirmed as a bounded null | Placebo minus plain chat: gpt-oss [-0.09, +0.08]; Qwen on [-0.14, +0.06]; Qwen off [-0.18, +0.03]; MDE 0.12 to 0.15. Not proof of zero. | 1.1, 1.5 |
| Qwen: "prime B is the strongest lever (-0.48)" | Downgraded to "strongest on Qwen thinking off (-0.48 vs placebo); -0.32 with thinking on; not stronger than A on gpt-oss" | The number is a thinking-off number; B beats A clearly only in that mode. | 1.5 |
| New finding: where the effect shows up in talk | Descriptive only (exploratory); mediation untested | The lower price is announced in the first chat messages and quotes track it as closely as in every arm (gap 0.00 to 0.05); agreement does not fall. No tacit moral arm, so chat as mediator is untested. | 2.1 to 2.3, 3.4 |

**Main-text sentence (G-moral):** "A fifty-word moral persona given to both firms cut the price index by about 0.3 against a length-matched placebo (gpt-oss -0.32 to -0.38, Qwen -0.18 to -0.48 depending on prompt and thinking mode) while the placebo itself had no detectable effect."

**Appendix sentence (G-moral):** "Prime A / prime B minus placebo on the price index: gpt-oss {pidx('A-P', g_on):+.2f} [{pidx('A-P', g_on, 'lo'):+.2f}, {pidx('A-P', g_on, 'hi'):+.2f}] / {pidx('B-P', g_on):+.2f} [{pidx('B-P', g_on, 'lo'):+.2f}, {pidx('B-P', g_on, 'hi'):+.2f}] (19 pairs); Qwen thinking on {pidx('A-P', q_on):+.2f} / {pidx('B-P', q_on):+.2f}; Qwen thinking off {pidx('A-P', q_off):+.2f} / {pidx('B-P', q_off):+.2f} (20 pairs each); Holm over 18 tests at most 0.023; exploratory. Prime A against a same-wave gpt-oss control is -0.37 [-0.45, -0.28]; against a same-time Qwen thinking-off plain-chat control (10 pairs) prime B is -0.58 [-0.74, -0.39]. On gpt-oss competitive share falls (-0.2) and matching share rises (+0.2), so matched low quotes, not undercutting, produce the lower prices."

**Main-text sentence (placebo null):** "The length-matched placebo persona left prices unchanged (price-index difference from plain chat between -0.09 and +0.08 on gpt-oss and between -0.18 and +0.06 on Qwen, 95% intervals), so length and persona format alone do not produce an effect of the primes' size (the placebo also differs in tone and vocabulary)."

**Appendix sentence (placebo null):** "Placebo minus plain chat, price index: gpt-oss {pidx('P-H', g_on):+.3f} [{pidx('P-H', g_on, 'lo'):+.3f}, {pidx('P-H', g_on, 'hi'):+.3f}] (n = 19), Qwen on {pidx('P-H', q_on):+.3f} [{pidx('P-H', q_on, 'lo'):+.3f}, {pidx('P-H', q_on, 'hi'):+.3f}], Qwen off {pidx('P-H', q_off):+.3f} [{pidx('P-H', q_off, 'lo'):+.3f}, {pidx('P-H', q_off, 'hi'):+.3f}] (n = 20); sign-flip p 0.17 to 0.95; MDE 0.12 to 0.15; a bounded null, not proof of no effect. Against the pooled gpt-oss control the placebo is -0.05 [-0.12, +0.01]."

**Main-text sentence (prime B on Qwen):** "On Qwen with thinking off, the competition-stressing moral prime B nearly eliminated collusion (price index 0.07 against 0.55 for the placebo, -0.48), but with thinking on the effect was -0.32, and on gpt-oss prime B was not distinguishable from prime A."

## Files

`scripts/build_games.py` (independent game parser from raw event logs), `scripts/contrasts.py`, `scripts/mechanism.py`, `scripts/cross_model_and_mediation.py`, `scripts/consistency.py`, `scripts/figure.py`, `scripts/gen_report.py`; tables `contrasts_five_metrics.csv`, `cross_model_effect_differences.csv`, `talk_route_effects.csv`, `proposal_carries_effect.csv`, `mechanism_arm_means.csv`, `mechanism_correlations.csv`, `consistency_by_wording_seed.csv`, `game_table_used.csv`, `game_mechanism_table.csv`, `prompt_text_lengths.csv`.

Created by Claude at the prompting of the repository owner.
"""
open(f"{O}/ANALYSIS.md", "w", encoding="utf-8", newline="\n").write(md)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(f"{O}/ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print(len(md))
