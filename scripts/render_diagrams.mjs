// bookforge P1.5 도해 프리렌더 — diagrams/fig-NN.json (AntV Infographic DSL 사이드카)
// → assets/fig-NN.svg (+ fig-NN.labels.json, G13 대조 정본).
//
// Usage: node render_diagrams.mjs <book_dir> --style <style>
// 계약(references/diagrams.md):
//   사이드카 {bf:{width:"full"|"twothirds", icons:false}, dsl:"..."|[줄배열]}
//   테마는 스타일 토큰(diagram 블록)이 강제 — 콘텐츠 theme 블록은 덮어쓴다.
//   렌더는 오프라인 재현 가능해야 한다: 산출 SVG 첫 줄의 dsl 해시가 일치하면 skip.
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { convertForeignObjectText, fontFaceCss, normalizeAuthoredSvg, pixelSelfCheck } from "./fo2text.mjs";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = path.join(SKILL, "assets", "fonts");
const CONVERTER_VERSION = 5; // fo2text/트림 알고리즘 변경 시 올려서 캐시 전체 무효화
const PIXEL_TOLERANCE = 0.02;
const MM2PT = 72 / 25.4;

function fail(msg) { console.error(`DIAGRAM FAIL: ${msg}`); process.exit(1); }

const args = process.argv.slice(2);
const bookDir = args[0] && !args[0].startsWith("--") ? path.resolve(args[0]) : null;
const style = args.includes("--style") ? args[args.indexOf("--style") + 1] : null;
if (!bookDir || !style) fail("usage: node render_diagrams.mjs <book_dir> --style <style>");

const tokensPath = path.join(SKILL, "styles", style, "tokens.json");
if (!existsSync(tokensPath)) fail(`unknown style: ${style}`);
const tokens = JSON.parse(readFileSync(tokensPath, "utf8"));
const dg = tokens.diagram;
if (!dg) fail(`styles/${style}/tokens.json에 diagram 블록 없음 — 이 스타일은 도해 미지원`);
// build_html.py와 동일 우선순위: book.json brand가 있으면 강조색(팔레트 1번)만 교체
const bookMeta = JSON.parse(readFileSync(path.join(bookDir, "book.json"), "utf8"));
const palette = [...dg.palette];
if (bookMeta.brand) palette[0] = bookMeta.brand;

// 템플릿 적합성 실측 원장 — blocked 템플릿은 SSR 전에 차단 (minFontPt 사후 검사와 이중 방어)
const ledger = JSON.parse(readFileSync(path.join(SKILL, "references", "diagram-ledger.json"), "utf8"));

// authored SVG 팔레트 강제 — 허용색 = 스타일 팔레트 + 뉴트럴(백·먹·회색 램프)
// CSS Color Level 4 named colors → hex (transparent/currentColor는 alienColors에서 별도 처리)
const CSS_NAMED_COLORS = {
  aliceblue: "#f0f8ff", antiquewhite: "#faebd7", aqua: "#00ffff", aquamarine: "#7fffd4", azure: "#f0ffff",
  beige: "#f5f5dc", bisque: "#ffe4c4", black: "#000000", blanchedalmond: "#ffebcd", blue: "#0000ff",
  blueviolet: "#8a2be2", brown: "#a52a2a", burlywood: "#deb887", cadetblue: "#5f9ea0", chartreuse: "#7fff00",
  chocolate: "#d2691e", coral: "#ff7f50", cornflowerblue: "#6495ed", cornsilk: "#fff8dc", crimson: "#dc143c",
  cyan: "#00ffff", darkblue: "#00008b", darkcyan: "#008b8b", darkgoldenrod: "#b8860b", darkgray: "#a9a9a9",
  darkgreen: "#006400", darkgrey: "#a9a9a9", darkkhaki: "#bdb76b", darkmagenta: "#8b008b", darkolivegreen: "#556b2f",
  darkorange: "#ff8c00", darkorchid: "#9932cc", darkred: "#8b0000", darksalmon: "#e9967a", darkseagreen: "#8fbc8f",
  darkslateblue: "#483d8b", darkslategray: "#2f4f4f", darkslategrey: "#2f4f4f", darkturquoise: "#00ced1",
  darkviolet: "#9400d3", deeppink: "#ff1493", deepskyblue: "#00bfff", dimgray: "#696969", dimgrey: "#696969",
  dodgerblue: "#1e90ff", firebrick: "#b22222", floralwhite: "#fffaf0", forestgreen: "#228b22", fuchsia: "#ff00ff",
  gainsboro: "#dcdcdc", ghostwhite: "#f8f8ff", gold: "#ffd700", goldenrod: "#daa520", gray: "#808080",
  green: "#008000", greenyellow: "#adff2f", grey: "#808080", honeydew: "#f0fff0", hotpink: "#ff69b4",
  indianred: "#cd5c5c", indigo: "#4b0082", ivory: "#fffff0", khaki: "#f0e68c", lavender: "#e6e6fa",
  lavenderblush: "#fff0f5", lawngreen: "#7cfc00", lemonchiffon: "#fffacd", lightblue: "#add8e6",
  lightcoral: "#f08080", lightcyan: "#e0ffff", lightgoldenrodyellow: "#fafad2", lightgray: "#d3d3d3",
  lightgreen: "#90ee90", lightgrey: "#d3d3d3", lightpink: "#ffb6c1", lightsalmon: "#ffa07a",
  lightseagreen: "#20b2aa", lightskyblue: "#87cefa", lightslategray: "#778899", lightslategrey: "#778899",
  lightsteelblue: "#b0c4de", lightyellow: "#ffffe0", lime: "#00ff00", limegreen: "#32cd32", linen: "#faf0e6",
  magenta: "#ff00ff", maroon: "#800000", mediumaquamarine: "#66cdaa", mediumblue: "#0000cd",
  mediumorchid: "#ba55d3", mediumpurple: "#9370db", mediumseagreen: "#3cb371", mediumslateblue: "#7b68ee",
  mediumspringgreen: "#00fa9a", mediumturquoise: "#48d1cc", mediumvioletred: "#c71585", midnightblue: "#191970",
  mintcream: "#f5fffa", mistyrose: "#ffe4e1", moccasin: "#ffe4b5", navajowhite: "#ffdead", navy: "#000080",
  oldlace: "#fdf5e6", olive: "#808000", olivedrab: "#6b8e23", orange: "#ffa500", orangered: "#ff4500",
  orchid: "#da70d6", palegoldenrod: "#eee8aa", palegreen: "#98fb98", paleturquoise: "#afeeee",
  palevioletred: "#db7093", papayawhip: "#ffefd5", peachpuff: "#ffdab9", peru: "#cd853f", pink: "#ffc0cb",
  plum: "#dda0dd", powderblue: "#b0e0e6", purple: "#800080", rebeccapurple: "#663399", red: "#ff0000",
  rosybrown: "#bc8f8f", royalblue: "#4169e1", saddlebrown: "#8b4513", salmon: "#fa8072", sandybrown: "#f4a460",
  seagreen: "#2e8b57", seashell: "#fff5ee", sienna: "#a0522d", silver: "#c0c0c0", skyblue: "#87ceeb",
  slateblue: "#6a5acd", slategray: "#708090", slategrey: "#708090", snow: "#fffafa", springgreen: "#00ff7f",
  steelblue: "#4682b4", tan: "#d2b48c", teal: "#008080", thistle: "#d8bfd8", tomato: "#ff6347",
  turquoise: "#40e0d0", violet: "#ee82ee", wheat: "#f5deb3", white: "#ffffff", whitesmoke: "#f5f5f5",
  yellow: "#ffff00", yellowgreen: "#9acd32",
};
function hslToHex(h, s, l) {
  s /= 100; l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
  return "#" + [f(0), f(8), f(4)].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
}
// 정규화 성공 시 "#rrggbb", 실패 시 null — null은 alienColors에서 위반으로 승격(침묵 통과 금지)
function normHex(c) {
  if (!c) return null;
  c = c.trim().toLowerCase();
  let m = c.match(/^rgba?\(\s*([\d.]+)(%?)\s*[, ]\s*([\d.]+)(%?)\s*[, ]\s*([\d.]+)(%?)/);
  if (m) {
    return "#" + [[m[1], m[2]], [m[3], m[4]], [m[5], m[6]]]
      .map(([v, pct]) => Math.max(0, Math.min(255, Math.round(pct ? (+v * 255) / 100 : +v))))
      .map((v) => v.toString(16).padStart(2, "0")).join("");
  }
  m = c.match(/^hsla?\(\s*(-?[\d.]+)(?:deg)?\s*[, ]\s*([\d.]+)%\s*[, ]\s*([\d.]+)%/);
  if (m) return hslToHex(((+m[1] % 360) + 360) % 360, +m[2], +m[3]);
  if (c in CSS_NAMED_COLORS) return CSS_NAMED_COLORS[c];
  if (/^#[0-9a-f]{3,4}$/.test(c)) c = "#" + [...c.slice(1)].map((ch) => ch + ch).join("");
  if (/^#[0-9a-f]{8}$/.test(c)) c = c.slice(0, 7); // 알파 채널 절단 — 색상 성분만 대조
  if (/^#[0-9a-f]{6}$/.test(c)) return c;
  return null;
}
function alienColors(svg, palette, strict = false) {
  // strict(authored 트랙): 허용색 = 스타일 팔레트 + paper(#ffffff)뿐 — 토큰 밖 색은
  // 무채색이라도 빌드 실패 (STYLE 「금지 사항」 2번, 토큰 밖 색 금지).
  // 비-strict(antv 트랙): 템플릿 산출 무채색 램프는 종전대로 허용.
  const allowed = new Set([...palette.map((c) => normHex(c)), "#ffffff"]);
  const out = new Set();
  const check = (raw) => {
    const v = raw.trim().toLowerCase();
    if (!v || v === "none" || v === "transparent" || v === "currentcolor" || v.startsWith("url(")) return;
    const hex = normHex(v);
    if (!hex) { out.add(`${v}(해석불가)`); return; } // 정규화 불가 색 문자열도 위반 — 무검증 통과 금지
    if (allowed.has(hex)) return;
    // 뉴트럴 허용: 무채색(채도 미미) 램프 — antv 트랙 한정
    const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    if (!strict && Math.max(r, g, b) - Math.min(r, g, b) <= 16) return;
    out.add(hex);
  };
  for (const m of svg.matchAll(/(?:fill|stroke)="([^"]+)"/gi)) check(m[1]);
  // style="fill:...;stroke:..." 인라인 CSS도 동일 검사 (fill-opacity 등 접미 속성은 비매칭)
  for (const s of svg.matchAll(/style="([^"]*)"/gi)) {
    for (const d of s[1].matchAll(/(?:^|;)\s*(?:fill|stroke)\s*:\s*([^;]+)/gi)) check(d[1]);
  }
  return [...out];
}

const diagramsDir = path.join(bookDir, "diagrams");
const sidecars = existsSync(diagramsDir)
  ? readdirSync(diagramsDir).filter((f) => /^fig-\d+\.json$/.test(f)).sort()
  : [];
if (!sidecars.length) { console.log("no diagrams — skip"); process.exit(0); }

// SSR 모듈: 1순위 = 커밋된 벤더 번들(vendor/antv-ssr.bundle.mjs — 레지스트리·
// node_modules 불필요, byte-identical 검증 완료). 폴백 = 로컬 node_modules.
const skillRequire = createRequire(path.join(SKILL, "package.json"));
let renderToString, getTemplate;
const bundlePath = path.join(SKILL, "vendor", "antv-ssr.bundle.mjs");
if (existsSync(bundlePath)) {
  ({ renderToString, getTemplate } = await import(bundlePath));
} else {
  try {
    ({ renderToString } = await import(skillRequire.resolve("@antv/infographic/ssr")));
    ({ getTemplate } = await import(skillRequire.resolve("@antv/infographic")));
  } catch {
    fail("도해 렌더러 부재 — vendor/antv-ssr.bundle.mjs 유실 시 스킬 루트에서 `npm ci` 후 `node vendor/build-bundle.mjs`");
  }
}

// Playwright: print_pdf.mjs와 동일하게 NODE_PATH(글로벌 npm root) 우선, 폴백으로 직접 해석
let chromium;
try {
  ({ chromium } = createRequire(import.meta.url)("playwright"));
} catch {
  try {
    const g = execSync("npm root -g", { encoding: "utf8" }).trim();
    ({ chromium } = createRequire(path.join(g, "noop.js"))("playwright"));
  } catch {
    fail("playwright 미가용 — `npm i -g playwright && npx playwright install chromium`");
  }
}

// AntV DSL 트랙 라벨 급수 강제 (6단계) — 역할별 목표 pt를 body_pt 배수로 선언한다.
//
// 왜 역할별인가: 5단계 실측에서 dsl 6건 전건이 **내부비(최대/최소) 1.714×**로
// 밴드 허용 내부비 1.425×(= 상한 11.4pt ÷ 하한 8pt)를 넘었다. 균일 축척은 상·하한을
// 함께 옮기므로 상한을 맞추면 하한이 깨진다(×0.478 축소 시 최소 6.65pt < 8pt).
// 따라서 title(대)·text(중)·desc(소)의 **격차 자체를 좁혀** 넣어야 한다.
//
// 키 표기는 반드시 케밥 `font-size`다 — 소비 지점이 SVG 속성명을 그대로 쓰므로
// `fontSize`는 조용히 무시된다(1단계 S0-2 실측).
//
// 이 상수가 바뀌면 산출 SVG가 바뀐다 → dsl 캐시 해시에 통째로 싣는다(labelScaleHash).
// authored 트랙 해시에는 넣지 않는다(주입은 dsl 전용 — authored는 캐시 히트 유지).
const LABEL_SCALE = {
  version: 1,
  title: 1.15,       // body_pt 배수. 밴드 상한 1.20의 96% — 반복 수렴 오차 여유
  text: 1.0,         // base.text / item.label / item.value = 본문과 같은 급수
  desc: 0.9,         // 보조 설명. 하한 대비 여유는 floorMargin이 별도로 보장
  capMargin: 0.96,   // title은 capPt×0.96을 넘지 않는다(밴드 상한 직격 방지)
  floorMargin: 1.07, // desc는 minFontPt×1.07 아래로 내려가지 않는다(하한 HARD 방지)
};
const LABEL_SCALE_MAX_ITER = 2; // 보정 반복 상한(= 최대 3회 렌더). 프레임 고정이라 실측은 2회에 끝난다.

// 목표 pt 산출. 반환 null이면 주입하지 않는다(판정 기준이 없으면 강제도 없다 — 5단계
// 「검사가 꺼지는 경우」와 같은 원칙으로, 꺼짐은 labelBandReport가 WARN으로 드러낸다).
function labelScalePlan() {
  const band = dg.labelBand && typeof dg.labelBand === "object" ? dg.labelBand : null;
  const maxRatio = band && typeof band.maxRatio === "number" ? band.maxRatio : null;
  const bodyPt = typeof tokens.body_pt === "number" ? tokens.body_pt : null;
  if (maxRatio === null || bodyPt === null) return null;
  const floorPt = typeof dg.minFontPt === "number" ? dg.minFontPt : 0;
  const capPt = bodyPt * maxRatio;
  const titlePt = Math.min(bodyPt * LABEL_SCALE.title, capPt * LABEL_SCALE.capMargin);
  const descPt = Math.max(bodyPt * LABEL_SCALE.desc, floorPt * LABEL_SCALE.floorMargin);
  if (descPt > titlePt) return null; // 밴드 상한과 글자 하한이 모순 — 주입으로 풀 수 없다
  const textPt = Math.min(Math.max(bodyPt * LABEL_SCALE.text, descPt), titlePt);
  return { bodyPt, floorPt, capPt, titlePt, textPt, descPt };
}
// dsl 해시에 실리는 주입 정책 지문 — 정책이 바뀌면 dsl 도해만 정확히 재렌더된다.
function labelScaleHash() {
  const plan = labelScalePlan();
  if (!plan) return null;
  return stableSort({
    ...LABEL_SCALE, maxIter: LABEL_SCALE_MAX_ITER,
    targetPt: { title: r3(plan.titlePt), text: r3(plan.textPt), desc: r3(plan.descPt) },
  });
}
// 주입은 스칼라 t(= title의 user unit) 하나로 매개한다 — 세 역할이 고정 비율로 함께 움직인다.
function injectFromT(plan, t) {
  const u = (pt) => Math.round((t * (pt / plan.titlePt)) * 1000) / 1000;
  return { title: Math.round(t * 1000) / 1000, text: u(plan.textPt), desc: u(plan.descPt) };
}
const injectEq = (a, b) => !!a && !!b && a.title === b.title && a.text === b.text && a.desc === b.desc;

// 왜 "밀착 트림 + 급수 주입"만으로는 안 되는가 (실측으로 뒤집힌 전제):
//   도해는 지면에서 **고정 물리 폭**(bf.width = 130/106/164mm)으로 발행된다. 세로 리스트
//   템플릿은 트림 폭의 대부분이 글자 폭이라, 급수를 줄이면 트림 폭이 같이 줄고 pt/u가 커진다
//   — 즉 **글자는 안 줄고 도형만 커진다**. iso-base-dsl/fig-02 실측: 밀착 트림으로 목표
//   10.925pt를 맞추면 viewBox 302.63u → 150.39u가 되어 원 지름이 10.5mm → 21.2mm로 배가되고
//   종횡비가 0.66 → 0.32로 무너져 발행 높이가 161mm → 326mm(판면 초과)가 된다.
// 해법: **폭 프레임 고정**. 무주입 0회차의 트림 폭 vbW0을 그대로 프레임으로 쓰면 pt/u가
//   scalePt0으로 보존되므로 주입 user unit = 목표pt / scalePt0 **한 방에 정확히 맞는다**
//   (반복 수렴 불필요). 도형은 지면에서 원래 크기 그대로이고 글자만 줄어든다. 남는 폭은
//   오른쪽 여백이 되며, 좌측 정렬축(판면 27mm 라인)은 트림이 지키던 대로 유지된다.
//   세로는 밀착 트림하므로(pt/u는 폭만의 함수) 타이틀이 줄며 생긴 윗여백은 회수된다.

function applyTheme(dsl, palette, inject) {
  // 콘텐츠의 theme 블록(들여쓰기 연속 줄 포함)을 제거하고 스타일 팔레트를 강제한다.
  const stripped = dsl.replace(/^theme\r?\n(?:[ \t]+.*\r?\n?)*/gm, "").replace(/\s+$/, "");
  let block = `theme\n  palette ${palette.join(" ")}\n`;
  if (inject) {
    // 도달 확인된 5개 역할 전부에 명시 주입한다. base.text는 미지 역할의 폴백이므로
    // 빠뜨리면 템플릿에 따라 강제 밖 라벨이 남는다(실측: base.text만 주면 title·desc까지 함께 먹는다).
    block += `  title\n    font-size ${inject.title}\n`
      + `  desc\n    font-size ${inject.desc}\n`
      + `  base\n    text\n      font-size ${inject.text}\n`
      + `  item\n    label\n      font-size ${inject.text}\n`
      + `    desc\n      font-size ${inject.desc}\n`
      + `    value\n      font-size ${inject.text}\n`;
  }
  return `${stripped}\n${block}`;
}

// 템플릿 하드코딩 급수(단계번호 배지 `01/02/03` = fontSize:16, ItemLabel 미경유)는 테마로
// 도달하지 않는다(1단계 S0-2 실증). 이들은 **SSR 원본에서 native `<text>`로만** 나타난다 —
// 테마 경유 라벨은 전부 foreignObject라 fo2text 변환 후에야 `<text>`가 된다(실측: fig-02
// 원본 native text 3 = 배지 3, foreignObject 7 = 타이틀 1 + label 3 + desc 3).
// 그래서 **변환 전 raw**에 클램프를 걸면 배지만 정확히 잡히고, pixelSelfCheck는 클램프된
// raw와 변환본을 비교하므로 "변환이 외형을 보존했는가"라는 자기검증의 의미도 그대로 남는다.
// (이는 생성 이미지 위 글자 합성이 아니라 렌더 파이프라인 내부의 결정론적 SVG 변환이다.)
// 배지는 text-anchor="middle" + dominant-baseline="central"이라 급수만 줄여도 중심이 유지된다.
function clampNativeText(svg, plan, scalePt) {
  let count = 0;
  const rewrite = (whole, num, unit) => {
    let user = parseFloat(num);
    if (unit === "pt") user *= 96 / 72;
    else if (unit && unit !== "px") return whole; // 미지 단위는 건드리지 않는다(하한 검사가 HARD로 잡는다)
    const pt = user * scalePt;
    const target = Math.min(Math.max(pt, plan.descPt), plan.titlePt);
    if (Math.abs(target - pt) < 1e-6) return whole;
    let nu = target / scalePt;
    if (unit === "pt") nu *= 72 / 96;
    count++;
    return whole.replace(/font-size="[\d.]+[a-z%]*"/i, `font-size="${Math.round(nu * 1000) / 1000}"`);
  };
  const out = svg.replace(/<(?:text|tspan)\b[^>]*?font-size="([\d.]+)([a-z%]*)"[^>]*>/gi,
    (whole, num, unit) => rewrite(whole, num, unit));
  return { svg: out, count };
}

function stripIconLines(dsl) {
  return dsl.split("\n").filter((l) => !/^\s+icon\s+\S/.test(l)).join("\n");
}

function sortDefsSymbols(svg) {
  // <symbol> id가 콘텐츠 해시라 정렬 = 결정론화 (네트워크 완료 순서 비결정 흡수)
  return svg.replace(/<defs\b[^>]*>([\s\S]*?)<\/defs>/, (whole, inner) => {
    const symbols = inner.match(/<symbol\b[\s\S]*?<\/symbol>/g);
    if (!symbols || symbols.length < 2) return whole;
    const rest = symbols.reduce((acc, s) => acc.replace(s, ""), inner);
    const sorted = [...symbols].sort((a, b) => {
      const ida = (a.match(/id="([^"]*)"/) || [])[1] || "";
      const idb = (b.match(/id="([^"]*)"/) || [])[1] || "";
      return ida < idb ? -1 : ida > idb ? 1 : 0;
    });
    return whole.replace(inner, rest.trim() ? rest + sorted.join("") : sorted.join(""));
  });
}

// viewBox 트림 — SVG 내부의 빈 좌우/상하 패딩을 제거해, 지면에서 도해가 판면
// 좌측 라인(27mm)에 정확히 물리고 폭이 명목 폭(130/86mm)과 일치하게 한다.
// (내부 여백이 있으면 콘텐츠가 8~36mm 안쪽에서 시작해 본문 정렬축이 어긋난다.)
// 반드시 pixelSelfCheck 이후에 적용할 것 — 트림은 원본과 프레이밍이 달라진다.
// frameW: 트림 폭의 **하한**(user unit). 6단계 라벨 급수 강제가 쓴다 — 글자만 줄이면
// 트림이 같이 좁아져 pt/u가 커지므로(= 도형이 지면에서 커지고 종횡비가 무너진다),
// 폭 프레임을 무주입 회차 값으로 고정해 pt/u를 보존한다. 세로는 그대로 밀착 트림한다.
async function trimViewBox(page, svg, frameW = null) {
  const harness = `<!doctype html><html><head><meta charset="utf-8"><style>
${fontFaceCss(FONT_DIR)}
html,body{margin:0;padding:0;background:#fff;}
#stage svg text, #stage svg tspan { font-family:'Pretendard' !important; }
</style></head><body><div id="stage">${svg}</div></body></html>`;
  await page.setContent(harness, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  return page.evaluate((fw) => {
    const el = document.querySelector("#stage svg");
    if (!el) return null;
    const bb = el.getBBox();
    if (!bb || bb.width < 1 || bb.height < 1) return null;
    // 패딩: 스트로크 폭·마커(getBBox 비포함)를 덮는 소여백
    const pad = Math.max(2, 0.008 * Math.max(bb.width, bb.height));
    const tight = bb.width + 2 * pad;
    const w = Math.max(tight, fw || 0); // 프레임 고정 시 남는 폭은 오른쪽 여백(좌측 정렬축 유지)
    el.setAttribute("viewBox",
      `${(bb.x - pad).toFixed(2)} ${(bb.y - pad).toFixed(2)} ` +
      `${w.toFixed(2)} ${(bb.height + 2 * pad).toFixed(2)}`);
    el.removeAttribute("width");
    el.removeAttribute("height");
    return { svg: new XMLSerializer().serializeToString(el), tightW: tight };
  }, frameW);
}

// 캐시 해시에 실리는 「판정 파라미터」 — 도해 SVG는 이 값들로 검사·환산되므로
// 값이 바뀌면 캐시가 그 도해만 정확히 무효화되어야 한다(전역 CONVERTER_VERSION 대신).
//   widthMm   : fontFloorViolations의 pt 환산 기준 폭 — 2·3단계 폭 동기화의 재렌더 트리거
//   minFontPt : 글자 하한(HARD)
//   labelBand : 라벨 밴드 상한 {maxRatio}(5단계 신설) — 부재 시 null로 고정.
//               null → 실값으로 바뀌는 순간 해당 스타일 도해 전건 재렌더가 **의도된 동작**이다.
// 키를 재귀 정렬해 tokens.json의 키 순서가 바뀌어도 해시가 흔들리지 않게 한다.
function stableSort(v) {
  if (Array.isArray(v)) return v.map(stableSort);
  if (v && typeof v === "object") {
    return Object.fromEntries(Object.keys(v).sort().map((k) => [k, stableSort(v[k])]));
  }
  return v === undefined ? null : v;
}
function gateParams(widthKey) {
  return stableSort({
    widthMm: (dg.widths || {})[widthKey] ?? null,
    minFontPt: dg.minFontPt ?? null,
    labelBand: dg.labelBand ?? null,
    // 5단계: 상한이 body_pt에 상대적이므로 본문 급수도 판정 파라미터다. 이게 없으면
    // body_pt만 바뀐 스타일에서 캐시된 metrics의 밴드 판정이 옛 기준으로 남는다.
    bodyPt: tokens.body_pt ?? null,
  });
}

// 라벨 급수 실측 — <text>/<tspan>의 font-size(속성·인라인 style)를 **트림 후 최종 좌표계**에서
// pt로 환산한다. 하한(fontFloorViolations, HARD)과 상한(labelBandReport, WARN)이 반드시 같은
// 스캔을 보게 해 두 판정이 서로 다른 숫자를 말하는 일이 없게 한다.
const BAND_TOL_PT = 0.05; // 하한 판정과 대칭인 부동소수 여유
function scanLabelPt(svg, widthKey) {
  const widthMm = (dg.widths || {})[widthKey] ?? null;
  const vb = svg.match(/viewBox="[-\d. ]*?([\d.]+) ([\d.]+)"\s*/);
  const vbW = vb ? parseFloat(vb[1]) : null;
  const scalePt = widthMm && vbW ? (widthMm * MM2PT) / vbW : null; // user unit -> 실제 pt
  const sizes = [];
  const unitErrors = [];
  const take = (tag, num, unit) => {
    let user = parseFloat(num);
    if (unit === "pt") user *= 96 / 72; // CSS pt → user unit(px)
    else if (unit && unit !== "px") { // 미지 단위는 검증 불가 — 침묵 통과 금지
      unitErrors.push(`${tag} font-size 단위 '${unit}' 미지원 — px/pt/무단위로 지정할 것`);
      return;
    }
    sizes.push({ tag, raw: `${num}${unit || "u"}`, pt: scalePt === null ? null : user * scalePt });
  };
  // <text>뿐 아니라 <tspan>의 font-size 속성·style 내 font-size도 검사 (하한 우회 차단)
  for (const m of svg.matchAll(/<(text|tspan)\b[^>]*?font-size="([\d.]+)([a-z%]*)"/gi)) take(m[1], m[2], m[3]);
  for (const m of svg.matchAll(/<(text|tspan)\b[^>]*?style="[^"]*?font-size\s*:\s*([\d.]+)([a-z%]*)/gi)) take(m[1], m[2], m[3]);
  return { widthMm, vbW, scalePt, sizes, unitErrors };
}

// 밴드 하한 — 기존 계약 그대로 **HARD**. (minFontPt 미선언·widths 미선언 시 검사가 꺼지는
// 종전 동작도 그대로 둔다 — 그 침묵은 labelBandReport가 WARN으로 드러낸다.)
function fontFloorViolations(scan) {
  const minPt = dg.minFontPt;
  if (!minPt || !scan.widthMm) return [];
  if (!scan.vbW) return [`viewBox 폭을 읽지 못함 — minFontPt 검사 불가`];
  const out = [...scan.unitErrors];
  for (const s of scan.sizes) {
    if (s.pt < minPt - BAND_TOL_PT) out.push(`${s.tag} ${s.raw} ≈ ${s.pt.toFixed(1)}pt < ${minPt}pt 하한`);
  }
  return out;
}

const r3 = (v) => (typeof v === "number" && isFinite(v) ? Math.round(v * 1000) / 1000 : null);

// 밴드 상한 — 라벨 최대 pt ≤ body_pt × labelBand.maxRatio.
//
// **WARN으로 태어난다** (설계 정본 report/w5-design.md 「최대 리스크」 1).
// 사용자 원 지적은 "도해 라벨이 본문보다 크다"였지만, 실측 코퍼스의 max/본문 비는 중앙 0.96·
// p90 1.17이고 도해 내부 활자비(중앙 1.095×)가 창 폭 비(8.74/8.00 = 1.0925×)를 넘는 도해가
// 다수라 상·하한을 **축척으로 동시에 만족시킬 수 없다**(축척은 두 끝을 함께 옮긴다).
// cap 0.92를 HARD로 내면 authored 대다수와 AntV 트랙 전체가 즉시 반려되어 릴리스가 선다.
// 따라서 cap 1.20[하우스 등급] · 강도 WARN으로 출생시키고, 스타일별 enforce 승격은
// 8단계(assets/fig-NN.metrics.json 집계로 원장 재도출)가 맡는다.
//
// 반환: 콘솔 출력용 lines + assets/fig-NN.metrics.json에 실릴 metrics.
function labelBandReport(scan, { name, kind, widthKey, scaled = false }) {
  const band = dg.labelBand && typeof dg.labelBand === "object" ? dg.labelBand : null;
  const maxRatio = band && typeof band.maxRatio === "number" ? band.maxRatio : null;
  const bodyPt = typeof tokens.body_pt === "number" ? tokens.body_pt : null;
  const floorPt = typeof dg.minFontPt === "number" ? dg.minFontPt : null;
  const pts = scan.sizes.map((s) => s.pt).filter((p) => typeof p === "number" && isFinite(p));
  const metrics = {
    schema: "bf-diagram-metrics/1",
    fig: name, kind, style, widthKey,
    widthMm: scan.widthMm, viewBoxW: r3(scan.vbW),
    // 환산 계수는 3자리로 자르면 pt 재산출이 어긋난다 — 5자리 유지
    ptPerUnit: scan.scalePt === null ? null : Math.round(scan.scalePt * 1e5) / 1e5,
    bodyPt, minFontPt: floorPt, maxRatio,
    sizeCount: pts.length,
    minPt: pts.length ? r3(Math.min(...pts)) : null,
    maxPt: pts.length ? r3(Math.max(...pts)) : null,
    ratio: null, capPt: null,
    band: { level: "WARN", verdict: "skip", reason: null },
    sizesPt: pts.map(r3).sort((a, b) => a - b),
  };
  const lines = [];
  // 검사가 꺼지는 모든 경우를 소리내어 알린다 — 미선언이 위반보다 조용해서는 안 된다.
  const off = maxRatio === null ? "tokens.diagram.labelBand.maxRatio 미선언"
    : bodyPt === null ? "tokens.body_pt 미선언(G1-SCALE도 같은 이유로 꺼진다)"
    : scan.scalePt === null ? `pt 환산 불가(widths.${widthKey} 또는 viewBox 폭 부재)`
    : !pts.length ? "font-size 실측 0건" : null;
  if (off) {
    metrics.band.reason = off;
    lines.push(`WARN DIAGRAM-BAND ${name}: 라벨 밴드 상한 검사 꺼짐 — ${off}`);
    return { metrics, lines, violated: false };
  }
  const minPt = Math.min(...pts), maxPt = Math.max(...pts);
  const capPt = bodyPt * maxRatio;
  metrics.ratio = r3(maxPt / bodyPt);
  metrics.capPt = r3(capPt);
  const violated = maxPt > capPt + BAND_TOL_PT;
  metrics.band.verdict = violated ? "violation" : "ok";
  // 콘솔 수치는 metrics.json에 실리는 값과 같은 반올림을 쓴다(두 산출물이 다른 숫자를 말하지 않게).
  const fact = `최대 라벨 ${metrics.maxPt}pt = 본문 ${bodyPt}pt × ${metrics.ratio} `
    + `(상한 ${maxRatio}× = ${metrics.capPt}pt) · 최소 라벨 ${metrics.minPt}pt`
    + (floorPt ? `(하한 ${floorPt}pt)` : "")
    + ` · 급수 ${pts.length}건 · bf.width=${widthKey} ${scan.widthMm}mm ÷ viewBox ${scan.vbW}u `
    + `= ${scan.scalePt.toFixed(5)}pt/u`;
  if (!violated) return { metrics, lines, violated: false };

  // ---- 반려 진단 (트랙별 분기) ----
  // 상한 위반이므로 수리 방향은 **라벨 축소 / viewBox 확대**다. 하한 위반의 처방
  // (폭 확대·font-size 확대)과 부호가 반대라는 점을 명시한다.
  const shrink = capPt / maxPt;                               // 균일 축척 계수(<1)
  const uniformOk = !floorPt || minPt * shrink >= floorPt - BAND_TOL_PT;
  const internal = maxPt / minPt;                             // 도해 내부 활자비
  const allowedInternal = floorPt ? capPt / floorPt : null;   // 밴드가 허용하는 최대 내부비
  lines.push(`WARN DIAGRAM-BAND ${name}: 라벨 밴드 상한 초과 — ${fact}`);
  if (kind === "antv" && scaled) {
    // 6단계 주입이 이미 걸렸는데도 넘는 경우 — 테마·클램프 어느 쪽으로도 못 잡은 급수가 남았다.
    lines.push(`WARN DIAGRAM-BAND ${name}:   → 라벨 급수 강제(역할별 font-size 주입 + 하드코딩 급수 클램프)를`
      + ` 적용한 뒤에도 상한 초과. 이 템플릿에 테마·native <text> 어느 경로로도 도달하지 않는 급수가 남아 있다`
      + `(예: CSS 클래스·<style> 블록 경유). fig-NN.metrics.json의 labelScale.iterations로 회차별 실측을 확인하고,`
      + ` 해소 불가면 8단계 원장에서 이 템플릿 자체를 판정할 것.`);
  } else if (kind === "antv") {
    lines.push(`WARN DIAGRAM-BAND ${name}:   → AntV DSL 트랙 = **6단계 스케일 강제 대상**`
      + `(applyTheme에 font-size 주입). 템플릿이 급수를 하드코딩하므로 사이드카·폭 조정으로는 해소되지 않는다.`
      + (uniformOk ? "" : ` 균일 축척(×${shrink.toFixed(3)})으로는 최소 라벨이 ${(minPt * shrink).toFixed(2)}pt로`
        + ` 하한 ${floorPt}pt 미달 — 6단계는 역할별(label/desc/title) 분리 주입이어야 한다.`));
  } else if (uniformOk) {
    lines.push(`WARN DIAGRAM-BAND ${name}:   → 수리: 라벨 font-size를 ×${shrink.toFixed(3)} 이하로 **축소**하거나,`
      + ` viewBox 폭을 ${scan.vbW}u → ${(scan.vbW / shrink).toFixed(1)}u 이상으로 **확대**할 것`
      + `(폭 확대 = 유효 pt 축소). ※ 하한 위반의 처방(폭 축소·font-size 확대)과 방향이 반대다.`);
  } else {
    lines.push(`WARN DIAGRAM-BAND ${name}:   → 균일 축척으로는 해소 불가(축척은 상·하한을 함께 옮긴다):`
      + ` ×${shrink.toFixed(3)} 축소 시 최소 라벨이 ${(minPt * shrink).toFixed(2)}pt로 하한 ${floorPt}pt 미달이고,`
      + ` viewBox 확대도 같은 이유로 막힌다. 이 도해의 라벨 최대/최소 비 ${internal.toFixed(3)}×가`
      + ` 밴드 허용 내부비 ${allowedInternal.toFixed(3)}×(= 상한 ${capPt.toFixed(2)}pt ÷ 하한 ${floorPt}pt)를 넘는다`
      + ` — 폭이 아니라 **라벨 간 상대 급수**를 좁혀야 한다(최대 라벨만 축소).`);
  }
  return { metrics, lines, violated: true };
}

// 실측을 도해별로 축약 없이 남긴다: 콘솔 1행 + assets/fig-NN.metrics.json(8단계 원장 입력).
// 캐시 히트 때도 저장된 metrics로 같은 줄을 다시 낸다 — 2회차 빌드에서 조용해지는 경고는
// 없는 경고와 같다.
function emitBand(report, outMetricsPath) {
  writeFileSync(outMetricsPath, JSON.stringify(report.metrics, null, 2));
  for (const l of report.lines) console.log(l);
  return report;
}
function bandSummary(m) {
  if (!m || m.maxPt === null) return "라벨 실측 없음";
  const r = m.ratio === null ? "" : ` = 본문 ${m.bodyPt}pt × ${m.ratio}`
    + (m.band && m.band.verdict === "violation" ? ` **상한 ${m.maxRatio}× 초과**` : "");
  const s = m.labelScale && m.labelScale.applied
    ? `, 급수 강제 적용(${m.labelScale.passes}회 수렴, 하드코딩 클램프 ${m.labelScale.nativeClamped}건)` : "";
  return `라벨 ${m.minPt}~${m.maxPt}pt${r}${s}`;
}
function replayBand(outMetricsPath, name) {
  if (!existsSync(outMetricsPath)) return null;
  let m;
  try { m = JSON.parse(readFileSync(outMetricsPath, "utf8")); } catch { return null; }
  if (m && m.band && m.band.verdict === "violation") {
    console.log(`WARN DIAGRAM-BAND ${name}: 라벨 밴드 상한 초과(캐시 유지) — `
      + `최대 ${m.maxPt}pt = 본문 ${m.bodyPt}pt × ${m.ratio} > 상한 ${m.maxRatio}× (${m.capPt}pt)`);
  } else if (m && m.band && m.band.verdict === "skip") {
    console.log(`WARN DIAGRAM-BAND ${name}: 라벨 밴드 상한 검사 꺼짐(캐시 유지) — ${m.band.reason}`);
  }
  return m;
}

async function ssrWithRetry(dsl, name) {
  // SSR 내장 타임아웃(10s)은 미지 템플릿 등 일부 경로에서 발화하지 않는다(실측) —
  // 외부 30s 레이스로 무한 대기를 차단한다.
  const withTimeout = (p, ms) => Promise.race([
    p, new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout ${ms}ms`)), ms).unref?.()),
  ]);
  for (let attempt = 1; attempt <= 3; attempt++) {
    try { return await withTimeout(renderToString(dsl), 30_000); }
    catch (e) {
      if (attempt === 3) fail(`${name}: SSR 3회 실패 — ${e.message}`);
      console.error(`${name}: SSR attempt ${attempt} failed (${e.message}) — retry`);
    }
  }
}

const assetsDir = path.join(bookDir, "assets");
mkdirSync(assetsDir, { recursive: true });
const checkDir = path.join(bookDir, "typeset", "diagcheck");
mkdirSync(checkDir, { recursive: true });

let browser = null;
let page = null;
let rendered = 0, skipped = 0, bandWarns = 0;

for (const file of sidecars) {
  const name = file.replace(/\.json$/, "");
  const sidecar = JSON.parse(readFileSync(path.join(bookDir, "diagrams", file), "utf8"));
  const bf = sidecar.bf || {};
  const widthKey = bf.width || "full";
  if (!["full", "twothirds"].includes(widthKey)) fail(`${name}: bf.width는 full|twothirds`);
  const kind = sidecar.kind || "antv";
  if (!["antv", "authored"].includes(kind)) fail(`${name}: kind는 antv|authored`);

  if (kind === "authored") {
    // ---- authored SVG 트랙: 에이전트가 그린 diagrams/fig-NN.svg를 동일 정규화 파이프라인에 통과 ----
    const srcPath = path.join(bookDir, "diagrams", `${name}.svg`);
    if (!existsSync(srcPath)) fail(`${name}: kind=authored인데 diagrams/${name}.svg 부재`);
    const rawAuthored = readFileSync(srcPath, "utf8");
    if (/xml-stylesheet/.test(rawAuthored) || /(?:href|src)="https?:\/\//.test(rawAuthored)) {
      fail(`${name}: 외부 참조(CDN 폰트·원격 자원) 금지 — 자립 SVG로 그릴 것`);
    }
    // palette 포함 필수: 스타일(팔레트) 교체 재빌드 시 캐시 미스로 alienColors 재검증 강제
    const hashA = createHash("sha256")
      .update(JSON.stringify({ svg: rawAuthored, width: widthKey, palette, gate: gateParams(widthKey), v: CONVERTER_VERSION }))
      .digest("hex");
    const outSvgA = path.join(assetsDir, `${name}.svg`);
    const outLabelsA = path.join(assetsDir, `${name}.labels.json`);
    const outMetricsA = path.join(assetsDir, `${name}.metrics.json`);
    if (existsSync(outSvgA) && existsSync(outLabelsA) && existsSync(outMetricsA)) {
      const head = readFileSync(outSvgA, "utf8").slice(0, 130);
      if (head.includes(`bf:authored=sha256:${hashA}`)) {
        skipped++;
        const m = replayBand(outMetricsA, name);
        console.log(`${name}: cache hit — skip (${bandSummary(m)})`);
        continue;
      }
    }
    const tA = Date.now();
    if (!browser) {
      browser = await chromium.launch();
      page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });
    }
    let normalized, labelsA;
    try {
      ({ svg: normalized, labels: labelsA } = await normalizeAuthoredSvg(page, rawAuthored, FONT_DIR));
    } catch (e) {
      fail(`${name}: ${e.message.replace(/^.*Error: /s, "").split("\n")[0]}`);
    }
    if (!labelsA.length) fail(`${name}: 라벨 0개`);
    const aliens = alienColors(normalized, palette, true);
    if (aliens.length) {
      // 구 토큰으로 그린 authored SVG를 위한 안내: insight --ink-mute가 대비 하한 미달로
      // 교체됐다(#6d747a는 tint #ecf8fe 위 4.37 < 4.5 — 실물 사고 사례가 있다).
      const migrated = aliens.includes("#6d747a")
        ? " · #6d747a는 대비 미달로 #5a6167로 교체됐다 — SVG의 해당 색을 바꿀 것"
        : "";
      fail(`${name}: 팔레트 밖 색 ${aliens.join(", ")} — authored SVG는 styles/${style} tokens.diagram.palette + #ffffff만 허용(토큰 밖 색 금지)${migrated}`);
    }
    const checkA = await pixelSelfCheck(browser, rawAuthored, normalized, FONT_DIR, path.join(checkDir, name));
    if (checkA.ratio > PIXEL_TOLERANCE) {
      fail(`${name}: 정규화 자기검증 실패 — 픽셀 상이율 ${(checkA.ratio * 100).toFixed(2)}% (${checkDir}/${name}.diff.png)`);
    }
    normalized = (await trimViewBox(page, normalized))?.svg || normalized;
    // 글자 밴드는 트림 후 최종 좌표계 기준으로 검사 (트림은 실크기를 키우는 방향).
    // 하한 = HARD(빌드 중단), 상한 = WARN(5단계 출생 강도).
    const scanA = scanLabelPt(normalized, widthKey);
    const floorsA = fontFloorViolations(scanA);
    if (floorsA.length) fail(`${name}: 글자 크기 하한 위반 — ${floorsA.join("; ")} (bf.width=${widthKey})`);
    const bandA = emitBand(labelBandReport(scanA, { name, kind, widthKey }), outMetricsA);
    writeFileSync(outSvgA, `<!--bf:authored=sha256:${hashA}-->\n${normalized}`);
    writeFileSync(outLabelsA, JSON.stringify(labelsA, null, 2));
    rendered++;
    if (bandA.violated) bandWarns++;
    console.log(`${name}: OK (authored) ${labelsA.length} labels, diff ${(checkA.ratio * 100).toFixed(2)}%, `
      + `${bandSummary(bandA.metrics)}, ${Date.now() - tA}ms`);
    continue;
  }

  let dsl = Array.isArray(sidecar.dsl) ? sidecar.dsl.join("\n") : sidecar.dsl;
  if (typeof dsl !== "string" || !dsl.trim().startsWith("infographic ")) {
    fail(`${name}: dsl은 'infographic <template>'로 시작하는 문자열(또는 줄 배열)`);
  }
  // AntV는 미지 템플릿명을 조용히 기본 템플릿으로 폴백한다(실측) — 오타 침묵 통과 차단
  const tplName = dsl.trim().split(/\s+/)[1];
  if (!getTemplate(tplName)) {
    fail(`${name}: 미지 템플릿 '${tplName}' — infographic-creator 스킬의 템플릿 목록 참조`);
  }
  // 실측 원장 사전 차단 — 8pt 하한에 도달 불가 판정 템플릿 (references/diagram-ledger.json)
  if (ledger.blocked_prefixes.some((p) => tplName.startsWith(p))) {
    fail(`${name}: 템플릿 '${tplName}'은 실측 원장에서 차단(라벨이 ${ledger.floor_pt}pt 하한 도달 불가) — 대안: sequence-timeline-simple 등 원장 ok 템플릿`);
  }
  const wantIcons = bf.icons === true;
  if (wantIcons && !dg.iconsAllowed) fail(`${name}: 이 스타일(${style})은 icons 미허용`);
  if (!wantIcons) dsl = stripIconLines(dsl);
  const dslBase = dsl;
  dsl = applyTheme(dslBase, palette, null); // 해시 입력 = 주입 이전의 결정론적 DSL

  const hash = createHash("sha256")
    // scale: 6단계 주입 정책 지문. **dsl 트랙에만** 실어 authored 캐시를 흔들지 않는다.
    .update(JSON.stringify({ dsl, width: widthKey, icons: wantIcons, gate: gateParams(widthKey), scale: labelScaleHash(), v: CONVERTER_VERSION }))
    .digest("hex");
  const outSvg = path.join(assetsDir, `${name}.svg`);
  const outLabels = path.join(assetsDir, `${name}.labels.json`);
  const outMetrics = path.join(assetsDir, `${name}.metrics.json`);
  if (existsSync(outSvg) && existsSync(outLabels) && existsSync(outMetrics)) {
    const head = readFileSync(outSvg, "utf8").slice(0, 120);
    if (head.includes(`bf:dsl=sha256:${hash}`)) {
      skipped++;
      const m = replayBand(outMetrics, name);
      console.log(`${name}: cache hit — skip (${bandSummary(m)})`);
      continue;
    }
  }

  const t0 = Date.now();
  // ---- 라벨 급수 강제 (6단계) ----
  // 0회차: 무주입 밀착 트림 → vbW0·scalePt0 실측(= 전후 비교의 "전").
  // 1회차: 목표pt/scalePt0을 역할별로 주입 + 하드코딩 급수 클램프 → 폭 프레임을 vbW0로 고정.
  //        프레임이 고정이므로 pt/u가 보존되어 목표 pt에 **한 방에** 맞는다.
  // 2회차(예외): 폭이 프레임을 넘겨(라벨이 오히려 커진 경우) pt/u가 바뀐 때만 1회 보정.
  const plan = labelScalePlan();
  let raw, rawUsed, converted, convertedPreTrim, labels, scan;
  let inject = null, scalePtEst = null, frameW = null, tightW = null, nativeClamped = 0, passes = 0, pre = null;
  const iterLog = [];
  for (let iter = 0; ; iter++) {
    passes = iter + 1;
    raw = await ssrWithRetry(inject ? applyTheme(dslBase, palette, inject) : dsl, name);
    if (wantIcons) {
      const symbols = (raw.match(/<symbol\b/g) || []).length;
      if (!symbols) fail(`${name}: icons:true인데 <symbol> 0개 — 아이콘 API 미도달(오프라인?). 조용한 탈락 금지`);
    }
    if (!browser) {
      browser = await chromium.launch();
      page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });
    }
    // 테마 미도달 하드코딩 급수(배지)는 변환 **전** raw에서 밴드 안으로 클램프한다.
    rawUsed = raw;
    nativeClamped = 0;
    if (plan && scalePtEst) {
      const c = clampNativeText(raw, plan, scalePtEst);
      rawUsed = c.svg; nativeClamped = c.count;
    }
    let convertedRaw;
    try {
      ({ svg: convertedRaw, labels } = await convertForeignObjectText(page, rawUsed, FONT_DIR));
    } catch (e) {
      fail(`${name}: ${e.message.replace(/^.*Error: /s, "").split("\n")[0]}`);
    }
    if (!labels.length) fail(`${name}: 변환 후 텍스트 줄 0개 — DSL에 라벨이 없거나 변환 실패`);
    converted = sortDefsSymbols(convertedRaw);
    if ((converted.match(/<foreignObject/g) || []).length) fail(`${name}: foreignObject 잔존`);
    convertedPreTrim = converted;
    const trimmed = await trimViewBox(page, converted, frameW);
    converted = trimmed?.svg || converted;
    tightW = trimmed ? r3(trimmed.tightW) : null;
    scan = scanLabelPt(converted, widthKey);
    const pts = scan.sizes.map((s) => s.pt).filter((p) => typeof p === "number" && isFinite(p));
    const maxPt = pts.length ? Math.max(...pts) : null, minPt = pts.length ? Math.min(...pts) : null;
    iterLog.push({ pass: iter, inject, frameW: r3(frameW), contentW: tightW, nativeClamped, viewBoxW: r3(scan.vbW),
      ptPerUnit: scan.scalePt === null ? null : Math.round(scan.scalePt * 1e5) / 1e5,
      minPt: r3(minPt), maxPt: r3(maxPt) });
    if (iter === 0) pre = { viewBoxW: r3(scan.vbW), minPt: r3(minPt), maxPt: r3(maxPt),
      ratio: plan ? r3(maxPt / plan.bodyPt) : null };
    if (!plan || scan.scalePt === null || !pts.length) break;      // 주입 불가 — 종전 동작
    const inBand = maxPt <= plan.capPt + BAND_TOL_PT && minPt >= plan.floorPt - BAND_TOL_PT;
    if (iter === 0 && inBand) break;                               // 이미 밴드 안 — 손대지 않는다
    if (inject && inBand) break;                                   // 목표 달성
    if (iter >= LABEL_SCALE_MAX_ITER) break;                       // 반복 상한 — 남은 초과는 WARN이 말한다
    // 프레임을 고정하므로 다음 회차 pt/u = 이번 회차 pt/u. 목표 pt를 그대로 나누면 정확히 맞는다.
    // (0회차는 밀착 트림 폭이 곧 프레임이 되고, 이후 보정 회차는 그때의 실측 폭을 프레임으로 갱신.)
    frameW = scan.vbW;
    scalePtEst = scan.scalePt;
    const next = injectFromT(plan, plan.titlePt / scalePtEst);
    if (injectEq(inject, next)) break;                             // 고정점 도달(더 돌려도 같은 값)
    inject = next;
  }

  // pixelSelfCheck는 **최종 회차의** raw(클램프 반영) ↔ 변환본(트림 전)을 비교한다 —
  // 클램프를 변환 전에 걸었으므로 이 자기검증은 여전히 "fo2text 변환이 외형을 보존했는가"다.
  const check = await pixelSelfCheck(browser, rawUsed, convertedPreTrim, FONT_DIR, path.join(checkDir, name));
  if (check.ratio > PIXEL_TOLERANCE) {
    fail(`${name}: 변환 자기검증 실패 — 픽셀 상이율 ${(check.ratio * 100).toFixed(2)}% > ${PIXEL_TOLERANCE * 100}% (${checkDir}/${name}.diff.png 확인)`);
  }
  // 글자 밴드는 트림 후 최종 좌표계 기준으로 검사 (트림은 실크기를 키우는 방향).
  // 하한 = HARD(빌드 중단), 상한 = WARN(5단계 출생 강도).
  const floors = fontFloorViolations(scan);
  if (floors.length) fail(`${name}: 도해 내 글자 크기 하한 위반 — ${floors.join("; ")} (bf.width=${widthKey} 기준)`);
  const reportD = labelBandReport(scan, { name, kind, widthKey, scaled: !!inject });
  reportD.metrics.labelScale = plan ? {
    version: LABEL_SCALE.version, applied: !!inject, passes,
    targetPt: { title: r3(plan.titlePt), text: r3(plan.textPt), desc: r3(plan.descPt) },
    injectedUnits: inject, nativeClamped, pre,
    // frameSlack: 프레임 고정으로 생긴 오른쪽 여백 비율(= 1 − 실내용폭/프레임폭).
    // 라벨을 줄이면 그림이 명목 폭을 다 채우지 않는다 — 8단계 원장의 "템플릿·폭 적합" 축 입력.
    frameW: r3(frameW), contentW: tightW,
    frameSlack: frameW && tightW ? r3(1 - tightW / frameW) : 0,
    iterations: iterLog,
  } :{ version: LABEL_SCALE.version, applied: false, passes, reason: "labelBand.maxRatio 또는 body_pt 미선언", pre, iterations: iterLog };
  const bandD = emitBand(reportD, outMetrics);

  writeFileSync(outSvg, `<!--bf:dsl=sha256:${hash}-->\n${converted}`);
  writeFileSync(outLabels, JSON.stringify(labels, null, 2));
  rendered++;
  if (bandD.violated) bandWarns++;
  if (inject) {
    console.log(`${name}: 라벨 급수 강제 — 목표 title/text/desc `
      + `${r3(plan.titlePt)}/${r3(plan.textPt)}/${r3(plan.descPt)}pt · 주입 `
      + `${inject.title}/${inject.text}/${inject.desc}u · 배지 등 하드코딩 클램프 ${nativeClamped}건 · `
      + `${passes}회 수렴 · 전 ${pre.minPt}~${pre.maxPt}pt(×${pre.ratio}) → 후 `
      + `${bandD.metrics.minPt}~${bandD.metrics.maxPt}pt(×${bandD.metrics.ratio}) · `
      + `프레임 ${r3(frameW)}u 고정(pt/u 보존), 실내용 ${tightW}u — 오른쪽 여백 `
      + `${((bandD.metrics.labelScale.frameSlack || 0) * 100).toFixed(1)}%`);
  }
  console.log(`${name}: OK ${labels.length} labels, diff ${(check.ratio * 100).toFixed(2)}%, `
    + `${bandSummary(bandD.metrics)}, ${Date.now() - t0}ms`);
}

if (browser) await browser.close();
console.log(`diagrams done: ${rendered} rendered, ${skipped} cached`
  + (bandWarns ? ` — 라벨 밴드 상한 WARN ${bandWarns}건(재렌더분 기준)` : ""));
