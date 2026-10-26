#!/usr/bin/env python3
"""Scratch cache merge + de-dup (outside the engine; no interface change). Concatenates shard cache files, keeps the
first line per request hash (the same rule CacheFile.load applies), reports conflicts (same hash, different text: the
sign of two backends sharing a model name, F20), and writes one merged cache that `replay --cache` accepts.
Usage: python -X utf8 merge_cache.py --out merged.cache.jsonl SHARD1.cache.jsonl SHARD2.cache.jsonl ...
Also: --runs merged_runs.jsonl RUN1.jsonl RUN2.jsonl ... concatenates run files, dropping exact duplicate (arm, paraphrase,
seed, scenario, model identity, condition) lines (F15 duplicates) and keeping the first; lines of different models
(llm.provider, llm.model) or conditions (llm.condition) are never duplicates of each other.
"""
import argparse, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="merged cache path")
    ap.add_argument("--runs", help="merged run-lines path; the positional files are then run files")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    if a.runs:
        seen = {}
        dup = 0
        for f in a.files:
            for l in open(f, encoding="utf-8"):
                if not l.strip():
                    continue
                d = json.loads(l)
                llm = d.get("llm") or {}
                k = (d.get("arm"), d.get("paraphrase"), d.get("seed"), d.get("scenarioId"), llm.get("provider"), llm.get("model"),
                     llm.get("condition"))
                if k in seen:
                    dup += 1
                    continue
                seen[k] = l
        with open(a.runs, "w", encoding="utf-8") as fh:
            fh.writelines(seen.values())
        print(f"runs: {len(seen)} unique lines, {dup} duplicate(s) dropped -> {a.runs}")
        return 0
    first = {}
    conflicts = 0
    n = 0
    for f in a.files:
        for no, l in enumerate(open(f, encoding="utf-8"), 1):
            if not l.strip():
                continue
            n += 1
            d = json.loads(l)
            if "hash" not in d or d.get("text") is None:
                sys.exit(f"{f}:{no} lacks hash or text")
            h = d["hash"]
            if h in first:
                if json.loads(first[h])["text"] != d["text"]:
                    conflicts += 1
                    print(f"CONFLICT {h[:12]} {f}:{no} differs from first occurrence (drawKey {d.get('drawKey')})")
                continue
            first[h] = l
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.writelines(first.values())
    print(f"cache: {n} lines in, {len(first)} unique hashes out, {conflicts} conflict(s) -> {a.out}")
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
