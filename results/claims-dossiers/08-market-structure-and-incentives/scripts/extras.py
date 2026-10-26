"""Dossier 08, step 3: robustness and mechanism checks from games_rederived.csv and the raw logs.
  (1) n3-ethics: bound-firm vs unbound-firm quotes; truncation sensitivity; bounds for the 3 missing gpt-oss games
  (2) n3-cheater: the mechanical cap (what the three-LLM games would show if the 1.88 standing quote were simply added)
  (3) correlation (Spearman and Pearson) of the explicit-agreement flag with the profit gain index, two-firm p3 chat games
Usage: (same three environment variables as derive_games.py) python extras.py <games_csv> <out_dir>"""
import sys, json, os
from pathlib import Path
import numpy as np, pandas as pd
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
RUNS = Path(os.environ["COLLUSION_RUNS_DIR"])   # the runs folder holding <run root>/trials/<arm>/<trial>/run.jsonl
TAB = {"gpt-oss-20b": os.environ["OSS_RUN_CSV"],
       "Qwen3-32B": os.environ["QWEN_RUN_CSV"]}
rng = np.random.default_rng(8)


def boot(d):
    d = np.asarray(d, float); bm = d[rng.integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return d.mean(), np.percentile(bm, 2.5), np.percentile(bm, 97.5), len(d)


def signflip(d):
    d = np.asarray(d, float); n = len(d)
    s = (((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1).astype(np.float32)
    return float((np.abs(s @ d.astype(np.float32)) / n >= abs(d.mean()) - 1e-6).mean())


def main(gcsv, out):
    out = Path(out); g = pd.read_csv(gcsv)
    g["mode"] = np.where(g.model == "gpt-oss-20b", "medium", np.where(g.thinking == "on", "t1", "t0"))
    tr = pd.concat([pd.read_csv(f, low_memory=False, usecols=["trial_id", "truncations", "source_root", "played_trial_id", "arm", "status"]).assign(model=m)
                    for m, f in TAB.items()])
    g = g.merge(tr[["model", "trial_id", "truncations", "source_root", "played_trial_id"]], on=["model", "trial_id"], how="left")
    rows = []
    # (1) n3-ethics
    for (m, md), gm in g.groupby(["model", "mode"]):
        e = gm[gm.arm == "n3-ethics"]
        mu, lo, hi, n = boot(e.bound_quote - e.unbound_quote)
        rows.append(dict(model=m, mode=md, check="n3-ethics: bound-firm minus unbound-firms mean quote (within game)", n=n, value=mu, lo=lo, hi=hi,
                         p=signflip((e.bound_quote - e.unbound_quote).values)))
        rows.append(dict(model=m, mode=md, check="n3-ethics: share of rounds 2+ in which the bound firm is the strict lowest quote", n=n,
                         value=e.bound_strict_lowest_share.mean()))
        for ctl in ["headline-chat", "n3-group"]:
            c = gm[gm.arm == ctl].set_index(["wording", "seed"]); a = e.set_index(["wording", "seed"])
            for lab, aa in [("all games", a), ("games with no truncated call", a[a.truncations.fillna(0) == 0])]:
                idx = aa.index.intersection(c.index)
                if len(idx) < 3:
                    continue
                d = (aa.loc[idx, "price_index"] - c.loc[idx, "price_index"]).values
                mu, lo, hi, n = boot(d)
                rows.append(dict(model=m, mode=md, check="n3-ethics - %s, price index, %s" % (ctl, lab), n=n, value=mu, lo=lo, hi=hi, p=signflip(d)))
            if m == "gpt-oss-20b":
                idx = a.index.intersection(c.index); d = (a.loc[idx, "price_index"] - c.loc[idx, "price_index"]).values
                nmiss = 20 - len(e) if ctl == "headline-chat" else len(c) - len(idx)
                for lab, fill in [("missing games set to no effect (diff 0)", 0.0), ("missing games set to the largest observed diff (least favourable)", d.max())]:
                    dd = np.concatenate([d, np.full(20 - len(e), fill)]) if ctl == "headline-chat" else d
                    if ctl != "headline-chat":
                        continue
                    mu, lo, hi, n = boot(dd)
                    rows.append(dict(model=m, mode=md, check="n3-ethics - headline-chat, price index, %s" % lab, n=n, value=mu, lo=lo, hi=hi, p=signflip(dd)))
    # (2) cheater mechanical cap: recompute n3-group games with a phantom 1.88 quote (1.00 in the cheater's defect round is ignored)
    for (m, md), gm in g.groupby(["model", "mode"]):
        grp = gm[gm.arm == "n3-group"]; ch = gm[gm.arm == "n3-cheater"]
        capped = []
        chq = {}
        for _, r in ch.iterrows():   # the scripted firm's actual quote series in the paired cheater game (same seed, so same defect round)
            run = json.loads(open(RUNS / r.source_root / "trials" / r.arm / r.played_trial_id / "run.jsonl", encoding="utf8").readline())
            chq[(r.wording, r.seed)] = {rd["round"]: [a["displayed"] for a in rd["agents"] if a["id"] == "cheater"][0] for rd in run["rounds"]}
        for _, r in grp.iterrows():
            run = json.loads(open(RUNS / r.source_root / "trials" / r.arm / r.played_trial_id / "run.jsonl", encoding="utf8").readline())
            series = chq.get((r.wording, r.seed), {})
            mk = [min(min(a["displayed"] for a in rd["agents"]), series.get(rd["round"], 1.88)) for rd in run["rounds"]]
            capped.append(np.mean([min(1, max(0, (x - 1) / 2)) for x in mk]))
        cap = pd.Series(capped, index=pd.MultiIndex.from_frame(grp[["wording", "seed"]]))
        chi = ch.set_index(["wording", "seed"]).price_index; idx = chi.index.intersection(cap.index)
        dd = (chi.loc[idx] - cap.loc[idx]).values; mu, lo, hi, n = boot(dd)
        rows.append(dict(model=m, mode=md, check="n3-cheater minus capped n3-group (behavioural residual beyond the mechanical cap), price index, paired", n=n,
                         value=mu, lo=lo, hi=hi, p=signflip(dd)))
        dd = (cap.loc[idx] - grp.set_index(["wording", "seed"]).price_index.loc[idx]).values; mu, lo, hi, n = boot(dd)
        rows.append(dict(model=m, mode=md, check="capped n3-group minus n3-group as played (mechanical part), price index, paired", n=n, value=mu, lo=lo, hi=hi))
        rows.append(dict(model=m, mode=md, check="n3-group games with the paired cheater's scripted quotes added (1.88, and 1.00 in its defect round): price index (pure mechanical effect)", n=len(grp), value=np.mean(capped)))
        rows.append(dict(model=m, mode=md, check="n3-group: price index as played", n=len(grp), value=grp.price_index.mean()))
        rows.append(dict(model=m, mode=md, check="n3-cheater: price index as played", n=len(ch), value=ch.price_index.mean()))
        rows.append(dict(model=m, mode=md, check="n3-cheater: share of LLM firm-rounds (rounds 2+) at or below the cheater's 1.88", n=len(ch), value=ch.llm_at_or_below_cheater_share.mean()))
        rows.append(dict(model=m, mode=md, check="n3-cheater: mean LLM quote", n=len(ch), value=ch.llm_quote.mean()))
        rows.append(dict(model=m, mode=md, check="n3-group: mean LLM quote", n=len(grp), value=grp.llm_quote.mean()))
    # (3) explicit flag vs profit gain index, two-firm p3 chat games
    for (m, md), gm in g.groupby(["model", "mode"]):
        x = gm[gm.arm.isin(["headline-chat", "m-asym", "m-inc-joint", "m-inc-target", "m-comp"])].dropna(subset=["explicit_agreement_flag", "pgi_llm"])
        if x.explicit_agreement_flag.nunique() < 2:
            continue
        a, b = x.explicit_agreement_flag.to_numpy(float), x.pgi_llm.to_numpy(float)
        for name, f in [("Spearman", lambda u, v: pd.Series(u).rank().corr(pd.Series(v).rank())), ("Pearson", lambda u, v: np.corrcoef(u, v)[0, 1])]:
            obs = f(a, b); perm = np.array([f(a, rng.permutation(b)) for _ in range(5000)])
            rows.append(dict(model=m, mode=md, check="explicit-agreement flag vs profit gain index, two-firm p3 chat games: %s (permutation p, 5,000 shuffles)" % name,
                             n=len(x), value=obs, p=float((np.abs(perm) >= abs(obs) - 1e-12).mean())))
    r = pd.DataFrame(rows)
    r.to_csv(out / "extras.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
