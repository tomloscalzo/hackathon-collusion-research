"""Assemble ANALYSIS.md from incentives_contrasts.csv. usage: python -X utf8 make_md.py"""
import pandas as pd, common as c
R = pd.read_csv("incentives_contrasts.csv"); R["ci"] = R.apply(c.ci_str, axis=1)
L = {"price_index": "price index", "comp_share": "competitive share", "profit_gain_index": "profit gain index"}
def tab(run):
    s = R[R.run == run].copy(); s["measure"] = s.measure.map(L)
    return c.md_table(s[["arm", "measure", "mode", "n_pairs", "control_mean", "arm_mean", "ci"]].rename(columns={"control_mean": "private chat", "arm_mean": "arm", "ci": "diff [95% CI]"}))
HEAD = """# Incentive texts: profit target with job risk, and joint-profit instruction

Created by Claude at the prompting of the repository owner. Code: `analyze.py`, `make_md.py`, `common.py`. Data: neutral run `steps/neutral/step1` (primary), anchored run (check). Numbers: `incentives_contrasts.csv`. Control: `headline-chat` (private chat) at penalty point 3, paired on (wording, seed) within thinking mode.

## Verdict

Neither incentive text raised prices detectably. **m-inc-target** (the owner's profit-target text with job risk) moves the price index by +0.09 [-0.06, +0.24] with thinking off and -0.02 [-0.10, +0.06] with thinking on; **m-inc-joint** (maximise joint profit) by +0.14 [-0.01, +0.28] off and -0.06 [-0.14, +0.01] on. So thinking-off points upward (joint-profit text up to +0.28 is not excluded; the interval just touches zero) but thinking-on is bounded to a rise of at most about +0.06 to +0.10. Competitive share is the cleaner signal: with thinking off it falls by about 0.12 for both texts (target -0.12 [-0.27, -0.00]; joint -0.11 [-0.27, +0.01]), i.e. firms undercut less; with thinking on it is at the floor already (control 0.01) and cannot fall further. The profit-gain index tells the same story (+0.10 [-0.03, +0.26] off for both; about 0 on).

Even the joint-profit instruction, which tells the firms to collude, barely moves things, because the private-chat control already sits high (price index 0.61 off, 0.77 on; profit gain 0.78 and 0.92) and the chat is explicit in every game. The ceiling, not a weak text, limits the effect: with thinking on there is little room above the control. The anchored run (control at 0.46 / 0.51) agrees: all effects within about +/-0.08 (joint, off: +0.08 [-0.05, +0.22]).

Because of the minimum detectable effect (about 0.15-0.25), these are bounds: a price-index change larger than about +0.28 (either text, thinking off) or +0.10 (thinking on) is ruled out; moderate rises with thinking off are not.

![forest plot](incentives.png)

Figure: arm minus private chat, neutral run, 95% bootstrap CI over 20 pairs.

## Tables

### Neutral (primary)

""" 
TAIL = "\n\n### Anchored (check)\n\n" + tab("anchored") + "\n\nProfit gain index: 0 = the competitive floor's profit, 1 = the monopoly profit (higher = more collusion).\n\n" + c.terms([("m-inc-target", "The firm is told its profit target and that missing it risks the job (owner's text)."), ("m-inc-joint", "The firm is told to maximise the two firms' joint profit."), ("Profit gain index", "(mean profit per firm-round - Nash profit) / (monopoly profit - Nash profit); 0 = floor profit, 1 = monopoly profit.")])
open("ANALYSIS.md", "w").write(HEAD + tab("neutral") + TAIL)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report("ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
