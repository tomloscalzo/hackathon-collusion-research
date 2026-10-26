"""Minimal Markdown -> standalone HTML converter for paper/paper.md.
Supports: # headings, paragraphs, **bold**, *italic*, `code`, bullet lists,
pipe tables, and $$...$$ display math (left for MathJax). Everything else is
passed through as text. Usage: python md2html.py in.md out.html
"""
import html, re, sys

CSS = """
:root { --bg:#ffffff; --fg:#1b1b1b; --muted:#555; --rule:#d8d8d8; --accent:#1f4e79; --code:#f3f3f3; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg:#121417; --fg:#e6e6e6; --muted:#a8a8a8; --rule:#333a42; --accent:#8ab4f8; --code:#1e2227; }
}
:root[data-theme="dark"] { --bg:#121417; --fg:#e6e6e6; --muted:#a8a8a8; --rule:#333a42; --accent:#8ab4f8; --code:#1e2227; }
html { background: var(--bg); }
body { background: var(--bg); color: var(--fg); font: 17px/1.55 Georgia, 'Times New Roman', serif;
       max-width: 46rem; margin: 0 auto; padding: 2rem 16px 4rem; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 1rem; color: var(--accent); }
h2 { font-size: 1.35rem; margin: 2.2rem 0 .6rem; border-bottom: 1px solid var(--rule); padding-bottom: .2rem; }
h3 { font-size: 1.1rem; margin: 1.6rem 0 .4rem; }
p { margin: .7rem 0; }
code { background: var(--code); padding: .05em .3em; border-radius: 3px; font-size: .92em; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92em; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--rule); padding: .35rem .5rem; text-align: left; vertical-align: top; }
th { background: var(--code); }
ul { padding-left: 1.4rem; }
li { margin: .3rem 0; }
.math { overflow-x: auto; margin: .6rem 0; }
.meta { color: var(--muted); font-size: .95em; }
"""

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w\\])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", s)
    s = s.replace("\\*", "*")
    return s

def convert(md):
    out, i, lines = [], 0, md.splitlines()
    para = []
    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()
    while i < len(lines):
        line = lines[i]
        if line.startswith("$$"):
            flush()
            out.append('<div class="math">' + html.escape(line) + "</div>")
            i += 1; continue
        m = re.match(r"^(#{1,3}) (.*)", line)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1; continue
        if line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            t = ["<table>"]
            for k, r in enumerate(cells):
                tag = "th" if k == 0 else "td"
                t.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in r) + "</tr>")
            t.append("</table>")
            out.append("\n".join(t)); continue
        if line.startswith("* "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("* "):
                items.append(lines[i][2:]); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        if line.strip() == "":
            flush(); i += 1; continue
        para.append(line.strip()); i += 1
    flush()
    return "\n".join(out)

src = open(sys.argv[1], encoding="utf-8").read()
body = convert(src)
title = re.search(r"^# (.*)", src, re.M).group(1)
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
<script>
window.MathJax = {{ tex: {{ displayMath: [['$$','$$']], inlineMath: [] }} }};
</script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-chtml.js"></script>
</head>
<body>
{body}
<p class="meta">Equations are written in LaTeX inside $$ markers and rendered by MathJax when a network is available; each is followed by a plain-text form so the page reads without it.</p>
</body>
</html>
"""
open(sys.argv[2], "w", encoding="utf-8").write(page)
print("wrote", sys.argv[2], len(page), "bytes")
