"""moral-primes ad-hoc analysis, gpt-oss-20b (reasoning effort medium) vs Qwen3-32B (thinking on).
Run: python -I -X utf8 analyse.py   (needs the analysis checkout's tools/trial for the Qwen wave-A raw recompute)"""
import sys, csv
from pathlib import Path
from statistics import mean
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_common"))
import oss_common as oc
import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
OSS = (_HK + "/work_scratch/oss_analysis/step1/final_t1/run.csv")
QRUN = oc.QWEN_RUN
QWAVE = (_HK + "/runs/2026-10-25_trackm_newarms_A")
QGM = HERE.parent.parent.parent / "ad-hoc-targeted-analysis" / "wave-a-moral-and-threat0" / "data" / "game_metrics.csv"
MET = [m[0] for m in oc.METRICS]

oss = oc.load_oss(OSS)
oss_all = oc.load_oss(OSS, include_bug=True)


def qwen_wave():
    repo = HERE
    while not (repo / "tools" / "trial" / "collect.py").exists():
        repo = repo.parent
    sys.path.insert(0, str(repo / "tools" / "trial"))
    import collect, analysis_m as am, run_csv, derive
    keep = {r["trial_id"] for r in csv.DictReader(open(QGM, encoding="utf-8"))
            if r["arm"] in ("moral-prime", "moral-prime-b", "moral-placebo") and r["thinking"] == "on"}
    out = []
    for ev in sorted(Path(QWAVE, "trials").rglob("events.jsonl")):
        d = ev.parent
        if "__failed" in d.name:
            continue
        params = collect.load_params(d)
        row, rounds, *_ = collect.trial_rows(d)
        if row["status"] != "done" or row["trial_id"] not in keep:
            continue
        floor = row["competitive_price"] if row["competitive_price"] != "" else 1.0
        coll = row["collusive_price"] if row["collusive_price"] != "" else 3.0
        tables = {"trials": run_csv.csvify([row]), "rounds": run_csv.csvify(rounds), "messages": [], "questions": [], "refusals": []}
        g = am.build_games(tables, float(floor), float(coll))[row["trial_id"]]
        m = am.measures(g["rounds"], 0.8)
        b = run_csv.benchmarks_of(params)
        pr = [x["profit"] for x in rounds if isinstance(x.get("profit"), (int, float))]
        gain = (mean(pr) - b[0]) / (b[1] - b[0]) if pr and b and b[1] != b[0] else None
        cls3 = run_csv.classify3(rounds, floor, collect._tick(params))
        matching = sum(1 for v in cls3.values() if v == "matching") / len(cls3) if cls3 else None
        last = {}
        for e in derive.read_events(d / "events.jsonl"):
            if e.get("kind") == "market" and isinstance(e.get("round"), int):
                last[e["round"]] = e
        mp = [run_csv.num(e.get("market_price")) for k, e in sorted(last.items())]
        mp = [x for x in mp if x is not None]
        out.append(dict(trial_id=row["trial_id"], arm=row["arm"], penalty_point="1", wording=str(int(row["wording"])), seed=str(int(row["seed"])),
                        price_index=float(row["collusion_level"]), market_price_mean=mean(mp) if mp else None, matching_share=matching,
                        competitive_share=m["competitive_share"], profit_gain_index=gain))
    return out


qw = qwen_wave()
qh = [r for r in oc.load_qwen(QRUN, "on") if r["arm"] == "headline-chat" and r["penalty_point"] == "1"]
qrows = qw + qh
with open(HERE / "qwen_games_used.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["arm", "wording", "seed"] + MET)
    for r in qrows:
        w.writerow([r["arm"], r["wording"], r["seed"]] + [r.get(m) for m in MET])

CON = [("moral-prime - headline-chat (p1)", ("moral-prime", 1), ("headline-chat", 1)),
       ("moral-prime-b - headline-chat (p1)", ("moral-prime-b", 1), ("headline-chat", 1)),
       ("moral-placebo - headline-chat (p1)", ("moral-placebo", 1), ("headline-chat", 1)),
       ("moral-prime - moral-placebo", ("moral-prime", 1), ("moral-placebo", 1)),
       ("moral-prime-b - moral-placebo", ("moral-prime-b", 1), ("moral-placebo", 1)),
       ("moral-prime - moral-prime-b", ("moral-prime", 1), ("moral-prime-b", 1))]


def f(x):
    return "" if x is None else "%.6f" % x


out = []
for lab, a, b in CON:
    for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qrows)):
        p = oc.paired(rows, a, b)
        for m in MET:
            s = p[m]
            out.append([model, lab, m, s["n_pairs"], f(s["mean_a"]), f(s["mean_b"]), f(s["diff"]), f(s["lo"]), f(s["hi"])])
with open(HERE / "standard_metrics.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"])
    w.writerows(out)

sens = []
oss_ne = [r for r in oss if r.get("empty_talk_done_count") in ("", "0", None, "0.0")]
for lab, a, b in CON:
    p = oc.paired(oss_ne, a, b)
    for m in MET:
        s = p[m]
        sens.append(["drop games with empty_talk_done_count>0", lab, m, s["n_pairs"], f(s["mean_a"]), f(s["mean_b"]), f(s["diff"]), f(s["lo"]), f(s["hi"])])
pool = {}
for r in oss_all:
    if r["arm"] in ("headline-chat", "hrep-fx-chat-p1", "hrep-nx-chat-p1") and str(r["penalty_point"]) == "1":
        pool.setdefault((r["wording"], r["seed"]), []).append(r)
prow = []
for (wd, sd), rs in pool.items():
    d = dict(arm="headline-pooled", penalty_point="1", wording=wd, seed=sd)
    for m in MET:
        d[m] = str(mean(float(x[m]) for x in rs if x.get(m) not in ("", None)))
    prow.append(d)
for a in ("moral-prime", "moral-prime-b", "moral-placebo"):
    p = oc.paired(oss + prow, (a, 1), ("headline-pooled", 1))
    for m in MET:
        s = p[m]
        sens.append(["control = headline-chat p1 pooled with hrep-fx-chat-p1 and hrep-nx-chat-p1 (build-bug headline replicates)", a + " - pooled headline", m, s["n_pairs"], f(s["mean_a"]), f(s["mean_b"]), f(s["diff"]), f(s["lo"]), f(s["hi"])])
with open(HERE / "sensitivity.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["sensitivity", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi"])
    w.writerows(sens)

cm = []
for model, rows in (("gpt-oss-20b", oss), ("Qwen3-32B", qrows)):
    for arm in ("headline-chat", "moral-placebo", "moral-prime", "moral-prime-b"):
        c = oc.cell_means(rows, arm, 1)
        sub = [r for r in rows if r["arm"] == arm and str(r["penalty_point"]) == "1"]
        et = [float(r["empty_talk_done_count"]) for r in sub if r.get("empty_talk_done_count") not in ("", None)]
        for m in MET:
            cm.append([model, arm, m, c[m]["n"], f(c[m]["mean"]), f(c[m]["lo"]), f(c[m]["hi"]), f(mean(et)) if et else "", sum(1 for x in et if x > 0) if et else ""])
with open(HERE / "cell_means.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["model", "arm", "metric", "n_games", "mean", "lo", "hi", "empty_talk_done_mean", "games_with_empty_talk"])
    w.writerows(cm)

ts = []
for arm in ("headline-chat", "moral-placebo", "moral-prime", "moral-prime-b"):
    sub = [r for r in oss if r["arm"] == arm and str(r["penalty_point"]) == "1"]
    cs = [float(r["competitive_share"]) for r in sub]
    pi = [float(r["price_index"]) for r in sub]
    rp = [float(r["rounds_played"]) for r in sub]
    ts.append([arm, len(sub), "%.2f" % mean(rp), sum(1 for x in pi if x < 0.1), sum(1 for x in pi if x > 0.6), sum(1 for x in cs if x > 0.5)])
with open(HERE / "game_counts.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["arm", "n_games", "mean_rounds_played", "games_price_index_below_0.1", "games_price_index_above_0.6", "games_competitive_share_above_0.5"])
    w.writerows(ts)
print("done", len(qw), len(qh))
