#!/usr/bin/env bash
# End-to-end post-run pipeline (bash; MOCK or real shards).  Usage: run_pipeline.sh <repo> <shards-root> <out-dir> <bands.csv> [plan.tsv]
# Stages: 1 ingest_merge (validate, merge, de-dup, tidy tables, QC gate)  2a tools/analysis.py (frozen, pre-declared family)
#         2b exploratory_contrasts.py (BH family)  3 ledger.py (gate + findings ledger)  4 summarize.py (summary + next steps)
set -u
REPO=$1; SHARDS=$2; OUT=$3; BANDS=$4; PLAN=${5:-}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
cd "$REPO"
PLANARG=""; [ -n "$PLAN" ] && PLANARG="--plan $PLAN"
python -X utf8 "$HERE/ingest_merge.py" --shards "$SHARDS" $PLANARG --cells "${CELLS:-$HERE/design_cells.csv}" --predeclared-design "${PREDECL:-$HERE/predeclared_design.json}" --repo . --out "$OUT" > "$OUT/stage1.log" 2>&1
echo "stage 1 ingest_merge: exit $? ($(tail -1 "$OUT/stage1.log"))"
python -X utf8 tools/analysis.py --runs "$OUT/merged_runs.jsonl" --bands "$BANDS" --design "$OUT/predeclared_design.json" --out "$OUT/analysis_report.txt" --json "$OUT/analysis.json"
echo "stage 2a tools/analysis.py: exit $?"
python -X utf8 "$HERE/exploratory_contrasts.py" --repo . --runs "$OUT/merged_runs.jsonl" --contrasts "${CONTRASTS:-$HERE/design_contrasts.csv}" --cells "${CELLS:-$HERE/design_cells.csv}" --bands "$BANDS" --out "$OUT" > "$OUT/stage2b.log" 2>&1
echo "stage 2b exploratory_contrasts: exit $?"
python -X utf8 "$HERE/ledger.py" --repo . --analysis "$OUT/analysis.json" --exploratory "$OUT/exploratory.json" --qc "$OUT/qc.json" --contrasts "${CONTRASTS:-$HERE/design_contrasts.csv}" --cells "${CELLS:-$HERE/design_cells.csv}" --runs "$OUT/runs.csv" --out "$OUT/ledger.csv" > "$OUT/stage3.log" 2>&1
echo "stage 3 ledger: exit $? ($(head -1 "$OUT/stage3.log"))"
python -X utf8 "$HERE/summarize.py" --ledger "$OUT/ledger.csv" --qc "$OUT/qc.json" --runs "$OUT/runs.csv" --out "$OUT/summary.md" --next "$OUT/next_steps.md"
echo "stage 4 summarize: exit $?"
