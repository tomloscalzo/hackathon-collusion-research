#!/usr/bin/env python3
"""Expand the Track M design file into grid.csv, one row per trial (C1.1; scope sections 14.1, 4.3, 4.4, 4.7, 7).

Usage: python -X utf8 tools/trial/make_grid.py <design.yaml> <grid.csv>      (PyYAML needed)

Trial id: <arm>__p<point>__w<wording>__s<seed>__t<0|1>   (t1 = thinking on, t0 = thinking off). collect.py parses it.
Rows come out in design order (arm, point, wording, seed, thinking), written LF-terminated, so the same design gives the
same bytes. Columns (GRID_COLS): trial_id, arm, penalty_point, scenario_file (under engine/src/main/resources/scenarios),
communication (tacit|private|monitored|public|unmonitored), firms, seats (comma list; `llm` or `scripted:<rule>`),
condition_texts (`seat:name;seat:name`, names in the seat-texts file; seat `all` = every LLM seat), wording, seed, thinking
(0|1), model_profile, temperature, top_p, top_k, max_tokens_talk/quote/question, timeout_sec (from the profile, per thinking
mode), wave (spending-order step, scope section 7), introspection (R2f R3f R2s R3s R4, or empty), options (JSON, sorted keys, for arm-specific
switches), theory_theta_star (C1.2: the number after `# theory-theta-star:` in the scenario file, the CartelSolver's collusion
margin at that penalty point, 0 = collusion does not pay; empty for a scenario file without the line, such as n3-group and n4-group,
(n3-cheater carries the N=3 theta*); a points-table file without it is an error), then (U6) slice and pilot, then (U11)
context_window (the design profile's context_window, default 16384; trial_cmd passes it to --context-window; collect.py copies it
into trials.csv so qc_report checks each trial against its own window).
slice: the 1-based position of the row's (wording, seed) pair in its arm, wording varying fastest: slice 1 = first wording + first
seed, slice 2 = second wording + first seed, ... (run_grid.py / run_waves.py --slice N, --exclude-slice N select on it). pilot: "true"
for a throwaway pilot row (arm key `pilot: true`; arms with `cell_from` default to true, `pilot: false` turns it off), else empty;
collect.py leaves pilot trials out of its tables unless --include-pilot.
An arm with `cell_from: introspection_cell` runs at that cell and is skipped, with a note on stderr, until the cell is set.
The cell can come from a file written by pick_cell.py: `make_grid.py design.yaml grid.csv --cell-file cell.json`.
--global-options key=value[,key=value] merges those options into EVERY row's options cell (values JSON-parsed if they parse, else
strings; the cell stays sorted-keys JSON, so a row's other options are untouched). `--global-options payoff_examples=neutral`
makes the neutral twin of a grid: same trial ids (the grid root identifies the condition), options gain payoff_examples. The
payoff_examples column (anchored|neutral|formula|none, last column) is the row's final payoff_examples option, anchored when absent; with
no global option the options cells (so the engine digests) are unchanged. An explicit payoff_examples=anchored drops the key from
the cell (the column still says anchored), so it is digest-identical to the default grid too.
--model-profile NAME retargets the whole design to one design profile (e.g. gpt_oss_20b, a model with no thinking-off mode): every arm gets
model_profile NAME and thinking [1] (t0 rows are dropped, so the trial ids keep their __t1 suffix and the t1 wave); arms already on NAME
(the oss-* arms), arms on the 14B profile and arms whose own profile has a different context window than NAME (the 32k fed arms) are skipped
with a note on stderr. --exclude-arms a,b drops arms by name. Without the flags the grid is byte-identical to before.
Validation errors raise ValueError (exit 2 from the CLI): bad seats, unknown point or profile, thinking not 0/1, duplicate ids.
"""
import csv
import json
import re
import sys
from pathlib import Path

SCENARIOS = Path(__file__).resolve().parents[2] / "engine" / "src" / "main" / "resources" / "scenarios"
DEFAULT_CONTEXT_WINDOW = 16384   # the window of the 16k deploy profiles; a design profile may set context_window (unit U11)
GRID_COLS = ["trial_id", "arm", "penalty_point", "scenario_file", "communication", "firms", "seats", "condition_texts",
             "wording", "seed", "thinking", "model_profile", "temperature", "top_p", "top_k", "max_tokens_talk",
             "max_tokens_quote", "max_tokens_question", "timeout_sec", "wave", "introspection", "options", "theory_theta_star", "slice", "pilot",
             "context_window", "payoff_examples"]
WATCHDOG_KEYS = ("question_when", "question_feedback")   # engine options of unit W2 (need the option question)
PAYOFF_EXAMPLES = ("anchored", "neutral", "formula", "none")   # engine option payoff_examples; absent from the options cell = anchored


def _texts(d):
    return ";".join("%s:%s" % (k, d[k]) for k in d)


COMMUNICATIONS = ("tacit", "private", "monitored", "public", "unmonitored")
_ID_OK = re.compile(r"^[A-Za-z0-9-]+$")


def _check(a, design):
    """Reject a bad arm with a ValueError that names the arm."""
    name = a.get("name")
    if not isinstance(name, str) or not _ID_OK.match(name):
        raise ValueError("arm name %r must be letters, digits and '-' only" % (name,))
    for key in ("firms", "seats", "communication", "condition_texts", "wordings", "seeds", "thinking", "wave", "model_profile"):
        if key not in a:
            raise ValueError("arm %s: missing %s" % (name, key))
    if a.get("cell_from") and not isinstance(design.get(a["cell_from"]), dict):
        raise ValueError("arm %s: cell_from %r is not a section of the design" % (name, a["cell_from"]))
    if not a.get("cell_from") and not a.get("points"):
        raise ValueError("arm %s: needs points or cell_from" % name)
    if set(a["wave"]) != {"t0", "t1"}:
        raise ValueError("arm %s: wave needs exactly the keys t0 and t1" % name)
    if a["communication"] not in COMMUNICATIONS and not a.get("cell_from"):
        raise ValueError("arm %s: communication %r not in %s" % (name, a["communication"], COMMUNICATIONS))
    for key in ("wordings", "seeds", "thinking", "points"):
        vals = a.get(key) or []
        if len(set(vals)) != len(vals):
            raise ValueError("arm %s: duplicate values in %s" % (name, key))
        if any(type(v) is not int for v in vals):
            raise ValueError("arm %s: %s must be integers (thinking 0 or 1, not true/false)" % (name, key))
    llm = ["all"] + ["llm%d" % (i + 1) for i, s in enumerate(a["seats"]) if s == "llm"]
    for seat in a["condition_texts"]:
        if seat not in llm:
            raise ValueError("arm %s: condition_texts seat %s is not one of %s" % (name, seat, llm))
    for s in a["seats"]:
        if s != "llm" and not str(s).startswith("scripted:"):
            raise ValueError("arm %s: seat %r must be llm or scripted:<rule>" % (name, s))


def _seeds_by_wording(a):
    """seeds_by_wording: {wording: [seed, ...]} -> that map (int keys); every wording of the arm needs a list, all of the same length."""
    m = {int(k): list(v) for k, v in a["seeds_by_wording"].items()}
    miss = [w for w in a.get("wordings") or [] if w not in m]
    if miss:
        raise ValueError("arm %s: seeds_by_wording has no seeds for wordings %s" % (a.get("name"), miss))
    if len({len(m[w]) for w in a["wordings"]}) > 1:
        raise ValueError("arm %s: seeds_by_wording lists differ in length" % a.get("name"))
    return m


def _split_top_level(spec):
    """Split on commas outside brackets, braces and double-quoted strings."""
    parts, depth, quoted, esc, cur = [], 0, False, False, []
    for ch in spec:
        if quoted:
            esc = (ch == "\\") and not esc
            if ch == '"' and not esc:
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    if quoted or depth != 0:
        raise ValueError("global options %r: unbalanced quote or bracket" % spec)
    parts.append("".join(cur))
    return [p for p in parts if p.strip()]


def _no_constant(name):
    raise ValueError("%s is not allowed in a global option value" % name)


def parse_global_options(spec):
    """`key=value[,key=value]` -> dict. Commas inside brackets or quotes do not split. A value is JSON-parsed when it parses
    (3, true, [1,2], "x"; NaN and Infinity are rejected), else kept as a string. payoff_examples must be anchored, neutral, formula or none.
    ValueError on a malformed spec."""
    out = {}
    for part in _split_top_level(spec or ""):
        key, eq, val = part.partition("=")
        key = key.strip()
        if not eq or not key:
            raise ValueError("global option %r must be key=value" % part)
        try:
            out[key] = json.loads(val, parse_constant=_no_constant)
        except json.JSONDecodeError:
            out[key] = val
    for k in WATCHDOG_KEYS:   # unit W2: arm-specific; a global value would put it in every row (rows without a question would then fail)
        if k in out:
            raise ValueError("global option %s is not allowed: it belongs to the arms that ask the watchdog question (design options)" % k)
    if "payoff_examples" in out and out["payoff_examples"] not in PAYOFF_EXAMPLES:
        raise ValueError("payoff_examples must be one of %s, got %r" % (PAYOFF_EXAMPLES, out["payoff_examples"]))
    return out


def _arm_rows(arm, design, global_options=None):
    a = dict(design.get("defaults") or {})
    a.update(arm)
    sbw = None
    if "seeds" not in arm and a.get("seeds_by_wording"):    # an arm's own seeds list overrides the design-wide per-wording map
        sbw = _seeds_by_wording(a)
        a["seeds"] = [s for w in a["wordings"] for s in sbw[w]]
    _check(a, design)
    name = a["name"]
    cell = design.get(a["cell_from"]) if a.get("cell_from") else None
    if cell is not None:
        if cell.get("point") is None or cell.get("communication") is None:
            return None
        a["points"], a["communication"] = [cell["point"]], cell["communication"]
    if len(a["seats"]) != int(a["firms"]):
        raise ValueError("arm %s: seats %s do not match firms %s" % (name, a["seats"], a["firms"]))
    if a.get("max_tokens") is not None and not isinstance(a["max_tokens"], dict):
        raise ValueError("arm %s: max_tokens must be a mapping {t0|t1: {...}}" % name)
    for mode, lim in (a.get("max_tokens") or {}).items():    # arm override of the profile's per-call token limits (U23)
        if mode not in ("t0", "t1") or not isinstance(lim, dict) or not set(lim) <= {"talk", "quote", "question"} \
                or any(type(v) is not int or v < 1 for v in lim.values()):
            raise ValueError("arm %s: max_tokens must be {t0|t1: {talk|quote|question: positive int}}" % name)
    prof = (design.get("model_profiles") or {}).get(a["model_profile"])
    if prof is None:
        raise ValueError("arm %s: unknown model profile %s" % (name, a["model_profile"]))
    pilot = a.get("pilot", bool(a.get("cell_from")))
    if type(pilot) is not bool:
        raise ValueError("arm %s: pilot must be true or false" % name)
    opts = dict(a.get("options") or {})
    opts.update(global_options or {})   # a global option wins over the arm's own value for the same key
    for k in WATCHDOG_KEYS:
        if k in opts and not isinstance(opts.get("question"), str):
            raise ValueError("arm %s: option %s needs an in-game question (option question)" % (name, k))
    if "question_when" in opts and not (opts["question_when"] in ("always", "non_competitive") or re.fullmatch(r"self_report_ge:-?[0-9]{1,6}", str(opts["question_when"]))):
        raise ValueError("arm %s: question_when must be always, non_competitive or self_report_ge:<k>, got %r" % (name, opts["question_when"]))
    if "question_feedback" in opts and opts["question_feedback"] not in ("fed", "none"):
        raise ValueError("arm %s: question_feedback must be fed or none, got %r" % (name, opts["question_feedback"]))
    payoff = opts.get("payoff_examples", "anchored")
    if payoff not in PAYOFF_EXAMPLES:
        raise ValueError("arm %s: payoff_examples must be one of %s, got %r" % (name, PAYOFF_EXAMPLES, payoff))
    if payoff == "anchored":
        opts.pop("payoff_examples", None)   # anchored is the engine default: the cell stays digest-identical to a grid without the key
    rows = []
    for pt in a["points"]:
        if pt not in design["points"]:
            raise ValueError("arm %s: point %s is not in the design's points" % (name, pt))
        for w in a["wordings"]:
            for s in (sbw[w] if sbw else a["seeds"]):
                for t in a["thinking"]:
                    if t not in (0, 1):
                        raise ValueError("arm %s: thinking must be 0 or 1, got %r" % (name, t))
                    p = prof["t%d" % t]
                    mt = dict(p["max_tokens"])
                    mt.update(((a.get("max_tokens") or {}).get("t%d" % t)) or {})   # arm override {t0: {quote: 900}} (U23)
                    rows.append({
                        "trial_id": "%s__p%s__w%s__s%s__t%d" % (name, pt, w, s, t), "arm": name, "penalty_point": pt,
                        "scenario_file": a.get("scenario") or design["points"][pt], "communication": a["communication"],
                        "firms": a["firms"], "seats": ",".join(a["seats"]), "condition_texts": _texts(a["condition_texts"]),
                        "wording": w, "seed": s, "thinking": t, "model_profile": a["model_profile"],
                        "temperature": p["temperature"], "top_p": p["top_p"], "top_k": p["top_k"],
                        "max_tokens_talk": mt["talk"], "max_tokens_quote": mt["quote"], "max_tokens_question": mt["question"],
                        "timeout_sec": p["timeout_sec"], "wave": a["wave"]["t%d" % t],
                        "introspection": a.get("introspection", ""),
                        "slice": (sbw[w] if sbw else a["seeds"]).index(s) * len(a["wordings"]) + a["wordings"].index(w) + 1,
                        "pilot": "true" if pilot else "",
                        "context_window": int(prof.get("context_window", DEFAULT_CONTEXT_WINDOW)),
                        "options": json.dumps(opts, sort_keys=True, separators=(",", ":")), "payoff_examples": payoff})
    return rows


THEORY_RE = re.compile(r"^#\s*theory-theta-star:(.*)$", re.M)
_NUMBER = re.compile(r"^[0-9]+(\.[0-9]+)?$")


def theory_theta_star(scenario_file, required=True):
    """The value of the `# theory-theta-star:` comment in a scenario file (as written, a string), or "" if absent and not required."""
    m = THEORY_RE.search((SCENARIOS / scenario_file).read_text(encoding="utf-8-sig"))
    if m:
        value = m.group(1).strip()
        if not _NUMBER.match(value):
            raise ValueError("%s: malformed '# theory-theta-star:' value %r" % (scenario_file, value))
        return value
    if required:
        raise ValueError("%s has no '# theory-theta-star: <number>' line" % scenario_file)
    return ""


def retarget(design, profile, exclude=()):
    """Return (design copy, notes): every arm moved to `profile`, thinking [1] only (see --model-profile in the module docstring)."""
    profiles = design.get("model_profiles") or {}
    if profile not in profiles:
        raise ValueError("unknown model profile %s (design profiles: %s)" % (profile, ", ".join(sorted(profiles))))
    if "t1" not in profiles[profile]:
        raise ValueError("model profile %s has no t1 settings" % profile)
    window = int(profiles[profile].get("context_window", DEFAULT_CONTEXT_WINDOW))
    names = {a["name"] for a in design["arms"]}
    unknown = sorted(set(exclude) - names)
    if unknown:
        raise ValueError("--exclude-arms names unknown arm(s): %s" % ", ".join(unknown))
    default_prof = (design.get("defaults") or {}).get("model_profile")
    out, notes = dict(design), []
    out["arms"] = []
    for arm in design["arms"]:
        own = arm.get("model_profile", default_prof)
        own_window = int((profiles.get(own) or {}).get("context_window", DEFAULT_CONTEXT_WINDOW))
        why = None
        if arm["name"] in exclude:
            why = "excluded by --exclude-arms"
        elif own == profile:
            why = "already on %s" % profile
        elif own == "qwen3_14b":
            why = "a 14B-model arm"
        elif own_window != window:
            why = "its profile %s has a %d-token window, %s has %d" % (own, own_window, profile, window)
        elif 1 not in (arm.get("thinking", (design.get("defaults") or {}).get("thinking", [0, 1]))):
            why = "a thinking-off-only arm"
        if why:
            notes.append("arm %s skipped by --model-profile %s: %s" % (arm["name"], profile, why))
            continue
        a = dict(arm)
        a["model_profile"], a["thinking"] = profile, [1]
        out["arms"].append(a)
    return out, notes


def expand(design, design_path=None, global_options=None):  # design_path is kept for callers; unused
    """Return (rows, notes): rows are dicts keyed by GRID_COLS (values stringified); notes list skipped arms.
    global_options (dict) is merged into every row's options; trial ids do not change."""
    rows, notes = [], []
    for arm in design["arms"]:
        got = _arm_rows(arm, design, global_options)
        if got is None:
            notes.append("arm %s skipped: %s is not set yet" % (arm["name"], arm["cell_from"]))
        else:
            rows.extend(got)
    ids = [r["trial_id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError("duplicate trial ids (duplicate arm names?): %s" % ", ".join(dup[:5]))
    overrides = {a["name"] for a in design["arms"] if a.get("scenario")}
    theory = {}
    for r in rows:
        key = (r["scenario_file"], r["arm"] in overrides)
        if key not in theory:
            theory[key] = theory_theta_star(key[0], required=not key[1])
        r["theory_theta_star"] = theory[key]
    return [{k: str(v) for k, v in r.items()} for r in rows], notes


def write_grid(rows, out):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, GRID_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_cell(path):
    """The chosen cell written by pick_cell.py: (point, communication). ValueError if the file is not a usable cell."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        point, comm = d["point"], d["communication"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError("cell file %s is not usable: %r" % (path, e))
    if type(point) is not int or comm not in COMMUNICATIONS:
        raise ValueError("cell file %s: need an integer point and a communication in %s" % (path, COMMUNICATIONS))
    return {"point": point, "communication": comm}


def main(argv):
    argv = list(argv)
    cell_file = None
    if "--cell-file" in argv:
        i = argv.index("--cell-file")
        if i + 1 >= len(argv):
            print("error: --cell-file needs a path", file=sys.stderr)
            return 2
        cell_file = argv[i + 1]
        del argv[i:i + 2]
    global_spec = None
    if "--global-options" in argv:
        i = argv.index("--global-options")
        if i + 1 >= len(argv):
            print("error: --global-options needs key=value[,key=value]", file=sys.stderr)
            return 2
        global_spec = argv[i + 1]
        del argv[i:i + 2]
    model_profile, exclude = None, ()
    for flag in ("--model-profile", "--exclude-arms"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 >= len(argv):
                print("error: %s needs a value" % flag, file=sys.stderr)
                return 2
            if flag == "--model-profile":
                model_profile = argv[i + 1]
            else:
                exclude = tuple(x for x in argv[i + 1].split(",") if x)
            del argv[i:i + 2]
    if exclude and not model_profile:
        print("error: --exclude-arms is only used together with --model-profile", file=sys.stderr)
        return 2
    if len(argv) != 3:
        print("usage: make_grid.py <design.yaml> <grid.csv> [--cell-file cell.json] [--global-options key=value[,key=value]] [--model-profile NAME [--exclude-arms a,b]]", file=sys.stderr)
        return 2
    import yaml
    design = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    try:
        if cell_file:
            design["introspection_cell"] = read_cell(cell_file)
        pre = []
        if model_profile:
            design, pre = retarget(design, model_profile, exclude)
        rows, notes = expand(design, argv[1], parse_global_options(global_spec))
        notes = pre + notes
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    for n in notes:
        print("note: " + n, file=sys.stderr)
    write_grid(rows, argv[2])
    print("%d trials -> %s" % (len(rows), argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
