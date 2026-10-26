"""Figure of the market-structure analysis, drawn from the committed paths_by_round.csv and event_time_paths.csv only.
analyze.py calls fig_market_structure(PB, S); re-render alone with: python -X utf8 figures.py
Labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv via arm_labels);
colours, line styles and scales are unchanged. Returns the plotted values; __main__ checks them against the CSVs."""
import os, sys
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # noqa: E402
L = arm_labels.label
MODE = {"off": "t0", "on": "t1"}


def fig_market_structure(PB, S, path="market_structure.png"):
    """PB: paths_by_round.csv (arm, mode, series, round, value, n_games); S: event_time_paths.csv."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.0)); plotted = []
    col = {"headline-chat": "#444", "n3-group": "#1f77b4", "n3-cheater": "#d95f02"}; ls = {"off": "-", "on": "--"}
    for arm in col:
        for mode in ("off", "on"):
            s = PB[(PB.arm == arm) & (PB["mode"] == mode) & (PB.series == "market_price_index") & (PB.n_games >= 8)]
            plotted.append(("path", arm, mode, list(s["round"]), list(s["value"])))
            axes[0].plot(s["round"], s["value"], ls[mode], color=col[arm], label=f"{L(arm)}; {L(MODE[mode])}")
    axes[0].set_xlabel("round of the game"); axes[0].set_ylabel("market price index (0 = floor, 1 = top)"); axes[0].set_title("Market price index by round (penalty point p3, neutral run; rounds with >= 8 games)\nsolid = t0: thinking off, dashed = t1: thinking on", fontsize=8); axes[0].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=1); axes[0].grid(alpha=.25)
    for mode in ("off", "on"):
        s = S[(S["mode"] == mode) & (S.series == "llm_quote_index") & (S.n_games >= 10)]
        plotted.append(("event", mode, list(s.k), list(s.cheater), list(s.control)))
        axes[1].plot(s.k, s.cheater, ls[mode], color="#d95f02", marker="o", ms=3, label=f"{L('n3-cheater')} (with cheater); {L(MODE[mode])}")
        axes[1].plot(s.k, s.control, ls[mode], color="#1f77b4", marker="o", ms=3, label=f"{L('n3-group')} (matched 3-firm chat); {L(MODE[mode])}")
    axes[1].axvline(0, color="#444", lw=1); axes[1].set_xlabel("rounds since the cheater's defection (0 = defect round)"); axes[1].set_ylabel("mean LLM quote index")
    axes[1].set_title("LLM firms' mean quote index around the cheater's defection\n(points with >= 10 games; quote index = (quote - 1)/2)\n(solid = t0: thinking off, dashed = t1: thinking on)", fontsize=8); axes[1].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=1); axes[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    return plotted


if __name__ == "__main__":
    os.chdir(HERE)
    PB = pd.read_csv("paths_by_round.csv"); S = pd.read_csv("event_time_paths.csv")
    got = fig_market_structure(PB, S)
    for g in got:
        if g[0] == "path":
            _, arm, mode, r, v = g
            e = PB[(PB.arm == arm) & (PB["mode"] == mode) & (PB.series == "market_price_index") & (PB.n_games >= 8)]
            assert r == list(e["round"]) and v == list(e["value"]) and len(v) > 0, (arm, mode)
        else:
            _, mode, k, a, c = g
            e = S[(S["mode"] == mode) & (S.series == "llm_quote_index") & (S.n_games >= 10)]
            assert k == list(e.k) and a == list(e.cheater) and c == list(e.control) and len(k) > 0, mode
    assert len(got) == 8
    print("market-structure: market_structure.png re-rendered; plotted values equal paths_by_round.csv and event_time_paths.csv")
