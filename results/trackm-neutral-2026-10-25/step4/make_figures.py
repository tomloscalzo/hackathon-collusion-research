"""Step 4 figures. Run from this folder: python -X utf8 make_figures.py [--orig] (reads data/, writes figures/).
Arm and code labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_labels.py); --orig draws
the earlier labels (the data path then reproduces the earlier PNGs byte for byte). Values come from data/*.csv unchanged.
$REPLOT_OUT overrides the output folder."""
import sys, os, textwrap
from pathlib import Path
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "analysis_style"))
import arm_labels as AL  # noqa: E402
ORIG = "--orig" in sys.argv
OUTF = os.environ.get("REPLOT_OUT", "figures")


def L(slug, wrap=24):
    return textwrap.fill(AL.label(slug), wrap)


BL, OR, GR, INK = "#2a6fb0", "#d9731a", "#8a8f98", "#222222"
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888", "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK})


def save(fig, name):
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(f"{OUTF}/{name}.png", dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def bars(name, labels, vals, los, his, colors, ylabel, title, ylim, note):
    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    v = [x * 100 for x in vals]; lo = [x * 100 for x in los]; hi = [x * 100 for x in his]
    ax.bar(labels, v, color=colors, width=0.55)
    ax.errorbar(range(len(v)), v, yerr=[[a - b for a, b in zip(v, lo)], [b - a for a, b in zip(v, hi)]],
                fmt="none", ecolor=INK, capsize=5, lw=1.5)
    for i, x in enumerate(v):
        ax.text(i, hi[i] + ylim[1] * 0.03, f"{x:.1f}%", ha="center", fontweight="bold")
    ax.set_ylabel(ylabel); ax.set_title(title, fontsize=11, loc="left"); ax.set_ylim(*ylim)
    fig.text(0.01, 0.005, note, fontsize=8.5, color="#555")
    save(fig, name)


def dots(name, labels, vals, los, his, colors, xlabel, title, xlim, note, signed):
    fig, ax = plt.subplots(figsize=(7.4, 1.9 + 0.6 * len(labels)))
    ys = list(range(len(labels)))[::-1]
    for y, v, lo, hi, c in zip(ys, vals, los, his, colors):
        ax.plot([lo, hi], [y, y], color=c, lw=2.5); ax.plot(v, y, "o", color=c, ms=10)
        ax.text(v, y + 0.2, f"{v:+.2f}" if signed else f"{v:.2f}", ha="center", fontweight="bold", fontsize=11)
    if signed:
        ax.axvline(0, color="#888", lw=1)
    else:
        ax.axvline(0.5, color="#888", lw=1, ls="--", label="chance (AUC = 0.5)"); ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.set_yticks(ys); ax.set_yticklabels(labels); ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11, loc="left"); ax.set_ylim(-0.6, len(labels) - 0.2); ax.set_xlim(*xlim)
    fig.text(0.01, 0.005, note, fontsize=8.5, color="#555")
    save(fig, name)


# 1.1 and 3.1: competitive share
arms = pd.read_csv("data/competitiveness_neutral_arms.csv"); arms = arms[arms.group == "arm"].set_index("arm")
t, c = arms.loc["headline-tacit"], arms.loc["headline-chat"]
bars("fig_1_1_chat_competitive", ["No chat\n(tacit)", "Private chat"] if ORIG else [L("headline-tacit"), L("headline-chat")], [t.comp_share, c.comp_share],
     [t.ci_lo, c.ci_lo], [t.ci_hi, c.ci_hi], [BL, OR], "Competitive firm-rounds\n(% of scored firm-rounds)",
     "Competitive share of firm-rounds, neutral run\nno chat vs private chat, both thinking modes pooled, 160 games per bar", (0, 48),
     "Chat minus no chat: -28.0 pp [-33.6, -22.2]. Neutral run, 95% CI over 20 paired units.")
j, k = arms.loc["ctl-32b-joint"], arms.loc["ctl-32b-compete"]
bars("fig_3_1_tacit_vs_controls", ["Told to\ncompete", "No chat\n(tacit)", "Told to maximise\njoint profit"] if ORIG else [L("ctl-32b-compete", 20), L("headline-tacit", 20), L("ctl-32b-joint", 20)],
     [k.comp_share, t.comp_share, j.comp_share], [k.ci_lo, t.ci_lo, j.ci_lo], [k.ci_hi, t.ci_hi, j.ci_hi],
     [GR, BL, GR], "Competitive firm-rounds\n(% of scored firm-rounds)", "Competitive share of firm-rounds, neutral run\nno chat (160 games) between the strict-compete and maximise-joint-profit controls", (0, 118),
     "Neutral run. Without a text channel firms fail to undercut in 66.3% of firm-rounds.")

# 1.2 and 1.5 from the lever table
L = pd.read_csv("data/levers_neutral.csv")
L = L[L.outcome == "price_index"].set_index(["id", "mode"])


def lv(i, m):
    r = L.loc[(i, m)]
    return r["diff"], r.ci_lo, r.ci_hi


ch = [lv("cheater", "off"), lv("cheater", "on")]
dots("fig_1_2_cheater", ["Thinking off", "Thinking on"] if ORIG else [AL.label("t0"), AL.label("t1")], [x[0] for x in ch], [x[1] for x in ch], [x[2] for x in ch],
     [BL, OR], ("Paired difference in price index:\n3 firms + planted defector minus 3-firm group chat" if ORIG else "Paired difference in price index (price_index):\nn3-cheater (3 firms + planted defector) minus n3-group (3-firm group chat), p3"), "Planted defector in a 3-firm cartel, neutral run\nprice index, 20 (wording, seed) pairs per thinking mode", (-0.5, 0.1),
     "Price index: 0 = competitive 1.00, 1 = monopoly 3.00. 20 paired units, 95% CI.", True)
five = {m: lv("5tick", m) for m in ("off", "on")}
late = {"off": (-0.332, -0.527, -0.106), "on": (-0.459, -0.584, -0.331)}  # rounds 5+, FINAL_NUMBERS.md (fivetick.csv)
v = [five["off"], late["off"], five["on"], late["on"]]
dots("fig_1_5_fivetick", ["Thinking off, all rounds", "Thinking off, rounds 5+", "Thinking on, all rounds",
                          "Thinking on, rounds 5+"] if ORIG else ["t0: thinking off, all rounds", "t0: thinking off, rounds 5+",
                                                                  "t1: thinking on, all rounds", "t1: thinking on, rounds 5+"],
     [x[0] for x in v], [x[1] for x in v], [x[2] for x in v], [BL, BL, OR, OR],
     ("Paired difference in price index:\n5-tick start minus headline private chat" if ORIG else "Paired difference in price index (price_index):\nstart-5tick (5-tick start) minus headline-chat (private chat), p3"), "5-tick start (round-1 quotes capped at 1.05), neutral run\nprice index, 20 (wording, seed) pairs per thinking mode", (-0.78, 0.1),
     "20 paired units (18 and 16 with a round 5+). 95% CI.", True)

# 1.3 and 2.2: frozen-threshold detection
D = pd.read_csv("data/detect_frozen_neutral_results.csv")
D = D[(D.split == "seed-primary") & (D.label == "c_outcome") & (D.rule == "youden")].set_index("detector")


def auc(keys):
    return ([D.loc[k].test_auc for k in keys], [D.loc[k].auc_lo for k in keys], [D.loc[k].auc_hi for k in keys])


a = auc(["text: rules score", "quotes: mean level"])
dots("fig_1_3_detector", ["Keyword rules\n(old detector)", "Early quotes,\nfrozen threshold"], *a, [GR, BL],
     "AUC (area under the ROC curve) on held-out games", "Detecting games that later reach high prices from rounds 1-3, neutral run\n145 held-out games; two detectors", (0.2, 1.0),
     "Fit on 10 seed-pairs, tested on the other 10 (145 games). 95% CI.", False)
a = auc(["text: TF-IDF + LR", "quotes: mean level", "both: quotes + TF-IDF + LR"])
dots("fig_2_2_combine", ["Chat text alone", "Quotes alone", "Text + quotes"], *a, [GR, BL, OR],
     "AUC (area under the ROC curve) on held-out games", "Detecting later high prices from rounds 1-3, neutral run\nchat text vs quotes vs both; 145 held-out games", (0.4, 1.02),
     "Same frozen split. Text + quotes minus quotes: -0.001 [-0.025, +0.041].", False)

# 3.4: watched coalition
C = pd.read_csv("data/channel_shift_results.csv")
C = C[C.measure.isin(["agree", "matching", "price_index"]) & C.comparison.str.startswith("CoT")]
names = ({"price_index": "Price index", "agree": "Agreement in chat", "matching": "Quote matching"} if ORIG else
         {"price_index": AL.label("price_index"), "agree": "agree: agreement in chat\n(keyword measure)", "matching": AL.label("matching_share")})
ys = {"price_index": 2, "agree": 1, "matching": 0}
fig, ax = plt.subplots(figsize=(7.4, 4.3))
TA = "Threat A (permits trying out different quotes on your own)" if ORIG else "d-cot-monitor-a: threat A (permits trying out different quotes on your own)"
TB = "Threat B (permits maximising own profit while quoting lower)" if ORIG else "d-cot-monitor-b: threat B (permits maximising own profit while quoting lower)"
for comp, col, lbl, dy in (("CoT threat A vs headline-chat, p1", BL, TA, -0.13),
                           ("CoT threat B vs headline-chat, p1", OR, TB, 0.13)):
    for _, r in C[C.comparison == comp].iterrows():
        y = ys[r.measure] + dy
        ax.plot([r.ci_lo, r.ci_hi], [y, y], color=col, lw=2.5)
        ax.plot(r.delta, y, "o", color=col, ms=9, label=lbl if r.measure == "price_index" else None)
ax.axvline(0, color="#888", lw=1)
ax.set_yticks([2, 1, 0]); ax.set_yticklabels([names[x] for x in ("price_index", "agree", "matching")])
ax.set_xlabel("Paired difference: threat arm minus headline private chat at point 1\n(price index; agreement in chat; matching share)" if ORIG else
              "Paired difference: threat arm minus headline-chat (private chat) at p1, t1 (thinking on)\n(price index; agreement in chat; matching share)"); ax.set_xlim(-0.65, 0.1)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.36), fontsize=9)
ax.set_title("Idle reasoning-monitor threat (no monitor exists), neutral run, thinking on only\nthree outcomes, 20 (wording, seed) pairs per threat text", fontsize=11, loc="left")
fig.text(0.01, 0.005, "20 paired units, 95% CI. Dot = mean paired difference; bar = 95% interval; negative = fell. Talk and actions fall together: no hidden-channel shift.",
         fontsize=8.5, color="#555")
save(fig, "fig_3_4_watched")
print("ok")
