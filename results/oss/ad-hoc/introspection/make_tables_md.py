"""Prints the Standard metrics markdown tables from standard_metrics.csv / appendix csv (gpt-oss beside Qwen thinking on)."""
import csv
LAB = {"market_price_mean": "Average absolute spread", "price_index": "Price index", "profit_gain_index": "Profit gain index", "competitive_share": "Competitive share", "matching_share": "Matching share"}
def tab(fn, skip=()):
    rows = list(csv.DictReader(open(fn, encoding="utf-8"))); cs = []
    for r in rows:
        if r["contrast"] not in cs: cs.append(r["contrast"])
    for c in cs:
        print("\n**%s**\n" % c)
        print("| Metric | gpt-oss n | gpt-oss arm | gpt-oss control | gpt-oss diff (95% CI) | Qwen n | Qwen diff (95% CI) |\n|---|---|---|---|---|---|---|")
        for m in LAB:
            g = [r for r in rows if r["contrast"] == c and r["metric"] == m and r["model"] == "gpt-oss-20b"][0]
            q = [r for r in rows if r["contrast"] == c and r["metric"] == m and r["model"] == "Qwen3-32B"][0]
            fm = lambda r: "%+.3f (%+.3f, %+.3f)" % (float(r["diff"]), float(r["lo"]), float(r["hi"]))
            print("| %s | %s | %s | %s | %s | %s | %s |" % (LAB[m], g["n_pairs"], g["mean_arm"], g["mean_control"], fm(g), q["n_pairs"], fm(q)))
tab("standard_metrics.csv"); print("\n=== APPENDIX r4"); tab("appendix_r4_announced_11_of_20.csv")
