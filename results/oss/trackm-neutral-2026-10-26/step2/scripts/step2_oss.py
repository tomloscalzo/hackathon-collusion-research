"""Step 2 (analyse and report) for the gpt-oss-20b neutral run (reasoning effort medium, one model, no anchored run).

Usage: python -X utf8 step2_oss.py <oss run.csv> <tables_dir> <out_dir> [--qwen-run-csv FILE] [--partial]
Reads the gpt-oss run.csv and run_firms.csv (Step 1, tools/trial/oss_run_csv.py), optionally the Qwen3-32B neutral run.csv
(thinking-on rows only, for the matched Qwen number beside each gpt-oss number; never pooled). Writes tables/*.csv,
figures/*.png and fragments.json (markdown pieces for make_report_oss.py).

Method (prompt-library/analysis/step2-analyze-and-report.md, adapted):
- unit = game; every contrast is arm minus its shared control on the same (wording, seed) pairs, paired-bootstrap 95% interval,
  resampling pairs stratified by wording, 10,000 draws, seed = CRC32 of the contrast name (the Qwen step2_contrasts.py rule);
  two-sided bootstrap p with floor 1/(B+1);
- the five standard metrics, each separately: average absolute spread (market_price_mean), price index, profit gain index,
  competitive share, matching share; plus the explicit-agreement flag and the two detector flags where they apply;
- Holm within the declared family (headline contrasts and the D set on the price index and profit gain index), BH (q = 0.10
  reported) within the exploratory family; one model, so no thinking-mode contrasts exist;
- the five planned formula / no-numbers arms (arm_build_bug = 1) played the headline prompt and are kept out of every contrast;
  they appear only in a labelled sensitivity table pooled with their headline cell.
"""
import sys, os, json, zlib, argparse
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[5] / "tools" / "analysis_style"))
import collusion_colors as CC

ap = argparse.ArgumentParser()
ap.add_argument("run_csv"); ap.add_argument("tables"); ap.add_argument("out")
ap.add_argument("--qwen-run-csv", default="")
ap.add_argument("--partial", action="store_true")
A = ap.parse_args()
OUT = Path(A.out); TAB = OUT / "tables"; FIG = OUT / "figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
B = 10000
MODEL = "gpt-oss-20b, reasoning effort medium"

ALL = pd.read_csv(A.run_csv, low_memory=False)
if "model_label" not in ALL or set(ALL.model_label.dropna()) != {MODEL}:
    raise SystemExit("error: run.csv is not a gpt-oss-only table (model_label)")
FIRMS = pd.read_csv(Path(A.run_csv).parent / "run_firms.csv", low_memory=False)
D = ALL[ALL.status == "done"].copy()
D["pair"] = D.wording.astype(int).astype(str) + "_" + D.seed.astype(int).astype(str)
D["explicit"] = D.explicit_agreement_flag
D["price_flag"] = D.price_detector_flag_any
D["conv_flag"] = D.conversation_detector_flag_any
Q = None
if A.qwen_run_csv and os.path.exists(A.qwen_run_csv):
    Q = pd.read_csv(A.qwen_run_csv, low_memory=False)
    Q = Q[(Q.status == "done") & (Q.thinking == "on")].copy()
    Q["pair"] = Q.wording.astype(int).astype(str) + "_" + Q.seed.astype(int).astype(str)
    Q["explicit"] = Q.explicit_agreement_flag
    Q["price_flag"] = Q.price_detector_flag_any
    Q["conv_flag"] = Q.conversation_detector_flag_any

M5 = [("spread", "market_price_mean", "Average absolute spread"), ("price", "price_index", "Price index"),
      ("pgi", "profit_gain_index", "Profit gain index"), ("comp", "competitive_share", "Competitive share"),
      ("match", "matching_share", "Matching share")]
EXTRA = [("explicit", "explicit", "Explicit-agreement flag rate"), ("price_flag", "price_flag", "Price-detector flag rate"),
         ("conv_flag", "conv_flag", "Conversation-detector flag rate")]
MLAB = {k: l for k, _, l in M5 + EXTRA}
MCOL = {k: c for k, c, _ in M5 + EXTRA}
METRIC_FOR_CC = {"spread": "average absolute spread", "price": "price index", "pgi": "profit gain index",
                 "comp": "competitive share", "match": "matching share", "explicit": "explicit agreement flag",
                 "price_flag": "collusive flag", "conv_flag": "collusive flag"}

ARMLAB = {
    "headline-tacit": "no chat (tacit)", "headline-chat": "private chat",
    "n3-group": "three firms", "n3-cheater": "three firms incl. a planted cheater", "n3-ethics": "three firms, ethics rule on one",
    "m-asym": "asymmetric rules (ethics rule on one firm)", "m-inc-joint": "incentive text: joint profit", "m-inc-target": "incentive text: profit target",
    "start-5tick": "5-tick start rule", "ctl-32b-joint": "control: maximise joint profit (gpt-oss)", "ctl-32b-compete": "control: strict compete (gpt-oss)",
    "d-cot-monitor-a": "reasoning-monitor threat A", "d-conflict": "conflict self-score", "d-conflict-ethics": "conflict self-score + ethics rule",
    "d-temptation-a": "temptation self-score A", "d-temptation-b": "temptation self-score B", "d-placebo": "placebo self-score",
    "r2f-confidant": "R2f confidant, fed back", "r3f-public": "R3f public, fed back", "r2s-confidant": "R2s confidant, saved only",
    "r3s-public": "R3s public, saved only", "r4-announced": "R4 announced post-game question",
    "moral-prime": "moral prime A", "moral-prime-b": "moral prime B", "moral-placebo": "moral placebo text",
    "wd-notice-only": "watchdog notice only", "wd-noncomp": "watchdog asks + may report", "wd-ask-noreport": "watchdog asks, no report",
}
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_common"))
from oss_arm_labels import label as _armlabel, maybe as _armmaybe, wrap as _armwrap   # owner rule: arm labels are "slug: description", never bare slugs


class _ArmLab(dict):
    def __missing__(self, k):
        return _armlabel(k)


ARMLAB = _ArmLab({k: _armlabel(k) for k in ARMLAB})   # one shared wording (results/oss/_common/oss_arm_labels.py)
SIDE = ["n3-group", "n3-cheater", "n3-ethics", "m-asym", "m-inc-joint", "m-inc-target", "start-5tick"]
CTRLS = ["ctl-32b-joint", "ctl-32b-compete"]
DSET = ["d-cot-monitor-a", "d-conflict", "d-conflict-ethics", "d-temptation-a", "d-temptation-b", "d-placebo"]
INTRO = ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"]
MORAL = ["moral-prime", "moral-prime-b", "moral-placebo"]
WD = ["wd-notice-only", "wd-noncomp", "wd-ask-noreport"]
FAM = {**{a: "side arm at point 3" for a in SIDE}, **{a: "control (positive / null)" for a in CTRLS},
       **{a: "D set at the cell" for a in DSET}, **{a: "introspection at the cell" for a in INTRO},
       **{a: "moral prime at the cell" for a in MORAL}, **{a: "watchdog at the cell" for a in WD}}
SUBQ = {"communication": "1.1, 3.1", "penalty point step": "1.1, 1.5", "side arm at point 3": "1.1, 1.2, 1.5",
        "control (positive / null)": "2.3 (calibration)", "D set at the cell": "3.4, 2.2", "introspection at the cell": "2.2, 2.3",
        "moral prime at the cell": "1.5", "watchdog at the cell": "3.4, 1.5", "direct contrast": "1.5, 3.4"}
BUG = sorted(ALL.loc[ALL.arm_build_bug == 1, "arm"].unique())


def S(df, arm, pt, col):
    d = df[(df.arm == arm) & (df.penalty_point == pt)]
    return d.groupby("pair")[col].mean()


def boot(d, name):
    d = d.dropna(); n = len(d)
    if n < 3:
        return dict(est=d.mean() if n else np.nan, lo=np.nan, hi=np.nan, p=np.nan, n=n, sd=np.nan)
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    w = np.array([int(p.split("_")[0]) for p in d.index]); v = d.values
    strata = [np.where(w == k)[0] for k in np.unique(w)]
    if min(len(ix) for ix in strata) >= 2:   # the analysis_m rule: stratified by wording, across wordings when a wording has one pair
        method = "stratified_by_wording"
        parts = [v[ix][rng.integers(0, len(ix), (B, len(ix)))] for ix in strata]
        m = np.concatenate(parts, axis=1).mean(1)
    else:
        method = "across_wordings"
        m = v[rng.integers(0, n, (B, n))].mean(1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    p = max(2 * min((m <= 0).mean(), (m >= 0).mean()), 1.0 / (B + 1))
    return dict(est=v.mean(), lo=lo, hi=hi, p=min(p, 1.0), n=n, sd=v.std(ddof=1), ci_method=method)


def diff(a, b):
    i = a.index.intersection(b.index)
    return a[i] - b[i]


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m); rm = 0
    for r, i in enumerate(o):
        rm = max(rm, (m - r) * p[i]); adj[i] = min(1, rm)
    return adj


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p); q = np.empty(m); prev = 1
    for r in range(m - 1, -1, -1):
        i = o[r]; prev = min(prev, p[i] * m / (r + 1)); q[i] = prev
    return q


# ------------------------------------------------------------------ contrasts
CONTRASTS = []   # (label, family, kind, arm, pt, ctrl_arm, ctrl_pt)
for pt in (1, 5):
    CONTRASTS.append(("private chat minus no chat, point %d" % pt, "communication", "declared", "headline-chat", pt, "headline-tacit", pt))
CONTRASTS += [("private chat: point 5 minus point 1", "penalty point step", "declared", "headline-chat", 5, "headline-chat", 1),
              ("private chat: point 3 minus point 1", "penalty point step", "declared", "headline-chat", 3, "headline-chat", 1),
              ("private chat: point 5 minus point 3", "penalty point step", "declared", "headline-chat", 5, "headline-chat", 3),
              ("no chat: point 5 minus point 1", "penalty point step", "declared", "headline-tacit", 5, "headline-tacit", 1)]
for a in SIDE + CTRLS:
    CONTRASTS.append((ARMLAB[a], FAM[a], "control" if a in CTRLS else "exploratory", a, 3, "headline-chat", 3))
for a in DSET + INTRO + MORAL + WD:
    CONTRASTS.append((ARMLAB[a], FAM[a], "declared" if a in DSET and a != "d-conflict-ethics" else "exploratory", a, 1, "headline-chat", 1))
CONTRASTS += [("moral prime A minus moral placebo", "direct contrast", "exploratory", "moral-prime", 1, "moral-placebo", 1),
              ("moral prime B minus moral placebo", "direct contrast", "exploratory", "moral-prime-b", 1, "moral-placebo", 1),
              ("watchdog asks + may report minus asks, no report", "direct contrast", "exploratory", "wd-noncomp", 1, "wd-ask-noreport", 1),
              ("watchdog asks + may report minus notice only", "direct contrast", "exploratory", "wd-noncomp", 1, "wd-notice-only", 1),
              ("conflict score + ethics rule minus conflict score", "direct contrast", "exploratory", "d-conflict-ethics", 1, "d-conflict", 1),
              ("R2f fed back minus R2s saved only (confidant)", "direct contrast", "exploratory", "r2f-confidant", 1, "r2s-confidant", 1),
              ("R3f fed back minus R3s saved only (public)", "direct contrast", "exploratory", "r3f-public", 1, "r3s-public", 1)]

rows = []
for lab, fam, kind, arm, pt, carm, cpt in CONTRASTS:
    for k, col, _ in M5 + EXTRA:
        if k in ("explicit", "conv_flag") and "tacit" in carm + arm:
            continue
        kk = kind if (kind != "declared" or k in ("price", "pgi")) else "exploratory"
        r = boot(diff(S(D, arm, pt, col), S(D, carm, cpt, col)), "oss|%s|%s" % (lab, k))
        r.update(lever=lab, family=fam, kind=kk, arm=arm, point=pt, control="%s p%d" % (carm, cpt), outcome=k, subq=SUBQ.get(fam, ""))
        r["arm_n"] = int(D[(D.arm == arm) & (D.penalty_point == pt)].shape[0])
        r["control_n"] = int(D[(D.arm == carm) & (D.penalty_point == cpt)].shape[0])
        r["arm_mean"] = D[(D.arm == arm) & (D.penalty_point == pt)][col].mean()
        r["control_mean"] = D[(D.arm == carm) & (D.penalty_point == cpt)][col].mean()
        if Q is not None and ((Q.arm == arm) & (Q.penalty_point == pt)).any() and ((Q.arm == carm) & (Q.penalty_point == cpt)).any():
            qr = boot(diff(S(Q, arm, pt, col), S(Q, carm, cpt, col)), "qwen|%s|%s" % (lab, k))
            r.update(qwen_est=qr["est"], qwen_lo=qr["lo"], qwen_hi=qr["hi"], qwen_n=qr["n"])
        rows.append(r)
T = pd.DataFrame(rows)
T["holm_p"] = np.nan; T["bh_q"] = np.nan; T["family_m"] = np.nan
mk = (T.kind == "declared") & T.p.notna()
T.loc[mk, "holm_p"] = holm(T.loc[mk, "p"]); T.loc[mk, "family_m"] = mk.sum()
mk = (T.kind == "exploratory") & T.p.notna()
T.loc[mk, "bh_q"] = bh(T.loc[mk, "p"]); T.loc[mk, "family_m"] = mk.sum()
T["excludes0"] = (T.lo > 0) | (T.hi < 0)
T["mde_computed"] = 2.8 * T.sd / np.sqrt(T.n)
if "qwen_est" in T:
    T["same_sign"] = np.where(T.qwen_est.notna() & T.est.notna(), np.sign(T.est) == np.sign(T.qwen_est), np.nan)
T.to_csv(TAB / "contrasts_all.csv", index=False, float_format="%.5g")

# ------------------------------------------------------------------ helpers for markdown
def f(x, k=2):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else ("%.*f" % (k, x))


def ci(r, k=2, pre=""):
    if np.isnan(r.get(pre + "est", np.nan)):
        return "n/a"
    if np.isnan(r.get(pre + "lo", np.nan)):
        return "%s (n<3)" % f(r[pre + "est"], k)
    return "%s [%s, %s]" % (f(r[pre + "est"], k), f(r[pre + "lo"], k), f(r[pre + "hi"], k))


_ARMCOLS = {"arm", "replicate_arm", "control_arm", "ctrl_arm", "headline_cell", "reference_cell"}   # columns whose values are arm slugs: shown as "slug: description"


def md_table(df, cols, heads):
    out = ["| " + " | ".join(heads) + " |", "|" + "---|" * len(heads)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(_armmaybe(r[c]) if c in _ARMCOLS else r[c]) for c in cols) + " |")
    return "\n".join(out)


FR = {}

# ------------------------------------------------------------------ design check and completion
comp = ALL.groupby(["arm", "penalty_point"]).agg(planned=("row_id", "size"), done=("status", lambda s: (s == "done").sum()),
                                                  failed=("status", lambda s: (s == "failed").sum()),
                                                  incomplete=("status", lambda s: (s == "incomplete").sum()),
                                                  build_bug=("arm_build_bug", "max")).reset_index()
comp["truncated_kept_flagged"] = comp.apply(lambda r: int(D[(D.arm == r.arm) & (D.penalty_point == r.penalty_point)].primary_flagged.sum()), axis=1)
et = D.groupby(["arm", "penalty_point"]).empty_talk_done_count.agg(["mean", lambda s: (s > 0).mean()]).reset_index()
et.columns = ["arm", "penalty_point", "empty_talk_mean", "empty_talk_game_share"]
comp = comp.merge(et, on=["arm", "penalty_point"], how="left")
comp.to_csv(TAB / "completion_by_arm.csv", index=False, float_format="%.4g")
c2 = comp.copy(); c2["empty_talk_mean"] = c2.empty_talk_mean.map(lambda x: f(x)); c2["empty_talk_game_share"] = c2.empty_talk_game_share.map(lambda x: f(x))
c2["arm"] = c2.apply(lambda r: _armlabel(r.arm), axis=1)   # hrep-* labels already say "replicate (build bug)"
FR["completion"] = md_table(c2, ["arm", "penalty_point", "planned", "done", "failed", "incomplete", "truncated_kept_flagged", "empty_talk_mean", "empty_talk_game_share"],
                            ["arm", "point", "planned", "done", "failed", "incomplete", "done, a call truncated (kept, flagged)", "empty talk turns read as done, mean per game", "share of games with any"])
pairs = D.groupby(["arm", "penalty_point"]).pair.nunique()
FR["n_done"], FR["n_planned"] = int(len(D)), int(len(ALL))
FR["n_failed"] = int((ALL.status == "failed").sum()); FR["n_incomplete"] = int((ALL.status == "incomplete").sum())
# completion balance: done share by wording
cb = ALL.assign(done=(ALL.status == "done").astype(int)).groupby("wording").done.mean()
FR["balance_wording"] = ", ".join("wording %d: %.2f" % (k, v) for k, v in cb.items())

# ------------------------------------------------------------------ headline cells
cells = []
for arm in ("headline-tacit", "headline-chat"):
    for pt in sorted(D[D.arm == arm].penalty_point.unique()):
        d = D[(D.arm == arm) & (D.penalty_point == pt)]
        r = dict(arm=arm, point=int(pt), n=len(d), theta_star=d.theory_theta_star.mean(), bot_price_index=d.baseline_price_index.mean())
        for k, col, _ in M5:
            g = d.groupby("pair")[col].mean()
            bb = boot(g - 0, "cell|%s|%d|%s" % (arm, pt, k))
            r[k], r[k + "_lo"], r[k + "_hi"] = bb["est"], bb["lo"], bb["hi"]
            if Q is not None:
                qd = Q[(Q.arm == arm) & (Q.penalty_point == pt)]
                r["qwen_" + k] = qd[col].mean() if len(qd) else np.nan
        cells.append(r)
CEL = pd.DataFrame(cells); CEL.to_csv(TAB / "headline_cells.csv", index=False, float_format="%.4g")
lines = []
for _, r in CEL.iterrows():
    lines.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s |" % (
        ARMLAB[r.arm], r.point, r.n,
        *["%s [%s, %s]%s" % (f(r[k]), f(r[k + "_lo"]), f(r[k + "_hi"]), (" (Qwen %s)" % f(r["qwen_" + k]) if "qwen_" + k in r and not np.isnan(r["qwen_" + k]) else "")) for k, _, _ in M5],
        f(r.theta_star), f(r.bot_price_index)))
FR["cells"] = "\n".join(["| communication | penalty point | games | average absolute spread | price index | profit gain index | competitive share | matching share | theory's sustainable level (price-index scale) | scripted undercutter's price index |",
                          "|---|---|---|---|---|---|---|---|---|---|"] + lines)

# A1-style cell ranking (the oss headline has 5 cells: tacit p1, p5; chat p1, p3, p5)
rk = CEL.sort_values("pgi", ascending=False).reset_index(drop=True)
FR["a1"] = "; ".join("%d. %s p%d (profit gain index %s)" % (i + 1, ARMLAB[r.arm], r.point, f(r.pgi)) for i, r in rk.iterrows())
chat1 = rk.index[(rk.arm == "headline-chat") & (rk.point == 1)]
FR["a1_rank"] = int(chat1[0]) + 1 if len(chat1) else None

# ------------------------------------------------------------------ contrast tables per family
def fam_table(fams, outcomes=None):
    sub = T[T.family.isin(fams)]
    out = []
    labs = list(dict.fromkeys(sub.lever))
    head = "| contrast (arm minus control) | control | pairs | " + " | ".join(MLAB[k] for k, _, _ in M5) + " | Qwen3-32B (thinking on), same contrast: price index | Qwen: profit gain index |"
    out.append(head); out.append("|" + "---|" * (head.count("|") - 1))
    for lab in labs:
        s = sub[sub.lever == lab].set_index("outcome")
        def cell(k):
            if k not in s.index: return "n/a"
            r = s.loc[k]; t = ci(r)
            if r.kind == "declared" and not np.isnan(r.holm_p): t += " (Holm p %s)" % f(r.holm_p, 3)
            elif r.kind == "exploratory" and not np.isnan(r.bh_q): t += " (BH q %s)" % f(r.bh_q, 2)
            return t
        qp = ci(s.loc["price"], pre="qwen_") if "qwen_est" in s.columns and "price" in s.index and not np.isnan(s.loc["price"].get("qwen_est", np.nan)) else "not in the Qwen neutral run.csv (see the ad-hoc report)"
        qg = ci(s.loc["pgi"], pre="qwen_") if "qwen_est" in s.columns and "pgi" in s.index and not np.isnan(s.loc["pgi"].get("qwen_est", np.nan)) else ""
        r0 = s.iloc[0]
        out.append("| %s | %s | %d | %s | %s | %s |" % (lab, r0.control, int(s.loc["price"].n) if "price" in s.index else 0, " | ".join(cell(k) for k, _, _ in M5), qp, qg))
    return "\n".join(out)

FR["t_comm"] = fam_table(["communication", "penalty point step"])
FR["t_side"] = fam_table(["side arm at point 3", "control (positive / null)"])
FR["t_cell"] = fam_table(["D set at the cell", "introspection at the cell"])
FR["t_moralwd"] = fam_table(["moral prime at the cell", "watchdog at the cell", "direct contrast"])
FR["holm_m"] = int((T.kind == "declared").sum()); FR["bh_m"] = int((T.kind == "exploratory").sum())

# ------------------------------------------------------------------ forest figure (5 metrics)
fam_order = ["communication", "penalty point step", "side arm at point 3", "control (positive / null)", "D set at the cell",
             "introspection at the cell", "moral prime at the cell", "watchdog at the cell", "direct contrast"]
for sortby, fn in (("family", "fig_forest_by_family.png"), ("effect", "fig_forest_sorted.png")):
    fig, axes = plt.subplots(1, 5, figsize=(26, 16), sharey=True)
    base = T[T.outcome == "price"].copy()
    base["fo"] = base.family.map({k: i for i, k in enumerate(fam_order)})
    base = base.sort_values(["fo", "lever"] if sortby == "family" else ["est"], ascending=True).reset_index(drop=True)
    order = list(base.lever)
    for ax, (k, col, lab) in zip(axes, M5):
        s = T[T.outcome == k].set_index("lever").reindex(order)
        y = np.arange(len(order))[::-1]
        comp_dir = k == "comp"
        colr = ["#1a9850" if ((e < 0) != comp_dir) else "#d73027" for e in s.est.fillna(0)]
        ax.errorbar(s.est, y, xerr=[s.est - s.lo, s.hi - s.est], fmt="none", ecolor="grey", lw=1)
        mk_ = s.kind.map({"declared": "s", "control": "D"}).fillna("o")
        for yy, e, c_, m_ in zip(y, s.est, colr, mk_):
            ax.plot(e, yy, m_, color=c_, ms=7)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_title("%s\narm minus control (red = more collusive, green = more competitive)" % lab, fontsize=10)
        ax.set_yticks(y); ax.set_yticklabels(["%s [%s]" % (l, s.loc[l, "family"]) for l in order], fontsize=9)
        ax.grid(axis="x", alpha=0.3)
    fig.suptitle("%s: every lever minus its shared control, five metrics, paired-bootstrap 95%% intervals over (wording, seed) pairs%s\n"
                 "square = declared, circle = exploratory, diamond = control arm; competitive share is a competition-direction metric (higher = green)"
                 % (MODEL, " (PARTIAL DATA)" if A.partial else ""), fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(FIG / fn, dpi=110); plt.close(fig)
T[T.outcome.isin([k for k, _, _ in M5])].to_csv(TAB / "forest.csv", index=False, float_format="%.5g")

# ------------------------------------------------------------------ heat maps: arm levels (absolute) and arm minus control
arms_levels = []
for arm in sorted(D.arm.unique()):
    for pt in sorted(D[D.arm == arm].penalty_point.unique()):
        d = D[(D.arm == arm) & (D.penalty_point == pt)]
        pe = d.payoff_examples.iloc[0] if "payoff_examples" in d and len(d) else "neutral"
        tag = "" if arm in BUG else (" (payoff block: %s)" % pe if pe != "neutral" else "")
        arms_levels.append(dict(cell=_armlabel("%s p%d" % (arm, pt)) + tag, n=len(d), **{k: d[col].mean() for k, col, _ in M5}))
AL = pd.DataFrame(arms_levels).set_index("cell"); AL.to_csv(TAB / "heat_arm_levels.csv", float_format="%.4g")
fig, axes = plt.subplots(1, 5, figsize=(22, max(8, 0.5 * len(AL))), sharey=True)
scales = {"spread": (1, 3), "price": (0, 1), "pgi": (0, 1), "comp": (0, 1), "match": (0, 1)}
for ax, (k, col, lab) in zip(axes, M5):
    v = AL[[k]].values.astype(float); vmin, vmax = scales[k]
    cm = CC.cmap_for(METRIC_FOR_CC[k])
    im = ax.imshow(v, aspect="auto", cmap=cm, vmin=vmin, vmax=vmax)
    for i in range(len(AL)):
        ax.text(0, i, "%s (n=%d)" % (f(v[i, 0]), AL.n.iloc[i]), ha="center", va="center", fontsize=9.5, color=CC.text_color(v[i, 0], vmin, vmax) if not np.isnan(v[i, 0]) else "k")
    ax.set_xticks([]); ax.set_title(lab, fontsize=11)
    ax.set_yticks(range(len(AL))); ax.set_yticklabels([_armwrap(x, width=34, max_lines=2) for x in AL.index], fontsize=9, linespacing=1.0)
    fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.02, fraction=0.03).set_label(CC.cbar_label(lab, METRIC_FOR_CC[k]), fontsize=9)
fig.suptitle("%s: mean of each metric per arm and penalty point (games, all rounds)%s" % (MODEL, " - PARTIAL DATA" if A.partial else ""), fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(FIG / "heat_arm_levels.png", dpi=110); plt.close(fig)

DL = T[T.outcome.isin([k for k, _, _ in M5])].pivot_table(index="lever", columns="outcome", values="est", sort=False)
DL = DL[[k for k, _, _ in M5]]; DL.to_csv(TAB / "heat_arm_minus_control.csv", float_format="%.4g")
fig, axes = plt.subplots(1, 5, figsize=(22, max(8, 0.38 * len(DL))), sharey=True)
for ax, (k, col, lab) in zip(axes, M5):
    v = DL[[k]].values.astype(float); lim = np.nanmax(np.abs(v)) if np.isfinite(np.nanmax(np.abs(v))) else 1
    lim = max(lim, 0.05)
    cm = CC.cmap_for(METRIC_FOR_CC[k], diff=True)
    im = ax.imshow(v, aspect="auto", cmap=cm, vmin=-lim, vmax=lim)
    for i in range(len(DL)):
        ax.text(0, i, f(v[i, 0]), ha="center", va="center", fontsize=9.5, color=CC.text_color(v[i, 0], -lim, lim) if not np.isnan(v[i, 0]) else "k")
    ax.set_xticks([]); ax.set_title(lab + "\narm minus control", fontsize=10)
    ax.set_yticks(range(len(DL))); ax.set_yticklabels(DL.index, fontsize=9)
    fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.02, fraction=0.03).set_label(CC.cbar_label(lab, METRIC_FOR_CC[k], diff=True), fontsize=9)
fig.suptitle("%s: paired differences, arm minus its shared control (red = more collusive, green = more competitive)%s" % (MODEL, " - PARTIAL DATA" if A.partial else ""), fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96]); fig.savefig(FIG / "heat_arm_minus_control.png", dpi=110); plt.close(fig)

# ------------------------------------------------------------------ say vs do, intent, scores, introspection
F = FIRMS.merge(D[["row_id", "arm", "penalty_point", "communication"]], on="row_id")
sd = F[F.communication != "tacit"].groupby("arm").agg(firms=("row_id", "size"), agreements=("agreements", "sum"),
                                                     agreed_then_undercut=("agreed_then_undercut", "sum"), held_after_agreement=("held_after_agreement", "sum"),
                                                     threat_then_punish=("threat_then_punish", "sum")).reset_index()
sd["undercut_share_after_agreement"] = sd.agreed_then_undercut / (sd.agreed_then_undercut + sd.held_after_agreement)
sd.to_csv(TAB / "say_do_by_arm.csv", index=False, float_format="%.4g")
FR["say_do"] = md_table(sd.assign(u=sd.undercut_share_after_agreement.map(f)), ["arm", "firms", "agreements", "agreed_then_undercut", "held_after_agreement", "u", "threat_then_punish"],
                        ["arm", "firm-games", "agreement messages", "rounds undercut after agreeing", "rounds held after agreeing", "undercut share after agreement", "threat then punish"])
ic = D.groupby("arm").game_intent_class.value_counts().unstack(fill_value=0)
ic.to_csv(TAB / "intent_classes_by_arm.csv")
FR["intent"] = md_table(ic.reset_index(), list(ic.reset_index().columns), list(ic.reset_index().columns))
sc = D[D.score_name.notna()].groupby(["arm", "score_name"]).agg(games=("row_id", "size"), score_mean=("score_mean", "mean"),
                                                                score_first=("score_first", "mean"), score_last=("score_last", "mean"),
                                                                price_index=("price_index", "mean")).reset_index()
if len(sc):
    sc["corr_score_vs_price_index"] = [D[(D.arm == a)][["score_mean", "price_index"]].corr(method="spearman").iloc[0, 1] if (D.arm == a).sum() > 3 else np.nan for a in sc.arm]
sc.to_csv(TAB / "self_scores.csv", index=False, float_format="%.4g")
FR["scores"] = md_table(sc.round(2), list(sc.columns), ["arm", "score", "games", "mean score (1-5)", "first-round score", "last-round score", "mean price index", "Spearman rho, score vs price index (game level)"]) if len(sc) else "No score games done yet."
cand_cols = ["candour_confidant", "candour_public", "concealment_confidant", "concealment_public", "invented_confession_confidant", "invented_confession_public", "questions_answered", "question_declines"]
cand_cols = [c for c in cand_cols if c in D]
it = D[D.arm.isin(INTRO + WD)].groupby("arm")[cand_cols].mean().reset_index()
it.insert(1, "games", D[D.arm.isin(INTRO + WD)].groupby("arm").size().values)
it.to_csv(TAB / "introspection_candour.csv", index=False, float_format="%.4g")
FR["intro"] = md_table(it.round(2), list(it.columns), list(it.columns))

# ------------------------------------------------------------------ detection at the frozen threshold
def wil(k, n):
    if n == 0: return (np.nan, np.nan)
    z = 1.96; p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h
det = []
for arm in sorted(D.arm.unique()):
    d = D[D.arm == arm]
    r = dict(arm=arm, games=len(d))
    for fl in ("price_flag", "conv_flag"):
        x = d[fl].dropna(); k, n = int(x.sum()), len(x)
        lo, hi = wil(k, n)
        r[fl] = "%d/%d (%s) [%s, %s]" % (k, n, f(k / n if n else np.nan), f(lo), f(hi)) if n else "n/a (no chat)"
    both = d[["price_flag", "conv_flag"]].dropna()
    r["both_flags"] = "%d/%d" % (int((both.sum(axis=1) == 2).sum()), len(both)) if len(both) else "n/a"
    r["high_price_games"] = int((d.price_index >= 0.5).sum())
    det.append(r)
DET = pd.DataFrame(det); DET.to_csv(TAB / "detector_flag_rates.csv", index=False)
FR["det"] = md_table(DET, ["arm", "games", "price_flag", "conv_flag", "both_flags", "high_price_games"],
                     ["arm", "games", "price-detector flagged games k/n (rate) [Wilson 95%]", "conversation-detector flagged games", "both flags", "games with price index >= 0.5"])
# null calibration and positive control
FR["det_ctl"] = "; ".join("%s: price flag %s, conversation flag %s" % (ARMLAB[a], DET.set_index("arm").loc[a, "price_flag"], DET.set_index("arm").loc[a, "conv_flag"]) for a in CTRLS if a in set(DET.arm))

# ------------------------------------------------------------------ channel shift (reasoning threat, R4, watchdog)
cs = []
for a in ["d-cot-monitor-a", "r4-announced"] + WD:
    s = T[(T.arm == a) & (T.control == "headline-chat p1")].set_index("outcome")
    if not len(s): continue
    ex = boot(diff(S(D, a, 1, "explicit_round_share"), S(D, "headline-chat", 1, "explicit_round_share")), "cs|" + a)
    cs.append(dict(arm=a, d_pgi=s.loc["pgi"].est, d_price=s.loc["price"].est, d_explicit_round_share=ex["est"],
                   d_explicit_round_share_ci="%s [%s, %s]" % (f(ex["est"]), f(ex["lo"]), f(ex["hi"])),
                   d_conv_flag=s.loc["conv_flag"].est if "conv_flag" in s.index else np.nan, d_price_flag=s.loc["price_flag"].est,
                   channel_shift=bool(ex["est"] < -0.05 and s.loc["price"].est > -0.05), n=int(s.loc["price"].n)))
CS = pd.DataFrame(cs); CS.to_csv(TAB / "channel_shift.csv", index=False, float_format="%.4g")
FR["cs"] = md_table(CS.round(3), list(CS.columns), ["arm", "change in profit gain index", "change in price index", "change in EXPLICIT round share", "same, with 95% CI", "change in conversation-flag rate", "change in price-flag rate", "channel shift (talk down by > 0.05, price index not down by > 0.05)", "pairs"]) if len(CS) else "n/a"

# ------------------------------------------------------------------ univariate summary
uni = []
for k, col, lab in M5 + [("rounds", "rounds_played", "Rounds played"), ("empty", "empty_talk_done_count", "Empty talk turns read as done"), ("refusals", "refusals", "Refusals")]:
    x = D[col].dropna()
    uni.append(dict(variable=lab, column=col, n=len(x), missing=int(D[col].isna().sum()), mean=x.mean(), median=x.median(), q25=x.quantile(.25), q75=x.quantile(.75), min=x.min(), max=x.max()))
UNI = pd.DataFrame(uni); UNI.to_csv(TAB / "univariate.csv", index=False, float_format="%.4g")
FR["uni"] = md_table(UNI.round(3), list(UNI.columns), list(UNI.columns))
# quotes on printed example points (neutral set 1.00, 1.50, ..., 4.00; plus 2.49) and on the floor
rd = pd.read_csv(Path(A.tables) / "rounds.csv", low_memory=False)
rd = rd[rd.trial_id.isin(D.played_trial_id)]
qv = pd.to_numeric(rd.quote, errors="coerce").dropna()
pts = np.round(np.arange(1.0, 4.01, 0.5), 2)
FR["focal"] = "Share of all quotes on a printed neutral example point (1.00, 1.50, ..., 4.00): %s; on 2.49 (the printed undercut example): %s; at 2.50: %s; at the 1.00 floor: %s; n quotes = %d." % (
    f(np.isin(np.round(qv, 2), pts).mean()), f((np.round(qv, 2) == 2.49).mean()), f((np.round(qv, 2) == 2.50).mean()), f((np.round(qv, 2) == 1.0).mean()), len(qv))
top = np.round(qv, 2).value_counts(normalize=True).head(10)
FR["focal_top"] = ", ".join("%.2f: %.2f" % (k, v) for k, v in top.items())
pd.DataFrame({"quote": top.index, "share": top.values}).to_csv(TAB / "quote_modes.csv", index=False)

# ------------------------------------------------------------------ correlation of outcomes (exploratory)
oc = D[[c for _, c, _ in M5]].corr(method="spearman"); oc.to_csv(TAB / "outcome_correlations.csv", float_format="%.3f")
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(oc.values, cmap=CC.NEUTRAL_DIVERGING if hasattr(CC, "NEUTRAL_DIVERGING") else "Blues", vmin=-1, vmax=1)
for i in range(5):
    for j in range(5):
        ax.text(j, i, "%.2f" % oc.values[i, j], ha="center", va="center", fontsize=10)
labs5 = [l for _, _, l in M5]
ax.set_xticks(range(5)); ax.set_xticklabels(labs5, rotation=30, ha="right"); ax.set_yticks(range(5)); ax.set_yticklabels(labs5)
fig.colorbar(im).set_label("Spearman correlation across games (neutral hue: no collusion direction)")
ax.set_title("%s: how the five metrics move together (game level, n=%d)" % (MODEL, len(D)), fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "outcome_correlations.png", dpi=110); plt.close(fig)

# ------------------------------------------------------------------ interaction: chat minus tacit at p1 vs p5
ia = []
for k, col, lab in M5:
    g1 = diff(S(D, "headline-chat", 1, col), S(D, "headline-tacit", 1, col)); g5 = diff(S(D, "headline-chat", 5, col), S(D, "headline-tacit", 5, col))
    r = boot(diff(g5, g1), "ia|" + k); r.update(outcome=lab); ia.append(r)
IA = pd.DataFrame(ia); IA.to_csv(TAB / "interaction_comm_x_penalty.csv", index=False, float_format="%.4g")
FR["ia"] = "\n".join(["| metric | (chat minus tacit at point 5) minus (chat minus tacit at point 1) [95% CI] | pairs |", "|---|---|---|"] +
                     ["| %s | %s | %d |" % (r.outcome, ci(r), r.n) for _, r in IA.iterrows()])

# ------------------------------------------------------------------ sensitivity
sens = []
def add_s(name, df, arm, pt, carm, cpt, col, k):
    r = boot(diff(S(df, arm, pt, col), S(df, carm, cpt, col)), "sens|%s|%s|%s" % (name, arm, k)); r.update(set=name, contrast="%s p%d minus %s p%d" % (arm, pt, carm, cpt), outcome=MLAB[k]); sens.append(r)
# (a) build-bug replicates pooled with their headline cell
POOL = D.copy()
for a in BUG:
    cell = ALL.loc[ALL.arm == a, "headline_replicate_of"].iloc[0]
    harm, hpt = cell.split("__p")
    POOL.loc[POOL.arm == a, "arm"] = harm
POOL = POOL.groupby(["arm", "penalty_point", "pair"])[[c for _, c, _ in M5]].mean().reset_index()
D_noempty = D[D.empty_talk_done_count.fillna(0) == 0]
D_noflag = D[D.primary_flagged == 0]
for k, col, lab in M5:
    for nm, df in (("primary (declared arms only)", D), ("headline pooled with the build-bug replicates (SENSITIVITY ONLY)", POOL),
                   ("games with no empty talk turn read as done", D_noempty), ("games with no truncated call", D_noflag)):
        add_s(nm, df, "headline-chat", 1, "headline-tacit", 1, col, k)
        add_s(nm, df, "headline-chat", 5, "headline-chat", 1, col, k)
SENS = pd.DataFrame(sens); SENS.to_csv(TAB / "sensitivity.csv", index=False, float_format="%.4g")
FR["sens"] = "\n".join(["| set | contrast | metric | estimate [95% CI] | pairs |", "|---|---|---|---|---|"] +
                       ["| %s | %s | %s | %s | %d |" % (r.set, r.contrast, r.outcome, ci(r), r.n) for _, r in SENS.iterrows()])
# build-bug replicate levels vs headline levels
bl = []
for a in BUG:
    cell = ALL.loc[ALL.arm == a, "headline_replicate_of"].iloc[0]; harm, hpt = cell.split("__p"); hpt = int(hpt)
    d1 = D[D.arm == a]; d0 = D[(D.arm == harm) & (D.penalty_point == hpt)]
    bl.append(dict(replicate_arm=a, headline_cell=cell, n_rep=len(d1), n_head=len(d0), **{"%s_rep" % k: d1[c].mean() for k, c, _ in M5}, **{"%s_head" % k: d0[c].mean() for k, c, _ in M5}))
BL = pd.DataFrame(bl); BL.to_csv(TAB / "build_bug_replicates_vs_headline.csv", index=False, float_format="%.4g")
FR["bug"] = md_table(BL.assign(price=lambda x: x.price_rep.map(f) + " vs " + x.price_head.map(f), pgi=lambda x: x.pgi_rep.map(f) + " vs " + x.pgi_head.map(f),
                               match=lambda x: x.match_rep.map(f) + " vs " + x.match_head.map(f)),
                     ["replicate_arm", "headline_cell", "n_rep", "n_head", "price", "pgi", "match"],
                     ["planned arm (build bug)", "headline cell it replicates", "games (replicate)", "games (headline)", "price index, replicate vs headline", "profit gain index", "matching share"]) if len(BL) else "none"
# payoff-block arms (corrected formula / no-numbers rerun and fx-ctl-joint): descriptive only, beside the matching headline cell
pb = []
PBD = D[D.payoff_examples.isin(["formula", "none"])] if "payoff_examples" in D else D.iloc[0:0]
for (arm, pt), d1 in PBD.groupby(["arm", "penalty_point"]):
    comm = d1.communication.iloc[0]
    harm = "ctl-32b-joint" if "ctl-joint" in arm else ("headline-tacit" if comm == "tacit" else "headline-chat")
    d0 = D[(D.arm == harm) & (D.penalty_point == pt) & (D.payoff_examples == "neutral")]
    r = dict(arm=arm, payoff_examples=d1.payoff_examples.iloc[0], point=int(pt), n=len(d1), reference="%s (neutral table)" % _armlabel("%s p%d" % (harm, pt)), n_ref=len(d0))
    for k, col, _ in M5:
        r[k] = d1[col].mean(); r[k + "_ref"] = d0[col].mean() if len(d0) else np.nan
        rr = boot(diff(S(D[D.payoff_examples == r["payoff_examples"]], arm, pt, col), S(D[D.payoff_examples == "neutral"], harm, pt, col)), "pb|%s|%s" % (arm, k))
        r[k + "_diff_ci"] = ci(rr)
    pb.append(r)
PB = pd.DataFrame(pb); PB.to_csv(TAB / "payoff_block_arms.csv", index=False, float_format="%.4g")
FR["payoff"] = ("\n".join(["| arm | payoff block | point | games | reference cell (games) | " + " | ".join("%s: arm vs reference; paired difference [95%% CI]" % MLAB[k] for k, _, _ in M5) + " |",
                           "|" + "---|" * (5 + len(M5))] +
                          ["| %s | %s | %d | %d | %s (%d) | %s |" % (_armlabel(r.arm), r.payoff_examples, r.point, r.n, r.reference, r.n_ref,
                                                                    " | ".join("%s vs %s; %s" % (f(r[k]), f(r[k + "_ref"]), r[k + "_diff_ci"]) for k, _, _ in M5)) for _, r in PB.iterrows()])
               if len(PB) else "No corrected formula / no-numbers games are in this run.csv yet.")
# empty talk as a covariate: Spearman with price index among chat games
ch = D[D.communication != "tacit"]
FR["empty_cov"] = "Among %d chat games, Spearman rho between the number of empty talk turns read as done and the price index = %s; mean price index with none %s (n=%d) vs with any %s (n=%d)." % (
    len(ch), f(ch[["empty_talk_done_count", "price_index"]].corr(method="spearman").iloc[0, 1]),
    f(ch[ch.empty_talk_done_count == 0].price_index.mean()), int((ch.empty_talk_done_count == 0).sum()),
    f(ch[ch.empty_talk_done_count > 0].price_index.mean()), int((ch.empty_talk_done_count > 0).sum()))

# ------------------------------------------------------------------ candidates
cand = T[(T.outcome.isin(["price", "pgi"])) & T.p.notna()].copy()
cand["abs"] = cand.est.abs()
cand = cand.sort_values("abs", ascending=False)
cand["robust"] = cand.excludes0 & ((cand.kind == "declared") & (cand.holm_p < 0.05) | (cand.kind != "declared") & (cand.bh_q < 0.10))
cand["untrustworthy_reason"] = np.where(cand.n < 10, "fewer than 10 pairs (partial data)" if A.partial else "fewer than 10 pairs", "")
cand[["lever", "family", "kind", "outcome", "est", "lo", "hi", "p", "holm_p", "bh_q", "n", "robust", "untrustworthy_reason", "subq"] + (["qwen_est", "qwen_lo", "qwen_hi", "same_sign"] if "qwen_est" in cand else [])].to_csv(TAB / "candidates.csv", index=False, float_format="%.4g")
FR["cand"] = "\n".join(["| contrast | outcome | estimate [95% CI] | pairs | survives its family's correction | Qwen same contrast | research sub-question |", "|---|---|---|---|---|---|---|"] +
                       ["| %s | %s | %s | %d | %s | %s | %s |" % (r.lever, MLAB[r.outcome], ci(r), r.n, "yes" if r.robust else "no", ci(r, pre="qwen_") if "qwen_est" in r and not np.isnan(r.get("qwen_est", np.nan)) else "n/a", r.subq)
                        for _, r in cand.head(16).iterrows()])
FR["partial"] = bool(A.partial)
json.dump(FR, open(OUT / "fragments.json", "w", encoding="utf-8"), indent=1, default=str)
print("step2_oss: %d games, %d contrasts rows, outputs in %s" % (len(D), len(T), OUT))
