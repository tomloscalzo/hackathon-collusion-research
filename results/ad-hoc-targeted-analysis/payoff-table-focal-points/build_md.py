"""Build ANALYSIS.md from the CSVs written by focal_points.py (rerunnable; python -X utf8 build_md.py)."""
import pandas as pd, os, re
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "analysis_style"))
import arm_labels  # shared glossary: every slug in a figure or table gets a legend row


def AXLEG(extra=(), **kw):
    """Figure legend grouped by axis (arm_labels.axis_legend), plus optional extra sections (title, codes)."""
    s = ("**Legend for the figure above, by axis** (generated from the shared glossary "
         "`tools/analysis_style/arm_glossary.csv`)\n\n" + arm_labels.axis_legend(**kw).rstrip("\n") + "\n")
    for title, codes in extra:
        s += "\n**" + title + "**\n\n" + arm_labels.legend_table(codes)
    return s.rstrip("\n") + "\n"


def LEG(slugs, what="table"):
    """Legend table (from tools/analysis_style/arm_glossary.csv) for the slugs a figure or table shows."""
    return ("**Legend for the " + what + " above: every slug and code it shows** (generated from the shared glossary "
            "`tools/analysis_style/arm_glossary.csv`)\n\n" + arm_labels.legend_table(slugs) + "\n")
P = pd.read_csv('quote_shares_pooled.csv'); D = pd.read_csv('paired_neutral_minus_anchored.csv')
S = pd.read_csv('quote_shares_by_cell.csv')
def f(x): return f'{x:.2f}'
def ci(r): return f'{r['diff']:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}]'
L = []
L.append('| arm | mode | neutral: on printed value | neutral: modal quotes | anchored: on printed value | anchored: modal quotes | neutral - anchored price index [95% CI] | neutral - anchored competitive share [95% CI] | neutral - anchored profit gain index [95% CI] |\n|---|---|---|---|---|---|---|---|---|')
for arm in ['headline-tacit', 'headline-chat', 'headline-monitored', 'ALL headline']:
    for m in ['t0', 't1']:
        n = P[(P.run == 'neutral') & (P.arm == arm) & (P['mode'] == m)].iloc[0]; a = P[(P.run == 'anchored') & (P.arm == arm) & (P['mode'] == m)].iloc[0]
        d = D[(D.arm == arm) & (D['mode'] == m) & (D.penalty_point == 'pooled')]
        pi = d[d.metric == 'price_index'].iloc[0]; cs = d[d.metric == 'competitive_share'].iloc[0]; pg = d[d.metric == 'profit_gain_index'].iloc[0]
        L.append(f'| {arm.replace("headline-","")} | {m} | {f(n.share_printed)} | {n.modal_quotes} | {f(a.share_printed)} | {a.modal_quotes} | {ci(pi)} | {ci(cs)} | {ci(pg)} |')
T1 = '\n'.join(L)
L = ['| arm | mode | penalty | neutral printed | anchored printed | neutral modal | anchored modal | neutral - anchored price index [95% CI] |\n|---|---|---|---|---|---|---|---|']
for arm in ['headline-tacit', 'headline-chat', 'headline-monitored']:
    for m in ['t0', 't1']:
        for p in [1, 3, 4, 5]:
            n = S[(S.run == 'neutral') & (S.arm == arm) & (S['mode'] == m) & (S.penalty_point == p)].iloc[0]
            a = S[(S.run == 'anchored') & (S.arm == arm) & (S['mode'] == m) & (S.penalty_point == p)].iloc[0]
            d = D[(D.arm == arm) & (D['mode'] == m) & (D.penalty_point == f'p{p}') & (D.metric == 'price_index')].iloc[0]
            L.append(f'| {arm.replace("headline-","")} | {m} | p{p} | {f(n.share_printed)} | {f(a.share_printed)} | {n.modal_quotes.split(";")[0]} | {a.modal_quotes.split(";")[0]} | {ci(d)} |')
T2 = '\n'.join(L)
if os.path.exists('formula_arms_done_games.csv'):
    X = pd.read_csv('formula_arms_done_games.csv')
    L = ['| arm | mode | DONE games | price index | competitive share | profit gain index | on neutral printed set | on anchored printed set | multiples of 0.05 | at 1.00 | modal quotes |\n|---|---|---|---|---|---|---|---|---|---|---|']
    for _, r in X.iterrows():
        L.append(f'| {r.arm} | {r["mode"]} | {r.n_done_games} | {f(r.price_index)} | {f(r.competitive_share)} | {f(r.profit_gain_index)} | {f(r.share_on_neutral_set)} | {f(r.share_on_anchored_set)} | {f(r.share_round_005)} | {f(r.share_at_1_00)} | {r.modal_quotes} |')
    T3 = '\n'.join(L)
else:
    T3 = 'No DONE games yet.'
def _pg(m):
    r = D[(D.arm == 'ALL headline') & (D['mode'] == m) & (D.penalty_point == 'pooled') & (D.metric == 'profit_gain_index')].iloc[0]
    return f'{r["diff"]:+.2f} [{r.lo:+.2f}, {r.hi:+.2f}]'
tpl = open('analysis_template.md', encoding='utf-8').read()
# {{LEGEND:slug,slug,...|what}} -> glossary legend table (see LEG)
AXLEGS = {'printed_share': AXLEG(cols=['headline-tacit', 'headline-chat', 'headline-monitored', 't0', 't1'], col_name='communication arm and thinking mode (each tick = one arm in one mode)', metric='printed_share', colour='none (a bar chart): bar height = share of quotes on a printed value; bar colour = payoff-table variant (see Series)', extra=[('Series (bar colours): payoff-table variant the prompt printed', ['neutral', 'anchored']), ('Other codes (firms, penalty points pooled)', ['2 firms', 'p1', 'p3', 'p4', 'p5'])])}
tpl = re.sub(r'\{\{AXLEG:(\w+)\}\}', lambda m: AXLEGS[m.group(1)].rstrip('\n'), tpl)
tpl = re.sub(r'\{\{LEGEND:([^|}]+)\|([^}]+)\}\}', lambda m: LEG(m.group(1).split(','), m.group(2)).rstrip('\n'), tpl)
open('ANALYSIS.md', 'w', encoding='utf-8').write(tpl.replace('{{T1}}', T1).replace('{{T2}}', T2).replace('{{T3}}', T3).replace('{{FORMULA_SECTION}}', open('formula_section.md', encoding='utf-8').read() if os.path.exists('formula_section.md') else '').replace('{{PG0}}', _pg('t0')).replace('{{PG1}}', _pg('t1')))
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report('ANALYSIS.md')
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
