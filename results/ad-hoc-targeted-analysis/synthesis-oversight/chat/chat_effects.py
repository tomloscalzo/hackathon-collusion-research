#!/usr/bin/env python3
"""Part C: chat-effect heterogeneity (H3). Private chat minus no chat (tacit), paired on (wording, seed) within
model x thinking x payoff block x penalty point; 95% percentile bootstrap over pairs (10,000 resamples, seed 20261026).

Inputs (environment variable HACKATHON_DIR, default the parent of the repo):
  Qwen3-32B neutral and anchored Step 1 run.csv (work_scratch/analysis_final/steps/<run>/step1/run.csv)
  gpt-oss-20b final Step 1 run.csv (work_scratch/oss_analysis/step1/final/run.csv)
  Qwen3-32B formula / no-numbers raw trials (runs/2026-10-25_trackm_formula, 32k reruns supersede) and the
  Qwen formula joint-profit control (runs/2026-10-25_trackm_fx_ctl_joint), metrics via the repo's run_csv.analyse_game
  (the loader of results/ad-hoc-targeted-analysis/payoff-table-focal-points/formula_no_numbers.py).
Output: chat_effects.csv (one row per contrast) and chat_levels.csv (joint-profit control levels)."""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
HD = Path(os.environ.get("HACKATHON_DIR", REPO.parent))
WS = HD / "work_scratch"
sys.path.insert(0, str(REPO / "results" / "ad-hoc-targeted-analysis" / "payoff-table-focal-points"))
sys.path.insert(0, str(REPO / "tools" / "trial"))
NB, SEED = 10000, 20261026
M = ["price_index", "profit_gain_index"]


def boot(d):
    d = np.asarray(d, float)
    rng = np.random.default_rng(SEED)
    bm = d[rng.integers(0, len(d), (NB, len(d)))].mean(axis=1)
    lo, hi = np.percentile(bm, [2.5, 97.5])
    return d.mean(), lo, hi


def load_runcsv(path, model, run):
    d = pd.read_csv(path, low_memory=False)
    d = d[d.status == "done"].copy()
    d["model"], d["run_label"] = model, run
    d["wording"] = d.wording.astype(int).astype(str)
    d["seed"] = d.seed.astype(int).astype(str)
    d["mode"] = d.thinking.map({"on": "on", "off": "off", 1: "on", 0: "off", "1": "on", "0": "off"})
    if model == "gpt-oss-20b":
        d["mode"] = "medium"
    return d[["model", "run_label", "arm", "penalty_point", "mode", "payoff_examples", "communication", "wording", "seed"] + M]


def load_qwen_formula():
    import formula_no_numbers as F
    rows = []
    for root, rr in [(HD / "runs/2026-10-25_trackm_formula", HD / "runs/2026-10-25_trackm_formula_x32k"),
                     (HD / "runs/2026-10-25_trackm_fx_ctl_joint", None)]:
        games, reruns = F.load_formula(root, rr)
        for tid, g in games.items():
            g = reruns.get(tid, g)
            pp = int(tid.split("__p")[1].split("__")[0])
            rows.append(dict(model="Qwen3-32B", run_label="formula", arm=g["arm"], penalty_point=pp, mode=g["mode"],
                             payoff_examples="none" if g["arm"].startswith("nx") else "formula",
                             communication="tacit" if "tacit" in g["arm"] else "private", wording=g["wording"], seed=g["seed"],
                             price_index=g["price_index"], profit_gain_index=g["profit_gain_index"]))
    return pd.DataFrame(rows)


def contrast(df, model, run, mode, pp, arm_t, arm_r, label, pp_r=None):
    a = df[(df.model == model) & (df.run_label == run) & (df["mode"] == mode) & (df.arm == arm_t) & (df.penalty_point == pp)]
    b = df[(df.model == model) & (df.run_label == run) & (df["mode"] == mode) & (df.arm == arm_r) & (df.penalty_point == (pp_r or pp))]
    j = a.merge(b, on=["wording", "seed"], suffixes=("_t", "_r"))
    if len(j) < 5:
        return None
    out = dict(model=model, run=run, mode=mode, penalty_point=pp, contrast=label, treatment=arm_t, reference=arm_r, n_pairs=len(j))
    for m in M:
        e, lo, hi = boot(j[m + "_t"] - j[m + "_r"])
        out.update({m + "_ref": j[m + "_r"].mean(), m + "_trt": j[m + "_t"].mean(), m + "_diff": e, m + "_lo": lo, m + "_hi": hi})
    return out


def main():
    q = pd.concat([load_runcsv(WS / "analysis_final/steps/neutral/step1/run.csv", "Qwen3-32B", "neutral"),
                   load_runcsv(WS / "analysis_final/steps/anchored/step1/run.csv", "Qwen3-32B", "anchored"),
                   load_qwen_formula()])
    o = load_runcsv(WS / "oss_analysis/step1/final/run.csv", "gpt-oss-20b", "neutral")
    o.loc[o.arm.str.startswith(("fx-", "nx-")), "run_label"] = "formula"
    o.loc[o.arm.str.startswith("hrep-"), "run_label"] = "replicate"
    df = pd.concat([q, o], ignore_index=True)
    R = []
    add = lambda r: r and R.append(r)
    for run in ["neutral", "anchored"]:
        for mode in ["off", "on"]:
            for pp in [1, 3, 4, 5]:
                add(contrast(df, "Qwen3-32B", run, mode, pp, "headline-chat", "headline-tacit", "private chat - tacit"))
                add(contrast(df, "Qwen3-32B", run, mode, pp, "headline-monitored", "headline-tacit", "regulator-monitored chat - tacit"))
                add(contrast(df, "Qwen3-32B", run, mode, pp, "headline-monitored", "headline-chat", "regulator-monitored chat - private chat"))
            add(contrast(df, "Qwen3-32B", run, mode, 3, "m-pub", "headline-tacit", "public chat - tacit"))
            add(contrast(df, "Qwen3-32B", run, mode, 3, "m-pub", "headline-chat", "public chat - private chat"))
            add(contrast(df, "Qwen3-32B", run, mode, 3, "m-mon0", "headline-chat", "'unmonitored' notice chat - private chat"))
    for mode in ["off", "on"]:
        add(contrast(df, "Qwen3-32B", "formula", mode, 1, "fx-chat-p1", "fx-tacit-p1", "private chat - tacit (formula payoff)"))
        add(contrast(df, "Qwen3-32B", "formula", mode, 1, "nx-chat-p1", "nx-tacit-p1", "private chat - tacit (no numbers)"))
    for pp in [1, 5]:
        add(contrast(df, "gpt-oss-20b", "neutral", "medium", pp, "headline-chat", "headline-tacit", "private chat - tacit"))
    add(contrast(df, "gpt-oss-20b", "replicate", "medium", 1, "hrep-fx-chat-p1", "hrep-fx-tacit-p1", "private chat - tacit (replicate wave)"))
    add(contrast(df, "gpt-oss-20b", "replicate", "medium", 1, "hrep-nx-chat-p1", "hrep-nx-tacit-p1", "private chat - tacit (replicate wave 2)"))
    add(contrast(df, "gpt-oss-20b", "formula", "medium", 1, "fx-chat-p1", "fx-tacit-p1", "private chat - tacit (formula payoff)"))
    add(contrast(df, "gpt-oss-20b", "formula", "medium", 1, "nx-chat-p1", "nx-tacit-p1", "private chat - tacit (no numbers)"))
    out = pd.DataFrame(R)
    out.to_csv(HERE / "chat_effects.csv", index=False, float_format="%.4f")
    # joint-profit ceiling controls and the chat level at the same cell
    L = []
    for (model, run, arm, mode, pp), g in df[df.arm.isin(["ctl-32b-joint", "fx-ctl-joint", "ctl-32b-compete"])].groupby(
            ["model", "run_label", "arm", "mode", "penalty_point"]):
        L.append(dict(model=model, run=run, arm=arm, mode=mode, penalty_point=pp, n=len(g), price_index=g.price_index.mean(),
                      profit_gain_index=g.profit_gain_index.mean()))
    for c in [("ctl-32b-joint", "headline-chat"), ("fx-ctl-joint", "headline-chat")]:
        for model in ["Qwen3-32B", "gpt-oss-20b"]:
            for mode in ["off", "on", "medium"]:
                for run in ["neutral", "anchored", "formula"]:
                    sub = df[(df.model == model) & (df.arm == c[0]) & (df["mode"] == mode) & (df.run_label == run)]
                    if len(sub):
                        r = contrast(df.assign(run_label=df.run_label.where(df.arm != c[0], "neutral" if c[0] == "fx-ctl-joint" else df.run_label)),
                                     model, "neutral" if c[0] == "fx-ctl-joint" else run, mode, 3, c[1], c[0], f"{c[1]} - {c[0]} (p3)")
                        if r:
                            r["ceiling_run"] = run
                            L.append(r)
    pd.DataFrame(L).to_csv(HERE / "chat_levels.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    print(out[["model", "run", "mode", "penalty_point", "contrast", "n_pairs", "price_index_ref", "price_index_trt", "price_index_diff",
               "price_index_lo", "price_index_hi", "profit_gain_index_diff", "profit_gain_index_lo", "profit_gain_index_hi"]].round(3).to_string())
    print(pd.DataFrame(L).round(3).to_string())


if __name__ == "__main__":
    main()
