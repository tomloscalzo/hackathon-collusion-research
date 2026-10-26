"""Insert a CI forest chart directly below every delta/CI table of a Markdown report.

    python tools/analysis_style/add_ci_forest.py path/to/ANALYSIS.md [more.md ...] [--dry]

A delta/CI table is a Markdown table with cells like "-0.109 [-0.321, +0.094]" (estimate and 95% CI) that
holds signed differences (a negative value or an explicit "+"). Level tables (all positive) and AUC/accuracy
tables are skipped and listed. The chart is built from the numbers already printed in the table (they come
from the committed CSV), so nothing is recomputed. PNGs go to forest/ next to the report; the inserted block
is wrapped in <!-- ci-forest:N --> ... <!-- /ci-forest --> markers, so re-running replaces it (idempotent).
Generators that write ANALYSIS.md call `process_text(text, md_path)` as their last step.
"""
import os
import re
import sys

try:
    from . import ci_forest as F
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ci_forest as F

BLOCK = re.compile(r"\n?<!-- ci-forest:\d+ -->.*?<!-- /ci-forest -->\n?", re.S)
SKIP_HDR = re.compile(r"\bAUC\b|accuracy|precision|recall", re.I)


def _cells(line):
    s = line.strip().strip("|")
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def _is_sep(line):
    return bool(re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?", line.strip()))


def process_text(text, md_path, dry=False):
    """Returns (new_text, n_charts, skipped) for the Markdown text of md_path."""
    text = BLOCK.sub("", text)
    lines = text.split("\n")
    out, i, n, skipped = [], 0, 0, []
    stem = os.path.splitext(os.path.basename(md_path))[0]
    outdir = os.path.join(os.path.dirname(md_path), "forest")
    heading = ""
    in_code = False
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            in_code = not in_code
        if not in_code and ln.startswith("#"):
            heading = ln.lstrip("# ").strip()
        if not in_code and ln.lstrip().startswith("|") and i + 1 < len(lines) and _is_sep(lines[i + 1]):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            tbl = lines[i:j]
            out.extend(tbl)
            header = _cells(tbl[0])
            recs = F.from_markdown_table(header, [_cells(r) for r in tbl[2:]])
            signed = any(r["estimate"] < 0 or r["lo"] < 0 for r in recs) or any(
                re.search(r"\+\d", c) for r in tbl[2:] for c in _cells(r))
            if recs and SKIP_HDR.search(" ".join(header)):
                skipped.append((i + 1, "AUC/accuracy table"))
            elif recs and not signed:
                skipped.append((i + 1, "level table (no signed differences)"))
            elif recs:
                n += 1
                png = os.path.join(outdir, f"{stem}_ci{n:02d}.png")
                if not dry:
                    os.makedirs(outdir, exist_ok=True)
                    title = f"{heading or stem}: differences with 95% CIs (table at line {i + 1})"
                    F.forest(recs, png, title=title)
                npng = sorted(p for p in os.listdir(outdir) if p.startswith(f"{stem}_ci{n:02d}")) if not dry else [f"{stem}_ci{n:02d}.png"]
                out.append("")
                out.append(f"<!-- ci-forest:{n} -->")
                for p in npng:
                    out.append(f"![CI forest chart for the table above ({heading}): estimates with 95% CI bars, red = collusion-direction move, "
                               f"green = competition-direction move, hollow = CI crosses zero](forest/{p})")
                    out.append("")
                out.append(f"*CI chart for the table above: one panel per metric, one row per contrast; dot = estimate, "
                           f"bar = 95% CI from the table, dashed line = zero, hollow dot = CI crosses zero. "
                           f"Source: the numbers printed in the table (committed CSV); nothing recomputed.*")
                out.append("")
                out.append(F.legend_md(recs).rstrip("\n"))
                out.append("<!-- /ci-forest -->")
            i = j
            continue
        out.append(ln)
        i += 1
    return "\n".join(out), n, skipped


METRIC_NAMES = {"market_price_mean": "Average absolute spread", "price_index": "Price index",
                "profit_gain_index": "Profit gain index", "competitive_share": "Competitive share (U16)",
                "matching_share": "Matching share"}


def csv_records(path):
    """Records from a standard_metrics.csv-style file: columns <metric>_diff, <metric>_lo, <metric>_hi
    (label = the contrast / run / mode columns). Returns [] if the file has no such columns."""
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []
    if "metric" in rows[0] and "diff" in rows[0] and ("ci_lo" in rows[0] or "lo" in rows[0]):      # long format
        labcols = [c for c in rows[0] if c in ("contrast", "comparison", "arm", "cell", "run", "mode", "model",
                                                "label", "opening", "thinking", "contrast")]
        recs = []
        for r in rows:
            lab = " / ".join(f"{c} {r[c]}" if c in ("opening", "thinking") else r[c]
                             for c in labcols if r[c] not in ("", "-")) or "(row)"
            try:
                recs.append(dict(label=lab, metric=r.get("metric_name") or METRIC_NAMES.get(r["metric"], r["metric"]),
                                 estimate=float(r["diff"]), lo=float(r.get("ci_lo") or r["lo"]), hi=float(r.get("ci_hi") or r["hi"]),
                                 p=float(r["p_holm_within_metric"]) if r.get("p_holm_within_metric") else None))
            except ValueError:
                pass
        return recs
    mets = [c[:-5] for c in rows[0] if c.endswith("_diff") and c[:-5] + "_lo" in rows[0] and c[:-5] + "_hi" in rows[0]]
    labcols = [c for c in rows[0] if c in ("contrast", "comparison", "arm", "cell", "run", "mode", "model", "label")]
    recs = []
    for r in rows:
        lab = " / ".join(r[c] for c in labcols if r[c] not in ("", "-")) or "(row)"
        for m in mets:
            try:
                recs.append(dict(label=lab, metric=METRIC_NAMES.get(m, m.replace("_", " ")),
                                 estimate=float(r[m + "_diff"]), lo=float(r[m + "_lo"]), hi=float(r[m + "_hi"]), p=None))
            except ValueError:
                pass
    return recs


def csv_fallback(md_path, text, dry=False):
    """For a report with no parsable delta table but a standard_metrics.csv beside it: append the chart
    built from the committed CSV in a closing section. Returns (text, n)."""
    csvp = os.path.join(os.path.dirname(md_path), "standard_metrics.csv")
    if not os.path.exists(csvp):
        return text, 0
    recs = csv_records(csvp)
    if not recs:
        return text, 0
    outdir = os.path.join(os.path.dirname(md_path), "forest")
    png = os.path.join(outdir, "standard_metrics_ci.png")
    if not dry:
        os.makedirs(outdir, exist_ok=True)
        F.forest(recs, png, title="Standard metrics: differences with 95% CIs (from standard_metrics.csv)")
    names = sorted(p for p in os.listdir(outdir) if p.startswith("standard_metrics_ci")) if not dry else ["standard_metrics_ci.png"]
    blk = ["", "<!-- ci-forest:csv -->", "## CI chart of the standard-metrics differences", "",
           "Built from the committed `standard_metrics.csv` (the contrasts reported above; nothing recomputed)."
           "", ""]
    for nme in names:
        blk += [f"![CI forest chart of the standard-metrics contrasts: estimates with 95% CI bars](forest/{nme})", ""]
    blk += [F.legend_md(recs).rstrip(chr(10)), "<!-- /ci-forest -->", ""]
    return text.rstrip(chr(10)) + chr(10) + chr(10).join(blk), 1


def main(argv):
    dry = "--dry" in argv
    total = 0
    for p in [a for a in argv if not a.startswith("--")]:
        with open(p, encoding="utf-8", newline="") as f:
            raw = f.read()
        crlf = "\r\n" in raw
        new, n, sk = process_text(raw.replace("\r\n", "\n"), p, dry)
        if n == 0 and os.path.basename(p) == "ANALYSIS.md":
            new, n = csv_fallback(p, new, dry)
        if not dry and n:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(new.replace("\n", "\r\n") if crlf else new)
        total += n
        print(f"{p}: {n} charts; skipped {sk}")
    print("TOTAL", total)


if __name__ == "__main__":
    main(sys.argv[1:])
