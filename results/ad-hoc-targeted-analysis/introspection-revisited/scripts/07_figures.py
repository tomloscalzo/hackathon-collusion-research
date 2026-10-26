NL = chr(10)
"""Figures for introspection revisited: a CI forest chart under every delta table, and the detector AUC chart.
Built from the committed CSVs only (no recomputation). Created by Claude at the prompting of the repository owner."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import ci_forest as CF  # noqa: E402
import arm_labels as AL  # noqa: E402

MODEL = {"gptoss": "gpt-oss", "qwen": "Qwen"}


def forest_from(csv, out, rowfn, metrics=None, title=None, filt=None):
    t = pd.read_csv(os.path.join(HERE, csv))
    if filt is not None:
        t = filt(t)
    if metrics:
        t = t[t.metric.isin(metrics)]
    rows = [dict(label=rowfn(r), metric=r.metric.replace("_", " "), estimate=r.estimate, lo=r.lo, hi=r.hi,
                 p=getattr(r, "holm", np.nan)) for r in t.itertuples() if r.estimate == r.estimate]
    CF.forest(rows, os.path.join(HERE, out), title=title)
    slugs = [a for a in dict.fromkeys(t.arm) if a in AL.glossary()] if "arm" in t else []
    extra = ""
    if slugs:
        extra = (NL + NL + "**Rows (y-axis) codes:** each row is 'slug: description (model)'; the model is gpt-oss-20b or Qwen3-32B. "
                 "'all five' = all five question arms pooled." + NL + NL + AL.legend_table(slugs, long=True) + NL + NL +
                 "The 'p=' printed beside each bar is the Holm-adjusted p of that cell (the family is named in the table's Terms)." + NL)
    with open(os.path.join(HERE, out.replace(".png", "_legend.md")), "w", encoding="utf8") as f:
        f.write(CF.legend_md(rows) + extra)


def main():
    forest_from("A_candour_arm_minus_control.csv", "fig_A_candour_rationale.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Candour of the quote plan and rationale: question arm minus no-question control (95% CI over pairs)",
                filt=lambda t: t[t.channel == "rationale"])
    forest_from("A_candour_arm_minus_control.csv", "fig_A_candour_chat.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Candour of the chat: question arm minus no-question control (95% CI over pairs)",
                filt=lambda t: t[t.channel == "chat"])
    forest_from("A_candour_arm_minus_control.csv", "fig_A_candour_reasoning.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Candour of the reasoning (chain of thought): question arm minus no-question control (95% CI over pairs)",
                filt=lambda t: t[t.channel == "reasoning"])
    forest_from("A4_answers_minus_rationale.csv", "fig_A4_answers_minus_rationale.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Introspection answer minus the same game's quote rationale (95% CI over games)")
    forest_from("C_dialogue_arm_minus_control.csv", "fig_C_dialogue.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Inter-firm chat: question arm minus no-question control (95% CI over pairs)")
    forest_from("standard_metrics.csv", "fig_standard_metrics.png",
                lambda r: "%s %s" % (r.arm, MODEL[r.model]),
                title="Five standard metrics: arm minus no-question control (95% CI over pairs)")
    forest_from("B_auc_differences.csv", "fig_B_auc_differences.png",
                lambda r: "%s (%s, %s pairs)" % (r.contrast, MODEL[r.model], "held-out" if r.split == "test" else "all"),
                title="gpt-oss AUC differences between detectors (95% CI over pairs)",
                filt=lambda t: t[t.model == "gptoss"].assign(metric="AUC difference"))

    # detector AUC chart
    ev = pd.read_csv(os.path.join(HERE, "B_detectors.csv"))
    ev = ev[(ev.population == "in-game question arms") & (ev.label == "label_late")]
    dets = ["early_pi", "mon_answers", "mon_answers+chat", "mon_chat", "mon_reasoning", "mon_rationale", "mon_qreasoning", "kw_chat",
            "claude_answers", "claude_chat"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 8), constrained_layout=True, sharex=True)
    for ax, model in zip(axes, ["gptoss", "qwen"]):
        e = ev[ev.model == model].set_index("detector")
        ds = [d for d in dets if d in e.index and e.loc[d].auc_test == e.loc[d].auc_test]
        y = np.arange(len(ds))[::-1]
        for yi, d in zip(y, ds):
            r = e.loc[d]
            col = "#5d7a99" if not d.startswith(("mon_answers", "claude_answers")) else "#8e44ad"
            ax.plot([r.auc_lo, r.auc_hi], [yi, yi], color=col, lw=2)
            ax.plot(r.auc_test, yi, "o", color=col, ms=8)
            ax.text(1.005, yi, "%.2f" % r.auc_test, va="center", fontsize=9)
        ax.axvline(0.5, ls=":", color="k")
        ax.set_yticks(y)
        import textwrap
        ax.set_yticklabels([textwrap.fill(AL.label(d), 26) for d in ds], fontsize=9)
        n = int(e.n_test.max())
        nneg = int(round(e.loc["early_pi"].n_test * (1 - e.loc["early_pi"].prev_test)))
        ax.set_title("%s: held-out games, n up to %d (%d not collusive)\nlabel: late price index >= 0.50" % (MODEL[model], n, nneg), fontsize=10)
        ax.set_xlabel("AUC, held-out pairs (0.5 = chance, 1 = perfect)\nbar = 95% CI, bootstrap over pairs")
        ax.set_xlim(0.0, 1.08)
    fig.suptitle("Which channel lets a monitor forecast sustained high prices from rounds 1-3? (in-game question arms)", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_B_detector_auc.png"), dpi=110)
    print("figures written")


if __name__ == "__main__":
    main()
