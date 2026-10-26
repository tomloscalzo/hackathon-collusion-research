"""Build ANALYSIS.md from ANALYSIS_template.md and the snippets printed by pg_tables.py."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
out = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "pg_tables.py")], capture_output=True,
                     text=True, encoding="utf-8", check=True).stdout
parts = re.split(r"<!-- (\w+) -->\n", out)
snip = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
t = open(os.path.join(HERE, "ANALYSIS_template.md"), encoding="utf-8").read()
for k, v in snip.items():
    t = t.replace("{{" + k + "}}", v)
assert "{{" not in t, re.findall(r"\{\{\w+\}\}", t)
open(os.path.join(HERE, "ANALYSIS.md"), "w", encoding="utf-8").write(t)
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(os.path.join(HERE, "ANALYSIS.md"))
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("ANALYSIS.md written", len(t))
