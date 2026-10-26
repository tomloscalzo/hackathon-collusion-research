"""Step 1.5 heat maps of derived features. usage: plots.py STEP1 AUDIT READING BATCH OUTDIR"""
import sys, os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

import features as F
import specs as S
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'tools' / 'analysis_style'))
import collusion_colors as CC   # shared red = collusion / green = competition convention
import arm_labels as AL         # 'slug: short label' tick text from tools/analysis_style/arm_glossary.csv
import textwrap

step1, audit, reading, batch, out = sys.argv[1:6]
DD = S.load_dd(step1)   # feature definitions for the in-chart row descriptions (same source as the STEP1_5.md tables)
os.makedirs(out + '/figures', exist_ok=True)
os.makedirs(out + '/tables', exist_ok=True)
_committed = out + '/tables/derived_game_table.csv'
if os.environ.get('STEP15_USE_COMMITTED_TABLE') == '1' and os.path.exists(_committed):
    d = pd.read_csv(_committed, low_memory=False)   # re-render colours only: reuse the committed numbers exactly
else:
    d = F.build(step1, audit, reading, batch)
d.to_csv(out + '/tables/derived_game_table.csv', index=False)

LEV = S.levels(d)   # shared with mkdoc.py so the legend tables list exactly the levels drawn
ARM_ORDER = LEV['arm']
for k in ['penalty_point', 'wording', 'planned_length', 'seed']:
    LEV[k] = [int(x) for x in LEV[k]]
    d[k] = d[k].astype('Int64')
d['cell'] = d.arm + '|' + d.thinking

# usable features
feats = [f for f in S.G if f in d.columns and d[f].notna().sum() >= 20 and d[f].nunique() > 1]
dropped = [f for f in S.G if f not in feats]
meta = {}
for f in feats:
    grp, status, kind = S.G[f]
    x = d[f].dropna()
    if kind in ('share', 'binary'):
        lo, hi = 0.0, 1.0
    elif kind == 'score':
        lo, hi = 1.0, 5.0
    else:
        lo, hi = float(np.percentile(x, 1)), float(np.percentile(x, 99))
        if hi <= lo:
            lo, hi = float(x.min()), float(x.max())
    meta[f] = dict(group=grp, status=status, kind=kind, lo=lo, hi=hi)
groups = sorted(set(m['group'] for m in meta.values()))
UNV = lambda f: 'UNVAL' in meta[f]['status']


def feat_cmap(f):
    c = CC.cmap_for(f)
    c = plt.get_cmap(c) if isinstance(c, str) else c
    c = c.copy(); c.set_bad('#e6e6e6')
    return c


def row_rgba(norm, fl):
    out = np.zeros(norm.shape + (4,))
    for i, f in enumerate(fl):
        out[i] = feat_cmap(f)(np.ma.masked_invalid(norm[i]))
    return out


def txt_color(f, nv):
    return CC.text_color(nv, 0, 1) if CC.direction(f) != CC.NEUTRAL else ('white' if nv > 0.7 else 'black')


PEND = []   # annotations are placed after layout so the figure can be grown to fit >= 9.5 pt numbers
ANNOT_PT = CC.MIN_ANNOT_PT
DROPPED = []


def annotate_later(ax, items, nr, nc):
    PEND.append((ax, items, nr, nc))


def flush_annotations(fig):
    fig.draw_without_rendering()   # constrained layout: settle the axes positions before sizing the numbers
    mine = [p for p in PEND if p[0].figure is fig]
    for p in mine:
        PEND.remove(p)
    ok = all(CC.annotations_fit(fig, ax, nr, nc, [t for _, _, t, _ in it], max_scale=2.5) for ax, it, nr, nc in mine)
    if not ok:
        return False
    for ax, it, nr, nc in mine:
        CC.fit_annotations(fig, ax, nr, nc, [t for _, _, t, _ in it], max_scale=2.5)
    for ax, it, nr, nc in mine:
        for i, j, t, c in it:
            ax.text(j, i, t, ha='center', va='center', fontsize=ANNOT_PT, color=c)
    return True


def legend_bar(fig, axs, label):
    import matplotlib as mpl
    sm = mpl.cm.ScalarMappable(cmap=CC.COLLUSION_CMAP, norm=mpl.colors.Normalize(0, 1)); sm.set_array([])
    cb = fig.colorbar(sm, ax=axs, fraction=0.025, pad=0.02)
    cb.set_ticks([0, 1]); cb.set_ticklabels(['row low', 'row high']); cb.ax.tick_params(labelsize=9)
    cb.set_label(label + '\nred = more collusive / green = more competitive (competition-direction rows run green at the high end);'
                 '\nblue rows have no collusion direction', fontsize=7)


def fmt(v):
    if pd.isna(v):
        return ''
    a = abs(v)
    return f'{v:.0f}' if a >= 100 else (f'{v:.1f}' if a >= 10 else f'{v:.2f}')


def cell_text(m, n):
    return '' if n == 0 else f'{fmt(m)}\nn={n}'


def draw(ax, mat, nmat, f, xl, yl, fs=6, show_y=True, rotx=0, tfs=None):
    m = meta[f]
    norm = np.clip((mat - m['lo']) / (m['hi'] - m['lo']), 0, 1)
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=feat_cmap(f), vmin=0, vmax=1, aspect='auto')
    annotate_later(ax, [(i, j, cell_text(mat[i, j], int(nmat[i, j])), txt_color(f, norm[i, j]))
                        for i in range(mat.shape[0]) for j in range(mat.shape[1])
                        if nmat[i, j] > 0 and not np.isnan(mat[i, j])], mat.shape[0], mat.shape[1])
    ax.set_xticks(range(len(xl)))
    ax.set_xticklabels([str(x) for x in xl], fontsize=tfs or fs + 1, rotation=rotx, ha='center')
    ax.set_yticks(range(len(yl)))
    ax.set_yticklabels([str(y) for y in yl] if show_y else [], fontsize=tfs or fs + 1)
    ax.tick_params(length=0)
    return im


def grp_stats(feat_list, col, levels):
    M = np.full((len(feat_list), len(levels)), np.nan)
    N = np.zeros((len(feat_list), len(levels)), int)
    for j, lv in enumerate(levels):
        sub = d[d[col] == lv]
        for i, f in enumerate(feat_list):
            x = sub[f].dropna()
            N[i, j] = len(x)
            if len(x):
                M[i, j] = x.mean()
    return M, N


def lab(f):
    m = meta[f]
    s = f'{f}  [{m["lo"]:.4g} to {m["hi"]:.4g}]'
    return s + ('  UNVAL' if UNV(f) else '')


TICK_PT = CC.MIN_TICK_PT   # owner's rule: no tiny tick text (>= 9 pt); wrap instead
FEAT_WRAP, FEAT_LINES = 34, 2
KEYED = []   # (figure title, axis) where set_arm_ticks fell back to a numbered key; must stay empty


def feat_short(f):
    """Short in-chart description of a feature: the glossary short label when the feature is in arm_glossary.csv,
    else its definition (specs / data dictionary); trimmed below to FEAT_LINES lines."""
    g = AL.glossary()
    return g[f]['short_label'] if f in g else S.feature_how(f, DD)[0]


def rowlab(f):
    """Feature row label: name, fixed colour range and UNVAL mark, then the short description (wrapped, trimmed)."""
    m = meta[f]
    head = [f, f'[{m["lo"]:.4g} to {m["hi"]:.4g}]' + ('  UNVAL' if UNV(f) else '')]
    return '\n'.join(head + CC._trim_words(feat_short(f), FEAT_WRAP, FEAT_LINES))


def row_h(fl):
    """Row height (inches) that fits the tallest row label at TICK_PT."""
    lines = max(rowlab(f).count('\n') + 1 for f in fl)
    return max(0.5, lines * TICK_PT * 1.25 / 72 + 0.12)


def code_ticks(ax, inp, levels, axis, title, show=True):
    """'code:' plus wrapped short label ticks via the shared collusion_colors.set_arm_ticks (>= 9 pt)."""
    if not show:
        (ax.set_yticks if axis == 'y' else ax.set_xticks)(range(len(levels)))
        (ax.set_yticklabels if axis == 'y' else ax.set_xticklabels)([])
        return
    codes = [S.code(inp, v) if inp != 'outcome' else S.outcome_slug(v) for v in levels]
    _, key = CC.set_arm_ticks(ax, codes, axis, fontsize=TICK_PT, grow=False)
    if key:
        KEYED.append((title, axis))



figs = []  # (filename, kind, group, title, caption)
nfig = [0]


def save(fig, name, kind, group, title, cap):
    nfig[0] += 1
    fn = f'F{nfig[0]:02d}_{name}.png'
    if not flush_annotations(fig):
        cap += ' Cell numbers are omitted here because the grid is too dense to print them legibly; colour is kept and the values are in tables/means_1var.csv, means_2var.csv and correlations.csv.'
        DROPPED.append(fn)
    fig.savefig(f'{out}/figures/{fn}', dpi=90, bbox_inches='tight')
    plt.close(fig)
    figs.append(dict(file=fn, kind=kind, group=group, title=title, caption=cap))


def short(g):
    return g.split(' ', 1)[1]


def unv_note(fl):
    u = [f for f in fl if UNV(f)]
    return ' UNVALIDATED (keyword/regex-based) features are marked UNVAL; the Step 2 pass found the agreement flag does not track behaviour.' if u else ''

# -------- 1-variable maps ---------
tabs1 = []
for g in groups:
    fl = [f for f in feats if meta[f]['group'] == g]
    if not fl:
        continue
    # small inputs in one figure
    ins = S.INPUTS_SMALL
    widths = [len(LEV[c]) for c in ins]
    H = max(2.5, row_h(fl) * len(fl) + 1.2)
    fig = plt.figure(figsize=(sum(widths) * 0.95 + 6.2, H + 2.0), layout='constrained')
    gs = fig.add_gridspec(1, len(ins), width_ratios=widths)
    for k, c in enumerate(ins):
        ax = fig.add_subplot(gs[0, k])
        M, N = grp_stats(fl, c, LEV[c])
        for i, f in enumerate(fl):
            for j, lv in enumerate(LEV[c]):
                tabs1.append((f, c, lv, M[i, j], N[i, j]))
        norm = np.full(M.shape, np.nan)
        for i, f in enumerate(fl):
            m = meta[f]
            norm[i] = np.clip((M[i] - m['lo']) / (m['hi'] - m['lo']), 0, 1)
        ax.imshow(row_rgba(norm, fl), aspect='auto')
        annotate_later(ax, [(i, j, cell_text(M[i, j], int(N[i, j])), txt_color(fl[i], norm[i, j]))
                            for i in range(M.shape[0]) for j in range(M.shape[1])
                            if N[i, j] > 0 and not np.isnan(M[i, j])], M.shape[0], M.shape[1])
        code_ticks(ax, c, LEV[c], 'x', g)
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([rowlab(f) for f in fl] if k == 0 else [], fontsize=TICK_PT)
        ax.set_title(c, fontsize=9); ax.tick_params(length=0)
    legend_bar(fig, fig.axes[:len(ins)], 'colour = mean of the row feature, scaled to the row range [low to high] in the row label')
    fig.suptitle(f'{short(g)}: mean of each derived feature by communication, penalty point, thinking, wording, planned length ({batch} batch)', fontsize=10, y=1.0 + 0.6 / H)
    save(fig, f'1var_small_{g.split()[0]}', '1var', g,
         f'1-variable means, {short(g)}: communication, penalty point, thinking, wording, planned length',
         f'Mean of each {short(g).lower()} feature by five inputs (cell = mean and n games where the feature is defined; grey = no data).' + unv_note(fl))
    for c in ['arm', 'seed']:
        lv = LEV[c]
        wide = max(6, len(lv) * (0.78 if c == 'arm' else 0.62) + 5.5)
        wide = max(wide, len(lv) * 0.62 + 6.5)   # room for the 3-line, 9 pt vertical code ticks
        fig, ax = plt.subplots(figsize=(wide, H + 2.6), layout='constrained')
        M, N = grp_stats(fl, c, lv)
        for i, f in enumerate(fl):
            for j, l in enumerate(lv):
                tabs1.append((f, c, l, M[i, j], N[i, j]))
        norm = np.full(M.shape, np.nan)
        for i, f in enumerate(fl):
            m = meta[f]
            norm[i] = np.clip((M[i] - m['lo']) / (m['hi'] - m['lo']), 0, 1)
        ax.imshow(row_rgba(norm, fl), aspect='auto')
        annotate_later(ax, [(i, j, cell_text(M[i, j], int(N[i, j])), txt_color(fl[i], norm[i, j]))
                            for i in range(M.shape[0]) for j in range(M.shape[1])
                            if N[i, j] > 0 and not np.isnan(M[i, j])], M.shape[0], M.shape[1])
        code_ticks(ax, c, lv, 'x', g)
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([rowlab(f) for f in fl], fontsize=TICK_PT); ax.tick_params(length=0)
        ax.set_title(f'{short(g)}: mean of each derived feature by {c} ({batch} batch)', fontsize=10)
        legend_bar(fig, ax, 'colour = mean of the row feature, scaled to the row range [low to high] in the row label')
        save(fig, f'1var_{c}_{g.split()[0]}', '1var', g, f'1-variable means, {short(g)}: by {c}',
             f'Mean of each {short(g).lower()} feature by {c} (cell = mean and n games; grey = feature undefined for that {c}).' + unv_note(fl))
pd.DataFrame(tabs1, columns=['feature', 'input', 'level', 'mean', 'n']).to_csv(out + '/tables/means_1var.csv', index=False)

# -------- 2-variable maps ---------
PAIRS = S.PAIRS
tabs2 = []
for (a, b, name, per, ncol) in PAIRS:
    for g in groups:
        fl = [f for f in feats if meta[f]['group'] == g]
        for ci in range(0, len(fl), per):
            chunk = fl[ci:ci + per]
            nrow = int(np.ceil(len(chunk) / ncol))
            la, lb = LEV[a], LEV[b]
            if name == 'arm_x_thinking':
                pw, ph = 2.6, 0.50 * len(la) + 1.3
            elif name == 'wording_x_seed':
                pw, ph = 0.55 * len(lb) + 2.4, 4.2   # room for the 9 pt 'seed: wording, length' ticks
            else:
                pw, ph = 0.95 * len(lb) + 1.7, 0.62 * len(la) + 1.1
            fig, axs = plt.subplots(nrow, ncol, figsize=(pw * ncol + (1.5 if name == 'arm_x_thinking' else 0), ph * nrow + 1.0), squeeze=False, layout='constrained')
            for k, f in enumerate(chunk):
                ax = axs[k // ncol, k % ncol]
                M = np.full((len(la), len(lb)), np.nan); N = np.zeros((len(la), len(lb)), int)
                for i, x in enumerate(la):
                    for j, y in enumerate(lb):
                        v = d.loc[(d[a] == x) & (d[b] == y), f].dropna()
                        N[i, j] = len(v)
                        if len(v):
                            M[i, j] = v.mean()
                        tabs2.append((f, a, x, b, y, M[i, j], N[i, j]))
                m = meta[f]
                big = name == 'arm_x_thinking'
                im = draw(ax, M, N, f, lb, la)
                code_ticks(ax, b, lb, 'x', f'{name} {f}')
                code_ticks(ax, a, la, 'y', f'{name} {f}', show=(k % ncol == 0) or not big)
                ax.set_title(f + (' [UNVAL]' if UNV(f) else '') + f'\n[{m["lo"]:.4g} to {m["hi"]:.4g}]', fontsize=7)
                ax.set_xlabel(b, fontsize=6); ax.set_ylabel(a, fontsize=6)
                cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
                cb.set_ticks([0, 1]); cb.set_ticklabels([f'{m["lo"]:.3g}', f'{m["hi"]:.3g}']); cb.ax.tick_params(labelsize=8)
                cb.set_label(CC.cbar_label('mean ' + f, f).replace('red = more collusive / green = more competitive', 'red = more collusive /\ngreen = more competitive'), fontsize=5)
            for k in range(len(chunk), nrow * ncol):
                axs[k // ncol, k % ncol].axis('off')
            fig.suptitle(f'{short(g)} by {a} x {b} ({batch} batch)', fontsize=10)
            part = f'_{ci // per + 1}' if len(fl) > per else ''
            save(fig, f'2var_{name}_{g.split()[0]}{part}', '2var', g, f'2-variable means, {short(g)}: {a} x {b}',
                 f'Mean (and n games) of {", ".join(chunk)} by {a} rows and {b} columns; each panel has its own fixed colour scale shown on its colour bar.' + unv_note(chunk))
pd.DataFrame(tabs2, columns=['feature', 'row_input', 'row_level', 'col_input', 'col_level', 'mean', 'n']).to_csv(out + '/tables/means_2var.csv', index=False)

# -------- correlation maps ---------
d['evidence_ending'] = d['evidence_ending'].astype(float)
ocols = [o for o, _ in S.OUTCOMES]
olabs = [l for _, l in S.OUTCOMES]


def corr_pooled(x, y):
    s = d[[x, y]].dropna()
    if len(s) < 20 or s[x].nunique() < 2 or s[y].nunique() < 2:
        return np.nan, len(s)
    return float(s[x].rank().corr(s[y].rank())), len(s)


def corr_within(x, y):
    s = d[[x, y, 'cell']].dropna()
    if len(s) < 30:
        return np.nan, len(s)
    rx = s.groupby('cell')[x].rank(); ry = s.groupby('cell')[y].rank()
    rx = rx - rx.groupby(s.cell).transform('mean'); ry = ry - ry.groupby(s.cell).transform('mean')
    if rx.std() == 0 or ry.std() == 0:
        return np.nan, len(s)
    return float(np.corrcoef(rx, ry)[0, 1]), len(s)


crow = []
for g in groups:
    fl = [f for f in feats if meta[f]['group'] == g]
    fig, axs = plt.subplots(1, 2, figsize=(2 * (len(ocols) * 0.95 + 0.8) + 8, max(2.5, row_h(fl) * len(fl) + 1.3) + 2.0), layout='constrained')
    for k, (fn, title) in enumerate([(corr_pooled, 'Spearman, all games pooled'), (corr_within, 'Spearman within arm x thinking cell (cell-centred ranks)')]):
        R = np.full((len(fl), len(ocols)), np.nan); N = np.zeros_like(R, int)
        for i, f in enumerate(fl):
            for j, o in enumerate(ocols):
                if f == o or (o == 'competitive_share' and f == 'competitive_share'):
                    continue
                R[i, j], N[i, j] = fn(f, o)
                crow.append((g, f, o, 'pooled' if k == 0 else 'within_cell', R[i, j], N[i, j]))
        ax = axs[k]
        cm = CC.NEUTRAL_DIVERGING.copy(); cm.set_bad('#e6e6e6')
        im_c = ax.imshow(np.ma.masked_invalid(R), cmap=cm, vmin=-1, vmax=1, aspect='auto')
        annotate_later(ax, [(i, j, f'{R[i, j]:.2f}\nn={N[i, j]}', 'white' if abs(R[i, j]) > 0.6 else 'black')
                            for i in range(R.shape[0]) for j in range(R.shape[1]) if not np.isnan(R[i, j])], R.shape[0], R.shape[1])
        code_ticks(ax, 'outcome', ocols, 'x', g)
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([rowlab(f) for f in fl] if k == 0 else [], fontsize=TICK_PT)
        ax.set_title(title, fontsize=8); ax.tick_params(length=0)
    cb = fig.colorbar(im_c, ax=list(axs), fraction=0.025, pad=0.02); cb.ax.tick_params(labelsize=7)
    cb.set_label('Spearman rho (-1 to +1)\nneutral colour: a correlation has no collusion direction', fontsize=7)
    fig.suptitle(f'{short(g)} against the basic outcomes ({batch} batch); colour = Spearman rho on -1 to +1', fontsize=10)
    save(fig, f'corr_{g.split()[0]}', 'corr', g, f'Feature-vs-outcome Spearman, {short(g)}',
         f'Game-level Spearman rho of each {short(g).lower()} feature with seven basic outcomes, pooled (left) and within arm x thinking cells (right); blank = fewer than 20 (pooled) or 30 (within) games or no variation.' + unv_note(fl))
pd.DataFrame(crow, columns=['group', 'feature', 'outcome', 'scope', 'spearman', 'n']).to_csv(out + '/tables/correlations.csv', index=False)

json.dump(dict(figs=figs, meta=meta, dropped=dropped, n_games=int(len(d)), batch=batch), open(out + '/tables/fig_index.json', 'w'), indent=1)
print('annotations dropped on', len(DROPPED), 'figures', DROPPED)
print('numbered-key fallbacks', len(KEYED), KEYED)
print('done', nfig[0], 'figures;', len(feats), 'features; dropped', dropped)
