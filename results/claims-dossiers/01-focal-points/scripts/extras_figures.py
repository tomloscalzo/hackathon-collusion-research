"""Dossier 01 extras: cross-model quote-pattern contrast, payoff-block ladder (salience vs level), two figures.
Usage: python -X utf8 extras_figures.py <dossier_dir> <repo_root>"""
import os, sys
try:
    import psutil
    psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D, REPO = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(REPO, "tools", "analysis_style"))
import arm_labels
sys.path.insert(0, os.path.join(D, "scripts"))
G = pd.read_csv(os.path.join(D, "data", "games.csv"))
L = pd.read_csv(os.path.join(D, "data", "quotes_long.csv.gz"))
T = os.path.join(D, "tables")
RNG = np.random.default_rng(11)
import itertools


def exact_p(d):
    n = len(d); s = np.array(list(itertools.product([1.0, -1.0], repeat=n)), dtype=np.float32)
    return float(np.mean(np.abs(s @ d.astype(np.float32)) / n >= abs(d.mean()) - 1e-9))


def boot(d, B=10000):
    idx = RNG.integers(0, len(d), (B, len(d))); m = d[idx].mean(1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def holm(ps):
    ps = np.asarray(ps); n = len(ps); o = np.argsort(ps); a = np.empty(n); r = 0
    for i, k in enumerate(o):
        r = max(r, min(1, (n - i) * ps[k])); a[k] = r
    return a


# ---- cross-model: gpt-oss minus Qwen (thinking on), same (wording, seed), printed-number headline cells
rows = []
for arm, pp in (("headline-chat", 1), ("headline-chat", 3), ("headline-chat", 5), ("headline-tacit", 1), ("headline-tacit", 5)):
    o = G[(G.model == "gpt-oss-20b") & (G.arm == arm) & (G.penalty_point == pp)].set_index(["wording", "seed"])
    q = G[(G.model == "Qwen3-32B") & (G.run == "qwen_neutral") & (G.arm == arm) & (G.penalty_point == pp) & (G.thinking == "on")].set_index(["wording", "seed"])
    j = o.join(q, lsuffix="_o", rsuffix="_q", how="inner")
    for k in ("q_exact", "q_under1to3", "price_index"):
        d = (j[k + "_o"] - j[k + "_q"]).values
        lo, hi = boot(d)
        rows.append(dict(cell=f"{arm} p{pp}", share=k.replace("q_", ""), n_pairs=len(d), gpt_oss=j[k + "_o"].mean(), qwen_t1=j[k + "_q"].mean(), diff=d.mean(), lo=lo, hi=hi, p_exact=exact_p(d)))
X = pd.DataFrame(rows)
X["p_holm"] = np.nan
for s, idx in X.groupby("share").groups.items():
    X.loc[idx, "p_holm"] = holm(X.loc[idx, "p_exact"].values)
X["family_size"] = 5
X.to_csv(os.path.join(T, "cross_model_quote_pattern.csv"), index=False, float_format="%.4f")
print(X.round(3).to_string())

# ---- payoff-block ladder: price index by what the payoff block prints, p1, thinking on
lad = []
spec = [("none (no numbers)", "nx"), ("formula only", "fx"), ("anchored table (prints 2.09)", "anch"), ("neutral table (prints 1.00 ... 4.00, 2.49/2.50)", "neut")]
for model in ("gpt-oss-20b", "Qwen3-32B"):
    for comm in ("chat", "tacit"):
        for name, code in spec:
            if model == "gpt-oss-20b" and code == "anch":
                continue
            if code in ("nx", "fx"):
                s = G[(G.model == model) & (G.arm == f"{code}-{comm}-p1") & (G.thinking == "on")]
            else:
                run = {"anch": "qwen_anchored", "neut": "qwen_neutral"}[code] if model == "Qwen3-32B" else "2026-10-26_trackm_oss_neutral"
                s = G[(G.model == model) & (G.run == run) & (G.arm == f"headline-{comm}") & (G.penalty_point == 1) & (G.thinking == "on")]
            v = s.price_index.values; lo, hi = boot(v)
            tq = L[L.trial_id.isin(s.trial_id) & (L.model == model) & L.run.isin(s.run.unique()) & L.arm.isin(s.arm.unique())]
            vc = tq.quote.round(2).value_counts(normalize=True).head(3)
            lad.append(dict(model=model, communication=comm, payoff_block=name, n_games=len(v), price_index=v.mean(), lo=lo, hi=hi,
                            avg_abs_spread=s.avg_abs_spread.mean(), profit_gain_index=s.profit_gain_index.mean(),
                            competitive_share=s.competitive_share.mean(), matching_share=s.matching_share.mean(),
                            top_quotes="; ".join("%.2f (%.0f%%)" % (k, 100 * x) for k, x in vc.items())))
LD = pd.DataFrame(lad)
LD.to_csv(os.path.join(T, "payoff_block_ladder.csv"), index=False, float_format="%.4f")
print(LD.round(3).to_string())

# ---- Figure 1: price index by payoff block (p1, thinking on); gpt-oss has no anchored-table run, so its line is broken there
fig, ax = plt.subplots(figsize=(10, 5.6), constrained_layout=True)
xs = {c: i for i, (n, c) in enumerate(spec)}
style = {("gpt-oss-20b", "chat"): ("#1f77b4", "o", "-"), ("gpt-oss-20b", "tacit"): ("#1f77b4", "s", "--"),
         ("Qwen3-32B", "chat"): ("#d62728", "o", "-"), ("Qwen3-32B", "tacit"): ("#d62728", "s", "--")}
for (model, comm), s in LD.groupby(["model", "communication"]):
    codes = [c for n, c in spec if n in set(s.payoff_block)]
    s = s.set_index("payoff_block").loc[[n for n, c in spec if c in codes]]
    col, mk, ls = style[(model, comm)]
    lab = f"{model}, {'private chat' if comm == 'chat' else 'no chat (tacit)'}"
    segs = [codes] if "anch" in codes else [[c for c in codes if c != "neut"], ["neut"]]
    for k, seg in enumerate(segs):
        ss = s[[c in seg for c in codes]]
        x = [xs[c] for c in seg]
        ax.errorbar(x, ss.price_index, yerr=[ss.price_index - ss.lo, ss.hi - ss.price_index], color=col, marker=mk, ls=ls, capsize=3,
                    label=lab if k == 0 else None)
ax.text(xs["anch"], 0.12, "gpt-oss-20b:\nanchored table\nnot run", ha="center", fontsize=9, color="#1f77b4")
ax.set_xticks(range(len(spec)))
ax.set_xticklabels(["none: no numbers,\nno formula\n(nx-chat-p1, nx-tacit-p1)", "formula: equations only,\nno example prices\n(fx-chat-p1, fx-tacit-p1)",
                    "anchored table:\nexamples at 1.54, 2.09, 3.00\n(headline-chat / -tacit)", "neutral table: examples\n1.00 to 4.00, 2.49 / 2.50\n(headline-chat / -tacit)"], fontsize=9.5)
ax.set_ylabel("Price index, mean over games\n(0 = competitive 1.00, 1 = monopoly 3.00)", fontsize=10)
ax.set_xlabel("What the prompt's payoff block prints (left = least printed numeric content)", fontsize=10)
ax.set_ylim(-0.02, 1.0)
ax.set_title("Price index by payoff block, penalty point 1 (fine 100), thinking on (gpt-oss: reasoning effort medium)\n20 games per point (gpt-oss formula-only private-chat cell: 19); bars = 95% bootstrap CI over games", fontsize=10.5)
ax.legend(fontsize=9, loc="upper left")
ax.grid(alpha=0.3)
fig.savefig(os.path.join(D, "fig1_payoff_block_ladder.png"), dpi=150)

# ---- Figure 2: quote histogram, headline-chat p1, both models (thinking on), with an inset around 2.44 to 2.52
fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.0), constrained_layout=True, sharey=True)
bins = np.round(np.arange(0.995, 3.0551, 0.01), 3)
for ax, (model, run, title) in zip(axs, (("gpt-oss-20b", "2026-10-26_trackm_oss_neutral", "gpt-oss-20b (reasoning effort medium)"), ("Qwen3-32B", "qwen_neutral", "Qwen3-32B, thinking on"))):
    q = L[(L.model == model) & (L.run == run) & (L.arm == "headline-chat") & (L.penalty_point == 1) & (L.thinking == "on")].quote.round(2)
    w = np.ones(len(q)) / len(q)
    ax.hist(q.clip(0.995, 3.045), bins=bins, weights=w, color="#555555")
    for p in (1.00, 1.50, 2.00, 2.49, 2.50, 3.00):
        ax.axvline(p, color="#d62728", lw=0.8, ls=":")
    ax.set_title(f"{title}\nheadline-chat: printed example prices, private chat; penalty point 1; n = {len(q)} quotes", fontsize=9.5)
    ax.set_xlabel("Quote (half-spread), 0.01-wide bins; quotes above 3.04 are drawn in the last bin", fontsize=9.5)
    ins = ax.inset_axes([0.05, 0.45, 0.38, 0.45])
    zb = np.round(np.arange(2.435, 2.5251, 0.01), 3)
    ins.hist(q[(q > 2.43) & (q < 2.53)], bins=zb, weights=np.ones(((q > 2.43) & (q < 2.53)).sum()) / len(q), color="#555555")
    ins.set_xticks([2.45, 2.47, 2.49, 2.51]); ins.tick_params(labelsize=8)
    ins.set_title("zoom 2.44 to 2.52", fontsize=8.5)
    ymax = ins.get_ylim()[1]
    for xv, lbl, dx in ((2.49, "on 2.49", -1), (2.50, "on 2.50", 1)):
        share = float((q.round(2) == xv).mean())
        ins.annotate(f"{lbl}: {share:.0%}", (xv, share), xytext=(xv + dx * 0.025, ymax * 0.8), ha="center", fontsize=8.5, color="#d62728",
                     arrowprops=dict(arrowstyle="-", color="#d62728", lw=0.6))
axs[0].set_ylabel("Share of the cell's quotes", fontsize=10)
fig.suptitle("Where quotes land relative to the printed example prices (red dotted lines: printed 1.00, 1.50, 2.00, 2.49, 2.50, 3.00)", fontsize=10.5)
fig.savefig(os.path.join(D, "fig2_quote_histogram_chat_p1.png"), dpi=150)
open(os.path.join(T, "legend_fig1.md"), "w", encoding="utf-8").write(arm_labels.axis_legend(
    cols=["none", "formula", "anchored", "neutral"], col_name="payoff block printed in the prompt",
    panels=["nx-chat-p1", "nx-tacit-p1", "fx-chat-p1", "fx-tacit-p1", "headline-chat", "headline-tacit", "p1", "t1"], panel_name="cells plotted (series: model x communication)",
    metric="price_index"))
open(os.path.join(T, "legend_fig2.md"), "w", encoding="utf-8").write(arm_labels.axis_legend(
    panels=["headline-chat", "neutral", "p1", "t1"], panel_name="cell shown in both panels", metric=None))
open(os.path.join(T, "legend_slugs.md"), "w", encoding="utf-8").write(
    arm_labels.legend_table(["headline-chat", "headline-tacit", "headline-monitored", "fx-chat-p1", "fx-tacit-p1", "fx-chat-p5", "nx-chat-p1", "nx-tacit-p1",
                             "fx-ctl-joint", "ctl-32b-joint", "hrep-fx-chat-p1", "neutral", "anchored", "formula", "none", "p1", "p3", "p5", "t0", "t1"], long=False))
