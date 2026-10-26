"""Build ANALYSIS.md from ANALYSIS_template.md, the snippets printed by pe_tables.py, and narrative.md (hand-written blocks)."""
import os, re, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__))
out = subprocess.run([sys.executable, '-X', 'utf8', os.path.join(H, 'pe_tables.py')], capture_output=True, text=True, encoding='utf-8', check=True).stdout
nar = open(os.path.join(H, 'narrative.md'), encoding='utf-8').read()
snip = {}
for src in (out, nar):
    parts = re.split(r'<!-- (\w+) -->\n', src)
    snip.update({parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)})
t = open(os.path.join(H, 'ANALYSIS_template.md'), encoding='utf-8').read()
for k, v in snip.items(): t = t.replace('{{' + k + '}}', v)
assert '{{' not in t, re.findall(r'\{\{\w+\}\}', t)
open(os.path.join(H, 'ANALYSIS.md'), 'w', encoding='utf-8', newline='\n').write(t)
print('ANALYSIS.md written', len(t))