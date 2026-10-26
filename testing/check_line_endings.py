#!/usr/bin/env python3
"""Line-ending check for files whose bytes are hashed into manifests or pre-declarations (standard library only).

Why: with core.autocrlf=true (the Git for Windows default) a checkout writes CRLF, so the same commit gives different
SHA-256 values on Windows and on Linux for the raw-text hashes the engine records: llm.analysisScriptSha256 and
scenarioHashes in every LLM manifest, sweepSha256 and scenarioHashes in batch manifests, and the hashes the
pre-declaration records for bands.csv and the design files. Request hashes, replay digests, CRN seeds and template hashes
do not depend on line endings (engine test LineEndingInvarianceTest), so replay itself is portable; the manifest
hashes are not, unless every machine checks the files out with LF. The root .gitattributes pins LF for them.

Checks:
  1. policy: every tracked *.py, *.yaml, *.yml, *.json, *.jsonl, *.csv, *.tsv, *.sh file and the hook scripts resolve
     to eol=lf (or -text, as the prompt files under engine/src/main/resources/prompts do);       FAIL if not
  2. index: no such file is stored with CRLF;                                                       FAIL if one is
  3. working copy: no such file has CRLF on disk (a copy written before the policy, or by an editor); WARN (FAIL with
     --strict), with the command that refreshes the working copy.

Usage: python -X utf8 testing/check_line_endings.py [--strict] [--repo DIR]      exit 0 = pass, 1 = fail
"""
import argparse
import hashlib
import os
import subprocess
import sys

PATTERNS = ["*.py", "*.yaml", "*.yml", "*.json", "*.jsonl", "*.csv", "*.tsv", "*.sh", ".githooks/pre-commit",
            ".githooks/commit-msg", "scripts/preflight"]
REFRESH = "git stash (if needed), then: git rm -r -q --cached . && git reset -q --hard HEAD"


def git(repo, *args, stdin=None, literal=False):
    pre = ["git", "-C", repo] + (["--literal-pathspecs"] if literal else [])
    r = subprocess.run(pre + list(args), input=stdin, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout.decode("utf-8", "replace")


def tracked(repo):
    out = git(repo, "ls-files", "-z", "--", *PATTERNS)
    return sorted(f for f in out.split("\0") if f)


def attributes(repo, files):
    """file -> (text, eol) from git check-attr."""
    out = git(repo, "check-attr", "-z", "--stdin", "text", "eol", stdin="\0".join(files).encode("utf-8"))
    parts = out.split("\0")
    attrs = {}
    for i in range(0, len(parts) - 2, 3):
        f, name, value = parts[i], parts[i + 1], parts[i + 2]
        attrs.setdefault(f, {})[name] = value
    return attrs


def index_eol(repo, files):
    out = git(repo, "ls-files", "--eol", "-z", "--", *files, literal=True)
    res = {}
    for rec in out.split("\0"):
        if "\t" in rec:
            info, f = rec.split("\t", 1)
            res[f] = info.split()[0]  # i/lf, i/crlf, i/mixed, i/none, i/-text
    return res


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
    ap.add_argument("--strict", action="store_true", help="a CRLF working copy fails instead of warning")
    a = ap.parse_args(argv)
    try:
        files = tracked(a.repo)
    except RuntimeError as e:
        print("FAIL  not a git work tree: %s" % e)
        print("RESULT: FAIL")
        return 1
    if not files:
        print("FAIL  no tracked hashed-input files found under %s" % a.repo)
        print("RESULT: FAIL")
        return 1
    attrs = attributes(a.repo, files)
    idx = index_eol(a.repo, files)
    policy = [f for f in files if not (attrs.get(f, {}).get("eol") == "lf" or attrs.get(f, {}).get("text") == "unset")]
    stored_crlf = [f for f in files if idx.get(f, "missing") in ("i/crlf", "i/mixed", "missing")]
    disk_crlf = []
    for f in files:
        p = os.path.join(a.repo, f)
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                if b"\r\n" in fh.read():
                    disk_crlf.append(f)
    print("line-ending check: %d hashed-input files" % len(files))
    print(("PASS" if not policy else "FAIL") + "  1 policy: every file resolves to eol=lf or -text"
          + ("" if not policy else " (%d do not, e.g. %s)" % (len(policy), policy[:5])))
    print(("PASS" if not stored_crlf else "FAIL") + "  2 index: no file stored with CRLF"
          + ("" if not stored_crlf else " (%d, e.g. %s)" % (len(stored_crlf), stored_crlf[:5])))
    level = "PASS" if not disk_crlf else ("FAIL" if a.strict else "WARN")
    print(level + "  3 working copy: no CRLF on disk" + ("" if not disk_crlf else
          " (%d files, e.g. %s); manifest hashes written from this checkout would differ from an LF machine's. "
          "Refresh with: %s" % (len(disk_crlf), disk_crlf[:5], REFRESH)))
    ap_path = os.path.join(a.repo, "tools", "analysis.py")
    if os.path.isfile(ap_path):
        with open(ap_path, "rb") as fh:
            b = fh.read()
        lf = sha(b.replace(b"\r\n", b"\n"))
        print("info  tools/analysis.py sha256: LF %s, this working copy %s" % (lf, "the same" if sha(b) == lf else sha(b)))
    failed = bool(policy or stored_crlf or (disk_crlf and a.strict))
    print("RESULT: " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
