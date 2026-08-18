# bookforge

**One-line topic → commercial-book-quality ebook PDF.** An agent skill that runs on both Claude Code and OpenAI Codex.

[한국어](README.md)

bookforge produces PDFs with real book anatomy — cover, leader-dot TOC, chapter openers, running heads, colophon. Content is written in plain Markdown; typesetting is owned by six style packs and deterministic scripts; quality is physically enforced by QC gates — a PDF that fails the gates cannot exist in `final/`. Page breaking, filling, and intentional whitespace follow a pagination rulebook ([references/pagination.md](references/pagination.md)) distilled from measurements of commercial books; density gates catch both unjustified emptiness and forced filler.

**v2.0.0**: a new diagram track lets the agent author vector infographics and technical diagrams (sequence, state machine, ER, swimlane, and more) directly into the body copy; a new gate checks the TOC's self-consistency against the printed folios, chapter-opener color, and text contrast; and every bundled font is now TrueType, so Chromium's print-to-PDF path produces zero Type3 fallback glyphs. Details below.

*A demo video will be published as a v2.0.0 GitHub Release asset — the embed goes here once the release is live.*

## Nine examples — every one produced by this skill

Three of the six styles — `practical`, `insight`, `business` — now ship a second book where the diagram track is the whole point, for nine total. Click a cover to open the full PDF.

| | | |
|:---:|:---:|:---:|
| [![practical](examples/showcase/practical-prompt-patterns-cover.png)](examples/practical-prompt-patterns.pdf) | [![insight](examples/showcase/insight-ondevice-ai-cover.png)](examples/insight-ondevice-ai.pdf) | [![academic](examples/showcase/academic-game-theory-cover.png)](examples/academic-game-theory.pdf) |
| **practical** how-to book<br>*24 Prompt Patterns*, 45p | **insight** tech report<br>*On-Device AI 2026*, 28p | **academic** scholarly<br>*Foundations of Game Theory*, 36p |
| [![essay](examples/showcase/essay-evening-sentences-cover.png)](examples/essay-evening-sentences.pdf) | [![business](examples/showcase/business-sme-ai-cover.png)](examples/business-sme-ai.pdf) | [![magazine](examples/showcase/magazine-trend-brief-cover.png)](examples/magazine-trend-brief.pdf) |
| **essay** minimal prose<br>*Sentences on the Way Home*, 32p | **business** consulting paper<br>*SME AI Adoption Strategy*, 28p | **magazine** trend issue<br>*TREND BRIEF*, 25p |
| [![insight](examples/showcase/insight-agent-protocols-cover.png)](examples/insight-agent-protocols.pdf) | [![practical](examples/showcase/practical-home-server-cover.png)](examples/practical-home-server.pdf) | [![business](examples/showcase/business-automation-redesign-cover.png)](examples/business-automation-redesign.pdf) |
| **insight** diagram-led<br>*AI Agent Protocols 2026*, 32p | **practical** diagram-led<br>*My Own Home Server*, 39p | **business** diagram-led<br>*Business Automation, Redesigned*, 31p |

## The diagram track — v2's centerpiece

Body diagrams are declared by the agent as sidecar files and normalized/validated by the build — never hand-placed vectors. Two tracks:

1. **antv** — sequence, comparison, hierarchy, and trend-style visualizations are declared as AntV Infographic DSL in `diagrams/fig-NN.json`. The renderer runs server-side rendering from a bundle committed to the repo (`vendor/antv-ssr.bundle.mjs`, pinned `@antv/infographic` 0.2.19), then rewrites the raw output's `<foreignObject>` text into native `<text>` (fo2text) so Typst's usvg backend doesn't silently drop it.
2. **authored** — the 11 technical-diagram families AntV's catalog doesn't cover (sequence, state machine, ER, swimlane, Gantt, radar, Venn, scatter, org chart, loop, permission matrix) are drawn as SVG by the agent directly. A `diagrams/fig-NN.svg` plus a `{"kind":"authored"}` sidecar is enough — the build bakes the font, forces the palette, checks label overlap, and enforces an 8pt floor, emitting `assets/fig-NN.svg`. Connector rules, complexity budgets, and type routing follow [references/diagrams.md](references/diagrams.md), which absorbs and restates [cathrynlavery/diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT) for bookforge's Korean typesetting, Pretendard, palette tokens, and gate system (no templates or code were imported — measured incompatible with Korean text and narrow trims).

Both tracks are physically checked by G0 (pre-render SVG source) and G13 (post-render — every diagram label must exist as real PDF text). Below are authored SVGs pulled from the actual examples.

| insight — hierarchy | business — swimlane | practical — flowchart |
|:---:|:---:|:---:|
| ![](examples/showcase/insight-agent-protocols-page6.png) | ![](examples/showcase/business-automation-redesign-page9.png) | ![](examples/showcase/practical-home-server-page12.png) |

### TOC coherence (G14) is part of the same generation of work

A TOC whose printed page numbers drift from the real folios, or whose color family doesn't match the chapter openers, reads like it belongs to a different book. G14 scans every page for this self-consistency and a text-contrast floor — the two TOCs below are from books that actually passed it.

| insight — side band + folio | business — indicator + chapter number |
|:---:|:---:|
| ![](examples/showcase/insight-agent-protocols-toc.png) | ![](examples/showcase/business-automation-redesign-toc.png) |

## Interior preview

| practical — callouts + procedure | business — table evidence | magazine — image + pull quote |
|:---:|:---:|:---:|
| ![](examples/showcase/practical-prompt-patterns-page9.png) | ![](examples/showcase/business-sme-ai-page9.png) | ![](examples/showcase/magazine-trend-brief-page6.png) |

| academic — definition box + section hierarchy | essay — generous margins | insight — narrow measurement table |
|:---:|:---:|:---:|
| ![](examples/showcase/academic-game-theory-page11.png) | ![](examples/showcase/essay-evening-sentences-page6.png) | ![](examples/showcase/insight-ondevice-ai-page10.png) |

## The six style packs

Each style ships a design rulebook (`styles/*/STYLE.md`) distilled from measured commercial publications — trim size in mm, font sizes in pt, leading, color tokens, page templates, and hard prohibitions.

| Style | Identity | Trim | Engine |
|---|---|---|---|
| `practical` | IT how-to books. Prose sets low in a serif (Noto Serif KR); labels, controls, and numerals stand up in a grotesque (Pretendard) — the typeface itself splits "text you read" from "text you act on" | 153×225 | Typst |
| `insight` | Tech-trend research reports | 182×257 | HTML→Chromium |
| `academic` | Scholarly monographs (booktabs tables, numbered sections) | 153×225 | Typst |
| `essay` | Minimal literary prose (1-ink + 1 accent) | 128×188 | Typst |
| `business` | Consulting white papers (navy system, action titles, key stats) | 200×280 | Typst |
| `magazine` | Trend magazines (editorial grid, full-page pull quotes) | 200×265 | HTML→Chromium |

## Install

```bash
git clone https://github.com/gongnyang/bookforge.git
cd bookforge
ln -sfn "$PWD" ~/.claude/skills/bookforge   # Claude Code
ln -sfn "$PWD" ~/.codex/skills/bookforge    # Codex CLI
ln -sfn "$PWD" ~/.agents/skills/bookforge   # shared agents dir
```

Requirements (self-checked by the skill):

- **Typst 0.14.x** — `practical`, `academic`, `essay`, `business`
- **Python 3 + PyMuPDF + markdown-it-py** — conversion and QC gates (`pip install pymupdf markdown-it-py`)
- **A global Playwright + Chromium** — `insight`, `magazine`, **and any book that uses `diagrams/`** (diagram prerendering runs through the Chromium harness even for Typst-engine styles) — `npm i -g playwright && npx playwright install chromium`; the build resolves playwright from the **global** `npm root -g`, so a project-local install is not picked up
- **Only for books using `diagrams/`** — the renderer uses a bundle already committed to the repo (`vendor/antv-ssr.bundle.mjs`, pinned `@antv/infographic` 0.2.19). **No `npm ci` is needed** — it reproduces even if the npm registry disappears. Only run `npm ci && node vendor/build-bundle.mjs` inside the skill folder if the bundle is somehow lost

Five OFL fonts (Pretendard, Noto Serif KR, Paperlogy, Gmarket Sans, Barlow) ship as **TrueType (TTF) throughout** and render out of the box — Chromium's print-to-PDF path cannot subset CFF (.otf) outlines and silently falls back to Type3, redrawing every glyph as a per-page vector (measured: the same body text produces 19 Type3 objects from the OTF source versus 1 Type0 subset and 0 Type3 objects from the converted TTF). Gate G2 enforces zero Type3 objects as a hard condition — [notice](assets/fonts/LICENSES.md).

## Use

Just ask your agent:

```
"Make an ebook about on-device AI trends in the insight style"   ← topic mode
"Typeset this manuscript (draft.docx) as an essay collection"    ← manuscript mode
```

The skill detects the mode, picks a style and length, and carries the book through to the end. For a chapter that needs a diagram, drop a `diagrams/fig-NN.json` (antv) or `diagrams/fig-NN.svg` (authored) — the build step prerenders it automatically. Or drive it manually:

```bash
python3 scripts/scaffold.py mybook --style essay --title "Title" --length short
# write chapters/*.md + outline.json, then
python3 scripts/build.py mybook        # → draft/book.pdf (diagrams prerender here automatically)
python3 scripts/qc_gate.py mybook      # gates pass → final/mybook.pdf
```

## Quality gates

Only the gate script can create `final/`:

| Gate | Check |
|---|---|
| G0 | (pre-render) diagram SVG source — stray `foreignObject`, missing text, external references, non-standalone paragraphs, sidecar integrity, dropped icons |
| G1 | render succeeds + trim matches `tokens.trim_mm` + **body size matches `tokens.body_pt` — blocks whole-document shrink** + page count within preset range (WARN — hard only with `--strict-pages`) |
| G2 | every font fully embedded + **zero Type3 glyphs** |
| G3-OVERFLOW | zero bbox overflow (1.5pt tolerance) |
| G3-COLLIDE | zero text-line collisions on a page (per-column bands in multi-column styles) |
| G3-FIT | front-matter text stays inside the declared frame |
| G4 | TOC/bookmarks match actual chapter-start pages |
| G6 | visual inspection of the contact sheet — the agent looks at the rendered pages |
| G7 | density — frame drift, unintended blank pages, tail shortfall, mid-page gaps (reach/ink/gap) |
| G8 | detects "air-filled" pages — leading/tracking stretched to force a fill |
| G9 | orphaned titles / widows at page end (single-column styles) |
| G10 | (pre-render) every callout, quote, and stat number must exist in the chapter body — blocks fabrication |
| G11 | `pageroles.json` (intentional-whitespace reason codes) integrity |
| G12 | zero filler blank pages before a chapter start (no forcing recto starts — this is a single-sided ebook) |
| G13 | (post-render) every diagram label exists as real PDF text — catches silent text drops during SVG→PDF conversion |
| G14 | TOC/design coherence — A: printed TOC page numbers self-consistent with actual folios / B: TOC hue family matches chapter openers / C: colored text meets a WCAG contrast floor (3:1 large text, 4.5:1 otherwise) |
| G15 | page rhythm (`business` style only, enforced only where measurement supports it) — blocks paragraphs over 8 lines / caps consecutive body pages with no visual element |

Thresholds and remedies live in [references/pagination.md](references/pagination.md); the diagram-track authoring contract lives in [references/diagrams.md](references/diagrams.md).

## Structure

```
SKILL.md            router (mode detection → pipeline → sub-doc pointers)
modes/               topic.md · manuscript.md
styles/<6>/          STYLE.md (rulebook) + theme.typ|theme.css + tokens.json
templates/base.typ   shared Typst book primitives
vendor/              antv-ssr.bundle.mjs (committed AntV SSR bundle — offline reproducibility) + build-bundle.mjs
scripts/             scaffold · build · qc_gate · tocgate (G14) · contact_sheet · convert_fonts (TTF conversion) · fetch_fonts · ingest_docx
references/          generated-art policy · pagination rulebook · diagram contract (diagrams.md) · orchestration · style-pack extension guide
examples/            9 example PDFs + a 36-shot showcase
```

Generated art policy: cover/body art must be **text-free generated images**; all lettering is set as vectors by the layout layer, and books containing generated images say so in captions and the colophon.

## License

Code & docs: MIT. Bundled fonts: OFL 1.1 ([notice](assets/fonts/LICENSES.md)). The nine example PDFs are demo outputs of the skill.
