# 도해 계약 (정본) — AntV Infographic DSL 사이드카

본문 도해는 **직접 SVG를 그리지 않고** AntV Infographic DSL로 선언한다. 빌드(P1.5)가
DSL을 프리렌더해 `assets/fig-NN.svg`를 만들고, 텍스트를 조판 엔진이 읽을 수 있는
네이티브 `<text>`로 변환한다(fo2text). 이유: AntV 원본 출력은 텍스트가
`<foreignObject>`라 Typst(usvg)에서 **에러 없이 텍스트만 전멸**한다.

## 파일 3점 세트 (이름 일치 강제)

```
<book_dir>/diagrams/fig-01.json      ← 콘텐츠가 작성 (DSL 사이드카)
<book_dir>/assets/fig-01.svg         ← 빌드 산출 (직접 만들지 않는다)
<book_dir>/assets/fig-01.labels.json ← 빌드 산출 (G13 대조 정본)
chapters/ch-NN.md 안: ![캡션](../assets/fig-01.svg "출처: …")   ← 단독 문단
```

## 사이드카 스키마

```json
{
  "bf": { "width": "full", "icons": false },
  "dsl": [
    "infographic sequence-ascending-steps",
    "data",
    "  title 단계 제목",
    "  sequences",
    "    - label 1단계",
    "      desc 설명 문장",
    "    - label 2단계"
  ]
}
```

- `dsl`: 문자열 또는 줄 배열. 첫 줄은 반드시 `infographic <template-name>`.
  템플릿 문법은 infographic-creator 스킬(~/.claude/skills/infographic-creator)이 정본.
- `bf.width`: `full`(기본) | `twothirds`. 도해 내 최소 글자 크기 검사의 물리 폭 기준.
- `bf.icons`: 기본 `false`. `true`는 HTML 트랙 스타일(insight·magazine)에서만 허용되며
  **네트워크가 필요**하다(아이콘 API). 렌더러가 요청 아이콘 수와 SVG `<symbol>` 수를
  대조해 조용한 탈락을 차단한다. `false`면 DSL의 `icon` 줄을 자동 제거한다.

## 스타일이 강제하는 것 (콘텐츠가 지정해도 덮어쓴다)

- **팔레트**: `styles/<style>/tokens.json`의 `diagram.palette`. DSL의 `theme` 블록은
  빌드가 제거·재작성한다. `book.json`의 `brand`가 있으면 강조색(1번)만 교체.
- **최소 글자 크기**: `diagram.minFontPt`(전 스타일 8pt). `bf.width` 물리 폭으로 환산해
  위반 시 렌더가 실패한다 — 대응은 라벨 축약 또는 항목 수 축소(글자 확대 아님).
- **폰트**: Pretendard 고정 (fo2text가 실측·방출).

## 금지 사항

- **회전·세로쓰기 라벨 금지** — fo2text가 감지 시 즉시 실패한다.
- **템플릿명 오타 주의** — AntV는 미지 템플릿을 조용히 기본형으로 폴백하지만,
  빌드가 설치본 카탈로그(276종)로 실명 검증해 미지명은 즉시 실패시킨다.
- **라벨 겹침** — SSR 박스 계산과 Pretendard 실폭의 차이로 긴 라벨이 이웃 텍스트를
  덮으면 변환기가 감지해 실패한다. 대응은 라벨 축약(글자 확대 아님).
- 산출 `assets/fig-NN.svg` 수동 편집 금지 — 첫 줄 해시가 어긋나도 캐시가 남는다.
  수정은 항상 사이드카 DSL에서, 재빌드로만.
- 도해로 수치를 새로 만들지 않는다 — 본문에 실재하는 수치·주장만 시각화 (G10 정신).
- magazine 목차 이미지맵은 장의 첫 이미지를 쓴다 — 장 첫 이미지가 도해면 사진 컷을
  먼저 배치할 것 (도해는 `<img>` 썸네일로 어울리지 않는다).

## 템플릿 선택 지침 (전량 목록은 infographic-creator 스킬)

| 정보 구조 | 템플릿 계열 |
|---|---|
| 병렬 요점 | `list-column-*` `list-grid-*` |
| 순서·단계 | `sequence-ascending-steps` `sequence-timeline-*` `sequence-roadmap-vertical-*` |
| 비교·SWOT | `compare-binary-*` `compare-swot` |
| 계층·트리 | `hierarchy-tree-*` `hierarchy-mindmap-*` |
| 수치 추이 | `chart-line-plain-text` `chart-bar-plain-text` (본문 실재 수치만) |

판형이 좁은 스타일(essay 78mm)은 가로형 템플릿(`list-row-*`, 가로 타임라인)을 피하고
세로형(`list-column-*`, `sequence-roadmap-vertical-*`)을 쓴다.

## 캐시와 오프라인

산출 SVG 첫 줄 `<!--bf:dsl=sha256:…-->`가 DSL+옵션 해시다. 일치하면 프리렌더를
건너뛰므로 **재빌드는 네트워크 없이 재현**된다(아이콘 API 재접근 불필요).
DSL·팔레트·변환기 버전이 바뀌면 자동 재렌더.

## 게이트

- **G0 (렌더 전)**: foreignObject 잔존 / `<text>` 부재 / 외부 참조(CDN) / 이미지 문단에
  텍스트 혼합 / 참조 SVG 부재 / icons:true인데 symbol 0.
- **G13 (렌더 후)**: `fig-NN.labels.json`의 렌더 줄 단위 라벨이 PDF 실텍스트에 존재.
- 실패 대응: `typeset/diagcheck/fig-NN.diff.png`(변환 자기검증 차분)를 먼저 본다.
