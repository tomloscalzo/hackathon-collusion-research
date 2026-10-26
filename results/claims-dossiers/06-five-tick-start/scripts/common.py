"""Shared loaders and per-round metric derivation for dossier 06 (independent of the existing ad hoc scripts)."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "2")
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception:
    pass
import numpy as np, pandas as pd
HK = os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch')
SRC = {
 "gpt-oss-20b (reasoning medium)": (HK + "/oss_analysis/step1/final_t2/run.csv", HK + "/oss_analysis/tables_t2/rounds.csv", "on"),
 "Qwen3-32B thinking on": (HK + "/analysis_final/steps/neutral/step1/run.csv", HK + "/analysis_final/steps/neutral/step1/tables/rounds.csv", "on"),
 "Qwen3-32B thinking off": (HK + "/analysis_final/steps/neutral/step1/run.csv", HK + "/analysis_final/steps/neutral/step1/tables/rounds.csv", "off"),
}
ARM, CTL = "start-5tick", "headline-chat"
def load(model):
    rp, dp, th = SRC[model]
    r = pd.read_csv(rp, low_memory=False)
    r = r[(r.status == "done") & (r.penalty_point == 3) & (r.arm.isin([ARM, CTL])) & (r.thinking == th)].copy()
    rd = pd.read_csv(dp, usecols=["trial_id", "round", "seat", "quote", "profit", "market_price", "imputed"])
    # rounds.csv is keyed by the PLAYED trial id (a rerun carries a suffix such as __x32k); map back to the planned id
    m = dict(zip(r.played_trial_id.fillna(r.trial_id), r.trial_id))
    rd = rd[rd.trial_id.isin(m)].copy(); rd["trial_id"] = rd.trial_id.map(m)
    # a few oss games hold duplicated round records (overlap of two attempts); keep the last record per (round, seat)
    rd = rd.drop_duplicates(["trial_id", "round", "seat"], keep="last")
    return r, rd
def firm_rounds(rd):
    """Per firm-round: own quote, rival's previous quote, competitive / matching flags (round 1 has no previous quote)."""
    a = rd.sort_values(["trial_id", "round", "seat"]).copy()
    a["k"] = a.groupby(["trial_id", "round"]).cumcount()
    w = a.pivot_table(index=["trial_id", "round"], columns="k", values=["quote", "profit", "market_price"]).reset_index()
    w.columns = ["trial_id", "round", "mp0", "mp1", "p0", "p1", "q0", "q1"]  # pivot_table orders the value columns alphabetically
    w = w.sort_values(["trial_id", "round"])
    w["prev_q0"] = w.groupby("trial_id").q0.shift(1); w["prev_q1"] = w.groupby("trial_id").q1.shift(1)
    rows = []
    for me, riv in ((0, 1), (1, 0)):
        d = pd.DataFrame({"trial_id": w.trial_id, "round": w["round"], "q": w[f"q{me}"], "q_riv": w[f"q{riv}"],
                          "riv_prev": w[f"prev_q{riv}"], "own_prev": w[f"prev_q{me}"], "profit": w[f"p{me}"], "mp": w[f"mp{me}"]})
        rows.append(d)
    f = pd.concat(rows, ignore_index=True)
    f["has_prev"] = f.riv_prev.notna()
    f["undercut"] = (f.q < f.riv_prev - 1e-9)
    f["both_floor"] = (f.q <= 1.0 + 1e-9) & (f.q_riv <= 1.0 + 1e-9)
    f["comp"] = f.undercut | f.both_floor
    f["match"] = ((f.q - f.riv_prev).abs() < 1e-9) & (f.q > 1.0 + 1e-9)
    f["at_floor"] = f.q <= 1.05 + 1e-9
    f["price_index_fr"] = (f.mp - 1) / 2
    return f
