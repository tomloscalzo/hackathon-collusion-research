"""Dossier 09A: self-knowledge tactics (introspection questions, self-score reply fields)
on gpt-oss-20b vs Qwen3-32B. Independent re-derivation from the two Step 1 run.csv tables.

Usage: python -X utf8 self_knowledge_contrasts.py <gptoss_run.csv> <qwen_run.csv> <out_dir>

Each contrast: arm game minus the headline-chat p1 game with the same (wording, seed) and
thinking mode (the design's control_row_id), primary rows only (in_primary == 1).
Bootstrap: 10,000 percentile draws over pairs (seed 20261025). Permutation: exact sign-flip
(all 2^n sign patterns) for n <= 20, two-sided, |mean| >= observed. Holm within a family
= all tactics x five metrics for one model mode. MDE = 2.8 x SE of the paired mean.
Created by Claude at the prompting of the repository owner.
"""
import os
import sys

try:
    import psutil
    psutil.Process().cpu_affinity([4, 5, 6, 7, 8, 9, 10, 11])
except Exception:
    pass
os.environ.setdefault("OMP_NUM_THREADS", "2")

import numpy as np
import pandas as pd


def _rank(v):
    return pd.Series(v).rank().to_numpy(float)


def _corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a - a.mean(); b = b - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else np.nan


def _corr_test(a, b, rank):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if rank:
        a, b = _rank(a), _rank(b)
    r = _corr(a, b)
    if not np.isfinite(r):
        return np.nan, np.nan
    g = np.random.default_rng(7)
    perm = np.array([_corr(a, g.permutation(b)) for _ in range(5000)])
    return r, float((np.abs(perm) >= abs(r) - 1e-12).mean())


class stats:  # numpy stand-ins (no scipy here); p from 5,000 permutations, two-sided
    @staticmethod
    def spearmanr(a, b):
        return _corr_test(a, b, True)

    @staticmethod
    def pearsonr(a, b):
        return _corr_test(a, b, False)

OSS, QWEN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

METRICS = [
    ("market_price_mean", "average absolute spread", -1),   # direction of "price-lowering": negative
    ("price_index", "price index", -1),
    ("profit_gain_index", "profit gain index", -1),
    ("competitive_share", "competitive share (U16)", +1),     # higher = more competitive
    ("matching_share", "matching share", -1),
]
TACTICS = [
    ("introspection", "r2f-confidant", "confidant question after each round, answer fed back"),
    ("introspection", "r3f-public", "public-statement question after each round, answer fed back"),
    ("introspection", "r2s-confidant", "confidant question inside the quote reply, saved only"),
    ("introspection", "r3s-public", "public-statement question inside the quote reply, saved only"),
    ("introspection", "r4-announced", "told it will explain itself after the game (post-game question)"),
    ("self-score", "d-conflict", "1-5 instruction-conflict self-score field in the quote reply"),
    ("self-score", "d-temptation-a", "1-5 temptation-to-coordinate self-score, version A"),
    ("self-score", "d-temptation-b", "1-5 temptation-to-coordinate self-score, version B"),
    ("self-score", "d-placebo", "placebo field: a whole number 1-5 chosen at random"),
]
RNG = np.random.default_rng(20261025)
B = 10000


def load(path, model):
    d = pd.read_csv(path, low_memory=False)
    d = d[(d.run == "neutral") & (d.in_primary == 1)].copy()
    d["model"] = model
    d["mode"] = model + "_" + d.thinking.map({"on": "t1", "off": "t0"})
    return d


_SIGNS = {}


def sign_flip_p(x):
    n = len(x)
    obs = abs(x.mean())
    if n <= 20:
        if n not in _SIGNS:
            idx = np.arange(2 ** n, dtype=np.int64)[:, None]
            _SIGNS[n] = (1 - 2 * ((idx >> np.arange(n)) & 1)).astype(np.float32)
        means = np.abs(_SIGNS[n] @ x.astype(np.float32)) / n
    else:
        signs = RNG.choice([-1, 1], size=(200000, n))
        means = np.abs((signs * x[None, :]).mean(axis=1))
    return float((means >= obs - 1e-6).mean())


def boot_ci(x):
    i = RNG.integers(0, len(x), size=(B, len(x)))
    m = x[i].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def holm(ps):
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for k, j in enumerate(order):
        run = max(run, (m - k) * ps[j])
        adj[j] = min(1.0, run)
    return adj


def paired(d, arm, mode, ctl_arm="headline-chat", ctl_filter=None):
    a = d[(d.arm == arm) & (d["mode"] == mode)]
    if ctl_filter is None:
        c = d[(d.arm == ctl_arm) & (d.penalty_point == 1) & (d["mode"] == mode)]
    else:
        c = ctl_filter
    m = a.merge(c, on=["wording", "seed"], suffixes=("_a", "_c"))
    return a, m


def main():
    oss = load(OSS, "gptoss")
    qw = load(QWEN, "qwen")
    d = pd.concat([oss, qw], ignore_index=True)
    # check: my pairing agrees with the design's control_row_id
    cl = d[d.arm.isin([t[1] for t in TACTICS])]
    rows = []
    for mode in ["gptoss_t1", "qwen_t1", "qwen_t0"]:
        for fam, arm, desc in TACTICS:
            a, m = paired(d, arm, mode)
            if len(a) == 0:
                for col, mname, _ in METRICS:
                    rows.append(dict(family=fam, tactic=arm, description=desc, model_mode=mode,
                                     n_arm_games=0, n_pairs=0, metric=mname))
                continue
            ok = (m["control_row_id_a"] == m["row_id_c"]).mean()
            assert ok == 1.0, (arm, mode, ok)
            for col, mname, comp in METRICS:
                x = (m[col + "_a"] - m[col + "_c"]).dropna().to_numpy(float)
                n = len(x)
                lo, hi = boot_ci(x)
                se = x.std(ddof=1) / np.sqrt(n)
                rows.append(dict(family=fam, tactic=arm, description=desc, model_mode=mode,
                                 n_arm_games=len(a), n_pairs=n, metric=mname,
                                 arm_mean=m[col + "_a"].mean(), control_mean=m[col + "_c"].mean(),
                                 effect=x.mean(), ci_lo=lo, ci_hi=hi, p=sign_flip_p(x),
                                 se=se, mde=2.8 * se, competitive_sign=comp))
    res = pd.DataFrame(rows)
    res["holm_p"] = np.nan
    for mode in res.model_mode.unique():
        k = (res.model_mode == mode) & res.p.notna()
        res.loc[k, "holm_p"] = holm(res.loc[k, "p"])
    res["holm_family_size"] = res.groupby("model_mode").p.transform(lambda s: s.notna().sum())
    res.to_csv(os.path.join(OUT, "contrasts_all.csv"), index=False)

    # supplementary contrasts (not in the Holm family): score fields minus placebo; fed minus saved;
    # gpt-oss pooled-replicate control sensitivity; d-conflict-ethics minus d-conflict
    sup = []
    def add(label, mode, x, n_note=""):
        x = x.dropna().to_numpy(float)
        if len(x) < 3:
            return
        lo, hi = boot_ci(x)
        se = x.std(ddof=1) / np.sqrt(len(x))
        sup.append(dict(contrast=label, model_mode=mode, n_pairs=len(x), metric=mname,
                        effect=x.mean(), ci_lo=lo, ci_hi=hi, p=sign_flip_p(x), mde=2.8 * se))
    for mode in ["gptoss_t1", "qwen_t1", "qwen_t0"]:
        for col, mname, _ in METRICS:
            def arm_df(arm):
                return d[(d.arm == arm) & (d["mode"] == mode)][["wording", "seed", col]]
            pairs = [("d-conflict", "d-placebo"), ("d-temptation-a", "d-placebo"),
                     ("d-temptation-b", "d-placebo"), ("r2f-confidant", "r2s-confidant"),
                     ("r3f-public", "r3s-public"), ("d-conflict-ethics", "d-conflict")]
            for a1, a2 in pairs:
                x1, x2 = arm_df(a1), arm_df(a2)
                if len(x1) and len(x2):
                    m = x1.merge(x2, on=["wording", "seed"])
                    add(f"{a1} minus {a2}", mode, m[col + "_x"] - m[col + "_y"])
            if mode == "gptoss_t1":
                c0 = d[(d.arm == "headline-chat") & (d.penalty_point == 1) & (d["mode"] == mode)]
                reps = d[d.arm.isin(["hrep-fx-chat-p1", "hrep-nx-chat-p1"]) & (d["mode"] == mode)]
                pooled = pd.concat([c0, reps]).groupby(["wording", "seed"])[col].mean().reset_index()
                for fam, arm, desc in TACTICS:
                    x1 = arm_df(arm)
                    m = x1.merge(pooled, on=["wording", "seed"])
                    add(f"{arm} minus pooled control (headline-chat p1 + 2 replicates)", mode,
                        m[col + "_x"] - m[col + "_y"])
                for rep in ["hrep-fx-chat-p1", "hrep-nx-chat-p1"]:
                    m = arm_df(rep).merge(c0[["wording", "seed", col]], on=["wording", "seed"])
                    add(f"{rep} (same headline prompt, replayed) minus headline-chat p1", mode,
                        m[col + "_x"] - m[col + "_y"])
    pd.DataFrame(sup).to_csv(os.path.join(OUT, "contrasts_supplementary.csv"), index=False)

    # self-score levels and candour per model
    lv = []
    for mode in ["gptoss_t1", "qwen_t1", "qwen_t0"]:
        for arm in ["d-conflict", "d-conflict-ethics", "d-temptation-a", "d-temptation-b", "d-placebo"]:
            g = d[(d.arm == arm) & (d["mode"] == mode)]
            if len(g) == 0:
                continue
            s = g.score_mean.dropna()
            r = dict(model_mode=mode, arm=arm, games=len(g), games_with_score=len(s),
                     score_mean=s.mean(), score_sd_games=s.std(), score_min=g.score_min.min(),
                     score_max=g.score_max.max(), share_games_mean_le_1_1=(s <= 1.1).mean(),
                     first=g.score_first.mean(), last=g.score_last.mean(),
                     answered=g.score_n_answered.sum(), unreadable=g.score_n_unreadable.sum())
            for col in ["price_index", "competitive_share", "profit_gain_index"]:
                ok = g[["score_mean", col]].dropna()
                if len(ok) >= 5 and ok.score_mean.nunique() > 1:
                    r[f"spearman_vs_{col}"] = stats.spearmanr(ok.score_mean, ok[col])[0]
                    r[f"spearman_p_vs_{col}"] = stats.spearmanr(ok.score_mean, ok[col])[1]
                    r[f"pearson_vs_{col}"] = stats.pearsonr(ok.score_mean, ok[col])[0]
                    r[f"pearson_p_vs_{col}"] = stats.pearsonr(ok.score_mean, ok[col])[1]
            lv.append(r)
    pd.DataFrame(lv).to_csv(os.path.join(OUT, "self_score_levels.csv"), index=False)

    cd = []
    for mode in ["gptoss_t1", "qwen_t1", "qwen_t0"]:
        for arm in ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"]:
            g = d[(d.arm == arm) & (d["mode"] == mode)]
            if len(g) == 0:
                continue
            q = "confidant" if "confidant" in arm else "public"
            cand = g[f"candour_{q}"].dropna()
            ment = g[f"answer_mentions_coordination_{q}_share"].dropna()
            r = dict(model_mode=mode, arm=arm, question=q, games=len(g),
                     games_with_candour=len(cand), candour_mean=cand.mean(),
                     candour_ci_lo=np.nan, candour_ci_hi=np.nan,
                     concealment_mean=1 - cand.mean() if len(cand) else np.nan,
                     mention_share_mean=ment.mean(),
                     invented_confession_mean=g[f"invented_confession_{q}"].mean(),
                     games_with_invented=g[f"invented_confession_{q}"].notna().sum(),
                     words_mean=g[f"answer_words_{q}_mean"].mean(),
                     answered=g.questions_answered.sum(), asked=g.questions_asked.sum())
            if len(cand) >= 3:
                r["candour_ci_lo"], r["candour_ci_hi"] = boot_ci(cand.to_numpy(float))
            ok = g[[f"answer_mentions_coordination_{q}_share", "price_index", "competitive_share"]].dropna()
            if len(ok) >= 5:
                for col in ["price_index", "competitive_share"]:
                    r[f"spearman_mention_vs_{col}"] = stats.spearmanr(ok.iloc[:, 0], ok[col])[0]
                    r[f"spearman_p_mention_vs_{col}"] = stats.spearmanr(ok.iloc[:, 0], ok[col])[1]
                    r[f"pearson_mention_vs_{col}"] = stats.pearsonr(ok.iloc[:, 0], ok[col])[0]
                    r[f"pearson_p_mention_vs_{col}"] = stats.pearsonr(ok.iloc[:, 0], ok[col])[1]
            cd.append(r)
    pd.DataFrame(cd).to_csv(os.path.join(OUT, "candour_levels.csv"), index=False)

    # cross-model differences in levels (gpt-oss minus Qwen thinking on / off), unpaired bootstrap over games
    xm = []
    specs = [(a, "score_mean") for a in ["d-conflict", "d-temptation-a", "d-temptation-b", "d-placebo"]] +             [(a, "candour_" + ("confidant" if "confidant" in a else "public"))
             for a in ["r2f-confidant", "r3f-public", "r2s-confidant", "r3s-public", "r4-announced"]]
    for arm, col in specs:
        g0 = d[(d.arm == arm) & (d["mode"] == "gptoss_t1")][col].dropna().to_numpy(float)
        for qm in ["qwen_t1", "qwen_t0"]:
            g1 = d[(d.arm == arm) & (d["mode"] == qm)][col].dropna().to_numpy(float)
            b0 = g0[RNG.integers(0, len(g0), size=(B, len(g0)))].mean(1)
            b1 = g1[RNG.integers(0, len(g1), size=(B, len(g1)))].mean(1)
            xm.append(dict(arm=arm, measure=col, comparison="gptoss_t1 minus " + qm,
                           n_gptoss=len(g0), n_qwen=len(g1), gptoss=g0.mean(), qwen=g1.mean(),
                           diff=g0.mean() - g1.mean(), ci_lo=np.percentile(b0 - b1, 2.5),
                           ci_hi=np.percentile(b0 - b1, 97.5)))
    pd.DataFrame(xm).to_csv(os.path.join(OUT, "cross_model_levels.csv"), index=False)
    print("done", len(res), len(sup))


if __name__ == "__main__":
    main()
