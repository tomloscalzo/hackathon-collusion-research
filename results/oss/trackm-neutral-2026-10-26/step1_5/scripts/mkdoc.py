"""usage: mkdoc.py STEP1 OUTDIR BATCH [patterns.md]"""
import sys, json, os
import pandas as pd
import specs as S

step1, out, batch = sys.argv[1:4]
pat = open(sys.argv[4], encoding='utf8').read() if len(sys.argv) > 4 else ''
ix = json.load(open(out + '/tables/fig_index.json'))
dd = pd.read_csv(step1 + '/data_dictionary.csv')
dd = dd[dd.file == 'run.csv'].set_index('column')
meta = ix['meta']
prim = 'primary' if batch == 'neutral' else 'comparison'
L = []
w = L.append
w('# Step 1.5: heat maps of the derived (engineered) features, gpt-oss-20b replication (neutral run, reasoning effort medium)\n')
PROV = os.environ.get('STEP15_PROVISIONAL', '') == '1'
if PROV:
    w('**PROVISIONAL (partial data).** Built while games were still running; every number will change when the run is complete. Not for citation.\n')
w(f'Created by Claude at the prompting of the repository owner. Complements Step 0.5 (the basic outcomes); the basic outcomes are not re-mapped here, they appear only as the columns of the correlation maps.\n')
w('**Orientation.** Two (in some arms three) language-model firms, called market makers, play a repeated pricing game for 7 to 20 rounds. Each round every firm posts one quote, its half-spread (the distance from the mid-price to its bid and ask), between 1.00 and 5.00 in ticks of 0.01; 1.00 is the competitive floor (no excess profit) and 3.00 the monopoly price; the lowest quote wins most customers (the rival is the other firm). A simulated regulator can investigate and fine; the penalty point (1 light to 5 heavy) sets the expected fine. This is the replication on a second model, **gpt-oss-20b at reasoning effort medium** (the model has no thinking-off mode, so there is no thinking contrast; every cell is the analogue of the Qwen3-32B thinking-on cell). The payoff table is the neutral one (evenly spaced example prices 1.00 to 4.00; the theory level 2.09 is never printed). Controls `ctl-32b-joint` and `ctl-32b-compete` keep their historical names but ran on gpt-oss-20b. Qwen3-32B results are in `results/trackm-neutral-2026-10-25/step1_5/`; cross-model comparisons only in `results/compare-models/qwen-vs-gpt-oss/`.\n')
w('**Build-bug arms left out.** The five planned formula / no-numbers arms of this run (renamed hrep-fx-chat-p1, hrep-fx-tacit-p1, hrep-fx-chat-p5, hrep-nx-chat-p1, hrep-nx-tacit-p1 in run.csv; %d done games) played the neutral headline prompt because a global grid override replaced their payoff block. They are headline-cell replicates (payoff_examples neutral; build bug), not focal-point tests, and are left out of every map; `tables/sensitivity_build_bug_replicates.csv` compares them with their headline cells. The corrected formula / no-numbers games (real names fx-*, nx-*, and the formula joint-profit control fx-ctl-joint; payoff_examples formula or none) appear, when present, as their own arms and as their own level of the payoff-examples input (arm family payoff_block); the focal-point analysis itself is in the ad-hoc focal-points report.\n' % ix.get('n_build_bug', 0))
w(f'**Data.** {ix["n_games"]} finished games of the gpt-oss-20b neutral run: the Step 1 `run.csv` and `run_firms.csv` plus the engineered outputs of the comprehension audit (per firm-round best response, hold, match, dominated and printed-value flags) and of the reading passes (reasoning-passage and introspection classes). All figures are game-level means; the unit of n is a game. Inputs: arm, communication, penalty point, wording, seed, planned length.\n')
if batch == 'anchored':
    w('**Coverage note.** The comprehension-audit firm-round file covers 1,240 of the 1,360 anchored games (the 120 others are not in that file, mostly placeholder reruns); the Play-quality features (group 4) are blank for them.\n')
w('## How to read\n')
w('- **1-variable maps** (`1var`): rows are derived features, columns are the levels of an input. A cell shows the mean and n (games where the feature is defined). Colour is a fixed scale per feature (the range in brackets after the feature name, the same in every figure): 0 to 1 for shares and flags, 1 to 5 for self-report scores, the 1st to 99th percentile of all games otherwise. Grey = no games have the feature defined there (for example self-report scores exist only in the D-set arms).')
w('- **2-variable maps** (`2var`): one panel per feature; rows and columns are two inputs; same fixed per-feature scale, shown on each colour bar.')
w('- **Correlation maps** (`corr`): Spearman rho at game level between each derived feature (rows) and seven basic outcomes (columns); left = all games pooled, right = within arm x penalty point cells (ranks centred in each cell, so differences between arms cannot drive the result). Neutral diverging colours (a correlation has no collusion direction), centred on 0. Several pairs overlap by construction (for example the best-response rate and the matching share); read them as descriptions, not causes.')
w('- **UNVALIDATED.** Features built from keyword or regex rules are marked UNVAL in the figures and listed below as UNVALIDATED. On Qwen3-32B the Step 2 systematic pass found the agreement flag does not track behaviour (not re-checked on gpt-oss), so no keyword-based map should be read as evidence of what the firms did or meant. The reasoning-passage classes were checked against two blind readers on Qwen3-32B text only (over-inclusive, precision about 0.4 to 0.7); they have no validation on gpt-oss text.')
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
  '| printed value | one of the example price points printed in the prompt (neutral table: 1.00 to 4.00 in 0.50 steps plus 2.49/2.50) |\n'
  '| arm / cell | arm = the design variant; cell = arm and penalty point (20 games; one reasoning mode) |\n'
  '| communication | tacit (no channel), private chat, monitored, public, unmonitored |\n'
  '| penalty point | 1 to 5, how strongly the expected fine deters collusion (1 = collusion pays) |\n'
  '| reasoning effort medium | gpt-oss-20b reasons before every reply at effort medium; no thinking-off mode exists, so no t0/t1 contrast |\n'
  '| empty talk read as done | a talk turn whose reply was empty, read by the engine as the firm saying nothing (gpt-oss-only option; per game in `empty_talk_done_count`) |\n'
  '| build-bug arms | the fx-*/nx-* arms of this run, which played the headline prompt; left out of the maps |\n'
  '| red / green | in heat maps of features with a collusion direction, red = more collusive, green = more competitive; blue = no direction |\n'
  '| wording, seed | one of five paraphrases; the seed fixes the planned horizon and the regulator\'s draws (each seed appears with one wording) |\n'
  '| planned length | the planned horizon in rounds (7, 15, 19, 20); a regulator may end a game earlier |\n'
  '| rival | the other firm (or firms) in the market |\n'
  '| controls | arms ctl-32b-joint and ctl-32b-compete (historical names; played by gpt-oss-20b): joint-profit and strict-compete instructions |\n'
  '| Spearman rho | rank correlation, -1 to +1 |\n'
  '| UNVALIDATED | derived from keyword or regex rules not checked against behaviour |\n\n</small>\n')
w('## External prompt ratings (Claude)\n')
w('Filled in by claude_ratings_step1_5.py.\n')
w('## Most striking patterns\n')
w((pat or 'To be written on the complete data.') + '\n')
w('## Definitions of the derived features\n')
w('<small>\n\n| Feature | Group | Status | How computed | Source |\n|---|---|---|---|---|')
for f, m in meta.items():
    if f in S.MANUAL:
        how, src = S.MANUAL[f]
    elif f in dd.index:
        r = dd.loc[f]
        how = str(r.description).replace('|', '/').replace('\n', ' ')
        src = 'run.csv' + (f' ({r.derived_from})' if isinstance(r.derived_from, str) else '') + (' from run_firms/analysis scripts' if False else '')
    else:
        how, src = '', ''
    w(f'| `{f}` | {m["group"]} | {m["status"]} | {how} | {src} |')
w('\n</small>\n')
if ix['dropped']:
    w('Not mapped (fewer than 20 games with a value, or no variation): ' + ', '.join(f'`{x}`' for x in ix['dropped']) + '.')
    w('`duplicate_market_rounds` is not a column in the Step 1 tables of this run, so it is not mapped. `concealment_*` equals 1 minus `candour_*` and is not repeated.\n')
w('## Figures\n')
kinds = [('1var', '1-variable heat maps'), ('2var', '2-variable heat maps'), ('corr', 'Feature-vs-outcome correlation maps')]
for k, t in kinds:
    w(f'### {t}\n')
    for f in [x for x in ix['figs'] if x['kind'] == k]:
        w(f'**{f["file"][:3]}. {f["title"]}.** {f["caption"]}\n')
        w(f'![{f["title"]}](figures/{f["file"]})\n')
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
