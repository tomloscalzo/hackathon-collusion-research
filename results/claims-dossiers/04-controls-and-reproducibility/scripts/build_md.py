import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../tools/analysis_style')))
import arm_labels as AL

C = pd.read_csv(OUT + '/g_ctl_contrasts.csv'); LV = pd.read_csv(OUT + '/g_ctl_levels.csv'); RR = pd.read_csv(OUT + '/g_repro_replicate_vs_headline.csv')
GAP = pd.read_csv(OUT + '/g_repro_gap_summary.csv'); COR = pd.read_csv(OUT + '/g_repro_correlations.csv'); LEV = pd.read_csv(OUT + '/g_repro_lever_effects.csv')
PL = pd.read_csv(OUT + '/g_repro_placebo_diagnostic.csv'); RV = pd.read_csv(OUT + '/g_repro_rep_vs_rep.csv'); W = pd.read_csv(OUT + '/q14_wording_effect.csv')
PW = pd.read_csv(OUT + '/q14_wording_power.csv'); CB = pd.read_csv(OUT + '/copybot_rederived_contrasts.csv'); FXJ = pd.read_csv(OUT + '/g_ctl_fx_joint.csv')


def f(r, k=3):
    return f"{r['diff']:+.{k}f} [{r['ci_lo']:+.{k}f}, {r['ci_hi']:+.{k}f}]"


def pf(p):
    return '<0.0001' if p < 1e-4 else f'{p:.4f}' if p < 0.001 else f'{p:.3f}'


MN = [MNAME[m] for m in MCOLS]
GO, Q1, Q0 = 'gpt-oss-20b (reasoning medium)', 'Qwen3-32B thinking on', 'Qwen3-32B thinking off'


def ctl_table(model):
    rows = ['| Contrast | ' + ' | '.join(MN) + ' |', '|---|' + '---|' * 5]
    for c in ['compete - chat', 'joint - chat', 'joint - compete']:
        cells = []
        for mn in MN:
            r = C[(C.model == model) & (C.contrast == c) & (C.metric == mn)].iloc[0]
            cells.append(f"{f(r, 2)}; p {pf(r.p_signflip)}, Holm {pf(r.p_holm)}")
        rows.append(f'| {c} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


lev = LV.set_index(['model', 'arm'])


def levrow(model):
    rows = ['| Arm (n = 20 games) | ' + ' | '.join(MN) + ' |', '|---|' + '---|' * 5]
    for a in ['strict-compete control', 'joint-profit control', 'headline-chat p3']:
        r = lev.loc[(model, a)]
        rows.append(f'| {a} | ' + ' | '.join(f"{r[mn]:.3f}" for mn in MN) + ' |')
    return '\n'.join(rows)


def rr_rows():
    rows = ['| Replicate arm minus its headline cell | n pairs | ' + ' | '.join(MN) + ' |', '|---|---|' + '---|' * 5]
    names = {'hrep-fx-chat-p1': 'hrep-fx-chat-p1 minus headline-chat p1', 'hrep-nx-chat-p1': 'hrep-nx-chat-p1 minus headline-chat p1',
             'hrep-fx-tacit-p1': 'hrep-fx-tacit-p1 minus headline-tacit p1', 'hrep-nx-tacit-p1': 'hrep-nx-tacit-p1 minus headline-tacit p1',
             'hrep-fx-chat-p5': 'hrep-fx-chat-p5 minus headline-chat p5', 'pooled': 'all five pooled (copies not independent)',
             'dedup': 'de-duplicated (copies averaged per headline game)'}
    for a, nm in names.items():
        s = RR[RR.arm == a]
        cells = []
        for mn in MN:
            r = s[s.metric == mn].iloc[0]
            h = '' if pd.isna(r.p_holm_arms) else f", Holm {pf(r.p_holm_arms)}"
            cells.append(f"{f(r, 3 if mn != 'Average absolute spread' else 2)}; p {pf(r.p_signflip)}{h}")
        rows.append(f'| {nm} | {int(s.n_pairs.iloc[0])} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def cmp_rows():
    s = LEV[LEV.ci_excludes0 & (LEV.price_diff.abs() <= 0.209)]
    rows = ['| Contrast (arm minus control) | Price index change [95% CI] | Profit gain index change | Holm p (family of 38) | Control from a different run root? | Arm and control in different submission batches? |', '|---|---|---|---|---|---|']
    for _, r in s.sort_values('price_diff', key=abs).iterrows():
        rows.append(f"| {r.contrast} (control {r.control}) | {r.price_diff:+.3f} [{r.price_lo:+.3f}, {r.price_hi:+.3f}] | {r.pgi_diff:+.3f} | {pf(r.p_holm_all)} | {'yes' if not r.same_run_root else 'no'} | {'yes' if not r.same_wave_batch else 'no'} |")
    return '\n'.join(rows)


def w_rows(model):
    rows = ['| Metric | n games | eps-sq (pooled games) | root eps-sq | p (pair permutation) | Holm (5 metrics) | max minus min of wording means | eta-sq (20 pair means, cell-adjusted) | p (pair-mean F permutation) | Holm (5 metrics) |', '|---|---|---|---|---|---|---|---|---|---|']
    for _, r in W[W.model == model].iterrows():
        rows.append(f"| {r.metric} | {int(r.n_games)} | {r.eps2_pooled:.3f} | {r.root_eps2_pooled:.3f} | {pf(r.p_pooled_pairperm)} | {pf(r.p_holm_pooled_5metrics)} | {r.wording_max_minus_min_pooled:.3f} | {r.eta2_pair:.3f} | {pf(r.p_F_pair)} | {pf(r.p_holm_pair_5metrics)} |")
    return '\n'.join(rows)


def cb_rows():
    rows = ['| Copier opens at / thinking | n pairs | ' + ' | '.join(MN) + ' |', '|---|---|' + '---|' * 5]
    for op in ['2.50', '1.50']:
        for th in ['t0', 't1']:
            s = CB[(CB.opening.map(lambda x: f'{float(x):.2f}') == op) & (CB.thinking == th)]
            cells = []
            for mn in MN:
                r = s[s.metric == mn].iloc[0]
                cells.append(f"{r.mean_a:.2f} vs {r.mean_b:.2f}; {f(r, 2)}; Holm {pf(r.p_holm_4cells)}")
            rows.append(f"| {op} / {'off' if th == 't0' else 'on'} | 20 | " + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


p = RR[RR.arm == 'pooled'].set_index('metric'); d = RR[RR.arm == 'dedup'].set_index('metric')
corr = COR.set_index('metric')
cor_rows = '\n'.join(f"| {mn} | {corr.loc[mn].pearson:.2f} | {corr.loc[mn].spearman:.2f} | {corr.loc[mn].pearson_cell_centred:.2f} | {corr.loc[mn].spearman_cell_centred:.2f} |" for mn in MN)
gap_rows = '\n'.join(f"| {r.metric} | {r.drift:+.3f} | {r.sd_gap:.3f} | {r.mean_abs_gap:.3f} | {r.drift / r.sd_gap:+.2f} |" for _, r in GAP.iterrows())
pl = PL.set_index(['contrast', 'metric'])


def two(df, c):
    a = df.loc[(c, 'Price index')]; b = df.loc[(c, 'Profit gain index')]
    return f"| {c} | {a['diff']:+.3f} [{a.ci_lo:+.3f}, {a.ci_hi:+.3f}] | {b['diff']:+.3f} [{b.ci_lo:+.3f}, {b.ci_hi:+.3f}] |"


pl_rows = '\n'.join(two(pl, c) for c in ['moral-placebo - headline-chat p1', 'd-placebo - headline-chat p1'])
rv = RV.set_index(['contrast', 'metric'])
rv_rows = '\n'.join(two(rv, c) for c in sorted(set(RV.contrast)))
fxj = FXJ.set_index('metric')
R1 = RR[RR.metric.str.startswith('Round-1')]
r1p = R1[R1.arm == 'pooled'].iloc[0]; r1d = R1[R1.arm == 'dedup'].iloc[0]
cj = lambda m, c, mn: C[(C.model == m) & (C.contrast == c) & (C.metric == mn)].iloc[0]
slugs = sorted(set(LEV.arm.tolist()) - {'headline-chat p1', 'headline-chat p5', 'headline-chat p3'}) + ['headline-chat', 'headline-tacit']
slugs = [x for x in slugs if x in AL.glossary()]
vals = dict(FIG1_LEGEND='**Legend: arms shown in Figure 1 (rows, y-axis; the x-axis is the price-index change, defined in the Terms table above; colour = direction, red more collusive, green more competitive)**' + chr(10) + chr(10) + AL.legend_table(slugs, long=True), CTL_GO=ctl_table(GO), CTL_Q1=ctl_table(Q1), CTL_Q0=ctl_table(Q0), LEV_GO=levrow(GO), LEV_Q1=levrow(Q1), LEV_Q0=levrow(Q0),
            RR_ROWS=rr_rows(), CMP_ROWS=cmp_rows(), W_GO=w_rows(GO), W_Q0=w_rows(Q0), W_Q1=w_rows(Q1), CB_ROWS=cb_rows(),
            COR_ROWS=cor_rows, GAP_ROWS=gap_rows, PL_ROWS=pl_rows, RV_ROWS=rv_rows,
            NSIG=str(int(LEV.ci_excludes0.sum())), NCOMP=str(int((LEV.ci_excludes0 & (LEV.price_diff.abs() <= 0.209)).sum())),
            NLE=str(int((LEV.price_diff.abs() <= 0.1044).sum())), NROB=str(int(LEV.still_excludes0_after_drift.sum())),
            NHOLM=str(int((LEV.p_holm_all < 0.05).sum())), NTOT=str(len(LEV)),
            PRICE_POOL=f(p.loc['Price index']), PGI_POOL=f(p.loc['Profit gain index']), SPREAD_POOL=f(p.loc['Average absolute spread'], 2),
            COMP_POOL=f(p.loc['Competitive share (U16)']), MATCH_POOL=f(p.loc['Matching share']),
            PRICE_DD=f(d.loc['Price index']), PGI_DD=f(d.loc['Profit gain index']), SPREAD_DD=f(d.loc['Average absolute spread'], 2),
            COMP_DD=f(d.loc['Competitive share (U16)']), MATCH_DD=f(d.loc['Matching share']),
            P_PRICE_POOL=pf(p.loc['Price index'].p_signflip), P_PRICE_DD=pf(d.loc['Price index'].p_signflip), P_PGI_DD=pf(d.loc['Profit gain index'].p_signflip),
            P_SPREAD_DD=pf(d.loc['Average absolute spread'].p_signflip), MDE_PRICE_POOL=f"{p.loc['Price index'].mde:.3f}", MDE_PRICE_DD=f"{d.loc['Price index'].mde:.3f}",
            R1_POOL=f(r1p, 2), R1_DD=f(r1d, 2), FXJ_PRICE=f(fxj.loc['Price index']), FXJ_PGI=f(fxj.loc['Profit gain index']),
            CTL_JC_P=f(cj(GO, 'joint - chat', 'Price index')), CTL_JC_Q1=f(cj(Q1, 'joint - chat', 'Price index')), CTL_JC_Q0=f(cj(Q0, 'joint - chat', 'Price index')),
            CTL_JC_Q0P=pf(cj(Q0, 'joint - chat', 'Price index').p_holm), CTL_JC_PH=pf(cj(GO, 'joint - chat', 'Price index').p_holm),
            CTL_JC_PGI=f(cj(GO, 'joint - chat', 'Profit gain index')), CTL_CC_PGI=f(cj(GO, 'compete - chat', 'Profit gain index')),
            PW_PGI=f"{PW.set_index('metric').loc['Profit gain index'].detectable_range_max_minus_min_approx:.2f}",
            PW_PRICE=f"{PW.set_index('metric').loc['Price index'].detectable_range_max_minus_min_approx:.2f}")
md = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.md'), encoding='utf-8').read()
for k, v in vals.items():
    md = md.replace('{{' + k + '}}', v)
open(OUT + '/ANALYSIS.md', 'w', encoding='utf-8').write(md)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(OUT + '/ANALYSIS.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print('unfilled:', re.findall(r'\{\{[A-Z0-9_]+\}\}', md))
