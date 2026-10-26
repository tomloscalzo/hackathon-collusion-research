"""Assemble ANALYSIS.md. usage: python -X utf8 make_md.py"""
import pandas as pd, common as c
G = pd.read_csv("market_structure_contrasts.csv"); G["ci"] = G.apply(c.ci_str, axis=1)
G = G.assign(measure=G.measure.map({"price_index": "price index", "comp_share": "competitive share"}))
def gt(run):
    s = G[G.run == run]; return c.md_table(s[["contrast", "measure", "mode", "n_pairs", "control_mean", "arm_mean", "ci"]].rename(columns={"control_mean": "control", "arm_mean": "arm", "ci": "diff [95% CI]"}))
P = pd.read_csv("punishment.csv")
O = pd.read_csv("event_time_windows.csv"); O["cheater vs control [95% CI]"] = O.apply(lambda r: f"{r['diff']:+.3f} [{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]", axis=1)
O["change since pre, vs control [95% CI]"] = O.apply(lambda r: "" if r.window.startswith("pre") else f"{r['change_vs_pre_diff']:+.3f} [{r['change_ci_lo']:+.3f}, {r['change_ci_hi']:+.3f}]", axis=1)
def ot(ser):
    s = O[O.series == ser]; return c.md_table(s[["mode", "window", "n_games", "cheater", "control", "cheater vs control [95% CI]", "change since pre, vs control [95% CI]"]])
HEAD = """# Market structure: a third firm, and a planted cheater

Created by Claude at the prompting of the repository owner. Code: `analyze.py`, `make_md.py`, `common.py`. Data: neutral run `steps/neutral/step1` (primary; price paths need its rounds table), anchored run (check; game-level only). Numbers: `market_structure_contrasts.csv`, `punishment.csv`, `paths_by_round.csv`, `event_time_*.csv`. All at penalty point 3, paired on (wording, seed) within thinking mode, 20 pairs.

## Verdict

**3 firms vs 2 (group chat).** Adding a third firm did not measurably lower prices: price index -0.01 [-0.20, +0.17] (thinking off) and -0.09 [-0.20, +0.01] (on); competitive share -0.11 [-0.26, +0.01] and -0.01. Bounds: a fall in the price index larger than about 0.20 is excluded, a rise larger than about 0.17 is excluded; the thinking-on point (-0.09) hints at modestly lower prices with three firms but its interval touches zero. Anchored run agrees (-0.06 [-0.19, +0.07]; -0.06 [-0.13, +0.01]).

**The planted cheater (n3-cheater vs 3-firm chat).** The scripted third firm quotes about 1.8-1.9 every round (below the two LLM firms' usual 2.5, so it takes the business) and in its defect round (median round 7, from round 6 to 10) quotes the floor once. The market price index is therefore pulled down a lot: -0.21 [-0.31, -0.10] (off) and -0.31 [-0.36, -0.25] (on), and the same in the anchored run (-0.18 and -0.13).

**Reaction to the defection, over time.** The market price falls to the floor for exactly one round and goes straight back to the cheater's standing level (market price index 0.44 before, 0.00 in the defect round, 0.44 after, thinking off; 0.40, 0.00, 0.37 on): there is no price war. The LLM firms' reaction is weak and depends on thinking. **Thinking off: no punishment at all**: 0 of 16 games had another firm undercut the cheater within 3 rounds, and the LLM quote index stays flat (change after the defection vs matched control +0.01 [-0.01, +0.04] in rounds 1-3 and -0.00 [-0.01, +0.00] in rounds 4-8; the LLM firms keep quoting about 0.75, above the matched no-cheater games at 0.59). **Thinking on: some punishment**: 9 of 16 games (56%) had a rival undercut within 3 rounds (median lag 2 rounds; 11 of 16 ever), but the LLM quotes were already well below the no-cheater control before the defection (0.52 vs 0.68; the standing undercutter was already being answered), and the further change is small and not distinguishable from zero: -0.04 [-0.09, +0.01] in rounds 1-3 and -0.02 [-0.14, +0.09] in rounds 4-8. Anchored run: 0 of 17 (off) and 4 of 16 (25%, on).

So a defector is punished only sometimes, and then by undercutting once or twice rather than a sustained war; the coalition (the two LLM firms) mostly just stays at its prices while the cheater takes the market. The event-time samples are small (14-15 games per mode at the defection, 10-11 by rounds 4-8, as games end early), so the post-defection changes are bounds of about +/-0.1 for thinking on and about +/-0.04 for thinking off.

![price paths and reactions to defection](market_structure.png)

Figure: left, market price index by round (dashed = thinking on); right, mean LLM quote index around the defection (0 = the cheater's defect round) against the matched 3-firm chat game at the same absolute rounds. Points with fewer than 10 games are omitted on the right.

## Tables

### Group size and cheater, game level, neutral (primary)

""" 
MID = "\n\n### Group size and cheater, game level, anchored (check)\n\n"
T2 = "\n\n### Punishment of the defector (games with a defection; punished = another firm undercuts within 3 rounds)\n\n"
T3 = "\n\n### Event time: LLM firms' mean quote index around the defection (neutral)\n\nWindows are rounds relative to the defect round; `control` is the matched 3-firm chat game at the same absolute rounds; the last column is the change since the pre window (k -3..-1) in the cheater game minus the same change in the control.\n\n"
T4 = "\n\n### Event time: market price index around the defection (neutral)\n\n"
TAIL = "\n\nThe cheater keeps its standing quote after the dip, so the market index does not recover above it. Two cheater games and some others are missing from the rounds table (53 neutral games overall); game-level rows use run.csv and cover all 20 pairs.\n\n" + c.terms([("n3-group", "Three LLM firms with a private group chat."), ("n3-cheater", "Two LLM firms plus a scripted third firm that undercuts at a fixed quote and defects once (drops to the floor) in its defect round."), ("Defect round; k", "The round the scripted firm's quote first differs from its opening quote; k = rounds since it."), ("Punished within 3", "Another firm undercuts within 3 rounds of the defection (run.csv coalition_punished)."), ("Quote index", "(quote - 1) / 2 for the LLM firms, averaged over the two.")])
open("ANALYSIS.md", "w").write(HEAD + gt("neutral") + MID + gt("anchored") + T2 + c.md_table(P) + T3 + ot("llm_quote_index") + T4 + ot("market_price_index") + TAIL)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report("ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
