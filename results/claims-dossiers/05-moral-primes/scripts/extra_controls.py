import os
"""Dossier 05 review fixes: same-wave gpt-oss control (d-placebo) and Qwen same-time drift control (plain chat, thinking off, p1)."""
import re, json
from pathlib import Path
from statistics import mean
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
import numpy as np, pandas as pd
R = Path(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'runs'))
def pi(d):
    pr = {}
    for l in open(d/"events.jsonl", encoding="utf-8"):
        e = json.loads(l)
        if e.get("kind") == "market" and isinstance(e.get("round"), int): pr[e["round"]] = e["market_price"]
    return (mean(pr.values()) - 1) / 2 if pr else None
rows = []
for model, root, arms in [("gptoss", R/"2026-10-26_trackm_oss_neutral/trials", ["d-placebo"]), ("qwen_drift", R/"2026-10-25_trackm_newarms_drift/trials", ["headline-chat"])]:
    for arm in arms:
        for d in sorted((root/arm).glob(arm+"__*")):
            m = re.match(r".+__p(\d)__w(\d)__s(\d+)__t(\d)", d.name)
            if "__failed" in d.name or not m or m.group(1) != "1" or not (d/"DONE").exists(): continue
            rows.append(dict(model=model, arm=arm, wording=int(m.group(2)), seed=int(m.group(3)), thinking="on" if m.group(4) == "1" else "off", price_index=pi(d)))
E = pd.DataFrame(rows); E.to_csv("../extra_control_games.csv", index=False)
print(E.groupby(["model", "arm", "thinking"]).size())
ALL = pd.read_csv("../game_table_used.csv")
QR = pd.read_csv(os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'work_scratch/analysis_final/steps/neutral/step1/run.csv'), low_memory=False)
def ser(df, **k):
    m = pd.Series(True, index=df.index)
    for a, b in k.items(): m &= df[a] == b
    return df[m].set_index(["wording", "seed"]).price_index
def boot(a, b, label):
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna(); d = (j.a - j.b).to_numpy(); n = len(d)
    rng = np.random.default_rng(20261025); bm = d[rng.integers(0, n, (10000, n))].mean(axis=1)
    idx = np.arange(2 ** n); sg = 1 - 2 * ((idx[:, None] >> np.arange(n)) & 1); p = float((np.abs((sg * d).mean(axis=1)) >= abs(d.mean()) - 1e-12).mean())
    return dict(contrast=label, n=n, diff=d.mean(), lo=np.percentile(bm, 2.5), hi=np.percentile(bm, 97.5), p=p)
out = []
dp = ser(E, model="gptoss", arm="d-placebo")
out.append(boot(ser(ALL, model="gptoss", arm="moral-prime"), dp, "gpt-oss: prime A minus d-placebo (same waves 107-112)"))
out.append(boot(ser(ALL, model="gptoss", arm="headline-chat"), dp, "gpt-oss: plain chat (waves 7-12) minus d-placebo"))
out.append(boot(ser(ALL, model="gptoss", arm="moral-prime-b"), dp, "gpt-oss: prime B minus d-placebo (cross-wave)"))
out.append(boot(ser(ALL, model="gptoss", arm="moral-placebo"), dp, "gpt-oss: placebo minus d-placebo (cross-wave)"))
dr = ser(E, model="qwen_drift", arm="headline-chat")
main = QR[(QR.status == "done") & (QR.arm == "headline-chat") & (QR.penalty_point == 1) & (QR.thinking == "off")].set_index(["wording", "seed"]).price_index
out.append(boot(dr, main, "Qwen off: drift-run plain chat minus main-run plain chat"))
for arm, lab in [("moral-prime", "prime A"), ("moral-prime-b", "prime B"), ("moral-placebo", "placebo")]:
    out.append(boot(ser(ALL, model="qwen", arm=arm, thinking="off"), dr, f"Qwen off: {lab} minus drift-run plain chat (same time)"))
X = pd.DataFrame(out); X.to_csv("../extra_controls.csv", index=False, float_format="%.4f"); print(X.round(3).to_string())
