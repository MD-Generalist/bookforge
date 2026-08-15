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
import { convertForeignObjectText, normalizeAuthoredSvg, pixelSelfCheck } from "./fo2text.mjs";

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

// 템플릿 적합성 실측 원장 — blocked 템플릿은 SSR 전에 차단 (minFontPt 사후 검사와 이중 방어)
const ledger = JSON.parse(readFileSync(path.join(SKILL, "references", "diagram-ledger.json"), "utf8"));

// authored SVG 팔레트 강제 — 허용색 = 스타일 팔레트 + 뉴트럴(백·먹·회색 램프)
function normHex(c) {
  if (!c) return null;
  c = c.trim().toLowerCase();
  const m = c.match(/^rgba?\((\d+)[, ]+(\d+)[, ]+(\d+)/);
  if (m) return "#" + [m[1], m[2], m[3]].map((v) => (+v).toString(16).padStart(2, "0")).join("");
  if (/^#[0-9a-f]{3}$/.test(c)) return "#" + [...c.slice(1)].map((ch) => ch + ch).join("");
  if (/^#[0-9a-f]{6}$/.test(c)) return c;
  return c; // none·currentColor·url(#...) 등은 상위에서 별도 판단
}
function alienColors(svg, palette) {
  const allowed = new Set(palette.map((c) => normHex(c)));
  const out = new Set();
  for (const m of svg.matchAll(/(?:fill|stroke)="([^"]+)"/g)) {
    const v = m[1].trim().toLowerCase();
    if (v === "none" || v === "transparent" || v === "currentcolor" || v.startsWith("url(")) continue;
    const hex = normHex(v);
    if (!hex || !hex.startsWith("#")) continue;
    if (allowed.has(hex)) continue;
    // 뉴트럴 허용: 무채색(채도 미미) 램프
    const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    if (Math.max(r, g, b) - Math.min(r, g, b) <= 16) continue;
    out.add(hex);
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
    const hashA = createHash("sha256")
      .update(JSON.stringify({ svg: rawAuthored, width: widthKey, v: CONVERTER_VERSION }))
      .digest("hex");
    const outSvgA = path.join(assetsDir, `${name}.svg`);
    const outLabelsA = path.join(assetsDir, `${name}.labels.json`);
    if (existsSync(outSvgA) && existsSync(outLabelsA)) {
      const head = readFileSync(outSvgA, "utf8").slice(0, 130);
      if (head.includes(`bf:authored=sha256:${hashA}`)) { skipped++; console.log(`${name}: cache hit — skip`); continue; }
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
    const aliens = alienColors(normalized, palette);
    if (aliens.length) {
      fail(`${name}: 팔레트 밖 유채색 ${aliens.join(", ")} — styles/${style} tokens.diagram.palette + 뉴트럴만 허용`);
    }
    const floorsA = fontFloorViolations(normalized, widthKey);
    if (floorsA.length) fail(`${name}: 글자 크기 하한 위반 — ${floorsA.join("; ")} (bf.width=${widthKey})`);
    const checkA = await pixelSelfCheck(browser, rawAuthored, normalized, FONT_DIR, path.join(checkDir, name));
    if (checkA.ratio > PIXEL_TOLERANCE) {
      fail(`${name}: 정규화 자기검증 실패 — 픽셀 상이율 ${(checkA.ratio * 100).toFixed(2)}% (${checkDir}/${name}.diff.png)`);
    }
    writeFileSync(outSvgA, `<!--bf:authored=sha256:${hashA}-->\n${normalized}`);
    writeFileSync(outLabelsA, JSON.stringify(labelsA, null, 2));
    rendered++;
    console.log(`${name}: OK (authored) ${labelsA.length} labels, diff ${(checkA.ratio * 100).toFixed(2)}%, ${Date.now() - tA}ms`);
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
    fail(`${name}: 템플릿 '${tplName}'은 실측 원장에서 차단(라벨이 ${ledger.floor_pt}pt 하한 도달 불가) — 대안: sequence-timeline-simple·sequence-column-vertical-arrow 등 원장 ok 템플릿`);
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
  let convertedRaw, labels;
  try {
    ({ svg: convertedRaw, labels } = await convertForeignObjectText(page, raw, FONT_DIR));
  } catch (e) {
    fail(`${name}: ${e.message.replace(/^.*Error: /s, "").split("\n")[0]}`);
  }
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
