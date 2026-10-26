"""Step 0.5 raw heat maps (means and counts only; DONE rows, game level).\nUsage: make_heatmaps.py NEUTRAL_RUN_CSV ANCHORED_RUN_CSV RESULTS_DIR [stage: 1|2|c|all|b]  (b = optional batch-means figure, not part of "all")\n"""
import sys, itertools, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "analysis_style"))
import collusion_colors as CC   # shared helpers: number sizing, "slug: short label" ticks
import arm_labels as AL         # shared glossary (arm_glossary.csv)

neu_csv, anc_csv, res = sys.argv[1:4]
stage = sys.argv[4] if len(sys.argv) > 4 else "all"
# optional: SHARD = "k/n" renders only every n-th figure of the stage starting at k (for parallel processes);
# HM_ONLY = comma-separated figure base names to render (verification runs); HM_DUMP = directory: every plotted
# matrix (mean, n, row codes, column codes) is written there as <figure>.json, to check that the numbers are unchanged.
SHARD = tuple(int(x) for x in (sys.argv[5] if len(sys.argv) > 5 else "0/1").split("/"))
ONLY = set(filter(None, os.environ.get("HM_ONLY", "").split(",")))
DUMPDIR = os.environ.get("HM_DUMP")
JOB = [0]


def want(name):
    """True if this process renders the figure `name` (shard and HM_ONLY filters)."""
    k = JOB[0]; JOB[0] += 1
    if ONLY:
        return name in ONLY
    return k % SHARD[1] == SHARD[0]
OUT = {"neutral": f"{res}/trackm-neutral-2026-10-25/step0_5",
       "anchored": f"{res}/trackm-anchored-2026-10-25/step0_5",
       "compare": f"{res}/trackm-compare-2026-10-25/step0_5"}


def load(p):
    d = pd.read_csv(p, low_memory=False)
    d = d[d.status == "done"].copy()
    d["ended_by_evidence"] = (d.end_reason == "EVIDENCE").astype(float)
    d["penalty_point"] = "p" + d.penalty_point.astype(int).astype(str)
    d["thinking"] = d.thinking.map({"off": "t0", "on": "t1"})
    d["wording"] = "w" + d.wording.astype(int).astype(str)
    d["seed"] = "s" + d.seed.astype(int).astype(str)
    d["planned_length"] = "L" + d.planned_length.astype(int).astype(str)
    d["firms"] = d.firms.astype(int).astype(str) + " firms"
    return d


D = {"neutral": load(neu_csv), "anchored": load(anc_csv)}
OUTC = {"price_index": "price index", "profit_gain_index": "profit gain index",
        "competitive_share": "competitive share", "matching_share": "matching share",
        "undercut_count": "undercut count", "rounds_played": "rounds played",
        "ended_by_evidence": "share ended by evidence", "collusive_game": "collusive-game share"}
absent = [o for o in OUTC if not all(o in d for d in D.values())]
OUTC = {k: v for k, v in OUTC.items() if k not in absent}
CBLAB = {"price_index": "price index = (market price - 1)/2, mean over rounds\n0 = competitive (price 1.00), 1 = monopoly (price 3.00)",
         "profit_gain_index": "profit gain index = (profit - competitive profit)/(monopoly - competitive profit)\n0 = competitive profit, 1 = monopoly (joint-profit) level",
         "competitive_share": "competitive share of scored rounds\n0 = never competitive, 1 = always competitive (higher = more competitive)",
         "matching_share": "matching share of scored rounds\n0 = never matches rival's previous quote, 1 = always",
         "undercut_count": "undercut count = rounds per game with an undercut\n(colour scale clipped at the 97th percentile)",
         "rounds_played": "rounds played per game\n(planned length, or fewer if ended by regulator evidence)",
         "ended_by_evidence": "share of games ended by regulator EVIDENCE\n0 = none ended, 1 = all ended",
         "collusive_game": "share of games with a collusive firm\n(firm collusive = competitive share <= 0.5); 0 = none, 1 = all"}
SRC = {"price_index": "price_index", "profit_gain_index": "profit_gain_index", "competitive_share": "competitive_share",
       "matching_share": "matching_share", "undercut_count": "undercut_count", "rounds_played": "rounds_played",
       "ended_by_evidence": "end_reason == EVIDENCE", "collusive_game": "collusive_game"}
INPUTS = ["arm_family", "arm", "communication", "penalty_point", "thinking", "wording", "seed", "planned_length", "firms"]
ORDER = {"communication": ["tacit", "private", "public", "monitored", "unmonitored"],
         "penalty_point": ["p1", "p3", "p4", "p5"], "thinking": ["t0", "t1"],
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
    if o == "undercut_count":
        VR[o] = (0, float(allv.quantile(.97)))
    elif o == "rounds_played":
        VR[o] = (float(allv.min()), float(allv.max()))
    else:
        VR[o] = (0, 1)
# Colours are those of the committed figures (viridis for means, RdBu_r for neutral - anchored differences): the owner
# asked that existing heat maps NOT be recoloured, so the red/green convention of collusion_colors is not applied here.
OCM = {o: "viridis" for o in OUTC}
DIFF_CM = "RdBu_r"
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
    return f"{m:.1f}" if o in ("undercut_count", "rounds_played") else f"{m:.2f}"


BIG = {"arm", "arm_family", "seed"}   # axes that always get "slug: short label" ticks (wrapped)
CODES_BIG = set()
for _d in D.values():
    for _v in BIG:
        CODES_BIG |= set(_d[_v].dropna())


def is_big(codes):
    return len(codes) > 10 or any(c in CODES_BIG for c in codes)


# short forms of the penalty-point labels for the narrow compare panels (the glossary text, abbreviated)
SHORT_PEN = {"p1": "fine 100 (lightest)", "p3": "fine 500 (middle)", "p4": "fine 1000", "p5": "fine 2000 (heaviest)"}
KEYS = {}   # figure -> {"rows": [...], "cols": [...]} when set_arm_ticks fell back to a numbered key


def tick_text(codes, wrap=CC.ARM_LABEL_WRAP, short=None):
    """Tick text of the shared rule: code on line 1, its glossary label wrapped below (at most 3 lines)."""
    if list(codes) == [""]:
        return [""]
    return CC.arm_tick_labels(list(codes), wrap, CC.ARM_LABEL_MAX_LINES, short)


def tick_pt(codes, fs):
    """Tick font size: exactly the 9 pt minimum on the long arm / arm-family / seed axes, else the figure's size (>= 9)."""
    return CC.MIN_TICK_PT if is_big(codes) else max(fs, CC.MIN_TICK_PT)


def set_ticks(ax, rl, cl, fs, grow, xwrap=None, xshort=None):
    """Both axes through collusion_colors.set_arm_ticks (>= 9 pt, wrapped, numbered key beyond 1.5x growth)."""
    k = KEYS.setdefault(ax.figure, {})
    if list(rl) == [""]:
        ax.set_yticks([])
    else:
        _, ky = CC.set_arm_ticks(ax, list(rl), "y", fontsize=tick_pt(rl, fs), grow=grow)
        if ky:
            k.setdefault("rows", []).append(ky)
    if list(cl) == [""]:
        ax.set_xticks([])
    else:
        _, kx = CC.set_arm_ticks(ax, list(cl), "x", wrap=xwrap or CC.ARM_LABEL_WRAP, fontsize=tick_pt(cl, fs), grow=grow, short=xshort)
        if kx:
            k.setdefault("cols", []).append(kx)


def draw(ax, M, N, rl, cl, o, annotate=2, fs=11, vr=None, cm=None, diff=False, grow=True, xwrap=None, xshort=None):
    lo, hi = vr or VR[o]
    ax.imshow(np.ma.masked_invalid(M), cmap=cm or OCM[o], vmin=lo, vmax=hi, aspect="auto")
    set_ticks(ax, rl, cl, fs, grow, xwrap, xshort)
    if not annotate:
        PEND.append(dict(ax=ax, items=[], nr=M.shape[0], nc=M.shape[1], M=M, N=N, rl=rl, cl=cl, title=ax.get_title() or o, force_csv=True))
    else:
        items = []
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if N[i, j] > 0 and not np.isnan(M[i, j]):
                    f = (M[i, j] - lo) / (hi - lo + 1e-12)
                    # text colour rule of the committed viridis / RdBu_r figures
                    c = ("black" if abs(f - .5) < .3 else "white") if diff else ("white" if f < .55 else "black")
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
    if DUMPDIR:
        import json
        os.makedirs(DUMPDIR, exist_ok=True)
        rec = [dict(title=q["title"], rows=list(map(str, q["rl"])), cols=list(map(str, q["cl"])),
                    mean=[[None if np.isnan(x) else float(x) for x in r] for r in np.asarray(q["M"], float)],
                    n=[[int(x) for x in r] for r in np.asarray(q["N"])]) for q in PEND if q["ax"].figure is fig]
        with open(os.path.join(DUMPDIR, Path(path).parents[2].name.split("-2026")[0] + "__" + os.path.basename(path)[:-4] + ".json"), "w") as fh:
            json.dump(rec, fh)
    kd = os.path.join(os.path.dirname(os.path.dirname(path)), "tick_keys")
    kf = os.path.join(kd, os.path.basename(path)[:-4] + ".json")
    keys = KEYS.pop(fig, {})
    if keys:
        import json
        os.makedirs(kd, exist_ok=True)
        with open(kf, "w") as fh:
            json.dump(keys, fh)
    elif os.path.exists(kf):
        os.remove(kf)
    flush(fig, path)
    fig.savefig(path, dpi=100, bbox_inches="tight"); plt.close(fig)


def wrap_label(text, width=44):
    return "\n".join(w for ln in text.split("\n") for w in (textwrap.wrap(ln, width) or [""]))


def cbar(fig, ax, o, vr=None, cm=None, label=None):
    lo, hi = vr or VR[o]
    sm = plt.cm.ScalarMappable(cmap=cm or OCM[o], norm=plt.Normalize(lo, hi)); sm.set_array([])
    c = fig.colorbar(sm, ax=ax, fraction=.03, pad=.02); c.ax.tick_params(labelsize=11)
    text = wrap_label(label or ("colour = mean of " + CBLAB[o]))   # wording of the committed (viridis) figures
    c.set_label(text, fontsize=8)
    CB_NEED[fig] = max(CB_NEED.get(fig, 0), max(len(x) for x in text.split("\n")) * 8 * 0.56 / 72 + 0.4)


def diff_label(o, ol):
    return f"difference in mean {ol}\n(neutral − anchored): red = neutral higher,\nblue = anchored higher"   # committed RdBu_r wording


def one_var(b):
    d = D[b]; vs = varying[b]
    groups = {"design": [v for v in vs if v not in ("arm", "seed")], "arm_seed": [v for v in vs if v in ("arm", "seed")]}
    for o, ol in OUTC.items():
        for gname, gv in groups.items():
            if not gv:
                continue
            if not want(f"1var_{o}_{gname}"):
                continue
            ls = {v: levels(v, d) for v in gv}
            mx = max(len(l) for l in ls.values())
            # room for the wrapped "code: short label" ticks left of every panel; each panel body is at least
            # label width / 1.45 so collusion_colors.set_arm_ticks keeps the labels (its numbered-key rule is 1.5x)
            lab_in = {v: CC.label_block_inches(tick_text(ls[v]), tick_pt(ls[v], 11))[0] for v in gv}
            Aw = [max(1.1, lab_in[v] / 1.45) for v in gv]; n_ = len(gv); A = sum(Aw) / n_
            gap = max(lab_in[v] for v in gv[1:]) + .5 if n_ > 1 else 0
            fw = lab_in[gv[0]] + .3 + sum(Aw) + (n_ - 1) * gap + 1.8
            rh = max(.5, max((t.count(chr(10)) + 1) * tick_pt(ls[v], 11) * 1.22 / 72 * 1.05 + .06 for v in gv for t in tick_text(ls[v])))
            fig, axs = plt.subplots(1, len(gv), figsize=(fw, max(3.5, rh * mx + 1.8)), squeeze=False,
                                    gridspec_kw={"wspace": gap / A, "width_ratios": Aw})
            fig.subplots_adjust(left=(lab_in[gv[0]] + .3) / fw, right=1 - 1.8 / fw)
            for ax, v in zip(axs[0], gv):
                g = d.groupby(v)[o].agg(["mean", "count"]).reindex(ls[v])
                draw(ax, g[["mean"]].values, g[["count"]].values, ls[v], [""], o, annotate=2, fs=11, grow=False)
                ax.set_title(v, fontsize=11); ax.set_xticks([])
                ax.set_xlabel("cell: mean (n games)", fontsize=10)
            fig.suptitle(f"Mean {ol} by each input on its own (cell = mean over games, n = number of games); {b} run, all {len(d)} DONE games pooled",
                         fontsize=13, y=1.0, va="bottom")
            cbar(fig, axs[0].tolist(), o)
            savefig(fig, f"{OUT[b]}/figures/1var_{o}_{gname}.png")


PRIORITY = [("communication", "penalty_point"), ("communication", "thinking"), ("penalty_point", "thinking"), ("arm", "thinking"),
            ("wording", "seed"), ("wording", "thinking"), ("planned_length", "communication")]


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
            if not want(f"2var_{o}__{a}_x_{c}"):
                continue
            M, N = grid(d, o, a, c, la, lb)
            m = mode(M.size); fs = 11 if M.size <= 60 else (9 if M.size <= 200 else 8)
            cw = .95
            nl = max(t.count(chr(10)) + 1 for t in tick_text(la))
            rh = max(.3, nl * tick_pt(la, fs) * 1.22 / 72 * 1.2 + .03)   # row pitch = height of the wrapped tick label   # base row pitch; set_arm_ticks grows it (<= 1.5x) for wrapped labels
            fig, ax = plt.subplots(figsize=(max(5, cw * len(lb) + 2.5) if m else max(6, .3 * len(lb) + 3),
                                            max(3.5, max(.6, rh) * len(la) + 1.5) if m == 2 else max(3.5, rh * len(la) + 1.5)))
            draw(ax, M, N, la, lb, o, annotate=m, fs=fs)
            ax.set_xlabel(c, fontsize=13); ax.set_ylabel(a, fontsize=13)
            note = {2: "mean and n per cell shown", 1: "mean per cell shown", 0: "colour only, too many cells to print"}[m]
            ax.set_title(f"Mean {ol} by {a} (rows) × {c} (columns); {b} run, all {len(d)} DONE games pooled "
                         f"({int((N > 0).sum())} non-empty cells)\n{note}", fontsize=9 if len(a + c) > 22 else 10)
            cbar(fig, ax, o)
            savefig(fig, f"{OUT[b]}/figures/2var_{o}__{a}_x_{c}.png")


def compare():
    n, a = D["neutral"], D["anchored"]
    lc, lp = levels("communication", n, a), levels("penalty_point", n, a)
    for o, ol in OUTC.items():
        if o not in ("price_index", "profit_gain_index", "competitive_share", "matching_share"):
            continue  # the committed compare folder holds these four outcomes only (the others have no fixed difference scale)
        if not want(f"diff_{o}__comm_x_penalty_x_thinking"):
            continue
        # taller and wider than before: the penalty-point ticks now read "p1: penalty point 1: ..." (wrapped)
        fig, axs = plt.subplots(3, 2, figsize=(14, 15), squeeze=False, gridspec_kw={"hspace": .8, "wspace": .62})
        dm = []
        for j, t in enumerate(["t0", "t1"]):
            Mn, Nn = grid(n[n.thinking == t], o, "communication", "penalty_point", lc, lp)
            Ma, Na = grid(a[a.thinking == t], o, "communication", "penalty_point", lc, lp)
            for i, (M, N, nm) in enumerate([(Mn, Nn, "neutral"), (Ma, Na, "anchored")]):
                draw(axs[i, j], M, N, lc, lp, o, annotate=2, fs=9, grow=False, xwrap=12, xshort=SHORT_PEN)
                axs[i, j].set_title(f"{nm} run, thinking {'ON (t1)' if t == 't1' else 'OFF (t0)'} (n = {int(N.sum())} games)", fontsize=10)
            dm.append((Mn - Ma, np.minimum(Nn, Na)))
        R = {"price_index": .5, "competitive_share": .5, "profit_gain_index": .5, "matching_share": .5,
             "ended_by_evidence": .5, "collusive_game": .5}.get(o)
        if R is None:
            R = max(float(np.nanmax(np.abs(x[0]))), 1e-6)
        for j, (Df, Nm) in enumerate(dm):
            draw(axs[2, j], Df, Nm, lc, lp, o, annotate=1, vr=(-R, R), cm=DIFF_CM, diff=True, fs=9, grow=False, xwrap=12, xshort=SHORT_PEN)
            axs[2, j].set_title(f"DIFFERENCE neutral − anchored, thinking {'ON (t1)' if j else 'OFF (t0)'}\n(cell: mean neutral − mean anchored)", fontsize=10)
        for i in range(3):
            axs[i, 0].set_ylabel("communication", fontsize=12)
        for j in range(2):
            axs[2, j].set_xlabel("penalty point", fontsize=12)
        cbar(fig, axs[:2, :].ravel().tolist(), o)
        cbar(fig, axs[2, :].tolist(), o, vr=(-R, R), cm=DIFF_CM,
             label=diff_label(o, ol))
        for j in range(2):
            axs[2, j].set_xlabel("penalty point (p1 = collusion pays ... p5 = does not)", fontsize=10)
        fig.suptitle(f"Mean {ol} by communication × penalty point × thinking: top neutral run, middle anchored run, bottom neutral − anchored\n"
                     f"neutral run = payoff examples evenly spaced 1.00-4.00; anchored run = examples printed at 1.54, 2.09, 3.00\n"
                     f"all DONE games: n = {len(n)} neutral, {len(a)} anchored; cells: mean and n; difference uses the smaller n",
                     fontsize=10, y=0.94)
        savefig(fig, f"{OUT['compare']}/figures/diff_{o}__comm_x_penalty_x_thinking.png")


def batch_means():
    fig, axs = plt.subplots(1, len(OUTC), figsize=(2.3 * len(OUTC) + 1, 3.2))
    for ax, (o, ol) in zip(axs, OUTC.items()):
        M = np.array([[D[b][o].mean()] for b in ["neutral", "anchored"]]); N = np.array([[D[b][o].count()] for b in ["neutral", "anchored"]])
        draw(ax, M, N, ["neutral", "anchored"], [""], o, annotate=2, grow=False); ax.set_title(ol, fontsize=11); ax.set_xticks([])
        ax.set_ylabel("run (payoff_examples)", fontsize=9); ax.set_xlabel("cell: mean, n games", fontsize=8)
    fig.suptitle(f"Mean of each outcome by run (neutral = evenly spaced payoff examples 1.00-4.00, n={len(D['neutral'])}; anchored = examples at 1.54, 2.09, 3.00, n={len(D['anchored'])}); "
                 "all DONE games pooled\n(each panel has its own colour scale, fixed 0-1 for indices and shares; definitions in STEP0_5.md)", fontsize=11, y=1.2)
    savefig(fig, f"{OUT['compare']}/figures/batch_means_all_outcomes.png")


if stage in ("all", "1"):
    for b in D: one_var(b)
if stage in ("all", "2"):
    for b in D: two_var(b)
if stage in ("all", "c"):
    compare()
if stage == "b":
    batch_means()
print("annotations dropped (values in tables/*.csv):", len(DROPPED))
print("absent outcomes:", absent, "varying:", varying)
