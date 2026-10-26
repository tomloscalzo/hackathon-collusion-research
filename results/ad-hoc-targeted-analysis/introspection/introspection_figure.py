"""Introspection figure, drawn from the committed saydo_by_arm.csv and arm_vs_control_price_index.csv only.
Arm labels read "slug: short label" from the shared glossary (tools/analysis_style/arm_glossary.csv via arm_labels);
colours and scales are unchanged. The plotted values are checked against the CSVs at the end.
Run (from this folder): python -X utf8 introspection_figure.py"""
import os, sys
import pandas as pd, numpy as np, matplotlib, matplotlib.ticker; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'analysis_style'))
import arm_labels  # noqa: E402
s = pd.read_csv('saydo_by_arm.csv'); s = s[s.run=='neutral']
b = pd.read_csv('arm_vs_control_price_index.csv'); b = b[(b.run=='neutral')&(b.thinking=='pooled')]
num = lambda x: float(x.split('%')[0])
arms = list(s.arm); lab = arm_labels.labels(arms, wrap=18)
fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.8))
bot = np.zeros(len(s)); plotted = {}
for k, c in [('consistent','#2a7f62'),('evasive','#d9822b'),('understated','#b03a48'),('overstated','#6b4c9a')]:
    v = np.array([num(x) for x in s[k]]); plotted[k] = list(v); ax[0].bar(lab, v, bottom=bot, color=c, label=k); bot += v
ax[0].set_ylabel('Share of answers (%) in each class'); ax[0].set_xlabel('question arm (slug: short label); r2/r3 = confidant/public question,'+'\n'+'f = fed back, s = saved only, r4 = announced post-game', fontsize=7); ax[0].set_title('What the answer says vs what the firm did\n(neutral run, Qwen3-32B, private chat p1, 40 games per arm;\nkeyword classifier, UNVALIDATED on edge cases)', fontsize=9)
ax[0].legend(fontsize=7, loc='upper center', bbox_to_anchor=(0.5, -0.30), ncol=4, title='answer class (what the answer says vs what the firm did)', title_fontsize=7); ax[0].tick_params(axis='x', labelsize=6.5)
y = np.arange(len(b))
ax[1].errorbar(b.est, y, xerr=[b.est-b.lo, b.hi-b.est], fmt='o', color='#1b6ca8', capsize=3)
ax[1].axvline(0, color='k', lw=.8); ax[1].set_yticks(y); ax[1].set_yticklabels(arm_labels.labels(list(b.arm), wrap=30), fontsize=8); ax[1].invert_yaxis()
ax[1].set_xlabel('Price index difference: arm minus no-question control (headline-chat: private chat, no other lever; p1)'+'\n'+'(dot = mean of 20 pairs; bar = 95% bootstrap CI)', fontsize=7); ax[1].set_ylabel('question arm'); ax[1].xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.05)); ax[1].tick_params(axis='x', labelsize=7); ax[1].set_title('Does asking change behaviour?\n(neutral run, both thinking modes averaged per pair)', fontsize=9)
fig.tight_layout(); fig.savefig('introspection_figure.png', dpi=130)
# check: the plotted values are the CSV values
chk = pd.read_csv('saydo_by_arm.csv'); chk = chk[chk.run=='neutral']
assert list(chk.arm) == arms and len(arms) == 5
for k, v in plotted.items():
    assert v == [num(x) for x in chk[k]], k
chk2 = pd.read_csv('arm_vs_control_price_index.csv'); chk2 = chk2[(chk2.run=='neutral')&(chk2.thinking=='pooled')]
assert list(chk2.est) == list(b.est) and list(chk2.lo) == list(b.lo) and list(chk2.hi) == list(b.hi) and len(b) == 5
print('introspection: introspection_figure.png re-rendered; plotted values equal the CSVs')
