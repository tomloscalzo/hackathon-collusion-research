"""Per-input (1-D) aggregates over the wide grid: share where collusion is chosen and mean theta*, for all cells and for
cells without a minimum price step (tick = 0). Usage: python -X utf8 oned_data.py <wide.csv> <out.json>"""
import csv, json, sys
from collections import defaultdict

INPUTS = ["delta", "N", "phi", "tick", "slope", "rhoTip", "pEvidence", "fineRatio", "sBarRatio"]
agg = {k: defaultdict(lambda: [0, 0.0, 0.0, 0, 0.0, 0.0]) for k in INPUTS}
tot = [0, 0.0, 0.0, 0.0, 0.0]
for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")):
    if r["error"]:
        continue
    t = float(r["theta_star"]); c = 1.0 if t > 1e-9 else 0.0
    tf = r["tick"] == "0.0"
    tot[0] += 1; tot[1] += c; tot[2] += t; tot[3] += c * c; tot[4] += t * t
    for k in INPUTS:
        a = agg[k][r[k]]
        a[0] += 1; a[1] += c; a[2] += t
        if tf:
            a[3] += 1; a[4] += c; a[5] += t
out = {}
for k in INPUTS:
    lv = sorted(agg[k], key=float)
    out[k] = {"levels": lv,
              "share_all": [round(agg[k][l][1] / agg[k][l][0], 4) for l in lv],
              "theta_all": [round(agg[k][l][2] / agg[k][l][0], 4) for l in lv],
              "share_tick0": [round(agg[k][l][4] / agg[k][l][3], 4) if agg[k][l][3] else None for l in lv],
              "theta_tick0": [round(agg[k][l][5] / agg[k][l][3], 4) if agg[k][l][3] else None for l in lv]}
    # main-effect share of variance (eta^2)
    for m, i, j in (("share", 1, 3), ("theta", 2, 4)):
        n = tot[0]; mu = tot[i] / n; sst = tot[j] - n * mu * mu
        ssb = sum(agg[k][l][0] * (agg[k][l][i] / agg[k][l][0] - mu) ** 2 for l in lv)
        out[k][f"eta2_{m}"] = round(ssb / sst, 3)
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
for k in INPUTS:
    o = out[k]
    print(k, "eta2", o["eta2_share"], o["eta2_theta"])
    print("  levels ", o["levels"])
    print("  share  ", o["share_all"], "\n  share0 ", o["share_tick0"])
    print("  theta  ", o["theta_all"], "\n  theta0 ", o["theta_tick0"])
