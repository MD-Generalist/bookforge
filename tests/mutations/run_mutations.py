#!/usr/bin/env python3
"""G14 뮤테이션 스위트 — 게이트의 감도(놓치지 않는가)를 회귀 자산으로 고정한다.

PASS 상태의 책 PDF에 고의 결함을 주입한 사본을 만들고, tocgate가 각 결함을
실제로 검출하는지 어서션한다. 전부 검출되어야 exit 0.

  M1  목차 쪽번호 변조  — 첫 장의 인쇄 쪽번호를 +7 틀리게 재스탬핑 → G14-A FAIL
  M2  목차 이색(異色)   — 목차 면에 도비라 색 계열과 무관한 마젠타 라벨 주입 → G14-B FAIL
  M3  저대비 텍스트     — 본문 면에 흰 바탕 연회색(#c8c8c8) 캡션 주입 → G14-C FAIL
  M8  절 쪽번호 변조   — 인쇄 목차의 **절 행** 쪽번호를 +5 틀리게 재스탬핑 → G14-D FAIL
                         (실측 사고 재현: 절 마커 오배정으로 절 쪽번호·레벨 2 북마크 10/15가
                          틀린 책이 G4 레벨 2 수 대조와 G14-A를 전부 통과해 출하됐다.
                          이 축만 빌더 산출물을 참조하지 않으므로 그 계열을 유일하게 잡는다)
  M7  전역 축소        — 전 면을 0.8035배로 재배치 → G1-SCALE FAIL
                         (실측 사고 재현: 출하된 insight-ondevice-ai.pdf가 정확히 이 상태였고
                          기존 15개 게이트를 전부 통과했다. 주입본 최빈 7.63pt = 사고본과 동일)
  M9  텍스트 겹침       — 도비라(장 오프너) 면의 **기존 행과 실제로 교차하도록** 좌표를 잡아
                         한 행을 스탬핑 → G3-COLLIDE FAIL
                         (실측 사고 재현: 목차가 넘쳐 도비라 면으로 흐르면서 도비라 제목 위에
                          목차 2행이 겹쳐 인쇄된 산출물이 실재한다 —
                          /mnt/d/bookforge-verify/_judge-fold2-head p3. 주입 좌표는 그 사고와
                          동형이 되도록 도비라 첫 행의 박스 안으로 잡는다)
  M11 앞부속 프레임 이탈 — 목차 면 하단(선언 front_frame_mm 밖)에 한 행을 스탬핑 → G3-FIT FAIL
                         (M10은 G16 저대비 토큰용으로 예약)
  M0  무변조 대조군     — 원본은 G14 전 축 + G1-SCALE + G3-COLLIDE/FIT PASS (오탐 없음 확인)

Usage: python3 tests/mutations/run_mutations.py <book_dir>
       (book_dir는 게이트 PASS 상태의 draft/book.pdf + outline.json 보유)
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from tocgate import (find_toc_pages, g14a_toc_numbers, g14b_key_color, g14c_contrast,
                     g14d_section_numbers, _printed_toc_rows)
from qc_gate import (g1_scale_check, line_records, g3_collide_page, _column_bands,
                     front_frame_for, MM2PT, TOL)


def style_tokens(book_dir):
    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    return book["style"], json.loads(
        (SKILL / "styles" / book["style"] / "tokens.json").read_text(encoding="utf-8"))


def collide_scan(doc, style, tokens):
    """qc_gate와 같은 함수 경로로 면별 원시 교차를 센다(면제 미적용)."""
    out = {}
    for pno in range(doc.page_count):
        page = doc[pno]
        recs = line_records(page.get_text("dict").get("blocks", []),
                            _column_bands(style, tokens.get("body_frame_mm"), page.rect))
        hits = g3_collide_page(recs)
        if hits:
            out[pno + 1] = hits
    return out


def fit_scan(doc, tokens, first_ch):
    """앞부속 프레임 적합 — qc_gate G3-FIT과 같은 판정(양성 조건 + 프레임 축)."""
    decl = tokens.get("front_frame_mm")
    probs = []
    for pg in range(1, first_ch):
        page = doc[pg - 1]
        recs = line_records(page.get_text("dict").get("blocks", []), None)
        if not recs:
            probs.append(f"p{pg}: 텍스트 0행")
            continue
        fr = front_frame_for(decl, pg) if decl else None
        if not fr:
            continue
        top, right, bottom, left = fr
        pr = page.rect
        box = fitz.Rect(left * MM2PT - TOL, top * MM2PT - TOL,
                        pr.width - right * MM2PT + TOL, pr.height - bottom * MM2PT + TOL)
        for r in recs:
            if not box.contains(fitz.Rect(r["raw"])):
                probs.append(f"p{pg}: '{r['text'][:16]}'")
    return probs


def _stamp_font():
    return str(SKILL / "assets" / "fonts" / "Pretendard-Regular.ttf")


def mutate_overlap(doc, ch_starts):
    """도비라(장 오프너) 면에서 **기존 행의 박스 안**에 한 행을 스탬핑해 실제 교차를 만든다.
    행 위/아래에 찍으면 교차가 성립하지 않아 감도 검증 자체가 무의미해지므로, 대상 행의
    세로 중앙에 베이스라인을 놓아 oy가 두 박스의 0.35배를 확실히 넘게 한다."""
    pno = ch_starts[0] - 1
    page = doc[pno]
    recs = line_records(page.get_text("dict").get("blocks", []), None)
    assert recs, "도비라 면에 텍스트 행이 없다 — M9 주입 불가"
    target = max(recs, key=lambda r: (r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
    x0, y0, x1, y1 = target["box"]
    size = 10.0
    page.insert_text(fitz.Point(x0 + 2, (y0 + y1) / 2 + 0.25 * size),
                     "겹침 변조 표본 라인", fontsize=size, fontfile=_stamp_font(),
                     fontname="F-ovl", color=(0, 0, 0))
    return pno + 1, target["text"][:18], [round(v, 1) for v in target["box"]]


def mutate_front_overflow(doc, tokens, first_ch):
    """마지막 목차 면의 선언 front_frame **밖**(하단 6pt 바깥)에 한 행을 스탬핑."""
    decl = tokens.get("front_frame_mm")
    if not decl or first_ch < 3:
        return None
    pg = first_ch - 1
    fr = front_frame_for(decl, pg)
    if not fr:
        return None
    top, right, bottom, left = fr
    page = doc[pg - 1]
    y = page.rect.height - bottom * MM2PT + 6
    page.insert_text(fitz.Point(left * MM2PT + 4, y), "프레임 이탈 변조 표본",
                     fontsize=9, fontfile=_stamp_font(), fontname="F-fit", color=(0, 0, 0))
    return pg, round(y, 1)


def load(book_dir):
    outline = json.loads((book_dir / "outline.json").read_text(encoding="utf-8"))
    titles = [c["title"].strip() for c in outline["chapters"]]
    doc = fitz.open(book_dir / "draft" / "book.pdf")
    ch_starts = sorted({p for l, _, p in doc.get_toc(simple=True) if l == 1})
    return doc, titles, ch_starts


def declared_body_pt(book_dir):
    """book.json의 style → styles/<style>/tokens.json의 body_pt."""
    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    tokens = json.loads((SKILL / "styles" / book["style"] / "tokens.json").read_text(encoding="utf-8"))
    return tokens.get("body_pt")


def mutate_global_shrink(src, dst, k=0.8035):
    """전 면을 k배로 축소 재배치 — Chromium shrink-to-fit 산출물과 동형.
    show_pdf_page는 form XObject 변환으로 싣기 때문에 텍스트 레이어 급수도 k배가 된다
    (실측: 9.49pt 원본 → 7.63pt, 출하 사고본과 동일값)."""
    s = fitz.open(src)
    out = fitz.open()
    for page in s:
        np_ = out.new_page(width=page.rect.width, height=page.rect.height)
        np_.show_pdf_page(fitz.Rect(0, 0, page.rect.width * k, page.rect.height * k),
                          s, page.number)
    out.save(dst)
    out.close()
    s.close()


def mutate_toc_number(doc, titles, ch_starts):
    """첫 장의 목차 인쇄 쪽번호를 지우고 +7 값으로 재스탬핑."""
    toc_pages = find_toc_pages(doc, titles)
    assert toc_pages, "목차 면 미발견 — 뮤테이션 불가"
    page = doc[toc_pages[0]]
    offset = ch_starts[0] - 1
    target = str(ch_starts[0] - offset)  # 첫 장 폴리오(=1)
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip() == target:
                    r = fitz.Rect(s["bbox"])
                    page.add_redact_annot(r, fill=(1, 1, 1))
                    page.apply_redactions()
                    page.insert_text(fitz.Point(r.x0, r.y1 - 1), str(int(target) + 7),
                                     fontsize=s["size"], color=(0, 0, 0))
                    return True
    return False


def mutate_alien_color(doc, titles):
    """목차 면에 마젠타(어느 스타일과도 다른 hue) 텍스트 주입."""
    toc_pages = find_toc_pages(doc, titles)
    page = doc[toc_pages[0]]
    page.insert_text(fitz.Point(60, 60), "MUTANT", fontsize=12, color=(0.9, 0.05, 0.55))
    return True


def mutate_low_contrast(doc, ch_starts):
    """본문 면에 흰 바탕 위 #c8c8c8 8pt 텍스트 주입 (대비 1.6:1)."""
    pno = ch_starts[0]  # 첫 장 시작 다음 면쯤이 무난
    page = doc[min(pno, doc.page_count - 1)]
    page.insert_text(fitz.Point(page.rect.x1 / 2, page.rect.y1 / 2),
                     "저대비 변조 표본", fontsize=8, fontfile=str(
                         SKILL / "assets" / "fonts" / "Pretendard-Regular.ttf"),
                     fontname="F-mut", color=(0.784, 0.784, 0.784))
    return True


def mutate_section_number(doc, titles, ch_starts):
    """인쇄 목차의 첫 **절 행** 쪽번호를 지우고 +5 값으로 재스탬핑.
    장 행이 아니라 절 행을 고른다 — G14-A는 장만 순회하므로 이 변조는 G14-D만 잡는다."""
    toc_pages = find_toc_pages(doc, titles, first_ch=ch_starts[0])
    if not toc_pages:
        return False
    for r in _printed_toc_rows(doc, toc_pages):
        txt = "".join(r["text"].split())
        if any(txt.startswith("".join(t.split())[:10]) for t in titles):
            continue                       # 장 행 — 건너뛴다
        page = doc[r["page"]]
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    if s["text"].strip() == str(r["printed"]) and \
                            abs(s["bbox"][1] - min(x["bbox"][1] for x in l["spans"])) < 1:
                        rect = fitz.Rect(s["bbox"])
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        page.apply_redactions()
                        page.insert_text(fitz.Point(rect.x0, rect.y1 - 1),
                                         str(r["printed"] + 5),
                                         fontsize=s["size"], color=(0, 0, 0))
                        return True
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    book_dir = Path(sys.argv[1]).resolve()
    results = {}

    # M0 대조군 — 원본은 전 축 PASS여야 뮤테이션 판정이 의미 있다
    doc, titles, ch_starts = load(book_dir)
    decl_pt = declared_body_pt(book_dir)
    a0, _ = g14a_toc_numbers(doc, titles, ch_starts)
    b0 = g14b_key_color(doc, titles, ch_starts)
    c0, _ = g14c_contrast(doc)
    s0 = g1_scale_check(doc, decl_pt)[1] if decl_pt else []
    tp0 = find_toc_pages(doc, titles, first_ch=ch_starts[0])
    d0, _w0, d0_pairs = g14d_section_numbers(doc, tp0, titles, ch_starts)
    style, tokens = style_tokens(book_dir)
    col0 = collide_scan(doc, style, tokens)
    fit0 = fit_scan(doc, tokens, ch_starts[0])
    results["M0-clean"] = (not a0 and not b0 and not c0 and not s0 and not d0
                           and not col0 and not fit0)
    if col0:
        print(f"      (M0 G3-COLLIDE 오탐 {sum(len(v) for v in col0.values())}건 {sorted(col0)})")
    if fit0:
        print(f"      (M0 G3-FIT 오탐 {len(fit0)}건 {fit0[:3]})")
    has_sections = bool(d0_pairs)
    doc.close()

    with tempfile.TemporaryDirectory() as td:
        # M1
        work = Path(td) / "m1.pdf"
        shutil.copy(book_dir / "draft" / "book.pdf", work)
        doc = fitz.open(work)
        assert mutate_toc_number(doc, titles, ch_starts), "M1 주입 실패"
        a1, _ = g14a_toc_numbers(doc, titles, ch_starts)
        results["M1-toc-number"] = bool(a1)
        doc.close()

        # M2
        work = Path(td) / "m2.pdf"
        shutil.copy(book_dir / "draft" / "book.pdf", work)
        doc = fitz.open(work)
        mutate_alien_color(doc, titles)
        b2 = g14b_key_color(doc, titles, ch_starts)
        results["M2-alien-color"] = bool(b2)
        doc.close()

        # M3
        work = Path(td) / "m3.pdf"
        shutil.copy(book_dir / "draft" / "book.pdf", work)
        doc = fitz.open(work)
        mutate_low_contrast(doc, ch_starts)
        c3, _ = g14c_contrast(doc)
        results["M3-low-contrast"] = bool(c3)
        doc.close()

        # M8 — toc_levels: 1 스타일(절 행 없음)에서는 성립하지 않으므로 건너뛴다
        if has_sections:
            work = Path(td) / "m8.pdf"
            shutil.copy(book_dir / "draft" / "book.pdf", work)
            doc = fitz.open(work)
            assert mutate_section_number(doc, titles, ch_starts), "M8 주입 실패"
            tp8 = find_toc_pages(doc, titles, first_ch=ch_starts[0])
            d8, _w8, _p8 = g14d_section_numbers(doc, tp8, titles, ch_starts)
            a8, _ = g14a_toc_numbers(doc, titles, ch_starts)
            results["M8-section-number"] = bool(d8)
            print(f"      (M8 G14-D {len(d8)}건 검출 / G14-A는 {len(a8)}건 — 장 축은 못 본다)")
            doc.close()
        else:
            print("      (M8 건너뜀 — toc_levels 1 또는 절 행 없음)")

        # M9 — 도비라 기존 행과 실제로 교차하는 겹침
        work = Path(td) / "m9.pdf"
        shutil.copy(book_dir / "draft" / "book.pdf", work)
        doc = fitz.open(work)
        pg9, victim, vbox = mutate_overlap(doc, ch_starts)
        col9 = collide_scan(doc, style, tokens)
        results["M9-text-overlap"] = pg9 in col9
        print(f"      (M9 도비라 p{pg9} '{victim}' 박스 {vbox} 안에 주입 → "
              f"교차 {len(col9.get(pg9, []))}건)")
        doc.close()

        # M11 — 앞부속 프레임 이탈 (front_frame_mm 미선언 스타일에서는 성립하지 않는다)
        inj = None
        if tokens.get("front_frame_mm") and ch_starts[0] >= 3:
            work = Path(td) / "m11.pdf"
            shutil.copy(book_dir / "draft" / "book.pdf", work)
            doc = fitz.open(work)
            inj = mutate_front_overflow(doc, tokens, ch_starts[0])
            f11 = fit_scan(doc, tokens, ch_starts[0])
            results["M11-front-frame"] = bool(f11)
            print(f"      (M11 p{inj[0]} 프레임 하단 밖 y={inj[1]}pt 주입 → G3-FIT {len(f11)}건)")
            doc.close()
        if inj is None:
            print("      (M11 건너뜀 — front_frame_mm 미선언 또는 앞부속 목차 면 없음)")

        # M7 — body_pt 미선언 스타일 팩에서는 검사 자체가 성립하지 않으므로 건너뛴다
        if decl_pt:
            work = Path(td) / "m7.pdf"
            mutate_global_shrink(book_dir / "draft" / "book.pdf", work)
            doc = fitz.open(work)
            meas7, s7 = g1_scale_check(doc, decl_pt)
            results["M7-global-shrink"] = bool(s7)
            print(f"      (M7 주입본 본문 {meas7}pt vs 선언 {decl_pt}pt)")
            doc.close()
        else:
            print("      (M7 건너뜀 — tokens.json에 body_pt 미선언)")

    ok = all(results.values())
    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    if not ok:
        sys.exit(1)
    print("전 뮤테이션 검출 — G14·G1-SCALE·G3-COLLIDE/FIT 감도 확인")


if __name__ == "__main__":
    main()
