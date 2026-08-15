"""magazine 폴리오 스탬핑 — build_html.py가 pass2 후 호출.

CSS counter(page)는 절대 번호만 찍을 수 있고 Chromium이 counter-reset: page를
무시하므로(실측), "본문 1쪽부터" 폴리오(book-anatomy C9)는 여기서 찍는다.
좌표·서체는 구 CSS @bottom-right 실측 재현: 우측 끝 = 재단폭 − 16mm(우여백선),
baseline = 재단높이 − 48.2pt, Gmarket Sans TTF Bold 9.5pt #111.
생략 면: 표지(1)·목차(2)·장 오프너(page: opener)·판권면(마지막) — 구 CSS의
nofolio/opener 규칙과 동일 집합.
"""
try:  # PyMuPDF 1.24+ 신 모듈명, 구버전은 fitz만 제공
    import pymupdf as fitz
except ImportError:
    import fitz

MM = 72 / 25.4
INK = (0x11 / 255, 0x11 / 255, 0x11 / 255)

def decorate(doc, ctx):
    numfont = str(ctx["fonts_dir"] / "GmarketSansTTFBold.ttf")
    numfont_f = fitz.Font(fontfile=numfont)
    openers = set(ctx["pages"].values())
    offset = min(openers) - 1 if openers else 0
    last = doc.page_count
    for pno in range(doc.page_count):
        n = pno + 1
        if n <= 2 or n in openers or n == last:
            continue
        page = doc[pno]
        folio = n - offset
        w = numfont_f.text_length(str(folio), fontsize=9.5)
        page.insert_text(
            fitz.Point(page.rect.x1 - 16 * MM - w, page.rect.y1 - 48.2), str(folio),
            fontsize=9.5, fontfile=numfont, fontname="F-num", color=INK)
