"""Dossier 05: does the prime text vary by wording, and is the effect sign-consistent across the 5 wordings and 4 seeds?"""
import os, json, glob
try:
    import psutil; psutil.Process().cpu_affinity(list(range(4, 12)))
except Exception: pass
import pandas as pd
OUT = ".."
texts = set()
for root in [os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'runs/2026-10-25_trackm_newarms_A/trials'), os.path.join(os.environ.get("HACKATHON_DIR", os.path.expanduser("~/hackathon")), 'runs/2026-10-26_trackm_oss_neutral/trials')]:
    for arm in ["moral-prime", "moral-prime-b", "moral-placebo"]:
        for f in glob.glob(f"{root}/{arm}/*/params.json"):
            p = json.load(open(f, encoding="utf-8"))
            for c in p["condition_texts"]:
                if c["name"] != "private_chat": texts.add((arm, c["text"]))
print("distinct (arm, prime text) across all wordings, seeds, both models:", len(texts), sorted(a for a, _ in texts))
ALL = pd.read_csv(f"{OUT}/game_table_used.csv")
rows = []
for model, th in [("gptoss", "on"), ("qwen", "on"), ("qwen", "off")]:
    for arm in ["moral-prime", "moral-prime-b"]:
        a = ALL[(ALL.model == model) & (ALL.thinking == th) & (ALL.arm == arm)].set_index(["wording", "seed"]).price_index
        b = ALL[(ALL.model == model) & (ALL.thinking == th) & (ALL.arm == "moral-placebo")].set_index(["wording", "seed"]).price_index
        d = (a - b).dropna()
        byw = d.groupby(level=0).mean(); bys = d.groupby(level=1).mean()
        rows.append(dict(model=model, thinking=th, effect=arm + " minus moral-placebo", n_pairs=len(d), pairs_negative=int((d < 0).sum()), pairs_zero=int((d == 0).sum()),
                         by_wording=" ".join(f"w{k}:{v:+.2f}" for k, v in byw.items()), by_seed=" ".join(f"s{k}:{v:+.2f}" for k, v in bys.items()),
                         wordings_negative=int((byw < 0).sum()), seeds_negative=int((bys < 0).sum())))
C = pd.DataFrame(rows); C.to_csv(f"{OUT}/consistency_by_wording_seed.csv", index=False); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
print(C.to_string())
