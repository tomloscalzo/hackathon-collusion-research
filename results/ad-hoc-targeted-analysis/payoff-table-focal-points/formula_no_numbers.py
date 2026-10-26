#!/usr/bin/env python3
"""Formula and no-numbers arms: five standard metrics paired against the neutral control, quote distributions, formula vs none,
the penalty-5 arm, a keyword count over the reasoning traces, and the truncation-rerun sensitivity.

Inputs (all paths are arguments; nothing is hard-coded):
  --formula-root   raw trials root of the formula/no-numbers run (<root>/trials/<arm>/<trial_id>/)
  --rerun-root     optional raw root of the 32k truncation reruns (ids end __x32k); supersedes the matching originals
  --neutral-run    the neutral run's Step 1 run.csv (controls; truncation reruns already resolved there)
  --neutral-tables a tools/trial/collect.py output folder of the neutral run (quotes and reasoning of the controls)
Outputs (in --out): formula_no_numbers_paired.csv, formula_vs_none.csv, formula_no_numbers_quotes.csv, formula_no_numbers_traces.csv,
formula_no_numbers_sensitivity.csv, fig_formula_heatmap.png, fig_formula_quotes.png.

Metrics per game are computed with tools/trial/run_csv.py's own per-game code (analyse_game), so they equal run.csv's columns:
 average absolute spread = market_price_mean (mean market quote, 1.00-5.00), price index, profit gain index, competitive share (U16),
 matching share. Pairing on (wording, seed) within thinking mode; 95% percentile bootstrap over pairs (10,000 resamples, seed 20261025);
 exact sign-flip permutation test over pairs (2^n sign patterns); Holm within each metric across the 9 arm x mode contrasts."""
import argparse, csv, json, re, sys, itertools, collections
from pathlib import Path
import numpy as np
import pandas as pd

csv.field_size_limit(10**9)
HERE = Path(__file__).resolve().parent
REPO = HERE
while not (REPO / "tools" / "trial" / "collect.py").exists():
    REPO = REPO.parent
sys.path.insert(0, str(REPO / "tools" / "trial"))
import run_csv, trunc_rerun  # noqa: E402

METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
           ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
ARMS = [("fx-chat-p1", "headline-chat", 1), ("fx-tacit-p1", "headline-tacit", 1), ("nx-chat-p1", "headline-chat", 1),
        ("nx-tacit-p1", "headline-tacit", 1), ("fx-chat-p5", "headline-chat", 5)]
NB, SEED = 10000, 20261025


def game_metrics(d):
    out = run_csv.analyse_game({"dir": str(d), "grid": trunc_rerun.grid_row(Path(d)) or {}, "cfg": {}})
    if not out.get("ok"):
        return None
    v, t = out["values"], out["trial_row"]
    return {k: v.get(k) for k, _ in METRICS} | {"truncations": sum(out.get("trunc", {}).values())}


def load_formula(root, rerun_root):
    """{trial_id: dict} for DONE games of the formula root; reruns = {original_id: rerun dict}."""
    games = {}
    for done in sorted(Path(root, "trials").rglob("DONE")):
        d = done.parent
        g = json.loads((d / "grid_row.json").read_text(encoding="utf-8"))
        m = game_metrics(d)
        if m is None:
            continue
        games[g["trial_id"]] = dict(m, trial_id=g["trial_id"], arm=g["arm"], wording=str(int(g["wording"])), seed=str(int(g["seed"])),
                                    mode="on" if str(g["thinking"]) == "1" else "off", dir=str(d))
    reruns = {}
    if rerun_root and Path(rerun_root).exists():
        for done in sorted(Path(rerun_root, "trials").rglob("DONE")):
            d = done.parent
            g = json.loads((d / "grid_row.json").read_text(encoding="utf-8"))
            m = game_metrics(d)
            base = g["trial_id"].replace("__x32k", "")
            if m and base in games:
                reruns[base] = dict(games[base], **m, dir=str(d), trial_id=g["trial_id"])
    return games, reruns


def stats(diff):
    d = np.asarray(diff, float)
    n = len(d)
    rng = np.random.default_rng(SEED)
    bm = d[rng.integers(0, n, (NB, n))].mean(axis=1)
    lo, hi = np.percentile(bm, [2.5, 97.5])
    # exact sign-flip test on the mean difference
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
    means = np.abs((signs * d).mean(axis=1))
    p = float((means >= abs(d.mean()) - 1e-12).mean())
    return d.mean(), lo, hi, p


def holm(ps):
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def paired(A, C, label):
    """A, C: DataFrames with wording, seed and metric columns -> list of rows of arm mean, control mean, diff, CI, p."""
    j = A.merge(C, on=["wording", "seed"], suffixes=("_a", "_c"))
    rows = []
    for col, nm in METRICS:
        s = j[[col + "_a", col + "_c"]].dropna()
        if len(s) < 3:
            continue
        m, lo, hi, p = stats(s[col + "_a"] - s[col + "_c"])
        rows.append(dict(contrast=label, metric=col, metric_label=nm, n_pairs=len(s), arm_mean=s[col + "_a"].mean(), control_mean=s[col + "_c"].mean(),
                         diff=m, ci_low=lo, ci_high=hi, p_exact=p))
    return rows


def frame(games, **eq):
    df = pd.DataFrame(list(games.values()) if isinstance(games, dict) else games)
    for k, v in eq.items():
        df = df[df[k] == v]
    return df


def build_contrasts(fgames, ctl):
    rows = []
    for arm, carm, pt in ARMS:
        for mode in ("off", "on"):
            A = frame(fgames, arm=arm, mode=mode)
            if A.empty:
                continue
            C = ctl[(ctl.arm == carm) & (ctl.penalty_point == pt) & (ctl["mode"] == mode)]
            for r in paired(A, C, f"{arm} minus neutral {carm} p{pt}"):
                rows.append(dict(arm=arm, mode=mode, control=f"{carm} p{pt}", n_arm_games=len(A), **r))
    D = pd.DataFrame(rows)
    D["p_holm"] = np.nan
    for col, _ in METRICS:
        idx = D.index[D.metric == col]
        D.loc[idx, "p_holm"] = holm(D.loc[idx, "p_exact"].to_numpy())
    return D


def formula_vs_none(fgames):
    rows = []
    for comm in ("chat", "tacit"):
        for mode in ("off", "on"):
            A, C = frame(fgames, arm=f"fx-{comm}-p1", mode=mode), frame(fgames, arm=f"nx-{comm}-p1", mode=mode)
            for r in paired(A, C, f"fx-{comm}-p1 minus nx-{comm}-p1"):
                rows.append(dict(comm=comm, mode=mode, **r))
    for mode in ("on",):
        A, C = frame(fgames, arm="fx-chat-p5", mode=mode), frame(fgames, arm="fx-chat-p1", mode=mode)
        for r in paired(A, C, "fx-chat-p5 minus fx-chat-p1"):
            rows.append(dict(comm="chat", mode=mode, **r))
    D = pd.DataFrame(rows)
    D["p_holm"] = np.nan
    for col, _ in METRICS:
        idx = D.index[D.metric == col]
        D.loc[idx, "p_holm"] = holm(D.loc[idx, "p_exact"].to_numpy())
    return D


# ---- quotes -------------------------------------------------------------------------------------------------------------
BINS = [("1.00", 1.0, 1.0), ("1.01-1.25", 1.0001, 1.25), ("1.26-1.50", 1.2501, 1.50), ("1.51-2.00", 1.5001, 2.0), ("2.01-3.00", 2.0001, 3.0), ("above 3.00", 3.0001, 5.0)]


def quotes_of(dirs):
    q = []
    for d in dirs:
        ev = Path(d, "events.jsonl")
        for line in ev.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("kind") == "market" and isinstance(e.get("prices"), dict):
                q += [float(v) for v in e["prices"].values() if isinstance(v, (int, float))]
    return q


def quote_rows(fgames, ctl_dirs):
    """ctl_dirs[(control arm, penalty, thinking 'on'|'off')] = (n games, [quotes])."""
    out = []
    for arm, carm, pt in ARMS:
        for mode in ("off", "on"):
            A = [g["dir"] for g in fgames.values() if g["arm"] == arm and g["mode"] == mode]
            if not A:
                continue
            nc, cqs = ctl_dirs.get((carm, pt, mode), (0, []))
            for who, ng, qs in ((arm, len(A), quotes_of(A)), (f"neutral {carm} p{pt}", nc, cqs)):
                q = np.round(np.array(qs), 2)
                if not len(q):
                    continue
                c = collections.Counter(q.tolist())
                top = "; ".join(f"{k:.2f} ({v / len(q):.0%})" for k, v in c.most_common(4))
                rec = dict(arm=arm, mode=mode, who=who, is_control=who != arm, n_games=ng, n_quotes=len(q), mean_quote=q.mean(), top_quotes=top)
                for nm, lo, hi in BINS:
                    rec["share_" + nm] = float(((q >= lo - 1e-9) & (q <= hi + 1e-9)).mean())
                out.append(rec)
    return pd.DataFrame(out)


# ---- reasoning traces ---------------------------------------------------------------------------------------------------
KEYS = {
    "demand formula": r"Q\s*\(|100\s*[*x×]\s*\(?\s*1\s*-",
    "30/70 flow split": (r"70\s*%|0\.7\b", r"30\s*%|0\.3\b"),   # both patterns must occur in the passage
    "profit per unit (quote minus 1.00)": r"\(\s*\d(?:\.\d+)?\s*-\s*1(?:\.0+)?\s*\)\s*[*x×]|(?:quote|price|b)\s*-\s*1\.00\s*\)?\s*[*x×]|profit per unit",
    "investigation probability": r"investigat[^.]{0,80}(?:\d\.\d+|\d+\s*%)|probability[^.]{0,60}investigat",
}
CALC = r"[=≈]\s*\d"   # a passage "computes" if it matches the demand formula or flow split AND shows a numeric evaluation


_CACHE = {}


def _table(path):
    if path not in _CACHE:
        _CACHE[path] = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
    return _CACHE[path]


def passages(tables, pred):
    """Reasoning passages (quote-call and talk-call) of thinking-on games selected by pred(trial_row)."""
    tr = {r["trial_id"]: r for r in _table(Path(tables) / "trials.csv")}
    keep = {k for k, r in tr.items() if r["status"] == "done" and pred(r)}
    for fn in ("rounds.csv", "messages.csv"):
        for r in _table(Path(tables) / fn):
            if r["trial_id"] in keep and r.get("reasoning"):
                yield r["trial_id"], fn[:-4], r["reasoning"]


def trace_rows(label, tables, pred):
    P = list(passages(tables, pred))
    n = len(P)
    rec = dict(group=label, n_passages=n, n_games=len({p[0] for p in P}))
    for nm, rx in KEYS.items():
        rx = (rx,) if isinstance(rx, str) else rx
        rec["share_" + nm] = sum(1 for _, _, t in P if all(re.search(x, t, re.S | re.I) for x in rx)) / n if n else np.nan
    comp = lambda t: bool(re.search(KEYS["demand formula"], t)) and bool(re.search(CALC, t))
    rec["share_computes_with_formula"] = sum(1 for _, _, t in P if comp(t)) / n if n else np.nan
    rec["games_with_any_computing_passage"] = len({g for g, _, t in P if comp(t)})
    return rec


# ---- figures ------------------------------------------------------------------------------------------------------------
# The two figures are drawn by figures.py (heat, quotes_fig) so they can be re-rendered from the committed CSVs alone.
from figures import heat as _heat, quotes_fig  # noqa: E402


def heat(D, fgames, ctl, path):
    return _heat(D, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--formula-root", required=True); ap.add_argument("--rerun-root", default=""); ap.add_argument("--neutral-run", required=True)
    ap.add_argument("--neutral-tables", required=True); ap.add_argument("--formula-tables", required=True)
    ap.add_argument("--out", default=str(HERE)); ap.add_argument("--reruns", choices=["originals", "reruns"], default="reruns")
    A = ap.parse_args()
    out = Path(A.out)
    orig, reruns = load_formula(A.formula_root, A.rerun_root)
    ctl = pd.read_csv(A.neutral_run, low_memory=False)
    ctl = ctl[ctl.status == "done"].copy()
    ctl["wording"] = ctl.wording.astype(int).astype(str); ctl["seed"] = ctl.seed.astype(int).astype(str); ctl["mode"] = ctl.thinking
    ctl = ctl[ctl.arm.isin(["headline-chat", "headline-tacit"])]
    for name, games in (("originals", orig), ("reruns", {k: reruns.get(k, v) for k, v in orig.items()})):
        D = build_contrasts(games, ctl)
        D.to_csv(out / f"formula_no_numbers_paired_{name}.csv", index=False, float_format="%.6f")
        if name == A.reruns:
            D.to_csv(out / "formula_no_numbers_paired.csv", index=False, float_format="%.6f")
            formula_vs_none(games).to_csv(out / "formula_vs_none.csv", index=False, float_format="%.6f")
            heat(D, games, ctl, out / "fig_formula_heatmap.png")
            sel = games
    # sensitivity: originals vs reruns
    O = pd.read_csv(out / "formula_no_numbers_paired_originals.csv"); R = pd.read_csv(out / "formula_no_numbers_paired_reruns.csv")
    S = O.merge(R, on=["arm", "mode", "metric"], suffixes=("_orig", "_rerun"))
    S["n_games_rerun_here"] = [sum(1 for k in reruns if orig[k]["arm"] == a and orig[k]["mode"] == m) for a, m in zip(S.arm, S["mode"])]
    S[["arm", "mode", "metric", "n_games_rerun_here", "arm_mean_orig", "arm_mean_rerun", "diff_orig", "ci_low_orig", "ci_high_orig", "diff_rerun", "ci_low_rerun", "ci_high_rerun"]].to_csv(
        out / "formula_no_numbers_sensitivity.csv", index=False, float_format="%.6f")
    pairs = []
    for k, rr in reruns.items():
        o = orig[k]
        pairs.append(dict(trial_id=k, arm=o["arm"], **{f"{c}_orig": o[c] for c, _ in METRICS}, **{f"{c}_rerun": rr[c] for c, _ in METRICS}, truncations_orig=o["truncations"], truncations_rerun=rr["truncations"]))
    pd.DataFrame(pairs).to_csv(out / "formula_no_numbers_rerun_games.csv", index=False, float_format="%.6f")
    # quotes
    tr = {r["trial_id"]: r for r in csv.DictReader(open(Path(A.neutral_tables) / "trials.csv", encoding="utf-8", newline="")) if r["status"] == "done"}
    cq = collections.defaultdict(list)
    for r in csv.DictReader(open(Path(A.neutral_tables) / "rounds.csv", encoding="utf-8", newline="")):
        t = tr.get(r["trial_id"])
        if t and r["imputed"] in ("0", "") and r["quote"] not in ("", None):
            cq[(t["arm"], int(t["penalty_point"]), t["thinking"])].append(float(r["quote"]))
    ctl_games = collections.Counter((t["arm"], int(t["penalty_point"]), t["thinking"]) for t in tr.values())
    ctl_dirs = {k: (ctl_games[k], v) for k, v in cq.items()}
    Q = quote_rows(sel, ctl_dirs)
    Q.to_csv(out / "formula_no_numbers_quotes.csv", index=False, float_format="%.6f")
    quotes_fig(Q, out / "fig_formula_quotes.png")
    # traces (thinking on)
    T = []
    for arm, carm, pt in ARMS:
        T.append(trace_rows(f"{arm} (formula/no-numbers arm)", A.formula_tables, lambda r, arm=arm: r["arm"] == arm and r["thinking"] == "on"))
    for carm, pt in (("headline-chat", 1), ("headline-tacit", 1), ("headline-chat", 5)):
        T.append(trace_rows(f"neutral {carm} p{pt} (control, prints examples)", A.neutral_tables, lambda r, c=carm, p=pt: r["arm"] == c and r["penalty_point"] == str(p) and r["thinking"] == "on"))
    pd.DataFrame(T).to_csv(out / "formula_no_numbers_traces.csv", index=False, float_format="%.4f")
    print("done")


if __name__ == "__main__":
    main()
