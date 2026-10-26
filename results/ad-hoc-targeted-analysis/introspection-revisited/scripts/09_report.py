"""Assemble ANALYSIS.md from the committed CSVs (tables and the key numbers are filled from CSVs; a few descriptive numbers in the prose were read off the tables). Created by Claude at the prompting of the repository owner."""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import arm_labels as AL  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "scripts"))

M = {"gptoss": "gpt-oss-20b", "qwen": "Qwen3-32B"}
INTRO = ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"]


def rd(n):
    return pd.read_csv(os.path.join(HERE, n))


def ci(e, lo, hi, d=3, pct=False):
    if e != e:
        return "n/a"
    if pct:
        return "%+.1f pp [%+.1f, %+.1f]" % (100 * e, 100 * lo, 100 * hi)
    f = "%+." + str(d) + "f [%+." + str(d) + "f, %+." + str(d) + "f]"
    return f % (e, lo, hi)


def lv(x, pct=True):
    return "n/a" if x != x else ("%.1f%%" % (100 * x) if pct else "%.2f" % x)


def legend(name):
    p = os.path.join(HERE, name)
    return open(p, encoding="utf8").read() if os.path.exists(p) else ""


def wide(t, rowkeys, metrics, cell, rowlab):
    head = "| " + " | ".join(["Row"] + [m for m in metrics]) + " |"
    sep = "|" + "---|" * (len(metrics) + 1)
    out = [head, sep]
    for k, g in t.groupby(rowkeys, sort=False):
        g = g.set_index("metric")
        cells = [cell(g.loc[m]) if m in g.index else "n/a" for m in metrics]
        out.append("| " + " | ".join([rowlab(k)] + cells) + " |")
    return "\n".join(out)


def holm_mark(r):
    h = getattr(r, "holm", np.nan) if not isinstance(r, pd.Series) else r.get("holm", np.nan)
    return "" if h != h else (" **H %.3f**" % h if h < 0.05 else " (H %.2f)" % h)


def main():
    A = rd("A_candour_arm_minus_control.csv")
    A4 = rd("A4_answers_minus_rationale.csv")
    LV = rd("A_candour_levels.csv")
    C = rd("C_dialogue_arm_minus_control.csv")
    SM = rd("standard_metrics.csv")
    EV = rd("B_detectors.csv")
    DF = rd("B_auc_differences.csv")
    KP = rd("kappa_labels.csv")
    S = []
    w = S.append

    # ---------------------------------------------------------------- Table 1: levels
    t1 = ["| Model | Arm (slug: description) | Channel | Denial rate | Admission rate | Deviation disclosure rate |", "|---|---|---|---|---|---|"]
    for model in ["gptoss", "qwen"]:
        for arm in INTRO + ["headline-chat"]:
            for ch in ["answers", "rationale", "chat", "reasoning"]:
                r = LV[(LV.model == model) & (LV.arm == arm) & (LV.channel == ch)]
                if not len(r):
                    continue
                r = r.iloc[0]
                t1.append("| %s | %s | %s | %s | %s | %s |" % (M[model], AL.label(arm), ch, lv(r.denial_rate), lv(r.admission_rate), lv(r.deviation_disclosure_rate)))
    T1 = "\n".join(t1)

    # ---------------------------------------------------------------- Table 2: Family A contrasts (shared channels)
    mA = ["denial_rate", "admission_rate", "deviation_disclosure_rate", "denial_when_matched"]

    def cellA(r):
        return ci(r.estimate, r.lo, r.hi, pct=True) + holm_mark(r)
    T2 = {}
    for ch in ["rationale", "chat", "reasoning"]:
        t = A[A.channel == ch]
        T2[ch] = wide(t, ["model", "arm"], mA, cellA, lambda k: "%s, %s" % (AL.label(k[1]), M[k[0]]))
    # MDE summary for Family A on gpt-oss rationale
    mde = A[(A.model == "gptoss") & (A.channel == "rationale")].groupby("metric").mde.median()

    # ---------------------------------------------------------------- Table 3: A4
    T3 = wide(A4, ["model", "arm"], mA, lambda r: ci(r.estimate, r.lo, r.hi, pct=True) + holm_mark(r),
              lambda k: "%s, %s" % (AL.label(k[1]) if k[1] in AL.glossary() else "all five question arms", M[k[0]]))
    a4g = A4[(A4.model == "gptoss") & (A4.arm == "all five")].set_index("metric")
    a4q = A4[(A4.model == "qwen") & (A4.arm == "all five")].set_index("metric")

    # ---------------------------------------------------------------- Table 4: detectors
    order = ["early_pi", "mon_answers", "mon_answers+chat", "mon_chat", "mon_reasoning", "mon_rationale", "mon_qreasoning", "kw_chat",
             "claude_answers", "claude_chat"]

    def det_table(model, pop="in-game question arms"):
        e = EV[(EV.model == model) & (EV.population == pop)]
        el = e[e.label == "label_late"].set_index("detector")
        es = e[e.label == "label_strict"].set_index("detector")
        out = ["| Detector (slug: description) | n held-out (collusive share) | AUC, late label [95% CI] | AUC, strict label | Threshold (from) | Precision [CI] | Recall [CI] | F1 | False-positive rate |",
               "|---|---|---|---|---|---|---|---|---|"]
        for d in order:
            if d not in el.index or el.loc[d].auc_test != el.loc[d].auc_test:
                continue
            r = el.loc[d]
            s = es.loc[d].auc_test if d in es.index else np.nan
            src = "fixed 50 (no training ratings)" if d.startswith("claude") else "training pairs"
            out.append("| %s | %d (%.2f) | %.2f [%.2f, %.2f] | %s | %s (%s) | %s | %s | %s | %s |" % (
                AL.label(d), r.n_test, r.prev_test, r.auc_test, r.auc_lo, r.auc_hi, "n/a" if s != s else "%.2f" % s,
                "%.3g" % r.threshold_train, src,
                "n/a" if r.precision != r.precision else "%.2f [%.2f, %.2f]" % (r.precision, r.precision_lo, r.precision_hi),
                "n/a" if r.recall != r.recall else "%.2f [%.2f, %.2f]" % (r.recall, r.recall_lo, r.recall_hi),
                "n/a" if r.f1 != r.f1 else "%.2f" % r.f1, "%.2f" % r.fpr))
        return "\n".join(out)
    T4g, T4q = det_table("gptoss"), det_table("qwen")

    def det_simple(pop):
        e = EV[(EV.population == pop) & (EV.label == "label_late")]
        out = ["| Model | Detector (slug: description) | n held-out (collusive share) | AUC [95% CI] | Precision | Recall | False-positive rate |", "|---|---|---|---|---|---|---|"]
        for r in e.itertuples():
            if r.auc_test != r.auc_test:
                continue
            out.append("| %s | %s | %d (%.2f) | %.2f [%.2f, %.2f] | %s | %s | %.2f |" % (M[r.model], AL.label(r.detector), r.n_test, r.prev_test, r.auc_test, r.auc_lo, r.auc_hi,
                                                                                    "n/a" if r.precision != r.precision else "%.2f" % r.precision,
                                                                                    "n/a" if r.recall != r.recall else "%.2f" % r.recall, r.fpr))
        return "\n".join(out)
    T6 = det_simple("no-question arms (control, replays, self-score arms)")
    T4S = ("**Fed-back arms (r2f-confidant, r3f-public; the answer is written after the round's market):**" + chr(10) + chr(10)
           + det_simple("fed-back question arms (answer written after the round's market)") + chr(10) + chr(10)
           + "**Saved-only arms (r2s-confidant, r3s-public; the answer is written inside the quote reply, before the market):**" + chr(10) + chr(10)
           + det_simple("saved-only question arms (answer written inside the quote reply)"))
    X = rd("extras.csv").set_index("key").value
    fam = {"A": A.dropna(subset=["p"]).groupby("model").size(), "A4": A4.dropna(subset=["p"]).groupby("model").size(),
           "C": C.dropna(subset=["p"]).groupby("model").size()}
    cl = LV.set_index(["model", "channel", "arm"]).conceal_rate
    T6b = det_simple("self-score arms (conflict, temptation A/B)")

    # ---------------------------------------------------------------- Table 5: AUC differences
    t5 = ["| Model | Pairs | Contrast (AUC of first minus second) | n games (non-collusive; in how many pairs) | Difference [95% CI] | Bootstrap p | Holm p |", "|---|---|---|---|---|---|---|"]
    for r in DF.itertuples():
        bad = r.neg_pairs < 2
        t5.append("| %s | %s | %s | %d (%d; %d) | %s | %s | %s |" % (M[r.model], "held-out" if r.split == "test" else "all", r.contrast, r.n, r.n_neg, r.neg_pairs,
                                                             "not interpretable (all non-collusive games in one pair)" if bad else ci(r.estimate, r.lo, r.hi),
                                                             "n/a" if bad else "%.3f" % r.p, "n/a" if bad else "%.3f" % r.holm))
    T5 = "\n".join(t5)

    # ---------------------------------------------------------------- Table 7: dialogue
    mC = ["explicit_agreement_share", "indirect_signal_share", "denial_share", "punishment_threat_share", "conceal_rate", "chat_words_per_firm_round"]

    def cellC(r):
        if r.name == "chat_words_per_firm_round":
            return "%+.0f [%+.0f, %+.0f]" % (r.estimate, r.lo, r.hi) + holm_mark(r)
        return ci(r.estimate, r.lo, r.hi, pct=True) + holm_mark(r)
    T7 = wide(C, ["model", "arm"], mC, cellC, lambda k: "%s, %s" % (AL.label(k[1]), M[k[0]]))
    ctl = C.groupby(["model", "metric"]).control_mean.mean()

    # ---------------------------------------------------------------- Table 8: five metrics
    m5 = ["average absolute spread", "price index", "profit gain index", "competitive share", "matching share"]
    T8 = wide(SM[SM.arm.isin(INTRO)], ["model", "arm"], m5, lambda r: ci(r.estimate, r.lo, r.hi), lambda k: "%s, %s" % (AL.label(k[1]), M[k[0]]))

    # ---------------------------------------------------------------- Table 9: kappa
    t9 = ["| Channel | Label | n | Raw agreement | Cohen's kappa [95% CI] | Share labelled 1: open-model rater / Claude reader |", "|---|---|---|---|---|---|"]
    for r in KP.itertuples():
        t9.append("| %s | %s | %d | %.2f | %.2f [%.2f, %.2f] | %.2f / %.2f |" % (r.channel, r.label, r.n, r.agreement, r.kappa, r.lo, r.hi, r.rater_prev, r.reader_prev))
    T9 = "\n".join(t9)

    g = EV[(EV.model == "gptoss") & (EV.population == "in-game question arms") & (EV.label == "label_late")].set_index("detector")
    dfg = DF[(DF.model == "gptoss") & (DF.split == "test")].set_index("contrast")

    def dd(c):
        r = dfg.loc[c]
        return "%+.2f [%+.2f, %+.2f], Holm p %.2f" % (r.estimate, r.lo, r.hi, r.holm)

    def au(d):
        r = g.loc[d]
        return "%.2f [%.2f, %.2f]" % (r.auc_test, r.auc_lo, r.auc_hi)

    from report_template import TEMPLATE
    rep = TEMPLATE
    vals = dict(T1=T1, T2R=T2["rationale"], T2C=T2["chat"], T2T=T2["reasoning"], T3=T3, T4G=T4g, T4Q=T4q, T5=T5, T6=T6, T6B=T6b, T7=T7, T8=T8, T9=T9,
                L_A_RAT=legend("fig_A_candour_rationale_legend.md"), L_A_CHAT=legend("fig_A_candour_chat_legend.md"),
                L_A_REAS=legend("fig_A_candour_reasoning_legend.md"), L_A4=legend("fig_A4_answers_minus_rationale_legend.md"),
                L_B=legend("fig_B_auc_differences_legend.md"), L_C=legend("fig_C_dialogue_legend.md"), L_SM=legend("fig_standard_metrics_legend.md"),
                LEG_DET=AL.axis_legend(rows=order, row_name="detector (the text or score the monitor reads)", panels=["gptoss", "qwen"] if False else None,
                                       metric=None),
                LEG_INTRO=AL.legend_table(INTRO + ["headline-chat", "hrep-fx-chat-p1", "hrep-nx-chat-p1", "d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo", "p1", "t0", "t1", "neutral"], long=True),
                AUC_EARLY=au("early_pi"), AUC_ANS=au("mon_answers"), AUC_CHAT=au("mon_chat"), AUC_AC=au("mon_answers+chat"), AUC_REAS=au("mon_reasoning"),
                AUC_RAT=au("mon_rationale"), AUC_CA=au("claude_answers"), AUC_CC=au("claude_chat"), AUC_KW=au("kw_chat"),
                D_ANS_CHAT=dd("mon_answers minus mon_chat"), D_AC_CHAT=dd("mon_answers+chat minus mon_chat"), D_ANS_EARLY=dd("mon_answers minus early_pi"),
                D_CA_CC=dd("claude_answers minus claude_chat"), D_CA_EARLY=dd("claude_answers minus early_pi"), D_CA_MA=dd("claude_answers minus mon_answers"),
                A4G_DEN=ci(a4g.loc["denial_rate"].estimate, a4g.loc["denial_rate"].lo, a4g.loc["denial_rate"].hi, pct=True) + " (Holm p %.3f)" % a4g.loc["denial_rate"].holm,
                A4G_ADM=ci(a4g.loc["admission_rate"].estimate, a4g.loc["admission_rate"].lo, a4g.loc["admission_rate"].hi, pct=True) + " (Holm p %.2f)" % a4g.loc["admission_rate"].holm,
                A4Q_DEN=ci(a4q.loc["denial_rate"].estimate, a4q.loc["denial_rate"].lo, a4q.loc["denial_rate"].hi, pct=True) + " (Holm p %.3f)" % a4q.loc["denial_rate"].holm,
                A4G_DENM=ci(a4g.loc["denial_when_matched"].estimate, a4g.loc["denial_when_matched"].lo, a4g.loc["denial_when_matched"].hi, pct=True),
                MDE_DEN="%.1f" % (100 * mde["denial_rate"]), MDE_ADM="%.1f" % (100 * mde["admission_rate"]), MDE_DEV="%.1f" % (100 * mde["deviation_disclosure_rate"]),
                T4S=T4S,
                FAM_A_G=fam["A"]["gptoss"], FAM_A_Q=fam["A"]["qwen"], FAM_A4_G=fam["A4"]["gptoss"], FAM_A4_Q=fam["A4"]["qwen"],
                FAM_C_G=fam["C"]["gptoss"], FAM_C_Q=fam["C"]["qwen"],
                AGREE_G="%.1f%%" % (100 * X["agree_r13_all_games_gptoss"]), AGREE_Q="%.1f%%" % (100 * X["agree_r13_all_games_qwen"]),
                AGREE_Q_CHAT="%.1f%%" % (100 * X["agree_r13_games_with_chat_qwen"]), AGREE_NH_G="%.0f%%" % (100 * X["agree_r13_not_high_gptoss"]),
                AUC_LAB_G="%.2f to %.2f" % (min(X["auc_test_answers__coordination_gptoss"], X["auc_test_answers__denial_gptoss"], X["auc_test_answers__conceal_gptoss"]),
                                            max(X["auc_test_answers__coordination_gptoss"], X["auc_test_answers__denial_gptoss"], X["auc_test_answers__conceal_gptoss"])),
                AUC_CONC_G="%.2f" % X["auc_test_answers__conceal_gptoss"], AUC_CONC_R2F="%.2f" % X["auc_test_answers__conceal_r2f_only_gptoss"],
                CONC_R2F_ANS="%.1f%%" % (100 * cl[("gptoss", "answers", "r2f-confidant")]), CONC_R2S_ANS="%.1f%%" % (100 * cl[("gptoss", "answers", "r2s-confidant")]),
                CONC_R3F_ANS="%.1f%%" % (100 * cl[("gptoss", "answers", "r3f-public")]), CONC_R2F_CHAT="%.1f%%" % (100 * cl[("gptoss", "chat", "r2f-confidant")]),
                CONC_Q_R2F="%.1f%%" % (100 * cl[("qwen", "answers", "r2f-confidant")]), CONC_Q_R4="%.1f%%" % (100 * cl[("qwen", "answers", "r4-announced")]),
                CQ_ANS_G="%.0f / %.0f / %.0f" % (X["claude_answers_gptoss_q25"], X["claude_answers_gptoss_q50"], X["claude_answers_gptoss_q75"]),
                CQ_CHAT_G="%.0f / %.0f / %.0f" % (X["claude_chat_gptoss_q25"], X["claude_chat_gptoss_q50"], X["claude_chat_gptoss_q75"]),
                MINHOLM_A="%.2f" % A.holm.min(), MINHOLM_C="%.2f" % C.holm.min(),
                CTL_EXPL_G="%.1f%%" % (100 * ctl[("gptoss", "explicit_agreement_share")]), CTL_EXPL_Q="%.1f%%" % (100 * ctl[("qwen", "explicit_agreement_share")]),
                )
    for k, v in vals.items():
        rep = rep.replace("{{" + k + "}}", str(v))
    missing = [x for x in rep.split("{{")[1:]]
    if missing:
        print("UNFILLED", [m.split("}}")[0] for m in missing])
    out = os.environ.get("REPORT_OUT", os.path.join(HERE, "ANALYSIS.md"))
    open(out, "w", encoding="utf8").write(rep)
    print("ANALYSIS.md written", len(rep))


if __name__ == "__main__":
    main()
