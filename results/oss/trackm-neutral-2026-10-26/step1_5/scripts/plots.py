"""Step 1.5 heat maps of derived features, gpt-oss-20b adaptation. usage: plots.py STEP1 AUDIT READING BATCH OUTDIR
One model at reasoning effort medium: no thinking facet; within-cell correlations use arm x penalty point cells. The five
build-bug arms (arm_build_bug = 1: planned formula / no-numbers, played the neutral headline prompt) are left out of every map and
compared with their headline cells in tables/sensitivity_build_bug_replicates.csv."""
import sys, os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

import features as F
import specs as S
from pathlib import Path
_up = [p for p in Path(__file__).resolve().parents if (p / 'tools' / 'analysis_style').is_dir()]
sys.path.insert(0, str(_up[0] / 'tools' / 'analysis_style'))
LABEL = 'gpt-oss-20b, reasoning effort medium, neutral run'
import collusion_colors as CC   # shared red = collusion / green = competition convention
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '_common'))
from oss_arm_labels import maybe as ARMLAB, wrap as ARMWRAP   # owner rule: arm labels are 'slug: description'

step1, audit, reading, batch, out = sys.argv[1:6]
os.makedirs(out + '/figures', exist_ok=True)
os.makedirs(out + '/tables', exist_ok=True)
_committed = out + '/tables/derived_game_table.csv'
if os.environ.get('STEP15_USE_COMMITTED_TABLE') == '1' and os.path.exists(_committed):
    d = pd.read_csv(_committed, low_memory=False)   # re-render colours only: reuse the committed numbers exactly
else:
    d = F.build(step1, audit, reading, batch)
if 'model_label' in d.columns and d.model_label.nunique() != 1:
    raise SystemExit('error: more than one model in run.csv')
d.to_csv(out + '/tables/derived_game_table.csv', index=False)
# build-bug arms: headline-cell replicates, kept out of the maps; sensitivity table against the declared headline cell
if 'arm_build_bug' in d.columns:
    _bug = d[d.arm_build_bug.fillna(0).astype(int) == 1]
    _rows = []
    for _arm, _g in _bug.groupby('arm'):
        _cell = _g.headline_replicate_of.iloc[0]
        _ha, _hp = _cell.split('__p')
        _h = d[(d.arm == _ha) & (d.penalty_point == int(_hp)) & (d.arm_build_bug.fillna(0).astype(int) == 0)]
        for _f in ['market_price_mean', 'price_index', 'profit_gain_index', 'competitive_share', 'matching_share', 'undercut_count', 'rounds_played']:   # run.csv columns only (audit and reading joins are by trial id, which the corrected fx/nx games share)
            if _f in d.columns:
                _rows.append(dict(build_bug_arm=_arm, replicate_of=_cell, feature=_f, bug_arm_mean=_g[_f].mean(), bug_arm_n=int(_g[_f].notna().sum()), headline_mean=_h[_f].mean(), headline_n=int(_h[_f].notna().sum())))
    pd.DataFrame(_rows).to_csv(out + '/tables/sensitivity_build_bug_replicates.csv', index=False)
    d = d[d.arm_build_bug.fillna(0).astype(int) == 0].copy()

ARM_ORDER = list(d.arm.drop_duplicates())
LEV = {
    'communication': ['tacit', 'private', 'monitored', 'unmonitored', 'public'],
    'penalty_point': [1, 2, 3, 4, 5],
    'thinking': ['off', 'on'],
    'wording': [0, 1, 2, 3, 4],
    'planned_length': [7, 15, 19, 20],
    'arm': ARM_ORDER,
    'seed': sorted(d.seed.dropna().unique()),
}
LEV['communication'] = [x for x in LEV['communication'] if x in set(d.communication)]   # gpt-oss grid: only the levels that exist
LEV['penalty_point'] = [x for x in LEV['penalty_point'] if x in set(d.penalty_point.astype(int))]
for k in ['penalty_point', 'wording', 'planned_length', 'seed']:
    LEV[k] = [int(x) for x in LEV[k]]
    d[k] = d[k].astype('Int64')
if 'payoff_examples' in d.columns and d.payoff_examples.nunique() > 1:   # corrected formula / no-numbers games: their own input level
    LEV['payoff_examples'] = [x for x in ['neutral', 'formula', 'none'] if x in set(d.payoff_examples)]
    S.INPUTS_SMALL = S.INPUTS_SMALL + ['payoff_examples']
d['cell'] = d.arm + '|p' + d.penalty_point.astype(str)   # gpt-oss: arm x penalty point (one reasoning mode)

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
                 '\nblue rows have no collusion direction', fontsize=9)


def fmt(v):
    if pd.isna(v):
        return ''
    a = abs(v)
    return f'{v:.0f}' if a >= 100 else (f'{v:.1f}' if a >= 10 else f'{v:.2f}')


def cell_text(m, n):
    return '' if n == 0 else f'{fmt(m)}\nn={n}'


def draw(ax, mat, nmat, f, xl, yl, fs=6, show_y=True, rotx=0):
    m = meta[f]
    norm = np.clip((mat - m['lo']) / (m['hi'] - m['lo']), 0, 1)
    im = ax.imshow(np.ma.masked_invalid(norm), cmap=feat_cmap(f), vmin=0, vmax=1, aspect='auto')
    annotate_later(ax, [(i, j, cell_text(mat[i, j], int(nmat[i, j])), txt_color(f, norm[i, j]))
                        for i in range(mat.shape[0]) for j in range(mat.shape[1])
                        if nmat[i, j] > 0 and not np.isnan(mat[i, j])], mat.shape[0], mat.shape[1])
    ax.set_xticks(range(len(xl)))
    ax.set_xticklabels([ARMWRAP(ARMLAB(str(x))) for x in xl], fontsize=max(fs + 1, 9), linespacing=1.0, rotation=rotx, ha='right' if rotx else 'center')
    ax.set_yticks(range(len(yl)))
    ax.set_yticklabels([ARMWRAP(ARMLAB(str(y)), width=30, max_lines=2) for y in yl] if show_y else [], fontsize=max(fs + 1, 9), linespacing=1.0)
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
    return ' UNVALIDATED (keyword/regex-based) features are marked UNVAL; on Qwen3-32B the Step 2 pass found the agreement flag does not track behaviour (not re-checked on gpt-oss).' if u else ''

# -------- 1-variable maps ---------
tabs1 = []
for g in groups:
    fl = [f for f in feats if meta[f]['group'] == g]
    if not fl:
        continue
    # small inputs in one figure
    ins = S.INPUTS_SMALL
    widths = [len(LEV[c]) for c in ins]
    H = max(2.5, 0.5 * len(fl) + 1.2)
    fig = plt.figure(figsize=(sum(widths) * 0.95 + 6.2, H))
    gs = GridSpec(1, len(ins), width_ratios=widths, wspace=0.06)
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
        ax.set_xticks(range(len(LEV[c]))); ax.set_xticklabels([ARMWRAP(ARMLAB(str(x))) for x in LEV[c]], fontsize=9, rotation=90 if c == 'arm' else 0, linespacing=1.0)
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([lab(f) for f in fl] if k == 0 else [], fontsize=9)
        ax.set_title(c, fontsize=9); ax.tick_params(length=0)
    legend_bar(fig, fig.axes[:len(ins)], 'colour = mean of the row feature, scaled to the row range [low to high] in the row label')
    fig.suptitle(f'{short(g)}: mean of each derived feature by communication, penalty point, wording, planned length ({LABEL})', fontsize=10, y=1.0 + 0.6 / H)
    save(fig, f'1var_small_{g.split()[0]}', '1var', g,
         f'1-variable means, {short(g)}: communication, penalty point, wording, planned length',
         f'Mean of each {short(g).lower()} feature by four inputs (cell = mean and n games where the feature is defined; grey = no data).' + unv_note(fl))
    for c in ['arm', 'seed']:
        lv = LEV[c]
        wide = max(6, len(lv) * (0.78 if c == 'arm' else 0.62) + 5.5)
        fig, ax = plt.subplots(figsize=(wide, H + 0.9))
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
        ax.set_xticks(range(len(lv))); ax.set_xticklabels([ARMWRAP(ARMLAB(str(x))) for x in lv], fontsize=9, rotation=90 if c == 'arm' else 0, ha='center', linespacing=1.0)
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([lab(f) for f in fl], fontsize=9); ax.tick_params(length=0)
        ax.set_title(f'{short(g)}: mean of each derived feature by {c} ({LABEL})', fontsize=10)
        legend_bar(fig, ax, 'colour = mean of the row feature, scaled to the row range [low to high] in the row label')
        save(fig, f'1var_{c}_{g.split()[0]}', '1var', g, f'1-variable means, {short(g)}: by {c}',
             f'Mean of each {short(g).lower()} feature by {c} (cell = mean and n games; grey = feature undefined for that {c}).' + unv_note(fl))
pd.DataFrame(tabs1, columns=['feature', 'input', 'level', 'mean', 'n']).to_csv(out + '/tables/means_1var.csv', index=False)

# -------- 2-variable maps ---------
PAIRS = [('communication', 'penalty_point', 'comm_x_penalty', 6, 3),
         ('arm', 'penalty_point', 'arm_x_penalty', 2, 2),   # readable numbers: 2 panels per figure, rows = only the arms where the feature is defined
         ('wording', 'seed', 'wording_x_seed', 4, 2)]   # gpt-oss: the thinking pairs are dropped
tabs2 = []
for (a, b, name, per, ncol) in PAIRS:
    for g in groups:
        fl = [f for f in feats if meta[f]['group'] == g]
        for ci in range(0, len(fl), per):
            chunk = fl[ci:ci + per]
            nrow = int(np.ceil(len(chunk) / ncol))
            la, lb = LEV[a], LEV[b]
            la_of = {f: ([x for x in la if d.loc[d[a] == x, f].notna().any()] or la) if name == 'arm_x_penalty' else la for f in chunk}
            if name == 'arm_x_penalty':
                pw, ph = 0.9 * len(lb) + 3.4, 0.46 * max(len(v) for v in la_of.values()) + 1.6
            elif name == 'wording_x_seed':
                pw, ph = 0.42 * len(lb) + 1.6, 2.4
            else:
                pw, ph = 0.95 * len(lb) + 1.7, 0.62 * len(la) + 1.1
            fig, axs = plt.subplots(nrow, ncol, figsize=(pw * ncol + (2.2 * ncol if a == "arm" else 0), ph * nrow), squeeze=False, constrained_layout=True)
            for k, f in enumerate(chunk):
                ax = axs[k // ncol, k % ncol]
                la = la_of[f]
                M = np.full((len(la), len(lb)), np.nan); N = np.zeros((len(la), len(lb)), int)
                for i, x in enumerate(la):
                    for j, y in enumerate(lb):
                        v = d.loc[(d[a] == x) & (d[b] == y), f].dropna()
                        N[i, j] = len(v)
                        if len(v):
                            M[i, j] = v.mean()
                        tabs2.append((f, a, x, b, y, M[i, j], N[i, j]))
                m = meta[f]
                im = draw(ax, M, N, f, lb, la, show_y=True)
                ax.set_title(f + (' [UNVAL]' if UNV(f) else '') + f'\n[{m["lo"]:.4g} to {m["hi"]:.4g}]', fontsize=9)
                ax.set_xlabel(b, fontsize=9); ax.set_ylabel(a, fontsize=9)
                cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
                cb.set_ticks([0, 1]); cb.set_ticklabels([f'{m["lo"]:.3g}', f'{m["hi"]:.3g}']); cb.ax.tick_params(labelsize=9)
                cb.set_label(CC.cbar_label('mean ' + f, f).replace('red = more collusive / green = more competitive', 'red = more collusive /\ngreen = more competitive'), fontsize=9)
            for k in range(len(chunk), nrow * ncol):
                axs[k // ncol, k % ncol].axis('off')
            fig.suptitle(f'{short(g)} by {a} x {b} ({LABEL})', fontsize=10)
            pass   # constrained_layout handles spacing (owner rule: no overlapping labels)
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
    fig, axs = plt.subplots(1, 2, figsize=(2 * (len(ocols) * 0.95 + 0.8) + 6, max(2.5, 0.42 * len(fl) + 1.3)), gridspec_kw=dict(wspace=0.04))
    for k, (fn, title) in enumerate([(corr_pooled, 'Spearman, all games pooled'), (corr_within, 'Spearman within arm x penalty point cell (cell-centred ranks)')]):
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
        ax.set_xticks(range(len(ocols))); ax.set_xticklabels(olabs, fontsize=9, rotation=40, ha='right')
        ax.set_yticks(range(len(fl))); ax.set_yticklabels([f + ('  UNVAL' if UNV(f) else '') for f in fl] if k == 0 else [], fontsize=9)
        ax.set_title(title, fontsize=9); ax.tick_params(length=0)
    cb = fig.colorbar(im_c, ax=list(axs), fraction=0.025, pad=0.02); cb.ax.tick_params(labelsize=9)
    cb.set_label('Spearman rho (-1 to +1)\nneutral colour: a correlation has no collusion direction', fontsize=9)
    fig.suptitle(f'{short(g)} against the basic outcomes ({LABEL}); colour = Spearman rho on -1 to +1', fontsize=10)
    save(fig, f'corr_{g.split()[0]}', 'corr', g, f'Feature-vs-outcome Spearman, {short(g)}',
         f'Game-level Spearman rho of each {short(g).lower()} feature with seven basic outcomes, pooled (left) and within arm x penalty point cells (right); blank = fewer than 20 (pooled) or 30 (within) games or no variation.' + unv_note(fl))
pd.DataFrame(crow, columns=['group', 'feature', 'outcome', 'scope', 'spearman', 'n']).to_csv(out + '/tables/correlations.csv', index=False)

json.dump(dict(figs=figs, meta=meta, dropped=dropped, n_games=int(len(d)), batch=batch, n_build_bug=int(len(_bug)) if 'arm_build_bug' in pd.read_csv(out + '/tables/derived_game_table.csv', nrows=1).columns else 0), open(out + '/tables/fig_index.json', 'w'), indent=1)
print('annotations dropped on', len(DROPPED), 'figures', DROPPED)
print('done', nfig[0], 'figures;', len(feats), 'features; dropped', dropped)
