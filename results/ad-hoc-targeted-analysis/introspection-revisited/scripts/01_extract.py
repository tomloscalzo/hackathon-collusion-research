"""Extract one row per firm-round with every text channel, for the introspection, D-set and control arms (penalty point 1, private chat).

Channels: chat messages the firm sent this round (and their reasoning), the quote reply's plan and rationale, the quote-call reasoning,
the in-reply extra field (introspection answer or self-score), and the separate question call's answer and reasoning (fed-back arms and
the post-game question of r4). Behaviour: own quote, market price, lowest rival quote of the previous round, matched / undercut flags.
Output: WORK/firm_rounds_<model>.pkl and WORK/games_<model>.csv. Created by Claude at the prompting of the repository owner.
"""
import json
import sys
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
from common import RUNCSV, RUNS, WORK, ARMS, set_affinity  # noqa: E402


def one(args):
    model, tid, arm, root = args
    path = "%s/%s/trials/%s/%s/events.jsonl" % (RUNS, root, tid.split("__")[0], tid)
    talk, quote, qa, market = {}, {}, {}, {}
    try:
        fh = open(path, encoding="utf8")
    except OSError:
        return []
    for line in fh:
        e = json.loads(line)
        k = e.get("kind")
        if k == "talk" and e.get("outcome") == "OK":
            p = e.get("parsed") or {}
            key = (int(e["round"]), e["seat"])
            talk.setdefault(key, []).append((int(e.get("turn", 0)), (p.get("message") or "").strip(), e.get("reasoning") or ""))
        elif k == "quote":
            key = (int(e["round"]), e["seat"])
            p = e.get("parsed") or {}
            if e.get("outcome") == "OK" or key not in quote:
                quote[key] = dict(plan=p.get("plan") or "", rationale=p.get("rationale") or "", quote_reasoning=e.get("reasoning") or "",
                                  self_report=e.get("self_report"), quote_outcome=e.get("outcome"))
        elif k == "question":
            key = (int(e.get("round") or 0), e["seat"])
            if e.get("outcome") == "OK" or key not in qa:
                p = e.get("parsed") or {}
                qa[key] = dict(q_answer=(p.get("message") if isinstance(p, dict) else None) or e.get("reply") or "",
                               q_reasoning=e.get("reasoning") or "", q_name=e.get("name"), q_mode=e.get("mode"))
        elif k == "market":
            market[int(e["round"])] = dict(market_price=e.get("market_price"), prices=e.get("prices") or {})
    fh.close()
    rows = []
    rounds = sorted(market)
    seats = sorted({s for (_, s) in quote} | {s for (_, s) in talk})
    for r in rounds:
        for s in seats:
            pr = market[r]["prices"]
            prev = market.get(r - 1, {}).get("prices", {})
            rivals_prev = [v for kk, v in prev.items() if kk != s]
            own = pr.get(s)
            rv_prev = min(rivals_prev) if rivals_prev else None
            t = sorted(talk.get((r, s), []))
            q = quote.get((r, s), {})
            a = qa.get((r, s), {})
            rows.append(dict(model=model, trial_id=tid, arm=arm, round=r, seat=s, quote=own, market_price=market[r]["market_price"],
                             rival_prev_min=rv_prev,
                             matched=(None if rv_prev is None or own is None else int(abs(own - rv_prev) < 1e-9 and own > 1.0 + 1e-9)),
                             undercut=(None if rv_prev is None or own is None else int(own < rv_prev - 1e-9 or (own <= 1.0 + 1e-9 and rv_prev <= 1.0 + 1e-9))),
                             chat="\n".join(m for _, m, _ in t if m), chat_reasoning="\n---\n".join(x for _, _, x in t if x), n_msgs=len(t),
                             plan=q.get("plan", ""), rationale=q.get("rationale", ""), quote_reasoning=q.get("quote_reasoning", ""),
                             self_report=q.get("self_report"), q_answer=a.get("q_answer", ""), q_reasoning=a.get("q_reasoning", "")))
    # post-game question (r4): stored with round 0 or after the last round
    for (r, s), a in qa.items():
        if r not in market:
            rows.append(dict(model=model, trial_id=tid, arm=arm, round=r, seat=s, postgame=1, q_answer=a["q_answer"], q_reasoning=a["q_reasoning"]))
    return rows


def main():
    set_affinity()
    jobs, games = [], []
    for model, p in RUNCSV.items():
        r = pd.read_csv(p, low_memory=False)
        s = r[r.arm.isin(ARMS) & (r.penalty_point == 1) & (r.in_primary == 1)].copy()
        s["model"] = model
        games.append(s)
        jobs += [(model, row.played_trial_id if isinstance(row.played_trial_id, str) else row.trial_id, row.arm, row.source_root)
                 for row in s.itertuples()]
    with Pool(6) as pool:
        out = pool.map(one, jobs, chunksize=4)
    fr = pd.DataFrame([x for rows in out for x in rows])
    missing = [j for j, rows in zip(jobs, out) if not rows]
    print("games", len(jobs), "missing", len(missing), missing[:5])
    for model in RUNCSV:
        fr[fr.model == model].to_pickle("%s/firm_rounds_%s.pkl" % (WORK, model))
        g = [x for x in games if x.model.iloc[0] == model][0]
        g.to_csv("%s/games_%s.csv" % (WORK, model), index=False)
        print(model, "firm-rounds", (fr.model == model).sum())


if __name__ == "__main__":
    main()
