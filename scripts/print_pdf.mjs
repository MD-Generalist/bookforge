// bookforge: HTML -> PDF via Playwright Chromium (preferCSSPageSize).
// Usage: NODE_PATH=$(npm root -g) node print_pdf.mjs <input.html> <output.pdf>
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const [html, out] = process.argv.slice(2);
if (!html || !out) { console.error("usage: print_pdf.mjs <in.html> <out.pdf>"); process.exit(2); }

const browser = await chromium.launch();
const page = await browser.newPage();
page.on("console", m => { if (m.type() === "error") console.error("[page]", m.text()); });
await page.goto("file://" + require("path").resolve(html), { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.pdf({
  path: out,
  preferCSSPageSize: true,
  printBackground: true,
  displayHeaderFooter: false,
});
await browser.close();
console.log("OK pdf:", out);
