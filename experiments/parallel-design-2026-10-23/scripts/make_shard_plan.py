#!/usr/bin/env python3
"""Launcher side of the design CSV: expand design_cells.csv into a shard plan (TSV), one shard per
(cell, model, paraphrase, seed block, endpoint).  The analysis side (ingest_merge.py) reads the same CSV, so the
cell ids, arm names and factor levels can never disagree between launcher and analysis.

MOCK use: the plan is consumed by mock/ShardHarness.java, which runs the real CLI against MockLlmServer.
A real launcher would consume the same plan and replace model/endpoint by real snapshots and base URLs.

Usage: python -X utf8 make_shard_plan.py design_cells.csv plan.tsv [--paraphrases 5] [--seeds 6] [--block 3]
                      [--fault SHARD_ID=behaviour ...] [--duplicate SHARD_ID]
"""
import argparse
import csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("plan")
    ap.add_argument("--paraphrases", type=int, default=5)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--block", type=int, default=3, help="seeds per shard")
    ap.add_argument("--endpoints", default="ep-a,ep-b")
    ap.add_argument("--fault", action="append", default=[], help="SHARD_ID=behaviour: override the behaviour of one shard")
    ap.add_argument("--duplicate", action="append", default=[], help="SHARD_ID: emit the shard a second time under a -dup suffix")
    a = ap.parse_args()
    faults = dict(x.split("=", 1) for x in a.fault)
    endpoints = a.endpoints.split(",")
    rows = []
    with open(a.cells, encoding="utf-8", newline="") as f:
        cells = [c for c in csv.DictReader(f) if not c["alias_of"] and c["models"]]
    k = 0
    for c in cells:
        for model in c["models"].split(";"):
            for p in range(a.paraphrases):
                for s0 in range(1, a.seeds + 1, a.block):
                    ep = endpoints[k % len(endpoints)]
                    k += 1
                    s1 = min(a.seeds, s0 + a.block - 1)
                    sid = "%s__%s__p%d__s%d-%d__%s" % (c["arm"], model, p, s0, s1, ep)
                    base = sid.rsplit("__", 1)[0]  # shard id without the endpoint suffix
                    beh = faults.get(sid, faults.get(base, c["mock_behaviour"]))
                    row = [sid, c["arm"], c["scenario"], c["condition"], str(p), str(s0), str(s1 - s0 + 1), model,
                           c["temperature"], beh, ep]
                    rows.append(row)
                    if sid in a.duplicate or base in a.duplicate:
                        rows.append([sid + "-dup"] + row[1:])
    with open(a.plan, "w", encoding="utf-8", newline="") as f:
        f.write("shard_id\tarm\tscenario\tcondition\tparaphrase\tseed\truns\tmodel\ttemperature\tbehaviour\tendpoint\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print("plan: %d shards from %d cells -> %s" % (len(rows), len(cells), a.plan))


if __name__ == "__main__":
    main()
