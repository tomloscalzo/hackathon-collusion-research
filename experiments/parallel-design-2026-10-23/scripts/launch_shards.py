#!/usr/bin/env python3
"""Scratch parallel runner (outside the engine; no interface change). Shards a design by arm x paraphrase x seed-range and
runs one `java -jar collusion-engine.jar run --seat LLM` process per shard, each with its own --out and --cache, spread
round-robin over one or more --base-url endpoints. Resume: a shard whose --out already has `seeds_per_shard` lines is
skipped (F15 workaround); a partial shard is re-run with --out moved aside first (its cache file is kept, so completed
calls replay from cache and cost nothing). A shard file holding lines of another model (llm.model != --model) is never
skipped or moved: the launcher stops, because shard file names do not carry the model; use one --out-dir per model.

Usage (run from the repo root so classpath scenario names resolve):
  python -X utf8 launch_shards.py --jar engine/target/collusion-engine.jar --out-dir OUT --model M
      --base-url URL [--base-url URL2 ...] --arm ripe=scenarios/ripe-game.yaml[@condition] [--arm ...]
      --paraphrases 0,1,2 --seed0 1 --seeds-per-shard 5 --shards 8 --jobs 8 [--extra "--temperature 0.7"]
Files per shard: OUT/<arm>_p<para>_s<seed0>.jsonl (+ .cache.jsonl, .calls.jsonl, .manifest.json). Seeds of shard k are
seed0 + k*seeds_per_shard .. +seeds_per_shard-1, identical across arms (paired design).
"""
import argparse, os, shlex, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor


def run_lines(p):
    """The run lines of p that parse.  A line that does not (a truncated last line of a killed run, possibly cut inside
    a multi-byte character) is not counted, so such a shard is partial: it is moved aside and rerun."""
    import json
    out = []
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                try:
                    out.append(json.loads(l))
                except ValueError:
                    continue
    return out


def models_in(p):
    """The llm.model values of the run lines already in p."""
    return {(r.get("llm") or {}).get("model") for r in run_lines(p)}


def count_lines(p):
    return len(run_lines(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", action="append", required=True)
    ap.add_argument("--arm", action="append", required=True, help="name=scenario[@condition]")
    ap.add_argument("--paraphrases", default="0")
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--seeds-per-shard", type=int, default=5)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--extra", default="", help="extra CLI options passed verbatim (e.g. --temperature 0.7 --budget-tokens N)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    jobs = []
    i = 0
    for arm in a.arm:
        name, spec = arm.split("=", 1)
        scenario, _, cond = spec.partition("@")  # '@' not ':' so Windows drive letters survive
        for p in [int(x) for x in a.paraphrases.split(",")]:
            for k in range(a.shards):
                s0 = a.seed0 + k * a.seeds_per_shard
                out = os.path.join(a.out_dir, f"{name}_p{p}_s{s0}.jsonl")
                have = count_lines(out)
                other = models_in(out) - {a.model}
                if other:
                    sys.exit(f"{out} holds run lines of another model {sorted(other)}: use a separate --out-dir per model")
                if have == a.seeds_per_shard:
                    print(f"skip {out}: complete ({have} lines)")
                    continue
                if have > 0:
                    aside = out + f".partial-{int(time.time())}"
                    os.replace(out, aside)
                    print(f"partial {out}: {have} lines moved to {aside}; rerun replays its cache")
                url = a.base_url[i % len(a.base_url)]
                i += 1
                cmd = ["java", "-jar", a.jar, "run", "--scenario", scenario, "--seat", "LLM", "--base-url", url,
                       "--model", a.model, "--seed", str(s0), "--runs", str(a.seeds_per_shard), "--paraphrase", str(p),
                       "--arm", name, "--out", out] + (["--condition", cond] if cond else []) + shlex.split(a.extra)
                jobs.append((out, cmd))
    print(f"{len(jobs)} shard(s) to run on {len(a.base_url)} endpoint(s), {a.jobs} at a time")
    if a.dry_run:
        for out, cmd in jobs:
            print(" ".join(cmd))
        return 0

    def run(job):
        out, cmd = job
        t0 = time.time()
        with open(out + ".log", "w", encoding="utf-8") as log:
            rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
        return out, rc, time.time() - t0

    bad = 0
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for out, rc, dt in ex.map(run, jobs):
            print(f"{'ok  ' if rc == 0 else 'FAIL'} rc={rc} {dt:6.1f}s {out} ({count_lines(out)} lines)")
            bad += rc != 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
