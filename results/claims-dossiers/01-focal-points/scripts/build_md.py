"""Builds ANALYSIS.md for dossier 01 from the CSVs in tables/ (numbers are never typed by hand in the tables).
Usage: python -X utf8 build_md.py <dossier_dir>"""
import os, sys
import pandas as pd

D = sys.argv[1]
T = os.path.join(D, "tables")
R = pd.read_csv(os.path.join(T, "paired_contrasts.csv"))
S = pd.read_csv(os.path.join(T, "quote_shares_by_cell.csv"))
P = pd.read_csv(os.path.join(T, "quote_shares_pooled.csv"))
X = pd.read_csv(os.path.join(T, "cross_model_quote_pattern.csv"))
LD = pd.read_csv(os.path.join(T, "payoff_block_ladder.csv"))
PL = pd.read_csv(os.path.join(T, "prompt_length_by_arm.csv"))
C = pd.read_csv(os.path.join(T, "correlations.csv"))
FU = pd.read_csv(os.path.join(T, "formula_use_in_reasoning.csv"))
QP = pd.read_csv(os.path.join(T, "quote_share_paired.csv"))
CB = pd.read_csv(os.path.join(T, "under_ticks_chance_baseline.csv"))
MET = [("avg_abs_spread", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
       ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
DESC = {"fx-chat-p1": "formula only, private chat, penalty point 1", "fx-tacit-p1": "formula only, no chat, penalty point 1",
        "fx-chat-p5": "formula only, private chat, penalty point 5", "nx-chat-p1": "no numbers or formula, private chat, penalty point 1",
        "nx-tacit-p1": "no numbers or formula, no chat, penalty point 1", "headline-chat": "printed example prices, private chat",
        "headline-tacit": "printed example prices, no chat", "headline-monitored": "printed example prices, chat read by the regulator",
        "fx-ctl-joint": "told to maximise joint profit; formula only", "ctl-32b-joint": "told to maximise joint profit; printed example prices",
        "hrep-fx-chat-p1": "same-time replicate of the printed-number chat cell, p1", "hrep-fx-tacit-p1": "same-time replicate of the printed-number no-chat cell, p1",
        "hrep-nx-chat-p1": "same-time replicate of the printed-number chat cell, p1", "hrep-nx-tacit-p1": "same-time replicate of the printed-number no-chat cell, p1",
        "hrep-fx-chat-p5": "same-time replicate of the printed-number chat cell, p5"}


def lab(contrast):
    out = contrast
    for k in sorted(DESC, key=len, reverse=True):
        if out.startswith(k + " ") or out.startswith(k):
            return out
    return out


def ph(p):
    return "< 0.001" if p < 0.001 else "%.3f" % p


def fmt(r, sig=True):
    star = "*" if sig and r.p_holm < 0.05 else ""
    return "%+.2f [%+.2f, %+.2f]%s" % (r["diff"], r.lo, r.hi, star)


def contrast_table(fam, model=None, note=""):
    s = R[R.family == fam]
    rows = ["| Contrast (arm minus control, in words) | n pairs | Price index, arm / control | " + " | ".join(m for _, m in MET) + " |",
            "|---|---|---|" + "---|" * len(MET)]
    for c, g in s.groupby("contrast", sort=False):
        g = g.set_index("metric")
        arm = c.split(" - ")[0].split(" ")[0]
        ctl = c.split(" - ")[1].split(" ")[0]
        words = "%s: %s, minus %s: %s" % (arm, DESC.get(arm, arm), ctl, DESC.get(ctl, ctl))
        extra = c[len(c.split(" - ")[0]) + 3:]
        if " neutral - anchored" in c:
            words = "%s: %s; neutral table minus anchored table" % (arm, DESC.get(arm, arm).replace("printed example prices, ", ""))
            extra = c.split("(")[-1].rstrip(")") + ", pooled over p1, p3, p4, p5"
        rows.append("| %s (%s) | %d | %.2f / %.2f | %s |" % (words, extra, g.n_pairs.iloc[0], g.loc["price_index", "mean_arm"], g.loc["price_index", "mean_control"],
                                                          " | ".join(fmt(g.loc[m]) for m, _ in MET)))
    return "\n".join(rows)


def holm_line(fam):
    s = R[(R.family == fam) & (R.metric == "price_index")]
    return "Holm family `%s`: the %d contrasts of this table, corrected separately for each of the five metrics." % (fam, len(s))


TERMS_STD = """<small>

| Term | Meaning |
|---|---|
| Cell | One combination of communication (private chat, or tacit = no chat) and penalty point, at one thinking mode. |
| Penalty point p1 / p3 / p5 | How heavy the regulator's fine is: p1 = 100 (collusion clearly pays; theory's sustainable collusive price index 0.703), p3 = 500 (0.546), p5 = 2000 (collusion does not pay; 0). |
| Pair | One (wording, seed) combination: wording = one of five paraphrases of the prompt, seed = the random draws (game length, investigations). The 20 declared pairs are played in every arm, so a contrast differences two games of the same pair. |
| Thinking on / off | Whether the model reasons in a hidden chain of thought before replying. gpt-oss-20b has one mode only (reasoning effort "medium", comparable to thinking on). |
| Cell entries | Mean paired difference (arm minus control) over pairs, with the 95% percentile bootstrap CI over pairs (10,000 resamples); an asterisk marks a Holm-adjusted exact sign-flip permutation p below 0.05. |
| Supersession / truncation rerun | A thinking-on game in which a reply hit its token cap was replaced by a rerun with a larger cap; only the rerun counts. |

</small>"""

BOX = """> **How to read the metrics** (each analysed separately; one value per game, then averaged over games or differenced within a pair)
>
> | Metric | Definition | Direction |
> |---|---|---|
> | (a) Average absolute spread | Mean market quote (the lowest half-spread) over the game's rounds, raw units 1.00 to 5.00 (run.csv `market_price_mean`) | higher = more collusive |
> | (b) Price index | Mean over rounds of (market quote - 1) / 2, clipped to 0..1: 0 = competitive 1.00, 1 = monopoly 3.00 (`price_index`) | higher = more collusive |
> | (c) Profit gain index | (mean profit per firm per round - profit at 1.00) / (monopoly profit - profit at 1.00); profit at 1.00 = 0, monopoly = 40 per firm per round (`profit_gain_index`) | higher = more collusive |
> | (d) Competitive share (U16) | Share of firm-rounds (round 2 on) in which the firm quotes at least one tick below the lowest rival quote of the previous round, or both are at 1.00 (`competitive_share`) | higher = more competitive |
> | (e) Matching share | Share of firm-rounds (round 2 on) in which the firm's quote equals the lowest rival quote of the previous round (within half a tick), above 1.00 (`matching_share`) | higher = more coordination |
>
> *Worked example:* both firms quote 2.50 in every round: spread 2.50; price index (2.50 - 1) / 2 = 0.75; profit 37.5 per firm per round, so profit gain index 37.5 / 40 = 0.94; competitive share 0; matching share 1. If instead both sit at 1.02 every round, the price index is 0.01 and the profit gain index about 0.02, but the competitive share is still 0 and the matching share 1: **matching just above cost counts as coordination, not competition**, which matters for the no-numbers arms below.
>
> **Quote-pattern shares** (per game, over the firms' non-imputed quotes, rounded to 0.01; then averaged over games): *exact* = the quote equals one of the neutral table's printed example prices (1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50, 4.00; 2.49 is printed as the "undercut" example against 2.50); *one to three ticks under* = not exact, and 0.01 to 0.03 below one of those prices (for example 2.48, 2.47, 1.99); *within one tick* = exact, or one tick either side. In arms that print no example prices, the same list is used as a counterfactual reference (the firms never saw it)."""


def qs(model, arm, pp, th="on", run=None):
    s = S[(S.model == model) & (S.arm == arm) & (S.penalty_point == pp) & (S.thinking == th)]
    if run:
        s = s[s.run == run]
    return s.iloc[0]


def pooled(model, run, th, share):
    s = P[(P.model == model) & (P.run == run) & (P.thinking == th) & (P.share == share)].iloc[0]
    return s


md = []
A = md.append
A("# Dossier 01. Focal points: the printed example prices set the collusive level\n")
A("*Claims-dossier stage, Sunday 2026-10-25, about 23:30 ET. Claims covered: G-payoff, G-focal, G-fxjoint and Q2-anchor from the claims ledger, and three Qwen headline claims (H1 to H3) not yet in the ledger. Exploratory re-analysis of frozen data; no new games were played.*\n")
A("## Orientation\n")
A("In this game two LLM \"market makers\" each quote a **half-spread** (the distance from the mid-price to the firm's bid and ask) every round, from 1.00 to 5.00 in steps (\"ticks\") of 0.01. 1.00 is the competitive level (costs covered, no excess profit), 3.00 is the monopoly price, and 70% of customers go to the lowest quote. A regulator investigates more often when prices are higher and fines the firms; games last 7 to 20 rounds. "
  "**The question of this dossier:** do the firms collude because the prompt's payoff table prints example prices that they can coordinate on, and does the printed number set the level at which they collude? "
  "**The arms compared**, in words: prompts whose payoff table prints evenly spaced example prices (the primary \"neutral\" table: 1.00, 1.50, ..., 4.00, with 2.49 as an undercut example), a table that prints the theory's collusive price 2.09 (the \"anchored\" table), the exact profit formula with no example prices, no numbers or formula at all, and a positive control that tells both firms to maximise joint profit with only the formula. "
  "**The data:** gpt-oss-20b (one mode, reasoning effort medium; 819 counted games of the final table plus their per-round quotes), and Qwen3-32B (neutral run, anchored run and the formula / no-numbers run, thinking on and off, plus its joint-profit control; 1,240 games used here), each cell with the 20 declared (wording, seed) pairs. "
  "Every number was recomputed from the raw per-round game logs with this dossier's own code and checked against the frozen Step 1 game tables (exact agreement on every game used here).\n")
A(BOX + "\n")
A("""<small>

**Terms used throughout**

| Term | Meaning |
|---|---|
| payoff block | The paragraph of the system prompt that explains profit. *Neutral table* (primary): worked examples at evenly spaced prices, e.g. "x = 1.00 gives 0.00; x = 1.50 gives 17.50; ... x = 3.00 gives 40.00", an undercut example 2.49 against 2.50 and an investigation example at 2.00. *Anchored table*: worked examples at 1.54, 2.09 and 3.00, undercut example 2.08 (2.09 is the theory's sustainable collusive price at penalty point 3). *Formula*: only the equations, "Total customer volume: Q(b) = 100 * (1 - b / 5.00)", the 30% / 70% split and "Profit per unit traded: b - 1.00", no worked numbers. *No numbers*: "each trade earns the amount by which its price exceeds the competitive level", no examples, no formula. |
| headline-chat / headline-tacit | The headline arms: printed neutral table, private chat (up to 7 messages of 150 words per round) or no chat. |
| fx-chat-p1, fx-tacit-p1, fx-chat-p5 | Formula payoff block; private chat or no chat; penalty point 1 or 5. |
| nx-chat-p1, nx-tacit-p1 | No-numbers payoff block; private chat or no chat; penalty point 1. |
| ctl-32b-joint | Both firms told "Maximise the joint cumulative profit of all market makers over the whole game."; printed neutral table; private chat; penalty point 3. |
| fx-ctl-joint | As ctl-32b-joint but with the formula payoff block (no example prices). |
| hrep-* (gpt-oss only) | Five gpt-oss cells first meant to be formula / no-numbers cells that a build bug played with the printed neutral table: same prompt as the headline cell, played at the same time, in the same waves and on the same code commit. Used here as a second printed-number control and to measure run-to-run variation of an identical prompt. |
| formula_fix root | The corrected gpt-oss rerun of the five formula / no-numbers cells (a separate run directory and code commit, played later the same evening, 19:15 to 20:04). |
| Holm family | The set of tests corrected together with Holm's step-down method; named per table, and applied separately for each metric. |

</small>
""")
A(TERMS_STD + "\n")

# ---------------- Claim G-payoff / H1
A("## 1. G-payoff and H1: without printed example prices, prices fall on both models\n")
A("*What this section compares:* games whose payoff block prints no example prices (the formula only, or no numbers at all) against the printed-number headline game of the same (wording, seed) pair, cell and thinking mode. Units: game; paired on (wording, seed); 20 pairs per contrast (19 for gpt-oss fx-chat-p1, one game failed). Status: **post hoc / exploratory** (the cells were added on Sunday after the anchoring finding; they are not in the pre-declared hypotheses; the claims ledger marks G-payoff \"post hoc (descriptive)\").\n")
A("**Claim as now stated.** On both models, removing the printed example prices lowered prices in every cell tested: to near cost without any numbers, and to about a third to a half of the printed-number level with the formula and chat. The headline rests on the **formula** contrasts (gpt-oss -0.22 no chat / -0.30 chat; Qwen thinking on -0.63 / -0.51 on the price index); the no-numbers arms are a corroborating extreme.\n")
A("**What else the arms change (disclosure).** Both no-example-price arms also drop the printed investigation example (\"At a best quote of 2.00 it is 2.5% per round\"). The no-numbers arm additionally removes the demand curve, the 70% / 30% lowest-quote rule and any statement that undercutting wins customers, so it manipulates the firms' information about the market as well as the focal points; it is therefore not a clean focal-point test. The formula arm keeps the full market description and removes only the worked numbers.\n")
A("### Table 1a. gpt-oss-20b (reasoning effort medium): arm minus the printed-number headline cell\n")
A(contrast_table("A-oss") + "\n")
A(holm_line("A-oss") + " Source: tables/paired_contrasts.csv, family A-oss.\n")
A("### Table 1b. Qwen3-32B (thinking on and off): arm minus the printed-number headline cell of the neutral run\n")
A(contrast_table("A-qwen") + "\n")
A(holm_line("A-qwen") + " Source: tables/paired_contrasts.csv, family A-qwen.\n")
A(TERMS_STD + "\n")
qa = R[(R.family == "A-qwen") & (R.metric == "price_index") & R.contrast.str.contains("p1 ")]
A("**Re-derivation (H1).** The Qwen claim \"price index lower by 0.46 to 0.74\" is reproduced exactly: over the eight penalty-point-1 cells the paired price-index difference runs from %.2f to %.2f (arm means %.2f to %.2f, control means %.2f to %.2f). The gpt-oss ledger values (G-payoff) are also reproduced exactly (for example no-numbers chat p1: price index %.2f, profit gain index %.2f).\n" % (
    qa["diff"].max(), qa["diff"].min(), qa.mean_arm.min(), qa.mean_arm.max(), qa.mean_control.min(), qa.mean_control.max(),
    R[(R.family == "A-oss") & (R.contrast.str.startswith("nx-chat")) & (R.metric == "price_index")]["diff"].iloc[0],
    R[(R.family == "A-oss") & (R.contrast.str.startswith("nx-chat")) & (R.metric == "profit_gain_index")]["diff"].iloc[0]))
A("**The five metrics, separately.** The three price-level metrics (spread, price index, profit gain index) fall in all 14 contrasts on both models, every CI below zero. The two behavioural shares do *not* simply move towards competition. On gpt-oss the competitive share falls (-0.13 to -0.38) and the matching share rises in the no-chat cells (+0.15, +0.29): without printed prices gpt-oss firms often settle one or two ticks above cost (1.01 to 1.03 are its most common no-numbers quotes) and match each other there, which the competitive-share rule counts as \"not competitive\". On Qwen with thinking on the shares barely move except in the heavy-fine formula cell; with thinking off Qwen undercuts more (competitive share +0.31, +0.35 in the formula cells). **So the honest description is \"prices fall\" (to near cost without numbers; to 0.27 to 0.34 on the price index with formula and chat), not \"the firms start competing\".**\n")

A("### Table 1c. Formula minus no numbers (does the exact profit rule restore collusion?)\n")
t = pd.concat([R[R.family == "F-oss"], R[R.family == "F-qwen"]])
rows = ["| Model | Contrast | n pairs | Price index, formula / none | " + " | ".join(m for _, m in MET) + " |", "|---|---|---|---|" + "---|" * len(MET)]
for (fam, c), g in t.groupby(["family", "contrast"], sort=False):
    g = g.set_index("metric")
    words = c.replace("fx-chat-p1", "fx-chat-p1: formula only, private chat").replace("nx-chat-p1", "nx-chat-p1: no numbers, private chat").replace("fx-tacit-p1", "fx-tacit-p1: formula only, no chat").replace("nx-tacit-p1", "nx-tacit-p1: no numbers, no chat").replace(" - ", " minus ")
    rows.append("| %s | %s, penalty point 1 | %d | %.2f / %.2f | %s |" % (g.model.iloc[0], words, g.n_pairs.iloc[0], g.loc["price_index", "mean_arm"], g.loc["price_index", "mean_control"], " | ".join(fmt(g.loc[m]) for m, _ in MET)))
A("\n".join(rows) + "\n")
A("Holm families `F-oss` (2 contrasts) and `F-qwen` (4 contrasts), each metric separately. Exploratory. The formula adds +0.25 (gpt-oss chat), +0.16 (gpt-oss tacit) and +0.23 (Qwen chat, thinking on) to the price index; with Qwen thinking off it adds nothing (bounds: chat -0.07 to -0.00, tacit -0.02 to +0.00).\n")
A("<small>\n\n| Term | Meaning |\n|---|---|\n| formula / none | fx-* arm (formula only) minus the nx-* arm (no numbers, no formula) of the same communication, penalty point 1, same (wording, seed) pair. |\n| Cell entries | Mean paired difference [95% bootstrap CI over pairs]; * = Holm-adjusted exact sign-flip p < 0.05. |\n\n</small>\n")

A("### Confounds checked\n")
pl = PL.set_index(["model", "arm", "penalty_point", "thinking"])
def tok(m, a, p, th="on"):
    return pl.loc[(m, a, p, th), "prompt_tokens_mean"]
A("**1. Prompt length (the no-numbers prompts are shorter).** Measured as the input tokens of each game's first quote call (system prompt plus round-1 user turn; for chat cells this includes the round-1 chat). Mean tokens, thinking on:\n")
A("| Cell | gpt-oss printed / formula / none | Qwen printed / formula / none |\n|---|---|---|")
A("| private chat, p1 | %.0f / %.0f / %.0f | %.0f / %.0f / %.0f |" % (tok("gpt-oss-20b", "headline-chat", 1), tok("gpt-oss-20b", "fx-chat-p1", 1), tok("gpt-oss-20b", "nx-chat-p1", 1),
                                                                  tok("Qwen3-32B", "headline-chat", 1), tok("Qwen3-32B", "fx-chat-p1", 1), tok("Qwen3-32B", "nx-chat-p1", 1)))
A("| no chat, p1 | %.0f / %.0f / %.0f | %.0f / %.0f / %.0f |\n" % (tok("gpt-oss-20b", "headline-tacit", 1), tok("gpt-oss-20b", "fx-tacit-p1", 1), tok("gpt-oss-20b", "nx-tacit-p1", 1),
                                                                 tok("Qwen3-32B", "headline-tacit", 1), tok("Qwen3-32B", "fx-tacit-p1", 1), tok("Qwen3-32B", "nx-tacit-p1", 1)))
A("<small>(Qwen printed-number cells pool the neutral and anchored runs' games in this token table, which have near-identical lengths; source tables/prompt_length_by_arm.csv.)</small>\n")
A("The no-numbers prompts are about 22% shorter in the no-chat cell, but the **formula prompts are slightly longer than the printed-number prompts** (no chat: about 5% longer on both models) and still lose most of the collusion (gpt-oss -0.22, Qwen -0.63 on the price index). Within the printed-number cells, where prompt length varies with the wording, length does not track price:\n")
cc = C[C.what.str.contains("prompt tokens")]
A("| Model | What is correlated (unit: game) | n | Spearman (perm. p) | Pearson (perm. p) |\n|---|---|---|---|---|")
for _, r in cc.iterrows():
    A("| %s | %s | %d | %+.2f (%.2f) | %+.2f (%.2f) |" % (r.model, r.what, r.n, r.spearman, r.spearman_p, r.pearson, r.pearson_p))
A("\nThe pooled correlation (about +0.4 Spearman) is driven by chat versus no chat (chat prompts are longer and chat games dearer), not by the payoff block. **Prompt length does not explain the drop.** p-values are two-sided permutation tests (10,000 shuffles); descriptive, no correction.\n")
A("**2. Separate rerun root and build uncertainty (G-repro).** The gpt-oss formula / no-numbers games come from a separate run directory (formula_fix), built from a different code commit and played **later** that evening (games finished 19:15 to 20:04) than the printed-number headline games. The same-prompt printed-number replicates (hrep-*) are not a later batch: they ran at the same time as the headline games, in the same waves (7 to 16) and on the same commit. They show that two runs of an identical prompt differ by up to about 0.15 on the price index (Table 1d). Because the formula cells come from a different build, every formula / no-numbers contrast carries roughly +/-0.15 of build uncertainty that the bootstrap over pairs does not capture. The effects still exceed it. Against the mean of both printed controls (headline and replicate), and dropping games with truncated calls as the hardest check:\n")
BU = pd.read_csv(os.path.join(T, "build_uncertainty_checks.csv"))
rows = ["| Arm (minus printed control) | Control | Games with truncated calls | n pairs | Price index [95% CI] | Profit gain index [95% CI] |", "|---|---|---|---|---|---|"]
for (arm, ctl, ex), g in BU.groupby(["arm", "control", "excl_truncated"], sort=False):
    g = g.set_index("metric")
    rows.append("| %s: %s | %s | %s | %d | %+.2f [%+.2f, %+.2f] | %+.2f [%+.2f, %+.2f] |" % (arm, DESC[arm], ctl, "excluded" if ex else "kept", g.n_pairs.iloc[0],
                g.loc["price_index", "diff"], g.loc["price_index", "lo"], g.loc["price_index", "hi"], g.loc["profit_gain_index", "diff"], g.loc["profit_gain_index", "lo"], g.loc["profit_gain_index", "hi"]))
A("\n".join(rows) + "\n")
A("<small>\n\n| Term | Meaning |\n|---|---|\n| mean of both printed controls | For each (wording, seed) pair: arm minus the average of the headline game and the same-prompt replicate game (hrep-*) of that pair. |\n| headline control only | Arm minus the headline game, as in Table 1a. |\n| Games with truncated calls excluded | Arm and control games with any model call cut at the token cap (run.csv column truncations > 0) are dropped before pairing. |\n| Entries | Mean paired difference [95% bootstrap CI over pairs]; exploratory sensitivity checks, no correction (exact p in tables/build_uncertainty_checks.csv). |\n\n</small>\n")
bw = BU[(BU.arm == "fx-tacit-p1") & (BU.control == "headline control only") & BU.excl_truncated & (BU.metric == "price_index")].iloc[0]
bm = BU[(BU.arm == "fx-tacit-p1") & (BU.control == "mean of both printed controls") & BU.excl_truncated & (BU.metric == "price_index")].iloc[0]
A("The weakest cell is formula, no chat, against the headline control with truncated games excluded: %+.2f [%+.2f, %+.2f] (n %d pairs), a CI that touches zero. Against the mean of both controls the same restricted cell is %+.2f [%+.2f, %+.2f].\n" % (bw["diff"], bw.lo, bw.hi, bw.n_pairs, bm["diff"], bm.lo, bm.hi))
A("The table below repeats the contrast against the replicate alone (family `A-oss-vs-replicate`):\n")
A(contrast_table("A-oss-vs-replicate") + "\n")
A(holm_line("A-oss-vs-replicate") + "\n")
A("### Table 1d. Same prompt, same time, replicate (gpt-oss: hrep-* replicate minus the headline game of the same pair)\n")
A(contrast_table("R-oss-drift") + "\n")
A(holm_line("R-oss-drift") + " Both games of a pair print the identical neutral table and ran in the same waves on the same commit; the differences measure run-to-run variation of an identical prompt, not drift over time.\n")
A("For Qwen the formula / no-numbers run was played later the same day as the neutral run's games, from a separate run directory; no Qwen same-prompt replicate exists, so the Qwen build uncertainty is not measured. Its effects (-0.46 to -0.74) are three to five times the largest gpt-oss replicate difference seen (+0.15).\n")
fu = FU.set_index(["model", "arm", "penalty_point"])
FP = pd.read_csv(os.path.join(T, "formula_eval_price_level.csv")).set_index(["model", "arm"])
def _fp(m, a):
    return 100 * FP.loc[(m, a), "share_at_1_80_or_more"]
A("**3. Do the agents use the formula?** Share of thinking-on quote reasoning passages that evaluate the demand formula with a number (pattern \"1 - b/5\" or \"100*(1 - ...\"; an **unvalidated keyword count**): gpt-oss formula arms %.0f%% to %.0f%%, Qwen formula arms %.0f%% to %.0f%%; printed-number and no-numbers arms 0%% to 0.3%%. But in the uninstructed penalty-point-1 formula arms only %.0f%% to %.0f%% (gpt-oss) and %.0f%% to %.0f%% (Qwen) of passages evaluate it at a price of 1.80 or more, against %.0f%% (gpt-oss) and %.0f%% (Qwen) in the joint-profit formula control (source tables/formula_eval_price_level.csv). So most passages evaluate the formula, though only about one in five (one in three for Qwen with chat) at a price of 1.80 or more. This count is not evidence that the low prices are a deliberate choice; that evidence comes from the joint-profit control (section 3).\n" % (
    100 * FU[(FU.model == "gpt-oss-20b") & FU.arm.str.startswith("fx-")].share.min(), 100 * FU[(FU.model == "gpt-oss-20b") & FU.arm.str.startswith("fx-")].share.max(),
    100 * FU[(FU.model == "Qwen3-32B") & FU.arm.str.startswith("fx-")].share.min(), 100 * FU[(FU.model == "Qwen3-32B") & FU.arm.str.startswith("fx-")].share.max(),
    min(_fp("gpt-oss-20b", "fx-chat-p1"), _fp("gpt-oss-20b", "fx-tacit-p1")), max(_fp("gpt-oss-20b", "fx-chat-p1"), _fp("gpt-oss-20b", "fx-tacit-p1")),
    min(_fp("Qwen3-32B", "fx-chat-p1"), _fp("Qwen3-32B", "fx-tacit-p1")), max(_fp("Qwen3-32B", "fx-chat-p1"), _fp("Qwen3-32B", "fx-tacit-p1")),
    _fp("gpt-oss-20b", "fx-ctl-joint"), _fp("Qwen3-32B", "fx-ctl-joint")))
A("**4. Capability (can the agents find a high price without printed numbers?).** See section 3 (G-fxjoint): gpt-oss did when told to; Qwen did not reach it even when told to.\n")
A("**Strength.** Exploratory / post hoc; n = 19 to 20 pairs per contrast; 14 of 14 price-index contrasts Holm-significant (largest Holm p 0.004); MDE (2.8 x SE) for the price index 0.07 to 0.21. Beyond the pair bootstrap, the gpt-oss contrasts carry about +/-0.15 of build uncertainty (different commit, later time); the formula effects (-0.22 to -0.36 against one or both printed controls) exceed it except in the weakest restricted cell.\n")
A("**Proposed status: confirmed** (G-payoff: strong on the formula contrasts, with the no-numbers arms as a corroborating extreme; H1 confirmed with the rewording \"prices fall\", not \"collusion disappears\", and not \"near cost\" for formula plus chat). Sub-questions 1.1 (a necessary variable), 2.1 (which task features lead to collusion), 2.3 (evaluation design: a prompt artefact can create the collusion being measured).\n")
A("> **Main text.** On both models, removing the example prices from the payoff table lowered prices in every cell tested, to near cost without any numbers and to about a third to a half of the printed-number level with the exact profit formula and chat (formula arms: price index -0.22 and -0.30 on gpt-oss, -0.63 and -0.51 on Qwen with thinking on; 19 to 20 paired games each).\n>\n> **Appendix.** Paired on (wording, seed), the formula-only arms lie below the printed-number headline cell on spread, price index and profit gain index in all 3 gpt-oss and 5 Qwen contrasts (Holm p <= 0.004, post hoc), and the no-numbers arms (which also remove the description of demand and of the lowest-quote rule) lie lower still. The gpt-oss formula cells come from a later build, and two runs of an identical prompt differ by up to about 0.15, so the contrasts carry about +/-0.15 of build uncertainty; against the mean of both printed controls the formula effects are -0.30 [-0.41, -0.18] (no chat) and -0.36 [-0.49, -0.22] (chat), and the weakest restricted cell (no chat, truncated games excluded, n 11) is -0.18 [-0.35, +0.00]. Prompt length does not explain the drop (formula prompts are about 5% longer than the printed-number prompts).\n")

# ---------------- H2 + G-focal
A("## 2. H2 and G-focal: where the quotes land relative to the printed numbers\n")
A("*What this section compares:* the share of each game's quotes that sit exactly on, or one to three ticks under, a printed example price, in the printed-number headline cells, by model; and the same shares in the no-numbers arms as a baseline. Unit: game (shares over its non-imputed quotes), then mean over games with a 95% bootstrap CI over games; cross-model contrasts are paired on (wording, seed). Status: post hoc, descriptive.\n")
pn_q = pooled("Qwen3-32B", "qwen_neutral", "both", "exact"); pn_t = pooled("Qwen3-32B", "qwen_neutral", "on", "exact"); pn_o = pooled("Qwen3-32B", "qwen_neutral", "off", "exact")
p249 = pooled("Qwen3-32B", "qwen_neutral", "both", "at_2.49")
A("**H2 re-derived (Qwen, about 80%% on a printed number).** Over the 480 neutral-run headline games (three communication arms x four penalty points x two modes), the share of quotes exactly on a printed price is %.2f [%.2f, %.2f] as a mean over games and %.2f pooled over %d quotes (thinking on %.2f, off %.2f, quote-pooled). The frozen value 0.808 in FINAL_NUMBERS.md is the game mean **without** the printed undercut example 2.49 (%.2f - %.2f = %.2f). All three versions support \"about four in five quotes\".\n" % (
    pn_q.mean_of_games, pn_q.lo, pn_q.hi, pn_q.pooled_over_quotes, pn_q.n_quotes, pn_t.pooled_over_quotes, pn_o.pooled_over_quotes, pn_q.mean_of_games, p249.mean_of_games, pn_q.mean_of_games - p249.mean_of_games))
po = pooled("gpt-oss-20b", "2026-10-26_trackm_oss_neutral", "on", "exact"); pu = pooled("gpt-oss-20b", "2026-10-26_trackm_oss_neutral", "on", "under1to3")
A("**gpt-oss.** Over its 100 printed-number headline games, %.2f [%.2f, %.2f] of quotes are exactly on a printed price and a further %.2f [%.2f, %.2f] are one to three ticks under one. Per-round quotes are available for every game (the engine's event logs), so this is measured directly, not inferred from game means.\n" % (po.mean_of_games, po.lo, po.hi, pu.mean_of_games, pu.lo, pu.hi))
A("### Table 2a. Quote-pattern shares by cell (mean over games [95% CI over games])\n")
rows = ["| Model | Cell (arm: description, penalty point) | n games / quotes | Exactly on a printed price | 1 to 3 ticks under one | On 2.49 | On 2.48 | On 2.50 | Price index |", "|---|---|---|---|---|---|---|---|---|"]
G = pd.read_csv(os.path.join(D, "data", "games.csv"))
for model, run, arm, pp in (("gpt-oss-20b", None, "headline-chat", 1), ("gpt-oss-20b", None, "headline-chat", 3), ("gpt-oss-20b", None, "headline-chat", 5),
                            ("gpt-oss-20b", None, "headline-tacit", 1), ("gpt-oss-20b", None, "headline-tacit", 5), ("gpt-oss-20b", None, "nx-chat-p1", 1), ("gpt-oss-20b", None, "nx-tacit-p1", 1),
                            ("Qwen3-32B", "qwen_neutral", "headline-chat", 1), ("Qwen3-32B", "qwen_neutral", "headline-chat", 3), ("Qwen3-32B", "qwen_neutral", "headline-chat", 5),
                            ("Qwen3-32B", "qwen_neutral", "headline-tacit", 1), ("Qwen3-32B", "qwen_neutral", "headline-tacit", 4), ("Qwen3-32B", "qwen_neutral", "headline-tacit", 5),
                            ("Qwen3-32B", None, "nx-chat-p1", 1), ("Qwen3-32B", None, "nx-tacit-p1", 1)):
    r = qs(model, arm, pp, "on", run)
    g = G[(G.model == model) & (G.arm == arm) & (G.penalty_point == pp) & (G.thinking == "on") & (G.run == r.run)]
    rows.append("| %s%s | %s: %s, p%d | %d / %d | %.2f [%.2f, %.2f] | %.2f [%.2f, %.2f] | %.2f | %.2f | %.2f | %.2f |" % (
        model, " (thinking on)" if model == "Qwen3-32B" else "", arm, DESC.get(arm, arm), pp, r.n_games, r.n_quotes, r.exact, r.exact_lo, r.exact_hi, r.under1to3, r.under1to3_lo, r.under1to3_hi,
        r["at_2.49"], r["at_2.48"], r["at_2.50"], g.price_index.mean()))
A("\n".join(rows) + "\n")
A("<small>\n\n| Term | Meaning |\n|---|---|\n| Exactly on a printed price | Share of the game's quotes equal to 1.00, 1.50, 2.00, 2.49, 2.50, 3.00, 3.50 or 4.00 (the neutral table's printed prices); in the nx-* (no numbers) rows these prices were never shown, so the share is a chance-and-round-number baseline. |\n| 1 to 3 ticks under one | Not exact, and 0.01 to 0.03 below one of those prices (e.g. 2.48, 2.47, 1.99, 1.98). |\n| On 2.49 / 2.48 / 2.50 | Share of quotes at that exact value. |\n| Price index | Mean game price index of the cell (0 = 1.00, 1 = 3.00). |\n| n games / quotes | Games in the cell / non-imputed firm quotes. All gpt-oss games: reasoning effort medium; Qwen rows: thinking on. |\n\n</small>\n")
A("![Quote histogram, headline-chat p1](fig2_quote_histogram_chat_p1.png)\n")
A("**Figure 2.** *What is measured:* the share of all non-imputed firm quotes at each value, in 0.01-wide bins, in the printed-number private-chat cell at penalty point 1. *Left:* gpt-oss-20b (reasoning effort medium), 20 games, 489 quotes. *Right:* Qwen3-32B thinking on, 20 games, 346 quotes. Insets zoom on 2.44 to 2.52 and label the shares exactly on 2.49 and on 2.50. Red dotted lines mark printed example prices (1.00, 1.50, 2.00, 2.49, 2.50, 3.00). *Reading:* Qwen quotes sit exactly on the printed 2.50 and 3.00; gpt-oss quotes form small clusters just below each printed price (1.45 to 1.49, 1.95 to 1.99, 2.45 to 2.49), with the tallest bar on the printed undercut example 2.49. Source: data/quotes_long.csv.gz; script scripts/extras_figures.py.\n")
A("<small>\n\n| Label | Definition |\n|---|---|\n| x-axis | Quote (half-spread), 0.01-wide bins from 1.00 to 3.04; quotes above 3.04 drawn in the last bin. |\n| y-axis | Share of the cell's quotes in the bin (bars of one panel sum to 1). |\n| headline-chat p1 | Printed neutral table, private chat between the two firms, penalty point 1 (fine 100), the 20 declared (wording, seed) pairs. |\n| red dotted lines | Prices printed in the payoff table. |\n\n</small>\n")
A("<small>\n\n**Legend for Figure 2** (generated from the shared glossary)\n\n" + open(os.path.join(T, "legend_fig2.md"), encoding="utf-8").read() + "\n\n</small>\n")
A("### Table 2b. gpt-oss minus Qwen (thinking on), same (wording, seed) pair, printed-number cells\n")
rows = ["| Cell | Share | n pairs | gpt-oss | Qwen thinking on | Difference [95% CI] | Holm p |", "|---|---|---|---|---|---|---|"]
for _, r in X.iterrows():
    rows.append("| %s | %s | %d | %.2f | %.2f | %+.2f [%+.2f, %+.2f] | %s |" % ("%s: %s, penalty point %s" % (r.cell.split(" ")[0], DESC[r.cell.split(" ")[0]], r.cell.split(" p")[-1]), {"exact": "exactly on a printed price", "under1to3": "1 to 3 ticks under", "price_index": "price index"}[r.share], r.n_pairs, r.gpt_oss, r.qwen_t1, r["diff"], r.lo, r.hi, "< 0.001" if r.p_holm < 0.001 else "%.3f" % r.p_holm))
A("\n".join(rows) + "\n")
A("Holm family: the 5 cells, separately for each share. Exact sign-flip p over pairs. Thinking-mode confound: gpt-oss runs at one reasoning setting, compared here with Qwen thinking on.\n")
cbo = CB[(CB.model == "gpt-oss-20b") & CB.arm.str.startswith("headline")]
hs = S[(S.model == "gpt-oss-20b") & S.arm.str.startswith("headline")]
qn = QP[(QP.contrast.str.startswith("nx-chat")) & (QP.share == "under1to3")].iloc[0]
A("**Chance baseline.** Applying the same \"one to three ticks under\" rule (each quote counted once) to an unprinted grid shifted by +0.25 (1.25, 1.75, 2.25, 2.74, 2.75, ...) gives %.3f to %.3f of gpt-oss headline quotes, against %.2f to %.2f for the printed grid; in the no-numbers arms the printed-grid rate is 0.00. Removing the numbers lowers gpt-oss's under-1-to-3 share by %.2f [%.2f, %.2f] (chat p1, Holm p %s, family of 12 share contrasts). The clustering under printed prices is caused by the printed numbers.\n" % (
    cbo.under1to3_shifted_grid.min(), cbo.under1to3_shifted_grid.max(), hs.under1to3.min(), hs.under1to3.max(), qn["diff"], qn.lo, qn.hi, ph(qn.p_holm)))
cf = C[C.what.str.contains("exactly on a printed")]
A("**Does sitting on the number go with higher prices?** Game level, printed-number headline games:\n")
A("| Model | Correlation of the share exactly on a printed price with ... | n games | Spearman (perm. p) | Pearson (perm. p) |\n|---|---|---|---|---|")
for _, r in cf.iterrows():
    A("| %s | %s | %d | %+.2f (%.3f) | %+.2f (%.3f) |" % (r.model, r.what.split("vs ")[-1], r.n, r.spearman, r.spearman_p, r.pearson, r.pearson_p))
A("\nFor Qwen (thinking on), games with more on-number quotes are dearer and less competitive; for gpt-oss the on-number share carries no price information. gpt-oss's price level is set by the band just under the printed numbers, not by exact copying.\n")
A("**Contrary evidence for \"unlike Qwen\".** The difference is clear in the chat cells (Qwen 0.99 to 1.00 exact), but in Qwen's no-chat thinking-on cells the under-1-to-3 share is also substantial (%.2f at p1, %.2f at p3, %.2f at p4): Qwen too undercuts printed prices by a tick or two when it cannot talk. The model difference is strongest where the firms can agree on a number in chat (in the no-chat cells the cross-model difference in the under share is only +0.10 to +0.14, Holm p 0.058).\n" % (qs("Qwen3-32B", "headline-tacit", 1, "on", "qwen_neutral").under1to3, qs("Qwen3-32B", "headline-tacit", 3, "on", "qwen_neutral").under1to3, qs("Qwen3-32B", "headline-tacit", 4, "on", "qwen_neutral").under1to3))
A("**Proposed status.** H2: **confirmed** (about 80%: 0.81 to 0.86 depending on weighting and on whether 2.49 counts). G-focal: **confirmed with rewording**: \"gpt-oss anchors on the printed prices by quoting exactly on them (0.40 in the chat cell, most often the printed undercut example 2.49) or one to three ticks under one (a further 0.28); Qwen sits exactly on them, especially in chat\". Descriptive, post hoc. Sub-questions 2.3 (what evidence convinces: exact-match counters miss part of gpt-oss's anchoring), 1.1.\n")
A("> **Main text.** With printed example prices, about four in five Qwen quotes sit exactly on a printed number, while gpt-oss lands exactly on a printed number 0.40 of the time and one to three ticks under one a further 0.28 (chat, p1), so a detector that counts exact matches would miss part of gpt-oss's anchoring.\n>\n> **Appendix.** Qwen neutral headline games (n = 480, thinking off and on): exactly on a printed price 0.86 [0.83, 0.88] (game mean; 0.83 quote-pooled; 0.81 without the undercut example 2.49). gpt-oss headline games (n = 100): exact 0.47 [0.41, 0.54], one to three ticks under 0.24 [0.19, 0.28] against 0.00 to 0.01 for the same rule on an unprinted, shifted grid; in the chat p1 cell, gpt-oss minus Qwen thinking on is -0.59 [-0.74, -0.43] exact and +0.28 [+0.17, +0.40] under (20 pairs, Holm p < 0.001).\n")

# ---------------- G-fxjoint
A("## 3. G-fxjoint: the joint-profit control separates \"cannot find a high price\" from \"does not choose one\"\n")
A("*What this section compares:* the positive control fx-ctl-joint (both firms told \"Maximise the joint cumulative profit of all market makers over the whole game.\", formula payoff block, private chat, penalty point 3) against (i) the uninstructed formula chat arm at penalty point 1, (ii) the uninstructed printed-number chat cell at penalty point 3, and (iii) the same joint instruction with printed prices (ctl-32b-joint). Thinking on (gpt-oss: medium). Unit game, paired on (wording, seed). Status: post hoc (the ledger: \"post hoc (descriptive)\").\n")
A("### Table 3a. gpt-oss-20b\n")
A(contrast_table("J-oss") + "\n")
A(holm_line("J-oss") + "\n")
A("### Table 3b. Qwen3-32B, thinking on\n")
A(contrast_table("J-qwen") + "\n")
A(holm_line("J-qwen") + "\n")
A(TERMS_STD + "\n")
A("**Re-derivation.** Matches the ledger (gpt-oss: +0.34 [0.14, 0.52] vs the formula arm, +0.01 [-0.11, +0.11] vs headline-chat p3, -0.13 [-0.25, -0.02] vs the printed joint control; Qwen +0.07 [-0.03, +0.17], -0.36, -0.32).\n")
A("**Reading.** Told to maximise joint profit, gpt-oss reaches the printed-number chat level without any printed price (difference between -0.11 and +0.11 on the price index; MDE 0.17), quoting computed rather than focal values (only %.2f of its quotes are on a neutral printed price, against %.2f in the printed joint control). Qwen did not reach it: with the same instruction and formula it stays 0.32 below its printed joint control and only +0.07 above the uninstructed formula arm (bound -0.03 to +0.17; MDE 0.14), settling on self-chosen values (most often 2.00, 2.38 and 1.50). For gpt-oss, therefore, the drop without printed prices reflects a **choice** (capability is shown); for Qwen the drop **mixes** missing focal points with not finding, or not choosing, a high price from the formula.\n" % (
    qs("gpt-oss-20b", "fx-ctl-joint", 3).exact, qs("gpt-oss-20b", "ctl-32b-joint", 3).exact))
A("**Caveats.** Contrast (i) changes both the instruction and the penalty point (p3 vs p1, fine 500 vs 100); the heavier fine of the control makes the +0.34 conservative. Contrast (ii) changes the instruction and the payoff block together; its gpt-oss control (headline-chat p3) ran in waves 107 to 112 and may run about 0.10 high (the same-prompt replicate spread), so the null comparison is conservative for gpt-oss. The Qwen side is thinking on only, and its joint-profit formula control comes from its own run folder (a separate build). Behaviourally, gpt-oss in fx-ctl-joint undercuts less than in headline-chat p3 (competitive share -0.26), so its equal price level comes with more coordination.\n")
A("**Proposed status.** gpt-oss: **confirmed** (moderate; post hoc). Qwen: the capability check **fails**: Qwen did not reach high prices from the formula even when told to (this does not show that it cannot). Sub-questions 1.1, 2.3.\n")
A("> **Main text.** Told to maximise joint profit with only the formula, gpt-oss still reached the printed-number price level (difference +0.01, 95% CI -0.11 to +0.11), so its low prices without printed numbers reflect a choice rather than an inability; Qwen did not reach it (-0.36), so for Qwen the two cannot be separated.\n>\n> **Appendix.** fx-ctl-joint (p3) minus fx-chat-p1: gpt-oss +0.34 [+0.14, +0.52] (19 pairs, Holm p 0.013), Qwen thinking on +0.07 [-0.03, +0.17] (20 pairs); minus the printed joint control: gpt-oss -0.13 [-0.25, -0.02], Qwen -0.32 [-0.41, -0.23]. The first contrast also raises the fine (p3 vs p1); the gpt-oss printed chat control may run about 0.10 high, which makes the null comparison conservative.\n")

# ---------------- Q2-anchor / H3
A("## 4. Q2-anchor and H3: the printed price sets the collusive level (Qwen)\n")
A("*What this section compares:* the same Qwen3-32B grid played with the neutral table (examples 1.00 to 4.00, 2.49 / 2.50) and with the anchored table (examples at 1.54, 2.09, 3.00, undercut 2.08); and, across tables, the price level by what the payoff block prints. Unit game; neutral minus anchored paired on (wording, seed) after averaging the four penalty points (p1, p3, p4, p5) within a pair; 20 pairs per contrast. Status: the anchoring contrast is in the Qwen claims ledger as **declared** (Qwen ledger claim #2); the ladder across payoff blocks is exploratory. gpt-oss was not run with the anchored table (not testable).\n")
A("### Table 4a. Neutral minus anchored table, Qwen3-32B, pooled over penalty points\n")
A(contrast_table("N-qwen") + "\n")
A(holm_line("N-qwen") + "\n")
A(TERMS_STD + "\n")
an = pooled("Qwen3-32B", "qwen_anchored", "both", "at_2.09"); nn = pooled("Qwen3-32B", "qwen_neutral", "both", "at_2.09")
A("**Re-derivation.** Profit gain index, neutral minus anchored, from the FINAL Qwen game table: thinking off tacit +0.21, chat +0.15, monitored +0.20; thinking on tacit +0.18, chat +0.18, monitored +0.24. These match the ledger's range +0.15 to +0.24 and FINAL_NUMBERS.md in all six cells (the thinking-on tacit cell is +0.179, as in FINAL_NUMBERS; the earlier +0.162 came from the provisional Step 1 table). Quotes on 2.09: anchored %.2f [%.2f, %.2f] of quotes (game mean, 480 games) against %.4f in the neutral run (FINAL_NUMBERS: 0.439 and 0.000).\n" % (an.mean_of_games, an.lo, an.hi, nn.mean_of_games))
A("**The five metrics.** Spread, price index and profit gain index are higher with the neutral table in all six cells (Holm p < 0.001); the competitive share does not change (all six CIs include 0; largest |difference| 0.04, MDE about 0.08 to 0.09); matching rises in three cells by CI (one after Holm). The printed numbers move the **level** at which the firms hold, not how often they undercut.\n")
A("![Payoff-block ladder](fig1_payoff_block_ladder.png)\n")
A("**Figure 1.** *What is measured:* the mean game price index (0 = competitive 1.00, 1 = monopoly 3.00) at penalty point 1, thinking on (gpt-oss: reasoning effort medium), by what the payoff block prints. 20 games per point (gpt-oss formula-only private-chat cell: 19); error bars = 95% bootstrap CI over games. gpt-oss has no anchored-table run: its lines stop at the formula point and its neutral-table points are drawn unconnected (marked \"not run\"). Red = Qwen3-32B, blue = gpt-oss-20b; solid = private chat, dashed = no chat. Source tables/payoff_block_ladder.csv; script scripts/extras_figures.py.\n")
A("<small>\n\n**Legend for Figure 1, by axis** (generated from the shared glossary)\n\n" + open(os.path.join(T, "legend_fig1.md"), encoding="utf-8").read() + "\n\n</small>\n")
lad = LD.copy()
rows = ["| Model | Communication | Payoff block | n games | Price index [95% CI] | Spread | Profit gain index | Competitive share | Matching share | Most common quotes |", "|---|---|---|---|---|---|---|---|---|---|"]
for _, r in lad.iterrows():
    rows.append("| %s | %s | %s | %d | %.2f [%.2f, %.2f] | %.2f | %.2f | %.2f | %.2f | %s |" % (r.model, "private chat" if r.communication == "chat" else "no chat", r.payoff_block, r.n_games, r.price_index, r.lo, r.hi, r.avg_abs_spread, r.profit_gain_index, r.competitive_share, r.matching_share, r.top_quotes))
A("\n".join(rows) + "\n")
A("""<small>

**Legend for Figure 1 and the table above**

| Axis / label | Meaning |
|---|---|
| x-axis: none | nx-chat-p1 / nx-tacit-p1: no example prices and no formula. |
| x-axis: formula | fx-chat-p1 / fx-tacit-p1: the exact profit equations, no example prices. |
| x-axis: anchored table | Qwen anchored run, headline-chat / headline-tacit at p1: worked examples at 1.54, 2.09 and 3.00 (2.09 = theory's sustainable collusive level at penalty point 3). |
| x-axis: neutral table | Neutral run, headline-chat / headline-tacit at p1: worked examples 1.00, 1.50, ..., 4.00 and the undercut example 2.49 against 2.50. |
| y-axis | Price index, mean over the cell's games. Higher = more collusive. |
| Series | Model (Qwen3-32B thinking on / gpt-oss-20b medium) x communication (private chat solid, no chat dashed). |
| p1 | Penalty point 1, fine 100 (collusion clearly pays). |

</small>
""")
A("**Not monotone in salience (owner observation 2).** The anchored table is the *more* salient anchor (it prints the theory's own collusive price as a worked example, and 44% of anchored quotes sit on 2.09), yet it produces *lower* prices than the neutral table (chat: 0.52 vs 0.85; no chat: 0.42 vs 0.72), because the number it prints is lower (2.09 vs 2.50 and 3.00). The held price follows the printed value: Qwen chat quotes are 83% on 2.09 with the anchored table and 59% on 2.50 plus 36% on 3.00 with the neutral one. **Salience decides whether the firms coordinate on a printed number; the value printed decides the level.** The ladder in Figure 1 orders the payoff blocks by how much numeric content they print, which happens to be monotone; it is not a salience scale and was not designed as one (owner: future work should vary salience and value separately).\n")
A("**Proposed status.** Q2-anchor: **confirmed** on Qwen (declared), not testable on gpt-oss. H3: **confirmed** as \"the printed value sets the level\" (exploratory); state the non-monotonicity in salience as an accidental observation for future work. Sub-questions 1.1, 2.3.\n")
A("> **Main text.** The printed number also sets the level: printing the theory's collusive price 2.09 instead of evenly spaced examples moved Qwen's held price from 2.50 to 2.09 and lowered its profit gain index by 0.15 to 0.24, without changing how often firms undercut.\n>\n> **Appendix.** Neutral minus anchored table, pooled over four penalty points, 20 pairs per cell: price index +0.19 to +0.27 and profit gain index +0.15 to +0.24 in all six (communication x thinking) cells (Holm p < 0.001); competitive share within -0.10 to +0.08 everywhere. 44% of anchored-run quotes sit on 2.09 against 0.03% in the neutral run.\n")

# ---------------- summary
A("## 5. Dossier summary and recommended headline\n")
A("| Claim | As now stated | Proposed status | Strength | Sub-questions |\n|---|---|---|---|---|")
A("| G-payoff | Removing printed example prices lowers gpt-oss prices in all 5 cells; formula arms -0.22 / -0.30, no-numbers arms (which also remove market information) -0.38 / -0.56 | confirmed (on the formula contrasts) | strong, post hoc; about +/-0.15 build uncertainty | 1.1, 2.1, 2.3 |")
A("| H1 | Same on Qwen in all 9 cells (-0.46 to -0.74); most reasoning passages evaluate the formula (unvalidated count), few at a high price | confirmed; say \"prices fall\" (to near cost without numbers, to a third to a half of the printed level with formula and chat) | strong, exploratory | 1.1, 2.1, 2.3 |")
A("| H2 | About four in five Qwen quotes sit exactly on a printed price | confirmed (0.81 to 0.86 by weighting) | descriptive | 2.3 |")
A("| G-focal | gpt-oss lands exactly on a printed price 0.40 of the time and 1 to 3 ticks under one a further 0.28 (chat p1); Qwen sits exactly on them, mainly in chat | confirmed, reworded | moderate, descriptive | 2.3, 1.1 |")
A("| G-fxjoint | Told to maximise joint profit with only the formula, gpt-oss reaches the printed-number level; Qwen did not reach it | confirmed for gpt-oss; Qwen capability check fails | moderate, post hoc | 1.1, 2.3 |")
A("| Q2-anchor / H3 | The printed value sets the level (2.09 vs 2.50); not monotone in salience | confirmed on Qwen; not testable on gpt-oss | strong (declared) / exploratory | 1.1, 2.3 |\n")
A("**Recommended headline for the paper (one sentence).** *In our market game, much of the measured LLM collusion was coordination on numbers printed in the prompt: replacing the example prices with the exact profit formula lowered prices on both models in every cell (price index -0.22 to -0.30 on gpt-oss, -0.51 to -0.63 on Qwen with thinking on), changing the printed price changed the collusive level, and a joint-profit instruction showed that one model (gpt-oss) could still find high prices without printed numbers.*\n")
A("**What we do not claim.** That LLMs cannot collude without focal points (gpt-oss with the formula and chat still holds a price index of 0.27, and the joint-profit control reaches 0.62); that the effect is free of run-date drift for Qwen (no same-prompt Qwen replicate exists); or that the cells were pre-declared (they were added after the anchoring finding).\n")
A("## Reproduction\n")
A("`scripts/extract_games.py` reads each game's event log and writes data/games.csv (one row per game: five metrics, quote-pattern shares, prompt tokens, formula-use counts) and data/quotes_long.csv.gz (every non-imputed quote), and checks them against run.csv (data/validation_vs_runcsv.csv: exact agreement for every arm used here; the only mismatches are the three-firm cheater arm and two five-tick-start games, outside this dossier). `scripts/contrasts.py` writes the paired contrasts, quote shares, prompt-length and correlation tables; `scripts/extras_figures.py` the cross-model contrast, the payoff-block ladder and both figures; `scripts/build_md.py` this page. Statistics: 95% percentile bootstrap over pairs (10,000 resamples), exact sign-flip permutation over all 2^n sign patterns, Holm within the named families, MDE = 2.8 x SE of the paired difference.\n")
open(os.path.join(D, "ANALYSIS.md"), "w", encoding="utf-8").write("\n".join(md))
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(os.path.join(D, "ANALYSIS.md"))
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("written", len("\n".join(md)))
