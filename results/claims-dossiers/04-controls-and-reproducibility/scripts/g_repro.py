import sys; sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from common import *
o = load('oss')
HEADMAP = {'hrep-fx-chat-p1': ('headline-chat', 1), 'hrep-nx-chat-p1': ('headline-chat', 1), 'hrep-fx-tacit-p1': ('headline-tacit', 1),
           'hrep-nx-tacit-p1': ('headline-tacit', 1), 'hrep-fx-chat-p5': ('headline-chat', 5)}
rows = []; allpairs = []
for arm, (h, p) in HEADMAP.items():
    a = sel(o, arm); b = sel(o, h, p)
    for m in MCOLS + ['round1_quote_mean']:
        r = contrast(a, b, m); allpairs.append((arm, m, r['d'], pairdiff(a, b, m)[0])); r.pop('d')
        r.update(group=arm + ' - ' + h + f' p{p}', arm=arm, metric=MNAME.get(m, 'Round-1 quote (diagnostic)'), mcol=m); rows.append(r)
# pooled over 5 arms (99 pairs; not independent) and de-duplicated (mean of copies per headline game)
for m in MCOLS + ['round1_quote_mean']:
    d = np.concatenate([x[2] for x in allpairs if x[1] == m])
    lo, hi = boot_ci(d); se = d.std(ddof=1) / np.sqrt(len(d))
    rows.append(dict(group='pooled 5 replicate arms (99 pairs, copies not independent)', arm='pooled', metric=MNAME.get(m, 'Round-1 quote (diagnostic)'), mcol=m,
                     n_pairs=len(d), diff=d.mean(), ci_lo=lo, ci_hi=hi, p_signflip=signflip_p(d), se=se, mde=2.8 * se,
                     mean_a=np.nan, mean_b=np.nan))
    # dedup: average copies per headline game (cell, pair)
    dd = pd.DataFrame([(HEADMAP[x[0]], pr, v) for x in allpairs if x[1] == m for pr, v in zip(x[3], x[2])], columns=['cell', 'pair', 'v'])
    dd = dd.groupby(['cell', 'pair']).v.mean().values
    lo, hi = boot_ci(dd); se = dd.std(ddof=1) / np.sqrt(len(dd))
    rows.append(dict(group='de-duplicated (copies averaged per headline game)', arm='dedup', metric=MNAME.get(m, 'Round-1 quote (diagnostic)'), mcol=m,
                     n_pairs=len(dd), diff=dd.mean(), ci_lo=lo, ci_hi=hi, p_signflip=signflip_p(dd), se=se, mde=2.8 * se, mean_a=np.nan, mean_b=np.nan))
R = pd.DataFrame(rows)
# Holm: family = the five replicate arms, within each metric (size 5)
R['p_holm_arms'] = np.nan
for m in R.mcol.unique():
    k = (R.mcol == m) & R.arm.str.startswith('hrep')
    R.loc[k, 'p_holm_arms'] = holm(R.loc[k, 'p_signflip'].values)
R.to_csv(OUT + '/g_repro_replicate_vs_headline.csv', index=False, float_format='%.5g')
pd.set_option('display.width', 250)
print(R[['group', 'metric', 'n_pairs', 'diff', 'ci_lo', 'ci_hi', 'p_signflip', 'p_holm_arms', 'mde']].to_string())

# ---- replicate vs replicate (fx vs nx copies of the same headline game) and pair-level spread
rr = []
for (x, y) in [('hrep-fx-chat-p1', 'hrep-nx-chat-p1'), ('hrep-fx-tacit-p1', 'hrep-nx-tacit-p1')]:
    for m in MCOLS:
        r = contrast(sel(o, x), sel(o, y), m); r.pop('d'); r.update(contrast=x + ' - ' + y, metric=MNAME[m]); rr.append(r)
pd.DataFrame(rr).to_csv(OUT + '/g_repro_rep_vs_rep.csv', index=False, float_format='%.5g'); print(pd.DataFrame(rr)[['contrast', 'metric', 'diff', 'ci_lo', 'ci_hi', 'p_signflip']])
# mean absolute pair gap (typical size of one game vs its replay), pooled
gap = []
for m in MCOLS:
    d = np.concatenate([x[2] for x in allpairs if x[1] == m]); gap.append(dict(metric=MNAME[m], mean_abs_gap=np.abs(d).mean(), sd_gap=d.std(ddof=1), drift=d.mean(), drift_over_sd=d.mean() / d.std(ddof=1)))
pd.DataFrame(gap).to_csv(OUT + '/g_repro_gap_summary.csv', index=False, float_format='%.4f'); print(pd.DataFrame(gap))

# ---- placebo diagnostic: placebo arms (no substantive instruction) vs headline-chat p1
pl = []
for arm in ['moral-placebo', 'd-placebo', 'r3f-public', 'r2f-confidant']:
    pass
for arm in ['moral-placebo', 'd-placebo']:
    for m in MCOLS:
        r = contrast(sel(o, arm), sel(o, 'headline-chat', 1), m); r.pop('d'); r.update(contrast=arm + ' - headline-chat p1', metric=MNAME[m]); pl.append(r)
pd.DataFrame(pl).to_csv(OUT + '/g_repro_placebo_diagnostic.csv', index=False, float_format='%.5g'); print(pd.DataFrame(pl)[['contrast', 'metric', 'diff', 'ci_lo', 'ci_hi', 'p_signflip']])
print(o[o.arm.isin(['moral-placebo','d-placebo'])].groupby('arm').wave.agg(lambda s: sorted(set(s))))
