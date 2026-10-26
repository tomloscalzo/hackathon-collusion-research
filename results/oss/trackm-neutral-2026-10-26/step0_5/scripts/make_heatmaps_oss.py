"""Step 0.5 raw heat maps for the gpt-oss-20b neutral run (means and counts only; DONE rows, game level).
Adapted from results/trackm-compare-2026-10-25/step0_5/make_heatmaps.py (the Qwen3-32B two-run version).
Usage: make_heatmaps_oss.py OSS_RUN_CSV OUT_DIR [stage: 1|2|s|all]
One model (gpt-oss-20b, reasoning effort medium on every call): no thinking facet and no anchored run, so no cross-run map.
The five arm_build_bug arms (fx-*/nx-*: planned formula / no-numbers arms that played the headline prompt because of a global
payoff_examples=neutral grid override) are left out of every main map and shown only in the labelled sensitivity figure (stage s).
"""
import sys, itertools, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "tools" / "analysis_style"))
import collusion_colors as CC   # shared red = collusion / green = competition convention
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_common"))
from oss_arm_labels import maybe as ARMLAB, wrap as ARMWRAP, label as ARMLABEL   # owner rule: arm labels are "slug: description", never bare slugs

run_csv, out_dir = sys.argv[1:3]
stage = sys.argv[3] if len(sys.argv) > 3 else "all"
RUNLAB = "gpt-oss-20b (reasoning effort medium), neutral payoff table"
B = "gpt-oss"
OUT = {B: out_dir}
# display names: the control arms' grid names say 32b, but the games ran on gpt-oss-20b
ARM_DISPLAY = {}   # slugs stay slugs in the data; figures label them with oss_arm_labels (the ctl-32b-* labels say they are gpt-oss controls)


def load(p, bug=False):
    d = pd.read_csv(p, low_memory=False)
    if set(d["model_label"].dropna().unique()) != {"gpt-oss-20b, reasoning effort medium"}:
        raise SystemExit("error: run.csv is not a gpt-oss-only table (model_label); refusing to draw mixed models")
    d = d[d.status == "done"].copy()
    d = d[d.arm_build_bug.fillna(0).astype(int) == (1 if bug else 0)].copy()
    d["avg_abs_spread"] = d.market_price_mean
    # the Qwen-era builder leaves the arms added on Sunday in family 'other'; give them their own family for the maps
    fam = {"moral-prime": "moral_prime", "moral-prime-b": "moral_prime", "moral-placebo": "moral_prime",
           "wd-notice-only": "watchdog", "wd-noncomp": "watchdog", "wd-ask-noreport": "watchdog", "d-conflict-ethics": "dset"}
    d["arm_family"] = [fam.get(a, f) if f == "other" else f for a, f in zip(d.arm, d.arm_family)]
    d["arm"] = d.arm.map(lambda a: ARM_DISPLAY.get(a, a))
    d["ended_by_evidence"] = (d.end_reason == "EVIDENCE").astype(float)
    d["penalty_point"] = "p" + d.penalty_point.astype(int).astype(str)
    d["thinking"] = d.thinking.map({"off": "t0", "on": "t1"})
    d["wording"] = "w" + d.wording.astype(int).astype(str)
    d["seed"] = "s" + d.seed.astype(int).astype(str)
    d["planned_length"] = "L" + d.planned_length.astype(int).astype(str)
    d["firms"] = d.firms.astype(int).astype(str) + " firms"
    return d


D = {B: load(run_csv)}
BUG = load(run_csv, bug=True)
N_NOT_DONE = int((pd.read_csv(run_csv, low_memory=False).status != "done").sum())
OUTC = {"avg_abs_spread": "average absolute spread", "price_index": "price index", "profit_gain_index": "profit gain index",
        "competitive_share": "competitive share", "matching_share": "matching share",
        "undercut_count": "undercut count", "rounds_played": "rounds played",
        "ended_by_evidence": "share ended by evidence", "collusive_game": "collusive-game share"}   # empty_talk_done_count is a technical covariate, not an outcome: no maps (owner rule); see the appendix table
absent = [o for o in OUTC if not all(o in d for d in D.values())]
OUTC = {k: v for k, v in OUTC.items() if k not in absent}
CBLAB = {"avg_abs_spread": "average absolute spread = mean market quote (half-spread), raw units\n1.00 = competitive floor, 3.00 = monopoly (colour clipped at 1.00 to 3.00)",
         "empty_talk_done_count": "empty talk replies read as done per game (gpt-oss covariate, unit E1)\n(colour scale clipped at the 97th percentile)",
         "price_index": "price index = (market price - 1)/2, mean over rounds\n0 = competitive (price 1.00), 1 = monopoly (price 3.00)",
         "profit_gain_index": "profit gain index = (profit - competitive profit)/(monopoly - competitive profit)\n0 = competitive profit, 1 = monopoly (joint-profit) level",
         "competitive_share": "competitive share of scored rounds\n0 = never competitive, 1 = always competitive (higher = more competitive)",
         "matching_share": "matching share of scored rounds\n0 = never matches rival's previous quote, 1 = always",
         "undercut_count": "undercut count = rounds per game with an undercut\n(colour scale clipped at the 97th percentile)",
         "rounds_played": "rounds played per game\n(planned length, or fewer if ended by regulator evidence)",
         "ended_by_evidence": "share of games ended by regulator EVIDENCE\n0 = none ended, 1 = all ended",
         "collusive_game": "share of games with a collusive firm\n(firm collusive = competitive share <= 0.5); 0 = none, 1 = all"}
SRC = {"avg_abs_spread": "market_price_mean", "empty_talk_done_count": "empty_talk_done_count", "price_index": "price_index", "profit_gain_index": "profit_gain_index", "competitive_share": "competitive_share",
       "matching_share": "matching_share", "undercut_count": "undercut_count", "rounds_played": "rounds_played",
       "ended_by_evidence": "end_reason == EVIDENCE", "collusive_game": "collusive_game"}
INPUTS = ["arm_family", "arm", "communication", "penalty_point", "payoff_examples", "wording", "seed", "planned_length", "firms"]   # thinking is constant (medium effort)
ORDER = {"communication": ["tacit", "private", "public", "monitored", "unmonitored"],
         "penalty_point": ["p1", "p3", "p4", "p5"], "thinking": ["t0", "t1"], "payoff_examples": ["neutral", "formula", "none"],
         "wording": [f"w{i}" for i in range(5)], "planned_length": ["L7", "L15", "L19", "L20"],
         "firms": ["2 firms", "3 firms"]}


def levels(v, *dfs):
    s = set().union(*[set(d[v].dropna()) for d in dfs])
    o = [x for x in ORDER.get(v, []) if x in s]
    if v == "seed":
        return sorted(s, key=lambda x: int(x[1:]))
    if v == "arm":
        fam = pd.concat(dfs).drop_duplicates("arm").set_index("arm").arm_family.to_dict()
        return sorted(s, key=lambda x: (fam.get(x, ""), x))
    return o + sorted(s - set(o), key=lambda x: (len(str(x)), str(x)))


varying = {b: [v for v in INPUTS if D[b][v].nunique() > 1] for b in D}
VR = {}
for o in OUTC:
    allv = pd.concat([D[b][o] for b in D])
    if o in ("undercut_count", "empty_talk_done_count"):
        VR[o] = (0, max(1.0, float(allv.quantile(.97))))
    elif o == "avg_abs_spread":
        VR[o] = (1.0, 3.0)
    elif o == "rounds_played":
        VR[o] = (float(allv.min()), float(allv.max()))
    else:
        VR[o] = (0, 1)
OCM = {o: CC.cmap_for(o) for o in OUTC}   # per-outcome colormap: RdYlGn_r (collusion), RdYlGn (competition), Blues (neutral)
PEND = []        # annotations are placed after layout so the figure can grow to fit >= 9.5 pt numbers
DROPPED = []
CB_NEED = {}     # figure -> inches of vertical room its colour bar label needs


def flush(fig, path):
    """Make the colour bar tall enough for its label (no overlap with the title), then place cell numbers
    (mean and n; else mean only) at >= 9.5 pt, growing the figure; if even that cannot fit, leave the colour and
    write the values to tables/<figure>.csv."""
    mine = [q for q in PEND if q["ax"].figure is fig]
    for q in mine:
        PEND.remove(q)
    need = CB_NEED.pop(fig, 0)
    if mine and need:
        w, h = fig.get_size_inches()
        ah = min(q["ax"].get_position().height for q in mine) * h
        if ah < need:
            fig.set_size_inches(w, h * min(need / ah, 4.0))
    if not mine:
        return
    for key in (() if any(q.get("force_csv") for q in mine) else ("full", "short")):
        if all(CC.annotations_fit(fig, q["ax"], q["nr"], q["nc"], [t[key] for t in q["items"]], max_scale=2.5) for q in mine):
            for q in mine:
                CC.fit_annotations(fig, q["ax"], q["nr"], q["nc"], [t[key] for t in q["items"]], max_scale=2.5)
            for q in mine:
                for t in q["items"]:
                    q["ax"].text(t["j"], t["i"], t[key], ha="center", va="center", color=t["c"], fontsize=CC.MIN_ANNOT_PT, linespacing=.9)
                if key == "short":   # the title note said 'mean and n'; only the mean fits at a legible size
                    q["ax"].set_title(q["ax"].get_title().replace("mean and n per cell shown", "mean per cell shown (n in tables/ and STEP0_5.md)"), fontsize=q["ax"].title.get_fontsize())
            return
    DROPPED.append(path)
    for q in mine:
        t_ = q["ax"].get_title()
        for old in ("mean and n per cell shown", "mean per cell shown", "colour only, too many cells to print"):
            t_ = t_.replace(old, "numbers omitted (too dense to print legibly); values in tables/" + os.path.basename(path)[:-4] + ".csv")
        q["ax"].set_title(t_, fontsize=q["ax"].title.get_fontsize())
    rows = [dict(panel=q["title"], row=q["rl"][i], col=q["cl"][j], mean=q["M"][i, j], n=int(q["N"][i, j]))
            for q in mine for i in range(q["nr"]) for j in range(q["nc"]) if q["N"][i, j] > 0]
    out = os.path.join(os.path.dirname(os.path.dirname(path)), "tables", os.path.basename(path)[:-4] + ".csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)




def fmt(m, o):
    return f"{m:.1f}" if o in ("undercut_count", "rounds_played", "empty_talk_done_count") else f"{m:.2f}"


def draw(ax, M, N, rl, cl, o, annotate=2, fs=11, vr=None, cm=None, diff=False):
    lo, hi = vr or VR[o]
    ax.set_facecolor("#d0d0d0")   # blank (no games) cells show grey, not white (Step 0.5 style rule)
    ax.imshow(np.ma.masked_invalid(M), cmap=cm or OCM[o], vmin=lo, vmax=hi, aspect="auto")
    ax.set_xticks(range(len(cl))); ax.set_yticks(range(len(rl)))
    cl_l = [ARMWRAP(ARMLAB(c)) for c in cl]; rl_l = [ARMWRAP(ARMLAB(r), width=30, max_lines=2) for r in rl]   # owner rule: >= 9 pt, wrapped, compact
    ax.set_xticklabels(cl_l, fontsize=max(fs, 9), rotation=90 if (len(cl) > 8 or max(len(str(c)) for c in cl_l) > 8) else 0, linespacing=1.0)
    ax.set_yticklabels(rl_l, fontsize=max(fs, 9), linespacing=1.0)
    if not annotate:
        PEND.append(dict(ax=ax, items=[], nr=M.shape[0], nc=M.shape[1], M=M, N=N, rl=rl, cl=cl, title=ax.get_title() or o, force_csv=True))
    else:
        direct = CC.direction(o) != CC.NEUTRAL
        items = []
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if N[i, j] > 0 and not np.isnan(M[i, j]):
                    f = (M[i, j] - lo) / (hi - lo + 1e-12)
                    c = ("white" if (f > .85 or f < .15) else "black") if (direct or diff) else ("white" if f > .7 else "black")
                    short = f"{M[i, j]:+.2f}" if diff else fmt(M[i, j], o)
                    items.append(dict(i=i, j=j, short=short, full=(short + "\nn=" + str(int(N[i, j]))) if annotate == 2 else short, c=c))
        PEND.append(dict(ax=ax, items=items, nr=M.shape[0], nc=M.shape[1], M=M, N=N, rl=rl, cl=cl, title=ax.get_title() or o))
    for s_ in ax.spines.values():
        s_.set_visible(False)


def grid(d, o, a, b, la, lb):
    g = d.groupby([a, b])[o].agg(["mean", "count"])
    M = np.full((len(la), len(lb)), np.nan); N = np.zeros_like(M)
    for (x, y), r in g.iterrows():
        if x in la and y in lb:
            M[la.index(x), lb.index(y)] = r["mean"]; N[la.index(x), lb.index(y)] = r["count"]
    return M, N


def mode(nc):
    return 2 if nc <= 40 else (1 if nc <= 160 else 0)


def savefig(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    flush(fig, path)
    fig.savefig(path, dpi=100, bbox_inches="tight"); plt.close(fig)


def wrap_label(text, width=44):
    return "\n".join(w for ln in text.split("\n") for w in (textwrap.wrap(ln, width) or [""]))


def cbar(fig, ax, o, vr=None, cm=None, label=None):
    lo, hi = vr or VR[o]
    sm = plt.cm.ScalarMappable(cmap=cm or OCM[o], norm=plt.Normalize(lo, hi)); sm.set_array([])
    c = fig.colorbar(sm, ax=ax, fraction=.03, pad=.02); c.ax.tick_params(labelsize=11)
    text = wrap_label(label or (CC.cbar_label("colour = mean of " + CBLAB[o], o)))
    c.set_label(text, fontsize=9)
    CB_NEED[fig] = max(CB_NEED.get(fig, 0), max(len(x) for x in text.split("\n")) * 8 * 0.56 / 72 + 0.4)


def diff_label(o, ol):
    if CC.direction(o) == CC.NEUTRAL:
        return f"difference in mean {ol} (neutral - anchored)\npurple = neutral run higher, blue = anchored run higher (no collusion direction)"
    return f"difference in mean {ol} (neutral - anchored)\nred = more collusive / green = more competitive (red = neutral run more collusive)"


def one_var(b):
    d = D[b]; vs = varying[b]
    groups = {"design": [v for v in vs if v not in ("arm", "seed")], "arm_seed": [v for v in vs if v in ("arm", "seed")]}
    for o, ol in OUTC.items():
        for gname, gv in groups.items():
            if not gv:
                continue
            ls = {v: levels(v, d) for v in gv}
            mx = max(len(l) for l in ls.values())
            fig, axs = plt.subplots(1, len(gv), figsize=(2.4 * len(gv) + 1.5, max(3.5, .5 * mx + 1.8)), squeeze=False,
                                    gridspec_kw={"width_ratios": [1.6 if v == "arm" else 1 for v in gv], "wspace": .9})
            for ax, v in zip(axs[0], gv):
                g = d.groupby(v)[o].agg(["mean", "count"]).reindex(ls[v])
                draw(ax, g[["mean"]].values, g[["count"]].values, ls[v], [""], o, annotate=2, fs=11)
                ax.set_title(v, fontsize=11); ax.set_xticks([])
                ax.set_xlabel("cell: mean (n games)", fontsize=10)
            fig.suptitle(f"Mean {ol} by each input on its own (cell = mean over games, n = number of games)\n{RUNLAB}: all {len(d)} DONE games pooled (formula/no-numbers build-bug arms excluded)",
                         fontsize=13, y=1.0, va="bottom")
            cbar(fig, axs[0].tolist(), o)
            savefig(fig, f"{OUT[b]}/figures/1var_{o}_{gname}.png")


PRIORITY = [("communication", "penalty_point"), ("arm", "penalty_point"), ("wording", "seed"), ("arm", "wording"),
            ("planned_length", "communication")]   # the thinking pairs of the Qwen version do not exist (one mode)


def pairs(b):
    vs = varying[b]
    ps = [(a, c) for a, c in PRIORITY if a in vs and c in vs]
    for a, c in itertools.combinations(vs, 2):
        if {a, c} == {"arm", "arm_family"}:
            continue
        if (a, c) not in ps and (c, a) not in ps:
            ps.append((a, c))
    return ps


def two_var(b):
    d = D[b]
    for a, c in pairs(b):
        la, lb = levels(a, d), levels(c, d)
        for o, ol in OUTC.items():
            M, N = grid(d, o, a, c, la, lb)
            m = mode(M.size); fs = 11 if M.size <= 60 else (9 if M.size <= 200 else 8)
            fig, ax = plt.subplots(figsize=(max(5, .95 * len(lb) + 2.5) if m else max(6, .3 * len(lb) + 3),
                                            max(3.5, .6 * len(la) + 1.5) if m == 2 else max(3.5, .3 * len(la) + 1.5)))
            draw(ax, M, N, la, lb, o, annotate=m, fs=fs)
            ax.set_xlabel(c, fontsize=13); ax.set_ylabel(a, fontsize=13)
            note = {2: "mean and n per cell shown", 1: "mean per cell shown", 0: "colour only, too many cells to print"}[m]
            ax.set_title(f"Mean {ol} by {a} (rows) × {c} (columns); {RUNLAB}, {len(d)} DONE games "
                         f"({int((N > 0).sum())} non-empty cells)\n{note}", fontsize=9 if len(a + c) > 22 else 10)
            cbar(fig, ax, o)
            savefig(fig, f"{OUT[b]}/figures/2var_{o}__{a}_x_{c}.png")


SENS_ROWS = [("headline-chat", "p1"), ("hrep-fx-chat-p1", "p1"), ("hrep-nx-chat-p1", "p1"), ("fx-chat-p1", "p1"), ("nx-chat-p1", "p1"),
             ("headline-tacit", "p1"), ("hrep-fx-tacit-p1", "p1"), ("hrep-nx-tacit-p1", "p1"), ("fx-tacit-p1", "p1"), ("nx-tacit-p1", "p1"),
             ("headline-chat", "p5"), ("hrep-fx-chat-p5", "p5"), ("fx-chat-p5", "p5")]
SENS_LABEL = {"headline-chat": "headline-chat (declared)", "headline-tacit": "headline-tacit (declared)",
              "hrep-fx-chat-p1": "hrep-fx-chat-p1 replicate*", "hrep-nx-chat-p1": "hrep-nx-chat-p1 replicate*",
              "hrep-fx-tacit-p1": "hrep-fx-tacit-p1 replicate*", "hrep-nx-tacit-p1": "hrep-nx-tacit-p1 replicate*",
              "hrep-fx-chat-p5": "hrep-fx-chat-p5 replicate*",
              "fx-chat-p1": "fx-chat-p1 (formula, corrected)", "nx-chat-p1": "nx-chat-p1 (no numbers, corrected)",
              "fx-tacit-p1": "fx-tacit-p1 (formula, corrected)", "nx-tacit-p1": "nx-tacit-p1 (no numbers, corrected)",
              "fx-chat-p5": "fx-chat-p5 (formula, corrected)"}
SENS_LABEL = {k: ARMLABEL(k) + (" (declared)" if k.startswith("headline") else " *" if k.startswith("hrep") else " (corrected)") for k in SENS_LABEL}
FIVE = ["avg_abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"]


def sensitivity():
    """The five build-bug arms beside the declared headline cells whose prompt they played (sensitivity only, never pooled here)."""
    d = pd.concat([D[B], BUG])
    have = set(d.arm)
    rows_ = [(a, p) for a, p in SENS_ROWS if a in have]   # the corrected formula / no-numbers arms appear once their root is collected
    rl = [f"{SENS_LABEL[a]} {p}" for a, p in rows_]
    fig, axs = plt.subplots(1, 5, figsize=(19, 6.5), squeeze=False, gridspec_kw={"wspace": 0.9})
    rows = []
    for k, (ax, o) in enumerate(zip(axs[0], FIVE)):
        M = np.full((len(rows_), 1), np.nan); N = np.zeros_like(M)
        for i, (a, p) in enumerate(rows_):
            x = d[(d.arm == a) & (d.penalty_point == p)][o].dropna()
            if len(x):
                M[i, 0], N[i, 0] = x.mean(), len(x)
            rows.append(dict(metric=o, row=rl[i], mean=M[i, 0], n=int(N[i, 0])))
        draw(ax, M, N, rl if k == 0 else [""] * len(rl), [""], o, annotate=2, fs=10)
        ax.set_title(OUTC[o], fontsize=11); ax.set_xticks([])
        cbar(fig, ax, o)
    fig.suptitle("SENSITIVITY ONLY: * = the five hrep-* arms, planned as formula / no-numbers but played with payoff_examples neutral (build bug),\n"
                 f"i.e. headline-cell replicates, beside the declared headline cell and (when collected) the corrected formula / no-numbers arms; {RUNLAB}; cell = mean (n DONE games)", fontsize=12, y=1.02, va="bottom")
    savefig(fig, f"{OUT[B]}/figures/sens_buildbug_replicates_vs_headline.png")
    os.makedirs(f"{OUT[B]}/tables", exist_ok=True)
    pd.DataFrame(rows).to_csv(f"{OUT[B]}/tables/sens_buildbug_replicates_vs_headline.csv", index=False)


def write_tables():
    """Long-format tables (levels, mean, n) behind every 1-variable and 2-variable map."""
    d = D[B]; os.makedirs(f"{OUT[B]}/tables", exist_ok=True)
    rows = []
    for v in varying[B]:
        g = d.groupby(v)[list(OUTC)].agg(["mean", "count"])
        for lev in levels(v, d):
            if lev in g.index:
                for o in OUTC:
                    rows.append(dict(variable=v, level=lev, outcome=o, mean=g.loc[lev, (o, "mean")], n=int(g.loc[lev, (o, "count")])))
    pd.DataFrame(rows).to_csv(f"{OUT[B]}/tables/h1_all.csv", index=False)
    rows = []
    for a, c in pairs(B):
        g = d.groupby([a, c])[list(OUTC)].agg(["mean", "count"])
        for (x, y) in g.index:
            for o in OUTC:
                rows.append(dict(var_a=a, level_a=x, var_b=c, level_b=y, outcome=o, mean=g.loc[(x, y), (o, "mean")], n=int(g.loc[(x, y), (o, "count")])))
    pd.DataFrame(rows).to_csv(f"{OUT[B]}/tables/h2_all.csv", index=False)


write_tables()
if stage in ("all", "1"):
    for b in D: one_var(b)
if stage in ("all", "2"):
    for b in D: two_var(b)
if stage in ("all", "s"):
    sensitivity()
print("annotations dropped (values in tables/*.csv):", len(DROPPED))
print("absent outcomes:", absent, "varying:", varying)
print("games:", len(D[B]), "build-bug replicates:", len(BUG), "rows not done:", N_NOT_DONE)
