"""Dossier 07 figure: detector AUC with 95% pair-bootstrap CIs, by population and detector.
usage: python -X utf8 d07_figure.py OUTDIR   (reads OUTDIR/detector_auc.csv). Created by Claude at the prompting of the repository owner."""
import sys, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT = sys.argv[1]; a = pd.read_csv(OUT + "/detector_auc.csv")
pops = [("Q-test-t1", "Qwen3-32B thinking on\nheadline + monitored chat\nheld-out half (n 70)"), ("Q-test", "Qwen3-32B on + off pooled\nheadline + monitored chat\nheld-out half (n 145)"),
        ("O-A", "gpt-oss-20b\nheadline chat\n(n 57)"), ("O-B", "gpt-oss-20b\nall chat arms\n(n 524)")]
dets = [("quotes: early mean level", "quotes: mean price index, rounds 1-3", "#1b6ca8"), ("text: TF-IDF + LR", "text: chat words, rounds 1-3 (TF-IDF + LR)", "#d98e04"),
        ("both: quote features + TF-IDF + LR", "both: quote features + chat words", "#6b4c9a")]
fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
for j, (det, lab, col) in enumerate(dets):
    for i, (p, _) in enumerate(pops):
        r = a[(a["pop"] == p) & (a.detector == det)].iloc[0]; x = i + (j - 1) * 0.22
        ax.errorbar(x, r.auc, yerr=[[r.auc - r.auc_lo], [r.auc_hi - r.auc]], fmt="o", color=col, capsize=3, label=lab if i == 0 else None)
ax.axhline(0.5, color="grey", ls=":", lw=1); ax.text(-0.45, 0.505, "chance", fontsize=9, color="grey", ha="left")
ax.set_xticks(range(len(pops))); ax.set_xticklabels([p[1] for p in pops], fontsize=9)
ax.set_ylabel("AUC for the late-outcome label (0.5 = chance, 1 = perfect)"); ax.set_ylim(0.25, 1.02)
ax.set_xlabel("Model and population of games (the detectors were all fitted and thresholded on Qwen3-32B fit-half games only)")
ax.set_title("Early-warning detectors frozen on Qwen3-32B: AUC with 95% CI (bootstrap over (wording, seed) pairs)", fontsize=10)
ax.legend(fontsize=9, loc="lower right", title="Detector (features from rounds 1 to 3 only)", title_fontsize=9)
fig.savefig(OUT + "/../fig_detector_auc.png", dpi=130)
