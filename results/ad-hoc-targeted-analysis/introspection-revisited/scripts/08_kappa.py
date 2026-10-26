"""Validation of the open-model LABEL rater against a blind Claude reader (the validation2 protocol: blind passages, Cohen's kappa).

  python 08_kappa.py sample   -> WORK/kappa/passages_blind.txt + key.csv (150 firm-round texts, stratified: 50 each of the
                                 answers, rationale and chat channels, half drawn from texts the rater labelled denial or undercut = 1,
                                 so rare labels have enough positives; both models)
  python 08_kappa.py score    -> kappa per label (reader vs rater), written to OUT/kappa_labels.csv
Created by Claude at the prompting of the repository owner."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
from common import WORK  # noqa: E402

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KD = WORK + "/kappa"
KEYS = ["coordination", "denial", "undercut", "explicit_agreement"]


def sample():
    os.makedirs(KD, exist_ok=True)
    L = pd.read_csv(WORK + "/labels_firmround.csv")
    FR = pd.read_pickle(WORK + "/fr_labelled.pkl")
    FR["rat"] = "Plan: " + FR.plan.fillna("") + "\nRationale: " + FR.rationale.fillna("")
    ins = FR.arm.isin(["r2s-confidant", "r3s-public"])
    FR.loc[ins, "q_answer"] = FR.loc[ins, "self_report"].astype(object)
    col = {"answers": "q_answer", "rationale": "rat", "chat": "chat"}
    rng = np.random.default_rng(5)
    picks = []
    for ch in col:
        l = L[(L.channel == ch) & (L.ok == 1)]
        rare = l[(l.denial == 1) | (l.undercut == 1)]
        a = rare.sample(min(25, len(rare)), random_state=5)
        b = l.drop(a.index).sample(50 - len(a), random_state=6)
        picks.append(pd.concat([a, b]))
    P = pd.concat(picks).sample(frac=1, random_state=7).reset_index(drop=True)
    P["pid"] = ["P%03d" % (i + 1) for i in range(len(P))]
    P = P.merge(FR[["model", "trial_id", "round", "seat", "q_answer", "rat", "chat"]], on=["model", "trial_id", "round", "seat"], how="left")
    with open(KD + "/passages_blind.txt", "w", encoding="utf8") as f:
        for r in P.itertuples():
            f.write("=" * 15 + " %s (kind: %s) " % (r.pid, {"answers": "answer to an after-round question about what it did and why",
                                                         "rationale": "plan and rationale attached to its price",
                                                         "chat": "chat messages sent to the other firm"}[r.channel]) + "=" * 15 + "\n")
            f.write(str(getattr(r, col[r.channel]))[:4000] + "\n\n")
    P[["pid", "model", "trial_id", "round", "seat", "channel"] + KEYS].to_csv(KD + "/key.csv", index=False)
    print("sampled", len(P))


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def score():
    K = pd.read_csv(KD + "/key.csv")
    R = pd.concat([pd.read_csv(KD + "/labels_reader_%s.csv" % h) for h in "AB"], ignore_index=True)
    J = K.merge(R, on="pid", suffixes=("_rater", "_reader"))
    rows = []
    rng = np.random.default_rng(1)
    for ch in ["all"] + sorted(J.channel.unique()):
        j = J if ch == "all" else J[J.channel == ch]
        for k in KEYS:
            x = j[[k + "_rater", k + "_reader"]].dropna().astype(int)
            a, b = x.iloc[:, 0].values, x.iloc[:, 1].values
            bs = []
            for _ in range(2000):
                i = rng.integers(0, len(a), len(a))
                bs.append(kappa(a[i], b[i]))
            rows.append(dict(channel=ch, label=k, n=len(a), agreement=(a == b).mean(), kappa=kappa(a, b),
                             lo=np.nanpercentile(bs, 2.5), hi=np.nanpercentile(bs, 97.5), rater_prev=a.mean(), reader_prev=b.mean()))
    t = pd.DataFrame(rows)
    t.to_csv(OUT + "/kappa_labels.csv", index=False)
    print(t.round(2).to_string())


if __name__ == "__main__":
    {"sample": sample, "score": score}[sys.argv[1]]()
