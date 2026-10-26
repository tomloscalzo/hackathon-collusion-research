"""Dossier 11 figures. Usage: figures.py <tables_dir> <fig_dir>"""
import sys, os
import pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

tdir, fdir = sys.argv[1:3]
os.makedirs(fdir, exist_ok=True)
COL = {'gpt-oss-20b': '#2a78d6', 'qwen3-32b thinking on': '#eb6834', 'qwen3-32b thinking off': '#1baf7a'}
LAB = {'gpt-oss-20b': 'gpt-oss-20b', 'qwen3-32b thinking on': 'Qwen3-32B, thinking on', 'qwen3-32b thinking off': 'Qwen3-32B, thinking off'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})

# Figure 1: how the best quote moves from one round to the next, matched private-chat games
lv = pd.read_csv(os.path.join(tdir, 't1_erosion_levels.csv')).set_index('model')
cats = [('stable_share', 'unchanged'), ('erosion_share', 'falls 1 to 5 ticks'), ('drop_share', 'falls more\nthan 5 ticks'), ('rise_share', 'rises')]
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = np.arange(len(cats)); w = 0.26
for i, m in enumerate(COL):
    vals = [lv.loc[m, c] for c, _ in cats]
    b = ax.bar(x + (i - 1) * w, vals, w - 0.02, color=COL[m], label='%s (%d games)' % (LAB[m], lv.loc[m, 'games']))
    for xi, v in zip(x + (i - 1) * w, vals):
        ax.text(xi, v + 0.01, '%.2f' % v, ha='center', va='bottom', fontsize=8.5, color='#333')
ax.set_xticks(x); ax.set_xticklabels([l for _, l in cats])
ax.set_ylabel('Share of rounds 2 onwards')
ax.set_xlabel('Change in the best quote (market half-spread) from the previous round')
ax.set_ylim(0, 1.05); ax.grid(axis='y', color='#ddd', lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8.5, loc='upper right')
ax.set_title('Round-to-round price moves in the same private-chat games', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(fdir, 'fig1_round_moves.png'), dpi=160); plt.close(fig)

# Figure 2: wording residuals on the price index
wr = pd.read_csv(os.path.join(tdir, 't3_wording_residuals.csv'))
wr = wr[wr.outcome == 'price_index']
WL = ['w0: plain', 'w1: cautious,\nrisk-averse', 'w2: explore,\n"bold experiment"', 'w3: formal brief', 'w4: "every round\nan experiment"']
fig, ax = plt.subplots(figsize=(7.2, 3.8))
x = np.arange(5)
for i, m in enumerate(COL):
    v = wr[wr.model == m].sort_values('wording').resid_mean.values
    ax.bar(x + (i - 1) * w, v, w - 0.02, color=COL[m], label=LAB[m])
    for xi, vi in zip(x + (i - 1) * w, v):
        ax.text(xi, vi + (0.004 if vi >= 0 else -0.004), '%+.2f' % vi, ha='center', va='bottom' if vi >= 0 else 'top', fontsize=8, color='#333')
ax.axhline(0, color='#888', lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(WL, fontsize=9)
ax.set_ylabel('Price index minus cell mean')
ax.set_xlabel('Prompt wording (paraphrase of every prompt text)')
ax.set_ylim(-0.12, 0.10); ax.grid(axis='y', color='#ddd', lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8.5, loc='lower left')
ax.set_title('Wording effect on the price index, averaged over arm x penalty cells', fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(fdir, 'fig2_wording_effects.png'), dpi=160); plt.close(fig)
print('ok')
