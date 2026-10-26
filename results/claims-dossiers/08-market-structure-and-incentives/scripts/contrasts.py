"""Dossier 08, step 2: paired contrasts on (wording, seed) from games_rederived.csv.
Per contrast and metric: n pairs, arm and control means, mean difference, 95% percentile bootstrap CI (10,000 resamples over
pairs, seed 8), exact two-sided sign-flip permutation p (all 2^n sign patterns, n <= 20), SE = sd/sqrt(n), MDE = 2.8 x SE,
and Holm within the family (model x mode x metric) over the dossier's 8 price-and-profit contrasts.
Usage: python contrasts.py <games_csv> <out_csv>"""
import sys
import numpy as np, pandas as pd
try:
    import psutil; psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass

CONTRASTS = [("n3-ethics", "headline-chat"), ("n3-ethics", "n3-group"), ("n3-cheater", "headline-chat"), ("n3-cheater", "n3-group"),
             ("m-inc-joint", "headline-chat"), ("n3-group", "headline-chat"), ("m-inc-target", "headline-chat"), ("m-asym", "headline-chat"),
             ("m-comp", "headline-chat")]
FAMILY = CONTRASTS[:8]   # m-comp exists on Qwen only; it is reported for Q13-channel-off outside the Holm family
METRICS = ["spread", "price_index", "pgi_llm", "comp_llm", "match_llm", "comp_all", "match_all", "pgi_all", "llm_quote",
           "explicit_agreement_flag", "conversation_detector_flag_any"]
rng = np.random.default_rng(8)


_SIGNS = {}


def signflip_p(d):
    """Exact two-sided sign-flip p over all 2^n sign patterns (cached sign matrix per n)."""
    n = len(d)
    if n not in _SIGNS:
        _SIGNS[n] = (((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1).astype(np.float32)
    stats = np.abs(_SIGNS[n] @ d.astype(np.float32)) / n
    return float((stats >= abs(d.mean()) - 1e-6).mean())


def holm(ps):
    ps = np.asarray(ps, float); m = len(ps); o = np.argsort(ps); adj = np.empty(m); run = 0
    for k, i in enumerate(o):
        run = max(run, (m - k) * ps[i]); adj[i] = min(1, run)
    return adj


def main(gcsv, out):
    g = pd.read_csv(gcsv)
    g["mode"] = np.where(g.model == "gpt-oss-20b", "medium", np.where(g.thinking == "on", "t1", "t0"))
    rows = []
    for (model, mode), gm in g.groupby(["model", "mode"]):
        for arm, ctl in CONTRASTS:
            a = gm[gm.arm == arm].set_index(["wording", "seed"]); c = gm[gm.arm == ctl].set_index(["wording", "seed"])
            if a.empty or c.empty:
                continue
            idx = a.index.intersection(c.index)
            for met in METRICS:
                x, y = a.loc[idx, met].astype(float), c.loc[idx, met].astype(float)
                ok = x.notna() & y.notna()
                d = (x[ok] - y[ok]).to_numpy()
                if len(d) == 0:
                    continue
                bs = rng.integers(0, len(d), size=(10000, len(d)))
                bm = d[bs].mean(axis=1)
                se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else np.nan
                rows.append(dict(model=model, mode=mode, contrast="%s - %s" % (arm, ctl), arm=arm, control=ctl, metric=met,
                                 n_pairs=len(d), mean_arm=x[ok].mean(), mean_control=y[ok].mean(), diff=d.mean(),
                                 lo=np.percentile(bm, 2.5), hi=np.percentile(bm, 97.5), p_signflip=signflip_p(d), se=se, mde=2.8 * se,
                                 in_family=(arm, ctl) in FAMILY))
    r = pd.DataFrame(rows)
    r["p_holm"] = np.nan
    for key, gi in r[r.in_family].groupby(["model", "mode", "metric"]):
        r.loc[gi.index, "p_holm"] = holm(gi.p_signflip.values)
    r["family_size"] = r[r.in_family].groupby(["model", "mode", "metric"]).contrast.transform("count")
    r.to_csv(out, index=False, float_format="%.4f")
    show = r[r.metric.isin(["spread", "price_index", "pgi_llm", "comp_llm", "match_llm", "comp_all", "match_all", "pgi_all", "explicit_agreement_flag"])]
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 1000)
    print(show[["model", "mode", "contrast", "metric", "n_pairs", "mean_arm", "mean_control", "diff", "lo", "hi", "p_signflip", "p_holm", "mde"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
