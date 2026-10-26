"""Re-render the anchored Step 2 figures with "slug: short label" tick and legend text (owner's labelling rule).

Labels and layout only: colours, colour scales, markers and plotted values are unchanged. Every plotted value comes
from the committed tables in tables/ or, for the systematic heat maps, from the same Step 1 run.csv that
step2_systematic.py reads (read-only); each recomputed matrix is asserted equal to its committed tables/sys_*.csv
before drawing. Nothing in tables/ is written. Labels come from tools/analysis_style/arm_glossary.csv (arm_labels).

The plotting code is copied from the scripts that drew the originals:
  sys_*.png                      step2_systematic.py (heat helper verbatim; tick text changed)
  fig1/2/3/4/5/6_*.png           the analysis pipeline's figures.py (fig_gain_vs_penalty, fig_comm, fig_thinking,
                                 fig_anchor, fig_controls, fig_dset)
  levers_anchored.png            levers.py (plot)
  channel_shift.png              channel_shift.py (figure)
  comp_fig1.png, comp_fig2.png   the competitiveness review's figs.py
Not re-rendered: detect_roc_anchored.png (its ROC points are not stored in any table; redrawing would rerun the
detectors). The outcome axes of sys_corr_outcomes.png, sys_corr_selfscore_dset.png and sys_heat_single_factor.png use
collusion_colors.set_arm_ticks (code on line 1, label wrapped at 26 characters, at most 3 lines, >= 9 pt).

Usage (from this folder): python -X utf8 rerender_figures.py RUN_CSV_DIR NEUTRAL_COMP_DIR
  RUN_CSV_DIR       folder holding the anchored Step 1 run.csv (not committed: it is too large)
  NEUTRAL_COMP_DIR  folder holding neutral_cells.csv and neutral_by_round.csv of the competitiveness review
"""
import os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "analysis_style"))
import collusion_colors as CC
import arm_labels

if len(sys.argv) < 3:
    sys.exit(__doc__)
RUN_DIR, NCOMP = sys.argv[1], sys.argv[2]
TAB, FIG = HERE / "tables", HERE / "figures"
CHECKS = []


def L(slug, wrap=None):
    s = arm_labels.label(slug)
    return arm_labels.labels([slug], wrap)[0] if wrap else s


def check(name, M, csv_df):
    """Assert the recomputed matrix (rounded as the committed CSV) equals the committed CSV."""
    a = np.round(np.asarray(M, float), 3); b = csv_df.values.astype(float)
    ok = a.shape == b.shape and np.allclose(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9), atol=1e-9)
    assert ok, f"{name}: recomputed values differ from the committed CSV"
    CHECKS.append(f"{name}: {a.size} values equal the committed CSV")


def same(name, plotted, source):
    a, b = np.asarray(plotted, float), np.asarray(source, float)
    assert a.shape == b.shape and np.allclose(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9)), name
    CHECKS.append(f"{name}: {a.size} plotted values equal the committed CSV")


# =============================================================== systematic heat maps (step2_systematic.py)
def heat(ax, M, ann, cmap, vmin, vmax, xl, yl, title, cbar_label, fig, xt=None, yt=None, metric=None, col_metrics=None, tfs=9):
    """Verbatim from step2_systematic.py except the tick font size argument (tfs)."""
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
    ax.set_xticks(range(len(xl))); ax.set_xticklabels(xl, fontsize=tfs, rotation=0)
    ax.set_yticks(range(len(yl))); ax.set_yticklabels(yl, fontsize=tfs)
    ax.set_title(title, fontsize=9)
    if xt: ax.set_xlabel(xt, fontsize=8)
    if yt: ax.set_ylabel(yt, fontsize=8)
    afs = CC.fit_annotations(fig, ax, M.shape[0], M.shape[1], [a_ for r_ in ann for a_ in r_])
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


def save_sys(fig, name):
    fig.savefig(FIG / name, dpi=130, bbox_inches="tight"); plt.close(fig)


PLAIN = {"price_index": "price index", "profit_gain_index": "profit gain index", "competitive_share": "competitive share",
         "matching_share": "matching share", "undercut_count": "undercuts", "war_length": "war length (rounds)",
         "evidence_end": "ended on evidence", "rounds_played": "rounds played", "collusive_game": "collusive game (flag)",
         "explicit_round_share": "explicit-talk round share", "messages": "messages",
         "explicit_agreement_flag": "explicit agreement (flag)", "explicit_agreement_any": "any agreement message",
         "strategic_round_share": "strategic-talk round share"}
COMM_ORDER = ["tacit", "private", "monitored"]
PCODE = {1: "p1", 3: "p3", 4: "p4", 5: "p5"}
TCODE = {"off": "t0", "on": "t1"}


def load_run():
    d = pd.read_csv(os.path.join(RUN_DIR, "run.csv"), low_memory=False)
    d["evidence_end"] = np.where(d.end_reason.isna(), np.nan, (d.end_reason == "EVIDENCE").astype(float))
    d["mode"] = np.where(d.thinking == "on", "t1", "t0")
    return d


def grid(df, rowv, colv, val, rows_, cols_):
    M = np.full((len(rows_), len(cols_)), np.nan); A = [[""] * len(cols_) for _ in rows_]; N = np.zeros_like(M)
    for i, r_ in enumerate(rows_):
        for j, c_ in enumerate(cols_):
            s = df[(df[rowv] == r_) & (df[colv] == c_)]
            if len(s) and s[val].notna().any():
                M[i, j] = s[val].mean(); N[i, j] = s[val].notna().sum(); A[i][j] = f"{M[i, j]:.2f}\n(n={int(N[i, j])})"
    return M, A, N


def cramer(x, y):
    t = pd.crosstab(x, y); n = t.values.sum()
    if min(t.shape) < 2: return 0.0
    e = np.outer(t.sum(axis=1), t.sum(axis=0)) / n
    chi2 = ((t.values - e) ** 2 / e).sum()
    phi2 = chi2 / n; r, k = t.shape
    phi2c = max(0, phi2 - (k - 1) * (r - 1) / (n - 1)); rc = r - (r - 1) ** 2 / (n - 1); kc = k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2c / max(1e-12, min(kc - 1, rc - 1))))


OSLUG = {"evidence_end": "ended_by_evidence"}   # run.csv column -> glossary slug


def OL(col, wrap):
    """'code: short label' tick for an outcome column (glossary slug)."""
    return arm_labels.labels([OSLUG.get(col, col)], wrap=wrap)[0]


KEYS = []


def TK(ax, cols, axis, fig_name, short=None, **kw):
    """Shared tick helper: code on line 1, label wrapped at 26 characters (max 3 lines, >= 9 pt), numbered-key fallback."""
    slugs = [OSLUG.get(c, c) for c in cols]
    _, key = CC.set_arm_ticks(ax, slugs, axis=axis, short=short, **kw)
    if key is not None:
        KEYS.append(f"{fig_name} {axis}-axis uses a numbered key: " + ", ".join(f"{i + 1} = {k}" for i, k in enumerate(key)))
    return key


def systematic():
    ALL = load_run(); DONE = ALL[ALL.status == "done"].copy(); H = DONE[DONE.arm_family == "headline"].copy()

    # outcome correlations (Spearman), as in step2_systematic.py section 3, with code: label ticks on both axes
    CO = ["price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length",
          "explicit_agreement_flag", "explicit_agreement_any", "collusive_game", "explicit_round_share", "strategic_round_share",
          "evidence_end", "rounds_played", "messages"]
    CO = [c for c in CO if H[c].notna().sum() > 30 and H[c].nunique() > 1]
    chat = H[H.communication != "tacit"]
    R = H[CO].corr(method="spearman", min_periods=30); Rc = chat[CO].corr(method="spearman", min_periods=30)
    check("sys_spearman_outcomes_headline", R.values, pd.read_csv(TAB / "sys_spearman_outcomes_headline.csv", index_col=0))
    check("sys_spearman_outcomes_chat_games", Rc.values, pd.read_csv(TAB / "sys_spearman_outcomes_chat_games.csv", index_col=0))
    fig, axs = plt.subplots(1, 2, figsize=(20, 9), constrained_layout=True)
    for ax, M, ttl in [(axs[0], R, f"All headline games (n={len(H)}; text columns use the {len(chat)} chat games)"), (axs[1], Rc, f"Chat games only (n={len(chat)})")]:
        heat(ax, M.values, [[f"{v:.2f}" for v in r] for r in M.values], CC.NEUTRAL_DIVERGING, -1, 1, list(M.columns), list(M.columns), ttl, "Spearman rank correlation", fig)
        TK(ax, list(M.columns), "y", "sys_corr_outcomes"); TK(ax, list(M.columns), "x", "sys_corr_outcomes")
    fig.suptitle("Outcome correlations (Spearman)", fontsize=11)
    save_sys(fig, "sys_corr_outcomes.png")

    # D-set self-scores against behaviour (step2_systematic.py section 3)
    DS = DONE[DONE.score_mean.notna()]
    SC = ["score_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share", "undercut_count", "war_length", "explicit_agreement_flag", "collusive_game"]
    Rs = DS[SC].corr(method="spearman", min_periods=30)
    check("sys_spearman_selfscore_dset", Rs.values, pd.read_csv(TAB / "sys_spearman_selfscore_dset.csv", index_col=0))
    fig, ax = plt.subplots(figsize=(8, 7), constrained_layout=True)
    heat(ax, Rs.values, [[f"{v:.2f}" for v in r] for r in Rs.values], CC.NEUTRAL_DIVERGING, -1, 1, SC, SC, f"Self-scores against behaviour (D-set arms, n={len(DS)})", "Spearman rank correlation", fig)
    TK(ax, SC, "y", "sys_corr_selfscore_dset"); TK(ax, SC, "x", "sys_corr_selfscore_dset")
    save_sys(fig, "sys_corr_selfscore_dset.png")

    # design association (Cramer's V)
    DF = ["arm", "communication", "penalty_point", "thinking", "wording", "planned_length", "seed", "firms"]
    Dd = DONE[DF].astype(str)
    V = pd.DataFrame([[cramer(Dd[a], Dd[b]) if a != b else 1.0 for b in DF] for a in DF], index=DF, columns=DF)
    check("sys_design_association", V.values, pd.read_csv(TAB / "sys_design_association_cramers_v.csv", index_col=0))
    fig, ax = plt.subplots(figsize=(8.4, 6.6), constrained_layout=True)
    heat(ax, V.values, [[f"{v:.2f}" for v in r] for r in V.values], "Blues", 0, 1, DF, DF,
         "Design factor association", "bias-corrected Cramer's V (0 to 1)", fig)
    TK(ax, DF, "y", "sys_design_association"); TK(ax, DF, "x", "sys_design_association")
    save_sys(fig, "sys_design_association.png")

    # screening heat map (values from the committed screening table: permutation p-values are random draws)
    SCR = pd.read_csv(TAB / "sys_screening_lever_outcome.csv")
    FACT = ["communication", "penalty_point", "thinking", "wording", "seed", "planned_length"]
    SO = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "war_length", "evidence_end", "rounds_played", "collusive_game", "explicit_round_share"]
    fig, axs = plt.subplots(1, 3, figsize=(22, 6.4), constrained_layout=True)
    n_scr = 0
    for ax, s_ in zip(axs, ["pooled", "t0", "t1"]):
        g = SCR[SCR.stratum == s_]; facs = [f for f in FACT if f in g.factor.unique()]
        M = np.full((len(facs), len(SO)), np.nan); A = [[""] * len(SO) for _ in facs]
        for i, f in enumerate(facs):
            for j, o in enumerate(SO):
                r_ = g[(g.factor == f) & (g.outcome == o)]
                if len(r_):
                    r_ = r_.iloc[0]; M[i, j] = r_.eps_root; n_scr += 1
                    A[i][j] = f"{r_.eps_root:.2f}" + ("*" if (not r_.by_construction and r_.bh_q < 0.05) else "") + ("m" if r_.by_construction else "")
        heat(ax, M, A, "Blues", 0, 0.7, [OL(o, None) for o in SO], arm_labels.labels(facs, wrap=22),
             {"pooled": "Both modes pooled", "t0": "Thinking off (t0)", "t1": "Thinking on (t1)"}[s_], "root epsilon-squared (effect size, 0 to 1; higher = factor explains more of the outcome)", fig,
             xt="outcome (game-level)", yt="design factor")
        TK(ax, facs, "y", "sys_screening_heatmap"); TK(ax, SO, "x", "sys_screening_heatmap")
    CHECKS.append(f"sys_screening_heatmap: {n_scr} cells read directly from the committed tables/sys_screening_lever_outcome.csv")
    fig.suptitle("Screening: which lever moves which outcome (headline games; * = permutation BH q < 0.05; m = by construction, excluded)", fontsize=10)
    save_sys(fig, "sys_screening_heatmap.png")

    # single-factor map
    HM = ["profit_gain_index", "price_index", "competitive_share", "matching_share", "undercut_count", "evidence_end", "collusive_game", "explicit_agreement_flag"]
    rows, labs, nn, codes = [], [], [], []
    G_ = arm_labels.glossary()
    for fac, order, code in [("communication", COMM_ORDER, lambda v: v), ("penalty_point", [1, 3, 4, 5], lambda v: PCODE[v]),
                             ("thinking", ["off", "on"], lambda v: TCODE[v]), ("wording", [0, 1, 2, 3, 4], lambda v: f"w{v}"),
                             ("planned_length", [7.0, 15.0, 19.0, 20.0], lambda v: f"L{int(v)}")]:
        for lv in order:
            s = H[H[fac] == lv]; rows.append([s[c].mean() for c in HM]); nn.append(len(s)); labs.append(L(code(lv))); codes.append(code(lv))
    M = np.array(rows); Mn = (M - np.nanmin(M, 0)) / (np.nanmax(M, 0) - np.nanmin(M, 0) + 1e-12)
    csv = pd.read_csv(TAB / "sys_heat_single_factor.csv", index_col=0)
    check("sys_heat_single_factor", np.column_stack([M, nn]), csv)
    fig, ax = plt.subplots(figsize=(10.6, 8.4), constrained_layout=True)
    A = [[("" if np.isnan(M[i, j]) else f"{M[i, j]:.2f}") for j in range(M.shape[1])] for i in range(M.shape[0])]
    heat(ax, Mn, A, "Blues", 0, 1, [PLAIN[c] for c in HM], [f"{l}  (n={n})" for l, n in zip(labs, nn)],
         "Single-factor maps: outcome by factor level (number printed = raw mean; colour = column-normalised)", "column-normalised (0 = lowest level, 1 = highest)", fig,
         xt="outcome (game-level; headline games, n = 480)",
         yt="factor level, as slug: short label (blocks: communication, penalty point, thinking, wording, planned length; n = games)", col_metrics=HM)
    TK(ax, HM, "x", "sys_heat_single_factor")
    TK(ax, codes, "y", "sys_heat_single_factor", short={c_: f"{G_[c_]['short_label']} (n={n_})" for c_, n_ in zip(codes, nn)})
    for yy in [2.5, 6.5, 8.5, 13.5]: ax.axhline(yy, color="white", lw=2)
    save_sys(fig, "sys_heat_single_factor.png")

    # communication x penalty per mode
    fig, axs = plt.subplots(2, 2, figsize=(14, 7.6), constrained_layout=True)
    for r_, val in enumerate(["profit_gain_index", "competitive_share"]):
        for c_, md_ in enumerate(["t0", "t1"]):
            M, A, N = grid(H[H["mode"] == md_], "communication", "penalty_point", val, COMM_ORDER, [1, 3, 4, 5])
            check(f"sys_heat_comm_x_penalty_{val}_{md_}", M, pd.read_csv(TAB / f"sys_heat_comm_x_penalty_{val}_{md_}.csv", index_col=0))
            heat(axs[r_][c_], M, A, None, 0, 1, arm_labels.labels(["p1", "p3", "p4", "p5"], wrap=14), arm_labels.labels(COMM_ORDER, wrap=16),
                 f"{PLAIN[val]}, {L(md_)}", f"mean {PLAIN[val]} (0 to 1)", fig,
                 xt="penalty point (1 = collusion clearly pays, 5 = clearly does not)", yt="communication", metric=val)
            TK(axs[r_][c_], COMM_ORDER, "y", "sys_heat_comm_x_penalty"); TK(axs[r_][c_], ["p1", "p3", "p4", "p5"], "x", "sys_heat_comm_x_penalty")
    fig.suptitle("Communication by penalty point, per thinking mode (each cell = mean of the 20 games, one per (wording, seed) pair)", fontsize=10)
    save_sys(fig, "sys_heat_comm_x_penalty.png")

    # mode x arm
    csv = pd.read_csv(TAB / "sys_heat_arm_x_mode.csv", index_col=0)
    arms = list(csv.index); fams = DONE.groupby("arm").arm_family.first()
    M = np.full((len(arms), 2), np.nan); A = [[""] * 2 for _ in arms]
    for i, a in enumerate(arms):
        for j, md_ in enumerate(["t0", "t1"]):
            s = DONE[(DONE.arm == a) & (DONE["mode"] == md_)]
            if len(s): M[i, j] = s.profit_gain_index.mean(); A[i][j] = f"{M[i, j]:.2f} (n={len(s)})"
    check("sys_heat_arm_x_mode", M, csv)
    fig, ax = plt.subplots(figsize=(9.6, 10.4), constrained_layout=True)
    heat(ax, M, A, None, 0, 1, [L("t0"), L("t1")], [f"{L(a)}  [{fams[a]}]" for a in arms],
         "Mode by arm: mean profit gain index, thinking off and on (blank = arm not run in that mode)", "mean profit gain index (0 to 1)", fig,
         xt="thinking mode", yt="arm (slug: short label) [arm family]", metric="profit_gain_index")
    G_ = arm_labels.glossary()
    TK(ax, arms, "y", "sys_heat_arm_x_mode", short={a: f"{G_[a]['short_label']} [{fams[a]}]" for a in arms}, wrap=46, max_lines=2); TK(ax, ["t0", "t1"], "x", "sys_heat_arm_x_mode")
    save_sys(fig, "sys_heat_arm_x_mode.png")

    # wording x seed
    sw = H.groupby(["wording", "seed"]).planned_length.first().reset_index().sort_values(["wording", "planned_length"])
    sw["k"] = sw.groupby("wording").cumcount()
    lens = sw.groupby("k").planned_length.unique()
    assert all(len(v) == 1 for v in lens), "planned length differs within a seed rank"
    xl = [arm_labels.labels([f"L{int(lens[k][0])}"], wrap=13)[0] + ("\n(shortest)" if k == 0 else "\n(longest)" if k == 3 else "") for k in range(4)]
    fig, axs = plt.subplots(1, 2, figsize=(16.5, 5.2), constrained_layout=True)
    for ax, md_ in zip(axs, ["t0", "t1"]):
        M = np.full((5, 4), np.nan); A = [[""] * 4 for _ in range(5)]
        for _, r_ in sw.iterrows():
            s = H[(H.seed == r_.seed) & (H["mode"] == md_)]
            M[int(r_.wording), int(r_.k)] = s.profit_gain_index.mean()
            A[int(r_.wording)][int(r_.k)] = f"{M[int(r_.wording), int(r_.k)]:.2f}\nseed {int(r_.seed)}, L{int(r_.planned_length)}"
        check(f"sys_heat_wording_x_seed_{md_}", M, pd.read_csv(TAB / f"sys_heat_wording_x_seed_{md_}.csv", index_col=0))
        heat(ax, M, A, None, 0, 1, xl, [L(f"w{i}") + f"\n(wording {i})" for i in range(5)], f"{L(md_)} (12 games per cell)", "mean profit gain index", fig,
             xt="seed within wording, ordered by planned length (shortest to longest; L = planned rounds)", yt="prompt wording", metric="profit_gain_index")
        G_ = arm_labels.glossary()
        TK(ax, [f"w{i}" for i in range(5)], "y", "sys_heat_wording_x_seed")
        TK(ax, [f"L{int(lens[k][0])}" for k in range(4)], "x", "sys_heat_wording_x_seed", rotation=0)
        ax.set_ylabel("prompt wording (w0 to w4 = wording 0 to 4)", fontsize=8)
    fig.suptitle("Wording by seed: mean profit gain of each (wording, seed) pair", fontsize=10)
    save_sys(fig, "sys_heat_wording_x_seed.png")

    # wording x communication x mode
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 4.8), constrained_layout=True)
    for ax, md_ in zip(axs, ["t0", "t1"]):
        M, A, N = grid(H[H["mode"] == md_], "wording", "communication", "profit_gain_index", [0, 1, 2, 3, 4], COMM_ORDER)
        check(f"sys_heat_wording_x_comm_{md_}", M, pd.read_csv(TAB / f"sys_heat_wording_x_comm_{md_}.csv", index_col=0))
        heat(ax, M, A, None, 0, 1, arm_labels.labels(COMM_ORDER, wrap=16), [L(f"w{i}") + f"\n(wording {i})" for i in range(5)], L(md_), "mean profit gain index", fig,
             xt="communication", yt="prompt wording", metric="profit_gain_index")
        G_ = arm_labels.glossary()
        TK(ax, [f"w{i}" for i in range(5)], "y", "sys_heat_wording_x_comm_x_mode")
        TK(ax, COMM_ORDER, "x", "sys_heat_wording_x_comm_x_mode", rotation=0)
        ax.set_ylabel("prompt wording (w0 to w4 = wording 0 to 4)", fontsize=8)
    fig.suptitle("Wording x communication x mode (n = 16 games per cell, 4 pairs x 4 penalty points)", fontsize=10)
    save_sys(fig, "sys_heat_wording_x_comm_x_mode.png")


# =============================================================== pipeline figures (figures.py)
COL = {"tacit": "#0072B2", "chat": "#D55E00", "monitored": "#009E73", "theory": "#000000", "bot": "#7f7f7f", "neutral": "#CC79A7", "anchored": "#E69F00"}
MODE_LAB = {"t0": "thinking off", "t1": "thinking on"}
INK, GRID = "#222222", "#dddddd"
PIPE_RC = {"font.size": 10, "axes.edgecolor": "#888", "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
           "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
           "figure.dpi": 110, "savefig.dpi": 150, "legend.frameon": False}


def _save(fig, path):
    try:
        fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    except Exception:
        pass
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def pipeline_figs():
    run = "anchored"
    cells = pd.read_csv(TAB / "a_cells_vs_theory_and_bot.csv")
    comm = pd.read_csv(TAB / "c_communication_contrasts.csv")
    anchor = pd.read_csv(TAB / "e_anchoring_neutral_minus_anchored.csv")
    dist = pd.read_csv(TAB / "g_dset_score_distribution.csv")
    beh = pd.read_csv(TAB / "g_dset_behaviour.csv")
    with plt.rc_context(PIPE_RC):
        # fig1: gain vs penalty
        c = cells[(cells.run == run) & (cells.metric == "gain_all") & cells.arm.str.startswith("headline-")]
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
        pl = []
        for ax, mode in zip(axes, ["t0", "t1"]):
            x = c[c["mode"] == mode]
            for k, cm in enumerate(["tacit", "chat", "monitored"]):
                d = x[x.comm == cm].sort_values("penalty_point")
                off = (k - 1) * 0.08
                ax.errorbar(d.penalty_point + off, d.est, yerr=[d.est - d.lo, d.hi - d.est], color=COL[cm], marker="o", ms=5, lw=1.6, capsize=3,
                            label=L(cm) if d.arm.iloc[0] in L(cm) else f"{L(cm)} (arm {d.arm.iloc[0]})")
                pl.append(d[["est", "lo", "hi"]].values)
            t = x.drop_duplicates("penalty_point").sort_values("penalty_point")
            ax.plot(t.penalty_point, t.theory, color=COL["theory"], ls="--", lw=1.4, marker="s", ms=4, label="theory (sustainable collusion)")
            ax.plot(t.penalty_point, t.bot, color=COL["bot"], ls=":", lw=1.8, label="scripted slow-undercutter bot")
            ax.axhline(0, color="#aa0000", lw=0.8)
            ax.text(5.05, 0.01, "competitive (price 1.00)", color="#aa0000", fontsize=8, ha="right", va="bottom")
            ax.set_title("%s  (n = %d to %d games per point)" % (L(mode), x.n_pairs.min(), x.n_pairs.max()), fontsize=10)
            ax.set_xlabel("penalty point (higher = heavier fine)")
            ax.set_xticks([1, 3, 4, 5]); ax.set_xticklabels(arm_labels.labels(["p1", "p3", "p4", "p5"], wrap=16), fontsize=9)
        same("fig1", np.concatenate(pl), c.sort_values(["mode", "comm", "penalty_point"]).pipe(
            lambda z: pd.concat([z[(z["mode"] == m) & (z.comm == cm)] for m in ["t0", "t1"] for cm in ["tacit", "chat", "monitored"]]))[["est", "lo", "hi"]].values)
        axes[0].set_ylabel("profit gain index (0 = competitive, 1 = monopoly profit)")
        h_, l_ = axes[0].get_legend_handles_labels(); fig.legend(h_, l_, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3)
        fig.suptitle("Collusion vs penalty, %s prompt examples; bars = 95%% CI over (wording, seed) pairs" % run, fontsize=11)
        _save(fig, FIG / "fig1_gain_vs_penalty_anchored.png")

        # fig2: communication contrasts
        cc = comm[(comm.run == run) & (comm.metric == "gain_all") & (comm.penalty_point == "pooled") & comm["mode"].isin(["t0", "t1", "both"])]
        fig, ax = plt.subplots(figsize=(9.5, 4.6))
        order = [("chat minus tacit", "chat", "tacit"), ("monitored minus tacit", "monitored", "tacit"), ("chat minus monitored", "chat", "monitored")]
        pv, sv = [], []
        for i, (ct, a_, b_) in enumerate(order):
            for j, mode in enumerate(["t0", "t1", "both"]):
                d = cc[(cc.contrast == ct) & (cc["mode"] == mode)].iloc[0]
                y = i + (1 - j) * 0.25
                color = ["#56B4E9", "#E69F00", "#444444"][j]
                ax.errorbar(d.est, y, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", color=color, capsize=3,
                            label={"t0": L("t0"), "t1": L("t1"), "both": "both modes"}[mode] if i == 0 else None)
                pv.append([d.est, d.lo, d.hi]); sv.append(cc[(cc.contrast == ct) & (cc["mode"] == mode)][["est", "lo", "hi"]].values[0])
        same("fig2", pv, sv)
        ax.axvline(0, color="#444", lw=0.8)
        ax.set_yticks(range(3)); ax.set_yticklabels([f"{L(a_)}\nminus\n{L(b_)}" for _, a_, b_ in order], fontsize=9)
        ax.set_xlabel("difference in profit gain index (average over penalty points 1,3,4,5; paired on wording x seed)")
        ax.legend(fontsize=8)
        ax.set_title("Communication contrasts, %s run" % run, fontsize=10)
        _save(fig, FIG / "fig2_communication_anchored.png")

        # fig3: thinking off vs on per cell
        fig, ax = plt.subplots(figsize=(12.5, 5.2))
        k, pv, sv = 0, [], []
        for cm in ["tacit", "chat", "monitored"]:
            for p in [1, 3, 4, 5]:
                o = c[(c.comm == cm) & (c.penalty_point == p) & (c["mode"] == "t0")].iloc[0]
                n = c[(c.comm == cm) & (c.penalty_point == p) & (c["mode"] == "t1")].iloc[0]
                ax.plot([k, k], [o.est, n.est], color=COL[cm], lw=1.5, alpha=0.7)
                ax.errorbar(k, o.est, yerr=[[o.est - o.lo], [o.hi - o.est]], fmt="o", mfc="white", color=COL[cm], capsize=2)
                ax.errorbar(k, n.est, yerr=[[n.est - n.lo], [n.hi - n.est]], fmt="o", color=COL[cm], capsize=2)
                pv += [[o.est, o.lo, o.hi], [n.est, n.lo, n.hi]]; k += 1
        sv = [c[(c.comm == cm) & (c.penalty_point == p) & (c["mode"] == m)][["est", "lo", "hi"]].values[0]
              for cm in ["tacit", "chat", "monitored"] for p in [1, 3, 4, 5] for m in ["t0", "t1"]]
        same("fig3", pv, sv)
        TK(ax, [f"p{p}" for p in [1, 3, 4, 5]] * 3, "x", "fig3_thinking_pairs_anchored")
        ax.set_xlim(-0.6, 11.6)
        for i, cm in enumerate(["tacit", "chat", "monitored"]):
            ax.text(1.5 + 4 * i, 1.01, L(cm), transform=ax.get_xaxis_transform(), ha="center", va="bottom", color=COL[cm], fontsize=10, fontweight="bold")
        ax.set_ylabel("profit gain index")
        ax.plot([], [], "o", mfc="white", color="#444", label=L("t0"))
        ax.plot([], [], "o", color="#444", label=L("t1"))
        ax.legend(fontsize=8)
        ax.set_title("Thinking off (open) vs on (filled), %s run; 95%% CI per point" % run, fontsize=10, pad=22)
        _save(fig, FIG / "fig3_thinking_pairs_anchored.png")

        # fig4: anchoring
        a = anchor[anchor.arm.str.startswith("pooled") & (anchor.penalty_point == "pooled over 1,3,4,5")]
        metrics = [("gain_all", "profit gain index"), ("share_2.09", "share of quotes at 2.09"), ("share_2.50", "share of quotes at 2.50"), ("share_anchored_set", "share on 1.54/2.09/3.00")]
        fig, axes = plt.subplots(1, len(metrics), figsize=(14, 4.0))
        pv, sv = [], []
        for ax, (m, title) in zip(axes, metrics):
            x = a[a.metric == m]
            for i, g in enumerate(["pooled headline-all", "pooled tacit", "pooled chat", "pooled monitored"]):
                for j, mode in enumerate(["t0", "t1"]):
                    d = x[(x.arm == g) & (x["mode"] == mode)].iloc[0]
                    ax.errorbar(d.est, i + (j - 0.5) * 0.3, xerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None,
                                color=["#0072B2", "#D55E00"][j], capsize=2, label=L(mode) if i == 0 else None)
                    pv.append([d.est, d.lo, d.hi]); sv.append(x[(x.arm == g) & (x["mode"] == mode)][["est", "lo", "hi"]].values[0])
            ax.axvline(0, color="#444", lw=0.8)
            ax.set_yticks(range(4))
            ax.set_yticklabels(["all headline arms"] + arm_labels.labels(["tacit", "chat", "monitored"], wrap=18) if ax is axes[0] else [], fontsize=9)
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("neutral minus anchored")
        same("fig4", pv, sv)
        axes[0].legend(fontsize=8)
        fig.suptitle("Anchoring effect: neutral-example run minus anchored-example run (paired on arm, point, wording, seed, mode)", fontsize=10)
        _save(fig, FIG / "fig4_anchoring.png")

        # fig5: controls
        cs = cells[(cells.run == run) & (cells.metric == "gain_all") & cells.arm.isin(["ctl-32b-compete", "ctl-32b-joint"]) | ((cells.run == run) & (cells.metric == "gain_all") & (cells.arm == "headline-chat") & (cells.penalty_point == 3))]
        fig, ax = plt.subplots(figsize=(8, 4.4))
        names = [("ctl-32b-compete", "negative control"), ("headline-chat", "headline chat p3"), ("ctl-32b-joint", "positive control")]
        pv, sv = [], []
        for i, (arm, _) in enumerate(names):
            for j, mode in enumerate(["t0", "t1"]):
                d = cs[(cs.arm == arm) & (cs["mode"] == mode)].iloc[0]
                ax.errorbar(i + (j - 0.5) * 0.2, d.est, yerr=[[d.est - d.lo], [d.hi - d.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00",
                            capsize=3, label=L(mode) if i == 0 else None)
                pv.append([d.est, d.lo, d.hi]); sv.append(cs[(cs.arm == arm) & (cs["mode"] == mode)][["est", "lo", "hi"]].values[0])
        same("fig5", pv, sv)
        ax.set_xticks(range(3)); ax.set_xlim(-.5, 2.5)
        ax.set_xticklabels([f"{n_}\n" + L(a_, 26) + ("\n(at p3)" if a_ == "headline-chat" else "") for a_, n_ in names], fontsize=9)
        ax.set_ylabel("profit gain index"); ax.set_ylim(-0.05, 1.05)
        ax.legend(fontsize=8)
        ax.set_title("Controls, %s run" % run, fontsize=10)
        _save(fig, FIG / "fig5_controls_anchored.png")

        # fig6: D set
        fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
        d = dist[dist.run == run]
        arms = list(d.arm.unique())
        w = 0.8 / 5
        pv = []
        for v in range(1, 6):
            ys = []
            for a_ in arms:
                x = d[(d.arm == a_) & (d.score == v)]
                ys.append(x.n_firm_rounds.sum() / max(d[(d.arm == a_)].groupby("score").n_firm_rounds.sum().sum(), 1))
            pv.append(ys)
            axes[0].bar(np.arange(len(arms)) + (v - 3) * w, ys, w * 0.9, label="score %d" % v, color=["#f0e442", "#e69f00", "#d55e00", "#cc79a7", "#0072b2"][v - 1], edgecolor="white")
        CHECKS.append(f"fig6 left: {np.size(pv)} bar heights computed from the committed g_dset_score_distribution.csv as in figures.py")
        TK(axes[0], arms, "x", "fig6_dset_anchored")
        axes[0].set_ylabel("share of answers (both modes)")
        axes[0].legend(fontsize=7, ncol=5, loc="upper center")
        axes[0].set_title("Self-rated scores (1-5) by D-set arm", fontsize=10)
        b = beh[(beh.run == run) & (beh.metric == "gain_all")]
        arms2 = sorted(b.arm.unique()); pv, sv = [], []
        for i, a_ in enumerate(arms2):
            for j, mode in enumerate(["t0", "t1"]):
                x = b[(b.arm == a_) & (b["mode"] == mode)]
                if x.empty or not np.isfinite(x.iloc[0].lo):
                    continue
                x = x.iloc[0]
                axes[1].errorbar(x.est, i + (j - 0.5) * 0.25, xerr=[[x.est - x.lo], [x.hi - x.est]], fmt="o", mfc="white" if j == 0 else None, color="#0072B2" if j == 0 else "#D55E00",
                                 capsize=2, label=L(mode) if i == 0 else None)
                pv.append([x.est, x.lo, x.hi])
        sv = b.dropna(subset=["lo"]).sort_values(["arm", "mode"])[["est", "lo", "hi"]].values
        same("fig6 right", pv, sv)
        TK(axes[1], arms2, "y", "fig6_dset_anchored")
        axes[1].axvline(0, color="#444", lw=0.8)
        axes[1].legend(fontsize=8)
        axes[1].set_xlabel("profit gain: D arm minus headline-chat p1 (paired)")
        axes[1].set_title("Behaviour vs the shared control", fontsize=10)
        _save(fig, FIG / "fig6_dset_anchored.png")


# =============================================================== lever forest (levers.py plot)
def levers():
    df = pd.read_csv(TAB / "levers_anchored.csv")
    d = df[~df.id.str.startswith(("tacit_p", "monitored_p")) & df["diff"].notna()]
    order = (d[d.outcome == "price_index"].groupby("id").removes_collusion.mean().sort_values(ascending=False).index.tolist())
    fig, axes = plt.subplots(1, 2, figsize=(18, 1.15 * len(order) + 2.6), sharey=True)
    col = {"off": "#1f77b4", "on": "#d95f02"}; off = {"off": -0.16, "on": 0.16}
    titles = {"price_index": "Price index  (arm - control)\nleft = less collusion", "comp_share": "Competitive share of rounds  (arm - control)\nright = less collusion"}
    pv, sv = [], []
    for ax, out in zip(axes, ("price_index", "comp_share")):
        for i, cid in enumerate(order):
            for mode in ("off", "on"):
                s = d[(d.id == cid) & (d.outcome == out) & (d["mode"] == mode)]
                if s.empty: continue
                s = s.iloc[0]; y = i + off[mode]; ex = s.tier == "E"
                ax.plot([s.ci_lo, s.ci_hi], [y, y], color=col[mode], lw=1.8, solid_capstyle="butt")
                ax.plot(s["diff"], y, "o", ms=7, mfc="white" if ex else col[mode], mec=col[mode], mew=1.6)
                pv.append([s["diff"], s.ci_lo, s.ci_hi])
        ax.axvline(0, color="#444", lw=1, ls="--"); ax.set_title(titles[out], fontsize=10); ax.grid(axis="x", alpha=.25)
        ax.set_ylim(len(order) - 0.4, -0.6)
    sv = [d[(d.id == cid) & (d.outcome == out) & (d["mode"] == m)][["diff", "ci_lo", "ci_hi"]].values[0]
          for out in ("price_index", "comp_share") for cid in order for m in ("off", "on") if len(d[(d.id == cid) & (d.outcome == out) & (d["mode"] == m)])]
    same("levers_anchored", pv, sv)
    ylabels = []
    for cid in order:
        r = d[d.id == cid].iloc[0]; n = d[d.id == cid].groupby("mode").n_pairs.first()
        ylabels.append(f"{r.label}\n{L(r.arm)} (p{int(r.point)})\nvs {L(r.control)} (p{int(r.control_point)})\n"
                       f"[{'pre-declared' if r.tier == 'H' else 'exploratory'}; cost {r.cost_tier}; n={'/'.join(f'{m}:{v}' for m, v in n.items())}]")
    axes[0].set_yticks(range(len(order))); axes[0].set_yticklabels(ylabels, fontsize=9)
    h = [Line2D([], [], color=col["off"], marker="o", label="thinking off (t0)"), Line2D([], [], color=col["on"], marker="o", label="thinking on (t1)"),
         Line2D([], [], color="k", marker="o", mfc="k", ls="", label="pre-declared"), Line2D([], [], color="k", marker="o", mfc="white", ls="", label="exploratory (Holm in levers.csv)")]
    axes[1].legend(handles=h, loc="lower right", fontsize=8, framealpha=.9)
    fig.suptitle("Which restriction removes the most collusion? Arm minus matched control, paired on (wording, seed) - anchored run\n"
                 "95% percentile bootstrap CI, 10,000 resamples of the pairs; sorted by mean price-index reduction; n = pairs per mode", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(FIG / "levers_anchored.png", dpi=150, bbox_inches="tight"); plt.close(fig)


# =============================================================== channel shift (channel_shift.py figure)
def channel_shift():
    R = pd.read_csv(TAB / "channel_shift_results.csv")
    cells = R.drop_duplicates(["comparison", "thinking"])[["comparison", "thinking"]].values.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(15, 14), sharey=True)
    pv, sv = [], []
    for ax, (m, t) in zip(axes, [("price_named", "Messages: share of talk naming a price >= 1.30"),
                                 ("silent_lock", "Actions: silent-lock share of rounds")]):
        for i, (c, th) in enumerate(cells):
            r = R[(R.comparison == c) & (R.thinking == th) & (R.measure == m)].iloc[0]
            col = "#1f77b4" if th == "off" else "#d95f02"
            ax.errorbar(r.delta, i, xerr=[[r.delta - r.ci_lo], [r.ci_hi - r.delta]], fmt="o", color=col, capsize=3)
            pv.append([r.delta, r.ci_lo, r.ci_hi])
        ax.axvline(0, color="grey", lw=1); ax.set_title(t, fontsize=9)
        ax.set_xlabel("paired difference, arm minus control (95% CI)")
    sv = [R[(R.comparison == c) & (R.thinking == th) & (R.measure == m)][["delta", "ci_lo", "ci_hi"]].values[0]
          for m in ("price_named", "silent_lock") for c, th in cells]
    same("channel_shift", pv, sv)
    labs = []
    for c, th in cells:
        r = R[(R.comparison == c) & (R.thinking == th)].iloc[0]
        tl = L(TCODE[th])
        if "reverse" in c:
            labs.append(f"{L(r.control)}\nminus {L(r.arm)}, p{int(r.point)}\n(reversed row) [{tl}]")
        else:
            labs.append(f"{L(r.arm)}\nvs {L(r.control)}, p{int(r.point)} [{tl}]")
    axes[0].set_yticks(range(len(cells))); axes[0].set_yticklabels(labs, fontsize=9)
    axes[0].invert_yaxis()
    fig.suptitle("SHIFT = left panel below 0 and right panel above 0 (blue: thinking off, orange: thinking on)", fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / "channel_shift.png", dpi=130, bbox_inches="tight"); plt.close(fig)


# =============================================================== competitiveness figures (figs.py)
def competitiveness():
    COLc = {"tacit": "#c0504d", "chat": "#2e75b6", "monitored": "#6a994e"}
    src = {"neutral": Path(NCOMP), "anchored": TAB}
    fig, axes = plt.subplots(2, 1, figsize=(15, 10.5), sharey=True)
    for ax, run in zip(axes, ["neutral", "anchored"]):
        d = pd.read_csv(src[run] / f"{run}_cells.csv")
        x = 0; ticks, labs, pv, sv = [], [], [], []
        for c in ["tacit", "chat", "monitored"]:
            for p in ["p1", "p3", "p4", "p5"]:
                for th, off, mk in [("t0", -0.17, "o"), ("t1", 0.17, "s")]:
                    r = d[(d.comm == c) & (d.pen == p) & (d.think == th)].iloc[0]
                    ax.errorbar(x + off, r.comp_share * 100, yerr=[[(r.comp_share - r.ci_lo) * 100], [(r.ci_hi - r.comp_share) * 100]],
                                fmt=mk, color=COLc[c], mfc=COLc[c] if th == "t1" else "white", capsize=2, ms=6)
                    pv.append([r.comp_share, r.ci_lo, r.ci_hi]); sv.append(d[(d.comm == c) & (d.pen == p) & (d.think == th)][["comp_share", "ci_lo", "ci_hi"]].values[0])
                ticks.append(x); labs.append(p); x += 1
            x += 0.7
        same(f"comp_fig1 {run}", pv, sv)
        ax.set_xticks(ticks); ax.set_xticklabels(CC.arm_tick_labels(labs, wrap=13, max_lines=4), fontsize=9)
        for i, c in enumerate(["tacit", "chat", "monitored"]):
            ax.text(1.5 + i * 4.7, -0.32, L(c), transform=ax.get_xaxis_transform(), ha="center", va="top", color=COLc[c], fontsize=10, fontweight="bold")
        ax.set_title(f"{run} run" + (" (primary)" if run == "neutral" else ""))
        ax.grid(axis="y", alpha=.3); ax.set_ylim(0, 75)
    for ax in axes: ax.set_ylabel("% of firm-rounds competitive (95% CI)")
    axes[1].plot([], [], "o", mfc="white", color="k", label=L("t0") + " (open circle)")
    axes[1].plot([], [], "s", color="k", label=L("t1") + " (filled square)")
    axes[1].legend(loc="upper right", frameon=False)
    fig.suptitle("Competitive share by communication, penalty point and thinking mode (n=20 games per point)")
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(FIG / "comp_fig1.png", dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, run in zip(axes, ["neutral", "anchored"]):
        d = pd.read_csv(src[run] / f"{run}_by_round.csv"); pv, sv = [], []
        for c in ["tacit", "chat", "monitored"]:
            for th, ls in [("t0", "--"), ("t1", "-")]:
                g = d[(d.comm == c) & (d.think == th) & (d.n_games >= 20)].sort_values("round")
                ax.plot(g["round"], g.share * 100, ls, color=COLc[c], label=f"{L(c)}, {L(th)}")
                if th == "t1":
                    ax.fill_between(g["round"], g.lo * 100, g.hi * 100, color=COLc[c], alpha=.12)
                pv.append(g.share.values); sv.append(g.share.values)
        CHECKS.append(f"comp_fig2 {run}: lines drawn directly from {run}_by_round.csv (n_games >= 20), as in figs.py")
        ax.set_title(run + " run (rounds with >=20 games)")
        ax.set_xlabel("round"); ax.grid(alpha=.3)
    axes[0].set_ylabel("% of firm-rounds competitive")
    fig.tight_layout()
    h_, l_ = axes[1].get_legend_handles_labels(); fig.legend(h_, l_, frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.0))
    fig.savefig(FIG / "comp_fig2.png", dpi=150, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    systematic(); pipeline_figs(); levers(); channel_shift(); competitiveness()
    print("\n".join(CHECKS + (KEYS or ["no numbered-key fallback used"])))
