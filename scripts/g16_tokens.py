#!/usr/bin/env python3
"""bookforge G16-TOKENS — 렌더 전 토큰 계약 게이트 (순수 함수 모듈).

Usage: python3 scripts/g16_tokens.py <style>        # 단일 스타일 사람 읽기용 출력

축 2개(1단계 범위 — BRAND는 후속 커밋):
  G16-SYNC     : 스타일 팩의 색 계약 정합. engine↔팩 실물 일치 · diagram.palette 존재 ·
                 palette_roles 무결성 · brand_default↔palette[0] 동기 ·
                 contrast_contract 형식(enforce bool)과 토큰명 해석 가능성
  G16-CONTRAST : contrast_contract 선언 페어의 WCAG 대비를 pt·bold 파생 하한과 대조

설계 근거 둘.
  ① 렌더 전 경계이므로 HARD FAIL은 "증명 가능한 것"에만 준다 — fg·bg가 둘 다
     불투명 리터럴 hex로 해석되는 페어만이 어떤 렌더링으로도 구제되지 않는다.
     알파·그라데이션·해석 불가 배경은 전부 WARN이고, 물리적 강제는 렌더 후
     G14-C(tocgate.py)가 픽셀 샘플로 계속 담당한다.
  ② 승격은 전역 플래그가 아니라 스타일별 데이터 스위치(contrast_contract.enforce)다.
     전역 --g16-warn-only는 긴급 탈출구로만 남는다(build.py).

부재는 결함이지만 잉여는 아니다 — 미사용 팔레트 슬롯·미사용 CSS 토큰은 영구 WARN이며
절대 FAIL로 올리지 않는다.
"""
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

ROLES = ("label", "fill", "stroke")


# ---------------------------------------------------------------- 대비 산술

def contrast_floor(pt, bold):
    """대비 하한의 단일 진리원.

    현행 tocgate.py:433(G14-C)과 같은 값이라 두 게이트가 다른 수를 내지 않는다.
    이 값은 WCAG(18pt / 14pt-bold)보다 두 갈래 모두 느슨하며, 교정은 W4 7단계에서
    이 함수 하나만 바꾸는 것으로 끝나야 한다 — 그래서 하한을 계약 데이터에
    저장하지 않고 pt·bold에서 파생한다.
    """
    return 3.0 if (pt >= 14 or (pt >= 10.5 and bold)) else 4.5


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(rgb):
    """WCAG 2.x 상대휘도 (sRGB 표준식)."""
    r, g, b = (_lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_rgb, bg_rgb):
    a, b = rel_luminance(fg_rgb), rel_luminance(bg_rgb)
    if a < b:
        a, b = b, a
    return (a + 0.05) / (b + 0.05)


# 4·8자리(알파 포함)도 인식한다. Chromium은 `#1b6e9cff`를 정상 파싱하므로(실측)
# 8자리를 "해석 불가"로 두면 렌더되는 입력을 게이트가 잠근다 — S1의 뿌리였다.
# 교대는 긴 것부터 — 짧은 대안이 먼저 물면 뒤 두 자리가 잘린다.
_HEX_RE = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")

# rgb()/rgba() 함수 표기 — 콤마·공백 구분자, 채널 %/정수, 알파 0~1 또는 %.
_RGB_FN_RE = re.compile(r"""rgba?\(\s*
    ([0-9.]+%?)\s*(?:,\s*|\s+)
    ([0-9.]+%?)\s*(?:,\s*|\s+)
    ([0-9.]+%?)\s*
    (?:(?:,|/)\s*([0-9.]+%?)\s*)?
\)""", re.X | re.I)


def _chan(tok, scale=255.0):
    v = float(tok[:-1]) / 100.0 * scale if tok.endswith("%") else float(tok)
    return max(0.0, min(scale, v))


def parse_color(s):
    """리터럴 색 -> (r,g,b,a) (a는 0~255). hex 3/4/6/8자리와 rgb()/rgba() 표기 지원.

    그 밖(var()·gradient·색이름·$플레이스홀더)은 None. 알파는 버리지 않고 실어 보낸다 —
    '반투명이라 정적 대비 산출 불가'(WARN)와 '아예 색이 아님'(FAIL)은 다른 판정이다.
    """
    if not isinstance(s, str):
        return None
    s = s.strip()
    m = _HEX_RE.fullmatch(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) if len(h) == 8 else 255
        return rgb + (a,)
    m = _RGB_FN_RE.fullmatch(s)
    if m:
        rgb = tuple(int(round(_chan(m.group(i)))) for i in (1, 2, 3))
        a = 255 if m.group(4) is None else int(round(_chan(m.group(4), 1.0) * 255))
        return rgb + (a,)
    return None


def parse_hex(s):
    """불투명 리터럴 색 -> (r,g,b). 반투명·비리터럴은 None(정적 대비 산출 대상 아님)."""
    c = parse_color(s)
    return None if c is None or c[3] != 255 else c[:3]


def norm_hex(s):
    """불투명 리터럴 색 -> '#rrggbb'. `#1b6e9cff`는 `#1b6e9c`로 정규화된다."""
    rgb = parse_hex(s)
    return None if rgb is None else "#%02x%02x%02x" % rgb


def _literal_res(s):
    """리터럴 색 문자열의 3분 해석. 리터럴이 아니면 None(호출자가 다음 경로로).

    반투명(알파<FF)은 FAIL이 아니라 nonliteral — 렌더는 되지만 정적 대비는 배경에
    의존하므로 증명이 성립하지 않는다(G14-C 픽셀 샘플 소관).
    """
    c = parse_color(s)
    if c is None:
        return None
    if c[3] != 255:
        return ("nonliteral", f"{s.strip()} (알파 {c[3]}/255 — 반투명)")
    return ("hex", "#%02x%02x%02x" % c[:3])


def _strip_important(val):
    """CSS `!important` 접미 제거 — 값의 색 해석에는 영향이 없다."""
    return re.sub(r"\s*!\s*important\s*$", "", val, flags=re.I)


# ------------------------------------------------------- theme.css 토큰 그래프

def _strip_comments(text):
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


_DECL_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]*)")


def css_root_vars(theme_text):
    """theme.css 전체의 커스텀 프로퍼티 선언 맵(값은 미해석 원문). 마지막 선언이 이긴다.

    **캐스케이드 근사임을 명시한다.** 선택자 특정성·@media 조건·상속 문맥을 해석하지
    않고 파일 등장 순서만 본다. 정확한 계산은 브라우저만 할 수 있으므로 여기서는
    "뒤에 오는 선언이 앞을 덮는다"는 동일 특정성 규칙만 근사한다.

    이전 구현은 첫 `:root` 블록의 첫 `}`까지만 읽어, 두 번째 `:root`나 @media 안의
    재정의를 통째로 무시하고 브라우저가 쓰지 않을 구값으로 대비를 계산했다(S5, 무신호).
    전수 수집은 그 무신호를 없앤다. 대가로 `.foo{--x:...}` 같은 국소 선언도 :root와
    같은 층으로 섞이지만, 계약이 참조하는 토큰은 전역 토큰이라 실무상 근사가 성립한다.
    """
    if not theme_text:
        return {}
    out = {}
    for name, val in _DECL_RE.findall(_strip_comments(theme_text)):
        out[name] = val.strip()   # 마지막 선언이 이긴다(dict 덮어쓰기)
    return out


def css_literal_hexes(theme_text):
    """theme.css에 리터럴로 등장하는 모든 hex(정규화). 주석은 제외 —
    주석 안의 '구 #6d747a' 같은 이력 기록이 사용 근거로 오인되면 안 된다.
    반투명 hex(알파<FF)는 불투명 색이 아니므로 집합에 넣지 않는다."""
    if not theme_text:
        return set()
    hexes = (norm_hex(m.group(0)) for m in _HEX_RE.finditer(_strip_comments(theme_text)))
    return {h for h in hexes if h}


# 해석 결과 종류: ("hex", "#rrggbb") / ("nonliteral", 사유) / ("unresolved", 사유)
# 2번째 원소는 hex일 때만 값이고, 나머지 둘은 **사람이 읽는 사유 문자열**이다.
# 사유를 여기서 만들어야 오귀속이 없다 — brand발 실패를 스타일 팩 탓으로 돌리던 게 S1의 부수 결함.
def _resolve_value(val, ctx, depth=0):
    if depth > 8:
        return ("nonliteral", f"var() 참조 깊이 8 초과: {val}")
    val = _strip_important(val.strip())
    # build_html.py:640-643이 렌더 전에 치환하는 두 플레이스홀더 — 완전 재현 가능하다.
    if val == "$key_color":
        return _brand_res(ctx)
    if val == "$key_tint":
        return ("nonliteral", "rgba(brand, 0.08) — 알파")   # 알파 — 정적 대비 산출 불가
    lit = _literal_res(val)
    if lit:
        return lit
    # var(--x, fallback)의 fallback 해석은 **의도적으로 하지 않는다** — 어느 쪽이
    # 쓰일지는 --x의 정의 여부에 달렸고 그건 캐스케이드 문맥이라 정적 증명이 아니다.
    m = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", val, re.I)
    if m:
        return _resolve_token(m.group(1), ctx, depth + 1)
    return ("nonliteral", val)


def _resolve_token(name, ctx, depth=0):
    """토큰명 -> 색. 지원 형식:
      '--ink'      theme.css :root 변수(체인·$key_color 치환 포함)
      'brand'      book.json brand > tokens.brand_default
      'palette[3]' tokens.diagram.palette 슬롯
      '#1e7aad'    리터럴 hex
      '~...'       비리터럴 배경의 명시 선언(그라데이션·이미지) — 대비 산출 대상 아님
    """
    if not isinstance(name, str):
        return ("unresolved", f"{name!r}는 문자열이 아님")
    name = name.strip()
    if name.startswith("~"):
        return ("nonliteral", name[1:] or "declared-nonliteral")
    lit = _literal_res(name)
    if lit:
        return lit
    if name == "brand":
        return _brand_res(ctx)
    m = re.fullmatch(r"palette\[(\d+)\]", name)
    if m:
        pal = ctx.get("palette") or []
        i = int(m.group(1))
        if i >= len(pal):
            return ("unresolved", f"palette[{i}] 범위 밖 — tokens.json diagram.palette는 {len(pal)}슬롯")
        return _literal_res(pal[i]) or ("nonliteral", f"palette[{i}]={pal[i]!r}")
    if name.startswith("--"):
        raw = ctx.get("vars", {}).get(name)
        if raw is None:
            return ("unresolved", f"{name}이 theme.css의 커스텀 프로퍼티 선언에 없음")
        return _resolve_value(raw, ctx, depth + 1)
    return ("unresolved", f"{name!r}은 지원 형식(--토큰 | brand | palette[n] | #hex | ~비리터럴) 밖")


def _brand_res(ctx):
    """brand(=$key_color) 해석 결과. 사유 문자열이 출처를 스스로 지목한다."""
    return ctx.get("brand_res") or ("unresolved", "brand 미선언")


def _ctx(tokens, theme_text, brand=None):
    # 출처를 붙들어 둔다 — brand는 book.json(사용자 데이터)에서 오고 brand_default는
    # 스타일 팩에서 온다. 해석 실패 메시지가 엉뚱한 파일을 지목하면 수리자가 헤맨다.
    from_book = isinstance(brand, str) and brand.strip() != ""
    raw = (brand if from_book else tokens.get("brand_default")) or ""
    src = "book.json brand" if from_book else "tokens.json brand_default"
    if not str(raw).strip():
        res = ("unresolved", f"{src} 미선언 — $key_color/brand 참조를 풀 수 없음")
    else:
        lit = _literal_res(raw)
        # 반투명 brand는 렌더는 되므로 nonliteral(WARN), 색이 아닌 값만 unresolved(FAIL).
        res = lit or ("unresolved", f"{src}={raw!r}가 리터럴 색(#hex | rgb())이 아님")
        if lit and lit[0] == "nonliteral":
            res = ("nonliteral", f"{src}={raw!r} — {lit[1]}")
    return {
        "vars": css_root_vars(theme_text),
        "brand": res[1] if res[0] == "hex" else None,
        "brand_res": res,
        "palette": (tokens.get("diagram") or {}).get("palette") or [],
    }


def _f(axis, level, msg):
    return {"axis": axis, "level": level, "msg": msg}


# ------------------------------------------------------------------- G16-SYNC

def g16_sync(style, tokens, theme_text, brand=None, style_dir=None):
    """색·역할 계약 정합. HARD FAIL은 증명 가능한 것에만."""
    out = []
    ctx = _ctx(tokens, theme_text, brand)
    engine = tokens.get("engine", "typst")
    dg = tokens.get("diagram")
    sd = Path(style_dir) if style_dir else (SKILL / "styles" / style)

    # ---- HARD ⓪ engine ↔ 팩 실물 일치 ----
    # theme.html이 실존하는데 engine이 html이 아니면 렌더 경로 선택이 틀린다. engine 키를
    # 한 줄 지우면 기본값 typst로 떨어져 html 전용 HARD들이 통째로 강등되던 구멍(S4).
    # 파일 실존 대조라 증명 가능하다 — 추정이 아니다.
    if (sd / "theme.html").exists() and engine != "html":
        out.append(_f("SYNC", "FAIL",
                      f"styles/{style}/theme.html이 실존하는데 engine={engine!r} — "
                      f"engine 키 누락/오기(기본값 typst)로 html 전용 검사가 강등된다"))

    # ---- HARD ① diagram.palette 존재 + palette_roles 무결성 (필수 계약) ----
    # 옵셔널이면 새 스타일이 빼먹고 G16-BRAND가 조용히 무력화된다.
    # `if dg:`(falsy 우회, S3)를 버리고 palette 부재 자체를 FAIL로 못박는다 —
    # 6스타일 전부 palette를 계약으로 가지며 render_diagrams.mjs:37 `[...dg.palette]`가
    # 이를 그대로 소비한다(부재 시 그쪽에서 터진다).
    if not isinstance(dg, dict):
        out.append(_f("SYNC", "FAIL",
                      f"diagram 블록 부재/비객체({type(dg).__name__}) — "
                      f"palette·palette_roles는 스타일 팩의 필수 계약이다"))
        dg = {}
    pal = dg.get("palette")
    if not isinstance(pal, list) or not pal:
        out.append(_f("SYNC", "FAIL",
                      f"diagram.palette 부재/빈 배열 — render_diagrams.mjs:37이 "
                      f"`[...dg.palette]`로 소비하는 필수 계약이다"))
        pal = pal if isinstance(pal, list) else []
    roles = dg.get("palette_roles")
    if roles is None:
        out.append(_f("SYNC", "FAIL", f"diagram.palette_roles 부재 — palette {len(pal)}슬롯과 "
                                      f"병렬 배열로 필수 선언(허용값 {'|'.join(ROLES)})"))
    elif not isinstance(roles, list) or len(roles) != len(pal):
        out.append(_f("SYNC", "FAIL", f"diagram.palette_roles 길이 {len(roles) if isinstance(roles, list) else '비배열'}"
                                      f" != palette {len(pal)}"))
    else:
        bad = [(i, r) for i, r in enumerate(roles) if r not in ROLES]
        for i, r in bad:
            out.append(_f("SYNC", "FAIL", f"diagram.palette_roles[{i}]={r!r} — 허용값 {'|'.join(ROLES)} 밖"))

    # ---- HARD ② brand_default ↔ palette[0] 동기 ----
    # render_diagrams.mjs:38이 book.json brand로 palette[0]을 덮어쓴다 = 0번 슬롯은
    # 브랜드 슬롯이라는 계약. 둘이 어긋나면 브랜드 없는 책의 도해 주색과 지면 키색이
    # 갈라진다. 단 typst 4종은 meta.brand가 theme.typ 계산식 안에서 재바인딩되어
    # (business: accent, brand는 navy-700 별도) 정적으로 증명할 수 없다 —
    # 스캔 범위 밖(플랜 전제교정 ③)이므로 WARN으로만 남긴다.
    bd = norm_hex(tokens.get("brand_default") or "")
    p0 = norm_hex(pal[0] or "") if pal else None
    if bd and p0 and bd != p0:
        lv = "FAIL" if engine == "html" else "WARN"
        note = "" if engine == "html" else " (typst: theme.typ 재바인딩은 정적 해석 범위 밖 — 수동 감사 항목)"
        out.append(_f("SYNC", lv, f"brand_default {bd} != diagram.palette[0] {p0}{note}"))

    # ---- HARD ③ contrast_contract 토큰명 해석 가능성 ----
    cc = tokens.get("contrast_contract")
    if isinstance(cc, dict):
        # enforce는 승격 스위치다. 문자열 "false"/"no"/"off"가 truthy로 읽혀 강제가
        # 켜지던 오탐(S9)을 막으려면 형식 자체를 계약으로 못박아야 한다 — 부재도 malformed다.
        if not isinstance(cc.get("enforce"), bool):
            out.append(_f("SYNC", "FAIL",
                          f"contrast_contract.enforce={cc.get('enforce')!r} — true/false(JSON bool) "
                          f"만 허용(부재·문자열 불가). 문자열은 truthy로 읽혀 강제가 오작동한다"))
        entries = cc.get("entries")
        if not isinstance(entries, list):
            out.append(_f("SYNC", "FAIL", "contrast_contract.entries가 배열이 아님"))
            entries = []
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                out.append(_f("SYNC", "FAIL", f"contrast_contract.entries[{i}]가 객체가 아님"))
                continue
            for k, ty in (("fg", str), ("bg", str), ("pt", (int, float)), ("bold", bool), ("where", str)):
                if not isinstance(e.get(k), ty) or isinstance(e.get(k), bool) != (ty is bool):
                    out.append(_f("SYNC", "FAIL",
                                  f"contrast_contract.entries[{i}] ({e.get('where', '?')}) 키 {k} 누락/형식 오류"))
            for side in ("fg", "bg"):
                kind, why = _resolve_token(e.get(side), ctx)
                if kind == "unresolved":
                    # 사유는 해석기가 만든다 — 실패 원인이 book.json이면 book.json을 지목한다.
                    out.append(_f("SYNC", "FAIL",
                                  f"contrast_contract.entries[{i}] ({e.get('where', '?')}) "
                                  f"{side}={e.get(side)!r} 해석 불가 — {why}"))

    # ---- WARN: 팔레트↔theme.css 교집합 (부재는 결함, 잉여는 아님) ----
    if pal and engine == "html":
        css_hex = css_literal_hexes(theme_text)
        if ctx["brand"]:
            css_hex.add(ctx["brand"])   # $key_color 치환 결과
        for i, c in enumerate(pal):
            h = norm_hex(c)
            if h and h not in css_hex:
                role = roles[i] if (isinstance(roles, list) and i < len(roles)) else None
                out.append(_f("SYNC", "WARN",
                              f"palette[{i}] {h} (role={role})이 theme.css 리터럴에 없음 — 도해 전용 슬롯"))
        pal_hex = {norm_hex(c) for c in pal if norm_hex(c)}
        for name, raw in ctx["vars"].items():
            kind, v = _resolve_value(raw, ctx)
            if kind != "hex" or v == "#ffffff":   # 백색은 alienColors가 암묵 허용(render_diagrams.mjs:108)
                continue
            if v not in pal_hex:
                out.append(_f("SYNC", "WARN", f"CSS 토큰 {name} {v}이 diagram.palette에 없음 — 도해에서 사용 불가"))
    elif pal and engine != "html":
        out.append(_f("SYNC", "WARN",
                      f"engine={engine} — theme.typ 색은 .darken()/.transparentize() 계산식이라 "
                      f"팔레트↔테마 대조는 스캔 범위 밖(수동 감사 항목)"))
    return out


# --------------------------------------------------------------- G16-CONTRAST

def g16_contrast(style, tokens, theme_text, brand=None):
    """선언 페어의 정적 대비 판정.

    fg·bg가 둘 다 불투명 리터럴 hex로 풀릴 때만 계산한다(그때만 증명이 성립).
    미달 시 contrast_contract.enforce가 true면 FAIL, false면 WARN.
    """
    out = []
    cc = tokens.get("contrast_contract")
    if not isinstance(cc, dict):
        # typst 4종이 이 경로다 — 축 N/A. 절대 FAIL이 아니다(잠김 차단).
        out.append(_f("CONTRAST", "WARN",
                      f"styles/{style}/tokens.json에 contrast_contract 미선언 — 축 N/A"))
        return out
    ctx = _ctx(tokens, theme_text, brand)
    # `is True` 엄격 판정 — "false"/"no"/"off" 같은 문자열이 truthy로 읽혀 강제를 켜던
    # 오탐(S9)을 차단한다. bool이 아닌 값 자체는 SYNC가 malformed FAIL로 이미 잡는다.
    enforce = cc.get("enforce") is True
    for i, e in enumerate(cc.get("entries") or []):
        if not isinstance(e, dict):
            continue
        where = e.get("where", f"entries[{i}]")
        pt, bold = e.get("pt"), bool(e.get("bold"))
        if not isinstance(pt, (int, float)) or isinstance(pt, bool):
            continue   # 형식 오류는 SYNC가 이미 FAIL로 잡았다
        fk, fv = _resolve_token(e.get("fg"), ctx)
        bk, bv = _resolve_token(e.get("bg"), ctx)
        src = f" [{e['source']}]" if e.get("source") else ""
        if fk != "hex" or bk != "hex":
            side, why = ("fg", fv) if fk != "hex" else ("bg", bv)
            out.append(_f("CONTRAST", "WARN",
                          f"{where}{src}: {side}={e.get(side)!r}가 불투명 리터럴이 아님 ({why}) "
                          f"— 정적 판정 불가, G14-C 픽셀 샘플 소관"))
            continue
        ratio = contrast_ratio(parse_hex(fv), parse_hex(bv))
        floor = contrast_floor(pt, bold)
        if ratio < floor:
            out.append(_f("CONTRAST", "FAIL" if enforce else "WARN",
                          f"{where}{src}: {e['fg']} {fv} on {e['bg']} {bv} "
                          f"= {ratio:.2f} < {floor} ({pt}pt{'/bold' if bold else ''})"))
    return out


# ------------------------------------------------------------------ 러너/도구

def style_inputs(style, skill=SKILL):
    """스타일 팩에서 (tokens, theme_text)를 읽는다. theme.css가 없으면 None."""
    sd = Path(skill) / "styles" / style
    tokens = json.loads((sd / "tokens.json").read_text(encoding="utf-8"))
    css = sd / "theme.css"
    return tokens, (css.read_text(encoding="utf-8") if css.exists() else None)


def run(style, tokens, theme_text, brand=None, style_dir=None):
    """두 축을 한 번에. build.py·qc_gate.py가 공유하는 단일 진입점.

    style_dir는 engine↔팩 실물 대조(HARD ⓪)에만 쓰이며, 생략하면 SKILL/styles/<style>.
    """
    return {
        "G16-SYNC": g16_sync(style, tokens, theme_text, brand, style_dir),
        "G16-CONTRAST": g16_contrast(style, tokens, theme_text, brand),
    }


def fails_of(findings):
    return [f for f in findings if f["level"] == "FAIL"]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 scripts/g16_tokens.py <style>")
    style = sys.argv[1]
    if not (SKILL / "styles" / style).exists():
        sys.exit(f"unknown style: {style}")
    tokens, css = style_inputs(style)
    res = run(style, tokens, css)
    nf = nw = 0
    print(f"G16-TOKENS  style={style}  engine={tokens.get('engine', 'typst')}  "
          f"theme.css={'있음' if css else '없음'}")
    for axis in ("G16-SYNC", "G16-CONTRAST"):
        fs = res[axis]
        f_n = len([x for x in fs if x["level"] == "FAIL"])
        w_n = len(fs) - f_n
        nf, nw = nf + f_n, nw + w_n
        print(f"\n  [{axis}] FAIL {f_n} · WARN {w_n}")
        for x in fs:
            print(f"    {x['level']:4} {x['msg']}")
        if not fs:
            print("    (없음)")
    print(f"\n  합계: FAIL {nf} · WARN {nw}")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
