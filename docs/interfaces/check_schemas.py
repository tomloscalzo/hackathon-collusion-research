"""Structural checker for the engine interface schemas (docs/interfaces/schemas, JSON Schema draft 2020-12 subset).

No third-party packages. It implements the keywords the schemas use (type, properties, required,
additionalProperties, items, enum, const, minimum, maximum, exclusiveMinimum, exclusiveMaximum, minLength, pattern,
minItems, uniqueItems, $ref to local #/$defs, anyOf, allOf, if/then/else) and refuses any other validation keyword, so a
schema can never silently ask for a check that is not made.

Checks, in order:
  1. every schema uses only supported keywords and every $ref resolves;
  2. llm_game_reply / llm_vignette_reply equal PromptBuilder.DECISION_SCHEMA / CHOICE_SCHEMA in substance (annotation
     keywords removed), read from the Java source;
  3. examples/*.examples.json: every "valid" object passes, every "invalid" object fails;
  4. data files given on the command line (files or directories, searched recursively), classified by file name and
     content, are validated;
  5. cross-field invariants are checked on the data that validated (see check_* functions).
Not checked: manifest.json, summary.csv and the Exporter CSVs (no schema; data_files() skips them). The call-log join
of check 5 groups calls by runKey across all call files given, so check paired arms with equal seeds separately.

Usage:  python -X utf8 docs/interfaces/check_schemas.py [data paths ...]
Exit 0 when everything passes, 1 otherwise.
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(HERE, "schemas")
EXAMPLES = os.path.join(HERE, "examples")
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
PROMPT_BUILDER = os.path.join(REPO, "engine", "src", "main", "java", "io", "github", "tomloscalzo", "collusion",
                              "agents", "llm", "PromptBuilder.java")
TALK_PARSER = os.path.join(os.path.dirname(PROMPT_BUILDER), "TalkParser.java")

ANNOTATIONS = {"$schema", "$id", "title", "description", "$comment", "examples", "default", "$defs"}
VALIDATION = {"type", "properties", "required", "additionalProperties", "items", "enum", "const", "minimum", "maximum",
              "exclusiveMinimum", "exclusiveMaximum", "minLength", "pattern", "minItems", "uniqueItems", "$ref", "anyOf",
              "allOf", "if", "then", "else"}

# ----------------------------------------------------------------------------------------------- minimal validator


def load_schemas():
    out = {}
    for f in sorted(os.listdir(SCHEMAS)):
        if f.endswith(".schema.json"):
            with open(os.path.join(SCHEMAS, f), encoding="utf-8") as fh:
                out[f[: -len(".schema.json")]] = json.load(fh)
    return out


def is_type(v, t):
    if t == "null":
        return v is None
    if t == "boolean":
        return isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    if t == "string":
        return isinstance(v, str)
    if t == "array":
        return isinstance(v, list)
    if t == "object":
        return isinstance(v, dict)
    raise ValueError("unknown type " + t)


def json_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return a == b


class Validator:
    def __init__(self, root):
        self.root = root

    def resolve(self, ref):
        if not ref.startswith("#/"):
            raise ValueError("only local refs are supported: " + ref)
        node = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    def errors(self, v, s, path="$"):
        errs = []
        if s is True or s == {}:
            return errs
        if s is False:
            return [path + ": no value allowed"]
        if "$ref" in s:
            errs += self.errors(v, self.resolve(s["$ref"]), path)
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(is_type(v, t) for t in ts):
                return errs + [f"{path}: expected {'/'.join(ts)}, got {type(v).__name__} {short(v)}"]
        if "const" in s and not json_equal(v, s["const"]):
            errs.append(f"{path}: expected const {s['const']!r}, got {short(v)}")
        if "enum" in s and not any(json_equal(v, e) for e in s["enum"]):
            errs.append(f"{path}: {short(v)} not in {s['enum']}")
        if is_type(v, "number"):
            if "minimum" in s and v < s["minimum"]:
                errs.append(f"{path}: {v} < minimum {s['minimum']}")
            if "maximum" in s and v > s["maximum"]:
                errs.append(f"{path}: {v} > maximum {s['maximum']}")
            if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
                errs.append(f"{path}: {v} <= exclusiveMinimum {s['exclusiveMinimum']}")
            if "exclusiveMaximum" in s and v >= s["exclusiveMaximum"]:
                errs.append(f"{path}: {v} >= exclusiveMaximum {s['exclusiveMaximum']}")
        if isinstance(v, str):
            if "minLength" in s and len(v) < s["minLength"]:
                errs.append(f"{path}: shorter than {s['minLength']}")
            if "pattern" in s and not re.search(s["pattern"], v):
                errs.append(f"{path}: {short(v)} does not match {s['pattern']}")
        if isinstance(v, list):
            if "minItems" in s and len(v) < s["minItems"]:
                errs.append(f"{path}: fewer than {s['minItems']} items")
            if s.get("uniqueItems"):
                seen = [json.dumps(x, sort_keys=True) for x in v]
                if len(seen) != len(set(seen)):
                    errs.append(f"{path}: items not unique")
            if "items" in s:
                for i, x in enumerate(v):
                    errs += self.errors(x, s["items"], f"{path}[{i}]")
        if isinstance(v, dict):
            for r in s.get("required", []):
                if r not in v:
                    errs.append(f"{path}: missing required '{r}'")
            props = s.get("properties", {})
            for k, x in v.items():
                if k in props:
                    errs += self.errors(x, props[k], f"{path}.{k}")
                elif "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        errs.append(f"{path}: unexpected property '{k}'")
                    elif isinstance(ap, dict):
                        errs += self.errors(x, ap, f"{path}.{k}")
        for sub in s.get("allOf", []):
            errs += self.errors(v, sub, path)
        if "anyOf" in s and not any(not self.errors(v, sub, path) for sub in s["anyOf"]):
            errs.append(f"{path}: matches none of anyOf")
        if "if" in s:
            if not self.errors(v, s["if"], path):
                if "then" in s:
                    errs += self.errors(v, s["then"], path)
            elif "else" in s:
                errs += self.errors(v, s["else"], path)
        return errs


def short(v):
    t = json.dumps(v)
    return t if len(t) < 60 else t[:57] + "..."


def keyword_problems(s, root, path="#"):
    """Unsupported keywords and dangling refs in a schema."""
    out = []
    if isinstance(s, bool):
        return out
    for k, x in s.items():
        if k not in ANNOTATIONS and k not in VALIDATION:
            out.append(f"{path}: unsupported keyword '{k}'")
    if "$ref" in s:
        try:
            Validator(root).resolve(s["$ref"])
        except (KeyError, ValueError):
            out.append(f"{path}: dangling $ref {s['$ref']}")
    for k in ("properties", "$defs"):
        for name, sub in s.get(k, {}).items():
            out += keyword_problems(sub, root, f"{path}/{k}/{name}")
    for k in ("items", "additionalProperties", "if", "then", "else"):
        if isinstance(s.get(k), dict):
            out += keyword_problems(s[k], root, f"{path}/{k}")
    for k in ("anyOf", "allOf"):
        for i, sub in enumerate(s.get(k, [])):
            out += keyword_problems(sub, root, f"{path}/{k}/{i}")
    return out


def strip_annotations(s):
    if isinstance(s, dict):
        return {k: strip_annotations(v) for k, v in s.items() if k not in ANNOTATIONS}
    if isinstance(s, list):
        return [strip_annotations(x) for x in s]
    return s


def java_constant(src, name):
    m = re.search(r"\b" + name + r"\s*=\s*((?:\"(?:[^\"\\]|\\.)*\"\s*\+?\s*)+);", src)
    if not m:
        raise ValueError("constant " + name + " not found")
    parts = re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(1))
    return "".join(p.replace('\\"', '"').replace("\\\\", "\\") for p in parts)


# ----------------------------------------------------------------------------------------------- reporting


class Report:
    def __init__(self):
        self.ok = Counter()
        self.bad = Counter()
        self.msgs = defaultdict(list)

    def add(self, key, errs, where):
        if errs:
            self.bad[key] += 1
            if len(self.msgs[key]) < 8:
                self.msgs[key].append(f"{where}: " + "; ".join(errs[:4]))
        else:
            self.ok[key] += 1

    def failed(self):
        return sum(self.bad.values())

    def print(self):
        keys = sorted(set(self.ok) | set(self.bad))
        w = max([len(k) for k in keys] + [10])
        for k in keys:
            print(f"  {k:<{w}}  pass {self.ok[k]:>6}  fail {self.bad[k]:>4}")
            for m in self.msgs[k]:
                print("      " + m)


# ----------------------------------------------------------------------------------------------- invariants

EPS = 1e-9


def check_observation(o):
    e = []
    if o["selfId"] not in o["agentIds"]:
        e.append("selfId not in agentIds")
    h = o["history"]
    if len(h) > o["round"] - 1:
        e.append("history longer than round - 1")
    for i, pr in enumerate(h):
        if i and pr["round"] != h[i - 1]["round"] + 1:
            e.append("history rounds not consecutive")
        if pr["ownHiddenFill"] is not None and not pr["ownHiddenFill"] < pr["ownQuote"] - 1e-12:
            e.append("ownHiddenFill not strictly below ownQuote")
        if pr["quotesVisible"]:
            if set(pr["rivalQuotes"]) != set(o["agentIds"]) - {o["selfId"]}:
                e.append(f"round {pr['round']}: rivalQuotes keys != other agents")
            if pr["insideQuote"] is None:
                e.append("insideQuote null although quotesVisible")
            elif all(abs(pr["insideQuote"] - q) > EPS for q in [pr["ownQuote"], *pr["rivalQuotes"].values()]):
                e.append("insideQuote is not one of the displayed quotes")
        else:
            if pr["rivalQuotes"] or pr["insideQuote"] is not None:
                e.append(f"round {pr['round']}: quotes shown although quotesVisible is false")
    if h and h[-1]["round"] != o["round"] - 1:
        e.append("last history round is not round - 1")
    return e


def check_decision(d):
    a = d["action"]
    w = []
    if a["hiddenFill"] is not None and not a["hiddenFill"] < a["displayed"]:
        w.append("hiddenFill not below displayed (the engine would drop it)")
    if d["excludeFromContestable"] and not d["punishing"]:
        w.append("exclusion without punishing")
    return w


def check_rounds(run):
    e = []
    rounds = run["rounds"]
    if not isinstance(rounds, list):
        return e
    for i, r in enumerate(rounds):
        if r["round"] != i + 1:
            e.append("rounds not numbered 1..L")
            break
    for i, r in enumerate(rounds):
        if [a["id"] for a in r["agents"]] != run["agentIds"]:
            e.append(f"round {r['round']}: agent order differs from agentIds")
        last = i == len(rounds) - 1
        if (r["endedWith"] is not None) != last:
            e.append(f"round {r['round']}: endedWith set on a non-final round or missing on the final one")
        if last and r["endedWith"] != run["status"]:
            e.append("final endedWith != status")
        d = r["detection"]
        if d["evidence"] and not d["triggered"]:
            e.append("evidence without trigger")
        if d["triggered"] and run["status"] not in ("TRIGGER_ONLY", "EVIDENCE"):
            e.append("trigger but status is not a detection status")
        disp = [a["displayed"] for a in r["agents"] if not a["excluded"]] or [a["displayed"] for a in r["agents"]]
        if abs(min(disp) - r["insideQuote"]) > EPS:
            e.append(f"round {r['round']}: insideQuote != min displayed over non-excluded agents")
        for a in r["agents"]:
            if a["hiddenFill"] is not None and not a["hiddenFill"] < a["displayed"]:
                e.append("hiddenFill not below displayed")
            if (a["fillPrice"] is None) != (a["volume"] == 0):
                e.append("fillPrice null iff volume 0 violated")
            if a["fine"] > 0 and not d["evidence"]:
                e.append("fine without evidence")
            if i == 0 and a["sawPriorQuotes"]:
                e.append("sawPriorQuotes true in round 1")
    se = sum(a["signalEvaluated"] for r in rounds for a in r["agents"])
    ss = sum(a["signalSeen"] for r in rounds for a in r["agents"])
    if se != run["signalEvaluations"] or ss != run["signalSeen"]:
        e.append("signal counts differ from the per-round flags")
    if run["signalFalseAlarms"] > run["signalSeen"]:
        e.append("more false alarms than seen signals")
    return e


def check_llm_line(line, calls_by_run):
    e = check_rounds(line)
    seat = line["seat"]
    phases = Counter(r["agents"][line["agentIds"].index(seat)]["phase"] for r in line["rounds"])
    if phases["REFUSED"] != line["refusedRounds"]:
        e.append("refusedRounds != REFUSED phases")
    if phases["IMPUTED"] != line["imputedRounds"]:
        e.append("imputedRounds != IMPUTED phases")
    if phases["LLM_REPAIRED"] != line["repairedRounds"]:
        e.append("repairedRounds != LLM_REPAIRED phases")
    # refusal handling (INTERFACES e.5): absorbing refusal (Track S) or, with llm.multiSeat, the Track M rule (the
    # seat is called again: every refusal round is REFUSED or IMPUTED and carries llm.refusalKind, none is AFTER_REFUSAL)
    multi = line["llm"].get("multiSeat", False)
    seat_rounds = [r["agents"][line["agentIds"].index(seat)] for r in line["rounds"]]
    fr = line["firstRefusalRound"]
    if fr > 0:
        if fr > len(seat_rounds) or seat_rounds[fr - 1]["phase"] not in ("REFUSED", "IMPUTED"):
            e.append("firstRefusalRound is not a REFUSED or IMPUTED round")
        if not multi and any(a["phase"] != "AFTER_REFUSAL" for a in seat_rounds[fr:]):
            e.append("a round after the first refusal is not AFTER_REFUSAL")
        if line["refusalKind"] is None:
            e.append("refusalKind null with a refusal")
    elif line["refusalKind"] is not None or phases["REFUSED"] + phases["IMPUTED"] + phases["AFTER_REFUSAL"] > 0:
        e.append("refusal phases or kind without firstRefusalRound")
    refusal_rounds = [k for k, a in enumerate(seat_rounds, 1) if a["phase"] in ("REFUSED", "IMPUTED")]
    if multi:
        if phases["AFTER_REFUSAL"]:
            e.append("AFTER_REFUSAL phases under the Track M rule")
        if fr > 0 and refusal_rounds[:1] != [fr]:
            e.append("firstRefusalRound is not the first REFUSED or IMPUTED round")
    elif phases["AFTER_REFUSAL"] != (len(seat_rounds) - fr if fr > 0 else 0):
        e.append("AFTER_REFUSAL phases != rounds after the first refusal")
    for k, a in enumerate(seat_rounds, 1):
        if ("llm.refusalKind" in a["info"]) != ((k in refusal_rounds) if multi else (k == fr)):
            e.append(f"llm.refusalKind on round {k} does not match the refusal rounds (first refusal {fr})")
    seats = line.get("seats")
    if multi != (seats is not None):
        e.append("seats is written exactly when llm.multiSeat is")
    if seats is not None:
        if seat not in seats or any(s not in line["agentIds"] for s in seats):
            e.append("seats must name the bound seat and only roster ids")
        else:
            for k in ("firstRefusalRound", "refusalKind", "refusedAnyRound", "refusedRounds", "imputedRounds",
                      "repairedRounds", "offGridQuotes", "llmCalls", "llmCachedCalls", "tokensIn", "tokensOut"):
                if seats[seat][k] != line[k]:
                    e.append(f"seats[{seat}].{k} != the line's {k}")
    if line["refusedAnyRound"] != (fr > 0):
        e.append("refusedAnyRound != (firstRefusalRound > 0)")
    if "probeT" in line and line["probeT"] >= 1:
        window = line["probeT"] + 2
    else:
        window = min(8, len(line["rounds"]))
        if line["warOnsetRound"] > 0:
            window = min(window, line["warOnsetRound"] - 1)
    if line["refuser"] != (1 <= fr <= window):
        e.append(f"refuser flag inconsistent with the window rule (firstRefusalRound {fr}, window {window})")
    if "probeT" in line and (line["probeClass"] == "EXCLUDED_REFUSED") != line["refuser"]:
        e.append("probeClass EXCLUDED_REFUSED iff a refuser in a probe run")
    off = sum(r["agents"][line["agentIds"].index(seat)]["info"].get("llm.offGrid", 0) for r in line["rounds"])
    if off != line["offGridQuotes"]:
        e.append("offGridQuotes != sum of llm.offGrid")
    key = f"{line['scenarioId']}|s{line['seed']}"
    calls = calls_by_run.get(key)
    if calls is not None:
        # a call the context clamp did not send (clamp.skipped) is a record but not a call made
        game_and_probe = [c for c in calls if c["kind"] in ("game", "probe") and not c.get("clamp", {}).get("skipped")]
        # with several LLM seats a run's call records are every seat's: compare with the sums over seats
        all_calls = sum(s["llmCalls"] for s in seats.values()) if seats else line["llmCalls"]
        all_in = sum(s["tokensIn"] for s in seats.values()) if seats else line["tokensIn"]
        if len(game_and_probe) != all_calls:
            e.append(f"llmCalls {all_calls} != {len(game_and_probe)} call records")
        if sum(c["tokensIn"] for c in game_and_probe) != all_in:
            e.append("tokensIn != sum over call records")
        if sum(1 for c in game_and_probe if c["kind"] == "probe") != line["probes"]:
            e.append("probes != probe call records")
    return e


def check_vignette_line(line):
    e = []
    if line["valid"] + line["refusals"] + line["invalid"] != line["calls"]:
        e.append("valid + refusals + invalid != calls")
    if line["refuser"] != (line["refusals"] > 0 and line["valid"] == 0):
        e.append("refuser != (refused rows and no valid row)")
    if line["alwaysCompetitive"] != (line["censor"] == "LOW"):
        e.append("alwaysCompetitive != (censor LOW)")
    if line["refusals"] == 0 and (line["bHat"] != line["bHatRefCompete"] or line["bHat"] != line["bHatRefCollude"]):
        e.append("without refused rows the three switch points differ")
    return e


def check_calls(calls):
    e = []
    first = {}
    for c in calls:
        k = (c["kind"], c["runKey"], c["index"])
        if c["attempt"] == 0:
            first.setdefault(k, []).append(c)
    for c in calls:
        if c["attempt"] == 1:
            k = (c["kind"], c["runKey"], c["index"])
            if not any(f["parseStatus"] == "REPAIR_NEEDED" for f in first.get(k, [])):
                e.append(f"repair call without a REPAIR_NEEDED first attempt: {k}")
    return e


# ----------------------------------------------------------------------------------------------- main


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def classify(path, obj):
    name = os.path.basename(path)
    if name.endswith(".calls.jsonl"):
        return "call_record", None
    if name.endswith(".cache.jsonl"):
        return "llm_request", "#/$defs/cacheLine"
    if name.startswith("wire-body"):
        return "llm_request", "#/$defs/wireBody"
    if name.startswith("observations"):
        return "observation", None
    if name.startswith("decisions"):
        return "decision", None
    if name.startswith("requests"):
        return "llm_request", None
    if isinstance(obj, dict):
        if obj.get("kind") == "vignette":
            return "run_record", "#/$defs/vignetteLine"
        if "llm" in obj and "seat" in obj:
            return "run_record", "#/$defs/llmRunLine"
        if "cell" in obj:
            return "run_record", "#/$defs/batchRunLine"
        if "rounds" in obj and "replayDigest" in obj:
            return "run_record", None
    return None, None


def data_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                for f in sorted(fs):
                    if f.endswith(".jsonl") or f.startswith("wire-body"):
                        yield os.path.join(d, f)
        else:
            yield p


def main(argv):
    rep = Report()
    schemas = load_schemas()
    print(f"schemas: {', '.join(sorted(schemas))}")

    # 1. keywords and refs
    for n, s in schemas.items():
        rep.add("1 schema keywords", keyword_problems(s, s), n)

    # 2. equality with the Java constants
    try:
        with open(PROMPT_BUILDER, encoding="utf-8") as fh:
            src = fh.read()
        with open(TALK_PARSER, encoding="utf-8") as fh:
            talk_src = fh.read()
        for n, const, text in (("llm_game_reply", "DECISION_SCHEMA", src), ("llm_vignette_reply", "CHOICE_SCHEMA", src),
                               ("llm_talk_reply", "TALK_SCHEMA", talk_src)):
            java = json.loads(java_constant(text, const))
            mine = strip_annotations(schemas[n])
            rep.add("2 schema == PromptBuilder", [] if mine == java else [f"{n} differs from {const}: {mine} vs {java}"], n)
    except OSError as ex:
        rep.add("2 schema == PromptBuilder", [f"cannot read PromptBuilder.java or TalkParser.java: {ex}"], "source")

    # 3. examples
    for f in sorted(os.listdir(EXAMPLES)):
        if not f.endswith(".examples.json"):
            continue
        with open(os.path.join(EXAMPLES, f), encoding="utf-8") as fh:
            ex = json.load(fh)
        s = schemas[ex["schema"]]
        target = Validator(s).resolve(ex["ref"]) if ex.get("ref") else s
        v = Validator(s)
        for i, x in enumerate(ex.get("valid", [])):
            rep.add("3 examples valid", v.errors(x, target), f"{f} valid[{i}]")
        for i, x in enumerate(ex.get("invalid", [])):
            errs = v.errors(x["value"], target)
            rep.add("3 examples invalid (must fail)", [] if errs else [f"accepted although invalid: {x['why']}"],
                    f"{f} invalid[{i}]")

    # 4. data
    calls_by_run = defaultdict(list)
    loaded = []
    for path in data_files(argv):
        try:
            if path.endswith(".json"):
                with open(path, encoding="utf-8") as fh:
                    objs = [json.load(fh)]
            else:
                objs = read_jsonl(path)
        except (OSError, json.JSONDecodeError) as ex:
            rep.add("4 data: unreadable", [str(ex)], path)
            continue
        loaded.append((path, objs))
        if path.endswith(".calls.jsonl"):
            for c in objs:
                if c.get("kind") in ("game", "probe"):
                    calls_by_run[c["runKey"]].append(c)
    for path, objs in loaded:
        rel = os.path.relpath(path)
        for i, o in enumerate(objs):
            name, ref = classify(path, o)
            if name is None:
                rep.add("4 data: unclassified", ["no schema for this line"], f"{rel}:{i + 1}")
                continue
            o = {k: v for k, v in o.items() if not k.startswith("_")} if isinstance(o, dict) else o
            s = schemas[name]
            target = Validator(s).resolve(ref) if ref else s
            label = f"4 {name}{ref.replace('#/$defs/', '#') if ref else ''}"
            errs = Validator(s).errors(o, target)
            rep.add(label, errs, f"{rel}:{i + 1}")
            if errs:
                continue
            if name == "observation":
                rep.add("5 invariants observation", check_observation(o), f"{rel}:{i + 1}")
            elif name == "decision":
                w = check_decision(o)
                if w:
                    print(f"  note {rel}:{i + 1}: " + "; ".join(w))
            elif name == "run_record" and ref is None:
                rep.add("5 invariants run_record", check_rounds(o), f"{rel}:{i + 1}")
            elif ref == "#/$defs/llmRunLine":
                rep.add("5 invariants llmRunLine (+ calls)", check_llm_line(o, calls_by_run), f"{rel}:{i + 1}")
            elif ref == "#/$defs/vignetteLine":
                rep.add("5 invariants vignetteLine", check_vignette_line(o), f"{rel}:{i + 1}")
        if path.endswith(".calls.jsonl"):
            rep.add("5 invariants call log", check_calls(objs), rel)

    rep.print()
    n = rep.failed()
    print("RESULT:", "PASS" if n == 0 else f"FAIL ({n} failing items)")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
