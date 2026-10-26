"""usage: mkdoc.py STEP1 OUTDIR BATCH [patterns.md]"""
import sys, json, os
import pandas as pd
import re
from pathlib import Path
import specs as S
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'tools' / 'analysis_style'))
import arm_labels as AL   # legend tables from the shared glossary tools/analysis_style/arm_glossary.csv
import collusion_colors as CC   # the colour direction of each feature row (the same rule plots.py colours by)

step1, out, batch = sys.argv[1:4]
pat = open(sys.argv[4], encoding='utf8').read() if len(sys.argv) > 4 else ''
ix = json.load(open(out + '/tables/fig_index.json'))
dd = S.load_dd(step1)
meta = ix['meta']
LEV = S.levels(pd.read_csv(out + '/tables/derived_game_table.csv', usecols=['arm', 'seed'], low_memory=False))
prim = 'primary' if batch == 'neutral' else 'comparison'


def feature_how(f):
    return S.feature_how(f, dd)


def feature_table(fl):
    """Legend rows for the derived features shown in a figure, from the same definitions as the Definitions table,
    with the colour direction plots.py uses for that row (collusion_colors.direction)."""
    rows = ['| Feature | Meaning (how computed) | Status | Colour direction |', '|---|---|---|---|']
    for f in fl:
        rows.append(f'| `{f}` | {feature_how(f)[0]} | {meta[f]["status"]} | {AL._DIR_TEXT[CC.direction(f)]} |')
    return '\n'.join(rows) + '\n'


ROW_SCALED = ('each row is coloured on its own fixed range (the [low to high] in the row label, the same in every figure): '
              'collusion-direction features run green (low) to red (high), competition-direction features red (low) to green (high), '
              'and features with no collusion direction use blue; grey = no game has the feature defined there.')


def fig_parts(fn):
    """(inputs or outcome columns shown, derived features shown) of a figure, from its file name and specs."""
    s = re.sub(r'^F\d+_', '', fn[:-4])
    kind, rest = s.split('_', 1)
    feats_of = lambda g: [f for f, m in meta.items() if m['group'].split()[0] == g]
    if kind == '1var':
        what, g = rest.rsplit('_', 1)
        return (S.INPUTS_SMALL if what == 'small' else [what]), feats_of(g)
    if kind == 'corr':
        return None, feats_of(rest)
    for a, b, name, per, ncol in S.PAIRS:
        if rest.startswith(name + '_'):
            g, *part = rest[len(name) + 1:].split('_')
            fl = feats_of(g)
            k = int(part[0]) - 1 if part else 0
            return [a, b], fl[k * per:(k + 1) * per]
    raise ValueError(fn)


AGREEMENT_FLAG_NOTE = ("Explicit agreement flag (chat games only; a keyword heuristic, not validated): 1 if at least two firms each sent a chat "
                       "message labelled as an agreement to coordinate prices (a one-sided 'agree' doesn't count), else 0. The labels come from "
                       "analysis_detect.py's keyword rules.")


def agreement_note(fn):
    """Owner's question 'What is explicit_agreement_flag?': the caption of every chart showing the agreement features defines
    them (the flag in the owner-approved wording; explicit_agreement_any / _first_round from the glossary)."""
    fl = fig_parts(fn)[1]
    out = []
    if 'explicit_agreement_flag' in fl:
        out.append(AGREEMENT_FLAG_NOTE)
    g = AL.glossary()
    for f in ('explicit_agreement_any', 'explicit_agreement_first_round'):
        if f in fl:
            out.append(g[f]['long_description'])
    return (' ' + ' '.join(out)) if out else ''


def legend_block(fn):
    """Per-figure legend grouped by axis (arm_labels.axis_legend for the glossary codes, the feature table for the
    derived features), with the colour scale the figure actually uses."""
    ins, fl = fig_parts(fn)
    out = ['<small>', '', '**Legend.** Every code on both axes of this figure. Input codes and outcome names come from the shared '
           'glossary; the derived features from the Definitions table above.', '']
    if ins is None:      # correlation map: rows = features, columns = basic outcomes
        out += ['**Rows (y-axis): derived feature**', '', feature_table(fl)]
        out.append(AL.axis_legend(cols=[S.outcome_slug(o) for o, _ in S.OUTCOMES], col_name='basic outcome (game level)',
                                  panels=None, metric='spearman_rho',
                                  colour='neutral diverging blue (-1) to purple (+1) on a fixed -1 to +1 scale; a correlation has no collusion '
                                         'direction. Left panel: all games pooled; right panel: within arm x thinking cells.'))
    elif len(ins) == 2:  # 2-variable maps: one panel per feature, rows = input a, columns = input b
        a, b = ins
        out.append(AL.axis_legend(rows=[S.code(a, v) for v in LEV[a]], row_name=a.replace('_', ' '),
                                  cols=[S.code(b, v) for v in LEV[b]], col_name=b.replace('_', ' ')))
        out += ['**Panels: derived feature (one per panel; the panel title)**', '', feature_table(fl),
                '**Colour / value (metric)**', '',
                'The mean of the panel\'s feature over the games in the cell (n printed under it). Colour scale: each panel has its own '
                'fixed range, shown on its colour bar (the same range in every figure); collusion-direction features run green (low) '
                'to red (high), competition-direction features red (low) to green (high), no-direction features blue (see the '
                'Colour direction column); grey = no games.', '']
    else:                # 1-variable maps: rows = features, columns = input levels (one panel per input when several)
        out += ['**Rows (y-axis): derived feature**', '', feature_table(fl)]
        name = ', '.join(i.replace('_', ' ') for i in ins)
        out.append(AL.axis_legend(cols=[S.code(i, v) for i in ins for v in LEV[i]],
                                  col_name=name + (' (one panel per input; the panel title names it)' if len(ins) > 1 else '')))
        out += ['**Colour / value (metric)**', '',
                'The mean of the row feature over the games with that input level (n printed under it). Colour scale: ' + ROW_SCALED, '']
    out += ['</small>', '']
    return '\n'.join(out) + '\n'


L = []
w = L.append
w(f'# Step 1.5: heat maps of the derived (engineered) features, Track M {batch} batch\n')
w(f'Created by Claude at the prompting of the repository owner. Complements Step 0.5 (the basic outcomes); the basic outcomes are not re-mapped here, they appear only as the columns of the correlation maps.\n')
w(f'**Data.** {ix["n_games"]} finished games of the {batch} batch ({prim} run): the Step 1 `run.csv` and `run_firms.csv` plus the engineered outputs of the comprehension audit (per firm-round best response, hold, match, dominated and printed-value flags) and of the reading passes (reasoning-passage and introspection classes). All figures are game-level means; the unit of n is a game. Inputs: arm, communication, penalty point, thinking, wording, seed, planned length.\n')
if batch == 'anchored':
    w('**Coverage note.** The comprehension-audit firm-round file covers 1,240 of the 1,360 anchored games (the 120 others are not in that file, mostly placeholder reruns); the Play-quality features (group 4) are blank for them.\n')
w('## How to read\n')
w('- **1-variable maps** (`1var`): rows are derived features, columns are the levels of an input. A cell shows the mean and n (games where the feature is defined). Colour is a fixed scale per feature (the range in brackets after the feature name, the same in every figure): 0 to 1 for shares and flags, 1 to 5 for self-report scores, the 1st to 99th percentile of all games otherwise. Grey = no games have the feature defined there (for example self-report scores exist only in the D-set arms).')
w('- **2-variable maps** (`2var`): one panel per feature; rows and columns are two inputs; same fixed per-feature scale, shown on each colour bar.')
w('- **Correlation maps** (`corr`): Spearman rho at game level between each derived feature (rows) and seven basic outcomes (columns); left = all games pooled, right = within arm x thinking cells (ranks centred in each cell, so differences between arms cannot drive the result). Red positive, blue negative. Several pairs overlap by construction (for example the best-response rate and the matching share); read them as descriptions, not causes.')
w('- **UNVALIDATED.** Features built from keyword or regex rules are marked UNVAL in the figures and listed below as UNVALIDATED. The Step 2 systematic pass found the agreement flag does not track behaviour, so no keyword-based map should be read as evidence of what the firms did or meant. The reasoning-passage classes were checked against two blind readers and found over-inclusive (precision about 0.4 to 0.7).')
w('- A pattern across arms is not an effect of the arm unless the arm is the thing varied: arms differ in design (communication, penalty point, rules), and many features exist only for a few arms.\n')
w('<small>\n\n**Terms**\n')
w('| Term | Meaning |\n|---|---|\n'
  '| half-spread / quote | a firm\'s price choice, from the 1.00 floor to 5.00; 1.00 is the competitive floor, 3.00 the monopoly level |\n'
  '| tick | the smallest quote step, 0.01 |\n'
  '| price index | mean over rounds of (market price - 1) / 2, clamped to 0..1 |\n'
  '| profit gain | (profit - Nash profit) / (monopoly profit - Nash profit) |\n'
  '| competitive share / matching share | share of firm-rounds undercutting / matching the rival\'s lowest previous-round quote |\n'
  '| undercut | a quote below every rival quote of the previous round and below the firm\'s own |\n'
  '| best response | the quote that maximises one-round profit against the rival\'s previous quote |\n'
  '| printed value | one of the example price points printed in the prompt (neutral: 1.00 to 4.00 plus 2.49/2.50; anchored: 1.00, 1.54, 2.08, 2.09, 3.00; 2.09 is the theory\'s collusive level at penalty point 3) |\n'
  '| arm / cell | arm = the design variant; cell = arm, penalty point and thinking mode (20 games) |\n'
  '| communication | tacit (no channel), private chat, monitored, public, unmonitored |\n'
  '| penalty point | 1 to 5, how strongly the expected fine deters collusion (1 = collusion pays) |\n'
  '| thinking | whether the model\'s reasoning mode is on |\n'
  '| wording, seed | one of five paraphrases; the seed fixes the planned horizon and the regulator\'s draws (each seed appears with one wording) |\n'
  '| planned length | the planned horizon in rounds (7, 15, 19, 20); a regulator may end a game earlier |\n'
  '| rival | the other firm (or firms) in the market |\n'
  '| controls | arms ctl-*: strict-compete and joint-profit instructions, used as paired comparison games |\n'
  '| Spearman rho | rank correlation, -1 to +1 |\n'
  '| UNVALIDATED | derived from keyword or regex rules not checked against behaviour |\n\n</small>\n')
w('## External prompt ratings (Claude)\n')
w('Placeholder. Two outcome-blind ratings by Claude of each unique prompt, `claude_conflict` and `claude_temptation` (1 to 5), are being produced separately and will be added to `run.csv` and mapped here in a follow-up pull request. They are not in this version.\n')
if pat:
    w('## Most striking patterns\n')
    w(pat + '\n')
w('## Definitions of the derived features\n')
w('<small>\n\n| Feature | Group | Status | How computed | Source |\n|---|---|---|---|---|')
for f, m in meta.items():
    how, src = feature_how(f)
    w(f'| `{f}` | {m["group"]} | {m["status"]} | {how} | {src} |')
w('\n</small>\n')
if ix['dropped']:
    w('Not mapped (fewer than 20 games with a value, or no variation): ' + ', '.join(f'`{x}`' for x in ix['dropped']) + '.')
    w('`duplicate_market_rounds` is not a column in the Step 1 tables of this batch, so it is not mapped. `concealment_*` equals 1 minus `candour_*` and is not repeated.\n')
w('## Figures\n')
kinds = [('1var', '1-variable heat maps'), ('2var', '2-variable heat maps'), ('corr', 'Feature-vs-outcome correlation maps')]
for k, t in kinds:
    w(f'### {t}\n')
    for f in [x for x in ix['figs'] if x['kind'] == k]:
        w(f'**{f["file"].split("_")[0]}. {f["title"]}.** {f["caption"]}{agreement_note(f["file"])}\n')
        w(f'![{f["title"]}](figures/{f["file"]})\n')
        w(legend_block(f['file']))
w('Tables behind every figure: `tables/means_1var.csv`, `tables/means_2var.csv`, `tables/correlations.csv`, and the game-level table `tables/derived_game_table.csv`. Code: `scripts/`.')
open(out + '/STEP1_5.md', 'w', encoding='utf8').write('\n'.join(L) + '\n')
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(out + '/STEP1_5.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print('ok')
