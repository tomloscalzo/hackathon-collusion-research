"""Targeted analysis 1: communication conditions (tacit, private, monitored, public, unmonitored), neutral run.
Usage: STEP1_DIR=<step1 folder> python communication.py"""
import re, os, numpy as np, pandas as pd
from common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
r = load_run()
arms = {"tacit": "headline-tacit", "private": "headline-chat", "monitored": "headline-monitored",
        "public": "m-pub", "unmonitored": "m-mon0"}
r = r[(r.penalty_point == 3) & r.arm.isin(arms.values())].copy()
r["cond"] = r.arm.map({v: k for k, v in arms.items()})
r["mode"] = r.thinking.map({"off": "thinking off", "on": "thinking on"})
# cell means
rows = []
for (c, m), g in r.groupby(["cond", "mode"]):
    for col in ["price_index", "competitive_share"]:
        mu, lo, hi = boot_ci(g.groupby(["wording", "seed"])[col].mean())
        rows.append(dict(condition=c, mode=m, metric=col, n_games=len(g), mean=mu, lo=lo, hi=hi))
cells = pd.DataFrame(rows); cells.to_csv("cells_by_condition.csv", index=False)
# paired contrasts
cons = [("tacit", x) for x in ["private", "monitored", "public", "unmonitored"]] + \
       [("private", x) for x in ["monitored", "public", "unmonitored"]]
rows = []
for m, g in r.groupby("mode"):
    for col in ["price_index", "competitive_share"]:
        for a, b in cons:
            d = paired(g, col, a, b); mu, lo, hi = boot_ci(d)
            rows.append(dict(mode=m, metric=col, contrast=f"{b} - {a}", n_pairs=len(d), diff=mu, lo=lo, hi=hi, p_signflip=signflip_p(d)))
con = pd.DataFrame(rows)
con["p_holm"] = np.nan
for k, ix in con.groupby(["mode", "metric"]).groups.items():
    con.loc[ix, "p_holm"] = holm(con.loc[ix, "p_signflip"])
con.to_csv("paired_contrasts.csv", index=False)
print(con.round(3).to_string())
# ---- message level ----
rd = pd.read_csv(os.path.join(DATA, "tables", "rounds.csv"), usecols=["trial_id", "round", "seat", "quote"])
ms = pd.read_csv(os.path.join(DATA, "tables", "messages.csv"), usecols=["trial_id", "round", "turn", "seat", "text", "parse_status"])
ms["trial_id"] = ms.trial_id.astype(str)
keep = r.set_index("trial_id")[["cond", "mode"]]
ms = ms[ms.trial_id.isin(keep.index) & (ms.parse_status == "OK")].copy()
rd = rd[rd.trial_id.isin(keep.index)]
num = re.compile(r"(?<![\d.])([1-5](?:\.\d{1,2})?)(?![\d])")
def prices(t):
    out = []
    for x in num.findall(str(t)):
        v = float(x)
        if 1.0 <= v <= 5.0 and ("." in x): out.append(v)   # require a decimal point: avoids "1 of 2", "3 rounds"
    return out
ms["named"] = ms.text.map(prices)
ms["names_price"] = ms.named.map(len) > 0
ms["price_named"] = ms.named.map(lambda l: l[-1] if l else np.nan)  # last price named in the message
q = rd.set_index(["trial_id", "round", "seat"]).quote
ms["q_same"] = [q.get((t, rr, s), np.nan) for t, rr, s in zip(ms.trial_id, ms["round"], ms.seat)]
ms["q_next"] = [q.get((t, rr + 1, s), np.nan) for t, rr, s in zip(ms.trial_id, ms["round"], ms.seat)]
ms = ms.join(keep, on="trial_id")
ms["hit_same"] = ((ms.q_same - ms.price_named).abs() < 0.005)
ms["hit_next"] = ((ms.q_next - ms.price_named).abs() < 0.005)
rows = []
for (c, m), g in ms.groupby(["cond", "mode"]):
    n = g[g.names_price]; nn = g[~g.names_price]
    # game-clustered bootstrap
    def cl(df, col):
        gm = df.dropna(subset=[col]).groupby("trial_id")[col].mean()
        return boot_ci(gm, 4000) if len(gm) > 1 else (np.nan,) * 3
    h = cl(n.assign(h=n.hit_next.astype(float)), "h")
    rows.append(dict(condition=c, mode=m, messages=len(g), share_naming_price=g.names_price.mean(),
        hit_same_round=n.hit_same[n.q_same.notna()].mean(), hit_next_round=n.hit_next[n.q_next.notna()].mean(),
        hit_next_if_hit_same=n.hit_next[n.hit_same & n.q_next.notna()].mean(),
        hit_next_if_miss_same=n.hit_next[~n.hit_same & n.q_next.notna() & n.q_same.notna()].mean(),
        base_next_equals_own_current_quote=(g.q_next == g.q_same)[g.q_next.notna()].mean(),
        mean_next_quote_when_naming=n.q_next.mean(), mean_next_quote_when_not=nn.q_next.mean(),
        corr_named_vs_next_quote=n[["price_named", "q_next"]].dropna().corr(method="spearman").iloc[0, 1]))
msg = pd.DataFrame(rows); msg.to_csv("message_price_naming.csv", index=False)
print(msg.round(3).to_string())
# named price vs next quote, binned
n = ms[ms.names_price & ms.q_next.notna()].copy()
n["named_bin"] = pd.cut(n.price_named, [0.99, 1.5, 2.0, 2.5, 3.01, 5.0], labels=["1.00-1.50", "1.51-2.00", "2.01-2.50", "2.51-3.00", ">3.00"])
b = n.groupby(["mode", "named_bin"], observed=True).agg(messages=("q_next", "size"), mean_next_quote=("q_next", "mean"),
        share_next_equals_named=("hit_next", "mean"), mean_named=("price_named", "mean")).reset_index()
b.to_csv("named_price_bins.csv", index=False); print(b.round(3).to_string())
# figure: drawn by fig_communication.py from cells_by_condition.csv (written above), with "slug: short label" ticks from the shared glossary
import runpy; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_communication.py"))
