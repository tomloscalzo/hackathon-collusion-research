"""Dossier 01: in formula-arm reasoning passages, at what price is the demand formula evaluated?
A passage counts as evaluating the formula at price b if it contains "1 - b/5" (keyword pattern, unvalidated).
Output tables/formula_eval_price_level.csv. Usage: python -X utf8 formula_price_level.py <dossier_dir>"""
import os, re, sys, json
import pandas as pd
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
D = sys.argv[1]
HK = os.environ.get("HACKATHON_DIR", os.path.join(os.path.expanduser("~"), "hackathon"))
RE = re.compile(r"1\s*[-−]\s*(\d+(?:\.\d+)?)\s*/\s*5")
G = pd.read_csv(os.path.join(D, "data", "games.csv"))
G = G[G.arm.str.match(r"^fx-") & (G.thinking == "on")]
rows = []
for (model, arm), s in G.groupby(["model", "arm"]):
    n = ev = hi = 0
    for _, r in s.iterrows():
        root = r.run
        tid = r.trial_id
        base = os.path.join(HK, "runs", root, "trials", tid.split("__")[0])
        d = os.path.join(base, tid)
        x = os.path.join(HK, "runs", root + "_x32k", "trials", tid.split("__")[0], tid + "__x32k")
        if getattr(r, "rerun_used", 0) == 1 and os.path.exists(x):
            d = x
        if not os.path.exists(d):
            continue
        for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
            e = json.loads(line)
            if e.get("kind") != "quote" or not isinstance(e.get("reasoning"), str):
                continue
            n += 1
            vals = [float(v) for v in RE.findall(e["reasoning"])]
            if vals:
                ev += 1
                hi += any(v >= 1.80 for v in vals)
    rows.append(dict(model=model, arm=arm, passages=n, evaluate_formula=ev, share_evaluate=ev / max(1, n),
                     evaluate_at_1_80_or_more=hi, share_at_1_80_or_more=hi / max(1, n)))
pd.DataFrame(rows).to_csv(os.path.join(D, "tables", "formula_eval_price_level.csv"), index=False, float_format="%.3f")
print(pd.DataFrame(rows).round(3).to_string())
