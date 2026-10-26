"""Post-write hook for report generators.

Every script that writes a Markdown report calls, as its last step after the .md is on disk,

    finalize_report(md_path)

which (re)inserts the CI forest charts under the delta/CI tables (tools/analysis_style/add_ci_forest.py,
idempotent: re-running replaces the previous charts). It never raises: a failure only prints a warning, so a
generator never fails because of the charts. Generators locate this file by walking up from their own path to
the directory that holds tools/analysis_style/report_hooks.py (no hard-coded paths).
"""
import os
import sys


def finalize_report(md_path):
    """Insert/refresh the CI forest charts in the Markdown file md_path. Returns the number of charts (0 on failure)."""
    try:
        md_path = os.fspath(md_path)
        if not os.path.isfile(md_path):
            print(f"WARNING: finalize_report: {md_path} not found; CI charts not added")
            return 0
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import add_ci_forest as A
        with open(md_path, encoding="utf-8", newline="") as f:
            raw = f.read()
        crlf = "\r\n" in raw
        new, n, _skipped = A.process_text(raw.replace("\r\n", "\n"), md_path)
        if n == 0 and os.path.basename(md_path) == "ANALYSIS.md":
            new, n = A.csv_fallback(md_path, new, False)
        if n and new != raw.replace("\r\n", "\n"):
            with open(md_path, "w", encoding="utf-8", newline="") as f:
                f.write(new.replace("\n", "\r\n") if crlf else new)
        print(f"finalize_report: {md_path}: {n} CI chart(s)")
        return n
    except Exception as e:  # never break a generator
        print(f"WARNING: finalize_report skipped for {md_path}: {e!r}")
        return 0
