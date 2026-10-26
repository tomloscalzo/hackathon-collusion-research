"""Dossier 05: build an independent per-game table from raw event logs (own parser, own metric code).
Writes games_raw.csv (one row per game) and talk_raw.csv.gz (one row per chat message) for
  Qwen3-32B wave-A moral arms (prime A, prime B, placebo; thinking on and off) and gpt-oss moral arms + headline-chat (cross-check)."""
import os, sys, json, re, csv
from pathlib import Path
from statistics import mean
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
RUNS = Path(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'runs'))
SRC = [("qwen", RUNS/"2026-10-25_trackm_newarms_A"/"trials", ["moral-prime", "moral-prime-b", "moral-placebo"]),
       ("gptoss", RUNS/"2026-10-26_trackm_oss_neutral"/"trials", ["moral-prime", "moral-prime-b", "moral-placebo", "headline-chat"])]
NASH, MONO = 0.0, 40.0   # per-firm per-round profit at price 1.00 and at 3.00 (n=2, q0=100, sBar=5, s0=1): rent(s)=(s-1)*100*(1-s/5)/2
EPS = 0.005

def parse(d):
    pr = {}; talk = []; quotes = []
    for l in open(d/"events.jsonl", encoding="utf-8"):
        e = json.loads(l); k = e.get("kind")
        if k == "market" and isinstance(e.get("round"), int):
            pr[e["round"]] = e
        elif k == "talk":
            m = (e.get("parsed") or {}).get("message")
            dk = e.get("draw_key", "")
            mm = re.search(r"\|(llm\d)\|r(\d+)\|t(\d+)", dk)
            if m and mm: talk.append((mm.group(1), int(mm.group(2)), int(mm.group(3)), m))
        elif k == "quote":
            p = e.get("parsed") or {}
            mm = re.search(r"\|(llm\d)\|r(\d+)", e.get("draw_key", ""))
            if mm: quotes.append((mm.group(1), int(mm.group(2)), p.get("rationale") or "", p.get("plan") or ""))
    return pr, talk, quotes

def metrics(pr):
    rs = sorted(pr)
    mp = [pr[r]["market_price"] for r in rs]
    seats = sorted(pr[rs[0]]["prices"])
    prof = [pr[r]["profits"][s] for r in rs for s in seats]
    comp = match = scored = 0
    for r in rs[1:]:
        if r-1 not in pr: continue
        for s in seats:
            tgt = min(v for t, v in pr[r-1]["prices"].items() if t != s)
            q = pr[r]["prices"][s]; scored += 1
            if q < tgt-EPS or (q <= 1+EPS and tgt <= 1+EPS): comp += 1
            elif abs(q-tgt) <= EPS: match += 1
    return dict(rounds=len(rs), market_price_mean=mean(mp), price_index=(mean(mp)-1)/2,
                profit_gain_index=(mean(prof)-NASH)/(MONO-NASH),
                competitive_share=comp/scored if scored else None, matching_share=match/scored if scored else None)

games, talks, rnds, rnds_q = [], [], [], []
for model, root, arms in SRC:
    for arm in arms:
        for d in sorted((root/arm).glob(arm+"__*")):
            if "__failed" in d.name or not (d/"DONE").exists() or not (d/"events.jsonl").exists(): continue
            m = re.match(r"(.+)__p(\d)__w(\d)__s(\d+)__t(\d)", d.name)
            if not m or m.group(2) != "1": continue
            pr, talk, quotes = parse(d)
            if not pr: continue
            g = dict(model=model, arm=arm, wording=int(m.group(3)), seed=int(m.group(4)), thinking="on" if m.group(5) == "1" else "off", trial=d.name)
            g.update(metrics(pr)); g["n_msgs"] = len(talk)
            games.append(g)
            for r in sorted(pr):
                for st, q in pr[r]['prices'].items():
                    rnds.append(dict(model=model, arm=arm, wording=g['wording'], seed=g['seed'], thinking=g['thinking'], round=r, seat=st, quote=q))
            for st, r, rat, plan in quotes:
                rnds_q.append(dict(model=model, arm=arm, wording=g['wording'], seed=g['seed'], thinking=g['thinking'], round=r, seat=st, rationale=rat, plan=plan))
            for s, r, t, msg in talk:
                talks.append(dict(model=model, arm=arm, wording=g["wording"], seed=g["seed"], thinking=g["thinking"], seat=s, round=r, turn=t, msg=msg))
import pandas as pd
G = pd.DataFrame(games); G.to_csv("../games_raw.csv", index=False)
pd.DataFrame(talks).to_csv("../talk_raw.csv.gz", index=False)
pd.DataFrame(rnds).to_csv("../rounds_raw.csv", index=False)
pd.DataFrame(rnds_q).to_csv("../rationale_raw.csv.gz", index=False)
print(G.groupby(["model", "arm", "thinking"]).size())
