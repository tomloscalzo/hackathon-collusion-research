"""Redraw figures/fig_screening_heatmap.png from tables/screening_lever_outcome.csv (labels and spacing only; data unchanged).
Usage: python -X utf8 replot_screening_heatmap.py <step2 folder>/"""
import sys, pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT = sys.argv[1] if len(sys.argv) > 1 else './'
SC = pd.read_csv(OUT + 'tables/screening_lever_outcome.csv')
SCRO = ['profit_gain_index', 'price_index', 'competitive_share', 'explicit', 'messages', 'rounds_played', 'war_length']
fig, axes = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={'wspace': 0.7})
fig.suptitle('Screening: effect size of each design factor on each outcome, neutral run, headline games (n = 240 per panel), exploratory; * = BH q < 0.05')
for ax, mode in zip(axes, ['t0', 't1']):
    pv_ = SC[SC['mode'] == mode].pivot(index='lever', columns='outcome', values='root_eps')[SCRO]
    q_ = SC[SC['mode'] == mode].pivot(index='lever', columns='outcome', values='bh_q')[SCRO]
    im = ax.imshow(pv_.values, cmap='viridis', vmin=0, vmax=1)
    for i in range(pv_.shape[0]):
        for j in range(pv_.shape[1]):
            ax.text(j, i, '%.2f%s' % (pv_.values[i, j], '*' if q_.values[i, j] < .05 else ''), ha='center', va='center', color='w', fontsize=8)
    ax.set_xticks(range(len(SCRO))); ax.set_xticklabels(['profit gain', 'price idx', 'comp. share', 'explicit flag', 'messages', 'rounds', 'war len'], rotation=30, ha='right')
    ax.set_yticks(range(pv_.shape[0])); ax.set_yticklabels([{'comm': 'communication', 'penalty_point': 'penalty point', 'wording': 'prompt wording', 'planned_length': 'planned length'}[x] for x in pv_.index])
    ax.set_title('thinking %s (headline games, exploratory)' % ('off' if mode == 't0' else 'on')); ax.set_xlabel('outcome (defined in the caption)'); ax.set_ylabel('design factor')
fig.colorbar(im, ax=axes, shrink=0.8, label='effect size: root epsilon-squared (0 to 1)')
fig.savefig(OUT + 'figures/fig_screening_heatmap.png', dpi=110, bbox_inches='tight'); plt.close(fig)
