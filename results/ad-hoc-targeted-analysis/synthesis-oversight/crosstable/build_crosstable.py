"""Build the factor x sprint sub-question cross-tables as figure-quality PNGs.

Inputs are transcribed by hand from committed reports (no recomputation):
  gpt-oss cells : results/oss/trackm-neutral-2026-10-26/step3_primary/SUMMARY.md section 3.4
                  (status words and the gpt-oss effects in its family tables 3.1-3.3)
  Qwen3-32B cells: results/compare-models/qwen-vs-gpt-oss/lever_table.csv (Qwen thinking on,
                  neutral run, price index), results/claims-dossiers/MASTER_CLAIMS.md,
                  results/claims-dossiers/09-failed-tactics/oversight/verdicts.csv,
                  results/ad-hoc-targeted-analysis/model-vs-llm/MODEL_VS_LLM.md
The per-row source is written to crosstable_cells.csv.

Outputs: crosstable_oss.png, crosstable_cumulative.png, crosstable_cells.csv (this folder).
Run: python -X utf8 build_crosstable.py
"""
import csv
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

COLS = [
    ("1.1", "necessary variables"),
    ("1.2", "replacing participants"),
    ("1.3", "improving detection"),
    ("1.4", "info-theoretic detection"),
    ("1.5", "cheapest restriction"),
    ("2.1", "tasks that lead to collusion"),
    ("2.2", "words plus actions"),
    ("2.3", "convincing evidence"),
    ("3.1", "conduits, side channels"),
    ("3.2", "trusted agents"),
    ("3.3", "peer identification"),
    ("3.4", "behaviour when watched"),
]
CI = {c: i for i, (c, _) in enumerate(COLS)}

# status code -> (label, face colour, hatch)
STATUS = {
    "c": ("confirmed", "#b9e3b0", None),
    "s": ("confirmed (suggestive)", "#e3f4dd", "////"),
    "d": ("downgraded", "#f9cf86", None),
    "u": ("unresolved", "#fde6bd", "\\\\\\\\"),
    "b": ("bounded null", "#d6e0ea", None),
    "r": ("not run", "#b8b8b8", None),
    "x": ("not addressed", "#d0d0d0", None),
}
NA_FACE = "#f4f4f4"
HATCH_COL = {"s": "#5aa54d", "u": "#c98a1c"}

FAMILIES = {
    "a": "(a) Environment / ripeness",
    "b": "(b) Tendencies and dispositions",
    "c": "(c) Observation, prediction, control",
}

# Each row: family, factor label, oss cells {col: "code:text"}, qwen cells {col: "code:text"}, source
ROWS = [
    ("a", "Penalty (p5 vs p1)",
     {"1.1": "c:-0.19 no chat; -0.15 chat", "1.5": "c:heaviest point only"},
     {"1.1": "c:-0.53 no chat; -0.31 chat", "1.5": "c:-0.53 / -0.31"},
     "oss: SUMMARY 3.1; Qwen: lever_table penalty tacit/chat p5-p1"),
    ("a", "Penalty x chat (does chat blunt the fine?)",
     {"1.1": "b:+0.10 pg", "3.1": "b:+0.10 pg"},
     {"1.1": "c:+0.23 (chat blunts)", "3.1": "c:+0.23"},
     "oss: SUMMARY 3.1 (profit gain); Qwen: lever_table penalty interaction (price index); MASTER G-interaction"),
    ("a", "Communication (private chat vs none)",
     {"1.1": "c:+0.21", "1.5": "c:ban chat: -0.21", "3.1": "c:+0.21", "3.3": "x:"},
     {"1.1": "c:+0.13 p1; +0.36 p5", "1.5": "c:ban chat: -0.13 (p1)", "3.1": "c:+0.17 pooled", "3.3": "x:"},
     "oss: SUMMARY 3.1; Qwen: lever_table communication, MASTER G-comm (pooled +0.17)"),
    ("a", "Regulator-monitored chat",
     {"1.5": "r:", "3.4": "r:"},
     {"1.5": "b:+0.007", "3.4": "b:+0.007; talk 0.00"},
     "Qwen: 09-failed-tactics verdicts.csv headline-monitored t1 (80 pairs); MASTER Q5-monitored"),
    ("a", "Number of firms (3 vs 2)",
     {"1.1": "b:+0.01", "1.2": "b:", "3.3": "x:"},
     {"1.1": "b:-0.09", "1.2": "b:", "3.3": "x:"},
     "oss: SUMMARY 3.1; Qwen: lever_table market-structure n3-group"),
    ("a", "Planted cheater",
     {"1.2": "d:residual -0.01", "2.3": "d:", "3.2": "d:", "3.3": "x:"},
     {"1.2": "d:residual -0.04", "2.3": "d:", "3.2": "d:", "3.3": "x:"},
     "oss: SUMMARY 3.1; Qwen: MASTER G-cheater (residual -0.041)"),
    ("a", "Game length, final round",
     {"1.1": "b:+0.01"},
     {"1.1": "x:not found"},
     "oss: MASTER D11-4; Qwen: no source found"),
    ("a", "Ripeness model (benchmark)",
     {"1.1": "d:signs hold", "1.5": "d:p5 still 0.42", "2.1": "d:"},
     {"1.1": "d:t1 r 0.76; t0 r 0.10", "1.5": "d:thinking on only", "2.1": "d:thinking on only"},
     "oss: SUMMARY 3.1; Qwen: MODEL_VS_LLM.md (headline-tacit Pearson with theta*: t1 0.76, t0 0.10)"),
    ("b", "Moral primes (vs placebo)",
     {"1.5": "c:-0.32 / -0.38", "2.2": "d:mechanism", "3.1": "d:mediation untested", "3.4": "c:"},
     {"1.5": "c:-0.22 / -0.32 (t0 -0.18 / -0.48)", "2.2": "d:mechanism", "3.1": "d:mediation untested", "3.4": "c:"},
     "oss: SUMMARY 3.2; Qwen: MASTER G-moral, lever_table moral-primes"),
    ("b", "Moral placebo (vs plain chat)",
     {"1.1": "b:-0.00", "1.5": "b:"},
     {"1.1": "b:-0.05", "1.5": "b:"},
     "oss: SUMMARY 3.2; Qwen: lever_table moral-placebo - headline-chat"),
    ("b", "Joint-profit incentive text",
     {"1.1": "d:+0.10, in drift band", "2.1": "d:matching +0.27"},
     {"1.1": "b:-0.06", "2.1": "b:"},
     "oss: SUMMARY 3.2; Qwen: lever_table m-inc-joint"),
    ("b", "Profit-target incentive text",
     {"1.1": "b:+0.04", "2.1": "b:"},
     {"1.1": "b:-0.02", "2.1": "b:"},
     "oss: SUMMARY 3.2; Qwen: lever_table m-inc-target"),
    ("b", "Ethics rule on one of three firms",
     {"1.2": "c:all seats fall", "1.5": "c:-0.22", "3.2": "c:"},
     {"1.2": "b:+0.02 (matching -0.18)", "1.5": "b:+0.02", "3.2": "b:"},
     "oss: SUMMARY 3.2; Qwen: lever_table ethics-rule, MASTER G-n3ethics"),
    ("b", "Ethics rule on one of two firms",
     {"1.1": "b:-0.02", "1.3": "s:talk -0.50", "1.5": "b:", "2.2": "s:", "3.4": "s:"},
     {"1.1": "b:-0.01", "1.3": "b:talk about -0.05", "1.5": "b:", "2.2": "b:", "3.4": "b:"},
     "oss: SUMMARY 3.2; Qwen: lever_table asymmetric; Qwen talk = oss -0.50 minus model difference -0.45 (MASTER G-asym-talk), derived"),
    ("b", "Instructed controls (compete / joint)",
     {"2.3": "c:calibrated"},
     {"2.3": "c:compete -0.77, joint -0.04 vs chat"},
     "oss: SUMMARY 3.2; Qwen: lever_table controls (vs headline-chat p3)"),
    ("b", "Printed example prices (focal points)",
     {"1.1": "c:-0.22 to -0.56", "1.5": "c:largest lever", "2.1": "c:", "2.3": "c:0.40-0.47 exactly on a printed price"},
     {"1.1": "c:-0.50 to -0.74", "1.5": "c:largest lever", "2.1": "c:", "2.3": "c:0.86 exactly on a printed price"},
     "oss: SUMMARY 3.2; Qwen: lever_table payoff-table-focal-points, MASTER H2"),
    ("b", "Formula joint-profit control",
     {"1.1": "c:+0.01: low prices are a choice", "2.3": "c:"},
     {"1.1": "d:-0.36: ceiling not reached", "2.3": "d:capability not shown"},
     "oss: SUMMARY 3.2; Qwen: lever_table fx-ctl-joint - headline-chat (p3), MASTER G-fxjoint"),
    ("b", "5-tick start",
     {"1.1": "c:-0.29", "1.5": "c:-0.29", "3.1": "d:mechanism"},
     {"1.1": "c:-0.55", "1.5": "c:-0.55 (t0 -0.39)", "3.1": "d:matching -0.62"},
     "oss: SUMMARY 3.2; Qwen: MASTER Q-5tick, G-5tick (mechanism)"),
    ("b", "Printed 2.09 (anchored table)",
     {"1.1": "r:", "2.3": "r:"},
     {"1.1": "c:held 2.50 moves to 2.09", "2.3": "c:pg -0.15 to -0.24"},
     "Qwen: MASTER Q2-anchor"),
    ("b", "Prompt wording (5 paraphrases)",
     {"1.1": "c:up to 0.15", "2.1": "c:", "2.3": "c:"},
     {"1.1": "c:thinking off only", "2.1": "c:", "2.3": "c:"},
     "oss: SUMMARY 3.2; Qwen: MASTER Q14-wording (t0 epsilon-squared 0.12; t1 null)"),
    ("b", "Reasoning mode (thinking on vs off)",
     {"1.1": "x:one mode only", "2.3": "x:"},
     {"1.1": "c:penalty x thinking -0.51 pg", "2.3": "d:aliased with token cap"},
     "Qwen: MASTER H1 (penalty bites with thinking on), Q17-thinking"),
    ("b", "Outcome vs strategic collusion",
     {"1.1": "d:no punishment signature", "2.1": "d:", "2.3": "d:49% vs 29% undercuts"},
     {"1.1": "d:focal holding", "2.1": "d:", "2.3": "d:0.83-0.86 on printed prices"},
     "oss: SUMMARY 3.2; Qwen: MASTER H2 (outcome vs strategic)"),
    ("c", "Detection from quotes (early prices)",
     {"1.2": "c:rule transfers, threshold does not", "1.3": "c:AUC 0.81-0.91", "1.4": "x:", "2.2": "c:text adds -0.01", "2.3": "c:"},
     {"1.2": "x:rule frozen on Qwen", "1.3": "c:AUC 0.90", "1.4": "x:", "2.2": "c:text adds -0.00", "2.3": "c:"},
     "oss: SUMMARY 3.3; Qwen: MASTER Q-AUC"),
    ("c", "Detection from chat text",
     {"1.2": "d:recall 0.29", "1.3": "d:AUC 0.65-0.83", "1.4": "d:", "2.2": "d:"},
     {"1.2": "d:recall 0.80", "1.3": "d:AUC 0.72", "1.4": "d:", "2.2": "d:"},
     "oss: SUMMARY 3.3; Qwen: MASTER Q-AUC (text 0.72), G-detect-text (recall 0.80)"),
    ("c", "Frozen keyword rules",
     {"1.3": "c:fail: 19 of 20 compete games flagged", "2.1": "d:intent class", "2.2": "c:", "2.3": "c:"},
     {"1.3": "c:fail: 9 of 20 compete games flagged", "2.1": "d:intent class", "2.2": "c:", "2.3": "c:"},
     "oss: SUMMARY 3.3; Qwen: MASTER Q9-frozen, Q11-intent"),
    ("c", "Say vs do (undercut after agreeing)",
     {"2.2": "d:23% vs 25%"},
     {"2.2": "c:1.9% after agreeing"},
     "oss: SUMMARY 3.3; Qwen: MASTER Q10-saydo"),
    ("c", "Observer (Claude) temptation ratings",
     {"1.3": "c:", "2.1": "c:rho +0.79 (+0.58 adj.)", "2.3": "c:"},
     {"1.3": "c:", "2.1": "c:rho +0.75", "2.3": "c:"},
     "oss: SUMMARY 3.3; Qwen: owner observation 7 / MASTER H1 temptation screen"),
    ("c", "Self-score fields (as a lever)",
     {"2.2": "b:", "3.4": "b:"},
     {"2.2": "b:-0.02 to +0.05", "3.4": "b:"},
     "oss: SUMMARY 3.3; Qwen: lever_table self-report-scores (d-conflict, d-temptation-a/b)"),
    ("c", "Self-reports (as a signal)",
     {"2.2": "d:partial +0.05", "2.3": "c:conflict 1.05 of 5"},
     {"2.2": "x:not found", "2.3": "c:conflict 1.00 of 5"},
     "oss: SUMMARY 3.3; Qwen: MASTER Q4-conflict"),
    ("c", "CoT-monitor threat: price",
     {"1.5": "u:-0.13", "3.4": "u:-0.13 (-0.18 vs pooled control)"},
     {"1.5": "c:-0.23 (threat B -0.20)", "3.4": "c:-0.23"},
     "oss: SUMMARY 3.3, MASTER G-cot; Qwen: lever_table cot-monitor-threat, verdicts.csv d-cot-monitor-b"),
    ("c", "CoT-monitor threat: mechanism",
     {"1.3": "c:agreement talk -0.58", "2.2": "c:", "3.4": "c:suppression, not hiding"},
     {"1.3": "c:agreement talk -0.55", "2.2": "c:", "3.4": "c:suppression, not hiding"},
     "oss/Qwen: 09-failed-tactics mechanism.csv explicit_agreement_flag; MASTER G-cot-mech"),
    ("c", "Watchdog (questions firms)",
     {"1.5": "d:-0.03 to +0.04", "3.2": "d:", "3.4": "d:report threat pg -0.07"},
     {"1.5": "d:-0.06 to -0.08, fails Holm", "3.2": "d:", "3.4": "d:report threat +0.00"},
     "oss: SUMMARY 3.3, MASTER G-watchdog; Qwen: verdicts.csv wd-* thinking on"),
    ("c", "Introspection questions",
     {"2.2": "b:-0.02 to +0.06", "2.3": "s:candour", "3.4": "b:"},
     {"2.2": "b:-0.07 to +0.02", "2.3": "s:candour", "3.4": "b:"},
     "oss: SUMMARY 3.3; Qwen: lever_table introspection (r2f, r3f, r2s, r3s), MASTER G-candour"),
    ("c", "Copy-bot control",
     {"2.3": "r:", "3.1": "r:"},
     {"2.3": "c:matching gap n.s.", "3.1": "c:"},
     "Qwen: MASTER Copy-bot (Qwen)"),
    ("c", "Tick churn (competitive share)",
     {"1.3": "c:", "2.3": "c:30-60% few-tick"},
     {"1.3": "c:", "2.3": "c:10-20% few-tick"},
     "oss/Qwen: MASTER D11-2"),
    ("c", "Reproducibility (same-prompt replays)",
     {"2.3": "c:+0.10; pair gap 0.22"},
     {"2.3": "r:"},
     "oss: SUMMARY 3.3, MASTER G-repro; Qwen: no hrep arms"),
]


def parse(cell):
    code, _, text = cell.partition(":")
    return code, text.strip()


def wrap(text, width):
    return "\n".join(textwrap.wrap(text, width)) if text else ""


def draw_cell(ax, x, y, w, h, code, text, fs, width_chars, italic=False):
    if code is None:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=NA_FACE, edgecolor="white", lw=1.2))
        ax.text(x + w / 2, y + h / 2, "-", ha="center", va="center", fontsize=fs, color="#9a9a9a")
        return
    label, face, hatch = STATUS[code]
    ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor="white", lw=1.2))
    if hatch:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="none", edgecolor=HATCH_COL[code],
                               hatch=hatch, lw=0, alpha=0.45))
    return label


SHORT = {"c": "confirmed", "s": "suggestive", "d": "downgraded", "u": "unresolved",
         "b": "bounded null", "r": "not run", "x": "not addressed"}


def build(mode):
    cumulative = mode == "cumulative"
    fs = 9
    col_w, fac_w, fam_w = 1.12, 2.35, 0.32
    row_h = 0.98 if cumulative else 0.56
    head_h = 0.75
    n = len(ROWS)
    width = fam_w + fac_w + col_w * len(COLS) + 0.2
    legend_h = 2.75 if cumulative else 2.75
    title_h = 0.95
    height = title_h + head_h + row_h * n + legend_h
    fig = plt.figure(figsize=(width, height), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    top = height - title_h
    if cumulative:
        title = ("Cumulative experiment: every factor against the sprint sub-questions, both models "
                 "(gpt-oss-20b medium reasoning; Qwen3-32B thinking on unless noted)")
        sub = ("Each cell is split: upper half = gpt-oss-20b, lower half = Qwen3-32B, each coloured by its own evidence status. "
               "Numbers are ABSOLUTE price-index effects of that model (arm minus its own control, 0-1 scale) unless "
               "a unit is named; the 95% CIs are in the source reports. Neither model is expressed relative to the other.")
    else:
        title = "gpt-oss-20b: every factor tested, against the sprint sub-questions (evidence status after adversarial review)"
        sub = ("Numbers are ABSOLUTE gpt-oss-20b price-index effects (arm minus its own control, 0-1 scale; pg = profit gain index; "
               "talk = share of games with two-sided agreement talk) unless a unit is named; the 95% CIs are in "
               "step3_primary/SUMMARY.md sections 3.1-3.3. Not relative to Qwen.")
    ax.text(0.15, height - 0.3, title, fontsize=12.5, fontweight="bold", va="center")
    ax.text(0.15, height - 0.68, wrap(sub, 235), fontsize=8.8, va="center", color="#333333")

    # header
    x0 = fam_w + fac_w
    ax.text(fam_w + 0.05, top - head_h / 2, "Factor", fontsize=fs + 0.5, fontweight="bold", va="center")
    for i, (code, name) in enumerate(COLS):
        cx = x0 + i * col_w
        ax.add_patch(Rectangle((cx, top - head_h), col_w, head_h, facecolor="#e9edf2", edgecolor="white", lw=1.2))
        ax.text(cx + col_w / 2, top - 0.2, code, ha="center", va="center", fontsize=fs + 1, fontweight="bold")
        ax.text(cx + col_w / 2, top - 0.5, wrap(name, 14), ha="center", va="center", fontsize=fs - 0.8,
                color="#333333", linespacing=1.0)

    y = top - head_h
    fam_start = {}
    for r, (fam, fac, oss, qwen, _src) in enumerate(ROWS):
        ry = y - (r + 1) * row_h
        fam_start.setdefault(fam, [ry + row_h, ry])
        fam_start[fam][1] = ry
        shade = "#ffffff" if r % 2 == 0 else "#fafafa"
        ax.add_patch(Rectangle((fam_w, ry), fac_w, row_h, facecolor=shade, edgecolor="#e6e6e6", lw=0.6))
        ax.text(fam_w + 0.06, ry + row_h / 2, wrap(fac, 27), fontsize=fs, va="center", linespacing=1.05)
        for i, (col, _) in enumerate(COLS):
            cx = x0 + i * col_w
            if not cumulative:
                cell = oss.get(col)
                if cell is None:
                    draw_cell(ax, cx, ry, col_w, row_h, None, "", fs, 15)
                    continue
                code, text = parse(cell)
                draw_cell(ax, cx, ry, col_w, row_h, code, text, fs, 15)
                lines = SHORT[code]
                body = wrap(text, 17)
                ax.text(cx + col_w / 2, ry + row_h / 2, lines + ("\n" + body if body else ""),
                        ha="center", va="center", fontsize=fs - 0.6 if body.count("\n") >= 1 else fs - 0.3,
                        linespacing=1.0, fontweight="normal")
            else:
                c_o, c_q = oss.get(col), qwen.get(col)
                if c_o is None and c_q is None:
                    draw_cell(ax, cx, ry, col_w, row_h, None, "", fs, 15)
                    continue
                for half, cell, tag in ((1, c_o, "oss"), (0, c_q, "Qwen")):
                    hy = ry + half * row_h / 2
                    if cell is None:
                        draw_cell(ax, cx, hy, col_w, row_h / 2, None, "", fs, 15)
                        continue
                    code, text = parse(cell)
                    draw_cell(ax, cx, hy, col_w, row_h / 2, code, text, fs, 15)
                    s = f"{tag}: {text}" if text else f"{tag}: {SHORT[code]}"
                    ax.text(cx + col_w / 2, hy + row_h / 4, wrap(s, 19), ha="center", va="center",
                            fontsize=fs - 1.2, linespacing=0.95)
                ax.plot([cx, cx + col_w], [ry + row_h / 2, ry + row_h / 2], color="white", lw=0.8)
    # family bands
    fam_cols = {"a": "#7a8ca3", "b": "#8f7aa3", "c": "#7aa39a"}
    for fam, (ytop, ybot) in fam_start.items():
        ax.add_patch(Rectangle((0.02, ybot), fam_w - 0.06, ytop - ybot, facecolor=fam_cols[fam], edgecolor="none"))
        ax.text(fam_w / 2 - 0.02, (ytop + ybot) / 2, FAMILIES[fam], rotation=90, ha="center", va="center",
                fontsize=fs + 0.5, color="white", fontweight="bold")
        ax.plot([0.02, width - 0.18], [ybot, ybot], color="#555555", lw=1.0)

    # legend
    ly = y - n * row_h - 0.35
    ax.text(0.15, ly, "Colour key (evidence status, from results/claims-dossiers/MASTER_CLAIMS.md and step3_primary/SUMMARY.md):",
            fontsize=fs + 0.5, fontweight="bold", va="center")
    keys = [("c", "confirmed: survives re-derivation and adversarial review (possibly narrowed)"),
            ("s", "confirmed (suggestive): direction confirmed, rests on an unvalidated keyword text measure"),
            ("d", "downgraded: weaker form only (smaller scope, conduct not price, or mechanical)"),
            ("u", "unresolved: same direction, CI excludes 0, fails multiplicity correction"),
            ("b", "bounded null: no detectable effect; the 95% CI bounds its size"),
            ("r", "not run: no arm exists for this factor on this model"),
            ("x", "not addressed: relevant, but no analysis measures it")]
    for k, (code, txt) in enumerate(keys):
        kx = 0.25 + (k % 2) * (width / 2 - 0.1)
        kyy = ly - 0.36 - (k // 2) * 0.32
        draw_cell(ax, kx, kyy - 0.12, 0.45, 0.24, code, "", fs, 10)
        ax.text(kx + 0.55, kyy, txt, fontsize=fs - 0.3, va="center")
    k = len(keys)
    kx = 0.25 + (k % 2) * (width / 2 - 0.1)
    kyy = ly - 0.36 - (k // 2) * 0.32
    draw_cell(ax, kx, kyy - 0.12, 0.45, 0.24, None, "", fs, 10)
    ax.text(kx + 0.55, kyy, "- (light grey): the factor is not relevant to this sub-question", fontsize=fs - 0.3, va="center")
    note_y = kyy - 0.42
    note = ("Amber, not red, marks weakened evidence so that colour never implies a collusion direction. "
            "Sub-questions: 1.x Track 1 markets and collusion; 2.x Track 2 detection and audit; 3.x Track 3 carriers and countermeasures. "
            "Arm-level definitions: step3_primary/SUMMARY.md legend tables; t0/t1 = Qwen thinking off/on.")
    if cumulative:
        note = ("Split cell: upper half gpt-oss-20b, lower half Qwen3-32B; a half in light grey with '-' means that model has no "
                "entry for that cell. No single combined status is assigned: where the halves differ in colour the models disagree. "
                "Qwen 'talk about -0.05' (ethics rule, one of two) is derived as the gpt-oss value minus the reported model difference. "
                + note)
    ax.text(0.15, note_y, wrap(note, 250), fontsize=fs - 0.6, va="top", color="#333333")
    out = os.path.join(HERE, f"crosstable_{'cumulative' if cumulative else 'oss'}.png")
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    return out


def write_csv():
    out = os.path.join(HERE, "crosstable_cells.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "factor", "subquestion", "oss_status", "oss_text", "qwen_status", "qwen_text", "source"])
        for fam, fac, oss, qwen, src in ROWS:
            for col, _ in COLS:
                if col in oss or col in qwen:
                    co, to = parse(oss[col]) if col in oss else ("", "")
                    cq, tq = parse(qwen[col]) if col in qwen else ("", "")
                    w.writerow([fam, fac, col, SHORT.get(co, "n/a"), to, SHORT.get(cq, "n/a"), tq, src])
    return out


if __name__ == "__main__":
    print(write_csv())
    print(build("oss"))
    print(build("cumulative"))
