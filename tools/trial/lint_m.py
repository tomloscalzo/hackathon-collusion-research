#!/usr/bin/env python3
"""Track M pre-run lint (C15.1; docs/levers/LEVER_KIT_DESIGN.md section 2.4, PROMPT_WORDING_PROPOSAL Part 2 rules).

Usage: python -X utf8 tools/trial/lint_m.py --texts seat_texts.json [--texts questions.json ...] [--design design.yaml]
           [--grid grid.csv] [--tokenizer NAME_OR_DIR] [--tolerance 0.10]
Exit status 0 = pass (warnings may print), 1 = at least one failure, 2 = usage or unreadable input. No LLM, no network.

Text data file: {"version": 1, "texts": [{"name", "slot", "text", ...optional flags}]} (a "questions" list is read the same way).
Optional flags per text:
  placebo_for   list of text names this text is the placebo or control for
  about_rule    true when the condition is about the rule (only then may the text use the banned words)
  true_statement  must be the boolean false on the one untrue text (the not-monitored notice); omit or true elsewhere
  owner_text_exempt_loaded  true ONLY on an owner-supplied verbatim text that must keep a banned word (today only moral_prime, whose last
                words are "goodwill and cooperation"); lets that one text pass check 2. It is not about_rule (the text is not about a rule).
                Must be a boolean. Every other text still fails on a banned word.
  owner_approved_idle_notice  true ONLY on an owner-approved idle (untrue) SEAT_NOTES notice that is not about the model's reasoning (today only
                watchdog_notice): it must also have true_statement false, and it may then be used by thinking-off arms (check 4 otherwise
                allows an untrue SEAT_NOTES text in thinking-on arms only). It does not waive the other checks. Must be a boolean.
  role_play     true on a text that states a made-up situation as a role-play (the pressure text); disclosed in the ethics appendix; must be a boolean
Checks (each failure names the text):
  1. placebo length: every placebo within +-10% (--tolerance) of every text it is the placebo for, in words (whitespace split),
     and in tokens when a tokenizer loads offline (transformers, local files only; skipped with a warning otherwise)
  2. banned words (collusion, collusive, collude, cartel, cooperate, cooperation, price-fixing) in any text that is not about_rule
  3. cap leakage ("40 rounds", "round 40", "maxRounds", "at most 40", also "forty rounds") in every text, and in the design
     and grid cells that carry text-like values (condition_texts, options)
  4. untruth flag: texts used by an unmonitored-communication arm (design or grid) in the TALK_NOTICE slot must include
     exactly one name with true_statement false; a non-boolean flag fails. The only other texts that may be untrue are
     SEAT_NOTES texts (the idle reasoning-monitor threat, variants A and B, U8), also explicitly flagged false, used by some arm, and only by
     arms that run with thinking on (the threat is about the reasoning); and the REPLY_FIELD instructions saying "no one will
     see this answer", which must be flagged false (disclosed in the ethics appendix) and used by some arm. No text in any other
     slot may be false.
     UNIT W2 (watchdog): a text may be untrue in the QUESTION slot, and a SEAT_NOTES text may be untrue in a thinking-off arm, only when it
     carries the explicit flag owner_approved_idle_notice: true (a boolean, only on a text flagged true_statement false; the owner approved that
     text by name); the QUESTION text must be used by some arm. The flag is never a substitute for true_statement or about_rule.
     Options cells: question_when (always | non_competitive | self_report_ge:<k>) and question_feedback (fed | none) need the option question;
     self_report_ge:<k> needs a reply_extra of kind integer with k inside min..max.
  5. references: every text name used by the design or grid exists in the texts files (condition_texts, and the option texts
     briefing_notice, round_reminder, quote_instruction and reply_extra.text); placebo_for names exist
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

BANNED = re.compile(r"\b(collu(?:sions?|sive|de[sd]?|ding)|cartels?|cooperat(?:e[sd]?|ion|ing)|price[- ]fixing)\b", re.I)
CAP = re.compile(r"\b(?:(?:40|forty)[\s-]+(?:rounds?|turns?)|rounds?\s+(?:40|forty)|max[_ ]?rounds|at\s+most\s+(?:40|forty)|(?:40|forty)th\s+round)\b", re.I)


def words(text):
    return len(text.split())


def load_texts(paths):
    out, errs = {}, []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8-sig"))
        if not isinstance(d, dict):
            raise ValueError("%s: top level must be an object" % Path(p).name)
        for key in ("texts", "questions"):
            for t in d.get(key) or []:
                if not isinstance(t, dict):
                    raise ValueError("%s: an entry in %r is not an object" % (Path(p).name, key))
                name = t.get("name")
                if not isinstance(name, str) or not isinstance(t.get("text"), str):
                    errs.append("%s: an entry in %r lacks a name or text" % (Path(p).name, key))
                elif name in out:
                    errs.append("text name %s is defined twice" % name)
                else:
                    out[name] = t
    return out, errs


def parse_condition_texts(s):
    return [x.split(":", 1)[1] for x in str(s).split(";") if ":" in x]


TEXT_OPTION_KEYS = ("briefing_notice", "round_reminder", "quote_instruction")
UNTRUE_SLOTS = ("TALK_NOTICE", "SEAT_NOTES", "REPLY_FIELD", "QUESTION")
WHEN_RE = re.compile(r"^(always|non_competitive|self_report_ge:-?[0-9]{1,6})$")   # option question_when (unit W2)
INREPLY = "_inreply"      # REPLY_FIELD <question>_inreply = the QUESTION text <question> (saved-only introspection, unit U10)
ONE_PER_SLOT = ("TALK_NOTICE",)      # SEAT_NOTES (threat variants A and B) and REPLY_FIELD ("no one will see this answer") may have several


def option_text_names(options):
    """Names of the texts an options cell (dict or JSON text) points at: the three text options and reply_extra.text."""
    if isinstance(options, str):
        try:
            options = json.loads(options) if options.strip() else {}
        except ValueError:
            return set()
    if not isinstance(options, dict):
        return set()
    out = {options[k] for k in TEXT_OPTION_KEYS if isinstance(options.get(k), str)}
    extra = options.get("reply_extra")
    if isinstance(extra, dict) and isinstance(extra.get("text"), str):
        out.add(extra["text"])
    return out


def option_cells(design, grid_rows):
    """(label, options dict) of every design arm and grid row that has options."""
    out = []
    for a in [dict((design or {}).get("defaults") or {}, **a) for a in (design or {}).get("arms") or []]:
        if isinstance(a.get("options"), dict):
            out.append(("design arm %s" % a.get("name"), a["options"]))
    for r in grid_rows:
        try:
            o = json.loads(r.get("options") or "{}")
        except ValueError:
            continue
        if isinstance(o, dict):
            out.append(("grid %s" % r.get("trial_id"), o))
    return out


def question_uses(design, grid_rows):
    """Names of the QUESTION texts used by an options cell (question, post_game_question)."""
    names = set()
    for _, o in option_cells(design, grid_rows):
        for k in ("question", "post_game_question"):
            v = o.get(k)
            names |= {v} if isinstance(v, str) else {x for x in v if isinstance(x, str)} if isinstance(v, list) else set()
    return names


def check_watchdog_options(design, grid_rows):
    """Unit W2: question_when / question_feedback in an options cell. Values are checked, both need a question, a
    self_report_ge:k needs a reply_extra of kind integer with k in range. Returns failure strings."""
    fails = []
    for label, o in option_cells(design, grid_rows):
        if "question_when" in o:
            w = o["question_when"]
            if not isinstance(w, str) or not WHEN_RE.match(w):
                fails.append("%s: question_when must be always, non_competitive or self_report_ge:<k>, got %r" % (label, w))
            elif not isinstance(o.get("question"), str):
                fails.append("%s: question_when needs an in-game question (option question)" % label)
            elif w.startswith("self_report_ge:"):
                extra, k = o.get("reply_extra"), int(w.split(":")[1])
                if not isinstance(extra, dict) or extra.get("kind") != "integer" or not (
                        isinstance(extra.get("min"), int) and isinstance(extra.get("max"), int) and extra["min"] <= k <= extra["max"]):
                    fails.append("%s: %s needs a reply_extra of kind integer with k inside its min..max" % (label, w))
        if "question_feedback" in o:
            if o["question_feedback"] not in ("fed", "none"):
                fails.append("%s: question_feedback must be fed or none, got %r" % (label, o["question_feedback"]))
            elif not isinstance(o.get("question"), str):
                fails.append("%s: question_feedback needs an in-game question (option question)" % label)
    return fails


def thinking_uses(design, grid_rows):
    """name -> set of thinking values (0/1) of the arms and grid rows that use the text (condition_texts or option texts)."""
    uses = {}
    for a in [dict((design or {}).get("defaults") or {}, **a) for a in (design or {}).get("arms") or []]:
        modes = {int(t) for t in a.get("thinking") or [0, 1]}
        for n in set((a.get("condition_texts") or {}).values()) | option_text_names(a.get("options")):
            uses.setdefault(n, set()).update(modes)
    for r in grid_rows:
        modes = {int(r["thinking"])} if str(r.get("thinking", "")).strip() in ("0", "1") else {0, 1}
        for n in set(parse_condition_texts(r.get("condition_texts", ""))) | option_text_names(r.get("options", "")):
            uses.setdefault(n, set()).update(modes)
    return uses


def used_names(design, grid_rows):
    """(names, unmonitored_names, cells): text names used, those used by unmonitored arms, text-like cells."""
    names, unmon, cells = set(), set(), []
    arms = [dict((design or {}).get("defaults") or {}, **a) for a in (design or {}).get("arms") or []]
    for a in arms:
        used = set((a.get("condition_texts") or {}).values())
        names |= used | option_text_names(a.get("options"))
        if a.get("communication") == "unmonitored":
            unmon |= used
        cells.append(("design arm %s" % a.get("name"), json.dumps(a.get("options") or {}) + " " + json.dumps(a.get("condition_texts") or {})))
    for r in grid_rows:
        used = set(parse_condition_texts(r.get("condition_texts", "")))
        names |= used | option_text_names(r.get("options", ""))
        if r.get("communication") == "unmonitored":
            unmon |= used
        cells.append(("grid %s" % r.get("trial_id"), "%s %s" % (r.get("options", ""), r.get("condition_texts", ""))))
    return names, unmon, cells


def load_tokenizer(name):
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(name, local_files_only=True)
        return lambda s: len(tok.encode(s))
    except Exception:  # not installed, not cached, or offline
        return None


def lint(texts, design=None, grid_rows=(), count_tokens=None, tolerance=0.10):
    """Return (failures, warnings) as lists of strings."""
    fails, warns = [], []
    if count_tokens is None:
        warns.append("no tokenizer available offline: token-length parity not checked (words only)")
    for name, t in sorted(texts.items()):
        for pname in t.get("placebo_for") or []:
            if pname not in texts:
                fails.append("%s: placebo_for names an unknown text %s" % (name, pname))
                continue
            for label, f in (("words", words),) + ((("tokens", count_tokens),) if count_tokens else ()):
                a, b = f(t["text"]), f(texts[pname]["text"])
                if b == 0:
                    fails.append("%s: %s is empty, no length to match" % (name, pname))
                elif abs(a - b) / b > tolerance:
                    fails.append("%s: placebo length %d %s vs %s %d (outside +-%d%%)" % (name, a, label, pname, b, round(tolerance * 100)))
        if not (t.get("about_rule") or t.get("owner_text_exempt_loaded") is True) and BANNED.search(t["text"]):
            fails.append("%s: banned word %r in a text that is not about the rule" % (name, BANNED.search(t["text"]).group(0)))
        if CAP.search(t["text"]):
            fails.append("%s: cap leakage %r" % (name, CAP.search(t["text"]).group(0)))
        if "true_statement" in t and not isinstance(t["true_statement"], bool):
            fails.append("%s: true_statement must be true or false" % name)
        if "owner_text_exempt_loaded" in t and not isinstance(t["owner_text_exempt_loaded"], bool):
            fails.append("%s: owner_text_exempt_loaded must be true or false" % name)
        if "owner_approved_idle_notice" in t and not isinstance(t["owner_approved_idle_notice"], bool):
            fails.append("%s: owner_approved_idle_notice must be true or false" % name)
        if "role_play" in t and not isinstance(t["role_play"], bool):
            fails.append("%s: role_play must be true or false" % name)
    names, unmon, cells = used_names(design, grid_rows)
    for label, cell in cells:
        if CAP.search(cell):
            fails.append("%s: cap leakage %r" % (label, CAP.search(cell).group(0)))
    for n in sorted(names - set(texts)):
        fails.append("text %s is used by the design or grid but not defined in the texts files" % n)
    false = sorted(n for n, t in texts.items() if t.get("true_statement") is False)
    notice_unmon = sorted(n for n in unmon if n in texts and texts[n].get("slot") == "TALK_NOTICE")
    if unmon and len(notice_unmon) != 1:
        fails.append("unmonitored arms must use exactly one TALK_NOTICE text, found %s" % (notice_unmon or "none"))
    for n in notice_unmon:
        if texts[n].get("true_statement") is not False:
            fails.append("%s: the untrue not-monitored text needs an explicit true_statement: false" % n)
    fails += check_watchdog_options(design, grid_rows)
    for n, t in sorted(texts.items()):    # unit W2: the explicit owner-approval flag for an untrue text
        if t.get("owner_approved_idle_notice") is True and t.get("true_statement") is not False:   # unit W2 (the bool check is above)
            fails.append("%s: owner_approved_idle_notice is only for a text flagged true_statement false" % n)
        if t.get("slot") == "QUESTION" and t.get("true_statement") is False and t.get("owner_approved_idle_notice") is not True:
            fails.append("%s: an untrue QUESTION text needs owner_approved_idle_notice: true (the owner approved it by name)" % n)
    qused = question_uses(design, grid_rows) if (design is not None or grid_rows) else None
    for n in false:
        if texts[n].get("slot") not in UNTRUE_SLOTS:
            fails.append("%s: true_statement false is only for a TALK_NOTICE, SEAT_NOTES or REPLY_FIELD text (slot %s)" % (n, texts[n].get("slot")))
    for n, t in sorted(texts.items()):
        if t.get("slot") == "REPLY_FIELD" and re.search(r"no one will see", t["text"], re.I) and t.get("true_statement") is not False:
            fails.append("%s: 'no one will see this answer' is untrue (the answers are read): needs an explicit true_statement: false" % n)
    for n, t in sorted(texts.items()):    # U10: an in-reply question (R2s/R3s) asks EXACTLY the question the fed-back arm asks
        if t.get("slot") == "REPLY_FIELD" and n.endswith(INREPLY):
            q = texts.get(n[:-len(INREPLY)])
            if q is None and not any(x.get("slot") == "QUESTION" for x in texts.values()):
                continue   # the questions file is not among the loaded texts: nothing to compare with
            if q is None or q.get("slot") != "QUESTION":
                fails.append("%s: the in-reply form of a question needs a QUESTION text named %s" % (n, n[:-len(INREPLY)]))
            elif q["text"] != t["text"]:
                fails.append("%s: the in-reply text must be word for word the QUESTION text %s" % (n, n[:-len(INREPLY)]))
    for slot in ONE_PER_SLOT:
        in_slot = [n for n in false if texts[n].get("slot") == slot]
        if len(in_slot) > 1:
            fails.append("more than one untrue text in slot %s: %s (one allowed)" % (slot, ", ".join(in_slot)))
    uses = thinking_uses(design, grid_rows) if (design is not None or grid_rows) else None
    for n in false if uses is not None else []:
        slot = texts[n].get("slot")
        if slot == "TALK_NOTICE" and n not in notice_unmon:
            fails.append("%s: true_statement false, but no unmonitored arm uses it as its notice (only the not-monitored text may be an untrue notice)" % n)
        elif slot == "REPLY_FIELD":
            if n not in uses:
                fails.append("%s: true_statement false, but no arm uses it" % n)
        elif slot == "QUESTION":
            if n not in qused:
                fails.append("%s: true_statement false, but no arm uses it as its question" % n)
        elif slot == "SEAT_NOTES":
            if n not in uses:
                fails.append("%s: true_statement false, but no arm uses it (only the idle reasoning-monitor threat may be an untrue SEAT_NOTES text)" % n)
            elif 0 in uses[n] and texts[n].get("owner_approved_idle_notice") is not True:
                fails.append("%s: an untrue reasoning-monitor text is used by an arm that runs with thinking off (thinking-on arms only)" % n)
    return fails, warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--texts", action="append", required=True)
    ap.add_argument("--design")
    ap.add_argument("--grid")
    ap.add_argument("--tokenizer", default="Qwen/Qwen3-14B")
    ap.add_argument("--tolerance", type=float, default=0.10)
    a = ap.parse_args(argv)
    try:
        texts, errs = load_texts(a.texts)
        design = None
        if a.design:
            import yaml
            design = yaml.safe_load(Path(a.design).read_text(encoding="utf-8"))
        grid = []
        if a.grid:
            with open(a.grid, encoding="utf-8", newline="") as f:
                grid = list(csv.DictReader(f))
    except Exception as e:                                  # unreadable or malformed input (incl. yaml.YAMLError): 2, never a traceback
        print("error: %s" % e, file=sys.stderr)
        return 2
    fails, warns = lint(texts, design, grid, load_tokenizer(a.tokenizer), a.tolerance)
    fails = errs + fails
    for w in warns:
        print("warning: " + w, file=sys.stderr)
    for f in fails:
        print("FAIL: " + f)
    print("lint_m: %s (%d texts, %d failures, %d warnings)" % ("FAIL" if fails else "PASS", len(texts), len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
