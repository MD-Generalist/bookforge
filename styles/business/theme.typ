// bookforge style: business — 비즈니스·컨설팅 리포트 (STYLE.md: 200×280, navy 시스템)
#import "base.typ": default-tokens, keep-words, numpad, chapter-state, full-bleed
#import "base.typ" as base
#let code-font = ((name: "DejaVu Sans Mono", covers: regex("[A-Za-z0-9]")), "Pretendard")

#let meta = json("meta.json")

#let navy-900 = rgb("#0A1E38")
#let navy-700 = rgb("#123A63")
#let navy-500 = rgb("#2E7CB8")
#let navy-300 = rgb("#7FB2D9")
#let navy-100 = rgb("#D8E4EF")
#let teal-600 = rgb("#0E6E62")
#let accent   = rgb(meta.at("brand", default: "#C2662E"))
#let alert-c  = rgb("#B3261E")
#let ink      = rgb("#1A1D21")
#let ink-60   = rgb("#5A6169")
#let ink-30   = rgb("#9AA5B1")
#let rule-c   = rgb("#D5D9DE")
#let paper-alt = rgb("#F4F6F8")

// content → 평문 (목차 Executive Summary 판별용)
#let plain-text(c) = {
  if type(c) == str { c }
  else if type(c) != content { "" }
  else if c.func() == text { c.text }
  else if c.has("children") { c.children.map(plain-text).join("") }
  else if c.has("body") { plain-text(c.body) }
  else if c.func() == smartquote { "'" }
  else { " " }
}

#let theme-tokens = default-tokens + (
  trim: (w: 200mm, h: 280mm),
  // 본문 5컬럼 132.5mm + 바깥 마진 컬럼 22.5mm(+거터 5mm) 확보
  margin: (top: 28mm, bottom: 30mm, left: 20mm, right: 47.5mm),
  brand: navy-700, brand-light: navy-100,
  ink: ink, muted: ink-60, paper: white,
  body-font: ("Pretendard",), sans-font: ("Pretendard",),
  display-font: ("Pretendard",),
  stat-font: ("Gmarket Sans",),
  quote-font: ("Noto Serif KR",),
  body-size: 10.5pt, body-leading: 0.62em,
)

#let TT = theme-tokens

// ---- cover: navy + vector data-mesh pattern (상단 40%) -----------------------
#let cover-pattern(w, h) = {
  // 결정론적 데이터 메시: 사선 + 노드
  for i in range(12) {
    let x = w * i / 11
    place(top + left, dx: x, dy: 0mm,
      line(end: (w * 0.35, h), stroke: 0.4pt + navy-500.transparentize(72%)))
  }
  for i in range(9) {
    let x = w * (i + 1) / 10
    let y = h * calc.rem(i * 37, 83) / 83
    place(top + left, dx: x, dy: y, circle(radius: 1.1mm, fill: navy-300.transparentize(55%)))
  }
}

#let make-cover(meta) = {
  page(margin: 0mm, header: none, footer: none, fill: navy-900, {
    set par(justify: false, first-line-indent: 0em)
    block(width: 100%, height: 40%, clip: true, cover-pattern(200mm, 112mm))
    place(top + left, dx: 20mm, dy: 20mm, rect(width: 24mm, height: 4mm, fill: accent))
    block(width: 100%, inset: (x: 20mm), {
      set text(fill: white, font: TT.display-font)
      v(14mm)  // 제목 블록 ≈ 상단 96mm 지점
      text(size: 8pt, tracking: 0.06em, fill: navy-300,
        upper(meta.at("series", default: "BOOKFORGE INSIGHT REPORT")))
      v(6mm)
      text(size: 34pt, weight: "extrabold", tracking: -0.025em, keep-words(meta.title))
      if meta.at("subtitle", default: none) != none {
        v(6mm)
        text(size: 15pt, weight: "regular", fill: navy-100, keep-words(meta.subtitle))
      }
      v(12mm)
      line(length: 100%, stroke: 0.6pt + navy-500.transparentize(40%))
      v(1fr)
    })
    place(bottom + left, dx: 20mm, dy: -18mm, {
      set text(size: 8pt, fill: navy-100, font: TT.sans-font)
      [#meta.at("author", default: "bookforge") · #meta.at("date", default: "") · #meta.at("series_no", default: "REPORT 01")]
    })
  })
}

// ---- 도비라: navy 풀블리드 + 96pt 장번호 + accent 룰 --------------------------
#let biz-opener(n, title, summary, t) = {
  full-bleed(t, block(fill: navy-900, width: 100%, height: 100%, inset: (x: 20mm, y: 28mm), {
    set text(fill: white, font: t.display-font)
    set par(justify: false, first-line-indent: 0em)
    v(10mm)
    text(size: 76pt, weight: "extrabold", tracking: -0.03em, fill: navy-300, numpad(n))
    v(6mm)
    text(size: 27pt, weight: "extrabold", tracking: -0.02em, keep-words(title))
    v(12mm)
    rect(width: 40mm, height: 3pt, fill: accent)
    if summary != none {
      v(6mm)
      set text(size: 11pt, weight: "regular", fill: navy-100)
      set par(leading: 0.7em, justify: false)
      block(width: 82%, summary)
    }
  }))
}

#let biz-tbl = counter("biz-tbl")
#let bf-chapter(title, summary: none) = {
  biz-tbl.update(0)
  base.chapter(title, summary: summary, t: TT, opener: biz-opener)
}

// ---- 키 스탯: accent 상단 룰 + Gmarket 숫자 ---------------------------------
#let bf-stat(value, label) = {
  block(breakable: false, width: 50mm, {
    rect(width: 100%, height: 2pt, fill: accent)
    v(3mm)
    text(font: TT.stat-font, weight: "bold", size: 34pt, tracking: -0.03em,
      fill: navy-900, value)
    v(2mm)
    text(font: TT.sans-font, size: 9pt, fill: ink-60, label)
  })
}

// ---- 콜아웃: 인사이트 박스 / 인용 박스 / alert ------------------------------
#let bf-callout(kind: "info", title: none, body) = {
  if kind == "quote" {
    block(breakable: false, inset: (left: 6mm),
      stroke: (left: 3pt + navy-500), {
        set text(font: TT.quote-font, size: 13pt, fill: navy-900)
        set par(leading: 0.62em, first-line-indent: 0em)
        body
      })
  } else {
    let label = if title != none { title } else if kind == "warn" { "유의" } else { "시사점" }
    let lc = if kind == "warn" { alert-c } else { navy-700 }
    block(
      width: 100%, breakable: false,
      fill: paper-alt, stroke: 0.5pt + navy-100, inset: 6mm,
      {
        text(font: TT.sans-font, size: 8pt, tracking: 0.06em, weight: "bold", fill: lc, upper(label))
        v(2.5mm)
        set text(size: 9.5pt)
        set par(leading: 0.6em, spacing: 0.8em)
        body
      })
  }
}

#let bf-fig(path, caption: none, source: none, width: 100%) = {
  block(breakable: false, {
    if caption != none {
      text(font: TT.sans-font, size: 11pt, weight: "semibold", fill: ink, caption)
      v(2.5mm)
    }
    image(path, width: width)
    if source != none {
      v(3mm)
      text(font: TT.sans-font, size: 7.5pt, fill: ink-60, [자료: #source])
    }
  })
}

// 표: 콘텐츠 [표] 캡션 계약 — 캡션이 실재할 때만 <표 n-m> 라벨, 출처는 콘텐츠가 준 것만
#let bf-tbl(caption: none, source: none, body) = block(breakable: false, above: 6mm, below: 6mm, width: 100%, {
  if caption != none {
    context {
      biz-tbl.step()
      let n = chapter-state.get().num
      let m = biz-tbl.get().first() + 1
      text(font: TT.sans-font, size: 9pt, weight: "bold", fill: navy-700,
        "<표 " + str(n) + "-" + str(m) + ">")
      h(0.5em)
      text(font: TT.sans-font, size: 9.5pt, weight: "semibold", fill: ink, caption)
    }
    v(2mm)
  }
  body
  if source != none {
    v(2mm)
    text(font: TT.sans-font, size: 7.5pt, fill: ink-60, [자료: #source])
  }
})

#let colophon(meta, t) = {
  pagebreak(weak: true)
  page(header: none, footer: none, background: none, {  // 판권면: 러닝·섹션 탭 생략
    set text(size: 8pt, fill: ink-60)
    set par(first-line-indent: 0em)
    v(1fr)
    line(length: 40%, stroke: 0.4pt + rule-c)
    v(4pt)
    [#meta.title · #meta.at("author", default: "bookforge") · #meta.at("date", default: "") 발행 · bookforge로 조판]
    linebreak()
    [본 보고서의 수치·인용은 본문 표기 출처를 따르며, 무단 전재를 금합니다.]
  })
}

// ---- 마스터 래퍼 -------------------------------------------------------------
#let book(meta: (:), tokens: (:), cover: none, toc: true, toc-title: "차례", body) = {
  let t = TT
  set document(title: meta.at("title", default: "무제"), author: meta.at("author", default: "bookforge"))
  set page(
    width: t.trim.w, height: t.trim.h,
    margin: (top: t.margin.top, bottom: t.margin.bottom, left: t.margin.left, right: t.margin.right),
    header: context {
      let prev = query(heading.where(level: 1).before(here()))
      if prev.len() > 0 {
        set text(font: t.sans-font, size: 8pt, tracking: 0.06em, fill: ink-60)
        prev.last().body
        h(1fr)
        meta.at("title", default: "")
        v(2mm)
        line(length: 100%, stroke: 0.4pt + rule-c)
      }
    },
    footer: context align(right,
      text(font: t.sans-font, size: 9pt, weight: "medium", fill: navy-700,
        str(counter(page).get().first()))),
    background: context {
      // 섹션 탭: 현재 장 번호 기준 세로 바
      let n = chapter-state.get().num
      if n > 0 {
        place(top + right, dx: -2mm, dy: 28mm + (n - 1) * 26mm,
          rect(width: 6mm, height: 24mm, fill: navy-500, {
            align(center + horizon, text(font: t.sans-font, size: 8pt, weight: "bold",
              fill: white, numpad(n)))
          }))
      }
    },
  )
  set text(font: t.body-font, size: t.body-size, fill: ink, lang: "ko", region: "KR")
  set text(costs: (orphan: 100%, widow: 100%, runt: 200%))
  set par(justify: true, leading: t.body-leading, spacing: 1.0em, first-line-indent: 0em)

  // 절/항: 액션 타이틀 문법 — 강제 개면 금지(흐름 배치), 개면은 H1만
  show heading.where(level: 2): it => {
    v(1.8em, weak: true)
    block(sticky: true, {
      text(font: t.sans-font, size: 16pt, weight: "bold", tracking: -0.01em, fill: navy-900, it.body)
      v(2.2mm)
      line(length: 100%, stroke: 0.8pt + navy-700)
    })
    v(1.1em, weak: true)
  }
  show heading.where(level: 3): it => {
    v(1.5em, weak: true)
    block(sticky: true, text(font: t.sans-font, size: 12pt, weight: "semibold", fill: navy-700, it.body))
    v(0.6em, weak: true)
  }
  set heading(numbering: none)

  show quote.where(block: true): it => bf-callout(kind: "quote")[#it.body]
  set list(marker: ([•], [–]), indent: 5mm, spacing: 0.7em, body-indent: 3mm)
  set enum(indent: 5mm, spacing: 0.7em, body-indent: 3mm)
  show list: set block(above: 1em, below: 1em)
  show enum: set block(above: 1em, below: 1em)
  set text(number-type: "lining", number-width: "tabular")
  show raw.where(block: true): it => block(
    width: 100%, fill: paper-alt, inset: 5mm, stroke: 0.5pt + navy-100,
    text(font: code-font, size: 8.5pt, it))

  // 표: 세로 괘선·얼룩말 금지, navy 상하 굵은 룰
  set table(stroke: none, inset: (x: 3mm, y: 2.6mm), fill: none)
  show table: it => {
    set text(size: 9pt, font: t.sans-font)
    block(breakable: false, {
      it
    })
  }
  set table(stroke: (x, y) => (
    top: if y == 0 { 1.2pt + navy-900 } else if y == 1 { 0.6pt + navy-700 } else { 0.4pt + rule-c },
    bottom: 1.2pt + navy-900,
  ))
  show table.cell.where(y: 0): it => text(weight: "semibold", fill: navy-900, it)
  show table.cell: set align(left + horizon)
  show link: it => text(fill: navy-500, it)
  show figure.caption: it => text(font: t.sans-font, size: 8pt, fill: ink-60, it)

  if cover != none { cover }
  // 리포트형: 속표지 생략, 목차 1면 완결 (STYLE.md「목차 문법」)
  //  - 좌측 22.5mm 컬럼 장번호 / 우측 5컬럼 장제목 + 절제목 리스트
  //  - 점선 리더 금지, 쪽번호 우측 정렬 tabular, 위계는 장·절 2단계까지
  //  - 최상단 Executive Summary는 장번호 없이 별도 행
  if toc {
    // 한 행 = 제목(1fr) + 쪽번호(우측 정렬). 리더 없음.
    let toc-row(body, pnum, t-size, p-size, t-fill, p-fill, t-weight, t-font) = grid(
      columns: (1fr, 11mm), column-gutter: 3mm,
      align: (left + top, right + top),
      text(font: t-font, size: t-size, weight: t-weight, tracking: -0.01em, fill: t-fill, body),
      {
        // 쪽번호를 제목 베이스라인에 맞춰 내림(급수 차 보정)
        v((t-size - p-size) * 0.88)
        text(font: t.sans-font, size: p-size, weight: "medium", fill: p-fill, str(pnum))
      },
    )

    // 항목 전체 렌더 — 간격/급수는 tier로 주입(1면 완결을 위한 적응 축소)
    let toc-body(entries, ch-gap, sec-gap, ch-size, sec-size, num-size) = {
      // 간격은 오직 v()로만 — 블록 자동 간격 제거(1면 예산 계산의 전제)
      set par(justify: false, first-line-indent: 0em, leading: 0.42em, spacing: 0em)
      set block(spacing: 0em)
      for (i, e) in entries.enumerate() {
        if i > 0 { v(ch-gap) }
        block(breakable: false, width: 100%, grid(
          columns: (22.5mm, 1fr),
          {
            // 장번호 01 / ES는 번호 없이 accent 마커
            if e.num == none {
              v(ch-size * 0.5)
              rect(width: 12mm, height: 2pt, fill: accent)
            } else {
              text(font: t.display-font, size: num-size, weight: "extrabold",
                tracking: -0.02em, fill: navy-300, numpad(e.num))
            }
          },
          {
            link(e.loc, toc-row(e.title, e.page, ch-size, ch-size * 0.7,
              navy-900, navy-700, "semibold", t.sans-font))
            if e.secs.len() > 0 {
              v(sec-gap * 0.9)
              for (j, s) in e.secs.enumerate() {
                if j > 0 { v(sec-gap) }
                link(s.loc, toc-row(s.title, s.page, sec-size, sec-size,
                  ink-60, ink-60, "regular", t.body-font))
              }
            }
          },
        ))
        // ES 블록은 본장과 헤어라인으로 분리
        if e.num == none {
          v(ch-gap * 0.6)
          line(length: 100%, stroke: 0.4pt + rule-c)
        }
      }
    }

    let toc-head = {
      set par(spacing: 0em)
      set block(spacing: 0em)
      text(font: t.sans-font, size: 8pt, tracking: 0.06em, weight: "bold", fill: accent, "CONTENTS")
      v(3mm)
      text(font: t.display-font, size: 20pt, weight: "extrabold", tracking: -0.02em,
        fill: navy-900, toc-title)
      v(4mm)
      line(length: 100%, stroke: 1.2pt + navy-900)
      v(8mm)
    }

    // 넉넉한 사양치부터 시도해 1면에 들어가는 첫 tier 채택
    let tiers = (
      (ch: 12mm,  sec: 6mm,   chs: 15pt,   secs: 10.5pt, num: 24pt),
      (ch: 10mm,  sec: 5mm,   chs: 14.5pt, secs: 10pt,   num: 22pt),
      (ch: 8mm,   sec: 4.2mm, chs: 14pt,   secs: 9.5pt,  num: 21pt),
      (ch: 6.5mm, sec: 3.4mm, chs: 13pt,   secs: 9pt,    num: 19pt),
      (ch: 6.0mm, sec: 3.1mm, chs: 12.5pt, secs: 8.8pt,  num: 18pt),
      (ch: 5.2mm, sec: 2.8mm, chs: 12pt,   secs: 8.5pt,  num: 17pt),
      (ch: 4.2mm, sec: 2.2mm, chs: 11.5pt, secs: 8.2pt,  num: 16pt),
      (ch: 3.4mm, sec: 1.7mm, chs: 11pt,   secs: 8pt,    num: 15pt),
      (ch: 2.8mm, sec: 1.2mm, chs: 10.5pt, secs: 7.6pt,  num: 14pt),
    )

    // 목차 면은 6컬럼 전폭(160mm)을 쓴다 — 바깥 마진 컬럼 해제
    page(
      margin: (top: t.margin.top, bottom: t.margin.bottom,
        left: t.margin.left, right: t.margin.left),
      header: none, footer: none, background: none,
      context {
        let w = t.trim.w - t.margin.left * 2
        let avail = t.trim.h - t.margin.top - t.margin.bottom

        // 장·절 수집 (2단계까지, 항 제외)
        let hs = query(heading).filter(h => h.level <= 2 and h.outlined)
        let entries = ()
        for h in hs {
          let p = counter(page).at(h.location()).first()
          if h.level == 1 {
            entries.push((
              num: entries.len() + 1, title: h.body,
              page: p, loc: h.location(), secs: (),
            ))
          } else if entries.len() > 0 {
            let last = entries.pop()
            last.secs.push((title: h.body, page: p, loc: h.location()))
            entries.push(last)
          }
        }
        // 1장이 Executive Summary면 번호 없는 별도 행으로
        if entries.len() > 0 {
          let head-title = lower(plain-text(entries.first().title))
          if head-title.contains("executive summary") or head-title.contains("요약") {
            let first = entries.first()
            first.num = none
            entries.at(0) = first
          }
        }

        let hh = measure(block(width: w, toc-head)).height
        let budget = avail - hh - 4mm
        let fits(tier) = measure(block(width: w,
          toc-body(entries, tier.ch, tier.sec, tier.chs, tier.secs, tier.num))).height
        let pick = tiers.last()
        for tier in tiers {
          if fits(tier) <= budget { pick = tier; break }
        }
        // 남은 여백은 장 사이 간격으로 되돌린다(사양치 12mm 상한)
        let slack = budget - fits(pick)
        let gaps = calc.max(entries.len() - 1, 1)
        let ch-gap = calc.min(pick.ch + slack / gaps, 12mm)

        toc-head
        toc-body(entries, ch-gap, pick.sec, pick.chs, pick.secs, pick.num)
      },
    )
  }
  counter(page).update(1)
  body
}
