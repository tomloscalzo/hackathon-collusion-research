#!/usr/bin/env python3
"""Stage 3: the findings ledger.  One row per (contrast, model) from tools/analysis.py --json (pre-declared family,
unchanged) and exploratory_contrasts.py (exploratory family), plus descriptive rows (controls, sanity control, refusal
picture).  Runs the sanity gate first: results are only labelled A/B/C when the gate passes.  Standard library only.

Confidence:  A = pre-declared SUPPORTED/REFUTED (Holm, band edge applied);  B = exploratory BH-significant and robust
(sign fraction >= 2/3, refusal bound (if required) excludes zero);  C = exploratory suggestive (not BH-significant but the
unadjusted one-sided 95% lower bound > 0) or pre-declared INCONCLUSIVE with the point in the predicted direction;
D = descriptive / no data / wrong direction.
Interestingness = effect x robustness x relevance; effect = |point| / max(band edge, 0.1); robustness = mean of
(sign fraction, bound ok, replicated across models [0.5 when a second model has no data]); relevance from design_contrasts.csv.
Rows with score >= --threshold (or confidence A) go to the main section, the rest to the appendix.

Usage: python -X utf8 ledger.py --repo DIR --analysis analysis.json --exploratory exploratory.json --qc qc.json
          --contrasts design_contrasts.csv --cells design_cells.csv --runs runs.csv --out ledger.csv [--threshold 0.5]
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict

HEADER = ["finding_id", "claim", "statistic", "contrast", "models", "point", "lower", "upper", "family_status", "band_edge",
          "paraphrase_spread", "refusal_bound", "n_per_arm", "evidence", "confidence", "score", "section", "sprint_q", "aud_tags", "caveats", "gate"]


def f3(x):
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else "%.3f" % x


def sanity_gate(an, qc, analysis, specs):
    g = dict(qc["gate"])
    g.pop("all", None)
    for model, res in analysis.items():
        g["controls_passed@" + model] = res["controls"]["status"] == "PASSED"
    # sign convention: the pre-declared rows of the design CSV must match analysis.py's frozen table, predicted sign > 0
    ok = True
    for cid, s in specs.items():
        if s["family"] != "predeclared":
            continue
        d = an.DEFAULT_DESIGN.get(cid)
        ok = ok and d is not None and d["a"] == s["arm_a"] and d["b"] == s["arm_b"] and d["stat"] == s["stat"] and s["predicted_sign"] == "+1" \
            and sorted(d.get("band_seats", [])) == sorted(x for x in s["band_seats"].split(";") if x)
    g["sign_convention_matches_predictions"] = ok
    # band rows exist for every contrast that names a band
    missing = []
    for model, res in analysis.items():
        for cid, r in res["family"].items():
            if specs.get(cid, {}).get("band_contrast") and r.get("built") and "no reference band row" in (r.get("bandNote") or ""):
                missing.append(cid + "@" + model)
    g["band_rows_present"] = not missing
    g["all"] = all(g.values())
    return g, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("repo", "analysis", "exploratory", "qc", "contrasts", "cells", "runs", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(a.repo, "tools"))
    import analysis as an
    analysis = json.load(open(a.analysis, encoding="utf-8"))
    explo = json.load(open(a.exploratory, encoding="utf-8"))
    qc = json.load(open(a.qc, encoding="utf-8"))
    specs = {r["contrast_id"]: r for r in csv.DictReader(open(a.contrasts, encoding="utf-8", newline=""))}
    alias = {r["arm"]: r["alias_of"] for r in csv.DictReader(open(a.cells, encoding="utf-8", newline="")) if r["alias_of"]}
    shards = defaultdict(set)
    for r in csv.DictReader(open(a.runs, encoding="utf-8", newline="")):
        shards[(r["arm"], r["model"])].add(r["shard_id"])
    gate, missing_bands = sanity_gate(an, qc, analysis, specs)
    gate_txt = "PASS" if gate["all"] else "FAIL:" + ",".join(k for k, v in gate.items() if not v and k != "all")

    def evidence(cid, model, arms):
        ss = sorted(set().union(*(shards[(alias.get(x, x), model)] for x in arms)))
        return "cell=%s; shards=%d [%s]; %s; runs.csv arm in %s" % (cid, len(ss), " ".join(ss[:3]) + (" ..." if len(ss) > 3 else ""), os.path.basename(a.analysis), arms)

    def robustness(sign_frac, bound_ok, other_models):
        rep = 0.5 if not other_models else (1.0 if any(other_models) else 0.0)
        return (sign_frac + (1.0 if bound_ok else 0.0) + rep) / 3.0

    rows = []
    # ---- pre-declared (tools/analysis.py output, unchanged)
    for model, res in sorted(analysis.items()):
        for cid in an.FAMILY:
            r = res["family"][cid]
            s = specs.get(cid, {})
            point, lower, upper = r.get("point"), r.get("lower"), r.get("upper")
            fam = "Holm alpha_i=%s rejected=%s outcome=%s" % (f3(r.get("alpha_i")), r.get("rejected"), r["outcome"])
            cav = [r.get("reason", "")]
            if r.get("smallerThanSpread"):
                cav.append("effect smaller than its paraphrase spread")
            if r.get("boundIncludesZero"):
                cav.append("refusal bound includes zero")
            if "boundPoint" in r and r["outcome"] == "REFUTED" and (r.get("boundLower") or 0) > 0:
                cav.append("BOUND-CONTESTED: refusers scored 0 give a positive effect (%s), the REFUTED verdict rests on the excluded-refuser sample" % f3(r["boundPoint"]))
            if "boundPoint" in r and r["outcome"] == "SUPPORTED" and r.get("boundIncludesZero"):
                cav.append("BOUND-CONTESTED: the refusal bound includes zero")
            if not r.get("built", True):
                cav.append("variant not built")
            if r["outcome"] in ("SUPPORTED", "REFUTED"):
                conf = "A"
            elif point is not None and point > 0 and "not decisive" in r.get("reason", ""):
                conf = "C"
            else:
                conf = "D"
            others = [analysis[m]["family"][cid]["outcome"] == r["outcome"] for m in analysis if m != model and analysis[m]["family"][cid].get("point") is not None]
            sf = (sum(1 for v in r.get("clusterValues", {}).values() if v > 0) / len(r["clusterValues"])) if r.get("clusterValues") else 0.0
            bound_ok = ("boundPoint" not in r) or (r.get("boundLower", 0) > 0)
            eff = abs(point) / max(r.get("bandEdge") or 0.0, an.REFUTE_BELOW) if point is not None else 0.0
            score = eff * robustness(sf, bound_ok, others) * float(s.get("relevance_weight", 0.5))
            rows.append({"finding_id": "%s@%s" % (cid, model), "claim": s.get("claim", cid), "statistic": r.get("stat"), "contrast": "%s - %s" % (r.get("a"), r.get("b")),
                         "models": model, "point": f3(point), "lower": f3(lower), "upper": f3(upper), "family_status": fam, "band_edge": f3(r.get("bandEdge")),
                         "paraphrase_spread": "clusters=%s range=[%s,%s] sd=%s" % (r.get("clusters"), f3(r.get("spreadMin")), f3(r.get("spreadMax")), f3(r.get("spreadSd"))),
                         "refusal_bound": "rates A/B %s/%s%s" % (f3(r.get("refusalA")), f3(r.get("refusalB")), "; bound %s [%s,%s]" % (f3(r["boundPoint"]), f3(r.get("boundLower")), f3(r.get("boundUpper"))) if "boundPoint" in r else ""),
                         "n_per_arm": "%s/%s" % (r.get("nA", 0), r.get("nB", 0)), "evidence": evidence(cid, model, [r.get("a"), r.get("b")]), "confidence": conf if gate["all"] else "GATE-FAILED",
                         "score": f3(score), "section": "main" if conf == "A" or score >= a.threshold else "appendix", "sprint_q": s.get("sprint_q", ""), "aud_tags": s.get("aud_tags", ""),
                         "caveats": "; ".join(c for c in cav if c), "gate": gate_txt})
    # ---- exploratory
    for model, res in sorted(explo.items()):
        for cid, r in res.items():
            s = specs[cid]
            point = r.get("point")
            fam = "BH q=%s significant=%s level=%s status=%s" % (f3(r.get("qValue")), r.get("bhSignificant"), r.get("bhLevel"), r.get("status"))
            bound_ok = ("boundPoint" not in r) or (r.get("boundLower95", 0) > 0)
            robust = r.get("signFrac", 0) >= 2 / 3 and bound_ok
            if point is None:
                conf = "D"
            elif r.get("bhSignificant") and robust and r.get("status") == "ESTIMATED":
                conf = "B"
            elif point > 0 and r.get("lower95", 0) > 0:
                conf = "C"
            else:
                conf = "D"
            cav = [r.get("status", "")]
            if not r.get("bandSizeMatched"):
                cav.append("band not at matched design size (regenerate bands.csv at this clusters x seeds)")
            if "boundPoint" in r and not bound_ok:
                cav.append("refusal bound does not exclude zero")
            if r.get("effectSpreadRatio") is not None and abs(r["effectSpreadRatio"]) < 1:
                cav.append("effect smaller than its paraphrase spread")
            if "placeholder" in s.get("claim", ""):
                cav.append("predicted sign is a placeholder")
            others = [explo[m][cid].get("bhSignificant", False) for m in explo if m != model and explo[m][cid].get("point") is not None]
            if not others:
                cav.append("single model")
            eff = abs(point) / max(r.get("bandEdge") or 0.0, an.REFUTE_BELOW) if point is not None else 0.0
            score = eff * robustness(r.get("signFrac", 0.0), bound_ok, others) * float(s["relevance_weight"])
            rows.append({"finding_id": "%s@%s" % (cid, model), "claim": s["claim"], "statistic": r["stat"], "contrast": "%s - %s (oriented, sign %+d)" % (r["a"], r["b"], r["sign"]),
                         "models": model, "point": f3(point), "lower": f3(r.get("lower95")), "upper": f3(r.get("upper95")), "family_status": fam, "band_edge": f3(r.get("bandEdge")),
                         "paraphrase_spread": "clusters=%s range=[%s,%s] sd=%s signFrac=%s" % (r.get("clusters"), f3(r.get("spreadMin")), f3(r.get("spreadMax")), f3(r.get("spreadSd")), f3(r.get("signFrac"))),
                         "refusal_bound": "rates A/B %s/%s%s" % (f3(r.get("refusalA")), f3(r.get("refusalB")), "; bound %s lower %s" % (f3(r["boundPoint"]), f3(r["boundLower95"])) if "boundPoint" in r else ""),
                         "n_per_arm": "%s/%s" % (r.get("nA", 0), r.get("nB", 0)), "evidence": evidence(cid, model, [r["a"], r["b"]]), "confidence": conf if gate["all"] else "GATE-FAILED",
                         "score": f3(score), "section": "main" if score >= a.threshold and conf in "BC" else "appendix", "sprint_q": s["sprint_q"], "aud_tags": s["aud_tags"],
                         "caveats": "; ".join(c for c in cav if c), "gate": gate_txt})
    # ---- descriptive rows: controls, sanity, refusal picture
    for model, res in sorted(analysis.items()):
        c = res["controls"]
        for key in ("e2", "competitive", "spontaneous"):
            v = c[key]
            rows.append({"finding_id": "P2-%s@%s" % (key, model), "claim": "control: mean CI of the %s arm" % v["arm"], "statistic": "meanCi", "contrast": v["arm"], "models": model,
                         "point": f3(v.get("mean")), "lower": f3(v.get("lo95")), "upper": f3(v.get("hi95")), "family_status": "P2 harness check: " + c["status"], "band_edge": "",
                         "paraphrase_spread": "", "refusal_bound": "", "n_per_arm": str(v["n"]), "evidence": evidence("P2", model, [v["arm"]]), "confidence": "D", "score": "", "section": "controls",
                         "sprint_q": "", "aud_tags": "AUD-EVAL", "caveats": "", "gate": gate_txt})
        s = res["sanity"]
        rows.append({"finding_id": "P1-A'@%s" % model, "claim": "sanity control: mean CI ripe minus unripe-A'", "statistic": "meanCi", "contrast": "ripe - unripe-a-prime", "models": model,
                     "point": f3(s.get("point")), "lower": f3(s.get("lower95")), "upper": "", "family_status": "outside the family: " + s["status"], "band_edge": "", "paraphrase_spread": "",
                     "refusal_bound": "", "n_per_arm": "", "evidence": evidence("P1-A'", model, ["ripe", "unripe-a-prime"]), "confidence": "D", "score": "", "section": "controls", "sprint_q": "",
                     "aud_tags": "AUD-EVAL", "caveats": "", "gate": gate_txt})
    for key, v in sorted(qc["refusal_by_model_arm"].items()):
        arm, model = key.split("|")
        rows.append({"finding_id": "refusal-%s@%s" % (arm, model), "claim": "refusal rate of arm %s" % arm, "statistic": "refuser share", "contrast": arm, "models": model, "point": f3(v["refusal_rate"]),
                     "lower": "", "upper": "", "family_status": "descriptive", "band_edge": "", "paraphrase_spread": "", "refusal_bound": "imputed-round rate %s" % f3(v["imputed_round_rate"]),
                     "n_per_arm": str(v["runs"]), "evidence": evidence("refusal", model, [arm]), "confidence": "D", "score": "", "section": "refusals", "sprint_q": "", "aud_tags": "AUD-ALN",
                     "caveats": "", "gate": gate_txt})
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    print("GATE %s %s" % (gate_txt, json.dumps({k: v for k, v in gate.items() if not v})))
    if missing_bands:
        print("missing band rows:", missing_bands)
    print("ledger rows %d -> %s" % (len(rows), a.out))
    for r in sorted((r for r in rows if r["score"]), key=lambda r: -float(r["score"]))[:8]:
        print("  %-5s %-5s score %s  %-22s point %s [%s, %s]  %s" % (r["confidence"], r["section"], r["score"], r["finding_id"], r["point"], r["lower"], r["upper"], r["family_status"][:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
