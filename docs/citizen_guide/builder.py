"""Shared PDF builder for the module guides (citizen, PHC worker).

A guide is a list of part modules, each with a `build()` returning chapter HTML. Every chapter starts with
`<h1><span class="num">N</span>Title</h1>`; the builder numbers pages, adds the contents list and PDF bookmarks.
"""

import datetime
import html as htmllib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz

from lib import CSS, ROOT

CHROME = next(
    (p for p in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ) if Path(p).exists()),
    None,
)
HEADING = re.compile(r'<section class="chapter" id="(c\d+)"><h1><span class="num">(\d+)</span>([^<]+)</h1>')


def _chapters(parts) -> tuple[list[str], list[tuple[str, str, str]]]:
    marked, entries = [], []
    for part in parts:
        for html in part.build():
            m = HEADING.search(html)
            entries.append((m.group(1), m.group(2), m.group(3)))
            marked.append(html.replace("</h1>", f'<span class="mk">@@{m.group(1)}@@</span></h1>', 1))
    return marked, entries


def _cover(title_html: str, subtitle: str, meta: str, today: str) -> str:
    return f"""
<section class="cover">
  <div class="bar"></div>
  <h1>{title_html}</h1>
  <div class="sub">{subtitle}</div>
  <div class="meta">{meta}<br>
    Generated {today} from the live code. Every <span style="color:#1f4fa8">path:line</span> link opens VS Code at that line.<br>
    Open any line by hand: Ctrl+P, paste the path and line, press Enter.
  </div>
</section>"""


def _toc(entries, pages: dict[str, int]) -> str:
    rows = "".join(
        f'<a href="#{a}"><div class="row"><span class="t"><b>{n}.</b> {t}</span><span class="pg">{pages.get(a, "")}</span></div></a>'
        for a, n, t in entries
    )
    return f'<section class="toc"><h1>Contents</h1>{rows}</section>'


def _render(html_path: Path, pdf_path: Path) -> None:
    profile = tempfile.mkdtemp(prefix="hn-guide-")
    try:
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
             f"--print-to-pdf={pdf_path}", html_path.as_uri()],
            check=True, timeout=240, capture_output=True,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _pages_of(pdf_path: Path, entries) -> dict[str, int]:
    doc = fitz.open(pdf_path)
    found = {}
    for anchor, _, _ in entries:
        for i, page in enumerate(doc):
            if page.search_for(f"@@{anchor}@@"):
                found[anchor] = i + 1
                break
    doc.close()
    return found


def run(*, parts, out: Path, work: Path, title_html: str, subtitle: str, meta: str, footer: str, doc_title: str) -> None:
    if CHROME is None:
        sys.exit("Chrome or Edge is needed to print the PDF.")
    body, entries = _chapters(parts)
    today = datetime.date.today().strftime("%d %B %Y")
    css = CSS.replace("HealthNexus · Citizen module guide", footer) + ".mk { color: #fff; font-size: 1px; position: absolute; }"

    def page(pages: dict[str, int]) -> str:
        return (
            f'<!doctype html><html><head><meta charset="utf-8"><title>{doc_title}</title><style>{css}</style></head><body>'
            f'{_cover(title_html, subtitle, meta, today)}{_toc(entries, pages)}{"".join(body)}</body></html>'
        )

    html, pdf = work / "_guide.html", work / "_pass.pdf"
    html.write_text(page({}), encoding="utf-8")
    _render(html, pdf)
    numbers = _pages_of(pdf, entries)
    html.write_text(page(numbers), encoding="utf-8")
    _render(html, pdf)
    numbers = _pages_of(pdf, entries)

    doc = fitz.open(pdf)
    for pg in doc:
        marks = [r for a, _, _ in entries for r in pg.search_for(f"@@{a}@@")]
        for r in marks:
            pg.add_redact_annot(r)
        if marks:
            pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    doc.set_toc([[1, f"{n}. {htmllib.unescape(t)}", numbers[a]] for a, n, t in entries if a in numbers])
    doc.set_metadata({"title": doc_title, "author": "HealthNexus", "subject": "Full-stack documentation"})
    doc.save(out, garbage=4, deflate=True)
    pages = len(doc)
    doc.close()
    html.unlink(missing_ok=True)
    pdf.unlink(missing_ok=True)
    print(f"Wrote {out} ({pages} pages, {out.stat().st_size // 1024} KB), {len(entries)} chapters")
