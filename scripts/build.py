#!/usr/bin/env python3
"""bookforge build: render a book project to draft/book.pdf.

Usage: python3 build.py <book_dir>
Reads  <book_dir>/book.json + outline.json + chapters/*.md
Route  style -> engine (typst | html) from styles/<style>/tokens.json ("engine").
Output <book_dir>/draft/book.pdf   (never writes final/ — that is qc_gate's job)
"""
import json, shutil, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FONTS = SKILL / "assets" / "fonts"

def die(msg: str):
    print(f"BUILD FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

def load(book_dir: Path):
    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    outline = json.loads((book_dir / "outline.json").read_text(encoding="utf-8"))
    style = book.get("style") or die("book.json: style missing")
    style_dir = SKILL / "styles" / style
    if not style_dir.exists():
        die(f"unknown style: {style}")
    tokens = json.loads((style_dir / "tokens.json").read_text(encoding="utf-8"))
    return book, outline, style_dir, tokens

def build_typst(book_dir: Path, book: dict, outline: dict, style_dir: Path):
    sys.path.insert(0, str(SKILL / "scripts"))
    from md2typ import convert_chapter

    ts = book_dir / "typeset"
    style_snap = ts / "_style"
    chap_out = ts / "chapters"
    for d in (style_snap, chap_out, book_dir / "draft"):
        d.mkdir(parents=True, exist_ok=True)

    shutil.copy(SKILL / "templates" / "base.typ", style_snap / "base.typ")
    shutil.copy(style_dir / "theme.typ", style_snap / "theme.typ")
    (style_snap / "meta.json").write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")

    includes = []
    for ch in outline["chapters"]:
        src = book_dir / "chapters" / ch["file"]
        if not src.exists():
            die(f"chapter file missing: {src}")
        dst = chap_out / (src.stem + ".typ")
        convert_chapter(src, dst, ch["title"], ch.get("summary"))
        includes.append(f'#include "chapters/{dst.name}"')

    main = "\n".join([
        '#import "_style/theme.typ": *',
        "#show: book.with(meta: meta, tokens: theme-tokens, cover: make-cover(meta), toc: true)",
        *includes,
        "#colophon(meta, TT)",
    ])
    (ts / "main.typ").write_text(main, encoding="utf-8")

    out = book_dir / "draft" / "book.pdf"
    cmd = ["typst", "compile", "--root", str(book_dir),
           "--font-path", str(FONTS), "--ignore-system-fonts",
           str(ts / "main.typ"), str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die("typst compile:\n" + r.stderr)
    print(f"OK draft: {out}")

def build_html(book_dir: Path, book: dict, outline: dict, style_dir: Path):
    from build_html import build as html_build  # scripts/build_html.py
    html_build(book_dir, book, outline, style_dir, SKILL)

def main():
    book_dir = Path(sys.argv[1]).resolve()
    book, outline, style_dir, tokens = load(book_dir)
    engine = tokens.get("engine", "typst")
    if engine == "typst":
        build_typst(book_dir, book, outline, style_dir)
    elif engine == "html":
        sys.path.insert(0, str(SKILL / "scripts"))
        build_html(book_dir, book, outline, style_dir)
    else:
        die(f"unknown engine: {engine}")

if __name__ == "__main__":
    main()
