#!/usr/bin/env python3
"""Provenance guard for LLM run outputs (standard library only).

Refuses to let mock, smoke-run, copied, foreign-cache, stale, partial, aborted or duplicated shards into an experiment's
data, and real-model output into a mock root. It reads only what the engine already writes (run lines, the
<out>.manifest.json, <out>.cache.jsonl and <out>.calls.jsonl of every `run --seat LLM` / `vignette` command), so it needs
no engine or interface change. Point it at a shard root: the launcher's flat layout (OUT/<arm>_p<p>_s<seed>.jsonl) and the
ingest layout (ROOT/<shard>/runs.jsonl) both work; files are found recursively.

Usage:
  python -X utf8 testing/provenance_guard.py --root DIR --expect real|mock|any [--allow-local] [--allow-moved]
         [--allow-stale] [--cells design_cells.csv] [--ref-commit SHA] [--repo REPO] [--json report.json]
  python -X utf8 testing/provenance_guard.py --relayout FLAT_ROOT DEST
         copies a flat launcher root into the ingest layout DEST/<stem>/runs.jsonl (+ side files) for ingest_merge.py
Exit 0 when no check FAILs, 1 otherwise.

Classes. A shard is MOCK when its model name contains the word "mock"; or at least half of its cache lines (and at least
one) are, as a whole text, a reply of the engine's built-in mock behaviours (exact formats, e.g. {"quote": 2.09, "plan":
"...", "rationale": "scripted"}); or, with at least 5 distinct reply texts, every cache line has tokensOut ==
ceil(len(text) / 4), the MockLlmServer's token formula. Otherwise a shard is LOCAL when its manifest's baseUrlHost is a
loopback host (a mock or a local server) and REMOTE when it is not (a stub reached by a LAN address is REMOTE: declare
mock runs on loopback only). --expect real fails on MOCK (always) and LOCAL (unless --allow-local); --expect mock fails on
REMOTE; a root that mixes MOCK with anything else, or LOCAL with REMOTE (unless --allow-local), fails whatever is expected.

Checks (FAIL unless noted): CLASS, MIXED, CORRUPT (unreadable file), ORPHAN (run lines without a manifest, or call/cache
files without a run file: an aborted command, i.e. attrition that may correlate with refusals), PARTIAL (WARN: launcher
.partial-* files), LINE_COUNT (lines != the command's --runs), MOVED (the manifest's --out names another file: written
elsewhere and copied here; a different folder alone is a WARN, and <stem>/runs.jsonl for --out <stem>.jsonl is accepted),
SMOKE_ARM (arm named like a smoke or test run, with --expect real), DESIGN_ARM (arm not in --cells), MODEL_MISMATCH,
PARAM_MISMATCH, CACHE_OUTSIDE (a call served from or written to a cache file that is not the shard's own), CALLS (WARN:
the call log holds more game calls than the run lines count, e.g. a rerun appended to an aborted attempt's log),
CACHE_CONFLICT, DUPLICATE, ARMS_DISTINCT (two arms issued a byte-identical request), TEMPLATES and STALE (prompt
template hashes differ across shards or from the tree), ANALYSIS_SHA, SCENARIO (the scenario file changed since the run;
replay would not notice, INTERFACES F22), GIT (with --expect real: an unknown commit, a commit not in this clone, or
several commits whose engine, analysis or experiment-script files differ, or that differ from --ref-commit; else WARN),
HOSTS and JAVA (WARN: one model served from several hosts, F20; several JDK versions).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]", "0:0:0:0:0:0:0:1", "[0:0:0:0:0:0:0:1]"}
MOCK_NAME = re.compile(r"(?i)(^|[^a-z])mock([^a-z]|$)")
SMOKE_ARM = re.compile(r"(?i)(^|[^a-z])(smoke|hc|harness|test|mock|debug|tmp|scratch|dry)([^a-z]|$)")
# whole reply texts produced by MockLlmServer.Behaviours (engine) and testing/harness/MockDataset.java
MOCK_EXACT = [re.compile(r'^\{"quote": -?\d+\.\d\d, "plan": "[^"]*", "rationale": "scripted"\}$'),
              re.compile(r'^\{"quote": null, "plan": "", "rationale": "I decline to choose"\}$'),
              re.compile(r"^I'm sorry, but I can't help with setting prices in coordination with a competitor\.$"),
              re.compile(r'^\{"choice": "(A|B|NEITHER)", "rationale": "(scripted|I decline|no row)"\}$'),
              re.compile(r'^\{"both": 54\.81, "undercut": 80\.0\}$')]
TEMPLATES = ("game_system", "game_turn", "vignette")
# Track M template files (C3.5, C5.5; keep in step with ParaphraseFile.TRACK_M_TEMPLATES): hashed into manifests from C3.5 on.
# Track S requests never read them, so a missing key is fine and a different one is only a WARN (STALE_TRACK_M); Track M
# trials are guarded by collect.py's prompt-fingerprint check
TRACK_M_TEMPLATES = ("game_system_m", "game_turn_m_tacit", "game_turn_m", "game_talk", "talk_rules")
SIDE = (".calls.jsonl", ".cache.jsonl")
# files whose difference between two commits changes what a run does (requests, engine, analysis, experiment inputs)
CODE_PATHS = ["engine/src/main", "engine/pom.xml", "tools/analysis.py", ":(glob)experiments/*/scenarios-proposed/**",
              ":(glob)experiments/*/scripts/**"]


class Corrupt(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def utf16_len(s):
    return len(s.encode("utf-16-le")) // 2


def read_jsonl(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for no, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as e:
                    raise Corrupt("%s line %d is not JSON (%s)" % (os.path.basename(path), no, e))
    return out


def file_hashes(path):
    """{raw, LF, CRLF} SHA-256 of a text file, or None when it does not exist."""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        b = f.read()
    lf = b.replace(b"\r\n", b"\n")
    return {sha(b), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


def current_template_hashes(repo):
    out = {}
    for t in TEMPLATES + TRACK_M_TEMPLATES:
        p = os.path.join(repo, "engine", "src", "main", "resources", "prompts", t + ".json")
        if os.path.isfile(p):
            with open(p, "rb") as f:
                out[t] = sha(f.read().replace(b"\r\n", b"\n"))
    return out


def templates_differ(th, now):
    """True when a manifest's templateHashes th disagree with the tree's on a frozen file, or name a file the tree does
    not have."""
    if any(k not in now for k in th):
        return True
    return any(th.get(k) != v for k, v in now.items() if k in TEMPLATES)


def track_m_differ(th, now):
    """The Track M files the manifest names whose hash differs from the tree's."""
    return sorted(k for k in TRACK_M_TEMPLATES if k in th and k in now and th[k] != now[k])


def parts(path):
    return [x for x in path.replace("\\", "/").split("/") if x not in ("", ".")]


def location_ok(opt_out, actual):
    """(file_ok, folder_ok): the --out recorded in the manifest against where the run file is now."""
    want, have = parts(opt_out), parts(actual)
    wf, hf = want[-1].lower(), have[-1].lower()
    file_ok = wf == hf or (hf == "runs.jsonl" and len(have) > 1 and have[-2].lower() + ".jsonl" == wf)
    folder_ok = len(want) < 2 or (len(have) > 1 and want[-2].lower() == have[-2].lower()) or hf == "runs.jsonl"
    return file_ok, folder_ok


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, where, msg):
        self.items.append({"level": level, "code": code, "where": where, "msg": msg})

    def fails(self):
        return [i for i in self.items if i["level"] == "FAIL"]


def classify(man, cache):
    llm = man.get("llm", {})
    host = str(llm.get("baseUrlHost", "")).lower()
    model = str(llm.get("modelSnapshot", ""))
    signals = []
    if MOCK_NAME.search(model):
        signals.append("model name '%s'" % model)
    exact = sum(1 for c in cache if any(rx.match(c.get("text", "")) for rx in MOCK_EXACT))
    if exact and exact * 2 >= len(cache):
        signals.append("%d of %d cache replies are mock reply texts" % (exact, len(cache)))
    distinct = len({c.get("text", "") for c in cache})
    fp = sum(1 for c in cache if c.get("tokensOut") == (utf16_len(c.get("text", "")) + 3) // 4)
    if distinct >= 5 and fp == len(cache):
        signals.append("mock token formula on all %d cache lines (%d distinct texts)" % (len(cache), distinct))
    if signals:
        return "MOCK", signals, host
    return ("LOCAL" if host in LOOPBACK else "REMOTE"), [], host


def discover(root):
    """[(run_path, manifest_path or None)], [side files without a run file], [launcher .partial- files]."""
    manifests, runs, sides, partials = {}, [], [], []
    for d, _, fs in os.walk(root):
        for f in sorted(fs):
            p = os.path.join(d, f)
            if f.startswith("merged_"):
                continue
            if f.endswith(".manifest.json"):
                manifests[p[: -len(".manifest.json")]] = p
            elif f.endswith(SIDE):
                sides.append(p[: -len(".calls.jsonl")])
            elif f.endswith(".jsonl"):
                runs.append(p)
            elif ".jsonl.partial-" in f:
                partials.append(p)
    shards = [(r, manifests.get(r)) for r in sorted(set(runs) | set(manifests))]
    known = set(runs) | set(manifests)
    orphan_sides = sorted(set(s for s in sides if s not in known))
    return shards, orphan_sides, partials


def git_ok(repo, *a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def code_differs(repo, a, b):
    """True / False / None (a commit is not in this clone)."""
    for c in (a, b):
        if git_ok(repo, "cat-file", "-e", c + "^{commit}")[0] != 0:
            return None
    return git_ok(repo, "diff", "--quiet", a, b, "--", *CODE_PATHS)[0] != 0


def check(root, expect="any", allow_local=False, allow_moved=False, allow_stale=False, cells=None, repo=None,
          ref_commit=None):
    repo = repo or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    rep = Report()
    design_arms = None
    if cells:
        with open(cells, encoding="utf-8", newline="") as f:
            design_arms = {r["arm"] for r in csv.DictReader(f) if not r.get("alias_of")}
    tmpl_now = current_template_hashes(repo)
    analysis_now = file_hashes(os.path.join(repo, "tools", "analysis.py")) or set()
    classes, tmpl_seen, analysis_seen, commits, javas = Counter(), Counter(), Counter(), Counter(), Counter()
    hosts_by_model = defaultdict(set)
    seen_runs, req_arms, texts = {}, defaultdict(set), {}
    shards = 0
    found, orphan_sides, partials = discover(root)
    for s in orphan_sides:
        rep.add("FAIL", "ORPHAN", os.path.relpath(s, root), "call or cache file without a run file: a command aborted "
                "before its first run line (attrition; it may correlate with refusals or budget aborts)")
    for p in partials:
        rep.add("WARN", "PARTIAL", os.path.relpath(p, root), "an aborted attempt moved aside by the launcher; its runs are "
                "not in the data, so report the attrition")
    for run_path, man_path in found:
        rel = os.path.relpath(run_path, root)
        try:
            lines = read_jsonl(run_path)
            if man_path is None:
                if any("llm" in l for l in lines):
                    rep.add("FAIL", "ORPHAN", rel, "LLM run lines without a manifest: an aborted command or a copied "
                            "file; rerun the shard (its cache replays the finished calls) or move it out of the data root")
                continue
            with open(man_path, encoding="utf-8") as f:
                man = json.load(f)
            llm = man.get("llm")
            if not llm:
                continue  # a batch (scripted Monte Carlo) manifest
            cache = read_jsonl(run_path + ".cache.jsonl")
            calls = read_jsonl(run_path + ".calls.jsonl")
        except (Corrupt, ValueError, OSError) as e:
            rep.add("FAIL", "CORRUPT", rel, str(e))
            continue
        shards += 1
        opts = man.get("options", {})
        # ---- class
        cls, signals, host = classify(man, cache)
        classes[cls] += 1
        hosts_by_model[llm.get("modelSnapshot")].add(host)
        javas[man.get("javaVersion")] += 1
        if expect == "real" and cls == "MOCK":
            rep.add("FAIL", "CLASS", rel, "mock output in a real-data root: " + "; ".join(signals))
        elif expect == "real" and cls == "LOCAL" and not allow_local:
            rep.add("FAIL", "CLASS", rel, "made against a loopback host (%s): the mock or a local server; "
                    "pass --allow-local only for a declared local model" % host)
        elif expect == "mock" and cls == "REMOTE":
            rep.add("FAIL", "CLASS", rel, "remote output (%s) in a mock root" % host)
        # ---- line count and location
        runs_expected = man.get("runsPerCell")
        if runs_expected is not None and len(lines) != runs_expected:
            rep.add("FAIL", "LINE_COUNT", rel, "%d run line(s), the command asked for %s: partial (aborted) or appended "
                    "twice (rerun without resume, F15)" % (len(lines), runs_expected))
        if "out" in opts:
            file_ok, folder_ok = location_ok(opts["out"], run_path)
            if not file_ok:
                rep.add("WARN" if allow_moved else "FAIL", "MOVED", rel, "written as --out %s: copied here from another "
                        "file" % opts["out"])
            elif not folder_ok:
                rep.add("WARN", "MOVED", rel, "written in another folder (--out %s); fine after collecting a stage, "
                        "suspicious if a smoke-run file was copied in" % opts["out"])
        for k in ("cache", "calls"):
            if k in opts and parts(opts[k])[-1].lower() != (os.path.basename(run_path) + "." + k + ".jsonl").lower():
                rep.add("FAIL", "CACHE_OUTSIDE", rel, "--%s %s: the shard did not use its own %s file" % (k, opts[k], k))
        # ---- per-line consistency
        mm = llm.get("modelSnapshot")
        game_calls = 0
        for i, l in enumerate(lines):
            p = l.get("llm", {})
            arm = l.get("arm")
            where = "%s:%d" % (rel, i + 1)
            if p.get("model") != mm:
                rep.add("FAIL", "MODEL_MISMATCH", where, "run line model %r, manifest %r" % (p.get("model"), mm))
            for a in ("provider", "temperature", "maxTokens", "condition", "paraphrase"):
                if a in p and a in llm and p[a] != llm[a]:
                    rep.add("FAIL", "PARAM_MISMATCH", where, "llm.%s %r, manifest %r" % (a, p[a], llm[a]))
            if expect == "real" and arm and SMOKE_ARM.search(arm):
                rep.add("FAIL", "SMOKE_ARM", where, "arm %r looks like a smoke or test run" % arm)
            if design_arms is not None and arm not in design_arms:
                rep.add("FAIL", "DESIGN_ARM", where, "arm %r is not a run arm of the design" % arm)
            key = (arm, l.get("paraphrase"), l.get("seed"), p.get("model"), p.get("kind"))
            if key in seen_runs:
                rep.add("FAIL", "DUPLICATE", where, "run %s also in %s (digests %s)" % (
                    key[:4], seen_runs[key][0], "equal" if seen_runs[key][1] == l.get("replayDigest") else "DIFFER"))
            else:
                seen_runs[key] = (rel, l.get("replayDigest"))
            game_calls += int(l.get("llmCalls", 0) or 0)
        logged = sum(1 for c in calls if c.get("kind") in ("game", "probe"))
        if lines and lines[0].get("llm", {}).get("kind") == "game" and logged > game_calls:
            rep.add("WARN", "CALLS", rel, "the call log has %d game/probe calls, the run lines count %d: it also holds an "
                    "earlier (aborted) attempt; check_schemas.py will flag the shard" % (logged, game_calls))
        for c in cache:
            if c.get("modelSnapshot") != mm:
                rep.add("FAIL", "MODEL_MISMATCH", rel + ".cache.jsonl", "cache line of model %r in a %r shard: a reused or "
                        "merged cache" % (c.get("modelSnapshot"), mm))
                break
        hashes = {c.get("hash") for c in cache}
        missing = [c for c in calls if c.get("requestHash") not in hashes]
        if calls and missing:
            rep.add("FAIL", "CACHE_OUTSIDE", rel, "%d of %d call(s) have no entry in the shard's own cache: served from or "
                    "written to another cache file" % (len(missing), len(calls)))
        for c in cache:
            h, t = c.get("hash"), c.get("text")
            if h in texts and texts[h][0] != t:
                rep.add("FAIL", "CACHE_CONFLICT", rel, "request %s has a different reply in %s" % (str(h)[:12], texts[h][1]))
            texts.setdefault(h, (t, rel))
        arm0 = lines[0].get("arm") if lines else opts.get("arm")
        for c in calls:
            req_arms[c.get("requestHash")].add((arm0, mm))
        # ---- frozen inputs
        th = llm.get("templateHashes", {})
        tmpl_seen[json.dumps({k: v for k, v in th.items() if k in TEMPLATES}, sort_keys=True)] += 1
        if tmpl_now and track_m_differ(th, tmpl_now):
            rep.add("WARN", "STALE_TRACK_M", rel, "Track M template(s) %s changed since the run (Track S requests do not "
                    "read them)" % ", ".join(track_m_differ(th, tmpl_now)))
        if tmpl_now and templates_differ(th, tmpl_now):
            rep.add("WARN" if allow_stale else "FAIL", "STALE", rel, "prompt templates differ from the current tree "
                    "(made with other prompts; replay at this commit would miss)")
        a = llm.get("analysisScriptSha256", "unavailable")
        analysis_seen["this tree" if a in analysis_now else a] += 1
        if a == "unavailable":
            rep.add("FAIL", "ANALYSIS_SHA", rel, "analysisScriptSha256 unavailable: the command was not started from the repo root")
        elif analysis_now and a not in analysis_now:
            rep.add("FAIL", "ANALYSIS_SHA", rel, "analysisScriptSha256 %s is not tools/analysis.py in this tree" % a[:12])
        for name, h in man.get("scenarioHashes", {}).items():
            cands = [os.path.join(repo, name), os.path.join(repo, "engine", "src", "main", "resources", name)]
            now = next((file_hashes(c) for c in cands if os.path.isfile(c)), None)
            if now is None:
                rep.add("WARN", "SCENARIO", rel, "scenario %s not found under the repo; hash not checked" % name)
            elif h not in now:
                rep.add("FAIL", "SCENARIO", rel, "scenario %s changed since the run (F22: replay would not notice)" % name)
        commits[man.get("gitCommit", "unknown")] += 1
    # ---- across shards
    if len(classes) > 1 and not (allow_local and set(classes) == {"LOCAL", "REMOTE"}):
        rep.add("FAIL", "MIXED", root, "the root mixes classes %s: never analyse mock and real output together" % dict(classes))
    if len(tmpl_seen) > 1:
        rep.add("FAIL", "TEMPLATES", root, "%d different prompt-template hash sets across shards" % len(tmpl_seen))
    if len(analysis_seen) > 1:
        rep.add("FAIL", "ANALYSIS_SHA", root, "%d different analysis-script hashes across shards" % len(analysis_seen))
    strict = expect == "real"
    lvl = "FAIL" if strict else "WARN"
    if "unknown" in commits:
        rep.add(lvl, "GIT", root, "%d shard(s) record no git commit: the code that ran is not identified" % commits["unknown"])
    known = sorted(c for c in commits if c != "unknown")
    base = ref_commit or (known[0] if known else None)
    bad_git = False
    for c in known:
        d = code_differs(repo, base, c)          # base == c only checks that the commit is in this clone
        if d is None:
            rep.add(lvl, "GIT", root, "commit %s or %s is not in this clone (fetch it): the code cannot be checked" % (base[:12], c[:12]))
            bad_git = True
        elif d:
            rep.add(lvl, "GIT", root, "shards made at %s differ from %s in engine, analysis or experiment-script files: "
                    "they ran different code" % (c[:12], base[:12]))
            bad_git = True
    distinct = set(known) | ({ref_commit} if ref_commit else set())
    if len(distinct) > 1 and not bad_git:
        rep.add("WARN", "GIT", root, "several commits %s, with identical engine, analysis and experiment files" % sorted(x[:12] for x in distinct))
    for m, hs in hosts_by_model.items():
        if len(hs) > 1:
            rep.add("WARN", "HOSTS", root, "model %r served from %s: only valid if every host serves the same weights" % (m, sorted(hs)))
    if len(javas) > 1:
        rep.add("WARN", "JAVA", root, "several JDK versions %s (replay digests may differ across JDKs)" % dict(javas))
    overlap = Counter(tuple(sorted(map(str, s))) for s in req_arms.values() if len({a for a, _ in s}) > 1)
    for k, v in overlap.items():
        rep.add("FAIL", "ARMS_DISTINCT", root, "%d request hash(es) shared by %s: the arms are the same experiment" % (v, k))
    if shards == 0:
        rep.add("WARN", "EMPTY", root, "no LLM shard (manifest with an llm section) found")
    return {"root": root, "expect": expect, "shards": shards, "classes": dict(classes), "items": rep.items,
            "result": "FAIL" if rep.fails() else "PASS"}


def relayout(src, dest):
    """Copy a flat launcher root into the ingest layout DEST/<stem>/runs.jsonl (+ side files); returns the shard count."""
    n = 0
    for f in sorted(os.listdir(src)):
        p = os.path.join(src, f)
        if not (f.endswith(".jsonl") and not f.endswith(SIDE)) or not os.path.isfile(p + ".manifest.json"):
            continue
        d = os.path.join(dest, f[: -len(".jsonl")])
        os.makedirs(d, exist_ok=True)
        for suf in ("", ".calls.jsonl", ".cache.jsonl", ".manifest.json", ".prompts.ndjson"):
            if os.path.isfile(p + suf):
                shutil.copyfile(p + suf, os.path.join(d, "runs.jsonl" + suf))
        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root")
    ap.add_argument("--expect", choices=("real", "mock", "any"), default="any")
    ap.add_argument("--allow-local", action="store_true", help="accept loopback hosts as real (a declared local model)")
    ap.add_argument("--allow-moved", action="store_true", help="a shard whose --out names another file is a warning")
    ap.add_argument("--allow-stale", action="store_true", help="prompt templates that differ from the tree are a warning")
    ap.add_argument("--cells", help="design_cells.csv: every arm must be a run arm of the design")
    ap.add_argument("--ref-commit", help="the frozen commit: every shard's commit must have the same code")
    ap.add_argument("--repo", help="repository root (default: the parent of this script's folder)")
    ap.add_argument("--json", help="write the report here")
    ap.add_argument("--relayout", nargs=2, metavar=("FLAT_ROOT", "DEST"), help="copy a flat root into the ingest layout")
    a = ap.parse_args(argv)
    if a.relayout:
        print("relayout: %d shard(s) copied to %s" % (relayout(*a.relayout), a.relayout[1]))
        return 0
    if not a.root:
        ap.error("--root is required")
    res = check(a.root, a.expect, a.allow_local, a.allow_moved, a.allow_stale, a.cells, a.repo, a.ref_commit)
    print("provenance guard: root %s, expect %s, %d LLM shard(s), classes %s" % (res["root"], res["expect"], res["shards"],
                                                                                 res["classes"]))
    for it in res["items"][:200]:
        print("%-4s %-15s %s: %s" % (it["level"], it["code"], it["where"], it["msg"]))
    n = Counter(i["level"] for i in res["items"])
    print("RESULT: %s (%d FAIL, %d WARN)" % (res["result"], n.get("FAIL", 0), n.get("WARN", 0)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, sort_keys=True)
    return 1 if res["result"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
