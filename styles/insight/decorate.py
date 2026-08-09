"""insight 러닝 장식 스탬핑 — build_html.py가 pass2 후 호출.

decorate(doc, ctx) 계약:
  doc: fitz.Document (draft/book.pdf, in place 수정)
  ctx: {"book": dict, "pages": {"chNN": abs_page}, "fonts_dir": Path}

STYLE.md 러닝 시스템: 시안 바(y 25.5mm, 좌 8mm·우 11mm) · 우측 세로 러닝헤드 ·
폴리오(Barlow Light 11.44pt, 우측 끝 x 170mm, baseline y 243mm).
생략 규칙: 표지(1)·목차(2)는 전부 생략, 도비라는 폴리오만 생략.
"""
import fitz

MM = 72 / 25.4
CYAN = (0x5E / 255, 0xC6 / 255, 0xDC / 255)
MUTE = (0x8A / 255, 0x93 / 255, 0x9B / 255)

def decorate(doc, ctx):
    numfont = str(ctx["fonts_dir"] / "Barlow-Light.ttf")
    hanfont = str(ctx["fonts_dir"] / "Pretendard-Light.otf")
    opener_pages = set(ctx["pages"].values())
    title = ctx["book"].get("title", "")

    for pno in range(doc.page_count):
        page = doc[pno]
        n = pno + 1
        if n <= 2:      # 표지·목차: 전부 생략
            continue
        y = 25.5 * MM
        page.draw_rect(fitz.Rect(0, y, 8 * MM, y + 1 * MM), color=None, fill=CYAN)
        page.draw_rect(fitz.Rect(182 * MM - 11 * MM, y, 182 * MM, y + 1 * MM),
                       color=None, fill=CYAN)
        page.insert_text(
            fitz.Point(177 * MM, 43 * MM), title,
            fontsize=7, fontfile=hanfont, fontname="F-han", rotate=270, color=MUTE)
        # 폴리오는 도비라에도 유지(STYLE 러닝 규약) — 표지·목차만 생략(위에서 continue)
        w = fitz.get_text_length(str(n), fontname="helv", fontsize=11.44)
        page.insert_text(
            fitz.Point(170 * MM - w, 243 * MM), str(n),
            fontsize=11.44, fontfile=numfont, fontname="F-num", color=MUTE)
