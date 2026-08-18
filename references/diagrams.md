# 도해 계약 (정본) — 사이드카 2트랙 (antv DSL / authored SVG)

본문 도해는 두 트랙 중 하나로 만든다: ① **antv** — 인포그래픽형 요점 시각화는 AntV
Infographic DSL로 선언(직접 그리지 않음), ② **authored** — 기술도해(시퀀스·상태머신·
ER·스위밍레인 등 AntV 미커버 11계열)는 에이전트가 SVG를 직접 그린다(§authored 트랙).
양쪽 다 빌드(P1.5)가 정규화해 `assets/fig-NN.svg` + `labels.json`을 산출한다.
antv 트랙의 핵심 우회: AntV 원본 출력은 텍스트가 `<foreignObject>`라 Typst(usvg)에서
**에러 없이 텍스트만 전멸**하므로 네이티브 `<text>`로 변환한다(fo2text).

## 파일 3점 세트 (이름 일치 강제)

```
<book_dir>/diagrams/fig-01.json      ← 콘텐츠가 작성 (DSL 사이드카)
<book_dir>/assets/fig-01.svg         ← 빌드 산출 (직접 만들지 않는다)
<book_dir>/assets/fig-01.labels.json ← 빌드 산출 (G13 대조 정본)
<book_dir>/assets/fig-01.metrics.json ← 빌드 산출 (라벨 급수 실측 — 밴드 판정 근거)
chapters/ch-NN.md 안: ![캡션](../assets/fig-01.svg "출처: …")   ← 단독 문단
```

## 사이드카 스키마

```json
{
  "kind": "antv",
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

- `kind`: `"antv"`(기본 — 생략 가능) | `"authored"`. authored면 `dsl` 대신
  `diagrams/fig-NN.svg`(에이전트가 직접 그린 SVG 소스)가 입력이다 — 아래 §authored 트랙.
- `dsl`: (antv 전용) 문자열 또는 줄 배열. 첫 줄은 반드시 `infographic <template-name>`.
  템플릿 문법은 infographic-creator 스킬(~/.claude/skills/infographic-creator)이 정본.
- `bf.width`: `full`(기본) | `twothirds`. **지면에 실제로 앉는 폭이자** 도해 내 최소 글자 크기
  검사의 물리 폭 기준이다 — 둘은 같은 값이어야 하고, 그 값은 스타일 팩의
  `tokens.json diagram.widths.<키>`(mm) 하나뿐이다. HTML 트랙은 빌더가 `twothirds`를
  `<figure class="svgfig twothirds">`로 발행하고 theme.css가 `$fig_full_mm`·`$fig_twothirds_mm`
  치환으로 그 mm를 받는다(G16-SYNC widths 축이 배선을 HARD로 지킨다).
  Typst 트랙은 `md2typ.py`가 사이드카를 읽어 `#bf-fig(..., width: Nmm)`으로 같은 mm를 발행한다
  (`full`도 수치로 발행한다 — `bf-fig` 기본값 `width: 100%`를 그대로 두면 판면폭이 제1의
  진리원이 되고 tokens는 그것을 추정하는 제2의 값으로 남는다). 여기서도 같은 축이
  `widths.full == theme.typ 판면폭(trim.w − margin.left − margin.right)`을 HARD로 대조한다.
- `bf.icons`: 기본 `false`. `true`는 HTML 트랙 스타일(insight·magazine)에서만 허용되며
  **네트워크가 필요**하다(아이콘 API). 렌더러가 요청 아이콘 수와 SVG `<symbol>` 수를
  대조해 조용한 탈락을 차단한다. `false`면 DSL의 `icon` 줄을 자동 제거한다.

## 스타일이 강제하는 것 (콘텐츠가 지정해도 덮어쓴다)

- **팔레트**: `styles/<style>/tokens.json`의 `diagram.palette`. DSL의 `theme` 블록은
  빌드가 제거·재작성한다. `book.json`의 `brand`가 있으면 강조색(1번)만 교체.
- **라벨 급수 밴드**: 하한과 상한이 **다른 키·다른 강도**다.
  - 하한 `diagram.minFontPt`(전 스타일 8pt) — `bf.width` 물리 폭으로 환산해 위반 시
    렌더가 **실패(HARD)**한다. 대응은 라벨 축약 또는 항목 수 축소(글자 확대 아님).
  - 상한 `diagram.labelBand.maxRatio`(전 스타일 1.2) — 라벨 최대 pt가 `body_pt × maxRatio`를
    넘으면 **WARN**. 대응 방향이 하한과 정반대다: **라벨 font-size 축소 또는 viewBox 확대**
    (폭 확대·글자 확대는 위반을 키운다). 축척은 상·하한을 함께 옮기므로, 도해 내부
    최대/최소 활자비가 `(body_pt × maxRatio) ÷ minFontPt`를 넘으면 어떤 폭으로도 두 술어를
    동시에 만족할 수 없다 — 그때는 라벨 간 상대 급수를 좁혀야 한다(렌더러가 그 진단을 낸다).
  - **AntV DSL 트랙은 렌더러가 자동으로 맞춘다(6단계).** 사이드카를 고칠 필요가 없다 —
    빌드가 테마에 역할별 `font-size`(케밥 표기)를 주입해 title `body_pt×1.15` ·
    label/value `×1.0` · desc `×0.9`(단, `minFontPt×1.07` 하한)로 강제하고, 테마가 닿지
    않는 템플릿 하드코딩 급수(단계번호 배지 등)는 변환 전 원본 SVG에서 같은 밴드 안으로
    클램프한다. 급수만 줄이면 트림 폭이 함께 줄어 pt/u가 커지므로(= 글자는 안 줄고 도형만
    커진다) **폭 프레임을 무주입 실측값으로 고정**한다 — 도형은 지면에서 원래 크기 그대로이고
    글자만 줄며, 남는 폭은 오른쪽 여백이 된다(`metrics.labelScale.frameSlack`).
  - 도해마다 실측이 `assets/fig-NN.metrics.json`(급수 전량·min/max pt·본문 대비 비)으로 남는다.
    `labels.json` 스키마는 건드리지 않는다(G13 무영향).
  - `labelBand.maxRatio`·`body_pt` 중 하나라도 없으면 상한 검사가 꺼지고, **꺼졌다는 사실이
    WARN으로 출력된다** — 미선언이 위반보다 조용해서는 안 된다.
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
| 순서·단계 | `sequence-timeline-simple`(106mm 실측 11.7pt) — `sequence-ascending-steps`는 desc 없이 라벨만(8.35pt 경계) |
| 비교·SWOT | `compare-binary-*` `compare-swot` |
| 계층·트리 | `hierarchy-tree-*` `hierarchy-mindmap-*` |
| 수치 추이 | `chart-line-plain-text` `chart-bar-plain-text` (본문 실재 수치만) |

판형이 좁은 스타일(essay 78mm)은 가로형 템플릿(`list-row-*`, 가로 타임라인)을 피한다.
**106mm 실측에서 이미 불가 판정된 템플릿**(라벨이 8pt 하한 미달): `sequence-roadmap-vertical-*`
4.7pt · `sequence-snake-steps` 5.8pt · `list-grid-*` 계열 5.6~6.4pt(130mm 기준) — 더 좁은
판형에서는 당연히 더 불가. 세로 단계는 `sequence-timeline-simple`(세로 타임라인)을 쓴다.

## 캐시와 오프라인

산출 SVG 첫 줄 `<!--bf:dsl=sha256:…-->`가 DSL+옵션 해시다. 일치하면 프리렌더를
건너뛰므로 **재빌드는 네트워크 없이 재현**된다(아이콘 API 재접근 불필요).
DSL·팔레트·변환기 버전, 그리고 **판정 파라미터**(해당 폭의 실검사 `widthMm` ·
`minFontPt` · `labelBand` · `body_pt`)가 바뀌면 자동 재렌더 — 검사 기준이 바뀐 도해가 옛 캐시로
조용히 통과하는 일이 없다. DSL 트랙 해시에는 **라벨 급수 주입 정책**(역할별 배수·목표 pt)도
실린다. 이 정책은 authored 트랙 해시에 없으므로, 정책을 바꾸면 DSL 도해만 재렌더된다.

## 게이트

- **G0 (렌더 전)**: foreignObject 잔존 / `<text>` 부재 / 외부 참조(CDN) / 이미지 문단에
  텍스트 혼합 / 참조 SVG 부재 / icons:true인데 symbol 0.
- **G13 (렌더 후)**: `fig-NN.labels.json`의 렌더 줄 단위 라벨이 PDF 실텍스트에 존재.
- 실패 대응: `typeset/diagcheck/fig-NN.diff.png`(변환 자기검증 차분)를 먼저 본다.


---

## authored SVG 트랙 (v2) — 기술도해는 직접 그린다

AntV 카탈로그는 "인포그래픽형 요점 시각화"에 강하고, **UML 시퀀스·상태머신·ER·
스위밍레인·간트·레이더·벤·산점도·조직도·루프·권한 매트릭스** 같은 기술도해는 0건이다
(276종 접두어 실측). 이 11계열은 에이전트가 SVG를 직접 그려 `diagrams/fig-NN.svg`에
두고, 사이드카를 `{"kind":"authored","bf":{"width":...}}`로 선언한다.

### 파이프라인 (antv 트랙과 동일 산출 계약)

빌드(P1.5)가 소스를 Chromium 하네스에 실측 마운트해 정규화한다:
① 폰트는 **Pretendard로 강제 베이크**(font-family 속성 재작성 — 다른 지정은 조용히 교정)
② 렌더 실측 라벨 수집 → `labels.json` (G13 대조 정본 — antv와 동일)
③ 회전·전단 라벨 즉시 실패 ④ 텍스트 겹침 실측 감지 즉시 실패
⑤ 팔레트 강제: `tokens.diagram.palette` + 뉴트럴(무채색 램프) 밖 유채색 즉시 실패
⑥ 글자 하한(minFontPt) 검사(HARD) + 상한(labelBand.maxRatio) 판정(WARN) ⑦ 외부 참조(CDN·원격) 즉시 실패
⑧ 원본↔정규화 pixelmatch 자기검증 ⑨ `<!--bf:authored=sha256:…-->` 해시 캐시.

### viewBox 환산 규칙 (하한 미달의 90%가 여기서 발생)

렌더 pt = `font-size(u) × 폭mm × 2.835 ÷ viewBox폭(u)`. **viewBox 폭 상한 =
`폭mm × 2.835 × font-size ÷ 8pt`** — 예: full 106mm에 12u 라벨이면 viewBox 폭 ≤ 450u.
좁게 그리고 크게 라벨하라. 106mm면 viewBox 400~420이 안전 대역이다.

### 타입 라우팅 (무엇을 그릴 것인가)

| 보여줄 것 | 타입 | 트랙 |
|---|---|---|
| 시스템 구성요소 + 연결 | 아키텍처 | authored |
| 분기 있는 결정 논리 | 플로우차트 | authored |
| 행위자 간 시간순 메시지 | **시퀀스** | authored |
| 상태 + 전이 + 조건 | **상태머신** | authored |
| 엔티티 + 필드 + 관계 | **ER** | authored |
| 부서·역할 교차 프로세스(핸드오프) | **스위밍레인** | authored |
| 작업·단계의 일정 배치 | **간트** | authored |
| 다항목 정량 비교(3~5축) | 레이더 | authored |
| 집합 간 겹침 | 벤 | authored |
| 두 변수 분포·상관 | 산점도 | authored |
| 보고·소유·에스컬레이션 | 조직도 | authored |
| 순환·플라이휠 | 루프 | authored |
| 역할×자원 권한 표 | 매트릭스 | authored |
| 병렬 요점·순서 단계·비교·SWOT·트리·타임라인·계층·수치 추이 | (기존 표 참조) | antv |

### 커넥터 규칙 (authored 필수 — 위반은 시각 판정 반려 사유)

1. **직교(orthogonal) 커넥터만.** 대각선 금지. 꺾임은 반경 6~8u 라운드 엘보.
   직선 `<line>`은 두 끝점이 같은 x 또는 y를 공유할 때만.
2. **라벨은 커넥터에서 6~10u 띄운다.** 화살표 위에 앉히지 않는다 — 선이 보여야 추적된다.
3. **커넥터끼리 겹침 금지.** 교차가 불가피하면 점프(bridge) 처리, 평행 주행은 ≥12u 이격.
   커넥터가 쌓이면 레이아웃 실패 — 개요+상세 2장으로 분할하라.
4. **같은 변에 여러 커넥터가 닿으면 접점을 분산한다** — 변 길이 L에 N개면 `L·k/(N+1)`
   지점, 인접 접점 ≥12u.
5. **출발·도착이 아닌 박스 뒤를 통과하지 않는다.** 우회가 기하학적으로 불가한 경우만
   파선(`stroke-dasharray`)으로 "통과"임을 표시하고 라벨은 보이는 끝에 둔다.
6. **라벨이 다른 노드를 덮지 않는다** (정규화기의 렌더 실측 겹침 감지가 강제).

### 복잡도 예산 (초과분은 도해 분할로 — 축소 금지)

노드 ≤9 · 화살표 ≤12 · 강조색 요소 ≤2 · 시퀀스 라이프라인 ≤5 · 스위밍레인 ≤5 ·
ER 엔티티 ≤8 · 트리 깊이 ≤4 · 조직도 ≤12노드/깊이 4 · 레이어 ≤6 · 벤 ≤3원 ·
레이더 5축·5계열 · 바 ≤8 · 선 그래프 ≤5계열 · 간트 ≤12작업 · 산점도 ≤30점 ·
주석 콜아웃 ≤2. **예산을 넘기면 글자를 줄이는 게 아니라 도해를 나눈다.**

### 수치 규율

도해로 수치를 새로 만들지 않는다 — 본문에 실재하는 수치·주장만 시각화(G10 정신).
차트형(바·선·산점도·레이더)의 모든 수치는 같은 장 본문에 문장으로 실재해야 한다.

> 타입 분류·커넥터 규칙·복잡도 예산은 cathrynlavery/diagram-design(MIT, Copyright
> 2025 Cathryn Lavery)의 명세를 bookforge 파이프라인(한국어 조판·Pretendard·팔레트
> 토큰·게이트 체계)에 맞게 재서술한 것이다. 템플릿·코드는 가져오지 않았다(한글 미지원·
> 판형 하한 충돌 실측). 겹침 검사는 원본의 정적 기하 검사(verify-geometry) 대신
> 렌더 실측(Chromium)으로 대체 — 목적 동일, 검출력 상위.
