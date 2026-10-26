"""Markdown tables and legend blocks for ANALYSIS.md (printed to stdout as named snippets).

Run: python pg_tables.py > tables_snippets.md   (the report pastes these snippets verbatim)
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402

MK = ["market_price_mean", "price_index", "profit_gain_index", "competitive_share", "matching_share"]
HDR = "| Model, mode | Contrast | n pairs | Average absolute spread | Price index | Profit gain index | Competitive share (U16) | Matching share |"
SEP = "|---|---|---|---|---|---|---|---|"


def f(r, m):
    s = f"{r[m + '_d']:+.2f} [{r[m + '_lo']:+.2f}, {r[m + '_hi']:+.2f}]"
    if r.get(m + "_holm", 1) < 0.05:
        s = f"**{s}**"
    return s


def table(df, theory=False):
    hdr, sep = HDR, SEP
    if theory:
        hdr += " Theory: spread / price index / gain |"
        sep += "---|"
    out = [hdr, sep]
    for _, r in df.iterrows():
        row = f"| {r['model']}, {r['mode']} | {r['contrast']} | {int(r['n_pairs'])} | " + " | ".join(f(r, m) for m in MK) + " |"
        if theory:
            row += f" {r['market_price_mean_theory']:+.2f} / {r['price_index_theory']:+.2f} / {r['profit_gain_index_theory']:+.2f} |"
        out.append(row)
    return "\n".join(out)


def main():
    R = pd.read_csv(os.path.join(HERE, "contrasts.csv"))
    print("<!-- S -->")
    print(table(R[R.family == "S: p5 - p1 slopes"], theory=True))
    print("<!-- STEPS -->")
    print(table(R[R.family == "S-steps: adjacent-step slopes"], theory=True))
    print("<!-- I -->")
    print(table(R[R.family == "I: slope interactions"]))
    print("<!-- O -->")
    print(table(R[R.family.str.startswith("O")]))
    print("<!-- C -->")
    print(table(R[R.family.str.startswith("C")]))
    H = pd.read_csv(os.path.join(HERE, "heed_coefficients.csv"))
    print("<!-- HEED -->")
    print("| Model, mode | Chain (payoff, communication) | Points | n pairs | β spread | β price index | β profit gain index | β competitive share | β matching share | Proportional response 1 - PI(p5)/PI(p1) | Per unit θ*: first step / last step / last - first [CI], p |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")

    def b(r, m):
        return f"{r['beta_' + m]:+.2f} [{r['beta_' + m + '_lo']:+.2f}, {r['beta_' + m + '_hi']:+.2f}]"
    for _, r in H.iterrows():
        e = ""
        if pd.notna(r.get("heed_early")):
            e = (f"{r.early_step}: {r.heed_early:+.2f}; {r.late_step}: {r.heed_late:+.2f}; "
                 f"{r.heed_late_minus_early:+.2f} [{r.heed_late_minus_early_lo:+.2f}, {r.heed_late_minus_early_hi:+.2f}], p {r.heed_late_minus_early_p:.3f}")
        ch = r.chain.replace("@anchored", "")
        print(f"| {r.model}, {r['mode']} | {ch} ({r.payoff}, {r.communication}) | {r.points} | {int(r.n_pairs)} | "
              + " | ".join(b(r, m) for m in MK)
              + f" | {r.prop:.2f} [{r.prop_lo:.2f}, {r.prop_hi:.2f}] | {e or 'only two points'} |")
    C = pd.read_csv(os.path.join(HERE, "cell_means.csv"))
    keep = ["headline-tacit", "headline-chat", "headline-monitored", "fx-chat-p1", "fx-chat-p5", "ctl-32b-joint",
            "m-inc-joint", "m-inc-target", "fx-ctl-joint", "ctl-32b-compete"]
    C = C[C.arm.isin(keep)].copy()
    C["arm"] = pd.Categorical(C.arm, keep)
    C = C.sort_values(["model", "mode", "payoff_examples", "arm", "penalty_point"])
    print("<!-- CELLS -->")
    print("| Model, mode | Arm | Payoff block | Communication | Penalty point | θ* | n games | Average absolute spread | Price index | Profit gain index | Competitive share (U16) | Matching share |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in C.iterrows():
        print(f"| {r.model}, {r['mode']} | {arm_labels.label(r.arm)} | {r.payoff_examples} | {r.communication} | p{r.penalty_point} | "
              f"{r.theta_star:.2f} | {int(r.price_index_count)} | {r.market_price_mean_mean:.2f} | {r.price_index_mean:.2f} | "
              f"{r.profit_gain_index_mean:.2f} | {r.competitive_share_mean:.2f} | {r.matching_share_mean:.2f} |")
    print("<!-- LEGEND_ARMS -->")
    print(arm_labels.legend_table(keep + ["anchored", "fx-chat", "gpt-oss-20b", "Qwen3-32B", "theta_star", "p1", "p3", "p4", "p5",
                                          "t0", "t1", "neutral", "formula", "tacit", "private", "monitored", "pair"], long=True))
    print("<!-- AXIS_FOREST -->")
    print(arm_labels.axis_legend(rows=["headline-tacit", "headline-chat", "headline-monitored", "fx-chat", "fx-ctl-joint",
                                       "ctl-32b-joint", "m-inc-joint", "m-inc-target", "gpt-oss-20b", "Qwen3-32B", "t0", "t1",
                                       "p1", "p3", "p4", "p5"],
                                 panels=["abs_spread", "price_index", "profit_gain_index", "competitive_share", "matching_share"],
                                 row_name="contrast = model, thinking mode, arm and penalty points compared",
                                 panel_name="metric (x-axis: the paired difference in that metric's units)", long=False))
    print("<!-- AXIS_CURVES -->")
    print(arm_labels.axis_legend(rows=["price_index", "profit_gain_index"], cols=["p1", "p3", "p4", "p5", "theta_star"],
                                 panels=["Qwen3-32B", "gpt-oss-20b", "t0", "t1"],
                                 row_name="the metric on the y-axis (top row, bottom row)",
                                 col_name="penalty point", panel_name="model and thinking mode", long=False))
    print("<!-- SERIES_CURVES -->")
    print(arm_labels.legend_table(["headline-tacit", "headline-chat", "headline-monitored", "fx-chat", "ctl-32b-joint",
                                   "m-inc-joint", "m-inc-target", "fx-ctl-joint", "theta_star"], long=False))


if __name__ == "__main__":
    main()
