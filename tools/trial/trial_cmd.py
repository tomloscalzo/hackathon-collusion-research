#!/usr/bin/env python3
"""The Track M trial command: one grid row into its trial directory (C14.1; scope sections 14.1, 14.8). Standard library only.

run_grid.py / run_waves.py call this once per trial as their game command. It reads `{trial_dir}/grid_row.json` (written by
the runner), builds the exact engine argv for that row, prints it, runs it and returns its exit status. It changes nothing
in the game: every flag it sends already exists in the jar (CONTRACTS.md, "The trial command").

    python -X utf8 {trial_cmd} --trial-dir {trial_dir} --jar {jar} --scenarios {scenarios}
        --base-url qwen3_14b=<URL> --model qwen3_14b=<served name> [--base-url qwen3_32b_fp8=<URL> --model qwen3_32b_fp8=<name>]
        --api-key-env COLLUSION_VLLM_KEY --code-commit <git sha> --budget-tokens <n> [--allow-remote] [--allow-unwired]
        [--java java] [--print]

`--base-url`/`--model` are keyed by the grid's model_profile (`PROFILE=value`); a value without `PROFILE=` serves every
profile. `--allow-remote` sets COLLUSION_ALLOW_REMOTE=1 for the game only (the jar refuses non-local URLs without it).
`--print` prints the argv as JSON and runs nothing. Exit status: the game's, or 2 for a bad row or option.

Row to argv: communication tacit = no talk, private/monitored/public/unmonitored = `--talk on`; thinking 0|1 = `--thinking
off|on`; wording = `--paraphrase`; scenario = `{scenarios}/<scenario_file>` (the bare name, a jar resource, without
--scenarios); temperature, top_p, top_k, timeout_sec when set; `--max-tokens` = the largest per-call limit of the calls the
game makes today (quote, plus talk with talk on), since the jar has one limit until the settings map is wired. Every row
gets `--context-clamp on --context-window 16384` (unit U2: lowers a call's max_tokens to fit the window, or skips it) and `--follow-redirects on` and `--reserve-out-tokens max` (client-side only: no prompt, request or cache key changes; the
default reservation assumes 120 output tokens a call, and a game that outgrows its reservation aborts), thinking-on rows also
`--call-timeout-sec quote=s,talk=s,question=s` (the design's thinking-on timeout_sec is 300, above Modal's 150 s redirect, so a
long call is redirected rather than timed out). out, cache and call log go inside the trial directory. Seats: the scenario
file is used as is (the headline rows use slice-m-pN: two LLM seats llm1, llm2); a row whose seat list disagrees with the
file's agents block is refused (exit 2, see check_seats()).

Flags the jar may not list (C12b.2 --call-settings today; --condition-texts and --options since C11.2; CONTRACTS.md "C14.1 pending flags"): the flags in PENDING are sent only when
the jar's usage text lists them. A row that needs one the jar lacks (a condition text other than `neutral`, or arm options)
is refused with exit 2, unless `--allow-unwired` is given: then it runs without them, says so on stdout and writes
`{trial_dir}/UNWIRED` (what was not applied), so such trials can be found and must never count as data.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TALK = {"tacit": False, "private": True, "monitored": True, "public": True, "unmonitored": True}
BLANK_TEXTS = {"neutral"}            # seat-texts names whose text is empty (prompts/seat_texts.json)
PENDING = ("--condition-texts", "--options", "--call-settings")
REQUIRED = ("trial_id", "arm", "penalty_point", "scenario_file", "communication", "wording", "seed", "thinking", "model_profile")
CONTEXT_WINDOW = 16384         # the served model window; the context clamp lowers max_tokens to fit it (unit U2)
_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def _keyed(values, profile, flag):
    """The value of a repeatable PROFILE=value option for this profile (an unkeyed value serves every profile)."""
    plain, keyed = None, {}
    for v in values or []:
        m = re.match(r"^([A-Za-z0-9_]+)=(.*)$", v)
        if m and not v.lower().startswith(("http:", "https:")):
            keyed[m.group(1)] = m.group(2)
            if not m.group(2).strip():
                raise ValueError("%s %s has an empty value" % (flag, v))
        else:
            plain = v
    if profile in keyed:
        return keyed[profile]
    if plain is not None and not plain.strip():
        raise ValueError("%s has an empty value" % flag)
    if plain is None:
        raise ValueError("no %s for model_profile %r (give %s %s=...)" % (flag, profile, flag, profile))
    return plain


def check_seats(text, seats, source):
    """Fail loudly unless the scenario file's agents block seats exactly what the grid row says. The file is used as is: a grid
    `llm` seat must be an LLM agent (with several LLM seats, called `llm<i>`, i = its position: the name the condition texts use), and a grid
    `scripted:<rule>` seat must be that rule (the agent kind, e.g. defect_once = DEFECT_ONCE)."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^agents:\s*$", l)), None)
    if start is None:
        raise ValueError("%s: no agents: block, cannot check the seats %s" % (source, ",".join(seats)))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() and not lines[i][0].isspace()), len(lines))
    if any(l.startswith("#") for l in lines[start + 1:]):
        raise ValueError("%s: a column-0 comment after agents: (cannot tell where the block ends)" % source)
    items = []
    for l in lines[start + 1:end]:
        if re.match(r"^  - ", l):
            items.append([])
        if items and l.strip():
            items[-1].append(l)
    ids = [next((m.group(1) for m in (re.search(r"\bid:\s*([\w-]+)", x) for x in it) if m), None) for it in items]
    kinds = [next((m.group(1) for m in (re.search(r"\bkind:\s*([A-Za-z_]+)", x) for x in it) if m), None) for it in items]
    if len(kinds) != len(seats) or None in kinds:
        raise ValueError("%s: the grid row has %d seats (%s) but the file's agents block has %d parsable seats"
                         % (source, len(seats), ",".join(seats), len(kinds)))
    for i, (seat, kind, sid) in enumerate(zip(seats, kinds, ids)):
        if seat == "llm":
            if kind != "LLM" or (seats.count("llm") > 1 and sid != "llm%d" % (i + 1)):
                raise ValueError("%s: seat %d is %s %s in the file but llm (an LLM seat llm%d) in the grid"
                                 % (source, i + 1, kind, sid, i + 1))
        elif not (seat.startswith("scripted:") and seat.split(":", 1)[1].upper() == kind):
            raise ValueError("%s: seat %d is %s in the file but %s in the grid" % (source, i + 1, kind, seat))


def call_settings(row):
    """The settings map of the row in CallSettingsMap.fromJson form (C12b.1), for --call-settings once the jar takes it."""
    m = {"thinking": row["thinking"] == "1", "calls": {}}
    for k, col in (("temperature", "temperature"), ("top_p", "top_p")):
        if row.get(col):
            m[k] = float(row[col])
    if row.get("top_k"):
        m["top_k"] = int(row["top_k"])
    for c in ("talk", "quote", "question"):
        m["calls"][c] = {"max_tokens": int(row["max_tokens_" + c]), "timeout_sec": int(row["timeout_sec"])}
    return m


EMPTY_TALK_PROFILES = ("gpt_oss_20b",)   # unit E1 (owner-approved): only these model profiles read an empty talk reply as done


def effective_options(row):
    """The row's options cell as sent to the engine: the grid's, plus empty_talk_as_done=on for the gpt-oss profile only (unit E1).
    Any other profile gets the grid's cell untouched (the same bytes as before)."""
    cell = row.get("options") or "{}"
    if row.get("model_profile") not in EMPTY_TALK_PROFILES:
        return cell
    opts = json.loads(cell) if cell.strip() else {}
    if not isinstance(opts, dict):
        raise ValueError("grid row %r: options %r is not a JSON object" % (row.get("trial_id"), cell))
    opts.setdefault("empty_talk_as_done", "on")
    return json.dumps(opts, sort_keys=True, separators=(",", ":"))


def needs_wiring(row):
    """The pending flags this row needs to be played as designed (condition texts, arm options)."""
    names = {p.split(":", 1)[-1] for p in (row.get("condition_texts") or "").split(";") if p.strip()}
    need = ["--condition-texts"] if names - BLANK_TEXTS else []
    if effective_options(row).strip() not in ("", "{}"):
        need.append("--options")
    return need


def _window(row):
    """The row's context window (grid column context_window, unit U11: 32,768 for the 32k profile); CONTEXT_WINDOW when absent."""
    v = str(row.get("context_window", "")).strip()
    if not v:
        return CONTEXT_WINDOW
    if not v.isdigit() or int(v) < 1024:
        raise ValueError("grid row %r: context_window %r is not a token count" % (row.get("trial_id"), v))
    return int(v)


def build(row, a, trial_dir, supported=frozenset()):
    """(argv, files, notes): the engine argv for one grid row; files = {path: text} to write first; notes for stdout."""
    missing = [c for c in REQUIRED if not str(row.get(c, "")).strip()]
    if missing:
        raise ValueError("grid row %r lacks %s" % (row.get("trial_id"), ", ".join(missing)))
    if row["communication"] not in TALK:
        raise ValueError("communication %r is not one of %s" % (row["communication"], ", ".join(TALK)))
    if row["thinking"] not in ("0", "1"):
        raise ValueError("thinking must be 0 or 1, not %r" % row["thinking"])
    if not _SHA.match(a.code_commit or ""):
        raise ValueError("--code-commit must be a git sha (7-40 hex), not %r" % a.code_commit)
    d, talk, think = Path(trial_dir), TALK[row["communication"]], row["thinking"] == "1"
    scen = (a.scenarios.rstrip("/\\") + "/" + row["scenario_file"]) if a.scenarios else row["scenario_file"]
    files, notes = {}, []
    if row.get("seats"):
        check_seats(scenario_text(scen), row["seats"].split(","), row["scenario_file"])
    argv = [a.java, "-jar", a.jar, "run", "--seat", "LLM", "--multi-seat", "on"] + (["--talk", "on"] if talk else []) + [
        "--trial-dir", str(d), "--runs", "1", "--scenario", scen, "--seed", row["seed"], "--paraphrase", row["wording"],
        "--arm", row["arm"], "--trial-id", row["trial_id"], "--penalty-point", row["penalty_point"],
        "--code-commit", a.code_commit, "--thinking", "on" if think else "off",
        "--model", _keyed(a.model, row["model_profile"], "--model"),
        "--base-url", _keyed(a.base_url, row["model_profile"], "--base-url"), "--api-key-env", a.api_key_env]
    if a.budget_tokens:
        argv += ["--budget-tokens", str(a.budget_tokens)]
    argv += ["--out", str(d / "run.jsonl"), "--cache", str(d / "cache.jsonl"), "--calls", str(d / "calls.jsonl")]
    for flag, col in (("--temperature", "temperature"), ("--top-p", "top_p"), ("--top-k", "top_k"), ("--timeout-sec", "timeout_sec")):
        if str(row.get(col, "")).strip():
            argv += [flag, row[col]]
    limits = [int(row[c]) for c in (["max_tokens_quote"] + (["max_tokens_talk"] if talk else [])) if str(row.get(c, "")).strip()]
    if limits:
        argv += ["--max-tokens", str(max(limits))]
    argv += ["--follow-redirects", "on", "--reserve-out-tokens", "max"]
    argv += ["--context-clamp", "on", "--context-window", str(_window(row))]   # unit U2: Track M only (this command)
    if think:
        if str(row.get("timeout_sec", "")).strip():
            argv += ["--call-timeout-sec", ",".join("%s=%s" % (c, row["timeout_sec"]) for c in ("quote", "talk", "question"))]
    if "--condition-texts" in supported and row.get("condition_texts"):
        argv += ["--condition-texts", row["condition_texts"]]
    if "--options" in supported and effective_options(row).strip() not in ("", "{}"):
        argv += ["--options", effective_options(row)]
    if "--call-settings" in supported:
        files[str(d / "call_settings.json")] = json.dumps(call_settings(row), sort_keys=True) + "\n"
        argv += ["--call-settings", str(d / "call_settings.json")]
    lacking = [f for f in needs_wiring(row) if f not in supported]
    if lacking and not a.allow_unwired:
        raise ValueError("trial %s needs %s, which this jar does not take yet (C11.2/C13.3); --allow-unwired runs it without them"
                         % (row["trial_id"], " ".join(lacking)))
    if lacking:
        files[str(d / "UNWIRED")] = "not applied: %s (condition_texts=%s options=%s)\n" % (
            " ".join(lacking), row.get("condition_texts"), effective_options(row))
        notes.append("WARNING: --allow-unwired: %s not applied (condition_texts=%r options=%r)"
                     % (" ".join(lacking), row.get("condition_texts"), effective_options(row)))
    return argv, files, notes


def scenario_text(scen):
    """A scenario file's text: the path, else (a bare name, run without --scenarios) the repo copy the jar was built from."""
    p = Path(scen)
    repo = Path(__file__).resolve().parents
    if not p.is_file() and len(p.parts) == 1 and len(repo) > 2:
        p = repo[2] / "engine" / "src" / "main" / "resources" / "scenarios" / scen
    if not p.is_file():
        raise ValueError("scenario file %s not found" % scen)
    return p.read_text(encoding="utf-8")


def jar_flags(java, jar):
    """The --flags the jar's usage text lists (it prints usage on stderr when run without a command)."""
    try:
        p = subprocess.run([java, "-jar", jar], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return frozenset()
    return frozenset(re.findall(r"--[a-z][a-z-]*", p.stdout + p.stderr))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trial_cmd.py", description="Run one Track M grid row (C14.1).")
    ap.add_argument("--trial-dir", required=True)
    ap.add_argument("--jar", required=True)
    ap.add_argument("--scenarios", default="")
    ap.add_argument("--java", default="java")
    ap.add_argument("--base-url", action="append", required=True)
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--api-key-env", required=True)
    ap.add_argument("--code-commit", required=True)
    ap.add_argument("--budget-tokens", type=int, default=0)
    ap.add_argument("--allow-remote", action="store_true")
    ap.add_argument("--allow-unwired", action="store_true")
    ap.add_argument("--print", action="store_true", dest="dry")
    a = ap.parse_args(argv)
    try:
        row = json.loads((Path(a.trial_dir) / "grid_row.json").read_text(encoding="utf-8"))
        supported = jar_flags(a.java, a.jar) if (needs_wiring(row) or not a.dry) else frozenset()
        cmd, files, notes = build(row, a, a.trial_dir, supported & set(PENDING))
    except (OSError, ValueError, KeyError) as e:
        print("trial_cmd: error: %s" % e, file=sys.stderr)
        return 2
    if a.dry:
        print(json.dumps(cmd))
        return 0
    for n in notes:
        print("trial_cmd: " + n, flush=True)
    print("trial_cmd: " + " ".join(cmd), flush=True)
    env = dict(os.environ, COLLUSION_ALLOW_REMOTE="1") if a.allow_remote else None
    try:
        Path(a.trial_dir, "UNWIRED").unlink(missing_ok=True)       # a rerun that is wired again drops the old mark
        for path, text in files.items():
            Path(path).write_text(text, encoding="utf-8")
        return subprocess.call(cmd, env=env, stdin=subprocess.DEVNULL)
    except OSError as e:
        print("trial_cmd: error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
