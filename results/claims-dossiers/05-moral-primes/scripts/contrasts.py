"""Dossier 05: contrasts on the five standard metrics, both models, with bootstrap CI, exact sign-flip p, Holm, MDE."""
import os
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np, pandas as pd
OUT = ".."
G = pd.read_csv(f"{OUT}/games_raw.csv")
QR = pd.read_csv(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/analysis_final/steps/neutral/step1/run.csv'), low_memory=False)
QR = QR[(QR.status == "done") & (QR.arm == "headline-chat") & (QR.penalty_point == 1)]
H = QR[["arm", "wording", "seed", "thinking", "market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]].copy(); H["model"] = "qwen"
OR = pd.read_csv(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/oss_analysis/step1/final_t2/run.csv'), low_memory=False)
OR = OR[(OR.status == "done") & (OR.penalty_point == 1) & OR.arm.isin(["hrep-fx-chat-p1", "hrep-nx-chat-p1"])]
HR = OR[["arm", "wording", "seed", "thinking", "market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]].copy(); HR["model"] = "gptoss"
cols = ["model", "arm", "wording", "seed", "thinking", "market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
ALL = pd.concat([G[cols], H[cols], HR[cols]], ignore_index=True)
ALL.to_csv(f"{OUT}/game_table_used.csv", index=False)
MET = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"), ("profit_gain_index", "Profit gain index"),
       ("competitive_share", "Competitive share (U16)"), ("matching_share", "Matching share")]
NB = 10000
def series(model, thinking, arm, metric):
    if arm == "pooled-control":
        s = pd.concat([ALL[(ALL.model == model) & (ALL.thinking == thinking) & (ALL.arm == a)].set_index(["wording", "seed"])[metric] for a in ["headline-chat", "hrep-fx-chat-p1", "hrep-nx-chat-p1"]], axis=1).mean(axis=1)
        return s
    d = ALL[(ALL.model == model) & (ALL.thinking == thinking) & (ALL.arm == arm)]
    return d.set_index(["wording", "seed"])[metric]
def signflip_p(d, rng):
    n = len(d)
    obs = abs(d.mean())
    if n <= 20:
        idx = np.arange(2 ** n)
        signs = 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1)
        m = np.abs((signs * d).mean(axis=1))
        return float((m >= obs - 1e-12).mean()), "exact"
    sg = rng.choice([-1, 1], size=(200000, n)); m = np.abs((sg * d).mean(axis=1))
    return float((m >= obs - 1e-12).mean()), "MC"
def contrast(model, thinking, a, b, metric, seed=20261025):
    j = pd.concat([series(model, thinking, a, metric).rename("a"), series(model, thinking, b, metric).rename("b")], axis=1).dropna()
    d = (j.a - j.b).to_numpy(); n = len(d)
    rng = np.random.default_rng(seed)
    bm = d[rng.integers(0, n, (NB, n))].mean(axis=1)
    p, kind = signflip_p(d, rng)
    se = d.std(ddof=1) / np.sqrt(n)
    return dict(n=n, mean_a=j.a.mean(), mean_b=j.b.mean(), diff=d.mean(), lo=np.percentile(bm, 2.5), hi=np.percentile(bm, 97.5), p=p, p_kind=kind, se=se, mde=2.8 * se)
CON = [("A-H", "moral-prime", "headline-chat"), ("B-H", "moral-prime-b", "headline-chat"), ("P-H", "moral-placebo", "headline-chat"),
       ("A-P", "moral-prime", "moral-placebo"), ("B-P", "moral-prime-b", "moral-placebo"), ("A-B", "moral-prime", "moral-prime-b")]
CELLS = [("gptoss", "on", "gpt-oss-20b (medium effort)"), ("qwen", "on", "Qwen3-32B thinking on"), ("qwen", "off", "Qwen3-32B thinking off")]
rows = []
for model, th, lab in CELLS:
    for cid, a, b in CON:
        for m, _ in MET:
            r = contrast(model, th, a, b, m); r.update(model=model, thinking=th, cell=lab, contrast=cid, arm_a=a, arm_b=b, metric=m); rows.append(r)
# pooled control sensitivity (gpt-oss)
for cid, a, b in [("A-pooled", "moral-prime", "pooled-control"), ("B-pooled", "moral-prime-b", "pooled-control"), ("P-pooled", "moral-placebo", "pooled-control")]:
    for m, _ in MET:
        r = contrast("gptoss", "on", a, b, m); r.update(model="gptoss", thinking="on", cell="gpt-oss-20b (medium effort)", contrast=cid, arm_a=a, arm_b=b, metric=m); rows.append(r)
C = pd.DataFrame(rows)
# Holm over the family: 6 contrasts x 3 cells = 18 price-index tests
fam = C[(C.metric == "price_index") & C.contrast.isin([c[0] for c in CON])].copy()
order = fam.sort_values("p").index; k = len(fam); run = 0.0; holm = {}
for rank, i in enumerate(order):
    run = max(run, min(1.0, (k - rank) * fam.loc[i, "p"])); holm[i] = run
C["holm_p_price_family18"] = pd.Series(holm)
C.to_csv(f"{OUT}/contrasts_five_metrics.csv", index=False, float_format="%.6f")
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(C[C.metric == "price_index"][["cell", "contrast", "n", "mean_a", "mean_b", "diff", "lo", "hi", "p", "p_kind", "holm_p_price_family18", "mde"]].round(4).to_string())
# means per arm
means = ALL.groupby(["model", "thinking", "arm"])[[m for m, _ in MET]].agg(["mean", "count"]).round(3)
means.to_csv(f"{OUT}/arm_means.csv")
print(means.xs("mean", axis=1, level=1) if False else ALL.groupby(["model", "thinking", "arm"])[[m for m, _ in MET]].mean().round(3))
