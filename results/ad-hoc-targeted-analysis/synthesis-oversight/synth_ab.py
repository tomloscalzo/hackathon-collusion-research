"""Synthesis Parts A and B: post-processing of committed game-level tables (no new games).

Part A: the reasoning-monitor (CoT) threat effect by condition, plus the share of the control's excess price
        (price index above 0) that the threat removes, and between-condition differences of the effect.
Part B: concealment / appearance keyword shares by oversight arm, paired arm-vs-arm within model.

Run from the repository root:  python -X utf8 results/ad-hoc-targeted-analysis/synthesis-oversight/synth_ab.py
Outputs: partA_conditions.csv, partA_between.csv, partB_arm_vs_control.csv, partB_arm_vs_arm.csv (same folder).
Bootstrap: 10,000 resamples over (wording, seed) pairs, percentile 95% CI, seed 20261026.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
AH = os.path.join(ROOT, "results", "ad-hoc-targeted-analysis")
OUT = os.path.dirname(os.path.abspath(__file__))
B = 10000
rng = np.random.default_rng(20261026)
METS = ["price_index", "profit_gain_index", "competitive_share", "matching_share"]


def boot(x, stat=np.mean):
    x = np.asarray(x, float)
    idx = rng.integers(0, len(x), (B, len(x)))
    s = np.array([stat(x[i]) for i in idx]) if stat is not np.mean else x[idx].mean(1)
    return np.percentile(s, [2.5, 97.5])


def paired(t, c, key=("wording", "seed")):
    m = t.merge(c, on=list(key), suffixes=("_t", "_c"))
    return m


# ---------------- Part A: condition table ----------------
cot = pd.read_csv(os.path.join(AH, "cot-monitor-threat", "game_level.csv"))
wa = pd.read_csv(os.path.join(AH, "wave-a-moral-and-threat0", "data", "game_metrics.csv"))
up = pd.read_csv(os.path.join(AH, "unprimed-levers", "game_metrics.csv"))
wd = pd.read_csv(os.path.join(AH, "watchdog-cot", "game_measures.csv"))

conds = {}
for run in ("neutral", "anchored"):
    ctl = cot[(cot.run == run) & (cot.arm == "headline-chat")]
    for arm, lab in (("d-cot-monitor-a", "A"), ("d-cot-monitor-b", "B")):
        conds[f"Qwen3-32B | {run} printed prices | threat {lab}"] = (cot[(cot.run == run) & (cot.arm == arm)], ctl)
conds["Qwen3-32B | neutral printed prices | threat 0"] = (
    wa[(wa.arm == "d-cot-monitor-0") & (wa.thinking == "on")], wa[(wa.arm == "headline-chat") & (wa.thinking == "on")])
conds["Qwen3-32B | formula, no printed prices | threat A"] = (up[up.cell == "+ CoT threat A"], up[up.cell == "fx-chat-p1 (control)"])
conds["gpt-oss-20b | neutral printed prices | threat A"] = (
    wd[(wd.model == "gpt-oss-20b") & (wd.arm == "d-cot-monitor-a")], wd[(wd.model == "gpt-oss-20b") & (wd.arm == "headline-chat")])

rowsA, diffs = [], {}
for name, (t, c) in conds.items():
    have = [k for k in METS if k in t.columns and k in c.columns]
    m = paired(t[["wording", "seed"] + have], c[["wording", "seed"] + have])
    r = {"condition": name, "n_pairs": len(m)}
    for k in have:
        d = m[k + "_t"] - m[k + "_c"]
        lo, hi = boot(d)
        r.update({f"{k}_ctl": m[k + "_c"].mean(), f"{k}_thr": m[k + "_t"].mean(), f"{k}_diff": d.mean(), f"{k}_lo": lo, f"{k}_hi": hi})
    # share of the control's excess price (price index above the 1.00 floor) removed: -mean(diff)/mean(control)
    pt, pc = m["price_index_t"].values, m["price_index_c"].values
    idx = rng.integers(0, len(pt), (B, len(pt)))
    ratio = 1 - pt[idx].mean(1) / pc[idx].mean(1)
    r["excess_removed"] = 1 - pt.mean() / pc.mean()
    r["excess_removed_lo"], r["excess_removed_hi"] = np.percentile(ratio, [2.5, 97.5])
    rowsA.append(r)
    diffs[name] = m.assign(d=m["price_index_t"] - m["price_index_c"], ct=m["price_index_c"])[["wording", "seed", "d", "ct", "price_index_t"]]
pd.DataFrame(rowsA).to_csv(os.path.join(OUT, "partA_conditions.csv"), index=False)

# between-condition differences of the paired effect, paired on (wording, seed) across runs
between = [
    ("formula A minus neutral A (Qwen)", "Qwen3-32B | formula, no printed prices | threat A", "Qwen3-32B | neutral printed prices | threat A"),
    ("neutral A minus anchored A (Qwen)", "Qwen3-32B | neutral printed prices | threat A", "Qwen3-32B | anchored printed prices | threat A"),
    ("formula A minus anchored A (Qwen)", "Qwen3-32B | formula, no printed prices | threat A", "Qwen3-32B | anchored printed prices | threat A"),
    ("gpt-oss A minus Qwen A (neutral)", "gpt-oss-20b | neutral printed prices | threat A", "Qwen3-32B | neutral printed prices | threat A"),
]
rowsB = []
for lab, a, b in between:
    m = diffs[a].merge(diffs[b], on=["wording", "seed"], suffixes=("_a", "_b"))
    dd = m["d_a"] - m["d_b"]
    lo, hi = boot(dd)
    pa, ca, pb, cb = (m[x].values for x in ("price_index_t_a", "ct_a", "price_index_t_b", "ct_b"))
    idx = rng.integers(0, len(m), (B, len(m)))
    rr = (1 - pa[idx].mean(1) / ca[idx].mean(1)) - (1 - pb[idx].mean(1) / cb[idx].mean(1))
    rowsB.append({"contrast": lab, "n_pairs": len(m), "effect_diff": dd.mean(), "lo": lo, "hi": hi,
                  "excess_removed_diff": (1 - pa.mean() / ca.mean()) - (1 - pb.mean() / cb.mean()),
                  "excess_removed_diff_lo": np.percentile(rr, 2.5), "excess_removed_diff_hi": np.percentile(rr, 97.5)})
pd.DataFrame(rowsB).to_csv(os.path.join(OUT, "partA_between.csv"), index=False)

# ---------------- Part B: concealment by oversight arm ----------------
wd["model"] = wd["model"].str.replace(" (thinking on)", "", regex=False)
# rough length normalisation: share of passages with a hit per 1,000 words of mean passage length
wd["q_conceal_strict_per1k"] = wd["q_conceal_strict"] / wd["q_words"] * 1000
wd["t_conceal_strict_per1k"] = wd["t_conceal_strict"] / wd["t_words"] * 1000
MB = ["q_conceal_strict", "q_conceal", "t_conceal_strict", "t_conceal", "q_conceal_strict_per1k", "t_conceal_strict_per1k",
      "q_watchdog", "q_rival_react", "agree_share", "price_index"]
ARMS = ["d-cot-monitor-a", "wd-noncomp", "wd-notice-only", "wd-ask-noreport"]
rc, ra = [], []
for model, g in wd.groupby("model"):
    ctl = g[g.arm == "headline-chat"]
    for arm in ARMS:
        m = paired(g[g.arm == arm][["wording", "seed"] + MB], ctl[["wording", "seed"] + MB])
        for k in MB:
            d = (m[k + "_t"] - m[k + "_c"]).dropna()
            lo, hi = boot(d)
            rc.append({"model": model, "arm": arm, "measure": k, "n_pairs": len(d), "arm_mean": m[k + "_t"].mean(),
                       "ctl_mean": m[k + "_c"].mean(), "diff": d.mean(), "lo": lo, "hi": hi})
    for i, a1 in enumerate(ARMS):
        for a2 in ARMS[i + 1:]:
            m = paired(g[g.arm == a1][["wording", "seed"] + MB], g[g.arm == a2][["wording", "seed"] + MB])
            for k in MB:
                d = (m[k + "_t"] - m[k + "_c"]).dropna()
                lo, hi = boot(d)
                ra.append({"model": model, "arm1": a1, "arm2": a2, "measure": k, "n_pairs": len(d), "diff": d.mean(), "lo": lo, "hi": hi})
pd.DataFrame(rc).to_csv(os.path.join(OUT, "partB_arm_vs_control.csv"), index=False)
pd.DataFrame(ra).to_csv(os.path.join(OUT, "partB_arm_vs_arm.csv"), index=False)
print("done")

# ---------------- Part B2: candour of the answers to the watchdog (report threat vs none, same questions) ----------------
OSS = os.path.join(ROOT, "results", "oss", "ad-hoc", "watchdog", "answers_keyword_flags.csv")
QW = os.path.join(AH, "watchdog", "answers_keyword_flags.csv")
q = pd.read_csv(QW).rename(columns={"label": "arm"})
q["arm"] = q["arm"].map({"noncomp": "wd-noncomp", "ask-noreport": "wd-ask-noreport"})
q["model"] = "Qwen3-32B " + q["mode"]
o = pd.read_csv(OSS)
o["model"] = "gpt-oss-20b medium"
ans = pd.concat([q, o], ignore_index=True)
ans["wording"] = ans.trial_id.str.extract(r"__w(\d+)__").astype(int)
ans["seed"] = ans.trial_id.str.extract(r"__s(\d+)__").astype(int)
# the admission rule also matches denials ("no coordination"), so also count admissions without a denial
ans["admits_without_denial"] = ((ans["admits_coordination"] == 1) & (ans["claims_independent"] == 0)).astype(int)
rows = []
for model, g in ans.groupby("model"):
    gm = g.groupby(["arm", "wording", "seed"])[["admits_coordination", "admits_without_denial", "claims_independent", "concealment_language"]].mean().reset_index()
    t, c = gm[gm.arm == "wd-noncomp"], gm[gm.arm == "wd-ask-noreport"]
    m = t.merge(c, on=["wording", "seed"], suffixes=("_t", "_c"))
    for k in ("admits_coordination", "admits_without_denial", "claims_independent", "concealment_language"):
        d = m[k + "_t"] - m[k + "_c"]
        lo, hi = boot(d)
        rows.append({"model": model, "measure": k, "n_pairs": len(m), "noncomp": m[k + "_t"].mean(), "ask_noreport": m[k + "_c"].mean(),
                     "diff": d.mean(), "lo": lo, "hi": hi})
pd.DataFrame(rows).to_csv(os.path.join(OUT, "partB_answer_candour.csv"), index=False)
print("candour done")
