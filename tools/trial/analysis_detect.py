#!/usr/bin/env python3
"""Track M analysis, part 2 (C10.2): the price detector and the conversation detector, scored against ground truth
(standard library only; scope sections 4.5 and 14.3).

Usage: python -X utf8 tools/trial/analysis_detect.py <tables_dir> <out_dir> [--competitive P] [--collusive P]
           [--truth truth_rounds.csv] [--truth-messages truth_messages.csv] [--level-min 0.8] [--window 2] [--tol 0.25]
Reads the collect.py tables (rounds.csv, messages.csv, trials.csv) and writes:
  detector_rounds.csv   trial_id, round, truth, price_flag, conversation_flag
  detector_scores.csv   detector (price | conversation | message:<category>), level (round | trial | message), truth,
                        tp, fp, fn, tn, precision, recall (blank when undefined)
  message_labels.csv    trial_id, round, turn, seat, proposal, agreement, threat (the keyword rules, per message)

Price detector (reads only prices; persistence over time, a simple form of dependence: no autocorrelation model): a round is flagged when each of the last `window` rounds is
played, at a level of at least `level_min` (level = (price - competitive)/(collusive - competitive)), and those levels
stay within `tol` of each other, i.e. high prices that persist and move together. Competitive prices are stable but not
high; a single high round or a jump is not flagged. Its start-up (the first window-1 rounds of a run) is its known cost.

Conversation detector (reads only messages; keyword rules for proposal, agreement and threat; refused messages are
ignored; a proposal, agreement or threat preceded by a negation in the same clause, such as "do not agree" or "I will
not punish you", does not count; a message with an agreement and a CONDITIONAL threat ("Agreed, 10. If you undercut I will
punish you", "agree, and I'll punish undercuts": the cartel with enforcement) is collusive talk, so it switches the flag
on, or keeps it on, unless it says the deal is over ("You broke our deal. If you undercut again, price war.": past or
finished states only, so "If you break the deal, I will punish you" is enforcement); any other message with a threat
switches it off. Known limits: a re-agreement in the same message as a broken-deal complaint ("You broke the deal.
Agreed, back to 10, but if you undercut again ...") switches the flag off; conditionals outside the CONDITIONAL list
are missed): a round is flagged from the first agreement message until the next
such threat message (the threat's own round is not flagged; a later agreement flags again).

Ground truth: --truth is a CSV trial_id, round, collusive (0/1), from the generator of a mock or from hand coding; with
none, truth falls back to the OUTCOME (round level >= threshold), labelled `outcome` in the scores. Scoring the price
detector against the outcome is circular; use it only for the conversation detector. --truth-messages (trial_id, round,
turn, seat, proposal, agreement, threat) enables message-level scores, over the labelled messages only (an unlabelled message
is ignored, not counted as a false positive, so label a random or stratified sample, not a convenient subset). With the
outcome fallback the price detector is NOT scored (circular: both read the same prices); only the conversation detector is.
Caveat on the mocks: their truth is derived from the same intended prices the price detector reads, so the mock tests
prove the implementation recovers a known truth, not that the rule is valid on real play.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_m as am  # noqa: E402

CATS = ("proposal", "agreement", "threat")
RULES = {
    "proposal": r"\b(propos\w*|suggest\w*|how about|what if we|let'?s|let us|we should|shall we|i offer)\b",
    "agreement": r"\b(agree[ds]?|(?<!big )(?<!good )(?<!great )deal\b(?! with)|accept(?:ed|s)?|sounds good|count me in|you have my word|settled)\b",
    "threat": r"\b(punish\w*|retaliat\w*|price war|match you down|or else|i will undercut|if you undercut|if you do it again)\b",
}
CONDITIONAL = r"\b(if (you|anyone|either of us)|should you|or else|unless|otherwise|undercuts|undercutting|anyone who undercuts?|any undercut|(?<!you )(?<!they )(?<!he )(?<!she )(undercut|cheat|betray|go below|drop below|cut) [^.!?;,]{0,20}\band (i|we)\b)"
DEAL_OVER = r"\b((deal|agreement) (is|was) (off|over|dead)|broke\b|broken\b|cheated\b|betrayed\b|we had a deal|agreed before|agreed to nothing)"  # past or finished states only: "if you break the deal" is enforcement
# a negation earlier in the same clause (no . ! ? ; , between it and the keyword) within three words; "no deal" too
NEGATION = re.compile(r"\b(?:not|never|cannot)\b[^.!?;,]{0,40}$")


def classify(text):
    """(proposal, agreement, threat) as 0/1 from the keyword rules."""
    t = text.lower().replace("n't", " not").replace("cannot", "can not")
    t = re.sub(r"\bno (deal|agreement)", r"not \1", t)
    t = re.sub(r"\b(let'?s|let us) not\b", "not", t)  # "let's not" is a refusal to propose
    out = []
    for cat in CATS:
        out.append(int(any(not _negated(t[:m.start()]) for m in re.finditer(RULES[cat], t))))
    return tuple(out)


def enforces(text):
    """True when a message's threat is conditional (on a future undercut) and the message does not say the deal is over:
    with an agreement, that is a cartel with enforcement ("Agreed, 10. If you undercut I will punish you.")."""
    t = text.lower()
    return bool(re.search(CONDITIONAL, t)) and not re.search(DEAL_OVER, t)


def _negated(before):
    m = NEGATION.search(before)
    return bool(m) and len(re.findall(r"\w+", before[m.start():])) <= 4  # the negation word plus up to three more words


def score(pred, truth, universe):
    """Counts and precision/recall of the predicted set against the true set over a universe of keys."""
    pred, truth, universe = set(pred), set(truth), set(universe) | set(pred) | set(truth)
    tp, fp, fn = len(pred & truth), len(pred - truth), len(truth - pred)
    return dict(tp=tp, fp=fp, fn=fn, tn=len(universe) - tp - fp - fn,
                precision=tp / (tp + fp) if tp + fp else "", recall=tp / (tp + fn) if tp + fn else "")


def price_flags(games, level_min=0.8, window=2, tol=0.25):
    if window < 1:
        raise ValueError("window must be at least 1")
    flags = set()
    for tid, g in games.items():
        rs = g["rounds"]
        for r in rs:
            lv = [rs[x]["level"] if x in rs else None for x in range(r - window + 1, r + 1)]
            if None not in lv and min(lv) >= level_min and max(lv) - min(lv) <= tol:
                flags.add((tid, r))
    return flags


def conversation_flags(games, messages):
    by_round = {}
    for i, m in enumerate(messages):
        if not m.get("refusal_kind") and m.get("text"):
            by_round.setdefault((m["trial_id"], int(m["round"])), []).append((int(m["turn"] or 0), i, m["text"]))
    flags = set()
    for tid, g in games.items():
        on = False
        for r in sorted(g["rounds"]):
            for _, _, text in sorted(by_round.get((tid, r), [])):
                _, agree, threat = classify(text)
                on = True if agree and (not threat or enforces(text)) else False if threat else on
            if on:
                flags.add((tid, r))
    return flags


def trial_level(flags, games):
    return {t for t, _ in flags if t in games}


def message_labels(messages):
    rows = []
    for m in messages:
        if m.get("refusal_kind") or not m.get("text"):
            continue
        rows.append(dict(trial_id=m["trial_id"], round=int(m["round"]), turn=int(m["turn"] or 0), seat=m["seat"],
                         **dict(zip(CATS, classify(m["text"])))))
    return rows


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_truth_rounds(path):
    return {(r["trial_id"], int(r["round"])): int(r["collusive"]) for r in _read(path)}


def read_truth_messages(path):
    return {(r["trial_id"], int(r["round"]), int(r["turn"]), r["seat"]): {c: int(r[c]) for c in CATS} for r in _read(path)}


def score_messages(rows, truth):
    """Message-level scores per category, over the messages that have a truth label."""
    out = []
    for cat in CATS:
        keys = {k for k in truth}
        pred = {(r["trial_id"], r["round"], r["turn"], r["seat"]) for r in rows if r[cat]} & keys
        out.append(dict(detector="message:" + cat, level="message", truth="ground_truth",
                        **score(pred, {k for k, v in truth.items() if v[cat]}, keys)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tables_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--competitive", type=float, help="override; default trials.csv competitive_price")
    ap.add_argument("--collusive", type=float, help="override; default trials.csv collusive_price")
    ap.add_argument("--truth")
    ap.add_argument("--truth-messages")
    ap.add_argument("--threshold", type=float, default=0.8, help="outcome truth: level at or above this")
    ap.add_argument("--level-min", type=float, default=0.8)
    ap.add_argument("--window", type=int, default=2)
    ap.add_argument("--tol", type=float, default=0.25)
    a = ap.parse_args(argv)
    d = Path(a.tables_dir)
    tables = am.load_tables(d)
    try:
        competitive, collusive = am.resolve_prices(tables, a.competitive, a.collusive)
    except ValueError as e:
        ap.error(str(e))
    games = {k: g for k, g in am.build_games(tables, competitive, collusive).items() if g["meta"].get("status") != "corrupt"}
    truth_path = Path(a.truth) if a.truth else d / "truth_rounds.csv"
    if truth_path.exists():
        truth, kind = read_truth_rounds(truth_path), "ground_truth"
    else:
        truth, kind = {(t, r): int(rd["level"] is not None and rd["level"] >= a.threshold) for t, g in games.items() for r, rd in g["rounds"].items()}, "outcome"
    universe = {(t, r) for t, g in games.items() for r in g["rounds"]}
    true_rounds = {k for k, v in truth.items() if v and k in universe}  # truth for dropped or corrupt trials is not scored
    price = price_flags(games, a.level_min, a.window, a.tol)
    conv = conversation_flags(games, tables["messages"])
    scores = []
    for name, flags in (("price", price), ("conversation", conv)):
        if name == "price" and kind == "outcome":
            continue  # circular: the outcome truth is a threshold on the prices the detector reads
        scores.append(dict(detector=name, level="round", truth=kind, **score(flags, true_rounds, universe)))
        scores.append(dict(detector=name, level="trial", truth=kind,
                           **score(trial_level(flags, games), trial_level(true_rounds, games), set(games))))
    labels = message_labels(tables["messages"])
    mt_path = Path(a.truth_messages) if a.truth_messages else d / "truth_messages.csv"
    if mt_path.exists():
        scores += score_messages(labels, read_truth_messages(mt_path))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    am.write_csv(out / "detector_rounds.csv", [dict(trial_id=t, round=r, truth=truth.get((t, r), ""), price_flag=int((t, r) in price),
                                                      conversation_flag=int((t, r) in conv)) for t, r in sorted(universe)],
                 ["trial_id", "round", "truth", "price_flag", "conversation_flag"])
    am.write_csv(out / "detector_scores.csv", scores, ["detector", "level", "truth", "tp", "fp", "fn", "tn", "precision", "recall"])
    am.write_csv(out / "message_labels.csv", labels, ["trial_id", "round", "turn", "seat"] + list(CATS))
    for n in ("detector_rounds.csv", "detector_scores.csv", "message_labels.csv"):
        print(out / n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
