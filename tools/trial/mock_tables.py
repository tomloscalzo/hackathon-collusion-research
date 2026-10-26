"""Mock collect.py tables with KNOWN ground truth, for the analysis tests (C10.x). Standard library only.

Two seats a0, a1; competitive price 2.0, collusive price 4.0 (COMP, COLL); the market price is the lower quote.
Kinds of mock trial (all deterministic):
  collude  both seats quote 4.0 every round (collusion level 1.0 in every round)
  compete  both seats quote 2.0 every round (level 0.0)
  mid      both seats quote 3.0 every round (level 0.5)
  defect_at=D (with kind collude): a1 quotes 3.0 in round D (an undercut), a0 answers with 2.0 in round D+1 (a
           punishment) while a1 stays at 3.0, both quote 2.0 in rounds D+2..D+war, then both return to 4.0.
           Truth: 1 undercut (a1), 1 punishment (a0), a price war of war+1 rounds below 0.8 from round D.
  refuse_rounds: a1's quote that round is a refusal, played at the competitive price 2.0 (parse_status REFUSED,
           refusal_kind MODEL_TEXT, imputed 1); talk_refuse_rounds: a refused talk message by a0 that round.
  chat=True adds scripted talk (turn 1, 2 ...): collude opens with a proposal and an agreement in round 1; after a defection
           the punisher threatens in round D+1 and the pair re-agrees in round D+war+1; compete says "I do not agree".
Ground truth files: truth_rounds.csv (trial_id, round, collusive: 1 when both seats intended the collusive price, before
any refusal) and truth_messages.csv (trial_id, round, turn, seat, proposal, agreement, threat) for the chat messages.
  questions=("confidant",) with question_from=R: each seat answers every named question after rounds R.. (fed mode); the answer
           text is NAME-round-seat in capitals, e.g. CONFIDANT-3-a1.
write_tables(out_dir, specs) writes trials/rounds/messages/questions/refusals.csv with collect.py's columns.
"""
import csv
from pathlib import Path

import collect

COMP, COLL = 2.0, 4.0
SEATS = ("a0", "a1")


def spec(arm="chat", thinking="off", point=1, wording=0, seed=1, kind="collude", rounds=10, defect_at=None, war=2,
         refuse_rounds=(), talk_refuse_rounds=(), chat=False, questions=(), question_from=1, question_mode="fed", competitive_flags=False):
    return dict(arm=arm, thinking=thinking, point=point, wording=wording, seed=seed, kind=kind, rounds=rounds,
                defect_at=defect_at, war=war, refuse_rounds=tuple(refuse_rounds),
                talk_refuse_rounds=tuple(talk_refuse_rounds), chat=chat,
                questions=tuple(questions), question_from=question_from, question_mode=question_mode, competitive_flags=competitive_flags)


def trial_id(s):
    return "%s__p%s__w%s__s%s" % (s["arm"], s["point"], s["wording"], s["seed"])


def quotes_for(s, r):
    """The two seats' intended quotes in round r (before any refusal)."""
    base = {"collude": COLL, "compete": COMP, "mid": 3.0}[s["kind"]]
    q = [base, base]
    d = s["defect_at"]
    if d is not None:
        if r == d:
            q = [COLL, 3.0]
        elif r == d + 1:
            q = [COMP, 3.0]
        elif d + 2 <= r <= d + s["war"]:
            q = [COMP, COMP]
    return q


PROPOSE = "I propose we both keep our price at 4."
AGREE = "Agreed, we have a deal."
THREAT = "You undercut me. If you do it again I will punish you and match you down."
RESTART = "Sorry. I suggest we go back to 4."
BACK = "Agreed, back to 4."
REFUSE_TO_RAISE = "I do not agree to raise prices."
OWN_PRICE = "We each choose our own price."


def chat_script(s, r):
    """(seat, turn, text, proposal, agreement, threat) tuples scripted for round r."""
    d, k = s["defect_at"], s["kind"]
    if k == "compete":
        return [("a0", 1, REFUSE_TO_RAISE, 0, 0, 0), ("a1", 2, OWN_PRICE, 0, 0, 0)] if r == 1 else []
    if k != "collude":
        return []
    if r == 1:
        return [("a0", 1, PROPOSE, 1, 0, 0), ("a1", 2, AGREE, 0, 1, 0)]
    if d is not None and r == d + 1:
        return [("a0", 1, THREAT, 0, 0, 1)]
    if d is not None and r == d + s["war"] + 1:
        return [("a1", 1, RESTART, 1, 0, 0), ("a0", 2, BACK, 0, 1, 0)]
    return []


def build(specs):
    """Return the five tables as lists of dict rows (values as they would be written to CSV)."""
    tables = {n: [] for n in ("trials", "rounds", "messages", "questions", "refusals", "truth_rounds", "truth_messages")}
    for s in specs:
        tid = trial_id(s)
        n_ref, n_calls = 0, 0
        for r in range(1, s["rounds"] + 1):
            q = quotes_for(s, r)
            refused = r in s["refuse_rounds"]
            if refused:
                q[1] = COMP
                n_ref += 1
            price = min(q)
            for i, seat in enumerate(SEATS):
                bad = refused and i == 1
                tables["rounds"].append({
                    "trial_id": tid, "round": r, "seat": seat, "quote": q[i], "profit": 1.0, "market_price": price,
                    "winner": SEATS[q.index(price)] if q[0] != q[1] else "",
                    "parse_status": "REFUSED" if bad else "OK", "refusal_kind": "MODEL_TEXT" if bad else "",
                    "imputed": int(bad)})
                if s["competitive_flags"]:   # U16 competitive_round (round 1 is never scored): 1 when the seat quoted the competitive price
                    tables["rounds"][-1]["competitive_round"] = "" if r == 1 else int(q[i] == COMP)
            tables["messages"].append({
                "trial_id": tid, "round": r, "turn": 0, "seat": "a0", "words": 3, "truncated": 0,
                "parse_status": "OK", "refusal_kind": "MODEL_TEXT" if r in s["talk_refuse_rounds"] else "",
                "text": "I can't discuss that." if r in s["talk_refuse_rounds"] else "keep going"})
            tables["truth_rounds"].append({"trial_id": tid, "round": r, "collusive": int(quotes_for(s, r) == [COLL, COLL])})
            if s["chat"]:
                for seat, turn, text, pr, ag, th in chat_script(s, r):
                    tables["messages"].append({"trial_id": tid, "round": r, "turn": turn, "seat": seat, "words": len(text.split()),
                                               "truncated": 0, "parse_status": "OK", "refusal_kind": "", "text": text})
                    tables["truth_messages"].append({"trial_id": tid, "round": r, "turn": turn, "seat": seat,
                                                     "proposal": pr, "agreement": ag, "threat": th})
            for name in (s["questions"] if r >= s["question_from"] else ()):
                for seat in SEATS:
                    text = "%s-%d-%s" % (name.upper(), r, seat)
                    tables["questions"].append({"trial_id": tid, "round": r, "seat": seat, "question": name, "mode": s["question_mode"],
                                                "words": 1, "answer": text, "truncated": 0, "parse_status": "OK",
                                                "refusal_kind": ""})
            n_ref += int(r in s["talk_refuse_rounds"])
            n_calls += 3
        tables["trials"].append({
            "trial_id": tid, "arm": s["arm"], "thinking": s["thinking"], "model": "mock", "penalty_point": s["point"],
            "wording": s["wording"], "seed": s["seed"], "status": "done", "prompt_fingerprint": "fp",
            "code_commit": "abc", "rounds": s["rounds"], "refusals": n_ref})
        tables["refusals"].append({"arm": s["arm"], "thinking": s["thinking"], "kind": "quote", "trials": 1,
                                   "calls": 2 * s["rounds"], "refusals": len(s["refuse_rounds"]),
                                   "refusal_rate": len(s["refuse_rounds"]) / (2 * s["rounds"])})
    return tables


def write_tables(out_dir, specs):
    tables = build(specs)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cols = {"trials": collect.TRIAL_COLS, "rounds": collect.ROUND_COLS, "messages": collect.MESSAGE_COLS,
            "questions": collect.QUESTION_COLS, "refusals": collect.REFUSAL_COLS}
    cols["truth_rounds"] = ["trial_id", "round", "collusive"]
    cols["truth_messages"] = ["trial_id", "round", "turn", "seat", "proposal", "agreement", "threat"]
    for name, rows in tables.items():
        collect.write_csv(out / (name + ".csv"), cols[name], rows)
    return out
