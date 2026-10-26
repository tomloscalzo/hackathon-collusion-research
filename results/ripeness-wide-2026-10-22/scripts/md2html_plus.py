"""Markdown -> standalone HTML (headings, paragraphs, bold/italic/code, links, images, bullet and numbered lists, pipe tables,
fenced code, inline HTML such as <u>). Links to .md files are rewritten to .html. Light/dark aware.
Usage: python -X utf8 md2html_plus.py in.md [out.html] | --fragment in.md out.html"""
import html, re, sys

CSS = """
:root{--bg:#fff;--fg:#1b1b1b;--muted:#555;--rule:#d8d8d8;--accent:#1f4e79;--code:#f3f4f6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121417;--fg:#e6e6e6;--muted:#a8a8a8;--rule:#333a42;--accent:#8ab4f8;--code:#1e2227}}
:root[data-theme="dark"]{--bg:#121417;--fg:#e6e6e6;--muted:#a8a8a8;--rule:#333a42;--accent:#8ab4f8;--code:#1e2227}
html{background:var(--bg)}body{background:var(--bg);color:var(--fg);font:15px/1.55 Helvetica,Arial,sans-serif;max-width:60rem;margin:0 auto;padding:1.5rem 16px 4rem}
h1{font-size:1.7rem;line-height:1.25;color:var(--accent);margin:0 0 1rem}h2{font-size:1.3rem;margin:2rem 0 .6rem;border-bottom:1px solid var(--rule);padding-bottom:.2rem}
h3{font-size:1.1rem;margin:1.5rem 0 .4rem}p{margin:.6rem 0}code{background:var(--code);padding:.05em .3em;border-radius:3px;font-size:.92em}
pre{background:var(--code);padding:.8rem;border-radius:4px;overflow-x:auto;font-size:.85em;line-height:1.35}pre code{background:none;padding:0}
table{border-collapse:collapse;margin:1rem 0;font-size:.92em;display:block;overflow-x:auto}th,td{border:1px solid var(--rule);padding:.35rem .5rem;text-align:left;vertical-align:top}
th{background:var(--code)}ul,ol{padding-left:1.5rem}li{margin:.25rem 0}img{max-width:100%}a{color:var(--accent)}
"""


def inline(t):
    codes = []
    t = re.sub(r"`([^`]+)`", lambda m: codes.append(m.group(1)) or f"\x00{len(codes) - 1}\x00", t)
    keep = []
    t = re.sub(r"</?(u|b|i|em|strong|br|sub|sup)\s*/?>", lambda m: keep.append(m.group(0)) or f"\x01{len(keep) - 1}\x01", t)
    t = html.escape(t, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{re.sub(r"[.]md(#|$)", r".html\1", m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\x01(\d+)\x01", lambda m: keep[int(m.group(1))], t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>", t)
    return t


def cells(line):
    line = line.strip().strip("|")
    out, cur, i = [], "", 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            cur += "|"; i += 2; continue
        if line[i] == "|":
            out.append(cur.strip()); cur = ""
        else:
            cur += line[i]
        i += 1
    out.append(cur.strip())
    return out


def convert(md):
    L = md.split("\n"); o = []; i = 0
    while i < len(L):
        ln = L[i]
        if ln.startswith("```"):
            j = i + 1; buf = []
            while j < len(L) and not L[j].startswith("```"):
                buf.append(L[j]); j += 1
            o.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>"); i = j + 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            n = len(m.group(1)); o.append(f"<h{n}>{inline(m.group(2))}</h{n}>"); i += 1; continue
        if ln.strip().startswith("|") and i + 1 < len(L) and re.match(r"^\s*\|?\s*:?-{2,}", L[i + 1]):
            hd = cells(ln); i += 2; rows = []
            while i < len(L) and L[i].strip().startswith("|"):
                rows.append(cells(L[i])); i += 1
            o.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hd) + "</tr>" +
                     "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            stack = []
            while i < len(L) and (re.match(r"^\s*([-*]|\d+\.)\s+", L[i]) or (L[i].startswith("   ") and L[i].strip() and stack)):
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", L[i])
                if not m:
                    o.append(" " + inline(L[i].strip())); i += 1; continue
                ind = len(m.group(1)); tag = "ol" if m.group(2)[0].isdigit() else "ul"
                while stack and stack[-1][0] > ind:
                    o.append(f"</li></{stack.pop()[1]}>")
                if not stack or stack[-1][0] < ind:
                    o.append(f"<{tag}><li>"); stack.append((ind, tag))
                else:
                    o.append("</li><li>")
                o.append(inline(m.group(3))); i += 1
            while stack:
                o.append(f"</li></{stack.pop()[1]}>")
            continue
        if not ln.strip():
            i += 1; continue
        buf = [ln]; i += 1
        while i < len(L) and L[i].strip() and not re.match(r"^(#{1,6}\s|```|\s*([-*]|\d+\.)\s|\s*\|)", L[i]):
            buf.append(L[i]); i += 1
        o.append("<p>" + inline(" ".join(x.strip() for x in buf)) + "</p>")
    return "\n".join(o)


def page(md, title):
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{convert(md)}</body></html>")


if __name__ == "__main__":
    if sys.argv[1] == "--fragment":
        open(sys.argv[3], "w", encoding="utf-8").write(convert(open(sys.argv[2], encoding="utf-8").read()))
    else:
        src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else re.sub(r"\.md$", ".html", src)
        md = open(src, encoding="utf-8").read()
        m = re.search(r"^#\s+(.*)", md, re.M)
        open(dst, "w", encoding="utf-8").write(page(md, re.sub(r"[*`]", "", m.group(1)) if m else src))
        print("wrote", dst)
