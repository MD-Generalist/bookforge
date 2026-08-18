#!/usr/bin/env python3
"""bookforge G16-TOKENS — 렌더 전 토큰 계약 게이트 (순수 함수 모듈).

Usage: python3 scripts/g16_tokens.py <style>        # 단일 스타일 사람 읽기용 출력

축 3개:
  G16-SYNC     : 스타일 팩의 색 계약 정합. engine↔팩 실물 일치 · diagram.palette 존재 ·
                 palette_roles 무결성 · brand_default↔palette[0] 동기 ·
                 contrast_contract 형식(enforce bool)과 토큰명 해석 가능성
  G16-CONTRAST : contrast_contract 선언 페어의 WCAG 대비를 pt·bold 파생 하한과 대조
  G16-BRAND    : 브랜드 입력 사전 검증(형식·치환 지점 대비·고정 동반색과의 hue 정합)

설계 근거 둘.
  ① 렌더 전 경계이므로 HARD FAIL은 "증명 가능한 것"에만 준다 — fg·bg가 둘 다
     불투명 리터럴 hex로 해석되는 페어만이 어떤 렌더링으로도 구제되지 않는다.
     알파·그라데이션·해석 불가 배경은 전부 WARN이고, 물리적 강제는 렌더 후
     G14-C(tocgate.py)가 픽셀 샘플로 계속 담당한다.
  ② 승격은 전역 플래그가 아니라 스타일별 데이터 스위치(contrast_contract.enforce)다.
     전역 --g16-warn-only는 긴급 탈출구로만 남는다(build.py).

부재는 결함이지만 잉여는 아니다 — 미사용 팔레트 슬롯·미사용 CSS 토큰은 영구 WARN이며
절대 FAIL로 올리지 않는다.

BRAND만 세 번째 원칙을 더 갖는다: **값 출처로 강도를 분기한다.** book.json.brand는
사용자 입력이 무검증으로 치환되는 구멍이라 FAIL, 스타일 팩의 brand_default는 이미
출하된 부채라 WARN이다. 후자를 FAIL로 두면 출하 기본색 하나가 그 스타일의 모든 책을
잠근다(business #C2662E는 백색 위 4.01로 자기 게이트에 걸린다).
"""
import colorsys
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

ROLES = ("label", "fill", "stroke")

# G14-B와 같은 값이어야 두 게이트가 다른 판정을 내지 않는다. 사전 FAIL의 존재 이유가
# "2-pass 렌더 후에야 G14-B에서 죽는 것"을 앞당기는 것이므로 값이 갈리면 목적이 무너진다.
# 출처: scripts/tocgate.py:368 `def g14b_key_color(..., tol=36, ...)` 기본 인자.
HUE_TOL_DEG = 36
# 유채/무채 경계도 같은 출처를 쓴다 — 출처: scripts/tocgate.py:39 `_is_colored(rgb, min_chroma=28)`.
MIN_CHROMA = 28
# 하한을 갓 넘긴 구간은 통과시키되 표시한다. 정적 토큰값과 렌더 샘플값의 관측 드리프트
# (0.63%)의 8배 여유 — 이 밴드 안은 렌더에서 하한 아래로 내려갈 수 있다.
THIN_BAND = 1.05


# ---------------------------------------------------------------- 대비 산술

def contrast_floor(pt, bold):
    """대비 하한의 **단일 진리원** — G16-CONTRAST(정적)와 G14-C(픽셀)가 함께 쓴다.

    WCAG 2.x 1.4.3 large-text 정의를 그대로 따른다: 18pt 이상, 또는 14pt 이상이면서
    볼드일 때만 대형 텍스트로 보고 3:1, 그 외에는 4.5:1.

    W4 7단계 이전에는 `pt >= 14 or (pt >= 10.5 and bold)`라는 자체 완화값을 썼다
    (두 갈래 모두 WCAG보다 느슨). 교정 근거·영향 실측은
    `/mnt/d/bookforge-verify/report/dualfloor-diff.md` — 출하 9권 전수 재스캔에서
    신규 FAIL은 business 2권의 accent #C2662E 10.5pt bold on white(4.01) 2건뿐이며,
    그 조판(styles/business/theme.typ `bf-exec-open`)은 같은 단계에서 수리했다.

    tocgate.py(G14-C)는 이 함수를 import해 쓴다 — 값 복제 금지. 두 게이트가 다른
    수를 내면 사전 게이트(렌더 전 FAIL 앞당기기)의 존재 이유가 무너진다.
    """
    return 3.0 if (pt >= 18 or (pt >= 14 and bold)) else 4.5


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


# ------------------------------------------------------------------- 색상각

def is_chromatic(rgb):
    """유채색 판정. tocgate.py:39 `_is_colored`와 같은 식·같은 임계."""
    return max(rgb) - min(rgb) > MIN_CHROMA


def hue_deg(rgb):
    """HLS 색상각(0~360). tocgate.py:44 `_hue`와 같은 산식(colorsys)."""
    return colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)[0] * 360


def hue_dist(a, b):
    """원형 거리. tocgate.py:49 `_hue_dist`와 동일."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


# ------------------------------------------------------- $key_label 결정론 파생

def derive_key_label(key_rgb, bg_rgb, pt, bold, step=0.004):
    """key를 **명도만** 단계적으로 낮춰 bg 위 대비가 하한을 처음 넘는 색.

    hue·채도를 보존하는 이유는 둘이다 — 브랜드 정체성이 라벨에서 유지되고,
    G16-BRAND ③ hue 정합이 파생 때문에 깨지지 않는다(색상각이 그대로다).
    밝은 배경에서 대비는 명도에 단조이므로 첫 통과값이 곧 최소 변형이다.

    목표를 하한이 아니라 하한×THIN_BAND로 잡는다 — 하한을 갓 넘긴 값으로 파생하면
    렌더 후 G14-C가 픽셀에서 재실측할 때 드리프트만으로 다시 미달이 될 수 있다.
    드리프트를 파생 단계에서 흡수해야 두 게이트가 같은 결론에 선다.
    """
    floor = contrast_floor(pt, bold) * THIN_BAND
    h, l, s = colorsys.rgb_to_hls(*(c / 255.0 for c in key_rgb))
    for i in range(int(l / step) + 2):
        li = max(0.0, l - i * step)
        rgb = tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb(h, li, s))
        if contrast_ratio(rgb, bg_rgb) >= floor:
            return rgb
    return (0, 0, 0)   # 순흑으로도 못 넘는 배경 = 배경 자체가 결함(CONTRAST 축 소관)


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
def _resolve_value(val, ctx, depth=0, trace=None):
    if depth > 8:
        return ("nonliteral", f"var() 참조 깊이 8 초과: {val}")
    val = _strip_important(val.strip())
    # build_html.py의 치환부가 렌더 전에 꽂는 세 플레이스홀더 — 완전 재현 가능하다.
    ph = _placeholder_res(val, ctx, trace)
    if ph:
        return ph
    lit = _literal_res(val)
    if lit:
        return lit
    # var(--x, fallback)의 fallback 해석은 **의도적으로 하지 않는다** — 어느 쪽이
    # 쓰일지는 --x의 정의 여부에 달렸고 그건 캐스케이드 문맥이라 정적 증명이 아니다.
    m = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", val, re.I)
    if m:
        return _resolve_token(m.group(1), ctx, depth + 1, trace)
    return ("nonliteral", val)


def _placeholder_res(val, ctx, trace=None):
    """build_html.py가 치환하는 $플레이스홀더 3종. 리터럴이 아니면 None.

    trace는 "이 값이 브랜드에서 왔는가"를 기록한다 — G16-BRAND가 치환 지점만
    골라 검사하려면 해석 경로가 brand를 지나갔는지 알아야 한다.
    """
    if val not in ("$key_color", "$key_tint", "$key_label"):
        return None
    if trace is not None:
        trace.add("brand")
    if val == "$key_color":
        return _brand_res(ctx)
    if val == "$key_tint":
        return ("nonliteral", "rgba(brand, 0.08) — 알파")   # 알파 — 정적 대비 산출 불가
    return ctx.get("key_label_res") or _brand_res(ctx)


def _resolve_token(name, ctx, depth=0, trace=None):
    """토큰명 -> 색. 지원 형식:
      '--ink'      theme.css :root 변수(체인·$key_color 치환 포함)
      'brand'      book.json brand > tokens.brand_default
      'palette[3]' tokens.diagram.palette 슬롯
      '#1e7aad'    리터럴 hex
      '$key_label' build_html.py가 파생해 꽂는 값(brand을 명도만 낮춘 라벨색)
      '~...'       비리터럴 배경의 명시 선언(그라데이션·이미지) — 대비 산출 대상 아님
    """
    if not isinstance(name, str):
        return ("unresolved", f"{name!r}는 문자열이 아님")
    name = name.strip()
    if name.startswith("~"):
        return ("nonliteral", name[1:] or "declared-nonliteral")
    ph = _placeholder_res(name, ctx, trace)
    if ph:
        return ph
    lit = _literal_res(name)
    if lit:
        return lit
    if name == "brand":
        if trace is not None:
            trace.add("brand")
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
        return _resolve_value(raw, ctx, depth + 1, trace)
    return ("unresolved",
            f"{name!r}은 지원 형식(--토큰 | brand | $key_label | palette[n] | #hex | ~비리터럴) 밖")


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
    ctx = {
        "vars": css_root_vars(theme_text),
        "brand": res[1] if res[0] == "hex" else None,
        "brand_res": res,
        "brand_src": src,
        "brand_from_book": from_book,
        "brand_raw": str(raw),
        "palette": (tokens.get("diagram") or {}).get("palette") or [],
        # 파생 중 자기참조(key_label.bg에 $key_label을 적는 실수)로 무한재귀에 빠지지 않게
        # 먼저 자리를 막아 둔다.
        "key_label_res": ("unresolved", "key_label 파생 중 자기참조"),
    }
    ctx["key_label_res"] = _key_label_res(tokens, ctx)
    return ctx


def _key_label_res(tokens, ctx):
    """tokens.json `key_label` 계약대로 brand에서 라벨색을 파생한다.

    계약이 없는 스타일은 brand 그대로 — 파생은 "이 자리 대비가 하한에 못 미친다"는
    실측이 있는 스타일만 선언한다(magazine `.callout-title` 4.45).
    """
    base = ctx["brand_res"]
    spec = tokens.get("key_label")
    if base[0] != "hex" or not isinstance(spec, dict):
        return base       # brand 해석 실패 사유를 그대로 승계한다(오귀속 방지)
    bk, bv = _resolve_token(spec.get("bg"), ctx)
    if bk != "hex":
        return ("unresolved", f"key_label.bg={spec.get('bg')!r} 해석 불가 — {bv}")
    pt, bold = spec.get("pt"), spec.get("bold")
    if not isinstance(pt, (int, float)) or isinstance(pt, bool) or not isinstance(bold, bool):
        return ("unresolved", f"key_label.pt/bold 형식 오류 (pt={pt!r} bold={bold!r})")
    rgb = derive_key_label(parse_hex(base[1]), parse_hex(bv), pt, bold)
    return ("hex", "#%02x%02x%02x" % rgb)


def key_label_hex(tokens, theme_text, brand=None):
    """build_html.py의 치환부가 쓰는 공개 진입점 — 파생 진리원은 여기 하나뿐이다.

    파생 불가(브랜드가 색이 아님 등)면 None을 돌려 호출자가 폴백을 고르게 한다.
    """
    kind, val = _ctx(tokens, theme_text, brand)["key_label_res"]
    return val if kind == "hex" else None


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
        # 양방향 모두 **렌더가 실제로 쓰는 팔레트**로 대조한다 — render_diagrams.mjs:38이
        # `if (bookMeta.brand) palette[0] = bookMeta.brand`로 0번 슬롯을 치환하므로,
        # 브랜드를 준 책에서 tokens의 brand_default는 지면에도 도해에도 나타나지 않는
        # 죽은 값이고 그것을 CSS와 대조하면 양쪽 방향 모두 오탐이 난다.
        # HARD ②가 brand_default == palette[0]을 이미 못박으므로 브랜드 미지정 책에서는 항등.
        pal_res = list(pal)
        if ctx["brand"]:
            pal_res[0] = ctx["brand"]
        for i, c in enumerate(pal_res):
            h = norm_hex(c)
            if h and h not in css_hex:
                role = roles[i] if (isinstance(roles, list) and i < len(roles)) else None
                out.append(_f("SYNC", "WARN",
                              f"palette[{i}] {h} (role={role})이 theme.css 리터럴에 없음 — 도해 전용 슬롯"))
        pal_hex = {norm_hex(c) for c in pal_res if norm_hex(c)}
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


# ------------------------------------------------------------------ G16-BRAND

# base.typ:17이 `paper: white`를 기본값으로 주고 스타일이 재선언할 때만 바뀐다
# (essay/theme.typ:17 `paper: rgb("#FBFAF7")`). 정적으로 읽히는 건 이 리터럴 형태뿐이다.
_TYP_PAPER_RE = re.compile(r"paper\s*:\s*rgb\(\s*\"(#[0-9a-fA-F]{3,8})\"\s*\)")


def _typst_paper(style_dir):
    """typst 스타일의 지면 바탕색. 선언이 없으면 templates/base.typ:17 기본값 백색."""
    tp = Path(style_dir) / "theme.typ" if style_dir else None
    if tp and tp.exists():
        m = _TYP_PAPER_RE.search(tp.read_text(encoding="utf-8"))
        if m:
            return norm_hex(m.group(1)) or "#ffffff"
    return "#ffffff"


def _brand_sites(style, tokens, ctx, engine, style_dir):
    """브랜드가 **글자로** 치환되는 자리 목록 -> [(where, fg_hex, bg_hex, pt, bold)].

    fg는 브랜드 원값이 아니라 **그 자리에 실제로 꽂히는 해석 결과**다 —
    $key_label처럼 파생을 거치는 자리는 파생 후 값으로 판정해야 파생과 검사가
    다른 수를 내지 않는다.

    자리를 상상하지 않고 치환 코드에서 역산한다.
      (a) build_html.py의 `$key_color`/`$key_label` 치환 -> contrast_contract 중
          fg 해석 경로가 brand을 지나간 엔트리. 배경도 그 엔트리가 선언한 실제 배경이다.
      (b) render_diagrams.mjs:38 `if (bookMeta.brand) palette[0] = bookMeta.brand`
          -> palette_roles[0]가 "label"일 때만(글자용 슬롯일 때만) 검사한다.
          도해 SVG의 허용 배경은 팔레트 + 백색이고(:108) 실제 지면은 백색이다.
      (c) typst 4종: theme.typ:14류의 `rgb(meta.at("brand", ...))`가 accent로 쓰이지만
          정확한 사용 지점은 `.darken()`/`.transparentize()` 계산식이라 스캔 범위 밖이다.
          그래서 계약이 보장하는 최소치 — 지면 바탕 위 본문급 글자 — 로만 근사한다.
    """
    sites = {}
    brand_hex = ctx["brand_res"][1] if ctx["brand_res"][0] == "hex" else None

    def add(where, fg, bg, pt, bold):
        fg, bg = norm_hex(fg or ""), norm_hex(bg or "")
        if not fg or not bg:
            return
        key = (fg, bg, contrast_floor(pt, bold))
        if key in sites:
            sites[key][0].append(where)
        else:
            sites[key] = ([where], fg, bg, pt, bold)

    cc = tokens.get("contrast_contract")
    if isinstance(cc, dict):
        for i, e in enumerate(cc.get("entries") or []):
            if not isinstance(e, dict):
                continue
            pt, bold = e.get("pt"), bool(e.get("bold"))
            if not isinstance(pt, (int, float)) or isinstance(pt, bool):
                continue
            trace = set()
            fk, fv = _resolve_token(e.get("fg"), ctx, trace=trace)
            if "brand" not in trace or fk != "hex":
                continue   # 브랜드 무관이거나 알파 전경 — 후자는 G14-C 소관
            bk, bv = _resolve_token(e.get("bg"), ctx)
            if bk != "hex":
                continue   # 알파·그라데이션 배경은 정적 증명 불가(G14-C 소관)
            add(e.get("where", f"entries[{i}]"), fv, bv, pt, bold)

    dg = tokens.get("diagram") or {}
    roles = dg.get("palette_roles")
    if ctx["brand_from_book"] and isinstance(roles, list) and roles and roles[0] == "label":
        mf = dg.get("minFontPt")
        if isinstance(mf, (int, float)) and not isinstance(mf, bool):
            add("도해 라벨 palette[0] (render_diagrams.mjs:38 치환)", brand_hex, "#ffffff", mf, False)

    if engine != "html":
        pt = tokens.get("body_pt")
        if isinstance(pt, (int, float)) and not isinstance(pt, bool):
            add("typst accent 근사 — 지면 바탕 위 본문급 글자 (정확한 치환 지점은 스캔 범위 밖)",
                brand_hex, _typst_paper(style_dir), pt, False)

    return [(" / ".join(w), fg, bg, pt, bold) for w, fg, bg, pt, bold in sites.values()]


def _hue_companions(tokens):
    """브랜드와 한 지면에서 공존하는 **고정** 유채색(색상각 목록).

    출처는 diagram.palette의 0번을 뺀 슬롯이다 — 0번만 브랜드로 치환되고(:38)
    나머지는 어떤 책에서도 고정이며, alienColors(:108)가 도해 색을 이 집합으로
    강제하므로 "브랜드와 반드시 함께 놓이는 색"의 정의가 코드로 보장된다.
    insight는 palette[1] #14577d가 곧 목차 1레벨 고정색 `--blue-800`이라
    G14-B가 실제로 비교하는 그 색이 여기 그대로 들어온다.
    무채색 슬롯은 색상각이 의미를 갖지 않으므로 제외한다.
    """
    pal = (tokens.get("diagram") or {}).get("palette") or []
    out = []
    for c in pal[1:]:
        rgb = parse_hex(c or "")
        if rgb and is_chromatic(rgb):
            out.append((norm_hex(c), hue_deg(rgb)))
    return out


def g16_brand(style, tokens, theme_text, brand=None, style_dir=None):
    """브랜드 입력 사전 검증 3종 — 형식 · 치환 지점 대비 · 고정 동반색과의 hue 정합.

    강도는 값 출처가 정한다: book.json.brand 위반은 FAIL(무검증 치환 구멍 봉쇄),
    brand_default 위반은 WARN(출하 부채 — 어떤 책도 잠그지 않는다).
    """
    out = []
    ctx = _ctx(tokens, theme_text, brand)
    src, raw = ctx["brand_src"], ctx["brand_raw"]
    sev = "FAIL" if ctx["brand_from_book"] else "WARN"
    engine = tokens.get("engine", "typst")
    sd = Path(style_dir) if style_dir else (SKILL / "styles" / style)

    # ---- ① 형식 ----
    kind, val = ctx["brand_res"]
    if kind == "unresolved":
        # 색이 아닌 값(`navy` 같은 CSS 색이름 포함)은 $key_color 치환 결과가 CSS에서
        # 조용히 무효가 되거나 build_html의 hex 산술을 터뜨린다.
        # 사유 문자열은 해석기가 출처를 지목해 이미 만들어 둔다 — 여기서 다시 붙이면 중복된다.
        out.append(_f("BRAND", sev if raw.strip() else "WARN",
                      f"{val}. 허용 형식은 #hex 3/4/6/8자리 또는 rgb()/rgba()"))
        return out
    if kind != "hex":
        # 반투명 브랜드는 렌더는 되지만 배경 합성 없이는 대비·hue가 성립하지 않는다.
        out.append(_f("BRAND", "WARN",
                      f"{val}. 대비·hue 축은 배경 합성이 필요해 N/A(G14-C 소관)"))
        return out
    rgb = parse_hex(val)

    # ---- ② 치환 지점 대비 ----
    for where, fg, bg, pt, bold in _brand_sites(style, tokens, ctx, engine, sd):
        ratio = contrast_ratio(parse_hex(fg), parse_hex(bg))
        floor = contrast_floor(pt, bold)
        derived = "" if fg == val else f"→{fg}"   # $key_label 파생을 거친 자리
        tag = f"{src}={val}{derived} on {bg} = {ratio:.2f}"
        note = f"({pt}pt{'/bold' if bold else ''}) @ {where}"
        if ratio < floor:
            out.append(_f("BRAND", sev, f"{tag} < {floor} {note}"))
        elif ratio < floor * THIN_BAND:
            # 렌더 샘플값은 토큰값과 최대 0.63% 어긋난다 — 하한을 갓 넘긴 값은
            # 렌더 후 G14-C에서 뒤집힐 수 있으므로 통과시키되 표시한다.
            out.append(_f("BRAND", "WARN", f"{tag} 여유 얇음 (하한 {floor} 대비 +{ratio - floor:.2f}) {note}"))

    # ---- ③ 고정 동반색과의 hue 정합 ----
    companions = _hue_companions(tokens)
    if not is_chromatic(rgb):
        # 무채색 근처는 HLS 색상각이 잡음이다(회색의 hue는 채널 반올림이 정한다).
        # 검사를 건너뛰되 침묵하지 않는다 — G14-B도 `_is_colored` 밖 색은 비교하지 않으므로
        # 사전·사후 판정이 같은 이유로 같이 침묵한다는 사실을 기록으로 남긴다.
        out.append(_f("BRAND", "WARN",
                      f"{src}={val} 채도 {max(rgb) - min(rgb)} ≤ {MIN_CHROMA} — 무채색이라 "
                      f"hue 정합 축 N/A (G14-B도 같은 임계로 비교 대상에서 뺀다)"))
    elif companions:
        h = hue_deg(rgb)
        near = min(companions, key=lambda c: hue_dist(h, c[1]))
        d = hue_dist(h, near[1])
        if d > HUE_TOL_DEG:
            out.append(_f("BRAND", sev,
                          f"{src}={val} (hue {h:.0f}°)가 고정 동반색 계열 밖 — 가장 가까운 "
                          f"{near[0]} (hue {near[1]:.0f}°)와 Δ{d:.0f}° > {HUE_TOL_DEG}°. "
                          f"이대로 두면 2-pass 렌더를 다 지불한 뒤 G14-B에서 죽는다"))
    # companions가 비면(무채색 팔레트) 비교 대상이 없다 — 침묵한다. 없는 계약을
    # 매 빌드 WARN으로 알리면 4스타일이 영구 소음이 된다.
    return out


# ------------------------------------------------------------------ 러너/도구

def style_inputs(style, skill=SKILL):
    """스타일 팩에서 (tokens, theme_text)를 읽는다. theme.css가 없으면 None."""
    sd = Path(skill) / "styles" / style
    tokens = json.loads((sd / "tokens.json").read_text(encoding="utf-8"))
    css = sd / "theme.css"
    return tokens, (css.read_text(encoding="utf-8") if css.exists() else None)


def run(style, tokens, theme_text, brand=None, style_dir=None):
    """세 축을 한 번에. build.py·qc_gate.py가 공유하는 단일 진입점.

    style_dir는 engine↔팩 실물 대조(HARD ⓪)와 typst 지면색 판독에 쓰이며,
    생략하면 SKILL/styles/<style>.
    """
    return {
        "G16-SYNC": g16_sync(style, tokens, theme_text, brand, style_dir),
        "G16-CONTRAST": g16_contrast(style, tokens, theme_text, brand),
        "G16-BRAND": g16_brand(style, tokens, theme_text, brand, style_dir),
    }


def fails_of(findings):
    return [f for f in findings if f["level"] == "FAIL"]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 scripts/g16_tokens.py <style> [brand]")
    style = sys.argv[1]
    # 2번째 인자는 book.json.brand를 흉내 낸다 — 브랜드 입력 검증을 책 하나 짓지 않고
    # 확인할 수 있어야 한다. 생략하면 팩의 brand_default(=출하 기본)를 본다.
    brand = sys.argv[2] if len(sys.argv) > 2 else None
    if not (SKILL / "styles" / style).exists():
        sys.exit(f"unknown style: {style}")
    tokens, css = style_inputs(style)
    res = run(style, tokens, css, brand)
    nf = nw = 0
    print(f"G16-TOKENS  style={style}  engine={tokens.get('engine', 'typst')}  "
          f"theme.css={'있음' if css else '없음'}  "
          f"brand={brand or tokens.get('brand_default')}"
          f"{'' if brand else ' (brand_default)'}")
    for axis in ("G16-SYNC", "G16-CONTRAST", "G16-BRAND"):
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
