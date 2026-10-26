"""Re-render only fig_screening_heatmap.png from tables/screening_lever_outcome.csv
(same drawing code as the block in step2_contrasts.py; colours and colourbar label only, no numbers recomputed).
Column labels read "metric slug: short label" from the shared glossary (tools/analysis_style/arm_labels.py);
--orig draws the old abbreviated labels (to check that the committed PNG is reproduced byte for byte).
Every annotated value is asserted equal to its screening_lever_outcome.csv cell. $REPLOT_OUT overrides the output folder.
Usage: python rerender_screening_heatmap.py [--orig]"""
import os
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools' / 'analysis_style'))
import collusion_colors as CC
import arm_labels as AL
ORIG = '--orig' in sys.argv
OUTDIR = Path(os.environ.get('REPLOT_OUT', HERE / 'figures'))
GS = {'explicit': 'explicit_agreement_flag'}
NCHK = 0
SC = pd.read_csv(HERE / 'tables' / 'screening_lever_outcome.csv')
SCRO = ['profit_gain_index', 'price_index', 'competitive_share', 'explicit', 'messages', 'rounds_played', 'war_length']
if ORIG:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={'wspace': 0.7})
else:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)
FCODE = {'comm': 'communication', 'penalty_point': 'penalty_point', 'wording': 'wording', 'planned_length': 'planned_length'}
fig.suptitle('Screening: effect size of each design factor on each outcome, neutral run, headline games (n = 240 per panel), exploratory; * = BH q < 0.05')
for ax, mode in zip(axes, ['t0', 't1']):
    pv_ = SC[SC['mode'] == mode].pivot(index='lever', columns='outcome', values='root_eps')[SCRO]
    q_ = SC[SC['mode'] == mode].pivot(index='lever', columns='outcome', values='bh_q')[SCRO]
    im = ax.imshow(pv_.values, cmap=CC.NEUTRAL_CMAP, vmin=0, vmax=1)   # effect size has no collusion direction
    for i in range(pv_.shape[0]):
        for j in range(pv_.shape[1]):
            r_ = SC[(SC['mode'] == mode) & (SC.lever == pv_.index[i]) & (SC.outcome == SCRO[j])]
            assert len(r_) == 1 and r_.root_eps.iloc[0] == pv_.values[i, j]; NCHK += 1
            ax.text(j, i, '%.2f%s' % (pv_.values[i, j], '*' if q_.values[i, j] < .05 else ''), ha='center', va='center', color='w' if pv_.values[i, j] > 0.7 else 'k', fontsize=10)
    ax.set_xticks(range(len(SCRO)))
    if ORIG:
        ax.set_xticklabels(['profit gain', 'price idx', 'comp. share', 'explicit flag', 'messages', 'rounds', 'war len'], rotation=30, ha='right')
    else:
        _, k1 = CC.set_arm_ticks(ax, [GS.get(o, o) for o in SCRO], 'x', grow=(mode == 't0'))
        _, k2 = CC.set_arm_ticks(ax, [FCODE[x] for x in pv_.index], 'y', grow=(mode == 't0'))
        assert k1 is None and k2 is None, 'numbered-key fallback'
    if ORIG:
        ax.set_yticks(range(pv_.shape[0])); ax.set_yticklabels([{'comm': 'communication', 'penalty_point': 'penalty point', 'wording': 'prompt wording', 'planned_length': 'planned length'}[x] for x in pv_.index])
    ax.set_title('thinking %s (headline games, exploratory)' % ('off' if mode == 't0' else 'on')); ax.set_xlabel('outcome (defined in the caption)'); ax.set_ylabel('design factor')
fig.colorbar(im, ax=axes, shrink=0.8, label='effect size: root epsilon-squared (0 to 1); * = BH q < 0.05' + chr(10) + 'neutral colour: this number has no collusion direction')
fig.savefig(OUTDIR / 'fig_screening_heatmap.png', dpi=110, bbox_inches='tight'); plt.close(fig)
print('annotated cells checked against the table:', NCHK)
