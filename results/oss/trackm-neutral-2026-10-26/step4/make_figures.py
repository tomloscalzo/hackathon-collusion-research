"""Step 4 figures for the gpt-oss-20b replication (one figure per section with a numeric contrast).

Two stages:
  1. extract: copy the exact source rows each figure uses into data/fig_<section>.csv
     (long format: row, metric, model, est, lo, hi, n, source, source_key).
  2. plot: build figures/fig_<section>.png from the data/ copies only.

Sources (read-only): out/compare/lever_table.csv, out_t2/step2/tables/contrasts_all.csv,
CLONE/results/oss/ad-hoc/{detection-transfer,penalty,controls}/*.csv.
No new analysis: every plotted value is a copied source value.
Style: dot = estimate, line = 95% CI, gpt-oss-20b (reasoning effort medium) blue circles,
Qwen3-32B (thinking on) vermilion squares (Okabe-Ito, colour-blind safe), fixed axis ranges.

Created by Claude at the prompting of the repository owner.
Usage: python -I -X utf8 make_figures.py   (run via aff.sh to keep cores 0-3 free)
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OSS = os.path.normpath(os.path.join(HERE, "..", ".."))            # work_scratch/oss_analysis
CLONE = os.path.normpath(os.path.join(OSS, "..", "..", "hackathon-collusion-model-analysis-oss_trackm-neutral"))
ADHOC = os.path.join(CLONE, "results", "oss", "ad-hoc")
LEVER = os.path.join(OSS, "out", "compare", "lever_table.csv")
CONTRASTS = os.path.join(OSS, "out_t2", "step2", "tables", "contrasts_all.csv")
DATA = os.path.join(HERE, "data")
FIGS = os.path.join(HERE, "figures")

OSS_M, QWEN_M = "gpt-oss-20b", "Qwen3-32B"
COL = {OSS_M: "#0072B2", QWEN_M: "#D55E00", OSS_M + " (all chat arms)": "#0072B2"}
MARK = {OSS_M: "o", QWEN_M: "s", OSS_M + " (all chat arms)": "^"}
FILL = {OSS_M: True, QWEN_M: True, OSS_M + " (all chat arms)": False}
LEG = {OSS_M: "gpt-oss-20b, reasoning effort medium", QWEN_M: "Qwen3-32B, thinking on",
       OSS_M + " (all chat arms)": "gpt-oss-20b, all chat arms (524 games)"}

METRICS = [("market_price_mean", "spread", "Average absolute spread\n(raw, 1.00 to 5.00)"),
           ("price_index", "price", "Price index\n(0 to 1)"),
           ("profit_gain_index", "pgi", "Profit gain index\n(0 to 1)"),
           ("competitive_share", "comp", "Competitive share\n(higher = more competitive)"),
           ("matching_share", "match", "Matching share\n(coordination signature)")]
DIFF_RANGE = {"market_price_mean": (-2.0, 2.0)}
DIFF_DEFAULT = (-1.1, 1.1)
LEVEL_RANGE = {"market_price_mean": (0.9, 3.1)}
LEVEL_DEFAULT = (-0.05, 1.05)

FIELDS = ["row", "metric", "model", "est", "lo", "hi", "n", "source", "source_key"]


def rd(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rel(path):
    return os.path.relpath(path, OSS).replace("\\", "/") if path.startswith(OSS) else \
        "CLONE/" + os.path.relpath(path, CLONE).replace("\\", "/")


# ---------------------------------------------------------------- extract
def from_lever(rows_spec):
    """rows_spec: list of (row label, topic, contrast)."""
    lev = rd(LEVER)
    out = []
    for label, topic, contrast in rows_spec:
        hit = [r for r in lev if r["topic"] == topic and r["contrast"] == contrast]
        if len(hit) != 5:
            sys.exit(f"lever_table: expected 5 metric rows for {topic} / {contrast}, got {len(hit)}")
        for r in hit:
            key = f"topic={topic}; contrast={contrast}; metric={r['metric']}"
            out.append(dict(row=label, metric=r["metric"], model=OSS_M, est=r["oss_diff"], lo=r["oss_lo"],
                            hi=r["oss_hi"], n=r["oss_n"], source=rel(LEVER), source_key=key + "; cols oss_*"))
            out.append(dict(row=label, metric=r["metric"], model=QWEN_M, est=r["qwen_diff"], lo=r["qwen_lo"],
                            hi=r["qwen_hi"], n=r["qwen_n"], source=rel(LEVER), source_key=key + "; cols qwen_*"))
    return out


def from_contrasts(rows_spec):
    """rows_spec: list of (row label, arm, control)."""
    con = rd(CONTRASTS)
    out = []
    for label, arm, control in rows_spec:
        for metric, short, _ in METRICS:
            hit = [r for r in con if r["arm"] == arm and r["control"] == control and r["outcome"] == short]
            if len(hit) != 1:
                sys.exit(f"contrasts_all: expected 1 row for {arm} / {control} / {short}, got {len(hit)}")
            r = hit[0]
            key = f"arm={arm}; control={control}; outcome={short}"
            out.append(dict(row=label, metric=metric, model=OSS_M, est=r["est"], lo=r["lo"], hi=r["hi"], n=r["n"],
                            source=rel(CONTRASTS), source_key=key + "; cols est/lo/hi"))
            out.append(dict(row=label, metric=metric, model=QWEN_M, est=r["qwen_est"], lo=r["qwen_lo"],
                            hi=r["qwen_hi"], n=r["qwen_n"], source=rel(CONTRASTS),
                            source_key=key + "; cols qwen_est/qwen_lo/qwen_hi"))
    return out


def from_detection(rows_spec, metric_name):
    """rows_spec: list of (row label, detector). Three populations per detector."""
    path = os.path.join(ADHOC, "detection-transfer", "detection_transfer.csv")
    det = rd(path)
    pops = [(QWEN_M, "Qwen headline-chat+monitored, held-out half (frozen, as published)"),
            (OSS_M, "headline-chat (p1,p3,p5)"),
            (OSS_M + " (all chat arms)", "B: all non-bug chat arms of the final data")]
    out = []
    for label, detector in rows_spec:
        for model, pop in pops:
            # Qwen DIFF rows are named without ", Qwen-fitted"
            want = detector if model == QWEN_M else detector.replace("both(quotes+TF-IDF)",
                                                                    "both(quotes+TF-IDF, Qwen-fitted)")
            hit = [r for r in det if r["label"] == "c_outcome" and r["population"] == pop and r["detector"] == want]
            if not hit:
                continue
            r = hit[0]
            out.append(dict(row=label, metric=metric_name, model=model, est=r["auc"], lo=r["auc_lo"], hi=r["auc_hi"],
                            n=r["n"], source=rel(path),
                            source_key=f"label=c_outcome; population={pop}; detector={want}; cols auc/auc_lo/auc_hi"))
    return out


def levels_3_1():
    pen = os.path.join(ADHOC, "penalty", "cells.csv")
    ctl = os.path.join(ADHOC, "controls", "cell_means.csv")
    out = []
    p = rd(pen)
    for label, pp in [("headline-tacit p1: no chat, light penalty (point 1)", "1"),
                      ("headline-tacit p5: no chat, heavy penalty (point 5)", "5")]:
        for model in (OSS_M, QWEN_M):
            for metric, _, _ in METRICS:
                hit = [r for r in p if r["model"] == model and r["arm"] == "headline-tacit"
                       and r["penalty_point"] == pp and r["metric"] == metric]
                if len(hit) != 1:
                    sys.exit(f"penalty/cells.csv: {model} tacit p{pp} {metric}: {len(hit)} rows")
                r = hit[0]
                out.append(dict(row=label, metric=metric, model=model, est=r["mean"], lo=r["lo"], hi=r["hi"],
                                n=r["n"], source=rel(pen),
                                source_key=f"model={model}; arm=headline-tacit; penalty_point={pp}; metric={metric}"))
    c = rd(ctl)
    for label, arm in [("ctl-32b-compete: told to compete (chat, point 3)", "ctl-32b-compete"),
                       ("ctl-32b-joint: told to maximise joint profit (chat, point 3)", "ctl-32b-joint")]:
        for model in (OSS_M, QWEN_M):
            hit = [r for r in c if r["model"] == model and r["arm"] == arm]
            r = hit[0]
            for metric, _, _ in METRICS:
                out.append(dict(row=label, metric=metric, model=model, est=r[metric + "_mean"], lo=r[metric + "_lo"],
                                hi=r[metric + "_hi"], n=r["n"], source=rel(ctl),
                                source_key=f"model={model}; arm={arm}; cols {metric}_mean/_lo/_hi"))
    return out


SPECS = {
    "1_1": dict(kind="diff", title="1.1  Removing the printed example prices lowers prices in every cell (arm minus control)",
                rows=lambda: from_lever([
                    ("nx-chat-p1: no numbers, chat, p1 (vs headline-chat p1)", "payoff-table-focal-points", "nx-chat-p1 (p1) - headline-chat (p1)"),
                    ("nx-tacit-p1: no numbers, no chat, p1 (vs headline-tacit p1)", "payoff-table-focal-points", "nx-tacit-p1 (p1) - headline-tacit (p1)"),
                    ("fx-chat-p1: formula only, chat, p1 (vs headline-chat p1)", "payoff-table-focal-points", "fx-chat-p1 (p1) - headline-chat (p1)"),
                    ("fx-tacit-p1: formula only, no chat, p1 (vs headline-tacit p1)", "payoff-table-focal-points", "fx-tacit-p1 (p1) - headline-tacit (p1)"),
                    ("fx-chat-p5: formula only, chat, p5 (vs headline-chat p5)", "payoff-table-focal-points", "fx-chat-p5 (p5) - headline-chat (p5)"),
                    ("chat - tacit: private chat vs no chat, p1 (printed prices)", "communication", "chat - tacit (p1)")])),
    "1_2": dict(kind="diff", title="1.2  A planted cheater lowers prices on both models (n3-cheater minus n3-group, point 3)",
                rows=lambda: from_lever([
                    ("n3-cheater: 2 LLM firms + scripted cheater (vs n3-group)", "cheater", "n3-cheater - n3-group"),
                    ("n3-group: 3 LLM firms, group chat (vs headline-chat p3)", "cheater", "n3-group - headline-chat (p3)")])),
    "1_3": dict(kind="auc", title="1.3  Detectors frozen on Qwen, applied unchanged to gpt-oss (AUC, label c_outcome)",
                xlabel="AUC (0.5 = chance, 1.0 = perfect)", xrange=(0.0, 1.0), ref=0.5,
                rows=lambda: from_detection([
                    ("quotes: mean early quote (rounds 1-3)", "quotes: mean level"),
                    ("quotes: quote features + logistic regression", "quotes: quote feats + LR"),
                    ("text: keyword-rules score (old detector)", "text: rules score")], "auc")),
    "1_5": dict(kind="diff", title="1.5  Restrictions compared (arm minus control, paired on wording and seed)",
                rows=lambda: from_lever([
                    ("nx-chat-p1: no example prices, chat, p1 (vs headline-chat p1)", "payoff-table-focal-points", "nx-chat-p1 (p1) - headline-chat (p1)"),
                    ("moral-prime-b: pro-competition persona B (vs moral-placebo)", "moral-primes", "moral-prime-b - moral-placebo"),
                    ("moral-prime: pro-competition persona A (vs moral-placebo)", "moral-primes", "moral-prime - moral-placebo"),
                    ("start-5tick: round-1 quotes 1.00-1.05, p3 (vs headline-chat p3)", "five-tick-start", "start-5tick - headline-chat (p3)")])),
    "2_1": dict(kind="diff", title="2.1  A joint-profit goal without printed numbers raises gpt-oss prices (arm minus control)",
                rows=lambda: from_lever([
                    ("fx-ctl-joint: joint-profit goal, formula only, p3 (vs fx-chat-p1)", "payoff-table-focal-points", "fx-ctl-joint (p3) - fx-chat-p1 (p1)"),
                    ("fx-ctl-joint: joint-profit goal, formula only, p3 (vs headline-chat p3)", "payoff-table-focal-points", "fx-ctl-joint (p3) - headline-chat (p3)"),
                    ("chat - tacit: private chat vs no chat, p1 (printed prices)", "communication", "chat - tacit (p1)")])),
    "2_2": dict(kind="auc2", title="2.2  Say, do, and both: frozen detectors (AUC and paired AUC differences, label c_outcome)",
                rows=lambda: from_detection([
                    ("text: chat text alone (TF-IDF + LR)", "text: TF-IDF + LR"),
                    ("quotes: mean early quote", "quotes: mean level"),
                    ("both: quotes + TF-IDF + LR", "both: quotes + TF-IDF + LR")], "auc")
                + from_detection([
                    ("both minus quotes alone (paired)", "DIFF both(quotes+TF-IDF) minus quotes: mean level"),
                    ("both minus text alone (paired)", "DIFF both(quotes+TF-IDF) minus text: TF-IDF + LR")], "auc_diff")),
    "2_3": dict(kind="diff", title="2.3  The instructed controls bracket private chat (control minus headline-chat, point 3)",
                rows=lambda: from_contrasts([
                    ("ctl-32b-compete: told to compete (vs headline-chat p3)", "ctl-32b-compete", "headline-chat p3"),
                    ("ctl-32b-joint: told to maximise joint profit (vs headline-chat p3)", "ctl-32b-joint", "headline-chat p3")])),
    "3_1": dict(kind="level", title="3.1  Levels without chat, beside the two instructed controls (mean over 20 games)",
                rows=levels_3_1),
    "3_2": dict(kind="diff", title="3.2  Trusted agents: a rule-bound third firm and a watchdog (arm minus control)",
                rows=lambda: from_lever([
                    ("n3-ethics: 1 of 3 firms rule-bound, p3 (vs n3-group)", "ethics-rule", "n3-ethics - n3-group (p3)"),
                    ("wd-notice-only: watchdog notice only, p1 (vs headline-chat p1)", "watchdog", "wd-notice-only - headline-chat (p1)"),
                    ("wd-ask-noreport: watchdog asks, p1 (vs headline-chat p1)", "watchdog", "wd-ask-noreport - headline-chat (p1)"),
                    ("wd-noncomp: asks + may report (vs wd-ask-noreport)", "watchdog", "wd-noncomp - wd-ask-noreport")])),
    "3_4": dict(kind="diff", title="3.4  An idle reasoning-monitor threat (d-cot-monitor-a minus headline-chat, point 1)",
                rows=lambda: from_contrasts([
                    ("d-cot-monitor-a: told reasoning is monitored (vs headline-chat p1)", "d-cot-monitor-a", "headline-chat p1")])),
}


def extract(sec):
    rows = SPECS[sec]["rows"]()
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, f"fig_{sec}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- plot
def load(sec):
    return rd(os.path.join(DATA, f"fig_{sec}.csv"))


def dots(ax, data, labels, models, xr, ref):
    offs = {m: o for m, o in zip(models, [-0.18, 0.18] if len(models) == 2 else [-0.24, 0.0, 0.24])}
    for i, lab in enumerate(labels):
        y = len(labels) - 1 - i
        for m in models:
            hit = [d for d in data if d["row"] == lab and d["model"] == m]
            if not hit:
                continue
            d = hit[0]
            e, lo, hi = float(d["est"]), float(d["lo"]), float(d["hi"])
            ax.plot([lo, hi], [y + offs[m]] * 2, color=COL[m], lw=2, solid_capstyle="round")
            ax.plot([e], [y + offs[m]], marker=MARK[m], ms=8, color=COL[m],
                    mfc=COL[m] if FILL[m] else "white", mew=1.6, linestyle="none")
    if ref is not None:
        ax.axvline(ref, color="#888888", lw=1, ls="--", zorder=0)
    ax.set_xlim(*xr)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_yticks(range(len(labels)))
    ax.grid(axis="x", color="#e5e5e5", lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def legend(fig, models, auc=False):
    lab = dict(LEG)
    if auc:
        lab[QWEN_M] = "Qwen3-32B, thinking off and on pooled, held-out half (145 games)"
        lab[OSS_M] = "gpt-oss-20b, headline chat (57 games)"
    hs = [plt.Line2D([], [], color=COL[m], marker=MARK[m], mfc=COL[m] if FILL[m] else "white", mew=1.6, ms=8, lw=2,
                     label=lab[m]) for m in models]
    fig.legend(handles=hs, loc="lower center", ncol=len(models), frameon=False, fontsize=9)


def _w(labels, width=28, lines=3):
    """Owner rule: readable compact ticks: word-wrapped at about 28 characters, at most 3 lines, 9 pt."""
    import textwrap
    out = []
    for l in labels:
        t = textwrap.wrap(str(l), width) or [""]
        if len(t) > lines:
            t = t[:lines]; t[-1] = t[-1][:width - 1].rstrip() + "…"
        out.append(chr(10).join(t))
    return out


def plot(sec):
    spec = SPECS[sec]
    data = load(sec)
    kind = spec["kind"]
    labels = list(dict.fromkeys(d["row"] for d in data))
    if kind in ("diff", "level"):
        models = [OSS_M, QWEN_M]
        rows_h = max(3.4, 0.62 * len(labels) + 2.4)
        fig, axes = plt.subplots(1, 5, figsize=(15, rows_h), sharey=True)
        for ax, (metric, _, mlab) in zip(axes, METRICS):
            sub = [d for d in data if d["metric"] == metric]
            if kind == "diff":
                xr = DIFF_RANGE.get(metric, DIFF_DEFAULT)
                ref = 0.0
            else:
                xr = LEVEL_RANGE.get(metric, LEVEL_DEFAULT)
                ref = 1.0 if metric == "market_price_mean" else 0.0
            dots(ax, sub, labels, models, xr, ref)
            ax.set_title(mlab, fontsize=9)
            ax.set_xlabel("difference (arm minus control)" if kind == "diff" else "level", fontsize=9)
            ax.tick_params(labelsize=9)
        axes[0].set_yticklabels(_w(reversed(labels)), fontsize=9, linespacing=1.0)
    elif kind == "auc":
        models = [QWEN_M, OSS_M, OSS_M + " (all chat arms)"]
        fig, ax = plt.subplots(figsize=(9, 0.9 * len(labels) + 2.4))
        dots(ax, data, labels, models, spec["xrange"], spec["ref"])
        ax.set_yticklabels(_w(reversed(labels)), fontsize=9, linespacing=1.0)
        ax.set_xlabel(spec["xlabel"], fontsize=9)
        axes = [ax]
    elif kind == "auc2":
        models = [QWEN_M, OSS_M, OSS_M + " (all chat arms)"]
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
        for ax, met, xr, ref, xl in [(axes[0], "auc", (0.0, 1.0), 0.5, "AUC (0.5 = chance)"),
                                    (axes[1], "auc_diff", (-0.2, 0.4), 0.0, "paired AUC difference")]:
            sub = [d for d in data if d["metric"] == met]
            labs = list(dict.fromkeys(d["row"] for d in sub))
            dots(ax, sub, labs, models, xr, ref)
            ax.set_yticklabels(_w(reversed(labs)), fontsize=9, linespacing=1.0)
            ax.set_xlabel(xl, fontsize=9)
            ax.tick_params(labelsize=9)
    sub = ("Dot = mean over the 20 games of the cell; line = 95% bootstrap interval over the (wording, seed) units"
           if kind == "level" else "Dot = estimate; line = 95% bootstrap interval over (wording, seed) pairs")
    fig.suptitle(spec["title"] + "\n" + sub,
                 fontsize=10, x=0.01, ha="left")
    legend(fig, models, auc=kind in ("auc", "auc2"))
    h = fig.get_size_inches()[1]
    fig.tight_layout()
    fig.subplots_adjust(top=1 - (0.85 if kind in ("diff", "level") else 0.6) / h, bottom=1.0 / h)
    os.makedirs(FIGS, exist_ok=True)
    fig.savefig(os.path.join(FIGS, f"fig_{sec}.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    secs = sys.argv[1:] or list(SPECS)
    for s in secs:
        extract(s)
        plot(s)
        print("built", s)
