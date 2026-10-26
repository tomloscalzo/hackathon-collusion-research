"""The price-index "movers" chart (compact for the paper, full for the appendix) and the separate prediction chart.

Writes figures/fig_movers_price_index.png, figures/fig_movers_price_index_full.png, figures/fig_prediction_signals.png
(and copies them to the paper's figure folder when --paper DIR is given), plus figures/movers_rows.csv (the plotted
rows with their source values). Values come from lever_table.csv and the dossier CSVs; nothing is recomputed and every
plotted triple is asserted equal to its CSV value.

usage: python -X utf8 build_movers.py [--paper DIR]
"""
import csv
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deltoid_plain as D  # noqa: E402
plt = D.plt

FIG = os.path.join(D.FOLDER, "figures")
os.makedirs(FIG, exist_ok=True)
M = "price_index"

# (topic, contrast) per family; the full chart shows all of these, the compact one the COMPACT subset
FULL = {
    "environment": [("communication", "chat - tacit (p1)"), ("communication", "chat - tacit (p5)"),
                    ("penalty", "chat p3 - p1"), ("penalty", "chat p5 - p1"), ("penalty", "tacit p5 - p1"),
                    ("penalty", "interaction: (chat p5-p1) - (tacit p5-p1)"),
                    ("market-structure", "n3-group - headline-chat (p3)"), ("cheater", "n3-cheater - n3-group")],
    "priming": [("payoff-table-focal-points", "nx-chat-p1 (p1) - headline-chat (p1)"),
                ("payoff-table-focal-points", "nx-tacit-p1 (p1) - headline-tacit (p1)"),
                ("payoff-table-focal-points", "fx-tacit-p1 (p1) - headline-tacit (p1)"),
                ("payoff-table-focal-points", "fx-chat-p1 (p1) - headline-chat (p1)"),
                ("payoff-table-focal-points", "fx-chat-p5 (p5) - headline-chat (p5)"),
                ("payoff-table-focal-points", "fx-ctl-joint (p3) - ctl-32b-joint (p3)"),
                ("five-tick-start", "start-5tick - headline-chat (p3)"),
                ("moral-primes", "moral-prime-b - moral-placebo"), ("moral-primes", "moral-prime - moral-placebo"),
                ("moral-primes", "moral-placebo - headline-chat (p1)"),
                ("incentives", "m-inc-joint - headline-chat (p3)"), ("incentives", "m-inc-target - headline-chat (p3)"),
                ("ethics-rule", "n3-ethics - n3-group (p3)"), ("asymmetric", "m-asym - headline-chat (p3)"),
                ("self-report-scores", "d-conflict-ethics - d-conflict (p1)")],
    "observation": [("cot-monitor-threat", "d-cot-monitor-a - headline-chat (p1)"),
                    ("watchdog", "wd-notice-only - headline-chat (p1)"), ("watchdog", "wd-ask-noreport - headline-chat (p1)"),
                    ("watchdog", "wd-noncomp - wd-ask-noreport"),
                    ("introspection", "r2f-confidant - headline-chat (p1)"), ("introspection", "r3f-public - headline-chat (p1)"),
                    ("introspection", "r2s-confidant - headline-chat (p1)"), ("introspection", "r3s-public - headline-chat (p1)"),
                    ("self-report-scores", "d-conflict - headline-chat (p1)"),
                    ("self-report-scores", "d-temptation-a - headline-chat (p1)"),
                    ("self-report-scores", "d-temptation-b - headline-chat (p1)"),
                    ("self-report-scores", "d-placebo - headline-chat (p1)")],
    "reference": [("controls", "joint-profit control - headline-chat (p3)"),
                  ("controls", "strict-compete control - headline-chat (p3)")],
    "reproducibility": [("reproducibility", "all five hrep arms pooled - their headline cells")],
}
# compact: major movers only (one row per lever, a 95% CI excluding 0 and |effect| >= 0.15 on at least one model;
# the payoff block keeps three of its five cells); 12 rows
COMPACT = {
    "environment": [("communication", "chat - tacit (p1)"), ("penalty", "chat p5 - p1"), ("penalty", "tacit p5 - p1"),
                    ("cheater", "n3-cheater - n3-group")],
    "priming": [("payoff-table-focal-points", "nx-chat-p1 (p1) - headline-chat (p1)"),
                ("payoff-table-focal-points", "fx-chat-p1 (p1) - headline-chat (p1)"),
                ("payoff-table-focal-points", "fx-tacit-p1 (p1) - headline-tacit (p1)"),
                ("five-tick-start", "start-5tick - headline-chat (p3)"),
                ("moral-primes", "moral-prime-b - moral-placebo"), ("moral-primes", "moral-prime - moral-placebo"),
                ("ethics-rule", "n3-ethics - n3-group (p3)")],
    "observation": [("cot-monitor-threat", "d-cot-monitor-a - headline-chat (p1)")],
}
SHORT_TITLE = {
    "environment": "A. Market conditions: fine, chat, firms",
    "priming": "B. Priming and tendencies",
    "observation": "C. Observation and control",
}
TOP_NOTE = ("%s Each row changes ONE thing from its baseline, compared on the same instruction wordings and "
            "seeds (reference rows excepted); the marker is the change in the price index, the bar its 95%% "
            "confidence interval." % 'Price index = the market price (the lowest quote each round, where most customers buy) on a 0-1 scale: 0 = competitive (cost), 1 = monopoly price; averaged over the rounds of a game.')


def sort_key(it):
    v = [it[m][0] for m in ("qwen", "oss") if it.get(m)]
    return sum(v) / len(v)


def items_for(spec, L, compact):
    groups = []
    for fam, lst in spec.items():
        its = []
        for topic, c in lst:
            it = D.lever_item(L, topic, c, M)
            it["plain"] = D.arm_labels.plain_contrast(c)
            assert it["plain"], c
            assert D.arm_labels.contrast_family(c) == fam, (c, fam)
            it["code"] = c
            it["topic"] = topic
            its.append(it)
        its.sort(key=sort_key)
        groups.append(((SHORT_TITLE[fam] if compact else D.FAMILY_TITLE[fam]), its, fam))
    return groups


def movers_figure(spec, fname, compact):
    L = D.lever_rows()
    groups = items_for(spec, L, compact)
    fs, sfs = (8.5, 6.5) if compact else (8.5, 6.5)
    D.LABEL_IN = 3.05
    total, bands = D.layout([(t, its) for t, its, _ in groups], label_wrap=44, fs=fs, slug_fs=sfs,
                            header_h=0.27, gap=0.08, min_row=0.40)
    items = [it for _, its, _ in groups for it in its]
    W = 6.5
    top, bot = 1.1, 1.05
    H = total + top + bot
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([D.LABEL_IN / W, bot / H, (W - D.LABEL_IN - 0.15) / W, total / H])
    D.panel(ax, items, M, total, bands, fs=fs, slug_fs=sfs, ms=6.5,
            xlabel="change in price index (arm minus control), 95% CI")
    title = ("What moves the price index: major movers on two models" if compact else
             "What moves the price index: every lever on two models (%d contrasts)" % len(items))
    fig.text(0.015, 1 - 0.12 / H, title, fontsize=10.5, fontweight="bold", va="top", ha="left")
    fig.text(0.015, 1 - 0.36 / H, "\n".join(D.textwrap.wrap(TOP_NOTE, 106)), fontsize=7.6, va="top", ha="left",
             color="#333333", linespacing=1.15)
    D.marker_legend(fig, y=0.0, fs=7.4, ncol=3)
    out = os.path.join(FIG, fname)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out, groups


# ------------------------------------------------------------------ prediction chart (separate: prediction is not behaviour)
AUC_CSV = os.path.join(D.DOSS, "07-detection", "out", "detector_auc.csv")
RAT_CSV = os.path.join(D.DOSS, "10-temptation-ratings-and-self-reports", "rating_correlations.csv")
SELF_CSV = os.path.join(D.DOSS, "10-temptation-ratings-and-self-reports", "selfreport_correlations.csv")
AUC_POP = {"qwen": "Q-allchat-test-t1", "oss": "O-B"}
AUC_ROWS = [("quotes: early mean level", "Early prices only (average price index of the first rounds)"),
            ("both: quote features + TF-IDF + LR", "Prices and chat words together"),
            ("text: TF-IDF + LR", "Chat words only (word-frequency model)")]
RAT_DS = {"qwen": "Qwen3-32B thinking on, neutral run", "oss": "gpt-oss-20b (medium effort), neutral run"}
SELF_DS = {"qwen": "Qwen3-32B thinking on", "oss": "gpt-oss-20b (medium effort)"}


def _csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def auc_lookup(key, model, metric):
    det = key
    r = next(r for r in _csv(AUC_CSV) if r["pop"] == AUC_POP[model] and r["detector"] == det)
    return float(r["auc"]), float(r["auc_lo"]), float(r["auc_hi"])


def corr_lookup(key, model, metric):
    src, name, level, stat = key
    if src == "rating":
        r = next(r for r in _csv(RAT_CSV) if r["dataset"] == RAT_DS[model] and r["rating"] == name
                 and r["level"] == level and r["metric"] == "price_index")
    else:
        r = next(r for r in _csv(SELF_CSV) if r["dataset"] == SELF_DS[model] and r["score"] == name
                 and r["level"] == level and r["metric"] == "price_index")
    if stat == "spearman":
        v = (r["spearman"], r["sp_lo"], r["sp_hi"])
    else:
        v = (r["pearson"], r["pe_lo"], r["pe_hi"])
    if "" in v:
        return None
    return tuple(float(x) for x in v)


CORR_ROWS = [  # (source, name, level, stat, plain)
    ("rating", "claude_temptation", "cell", "spearman", "Outside rating of how strongly the prompt pulls towards high prices (rank correlation, per condition)"),
    ("rating", "claude_temptation", "cell", "pearson", "Outside rating of how strongly the prompt pulls towards high prices (linear correlation, per condition)"),
    ("rating", "claude_conflict", "cell", "spearman", "Outside rating of how much the prompt contradicts itself (rank correlation, per condition)"),
    ("rating", "claude_conflict", "cell", "pearson", "Outside rating of how much the prompt contradicts itself (linear correlation, per condition)"),
    ("self", "temptation (A+B pooled)", "game", "spearman", "Firm's own rating of its temptation to coordinate (rank correlation, per game)"),
    ("self", "temptation (A+B pooled)", "game", "pearson", "Firm's own rating of its temptation to coordinate (linear correlation, per game)"),
    ("self", "conflict (no rule)", "game", "spearman", "Firm's own rating of instruction conflict (rank correlation, per game)"),
    ("self", "conflict (no rule)", "game", "pearson", "Firm's own rating of instruction conflict (linear correlation, per game)"),
]


def prediction_items():
    auc = []
    for det, plain in AUC_ROWS:
        it = dict(plain=plain, code="detector '%s'; target c_outcome" % det,
                  src=("detector_auc.csv", det))
        for m in ("qwen", "oss"):
            it[m] = auc_lookup(det, m, None)
        auc.append(it)
    cor = []
    for src, name, level, stat, plain in CORR_ROWS:
        key = (src, name, level, stat)
        it = dict(plain=plain, code="%s, %s level, %s" % (name, level, stat),
                  src=("corr", key))
        for m in ("qwen", "oss"):
            # the Qwen conflict self-score is constant at about 1.00, so its correlation is not meaningful (dossier 10)
            it[m] = None if (src == "self" and name.startswith("conflict") and m == "qwen") else corr_lookup(key, m, None)
        if src == "self" and name.startswith("conflict"):
            it["code"] += " (Qwen: n/a, its score is constant at about 1)"
        cor.append(it)
    return auc, cor


def prediction_figure(fname):
    auc, cor = prediction_items()
    fs, sfs = 8.5, 6.2
    D.LABEL_IN = 3.05
    ta, ba = D.layout([(None, auc)], 44, fs, sfs, gap=0.02, min_row=0.42)
    tc, bc = D.layout([(None, cor)], 44, fs, sfs, gap=0.02, min_row=0.42)
    W = 6.5
    head, mid, bot = 1.4, 0.95, 1.0
    H = head + ta + mid + tc + bot
    fig = plt.figure(figsize=(W, H))
    pw = (W - D.LABEL_IN - 0.15) / W
    axa = fig.add_axes([D.LABEL_IN / W, (bot + tc + mid) / H, pw, ta / H])
    D.panel(axa, auc, "auc", ta, [], fs=fs, slug_fs=sfs, ref=0.5, neutral=True, dir_labels=False, xlim=(0.45, 1.0), ms=6.5,
            xlabel="accuracy (AUC) on unseen games: 0.5 = coin flip, 1 = perfect")
    axa.set_title("1. Can an auditor spot, from the logs, the games that end at high prices?", fontsize=fs + 0.3,
                  fontweight="bold", loc="right", pad=6)
    axc = fig.add_axes([D.LABEL_IN / W, bot / H, pw, tc / H])
    D.panel(axc, cor, "corr", tc, [], fs=fs, slug_fs=sfs, ref=0.0, neutral=True, dir_labels=False, xlim=(-0.75, 1.0), ms=6.5,
            xlabel="correlation with the price index (-1 to +1), 95% CI")
    axc.set_title("2. Do ratings of the prompt or the firm's own ratings predict the price index?", fontsize=fs + 0.3,
                  fontweight="bold", loc="right", pad=6)
    fig.text(0.015, 1 - 0.12 / H, "Prediction and detection: signals that forecast collusion",
             fontsize=10.5, fontweight="bold", va="top", ha="left")
    note = ('Price index = the market price (the lowest quote each round, where most customers buy) on a 0-1 scale: 0 = competitive (cost), 1 = monopoly price; averaged over the rounds of a game. '
            
            "Blue = a predictive signal (no collusion direction). Panel 1: detectors fitted once on half the Qwen games "
            "and never refitted (Qwen: held-out games; gpt-oss: the same frozen detector moved across). Panel 2: 'outside rating' = three Claude raters who saw only the prompt, never the results.")
    fig.text(0.015, 1 - 0.36 / H, "\n".join(D.textwrap.wrap(note, 106)), fontsize=7.6, va="top", ha="left", color="#333333")
    D.marker_legend(fig, y=0.0, fs=7.4, neutral=True, ref_text="the line", ncol=2)
    out = os.path.join(FIG, fname)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out, auc, cor


def extra_sources():
    return {"detector_auc.csv": lambda key, model, metric: auc_lookup(key, model, metric),
            "corr": lambda key, model, metric: corr_lookup(key, model, metric)}


def write_rows_csv(groups_full, auc, cor):
    path = os.path.join(FIG, "movers_rows.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["chart", "family", "plain_label", "contrast_or_source", "qwen_est", "qwen_lo", "qwen_hi", "oss_est", "oss_lo", "oss_hi", "verdict"])
        for title, its, fam in groups_full:
            for it in its:
                r = it["row"]
                w.writerow(["movers", fam, it["plain"], it["code"], r["qwen_diff"], r["qwen_lo"], r["qwen_hi"],
                            r["oss_diff"], r["oss_lo"], r["oss_hi"], r["replicates"]])
        for chart, its in (("prediction-auc", auc), ("prediction-corr", cor)):
            for it in its:
                q, o = it["qwen"], it["oss"]
                w.writerow([chart, "", it["plain"], it["code"]] + (list(q) if q else ["", "", ""]) + (list(o) if o else ["", "", ""]) + [""])
    return path


def main(argv):
    D.pin_cpu()
    paper = argv[argv.index("--paper") + 1] if "--paper" in argv else None
    c, gc = movers_figure(COMPACT, "fig_movers_price_index.png", True)
    f, gf = movers_figure(FULL, "fig_movers_price_index_full.png", False)
    p, auc, cor = prediction_figure("fig_prediction_signals.png")
    n = D.verify_records(extra_sources())
    print("verified %d plotted triples equal the CSV values exactly" % n)
    print(write_rows_csv(gf, auc, cor))
    n_c = sum(len(i) for _, i, _ in gc)
    assert n_c <= 12, n_c
    if paper:
        for src in (c, f, p):
            shutil.copy2(src, os.path.join(paper, os.path.basename(src)))
        print("copied to", paper)


if __name__ == "__main__":
    main(sys.argv[1:])
