"""Collect the three watchdog arms with tools/trial/collect.py into a scratch dir (rerunnable).
Only DONE games are used downstream (analyze.py filters status == done); games still running are listed.
Usage: python collect_arms.py [--runs-root RUNS] [--scratch SCRATCH]"""
import limits, argparse, os, subprocess, sys, shutil
from pathlib import Path
ap = argparse.ArgumentParser()
HK = Path(os.environ.get("HACKATHON_DIR", Path.home() / "hackathon"))   # parent of runs/ and work_scratch/
ap.add_argument("--runs-root", default=str(HK / "runs"))
ap.add_argument("--scratch", default=str(HK / "work_scratch" / "watchdog_collect"))
a = ap.parse_args()
repo = Path(__file__).resolve().parents[3]
roots = {"wave_a": Path(a.runs_root) / "2026-10-25_trackm_newarms_A" / "trials" / "wd-notice-only",
         "wave_b": Path(a.runs_root) / "2026-10-25_trackm_watchdog" / "trials"}
for name, root in roots.items():
    out = Path(a.scratch) / name
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    r = subprocess.run([sys.executable, "-X", "utf8", str(repo / "tools/trial/collect.py"), str(root), str(out), "--include-pilot"],
                       capture_output=True, text=True, encoding="utf-8")
    print(name, "exit", r.returncode, r.stderr.strip()[-300:])
    undone = [d.parent.name for d in root.rglob("events.jsonl") if not (d.parent / "DONE").exists()]
    print(name, "not DONE (excluded):", undone)
