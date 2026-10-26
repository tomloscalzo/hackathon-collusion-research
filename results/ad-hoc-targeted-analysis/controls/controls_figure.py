import os, sys, textwrap
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'tools', 'analysis_style'))
import arm_labels  # shared slug glossary: ticks read "slug: short label"
os.chdir(HERE)
fig, ax = plt.subplots(1, 2, figsize=(12, 6.0), sharey=True)
ROLE = {'ctl-32b-compete': '(strict-compete, negative control)', 'ctl-32b-joint': '(joint-profit, positive control)', 'headline-chat': '(reference)'}
W = lambda t: textwrap.fill(t, 24, break_on_hyphens=False, break_long_words=False)
lab = {k: W(arm_labels.label(k)) + '\n' + W(v) for k, v in ROLE.items()}
col = {'off':'#1b6ca8','on':'#d9822b'}
rng = np.random.default_rng(0)
plotted = []
for a, run in zip(ax, ['neutral','anchored']):
    g = pd.read_csv(f'control_games_{run}.csv')
    for i, arm in enumerate(lab):
        for j, m in enumerate(['off','on']):
            y = g[(g.arm==arm)&(g['mode']==m)].mean_q
            x = i + (j-0.5)*0.3 + rng.uniform(-.05,.05,len(y))
            sc = a.scatter(x, y, s=22, color=col[m], alpha=.7, label=arm_labels.label('t' + str(j)) if i==0 else None)
            a.hlines(y.mean(), i+(j-.5)*.3-.12, i+(j-.5)*.3+.12, color='k')
            plotted.append((run, arm, m, sc, y.mean(), a.collections[-1]))
    for v, t in [(1,'1.00 competitive floor'),(2,'2.00 threshold'),(3,'3.00 monopoly')]:
        a.axhline(v, ls=':', color='grey'); a.text(2.45, v+.03, t, ha='right', fontsize=7, color='grey')
    a.set_xticks(range(3)); a.set_xticklabels(lab.values(), fontsize=8); a.set_title(arm_labels.label(run) + ' (' + ('1.00-4.00' if run=='neutral' else 'examples at 1.54, 2.09, 3.00') + ')', fontsize=9); a.set_xlabel('control arm (20 games per mode; penalty point p3, private chat)', fontsize=8); a.set_ylim(.9,3.1)
ax[0].set_ylabel('Mean half-spread quote per game (one dot = one game)')
h, l = ax[0].get_legend_handles_labels(); h.append(Line2D([0],[0],color='k',lw=2)); l.append('black bar = mean of the 20 game means')
fig.legend(h, l, fontsize=8, loc='lower center', ncol=3, frameon=False)
fig.suptitle('Mean quote (half-spread) per game by control arm: strict-compete and joint-profit instruction controls vs the headline-chat reference; one dot = one game', fontsize=9)
fig.tight_layout(rect=[0,.06,1,.95])
# check: every plotted dot and bar is a committed CSV value (no number changes)
for run, arm, m, sc, mu, bar in plotted:
    g = pd.read_csv(f'control_games_{run}.csv'); ref = g[(g.arm==arm)&(g['mode']==m)].mean_q.to_numpy()
    assert np.array_equal(sc.get_offsets()[:, 1].data if hasattr(sc.get_offsets(), 'data') else sc.get_offsets()[:, 1], ref)
    assert np.allclose(bar.get_segments()[0][:, 1], ref.mean(), rtol=0, atol=1e-12)
fig.savefig('controls_figure.png', dpi=130)
print('controls_figure.png written; plotted values equal control_games_*.csv')
