"""Extract compact per-round tables (quotes, plans, chat, reasoning) for the side-channel analysis.

Reads the primary trial list of each run from its step-1 run.csv (status done, in_primary 1, not a build-bug arm)
and joins to trial folders on (source_root, played_trial_id). Writes pickles to OUT.
"""
import json, os, sys
from multiprocessing import Pool
import pandas as pd

HK = os.environ.get("HACKATHON_DIR", os.path.join(os.path.expanduser("~"), "hackathon"))
OUT = os.path.join(HK, "work_scratch", "side_channels")
OSS_RUN = os.path.join(HK, "work_scratch", "oss_analysis", "step1", "final", "run.csv")
QWEN_RUN = os.path.join(HK, "work_scratch", "analysis_final", "steps", "neutral", "step1", "run.csv")
OSS_ARMS = {"headline-chat", "headline-tacit", "m-asym", "d-cot-monitor-a", "d-placebo", "ctl-32b-compete",
            "ctl-32b-joint", "d-conflict", "d-conflict-ethics"}
QWEN_ARMS = {"headline-chat", "headline-tacit", "m-asym", "d-cot-monitor-a", "d-cot-monitor-b", "d-placebo",
             "ctl-32b-compete", "ctl-32b-joint"}


def parse(job):
    model, root, arm, tid, meta = job
    path = os.path.join(HK, "runs", root, "trials", arm, tid, "events.jsonl")
    q, t, m = [], [], []
    try:
        fh = open(path, encoding="utf-8")
    except OSError:
        return None
    with fh:
        for line in fh:
            e = json.loads(line)
            k = e.get("kind")
            base = dict(model=model, source_root=root, trial_id=tid, **meta)
            if k == "quote":
                p = e.get("parsed") or {}
                q.append(dict(base, round=e["round"], seat=e["seat"], quote=e.get("quote", p.get("quote")),
                              plan=p.get("plan"), rationale=p.get("rationale"), reasoning=e.get("reasoning"),
                              outcome=e.get("outcome")))
            elif k == "talk":
                p = e.get("parsed") or {}
                t.append(dict(base, round=e["round"], seat=e["seat"], turn=e.get("turn"),
                              message=p.get("message"), done=p.get("done"), reasoning=e.get("reasoning"),
                              outcome=e.get("outcome"), seq=e.get("seq")))
            elif k == "market":
                for s, v in (e.get("prices") or {}).items():
                    m.append(dict(base, round=e["round"], seat=s, price=v, market_price=e.get("market_price")))
    return q, t, m


def jobs_from_run(model, run, arms):
    r = pd.read_csv(run, low_memory=False)
    r = r[(r.status == "done") & (r.in_primary == 1)]
    if "arm_build_bug" in r:
        r = r[r.arm_build_bug.fillna(0).astype(int) != 1]
    r = r[r.arm.isin(arms)]
    out = []
    for _, x in r.iterrows():
        meta = dict(arm=x.arm, penalty_point=int(x.penalty_point), thinking=x.thinking, wording=int(x.wording), seed=int(x.seed))
        out.append((model, x.source_root, x.arm, x.played_trial_id, meta))
    return out


def copybot_jobs():
    root = "2026-10-25_trackm_copybot"
    out = []
    for arm in os.listdir(os.path.join(HK, "runs", root, "trials")):
        for tid in os.listdir(os.path.join(HK, "runs", root, "trials", arm)):
            d = os.path.join(HK, "runs", root, "trials", arm, tid)
            if not os.path.exists(os.path.join(d, "DONE")):
                continue
            parts = tid.split("__")
            meta = dict(arm=arm, penalty_point=int(parts[1][1:]), thinking="on" if parts[4] == "t1" else "off",
                        wording=int(parts[2][1:]), seed=int(parts[3][1:]))
            out.append(("qwen3-32b", root, arm, tid, meta))
    return out


if __name__ == "__main__":
    jobs = jobs_from_run("gpt-oss-20b", OSS_RUN, OSS_ARMS) + jobs_from_run("qwen3-32b", QWEN_RUN, QWEN_ARMS) + copybot_jobs()
    print(len(jobs), "trials")
    with Pool(6) as pool:
        res = pool.map(parse, jobs, chunksize=4)
    miss = [j[3] for j, r in zip(jobs, res) if r is None]
    print("missing", len(miss), miss[:5])
    Q, T, M = [], [], []
    for r in res:
        if r:
            Q += r[0]; T += r[1]; M += r[2]
    pd.DataFrame(Q).to_pickle(os.path.join(OUT, "quotes.pkl"))
    pd.DataFrame(T).to_pickle(os.path.join(OUT, "talk.pkl"))
    pd.DataFrame(M).to_pickle(os.path.join(OUT, "market.pkl"))
    print(len(Q), len(T), len(M))
