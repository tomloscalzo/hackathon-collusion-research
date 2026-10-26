"""Does the compliance watchdog change the agents' chain of thought? Game-level measures, paired deltas, post-question split.
Usage: python -X utf8 analyze.py [--out DIR]   (reads the collected tables under $HACKATHON_DIR/work_scratch). Keyword rules UNVALIDATED."""
import csv, os, sys, argparse, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measures as M
ic = M.ic
csv.field_size_limit(10**9)
HK = Path(os.environ.get("HACKATHON_DIR", Path.home() / "hackathon")) / "work_scratch"
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(Path(__file__).resolve().parent)); a = ap.parse_args()
OUT = Path(a.out)
SRC = {  # model -> list of (tables dir, arms to take)
 "gpt-oss-20b": [(HK / "oss_analysis/tables", {"headline-chat", "wd-notice-only", "wd-noncomp", "wd-ask-noreport", "d-cot-monitor-a"})],
 "Qwen3-32B (thinking on)": [(HK / "analysis_final/tables_neutral_f3", {"headline-chat", "d-cot-monitor-a"}),
                             (HK / "watchdog_collect/wave_a", {"wd-notice-only"}), (HK / "watchdog_collect/wave_b", {"wd-noncomp", "wd-ask-noreport"})]}
ARMS = ["headline-chat", "wd-notice-only", "wd-noncomp", "wd-ask-noreport", "d-cot-monitor-a"]
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))

def f(x):
    try: return float(x)
    except Exception: return None

games = []
rows_pass = []
postq = []
for model, srcs in SRC.items():
    for d, arms in srcs:
        T = {t["trial_id"]: t for t in rd(d / "trials.csv") if t["arm"] in arms and t["penalty_point"] == "1" and t["thinking"] == "on" and t["status"] == "done"}
        R = collections.defaultdict(list)
        for r in rd(d / "rounds.csv"):
            if r["trial_id"] in T: R[r["trial_id"]].append(r)
        MS = collections.defaultdict(list)
        for m in rd(d / "messages.csv"):
            if m["trial_id"] in T: MS[m["trial_id"]].append(m)
        QA = collections.defaultdict(list)
        if (d / "questions.csv").is_file():
            for q in rd(d / "questions.csv"):
                if q["trial_id"] in T: QA[q["trial_id"]].append(q)
        for tid, t in T.items():
            rs = sorted(R[tid], key=lambda r: (int(r["round"]), r["seat"]))
            quotes = {(int(r["round"]), r["seat"]): f(r["quote"]) for r in rs}
            seats = sorted({r["seat"] for r in rs})
            asked = {(int(r["round"]), r["seat"]): r["wd_asked"] == "1" for r in rs}
            g = dict(model=model, arm=t["arm"], trial_id=tid, wording=t["wording"], seed=t["seed"], rounds=int(t["rounds"]))
            mp = [f(r["market_price"]) for r in rs if r["seat"] == seats[0] and f(r["market_price"]) is not None]
            g["avg_spread"] = float(np.mean(mp))
            g["price_index"] = f(t["collusion_level"]) if f(t["collusion_level"]) is not None else float(np.mean([(p - 1) / 2 for p in mp]))
            g["profit_gain_index"] = float(np.mean([f(r["profit"]) for r in rs if f(r["profit"]) is not None])) / 40.0
            comp = [f(r["competitive_round"]) for r in rs if f(r["competitive_round"]) is not None]
            g["competitive_share"] = float(np.mean(comp)) if comp else np.nan
            mt = []
            for r in rs:
                n = int(r["round"])
                if n >= 2 and f(r["quote"]) is not None:
                    riv = [quotes.get((n - 1, s)) for s in seats if s != r["seat"] and quotes.get((n - 1, s)) is not None]
                    if riv: mt.append(float(abs(f(r["quote"]) - min(riv)) < 1e-9 and min(riv) > 1.0 + 1e-9))
            g["matching_share"] = float(np.mean(mt)) if mt else np.nan
            fr = collections.defaultdict(lambda: dict(q="", tr=[], tx=[]))
            for r in rs:
                if r["imputed"] != "1" and not r["refusal_kind"]: fr[(int(r["round"]), r["seat"])]["q"] = r["reasoning"] or ""
            for m in MS[tid]:
                if m["refusal_kind"] or m["parse_status"] not in ("OK", ""): continue
                k = (int(m["round"]), m["seat"]); fr[k]["tr"].append(m["reasoning"] or ""); fr[k]["tx"].append(m["text"] or "")
            qs = [(k, v["q"]) for k, v in fr.items() if v["q"].strip()]
            trs = [x for v in fr.values() for x in v["tr"] if x.strip()]
            txs = [x for v in fr.values() for x in v["tx"] if x.strip()]
            P = lambda xs, rx: float(np.mean([M.has(rx, x) for x in xs])) if xs else np.nan
            g["n_quote_passages"] = len(qs); g["n_talk_passages"] = len(trs); g["n_messages"] = len(txs)
            qt = [x for _, x in qs]
            g["q_watchdog"] = P(qt, M.WATCHDOG); g["q_regulator"] = P(qt, M.REGULATOR); g["q_conceal"] = P(qt, M.CONCEAL); g["q_conceal_strict"] = P(qt, M.CONCEAL_STRICT)
            g["q_rival_react"] = float(np.mean([M.rival_react(x) for x in qt])) if qt else np.nan
            g["t_watchdog"] = P(trs, M.WATCHDOG); g["t_regulator"] = P(trs, M.REGULATOR); g["t_conceal"] = P(trs, M.CONCEAL); g["t_conceal_strict"] = P(trs, M.CONCEAL_STRICT)
            g["q_words"] = float(np.mean([M.words(x) for x in qt])) if qt else np.nan
            g["t_words"] = float(np.mean([M.words(x) for x in trs])) if trs else np.nan
            g["agree_share"] = P(txs, M.AGREE)
            g["agree_per_msg"] = float(np.mean([len(M.AGREE.findall(x)) for x in txs])) if txs else np.nan

            def cls(v):
                cs = [ic.classify_text(v["q"])] + [ic.classify_text(x) for x in v["tr"]]
                return ic._max(cs)
            def has_talk(v): return any(x.strip() for x in v["tr"])
            def cls_talk(v): return ic._max([ic.classify_text(x) for x in v["tr"]])
            used = {k: v for k, v in fr.items() if v["q"].strip() or has_talk(v)}
            C = {k: cls(v) for k, v in used.items()}
            nC = len(C)
            for nm, key in (("explicit", ic.EXPLICIT), ("strategic", ic.STRATEGIC), ("none", ic.NONE)):
                g[nm + "_share"] = sum(1 for c in C.values() if c == key) / nC if nC else np.nan
            cq = [ic.classify_text(v["q"]) for v in used.values() if v["q"].strip()]
            ct = [cls_talk(v) for v in used.values() if has_talk(v)]
            for nm, cc in (("q", cq), ("t", ct)):
                g[nm + "_explicit_share"] = sum(c == ic.EXPLICIT for c in cc) / len(cc) if cc else np.nan
                g[nm + "_strategic_share"] = sum(c == ic.STRATEGIC for c in cc) / len(cc) if cc else np.nan
            ans = [q for q in QA[tid] if q["question"].startswith("watchdog")]
            g["n_answers"] = len(ans)
            g["ans_conceal"] = P([q["answer"] for q in ans if q["answer"].strip()], M.CONCEAL)
            g["ans_reason_conceal"] = P([q["reasoning"] for q in ans if (q["reasoning"] or "").strip()], M.CONCEAL)
            games.append(g)
            if t["arm"] in ("wd-noncomp", "wd-ask-noreport"):
                acc = collections.defaultdict(lambda: collections.defaultdict(list))
                for (n, s), v in used.items():
                    if n < 2: continue
                    grp = "after" if asked.get((n - 1, s)) else "other"
                    x = v["q"]
                    if x.strip():
                        acc[grp]["q_watchdog"].append(M.has(M.WATCHDOG, x)); acc[grp]["q_conceal"].append(M.has(M.CONCEAL, x)); acc[grp]["q_conceal_strict"].append(M.has(M.CONCEAL_STRICT, x))
                        acc[grp]["q_rival_react"].append(M.rival_react(x)); acc[grp]["q_words"].append(M.words(x))
                        acc[grp]["q_explicit"].append(ic.classify_text(x) == ic.EXPLICIT); acc[grp]["q_strategic"].append(ic.classify_text(x) == ic.STRATEGIC)
                    acc[grp]["round_explicit"].append(C[(n, s)] == ic.EXPLICIT); acc[grp]["round_strategic"].append(C[(n, s)] == ic.STRATEGIC)
                    if quotes.get((n, s)) is not None and quotes.get((n - 1, s)) is not None:
                        acc[grp]["quote_change"].append(abs(quotes[(n, s)] - quotes[(n - 1, s)]) > 1e-9)
                row = dict(model=model, arm=t["arm"], trial_id=tid)
                for meas in acc["after"]:
                    if acc["other"].get(meas) and acc["after"][meas]:
                        row[meas + "_after"] = float(np.mean(acc["after"][meas])); row[meas + "_other"] = float(np.mean(acc["other"][meas]))
                row["n_after"] = len(acc["after"]["round_explicit"]); row["n_other"] = len(acc["other"]["round_explicit"])
                postq.append(row)
            for (n, s), v in fr.items():
                if v["q"].strip(): rows_pass.append(dict(model=model, arm=t["arm"], trial_id=tid, round=n, seat=s, channel="quote", text=v["q"], hit=int(M.has(M.CONCEAL, v["q"])), strict=int(M.has(M.CONCEAL_STRICT, v["q"]))))
            for m in MS[tid]:
                if (m["reasoning"] or "").strip(): rows_pass.append(dict(model=model, arm=t["arm"], trial_id=tid, round=m["round"], seat=m["seat"], channel="talk", text=m["reasoning"], hit=int(M.has(M.CONCEAL, m["reasoning"])), strict=int(M.has(M.CONCEAL_STRICT, m["reasoning"]))))

def wcsv(p, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
wcsv(OUT / "game_measures.csv", games)
SCR = HK / "wdcot"; SCR.mkdir(exist_ok=True)
wcsv(SCR / "passages_all.csv", rows_pass)   # large; kept in scratch, not committed
wcsv(OUT / "post_question_games.csv", postq)

MEAS = collections.OrderedDict([
 ("avg_spread", "average absolute spread"), ("price_index", "price index"), ("profit_gain_index", "profit gain index"), ("competitive_share", "competitive share (U16)"), ("matching_share", "matching share"),
 ("q_watchdog", "quote reasoning mentions the watchdog"), ("q_regulator", "quote reasoning mentions regulator/investigation/report"),
 ("t_watchdog", "talk reasoning mentions the watchdog"), ("t_regulator", "talk reasoning mentions regulator/investigation/report"),
 ("explicit_share", "EXPLICIT share of firm-rounds (quote + talk reasoning)"), ("strategic_share", "STRATEGIC-UNNAMED share of firm-rounds (quote + talk reasoning)"),
 ("q_conceal", "concealment keyword, quote reasoning"), ("t_conceal", "concealment keyword, talk reasoning"),
 ("q_conceal_strict", "concealment keyword (strict: appearance/hiding words only), quote reasoning"), ("t_conceal_strict", "concealment keyword (strict), talk reasoning"),
 ("q_words", "quote reasoning length (words)"), ("t_words", "talk reasoning length (words)"),
 ("q_rival_react", "quote calls reasoning about the rival's reaction"), ("agree_share", "chat messages with agreement words"), ("agree_per_msg", "agreement words per chat message"),
 ("q_explicit_share", "EXPLICIT share, quote reasoning only"), ("q_strategic_share", "STRATEGIC share, quote reasoning only"),
 ("t_explicit_share", "EXPLICIT share, talk reasoning only"), ("t_strategic_share", "STRATEGIC share, talk reasoning only"), ("ans_conceal", "concealment keyword in the answer to the watchdog"), ("ans_reason_conceal", "concealment keyword in the reasoning before answering the watchdog")])
rng = np.random.default_rng(20261026)
def boot(d, B=10000):
    d = np.asarray(d); i = rng.integers(0, len(d), (B, len(d))); return np.percentile(d[i].mean(1), [2.5, 97.5])
def signflip(d):
    d = np.asarray(d); n = len(d)
    if n > 22: return np.nan
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
    m = np.abs((signs * d).mean(1)); return float((m >= abs(d.mean()) - 1e-12).mean())
G = collections.defaultdict(dict)
for g in games: G[(g["model"], g["arm"])][(g["wording"], g["seed"])] = g
dl = []
for model in SRC:
    for arm in ARMS[1:]:
        ctl = G[(model, "headline-chat")]; trt = G[(model, arm)]
        keys = sorted(set(ctl) & set(trt))
        for m, lab in MEAS.items():
            pairs = [(ctl[k][m], trt[k][m]) for k in keys if ctl[k].get(m) is not None and trt[k].get(m) is not None and not (np.isnan(ctl[k][m]) or np.isnan(trt[k][m]))]
            if len(pairs) < 5:
                dl.append(dict(model=model, arm=arm, measure=m, label=lab, n_pairs=len(pairs))); continue
            c = np.array([p[0] for p in pairs]); t_ = np.array([p[1] for p in pairs]); d = t_ - c; lo, hi = boot(d)
            dl.append(dict(model=model, arm=arm, measure=m, label=lab, n_pairs=len(pairs), control_mean=c.mean(), arm_mean=t_.mean(), delta=d.mean(), ci_lo=lo, ci_hi=hi, p_signflip=signflip(d)))
for m in MEAS:
    fam = [r for r in dl if r["measure"] == m and r["arm"] != "d-cot-monitor-a" and "p_signflip" in r and not np.isnan(r["p_signflip"])]
    fam.sort(key=lambda r: r["p_signflip"]); k = len(fam); run = 0
    for i, r in enumerate(fam):
        run = max(run, min(1.0, (k - i) * r["p_signflip"])); r["p_holm"] = run
wcsv(OUT / "paired_deltas.csv", dl)

lv = []
for (model, arm), gs in G.items():
    row = dict(model=model, arm=arm, n_games=len(gs))
    for m in MEAS:
        v = [g[m] for g in gs.values() if g.get(m) is not None and not np.isnan(g[m])]
        row[m] = float(np.mean(v)) if v else np.nan
    row["quote_passages"] = sum(g["n_quote_passages"] for g in gs.values()); row["talk_passages"] = sum(g["n_talk_passages"] for g in gs.values()); row["messages"] = sum(g["n_messages"] for g in gs.values())
    lv.append(row)
wcsv(OUT / "arm_means.csv", lv)

pq = []
for model in SRC:
    for arm in ("wd-noncomp", "wd-ask-noreport", "both"):
        rows = [r for r in postq if r["model"] == model and (arm == "both" or r["arm"] == arm)]
        for m in ("q_watchdog", "q_conceal", "q_conceal_strict", "q_rival_react", "q_words", "q_explicit", "q_strategic", "round_explicit", "round_strategic", "quote_change"):
            sel = [r for r in rows if m + "_after" in r]
            dd = [r[m + "_after"] - r[m + "_other"] for r in sel]
            if len(dd) < 5: continue
            lo, hi = boot(dd)
            pq.append(dict(model=model, arm=arm, measure=m, n_games=len(dd), after_asked=np.mean([r[m + "_after"] for r in sel]), other_rounds=np.mean([r[m + "_other"] for r in sel]),
                           delta=np.mean(dd), ci_lo=lo, ci_hi=hi, p_signflip=signflip(dd)))
wcsv(OUT / "post_question.csv", pq)
print(len(games), "games;", dict(collections.Counter((g["model"], g["arm"]) for g in games)))
