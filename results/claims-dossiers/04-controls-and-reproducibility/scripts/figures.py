import sys, os, textwrap; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../tools/analysis_style')))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from common import *
import arm_labels as AL
L = pd.read_csv(OUT + '/g_repro_lever_effects.csv')
NICE = {'fx-ctl-joint - ctl-32b-joint': 'fx-ctl-joint minus ctl-32b-joint: joint-profit control with formula payoff block, minus ordinary joint-profit control',
        'fx-chat-p1 - nx-chat-p1 (formula minus no-numbers)': 'fx-chat-p1 minus nx-chat-p1: formula minus no-numbers, private chat, p1',
        'headline-chat p1 - tacit p1 (chat)': 'headline-chat p1 minus headline-tacit p1: private chat vs no chat, light fine',
        'headline-chat p5 - tacit p5 (chat)': 'headline-chat p5 minus headline-tacit p5: private chat vs no chat, heavy fine',
        'headline-chat p5 - p1 (penalty)': 'headline-chat p5 minus p1: heavy vs light fine, private chat',
        'headline-chat p3 - p1 (penalty)': 'headline-chat p3 minus p1: intermediate vs light fine, private chat',
        'headline-tacit p5 - p1 (penalty)': 'headline-tacit p5 minus p1: heavy vs light fine, no chat'}
def lab(r):
    c = r.contrast
    xw = (set(eval(r.arm_waves)) != set(eval(r.control_waves)))
    mark = ' [cross-wave]' if xw else ''
    if c in NICE: return NICE[c] + (' [same run]' if r.same_run_root else ' [other run root]') + mark
    return AL.label(r.arm).replace(' (32B)', '') + f'  (vs {r.control})' + mark
L['lab'] = L.apply(lab, axis=1)
L['lab'] = L['lab'].str.replace('headline-chat p1: ', 'headline-chat p1: ')
L = L.sort_values('price_diff').reset_index(drop=True)
RED, GREEN = '#b2182b', '#1a9850'
fig, ax = plt.subplots(figsize=(13, 0.34 * len(L) + 2.2), constrained_layout=True)
ax.axvspan(-0.1044, 0.1044, color='#cccccc', alpha=0.6, lw=0)
for i, r in L.iterrows():
    c = RED if r.price_diff > 0 else GREEN
    ax.plot([r.price_lo, r.price_hi], [i, i], color=c, lw=2)
    ax.plot(r.price_diff, i, 'o' if r.same_run_root else 's', color=c, ms=7, mfc=c if r.ci_excludes0 else 'white')
ax.axvline(0, color='k', lw=1)
ax.set_yticks(range(len(L))); ax.set_yticklabels([textwrap.fill(t, 62) for t in L.lab], fontsize=9)
ax.set_xlabel('gpt-oss-20b: change in price index, arm minus its control (paired on wording and seed; 95% bootstrap CI)\nred = more collusive, green = more competitive; grey band = the replicate-minus-headline gap (+/-0.104)', fontsize=10)
fig.suptitle('Lever effects on the price index against the size of the same-prompt replicate gap (gpt-oss-20b, neutral table, n = 11 to 20 pairs per row)', fontsize=11)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], marker='o', color='k', mfc='k', ls='', label='filled circle: CI excludes 0, control from the same run root'),
                   Line2D([], [], marker='o', color='k', mfc='white', ls='', label='open circle: CI includes 0, same run root'),
                   Line2D([], [], marker='s', color='k', mfc='k', ls='', label='square: control from a different run root (cross-root contrast)'),
                   Line2D([], [], marker='', color='none', ls='', label='[cross-wave] after a label: arm and control ran in different waves')], loc='lower right', fontsize=9)
ax.tick_params(axis='x', labelsize=9); fig.savefig(OUT + '/fig1_lever_effects_vs_replicate_gap.png', dpi=130)

W = pd.read_csv(OUT + '/q14_wording_effect.csv')
fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True, constrained_layout=True)
q = load('qwen'); o = load('oss')
specs = [('Qwen3-32B thinking off (t0): 12 headline cells', q[(q.think == 't0') & q.arm.isin(['headline-chat', 'headline-tacit', 'headline-monitored'])]),
         ('Qwen3-32B thinking on (t1): 12 headline cells', q[(q.think == 't1') & q.arm.isin(['headline-chat', 'headline-tacit', 'headline-monitored'])]),
         ('gpt-oss-20b (reasoning medium): 5 headline cells', o[o.arm.isin(['headline-chat', 'headline-tacit'])])]
for ax, (t, D) in zip(axs, specs):
    D = D.copy(); D['cell'] = D.arm + D.penalty_point.astype(str); D['adj'] = D.profit_gain_index - D.groupby('cell').profit_gain_index.transform('mean')
    pm = D.groupby('pair').agg(adj=('adj', 'mean'), w=('wording', 'first'))
    for w in range(5):
        v = pm[pm.w == w].adj.values; ax.scatter(np.full(len(v), w) + np.linspace(-0.12, 0.12, len(v)), v, color='#555555', s=28, zorder=3)
        ax.plot([w - 0.25, w + 0.25], [v.mean()] * 2, color='#2166ac', lw=3, zorder=4)
    ax.axhline(0, color='k', lw=0.8); ax.set_xticks(range(5)); ax.set_xticklabels([f'wording {w}' for w in range(5)], fontsize=9)
    ax.set_title(t, fontsize=10); ax.set_xlabel('prompt wording (5 hand-written paraphrases; 4 seeds each)', fontsize=9)
axs[0].set_ylabel('profit gain index of a (wording, seed) pair,\naveraged over its games, minus the cell mean', fontsize=9)
fig.suptitle('Does prompt wording move the profit gain index? Grey dots = 20 pairs; blue bar = wording mean', fontsize=11)
fig.savefig(OUT + '/fig2_wording_profit_gain.png', dpi=130)
print(L[['lab', 'price_diff']].tail(3))
