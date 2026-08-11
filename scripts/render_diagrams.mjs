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
import { convertForeignObjectText, pixelSelfCheck } from "./fo2text.mjs";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = path.join(SKILL, "assets", "fonts");
const CONVERTER_VERSION = 2; // fo2text 알고리즘 변경 시 올려서 캐시 전체 무효화
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

const diagramsDir = path.join(bookDir, "diagrams");
const sidecars = existsSync(diagramsDir)
  ? readdirSync(diagramsDir).filter((f) => /^fig-\d+\.json$/.test(f)).sort()
  : [];
if (!sidecars.length) { console.log("no diagrams — skip"); process.exit(0); }

// SSR 모듈: 스킬 로컬 node_modules (버전 고정 0.2.19)
const skillRequire = createRequire(path.join(SKILL, "package.json"));
let renderToString, getTemplate;
try {
  ({ renderToString } = await import(skillRequire.resolve("@antv/infographic/ssr")));
  ({ getTemplate } = await import(skillRequire.resolve("@antv/infographic")));
} catch {
  fail("@antv/infographic 미설치 — 스킬 루트에서 `npm ci` 실행 필요");
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

function applyTheme(dsl, palette) {
  // 콘텐츠의 theme 블록(들여쓰기 연속 줄 포함)을 제거하고 스타일 팔레트를 강제한다.
  const stripped = dsl.replace(/^theme\r?\n(?:[ \t]+.*\r?\n?)*/gm, "").replace(/\s+$/, "");
  return `${stripped}\ntheme\n  palette ${palette.join(" ")}\n`;
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

function fontFloorViolations(svg, widthKey) {
  const minPt = dg.minFontPt;
  const widthMm = (dg.widths || {})[widthKey];
  if (!minPt || !widthMm) return [];
  const vb = svg.match(/viewBox="[-\d. ]*?([\d.]+) ([\d.]+)"\s*/);
  const vbW = vb ? parseFloat(vb[1]) : null;
  if (!vbW) return [`viewBox 폭을 읽지 못함 — minFontPt 검사 불가`];
  const scalePt = (widthMm * MM2PT) / vbW; // user unit -> 실제 pt
  const out = [];
  for (const m of svg.matchAll(/<text [^>]*font-size="([\d.]+)"/g)) {
    const pt = parseFloat(m[1]) * scalePt;
    if (pt < minPt - 0.05) out.push(`text ${m[1]}u ≈ ${pt.toFixed(1)}pt < ${minPt}pt 하한`);
  }
  return out;
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
let rendered = 0, skipped = 0;

for (const file of sidecars) {
  const name = file.replace(/\.json$/, "");
  const sidecar = JSON.parse(readFileSync(path.join(bookDir, "diagrams", file), "utf8"));
  const bf = sidecar.bf || {};
  const widthKey = bf.width || "full";
  if (!["full", "twothirds"].includes(widthKey)) fail(`${name}: bf.width는 full|twothirds`);
  let dsl = Array.isArray(sidecar.dsl) ? sidecar.dsl.join("\n") : sidecar.dsl;
  if (typeof dsl !== "string" || !dsl.trim().startsWith("infographic ")) {
    fail(`${name}: dsl은 'infographic <template>'로 시작하는 문자열(또는 줄 배열)`);
  }
  // AntV는 미지 템플릿명을 조용히 기본 템플릿으로 폴백한다(실측) — 오타 침묵 통과 차단
  const tplName = dsl.trim().split(/\s+/)[1];
  if (!getTemplate(tplName)) {
    fail(`${name}: 미지 템플릿 '${tplName}' — infographic-creator 스킬의 템플릿 목록 참조`);
  }
  const wantIcons = bf.icons === true;
  if (wantIcons && !dg.iconsAllowed) fail(`${name}: 이 스타일(${style})은 icons 미허용`);
  if (!wantIcons) dsl = stripIconLines(dsl);
  dsl = applyTheme(dsl, palette);

  const hash = createHash("sha256")
    .update(JSON.stringify({ dsl, width: widthKey, icons: wantIcons, v: CONVERTER_VERSION }))
    .digest("hex");
  const outSvg = path.join(assetsDir, `${name}.svg`);
  const outLabels = path.join(assetsDir, `${name}.labels.json`);
  if (existsSync(outSvg) && existsSync(outLabels)) {
    const head = readFileSync(outSvg, "utf8").slice(0, 120);
    if (head.includes(`bf:dsl=sha256:${hash}`)) { skipped++; console.log(`${name}: cache hit — skip`); continue; }
  }

  const t0 = Date.now();
  let raw = await ssrWithRetry(dsl, name);
  if (wantIcons) {
    const symbols = (raw.match(/<symbol\b/g) || []).length;
    if (!symbols) fail(`${name}: icons:true인데 <symbol> 0개 — 아이콘 API 미도달(오프라인?). 조용한 탈락 금지`);
  }

  if (!browser) {
    browser = await chromium.launch();
    page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 2 });
  }
  const { svg: convertedRaw, labels } = await convertForeignObjectText(page, raw, FONT_DIR);
  if (!labels.length) fail(`${name}: 변환 후 텍스트 줄 0개 — DSL에 라벨이 없거나 변환 실패`);
  let converted = sortDefsSymbols(convertedRaw);

  if ((converted.match(/<foreignObject/g) || []).length) fail(`${name}: foreignObject 잔존`);
  const floors = fontFloorViolations(converted, widthKey);
  if (floors.length) fail(`${name}: 도해 내 글자 크기 하한 위반 — ${floors.join("; ")} (bf.width=${widthKey} 기준)`);

  const check = await pixelSelfCheck(browser, raw, converted, FONT_DIR, path.join(checkDir, name));
  if (check.ratio > PIXEL_TOLERANCE) {
    fail(`${name}: 변환 자기검증 실패 — 픽셀 상이율 ${(check.ratio * 100).toFixed(2)}% > ${PIXEL_TOLERANCE * 100}% (${checkDir}/${name}.diff.png 확인)`);
  }

  writeFileSync(outSvg, `<!--bf:dsl=sha256:${hash}-->\n${converted}`);
  writeFileSync(outLabels, JSON.stringify(labels, null, 2));
  rendered++;
  console.log(`${name}: OK ${labels.length} labels, diff ${(check.ratio * 100).toFixed(2)}%, ${Date.now() - t0}ms`);
}

if (browser) await browser.close();
console.log(`diagrams done: ${rendered} rendered, ${skipped} cached`);
