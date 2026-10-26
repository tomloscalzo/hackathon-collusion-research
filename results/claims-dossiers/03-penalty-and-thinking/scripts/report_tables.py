"""Prints the five-metric Markdown tables used in ANALYSIS.md (from the CSVs in the dossier folder)."""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common03 import OUT, METRICS
SHORT = {"market_price_mean": "Avg abs spread", "price_index": "Price index", "profit_gain_index": "Profit gain index",
         "competitive_share": "Competitive share", "matching_share": "Matching share"}
GRP = {("qwen", "t1"): "Qwen3-32B thinking on", ("qwen", "t0"): "Qwen3-32B thinking off", ("oss", "t1"): "gpt-oss-20b (medium effort)"}


def cell(r):
    star = "" if pd.isna(r.get("p_holm", float("nan"))) else f"; Holm p {r.p_holm:.3f}"
    return f"{r.effect:+.3f} [{r.ci_lo:+.3f}, {r.ci_hi:+.3f}]{star}"


def table(df, keys, label):
    print("| " + " | ".join(["Contrast", "Model and mode", "n pairs"] + [SHORT[m] for m, _, _ in METRICS]) + " |")
    print("|" + "---|" * (3 + len(METRICS)))
    for k in keys:
        sub = df
        for c, v in k.items():
            sub = sub[sub[c] == v]
        vals = []
        for m, _, _ in METRICS:
            s = sub[sub.metric == m]
            vals.append(cell(s.iloc[0]) if len(s) else "n/a")
        n = int(sub.n_pairs.iloc[0]) if len(sub) else 0
        print(f"| {label(k)} | {GRP.get((k.get('model'), k.get('mode')), k.get('mode', ''))} | {n} | " + " | ".join(vals) + " |")
    print()


pen = pd.read_csv(f"{OUT}/penalty_contrasts.csv")
keys = []
for comm in ["tacit", "chat", "monitored"]:
    for mode in ["t1", "t0"]:
        for c in ["p3-p1", "p4-p1", "p5-p1"]:
            keys.append(dict(model="qwen", mode=mode, comm=comm, contrast=c))
for comm, cs in [("tacit", ["p5-p1"]), ("chat", ["p3-p1", "p5-p1", "p5-p3"])]:
    for c in cs:
        keys.append(dict(model="oss", mode="t1", comm=comm, contrast=c))
print("### penalty"); table(pen, keys, lambda k: f"{k['comm']} {k['contrast']}")

it = pd.read_csv(f"{OUT}/interactions.csv")
keys = [dict(model=m, mode=mo, contrast=c) for m, mo, c in it[["model", "mode", "contrast"]].drop_duplicates().itertuples(index=False)]
print("### interactions"); table(it, keys, lambda k: k["contrast"])

th = pd.read_csv(f"{OUT}/thinking_contrasts.csv"); th = th[th.family == "thinking-main"]; th["mode"] = "t1-t0"
keys = [dict(contrast=c) for c in th.contrast.unique()]
print("### thinking"); table(th, keys, lambda k: k["contrast"])

mc = pd.read_csv(f"{OUT}/model_compare.csv")
keys = [dict(contrast=c) for c in mc.contrast.unique()]
print("### model compare"); table(mc, keys, lambda k: k["contrast"])
