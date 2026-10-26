#!/usr/bin/env python3
"""Conduct scoring for the Track S P2 arms (see DECLARATION.md in this folder). Standard library only; READ-ONLY on run data.

Usage:
  python -X utf8 experiments/p2-posthoc-2026-10-24/conduct.py ROOT [ROOT ...] --out-csv conduct.csv --out-md conduct.md

Each ROOT is a directory holding shard files  <arm>_p<paraphrase>_s<seed>.jsonl  (one run line per shard) with the sidecars
.jsonl.cache.jsonl, .jsonl.calls.jsonl, .jsonl.log, .jsonl.manifest.json. A shard that has sidecars but no (or an empty)
run file is counted as ABORTED (the exception line of its log is listed). Rows are grouped by arm x model x thinking x seed
block (seeds 1-4 = original seed set, seeds 5 and up = the extension block). The frozen tools/analysis.py is not used.

Round-1 conduct class, from the LLM's round-1 displayed quote q (rival quote sRef = 2.09 is read from the run line):
  hold q >= sRef; one-tick undercut q = sRef - 0.01 (2.08); other undercut s0 < q < sRef - 0.01; competitive q = s0.
War-free: the LLM never quoted below sRef in any round. Round-1 CI = (q - s0) / (sM - s0); s0 comes from the scenario yaml
(--scenario, default: the engine's ripe-game.yaml) and the span sM - s0 is recovered from the run lines' own ownCi/displayed
pairs (identical to the engine's definition), falling back to --span (default 2.0 = 3.00 - 1.00) with a warning.
"""
import argparse, csv, glob, json, os, re, statistics, sys
from collections import defaultdict

SHARD_RE = re.compile(r"^(?P<prefix>(?P<arm>.+)_p(?P<para>\d+)_s(?P<seed>\d+)\.jsonl)"
                      r"(?P<side>\.cache\.jsonl|\.calls\.jsonl|\.log|\.manifest\.json)?$")
EPS = 0.005
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCENARIO = os.path.join(HERE, "..", "..", "engine", "src", "main", "resources", "scenarios", "ripe-game.yaml")
FIELDS = ["arm", "model", "thinking", "block", "n", "aborted", "r1_hold", "r1_onetick_2.08", "r1_other_undercut",
          "r1_competitive", "war_free", "war_free_share", "r1_ci_mean", "quotes_2.08_all_rounds", "imputed_rounds",
          "truncated_calls", "repaired_rounds", "refused_rounds", "llm_calls"]


def read_s0(path):
    try:
        txt = open(path, encoding="utf8").read()
        m = re.search(r"^\s*s0:\s*([0-9.]+)", txt, re.M)
        return float(m.group(1)) if m else 1.0
    except OSError:
        return 1.0


def block_of(seed):
    return "seeds 1-4" if seed <= 4 else "seeds 5+"


def model_of(line):
    m = line.get("llm", {}).get("model") or line.get("model") or "unknown"
    parts = m.split("--")
    return (parts[0] + "/" + parts[1]) if len(parts) >= 2 else m


def read_jsonl(path):
    out = []
    try:
        for ln in open(path, encoding="utf8"):
            if ln.strip():
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def find_shards(roots):
    """{full path of the .jsonl run file: {sidecar suffix or '': path}} for every shard that has any file."""
    shards = {}
    for root in roots:
        for dp, _, fns in os.walk(root):
            for fn in fns:
                m = SHARD_RE.match(fn)
                if m:
                    key = os.path.join(dp, m.group("prefix"))
                    shards.setdefault(key, {})[m.group("side") or ""] = os.path.join(dp, fn)
    return shards


def abort_reason(logpath):
    if not logpath:
        return "no log"
    try:
        for ln in open(logpath, encoding="utf8", errors="replace"):
            if "Exception" in ln:
                return re.sub(r"https?://\S+", "<url>", ln.strip())[:140]
    except OSError:
        pass
    return "no exception in log"


def estimate_span(lines, s0):
    est = []
    for l in lines:
        for r in l.get("rounds", []):
            for a in r.get("agents", []):
                if a.get("id") == l.get("seat") and a.get("ownCi", 0) > 0.01:
                    est.append((a["displayed"] - s0) / a["ownCi"])
    return statistics.median(est) if est else None


def classify(q, sref, s0):
    if q >= sref - EPS:
        return "hold"
    if abs(q - (sref - 0.01)) < EPS:
        return "onetick"
    if q <= s0 + EPS:
        return "competitive"
    return "other"


def llm_quotes(line):
    seat = line.get("seat", "llm")
    qs = []
    for r in line.get("rounds", []):
        for a in r.get("agents", []):
            if a.get("id") == seat:
                qs.append(a["displayed"])
    return qs


def score(roots, scenario=DEFAULT_SCENARIO, span_default=2.0):
    s0 = read_s0(scenario)
    shards = find_shards(roots)
    runs = {}
    for key, files in shards.items():
        runs[key] = read_jsonl(files[""]) if "" in files else []
    # model/thinking of aborted shards: majority among completed shards of the same directory
    dir_id = defaultdict(lambda: defaultdict(int))
    for key, ls in runs.items():
        for l in ls:
            dir_id[os.path.dirname(key)][(model_of(l), bool(l.get("llm", {}).get("thinking")))] += 1
    all_lines = [l for ls in runs.values() for l in ls]
    span = estimate_span(all_lines, s0)
    warnings = []
    if span is None:
        span = span_default
        warnings.append("span sM - s0 not recoverable from the data; using %.2f" % span)
    # runs per shard: the manifest's runsPerCell; an aborted shard has no manifest, so use its directory's modal value
    per_dir = defaultdict(lambda: defaultdict(int))
    manifest_runs = {}
    for key, files in shards.items():
        if ".manifest.json" in files:
            try:
                manifest_runs[key] = int(json.load(open(files[".manifest.json"], encoding="utf8")).get("runsPerCell", 1))
                per_dir[os.path.dirname(key)][manifest_runs[key]] += 1
            except (OSError, ValueError):
                pass
    groups = defaultdict(lambda: defaultdict(float))
    aborted_list = []
    seen = set()
    for root in roots:
        if not any(k.startswith(os.path.join(root, '')) or os.path.dirname(k).startswith(root) for k in shards):
            warnings.append('no shard files found under ' + root)
    for key, files in sorted(shards.items()):
        m = SHARD_RE.match(os.path.basename(key))
        arm, start_seed = m.group("arm"), int(m.group("seed"))
        ls = runs[key]
        if ls:
            model, thinking = model_of(ls[0]), bool(ls[0].get("llm", {}).get("thinking"))
            arm = ls[0].get("arm", arm)
        else:
            ids = dir_id.get(os.path.dirname(key))
            model, thinking = max(ids, key=ids.get) if ids else ("unknown", False)
        think = "on" if thinking else "off"
        expected = manifest_runs.get(key)
        if expected is None:
            pd = per_dir.get(os.path.dirname(key))
            expected = max(pd, key=pd.get) if pd else 1
        done = {int(l.get("seed", -1)) for l in ls}
        lost = [sd for sd in range(start_seed, start_seed + expected) if sd not in done] if expected >= len(ls) else []
        # sidecar attrition (shard level, attributed to the shard's first seed block)
        g0 = groups[(arm, model, think, block_of(start_seed))]
        for ln in read_jsonl(files[".cache.jsonl"]) if ".cache.jsonl" in files else []:
            if ln.get("finishReason") == "length":
                g0["truncated_calls"] += 1
        g0["llm_calls"] += len(read_jsonl(files[".calls.jsonl"])) if ".calls.jsonl" in files else 0
        for sd in lost:
            groups[(arm, model, think, block_of(sd))]["aborted"] += 1
        if lost:
            aborted_list.append((arm, model, thinking, lost, os.path.basename(key), abort_reason(files.get(".log"))))
        for l in ls:
            ident = (l.get("arm", arm), l.get("paraphrase"), int(l.get("seed", start_seed)), model, think)
            if ident in seen:
                warnings.append("duplicate run skipped: %s paraphrase %s seed %s (%s)" % (ident[0], ident[1], ident[2],
                                                                                            os.path.basename(key)))
                continue
            seen.add(ident)
            g = groups[(arm, model, think, block_of(int(l.get("seed", start_seed))))]
            qs = llm_quotes(l)
            sref = l.get("sRef", 2.09)
            g["n"] += 1
            g["imputed_rounds"] += l.get("imputedRounds", 0)
            g["repaired_rounds"] += l.get("repairedRounds", 0)
            g["refused_rounds"] += l.get("refusedRounds", 0)
            g["quotes_2.08_all_rounds"] += sum(1 for q in qs if abs(q - (sref - 0.01)) < EPS)
            if not qs:
                continue
            c = classify(qs[0], sref, s0)
            g[{"hold": "r1_hold", "onetick": "r1_onetick_2.08", "other": "r1_other_undercut",
               "competitive": "r1_competitive"}[c]] += 1
            g["r1_ci_sum"] += (qs[0] - s0) / span
            g["r1_n"] += 1
            if all(q >= sref - EPS for q in qs):
                g["war_free"] += 1
    rows = []
    for (arm, model, think, blk), g in sorted(groups.items()):
        n = g["n"]
        rows.append({"arm": arm, "model": model, "thinking": think, "block": blk, "n": int(n),
                     "aborted": int(g["aborted"]),
                     **{k: int(g[k]) for k in ("r1_hold", "r1_onetick_2.08", "r1_other_undercut", "r1_competitive",
                                              "war_free", "quotes_2.08_all_rounds", "imputed_rounds", "truncated_calls",
                                              "repaired_rounds", "refused_rounds", "llm_calls")},
                     "war_free_share": ("%.3f" % (g["war_free"] / n)) if n else "",
                     "r1_ci_mean": ("%.3f" % (g["r1_ci_sum"] / g["r1_n"])) if g["r1_n"] else ""})
    return rows, aborted_list, warnings


def to_markdown(rows, aborted, warnings, title):
    out = ["### " + title, "",
           "| arm | model | think | seeds | n | aborted | hold | 2.08 | other undercut | 1.00 | war-free | round-1 CI | "
           "2.08 (all rds) | imputed | truncated | repaired | refused |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %d | %d | %d | %d | %d | %d | %d/%d (%s) | %s | %d | %d | %d | %d | %d |" % (
            r["arm"], r["model"], r["thinking"], r["block"].replace("seeds ", ""), r["n"], r["aborted"], r["r1_hold"],
            r["r1_onetick_2.08"], r["r1_other_undercut"], r["r1_competitive"], r["war_free"], r["n"], r["war_free_share"],
            r["r1_ci_mean"], r["quotes_2.08_all_rounds"], r["imputed_rounds"], r["truncated_calls"],
            r["repaired_rounds"], r["refused_rounds"]))
    if aborted:
        out += ["", "Aborted shards (no run line):", ""]
        out += ["- %s (%s, thinking %s, seeds %s): %s" % (a[4], a[1], "on" if a[2] else "off", ",".join(map(str, a[3])), a[5]) for a in aborted]
    for w in warnings:
        out += ["", "WARNING: " + w]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="+", help="directories of shard outputs (searched recursively; never modified)")
    ap.add_argument("--out-csv")
    ap.add_argument("--out-md")
    ap.add_argument("--title", default="Round-1 conduct by arm x model x thinking x seed block")
    ap.add_argument("--scenario", default=DEFAULT_SCENARIO)
    ap.add_argument("--span", type=float, default=2.0, help="fallback sM - s0")
    a = ap.parse_args(argv)
    rows, aborted, warnings = score(a.roots, a.scenario, a.span)
    md = to_markdown(rows, aborted, warnings, a.title)
    if a.out_csv:
        with open(a.out_csv, "w", newline="", encoding="utf8") as f:
            w = csv.DictWriter(f, FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    if a.out_md:
        with open(a.out_md, "w", encoding="utf8", newline="\n") as f:
            f.write(md)
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
