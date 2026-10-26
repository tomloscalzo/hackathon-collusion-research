"""Add small-font Terms tables to the Step 3 SUMMARY.md and the Step 1 README.md, reusing the term definitions of add_terms.py.
usage: add_terms_other.py RESULTS_DIR   (the results/trackm-neutral-2026-10-25 folder)"""
import re, sys, os
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, 'add_terms.py'), encoding='utf-8').read().split('SEC = {')[0]
ns = {}
exec(compile(src.split("p = sys.argv[1]")[0], 'terms', 'exec'), ns)
T = ns['T']
R = sys.argv[1]


def table(keys):
    L = ['<small>', '', '**Terms used in this section**', '', '| Term | Plain-language meaning |', '|---|---|']
    L += ['| %s | %s |' % (k, T[k].replace('|', '/')) for k in keys]
    return '\n'.join(L + ['', '</small>', '']) + '\n'


def insert(path, plan, topline):
    s = open(path, encoding='utf-8', newline='').read().replace('\r\n', '\n')
    s = re.sub(r'<small>\n\n\*\*Terms used in this section\*\*.*?</small>\n\n?', '', s, flags=re.S)
    heads = list(re.finditer(r'^## .*$', s, re.M))
    out, last = [], 0
    for i, m in enumerate(heads):
        for prefix, keys in plan.items():
            if m.group(0).startswith(prefix):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(s)
                out.append(s[last:end].rstrip('\n') + '\n\n' + table(keys) + '\n')
                last = end
    out.append(s[last:])
    s = ''.join(out)
    if topline not in s:
        s = s.replace('\n---', '\n' + topline + '\n\n---', 1) if False else re.sub(r'(\n## )', '\n' + topline + '\n\n## ', s, count=1)
    open(path, 'w', encoding='utf-8', newline='\n').write(s)


insert(R + '/step3/SUMMARY.md', {
    '## 1. 60-second': ['profit gain index (pgi)', 'CI, n, pairs', 't0, t1 (thinking off, on)', 'anchored, neutral', 'CoT threat A, B, control (0)', 'say vs do, keyword rule'],
    '## 3. What changed': ['declared, exploratory, post hoc', 'supersession, rerun, truncation'],
    '## 4. Claims ledger': ['Holm, adjusted p, family', 'BH, q-value, m', 'minimum detectable effect (MDE)'],
    '## 5. Headline': ['p1, p3, p4, p5', 'cell, cell check (A1)', 'PASS, CLOSE, FAIL', 'price detector, conversation detector', 'D set', 'channel shift', 'aliasing'],
    '## 8. Threats': ['placeholder-text games', 'R arms (R2f, R3f, R2s, R3s, R4)', '5-tick'],
}, 'Terms and acronyms are explained in a small table after each section and in the [glossary](#12-glossary) at the end.')
insert(R + '/step1/README.md', {
    '## What this is': ['anchored, neutral', 'supersession, rerun, truncation', 'wording, seed', 'planned, done, never started'],
    '## Validation status': ['say vs do, keyword rule', 'price detector, conversation detector', 'Wilson interval'],
}, 'Terms are explained in a small table after each section; see also the [glossary in the Step 3 summary](../step3/SUMMARY.md#12-glossary) and the [Step 2 glossary](../step2/REPORT.md#16-glossary).')
