"""Re-render the Step 2 systematic figures (figures/sys_*.png) with "slug: short label" ticks from the shared
glossary (tools/analysis_style/arm_labels.py). Labels and layout only: the drawing code and colour maps are those of
step2_systematic.py, whose statistics are NOT rerun (no permutation test, no bootstrap, no table is written).

Each plotted matrix is rebuilt the way step2_systematic.py builds it (plain means, Spearman correlations and the
bias-corrected Cramer's V of the neutral Step 1 run.csv, which is not committed: folder in the environment variable
ANALYSIS_FINAL_DIR, file steps/neutral/step1/run.csv) and asserted equal, to the 3 decimals kept, to the committed
table it was saved as (tables/sys_*.csv); the screening map is drawn from tables/sys_screening_lever_outcome.csv.
Usage: python -X utf8 replot_sys_figures.py [--orig]   (--orig = the old labels, to check that the data path
reproduces the committed PNGs byte for byte; writes to $REPLOT_OUT if set, else figures/)."""
import os
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import collusion_colors as CC  # noqa: E402
import arm_labels as AL  # noqa: E402

ORIG = "--orig" in sys.argv
FIG = str(Path(os.environ.get("REPLOT_OUT", HERE / "figures")))
TAB = HERE / "tables"
W = os.environ["ANALYSIS_FINAL_DIR"].rstrip("/") + "/"
NCHECK = [0]


def same(M, name):
    """assert a plotted matrix equals the committed table (rounded to 3 decimals, as saved)"""
    t = pd.read_csv(TAB / name, index_col=0)
    a = np.round(np.asarray(M, float), 3)
    b = t.values.astype(float)
    assert a.shape == b.shape and np.allclose(a, b, equal_nan=True, atol=1e-9), "plotted values differ from tables/" + name
    NCHECK[0] += a.size


KEYS = {}


def ticks(ax, codes, axis, name, **kw):
    """wrapped "code:" + short label ticks from the shared helper (numbered key if they would distort the chart)"""
    labs, key = CC.set_arm_ticks(ax, codes, axis, **kw)
    if key is not None:
        KEYS.setdefault(name, []).append((axis, key))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=130, bbox_inches="tight"); plt.close(fig)


def heat(ax, M, ann, cmap, vmin, vmax, xl, yl, title, cbar_label, fig, metric=None, col_metrics=None):
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
LEVELNAME = {"communication": "communication", "penalty_point": "penalty point", "thinking": "thinking",
             "wording": "wording", "seed": "seed", "planned_length": "planned length"}
GSLUG = {"evidence_end": "ended_by_evidence"}   # run.csv helper column -> glossary slug
FACTNAME = {"arm": "arm (grid arm slug)", "communication": "communication (tacit / private / monitored ...)",
            "penalty_point": "penalty_point (p1 to p5)", "thinking": "thinking (t0 off / t1 on)",
            "wording": "wording (w0 to w4)", "planned_length": "planned_length (L7 to L20)",
            "seed": "seed (s42 ... s273)", "firms": "firms (2 firms / 3 firms)"}


def mlab(c, wrap=None):
    """metric tick: 'slug: short label' (old: plain words)"""
    if ORIG:
        return PLAIN.get(c, c)
    t = AL.label(GSLUG.get(c, c))
    return textwrap.fill(t, wrap) if wrap else t


def code(slug, wrap=None):
    t = AL.label(slug)
    return textwrap.fill(t, wrap) if wrap else t


def load(b):
    d = pd.read_csv(f"{W}steps/{b}/step1/run.csv")
    d["evidence_end"] = np.where(d.end_reason.isna(), np.nan, (d.end_reason == "EVIDENCE").astype(float))
    d["mode"] = np.where(d.thinking == "on", "t1", "t0")
    return d


ALL = load("neutral")
DONE = ALL[ALL.status == "done"].copy()
H = DONE[DONE.arm_family == "headline"].copy()
COMM_ORDER = ["tacit", "private", "monitored"]
os.makedirs(FIG, exist_ok=True)


# ---- design association (bias-corrected Cramer's V)
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
same(V.values, "sys_design_association_cramers_v.csv")
fig, ax = plt.subplots(figsize=(5.6, 4.6) if ORIG else (6.8, 5.4), constrained_layout=not ORIG)
names = DF if ORIG else [FACTNAME[f] for f in DF]
heat(ax, V.values, [[f"{v:.2f}" for v in r] for r in V.values], "Blues", 0, 1, names, names,
     "Design factor association", "bias-corrected Cramer's V (0 to 1)", fig)
if ORIG:
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
else:
    ticks(ax, DF, "y", "sys_design_association.png"); ticks(ax, DF, "x", "sys_design_association.png")
save(fig, "sys_design_association.png")

# ---- correlation matrices
CO = ["price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length",
      "explicit_agreement_flag", "explicit_agreement_any", "collusive_game", "explicit_round_share", "strategic_round_share",
      "evidence_end", "rounds_played", "messages"]
CO = [c for c in CO if H[c].notna().sum() > 30 and H[c].nunique() > 1]
chat = H[H.communication != "tacit"]
R = H[CO].corr(method="spearman", min_periods=30); same(R.values, "sys_spearman_outcomes_headline.csv")
Rc = chat[CO].corr(method="spearman", min_periods=30); same(Rc.values, "sys_spearman_outcomes_chat_games.csv")
fig, axs = plt.subplots(1, 2, figsize=(16, 6.4) if ORIG else (17, 8), constrained_layout=not ORIG)
if ORIG:
    plt.subplots_adjust(wspace=0.6)
for ax, M, ttl in [(axs[0], R, f"All headline games (n={len(H)}; text columns use the {len(chat)} chat games)"), (axs[1], Rc, f"Chat games only (n={len(chat)})")]:
    names = [mlab(c) if ORIG else mlab(c, 40) for c in M.columns]
    heat(ax, M.values, [[f"{v:.2f}" for v in r] for r in M.values], CC.NEUTRAL_DIVERGING, -1, 1, names, names, ttl, "Spearman rank correlation", fig)
    if ORIG:
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    else:
        codes = [GSLUG.get(c, c) for c in M.columns]
        ticks(ax, codes, "y", "sys_corr_outcomes.png"); ticks(ax, codes, "x", "sys_corr_outcomes.png")
fig.suptitle("Outcome correlations (Spearman)", fontsize=11)
save(fig, "sys_corr_outcomes.png")
DS = DONE[DONE.score_mean.notna()]
SC = ["score_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length", "explicit_agreement_flag", "collusive_game"]
Rs = DS[SC].corr(method="spearman", min_periods=30); same(Rs.values, "sys_spearman_selfscore_dset.csv")
fig, ax = plt.subplots(figsize=(6.4, 5.4) if ORIG else (8.5, 6.8), constrained_layout=not ORIG)
names = [PLAIN.get(c, "self-score (D-set question)" if c == "score_mean" else c) for c in SC] if ORIG else [mlab(c) for c in SC]
heat(ax, Rs.values, [[f"{v:.2f}" for v in r] for r in Rs.values], CC.NEUTRAL_DIVERGING, -1, 1, names, names, f"Self-scores against behaviour (D-set arms, n={len(DS)})", "Spearman rank correlation", fig)
if ORIG:
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
else:
    ticks(ax, SC, "y", "sys_corr_selfscore_dset.png"); ticks(ax, SC, "x", "sys_corr_selfscore_dset.png")
save(fig, "sys_corr_selfscore_dset.png")

# ---- screening overview (from the committed table)
FACT = ["communication", "penalty_point", "thinking", "wording", "seed", "planned_length"]
SO = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "war_length", "evidence_end", "rounds_played", "collusive_game", "explicit_round_share"]
SCR = pd.read_csv(TAB / "sys_screening_lever_outcome.csv")
fig, axs = plt.subplots(1, 3, figsize=(19, 5.2) if ORIG else (20, 6.0), constrained_layout=not ORIG)
if ORIG:
    plt.subplots_adjust(wspace=0.45)
for ax, s_ in zip(axs, ["pooled", "t0", "t1"]):
    g = SCR[SCR.stratum == s_]; facs = [f for f in FACT if f in g.factor.unique()]
    M = np.full((len(facs), len(SO)), np.nan); A = [[""] * len(SO) for _ in facs]
    for i, f in enumerate(facs):
        for j, o in enumerate(SO):
            r_ = g[(g.factor == f) & (g.outcome == o)]
            if len(r_):
                r_ = r_.iloc[0]; M[i, j] = r_.eps_root; NCHECK[0] += 1
                A[i][j] = f"{r_.eps_root:.2f}" + ("*" if (not r_.by_construction and r_.bh_q < 0.05) else "") + ("m" if r_.by_construction else "")
    heat(ax, M, A, "Blues", 0, 0.7, [PLAIN.get(o, o) if ORIG else mlab(o) for o in SO], [LEVELNAME[f] for f in facs],
         {"pooled": "Both modes pooled", "t0": "Thinking off (t0)", "t1": "Thinking on (t1)"}[s_], "root epsilon-squared (0 to 1)", fig)
    if ORIG:
        plt.setp(ax.get_xticklabels(), rotation=50, ha="right")
    else:
        ticks(ax, [GSLUG.get(o, o) for o in SO], "x", "sys_screening_heatmap.png", grow=(s_ == "pooled"))
        ticks(ax, facs, "y", "sys_screening_heatmap.png", grow=(s_ == "pooled"))
fig.suptitle("Screening: which lever moves which outcome (headline games; * = permutation BH q < 0.05; m = by construction, excluded)", fontsize=10)
save(fig, "sys_screening_heatmap.png")

# ---- single-factor map
HM = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "evidence_end", "collusive_game", "explicit_agreement_flag"]
LVSLUG = {"communication": lambda v: v, "penalty_point": lambda v: "p%d" % v, "thinking": lambda v: {"off": "t0", "on": "t1"}[v],
          "wording": lambda v: "w%d" % v, "planned_length": lambda v: "L%d" % v}
rows, labs, nn, lvc, lvshort = [], [], [], [], {}
for fac, order in [("communication", COMM_ORDER), ("penalty_point", [1, 3, 4, 5]), ("thinking", ["off", "on"]), ("wording", [0, 1, 2, 3, 4]), ("planned_length", [7.0, 15.0, 19.0, 20.0])]:
    for lv in order:
        s = H[H[fac] == lv]; rows.append([s[c].mean() for c in HM]); nn.append(len(s))
        lvc.append(LVSLUG[fac](lv)); lvshort[LVSLUG[fac](lv)] = "%s, n=%d" % (AL.glossary()[LVSLUG[fac](lv)]["short_label"], len(s))
        labs.append(f"{LEVELNAME[fac]} = {int(lv) if isinstance(lv, float) else lv}" if ORIG else f"{LEVELNAME[fac]} = {code(LVSLUG[fac](lv))}")
M = np.array(rows); Mn = (M - np.nanmin(M, 0)) / (np.nanmax(M, 0) - np.nanmin(M, 0) + 1e-12)
same(np.column_stack([M, nn]), "sys_heat_single_factor.csv")
fig, ax = plt.subplots(figsize=(8.6, 8.4) if ORIG else (9.5, 9.0), constrained_layout=not ORIG)
A = [[("" if np.isnan(M[i, j]) else f"{M[i, j]:.2f}") for j in range(M.shape[1])] for i in range(M.shape[0])]
heat(ax, Mn, A, "Blues", 0, 1, [PLAIN[c] if ORIG else mlab(c, 26) for c in HM], [f"{l}  (n={n})" for l, n in zip(labs, nn)],
     "Single-factor maps: outcome by factor level", "column-normalised (0 = lowest level, 1 = highest)", fig, col_metrics=HM)
if ORIG:
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
else:
    ticks(ax, lvc, "y", "sys_heat_single_factor.png", short=lvshort)
    ticks(ax, [GSLUG.get(c, c) for c in HM], "x", "sys_heat_single_factor.png")
for yy in [2.5, 6.5, 8.5, 13.5]: ax.axhline(yy, color="white", lw=2)
save(fig, "sys_heat_single_factor.png")


# ---- communication x penalty per mode
def grid(df, rowv, colv, val, rows_, cols_):
    M = np.full((len(rows_), len(cols_)), np.nan); A = [[""] * len(cols_) for _ in rows_]; N = np.zeros_like(M)
    for i, r_ in enumerate(rows_):
        for j, c_ in enumerate(cols_):
            s = df[(df[rowv] == r_) & (df[colv] == c_)]
            if len(s) and s[val].notna().any():
                M[i, j] = s[val].mean(); N[i, j] = s[val].notna().sum(); A[i][j] = f"{M[i, j]:.2f}\n(n={int(N[i, j])})"
    return M, A, N


fig, axs = plt.subplots(2, 2, figsize=(12, 6.8) if ORIG else (12, 7.4), constrained_layout=not ORIG)
if ORIG:
    plt.subplots_adjust(wspace=0.4, hspace=0.3)
for r_, val in enumerate(["profit_gain_index", "competitive_share"]):
    for c_, md_ in enumerate(["t0", "t1"]):
        M, A, N = grid(H[H["mode"] == md_], "communication", "penalty_point", val, COMM_ORDER, [1, 3, 4, 5])
        same(M, f"sys_heat_comm_x_penalty_{val}_{md_}.csv")
        xl = ["p1", "p3", "p4", "p5"] if ORIG else [code(p, 16) for p in ["p1", "p3", "p4", "p5"]]
        yl = COMM_ORDER if ORIG else [code(c, 16) for c in COMM_ORDER]
        heat(axs[r_][c_], M, A, None, 0, 1, xl, yl, f"{PLAIN[val]}, thinking {'off' if md_ == 't0' else 'on'}", f"mean {PLAIN[val]} (0 to 1)", fig, metric=val)
        if not ORIG:
            first = (r_ == 0 and c_ == 0)
            ticks(axs[r_][c_], ["p1", "p3", "p4", "p5"], "x", "sys_heat_comm_x_penalty.png", grow=first,
                  short={p: AL.glossary()[p]["short_label"].split(": ", 1)[-1] for p in ["p1", "p3", "p4", "p5"]})
            ticks(axs[r_][c_], COMM_ORDER, "y", "sys_heat_comm_x_penalty.png", grow=first)
fig.suptitle("Communication by penalty point, per thinking mode", fontsize=10)
save(fig, "sys_heat_comm_x_penalty.png")

# ---- mode x arm (all done arms, in the order and with the families of tables/sys_univariate_by_arm_all_done.csv)
AT = pd.read_csv(TAB / "sys_univariate_by_arm_all_done.csv")
arms = list(AT.arm); fams = AT.set_index("arm").family
M = np.full((len(arms), 2), np.nan); A = [[""] * 2 for _ in arms]
for i, a in enumerate(arms):
    for j, md_ in enumerate(["t0", "t1"]):
        s = DONE[(DONE.arm == a) & (DONE["mode"] == md_)]
        if len(s): M[i, j] = s.profit_gain_index.mean(); A[i][j] = f"{M[i, j]:.2f} (n={len(s)})"
same(M, "sys_heat_arm_x_mode.csv")
fig, ax = plt.subplots(figsize=(5.4, 9.2) if ORIG else (5.6, 12.5), constrained_layout=not ORIG)
yl = [f"{a} [{fams[a]}]" for a in arms] if ORIG else [f"{code(a)} [{fams[a]}]" for a in arms]
xl = ["thinking off", "thinking on"] if ORIG else ["t0: thinking off", "t1: thinking on"]
heat(ax, M, A, None, 0, 1, xl, yl, "Mode by arm: mean profit gain, thinking off and on", "mean profit gain index (0 to 1)", fig, metric="profit_gain_index")
if not ORIG:
    ticks(ax, arms, "y", "sys_heat_arm_x_mode.png", short={a: "[%s] %s" % (fams[a], AL.glossary()[a]["short_label"]) for a in arms})
    ticks(ax, ["t0", "t1"], "x", "sys_heat_arm_x_mode.png")
save(fig, "sys_heat_arm_x_mode.png")

# ---- wording x seed
sw = H.groupby(["wording", "seed"]).planned_length.first().reset_index().sort_values(["wording", "planned_length"])
sw["k"] = sw.groupby("wording").cumcount()
fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.2) if ORIG else (14, 4.8), constrained_layout=not ORIG)
if ORIG:
    plt.subplots_adjust(wspace=0.4)
for ax, md_ in zip(axs, ["t0", "t1"]):
    M = np.full((5, 4), np.nan); A = [[""] * 4 for _ in range(5)]
    for _, r_ in sw.iterrows():
        s = H[(H.seed == r_.seed) & (H["mode"] == md_)]
        M[int(r_.wording), int(r_.k)] = s.profit_gain_index.mean()
        A[int(r_.wording)][int(r_.k)] = (f"{M[int(r_.wording), int(r_.k)]:.2f}\nseed {int(r_.seed)}, L{int(r_.planned_length)}" if ORIG
                                         else f"{M[int(r_.wording), int(r_.k)]:.2f}\ns{int(r_.seed)}, L{int(r_.planned_length)}")
    same(M, f"sys_heat_wording_x_seed_{md_}.csv")
    xl = ["shortest", "", "", "longest"] if ORIG else ["shortest seed\nof the wording", "2nd", "3rd", "longest seed\nof the wording"]
    yl = [f"wording {i}" for i in range(5)] if ORIG else [code("w%d" % i) for i in range(5)]
    heat(ax, M, A, None, 0, 1, xl, yl, f"thinking {'off' if md_ == 't0' else 'on'} (12 games per cell: 3 communication arms x 4 penalty points)", "mean profit gain index", fig, metric="profit_gain_index")
    if not ORIG:
        ticks(ax, ["w%d" % i for i in range(5)], "y", "sys_heat_wording_x_seed.png", grow=(md_ == "t0"))
fig.suptitle("Wording by seed: mean profit gain of each (wording, seed) pair" + ("" if ORIG else "; in each cell sN = seed N and LN = planned length N rounds"), fontsize=10)
save(fig, "sys_heat_wording_x_seed.png")

# ---- wording x communication x mode
fig, axs = plt.subplots(1, 2, figsize=(10, 4) if ORIG else (11.5, 4.6), constrained_layout=not ORIG)
if ORIG:
    plt.subplots_adjust(wspace=0.4)
for ax, md_ in zip(axs, ["t0", "t1"]):
    M, A, N = grid(H[H["mode"] == md_], "wording", "communication", "profit_gain_index", [0, 1, 2, 3, 4], COMM_ORDER)
    same(M, f"sys_heat_wording_x_comm_{md_}.csv")
    xl = COMM_ORDER if ORIG else [code(c, 16) for c in COMM_ORDER]
    yl = [f"wording {i}" for i in range(5)] if ORIG else [code("w%d" % i) for i in range(5)]
    heat(ax, M, A, None, 0, 1, xl, yl, f"thinking {'off' if md_ == 't0' else 'on'}", "mean profit gain index", fig, metric="profit_gain_index")
    if not ORIG:
        ticks(ax, ["w%d" % i for i in range(5)], "y", "sys_heat_wording_x_comm_x_mode.png", grow=(md_ == "t0"))
        ticks(ax, COMM_ORDER, "x", "sys_heat_wording_x_comm_x_mode.png", grow=(md_ == "t0"))
fig.suptitle("Wording x communication x mode (n = 16 games per cell, 4 pairs x 4 penalty points)", fontsize=10)
save(fig, "sys_heat_wording_x_comm_x_mode.png")
print("plotted values checked against the committed tables:", NCHECK[0])
print("numbered-key axes (pass row_key/col_key to axis_legend):", KEYS or "none")
