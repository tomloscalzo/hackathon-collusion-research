"""Re-render figures/fig_channel_shift_quadrant.png from the committed tables/channel_shift_contrasts.csv (the drawing
block of step2_contrasts.py; labels only: each point is labelled "arm slug: short label" from the shared glossary
tools/analysis_style/arm_labels.py). No statistic is recomputed; every plotted point is asserted equal to its table row.
--orig draws the old labels. $REPLOT_OUT overrides the output folder.
Usage: python -X utf8 replot_channel_shift.py [--orig]"""
import os
import sys
import textwrap
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools' / 'analysis_style'))
import arm_labels as AL  # noqa: E402

ORIG = '--orig' in sys.argv
OUTDIR = Path(os.environ.get('REPLOT_OUT', HERE / 'figures'))
CS = pd.read_csv(HERE / 'tables' / 'channel_shift_contrasts.csv')
ARM = {'monitored chat vs private chat': 'headline-monitored', 'published chat vs private chat (p3)': 'm-pub',
       '"not monitored" vs private chat (p3)': 'm-mon0', 'reasoning-monitor threat A vs control (cell)': 'd-cot-monitor-a',
       'reasoning-monitor threat B vs control (cell)': 'd-cot-monitor-b', 'R4 announced vs control (cell)': 'r4-announced'}
n = 0
fig, axes = plt.subplots(1, 2, figsize=(14, 6) if ORIG else (16, 7), sharey=True)
for ax, mode in zip(axes, ['t0', 't1']):
    ax.axhline(0, color='k', lw=.7); ax.axvline(0, color='k', lw=.7)
    for lab in CS.contrast.unique():
        a = CS[(CS.run == 'neutral') & (CS.contrast == lab) & (CS['mode'] == mode)]
        if a.empty: continue
        x = a[a.outcome == 'explicit_round_share']; y = a[a.outcome == 'pgi']
        if x.empty or y.empty: continue
        assert len(x) == 1 and len(y) == 1
        kw = {} if ORIG else dict(color='C%d' % list(ARM).index(lab), label=AL.label(ARM[lab]))
        c = ax.errorbar(x.est.iloc[0], y.est.iloc[0], xerr=[[x.est.iloc[0] - x.lo.iloc[0]], [x.hi.iloc[0] - x.est.iloc[0]]], yerr=[[y.est.iloc[0] - y.lo.iloc[0]], [y.hi.iloc[0] - y.est.iloc[0]]], fmt='o', capsize=3, **kw)
        assert c.lines[0].get_xdata()[0] == x.est.iloc[0] and c.lines[0].get_ydata()[0] == y.est.iloc[0]; n += 1
        text = lab.split(' vs ')[0] if ORIG else ARM[lab]
        ax.annotate(text, (x.est.iloc[0], y.est.iloc[0]), fontsize=7 if ORIG else 9, xytext=(4, 4), textcoords='offset points')
    ax.set_title('thinking %s' % ('off' if mode == 't0' else 'on') if ORIG else '%s: thinking %s' % (mode, 'off' if mode == 't0' else 'on'))
    ax.set_xlabel('change in share of rounds with EXPLICIT talk (keyword rule), arm minus control')
axes[0].set_ylabel('change in profit gain index, arm minus control')
if not ORIG:
    for ax in axes:
        ax.legend(fontsize=9, loc='upper center', bbox_to_anchor=(0.5, -0.12), title='arm (colour; point labelled with its slug)', title_fontsize=9)
fig.suptitle('Channel shift (exploratory): talk about coordinating moves little, and so does profit, when coordination is made risky (neutral run)'
             + ('' if ORIG else '\ncontrol for every arm: headline-chat (private chat) at the same penalty point (p3 for m-pub and m-mon0, p1 for the cell arms; pooled over p1, p3, p4, p5 for headline-monitored)'),
             fontsize=None if ORIG else 10)
fig.tight_layout(); OUTDIR.mkdir(parents=True, exist_ok=True); fig.savefig(OUTDIR / 'fig_channel_shift_quadrant.png', dpi=110, **({} if ORIG else {'bbox_inches': 'tight'})); plt.close(fig)
print('points checked against the table:', n)
