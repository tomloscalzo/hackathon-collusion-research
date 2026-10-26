"""Wording x seed robustness of the Track M headline results (neutral and anchored runs).

Usage: python -X utf8 wording_seed.py --neutral RUN_CSV --anchored RUN_CSV [--out DIR]
RUN_CSV = the Step 1 run.csv of each run. Only DONE games of the three headline arms (tacit, chat, monitored) at penalty
points 1, 3, 4, 5 in both thinking modes (24 cells x 20 pairs per run) are used. A "pair" is one (wording, seed)
combination; every seed is used with exactly ONE wording (design), so wording and seed cannot be separated, only nested.
Outputs (CSV): variance_by_pair.csv, wording_x_thinking.csv, wording_x_thinking_cells.csv, leave_one_wording_out.csv,
leave_one_wording_out_summary.csv, fig_variance.png.
"""
import argparse, os, sys, itertools, numpy as np, pandas as pd
if os.name == 'nt':   # BelowNormal priority; affinity is set by the caller (0xFF0)
    try:
        import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception: pass

ap = argparse.ArgumentParser(); ap.add_argument('--neutral', required=True); ap.add_argument('--anchored', required=True)
ap.add_argument('--out', default='.'); a = ap.parse_args()
rng = np.random.default_rng(5); B = 10000
HEAD = ['headline-tacit', 'headline-chat', 'headline-monitored']; PTS = [1, 3, 4, 5]
METRICS = {'mean_quote': 'market_price_mean', 'price_index': 'price_index', 'gain': 'profit_gain_index',
           'comp_share': 'competitive_share', 'match_share': 'matching_share'}

def load(path):
    d = pd.read_csv(path, usecols=['arm', 'penalty_point', 'thinking', 'wording', 'seed', 'status', 'profit_gain_index', 'price_index', 'competitive_share', 'matching_share', 'market_price_mean'])
    d = d[(d.status == 'done') & d.arm.isin(HEAD) & d.penalty_point.isin(PTS)].copy()
    d['mode'] = d.thinking.map({'off': 't0', 'on': 't1'}); d['pair'] = d.wording.astype(str) + '_' + d.seed.astype(str)
    return d
RUNS = {'neutral': load(a.neutral), 'anchored': load(a.anchored)}
for r, d in RUNS.items():
    assert d.groupby('seed').wording.nunique().max() == 1, 'seed used with more than one wording'

# ------------------------------------------------------------------ 1. variance explained by the (wording, seed) pair
def components(Y, wording):
    """Y: array pairs x cells (balanced, crossed, one game per pair x cell); wording: int array by pair (equal seeds per wording)."""
    Y = np.asarray(Y, float); wording = np.asarray(wording)
    n, k = Y.shape; R = Y - Y.mean(axis=0)                                        # remove cell means
    pm = R.mean(axis=1); ss_pair = k * (pm ** 2).sum(); ss_tot = (R ** 2).sum()
    ws = np.unique(wording); m = n / len(ws)
    wm = np.array([pm[wording == w].mean() for w in ws])
    ss_w = k * m * (wm ** 2).sum(); ss_s = ss_pair - ss_w
    ss_e = ss_tot - ss_pair; df_w = len(ws) - 1; df_s = n - len(ws); df_e = (k - 1) * (n - 1)
    ms_w, ms_s, ms_e, ms_p = ss_w / df_w, ss_s / df_s, ss_e / df_e, ss_pair / (n - 1)
    v_e = ms_e; v_s = max((ms_s - ms_e) / k, 0); v_w = max((ms_w - ms_s) / (k * m), 0)
    v_p = v_w + v_s; tot = v_p + v_e                                               # pair = wording + seed within wording
    return dict(eta2_pair=ss_pair / ss_tot, eta2_wording=ss_w / ss_tot, eta2_seed_in_wording=ss_s / ss_tot,
                share_pair=v_p / tot if tot > 0 else np.nan, share_wording=v_w / tot if tot > 0 else np.nan,
                share_seed_in_wording=v_s / tot if tot > 0 else np.nan,
                F_pair=ms_p / ms_e, F_wording_vs_seed=ms_w / ms_s, F_seed_in_wording=ms_s / ms_e)

def perm_p(Y, wording, nperm=1000):
    """Permutation p-values (no scipy): pair labels shuffled within each cell; wording labels shuffled among pairs (seeds kept whole)."""
    Y = np.asarray(Y, float); wording = np.asarray(wording); c0 = components(Y, wording); h1 = h2 = 1
    for _ in range(nperm):
        Yp = np.take_along_axis(Y, np.argsort(rng.random(Y.shape), axis=0), axis=0)
        h1 += components(Yp, wording)['F_pair'] >= c0['F_pair']
        h2 += components(Y, rng.permutation(wording))['F_wording_vs_seed'] >= c0['F_wording_vs_seed']
    return dict(p_pair=h1 / (nperm + 1), p_wording_vs_seed=h2 / (nperm + 1))

def wide(d, col, modes, arms):
    s = d[d['mode'].isin(modes) & d.arm.isin(arms)]
    return s.pivot_table(index='pair', columns=['arm', 'mode', 'penalty_point'], values=col).dropna()

def boot_components(Y, wording, key='share_pair', B=1000):
    Y = np.asarray(Y, float); wording = np.asarray(wording); out = []
    groups = [np.where(wording == w)[0] for w in np.unique(wording)]
    for _ in range(B):
        idx = np.concatenate([rng.choice(g, len(g)) for g in groups])             # resample seeds within wording
        out.append(components(Y[idx], wording[idx])[key])
    return np.nanpercentile(out, [2.5, 97.5])

rows = []
for run, d in RUNS.items():
    wording = d.drop_duplicates('pair').set_index('pair').wording
    for mname, col in METRICS.items():
        for label, modes, arms in [('both modes', ['t0', 't1'], HEAD), ('thinking off', ['t0'], HEAD), ('thinking on', ['t1'], HEAD)] + \
                                  [('arm: ' + x.replace('headline-', ''), ['t0', 't1'], [x]) for x in HEAD]:
            Y = wide(d, col, modes, arms); w = wording.reindex(Y.index).values
            c = components(Y.values, w); c.update(perm_p(Y.values, w)); lo, hi = boot_components(Y.values, w)
            rows.append(dict(run=run, metric=mname, subset=label, n_pairs=len(Y), n_cells=Y.shape[1], **c, share_pair_lo=lo, share_pair_hi=hi))
V = pd.DataFrame(rows); V.to_csv(os.path.join(a.out, 'variance_by_pair.csv'), index=False, float_format='%.4f')

# ------------------------------------------------------------------ 2. wording x thinking
def pair_vec(d, col, arm, mode, pt=None):
    s = d[(d.arm == arm) & (d['mode'] == mode)]
    s = s if pt is None else s[s.penalty_point == pt]
    return s.groupby('pair')[col].mean()                                             # mean over penalty points when pt is None
def boot_mean(x, B=B):
    x = np.asarray(x, float); b = rng.choice(x, (B, len(x))).mean(axis=1); return np.percentile(b, [2.5, 97.5])
rows, cells = [], []
for run, d in RUNS.items():
    wording = d.drop_duplicates('pair').set_index('pair').wording
    for mname, col in METRICS.items():
        for arm in HEAD + ['ALL headline']:
            arms = HEAD if arm == 'ALL headline' else [arm]
            eff = pd.concat([(pair_vec(d, col, x, 't1') - pair_vec(d, col, x, 't0')) for x in arms], axis=1).mean(axis=1)
            on = pd.concat([pair_vec(d, col, x, 't1') for x in arms], axis=1).mean(axis=1)
            off = pd.concat([pair_vec(d, col, x, 't0') for x in arms], axis=1).mean(axis=1)
            w = wording.reindex(eff.index)
            stat = lambda e, ww: e.groupby(ww.values).mean().var(ddof=1)
            obs = stat(eff, w); perm = [stat(eff, pd.Series(rng.permutation(w.values), index=w.index)) for _ in range(5000)]
            p_int = (np.sum(np.array(perm) >= obs - 1e-12) + 1) / 5001
            lo, hi = boot_mean(eff.values)
            rows.append(dict(run=run, metric=mname, arm=arm, wording='ALL', n_pairs=len(eff), thinking_effect=eff.mean(), lo=lo, hi=hi,
                             var_across_wordings=obs, p_wording_x_thinking_perm=p_int))
            for wd in sorted(w.unique()):
                e = eff[w == wd]; l, h = boot_mean(e.values)
                rows.append(dict(run=run, metric=mname, arm=arm, wording=wd, n_pairs=len(e), thinking_effect=e.mean(), lo=l, hi=h))
                cells.append(dict(run=run, metric=mname, arm=arm, wording=wd, thinking_off=off[w == wd].mean(), thinking_on=on[w == wd].mean()))
pd.DataFrame(rows).to_csv(os.path.join(a.out, 'wording_x_thinking.csv'), index=False, float_format='%.4f')
pd.DataFrame(cells).to_csv(os.path.join(a.out, 'wording_x_thinking_cells.csv'), index=False, float_format='%.4f')

# ------------------------------------------------------------------ 3. leave-one-wording-out headline contrasts
def contrasts(d, col):
    V = lambda arm, m, pt: d[(d.arm == arm) & (d['mode'] == m) & (d.penalty_point == pt)].set_index('pair')[col]
    pooled = lambda fa, fb: pd.concat([fa(p) - fb(p) for p in PTS], axis=1).mean(axis=1)
    C = {}
    for m in ['t0', 't1']:
        C[f'chat - tacit, pooled penalties, {m}'] = pooled(lambda p: V('headline-chat', m, p), lambda p: V('headline-tacit', m, p))
        C[f'monitored - chat, pooled penalties, {m}'] = pooled(lambda p: V('headline-monitored', m, p), lambda p: V('headline-chat', m, p))
        for c in ['chat', 'tacit']:
            C[f'p5 - p1 {c}, {m}'] = V('headline-' + c, m, 5) - V('headline-' + c, m, 1)
    for c in ['tacit', 'chat', 'monitored']:
        C[f'thinking on - off, {c}, pooled penalties'] = pooled(lambda p: V('headline-' + c, 't1', p), lambda p: V('headline-' + c, 't0', p))
        C[f'(p5 - p1) x thinking, {c}'] = (V('headline-' + c, 't1', 5) - V('headline-' + c, 't1', 1)) - (V('headline-' + c, 't0', 5) - V('headline-' + c, 't0', 1))
    return C
rows = []
for run, d in RUNS.items():
    wording = d.drop_duplicates('pair').set_index('pair').wording
    for mname, col in METRICS.items():
        for cname, s in contrasts(d, col).items():
            s = s.dropna(); w = wording.reindex(s.index)
            lo, hi = boot_mean(s.values)
            rows.append(dict(run=run, metric=mname, contrast=cname, dropped_wording='none', n_pairs=len(s), est=s.mean(), lo=lo, hi=hi))
            for wd in sorted(w.unique()):
                k = s[w != wd]; lo, hi = boot_mean(k.values)
                rows.append(dict(run=run, metric=mname, contrast=cname, dropped_wording=wd, n_pairs=len(k), est=k.mean(), lo=lo, hi=hi))
            for wd in sorted(w.unique()):                                                # that wording alone (4 pairs)
                k = s[w == wd]; lo, hi = boot_mean(k.values)
                rows.append(dict(run=run, metric=mname, contrast=cname, dropped_wording=f'only {wd}', n_pairs=len(k), est=k.mean(), lo=lo, hi=hi))
L = pd.DataFrame(rows); L['dropped_wording'] = L.dropped_wording.astype(str); L.to_csv(os.path.join(a.out, 'leave_one_wording_out.csv'), index=False, float_format='%.4f')
sm = []
for (run, met, c), g in L.groupby(['run', 'metric', 'contrast'], sort=False):
    full = g[g.dropped_wording == 'none'].iloc[0]
    lo1 = g[~g.dropped_wording.isin(['none']) & ~g.dropped_wording.str.startswith('only')]
    only = g[g.dropped_wording.str.startswith('only')]
    sgn = np.sign(full.est)
    sig_full = (full.lo > 0) or (full.hi < 0)
    sm.append(dict(run=run, metric=met, contrast=c, est=full.est, lo=full.lo, hi=full.hi, significant_full=sig_full,
                   loo_min=lo1.est.min(), loo_max=lo1.est.max(),
                   loo_same_sign=int((np.sign(lo1.est) == sgn).sum()), loo_ci_excludes_zero_same_sign=int(((lo1.lo > 0) & (sgn > 0) | (lo1.hi < 0) & (sgn < 0)).sum()),
                   single_wording_same_sign=int((np.sign(only.est) == sgn).sum()),
                   holds_in_every_loo=bool(sig_full and (((lo1.lo > 0) & (sgn > 0)) | ((lo1.hi < 0) & (sgn < 0))).all())))
S = pd.DataFrame(sm); S.to_csv(os.path.join(a.out, 'leave_one_wording_out_summary.csv'), index=False, float_format='%.4f')

# ------------------------------------------------------------------ figure: shares of within-cell variance, five metrics
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 5, figsize=(12, 3.4), sharey=True)
TITLES = {'mean_quote': 'mean quote', 'price_index': 'price index', 'gain': 'profit gain index', 'comp_share': 'competitive share', 'match_share': 'matching share'}
for ax, met in zip(axs, METRICS):
    sub = V[(V.metric == met) & V.subset.isin(['thinking off', 'thinking on'])]; labs = []; x = 0
    for run in ['neutral', 'anchored']:
        for s_ in ['thinking off', 'thinking on']:
            r = sub[(sub.run == run) & (sub.subset == s_)].iloc[0]
            ax.bar(x, r.share_wording, color='#1f77b4', label='wording' if (x == 0 and met == 'gain') else None)
            ax.bar(x, r.share_seed_in_wording, bottom=r.share_wording, color='#d95f02', label='seed within wording' if (x == 0 and met == 'gain') else None)
            ax.bar(x, 1 - r.share_pair, bottom=r.share_pair, color='#cccccc', label='game-level noise' if (x == 0 and met == 'gain') else None)
            labs.append(('N' if run == 'neutral' else 'A') + (' off' if s_ == 'thinking off' else ' on')); x += 1
    ax.set_xticks(range(x)); ax.set_xticklabels(labs, fontsize=8); ax.set_title(TITLES[met], fontsize=9); ax.spines[['top', 'right']].set_visible(False)
axs[0].set_ylabel('share of within-cell variance')
fig.legend(frameon=False, fontsize=8, loc='upper center', ncol=3, bbox_to_anchor=(0.5, 1.02))
fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(os.path.join(a.out, 'fig_variance.png'), dpi=140)
