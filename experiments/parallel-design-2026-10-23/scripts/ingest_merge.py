#!/usr/bin/env python3
"""Stage 1 of the post-run pipeline: ingest the shard outputs of a parallel LLM run, validate, merge, de-duplicate and
build the tidy tables plus a QC report.  Standard library only; run with ``python -X utf8``.

Inputs   --shards ROOT       every ROOT/<shard_id>/runs.jsonl (+ .calls.jsonl, .cache.jsonl, .manifest.json)
         --plan plan.tsv     the launcher's shard plan (shard_id -> endpoint, model, behaviour); optional
         --cells design_cells.csv   the design CSV (cell_id, arm, alias_of, condition, factor levels, stage)
         --repo DIR          repo root (docs/interfaces/check_schemas.py, tools/analysis.py, engine jar)
Outputs  OUT/runs.csv (tidy per-run table), OUT/calls.csv (per-call table), OUT/merged_runs.jsonl (de-duplicated run
         lines, the input of tools/analysis.py), OUT/merged_cache.jsonl, OUT/runs_dropped.csv, OUT/cache_conflicts.csv,
         OUT/predeclared_design.json (alias overrides for tools/analysis.py --design), OUT/qc.json, OUT/qc_report.txt,
         OUT/dashboards/*.csv and OUT/dashboards.html.

Reused from the repo (imported, not copied): docs/interfaces/check_schemas.py -> load_schemas, Validator, classify,
check_llm_line, check_calls, read_jsonl; tools/analysis.py -> mean, sd.
"""
import argparse
import csv
import hashlib
import html
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

PARSE_FAIL_MAX = 0.02      # shard flag: PARSE_FAIL share of first attempts
REFUSAL_MAX = 0.30         # arm flag: refusal rate considered implausible for a usable cell
CAP_PATTERNS = ("40 rounds", "round 40", "maxRounds", "forty rounds", "40-round")


def sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def canonical_condition(spec):
    """The engine's Condition.canonical() form of a --condition string (sorted keys, defaults filled)."""
    c = {"elicitation": "SPONTANEOUS", "guardrail": "off", "label": "NEUTRAL", "notice": "off", "stakes": "1"}
    for kv in (spec or "").replace(";", ",").split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            k, v = k.strip().lower(), v.strip()
            c[k] = v.upper() if k in ("elicitation", "label") else ("on" if v.upper() in ("ON", "TRUE", "1") else "off") if k in ("guardrail", "notice") else v
    return ",".join("%s=%s" % (k, c[k]) for k in sorted(c))


def load_cells(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["arm"]: r for r in rows}


def load_plan(path):
    if not path:
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {r["shard_id"]: r for r in csv.DictReader(f, delimiter="\t")}


def discover(root):
    out = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d, "runs.jsonl")
        if os.path.isfile(p):
            out.append((d, p))
    return out


def validate_shard(cs, schemas, runs, calls, cache):
    """Schema + invariant check of one shard with check_schemas.py's own functions (per shard, because its call-log join
    groups by runKey and paired arms share seeds).  Returns a list of problems."""
    probs = []
    v_run = cs.Validator(schemas["run_record"])
    v_call = cs.Validator(schemas["call_record"])
    v_req = cs.Validator(schemas["llm_request"])
    for i, r in enumerate(runs):
        _, ref = cs.classify("runs.jsonl", r)
        target = v_run.resolve(ref) if ref else schemas["run_record"]
        probs += ["run[%d]: %s" % (i, e) for e in v_run.errors(r, target)]
    for i, c in enumerate(calls):
        probs += ["call[%d]: %s" % (i, e) for e in v_call.errors(c, schemas["call_record"])]
    cache_target = v_req.resolve("#/$defs/cacheLine")
    for i, c in enumerate(cache):
        probs += ["cache[%d]: %s" % (i, e) for e in v_req.errors(c, cache_target)]
    if not probs:
        by_run = defaultdict(list)
        for c in calls:
            if c["kind"] in ("game", "probe"):
                by_run[c["runKey"]].append(c)
        for i, r in enumerate(runs):
            if "seat" in r:
                probs += ["run[%d] invariant: %s" % (i, e) for e in cs.check_llm_line(r, by_run)]
        probs += ["calls invariant: %s" % e for e in cs.check_calls(calls)]
    return probs


def replay(java, jar, repo, shard_dir):
    cmd = [java, "-jar", jar, "replay", "--cache", os.path.join(shard_dir, "runs.jsonl.cache.jsonl"), "--run", os.path.join(shard_dir, "runs.jsonl")]
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shards", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--cells", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--replay-sample", type=int, default=3, help="shards replayed from their caches (plus every flagged shard)")
    ap.add_argument("--java", default=os.environ.get("JAVA", "java"))
    ap.add_argument("--predeclared-design", help="the committed alias-override JSON; the generated override must equal it (gate item predeclared_design_matches)")
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(a.repo, "docs", "interfaces"))
    sys.path.insert(0, os.path.join(a.repo, "tools"))
    import check_schemas as cs
    import analysis
    os.makedirs(os.path.join(a.out, "dashboards"), exist_ok=True)
    schemas = cs.load_schemas()
    cells = load_cells(a.cells)
    plan = load_plan(a.plan)
    analysis_sha = sha256_file(os.path.join(a.repo, "tools", "analysis.py"))
    qc = {"shards": {}, "alarms": [], "warnings": [], "checks": {}}

    # ---------------------------------------------------------------- 1. per-shard load, validate, manifest, parse rates
    runs_all, calls_all, cache_lines = [], [], {}
    cache_conflicts = []
    manifests = {}
    for sid, rpath in discover(a.shards):
        d = os.path.dirname(rpath)
        runs = cs.read_jsonl(rpath)
        calls = cs.read_jsonl(rpath + ".calls.jsonl")
        with open(rpath + ".cache.jsonl", encoding="utf-8") as f:
            raw_cache = [l.rstrip("\n") for l in f if l.strip()]
        cache = [json.loads(l) for l in raw_cache]
        with open(rpath + ".manifest.json", encoding="utf-8") as f:
            man = json.load(f)
        manifests[sid] = man
        meta = plan.get(sid, {})
        endpoint = meta.get("endpoint") or (sid.rsplit("__", 1)[-1].split("-dup")[0] if "__" in sid else "unknown")
        probs = validate_shard(cs, schemas, runs, calls, cache)
        first = [c for c in calls if c["attempt"] == 0 and c["kind"] == "game"]
        pf = sum(1 for c in calls if c["parseStatus"] == "PARSE_FAIL")
        rep = sum(1 for c in first if c["parseStatus"] == "REPAIR_NEEDED")
        sh = {"endpoint": endpoint, "runs": len(runs), "calls": len(calls), "cached_calls": sum(1 for c in calls if c["cached"]),
              "parse_fail_rate": pf / len(first) if first else 0.0, "repair_rate": rep / len(first) if first else 0.0,
              "tokens_in": sum(c["tokensIn"] for c in calls), "tokens_out": sum(c["tokensOut"] for c in calls),
              "latency_ms_mean": analysis.mean([c["latencyMs"] for c in calls]) if calls else 0.0,
              "schema_problems": len(probs), "schema_detail": probs[:5], "model_snapshot": man["llm"]["modelSnapshot"],
              "temperature": man["llm"]["temperature"], "condition": man["llm"]["condition"], "paraphrase": man["llm"]["paraphrase"],
              "flags": []}
        if probs:
            sh["flags"].append("SCHEMA")
        if sh["parse_fail_rate"] > PARSE_FAIL_MAX:
            sh["flags"].append("PARSE_FAIL>%.0f%%" % (100 * PARSE_FAIL_MAX))
        arm = runs[0]["arm"] if runs else meta.get("arm")
        cell = cells.get(arm)
        if cell:
            if canonical_condition(cell["condition"]) != man["llm"]["condition"]:
                sh["flags"].append("CONDITION!=DESIGN")
            if abs(float(cell["temperature"]) - float(man["llm"]["temperature"])) > 1e-9:
                sh["flags"].append("TEMPERATURE!=DESIGN")
            if man["llm"]["modelSnapshot"] not in cell["models"].split(";"):
                sh["flags"].append("MODEL!=DESIGN")
        else:
            sh["flags"].append("ARM-NOT-IN-DESIGN")
        if man["llm"]["analysisScriptSha256"] != analysis_sha:
            sh["flags"].append("ANALYSIS-SHA")
        qc["shards"][sid] = sh
        # cache merge: first line per hash wins; a later line that is not byte-identical is a conflict
        for raw, c in zip(raw_cache, cache):
            prev = cache_lines.get(c["hash"])
            if prev is None:
                cache_lines[c["hash"]] = (raw, sid)
            elif prev[0] != raw:
                cache_conflicts.append({"hash": c["hash"], "first_shard": prev[1], "conflicting_shard": sid})
        for r in runs:
            r["_shard"], r["_endpoint"], r["_cell"] = sid, endpoint, (cell or {}).get("cell_id", "")
            r["_man"] = man
        runs_all += runs
        for c in calls:
            c["_shard"], c["_endpoint"], c["_model"], c["_arm"] = sid, endpoint, man["llm"]["modelSnapshot"], arm
        calls_all += calls

    # ---------------------------------------------------------------- 2. manifest consistency across shards
    def hset(key):
        return Counter(json.dumps(m["llm"].get(key), sort_keys=True) for m in manifests.values())
    for key in ("templateHashes", "paraphraseItemHashes", "analysisScriptSha256"):
        c = hset(key)
        qc["checks"]["manifest_" + key] = "PASS (1 value)" if len(c) == 1 else "FAIL (%d values)" % len(c)
        if len(c) != 1:
            qc["alarms"].append("manifest %s differs across shards: %s" % (key, [k[:40] for k in c]))
    if any(m["llm"]["analysisScriptSha256"] != analysis_sha for m in manifests.values()):
        qc["alarms"].append("manifest analysisScriptSha256 != sha256(tools/analysis.py) = %s" % analysis_sha[:12])
    qc["checks"]["git_commits"] = sorted(set(m["gitCommit"] for m in manifests.values()))
    snaps = defaultdict(set)
    for m in manifests.values():
        snaps[m["llm"]["modelSnapshot"]].add(m["llm"]["baseUrlHost"])
    qc["checks"]["model_snapshots"] = {k: sorted(v) for k, v in snaps.items()}

    # ---------------------------------------------------------------- 3. de-duplication of run lines
    kept, dropped, seen = [], [], {}
    for r in runs_all:
        key = (r["arm"], r.get("paraphrase"), r["seed"], r["llm"]["model"])
        if key in seen:
            same = seen[key]["replayDigest"] == r["replayDigest"]
            dropped.append({"arm": key[0], "paraphrase": key[1], "seed": key[2], "model": key[3], "shard": r["_shard"],
                            "kept_shard": seen[key]["_shard"], "digest_equal": same})
            if not same:
                qc["alarms"].append("digest conflict for %s between %s and %s" % (key, seen[key]["_shard"], r["_shard"]))
            continue
        seen[key] = r
        kept.append(r)
    qc["checks"]["runs_total"], qc["checks"]["runs_kept"], qc["checks"]["runs_dropped_duplicates"] = len(runs_all), len(kept), len(dropped)
    qc["checks"]["cache_entries"], qc["checks"]["cache_conflicts"] = len(cache_lines), len(cache_conflicts)
    if cache_conflicts:
        qc["alarms"].append("%d cache hash conflict(s): same request hash, different line (see cache_conflicts.csv)" % len(cache_conflicts))

    # ---------------------------------------------------------------- 4. replay a sample (plus every flagged shard)
    jar = os.path.join(a.repo, "engine", "target", "collusion-engine.jar")
    sids = sorted(qc["shards"])
    sample = set(sids[i] for i in range(0, len(sids), max(1, len(sids) // max(1, a.replay_sample)))[:a.replay_sample])
    sample |= set(s for s in sids if qc["shards"][s]["flags"])
    sample |= set(x["conflicting_shard"] for x in cache_conflicts)
    qc["checks"]["replay"] = {}
    for sid in sorted(sample):
        ok, tail = replay(a.java, jar, a.repo, os.path.join(a.shards, sid))
        qc["checks"]["replay"][sid] = "OK" if ok else "FAIL " + " ".join(tail)
        if not ok:
            qc["alarms"].append("replay failed for shard %s" % sid)
            qc["shards"][sid]["flags"].append("REPLAY")

    # ---------------------------------------------------------------- 5. leakage grep (replies and manifest options)
    hits = []
    for h, (raw, sid) in cache_lines.items():
        txt = json.loads(raw)["text"]
        if any(p.lower() in txt.lower() for p in CAP_PATTERNS):
            hits.append((sid, h[:12]))
    qc["checks"]["cap_leak_hits_in_replies"] = len(hits)
    if hits:
        qc["alarms"].append("the round cap is mentioned in %d reply text(s): %s" % (len(hits), hits[:5]))
    qc["warnings"].append("leakage check covers reply texts only: prompts are not persisted (cache stores hash + reply); "
                          "have the launcher dump one rendered prompt per cell and grep those too")
    # cross-arm request-hash overlap: two arms issuing byte-identical requests are the same experiment (and share cache hits)
    arms_by_hash = defaultdict(set)
    for c in calls_all:
        arms_by_hash[c["requestHash"]].add((c["_arm"], c["_model"]))
    overlap = Counter(tuple(sorted(s)) for s in arms_by_hash.values() if len(s) > 1)
    qc["checks"]["cross_arm_hash_overlap"] = {" vs ".join("%s@%s" % p for p in k): v for k, v in overlap.items()}
    for k, v in overlap.items():
        qc["alarms"].append("%d request hashes shared between arms %s: the arms are not distinct at the request level" % (v, k))

    # ---------------------------------------------------------------- 6. tidy tables
    def fac(r, k):
        return (cells.get(r["arm"]) or {}).get("factor_" + k, "")
    cols = ["run_id", "shard_id", "endpoint", "cell_id", "stage", "arm", "model", "model_snapshot", "temperature", "paraphrase",
            "paraphrase_id", "condition", "f_elicitation", "f_label", "f_guardrail", "f_notice", "f_stakes", "f_temperature",
            "scenario_id", "seed", "status", "rounds", "short_run", "war_onset_round", "stat_rounds", "p_adhere", "mean_ci",
            "p_collude", "gap_ci", "responder", "refuser", "refused_rounds", "imputed_rounds", "repaired_rounds", "off_grid_quotes",
            "llm_calls", "llm_cached_calls", "tokens_in", "tokens_out", "probes", "probes_correct", "replay_digest",
            "template_hashes_sha12", "analysis_sha12", "git_commit"]
    with open(os.path.join(a.out, "runs.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in kept:
            m = r["_man"]
            th = hashlib.sha256(json.dumps(m["llm"]["templateHashes"], sort_keys=True).encode()).hexdigest()[:12]
            w.writerow(["%s|p%s|s%s|%s" % (r["arm"], r.get("paraphrase"), r["seed"], r["llm"]["model"]), r["_shard"], r["_endpoint"], r["_cell"],
                        (cells.get(r["arm"]) or {}).get("stage", ""), r["arm"], r["llm"]["model"], m["llm"]["modelSnapshot"], m["llm"]["temperature"],
                        r.get("paraphrase"), r.get("paraphraseId"), m["llm"]["condition"], fac(r, "elicitation"), fac(r, "label"), fac(r, "guardrail"),
                        fac(r, "notice"), fac(r, "stakes"), fac(r, "temperature"), r["scenarioId"], r["seed"], r["status"], len(r["rounds"]),
                        r.get("shortRun"), r.get("warOnsetRound"), r.get("statRounds"), r.get("pAdhere"), r.get("meanCi"), r.get("pCollude"),
                        r.get("gapCi"), r.get("responder"), r.get("refuser"), r.get("refusedRounds"), r.get("imputedRounds"), r.get("repairedRounds"),
                        r.get("offGridQuotes"), r.get("llmCalls"), r.get("llmCachedCalls"), r.get("tokensIn"), r.get("tokensOut"), r.get("probes"),
                        r.get("probesCorrect"), r["replayDigest"], th, m["llm"]["analysisScriptSha256"][:12], m["gitCommit"][:12]])
    with open(os.path.join(a.out, "calls.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["shard_id", "endpoint", "model", "arm", "kind", "run_key", "index", "attempt", "request_hash", "cached", "tokens_in",
                    "tokens_out", "latency_ms", "parse_status", "reply_chars"])
        for c in calls_all:
            entry = cache_lines.get(c["requestHash"])
            w.writerow([c["_shard"], c["_endpoint"], c["_model"], c["_arm"], c["kind"], c["runKey"], c["index"], c["attempt"], c["requestHash"],
                        c["cached"], c["tokensIn"], c["tokensOut"], c["latencyMs"], c["parseStatus"], len(json.loads(entry[0])["text"]) if entry else ""])
    with open(os.path.join(a.out, "merged_runs.jsonl"), "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, sort_keys=True) + "\n")
    with open(os.path.join(a.out, "merged_cache.jsonl"), "w", encoding="utf-8") as f:
        for h in sorted(cache_lines):
            f.write(cache_lines[h][0] + "\n")
    for name, rows, head in (("runs_dropped.csv", dropped, ["arm", "paraphrase", "seed", "model", "shard", "kept_shard", "digest_equal"]),
                             ("cache_conflicts.csv", cache_conflicts, ["hash", "first_shard", "conflicting_shard"])):
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=head)
            w.writeheader()
            w.writerows(rows)
    # alias overrides for tools/analysis.py --design (an alias arm is the same runs under the design's name)
    over = {}
    for t, spec in analysis.DEFAULT_DESIGN.items():
        s = dict(spec)
        for side in ("a", "b"):
            if s[side] in cells and cells[s[side]]["alias_of"]:
                s[side] = cells[s[side]]["alias_of"]
        if s != spec:
            over[t] = s
    with open(os.path.join(a.out, "predeclared_design.json"), "w", encoding="utf-8") as f:
        json.dump(over, f, indent=1)
    # the override is a pre-declaration artefact: when a committed copy is given, the generated one must equal it exactly
    # (review finding 4: analysis.py --design does dict.update, so any key could otherwise be rewritten at analysis time)
    predeclared_ok = True
    if a.predeclared_design:
        with open(a.predeclared_design, encoding="utf-8") as f:
            committed = json.load(f)
        predeclared_ok = committed == over
        if not predeclared_ok:
            qc["alarms"].append("predeclared_design.json differs from the committed %s" % a.predeclared_design)

    # ---------------------------------------------------------------- 7. balance, refusal picture, dashboards
    bal = defaultdict(Counter)
    ep_arm = defaultdict(Counter)
    for r in kept:
        bal[(r["arm"], r["llm"]["model"])][r.get("paraphrase")] += 1
        ep_arm[r["_endpoint"]][r["arm"]] += 1
    for key, c in bal.items():
        if max(c.values()) - min(c.values()) > 0:
            qc["warnings"].append("paraphrase counts unbalanced for %s: %s" % (key, dict(c)))
    qc["checks"]["runs_per_endpoint"] = {e: sum(c.values()) for e, c in ep_arm.items()}
    refusal = {}
    for key in sorted(bal):
        rs = [r for r in kept if (r["arm"], r["llm"]["model"]) == key]
        refusal["%s|%s" % key] = {"runs": len(rs), "refusal_rate": sum(1 for r in rs if r.get("refuser")) / len(rs),
                                 "imputed_round_rate": sum(r.get("imputedRounds", 0) for r in rs) / max(1, sum(len(r["rounds"]) for r in rs))}
        if refusal["%s|%s" % key]["refusal_rate"] > REFUSAL_MAX:
            qc["warnings"].append("refusal rate %.2f > %.2f for arm %s model %s" % (refusal["%s|%s" % key]["refusal_rate"], REFUSAL_MAX, *key))
    qc["refusal_by_model_arm"] = refusal
    dash = {}
    dash["refusal_by_model_arm.csv"] = (["arm|model", "runs", "refusal_rate", "imputed_round_rate"],
                                        [[k, v["runs"], "%.3f" % v["refusal_rate"], "%.3f" % v["imputed_round_rate"]] for k, v in refusal.items()])
    dash["parse_repair_by_shard.csv"] = (["shard_id", "endpoint", "calls", "cached", "repair_rate", "parse_fail_rate", "flags"],
                                         [[s, v["endpoint"], v["calls"], v["cached_calls"], "%.3f" % v["repair_rate"], "%.3f" % v["parse_fail_rate"], " ".join(v["flags"])]
                                          for s, v in sorted(qc["shards"].items())])
    dash["tokens_latency_by_shard.csv"] = (["shard_id", "endpoint", "model", "runs", "tokens_in", "tokens_out", "latency_ms_mean"],
                                           [[s, v["endpoint"], v["model_snapshot"], v["runs"], v["tokens_in"], v["tokens_out"], "%.1f" % v["latency_ms_mean"]]
                                            for s, v in sorted(qc["shards"].items())])
    lengths = Counter(len(r["rounds"]) for r in kept)
    dash["run_length.csv"] = (["rounds", "runs", "share"], [[k, v, "%.3f" % (v / len(kept))] for k, v in sorted(lengths.items())])
    onset = defaultdict(Counter)
    for r in kept:
        onset[(r["arm"], r["llm"]["model"])][r.get("warOnsetRound")] += 1
    dash["war_onset.csv"] = (["arm|model", "war_onset_round(-1=none)", "runs"],
                             [["%s|%s" % k, o, n] for k, c in sorted(onset.items()) for o, n in sorted(c.items(), key=lambda kv: (kv[0] is None, kv[0]))])
    dash["paraphrase_balance.csv"] = (["arm|model", "paraphrase", "runs"], [["%s|%s" % k, p, n] for k, c in sorted(bal.items()) for p, n in sorted(c.items())])
    for name, (head, rows) in dash.items():
        with open(os.path.join(a.out, "dashboards", name), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(rows)
    parts = ["<html><head><meta charset='utf-8'><title>MOCK QC dashboards</title><style>table{border-collapse:collapse;font:12px monospace}"
             "td,th{border:1px solid #999;padding:2px 6px}</style></head><body><h1>QC dashboards (MOCK data)</h1>"]
    for name, (head, rows) in dash.items():
        parts.append("<h2>%s</h2><table><tr>%s</tr>" % (name, "".join("<th>%s</th>" % html.escape(str(h)) for h in head)))
        parts += ["<tr>%s</tr>" % "".join("<td>%s</td>" % html.escape(str(x)) for x in row) for row in rows]
        parts.append("</table>")
    parts.append("</body></html>")
    with open(os.path.join(a.out, "dashboards.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    # ---------------------------------------------------------------- 8. QC verdict
    flagged = {s: v["flags"] for s, v in qc["shards"].items() if v["flags"]}
    qc["flagged_shards"] = flagged
    qc["gate"] = {"no_cache_conflicts": not cache_conflicts, "no_digest_conflicts": not any("digest conflict" in x for x in qc["alarms"]),
                  "manifests_consistent": all(v.startswith("PASS") for k, v in qc["checks"].items() if k.startswith("manifest_")),
                  "replay_ok": all(v == "OK" for v in qc["checks"]["replay"].values()),
                  "no_cap_leak": not hits, "no_schema_failures": not any("SCHEMA" in f for f in flagged.values()),
                  "arms_distinct": not overlap}
    qc["gate"]["predeclared_design_matches"] = predeclared_ok
    qc["gate"]["all"] = all(qc["gate"].values())
    with open(os.path.join(a.out, "qc.json"), "w", encoding="utf-8") as f:
        json.dump(qc, f, indent=1, sort_keys=True)
    L = ["QC REPORT (MOCK data) - ingest_merge.py", "shards %d  runs %d kept %d dropped-duplicates %d  cache entries %d conflicts %d" % (
        len(qc["shards"]), len(runs_all), len(kept), len(dropped), len(cache_lines), len(cache_conflicts))]
    L += ["check %s: %s" % (k, v) for k, v in sorted(qc["checks"].items()) if not isinstance(v, dict)]
    L += ["replay %s: %s" % (k, v) for k, v in sorted(qc["checks"]["replay"].items())]
    L += ["flagged shard %s: %s" % (s, " ".join(fl)) for s, fl in sorted(flagged.items())]
    L += ["ALARM: " + x for x in qc["alarms"]] + ["warning: " + x for x in qc["warnings"]]
    L.append("GATE: " + ("PASS" if qc["gate"]["all"] else "FAIL ") + json.dumps({k: v for k, v in qc["gate"].items() if not v}))
    with open(os.path.join(a.out, "qc_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if qc["gate"]["all"] else 1


if __name__ == "__main__":
    sys.exit(main())
