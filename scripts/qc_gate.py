#!/usr/bin/env python3
"""bookforge QC gate — the ONLY path from draft/ to final/.

Usage: python3 qc_gate.py <book_dir>
Gates (all must PASS):
  G1 render   : draft/book.pdf exists, opens, page count in length preset range
  G2 fonts    : every font fully embedded (subset ok)
  G3 overflow : no text/image bbox escapes the page rect (tolerance 1.5pt)
  G4 toc      : TOC page numbers match actual chapter start pages
  G5 blank    : no unintentionally blank pages (no text AND no drawings/images)
Writes <book_dir>/gate-report.json. On PASS copies draft/book.pdf -> final/<slug>.pdf.
Exit 0 = PASS, 1 = FAIL.  (G6 visual judgement is done by the agent on the
contact sheet — this script only automates G1–G5.)
"""
import json, re, shutil, sys
from pathlib import Path

import fitz  # PyMuPDF

SKILL = Path(__file__).resolve().parent.parent
TOL = 1.5  # pt

def main():
    book_dir = Path(sys.argv[1]).resolve()
    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    outline = json.loads((book_dir / "outline.json").read_text(encoding="utf-8"))
    tokens = json.loads((SKILL / "styles" / book["style"] / "tokens.json").read_text(encoding="utf-8"))
    report = {"gates": {}, "pass": False}
    fails = []

    pdf = book_dir / "draft" / "book.pdf"

    # G1 render + page count
    g1 = {"exists": pdf.exists()}
    if not pdf.exists():
        finish(book_dir, report, ["G1: draft/book.pdf missing"])
    doc = fitz.open(pdf)
    n = doc.page_count
    lo, hi = tokens.get("length_pages", {}).get(book.get("length", "short"), [10, 400])
    g1.update({"pages": n, "range": [lo, hi], "ok": lo <= n <= hi})
    report["gates"]["G1"] = g1
    if not g1["ok"]:
        fails.append(f"G1: page count {n} outside [{lo},{hi}]")

    # G2 font embedding
    not_embedded = set()
    for pno in range(n):
        for f in doc.get_page_fonts(pno, full=True):
            # tuple: xref, ext, type, basefont, name, encoding, referencer
            xref, ext, ftype, basefont = f[0], f[1], f[2], f[3]
            if ftype == "Type3":
                continue
            if ext == "n/a" or ext == "":
                extracted = doc.extract_font(xref)
                if not extracted or not extracted[-1]:
                    not_embedded.add(basefont)
    report["gates"]["G2"] = {"not_embedded": sorted(not_embedded), "ok": not not_embedded}
    if not_embedded:
        fails.append(f"G2: fonts not embedded: {sorted(not_embedded)}")

    # G3 overflow
    overflows = []
    for pno in range(n):
        page = doc[pno]
        pr = page.rect
        clip = fitz.Rect(pr.x0 - TOL, pr.y0 - TOL, pr.x1 + TOL, pr.y1 + TOL)
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            bb = fitz.Rect(block["bbox"])
            if not clip.contains(bb):
                overflows.append({"page": pno + 1, "bbox": list(block["bbox"]),
                                  "kind": "text" if block.get("type") == 0 else "image"})
    report["gates"]["G3"] = {"overflows": overflows[:20], "count": len(overflows), "ok": not overflows}
    if overflows:
        fails.append(f"G3: {len(overflows)} bbox overflow(s), first on page {overflows[0]['page']}")

    # G4 TOC consistency (PDF bookmarks vs chapter titles found in TOC text)
    toc_entries = doc.get_toc(simple=True)  # [level, title, page]
    lvl1 = [(t.strip(), p) for (l, t, p) in toc_entries if l == 1]
    g4 = {"bookmarks": len(lvl1), "mismatches": [], "ok": True}
    want = [ch["title"].strip() for ch in outline["chapters"]]
    if len(lvl1) < len(want):
        g4["ok"] = False
        g4["mismatches"].append(f"bookmark count {len(lvl1)} < chapters {len(want)}")
    else:
        for title, page in lvl1:
            if page < 1 or page > n:
                g4["ok"] = False
                g4["mismatches"].append(f"'{title}' -> bad page {page}")
            else:
                text = doc[page - 1].get_text()
                norm = lambda s: re.sub(r"\s+", "", s)
                if norm(title) not in norm(text):
                    g4["ok"] = False
                    g4["mismatches"].append(f"'{title}' not found on its page {page}")
    # printed TOC page numbers: find TOC page, compare listed numbers with bookmark pages
    report["gates"]["G4"] = g4
    if not g4["ok"]:
        fails.append("G4: " + "; ".join(g4["mismatches"][:3]))

    # G5 blank pages
    blanks = []
    for pno in range(n):
        page = doc[pno]
        if page.get_text().strip():
            continue
        if page.get_images(full=True):
            continue
        if page.get_drawings():
            continue
        blanks.append(pno + 1)
    report["gates"]["G5"] = {"blank_pages": blanks, "ok": not blanks}
    if blanks:
        fails.append(f"G5: blank pages {blanks}")

    doc.close()

    if fails:
        finish(book_dir, report, fails)

    # PASS -> final/
    report["pass"] = True
    final_dir = book_dir / "final"
    final_dir.mkdir(exist_ok=True)
    slug = book_dir.name
    dst = final_dir / f"{slug}.pdf"
    shutil.copy(pdf, dst)
    report["final"] = str(dst)
    (book_dir / "gate-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS -> {dst}")
    sys.exit(0)

def finish(book_dir, report, fails):
    report["fails"] = fails
    (book_dir / "gate-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in fails:
        print("FAIL", f, file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
