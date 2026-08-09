#!/usr/bin/env python3
"""bookforge HTML engine: md -> themed HTML -> Chromium print (2-pass TOC).

Theme contract (styles/<style>/):
  theme.css   — full print stylesheet (@page, tokens via :root, component classes)
  theme.html  — python str.Template page skeleton with $title $subtitle $author
                $date $brand $toc $body $fonts_dir placeholders
Chapter markers: each chapter opener embeds an invisible ⟦chNN⟧ marker; pass 1
extracts real page numbers with PyMuPDF, injects them into .tocpg spans, pass 2
prints the final PDF.
"""
import json, os, re, subprocess, sys
from pathlib import Path
from string import Template

import fitz
from markdown_it import MarkdownIt

MD = MarkdownIt("commonmark", {"html": True, "typographer": True}) \
    .enable("table").enable("strikethrough")

CALLOUT_RE = re.compile(r"^:::\s*(info|tip|warn|quote|stat)\s*(.*)$")

def md_to_html(md: str) -> str:
    """markdown subset -> html, with ::: callout directive support."""
    out, lines, buf = [], md.split("\n"), []
    def flush():
        if buf:
            out.append(MD.render("\n".join(buf)))
            buf.clear()
    i = 0
    while i < len(lines):
        m = CALLOUT_RE.match(lines[i].strip())
        if m:
            flush()
            kind, title = m.group(1), m.group(2).strip()
            body, i = [], i + 1
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i]); i += 1
            i += 1
            if kind == "stat":
                ls = [l.strip() for l in body if l.strip()]
                value = ls[0] if ls else ""
                label = ls[1] if len(ls) > 1 else ""
                out.append(f'<div class="stat"><span class="stat-value">{value}</span>'
                           f'<span class="stat-label">{label}</span></div>')
            else:
                t = f'<div class="callout-title">{title}</div>' if title else ""
                out.append(f'<div class="callout callout-{kind}">{t}{MD.render(chr(10).join(body))}</div>')
        else:
            buf.append(lines[i]); i += 1
    flush()
    return "\n".join(out)

def build(book_dir: Path, book: dict, outline: dict, style_dir: Path, skill: Path):
    ts = book_dir / "typeset"
    ts.mkdir(exist_ok=True)
    (book_dir / "draft").mkdir(exist_ok=True)

    tokens = json.loads((style_dir / "tokens.json").read_text(encoding="utf-8"))
    key = book.get("brand") or tokens.get("brand_default", "#0E7C7B")
    r_, g_, b_ = (int(key.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    cover_img = book_dir / "assets" / "cover.png"
    if not cover_img.exists():
        cover_img = book_dir / "assets" / "cover.jpg"

    tpl = Template((style_dir / "theme.html").read_text(encoding="utf-8"))
    css = Template((style_dir / "theme.css").read_text(encoding="utf-8")).safe_substitute(
        fonts_dir=(skill / "assets" / "fonts").as_uri(),
        key_color=key,
        key_tint=f"rgba({r_},{g_},{b_},0.08)",
    )

    toc_items, sections = [], []
    for idx, ch in enumerate(outline["chapters"], 1):
        mk = f"ch{idx:02d}"
        src = book_dir / "chapters" / ch["file"]
        raw = src.read_text(encoding="utf-8")
        # strip the leading H1 (title comes from outline)
        raw = re.sub(r"^#\s+.*\n", "", raw, count=1)
        body_html = md_to_html(raw)
        summary = ch.get("summary") or ""
        sections.append(
            f'<section class="chapter" id="{mk}">\n'
            f'<div class="opener"><span class="pgmark">@@{mk}@@</span>'
            f'<div class="opener-num">{idx:02d}</div>'
            f'<h1 class="opener-title">{ch["title"]}</h1>'
            f'<p class="opener-summary">{summary}</p></div>\n'
            f'<div class="chapter-body">{body_html}</div>\n</section>')
        toc_items.append(
            f'<li><span class="toc-title">{ch["title"]}</span>'
            f'<span class="toc-leader"></span>'
            f'<span class="tocpg" data-mk="{mk}">00</span></li>')

    html = tpl.substitute(
        title=book.get("title", ""), subtitle=book.get("subtitle") or "",
        author=book.get("author", "bookforge"), date=book.get("date", ""),
        brand=key,
        cover_art=f"background-image:url('{cover_img.as_uri()}')" if cover_img.exists() else "",
        toc="<ol class=\"toc\">" + "\n".join(toc_items) + "</ol>",
        body="\n".join(sections),
        css=css,
    )
    page1 = ts / "book.html"
    page1.write_text(html, encoding="utf-8")

    env = dict(os.environ)
    env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True,
                                      text=True).stdout.strip()
    printer = skill / "scripts" / "print_pdf.mjs"
    pdf1 = ts / "pass1.pdf"
    r = subprocess.run(["node", str(printer), str(page1), str(pdf1)],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit("HTML pass1 print failed:\n" + r.stderr)

    # pass 1: locate markers
    doc = fitz.open(pdf1)
    pages = {}
    for pno in range(doc.page_count):
        norm = re.sub(r"\s+", "", doc[pno].get_text())
        for m in re.findall(r"@@(ch\d+)@@", norm):
            pages.setdefault(m, pno + 1)
    doc.close()

    # magazine convention: absolute page numbers, cover = page 1
    html2 = html
    for mk, abs_page in pages.items():
        html2 = html2.replace(f'<span class="tocpg" data-mk="{mk}">00</span>',
                              f'<span class="tocpg" data-mk="{mk}">{abs_page}</span>')
    page2 = ts / "book-final.html"
    page2.write_text(html2, encoding="utf-8")

    out = book_dir / "draft" / "book.pdf"
    r = subprocess.run(["node", str(printer), str(page2), str(out)],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit("HTML pass2 print failed:\n" + r.stderr)

    # optional theme post-decoration (running marks, folio) via PyMuPDF
    dec = style_dir / "decorate.py"
    if dec.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("theme_decorate", dec)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = fitz.open(out)
        mod.decorate(doc, {"book": book, "pages": pages,
                           "fonts_dir": skill / "assets" / "fonts"})
        doc.saveIncr()
        doc.close()
    print(f"OK draft: {out} (chapter pages: {pages})")
