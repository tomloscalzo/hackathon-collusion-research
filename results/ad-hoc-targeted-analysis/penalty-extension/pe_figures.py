"""Figures for the penalty-extension report (reads the CSVs written by pe_analysis.py; run from any folder).

  fig_penalty_curves.png         price index against the fine (log axis), one panel per model x objective: observed cell
                                 means with 95% CIs, theory curves overlaid (fine-aware cartel price theta*, fine-aware joint
                                 optimum, one-shot best response = static Nash = 1.00, and the fine-aware best response to a
                                 rival at 2.50 when the theory file has it)
  fig_penalty_curves_all5.png    the five metrics against the fine, one row per metric, colour = model x objective
  fig_forest_vs500_<model>.png   CI forest chart under the "each fine minus fine 500" delta table, per model
  fig_forest_steps_<model>.png   CI forest chart under the "adjacent fine steps" delta table, per model
  fig_forest_gap_<model>.png     observed price index minus the primary theory benchmark, per objective and fine
"""
import os as _os, pathlib as _pl; _ROOT = _os.environ.get("COLLUSION_WORK_ROOT") or next((str(q) for q in _pl.Path(__file__).resolve().parents if (q / "runs").is_dir()), "..")  # the work directory holding runs/ and work_scratch/
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels as AL  # noqa: E402
import ci_forest  # noqa: E402

THEORY = os.environ.get("PE_THEORY", os.path.join(os.path.dirname(os.path.abspath(__file__)), "theory_by_fine.csv"))

_PE_LBL = {"headline-chat": "headline-chat: default objective, maximise own profit", "ctl-32b-joint": "ctl-32b-joint: told to maximise joint profit",
           "m-inc-joint": "m-inc-joint: told to maximise joint profit (same prompt; stopped early, biased)", "m-inc-target": "m-inc-target: profit-target pressure"}
_SHORT = {"headline-chat": "headline-chat: own profit", "ctl-32b-joint": "ctl-32b-joint: joint profit", "m-inc-joint": "m-inc-joint: joint profit (biased)", "m-inc-target": "m-inc-target: profit target"}
def _pe_label(slug, _orig=None): return _PE_LBL.get(slug) or AL.label(slug)
METRICS = [("market_price_mean", "Average absolute spread"), ("price_index", "Price index"),
           ("profit_gain_index", "Profit gain index"), ("competitive_share", "Competitive share"),
           ("matching_share", "Matching share")]
PANELS = [("gpt-oss-20b", "headline-chat"), ("gpt-oss-20b", "ctl-32b-joint"), ("gpt-oss-20b", "m-inc-joint"),
          ("gpt-oss-20b", "m-inc-target"), ("Qwen3-32B", "headline-chat"), ("Qwen3-32B", "ctl-32b-joint")]
FINES = [100, 500, 1000, 2000, 2500, 10000]
plt.rcParams.update({"font.size": 10})


def theory():
    if not os.path.exists(THEORY):
        return None
    T = pd.read_csv(THEORY).sort_values("fine")
    if "fine_aware_br_to_2.50" in T:
        T["idx_br_to_250"] = ((T["fine_aware_br_to_2.50"] - 1) / 2).clip(0, 1)
    return T


def curves(CM, T):
    fig, axes = plt.subplots(2, 4, figsize=(17, 8.6), sharey=True, constrained_layout=True)
    axes = axes.ravel()
    for ax, (model, arm) in zip(axes, PANELS):
        d = CM[(CM.model == model) & (CM.arm == arm)].sort_values("fine")
        if T is not None:
            ax.plot(T.fine, T.idx_theta_star, color="#7d3c98", lw=2, label="theory: fine-aware cartel price θ* (own profit, self-enforcing)")
            ax.plot(T.fine, T.idx_joint_opt, color="#2e86c1", lw=1.6, ls="--", label="theory: fine-aware joint-profit optimum\n(coincides with θ* to the 0.01 grid)")
            if "idx_static_nash" in T:
                ax.plot(T.fine, T.idx_static_nash, color="#1e8449", lw=1.4, ls=":", label="theory: one-shot best response (static Nash, 1.00)")
            if "idx_br_to_250" in T:
                ax.plot(T.fine, T.idx_br_to_250, color="#d68910", lw=1.2, ls="-.", label="theory: fine-aware best response to a rival at 2.50")
        if len(d):
            yerr = np.vstack([d.price_index_mean - d.price_index_lo, d.price_index_hi - d.price_index_mean])
            ax.errorbar(d.fine, d.price_index_mean, yerr=yerr, fmt="o-", color="#c0392b", ms=6, capsize=3, lw=1.6,
                        label="observed mean price index, 95% CI")
            for _, r in d.iterrows():
                ax.annotate(f"n={int(r.n_games)}", (r.fine, r.price_index_hi), textcoords="offset points", xytext=(0, 5),
                            ha="center", fontsize=8, color="#444")
        ax.set_xscale("log")
        ax.set_xticks(FINES)
        ax.set_xticklabels(["100\n(p1)", "500\n(p3)", "1,000\n(p4=x10)", "2,000\n(p5)", "\n\n2,500 (x25)", "10,000\n(x100)"], fontsize=8)
        ax.minorticks_off()
        ax.set_ylim(-0.05, 1.08)
        ax.grid(alpha=0.3)
        ax.set_title(f"{model}\n{_pe_label(arm)}", fontsize=9.5)
        ax.set_xlabel("Fine per firm on a finding (log scale)")
    for ax in axes[len(PANELS):]:
        ax.axis("off")
    axes[0].set_ylabel("Price index (0 = competitive 1.00, 1 = monopoly 3.00)")
    axes[4].set_ylabel("Price index (0 = competitive 1.00, 1 = monopoly 3.00)")
    h, l = axes[0].get_legend_handles_labels()
    axes[-1].legend(h, l, loc="center", fontsize=9, frameon=False, title="Legend")
    fig.suptitle("Penalty-response curves: market price index against the fine, by model and objective "
                 "(neutral payoff table, private chat, reasoning on)", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_penalty_curves.png"), dpi=120)
    plt.close(fig)


def curves_all5(CM):
    fig, axes = plt.subplots(1, 5, figsize=(21, 4.8), constrained_layout=True)
    cols = plt.get_cmap("tab10")
    for ax, (m, lab) in zip(axes, METRICS):
        for k, (model, arm) in enumerate(PANELS):
            d = CM[(CM.model == model) & (CM.arm == arm)].sort_values("fine")
            if not len(d):
                continue
            ax.errorbar(d.fine * (1 + 0.03 * (k - 2.5)), d[f"{m}_mean"],
                        yerr=np.vstack([d[f"{m}_mean"] - d[f"{m}_lo"], d[f"{m}_hi"] - d[f"{m}_mean"]]),
                        fmt="o-", ms=4, capsize=2, lw=1.2, color=cols(k), label=f"{model}, {_pe_label(arm)}")
        ax.set_xscale("log"); ax.set_xticks(FINES); ax.set_xticklabels(["100", "500", "1k", "2k", "2.5k", "10k"]); ax.minorticks_off()
        ax.set_title(lab); ax.set_xlabel("Fine (log scale)"); ax.grid(alpha=0.3)
        ax.set_ylabel(lab + (" (half-spread, 1.00 to 5.00)" if m == "market_price_mean" else " (0 to 1)"))
    axes[-1].legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, title="Model, objective arm")
    fig.suptitle("The five standard metrics against the fine (cell means, 95% CI; points offset slightly for legibility)", fontsize=11)
    fig.savefig(os.path.join(HERE, "fig_penalty_curves_all5.png"), dpi=110)
    plt.close(fig)


def forests(CT, RA):
    for model in ["gpt-oss-20b", "Qwen3-32B"]:
        tag = "oss" if model.startswith("gpt") else "qwen"
        for fam, name, what in [("V: vs fine 500 (p3)", "vs500", "each fine minus fine 500 (p3)"),
                                ("S: adjacent fine steps", "steps", "each fine minus the next lower fine")]:
            d = CT[(CT.family == fam) & (CT.model == model)]
            rows = []
            for _, r in d.iterrows():
                for m, lab in METRICS:
                    if pd.notna(r[f"{m}_d"]):
                        rows.append({"label": r.contrast, "metric": lab, "estimate": r[f"{m}_d"], "lo": r[f"{m}_lo"],
                                     "hi": r[f"{m}_hi"], "p": r.get(f"{m}_holm")})
            if rows:
                ci_forest.forest(rows, os.path.join(HERE, f"fig_forest_{name}_{tag}.png"),
                                 title=f"{model}: paired change, {what}; centroid and 95% bootstrap CI over (wording, seed) pairs",
                                 xlabel="paired difference")
        d = RA[RA.model == model]
        rows = []
        for _, r in d.iterrows():
            pc = r.primary_used
            if isinstance(pc, str) and pd.notna(r.get(f"gap_{pc}")):
                bench = "θ*" if pc == "idx_theta_star" else "joint optimum"
                rows.append({"label": f"{_SHORT.get(r.arm, r.arm)}, fine {int(r.fine):,}", "metric": "Price index minus theory",
                             "estimate": r[f"gap_{pc}"], "lo": r[f"gap_{pc}_lo"], "hi": r[f"gap_{pc}_hi"]})
        if rows:
            ci_forest.forest(rows, os.path.join(HERE, f"fig_forest_gap_{tag}.png"),
                             title=f"{model}: observed price index minus the rational benchmark (> 0: prices above what the fine makes optimal)",
                             xlabel="price index minus theory (index units)")


def main():
    CM = pd.read_csv(os.path.join(HERE, "cell_means.csv"))
    CT = pd.read_csv(os.path.join(HERE, "contrasts.csv"))
    RA = pd.read_csv(os.path.join(HERE, "rationality.csv"))
    T = theory()
    curves(CM, T)
    curves_all5(CM)
    forests(CT, RA)
    print("figures written")


if __name__ == "__main__":
    main()
