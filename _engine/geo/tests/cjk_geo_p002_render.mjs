// Offline DOM gate. Supply an existing Playwright package.json, Chromium
// executable, candidate directory, original Guide pages and owned runtime path.
// No Simulator, screenshots, shared CSS edits or external requests.
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const argumentsByName = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  assert.ok(process.argv[index].startsWith("--") && process.argv[index + 1]);
  argumentsByName.set(process.argv[index].slice(2), path.resolve(process.argv[index + 1]));
}
for (const name of ["playwright", "chromium", "candidates", "original-pages", "runtime", "output"]) {
  assert.ok(argumentsByName.has(name), `Missing --${name}`);
}
const require = createRequire(argumentsByName.get("playwright"));
const { chromium } = require("playwright");
const runtime = argumentsByName.get("runtime");
fs.mkdirSync(runtime, { recursive: true });
process.env.TMPDIR = runtime;
process.env.TMP = runtime;
process.env.TEMP = runtime;
const digest = value => crypto.createHash("sha256").update(value).digest("hex");
const inventory = JSON.parse(fs.readFileSync(path.join(argumentsByName.get("candidates"), "content-inventory.json"), "utf8"));
assert.equal(inventory.cells.length, 470);
const repaired = inventory.cells.filter(row => row.repair_scope === "P0-02");
assert.equal(repaired.length, 12);
assert.equal(repaired.filter(row => row.locale === "ar-SA").length, 2);
assert.equal(repaired.filter(row => row.locale === "ur-PK").length, 0);
const keys = ["lumibopomofopro", "lumiletterspro"];
const browser = await chromium.launch({
  executablePath: argumentsByName.get("chromium"),
  headless: true,
  downloadsPath: path.join(runtime, "downloads"),
  tracesDir: path.join(runtime, "traces"),
  env: { ...process.env, TMPDIR: runtime },
});
const records = [];
try {
  for (const width of [390, 1024]) {
    const context = await browser.newContext({
      viewport: { width, height: 880 },
      javaScriptEnabled: false,
      serviceWorkers: "block",
    });
    await context.route("**/*", route => route.abort());
    const page = await context.newPage();
    for (const locale of ["ar-SA", "ur-PK"]) {
      for (const key of keys) {
        const root = locale === "ar-SA" ? argumentsByName.get("candidates") : argumentsByName.get("original-pages");
        const file = path.join(root, locale, `${key}.html`);
        const original = fs.readFileSync(file);
        await page.setContent(original.toString("utf8"), { waitUntil: "domcontentloaded" });
        const result = await page.evaluate(() => ({
          language: document.documentElement.lang,
          direction: getComputedStyle(document.querySelector("main") ?? document.body).direction,
          text: document.body.textContent,
          isolates: [...document.querySelectorAll("main bdi")].map(node => ({
            text: node.textContent,
            direction: getComputedStyle(node).direction,
            bidi: getComputedStyle(node).unicodeBidi,
          })),
        }));
        assert.equal(result.language, locale);
        assert.equal(result.direction, "rtl");
        if (locale === "ar-SA") {
          assert.ok(!result.text.includes("Pro edition"));
          assert.ok(result.isolates.length > 0);
          for (const isolate of result.isolates) {
            assert.ok(isolate.text.length > 0);
            assert.equal(isolate.direction, "ltr");
            assert.equal(isolate.bidi, "isolate");
            assert.ok(!/[\u0600-\u06ff]/u.test(isolate.text));
          }
        } else {
          assert.ok(/[ٹڈڑںھہۂے]/u.test(result.text));
        }
        assert.equal(digest(original), digest(fs.readFileSync(file)));
        records.push({
          key, locale, width,
          source_sha256: digest(original),
          direction: result.direction,
          isolates: result.isolates.length,
          scope: locale === "ar-SA" ? "repaired_P0-02" : "unchanged_Urdu_readback",
        });
      }
    }
    await context.close();
  }
} finally {
  await browser.close();
}
fs.mkdirSync(path.dirname(argumentsByName.get("output")), { recursive: true });
fs.writeFileSync(argumentsByName.get("output"), JSON.stringify({
  status: "PASS",
  repaired_arabic_cells: 2,
  unchanged_urdu_cells: 2,
  viewport_checks: records.length,
  layout_or_glyph_pass_claimed: false,
  screenshots: 0,
  records,
}, null, 2) + "\n");
console.log(JSON.stringify({ status: "PASS", viewport_checks: records.length, repaired_arabic_cells: 2, unchanged_urdu_cells: 2 }));
