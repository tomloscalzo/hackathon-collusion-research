"""Penalty extension: how do four objectives respond to much heavier fines, and is the response rational?

Post-processing only (no Modal or LLM call). Inputs (defaults are the local run roots; nothing is written there):
  controls  gpt-oss-20b: the Step 1 run table of the gpt-oss replication (--oss-run; headline-chat p1/p3/p5,
            ctl-32b-joint, m-inc-joint, m-inc-target p3; neutral table, status done)
            Qwen3-32B: the rated run table (--qwen-run; run = neutral, thinking on, status done; headline-chat p1/p3/p4/p5,
            ctl-32b-joint p3). Both tables already apply the 32k-token truncation-rerun supersession.
  new games the trial folders of the penalty-extension roots (--new-root, repeatable). Every DONE trial is scored with the
            repo's own Step 1 game scorer (tools/trial/run_csv.analyse_game), so the five metrics are computed exactly as
            in the control tables (checked equal on control games). A DONE <trial id>__x32k rerun in <root>_x32k replaces
            its original. FAILED or unfinished trials are listed in missing_trials.csv, never imputed.
  theory    --theory CSV (fine, idx_theta_star, idx_joint_opt, optionally idx_one_shot and more idx_* columns), written by
            the rationality computation; if absent, a local fallback joint optimum (the penalty-gradients formula) is used
            and labelled as such.

Fine of each penalty point: 1 -> 100, 3 -> 500, 4 -> 1,000, 5 -> 2,000, 25 -> 2,500, 100 -> 10,000 (read from the
scenario file of each game; the points 25 and 100 are the new files slice-m-p25 / slice-m-p100).

Statistics (as penalty-gradients): every contrast is paired on (wording, seed): 95% percentile bootstrap over pairs
(10,000 resamples) and an exact two-sided sign-flip test (all 2^n patterns, n <= 20). Holm within each named family,
separately per metric. Cell means carry a 95% percentile bootstrap CI over games.
"""
import os as _os, pathlib as _pl; _ROOT = _os.environ.get("COLLUSION_WORK_ROOT") or next((str(q) for q in _pl.Path(__file__).resolve().parents if (q / "runs").is_dir()), "..")  # the work directory holding runs/ and work_scratch/
import argparse
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNS = Path(_ROOT + "/runs")
SCR = Path(_ROOT + "/work_scratch")

METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share"),
           ("matching_share", "Matching share")]
MK = [m for m, _ in METRICS]
NB, SEED = 10000, 20261026
FINE = {1: 100, 2: 300, 3: 500, 4: 1000, 5: 2000, 25: 2500, 100: 10000}
ARMS = ["headline-chat", "ctl-32b-joint", "m-inc-joint", "m-inc-target"]
OBJ = {"headline-chat": "own profit (default)", "ctl-32b-joint": "joint profit (control)",
       "m-inc-joint": "joint profit (incentive arm; same prompt as ctl-32b-joint)", "m-inc-target": "profit-target pressure"}
# which theory benchmark is the primary one for each objective
PRIMARY = {"headline-chat": "idx_theta_star", "m-inc-target": "idx_theta_star",
           "ctl-32b-joint": "idx_joint_opt", "m-inc-joint": "idx_joint_opt"}
NEW_ROOTS = ["2026-10-26_trackm_oss_penalty_ext", "2026-10-26_trackm_oss_penalty_ext_target", "2026-10-26_trackm_penalty_ext"]


# ---------------------------------------------------------------- loading
def load_controls(oss_run, qwen_run):
    keep = ["trial_id", "arm", "penalty_point", "wording", "seed"] + MK
    o = pd.read_csv(oss_run, low_memory=False)
    o = o[(o.status == "done") & o.arm.isin(ARMS) & (o.payoff_examples == "neutral")].copy()
    o["model"] = "gpt-oss-20b"
    q = pd.read_csv(qwen_run, low_memory=False)
    q = q[(q.run == "neutral") & (q.status == "done") & (q.thinking == "on") & q.arm.isin(ARMS)].copy()
    q["model"] = "Qwen3-32B"
    G = pd.concat([o[keep + ["model"]], q[keep + ["model"]]], ignore_index=True)
    G["source"] = "control run table"
    G["truncated_calls"] = np.nan
    return G


def _score(args):
    tdir, grid = args
    sys.path.insert(0, str(REPO / "tools" / "trial"))
    import run_csv  # noqa: E402
    o = run_csv.analyse_game({"dir": tdir, "grid": grid, "cfg": {}})
    if not o.get("ok"):
        return tdir, None
    v = o["values"]
    return tdir, {**{m: v.get(m) for m in MK}, "fine_file": o.get("fine"), "truncated_calls": len(o.get("trunc") or {}),
                  "rounds_played": v.get("rounds_played"), "fined": v.get("fined"), "end_reason": v.get("end_reason")}


def load_new(roots, cache_path, workers):
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    todo, rows, missing = [], [], []
    for root in roots:
        base = RUNS / root
        if not (base / "trials").is_dir():
            continue
        x32 = RUNS / (root + "_x32k") / "trials"
        for t in sorted((base / "trials").glob("*/*")):
            if not (t / "grid_row.json").exists():
                continue
            grid = json.loads((t / "grid_row.json").read_text(encoding="utf-8-sig"))
            use = t
            xr = x32 / t.parent.name / (t.name + "__x32k")
            if (xr / "DONE").exists():
                use = xr
            if not (use / "DONE").exists():
                missing.append({"root": root, "trial_id": t.name, "state": "FAILED" if (use / "FAILED").exists() else "not finished"})
                continue
            key = "%s|%s" % (use, (use / "DONE").stat().st_mtime)
            rows.append((root, t.name, grid, str(use), key))
            if key not in cache:
                todo.append((str(use), grid, key))
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for (tdir, grid, key), (_, res) in zip(todo, ex.map(_score, [(a, b) for a, b, _ in todo], chunksize=4)):
                cache[key] = res
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    out = []
    for root, tid, grid, use, key in rows:
        res = cache.get(key)
        if res is None:
            missing.append({"root": root, "trial_id": tid, "state": "corrupt (scorer)"}); continue
        model = "gpt-oss-20b" if grid["model_profile"].startswith("gpt_oss") else "Qwen3-32B"
        out.append({"trial_id": tid, "arm": grid["arm"], "penalty_point": int(grid["penalty_point"]),
                    "wording": int(grid["wording"]), "seed": int(grid["seed"]), "model": model,
                    "source": root + ("_x32k" if use.endswith("__x32k") else ""), **res})
    N = pd.DataFrame(out)
    return N, pd.DataFrame(missing, columns=["root", "trial_id", "state"])


# ---------------------------------------------------------------- theory
def fallback_theory(fines, c=0.95):
    """Joint optimum (penalty-gradients joint_optimum.csv formula): both firms quote s every round; per-firm profit
    (s-1)*50*(1-s/5) booked in the round; investigation probability 0.025*(s-1) finds evidence for sure, every firm
    pays F and the game ends; otherwise it continues with probability c. V(s) = (pi - h*F) / (1 - c*(1-h))."""
    s = np.round(np.arange(1.00, 5.0001, 0.01), 2)
    pi = (s - 1) * 50 * (1 - s / 5)
    h = np.clip(0.025 * (s - 1), 0, 1)
    rows = []
    for F in fines:
        v = (pi - h * F) / (1 - c * (1 - h))
        so = s[int(np.argmax(v))]
        rows.append({"fine": F, "idx_joint_opt": min(1.0, (so - 1) / 2)})
    return pd.DataFrame(rows)


def load_theory(path, fines):
    if path and Path(path).exists():
        T = pd.read_csv(path)
        T["fine"] = T["fine"].astype(float)
        return T, "rationality computation (%s)" % Path(path).name
    T = fallback_theory(fines)
    T["fine"] = T["fine"].astype(float)
    return T, "LOCAL FALLBACK (joint optimum only; the theory file was absent)"


# ---------------------------------------------------------------- statistics
_SIGNS = {}


def signflip(x):
    n = len(x)
    if n == 0:
        return np.nan
    if n > 20:
        rng = np.random.default_rng(1)
        s = rng.choice([1.0, -1.0], size=(200000, n))
    else:
        if n not in _SIGNS:
            _SIGNS[n] = np.array(list(itertools.product([1.0, -1.0], repeat=n)), dtype=np.float64)
        s = _SIGNS[n]
    x = np.asarray(x, dtype=np.float64)
    obs = abs(x.sum())
    return float((np.abs(s @ x) >= obs * (1 - 1e-9) - 1e-12).mean())


def boot(x, rng):
    x = np.asarray(x, float)
    if len(x) == 0:
        return np.nan, np.nan
    idx = rng.integers(0, len(x), size=(NB, len(x)))
    m = x[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def holm(p):
    p = np.asarray(p, float)
    adj = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    idx = np.where(ok)[0]
    o = idx[np.argsort(p[ok])]
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, (len(o) - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def cellframe(G, model, arm, pp):
    d = G[(G.model == model) & (G.arm == arm) & (G.penalty_point == pp)]
    return d.set_index("pair")[MK]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oss-run", default=str(SCR / "oss_analysis/step1/final_t2/run.csv"))
    ap.add_argument("--qwen-run", default=str(SCR / "prompt_ratings/run_csv_rated/run.csv"))
    ap.add_argument("--new-root", action="append", default=None)
    ap.add_argument("--theory", default=str(Path(__file__).resolve().parent / "theory_by_fine.csv"))
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    C = load_controls(a.oss_run, a.qwen_run)
    N, miss = load_new(a.new_root or NEW_ROOTS, SCR / "penalty_ext/score_cache.json", a.workers)
    G = pd.concat([C, N], ignore_index=True) if len(N) else C
    G["penalty_point"] = G.penalty_point.astype(int)
    G["fine"] = G.penalty_point.map(FINE).astype(float)
    if "fine_file" in G:   # the new games' fine read from the played scenario must match the mapping
        bad = G[G.fine_file.notna() & (G.fine_file.astype(float) != G.fine)]
        if len(bad):
            raise SystemExit("fine mismatch in %d games: %s" % (len(bad), bad.trial_id.tolist()[:5]))
    G["pair"] = G.wording.astype(int).astype(str) + "_" + G.seed.astype(int).astype(str)
    G["objective"] = G.arm.map(OBJ)
    cols = ["model", "arm", "objective", "penalty_point", "fine", "wording", "seed", "pair", "trial_id", "source"] + MK + \
           [c for c in ("truncated_calls", "rounds_played", "fined", "end_reason") if c in G]
    G[cols].sort_values(["model", "arm", "fine", "pair"]).to_csv(out / "games_used.csv", index=False, float_format="%.6f")
    miss.to_csv(out / "missing_trials.csv", index=False)

    T, tsrc = load_theory(a.theory, sorted(G.fine.unique()))
    tcols = [c for c in T.columns if c.startswith("idx_")]

    # cell means
    rows = []
    for (model, arm, pp), d in G.groupby(["model", "arm", "penalty_point"]):
        r = {"model": model, "arm": arm, "objective": OBJ[arm], "penalty_point": pp, "fine": FINE[pp], "n_games": len(d),
             "new_games": int(d.source.ne("control run table").sum())}
        for m in MK:
            x = d[m].dropna().values
            lo, hi = boot(x, rng)
            r.update({f"{m}_mean": x.mean() if len(x) else np.nan, f"{m}_lo": lo, f"{m}_hi": hi})
        rows.append(r)
    CM = pd.DataFrame(rows).merge(T[["fine"] + tcols], on="fine", how="left")
    CM.to_csv(out / "cell_means.csv", index=False, float_format="%.4f")

    # paired contrasts: every fine vs fine 500 (p3), and adjacent fine steps, within model x arm
    crow = []
    for (model, arm), d in G.groupby(["model", "arm"]):
        pts = sorted(d.penalty_point.unique(), key=lambda p: FINE[p])
        fr = {p: cellframe(G, model, arm, p) for p in pts}
        pairs = [("V: vs fine 500 (p3)", p, 3) for p in pts if p != 3 and 3 in pts]
        pairs += [("S: adjacent fine steps", hi, lo) for lo, hi in zip(pts[:-1], pts[1:])]
        for fam, hi_, lo_ in pairs:
            common = sorted(set(fr[hi_].index) & set(fr[lo_].index))
            r = {"family": fam, "model": model, "arm": arm, "objective": OBJ[arm], "fine_hi": FINE[hi_], "fine_lo": FINE[lo_],
                 "contrast": f"{arm}: fine {FINE[hi_]:,} - fine {FINE[lo_]:,}", "n_pairs": len(common)}
            for m in MK:
                x = (fr[hi_].loc[common, m] - fr[lo_].loc[common, m]).dropna().values
                lo, hi = boot(x, rng)
                r.update({f"{m}_d": x.mean() if len(x) else np.nan, f"{m}_lo": lo, f"{m}_hi": hi, f"{m}_p": signflip(x)})
            th = T.set_index("fine")
            for c in tcols:
                r[f"price_index_theory_{c}"] = (th.loc[FINE[hi_], c] - th.loc[FINE[lo_], c]) if FINE[hi_] in th.index and FINE[lo_] in th.index else np.nan
            crow.append(r)
    CT = pd.DataFrame(crow)
    if len(CT):
        for (fam, model), idx in CT.groupby(["family", "model"]).groups.items():
            for m in MK:
                CT.loc[idx, f"{m}_holm"] = holm(CT.loc[idx, f"{m}_p"].values)
    CT.to_csv(out / "contrasts.csv", index=False, float_format="%.4f")

    # rationality: observed price index minus theory, per model x arm x fine
    rr = []
    th = T.set_index("fine")
    for (model, arm, pp), d in G.groupby(["model", "arm", "penalty_point"]):
        F = FINE[pp]
        x = d.price_index.dropna().values
        r = {"model": model, "arm": arm, "objective": OBJ[arm], "fine": F, "n_games": len(x),
             "price_index_obs": x.mean(), "primary_benchmark": PRIMARY[arm]}
        r["obs_lo"], r["obs_hi"] = boot(x, rng)
        for c in tcols:
            t = th.loc[F, c] if F in th.index else np.nan
            dlo, dhi = r["obs_lo"] - t, r["obs_hi"] - t
            r.update({c: t, f"gap_{c}": x.mean() - t, f"gap_{c}_lo": dlo, f"gap_{c}_hi": dhi})
        pc = PRIMARY[arm] if PRIMARY[arm] in tcols else (tcols[0] if tcols else None)
        r["primary_used"] = pc
        if pc and not np.isnan(r.get(pc, np.nan)):
            g, lo, hi = r[f"gap_{pc}"], r[f"gap_{pc}_lo"], r[f"gap_{pc}_hi"]
            r["class"] = ("near-rational" if (lo <= 0 <= hi) or abs(g) <= 0.05 else
                          "under-responsive (above theory)" if lo > 0 else "over-responsive (below theory)")
        else:
            r["class"] = "no theory value"
        rr.append(r)
    RA = pd.DataFrame(rr)
    RA.to_csv(out / "rationality.csv", index=False, float_format="%.4f")

    # elasticity: OLS slope of price index on log10(fine), pair-cluster bootstrap; theory slope on the same fines
    er = []
    for (model, arm), d in G.groupby(["model", "arm"]):
        d = d.dropna(subset=["price_index"])
        fines = sorted(d.fine.unique())
        if len(fines) < 2:
            continue
        X = np.log10(d.fine.values)
        y = d.price_index.values
        slope = np.polyfit(X, y, 1)[0]
        prs = d.pair.values
        up = np.unique(prs)
        bs = []
        byp = {p: np.where(prs == p)[0] for p in up}
        for _ in range(2000):
            pick = rng.choice(up, size=len(up))
            ii = np.concatenate([byp[p] for p in pick])
            if len(np.unique(X[ii])) > 1:
                bs.append(np.polyfit(X[ii], y[ii], 1)[0])
        r = {"model": model, "arm": arm, "objective": OBJ[arm], "fines": ";".join(str(int(f)) for f in fines), "n_games": len(d),
             "slope_obs": slope, "slope_lo": np.percentile(bs, 2.5), "slope_hi": np.percentile(bs, 97.5)}
        for c in tcols:
            tv = [th.loc[f, c] if f in th.index else np.nan for f in fines]
            r[f"slope_{c}"] = np.polyfit(np.log10(fines), tv, 1)[0] if not np.isnan(tv).any() else np.nan
        pc = PRIMARY[arm] if PRIMARY[arm] in tcols else (tcols[0] if tcols else None)
        ts = r.get(f"slope_{pc}", np.nan) if pc else np.nan
        r["response_ratio_primary"] = slope / ts if ts == ts and ts != 0 else np.nan   # observed slope / theory slope
        er.append(r)
    pd.DataFrame(er).to_csv(out / "elasticity.csv", index=False, float_format="%.4f")

    prov = {"theory_source": tsrc, "theory_columns": tcols, "control_games": int((G.source == "control run table").sum()),
            "new_games_done": int((G.source != "control run table").sum()), "missing_or_failed": len(miss),
            "bootstrap": NB, "seed": SEED, "fine_map": FINE}
    (out / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print(json.dumps(prov))


if __name__ == "__main__":
    main()
