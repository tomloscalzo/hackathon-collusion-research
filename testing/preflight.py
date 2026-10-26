#!/usr/bin/env python3
"""Pre-flight go/no-go gate for the LLM experiments (standard library only). Wrapper: scripts/preflight.

Stages (testing/TEST_AND_VALIDATION_PLAN.md section 4 explains every check):
  dev         toolchain, line endings, the JUnit suite, the jar (clean rebuild; its prompts must equal the source), the
              analysis self-test, the schema check, and the mock end-to-end and provenance tests (testing/test_harness.py).
  first-call  dev, plus: JDK 17 required, clean tree (no modified file, no untracked file in code or experiment inputs),
              HEAD on origin/main, commit hooks on, a fresh output root outside the repo (--out-root), and the freeze
              record if given. On GO the jar is copied into the output root: launch the stage with
              --jar <out-root>/collusion-engine.jar, so the stage keeps its own jar and later builds cannot touch it.
  ingest      before any result is read: the provenance guard (--expect real) on --out-root, the freeze record if given
              (checked with the stage's own jar copy when present), the analysis self-test and the line endings. No build.

Freeze record (the prompt half of INTERFACES F24): --write-freeze FILE rebuilds the jar and records the LF SHA-256 of
every frozen input (every engine source file and pom.xml, the prompt templates, scenarios and sweeps, tools/analysis.py,
the experiment design files and proposed scenarios, the dataset generator, and the bands file given with --bands, whose
path is stored), plus two digests of the MOCK freeze set (testing/harness/MockDataset.java --freeze: every game cell of the
design x 12 paraphrases with a probe and a repair, and every vignette condition x 12 paraphrases): the request-hash digest
(every rendered request) and the run digest (engine and parser). --freeze FILE re-computes all of it and fails on any
difference; with --freeze the provenance guard also requires every shard's commit to have the recorded commit's code.

Usage:  scripts/preflight [--stage dev|first-call|ingest] [--out-root DIR] [--cells CSV] [--bands CSV]
                          [--freeze FILE | --write-freeze FILE] [--allow-local] [--allow-moved] [--allow-stale]
                          [--skip-tests]
Exit 0 = GO (no FAIL), 1 = NO-GO.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
ENGINE = os.path.join(REPO, "engine")
JAR = os.path.join(ENGINE, "target", "collusion-engine.jar")
PROMPTS = os.path.join(ENGINE, "src", "main", "resources", "prompts")
FROZEN_GLOBS = ["engine/pom.xml", "engine/src/main/**/*.java", "engine/src/main/resources/**/*.json",
                "engine/src/main/resources/**/*.yaml", "tools/analysis.py",
                "experiments/*/scenarios-proposed/*.yaml", "experiments/*/scripts/*.py", "experiments/*/scripts/*.csv",
                "experiments/*/scripts/*.json", "testing/harness/MockDataset.java"]
CODE_DIR_RX = re.compile(r"^(engine/src/main/|engine/pom\.xml|tools/|testing/harness/|experiments/[^/]+/(scenarios-proposed|scripts)/)")
sys.path.insert(0, HERE)

RESULTS = []
BUILT = {"jar": False}


def say(level, cid, text, detail=""):
    RESULTS.append((level, cid, text, detail))
    print("%-4s  %-4s %s%s" % (level, cid, text, ("  [" + detail + "]") if detail else ""), flush=True)


def sha_lf(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(cmd, cwd=REPO, env=None, timeout=900):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    return r.returncode, r.stdout + r.stderr, time.time() - t0


def java_home():
    for c in (os.environ.get("JAVA_HOME"), "/usr/lib/jvm/java-17-openjdk", "/usr/lib/jvm/java-17-openjdk-amd64"):
        if c and os.path.isdir(c):
            return c
    return None


def java_bin():
    jh = java_home()
    if jh:
        for n in ("java.exe", "java"):
            p = os.path.join(jh, "bin", n)
            if os.path.isfile(p):
                return p
    return shutil.which("java") or "java"


def mvn_bin():
    for c in (os.environ.get("MVN"), shutil.which("mvn.cmd"), shutil.which("mvn")):
        if c and os.path.isfile(c):
            return c
    return None


def env_java():
    e = dict(os.environ)
    jh = java_home()
    if jh:
        e["JAVA_HOME"] = jh
        e["PATH"] = os.path.join(jh, "bin") + os.pathsep + e.get("PATH", "")
    e.pop("COLLUSION_ALLOW_REMOTE", None)   # nothing preflight runs may call a remote host
    return e


# ------------------------------------------------------------------------------------------------------------ checks
def check_toolchain(strict):
    rc, out, _ = run([java_bin(), "-version"])
    m = re.search(r'version "(\d+)', out)
    major = int(m.group(1)) if m else None
    first = (out.splitlines() or ["no java"])[0]
    if major == 17:
        say("PASS", "T1", "JDK 17 (the runtime the replay digests were made with, INTERFACES i.0 item 11)", first)
    else:
        say("FAIL" if (strict or major is None) else "WARN", "T1", "JDK 17 required for runs (Double.toString changed in "
            "JDK 19; digests can differ across JDKs)", first)
    say("PASS" if sys.version_info >= (3, 8) else "FAIL", "T1", "Python >= 3.8", sys.version.split()[0])
    if os.environ.get("COLLUSION_ALLOW_REMOTE") == "1":
        say("INFO", "T1", "COLLUSION_ALLOW_REMOTE=1 is exported: preflight and the tests run without it, the CLI in this "
            "shell will allow remote calls")
    else:
        say("INFO", "T1", "COLLUSION_ALLOW_REMOTE is not set: no remote call is possible from this shell")


def check_line_endings():
    rc, out, _ = run([sys.executable, "-X", "utf8", os.path.join(HERE, "check_line_endings.py")])
    detail = next((l for l in out.splitlines() if l.startswith("info")), "")
    if rc != 0:
        say("FAIL", "T2", "line-ending policy for hashed inputs", out.strip().splitlines()[-2] if out.strip() else "")
    elif "WARN  3" in out:
        say("WARN", "T2", "working copy has CRLF in hashed inputs: manifest hashes from this checkout differ from LF "
            "machines; refresh with: git rm -r -q --cached . && git reset -q --hard HEAD (clean tree only)", detail)
    else:
        say("PASS", "T2", "hashed inputs are LF in the policy, the index and the working copy", detail)


def surefire_counts():
    tot = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for p in glob.glob(os.path.join(ENGINE, "target", "surefire-reports", "TEST-*.xml")):
        with open(p, encoding="utf-8") as fh:
            head = fh.read(4000)
        for key in tot:
            m = re.search(r' %s="(\d+)"' % key, head)
            tot[key] += int(m.group(1)) if m else 0
    return tot


def check_maven():
    mvn = mvn_bin()
    if not mvn:
        say("FAIL", "T3", "Maven not found (set MVN or put mvn on PATH)")
        return
    shutil.rmtree(os.path.join(ENGINE, "target", "surefire-reports"), ignore_errors=True)
    rc, out, dt = run([mvn, "-q", "test"], cwd=ENGINE, env=env_java())
    c = surefire_counts()
    ok = rc == 0 and c["failures"] == c["errors"] == 0 and c["tests"] > 0
    say("PASS" if ok else "FAIL", "T3", "JUnit suite (mvn -q test)", "%d tests, %d failures, %d errors, %d skipped, %.0f s" % (
        c["tests"], c["failures"], c["errors"], c["skipped"], dt))
    if c["skipped"]:
        say("WARN", "T3", "%d JUnit test(s) skipped" % c["skipped"])
    if rc != 0:
        print("\n".join(l for l in out.splitlines() if "FAIL" in l or "ERROR]" in l)[:3000])


def build_jar():
    if BUILT["jar"]:
        return True
    mvn = mvn_bin()
    if not mvn:
        say("FAIL", "T4", "cannot build the jar: Maven not found")
        return False
    rc, out, dt = run([mvn, "-q", "-DskipTests", "clean", "package"], cwd=ENGINE, env=env_java())
    if rc != 0 or not os.path.isfile(JAR):
        say("FAIL", "T4", "jar build (mvn -q -DskipTests clean package); on Windows a jar in use by running shards cannot "
            "be replaced: launch stages from their own jar copy (first-call does this)", out.strip()[-300:])
        return False
    BUILT["jar"] = True
    return True


def check_jar():
    if not build_jar():
        return
    bad = []
    with zipfile.ZipFile(JAR) as z:
        names = {n for n in z.namelist() if n.startswith("prompts/") and n.endswith(".json")}
        src = {"prompts/" + os.path.basename(p): p for p in glob.glob(os.path.join(PROMPTS, "*.json"))}
        if names != set(src):
            bad.append("prompt file sets differ: jar %s, source %s" % (sorted(names), sorted(src)))
        for name, p in src.items():
            with open(p, "rb") as fh:
                if name in names and z.read(name) != fh.read():
                    bad.append(name)
    say("PASS" if not bad else "FAIL", "T4", "jar rebuilt clean from this tree; its prompt files equal the source",
        ("sha256 %s" % sha_file(JAR)[:16]) if not bad else "stale jar: %s" % bad)


def check_selftest():
    rc, out, _ = run([sys.executable, "-X", "utf8", os.path.join(REPO, "tools", "analysis.py"), "--selftest"])
    say("PASS" if rc == 0 and "SELFTEST OK" in out else "FAIL", "T5", "tools/analysis.py --selftest",
        "%d checks" % out.count("PASS  "))


def check_schemas():
    rc, out, _ = run([sys.executable, "-X", "utf8", os.path.join(REPO, "docs", "interfaces", "check_schemas.py")])
    say("PASS" if rc == 0 else "FAIL", "T6", "check_schemas.py: schema keywords, reply schemas == PromptBuilder, examples",
        out.strip().splitlines()[-1] if out.strip() else "")


def check_harness_tests():
    rc, out, dt = run([sys.executable, "-X", "utf8", "-m", "unittest", "testing/test_harness.py"], env=env_java())
    m = re.search(r"Ran (\d+) tests?", out)
    skipped = re.search(r"skipped=(\d+)", out)
    ok = rc == 0 and m and not skipped
    say("PASS" if ok else "FAIL", "T7", "mock end-to-end + provenance-guard tests (testing/test_harness.py)",
        "%s tests, %.0f s%s" % (m.group(1) if m else "?", dt, ", %s skipped" % skipped.group(1) if skipped else ""))
    if not ok:
        print(out[-3000:])


def git(*a, timeout=60):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, env=env, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, ""


def check_git_state():
    rc, out = git("status", "--porcelain", "--untracked-files=all")
    lines = [l for l in out.splitlines() if l]
    tracked = [l for l in lines if not l.startswith("??")]
    untracked = [l[3:].strip().strip('"') for l in lines if l.startswith("??")]
    code_untracked = [u for u in untracked if CODE_DIR_RX.match(u.replace("\\", "/"))]
    say("PASS" if not tracked else "FAIL", "G1", "no modified tracked file (the manifest's gitCommit then names the code "
        "that ran)", ("%d modified: %s" % (len(tracked), tracked[:3])) if tracked else "")
    say("PASS" if not code_untracked else "FAIL", "G1", "no untracked file in engine/src/main, tools, testing/harness or "
        "the experiment scripts and scenarios (it would run without being in the commit)",
        str(code_untracked[:3]) if code_untracked else "")
    other = [u for u in untracked if u not in code_untracked]
    if other:
        say("WARN", "G1", "%d other untracked file(s) in the repo (outputs belong outside it)" % len(other), str(other[:3]))
    frc, _ = git("fetch", "-q", "origin", timeout=30)
    _, head = git("rev-parse", "HEAD")
    rc2, _ = git("merge-base", "--is-ancestor", "HEAD", "origin/main")
    say("PASS" if rc2 == 0 else "WARN", "G2", "HEAD is on origin/main (runs are made from merged, reviewed code)",
        head[:12] + ("" if frc == 0 else "; git fetch failed or timed out, origin/main may be stale"))
    _, hp = git("config", "--get", "core.hooksPath")
    _, terms = git("config", "--get", "hooks.protectedTerms")
    ok = hp == ".githooks" and terms and os.path.isfile(terms)
    say("PASS" if ok else "WARN", "G3", "commit hooks on (needed to commit results)", "hooksPath=%s terms=%s" % (
        hp or "unset", "set" if terms and os.path.isfile(terms) else "missing"))


def inside_repo(path):
    a = os.path.normcase(os.path.abspath(path))
    r = os.path.normcase(REPO)
    return a == r or a.startswith(r + os.sep)


def check_out_root(a, stage, ref_commit):
    root = a.out_root
    if not root:
        say("FAIL" if stage == "ingest" else "WARN", "G4", "--out-root not given: the output root cannot be checked")
        return False
    if inside_repo(root):
        rc = subprocess.run(["git", "-C", REPO, "check-ignore", "-q", os.path.abspath(root)]).returncode
        say("PASS" if rc == 0 else "FAIL", "G4", "output root is outside the repo or git-ignored", root)
    else:
        say("PASS", "G4", "output root is outside the repo", root)
    content = [f for f in os.listdir(root)] if os.path.isdir(root) else []
    if not [f for f in content if f != "collusion-engine.jar"]:
        say("FAIL" if stage == "ingest" else "PASS", "G5", "output root is empty" + (": nothing to ingest" if stage == "ingest"
            else " (no leftover can be skipped as complete by the launcher)"))
        return True
    import provenance_guard as pg
    res = pg.check(root, expect="real", allow_local=a.allow_local, allow_moved=a.allow_moved, allow_stale=a.allow_stale,
                   cells=a.cells, repo=REPO, ref_commit=ref_commit)
    fails = [i for i in res["items"] if i["level"] == "FAIL"]
    warns = [i for i in res["items"] if i["level"] == "WARN"]
    say("FAIL" if fails else ("WARN" if warns else "PASS"), "G5", "provenance guard --expect real on the output root",
        "%d shard(s) %s; %d FAIL, %d WARN" % (res["shards"], res["classes"], len(fails), len(warns)))
    for i in (fails + warns)[:25]:
        print("        %-4s %-14s %s: %s" % (i["level"], i["code"], i["where"], i["msg"][:160]))
    if stage == "first-call" and res["shards"]:
        say("FAIL", "G5", "the output root already holds shards: the launcher skips any shard with the expected line "
            "count, so start each stage in a fresh folder")
    return not fails


def stage_jar(root):
    """Copy the freshly built jar into the stage folder; the stage is launched from this copy."""
    os.makedirs(root, exist_ok=True)
    dst = os.path.join(root, "collusion-engine.jar")
    shutil.copyfile(JAR, dst)
    say("INFO", "J1", "stage jar: launch with --jar %s" % dst, "sha256 %s" % sha_file(dst)[:16])


# ------------------------------------------------------------------------------------------------------------ freeze
def frozen_files():
    files = {}
    for g in FROZEN_GLOBS:
        for p in sorted(glob.glob(os.path.join(REPO, g), recursive=True)):
            files[os.path.relpath(p, REPO).replace(os.sep, "/")] = sha_lf(p)
    return files


def mock_digests(jar):
    tmp = tempfile.mkdtemp(prefix="collusion-freeze-")
    try:
        out = os.path.join(tmp, "stage")
        rc, log, _ = run([java_bin(), "-cp", jar, os.path.join("testing", "harness", "MockDataset.java"), "--freeze", out],
                         env=env_java())
        if rc != 0:
            raise RuntimeError("MockDataset --freeze failed: " + log[-800:])
        req, runs = [], []
        for p in sorted(glob.glob(os.path.join(out, "*.jsonl"))):
            if p.endswith((".calls.jsonl", ".cache.jsonl")):
                continue
            name = os.path.basename(p)
            with open(p + ".calls.jsonl", encoding="utf-8") as f:
                req += ["%s %s" % (name, json.loads(l)["requestHash"]) for l in f if l.strip()]
            with open(p, encoding="utf-8") as f:
                runs += ["%s %s" % (name, json.loads(l)["replayDigest"]) for l in f if l.strip()]
        h = lambda xs: hashlib.sha256("\n".join(xs).encode("utf-8")).hexdigest()
        return {"mockRequestDigest": h(req), "mockRunDigest": h(runs), "mockRequests": len(req), "mockRuns": len(runs)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def rel_or_abs(p):
    return os.path.relpath(p, REPO).replace(os.sep, "/") if inside_repo(p) else os.path.abspath(p)


def write_freeze(path, bands):
    BUILT["jar"] = False
    if not build_jar():
        return
    rec = {"files": frozen_files()}
    if bands:
        rec["bandsPath"] = rel_or_abs(bands)
        rec["bandsSha256"] = sha_lf(bands)
    rec.update(mock_digests(JAR))
    _, head = git("rev-parse", "HEAD")
    rec["recordedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    rec["gitCommitWhenRecorded"] = head
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    say("INFO", "F0", "freeze record written: %d files%s, %d mock requests, %d mock runs" % (
        len(rec["files"]), " + bands" if bands else "", rec["mockRequests"], rec["mockRuns"]), path)


def verify_freeze(path, bands, jar):
    with open(path, encoding="utf-8") as f:
        want = json.load(f)
    have = frozen_files()
    diff = sorted(k for k in set(want["files"]) | set(have) if want["files"].get(k) != have.get(k))
    say("PASS" if not diff else "FAIL", "F1", "frozen input files unchanged since the freeze record",
        ("%d differ: %s" % (len(diff), diff[:5])) if diff else "%d files" % len(want["files"]))
    bp = bands or want.get("bandsPath")
    if want.get("bandsSha256"):
        full = bp if (bp and os.path.isabs(bp)) else os.path.join(REPO, bp or "")
        ok = os.path.isfile(full) and sha_lf(full) == want["bandsSha256"]
        say("PASS" if ok else "FAIL", "F1", "bands file unchanged since the freeze record", bp or "")
    d = mock_digests(jar)
    for k, what in (("mockRequestDigest", "every rendered request of the freeze set (prompt bytes, draw keys, schemas) unchanged"),
                    ("mockRunDigest", "engine and parser behaviour on the freeze set unchanged")):
        say("PASS" if want.get(k) == d[k] else "FAIL", "F2", what, "%s, jar %s" % (d[k][:16], os.path.relpath(jar, REPO)
                                                                                    if inside_repo(jar) else jar))
    return want.get("gitCommitWhenRecorded")


# ------------------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", choices=("dev", "first-call", "ingest"), default="dev")
    ap.add_argument("--out-root", help="the stage's output folder (first-call: fresh and outside the repo; ingest: the shards)")
    ap.add_argument("--cells", help="design_cells.csv: the provenance guard then requires every arm to be a design arm")
    ap.add_argument("--bands", help="the bands CSV (write: recorded in the freeze; verify: overrides the recorded path)")
    ap.add_argument("--freeze", help="verify this freeze record")
    ap.add_argument("--write-freeze", help="write a freeze record here (at the freezing commit) and exit")
    ap.add_argument("--allow-local", action="store_true", help="a declared local model on a loopback host counts as real")
    ap.add_argument("--allow-moved", action="store_true", help="a shard whose --out names another file is a warning")
    ap.add_argument("--allow-stale", action="store_true", help="prompt templates that differ from the tree are a warning")
    ap.add_argument("--skip-tests", action="store_true", help="skip the JUnit suite and testing/test_harness.py (quick re-check)")
    a = ap.parse_args(argv)
    t0 = time.time()
    print("preflight: stage %s, repo %s" % (a.stage, REPO))
    if a.write_freeze:
        write_freeze(a.write_freeze, a.bands)
        return 1 if any(r[0] == "FAIL" for r in RESULTS) else 0
    ref = None
    if a.stage in ("dev", "first-call"):
        check_toolchain(strict=a.stage == "first-call")
        check_line_endings()
        if a.skip_tests:
            say("WARN", "T3", "tests skipped (--skip-tests): this is not a full gate")
        else:
            check_maven()
        check_jar()
        check_selftest()
        check_schemas()
        if not a.skip_tests:
            check_harness_tests()
        if a.freeze:
            ref = verify_freeze(a.freeze, a.bands, JAR)
    if a.stage == "first-call":
        check_git_state()
        ok = check_out_root(a, a.stage, ref)
        if ok and a.out_root and not any(r[0] == "FAIL" for r in RESULTS):
            stage_jar(a.out_root)
    if a.stage == "ingest":
        check_toolchain(strict=True)
        check_line_endings()
        check_selftest()
        if a.freeze:
            sj = os.path.join(a.out_root or "", "collusion-engine.jar")
            jar = sj if a.out_root and os.path.isfile(sj) else (JAR if build_jar() else None)
            if jar:
                ref = verify_freeze(a.freeze, a.bands, jar)
        check_out_root(a, a.stage, ref)
    if not a.freeze and a.stage in ("first-call", "ingest"):
        say("WARN", "F1", "no --freeze record given: prompt and input freeze not verified (required before the first "
            "claim-bearing call)")
    fails = [r for r in RESULTS if r[0] == "FAIL"]
    warns = [r for r in RESULTS if r[0] == "WARN"]
    print("-" * 100)
    print("%s  stage %s: %d FAIL, %d WARN, %.0f s" % ("NO-GO" if fails else "GO", a.stage, len(fails), len(warns), time.time() - t0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
