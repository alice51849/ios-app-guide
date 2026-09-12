import {chromium} from "playwright";
import axe from "axe-core";
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import {createRequire} from "node:module";

const require=createRequire(import.meta.url);
const playwrightVersion=require("playwright/package.json").version;
if(playwrightVersion!=="1.63.0"||axe.version!=="4.13.0") throw new Error("locked browser/a11y dependency mismatch");
const args = process.argv.slice(2);
const value = name => args[args.indexOf(name) + 1];
if (!args.includes("--fixtures") || !args.includes("--output")) {
  throw new Error("--fixtures and --output are required; this runner never opens a public page");
}
const fixtures = path.resolve(value("--fixtures"));
const output = path.resolve(value("--output"));
const manifestBytes = await fs.readFile(path.join(fixtures, "fixtures.json"));
const fixture = JSON.parse(manifestBytes);
const viewports = [[320,568],[375,667],[390,844],[768,1024],[1024,768]];
const longest = new Map();
for (const row of fixture.rows) {
  if (!longest.has(row.locale) || row.app_name.length > longest.get(row.locale).app_name.length) {
    longest.set(row.locale, row);
  }
}
const selected = args.includes("--smoke") ? [...longest.values()] : fixture.rows;
const jobs = viewports.flatMap(([width,height]) => selected.map(row => ({row,width,height})));
const results = [], failures = [], requests = [], a11y = [];
const hash = body => crypto.createHash("sha256").update(body).digest("hex");
const browser = await chromium.launch({headless:true, args:["--disable-background-networking","--disable-component-update","--disable-sync"]});
const browserVersion=browser.version();
let cursor=0;

async function load(page, source) {
  await page.goto("about:blank");
  await page.setContent(source, {waitUntil:"load"});
  await page.evaluate(() => {
    window.__shifts = [];
    new PerformanceObserver(list => {
      window.__shifts.push(...list.getEntries().filter(e => !e.hadRecentInput).map(e => e.value));
    }).observe({type:"layout-shift", buffered:true});
  });
  await page.waitForTimeout(40);
}

async function measure(page) {
  return page.evaluate(() => {
    const rect = node => {
      if (!node) return null;
      const r=node.getBoundingClientRect();
      return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom};
    };
    const visible = node => {
      const s=getComputedStyle(node), r=node.getBoundingClientRect();
      const closed=node.closest("details:not([open])");
      return r.width>0 && r.height>0 && s.visibility!=="hidden" && s.display!=="none"
        && (!closed || node.tagName==="SUMMARY");
    };
    const controls=[...document.querySelectorAll("a[href],button,input:not([type=hidden]),summary")].filter(visible);
    const badTargets=controls.flatMap(node => {
      let target=node;
      if (node.matches("input[type=checkbox]") && node.labels?.length) target=node.labels[0];
      const r=rect(target);
      return r.width<43.9||r.height<43.9 ? [{tag:node.tagName,name:node.getAttribute("name"),rect:r}] : [];
    });
    const primary=document.querySelector("[data-primary-app-store-cta]");
    const slot=document.querySelector("[data-owned-email-slot]");
    const primaryRect=rect(primary), form=document.querySelector("form");
    const interactiveOrder=controls.filter(node=>node.closest(".oe-core")).map(node=>node.getAttribute("href")||node.id);
    const intrusive=[...document.querySelectorAll("[data-owned-email-slot], [data-owned-email-slot] *")]
      .filter(node=>["fixed","sticky"].includes(getComputedStyle(node).position)).length;
    return {
      primary:primaryRect, primary_visible:!!primaryRect&&primaryRect.y>=0&&primaryRect.bottom<=innerHeight,
      primary_before_capture:!primary||!!(primary.compareDocumentPosition(slot)&Node.DOCUMENT_POSITION_FOLLOWING),
      primary_before_form:!primary||!form||!!(primary.compareDocumentPosition(form)&Node.DOCUMENT_POSITION_FOLLOWING),
      core_html:document.querySelector(".oe-core")?.outerHTML, core_order:interactiveOrder,
      overflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),
      bad_targets:badTargets, intrusive, page_scripts:document.scripts.length,
      forms:document.forms.length, unchecked:!document.querySelector("input[type=checkbox]")?.checked,
      cls:(window.__shifts||[]).reduce((sum,n)=>sum+n,0),
      apple_links:[...document.querySelectorAll("a[href]")].filter(a=>/https:\/\/(?:apps|itunes)\.apple\.com/.test(a.href)).length,
      primary_hit:!primaryRect||document.elementFromPoint(primaryRect.x+primaryRect.width/2,primaryRect.y+primaryRect.height/2)?.closest("[data-primary-app-store-cta]")===primary,
    };
  });
}

async function auditA11y(page, key) {
  await page.evaluate(axe.source);
  const report = await page.evaluate(async () => {
    const result=await window.axe.run(document, {runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}});
    return {violations:result.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})),
      incomplete:result.incomplete.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))};
  });
  a11y.push({key,...report});
  return report;
}

async function execute() {
  const context=await browser.newContext({javaScriptEnabled:true,serviceWorkers:"block"});
  const noJsContext=await browser.newContext({javaScriptEnabled:false,serviceWorkers:"block"});
  for (const target of [context,noJsContext]) await target.route("**/*", route => {
      requests.push({url:route.request().url(),method:route.request().method()});
      return route.abort();
    });
  const page=await context.newPage();
  const noJs=await noJsContext.newPage();
  page.setDefaultTimeout(15000);
  noJs.setDefaultTimeout(15000);
  try {
    while (cursor<jobs.length) {
      const job=jobs[cursor++], {row,width,height}=job, key=`${row.app_id}/${row.locale}/${width}`;
      try {
        await page.setViewportSize({width,height});
        await noJs.setViewportSize({width,height});
        const inactive=await fs.readFile(path.join(fixtures,"inactive",row.capture_path),"utf8");
        const active=await fs.readFile(path.join(fixtures,"active",row.capture_path),"utf8");
        if(hash(inactive)!==fixture.inactive_hashes[row.capture_path]||hash(active)!==fixture.active_hashes[row.capture_path]) throw new Error("fixture digest mismatch");
        await load(page,inactive);
        const base=await measure(page);
        const isA11y=longest.get(row.locale).app_key===row.app_key;
        let inactiveA11y=null,activeA11y=null;
        if(isA11y) inactiveA11y=await auditA11y(page,`${key}/inactive`);
        await load(page,active);
        const closed=await measure(page);
        await page.locator("summary").click();
        await page.waitForTimeout(40);
        const expanded=await measure(page);
        const native=await page.evaluate(() => ({
          email:document.querySelector("input[type=email]")?.required,
          consent:document.querySelector("input[type=checkbox]")?.required,
          form_invalid:!document.querySelector("form").checkValidity(),
          method:document.querySelector("form").method,
        }));
        if(isA11y) {
          activeA11y=await auditA11y(page,`${key}/active`);
          await page.locator("input[type=email]").fill("geometry-only@example.invalid");
          await page.locator("input[type=checkbox]").check();
          native.valid_after_explicit_consent=await page.locator("form").evaluate(form=>form.checkValidity());
          await page.locator("input[type=checkbox]").uncheck();
        }
        await page.goto("about:blank");
        await page.setContent(inactive,{waitUntil:"load"});
        const rolledBack=await measure(page);
        await noJs.goto("about:blank");
        await noJs.setContent(active,{waitUntil:"load"});
        await noJs.locator("summary").click();
        const withoutJs=await measure(noJs);
        const noJsNative=await noJs.locator("form").evaluate(form=>!form.checkValidity());
        if(isA11y) {
          await noJs.locator("input[type=email]").fill("geometry-only@example.invalid");
          await noJs.locator("input[type=checkbox]").check();
          native.no_js_valid_after_consent=await noJs.locator("form").evaluate(form=>form.checkValidity());
          await noJs.locator("input[type=checkbox]").uncheck();
        }
        const errors=[];
        for (const [mode,m] of Object.entries({base,closed,expanded,rolledBack,withoutJs})) {
          if(row.locale!=="bn-BD"&&(!m.primary_visible||!m.primary_hit)) errors.push(`${mode}:primary_offscreen_or_obscured`);
          if(row.locale==="bn-BD"&&(m.primary||m.apple_links)) errors.push(`${mode}:bn_store_cta`);
          if(m.overflow>1) errors.push(`${mode}:overflow`);
          if(m.bad_targets.length) errors.push(`${mode}:target_under_44`);
          if(m.intrusive||m.page_scripts) errors.push(`${mode}:intrusive_or_scripted`);
          if(!m.primary_before_capture||!m.primary_before_form) errors.push(`${mode}:capture_precedes_core`);
          if(m.cls!==0) errors.push(`${mode}:cls`);
        }
        if(base.forms||rolledBack.forms||closed.forms!==1||expanded.forms!==1) errors.push("wrong_active_default");
        if(!closed.unchecked||!expanded.unchecked||!native.email||!native.consent||!native.form_invalid||native.method!=="post") errors.push("invalid_native_consent");
        if(isA11y&&!native.valid_after_explicit_consent) errors.push("no_js_form_unusable");
        if(!noJsNative||withoutJs.forms!==1||!withoutJs.unchecked) errors.push("no_js_native_invalid");
        if(isA11y&&!native.no_js_valid_after_consent) errors.push("no_js_form_unusable");
        if(base.core_html!==closed.core_html||base.core_html!==expanded.core_html||base.core_html!==rolledBack.core_html) errors.push("core_html_changed");
        if(JSON.stringify(base.primary)!==JSON.stringify(closed.primary)||JSON.stringify(base.primary)!==JSON.stringify(expanded.primary)||JSON.stringify(base.primary)!==JSON.stringify(rolledBack.primary)||JSON.stringify(base.primary)!==JSON.stringify(withoutJs.primary)) errors.push("primary_geometry_changed");
        if(JSON.stringify(base.core_order)!==JSON.stringify(expanded.core_order)) errors.push("primary_order_changed");
        if(inactiveA11y?.violations.length||activeA11y?.violations.length) errors.push("axe_violation");
        const result={app_id:row.app_id,app_key:row.app_key,locale:row.locale,width,height,
          inactive_sha256:hash(inactive),active_sha256:hash(active),errors,
          primary:base.primary,active_primary:expanded.primary,rollback_primary:rolledBack.primary,
          core_digest:hash(base.core_html),cls:Math.max(base.cls,closed.cls,expanded.cls),
          overflow:Math.max(base.overflow,closed.overflow,expanded.overflow,rolledBack.overflow),
          targets_ok:![base,closed,expanded,rolledBack,withoutJs].some(m=>m.bad_targets.length),
          no_js:true,native_form:true,rollback:errors.every(e=>!e.includes("rollback")&&!e.includes("core_html")),
          a11y:isA11y};
        results.push(result);
        if(errors.length) failures.push({...result,details:{base,closed,expanded,rolledBack,withoutJs,native,inactiveA11y,activeA11y}});
        if(results.length%50===0) console.log(`geometry ${results.length}/${jobs.length} failures=${failures.length}`);
      } catch(error) { failures.push({key,error:String(error)}); }
    }
  } finally { await context.close(); await noJsContext.close(); }
}

try { await Promise.all([execute(),execute()]); } finally { await browser.close(); }
await fs.mkdir(path.dirname(output),{recursive:true});
const report={
  schema:"lumi.owned-email-geometry/v1",observed_at:new Date().toISOString(),
  source_digest:fixture.source_digest,fixture_manifest_sha256:hash(manifestBytes),
  viewports,locales:[...new Set(selected.map(r=>r.locale))].sort(),app_count:new Set(selected.map(r=>r.app_id)).size,
  cases:results.length,no_js_cases:results.filter(r=>r.no_js).length,active_preview_cases:results.length,
  rollback_cases:results.filter(r=>r.rollback).length,cls_cases:results.length*2,
  a11y_cases:a11y.length,a11y,failures,network_requests:requests,page_scripts:0,
  max_cls:Math.max(0,...results.map(r=>r.cls)),max_overflow:Math.max(0,...results.map(r=>r.overflow)),
  inactive_hashes:fixture.inactive_hashes,active_hashes:fixture.active_hashes,
  browser:"chromium",browser_version:browserVersion,node_version:process.version,
  playwright_version:playwrightVersion,axe_version:axe.version,rows:results,
};
await fs.writeFile(output,JSON.stringify(report));
console.log(JSON.stringify({cases:report.cases,a11y:report.a11y_cases,failures:failures.length,requests:requests.length,max_cls:report.max_cls,max_overflow:report.max_overflow}));
if(failures.length||requests.length) process.exitCode=1;
