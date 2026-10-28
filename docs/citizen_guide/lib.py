"""Helpers for the citizen-module guide: every file:line is looked up in the live code, so a stale reference
fails the build instead of printing a wrong line number."""

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_files: dict[str, list[str]] = {}


def _lines(path: str) -> list[str]:
    if path not in _files:
        _files[path] = (ROOT / path).read_text(encoding="utf-8").split("\n")
    return _files[path]


def find(path: str, pattern: str, nth: int = 1) -> int:
    seen = 0
    for i, line in enumerate(_lines(path), 1):
        if pattern in line:
            seen += 1
            if seen == nth:
                return i
    raise AssertionError(f"{path}: pattern not found (#{nth}): {pattern!r}")


def uri(path: str, line: int) -> str:
    return f"vscode://file/{(ROOT / path).as_posix()}:{line}"


def ref(path: str, pattern: str, nth: int = 1, text: str | None = None) -> str:
    line = find(path, pattern, nth)
    short = path.replace("backend/app/", "app/").replace("frontend/src/", "src/")
    label = text or f"{short}:{line}"
    return f'<a class="ref" href="{uri(path, line)}">{html.escape(label)}</a>'


def refline(path: str, line: int) -> str:
    short = path.replace("backend/app/", "app/").replace("frontend/src/", "src/")
    return f'<a class="ref" href="{uri(path, line)}">{html.escape(short)}:{line}</a>'


def e(text: str) -> str:
    return html.escape(text)


def md(text: str) -> str:
    """Tiny inline markup: `code` and **bold**."""
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return re.sub(r"(?<![A-Za-z0-9*])\*([^*\n]+)\*(?![A-Za-z0-9*])", r"<i>\1</i>", text)


def chapter(num: str, title: str, anchor: str, lead: str, body: str) -> str:
    return (
        f'<section class="chapter" id="{anchor}"><h1><span class="num">{num}</span>{e(title)}</h1>'
        f'<p class="lead">{md(lead)}</p>{body}</section>'
    )


def h2(text: str) -> str:
    return f"<h2>{e(text)}</h2>"


def p(text: str) -> str:
    return f"<p>{md(text)}</p>"


def bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{md(i)}</li>" for i in items) + "</ul>"


def note(text: str, kind: str = "note") -> str:
    return f'<div class="callout {kind}">{md(text)}</div>'


def files(rows: list[tuple[str, str, str]]) -> str:
    """(path, pattern|'' for line 1, what it is). Linked to the first matching line."""
    out = ['<table class="grid"><thead><tr><th>File</th><th>Role</th></tr></thead><tbody>']
    for path, pattern, what in rows:
        link = ref(path, pattern) if pattern else f'<a class="ref" href="{uri(path, 1)}">{e(path.replace("backend/app/", "app/").replace("frontend/src/", "src/"))}:1</a>'
        out.append(f"<tr><td>{link}</td><td>{md(what)}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def functions(rows: list[tuple[str, str, str, str]]) -> str:
    """(symbol shown, path, pattern, what it does)."""
    out = ['<table class="grid"><thead><tr><th>Function / component</th><th>Where</th><th>What it does</th></tr></thead><tbody>']
    for symbol, path, pattern, what in rows:
        out.append(f"<tr><td><code>{e(symbol)}</code></td><td>{ref(path, pattern)}</td><td>{md(what)}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


LAYER = {
    "Browser": "ui", "API client": "client", "Router": "route", "Guard": "guard", "Service": "service",
    "Database": "db", "Email": "mail", "Background": "bg", "Model": "ml",
}


def flow(steps: list[tuple[str, str, str, str]]) -> str:
    """(layer, what happens, path, pattern): the end-to-end walk, one step per code location."""
    out = ['<table class="flow"><thead><tr><th>#</th><th>Layer</th><th>What happens</th><th>Open in code</th></tr></thead><tbody>']
    for n, (layer, what, path, pattern) in enumerate(steps, 1):
        out.append(
            f'<tr><td class="n">{n}</td><td><span class="chip {LAYER[layer]}">{layer}</span></td>'
            f"<td>{md(what)}</td><td>{ref(path, pattern) if path else ''}</td></tr>"
        )
    out.append("</tbody></table>")
    return "".join(out)


def chain(boxes: list[str]) -> str:
    """A wrapped row of boxes with arrows: the short picture before the detailed table."""
    parts = []
    for i, b in enumerate(boxes):
        parts.append(f'<div class="box">{md(b)}</div>')
        if i < len(boxes) - 1:
            parts.append('<div class="arrow">→</div>')
    return f'<div class="chain">{"".join(parts)}</div>'


def tables(rows: list[tuple[str, str]]) -> str:
    out = ['<table class="grid"><thead><tr><th>Table</th><th>Used for</th></tr></thead><tbody>']
    for name, what in rows:
        out.append(f"<tr><td><code>{e(name)}</code></td><td>{md(what)}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def qa(items: list[tuple[str, str]]) -> str:
    out = ['<div class="qa"><h3>Questions you may be asked</h3>']
    for q, a in items:
        out.append(f'<div class="q"><p class="qq">Q. {md(q)}</p><p class="aa">{md(a)}</p></div>')
    out.append("</div>")
    return "".join(out)


def table(headers: list[str], rows: list[list[str]], cls: str = "grid") -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c if '<' in c else md(c)}</td>" for c in row) + "</tr>" for row in rows)
    body = re.sub(r"`([^`<]+)`", r"<code>\1</code>", body)
    body = re.sub(r"\*\*([^*<]+)\*\*", r"<b>\1</b>", body)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm;
  @bottom-center { content: "HealthNexus · Citizen module guide · page " counter(page); font: 8pt 'Segoe UI', sans-serif; color: #6e6e68; } }
* { box-sizing: border-box; }
body { font: 9.6pt/1.45 'Segoe UI', 'Inter', Arial, sans-serif; color: #1c1c1a; margin: 0; }
code, .ref, pre { font-family: Consolas, 'Cascadia Mono', monospace; }
code { background: #f1ecd6; padding: 0 3px; border-radius: 3px; font-size: 8.8pt; }
a { color: inherit; }
a.ref { color: #1f4fa8; font-size: 8pt; text-decoration: none; border-bottom: 1px dotted #1f4fa8; white-space: nowrap; }
.cover { height: 255mm; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }
.cover h1 { font: 700 32pt/1.1 Georgia, serif; color: #344e34; margin: 0 0 6mm; }
.cover .sub { font-size: 14pt; color: #4a4638; margin-bottom: 14mm; }
.cover .meta { font-size: 10pt; color: #6e6e68; line-height: 1.7; }
.cover .bar { height: 6px; width: 60mm; background: #9ca763; margin-bottom: 10mm; }
.chapter { page-break-before: always; }
h1 { font: 700 20pt/1.15 Georgia, serif; color: #344e34; margin: 0 0 3mm; display: flex; gap: 4mm; align-items: baseline; border-bottom: 2px solid #9ca763; padding-bottom: 2mm; }
h1 .num { color: #9ca763; font-size: 22pt; }
h2 { font: 700 13pt Georgia, serif; color: #344e34; margin: 6mm 0 2mm; break-after: avoid; }
h3 { font: 700 10.5pt 'Segoe UI', sans-serif; color: #344e34; margin: 4mm 0 2mm; break-after: avoid; }
.lead { font-size: 10.5pt; color: #3d3a2e; margin: 2mm 0 4mm; }
p { margin: 1.5mm 0 2.5mm; }
ul { margin: 1mm 0 3mm; padding-left: 5mm; } li { margin: 0.8mm 0; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm; font-size: 8.8pt; }
th { background: #344e34; color: #fff; text-align: left; padding: 1.6mm 2mm; font-weight: 600; }
td { border-bottom: 1px solid #e0d4a8; padding: 1.5mm 2mm; vertical-align: top; }
tr { break-inside: avoid; }
table.flow td.n { width: 6mm; font-weight: 700; color: #344e34; text-align: center; }
.chip { display: inline-block; font-size: 7.5pt; font-weight: 700; padding: 0.4mm 2mm; border-radius: 10px; white-space: nowrap; }
.chip.ui { background: #e0e7f5; color: #1f3d80; } .chip.client { background: #e6e0f3; color: #4a3a8a; }
.chip.route { background: #d9efe6; color: #1d5a45; } .chip.guard { background: #fbe3d6; color: #8a3a14; }
.chip.service { background: #f6ecc0; color: #6b5300; } .chip.db { background: #dfe3e0; color: #2f3a33; }
.chip.mail { background: #f4dce6; color: #86204f; } .chip.bg { background: #e3e3e3; color: #444; } .chip.ml { background: #d8ecf2; color: #135a73; }
.callout { border-left: 4px solid #9ca763; background: #f7f4e4; padding: 2.2mm 3.5mm; margin: 3mm 0; border-radius: 0 4px 4px 0; }
.callout.warn { border-color: #d19a1b; background: #fbf1d8; } .callout.key { border-color: #344e34; background: #eaf0e1; }
.chain { display: flex; flex-wrap: wrap; align-items: center; gap: 1.5mm; margin: 3mm 0 4mm; }
.box { border: 1.4px solid #344e34; background: #f4f7ee; border-radius: 6px; padding: 1.6mm 2.6mm; font-size: 8.4pt; text-align: center; max-width: 42mm; }
.arrow { color: #344e34; font-weight: 700; }
.qa { background: #fbf9ee; border: 1px solid #e0d4a8; border-radius: 6px; padding: 1mm 4mm 2mm; margin-top: 5mm; }
.q { break-inside: avoid; margin-bottom: 2.5mm; } .qq { font-weight: 700; margin-bottom: 0.5mm; color: #344e34; } .aa { margin: 0; }
.toc { page-break-after: always; } .toc h1 { border: 0; } .toc a { text-decoration: none; }
.toc .row { display: flex; align-items: baseline; gap: 2mm; padding: 1mm 0; border-bottom: 1px dotted #c9bd8b; }
.toc .row .t { flex: 1; } .toc .row .pg { color: #6e6e68; font-variant-numeric: tabular-nums; }
.toc .row.sub { padding-left: 8mm; font-size: 9pt; color: #4a4638; }
.fig { margin: 3mm 0; text-align: center; } .fig svg { max-width: 100%; height: auto; }
.small { font-size: 8.4pt; color: #6e6e68; }
pre.tree { background: #f7f4e4; border: 1px solid #e0d4a8; border-radius: 6px; padding: 3mm; font: 8.4pt/1.35 Consolas, monospace; white-space: pre-wrap; margin: 2mm 0 4mm; }
.fig img { max-width: 100%; max-height: 62mm; border: 1px solid #e0d4a8; border-radius: 4px; }
.kpis { display: flex; flex-wrap: wrap; gap: 3mm; margin: 3mm 0 4mm; }
.kpi { flex: 1 1 34mm; border: 1.4px solid #344e34; background: #f4f7ee; border-radius: 8px; padding: 2.4mm 3mm; text-align: center; }
.kpi .v { font: 700 16pt Georgia, serif; color: #344e34; } .kpi .l { font-size: 8pt; color: #4a4638; }
"""


def pre(text: str, cls: str = "tree") -> str:
    """A preformatted block (folder trees, formulas)."""
    return f'<pre class="{cls}">{html.escape(text)}</pre>'


def figure(path: str, caption: str) -> str:
    """An image embedded in the page, so the PDF is self-contained."""
    import base64

    data = base64.b64encode((ROOT / path).read_bytes()).decode()
    return f'<div class="fig"><img src="data:image/png;base64,{data}" alt="{html.escape(caption)}"><div class="small">{md(caption)}</div></div>'


def kpis(items: list[tuple[str, str]]) -> str:
    """A row of big numbers: [(value, label), ...]."""
    cells = "".join(f'<div class="kpi"><div class="v">{html.escape(v)}</div><div class="l">{md(l)}</div></div>' for v, l in items)
    return f'<div class="kpis">{cells}</div>'
