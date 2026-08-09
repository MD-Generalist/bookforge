// bookforge style: practical — 실용·활용서 (견본: NIA 핵심용어집 실측 기반)
// This file is snapshotted into <book>/typeset/_style/ next to base.typ + meta.json.
#import "base.typ": *

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

// ---- baked helpers for converter output ------------------------------------
#let bf-chapter(title, summary: none) = chapter(title, summary: summary, t: TT, opener: practical-opener)
#let bf-callout(kind: "info", title: none, body) = callout(kind: kind, title: title, t: TT, body)
#let bf-stat(value, label) = stat(value, label, t: TT)
#let bf-fig(path, caption: none, source: none, width: 100%) = bookfig(path, caption: caption, source: source, width: width, t: TT)
