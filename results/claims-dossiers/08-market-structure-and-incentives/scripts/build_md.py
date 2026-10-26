"""Dossier 08: assemble ANALYSIS.md from tables.json and the prose files in scripts/prose/. Usage: python build_md.py <dossier_dir>
Each prose file may contain {{TABLE:arm|control}} and {{TERMS_CELL}} placeholders."""
import sys, json, re
from pathlib import Path

D = Path(sys.argv[1])
T = json.load(open(D / "tables.json", encoding="utf8"))
P = D / "scripts" / "prose"
TERMS_CELL = (P / "_terms_cell.md").read_text(encoding="utf8").strip()


def fill(text):
    text = text.replace("{{TERMS_CELL}}", TERMS_CELL)
    return re.sub(r"\{\{TABLE:([^}]+)\}\}", lambda m: T[m.group(1)], text)


parts = [fill(f.read_text(encoding="utf8")).strip() for f in sorted(P.glob("[0-9]*.md"))]
(D / "ANALYSIS.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
try:  # re-insert the CI forest charts (tools/analysis_style/report_hooks.py); never fails the generator
    import sys as _sys, pathlib as _pl
    _rt = next(q for q in _pl.Path(__file__).resolve().parents if (q / 'tools' / 'analysis_style' / 'report_hooks.py').exists())
    _sys.path.insert(0, str(_rt / 'tools' / 'analysis_style')); import report_hooks as _rh
    _rh.finalize_report(D / "ANALYSIS.md")
except Exception as _e:
    print('WARNING: CI charts not added:', _e)
print("written", len(parts), "parts")
