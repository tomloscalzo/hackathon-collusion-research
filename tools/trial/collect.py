#!/usr/bin/env python3
"""Collect many trial directories into flat tables (standard library only; scope sections 14.1 and 4.6).

Usage: python -X utf8 tools/trial/collect.py <trials_root> <out_dir> [--include-pilot] [--rerun-root DIR]... [--include-superseded]
Trials whose grid_row.json says pilot (throwaway pilot rows, make_grid pilot column) are left out of every table unless
--include-pilot is given; trials.csv carries a pilot column (1 or empty), so analysis of an included set can drop them again.
Truncation reruns (unit N3, trunc_rerun.py): if <trials_root>/superseded.csv exists (original_id,rerun_id,reason), each superseded
original (a thinking-on game with a call cut at the token limit) is left out of every table and its rerun (trial id = original id +
`__x32k`, run in a separate root) is collected in its place: the rerun's arm, penalty point, wording, seed and thinking come from its
params.json or, failing that, from its directory name with the `__x32k` suffix stripped, so it pairs and groups under the original's
cell. Pass the rerun root(s) with --rerun-root (repeatable; a rerun root nested inside <trials_root> is found by itself). An original
whose rerun was not collected or is not DONE stays in (warning on stderr), and a `__x32k` trial not listed in superseded.csv is left
out (warning), so a game is never counted twice. --include-superseded is the sensitivity analysis: it includes the superseded
originals and excludes their reruns, again so a game is never counted twice. Without superseded.csv and --rerun-root nothing changes.
Finds every directory under <trials_root> that holds an events.jsonl and writes, LF-terminated and sorted so a re-run
gives identical files:
  trials.csv    one row per trial: trial_id, arm, thinking (on|off|""), model, penalty_point, wording, seed, status,
                then the summary measures computed from the events with derive.build_summary: rounds,
                collusion_level, time_to_high_price, undercuts, punishments, refusals (quote and talk only), question_declines (refused introspection-question calls, apart), parse_failures, truncations,
                imputed, truncated_talk, word_capped_talk, messages, profit_total (refusals, parse_failures and truncations as in refusals.csv;
                imputed counts imputed quotes, so an UNPARSEABLE quote is in both imputed and parse_failures)
  rounds.csv    one row per quote event: trial_id, round, seat, quote, profit, market_price, winner, parse_status
                (the quote event's outcome; OK when absent), refusal_kind, imputed, self_report, self_report_name,
                self_report_kind (U8, option reply_extra: the seat's answer to the extra field after the quote, or last with position last, e.g. a 1-5 score;
                self_report_name = the field's name such as conflict_score, self_report_kind = integer|text; all three empty when
                the game has no extra field, self_report alone empty when the reply gave no readable value)
  questions.csv one row per question event (C9.2): trial_id, round, seat, question (name), mode (fed|post; U10: inreply), words,
                answer, truncated, parse_status, refusal_kind; name and mode fall back to the draw key
                `question|<name>|fed|...`. U10, mode `inreply` (the saved-only arms R2s/R3s): one row per quote event whose extra reply
                field is text (self_report_kind text; params.json reply_extra.text_name `<name>_inreply` gives question <name>), the
                answer being self_report; parse_status is OK, ABSENT (no readable answer) or REFUSED (derive.INREPLY_DECLINE), refusal_kind ""
                | ABSENT | MODEL_DECLINE. An ABSENT or REFUSED answer is a question decline (trials.csv question_declines, the refusals.csv
                `question` row; counts_toward_pause 0), and each answered, absent or refused field counts as one question call there.
                A quote that itself failed (refused, imputed, truncated) asked no question and has no row.
  refusals.csv  the refusal table (C9.2; scope 4.5, reported prominently): one row per arm x thinking x kind in
                (talk, quote, question): trials, calls, refusals, refusal_rate, parse_failures, truncations,
                counts_toward_pause (0 for the question row: question declines never pause an arm, U15), trials_with_refusal, by_refusal_kind (a JSON object, {"MODEL_DECLINE":1,"MODEL_TEXT":2}) and patterns (the
                matched refusal text, from the event field `refusal_pattern`, counted in the same JSON form; "(unrecorded)"
                when absent). One definition, derive.call_failure (quality review Q3): a call is refused when it has a
                refusal_kind other than UNPARSEABLE / TRUNCATED, or outcome REFUSED without a kind ("(none)"); refusal_kind
                UNPARSEABLE counts as a parse failure and TRUNCATED as a truncation (imputed rounds, never refusals).
                calls = events of that kind. imputed_rounds = played rounds with an imputed call (parse failure or
                truncation) of that kind (post-game questions excluded), played_rounds = the group's played rounds
                (rounds with a quote), imputed_round_share = their ratio (fix-imputed_visibility). Every arm x
                thinking x kind row is written, with zeros, so nothing is dropped silently. Corrupt trials count in no row.
  clamp.csv     one row per context_clamp event (unit U3; U2 writes them when the context-window clamp binds): trial_id, arm,
                thinking, penalty_point, round, seat, call_type, attempt, est_prompt_tokens, requested_max_tokens,
                granted_max_tokens, reduction (requested - granted; a skipped call has granted 0), skipped, real_tokens_in
                (tokens_in of the call event with the same draw_key, in order; empty when none), window, margin,
                min_tokens, draw_key. Header only when no trial clamped.
  clamp_summary.csv  one row per arm x penalty_point (the cell) x thinking (the mode): trials, calls (talk + quote + question
                events), clamped, clamp_share (clamped / calls; clamped = distinct talk, quote or question calls that were clamped, probes excluded), median_reduction, worst_reduction (requested - granted over clamped calls that were sent; skipped calls are counted in `skipped`),
                skipped (clamped calls that were not sent, imputed as TRUNCATED with context_clamp_skipped), max_prompt_tokens,
                trials_affected (trials with any clamped call). trials.csv also gets max_prompt_tokens (the larger of the
                real tokens_in and the estimate of any event of the trial), clamped_calls and skipped_calls, and context_window (U11: the trial's
                window from grid_row.json, blank when the grid has none; qc_report uses it per trial).
                Unit W2 (watchdog, option question_when): trials.csv also gets question_when and question_feedback (params.json; blank when the
                option is absent), asked_count (firm-rounds where the question was asked) and eligible_count (firm-rounds where the trigger could be
                evaluated: round >= 2 with a rival quote the round before), both counted from the watchdog_check events and blank for a trial with no
                question_when; rounds.csv gets wd_eligible, wd_triggered and wd_asked (1/0 from the same event, blank when none: round 1, or no
                question_when). A round that was not asked has no question event and no questions.csv row.
                Unit E1 (gpt-oss only, option empty_talk_as_done): trials.csv gets a last column empty_talk_done_count (talk turns whose empty
                reply was read as done, counted from the empty_reply_as_done events; 0 for such a trial with none, blank for the other trials),
                and only when at least one collected trial ran with the option; otherwise trials.csv is byte-identical to before.
                tools/trial/qc_report.py reads these tables.
  firms.csv     one row per trial x firm (U16, tools/trial/competitiveness.py): scored_rounds, competitive_rounds,
                noncompetitive_rounds and their percentages, always_competitive (1/0), first_stop_round (first round >= 2 not
                competitive), round1_class (floor|above_floor; round 1 is not in the shares). rounds.csv carries the matching
                `competitive_round` flag (1/0; blank for round 1 and when competitive_price is unknown). Target = lowest OTHER
                firm's quote the round before; competitive = undercut by >= 1 tick, or floor against a floor target. The floor is
                competitive_price, the tick params market.quoteIncrement (competitiveness.DEFAULT_TICK when absent)
  messages.csv  one row per talk event (done turns included, with empty text; trials.csv `messages`
                counts the talk events that are not done, C5.6): trial_id, round, turn, seat, words, truncated, word_capped, parse_status,
                refusal_kind, text (truncated = cut at the token limit, word_capped = cut at 150 words: derive.cut_kinds;
                truncated_talk and word_capped_talk in trials.csv count them). The text of an imputed turn (truncated
                or unparseable, which can hold private <think> reasoning) is never written: a placeholder such as
                `[imputed: truncated thinking]` with words 0 (derive.shown_text; questions.csv `answer` the same)
                (turn = the event's turn, else its 0-based position in the round's talk)

Guard (C9.2): the trials of one arm must all carry the same params.json `prompt_fingerprint` and `code_commit`;
otherwise collect raises MixedFingerprintError and writes nothing (the CLI exits 1). A trial missing a key counts as a
different value from trials that have it; if no trial of the arm has it, a warning goes to stderr. Both are columns
of trials.csv.

Reasoning (C9.3): rounds.csv, messages.csv and questions.csv end with a `reasoning` column, the event's `reasoning` text on
one line (empty when the event has none); analysis_r.py reads it for the thinks/says/does table. trials.csv carries
`competitive_price` and `collusive_price` from params.json (empty when absent); the analysis CLIs default their
--competitive/--collusive to them.

Trial metadata comes from params.json keys arm, thinking (true/false/"on"/"off", or settings.thinking), model (or
model_name, else the seats' model.served_name, else grid_row.json model_profile), penalty_point, wording, seed. A missing key falls back to the trial directory name
<arm>__p<point>__w<wording>__s<seed>[__t0|__t1] (optional __t suffix from make_grid.py = thinking fallback, 1 = on), else is left empty. status is "done" (a DONE file), "failed" (a FAILED file) or
"incomplete"; "corrupt" when events.jsonl or params.json cannot be parsed (the row is kept with empty measures and a
warning on stderr). The mixed prompt-fingerprint / code-commit guard is C9.2. Computed from the raw events, never from summary.json, so the tables cannot drift from the record.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import competitiveness  # noqa: E402  (U16)
import derive  # noqa: E402
import trunc_rerun  # noqa: E402  (N3: superseded.csv)

NAME_RE = re.compile(r"^(?P<arm>.+?)__p(?P<penalty_point>[^_]+)__w(?P<wording>[^_]+)__s(?P<seed>.+?)(?:__t(?P<thinking_suffix>[01]))?(?:__x32k)?$")
TRIAL_COLS = ["trial_id", "arm", "thinking", "model", "penalty_point", "wording", "seed", "status", "prompt_fingerprint", "code_commit", "competitive_price", "collusive_price", "rounds",
              "collusion_level", "time_to_high_price", "undercuts", "punishments", "refusals", "question_declines", "parse_failures", "truncations", "imputed",
              "truncated_talk", "word_capped_talk", "messages", "profit_total", "pilot",
              "max_prompt_tokens", "clamped_calls", "skipped_calls", "context_window", "question_when", "question_feedback", "asked_count", "eligible_count"]
EMPTY_TALK_COL = "empty_talk_done_count"   # unit E1: appended to trials.csv only when some trial ran with empty_talk_as_done (gpt-oss)
ROUND_COLS = ["trial_id", "round", "seat", "quote", "profit", "market_price", "winner", "parse_status",
              "refusal_kind", "imputed", "competitive_round", "self_report", "self_report_name", "self_report_kind",
              "wd_eligible", "wd_triggered", "wd_asked", "reasoning"]
FIRM_COLS = ["trial_id", "seat", "scored_rounds", "competitive_rounds", "noncompetitive_rounds", "competitive_pct",
             "noncompetitive_pct", "always_competitive", "first_stop_round", "round1_class"]
QUESTION_COLS = ["trial_id", "round", "seat", "question", "mode", "words", "answer", "truncated", "parse_status",
                 "refusal_kind", "reasoning"]
REFUSAL_COLS = ["arm", "thinking", "kind", "trials", "calls", "refusals", "refusal_rate", "parse_failures", "truncations",
                "imputed_rounds", "played_rounds", "imputed_round_share", "inreply_calls", "counts_toward_pause", "trials_with_refusal", "by_refusal_kind", "patterns"]
KINDS = ("talk", "quote", "question")
CLAMP_COLS = ["trial_id", "arm", "thinking", "penalty_point", "round", "seat", "call_type", "attempt", "est_prompt_tokens",
              "requested_max_tokens", "granted_max_tokens", "reduction", "skipped", "real_tokens_in", "window", "margin", "min_tokens", "draw_key"]
CLAMP_SUMMARY_COLS = ["arm", "penalty_point", "thinking", "trials", "calls", "clamped", "clamp_share", "median_reduction",
                      "worst_reduction", "skipped", "max_prompt_tokens", "trials_affected"]
GUARDED = ("prompt_fingerprint", "code_commit")


class MixedFingerprintError(ValueError):
    """An arm's trials carry more than one prompt fingerprint or code commit."""


MESSAGE_COLS = ["trial_id", "round", "turn", "seat", "words", "truncated", "word_capped", "parse_status", "refusal_kind", "text", "reasoning"]


def find_trials(root):
    """Trial directories (those with events.jsonl) under root, sorted by name."""
    found = sorted((p.parent for p in Path(root).rglob("events.jsonl")), key=lambda p: str(p))
    names = [p.name for p in found]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError("duplicate trial directory names under %s: %s" % (root, ", ".join(dup)))
    return sorted(found, key=lambda p: p.name)


def load_params(trial):
    f = Path(trial) / "params.json"
    return json.loads(f.read_text(encoding="utf-8-sig")) if f.exists() else {}


def _thinking(params):
    v = params.get("thinking", (params.get("settings") or {}).get("thinking") if isinstance(params.get("settings"), dict) else None)
    if v is True or v == "on":
        return "on"
    if v is False or v == "off":
        return "off"
    return ""


def is_pilot(trial):
    """True when the trial's grid_row.json (written by run_grid.py) marks it a throwaway pilot (grid column pilot = true)."""
    f = Path(trial) / "grid_row.json"
    try:
        return str(json.loads(f.read_text(encoding="utf-8-sig")).get("pilot", "")).strip().lower() in ("true", "1")
    except (OSError, ValueError, AttributeError):
        return False


def _grid_window(trial):
    """The trial's context window from grid_row.json (grid column context_window, unit U11), "" when absent."""
    try:
        v = json.loads((Path(trial) / "grid_row.json").read_text(encoding="utf-8-sig")).get("context_window")
    except (OSError, ValueError, AttributeError):
        return ""
    return int(v) if isinstance(v, (int, str)) and not isinstance(v, bool) and str(v).strip().isdigit() else ""


def trial_meta(trial, params):
    m = NAME_RE.match(Path(trial).name)
    from_name = m.groupdict() if m else {}
    def pick(key, *alts):
        for k in (key,) + alts:
            if params.get(k) is not None:
                return params[k]
        return from_name.get(key, "")
    if not _thinking(params) and from_name.get("thinking_suffix"):      # C1.1: the id's __t1 / __t0 suffix is the fallback
        params = dict(params, thinking="on" if from_name["thinking_suffix"] == "1" else "off")
    marks = {n: (Path(trial) / n).exists() for n in ("DONE", "FAILED")}
    return {"trial_id": Path(trial).name, "arm": pick("arm"), "thinking": _thinking(params),
            "model": _model(trial, params),
            "prompt_fingerprint": params.get("prompt_fingerprint") or "", "code_commit": params.get("code_commit") or "",
            "competitive_price": _price(params.get("competitive_price")), "collusive_price": _price(params.get("collusive_price")), "penalty_point": pick("penalty_point"),
            "wording": pick("wording"), "seed": pick("seed"),
            "status": "failed" if marks["FAILED"] else "done" if marks["DONE"] else "incomplete",
            "pilot": "1" if is_pilot(trial) else "", "context_window": _grid_window(trial)}


def _model(trial, params):
    """The trial's model: params.json model / model_name (the C4.3 writer always sets model); else the LLM seats'
    model.served_name as TrialParams writes it (distinct names joined with " | ", since served names contain "+"); else,
    for a corrupt or param-less trial, grid_row.json model_profile (run_grid; a profile name such as qwen3_14b); else ""."""
    for k in ("model", "model_name"):
        if isinstance(params.get(k), str) and params[k]:
            return params[k]
    seats = params.get("seats") if isinstance(params.get("seats"), list) else []
    names = sorted({str(s["model"]["served_name"]) for s in seats if isinstance(s, dict) and isinstance(s.get("model"), dict)
                    and s["model"].get("served_name")})
    if names:
        return " | ".join(names)
    try:
        row = json.loads((Path(trial) / "grid_row.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    return str(row.get("model_profile") or "") if isinstance(row, dict) else ""


def _price(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else ""


def _reasoning(e):
    """The event's reasoning text on one line ("" when absent); derive.py's docstring defines the field."""
    r = e.get("reasoning")
    return " ".join(r.split()) if isinstance(r, str) else ""


def _done(e):
    """A talk event that says done (C5.6: a refusal or an imputed talk reply is done too, parsed.done true)."""
    p = e.get("parsed")
    return isinstance(p, dict) and p.get("done") is True


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def trial_rows(trial):
    """Return (trial_row, round_rows, message_rows, question_rows, calls, refusals, failures) for one trial directory.
    calls maps kind -> number of events; refusals is a list of (kind, refusal_kind, pattern); failures maps
    (kind, "parse_failure" | "truncation") -> number of imputed parse failures (derive.call_failure), plus
    (kind, "imputed_rounds") -> played rounds with an imputed call of that kind and ("game", "played_rounds")."""
    try:
        params = load_params(trial)
        events = derive.read_events(Path(trial) / "events.jsonl")
    except ValueError as e:  # includes json.JSONDecodeError; a corrupt trial is kept visible, never dropped
        print("warning: trial %s is corrupt (%s); status=corrupt" % (Path(trial).name, e), file=sys.stderr)
        meta = trial_meta(trial, {})
        meta["status"] = "corrupt"
        return dict(meta), [], [], [], {}, [], {}
    meta = trial_meta(trial, params)
    tid = meta["trial_id"]
    summ = derive.build_summary(events, params)
    clamp = clamp_rows(events, meta)
    peaks = [e["tokens_in"] for e in events if _is_int(e.get("tokens_in"))] + [c["est_prompt_tokens"] for c in clamp if _is_int(c["est_prompt_tokens"])]
    market = {e["round"]: e for e in events if e.get("kind") == "market" and _is_int(e.get("round"))}
    wd = {(e.get("round"), e.get("seat")): e for e in events if e.get("kind") == "watchdog_check"}   # unit W2: question_when checks
    rounds, messages, questions, position = [], [], [], {}
    calls, refusals, failures, imputed_at = {}, [], {}, {}
    for e in events:
        r, kind = e.get("round"), e.get("kind")
        if not _is_int(r):
            continue
        if kind in KINDS:
            calls[kind] = calls.get(kind, 0) + 1
            cls = derive.call_failure(e.get("refusal_kind"), e.get("outcome"))
            if cls == "refusal":
                refusals.append((kind, str(e.get("refusal_kind") or "(none)"), " ".join(str(e.get("refusal_pattern") or "(unrecorded)").split())))
            elif cls:
                failures[(kind, cls)] = failures.get((kind, cls), 0) + 1
                if not (kind == "question" and _question_mode(e) == "post"):   # a post-game question does not change the game
                    imputed_at.setdefault(kind, set()).add(r)
        if kind == "question":
            p = e.get("parsed") if isinstance(e.get("parsed"), dict) else {}
            text = derive.shown_text(e, e["reply"] if isinstance(e.get("reply"), str) else (p["message"] if isinstance(p.get("message"), str) else ""))
            parts = str(e.get("draw_key", "")).split("|")
            dk = parts if parts[0] == "question" and len(parts) > 2 else []
            questions.append({"trial_id": tid, "round": r, "seat": e.get("seat", ""),
                              "question": e.get("name") or (dk[1] if dk else ""), "mode": _question_mode(e),
                              "words": 0 if derive.withheld(text) else derive.word_count(text), "answer": " ".join(text.split()),
                              "truncated": int(derive.cut_kinds(e)[0]),
                              "parse_status": e.get("outcome") or "OK", "refusal_kind": e.get("refusal_kind") or "", "reasoning": _reasoning(e)})
        if kind == "quote" and (st := derive.inreply_status(e)):   # U10: a saved-only question, a text field in the quote reply
            calls["inreply"] = calls.get("inreply", 0) + 1   # kept apart: the quote call is counted once in calls["quote"] (clamp totals)
            if st != "ANSWERED":   # a question decline: reported apart, never toward the arm pause (derive.is_inreply_decline)
                refusals.append(("question", "ABSENT" if st == "ABSENT" else "MODEL_DECLINE",
                                 "(no answer in the reply field)" if st == "ABSENT" else (derive.INREPLY_DECLINE.search(e["self_report"]).group(0).strip().lower())))
            text = e["self_report"] if st == "ANSWERED" or st == "REFUSED" else ""
            questions.append({"trial_id": tid, "round": r, "seat": e.get("seat", ""), "question": _inreply_name(params, e), "mode": "inreply",
                              "words": derive.word_count(text), "answer": " ".join(text.split()), "truncated": int(derive.cut_kinds(e)[0]),
                              "parse_status": "OK" if st == "ANSWERED" else st, "refusal_kind": "" if st == "ANSWERED" else ("ABSENT" if st == "ABSENT" else "MODEL_DECLINE"),
                              "reasoning": _reasoning(e)})
        if kind == "quote":
            m = market.get(r, {})
            rounds.append({"trial_id": tid, "round": r, "seat": e.get("seat", ""), "quote": _cell(e.get("quote")),
                           "profit": _num(_cell((m.get("profits") or {}).get(e.get("seat")))),
                           "market_price": _num(_cell(m.get("market_price"))), "winner": m.get("winner") or "",
                           "parse_status": e.get("outcome") or "OK", "refusal_kind": e.get("refusal_kind") or "",
                           "imputed": int(bool(e.get("imputed") or e.get("outcome") == "IMPUTED")),
                           "self_report": e["self_report"] if type(e.get("self_report")) in (int, float, str) else "",
                           "self_report_name": _text(e.get("self_report_name")), "self_report_kind": _text(e.get("self_report_kind")),
                           "reasoning": _reasoning(e),
                           **({"wd_eligible": int(bool(c.get("eligible"))), "wd_triggered": int(bool(c.get("triggered"))), "wd_asked": int(bool(c.get("asked")))}
                              if (c := wd.get((r, e.get("seat")))) else {})})
        elif kind == "talk":
            p = e.get("parsed") if isinstance(e.get("parsed"), dict) else {}
            token, word = derive.cut_kinds(e)
            text = p.get("message") if isinstance(p.get("message"), str) else (e.get("reply") if isinstance(e.get("reply"), str) else "")
            text = derive.shown_text(e, text)   # never the raw reply of an imputed turn (it can hold private <think> text)
            turn = e["turn"] if _is_int(e.get("turn")) else position.get(r, 0)
            position[r] = position.get(r, 0) + 1
            messages.append({"trial_id": tid, "round": r, "turn": turn, "seat": e.get("seat", ""),
                             "words": 0 if derive.withheld(text) else derive.word_count(text),
                             "truncated": int(token), "word_capped": int(word),
                             "parse_status": e.get("outcome") or "OK", "refusal_kind": e.get("refusal_kind") or "",
                             "text": " ".join(text.split()), "reasoning": _reasoning(e)})
    _mark_competitive(rounds, meta["competitive_price"], _tick(params))
    played = {x["round"] for x in rounds}   # rounds with a quote: the game's played rounds
    for kind, rs in imputed_at.items():
        failures[(kind, "imputed_rounds")] = len(rs & played)
    failures[("game", "played_rounds")] = len(played)
    seats = summ["seats"].values()
    row = dict(meta, rounds=summ["rounds"], collusion_level=_cell(summ["collusion_level"]),
               time_to_high_price=_cell(summ["time_to_high_price"]), undercuts=summ["undercuts"]["total"],
               punishments=summ["punishments"]["total"], refusals=sum(1 for r in refusals if r[0] not in derive.QUESTION_KINDS),
               question_declines=sum(1 for r in refusals if r[0] in derive.QUESTION_KINDS),
               parse_failures=sum(n for (_, c), n in failures.items() if c == "parse_failure"),
               truncations=sum(n for (_, c), n in failures.items() if c == "truncation"),
               imputed=sum(s["imputed"] for s in seats), truncated_talk=sum(m["truncated"] for m in messages),
               word_capped_talk=sum(m["word_capped"] for m in messages),
               messages=sum(1 for e in events if e.get("kind") == "talk" and not _done(e)), profit_total=_cell(round(sum(s["profit_total"] for s in seats), 6)),
               max_prompt_tokens=max(peaks) if peaks else "", clamped_calls=len(clamp), skipped_calls=sum(1 for c in clamp if c["skipped"]))
    if params.get("question_when") not in (None, "always") or wd:   # unit W2: absent for every other trial (additive columns, blank)
        row.update(question_when=params.get("question_when") or "", question_feedback=params.get("question_feedback") or "",
                   asked_count=sum(1 for c in wd.values() if c.get("asked")), eligible_count=sum(1 for c in wd.values() if c.get("eligible")))
    elif params.get("question_when") is not None or params.get("question_feedback") is not None:   # always: every round asked, no checks logged
        row.update(question_when=params.get("question_when") or "", question_feedback=params.get("question_feedback") or "")
    if params.get("empty_talk_as_done") is True:   # unit E1 (gpt-oss only): talk turns read as done from an empty reply; blank for other trials
        row[EMPTY_TALK_COL] = sum(1 for e in events if e.get("kind") == "empty_reply_as_done")
    return row, rounds, messages, questions, calls, refusals, failures


def _clamp_row(meta, e, **kw):
    row = {"trial_id": meta["trial_id"], "arm": meta["arm"], "thinking": meta["thinking"], "penalty_point": meta["penalty_point"],
           "round": _cell(e.get("round")), "seat": e.get("seat", ""), "draw_key": _cell(e.get("draw_key"))}
    row.update(kw)
    return row


def clamp_rows(events, meta):
    """clamp.csv rows for one trial: its `context_clamp` events (U2), each joined to the real tokens_in of the call event
    with the same draw_key (the nth clamp event of a key takes the nth such event). A skipped call that has no clamp event
    but is flagged context_clamp_skipped is added too, so no skipped call is lost."""
    own = {}
    for e in events:
        if e.get("kind") in KINDS + ("attempt", "probe") and e.get("draw_key") is not None and _is_int(e.get("tokens_in")):
            own.setdefault(e["draw_key"], []).append(e["tokens_in"])
    used, out = {}, []
    for e in events:
        if e.get("kind") != "context_clamp":
            continue
        k = e.get("draw_key")
        req, gr = e.get("requested_max_tokens"), e.get("granted_max_tokens")
        real = own.get(k, [])
        i = e["attempt"] if _is_int(e.get("attempt")) else used.get(k, 0)   # attempt 0 / 1 = the first / second call event of the key
        used[k] = used.get(k, 0) + 1
        out.append(_clamp_row(meta, e, call_type=e.get("call_type", ""), attempt=_cell(e.get("attempt")),
                              est_prompt_tokens=_cell(e.get("est_prompt_tokens")), requested_max_tokens=_cell(req), granted_max_tokens=_cell(gr),
                              reduction=req - gr if _is_int(req) and _is_int(gr) else "", skipped=bool(e.get("skipped")),
                              real_tokens_in=real[i] if i < len(real) else "", window=_cell(e.get("window")), margin=_cell(e.get("margin")),
                              min_tokens=_cell(e.get("min_tokens"))))
    seen = {r["draw_key"] for r in out if r["skipped"]}
    for e in events:
        if e.get("context_clamp_skipped") is True and e.get("kind") in KINDS and _cell(e.get("draw_key")) not in seen:
            out.append(_clamp_row(meta, e, call_type=e.get("kind"), attempt="", est_prompt_tokens="", requested_max_tokens="", granted_max_tokens=0,
                                  reduction="", skipped=True, real_tokens_in="", window="", margin="", min_tokens=""))
    return out


def clamp_summary(trials, per_trial, clamps):
    """Rows for clamp_summary.csv: arm x penalty_point x thinking. clamps is one list of clamp.csv rows per trial."""
    groups = {}
    for t, (calls, _, _), cl in zip(trials, per_trial, clamps):
        if t["status"] != "corrupt":
            groups.setdefault((str(t["arm"]), str(t["penalty_point"]), t["thinking"]), []).append((t, calls, cl))
    out = []
    for (arm, pp, thinking), items in sorted(groups.items()):
        allrows = [c for _, _, cl in items for c in cl]
        # model calls only (probes are not in `calls`); a repaired call clamped on both attempts counts once (distinct draw_key)
        rows = list({(c["trial_id"], c["draw_key"]) if c["draw_key"] != "" else id(c): c for c in allrows if c["call_type"] in KINDS}.values())
        n_calls = sum(sum(calls.get(k, 0) for k in KINDS) for _, calls, _ in items)
        reds = sorted(c["reduction"] for c in rows if _is_int(c["reduction"]) and not c["skipped"])   # skipped calls are counted apart
        mid = len(reds) // 2
        med = "" if not reds else reds[mid] if len(reds) % 2 else round((reds[mid - 1] + reds[mid]) / 2, 1)
        peaks = [t["max_prompt_tokens"] for t, _, _ in items if _is_int(t.get("max_prompt_tokens"))]
        out.append({"arm": arm, "penalty_point": pp, "thinking": thinking, "trials": len(items), "calls": n_calls, "clamped": len(rows),
                    "clamp_share": round(len(rows) / n_calls, 6) if n_calls else "", "median_reduction": med,
                    "worst_reduction": reds[-1] if reds else "", "skipped": sum(1 for c in rows if c["skipped"]),
                    "max_prompt_tokens": max(peaks) if peaks else "", "trials_affected": sum(1 for _, _, cl in items if cl)})
    return out


def _tick(params):
    m = params.get("market") if isinstance(params.get("market"), dict) else {}
    v = _price(m.get("quoteIncrement"))
    return v if v else competitiveness.DEFAULT_TICK


def _mark_competitive(rounds, floor, tick):
    """Set competitive_round (1/0, blank = not scored) on the quote rows of one trial (U16)."""
    flags = competitiveness.classify(rounds, floor, tick)[0] if floor != "" else {}
    for x in rounds:
        v = flags.get((x["round"], x["seat"]))
        x["competitive_round"] = "" if v is None else int(v)


def _inreply_name(params, e):
    """The question name of an in-reply answer: params.json reply_extra.text_name without its `_inreply` suffix (confidant_inreply
    -> confidant, the QUESTION text asked), else the field's name."""
    t = ((params or {}).get("reply_extra") or {}).get("text_name")
    return t[:-len("_inreply")] if isinstance(t, str) and t.endswith("_inreply") else (t or _text(e.get("self_report_name")))


def _question_mode(e):
    parts = str(e.get("draw_key", "")).split("|")
    return e.get("mode") or (parts[2] if parts[0] == "question" and len(parts) > 2 else "")


def _num(x):
    return round(x, 6) if isinstance(x, float) else x


def _text(x):
    return x if isinstance(x, str) else ""


def _cell(x):
    return "" if x is None else x


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def check_fingerprints(trials):
    """Raise MixedFingerprintError for an arm whose (non-corrupt) trials differ in prompt_fingerprint or code_commit."""
    by_arm = {}
    for t in trials:
        if t["status"] != "corrupt":
            by_arm.setdefault(t["arm"], []).append(t)
    for arm, ts in sorted(by_arm.items(), key=lambda kv: str(kv[0])):
        for key in GUARDED:
            vals = {t[key] for t in ts}
            if vals == {""}:
                print("warning: arm %s: no trial records %s" % (arm, key), file=sys.stderr)
            elif len(vals) > 1:
                raise MixedFingerprintError("arm %s has %d different %s values: %s" % (
                    arm, len(vals), key, ", ".join(sorted(v or "(missing)" for v in vals))))


def _fmt(d):
    return json.dumps(dict(sorted(d.items())), ensure_ascii=False, separators=(",", ":")) if d else ""


def refusal_table(trials, per_trial):
    """Rows for refusals.csv: every arm x thinking x kind, with counts, rate, refusal kinds and matched patterns."""
    groups = {}
    for t, (calls, refs, fails) in zip(trials, per_trial):
        if t["status"] != "corrupt":
            groups.setdefault((str(t["arm"]), t["thinking"]), []).append((calls, refs, fails))
    out = []
    for (arm, thinking), items in sorted(groups.items()):
        for kind in KINDS:
            n_inreply = sum(c.get("inreply", 0) for c, _, _ in items) if kind == "question" else 0
            n_calls = sum(c.get(kind, 0) for c, _, _ in items) + n_inreply   # in-reply answers count as question calls here only
            mine = [[r for r in refs if r[0] == kind] for _, refs, _ in items]
            kinds, pats = {}, {}
            for r in (x for m in mine for x in m):
                kinds[r[1]] = kinds.get(r[1], 0) + 1
                pats[r[2]] = pats.get(r[2], 0) + 1
            n_ref = sum(kinds.values())
            n_imp = sum(f.get((kind, "imputed_rounds"), 0) for _, _, f in items)
            played = sum(f.get(("game", "played_rounds"), 0) for _, _, f in items)
            out.append({"arm": arm, "thinking": thinking, "kind": kind, "trials": len(items), "calls": n_calls,
                        "refusals": n_ref, "refusal_rate": round(n_ref / n_calls, 6) if n_calls else "",
                        "parse_failures": sum(f.get((kind, "parse_failure"), 0) for _, _, f in items),
                        "truncations": sum(f.get((kind, "truncation"), 0) for _, _, f in items),
                        "imputed_rounds": n_imp, "played_rounds": played,
                        "imputed_round_share": round(n_imp / played, 6) if played else "", "inreply_calls": n_inreply,
                        "counts_toward_pause": int(kind not in derive.QUESTION_KINDS),
                        "trials_with_refusal": sum(1 for m in mine if m), "by_refusal_kind": _fmt(kinds),
                        "patterns": _fmt(pats)})
    return out


def select_trials(root, rerun_roots=(), include_superseded=False):
    """The trial directories to collect: find_trials(root) plus those of the rerun roots, minus the double counts of superseded.csv
    (module docstring). Unchanged find_trials(root) when there is no superseded.csv and no rerun root."""
    found = {p.resolve(): p for p in find_trials(root)}
    for rr in rerun_roots:
        found.update({p.resolve(): p for p in find_trials(rr)})
    paths = sorted(found.values(), key=lambda p: p.name)
    names = [p.name for p in paths]
    dup = sorted({n for i, n in enumerate(names) if i and names[i - 1] == n})   # paths are sorted by name
    if dup:
        raise ValueError("duplicate trial directory names under %s: %s" % (", ".join(map(str, (root,) + tuple(rerun_roots))), ", ".join(dup)))
    sup = trunc_rerun.read_superseded(root)
    if not sup and not rerun_roots:
        stray = [p for p in paths if p.name.endswith(trunc_rerun.SUFFIX)]
        for p in stray:
            print("warning: %s is a truncation rerun not listed in %s; left out" % (p.name, trunc_rerun.SUPERSEDED), file=sys.stderr)
        return [p for p in paths if p not in stray]
    by_name = {p.name: p for p in paths}
    pair = {r["original_id"]: r["rerun_id"] for r in sup}
    reruns = set(pair.values())
    usable = {o for o, r in pair.items() if r in by_name and (by_name[r] / "DONE").exists()}
    for o in sorted(set(pair) - usable):
        print("warning: %s is superseded by %s, which is not collected or not DONE; the original stays in" % (o, pair[o]), file=sys.stderr)
    out = []
    for p in paths:
        n = p.name
        if n in pair:
            if n in usable and not include_superseded:
                continue
        elif n in reruns:
            if include_superseded or n not in {pair[o] for o in usable}:
                continue
        elif n.endswith(trunc_rerun.SUFFIX):
            print("warning: %s is a rerun not listed in %s; left out" % (n, trunc_rerun.SUPERSEDED), file=sys.stderr)
            continue
        out.append(p)
    return out


def collect(root, out_dir, include_pilot=False, rerun_roots=(), include_superseded=False):
    """Write the tables (trials, rounds, messages, questions, refusals, firms, clamp, clamp_summary) into out_dir; return the paths. Raises MixedFingerprintError before writing anything.
    Trials marked pilot in their grid_row.json (throwaway pilots) are left out unless include_pilot; trials.csv then has pilot = 1 for them.
    rerun_roots / include_superseded: truncation reruns, see the module docstring (select_trials)."""
    trials, rounds, messages, questions, per_trial, firms, clamps = [], [], [], [], [], [], []
    skipped = {}
    for t in select_trials(root, rerun_roots, include_superseded):
        if not include_pilot and is_pilot(t):
            arm = str(load_params(t).get("arm") or NAME_RE.sub(r"\g<arm>", t.name))
            skipped[arm] = skipped.get(arm, 0) + 1
            continue
        a, b, c, q, calls, refs, fails = trial_rows(t)
        trials.append(a)
        rounds += b
        if a["competitive_price"] != "":
            firms += competitiveness.firm_rows(b, a["competitive_price"], _tick(load_params(t)), a["trial_id"])
        messages += c
        questions += q
        per_trial.append((calls, refs, fails))
        clamps.append(clamp_rows(derive.read_events(Path(t) / "events.jsonl"), a) if a["status"] != "corrupt" else [])
    if skipped:
        print("note: %d pilot trial(s) left out (use --include-pilot to keep them); per arm: %s. A cell_from arm is pilot unless the design says pilot: false"
              % (sum(skipped.values()), ", ".join("%s %d" % kv for kv in sorted(skipped.items()))), file=sys.stderr)
    check_fingerprints(trials)
    if any(t["thinking"] == "" and t["status"] != "corrupt" for t in trials):
        print("warning: some trials have no thinking value in params.json; they form a blank-thinking group", file=sys.stderr)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    tcols = TRIAL_COLS + [EMPTY_TALK_COL] if any(EMPTY_TALK_COL in t for t in trials) else TRIAL_COLS
    for name, cols, rows in (("trials.csv", tcols, trials), ("rounds.csv", ROUND_COLS, rounds),
                             ("messages.csv", MESSAGE_COLS, messages), ("questions.csv", QUESTION_COLS, questions),
                             ("refusals.csv", REFUSAL_COLS, refusal_table(trials, per_trial)),
                             ("firms.csv", FIRM_COLS, firms),
                             ("clamp.csv", CLAMP_COLS, [c for cl in clamps for c in cl]),
                             ("clamp_summary.csv", CLAMP_SUMMARY_COLS, clamp_summary(trials, per_trial, clamps))):
        write_csv(out / name, cols, rows)
        paths.append(out / name)
    return paths


USAGE = """usage: collect.py <trials_root> <out_dir> [--include-pilot] [--rerun-root DIR]... [--include-superseded]
  --include-pilot        keep throwaway pilot trials
  --rerun-root DIR       root of the truncation reruns (trunc_rerun.py); repeatable. Needed unless the rerun root is inside <trials_root>
  --include-superseded   sensitivity analysis: include the superseded originals listed in <trials_root>/superseded.csv and EXCLUDE
                         their reruns, so a game is never counted twice (default: originals out, reruns in under the original's cell)"""


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(USAGE)
        return 0
    rest, rerun_roots, i = [], [], 1
    include_pilot = include_superseded = False
    while i < len(argv):
        x = argv[i]
        if x == "--include-pilot":
            include_pilot = True
        elif x == "--include-superseded":
            include_superseded = True
        elif x == "--rerun-root" and i + 1 < len(argv):
            rerun_roots.append(argv[i + 1])
            i += 1
        else:
            rest.append(x)
        i += 1
    if len(rest) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        paths = collect(rest[0], rest[1], include_pilot, rerun_roots, include_superseded)
    except ValueError as e:
        if isinstance(e, MixedFingerprintError):
            print("error: refusing to merge: %s" % e, file=sys.stderr)
            return 1
        print("error: %s" % e, file=sys.stderr)
        return 2
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
