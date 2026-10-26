#!/usr/bin/env python3
"""gpt-oss-20b replication of the Qwen3-32B Track M headline patterns (rerunnable; DONE games only).

Usage (from the repo root):
  python -X utf8 results/ad-hoc-targeted-analysis/gpt-oss-replication/analyze_oss_replication.py \
      --oss-run <runs/2026-10-25_trackm_oss> --qwen-tables <neutral step1 tables dir> --scratch <scratch dir> [--out <dir>]

Steps: (1) tools/trial/collect.py on the gpt-oss trials into --scratch (raw tables are NOT checked in);
(2) per-game metrics for gpt-oss and the Qwen3-32B thinking-on controls; (3) the tables written to --out (default: this folder).
Only games with a DONE marker are used (collect.py status "done"); trials whose directory name carries __failed_empty_talk are
dropped. A chat cell with fewer than 20 DONE games is flagged INCOMPLETE. Paired tests use only (wording, seed) pairs that are
DONE in both arms. Bootstrap: percentile, 10,000 resamples of pairs, fixed seed. Standard library plus numpy.
"""
import argparse, collections, csv, json, math, os, re, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "trial"))
import competitiveness as comp  # noqa: E402

FLOOR, TICK = 1.0, 0.01
PRINTED = [1.00, 1.50, 2.00, 2.50, 3.00, 3.50, 4.00]
ARMS_OSS = {"tacit_p1": "oss-headline-tacit-p1", "chat_p1": "oss-headline-chat-p1", "chat_p5": "oss-headline-chat-p5"}
ARMS_QWEN = {"tacit_p1": ("headline-tacit", "1"), "chat_p1": ("headline-chat", "1"), "chat_p5": ("headline-chat", "5")}
METRICS = ["price_index", "competitive_share", "matching_share", "undercuts"]
NB, MARGIN = 10000, 0.15


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf8", newline="")))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def collect(oss_run, scratch):
    out = Path(scratch) / "collected"
    cmd = [sys.executable, "-X", "utf8", str(REPO / "tools/trial/collect.py"), str(Path(oss_run) / "trials"), str(out), "--include-pilot"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return out


def game_table(trials, rounds):
    """per-game metrics. trials/rounds are lists of dicts (collect.py format)."""
    by = collections.defaultdict(list)
    for r in rounds:
        by[r["trial_id"]].append(r)
    out = {}
    for t in trials:
        tid = t["trial_id"]
        rows = by.get(tid, [])
        flags, _ = comp.classify(rows, FLOOR, TICK)
        q = {}
        for r in rows:
            v = num(r["quote"])
            if v is not None:
                q[(int(r["round"]), r["seat"])] = v
        n = len(flags)
        c = sum(flags.values())
        m = 0
        for (rnd, seat), isc in flags.items():
            rivals = [v for (rr, s), v in q.items() if rr == rnd - 1 and s != seat]
            tgt = min(rivals)
            if (not isc) and abs(q[(rnd, seat)] - tgt) <= TICK / 2 and tgt > FLOOR + TICK / 2:
                m += 1
        m_wording = t["wording"]
        out[tid] = dict(trial_id=tid, arm=t["arm"], penalty_point=t["penalty_point"], pair=(t["wording"], t["seed"]),
                        rounds=int(t["rounds"] or 0), price_index=num(t["collusion_level"]),
                        competitive_share=c / n if n else None, matching_share=m / n if n else None,
                        undercuts=num(t["undercuts"]), scored_firm_rounds=n)
    return out


def boot_ci(vals, rng):
    v = np.asarray(vals, float)
    idx = rng.integers(0, len(v), (NB, len(v)))
    b = v[idx].mean(1)
    return np.percentile(b, [2.5, 97.5])


def perm_p(d, rng=None):
    """exact paired sign-flip permutation p (two-sided) for n <= 20 else Monte Carlo."""
    d = np.asarray(d, float)
    n = len(d)
    obs = abs(d.mean())
    if n <= 20:
        signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
        m = np.abs((signs * d).mean(1))
    else:
        signs = rng.choice([-1, 1], (200000, n))
        m = np.abs((signs * d).mean(1))
    return float((m >= obs - 1e-12).mean())


def pair_diffs(games, armA, armB, metric):
    """dict pair -> value(A) - value(B) over pairs present in both arms."""
    a = {g["pair"]: g[metric] for g in games if g["key"] == armA and g[metric] is not None}
    b = {g["pair"]: g[metric] for g in games if g["key"] == armB and g[metric] is not None}
    ks = sorted(set(a) & set(b))
    return ks, np.array([a[k] - b[k] for k in ks]), np.array([b[k] for k in ks])


def fmt(x, d=3):
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), d)


def write(path, rows, cols):
    with open(path, "w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def undercut_reaction(rounds, ids):
    """firm-rounds r>=2. undercut = rival's last quote below own last quote and above the floor.
    lowers = quote below own last quote. Returns counts and per-game rows for cluster bootstrap."""
    by = collections.defaultdict(dict)
    for r in rounds:
        if r["trial_id"] in ids and num(r["quote"]) is not None:
            by[r["trial_id"]][(int(r["round"]), r["seat"])] = num(r["quote"])
    per_game = {}
    for tid, q in by.items():
        c = collections.Counter()
        for (rnd, seat), v in q.items():
            if rnd < 2 or (rnd - 1, seat) not in q:
                continue
            own = q[(rnd - 1, seat)]
            rivals = [x for (rr, s), x in q.items() if rr == rnd - 1 and s != seat]
            if not rivals:
                continue
            rv = min(rivals)
            und = rv < own - TICK / 2 and rv > FLOOR + TICK / 2
            low = v < own - TICK / 2
            reach = v <= rv + TICK / 2
            k = "U" if und else "N"
            c[k] += 1
            c[k + "_low"] += low
            c[k + "_reach"] += reach
        per_game[tid] = c
    return per_game


def ur_summary(per_game, rng, label, model):
    tot = collections.Counter()
    for c in per_game.values():
        tot.update(c)
    def rate(c, k, s):
        return c[k + s] / c[k] if c[k] else float("nan")
    games = list(per_game.values())
    diffs = []
    for _ in range(2000):
        s = collections.Counter()
        for i in rng.integers(0, len(games), len(games)):
            s.update(games[i])
        diffs.append(rate(s, "U", "_low") - rate(s, "N", "_low"))
    lo, hi = np.nanpercentile(diffs, [2.5, 97.5])
    return dict(model=model, arm=label, games=len(games), undercut_firm_rounds=tot["U"], other_firm_rounds=tot["N"],
                p_lower_if_undercut=fmt(rate(tot, "U", "_low")), p_lower_otherwise=fmt(rate(tot, "N", "_low")),
                diff=fmt(rate(tot, "U", "_low") - rate(tot, "N", "_low")), diff_ci_lo=fmt(lo), diff_ci_hi=fmt(hi),
                p_at_or_below_rival_if_undercut=fmt(rate(tot, "U", "_reach")))


def focal(rounds, ids):
    qs = [num(r["quote"]) for r in rounds if r["trial_id"] in ids and num(r["quote"]) is not None]
    return qs


def calls_stats(oss_run, ids):
    rows = collections.defaultdict(list)
    for tid in ids:
        for arm_dir in (Path(oss_run) / "trials").iterdir():
            p = arm_dir / tid / "calls.jsonl"
            if p.exists():
                for line in open(p, encoding="utf8"):
                    if line.strip():
                        e = json.loads(line)
                        rows[(e["arm"] if "arm" in e else tid.split("__")[0], e.get("kind", "?"))].append(e)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oss-run", required=True)
    ap.add_argument("--qwen-tables", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--skip-collect", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    rng = np.random.default_rng(20261025)
    cdir = Path(a.scratch) / "collected" if a.skip_collect else collect(a.oss_run, a.scratch)

    # ---- gpt-oss
    ot = [t for t in read_csv(cdir / "trials.csv") if t["status"] == "done" and "__failed_empty_talk" not in t["trial_id"]]
    ofailed = collections.Counter(t["arm"] for t in read_csv(cdir / "trials.csv") if t["status"] != "done")
    orounds = read_csv(cdir / "rounds.csv")
    og = game_table(ot, orounds)
    # ---- Qwen controls (thinking on, headline arms, point 1 or 5, no pilot)
    tab = Path(a.qwen_tables)
    qt = [t for t in read_csv(tab / "trials.csv") if t["status"] == "done" and t["thinking"] == "on" and t["pilot"] == ""
          and (t["arm"], t["penalty_point"]) in set(ARMS_QWEN.values())]
    qids = {t["trial_id"] for t in qt}
    qrounds = [r for r in read_csv(tab / "rounds.csv") if r["trial_id"] in qids]
    qg = game_table(qt, qrounds)

    games = []
    for model, gt, mapping in (("gpt-oss-20b", og, {v: k for k, v in ARMS_OSS.items()}),
                               ("Qwen3-32B", qg, {v: k for k, v in ARMS_QWEN.items()})):
        for g in gt.values():
            key = mapping.get(g["arm"] if model == "gpt-oss-20b" else (g["arm"], g["penalty_point"]))
            if key:
                g["key"], g["model"] = key, model
                games.append(g)
    write(out / "game_level.csv", sorted(games, key=lambda g: (g["model"], g["key"], g["trial_id"])),
          ["model", "key", "trial_id", "pair", "rounds", "price_index", "competitive_share", "matching_share", "undercuts", "scored_firm_rounds"])

    # ---- 1. per-arm summary
    arm_rows, foc_rows = [], []
    ids_by = collections.defaultdict(set)
    for g in games:
        ids_by[(g["model"], g["key"])].add(g["trial_id"])
    for model in ("gpt-oss-20b", "Qwen3-32B"):
        for key in ARMS_OSS:
            gs = [g for g in games if g["model"] == model and g["key"] == key]
            if not gs:
                continue
            row = dict(model=model, arm=key, games_done=len(gs),
                       status="INCOMPLETE (chat cell short of 20 DONE games; reruns pending)" if (len(gs) < 20 and "chat" in key) else ("complete" if len(gs) >= 20 else "INCOMPLETE"),
                       mean_rounds=fmt(np.mean([g["rounds"] for g in gs]), 1))
            for m in METRICS:
                v = [g[m] for g in gs if g[m] is not None]
                lo, hi = boot_ci(v, rng)
                row[m], row[m + "_ci_lo"], row[m + "_ci_hi"] = fmt(np.mean(v)), fmt(lo), fmt(hi)
            arm_rows.append(row)
            rd = orounds if model == "gpt-oss-20b" else qrounds
            qs = focal(rd, ids_by[(model, key)])
            cnt = collections.Counter(round(x, 2) for x in qs)
            on_printed = sum(1 for x in qs if any(abs(x - p) < 0.005 for p in PRINTED))
            mode, mc = cnt.most_common(1)[0]
            top3 = "; ".join("%.2f (%.1f%%)" % (k, 100 * c / len(qs)) for k, c in cnt.most_common(3))
            on249 = sum(1 for x in qs if any(abs(x - p) < 0.005 for p in PRINTED + [2.49]))
            foc = dict(model=model, arm=key, quotes=len(qs), share_on_printed_value=fmt(on_printed / len(qs)),
                       share_on_printed_or_2_49=fmt(on249 / len(qs)),
                       modal_quote=mode, modal_share=fmt(mc / len(qs)), top3=top3, share_at_floor_1_00=fmt(cnt[1.0] / len(qs)))
            for p in PRINTED:
                foc["share_%.2f" % p] = fmt(cnt[round(p, 2)] / len(qs))
            foc_rows.append(foc)
    write(out / "arm_summary.csv", arm_rows, ["model", "arm", "games_done", "status", "mean_rounds"] + sum(([m, m + "_ci_lo", m + "_ci_hi"] for m in METRICS), []))
    write(out / "focal_points.csv", foc_rows, ["model", "arm", "quotes", "share_on_printed_value", "share_on_printed_or_2_49", "modal_quote", "modal_share", "top3", "share_at_floor_1_00"] + ["share_%.2f" % p for p in PRINTED])

    # ---- 2. same-sign tests
    tests = [("chat_p1 - tacit_p1", "chat_p1", "tacit_p1"), ("chat_p5 - chat_p1", "chat_p5", "chat_p1")]
    srows = []
    for metric in ("price_index", "competitive_share"):
        for name, A, B in tests:
            res = {}
            for model in ("gpt-oss-20b", "Qwen3-32B"):
                gm = [g for g in games if g["model"] == model]
                ks, d, ctrl = pair_diffs(gm, A, B, metric)
                res[model] = (ks, d, ctrl)
            (ko, do, co), (kq, dq, cq) = res["gpt-oss-20b"], res["Qwen3-32B"]
            if len(do) < 2:
                continue
            lo, hi = boot_ci(do, rng)
            qlo, qhi = boot_ci(dq, rng)
            # difference of effects (independent pair resamples)
            bo = do[rng.integers(0, len(do), (NB, len(do)))].mean(1)
            bq = dq[rng.integers(0, len(dq), (NB, len(dq)))].mean(1)
            dd = bo - bq
            dlo, dhi = np.percentile(dd, [2.5, 97.5])
            est_o, est_q = do.mean(), dq.mean()
            same = (est_o > 0) == (est_q > 0) and est_o != 0
            incomplete = "chat" in A + B and any(len([g for g in games if g["model"] == "gpt-oss-20b" and g["key"] == k]) < 20 for k in (A, B) if "chat" in k)
            qin = qlo - MARGIN <= est_o <= qhi + MARGIN
            srows.append(dict(
                metric=metric, contrast=name, status="INCOMPLETE (chat reruns pending; pairs shown are those DONE in both arms)" if incomplete else "complete",
                oss_pairs=len(do), oss_effect=fmt(est_o), oss_ci_lo=fmt(lo), oss_ci_hi=fmt(hi), oss_perm_p=fmt(perm_p(do, rng), 4),
                oss_effect_pct_of_control=fmt(est_o / co.mean()) if co.mean() else "",
                qwen_pairs=len(dq), qwen_effect=fmt(est_q), qwen_ci_lo=fmt(qlo), qwen_ci_hi=fmt(qhi),
                qwen_effect_pct_of_control=fmt(est_q / cq.mean()) if cq.mean() else "",
                same_sign=int(same), diff_oss_minus_qwen=fmt(est_o - est_q), diff_ci_lo=fmt(dlo), diff_ci_hi=fmt(dhi),
                diff_ci_includes_0=int(dlo <= 0 <= dhi), oss_within_qwen_ci_pm_margin=int(qin),
                replicates=int(same and ((dlo <= 0 <= dhi) or qin)),
                oss_detectable_min_effect_note="n=20 pairs cannot detect effects below about 0.2"))
    write(out / "same_sign_tests.csv", srows, list(srows[0].keys()) if srows else ["metric"])

    # ---- 3. reaction to undercut
    ur = []
    for model, rd in (("gpt-oss-20b", orounds), ("Qwen3-32B", qrounds)):
        for key in ARMS_OSS:
            ids = ids_by.get((model, key))
            if ids:
                ur.append(ur_summary(undercut_reaction(rd, ids), rng, key, model))
        ids = set().union(*[ids_by[(model, k)] for k in ARMS_OSS if (model, k) in ids_by])
        ur.append(ur_summary(undercut_reaction(rd, ids), rng, "all three arms", model))
    write(out / "undercut_reaction.csv", ur, list(ur[0].keys()))

    # ---- 4. latency and tokens (gpt-oss, DONE games)
    cs = collections.defaultdict(list)
    for g in games:
        if g["model"] != "gpt-oss-20b":
            continue
        for arm_dir in (Path(a.oss_run) / "trials").iterdir():
            p = arm_dir / g["trial_id"] / "calls.jsonl"
            if p.exists():
                for line in open(p, encoding="utf8"):
                    if line.strip():
                        e = json.loads(line)
                        cs[(g["key"], e.get("kind", "?"))].append(e)
    lrows = []
    for (key, kind), es in sorted(cs.items()):
        lat = np.array([e["latencyMs"] / 1000 for e in es if e.get("latencyMs") is not None and not e.get("cached")], float)
        tout = np.array([e["tokensOut"] for e in es if e.get("tokensOut") is not None], float)
        tin = np.array([e["tokensIn"] for e in es if e.get("tokensIn") is not None], float)
        lrows.append(dict(arm=key, call_kind=kind, calls=len(es), latency_s_median=fmt(np.median(lat), 1), latency_s_p90=fmt(np.percentile(lat, 90), 1),
                          latency_s_max=fmt(lat.max(), 1), tokens_in_median=fmt(np.median(tin), 0), tokens_out_median=fmt(np.median(tout), 0),
                          tokens_out_p90=fmt(np.percentile(tout, 90), 0), tokens_out_max=fmt(tout.max(), 0),
                          non_ok_parse=sum(1 for e in es if e.get("parseStatus") not in ("OK", None))))
    write(out / "latency_tokens.csv", lrows, list(lrows[0].keys()) if lrows else ["arm"])
    # failed-game accounting
    write(out / "excluded_games.csv", [dict(arm=k, not_done_games=v) for k, v in sorted(ofailed.items())], ["arm", "not_done_games"])
    print("done:", {k: len(v) for k, v in ids_by.items()})


if __name__ == "__main__":
    main()
