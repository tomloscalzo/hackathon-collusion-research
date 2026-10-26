"""Redraw fig_variance.png from variance_by_pair.csv (labels only; same data as the block in wording_seed.py). usage: python -X utf8 fig_variance.py
Run and thinking-mode tick labels are "slug: short label" from the shared glossary (tools/analysis_style/arm_labels.py)."""
import os, sys, textwrap
import pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'analysis_style'))
import arm_labels
V = pd.read_csv('variance_by_pair.csv')
METRICS = ['mean_quote', 'price_index', 'gain', 'comp_share', 'match_share']
TITLES = {'mean_quote': 'mean quote (abs_spread)\n(1.00-5.00)', 'price_index': 'price index\n(0-1)', 'gain': 'profit gain index\n(0-1)', 'comp_share': 'competitive share\n(0-1)', 'match_share': 'matching share\n(0-1)'}
MODE = {'thinking off': 't0', 'thinking on': 't1'}
tick = lambda run, s_: arm_labels.label(MODE[s_]).replace(': ', ':\n')   # the run label goes under each pair of bars
fig, axs = plt.subplots(1, 5, figsize=(17, 5.6), sharey=True)
plotted = []
for ax, met in zip(axs, METRICS):
    sub = V[(V.metric == met) & V.subset.isin(['thinking off', 'thinking on'])]; labs = []; x = 0
    for run in ['neutral', 'anchored']:
        for s_ in ['thinking off', 'thinking on']:
            r = sub[(sub.run == run) & (sub.subset == s_)].iloc[0]
            ax.bar(x, r.share_wording, color='#1f77b4', label='wording (5 prompt paraphrases, with their seeds)' if (x == 0 and met == 'gain') else None)
            ax.bar(x, r.share_seed_in_wording, bottom=r.share_wording, color='#d95f02', label='seed within wording (4 seeds per wording)' if (x == 0 and met == 'gain') else None)
            ax.bar(x, 1 - r.share_pair, bottom=r.share_pair, color='#cccccc', label='game-level noise (everything not shared by a pair)' if (x == 0 and met == 'gain') else None)
            plotted.append((met, run, s_, r.share_wording, r.share_seed_in_wording, r.share_pair))
            labs.append(tick(run, s_)); x += 1
    for g, run in enumerate(['neutral', 'anchored']):
        ax.text(2 * g + 0.5, -0.17, textwrap.fill(arm_labels.label(run) + ' run', 24, break_on_hyphens=False), transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
    ax.set_xticks(range(x)); ax.set_xticklabels(labs, fontsize=7.5); ax.set_title(TITLES[met], fontsize=9); ax.spines[['top', 'right']].set_visible(False)
axs[0].set_ylabel('share of within-cell variance (0-1; bars sum to 1)')
fig.supxlabel('Bars: ' + arm_labels.label('neutral') + ' run and ' + arm_labels.label('anchored') + ' run, each with t0 = thinking off and t1 = thinking on. Each bar: 12 headline cells (3 communication arms x 4 penalty points), 20 (wording, seed) pairs.', fontsize=8)
fig.suptitle('Share of within-cell variance of each game metric explained by prompt wording, seed within wording, and game-level noise', fontsize=10)
fig.legend(frameon=False, fontsize=8, loc='upper center', ncol=3, bbox_to_anchor=(0.5, 0.95))
fig.tight_layout(rect=(0, 0.1, 1, 0.88)); fig.savefig('fig_variance.png', dpi=140)
# check (c): the plotted values are the committed CSV values
V2 = pd.read_csv('variance_by_pair.csv')
for met, run, s_, w, sd, sp in plotted:
    r = V2[(V2.metric == met) & (V2.run == run) & (V2.subset == s_)].iloc[0]
    assert (w, sd, sp) == (r.share_wording, r.share_seed_in_wording, r.share_pair)
print('fig_variance.png written; plotted values equal variance_by_pair.csv:', len(plotted), 'bars')
