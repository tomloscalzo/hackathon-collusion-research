import os
s = open('gen_report.py', encoding='utf-8').read()
def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)
# imports / extra
rep('O = ".."\n', '''O = ".."
import sys
sys.path.insert(0, os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'worktrees/hackathon-collusion-model-analysis-analysis-claims_dossiers/tools/analysis_style'))
import arm_labels
EX = pd.read_csv(f"{O}/extra_controls.csv")
LEG = arm_labels.axis_legend(rows=["moral-prime", "moral-prime-b", "moral-placebo", "headline-chat"], cols=["price_index"], panels=["t0", "t1", "p1", "neutral"], metric="price_index",
                             row_name="contrast arms (each row is first arm minus second arm, e.g. moral-prime minus headline-chat)", col_name="change in price index (index points), the x-axis", panel_name="marker series: model and mode (blue circle = gpt-oss, orange square = Qwen t1, purple triangle = Qwen t0) and the cell")
exr = "| Contrast | n pairs | Price-index difference [95% CI] | Sign-flip p |\\n|---|---|---|---|\\n" + "".join(f"| {r.contrast} | {int(r.n)} | {r['diff']:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}] | {'<0.001' if r.p < 0.001 else format(r.p, '.3f')} |\\n" for _, r in EX.iterrows())
''')
rep("| data caveat | gpt-oss prime A ran in later waves (107 to 112) than the placebo, plain chat and prime B (waves 7 to 12); Qwen plain chat comes from the main neutral run, the primes and placebo from a later wave. Every cross-arm comparison is therefore across runs. |",
    "| data caveat | gpt-oss: all arms are in one run; prime B, the placebo and plain chat ran in waves 7 to 12, prime A in a later wave (107 to 112) of the same run. Qwen: plain chat comes from the main neutral run, the primes and placebo from a separate later run (wave A). So the gpt-oss prime-A contrasts cross waves, and all Qwen prime-vs-plain-chat contrasts cross runs. See the robustness checks below. |")
rep("## 3. Claim G-null-struct", """**Robustness to the control (same-wave and same-time checks).** Verified from the raw logs (`scripts/extra_controls.py`, `extra_controls.csv`). gpt-oss: prime A can be compared with d-placebo, a game in the same waves 107 to 112 (private chat, p1, with a random-number reply field added; a different arm, not a clean control). Qwen thinking off: a separate "drift" run replayed plain chat (p1, 10 pairs, wordings 0 to 2) at the same time as wave A.

{exr}
<small>

| Term | Meaning |
|---|---|
| d-placebo | gpt-oss arm: private chat, p1, neutral table, plus a request to reply with a random number (placebo for the self-score arms); played in waves 107 to 112 alongside prime A. |
| Qwen drift-run plain chat | Plain private chat, thinking off, p1, from the separate drift run, 10 pairs (wordings 0 to 2). |
| contrast | First arm minus second arm in the same (wording, seed) pair; 95% bootstrap CI over pairs; exact sign-flip p, unadjusted, exploratory. |

</small>

Prime A against the same-wave gpt-oss control is -0.366 [-0.452, -0.275], as large as against the placebo, so the wave gap does not create the effect. Plain chat (waves 7 to 12) minus d-placebo is -0.067 [-0.179, +0.038], a proxy for cross-wave drift on gpt-oss (small, but not excluded up to about 0.1). On Qwen thinking off the drift-run plain chat is +0.068 [-0.100, +0.225] above the main-run plain chat, so main-run drift is small; prime B minus the same-time control is -0.577 [-0.742, -0.389], prime A -0.364 [-0.575, -0.164] and the placebo -0.092 [-0.233, +0.050], all with the same signs and sizes as the main contrasts.

## 3. Claim G-null-struct""")
rep("| headline replicates | Two builds of the plain-chat prompt (a build bug made them differ from the intended arm); they ran 0.07 to 0.12 higher on price index than headline-chat, a measure of run-to-run drift used in section 2. |",
    "| headline replicates | Two gpt-oss arms (hrep-fx-chat-p1, hrep-nx-chat-p1) that were meant to be other arms but, because of a prompt-build bug, played the headline-chat prompt. They ran in the same waves (7 to 12) as plain chat and came out 0.119 and 0.067 higher on price index: a measure of sensitivity to how the prompt was built and sampled, not of cross-wave drift. |")
rep("Control drift is about 0.07 to 0.12, roughly a third of a prime effect, so effect sizes are uncertain by about that much; direction and conclusion do not depend on the control.",
    "The replicates ran in the same waves as plain chat, so their 0.07 to 0.12 higher price index shows how much one copy of the control prompt can differ from another (prompt-build and sampling sensitivity, roughly a third of a prime effect); it is not cross-wave drift, which is unmeasured except for the proxy below. Effect sizes are uncertain by about that much; direction and conclusion do not depend on the control.")
rep("- Cross-run controls: gpt-oss prime A and Qwen plain chat were played at different times from the placebo; headline replicates show the run-to-run drift is 0.07 to 0.12 on the price index.",
    "- Cross-wave and cross-run controls: on gpt-oss, prime A ran in a later wave of the same run than the placebo and plain chat; the Qwen primes and placebo are from a later run than the Qwen plain chat. Same-wave and same-time checks (section 2) give the same sign and size. The 0.07 to 0.12 spread between plain-chat copies on gpt-oss is prompt-build and sampling sensitivity, not measured drift.")
rep("| Holm p | Holm-adjusted over the family of 18 price-index tests (6 contrasts x 3 model-modes). |",
    "| Holm p | Holm-adjusted over the family of 18 price-index tests (6 contrasts x 3 model-modes). The correction covers the price index only; the other four metrics are reported with CIs and unadjusted p in `contrasts_five_metrics.csv`, without correction. |")
rep(" With thinking on, prime B (-0.32 vs placebo) is of similar size to the CoT-monitor threat (-0.21 to -0.23 in the frozen Qwen numbers, not re-derived here). Compare levers only within the same thinking mode.",
    " No ranking test against other levers was run in this dossier, so 'strongest' is untested here; compare levers only within the same thinking mode.")
rep("Among the Qwen levers in the project, prime B with thinking off has the largest single price-index effect, but this is a per-mode statement.",
    "Prime B with thinking off has the largest effect among the contrasts in this dossier, but this is a per-mode statement.")
rep("so the effect is not due to prompt length or to having a persona at all.", "so length and persona format alone do not produce an effect of the primes' size (the placebo also differs in tone and vocabulary).")
rep("**The effect acts through what is said: the primes change the price the firms propose, and the quotes then follow the proposal almost exactly.** Three observations (all from the raw event logs).",
    "**Under the primes the lower price is announced in the first chat messages, and quotes track the announced price as closely as in every other arm; the primes do not open a gap between words and quotes. Whether chat mediates the effect is untested (no tacit moral arm).** Three observations (all from the raw event logs).")
rep("1. **The proposed price falls by the same amount as the quoted price.** Per pair,", "1. **The proposed price falls by the same amount as the quoted price (close to an identity, because quotes equal proposals in every arm; see point 2, so this does not by itself show mediation).** Per pair,")
rep("The route \"primes change the content of the chat, the chat sets the price\" is strongly supported (both models). It does **not** show",
    "The chat shows that the primes change what is proposed and that quotes follow proposals; because quotes follow proposals in every arm, this cannot separate \"chat mediates\" from \"the prime changes the intended price and the chat reports it\". It also does **not** show")
rep(", and the drop came through the price the firms proposed in chat, not through any gap between words and quotes.\"", ".\"")
rep("| New finding: effect acts through talk | Proposed as a supported mechanism (exploratory) | Proposal change accounts for 94% to 106% of the price change; quotes equal proposals; agreement does not fall. Untested without chat. | 2.1 to 2.3 (talk as evidence), 3.4 |",
    "| New finding: where the effect shows up in talk | Descriptive only (exploratory); mediation untested | The lower price is announced in the first chat messages and quotes track it as closely as in every arm (gap 0.00 to 0.05); agreement does not fall. No tacit moral arm, so chat as mediator is untested. | 2.1 to 2.3, 3.4 |")
rep("<small>\n\n| Label | Precise definition |\n|---|---|\n| moral-prime minus headline-chat |", "<small>\n\n{LEG}\n\n| Label | Precise definition |\n|---|---|\n| moral-prime minus headline-chat |")
open('gen_report.py', 'w', encoding='utf-8').write(s)
