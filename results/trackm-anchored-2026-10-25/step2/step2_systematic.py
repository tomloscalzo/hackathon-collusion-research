"""Step 2 systematic sections (design check, one-variable summaries, correlation
matrices, screening, heat maps, words vs actions, three-variable views,
sensitivity) for one Track M batch.

Usage: python step2_systematic.py <neutral|anchored> <out_step2_dir>
Reads  <STEPS_ROOT>/<batch>/step1/run.csv, where STEPS_ROOT is an environment variable
       (default: analysis_final/steps under the current directory) holding the Step 1 outputs
       (and the other batch's run.csv for the cross-run sensitivity).
Writes tables/sys_*.csv, figures/sys_*.png and tables/sys_fragments.json
(markdown fragments that the report splices in).
Unit = game; intervals = 95% percentile bootstrap resampling the 20
(wording, seed) pairs; exploratory throughout.
"""
import sys, json, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "analysis_style"))
import collusion_colors as CC   # shared red = collusion / green = competition convention

BATCH, OUT = sys.argv[1], sys.argv[2]
ROOT = os.environ.get("STEPS_ROOT", "analysis_final/steps")
TAB, FIG = os.path.join(OUT, "tables"), os.path.join(OUT, "figures")
os.makedirs(TAB, exist_ok=True); os.makedirs(FIG, exist_ok=True)
RNG = np.random.default_rng(20261025)
B = 2000

def load(b):
    d = pd.read_csv(f"{ROOT}/{b}/step1/run.csv")
    d["evidence_end"] = np.where(d.end_reason.isna(), np.nan, (d.end_reason == "EVIDENCE").astype(float))
    d["t"] = (d.thinking == "on").astype(int)
    d["mode"] = np.where(d.thinking == "on", "t1", "t0")
    d["pair"] = d.wording.astype(str) + "-" + d.seed.astype(str)
    d["high"] = (d.price_index >= 0.5).astype(float).where(d.price_index.notna())
    return d

ALL = load(BATCH); OTHER = load("neutral" if BATCH == "anchored" else "anchored")
DONE = ALL[ALL.status == "done"].copy()
H = DONE[DONE.arm_family == "headline"].copy()          # 3 arms x 4 points x 2 modes x 20 pairs
COMM_ORDER = ["tacit", "private", "monitored"]
FR = {}                                                 # report fragments

# ---------------------------------------------------------------- helpers
def boot_mean(df, col, groupcol="pair"):
    x = df[[col, groupcol]].dropna()
    if len(x) == 0: return (np.nan,) * 3 + (0,)
    g = x.groupby(groupcol)[col].agg(["sum", "count"])
    s, c = g["sum"].values, g["count"].values
    idx = RNG.integers(0, len(g), (B, len(g)))
    bm = s[idx].sum(1) / c[idx].sum(1)
    return s.sum() / c.sum(), *np.percentile(bm, [2.5, 97.5]), int(c.sum())

def f2(x, k=2):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{k}f}"

def mci(df, col, k=2):
    m, lo, hi, n = boot_mean(df, col)
    return "n/a" if n == 0 else f"{m:.{k}f} [{lo:.{k}f}, {hi:.{k}f}]"

def md(df, index=False):
    if index: df = df.reset_index()
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r.values) + " |")
    return "\n".join(out)

def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=130, bbox_inches="tight"); plt.close(fig)

def heat(ax, M, ann, cmap, vmin, vmax, xl, yl, title, cbar_label, fig, xt=None, yt=None, metric=None, col_metrics=None):
    """metric: name of the plotted quantity -> colours by the shared convention (red = more
    collusive, green = more competitive). col_metrics: one metric per column (column-normalised maps).
    Neither given: neutral colour (no collusion direction), with a note on the colourbar."""
    if col_metrics is not None:
        cmaps = [CC.cmap_for(m_) for m_ in col_metrics]
        import matplotlib as mpl
        rgba = np.ones(M.shape + (4,))
        for j, c_ in enumerate(cmaps):
            rgba[:, j, :] = mpl.colormaps[c_](np.clip(np.nan_to_num(M[:, j], nan=0.5), 0, 1)) if isinstance(c_, str) else c_(np.clip(np.nan_to_num(M[:, j], nan=0.5), 0, 1))
        rgba[np.isnan(M)] = (1, 1, 1, 1)
        im = ax.imshow(rgba, aspect="auto")
        sm = mpl.cm.ScalarMappable(cmap=CC.COLLUSION_CMAP, norm=mpl.colors.Normalize(vmin, vmax)); sm.set_array([])
        label = (cbar_label + "\nred = more collusive / green = more competitive (columns of competition-direction metrics run green at the high end);"
                 "\nblue columns have no collusion direction")
        cmap_used = "col"
    else:
        if metric is not None:
            cmap = CC.cmap_for(metric)
        label = CC.cbar_label(cbar_label, metric if metric is not None else "neutral")
        im = ax.imshow(M, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto"); sm = im
        cmap_used = cmap
    ax.set_xticks(range(len(xl))); ax.set_xticklabels(xl, fontsize=9, rotation=0)
    ax.set_yticks(range(len(yl))); ax.set_yticklabels(yl, fontsize=9)
    ax.set_title(title, fontsize=9)
    if xt: ax.set_xlabel(xt, fontsize=8)
    if yt: ax.set_ylabel(yt, fontsize=8)
    afs = CC.fit_annotations(fig, ax, M.shape[0], M.shape[1], [a_ for r_ in ann for a_ in r_])   # numbers >= ~9.5 pt on screen
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isnan(v): continue
            rel = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            if cmap_used == "col":
                white = (rel > 0.85 or rel < 0.15) if col_metrics[j] != "neutral" and CC.direction(col_metrics[j]) != CC.NEUTRAL else rel > 0.7
            elif cmap_used in (CC.COLLUSION_CMAP, CC.COMPETITION_CMAP):
                white = rel > 0.85 or rel < 0.15
            else:
                white = rel > 0.7
            ax.text(j, i, ann[i][j], ha="center", va="center", fontsize=afs, color="white" if white else "black")
    cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02); cb.set_label(label, fontsize=7); cb.ax.tick_params(labelsize=7)

PLAIN = {"price_index": "price index", "profit_gain_index": "profit gain index", "competitive_share": "competitive share",
         "matching_share": "matching share", "undercut_count": "undercuts", "war_length": "war length (rounds)",
         "evidence_end": "ended on evidence", "rounds_played": "rounds played", "collusive_game": "collusive game (flag)",
         "explicit_round_share": "explicit-talk round share", "messages": "messages",
         "explicit_agreement_flag": "explicit agreement (flag)", "explicit_agreement_any": "any agreement message",
         "strategic_round_share": "strategic-talk round share"}
OUTS = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "war_length",
        "evidence_end", "rounds_played", "collusive_game", "explicit_round_share", "messages"]
LEVELNAME = {"communication": "communication", "penalty_point": "penalty point", "thinking": "thinking",
             "wording": "wording", "seed": "seed", "planned_length": "planned length"}

# ---------------------------------------------------------------- 1. design check
cell = (ALL.groupby(["arm_family", "arm", "communication", "penalty_point", "mode"])
        .agg(planned=("row_id", "size"), done=("status", lambda s: (s == "done").sum()),
             never_started=("status", lambda s: (s == "never_started").sum()),
             truncation_rerun=("supersession", lambda s: s.isin(["truncation_rerun", "both"]).sum()),
             rerun_missing=("supersession", lambda s: (s == "rerun_missing").sum()),
             placeholder_rerun=("supersession", lambda s: s.isin(["placeholder_rerun", "both"]).sum()),
             ).reset_index())
dup = DONE.groupby(["arm", "penalty_point", "mode"]).pair.apply(lambda s: s.duplicated().sum()).sum()
cell.to_csv(f"{TAB}/sys_design_planned_done_by_arm_point_mode.csv", index=False)
fam = (cell.groupby(["arm_family", "mode"]).agg(cells=("arm", "size"), planned=("planned", "sum"), done=("done", "sum"),
       never_started=("never_started", "sum"), truncation_rerun=("truncation_rerun", "sum"),
       rerun_missing=("rerun_missing", "sum"), placeholder_rerun=("placeholder_rerun", "sum")).reset_index())
fam["cells_with_20_done"] = cell.groupby(["arm_family", "mode"]).done.apply(lambda s: (s == 20).sum()).values
fam.to_csv(f"{TAB}/sys_design_by_family_mode.csv", index=False)
bad = cell[(cell.done != cell.planned) | ((cell.done != 20) & (cell.planned > 0))]
ns_all14 = ALL[ALL.status == "never_started"].arm.str.contains("14b|smoke").all()
# rerun rate by mode among done
rr = DONE.assign(rr=DONE.supersession.isin(["truncation_rerun", "both", "rerun_missing"]))
rrt = rr.groupby(["mode"]).rr.agg(["sum", "size"])
rr_arm = (rr[rr.arm_family == "headline"].groupby(["arm", "mode"]).rr.agg(["sum", "size"]).reset_index())
rr_arm["rate"] = (rr_arm["sum"] / rr_arm["size"]).round(3)
rr_arm.to_csv(f"{TAB}/sys_rerun_rate_headline.csv", index=False)
fam_t = fam.copy()
fam_t["mode"] = fam_t["mode"].map({"t0": "t0", "t1": "t1"})
fam_show = fam_t[["arm_family", "mode", "cells", "planned", "done", "never_started", "truncation_rerun", "rerun_missing", "placeholder_rerun"]]
cnt_all_cells = int(len(cell)); cnt_20 = int((cell.done == 20).sum())
lines = []
lines.append(f"Systematic check, per arm x penalty point x mode (`tables/sys_design_planned_done_by_arm_point_mode.csv`, {cnt_all_cells} cells): "
             f"{cnt_20} cells have 20 done games; {int((cell.never_started > 0).sum())} cells contain never-started rows "
             f"({'all 14B or smoke arms outside the queue' if ns_all14 else 'CHECK: not only the 14B arms'}); "
             f"{int(dup)} duplicated (wording, seed) pairs inside any arm x point x mode cell. Roll-up by arm family and mode (games):")
lines.append("")
lines.append(md(fam_show))
lines.append("")
rt0, rt1 = rrt.loc["t0"], rrt.loc["t1"]
lines.append(f"**Completion as an outcome.** Truncation reruns (or missing reruns) among done games: thinking off {int(rt0['sum'])} of {int(rt0['size'])}, thinking on {int(rt1['sum'])} of {int(rt1['size'])}. "
             "Among the 24 headline cells, by arm (thinking on only is affected): " +
             "; ".join(f"{r.arm} {int(r['sum'])}/{int(r['size'])}" for _, r in rr_arm[rr_arm['mode'] == 't1'].iterrows()) +
             " (`tables/sys_rerun_rate_headline.csv`). Never-started rows are excluded from every rate below.")
# design association matrix (bias-corrected Cramer's V)
def cramer(x, y):
    t = pd.crosstab(x, y); n = t.values.sum()
    if min(t.shape) < 2: return 0.0
    e = np.outer(t.sum(1), t.sum(0)) / n
    chi2 = ((t.values - e) ** 2 / e).sum()
    phi2 = chi2 / n; r, k = t.shape
    phi2c = max(0, phi2 - (k - 1) * (r - 1) / (n - 1)); rc = r - (r - 1) ** 2 / (n - 1); kc = k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2c / max(1e-12, min(kc - 1, rc - 1))))
DF = ["arm", "communication", "penalty_point", "thinking", "wording", "planned_length", "seed", "firms"]
Dd = DONE[DF].astype(str)
V = pd.DataFrame([[cramer(Dd[a], Dd[b]) if a != b else 1.0 for b in DF] for a in DF], index=DF, columns=DF)
V.round(3).to_csv(f"{TAB}/sys_design_association_cramers_v.csv")
fig, ax = plt.subplots(figsize=(5.6, 4.6))
heat(ax, V.values, [[f"{v:.2f}" for v in r] for r in V.values], "Blues", 0, 1, DF, DF,
     "Design factor association", "bias-corrected Cramer's V (0 to 1)", fig)
plt.setp(ax.get_xticklabels(), rotation=40, ha="right"); save(fig, "sys_design_association.png")
hi = [(a, b, V.loc[a, b]) for i, a in enumerate(DF) for b in DF[i + 1:] if V.loc[a, b] >= 0.3]
FR["design"] = "\n".join(lines) + "\n\n**Design association (all done games).** Pairs with V of 0.3 or more: " + \
    "; ".join(f"{a} x {b} = {v:.2f}" for a, b, v in hi) + \
    ". Seed is nested in wording and planned length (each seed has one wording and one length), arm is tied to firms and, for the two reasoning-monitor arms, to thinking on only. Wording and planned length are crossed (V near 0), so a wording effect and a length effect can be separated; a seed effect cannot be split from its wording and length. ![design association](figures/sys_design_association.png)"

# ---------------------------------------------------------------- 2. one-variable summaries
uni_rows = []
for o in OUTS + ["explicit_agreement_flag", "explicit_agreement_any", "strategic_round_share"]:
    x = H[o].dropna()
    if len(x) == 0: continue
    m, lo, hi_, n = boot_mean(H, o)
    q1, q2, q3 = np.percentile(x, [25, 50, 75])
    uni_rows.append(dict(outcome=o, n=n, missing=len(H) - n, mean=round(m, 3), ci_lo=round(lo, 3), ci_hi=round(hi_, 3),
                         median=round(q2, 3), q1=round(q1, 3), q3=round(q3, 3)))
U = pd.DataFrame(uni_rows); U.to_csv(f"{TAB}/sys_univariate_outcomes_headline.csv", index=False)
Ushow = U.assign(**{"mean [95% CI]": U.apply(lambda r: f"{r['mean']:.2f} [{r.ci_lo:.2f}, {r.ci_hi:.2f}]", axis=1),
                    "median (IQR)": U.apply(lambda r: f"{r['median']:.2f} ({r.q1:.2f}, {r.q3:.2f})", axis=1)})[["outcome", "n", "missing", "mean [95% CI]", "median (IQR)"]]
Ushow["outcome"] = Ushow.outcome.map(lambda o: PLAIN.get(o, o))

TCOLS = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "evidence_end", "rounds_played", "collusive_game", "explicit_agreement_flag"]
def factor_table(df, fac, order=None, ci_cols=("profit_gain_index", "price_index")):
    rows = []
    levels = order or sorted(df[fac].dropna().unique(), key=lambda v: (str(type(v)), v))
    for lv in levels:
        s = df[df[fac] == lv]
        r = {"level": (int(lv) if isinstance(lv, float) and float(lv).is_integer() else lv), "games": len(s)}
        for c in TCOLS:
            r[PLAIN[c]] = mci(s, c) if c in ci_cols else f2(s[c].mean(), 2 if c != "rounds_played" else 1)
        rows.append(r)
    return pd.DataFrame(rows)
fac_tabs = {}
SEEDORDER = None
for fac, order in [("communication", COMM_ORDER), ("penalty_point", [1, 3, 4, 5]), ("thinking", ["off", "on"]),
                   ("wording", [0, 1, 2, 3, 4]), ("planned_length", [7.0, 15.0, 19.0, 20.0])]:
    t = factor_table(H, fac, order); fac_tabs[fac] = t; t.to_csv(f"{TAB}/sys_univariate_by_{fac}_headline.csv", index=False)
# seed (20 levels): CSV, summary only
St = factor_table(H, "seed"); St["wording"] = St.level.map(H.groupby("seed").wording.first()); St["planned_length"] = St.level.map(H.groupby("seed").planned_length.first())
St.to_csv(f"{TAB}/sys_univariate_by_seed_headline.csv", index=False)
seedm = H.groupby("seed").profit_gain_index.mean()
# ICC (between-seed share of variance) for pgi after removing design cell means
H["cellmean"] = H.groupby(["arm", "penalty_point", "mode"]).profit_gain_index.transform("mean")
res = H.profit_gain_index - H.cellmean
bw = res.groupby(H.seed).mean()
seed_sd = float(bw.std(ddof=1)); res_sd = float(res.std(ddof=1))
# arm table (all done games)
arm_rows = []
for arm, s in DONE.groupby("arm"):
    r = {"arm": arm, "family": s.arm_family.iloc[0], "games": len(s)}
    for md_ in ["t0", "t1"]:
        ss = s[s["mode"] == md_]
        r[f"profit gain {md_}"] = mci(ss, "profit_gain_index") if len(ss) else "-"
        r[f"n {md_}"] = len(ss)
    r["price index"] = f2(s.price_index.mean()); r["competitive share"] = f2(s.competitive_share.mean())
    r["ended on evidence"] = f2(s.evidence_end.mean())
    arm_rows.append(r)
AT = pd.DataFrame(arm_rows).sort_values(["family", "arm"]); AT.to_csv(f"{TAB}/sys_univariate_by_arm_all_done.csv", index=False)
const = [c for c in ["payoff_examples", "model_profile", "temperature", "firms"] if DONE[c].nunique() == 1]
uni = ["**Overall (headline games: 3 communication arms x 4 penalty points x 2 modes x 20 pairs = 480).**", "", md(Ushow), ""]
for fac in ["communication", "penalty_point", "thinking", "wording", "planned_length"]:
    uni += [f"**By {LEVELNAME[fac]}** (headline games; each level pools the other factors, which are balanced):", "", md(fac_tabs[fac].rename(columns={"level": LEVELNAME[fac]})), ""]
uni += [f"**By seed.** 20 seeds, each with one wording and one planned length (`tables/sys_univariate_by_seed_headline.csv`; grid in the heat maps). "
        f"Mean profit gain index by seed runs from {seedm.min():.2f} (seed {int(seedm.idxmin())}) to {seedm.max():.2f} (seed {int(seedm.idxmax())}). "
        f"After removing the arm x point x mode cell means, the SD of the 20 seed means is {seed_sd:.3f} against a game-level residual SD of {res_sd:.3f}, "
        f"so a seed (a pair) accounts for about {100 * seed_sd**2 / res_sd**2:.0f}% of the residual variance.", "",
        "**By arm (all 29 arms with done games, both modes; the arm tables of the declared sections give the matched contrasts).**", "",
        md(AT[["arm", "games", "profit gain t0", "n t0", "profit gain t1", "n t1", "price index", "competitive share", "ended on evidence"]]), "",
        f"Constant within the batch and therefore skipped: {', '.join(const)}; payoff-example wording is `{DONE.payoff_examples.iloc[0]}`."]
FR["univariate"] = "\n".join(uni)

# ---------------------------------------------------------------- 3. correlation matrices
CO = ["price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length",
      "explicit_agreement_flag", "explicit_agreement_any", "collusive_game", "explicit_round_share", "strategic_round_share",
      "evidence_end", "rounds_played", "messages"]
CO = [c for c in CO if H[c].notna().sum() > 30 and H[c].nunique() > 1]
bc = {frozenset(p) for p in [("price_index", "profit_gain_index"), ("competitive_share", "matching_share"),
      ("explicit_agreement_flag", "explicit_agreement_any"), ("explicit_round_share", "strategic_round_share")]}
chat = H[H.communication != "tacit"]
R = H[CO].corr(method="spearman", min_periods=30); R.round(3).to_csv(f"{TAB}/sys_spearman_outcomes_headline.csv")
Rc = chat[CO].corr(method="spearman", min_periods=30); Rc.round(3).to_csv(f"{TAB}/sys_spearman_outcomes_chat_games.csv")
fig, axs = plt.subplots(1, 2, figsize=(16, 6.4))
plt.subplots_adjust(wspace=0.6)
for ax, M, ttl in [(axs[0], R, f"All headline games (n={len(H)}; text columns use the {len(chat)} chat games)"), (axs[1], Rc, f"Chat games only (n={len(chat)})")]:
    names = [PLAIN.get(c, c) for c in M.columns]
    heat(ax, M.values, [[f"{v:.2f}" for v in r] for r in M.values], CC.NEUTRAL_DIVERGING, -1, 1, names, names, ttl, "Spearman rank correlation", fig)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
fig.suptitle("Outcome correlations (Spearman)", fontsize=11)
save(fig, "sys_corr_outcomes.png")
pairs = []
for i, a in enumerate(CO):
    for b in CO[i + 1:]:
        v = Rc.loc[a, b] if pd.notna(Rc.loc[a, b]) else R.loc[a, b]
        if pd.notna(v): pairs.append((a, b, v, frozenset((a, b)) in bc or {a, b} <= {"explicit_agreement_flag", "explicit_agreement_any"}))
pairs.sort(key=lambda t: -abs(t[2]))
pt = pd.DataFrame([dict(pair=f"{PLAIN.get(a, a)} x {PLAIN.get(b, b)}", rho=round(v, 2), note="by construction or shared inputs" if c else "") for a, b, v, c in pairs[:12]])
pd.DataFrame([dict(a=a, b=b, rho=v, by_construction=c) for a, b, v, c in pairs]).to_csv(f"{TAB}/sys_spearman_outcome_pairs_ranked.csv", index=False)
pt.to_csv(f"{TAB}/sys_spearman_top_pairs.csv", index=False)
# D-set self scores
DS = DONE[DONE.score_mean.notna()]
SC = ["score_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length", "explicit_agreement_flag", "collusive_game"]
Rs = DS[SC].corr(method="spearman", min_periods=30); Rs.round(3).to_csv(f"{TAB}/sys_spearman_selfscore_dset.csv")
fig, ax = plt.subplots(figsize=(6.4, 5.4))
names = [PLAIN.get(c, "self-score (D-set question)" if c == "score_mean" else c) for c in SC]
heat(ax, Rs.values, [[f"{v:.2f}" for v in r] for r in Rs.values], CC.NEUTRAL_DIVERGING, -1, 1, names, names, f"Self-scores against behaviour (D-set arms, n={len(DS)})", "Spearman rank correlation", fig)
plt.setp(ax.get_xticklabels(), rotation=45, ha="right"); save(fig, "sys_corr_selfscore_dset.png")
sc_by = DS.groupby("arm").score_mean.agg(["mean", "count"]).round(2)
sc_rows = "; ".join(f"{a} mean {r['mean']:.2f}" for a, r in sc_by.iterrows())
rs_ = Rs["score_mean"].drop("score_mean")
sc_top = "; ".join(f"{PLAIN.get(k, k)} {v:+.2f}" for k, v in rs_.sort_values(key=abs, ascending=False).head(4).items())
FR["corr"] = ("**Outcome by outcome, Spearman.** Top pairs (chat games where the text flag exists; `tables/sys_spearman_outcome_pairs_ranked.csv` has all):\n\n" + md(pt) +
              "\n\nPairs marked are true by construction or share inputs (profit gain and price index; competitive and matching share, which sum with 'above' to 1; the two agreement flags; the two talk shares) and are not findings. "
              "![outcome correlations](figures/sys_corr_outcomes.png)\n\n"
              f"**Self-scores.** The 1-to-5 self-scores exist only in the D-set arms (n={len(DS)}; each arm answers one of conflict, placebo or temptation questions): {sc_rows}. "
              f"Strongest rank correlations of the self-score with behaviour: {sc_top}. "
              "Different arms ask different questions, so this pools unlike scores; read it as a screen only. ![self-score correlations](figures/sys_corr_selfscore_dset.png)")

# ---------------------------------------------------------------- 4. screening (headline games)
def ranks_tie(x):
    r = pd.Series(x).rank(method="average").values
    n = len(x); _, c = np.unique(x, return_counts=True)
    ties = 1 - ((c ** 3 - c).sum()) / (n ** 3 - n) if n > 1 else 1
    return r, ties
def eps_from(r, ties, lab_codes, k, n):
    sums = np.bincount(lab_codes, weights=r, minlength=k); cnt = np.bincount(lab_codes, minlength=k)
    ok = cnt > 0
    Hs = 12.0 / (n * (n + 1)) * (sums[ok] ** 2 / cnt[ok]).sum() - 3 * (n + 1)
    Hs /= ties if ties > 0 else 1
    return float(np.sqrt(max(0.0, Hs / (n - 1))))
FACT = ["communication", "penalty_point", "thinking", "wording", "seed", "planned_length"]
KIND = {"communication": "within", "penalty_point": "within", "thinking": "within", "wording": "between", "planned_length": "between", "seed": "game"}
SO = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "war_length", "evidence_end", "rounds_played", "collusive_game", "explicit_round_share"]
MECH = {("planned_length", "rounds_played"), ("seed", "rounds_played"), ("wording", "rounds_played"), ("planned_length", "evidence_end"), ("seed", "evidence_end")}   # a horizon cap sets rounds by construction; a seed fixes the investigation draws
BP = 999
def screen(df, strata_name, facs):
    out = []
    pairs_all = df.groupby("pair").ngroup().values
    for o in SO:
        sub = df[df[o].notna()]
        if sub[o].nunique() < 2: continue
        x = sub[o].values; r, ties = ranks_tie(x); n = len(x)
        cl = sub.groupby("pair").ngroup().values; G = cl.max() + 1
        base = np.argsort(cl, kind="stable")
        for f in facs:
            lab_raw = sub[f].values
            lv, lab = np.unique(lab_raw, return_inverse=True); k = len(lv)
            if k < 2: continue
            e = eps_from(r, ties, lab, k, n)
            means = pd.Series(x).groupby(lab_raw).mean()
            rng_raw = float(means.max() - means.min())
            kind = KIND[f]; cnt = 0
            if kind == "within":
                for _ in range(BP):
                    o_ = np.lexsort((RNG.random(n), cl)); nl = np.empty(n, int); nl[base] = lab[o_]
                    cnt += eps_from(r, ties, nl, k, n) >= e
            elif kind == "between":
                pl = pd.Series(lab).groupby(cl).first().values
                for _ in range(BP):
                    nl = RNG.permutation(pl)[cl]
                    cnt += eps_from(r, ties, nl, k, n) >= e
            else:
                for _ in range(BP):
                    cnt += eps_from(r, ties, RNG.permutation(lab), k, n) >= e
            out.append(dict(stratum=strata_name, outcome=o, factor=f, n=n, levels=k, eps_root=round(e, 3), raw_range=round(rng_raw, 3),
                            perm_p=round((cnt + 1) / (BP + 1), 4), by_construction=((f, o) in MECH) or (f == "communication" and o in ("explicit_round_share",)) ,
                            aliased=(f in ("seed",))))
    return pd.DataFrame(out)
SCR = pd.concat([screen(H, "pooled", FACT), screen(H[H["mode"] == "t0"], "t0", [f for f in FACT if f != "thinking"]),
                 screen(H[H["mode"] == "t1"], "t1", [f for f in FACT if f != "thinking"])])
def bh(p):
    p = np.asarray(p); m = len(p); o = np.argsort(p); q = np.empty(m); prev = 1.0
    for i, j in enumerate(o[::-1]):
        rank = m - i; prev = min(prev, p[j] * m / rank); q[j] = prev
    return q
SCR["bh_q"] = np.nan
SCR = SCR.reset_index(drop=True)
for s_ in SCR.stratum.unique():
    m = (SCR.stratum == s_) & (~SCR.by_construction)
    SCR.loc[m, "bh_q"] = bh(SCR.loc[m, "perm_p"].values).round(4)
SCR.to_csv(f"{TAB}/sys_screening_lever_outcome.csv", index=False)
# overview heat map: factors x outcomes, 3 strata
fig, axs = plt.subplots(1, 3, figsize=(19, 5.2))
plt.subplots_adjust(wspace=0.45)
for ax, s_ in zip(axs, ["pooled", "t0", "t1"]):
    g = SCR[SCR.stratum == s_]; facs = [f for f in FACT if f in g.factor.unique()]
    M = np.full((len(facs), len(SO)), np.nan); A = [[""] * len(SO) for _ in facs]
    for i, f in enumerate(facs):
        for j, o in enumerate(SO):
            r_ = g[(g.factor == f) & (g.outcome == o)]
            if len(r_):
                r_ = r_.iloc[0]; M[i, j] = r_.eps_root
                A[i][j] = f"{r_.eps_root:.2f}" + ("*" if (not r_.by_construction and r_.bh_q < 0.05) else "") + ("m" if r_.by_construction else "")
    heat(ax, M, A, "Blues", 0, 0.7, [PLAIN.get(o, o) for o in SO], [LEVELNAME[f] for f in facs],
         {"pooled": "Both modes pooled", "t0": "Thinking off (t0)", "t1": "Thinking on (t1)"}[s_], "root epsilon-squared (effect size, 0 to 1; higher = factor explains more of the outcome)", fig,
         xt="outcome (game-level)", yt="design factor")
    plt.setp(ax.get_xticklabels(), rotation=50, ha="right")
fig.suptitle("Screening: which lever moves which outcome (headline games; * = permutation BH q < 0.05; m = by construction, excluded)", fontsize=10)
save(fig, "sys_screening_heatmap.png")
def rank_tab(o, strata):
    g = SCR[(SCR.outcome == o) & (SCR.stratum == strata)].sort_values("eps_root", ascending=False)
    return pd.DataFrame({"factor": g.factor.map(LEVELNAME), "root eps-sq": g.eps_root.map(lambda v: f"{v:.2f}"), "max-min of level means": g.raw_range.map(lambda v: f"{v:.2f}"),
                         "perm p": g.perm_p, "BH q": g.bh_q.map(lambda v: "" if pd.isna(v) else f"{v:.3f}")})
rk = rank_tab("profit_gain_index", "pooled")
rk0, rk1 = rank_tab("profit_gain_index", "t0"), rank_tab("profit_gain_index", "t1")
mt = {s_: int(((SCR.stratum == s_) & (~SCR.by_construction)).sum()) for s_ in ["pooled", "t0", "t1"]}
surv = SCR[(SCR.bh_q < 0.05)].copy()
surv_txt = {}
for s_ in ["t0", "t1"]:
    g = surv[surv.stratum == s_].sort_values("eps_root", ascending=False).head(6)
    surv_txt[s_] = "; ".join(f"{LEVELNAME[r.factor]} on {PLAIN.get(r.outcome, r.outcome)} ({r.eps_root:.2f})" for _, r in g.iterrows()) or "none"
FR["screen"] = (f"Effect size is the root epsilon-squared of a Kruskal-Wallis test (0 to 1, comparable across factors and outcomes), with the raw max-minus-min of the level means beside it. "
                f"Permutation p-values use {BP} shuffles (floor {1/(BP+1):.3f}); communication, penalty point and thinking permute labels within each (wording, seed) pair, wording and planned length permute whole pairs, seed permutes games. "
                f"BH within each stratum over {mt['pooled']} (pooled), {mt['t0']} (t0) and {mt['t1']} (t1) tests, by-construction pairs removed before counting. Seed is aliased with wording and planned length, so a seed effect includes both.\n\n"
                "Main outcome, profit gain index, both modes pooled:\n\n" + md(rk) + "\n\nThinking off (t0):\n\n" + md(rk0) + "\n\nThinking on (t1):\n\n" + md(rk1) +
                f"\n\nSurvivors at BH q below 0.05, strongest first. t0: {surv_txt['t0']}. t1: {surv_txt['t1']}. Full table: `tables/sys_screening_lever_outcome.csv`. ![screening](figures/sys_screening_heatmap.png)")

# ---------------------------------------------------------------- 5. heat maps
# 5a single-factor map (rows = levels, columns = outcomes)
HM = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "evidence_end", "collusive_game", "explicit_agreement_flag"]
rows, labs, nn = [], [], []
for fac, order in [("communication", COMM_ORDER), ("penalty_point", [1, 3, 4, 5]), ("thinking", ["off", "on"]), ("wording", [0, 1, 2, 3, 4]), ("planned_length", [7.0, 15.0, 19.0, 20.0])]:
    for lv in order:
        s = H[H[fac] == lv]; rows.append([s[c].mean() for c in HM]); nn.append(len(s)); labs.append(f"{LEVELNAME[fac]} = {int(lv) if isinstance(lv, float) else lv}")
M = np.array(rows); Mn = (M - np.nanmin(M, 0)) / (np.nanmax(M, 0) - np.nanmin(M, 0) + 1e-12)
pd.DataFrame(M, index=labs, columns=HM).assign(games=nn).round(3).to_csv(f"{TAB}/sys_heat_single_factor.csv")
fig, ax = plt.subplots(figsize=(8.6, 8.4))
A = [[("" if np.isnan(M[i, j]) else f"{M[i, j]:.2f}") for j in range(M.shape[1])] for i in range(M.shape[0])]
heat(ax, Mn, A, "Blues", 0, 1, [PLAIN[c] for c in HM], [f"{l}  (n={n})" for l, n in zip(labs, nn)],
     "Single-factor maps: outcome by factor level (number printed = raw mean; colour = column-normalised)", "column-normalised (0 = lowest level, 1 = highest)", fig,
     xt="outcome (game-level; headline games, n = 480)", yt="factor = level (n = games at that level)", col_metrics=HM)
plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
for yy in [2.5, 6.5, 8.5, 13.5]: ax.axhline(yy, color="white", lw=2)
save(fig, "sys_heat_single_factor.png")
# 5b communication x penalty per mode
def grid(df, rowv, colv, val, rows_, cols_):
    M = np.full((len(rows_), len(cols_)), np.nan); A = [[""] * len(cols_) for _ in rows_]; N = np.zeros_like(M)
    for i, r_ in enumerate(rows_):
        for j, c_ in enumerate(cols_):
            s = df[(df[rowv] == r_) & (df[colv] == c_)]
            if len(s) and s[val].notna().any():
                M[i, j] = s[val].mean(); N[i, j] = s[val].notna().sum(); A[i][j] = f"{M[i, j]:.2f}\n(n={int(N[i, j])})"
    return M, A, N
fig, axs = plt.subplots(2, 2, figsize=(12, 6.8))
plt.subplots_adjust(wspace=0.4, hspace=0.3)
for r_, val in enumerate(["profit_gain_index", "competitive_share"]):
    for c_, md_ in enumerate(["t0", "t1"]):
        M, A, N = grid(H[H["mode"] == md_], "communication", "penalty_point", val, COMM_ORDER, [1, 3, 4, 5])
        heat(axs[r_][c_], M, A, None, 0, 1, ["p1", "p3", "p4", "p5"], COMM_ORDER, f"{PLAIN[val]}, thinking {'off' if md_ == 't0' else 'on'}", f"mean {PLAIN[val]} (0 to 1)", fig,
             xt="penalty point (1 = collusion clearly pays, 5 = clearly does not)", yt="communication (tacit = no chat)", metric=val)
        pd.DataFrame(M, index=COMM_ORDER, columns=["p1", "p3", "p4", "p5"]).round(3).to_csv(f"{TAB}/sys_heat_comm_x_penalty_{val}_{md_}.csv")
fig.suptitle("Communication by penalty point, per thinking mode (each cell = mean of the 20 games, one per (wording, seed) pair)", fontsize=10)
save(fig, "sys_heat_comm_x_penalty.png")
# 5c mode x arm (all done arms)
arms = list(AT.arm); fams = AT.set_index("arm").family
M = np.full((len(arms), 2), np.nan); A = [[""] * 2 for _ in arms]
for i, a in enumerate(arms):
    for j, md_ in enumerate(["t0", "t1"]):
        s = DONE[(DONE.arm == a) & (DONE["mode"] == md_)]
        if len(s): M[i, j] = s.profit_gain_index.mean(); A[i][j] = f"{M[i, j]:.2f} (n={len(s)})"
pd.DataFrame(M, index=arms, columns=["t0", "t1"]).round(3).to_csv(f"{TAB}/sys_heat_arm_x_mode.csv")
fig, ax = plt.subplots(figsize=(5.4, 9.2))
heat(ax, M, A, None, 0, 1, ["thinking off", "thinking on"], [f"{a} [{fams[a]}]" for a in arms], "Mode by arm: mean profit gain index, thinking off and on (blank = arm not run in that mode)", "mean profit gain index (0 to 1)", fig,
     xt="thinking mode", yt="arm [arm family]", metric="profit_gain_index")
save(fig, "sys_heat_arm_x_mode.png")
# 5d wording x seed (paraphrase and seed spread), grid wording x seed-within-wording ordered by planned length
sw = H.groupby(["wording", "seed"]).planned_length.first().reset_index().sort_values(["wording", "planned_length"])
sw["k"] = sw.groupby("wording").cumcount()
fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.2))
plt.subplots_adjust(wspace=0.4)
for ax, md_ in zip(axs, ["t0", "t1"]):
    M = np.full((5, 4), np.nan); A = [[""] * 4 for _ in range(5)]
    for _, r_ in sw.iterrows():
        s = H[(H.seed == r_.seed) & (H["mode"] == md_)]
        M[int(r_.wording), int(r_.k)] = s.profit_gain_index.mean(); A[int(r_.wording)][int(r_.k)] = f"{M[int(r_.wording), int(r_.k)]:.2f}\nseed {int(r_.seed)}, L{int(r_.planned_length)}"
    pd.DataFrame(M, index=[f"wording {i}" for i in range(5)], columns=[f"seed rank {k+1} (by length)" for k in range(4)]).round(3).to_csv(f"{TAB}/sys_heat_wording_x_seed_{md_}.csv")
    heat(ax, M, A, None, 0, 1, ["shortest", "", "", "longest"], [f"wording {i}" for i in range(5)], f"thinking {'off' if md_ == 't0' else 'on'} (12 games per cell)", "mean profit gain index", fig,
         xt="seed within wording, ordered by planned length (L = planned rounds)", yt="prompt wording (0 to 4)", metric="profit_gain_index")
fig.suptitle("Wording by seed: mean profit gain of each (wording, seed) pair", fontsize=10)
save(fig, "sys_heat_wording_x_seed.png")
sdw = {m_: H[H['mode'] == m_].groupby("wording").profit_gain_index.mean() for m_ in ["t0", "t1"]}
sds = {m_: H[H['mode'] == m_].groupby("seed").profit_gain_index.mean() for m_ in ["t0", "t1"]}

# ---------------------------------------------------------------- 6. three-variable
# wording x communication x mode
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
plt.subplots_adjust(wspace=0.4)
for ax, md_ in zip(axs, ["t0", "t1"]):
    M, A, N = grid(H[H["mode"] == md_], "wording", "communication", "profit_gain_index", [0, 1, 2, 3, 4], COMM_ORDER)
    heat(ax, M, A, None, 0, 1, COMM_ORDER, [f"wording {i}" for i in range(5)], f"thinking {'off' if md_ == 't0' else 'on'}", "mean profit gain index", fig,
         xt="communication (tacit = no chat)", yt="prompt wording (0 to 4)", metric="profit_gain_index")
    pd.DataFrame(M, index=range(5), columns=COMM_ORDER).round(3).to_csv(f"{TAB}/sys_heat_wording_x_comm_{md_}.csv")
fig.suptitle("Wording x communication x mode (n = 16 games per cell, 4 pairs x 4 penalty points)", fontsize=10)
save(fig, "sys_heat_wording_x_comm_x_mode.png")
# interactions (OLS, parametric bootstrap null)
def design(df, terms, inter):
    cols = [np.ones(len(df))]
    def dummies(c):
        return [(df[c] == v).astype(float).values for v in sorted(df[c].unique())[1:]]
    for t in terms: cols += dummies(t)
    for a, b in inter:
        for da in dummies(a):
            for db in dummies(b): cols.append(da * db)
    return np.column_stack(cols)
def rss(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ beta; return float(r @ r), np.linalg.matrix_rank(X), X @ beta
def interaction(df, terms, inter, y="profit_gain_index", B_=500):
    df = df[df[y].notna()]; yv = df[y].values
    X0, X1 = design(df, terms, []), design(df, terms, inter)
    r0, k0, f0 = rss(X0, yv); r1, k1, _ = rss(X1, yv)
    n = len(yv); F = ((r0 - r1) / (k1 - k0)) / (r1 / (n - k1)); sd = np.sqrt(r0 / (n - k0)); cnt = 0
    for _ in range(B_):
        ys = f0 + RNG.normal(0, sd, n); a0, _, _ = rss(X0, ys); a1, _, _ = rss(X1, ys)
        cnt += (((a0 - a1) / (k1 - k0)) / (a1 / (n - k1))) >= F
    return F, k1 - k0, (cnt + 1) / (B_ + 1), 1 - r0 / float(((yv - yv.mean()) ** 2).sum()), 1 - r1 / float(((yv - yv.mean()) ** 2).sum()), n
irows = []
for md_ in ["t0", "t1"]:
    s = H[H["mode"] == md_]
    F, df_, p, a, b, n = interaction(s, ["communication", "penalty_point"], [("communication", "penalty_point")])
    irows.append(dict(test="communication x penalty point", mode=md_, n=n, extra_df=df_, F=round(F, 2), boot_p=round(p, 3), R2_additive=round(a, 2), R2_with_interaction=round(b, 2)))
for t_, ter, it in [("communication x thinking (point adjusted)", ["communication", "penalty_point", "thinking"], [("communication", "thinking")]),
                    ("penalty point x thinking (communication adjusted)", ["communication", "penalty_point", "thinking"], [("penalty_point", "thinking")])]:
    F, df_, p, a, b, n = interaction(H, ter, it)
    irows.append(dict(test=t_, mode="pooled", n=n, extra_df=df_, F=round(F, 2), boot_p=round(p, 3), R2_additive=round(a, 2), R2_with_interaction=round(b, 2)))
IT = pd.DataFrame(irows); IT.to_csv(f"{TAB}/sys_interactions_profit_gain.csv", index=False)
# three-variable table: comm x penalty x mode, pgi mean[CI] and collusive k/n
t3 = []
for md_ in ["t0", "t1"]:
    for c_ in COMM_ORDER:
        r = {"mode": md_, "communication": c_}
        for p_ in [1, 3, 4, 5]:
            s = H[(H["mode"] == md_) & (H.communication == c_) & (H.penalty_point == p_)]
            r[f"p{p_}"] = f"{mci(s, 'profit_gain_index')} ({int(s.collusive_game.sum())}/{len(s)})"
        t3.append(r)
T3 = pd.DataFrame(t3); T3.to_csv(f"{TAB}/sys_three_var_comm_penalty_mode.csv", index=False)
FR["heat"] = ("![single-factor map](figures/sys_heat_single_factor.png)\n\n"
              "Single-factor map: each row is one level of one factor (headline games, other factors pooled), each column an outcome; colour is normalised within a column so levels compare, the printed number is the raw mean (`tables/sys_heat_single_factor.csv`).\n\n"
              "![communication by penalty point](figures/sys_heat_comm_x_penalty.png)\n\n"
              "Communication by penalty point per mode (2D maps; 20 games per cell; absolute 0 to 1 scale; CSVs `tables/sys_heat_comm_x_penalty_*.csv`).\n\n"
              "![mode by arm](figures/sys_heat_arm_x_mode.png)\n\n"
              "Mode by arm (all arms with done games; n printed in each cell; side arms run at their own penalty point, so compare with the headline row at the same point, not with each other).\n\n"
              "![wording by seed](figures/sys_heat_wording_x_seed.png)\n\n"
              f"Paraphrase and seed spread (12 games per cell: 3 communication arms x 4 penalty points). Across the five wordings the mean profit gain index spans {sdw['t0'].min():.2f} to {sdw['t0'].max():.2f} (thinking off) and {sdw['t1'].min():.2f} to {sdw['t1'].max():.2f} (thinking on); "
              f"across the 20 seeds it spans {sds['t0'].min():.2f} to {sds['t0'].max():.2f} and {sds['t1'].min():.2f} to {sds['t1'].max():.2f}.")
FR["interact"] = ("Interaction tests on profit gain index (least squares with indicator terms; null from a parametric bootstrap of 500 draws under the additive fit; games as units, so the p-values ignore the pair clustering and are indicative):\n\n" + md(IT) +
                  "\n\n**Three-variable view: communication x penalty point x mode** (mean profit gain index with 95% CI over the 20 pairs; in brackets the count of games flagged collusive / games, n = 20 per cell):\n\n" + md(T3) +
                  "\n\n![wording x communication x mode](figures/sys_heat_wording_x_comm_x_mode.png)\n\nA wording x communication x mode view with n = 16 games per cell (4 pairs x 4 penalty points); finer cuts than this leave under 10 games per cell and are not shown.")

# ---------------------------------------------------------------- 7. words vs actions
WA = DONE[(DONE.arm_family.isin(["headline"])) & DONE.explicit_agreement_flag.notna()].copy()
wa_rows = []
for md_ in ["t0", "t1", "both"]:
    s0 = WA if md_ == "both" else WA[WA["mode"] == md_]
    for fl in [1.0, 0.0]:
        s = s0[s0.explicit_agreement_flag == fl]
        wa_rows.append({"mode": md_, "agreement flag": int(fl), "games": len(s), "profit gain index": f2(s.profit_gain_index.mean()),
                        "price index": f2(s.price_index.mean()), "competitive share": f2(s.competitive_share.mean()),
                        "share with price index >= 0.5": f2(s.high.mean()), "undercuts": f2(s.undercut_count.mean())})
WAT = pd.DataFrame(wa_rows); WAT.to_csv(f"{TAB}/sys_words_vs_actions_flag.csv", index=False)
ct = pd.crosstab(WA.explicit_agreement_flag.map({1.0: "agreement flag 1", 0.0: "agreement flag 0"}), WA.high.map({1.0: "price index >= 0.5", 0.0: "price index < 0.5"}))
ct.to_csv(f"{TAB}/sys_words_vs_actions_2x2.csv")
cls = DONE[DONE.arm_family == "headline"].groupby(["communication", "game_intent_class"]).agg(
    games=("row_id", "size"), pgi=("profit_gain_index", "mean"), price=("price_index", "mean"), high=("high", "mean"), comp=("competitive_share", "mean")).round(2).reset_index()
cls.to_csv(f"{TAB}/sys_words_vs_actions_intent_class.csv", index=False)
ap = WA[WA.agreement_precedes_high_price.notna()].groupby("agreement_precedes_high_price").agg(games=("row_id", "size"), pgi=("profit_gain_index", "mean")).round(2)
ct_txt = ct.to_string()
a_none = H[(H.communication == "tacit")]
# agreement in talk-with-no-flag games: fraction with any agreement but flag 0
anyv = WA.explicit_agreement_any.mean(); flagv = WA.explicit_agreement_flag.mean()
# correlation of explicit_round_share with pgi within chat games, by mode
rho_ers = {m_: chat[chat["mode"] == m_][["explicit_round_share", "profit_gain_index"]].corr(method="spearman").iloc[0, 1] for m_ in ["t0", "t1"]}
FR["words"] = (f"Games in the headline chat arms (private and monitored; n = {len(WA)}) cross-tabulated by the pre-declared agreement flag (`explicit_agreement_flag`: an agreement message sent by at least two firms) against behaviour:\n\n" + md(WAT) +
               f"\n\n2 x 2 (counts of games; 'high' = price index of 0.5 or more, a market price of 2.0 or more, an arbitrary line chosen for display):\n\n```\n{ct_txt}\n```\n\n"
               f"The flag is almost always 1 ({100*flagv:.0f}% of chat games, against {100*anyv:.0f}% with any agreement message), so the 0 group is small (n = {int((WA.explicit_agreement_flag == 0).sum())}). "
               f"Within chat games the Spearman correlation of the explicit-talk round share with the profit gain index is {rho_ers['t0']:+.2f} (thinking off) and {rho_ers['t1']:+.2f} (thinking on). "
               "Games by the intent class of their text, with the silent tacit arm shown as NO_TEXT:\n\n" + md(cls.rename(columns={"game_intent_class": "intent class", "pgi": "profit gain", "price": "price index", "high": "share high", "comp": "competitive share"})) +
               "\n\n**Caveat.** The agreement flag, the intent class and the explicit-talk shares are keyword rules; Step 1 check 14 (their validation) fails by design, so none of them is validated. The cross-tab shows co-occurrence of keywords and prices, not that the firms agreed, and a flag at 90% prevalence has little room to discriminate.")

# ---------------------------------------------------------------- 8. sensitivity (systematic)
def hm(df, col):
    return df.groupby(["communication", "mode"])[col].mean().unstack()
base = hm(H, "profit_gain_index")
long_ = hm(H[H.planned_length >= 19], "profit_gain_index")
clean = H[H.supersession == "none"]
c1 = hm(clean, "profit_gain_index")
imp = H[(H.imputed_round_share == 0) & (H.refusals == 0)]
c2 = hm(imp, "profit_gain_index")
sens = []
for c_ in COMM_ORDER:
    for md_ in ["t0", "t1"]:
        sens.append({"communication": c_, "mode": md_, "all-rounds (reported)": f2(base.loc[c_, md_]), "planned length 19 or 20 only": f2(long_.loc[c_, md_]),
                     "excluding rerun-flagged games": f2(c1.loc[c_, md_]), "no refusal or imputed round": f2(c2.loc[c_, md_]),
                     "n (all / no rerun / clean)": f"{len(H[(H.communication==c_)&(H['mode']==md_)])} / {len(clean[(clean.communication==c_)&(clean['mode']==md_)])} / {len(imp[(imp.communication==c_)&(imp['mode']==md_)])}"})
SE = pd.DataFrame(sens); SE.to_csv(f"{TAB}/sys_sensitivity_headline.csv", index=False)
# screening rank stability: eps ranking for pgi under price_index and w1_20? use cross-run correlation of factor-level means
OH = OTHER[(OTHER.status == "done") & (OTHER.arm_family == "headline")]
lm = []
for fac in ["communication", "penalty_point", "thinking", "wording", "planned_length"]:
    a = H.groupby(fac).profit_gain_index.mean(); b = OH.groupby(fac).profit_gain_index.mean()
    for lv in a.index:
        lm.append(dict(factor=fac, level=lv, this=a[lv], other=b[lv]))
LM = pd.DataFrame(lm); LM.to_csv(f"{TAB}/sys_cross_run_level_means.csv", index=False)
other_name = "neutral" if BATCH == "anchored" else "anchored"
rho_x = LM[["this", "other"]].corr(method="spearman").iloc[0, 1]
# which factor spans largest range, in each run
def rng_of(df, fac): g = df.groupby(fac).profit_gain_index.mean(); return g.max() - g.min()
cr = pd.DataFrame({"factor": [LEVELNAME[f] for f in LM.factor.unique()],
                   f"range of level means, {BATCH}": [f2(rng_of(H, f)) for f in LM.factor.unique()],
                   f"range of level means, {other_name}": [f2(rng_of(OH, f)) for f in LM.factor.unique()]})
# screening effect sizes in the other run (pooled stratum for pgi) cheap: Kruskal eps only
def eps_only(df, f, o):
    s = df[df[o].notna()]; r, t = ranks_tie(s[o].values); lv, lab = np.unique(s[f].values, return_inverse=True); return eps_from(r, t, lab, len(lv), len(s))
cr[f"root eps-sq, {BATCH}"] = [f2(eps_only(H, f, "profit_gain_index")) for f in LM.factor.unique()]
cr[f"root eps-sq, {other_name}"] = [f2(eps_only(OH, f, "profit_gain_index")) for f in LM.factor.unique()]
cr.to_csv(f"{TAB}/sys_cross_run_factor_ranges.csv", index=False)
FR["sens"] = ("Headline games, mean profit gain index by communication and mode under alternative choices (`tables/sys_sensitivity_headline.csv`):\n\n" + md(SE) +
              "\n\nOnly 51 of the 480 headline games reach round 20 (the window is complete for them and the rounds 1 to 20 index equals the all-round index), so a window comparison is replaced by the long-horizon seeds (planned length 19 or 20; n = 40 games per row). the third column drops the games that replaced a truncated original, or stand in for a missing rerun; the fourth drops games with any refusal or imputed round. Never-started rows are all 14B arms outside the queue, so best-case and worst-case imputation of failures does not apply to the headline.\n\n"
              f"**Same factors in the {other_name} run** (headline games; interim for the neutral side in the anchored report). Spearman correlation of the 17 factor-level means between the two runs: {rho_x:.2f}.\n\n" + md(cr))

json.dump(FR, open(f"{TAB}/sys_fragments.json", "w"), indent=1)
# console summary for the author
print(U.to_string()); print(R.round(2).to_string()); print(pt.to_string())
print(SCR[SCR.stratum == "pooled"].sort_values("eps_root", ascending=False).head(15).to_string())
print(IT.to_string()); print(SE.to_string()); print(cr.to_string()); print(WAT.to_string()); print(ct); print(cls.to_string())
print("seed sd", seed_sd, res_sd, sc_rows, sc_top)
print(surv_txt)
