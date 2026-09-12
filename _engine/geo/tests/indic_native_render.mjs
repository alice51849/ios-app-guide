// Offline DOM/font evidence only; no shared-layout, screenshot or Simulator claim.
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {createRequire} from "node:module";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  assert.ok(process.argv[index].startsWith("--") && process.argv[index + 1]);
  args.set(process.argv[index].slice(2), path.resolve(process.argv[index + 1]));
}
for (const key of ["playwright", "chromium", "candidates", "runtime", "output"]) assert.ok(args.has(key), key);
const require = createRequire(args.get("playwright"));
const {chromium} = require("playwright");
const runtime = args.get("runtime");
fs.mkdirSync(runtime, {recursive: true});
process.env.TMPDIR = runtime;
const root = args.get("candidates");
const inventory = JSON.parse(fs.readFileSync(path.join(root, "content-inventory.json"), "utf8"));
assert.equal(inventory.cells.length, 470);
assert.equal(new Set(inventory.cells.map(row => row.app_id)).size, 47);
const selected = {
  "bn-BD": "lumibopomofo", "gu-IN": "aim990", hi: "lumimissionpro",
  "kn-IN": "lumimathpro", "ml-IN": "aibriefpack", "mr-IN": "lumibopomofo",
  "or-IN": "tripplanet", "pa-IN": "lumibopomofo", "ta-IN": "lumiletterspro",
  "te-IN": "aim990",
};
const digest = value => crypto.createHash("sha256").update(value).digest("hex");
const browser = await chromium.launch({
  executablePath: args.get("chromium"), headless: true,
  downloadsPath: path.join(runtime, "downloads"),
});
const records = [];
try {
  for (const width of [390, 1024]) {
    const context = await browser.newContext({viewport: {width, height: 900}, javaScriptEnabled: false, serviceWorkers: "block"});
    await context.route("**/*", route => route.abort());
    const page = await context.newPage();
    for (const [locale, key] of Object.entries(selected)) {
      const file = path.join(root, locale, `${key}.html`);
      const source = fs.readFileSync(file);
      const cell = inventory.cells.find(row => row.locale === locale && row.app_key === key);
      await page.setContent(source.toString("utf8"), {waitUntil: "domcontentloaded"});
      const result = await page.evaluate(() => ({
        locale: document.documentElement.lang,
        direction: getComputedStyle(document.querySelector("main")).direction,
        text: document.querySelector("main").textContent,
        stores: [...document.querySelectorAll("a[href]")].map(node => node.href).filter(url => url.includes("apps.apple.com")),
      }));
      assert.equal(result.locale, locale);
      assert.equal(result.direction, "ltr");
      assert.ok(result.text.includes(cell.publisher_disclosure));
      assert.ok(!result.text.includes("\u25cc") && !result.text.includes("\ufffd"));
      assert.ok(!/Pro edition|Full Pro edition|Unlock your potential/.test(result.text));
      if (locale === "bn-BD") {
        assert.deepEqual(result.stores, []);
        assert.ok(result.text.includes("Apple App Store এখনো বাংলাদেশে"));
      } else {
        assert.ok(result.stores.length > 0);
        for (const url of result.stores) assert.equal(new URL(url).pathname, `/in/app/id${cell.app_id}`);
      }
      let fontEvidence = null;
      if (locale === "or-IN" || locale === "kn-IN") {
        const text = locale === "or-IN" ? "ଦ୍ୱାରା ୱିଜେଟ୍।" : "ಸ್ಕ್ಯಾನ್ ದುಡುಕಿನ ಖರೀದಿ।";
        const probe = await page.evaluate(text => {
          const span = document.createElement("span");
          span.id = "indic-shaping-probe";
          span.textContent = text;
          span.style.font = "28px -apple-system, BlinkMacSystemFont, sans-serif";
          document.querySelector("main").appendChild(span);
          return {text: span.textContent, width: span.getBoundingClientRect().width};
        }, text);
        assert.equal(probe.text, text);
        assert.ok(probe.width > 0);
        const cdp = await context.newCDPSession(page);
        await cdp.send("DOM.enable");
        await cdp.send("CSS.enable");
        const document = await cdp.send("DOM.getDocument");
        const node = await cdp.send("DOM.querySelector", {nodeId: document.root.nodeId, selector: "#indic-shaping-probe"});
        const {fonts} = await cdp.send("CSS.getPlatformFontsForNode", {nodeId: node.nodeId});
        assert.ok(fonts.every(font => !/LastResort/i.test(font.familyName)));
        assert.ok(fonts.some(font => (locale === "or-IN" ? /Oriya|Odia/i : /Kannada/i).test(font.familyName) && font.glyphCount > 0));
        fontEvidence = {text, fonts};
        await cdp.detach();
      }
      assert.equal(digest(source), digest(fs.readFileSync(file)));
      records.push({key, locale, width, source_sha256: digest(source), direction: result.direction,
        app_store_links: result.stores.length, font_evidence: fontEvidence});
    }
    await context.close();
  }
} finally {
  await browser.close();
}
assert.equal(records.length, 20);
fs.writeFileSync(args.get("output"), JSON.stringify({
  status: "PASS", viewport_checks: 20, exact_locales: Object.keys(selected),
  glyph_font_checks: records.filter(row => row.font_evidence).length,
  layout_pass_claimed: false, source_mutations: 0, records,
}, null, 2) + "\n");
console.log(JSON.stringify({status: "PASS", viewport_checks: 20, glyph_font_checks: 4, source_mutations: 0}));
