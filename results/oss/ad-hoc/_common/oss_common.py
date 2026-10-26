"""Shared helpers for the gpt-oss-20b ad-hoc analyses (results/oss/ad-hoc/<topic>/).

Standard library only. Import with:  sys.path.insert(0, <this folder>); import oss_common as oc

- oc.load_oss(path)            gpt-oss rows: status done and in_primary 1; the five build-bug arms (arm_build_bug 1: planned formula /
                               no-numbers arms that played the neutral headline prompt) are DROPPED unless include_bug=True.
- oc.load_qwen(path)           Qwen3-32B neutral rows (thinking on by default: the t1 analogue of gpt-oss reasoning effort medium).
- oc.METRICS                   the five standard metrics (column, label, direction: +1 = higher is more collusive).
- oc.paired(rows, a, b)        paired contrast arm a minus control b on (wording, seed); a and b are (arm, penalty_point) tuples.
                               Returns dict per metric: n_pairs, mean_a, mean_b, diff, lo, hi (95% percentile bootstrap, 2000 draws).
- oc.cell_means(rows, arm, pt) mean and 95% bootstrap CI of each metric over the cell's games.
Fixed seed: 20261026.
"""
import csv
import random

import os as _os
from pathlib import Path as _P
_HK = str(_P(_os.environ.get("HACKATHON_DIR", _P.home() / "hackathon"))).replace("\\", "/")   # parent of runs/ and work_scratch/
_REPO = str(_P(__file__).resolve().parents[4]).replace("\\", "/")   # repository root
OSS_RUN = (_HK + "/work_scratch/oss_analysis/step1/final/run.csv")
QWEN_RUN = (_HK + "/work_scratch/analysis_final/steps/neutral/step1/run.csv")
METRICS = [("market_price_mean", "Average absolute spread", +1), ("price_index", "Price index", +1),
           ("profit_gain_index", "Profit gain index", +1), ("competitive_share", "Competitive share", -1),
           ("matching_share", "Matching share", +1)]
SEED = 20261026
B = 2000


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_oss(path=OSS_RUN, include_bug=False):
    rows = [r for r in _read(path) if r["status"] == "done" and r.get("in_primary") == "1"]
    bad = {r.get("model_label") for r in rows} - {"gpt-oss-20b, reasoning effort medium"}
    if bad:
        raise SystemExit("refusing mixed-model input: %s" % bad)
    return rows if include_bug else [r for r in rows if r.get("arm_build_bug") != "1"]


def load_qwen(path=QWEN_RUN, thinking="on"):
    return [r for r in _read(path) if r["status"] == "done" and r.get("in_primary") == "1" and (thinking is None or r["thinking"] == thinking)]


def _pick(rows, arm, pt):
    return [r for r in rows if r["arm"] == arm and (pt is None or str(r["penalty_point"]) == str(pt))]


def _boot(vals, rng):
    n = len(vals)
    ms = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return ms[int(0.025 * B)], ms[int(0.975 * B) - 1]


def cell_means(rows, arm, pt=None):
    rng = random.Random(SEED)
    sub = _pick(rows, arm, pt)
    out = {}
    for col, _, _ in METRICS:
        v = [x for x in (_f(r.get(col)) for r in sub) if x is not None]
        if not v:
            out[col] = {"n": 0, "mean": None, "lo": None, "hi": None}
            continue
        lo, hi = _boot(v, rng)
        out[col] = {"n": len(v), "mean": sum(v) / len(v), "lo": lo, "hi": hi}
    return out


def paired(rows, a, b, rows_b=None):
    """a, b = (arm, penalty_point); rows_b defaults to rows. Pairs on (wording, seed)."""
    rng = random.Random(SEED)
    A = {(r["wording"], r["seed"]): r for r in _pick(rows, *a)}
    Bm = {(r["wording"], r["seed"]): r for r in _pick(rows_b or rows, *b)}
    keys = sorted(set(A) & set(Bm))
    out = {}
    for col, _, _ in METRICS:
        d, va, vb = [], [], []
        for k in keys:
            x, y = _f(A[k].get(col)), _f(Bm[k].get(col))
            if x is None or y is None:
                continue
            d.append(x - y); va.append(x); vb.append(y)
        if not d:
            out[col] = {"n_pairs": 0, "mean_a": None, "mean_b": None, "diff": None, "lo": None, "hi": None}
            continue
        lo, hi = _boot(d, rng)
        out[col] = {"n_pairs": len(d), "mean_a": sum(va) / len(va), "mean_b": sum(vb) / len(vb), "diff": sum(d) / len(d), "lo": lo, "hi": hi}
    return out


def fmt(x, nd=3):
    return "" if x is None else ("%.*f" % (nd, x))
