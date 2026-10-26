"""Render a Markdown file containing ```mermaid fences to standalone HTML.
Runs md2html_plus.py (path given as the third argument) for the Markdown, then replaces each fenced
mermaid block with a <pre class="mermaid"> element and injects Mermaid from cdnjs (pinned version),
so the diagram renders in the browser while the plain-table fallback in the document stays readable.
Usage: python -X utf8 tools/render_mermaid_html.py in.md out.html path/to/md2html_plus.py
"""
import html, re, subprocess, sys

src, dst, converter = sys.argv[1:4]
subprocess.run([sys.executable, "-X", "utf8", converter, src, dst], check=True)
page = open(dst, encoding="utf-8").read()
md = open(src, encoding="utf-8").read()
blocks = re.findall(r"```mermaid\n(.*?)```", md, flags=re.S)

# the converter emits fenced code as <pre><code ...>escaped text</code></pre>; replace mermaid ones in order
def repl_factory(iterator):
    def repl(m):
        try:
            code = next(iterator)
        except StopIteration:
            return m.group(0)
        return '<pre class="mermaid">' + html.escape(code, quote=False) + "</pre>"
    return repl

it = iter(blocks)
page, n = re.subn(r"<pre><code[^>]*>(?:mermaid\n)?(.*?)</code></pre>",
                  lambda m: repl_factory(it)(m) if "gantt" in html.unescape(m.group(1)) else m.group(0),
                  page, flags=re.S)
script = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"></script>\n'
          '<script>mermaid.initialize({startOnLoad:true, theme: window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default", gantt:{useWidth: 1400, barHeight: 18, fontSize: 12}});</script>\n'
          '<style>.mermaid{overflow-x:auto;background:transparent}pre.mermaid{border:0;padding:0}</style>\n')
page = page.replace("</body>", script + "</body>", 1)
open(dst, "w", encoding="utf-8").write(page)
print(f"rendered {dst}; mermaid blocks replaced: {n} of {len(blocks)}")
