"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const {spawn} = require("node:child_process");

const pages = path.resolve(process.argv[2]);
const workspace = path.resolve(process.argv[3]);
const chrome = process.env.CHROME_BINARY || [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"
].find((file) => fs.existsSync(file));
if (!chrome || !fs.existsSync(chrome)) {
  throw new Error("No Chromium browser is installed. Set CHROME_BINARY to an existing isolated test browser.");
}

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(predicate, limit = 15000) {
  const start = Date.now();
  while (Date.now() - start < limit) {
    const result = await predicate();
    if (result) return result;
    await pause(100);
  }
  throw new Error("Timed out waiting for browser state.");
}

async function connect(url) {
  const socket = new WebSocket(url);
  const pending = new Map();
  const listeners = new Map();
  let sequence = 0;
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const {resolve, reject, timer} = pending.get(message.id);
      clearTimeout(timer);
      pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    } else if (listeners.has(message.method)) {
      for (const listener of listeners.get(message.method)) listener(message.params);
    }
  });
  socket.addEventListener("close", () => {
    for (const {reject, timer} of pending.values()) {
      clearTimeout(timer);
      reject(new Error("Browser connection closed."));
    }
    pending.clear();
  });
  return {
    socket,
    on(method, listener) {
      if (!listeners.has(method)) listeners.set(method, []);
      listeners.get(method).push(listener);
    },
    send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = ++sequence;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + " timed out")); }, 15000);
        pending.set(id, {resolve, reject, timer});
        socket.send(JSON.stringify({id, method, params}));
      });
    }
  };
}

(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(pages, "data/hero-tasks/manifest.json"), "utf8"));
  const prefix = new URL(manifest.records[0].url).pathname.split("/").slice(0, -3).join("/");
  const requests = [];
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    const relative = pathname.startsWith(prefix + "/") ? pathname.slice(prefix.length + 1) : "";
    const filename = path.resolve(pages, relative);
    requests.push(pathname);
    if (!filename.startsWith(pages + path.sep) || !fs.existsSync(filename) || !fs.statSync(filename).isFile()) {
      response.writeHead(404).end();
      return;
    }
    const mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".csv": "text/csv", ".json": "application/json"};
    response.writeHead(200, {"Content-Type": (mime[path.extname(filename)] || "application/octet-stream") + ";charset=utf-8", "Cache-Control": "no-store"});
    response.end(fs.readFileSync(filename));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = "http://127.0.0.1:" + server.address().port;
  const profile = path.join(workspace, "browser-profile");
  const downloads = path.join(workspace, "downloads");
  fs.mkdirSync(downloads, {recursive: true});
  const child = spawn(chrome, [
    "--headless=new", "--no-first-run", "--no-default-browser-check",
    "--disable-background-networking", "--disable-component-update", "--disable-sync",
    "--disable-breakpad", "--disable-crash-reporter", "--metrics-recording-only", "--no-proxy-server",
    "--password-store=basic", "--use-mock-keychain",
    "--user-data-dir=" + profile, "--remote-debugging-port=0",
    "--remote-debugging-address=127.0.0.1", "about:blank"
  ], {stdio: ["ignore", "ignore", "pipe"], env: {...process.env, TMPDIR: workspace}});
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr = (stderr + chunk.toString()).slice(-4000); });
  let browser, page;
  try {
    const portFile = path.join(profile, "DevToolsActivePort");
    const port = await until(() => {
      if (child.exitCode !== null) throw new Error("Chromium exited: " + stderr);
      return fs.existsSync(portFile) && fs.readFileSync(portFile, "utf8").split("\n")[0];
    });
    const info = await (await fetch("http://127.0.0.1:" + port + "/json/version")).json();
    browser = await connect(info.webSocketDebuggerUrl);
    await browser.send("Browser.setDownloadBehavior", {behavior: "allow", downloadPath: downloads});
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list")).json();
    page = await connect(targets.find((target) => target.type === "page").webSocketDebuggerUrl);
    await page.send("Page.enable");
    await page.send("Runtime.enable");
    let acceptDialog = true;
    page.on("Page.javascriptDialogOpening", () => {
      page.send("Page.handleJavaScriptDialog", {accept: acceptDialog}).catch(() => {});
    });
    await page.send("Network.enable");
    await page.send("Fetch.enable", {patterns: [{urlPattern: "*"}]});
    const external = [];
    const failures = [];
    page.on("Network.loadingFailed", (event) => failures.push(event.errorText));
    page.on("Fetch.requestPaused", (event) => {
      if (event.request.url.startsWith(origin + "/")) {
        page.send("Fetch.continueRequest", {requestId: event.requestId}).catch(() => {});
      } else {
        external.push(event.request.url);
        page.send("Fetch.failRequest", {requestId: event.requestId, errorReason: "BlockedByClient"}).catch(() => {});
      }
    });
    const evaluate = async (expression) => {
      const result = await page.send("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
      if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    async function navigate(record, width = 360) {
      await page.send("Emulation.setDeviceMetricsOverride", {width, height: 568, deviceScaleFactor: 1, mobile: false});
      const navigation = await page.send("Page.navigate", {url: origin + prefix + "/" + record.path});
      if (navigation.errorText) throw new Error(navigation.errorText);
      try {
        await until(async () => {
          try {
            return await evaluate(`document.documentElement?.lang===${JSON.stringify(record.locale)} &&
              document.readyState!=="loading" && document.getElementById("hero-form")?.dataset.ready==="true"`);
          } catch (error) {
            if (/context|navigat/i.test(error.message)) return false;
            throw error;
          }
        }, 30000);
      } catch (error) {
        throw new Error(error.message + " " + JSON.stringify({locale: record.locale, requests: requests.slice(-8), external: external.slice(-8), failures}));
      }
      const state = await evaluate(`({
        locale:document.documentElement.lang,
        ready:typeof HeroTaskCore==="object"&&!document.getElementById("download-csv").disabled,
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        scripts:[...document.scripts].filter(s=>s.src).length,
        name:document.querySelector("[data-field=name]").value
      })`);
      assert.equal(state.locale, record.locale);
      assert.equal(state.ready, true, record.locale);
      assert.equal(state.overflow, false, record.locale + " overflow at " + width);
      assert.equal(state.scripts, 2);
      assert.equal(await evaluate(`([...document.querySelectorAll("h1,.fields label,.totals p")]).every(
        element=>element.scrollWidth<=element.clientWidth+1&&
          element.getBoundingClientRect().height<=parseFloat(getComputedStyle(element).lineHeight)+1
      )`), true, record.locale + " primary labels remain complete on one line");
      assert.equal(await evaluate(`(()=>{
        const rect=document.getElementById("download-csv").getBoundingClientRect();
        return rect.height>=44&&rect.top>=0&&rect.bottom<=innerHeight;
      })()`), true, record.locale + " primary action is visible");
      assert.equal(await evaluate(`(()=>{
        const result=document.querySelector(".totals").getBoundingClientRect();
        const action=document.getElementById("download-csv").getBoundingClientRect();
        return result.top>=0&&result.bottom+8<=action.top;
      })()`), true, record.locale + " first-screen results are not covered");
    }
    for (const record of manifest.records) {
      await navigate(record, 320);
      if (process.env.HERO_SCREENSHOT_DIR && ["en-US", "ar-SA", "bn-BD"].includes(record.locale)) {
        const directory = path.resolve(process.env.HERO_SCREENSHOT_DIR);
        assert(directory.startsWith(path.dirname(workspace) + path.sep));
        fs.mkdirSync(directory, {recursive: true});
        const screenshot = await page.send("Page.captureScreenshot", {format: "png"});
        fs.writeFileSync(path.join(directory, record.locale + ".png"), Buffer.from(screenshot.data, "base64"));
      }
      await page.send("Emulation.setDeviceMetricsOverride", {width: 1366, height: 1024, deviceScaleFactor: 1, mobile: false});
      assert.equal(await evaluate("document.documentElement.scrollWidth>innerWidth+1"), false, record.locale);
      assert.equal(await evaluate("Object.keys(localStorage).length+Object.keys(sessionStorage).length"), 0);
    }
    const english = manifest.records.find((record) => record.locale === "en-US");
    await navigate(english);
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("hourly-income");input.value="0";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true);
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-purchase").click()');
    assert.equal(await evaluate('document.getElementById("purchase-rows").children.length'), 4);
    acceptDialog = false;
    await evaluate('document.querySelector("#purchase-rows .purchase-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("purchase-rows").children.length'), 4);
    await evaluate('document.getElementById("reset-example").click()');
    assert.equal(await evaluate('document.getElementById("purchase-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#purchase-rows .purchase-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("purchase-rows").children.length'), 3);
    await evaluate(`(()=>{
      const row=document.querySelector(".purchase-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=quantity]").value='2';
      row.querySelector("[data-field=price]").value='10.50';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    const filename = path.join(downloads, "purchase-worktime-sheet.csv");
    await until(() => fs.existsSync(filename));
    const csv = fs.readFileSync(filename, "utf8");
    assert(csv.includes(`"'=1+1"`));
    assert(csv.includes('"21.00"'));
    assert(csv.includes('"201.00"'));
    assert(!csv.includes("<script>"));
    await evaluate('document.getElementById("reset-example").click()');
    assert.notEqual(await evaluate('document.querySelector("[data-field=name]").value'), "=1+1");
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale));
      assert.equal(await evaluate(`(()=>{
        const input=document.getElementById("hourly-income");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(20.5);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native decimal input");
    }
    assert.deepEqual(external.filter((url) => !url.startsWith("data:")), []);
    console.log(JSON.stringify({locales: manifest.records.length, viewports: 2, downloads: 1, external_requests: external.length}));
  } finally {
    if (browser) await browser.send("Browser.close").catch(() => {});
    if (page) page.socket.close();
    if (browser) browser.socket.close();
    if (child.exitCode === null) {
      child.kill("SIGTERM");
      await Promise.race([new Promise((resolve) => child.once("exit", resolve)), pause(5000)]);
      if (child.exitCode === null) child.kill("SIGKILL");
    }
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => { console.error(error.stack); process.exitCode = 1; });
