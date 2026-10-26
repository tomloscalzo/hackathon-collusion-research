#!/usr/bin/env python3
"""Final quality-check report for a finished Track M run (unit U3; standard library only).

Usage: python -X utf8 tools/trial/qc_report.py <tables_dir> [--out qc_report.md] [--threshold 0.05] [--window N] [--no-html]
<tables_dir> is the output of collect.py (trials.csv, refusals.csv, clamp.csv, clamp_summary.csv). Writes one Markdown page
(default <tables_dir>/qc_report.md, LF endings) and, unless --no-html, an html twin next to it (tools/md2html.py).

The page lists, per arm: trials by status (failures), refusals, parse failures (imputed), truncations, imputed quotes, the
context-window clamp statistics, and a clearly labelled list of every trial with a clamped or skipped call (the calls
themselves: round, seat, call type, requested -> granted max_tokens). A call is "skipped" when the clamp could not leave
min_tokens of room: it was not sent and was imputed as TRUNCATED (INTERFACES e.5, Context clamp).

Severity (the owner's final quality check: "if severe for an arm or scenario we can rerun those with larger capacity"):
an arm, and each arm x penalty_point (scenario cell) x thinking mode, is SEVERE when its clamp_share (clamped calls / model
calls) is >= --threshold (default 0.05) or it has ANY skipped call. Rerun the SEVERE rows with a larger context window.
A trial's window is, in order: --window N when given (an explicit override), trials.csv context_window (the grid's per-profile window, unit U11, so a 32k arm is checked
against 32,768 automatically), the window of its clamp.csv rows, else the largest clamp.csv window. A trial whose
longest prompt exceeds its window is marked ("overflow allowed but recorded"). Arms whose window is larger than the standard
16,384 (the 32k introspection arms) also get their own section that lists EVERY such trial with window, longest prompt, clamped
and skipped calls, whether or not anything overflowed. That section keys on trials.csv context_window (the grid's
column), so a run collected without grid_row.json is checked only through the overflow marks above.

The page ends with the competitiveness section (competitiveness.competitiveness_section from unit U16, called per arm and
floor over rounds.csv; the tick is competitiveness.DEFAULT_TICK); an error there is reported in the page, never fatal.
Exit status: 0 always when the report was written (the flags are in the page); 2 usage or missing tables.
"""
import csv
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
DEFAULT_THRESHOLD = 0.05
STANDARD_WINDOW = 16384   # the 16k deploy profiles; a trial with a larger context_window gets its own report section (unit U11)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def severe(clamped, calls, skipped, threshold):
    """True when the clamp share reaches the threshold or any call was skipped."""
    share = clamped / calls if calls else 0.0
    return skipped > 0 or (clamped > 0 and share >= threshold)


def table(head, rows):
    if not rows:
        return "_none_\n"
    esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(v) for v in r) + " |" for r in rows]) + "\n"


def fmt_share(x):
    return "%.1f%%" % (100 * x)


def build(tables, threshold=DEFAULT_THRESHOLD, window=None):
    """The Markdown text for the tables in the directory `tables`."""
    t = Path(tables)
    trials, refusals = read_csv(t / "trials.csv"), read_csv(t / "refusals.csv")
    clamp = read_csv(t / "clamp.csv") if (t / "clamp.csv").exists() else []
    summ = read_csv(t / "clamp_summary.csv") if (t / "clamp_summary.csv").exists() else []
    windows = [num(c["window"]) for c in clamp if c.get("window")]
    win = window or (max(windows) if windows else None)
    arms = sorted({r["arm"] for r in trials})
    out = ["# Quality check report", "",
           "Severity threshold: a clamp share of %s of model calls, or any skipped call (set with `--threshold`). %d trials, %d arms." % (
               fmt_share(threshold), len(trials), len(arms)), ""]

    # severity: per arm and per arm x cell x mode
    by_arm = {}
    for r in summ:
        a = by_arm.setdefault(r["arm"], [0, 0, 0])
        a[0] += int(num(r["clamped"]))
        a[1] += int(num(r["calls"]))
        a[2] += int(num(r["skipped"]))
    out += ["## Severity flags (rerun candidates)", ""]
    flagged = [(a, v) for a, v in sorted(by_arm.items()) if severe(v[0], v[1], v[2], threshold)]
    cells = [r for r in summ if severe(int(num(r["clamped"])), int(num(r["calls"])), int(num(r["skipped"])), threshold)]
    if not flagged and not cells:
        out += ["No arm or scenario is severe: no cell has a clamp share of %s or more and no call was skipped." % fmt_share(threshold), ""]
    else:
        out += ["**SEVERE arms (rerun with a larger context window):**", "",
                table(["arm", "clamped calls", "model calls", "clamp share", "skipped calls"],
                      [(a, v[0], v[1], fmt_share(v[0] / v[1]) if v[1] else "", v[2]) for a, v in flagged]), "",
                "**SEVERE scenarios (arm x penalty point x thinking mode):**", "",
                table(["arm", "penalty_point", "thinking", "clamped", "calls", "clamp share", "skipped", "trials affected"],
                      [(r["arm"], r["penalty_point"], r["thinking"], r["clamped"], r["calls"],
                        fmt_share(num(r["clamp_share"])), r["skipped"], "%s of %s" % (r["trials_affected"], r["trials"])) for r in cells]), ""]

    # failures, refusals, imputations, truncations per arm
    out += ["## Failures, refusals, imputations and truncations per arm", ""]
    rows = []
    for a in arms:
        ts = [r for r in trials if r["arm"] == a]
        st = {s: sum(1 for r in ts if r["status"] == s) for s in ("done", "failed", "incomplete", "corrupt")}
        rf = [r for r in refusals if r["arm"] == a]
        tot = lambda col: sum(int(num(r.get(col))) for r in rf)
        calls = tot("calls") - tot("inreply_calls")   # an in-reply question rides in a quote call already counted
        qd = sum(int(num(r["refusals"])) for r in rf if r["kind"] == "question")   # U10: question declines apart (never toward the pause)
        rows.append((a, len(ts), st["done"], st["failed"], st["incomplete"], st["corrupt"], tot("refusals") - qd, qd, tot("parse_failures"),
                     tot("truncations"), sum(int(num(r["imputed"])) for r in ts),
                     fmt_share(tot("truncations") / calls) if calls else ""))
    out += [table(["arm", "trials", "done", "failed", "incomplete", "corrupt", "refusals", "question declines", "parse failures", "truncations",
                   "imputed quotes", "truncation share of calls"], rows), "",
            "Refusals, parse failures and truncations follow collect.py (`derive.call_failure`); a skipped clamp call is a truncation "
            "(imputed, never a refusal). The 5% truncation stop of the runner counts them too. `refusals` are talk and quote refusals "
            "(they count toward the 40% arm pause); `question declines` are listed apart below.", ""]

    # introspection-question declines (unit U15 fed-back question calls, unit U10 in-reply answers), apart from the refusals
    out += question_declines(refusals, arms)

    # clamp stats
    out += ["## Context-window clamp statistics", ""]
    if not summ:
        out += ["_clamp_summary.csv is absent or empty (tables made before unit U3 have no clamp data)._", ""]
    else:
        out += [table(["arm", "penalty_point", "thinking", "trials", "model calls", "clamped", "share", "median reduction", "worst reduction",
                       "skipped", "longest prompt (tokens)", "trials affected"],
                      [(r["arm"], r["penalty_point"], r["thinking"], r["trials"], r["calls"], r["clamped"], fmt_share(num(r["clamp_share"])),
                        r["median_reduction"], r["worst_reduction"], r["skipped"], r["max_prompt_tokens"], r["trials_affected"]) for r in summ]),
                "Reduction = requested max_tokens minus granted (tokens); a skipped call has granted 0. Share = clamped events / talk, quote and question events.", ""]

    # affected trials
    out += ["## Trials with clamped or skipped calls (explicit list)", ""]
    hit = [r for r in trials if int(num(r.get("clamped_calls"))) > 0 or int(num(r.get("skipped_calls"))) > 0]
    own = {}
    for c in clamp:
        if c.get("window"):
            own[c["trial_id"]] = max(own.get(c["trial_id"], 0), num(c["window"]))
    tw = lambda r: window or num(r.get("context_window")) or own.get(r["trial_id"]) or win
    over = [r for r in trials if tw(r) and num(r.get("max_prompt_tokens"), -1) > tw(r)]
    if not hit and not over:
        out += ["No trial had a clamped or skipped call%s." % (" or a prompt above its window" if win or any(tw(r) for r in trials) else ""), ""]
    for a in arms:
        mine = [r for r in hit + [x for x in over if x not in hit] if r["arm"] == a]
        if not mine:
            continue
        out += ["### Arm %s: %d trial(s) affected" % (a, len(mine)), ""]
        out += [table(["trial", "thinking", "clamped calls", "skipped calls", "longest prompt (tokens)", "prompt above window"],
                      [(r["trial_id"], r["thinking"], r["clamped_calls"], r["skipped_calls"], r["max_prompt_tokens"],
                        "yes (window %d)" % tw(r) if tw(r) and num(r.get("max_prompt_tokens"), -1) > tw(r) else "") for r in mine]), ""]
        calls = [c for c in clamp if c["arm"] == a]
        if calls:
            out += ["Calls (SKIPPED = not sent, imputed as truncated):", "",
                    table(["trial", "round", "seat", "call", "attempt", "requested -> granted", "estimated prompt", "real tokens_in", "skipped"],
                          [(c["trial_id"], c["round"], c["seat"], c["call_type"], c["attempt"], "%s -> %s" % (c["requested_max_tokens"], c["granted_max_tokens"]),
                            c["est_prompt_tokens"], c["real_tokens_in"], "SKIPPED" if str(c["skipped"]) == "True" else "") for c in calls]), ""]
    if win or any(tw(r) for r in trials):
        out += ["Window used for the overflow mark: %s. A prompt above it is allowed (some arms run with a bigger window than the model serves) but recorded here." % (
            ", ".join("%d tokens" % w for w in sorted({int(tw(r)) for r in trials if tw(r)})) or "%d tokens" % win), ""]

    # arms with a window above the standard one (unit U11: the 32k introspection arms): every trial, explicitly
    big = [r for r in trials if num(r.get("context_window")) > STANDARD_WINDOW]
    out += ["## Arms with an extended context window (explicit list)", ""]
    if not big:
        out += ["No trial ran with a window above %d tokens." % STANDARD_WINDOW, ""]
    else:
        out += ["These arms ran on the larger-window deployment (overflow of even that window is allowed, not capped, and recorded). "
                "Every trial is listed with its longest prompt; OVERFLOW marks a prompt above the window.", ""]
        for a in sorted({r["arm"] for r in big}):
            mine = [r for r in big if r["arm"] == a]
            bad = [r for r in mine if num(r.get("max_prompt_tokens"), -1) > num(r["context_window"]) or int(num(r.get("skipped_calls"))) > 0
                   or int(num(r.get("clamped_calls"))) > 0]
            out += ["### Arm %s: %d trial(s), %d with an overflow, clamped or skipped call" % (a, len(mine), len(bad)), "",
                    table(["trial", "thinking", "window", "longest prompt (tokens)", "clamped calls", "skipped calls", "overflow"],
                          [(r["trial_id"], r["thinking"], r["context_window"], r["max_prompt_tokens"], r["clamped_calls"], r["skipped_calls"],
                            "OVERFLOW" if num(r.get("max_prompt_tokens"), -1) > num(r["context_window"]) else "") for r in mine]), ""]

    out += competitiveness(tables)
    out += intent(tables)
    return "\n".join(out).rstrip("\n") + "\n"


def question_declines(refusals, arms):
    """Section for the introspection questions that were declined: fed/post question calls refused (unit U15) and in-reply answers
    that were absent or refused (unit U10: refusal_kind ABSENT / MODEL_DECLINE on the question row of refusals.csv)."""
    rows = []
    for a in arms:
        for r in refusals:
            if r["arm"] == a and r["kind"] == "question" and num(r["calls"]) > 0:
                n, calls = int(num(r["refusals"])), int(num(r["calls"]))
                rows.append((a, r["thinking"], r["trials"], calls, n, fmt_share(n / calls), r.get("by_refusal_kind", ""), r.get("patterns", "")))
    out = ["## Question declines", ""]
    if not rows:
        return out + ["_No introspection-question calls or in-reply answers in these tables._", ""]
    out += [table(["arm", "thinking", "trials", "question calls", "declines", "decline share", "by kind", "patterns"], rows), "",
            "A question decline is a refused question call (separate call, fed or post) or an in-reply answer (saved-only arms R2s/R3s) that is "
            "absent (ABSENT) or an assistant-style refusal (MODEL_DECLINE). Declines are reported here, never as refusals: they do not count "
            "toward the 40% arm pause and are not in the `refusals` column. An in-reply field of a quote that itself failed is not a question call.", ""]
    return out


def competitiveness(tables):
    """Lines of the competitiveness section (unit U16): per arm and competitive_price (the floor), the per-game lines of
    competitiveness.competitiveness_section over rounds.csv. Trials without a competitive_price are named, not scored.
    Never fatal: an error is reported in the page."""
    t = Path(tables)
    if not (t / "rounds.csv").is_file():
        return []
    try:
        import competitiveness
        rounds = {}
        for r in read_csv(t / "rounds.csv"):
            rounds.setdefault(r["trial_id"], []).append(r)
        groups, unscored = {}, []
        for tr in read_csv(t / "trials.csv"):
            if tr["status"] == "corrupt" or tr["trial_id"] not in rounds:
                continue
            if tr.get("competitive_price", "") == "":
                unscored.append(tr["trial_id"])
            else:
                groups.setdefault((tr["arm"], float(tr["competitive_price"])), {})[tr["trial_id"]] = rounds[tr["trial_id"]]
        out = ["## Competitiveness (unit U16)", ""]
        for (arm, floor), games in sorted(groups.items()):
            out += ["```", competitiveness.competitiveness_section(games, floor, title="Arm %s" % arm), "```", ""]
        if unscored:
            out += ["Not scored (no competitive_price in params.json): %s" % ", ".join(sorted(unscored)), ""]
        return [""] + out if groups or unscored else []
    except Exception as e:  # never fatal: the clamp and failure parts matter more
        return ["", "## Competitiveness (unit U16)", "", "_competitiveness section failed: %s_" % e, ""]


def intent(tables):
    """Intent-class section (unit U19, intent_classes.intent_section) when rounds.csv exists (no grid or baseline: D level from the arm name; run intent_classes.py for those options); never fatal."""
    t = Path(tables)
    try:
        import intent_classes
        return intent_classes.intent_section(t) if (t / "rounds.csv").is_file() else []
    except Exception as e:
        return ["", "## Intent classes (unit U19)", "", "_intent section failed: %s_" % e, ""]


def main(argv):
    args, opts, i = [], {"--out": None, "--threshold": str(DEFAULT_THRESHOLD), "--window": None}, 1
    html_twin = True
    while i < len(argv):
        a = argv[i]
        if a == "--no-html":
            html_twin = False
        elif a in opts and i + 1 < len(argv):
            opts[a] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            print("unknown or incomplete option %s" % a, file=sys.stderr)
            return 2
        else:
            args.append(a)
        i += 1
    if len(args) != 1:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    try:
        threshold = float(opts["--threshold"])
        window = int(opts["--window"]) if opts["--window"] else None
    except ValueError:
        print("--threshold must be a number and --window an integer", file=sys.stderr)
        return 2
    d = Path(args[0])
    for need in ("trials.csv", "refusals.csv"):
        if not (d / need).is_file():
            print("%s not found in %s (run collect.py first)" % (need, d), file=sys.stderr)
            return 2
    md = build(d, threshold, window)
    out = Path(opts["--out"]) if opts["--out"] else d / "qc_report.md"
    out.write_text(md, encoding="utf-8", newline="\n")
    print(out)
    if html_twin:
        try:
            twin = out.with_suffix(".html")
            r = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve().parents[1] / "md2html.py"), str(out), str(twin)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip()[-200:])
            print(twin)
        except Exception as e:  # the Markdown is the report; the twin is a convenience
            print("warning: no html twin (%s)" % e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
