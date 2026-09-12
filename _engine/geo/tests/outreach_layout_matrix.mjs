import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";
import { measureOutreachPage } from "./outreach_geometry_probe.mjs";

const args = Object.fromEntries(Array.from({ length: (process.argv.length - 2) / 2 }, (_, index) =>
  [process.argv[2 + index * 2].slice(2), process.argv[3 + index * 2]]));
for (const name of ["manifest", "playwright", "chromium", "output"]) assert.ok(args[name], name);
const manifest = JSON.parse(fs.readFileSync(args.manifest, "utf8"));
const output = path.resolve(args.output);
assert.ok(!fs.existsSync(output), "Keep prior evidence immutable; use a new --output");
fs.mkdirSync(output, { recursive: true });
const runtime = path.join(output, "runtime");
fs.mkdirSync(runtime, { recursive: true });
process.env.TMPDIR = runtime;
process.env.TMP = runtime;
process.env.TEMP = runtime;
const require = createRequire(path.resolve(args.playwright));
const { chromium } = require("playwright");
const mode = args.mode ?? "pilot";
const sides = (args.sides ?? "baseline,candidate").split(",");
const widths = args.widths ? args.widths.split(",").map(Number) : mode === "audit" ? [375, 390, 1024] : mode === "pilot" ? [320, 390, 1024] :
  mode === "supplement" ? [320, 1440] : manifest.viewports;
assert.ok(widths.every(width => manifest.viewports.includes(width)));
const motions = args.motions ? args.motions.split(",") : mode === "matrix" ? ["no-preference", "reduce"] : ["reduce"];
assert.ok(motions.every(motion => ["no-preference", "reduce"].includes(motion)));
const scripts = args.scripts ? args.scripts.split(",").map(value => {
  assert.ok(["true", "false"].includes(value)); return value === "true";
}) : [false, true];
let rows = manifest.rows.filter(row => mode === "audit" ? row.group.startsWith("audit-") :
  mode === "supplement" ? row.group.startsWith("supplement-") : row.group === "matrix");
if (mode === "pilot") rows = rows.filter(row => ["aibriefpack", "lumiletterspro", "zipbox"].includes(row.app));
if (args.locales) rows = rows.filter(row => args.locales.split(",").includes(row.locale));
if (args.apps) rows = rows.filter(row => args.apps.split(",").includes(row.app));
const sha = value => crypto.createHash("sha256").update(value).digest("hex");
const bounded = async (promise, label) => {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`Timeout: ${label}`)), 45000); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
};
const settleLayout = async (page, width) => {
  await page.evaluate(() => { history.scrollRestoration = "manual"; scrollTo(0, 0); });
  let previous;
  for (let attempt = 0; attempt < 12; attempt++) {
    await page.waitForTimeout(35);
    const current = await bounded(page.evaluate(() => {
      const nodes = [...document.querySelectorAll("h1,main,.iag-decision-card,.iag-decision-card__cta")];
      return JSON.stringify([innerWidth, scrollX, scrollY, document.documentElement.scrollWidth,
        ...nodes.map(node => {
          const bounds = node.getBoundingClientRect(), css = getComputedStyle(node);
          return [bounds.x, bounds.y, bounds.width, bounds.height, css.fontSize];
        })]);
    }), "stable layout");
    if (current === previous) return;
    previous = current;
  }
  throw new Error(`Layout did not settle at ${width}px`);
};
const mime = filename => {
  if (filename.endsWith(".css")) return "text/css";
  if (filename.endsWith(".js")) return "application/javascript";
  if (filename.endsWith(".json")) return "application/json";
  if (filename.endsWith(".svg")) return "image/svg+xml";
  if (filename.endsWith(".jpg") || filename.endsWith(".jpeg")) return "image/jpeg";
  if (filename.endsWith(".png")) return "image/png";
  if (filename.endsWith(".woff2")) return "font/woff2";
  return "application/octet-stream";
};
const cache = new Map();
const errors = [];
const requests = new Map();
const baselineByCase = new Map();
const results = fs.createWriteStream(path.join(output, "measurements.jsonl"));
const failuresFile = fs.createWriteStream(path.join(output, "failures.jsonl"));
const summary = {
  mode, locales: [...new Set(rows.map(row => row.locale))], apps: [...new Set(rows.map(row => row.app))],
  cases: 0, errors: 0, baselineFailures: 0, candidateFailures: 0,
  baselineGermanicCells: [], candidateGermanicCells: [],
  baselineCjkCells: [], candidateCjkCells: [],
  healthyComparisons: 0, unexpectedHealthyShifts: [],
  intentionalResponsiveShifts: [],
  stickyChecks: [],
  fonts: [], reducedMotionModes: motions, scriptModes: scripts,
  viewports: widths, sourceManifest: sha(fs.readFileSync(args.manifest)),
  startedAt: new Date().toISOString(),
  runnerSha256: sha(fs.readFileSync(fileURLToPath(import.meta.url))),
  probeSha256: sha(fs.readFileSync(fileURLToPath(new URL("./outreach_geometry_probe.mjs", import.meta.url)))),
};
const badSets = Object.fromEntries(["baselineGermanicCells", "candidateGermanicCells", "baselineCjkCells", "candidateCjkCells"].map(key => [key, new Set()]));
const browser = await chromium.launch({
  executablePath: path.resolve(args.chromium), headless: true,
  downloadsPath: path.join(runtime, "downloads"), tracesDir: path.join(runtime, "traces"),
  env: { ...process.env, TMPDIR: runtime },
});
try {
  summary.detectorControls = [];
  const controlContext = await browser.newContext({ viewport: { width: 320, height: 568 } });
  const controlPage = await controlContext.newPage();
  const fixtures = [
    {
      name: "nested-hidden-ancestors",
      source: '<div style="width:120px;overflow:hidden"><section style="width:90px;overflow:hidden"><a href="https://apps.apple.com/app/id1" style="display:inline-block;min-height:44px;white-space:nowrap">Download the complete application with all features</a></section></div>',
      check: result => result.failures.some(failure => failure.clips?.length >= 2),
    },
    {
      name: "natural-multiline-caption",
      source: '<div style="width:140px"><a href="https://apps.apple.com/app/id1" style="display:block;min-height:44px;line-height:1.6">Natural marketing captions wrap without cutting words.</a></div>',
      check: result => result.failures.length === 0,
    },
    {
      name: "actual-ink-overlap",
      source: '<p style="width:70px;font:24px/6px sans-serif">Overlapping glyph descenders and accents repeat on several lines</p>',
      check: result => result.failures.some(failure => failure.lineOverlap),
    },
    {
      name: "minimum-44px",
      source: '<button style="width:43px;height:43px;padding:0">Go</button>',
      check: result => result.failures.some(failure => failure.small),
    },
    {
      name: "inset-clip-path",
      source: '<div style="width:90px;clip-path:inset(0 20px 0 0)"><p>Wide clipped caption</p></div>',
      check: result => result.failures.some(failure => failure.clips?.some(clip => clip.clipPath !== "none")),
    },
    {
      name: "cjk-optical-punctuation-contained-ink",
      language: "zh-Hant",
      source: '<p style="width:30.5px;font:16px/1.6 Arial">甲】</p>',
      check: result => result.failures.length === 0,
    },
    {
      name: "cjk-real-ink-clipping",
      language: "zh-Hant",
      source: '<div style="width:16px;overflow:hidden"><p style="white-space:nowrap;font:16px/1.6 Arial">甲甲】</p></div>',
      check: result => result.failures.some(failure => failure.clips?.length),
    },
  ];
  for (const fixture of fixtures) {
    await controlPage.setContent(`<html lang="${fixture.language ?? "en"}"><body>${fixture.source}</body></html>`);
    const measured = await controlPage.evaluate(measureOutreachPage, { width: 320 });
    assert.ok(fixture.check(measured), `Geometry detector control failed: ${fixture.name}`);
    summary.detectorControls.push({ name: fixture.name, pass: true });
  }
  await controlContext.close();
  profiles: for (const javascript of scripts) {
    for (const motion of motions) {
      for (const side of sides) {
        const root = manifest[side];
        const parallelContexts = mode === "matrix" || mode === "supplement" ? 4 : mode === "audit" ? 2 : 1;
        const batches = Array.from({ length: parallelContexts }, (_, index) =>
          rows.slice(Math.ceil(rows.length / parallelContexts) * index, Math.ceil(rows.length / parallelContexts) * (index + 1))).filter(batch => batch.length);
        await Promise.all(batches.map(async batch => {
        const context = await browser.newContext({
          viewport: { width: widths[0], height: 900 }, isMobile: true, hasTouch: true,
          deviceScaleFactor: 1, javaScriptEnabled: javascript, reducedMotion: motion,
          serviceWorkers: "block",
        });
        if (javascript) await context.addInitScript(() => {
          Object.defineProperty(navigator, "share", { configurable: true, value: async () => { throw new DOMException("Offline regression fixture", "AbortError"); } });
          Object.defineProperty(navigator, "canShare", { configurable: true, value: () => true });
        });
        let active;
        await context.route("**/*", async route => {
          const request = route.request(), url = request.url();
          if (request.method() !== "GET") {
            requests.set(request.method() + " " + url, "blocked-mutation");
            return route.abort();
          }
          if (request.isNavigationRequest()) {
            return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8",
              body: fs.readFileSync(path.join(root, active.relative)) });
          }
          const relative = decodeURIComponent(new URL(url).pathname).replace(/^\/ios-app-guide\//, "");
          const local = path.resolve(root, relative);
          let resource;
          if (local.startsWith(root + path.sep) && fs.existsSync(local) && fs.statSync(local).isFile()) resource = local;
          else resource = manifest.external_cache[url];
          if (!resource) {
            requests.set(url, "blocked-unavailable-resource");
            return route.abort();
          }
          if (!cache.has(resource)) cache.set(resource, fs.readFileSync(resource));
          let contentType = mime(relative);
          const body = cache.get(resource);
          if (contentType === "application/octet-stream") {
            if (body[0] === 0xff && body[1] === 0xd8) contentType = "image/jpeg";
            else if (body.toString("utf8", 0, 250).includes("<svg")) contentType = "image/svg+xml";
          }
          return route.fulfill({ status: 200, contentType, body });
        });
        const page = await context.newPage();
        const cdp = await context.newCDPSession(page);
        await cdp.send("DOM.enable");
        await cdp.send("CSS.enable");
        const sampledFonts = new Set();
        for (const [index, row] of batch.entries()) {
          if (mode === "audit" && ((row.group === "audit-germanic" && javascript) || (row.group === "audit-cjk" && !javascript))) continue;
          active = row;
          try {
            await page.goto(row.url, { waitUntil: "load", timeout: 45000 });
            await bounded(page.evaluate(async () => { await document.fonts.ready; return document.fonts.status; }), "fonts.ready");
            const rowWidths = mode === "audit" ? row.group === "audit-germanic" ? [375] : [390, 1024] : widths;
            for (const width of rowWidths) {
              const height = mode === "audit" ? row.group === "audit-germanic" ? 812 : 880 :
                ({ 320: 568, 375: 812, 390: 844, 768: 1024, 1024: 768, 1440: 900 }[width]);
              await page.setViewportSize({ width, height });
              await settleLayout(page, width);
              const result = await bounded(page.evaluate(measureOutreachPage, { width }), "Range geometry");
              const key = `${row.group}:${row.locale}:${row.app}:${width}:${javascript}:${motion}`;
              assert.equal(result.fontStatus, "loaded");
              assert.ok(result.fonts.every(font => font.status === "loaded"));
              assert.equal(result.reducedMotion, motion === "reduce");
              if (["ar-SA", "ur-PK", "he"].includes(row.locale)) assert.equal(result.direction, "rtl");
              const failed = result.horizontalOverflow || result.failures.length > 0 || result.actionOverlaps.length > 0;
              summary.cases++;
              if (failed) summary[side === "baseline" ? "baselineFailures" : "candidateFailures"]++;
              if (row.group === "audit-germanic" && result.legacyAppleClips) badSets[`${side}GermanicCells`].add(`${row.locale}/${row.app}`);
              if (row.group === "audit-cjk" && result.legacyCjkOverflow) badSets[`${side}CjkCells`].add(`${row.locale}/${row.app}`);
              if (javascript && result.mobileBarPresent) assert.ok(result.mobileScriptActive, "First-party mobile CTA script did not execute");
              if (!javascript) assert.ok(!result.mobileScriptActive, "Page scripts ran with JavaScript disabled");
              if (side === "baseline") baselineByCase.set(key, { healthy: !failed, anchors: result.anchors, controls: result.controls });
              else if (baselineByCase.get(key)?.healthy) {
                summary.healthyComparisons++;
                const before = baselineByCase.get(key).anchors;
                const shifts = [];
                for (let position = 0; position < Math.min(before.length, result.anchors.length); position++) {
                  const first = before[position], second = result.anchors[position];
                  if (first.selector === second.selector) {
                    const fields = Object.fromEntries(["left", "top", "width", "height"].map(field =>
                      [field, second.bounds[field] - first.bounds[field]]).filter(([, delta]) => Math.abs(delta) > 1));
                    if (Object.keys(fields).length) shifts.push({ selector: first.selector, fields });
                  }
                }
                if (shifts.length) {
                  const previousControls = baselineByCase.get(key).controls;
                  const wrapChanges = result.controls.flatMap((control, position) => {
                    const old = previousControls[position];
                    return old && old.selector === control.selector && old.text === control.text &&
                      old.whiteSpace === "nowrap" && control.whiteSpace === "normal" &&
                      control.lines > old.lines && control.bounds.height > old.bounds.height
                      ? [{ selector: control.selector, lines: [old.lines, control.lines], heightDelta: control.bounds.height - old.bounds.height }]
                      : [];
                  });
                  const containerWidthChanged = shifts.some(shift =>
                    /^(main|aside\.iag-decision-card|img\.iag-decision-card__icon)$/.test(shift.selector) &&
                    ("width" in shift.fields || "left" in shift.fields));
                  const scriptLeading = ["th", "ar-SA", "ur-PK", "vi"].includes(row.locale) && !containerWidthChanged;
                  const unrelatedMove = shifts.some(shift => shift.selector === "h1" || shift.selector === "img.iag-decision-card__icon");
                  if ((wrapChanges.length && !unrelatedMove && !containerWidthChanged) || scriptLeading) {
                    summary.intentionalResponsiveShifts.push({ key, reason: scriptLeading ? "script ink-safe leading and bidi" : "natural CTA wrapping", wrapChanges, shifts });
                  } else {
                    summary.unexpectedHealthyShifts.push({ key, shifts });
                  }
                }
              }
              const record = { key, side, locale: row.locale, app: row.app, width, height, javascript, motion,
                failed, ...result };
              if (!results.write(JSON.stringify(record) + "\n")) await new Promise(resolve => results.once("drain", resolve));
              if (failed) failuresFile.write(JSON.stringify(record) + "\n");
              if (!sampledFonts.has(row.locale)) {
                const { root: documentRoot } = await cdp.send("DOM.getDocument");
                const actualFonts = [];
                for (const selector of ["h1", ".iag-decision-card__terms", ".iag-decision-card__cta"]) {
                  const { nodeId } = await cdp.send("DOM.querySelector", { nodeId: documentRoot.nodeId, selector });
                  if (!nodeId) continue;
                  const fontData = await cdp.send("CSS.getPlatformFontsForNode", { nodeId });
                  assert.ok(fontData.fonts.length);
                  assert.ok(fontData.fonts.every(font => font.glyphCount > 0 && !/LastResort|notdef/i.test(font.familyName)));
                  actualFonts.push({ selector, fonts: fontData.fonts });
                }
                summary.fonts.push({ side, locale: row.locale, javascript, motion, actualFonts });
                sampledFonts.add(row.locale);
              }
              if (javascript && mode === "matrix" && side === "candidate" && row.app === manifest.apps[0] && result.mobileBarPresent) {
                if (width >= 768) {
                  assert.equal(await page.locator("[data-mobile-store-cta]").evaluate(node => getComputedStyle(node).display), "none");
                  summary.stickyChecks.push({ locale: row.locale, width, motion, hiddenOnDesktop: true });
                } else {
                  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
                  let lastBar;
                  let ready = false;
                  for (let attempt = 0; attempt < 20; attempt++) {
                    await page.waitForTimeout(35);
                    const state = await page.locator("[data-mobile-store-cta]").evaluate(node => {
                      const rect = node.getBoundingClientRect();
                      return { visible: node.classList.contains("is-visible"), opacity: getComputedStyle(node).opacity,
                        top: rect.top, height: rect.height };
                    });
                    if (state.visible && state.opacity === "1" && JSON.stringify(state) === lastBar) { ready = true; break; }
                    lastBar = JSON.stringify(state);
                  }
                  assert.ok(ready, "Sticky CTA did not reach its visible state");
                  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
                  await page.waitForTimeout(40);
                  const sticky = await page.evaluate(measureOutreachPage, { width });
                  const bar = await page.locator("[data-mobile-store-cta]").boundingBox();
                  assert.ok(bar.y >= 0 && bar.y + bar.height <= height + 1, "Sticky CTA escaped viewport");
                  assert.equal(sticky.failures.length, 0, "Sticky CTA state has clipped text or small controls");
                  assert.equal(sticky.actionOverlaps.length, 0, "Sticky CTA overlaps another actionable control");
                  summary.stickyChecks.push({ locale: row.locale, width, motion, pass: true, height: bar.height });
                }
              }
            }
          } catch (error) {
            const failure = { side, app: row.app, locale: row.locale, javascript, motion, error: error.message.slice(0, 350) };
            errors.push(failure);
            fs.appendFileSync(path.join(output, "errors.jsonl"), JSON.stringify(failure) + "\n");
          }
          if ((index + 1) % 200 === 0) console.log(JSON.stringify({ side, javascript, motion, processed: index + 1, batchTotal: batch.length, candidateFailures: summary.candidateFailures, errors: errors.length }));
        }
        await context.close();
        }));
        if (side === "candidate" && (summary.candidateFailures || errors.length)) {
          summary.stoppedAfterFailingProfile = true;
          break profiles;
        }
      }
    }
  }
} finally {
  await browser.close();
  results.end();
  failuresFile.end();
  await Promise.all([
    new Promise(resolve => results.on("finish", resolve)),
    new Promise(resolve => failuresFile.on("finish", resolve)),
  ]);
}
summary.errors = errors.length;
summary.errorDetails = errors;
summary.requests = [...requests].map(([url, status]) => ({ url, status }));
for (const key of Object.keys(badSets)) summary[key] = [...badSets[key]].sort();
summary.finishedAt = new Date().toISOString();
fs.writeFileSync(path.join(output, "summary.json"), JSON.stringify(summary, null, 2) + "\n");
console.log(JSON.stringify({
  cases: summary.cases, errors: errors.length, baselineFailures: summary.baselineFailures,
  candidateFailures: summary.candidateFailures,
  germanic: [summary.baselineGermanicCells.length, summary.candidateGermanicCells.length],
  cjk: [summary.baselineCjkCells.length, summary.candidateCjkCells.length],
  healthyComparisons: summary.healthyComparisons, unexpectedShifts: summary.unexpectedHealthyShifts.length,
}));
if (errors.length || summary.candidateFailures) process.exitCode = 1;
