"""Redraw the lever forest from tables/forest_neutral.csv (step2_contrasts.py output), with row labels. usage: forest_plot.py OUTDIR [--orig]
Row labels read "arm slug: lever in words" (slugs from the shared glossary tools/analysis_style/arm_glossary.csv);
--orig draws the old words-only labels (to check the data path reproduces the committed PNGs). Values are not changed:
every plotted point is asserted equal to its forest_neutral.csv row."""
import sys
from pathlib import Path
import pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT = sys.argv[1]
FOR = pd.read_csv(OUT + 'tables/forest_neutral.csv')
ORDER = ['communication', 'side arm at point 3', 'control (positive/null)', 'D set at the cell', 'introspection at the cell']
LAB = {'pgi': 'Profit gain index', 'price': 'Price index', 'comp': 'Competitive share', 'explicit': 'Explicit-agreement flag rate'}
ORIG = '--orig' in sys.argv
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools' / 'analysis_style'))
import arm_labels as AL  # noqa: E402
import collusion_colors as CC  # noqa: E402
SLUG = {'three firms (group)': 'n3-group', 'three firms + planted cheater': 'n3-cheater', 'published chat': 'm-pub',
        'chat "not monitored"': 'm-mon0', 'three firms, ethics rule on one': 'n3-ethics', 'asymmetric rules': 'm-asym',
        'compliance reminder': 'm-comp', 'incentive text (joint)': 'm-inc-joint', 'incentive text (target)': 'm-inc-target',
        '5-tick start rule': 'start-5tick', 'maximise-joint-profit instruction': 'ctl-32b-joint',
        'strict compete instruction': 'ctl-32b-compete', 'reasoning-monitor threat A': 'd-cot-monitor-a',
        'reasoning-monitor threat B': 'd-cot-monitor-b', 'instruction-conflict score': 'd-conflict',
        'temptation score A': 'd-temptation-a', 'temptation score B': 'd-temptation-b', 'placebo score': 'd-placebo',
        'R2f fed-back, confidant': 'r2f-confidant', 'R3f fed-back, public': 'r3f-public',
        'R2s saved-only, confidant': 'r2s-confidant', 'R3s saved-only, public': 'r3s-public', 'R4 announced': 'r4-announced'}
PAIRS = {'chat minus tacit (pooled over points)': ('headline-chat', 'headline-tacit'),
         'monitored minus chat (pooled over points)': ('headline-monitored', 'headline-chat')}
for _s in list(SLUG.values()) + [a for p_ in PAIRS.values() for a in p_]:
    assert _s in AL.glossary(), _s


def rowlab(l):
    if ORIG:
        return l
    if l in PAIRS:
        return '%s minus %s (pooled over points)' % PAIRS[l]
    return '%s: %s' % (SLUG[l], l)


def rowcode(l):
    """(code, short text) for the shared wrapped tick: the arm slug on line 1, the lever in words below"""
    if l in PAIRS:
        return PAIRS[l][0], 'minus %s (pooled over points)' % PAIRS[l][1]
    return SLUG[l], l


NCHK = [0]
COL = {'declared': '#1b6ca8', 'exploratory': '#c4631c', 'control': '#6b6b6b'}


def forest(sortby, fn):
    fig, axes = plt.subplots(2, 4, figsize=(22, 17) if ORIG else (26, 20), constrained_layout=not ORIG)
    for ri, mode in enumerate(['t0', 't1']):
        b = FOR[FOR['mode'] == mode]
        b = b[(b.family != 'communication') | b.lever.str.contains('pooled')]
        labs = []
        for fam in ORDER:
            labs += list(dict.fromkeys(b[b.family == fam].lever))
        if sortby:
            ref = b[b.outcome == 'pgi'].set_index('lever').est
            labs = sorted(labs, key=lambda l: ref.get(l, 0))
        for ci, oc in enumerate(LAB):
            ax = axes[ri, ci]
            ax.axvspan(-0.25, 0.25, color='#dddddd', alpha=.5, lw=0); ax.axvline(0, color='k', lw=.8)
            for yi, l in enumerate(labs):
                r = b[(b.lever == l) & (b.outcome == oc)]
                if r.empty: continue
                r = r.iloc[0]; c = COL.get(r.kind, '#c4631c')
                assert len(b[(b.lever == l) & (b.outcome == oc)]) == 1; NCHK[0] += 1
                ax.plot([r.lo, r.hi], [yi, yi], color=c, lw=2.2); ax.plot(r.est, yi, 's' if r.kind == 'declared' else 'o', color=c, ms=6)
            if ORIG:
                ax.set_yticks(range(len(labs))); ax.set_yticklabels([rowlab(l) for l in labs], fontsize=8)
            else:
                codes = [rowcode(l)[0] for l in labs]
                _, key = CC.set_arm_ticks(ax, codes, 'y', wrap=40, max_lines=2, short={c: t for c, t in map(rowcode, labs)} if len(set(codes)) == len(codes) else None,
                                          grow=(ri == 0 and ci == 0))
                assert key is None, 'forest ticks fell back to a numbered key'
                if len(set(codes)) != len(codes):
                    raise SystemExit('duplicate row codes')
            ax.set_ylim(len(labs) - .5, -.5); ax.set_xlim(-1.05, 1.05)
            ax.set_title('%s, thinking %s' % (LAB[oc], 'off' if mode == 't0' else 'on'), fontsize=10)
            ax.set_xlabel('arm minus control, 95% interval (grey: +-0.25 rule-of-thumb detectable effect)', fontsize=7 if ORIG else 9)
    fig.suptitle('Lever forest, neutral run, 20 (wording, seed) pairs per row (%s). Blue squares declared, orange circles exploratory, grey controls.' % ('sorted by effect on profit gain' if sortby else 'ordered by lever family'), fontsize=13)
    if ORIG:
        fig.tight_layout(rect=[0, 0, 1, .97])
    fig.savefig(OUT + 'figures/' + fn, dpi=100, **({} if ORIG else {'bbox_inches': 'tight'})); plt.close(fig)


forest(False, 'fig_forest_by_family.png'); forest(True, 'fig_forest_sorted.png')
print('forest points drawn, one table row each:', NCHK[0])
