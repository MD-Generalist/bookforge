# 스타일 팩 추가·수정 가이드 (메인테이너용)

## 스타일 팩 계약

`styles/<이름>/`에 다음을 둔다:

| 파일 | 역할 |
|---|---|
| `STYLE.md` | 디자인 규칙서(수치 포함). 집필 톤·지면 문법의 단일 진실 원천 |
| `tokens.json` | `engine`(typst\|html), `trim_mm`(G1이 PDF 실측과 ±0.5mm 대조 — 테마 하드코딩과 어긋나면 FAIL), `length_pages`, `brand_default`, `fonts`(스타일이 실제 쓰는 동봉 패밀리 목록), `body_frame_mm`(pagemetrics 판면 정본), `diagram`(팔레트·minFontPt·widths) |
| `theme.typ` | (typst 엔진) 테마 구현 |
| `theme.html` + `theme.css` | (html 엔진) 페이지 골격 + 인쇄 스타일시트 |
| `decorate.py` | (html 엔진, 선택) 렌더 후 PyMuPDF 러닝 장식 스탬핑 |

## Typst 테마 계약

`theme.typ`는 `templates/base.typ`(빌드 시 같은 폴더로 스냅샷됨)를 `#import "base.typ"`로 가져오고, 다음 심볼을 반드시 export한다 — 생성되는 main.typ과 md 변환 결과가 이 이름들을 호출한다:

`meta`(= `json("meta.json")`) · `theme-tokens` · `TT` · `book(meta:, tokens:, cover:, toc:, body)` · `make-cover(meta)` · `colophon(meta, t)` · `bf-chapter(title, summary:)` · `bf-callout(kind:, title:, body)` · `bf-stat(value, label)` · `bf-fig(path, caption:, source:, width:)`

base의 `book()`을 그대로 쓰거나(practical처럼 토큰만 교체), 완전히 대체할 수 있다(essay·business·academic처럼). base가 제공하는 부품: `default-tokens`, `keep-words`(제목 어절 단위 줄바꿈 우회 — Typst는 keep-all 미지원), `full-bleed`, `chapter-state`, `numpad`.

주의: 문단 간격을 0으로 쓰는 스타일은 `list/enum spacing`과 블록 above/below를 반드시 명시하라 — 기본값 상속 시 줄겹침이 난다.

## HTML 테마 계약

`theme.html`은 python `string.Template` — `$title $subtitle $author $date $brand $cover_art $toc $body $css` + `$tocmap`(magazine 목차 이미지 맵) `$backquote`(뒤표지 인용) 플레이스홀더. `$` 문자를 리터럴로 쓰려면 `$$`. css 쪽 플레이스홀더는 `$fonts_dir $key_color $key_tint`.

`theme.css`엔 `$fonts_dir`(폰트 폴더 file:// URI), `$key_color`, `$key_tint`가 주입된다. 규칙:

- `@page { size: <trim>mm; margin: ... }` + 풀페이지 섹션(표지·목차)용 `@page full { margin: 0 }` — 해당 섹션에 `page: full; width/height = trim` 지정. 네거티브 마진으로 판형을 흉내내지 말 것(깨진다).
- 목차 쪽번호는 빌더가 2-pass로 주입 — 장 오프너에 `<span class="pgmark">@@chNN@@</span>` 마커와 목차에 `<span class="tocpg" data-mk="chNN">00</span>`을 유지할 것.
- 러닝 장식(폴리오·바·세로 러닝헤드)은 CSS 마진박스보다 `decorate.py` 스탬핑이 정확하다: `decorate(doc, ctx)` — `ctx = {book, pages(마커→쪽), fonts_dir}`. 페이지별 생략 규칙을 코드로 구현.
- 폰트는 전부 로컬 `@font-face`(assets/fonts). 웹 CDN 금지 — 결정론 훼손.

## 검증 루프

수정 후엔 반드시 스모크 북으로 실렌더한다:

```bash
python3 scripts/scaffold.py /tmp/smoke --style <이름> --title "스모크" --length short
# outline·chapters에 표·코드·콜아웃·리스트가 다 들어간 짧은 검증 콘텐츠를 넣고
python3 scripts/build.py /tmp/smoke && python3 scripts/contact_sheet.py /tmp/smoke/draft/book.pdf /tmp/smoke/qc --dpi 85
```

렌더 PNG를 눈으로 확인하기 전까지 완료가 아니다.
