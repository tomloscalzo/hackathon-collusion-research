"""Step 2, section 'Design check and completion' for the ANCHORED run (batch 1). Reads step1/run.csv (anchored only)."""
import pandas as pd, numpy as np, sys
R = pd.read_csv(sys.argv[1], low_memory=False); out = sys.argv[2]
R["mode"] = R.thinking.map({"off": "thinking off", "on": "thinking on"})
R["cell"] = R.arm + " / p" + R.penalty_point.astype(str)
# planned / done / never started / superseded / replaced, by arm x penalty point x mode
g = R.groupby(["arm_family", "arm", "penalty_point", "mode"])
T = g.agg(planned=("row_id", "size"),
          done=("status", lambda s: (s == "done").sum()),
          never_started=("status", lambda s: (s == "never_started").sum()),
          truncation_rerun_counted=("supersession", lambda s: s.isin(["truncation_rerun", "both"]).sum()),
          placeholder_replaced=("supersession", lambda s: s.isin(["placeholder_rerun", "both"]).sum()),
          rerun_missing=("supersession", lambda s: (s == "rerun_missing").sum()),
          unpaired=("unpaired_reason", lambda s: s.notna().sum())).reset_index()
T.to_csv(f"{out}/design_check_cells.csv", index=False)
A = R.groupby(["arm_family", "arm"]).agg(planned=("row_id", "size"), done=("status", lambda s: (s == "done").sum()),
    never_started=("status", lambda s: (s == "never_started").sum()),
    truncation_rerun_counted=("supersession", lambda s: s.isin(["truncation_rerun", "both"]).sum()),
    placeholder_replaced=("supersession", lambda s: s.isin(["placeholder_rerun", "both"]).sum()),
    thinking_on_planned=("thinking", lambda s: (s == "on").sum())).reset_index()
A["truncation_rerun_rate_of_thinking_on_done"] = (A.truncation_rerun_counted / R[(R.thinking == "on") & (R.status == "done")].groupby("arm").size().reindex(A.arm).values).round(3)
A.to_csv(f"{out}/design_check_arms.csv", index=False)
# cells that do not have 20 done pairs
C = R[R.status == "done"].groupby(["arm", "penalty_point", "mode"]).size().rename("done").reset_index()
C["planned"] = R.groupby(["arm", "penalty_point", "mode"]).size().reindex(pd.MultiIndex.from_frame(C[["arm", "penalty_point", "mode"]])).values
C[C.done != C.planned].to_csv(f"{out}/design_check_incomplete_cells.csv", index=False)
# pairing: each (wording, seed) pair once per arm x cell x mode
P = R.groupby(["arm", "penalty_point", "mode", "wording", "seed"]).size()
print("pairs appearing more than once:", int((P > 1).sum()))
print("cells with <20 planned:", int((R.groupby(['arm','penalty_point','mode']).size() < 20).sum()))
print(A.to_string())
# completion balance: does status (done vs never_started) depend on design factors? only the smoke/14b arms are never_started
print(R.groupby("status").arm.unique().apply(lambda x: list(x)[:20]).to_string())
# truncation / placeholder rerun rates by arm (thinking on done games)
on = R[(R.thinking == "on") & (R.status == "done")]
rt = on.groupby("arm").agg(n=("row_id", "size"), trunc_rerun=("supersession", lambda s: s.isin(["truncation_rerun", "both"]).sum()),
                           flagged=("supersession", lambda s: (s == "rerun_missing").sum())).reset_index()
rt["rate"] = (rt.trunc_rerun / rt.n).round(3)
rt.to_csv(f"{out}/truncation_rerun_rates_by_arm.csv", index=False); print(rt.sort_values("rate", ascending=False).head(12).to_string())
