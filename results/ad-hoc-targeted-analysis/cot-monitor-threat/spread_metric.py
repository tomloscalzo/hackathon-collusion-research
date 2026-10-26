#!/usr/bin/env python3
"""Average absolute spread for the CoT-monitor-threat analysis (owner rule: all five standard metrics, separately).

The other four metrics (price index, competitive share, matching share, profit gain index) are in analyze.py / paired_effects.csv.
This script adds the fifth, the average absolute spread: the mean market quote (the half-spread) in raw units, 1.00 to 5.00, not rescaled
(run.csv column market_price_mean). Same pairs as analyze.py: threat arm (d-cot-monitor-a / -b) minus headline-chat, thinking on, private
chat, penalty point 1, paired on (wording, seed); 95% percentile bootstrap over the 20 pairs (10,000 resamples, seed 20261025).
Writes spread_effects.csv and inserts the spread rows into ANALYSIS.md (sections 1 and 2, the metrics box and the Terms row).
Usage (from this folder): python -X utf8 spread_metric.py --steps <analysis_final/steps dir>"""
import argparse, re
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
NB, SEED = 10000, 20261025
ap = argparse.ArgumentParser()
ap.add_argument("--steps", required=True, help="analysis_final/steps (holds neutral/ and anchored/ step1/run.csv)")
A = ap.parse_args()


def boot(d):
    d = np.asarray(d, float)
    d = d[~np.isnan(d)]
    n = len(d)
    rng = np.random.default_rng(SEED)
    m = d[rng.integers(0, n, (NB, n))].mean(axis=1)
    return d.mean(), *np.percentile(m, [2.5, 97.5]), n


gl = pd.read_csv(HERE / "game_level.csv")
S = {}
for run in ("neutral", "anchored"):
    df = pd.read_csv(Path(A.steps) / run / "step1" / "run.csv", low_memory=False)
    df = df[(df.status == "done") & (df.thinking == "on") & (df.penalty_point == 1) & df.arm.isin(["headline-chat", "d-cot-monitor-a", "d-cot-monitor-b"])]
    for arm, g in df.groupby("arm"):
        S[(run, arm)] = g.assign(wording=g.wording.astype(int), seed=g.seed.astype(int)).set_index(["wording", "seed"])
    # same games as analyze.py (game_level.csv): the price index must agree
    for arm in ("headline-chat", "d-cot-monitor-a", "d-cot-monitor-b"):
        ref = gl[(gl.run == run) & (gl.arm == arm)].set_index(["wording", "seed"]).price_index
        assert len(ref) == len(S[(run, arm)]) and np.allclose(S[(run, arm)].price_index.reindex(ref.index), ref, atol=1e-3), (run, arm)


def eff(run, arm):
    a, c = S[(run, arm)].market_price_mean, S[(run, "headline-chat")].market_price_mean
    j = pd.concat([a.rename("a"), c.rename("c")], axis=1, join="inner").dropna()
    return j.a - j.c, j.a.mean(), j.c.mean()


rows, diffs = [], {}
for run in ("neutral", "anchored"):
    for arm in ("d-cot-monitor-a", "d-cot-monitor-b"):
        d, am, cm = eff(run, arm)
        diffs[(run, arm)] = d
        mu, lo, hi, n = boot(d)
        rows.append(dict(contrast=f"{run}: threat {arm[-1].upper()} minus headline-chat", arm_mean=am, control_mean=cm, delta=mu, lo=lo, hi=hi, n_pairs=n))
for arm in ("d-cot-monitor-a", "d-cot-monitor-b"):
    d = diffs[("neutral", arm)] - diffs[("anchored", arm)]
    mu, lo, hi, n = boot(d)
    rows.append(dict(contrast=f"threat {arm[-1].upper()}: neutral effect minus anchored effect", arm_mean=diffs[("neutral", arm)].mean(), control_mean=diffs[("anchored", arm)].mean(), delta=mu, lo=lo, hi=hi, n_pairs=n))
for run in ("neutral", "anchored"):
    d = diffs[(run, "d-cot-monitor-a")] - diffs[(run, "d-cot-monitor-b")]
    mu, lo, hi, n = boot(d)
    rows.append(dict(contrast=f"{run}: threat A effect minus threat B effect", arm_mean=np.nan, control_mean=np.nan, delta=mu, lo=lo, hi=hi, n_pairs=n))
E = pd.DataFrame(rows)
E.to_csv(HERE / "spread_effects.csv", index=False, float_format="%.6f")
f = lambda x: f"{x:+.3f}"
ci = lambda r: f"{f(r.delta)} [{f(r.lo)}, {f(r.hi)}]"
R = {r.contrast: r for r in E.itertuples()}

md = HERE / "ANALYSIS.md"
s = md.read_text(encoding="utf-8")
# drop earlier insertions so the script can be rerun
s = re.sub(r"^\| (neutral|anchored) \| [AB] \| average absolute spread \|[^\n]*\n", "", s, flags=re.M)
s = re.sub(r"^\| [AB] \| average absolute spread \|[^\n]*\n", "", s, flags=re.M)
# section 1 table: four rows before the price-index rows
rows1 = "".join(f"| {run} | {t} | average absolute spread | {R[f'{run}: threat {t} minus headline-chat'].arm_mean:.3f} | {R[f'{run}: threat {t} minus headline-chat'].control_mean:.3f} | {ci(R[f'{run}: threat {t} minus headline-chat'])} |\n"
                for run, t in (("neutral", "A"), ("neutral", "B"), ("anchored", "A"), ("anchored", "B")))
anchor1 = "| neutral | A | price index |"
assert anchor1 in s
s = s.replace(anchor1, rows1 + anchor1, 1)
# section 2 table: two rows before the price-index rows
rows2 = "".join(f"| {t} | average absolute spread | {f(R[f'threat {t}: neutral effect minus anchored effect'].arm_mean)} | {f(R[f'threat {t}: neutral effect minus anchored effect'].control_mean)} | {ci(R[f'threat {t}: neutral effect minus anchored effect'])} |\n" for t in ("A", "B"))
anchor2 = chr(10) + "| A | price index |"
assert anchor2 in s
s = s.replace(anchor2, "\n" + rows2.split("\n")[0] + anchor2, 1)
anchor2b = chr(10) + "| B | price index |"
assert anchor2b in s
s = s.replace(anchor2b, "\n" + rows2.split("\n")[1] + anchor2b, 1)
# metrics box bullet
if "Average absolute spread" not in s.split("## Verdict")[0]:
    box = "> - **Price index** = (market price"
    assert box in s
    s = s.replace(box, "> - **Average absolute spread** = the mean market quote (the half-spread) in raw units, 1.00 (competitive) to 5.00, not rescaled; 3.00 is the monopoly price. Lower = more competitive.\n" + box, 1)
# Terms row for the measure
old = "| measure | Price index, competitive share"
if old in s:
    s = s.replace(old, "| measure | Average absolute spread (mean market quote in raw units, 1.00 to 5.00, not rescaled), price index, competitive share", 1)
# A vs B sentence
ab_n, ab_a = R["neutral: threat A effect minus threat B effect"], R["anchored: threat A effect minus threat B effect"]
note = (f"Average absolute spread, A minus B (`spread_effects.csv`): neutral {ci(ab_n)}, anchored {ci(ab_a)} (raw quote units; positive = A's quotes are higher than B's).")
if "Average absolute spread, A minus B" not in s:
    key = "Threat A against threat B (A minus B, `a_vs_b.csv`):"
    assert key in s
    i = s.index(key)
    j = s.index("\n", i)
    s = s[:j] + " " + note + s[j:]
s = s.replace("(`neutral_vs_anchored.csv`)", "(`neutral_vs_anchored.csv`; the spread rows are in `spread_effects.csv`)", 1) if "spread rows are in" not in s else s
s = s.replace("all values are on the 0-to-1 scale of the measure.", "all values are on the scale of the measure (0 to 1, except the average absolute spread, which is in raw quote units, 1.00 to 5.00).")
md.write_text(s, encoding="utf-8", newline="\n")
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(md)
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print(E.to_string())
