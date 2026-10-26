"""Build ANALYSIS.md tables from the CSVs written by wording_seed.py and fill analysis_template.md (python -X utf8 build_md.py)."""
import pandas as pd, numpy as np
V = pd.read_csv('variance_by_pair.csv'); W = pd.read_csv('wording_x_thinking.csv'); S = pd.read_csv('leave_one_wording_out_summary.csv')
MET = ['mean_quote', 'price_index', 'gain', 'comp_share', 'match_share']
NAME = dict(mean_quote='mean quote', price_index='price index', gain='profit gain index', comp_share='competitive share', match_share='matching share')
pc = lambda x: f'{100*x:.0f}%'
def est(r, d=2): return f'{r["est"]:+.{d}f} [{r.lo:+.{d}f}, {r.hi:+.{d}f}]'
def tab(head, rows): return '| ' + ' | '.join(head) + ' |\n|' + '---|' * len(head) + '\n' + '\n'.join('| ' + ' | '.join(map(str, r)) + ' |' for r in rows)

rows = []
for run in ['neutral', 'anchored']:
    for m in MET:
        r = V[(V.run == run) & (V.metric == m) & (V.subset == 'both modes')].iloc[0]
        off = V[(V.run == run) & (V.metric == m) & (V.subset == 'thinking off')].iloc[0]; on = V[(V.run == run) & (V.metric == m) & (V.subset == 'thinking on')].iloc[0]
        rows.append([run, NAME[m], f'{pc(r.share_pair)} [{pc(r.share_pair_lo)}, {pc(r.share_pair_hi)}]', pc(r.share_wording), pc(r.share_seed_in_wording),
                     f'{r.p_pair:.3f}', f'{r.p_wording_vs_seed:.3f}', pc(off.share_pair), pc(on.share_pair)])
T_VAR = tab(['run', 'metric', 'pair share of variance [95% CI]', 'of which wording', 'of which seed within wording', 'p: pair effect', 'p: wording vs seed', 'pair share, thinking off', 'pair share, thinking on'], rows)

out = {}
for run in ['neutral', 'anchored']:
    rows = []
    for wd in ['ALL', '0', '1', '2', '3', '4']:
        r_ = [('all 5 wordings (20 pairs)' if wd == 'ALL' else f'wording {wd} only (4 pairs)')]
        for m in MET:
            x = W[(W.run == run) & (W.metric == m) & (W.arm == 'ALL headline') & (W.wording.astype(str) == wd)].iloc[0]
            r_.append(f'{x.thinking_effect:+.2f} [{x.lo:+.2f}, {x.hi:+.2f}]')
        rows.append(r_)
    pr = ['wording x thinking, permutation p']
    for m in MET:
        x = W[(W.run == run) & (W.metric == m) & (W.arm == 'ALL headline') & (W.wording.astype(str) == 'ALL')].iloc[0]; pr.append(f'{x.p_wording_x_thinking_perm:.3f}')
    rows.append(pr)
    out[run] = tab(['subset'] + [NAME[m] for m in MET], rows)
T_WT_N, T_WT_A = out['neutral'], out['anchored']

CON = ['chat - tacit, pooled penalties, t0', 'chat - tacit, pooled penalties, t1', 'monitored - chat, pooled penalties, t0', 'monitored - chat, pooled penalties, t1',
       'p5 - p1 chat, t0', 'p5 - p1 chat, t1', 'p5 - p1 tacit, t0', 'p5 - p1 tacit, t1',
       'thinking on - off, tacit, pooled penalties', 'thinking on - off, chat, pooled penalties', 'thinking on - off, monitored, pooled penalties']
for run in ['neutral', 'anchored']:
    rows = []
    for c in CON:
        r_ = [c]
        for m in MET:
            x = S[(S.run == run) & (S.metric == m) & (S.contrast == c)].iloc[0]
            r_.append(f'{est(x)}; leave-one-out {x.loo_ci_excludes_zero_same_sign}/5 clear, single wording same sign {x.single_wording_same_sign}/5')
        rows.append(r_)
    out[run + '_c'] = tab(['contrast (paired on pair)'] + [NAME[m] for m in MET], rows)
T_C_N, T_C_A = out['neutral_c'], out['anchored_c']
rows = []
for run in ['neutral', 'anchored']:
    for m in MET:
        g = S[(S.run == run) & (S.metric == m) & S.contrast.isin(CON)]
        sig = g[g.significant_full]
        rows.append([run, NAME[m], len(g), len(sig), int(sig.holds_in_every_loo.sum()), '; '.join(sig[~sig.holds_in_every_loo].contrast) or 'none'])
T_HOLD = tab(['run', 'metric', 'contrasts', 'clear in full data (CI excludes 0)', 'of those, clear in every leave-one-wording-out', 'clear in full data but not in every leave-one-out'], rows)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'analysis_style'))
import arm_labels  # shared glossary: legend tables under every figure and slug table
MARK = '**Slugs and codes shown (from the shared glossary).** '
def legend(slugs, note): return MARK + note + '\n\n' + arm_labels.legend_table(slugs).rstrip('\n')
RUNS = ['neutral', 'anchored']; MODES = ['t0', 't1']; HL = ['headline-tacit', 'headline-chat', 'headline-monitored']; PP = ['p1', 'p3', 'p4', 'p5']
MSL = ['abs_spread', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share']
WD = ['w0', 'w1', 'w2', 'w3', 'w4']
MNOTE = 'Metric names map to slugs: mean quote = abs_spread, price index = price_index, profit gain index = profit_gain_index, competitive share = competitive_share, matching share = matching_share.'
CNOTE = 'Contrast codes: chat = private chat (arm headline-chat), tacit = no chat (arm headline-tacit), monitored = arm headline-monitored; p1 / p5 = penalty points; t0 / t1 = thinking off / on.'
LEG = dict(
    LEG_FIG=('**Slugs and codes shown, by axis (from the shared glossary).** Bars are labelled with the thinking-mode slug, with the run under each pair of bars; '
             'panels left to right are the five game metrics whose variance is split (' + MNOTE + ')\n\n'
             + arm_labels.axis_legend(cols=MODES + RUNS, col_name='thinking mode (each bar) and run (under each pair of bars); left to right neutral t0, neutral t1, anchored t0, anchored t1',
                                      panels=MSL, panel_name='game metric whose within-cell variance is split (left to right)',
                                      metric='variance_share',
                                      colour='not a red/green collusion scale; the y-axis is the share of within-cell variance (0 to 1, each bar sums to 1); '
                                             'blue = prompt wording (with its 4 seeds), orange = seed within wording, grey = game-level noise.').rstrip('\n')
             + '\n\n**Sources of variance (bar segments)**\n\n' + arm_labels.legend_table(['wording', 'seed', 'pair']).rstrip('\n')
             + '\n\n**Setting (the same in every bar)**\n\n' + arm_labels.legend_table(HL + PP + ['cell']).rstrip('\n')),
    LEG_VAR=legend(RUNS + MODES + ['wording', 'seed', 'pair', 'cell'] + MSL, MNOTE),
    LEG_WT=legend(WD + MODES + RUNS + HL + PP + MSL, 'Wording k (0 to 4) = slug wk; off / on = t0 / t1. ' + MNOTE),
    LEG_C_N=legend(['private', 'tacit', 'monitored'] + HL + PP + MODES + ['neutral', 'wording'] + MSL, CNOTE + ' Columns: ' + MNOTE),
    LEG_C_A=legend(['private', 'tacit', 'monitored'] + HL + PP + MODES + ['anchored', 'wording'] + MSL, CNOTE + ' Columns: ' + MNOTE),
    LEG_HOLD=legend(RUNS + MSL + ['private', 'tacit', 'monitored', 'p1', 'p5', 't0', 't1', 'wording'], MNOTE + ' ' + CNOTE),
)
tpl = open('analysis_template.md', encoding='utf-8').read()
for k, v in dict(T_VAR=T_VAR, T_WT_N=T_WT_N, T_WT_A=T_WT_A, T_C_N=T_C_N, T_C_A=T_C_A, T_HOLD=T_HOLD, **LEG).items(): tpl = tpl.replace('{{' + k + '}}', v)
open('ANALYSIS.md', 'w', encoding='utf-8', newline='\n').write(tpl)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report('ANALYSIS.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
