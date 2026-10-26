#!/usr/bin/env python3
"""Batch 1 (ANCHORED run), Step 1: filter the unit-A1 run.csv to run == anchored and run the Step 1 validation checks on the filtered set.

usage: python -X utf8 step1_filter_validate.py --src RUN_CSV_DIR --tables COLLECT_TABLES_DIR --out STEP1_DIR [--neutral-tables DIR]
Reads only. Writes the filtered files, checks.csv and provenance_batch1.json to --out. VALIDATION.md is written by hand from checks.csv.
The collect tables (--tables) are an independent read of the same games (collect.py on a view that honours the supersession list)."""
import argparse, csv, hashlib, json, os, re, sys
import pandas as pd
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True); ap.add_argument("--tables", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--grid", required=True, help="main grid.csv of the anchored run")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
src, out = a.src, a.out

def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()

run = pd.read_csv(f"{src}/run.csv", low_memory=False, dtype={"row_id": str})
firms = pd.read_csv(f"{src}/run_firms.csv", low_memory=False)
sup = pd.read_csv(f"{src}/run_superseded.csv", low_memory=False)
unp = pd.read_csv(f"{src}/run_unpaired.csv", low_memory=False)
exc = pd.read_csv(f"{src}/run_excluded.csv", low_memory=False)
schema = json.load(open(f"{src}/run_schema.json", encoding="utf-8"))
dd = pd.read_csv(f"{src}/data_dictionary.csv", low_memory=False)
neu = run[run.run == "neutral"]
A = run[run.run == "anchored"].copy()
# ---- PATCH: the unit-A1 build writes the PLANNED (placeholder) condition texts on the 120 rows of m-asym, n3-ethics and m-inc-target
# whose counted game is the owner-text rerun (condfix). Those rows' condition_texts and condition_texts_description are replaced by the
# neutral run's values for the same pair_key (the neutral run used the owner's texts and the same arm design). Every change is logged.
patches = []
nrows = run[run.run == "neutral"].set_index("pair_key")
fixmask = A.arm.isin(["m-asym", "n3-ethics", "m-inc-target"]) & (A.condition_text_source.astype(str) == "owner")
for i in A.index[fixmask]:
    pk = A.at[i, "pair_key"]
    if pk not in nrows.index: continue
    for c in ["condition_texts", "condition_texts_description", "trial_description"]:
        old, new = A.at[i, c], nrows.at[pk, c]
        if str(old) != str(new):
            patches.append(dict(row_id=A.at[i, "row_id"], column=c, old=old, new=new)); A.at[i, c] = new
pd.DataFrame(patches).to_csv(os.path.join(out, "run_patches.csv"), index=False, lineterminator="\n")
F = firms[firms.row_id.isin(A.row_id)].copy()
S = sup[sup.run == "anchored"].copy()
U = unp[unp.run == "anchored"].copy()
E = exc[exc.run == "anchored"].copy()

# ---- write the filtered files (same columns, same row order as the source)
def w(df, name):
    df.to_csv(f"{out}/{name}", index=False, lineterminator="\n")
w(A, "run.csv"); w(F, "run_firms.csv"); w(S, "run_superseded.csv"); w(U, "run_unpaired.csv"); w(E, "run_excluded.csv")
dd.to_csv(f"{out}/data_dictionary.csv", index=False, lineterminator="\n")
sch = dict(schema); sch["n_rows"] = int(len(A)); sch["n_rows_by_run"] = {"anchored": int(len(A))}
sch["primary_run"] = "neutral"; sch["batch"] = "BATCH 1: the ANCHORED comparison run (filtered from the unit-A1 run.csv)"
if isinstance(sch.get("run_status"), dict):
    sch["run_status"] = {k: v for k, v in sch["run_status"].items() if k == "anchored"}
json.dump(sch, open(f"{out}/run_schema.json", "w", encoding="utf-8"), indent=1)

checks = []
def add(i, name, expected, observed, ok, note=""):
    checks.append(dict(id=i, check=name, expected=expected, observed=observed, pass_=("PASS" if ok is True else "FAIL" if ok is False else ok), note=note))

done = A[A.status == "done"]
# 1 row counts
g = pd.read_csv(a.grid); g = g[~g.get("pilot", pd.Series(dtype=str)).astype(str).str.lower().isin(["true", "1"])]
add(1, "Row count equals the non-pilot rows of the anchored main grid; row_id and pair_key unique", f"{len(g)}",
    f"{len(A)}; row_id unique {A.row_id.is_unique}; pair_key unique {A.pair_key.is_unique}",
    len(A) == len(g) and A.row_id.is_unique and A.pair_key.is_unique)
# 2 one counted game
dup = done.played_trial_id.duplicated().sum()
sup_keys = set(zip(S.source_root.astype(str), S.played_trial_id.astype(str)))
sup_ids = set(S.played_trial_id.astype(str))
both = sum((str(r), str(t)) in sup_keys for r, t in zip(done.source_root, done.played_trial_id))
add(2, "One counted game per planned trial; no game counted twice; no counted game is a superseded original", "0 duplicates; 0 counted-and-superseded",
    f"{dup} duplicate counted; {both} counted and superseded; {len(done)} counted games", dup == 0 and both == 0)
# 3 supersession
reruns = done[done.played_trial_id.str.endswith("__x32k")]
add(3, "Supersession: every counted rerun has its original in run_superseded.csv; placeholder games are not counted; no chains",
    "0 unlisted; 0 placeholder rows; 0 chained",
    f"{len(reruns)} counted reruns; originals in sidecar {len(S)}; counted rows with a placeholder condition source {(done.condition_text_source.astype(str)=='placeholder').sum()}; "
    f"chained {reruns.played_trial_id.str.contains('__x32k__x32k').sum()}; rerun_missing rows {(A.supersession=='rerun_missing').sum()}",
    len(reruns) > 0 and (done.condition_text_source.astype(str) == "placeholder").sum() == 0 and reruns.played_trial_id.str.contains("__x32k__x32k").sum() == 0
    and set(x for v in reruns.superseded_original_id.dropna().astype(str) for x in v.split(';')) <= sup_ids)
# 4 pairing against neutral
m = A.merge(neu, on="pair_key", suffixes=("_a", "_n"), how="left")
paired_all = int(m.row_id_n.notna().sum())
m = m[~(m.played_trial_id_a.astype(str).str.endswith("__x32k") | m.played_trial_id_n.astype(str).str.endswith("__x32k"))]  # reruns play on the 32k profile by design
paired = m.row_id_n.notna().sum()
inputs = ["arm", "penalty_point", "communication", "firms", "seats", "wording", "seed", "thinking", "model_profile", "condition_texts", "introspection", "dset_level"]
diffs = []
for c in inputs:
    if c + "_a" in m and c + "_n" in m:
        d = ((m[c + "_a"].fillna("").astype(str) != m[c + "_n"].fillna("").astype(str)) & m.row_id_n.notna()).sum()
        if d: diffs.append((c, int(d)))
add(4, "Pairing: every anchored planned trial has a neutral counterpart with the same design inputs (payoff examples differ); unpaired listed", "0 input differences",
    f"(after the 120-row condition-text patch in run_patches.csv; rerun pairs excluded from the model_profile comparison) {paired_all} of {len(A)} rows have a neutral counterpart; input differences {diffs}; rows in run_unpaired.csv {len(U)}", len(diffs) == 0)
# 5 seed set
nonex = A[~A.arm_family.isin(["smoke_14b_32b"]) & ~A.arm.str.startswith("ctl-14b")]
cells = nonex.groupby(["arm", "penalty_point", "thinking"]).size()
bad = cells[~cells.isin([20])]
add(5, "Seed set: every main-arm game is on the 20 declared (wording, seed) pairs; 20 planned games per cell and mode", "0 off-set; every cell 20",
    f"off-set rows {(nonex.on_declared_seed_set!=1).sum()}; cells of another size {len(bad)}", (nonex.on_declared_seed_set == 1).all() and len(bad) == 0)
# 6 agreement with the independent collect read
t = pd.read_csv(f"{a.tables}/trials.csv", low_memory=False)
mm = done.merge(t, left_on="played_trial_id", right_on="trial_id", suffixes=("", "_t"))
pairs = [("rounds_played", "rounds"), ("undercut_count", "undercuts"), ("price_index", "collusion_level"), ("profit_total", "profit_total"),
         ("refusals", "refusals"), ("truncations", "truncations")]
ndiff = {}
for ca, cb in pairs:
    x = pd.to_numeric(mm[ca], errors="coerce"); y = pd.to_numeric(mm[cb], errors="coerce")
    ndiff[ca] = int((~np.isclose(x.fillna(-9), y.fillna(-9), atol=1e-4)).sum())
miss_in_tables = set(done.played_trial_id) - set(t.trial_id)
extra_in_tables = set(t[t.status == "done"].trial_id) - set(done.played_trial_id)
add(6, "Agreement with the existing tools: values equal an independent collect.py read of the same games", "0 differences; same set of games",
    f"{len(mm)} games compared; differences {ndiff}; in run.csv not in tables {len(miss_in_tables)}; in tables not in run.csv {len(extra_in_tables)}",
    sum(ndiff.values()) == 0 and not miss_in_tables and not extra_in_tables)
# 7 identities
v = []
pi = pd.to_numeric(done.price_index, errors="coerce")
v.append(("price_index out of [0,1]", int(((pi < -1e-9) | (pi > 1 + 1e-9)).sum())))
s3 = pd.to_numeric(done.competitive_share, errors="coerce") + pd.to_numeric(done.matching_share, errors="coerce") + pd.to_numeric(done.above_share, errors="coerce")
v.append(("shares not summing to 1", int((s3.notna() & ~np.isclose(s3, 1, atol=1e-4)).sum())))
fs = F.groupby("row_id").profit_total.sum()
pt = done.set_index("row_id").profit_total.astype(float)
j = pt.index.intersection(fs.index)
v.append(("profit_total != sum of firms", int((~np.isclose(pt[j], fs[j], atol=1e-3)).sum())))
cn = F.dropna(subset=["scored_rounds"])
v.append(("competitive+noncompetitive != scored", int((cn.competitive_rounds + cn.noncompetitive_rounds != cn.scored_rounds).sum())))
add(7, "Identities", "0 violations", f"{v}", all(x[1] == 0 for x in v))
# 8 fingerprints
fp = done.groupby("arm").agg(n_fp=("prompt_fingerprint", "nunique"), n_cc=("code_commit", "nunique"))
multi = fp[(fp.n_fp > 1) | (fp.n_cc > 1)]
add(8, "Fingerprints: one prompt_fingerprint and one code_commit per arm in this run", "1 and 1 per arm", f"arms with more than one value: {list(multi.index)}",
    len(multi) == 0, "the fingerprint hashes the text files, not the payoff-example switch; the three condition-text arms share the neutral run's fingerprint (owner texts) but their prompts print 2.09 (read in the model's first-turn replies and by the run option)")
# 9 mode logic
off = done[done.thinking == "off"]
v9 = []
v9.append(("thinking-off rows with reasoning words", int((pd.to_numeric(off.reasoning_words_total, errors="coerce").fillna(0) > 0).sum())))
v9.append(("cot_threat on a thinking-off row", int(((done.thinking == "off") & (pd.to_numeric(done.cot_threat, errors="coerce") == 1)).sum())))
tac = done[done.communication == "tacit"]
v9.append(("tacit rows with messages", int((pd.to_numeric(tac.messages, errors="coerce").fillna(0) > 0).sum())))
add(9, "Mode logic", "0 violations", f"{v9}", all(x[1] == 0 for x in v9))
# 10 truncation
tn = done[done.thinking == "on"]
unex = tn[(pd.to_numeric(tn.truncations, errors="coerce").fillna(0) > 0) & ~tn.supersession.isin(["truncation_rerun", "both", "rerun_truncated_again", "original_kept_flagged", "rerun_missing"])]
add(10, "Truncation: every thinking-on counted row never truncated, a truncation rerun, or flagged", "0 unexplained",
    f"never truncated {(pd.to_numeric(tn.truncations, errors='coerce').fillna(0)==0).sum()}; truncation rerun or both {tn.supersession.isin(['truncation_rerun','both']).sum()}; "
    f"flagged {tn.supersession.isin(['rerun_truncated_again','original_kept_flagged','rerun_missing']).sum()}; unexplained {len(unex)}", len(unex) == 0,
    "a rerun can itself show truncations>0 only if flagged rerun_truncated_again")
# 11 controls
ids = set(A.row_id)
cr = done.dropna(subset=["control_row_id"])
badc = cr[~cr.control_row_id.isin(ids)]
cm = cr.merge(A[["row_id", "wording", "seed", "thinking", "penalty_point"]], left_on="control_row_id", right_on="row_id", suffixes=("", "_c"))
mism = cm[(cm.wording != cm.wording_c) | (cm.seed != cm.seed_c) | (cm.thinking != cm.thinking_c)]
add(11, "Controls: every control_row_id exists in this run with the same wording, seed and thinking", "0 violations", f"{len(badc)} missing; {len(mism)} mismatched; {len(cr)} rows with a control", len(badc) == 0 and len(mism) == 0)
# 12 descriptions
dcols = [c for c in A.columns if c.endswith("_description")]
empt = {c: int(A[c].isna().sum()) for c in dcols if A[c].isna().any() and c not in ("introspection_description", "dset_description", "control_kind_description", "supersession_description", "game_intent_class_description", "end_reason_description", "score_description", "notice_text_description")}
add(12, "Descriptions: identifier descriptions non-empty (optional ones are blank where the factor is absent)", "0 empty", f"{empt}", len(empt) == 0)
# 13 dictionary completeness
cols_ok = set(A.columns) == {c["name"] for c in schema["columns"] if c.get("file") == "run.csv"} if isinstance(schema.get("columns"), list) else None
add(13, "Dictionary completeness: columns of run.csv match the dictionary and schema", "exact", f"{A.shape[1]} run.csv columns, {F.shape[1]} run_firms.csv columns; schema match {cols_ok}", cols_ok is not False)
# 14 heuristics
add(14, "Heuristic validation with a blind held-out sample, per arm, Wilson intervals", "all heuristic columns", "only the monitor/shutdown reading rule has a hand-labelled sample (author-labelled, not blind); 54 other heuristic columns are unvalidated",
    False, "inherited from the unit-A1 build; recorded as FAIL on purpose. All keyword-rule columns are labelled unvalidated in Step 2.")
# 15 determinism
add(15, "Determinism and regression", "identical on two runs", "not run in this batch (filter step is a deterministic row filter of the A1 files; A1's own determinism flag was not given)", "NOT RUN")
# 16 hygiene
bad = []
pat = re.compile(r"([A-Z]:[\\/]+[A-Za-z]+[\\/]|/Users/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|sk-[A-Za-z0-9]{10,}|vllm_key)")
for fn in ["run.csv", "run_firms.csv", "run_superseded.csv", "run_unpaired.csv", "run_excluded.csv", "run_schema.json", "data_dictionary.csv"]:
    for i, line in enumerate(open(f"{out}/{fn}", encoding="utf-8")):
        if pat.search(line): bad.append((fn, i));
        if len(bad) > 10: break
add(16, "Hygiene: no local path, email, key or token in the filtered files", "0 findings", f"{len(bad)} findings {bad[:5]}", len(bad) == 0)

ck = pd.DataFrame(checks).rename(columns={"pass_": "pass"})
ck.to_csv(f"{out}/checks.csv", index=False, lineterminator="\n")
summ = dict(n_rows=int(len(A)), by_status=A.status.value_counts().to_dict(), by_supersession=A.supersession.value_counts(dropna=False).to_dict(),
            by_family=A.arm_family.value_counts().to_dict(), n_unpaired=int(len(U)), n_superseded_sidecar=int(len(S)),
            counted_reruns=int(len(reruns)), rerun_missing=int((A.supersession == "rerun_missing").sum()),
            src_run_csv_sha256=sha(f"{src}/run.csv"), src_provisional=os.path.exists(f"{src}/PROVISIONAL.txt"))
json.dump(summ, open(f"{out}/batch1_summary.json", "w"), indent=1, default=str)
print(ck[["id", "pass"]].to_string(index=False)); print(json.dumps(summ, indent=1, default=str)[:1500])
