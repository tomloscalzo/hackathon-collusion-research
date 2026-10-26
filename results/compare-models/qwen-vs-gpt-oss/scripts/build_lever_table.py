"""Collect the per-topic standard_metrics.csv files of the gpt-oss ad-hoc reports into one lever table (Qwen effect vs gpt-oss effect).

usage: python -I -X utf8 build_lever_table.py <adhoc_root> <out_dir>
Each results/oss/ad-hoc/<topic>/standard_metrics.csv is long format: model, contrast, metric, n_pairs, mean_arm, mean_control, diff, lo, hi.
Output: lever_table.csv (one row per topic x contrast x metric, both models side by side, with the replication verdict) and lever_table_rows.md.
Verdict rules (fixed before looking at the numbers):
- sign: 'same' if both CIs exclude 0 on the same side; 'opposite' if both exclude 0 on opposite sides; 'gpt-oss null' / 'Qwen null' if only one excludes 0;
  'both null' if neither does.
- magnitude (only when sign is 'same'): 'similar' if the gpt-oss estimate lies inside the Qwen CI or the Qwen estimate inside the gpt-oss CI; else 'smaller'
  or 'larger' (gpt-oss relative to Qwen, by absolute size).
- replicates: 'yes (sign and magnitude)', 'in sign only', 'no (opposite)', 'no (gpt-oss null)', 'not on Qwen either', 'new on gpt-oss'.
"""
import csv
import sys
from pathlib import Path

root, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
METRICS = ["market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
LABEL = {"market_price_mean": "Average absolute spread", "price_index": "Price index", "profit_gain_index": "Profit gain index",
         "competitive_share": "Competitive share", "matching_share": "Matching share"}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def side(lo, hi):
    if lo is None or hi is None:
        return None
    return 1 if lo > 0 else -1 if hi < 0 else 0


def verdict(q, o):
    sq, so = side(q["lo"], q["hi"]), side(o["lo"], o["hi"])
    if sq is None or so is None:
        return "", "", "not comparable (missing CI)"
    if sq and so and sq == so:
        sim = (q["lo"] <= o["diff"] <= q["hi"]) or (o["lo"] <= q["diff"] <= o["hi"])
        mag = "similar" if sim else ("smaller" if abs(o["diff"]) < abs(q["diff"]) else "larger")
        return "same", mag, "yes (sign and magnitude)" if sim else "in sign only (%s on gpt-oss)" % mag
    if sq and so:
        return "opposite", "", "no (opposite sign)"
    if sq and not so:
        return "gpt-oss null", "", "no (gpt-oss CI includes 0)"
    if so and not sq:
        return "Qwen null", "", "new on gpt-oss (Qwen CI includes 0)"
    return "both null", "", "not on Qwen either (both CIs include 0)"


rows = []
for p in sorted(root.glob("*/standard_metrics.csv")):
    topic = p.parent.name
    data = {}
    with open(p, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            m = (r.get("model") or "").lower()
            key = "qwen" if "qwen" in m else "oss" if "oss" in m else None
            if key is None or r.get("metric") not in METRICS:
                continue
            data.setdefault((r["contrast"], r["metric"]), {})[key] = {k: f(r.get(k)) for k in ("n_pairs", "diff", "lo", "hi", "mean_arm", "mean_control")}
    for (contrast, metric), d in data.items():
        if "oss" not in d:
            continue
        o, q = d["oss"], d.get("qwen")
        s, mg, v = verdict(q, o) if q else ("", "", "no Qwen counterpart")
        rows.append({"topic": topic, "contrast": contrast, "metric": metric, "metric_label": LABEL[metric],
                     "qwen_diff": q and q["diff"], "qwen_lo": q and q["lo"], "qwen_hi": q and q["hi"], "qwen_n": q and q["n_pairs"],
                     "oss_diff": o["diff"], "oss_lo": o["lo"], "oss_hi": o["hi"], "oss_n": o["n_pairs"], "sign": s, "magnitude": mg, "replicates": v})
cols = ["topic", "contrast", "metric", "metric_label", "qwen_diff", "qwen_lo", "qwen_hi", "qwen_n", "oss_diff", "oss_lo", "oss_hi", "oss_n", "sign", "magnitude", "replicates"]
with open(out / "lever_table.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("%.3f" % v if isinstance(v, float) and k not in ("qwen_n", "oss_n") else ("%d" % v if isinstance(v, float) else ("" if v is None else v))) for k, v in r.items()})


def ci(d, lo, hi):
    return "" if d is None else "%+.3f [%+.3f, %+.3f]" % (d, lo, hi)


L = []
for topic in sorted({r["topic"] for r in rows}):
    L.append("### %s\n" % topic)
    L.append("| Contrast | Metric | Qwen3-32B (thinking on) diff [95% CI], n | gpt-oss-20b (medium) diff [95% CI], n | Replicates? |\n|---|---|---|---|---|")
    for r in [x for x in rows if x["topic"] == topic]:
        L.append("| %s | %s | %s | %s | %s |" % (r["contrast"], r["metric_label"],
                 (ci(r["qwen_diff"], r["qwen_lo"], r["qwen_hi"]) + (", %d" % r["qwen_n"] if r["qwen_n"] else "")) if r["qwen_diff"] is not None else "not available",
                 ci(r["oss_diff"], r["oss_lo"], r["oss_hi"]) + (", %d" % r["oss_n"] if r["oss_n"] else ""), r["replicates"]))
    L.append("")
(out / "lever_table_rows.md").write_text("\n".join(L), encoding="utf-8")
print("rows", len(rows), "topics", len({r['topic'] for r in rows}))
