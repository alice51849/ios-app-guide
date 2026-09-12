import {chromium} from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";

const args=process.argv.slice(2), value=name=>args[args.indexOf(name)+1];
if(!args.includes("--fixtures")||!args.includes("--output")) throw new Error("--fixtures and --output are required");
const root=path.resolve(value("--fixtures")), output=path.resolve(value("--output"));
const bytes=await fs.readFile(path.join(root,"fixtures.json")), fixture=JSON.parse(bytes);
const viewports=[[320,568],[375,667],[390,844],[768,1024],[1024,768]];
const results=[], requests=[];
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({javaScriptEnabled:false,serviceWorkers:"block"});
await context.route("**/*",route=>{requests.push({method:route.request().method(),url:route.request().url()});return route.abort();});
const page=await context.newPage();
async function measure(source) {
  await page.goto("about:blank");
  await page.setContent(source,{waitUntil:"load"});
  return page.evaluate(()=>{
    const links=[...document.querySelectorAll("a[href]")].filter(a=>/^https:\/\/(?:apps|itunes)\.apple\.com\/.*\/?app\//.test(a.href));
    return {links:links.map(a=>{const r=a.getBoundingClientRect();return {href:a.href,x:r.x,y:r.y,width:r.width,height:r.height};}),
      first_visible:links.length?links[0].getBoundingClientRect().top>=0&&links[0].getBoundingClientRect().bottom<=innerHeight:null,
      overflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),capture_count:document.querySelectorAll(".tool-email-capture").length};
  });
}
try {
  for(const [width,height] of viewports) {
    await page.setViewportSize({width,height});
    for(const row of fixture.rows) {
      const baseline=await fs.readFile(path.join(root,"main",row.locale+".html"),"utf8");
      const inactive=await fs.readFile(path.join(root,"inactive",row.locale+".html"),"utf8");
      const active=await fs.readFile(path.join(root,"active",row.locale+".html"),"utf8");
      const before=await measure(baseline), off=await measure(inactive), preview=await measure(active);
      results.push({locale:row.locale,width,height,
        inactive_preserved:baseline===inactive&&JSON.stringify(before.links)===JSON.stringify(off.links)&&off.capture_count===0,
        active_preserved:JSON.stringify(before.links)===JSON.stringify(preview.links),
        active_overflow_added:Math.max(0,preview.overflow-before.overflow),
        baseline_primary_visible:before.first_visible,before,off,preview});
    }
    console.log(`compatibility width=${width} cases=${results.length}`);
  }
} finally {await browser.close();}
const report={
  schema:"lumi.owned-email-layout-dependencies/v1",observed_at:new Date().toISOString(),
  main_revisions:fixture.main_revisions,source_digest:fixture.source_digest,shared_feature_merged:false,
  dependency_files:fixture.dependency_files,fixture_sha256:crypto.createHash("sha256").update(bytes).digest("hex"),
  compatibility_cases:results.length,non_capture_preserved:results.every(r=>r.inactive_preserved),
  non_interference_failures:results.filter(r=>!r.inactive_preserved).length,
  active_preview_non_interference_failures:results.filter(r=>!r.active_preserved||r.active_overflow_added>1).length,
  baseline_primary_offscreen:results.filter(r=>r.baseline_primary_visible===false).length,
  blocked_existing_resource_requests:requests,rows:results,
};
await fs.mkdir(path.dirname(output),{recursive:true});
await fs.writeFile(output,JSON.stringify(report));
console.log(JSON.stringify({cases:report.compatibility_cases,inactive_failures:report.non_interference_failures,active_preview_failures:report.active_preview_non_interference_failures,baseline_offscreen:report.baseline_primary_offscreen}));
if(report.non_interference_failures) process.exitCode=1;
