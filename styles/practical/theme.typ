// bookforge style: practical — 실용·활용서 (견본: NIA 핵심용어집 실측 기반)
// This file is snapshotted into <book>/typeset/_style/ next to base.typ + meta.json.
#import "base.typ": *
#let code-font = ((name: "DejaVu Sans Mono", covers: "latin-in-cjk"), "Pretendard")

#let meta = json("meta.json")

#let theme-tokens = default-tokens + (
  trim: (w: 153mm, h: 225mm),
  margin: (top: 20mm, bottom: 18mm, left: 17mm, right: 15mm),
  brand: rgb(meta.at("brand", default: "#1a5fb4")),
  brand-light: rgb(meta.at("brand_light", default: "#e8f0fa")),
  ink: rgb("#20242a"),
  muted: rgb("#6b7480"),
  body-font: ("Pretendard",),
  sans-font: ("Pretendard",),
  display-font: ("Pretendard",),
  body-size: 9.5pt,
  body-leading: 0.88em,
  heading2-size: 14pt,
  heading3-size: 10.5pt,
)

#let TT = theme-tokens

// ---- STYLE.md 컬러 토큰 (brand 계열만 주제색 교체, 나머지는 고정) -----------
#let c-brand = TT.brand
#let c-pale = TT.brand-light            // brand-pale  — 목차 필 바탕
#let c-deep = TT.brand.darken(30%)      // brand-deep  — 밝은 바탕 위 브랜드 글자
#let c-high = rgb("#BDD756")            // highlight   — 브랜드 색면 위 라벨 (고정)
#let c-rule = rgb("#D9DCDE")            // rule        — 점 리더·괘선 (고정)

// ---- cover: vector typography, solid brand ground + light rules ------------
#let make-cover(meta) = {
  let t = TT
  page(margin: 0mm, header: none, footer: none, fill: t.brand, {
    set par(justify: false, first-line-indent: 0em)
    block(width: 100%, height: 100%, inset: (x: 18mm, y: 22mm), {
      set text(fill: white, font: t.display-font)
      // series capsule: 백색 필 + 브랜드색 글자
      box(fill: white, radius: 20pt, inset: (x: 10pt, y: 5pt),
        text(size: 8.5pt, tracking: 0.12em, weight: "bold", fill: t.brand,
          meta.at("series", default: "BOOKFORGE LIBRARY")))
      v(12%)
      text(size: 54pt, weight: "black", tracking: -0.015em, keep-words(meta.title))
      if meta.at("subtitle", default: none) != none {
        v(10mm)
        rect(width: 26mm, height: 2.2mm, fill: white.transparentize(30%))
        v(6mm)
        text(size: 13.5pt, weight: "medium", fill: white.transparentize(12%), keep-words(meta.subtitle))
      }
      v(1fr)
      align(right, text(size: 10.5pt, weight: "semibold", fill: white,
        meta.at("publisher", default: meta.at("author", default: "bookforge"))))
    })
  })
}

// ---- chapter opener: full-bleed brand page, giant number --------------------
#let practical-opener(n, title, summary, t) = {
  full-bleed(t, block(fill: t.brand, width: 100%, height: 100%, inset: (x: 20mm, y: 24mm), {
    set text(fill: white, font: t.display-font)
    text(size: 9pt, tracking: 0.18em, weight: "semibold", fill: white.transparentize(30%), "CHAPTER")
    v(4pt)
    text(size: 70pt, weight: "black", numpad(n))
    v(1.6em)
    line(length: 34%, stroke: 1pt + white.transparentize(45%))
    v(1.4em)
    text(size: 22pt, weight: "bold", keep-words(title))
    if summary != none {
      v(2em)
      set text(size: 10pt, weight: "regular", fill: white.transparentize(12%))
      set par(leading: 0.95em, justify: false)
      block(width: 80%, summary)
    }
  }))
}

// ---- TOC: 파트 목차 1쪽 (STYLE.md「목차 문법」+ 2단 변형) --------------------
// 헤더 밴드 56mm(우하단 r12mm) → PART 배지 23×46mm(x 27, y 41.6) → 파트 제목
// → 장(H1) 행 20pt `[필 라벨][제목][점 리더][쪽번호]`
// → 절(H2) 행 16pt `[4mm 들여쓰기][제목][점 리더][쪽번호]`
// 항목이 판면 1단에 안 들어가면 판면 폭 2단(거터 11.8mm, 단 경계 0.3pt brand 룰)
#let toc-band-h = 56mm
#let toc-badge-x = 27mm
#let toc-badge-y = 41.6mm
#let toc-badge-w = 23mm
#let toc-badge-h = 46mm
#let toc-col-x = toc-badge-x + toc-badge-w + 6mm   // 배지 오른쪽 6mm
#let toc-row-h = 20pt        // 장 행
#let toc-sub-h = 16pt        // 절 행 (2단 변형 행간)
#let toc-gutter = 11.8mm     // 단 거터
#let toc-list-y = 91mm       // 배지 하단(87.6mm) 아래에서 목록 시작
#let toc-chip-w = 11.5mm

#let toc-part-badge(num) = block(
  width: toc-badge-w, height: toc-badge-h,
  fill: c-brand, radius: 3mm, stroke: none, inset: 0pt,
  {
    set align(center)
    set par(leading: 0em, spacing: 0em)
    v(8.2mm)
    text(font: TT.sans-font, size: 20pt, weight: "bold", tracking: 0.03em,
      fill: c-high, "PART")
    v(5.0mm)
    line(length: 16mm, stroke: 0.6pt + white)
    v(4.4mm)
    text(font: TT.display-font, size: 46pt, weight: "black", tracking: -0.045em,
      fill: white, num)
  })

// 한 행 = 한 줄 계약: 단 폭을 넘치는 제목만 그 행에서 축소(잘라내기·줄바꿈 금지)
#let toc-fit(body, avail, size, weight, fill) = context {
  let f = TT.sans-font
  let m = measure(text(font: f, size: size, weight: weight, body))
  let s = if m.width > avail and m.width > 0pt { size * (avail / m.width) } else { size }
  text(font: f, size: s, weight: weight, fill: fill, body)
}

// 점 리더 — 0.5pt 원점, 간격 2pt, rule
#let toc-leader(pad) = box(width: 1fr, inset: (x: pad),
  repeat(gap: 2pt, box(baseline: -0.85pt,
    circle(radius: 0.33pt, fill: c-rule, stroke: none))))

#let toc-pageno(loc, w, size, fill) = box(width: w, align(right,
  text(font: TT.sans-font, size: size, weight: "medium", fill: fill,
    number-width: "tabular", str(counter(page).at(loc).first()))))

// 장(H1) 행 — 필 라벨 + 제목 + 리더 + 쪽번호
#let toc-ch-row(n, hd, cw, t) = block(
  width: 100%, height: toc-row-h, above: 0pt, below: 0pt, spacing: 0pt, breakable: false,
  align(horizon, link(hd.location(), {
    box(width: toc-chip-w, height: 4.7mm, fill: c-pale, radius: 1mm, baseline: 1.35mm,
      align(center + horizon, text(font: TT.sans-font, size: 6.9pt, weight: "bold",
        fill: c-deep, tracking: 0.02em, number-width: "tabular", "CH│" + numpad(n))))
    h(3mm)
    toc-fit(hd.body, cw - toc-chip-w - 3mm - 2mm - 9mm, 9.5pt, "regular", t.ink)
    toc-leader(2mm)
    toc-pageno(hd.location(), 9mm, 10pt, t.ink)
  })))

// 절(H2) 행 — 필 라벨 없이 4mm 들여쓰기 + 제목 + 리더 + 쪽번호
#let toc-sub-row(hd, cw, t) = block(
  width: 100%, height: toc-sub-h, above: 0pt, below: 0pt, spacing: 0pt, breakable: false,
  align(horizon, link(hd.location(), {
    h(4mm)
    toc-fit(hd.body, cw - 4mm - 1.3mm - 5.6mm, 8.5pt, "light", t.ink)
    toc-leader(1.3mm)
    toc-pageno(hd.location(), 5.6mm, 8.5pt, t.muted)
  })))

#let practical-toc(meta, t, title: "차례") = {
  let col-w = t.trim.w - t.margin.right - toc-col-x
  let list-w = t.trim.w - t.margin.left - t.margin.right
  let cw = (list-w - toc-gutter) / 2
  page(header: none, footer: none, margin: 0mm, fill: t.paper, {
    set par(justify: false, first-line-indent: 0em)

    // ① 헤더 밴드 — 풀블리드, 우하단 모서리만 r12mm
    place(top + left, rect(width: t.trim.w, height: toc-band-h, fill: c-brand,
      stroke: none, radius: (bottom-right: 12mm)))
    place(top + left, dx: toc-badge-x, dy: 21.0mm,
      text(font: TT.sans-font, size: 8pt, weight: "bold", tracking: 0.26em,
        fill: c-high, "CONTENTS"))
    place(top + left, dx: toc-badge-x, dy: 25.9mm,
      text(font: TT.display-font, size: 23pt, weight: "black", tracking: -0.03em,
        fill: white, title))

    // ② PART 배지
    place(top + left, dx: toc-badge-x, dy: toc-badge-y, toc-part-badge("01"))

    // ③ 파트 제목 — 밴드 아래(배지는 밴드에서 내려온 탭)
    place(top + left, dx: toc-col-x, dy: toc-band-h + 3.4mm, block(width: col-w, {
      text(font: TT.display-font, size: 20.9pt, weight: "bold", tracking: -0.03em,
        fill: t.ink, keep-words(meta.title))
      if meta.at("subtitle", default: none) != none {
        v(2.2mm)
        text(font: TT.sans-font, size: 8.5pt, weight: "regular", fill: t.muted,
          keep-words(meta.subtitle))
      }
    }))

    // ④ 항목 — 장(H1) + 그에 속한 절(H2)을 한 그룹으로, 판면 폭에 배치
    context {
      let groups = ()
      for hd in query(heading).filter(hd => hd.level <= 2) {
        if hd.level == 1 { groups.push((ch: hd, subs: ())) }
        else if groups.len() > 0 {
          let g = groups.pop()
          g.subs.push(hd)
          groups.push(g)
        }
      }
      if groups.len() == 0 { return }
      let gh = groups.map(g => toc-row-h + g.subs.len() * toc-sub-h)
      let total = gh.fold(0pt, (a, b) => a + b)
      let avail = t.trim.h - t.margin.bottom - toc-list-y

      let draw(idxs, w) = {
        show link: it => text(fill: t.ink, it)     // 목차 글자에 별색 금지
        for i in idxs {
          block(breakable: false, above: 0pt, below: 0pt, spacing: 0pt, {
            toc-ch-row(i + 1, groups.at(i).ch, w, t)
            for s in groups.at(i).subs { toc-sub-row(s, w, t) }
          })
        }
      }

      if total > avail and groups.len() > 1 {
        // 2단 변형 — 그룹 단위 균형 분할
        let k = 1
        let bd = none
        let cum = 0pt
        for i in range(1, groups.len()) {
          cum = cum + gh.at(i - 1)
          let d = calc.abs((cum - total / 2).pt())
          if bd == none or d < bd { bd = d; k = i }
        }
        let h1 = gh.slice(0, k).fold(0pt, (a, b) => a + b)
        let h2 = gh.slice(k).fold(0pt, (a, b) => a + b)
        place(top + left, dx: t.margin.left, dy: toc-list-y,
          block(width: cw, draw(range(0, k), cw)))
        place(top + left, dx: t.margin.left + cw + toc-gutter, dy: toc-list-y,
          block(width: cw, draw(range(k, groups.len()), cw)))
        // 단 경계 세로 룰 — 0.3pt brand
        place(top + left, dx: t.margin.left + cw + toc-gutter / 2, dy: toc-list-y,
          line(angle: 90deg, length: calc.max(h1, h2), stroke: 0.3pt + c-brand))
      } else {
        place(top + left, dx: t.margin.left, dy: toc-list-y,
          block(width: list-w, draw(range(0, groups.len()), list-w)))
      }
    }
  })
}

// ---- 마스터 래퍼: base.book()에서 TOC만 교체 --------------------------------
#let book(meta: (:), tokens: (:), cover: none, toc: true, toc-title: "차례",
          toc-cols: 1, body) = {
  let t = merged(tokens)

  set document(title: meta.at("title", default: "무제"), author: meta.at("author", default: "bookforge"))
  set page(
    width: t.trim.w, height: t.trim.h,
    margin: (top: t.margin.top, bottom: t.margin.bottom, left: t.margin.left, right: t.margin.right),
    fill: t.paper,
    footer: context {
      let pn = counter(page).get().first()
      align(center, text(font: t.sans-font, size: 8pt, fill: t.muted, str(pn)))
    },
    header: context {
      let sel = heading.where(level: 1)
      let prev = query(sel.before(here()))
      if prev.len() > 0 {
        set text(font: t.sans-font, size: 7.5pt, fill: t.muted, tracking: 0.06em)
        prev.last().body
        h(1fr)
        text(fill: t.brand, meta.at("title", default: ""))
      }
    },
  )
  set text(font: t.body-font, size: t.body-size, fill: t.ink, lang: "ko", region: "KR")
  set text(costs: (orphan: 100%, widow: 100%, runt: 200%))
  set par(justify: true, leading: t.body-leading, spacing: 1.15em, first-line-indent: (amount: 1em, all: false))

  show heading.where(level: 2): it => {
    v(1.6em, weak: true)
    block(sticky: true, text(font: t.sans-font, size: t.heading2-size, weight: "bold", fill: t.ink, it.body))
    v(0.7em, weak: true)
  }
  show heading.where(level: 3): it => {
    v(1.2em, weak: true)
    block(sticky: true, {
      box(baseline: -0.12em, circle(radius: 2.2pt, fill: t.brand))
      h(6pt)
      text(font: t.sans-font, size: t.heading3-size, weight: "semibold", fill: t.ink, it.body)
    })
    v(0.5em, weak: true)
  }
  set heading(numbering: none)

  show quote.where(block: true): it => block(
    inset: (left: 1.2em, y: 0.3em),
    stroke: (left: 2pt + t.brand.transparentize(50%)),
    text(fill: t.ink.transparentize(15%), it.body))
  set list(marker: ([•], [–]), indent: 0.5em)
  set enum(indent: 0.5em)
  show raw.where(block: true): it => block(
    width: 100%, fill: luma(247), radius: 4pt, inset: 9pt, breakable: true,
    text(font: code-font, size: 8pt, it))
  show raw.where(block: false): it => box(fill: luma(243), radius: 2pt, inset: (x: 3pt, y: 1pt), text(font: code-font, size: 0.92em, it))
  set table(stroke: none, inset: (x: 7pt, y: 6pt))
  show table: it => {
    set text(size: 8.7pt, font: t.sans-font)
    it
  }
  show table.cell.where(y: 0): it => text(weight: "semibold", fill: white, it)
  set table(fill: (x, y) => if y == 0 { t.brand } else if calc.odd(y) { t.brand-light.transparentize(45%) } else { none })
  show figure.where(kind: table): set figure.caption(position: top)
  show figure.caption: it => text(font: t.sans-font, size: 8.5pt, fill: t.muted, it)
  show link: it => text(fill: t.brand, it)

  if cover != none { cover }
  title-page(meta, t)
  if toc { practical-toc(meta, t, title: toc-title) }
  counter(page).update(1)

  body
}

// ---- baked helpers for converter output ------------------------------------
#let bf-chapter(title, summary: none) = chapter(title, summary: summary, t: TT, opener: practical-opener)
#let bf-callout(kind: "info", title: none, body) = callout(kind: kind, title: title, t: TT, body)
#let bf-stat(value, label) = stat(value, label, t: TT)
#let bf-fig(path, caption: none, source: none, width: 100%) = bookfig(path, caption: caption, source: source, width: width, t: TT)
#let bf-tbl(caption: none, source: none, body) = bf-tbl-base(caption: caption, source: source, t: TT, body)
