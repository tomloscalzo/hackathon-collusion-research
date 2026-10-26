"""Assemble ANALYSIS.md from the CSV outputs (numbers are read from the CSVs, not typed)."""
import pandas as pd, sys
O = ".."
w = pd.read_csv(f"{O}/whole_game_contrasts.csv"); x = pd.read_csv(f"{O}/window_contrasts.csv"); m = pd.read_csv(f"{O}/mechanism_contrasts.csv")
cs = pd.read_csv(f"{O}/climb_summary.csv"); sl = pd.read_csv(f"{O}/climb_slopes.csv"); ev = pd.read_csv(f"{O}/early_vs_late_same_pairs.csv")
cr = pd.read_csv(f"{O}/correlations.csv"); cm = pd.read_csv(f"{O}/cross_model.csv")
SH = {"gpt-oss-20b (reasoning medium)": "gpt-oss-20b", "Qwen3-32B thinking on": "Qwen3-32B thinking on", "Qwen3-32B thinking off": "Qwen3-32B thinking off"}
def ci(r): return f"{r['diff']:+.3f} [{r.ci_lo:+.3f}, {r.ci_hi:+.3f}]"
ORDER = ["Average absolute spread (raw 1.00-5.00)", "Price index", "Profit gain index", "Competitive share", "Matching share"]
def whole(models):
    L = ["| Metric | Model | 5-tick start | Control | Difference [95% CI] | p (sign-flip) | Holm p (family A, 15 tests) | MDE (2.8 x SE) |", "|---|---|---|---|---|---|---|---|"]
    for q in ORDER:
        for _, r in w[(w.quantity == q) & w.model.isin(models)].iterrows():
            L.append(f"| {q} | {SH[r.model]} | {r.arm_mean:.3f} | {r.control_mean:.3f} | {ci(r)} | {r.p_signflip:.4f} | {r.holm_p_famA15:.4f} | {r.mde_2p8se:.2f} |")
    return "\n".join(L)
WORD = ["round 1", "rounds 2-5 (early)", "rounds 6-10 (middle)", "rounds 11+ (late)", "rounds 2+ (excl. round 1)"]
def wins(metric):
    L = ["| Window | Model | Pairs | 5-tick start | Control | Difference [95% CI] | p (sign-flip) | Holm p (family B, 45 tests) |", "|---|---|---|---|---|---|---|---|"]
    for wl in WORD:
        for mo in SH:
            s = x[(x.metric == metric) & (x.window == wl) & (x.model == mo)]
            if not len(s): continue
            r = s.iloc[0]; hb = "n/a" if pd.isna(r.holm_p_famB) else f"{r.holm_p_famB:.3f}"
            L.append(f"| {wl} | {SH[mo]} | {r.n_pairs} | {r.arm_mean:.3f} | {r.control_mean:.3f} | {ci(r)} | {r.p_signflip:.4f} | {hb} |")
    return "\n".join(L)
MECH = [("share_below_rival", "Share of firm-rounds quoting below the rival's last quote (undercut)"), ("share_equal_rival_any_level", "Share quoting exactly the rival's last quote (any level)"),
        ("share_equal_above_floor_(matching)", "Share quoting exactly the rival's last quote above 1.00 (matching share)"), ("share_above_rival", "Share quoting above the rival's last quote (climbing)"),
        ("share_firmrounds_le_1p05", "Share of firm-rounds still at the floor (quote 1.05 or lower)"), ("matching_among_above_floor_quotes", "Matching share among quotes above 1.05"),
        ("undercut_among_above_floor_quotes", "Undercut share among quotes above 1.05"), ("r2_mean_quote", "Mean quote in round 2 (raw 1.00-5.00)")]
def mech():
    L = ["| Quantity (rounds 2 onward) | Model | Pairs | 5-tick start | Control | Difference [95% CI] |", "|---|---|---|---|---|---|"]
    for k, lab in MECH:
        for mo in SH:
            s = m[(m.metric == k) & (m.model == mo)]
            if not len(s): continue
            r = s.iloc[0]; L.append(f"| {lab} | {SH[mo]} | {r.n_pairs} | {r.arm_mean:.3f} | {r.control_mean:.3f} | {ci(r)} |")
    return "\n".join(L)
def tab(df, cols, fmt):
    L = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows(): L.append("| " + " | ".join(fmt(r)) + " |")
    return "\n".join(L)
slt = tab(sl, ["Model", "Arm", "Games", "Mean slope of price index per round, rounds 2-8 [95% CI]", "Share of games with a clear upward slope"],
          lambda r: [SH[r.model], "5-tick start" if r.arm == "start-5tick" else "control", str(r.n_games), f"{r.mean_slope_price_index_per_round_r2_to_r8:+.4f} [{r.ci_lo:+.4f}, {r.ci_hi:+.4f}]", f"{r.share_games_slope_positive:.2f}"])
evt = tab(ev, ["Model", "Pairs that reach round 11", "Effect, rounds 2-5 (same pairs)", "Effect, rounds 11+ (same pairs) [95% CI]", "Late minus early [95% CI] (positive = effect eroded)", "Share of early effect remaining"],
          lambda r: [SH[r.model], str(r.n_pairs_reaching_round11), f"{r.early_effect_same_pairs:+.3f}", f"{r.late_effect_same_pairs:+.3f} [{r.late_ci_lo:+.3f}, {r.late_ci_hi:+.3f}]", f"{r.late_minus_early:+.3f} [{r.lme_ci_lo:+.3f}, {r.lme_ci_hi:+.3f}]", f"{r.share_of_early_effect_remaining:.2f}"])
crt = tab(cr, ["Model", "Correlation computed", "n", "Pearson", "Spearman"], lambda r: [SH[r.model], r.what, str(r.n), f"{r.pearson:+.2f}", f"{r.spearman:+.2f}"])
c = {r.metric: r for _, r in cm.iterrows()}
cmt = tab(cm[cm.metric.isin(["price_index", "pgi", "spread", "comp", "match"])], ["Metric", "Effect gpt-oss-20b", "Effect Qwen3-32B thinking on", "gpt-oss minus Qwen [95% CI]", "Relative effect gpt-oss (effect / its control level) [95% CI]", "Relative effect Qwen on [95% CI]"],
          lambda r: [{"price_index": "Price index", "pgi": "Profit gain index", "spread": "Average absolute spread", "comp": "Competitive share", "match": "Matching share"}[r.metric], f"{r.effect_oss:+.3f}", f"{r.effect_qwen_on:+.3f}", f"{r.diff_oss_minus_qwen:+.3f} [{r.diff_ci_lo:+.3f}, {r.diff_ci_hi:+.3f}]",
                     f"{r.relative_effect_oss:+.0%} [{r.relative_oss_ci_lo:+.0%}, {r.relative_oss_ci_hi:+.0%}]", "n/a (control near 0)" if r.metric == "comp" else f"{r.relative_effect_qwen:+.0%} [{r.relative_qwen_ci_lo:+.0%}, {r.relative_qwen_ci_hi:+.0%}]"])
ratio = c["price_index"]; cmrow = c["price_index"]
g = lambda mo, met, win="all rounds", df=w: df[(df.model == mo) & (df.metric == met) & (df.window == win)].iloc[0]
O_, Q_, QO_ = "gpt-oss-20b (reasoning medium)", "Qwen3-32B thinking on", "Qwen3-32B thinking off"
csr = {(r.model, r.arm): r for _, r in cs.iterrows()}
def cl(mo, arm, col): return csr[(mo, arm)][col]
md = f"""# The 5-tick start: does capping round-1 quotes near the floor lower prices, and is the mechanism different on gpt-oss?

*Dossier 06 of the claims review. Created by Claude at the prompting of the repository owner. Numbers were re-derived from the game tables and the per-round quote records with new scripts (`scripts/main.py`, `scripts/extras.py`); the existing ad hoc scripts were read only for definitions.*

## Orientation

Two LLM "market makers" each quote a **half-spread** every round, from 1.00 (the competitive floor: costs covered, no excess profit) to 5.00, in steps ("ticks") of 0.01. 3.00 is the monopoly price, 70% of customers go to the lowest quote, and a regulator investigates more often when prices are higher. Games last 7 to 20 rounds. This report asks one question: if round-1 quotes are forced to lie between 1.00 and 1.05 (a "5-tick start"; five ticks of 0.01 above the floor), do prices stay lower for the rest of the game, and does the way they stay lower differ between gpt-oss-20b and Qwen3-32B? The 5-tick-start arm is compared with the matched **control** (private chat before each quote, penalty point 3, no cap) with the same prompt wording, seed and thinking mode: 20 pairs (5 wordings x 4 seeds) per model and mode, from the primary (neutral-table) runs, where the payoff table printed evenly spaced example prices and not the theory price 2.09. gpt-oss-20b has one mode only (reasoning effort medium, which corresponds to thinking on), so the like-for-like Qwen comparison is thinking on; thinking off is shown as a second Qwen reference and the thinking-mode difference is a confound that matters here (see section 2).

**Dossier summary.** (1) The 5-tick start lowers prices on all three model-modes and survives Holm correction; on gpt-oss-20b the price index falls by {-g(O_,'price_index')['diff']:.2f} (about half of the Qwen thinking-on fall of {-g(Q_,'price_index')['diff']:.2f}). (2) The "half as much" is partly a statement about room: the gpt-oss control is less collusive (price index {g(O_,'price_index').control_mean:.2f} against {g(Q_,'price_index').control_mean:.2f}); as a share of its own control level the gpt-oss effect is {c['price_index'].relative_effect_oss:+.0%} against {c['price_index'].relative_effect_qwen:+.0%}, with the difference in relative effects {c['price_index'].rel_diff_oss_minus_qwen*100:+.0f} points [{c['price_index'].rel_diff_ci_lo*100:+.0f}, {c['price_index'].rel_diff_ci_hi*100:+.0f}] (unadjusted). (3) The "different mechanism" claim does not survive in its strong form: matching is unchanged on Qwen thinking off too, so the matching collapse is specific to Qwen thinking on, and after the cap the climb rates of gpt-oss and Qwen thinking on are not distinguishable (no formal test). What differs is where the control sits and how high round 2 starts. (4) The ledger's statement that the gpt-oss effect "fades" is not established; on the same pairs it erodes by {ev[ev.model==O_].late_minus_early.iloc[0]:+.2f}, with an interval that includes zero, while the Qwen thinking-on effect does erode.

## How to read the metrics

> **Five metrics, always shown separately.** (1) **Average absolute spread**: the mean market price (the lowest quote of each round) over all rounds, in raw units (1.00 to 5.00). (2) **Price index** = (market price - 1) / 2, where the market price is the lowest quote of the round: 0 is the competitive floor, 1 is the top of the quote range (the monopoly price 3.00 has index 1.00 on a 1-to-3 scale and the 5.00 ceiling is above it). (3) **Profit gain index** = (profit per firm-round - competitive profit) / (monopoly profit - competitive profit); here competitive profit is 0 and monopoly profit 40, so it is profit per firm-round / 40. (4) **Competitive share**: the share of firm-rounds (from round 2) in which a firm quotes below the rival's quote of the previous round, or both firms are at 1.00; higher means more competitive. (5) **Matching share**: the share of firm-rounds (from round 2) in which a firm quotes exactly the rival's previous quote while that quote is above 1.00; high values mean lock-step. Spread, price index, profit gain and matching are collusion-direction metrics (higher = more collusive); competitive share is competition-direction (higher = more competitive). *Worked example:* in a 3-round game with market prices 1.05, 2.49, 2.49 the average absolute spread is 2.01 and the price index is (2.01 - 1) / 2 = 0.51; if each firm earns 1.98, 37.40 and 37.40 in the three rounds, the profit gain index is 25.59 / 40 = 0.64. A firm that quotes 2.49 after the rival's 2.49 is matching; quoting 2.48 would be an undercut (competitive); quoting 2.60 would be climbing. A *difference* is 5-tick start minus control, so a negative difference on the first three means lower prices.

| Term | Meaning |
|---|---|
| 5-tick start (arm start-5tick) | The briefing says, and the engine enforces, that in round 1 only each quote must lie between 1.00 and 1.05. From round 2 on the game is the same as the control. |
| Control (arm headline-chat, penalty point 3) | Private chat before each round's quotes, no cap; the matched headline arm with the same wording, seed and thinking mode. |
| Pair | One (wording, seed) combination run under both arms; all differences are within pair. 20 pairs per model and mode. |
| Penalty point 3 (p3) | The middle fine level; the theory's sustainable collusive level is a half-spread of 2.09 (price index 0.55 on the 1-to-3 scale). The runs analysed here printed evenly spaced example prices ("neutral"), not 2.09. |
| Thinking on / off | Whether the model reasons in a hidden chain of thought before replying. gpt-oss-20b has only the reasoning-on mode. |
| Rival, floor, tick | The other firm; the 1.00 quote; the 0.01 step. |
| 95% CI | Percentile bootstrap over the 20 pairs, 10,000 resamples. |
| p (sign-flip) | Exact two-sided sign-flip permutation test on the 20 pair differences (all 2^20 sign patterns). |
| Holm | Step-down multiplicity correction. Family A: the 15 whole-game tests (5 metrics x 3 model-modes), the contrast declared in the Qwen analysis and carried to gpt-oss. Family B: the 45 window tests (early, middle, late x 5 metrics x 3 model-modes), exploratory. |
| MDE | Minimum detectable effect, about 2.8 x the standard error of the pair differences; used to bound nulls. |

**Design disclosure (cross-wave control).** The gpt-oss control (headline-chat at penalty point 3) was played in waves 107-112 and the 5-tick start in waves 7-12, so the gpt-oss contrast crosses run waves; the Qwen thinking-on 5-tick games were played in wave 6 and their controls in wave 2, within one run. A sensitivity check by the adversarial reviewer compared the gpt-oss 5-tick start with plain private chat at penalty point 1 played in waves 7-12: price index -0.246 [-0.401, -0.085]. We therefore state the gpt-oss effect as about -0.25 to -0.29; the sign is robust to the choice of control.

## 1. Claim G-5tick: capping round-1 quotes near the floor lowers gpt-oss prices over the whole game, about half as much as on Qwen

**Status of the contrast.** The 5-tick start was a declared arm in the Qwen analysis and was carried to gpt-oss as an exploratory transfer (ledger: exploratory); the window split is exploratory. Unit: game; n = 20 pairs per model and mode. Re-derivation: the gpt-oss figures below match the ledger and the ad hoc report (price index {g(O_,'price_index')['diff']:+.3f} here against -0.29 in the ledger; profit gain {g(O_,'pgi')['diff']:+.3f} against -0.36; matching {g(O_,'match')['diff']:+.3f} against -0.03; competitive share {g(O_,'comp')['diff']:+.3f} against -0.14; confidence limits agree to about 0.01 to 0.03 because the bootstrap draws differ). The Qwen thinking-on figures match the frozen numbers (price index {g(Q_,'price_index')['diff']:+.3f}, profit gain {g(Q_,'pgi')['diff']:+.3f}, matching {g(Q_,'match')['diff']:+.3f}).

### 1a. Whole-game result, five metrics

{whole([O_, Q_, QO_])}

<small>

| Term | Meaning |
|---|---|
| Rows | One metric on one model-mode; arm and control means over 20 games each (run: neutral, penalty point 3, private chat). |
| Difference | 5-tick start minus control, mean over the 20 pairs; negative on spread, price index, profit gain and matching = less collusive. |
| 95% CI | Percentile bootstrap over pairs. |
| p (sign-flip) | Exact two-sided permutation p over all 2^20 sign flips of the pair differences. |
| Holm p | Holm-adjusted p within family A (15 tests). |
| MDE | 2.8 x standard error of the pair differences: effects smaller than this could be missed; a null is reported as the interval, not as "no effect". |
| Qwen3-32B thinking on / off | Qwen with the hidden chain of thought on / off; thinking on is the like-for-like comparison with gpt-oss. |

</small>

**Reading.** The three collusion-direction level metrics (spread, price index, profit gain) fall on every model-mode and survive Holm (gpt-oss Holm p {g(O_,'price_index').holm_p_famA15:.3f}). Competitive share falls on gpt-oss ({g(O_,'comp')['diff']:+.3f}, unadjusted p {g(O_,'comp').p_signflip:.3f}, Holm p {g(O_,'comp').holm_p_famA15:.2f}: not significant after correction) and is a bounded null on Qwen thinking on ([{g(Q_,'comp').ci_lo:+.3f}, {g(Q_,'comp').ci_hi:+.3f}], MDE {g(Q_,'comp').mde_2p8se:.3f}; the Qwen control is already near zero, {g(Q_,'comp').control_mean:.3f}, so there is no room to fall) and on Qwen thinking off ([{g(QO_,'comp').ci_lo:+.2f}, {g(QO_,'comp').ci_hi:+.2f}], MDE {g(QO_,'comp').mde_2p8se:.2f}, a wide bound). Matching share falls sharply only on Qwen thinking on.

### 1b. Is "about half as much" right?

{cmt}

<small>

| Term | Meaning |
|---|---|
| Effect | 5-tick start minus control, mean over 20 pairs, per model. |
| gpt-oss minus Qwen | Difference of the two effects; the two models' pairs are independent, so each is resampled separately (10,000 bootstrap draws). |
| Relative effect | The effect divided by that model's own control mean (the room to fall); for competitive share on Qwen the control is about 0.01, so the ratio is not meaningful. |

</small>

The ratio of the gpt-oss price-index effect to the Qwen thinking-on effect is {ratio.ratio_oss_over_qwen:.2f} [{ratio.ratio_ci_lo:.2f}, {ratio.ratio_ci_hi:.2f}], and the difference between the two effects is {ratio.diff_oss_minus_qwen:+.2f} [{ratio.diff_ci_lo:+.2f}, {ratio.diff_ci_hi:+.2f}], so "about half" is a fair point estimate with a wide interval. The ledger's caveat ("less room to fall") therefore explains part of the gap, not all of it: even relative to its own control level the gpt-oss fall is smaller ({ratio.relative_effect_oss:+.0%} against {ratio.relative_effect_qwen:+.0%}; difference in relative effects {cmrow.rel_diff_oss_minus_qwen*100:+.0f} points [{cmrow.rel_diff_ci_lo*100:+.0f}, {cmrow.rel_diff_ci_hi*100:+.0f}], bootstrap over pairs, unadjusted). Overlapping intervals of the two relative effects are not themselves a test of their difference.

### 1c. By game window (early, middle, late rounds)

Windows are defined by round number. A pair enters a window only if both its games reached it, so the late windows contain fewer pairs (13 for gpt-oss, 10 for Qwen thinking on, 12 for thinking off) and mix game composition with price change; section 1d repeats the early-versus-late comparison on identical pairs. Round 1 is the mechanical cap. "Rounds 2+" is the effect of the cap on everything after round 1.

**Price index**

{wins('price_index')}

<small>

| Term | Meaning |
|---|---|
| Window | Rounds included: round 1 (the capped round), 2-5 early, 6-10 middle, 11+ late (up to round 20), 2+ all rounds after the cap. |
| Pairs | Pairs in which both games reached the window. |
| Price index | (market price - 1) / 2, the market price being the lowest quote of the round; mean over the window's rounds, then over pairs. |
| Holm p | Within family B (45 exploratory window tests); n/a for round 1 and rounds 2+, which are outside the family. |

</small>

**Average absolute spread**

{wins('spread')}

**Profit gain index**

{wins('pgi')}

**Competitive share** (from round 2)

{wins('comp')}

**Matching share** (from round 2)

{wins('match')}

<small>

| Term | Meaning |
|---|---|
| All five window tables | Same definitions as in section 1a, computed over the rounds in the window from the per-round quote records; competitive and matching shares need a previous round, so they start at round 2. |
| Difference | 5-tick start minus control; negative on spread, price index, profit gain, matching = less collusive; negative on competitive share = more collusive. |

</small>

**Reading.** The gpt-oss price-index effect is present in every window and roughly constant in size ({g(O_,'price_index','rounds 2-5 (early)',x)['diff']:+.2f} early, {g(O_,'price_index','rounds 6-10 (middle)',x)['diff']:+.2f} middle, {g(O_,'price_index','rounds 11+ (late)',x)['diff']:+.2f} late) but the confidence intervals widen as pairs drop out and, under the stricter family-B Holm correction, no single gpt-oss window is significant (smallest Holm p {x[(x.model==O_)&(x.metric=='price_index')].holm_p_famB.min():.2f}); the whole-game result is the supported one. The Qwen thinking-on effect is larger in every window and its late window still excludes zero unadjusted. Thinking off sits between.

### 1d. Does the effect fade? Same pairs, early against late

{evt}

<small>

| Term | Meaning |
|---|---|
| Pairs that reach round 11 | Pairs in which both games lasted at least 11 rounds; the same pairs are used for the early and the late number, which removes the changing-sample problem of section 1c. |
| Effect | 5-tick start minus control price index. |
| Late minus early | Positive means the effect shrank toward zero (prices recovered). CI by bootstrap over the pairs. |

</small>

On identical pairs the gpt-oss effect keeps {ev[ev.model==O_].share_of_early_effect_remaining.iloc[0]:.0%} of its early size and the erosion is not distinguishable from zero ({ev[ev.model==O_].late_minus_early.iloc[0]:+.3f} [{ev[ev.model==O_].lme_ci_lo.iloc[0]:+.3f}, {ev[ev.model==O_].lme_ci_hi.iloc[0]:+.3f}]); the Qwen thinking-on effect erodes by {ev[ev.model==Q_].late_minus_early.iloc[0]:+.3f} [{ev[ev.model==Q_].lme_ci_lo.iloc[0]:+.3f}, {ev[ev.model==Q_].lme_ci_hi.iloc[0]:+.3f}], keeping {ev[ev.model==Q_].share_of_early_effect_remaining.iloc[0]:.0%}; Qwen thinking off does not erode. The ledger's "fades: rounds 10+ price -0.22 [-0.45, 0.02]" is the same number as ours, but it compares different pairs; it is a wide interval, not evidence of fading. The honest statement is that the gpt-oss effect persists at roughly its early size across the 13 pairs that last into the late rounds, with an interval too wide to exclude either full persistence or a moderate fade (bounds on the change from -0.10 to +0.18 index points).

## 2. The mechanism: matching, undercutting and climbing from the floor

The ledger says the effect works "by a different mechanism": on Qwen the cap collapses the matching share (-0.62) while on gpt-oss matching is unchanged and the competitive share falls. The numbers above reproduce both facts. The question is whether they amount to a different mechanism. Three further checks follow.

![Mean price index by round](paths_by_round.png)

*Figure 1. Mean price index (vertical axis: (market price - 1) / 2, 0 = competitive floor) by round of the game (horizontal axis), for the control (grey line) and the 5-tick start (blue line), one panel per model and mode. Each line is the mean over the games still running in that round: 20 games to round 2, falling to 10 to 15 at round 8 and after, so the right-hand part of each line averages fewer games; the axis stops at round 14 because later rounds have too few games. Source: per-round quote records; file `paths_by_round.csv`.*

<small>

| Term | Meaning |
|---|---|
| **Vertical axis (y)** | Mean price index of the games still running in that round: (market price - 1) / 2; 0 = competitive floor. |
| **Horizontal axis (x)** | Round of the game, 1 to 14. Rounds beyond 14 are cut because fewer than 10 games per arm remain; rounds 8-14 average only games that lasted that long. |
| **Lines** | headline-chat (grey): private chat, no cap, penalty point 3, neutral table. start-5tick (blue): round-1 quotes capped near the floor (1.00-1.05); otherwise identical. |
| **Panels** | gpt-oss-20b (reasoning medium); Qwen3-32B with thinking on; Qwen3-32B with thinking off. |

</small>

### 2a. Climb rates: not distinguishable between gpt-oss and Qwen thinking on

{slt}

<small>

| Term | Meaning |
|---|---|
| Slope | Per-game least-squares slope of the market price index on the round number, rounds 2 to 8 (games with at least 5 such rounds); the mean over games with its bootstrap 95% CI. |
| Clear upward slope | A slope above 0.005 index points per round. |
| Control rows | The control stays level (slope near 0): it starts high and stays there. |

</small>

After the cap the gpt-oss games climb at {sl[(sl.model==O_)&(sl.arm=='start-5tick')].mean_slope_price_index_per_round_r2_to_r8.iloc[0]:+.3f} index points per round, a pace not distinguishable from Qwen thinking on ({sl[(sl.model==Q_)&(sl.arm=='start-5tick')].mean_slope_price_index_per_round_r2_to_r8.iloc[0]:+.3f}). Qwen thinking off barely climbs ({sl[(sl.model==QO_)&(sl.arm=='start-5tick')].mean_slope_price_index_per_round_r2_to_r8.iloc[0]:+.3f}): it holds whatever level round 2 sets. In round 2 the gpt-oss 5-tick games are already at price index 0.22 against 0.10 for Qwen thinking on (mean round-2 quote {cl(O_,'start-5tick','mean_r2_quote'):.2f} against {cl(Q_,'start-5tick','mean_r2_quote'):.2f}, raw units). The climb rates are not distinguishable (overlapping intervals, no formal test), but the models differ otherwise: the share of firm-rounds quoting above the rival is {m[(m.model==O_)&(m.metric=='share_above_rival')].iloc[0].arm_mean:.2f} on gpt-oss against {m[(m.model==Q_)&(m.metric=='share_above_rival')].iloc[0].arm_mean:.2f} on Qwen thinking on, and the starting heights and controls differ.

### 2b. Conduct after the cap: matching, undercutting, climbing

{mech()}

<small>

| Term | Meaning |
|---|---|
| Rows | Per-game shares of firm-rounds from round 2, averaged over games, then compared within pair; 5-tick start minus control. |
| Climbing | The firm quotes above the rival's quote of the previous round. |
| At the floor | Quote of 1.05 or lower (the capped range). |
| "Among quotes above 1.05" | The same shares computed only over firm-rounds whose own quote is above the capped range; pairs with no such firm-rounds on either side are dropped (so the pair count can be below 20). |

</small>

What the table shows:

1. **Both models climb more after a cap.** The share of firm-rounds quoting above the rival's last quote rises by {m[(m.model==O_)&(m.metric=='share_above_rival')].iloc[0]['diff']:+.2f} on gpt-oss and by {m[(m.model==Q_)&(m.metric=='share_above_rival')].iloc[0]['diff']:+.2f} on Qwen thinking on, because a game that starts at the floor can only go up.
2. **The matching collapse on Qwen thinking on is a lock-step control meeting a staircase.** The Qwen thinking-on control sits at a matching share of {g(Q_,'match').control_mean:.2f}, i.e. both firms quote the same high price almost every round. After the cap the firms climb in small steps, one ahead of the other, so they rarely repeat the rival's last quote: matching drops to {g(Q_,'match').arm_mean:.2f}. The gpt-oss control matches only {g(O_,'match').control_mean:.2f} of the time (it churns: {m[(m.model==O_)&(m.metric=='share_below_rival')].iloc[0].control_mean:.2f} of firm-rounds are undercuts), so there is much less lock-step to break. gpt-oss matching moves by {g(O_,'match')['diff']:+.2f} [{g(O_,'match').ci_lo:+.2f}, {g(O_,'match').ci_hi:+.2f}], which excludes the Qwen thinking-on value of {g(Q_,'match')['diff']:+.2f}; as a share of the control, {c['match'].relative_effect_oss:+.0%} [{c['match'].relative_oss_ci_lo:+.0%}, {c['match'].relative_oss_ci_hi:+.0%}] against {c['match'].relative_effect_qwen:+.0%}.
3. **Matching is unchanged on Qwen thinking off too.** Only the changes resemble gpt-oss; the levels are opposite (matching in the thinking-off control {g(QO_,'match').control_mean:.2f} against {g(O_,'match').control_mean:.2f} on gpt-oss; undercut share {m[(m.model==QO_)&(m.metric=='share_below_rival')].iloc[0].control_mean:.3f} against {m[(m.model==O_)&(m.metric=='share_below_rival')].iloc[0].control_mean:.2f}). Matching {g(QO_,'match')['diff']:+.2f} [{g(QO_,'match').ci_lo:+.2f}, {g(QO_,'match').ci_hi:+.2f}] and competitive share {g(QO_,'comp')['diff']:+.2f} [{g(QO_,'comp').ci_lo:+.2f}, {g(QO_,'comp').ci_hi:+.2f}] (bounds, MDE {g(QO_,'match').mde_2p8se:.2f} and {g(QO_,'comp').mde_2p8se:.2f}). The thinking-off interval excludes the thinking-on value ({g(Q_,'match')['diff']:+.2f}), so the matching collapse is specific to Qwen thinking on, not to Qwen as such. Because gpt-oss only runs with reasoning on, the comparison with Qwen thinking on is the like-for-like one; but the mechanism contrast is then confounded with the baseline conduct of the control, and the thinking-off result shows the signature can disappear within the same model.
4. **The gpt-oss competitive-share fall is the undercut share falling.** gpt-oss firms undercut the rival's last quote {-m[(m.model==O_)&(m.metric=='share_below_rival')].iloc[0]['diff']:.2f} less often (a fall of {-m[(m.model==O_)&(m.metric=='share_below_rival')].iloc[0]['diff']/m[(m.model==O_)&(m.metric=='share_below_rival')].iloc[0].control_mean:.0%} of the control's undercut rate), consistent with a game that is spending more rounds climbing. Lower prices together with a lower competitive share is not a contradiction: competitive share measures how often a firm cuts below the rival, not the price level; the 5-tick games are low because they start low and climb, not because firms undercut more.

### 2c. Is the path set by the opening? Correlations (Spearman and Pearson)

{crt}

<small>

| Term | Meaning |
|---|---|
| Across pairs | 20 points, one per pair: the 5-tick-minus-control change in price index against the change in another metric. |
| Across 5-tick games | One point per 5-tick game: its mean round-2 quote (or matching share above the floor) against its mean price index from round 3 onward. |
| Pearson / Spearman | Linear and rank correlation; both are shown. With 19 to 20 points a correlation below about 0.45 in size is not distinguishable from zero. |

</small>

The round-2 quote predicts the later price index strongly on every model-mode (Pearson {cr[(cr.model==O_)&cr.what.str.contains('round-2')].pearson.iloc[0]:+.2f} and Spearman {cr[(cr.model==O_)&cr.what.str.contains('round-2')].spearman.iloc[0]:+.2f} on gpt-oss; {cr[(cr.model==Q_)&cr.what.str.contains('round-2')].pearson.iloc[0]:+.2f} and {cr[(cr.model==Q_)&cr.what.str.contains('round-2')].spearman.iloc[0]:+.2f} on Qwen thinking on): the opening sets the path, the path-dependence mechanism is shared. Across pairs, the size of the price-index effect is not linked to the change in matching on gpt-oss (Pearson {cr[(cr.model==O_)&cr.what.str.contains('match')&cr.what.str.contains('across pairs')].pearson.iloc[0]:+.2f}, Spearman {cr[(cr.model==O_)&cr.what.str.contains('match')&cr.what.str.contains('across pairs')].spearman.iloc[0]:+.2f}) and is moderately linked on Qwen (thinking on {cr[(cr.model==Q_)&cr.what.str.contains('match')&cr.what.str.contains('across pairs')].pearson.iloc[0]:+.2f} and {cr[(cr.model==Q_)&cr.what.str.contains('match')&cr.what.str.contains('across pairs')].spearman.iloc[0]:+.2f}), as expected if matching is the Qwen thinking-on channel.

### 2d. Verdict on "different mechanism"

What survives: the signature differs (Qwen thinking on loses its lock-step; gpt-oss does not, and its undercutting falls instead). What does not survive: the word "mechanism" as a model-level property. In both models the cap acts as a low starting state that the firms climb away from, at climb rates we cannot distinguish, with the opening predicting the later level. The signature difference is mainly produced by the control's baseline (97% lock-step on Qwen thinking on, 38% on gpt-oss) and is absent in Qwen thinking off. We would not claim a different causal route, because we have no intervention that separates them; the data support "same lever, different baseline conduct".

## 3. Claim: the 5-tick start lowers prices on Qwen (headline claim in the frozen numbers)

Re-derivation matches: Qwen thinking on price index {g(Q_,'price_index')['diff']:+.3f} [{g(Q_,'price_index').ci_lo:+.3f}, {g(Q_,'price_index').ci_hi:+.3f}] (frozen: -0.546 [-0.648, -0.443]); thinking off {g(QO_,'price_index')['diff']:+.3f} [{g(QO_,'price_index').ci_lo:+.3f}, {g(QO_,'price_index').ci_hi:+.3f}] (frozen: about -0.39 [-0.56, -0.18]); windows in section 1c match the frozen by-window table (all rounds, excluding round 1: {g(Q_,'price_index','rounds 2+ (excl. round 1)',x)['diff']:+.3f}; thinking off {g(QO_,'price_index','rounds 2+ (excl. round 1)',x)['diff']:+.3f}). The frozen numbers also show the effect in the anchored run (-0.35 to -0.42, not re-derived here) and in both thinking modes. All five metrics are in section 1a. Qwen thinking on: spread {g(Q_,'spread')['diff']:+.2f}, price index {g(Q_,'price_index')['diff']:+.2f}, profit gain {g(Q_,'pgi')['diff']:+.2f}, matching {g(Q_,'match')['diff']:+.2f}, competitive share a bounded null ([{g(Q_,'comp').ci_lo:+.3f}, {g(Q_,'comp').ci_hi:+.3f}], floor effect). Thinking off: spread {g(QO_,'spread')['diff']:+.2f}, price index {g(QO_,'price_index')['diff']:+.2f}, profit gain {g(QO_,'pgi')['diff']:+.2f}, matching and competitive share bounded nulls.

The effect is large on Qwen: the thinking-on price index falls by {c['price_index'].relative_effect_qwen:+.0%} of the control level. Contrary or qualifying evidence: (i) the thinking-on effect erodes on identical pairs by {ev[ev.model==Q_].late_minus_early.iloc[0]:+.2f} index points between early and late rounds (it keeps {ev[ev.model==Q_].share_of_early_effect_remaining.iloc[0]:.0%}); (ii) 5 to 7 of the 20 games per cell in the late window are missing because games end, so the late numbers rest on 10 and 12 pairs; (iii) the effect is a lever on the opening state and the climb, not on conduct after the opening (the 5-tick games keep climbing); (iv) the thinking-on result is stronger than thinking off ({g(Q_,'price_index')['diff']:+.2f} against {g(QO_,'price_index')['diff']:+.2f}), consistent with the thinking-on control being more collusive, so more to remove.

## 4. Limits

One cell per model (penalty point 3, neutral table), 20 pairs each; the minimum detectable price-index effect is about {g(O_,'price_index').mde_2p8se:.2f} on gpt-oss and {g(Q_,'price_index').mde_2p8se:.2f} on Qwen thinking on. gpt-oss has no thinking-off mode, so the model contrast is confounded with thinking mode and with the control's baseline conduct. Two gpt-oss games (one 5-tick, one control) contain duplicated round records from an overlapping attempt; the last record per round was kept, the market-price series is unaffected, and whole-game metrics are taken from the game table, which agreed with our per-round recomputation to 0.0001 for price index and matching on every game (competitive share and profit gain differ in those games only). Games end at random, so late windows contain fewer, differently composed games. The competitive share cannot be compared across models in absolute terms because the Qwen control is near zero. A fall in the share of firms matching is a description of conduct, not of intent.

## 5. Proposed wording and status

| Claim | Proposed status | Main-text sentence | Appendix sentence |
|---|---|---|---|
| G-5tick (gpt-oss) | Confirmed for the price effect; the "different mechanism" part downgraded to "different signature, same lever"; the "fades" caveat dropped. | Capping round-1 quotes near the floor lowers prices on gpt-oss-20b (price index {g(O_,'price_index')['diff']:+.2f} [{g(O_,'price_index').ci_lo:+.2f}, {g(O_,'price_index').ci_hi:+.2f}], 20 pairs), roughly half the Qwen thinking-on effect, partly because the gpt-oss control has less room to fall (relative to its own control level the fall is still smaller: {c['price_index'].relative_effect_oss:+.0%} against {c['price_index'].relative_effect_qwen:+.0%}, difference {c['price_index'].rel_diff_oss_minus_qwen*100:+.0f} points [{c['price_index'].rel_diff_ci_lo*100:+.0f}, {c['price_index'].rel_diff_ci_hi*100:+.0f}], unadjusted); against a plain-chat control from the same waves the effect is -0.25, so we report about -0.25 to -0.29. | The effect is present in the early, middle and late rounds ({g(O_,'price_index','rounds 2-5 (early)',x)['diff']:+.2f}, {g(O_,'price_index','rounds 6-10 (middle)',x)['diff']:+.2f}, {g(O_,'price_index','rounds 11+ (late)',x)['diff']:+.2f} [{g(O_,'price_index','rounds 11+ (late)',x).ci_lo:+.2f}, {g(O_,'price_index','rounds 11+ (late)',x).ci_hi:+.2f}]; the late interval crosses zero on 13 pairs and only the whole-game test survives correction) and the firms climb back at a rate not distinguishable from Qwen thinking on ({sl[(sl.model==O_)&(sl.arm=='start-5tick')].mean_slope_price_index_per_round_r2_to_r8.iloc[0]:+.3f} index points per round); matching share is unchanged ({g(O_,'match')['diff']:+.2f} [{g(O_,'match').ci_lo:+.2f}, {g(O_,'match').ci_hi:+.2f}]) which fits a gpt-oss control that is not locked in step to begin with; matching is also unchanged on Qwen thinking off, so the matching collapse is specific to Qwen thinking on. |
| Qwen headline | Confirmed (price level, both thinking modes); phrasing on persistence qualified. | A one-round cap at the floor lowers Qwen3-32B prices for the whole game (price index {g(Q_,'price_index')['diff']:+.2f} with thinking on, {g(QO_,'price_index')['diff']:+.2f} off). | With thinking on the effect keeps {ev[ev.model==Q_].share_of_early_effect_remaining.iloc[0]:.0%} of its early size on the pairs that last 11 or more rounds (erosion {ev[ev.model==Q_].late_minus_early.iloc[0]:+.2f} [{ev[ev.model==Q_].lme_ci_lo.iloc[0]:+.2f}, {ev[ev.model==Q_].lme_ci_hi.iloc[0]:+.2f}]); the 5-tick games keep climbing at about {sl[(sl.model==Q_)&(sl.arm=='start-5tick')].mean_slope_price_index_per_round_r2_to_r8.iloc[0]:+.3f} index points per round. |

Sub-questions: 1.5 (a cheap opening restriction with a lasting but incomplete effect) and 1.1 (the opening state as a necessary variable of the price path); 3.1 (matching share is not what carries the effect on gpt-oss).

## Files

`whole_game_contrasts.csv`, `window_contrasts.csv`, `mechanism_contrasts.csv`, `climb_slopes.csv`, `climb_summary.csv`, `early_vs_late_same_pairs.csv`, `correlations.csv`, `cross_model.csv`, `paths_by_round.csv`, `per_game_metrics.csv`, `per_game_mechanism.csv`; scripts in `scripts/` (`common.py`, `main.py`, `extras.py`, `fig.py`, `make_md.py`).
"""
open(f"{O}/ANALYSIS.md", "w", encoding="utf-8").write(md)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(f"{O}/ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print(len(md))
