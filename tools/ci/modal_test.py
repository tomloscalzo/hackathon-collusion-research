"""Run the engine's Maven test gate (`mvn -q -o test`) on Modal CPU.

Usage: python -X utf8 tools/ci/modal_test.py <worktree_path> [--cpu 16] [--memory-gb 16] [--timeout-min 40]

Sends the worktree (everything except .git, top-level results, target, __pycache__) as a tarball to a Modal function whose image has
JDK 17, Maven and the engine's dependencies pre-fetched (the image is cached; the first run builds it). The function runs
`mvn -q -o test` in engine/ and returns the exit code and the surefire reports. This script prints a summary, writes the
reports to <worktree>/engine/target/modal-surefire/ and exits with Maven's exit code (2 = infrastructure failure).
Does not read or change engine code or tests. No key is used: the Modal token in ~/.modal.toml is enough.
"""
import argparse
import io
import sys
import tarfile
import time
from pathlib import Path

EXCLUDE_DIRS = {".git", "target", "__pycache__", "node_modules", ".venv"}   # at any depth
EXCLUDE_TOP = {"results"}                                                 # large output folder, top level only (engine has a Java package "results")
PRICE_CPU_CORE_SEC = 0.0000131   # USD per core-second (Modal list price for cpu= cores; verify at modal.com/pricing)
PRICE_MEM_GIB_SEC = 0.00000222   # USD per GiB-second


def make_tar(root):
    root = Path(root).resolve()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=3) as tf:
        def keep(ti):
            parts = Path(ti.name).parts
            return None if any(p in EXCLUDE_DIRS for p in parts) else ti
        for top in sorted(root.iterdir()):
            if top.name in EXCLUDE_DIRS or top.name in EXCLUDE_TOP:
                continue
            tf.add(str(top), arcname="repo/" + top.name, filter=keep)
    return buf.getvalue()


def build_app(cpu, memory_gb, timeout_min):
    import modal
    pom = Path(__file__).resolve().parents[2] / "engine" / "pom.xml"
    prefetch = (
        "mkdir -p /warm/src/test/java && cp /warm/pom.xml /warm/pom.xml.bak && "
        "echo 'import org.junit.jupiter.api.Test; class WarmTest { @Test void t() {} }' > /warm/src/test/java/WarmTest.java && "
        "cd /warm && mvn -q dependency:go-offline && mvn -q test && mvn -q dependency:resolve-plugins")
    image = (modal.Image.debian_slim(python_version="%d.%d" % sys.version_info[:2])
             .apt_install("openjdk-17-jdk-headless", "maven")
             .add_local_file(str(pom), "/warm/pom.xml", copy=True)
             .run_commands(prefetch))
    app = modal.App("collusion-test-gate")

    @app.function(image=image, cpu=cpu, memory=memory_gb * 1024, timeout=timeout_min * 60, serialized=True)
    def run_tests(tar_bytes):
        import glob, io as _io, os, re, subprocess, tarfile as _tf, time as _t
        work = "/work"
        os.makedirs(work, exist_ok=True)
        with _tf.open(fileobj=_io.BytesIO(tar_bytes), mode="r:gz") as tf:
            tf.extractall(work)
        eng = work + "/repo/engine"
        t0 = _t.time()
        p = subprocess.run(["mvn", "-q", "-o", "test"], cwd=eng, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, errors="replace", env=dict(os.environ, JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8"))
        secs = _t.time() - t0
        tests = fails = errs = skips = 0
        for f in glob.glob(eng + "/target/surefire-reports/TEST-*.xml"):
            head = open(f, encoding="utf-8", errors="replace").read(4000)
            m = re.search(r'<testsuite [^>]*>', head)
            if not m:
                continue
            g = lambda k: int(re.search(k + r'="(\d+)"', m.group(0)).group(1))
            tests += g("tests"); fails += g("failures"); errs += g("errors"); skips += g("skipped")
        out = _io.BytesIO()
        with _tf.open(fileobj=out, mode="w:gz") as tf:
            if os.path.isdir(eng + "/target/surefire-reports"):
                tf.add(eng + "/target/surefire-reports", arcname="surefire-reports")
        return {"exit": p.returncode, "tests": tests, "failures": fails, "errors": errs, "skipped": skips,
                "mvn_seconds": secs, "log_tail": p.stdout[-6000:], "reports": out.getvalue()}

    return app, run_tests


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("worktree")
    ap.add_argument("--cpu", type=float, default=16)
    ap.add_argument("--memory-gb", type=int, default=16)
    ap.add_argument("--timeout-min", type=int, default=40)
    a = ap.parse_args(argv)
    wt = Path(a.worktree).resolve()
    if not (wt / "engine" / "pom.xml").is_file():
        print("not a worktree with engine/pom.xml: %s" % wt)
        return 2
    t0 = time.time()
    data = make_tar(wt)
    print("sent %.1f MB; starting Modal run (cpu=%g, memory=%d GB)" % (len(data) / 1e6, a.cpu, a.memory_gb))
    try:
        import modal
        app, fn = build_app(a.cpu, a.memory_gb, a.timeout_min)
        with modal.enable_output(), app.run():
            r = fn.remote(data)
    except Exception as e:  # infrastructure failure
        print("MODAL FAILURE: %s: %s" % (type(e).__name__, e))
        return 2
    wall = time.time() - t0
    dest = wt / "engine" / "target" / "modal-surefire"
    dest.mkdir(parents=True, exist_ok=True)
    if r["reports"]:
        with tarfile.open(fileobj=io.BytesIO(r["reports"]), mode="r:gz") as tf:
            tf.extractall(dest)
    if r["exit"] != 0:
        print("---- mvn output (tail) ----\n" + r["log_tail"])
    cost = a.cpu * r["mvn_seconds"] * PRICE_CPU_CORE_SEC + a.memory_gb * r["mvn_seconds"] * PRICE_MEM_GIB_SEC
    print("RESULT exit=%d tests=%d failures=%d errors=%d skipped=%d  mvn=%.0fs wall=%.0fs  est.cost=$%.3f  reports=%s"
          % (r["exit"], r["tests"], r["failures"], r["errors"], r["skipped"], r["mvn_seconds"], wall, cost, dest))
    return r["exit"]


if __name__ == "__main__":
    sys.exit(main())
