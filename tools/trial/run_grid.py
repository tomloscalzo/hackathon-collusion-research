#!/usr/bin/env python3
"""Run the trials of a grid.csv, one process per trial (C8.1; scope sections 14.1, 14.4, 7.1). Standard library only.
`--slice 1` runs only slice 1 of the grid (first wording + first seed of each arm); `--exclude-slice 1` leaves it out (U6).

Usage: python -X utf8 tools/trial/run_grid.py --grid grid.csv --out <trials_root> [--max-concurrency N] [--wave 1,2]
           [--arm A,B] [--limit N] [--timeout SEC] -- <game command with {placeholders}>

Each trial runs in <out>/<arm>/<trial_id>/. The command after `--` is split into arguments (never a shell string); in each
argument `{trial_dir}` and every grid column (`{trial_id}`, `{seed}`, `{model_profile}` ...) is filled in. The runner writes
`grid_row.json` (the trial's row) first, and the process's output goes to `console.log` in the trial directory.
Exit code 0 from the command = success: the runner writes `DONE`. Anything else (or a timeout) is retried once in the same
directory (so the trial's own cache is reused); a second failure writes `FAILED` holding the reason (exit code, last stderr
lines). Resuming = running the same command again: trials with `DONE` are skipped, everything else (FAILED, killed, never
started) runs again with a fresh retry. Trials run in order of (wave, grid order), `--wave` and `--arm` filter, `--limit` caps
how many are started. Exit status 0 if no trial failed, else 1. A trial that times out has its whole process tree killed.
Ctrl-C stops starting new trials and kills the games it started. The command template is checked against the grid before
any trial starts (use {{ and }} for literal braces). The periodic status line and the automatic stops (stop_rules.py, C8.2) are always on from the command line; --config adds the cost rules; a stop exits with status 3, a paused arm with 4.
`--executor modal --jar collusion-engine.jar` runs each trial in a Modal CPU container instead (modal_executor.py, C8.3; the placeholders {jar} and {scenarios} are then available).
{trial_cmd} is the Track M trial command (trial_cmd.py, C14.1) for both executors; the local executor also fills {jar} and
{scenarios} when --jar is given (the jar's absolute path and --scenarios), so one template serves both.

The executor is a small object with run(row, trial_dir, timeout) -> Result(returncode, reason); LocalExecutor is the
local process pool's worker (C8.3 adds a Modal one).
"""
import argparse
import csv
import json
import os
import re
import signal
import string
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stop_rules  # noqa: E402


class Result:
    def __init__(self, returncode, reason=""):
        self.returncode, self.reason = returncode, reason


def load_grid(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_grid(rows):
    """Reject a grid that would crash the runner or make two trials share a directory or escape --out."""
    seen = set()
    for r in rows:
        for col in ("trial_id", "arm", "wave"):
            if not r.get(col):
                raise ValueError("grid row %r has no %s" % (r.get("trial_id"), col))
        if not _SAFE.match(r["trial_id"]) or not _SAFE.match(r["arm"]) or ".." in r["trial_id"] + r["arm"]:
            raise ValueError("unsafe trial_id or arm: %r / %r" % (r["trial_id"], r["arm"]))
        if not r["wave"].isdigit():
            raise ValueError("trial %s: wave %r is not a number" % (r["trial_id"], r["wave"]))
        if r["trial_id"] in seen:
            raise ValueError("duplicate trial_id %s" % r["trial_id"])
        seen.add(r["trial_id"])


def build_command(template, row, trial_dir, extras=None):
    """Fill {trial_dir} and the grid columns into each argument of the command template (one argv entry each)."""
    clash = sorted(set(extras or {}) & set(row))
    if clash:
        raise ValueError("grid columns %s clash with the executor placeholders" % clash)
    fields = dict(row, trial_dir=str(trial_dir), **(extras or {}))
    out = []
    for a in template:
        try:
            names = [n for _, n, _, _ in string.Formatter().parse(a) if n is not None]
        except ValueError as e:
            raise ValueError("bad command argument %r: %s (use {{ and }} for literal braces)" % (a, e))
        for n in names:
            if n not in fields:
                raise ValueError("command placeholder {%s} is not a grid column or trial_dir (nor %s)" % (n, ", ".join(sorted(extras or {})) or "an executor placeholder"))
        out.append(a.format_map(fields))
    return out


def _kill_tree(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()


class LocalExecutor:
    """Run the game command as a local subprocess in the trial directory; stdout and stderr go to console.log."""

    def __init__(self, template, extras=None):
        self.template, self.extras = template, dict(extras or {})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def check(self, row):
        build_command(self.template, row, "TRIAL_DIR", self.extras)

    def run(self, row, trial_dir, timeout=None):
        argv = build_command(self.template, row, trial_dir, self.extras)
        log = Path(trial_dir) / "console.log"
        with open(log, "ab") as out:
            out.write(("--- attempt at %s\n" % time.strftime("%Y-%m-%d %H:%M:%S")).encode())
            out.flush()
            flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
            try:
                p = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **flags)
            except OSError as e:
                return Result(-1, "could not start: %s" % e)
            try:
                rc = p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_tree(p)
                p.wait()
                return Result(-1, "timed out after %ss" % timeout)
            except BaseException:                         # Ctrl-C: do not leave the game running
                _kill_tree(p)
                raise
        if rc == 0:
            return Result(0)
        tail = log.read_bytes()[-600:].decode("utf-8", "replace").strip()
        return Result(rc, "exit code %d: %s" % (rc, tail))


def _run_trial(row, out, executor, timeout):
    d = Path(out) / row["arm"] / row["trial_id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "FAILED").unlink(missing_ok=True)
    (d / "DONE").unlink(missing_ok=True)
    (d / "grid_row.json").write_text(json.dumps(row, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    start, res, attempts = time.time(), None, 0
    for attempts in (1, 2):                                  # one retry
        try:
            res = executor.run(row, d, timeout)
        except Exception as e:                               # an executor bug is a trial failure, not a crash
            res = Result(-1, "executor error: %r" % e)
        if res.returncode == 0:
            (d / "DONE").write_text("attempts %d\n" % attempts, encoding="utf-8")
            break
    else:
        (d / "FAILED").write_text(res.reason + "\n", encoding="utf-8")
    status, seconds = ("done" if res.returncode == 0 else "failed"), time.time() - start
    (d / "run_stats.json").write_text(json.dumps({"status": status, "seconds": seconds, "attempts": attempts}) + chr(10), encoding="utf-8")
    return {"trial_id": row["trial_id"], "arm": row["arm"], "status": status,
            "attempts": attempts, "seconds": seconds, "reason": "" if res.returncode == 0 else res.reason, "row": row}


def _one(row, out, executor, timeout, monitor=None, lock=None):
    """Run one trial; with a monitor, skip it if the run has stopped or its arm is paused, and record its measures."""
    if monitor is not None:
        with lock:
            if monitor.stop_reason:
                return {"trial_id": row["trial_id"], "arm": row["arm"], "status": "not_started", "attempts": 0, "seconds": 0.0, "reason": "", "row": row}
            if row["arm"] in monitor.paused:
                return {"trial_id": row["trial_id"], "arm": row["arm"], "status": "paused", "attempts": 0, "seconds": 0.0, "reason": "", "row": row}
    r = _run_trial(row, out, executor, timeout)
    if monitor is not None:
        m = stop_rules.measure(Path(out) / row["arm"] / row["trial_id"], r["status"], r["seconds"], row["arm"])
        with lock:                                           # recorded before this worker takes the next trial
            monitor.record(m)
    return r


def slice_filter(rows, include=None, exclude=None):
    """Rows whose grid `slice` (make_grid: 1 = first wording + first seed of the arm) is in include and not in exclude (sets of int).
    ValueError if a slice option is used on a grid without a numeric slice column."""
    if not include and not exclude:
        return list(rows)
    bad = [r.get("trial_id") for r in rows if not str(r.get("slice", "")).isdigit()]
    if bad:
        raise ValueError("--slice/--exclude-slice need a numeric slice column in the grid (rerun make_grid.py); e.g. trial %s" % bad[0])
    return [r for r in rows if (not include or int(r["slice"]) in include) and int(r["slice"]) not in (exclude or ())]


def select(rows, out, waves=None, arms=None, limit=None, slices=None, exclude_slices=None):
    """(todo, skipped, done): rows to run in (wave, grid order), the number already DONE, and those rows."""
    chosen = [r for r in slice_filter(rows, slices, exclude_slices) if (not waves or int(r["wave"]) in waves) and (not arms or r["arm"] in arms)]
    chosen.sort(key=lambda r: int(r["wave"]))               # stable: grid order inside a wave
    todo = [r for r in chosen if not (Path(out) / r["arm"] / r["trial_id"] / "DONE").exists()]
    skipped = len(chosen) - len(todo)
    done = [r for r in chosen if r not in todo]
    return (todo[:limit] if limit else todo), skipped, done


def run_grid(rows, out, executor, max_concurrency=4, waves=None, arms=None, limit=None, timeout=None, monitor=None, slices=None, exclude_slices=None):
    """Run the selected trials with at most max_concurrency at once; returns {"counts", "skipped", "results", "stopped", "not_started"}.
    With a stop_rules.Monitor: stop rules, arm pauses, cost and the status line (C8.2); counts then also hold "paused"."""
    validate_grid(rows)
    todo, skipped, _ = select(rows, out, waves, arms, limit, slices, exclude_slices)
    if monitor is not None:                                  # a rerun remembers what the DONE trials already cost and did
        for r in select(rows, out, waves, arms, None, slices, exclude_slices)[2]:
            d = Path(out) / r["arm"] / r["trial_id"]
            try:
                st = json.loads((d / "run_stats.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                st = {"seconds": 0.0}
            monitor.preload(stop_rules.measure(d, "done", float(st.get("seconds", 0.0)), r["arm"]))
    if todo and hasattr(executor, "check"):
        executor.check(todo[0])                              # a bad command template fails here, not once per trial
    results, lock = [], threading.Lock()
    pool = ThreadPoolExecutor(max_workers=max(1, max_concurrency))
    try:
        futures = [pool.submit(_one, r, out, executor, timeout, monitor, lock) for r in todo]
        for f in as_completed(futures):
            results.append(f.result())
    except BaseException:                                    # Ctrl-C: start nothing more
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    counts = Counter(r["status"] for r in results)
    not_started = counts.pop("not_started", 0)
    return {"counts": dict(counts), "skipped": skipped, "results": results, "not_started": not_started,
            "stopped": monitor.stop_reason if monitor else None}


def make_modal_executor(args, template):
    """The --executor modal executor (C8.3). Imported here so a local run never needs Modal."""
    import modal_executor
    jar = Path(args.jar) if args.jar else None
    if jar is None or not jar.is_file():
        raise ValueError("--executor modal needs --jar <path to collusion-engine.jar> (an existing file)")
    scen = Path(args.scenarios)
    if not scen.is_dir():
        raise ValueError("--scenarios %s is not a directory" % scen)
    return modal_executor.ModalExecutor(template, key_env=args.key_env, jar=jar, scenarios=scen, secret=args.modal_secret,
                                        cpu=args.modal_cpu, max_containers=args.modal_max_containers, memory=args.modal_memory)


TRIAL_CMD = Path(__file__).resolve().parent / "trial_cmd.py"


def local_extras(args):
    """The local executor's extra placeholders: {trial_cmd} (C14.1), and {jar} and {scenarios} when --jar is given."""
    extras = {"trial_cmd": str(TRIAL_CMD)}
    if args.jar:
        extras.update(jar=str(Path(args.jar).resolve()), scenarios=str(Path(args.scenarios).resolve()))
    return extras


def _ints(s):
    return {int(x) for x in s.split(",")} if s else None


def main(argv):
    if "--" not in argv:
        print("usage: run_grid.py --grid grid.csv --out DIR [options] -- <game command>", file=sys.stderr)
        return 2
    i = argv.index("--")
    ap = argparse.ArgumentParser(prog="run_grid.py")
    ap.add_argument("--grid", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-concurrency", type=int, default=4)
    ap.add_argument("--wave", default="")
    ap.add_argument("--arm", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--slice", default="", help="comma list of grid slices to run (1 = first wording + first seed of each arm, 2 = next wording ...)")
    ap.add_argument("--exclude-slice", default="", help="comma list of grid slices to leave out (e.g. 1 once slice 1 is done)")
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--executor", default="local", help="local (default) or modal (each trial in a Modal CPU container, C8.3)")
    ap.add_argument("--jar", default="", help="the engine jar: modal puts it in the image; locally it fills {jar}")
    ap.add_argument("--scenarios", default=str(Path(__file__).resolve().parents[2] / "engine" / "src" / "main" / "resources" / "scenarios"),
                    help="modal: the scenario directory to put in the image (default: the repo's)")
    ap.add_argument("--key-env", default="COLLUSION_VLLM_KEY", help="modal: the variable name the jar's --api-key-env names")
    ap.add_argument("--modal-secret", default="collusion-vllm-api-key")
    ap.add_argument("--modal-cpu", type=float, default=1.0)
    ap.add_argument("--modal-memory", type=int, default=2048, help="modal: MiB per container (the JVM needs room)")
    ap.add_argument("--modal-max-containers", type=int, default=500)
    ap.add_argument("--config", default="", help="JSON file: rate_per_hour, games_per_container, token_price_per_million_in/out, "
                    "pilot_cost_per_game, stage_cap_usd, context_window (see stop_rules.py); each key switches its rule on")
    a = ap.parse_args(argv[1:i])
    template = argv[i + 1:]
    if not template:
        print("error: no game command after --", file=sys.stderr)
        return 2
    if a.executor not in ("local", "modal"):
        print("error: --executor must be local or modal", file=sys.stderr)
        return 2
    try:
        executor = make_modal_executor(a, template) if a.executor == "modal" else LocalExecutor(template, local_extras(a))
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    try:
        rows = load_grid(a.grid)
        cfg = json.loads(Path(a.config).read_text(encoding="utf-8-sig")) if a.config else None
        stop_rules.check_config(cfg)
        arms = set(a.arm.split(",")) if a.arm else None
        slices, excl = _ints(a.slice), _ints(a.exclude_slice)
        total = len(select(rows, a.out, _ints(a.wave), arms, a.limit or None, slices, excl)[0])
        monitor = stop_rules.Monitor(cfg, total=total, out=lambda s: print(s, flush=True))
        with executor:
            res = run_grid(rows, a.out, executor, a.max_concurrency, _ints(a.wave), arms, a.limit or None, a.timeout, monitor, slices, excl)
    except (ValueError, OSError, RuntimeError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print(monitor.status_line(), flush=True)
    print("done %d, failed %d, paused %d, not started %d, already done %d" % (
        res["counts"].get("done", 0), res["counts"].get("failed", 0), res["counts"].get("paused", 0), res["not_started"], res["skipped"]))
    if res["stopped"]:
        print("stopped: " + res["stopped"])
        return 3
    if monitor.paused:
        print("WARNING: incomplete, arms paused for refusals: " + ", ".join(sorted(monitor.paused)))
        return 4
    return 1 if res["counts"].get("failed") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
