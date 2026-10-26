"""Targeted analysis 3: thinking on vs off, neutral run. Reaction to being undercut, best-response rate, undercut counts,
penalty response. Usage: STEP1_DIR=<step1 folder> AUDIT_DIR=<folder with firmrounds_neutral.csv> python thinking.py"""
import os, numpy as np, pandas as pd
from common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
AUD = os.environ.get("AUDIT_DIR", "comprehension_audit")
TOL = 0.0051
f = pd.read_csv(os.path.join(AUD, "firmrounds_neutral.csv"))
f[["arm", "pp", "w", "s", "t"]] = f.trial.str.extract(r"^(.*?)__p(\d)__w(\d)__s(\d+)__t(\d)", expand=True)
HEAD = {"headline-tacit": "tacit", "headline-chat": "chat", "headline-monitored": "monitored"}
f = f[f.arm.isin(HEAD)].copy()
f["cond"] = f.arm.map(HEAD); f["wording"] = f.w.astype(int); f["seed"] = f.s.astype(int); f["pp"] = f.pp.astype(int)
f["mode"] = f["mode"].map({"nothink": "off", "think": "on"})
g2 = f[f.own_prev.notna()].copy()                      # rounds with a previous round
g2["undercut_last"] = g2.rival_prev < g2.own_prev - TOL
g2["reduced"] = g2.quote < g2.own_prev - TOL
g2["at_or_below_rival"] = g2.quote <= g2.rival_prev + TOL
g2["br"] = g2.cat == "best_response"
g2["rival_floor"] = g2.rival_prev <= 1.0 + 1e-9
def rate(x, num, den): return x[num].sum() / max(x[den].sum(), 1) if x[den].sum() else np.nan
# --- pair-level metrics (pool the headline cells of a (wording, seed) pair within a mode) ---
rows = []
for (m, w, s), g in g2.groupby(["mode", "wording", "seed"]):
    u = g[g.undercut_last]; nu = g[~g.undercut_last]; nf = g[~g.rival_floor]
    rows.append(dict(mode=m, wording=w, seed=s, events=len(u),
        reduce_after_undercut=u.reduced.mean() if len(u) else np.nan,
        match_or_beat_after_undercut=u.at_or_below_rival.mean() if len(u) else np.nan,
        reduce_when_not_undercut=nu.reduced.mean(),
        best_response_rate=g.br.mean(), best_response_rate_excl_rival_floor=nf.br.mean()))
pm = pd.DataFrame(rows)
run = load_run(); run = run[run.arm.isin(HEAD)].copy(); run["mode"] = run.thinking
rr = run.groupby(["mode", "wording", "seed"]).agg(undercuts_per_game=("undercut_count", "mean"),
        punishments_per_game=("punishment_count", "mean"), gain=("profit_gain_index", "mean"),
        comp_share=("competitive_share", "mean")).reset_index()
pm = pm.merge(rr, on=["mode", "wording", "seed"], how="outer"); pm.to_csv("pair_metrics.csv", index=False)
mets = ["reduce_after_undercut", "match_or_beat_after_undercut", "reduce_when_not_undercut", "best_response_rate",
        "best_response_rate_excl_rival_floor", "undercuts_per_game", "punishments_per_game", "comp_share", "gain"]
rows = []
for k in mets:
    p = pm.pivot_table(index=["wording", "seed"], columns="mode", values=k)
    d = (p["on"] - p["off"]).dropna(); mu, lo, hi = boot_ci(d)
    rows.append(dict(metric=k, off=p["off"].mean(), on=p["on"].mean(), n_pairs=len(d), diff_on_minus_off=mu, lo=lo, hi=hi, p_signflip=signflip_p(d)))
T = pd.DataFrame(rows); T["p_holm"] = holm(T.p_signflip.values); T.to_csv("thinking_contrasts.csv", index=False)
print(T.round(3).to_string())
# --- by communication ---
rows = []
for (m, c), g in g2.groupby(["mode", "cond"]):
    u = g[g.undercut_last]
    rows.append(dict(mode=m, cond=c, undercut_events=len(u), reduce_after_undercut=u.reduced.mean(),
                     match_or_beat=u.at_or_below_rival.mean(), best_response_rate=g.br.mean(), firm_rounds=len(g)))
pd.DataFrame(rows).to_csv("by_communication.csv", index=False); print(pd.DataFrame(rows).round(3).to_string())
# --- penalty response by mode: p5 - p1 slope of several outcomes, pooled over communication ---
rows = []
for m, g in g2.groupby("mode"):
    pass
res = []
for k in ["gain", "undercuts", "reduce", "br"]:
    for m in ["off", "on"]:
        if k == "gain": q = run[run["mode"] == m].pivot_table(index=["wording", "seed"], columns="penalty_point", values="profit_gain_index")
        elif k == "undercuts": q = run[run["mode"] == m].pivot_table(index=["wording", "seed"], columns="penalty_point", values="undercut_count")
        elif k == "reduce": q = g2[(g2["mode"] == m) & g2.undercut_last].pivot_table(index=["wording", "seed"], columns="pp", values="reduced")
        else: q = g2[g2["mode"] == m].pivot_table(index=["wording", "seed"], columns="pp", values="br")
        d = (q[5] - q[1]).dropna(); mu, lo, hi = boot_ci(d)
        res.append(dict(outcome=k, mode=m, n_pairs=len(d), p1=q[1].mean(), p5=q[5].mean(), slope_p5_minus_p1=mu, lo=lo, hi=hi, p_signflip=signflip_p(d)))
P = pd.DataFrame(res); P.to_csv("penalty_response_by_mode.csv", index=False); print(P.round(3).to_string())
# --- figure ---
fig, ax = plt.subplots(1, 3, figsize=(12, 5.2))
YL = {"reduce_after_undercut": "Share of undercut firm-rounds in which the firm cut its quote\n(0 to 1; mean over 20 pairs)",
      "best_response_rate": "Share of firm-rounds at the one-round profit-maximising quote\n(0 to 1; mean over 20 pairs)",
      "undercuts_per_game": "Undercuts per game (count of rounds where a firm quoted below\nboth the rival's previous quote and its own; mean over 20 pairs)"}
for i, (k, t) in enumerate([("reduce_after_undercut", "A. Cut price after being undercut"), ("best_response_rate", "B. At the best response"), ("undercuts_per_game", "C. Undercuts per game")]):
    r = T[T.metric == k].iloc[0]
    for j, m in enumerate(["off", "on"]):
        v = pm[pm["mode"] == m][k].dropna(); mu, lo, hi = boot_ci(v)
        ax[i].errorbar(j, mu, yerr=[[mu - lo], [hi - mu]], fmt="o", color=["#1f77b4", "#d95f02"][j], capsize=4,
                       label=["thinking off (t0): mean and 95% CI", "thinking on (t1): mean and 95% CI"][j])
    ax[i].set_xticks([0, 1]); ax[i].set_xticklabels(["thinking off (t0)", "thinking on (t1)"]); ax[i].set_xlim(-.5, 1.5); ax[i].set_title(t, fontsize=10); ax[i].grid(alpha=.3)
    ax[i].set_ylabel(YL[k], fontsize=7.5); ax[i].set_xlabel("Qwen3-32B reasoning mode", fontsize=8)
h, l = ax[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, fontsize=8, frameon=False)
fig.suptitle("Neutral run, headline arms (tacit, private chat, monitored), penalty points 1/3/4/5: how thinking-off and thinking-on firms react to being undercut\n(12 cells x 20 games per mode; bars = 95% paired bootstrap CI over the 20 (wording, seed) pairs)", fontsize=9)
plt.tight_layout(rect=(0, 0.07, 1, 0.92)); plt.savefig("fig_thinking.png", dpi=130)
# --- cross-check vs audit pooled T4a (all arms) ---
print(open(os.path.join(AUD, "T4a_response_to_undercut_neutral.csv")).read())
