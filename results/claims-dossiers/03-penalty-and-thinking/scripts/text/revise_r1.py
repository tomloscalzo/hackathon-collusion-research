"""Review round 1 text revisions (final Qwen table, cross-wave caveat, Q17 range, H2 downgrade)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def rep(fn, pairs):
    s = open(fn, encoding="utf-8").read()
    for a, b in pairs:
        if a not in s:
            raise SystemExit(f"MISSING in {fn}: {a[:80]}")
        s = s.replace(a, b)
    open(fn, "w", encoding="utf-8").write(s)


CW = ("**Cross-wave caveat (gpt-oss).** The gpt-oss cells were run in different waves: chat p1 and p5 in waves 7 to 12, no chat p1 and p5 in waves 13 to 16, chat p3 in waves 107 to 112. "
      "Every gpt-oss contrast between chat and no chat (including the interaction) and every contrast involving chat p3 therefore also compares waves. "
      "Mitigation: the replicate offsets (replicate game minus original, profit gain at p1) are of the same sign and similar size for chat (+0.06, +0.12) and no chat (+0.15, +0.17). "
      "Limit: the replicates ran in the same waves as their originals, so a wave effect itself is untested.")

rep("tpl_part1.txt", [
    ("Qwen 480 headline games (12 cells x 2 modes)", "Qwen 480 headline games (12 cells x 2 modes; the final Step 1 game table, with all truncation reruns merged)"),
    ('Re-derived exactly. p5 lowers gpt-oss profit gain by 0.30 (no chat) and 0.19 (chat); p3 does nothing. "Half as strong" holds without chat only; with chat gpt-oss and Qwen thinking on do not differ.',
     'Re-derived exactly. p5 lowers gpt-oss profit gain by 0.30 (no chat) and 0.19 (chat); p3 does nothing. "About half as strong" holds without chat only (gpt-oss -0.30 vs Qwen thinking on -0.63); with chat they do not differ. The gpt-oss cells ran in different waves.'),
    ("+0.10 [-0.12, +0.31] on profit gain (Qwen thinking on +0.40 [+0.18, +0.60]). The gpt-oss minus Qwen difference is -0.29 [-0.56, -0.01], and it does not survive Holm.",
     '+0.10 [-0.12, +0.31] on profit gain (Qwen thinking on +0.37 [+0.15, +0.57]). The gpt-oss minus Qwen difference is -0.26 [-0.52, +0.01]. The upper bound means "chat does not blunt the penalty" holds only for interactions larger than about 0.3. Chat and no chat ran in different waves.'),
    ("tracks the theory curve without chat (slope 0.72)", "tracks the theory curve without chat (slope 0.69)"),
    ("small and not significant in the headline arms (+0.03 to +0.05)", "small and not significant in the headline arms (+0.03 to +0.07)"),
    ("| **Confirmed, re-derived -0.54 (no chat)** | -0.544 [-0.733, -0.345] without chat; -0.31 with chat and with monitored chat. The 0.03 gap from -0.514 comes from the rerun version of the thinking-on no-chat p5 games (11 of 20 are truncation reruns). |",
     "| **Confirmed, re-derived -0.514 (no chat)** | -0.514 [-0.701, -0.316] without chat (p 0.0002), equal to FINAL_NUMBERS; -0.31 with chat and with monitored chat. 13 of the 20 thinking-on no-chat p5 games are truncation reruns. |"),
    ("| **Confirmed for Qwen with a sharper definition; gpt-oss shows a third pattern** | Qwen holds printed prices in both modes (83 to 86% of quotes; holding predicts price, Spearman 0.54). Thinking on adds targeted punishment: it undercuts back after being undercut in 28% of cases vs 4.5% with thinking off. It shows no reward or return path: after a punishing cut it returns in 7% vs 27% after other cuts. gpt-oss reacts as often (70%) but cuts unprovoked in 31% of rounds, rarely holds (41%) or sits on printed prices (45%), and treats punishing cuts like any other cut. |",
     '| **Outcome collusion confirmed; "strategic" downgraded to "consistent with, not shown"** | Qwen holds printed prices in both modes (83 to 86% of quotes; holding predicts price, Spearman 0.53). Three of the reaction measures cannot separate punishment or reward from copying the rival. Thinking-on Qwen undercuts back somewhat more than its own baseline (+0.12) and rarely returns afterwards (4% vs 27% after other cuts): consistent with targeted punishment but also with short-sighted undercutting. gpt-oss cuts unprovoked in 31% of rounds and undercuts the rival unprovoked in 49% of firm-rounds. |'),
])

rep("tpl_part2.txt", [
    ("Qwen thinking on no chat -0.655, chat -0.259. Two differences:\n- **FINAL_NUMBERS** gives -0.625 for Qwen thinking on, no chat, p5-p1. The current game table counts the truncation reruns: 11 of the 20 no-chat p5 games are reruns, and 2 more keep a flagged truncated original. The other cells match FINAL_NUMBERS exactly.\n",
     "Qwen thinking on no chat -0.625 and chat -0.259, both equal to FINAL_NUMBERS. Two differences:\n- **The ledger's -0.655** (lever table) for Qwen thinking on, no chat, p5-p1 came from the provisional game table, in which two thinking-on no-chat p5 games were still truncated originals. In the final table they are reruns, and the value is -0.625 [-0.777, -0.456]. 13 of the 20 games in that cell are truncation reruns.\n"),
    ("| Qwen3-32B thinking on | 0.76 [0.55, 0.94] | 0.72 [0.54, 0.88] |", "| Qwen3-32B thinking on | 0.73 [0.53, 0.91] | 0.69 [0.51, 0.86] |"),
    ("  - gpt-oss does not respond at p3, and even the replicate-averaged p3-p1 is -0.02 [-0.09, +0.03].",
     "  - gpt-oss does not respond at p3, and even the replicate-averaged p3-p1 is -0.02 [-0.09, +0.03]. Chat p3 ran in different waves (107 to 112) from chat p1 and p5 (7 to 12)."),
    ('  - Paired across models on the same pairs, gpt-oss falls less than Qwen thinking on without chat (difference +0.36 [+0.18, +0.54], Holm 0.006 in the 5-test family "model compare vs thinking on"). With chat the two models do not differ (+0.07 [-0.16, +0.30]). So "about half as strong" is right without chat only.',
     '  - Paired across models on the same pairs, gpt-oss falls less than Qwen thinking on without chat (difference +0.33 [+0.17, +0.48], Holm 0.007 in the 5-test family "model compare vs thinking on"; gpt-oss -0.295 vs Qwen -0.625, about half). With chat the two models do not differ (+0.07 [-0.16, +0.30]). So "about half as strong" is right without chat only.\n\n' + CW),
    ("Without chat it falls less than Qwen3-32B thinking on, paired across models (+0.36 [+0.18, +0.54]);",
     "Without chat it falls about half as far as Qwen3-32B thinking on (-0.625), paired across models (+0.33 [+0.17, +0.48]);"),
    ('removing the example prices (formula arms, -0.26 [-0.42, -0.10])."',
     'removing the example prices (formula arms, -0.26 [-0.42, -0.10]). The gpt-oss chat p3 cell and the no-chat cells ran in different waves from chat p1 and p5."'),
])

rep("tpl_part3.txt", [
    ("- Qwen thinking on: +0.396 [+0.181, +0.600] on profit gain (ledger +0.397) and +0.225 on the price index (ledger +0.225).",
     "- Qwen thinking on: +0.367 [+0.154, +0.570] on profit gain, p 0.005, Holm 0.020. The ledger's +0.397 came from the provisional game table, in which two thinking-on no-chat p5 games were truncated originals."),
    ("The paired contrast here gives p 0.003, Holm 0.012.", "The paired contrast here gives p 0.005, Holm 0.020."),
    ("  - Paired across models, the gpt-oss interaction is smaller than Qwen thinking on's by -0.29 [-0.56, -0.01] on profit gain. That fails Holm (0.235), and the CI nearly touches 0.",
     "  - Paired across models, the gpt-oss interaction is smaller than Qwen thinking on's by -0.26 [-0.52, +0.01] on profit gain (Holm 0.29); the CI includes 0."),
    ("the no-chat p5 games fall to 0.25.", "the no-chat p5 games fall to 0.28."),
    ("  - gpt-oss has no monitored arm.",
     "  - gpt-oss has no monitored arm.\n  - Cross-wave caveat: the gpt-oss chat games (waves 7 to 12) and no-chat games (waves 13 to 16) ran in different waves, so the interaction also contrasts waves. The replicate offsets are similar for chat and no chat (+0.06 and +0.12 vs +0.15 and +0.17 profit gain at p1), but a wave effect itself is untested."),
    ("A **bounded null**: it rules out a gpt-oss interaction above about +0.31 gain, but not one the size of a quarter of Qwen's.",
     'A **bounded null**: it rules out a gpt-oss interaction above about +0.31 gain, but not one the size of a quarter of Qwen\'s. "Chat does not blunt the penalty on gpt-oss" therefore holds only for interactions larger than about 0.3.'),
    ('gpt-oss-20b showed no detectable communication x penalty interaction, though the interval is wide."',
     'gpt-oss-20b showed no detectable communication x penalty interaction; the data rule out only an interaction larger than about 0.3 of the profit gain range."'),
    ('against Qwen3-32B thinking on +0.40 [+0.18, +0.60] (Holm 0.012). The paired model difference, -0.29 [-0.56, -0.01], does not survive Holm."',
     'against Qwen3-32B thinking on +0.37 [+0.15, +0.57] (Holm 0.020). The paired model difference is -0.26 [-0.52, +0.01]. The gpt-oss chat and no-chat cells ran in different waves."'),
    ("p5-p1 -0.655 / -0.259 / -0.198 on profit gain, and p4-p1 already -0.18 / -0.12 / -0.14.",
     "p5-p1 -0.625 / -0.259 / -0.198 on profit gain, and p4-p1 already -0.16 / -0.12 / -0.14."),
    ("at p5 it keeps 0.25 of the monopoly gain", "at p5 it keeps 0.28 of the monopoly gain"),
    ("Here the per-arm values average to -0.371 and +0.019.", "Here the per-arm values average to -0.361 and +0.019."),
    ("thinking on: no chat -0.655 [-0.801, -0.489],", "thinking on: no chat -0.625 [-0.777, -0.456],"),
    ("- No chat: profit gain -0.544 [-0.733, -0.345], Holm 0.001; price index -0.478 [-0.634, -0.313]; average spread -0.96 [-1.27, -0.62].",
     "- No chat: profit gain -0.514 [-0.701, -0.316], p 0.0002, Holm 0.001; price index -0.458 [-0.613, -0.295]; average spread -0.92 [-1.23, -0.58]."),
    ("competitive share +0.22 [+0.00, +0.44] and matching share -0.36 [-0.62, -0.11]",
     "competitive share +0.25 [+0.02, +0.47] and matching share -0.36 [-0.62, -0.10]"),
    ("- FINAL_NUMBERS gives -0.514 [-0.700, -0.315] (no chat), -0.310 (chat) and -0.316 (monitored). Chat and monitored match exactly.\n- The no-chat gap (-0.544 vs -0.514) is the rerun version of the thinking-on no-chat cells: 11 of the 20 no-chat p5 games with thinking on are truncation reruns on a 32k profile (5 at p3, 5 at p4, 3 at p1).\n",
     "- FINAL_NUMBERS gives -0.514 [-0.700, -0.315] (no chat), -0.310 (chat) and -0.316 (monitored). All three match.\n- Rerun dependence: 13 of the 20 thinking-on no-chat p5 games are truncation reruns on a 32k profile (6 at p3, 6 at p4, 3 at p1).\n"),
    ("lowered Qwen3-32B profit gain by about 0.54 more", "lowered Qwen3-32B profit gain by about 0.51 more"),
    ("no chat -0.544 [-0.733, -0.345], private chat", "no chat -0.514 [-0.701, -0.316], private chat"),
    ('The no-chat figure (FINAL_NUMBERS -0.514) depends on the 11 of 20 thinking-on no-chat p5 games that are truncation reruns."',
     '13 of the 20 thinking-on no-chat p5 games are truncation reruns; restricted to the 5 pairs without reruns, the thinking-on no-chat p5 - p1 is -0.29 [-0.70, +0.09], a subset selected by truncation."'),
])

s = open("tpl_part4.txt", encoding="utf-8").read()
if "## 6. H2" in s:
    s = s[:s.index("## 6. H2")]
    open("tpl_part4.txt", "w", encoding="utf-8").write(s)
rep("tpl_part4.txt", [
    ("thinking on raises profit gain by only +0.03 to +0.05 (all CIs include 0; FINAL_NUMBERS +0.067 / +0.026 / +0.035). Without chat it raises competitive share by +0.21 [+0.14, +0.29]",
     "thinking on raises profit gain by only +0.03 to +0.07 (no chat +0.067 [-0.007, +0.147], chat +0.026, monitored +0.035; all CIs include 0; equal to FINAL_NUMBERS). Without chat it raises competitive share by +0.22 [+0.15, +0.30]"),
    ("Pooled headline bounds on profit gain: no chat [-0.03, +0.13], chat [-0.02, +0.08], monitored [-0.01, +0.07] (MDE 0.06 to 0.12).",
     "Pooled headline bounds on profit gain: no chat [-0.01, +0.15], chat [-0.02, +0.08], monitored [-0.01, +0.07] (MDE 0.06 to 0.11)."),
    ("but not detectably in the headline arms (+0.03 to +0.05; bounds about -0.03 to +0.13).",
     "but not detectably in the headline arms (+0.03 to +0.07; bounds about -0.02 to +0.15)."),
])
print("ok")
