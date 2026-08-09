#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demand-backed free tool pages (W19, 2026-08-09).

Six single-page, genuinely working, pure-front-end tools built from queries in
geo/_demand/shortlist.json that engines confirmed have real search volume
(tool-type intent: checker / calculator / converter / maker).  Each page ends
with an honest, claim-free pointer to the matching app.

Honesty rules (hard-coded): no ratings/aggregateRating anywhere, no fabricated
app features (app cards only name the app and defer to its live listing), all
processing stays in the visitor's browser, currency page labels its rates as
ECB reference rates with a visible date.

Registered in geo/publish.py (after the other tool generators, before
add_related_tools / gen_tool_email_capture / sitemap) so pages survive
republishes and automatically get related-tools links + the email-capture
module once its endpoint is enabled.
"""
from __future__ import annotations

import html
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
TOOLS = PAGES / "tools"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
RATES_CACHE = HERE / "_demand" / "ecb_usd_rates.json"
DATE = "2026-08-09"

sys.path.insert(0, str(HERE))
from gen_calculator import write_tools_sitemap  # noqa: E402

CSS = """
:root{--ink:#3d3223;--muted:#8a7a5f;--line:#e9dcc3;--paper:#fff;--bg:#faf3e4;--brand:#9a6b16;--gold:#c8922a;--soft:#fdf6e8;--good:#2e7d4f;--bad:#b3452e;--warn:#fff6d9;--shadow:0 22px 60px rgba(122,90,35,.13)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(circle at 88% 0,#fff 0,var(--bg) 55%,#f3e6cd 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#8a5c10}.wrap{width:min(1080px,calc(100% - 30px));margin:auto}
.top{position:sticky;top:0;z-index:8;background:#fffdf8f2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}
.nav{min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}
.hero{padding:56px 0 26px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--brand);white-space:nowrap}
.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}
.hero h1{font-size:clamp(32px,5.6vw,56px);line-height:1.06;letter-spacing:-.03em;margin:.3em 0 .22em}
.lead{font-size:clamp(17px,2.2vw,20px);color:var(--muted);margin:0}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}
.tool,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow)}
.tool{padding:clamp(20px,4vw,34px);margin:14px auto 28px}
.tool h2,.card h2,.app-card h2{font-size:clamp(22px,3.4vw,31px);line-height:1.15;margin:0 0 6px}
.intro{color:var(--muted);margin:0 0 8px}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px}
.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--brand);margin-bottom:6px;white-space:nowrap}
select,input,button,textarea{font:inherit;color:var(--ink)}
select,input:not([type=range]):not([type=file]),textarea{width:100%;border:1px solid #dcc9a4;border-radius:13px;background:#fff;padding:10px 12px}
select,input:not([type=range]):not([type=file]){min-height:46px}
textarea{min-height:74px;resize:vertical}
.button{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;background:linear-gradient(135deg,var(--brand),var(--gold));color:#fff;text-decoration:none;font-weight:850;padding:12px 19px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(154,107,22,.24)}
.button.ghost{background:#fff;color:var(--brand);border:1px solid var(--line);box-shadow:none}
.button[disabled]{opacity:.45;cursor:not-allowed}
.results{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin-top:18px}
.result{background:var(--soft);border:1px solid #ecd9b4;border-radius:16px;padding:13px;min-width:0}
.result strong{display:block;font-size:12px;color:#96793d;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.result span{display:block;font-size:16px;font-weight:780;margin-top:5px;white-space:nowrap;overflow-x:auto}
.result.ok span{color:var(--good)}.result.err span{color:var(--bad)}
.note{background:var(--warn);border:1px solid #ead9a7;border-radius:15px;padding:12px 15px;margin:14px 0 0;font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:28px}
.card,.app-card{padding:clamp(20px,3.4vw,28px)}.card.wide{grid-column:1/-1}
.card ul,.card ol{padding-left:22px;margin:8px 0}.card li{margin:7px 0}
.app-card{margin:0 auto 34px;background:linear-gradient(135deg,#fffdf7,#f7ecd6)}
.app-card .button{margin-top:8px}
.faq{margin-bottom:28px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}
.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
canvas.stage{max-width:100%;height:auto;border:1px solid var(--line);border-radius:14px;background:#fff;touch-action:none}
.filedrop{border:2px dashed #dcc9a4;border-radius:18px;padding:26px;text-align:center;background:var(--soft);margin-top:14px}
.filedrop input{width:auto}
.footer{background:#4a3a1e;color:#f6eeda;text-align:center;padding:26px 0}
.footer a{color:#f0ddb4}
.small{font-size:13px;color:var(--muted)}
@media(max-width:900px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1080px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
"""


def esc(text):
    return html.escape(text, quote=True)


def jsl(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def render_page(tool):
    url = f"{SITE}/tools/{tool['slug']}.html"
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": "en",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in tool["faq"]
        ],
    }
    app_ld = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": tool["h1"],
        "description": tool["description"],
        "url": url,
        "inLanguage": "en",
        "datePublished": DATE,
        "dateModified": DATE,
        "applicationCategory": tool["category"],
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": tool["features"],
    }
    badges = "".join(f'<span class="badge">{esc(b)}</span>' for b in tool["badges"])
    faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
        for q, a in tool["faq"]
    )
    related = "".join(
        f'<li><a href="{esc(href)}">{esc(label)}</a></li>'
        for href, label in tool["related"]
    )
    app_name = tool["app_name"]
    app_url = f"https://apps.apple.com/app/id{tool['app_id']}"
    print_css = tool.get("print_css", ".top,.hero,.app-card,.footer,.faq,.grid{display:none!important}body{background:#fff}.tool{box-shadow:none;border:0}")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(tool['title'])}</title>
<meta name="description" content="{esc(tool['description'])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(tool['h1'])}">
<meta property="og:description" content="{esc(tool['description'])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{CSS}
@media print{{{print_css}}}
{tool.get('extra_css','')}</style>
<script type="application/ld+json">{jsl(app_ld)}</script>
<script type="application/ld+json">{jsl(faq_ld)}</script>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="index.html">← Free tools</a><a href="{SITE}/" >iOS App Guide</a></div></header>
<section class="hero wrap">
<span class="eyebrow">{esc(tool['eyebrow'])}</span>
<h1>{esc(tool['h1'])}</h1>
<p class="lead">{esc(tool['lead'])}</p>
<div class="badges">{badges}</div>
</section>
<main class="wrap">
<section class="tool" id="tool">{tool['body']}</section>
<section class="grid">
<article class="card"><h2>How it works</h2>{tool['how']}</article>
<article class="card"><h2>What it will never do</h2>{tool['boundaries']}</article>
<article class="card wide"><h2>More free tools</h2><ul>{related}</ul></article>
</section>
<section class="faq"><h2>Questions</h2>{faq_html}</section>
<section class="app-card"><h2>{esc(tool['app_heading'])}</h2>
<p>{esc(app_name)} is optional — this free tool runs entirely in your browser and works without it. Check the app’s current App Store listing for exact features, pricing and availability before downloading.</p>
<a class="button" href="{app_url}" rel="nofollow noopener">View {esc(app_name)} on the App Store</a></section>
</main>
<footer class="footer"><div class="wrap">Runs in your browser · nothing is uploaded or stored · <a href="index.html">all free tools</a></div></footer>
<script>{tool['script']}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- tool bodies

def passport_checker():
    standards = [
        {"id": "us", "label": "US passport / visa — 2 × 2 in", "w": 50.8, "h": 50.8, "px": [600, 600]},
        {"id": "schengen", "label": "Schengen / EU visa — 35 × 45 mm", "w": 35, "h": 45},
        {"id": "uk", "label": "UK passport — 35 × 45 mm", "w": 35, "h": 45},
        {"id": "tw", "label": "Taiwan passport (2吋) — 35 × 45 mm", "w": 35, "h": 45},
        {"id": "jp", "label": "Japan passport — 35 × 45 mm", "w": 35, "h": 45},
        {"id": "kr", "label": "Korea passport — 35 × 45 mm", "w": 35, "h": 45},
        {"id": "cn", "label": "China passport — 33 × 48 mm", "w": 33, "h": 48},
        {"id": "in", "label": "India passport / OCI — 51 × 51 mm", "w": 51, "h": 51},
        {"id": "ca", "label": "Canada passport — 50 × 70 mm", "w": 50, "h": 70},
        {"id": "ph", "label": "Philippines passport — 35 × 45 mm", "w": 35, "h": 45},
    ]
    options = "".join(
        f'<option value="{s["id"]}">{esc(s["label"])}</option>' for s in standards
    )
    body = f"""
<h2>Check a photo against an official size</h2>
<p class="intro">Everything happens on this page — the photo never leaves your device.</p>
<div class="controls">
<div class="field"><label for="std">Document standard</label><select id="std">{options}</select></div>
<div class="field"><label for="file">Photo (JPG/PNG/HEIC-converted)</label><input type="file" id="file" accept="image/*"></div>
<div class="field"><label>&nbsp;</label><button class="button" id="dl" disabled>Download centered crop</button></div>
</div>
<div class="results" id="out" hidden>
<div class="result" id="r-dim"><strong>Pixels</strong><span>—</span></div>
<div class="result" id="r-aspect"><strong>Aspect ratio</strong><span>—</span></div>
<div class="result" id="r-res"><strong>Print resolution</strong><span>—</span></div>
<div class="result" id="r-verdict"><strong>Size verdict</strong><span>—</span></div>
</div>
<div style="margin-top:18px"><canvas class="stage" id="prev" width="10" height="10" hidden></canvas></div>
<p class="note">This checks <strong>size, aspect ratio and resolution only</strong>. It cannot judge head position, background, lighting, expression or official acceptance — always confirm the issuing authority’s photo rules.</p>
"""
    script = """
var STD=%s;
var img=null,cropCanvas=null,cur=null;
var file=document.getElementById('file'),sel=document.getElementById('std'),dl=document.getElementById('dl');
function mm2px(mm){return Math.round(mm/25.4*300);}
function target(){var s=STD.filter(function(x){return x.id===sel.value;})[0];
  var w=s.px?s.px[0]:mm2px(s.w),h=s.px?s.px[1]:mm2px(s.h);return {s:s,w:w,h:h};}
function set(id,txt,ok){var el=document.getElementById(id);el.querySelector('span').textContent=txt;
  el.classList.remove('ok','err');if(ok===true)el.classList.add('ok');if(ok===false)el.classList.add('err');}
function analyze(){if(!img)return;var t=target();
  document.getElementById('out').hidden=false;
  set('r-dim',img.naturalWidth+' × '+img.naturalHeight+' px');
  var want=t.w/t.h,have=img.naturalWidth/img.naturalHeight;
  var dev=Math.abs(have-want)/want;
  set('r-aspect',have.toFixed(3)+' (target '+want.toFixed(3)+')',dev<=0.015);
  var okRes=img.naturalWidth>=t.w&&img.naturalHeight>=t.h;
  set('r-res',okRes?('enough for 300 DPI ('+t.w+'×'+t.h+')'):('below '+t.w+'×'+t.h+' at 300 DPI'),okRes);
  var pass=dev<=0.015&&okRes;
  set('r-verdict',pass?'Pass — size looks right':(okRes?'Crop needed — use the download':'Too small — retake or rescan'),pass);
  var cw,ch;
  if(have>want){ch=img.naturalHeight;cw=Math.round(ch*want);}else{cw=img.naturalWidth;ch=Math.round(cw/want);}
  var sx=Math.round((img.naturalWidth-cw)/2),sy=Math.round((img.naturalHeight-ch)*0.38);
  cropCanvas=document.createElement('canvas');cropCanvas.width=t.w;cropCanvas.height=t.h;
  var cx=cropCanvas.getContext('2d');cx.imageSmoothingQuality='high';
  cx.drawImage(img,sx,sy,cw,ch,0,0,t.w,t.h);
  var prev=document.getElementById('prev');prev.hidden=false;
  var scale=Math.min(1,340/t.h);prev.width=Math.round(t.w*scale);prev.height=Math.round(t.h*scale);
  prev.getContext('2d').drawImage(cropCanvas,0,0,prev.width,prev.height);
  dl.disabled=false;cur=t;}
file.addEventListener('change',function(){var f=file.files[0];if(!f)return;
  var u=URL.createObjectURL(f);img=new Image();
  img.onload=function(){URL.revokeObjectURL(u);analyze();};img.src=u;});
sel.addEventListener('change',analyze);
dl.addEventListener('click',function(){if(!cropCanvas)return;
  cropCanvas.toBlob(function(b){var a=document.createElement('a');
    a.href=URL.createObjectURL(b);a.download='photo-'+cur.s.id+'-'+cur.w+'x'+cur.h+'.jpg';
    a.click();setTimeout(function(){URL.revokeObjectURL(a.href);},4000);},'image/jpeg',0.92);});
""" % jsl(standards)
    return {
        "slug": "passport-photo-checker",
        "queries": ["passport photo checker", "id photo crop", "passport photo crop"],
        "app_key": "snapport",
        "app_id": "6780575828",
        "app_name": "Snapport: Passport & ID Photos",
        "app_heading": "Need guided ID photos on iPhone?",
        "title": "Passport Photo Checker — Free ID Photo Size Check & Crop Online",
        "description": "Check a passport or ID photo against official sizes (US 2x2 in, 35x45 mm and more), see if the resolution is enough for 300 DPI printing, and download a centered crop. Free, in your browser, nothing uploaded.",
        "h1": "Passport photo checker",
        "eyebrow": "Free checker · runs on this page · nothing uploaded",
        "lead": "Pick a document standard, drop in a photo, and see instantly whether its size, aspect ratio and resolution fit — with a downloadable centered crop.",
        "badges": ["Photo never leaves your device", "10 official size standards", "300 DPI print check", "Free, no account"],
        "category": "UtilitiesApplication",
        "features": [
            "Ten passport/ID size standards (US, Schengen, UK, Taiwan, Japan, Korea, China, India, Canada, Philippines)",
            "Pixel, aspect-ratio and 300 DPI resolution verdicts",
            "Centered crop preview and JPEG download at exact target pixels",
            "All processing in the browser; no upload, account or storage",
        ],
        "how": "<ol><li>Choose the document standard — sizes come from each authority’s published requirement.</li><li>Select a photo. The page reads its pixel size locally.</li><li>Aspect ratio is compared with a 1.5% tolerance; resolution is compared against the 300 DPI print size.</li><li>Download a centered crop at the exact target pixels (crop is biased slightly upward, where faces usually sit).</li></ol>",
        "boundaries": "<ul><li>It never uploads, stores or transmits your photo.</li><li>It cannot verify head size, background color, glasses, expression or shadows.</li><li>A “Pass” here is a size check, not official approval — acceptance is always decided by the issuing authority.</li><li>It will not upscale a too-small photo into a fake high-resolution file.</li></ul>",
        "faq": [
            ("Is my photo uploaded anywhere?", "No. The file is read directly by your browser with the HTML file API and never leaves your device. There is no server, account or analytics on the photo."),
            ("Which sizes are supported?", "US 2×2 inch, the 35×45 mm family (Schengen/EU, UK, Taiwan, Japan, Korea, Philippines), China 33×48 mm, India 51×51 mm and Canada 50×70 mm."),
            ("Does a Pass mean my photo will be accepted?", "No. This tool checks size, aspect ratio and print resolution only. Authorities also judge background, head position, expression and lighting, which this page cannot see."),
            ("Why is the crop slightly above center?", "Faces usually sit in the upper part of a portrait, so the crop keeps about 38% of the spare height above the frame. Re-shoot if the face still is not positioned correctly."),
        ],
        "related": [
            ("passport-photo-size-guide.html", "Passport / ID photo size guide by country"),
            ("jpg-to-pdf.html", "JPG to PDF converter"),
            ("photo-mosaic-blur.html", "Mosaic / blur part of a photo"),
        ],
        "body": body,
        "script": script,
    }


def currency_converter():
    snapshot = json.loads(RATES_CACHE.read_text(encoding="utf-8"))
    names = {
        "USD": "US Dollar", "EUR": "Euro", "JPY": "Japanese Yen", "GBP": "British Pound",
        "AUD": "Australian Dollar", "BRL": "Brazilian Real", "CAD": "Canadian Dollar",
        "CHF": "Swiss Franc", "CNY": "Chinese Yuan", "CZK": "Czech Koruna",
        "DKK": "Danish Krone", "HKD": "Hong Kong Dollar", "HUF": "Hungarian Forint",
        "IDR": "Indonesian Rupiah", "ILS": "Israeli Shekel", "INR": "Indian Rupee",
        "ISK": "Icelandic Krona", "KRW": "South Korean Won", "MXN": "Mexican Peso",
        "MYR": "Malaysian Ringgit", "NOK": "Norwegian Krone", "NZD": "New Zealand Dollar",
        "PHP": "Philippine Peso", "PLN": "Polish Zloty", "RON": "Romanian Leu",
        "SEK": "Swedish Krona", "SGD": "Singapore Dollar", "THB": "Thai Baht",
        "TRY": "Turkish Lira", "ZAR": "South African Rand",
    }
    body = """
<h2>Convert between 30 currencies</h2>
<p class="intro">European Central Bank reference rates. The rate and its date are always shown — reference rates are not the rate your bank or card will give you.</p>
<div class="controls">
<div class="field"><label for="amt">Amount</label><input type="number" id="amt" value="100" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="from">From</label><select id="from"></select></div>
<div class="field"><label for="to">To</label><select id="to"></select></div>
</div>
<div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button ghost" id="swap">⇅ Swap</button>
</div>
<div class="results">
<div class="result" style="grid-column:1/-1"><strong>Converted</strong><span id="res">—</span></div>
<div class="result" style="grid-column:1/-1"><strong>Rate</strong><span id="rate">—</span></div>
<div class="result" style="grid-column:1/-1"><strong>Rates as of</strong><span id="asof">—</span></div>
</div>
<p class="note" id="srcnote">ECB reference rates. Cards, banks and exchange counters add their own margin — treat this as a fair mid-market reference, not a quote.</p>
"""
    script = """
var SNAP=%s,NAMES=%s;
var rates=null,asof='',src='';
function useData(base,d,date,label){rates={};rates[base]=1;
  for(var k in d)rates[k]=d[k];asof=date;src=label;fill();calc();}
function fill(){var codes=Object.keys(rates).sort();
  ['from','to'].forEach(function(id){var sel=document.getElementById(id);
    var keep=sel.value;sel.innerHTML='';
    codes.forEach(function(c){var o=document.createElement('option');o.value=c;
      o.textContent=c+(NAMES[c]?' — '+NAMES[c]:'');sel.appendChild(o);});
    sel.value=keep&&codes.indexOf(keep)>=0?keep:(id==='from'?'USD':'EUR');});}
function fmt(x){return x.toLocaleString(undefined,{maximumFractionDigits:x>=100?2:4});}
function calc(){if(!rates)return;
  var a=parseFloat(document.getElementById('amt').value)||0;
  var f=document.getElementById('from').value,t=document.getElementById('to').value;
  var r=rates[t]/rates[f];
  document.getElementById('res').textContent=fmt(a)+' '+f+' = '+fmt(a*r)+' '+t;
  document.getElementById('rate').textContent='1 '+f+' = '+fmt(r)+' '+t;
  document.getElementById('asof').textContent=asof+' · '+src;}
['amt','from','to'].forEach(function(id){
  document.getElementById(id).addEventListener('input',calc);
  document.getElementById(id).addEventListener('change',calc);});
document.getElementById('swap').addEventListener('click',function(){
  var f=document.getElementById('from'),t=document.getElementById('to');
  var v=f.value;f.value=t.value;t.value=v;calc();});
useData(SNAP.base,SNAP.rates,SNAP.date,'built-in ECB snapshot');
fetch('https://api.frankfurter.dev/v1/latest?base=USD').then(function(r){return r.json();})
  .then(function(d){if(d&&d.rates)useData(d.base,d.rates,d.date,'live ECB reference (frankfurter.dev)');})
  .catch(function(){});
""" % (jsl(snapshot), jsl(names))
    return {
        "slug": "currency-converter",
        "queries": ["currency converter", "exchange rate calculator", "exchange rate converter"],
        "app_key": "gmoney",
        "app_id": "6755782939",
        "app_name": "G+Money",
        "app_heading": "Tracking money across currencies on iPhone?",
        "title": "Currency Converter — Free Exchange Rate Calculator (ECB Reference Rates)",
        "description": "Convert between 30 currencies with dated European Central Bank reference rates. Free exchange rate calculator that shows its rate, its date and its source — no account, no ads-wall.",
        "h1": "Currency converter",
        "eyebrow": "ECB reference rates · date always shown · free",
        "lead": "A converter that tells you exactly which rate it used and when it was published — because a rate without a date is a guess.",
        "badges": ["30 currencies", "Dated ECB reference rates", "Works offline after load", "No account"],
        "category": "FinanceApplication",
        "features": [
            "30-currency conversion on ECB reference rates",
            "Rate, date and source always displayed",
            "Built-in dated snapshot works even if the live feed is unreachable",
            "No account, tracking wall or hidden margin",
        ],
        "how": "<ol><li>The page ships with a dated ECB snapshot, then tries to refresh from the open frankfurter.dev feed of ECB reference rates.</li><li>Conversion is transparent cross-rate math: amount × rate(to) ÷ rate(from) against the USD base.</li><li>The rate line and its publication date update with every input.</li></ol>",
        "boundaries": "<ul><li>It never claims to show the rate your bank, card or exchange counter will give you — those include margins this page cannot know.</li><li>No quotes, no predictions, no “best time to exchange” advice.</li><li>ECB publishes reference rates on working days; weekends show the last working-day rate with its date.</li></ul>",
        "faq": [
            ("Where do the rates come from?", "European Central Bank reference rates, via the open frankfurter.dev API, with a dated built-in snapshot as fallback. The source and date are always displayed under the result."),
            ("Is this the rate I will get at my bank?", "No. Banks, cards and exchange counters add their own margin and fees. ECB reference rates are a fair mid-market reference for comparison only."),
            ("Does it work offline?", "After the page loads once, conversion keeps working with the most recent rates it has, and keeps showing their date so you always know how fresh they are."),
            ("Why only 30 currencies?", "The ECB publishes reference rates for these currencies. The page will not fill the gaps with unsourced numbers."),
        ],
        "related": [
            ("hours-of-work-calculator.html", "Hours of work calculator (price → work time)"),
            ("subscription-cost-calculator.html", "Subscription cost calculator"),
            ("paycheck-budget-calculator.html", "Paycheck budget calculator"),
        ],
        "body": body,
        "script": script,
    }


def paycheck_budget():
    body = """
<h2>Split one paycheck honestly</h2>
<p class="intro">Enter what actually lands in your account. The split is editable — 50/30/20 is a starting point, not a rule.</p>
<div class="controls">
<div class="field"><label for="pay">Take-home per paycheck</label><input type="number" id="pay" value="2000" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="freq">Pay frequency</label><select id="freq">
<option value="4.3333">Weekly</option><option value="2.1667" selected>Every two weeks</option>
<option value="2">Twice a month</option><option value="1">Monthly</option></select></div>
<div class="field"><label for="bills">Fixed monthly bills (rent, utilities…)</label><input type="number" id="bills" value="900" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="pn">Needs %</label><input type="number" id="pn" value="50" min="0" max="100"></div>
<div class="field"><label for="pw">Wants %</label><input type="number" id="pw" value="30" min="0" max="100"></div>
<div class="field"><label for="ps">Savings % (auto = 100 − needs − wants)</label><input type="number" id="ps" value="20" readonly></div>
</div>
<div class="results">
<div class="result"><strong>Monthly take-home</strong><span id="m-total">—</span></div>
<div class="result"><strong>Needs / month</strong><span id="m-needs">—</span></div>
<div class="result"><strong>Wants / month</strong><span id="m-wants">—</span></div>
<div class="result"><strong>Savings / month</strong><span id="m-save">—</span></div>
<div class="result"><strong>Needs / paycheck</strong><span id="p-needs">—</span></div>
<div class="result"><strong>Wants / paycheck</strong><span id="p-wants">—</span></div>
<div class="result"><strong>Savings / paycheck</strong><span id="p-save">—</span></div>
<div class="result" id="left-box"><strong>Needs left after fixed bills</strong><span id="m-left">—</span></div>
</div>
<p class="note" id="warn" hidden></p>
<p class="small">Math: monthly = paycheck × factor (weekly 52/12, biweekly 26/12, semi-monthly 2, monthly 1). Nothing is saved or sent anywhere.</p>
"""
    script = """
function n(id){return parseFloat(document.getElementById(id).value)||0;}
function fmt(x){return x.toLocaleString(undefined,{maximumFractionDigits:0});}
function set(id,v){document.getElementById(id).textContent=fmt(v);}
function calc(){
  var pn=Math.min(100,Math.max(0,n('pn'))),pw=Math.min(100,Math.max(0,n('pw')));
  var ps=Math.max(0,100-pn-pw);document.getElementById('ps').value=ps.toFixed(0);
  var pay=n('pay'),factor=parseFloat(document.getElementById('freq').value);
  var monthly=pay*factor,bills=n('bills');
  set('m-total',monthly);set('m-needs',monthly*pn/100);set('m-wants',monthly*pw/100);set('m-save',monthly*ps/100);
  set('p-needs',pay*pn/100);set('p-wants',pay*pw/100);set('p-save',pay*ps/100);
  var left=monthly*pn/100-bills;set('m-left',left);
  var box=document.getElementById('left-box');box.classList.toggle('err',left<0);box.classList.toggle('ok',left>=0);
  var w=document.getElementById('warn');
  if(pn+pw>100){w.hidden=false;w.textContent='Needs + wants exceed 100% — savings is set to 0 and the split no longer adds up. Reduce one of them.';}
  else if(left<0){w.hidden=false;w.textContent='Fixed bills are larger than the whole needs bucket. This is a signal to raise the needs %, not to hide the gap.';}
  else w.hidden=true;}
['pay','freq','bills','pn','pw'].forEach(function(id){
  document.getElementById(id).addEventListener('input',calc);
  document.getElementById(id).addEventListener('change',calc);});
calc();
"""
    return {
        "slug": "paycheck-budget-calculator",
        "queries": ["budget calculator", "budget by paycheck", "budget planner"],
        "app_key": "hourstag",
        "app_id": "6754218117",
        "app_name": "HoursTag: Hours to Buy",
        "app_heading": "Want to see prices as hours of your work?",
        "title": "Paycheck Budget Calculator — Free Budget by Paycheck (50/30/20, Editable)",
        "description": "Split each paycheck into needs, wants and savings with transparent math. Editable 50/30/20 split, per-paycheck and per-month numbers, fixed-bills check. Free, no account, nothing stored.",
        "h1": "Paycheck budget calculator",
        "eyebrow": "Budget by paycheck · transparent math · free",
        "lead": "Start from the money that actually arrives, split it per paycheck and per month, and see immediately whether fixed bills even fit inside the needs bucket.",
        "badges": ["Per-paycheck and monthly view", "Editable 50/30/20", "Fixed-bills reality check", "Nothing saved or sent"],
        "category": "FinanceApplication",
        "features": [
            "Weekly, biweekly, semi-monthly and monthly pay frequencies",
            "Editable needs/wants percentages with auto-balancing savings",
            "Per-paycheck and per-month amounts side by side",
            "Fixed-bills vs needs-bucket check with visible math",
        ],
        "how": "<ol><li>Enter take-home pay per paycheck and how often you are paid.</li><li>Monthly income = paycheck × frequency factor (weekly 52÷12, biweekly 26÷12, twice a month 2, monthly 1).</li><li>The needs/wants/savings split applies to both views; savings auto-balances to keep the total at 100%.</li><li>Fixed bills are subtracted from the monthly needs bucket so a shortfall is visible, not hidden.</li></ol>",
        "boundaries": "<ul><li>No budgeting advice — the split percentages are yours to change.</li><li>No income, spending or savings prediction; it only rearranges numbers you typed.</li><li>Nothing is stored: reloading the page clears everything.</li></ul>",
        "faq": [
            ("Is 50/30/20 a rule I should follow?", "It is a common starting point, nothing more. The point of this calculator is that the split is editable — high-rent cities often need a much larger needs share."),
            ("Why per paycheck instead of per month?", "Most people are paid weekly or biweekly, and overspending happens between paychecks. Seeing both views keeps the monthly plan and the between-paychecks reality connected."),
            ("Does it store my income?", "No. There is no account, no localStorage and no network call. Numbers exist only while the page is open."),
            ("What does a red ‘needs left’ mean?", "Your fixed bills are bigger than the entire needs bucket at the current split, so the plan is not realistic yet — raise the needs percentage or lower a bill."),
        ],
        "related": [
            ("hours-of-work-calculator.html", "Hours of work calculator (price → work time)"),
            ("subscription-cost-calculator.html", "Subscription cost calculator"),
            ("currency-converter.html", "Currency converter (ECB reference rates)"),
        ],
        "body": body,
        "script": script,
    }


def resume_maker():
    body = """
<h2>Fill in, preview, print to PDF</h2>
<p class="intro">Everything stays on this page. Print with your browser (⌘P / Ctrl-P) and choose “Save as PDF”.</p>
<div class="controls">
<div class="field"><label for="f-name">Full name</label><input id="f-name" value="" placeholder="Jordan Lee"></div>
<div class="field"><label for="f-title">Target role</label><input id="f-title" placeholder="Product Designer"></div>
<div class="field"><label for="f-contact">Contact line</label><input id="f-contact" placeholder="city · email · phone"></div>
</div>
<div class="field" style="margin-top:12px"><label for="f-summary">Summary (2–3 lines)</label><textarea id="f-summary" placeholder="What you do, for whom, with what results."></textarea></div>
<div class="field" style="margin-top:12px"><label for="f-skills">Skills (comma separated)</label><input id="f-skills" placeholder="Figma, prototyping, user research"></div>
<div id="jobs"></div>
<div class="field" style="margin-top:12px"><label for="f-edu">Education (one line per entry)</label><textarea id="f-edu" placeholder="B.S. Computer Science — State University, 2019"></textarea></div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button" onclick="window.print()">Print / save as PDF</button>
<button class="button ghost" id="tpl">Switch template</button>
</div>
<div id="resume" class="resume classic" style="margin-top:22px">
<div id="rv"></div>
</div>
<p class="note">An ATS reads printed text, not design tricks: this template is single-column, real text, no tables or graphics — the safest structure for automated screening.</p>
"""
    extra_css = """
.resume{background:#fff;border:1px solid var(--line);border-radius:6px;padding:34px 40px;max-width:730px;box-shadow:var(--shadow)}
.resume h3{font-size:26px;margin:0}.resume .rt{color:#666;margin:2px 0 2px;font-size:15px}
.resume .rc{color:#777;font-size:13px;margin:0 0 12px}
.resume h4{font-size:13px;letter-spacing:.09em;text-transform:uppercase;border-bottom:1px solid #ddd;padding-bottom:4px;margin:16px 0 8px}
.resume p,.resume li{font-size:13.5px;line-height:1.5;margin:4px 0}
.resume ul{margin:4px 0;padding-left:18px}
.resume .job b{font-size:14px}.resume .job i{color:#666;font-style:normal;font-size:12.5px;float:right}
.resume.classic{font-family:ui-serif,Georgia,serif}
.resume.modern{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.resume.modern h3{letter-spacing:-.02em}.resume.modern h4{border-color:#c8922a;color:#9a6b16}
@media print{body *{visibility:hidden}#resume,#resume *{visibility:visible}#resume{position:absolute;left:0;top:0;width:100%;max-width:none;border:0;box-shadow:none;border-radius:0}}
"""
    script = """
var JOBS=3,jobsDiv=document.getElementById('jobs');
for(var i=1;i<=JOBS;i++){jobsDiv.insertAdjacentHTML('beforeend',
 '<div class="controls" style="margin-top:12px">'
 +'<div class="field"><label>Role '+i+'</label><input id="j'+i+'r" placeholder="Role"></div>'
 +'<div class="field"><label>Company · dates</label><input id="j'+i+'c" placeholder="Company · 2021–2024"></div>'
 +'<div class="field"><label>Bullets (one per line)</label><textarea id="j'+i+'b" placeholder="Did X, which led to Y"></textarea></div></div>');}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
function lines(s){return s.split('\\n').map(function(x){return x.trim();}).filter(Boolean);}
function render(){
 var h='';
 var name=val('f-name'),title=val('f-title'),contact=val('f-contact');
 h+='<h3>'+esc(name||'Your Name')+'</h3>';
 if(title)h+='<p class="rt">'+esc(title)+'</p>';
 if(contact)h+='<p class="rc">'+esc(contact)+'</p>';
 var sum=val('f-summary');if(sum)h+='<h4>Summary</h4><p>'+esc(sum)+'</p>';
 var jobs='';
 for(var i=1;i<=JOBS;i++){var r=val('j'+i+'r'),c=val('j'+i+'c'),b=lines(val('j'+i+'b'));
   if(!r&&!c&&!b.length)continue;
   jobs+='<div class="job"><p><b>'+esc(r)+'</b> <i>'+esc(c)+'</i></p>';
   if(b.length)jobs+='<ul>'+b.map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul>';
   jobs+='</div>';}
 if(jobs)h+='<h4>Experience</h4>'+jobs;
 var sk=val('f-skills');if(sk)h+='<h4>Skills</h4><p>'+esc(sk)+'</p>';
 var ed=lines(val('f-edu'));if(ed.length)h+='<h4>Education</h4>'+ed.map(function(x){return '<p>'+esc(x)+'</p>';}).join('');
 document.getElementById('rv').innerHTML=h;}
function val(id){return document.getElementById(id).value;}
document.querySelectorAll('input,textarea').forEach(function(el){el.addEventListener('input',render);});
document.getElementById('tpl').addEventListener('click',function(){
 document.getElementById('resume').classList.toggle('classic');
 document.getElementById('resume').classList.toggle('modern');});
render();
"""
    return {
        "slug": "resume-template-maker",
        "queries": ["free resume maker", "resume templates", "cv maker free", "free resume template"],
        "app_key": "cvdesk",
        "app_id": "6781337213",
        "app_name": "CV Desk: ATS Resume Builder",
        "app_heading": "Building and iterating resumes on iPhone?",
        "title": "Free Resume Maker — Clean ATS-Safe Template, Print to PDF, No Sign-Up",
        "description": "Type your details, preview a clean single-column ATS-safe resume in two template styles, and print to PDF with your browser. Completely free, no account, nothing uploaded or stored.",
        "h1": "Free resume maker",
        "eyebrow": "No sign-up · no watermark · print to PDF",
        "lead": "A resume template that fills itself in as you type — single-column, real text, ATS-safe — then prints to PDF straight from your browser.",
        "badges": ["No account or sign-up", "No watermark", "ATS-safe single column", "Nothing uploaded"],
        "category": "BusinessApplication",
        "features": [
            "Live preview in two template styles (classic serif, modern)",
            "Single-column ATS-safe structure with real text only",
            "Print-to-PDF via the browser with print-optimized CSS",
            "No account, upload, storage or watermark",
        ],
        "how": "<ol><li>Fill the form — the preview updates with every keystroke.</li><li>Empty sections disappear automatically, so a short resume still looks intentional.</li><li>Switch between the serif and modern template any time; content is identical.</li><li>Print with ⌘P / Ctrl-P and choose “Save as PDF” — the print stylesheet outputs only the resume.</li></ol>",
        "boundaries": "<ul><li>No writing advice, keyword stuffing or AI-generated claims about you.</li><li>Nothing is uploaded or stored — closing the tab discards the draft, so print or copy your text before leaving.</li><li>It cannot guarantee any screening outcome; it only guarantees a structure ATS parsers read reliably.</li></ul>",
        "faq": [
            ("Is it really free, with no watermark?", "Yes. The page has no account, no paywall and adds nothing to the printed output. What you see in the preview is exactly what prints."),
            ("Is the template ATS-safe?", "It is single-column, real text, with standard section headings and no tables, columns, icons or graphics — the structure automated screeners parse most reliably."),
            ("Where is my data stored?", "Nowhere. The draft lives only in the open page. Closing or reloading the tab clears it, so save your PDF first."),
            ("How do I get a PDF?", "Use your browser’s print dialog (⌘P / Ctrl-P) and choose “Save as PDF”. The print stylesheet hides everything except the resume itself."),
        ],
        "related": [
            ("ats-resume-keyword-checker.html", "ATS resume keyword checker"),
            ("meeting-notes-template-generator.html", "Meeting notes template generator"),
        ],
        "body": body,
        "script": script,
        "extra_css": extra_css,
        "print_css": "",
    }


def jpg_to_pdf():
    body = """
<h2>Combine images into one PDF</h2>
<p class="intro">Pick photos or scans, order them, download a PDF. Files are processed by your browser only.</p>
<div class="filedrop"><input type="file" id="file" accept="image/*" multiple> <span class="small">JPG, PNG, WebP — multiple allowed</span></div>
<div class="controls" style="margin-top:14px">
<div class="field"><label for="size">Page size</label><select id="size">
<option value="a4">A4</option><option value="letter">US Letter</option><option value="fit">Fit each image</option></select></div>
<div class="field"><label for="margin">Margin</label><select id="margin">
<option value="24">Normal</option><option value="0">None</option><option value="48">Wide</option></select></div>
<div class="field"><label>&nbsp;</label><button class="button" id="make" disabled>Download PDF</button></div>
</div>
<ol id="list" style="margin-top:14px;padding-left:22px"></ol>
<p class="note">Each image becomes one PDF page. Nothing is uploaded — the PDF is assembled locally in your browser.</p>
"""
    script = r"""
var files=[];
var input=document.getElementById('file'),list=document.getElementById('list'),make=document.getElementById('make');
input.addEventListener('change',function(){
  for(var i=0;i<input.files.length;i++)files.push(input.files[i]);
  input.value='';draw();});
function draw(){list.innerHTML='';
  files.forEach(function(f,i){
    var li=document.createElement('li');
    li.innerHTML=esc(f.name)+' <button data-a="up" data-i="'+i+'">↑</button> <button data-a="dn" data-i="'+i+'">↓</button> <button data-a="rm" data-i="'+i+'">✕</button>';
    list.appendChild(li);});
  make.disabled=!files.length;}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
list.addEventListener('click',function(e){
  var b=e.target.closest('button');if(!b)return;
  var i=+b.dataset.i,a=b.dataset.a;
  if(a==='rm')files.splice(i,1);
  if(a==='up'&&i>0){var t=files[i-1];files[i-1]=files[i];files[i]=t;}
  if(a==='dn'&&i<files.length-1){var t2=files[i+1];files[i+1]=files[i];files[i]=t2;}
  draw();});
function loadImage(f){return new Promise(function(res,rej){
  var u=URL.createObjectURL(f),im=new Image();
  im.onload=function(){res({img:im,url:u});};im.onerror=rej;im.src=u;});}
function toJpeg(img){
  var MAX=2600,w=img.naturalWidth,h=img.naturalHeight;
  var s=Math.min(1,MAX/Math.max(w,h));w=Math.round(w*s);h=Math.round(h*s);
  var c=document.createElement('canvas');c.width=w;c.height=h;
  var x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,w,h);x.drawImage(img,0,0,w,h);
  return new Promise(function(res){c.toBlob(function(b){
    b.arrayBuffer().then(function(buf){res({bytes:new Uint8Array(buf),w:w,h:h});});},'image/jpeg',0.9);});}
function buildPdf(images,pageSize,margin){
  var enc=new TextEncoder(),parts=[],offsets=[],pos=0;
  function push(x){var b=typeof x==='string'?enc.encode(x):x;parts.push(b);pos+=b.length;}
  function obj(id,body){offsets[id]=pos;push(id+' 0 obj\n'+body+'\nendobj\n');}
  push('%PDF-1.4\n');
  var n=images.length,kids=[];
  for(var i=0;i<n;i++)kids.push((5+i*3)+' 0 R');
  obj(1,'<< /Type /Catalog /Pages 2 0 R >>');
  obj(2,'<< /Type /Pages /Kids ['+kids.join(' ')+'] /Count '+n+' >>');
  for(var i=0;i<n;i++){
    var im=images[i];
    var pw,ph;
    if(pageSize==='a4'){pw=595.28;ph=841.89;}
    else if(pageSize==='letter'){pw=612;ph=792;}
    else{pw=im.w*72/96+2*margin;ph=im.h*72/96+2*margin;}
    var availW=pw-2*margin,availH=ph-2*margin;
    var s=Math.min(availW/im.w,availH/im.h);
    var dw=im.w*s,dh=im.h*s,dx=(pw-dw)/2,dy=(ph-dh)/2;
    var xo=3+i*3,co=4+i*3,po=5+i*3;
    offsets[xo]=pos;
    push(xo+' 0 obj\n<< /Type /XObject /Subtype /Image /Width '+im.w+' /Height '+im.h
      +' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '+im.bytes.length+' >>\nstream\n');
    push(im.bytes);push('\nendstream\nendobj\n');
    var content='q '+dw.toFixed(2)+' 0 0 '+dh.toFixed(2)+' '+dx.toFixed(2)+' '+dy.toFixed(2)+' cm /Im'+i+' Do Q';
    obj(co,'<< /Length '+content.length+' >>\nstream\n'+content+'\nendstream');
    obj(po,'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '+pw.toFixed(2)+' '+ph.toFixed(2)
      +'] /Resources << /XObject << /Im'+i+' '+xo+' 0 R >> >> /Contents '+co+' 0 R >>');}
  var total=3+n*3;
  var xref=pos,table='xref\n0 '+total+'\n0000000000 65535 f \n';
  for(var id=1;id<total;id++){
    table+=String(offsets[id]).padStart(10,'0')+' 00000 n \n';}
  push(table+'trailer\n<< /Size '+total+' /Root 1 0 R >>\nstartxref\n'+xref+'\n%%EOF');
  return new Blob(parts,{type:'application/pdf'});}
make.addEventListener('click',function(){
  make.disabled=true;make.textContent='Working…';
  var pageSize=document.getElementById('size').value;
  var margin=parseFloat(document.getElementById('margin').value);
  Promise.all(files.map(loadImage)).then(function(loaded){
    return Promise.all(loaded.map(function(l){
      var p=toJpeg(l.img);URL.revokeObjectURL(l.url);return p;}));
  }).then(function(images){
    var blob=buildPdf(images,pageSize,margin);
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='images.pdf';a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},5000);
  }).catch(function(e){alert('Could not read one of the images: '+e);})
  .finally(function(){make.disabled=false;make.textContent='Download PDF';});});
"""
    return {
        "slug": "jpg-to-pdf",
        "queries": ["scanner to pdf", "free scanner to pdf", "scan pdf", "jpg to pdf"],
        "app_key": "scanto",
        "app_id": "6779977651",
        "app_name": "ScanTo Pro: Offline PDF & OCR",
        "app_heading": "Scanning documents regularly on iPhone?",
        "title": "JPG to PDF Converter — Free, Private, Runs in Your Browser",
        "description": "Turn photos or scans (JPG, PNG, WebP) into a single PDF directly in your browser. Reorder pages, choose A4, Letter or fit-to-image. Free, no upload, no watermark, no account.",
        "h1": "JPG to PDF converter",
        "eyebrow": "No upload · no watermark · assembled locally",
        "lead": "Select images, put them in order, download one PDF. The whole conversion happens inside your browser — your documents never touch a server.",
        "badges": ["Files never uploaded", "Multiple images → one PDF", "A4 / Letter / fit", "No watermark"],
        "category": "UtilitiesApplication",
        "features": [
            "Multiple JPG/PNG/WebP images combined into one PDF",
            "Page reorder and remove before export",
            "A4, US Letter or fit-to-image pages with margin options",
            "PDF assembled locally in the browser; no upload or account",
        ],
        "how": "<ol><li>Selected images are read locally with the file API.</li><li>Each image is normalized to JPEG (long edge capped at 2600 px, white background) on a canvas.</li><li>A minimal PDF is assembled in the page — one image per page, scaled into your chosen page size and margin.</li><li>The result downloads as a normal PDF file; nothing is transmitted.</li></ol>",
        "boundaries": "<ul><li>No OCR — the output PDF contains images, not selectable text.</li><li>No compression promises: file size depends on your images.</li><li>Nothing is uploaded, logged or kept; reloading the page clears the list.</li></ul>",
        "faq": [
            ("Are my documents uploaded to a server?", "No. The images are read and the PDF is assembled entirely inside your browser. Airplane mode after loading the page works fine."),
            ("Is there a page limit or watermark?", "No watermark, no forced limit. Very large batches are limited only by your device’s memory."),
            ("Can it make the text searchable (OCR)?", "No. This tool outputs image pages. OCR needs an actual recognition engine, which is exactly the kind of job a dedicated scanning app does better."),
            ("Why do my photos get converted to JPEG?", "PDF embeds JPEG natively and it keeps files small. Images are drawn on a white background, so transparent PNGs stay readable."),
        ],
        "related": [
            ("image-to-pdf-iphone.html", "Image to PDF on iPhone (built-in ways)"),
            ("photo-storage-calculator.html", "Photo storage calculator"),
            ("passport-photo-checker.html", "Passport photo checker"),
        ],
        "body": body,
        "script": script,
    }


def mosaic_blur():
    body = """
<h2>Hide part of a photo</h2>
<p class="intro">Load a photo, drag over what should disappear — faces, names, addresses, plates. The photo never leaves your device.</p>
<div class="controls">
<div class="field"><label for="file">Photo</label><input type="file" id="file" accept="image/*"></div>
<div class="field"><label for="mode">Effect</label><select id="mode"><option value="mosaic">Mosaic (pixelate)</option><option value="blur">Blur</option><option value="black">Solid black</option></select></div>
<div class="field"><label for="strength">Strength</label><input type="range" id="strength" min="6" max="40" value="16" style="width:100%"></div>
</div>
<div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button ghost" id="undo" disabled>Undo</button>
<button class="button" id="dl" disabled>Download image</button>
</div>
<div style="margin-top:16px"><canvas class="stage" id="stage" width="10" height="10" hidden></canvas></div>
<p class="note"><strong>Mosaic and blur can sometimes be reversed</strong> by specialized software, especially small text at low strength. For text you must truly redact, use “Solid black”, which destroys the pixels completely.</p>
"""
    script = """
var img=null,ops=[],canvas=document.getElementById('stage'),ctx=canvas.getContext('2d');
var fileEl=document.getElementById('file'),undoBtn=document.getElementById('undo'),dlBtn=document.getElementById('dl');
var drag=null;
fileEl.addEventListener('change',function(){var f=fileEl.files[0];if(!f)return;
  var u=URL.createObjectURL(f);var im=new Image();
  im.onload=function(){URL.revokeObjectURL(u);img=im;ops=[];
    var MAX=2200,s=Math.min(1,MAX/Math.max(im.naturalWidth,im.naturalHeight));
    canvas.width=Math.round(im.naturalWidth*s);canvas.height=Math.round(im.naturalHeight*s);
    canvas.hidden=false;render();dlBtn.disabled=false;};
  im.src=u;});
function render(){if(!img)return;
  ctx.filter='none';ctx.imageSmoothingEnabled=true;
  ctx.drawImage(img,0,0,canvas.width,canvas.height);
  ops.forEach(function(op){apply(op);});
  undoBtn.disabled=!ops.length;}
function apply(op){
  var x=op.x,y=op.y,w=op.w,h=op.h;
  if(w<3||h<3)return;
  if(op.mode==='black'){ctx.fillStyle='#000';ctx.fillRect(x,y,w,h);return;}
  if(op.mode==='blur'){
    var t=document.createElement('canvas');t.width=w;t.height=h;
    var tx=t.getContext('2d');
    tx.filter='blur('+Math.round(op.strength/2)+'px)';
    tx.drawImage(canvas,x,y,w,h,0,0,w,h);
    ctx.drawImage(t,x,y);return;}
  var bs=Math.max(2,Math.round(op.strength));
  var sw=Math.max(1,Math.round(w/bs)),sh=Math.max(1,Math.round(h/bs));
  var t2=document.createElement('canvas');t2.width=sw;t2.height=sh;
  var t2x=t2.getContext('2d');
  t2x.drawImage(canvas,x,y,w,h,0,0,sw,sh);
  ctx.imageSmoothingEnabled=false;
  ctx.drawImage(t2,0,0,sw,sh,x,y,w,h);
  ctx.imageSmoothingEnabled=true;}
function pos(e){var r=canvas.getBoundingClientRect();
  return {x:(e.clientX-r.left)*canvas.width/r.width,
          y:(e.clientY-r.top)*canvas.height/r.height};}
canvas.addEventListener('pointerdown',function(e){if(!img)return;
  canvas.setPointerCapture(e.pointerId);drag=pos(e);e.preventDefault();});
canvas.addEventListener('pointermove',function(e){if(!drag)return;
  var p=pos(e);render();
  ctx.save();ctx.strokeStyle='#c8922a';ctx.lineWidth=2;ctx.setLineDash([6,4]);
  ctx.strokeRect(Math.min(drag.x,p.x),Math.min(drag.y,p.y),Math.abs(p.x-drag.x),Math.abs(p.y-drag.y));
  ctx.restore();});
canvas.addEventListener('pointerup',function(e){if(!drag)return;
  var p=pos(e);
  var op={x:Math.round(Math.min(drag.x,p.x)),y:Math.round(Math.min(drag.y,p.y)),
    w:Math.round(Math.abs(p.x-drag.x)),h:Math.round(Math.abs(p.y-drag.y)),
    mode:document.getElementById('mode').value,
    strength:parseInt(document.getElementById('strength').value,10)};
  drag=null;
  if(op.w>=3&&op.h>=3)ops.push(op);
  render();});
undoBtn.addEventListener('click',function(){ops.pop();render();});
dlBtn.addEventListener('click',function(){render();
  canvas.toBlob(function(b){var a=document.createElement('a');
    a.href=URL.createObjectURL(b);a.download='redacted.jpg';a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},4000);},'image/jpeg',0.92);});
"""
    return {
        "slug": "photo-mosaic-blur",
        "queries": ["mosaic blur photo maker", "blur part of a photo", "pixelate photo"],
        "app_key": "maskmyfile",
        "app_id": "6792850916",
        "app_name": "Mask My File",
        "app_heading": "Redacting files and screenshots on iPhone?",
        "title": "Mosaic Blur Photo Tool — Pixelate, Blur or Black Out Part of a Photo Online",
        "description": "Drag over faces, names or plates to pixelate, blur or black them out — directly in your browser. Free mosaic blur photo maker with honest notes on what blur can and cannot protect. Nothing uploaded.",
        "h1": "Mosaic / blur part of a photo",
        "eyebrow": "Free redaction tool · nothing uploaded · honest limits",
        "lead": "Drag rectangles over anything that should not be shared. Choose mosaic, blur, or — for text that truly must go — solid black.",
        "badges": ["Photo never leaves your device", "Mosaic, blur or solid black", "Multi-region + undo", "Free, no account"],
        "category": "UtilitiesApplication",
        "features": [
            "Drag-to-select regions with mouse or touch",
            "Mosaic (pixelate), blur, and irreversible solid-black modes",
            "Multiple regions with undo",
            "JPEG export; all processing in the browser",
        ],
        "how": "<ol><li>The photo is drawn on a canvas in your browser (long edge capped at 2200 px).</li><li>Drag a rectangle; the selected pixels are pixelated, blurred, or filled black.</li><li>Stack as many regions as needed; undo removes the last one.</li><li>Download re-renders every region and exports a JPEG.</li></ol>",
        "boundaries": "<ul><li>It will not pretend mosaic is bulletproof: pixelation and blur of small text can sometimes be reversed — the page says so next to the tool.</li><li>No face detection, no automatic anything — you choose what disappears.</li><li>Nothing is uploaded or stored; EXIF metadata is dropped by re-encoding, but verify before sharing sensitive images.</li></ul>",
        "faq": [
            ("Is the photo uploaded for processing?", "No. Selection, pixelation, blur and export all run in your browser on a canvas. The image never leaves your device."),
            ("Can mosaic or blur be reversed?", "Sometimes, yes — research has reconstructed small pixelated text, especially at low strength. For information that absolutely must not leak, use the solid-black mode, which destroys the pixels."),
            ("Does the exported photo keep location metadata?", "The export is re-encoded from the canvas, which drops EXIF data including GPS coordinates. Still, always double-check before sharing anything sensitive."),
            ("Why is my huge photo downsized?", "The working canvas caps the long edge at 2200 px so redaction stays fast on phones. For full-resolution redaction, use a dedicated app."),
        ],
        "related": [
            ("blurry-photo-diagnostic.html", "Blurry photo diagnostic"),
            ("passport-photo-checker.html", "Passport photo checker"),
            ("jpg-to-pdf.html", "JPG to PDF converter"),
        ],
        "body": body,
        "script": script,
    }


TOOL_BUILDERS = [
    passport_checker,
    currency_converter,
    paycheck_budget,
    resume_maker,
    jpg_to_pdf,
    mosaic_blur,
]

INDEX_CARDS = {
    "passport-photo-checker": "Check a passport/ID photo against 10 official sizes and download a centered crop — nothing uploaded.",
    "currency-converter": "Convert 30 currencies on dated ECB reference rates that always show their source.",
    "paycheck-budget-calculator": "Split each paycheck into needs, wants and savings with editable, transparent math.",
    "resume-template-maker": "Type, preview an ATS-safe template and print to PDF — no sign-up, no watermark.",
    "jpg-to-pdf": "Combine photos or scans into one PDF entirely in your browser — no upload, no watermark.",
    "photo-mosaic-blur": "Pixelate, blur or black out parts of a photo before sharing — with honest limits.",
}


def update_index(tools):
    index = TOOLS / "index.html"
    text = index.read_text(encoding="utf-8")
    marker = "</section></main>"
    if marker not in text:
        raise RuntimeError("tools/index.html missing grid marker")
    added = 0
    for tool in tools:
        slug = tool["slug"]
        if f'href="{slug}.html"' in text:
            continue
        card = (
            f'<article class="card third" data-tool="{slug}">'
            f'<h2><a href="{slug}.html">{esc(tool["h1"][0].upper() + tool["h1"][1:])}</a></h2>'
            f"<p>{esc(INDEX_CARDS[slug])}</p></article>"
        )
        text = text.replace(marker, card + marker, 1)
        added += 1
    if added:
        index.write_text(text, encoding="utf-8")
    return added


def refresh_rates():
    """Refresh the embedded ECB snapshot; keep the cached one on any failure."""
    try:
        req = urllib.request.Request(
            "https://api.frankfurter.dev/v1/latest?base=USD",
            headers={"User-Agent": "Mozilla/5.0 (demand tools rates refresh)"},
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        if data.get("rates") and data.get("date"):
            RATES_CACHE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as exc:
        print(f"rates refresh skipped (using cached snapshot): {exc}")


def main():
    TOOLS.mkdir(parents=True, exist_ok=True)
    refresh_rates()
    tools = [build() for build in TOOL_BUILDERS]
    for tool in tools:
        out = TOOLS / f"{tool['slug']}.html"
        page = render_page(tool)
        if not out.exists() or out.read_text(encoding="utf-8") != page:
            out.write_text(page, encoding="utf-8")
            print(f"wrote tools/{tool['slug']}.html")
    added = update_index(tools)
    count = write_tools_sitemap()
    print(f"demand_tools: {len(tools)} tools, {added} new index cards, sitemap {count} urls")


if __name__ == "__main__":
    main()
