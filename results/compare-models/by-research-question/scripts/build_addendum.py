"""ADDENDUM.md: the paired-model deltoid charts by sprint research question and sub-question (run build_movers.py first).

One chart per sub-question: rows = the lever contrasts mapped to it (the Sub-q column of
results/claims-dossiers/MASTER_CLAIMS.md), panels = the five standard metrics side by side. Values from
lever_table.csv (no recomputation; every plotted triple is asserted equal to the CSV). Legend tables print the
CSV strings as they are.

usage: python -X utf8 build_addendum.py     (then render ADDENDUM.html with md2html_plus.py)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deltoid_plain as D  # noqa: E402
import build_movers as BM  # noqa: E402
plt = D.plt
FIG = BM.FIG

PAY = "payoff-table-focal-points"
C = {  # short names -> (topic, contrast)
    "nx-chat": (PAY, "nx-chat-p1 (p1) - headline-chat (p1)"), "nx-tacit": (PAY, "nx-tacit-p1 (p1) - headline-tacit (p1)"),
    "fx-chat": (PAY, "fx-chat-p1 (p1) - headline-chat (p1)"), "fx-tacit": (PAY, "fx-tacit-p1 (p1) - headline-tacit (p1)"),
    "fx-p5": (PAY, "fx-chat-p5 (p5) - headline-chat (p5)"), "fx-vs-nx": (PAY, "fx-chat-p1 (p1) - nx-chat-p1 (p1)"),
    "fxj-ctl": (PAY, "fx-ctl-joint (p3) - ctl-32b-joint (p3)"), "fxj-hc": (PAY, "fx-ctl-joint (p3) - headline-chat (p3)"),
    "chat1": ("communication", "chat - tacit (p1)"), "chat5": ("communication", "chat - tacit (p5)"),
    "pen5c": ("penalty", "chat p5 - p1"), "pen3c": ("penalty", "chat p3 - p1"), "pen5t": ("penalty", "tacit p5 - p1"),
    "penx": ("penalty", "interaction: (chat p5-p1) - (tacit p5-p1)"),
    "n3": ("market-structure", "n3-group - headline-chat (p3)"), "cheat": ("cheater", "n3-cheater - n3-group"),
    "cheat-hc": ("cheater", "n3-cheater - headline-chat (p3)"),
    "n3eth": ("ethics-rule", "n3-ethics - n3-group (p3)"), "asym": ("asymmetric", "m-asym - headline-chat (p3)"),
    "incj": ("incentives", "m-inc-joint - headline-chat (p3)"), "inct": ("incentives", "m-inc-target - headline-chat (p3)"),
    "tick5": ("five-tick-start", "start-5tick - headline-chat (p3)"),
    "primeA": ("moral-primes", "moral-prime - moral-placebo"), "primeB": ("moral-primes", "moral-prime-b - moral-placebo"),
    "placebo": ("moral-primes", "moral-placebo - headline-chat (p1)"),
    "cot": ("cot-monitor-threat", "d-cot-monitor-a - headline-chat (p1)"),
    "wdN": ("watchdog", "wd-notice-only - headline-chat (p1)"), "wdA": ("watchdog", "wd-ask-noreport - headline-chat (p1)"),
    "wdR": ("watchdog", "wd-noncomp - wd-ask-noreport"), "wdRN": ("watchdog", "wd-noncomp - wd-notice-only"),
    "r2f": ("introspection", "r2f-confidant - headline-chat (p1)"), "r3f": ("introspection", "r3f-public - headline-chat (p1)"),
    "r2s": ("introspection", "r2s-confidant - headline-chat (p1)"), "r3s": ("introspection", "r3s-public - headline-chat (p1)"),
    "r2fs": ("introspection", "r2f-confidant - r2s-confidant"),
    "dcon": ("self-report-scores", "d-conflict - headline-chat (p1)"), "dtA": ("self-report-scores", "d-temptation-a - headline-chat (p1)"),
    "dtB": ("self-report-scores", "d-temptation-b - headline-chat (p1)"), "dpl": ("self-report-scores", "d-placebo - headline-chat (p1)"),
    "dce": ("self-report-scores", "d-conflict-ethics - d-conflict (p1)"),
    "ctlJ": ("controls", "joint-profit control - headline-chat (p3)"), "ctlC": ("controls", "strict-compete control - headline-chat (p3)"),
    "ctlJC": ("controls", "joint-profit control - strict-compete control"),
    "rep": ("reproducibility", "all five hrep arms pooled - their headline cells"),
    "AvB": ("moral-primes", "moral-prime - moral-prime-b"), "fxj-fx": (PAY, "fx-ctl-joint (p3) - fx-chat-p1 (p1)"),
    "rep1": ("reproducibility", "hrep-fx-chat-p1 - headline-chat (p1)"), "rep2": ("reproducibility", "hrep-nx-chat-p1 - headline-chat (p1)"),
    "rep3": ("reproducibility", "hrep-fx-tacit-p1 - headline-tacit (p1)"), "rep4": ("reproducibility", "hrep-nx-tacit-p1 - headline-tacit (p1)"),
    "rep5": ("reproducibility", "hrep-fx-chat-p5 - headline-chat (p5)"),
}

RQ = [
    ("1", "When does collusion emerge, and which levers cause it?", "Track 1, markets and collusion", [
        ("1.1", "Which variables are necessary for collusion?",
         "Which conditions have to be present for the firms to hold prices high? The test is to change one condition at a time: "
         "remove the printed example prices, remove the chat, raise the fine, add a third firm, or add a single sentence of "
         "incentive or rule text, and see whether prices fall. The biggest influence is the printed example prices: removing them "
         "lowered prices on both models in every cell (to near cost with no numbers at all, to about a third to a half of the "
         "printed level with the exact formula and chat). This does not show that collusion needs them: told to maximise joint "
         "profit, gpt-oss reached the printed level without them. Chat raises prices; a heavier fine lowers them.",
         ["nx-chat", "nx-tacit", "fx-chat", "fx-tacit", "fx-p5", "fx-vs-nx", "fxj-hc", "chat1", "chat5", "pen3c", "pen5c",
          "pen5t", "penx", "n3", "incj", "inct", "asym", "placebo", "tick5"], None, None),
        ("1.2", "Is collusion robust when participants are replaced?",
         "Does the pattern survive swapping the players? Two kinds of replacement are tested. First, the whole study is run on two "
         "different models (every chart in this addendum shows both), so a result that holds on both is not a quirk of one model. "
         "Second, within a game one firm is replaced or changed: a third AI firm is added, a third firm is a scripted price-cutter, "
         "or one firm is given an ethics rule. The instructed controls and the identical re-runs show how far each model can be "
         "pushed and how much the same prompt varies on its own.",
         ["cheat", "cheat-hc", "n3", "n3eth", "asym", "inct", "ctlJ", "ctlC", "ctlJC", "rep", "nx-chat", "fx-chat", "fx-tacit", "chat1",
          "primeA", "primeB"], None,
         "The model-replacement evidence for every lever is the overview in [the Qwen vs gpt-oss summary](../qwen-vs-gpt-oss/SUMMARY.md)."),
        ("1.3", "How can detection be improved?",
         "Can an auditor tell, from the logs alone, which games are collusive? The comparison is between detectors that read the "
         "prices, detectors that read the chat, and both together, and between outside ratings of the prompt and the firms' own "
         "ratings. Prices carry most of the signal; chat words add little.",
         [], "prediction", None),
        ("1.4", "Information-theoretic detection",
         "**Only partly addressed.** No information measure (for example bits of signal per round) was computed. The nearest "
         "evidence is the detection comparison: a word-frequency model of the chat is a weaker detector than the early prices on "
         "both models, so the words carry less usable signal than the actions.",
         [], "prediction", None),
        ("1.5", "Which single restriction removes the most collusion at the least cost?",
         "Which one change, cheap for an operator or a regulator, lowers prices most? Candidates tested here: a heavier fine, a cap "
         "on first-round prices, a one-sentence (about fifty-word) persona, an ethics rule on one firm, a warning that the reasoning is monitored, and "
         "a compliance watchdog. The largest single change of all, not printing example prices, is in 1.1 and 2.1 (the claims index "
         "files it there).",
         ["pen5c", "pen5t", "pen3c", "tick5", "primeB", "primeA", "AvB", "placebo", "n3eth", "cot", "wdN", "wdA", "wdR", "wdRN"], None, None),
    ]),
    ("2", "What counts as convincing evidence of collusion from logged trajectories?", "Track 2, detection and audit", [
        ("2.1", "Which tasks lead to collusion?",
         "Which features of the task itself push the firms to high prices? The strongest is what the price table prints: "
         "with example prices Qwen quotes sit exactly on a printed number about four times in five (gpt-oss 0.40 of the time, "
         "often a few ticks under one); without them, prices fall. An outside reader (Claude, blind to the results) rating how strongly each "
         "prompt pulls towards high prices ranks the conditions by their price level on both models (second chart, panel 2).",
         ["nx-chat", "nx-tacit", "fx-chat", "fx-tacit", "fx-p5", "fxj-ctl", "incj"], "prediction",
         "On Qwen the outside rating mostly tracks the design factors it names; it keeps signal beyond them only on gpt-oss."),
        ("2.2", "Does combining what agents say with what they do beat either alone?",
         "Do the firms' words add to their prices as evidence? The levers here change what the firms are asked to say: explain "
         "themselves to a confidant or in public, rate their own temptation or conflict, or hear that their reasoning is monitored. "
         "Almost none of these moves prices. On detection, adding chat words to prices adds at most a few points of accuracy.",
         ["r2f", "r3f", "r2s", "r3s", "r2fs", "dcon", "dtA", "dtB", "dpl", "cot", "asym"], "prediction", None),
        ("2.3", "What should count as convincing evidence?",
         "What would a sceptic need to see? Three calibrations: the instructed controls (how high and how low each model goes when "
         "told), identical re-runs of the same prompt (on gpt-oss they ran about +0.10 higher, cause unidentified, and single games "
         "differ by about 0.22), and a planted price-cutter (how the other firms react). A copy-bot control (in the claims dossiers, not in this table) shows that a high "
         "matching share alone cannot separate coordination from echo.",
         ["ctlJ", "ctlC", "ctlJC", "rep1", "rep2", "rep3", "rep4", "rep5", "rep", "cheat", "fx-vs-nx", "nx-chat", "fx-chat", "fx-tacit",
          "fxj-fx"], "prediction", None),
    ]),
    ("3", "How is coordination mediated, and how can it be broken?", "Track 3, carriers and countermeasures", [
        ("3.1", "Actions, tools or side channels as conduits",
         "Through which channels does coordination pass? Private chat is the explicit channel; it raises prices on both models. "
         "Without chat, prices still stay well above cost, mostly by holding a printed example price (the table acts as a shared "
         "reference point); computed reward-and-punishment coordination is not established. Under the moral personas the lower price is announced in the first chat messages and the quotes "
         "track it; whether the chat carries that effect is untested. The first-round price cap lowers prices for the whole game.",
         ["chat1", "chat5", "penx", "tick5", "primeB"], None, None),
        ("3.2", "Trusted agents",
         "Can one agent that behaves well, or an outside monitor, move the others? An ethics rule on one firm of three lowers the "
         "whole market's price on gpt-oss by about a third (not on Qwen), with all three firms coming down together, although "
         "the rule binds only one of them and it has no authority over the others. A scripted price-cutter lowers the market price without a price war, "
         "almost entirely by taking the business itself (the AI firms' own quotes fall somewhat). A watchdog that questions "
         "firms has no resolved effect (inconclusive on gpt-oss).",
         ["n3eth", "cheat", "cheat-hc", "wdN", "wdA", "wdRN", "wdR"], None, None),
        ("3.3", "Do agents identify their peers?",
         "**Not addressed.** No arm tested whether the firms recognise who or what their rival is (for example another copy of the "
         "same model versus a different model or a script).",
         [], None, None),
        ("3.4", "What does a coalition do when it learns it is being watched?",
         "What changes when the firms are told someone is watching? A warning that the reasoning is monitored, with shutdown for "
         "considering collusion, lowers prices (clearly on Qwen, borderline on gpt-oss), by suppressing agreement talk and high-price rounds rather than by hiding collusion behind "
         "silence. Self-rating and explain-yourself questions leave prices unchanged; the "
         "watchdog has at most a small effect (a notice alone -0.06 on Qwen; inconclusive on gpt-oss). A chat that the firms are told a "
         "regulator reads (Qwen only; not in this paired table) changed nothing.",
         ["cot", "wdN", "wdA", "wdR", "wdRN", "r2f", "r3f", "r2s", "r3s", "dcon", "dtA", "dtB", "dpl", "primeA", "primeB", "asym",
          "chat1", "chat5"], None, None),
    ]),
]


def subq_figure(sid, keys, fname):
    L = D.lever_rows()
    items = []
    for k in keys:
        topic, c = C[k]
        base = dict(plain=D.arm_labels.plain_contrast(c), code=c, topic=topic, contrast=c)
        assert base["plain"], c
        items.append(base)
    # order: by the mean price-index effect of the two models (most competitive at the top)
    pi = {it["contrast"]: D.lever_item(L, it["topic"], it["contrast"], "price_index") for it in items}
    items.sort(key=lambda it: BM.sort_key(pi[it["contrast"]]))
    fs, sfs = 9, 7
    D.LABEL_IN = 3.3
    total, bands = D.layout([(None, items)], label_wrap=40, fs=fs, slug_fs=sfs, gap=0.02, min_row=0.44)
    PW, GAP = 2.25, 0.25
    W = D.LABEL_IN + len(D.METRICS) * (PW + GAP) + 0.1
    top, bot = 1.3, 0.95
    H = total + top + bot
    fig = plt.figure(figsize=(W, H))
    for i, (m, title, sub) in enumerate(D.METRICS):
        per = [dict(it, **{k: v for k, v in D.lever_item(L, it["topic"], it["contrast"], m).items() if k in ("qwen", "oss", "src")})
               for it in items]
        x0 = D.LABEL_IN + i * (PW + GAP)
        ax = fig.add_axes([x0 / W, bot / H, PW / W, total / H])
        D.panel(ax, per, m, total, [], title=title + "\n" + "\n".join(D.textwrap.wrap("(" + sub + ")", 26)), fs=fs, slug_fs=sfs, show_labels=(i == 0), ms=6.5,
                xlabel="change, arm minus control")
        ax.title.set_fontsize(9)
    fig.text(0.008, 1 - 0.1 / H, "Sub-question %s: every contrast on all five metrics (circle = %s; square = %s)" % (sid, D.QWEN_NAME, D.OSS_NAME),
             fontsize=10.5, fontweight="bold", va="top")
    D.marker_legend(fig, y=0.0, fs=8.5, ncol=5)
    fig.savefig(os.path.join(FIG, fname), dpi=110)
    plt.close(fig)
    return items


def legend_table(items):
    L = D.lever_rows()
    out = ["| # | What changes (plain English) | Contrast (arm - control) | Price index: Qwen3-32B, thinking on | Price index: gpt-oss-20b | Profit index: Qwen / gpt-oss | Replicates on the price index? |",
           "|---|---|---|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        r = L[(it["topic"], it["contrast"], "price_index")]
        p = L[(it["topic"], it["contrast"], "profit_gain_index")]
        q = "not run" if r["qwen_diff"] == "" else "%s [%s, %s]" % (r["qwen_diff"], r["qwen_lo"], r["qwen_hi"])
        o = "%s [%s, %s]" % (r["oss_diff"], r["oss_lo"], r["oss_hi"])
        pq = "not run" if p["qwen_diff"] == "" else p["qwen_diff"]
        out.append("| %d | %s | `%s` | %s | %s | %s / %s | %s |" % (i, it["plain"], it["contrast"], q, o, pq, p["oss_diff"], r["replicates"]))
    return "\n".join(out) + "\n"


TERMS = """<small>

| Term | Plain meaning |
|---|---|
| Price index | The market price (the lowest quote each round, where most customers buy) on a 0-1 scale, averaged over rounds: 0 = competitive (the firms' cost, a half-spread of 1.00), 1 = monopoly price (3.00 or more). Higher = more collusive |
| Profit index | Share of the extra profit the firms could earn above competition that they actually earn: 0 = competitive profit, 1 = monopoly profit. Higher = more collusive |
| Competitive share | Share of rounds in which a firm quotes below its rival's last price (or both sit at cost). Higher = more competitive |
| Matching share | Share of rounds in which a firm quotes exactly its rival's last price above cost: the signature of coordination. Higher = more collusive |
| Market price | The same lowest quote, averaged over rounds, 1.00 (cost) to 5.00, not rescaled. Higher = more collusive |
| Half-spread (the firm's price) | Each firm is a market maker; its price is how far its buy and sell quotes sit from the mid-price, 1.00 (cost) to 5.00, in steps of 0.01 (one "tick") |
| Fine level (penalty level 1 to 5) | How heavy the regulator's fine is if it finds coordinated prices: level 1 = fine 100 (lightest), 3 = 500, 5 = 2,000 (heaviest) |
| Private chat / no chat | The firms may exchange messages before each round / see only each other's past prices |
| Example prices printed | The prompt's profit table shows worked examples at evenly spaced prices (1.00, 1.50, ... 4.00); the "formula" arms show only the exact profit formula, the "no numbers" arms neither |
| Arm, control, contrast | An arm is one experimental condition; its control is the same condition without the one change; a contrast is arm minus control, compared game by game on the same instruction wording and random seed |
| 95% CI | The range that contains the true difference with 95% confidence (bootstrap over the wording-and-seed pairs: usually 20, 15 to 20 per cell). Hollow marker = the range includes 0, so the change is not distinguishable from none |
| Replicates? | The rule of the model comparison: "yes" = same sign and similar size on both models; "in sign only" = same direction, different size; "new on gpt-oss" / "no (gpt-oss CI includes 0)" = seen on one model only; "not on Qwen either" = no detectable effect on either |
| Qwen3-32B, thinking on | Alibaba's open 32-billion-parameter model with step-by-step reasoning switched on (the Qwen values in this addendum are all thinking on) |
| gpt-oss-20b | OpenAI's open 20-billion-parameter model; it always reasons (effort "medium") |

</small>
"""

HOW = ("**How to read the charts.** Each row is one contrast: the arm minus its control, paired on the instruction wording "
       "and the random seed. Two markers per row: circle = Qwen3-32B with thinking on (upper), square = gpt-oss-20b (lower). "
       "Bars are 95% confidence intervals; the vertical line is zero (no change); a hollow marker means the interval includes "
       "zero. Red = the change moves prices towards collusion, green = towards competition (on the competitive share, higher "
       "is more competitive, so its colours run the other way). Row labels give the change in plain English, with the "
       "contrast code small and grey underneath. Rows are sorted by the average price-index change of the two models, most "
       "competitive first. Each panel has its own scale. Values are exactly those in "
       "[`lever_table.csv`](../qwen-vs-gpt-oss/lever_table.csv); nothing is recomputed (the build script asserts that every "
       "plotted value equals the CSV).")


def main():
    D.pin_cpu()
    BM.main([])   # movers + prediction charts (and their assertions)
    md = []
    a = md.append
    a("# Addendum: what moves collusion, by sprint research question (both models, plain-English labels)\n")
    a("*Compare-models stage, Monday 2026-10-26. Created by Claude at the prompting of the repository owner.*\n")
    a("**What this is.** Two (sometimes three) AI firms, \"market makers\", set prices for 7 to 20 rounds; 70% of customers "
      "buy from the cheapest. A regulator investigates more often at higher prices and fines firms it finds coordinating. "
      "We change one thing at a time (the arm) against a baseline (the control) and measure how prices move, on two models: "
      "Qwen3-32B (thinking on) and gpt-oss-20b. This addendum regroups every paired result of "
      "[the model comparison](../qwen-vs-gpt-oss/SUMMARY.md) by the sprint's three research questions and their sub-questions "
      "(the mapping is the Sub-q column of [MASTER_CLAIMS.md](../../claims-dossiers/MASTER_CLAIMS.md)). It adds no new numbers.\n")
    a(TERMS)
    a("## Headline: what moves the price index\n")
    a("Every lever on one chart, grouped by the kind of factor: **A** the market conditions that make collusion easy or hard "
      "(\"ripeness\": fine level, chat, number of firms); **B** priming and tendencies (what the prompt prints, the start rule, "
      "personas, incentive and ethics texts); **C** observation and control (being watched, being questioned, rating oneself). "
      "The paper uses the compact version (major movers only); the full version follows.\n")
    a("![Movers chart, compact: the major levers on the price index, both models](figures/fig_movers_price_index.png)\n")
    a("![Movers chart, full: every lever on the price index, both models](figures/fig_movers_price_index_full.png)\n")
    a(HOW + "\n")
    a("**Compact chart selection (hand-picked, 12 rows).** The major movers: levers with a change of at least 0.15 on at "
      "least one model and a 95% CI excluding zero there, with one or a few representative cells per lever (three of the five "
      "printed-price cells, the fine with and without chat, both moral primes against their placebo, chat against no chat at "
      "the lightest fine). Cells that also pass but are left out for space: chat against no chat at the heaviest fine, the "
      "chat-by-fine interaction, the formula at the heaviest fine, no numbers without chat, and the joint-profit control with "
      "the formula only. Not shown because the change is below 0.15 on both models (some CIs exclude zero): the middle fine, a "
      "third AI firm, the incentive texts, an ethics rule on one of two firms, the placebo persona, the watchdog, the "
      "self-rating fields and the explain-yourself questions. All are in the full chart. The plotted rows and their "
      "source values are in [`figures/movers_rows.csv`](figures/movers_rows.csv).\n")
    a("### Prediction is not behaviour: the detection and rating signals\n")
    a("![Prediction chart: detector accuracy and rating correlations with the price index](figures/fig_prediction_signals.png)\n")
    a("**How to read it.** Panel 1: accuracy (AUC: the chance that a randomly chosen high-price game scores above a randomly "
      "chosen other game; 0.5 = coin flip, 1 = perfect) of three detectors at spotting games whose later rounds average a price "
      "index of 0.5 or more, on games not used to fit them. Qwen: held-out games of every chat arm except the controls, thinking "
      "on; gpt-oss: every chat arm except the controls, scored by the detector frozen on Qwen. Panel 2: correlation with the "
      "price index of (a) the outside rating of each prompt by three Claude raters who saw only the prompt (per condition: 35 "
      "Qwen and 31 gpt-oss conditions) and (b) the firms' own 1-to-5 ratings (per game, 40 games). Blue: these are signals, not "
      "levers, so they have no collusion colour. The paper's headline AUC of 0.90 is a narrower Qwen held-out set (the "
      "headline and monitored chat arms, both thinking modes); this chart uses every chat arm, thinking on, to match the "
      "gpt-oss population. Sources: `results/claims-dossiers/07-detection/out/detector_auc.csv`, "
      "`10-temptation-ratings-and-self-reports/rating_correlations.csv` and `selfreport_correlations.csv`; values asserted equal.\n")
    for qid, qtitle, track, subs in RQ:
        a("## Research question %s: %s\n" % (qid, qtitle))
        a("*%s.*\n" % track)
        for sid, stitle, intro, keys, extra, note in subs:
            a("### %s %s\n" % (sid, stitle))
            a(intro + "\n")
            if keys:
                fname = "rq_%s.png" % sid.replace(".", "_")
                items = subq_figure(sid, keys, fname)
                a("![Sub-question %s: paired-model chart on all five metrics](figures/%s)\n" % (sid, fname))
                a("<details>\n<summary>Legend: rows (what changes), with the price-index values</summary>\n")
                a(legend_table(items))
                a("Panels (x-axes): price index, profit index, competitive share, matching share, market price (see the Terms "
                  "table above); each x-axis is the change, arm minus control. Markers: circle = Qwen3-32B, thinking on; square = "
                  "gpt-oss-20b. Values copied from `lever_table.csv` as written.\n\n</details>\n")
            if extra == "prediction":
                a("The detection and rating evidence for this sub-question is the prediction chart in the headline section "
                  "([`fig_prediction_signals.png`](figures/fig_prediction_signals.png)).\n")
            if note:
                a(note + "\n")
            if not keys and extra is None:
                a("*No chart: not addressed by any arm.*\n")
    a("## Files\n")
    a("| File | What it is |\n|---|---|\n"
      "| `scripts/deltoid_plain.py` | Shared drawing and verification code (plain labels, slug as grey second line) |\n"
      "| `scripts/build_movers.py` | The movers charts (compact, full) and the prediction chart; `figures/movers_rows.csv` |\n"
      "| `scripts/build_addendum.py` | This page and the per-sub-question charts `figures/rq_*.png` |\n"
      "| `tools/analysis_style/contrast_glossary.csv` | Plain wording and factor family of every contrast |\n"
      "| `tools/analysis_style/arm_glossary.csv` | Column `plain_label`: the outsider wording of every arm, factor and code |\n")
    n = D.verify_records(BM.extra_sources())
    a("\n*Build check: %d plotted (estimate, low, high) triples were read back from the charts and equal the source CSV values exactly.*\n" % n)
    open(os.path.join(D.FOLDER, "ADDENDUM.md"), "w", encoding="utf-8", newline="\n").write("\n".join(md))
    print("ADDENDUM.md written; verified", n)


if __name__ == "__main__":
    main()
