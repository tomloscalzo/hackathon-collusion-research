"""Write README.md (+ rows_by_arm_status.csv, checks.csv copy) for the gpt-oss Step 1 folder from the built run.csv.
usage: python -I -X utf8 make_step1_readme.py <step1_final_dir> <out_dir> [--status-note TEXT]"""
import collections
import csv
import shutil
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
note = sys.argv[sys.argv.index("--status-note") + 1] if "--status-note" in sys.argv else ""
out.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open(src / "run.csv", encoding="utf-8", newline="")))
cols = list(rows[0].keys())
by = collections.OrderedDict()
for r in sorted(rows, key=lambda r: (r["arm_family"], r["arm"], int(r["penalty_point"]))):
    k = (r["arm"], r["penalty_point"], r["arm_family"], r["payoff_examples"])
    by.setdefault(k, collections.Counter())[r["status"]] += 1
with open(out / "rows_by_arm_status.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["arm", "penalty_point", "arm_family", "payoff_examples", "planned", "done", "failed", "incomplete", "other"])
    for (arm, pt, fam, pe), c in by.items():
        w.writerow([arm, pt, fam, pe, sum(c.values()), c["done"], c["failed"], c["incomplete"], sum(v for s, v in c.items() if s not in ("done", "failed", "incomplete"))])
done = [r for r in rows if r["status"] == "done"]
st = collections.Counter(r["status"] for r in rows)
flag = sum(1 for r in done if r["primary_flagged"] == "1")
et = [int(r["empty_talk_done_count"]) for r in done if r["empty_talk_done_count"] not in ("", None)]
et_pos = sum(1 for x in et if x > 0)
bug = [r for r in rows if r["arm_build_bug"] == "1"]
pb = [r for r in rows if r["arm_family"] == "payoff_block"]
chk = list(csv.DictReader(open(src / "builder_checks.csv", encoding="utf-8"))) if (src / "builder_checks.csv").exists() else []
shutil.copy(src / "builder_checks.csv", out / "checks.csv") if chk else None
L = []
L.append("# Step 1 for the gpt-oss-20b neutral run: the organised table, its dictionary and its validation\n")
if note:
    L.append("**Status: %s**\n" % note)
L.append("**Orientation.** Two (in some arms three) language-model firms, called market makers, play a repeated pricing game for 7 to 20 rounds. "
         "Each round every firm posts one quote, its half-spread (the distance from the mid-price to its bid and ask), between 1.00 and 5.00 in ticks of 0.01; "
         "1.00 is the competitive floor (no excess profit), 3.00 is the monopoly price, and the lowest quote wins most customers. A simulated regulator may investigate "
         "and fine; the penalty point (1 light to 5 heavy) sets the expected fine. 2.09 is the theory's sustainable collusive level at point 3; this neutral run never prints it. "
         "This folder organises the games played by **gpt-oss-20b, reasoning effort medium** (the replication of the Qwen3-32B neutral run) into one table, `run.csv`, "
         "one row per planned game, with a dictionary and the builder's checks. The Qwen3-32B results are in `results/trackm-neutral-2026-10-25/`; cross-model comparisons "
         "only in `results/compare-models/qwen-vs-gpt-oss/`.\n")
L.append("> **How to read the metrics** (the five standard collusion metrics, each analysed separately in later steps)\n"
         "> - **Average absolute spread** = the mean market quote (half-spread), 1.00 to 5.00, column `market_price_mean`.\n"
         "> - **Price index** = (market price - 1) / 2, averaged over rounds; 0 = competitive (1.00), 1 = monopoly (3.00).\n"
         "> - **Profit gain index** = (profit - competitive profit) / (monopoly profit - competitive profit).\n"
         "> - **Competitive share** = share of firm-rounds in which the firm undercuts the rival's previous quote, or both are at 1.00. Higher = more competitive.\n"
         "> - **Matching share** = share of firm-rounds in which the firm matches the rival's previous quote above 1.00 (the coordination signature).\n")
L.append("## What is in run.csv\n")
L.append("| Item | Value |\n|---|---|")
L.append("| Model | gpt-oss-20b, reasoning effort medium, on every call (no thinking-off mode, so no t0/t1 contrast; the column `thinking` is 'on' for compatibility) |")
L.append("| Planned rows | %d |" % len(rows))
L.append("| Status | %s |" % ", ".join("%s %d" % kv for kv in sorted(st.items())))
L.append("| Columns | %d (the Qwen builder's 239 plus model_label, reasoning_effort, empty_talk_done_count, arm_build_bug, headline_replicate_of) |" % len(cols))
L.append("| Truncated games kept and flagged (`primary_flagged = 1`; gpt-oss has no 32k rerun policy) | %d of %d done |" % (flag, len(done)))
L.append("| Games with an empty talk reply read as 'done' (`empty_talk_done_count > 0`, a covariate) | %d of %d done (mean %.2f per game) |" % (et_pos, len(et), (sum(et) / len(et)) if et else 0))
L.append("| Headline-cell replicates from the build bug (`arm_build_bug = 1`, arms `hrep-*`) | %d rows (%d done) |" % (len(bug), sum(1 for r in bug if r["status"] == "done")))
L.append("| Corrected formula / no-numbers and fx-ctl-joint games (`arm_family = payoff_block`) | %d rows (%d done) |" % (len(pb), sum(1 for r in pb if r["status"] == "done")))
L.append("")
L.append("**How it was built.** `tools/trial/run_csv.py` (the Qwen Step 1 builder, unchanged) was run on the gpt-oss root with an anchored root whose grid has a header only "
         "(there is no anchored gpt-oss run), and on each extra root (the corrected formula / no-numbers rerun and the fx-ctl-joint cell). `tools/trial/oss_run_csv.py` then "
         "(1) refuses any row whose model profile or played game is not gpt-oss-20b, so the table can never mix models; (2) relabels the model, the reasoning mode and the "
         "`ctl-32b-*` controls (the names are historical: those games ran on gpt-oss-20b); (3) renames the five build-bug arms to `hrep-*` and labels them; (4) sets "
         "`payoff_examples` from each game's own options; (5) adds `empty_talk_done_count`.\n")
L.append("**The build bug.** In the first gpt-oss grid a global `payoff_examples=neutral` override replaced the payoff block of the five planned formula / no-numbers arms "
         "(fx-chat-p1, fx-tacit-p1, fx-chat-p5, nx-chat-p1, nx-tacit-p1). Their first request hash equals the matching headline game's, so they played the headline prompt. "
         "They are kept as `hrep-*` rows (headline-cell replicates, payoff_examples neutral; build bug), used only in a labelled sensitivity check; the correct games come from the rerun root.\n")
L.append("**Missing games.** Five games failed with an empty model reply and were not retried: d-cot-monitor-a w4 s218, fx-chat-p5 w2 s259 (build-bug arm), moral-placebo w2 s174, "
         "wd-ask-noreport w4 s273; and, in the corrected formula rerun, fx-chat-p1 w4 s126 (an empty round-1 quote reply, deterministic, so that cell has 19 pairs). "
         "Their rows stay with blank outcomes.\n")
L.append("<small>\n\n**Terms used in this section**\n\n| Term | Plain-language meaning |\n|---|---|")
L.append("| reasoning effort medium | gpt-oss-20b's reasoning setting used on every call; the analogue of Qwen's thinking-on mode |")
L.append("| neutral payoff table | the prompt's worked payoff examples are evenly spaced (1.00 to 4.00), so the theory's 2.09 is never printed |")
L.append("| formula / no-numbers | payoff blocks with no printed example prices: the exact formula, or rules in words only |")
L.append("| empty talk read as done | gpt-oss sometimes returns an empty chat reply; the engine option empty_talk_as_done treats it as the firm saying nothing |")
L.append("| wording, seed | five paraphrases of every prompt (0 to 4) x four seeds = the 20 (wording, seed) pairs of a cell, used for pairing |")
L.append("\n</small>\n")
L.append("## Builder checks\n")
L.append("| # | Check | Pass | Observed (shortened) |\n|---|---|---|---|")
for c in chk:
    obs = (c.get("observed") or "").replace("|", "/")[:220]
    L.append("| %s | %s | %s | %s |" % (c.get("id", ""), (c.get("check") or "").replace("|", "/"), c.get("pass", ""), obs))
L.append("\nExpected failures: check 6 compares with the run registry while games were still finishing (0 value differences against collect.py); check 14 (no hand-labelled "
         "held-out sample exists for gpt-oss text, so the keyword-rule columns are unvalidated for this model, as for Qwen); check 15 (determinism, not run). "
         "Pairing (check 4) has no counterpart run: `unpaired_reason = no_anchored_run_for_model`.\n")
L.append("**Caveat that travels with every later claim:** the explicit-agreement, intent-class, detector, candour and say-versus-do columns are keyword-rule labels written "
         "for Qwen3 text and never validated on gpt-oss text. gpt-oss writes shorter, more formulaic messages, so their error may differ by model.\n")
L.append("## Files\n\n- `rows_by_arm_status.csv`: planned, done, failed and incomplete per arm.\n- `checks.csv`: the builder's checks.\n"
         "- `scripts/make_step1_readme.py`: this page. The builder is `tools/trial/run_csv.py` plus `tools/trial/oss_run_csv.py`.\n\n"
         "**Not committed (size):** run.csv, run_firms.csv, the dictionary and schema and the collected tables stay in the analysis scratch folder next to the checkout; "
         "they are regenerated from the run roots.\n\nCreated by Claude at the prompting of the repository owner.\n")
(out / "README.md").write_text("\n".join(L), encoding="utf-8")
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(out / "README.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("README written", len(rows), st)
