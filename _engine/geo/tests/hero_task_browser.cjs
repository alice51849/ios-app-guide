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
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + " timed out")); }, Number(process.env.HERO_CDP_TIMEOUT_MS || 60000));
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
        wide:[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>innerWidth+1||e.getBoundingClientRect().left<-1||e.scrollWidth>e.clientWidth+1)
          .slice(0,6).map(e=>e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(e.className&&typeof e.className==="string"?"."+e.className.split(" ").join("."):"")+"="+Math.round(e.getBoundingClientRect().width)+"px:"+(e.textContent||"").trim().slice(0,40)),
        scripts:[...document.scripts].filter(s=>s.src).length,
        name:document.querySelector("[data-field=name],[data-field=point]").value
      })`);
      assert.equal(state.locale, record.locale);
      assert.equal(state.ready, true, record.locale);
      assert.equal(state.overflow, false, record.locale + "/" + record.task_id + " overflow at " + width + " " + JSON.stringify(state.wide));
      assert.equal(state.scripts, 2);
      const clipped = await evaluate(`([...document.querySelectorAll("h1,.fields label,.totals p")]).filter(
        element=>!(element.scrollWidth<=element.clientWidth+1&&
          element.getBoundingClientRect().height<=parseFloat(getComputedStyle(element).lineHeight)+1)
      ).map(element=>element.tagName.toLowerCase()+":"+element.textContent.trim()+"="+element.scrollWidth+"/"+element.clientWidth)`);
      assert.deepEqual(clipped, [], record.locale + "/" + record.task_id + " primary labels remain complete on one line");
      assert.equal(await evaluate(`(()=>{
        const rect=document.getElementById("download-csv").getBoundingClientRect();
        return rect.height>=44&&rect.top>=0&&rect.bottom<=innerHeight;
      })()`), true, record.locale + " primary action is visible");
      const firstScreen = await evaluate(`(()=>{
        const result=document.querySelector(".totals").getBoundingClientRect();
        const action=document.getElementById("download-csv").getBoundingClientRect();
        const rows=[...document.querySelectorAll(".totals>div")].map(e=>Math.round(e.getBoundingClientRect().height));
        const children=[...document.getElementById("hero-fields").children].filter(e=>e.tagName!=="TEMPLATE").map(e=>{const r=e.getBoundingClientRect();return (e.id||e.className||e.tagName.toLowerCase())+"@"+Math.round(r.top)+"-"+Math.round(r.bottom)+"/o"+getComputedStyle(e).order;});
        return {ok:result.top>=0&&result.bottom+8<=action.top,top:Math.round(result.top),bottom:Math.round(result.bottom),action:Math.round(action.top),rows,inner:innerHeight,children};
      })()`);
      assert.equal(firstScreen.ok, true, record.locale + "/" + record.task_id + " first-screen results are not covered " + JSON.stringify(firstScreen));
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
    const english = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "purchase-worktime");
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
    const maintenance = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "maintenance-next-due");
    await navigate(maintenance);
    assert.equal(await evaluate('document.getElementById("today-date").value.length'), 10, "live sheet starts from the visitor's own day");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("today-date");input.value="";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "an invalid date disables the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-task").click()');
    assert.equal(await evaluate('document.getElementById("maintenance-rows").children.length'), 4);
    assert.equal(await evaluate('document.getElementById("today-date").value'), maintenance.example_today || "2026-09-05");
    acceptDialog = false;
    await evaluate('document.querySelector("#maintenance-rows .maintenance-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("maintenance-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#maintenance-rows .maintenance-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("maintenance-rows").children.length'), 3);
    await evaluate(`(()=>{
      const row=document.querySelector(".maintenance-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=last_done]").value='2024-01-31';
      row.querySelector("[data-field=interval_value]").value='1';
      row.querySelector("[data-field=interval_unit]").value='month';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    const maintenanceFile = path.join(downloads, "maintenance-next-due-sheet.csv");
    await until(() => fs.existsSync(maintenanceFile));
    const maintenanceCsv = fs.readFileSync(maintenanceFile, "utf8");
    assert(maintenanceCsv.includes(`"'=1+1"`));
    assert(maintenanceCsv.includes('"2024-02-29"'));
    assert(maintenanceCsv.includes('"Overdue"'));
    assert(!maintenanceCsv.includes("<script>"));
    assert.equal(await evaluate('document.querySelector(".maintenance-row [data-output=status]").dataset.status'), "overdue");
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "maintenance-next-due"));
      assert.equal(await evaluate(`(()=>{
        const input=document.querySelector(".maintenance-row [data-field=interval_value]");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(12);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native digit interval input");
    }
    const profit = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "project-profit");
    await navigate(profit);
    assert.equal(await evaluate('document.getElementById("profit-rows").children.length'), 3);
    assert.equal(await evaluate('document.getElementById("hourly-net").textContent'), "87.97");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("hours-spent");input.value="12.3";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "hours outside quarter-hour steps disable the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-expense").click()');
    assert.equal(await evaluate('document.getElementById("profit-rows").children.length'), 4);
    assert.equal(await evaluate('document.querySelector("#profit-rows .profit-row:last-child").dataset.kind'), "expense");
    acceptDialog = false;
    await evaluate('document.querySelector("#profit-rows .profit-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("profit-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#profit-rows .profit-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("profit-rows").children.length'), 3);
    await evaluate(`(()=>{
      const row=document.querySelector(".profit-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=amount]").value='100';
      document.getElementById("hours-spent").value='';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.getElementById("hourly-net").textContent'), "—", "no hours means no hourly figure");
    const profitFile = path.join(downloads, "project-profit-sheet.csv");
    await until(() => fs.existsSync(profitFile) && fs.statSync(profitFile).size > 0);
    await until(async () => { const size = fs.statSync(profitFile).size; await pause(150); return fs.statSync(profitFile).size === size; });
    const profitCsv = fs.readFileSync(profitFile, "utf8");
    assert(profitCsv.includes(`"'=1+1"`), "profit csv: " + profitCsv.slice(0, 500));
    assert(profitCsv.includes('"-300.39"'), "negative profit stays a plain number: " + profitCsv.slice(0, 500));
    assert(!profitCsv.includes(`"'-300.39"`));
    assert(!profitCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "project-profit"));
      assert.equal(await evaluate(`(()=>{
        const input=document.querySelector(".profit-row [data-field=amount]");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(20.5);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native decimal amount input");
    }
    const battery = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "battery-wear");
    await navigate(battery);
    assert.equal(await evaluate('document.getElementById("today-month").value.length'), 7, "live sheet starts from the visitor's own month");
    assert.equal(await evaluate('document.getElementById("battery-rows").children.length'), 3);
    assert.equal(await evaluate(`(()=>{
      const input=document.querySelector(".battery-row [data-field=max_capacity_pct]");input.value="59";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "a capacity outside 60-100 disables the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-device").click()');
    assert.equal(await evaluate('document.getElementById("battery-rows").children.length'), 4);
    acceptDialog = false;
    await evaluate('document.querySelector("#battery-rows .battery-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("battery-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#battery-rows .battery-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("battery-rows").children.length'), 3);
    await evaluate(`(()=>{
      document.getElementById("today-month").value='2026-09';
      const row=document.querySelector(".battery-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=purchase_month]").value='2024-09';
      row.querySelector("[data-field=max_capacity_pct]").value='88';
      row.querySelector("[data-field=cycle_count]").value='412';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.querySelector(".battery-row [data-output=wear]").textContent.includes("0.38")'), true);
    assert.equal(await evaluate('document.querySelector(".battery-row [data-output=months]").textContent.includes("12")'), true);
    assert.equal(await evaluate('document.getElementById("device-count").textContent'), "3");
    assert.equal(await evaluate('document.getElementById("soonest-80").textContent'), "Already at or below 80%", "a device already at 80% makes the soonest figure a fact");
    const batteryFile = path.join(downloads, "battery-wear-range-sheet.csv");
    await until(() => fs.existsSync(batteryFile) && fs.statSync(batteryFile).size > 0);
    await until(async () => { const size = fs.statSync(batteryFile).size; await pause(150); return fs.statSync(batteryFile).size === size; });
    const batteryCsv = fs.readFileSync(batteryFile, "utf8");
    assert(batteryCsv.includes(`"'=1+1"`));
    assert(batteryCsv.includes('"0.38"') && batteryCsv.includes('"0.63"'), "wear stays a band");
    assert(batteryCsv.includes("; Estimated: Age (months), Wear % per month, Months to 80%"), "every derived figure carries its estimate marker: " + batteryCsv.slice(0, 500));
    assert(batteryCsv.includes("You provided: Purchase month, Maximum capacity %, Cycle count;"), "typed-in values are marked as provided");
    assert(!batteryCsv.toLowerCase().includes("score"));
    assert(!batteryCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "battery-wear"));
      assert.equal(await evaluate(`(()=>{
        const input=document.querySelector(".battery-row [data-field=max_capacity_pct]");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(91);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native digit capacity input");
    }
    const bandwidth = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "bandwidth-need");
    await navigate(bandwidth);
    assert.equal(await evaluate('document.getElementById("bandwidth-rows").children.length'), 3);
    assert.equal(await evaluate('document.getElementById("status-total").dataset.status'), "ok");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("plan-down");input.value="0.4";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "a plan speed outside 0.5-10000 disables the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-row").click()');
    assert.equal(await evaluate('document.getElementById("bandwidth-rows").children.length'), 4);
    acceptDialog = false;
    await evaluate('document.querySelector("#bandwidth-rows .bandwidth-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("bandwidth-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#bandwidth-rows .bandwidth-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("bandwidth-rows").children.length'), 3);
    await evaluate(`(()=>{
      document.getElementById("plan-down").value='10';
      const row=document.querySelector(".bandwidth-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=activity]").value='uhd_stream';
      row.querySelector("[data-field=devices]").value='2';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.getElementById("status-total").dataset.status'), "short", "over-committed plan shows the honest verdict");
    const bandwidthFile = path.join(downloads, "bandwidth-need-sheet.csv");
    await until(() => fs.existsSync(bandwidthFile) && fs.statSync(bandwidthFile).size > 0);
    await until(async () => { const size = fs.statSync(bandwidthFile).size; await pause(150); return fs.statSync(bandwidthFile).size === size; });
    const bandwidthCsv = fs.readFileSync(bandwidthFile, "utf8");
    assert(bandwidthCsv.includes(`"'=1+1"`), "bandwidth csv: " + bandwidthCsv.slice(0, 500));
    assert(bandwidthCsv.includes('"Not enough"'), "verdict is written in words: " + bandwidthCsv.slice(0, 500));
    assert(/"-\d+\.\d"/.test(bandwidthCsv) && !bandwidthCsv.includes(`"'-`), "negative headroom stays a plain number");
    assert(!bandwidthCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "bandwidth-need"));
      assert.equal(await evaluate(`(()=>{
        const input=document.getElementById("plan-down");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(50.5);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native decimal plan input");
    }
    const trip = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "trip-budget");
    await navigate(trip);
    assert.equal(await evaluate('document.getElementById("fixed-rows").children.length'), 2);
    assert.equal(await evaluate('document.getElementById("per-person-day").textContent'), "124.95");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("share-food");input.value="41";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "shares that do not add up to 100 disable the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-fixed").click()');
    assert.equal(await evaluate('document.getElementById("fixed-rows").children.length'), 3);
    acceptDialog = false;
    await evaluate('document.querySelector("#fixed-rows .fixed-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("fixed-rows").children.length'), 3);
    acceptDialog = true;
    await evaluate('document.querySelector("#fixed-rows .fixed-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("fixed-rows").children.length'), 2);
    await evaluate(`(()=>{
      const row=document.querySelector(".fixed-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=amount]").value='1000';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.getElementById("variable-total").textContent'), "1,149.50");
    const tripFile = path.join(downloads, "trip-budget-sheet.csv");
    await until(() => fs.existsSync(tripFile) && fs.statSync(tripFile).size > 0);
    await until(async () => { const size = fs.statSync(tripFile).size; await pause(150); return fs.statSync(tripFile).size === size; });
    const tripCsv = fs.readFileSync(tripFile, "utf8");
    assert(tripCsv.includes(`"'=1+1"`), "trip csv: " + tripCsv.slice(0, 500));
    assert(tripCsv.includes('"1149.50"') && tripCsv.includes('"100%"'), "left to spend reconciles: " + tripCsv.slice(0, 500));
    assert(!tripCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "trip-budget"));
      assert.equal(await evaluate(`(()=>{
        const input=document.getElementById("budget-total");
        input.value=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false}).format(2500.5);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native decimal budget input");
    }
    const itinerary = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "day-itinerary");
    await navigate(itinerary);
    assert.equal(await evaluate('document.getElementById("stop-rows").children.length'), 3);
    assert.equal(await evaluate('document.getElementById("status-total").dataset.status'), "fits");
    assert.equal(await evaluate('document.getElementById("total-minutes").textContent'), "455");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("end-time");input.value="9:00";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "a time that is not HH:MM disables the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-stop").click()');
    assert.equal(await evaluate('document.getElementById("stop-rows").children.length'), 4);
    acceptDialog = false;
    await evaluate('document.querySelector("#stop-rows .stop-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("stop-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#stop-rows .stop-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("stop-rows").children.length'), 3);
    await evaluate(`(()=>{
      document.getElementById("start-time").value='22:00';
      document.getElementById("end-time").value='02:00';
      document.getElementById("end-time").dispatchEvent(new Event("input",{bubbles:true}));
    })()`);
    assert.equal(await evaluate('document.querySelector("#stop-rows .stop-row [data-output=leave]").textContent'), "00:00 +1", "past midnight carries a day marker");
    assert.equal(await evaluate('document.getElementById("available-minutes").textContent'), "240");
    await evaluate(`(()=>{
      const row=document.querySelector(".stop-row");
      row.querySelector("[data-field=name]").value='=1+1';
      row.querySelector("[data-field=stay_min]").value='600';
      row.dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.getElementById("status-total").dataset.status'), "overrun", "a day that does not fit shows the honest verdict");
    const itineraryFile = path.join(downloads, "day-itinerary-sheet.csv");
    await until(() => fs.existsSync(itineraryFile) && fs.statSync(itineraryFile).size > 0);
    await until(async () => { const size = fs.statSync(itineraryFile).size; await pause(150); return fs.statSync(itineraryFile).size === size; });
    const itineraryCsv = fs.readFileSync(itineraryFile, "utf8");
    assert(itineraryCsv.includes(`"'=1+1"`), "itinerary csv: " + itineraryCsv.slice(0, 500));
    assert(itineraryCsv.includes('"Over time"') && itineraryCsv.includes(' +1"'), "verdict in words and day marker kept: " + itineraryCsv.slice(0, 500));
    assert(!itineraryCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "day-itinerary"));
      assert.equal(await evaluate(`(()=>{
        const digits=new Intl.NumberFormat(document.documentElement.lang,{useGrouping:false,minimumIntegerDigits:2});
        const input=document.getElementById("start-time");
        input.value=digits.format(8)+":"+digits.format(30);
        input.dispatchEvent(new Event("input",{bubbles:true}));
        return document.getElementById("download-csv").disabled;
      })()`), false, locale + " native digit clock input");
    }
    const outline = manifest.records.find((record) => record.locale === "en-US" && record.task_id === "one-page-outline");
    await navigate(outline);
    assert.equal(await evaluate('document.getElementById("point-rows").children.length'), 3);
    assert.equal(await evaluate('document.getElementById("point-count").textContent'), "3");
    assert.equal(await evaluate('document.querySelector("#point-rows [data-remove]").disabled'), true, "three points is the minimum");
    assert.equal(await evaluate(`(()=>{
      const input=document.getElementById("headline");input.value="   ";
      input.dispatchEvent(new Event("input",{bubbles:true}));
      return document.getElementById("download-csv").disabled&&document.getElementById("hero-status").textContent.length>0;
    })()`), true, "an empty headline disables the download");
    await evaluate('document.getElementById("reset-example").click();document.getElementById("add-point").click()');
    assert.equal(await evaluate('document.getElementById("point-rows").children.length'), 4);
    assert.equal(await evaluate('document.getElementById("download-csv").disabled'), true, "a new empty point must be filled in first");
    acceptDialog = false;
    await evaluate('document.querySelector("#point-rows .point-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("point-rows").children.length'), 4);
    acceptDialog = true;
    await evaluate('document.querySelector("#point-rows .point-row:last-child [data-remove]").click()');
    assert.equal(await evaluate('document.getElementById("point-rows").children.length'), 3);
    await evaluate(`(()=>{
      document.getElementById("headline").value='=1+1';
      document.getElementById("metric").value='-3%';
      document.getElementById("metric").dispatchEvent(new Event("input",{bubbles:true}));
      document.getElementById("download-csv").click();
    })()`);
    assert.equal(await evaluate('document.getElementById("preview-headline").textContent'), "=1+1", "the preview shows the text verbatim");
    assert.equal(await evaluate('document.getElementById("preview-metric").hidden'), false);
    const outlineFile = path.join(downloads, "one-page-outline-sheet.csv");
    await until(() => fs.existsSync(outlineFile) && fs.statSync(outlineFile).size > 0);
    await until(async () => { const size = fs.statSync(outlineFile).size; await pause(150); return fs.statSync(outlineFile).size === size; });
    const outlineCsv = fs.readFileSync(outlineFile, "utf8");
    assert(outlineCsv.includes(`"'=1+1"`), "outline csv: " + outlineCsv.slice(0, 500));
    assert(outlineCsv.includes('"-3%"') && !outlineCsv.includes(`"'-3%"`), "a negative percentage stays a plain value");
    assert(!outlineCsv.includes("<script>"));
    for (const locale of ["de-DE", "ar-SA", "bn-BD"]) {
      await navigate(manifest.records.find((record) => record.locale === locale && record.task_id === "one-page-outline"));
      assert.equal(await evaluate(`(()=>{
        const headline=document.getElementById("headline").value;
        return headline==="Ship the checkout redesign by 30 September"?"english":document.getElementById("download-csv").disabled?"disabled":"native";
      })()`), "native", locale + " worked example is native prose and valid");
    }
    assert.deepEqual(external.filter((url) => !url.startsWith("data:")), []);
    console.log(JSON.stringify({locales: manifest.locale_count, records: manifest.records.length, tasks: manifest.task_count, viewports: 2, downloads: 8, external_requests: external.length}));
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
