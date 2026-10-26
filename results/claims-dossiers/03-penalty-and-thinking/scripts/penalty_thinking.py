"""Dossier 03, part 1: penalty dose-response, communication x penalty interaction,
thinking x penalty interaction, thinking on vs off (Qwen), and the gpt-oss
comparison. All five standard metrics. Paired on (wording, seed).
Writes: penalty_contrasts.csv, interactions.csv, thinking_contrasts.csv,
cells.csv, tracking_slopes.csv, model_compare.csv, sensitivity.csv."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common03 import *

q = headline("qwen"); o = headline("oss"); o_rep = headline("oss", include_hrep=True)
rows = []

# ---------- cells ----------
cells = []
for name, h in [("qwen", q), ("oss", o)]:
    for (comm, mode, pp), g in h.groupby(["comm", "mode", "penalty_point"]):
        r = dict(model=name, comm=comm, mode=mode, penalty_point=pp, n_games=len(g),
                 theory_price_index=THETA[pp], theory_gain=THEORY_GAIN[pp])
        for m, _, _ in METRICS:
            r[m] = g[m].mean()
        cells.append(r)
cells = pd.DataFrame(cells)
cells.to_csv(f"{OUT}/cells.csv", index=False)

# ---------- penalty steps ----------
def steps(h, name, mode, comm, pts):
    out = []
    for m, lab, _ in METRICS:
        w = cell_wide(h, m, comm, mode)
        for a, b in pts:
            if a in w and b in w:
                x = (w[b] - w[a]).values
                out.append(summarise(x, model=name, mode=mode, comm=comm, contrast=f"p{b}-p{a}", metric=m))
    return out

pen = []
for mode in ["t1", "t0"]:
    for comm in ["tacit", "chat", "monitored"]:
        pen += steps(q, "qwen", mode, comm, [(1, 3), (1, 4), (1, 5), (3, 5), (4, 5)])
pen += steps(o, "oss", "t1", "chat", [(1, 3), (1, 5), (3, 5)])
pen += steps(o, "oss", "t1", "tacit", [(1, 5)])
pen = pd.DataFrame(pen)
# Holm family: within (model, mode, metric), the p_k - p1 steps and p5 - p3 (declared penalty curve)
pen["in_family"] = pen.contrast.isin(["p3-p1", "p4-p1", "p5-p1", "p5-p3"])
fam = holm(pen[pen.in_family], by=["model", "mode", "metric"])
pen = pen.merge(fam[["p_holm", "holm_family_size"]], left_index=True, right_index=True, how="left")
pen.to_csv(f"{OUT}/penalty_contrasts.csv", index=False)

# ---------- tracking slope: per pair OLS slope of metric on theory across points ----------
trk = []
for name, h, modes, comms in [("qwen", q, ["t1", "t0"], ["tacit", "chat", "monitored"]), ("oss", o, ["t1"], ["tacit", "chat"])]:
    for mode in modes:
        for comm in comms:
            for m, theory in [("price_index", THETA), ("profit_gain_index", THEORY_GAIN)]:
                w = cell_wide(h, m, comm, mode).dropna()
                pts = list(w.columns); t = np.array([theory[p] for p in pts])
                tc = t - t.mean()
                sl = (w.values - w.values.mean(1, keepdims=True)) @ tc / (tc @ tc)
                trk.append(summarise(sl, model=name, mode=mode, comm=comm, metric=m,
                                     points="+".join(f"p{p}" for p in pts)))
trk = pd.DataFrame(trk); trk.to_csv(f"{OUT}/tracking_slopes.csv", index=False)

# ---------- interactions ----------
def slope(h, m, comm, mode, a=1, b=5):
    w = cell_wide(h, m, comm, mode)
    return (w[b] - w[a])

inter = []
for m, _, _ in METRICS:
    for mode in ["t1", "t0"]:
        for c2 in ["chat", "monitored"]:
            x = (slope(q, m, c2, mode) - slope(q, m, "tacit", mode)).values
            inter.append(summarise(x, model="qwen", mode=mode, contrast=f"comm x penalty: ({c2} p5-p1) - (tacit p5-p1)", metric=m, family="qwen-interactions"))
    for comm in ["tacit", "chat", "monitored"]:
        x = (slope(q, m, comm, "t1") - slope(q, m, comm, "t0")).values
        inter.append(summarise(x, model="qwen", mode="t1-t0", contrast=f"thinking x penalty: (p5-p1 on) - (p5-p1 off), {comm}", metric=m, family="qwen-interactions"))
    x = (slope(o, m, "chat", "t1") - slope(o, m, "tacit", "t1")).values
    inter.append(summarise(x, model="oss", mode="t1", contrast="comm x penalty: (chat p5-p1) - (tacit p5-p1)", metric=m, family="oss-interaction"))
inter = pd.DataFrame(inter)
inter = holm(inter, by=["family", "metric"])
inter.to_csv(f"{OUT}/interactions.csv", index=False)

# ---------- thinking on - off (Qwen) ----------
th = []
for m, _, _ in METRICS:
    for comm in ["tacit", "chat", "monitored"]:
        a = cell_wide(q, m, comm, "t1"); b = cell_wide(q, m, comm, "t0")
        x = (a.mean(1) - b.mean(1)).values
        th.append(summarise(x, model="qwen", contrast=f"on - off, {comm}, pooled p1/p3/p4/p5", metric=m, family="thinking-main"))
        for pp in [1, 3, 4, 5]:
            th.append(summarise((a[pp] - b[pp]).values, model="qwen", contrast=f"on - off, {comm}, p{pp}", metric=m, family="thinking-cells"))
th = pd.DataFrame(th)
th = holm(th, by=["family", "metric"])
# all arms with both modes (Q17): on - off profit gain per arm (pooled over its points)
d = load("qwen")
arm_rows = []
for arm, g in d.groupby("arm"):
    w = g.pivot_table(index=["pair", "penalty_point"], columns="mode", values="profit_gain_index")
    if {"t0", "t1"} <= set(w.columns):
        x = (w.t1 - w.t0).groupby(level=0).mean().values
        if len(x) >= 10:
            r = summarise(x, model="qwen", contrast=f"on - off, arm {arm}", metric="profit_gain_index", family="thinking-all-arms")
            r["arm"] = arm
            r["tok_cap_quote_t0"] = g[g["mode"] == "t0"].max_tokens_quote.median()
            r["tok_cap_quote_t1"] = g[g["mode"] == "t1"].max_tokens_quote.median()
            arm_rows.append(r)
arms = holm(pd.DataFrame(arm_rows), by=["family"])
arms.to_csv(f"{OUT}/thinking_all_arms.csv", index=False)
th.to_csv(f"{OUT}/thinking_contrasts.csv", index=False)

# ---------- gpt-oss vs Qwen, paired across models on (wording, seed) ----------
cmp_rows = []
for m, _, _ in METRICS:
    for comm, a, b in [("chat", 1, 5), ("chat", 1, 3), ("chat", 3, 5), ("tacit", 1, 5)]:
        so = (cell_wide(o, m, comm, "t1")[b] - cell_wide(o, m, comm, "t1")[a])
        for qm in ["t1", "t0"]:
            sq = (cell_wide(q, m, comm, qm)[b] - cell_wide(q, m, comm, qm)[a])
            x = (so - sq).dropna().values
            cmp_rows.append(summarise(x, contrast=f"oss minus qwen {qm}: {comm} p{b}-p{a}", metric=m, family=f"model-compare-{qm}"))
    for qm in ["t1", "t0"]:
        so = slope(o, m, "chat", "t1") - slope(o, m, "tacit", "t1")
        sq = slope(q, m, "chat", qm) - slope(q, m, "tacit", qm)
        cmp_rows.append(summarise((so - sq).dropna().values, contrast=f"oss minus qwen {qm}: comm x penalty interaction", metric=m, family=f"model-compare-{qm}"))
cmp = holm(pd.DataFrame(cmp_rows), by=["family", "metric"])
cmp.to_csv(f"{OUT}/model_compare.csv", index=False)

# ---------- sensitivity (gpt-oss): drop flagged games; add the headline replicate arms ----------
sens = []
of = o[o.primary_flagged != 1]
for m, _, _ in METRICS:
    for comm, a, b in [("chat", 1, 5), ("tacit", 1, 5), ("chat", 1, 3)]:
        w = cell_wide(of, m, comm, "t1")
        sens.append(summarise((w[b] - w[a]).dropna().values, model="oss", variant="drop flagged (original_kept_flagged) games", contrast=f"{comm} p{b}-p{a}", metric=m))
        w = cell_wide(o_rep, m, comm, "t1")   # mean over original + replicate games per pair and cell
        sens.append(summarise((w[b] - w[a]).dropna().values, model="oss", variant="headline + replicate games averaged per pair", contrast=f"{comm} p{b}-p{a}", metric=m))
    # formula arms (no example prices): chat p5 - p1
    dd = load("oss"); fx = dd[dd.arm.isin(["fx-chat-p1", "fx-chat-p5"])]
    w = fx.pivot_table(index="pair", columns="penalty_point", values=m)
    if 1 in w and 5 in w:
        sens.append(summarise((w[5] - w[1]).dropna().values, model="oss", variant="formula arms (exact formula, no example prices)", contrast="chat p5-p1", metric=m))
    qd = load("qwen"); fxq = qd[qd.arm.isin(["fx-chat-p1", "fx-chat-p5"])]
    for qm in ["t1", "t0"]:
        w = fxq[fxq["mode"] == qm].pivot_table(index="pair", columns="penalty_point", values=m)
        if 1 in w and 5 in w:
            sens.append(summarise((w[5] - w[1]).dropna().values, model=f"qwen {qm}", variant="formula arms (exact formula, no example prices)", contrast="chat p5-p1", metric=m))
    # Qwen: drop truncation-rerun pairs
    qq = q[q.supersession == "none"]
    for qm in ["t1", "t0"]:
        for comm in ["tacit", "chat"]:
            w = cell_wide(qq, m, comm, qm)
            sens.append(summarise((w[5] - w[1]).dropna().values, model=f"qwen {qm}", variant="drop pairs with a truncation-rerun game", contrast=f"{comm} p5-p1", metric=m))
pd.DataFrame(sens).to_csv(f"{OUT}/sensitivity.csv", index=False)
print("done")
