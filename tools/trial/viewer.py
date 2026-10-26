#!/usr/bin/env python3
"""Static HTML viewer for Track M trial transcripts (C10.5; scope section 14.1). Standard library only, no external assets.

Usage: python -X utf8 tools/trial/viewer.py <trials_root> <out_dir>
Writes <out_dir>/index.html (one row per trial: trial, arm, thinking mode, seed, penalty point, wording, status, collusion level,
refusals, with a link to its transcript) and <out_dir>/trials/<trial_id>.html (the transcript rendered from the trial's
events.jsonl with derive.render_transcript, so it matches transcript.md). The pages use only inline CSS, follow the browser's
light or dark setting (prefers-color-scheme), and work from a file:// folder. All text from the events is HTML-escaped. Rows
come from collect.trial_rows (same measures as trials.csv); a corrupt trial is listed without a link. A page is written per
trial in sorted order, so a rerun gives identical files. A trial with refusals is marked in the index and the refused calls
are highlighted in its transcript.
"""
import hashlib
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402
import derive  # noqa: E402

CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1b1f23;--mute:#5b6570;--line:#d0d7de;--accent:#0b5cad;--warn:#fff4d6;--warnfg:#7a4b00;--quote:#f3f5f7}
@media (prefers-color-scheme:dark){:root{--bg:#14181c;--fg:#e4e8ec;--mute:#9aa5b1;--line:#333b44;--accent:#79b8ff;--warn:#3b3115;--warnfg:#f2cc7a;--quote:#1d2329}}
body{margin:0 auto;max-width:60rem;padding:1rem 16px 3rem;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
a{color:var(--accent)}h1{font-size:1.4rem}h2{font-size:1.2rem;margin-top:2rem;border-bottom:1px solid var(--line)}h3{font-size:1rem;color:var(--mute);margin-bottom:.3rem}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border-bottom:1px solid var(--line);padding:.35rem .5rem;text-align:left}th{color:var(--mute)}
.wrap{overflow-x:auto}.item{margin:.15rem 0}.i1{margin-left:1.5rem;color:var(--mute)}.i2{margin-left:3rem;color:var(--mute)}
.refusal{background:var(--warn);color:var(--warnfg);padding:0 .3rem;border-radius:3px}blockquote{margin:.3rem 0;padding:.3rem .8rem;background:var(--quote);border-left:3px solid var(--line);white-space:pre-wrap}
.num{text-align:right}
"""
PAGE = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>%s</title><style>%s</style></head><body>\n%s\n</body></html>\n")
HEADING = re.compile(r"^(#{1,3}) (.*)$")


FLAG = re.compile(r"(\[[^\]]*(?:REFUSED|refusal)[^\]]*\])")
MODEL_LINE = re.compile(r"^- (?:reasoning|plan|rationale)\b")
CALL_HEAD = re.compile(r"^(.*?\(\d+ words\)(?: \[[^\]]*\])?)(: .*)?$")
QUOTE_LINE = re.compile(r"^- \w+: quote ")


def page_name(trial_id):
    return (re.sub(r"[^A-Za-z0-9._-]", "_", trial_id) or "_") + ".html"


def unique_names(ids):
    """{trial_id: file name}; ids whose sanitised names collide (also ignoring case) get a short hash suffix."""
    names = {i: page_name(i) for i in ids}
    count = {}
    for n in names.values():
        count[n.lower()] = count.get(n.lower(), 0) + 1
    return {i: (n if count[n.lower()] == 1 else n[:-5] + "-" + hashlib.sha1(i.encode("utf-8")).hexdigest()[:6] + ".html") for i, n in names.items()}


def _inline(text):
    """Escape a line; highlight refusal flags only where derive.py writes them, never inside model-authored text."""
    if MODEL_LINE.match(text):
        return html.escape(text)
    m = CALL_HEAD.match(text)
    if m:
        head, rest = m.group(1), m.group(2) or ""
    elif QUOTE_LINE.match(text) or ": " not in text:
        head, rest = text, ""
    else:
        head, rest = "", text                       # a line shape with free text: no highlight
    return FLAG.sub(r'<span class="refusal">\1</span>', html.escape(head)) + html.escape(rest)


def transcript_html(md):
    """Render the transcript markdown subset (headings, numbered and bulleted lines, blockquotes) as HTML."""
    out, quote = [], []

    def flush():
        if quote:
            out.append("<blockquote>%s</blockquote>" % html.escape("\n".join(quote)))
            quote.clear()

    for line in md.splitlines():
        if line.startswith(">"):
            quote.append(line[1:].lstrip(" "))
            continue
        flush()
        if not line.strip():
            continue
        m = HEADING.match(line)
        if m:
            n = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (n, _inline(m.group(2)), n))
            continue
        # derive.py nests reasoning with 3 spaces under "N. " lines and plan/rationale/reasoning with 2 spaces under "- " lines
        depth = min(2, (len(line) - len(line.lstrip(" "))) // 2 if line.lstrip().startswith("-") else (len(line) - len(line.lstrip(" "))) // 3)
        out.append('<div class="item i%d">%s</div>' % (depth, _inline(line.strip())))
    flush()
    return "\n".join(out)


def _cell(x):
    return html.escape("" if x is None else str(x))


def build(root, out_dir):
    """Write the index and the transcript pages; return the list of paths written."""
    out = Path(out_dir)
    (out / "trials").mkdir(parents=True, exist_ok=True)
    if not Path(root).is_dir():
        raise ValueError("%s is not a directory" % root)
    paths, rows = [], []
    found = collect.find_trials(root)
    if not found:
        print("warning: no trial directories (with events.jsonl) under %s" % root, file=sys.stderr)
    fnames = unique_names([t.name for t in found])
    for t in found:
        row = collect.trial_rows(t)[0]
        link = ""
        if row["status"] != "corrupt":
            events = derive.read_events(Path(t) / "events.jsonl")
            name = fnames[row["trial_id"]]
            body = '<p><a href="../index.html">All trials</a></p>\n' + transcript_html(derive.render_transcript(events, "Transcript: " + row["trial_id"]))
            (out / "trials" / name).write_text(PAGE % (html.escape(row["trial_id"]), CSS, body), encoding="utf-8", newline="\n")
            paths.append(out / "trials" / name)
            link = "trials/" + name
        rows.append((row, link))
    head = ["trial", "arm", "mode", "seed", "point", "wording", "status", "collusion level", "refusals"]
    trs = []
    for row, link in rows:
        name = _cell(row["trial_id"])
        first = '<a href="%s">%s</a>' % (html.escape(link, quote=True), name) if link else name
        mode = {"on": "thinking on", "off": "thinking off"}.get(row["thinking"], "")
        ref = '<span class="refusal">%s</span>' % _cell(row.get("refusals", "")) if row.get("refusals", "") not in ("", 0) else _cell(row.get("refusals", ""))
        qd = row.get("question_declines", "")
        if qd not in ("", 0, "0", None):   # U15: question declines are apart from refusals but still shown
            ref += ' <span class="refusal">+%s question</span>' % _cell(qd)
        cells = [first, _cell(row["arm"]), mode, _cell(row["seed"]), _cell(row["penalty_point"]), _cell(row["wording"]),
                 _cell(row["status"]), _cell(row.get("collusion_level", "")), ref]
        trs.append("<tr>%s</tr>" % "".join("<td%s>%s</td>" % (' class="num"' if i in (3, 4, 7, 8) else "", c) for i, c in enumerate(cells)))
    body = ("<h1>Trial transcripts</h1><p>%d trials. Collusion level: 0 = competitive price, 1 = collusive price. "
            "Highlighted refusals are counted, not dropped.</p><div class=\"wrap\"><table><thead><tr>%s</tr></thead><tbody>\n%s\n</tbody></table></div>"
            % (len(rows), "".join("<th>%s</th>" % h for h in head), "\n".join(trs)))
    (out / "index.html").write_text(PAGE % ("Trial transcripts", CSS, body), encoding="utf-8", newline="\n")
    return [out / "index.html"] + paths


def main(argv):
    if len(argv) != 3:
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    try:
        paths = build(argv[1], argv[2])
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print("%s (%d transcript pages)" % (paths[0], len(paths) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
