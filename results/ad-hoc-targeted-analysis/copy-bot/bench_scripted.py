"""Scripted copy-bot benchmark: two COPIER firms on the slice-m-p1 market, no LLM. CPU only.
Usage: python bench_scripted.py <engine jar> <out dir> <slice-m-p1.yaml scenario file>"""
import csv, json, random, subprocess, sys, tempfile
from pathlib import Path
JAR = sys.argv[1]
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
SC = Path(sys.argv[3]).read_text(encoding="utf-8")
SEEDS = [91,42,226,118,47,94,171,227,55,133,174,259,115,136,193,261,126,151,218,273]  # the 20 declared pairs' seeds
GRID = [round(1 + 0.01 * i, 2) for i in range(0, 401)]   # quote grid 1.00 .. 5.00
S0, SBAR, Q0, N = 1.0, 5.0, 100.0, 2

def scen(oa, ob):
    head = SC.split("agents:\n")[0]
    return head + ("agents:\n  - id: A\n    category: M\n    kind: COPIER\n    config: {open: %s}\n"
                   "  - id: B\n    category: M\n    kind: COPIER\n    config: {open: %s}\n" % (oa, ob))

def run(oa, ob, seed, jar=JAR):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "s.yaml"; f.write_text(scen(oa, ob), encoding="utf-8")
        o = Path(td) / "r.jsonl"
        d = subprocess.run(["java", "-jar", jar, "run", "--scenario", str(f), "--seed", str(seed), "--out", str(o)],
                           capture_output=True, text=True, encoding="utf-8")
        if d.returncode: raise RuntimeError(d.stderr[-400:])
        return json.loads(o.read_text(encoding="utf-8"))

rows = []; rnd = random.Random(20261025)
variants = [("fixed", x, x) for x in (1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00)]
for k in range(10):   # random grid start: each firm draws its own value
    variants.append(("random", rnd.choice(GRID), rnd.choice(GRID)))
for name, oa, ob in variants:
    for seed in SEEDS:
        r = run(oa, ob, seed)
        qa = [x["agents"][0]["displayed"] for x in r["rounds"]]
        qb = [x["agents"][1]["displayed"] for x in r["rounds"]]
        pa = [x["agents"][0]["payoff"] for x in r["rounds"]]
        inside = [x["insideQuote"] for x in r["rounds"]]
        nr = len(qa)
        rows.append(dict(variant=name, open_A=oa, open_B=ob, seed=seed, rounds=nr, first_quote_A=qa[0], first_quote_B=qb[0],
                         last_quote_A=qa[-1], last_quote_B=qb[-1], mean_inside=sum(inside) / nr,
                         price_index=sum(min(1, max(0, (p - S0) / ((S0 + SBAR) / 2 - S0))) for p in inside) / nr,
                         n_distinct_quotes=len(set(qa + qb)), status=r.get("status", ""),
                         quotes_A=" ".join("%.2f" % x for x in qa[:12]), quotes_B=" ".join("%.2f" % x for x in qb[:12])))
with open(OUT / "scripted_copybot_games.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "games")
