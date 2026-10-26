"""Build the monitor and label requests (JSONL) from the extracted firm-rounds (Created by Claude at the prompting of the repository owner)."""
import json
import sys

import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
from common import WORK, INTRO  # noqa: E402
from prompts import LABEL_SYSTEM, MONITOR_SYSTEM, label_user, monitor_user  # noqa: E402

FIRM = {"llm1": "Firm A", "llm2": "Firm B", "llm3": "Firm C"}


def clip(t, n):
    t = (t or "").strip()
    if len(t) <= n:
        return t
    h = n // 2
    return t[:h] + "\n[... middle omitted ...]\n" + t[-h:]


def body(g, col, n):
    parts = []
    for rd, gg in g.groupby("round"):
        seg = []
        for x in gg.itertuples():
            t = getattr(x, col)
            if isinstance(t, str) and t.strip():
                seg.append("%s:\n%s" % (FIRM.get(x.seat, x.seat), clip(t, n)))
        if seg:
            parts.append("ROUND %d\n" % rd + "\n\n".join(seg))
    return "\n\n".join(parts)


def main():
    reqs = []
    for model in ["gptoss", "qwen"]:
        fr = pd.read_pickle("%s/firm_rounds_%s.pkl" % (WORK, model))
        if "postgame" not in fr:
            fr["postgame"] = 0
        fr = fr[fr.postgame.fillna(0) != 1].copy()
        ins = fr.arm.isin(["r2s-confidant", "r3s-public"])
        fr.loc[ins, "q_answer"] = fr.loc[ins, "self_report"].astype(object).where(fr.loc[ins, "self_report"].notna(), "")
        fr["rat"] = "Plan: " + fr.plan.fillna("").str.strip() + "\nRationale: " + fr.rationale.fillna("").str.strip()
        # ---- firm-round LABEL requests
        chans = {"rationale": "rat", "chat": "chat", "answers": "q_answer", "reasoning": "quote_reasoning"}
        for r in fr.itertuples():
            for ch, col in chans.items():
                txt = getattr(r, col)
                if not isinstance(txt, str) or not txt.strip():
                    continue
                if ch == "answers" and r.arm not in INTRO:
                    continue
                rid = "L|%s|%s|%d|%s|%s" % (model, r.trial_id, r.round, r.seat, ch)
                reqs.append(dict(id=rid, effort="low", max_tokens=1200,
                                 messages=[{"role": "system", "content": LABEL_SYSTEM},
                                           {"role": "user", "content": label_user(ch, clip(txt, 8000))}]))
        # ---- game-level MONITOR requests (rounds 1-3)
        e = fr[fr["round"] <= 3]
        for tid, g in e.groupby("trial_id"):
            arm = g.arm.iloc[0]
            g = g.sort_values(["round", "seat"])
            bodies = {"chat": body(g, "chat", 4000), "rationale": body(g, "rat", 1500), "reasoning": body(g, "quote_reasoning", 3000)}
            if arm in INTRO:
                bodies["answers"] = body(g, "q_answer", 2500)
                bodies["qreasoning"] = body(g, "q_reasoning", 3000)
                ac = []
                for rd, gg in g.groupby("round"):
                    seg = ["ROUND %d" % rd]
                    for x in gg.itertuples():
                        if isinstance(x.chat, str) and x.chat.strip():
                            seg.append("%s chat:\n%s" % (FIRM.get(x.seat, x.seat), clip(x.chat, 4000)))
                    for x in gg.itertuples():
                        if isinstance(x.q_answer, str) and x.q_answer.strip():
                            seg.append("%s answer to the after-round question:\n%s" % (FIRM.get(x.seat, x.seat), clip(x.q_answer, 2500)))
                    ac.append("\n\n".join(seg))
                bodies["answers+chat"] = "\n\n".join(ac)
            for ch, b in bodies.items():
                if not b.strip():
                    continue
                reqs.append(dict(id="G|%s|%s|%s" % (model, tid, ch), effort="medium", max_tokens=4000,
                                 messages=[{"role": "system", "content": MONITOR_SYSTEM},
                                           {"role": "user", "content": monitor_user(ch, b)}]))
    with open(WORK + "/requests.jsonl", "w", encoding="utf8") as f:
        for q in reqs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    s = pd.Series([q["id"].split("|")[0] + "|" + q["id"].split("|")[1] + "|" + q["id"].split("|")[-1] for q in reqs]).value_counts()
    print(s.to_string())
    print("total", len(reqs), "chars", sum(len(q["messages"][1]["content"]) for q in reqs))


if __name__ == "__main__":
    main()
