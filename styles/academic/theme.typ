// bookforge style: academic — 학술·논문형 (STYLE.md: 신국판 153×225, 1도+먹)
#import "base.typ": default-tokens, keep-words, chapter-state
#import "base.typ" as base

#let meta = json("meta.json")

#let accent = rgb(meta.at("brand", default: "#12395F"))
#let accent-tint = rgb("#E8EDF3")
#let ink = rgb("#1A1A1A")
#let muted = rgb("#6E6E6E")
#let rule-c = rgb("#2E2E2E")

#let theme-tokens = default-tokens + (
  trim: (w: 153mm, h: 225mm),
  margin: (top: 26mm, bottom: 34.9mm, left: 25mm, right: 22mm),
  brand: accent, brand-light: accent-tint,
  ink: ink, muted: muted, paper: white,
  body-font: ("Libertinus Serif", "Noto Serif KR"),
  sans-font: ("Pretendard",),
  display-font: ("Pretendard",),
  body-size: 10pt,
)

#let TT = theme-tokens

// ---- 표지: 이중 룰 표제 블록, 타이포 전용 ------------------------------------
#let make-cover(meta) = {
  page(header: none, footer: none, {
    set par(justify: false, first-line-indent: 0em)
    v(48mm - 26mm)
    line(length: 100%, stroke: 1.2pt + accent)
    v(9mm)
    align(center, {
      text(font: TT.display-font, weight: "semibold", size: 28pt, tracking: -0.02em,
        fill: ink, keep-words(meta.title))
    })
    v(9mm)
    line(length: 100%, stroke: 0.4pt + rule-c)
    if meta.at("subtitle", default: none) != none {
      v(7mm)
      align(center, text(font: ("Noto Serif KR",), size: 13pt, fill: ink, keep-words(meta.subtitle)))
    }
    v(16mm)
    align(center, text(font: TT.display-font, weight: "medium", size: 11.5pt, fill: ink,
      meta.at("author", default: "bookforge")))
    v(1fr)
    align(center, text(font: TT.display-font, weight: "medium", size: 9.5pt, fill: ink,
      meta.at("publisher", default: "bookforge")))
  })
}

// ---- 장 헤더: 도비라 별면 금지 — 같은 면에서 본문 시작 ------------------------
#let bf-chapter(title, summary: none) = {
  pagebreak(weak: true)
  chapter-state.update(s => (num: s.num + 1, title: title))
  counter(heading).step(level: 1)
  context {
    let n = chapter-state.get().num
    v(12mm)
    hide(block(height: 0pt, heading(level: 1, outlined: true, bookmarked: true, numbering: none, title)))
    v(-1.2em)
    text(font: TT.display-font, weight: "medium", size: 10pt, tracking: 0.15em,
      fill: accent, "제" + str(n) + "장")
    v(4mm)
    line(length: 18mm, stroke: 1pt + accent)
    v(7mm)
    text(font: TT.display-font, weight: "semibold", size: 20pt, fill: ink, keep-words(title))
    v(8mm)
    line(length: 100%, stroke: 1pt + ink)
    if summary != none {
      v(9mm)
      block({
        set text(font: ("Noto Serif KR",), size: 9.5pt, fill: muted)
        set par(leading: 6.5pt, first-line-indent: 0em, justify: true)
        summary
      })
    }
    v(12mm)
  }
}

// ---- 정의·정리 박스 ----------------------------------------------------------
#let bf-callout(kind: "info", title: none, body) = {
  let label = if title != none { title } else if kind == "warn" { "유의" } else { "정리" }
  block(
    width: 100%, breakable: false,
    fill: accent-tint, stroke: (left: 1.5pt + accent),
    inset: (x: 8pt, y: 6pt), above: 5mm, below: 5mm,
    {
      set text(size: 9.5pt)
      set par(leading: 6.5pt, first-line-indent: 0em)
      text(font: TT.sans-font, weight: "semibold", size: 9.5pt, fill: accent, label)
      h(1em)
      body
    })
}

#let bf-stat(value, label) = bf-callout(title: "수치")[#strong(value) — #label]

#let fig-counter = counter("bf-fig")

#let bf-fig(path, caption: none, source: none, width: 100%) = {
  block(breakable: false, above: 5mm, below: 5mm, {
    align(center, image(path, width: width))
    context {
      fig-counter.step()
      let n = chapter-state.get().num
      let f = fig-counter.get().first() + 1
      if caption != none {
        v(2mm)
        align(center, {
          set text(font: TT.sans-font, size: 8.5pt)
          text(weight: "semibold", fill: accent, "[그림 " + str(n) + "-" + str(f) + "] ")
          text(fill: ink, caption)
          if source != none { text(fill: muted)[ (자료: #source)] }
        })
      }
    }
  })
}

#let colophon(meta, t) = {
  pagebreak(weak: true)
  set text(font: TT.display-font, size: 8.5pt, fill: ink)
  set par(leading: 4.5pt, first-line-indent: 0em)
  v(1fr)
  meta.title
  if meta.at("subtitle", default: none) != none [ — #meta.subtitle]
  linebreak()
  [#meta.at("date", default: "") 발행 · 지은이 #meta.at("author", default: "bookforge")]
  linebreak()
  [조판 bookforge · 본문 Noto Serif KR·Libertinus Serif · 표제 Pretendard]
}

// ---- 마스터 래퍼 -------------------------------------------------------------
#let book(meta: (:), tokens: (:), cover: none, toc: true, toc-title: "차 례", body) = {
  let t = TT
  set document(title: meta.at("title", default: "무제"), author: meta.at("author", default: "bookforge"))
  set page(
    width: t.trim.w, height: t.trim.h,
    margin: (top: t.margin.top, bottom: t.margin.bottom, left: t.margin.left, right: t.margin.right),
    header: context {
      let prev = query(heading.where(level: 1).before(here()))
      // 장 시작 면(도비라)은 러닝헤드 생략
      let starts = query(heading.where(level: 1)).map(h => h.location().page())
      if prev.len() > 0 and not starts.contains(here().page()) {
        set text(font: t.sans-font, size: 8.5pt, weight: "medium", fill: ink)
        text(fill: accent, "제" + str(prev.len()) + "장")
        h(2em)
        prev.last().body
        h(1fr)
        text(fill: muted, meta.at("title", default: ""))
        v(1.5mm)
        line(length: 100%, stroke: 0.4pt + rule-c)
      }
    },
    footer: context align(center,
      text(font: t.sans-font, size: 9pt, fill: ink, str(counter(page).get().first()))),
  )
  // 행송 17.5pt 고정: top/bottom-edge 고정 + leading 7.5pt
  set text(font: t.body-font, size: 10pt, fill: ink, lang: "ko", region: "KR",
    top-edge: 0.8em, bottom-edge: -0.2em, hyphenate: false,
    number-type: "lining", number-width: "tabular")
  set par(justify: true, leading: 7.5pt, spacing: 7.5pt,
    first-line-indent: (amount: 1em, all: true))

  set heading(numbering: (..n) => {
    let p = n.pos()
    if p.len() >= 2 { p.slice(1).map(str).join(".") } else { none }
  })
  show heading.where(level: 2): it => {
    v(26.25pt, weak: true)
    block(text(font: t.sans-font, size: 11.5pt, weight: "semibold", fill: ink, {
      counter(heading).display((..n) => str(chapter-state.get().num) + "." + str(n.pos().at(1, default: 1)))
      h(1.5em)
      it.body
    }))
    v(8.75pt, weak: true)
  }
  show heading.where(level: 3): it => {
    v(17.5pt, weak: true)
    block(text(font: t.sans-font, size: 10.5pt, weight: "medium", fill: ink, it.body))
    v(5pt, weak: true)
  }

  show quote.where(block: true): it => block(
    inset: (left: 2em, right: 1em), above: 6mm, below: 6mm, {
      set text(size: 9.5pt)
      set par(leading: 6.5pt, first-line-indent: 0em)
      it.body
    })
  set list(indent: 1em, spacing: 7.5pt)
  set enum(indent: 1em, spacing: 7.5pt)
  show raw.where(block: true): it => block(
    width: 100%, fill: luma(248), inset: 8pt, above: 5mm, below: 5mm,
    text(size: 8.5pt, it))

  // 3선표(booktabs): 상하 1.0pt 먹, 헤더 아래 0.4pt
  set table(stroke: none, inset: (x: 8pt, y: 5pt))
  show table: it => { set text(size: 9pt, font: t.sans-font); it }
  set table(stroke: (x, y) => (
    top: if y == 0 { 1pt + ink } else if y == 1 { 0.4pt + rule-c } else { none },
    bottom: 1pt + ink,
  ))
  show table.cell.where(y: 0): it => text(weight: "semibold", it)
  show link: it => text(fill: accent, it)

  if cover != none { cover }
  // 속표지
  page(header: none, footer: none, {
    v(44mm)
    line(length: 100%, stroke: 0.4pt + rule-c)
    v(7mm)
    align(center, text(font: t.display-font, weight: "semibold", size: 20pt, keep-words(meta.title)))
    if meta.at("subtitle", default: none) != none {
      v(5mm)
      align(center, text(font: ("Noto Serif KR",), size: 11pt, meta.subtitle))
    }
    v(10mm)
    align(center, text(font: t.display-font, weight: "medium", size: 10pt, meta.at("author", default: "")))
  })
  if toc {
    page(header: none, footer: none, {
      v(24mm - 26mm + 4mm)
      text(font: t.display-font, weight: "semibold", size: 16pt, tracking: 1em, toc-title)
      v(10mm)
      line(length: 100%, stroke: 0.4pt + rule-c)
      v(6mm)
      show outline.entry.where(level: 1): it => {
        v(2.5mm, weak: true)
        link(it.element.location(), context {
          let n = query(heading.where(level: 1).before(it.element.location(), inclusive: true)).len()
          box(width: 14mm, text(font: t.sans-font, weight: "medium", size: 10.5pt, "제" + str(n) + "장"))
          text(font: t.sans-font, weight: "medium", size: 10.5pt, it.element.body)
          h(1fr)
          box(width: 9mm, align(right, text(size: 10pt, it.page())))
        })
      }
      outline(title: none, depth: 1)
    })
  }
  counter(page).update(1)
  body
}
