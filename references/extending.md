# 스타일 팩 추가·수정 가이드 (메인테이너용)

## 스타일 팩 계약

`styles/<이름>/`에 다음을 둔다:

| 파일 | 역할 |
|---|---|
| `STYLE.md` | 디자인 규칙서(수치 포함). 집필 톤·지면 문법의 단일 진실 원천 |
| `tokens.json` | `engine`(typst\|html), `trim_mm`(G1이 PDF 실측과 ±0.5mm 대조 — 테마 하드코딩과 어긋나면 FAIL), **`body_pt`**(테마가 선언한 본문 급수. G1-SCALE이 PDF 본문 최빈 pt와 ±0.3pt 대조 — 전역 축소 차단. **미선언 시 WARN만 나가고 그 스타일은 축소 검출 불가**이므로 새 팩은 반드시 넣을 것), `length_pages`, `brand_default`, `fonts`(스타일이 실제 쓰는 동봉 패밀리 목록), `body_frame_mm`(pagemetrics 판면 정본), **`front_frame_mm`**(선택 — 앞부속(표지·목차) 텍스트 봉투 `[top,right,bottom,left]`mm. 리스트면 앞부속 전 면 공통, 객체면 `{"cover": [...], "toc": [...]}`로 1면=표지·나머지=목차. G3-FIT이 이 프레임 밖 텍스트를 FAIL시킨다. 표지·목차는 `body_frame_mm`이 아니라 자체 padding·절대배치를 쓰므로 body_frame을 재사용할 수 없고, **미선언이면 그 스타일은 앞부속 프레임 검사가 WARN과 함께 생략**된다 — 값을 CSS에서 확정할 수 없는 스타일에 억지로 넣지 말 것. 값은 CSS 선언 좌표에서 글리프 오버행을 흡수한 봉투로 잡고, 근거와 실측 여유를 같은 파일의 `_front_frame_mm_note`에 남긴다. **선언값 타당성은 G16-SYNC가 렌더 전에 기계 검증한다**: 4원소 수치 배열 · 각 값 ≥ 0 · `좌+우 < trim_w` ∧ `상+하 < trim_h` · 객체형이면 `cover`·`toc` **둘 다** 필수(하나만 선언하거나 한쪽이 `null`이면 나머지 면의 축이 경고 없이 전부 꺼지므로 HARD FAIL) — 전부 증명 가능한 모순이다. 프레임 면적이 지면의 95% 이상이면 축이 항등이 되므로 WARN(`[0,0,0,0]`이 그 형태), qc_gate도 같은 WARN을 리포트에 싣고 "선언은 있으나 검사한 면 0개"를 별도 WARN으로 남긴다 — **위조가 미선언보다 조용해서는 안 된다**), **`toc_levels`**(인쇄 목차에 노출하는 계층 수. 1이면 빌더가 절 엔트리도, `<h2>`의 `@@chNNsMM@@` 마커도, 레벨 2 북마크도 발행하지 않는다 — STYLE.md가 "계층 1단계까지만"을 선언한 스타일은 1로 둘 것. **미선언 시 2로 폴백**), **`toc_capacity`**(단면 목차 스타일 전용 — 아래 「단면 목차 팩」. TOCPAGE 블록이 없는 html 엔진 스타일이 이걸 선언하지 않으면 빌드가 `die()`), `diagram`(`palette`·**`palette_roles`**·minFontPt·widths — `palette_roles`는 `palette`와 병렬인 **필수** 배열로 슬롯별 역할(`label`\|`fill`\|`stroke`)을 선언한다. 부재·길이 불일치·허용값 밖은 G16-SYNC HARD FAIL — 옵셔널이면 새 스타일이 빼먹고 G16-BRAND가 조용히 무력화된다. 0번 슬롯은 `render_diagrams.mjs:38`이 `book.json.brand`로 덮어쓰는 브랜드 치환 슬롯이라 `label`이어야 브랜드 대비 검증이 성립한다), **`contrast_contract`**(선택 — 렌더 전 대비 계약. `{"enforce": bool, "entries": [{"fg":, "bg":, "pt":, "bold":, "where":}, ...]}` 형식. `fg`/`bg`는 hex 리터럴이 아니라 **토큰명**(`--css-var` \| `brand` \| `palette[n]` \| `$key_label` \| 리터럴 `#hex`)으로 적어 브랜드가 바뀌어도 계약이 썩지 않는다. 하한은 저장하지 않고 `pt`/`bold`에서 WCAG로 파생한다(`scripts/g16_tokens.py`의 `contrast_floor`가 단일 진리원 — G14-C와 공유). `enforce:true`인 스타일만 미달이 G16-CONTRAST **HARD FAIL**, 그 외(부재·`false`)는 WARN — typst 4종처럼 키 자체가 없으면 그 스타일은 이 축이 N/A로 빠진다(절대 FAIL 아님)), **`key_label`**(선택 — `$key_label` 플레이스홀더가 파생할 라벨색의 배경·급수 계약. `{"bg": "--토큰", "pt": N, "bold": bool}`. brand를 명도만 낮춰 그 배경 위 대비 하한(×1.05 여유)을 처음 넘는 색을 결정론 파생한다(`derive_key_label`) — hue·채도는 보존해 브랜드 정체성과 G16-BRAND hue 정합을 깨지 않는다. 미선언이면 brand 원색을 그대로 쓴다. 대비 실측이 있는 스타일만 선언할 것(magazine `.callout-title` 4.45가 근거)) |
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
- 목차 쪽번호는 빌더가 2-pass로 주입 — 장 오프너에 `<span class="pgmark">@@chNN@@</span>` 마커와 목차에 `<span class="tocpg" data-mk="chNN">00</span>`을 유지할 것. `toc_levels >= 2`면 절 마커 `@@chNNsMM@@`도 발행되므로 `<h2>`에 **`position: relative`가 필수**다 — 없으면 마커가 문서 원점(1면)에 붙어 모든 쪽번호가 어긋나고 사후조건은 충족된다.
- **`.tocpg` 칼럼 폭은 고정해야 한다.** pass 2에서 `00`이 실제 쪽번호로 바뀔 때 제목의 가용 폭이 변하면 경계 길이 제목이 접혀 면이 밀리고, 그 밀림은 pass 1 HTML 검사로 볼 수 없다(insight `flex: 0 0 6.5mm` = 3자리 실측폭 + 여유. 4자리 폴리오는 빌더가 `die()`).
- **다면 목차**(분량에 따라 목차 면 수가 늘어나는 스타일)는 `theme.html`의 목차 섹션 전체를 `<!--BF:TOCPAGE-->` … `<!--/BF:TOCPAGE-->`로 감싼다. 빌더가 `Template.substitute` **전에** 이 블록을 잘라내 N회 복제하고 각 복제본의 `$toc`→`$toc_i`, `$toc_mod`→`$toc_mod_i`로 치환한다. 2면 이후는 `$toc_mod = "toc-cont"`이므로 1면에만 두는 요소는 CSS에서 `.toc-page.toc-cont` 선택자로 감춘다. 목차 마크업·장식을 `decorate.py`로 옮기지 말 것 — 겹침 게이트가 스탬핑 가구를 면제하면 사고 지점이 통째로 검사 밖으로 나간다.
- 빌더는 `<book_dir>/typeset/tocplan.json`(면 수·면별 행 수·**예측 바닥 mm·실측 바닥 mm·렌더 배율·재계획 여부**·발행 절 마커 수·빌드 경고)을 남긴다. G4가 레벨 2 북마크 수를 이 파일의 `section_markers`와 대조하고, 빌드 경고를 게이트 리포트의 warns로 올린다. **html 엔진인데 이 파일이 없으면 G4가 FAIL**한다.
- **높이·폭 모델은 계획자일 뿐이고 `pass1.pdf`가 검증자다.** 빌더는 렌더 후 목차 면의 스팬 bbox로 실제 바닥(mm)을 재고, 전역 축소 배율(본문 최빈 pt / `body_pt`)로 원좌표를 복원한다. 물리 한계 초과면 **실측 접힘 실태로 1회 재계획하고 pass1을 다시 렌더**하며(결정론·최대 1회) 그래도 넘치면 `die()`. 미학 한계 초과·모델 이탈은 WARN으로 남는다. 추정 정확도만으로는 "조용한 넘침 → 문서 전역 축소" 계열을 닫을 수 없다는 것이 이 구조의 이유다.

### 단면 목차 팩 (TOCPAGE 블록이 없는 html 엔진 스타일)

목차를 스프레드 1면에 고정하는 스타일(magazine 계열)은 `tokens.json`에 **`toc_capacity`를 반드시 선언**한다. 선언이 없으면 빌드가 `die()`한다 — 구 구현은 `if style != "magazine": return`으로 **폴더 이름**이 방어선이어서, magazine 파생 팩을 하나 만들면 용량 검사가 조용히 사라지고 넘침이 전역 축소로 갔다.

```json
"toc_capacity": {
  "top_mm": 41.36,        // 첫 항목 제목 글리프 top
  "pitch_mm": 23.548,     // 항목 피치
  "tail_mm": 14.217,      // 마지막 항목 top → 콘텐츠 bottom
  "bottom_mm": 238.0,     // 콘텐츠 하단 = 재단높이 − padding-bottom
  "title_avail_mm": 75.0, // 제목 1행 가용 폭
  "font": "Paperlogy-7Bold", "size_pt": 22.0   // assets/fonts 파일명(확장자 제외)
}
```

값은 전부 `[실측]`이어야 한다(실렌더 PDF의 스팬 bbox). 빌더는 이 선언으로 ①제목이 1행에 들어가는지 ②예측 바닥이 `bottom_mm` 이하인지를 검사하고, 초과 시 상한 장 수와 대응 3종을 담아 `die()`한다. **`overflow:hidden`으로 잘라내거나 폰트·행간을 줄여 밀어 넣는 대응은 금지** — 잘린 목차는 어떤 게이트도 검출하지 못한다.

**접힘은 예산이 아니라 금지다.** `.toc li{flex-wrap:wrap}` 구조에서 제목이 1행을 넘으면 높이만 느는 게 아니라 정렬이 파손된다(실측: 제목 좌단이 쪽번호 칼럼보다 왼쪽으로 17mm 이탈, 쪽번호가 제목 위 독립 행으로 고아화). 근사 높이로 흡수하지 말고 `die()`할 것.
- **절 목록과 절 마커는 한 경로에서만 나온다.** `md_to_html(md, …, sec_marker="chNN", sec_titles_out=lst)`가 비콜아웃 청크를 렌더하는 그 자리에서 `<h2>`에 마커를 주입하고 주입한 제목을 순서대로 돌려준다. 원고를 줄 단위로 다시 스캔해 절 목록을 만들지 말 것 — 콜아웃 안 `## `(마커만 생김)·코드블록 안 `## `(목록만 생김)·리터럴 `<h2>`·`:::` 미종료가 전부 두 경로를 어긋나게 하고, 그 어긋남은 절 쪽번호와 레벨 2 북마크를 조용히 오배정한다. 빌더는 pass 1에서 `발행 마커 == 회수 마커`를 **양방향**으로 검사한다(단방향이면 잉여 마커가 통과한다).
- 러닝 장식(폴리오·바·세로 러닝헤드)은 CSS 마진박스보다 `decorate.py` 스탬핑이 정확하다: `decorate(doc, ctx)` — `ctx = {book, pages(마커→쪽), fonts_dir}`. 페이지별 생략 규칙을 코드로 구현.
- 폰트는 전부 로컬 `@font-face`(assets/fonts). 웹 CDN 금지 — 결정론 훼손.

## 검증 루프

수정 후엔 반드시 스모크 북으로 실렌더한다:

```bash
python3 scripts/scaffold.py /tmp/smoke --style <이름> --title "스모크" --length short
# outline·chapters에 표·코드·콜아웃·리스트가 다 들어간 짧은 검증 콘텐츠를 넣고
python3 scripts/build.py /tmp/smoke && python3 scripts/qc_gate.py /tmp/smoke
python3 scripts/contact_sheet.py /tmp/smoke/draft/book.pdf /tmp/smoke/qc --dpi 85
# 대비 계약 린터(G16-LINT)는 qc_gate가 자동으로 부른다. 축① 완전성은 qc_gate에서
# WARN이므로, **스타일 팩을 고친 뒤에는** 전 요소를 밟는 이 스모크 북에서 직접 돌려
# MISSING까지 0으로 만든다 — 그 축이 강제력을 갖는 자리가 여기다:
python3 tests/lint_contrast.py /tmp/smoke
python3 tests/mutations/run_mutations.py /tmp/smoke   # 게이트 감도 회귀
```

렌더 PNG를 눈으로 확인하기 전까지 완료가 아니다.

`contrast_contract`를 손댔다면 린터의 세 축이 각각 무엇을 잡는지 알고 볼 것:
① 완전성(theme.css 규칙 ↔ 계약 엔트리 양방향 diff) ② pt 정합(계약이 신고한 급수가
theme.css에 실재하는가 — pt는 `contrast_floor`의 입력이라 위조하면 계약이 스스로
하한을 낮춘다) ③ 값 커버리지(theme.css의 모든 `color:`/`background:` 리터럴이 어떤
엔트리에든 등장하는가 — 원고와 무관해 새 색의 조용한 추가를 잡는다).
②③과 유령 엔트리는 `qc_gate`가 `fails`로 올린다(HTML 엔진 한정, typst는 명시 skip).
