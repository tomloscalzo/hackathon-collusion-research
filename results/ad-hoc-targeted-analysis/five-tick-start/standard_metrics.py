#!/usr/bin/env python3
"""Standard metrics (owner rule): every ad-hoc analysis reports, for each main contrast, the five standard collusion and coordination metrics, analysed separately:
  average absolute spread  mean market quote (the half-spread) in raw units, 1.00-5.00, not rescaled (run.csv market_price_mean)
  price index              (market price - 1)/2, 0 = competitive, 1 = monopoly 3.00
  profit gain index        (profit - competitive) / (monopoly - competitive)
  competitive share (U16)  share of firm-rounds that quote below the lowest rival's previous-round quote, or both at 1.00
  matching share           share of firm-rounds that quote equal to the lowest rival's previous-round quote, above 1.00 (coordination signature)
Contrasts are paired on the (wording, seed) pair (within thinking mode and run where stated); 95% percentile bootstrap over pairs
(10,000 resamples, seed 20261025). Game-level values come from the Step 1 run.csv (or, where a game is not in run.csv, are
recomputed from its raw trial directory with the same code as tools/trial/run_csv.py).
Usage (from this folder): python -X utf8 standard_metrics.py --data <analysis_final dir> --name ethics-rule|incentives|market-structure|five-tick-start
Writes standard_metrics.csv and inserts/replaces the 'Standard metrics' section of ANALYSIS.md (regenerate ANALYSIS.html afterwards)."""
import argparse, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
M = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
     ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
NB, SEED = 10000, 20261025
DEFS = ("Average absolute spread: the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled (1.00 = competitive floor, 3.00 = monopoly price; lower = less collusion). "
        "Price index: (market price - 1)/2, from 0 (competitive) to 1 (monopoly 3.00) (lower = less collusion). "
        "Profit gain index: (profit - competitive) / (monopoly - competitive), 0 = competitive profit, 1 = monopoly profit (lower = less collusion). "
        "Competitive share (U16): share of firm-rounds that are competitive, meaning the firm quotes below the lowest rival's previous-round quote, or both are at 1.00 (higher = less collusion). "
        "Matching share: share of firm-rounds in which the firm's quote equals the lowest rival's previous-round quote, above 1.00 (higher = more coordination; the coordination signature). "
        "The five are analysed separately, never blended. ")
TERMS = [("Average absolute spread", "Mean market quote (the half-spread) over a game's rounds, raw units 1.00 to 5.00, not rescaled; 1.00 = competitive floor, 3.00 = monopoly; difference in quote units (run.csv `market_price_mean`)"),
         ("Price index", "(market price - 1) / 2 averaged over a game's rounds, 0 = competitive 1.00, 1 = monopoly 3.00; difference in index units"),
         ("Profit gain index", "(mean profit per firm per round - competitive profit) / (monopoly profit - competitive profit); 0 = competitive profit, 1 = monopoly profit; difference in index units"),
         ("Competitive share (U16)", "Share of scored firm-rounds in which the firm quotes below the lowest rival's quote of the previous round, or both are at 1.00; round 1 is not scored; difference in share units"),
         ("Matching share", "Share of scored firm-rounds in which the firm's quote equals the lowest rival's previous-round quote (within half a tick), above 1.00; the coordination signature; competitive + matching + above-rival shares sum to 1; difference in share units")]


def load_run(steps, run):
    df = pd.read_csv(Path(steps) / run / "step1" / "run.csv", low_memory=False)
    df = df[df.status == "done"].copy()
    df["wording"] = df.wording.astype(int).astype(str)
    df["seed"] = df.seed.astype(int).astype(str)
    df["mode"] = df.thinking
    return df


def ser(df, metric, **eq):
    """Per-(wording, seed) mean of `metric` over the games matching the filters (a list value means 'any of')."""
    m = pd.Series(True, index=df.index)
    for k, v in eq.items():
        m &= df[k].isin(v) if isinstance(v, (list, tuple, set)) else (df[k] == v)
    return df[m].groupby(["wording", "seed"])[metric].mean()


def stats(t, r):
    j = pd.concat([t.rename("t"), r.rename("r")], axis=1).dropna()
    n = len(j)
    if n < 2:
        return dict(n=n, ref=np.nan, arm=np.nan, diff=np.nan, lo=np.nan, hi=np.nan)
    d = (j.t - j.r).to_numpy()
    rng = np.random.default_rng(SEED)
    bm = d[rng.integers(0, n, (NB, n))].mean(axis=1)
    lo, hi = np.percentile(bm, [2.5, 97.5])
    return dict(n=n, ref=j.r.mean(), arm=j.t.mean(), diff=d.mean(), lo=lo, hi=hi)


class Table:
    def __init__(self):
        self.rows = []

    def add(self, contrast, run, mode, f):
        """f(metric) -> (treatment Series, reference Series) indexed by pair."""
        rec = dict(contrast=contrast, run=run, mode=mode)
        for col, _ in M:
            t, r = f(col)
            s = stats(t, r)
            for k, v in s.items():
                rec[f"{col}_{k}"] = v
        self.rows.append(rec)

    def df(self):
        return pd.DataFrame(self.rows)


def fmt(r, col):
    if np.isnan(r[col + "_diff"]):
        return "n/a"
    return f"{r[col + '_diff']:+.3f} [{r[col + '_lo']:+.3f}, {r[col + '_hi']:+.3f}]"


def md_table(T):
    cols = list(T.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(x) for x in row) + " |" for row in T.itertuples(index=False)]
    return "\n".join(out)


def degenerate_notes(D, tol=0.03):
    notes = []
    bad = D[(D.competitive_share_arm.between(0, tol)) & (D.competitive_share_ref.between(0, tol))]
    if len(bad):
        notes.append(f"{len(bad)} of {len(D)} rows have a competitive share of {tol:.2f} or less in BOTH arms (the floor): there the competitive-share difference is degenerate and carries almost no information, and the spread, price index, profit gain index and matching share are the informative metrics.")
    top = D[(D.competitive_share_arm >= 1 - tol) & (D.competitive_share_ref >= 1 - tol)]
    if len(top):
        notes.append(f"{len(top)} rows have a competitive share of {1 - tol:.2f} or more in both arms (all firm-rounds at the 1.00 floor count as competitive): degenerate.")
    mt = D[(D.matching_share_arm >= 1 - tol) & (D.matching_share_ref >= 1 - tol)]
    if len(mt):
        notes.append(f"{len(mt)} of {len(D)} rows have a matching share of {1 - tol:.2f} or more in BOTH arms (nearly every firm-round matches the lowest rival quote above 1.00): there the matching-share difference is degenerate (a ceiling), and the spread, price index and profit gain index carry the contrast.")
    mb = D[(D.matching_share_arm.between(0, tol)) & (D.matching_share_ref.between(0, tol))]
    if len(mb):
        notes.append(f"{len(mb)} of {len(D)} rows have a matching share of {tol:.2f} or less in BOTH arms (no coordination signature in either arm): the matching-share difference is degenerate.")
    return notes


def terms_block():
    rows = "\n".join(f"| {a} | {b} |" for a, b in TERMS)
    return ("<small>\n\n**Terms for the standard-metrics table.** Each row is one contrast, analysed on the five standard metrics separately.\n\n"
            "| Label | Meaning |\n|---|---|\n"
            "| contrast \"X - Y\" | The value is arm X's game minus arm Y's game in the same (wording, seed) pair; X and Y are defined where the contrast is introduced above |\n"
            "| run / mode | Neutral or anchored run; thinking off / on (Qwen3-32B reasoning mode), analysed separately, where a column is shown |\n"
            "| n pairs | Number of (wording, seed) pairs (5 prompt paraphrases times 4 seeds) with both games finished |\n"
            "| each cell | Mean over the pairs of (first game minus second game), with the 95% percentile bootstrap CI over the pairs in brackets; a CI that excludes zero is a clear difference |\n\n"
            "| Column | Meaning |\n|---|---|\n" + rows + "\n\n</small>\n\n")


def patch_terms(sm):
    """Bring an existing <small> Terms block for the standard-metrics table to all five metrics (keeps the other agent's labels)."""
    sm = sm.replace("three standard metrics", "five standard metrics").replace("the three standard", "the five standard")
    if not any(l.startswith("| ") for l in sm.split("\n")):   # free-text Terms paragraph: append the two new definitions
        add = (" Average absolute spread = the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled (1.00 = competitive floor, 3.00 = monopoly price); difference in quote units."
               " Matching share = share of firm-rounds (round 2 on) in which the firm's quote equals the lowest rival's previous-round quote, above 1.00 (the coordination signature); difference in share units.")
        return re.sub(r"\s*</small>", lambda m: add + "\n\n</small>", sm, count=1)
    lines = sm.split("\n")
    names = [t.split(" (")[0] for t, _ in TERMS]
    for name, meaning in TERMS:
        if any(l.startswith("| " + name.split(" (")[0]) for l in lines):
            continue
        row = f"| {name} | {meaning} |"
        if name == "Average absolute spread":
            idx = next((i for i, l in enumerate(lines) if l.startswith("| Price index |")), None)
            if idx is None:
                idx = max([i for i, l in enumerate(lines) if l.startswith("| ") and any(l.startswith("| " + t + " |") for t in names)] or [len(lines) - 2])
            lines.insert(idx, row)
        else:
            idx = max([i for i, l in enumerate(lines) if any(l.startswith("| " + t + " |") for t in names)] or [-1])
            lines.insert(idx + 1 if idx >= 0 else len(lines) - 1, row)
    return "\n".join(lines)


def finish(T, intro, notes=(), md="ANALYSIS.md", csv="standard_metrics.csv"):
    D = T.df()
    D.to_csv(csv, index=False, float_format="%.6f")
    out = pd.DataFrame({"contrast": D.contrast, "run": D.run, "mode": D["mode"], "n pairs": D.price_index_n.astype(int)})
    for c in ("run", "mode"):
        if (out[c] == "-").all():
            out = out.drop(columns=c)
    for col, nm in M:
        out[nm] = D.apply(lambda r, col=col: fmt(r, col), axis=1)
    s = Path(md).read_text(encoding="utf-8")
    h = re.search(r"^## Standard metrics[^\n]*\n", s, flags=re.M)
    own = None
    end = None
    if h:
        nxt = re.search(r"\n## ", s[h.end():])
        end = h.end() + nxt.start() + 1 if nxt else len(s)
        for sm in re.finditer(r"<small>.*?</small>\n*", s[h.end():end], flags=re.S):
            if own is None and re.search(r"standard.metrics|Terms for the table above|^\| Price index \|", sm.group(0), flags=re.I | re.M):
                own = sm.group(0)
                continue
            end = h.end() + sm.start()   # a foreign <small> (another table's terms) ends the section
            break
        dangling = re.search(r"<small>\s*$", s[h.end():end])   # an opener belonging to what follows (e.g. a Terms block)
        if dangling:
            end = h.end() + dangling.start()
    lead = ""
    if h:
        m_ = re.match(r"\s*(\*[^*\n]+\*)", s[h.end():])
        if m_:
            lead = m_.group(1).replace("three standard", "five standard").replace("(price index, competitive share, profit gain index)", "(average absolute spread, price index, profit gain index, competitive share, matching share)") + " "
    old_notes = []
    if h:
        seg = s[h.end():end]
        mt = re.search(r"\n\|", seg)
        pre = (seg[:mt.start()] if mt else "").strip()
        if lead and pre.startswith(lead.strip()):
            pre = pre[len(lead.strip()):].strip()
        k = min([i for i in (pre.find(" Price index:"), pre.find("Average absolute spread:")) if i >= 0] or [-1])
        if k > 0 and not pre.startswith("Price index:"):
            intro = pre[:k].strip().replace("three standard", "five standard").replace("The three", "The five")
        nb = re.search(r"Notes on the standard metrics:\n\n((?:- [^\n]*\n)+)", seg)
        if nb:
            old_notes = [x[2:] for x in nb.group(1).strip().split("\n")]
            old_notes = [x for x in old_notes if not re.search(r"rows? have a (competitive|matching) share of", x)]
    sec = ("## Standard metrics\n\n" + lead + intro.strip() + " " + DEFS +
           "Each cell is the mean paired difference with its 95% percentile bootstrap CI over the paired (wording, seed) pairs (10,000 resamples). Means, counts and CIs: `standard_metrics.csv`; script: `standard_metrics.py`.\n\n"
           + md_table(out) + "\n\n")
    sec += (patch_terms(own).rstrip("\n") + "\n\n") if own else terms_block()
    allnotes = (old_notes if old_notes else list(notes)) + degenerate_notes(D)
    if allnotes:
        sec += "Notes on the standard metrics:\n\n" + "\n".join("- " + n for n in allnotes) + "\n\n"
    if h:
        s = s[:h.start()] + sec + s[end:].lstrip("\n")
    else:
        m = list(re.finditer(r"\n## (Files|Reproduce|Method and files)[^\n]*\n", s))
        if m:
            i = m[-1].start() + 1
            s = s[:i] + sec + s[i:]
        else:
            s = s.rstrip("\n") + "\n\n" + sec.rstrip("\n") + "\n"
    s = re.sub(r"\n{3,}", "\n\n", s)
    Path(md).write_text(s, encoding="utf-8", newline="\n")
    try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
        import sys as _sys, pathlib as _pl
        _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
        _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
        _rh.finalize_report(md)
    except Exception as _e:
        print('WARNING: CI charts not added:', _e)
    print(out.to_string())


import common as c
ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--name", required=True); A = ap.parse_args()
SPEC = {"ethics-rule": [("m-asym vs private chat", "m-asym", "headline-chat"), ("n3-ethics vs 3-firm chat", "n3-ethics", "n3-group")],
        "incentives": [("m-inc-target vs private chat", "m-inc-target", "headline-chat"), ("m-inc-joint vs private chat", "m-inc-joint", "headline-chat")],
        "market-structure": [("3 firms vs 2 firms", "n3-group", "headline-chat"), ("cheater vs 3-firm chat", "n3-cheater", "n3-group")],
        "five-tick-start": [("5-tick start vs private chat", "start-5tick", "headline-chat")]}[A.name]
COL = {"market_price_mean": "market_price_mean", "price_index": "price_index", "profit_gain_index": "profit_gain_index",
       "competitive_share": "comp_share", "matching_share": "matching_share"}
T = Table()
for run in ("neutral", "anchored"):
    g = c.load_games(A.data, run)
    for lab, arm, carm in SPEC:
        for mode in ("off", "on"):
            rec = dict(contrast=lab, run=run, mode=mode)
            for col, nm in M:
                x = c.contrast(g, arm, 3, carm, 3, mode, COL[col], f"std{run}{arm}{mode}{COL[col]}")
                rec.update({f"{col}_n": x["n_pairs"], f"{col}_ref": x["control_mean"], f"{col}_arm": x["arm_mean"], f"{col}_diff": x["diff"], f"{col}_lo": x["ci_lo"], f"{col}_hi": x["ci_hi"]})
            T.rows.append(rec)
finish(T, "Every main contrast (arm minus matched control, penalty point 3), neutral run, with the anchored run as the check; thinking off and on separately. Game-level values from the Step 1 run.csv.")
