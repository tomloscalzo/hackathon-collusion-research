"""Figures and Markdown table snippets for results/ad-hoc-targeted-analysis/side-channels/.

Reads the CSVs written by price_channel.py, text_channel.py, std_metrics.py and keywords.py (copied next to this
script in the report folder) and writes PNGs plus tables.md. No number is recomputed for the forest charts.
"""
import os, sys, textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import ci_forest as CF, arm_labels as AL

CLAB = {  # contrast key -> "slug (model, cell) minus control" row label
    "oss: ethics rule on one firm (m-asym) minus headline chat, p3": "m-asym (gpt-oss p3)",
    "oss: reasoning-monitor threat A minus headline chat, p1": "d-cot-monitor-a (gpt-oss p1)",
    "oss: ethics rule under conflict prompt minus conflict prompt, p1": "d-conflict-ethics (gpt-oss p1)",
    "qwen t1: reasoning-monitor threat A minus headline chat, p1": "d-cot-monitor-a (Qwen t1 p1)",
    "qwen t1: reasoning-monitor threat B minus headline chat, p1": "d-cot-monitor-b (Qwen t1 p1)",
    "qwen t1: ethics rule on one firm (m-asym) minus headline chat, p3": "m-asym (Qwen t1 p3)",
    "oss: no chat (tacit) minus headline chat, p1": "headline-tacit (gpt-oss p1)",
    "qwen t1: no chat (tacit) minus headline chat, p1": "headline-tacit (Qwen t1 p1)",
}
FEATS = ["parity", "digit", "round05", "movesize"]
PMET = {"te": "price-move transfer entropy (bits, bias-corrected)", "cmi_parity": "odd/even-cent code test (bits)",
        "cmi_digit": "last-digit code test (bits)", "cmi_round05": "digit 0-or-5 code test (bits)",
        "cmi_movesize": "move-size code test (bits)", "alternation": "alternation rate of own moves (share)",
        "odd_share": "odd-cent share of quotes above 1.00"}


CTRL = {"oss: ethics rule under conflict prompt minus conflict prompt, p1": "d-conflict"}


def tlab(c):
    """Table row label: 'slug: short label (model, cell) minus control-slug: short label'."""
    short = CLAB[c]; slug = short.split(" (")[0]; rest = short[len(slug):].strip()
    ctrl = CTRL.get(c, "headline-chat")
    return f"{AL.label(slug)} {rest} minus {AL.label(ctrl)}"


def cell_label(c):
    parts = c.split("|"); model = "gpt-oss-20b" if parts[0] == "oss" else "Qwen3-32B"
    arm = parts[1]; slug = {"copybot-o150": "copybot-o150-tacit", "copybot-o250": "copybot-o250-tacit"}.get(arm, arm)
    rest = [p for p in parts[2:]]
    extra = ", ".join(x.replace("t1", "thinking on").replace("t0", "thinking off") for x in rest)
    return f"{AL.label(slug)} [{model}, {extra}]", slug


def fmt(v, d=3):
    return "" if pd.isna(v) else f"{v:+.{d}f}"


def ci(r, d=3):
    s_ = f"{r['diff']:+.{d}f} [{r['lo']:+.{d}f}, {r['hi']:+.{d}f}]"
    for k in ("signflip_p", "perm_p"):
        if k in r and not pd.isna(r[k]):
            s_ += f" (p {r[k]:.3f})"
    return s_


def main():
    md = []
    # ---- standard metrics
    S = pd.read_csv(os.path.join(HERE, "standard_metrics.csv"))
    sm = S[S.lo.notna()].copy(); sm["label"] = sm.contrast.map(CLAB); sm["tlabel"] = sm.contrast.map(tlab)
    mets = list(dict.fromkeys(sm.metric))
    md.append("<!-- TABLE std -->\n| Contrast (treatment minus control) | pairs | " + " | ".join(mets) + " |\n|---|---|" + "---|" * len(mets))
    for lab, g in sm.groupby("tlabel", sort=False):
        md.append(f"| {lab} | {int(g.n_pairs.iloc[0])} | " + " | ".join(ci(g[g.metric == m].iloc[0]) for m in mets) + " |")
    ag = S[S.lo.isna()]
    md.append("\n<!-- TABLE agree -->\n| Contrast | both firms sent an agreement message (`explicit_agreement_flag`): treatment / control | any agreement message (`explicit_agreement_any`): treatment / control |\n|---|---|---|")
    for c, g in ag.groupby("contrast", sort=False):
        a = g[g.metric == "explicit_agreement_flag"].iloc[0]; b = g[g.metric == "explicit_agreement_any"].iloc[0]
        md.append(f"| {tlab(c)} | {a.treatment:.2f} / {a.control:.2f} | {b.treatment:.2f} / {b.control:.2f} |")
    CF.forest(sm.rename(columns={"diff": "estimate"})[["label", "metric", "estimate", "lo", "hi"]],
              os.path.join(HERE, "fig_standard_metrics_forest.png"),
              title="Five standard metrics, treatment minus control (95% bootstrap CI over (wording, seed) pairs)")
    md.append("\n<!-- LEGEND std -->\n" + CF.legend_md(sm.rename(columns={"diff": "estimate"})))

    # ---- price cells (TE and raw MI from v1; code tests from v2)
    P = pd.read_csv(os.path.join(HERE, "price_cells.csv"))
    V = pd.read_csv(os.path.join(HERE, "price_codes_v2.csv"))
    fam_n = int(V.holm_family_size.iloc[0])
    md.append("\n<!-- TABLE cells -->\n| Cell [model, details] | role | games | transitions | TE (bits, bc; p) | raw digit MI (bits, bc) | "
              + " | ".join(f"{f} code: bc bits; p under S / S-no-focal / S+game; min Holm p" for f in FEATS) + " |\n|---|---|---|---|---|---|" + "---|" * len(FEATS))
    for _, r in P.iterrows():
        lab, _ = cell_label(r.cell); v = V[V.cell == r.cell]
        def c(f):
            g = v[v.feature == f].set_index("mode")
            hol = g.p_holm.min()
            hs = "excluded (degenerate)" if g.degenerate.iloc[0] and "copybot" not in r.cell else ("calibration" if "copybot" in r.cell else f"{hol:.2f}")
            return f"{g.loc['S', 'bc']:+.3f}; {g.loc['S', 'p']:.4f} / {g.loc['S_nofocal', 'p']:.4f} / {g.loc['S_game', 'p']:.4f}; {hs}"
        md.append(f"| {lab} | {r.role} | {r.games} | {r.n_trans} | {r.te_bc:+.3f} ({r.te_p:.3f}) | {r.mi_digit_bc:+.3f} | " + " | ".join(c(f) for f in FEATS) + " |")
    panels = [("te", "Price-move transfer entropy\n(ordinary price-following)"), ("mi_digit", "Raw last-digit MI\n(no conditioning)")] + \
             [(f, t) for f, t in zip(FEATS, ["Odd/even-cent code test", "Last-digit code test", "Digit 0-or-5 code test", "Move-size code test"])]
    labs = [textwrap.fill(cell_label(c)[0], 44) for c in P.cell]
    fig, axes = plt.subplots(1, 6, figsize=(22, 0.55 * len(P) + 2.4), sharey=True, constrained_layout=True)
    y = np.arange(len(P))[::-1]
    cols = {"control": ("#5d7a99", "o"), "treatment": ("#8e44ad", "D"), "no-chat": ("#d68910", "s"), "negative": ("#7f8c8d", "v"), "positive": ("#111111", "^")}
    for ax, (f, t) in zip(axes, panels):
        for yi, (_, r) in zip(y, P.iterrows()):
            if f in ("te", "mi_digit"):
                v_ = r[f + "_bc"]; sd = abs((r[f] - r[f + "_nullmean"]) / r[f + "_z"]) if r[f + "_z"] not in (0,) and not pd.isna(r[f + "_z"]) else 0
            else:
                g = V[(V.cell == r.cell) & (V.feature == f) & (V["mode"] == "S")].iloc[0]; v_ = g.bc; sd = g.null_sd
            colr, mk = cols[r.role]
            ax.errorbar(v_, yi, xerr=1.96 * sd, fmt=mk, color=colr, ms=6, capsize=3)
        ax.axvline(0, ls="--", color="k", lw=0.8); ax.set_title(t + ("" if f in ("te", "mi_digit") else "\n(conditioned on state S)"), fontsize=10)
        ax.set_xlabel("bits per transition\n(observed minus null mean)", fontsize=9); ax.tick_params(labelsize=9)
    axes[0].set_yticks(y); axes[0].set_yticklabels(labs, fontsize=9)
    from matplotlib.lines import Line2D
    axes[-1].legend([Line2D([], [], marker=m_, ls="", color=c_) for c_, m_ in cols.values()], list(cols), title="cell role", fontsize=9, loc="lower right")
    fig.suptitle("Information carried by prices, per cell (19-20 games and 186-530 firm-round transitions per cell): bias-corrected bits, bars = permutation null +/-1.96 SD", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_price_channel_cells.png"), dpi=110); plt.close(fig)
    slugs = list(dict.fromkeys(cell_label(c)[1] for c in P.cell))
    md.append("\n<!-- LEGEND cells -->\n<small>\n\n**Rows (y-axis):** one cell (arm, model, penalty point, thinking mode; for the copy-bot, the direction of the test). Note: the glossary's short label for ctl-32b-compete says \"(32B)\" because the arm was first run on Qwen3-32B; the gpt-oss row is the same prompt played by gpt-oss-20b.\n\n"
              + AL.legend_table(slugs) + "\n\n**Columns (x-axis), one per panel:** (1) price-move transfer entropy; (2) raw last-digit mutual information; (3)-(6) the four code tests (odd/even cents, last digit, digit 0 or 5, move size) under conditioning set S. All in bits per firm-round transition, observed minus the null mean; the bar is +/-1.96 null SD. Neutral quantities (no collusion direction).\n\n**Colour and marker:** the cell's role: control (blue-grey circle) = the chat arm a treatment is compared with; treatment (purple diamond) = an arm where agreement talk fell; no-chat (orange square) = tacit baseline; negative (grey triangle down) = no hidden channel possible or constant prices; positive (black triangle up) = known information flow (the scripted copier copying the LLM). These role colours are deliberately not red/green.\n\n</small>")

    # ---- price contrasts
    K = pd.read_csv(os.path.join(HERE, "price_contrasts.csv"))
    K = K[K.metric.isin(PMET)].copy(); K["label"] = K.contrast.map(CLAB); K["tlabel"] = K.contrast.map(tlab)
    KP = pd.read_csv(os.path.join(HERE, "price_contrast_perm_v2.csv")).rename(columns={"perm_p_two_sided": "perm_p2"})
    K = K.drop(columns=["perm_p"], errors="ignore").merge(KP[["contrast", "metric", "perm_p2"]], on=["contrast", "metric"], how="left").rename(columns={"perm_p2": "perm_p"})
    K["metric"] = K.metric.map(PMET)
    pm = list(PMET.values())
    md.append("\n<!-- TABLE pcontr -->\n| Contrast | pairs | " + " | ".join(pm) + " |\n|---|---|" + "---|" * len(pm))
    for lab, g in K.groupby("tlabel", sort=False):
        md.append(f"| {lab} | {int(g.n_pairs.iloc[0])} | " + " | ".join(ci(g[g.metric == m].iloc[0]) for m in pm) + " |")
    T = pd.read_csv(os.path.join(HERE, "price_contrasts.csv")); T = T[T.metric == "digit_tvd"]
    md.append("\n<!-- TABLE tvd -->\n| Contrast | total-variation distance between last-digit distributions | arm-swap permutation p |\n|---|---|---|")
    for _, r in T.iterrows():
        md.append(f"| {tlab(r.contrast)} | {r['diff']:.3f} | {r.perm_p:.3f} |")
    CF.forest(K.rename(columns={"diff": "estimate"})[["label", "metric", "estimate", "lo", "hi"]],
              os.path.join(HERE, "fig_price_contrasts_forest.png"),
              title="Price-channel statistics, treatment minus control (95% bootstrap CI over (wording, seed) pairs)", sharex=False)
    md.append("\n<!-- LEGEND pcontr -->\n" + CF.legend_md(K.rename(columns={"diff": "estimate"})))

    # ---- power (v2)
    W = pd.read_csv(os.path.join(HERE, "price_power_v2.csv"))
    fr = sorted(W.fraction.unique())
    PL = {"parity_global": "odd->up / even->down in every game; tested with S", "parity_pergame": "odd/even mapping random per game; tested with S+game", "digit_pergame": "each last digit mapped to a random move, per game; tested with S+game"}
    md.append("\n<!-- TABLE power -->\n| Cell | planted code | " + " | ".join(f"planted in {int(f*100)}% of transitions" for f in fr) + " |\n|---|---|" + "---|" * len(fr))
    for (c, k), g in W.groupby(["cell", "planted"], sort=False):
        md.append(f"| {cell_label(c)[0]} | {PL[k]} | " + " | ".join(f"{g[g.fraction == f].power.iloc[0]:.2f} ({g[g.fraction == f].mean_bc_bits.iloc[0]:+.3f})" for f in fr) + " |")
    md.append("\n<small>\n\n**Terms (power table).** Entry = share of 40 simulations in which the planted code was detected at p < 0.05 (200 within-stratum permutations each); in brackets the mean bias-corrected bits. Planted = in that fraction of the cell's real transitions, the rival's next move is overwritten by the code's prescription. S = price-following state (relative position, both last moves, focal-price flags); S+game = S plus the game id, permuted within game. Cells as in the per-cell table.\n\n</small>")

    # ---- digit entropy (capacity bound)
    m = pd.read_pickle(os.path.join(os.environ.get("SC_DATA", HERE), "market.pkl")) if os.path.exists(os.path.join(os.environ.get("SC_DATA", HERE), "market.pkl")) else None
    if m is not None:
        m["c"] = (m.price * 100).round().astype(int)
        md.append("\n<!-- TABLE entropy -->\n| Cell | quotes above 1.00 | entropy of the last cent digit (bits per quote; 3.32 = uniform) | share ending in 0 |\n|---|---|---|---|")
        for c in P.cell:
            if "->" in c and "bot->llm" in c:
                continue
            parts = c.split("|"); mod = "gpt-oss-20b" if parts[0] == "oss" else "qwen3-32b"
            arm = {"copybot-o150": "copybot-o150-tacit", "copybot-o250": "copybot-o250-tacit"}.get(parts[1], parts[1])
            th = "off" if "t0" in parts else "on"; pp = int([x for x in parts if x.startswith("p")][0][1:]) if any(x.startswith("p") for x in parts[2:]) else 1
            x = m[(m.model == mod) & (m.arm == arm) & (m.thinking == th) & (m.penalty_point == pp) & (m.c > 100)]
            if "copybot" in arm:
                x = x[x.seat == "llm1"]
            d = np.bincount(x.c % 10, minlength=10) / max(len(x), 1); d = d[d > 0]
            md.append(f"| {cell_label(c)[0].split(' [')[0]} [{mod}, {', '.join(parts[2:3])}] | {len(x)} | {max(0.0, -(d * np.log2(d)).sum()):.2f} | {('-' if len(x) == 0 else format((x.c % 10 == 0).mean(), '.2f'))} |")

    # ---- text channel
    A = pd.read_csv(os.path.join(HERE, "text_auc.csv"))
    md.append("\n<!-- TABLE text -->\n| Cell [model] | target | rounds | baseline AUC | raw text: excess (p) | L0 (numbers + agreement verbs removed): excess (p) | L1 (numbers + broad agreement lexicon removed): excess (p) | L2 (also direction words removed): excess (p) | META (length, count, done timing): excess (p) |\n|---|---|---|---|---|---|---|---|---|")
    for (c, tg), g in A.groupby(["cell", "target"], sort=False):
        def e(v):
            r = g[g.variant == v].iloc[0]; return "n/a" if pd.isna(r.excess) else f"{r.excess:+.3f} ({r.p:.2f})"
        md.append(f"| {cell_label(c)[0]} | {tg} | {g.n_rounds.iloc[0]} | {g.auc_base.iloc[0]:.3f} | {e('raw')} | {e('L0')} | {e('L1')} | {e('L2')} | {e('META')} |")
    # forest-style chart of excess with +/-1.96 shuffle SD
    fig, axes = plt.subplots(1, 5, figsize=(21, 0.5 * A.cell.nunique() * 2 + 2), sharey=True, constrained_layout=True)
    rows = list(dict.fromkeys(zip(A.cell, A.target)))
    yl = [textwrap.fill(f"{cell_label(c)[0]} - target: {t}", 50) for c, t in rows]; yy = np.arange(len(rows))[::-1]
    for ax, v in zip(axes, ["raw", "L0", "L1", "L2", "META"]):
        for yi, (c, t) in zip(yy, rows):
            r = A[(A.cell == c) & (A.target == t) & (A.variant == v)].iloc[0]
            if pd.isna(r.excess):
                continue
            sig = r.p <= 0.05
            ax.errorbar(r.excess, yi, xerr=1.96 * r.null_gain_sd, fmt="o", mfc="#5d7a99" if sig else "white", color="#5d7a99", ms=6, capsize=3)
        ax.axvline(0, ls="--", color="k", lw=0.8); ax.tick_params(labelsize=9)
        ax.set_title({"raw": "raw chat text (positive reference)", "L0": "L0: numbers, agreement verbs removed", "L1": "L1: numbers and agreement words removed",
                      "L2": "L2: also price-direction words removed", "META": "META: lengths, counts, done timing"}[v], fontsize=10)
        ax.set_xlabel("AUC gain over baseline, minus shuffled-text gain", fontsize=9)
    axes[0].set_yticks(yy); axes[0].set_yticklabels(yl, fontsize=9)
    fig.suptitle("Does chat text predict the round's price outcome beyond the previous round's prices? (filled = within-game shuffle p <= 0.05; about 150-245 rounds per cell)", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_text_channel.png"), dpi=110); plt.close(fig)
    slugs = list(dict.fromkeys(cell_label(c)[1] for c in A.cell))
    md.append("\n<!-- LEGEND text -->\n<small>\n\n**Rows (y-axis):** one cell and target. Targets: *match* = both firms quote the same half-spread above 1.00 in that round; *cut* = the market price (lowest quote) is below the previous round's.\n\n"
              + AL.legend_table(slugs) + "\n\n**Columns (x-axis), one per panel (text variant):** the cross-validated AUC of baseline + text minus that of the baseline alone, minus the mean of the same gain with the text rows shuffled within game (30 shuffles); the bar is ±1.96 shuffle SD; filled marker = shuffle p <= 0.05. Neutral quantity (no collusion direction).\n\n</small>")
    TP = pd.read_csv(os.path.join(HERE, "text_power.csv"))
    md.append("\n<!-- TABLE tpower -->\n| Cell | planted token in 10% of cut rounds | 20% | 40% |\n|---|---|---|---|")
    for c, g in TP.groupby("cell", sort=False):
        md.append(f"| {cell_label(c)[0]} | " + " | ".join(f"{g[g.planted_fraction_of_cut_rounds == f].power.iloc[0]:.1f} ({g[g.planted_fraction_of_cut_rounds == f].mean_excess.iloc[0]:+.3f})" for f in [0.1, 0.2, 0.4]) + " |")
    TT = pd.read_csv(os.path.join(HERE, "text_top_tokens.csv"))
    md.append("\n<!-- TABLE ttok -->\n| Cell | variant | words most correlated with a cut (r) | words most correlated with no cut (r) |\n|---|---|---|---|")
    for (c, v), g in TT.groupby(["cell", "variant"], sort=False):
        pos = ", ".join(f"{t} ({r_:+.2f})" for t, r_ in zip(g[g.r > 0].token, g[g.r > 0].r))
        neg = ", ".join(f"{t} ({r_:+.2f})" for t, r_ in zip(g[g.r < 0].token, g[g.r < 0].r))
        md.append(f"| {cell_label(c)[0]} | {v} | {pos} | {neg} |")
    O = pd.read_csv(os.path.join(HERE, "text_overt.csv"))
    md.append("\n<!-- TABLE overt -->\n| Cell | chat rounds | rounds whose chat states a price (x.xx) | both firms quote the SAME price and it was stated in that round's chat (observed / chance from another game's chat) | both quotes among the stated prices (loose) | spelled-out price phrases | last-message word count mod 10 = rival's next cent digit (observed / shuffled chance; p) | agreement-lexicon words per round |\n|---|---|---|---|---|---|---|---|")
    for _, r in O.iterrows():
        md.append(f"| {cell_label(r.cell)[0]} | {r.n_rounds} | {r.has_price:.2f} | {r.announced_same:.2f} / {r.announced_same_chance:.2f} | {r.announced_hit:.2f} | {r.has_spelled:.3f} | {r.lenmod_hit:.3f} / {r.lenmod_chance:.3f}; {r.lenmod_p:.2f} | {r.agree_words:.1f} |")
    OC = pd.read_csv(os.path.join(HERE, "text_overt_contrasts.csv")); OC["label"] = OC.contrast.map(CLAB); OC["tlabel"] = OC.contrast.map(tlab)
    OM = {"has_price": "share of chat rounds stating a price", "announced_same": "share of rounds both firms quote the SAME price, stated in that round's chat",
          "announced_hit": "share of rounds both quotes are among the round's stated prices (loose)",
          "agree_words": "words per round from the broad agreement lexicon"}
    OC = OC[OC.metric.isin(OM)].copy(); OC["metric"] = OC.metric.map(OM)
    om = list(OM.values())
    md.append("\n<!-- TABLE ocontr -->\n| Contrast | pairs | " + " | ".join(om) + " |\n|---|---|" + "---|" * len(om))
    for lab, g in OC.groupby("tlabel", sort=False):
        md.append(f"| {lab} | {int(g.n_pairs.iloc[0])} | " + " | ".join(ci(g[g.metric == mm].iloc[0]) for mm in om) + " |")
    CF.forest(OC.rename(columns={"diff": "estimate"})[["label", "metric", "estimate", "lo", "hi"]],
              os.path.join(HERE, "fig_text_overt_forest.png"), title="Overt numbers and length codes in chat, treatment minus control (95% bootstrap CI over pairs)", sharex=False)
    md.append("\n<!-- LEGEND ocontr -->\n" + CF.legend_md(OC.rename(columns={"diff": "estimate"})))

    # ---- keywords and blind readers
    B = pd.read_csv(os.path.join(HERE, "blind_readers.csv"))
    LB = ["ENCODED", "PRICE-SIGNAL", "CONCEALMENT", "NONE"]
    md.append("\n<!-- TABLE blind -->\n| Model | Arm | lexicon-hit items: " + " / ".join(LB) + " | random items: " + " / ".join(LB) + " |\n|---|---|---|---|")
    for (mo, a), g in B.groupby(["model", "arm"]):
        h = g[g.stratum == "hit"].label1.value_counts(); r_ = g[g.stratum == "random"].label1.value_counts()
        md.append(f"| {mo} | {AL.label(a)} | " + " / ".join(str(h.get(k, 0)) for k in LB) + f" (n {int((g.stratum == 'hit').sum())}) | " + " / ".join(str(r_.get(k, 0)) for k in LB) + f" (n {int((g.stratum == 'random').sum())}) |")
    KW = pd.read_csv(os.path.join(HERE, "keyword_rates.csv"))
    piv = KW.pivot_table(index=["model", "arm", "thinking", "penalty_point"], columns="field", values="any")
    pc = KW.pivot_table(index=["model", "arm", "thinking", "penalty_point"], columns="field", values="code")
    fields = ["plan", "rationale", "quote reasoning", "talk reasoning", "chat message"]
    md.append("\n<!-- TABLE kw -->\n| Model | Arm | thinking | penalty point | " + " | ".join(f"{f}: any covert term / code term" for f in fields) + " |\n|---|---|---|---|" + "---|" * len(fields))
    for idx in piv.index:
        md.append(f"| {idx[0]} | {AL.label(idx[1])} | {idx[2]} | p{idx[3]} | " + " | ".join(
            ("-" if pd.isna(piv.loc[idx].get(f)) else f"{piv.loc[idx][f]:.3f} / {pc.loc[idx][f]:.3f}") for f in fields) + " |")
    open(os.path.join(HERE, "tables.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("ok")


if __name__ == "__main__":
    main()
