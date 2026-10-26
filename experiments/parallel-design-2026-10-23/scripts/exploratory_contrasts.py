#!/usr/bin/env python3
"""Stage 2b: the exploratory family.  Same estimator as tools/analysis.py (paired (paraphrase, seed) cells, paraphrase
clusters, percentile cluster bootstrap with B = 4000 and a fixed seed), run for arbitrary (arm_a, arm_b) pairs listed in
design_contrasts.csv with family = exploratory, per model, with Benjamini-Hochberg over the family instead of Holm, and
a band-edge lookup in the engine's bands.csv with a design-size match check.  Standard library only.

Reused from tools/analysis.py (imported): clusters, cell_means, bootstrap_means, percentile, band_edge, load_bands,
load_runs, n_runs, refusal_rate, mean, sd, model_of, B, SEED, MIN_RUNS, REFUSAL_GAP.  Nothing of analysis.py is changed.

Usage: python -X utf8 exploratory_contrasts.py --repo DIR --runs merged_runs.jsonl --contrasts design_contrasts.csv
          --cells design_cells.csv --bands bands.csv --out OUTDIR [--q 0.10] [--family exploratory]
Outputs: OUTDIR/exploratory.json, OUTDIR/exploratory.csv, OUTDIR/dashboards/paraphrase_spread.csv (every contrast of the
CSV, pre-declared ones included as DESCRIPTIVE rows: their inference comes from tools/analysis.py only).
"""
import argparse
import csv
import json
import math
import os
import random
import sys
from collections import defaultdict


def bh(pvals, q):
    """pvals: dict id -> p (None = no data).  Returns dict id -> (q_value, significant)."""
    items = sorted((p, k) for k, p in pvals.items() if p is not None)
    m = len(items)
    out = {}
    running = 1.0
    for rank in range(m, 0, -1):
        p, k = items[rank - 1]
        running = min(running, p * m / rank)
        out[k] = (running, running <= q)
    for k in pvals:
        out.setdefault(k, (None, False))
    return out


def seeds_per_paraphrase(recs, arm):
    per = defaultdict(set)
    for r in recs:
        if r.get("arm") == arm and not r.get("refuser"):
            per[r.get("paraphrase")].add(r.get("seed"))
    return sorted(len(s) for s in per.values())


def one_contrast(an, cid, spec, recs, bands, model):
    sign = int(spec["predicted_sign"])
    a, b, stat = spec["arm_a"], spec["arm_b"], spec["stat"]
    res = {"contrast": cid, "model": model, "family": spec["family"], "stat": stat, "a": a, "b": b, "sign": sign,
           "nA": an.n_runs(recs, a), "nB": an.n_runs(recs, b), "refusalA": an.refusal_rate(recs, a), "refusalB": an.refusal_rate(recs, b)}
    seats = [s for s in spec["band_seats"].split(";") if s]
    edge, note = an.band_edge(bands, [spec["band_contrast"]] if spec["band_contrast"] else [], seats)
    res["bandEdge"], res["bandNote"] = edge, note
    rows = [r for r in bands if r.get("contrast") == spec["band_contrast"]]
    spp = seeds_per_paraphrase(recs, a)
    cl = an.clusters(recs, a, b, stat)
    res["clusters"] = len(cl)
    res["bandSizeMatched"] = bool(rows) and all(int(r["clusters"]) == len(cl) and int(r["seeds_per_cluster"]) == (spp[len(spp) // 2] if spp else -1) for r in rows)
    if res["nA"] == 0 or res["nB"] == 0:
        res.update({"status": "NO DATA", "p": None})
        return res
    if len(cl) < 2:
        res.update({"status": "INCONCLUSIVE (fewer than 2 clusters)", "p": None})
        return res
    vals = [sign * cl[k] for k in sorted(cl, key=str)]          # oriented: positive = predicted direction
    res["clusterValues"] = {str(k): sign * cl[k] for k in sorted(cl, key=str)}
    res["point"] = an.mean(vals)
    res["spreadMin"], res["spreadMax"], res["spreadSd"] = min(vals), max(vals), an.sd(vals)
    res["signFrac"] = sum(1 for v in vals if v > 0) / len(vals)
    res["effectSpreadRatio"] = (res["point"] / res["spreadSd"]) if res["spreadSd"] and not math.isnan(res["spreadSd"]) and res["spreadSd"] > 0 else None
    boot = an.bootstrap_means(vals, random.Random("%d:%s:%s" % (an.SEED, cid, model)))
    res["p"] = (1 + sum(1 for x in boot if x <= 0.0)) / (an.B + 1)
    res["lower95"], res["upper95"] = an.percentile(boot, 5.0), an.percentile(boot, 95.0)
    if abs(res["refusalA"] - res["refusalB"]) > an.REFUSAL_GAP:
        clb = an.clusters(recs, a, b, stat, bound=True)
        if len(clb) >= 2:
            vb = [sign * clb[k] for k in sorted(clb, key=str)]
            bb = an.bootstrap_means(vb, random.Random("%d:%s:%s:bound" % (an.SEED, cid, model)))
            res["boundPoint"], res["boundLower95"] = an.mean(vb), an.percentile(bb, 5.0)
    res["status"] = "INCONCLUSIVE (fewer than %d runs)" % an.MIN_RUNS if min(res["nA"], res["nB"]) < an.MIN_RUNS else "ESTIMATED"
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--contrasts", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--bands")
    ap.add_argument("--out", required=True)
    ap.add_argument("--q", type=float, default=0.10, help="BH false-discovery level of the exploratory family")
    ap.add_argument("--family", default="exploratory")
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(a.repo, "tools"))
    import analysis as an
    os.makedirs(os.path.join(a.out, "dashboards"), exist_ok=True)
    with open(a.contrasts, encoding="utf-8", newline="") as f:
        specs = {r["contrast_id"]: r for r in csv.DictReader(f)}
    with open(a.cells, encoding="utf-8", newline="") as f:
        alias = {r["arm"]: r["alias_of"] for r in csv.DictReader(f) if r["alias_of"]}
    for s in specs.values():                       # resolve alias arms (slope-0.025 -> ripe, ...) exactly as the pre-declared runner does
        s["arm_a"], s["arm_b"] = alias.get(s["arm_a"], s["arm_a"]), alias.get(s["arm_b"], s["arm_b"])
    recs = an.load_runs([a.runs])
    bands = an.load_bands(a.bands)
    by_model = defaultdict(list)
    for r in recs:
        by_model[an.model_of(r)].append(r)
    out, spread_rows = {}, []
    for model, rs in sorted(by_model.items()):
        out[model] = {}
        for cid, spec in specs.items():
            res = one_contrast(an, cid, spec, rs, bands, model)
            if spec["family"] == a.family:
                out[model][cid] = res
            if "point" in res:
                spread_rows.append([model, cid, spec["family"] if spec["family"] == a.family else "DESCRIPTIVE(" + spec["family"] + ")", res["clusters"],
                                    "%.4f" % res["point"], "%.4f" % res["spreadMin"], "%.4f" % res["spreadMax"], "%.4f" % res["spreadSd"],
                                    "%.2f" % res["effectSpreadRatio"] if res["effectSpreadRatio"] is not None else "n/a", "%.2f" % res["signFrac"],
                                    " ".join("%s:%.3f" % kv for kv in res["clusterValues"].items())])
        levels = bh({cid: r.get("p") for cid, r in out[model].items() if r.get("status") == "ESTIMATED"}, a.q)
        for cid, r in out[model].items():
            r["qValue"], r["bhSignificant"] = levels.get(cid, (None, False))
            r["bhLevel"] = a.q
    with open(os.path.join(a.out, "exploratory.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    cols = ["model", "contrast", "stat", "a", "b", "sign", "status", "nA", "nB", "clusters", "point", "lower95", "upper95", "p", "qValue",
            "bhSignificant", "bandEdge", "bandSizeMatched", "spreadSd", "signFrac", "effectSpreadRatio", "refusalA", "refusalB", "boundPoint", "boundLower95"]
    with open(os.path.join(a.out, "exploratory.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for model in sorted(out):
            for cid in specs:
                if cid in out[model]:
                    r = out[model][cid]
                    w.writerow([("%.4f" % r[c]) if isinstance(r.get(c), float) else r.get(c, "") for c in cols])
    with open(os.path.join(a.out, "dashboards", "paraphrase_spread.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "contrast", "family", "clusters", "point(oriented)", "min", "max", "sd", "effect/sd", "sign_frac", "cluster_values"])
        w.writerows(spread_rows)
    for model in sorted(out):
        print("MODEL %s (exploratory family, BH q <= %.2f)" % (model, a.q))
        for cid, r in out[model].items():
            if "point" in r:
                print("  %-4s %-30s point %+.3f [%.3f, %.3f] p %.4f q %s%s band %.3f%s spreadSd %.3f signFrac %.2f n %d/%d refusal %.2f/%.2f%s" % (
                    cid, r["a"] + " - " + r["b"], r["point"], r["lower95"], r["upper95"], r["p"], "%.4f" % r["qValue"] if r["qValue"] is not None else "n/a",
                    " BH-SIG" if r["bhSignificant"] else "", r["bandEdge"], "" if r["bandSizeMatched"] else " (band size NOT matched)", r["spreadSd"],
                    r["signFrac"], r["nA"], r["nB"], r["refusalA"], r["refusalB"], "  bound %+.3f lower %.3f" % (r["boundPoint"], r["boundLower95"]) if "boundPoint" in r else ""))
            else:
                print("  %-4s %-30s %s" % (cid, r["a"] + " - " + r["b"], r["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
