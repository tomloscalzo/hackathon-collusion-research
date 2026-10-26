"""Post-process an md2html_plus .html twin: render the escaped <small> blocks as small-font .terms divs, and give the h2 headings anchor ids.
usage: html_small.py FILE.html"""
import re, sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
s = s.replace('<p>&lt;small&gt;</p>', '<div class="terms">').replace('<p>&lt;/small&gt;</p>', '</div>')
css = '.terms{font-size:.78rem;line-height:1.35;color:var(--muted);margin:1rem 0 1.5rem}.terms table{font-size:.78rem}.terms td,.terms th{padding:.2rem .4rem}'
if '.terms{' not in s:
    s = s.replace('</style>', css + '</style>', 1)


def slug(t):
    t = re.sub(r'<[^>]+>', '', t).lower()
    t = re.sub(r'[^a-z0-9 -]', '', t)
    return t.strip().replace(' ', '-')


def add_id(m):
    if 'id=' in m.group(1):
        return m.group(0)
    return '<h2 id="%s">%s</h2>' % (slug(m.group(2)), m.group(2))


s = re.sub(r'<h2([^>]*)>(.*?)</h2>', lambda m: add_id(m) if 'id=' not in m.group(1) else m.group(0), s)
open(p, 'w', encoding='utf-8').write(s)
