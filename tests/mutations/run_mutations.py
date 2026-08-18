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
  M10 저대비 토큰       — 스타일 팩을 **임시 복사본**에 복제(저장소 styles/ 불변조)한 뒤
                         contrast_contract.entries 중 정적으로 대비 산출 가능한 첫 페어를
                         골라 fg를 bg와 동일 색으로 재기록(ratio=1.0) → g16_tokens.run을
                         그 복사본 대상으로 실행해 G16-CONTRAST FAIL 검출
                         (enforce:true 스타일만 성립 — 현재 insight·magazine)
  M12 palette_roles 훼손 — 임시 스타일 팩 사본의 diagram.palette_roles를 허용값 밖으로
                         바꿔 → G16-SYNC FAIL (HARD를 내는 축인데 감도 자산이 없었다)
  M13 위반 브랜드      — book.json.brand 위치에 고정 동반색과 hue가 어긋나는 색을 넣어
                         → G16-BRAND FAIL (출처가 book.json이라 FAIL 강도)
  M14 pt 위조(린터 배선) — 임시 스타일 팩 사본에서 계약 엔트리의 pt만 theme.css에 없는
                         값으로 위조 → 린터 축② PT_UNATTAINABLE FAIL, 그리고 그 코드가
                         **qc_gate가 fails로 올리는 집합**(LINT_HARD_CODES)에 실재함을
                         함께 어서션한다. pt는 contrast_floor의 입력이라 위조하면 계약이
                         스스로 하한을 4.5 -> 3.0으로 낮춘다(W4 판정 D1-L2)
  M9b 본문 면 겹침·승인 — 본문 면(도비라·앞부속·전면도판 아님)에 ㉠머리카락 교차만 주입
                         → 검출, ㉡같은 면에 OVERLAP_APPROVED → **면제 성립**(collide_exempt
                         분기를 실제로 밟는다), ㉢같은 면에 상한 초과 겹침을 더 주입하고
                         승인 유지 → G11 선행조건 FAIL(면당 일괄 면제의 폭발 반경 상한)
  M9c 면제 차감 불변식  — `collide_exempt_pages`가 도비라·앞부속을 어떤 입력에서도 빼는지
                         (표지가 fullbleed여도) 직접 어서션 — W4 판정 D2의 회귀 고정
  M15 라벨 밴드 상한    — 임시 책 사본에 **합성 authored 도해**를 심는다: 폭·viewBox를 알고
                         있으므로 라벨 pt를 원하는 값으로 정확히 놓을 수 있다. 두 표본을
                         한 쌍으로 돌린다 — ㉠상한 초과분(본문×maxRatio를 크게 넘고 하한은
                         지키는 라벨) → render_diagrams가 **WARN**(exit 0)으로 검출하고
                         metrics.json에 verdict=violation을 남기는가, ㉡대조군(밴드 안)
                         → WARN 0·verdict=ok(오탐 없음). 강도까지 어서션하는 것이 핵심이다:
                         이 축은 **HARD가 아니어야** 정상이다(설계 report/w5-design.md 리스크 1
                         — 0.92 HARD는 코퍼스 68/92를 폭으로 구제 불가 상태로 반려해 릴리스를
                         세운다). rc!=0이면 그 자체가 회귀다.
  M0  무변조 대조군     — 원본은 G14 전 축 + G1-SCALE + G3-COLLIDE/FIT + G16(SYNC/CONTRAST/
                         BRAND 전 축, 원본 스타일 팩) PASS (오탐 없음 확인)

**결번 M4·M5·M6**: 플랜 단계에서 예약했다가 쓰지 않은 번호다(각각 G7 밀도·G8 공기·G9
고립용으로 잡았으나 그 세 축은 실측 코퍼스에 참양성 표본이 이미 있어 합성 주입이
불필요하다고 판단). 빠진 축이 아니라 **폐기된 번호**이므로 재사용하지 않는다.

Usage: python3 tests/mutations/run_mutations.py <book_dir>
       (book_dir는 게이트 PASS 상태의 draft/book.pdf + outline.json 보유)
"""
import colorsys
import importlib.util
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
                     front_frame_for, collide_exempt_pages, LINT_HARD_CODES,
                     COLLIDE_OX_PT, OVERLAP_APPROVE_MAX_OX_PT, MM2PT, TOL)
import g16_tokens as g16


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


def mutate_low_contrast_tokens(style_dir, tokens, theme_text):
    """contrast_contract.entries 중 정적으로 대비 산출 가능한(fg·bg 둘 다 불투명
    리터럴 hex로 풀리는) 첫 페어를 골라 fg를 bg와 동일 색으로 되쓴다 —
    ratio=1.0이라 pt·bold와 무관하게 어떤 하한도 확실히 미달한다.

    style_dir는 임시 복사본이어야 한다(저장소 styles/ 절대 변조 금지). tokens.json을
    그 자리에서 덮어써, 이후 g16_tokens.style_inputs(style_dir=...)로 다시 읽으면
    검사가 실제로 "그 복사본"을 본다."""
    ctx = g16._ctx(tokens, theme_text)
    entries = (tokens.get("contrast_contract") or {}).get("entries") or []
    for i, e in enumerate(entries):
        fk, _fv = g16._resolve_token(e.get("fg"), ctx)
        bk, bv = g16._resolve_token(e.get("bg"), ctx)
        if fk == "hex" and bk == "hex":
            victim = dict(e, fg=bv)
            new_entries = entries[:i] + [victim] + entries[i + 1:]
            new_cc = dict(tokens["contrast_contract"], entries=new_entries)
            new_tokens = dict(tokens, contrast_contract=new_cc)
            (Path(style_dir) / "tokens.json").write_text(
                json.dumps(new_tokens, ensure_ascii=False, indent=2), encoding="utf-8")
            return i, victim
    raise AssertionError(
        "contrast_contract에 정적 판정 가능한 페어가 없음 — M10 주입 불가")


def mutate_palette_roles(style_dir, tokens):
    """diagram.palette_roles를 허용값(label|fill|stroke) 밖으로 바꿔 되쓴다.

    G16-SYNC는 build.py를 die()시키는 HARD 축인데 감도 회귀 자산이 없었다(W4 판정 D8).
    palette_roles는 G16-BRAND가 "0번 슬롯이 라벨색인가"를 판정하는 입력이라, 여기가
    조용히 부패하면 브랜드 대비 축이 통째로 빗나간다."""
    roles = list((tokens.get("diagram") or {}).get("palette_roles") or [])
    assert roles, "palette_roles가 없다 — M12 주입 불가"
    victim = list(roles)
    victim[0] = "labl"          # 오타 한 글자 — 사람이 실제로 내는 형태의 부패
    new_dg = dict(tokens["diagram"], palette_roles=victim)
    (Path(style_dir) / "tokens.json").write_text(
        json.dumps(dict(tokens, diagram=new_dg), ensure_ascii=False, indent=2), encoding="utf-8")
    return roles[0], victim[0]


def violating_brand(tokens, theme_text):
    """고정 동반색 계열에서 hue가 가장 먼 유채색을 찾아 돌려준다(book.json.brand 위치용).

    임의의 색을 박으면 그 스타일의 동반색과 우연히 계열이 맞을 수 있어 감도 검증이
    무의미해진다 — 12색환을 돌며 **실제로 Δ > HUE_TOL_DEG인 색**을 고른다."""
    comps = g16._hue_companions(tokens)
    if not comps:
        return None
    best = None
    for deg in range(0, 360, 5):
        r, g_, b = colorsys.hls_to_rgb(deg / 360.0, 0.35, 0.9)
        rgb = (int(r * 255), int(g_ * 255), int(b * 255))
        if not g16.is_chromatic(rgb):
            continue
        h = g16.hue_deg(rgb)
        d = min(g16.hue_dist(h, c[1]) for c in comps)
        if best is None or d > best[0]:
            best = (d, "#%02x%02x%02x" % rgb)
    if best and best[0] > g16.HUE_TOL_DEG:
        return best[1]
    return None


def mutate_contract_pt(style_dir, tokens, theme_text):
    """계약 엔트리 하나의 **pt만** theme.css의 어떤 font-size에도 없는 값으로 위조한다.

    색은 그대로 두는 것이 핵심이다 — 색까지 바꾸면 유령 엔트리(GHOST)로 잡히지만,
    현실의 자기완화는 "하한을 3.0으로 낮추려고 pt를 올리는" 형태다. 그 경로를 잡는
    유일한 축이 린터 ②(PT_UNATTAINABLE)이고, 그 린터가 파이프라인에서 실행되지 않아
    출하 경로가 전부 통과하던 것이 W4 판정 D1이다."""
    entries = (tokens.get("contrast_contract") or {}).get("entries") or []
    assert entries, "contrast_contract.entries가 없다 — M14 주입 불가"
    for i, e in enumerate(entries):
        if not isinstance(e.get("pt"), (int, float)) or isinstance(e.get("pt"), bool):
            continue
        # 13.7pt: 어떤 theme.css에도 없는 값이면서 하한 갈래(14)를 갓 밑도는 값이라
        # "위조하려다 실수한 값"처럼 보이지 않는다. 실제 완화 시도는 14~18로 올린다.
        victim = dict(e, pt=13.7)
        new_cc = dict(tokens["contrast_contract"], entries=entries[:i] + [victim] + entries[i + 1:])
        (Path(style_dir) / "tokens.json").write_text(
            json.dumps(dict(tokens, contrast_contract=new_cc), ensure_ascii=False, indent=2),
            encoding="utf-8")
        return i, e.get("pt"), victim
    raise AssertionError("pt를 가진 엔트리가 없다 — M14 주입 불가")


def band_probe_book(root, style, tokens, ratio_of_cap):
    """합성 authored 도해 1건짜리 최소 책을 만든다 (render_diagrams 전용 — 빌드하지 않는다).

    viewBox 폭을 `widths.full × MM2PT`로 잡으면 트림 전 환산이 1pt/user-unit이라
    라벨 pt를 사실상 직접 지정할 수 있다(트림 패딩만큼만 살짝 줄어들고, 그 오차는
    어서션이 실측 metrics를 읽으므로 흡수된다). 색은 스타일 팔레트에서만 고른다 —
    authored 트랙 alienColors가 팔레트 밖 색을 HARD로 죽이기 때문에, 색 때문에 죽으면
    밴드 감도를 재는 것이 아니라 다른 축을 재게 된다.

    ratio_of_cap: 상한(body_pt × maxRatio) 대비 최대 라벨 배수. >1이면 위반 표본.
    """
    dg = tokens["diagram"]
    body = tokens["body_pt"]
    cap = body * dg["labelBand"]["maxRatio"]
    floor = dg["minFontPt"]
    vb_w = dg["widths"]["full"] * MM2PT          # 트림 전 1pt == 1 user unit
    vb_h = 200.0
    pad = max(2.0, 0.008 * max(vb_w, vb_h))      # render_diagrams.trimViewBox와 동일 식
    scale = vb_w / (vb_w + 2 * pad)              # 트림 후 pt/user-unit
    big = (cap * ratio_of_cap) / scale
    small = (floor * 1.15) / scale               # 하한은 넉넉히 통과시킨다(HARD 회피)
    ink = dg["palette"][0]
    d = Path(root)
    (d / "diagrams").mkdir(parents=True, exist_ok=True)
    (d / "book.json").write_text(json.dumps({"style": style, "title": "밴드 프로브"},
                                            ensure_ascii=False), encoding="utf-8")
    (d / "diagrams" / "fig-01.json").write_text(
        json.dumps({"kind": "authored", "bf": {"width": "full"}}), encoding="utf-8")
    # rect는 bbox를 고정해 트림 결과를 예측 가능하게 만드는 용도(fill:none → alienColors 무관)
    (d / "diagrams" / "fig-01.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w:.2f} {vb_h:.2f}">'
        f'<rect x="0" y="0" width="{vb_w:.2f}" height="{vb_h:.2f}" fill="none" stroke="none"/>'
        f'<text x="4" y="60" font-size="{big:.3f}" fill="{ink}">밴드 표본</text>'
        f'<text x="4" y="170" font-size="{small:.3f}" fill="{ink}">하한 표본</text>'
        f'</svg>', encoding="utf-8")
    return {"cap_pt": cap, "floor_pt": floor, "expect_max_pt": big * scale}


def run_render_diagrams(book_dir, style):
    """render_diagrams.mjs를 실제로 돌린다. (rc, stdout+stderr) 반환."""
    import os
    import subprocess
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True,
                                          text=True).stdout.strip()
    except OSError:
        pass
    r = subprocess.run(["node", str(SKILL / "scripts" / "render_diagrams.mjs"),
                        str(book_dir), "--style", style],
                       capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def pick_body_page(doc, ch_starts, first_ch):
    """도비라·앞부속이 아닌 본문 면 중 라인이 넉넉한 면. (면번호, recs)."""
    for pno in range(first_ch - 1, doc.page_count):
        pg = pno + 1
        if pg in ch_starts or pg < first_ch:
            continue
        recs = line_records(doc[pno].get_text("dict").get("blocks", []), None)
        if len(recs) >= 12:
            return pg, recs
    return None, None


def mutate_hairline_overlap(doc, pg, recs):
    """기존 행 끝단에 **머리카락만큼**(ox ≈ 2pt) 물리는 장식 글리프를 찍는다.
    OVERLAP_APPROVED가 존재하는 사유(정당한 조판)와 같은 크기의 교차다."""
    t = recs[3]
    x0, y0, x1, y1 = t["box"]
    doc[pg - 1].insert_text(fitz.Point(x1 - 2.0, (y0 + y1) / 2 + 2.0), "·",
                            fontsize=8, fontfile=_stamp_font(), fontname="Fhl", color=(0, 0, 0))
    return t["text"][:16]


def mutate_severe_overlap(doc, pg, recs):
    """본문 행 위에 온전한 한 행을 통째로 덮어쓴다(ox ≫ 상한). 명백한 결함."""
    t = recs[9]
    x0, y0, x1, y1 = t["box"]
    doc[pg - 1].insert_text(fitz.Point(x0, (y0 + y1) / 2 + 2.5),
                            "중대한 겹침 주입 행 이 문장은 아래 본문과 완전히 겹쳐 인쇄된다",
                            fontsize=9.5, fontfile=_stamp_font(), fontname="Fsv", color=(0, 0, 0))
    return t["text"][:16]


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
    _tokens_g16_0, theme_text_0 = g16.style_inputs(style)  # 원본 styles/<style> (변조 없음)
    res_g16_0 = g16.run(style, _tokens_g16_0, theme_text_0)
    g16_fails0 = {ax: g16.fails_of(fs) for ax, fs in res_g16_0.items() if g16.fails_of(fs)}
    results["M0-clean"] = (not a0 and not b0 and not c0 and not s0 and not d0
                           and not col0 and not fit0 and not g16_fails0)
    if col0:
        print(f"      (M0 G3-COLLIDE 오탐 {sum(len(v) for v in col0.values())}건 {sorted(col0)})")
    if fit0:
        print(f"      (M0 G3-FIT 오탐 {len(fit0)}건 {fit0[:3]})")
    if g16_fails0:
        n = sum(len(v) for v in g16_fails0.values())
        print(f"      (M0 G16 오탐 {n}건 {list(g16_fails0)})")
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

        # M9b — **본문 면** 겹침과 OVERLAP_APPROVED. M9는 도비라(면제가 차단된 면)에만
        # 주입하므로 `collide_exempt` 분기를 한 번도 밟지 않았다(W4 판정 D8). 여기서
        # 세 상태를 한 면에서 순서대로 확인한다: 머리카락 교차 검출 → 승인으로 면제 성립
        # → 상한 초과 겹침을 얹으면 승인이 무효(G11 선행조건 FAIL).
        work = Path(td) / "m9b.pdf"
        shutil.copy(book_dir / "draft" / "book.pdf", work)
        doc = fitz.open(work)
        pgb, recsb = pick_body_page(doc, ch_starts, ch_starts[0])
        assert pgb, "본문 면을 찾지 못했다 — M9b 주입 불가"
        hl_victim = mutate_hairline_overlap(doc, pgb, recsb)
        colb = collide_scan(doc, style, tokens)
        hits_hair = colb.get(pgb, [])
        exempt_hair = collide_exempt_pages(set(), {pgb}, ch_starts, ch_starts[0])
        ok_detect = bool(hits_hair)
        ok_exempt = pgb in exempt_hair                       # 승인이 실제로 면제를 만든다
        ok_bound_hair = all(h["ox"] <= OVERLAP_APPROVE_MAX_OX_PT for h in hits_hair)
        mutate_severe_overlap(doc, pgb, recsb)
        colc = collide_scan(doc, style, tokens)
        over = [h for h in colc.get(pgb, []) if h["ox"] > OVERLAP_APPROVE_MAX_OX_PT]
        results["M9b-body-overlap-approve"] = ok_detect and ok_exempt and ok_bound_hair and bool(over)
        print(f"      (M9b 본문 p{pgb} '{hl_victim}' — 머리카락 교차 {len(hits_hair)}건 "
              f"ox {[h['ox'] for h in hits_hair]} <= 상한 {OVERLAP_APPROVE_MAX_OX_PT}pt: {ok_bound_hair} · "
              f"승인 면제 성립 {ok_exempt} / 중대 겹침 추가 후 상한 초과 {len(over)}건 "
              f"ox {[h['ox'] for h in over][:2]} → G11 선행조건 FAIL)")
        doc.close()

        # M9c — 면제 차감 불변식. 표지가 fullbleed(imgarea 1.0)여도, 도비라에 승인이
        # 찍혀도 그 면들은 면제 집합에 들어갈 수 없다(W4 판정 D2 회귀 고정).
        fc = ch_starts[0]
        ex = collide_exempt_pages({1, 2, fc, fc + 1}, {1, 2, fc, fc + 1}, ch_starts, fc)
        results["M9c-exempt-front-cut"] = (1 not in ex and 2 not in ex
                                           and fc not in ex and (fc + 1) in ex)
        print(f"      (M9c 표지·목차·도비라 전부 fullbleed+승인 입력 → 면제 집합 {sorted(ex)} "
              f"(앞부속 1~{fc - 1}·도비라 {ch_starts[:3]} 차감 확인))")

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

        # M10 — G16-CONTRAST 저대비 토큰. 스타일 팩을 임시 복사본에 복제해 그 사본만
        # 변조한다(저장소 styles/는 절대 변조하지 않는다). enforce:true가 아니면
        # G16-CONTRAST가 WARN까지만 올리므로 이 스타일에서는 성립하지 않는다.
        cc = (tokens.get("contrast_contract") or {})
        if cc.get("enforce") is True:
            style_copy = Path(td) / "style10"
            shutil.copytree(SKILL / "styles" / style, style_copy)
            tokens10, css10 = g16.style_inputs(style, style_dir=style_copy)
            idx10, victim10 = mutate_low_contrast_tokens(style_copy, tokens10, css10)
            # 검사는 방금 되쓴 파일을 다시 읽어서 돈다 — "그 복사본"을 실제로 본다.
            tokens10b, css10b = g16.style_inputs(style, style_dir=style_copy)
            res10 = g16.run(style, tokens10b, css10b, style_dir=style_copy)
            fails10 = g16.fails_of(res10["G16-CONTRAST"])
            results["M10-low-contrast-tokens"] = bool(fails10)
            print(f"      (M10 entries[{idx10}] {victim10['where']} fg={victim10['fg']} "
                  f"(=bg, ratio 1.0) → G16-CONTRAST FAIL {len(fails10)}건)")
        else:
            print(f"      (M10 건너뜀 — {style} contrast_contract.enforce != true)")

        # M12 — G16-SYNC palette_roles 훼손. M10과 같은 임시 사본 원칙.
        style12 = Path(td) / "style12"
        shutil.copytree(SKILL / "styles" / style, style12)
        tok12, css12 = g16.style_inputs(style, style_dir=style12)
        was, now = mutate_palette_roles(style12, tok12)
        tok12b, css12b = g16.style_inputs(style, style_dir=style12)
        f12 = g16.fails_of(g16.run(style, tok12b, css12b, style_dir=style12)["G16-SYNC"])
        results["M12-palette-roles"] = bool(f12)
        print(f"      (M12 palette_roles[0] {was!r} → {now!r} → G16-SYNC FAIL {len(f12)}건)")

        # M13 — G16-BRAND. brand는 book.json 위치(=FAIL 강도)로 주입한다.
        bad_brand = violating_brand(tokens, g16.style_inputs(style)[1])
        if bad_brand:
            tok13, css13 = g16.style_inputs(style)
            f13 = g16.fails_of(g16.run(style, tok13, css13, brand=bad_brand)["G16-BRAND"])
            results["M13-violating-brand"] = bool(f13)
            print(f"      (M13 book.json brand={bad_brand} → G16-BRAND FAIL {len(f13)}건: "
                  f"{f13[0]['msg'][:76] if f13 else ''})")
        else:
            print("      (M13 건너뜀 — 고정 동반색이 없어 hue 정합 축이 성립하지 않음)")

        # M14 — 린터 배선. pt만 위조하고 색은 그대로 두어 축②(PT_UNATTAINABLE)를 겨눈다.
        # 두 가지를 함께 어서션한다: ㉠린터가 위조를 잡는가 ㉡그 코드가 qc_gate가 fails로
        # 올리는 집합에 실재하는가(배선 — 린터가 잡아도 아무도 부르지 않으면 무효였다).
        html14 = book_dir / "typeset" / "book-final.html"
        if html14.exists():
            style14 = Path(td) / "style14"
            shutil.copytree(SKILL / "styles" / style, style14)
            tok14, css14 = g16.style_inputs(style, style_dir=style14)
            idx14, old_pt, victim14 = mutate_contract_pt(style14, tok14, css14)
            spec = importlib.util.spec_from_file_location(
                "bf_lint_contrast", SKILL / "tests" / "lint_contrast.py")
            lint = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lint)
            lint._VIRT_CACHE.clear()
            r14 = lint.lint_book(book_dir, style_dir_override=style14)
            codes14 = {x["code"] for x in r14["findings"] if x["level"] == "FAIL"}
            hard14 = codes14 & LINT_HARD_CODES
            results["M14-linter-pt-forgery"] = ("PT_UNATTAINABLE" in codes14
                                                and "PT_UNATTAINABLE" in LINT_HARD_CODES
                                                and bool(hard14))
            print(f"      (M14 entries[{idx14}] {victim14.get('where', '?')[:30]} "
                  f"pt {old_pt} → 13.7 → 린터 FAIL 코드 {sorted(codes14)} · "
                  f"qc_gate가 fails로 올리는 코드 {sorted(hard14)})")
        else:
            print("      (M14 건너뜀 — typeset/book-final.html 부재(typst 엔진))")

        # M15 — 라벨 밴드 상한(WARN 축). 위반 표본과 대조군을 한 쌍으로 돌려
        # 감도(검출)와 특이도(오탐 0)를 함께 고정하고, **강도가 WARN**임을 rc로 어서션한다.
        dgm = tokens.get("diagram") or {}
        if not (isinstance(dgm.get("labelBand"), dict) and tokens.get("body_pt")
                and (dgm.get("widths") or {}).get("full") and dgm.get("palette")):
            print("      (M15 건너뜀 — 이 스타일에 diagram.labelBand/body_pt/widths.full 미선언)")
        else:
            def band_run(tag, ratio_of_cap):
                bd = Path(td) / f"m15-{tag}"
                spec_ = band_probe_book(bd, style, tokens, ratio_of_cap)
                rc_, out_ = run_render_diagrams(bd, style)
                mp = bd / "assets" / "fig-01.metrics.json"
                met = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else None
                return spec_, rc_, out_, met

            spec_v, rc_v, out_v, met_v = band_run("violate", 1.8)
            spec_c, rc_c, out_c, met_c = band_run("control", 0.9)
            if rc_v == 0 and rc_c == 0 and met_v and met_c:
                warn_v = "DIAGRAM-BAND" in out_v and "상한 초과" in out_v
                warn_c = "상한 초과" not in out_c
                ok15 = (warn_v and met_v["band"]["verdict"] == "violation"
                        and met_v["band"]["level"] == "WARN"
                        and met_v["maxPt"] > met_v["capPt"]
                        and met_v["minPt"] >= met_v["minFontPt"]      # 하한 HARD를 안 밟았다
                        and warn_c and met_c["band"]["verdict"] == "ok"
                        and met_c["maxPt"] <= met_c["capPt"])
                results["M15-label-band"] = ok15
                print(f"      (M15 위반본 max {met_v['maxPt']}pt = 본문 {met_v['bodyPt']}pt × "
                      f"{met_v['ratio']} > 상한 {met_v['maxRatio']}×({met_v['capPt']}pt) "
                      f"· 최소 {met_v['minPt']}pt ≥ 하한 {met_v['minFontPt']}pt → "
                      f"WARN 검출 {warn_v} · **exit {rc_v}(HARD 아님)** / "
                      f"대조군 max {met_c['maxPt']}pt ≤ {met_c['capPt']}pt → WARN 없음 {warn_c})")
            else:
                results["M15-label-band"] = False
                head = (out_v or out_c).strip().splitlines()[-1:] or [""]
                print(f"      (M15 실행 실패 — rc {rc_v}/{rc_c}, metrics {bool(met_v)}/{bool(met_c)}: "
                      f"{head[0][:120]})")

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
    print("전 뮤테이션 검출 — G14·G1-SCALE·G3-COLLIDE/FIT·G16 3축·린터 배선·도해 라벨 밴드 감도 확인")


if __name__ == "__main__":
    main()
