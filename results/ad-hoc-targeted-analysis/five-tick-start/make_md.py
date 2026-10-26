"""Assemble ANALYSIS.md. usage: python -X utf8 make_md.py"""
import pandas as pd, common as c
W = pd.read_csv("five_tick_windows.csv"); W["diff [95% CI]"] = W.apply(c.ci_str, axis=1)
P = pd.read_csv("paths_by_round.csv"); CL = pd.read_csv("climb_back.csv")
sel = [1, 2, 3, 5, 8, 10, 15]
pp = P[P["round"].isin(sel)].copy(); pp["cell"] = pp.price_index.map("{:.2f}".format) + " (n=" + pp.n_games.astype(str) + ")"
pp = pp.pivot_table(index=["thinking", "round"], columns="arm", values="cell", aggfunc="first").reset_index()[["thinking", "round", "start-5tick", "headline-chat"]]
HEAD = """# 5-tick start vs private chat: a one-round cap that does not wash out

Created by Claude at the prompting of the repository owner. Code: `analyze.py`, `make_md.py`, `common.py`. Data: neutral run `steps/neutral/step1` (rounds table for paths and windows), anchored run (game-level check plus the provisional extras file, copied here as `fivetick_provisional.csv`; source `analysis_final/out_provisional/extras/fivetick.csv`). Numbers: `five_tick_windows.csv`, `paths_by_round.csv`, `climb_back.csv`. Contrast: `start-5tick` vs `headline-chat`, both penalty point 3, paired on (wording, seed) within thinking mode.

## Verdict

The 5-tick start (round-1 quotes capped to 1.00-1.05, i.e. within 5 ticks of the floor) **lowers prices by a large and lasting amount, and the effect is not a round-1 artefact.** Price index, neutral run: -0.40 [-0.57, -0.20] (thinking off) and -0.56 [-0.66, -0.46] (on) over all rounds. **Excluding round 1** it is -0.37 [-0.55, -0.16] (off) and -0.55 [-0.66, -0.44] (on): essentially unchanged. **In rounds 5+** it is -0.33 [-0.53, -0.12] (off, 18 pairs) and -0.48 [-0.60, -0.34] (on, 15 pairs); in rounds 10+ it is still -0.45 [-0.65, -0.24] (off, 12 pairs) and -0.39 [-0.56, -0.20] (on, 9 pairs). The anchored run gives the same (-0.42 and -0.35 all rounds; -0.41 and -0.34 in rounds 5+). Even the least favourable bound (CI upper end) is a drop of 0.12 in rounds 5+, so the effect is far above the minimum detectable effect of 0.15-0.25 at its point estimate.

**Do firms climb back up? Only partly and slowly.** Round 2 is already 0.22 (off) and 0.07 (on) against controls of 0.62 and 0.78: the cap is carried forward, not forgotten. With thinking off the price index drifts only from about 0.22 (rounds 2-5) to 0.24 (rounds 6+) and the game-average path is 0.13-0.19 in rounds 8-15 (a shrinking set of games, so not a fall in any one game); 7 of 20 games (35%) ever reach a market price of 2.00 (index 0.5) after round 1, against 18 of 20 (90%) in private chat, and only 1 of 20 reaches 0.8. With thinking on there is a steady climb, from 0.07 in round 2 to 0.16 in round 5, 0.28 by round 10 and 0.31 by round 15 (the later rounds have fewer games, 7-13), but 5 of 19 games (26%) ever reach 0.5 against all 20 controls, and none reaches 0.8. So a first-round anchor near the floor is partly eroded by the chat (thinking on) but nowhere near closed within 20 rounds. These later-round paths are based on 10-13 games, so the shape is indicative.

![price paths](five_tick.png)

Figure: market price index by round, mean over games, rounds with at least 8 games (neutral run).

## Tables

### Price index by window, arm minus control (95% CI over pairs)

"""
TAIL = "\n\nThe neutral all-rounds figures here come from the rounds table and differ in the third decimal from the provisional extras file (which drops imputed rounds). `anchored (provisional file)` rows are copied from that file; the anchored data set has no rounds table, so only its all-rounds row is recomputed.\n\n### Market price index at selected rounds (cell = mean, n games)\n\n" + c.md_table(pp) + "\n\n### Climbing back up (neutral; round 2 on)\n\n" + c.md_table(CL.rename(columns=lambda s: s.replace("_", " "))) + "\n\n`median first round ge 0 5` is among games that ever reach 0.5. Game counts are the games with rounds data.\n\n" + c.terms([("5-tick start", "Engine-enforced cap on the round-1 quote: 1.00-1.05, five ticks above the floor. Later rounds are unrestricted."), ("Excluding round 1 / rounds 5+", "Price index averaged over rounds 2 on / 5 on; a pair needs a round in the window in both games, so n pairs falls in later windows as games end early.")])
open("ANALYSIS.md", "w").write(HEAD + c.md_table(W[["run", "mode", "window", "n_pairs", "control_mean", "arm_mean", "diff [95% CI]"]].rename(columns={"control_mean": "private chat", "arm_mean": "5-tick"})) + TAIL)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report("ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
