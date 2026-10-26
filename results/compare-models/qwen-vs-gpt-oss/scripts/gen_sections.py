"""Generate the per-lever comparison tables (lever_sections.md) and the lever counts from lever_table.csv.
usage: python -I -X utf8 gen_sections.py <lever_table.csv> <out_md>"""
import collections
import csv
import re
import sys

src, out = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(src, encoding='utf-8')) if r['topic'] != 'reproducibility']
from lever_defs import DROP, PRIMARY, ORDER, TITLE, ARM, ALIAS  # noqa: E402
KEYS = sorted(ARM, key=len, reverse=True)
PAT = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(k) for k in KEYS) + r')(?![\w-])')


def lab(c):
    return PAT.sub(lambda m: '%s: %s' % (m.group(1), ARM[m.group(1)]), ALIAS.get(c, c))


def ci(d, lo, hi):
    return '%+.3f [%+.3f, %+.3f]' % (float(d), float(lo), float(hi)) if d not in ('', None) else 'not available'


L = []
for t in ORDER:
    rr = [r for r in rows if r['topic'] == t and (t, r['contrast']) not in DROP]
    if not rr:
        continue
    L.append('### %s\n' % TITLE[t])
    L.append('Source: `results/oss/ad-hoc/%s/standard_metrics.csv` (both models). Exploratory unless the topic report says declared; '
             'no family correction in this table.\n' % t)
    L.append('| Contrast (arm minus control) | Role | Metric | Qwen3-32B, thinking on: diff [95% CI], n | gpt-oss-20b, medium: diff [95% CI], n | Replicates? |')
    L.append('|---|---|---|---|---|---|')
    for r in rr:
        q = ci(r['qwen_diff'], r['qwen_lo'], r['qwen_hi']) + ((', %s' % r['qwen_n']) if r['qwen_n'] else '')
        o = ci(r['oss_diff'], r['oss_lo'], r['oss_hi']) + ', %s' % r['oss_n']
        role = 'lever' if (t, r['contrast']) in PRIMARY else 'secondary'
        L.append('| %s | %s | %s | %s | %s | %s |' % (lab(r['contrast']), role, r['metric_label'], q, o, r['replicates']))
    L.append('\n<small>Legend: arm labels read "slug: description"; Role "lever" = the arm against its own control (counted in the verdict), '
             '"secondary" = a within-family or descriptive comparison. Metric and verdict terms are defined in the table after the last lever.</small>\n')
open(out, 'w', encoding='utf-8').write('\n'.join(L))
for metric in ('price_index', 'profit_gain_index'):
    c = collections.Counter(r['replicates'] for r in rows if r['metric'] == metric and (r['topic'], r['contrast']) in PRIMARY)
    print(metric, sum(c.values()), dict(c))
c = collections.Counter(r['metric'] for r in rows if (r['topic'], r['contrast']) in PRIMARY and r['replicates'] == 'no (opposite sign)')
print('opposite-sign lever rows by metric:', dict(c))
