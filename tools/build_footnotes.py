"""Build model/MODEL_SPEC_WITH_LOCAL_FOOTNOTES.md and .html from MODEL_SPEC.md and an
annotations JSON. The spec text is copied verbatim; footnote tables are inserted after
the block whose first line starts with the given anchor prefix.

annotations.json: a list of {"after": "<exact prefix of the block's first line, >= 25 chars>",
                             "vars": [["symbol", "meaning"], ...],
                             "terms": [["composite term", "meaning"], ...]}
A "block" is a run of non-blank lines (paragraph, equation line, table, list, heading).
Usage: python build_footnotes.py SOURCE.md annotations.json OUT.md OUT.html ["label"]
SOURCE.md may be a previously generated footnoted file (its tables are stripped first), so OUT.md can equal SOURCE.md.
"""
import html, json, re, sys

spec_path, ann_path, out_md, out_html = sys.argv[1:5]
label = sys.argv[5] if len(sys.argv) > 5 else "model/MODEL_SPEC.md"
spec = open(spec_path, encoding="utf-8").read()
# idempotent: strip a previous generation header and previously inserted footnote tables,
# so a footnoted file can be regenerated in place after editing its text
spec = re.sub(r"\A<!-- Generated from .*?-->\n\n", "", spec, count=1, flags=re.S)
spec = re.sub(r"\n\n<table><tr><th><sub>Symbol / term</sub></th>.*?</table>", "", spec, flags=re.S)
anns = json.load(open(ann_path, encoding="utf-8"))

# split into blocks (keep blank-line separators)
lines = spec.split("\n")
blocks, cur = [], []
for ln in lines:
    if ln.strip() == "":
        if cur:
            blocks.append(cur); cur = []
        blocks.append([ln])
    else:
        cur.append(ln)
if cur:
    blocks.append(cur)

def md_table(a):
    rows = []
    rows.append("<table><tr><th><sub>Symbol / term</sub></th><th><sub>Meaning here</sub></th></tr>")
    for s, m in a.get("vars", []):
        rows.append(f"<tr><td><sub>{html.escape(s)}</sub></td><td><sub>{html.escape(m)}</sub></td></tr>")
    for s, m in a.get("terms", []):
        rows.append(f"<tr><td><sub><em>{html.escape(s)}</em></sub></td><td><sub>{html.escape(m)}</sub></td></tr>")
    rows.append("</table>")
    return "\n".join(rows)

used, out, matched = set(), [], 0
for b in blocks:
    out.extend(b)
    first = b[0]
    for i, a in enumerate(anns):
        if i in used:
            continue
        if first.startswith(a["after"]):
            out.append("")
            out.append(md_table(a))
            used.add(i); matched += 1
            break
missing = [a["after"][:60] for i, a in enumerate(anns) if i not in used]
md = "\n".join(out)
header = (f"<!-- Generated from {label} by tools/build_footnotes.py. The source text is unchanged; "
          "only the small footnote tables are added. Regenerate after editing MODEL_SPEC.md. -->\n\n")
open(out_md, "w", encoding="utf-8").write(header + md)

# ---- HTML: reuse the minimal converter approach (headings, paragraphs, lists, tables, raw HTML tables)
CSS = """
:root { --bg:#ffffff; --fg:#1b1b1b; --muted:#5a5a5a; --rule:#d8d8d8; --accent:#1f4e79; --code:#f3f3f3; --fn:#f7f7f9; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg:#121417; --fg:#e6e6e6; --muted:#9aa3ad; --rule:#333a42; --accent:#8ab4f8; --code:#1e2227; --fn:#181b20; }
}
:root[data-theme="dark"] { --bg:#121417; --fg:#e6e6e6; --muted:#9aa3ad; --rule:#333a42; --accent:#8ab4f8; --code:#1e2227; --fn:#181b20; }
html { background: var(--bg); }
body { background: var(--bg); color: var(--fg); font: 16px/1.55 Georgia, 'Times New Roman', serif; max-width: 52rem; margin: 0 auto; padding: 2rem 16px 4rem; }
h1 { font-size: 1.8rem; line-height: 1.2; color: var(--accent); }
h2 { font-size: 1.35rem; margin: 2.2rem 0 .6rem; border-bottom: 1px solid var(--rule); padding-bottom: .2rem; }
h3 { font-size: 1.1rem; margin: 1.6rem 0 .4rem; }
p { margin: .7rem 0; } code { background: var(--code); padding: .05em .3em; border-radius: 3px; font-size: .92em; }
table { border-collapse: collapse; width: 100%; margin: .8rem 0; font-size: .92em; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--rule); padding: .3rem .5rem; text-align: left; vertical-align: top; }
th { background: var(--code); }
table.fn { font-size: 80%; color: var(--muted); background: var(--fn); margin: .3rem 0 1rem; }
table.fn th, table.fn td { border-color: var(--rule); padding: .2rem .45rem; }
table.fn sub { vertical-align: baseline; font-size: 100%; }
ul { padding-left: 1.4rem; } li { margin: .3rem 0; }
.eq { font-family: 'Cambria Math', Georgia, serif; margin: .5rem 0 .5rem 1.5rem; overflow-x: auto; white-space: pre-wrap; }
"""

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w\\])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", s)
    s = s.replace("\\*", "*").replace("\\|", "|")
    return s

def convert(md):
    out, i, ls = [], 0, md.splitlines()
    para = []
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
    while i < len(ls):
        line = ls[i]
        if line.startswith("<table><tr><th><sub>"):
            flush()
            tbl = []
            while i < len(ls) and not ls[i].startswith("</table>"):
                tbl.append(ls[i]); i += 1
            tbl.append(ls[i]); i += 1
            out.append("\n".join(tbl).replace("<table>", '<table class="fn">', 1))
            continue
        if line.startswith("<!--"):
            i += 1; continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            flush(); lvl = len(m.group(1)); out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        if line.startswith("|"):
            flush(); rows = []
            while i < len(ls) and ls[i].startswith("|"):
                rows.append(ls[i]); i += 1
            cells = [[c.strip() for c in re.split(r"(?<!\\)\|", r.strip().strip("|"))] for r in rows]
            cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            t = ["<table>"]
            for k, r in enumerate(cells):
                tag = "th" if k == 0 else "td"
                t.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in r) + "</tr>")
            t.append("</table>"); out.append("\n".join(t)); continue
        if line.startswith("* "):
            flush(); items = []
            while i < len(ls) and ls[i].startswith("* "):
                items.append(ls[i][2:]); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>"); continue
        if re.match(r"^\d+\. ", line):
            flush(); items = []
            while i < len(ls) and re.match(r"^\d+\. ", ls[i]):
                items.append(re.sub(r"^\d+\. ", "", ls[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>"); continue
        if line.startswith("  ") and line.strip():
            flush(); out.append('<div class="eq">' + inline(line.strip()) + "</div>"); i += 1; continue
        if line.strip() == "---":
            flush(); out.append("<hr>"); i += 1; continue
        if line.strip() == "":
            flush(); i += 1; continue
        para.append(line.strip()); i += 1
    flush()
    return "\n".join(out)

title = re.search(r"^# (.*)", spec, re.M).group(1)
body = convert(md)
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} (annotated)</title>
<style>{CSS}</style>
</head>
<body>
<p><em>Annotated copy of <code>{html.escape(label)}</code>: the text is unchanged; the small muted tables after equations and paragraphs define every symbol and composite term used locally. Equations are plain Unicode text, so no MathJax is needed.</em></p>
{body}
</body>
</html>
"""
open(out_html, "w", encoding="utf-8").write(page)
print(f"matched {matched}/{len(anns)} annotations; missing: {missing}")
