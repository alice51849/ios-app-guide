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
from site_config import PUBLIC_SITE  # noqa: E402
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
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


# Locales that get native-language tool pages.  Chosen from the search-demand
# audit: TH/MY/VN search in English (so no translation), JP/KR/DE/TW search in
# their own language.  Every localized page below is titled with a phrasing the
# engines themselves emitted — never a translated English sentence.
LOCALES = ("en", "ja", "ko", "de-DE", "zh-Hant")

CHROME = {
    "en": {
        "back": "← Free tools", "site": "iOS App Guide",
        "how": "How it works", "never": "What it will never do",
        "more": "More free tools", "questions": "Questions",
        "footer": "Runs in your browser · nothing is uploaded or stored",
        "all": "all free tools",
        "optional": "{app} is optional — this free tool runs entirely in your browser and works without it. Check the app’s current App Store listing for exact features, pricing and availability before downloading.",
        "cta": "View {app} on the App Store",
    },
    "ja": {
        "back": "← 無料ツール一覧", "site": "iOS App Guide",
        "how": "しくみ", "never": "このツールがしないこと",
        "more": "ほかの無料ツール", "questions": "よくある質問",
        "footer": "ブラウザ内で動作 · アップロード・保存は一切なし",
        "all": "無料ツール一覧",
        "optional": "{app} は任意です。このツールはブラウザだけで動くので、アプリがなくても使えます。機能・価格・配信状況は App Store の最新ページでご確認ください。",
        "cta": "App Store で {app} を見る",
    },
    "ko": {
        "back": "← 무료 도구", "site": "iOS App Guide",
        "how": "작동 방식", "never": "이 도구가 하지 않는 일",
        "more": "다른 무료 도구", "questions": "자주 묻는 질문",
        "footer": "브라우저에서 실행 · 업로드하거나 저장하지 않습니다",
        "all": "무료 도구 전체",
        "optional": "{app} 은(는) 선택 사항입니다. 이 도구는 브라우저에서만 동작하므로 앱 없이도 사용할 수 있습니다. 기능·가격·제공 여부는 App Store의 현재 페이지에서 확인하세요.",
        "cta": "App Store에서 {app} 보기",
    },
    "de-DE": {
        "back": "← Kostenlose Tools", "site": "iOS App Guide",
        "how": "So funktioniert es", "never": "Was dieses Tool nicht tut",
        "more": "Weitere kostenlose Tools", "questions": "Fragen",
        "footer": "Läuft im Browser · nichts wird hochgeladen oder gespeichert",
        "all": "alle kostenlosen Tools",
        "optional": "{app} ist optional — dieses Tool läuft komplett im Browser und funktioniert auch ohne die App. Funktionen, Preis und Verfügbarkeit stehen aktuell auf der App-Store-Seite.",
        "cta": "{app} im App Store ansehen",
    },
    "zh-Hant": {
        "back": "← 免費工具", "site": "iOS App Guide",
        "how": "運作方式", "never": "這個工具不會做的事",
        "more": "其他免費工具", "questions": "常見問題",
        "footer": "全部在瀏覽器內完成 · 不上傳、不儲存",
        "all": "所有免費工具",
        "optional": "{app} 是選用的——這個工具完全在瀏覽器裡執行，沒有 App 也能用。功能、價格與上架狀況請以 App Store 頁面為準。",
        "cta": "在 App Store 查看 {app}",
    },
}


def esc(text):
    return html.escape(text, quote=True)


def jsl(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def render_page(tool):
    lang = tool.get("lang", "en")
    sub = "" if lang == "en" else f"/{lang}"
    chrome = CHROME[lang]
    url = f"{SITE}{sub}/tools/{tool['slug']}.html"
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": lang,
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
        "inLanguage": lang,
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
    alts = "".join(
        f'\n<link rel="alternate" hreflang="{code}" href="{href}">'
        for code, href in tool.get("alts", [])
    )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(tool['title'])}</title>
<meta name="description" content="{esc(tool['description'])}">
<link rel="canonical" href="{url}">{alts}
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
<header class="top"><div class="wrap nav"><a href="index.html">{esc(chrome['back'])}</a><a href="{SITE}{sub}/" >{esc(chrome['site'])}</a></div></header>
<section class="hero wrap">
<span class="eyebrow">{esc(tool['eyebrow'])}</span>
<h1>{esc(tool['h1'])}</h1>
<p class="lead">{esc(tool['lead'])}</p>
<div class="badges">{badges}</div>
</section>
<main class="wrap">
<section class="tool" id="tool">{tool['body']}</section>
<section class="grid">
<article class="card"><h2>{esc(chrome['how'])}</h2>{tool['how']}</article>
<article class="card"><h2>{esc(chrome['never'])}</h2>{tool['boundaries']}</article>
<article class="card wide"><h2>{esc(chrome['more'])}</h2><ul>{related}</ul></article>
</section>
<section class="faq"><h2>{esc(chrome['questions'])}</h2>{faq_html}</section>
<section class="app-card"><h2>{esc(tool['app_heading'])}</h2>
<p>{esc(chrome['optional'].format(app=app_name))}</p>
<a class="button" href="{app_url}" rel="nofollow noopener">{esc(chrome['cta'].format(app=app_name))}</a></section>
</main>
<footer class="footer"><div class="wrap">{esc(tool.get('footer_note', chrome['footer']))} · <a href="index.html">{esc(chrome['all'])}</a></div></footer>
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


# ------------------------------------------------------------------ i18n core
#
# Everything below is a "spec": one working tool, one body/script pair, and a
# per-locale string table.  A spec is expanded into one page per locale listed
# in its string table.  Each locale entry records `q` — the engine-emitted
# queries (with their measured demand level) the page is built for — so the
# reason a page exists stays checkable in the source.


def bullets(items, tag="ul"):
    return f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>"


def make_tool(spec, lang):
    s = spec["i18n"][lang]
    ui = s["ui"]
    langs = list(spec["i18n"])
    alts = []
    for code in langs:
        sub = "" if code == "en" else f"/{code}"
        alts.append((code, f"{SITE}{sub}/tools/{spec['slug']}.html"))
    alts.append(("x-default", f"{SITE}/tools/{spec['slug']}.html"))
    tool = {
        "slug": spec["slug"],
        "lang": lang,
        "alts": alts,
        "queries": [q for q, _ in s["q"]],
        "demand": s["q"],
        "app_key": spec["app_key"],
        "app_id": spec["app_id"],
        "app_name": spec["app_name"],
        "category": spec["category"],
        "app_heading": s["app_heading"],
        "title": s["title"],
        "description": s["description"],
        "h1": s["h1"],
        "eyebrow": s["eyebrow"],
        "lead": s["lead"],
        "badges": s["badges"],
        "features": s["features"],
        "how": bullets(s["how"], "ol"),
        "boundaries": bullets(s["never"]),
        "faq": s["faq"],
        "card": s["card"],
        "body": spec["body"].format(ui=ui),
        "script": "var L=" + jsl(ui) + ";\n" + spec["script"],
    }
    for key in ("extra_css", "print_css"):
        if key in spec:
            tool[key] = spec[key]
    if "footer_note" in s:
        tool["footer_note"] = s["footer_note"]
    return tool


# ------------------------------------------------------------ 1. compressor

IMAGE_COMPRESSOR_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="filedrop"><input type="file" id="file" accept="image/*"> <span class="small">{ui[accept]}</span></div>
<div class="controls" style="margin-top:16px">
<div class="field"><label for="maxw">{ui[l_size]}</label><select id="maxw">
<option value="0">{ui[o_keep]}</option><option value="2560">2560 px</option>
<option value="1920" selected>1920 px</option><option value="1280">1280 px</option>
<option value="1024">1024 px</option><option value="640">640 px</option></select></div>
<div class="field"><label for="q">{ui[l_quality]} · <span id="qv">80</span></label><input type="range" id="q" min="30" max="96" value="80"></div>
<div class="field"><label for="fmt">{ui[l_format]}</label><select id="fmt">
<option value="image/jpeg">JPEG</option><option value="image/webp">WebP</option></select></div>
</div>
<div class="results">
<div class="result"><strong>{ui[r_before]}</strong><span id="o">—</span></div>
<div class="result"><strong>{ui[r_after]}</strong><span id="n">—</span></div>
<div class="result ok"><strong>{ui[r_saved]}</strong><span id="s">—</span></div>
<div class="result"><strong>{ui[r_dim]}</strong><span id="d">—</span></div>
</div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<a class="button" id="dl" download>{ui[b_download]}</a></div>
<canvas class="stage" id="cv" style="margin-top:18px;display:none"></canvas>
<p class="note">{ui[note]}</p>
"""

IMAGE_COMPRESSOR_JS = r"""
var file=null,img=null,url='';
var $=function(i){return document.getElementById(i);};
function human(b){if(b<1024)return b+' B';
  if(b<1048576)return (b/1024).toFixed(0)+' KB';
  return (b/1048576).toFixed(2)+' MB';}
$('file').addEventListener('change',function(){
  file=$('file').files[0];if(!file)return;
  if(url)URL.revokeObjectURL(url);
  url=URL.createObjectURL(file);img=new Image();
  img.onload=run;img.onerror=function(){alert(L.err_read);};img.src=url;});
$('q').addEventListener('input',function(){$('qv').textContent=$('q').value;run();});
['maxw','fmt'].forEach(function(i){$(i).addEventListener('change',run);});
function run(){
  if(!img||!img.naturalWidth)return;
  var maxw=parseInt($('maxw').value,10)||0;
  var w=img.naturalWidth,h=img.naturalHeight;
  if(maxw&&Math.max(w,h)>maxw){var s=maxw/Math.max(w,h);w=Math.round(w*s);h=Math.round(h*s);}
  var c=$('cv');c.width=w;c.height=h;c.style.display='block';
  var x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,w,h);
  x.imageSmoothingQuality='high';x.drawImage(img,0,0,w,h);
  var type=$('fmt').value,quality=parseInt($('q').value,10)/100;
  c.toBlob(function(b){
    if(!b)return;
    $('o').textContent=human(file.size);
    $('n').textContent=human(b.size);
    var pct=100-(b.size/file.size*100);
    $('s').textContent=(pct>=0?'-':'+')+Math.abs(pct).toFixed(0)+'%';
    $('d').textContent=w+' × '+h+' px';
    var a=$('dl');if(a.href&&a.dataset.blob)URL.revokeObjectURL(a.href);
    a.href=URL.createObjectURL(b);a.dataset.blob='1';
    var base=(file.name||'image').replace(/\.[^.]+$/,'');
    a.download=base+'-'+w+'px.'+(type==='image/webp'?'webp':'jpg');
  },type,quality);}
"""


def spec_image_compressor():
    return {
        "slug": "image-compressor",
        "app_key": "scanto",
        "app_id": "6779977651",
        "app_name": "ScanTo Pro: Offline PDF & OCR",
        "category": "UtilitiesApplication",
        "body": IMAGE_COMPRESSOR_BODY,
        "script": IMAGE_COMPRESSOR_JS,
        "i18n": {
            "en": {
                "q": [("compress image", "D2"), ("resize image", "D2"), ("reduce image file size", "D2")],
                "title": "Compress Image — Free Photo Resizer That Shows the Real File Size",
                "description": "Shrink a photo in your browser: pick a maximum edge, set JPEG or WebP quality, and see the exact before/after file size before you download. Nothing is uploaded.",
                "h1": "Compress an image",
                "eyebrow": "Runs in your browser · exact before/after size",
                "lead": "Most compressors hide what they did to your photo. This one shows the original size, the new size and the resulting pixel dimensions before you download anything.",
                "badges": ["No upload", "JPEG or WebP", "Exact size shown", "No watermark"],
                "features": ["Resize by longest edge", "JPEG and WebP output with a quality slider", "Before/after byte counts and final pixel dimensions", "Runs entirely in the browser"],
                "how": [
                    "Your file is read locally and decoded by the browser — it is never sent anywhere.",
                    "The image is redrawn on a canvas at your chosen maximum edge with high-quality smoothing, on a white background so transparent PNGs stay readable.",
                    "The canvas is re-encoded as JPEG or WebP at the quality you pick, and the resulting blob is measured byte-for-byte.",
                    "The download link points at that blob. Change any control and it re-encodes instantly.",
                ],
                "never": [
                    "It never claims a fixed “90% smaller” number — the saving depends entirely on your image, and the real figure is shown.",
                    "It cannot add detail back. Going down in pixels is permanent in the exported copy; your original file is untouched.",
                    "No upload, no queue, no account, no watermark.",
                ],
                "faq": [
                    ("Is my photo uploaded?", "No. The file is decoded, resized and re-encoded by your own browser. You can put the device in airplane mode after the page loads and it still works."),
                    ("JPEG or WebP — which should I pick?", "WebP is usually 20–35% smaller at the same visual quality and is supported by every current browser and iOS. Pick JPEG when something must accept a .jpg specifically, such as an older upload form."),
                    ("Why is my PNG bigger after compressing?", "PNG stores flat graphics losslessly and can beat JPEG on screenshots or line art. When the result is larger, the page shows a “+” percentage — keep the original in that case."),
                    ("Does it strip location data?", "Re-encoding through a canvas drops EXIF, including GPS. That is a side effect, not a privacy guarantee — if a photo is sensitive, verify the exported copy before sharing it."),
                ],
                "app_heading": "Scanning or sending documents from iPhone often?",
                "card": "Resize and re-encode a photo in your browser with the exact before/after file size shown.",
                "ui": {
                    "h2": "Pick a photo, choose a size, see the real saving",
                    "intro": "JPG, PNG, WebP or HEIC that your browser can decode. Nothing leaves this page.",
                    "accept": "One image at a time",
                    "l_size": "Longest edge", "o_keep": "Keep original",
                    "l_quality": "Quality", "l_format": "Output format",
                    "r_before": "Original", "r_after": "Compressed", "r_saved": "Change", "r_dim": "Dimensions",
                    "b_download": "Download compressed image",
                    "note": "The percentage is measured from the actual encoded bytes, not estimated. Your original file is never modified.",
                    "err_read": "That file could not be decoded by this browser.",
                },
            },
            "ja": {
                "q": [("画像圧縮", "D3"), ("画像 サイズ 変更", "store-hint")],
                "title": "画像圧縮ツール — 圧縮前後のファイルサイズがそのまま見える（無料・ブラウザ完結）",
                "description": "写真の長辺と画質を選ぶだけで、圧縮前と圧縮後の実サイズを表示してからダウンロードできます。アップロードなし、ウォーターマークなし、登録なし。",
                "h1": "画像を圧縮する",
                "eyebrow": "ブラウザ内で処理 · 圧縮前後のサイズを表示",
                "lead": "「どれだけ小さくなったか」を推定値ではなく実バイト数で表示します。元のファイルには一切手を加えません。",
                "badges": ["アップロードなし", "JPEG / WebP", "実サイズ表示", "ウォーターマークなし"],
                "features": ["長辺を指定してリサイズ", "JPEG・WebP と画質スライダー", "圧縮前後のバイト数と最終ピクセル数を表示", "すべてブラウザ内で処理"],
                "how": [
                    "選んだファイルはブラウザ内で読み込まれ、どこにも送信されません。",
                    "指定した長辺に合わせて canvas に描き直します。背景は白で塗るため、透過 PNG も読めるまま残ります。",
                    "選んだ画質で JPEG または WebP に再エンコードし、できたデータのバイト数を実測します。",
                    "ダウンロードリンクはそのデータを指します。設定を変えるとその場で再エンコードします。",
                ],
                "never": [
                    "「90% 削減」のような固定の宣伝文句は出しません。削減率は画像次第なので、実測値だけを表示します。",
                    "失われた解像度は戻せません。書き出したコピーの縮小は元に戻せませんが、元ファイルはそのまま残ります。",
                    "アップロード・順番待ち・アカウント・ウォーターマークはありません。",
                ],
                "faq": [
                    ("写真はサーバーに送られますか？", "いいえ。デコード・リサイズ・再エンコードはすべてご自身のブラウザ内で行われます。ページを開いた後は機内モードでも動作します。"),
                    ("JPEG と WebP はどちらを選べばよいですか？", "同じ見た目なら WebP のほうが 20〜35% ほど小さくなり、現行のブラウザと iOS で表示できます。提出フォームなどが .jpg を要求する場合だけ JPEG を選んでください。"),
                    ("PNG を圧縮したら逆に大きくなりました", "スクリーンショットや線画のような平坦な画像は PNG のほうが小さいことがあります。その場合は結果が「+」で表示されるので、元のファイルを使ってください。"),
                    ("位置情報は消えますか？", "canvas を通して再エンコードすると EXIF（GPS を含む）は失われます。ただしこれは副作用であってプライバシー保証ではありません。重要な写真は書き出した側を必ず確認してください。"),
                ],
                "app_heading": "iPhone で書類をよくスキャン・送信しますか？",
                "card": "写真の長辺と画質を選び、圧縮前後の実サイズを見てから保存できます。",
                "ui": {
                    "h2": "写真を選んで、サイズを決めて、実際の削減量を見る",
                    "intro": "ブラウザがデコードできる JPG・PNG・WebP・HEIC に対応。データはこのページから出ません。",
                    "accept": "一度に 1 枚",
                    "l_size": "長辺", "o_keep": "元のまま",
                    "l_quality": "画質", "l_format": "出力形式",
                    "r_before": "元のサイズ", "r_after": "圧縮後", "r_saved": "変化", "r_dim": "ピクセル数",
                    "b_download": "圧縮した画像を保存",
                    "note": "パーセンテージは実際にエンコードされたバイト数から計算しています（推定ではありません）。元ファイルは変更されません。",
                    "err_read": "このブラウザではこのファイルをデコードできませんでした。",
                },
            },
            "de-DE": {
                "q": [("bilder verkleinern", "D2"), ("foto komprimieren", "store-hint")],
                "title": "Bilder verkleinern — kostenlos im Browser, mit echter Vorher/Nachher-Dateigröße",
                "description": "Foto verkleinern und komprimieren: längste Kante und Qualität wählen, exakte Dateigröße vor dem Download sehen. Ohne Upload, ohne Wasserzeichen, ohne Anmeldung.",
                "h1": "Bild verkleinern",
                "eyebrow": "Läuft im Browser · exakte Größe vorher/nachher",
                "lead": "Die Ersparnis wird an den tatsächlich erzeugten Bytes gemessen, nicht geschätzt. Ihre Originaldatei bleibt unverändert.",
                "badges": ["Kein Upload", "JPEG oder WebP", "Exakte Größe", "Kein Wasserzeichen"],
                "features": ["Verkleinern über die längste Kante", "JPEG- und WebP-Ausgabe mit Qualitätsregler", "Bytes vorher/nachher und finale Pixelmaße", "Läuft vollständig im Browser"],
                "how": [
                    "Die Datei wird lokal gelesen und vom Browser dekodiert — sie wird nirgendwohin gesendet.",
                    "Das Bild wird auf einem Canvas mit der gewählten längsten Kante neu gezeichnet, auf weißem Grund, damit transparente PNGs lesbar bleiben.",
                    "Das Canvas wird als JPEG oder WebP in der gewählten Qualität neu kodiert und byte-genau gemessen.",
                    "Der Download-Link zeigt auf genau dieses Ergebnis und wird bei jeder Änderung sofort neu erzeugt.",
                ],
                "never": [
                    "Es verspricht keine feste Prozentzahl — die Ersparnis hängt vom Bild ab, deshalb steht dort der gemessene Wert.",
                    "Verlorene Auflösung kommt nicht zurück. Die exportierte Kopie ist endgültig verkleinert, das Original bleibt unangetastet.",
                    "Kein Upload, keine Warteschlange, kein Konto, kein Wasserzeichen.",
                ],
                "faq": [
                    ("Wird mein Foto hochgeladen?", "Nein. Dekodieren, Verkleinern und Kodieren übernimmt Ihr eigener Browser. Nach dem Laden der Seite funktioniert das Tool auch im Flugmodus."),
                    ("JPEG oder WebP?", "WebP ist bei gleicher Bildwirkung meist 20–35 % kleiner und wird von allen aktuellen Browsern und von iOS unterstützt. JPEG nur, wenn ein Formular ausdrücklich .jpg verlangt."),
                    ("Warum wird mein PNG größer?", "Flächige Grafiken und Screenshots sind als PNG oft kleiner als als JPEG. In dem Fall zeigt die Seite ein „+“ — dann behalten Sie das Original."),
                    ("Werden GPS-Daten entfernt?", "Beim Neukodieren über das Canvas gehen EXIF-Daten inklusive GPS verloren. Das ist ein Nebeneffekt, keine Datenschutzgarantie — prüfen Sie sensible Bilder nach dem Export selbst."),
                ],
                "app_heading": "Scannen und verschicken Sie oft Dokumente mit dem iPhone?",
                "card": "Foto im Browser verkleinern und komprimieren — mit exakter Dateigröße vorher und nachher.",
                "ui": {
                    "h2": "Foto wählen, Größe festlegen, echte Ersparnis sehen",
                    "intro": "JPG, PNG, WebP oder HEIC, sofern Ihr Browser es dekodieren kann. Nichts verlässt diese Seite.",
                    "accept": "Ein Bild pro Durchgang",
                    "l_size": "Längste Kante", "o_keep": "Original behalten",
                    "l_quality": "Qualität", "l_format": "Ausgabeformat",
                    "r_before": "Original", "r_after": "Komprimiert", "r_saved": "Veränderung", "r_dim": "Maße",
                    "b_download": "Verkleinertes Bild herunterladen",
                    "note": "Die Prozentangabe stammt aus den tatsächlich kodierten Bytes, nicht aus einer Schätzung. Ihre Originaldatei wird nie verändert.",
                    "err_read": "Diese Datei konnte vom Browser nicht dekodiert werden.",
                },
            },
            "zh-Hant": {
                "q": [("圖片壓縮", "D3"), ("照片縮小", "store-hint")],
                "title": "圖片壓縮 — 免費線上壓縮，壓縮前後檔案大小直接顯示",
                "description": "選長邊、選畫質，下載前就看得到壓縮前與壓縮後的實際檔案大小。全程在瀏覽器完成，不上傳、不加浮水印、免註冊。",
                "h1": "壓縮圖片",
                "eyebrow": "瀏覽器內完成 · 顯示實際前後大小",
                "lead": "縮了多少不是估算，是實際編碼後的位元組數。原始檔案不會被更動。",
                "badges": ["不上傳", "JPEG / WebP", "顯示實際大小", "無浮水印"],
                "features": ["依長邊縮放", "JPEG、WebP 輸出與畫質滑桿", "顯示前後位元組數與最終像素尺寸", "完全在瀏覽器內執行"],
                "how": [
                    "檔案在本機讀取並由瀏覽器解碼，不會送到任何伺服器。",
                    "依照你選的長邊在 canvas 上重繪，底色填白，所以透明 PNG 仍然看得清楚。",
                    "用你選的畫質重新編碼成 JPEG 或 WebP，並實際量測產生的位元組數。",
                    "下載連結指向這份資料；改任何設定都會立刻重新編碼。",
                ],
                "never": [
                    "不會宣稱固定的「縮小 90%」——壓縮率完全取決於圖片，所以只顯示實測值。",
                    "無法把失去的細節補回來。輸出的副本縮小後不可逆，但你的原始檔完全不受影響。",
                    "沒有上傳、沒有排隊、不用帳號、沒有浮水印。",
                ],
                "faq": [
                    ("照片會被上傳嗎？", "不會。解碼、縮放、重新編碼都由你自己的瀏覽器完成。頁面載入後開飛航模式也照樣能用。"),
                    ("JPEG 和 WebP 該選哪個？", "同樣觀感下 WebP 通常小 20–35%，現行瀏覽器與 iOS 都支援。只有在表單明確要求 .jpg 時才選 JPEG。"),
                    ("為什麼 PNG 壓完反而變大？", "截圖、線稿這類大片單色的圖，PNG 本來就比 JPEG 小。這時頁面會顯示「+」，請直接留用原檔。"),
                    ("會移除定位資訊嗎？", "經過 canvas 重新編碼後 EXIF（含 GPS）會消失。但這是副作用、不是隱私保證；重要照片請自行檢查輸出的副本。"),
                ],
                "app_heading": "常常用 iPhone 掃描或傳送文件嗎？",
                "card": "在瀏覽器裡縮放與壓縮照片，下載前先看到實際的前後檔案大小。",
                "ui": {
                    "h2": "選一張照片，決定尺寸，看見真正縮了多少",
                    "intro": "支援瀏覽器能解碼的 JPG、PNG、WebP、HEIC。資料不會離開這個頁面。",
                    "accept": "一次一張",
                    "l_size": "長邊", "o_keep": "維持原尺寸",
                    "l_quality": "畫質", "l_format": "輸出格式",
                    "r_before": "原始", "r_after": "壓縮後", "r_saved": "變化", "r_dim": "尺寸",
                    "b_download": "下載壓縮後的圖片",
                    "note": "百分比由實際編碼出的位元組計算，不是估算值。原始檔案永遠不會被修改。",
                    "err_read": "這個瀏覽器無法解碼這個檔案。",
                },
            },
        },
    }


# ------------------------------------------------------------ 2. white noise

NOISE_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="type">{ui[l_type]}</label><select id="type">
<option value="white">{ui[t_white]}</option><option value="pink" selected>{ui[t_pink]}</option>
<option value="brown">{ui[t_brown]}</option></select></div>
<div class="field"><label for="vol">{ui[l_vol]} · <span id="vv">40</span></label><input type="range" id="vol" min="0" max="100" value="40"></div>
<div class="field"><label for="timer">{ui[l_timer]}</label><select id="timer">
<option value="0">{ui[t_off]}</option><option value="15">15 min</option><option value="30">30 min</option>
<option value="45">45 min</option><option value="60">60 min</option><option value="90">90 min</option></select></div>
</div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button" id="play">{ui[b_play]}</button>
<button class="button ghost" id="stop" disabled>{ui[b_stop]}</button></div>
<div class="results">
<div class="result"><strong>{ui[r_state]}</strong><span id="state">—</span></div>
<div class="result"><strong>{ui[r_left]}</strong><span id="left">—</span></div>
<div class="result" style="grid-column:span 2"><strong>{ui[r_profile]}</strong><span id="prof">—</span></div>
</div>
<p class="note">{ui[note]}</p>
"""

NOISE_JS = r"""
var ctx=null,src=null,gain=null,tick=null,endAt=0,fading=false;
var $=function(i){return document.getElementById(i);};
function buffer(kind){
  var len=Math.floor(ctx.sampleRate*10),buf=ctx.createBuffer(1,len,ctx.sampleRate),d=buf.getChannelData(0),i;
  if(kind==='white'){for(i=0;i<len;i++)d[i]=Math.random()*2-1;}
  else if(kind==='pink'){var b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
    for(i=0;i<len;i++){var w=Math.random()*2-1;
      b0=0.99886*b0+w*0.0555179;b1=0.99332*b1+w*0.0750759;b2=0.96900*b2+w*0.1538520;
      b3=0.86650*b3+w*0.3104856;b4=0.55000*b4+w*0.5329522;b5=-0.7616*b5-w*0.0168980;
      d[i]=(b0+b1+b2+b3+b4+b5+b6+w*0.5362)*0.11;b6=w*0.115926;}}
  else{var last=0;for(i=0;i<len;i++){var w2=Math.random()*2-1;last=(last+0.02*w2)/1.02;d[i]=last*3.5;}}
  return buf;}
function level(){return Math.pow(parseInt($('vol').value,10)/100,2)*0.9;}
function mmss(ms){var s=Math.max(0,Math.round(ms/1000));
  return Math.floor(s/60)+':'+('0'+(s%60)).slice(-2);}
function start(){
  var AC=window.AudioContext||window.webkitAudioContext;
  if(!AC){$('state').textContent=L.s_unsupported;return;}
  if(!ctx)ctx=new AC();
  if(ctx.state==='suspended')ctx.resume();
  stop(true);
  var kind=$('type').value;
  src=ctx.createBufferSource();src.buffer=buffer(kind);src.loop=true;
  gain=ctx.createGain();gain.gain.setValueAtTime(0.0001,ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(Math.max(level(),0.0002),ctx.currentTime+1.2);
  src.connect(gain).connect(ctx.destination);src.start();
  fading=false;
  var mins=parseInt($('timer').value,10)||0;
  endAt=mins?Date.now()+mins*60000:0;
  $('play').disabled=true;$('stop').disabled=false;
  $('state').textContent=L.s_playing;
  $('prof').textContent=L['d_'+kind];
  tick=setInterval(update,500);update();}
function update(){
  if(!endAt){$('left').textContent=L.s_nolimit;return;}
  var ms=endAt-Date.now();$('left').textContent=mmss(ms);
  if(ms<=30000&&!fading&&gain){fading=true;
    gain.gain.linearRampToValueAtTime(0.0001,ctx.currentTime+Math.max(ms/1000,1));}
  if(ms<=0)stop();}
function stop(quiet){
  if(tick){clearInterval(tick);tick=null;}
  if(src){try{src.stop();}catch(e){}src.disconnect();src=null;}
  if(gain){gain.disconnect();gain=null;}
  endAt=0;fading=false;
  $('play').disabled=false;$('stop').disabled=true;
  if(!quiet){$('state').textContent=L.s_stopped;$('left').textContent='—';}}
$('play').addEventListener('click',start);
$('stop').addEventListener('click',function(){stop();});
$('vol').addEventListener('input',function(){$('vv').textContent=$('vol').value;
  if(gain&&!fading)gain.gain.setTargetAtTime(level(),ctx.currentTime,0.05);});
$('type').addEventListener('change',function(){$('prof').textContent=L['d_'+$('type').value];
  if(src)start();});
$('timer').addEventListener('change',function(){
  if(!src)return;var m=parseInt($('timer').value,10)||0;
  endAt=m?Date.now()+m*60000:0;fading=false;
  if(gain)gain.gain.setTargetAtTime(level(),ctx.currentTime,0.05);update();});
$('prof').textContent=L.d_pink;
"""

_NOISE_APP = {"app_key": "sereno", "app_id": "6788236641", "app_name": "Sereno",
              "category": "HealthApplication"}


def spec_white_noise():
    spec = dict(_NOISE_APP)
    spec.update({
        "slug": "white-noise-generator",
        "body": NOISE_BODY,
        "script": NOISE_JS,
        "i18n": {
            "en": {
                "q": [("white noise", "D2"), ("brown noise", "D2"), ("what is the difference between white pink and brown noise", "D4")],
                "title": "White, Pink and Brown Noise Generator — Free, No Download, With Sleep Timer",
                "description": "Play real white, pink or brown noise generated in your browser, with a volume control and a sleep timer that fades out instead of cutting off. No account, no download, no ads.",
                "h1": "White, pink and brown noise",
                "eyebrow": "Generated live in your browser · sleep timer",
                "lead": "Three genuinely different noise colours, synthesised on the spot rather than looped from a short clip, with a timer that fades out over the last 30 seconds.",
                "badges": ["White · pink · brown", "Sleep timer with fade-out", "No download", "Works offline after load"],
                "features": ["Live-synthesised white, pink and brown noise", "Volume control on a perceptual curve", "Sleep timer with a 30-second fade-out", "Runs offline once the page has loaded"],
                "how": [
                    "The Web Audio API builds a ten-second noise buffer in memory and loops it, so nothing is streamed or downloaded.",
                    "White noise is uniform random samples. Pink noise runs those samples through a Voss–McCartney filter bank so energy falls about 3 dB per octave. Brown noise integrates them, falling about 6 dB per octave — deeper still.",
                    "The volume slider is squared before it reaches the gain node, so the middle of the slider sounds like the middle to your ears.",
                    "When the timer has 30 seconds left the gain ramps to silence, so you are not woken by an abrupt stop.",
                ],
                "never": [
                    "It makes no health claims. Noise is not a treatment for insomnia, tinnitus or ADHD, and this page will not pretend otherwise.",
                    "It does not record, listen to, or analyse anything — the microphone is never touched.",
                    "Nothing is uploaded and nothing is stored; closing the tab ends it completely.",
                ],
                "faq": [
                    ("What is the actual difference between white, pink and brown noise?", "It is the slope of the energy across frequency. White is flat and sounds hissy. Pink drops about 3 dB per octave and sounds like steady rain. Brown drops about 6 dB per octave and sounds like a low waterfall. Switch between them on this page and the difference is immediate."),
                    ("Will it keep playing when my screen locks?", "On a phone, a browser tab usually stops or is suspended when the screen locks or you switch apps. That is an OS rule, not a setting on this page — an installed app is the only way around it."),
                    ("Does it use data while playing?", "No. The sound is generated on your device. After the page has loaded you can go offline entirely."),
                ],
                "app_heading": "Want noise that keeps playing with the screen off?",
                "card": "Play live-generated white, pink or brown noise with a sleep timer that fades out.",
                "ui": {
                    "h2": "Pick a colour of noise and press play",
                    "intro": "Sound is synthesised on your device — nothing is streamed.",
                    "l_type": "Noise colour", "t_white": "White", "t_pink": "Pink", "t_brown": "Brown",
                    "l_vol": "Volume", "l_timer": "Sleep timer", "t_off": "No timer",
                    "b_play": "▶ Play", "b_stop": "■ Stop",
                    "r_state": "Status", "r_left": "Time left", "r_profile": "What you are hearing",
                    "s_playing": "Playing", "s_stopped": "Stopped", "s_nolimit": "No timer",
                    "s_unsupported": "This browser has no Web Audio support",
                    "d_white": "Flat energy across all frequencies — hissy, like untuned radio.",
                    "d_pink": "About −3 dB per octave — balanced, like steady rain.",
                    "d_brown": "About −6 dB per octave — deep, like a distant waterfall.",
                    "note": "Start at a low volume. Sustained sound above roughly 70 dB through headphones is not safe for overnight use.",
                },
            },
            "ja": {
                "q": [("ホワイトノイズ", "D4"), ("ホワイトノイズ アプリ", "store-hint")],
                "title": "ホワイトノイズ／ピンクノイズ／ブラウンノイズ生成 — 無料・ダウンロード不要・スリープタイマー付き",
                "description": "ブラウザ内で生成する本物のホワイト・ピンク・ブラウンノイズ。音量調整と、最後の30秒でフェードアウトするスリープタイマー付き。登録不要・広告なし。",
                "h1": "ホワイトノイズを再生する",
                "eyebrow": "その場で生成 · スリープタイマー付き",
                "lead": "短いループ音源ではなく、その場で合成した3種類のノイズ。タイマーは最後の30秒でフェードアウトするので、急に止まって目が覚めることがありません。",
                "badges": ["ホワイト・ピンク・ブラウン", "フェードアウト付きタイマー", "ダウンロード不要", "読み込み後はオフライン可"],
                "features": ["ホワイト・ピンク・ブラウンノイズをリアルタイム合成", "聴感に合わせた音量カーブ", "30秒フェードアウト付きスリープタイマー", "ページ読み込み後はオフラインでも動作"],
                "how": [
                    "Web Audio API で 10 秒分のノイズをメモリ上に作り、それをループ再生します。音源をダウンロードしたりストリーミングしたりはしません。",
                    "ホワイトは一様乱数そのもの。ピンクは Voss–McCartney 型のフィルタを通してオクターブあたり約 −3 dB に、ブラウンは積分してオクターブあたり約 −6 dB にしています。",
                    "音量スライダーは2乗してからゲインに渡すため、スライダーの真ん中が耳にも真ん中に聞こえます。",
                    "タイマー残り 30 秒でゲインを 0 に向けて下げるので、突然無音になりません。",
                ],
                "never": [
                    "健康効果はうたいません。ノイズは不眠・耳鳴り・ADHD の治療ではありません。",
                    "録音・集音・解析は一切行いません。マイクには触れません。",
                    "アップロードも保存もしません。タブを閉じればそれで終わりです。",
                ],
                "faq": [
                    ("ホワイト・ピンク・ブラウンの違いは？", "周波数に対するエネルギーの傾きです。ホワイトは平坦で「サー」という高めの音、ピンクは約 −3 dB/oct で雨音のようなバランス、ブラウンは約 −6 dB/oct で遠くの滝のような低音寄りです。このページで切り替えればすぐ分かります。"),
                    ("画面をロックしても鳴り続けますか？", "スマートフォンではブラウザのタブは画面ロックやアプリ切り替えで停止・サスペンドされるのが普通です。これは OS の仕様で、このページの設定では変えられません。インストール型のアプリだけが回避できます。"),
                    ("通信量はかかりますか？", "かかりません。音は端末側で生成しています。ページを読み込んだ後は完全にオフラインで使えます。"),
                ],
                "app_heading": "画面を消したままノイズを鳴らし続けたいですか？",
                "card": "ホワイト／ピンク／ブラウンノイズをその場で生成。フェードアウト付きタイマー。",
                "ui": {
                    "h2": "ノイズの種類を選んで再生",
                    "intro": "音は端末内で合成しています。ストリーミングはしていません。",
                    "l_type": "ノイズの種類", "t_white": "ホワイト", "t_pink": "ピンク", "t_brown": "ブラウン",
                    "l_vol": "音量", "l_timer": "スリープタイマー", "t_off": "タイマーなし",
                    "b_play": "▶ 再生", "b_stop": "■ 停止",
                    "r_state": "状態", "r_left": "残り時間", "r_profile": "いま鳴っている音",
                    "s_playing": "再生中", "s_stopped": "停止", "s_nolimit": "タイマーなし",
                    "s_unsupported": "このブラウザは Web Audio に対応していません",
                    "d_white": "全周波数でほぼ平坦。ラジオの砂嵐のような「サー」という音。",
                    "d_pink": "オクターブあたり約 −3 dB。一定に降る雨のようなバランス。",
                    "d_brown": "オクターブあたり約 −6 dB。遠くの滝のような低い音。",
                    "note": "小さめの音量から始めてください。ヘッドホンでおよそ 70 dB を超える音を一晩流し続けるのは安全ではありません。",
                },
            },
            "ko": {
                "q": [("백색소음", "D3"), ("백색소음 앱", "store-hint")],
                "title": "백색소음·핑크노이즈·브라운노이즈 재생기 — 무료, 설치 없이, 수면 타이머 포함",
                "description": "브라우저에서 직접 생성하는 백색소음, 핑크노이즈, 브라운노이즈. 음량 조절과 마지막 30초에 서서히 줄어드는 수면 타이머 제공. 가입도 광고도 없습니다.",
                "h1": "백색소음 재생",
                "eyebrow": "브라우저에서 실시간 생성 · 수면 타이머",
                "lead": "짧은 음원을 반복 재생하는 것이 아니라 그 자리에서 합성한 세 가지 소음. 타이머는 마지막 30초 동안 서서히 줄어들어 갑자기 끊기지 않습니다.",
                "badges": ["백색·핑크·브라운", "페이드아웃 타이머", "설치 불필요", "로드 후 오프라인 가능"],
                "features": ["백색·핑크·브라운 소음 실시간 합성", "청감에 맞춘 음량 곡선", "30초 페이드아웃 수면 타이머", "페이지 로드 후 오프라인 동작"],
                "how": [
                    "Web Audio API로 10초 분량의 소음 버퍼를 메모리에 만들고 반복 재생합니다. 스트리밍하거나 내려받지 않습니다.",
                    "백색소음은 균일 난수 그대로, 핑크노이즈는 Voss–McCartney 필터를 거쳐 옥타브당 약 −3 dB, 브라운노이즈는 적분하여 약 −6 dB로 떨어집니다.",
                    "음량 슬라이더 값은 제곱해서 게인에 전달하므로 슬라이더 중간이 귀에도 중간으로 들립니다.",
                    "타이머가 30초 남으면 게인을 0으로 낮춥니다. 갑자기 무음이 되지 않습니다.",
                ],
                "never": [
                    "건강 효과를 주장하지 않습니다. 소음은 불면증·이명·ADHD의 치료가 아닙니다.",
                    "녹음하거나 듣거나 분석하지 않습니다. 마이크를 전혀 사용하지 않습니다.",
                    "업로드도 저장도 없습니다. 탭을 닫으면 그것으로 끝입니다.",
                ],
                "faq": [
                    ("백색·핑크·브라운 소음의 실제 차이는?", "주파수에 대한 에너지 기울기입니다. 백색은 평탄해서 '쉬-' 하는 소리, 핑크는 옥타브당 약 −3 dB로 고른 빗소리, 브라운은 약 −6 dB로 멀리서 나는 폭포 소리에 가깝습니다. 이 페이지에서 바꿔 보면 바로 알 수 있습니다."),
                    ("화면을 끄면 계속 재생되나요?", "스마트폰에서는 화면이 꺼지거나 앱을 전환하면 브라우저 탭이 보통 정지·일시중단됩니다. 이는 이 페이지 설정이 아니라 운영체제 규칙이며, 설치형 앱만 우회할 수 있습니다."),
                    ("데이터를 사용하나요?", "아니요. 소리는 기기에서 생성됩니다. 페이지를 한 번 불러온 뒤에는 완전히 오프라인으로 쓸 수 있습니다."),
                ],
                "app_heading": "화면을 끈 상태에서도 계속 재생되길 원하나요?",
                "card": "백색·핑크·브라운 소음을 실시간 생성하고 페이드아웃 타이머로 끕니다.",
                "ui": {
                    "h2": "소음 종류를 고르고 재생",
                    "intro": "소리는 기기 안에서 합성됩니다. 스트리밍하지 않습니다.",
                    "l_type": "소음 종류", "t_white": "백색", "t_pink": "핑크", "t_brown": "브라운",
                    "l_vol": "음량", "l_timer": "수면 타이머", "t_off": "타이머 없음",
                    "b_play": "▶ 재생", "b_stop": "■ 정지",
                    "r_state": "상태", "r_left": "남은 시간", "r_profile": "지금 들리는 소리",
                    "s_playing": "재생 중", "s_stopped": "정지됨", "s_nolimit": "타이머 없음",
                    "s_unsupported": "이 브라우저는 Web Audio를 지원하지 않습니다",
                    "d_white": "모든 주파수가 거의 평탄 — 라디오 잡음 같은 '쉬-' 소리.",
                    "d_pink": "옥타브당 약 −3 dB — 고르게 내리는 빗소리에 가까움.",
                    "d_brown": "옥타브당 약 −6 dB — 멀리서 들리는 폭포처럼 낮은 소리.",
                    "note": "작은 음량으로 시작하세요. 이어폰으로 약 70 dB를 넘는 소리를 밤새 듣는 것은 안전하지 않습니다.",
                },
            },
            "de-DE": {
                "q": [("weisses rauschen", "D2"), ("einschlafgeräusche", "store-hint")],
                "title": "Weißes, rosa und braunes Rauschen — kostenloser Generator mit Einschlaf-Timer",
                "description": "Weißes, rosa oder braunes Rauschen direkt im Browser erzeugt, mit Lautstärkeregler und Einschlaf-Timer, der ausblendet statt abzubrechen. Ohne Konto, ohne Download, ohne Werbung.",
                "h1": "Weißes Rauschen",
                "eyebrow": "Live im Browser erzeugt · Einschlaf-Timer",
                "lead": "Drei wirklich unterschiedliche Rauscharten, live synthetisiert statt aus einem kurzen Clip geloopt — mit einem Timer, der in den letzten 30 Sekunden ausblendet.",
                "badges": ["Weiß · Rosa · Braun", "Timer mit Ausblenden", "Kein Download", "Nach dem Laden offline"],
                "features": ["Weißes, rosa und braunes Rauschen in Echtzeit erzeugt", "Lautstärke auf wahrnehmungsgerechter Kurve", "Einschlaf-Timer mit 30 Sekunden Ausblenden", "Läuft offline, sobald die Seite geladen ist"],
                "how": [
                    "Die Web-Audio-API erzeugt einen zehn Sekunden langen Rauschpuffer im Speicher und wiederholt ihn — es wird nichts gestreamt oder heruntergeladen.",
                    "Weißes Rauschen sind gleichverteilte Zufallswerte. Rosa läuft durch eine Voss-McCartney-Filterbank und fällt rund 3 dB pro Oktave, braunes wird integriert und fällt rund 6 dB pro Oktave.",
                    "Der Lautstärkewert wird quadriert, bevor er an den Gain-Knoten geht — so klingt die Mitte des Reglers auch nach Mitte.",
                    "30 Sekunden vor Ablauf des Timers fährt der Pegel auf null, damit Sie nicht durch ein abruptes Ende geweckt werden.",
                ],
                "never": [
                    "Es werden keine gesundheitlichen Wirkungen behauptet. Rauschen ist keine Behandlung für Schlafstörungen, Tinnitus oder ADHS.",
                    "Es wird nichts aufgenommen, mitgehört oder ausgewertet — das Mikrofon wird nie angefasst.",
                    "Nichts wird hochgeladen oder gespeichert; mit dem Schließen des Tabs ist alles vorbei.",
                ],
                "faq": [
                    ("Worin unterscheiden sich weißes, rosa und braunes Rauschen wirklich?", "In der Energieverteilung über die Frequenz. Weiß ist flach und zischt, rosa fällt etwa 3 dB pro Oktave und klingt wie gleichmäßiger Regen, braun fällt etwa 6 dB pro Oktave und klingt wie ein entfernter Wasserfall. Auf dieser Seite hören Sie den Unterschied sofort."),
                    ("Läuft es weiter, wenn das Display aus ist?", "Auf dem Smartphone wird ein Browser-Tab beim Sperren oder App-Wechsel in der Regel angehalten. Das ist eine Regel des Betriebssystems und lässt sich auf dieser Seite nicht umgehen — nur eine installierte App kann das."),
                    ("Verbraucht das Datenvolumen?", "Nein. Der Klang entsteht auf Ihrem Gerät. Nach dem Laden der Seite können Sie komplett offline gehen."),
                ],
                "app_heading": "Soll das Rauschen auch bei ausgeschaltetem Display weiterlaufen?",
                "card": "Weißes, rosa oder braunes Rauschen live erzeugen — mit ausblendendem Einschlaf-Timer.",
                "ui": {
                    "h2": "Rauschart wählen und abspielen",
                    "intro": "Der Klang wird auf Ihrem Gerät erzeugt — nichts wird gestreamt.",
                    "l_type": "Rauschart", "t_white": "Weiß", "t_pink": "Rosa", "t_brown": "Braun",
                    "l_vol": "Lautstärke", "l_timer": "Einschlaf-Timer", "t_off": "Kein Timer",
                    "b_play": "▶ Abspielen", "b_stop": "■ Stopp",
                    "r_state": "Status", "r_left": "Restzeit", "r_profile": "Was Sie gerade hören",
                    "s_playing": "Läuft", "s_stopped": "Gestoppt", "s_nolimit": "Kein Timer",
                    "s_unsupported": "Dieser Browser unterstützt kein Web Audio",
                    "d_white": "Über alle Frequenzen gleich stark — zischend wie ein untunter Sender.",
                    "d_pink": "Etwa −3 dB pro Oktave — ausgewogen, wie gleichmäßiger Regen.",
                    "d_brown": "Etwa −6 dB pro Oktave — tief, wie ein entfernter Wasserfall.",
                    "note": "Fangen Sie leise an. Dauerbeschallung über etwa 70 dB per Kopfhörer ist für eine ganze Nacht nicht unbedenklich.",
                },
            },
            "zh-Hant": {
                "q": [("白噪音", "D2"), ("助眠 音樂", "store-hint")],
                "title": "白噪音／粉紅噪音／褐色噪音產生器 — 免費、免下載、附睡眠定時",
                "description": "在瀏覽器裡即時合成白噪音、粉紅噪音與褐色噪音，可調音量，睡眠定時結束前 30 秒漸弱而不是突然斷掉。免註冊、無廣告。",
                "h1": "白噪音產生器",
                "eyebrow": "瀏覽器即時合成 · 附睡眠定時",
                "lead": "三種真正不同的噪音，是當場合成的，不是短音檔循環；定時結束前 30 秒會慢慢淡出，不會把你嚇醒。",
                "badges": ["白／粉紅／褐色", "淡出式睡眠定時", "免下載", "載入後可離線"],
                "features": ["即時合成白、粉紅、褐色噪音", "符合聽感的音量曲線", "結束前 30 秒淡出的睡眠定時", "頁面載入後可離線使用"],
                "how": [
                    "用 Web Audio API 在記憶體中產生 10 秒的噪音並循環播放，不下載也不串流任何音檔。",
                    "白噪音是均勻亂數；粉紅噪音經過 Voss–McCartney 濾波器，能量每八度約降 3 dB；褐色噪音再積分一次，每八度約降 6 dB。",
                    "音量滑桿的值會先平方再送進 gain，所以滑桿的中間聽起來也是中間。",
                    "定時剩 30 秒時音量會滑向 0，不會突然靜音。",
                ],
                "never": [
                    "不主張任何健康療效。噪音不是失眠、耳鳴或 ADHD 的治療方式。",
                    "不錄音、不監聽、不分析，完全不會使用麥克風。",
                    "不上傳、不儲存；關掉分頁就結束了。",
                ],
                "faq": [
                    ("白噪音、粉紅噪音、褐色噪音差在哪？", "差在能量隨頻率的斜率。白噪音平坦，聽起來是「嘶」；粉紅噪音每八度約降 3 dB，像穩定的雨聲；褐色噪音每八度約降 6 dB，像遠處的瀑布。在這個頁面切換一下就聽得出來。"),
                    ("鎖定螢幕後還會繼續播嗎？", "手機上瀏覽器分頁在鎖屏或切換 App 時通常會被暫停，這是作業系統的規則，不是這個頁面的設定；只有安裝型 App 能繞過。"),
                    ("會耗網路流量嗎？", "不會。聲音是在你的裝置上產生的，頁面載入後可以完全離線。"),
                ],
                "app_heading": "想在螢幕關閉後也繼續播放嗎？",
                "card": "即時產生白／粉紅／褐色噪音，附會淡出的睡眠定時。",
                "ui": {
                    "h2": "選一種噪音，按下播放",
                    "intro": "聲音在你的裝置上合成，不做串流。",
                    "l_type": "噪音種類", "t_white": "白噪音", "t_pink": "粉紅噪音", "t_brown": "褐色噪音",
                    "l_vol": "音量", "l_timer": "睡眠定時", "t_off": "不定時",
                    "b_play": "▶ 播放", "b_stop": "■ 停止",
                    "r_state": "狀態", "r_left": "剩餘時間", "r_profile": "你現在聽到的",
                    "s_playing": "播放中", "s_stopped": "已停止", "s_nolimit": "不定時",
                    "s_unsupported": "這個瀏覽器不支援 Web Audio",
                    "d_white": "全頻段能量平坦，像沒調到台的收音機「嘶」聲。",
                    "d_pink": "每八度約 −3 dB，像穩定下著的雨。",
                    "d_brown": "每八度約 −6 dB，低沉，像遠處的瀑布。",
                    "note": "請從小音量開始。用耳機整夜播放超過約 70 dB 並不安全。",
                },
            },
        },
    })
    return spec


# ---------------------------------------------------------- 3. sleep cycles

SLEEP_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="mode">{ui[l_mode]}</label><select id="mode">
<option value="wake">{ui[m_wake]}</option><option value="bed">{ui[m_bed]}</option></select></div>
<div class="field"><label for="time">{ui[l_time]}</label><input type="time" id="time" value="07:00"></div>
<div class="field"><label for="fall">{ui[l_fall]}</label><select id="fall">
<option value="0">0 min</option><option value="10">10 min</option><option value="15" selected>15 min</option>
<option value="20">20 min</option><option value="30">30 min</option></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="cyc">{ui[l_cycle]} · <span id="cv">90</span> min</label><input type="range" id="cyc" min="80" max="110" step="5" value="90"></div>
<div class="field" style="align-self:end"><button class="button ghost" id="now">{ui[b_now]}</button></div>
<div class="field"></div>
</div>
<div id="out" class="results"></div>
<p class="note">{ui[note]}</p>
"""

SLEEP_JS = r"""
var $=function(i){return document.getElementById(i);};
function pad(n){return ('0'+n).slice(-2);}
function fmt(mins){mins=((mins%1440)+1440)%1440;return pad(Math.floor(mins/60))+':'+pad(mins%60);}
function render(){
  var mode=$('mode').value,fall=parseInt($('fall').value,10),cyc=parseInt($('cyc').value,10);
  var parts=($('time').value||'07:00').split(':');
  var base=parseInt(parts[0],10)*60+parseInt(parts[1],10);
  var out=$('out');out.innerHTML='';
  for(var n=6;n>=3;n--){
    var total=n*cyc;
    var t=mode==='wake'?base-total-fall:base+fall+total;
    var d=document.createElement('div');d.className='result'+(n===5||n===6?' ok':'');
    var hrs=(total/60);
    d.innerHTML='<strong>'+n+' '+L.cycles+' · '+hrs.toFixed(1)+' '+L.hours+'</strong><span>'+fmt(t)+'</span>';
    out.appendChild(d);}
  var label=document.createElement('div');
  label.className='result';label.style.gridColumn='1/-1';
  label.innerHTML='<strong>'+(mode==='wake'?L.exp_wake:L.exp_bed)+'</strong><span>'+
    L.exp_note.replace('{f}',fall).replace('{c}',cyc)+'</span>';
  out.appendChild(label);}
['mode','time','fall'].forEach(function(i){$(i).addEventListener('change',render);});
$('cyc').addEventListener('input',function(){$('cv').textContent=$('cyc').value;render();});
$('now').addEventListener('click',function(){
  var d=new Date();$('mode').value='bed';
  $('time').value=pad(d.getHours())+':'+pad(d.getMinutes());render();});
render();
"""


def spec_sleep_cycles():
    spec = dict(_NOISE_APP)
    spec.update({
        "slug": "sleep-cycle-calculator",
        "body": SLEEP_BODY,
        "script": SLEEP_JS,
        "i18n": {
            "en": {
                "q": [("what time should i go to bed", "D4"), ("sleep cycle calculator", "D2")],
                "title": "What Time Should I Go to Bed? — Free Sleep Cycle Calculator",
                "description": "Enter the time you must wake up and get bedtimes that land between sleep cycles, with the fall-asleep delay and cycle length you can adjust yourself. Plain arithmetic, no tracking.",
                "h1": "What time should I go to bed?",
                "eyebrow": "Plain arithmetic · nothing measured, nothing stored",
                "lead": "Waking mid-cycle is what makes an eight-hour night feel terrible. Pick your alarm time and this counts whole cycles backwards — with every assumption on screen and editable.",
                "badges": ["Bedtime or wake time", "Adjustable cycle length", "Adjustable fall-asleep delay", "No account"],
                "features": ["Bedtimes counted back from an alarm time", "Wake times counted forward from a bedtime", "Cycle length adjustable 80–110 minutes", "Fall-asleep delay adjustable"],
                "how": [
                    "One cycle defaults to 90 minutes, the usual textbook average. Yours may be anywhere from about 80 to 110 minutes, so the slider changes it.",
                    "In wake mode: bedtime = alarm − (cycles × cycle length) − fall-asleep delay. In bedtime mode the same sum runs forwards.",
                    "Five and six cycles (about 7.5–9 hours) are highlighted because that is where most adult sleep-need estimates sit.",
                    "Everything is computed in the page. No date, no alarm and no habit is saved anywhere.",
                ],
                "never": [
                    "It does not measure your sleep. Nothing here detects a real cycle — it is arithmetic on an average, not a reading from your body.",
                    "It gives no medical advice. Persistent trouble sleeping is a question for a doctor, not a calculator.",
                    "It never claims a “best” bedtime. It shows options; which one you use is your call.",
                ],
                "faq": [
                    ("Is a sleep cycle really 90 minutes?", "90 minutes is the common average, but individual cycles run roughly 80–110 minutes and change through the night. That is exactly why the cycle length here is a slider rather than a fixed number."),
                    ("Why subtract time for falling asleep?", "Because you do not fall asleep the instant you lie down. Sleep-onset latency of 10–20 minutes is typical, so the calculation subtracts it before counting cycles."),
                    ("Should I always aim for six cycles?", "No. Total sleep need varies from person to person. Six cycles is nine hours, which is more than many adults need. Compare the options and see which wake-up actually feels better."),
                ],
                "app_heading": "Trouble settling once you are in bed?",
                "card": "Count whole sleep cycles back from your alarm — cycle length and fall-asleep delay adjustable.",
                "ui": {
                    "h2": "Count backwards from your alarm",
                    "intro": "Change any assumption; the times update immediately.",
                    "l_mode": "I know my…", "m_wake": "Wake-up time", "m_bed": "Bedtime",
                    "l_time": "Time", "l_fall": "Time to fall asleep",
                    "l_cycle": "Cycle length", "b_now": "Going to bed now",
                    "cycles": "cycles", "hours": "h",
                    "exp_wake": "Go to bed at one of these", "exp_bed": "Set the alarm for one of these",
                    "exp_note": "Assumes {f} min to fall asleep and a {c} min cycle — both editable above.",
                    "note": "These are averages, not a measurement of your sleep. Highlighted rows are 5 and 6 cycles, roughly 7.5–9 hours.",
                },
            },
            "ko": {
                "q": [("수면 시간 계산", "D2"), ("수면 앱", "store-hint")],
                "title": "몇 시에 자야 할까 — 무료 수면 주기 계산기",
                "description": "일어나야 하는 시각을 넣으면 수면 주기 사이에서 깨는 취침 시각을 알려줍니다. 잠드는 데 걸리는 시간과 주기 길이는 직접 조절할 수 있습니다. 단순 계산, 추적 없음.",
                "h1": "몇 시에 자야 할까?",
                "eyebrow": "단순 계산 · 측정하지 않고 저장하지 않음",
                "lead": "주기 한가운데서 깨면 8시간을 자도 개운하지 않습니다. 알람 시각을 넣으면 주기 단위로 거꾸로 세어 줍니다. 모든 가정은 화면에 있고 직접 바꿀 수 있습니다.",
                "badges": ["취침·기상 양방향", "주기 길이 조절", "잠드는 시간 조절", "가입 불필요"],
                "features": ["알람 시각에서 거꾸로 계산한 취침 시각", "취침 시각에서 계산한 기상 시각", "주기 길이 80–110분 조절", "잠드는 데 걸리는 시간 조절"],
                "how": [
                    "기본 주기는 교과서 평균인 90분입니다. 사람마다 약 80–110분이므로 슬라이더로 바꿀 수 있습니다.",
                    "기상 모드에서는 취침 시각 = 알람 − (주기 수 × 주기 길이) − 잠드는 시간. 취침 모드에서는 같은 식을 앞으로 계산합니다.",
                    "5주기와 6주기(약 7.5–9시간)를 강조 표시합니다. 대부분의 성인 수면 권장 범위가 여기에 있기 때문입니다.",
                    "모든 계산은 페이지 안에서 이루어지며 어떤 기록도 저장하지 않습니다.",
                ],
                "never": [
                    "수면을 측정하지 않습니다. 실제 주기를 감지하는 것이 아니라 평균값으로 계산할 뿐입니다.",
                    "의학적 조언을 하지 않습니다. 지속적인 수면 문제는 계산기가 아니라 의사와 상의할 일입니다.",
                    "'최적의 취침 시각'이라고 말하지 않습니다. 선택지를 보여줄 뿐 결정은 사용자의 몫입니다.",
                ],
                "faq": [
                    ("수면 주기는 정말 90분인가요?", "90분은 흔히 쓰는 평균이고, 실제로는 약 80–110분 사이이며 밤사이에도 변합니다. 그래서 이 페이지에서는 주기 길이를 고정값이 아니라 슬라이더로 두었습니다."),
                    ("왜 잠드는 시간을 빼나요?", "누웠다고 바로 잠들지는 않기 때문입니다. 보통 10–20분이 걸리므로 주기를 세기 전에 먼저 빼 줍니다."),
                    ("항상 6주기를 목표로 해야 하나요?", "아닙니다. 필요한 총 수면 시간은 사람마다 다릅니다. 6주기는 9시간으로 많은 성인에게는 과합니다. 몇 가지를 비교해 보고 실제로 개운한 쪽을 고르세요."),
                ],
                "app_heading": "누워도 쉽게 잠들지 않나요?",
                "card": "알람 시각에서 수면 주기 단위로 거꾸로 계산 — 주기 길이와 잠드는 시간 조절 가능.",
                "ui": {
                    "h2": "알람 시각에서 거꾸로 세기",
                    "intro": "어떤 값이든 바꾸면 시간이 바로 갱신됩니다.",
                    "l_mode": "내가 아는 것은…", "m_wake": "기상 시각", "m_bed": "취침 시각",
                    "l_time": "시각", "l_fall": "잠드는 데 걸리는 시간",
                    "l_cycle": "주기 길이", "b_now": "지금 자러 갑니다",
                    "cycles": "주기", "hours": "시간",
                    "exp_wake": "이 중 한 시각에 잠자리에", "exp_bed": "이 중 한 시각에 알람을",
                    "exp_note": "잠드는 데 {f}분, 주기 {c}분으로 계산 — 둘 다 위에서 변경할 수 있습니다.",
                    "note": "평균값에 근거한 계산이며 수면 측정이 아닙니다. 강조된 줄은 5·6주기, 약 7.5–9시간입니다.",
                },
            },
            "zh-Hant": {
                "q": [("睡眠計算機", "D3"), ("幾點睡", "store-hint")],
                "title": "幾點睡才好 — 免費睡眠週期計算機",
                "description": "輸入必須起床的時間，算出落在睡眠週期之間的就寢時間；入睡所需時間與週期長度都可以自己調。純算術、不追蹤、不儲存。",
                "h1": "幾點睡才好？",
                "eyebrow": "純算術 · 不量測、不儲存",
                "lead": "在週期中間被叫醒，就算睡滿八小時也還是很累。輸入鬧鐘時間，這裡會以完整週期往回推，而且每個假設都攤開讓你自己改。",
                "badges": ["就寢／起床雙向", "週期長度可調", "入睡時間可調", "免註冊"],
                "features": ["由鬧鐘時間往回推的就寢時間", "由就寢時間往前推的起床時間", "週期長度 80–110 分鐘可調", "入睡所需時間可調"],
                "how": [
                    "預設一個週期 90 分鐘，是常見的平均值。實際上每個人大約落在 80–110 分鐘，所以做成滑桿讓你調整。",
                    "起床模式：就寢時間＝鬧鐘 −（週期數 × 週期長度）− 入睡時間；就寢模式則是同一條式子往前算。",
                    "5 與 6 個週期（約 7.5–9 小時）會標示出來，因為多數成人的睡眠需求落在這個區間。",
                    "全部在頁面內計算，不會儲存任何日期、鬧鐘或習慣資料。",
                ],
                "never": [
                    "不會量測你的睡眠。這裡沒有偵測任何真實週期，只是用平均值做算術。",
                    "不提供醫療建議。長期睡不好請找醫師，而不是計算機。",
                    "不會宣稱哪個是「最佳」就寢時間，只列出選項，決定權在你。",
                ],
                "faq": [
                    ("睡眠週期真的是 90 分鐘嗎？", "90 分鐘是常用的平均值，實際大約在 80–110 分鐘之間，而且一夜之中還會變化。所以這裡把週期長度做成滑桿，而不是寫死。"),
                    ("為什麼要扣掉入睡時間？", "因為躺下不等於睡著。入睡通常要 10–20 分鐘，所以在數週期之前先扣掉。"),
                    ("是不是都該睡滿 6 個週期？", "不是。每個人需要的總時數不同，6 個週期是 9 小時，對很多成人來說偏多。比較幾個選項，挑實際起來最清醒的那個。"),
                ],
                "app_heading": "躺下之後很難靜下來嗎？",
                "card": "從鬧鐘時間往回推完整睡眠週期，週期長度與入睡時間都可調。",
                "ui": {
                    "h2": "從鬧鐘時間往回推",
                    "intro": "任何一個假設改動，時間都會立刻更新。",
                    "l_mode": "我已知的是…", "m_wake": "起床時間", "m_bed": "就寢時間",
                    "l_time": "時間", "l_fall": "入睡需要的時間",
                    "l_cycle": "週期長度", "b_now": "現在就要睡",
                    "cycles": "個週期", "hours": "小時",
                    "exp_wake": "在這幾個時間點上床", "exp_bed": "把鬧鐘設在這幾個時間",
                    "exp_note": "以入睡 {f} 分鐘、週期 {c} 分鐘計算——兩者都可在上方修改。",
                    "note": "這是以平均值做的推算，不是睡眠量測。標示的是 5 與 6 個週期，約 7.5–9 小時。",
                },
            },
        },
    })
    return spec


# --------------------------------------------------------- 4. packing list

PACKING_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="nights">{ui[l_nights]}</label><input type="number" id="nights" value="5" min="1" max="60" inputmode="numeric"></div>
<div class="field"><label for="adults">{ui[l_adults]}</label><input type="number" id="adults" value="2" min="1" max="12" inputmode="numeric"></div>
<div class="field"><label for="kids">{ui[l_kids]}</label><input type="number" id="kids" value="0" min="0" max="12" inputmode="numeric"></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="climate">{ui[l_climate]}</label><select id="climate">
<option value="hot">{ui[c_hot]}</option><option value="mild" selected>{ui[c_mild]}</option>
<option value="cold">{ui[c_cold]}</option></select></div>
<div class="field"><label for="trip">{ui[l_trip]}</label><select id="trip">
<option value="city" selected>{ui[p_city]}</option><option value="beach">{ui[p_beach]}</option>
<option value="hiking">{ui[p_hiking]}</option><option value="business">{ui[p_business]}</option></select></div>
<div class="field"><label>{ui[l_extras]}</label>
<label class="small"><input type="checkbox" id="ointl" style="width:auto" checked> {ui[o_intl]}</label>
<label class="small"><input type="checkbox" id="olaptop" style="width:auto"> {ui[o_laptop]}</label>
<label class="small"><input type="checkbox" id="obaby" style="width:auto"> {ui[o_baby]}</label>
<label class="small"><input type="checkbox" id="odrive" style="width:auto"> {ui[o_drive]}</label></div>
</div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button ghost" id="copy">{ui[b_copy]}</button>
<button class="button ghost" id="txt">{ui[b_txt]}</button>
<button class="button ghost" id="print">{ui[b_print]}</button></div>
<div id="out" style="margin-top:18px"></div>
<p class="note">{ui[note]}</p>
"""

PACKING_JS = r"""
var $=function(i){return document.getElementById(i);};
function ctx(){return {
  n:Math.max(1,parseInt($('nights').value,10)||1),
  a:Math.max(1,parseInt($('adults').value,10)||1),
  k:Math.max(0,parseInt($('kids').value,10)||0),
  cl:$('climate').value,tp:$('trip').value,
  intl:$('ointl').checked,lap:$('olaptop').checked,
  baby:$('obaby').checked,drive:$('odrive').checked};}
var ITEMS=[
['passport','doc',function(c){return c.a+c.k;},function(c){return c.intl;}],
['id','doc',function(){return 1;},function(c){return !c.intl;}],
['tickets','doc',function(){return 1;},function(){return true;}],
['insurance','doc',function(){return 1;},function(c){return c.intl;}],
['wallet','doc',function(){return 1;},function(){return true;}],
['licence','doc',function(){return 1;},function(c){return c.drive;}],
['underwear','cloth',function(c){return Math.min(c.n+1,14);},function(){return true;}],
['socks','cloth',function(c){return Math.min(c.n+1,14);},function(){return true;}],
['tshirt','cloth',function(c){return Math.min(c.n+1,8);},function(){return true;}],
['trousers','cloth',function(c){return Math.ceil(c.n/3)+1;},function(){return true;}],
['sleepwear','cloth',function(){return 1;},function(){return true;}],
['shoes','cloth',function(){return 1;},function(){return true;}],
['sweater','cloth',function(c){return c.cl==='cold'?2:1;},function(c){return c.cl!=='hot';}],
['coat','cloth',function(){return 1;},function(c){return c.cl==='cold';}],
['gloveshat','cloth',function(){return 1;},function(c){return c.cl==='cold';}],
['shorts','cloth',function(){return 2;},function(c){return c.cl==='hot';}],
['swimsuit','cloth',function(){return 1;},function(c){return c.cl==='hot'||c.tp==='beach';}],
['sandals','cloth',function(){return 1;},function(c){return c.cl==='hot'||c.tp==='beach';}],
['raincoat','cloth',function(){return 1;},function(c){return c.cl!=='hot';}],
['shirt','cloth',function(c){return Math.min(c.n,5);},function(c){return c.tp==='business';}],
['blazer','cloth',function(){return 1;},function(c){return c.tp==='business';}],
['dressshoes','cloth',function(){return 1;},function(c){return c.tp==='business';}],
['toothbrush','toilet',function(c){return c.a+c.k;},function(){return true;}],
['toothpaste','toilet',function(){return 1;},function(){return true;}],
['shampoo','toilet',function(){return 1;},function(){return true;}],
['deodorant','toilet',function(){return 1;},function(){return true;}],
['razor','toilet',function(){return 1;},function(){return true;}],
['meds','toilet',function(){return 1;},function(){return true;}],
['sunscreen','toilet',function(){return 1;},function(c){return c.cl==='hot'||c.tp==='beach'||c.tp==='hiking';}],
['glasses','toilet',function(){return 1;},function(){return true;}],
['charger','tech',function(c){return c.a;},function(){return true;}],
['powerbank','tech',function(){return 1;},function(){return true;}],
['adapter','tech',function(){return 1;},function(c){return c.intl;}],
['headphones','tech',function(c){return c.a;},function(){return true;}],
['laptop','tech',function(){return 1;},function(c){return c.lap;}],
['laptopcharger','tech',function(){return 1;},function(c){return c.lap;}],
['kidsnacks','kid',function(){return 1;},function(c){return c.k>0;}],
['kidtoys','kid',function(){return 1;},function(c){return c.k>0;}],
['kidclothes','kid',function(c){return c.k*2;},function(c){return c.k>0;}],
['wipes','kid',function(){return 1;},function(c){return c.k>0||c.baby;}],
['diapers','kid',function(c){return c.n*6;},function(c){return c.baby;}],
['bottles','kid',function(){return 2;},function(c){return c.baby;}],
['carrier','kid',function(){return 1;},function(c){return c.baby;}],
['beachtowel','act',function(c){return c.a+c.k;},function(c){return c.tp==='beach';}],
['snorkel','act',function(){return 1;},function(c){return c.tp==='beach';}],
['boots','act',function(){return 1;},function(c){return c.tp==='hiking';}],
['daypack','act',function(){return 1;},function(c){return c.tp==='hiking';}],
['firstaid','act',function(){return 1;},function(c){return c.tp==='hiking';}],
['bottle','act',function(c){return c.a+c.k;},function(){return true;}],
['book','act',function(){return 1;},function(){return true;}]];
var CATS=['doc','cloth','toilet','tech','kid','act'];
function lines(){
  var c=ctx(),out=[];
  CATS.forEach(function(cat){
    var rows=[];
    ITEMS.forEach(function(it){
      if(it[1]!==cat||!it[3](c))return;
      var n=Math.max(1,Math.round(it[2](c)));
      rows.push({name:L['i_'+it[0]],qty:n});});
    if(rows.length)out.push({cat:L['c_'+cat],rows:rows});});
  return out;}
function render(){
  var groups=lines(),host=$('out');host.innerHTML='';var total=0;
  groups.forEach(function(g){
    var card=document.createElement('article');card.className='card';
    card.style.marginBottom='14px';
    var h=document.createElement('h2');h.textContent=g.cat;h.style.fontSize='20px';card.appendChild(h);
    var ul=document.createElement('ul');ul.style.listStyle='none';ul.style.paddingLeft='0';
    g.rows.forEach(function(r){
      total++;
      var li=document.createElement('li');li.style.margin='6px 0';
      var cb=document.createElement('input');cb.type='checkbox';cb.style.width='auto';
      cb.style.marginRight='8px';li.appendChild(cb);
      li.appendChild(document.createTextNode(r.name+(r.qty>1?'  × '+r.qty:'')));
      ul.appendChild(li);});
    card.appendChild(ul);host.appendChild(card);});
  var p=document.createElement('p');p.className='small';
  p.textContent=L.count.replace('{n}',total);host.appendChild(p);}
function asText(){
  return lines().map(function(g){
    return g.cat+'\n'+g.rows.map(function(r){
      return '[ ] '+r.name+(r.qty>1?' x'+r.qty:'');}).join('\n');}).join('\n\n');}
['nights','adults','kids','climate','trip','ointl','olaptop','obaby','odrive']
  .forEach(function(i){$(i).addEventListener('input',render);$(i).addEventListener('change',render);});
$('copy').addEventListener('click',function(){
  var t=asText();
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(t).then(function(){$('copy').textContent=L.b_copied;
      setTimeout(function(){$('copy').textContent=L.b_copy;},1600);});}
  else{window.prompt(L.b_copy,t);}});
$('txt').addEventListener('click',function(){
  var b=new Blob([asText()],{type:'text/plain;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download='packing-list.txt';a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);},4000);});
$('print').addEventListener('click',function(){window.print();});
render();
"""

_TRIP_APP = {"app_key": "tripbeelite", "app_id": "6791299610", "app_name": "TripBee Lite",
             "category": "TravelApplication"}

_PACK_ITEMS_EN = {
    "c_doc": "Documents & money", "c_cloth": "Clothing", "c_toilet": "Toiletries",
    "c_tech": "Electronics", "c_kid": "Children", "c_act": "Trip-specific",
    "i_passport": "Passport", "i_id": "ID card", "i_tickets": "Tickets / booking confirmations",
    "i_insurance": "Travel insurance details", "i_wallet": "Wallet, cards, some cash",
    "i_licence": "Driving licence", "i_underwear": "Underwear", "i_socks": "Socks",
    "i_tshirt": "Tops / t-shirts", "i_trousers": "Trousers", "i_sleepwear": "Sleepwear",
    "i_shoes": "Comfortable shoes", "i_sweater": "Sweater / fleece", "i_coat": "Warm coat",
    "i_gloveshat": "Hat, gloves, scarf", "i_shorts": "Shorts", "i_swimsuit": "Swimsuit",
    "i_sandals": "Sandals", "i_raincoat": "Rain jacket", "i_shirt": "Dress shirts",
    "i_blazer": "Blazer", "i_dressshoes": "Formal shoes", "i_toothbrush": "Toothbrush",
    "i_toothpaste": "Toothpaste", "i_shampoo": "Shampoo & soap", "i_deodorant": "Deodorant",
    "i_razor": "Razor", "i_meds": "Regular medication + painkillers",
    "i_sunscreen": "Sunscreen", "i_glasses": "Glasses / contact lenses",
    "i_charger": "Phone charger", "i_powerbank": "Power bank", "i_adapter": "Travel plug adapter",
    "i_headphones": "Headphones", "i_laptop": "Laptop / tablet", "i_laptopcharger": "Laptop charger",
    "i_kidsnacks": "Snacks for the journey", "i_kidtoys": "Quiet toys / books",
    "i_kidclothes": "Spare kids clothes", "i_wipes": "Wet wipes", "i_diapers": "Nappies",
    "i_bottles": "Bottles / feeding kit", "i_carrier": "Carrier or stroller",
    "i_beachtowel": "Beach towel", "i_snorkel": "Snorkel / goggles", "i_boots": "Hiking boots",
    "i_daypack": "Daypack", "i_firstaid": "First-aid kit", "i_bottle": "Water bottle",
    "i_book": "Book / downloaded entertainment",
}


def spec_packing_list():
    spec = dict(_TRIP_APP)
    spec.update({
        "slug": "packing-list-generator",
        "body": PACKING_BODY,
        "script": PACKING_JS,
        "i18n": {
            "en": {
                "q": [("packing list", "D2"), ("travel checklist", "store-hint")],
                "title": "Packing List Generator — Free, Quantity-Aware, Printable",
                "description": "Build a packing list from trip length, climate, trip type and who is coming. Quantities are calculated, not guessed, and you can copy, print or download it. No sign-up.",
                "h1": "Packing list generator",
                "eyebrow": "Quantities calculated from your trip · printable",
                "lead": "Generic packing lists tell you to bring socks. This one works out how many, from the number of nights, the climate and who is travelling.",
                "badges": ["Quantities calculated", "Kids and baby items", "Copy · print · .txt", "No sign-up"],
                "features": ["Quantities derived from nights and travellers", "Climate and trip-type specific sections", "Children and baby add-ons", "Copy, print or download as plain text"],
                "how": [
                    "Every item carries a rule. Underwear and socks are nights + 1 (capped at 14), tops are nights + 1 up to eight, trousers are one per three nights plus one.",
                    "Climate opens or closes whole groups: a warm coat, hat and gloves only appear for cold, shorts and sandals only for hot, a rain jacket for anything that is not hot.",
                    "Trip type adds its own block — dress shirts and formal shoes for business, boots and a daypack for hiking, towels and snorkel for a beach trip.",
                    "Children add snacks, spare clothes and wipes; the baby option adds nappies at six per night plus feeding kit.",
                ],
                "never": [
                    "It is not an airline rule checker. Liquid limits, battery rules and baggage weights change by carrier and route — check your airline.",
                    "It does not save your trip. Reload the page and it is gone; nothing is stored or sent.",
                    "It cannot know your personal must-haves. Treat the output as a starting list, then add yours.",
                ],
                "faq": [
                    ("How are the quantities worked out?", "From the numbers you enter. Underwear and socks are one per night plus a spare, capped at fourteen; tops are one per night up to eight; trousers are one per three nights plus one. Every rule is listed under “How it works”."),
                    ("Can I use it for a family trip?", "Yes. Adults and children are separate inputs, so per-person items like toothbrushes and water bottles scale, and the children’s section only appears when there is at least one child."),
                    ("Does it save my list?", "No. It is generated fresh each time. Use copy, download .txt or print if you want to keep it."),
                ],
                "app_heading": "Want the list to survive the trip and the next one?",
                "card": "Generate a packing list with calculated quantities from nights, climate, trip type and travellers.",
                "ui": dict(_PACK_ITEMS_EN, **{
                    "h2": "Describe the trip, get the list",
                    "intro": "Quantities update as you type. Nothing is stored.",
                    "l_nights": "Nights", "l_adults": "Adults", "l_kids": "Children",
                    "l_climate": "Climate", "c_hot": "Hot", "c_mild": "Mild", "c_cold": "Cold",
                    "l_trip": "Trip type", "p_city": "City / general", "p_beach": "Beach",
                    "p_hiking": "Hiking / outdoors", "p_business": "Business",
                    "l_extras": "Extras", "o_intl": "Abroad", "o_laptop": "Taking a laptop",
                    "o_baby": "Travelling with a baby", "o_drive": "Driving",
                    "b_copy": "Copy list", "b_copied": "Copied", "b_txt": "Download .txt",
                    "b_print": "Print", "count": "{n} items in this list.",
                    "note": "Rules are visible under “How it works” — if one does not fit how you pack, override it.",
                }),
            },
            "ja": {
                "q": [("持ち物リスト", "D4"), ("持ち物リスト アプリ", "store-hint")],
                "title": "旅行の持ち物リスト作成 — 泊数から必要数まで自動計算・印刷可・無料",
                "description": "泊数・気候・旅行の種類・同行者を入れるだけで、枚数まで計算した持ち物リストを作ります。コピー・印刷・テキスト保存ができ、登録は不要です。",
                "h1": "持ち物リストを作る",
                "eyebrow": "泊数から必要数を計算 · 印刷対応",
                "lead": "「靴下」とだけ書いてあるリストは役に立ちません。ここでは泊数・気候・同行者から必要な枚数まで出します。",
                "badges": ["枚数まで自動計算", "子ども・赤ちゃん対応", "コピー・印刷・.txt", "登録不要"],
                "features": ["泊数と人数から必要数を算出", "気候・旅行タイプ別の項目", "子ども／赤ちゃん用の追加項目", "コピー・印刷・テキスト保存"],
                "how": [
                    "項目ごとに計算ルールがあります。下着と靴下は「泊数＋1」（上限14）、トップスは「泊数＋1」（上限8）、ボトムスは「3泊につき1本＋1」です。",
                    "気候でグループごと切り替わります。厚手のコート・帽子・手袋は「寒い」のときだけ、短パンとサンダルは「暑い」のときだけ、レインウェアは暑い以外で表示されます。",
                    "旅行の種類ごとに固有のブロックが増えます。ビジネスならワイシャツと革靴、ハイキングなら登山靴とデイパック、ビーチならタオルとシュノーケルです。",
                    "子どもがいるとおやつ・着替え・ウェットティッシュが、赤ちゃん指定ではおむつ（1泊6枚）と授乳用品が加わります。",
                ],
                "never": [
                    "航空会社のルールチェッカーではありません。液体・バッテリー・重量の規定は航空会社と路線で異なります。必ず各社の案内を確認してください。",
                    "旅程を保存しません。再読み込みすれば消えますし、送信も保存もしていません。",
                    "あなた個人の必需品までは分かりません。出力はあくまで出発点として使ってください。",
                ],
                "faq": [
                    ("枚数はどう決まっていますか？", "入力した数値から計算しています。下着・靴下は泊数＋1（最大14）、トップスは泊数＋1（最大8）、ボトムスは3泊につき1本＋1です。すべてのルールは「しくみ」に書いてあります。"),
                    ("家族旅行にも使えますか？", "使えます。大人と子どもを別々に入力するので、歯ブラシや水筒のような1人1つの項目は人数分に増え、子ども用の項目は子どもが1人以上いるときだけ出ます。"),
                    ("リストは保存されますか？", "保存されません。毎回その場で作り直しています。残したい場合はコピー・.txt 保存・印刷を使ってください。"),
                ],
                "app_heading": "そのリストを次の旅行でも使いたいですか？",
                "card": "泊数・気候・旅行タイプ・同行者から、枚数まで計算した持ち物リストを作ります。",
                "ui": {
                    "c_doc": "書類・お金", "c_cloth": "衣類", "c_toilet": "洗面・衛生",
                    "c_tech": "電子機器", "c_kid": "子ども", "c_act": "旅行タイプ別",
                    "i_passport": "パスポート", "i_id": "身分証", "i_tickets": "チケット・予約確認",
                    "i_insurance": "海外旅行保険の控え", "i_wallet": "財布・カード・現金",
                    "i_licence": "運転免許証", "i_underwear": "下着", "i_socks": "靴下",
                    "i_tshirt": "トップス", "i_trousers": "ボトムス", "i_sleepwear": "寝間着",
                    "i_shoes": "歩きやすい靴", "i_sweater": "セーター・フリース", "i_coat": "厚手のコート",
                    "i_gloveshat": "帽子・手袋・マフラー", "i_shorts": "短パン", "i_swimsuit": "水着",
                    "i_sandals": "サンダル", "i_raincoat": "レインウェア", "i_shirt": "ワイシャツ",
                    "i_blazer": "ジャケット", "i_dressshoes": "革靴", "i_toothbrush": "歯ブラシ",
                    "i_toothpaste": "歯みがき粉", "i_shampoo": "シャンプー・石けん", "i_deodorant": "制汗剤",
                    "i_razor": "ひげそり", "i_meds": "常備薬・痛み止め", "i_sunscreen": "日焼け止め",
                    "i_glasses": "メガネ・コンタクト", "i_charger": "スマホの充電器",
                    "i_powerbank": "モバイルバッテリー", "i_adapter": "変換プラグ", "i_headphones": "イヤホン",
                    "i_laptop": "ノートPC・タブレット", "i_laptopcharger": "PCの充電器",
                    "i_kidsnacks": "移動中のおやつ", "i_kidtoys": "静かに遊べるおもちゃ・絵本",
                    "i_kidclothes": "子どもの着替え", "i_wipes": "ウェットティッシュ", "i_diapers": "おむつ",
                    "i_bottles": "哺乳瓶・授乳用品", "i_carrier": "抱っこひも・ベビーカー",
                    "i_beachtowel": "ビーチタオル", "i_snorkel": "シュノーケル・ゴーグル",
                    "i_boots": "登山靴", "i_daypack": "デイパック", "i_firstaid": "救急セット",
                    "i_bottle": "水筒", "i_book": "本・ダウンロード済みの動画",
                    "h2": "旅行の条件を入れるとリストができます",
                    "intro": "入力すると必要数がその場で変わります。保存はしません。",
                    "l_nights": "泊数", "l_adults": "大人", "l_kids": "子ども",
                    "l_climate": "気候", "c_hot": "暑い", "c_mild": "ふつう", "c_cold": "寒い",
                    "l_trip": "旅行の種類", "p_city": "街歩き・一般", "p_beach": "ビーチ",
                    "p_hiking": "ハイキング・アウトドア", "p_business": "出張",
                    "l_extras": "追加条件", "o_intl": "海外", "o_laptop": "ノートPCを持参",
                    "o_baby": "赤ちゃん連れ", "o_drive": "運転する",
                    "b_copy": "リストをコピー", "b_copied": "コピーしました", "b_txt": ".txt で保存",
                    "b_print": "印刷", "count": "この条件では {n} 項目です。",
                    "note": "計算ルールは「しくみ」に全部書いてあります。合わない場合は手元で足し引きしてください。",
                },
            },
            "de-DE": {
                "q": [("packliste urlaub", "D2"), ("packliste app", "store-hint")],
                "title": "Packliste erstellen — kostenlos, mit berechneten Mengen, druckbar",
                "description": "Packliste aus Reisedauer, Klima, Reiseart und Mitreisenden erzeugen. Die Mengen werden berechnet, nicht geraten — kopieren, drucken oder als .txt speichern. Ohne Anmeldung.",
                "h1": "Packliste erstellen",
                "eyebrow": "Mengen aus Ihrer Reise berechnet · druckbar",
                "lead": "Allgemeine Packlisten sagen „Socken“. Diese rechnet aus, wie viele — aus Nächten, Klima und Mitreisenden.",
                "badges": ["Mengen berechnet", "Kinder und Baby", "Kopieren · Drucken · .txt", "Ohne Anmeldung"],
                "features": ["Mengen aus Nächten und Personenzahl", "Abschnitte nach Klima und Reiseart", "Zusätze für Kinder und Babys", "Kopieren, drucken oder als Text speichern"],
                "how": [
                    "Jeder Eintrag hat eine Regel: Unterwäsche und Socken sind Nächte + 1 (max. 14), Oberteile Nächte + 1 (max. 8), Hosen eine je drei Nächte plus eine.",
                    "Das Klima schaltet ganze Gruppen: Wintermantel, Mütze und Handschuhe nur bei kalt, Shorts und Sandalen nur bei heiß, Regenjacke bei allem außer heiß.",
                    "Die Reiseart ergänzt eigene Blöcke — Hemden und Anzugschuhe geschäftlich, Wanderschuhe und Tagesrucksack beim Wandern, Handtuch und Schnorchel am Strand.",
                    "Kinder ergänzen Snacks, Wechselkleidung und Feuchttücher; die Baby-Option fügt sechs Windeln pro Nacht und Fläschchen hinzu.",
                ],
                "never": [
                    "Es prüft keine Airline-Regeln. Flüssigkeits-, Akku- und Gewichtsgrenzen unterscheiden sich je Fluggesellschaft und Strecke.",
                    "Es speichert Ihre Reise nicht. Nach dem Neuladen ist die Liste weg; nichts wird gesendet oder abgelegt.",
                    "Es kennt Ihre persönlichen Unverzichtbaren nicht. Nehmen Sie die Ausgabe als Ausgangsliste.",
                ],
                "faq": [
                    ("Wie kommen die Mengen zustande?", "Aus Ihren Eingaben. Unterwäsche und Socken: Nächte + 1, höchstens 14. Oberteile: Nächte + 1, höchstens 8. Hosen: eine je drei Nächte plus eine. Alle Regeln stehen unter „So funktioniert es“."),
                    ("Taugt das für eine Familienreise?", "Ja. Erwachsene und Kinder sind getrennte Felder, Pro-Kopf-Dinge wie Zahnbürsten und Trinkflaschen skalieren mit, und der Kinderabschnitt erscheint nur, wenn mindestens ein Kind mitreist."),
                    ("Wird die Liste gespeichert?", "Nein, sie wird jedes Mal neu erzeugt. Zum Behalten kopieren, als .txt herunterladen oder drucken."),
                ],
                "app_heading": "Soll die Liste die Reise überdauern?",
                "card": "Packliste mit berechneten Mengen aus Nächten, Klima, Reiseart und Mitreisenden.",
                "ui": {
                    "c_doc": "Dokumente & Geld", "c_cloth": "Kleidung", "c_toilet": "Kulturbeutel",
                    "c_tech": "Elektronik", "c_kid": "Kinder", "c_act": "Reisespezifisch",
                    "i_passport": "Reisepass", "i_id": "Personalausweis", "i_tickets": "Tickets / Buchungsbestätigungen",
                    "i_insurance": "Reiseversicherung (Unterlagen)", "i_wallet": "Geldbörse, Karten, Bargeld",
                    "i_licence": "Führerschein", "i_underwear": "Unterwäsche", "i_socks": "Socken",
                    "i_tshirt": "Oberteile / T-Shirts", "i_trousers": "Hosen", "i_sleepwear": "Schlafsachen",
                    "i_shoes": "Bequeme Schuhe", "i_sweater": "Pullover / Fleece", "i_coat": "Warmer Mantel",
                    "i_gloveshat": "Mütze, Handschuhe, Schal", "i_shorts": "Shorts", "i_swimsuit": "Badesachen",
                    "i_sandals": "Sandalen", "i_raincoat": "Regenjacke", "i_shirt": "Hemden",
                    "i_blazer": "Sakko", "i_dressshoes": "Anzugschuhe", "i_toothbrush": "Zahnbürste",
                    "i_toothpaste": "Zahnpasta", "i_shampoo": "Shampoo & Seife", "i_deodorant": "Deo",
                    "i_razor": "Rasierer", "i_meds": "Dauermedikamente + Schmerzmittel",
                    "i_sunscreen": "Sonnencreme", "i_glasses": "Brille / Kontaktlinsen",
                    "i_charger": "Handy-Ladegerät", "i_powerbank": "Powerbank", "i_adapter": "Reiseadapter",
                    "i_headphones": "Kopfhörer", "i_laptop": "Laptop / Tablet", "i_laptopcharger": "Laptop-Netzteil",
                    "i_kidsnacks": "Snacks für unterwegs", "i_kidtoys": "Leise Spielsachen / Bücher",
                    "i_kidclothes": "Wechselkleidung für Kinder", "i_wipes": "Feuchttücher", "i_diapers": "Windeln",
                    "i_bottles": "Fläschchen / Fütterzubehör", "i_carrier": "Trage oder Kinderwagen",
                    "i_beachtowel": "Strandtuch", "i_snorkel": "Schnorchel / Taucherbrille",
                    "i_boots": "Wanderschuhe", "i_daypack": "Tagesrucksack", "i_firstaid": "Erste-Hilfe-Set",
                    "i_bottle": "Trinkflasche", "i_book": "Buch / heruntergeladene Unterhaltung",
                    "h2": "Reise beschreiben, Liste bekommen",
                    "intro": "Die Mengen aktualisieren sich beim Tippen. Nichts wird gespeichert.",
                    "l_nights": "Nächte", "l_adults": "Erwachsene", "l_kids": "Kinder",
                    "l_climate": "Klima", "c_hot": "Heiß", "c_mild": "Gemäßigt", "c_cold": "Kalt",
                    "l_trip": "Reiseart", "p_city": "Städtereise / allgemein", "p_beach": "Strand",
                    "p_hiking": "Wandern / Outdoor", "p_business": "Geschäftlich",
                    "l_extras": "Zusätze", "o_intl": "Ins Ausland", "o_laptop": "Laptop dabei",
                    "o_baby": "Mit Baby", "o_drive": "Selbst fahren",
                    "b_copy": "Liste kopieren", "b_copied": "Kopiert", "b_txt": ".txt herunterladen",
                    "b_print": "Drucken", "count": "{n} Einträge in dieser Liste.",
                    "note": "Alle Regeln stehen unter „So funktioniert es“ — passt eine nicht zu Ihnen, überschreiben Sie sie.",
                },
            },
            "zh-Hant": {
                "q": [("行李清單", "D3"), ("旅行 打包", "store-hint")],
                "title": "行李清單產生器 — 依天數自動算數量，可列印，免費",
                "description": "輸入天數、氣候、旅行類型與同行人數，直接產生連數量都算好的行李清單，可複製、列印或存成 .txt，免註冊。",
                "h1": "行李清單產生器",
                "eyebrow": "數量依行程計算 · 可列印",
                "lead": "一般清單只會寫「襪子」。這裡會依住幾晚、什麼氣候、幾個人，把數量一起算出來。",
                "badges": ["數量自動計算", "含兒童與嬰兒", "複製／列印／.txt", "免註冊"],
                "features": ["依晚數與人數推算數量", "依氣候與旅行類型調整項目", "兒童與嬰兒專屬項目", "可複製、列印或下載純文字"],
                "how": [
                    "每個項目都有規則：內衣與襪子是「晚數＋1」（上限 14），上衣是「晚數＋1」（上限 8），褲子是「每三晚一件再加一件」。",
                    "氣候會整組開關：厚外套、帽子手套只在「冷」出現，短褲涼鞋只在「熱」出現，雨衣則在非炎熱時出現。",
                    "旅行類型各有專屬區塊：出差是襯衫與皮鞋，健行是登山鞋與小背包，海邊是浴巾與浮潛用具。",
                    "有小孩會加上點心、備用衣物與濕紙巾；勾選嬰兒則以「每晚 6 片」計算尿布並加上餵食用品。",
                ],
                "never": [
                    "這不是航空規定檢查工具。液體、電池與行李重量規定各航空公司與航線都不同，請以航空公司公告為準。",
                    "不會儲存你的行程。重新整理就沒了，也不會上傳。",
                    "無法知道你個人的必需品，請把結果當成起點再自行增補。",
                ],
                "faq": [
                    ("數量是怎麼算的？", "都是從你輸入的數字推出來的：內衣襪子是晚數＋1（上限 14），上衣是晚數＋1（上限 8），褲子是每三晚一件再加一件。所有規則都寫在「運作方式」裡。"),
                    ("家庭旅行可以用嗎？", "可以。大人與小孩是分開的欄位，牙刷、水壺這類每人一份的項目會照人數增加，兒童區塊只有在至少一位小孩時才出現。"),
                    ("清單會被保存嗎？", "不會，每次都是重新產生的。想留著請用複製、下載 .txt 或列印。"),
                ],
                "app_heading": "想讓這份清單留到下次旅行嗎？",
                "card": "依天數、氣候、旅行類型與人數，產生連數量都算好的行李清單。",
                "ui": {
                    "c_doc": "證件與金錢", "c_cloth": "衣物", "c_toilet": "盥洗用品",
                    "c_tech": "電子產品", "c_kid": "兒童", "c_act": "行程專屬",
                    "i_passport": "護照", "i_id": "身分證", "i_tickets": "機票／訂房確認",
                    "i_insurance": "旅平險資料", "i_wallet": "錢包、卡片、少量現金",
                    "i_licence": "駕照", "i_underwear": "內衣褲", "i_socks": "襪子",
                    "i_tshirt": "上衣", "i_trousers": "褲子／裙子", "i_sleepwear": "睡衣",
                    "i_shoes": "好走的鞋", "i_sweater": "毛衣／刷毛外套", "i_coat": "厚外套",
                    "i_gloveshat": "帽子、手套、圍巾", "i_shorts": "短褲", "i_swimsuit": "泳衣",
                    "i_sandals": "涼鞋", "i_raincoat": "雨衣", "i_shirt": "襯衫",
                    "i_blazer": "西裝外套", "i_dressshoes": "皮鞋", "i_toothbrush": "牙刷",
                    "i_toothpaste": "牙膏", "i_shampoo": "洗髮精與沐浴用品", "i_deodorant": "體香劑",
                    "i_razor": "刮鬍刀", "i_meds": "常備藥與止痛藥", "i_sunscreen": "防曬乳",
                    "i_glasses": "眼鏡／隱形眼鏡", "i_charger": "手機充電器",
                    "i_powerbank": "行動電源", "i_adapter": "轉接插頭", "i_headphones": "耳機",
                    "i_laptop": "筆電／平板", "i_laptopcharger": "筆電充電器",
                    "i_kidsnacks": "路上的點心", "i_kidtoys": "安靜的玩具／童書",
                    "i_kidclothes": "小孩替換衣物", "i_wipes": "濕紙巾", "i_diapers": "尿布",
                    "i_bottles": "奶瓶／餵食用品", "i_carrier": "揹巾或推車",
                    "i_beachtowel": "海灘巾", "i_snorkel": "浮潛用具／泳鏡",
                    "i_boots": "登山鞋", "i_daypack": "小背包", "i_firstaid": "急救包",
                    "i_bottle": "水壺", "i_book": "書／已下載的影音",
                    "h2": "描述行程，立刻產生清單",
                    "intro": "邊輸入邊更新數量，不會保存任何資料。",
                    "l_nights": "住幾晚", "l_adults": "大人", "l_kids": "小孩",
                    "l_climate": "氣候", "c_hot": "熱", "c_mild": "溫和", "c_cold": "冷",
                    "l_trip": "旅行類型", "p_city": "城市／一般", "p_beach": "海邊",
                    "p_hiking": "健行／戶外", "p_business": "出差",
                    "l_extras": "其他條件", "o_intl": "出國", "o_laptop": "會帶筆電",
                    "o_baby": "帶嬰兒", "o_drive": "會自己開車",
                    "b_copy": "複製清單", "b_copied": "已複製", "b_txt": "下載 .txt",
                    "b_print": "列印", "count": "這份清單共 {n} 項。",
                    "note": "所有規則都寫在「運作方式」；不符合你的習慣就自行增減。",
                },
            },
        },
    })
    return spec


TOOL_BUILDERS = [
    passport_checker,
    currency_converter,
    paycheck_budget,
    resume_maker,
    jpg_to_pdf,
    mosaic_blur,
]

# ------------------------------------------------------- 5. travel budget

TRAVEL_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="days">{ui[l_days]}</label><input type="number" id="days" value="7" min="1" max="365" inputmode="numeric"></div>
<div class="field"><label for="people">{ui[l_people]}</label><input type="number" id="people" value="2" min="1" max="20" inputmode="numeric"></div>
<div class="field"><label for="home">{ui[l_home]}</label><select id="home"></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="dest">{ui[l_dest]}</label><select id="dest"></select></div>
<div class="field"><label for="flights">{ui[l_flights]}</label><input type="number" id="flights" value="600" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="onceoff">{ui[l_onceoff]}</label><input type="number" id="onceoff" value="120" min="0" step="any" inputmode="decimal"></div>
</div>
<h2 style="font-size:20px;margin:22px 0 0">{ui[h_daily]}</h2>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="stay">{ui[l_stay]}</label><input type="number" id="stay" value="90" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="food">{ui[l_food]}</label><input type="number" id="food" value="45" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="local">{ui[l_local]}</label><input type="number" id="local" value="15" min="0" step="any" inputmode="decimal"></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="fun">{ui[l_fun]}</label><input type="number" id="fun" value="25" min="0" step="any" inputmode="decimal"></div>
<div class="field"><label for="buffer">{ui[l_buffer]} · <span id="bv">10</span>%</label><input type="range" id="buffer" min="0" max="30" value="10"></div>
<div class="field"></div>
</div>
<div class="results">
<div class="result"><strong>{ui[r_daily]}</strong><span id="rdaily">—</span></div>
<div class="result"><strong>{ui[r_onsite]}</strong><span id="ronsite">—</span></div>
<div class="result"><strong>{ui[r_fixed]}</strong><span id="rfixed">—</span></div>
<div class="result ok"><strong>{ui[r_total]}</strong><span id="rtotal">—</span></div>
<div class="result" style="grid-column:span 2"><strong>{ui[r_person]}</strong><span id="rperson">—</span></div>
<div class="result" style="grid-column:span 2"><strong>{ui[r_rate]}</strong><span id="rrate">—</span></div>
</div>
<p class="note" id="srcnote">{ui[note]}</p>
"""

TRAVEL_JS_TMPL = r"""
var SNAP=%s;
var rates=null,asof='',srclabel='';
var $=function(i){return document.getElementById(i);};
function fill(){var codes=Object.keys(rates).sort();
  [['home','EUR'],['dest','JPY']].forEach(function(p){
    var sel=$(p[0]),keep=sel.value;sel.innerHTML='';
    codes.forEach(function(c){var o=document.createElement('option');
      o.value=c;o.textContent=c;sel.appendChild(o);});
    sel.value=keep&&codes.indexOf(keep)>=0?keep:p[1];});}
function money(v,c){return v.toLocaleString(undefined,{maximumFractionDigits:v>=100?0:2})+' '+c;}
function calc(){
  if(!rates)return;
  var d=Math.max(1,parseInt($('days').value,10)||1);
  var p=Math.max(1,parseInt($('people').value,10)||1);
  var home=$('home').value,dest=$('dest').value;
  var num=function(id){return Math.max(0,parseFloat($(id).value)||0);};
  var perDay=num('stay')+num('food')+num('local')+num('fun');
  var buf=parseInt($('buffer').value,10)||0;
  var onsiteDest=perDay*d*(1+buf/100);
  var r=rates[home]/rates[dest];
  var onsiteHome=onsiteDest*r;
  var fixed=num('flights')+num('onceoff');
  var total=onsiteHome+fixed;
  $('rdaily').textContent=money(perDay,dest);
  $('ronsite').textContent=money(onsiteDest,dest)+' ≈ '+money(onsiteHome,home);
  $('rfixed').textContent=money(fixed,home);
  $('rtotal').textContent=money(total,home);
  $('rperson').textContent=money(total/p,home)+' · '+money(total/p/d,home)+' '+L.per_day;
  $('rrate').textContent='1 '+dest+' = '+(r).toLocaleString(undefined,{maximumFractionDigits:6})+' '+home
    +' · '+asof+' · '+srclabel;}
['days','people','stay','food','local','fun','flights','onceoff']
  .forEach(function(i){$(i).addEventListener('input',calc);});
['home','dest'].forEach(function(i){$(i).addEventListener('change',calc);});
$('buffer').addEventListener('input',function(){$('bv').textContent=$('buffer').value;calc();});
function useData(base,d,date,label){rates={};rates[base]=1;
  for(var k in d)rates[k]=d[k];asof=date;srclabel=label;fill();calc();}
useData(SNAP.base,SNAP.rates,SNAP.date,L.src_snapshot);
fetch('https://api.frankfurter.dev/v1/latest?base=USD').then(function(r){return r.json();})
  .then(function(d){if(d&&d.rates)useData(d.base,d.rates,d.date,L.src_live);})
  .catch(function(){});
"""

_GMONEY_APP = {"app_key": "gmoneylite", "app_id": "6793436548", "app_name": "G+Money Lite",
               "category": "TravelApplication"}


def spec_travel_budget():
    snapshot = json.loads(RATES_CACHE.read_text(encoding="utf-8"))
    spec = dict(_GMONEY_APP)
    spec.update({
        "slug": "travel-budget-calculator",
        "body": TRAVEL_BODY,
        "script": TRAVEL_JS_TMPL % jsl(snapshot),
        "i18n": {
            "en": {
                "q": [("travel budget calculator", "D2"), ("travel expense calculator", "store-hint"), ("exchange rate", "store-hint")],
                "title": "Travel Budget Calculator — Two Currencies, ECB Reference Rates, No Sign-Up",
                "description": "Work out what a trip actually costs: daily spend in the destination currency, fixed costs at home, converted on dated ECB reference rates. Per person and per day included.",
                "h1": "Travel budget calculator",
                "eyebrow": "Two currencies · dated ECB reference rates",
                "lead": "Daily costs happen in the destination currency, flights and insurance in yours. This keeps the two apart and converts only at the end, on a rate whose date is on screen.",
                "badges": ["Two currencies", "Dated ECB rates", "Per person, per day", "No account"],
                "features": ["Daily spend entered in the destination currency", "Fixed costs entered in your home currency", "Adjustable contingency buffer", "Per-person and per-person-per-day totals"],
                "how": [
                    "Accommodation, food, local transport and activities are entered per day in the destination currency, added, then multiplied by the number of days.",
                    "The contingency slider adds a percentage to that on-site subtotal — 10% by default, because trips overrun.",
                    "Only the on-site subtotal is converted, using the cross-rate from the ECB reference table. Flights and insurance are already in your currency and are added afterwards.",
                    "The page ships with a dated ECB snapshot and tries to refresh from the open frankfurter.dev feed; whichever it used is printed with its date.",
                ],
                "never": [
                    "It is not a quote. Card and bank margins of 1–4% are not in these numbers, and the ECB rate is a mid-market reference.",
                    "It has no price database — every figure here is one you typed. It does not guess what a hotel in a city costs.",
                    "Nothing is saved or sent. Reload and the trip is gone.",
                ],
                "faq": [
                    ("Which rate does it convert with?", "The European Central Bank reference rate, fetched from the open frankfurter.dev feed with a dated snapshot as fallback. The rate, its date and which source was used are shown in the last result box."),
                    ("Why keep the two currencies apart?", "Because mixing them is where travel budgets go wrong. Hotel and food are spent in the destination currency and are exposed to rate moves; a flight you already paid at home is not."),
                    ("Is 10% contingency the right buffer?", "It is only a starting point that you can set anywhere from 0 to 30%. Long trips and unfamiliar destinations usually want more."),
                ],
                "app_heading": "Want to track the real spend while you are there?",
                "card": "Budget a trip in two currencies on dated ECB reference rates — per person and per day.",
                "ui": {
                    "h2": "Split the trip into on-site and fixed costs",
                    "intro": "Daily amounts in the destination currency, fixed costs in yours.",
                    "l_days": "Days", "l_people": "Travellers", "l_home": "Your currency",
                    "l_dest": "Destination currency", "l_flights": "Flights (your currency)",
                    "l_onceoff": "Insurance, visa, other (your currency)",
                    "h_daily": "Per day, per group — in the destination currency",
                    "l_stay": "Accommodation", "l_food": "Food & drink", "l_local": "Local transport",
                    "l_fun": "Activities", "l_buffer": "Contingency",
                    "r_daily": "Daily spend", "r_onsite": "On-site total", "r_fixed": "Fixed costs",
                    "r_total": "Trip total", "r_person": "Per traveller", "r_rate": "Rate used",
                    "per_day": "per day", "src_snapshot": "built-in ECB snapshot",
                    "src_live": "live ECB reference (frankfurter.dev)",
                    "note": "ECB reference rates are a mid-market reference, not the rate your card will give you — banks and cards add their own margin.",
                },
            },
            "ko": {
                "q": [("여행 가계부", "store-hint"), ("환율 계산기 앱", "store-hint")],
                "title": "여행 예산 계산기 — 두 통화, ECB 기준환율, 가입 없이",
                "description": "현지 통화로 쓰는 하루 경비와 자국 통화로 내는 고정비를 나눠 계산하고, 날짜가 표시된 ECB 기준환율로 환산합니다. 1인당·하루당 금액까지 표시.",
                "h1": "여행 예산 계산기",
                "eyebrow": "두 통화 · 날짜가 표시된 ECB 기준환율",
                "lead": "숙박비와 식비는 현지 통화, 항공권과 보험은 자국 통화로 나갑니다. 이 계산기는 둘을 섞지 않고, 마지막에만 환산합니다.",
                "badges": ["두 통화 분리", "날짜 표시 ECB 환율", "1인당·하루당", "가입 불필요"],
                "features": ["하루 경비는 현지 통화로 입력", "고정비는 자국 통화로 입력", "예비비 비율 조절", "1인당 및 1인 1일당 금액"],
                "how": [
                    "숙박·식사·현지 교통·액티비티를 현지 통화로 하루치 입력하면 합산 후 일수를 곱합니다.",
                    "예비비 슬라이더가 현지 지출 소계에 비율을 더합니다. 기본값은 10%입니다.",
                    "환산은 현지 지출 소계에만 적용하며, ECB 기준환율 표의 교차환율을 씁니다. 항공권과 보험은 이미 자국 통화이므로 그 뒤에 더합니다.",
                    "페이지에는 날짜가 있는 ECB 스냅숏이 포함되어 있고, 공개 frankfurter.dev 피드로 갱신을 시도합니다. 실제로 쓴 출처와 날짜를 함께 표시합니다.",
                ],
                "never": [
                    "견적이 아닙니다. 카드·은행 마진(보통 1–4%)은 포함되어 있지 않으며 ECB 환율은 중간 기준값입니다.",
                    "가격 데이터베이스가 없습니다. 모든 숫자는 사용자가 입력한 값이며, 호텔 시세를 추정하지 않습니다.",
                    "저장하거나 전송하지 않습니다. 새로고침하면 사라집니다.",
                ],
                "faq": [
                    ("어떤 환율로 환산하나요?", "유럽중앙은행(ECB) 기준환율이며 공개 frankfurter.dev 피드에서 가져오고, 실패하면 내장된 날짜 있는 스냅숏을 씁니다. 사용한 환율·날짜·출처가 마지막 칸에 표시됩니다."),
                    ("왜 통화를 나눠서 입력하나요?", "섞는 순간 여행 예산이 어긋나기 때문입니다. 숙박과 식비는 현지 통화라 환율 변동에 노출되지만, 이미 결제한 항공권은 그렇지 않습니다."),
                    ("예비비 10%가 적당한가요?", "출발점일 뿐이며 0–30% 사이에서 조절할 수 있습니다. 장기 여행이나 처음 가는 곳이라면 보통 더 많이 잡습니다."),
                ],
                "app_heading": "현지에서 실제 지출도 기록하고 싶나요?",
                "card": "현지·자국 통화를 나눠 여행 예산을 계산하고 날짜 있는 ECB 환율로 환산합니다.",
                "ui": {
                    "h2": "현지 지출과 고정비를 나눠서",
                    "intro": "하루 금액은 현지 통화로, 고정비는 자국 통화로 입력하세요.",
                    "l_days": "일수", "l_people": "인원", "l_home": "자국 통화",
                    "l_dest": "현지 통화", "l_flights": "항공권 (자국 통화)",
                    "l_onceoff": "보험·비자·기타 (자국 통화)",
                    "h_daily": "하루 · 일행 전체 — 현지 통화로",
                    "l_stay": "숙박", "l_food": "식비", "l_local": "현지 교통",
                    "l_fun": "액티비티", "l_buffer": "예비비",
                    "r_daily": "하루 지출", "r_onsite": "현지 지출 합계", "r_fixed": "고정비",
                    "r_total": "여행 총액", "r_person": "1인당", "r_rate": "적용 환율",
                    "per_day": "하루", "src_snapshot": "내장 ECB 스냅숏",
                    "src_live": "실시간 ECB 기준환율 (frankfurter.dev)",
                    "note": "ECB 기준환율은 중간 기준값이며 카드사·은행은 자체 마진을 더합니다. 실제 결제 환율과 다릅니다.",
                },
            },
            "zh-Hant": {
                "q": [("旅遊預算", "D2"), ("匯率換算", "D3")],
                "title": "旅遊預算計算機 — 兩種幣別、ECB 參考匯率、免註冊",
                "description": "把當地花費（當地幣別）與機票保險（本國幣別）分開計算，最後才用有標日期的 ECB 參考匯率換算，並算出每人與每人每天的金額。",
                "h1": "旅遊預算計算機",
                "eyebrow": "兩種幣別 · 標明日期的 ECB 參考匯率",
                "lead": "住宿餐飲花的是當地貨幣，機票保險付的是本國貨幣。這裡把兩者分開，最後才換算，而且把用的匯率與日期寫在畫面上。",
                "badges": ["兩種幣別分開", "標日期的 ECB 匯率", "每人／每天", "免註冊"],
                "features": ["當地花費以當地幣別輸入", "固定支出以本國幣別輸入", "可調整的預備金比例", "每人與每人每天金額"],
                "how": [
                    "住宿、餐飲、當地交通與活動以當地幣別輸入每日金額，加總後乘上天數。",
                    "預備金滑桿會在當地花費小計上加一個百分比，預設 10%，因為旅行幾乎都會超支。",
                    "只有當地花費小計會被換算，使用 ECB 參考匯率表的交叉匯率；機票與保險本來就是本國幣別，之後才相加。",
                    "頁面內建有日期的 ECB 匯率快照，並會嘗試向公開的 frankfurter.dev 更新；實際用到哪一份、日期是什麼都會顯示。",
                ],
                "never": [
                    "這不是報價。銀行與信用卡通常另有 1–4% 的價差，ECB 匯率只是中間參考值。",
                    "沒有任何價格資料庫，所有數字都是你自己輸入的，不會替你猜某個城市的房價。",
                    "不儲存、不上傳，重新整理就沒了。",
                ],
                "faq": [
                    ("是用哪種匯率換算？", "歐洲央行（ECB）參考匯率，透過公開的 frankfurter.dev 取得，取不到時使用內建、標有日期的快照。實際使用的匯率、日期與來源都顯示在最後一格。"),
                    ("為什麼要把兩種幣別分開？", "因為混在一起就是旅遊預算失準的主因。住宿與餐飲是當地幣別、會受匯率波動影響；已經在國內付掉的機票則不會。"),
                    ("預備金抓 10% 夠嗎？", "那只是起點，可以在 0–30% 之間調整。天數長或第一次去的地方通常要抓更多。"),
                ],
                "app_heading": "想在旅途中記下實際花費嗎？",
                "card": "以兩種幣別計算旅遊預算，使用標明日期的 ECB 參考匯率換算。",
                "ui": {
                    "h2": "把當地花費與固定支出分開算",
                    "intro": "每日金額用當地幣別，固定支出用你的幣別。",
                    "l_days": "天數", "l_people": "人數", "l_home": "你的幣別",
                    "l_dest": "當地幣別", "l_flights": "機票（你的幣別）",
                    "l_onceoff": "保險、簽證、其他（你的幣別）",
                    "h_daily": "每天 · 全團合計 — 以當地幣別",
                    "l_stay": "住宿", "l_food": "餐飲", "l_local": "當地交通",
                    "l_fun": "活動與門票", "l_buffer": "預備金",
                    "r_daily": "每日花費", "r_onsite": "當地花費合計", "r_fixed": "固定支出",
                    "r_total": "旅程總額", "r_person": "每人", "r_rate": "使用匯率",
                    "per_day": "每天", "src_snapshot": "內建 ECB 快照",
                    "src_live": "即時 ECB 參考匯率（frankfurter.dev）",
                    "note": "ECB 參考匯率是中間價，不是你刷卡會拿到的匯率；銀行與發卡機構會另外加價。",
                },
            },
        },
    })
    return spec


# --------------------------------------------------------- 6. voice to text

VOICE_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="lang">{ui[l_lang]}</label><select id="lang">
<option value="en-US">English (US)</option><option value="en-GB">English (UK)</option>
<option value="ja-JP">日本語</option><option value="ko-KR">한국어</option>
<option value="de-DE">Deutsch</option><option value="zh-TW">中文（台灣）</option>
<option value="zh-CN">中文（简体）</option><option value="es-ES">Español</option>
<option value="fr-FR">Français</option><option value="pt-BR">Português (BR)</option>
<option value="th-TH">ไทย</option><option value="id-ID">Bahasa Indonesia</option></select></div>
<div class="field"><label for="punct">{ui[l_punct]}</label><select id="punct">
<option value="1">{ui[on]}</option><option value="0">{ui[off]}</option></select></div>
<div class="field" style="align-self:end;display:flex;gap:8px">
<button class="button" id="rec">{ui[b_start]}</button>
<button class="button ghost" id="clear">{ui[b_clear]}</button></div>
</div>
<div class="results">
<div class="result"><strong>{ui[r_state]}</strong><span id="state">—</span></div>
<div class="result"><strong>{ui[r_words]}</strong><span id="words">0</span></div>
<div class="result"><strong>{ui[r_chars]}</strong><span id="chars">0</span></div>
<div class="result"><strong>{ui[r_support]}</strong><span id="sup">—</span></div>
</div>
<textarea id="text" style="margin-top:16px;min-height:220px" placeholder="{ui[ph]}"></textarea>
<p class="small" id="interim" style="min-height:1.4em;color:#8a7a5f"></p>
<div style="display:flex;gap:10px;flex-wrap:wrap">
<button class="button ghost" id="copy">{ui[b_copy]}</button>
<button class="button ghost" id="dl">{ui[b_txt]}</button></div>
<p class="note">{ui[note]}</p>
"""

VOICE_JS = r"""
var $=function(i){return document.getElementById(i);};
var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
var rec=null,on=false;
$('sup').textContent=SR?L.sup_yes:L.sup_no;
if(!SR){$('rec').disabled=true;$('state').textContent=L.s_unsupported;}
function count(){var t=$('text').value;
  $('chars').textContent=String(t.length);
  var w=t.trim()?t.trim().split(/\s+/).length:0;
  if(/[぀-ヿ一-鿿가-힯]/.test(t))
    w=t.replace(/\s+/g,'').length;
  $('words').textContent=String(w);}
$('text').addEventListener('input',count);
function stop(){if(rec){try{rec.stop();}catch(e){}}on=false;
  $('rec').textContent=L.b_start;$('state').textContent=L.s_idle;$('interim').textContent='';}
function start(){
  if(!SR)return;
  rec=new SR();rec.lang=$('lang').value;rec.continuous=true;rec.interimResults=true;
  rec.onresult=function(e){
    var add='',tmp='';
    for(var i=e.resultIndex;i<e.results.length;i++){
      var s=e.results[i][0].transcript;
      if(e.results[i].isFinal)add+=s;else tmp+=s;}
    if(add){
      var box=$('text'),sep=box.value&&!/\s$/.test(box.value)?' ':'';
      if($('punct').value==='1'){add=add.replace(/^\s+/,'');
        if(add&&!/[.!?。！？]$/.test(add.trim()))add=add.trim()+' ';}
      box.value+=sep+add;count();}
    $('interim').textContent=tmp;};
  rec.onerror=function(e){$('state').textContent=L.s_error+' ('+e.error+')';on=false;
    $('rec').textContent=L.b_start;};
  rec.onend=function(){if(on){try{rec.start();}catch(e){}}else{$('state').textContent=L.s_idle;}};
  try{rec.start();}catch(e){$('state').textContent=L.s_error;return;}
  on=true;$('rec').textContent=L.b_stop;$('state').textContent=L.s_listening;}
$('rec').addEventListener('click',function(){on?stop():start();});
$('clear').addEventListener('click',function(){$('text').value='';$('interim').textContent='';count();});
$('lang').addEventListener('change',function(){if(on){stop();start();}});
$('copy').addEventListener('click',function(){
  var t=$('text').value;
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(t).then(function(){
      $('copy').textContent=L.b_copied;
      setTimeout(function(){$('copy').textContent=L.b_copy;},1600);});}
  else window.prompt(L.b_copy,t);});
$('dl').addEventListener('click',function(){
  var b=new Blob([$('text').value],{type:'text/plain;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download='transcript.txt';a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);},4000);});
if(L.rec_lang)$('lang').value=L.rec_lang;
$('state').textContent=SR?L.s_idle:L.s_unsupported;
count();
"""

_SONO_APP = {"app_key": "sononote", "app_id": "6782139553", "app_name": "Sono Note",
             "category": "ProductivityApplication"}


def spec_voice_to_text():
    spec = dict(_SONO_APP)
    spec.update({
        "slug": "voice-to-text",
        "body": VOICE_BODY,
        "script": VOICE_JS,
        "i18n": {
            "en": {
                "q": [("voice to text", "D3"), ("speech to text", "D3")],
                "title": "Voice to Text — Free Browser Dictation in 12 Languages",
                "description": "Dictate straight into your browser and get editable text you can copy or download. Twelve languages, live word count, no account. Honest about where recognition happens.",
                "h1": "Voice to text",
                "eyebrow": "Browser dictation · 12 languages · no account",
                "lead": "Press start, talk, and the words land in an editable box you can correct, copy or save as a text file.",
                "badges": ["12 recognition languages", "Editable as you go", "Copy or .txt", "No account"],
                "features": ["Continuous dictation with live interim text", "Twelve recognition languages", "Word and character count that handles CJK", "Copy to clipboard or download as .txt"],
                "how": [
                    "The page uses the browser’s built-in SpeechRecognition API. Recognition runs continuously and restarts itself if the browser cuts the session short.",
                    "Interim results appear in grey under the box; only finalised phrases are written into the editable text area, so you can keep typing corrections while you speak.",
                    "The tidy-up option trims stray leading spaces and spaces phrases apart. It does not rewrite your words.",
                    "The counter switches to characters for Japanese, Korean and Chinese, where counting whitespace-separated words is meaningless.",
                ],
                "never": [
                    "It does not promise on-device recognition. Most desktop browsers, Chrome in particular, send the audio to the browser vendor’s servers to be transcribed — that is the browser’s behaviour, not a choice this page can make.",
                    "It never stores or transmits anything itself. The text stays in the page and is gone when you close the tab.",
                    "It does not identify speakers, add timestamps, or transcribe an audio file — it listens to a live microphone only.",
                ],
                "faq": [
                    ("Which browsers work?", "Safari on iOS and macOS, Chrome, and Edge implement the SpeechRecognition API. Firefox currently does not; the page tells you on load which side you are on."),
                    ("Does my voice leave my device?", "That depends on the browser, not on this page. Chrome and Edge send audio to a cloud service for recognition; Safari can use on-device recognition for some languages. Do not dictate confidential material into any browser you have not checked."),
                    ("Can I transcribe an existing recording?", "No. The Web Speech API only listens to a live microphone. Playing a recording into the mic works but the quality is poor — a real transcription app handles files properly."),
                ],
                "app_heading": "Need recordings and transcripts kept together?",
                "card": "Dictate into your browser in 12 languages and copy or download the text.",
                "footer_note": "Runs in your browser · recognition may be performed by your browser’s own speech service",
                "ui": {
                    "rec_lang": "en-US",
                    "h2": "Press start and talk",
                    "intro": "Your browser asks for microphone permission the first time.",
                    "l_lang": "Recognition language", "l_punct": "Tidy up spacing",
                    "on": "On", "off": "Off",
                    "b_start": "● Start", "b_stop": "■ Stop", "b_clear": "Clear",
                    "r_state": "Status", "r_words": "Words", "r_chars": "Characters", "r_support": "Browser support",
                    "s_idle": "Ready", "s_listening": "Listening…", "s_error": "Error",
                    "s_unsupported": "Not supported by this browser",
                    "sup_yes": "Available", "sup_no": "Unavailable",
                    "ph": "Text appears here and stays editable.",
                    "b_copy": "Copy text", "b_copied": "Copied", "b_txt": "Download .txt",
                    "note": "Recognition is performed by your browser. Chrome and Edge send the audio to their own servers; Safari may recognise on device. Nothing is sent by this page itself.",
                },
            },
            "ja": {
                "q": [("文字起こし", "D4"), ("音声 テキスト 変換", "store-hint")],
                "title": "音声をテキストに — ブラウザだけで使える無料の文字起こし（12言語）",
                "description": "ブラウザに話しかけるだけで、編集できるテキストになります。コピーや .txt 保存に対応、登録不要。認識がどこで行われるかも正直に書いています。",
                "h1": "音声をテキストにする",
                "eyebrow": "ブラウザで音声入力 · 12言語 · 登録不要",
                "lead": "開始を押して話すと、編集できる欄に文字が入ります。その場で直して、コピーやテキストファイル保存ができます。",
                "badges": ["12言語に対応", "話しながら修正できる", "コピー／.txt 保存", "登録不要"],
                "features": ["連続音声入力（途中経過も表示）", "12言語の認識", "日本語では文字数でカウント", "クリップボードへコピー・.txt 保存"],
                "how": [
                    "ブラウザ内蔵の SpeechRecognition API を使います。セッションが途中で切れても自動で再開します。",
                    "認識途中の文字は入力欄の下にグレーで表示し、確定した文だけを編集欄に書き込みます。話しながら前の文を直せます。",
                    "整形オプションは余分な空白の除去と文の区切りだけを行い、言い回しを書き換えることはしません。",
                    "日本語・韓国語・中国語では単語数ではなく文字数を数えます。空白区切りの語数に意味がないためです。",
                ],
                "never": [
                    "「端末内で認識します」とは約束しません。Chrome など多くのブラウザは音声を提供元のサーバーに送って認識します。これはブラウザの動作で、このページが決められることではありません。",
                    "このページ自体は保存も送信も行いません。文字はページ内にだけ残り、タブを閉じれば消えます。",
                    "話者の識別、タイムスタンプ、音声ファイルの文字起こしには対応していません。マイクの生音声だけを扱います。",
                ],
                "faq": [
                    ("どのブラウザで使えますか？", "iOS と macOS の Safari、Chrome、Edge が SpeechRecognition API に対応しています。Firefox は現時点で非対応です。読み込み時に対応状況を表示します。"),
                    ("声は端末の外に出ますか？", "ブラウザ次第です。Chrome と Edge は認識のために音声をクラウドへ送ります。Safari は言語によっては端末内で認識します。確認していないブラウザで機密情報を話さないでください。"),
                    ("録音済みの音声を文字起こしできますか？", "できません。Web Speech API はマイクの生音声だけを扱います。スピーカーで再生してマイクに拾わせることはできますが精度は落ちます。ファイルを扱うのは専用アプリの仕事です。"),
                ],
                "app_heading": "録音と文字起こしを一緒に残したいですか？",
                "card": "ブラウザで 12 言語の音声入力。テキストはコピーも .txt 保存もできます。",
                "footer_note": "ブラウザ内で動作 · 音声認識はブラウザ側のサービスが行う場合があります",
                "ui": {
                    "rec_lang": "ja-JP",
                    "h2": "開始を押して話してください",
                    "intro": "初回はブラウザがマイクの許可を求めます。",
                    "l_lang": "認識する言語", "l_punct": "空白の自動整形",
                    "on": "オン", "off": "オフ",
                    "b_start": "● 開始", "b_stop": "■ 停止", "b_clear": "消去",
                    "r_state": "状態", "r_words": "語数／文字数", "r_chars": "文字数", "r_support": "ブラウザ対応",
                    "s_idle": "待機中", "s_listening": "認識中…", "s_error": "エラー",
                    "s_unsupported": "このブラウザは非対応です",
                    "sup_yes": "利用できます", "sup_no": "利用できません",
                    "ph": "ここに文字が入り、そのまま編集できます。",
                    "b_copy": "コピー", "b_copied": "コピーしました", "b_txt": ".txt で保存",
                    "note": "認識はブラウザが行います。Chrome と Edge は音声を自社サーバーへ送ります。Safari は端末内で認識する場合があります。このページ自体は何も送信しません。",
                },
            },
            "ko": {
                "q": [("음성 텍스트 변환", "D2"), ("녹음 텍스트", "store-hint")],
                "title": "음성을 텍스트로 — 설치 없이 브라우저에서 쓰는 무료 받아쓰기 (12개 언어)",
                "description": "브라우저에 말하면 편집 가능한 텍스트가 됩니다. 복사하거나 .txt로 저장하세요. 가입 불필요, 인식이 어디에서 이루어지는지도 정직하게 밝힙니다.",
                "h1": "음성 텍스트 변환",
                "eyebrow": "브라우저 받아쓰기 · 12개 언어 · 가입 불필요",
                "lead": "시작을 누르고 말하면 편집할 수 있는 칸에 글자가 들어갑니다. 그 자리에서 고치고, 복사하거나 파일로 저장하세요.",
                "badges": ["12개 인식 언어", "말하면서 수정 가능", "복사 또는 .txt", "가입 불필요"],
                "features": ["중간 결과가 보이는 연속 받아쓰기", "12개 언어 인식", "한국어는 글자 수로 계산", "클립보드 복사 및 .txt 저장"],
                "how": [
                    "브라우저에 내장된 SpeechRecognition API를 사용합니다. 세션이 끊기면 자동으로 다시 시작합니다.",
                    "인식 중인 문장은 입력칸 아래에 회색으로, 확정된 문장만 편집 가능한 칸에 들어갑니다. 말하면서 앞 문장을 고칠 수 있습니다.",
                    "정리 옵션은 불필요한 공백을 없애고 문장 사이를 띄우기만 합니다. 표현을 바꾸지 않습니다.",
                    "한국어·일본어·중국어에서는 단어 수 대신 글자 수를 셉니다. 공백 기준 단어 수가 의미 없기 때문입니다.",
                ],
                "never": [
                    "기기 내 인식을 약속하지 않습니다. Chrome 등 다수 브라우저는 인식을 위해 음성을 제조사 서버로 보냅니다. 이는 브라우저의 동작이며 이 페이지가 정할 수 있는 부분이 아닙니다.",
                    "이 페이지 자체는 저장하거나 전송하지 않습니다. 텍스트는 페이지 안에만 있고 탭을 닫으면 사라집니다.",
                    "화자 구분, 타임스탬프, 오디오 파일 변환은 지원하지 않습니다. 실시간 마이크만 사용합니다.",
                ],
                "faq": [
                    ("어떤 브라우저에서 되나요?", "iOS·macOS의 Safari, Chrome, Edge가 SpeechRecognition API를 지원합니다. Firefox는 현재 지원하지 않으며, 페이지를 열면 지원 여부가 표시됩니다."),
                    ("제 목소리가 기기 밖으로 나가나요?", "이 페이지가 아니라 브라우저에 달려 있습니다. Chrome과 Edge는 인식을 위해 음성을 클라우드로 보내고, Safari는 일부 언어에서 기기 내 인식을 씁니다. 확인하지 않은 브라우저에서 기밀 내용을 말하지 마세요."),
                    ("녹음 파일도 변환되나요?", "안 됩니다. Web Speech API는 실시간 마이크만 처리합니다. 스피커로 재생해 마이크로 받는 방법은 품질이 크게 떨어집니다."),
                ],
                "app_heading": "녹음과 텍스트를 함께 보관하고 싶나요?",
                "card": "브라우저에서 12개 언어로 받아쓰고 텍스트를 복사하거나 저장합니다.",
                "footer_note": "브라우저에서 실행 · 음성 인식은 브라우저의 자체 서비스가 수행할 수 있습니다",
                "ui": {
                    "rec_lang": "ko-KR",
                    "h2": "시작을 누르고 말하세요",
                    "intro": "처음에는 브라우저가 마이크 권한을 요청합니다.",
                    "l_lang": "인식 언어", "l_punct": "띄어쓰기 정리",
                    "on": "켬", "off": "끔",
                    "b_start": "● 시작", "b_stop": "■ 정지", "b_clear": "지우기",
                    "r_state": "상태", "r_words": "단어/글자", "r_chars": "문자 수", "r_support": "브라우저 지원",
                    "s_idle": "대기 중", "s_listening": "듣는 중…", "s_error": "오류",
                    "s_unsupported": "이 브라우저는 지원하지 않습니다",
                    "sup_yes": "사용 가능", "sup_no": "사용 불가",
                    "ph": "여기에 텍스트가 들어오고 계속 수정할 수 있습니다.",
                    "b_copy": "텍스트 복사", "b_copied": "복사됨", "b_txt": ".txt 저장",
                    "note": "인식은 브라우저가 수행합니다. Chrome과 Edge는 음성을 자사 서버로 보내고, Safari는 기기 내에서 처리할 수 있습니다. 이 페이지 자체는 아무것도 전송하지 않습니다.",
                },
            },
            "de-DE": {
                "q": [("sprache zu text", "D3"), ("audio transkribieren", "store-hint")],
                "title": "Sprache zu Text — kostenloses Diktat im Browser, 12 Sprachen",
                "description": "Ins Mikrofon sprechen, editierbaren Text bekommen, kopieren oder als .txt speichern. Zwölf Sprachen, kein Konto — und eine ehrliche Angabe, wo die Erkennung stattfindet.",
                "h1": "Sprache zu Text",
                "eyebrow": "Diktat im Browser · 12 Sprachen · ohne Konto",
                "lead": "Start drücken, sprechen — der Text landet in einem Feld, das Sie sofort korrigieren, kopieren oder speichern können.",
                "badges": ["12 Erkennungssprachen", "Während des Sprechens editierbar", "Kopieren oder .txt", "Ohne Konto"],
                "features": ["Fortlaufendes Diktat mit Zwischenergebnis", "Zwölf Erkennungssprachen", "Wort- und Zeichenzähler, CJK-tauglich", "In die Zwischenablage kopieren oder als .txt speichern"],
                "how": [
                    "Die Seite nutzt die im Browser eingebaute SpeechRecognition-API und startet die Sitzung automatisch neu, wenn der Browser sie beendet.",
                    "Zwischenergebnisse stehen grau unter dem Feld; nur abgeschlossene Sätze werden in den editierbaren Text übernommen.",
                    "Die Aufräum-Option entfernt nur überflüssige Leerzeichen und trennt Sätze. Ihre Formulierungen bleiben unverändert.",
                    "Für Japanisch, Koreanisch und Chinesisch zählt die Anzeige Zeichen statt Wörter.",
                ],
                "never": [
                    "Es verspricht keine Erkennung auf dem Gerät. Chrome und die meisten Desktop-Browser senden das Audio an die Server des Browser-Anbieters — das ist deren Verhalten, nicht eine Entscheidung dieser Seite.",
                    "Die Seite selbst speichert und sendet nichts. Der Text bleibt im Tab und ist beim Schließen weg.",
                    "Keine Sprechererkennung, keine Zeitstempel, keine Transkription vorhandener Dateien — nur das Live-Mikrofon.",
                ],
                "faq": [
                    ("Welche Browser funktionieren?", "Safari unter iOS und macOS, Chrome und Edge unterstützen die SpeechRecognition-API. Firefox derzeit nicht; die Seite zeigt beim Laden, woran Sie sind."),
                    ("Verlässt meine Stimme das Gerät?", "Das hängt vom Browser ab, nicht von dieser Seite. Chrome und Edge senden Audio zur Erkennung in die Cloud, Safari kann in manchen Sprachen lokal erkennen. Diktieren Sie nichts Vertrauliches in einen Browser, den Sie nicht geprüft haben."),
                    ("Kann ich eine vorhandene Aufnahme transkribieren?", "Nein. Die Web-Speech-API hört nur das Live-Mikrofon. Abspielen und mitschneiden funktioniert, liefert aber schlechte Ergebnisse."),
                ],
                "app_heading": "Aufnahme und Text am selben Ort behalten?",
                "card": "Im Browser in 12 Sprachen diktieren und den Text kopieren oder speichern.",
                "footer_note": "Läuft im Browser · die Erkennung übernimmt ggf. der Spracherkennungsdienst Ihres Browsers",
                "ui": {
                    "rec_lang": "de-DE",
                    "h2": "Start drücken und sprechen",
                    "intro": "Beim ersten Mal fragt der Browser nach der Mikrofon-Erlaubnis.",
                    "l_lang": "Erkennungssprache", "l_punct": "Abstände aufräumen",
                    "on": "An", "off": "Aus",
                    "b_start": "● Start", "b_stop": "■ Stopp", "b_clear": "Leeren",
                    "r_state": "Status", "r_words": "Wörter", "r_chars": "Zeichen", "r_support": "Browser-Unterstützung",
                    "s_idle": "Bereit", "s_listening": "Hört zu …", "s_error": "Fehler",
                    "s_unsupported": "Von diesem Browser nicht unterstützt",
                    "sup_yes": "Verfügbar", "sup_no": "Nicht verfügbar",
                    "ph": "Hier erscheint der Text und bleibt editierbar.",
                    "b_copy": "Text kopieren", "b_copied": "Kopiert", "b_txt": ".txt herunterladen",
                    "note": "Die Erkennung übernimmt Ihr Browser. Chrome und Edge senden das Audio an eigene Server, Safari erkennt teils lokal. Diese Seite selbst sendet nichts.",
                },
            },
            "zh-Hant": {
                "q": [("語音轉文字", "D4"), ("錄音 轉 文字", "store-hint")],
                "title": "語音轉文字 — 免安裝、瀏覽器直接用的免費聽寫（12 種語言）",
                "description": "對著瀏覽器說話就變成可編輯的文字，可複製或下載 .txt。免註冊，並且誠實說明語音辨識實際在哪裡進行。",
                "h1": "語音轉文字",
                "eyebrow": "瀏覽器聽寫 · 12 種語言 · 免註冊",
                "lead": "按下開始就說話，文字會進到可編輯的欄位，能當場修正、複製，或存成文字檔。",
                "badges": ["12 種辨識語言", "可邊說邊改", "複製或 .txt", "免註冊"],
                "features": ["連續聽寫並顯示暫時結果", "12 種辨識語言", "中日韓改以字數計算", "複製到剪貼簿或下載 .txt"],
                "how": [
                    "使用瀏覽器內建的 SpeechRecognition API，若瀏覽器中斷會自動重新開始。",
                    "辨識中的內容以灰字顯示在欄位下方，只有確定的句子才寫進可編輯欄位，所以你可以邊說邊改前面的字。",
                    "整理選項只會清掉多餘空白與分隔句子，不會改寫你的用字。",
                    "中文、日文、韓文以字數計算，因為用空白斷詞沒有意義。",
                ],
                "never": [
                    "不宣稱「在你的裝置上辨識」。Chrome 等多數瀏覽器會把聲音送到瀏覽器廠商的伺服器辨識，這是瀏覽器的行為，不是這個頁面能決定的。",
                    "這個頁面本身不儲存也不傳送任何東西，文字只留在頁面內，關掉分頁就消失。",
                    "不做語者辨識、不加時間軸、也不能轉錄音檔，只處理即時麥克風。",
                ],
                "faq": [
                    ("哪些瀏覽器可以用？", "iOS 與 macOS 的 Safari、Chrome、Edge 支援 SpeechRecognition API；Firefox 目前不支援。頁面載入時會直接顯示你這台的支援狀況。"),
                    ("我的聲音會離開裝置嗎？", "這取決於瀏覽器而不是這個頁面。Chrome 與 Edge 會把聲音送到雲端辨識，Safari 在部分語言可在裝置上辨識。沒確認過的瀏覽器請不要用來講機密內容。"),
                    ("可以轉錄已經錄好的檔案嗎？", "不行。Web Speech API 只處理即時麥克風。用喇叭播出來讓麥克風收音可行但品質很差，檔案轉錄要交給專門的 App。"),
                ],
                "app_heading": "想把錄音和文字放在一起保存嗎？",
                "card": "在瀏覽器用 12 種語言聽寫，文字可複製或下載。",
                "footer_note": "在瀏覽器內執行 · 語音辨識可能由瀏覽器自家的服務進行",
                "ui": {
                    "rec_lang": "zh-TW",
                    "h2": "按下開始，然後說話",
                    "intro": "第一次使用時瀏覽器會要求麥克風權限。",
                    "l_lang": "辨識語言", "l_punct": "自動整理空白",
                    "on": "開", "off": "關",
                    "b_start": "● 開始", "b_stop": "■ 停止", "b_clear": "清空",
                    "r_state": "狀態", "r_words": "字數", "r_chars": "字元數", "r_support": "瀏覽器支援",
                    "s_idle": "待機", "s_listening": "辨識中…", "s_error": "錯誤",
                    "s_unsupported": "這個瀏覽器不支援",
                    "sup_yes": "可以使用", "sup_no": "無法使用",
                    "ph": "文字會出現在這裡，而且可以直接編輯。",
                    "b_copy": "複製文字", "b_copied": "已複製", "b_txt": "下載 .txt",
                    "note": "辨識由瀏覽器執行：Chrome 與 Edge 會把聲音送到自家伺服器，Safari 可能在裝置上處理。這個頁面本身不傳送任何資料。",
                },
            },
        },
    })
    return spec


# ------------------------------------------------------------ 7. sharpener

SHARPEN_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="filedrop"><input type="file" id="file" accept="image/*"> <span class="small">{ui[accept]}</span></div>
<div class="controls" style="margin-top:16px">
<div class="field"><label for="amt">{ui[l_amount]} · <span id="av">80</span>%</label><input type="range" id="amt" min="0" max="200" value="80"></div>
<div class="field"><label for="rad">{ui[l_radius]} · <span id="rv">2</span> px</label><input type="range" id="rad" min="1" max="6" value="2"></div>
<div class="field"><label for="thr">{ui[l_threshold]} · <span id="tv">4</span></label><input type="range" id="thr" min="0" max="30" value="4"></div>
</div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button ghost" id="toggle" disabled>{ui[b_before]}</button>
<a class="button" id="dl" download>{ui[b_download]}</a></div>
<canvas class="stage" id="cv" style="margin-top:18px;display:none"></canvas>
<p class="note">{ui[note]}</p>
"""

SHARPEN_JS = r"""
var $=function(i){return document.getElementById(i);};
var img=null,url='',base=null,W=0,H=0,showing='after';
function boxBlur(src,w,h,r){
  var tmp=new Float32Array(src.length),out=new Float32Array(src.length),c,x,y,i,k,sum,n;
  for(c=0;c<3;c++){
    for(y=0;y<h;y++){
      for(x=0;x<w;x++){
        sum=0;n=0;
        for(k=-r;k<=r;k++){var xx=x+k;if(xx<0||xx>=w)continue;
          sum+=src[(y*w+xx)*4+c];n++;}
        tmp[(y*w+x)*4+c]=sum/n;}}
    for(x=0;x<w;x++){
      for(y=0;y<h;y++){
        sum=0;n=0;
        for(k=-r;k<=r;k++){var yy=y+k;if(yy<0||yy>=h)continue;
          sum+=tmp[(yy*w+x)*4+c];n++;}
        out[(y*w+x)*4+c]=sum/n;}}}
  return out;}
function unsharp(src,w,h,amount,radius,threshold){
  var blur=boxBlur(src,w,h,radius),out=new Uint8ClampedArray(src.length),i,c;
  for(i=0;i<src.length;i+=4){
    for(c=0;c<3;c++){
      var o=src[i+c],d=o-blur[i+c];
      if(Math.abs(d)<threshold)out[i+c]=o;
      else out[i+c]=o+d*amount;}
    out[i+3]=src[i+3];}
  return out;}
function apply(){
  if(!base)return;
  var cv=$('cv'),cx=cv.getContext('2d');
  var amount=parseInt($('amt').value,10)/100;
  var radius=parseInt($('rad').value,10);
  var threshold=parseInt($('thr').value,10);
  if(showing==='before'){
    cx.putImageData(new ImageData(new Uint8ClampedArray(base),W,H),0,0);}
  else{
    var out=unsharp(base,W,H,amount,radius,threshold);
    cx.putImageData(new ImageData(out,W,H),0,0);}
  cv.toBlob(function(b){
    var a=$('dl');if(a.dataset.blob)URL.revokeObjectURL(a.href);
    a.href=URL.createObjectURL(b);a.dataset.blob='1';
    a.download='sharpened.png';},'image/png');}
$('file').addEventListener('change',function(){
  var f=$('file').files[0];if(!f)return;
  if(url)URL.revokeObjectURL(url);
  url=URL.createObjectURL(f);img=new Image();
  img.onload=function(){
    var MAX=1800,s=Math.min(1,MAX/Math.max(img.naturalWidth,img.naturalHeight));
    W=Math.round(img.naturalWidth*s);H=Math.round(img.naturalHeight*s);
    var cv=$('cv');cv.width=W;cv.height=H;cv.style.display='block';
    var cx=cv.getContext('2d');cx.drawImage(img,0,0,W,H);
    base=cx.getImageData(0,0,W,H).data;
    $('toggle').disabled=false;showing='after';apply();};
  img.onerror=function(){alert(L.err_read);};
  img.src=url;});
$('amt').addEventListener('input',function(){$('av').textContent=$('amt').value;showing='after';apply();});
$('rad').addEventListener('input',function(){$('rv').textContent=$('rad').value;showing='after';apply();});
$('thr').addEventListener('input',function(){$('tv').textContent=$('thr').value;showing='after';apply();});
$('toggle').addEventListener('click',function(){
  showing=showing==='after'?'before':'after';
  $('toggle').textContent=showing==='after'?L.b_before:L.b_after;apply();});
"""

_UNBLURRY_APP = {"app_key": "unblurry", "app_id": "6782275018", "app_name": "Unblurry",
                 "category": "PhotoApplication"}


def spec_photo_sharpen():
    spec = dict(_UNBLURRY_APP)
    spec.update({
        "slug": "photo-sharpener",
        "body": SHARPEN_BODY,
        "script": SHARPEN_JS,
        "i18n": {
            "en": {
                "q": [("sharpen image", "D2"), ("fix blurry photo", "store-hint"), ("photo enhancer app", "store-hint")],
                "title": "Sharpen a Photo Online — Free Unsharp Mask, Honest About Its Limits",
                "description": "Real unsharp-mask sharpening in your browser with amount, radius and threshold controls, plus a before/after toggle. No upload, no watermark — and a clear statement of what sharpening cannot fix.",
                "h1": "Sharpen a photo",
                "eyebrow": "Real unsharp mask · before/after toggle",
                "lead": "This runs the same unsharp-mask maths that photo editors use, with the three controls that matter, and it tells you plainly which kinds of blur it cannot undo.",
                "badges": ["Amount, radius, threshold", "Before/after toggle", "No upload", "PNG export"],
                "features": ["Unsharp mask with amount, radius and threshold", "Instant before/after comparison", "Runs entirely in the browser", "Lossless PNG export"],
                "how": [
                    "The image is drawn to a canvas (long edge capped at 1800 px) and its pixels are read out.",
                    "A separable box blur of your chosen radius produces a soft copy. The difference between original and blur is the detail layer.",
                    "That detail layer is multiplied by the amount and added back — the classic unsharp mask. The threshold skips differences smaller than the value you set, so flat sky and skin do not turn grainy.",
                    "Export is PNG, so the sharpening is not immediately undone by JPEG compression.",
                ],
                "never": [
                    "It cannot recover detail that was never recorded. Motion blur, a missed focus and heavy upscaling are lost information — sharpening only raises local contrast around edges that already exist.",
                    "There is no AI, no invented pixels and no “enhance” magic. What you see is arithmetic on your own pixels.",
                    "Nothing is uploaded. The image never leaves the tab.",
                ],
                "faq": [
                    ("Can this fix an out-of-focus photo?", "No, and neither can any honest sharpening filter. Out-of-focus and motion blur destroy information. Unsharp mask increases contrast at edges, which makes a slightly soft photo look crisper — it does not reconstruct what the sensor never captured."),
                    ("What do the three sliders do?", "Amount is how strongly the detail layer is added back. Radius is how wide the edge halo is — small for fine detail, larger for soft images. Threshold ignores small differences so noise and smooth areas stay smooth."),
                    ("Why does the image get halos?", "That is over-sharpening: too much amount with too large a radius. Lower the amount first, then the radius. The before/after toggle makes it obvious."),
                ],
                "app_heading": "Sharpening photos on iPhone regularly?",
                "card": "Unsharp-mask sharpening in your browser with amount, radius, threshold and a before/after toggle.",
                "ui": {
                    "h2": "Load a photo and sharpen it",
                    "intro": "Processing happens on this page; the file is never uploaded.",
                    "accept": "One image at a time",
                    "l_amount": "Amount", "l_radius": "Radius", "l_threshold": "Threshold",
                    "b_before": "Show original", "b_after": "Show sharpened",
                    "b_download": "Download PNG",
                    "note": "Sharpening raises contrast at existing edges. It cannot undo motion blur or a missed focus — no tool can.",
                    "err_read": "That file could not be decoded by this browser.",
                },
            },
            "ja": {
                "q": [("写真 高画質化", "store-hint"), ("ぼやけた写真 修正", "store-hint")],
                "title": "写真をシャープにする — アンシャープマスクを無料でブラウザ内処理",
                "description": "強さ・半径・しきい値を調整できる本物のアンシャープマスクをブラウザ内で実行。処理前後を切り替えて比較でき、アップロードもウォーターマークもありません。",
                "h1": "写真をシャープにする",
                "eyebrow": "本物のアンシャープマスク · 前後比較",
                "lead": "写真編集ソフトと同じアンシャープマスクの計算を、必要な3つのつまみだけで。直せないボケについても正直に書いています。",
                "badges": ["強さ・半径・しきい値", "処理前後の切り替え", "アップロードなし", "PNG で保存"],
                "features": ["強さ・半径・しきい値つきアンシャープマスク", "処理前後をワンタップで比較", "すべてブラウザ内で処理", "劣化のない PNG 書き出し"],
                "how": [
                    "画像を canvas に描き（長辺は 1800 px まで）、ピクセルを取り出します。",
                    "指定した半径で分離型ボックスぼかしをかけ、元画像との差分を「ディテール層」として取り出します。",
                    "そのディテール層を強さの分だけ足し戻す、これが古典的なアンシャープマスクです。しきい値より小さい差は無視するので、空や肌がざらつきません。",
                    "書き出しは PNG です。JPEG 再圧縮でシャープ感がすぐ失われるのを避けるためです。",
                ],
                "never": [
                    "撮れていない情報は戻せません。手ブレ・ピンボケ・強い拡大で失われた情報は復元できず、できるのは既にあるエッジの局所コントラストを上げることだけです。",
                    "AI も生成もありません。あなたのピクセルに対する計算だけです。",
                    "アップロードしません。画像はタブの外に出ません。",
                ],
                "faq": [
                    ("ピンボケ写真は直りますか？", "直りません。正直なシャープ処理ならどれも同じです。ピンボケと手ブレは情報そのものが失われています。アンシャープマスクはエッジのコントラストを上げるので「少し甘い」写真はくっきり見えますが、写っていないものは作れません。"),
                    ("3つのつまみは何ですか？", "強さは差分をどれだけ足し戻すか、半径はエッジの縁取りの幅（細部なら小さく、眠い画像なら大きく）、しきい値はどれだけ小さい差を無視するか（ノイズと平坦部を守ります）。"),
                    ("縁に白い線が出るのですが", "かけすぎです。強さが大きく半径も大きい状態なので、まず強さを下げ、それでも残るなら半径を下げてください。前後比較ボタンで確認できます。"),
                ],
                "app_heading": "iPhone でよく写真を補正しますか？",
                "card": "強さ・半径・しきい値を調整できるアンシャープマスクをブラウザ内で。前後比較つき。",
                "ui": {
                    "h2": "写真を読み込んでシャープにする",
                    "intro": "処理はこのページ内で行われ、ファイルは送信されません。",
                    "accept": "一度に 1 枚",
                    "l_amount": "強さ", "l_radius": "半径", "l_threshold": "しきい値",
                    "b_before": "処理前を表示", "b_after": "処理後を表示",
                    "b_download": "PNG を保存",
                    "note": "シャープ処理は既存のエッジのコントラストを上げるだけです。手ブレやピンボケは元に戻せません（どのツールでも同じです）。",
                    "err_read": "このブラウザではこのファイルを読み込めませんでした。",
                },
            },
            "ko": {
                "q": [("사진 화질 개선", "D2"), ("흐린 사진 복원", "store-hint")],
                "title": "사진 선명하게 — 무료 언샤프 마스크, 브라우저에서 바로",
                "description": "강도·반경·임계값을 조절하는 진짜 언샤프 마스크를 브라우저에서 실행합니다. 적용 전후 비교, 업로드 없음, 워터마크 없음. 못 고치는 것도 분명히 밝힙니다.",
                "h1": "사진 선명하게 만들기",
                "eyebrow": "진짜 언샤프 마스크 · 전후 비교",
                "lead": "사진 편집 프로그램이 쓰는 것과 같은 언샤프 마스크 연산을, 실제로 중요한 세 가지 조절값만으로. 되살릴 수 없는 흐림은 솔직히 말합니다.",
                "badges": ["강도·반경·임계값", "전후 전환", "업로드 없음", "PNG 저장"],
                "features": ["강도·반경·임계값이 있는 언샤프 마스크", "적용 전후 즉시 비교", "브라우저에서 전부 처리", "무손실 PNG 저장"],
                "how": [
                    "이미지를 캔버스에 그리고(긴 변 최대 1800 px) 픽셀을 읽어옵니다.",
                    "지정한 반경으로 분리형 박스 블러를 적용해 부드러운 사본을 만들고, 원본과의 차이를 디테일 층으로 씁니다.",
                    "그 디테일 층에 강도를 곱해 다시 더합니다. 이것이 고전적인 언샤프 마스크입니다. 임계값보다 작은 차이는 건너뛰므로 하늘이나 피부가 거칠어지지 않습니다.",
                    "저장은 PNG입니다. JPEG 재압축으로 선명함이 곧바로 사라지지 않도록 하기 위해서입니다.",
                ],
                "never": [
                    "기록되지 않은 디테일은 되살릴 수 없습니다. 흔들림, 초점 실패, 과도한 확대는 정보 자체가 사라진 것이며, 선명화는 이미 존재하는 경계의 대비만 올립니다.",
                    "AI도, 만들어낸 픽셀도 없습니다. 사용자의 픽셀에 대한 계산뿐입니다.",
                    "업로드하지 않습니다. 이미지는 탭 밖으로 나가지 않습니다.",
                ],
                "faq": [
                    ("초점이 나간 사진도 살릴 수 있나요?", "없습니다. 정직한 선명화 필터라면 모두 마찬가지입니다. 초점 실패와 흔들림은 정보를 없앱니다. 언샤프 마스크는 경계 대비를 올려 조금 무른 사진을 또렷해 보이게 할 뿐입니다."),
                    ("세 개의 슬라이더는 무엇인가요?", "강도는 디테일을 얼마나 되돌릴지, 반경은 경계 테두리의 폭(세밀한 사진은 작게, 무른 사진은 크게), 임계값은 얼마나 작은 차이를 무시할지를 정합니다."),
                    ("테두리에 흰 줄이 생깁니다", "과도한 선명화입니다. 강도가 크고 반경도 큰 상태이니 강도를 먼저 낮추고, 그래도 남으면 반경을 줄이세요. 전후 전환 버튼으로 확인할 수 있습니다."),
                ],
                "app_heading": "아이폰에서 사진 보정을 자주 하나요?",
                "card": "브라우저에서 강도·반경·임계값을 조절하는 언샤프 마스크. 전후 비교 포함.",
                "ui": {
                    "h2": "사진을 불러와 선명하게",
                    "intro": "처리는 이 페이지 안에서 이루어지며 파일은 전송되지 않습니다.",
                    "accept": "한 번에 한 장",
                    "l_amount": "강도", "l_radius": "반경", "l_threshold": "임계값",
                    "b_before": "원본 보기", "b_after": "적용본 보기",
                    "b_download": "PNG 저장",
                    "note": "선명화는 기존 경계의 대비를 올릴 뿐입니다. 흔들림이나 초점 실패는 어떤 도구로도 되돌릴 수 없습니다.",
                    "err_read": "이 브라우저에서 파일을 읽을 수 없습니다.",
                },
            },
            "de-DE": {
                "q": [("foto schärfen", "store-hint"), ("unscharfes bild verbessern", "store-hint")],
                "title": "Foto schärfen — kostenlose Unscharfmaskierung direkt im Browser",
                "description": "Echte Unscharfmaskierung mit Stärke, Radius und Schwellenwert, dazu Vorher/Nachher-Umschalter. Kein Upload, kein Wasserzeichen — und eine klare Ansage, was Schärfen nicht kann.",
                "h1": "Foto schärfen",
                "eyebrow": "Echte Unscharfmaskierung · Vorher/Nachher",
                "lead": "Dieselbe Rechnung, die Bildbearbeitungsprogramme verwenden, mit den drei Reglern, auf die es ankommt — und einer ehrlichen Angabe zu ihren Grenzen.",
                "badges": ["Stärke, Radius, Schwelle", "Vorher/Nachher", "Kein Upload", "PNG-Export"],
                "features": ["Unscharfmaskierung mit Stärke, Radius und Schwellenwert", "Sofortiger Vorher-Nachher-Vergleich", "Läuft komplett im Browser", "Verlustfreier PNG-Export"],
                "how": [
                    "Das Bild wird auf ein Canvas gezeichnet (längste Kante max. 1800 px) und seine Pixel ausgelesen.",
                    "Ein separabler Boxblur mit dem gewählten Radius liefert eine weiche Kopie; die Differenz zum Original ist die Detailebene.",
                    "Diese Detailebene wird mit der Stärke multipliziert und wieder addiert — die klassische Unscharfmaskierung. Der Schwellenwert überspringt kleine Differenzen, damit Himmel und Haut nicht körnig werden.",
                    "Exportiert wird PNG, damit die Schärfung nicht sofort von einer JPEG-Kompression wieder aufgefressen wird.",
                ],
                "never": [
                    "Es holt keine Details zurück, die nie aufgezeichnet wurden. Bewegungsunschärfe, danebenliegender Fokus und starkes Hochskalieren sind verlorene Information.",
                    "Keine KI, keine erfundenen Pixel. Nur Arithmetik auf Ihren eigenen Bildpunkten.",
                    "Nichts wird hochgeladen — das Bild verlässt den Tab nicht.",
                ],
                "faq": [
                    ("Rettet das ein unscharfes Foto?", "Nein, und kein ehrlicher Schärfefilter tut das. Fehlfokus und Bewegungsunschärfe zerstören Information. Unscharfmaskierung erhöht den Kontrast an vorhandenen Kanten — ein leicht weiches Bild wirkt dann knackiger."),
                    ("Was machen die drei Regler?", "Die Stärke bestimmt, wie kräftig die Detailebene zurückkommt. Der Radius bestimmt die Breite des Kantensaums. Der Schwellenwert ignoriert kleine Differenzen, damit Rauschen und glatte Flächen glatt bleiben."),
                    ("Woher kommen die hellen Ränder?", "Das ist Überschärfung: zu viel Stärke bei zu großem Radius. Erst die Stärke reduzieren, dann den Radius. Der Vorher/Nachher-Knopf macht es sichtbar."),
                ],
                "app_heading": "Schärfen Sie öfter Fotos auf dem iPhone?",
                "card": "Unscharfmaskierung im Browser mit Stärke, Radius, Schwelle und Vorher/Nachher.",
                "ui": {
                    "h2": "Foto laden und schärfen",
                    "intro": "Die Verarbeitung passiert auf dieser Seite; die Datei wird nie hochgeladen.",
                    "accept": "Ein Bild pro Durchgang",
                    "l_amount": "Stärke", "l_radius": "Radius", "l_threshold": "Schwellenwert",
                    "b_before": "Original zeigen", "b_after": "Geschärft zeigen",
                    "b_download": "PNG herunterladen",
                    "note": "Schärfen erhöht den Kontrast an vorhandenen Kanten. Bewegungsunschärfe oder Fehlfokus kann es nicht rückgängig machen — kein Werkzeug kann das.",
                    "err_read": "Diese Datei konnte vom Browser nicht dekodiert werden.",
                },
            },
        },
    })
    return spec


# ---------------------------------------------------------- 8. film filter

FILM_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="filedrop"><input type="file" id="file" accept="image/*"> <span class="small">{ui[accept]}</span></div>
<div class="controls" style="margin-top:16px">
<div class="field"><label for="look">{ui[l_look]}</label><select id="look">
<option value="warmfade">{ui[k_warmfade]}</option><option value="coolmatte">{ui[k_coolmatte]}</option>
<option value="goldhour">{ui[k_goldhour]}</option><option value="mono">{ui[k_mono]}</option>
<option value="crossprocess">{ui[k_cross]}</option></select></div>
<div class="field"><label for="str">{ui[l_strength]} · <span id="sv">70</span>%</label><input type="range" id="str" min="0" max="100" value="70"></div>
<div class="field"><label for="grain">{ui[l_grain]} · <span id="gv">12</span></label><input type="range" id="grain" min="0" max="40" value="12"></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="vig">{ui[l_vignette]} · <span id="vv">25</span>%</label><input type="range" id="vig" min="0" max="70" value="25"></div>
<div class="field" style="align-self:end"><button class="button ghost" id="toggle" disabled>{ui[b_before]}</button></div>
<div class="field" style="align-self:end"><a class="button" id="dl" download>{ui[b_download]}</a></div>
</div>
<canvas class="stage" id="cv" style="margin-top:18px;display:none"></canvas>
<p class="note">{ui[note]}</p>
"""

FILM_JS = r"""
var $=function(i){return document.getElementById(i);};
var img=null,url='',base=null,W=0,H=0,showing='after';
var LOOKS={
 warmfade:{r:[1.06,10],g:[1.00,6],b:[0.92,14],sat:0.92,lift:12},
 coolmatte:{r:[0.94,6],g:[1.00,8],b:[1.10,10],sat:0.88,lift:16},
 goldhour:{r:[1.14,6],g:[1.02,2],b:[0.86,0],sat:1.10,lift:4},
 mono:{r:[1,0],g:[1,0],b:[1,0],sat:0,lift:6,contrast:1.12},
 crossprocess:{r:[1.10,0],g:[0.98,10],b:[1.16,0],sat:1.25,lift:0,contrast:1.18}};
function grade(src,w,h,key,strength,grain,vig){
  var K=LOOKS[key],out=new Uint8ClampedArray(src.length);
  var cx=w/2,cy=h/2,maxd=Math.sqrt(cx*cx+cy*cy),con=K.contrast||1;
  for(var i=0,p=0;i<src.length;i+=4,p++){
    var r=src[i],g=src[i+1],b=src[i+2];
    var lum=0.2126*r+0.7152*g+0.0722*b;
    var nr=r*K.r[0]+K.r[1],ng=g*K.g[0]+K.g[1],nb=b*K.b[0]+K.b[1];
    nr=lum+(nr-lum)*K.sat;ng=lum+(ng-lum)*K.sat;nb=lum+(nb-lum)*K.sat;
    nr=(nr-128)*con+128+K.lift;ng=(ng-128)*con+128+K.lift;nb=(nb-128)*con+128+K.lift;
    nr=r+(nr-r)*strength;ng=g+(ng-g)*strength;nb=b+(nb-b)*strength;
    if(grain>0){var n=(Math.random()-0.5)*grain;nr+=n;ng+=n;nb+=n;}
    if(vig>0){var x=p%w,y=(p-x)/w;
      var d=Math.sqrt((x-cx)*(x-cx)+(y-cy)*(y-cy))/maxd;
      var f=1-vig*Math.pow(d,2.2);nr*=f;ng*=f;nb*=f;}
    out[i]=nr;out[i+1]=ng;out[i+2]=nb;out[i+3]=src[i+3];}
  return out;}
function apply(){
  if(!base)return;
  var cv=$('cv'),cx=cv.getContext('2d');
  if(showing==='before'){cx.putImageData(new ImageData(new Uint8ClampedArray(base),W,H),0,0);}
  else{
    var out=grade(base,W,H,$('look').value,
      parseInt($('str').value,10)/100,parseInt($('grain').value,10),
      parseInt($('vig').value,10)/100);
    cx.putImageData(new ImageData(out,W,H),0,0);}
  cv.toBlob(function(b){var a=$('dl');
    if(a.dataset.blob)URL.revokeObjectURL(a.href);
    a.href=URL.createObjectURL(b);a.dataset.blob='1';
    a.download=$('look').value+'.jpg';},'image/jpeg',0.92);}
$('file').addEventListener('change',function(){
  var f=$('file').files[0];if(!f)return;
  if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(f);
  img=new Image();
  img.onload=function(){
    var MAX=1800,s=Math.min(1,MAX/Math.max(img.naturalWidth,img.naturalHeight));
    W=Math.round(img.naturalWidth*s);H=Math.round(img.naturalHeight*s);
    var cv=$('cv');cv.width=W;cv.height=H;cv.style.display='block';
    var cx=cv.getContext('2d');cx.drawImage(img,0,0,W,H);
    base=cx.getImageData(0,0,W,H).data;
    $('toggle').disabled=false;showing='after';apply();};
  img.onerror=function(){alert(L.err_read);};img.src=url;});
[['look','change'],['str','input'],['grain','input'],['vig','input']].forEach(function(p){
  $(p[0]).addEventListener(p[1],function(){
    if(p[0]==='str')$('sv').textContent=$('str').value;
    if(p[0]==='grain')$('gv').textContent=$('grain').value;
    if(p[0]==='vig')$('vv').textContent=$('vig').value;
    showing='after';apply();});});
$('toggle').addEventListener('click',function(){
  showing=showing==='after'?'before':'after';
  $('toggle').textContent=showing==='after'?L.b_before:L.b_after;apply();});
"""

_PHOTOCREAM_APP = {"app_key": "photocream", "app_id": "6781808054", "app_name": "PhotoCream",
                   "category": "PhotoApplication"}


def spec_film_filter():
    spec = dict(_PHOTOCREAM_APP)
    spec.update({
        "slug": "film-photo-filter",
        "body": FILM_BODY,
        "script": FILM_JS,
        "i18n": {
            "en": {
                "q": [("vintage photo filter", "D2"), ("photo editor app", "store-hint")],
                "title": "Film Photo Filter — Free Vintage Looks With Grain and Vignette, In Your Browser",
                "description": "Five film-style colour looks with adjustable strength, grain and vignette, applied to your own pixels in the browser. Before/after toggle, JPEG export, no upload and no watermark.",
                "h1": "Film photo filter",
                "eyebrow": "Real colour grading · adjustable grain",
                "lead": "Five looks built from actual channel curves rather than a flat colour overlay — with strength, grain and vignette on separate sliders so you can stop before it becomes a costume.",
                "badges": ["5 film looks", "Grain and vignette", "Before/after", "No watermark"],
                "features": ["Five channel-curve based film looks", "Independent strength, grain and vignette", "Before/after comparison", "JPEG export at quality 0.92"],
                "how": [
                    "Each look is a set of per-channel gain and lift values plus saturation and contrast — the same shape as a simple film emulation curve, not a coloured layer pasted on top.",
                    "Strength blends the graded result back towards your original, so 40% is genuinely half as strong as 80%.",
                    "Grain adds the same random offset to all three channels, which is how film grain behaves; colour noise looks like a broken sensor instead.",
                    "The vignette darkens by distance from the centre on a squared falloff, so it stays smooth rather than showing a ring.",
                ],
                "never": [
                    "It does not claim to be a specific film stock. These are looks inspired by film characteristics, not measured emulations of a named emulsion.",
                    "Nothing is uploaded. Your photo is decoded, graded and exported inside the tab.",
                    "No watermark, no export limit, no account.",
                ],
                "faq": [
                    ("Is this a real film emulation?", "No, and it does not claim to be. A measured emulation needs the actual response curves of a named film stock. These are five plausible looks made from channel gains, lift, saturation and contrast — honest colour grading, not a copy of a specific stock."),
                    ("Why is the grain grey rather than colourful?", "Because real film grain moves all three channels together. Independent per-channel noise reads as sensor noise, which is exactly the thing people are trying to get away from."),
                    ("Does it reduce quality?", "Export is JPEG at quality 0.92 from a copy capped at 1800 px on the long edge. Your original file is untouched, so you can always go back."),
                ],
                "app_heading": "Want these looks on the photos you take?",
                "card": "Five film-style looks with adjustable strength, grain and vignette, applied in your browser.",
                "ui": {
                    "h2": "Load a photo and pick a look",
                    "intro": "Grading happens on this page; the file is never uploaded.",
                    "accept": "One image at a time",
                    "l_look": "Look", "k_warmfade": "Warm fade", "k_coolmatte": "Cool matte",
                    "k_goldhour": "Golden hour", "k_mono": "Monochrome", "k_cross": "Cross process",
                    "l_strength": "Strength", "l_grain": "Grain", "l_vignette": "Vignette",
                    "b_before": "Show original", "b_after": "Show graded",
                    "b_download": "Download JPEG",
                    "note": "These are looks inspired by film characteristics — not measured emulations of any named film stock.",
                    "err_read": "That file could not be decoded by this browser.",
                },
            },
            "de-DE": {
                "q": [("foto filter app", "store-hint"), ("vintage filter app", "store-hint")],
                "title": "Foto-Filter im Vintage-Look — kostenlos im Browser, mit Korn und Vignette",
                "description": "Fünf filmähnliche Farblooks mit einstellbarer Stärke, Korn und Vignette, direkt auf Ihre Pixel angewendet. Vorher/Nachher, JPEG-Export, kein Upload, kein Wasserzeichen.",
                "h1": "Foto-Filter im Filmlook",
                "eyebrow": "Echte Farbbearbeitung · einstellbares Korn",
                "lead": "Fünf Looks aus echten Kanalkurven statt einer bunten Farbfläche — Stärke, Korn und Vignette getrennt regelbar, damit es nicht in Kostüm umschlägt.",
                "badges": ["5 Filmlooks", "Korn und Vignette", "Vorher/Nachher", "Kein Wasserzeichen"],
                "features": ["Fünf Looks auf Basis von Kanalkurven", "Stärke, Korn und Vignette unabhängig", "Vorher-Nachher-Vergleich", "JPEG-Export mit Qualität 0,92"],
                "how": [
                    "Jeder Look besteht aus Kanalverstärkung und Anhebung plus Sättigung und Kontrast — die Form einer einfachen Filmemulation, keine aufgeklebte Farbebene.",
                    "Die Stärke blendet das Ergebnis zurück Richtung Original, 40 % ist also wirklich halb so stark wie 80 %.",
                    "Das Korn addiert denselben Zufallswert auf alle drei Kanäle, so verhält sich Filmkorn; kanalweises Rauschen sieht dagegen nach defektem Sensor aus.",
                    "Die Vignette dunkelt nach Abstand zur Mitte mit quadratischem Verlauf ab und bleibt dadurch weich statt ringförmig.",
                ],
                "never": [
                    "Es behauptet nicht, ein bestimmter Filmtyp zu sein. Das sind von Filmeigenschaften inspirierte Looks, keine vermessenen Emulationen einer benannten Emulsion.",
                    "Nichts wird hochgeladen. Ihr Foto wird im Tab dekodiert, bearbeitet und exportiert.",
                    "Kein Wasserzeichen, kein Exportlimit, kein Konto.",
                ],
                "faq": [
                    ("Ist das eine echte Filmemulation?", "Nein, und das wird auch nicht behauptet. Eine vermessene Emulation bräuchte die tatsächlichen Kennlinien eines benannten Films. Hier sind es fünf plausible Looks aus Kanalverstärkung, Anhebung, Sättigung und Kontrast."),
                    ("Warum ist das Korn grau und nicht bunt?", "Weil echtes Filmkorn alle drei Kanäle gemeinsam bewegt. Getrenntes Farbrauschen wirkt wie Sensorrauschen — genau das, wovon man wegwill."),
                    ("Verliert das Bild an Qualität?", "Exportiert wird JPEG mit Qualität 0,92 aus einer auf 1800 px längster Kante begrenzten Kopie. Ihre Originaldatei bleibt unangetastet."),
                ],
                "app_heading": "Diese Looks direkt beim Fotografieren?",
                "card": "Fünf Filmlooks mit einstellbarer Stärke, Korn und Vignette — im Browser angewendet.",
                "ui": {
                    "h2": "Foto laden und Look wählen",
                    "intro": "Die Bearbeitung läuft auf dieser Seite; die Datei wird nie hochgeladen.",
                    "accept": "Ein Bild pro Durchgang",
                    "l_look": "Look", "k_warmfade": "Warmes Fade", "k_coolmatte": "Kühl matt",
                    "k_goldhour": "Goldene Stunde", "k_mono": "Schwarzweiß", "k_cross": "Cross-Entwicklung",
                    "l_strength": "Stärke", "l_grain": "Korn", "l_vignette": "Vignette",
                    "b_before": "Original zeigen", "b_after": "Bearbeitet zeigen",
                    "b_download": "JPEG herunterladen",
                    "note": "Von Filmeigenschaften inspirierte Looks — keine vermessene Emulation eines konkreten Filmtyps.",
                    "err_read": "Diese Datei konnte vom Browser nicht dekodiert werden.",
                },
            },
        },
    })
    return spec


# --------------------------------------------------------- 9. redact to PDF

REDACT_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="filedrop"><input type="file" id="file" accept="image/*"> <span class="small">{ui[accept]}</span></div>
<div class="controls" style="margin-top:16px">
<div class="field"><label for="mode">{ui[l_mode]}</label><select id="mode">
<option value="black">{ui[m_black]}</option><option value="pixel">{ui[m_pixel]}</option></select></div>
<div class="field"><label for="px">{ui[l_block]} · <span id="pv">14</span> px</label><input type="range" id="px" min="6" max="40" value="14"></div>
<div class="field" style="align-self:end;display:flex;gap:8px">
<button class="button ghost" id="undo" disabled>{ui[b_undo]}</button>
<button class="button ghost" id="reset" disabled>{ui[b_reset]}</button></div>
</div>
<canvas class="stage" id="cv" style="margin-top:18px;display:none;cursor:crosshair"></canvas>
<div class="results">
<div class="result"><strong>{ui[r_areas]}</strong><span id="n">0</span></div>
<div class="result" style="grid-column:span 3"><strong>{ui[r_hint]}</strong><span id="hint">{ui[hint_wait]}</span></div>
</div>
<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
<button class="button" id="pdf" disabled>{ui[b_pdf]}</button>
<a class="button ghost" id="png" download>{ui[b_png]}</a></div>
<p class="note">{ui[note]}</p>
"""

REDACT_JS = r"""
var $=function(i){return document.getElementById(i);};
var img=null,url='',W=0,H=0,regions=[],drag=null;
var cv=$('cv');
function ctx2d(){return cv.getContext('2d');}
function pixelate(cx,x,y,w,h,size){
  var data=cx.getImageData(x,y,w,h);
  var d=data.data;
  for(var by=0;by<h;by+=size){
    for(var bx=0;bx<w;bx+=size){
      var r=0,g=0,b=0,n=0,px,py;
      for(py=by;py<Math.min(by+size,h);py++){
        for(px=bx;px<Math.min(bx+size,w);px++){
          var i=(py*w+px)*4;r+=d[i];g+=d[i+1];b+=d[i+2];n++;}}
      if(!n)continue;r=r/n;g=g/n;b=b/n;
      for(py=by;py<Math.min(by+size,h);py++){
        for(px=bx;px<Math.min(bx+size,w);px++){
          var j=(py*w+px)*4;d[j]=r;d[j+1]=g;d[j+2]=b;}}}}
  cx.putImageData(data,x,y);}
function redraw(preview){
  if(!img)return;
  var cx=ctx2d();
  cx.drawImage(img,0,0,W,H);
  var size=parseInt($('px').value,10);
  regions.forEach(function(r){
    if(r.mode==='pixel')pixelate(cx,r.x,r.y,r.w,r.h,size);
    else{cx.fillStyle='#000';cx.fillRect(r.x,r.y,r.w,r.h);}});
  if(preview){cx.strokeStyle='#c8922a';cx.lineWidth=2;
    cx.strokeRect(preview.x,preview.y,preview.w,preview.h);}
  $('n').textContent=String(regions.length);
  $('undo').disabled=!regions.length;
  $('reset').disabled=!regions.length;
  $('pdf').disabled=!img;
  updatePng();}
function updatePng(){
  cv.toBlob(function(b){
    var a=$('png');if(a.dataset.blob)URL.revokeObjectURL(a.href);
    a.href=URL.createObjectURL(b);a.dataset.blob='1';a.download='redacted.png';},'image/png');}
function norm(a,b){
  return {x:Math.round(Math.min(a.x,b.x)),y:Math.round(Math.min(a.y,b.y)),
    w:Math.round(Math.abs(a.x-b.x)),h:Math.round(Math.abs(a.y-b.y))};}
function pos(e){
  var r=cv.getBoundingClientRect();
  var t=e.touches&&e.touches[0]?e.touches[0]:e;
  return {x:(t.clientX-r.left)*(W/r.width),y:(t.clientY-r.top)*(H/r.height)};}
function addRegion(x,y,w,h){
  if(w<4||h<4)return false;
  regions.push({x:x,y:y,w:w,h:h,mode:$('mode').value});redraw();return true;}
cv.addEventListener('pointerdown',function(e){
  if(!img)return;drag={a:pos(e)};cv.setPointerCapture&&cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',function(e){
  if(!drag)return;var r=norm(drag.a,pos(e));redraw(r);});
cv.addEventListener('pointerup',function(e){
  if(!drag)return;var r=norm(drag.a,pos(e));drag=null;
  if(!addRegion(r.x,r.y,r.w,r.h))redraw();});
$('undo').addEventListener('click',function(){regions.pop();redraw();});
$('reset').addEventListener('click',function(){regions=[];redraw();});
$('mode').addEventListener('change',function(){redraw();});
$('px').addEventListener('input',function(){$('pv').textContent=$('px').value;redraw();});
$('file').addEventListener('change',function(){
  var f=$('file').files[0];if(!f)return;
  if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(f);
  img=new Image();
  img.onload=function(){
    var MAX=2000,s=Math.min(1,MAX/Math.max(img.naturalWidth,img.naturalHeight));
    W=Math.round(img.naturalWidth*s);H=Math.round(img.naturalHeight*s);
    cv.width=W;cv.height=H;cv.style.display='block';
    regions=[];$('hint').textContent=L.hint_ready;redraw();};
  img.onerror=function(){alert(L.err_read);};img.src=url;});
function buildPdf(bytes,w,h){
  var enc=new TextEncoder(),parts=[],offsets=[],pos=0;
  function push(x){var b=typeof x==='string'?enc.encode(x):x;parts.push(b);pos+=b.length;}
  function obj(id,body){offsets[id]=pos;push(id+' 0 obj\n'+body+'\nendobj\n');}
  push('%PDF-1.4\n');
  var pw=595.28,ph=841.89,margin=24;
  var availW=pw-2*margin,availH=ph-2*margin;
  var s=Math.min(availW/w,availH/h),dw=w*s,dh=h*s,dx=(pw-dw)/2,dy=(ph-dh)/2;
  obj(1,'<< /Type /Catalog /Pages 2 0 R >>');
  obj(2,'<< /Type /Pages /Kids [5 0 R] /Count 1 >>');
  offsets[3]=pos;
  push('3 0 obj\n<< /Type /XObject /Subtype /Image /Width '+w+' /Height '+h
    +' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '
    +bytes.length+' >>\nstream\n');
  push(bytes);push('\nendstream\nendobj\n');
  var content='q '+dw.toFixed(2)+' 0 0 '+dh.toFixed(2)+' '+dx.toFixed(2)+' '+dy.toFixed(2)+' cm /Im0 Do Q';
  obj(4,'<< /Length '+content.length+' >>\nstream\n'+content+'\nendstream');
  obj(5,'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '+pw.toFixed(2)+' '+ph.toFixed(2)
    +'] /Resources << /XObject << /Im0 3 0 R >> >> /Contents 4 0 R >>');
  var total=6,xref=pos,table='xref\n0 '+total+'\n0000000000 65535 f \n';
  for(var id=1;id<total;id++)table+=String(offsets[id]).padStart(10,'0')+' 00000 n \n';
  push(table+'trailer\n<< /Size '+total+' /Root 1 0 R >>\nstartxref\n'+xref+'\n%%EOF');
  return new Blob(parts,{type:'application/pdf'});}
$('pdf').addEventListener('click',function(){
  if(!img)return;
  redraw();
  cv.toBlob(function(b){
    b.arrayBuffer().then(function(buf){
      var pdf=buildPdf(new Uint8Array(buf),W,H);
      var a=document.createElement('a');a.href=URL.createObjectURL(pdf);
      a.download='redacted.pdf';a.click();
      setTimeout(function(){URL.revokeObjectURL(a.href);},5000);});},'image/jpeg',0.92);});
"""

_MASK_APP = {"app_key": "maskmyfile", "app_id": "6792850916", "app_name": "Mask My File",
             "category": "UtilitiesApplication"}


def spec_redact_pdf():
    spec = dict(_MASK_APP)
    spec.update({
        "slug": "redact-to-pdf",
        "body": REDACT_BODY,
        "script": REDACT_JS,
        "i18n": {
            "en": {
                "q": [("redact pdf", "D2"), ("black out text", "store-hint")],
                "title": "Redact and Export to PDF — Free, Pixels Really Removed, No Upload",
                "description": "Drag boxes over a scan or screenshot to black out or pixelate it, then export a flattened PDF or PNG. The covered pixels are genuinely destroyed before export — nothing is uploaded.",
                "h1": "Redact a document to PDF",
                "eyebrow": "Pixels destroyed, not covered · flattened export",
                "lead": "Drawing a black rectangle in a PDF viewer leaves the text sitting underneath it. This flattens the image first, so what you blacked out is actually gone from the file you share.",
                "badges": ["Black out or pixelate", "Flattened PDF export", "No upload", "PNG export too"],
                "features": ["Drag-to-select redaction areas", "Solid black or pixelate mode", "Flattened single-page PDF export", "Undo and reset, all in the browser"],
                "how": [
                    "Your image is drawn on a canvas at up to 2000 px on the long edge. Every redaction is repainted onto those pixels, not stored as a separate layer.",
                    "Black mode fills the rectangle with solid black. Pixelate averages each block and writes the average back, so no original values survive inside the area.",
                    "Export re-encodes the finished canvas as JPEG and wraps it in a minimal one-page PDF written by this page — the PDF contains only the flattened image.",
                    "Undo removes the last area and repaints from the original, so mistakes cost nothing.",
                ],
                "never": [
                    "It cannot open a PDF. Browsers cannot render PDF pages without an external library, and this page loads no external code. Export or screenshot the page as an image first — which is also what makes the redaction safe.",
                    "It does not remove metadata from your source file, because it never reads it; the export is a fresh canvas render.",
                    "Nothing is uploaded, and no copy is kept when you close the tab.",
                ],
                "faq": [
                    ("Why is drawing a black box in a PDF editor unsafe?", "Because most editors add the rectangle as a new object on top. The original text is still in the file and can be selected, copied or extracted. Flattening to an image, as this page does, removes it for real."),
                    ("Black out or pixelate — which is safer?", "Solid black. Pixelation with a small block size can sometimes be attacked when the underlying content is predictable, such as a short number. For anything sensitive use black."),
                    ("Can I redact several pages?", "One image per pass, exported as a one-page PDF. For multi-page documents, redact each page and then combine them with the JPG-to-PDF tool listed below."),
                ],
                "app_heading": "Redacting files on iPhone regularly?",
                "card": "Black out or pixelate a scan and export a flattened PDF — the hidden pixels are really gone.",
                "ui": {
                    "h2": "Load a scan, drag over what must go",
                    "intro": "Everything happens on this page. The file is never uploaded.",
                    "accept": "Scan, photo or screenshot",
                    "l_mode": "Redaction style", "m_black": "Solid black", "m_pixel": "Pixelate",
                    "l_block": "Block size", "b_undo": "Undo", "b_reset": "Reset",
                    "r_areas": "Areas", "r_hint": "Next step",
                    "hint_wait": "Choose an image to start",
                    "hint_ready": "Drag on the image to cover an area",
                    "b_pdf": "Download flattened PDF", "b_png": "Download PNG",
                    "note": "Redaction is applied to the pixels before export. Solid black is the safest option for anything genuinely sensitive.",
                    "err_read": "That file could not be decoded by this browser.",
                },
            },
            "ja": {
                "q": [("pdf 黒塗り", "store-hint"), ("モザイク", "D3")],
                "title": "黒塗りして PDF で書き出す — 無料・ピクセルごと消える・アップロードなし",
                "description": "スキャンやスクリーンショットの上をドラッグして黒塗り／モザイクをかけ、統合済みの PDF または PNG で書き出します。隠した部分は書き出し前に本当に消えます。",
                "h1": "書類を黒塗りして PDF にする",
                "eyebrow": "覆うのではなく消す · 統合して書き出し",
                "lead": "PDF ビューアで黒い四角を描いても、その下の文字はファイルに残ります。ここでは先に画像として統合するので、隠した内容は共有するファイルから実際に消えます。",
                "badges": ["黒塗り／モザイク", "統合済み PDF 書き出し", "アップロードなし", "PNG でも保存可"],
                "features": ["ドラッグで範囲を指定", "べた塗りとモザイクの2方式", "1ページの統合済み PDF を書き出し", "元に戻す・全消去、すべてブラウザ内"],
                "how": [
                    "画像を canvas に描き（長辺 2000 px まで）、黒塗りはそのピクセルに直接描き込みます。別レイヤーとしては保持しません。",
                    "べた塗りは範囲を黒で塗りつぶし、モザイクはブロックごとに平均色を計算して書き戻すため、範囲内に元の値は残りません。",
                    "書き出しでは完成した canvas を JPEG に再エンコードし、このページが生成する最小限の1ページ PDF に埋め込みます。PDF の中身は統合済みの画像だけです。",
                    "「元に戻す」は最後の範囲を取り消して元画像から描き直すので、やり直しは無料です。",
                ],
                "never": [
                    "PDF を直接開くことはできません。ブラウザは外部ライブラリなしに PDF を描画できず、このページは外部コードを一切読み込みません。先に画像として書き出すかスクリーンショットを撮ってください（それ自体が安全な黒塗りの条件でもあります）。",
                    "元ファイルのメタデータは削除しません。そもそも読み取っておらず、書き出しは canvas からの新規レンダリングです。",
                    "アップロードしません。タブを閉じれば何も残りません。",
                ],
                "faq": [
                    ("PDF 編集ソフトで黒い四角を描くのはなぜ危険ですか？", "多くのソフトは四角を「上に置くオブジェクト」として追加するだけで、元の文字はファイル内に残り、選択・コピー・抽出できてしまうからです。このページのように画像へ統合すれば本当に消えます。"),
                    ("べた塗りとモザイクはどちらが安全ですか？", "べた塗りです。ブロックが小さいモザイクは、隠した内容が短い数字などで推測しやすい場合に復元されることがあります。機密情報にはべた塗りを使ってください。"),
                    ("複数ページをまとめて処理できますか？", "1回につき1枚、1ページの PDF として書き出します。複数ページの場合は各ページを処理してから、下に挙げた JPG→PDF ツールで結合してください。"),
                ],
                "app_heading": "iPhone でよく黒塗りしますか？",
                "card": "スキャンを黒塗り／モザイクして統合済み PDF に。隠した部分は本当に消えます。",
                "ui": {
                    "h2": "画像を読み込み、消したい所をドラッグ",
                    "intro": "処理はすべてこのページ内で行われ、ファイルは送信されません。",
                    "accept": "スキャン・写真・スクリーンショット",
                    "l_mode": "隠し方", "m_black": "黒でべた塗り", "m_pixel": "モザイク",
                    "l_block": "ブロックの大きさ", "b_undo": "元に戻す", "b_reset": "全消去",
                    "r_areas": "範囲の数", "r_hint": "次の操作",
                    "hint_wait": "画像を選んでください",
                    "hint_ready": "画像の上をドラッグして範囲を指定",
                    "b_pdf": "統合済み PDF を保存", "b_png": "PNG を保存",
                    "note": "黒塗りは書き出し前にピクセルへ適用されます。本当に機密性の高いものはべた塗りが最も安全です。",
                    "err_read": "このブラウザではこのファイルを読み込めませんでした。",
                },
            },
            "ko": {
                "q": [("pdf 마스킹", "store-hint"), ("사진 모자이크", "store-hint")],
                "title": "가리고 PDF로 저장 — 무료, 픽셀까지 실제로 삭제, 업로드 없음",
                "description": "스캔이나 스크린숏 위를 드래그해 검게 칠하거나 모자이크한 뒤 병합된 PDF 또는 PNG로 저장합니다. 가린 픽셀은 저장 전에 실제로 사라집니다.",
                "h1": "문서를 가리고 PDF로",
                "eyebrow": "덮는 것이 아니라 지움 · 병합 저장",
                "lead": "PDF 뷰어에서 검은 사각형을 그려도 그 아래 글자는 파일에 그대로 남습니다. 여기서는 먼저 이미지로 병합하므로 가린 내용이 공유 파일에서 실제로 사라집니다.",
                "badges": ["검게 칠하기 / 모자이크", "병합된 PDF 저장", "업로드 없음", "PNG 저장도 가능"],
                "features": ["드래그로 영역 지정", "단색 검정과 모자이크 두 방식", "1페이지 병합 PDF 저장", "실행 취소·초기화, 모두 브라우저에서"],
                "how": [
                    "이미지를 캔버스에 그리고(긴 변 최대 2000 px) 가림 처리를 그 픽셀에 직접 칠합니다. 별도 레이어로 두지 않습니다.",
                    "검정 모드는 영역을 단색으로 채우고, 모자이크는 블록마다 평균색을 계산해 다시 씁니다. 영역 안에 원래 값은 남지 않습니다.",
                    "저장 시 완성된 캔버스를 JPEG로 다시 인코딩하고, 이 페이지가 만드는 최소 크기의 1페이지 PDF에 넣습니다. PDF에는 병합된 이미지만 들어갑니다.",
                    "실행 취소는 마지막 영역을 없애고 원본에서 다시 그립니다.",
                ],
                "never": [
                    "PDF를 직접 열 수 없습니다. 브라우저는 외부 라이브러리 없이 PDF를 그릴 수 없고, 이 페이지는 외부 코드를 전혀 불러오지 않습니다. 먼저 이미지로 내보내거나 스크린숏을 찍으세요 — 그 자체가 안전한 가림의 조건이기도 합니다.",
                    "원본 파일의 메타데이터를 지우지 않습니다. 애초에 읽지 않으며, 저장물은 캔버스에서 새로 렌더링한 것입니다.",
                    "업로드하지 않고, 탭을 닫으면 아무것도 남지 않습니다.",
                ],
                "faq": [
                    ("PDF 편집기에서 검은 사각형을 그리면 왜 위험한가요?", "대부분의 편집기는 사각형을 위에 얹는 객체로 추가할 뿐이라 원래 글자가 파일에 남아 선택·복사·추출될 수 있기 때문입니다. 이 페이지처럼 이미지로 병합하면 실제로 지워집니다."),
                    ("검정과 모자이크 중 무엇이 안전한가요?", "단색 검정입니다. 블록이 작은 모자이크는 가린 내용이 짧은 숫자처럼 예측 가능할 때 복원될 수 있습니다. 민감한 내용에는 검정을 쓰세요."),
                    ("여러 장을 한 번에 처리할 수 있나요?", "한 번에 한 장, 1페이지 PDF로 저장합니다. 여러 페이지는 각각 처리한 뒤 아래의 JPG→PDF 도구로 합치세요."),
                ],
                "app_heading": "아이폰에서 문서를 자주 가리나요?",
                "card": "스캔을 검게 칠하거나 모자이크해 병합된 PDF로 저장 — 가린 픽셀은 실제로 사라집니다.",
                "ui": {
                    "h2": "이미지를 불러오고 가릴 부분을 드래그",
                    "intro": "모든 처리는 이 페이지에서 이루어지며 파일은 전송되지 않습니다.",
                    "accept": "스캔, 사진 또는 스크린숏",
                    "l_mode": "가리는 방식", "m_black": "단색 검정", "m_pixel": "모자이크",
                    "l_block": "블록 크기", "b_undo": "실행 취소", "b_reset": "초기화",
                    "r_areas": "영역 수", "r_hint": "다음 단계",
                    "hint_wait": "이미지를 선택하세요",
                    "hint_ready": "이미지 위를 드래그해 영역을 지정하세요",
                    "b_pdf": "병합된 PDF 저장", "b_png": "PNG 저장",
                    "note": "가림 처리는 저장 전에 픽셀에 적용됩니다. 정말 민감한 내용에는 단색 검정이 가장 안전합니다.",
                    "err_read": "이 브라우저에서 파일을 읽을 수 없습니다.",
                },
            },
            "de-DE": {
                "q": [("pdf schwärzen", "store-hint"), ("blur photo", "store-hint")],
                "title": "Schwärzen und als PDF exportieren — kostenlos, Pixel wirklich entfernt, ohne Upload",
                "description": "Bereiche auf einem Scan oder Screenshot per Ziehen schwärzen oder verpixeln und als flach gerechnetes PDF oder PNG speichern. Die verdeckten Pixel sind vor dem Export tatsächlich weg.",
                "h1": "Dokument schwärzen und als PDF speichern",
                "eyebrow": "Pixel entfernt statt überdeckt · flach exportiert",
                "lead": "Ein schwarzes Rechteck im PDF-Viewer lässt den Text darunter in der Datei stehen. Hier wird zuerst auf ein Bild flach gerechnet — das Geschwärzte ist aus der geteilten Datei wirklich verschwunden.",
                "badges": ["Schwärzen oder verpixeln", "Flaches PDF", "Kein Upload", "Auch PNG"],
                "features": ["Bereiche per Ziehen markieren", "Deckendes Schwarz oder Verpixeln", "Einseitiges, flach gerechnetes PDF", "Rückgängig und Zurücksetzen, alles im Browser"],
                "how": [
                    "Das Bild wird auf ein Canvas gezeichnet (längste Kante max. 2000 px). Jede Schwärzung wird direkt in diese Pixel gemalt, nicht als eigene Ebene abgelegt.",
                    "Der Schwarz-Modus füllt das Rechteck deckend. Verpixeln mittelt jeden Block und schreibt den Mittelwert zurück — im Bereich überlebt kein Originalwert.",
                    "Beim Export wird das fertige Canvas als JPEG kodiert und in ein minimales einseitiges PDF gepackt, das diese Seite selbst schreibt. Im PDF steht nur das flache Bild.",
                    "Rückgängig entfernt den letzten Bereich und zeichnet vom Original neu.",
                ],
                "never": [
                    "Es kann keine PDF-Datei öffnen. Browser rendern PDF-Seiten nicht ohne externe Bibliothek, und diese Seite lädt keinerlei externen Code. Exportieren Sie die Seite vorher als Bild — genau das macht die Schwärzung überhaupt erst sicher.",
                    "Es entfernt keine Metadaten aus Ihrer Quelldatei, denn es liest sie gar nicht; der Export ist ein frisch gerendertes Canvas.",
                    "Nichts wird hochgeladen, und beim Schließen des Tabs bleibt keine Kopie zurück.",
                ],
                "faq": [
                    ("Warum ist ein schwarzes Rechteck im PDF-Editor unsicher?", "Weil die meisten Editoren das Rechteck als zusätzliches Objekt darüberlegen. Der ursprüngliche Text bleibt in der Datei und lässt sich markieren, kopieren oder extrahieren. Das Flachrechnen auf ein Bild entfernt ihn wirklich."),
                    ("Schwärzen oder verpixeln?", "Deckendes Schwarz. Verpixeln mit kleiner Blockgröße kann angegriffen werden, wenn der Inhalt vorhersagbar ist, etwa eine kurze Zahl. Für Sensibles gilt: schwarz."),
                    ("Mehrere Seiten auf einmal?", "Ein Bild pro Durchgang, als einseitiges PDF. Bei mehrseitigen Dokumenten jede Seite bearbeiten und anschließend mit dem unten verlinkten JPG-zu-PDF-Tool zusammenführen."),
                ],
                "app_heading": "Schwärzen Sie öfter Dateien auf dem iPhone?",
                "card": "Scan schwärzen oder verpixeln und als flach gerechnetes PDF speichern.",
                "ui": {
                    "h2": "Scan laden, über den Bereich ziehen",
                    "intro": "Alles läuft auf dieser Seite. Die Datei wird nie hochgeladen.",
                    "accept": "Scan, Foto oder Screenshot",
                    "l_mode": "Art der Schwärzung", "m_black": "Deckendes Schwarz", "m_pixel": "Verpixeln",
                    "l_block": "Blockgröße", "b_undo": "Rückgängig", "b_reset": "Zurücksetzen",
                    "r_areas": "Bereiche", "r_hint": "Nächster Schritt",
                    "hint_wait": "Wählen Sie ein Bild",
                    "hint_ready": "Auf dem Bild ziehen, um einen Bereich abzudecken",
                    "b_pdf": "Flaches PDF herunterladen", "b_png": "PNG herunterladen",
                    "note": "Die Schwärzung wird vor dem Export auf die Pixel angewendet. Für wirklich Sensibles ist deckendes Schwarz die sichere Wahl.",
                    "err_read": "Diese Datei konnte vom Browser nicht dekodiert werden.",
                },
            },
            "zh-Hant": {
                "q": [("照片馬賽克", "D3"), ("文件 遮蔽", "store-hint")],
                "title": "遮蔽後輸出 PDF — 免費、像素真的被清掉、不上傳",
                "description": "在掃描檔或截圖上拖曳出要遮的區域，塗黑或打馬賽克後輸出已壓平的 PDF 或 PNG。被遮住的像素在輸出前就已經真的消失。",
                "h1": "文件遮蔽並輸出 PDF",
                "eyebrow": "是清掉不是蓋住 · 壓平輸出",
                "lead": "在 PDF 閱讀器裡畫一個黑框，底下的文字仍然留在檔案裡。這裡會先壓平成影像，所以你遮掉的內容真的不在你分享出去的檔案裡。",
                "badges": ["塗黑或馬賽克", "壓平的 PDF", "不上傳", "也能存 PNG"],
                "features": ["拖曳選取遮蔽區域", "純黑與馬賽克兩種方式", "輸出單頁壓平 PDF", "可復原與重設，全在瀏覽器"],
                "how": [
                    "影像會畫在 canvas 上（長邊最多 2000 px），每個遮蔽都直接畫進那些像素，不會另存成圖層。",
                    "純黑模式把區域整個填黑；馬賽克模式逐格計算平均色再寫回去，區域內不會留下任何原始數值。",
                    "輸出時把完成的 canvas 重新編碼成 JPEG，再包進本頁自行產生的最小單頁 PDF，PDF 裡只有那張壓平的影像。",
                    "「復原」會移除最後一個區域並從原圖重畫，畫錯不用重來。",
                ],
                "never": [
                    "無法直接開啟 PDF。瀏覽器沒有外部函式庫就無法繪製 PDF 頁面，而本頁完全不載入外部程式。請先把檔案輸出成影像或截圖——這件事本身也正是遮蔽能安全的前提。",
                    "不會移除來源檔的中繼資料，因為根本沒有讀它；輸出的是重新繪製的 canvas。",
                    "不上傳，關掉分頁後不留任何副本。",
                ],
                "faq": [
                    ("為什麼在 PDF 編輯器畫黑框不安全？", "因為多數編輯器只是把黑框當成疊在上面的物件加進去，原本的文字仍在檔案裡，可以被選取、複製或抽取出來。像本頁這樣壓平成影像才是真的刪掉。"),
                    ("塗黑和馬賽克哪個安全？", "純黑。格子太小的馬賽克，在被遮內容可預測（例如一組短數字）時有機會被還原。敏感資料請用純黑。"),
                    ("可以一次處理多頁嗎？", "一次一張，輸出單頁 PDF。多頁文件請逐頁處理，再用下面的 JPG 轉 PDF 工具合併。"),
                ],
                "app_heading": "常常需要在 iPhone 上遮蔽檔案嗎？",
                "card": "把掃描檔塗黑或打馬賽克並輸出壓平的 PDF，被遮的像素真的消失。",
                "ui": {
                    "h2": "載入影像，拖曳出要遮掉的地方",
                    "intro": "全部在這個頁面完成，檔案不會上傳。",
                    "accept": "掃描檔、照片或截圖",
                    "l_mode": "遮蔽方式", "m_black": "純黑填滿", "m_pixel": "馬賽克",
                    "l_block": "格子大小", "b_undo": "復原", "b_reset": "全部清除",
                    "r_areas": "區域數", "r_hint": "下一步",
                    "hint_wait": "請先選一張影像",
                    "hint_ready": "在影像上拖曳出要遮蔽的範圍",
                    "b_pdf": "下載壓平的 PDF", "b_png": "下載 PNG",
                    "note": "遮蔽是在輸出前直接套用到像素上。真正敏感的內容請使用純黑填滿。",
                    "err_read": "這個瀏覽器無法讀取這個檔案。",
                },
            },
        },
    })
    return spec


# ------------------------------------------------------ 10. math worksheet

WORKSHEET_CSS = """
.sheet{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:18px}
.sheet h3{margin:0 0 4px;font-family:ui-serif,Georgia,serif}
.probs{display:grid;grid-template-columns:repeat(var(--cols,3),minmax(0,1fr));gap:14px 22px;margin-top:14px}
.prob{font-size:19px;font-variant-numeric:tabular-nums;border-bottom:1px solid #e4d7bd;padding:6px 2px}
.prob i{font-style:normal;color:#b09258}
.key{margin-top:16px;font-size:14px;color:var(--muted);column-count:3;column-gap:20px}
@media(max-width:640px){.probs{grid-template-columns:repeat(2,minmax(0,1fr))}.key{column-count:2}}
"""

WORKSHEET_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label>{ui[l_ops]}</label>
<label class="small"><input type="checkbox" id="op_add" style="width:auto" checked> {ui[o_add]}</label>
<label class="small"><input type="checkbox" id="op_sub" style="width:auto" checked> {ui[o_sub]}</label>
<label class="small"><input type="checkbox" id="op_mul" style="width:auto"> {ui[o_mul]}</label>
<label class="small"><input type="checkbox" id="op_div" style="width:auto"> {ui[o_div]}</label></div>
<div class="field"><label for="max">{ui[l_max]}</label><select id="max">
<option value="10">10</option><option value="20" selected>20</option>
<option value="50">50</option><option value="100">100</option></select></div>
<div class="field"><label for="count">{ui[l_count]}</label><select id="count">
<option value="12">12</option><option value="20">20</option><option value="24" selected>24</option>
<option value="30">30</option><option value="40">40</option></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="cols">{ui[l_cols]}</label><select id="cols">
<option value="2">2</option><option value="3" selected>3</option><option value="4">4</option></select></div>
<div class="field"><label for="key">{ui[l_key]}</label><select id="key">
<option value="0">{ui[off]}</option><option value="1">{ui[on]}</option></select></div>
<div class="field" style="align-self:end;display:flex;gap:8px">
<button class="button" id="new">{ui[b_new]}</button>
<button class="button ghost" id="print">{ui[b_print]}</button></div>
</div>
<div class="sheet" id="sheet"></div>
<p class="note">{ui[note]}</p>
"""

WORKSHEET_JS = r"""
var $=function(i){return document.getElementById(i);};
var seed=Math.floor(Math.random()*1e9);
function rnd(){seed=(seed*1103515245+12345)&0x7fffffff;return seed/0x7fffffff;}
function ri(a,b){return a+Math.floor(rnd()*(b-a+1));}
function ops(){var o=[];
  if($('op_add').checked)o.push('+');
  if($('op_sub').checked)o.push('-');
  if($('op_mul').checked)o.push('x');
  if($('op_div').checked)o.push('/');
  return o.length?o:['+'];}
function problems(){
  var list=ops(),max=parseInt($('max').value,10),n=parseInt($('count').value,10),out=[];
  for(var i=0;i<n;i++){
    var op=list[Math.floor(rnd()*list.length)],a,b,ans;
    if(op==='+'){a=ri(1,max);b=ri(1,max-a>1?max-a:1);ans=a+b;}
    else if(op==='-'){a=ri(2,max);b=ri(1,a);ans=a-b;}
    else if(op==='x'){var lim=max<=20?9:12;a=ri(2,lim);b=ri(2,lim);ans=a*b;}
    else{var lim2=max<=20?9:12;b=ri(2,lim2);ans=ri(2,lim2);a=b*ans;}
    out.push({a:a,b:b,op:op,ans:ans});}
  return out;}
function sign(op){return op==='x'?'×':(op==='/'?'÷':op);}
function render(){
  var ps=problems(),host=$('sheet'),cols=$('cols').value;
  var h='<h3>'+L.title_sheet+'</h3><p class="small">'+L.meta
      .replace('{n}',ps.length)+'</p>';
  h+='<div class="probs" style="--cols:'+cols+'">';
  ps.forEach(function(p,i){
    h+='<div class="prob"><i>'+(i+1)+'.</i> '+p.a+' '+sign(p.op)+' '+p.b+' =</div>';});
  h+='</div>';
  if($('key').value==='1'){
    h+='<div class="key"><strong>'+L.answers+'</strong><br>';
    ps.forEach(function(p,i){h+=(i+1)+'. '+p.ans+'<br>';});
    h+='</div>';}
  host.innerHTML=h;
  window.__last=ps;}
['op_add','op_sub','op_mul','op_div','max','count','cols','key'].forEach(function(i){
  $(i).addEventListener('change',render);});
$('new').addEventListener('click',function(){seed=Math.floor(Math.random()*1e9);render();});
$('print').addEventListener('click',function(){window.print();});
render();
"""

_MATH_APP = {"app_key": "lumimath", "app_id": "6778269699", "app_name": "Lumi Math Planet",
             "category": "EducationalApplication"}


def spec_math_worksheet():
    spec = dict(_MATH_APP)
    spec.update({
        "slug": "math-worksheet-generator",
        "body": WORKSHEET_BODY,
        "script": WORKSHEET_JS,
        "extra_css": WORKSHEET_CSS,
        "print_css": ".top,.hero,.app-card,.footer,.faq,.grid,.controls,.note{display:none!important}body{background:#fff}.tool{box-shadow:none;border:0;padding:0}.sheet{border:0;padding:0}",
        "i18n": {
            "en": {
                "q": [("math worksheets", "D2"), ("addition worksheets", "D2"), ("math app for kids", "store-hint")],
                "title": "Math Worksheet Generator — Free Printable Addition, Subtraction, Times Tables",
                "description": "Generate a printable arithmetic worksheet in seconds: pick the operations, the number range and how many problems, with an optional answer key. Free, no sign-up, prints clean.",
                "h1": "Math worksheet generator",
                "eyebrow": "Printable · answer key optional · free",
                "lead": "Pick what your child is working on, press print. Subtraction never goes negative and division always comes out whole, so nothing on the page needs an apology.",
                "badges": ["+ − × ÷", "Answer key", "Prints clean", "No sign-up"],
                "features": ["Choose any mix of the four operations", "Number range from 10 to 100", "12 to 40 problems, 2–4 columns", "Optional answer key on the same sheet"],
                "how": [
                    "Problems are drawn from a small seeded generator, so the sheet on screen is exactly the sheet that prints. “New sheet” draws a fresh seed.",
                    "Subtraction always picks the smaller number second, so a beginner never meets a negative answer by accident.",
                    "Division is generated backwards from a whole quotient, so every division on the sheet divides exactly.",
                    "Multiplication stays inside the times tables — up to 9×9 for the smaller ranges and 12×12 for the larger ones.",
                ],
                "never": [
                    "It does not grade anything, track a child, or store a name. Nothing is saved and nothing is sent.",
                    "It is not a curriculum. Number ranges and operations are your choice; the page has no opinion about what a given age should be doing.",
                    "No account, no watermark, no print limit.",
                ],
                "faq": [
                    ("Will the printed sheet match the screen?", "Yes. The problems are generated once from a seed and only redrawn when you change a setting or press “New sheet”, so printing shows the same problems in the same order."),
                    ("Can I get an answer key?", "Yes — turn it on and it prints at the bottom of the same sheet in three columns. Turn it off for the child’s copy and on for yours."),
                    ("Are there negative answers or remainders?", "No. Subtraction is always ordered so the answer is zero or positive, and division problems are built from a whole answer, so they never leave a remainder."),
                ],
                "app_heading": "Practising maths on an iPad too?",
                "card": "Generate a printable +, −, ×, ÷ worksheet with an optional answer key.",
                "ui": {
                    "h2": "Build a worksheet",
                    "intro": "Everything is generated on this page. Nothing is stored.",
                    "l_ops": "Operations", "o_add": "Addition", "o_sub": "Subtraction",
                    "o_mul": "Multiplication", "o_div": "Division",
                    "l_max": "Largest number", "l_count": "Problems", "l_cols": "Columns",
                    "l_key": "Answer key", "on": "Include", "off": "Hide",
                    "b_new": "New sheet", "b_print": "Print",
                    "title_sheet": "Practice sheet", "meta": "{n} problems · name: ____________  date: __________",
                    "answers": "Answers",
                    "note": "Subtraction never produces a negative result and every division divides exactly.",
                },
            },
            "de-DE": {
                "q": [("mathe arbeitsblätter", "store-hint"), ("mathe app kinder", "store-hint")],
                "title": "Mathe-Arbeitsblatt erstellen — kostenlos, druckbar, mit Lösungen",
                "description": "Rechenblatt in Sekunden erzeugen: Rechenarten, Zahlenraum und Anzahl wählen, Lösungsblatt optional. Kostenlos, ohne Anmeldung, sauberer Ausdruck.",
                "h1": "Mathe-Arbeitsblatt erstellen",
                "eyebrow": "Druckbar · Lösungen optional · kostenlos",
                "lead": "Auswählen, was gerade geübt wird, und drucken. Subtraktion wird nie negativ und Division geht immer glatt auf.",
                "badges": ["+ − × ÷", "Lösungsteil", "Sauberer Druck", "Ohne Anmeldung"],
                "features": ["Beliebige Mischung der vier Rechenarten", "Zahlenraum 10 bis 100", "12 bis 40 Aufgaben, 2–4 Spalten", "Lösungen wahlweise auf demselben Blatt"],
                "how": [
                    "Die Aufgaben stammen aus einem kleinen Zufallsgenerator mit festem Startwert — auf dem Papier steht genau das, was auf dem Bildschirm steht. „Neues Blatt“ zieht einen neuen Startwert.",
                    "Bei der Subtraktion steht die kleinere Zahl immer hinten, damit Anfänger nicht versehentlich auf ein negatives Ergebnis stoßen.",
                    "Divisionsaufgaben werden von einem ganzzahligen Ergebnis aus rückwärts gebildet und gehen deshalb immer glatt auf.",
                    "Die Multiplikation bleibt im kleinen Einmaleins — bis 9×9 in den kleinen Zahlenräumen, bis 12×12 in den größeren.",
                ],
                "never": [
                    "Es bewertet nichts, verfolgt kein Kind und speichert keinen Namen. Nichts wird gespeichert oder gesendet.",
                    "Es ist kein Lehrplan. Zahlenraum und Rechenarten wählen Sie; die Seite hat keine Meinung dazu, was in welchem Alter dran ist.",
                    "Kein Konto, kein Wasserzeichen, kein Drucklimit.",
                ],
                "faq": [
                    ("Stimmt der Ausdruck mit dem Bildschirm überein?", "Ja. Die Aufgaben werden einmal aus einem Startwert erzeugt und nur bei einer Änderung oder bei „Neues Blatt“ neu gezogen."),
                    ("Gibt es einen Lösungsteil?", "Ja, er lässt sich einschalten und wird dreispaltig unten auf dasselbe Blatt gedruckt. Für das Kind ausschalten, für sich selbst einschalten."),
                    ("Kommen negative Ergebnisse oder Reste vor?", "Nein. Die Subtraktion ist so geordnet, dass das Ergebnis null oder positiv ist, und Divisionsaufgaben entstehen aus einem ganzzahligen Ergebnis."),
                ],
                "app_heading": "Wird auch auf dem iPad geübt?",
                "card": "Druckbares Arbeitsblatt für +, −, ×, ÷ mit optionalem Lösungsteil.",
                "ui": {
                    "h2": "Arbeitsblatt zusammenstellen",
                    "intro": "Alles wird auf dieser Seite erzeugt. Nichts wird gespeichert.",
                    "l_ops": "Rechenarten", "o_add": "Addition", "o_sub": "Subtraktion",
                    "o_mul": "Multiplikation", "o_div": "Division",
                    "l_max": "Größte Zahl", "l_count": "Aufgaben", "l_cols": "Spalten",
                    "l_key": "Lösungen", "on": "Anzeigen", "off": "Ausblenden",
                    "b_new": "Neues Blatt", "b_print": "Drucken",
                    "title_sheet": "Übungsblatt", "meta": "{n} Aufgaben · Name: ____________  Datum: __________",
                    "answers": "Lösungen",
                    "note": "Subtraktion ergibt nie ein negatives Ergebnis, und jede Division geht glatt auf.",
                },
            },
            "zh-Hant": {
                "q": [("數學練習題", "D3"), ("兒童 數學", "store-hint")],
                "title": "數學練習題產生器 — 免費可列印的加減乘除練習卷",
                "description": "選運算、選數字範圍、選題數，幾秒鐘產生一張可列印的練習卷，答案可選擇印或不印。免費、免註冊、列印乾淨。",
                "h1": "數學練習題產生器",
                "eyebrow": "可列印 · 答案可選 · 免費",
                "lead": "挑孩子現在在練的部分，直接列印。減法不會出現負數，除法一定整除，整張卷子不需要打折扣。",
                "badges": ["加減乘除", "附答案", "列印乾淨", "免註冊"],
                "features": ["四則運算任意組合", "數字範圍 10 到 100", "12 到 40 題，2–4 欄", "答案可印在同一張"],
                "how": [
                    "題目由一個帶種子的小型亂數產生器產生，所以螢幕上看到的就是列印出來的那一張。按「換一張」才會重抽。",
                    "減法一律把較小的數放後面，初學的孩子不會意外碰到負數。",
                    "除法是從整數商反推出來的，所以每一題都能整除。",
                    "乘法維持在乘法表範圍內：小範圍到 9×9，大範圍到 12×12。",
                ],
                "never": [
                    "不評分、不追蹤孩子、不記姓名，什麼都不儲存也不上傳。",
                    "這不是課綱。數字範圍與運算由你決定，頁面不對「幾歲該做什麼」表示意見。",
                    "不用帳號、沒有浮水印、沒有列印次數限制。",
                ],
                "faq": [
                    ("列印出來會跟畫面一樣嗎？", "會。題目由固定種子產生一次，只有改設定或按「換一張」才會重抽，所以列印的題目與順序完全相同。"),
                    ("可以印答案嗎？", "可以，開啟後會以三欄印在同一張的下方。給孩子的那份關掉、自己留的那份打開即可。"),
                    ("會出現負數或餘數嗎？", "不會。減法的順序保證結果為零或正數，除法題目由整數答案反推，所以不會有餘數。"),
                ],
                "app_heading": "也在 iPad 上練數學嗎？",
                "card": "產生可列印的加減乘除練習卷，答案可選擇一起印。",
                "ui": {
                    "h2": "組一張練習卷",
                    "intro": "全部在這個頁面產生，不會儲存任何資料。",
                    "l_ops": "運算", "o_add": "加法", "o_sub": "減法",
                    "o_mul": "乘法", "o_div": "除法",
                    "l_max": "最大數字", "l_count": "題數", "l_cols": "欄數",
                    "l_key": "答案", "on": "一起印", "off": "不印",
                    "b_new": "換一張", "b_print": "列印",
                    "title_sheet": "練習卷", "meta": "共 {n} 題 · 姓名：____________  日期：__________",
                    "answers": "答案",
                    "note": "減法不會出現負數，每一題除法都整除。",
                },
            },
        },
    })
    return spec


# -------------------------------------------------------- 11. reward chart

CHART_CSS = """
.chart{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px;margin-top:18px;overflow-x:auto}
.chart table{border-collapse:collapse;width:100%;min-width:520px}
.chart th,.chart td{border:1px solid #e0cfa9;padding:9px 8px;text-align:center;font-size:15px}
.chart th:first-child,.chart td:first-child{text-align:left;min-width:150px}
.chart thead th{background:var(--soft);color:var(--brand);white-space:nowrap}
.chart .box{display:inline-block;width:22px;height:22px;border:1.5px solid #d7c299;border-radius:6px}
.chart h3{margin:0 0 2px;font-family:ui-serif,Georgia,serif}
.chart .goal{margin-top:12px;font-size:14px;color:var(--muted)}
"""

CHART_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="name">{ui[l_name]}</label><input type="text" id="name" value="{ui[v_name]}" maxlength="24"></div>
<div class="field"><label for="days">{ui[l_days]}</label><select id="days">
<option value="5">{ui[d_5]}</option><option value="7" selected>{ui[d_7]}</option>
<option value="14">{ui[d_14]}</option></select></div>
<div class="field"><label for="goal">{ui[l_goal]}</label><input type="number" id="goal" value="15" min="1" max="200" inputmode="numeric"></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field" style="grid-column:1/-1"><label for="tasks">{ui[l_tasks]}</label>
<textarea id="tasks" style="min-height:120px">{ui[v_tasks]}</textarea></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field" style="grid-column:span 2"><label for="reward">{ui[l_reward]}</label><input type="text" id="reward" value="{ui[v_reward]}" maxlength="80"></div>
<div class="field" style="align-self:end"><button class="button ghost" id="print">{ui[b_print]}</button></div>
</div>
<div class="chart" id="chart"></div>
<p class="note">{ui[note]}</p>
"""

CHART_JS = r"""
var $=function(i){return document.getElementById(i);};
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
function tasks(){
  return $('tasks').value.split('\n').map(function(t){return t.trim();})
    .filter(function(t){return t.length;}).slice(0,12);}
function headers(n){
  if(n===7)return L.days7;
  if(n===5)return L.days7.slice(0,5);
  return L.days7.concat(L.days7).map(function(d,i){return d+' '+(i<7?'1':'2');});}
function render(){
  var t=tasks(),n=parseInt($('days').value,10),hs=headers(n);
  var h='<h3>'+esc($('name').value||L.v_name)+' · '+L.chart_title+'</h3>';
  h+='<p class="small">'+L.sub+'</p><table><thead><tr><th>'+L.col_task+'</th>';
  hs.forEach(function(d){h+='<th>'+esc(d)+'</th>';});
  h+='</tr></thead><tbody>';
  t.forEach(function(task){
    h+='<tr><td>'+esc(task)+'</td>';
    for(var i=0;i<n;i++)h+='<td><span class="box"></span></td>';
    h+='</tr>';});
  h+='</tbody></table>';
  var total=t.length*n,goal=parseInt($('goal').value,10)||0;
  h+='<p class="goal">'+L.goal_line.replace('{g}',goal).replace('{t}',total)
    +'<br>'+L.reward_line.replace('{r}',esc($('reward').value||'—'))+'</p>';
  if(goal>total)h+='<p class="goal" style="color:#b3452e">'+L.warn_goal+'</p>';
  $('chart').innerHTML=h;
  window.__chart={tasks:t,days:n,total:total,goal:goal};}
['name','days','goal','tasks','reward'].forEach(function(i){
  $(i).addEventListener('input',render);$(i).addEventListener('change',render);});
$('print').addEventListener('click',function(){window.print();});
render();
"""

_MISSION_APP = {"app_key": "lumimission", "app_id": "6779750237",
                "app_name": "Lumi Mission Planet", "category": "EducationalApplication"}


def spec_reward_chart():
    spec = dict(_MISSION_APP)
    spec.update({
        "slug": "reward-chart-maker",
        "body": CHART_BODY,
        "script": CHART_JS,
        "extra_css": CHART_CSS,
        "print_css": ".top,.hero,.app-card,.footer,.faq,.grid,.controls,.note{display:none!important}body{background:#fff}.tool{box-shadow:none;border:0;padding:0}.chart{border:0;padding:0}",
        "i18n": {
            "en": {
                "q": [("reward chart", "D2"), ("sticker chart", "store-hint")],
                "title": "Reward Chart Maker — Free Printable Sticker Chart for Kids",
                "description": "Type the tasks, choose five, seven or fourteen days, set a goal, print. A plain sticker chart with no account, no tracking and no paywall.",
                "h1": "Reward chart maker",
                "eyebrow": "Printable · your tasks · no account",
                "lead": "One page, your child’s own list of jobs, boxes big enough for a real sticker — and a goal that is checked against how many boxes actually exist.",
                "badges": ["Your own tasks", "5, 7 or 14 days", "Goal check", "Prints clean"],
                "features": ["Up to twelve tasks in your own words", "Five, seven or fourteen day layouts", "Star goal validated against the number of boxes", "Prints without the page furniture"],
                "how": [
                    "Each line you type becomes a row, up to twelve. Blank lines are ignored, so you can space the list out while writing it.",
                    "Columns come from the day setting; the fourteen-day layout repeats the week and numbers the two halves.",
                    "The total number of boxes is tasks × days, and the goal is compared against it — if you ask for more stars than the chart can hold, the page says so instead of printing something unachievable.",
                    "Printing hides the controls and the site furniture and leaves just the chart.",
                ],
                "never": [
                    "It does not store your child’s name or your task list. Reload the page and it is back to the defaults.",
                    "It gives no parenting advice and makes no claims about what reward charts achieve.",
                    "No account, no email wall, no watermark.",
                ],
                "faq": [
                    ("How many tasks can I add?", "Twelve rows, which is already more than most charts should have. Fewer, clearer jobs tend to work better than a long list."),
                    ("Why does it warn about my goal?", "Because a goal larger than tasks × days cannot be reached even with a perfect run. The page tells you rather than letting the chart fail quietly."),
                    ("Can I save the chart?", "Not on the page — nothing is stored. Print it, or use your browser’s print-to-PDF to keep a copy."),
                ],
                "app_heading": "Want the routine to carry on between print-outs?",
                "card": "Type your own tasks and print a 5, 7 or 14 day sticker chart with a checked goal.",
                "ui": {
                    "h2": "Make a chart",
                    "intro": "Nothing is stored — this is generated fresh each time.",
                    "l_name": "Child’s name", "v_name": "My chart",
                    "l_days": "Layout", "d_5": "5 days (school week)", "d_7": "7 days", "d_14": "14 days",
                    "l_goal": "Star goal", "l_tasks": "Tasks — one per line",
                    "v_tasks": "Get dressed by myself\nBrush teeth\nTidy up toys\nHelp lay the table\nRead for 10 minutes",
                    "l_reward": "Reward when the goal is reached", "v_reward": "Choose a film for family night",
                    "b_print": "Print", "chart_title": "Reward chart",
                    "sub": "One sticker or tick per box.", "col_task": "Task",
                    "days7": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "goal_line": "Goal: {g} stars · this chart has {t} boxes.",
                    "reward_line": "Reward: {r}",
                    "warn_goal": "The goal is higher than the number of boxes on this chart — lower it or add days.",
                    "note": "Everything you type stays on this page. Nothing is saved, sent or shared.",
                },
            },
            "ko": {
                "q": [("칭찬스티커", "D4"), ("아이 습관 앱", "store-hint")],
                "title": "칭찬스티커판 만들기 — 무료 인쇄용 보상 차트",
                "description": "할 일을 직접 입력하고 5일·7일·14일 중에 고른 뒤 목표를 정해서 인쇄하세요. 가입도, 추적도, 결제도 없습니다.",
                "h1": "칭찬스티커판 만들기",
                "eyebrow": "인쇄용 · 직접 쓴 할 일 · 가입 불필요",
                "lead": "한 장에 우리 아이의 할 일 목록, 스티커가 실제로 들어가는 크기의 칸, 그리고 칸 수에 맞는지 확인해 주는 목표.",
                "badges": ["직접 쓰는 할 일", "5·7·14일", "목표 검증", "깔끔한 인쇄"],
                "features": ["최대 12개의 할 일을 직접 입력", "5일·7일·14일 배치", "칸 수에 맞춰 검증되는 별 목표", "웹페이지 요소 없이 인쇄"],
                "how": [
                    "입력한 각 줄이 한 행이 되며 최대 12줄입니다. 빈 줄은 무시되므로 편하게 띄어 써도 됩니다.",
                    "열 수는 선택한 일수에 따라 정해지며, 14일 배치는 한 주를 두 번 반복하고 1·2로 구분합니다.",
                    "전체 칸 수는 할 일 × 일수이며 목표와 비교합니다. 칸보다 많은 별을 목표로 잡으면 그대로 인쇄하지 않고 알려 줍니다.",
                    "인쇄하면 설정과 사이트 요소는 숨고 차트만 남습니다.",
                ],
                "never": [
                    "아이 이름이나 할 일 목록을 저장하지 않습니다. 새로고침하면 기본값으로 돌아갑니다.",
                    "육아 조언을 하지 않으며, 보상 차트의 효과에 대해서도 아무것도 주장하지 않습니다.",
                    "가입, 이메일 요구, 워터마크가 없습니다.",
                ],
                "faq": [
                    ("할 일은 몇 개까지 되나요?", "12줄까지입니다. 사실 대부분의 차트에는 그보다 적은 편이 낫습니다. 항목이 적고 분명할수록 잘 지켜집니다."),
                    ("목표 경고는 왜 뜨나요?", "할 일 × 일수보다 목표가 크면 전부 성공해도 도달할 수 없기 때문입니다. 조용히 실패하게 두지 않고 알려 줍니다."),
                    ("차트를 저장할 수 있나요?", "페이지에는 저장되지 않습니다. 인쇄하거나 브라우저의 PDF로 저장 기능을 쓰세요."),
                ],
                "app_heading": "출력물 사이의 기간에도 습관을 이어가고 싶나요?",
                "card": "직접 쓴 할 일로 5·7·14일 칭찬스티커판을 만들고 목표까지 검증해 인쇄합니다.",
                "ui": {
                    "h2": "차트 만들기",
                    "intro": "저장하지 않습니다. 매번 새로 만들어집니다.",
                    "l_name": "아이 이름", "v_name": "우리 아이 차트",
                    "l_days": "배치", "d_5": "5일 (평일)", "d_7": "7일", "d_14": "14일",
                    "l_goal": "별 목표", "l_tasks": "할 일 — 한 줄에 하나",
                    "v_tasks": "혼자 옷 입기\n양치하기\n장난감 정리하기\n식탁 차리기 돕기\n10분 책 읽기",
                    "l_reward": "목표 달성 시 보상", "v_reward": "가족 영화의 밤 영화 고르기",
                    "b_print": "인쇄", "chart_title": "칭찬 차트",
                    "sub": "한 칸에 스티커 하나 또는 체크 하나.", "col_task": "할 일",
                    "days7": ["월", "화", "수", "목", "금", "토", "일"],
                    "goal_line": "목표: 별 {g}개 · 이 차트의 칸 수는 {t}개입니다.",
                    "reward_line": "보상: {r}",
                    "warn_goal": "목표가 차트의 칸 수보다 많습니다. 목표를 낮추거나 일수를 늘리세요.",
                    "note": "입력한 내용은 이 페이지에만 있습니다. 저장·전송·공유하지 않습니다.",
                },
            },
            "de-DE": {
                "q": [("belohnungssystem kinder", "D2"), ("routine app kinder", "store-hint")],
                "title": "Belohnungstafel erstellen — kostenlose druckbare Stickertafel für Kinder",
                "description": "Aufgaben eintippen, 5, 7 oder 14 Tage wählen, Ziel festlegen, drucken. Eine schlichte Stickertafel ohne Konto, ohne Tracking, ohne Bezahlschranke.",
                "h1": "Belohnungstafel erstellen",
                "eyebrow": "Druckbar · eigene Aufgaben · ohne Konto",
                "lead": "Eine Seite, die eigenen Aufgaben Ihres Kindes, Kästchen groß genug für einen echten Sticker — und ein Ziel, das gegen die Zahl der Kästchen geprüft wird.",
                "badges": ["Eigene Aufgaben", "5, 7 oder 14 Tage", "Zielprüfung", "Sauberer Druck"],
                "features": ["Bis zu zwölf Aufgaben in eigenen Worten", "Layouts für fünf, sieben oder vierzehn Tage", "Sternziel wird gegen die Kästchenzahl geprüft", "Druck ohne Seitenelemente"],
                "how": [
                    "Jede eingegebene Zeile wird zu einer Zeile der Tabelle, höchstens zwölf. Leerzeilen werden ignoriert.",
                    "Die Spalten ergeben sich aus der Tagesauswahl; das Vierzehn-Tage-Layout wiederholt die Woche und nummeriert beide Hälften.",
                    "Die Gesamtzahl der Kästchen ist Aufgaben × Tage und wird mit dem Ziel verglichen. Ist das Ziel höher, sagt die Seite das, statt etwas Unerreichbares zu drucken.",
                    "Beim Drucken verschwinden Bedienelemente und Seitenrahmen, übrig bleibt die Tafel.",
                ],
                "never": [
                    "Es speichert weder den Namen Ihres Kindes noch Ihre Aufgabenliste. Nach dem Neuladen stehen wieder die Vorgaben da.",
                    "Es gibt keine Erziehungsratschläge und behauptet nichts über die Wirkung von Belohnungstafeln.",
                    "Kein Konto, keine E-Mail-Hürde, kein Wasserzeichen.",
                ],
                "faq": [
                    ("Wie viele Aufgaben sind möglich?", "Zwölf Zeilen — das ist für die meisten Tafeln schon mehr als sinnvoll. Wenige, klare Aufgaben funktionieren besser als eine lange Liste."),
                    ("Warum warnt die Seite bei meinem Ziel?", "Weil ein Ziel über Aufgaben × Tage selbst bei perfektem Verlauf nicht erreichbar ist. Die Seite sagt es, statt die Tafel still scheitern zu lassen."),
                    ("Kann ich die Tafel speichern?", "Nicht auf der Seite — es wird nichts gespeichert. Drucken Sie sie oder nutzen Sie „Als PDF sichern“ im Druckdialog."),
                ],
                "app_heading": "Soll die Routine zwischen zwei Ausdrucken weiterlaufen?",
                "card": "Eigene Aufgaben eintragen und eine Stickertafel für 5, 7 oder 14 Tage drucken.",
                "ui": {
                    "h2": "Tafel erstellen",
                    "intro": "Nichts wird gespeichert — jedes Mal frisch erzeugt.",
                    "l_name": "Name des Kindes", "v_name": "Meine Tafel",
                    "l_days": "Layout", "d_5": "5 Tage (Schulwoche)", "d_7": "7 Tage", "d_14": "14 Tage",
                    "l_goal": "Sternziel", "l_tasks": "Aufgaben — eine pro Zeile",
                    "v_tasks": "Alleine anziehen\nZähne putzen\nSpielsachen aufräumen\nBeim Tischdecken helfen\n10 Minuten lesen",
                    "l_reward": "Belohnung bei Zielerreichung", "v_reward": "Film für den Familienabend aussuchen",
                    "b_print": "Drucken", "chart_title": "Belohnungstafel",
                    "sub": "Ein Sticker oder Haken pro Kästchen.", "col_task": "Aufgabe",
                    "days7": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
                    "goal_line": "Ziel: {g} Sterne · diese Tafel hat {t} Kästchen.",
                    "reward_line": "Belohnung: {r}",
                    "warn_goal": "Das Ziel liegt über der Zahl der Kästchen — Ziel senken oder Tage hinzufügen.",
                    "note": "Alles Eingetippte bleibt auf dieser Seite. Nichts wird gespeichert, gesendet oder geteilt.",
                },
            },
        },
    })
    return spec


# ------------------------------------------------------ 12. letter tracing

TRACE_CSS = """
.trace{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:18px}
.trace svg{display:block;width:100%;height:auto;margin-bottom:10px}
.trace .lbl{font-size:13px;color:var(--muted);margin:0 0 4px}
"""

TRACE_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="controls">
<div class="field"><label for="letters">{ui[l_letters]}</label><input type="text" id="letters" value="A B C" maxlength="60"></div>
<div class="field"><label for="case">{ui[l_case]}</label><select id="case">
<option value="upper">{ui[c_upper]}</option><option value="lower">{ui[c_lower]}</option>
<option value="both" selected>{ui[c_both]}</option></select></div>
<div class="field"><label for="rows">{ui[l_rows]}</label><select id="rows">
<option value="1">1</option><option value="2" selected>2</option><option value="3">3</option></select></div>
</div>
<div class="controls" style="margin-top:10px">
<div class="field"><label for="style">{ui[l_style]}</label><select id="style">
<option value="dotted" selected>{ui[s_dotted]}</option><option value="outline">{ui[s_outline]}</option>
<option value="faded">{ui[s_faded]}</option></select></div>
<div class="field"><label for="start">{ui[l_start]}</label><select id="start">
<option value="1">{ui[on]}</option><option value="0">{ui[off]}</option></select></div>
<div class="field" style="align-self:end"><button class="button ghost" id="print">{ui[b_print]}</button></div>
</div>
<div class="trace" id="sheet"></div>
<p class="note">{ui[note]}</p>
"""

TRACE_JS = r"""
var $=function(i){return document.getElementById(i);};
function chars(){
  var raw=$('letters').value.replace(/\s+/g,'');
  var mode=$('case').value,out=[];
  for(var i=0;i<raw.length&&out.length<12;i++){
    var c=raw[i];
    if(mode==='upper')out.push(c.toUpperCase());
    else if(mode==='lower')out.push(c.toLowerCase());
    else{out.push(c.toUpperCase());out.push(c.toLowerCase());}}
  return out;}
function styleAttrs(){
  var s=$('style').value;
  if(s==='outline')return {fill:'none',stroke:'#c9b489',dash:'',width:2};
  if(s==='faded')return {fill:'#eadfc6',stroke:'none',dash:'',width:0};
  return {fill:'none',stroke:'#c9b489',dash:'5 7',width:2.5};}
function rowSvg(ch,perRow){
  var st=styleAttrs(),w=980,h=170,x0=40,gap=(w-x0*2)/perRow;
  var s='<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-label="'+ch+'">';
  s+='<line x1="20" y1="30" x2="'+(w-20)+'" y2="30" stroke="#ece0c6" stroke-width="2"/>';
  s+='<line x1="20" y1="90" x2="'+(w-20)+'" y2="90" stroke="#e7d9ba" stroke-width="2" stroke-dasharray="7 9"/>';
  s+='<line x1="20" y1="140" x2="'+(w-20)+'" y2="140" stroke="#ddc9a0" stroke-width="2.5"/>';
  for(var i=0;i<perRow;i++){
    var x=x0+gap*i;
    s+='<text x="'+x+'" y="140" font-size="120" font-family="Verdana,Geneva,sans-serif"'
      +' fill="'+st.fill+'" stroke="'+st.stroke+'" stroke-width="'+st.width+'"'
      +(st.dash?' stroke-dasharray="'+st.dash+'"':'')+'>'+ch+'</text>';
    if($('start').value==='1'&&i===0)
      s+='<circle cx="'+(x+6)+'" cy="42" r="7" fill="#c8922a"/>';}
  s+='</svg>';
  return s;}
function render(){
  var cs=chars(),rows=parseInt($('rows').value,10),host=$('sheet'),h='';
  if(!cs.length){host.innerHTML='<p class="small">'+L.empty+'</p>';window.__trace=[];return;}
  cs.forEach(function(c){
    for(var r=0;r<rows;r++){
      h+='<p class="lbl">'+c+'</p>'+rowSvg(c,6);}});
  host.innerHTML=h;
  window.__trace=cs;}
['letters','case','rows','style','start'].forEach(function(i){
  $(i).addEventListener('input',render);$(i).addEventListener('change',render);});
$('print').addEventListener('click',function(){window.print();});
render();
"""

_LETTERS_APP = {"app_key": "lumiletters", "app_id": "6778748533", "app_name": "Lumi Letters",
                "category": "EducationalApplication"}


def spec_letter_tracing():
    spec = dict(_LETTERS_APP)
    spec.update({
        "slug": "letter-tracing-worksheet",
        "body": TRACE_BODY,
        "script": TRACE_JS,
        "extra_css": TRACE_CSS,
        "print_css": ".top,.hero,.app-card,.footer,.faq,.grid,.controls,.note{display:none!important}body{background:#fff}.tool{box-shadow:none;border:0;padding:0}.trace{border:0;padding:0}",
        "i18n": {
            "en": {
                "q": [("letter tracing", "D2"), ("abc app for kids", "store-hint")],
                "title": "Letter Tracing Worksheet Generator — Free Printable, Any Letters",
                "description": "Make a printable tracing sheet from any letters you type, in upper case, lower case or both, with three guide styles and proper baseline, midline and cap-height rules.",
                "h1": "Letter tracing worksheet",
                "eyebrow": "Any letters · real guide lines · printable",
                "lead": "Type the letters your child is working on — not a fixed A-to-Z pack — and get ruled rows with a cap-height line, a dashed midline and a solid baseline.",
                "badges": ["Your letters", "Upper, lower or both", "3 guide styles", "Prints clean"],
                "features": ["Any letters you type, up to twelve per sheet", "Upper case, lower case or both", "Dotted, outline or faded guide styles", "Cap-height, midline and baseline rules on every row"],
                "how": [
                    "Each row is drawn as SVG, so it prints at your printer’s resolution rather than as a blurry bitmap.",
                    "Three rules run behind the letters: a light cap-height line, a dashed midline for x-height and a heavier baseline — the same structure as school handwriting paper.",
                    "Dotted uses a dashed stroke and no fill, outline uses a solid stroke and no fill, and faded uses a pale fill for children who are still following shapes rather than lines.",
                    "The starting dot marks where the first letter of each row begins, and can be turned off.",
                ],
                "never": [
                    "It does not teach a specific handwriting scheme. Letter shapes come from a standard sans-serif face, not from a cursive or school-specific font.",
                    "It stores nothing. The letters you type never leave the page.",
                    "No account, no watermark, no limit on how many sheets you print.",
                ],
                "faq": [
                    ("Can I use it for the letters my child gets wrong?", "That is the point. Type just those letters — three problem letters repeated over two rows each is far more useful than a full alphabet pack."),
                    ("Why are there three lines?", "They are cap height, midline and baseline. Children need the midline to judge where lower-case letters stop and where ascenders and descenders go; a single line is not enough."),
                    ("Does it do cursive or a specific school font?", "No. It uses a standard sans-serif face and says so, rather than claiming to match a particular national handwriting scheme."),
                ],
                "app_heading": "Learning letters on an iPad as well?",
                "card": "Print a tracing sheet for exactly the letters you type, with real handwriting guide lines.",
                "ui": {
                    "h2": "Choose the letters",
                    "intro": "Type letters, separated or not. Up to twelve per sheet.",
                    "l_letters": "Letters", "l_case": "Case", "c_upper": "Upper case",
                    "c_lower": "Lower case", "c_both": "Both",
                    "l_rows": "Rows per letter", "l_style": "Guide style",
                    "s_dotted": "Dotted", "s_outline": "Outline", "s_faded": "Faded",
                    "l_start": "Starting dot", "on": "Show", "off": "Hide",
                    "b_print": "Print", "empty": "Type at least one letter.",
                    "note": "Letters are drawn in a standard sans-serif face — this is not a national handwriting scheme font.",
                },
            },
            "de-DE": {
                "q": [("lesen lernen", "D2"), ("abc app kinder", "store-hint")],
                "title": "Buchstaben nachspuren — kostenlose druckbare Vorlage für beliebige Buchstaben",
                "description": "Druckbares Schwungübungsblatt aus genau den Buchstaben, die Sie eintippen — Groß, Klein oder beides, drei Linienarten und echte Grund-, Mittel- und Oberlinie.",
                "h1": "Buchstaben-Nachspurblatt",
                "eyebrow": "Eigene Buchstaben · echte Linien · druckbar",
                "lead": "Tippen Sie genau die Buchstaben ein, die gerade dran sind — kein festes A-bis-Z-Paket — und bekommen Sie linierte Zeilen mit Ober-, Mittel- und Grundlinie.",
                "badges": ["Eigene Buchstaben", "Groß, klein oder beides", "3 Linienarten", "Sauberer Druck"],
                "features": ["Beliebige Buchstaben, bis zu zwölf pro Blatt", "Großbuchstaben, Kleinbuchstaben oder beides", "Gepunktet, Umriss oder blass", "Ober-, Mittel- und Grundlinie in jeder Zeile"],
                "how": [
                    "Jede Zeile wird als SVG gezeichnet und druckt daher in der Auflösung Ihres Druckers statt als unscharfe Bitmap.",
                    "Hinter den Buchstaben laufen drei Linien: eine helle Oberlinie, eine gestrichelte Mittellinie für die x-Höhe und eine kräftigere Grundlinie — wie auf Schulschreibpapier.",
                    "Gepunktet nutzt eine gestrichelte Kontur ohne Füllung, Umriss eine durchgezogene Kontur ohne Füllung, blass eine helle Füllung für Kinder, die noch Formen statt Linien folgen.",
                    "Der Startpunkt markiert den Beginn des ersten Buchstabens jeder Zeile und lässt sich abschalten.",
                ],
                "never": [
                    "Es lehrt keine bestimmte Ausgangsschrift. Die Formen stammen aus einer Standard-Groteskschrift, nicht aus einer Schulschriftart.",
                    "Es speichert nichts. Die eingetippten Buchstaben verlassen die Seite nie.",
                    "Kein Konto, kein Wasserzeichen, keine Begrenzung der Ausdrucke.",
                ],
                "faq": [
                    ("Kann ich nur die schwierigen Buchstaben üben?", "Genau dafür ist es gedacht. Drei Problembuchstaben mit je zwei Zeilen bringen mehr als ein komplettes Alphabetpaket."),
                    ("Warum drei Linien?", "Oberlinie, Mittellinie und Grundlinie. Kinder brauchen die Mittellinie, um zu sehen, wo Kleinbuchstaben enden und wohin Ober- und Unterlängen gehen."),
                    ("Gibt es Schreibschrift oder eine Schulausgangsschrift?", "Nein. Es verwendet eine Standard-Groteskschrift und sagt das auch, statt eine bestimmte Ausgangsschrift zu behaupten."),
                ],
                "app_heading": "Wird auch auf dem iPad geübt?",
                "card": "Nachspurblatt für genau die eingetippten Buchstaben, mit echten Schreiblinien.",
                "ui": {
                    "h2": "Buchstaben wählen",
                    "intro": "Buchstaben eintippen, mit oder ohne Leerzeichen. Bis zu zwölf pro Blatt.",
                    "l_letters": "Buchstaben", "l_case": "Schreibweise", "c_upper": "Großbuchstaben",
                    "c_lower": "Kleinbuchstaben", "c_both": "Beides",
                    "l_rows": "Zeilen je Buchstabe", "l_style": "Linienart",
                    "s_dotted": "Gepunktet", "s_outline": "Umriss", "s_faded": "Blass",
                    "l_start": "Startpunkt", "on": "Anzeigen", "off": "Ausblenden",
                    "b_print": "Drucken", "empty": "Bitte mindestens einen Buchstaben eingeben.",
                    "note": "Die Buchstaben stehen in einer Standard-Groteskschrift — das ist keine offizielle Schulausgangsschrift.",
                },
            },
        },
    })
    return spec


# --------------------------------------------------- 13. duplicate photos

DUPE_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<div class="filedrop"><input type="file" id="file" accept="image/*" multiple> <span class="small">{ui[accept]}</span></div>
<div class="controls" style="margin-top:16px">
<div class="field"><label for="tol">{ui[l_tol]} · <span id="tv">6</span></label><input type="range" id="tol" min="0" max="16" value="6"></div>
<div class="field" style="align-self:end"><button class="button" id="scan" disabled>{ui[b_scan]}</button></div>
<div class="field" style="align-self:end"><button class="button ghost" id="clear">{ui[b_clear]}</button></div>
</div>
<div class="results">
<div class="result"><strong>{ui[r_files]}</strong><span id="nfiles">0</span></div>
<div class="result"><strong>{ui[r_groups]}</strong><span id="ngroups">—</span></div>
<div class="result"><strong>{ui[r_dupes]}</strong><span id="ndupes">—</span></div>
<div class="result ok"><strong>{ui[r_bytes]}</strong><span id="nbytes">—</span></div>
</div>
<div id="out" style="margin-top:18px"></div>
<p class="note">{ui[note]}</p>
"""

DUPE_JS = r"""
var $=function(i){return document.getElementById(i);};
var files=[],items=[];
function human(b){if(b<1024)return b+' B';
  if(b<1048576)return (b/1024).toFixed(0)+' KB';
  return (b/1048576).toFixed(2)+' MB';}
function ahash(img){
  var N=8,c=document.createElement('canvas');c.width=N;c.height=N;
  var x=c.getContext('2d');x.drawImage(img,0,0,N,N);
  var d=x.getImageData(0,0,N,N).data,g=[],sum=0,i;
  for(i=0;i<N*N;i++){var v=0.2126*d[i*4]+0.7152*d[i*4+1]+0.0722*d[i*4+2];
    g.push(v);sum+=v;}
  var avg=sum/(N*N),bits='';
  for(i=0;i<N*N;i++)bits+=(g[i]>=avg?'1':'0');
  return bits;}
function dist(a,b){var n=0;for(var i=0;i<a.length;i++)if(a[i]!==b[i])n++;return n;}
function group(items,tol){
  var used=[],groups=[];
  for(var i=0;i<items.length;i++){
    if(used[i])continue;
    var g=[items[i]];used[i]=1;
    for(var j=i+1;j<items.length;j++){
      if(used[j])continue;
      if(dist(items[i].hash,items[j].hash)<=tol){g.push(items[j]);used[j]=1;}}
    if(g.length>1)groups.push(g);}
  return groups;}
function load(f){return new Promise(function(res){
  var u=URL.createObjectURL(f),im=new Image();
  im.onload=function(){
    var h=ahash(im);URL.revokeObjectURL(u);
    res({name:f.name,size:f.size,hash:h,w:im.naturalWidth,h2:im.naturalHeight});};
  im.onerror=function(){URL.revokeObjectURL(u);res(null);};
  im.src=u;});}
$('file').addEventListener('change',function(){
  for(var i=0;i<$('file').files.length;i++)files.push($('file').files[i]);
  $('file').value='';$('nfiles').textContent=String(files.length);
  $('scan').disabled=files.length<2;});
$('clear').addEventListener('click',function(){
  files=[];items=[];$('nfiles').textContent='0';$('scan').disabled=true;
  ['ngroups','ndupes','nbytes'].forEach(function(i){$(i).textContent='—';});
  $('out').innerHTML='';});
$('tol').addEventListener('input',function(){$('tv').textContent=$('tol').value;
  if(items.length)show();});
$('scan').addEventListener('click',function(){
  $('scan').disabled=true;$('scan').textContent=L.b_working;
  Promise.all(files.map(load)).then(function(list){
    items=list.filter(function(x){return x;});
    show();}).catch(function(){}).then(function(){
    $('scan').disabled=false;$('scan').textContent=L.b_scan;});});
function show(){
  var tol=parseInt($('tol').value,10),groups=group(items,tol);
  var dupes=0,bytes=0;
  groups.forEach(function(g){
    var sorted=g.slice().sort(function(a,b){return b.size-a.size;});
    dupes+=g.length-1;
    for(var i=1;i<sorted.length;i++)bytes+=sorted[i].size;});
  $('ngroups').textContent=String(groups.length);
  $('ndupes').textContent=String(dupes);
  $('nbytes').textContent=human(bytes);
  var host=$('out');host.innerHTML='';
  if(!groups.length){
    var p=document.createElement('p');p.className='small';
    p.textContent=L.none;host.appendChild(p);window.__groups=[];return;}
  groups.forEach(function(g,gi){
    var card=document.createElement('article');card.className='card';
    card.style.marginBottom='12px';
    var h=document.createElement('h2');h.style.fontSize='19px';
    h.textContent=L.group.replace('{i}',gi+1).replace('{n}',g.length);
    card.appendChild(h);
    var ul=document.createElement('ul');
    g.slice().sort(function(a,b){return b.size-a.size;}).forEach(function(it,i){
      var li=document.createElement('li');
      li.textContent=it.name+' — '+it.w+'×'+it.h2+' · '+human(it.size)
        +(i===0?'  ('+L.keep+')':'');
      ul.appendChild(li);});
    card.appendChild(ul);host.appendChild(card);});
  window.__groups=groups;}
"""

_PICCLEAR_APP = {"app_key": "picclear", "app_id": "6780223070", "app_name": "PicClear",
                 "category": "UtilitiesApplication"}


def spec_duplicate_photos():
    spec = dict(_PICCLEAR_APP)
    spec.update({
        "slug": "duplicate-photo-finder",
        "body": DUPE_BODY,
        "script": DUPE_JS,
        "i18n": {
            "en": {
                "q": [("duplicate photos", "D2"), ("free up iphone storage", "D2"), ("delete duplicate photos", "store-hint")],
                "title": "Duplicate Photo Finder — Free, In-Browser, Finds Near-Duplicates Too",
                "description": "Select photos and this groups visual duplicates and near-duplicates using a perceptual hash, showing which copy is largest and how many bytes the rest are costing. Nothing is uploaded.",
                "h1": "Duplicate photo finder",
                "eyebrow": "Perceptual hashing · runs in your browser",
                "lead": "Byte-for-byte comparison misses the case that actually fills a phone: twelve nearly identical shots of the same thing. This compares what the pictures look like.",
                "badges": ["Near-duplicates too", "Adjustable strictness", "Shows bytes at stake", "No upload"],
                "features": ["8×8 average perceptual hash per image", "Adjustable Hamming-distance tolerance", "Groups sorted with the largest copy first", "Reclaimable byte total"],
                "how": [
                    "Each image is drawn to an 8×8 canvas, converted to luminance and turned into a 64-bit average hash — one bit per cell, set when that cell is brighter than the image mean.",
                    "Two images are treated as duplicates when their hashes differ in no more than the number of bits you set. Zero means visually identical; six catches slight crops, exposure changes and re-saves.",
                    "Within each group the largest file is listed first and marked as the one to keep; the sizes of the others are what the counter adds up.",
                    "Changing the tolerance regroups instantly without re-reading the files.",
                ],
                "never": [
                    "It cannot delete anything. A web page has no access to your photo library — this tells you which files to deal with, and you do the deleting.",
                    "It does not read EXIF, dates or locations. The grouping is purely on appearance.",
                    "Nothing is uploaded. Hashing happens on your own device.",
                ],
                "faq": [
                    ("How is this different from an exact duplicate finder?", "An exact finder compares bytes, so re-saving, resizing or a different export setting hides the duplicate. A perceptual hash compares what the image looks like, which is why it also catches burst shots and near-identical retakes."),
                    ("What tolerance should I use?", "Zero or one for exact and near-exact copies. Around six is a good default for burst shots and slight edits. Above ten you will start seeing false matches on flat images like screenshots of the same app."),
                    ("Can it clean my phone directly?", "No. A browser page cannot touch your photo library, and any page claiming otherwise is not telling the truth. Use this to identify the files, then delete them yourself."),
                ],
                "app_heading": "Want this to run against the whole camera roll?",
                "card": "Group visually duplicate photos with a perceptual hash and see the bytes at stake.",
                "ui": {
                    "h2": "Select photos and scan",
                    "intro": "Files are read and hashed on this page; nothing is uploaded.",
                    "accept": "Multiple images allowed",
                    "l_tol": "Tolerance (bits)", "b_scan": "Scan for duplicates",
                    "b_working": "Working…", "b_clear": "Clear",
                    "r_files": "Files loaded", "r_groups": "Duplicate groups",
                    "r_dupes": "Extra copies", "r_bytes": "Bytes in extra copies",
                    "group": "Group {i} · {n} similar images", "keep": "largest — keep this one",
                    "none": "No duplicates at this tolerance.",
                    "note": "This page can never delete a file. It identifies duplicates; removing them is up to you.",
                },
            },
            "ja": {
                "q": [("重複写真 削除", "D2"), ("iphone 容量 いっぱい", "store-hint")],
                "title": "重複写真の検出 — 無料・ブラウザ内・「ほぼ同じ」写真も見つかります",
                "description": "写真を選ぶだけで、知覚ハッシュを使って重複・ほぼ重複をグループ化し、どれを残すべきか、残りが何バイト占めているかを表示します。アップロードはありません。",
                "h1": "重複写真を見つける",
                "eyebrow": "知覚ハッシュ · ブラウザ内で処理",
                "lead": "容量を食っているのは完全に同一のファイルではなく、同じ被写体をほぼ同じ構図で撮った十数枚です。このツールは見た目を比べます。",
                "badges": ["ほぼ同じ写真も検出", "厳しさを調整可能", "節約できる容量を表示", "アップロードなし"],
                "features": ["1枚ごとに 8×8 の平均ハッシュを計算", "ハミング距離のしきい値を調整可能", "各グループで最大のファイルを先頭に表示", "削除で空く容量の合計"],
                "how": [
                    "各画像を 8×8 の canvas に描いて輝度に変換し、平均より明るいセルを 1 とする 64 ビットの平均ハッシュにします。",
                    "2枚のハッシュの違いが指定ビット数以内なら重複とみなします。0 は見た目が同一、6 くらいで軽いトリミング・露出差・再保存も拾えます。",
                    "各グループ内ではファイルサイズが最大のものを先頭に置き「これを残す」と示します。カウンタが足しているのは残りのサイズです。",
                    "しきい値を変えるとファイルを読み直さずにその場で再グループ化します。",
                ],
                "never": [
                    "ファイルを削除することはできません。ウェブページは写真ライブラリにアクセスできないので、どれを処理すべきかを示すところまでです。",
                    "EXIF・撮影日時・位置情報は読みません。判定は見た目だけです。",
                    "アップロードしません。ハッシュ計算はすべて端末内です。",
                ],
                "faq": [
                    ("完全一致の重複検出と何が違いますか？", "完全一致はバイト単位の比較なので、再保存・リサイズ・書き出し設定の違いで見つからなくなります。知覚ハッシュは見た目を比較するため、連写やほぼ同じ撮り直しも拾えます。"),
                    ("しきい値はいくつが良いですか？", "完全〜ほぼ完全な複製なら 0〜1、連写や軽い編集を含めるなら 6 前後が目安です。10 を超えると、同じアプリのスクリーンショットのような平坦な画像で誤検出が出はじめます。"),
                    ("iPhone の写真を直接消せますか？", "できません。ブラウザのページは写真ライブラリに触れられません。そう主張するページがあれば、それは正しくありません。ここで対象を特定し、削除はご自身で行ってください。"),
                ],
                "app_heading": "カメラロール全体に対して実行したいですか？",
                "card": "知覚ハッシュで見た目が同じ写真をグループ化し、空く容量を表示します。",
                "ui": {
                    "h2": "写真を選んでスキャン",
                    "intro": "ファイルの読み込みとハッシュ計算はこのページ内で行われます。",
                    "accept": "複数選択できます",
                    "l_tol": "許容ビット数", "b_scan": "重複を検出",
                    "b_working": "処理中…", "b_clear": "クリア",
                    "r_files": "読み込んだ枚数", "r_groups": "重複グループ",
                    "r_dupes": "余分なコピー", "r_bytes": "余分なコピーの合計",
                    "group": "グループ {i} · 似た画像 {n} 枚", "keep": "最大 — これを残す",
                    "none": "このしきい値では重複は見つかりませんでした。",
                    "note": "このページがファイルを削除することはありません。特定するところまでで、削除はご自身の操作です。",
                },
            },
            "zh-Hant": {
                "q": [("重複照片", "D3"), ("手機 空間 不足", "store-hint")],
                "title": "重複照片偵測 — 免費、瀏覽器內執行、連「幾乎相同」的也找得到",
                "description": "選好照片，用感知雜湊把重複與近似重複分組，標出該留哪一張、其餘佔了多少空間。全程不上傳。",
                "h1": "重複照片偵測",
                "eyebrow": "感知雜湊 · 在瀏覽器內執行",
                "lead": "把手機塞爆的通常不是完全相同的檔案，而是同一個東西連拍的十幾張。這個工具比的是「看起來像不像」。",
                "badges": ["連近似的都找得到", "可調整嚴格度", "顯示可省下的容量", "不上傳"],
                "features": ["每張圖計算 8×8 平均感知雜湊", "可調整的漢明距離門檻", "每組把最大的檔案排在最前面", "可回收位元組總計"],
                "how": [
                    "每張圖畫到 8×8 的 canvas 上轉成亮度，再產生 64 位元的平均雜湊：比平均亮的格子記為 1。",
                    "兩張圖的雜湊差異在你設定的位元數以內就算重複。0 代表看起來完全相同，6 左右可以抓到輕微裁切、曝光差異與重新存檔。",
                    "每一組裡把檔案最大的排第一並標示「留這張」，計數器加總的是其餘那些的大小。",
                    "調整門檻會立刻重新分組，不需要重讀檔案。",
                ],
                "never": [
                    "無法刪除任何檔案。網頁碰不到你的照片圖庫，這裡只能告訴你該處理哪些，刪除要你自己來。",
                    "不讀取 EXIF、日期或位置，分組完全依據外觀。",
                    "不上傳，雜湊計算全部在你的裝置上完成。",
                ],
                "faq": [
                    ("和「完全相同」的重複偵測差在哪？", "完全相同是比位元組，只要重新存檔、縮圖或換個匯出設定就抓不到了。感知雜湊比的是外觀，所以連拍與幾乎一樣的重拍也能歸在一起。"),
                    ("門檻要設多少？", "完全或幾乎完全相同設 0–1；連拍與輕微編輯大約設 6。超過 10 之後，像同一個 App 的截圖那種大片單色的圖會開始誤判。"),
                    ("可以直接清理我的手機嗎？", "不行。瀏覽器頁面碰不到照片圖庫，任何宣稱做得到的頁面都不誠實。請用這裡找出檔案，再自己刪除。"),
                ],
                "app_heading": "想對整個相簿跑一次嗎？",
                "card": "用感知雜湊把看起來相同的照片分組，並顯示可以省下的容量。",
                "ui": {
                    "h2": "選擇照片並掃描",
                    "intro": "讀檔與計算雜湊都在這個頁面內完成，不會上傳。",
                    "accept": "可以一次選多張",
                    "l_tol": "容許差異（位元）", "b_scan": "開始偵測",
                    "b_working": "處理中…", "b_clear": "清除",
                    "r_files": "已載入", "r_groups": "重複群組",
                    "r_dupes": "多餘的副本", "r_bytes": "多餘副本佔用",
                    "group": "第 {i} 組 · {n} 張相似影像", "keep": "最大 — 留這張",
                    "none": "在這個門檻下沒有找到重複。",
                    "note": "這個頁面永遠不會刪除檔案，只負責找出來；刪除由你決定與執行。",
                },
            },
        },
    })
    return spec


# ------------------------------------------------------- 14. flashcards

FLASH_BODY = """
<h2>{ui[h2]}</h2>
<p class="intro">{ui[intro]}</p>
<textarea id="src" style="min-height:150px">{ui[v_src]}</textarea>
<div class="controls" style="margin-top:12px">
<div class="field"><label for="dir">{ui[l_dir]}</label><select id="dir">
<option value="ft">{ui[d_ft]}</option><option value="tf">{ui[d_tf]}</option>
<option value="mix">{ui[d_mix]}</option></select></div>
<div class="field"><label for="shuffle">{ui[l_shuffle]}</label><select id="shuffle">
<option value="1">{ui[on]}</option><option value="0">{ui[off]}</option></select></div>
<div class="field" style="align-self:end;display:flex;gap:8px">
<button class="button" id="start">{ui[b_start]}</button>
<button class="button ghost" id="csv">{ui[b_csv]}</button></div>
</div>
<div class="results">
<div class="result"><strong>{ui[r_cards]}</strong><span id="ncards">0</span></div>
<div class="result"><strong>{ui[r_round]}</strong><span id="nround">—</span></div>
<div class="result ok"><strong>{ui[r_known]}</strong><span id="nknown">0</span></div>
<div class="result"><strong>{ui[r_left]}</strong><span id="nleft">—</span></div>
</div>
<div class="card" id="stage" style="margin-top:18px;display:none;text-align:center;padding:34px 20px">
<p class="small" id="side">—</p>
<p id="face" style="font-size:clamp(24px,5vw,40px);font-weight:800;margin:6px 0 18px;word-break:break-word">—</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
<button class="button ghost" id="flip">{ui[b_flip]}</button>
<button class="button" id="yes" disabled>{ui[b_yes]}</button>
<button class="button ghost" id="no" disabled>{ui[b_no]}</button></div>
</div>
<p class="note">{ui[note]}</p>
"""

FLASH_JS = r"""
var $=function(i){return document.getElementById(i);};
var deck=[],queue=[],cur=null,known=0,round=1,showingBack=false;
function parse(){
  var out=[];
  $('src').value.split('\n').forEach(function(line){
    var t=line.trim();if(!t)return;
    var m=t.split(/\t|\s+[-–—]\s+|\s*[,;:|]\s*/);
    if(m.length<2)return;
    var front=m[0].trim(),back=m.slice(1).join(' ').trim();
    if(front&&back)out.push({f:front,b:back});});
  return out;}
function refresh(){deck=parse();$('ncards').textContent=String(deck.length);
  $('start').disabled=!deck.length;window.__deck=deck;}
$('src').addEventListener('input',refresh);
function shuffle(a){for(var i=a.length-1;i>0;i--){
  var j=Math.floor(Math.random()*(i+1)),t=a[i];a[i]=a[j];a[j]=t;}return a;}
function faceOf(card,back){
  var d=$('dir').value;
  var flip=d==='tf'||(d==='mix'&&card.r);
  return back?(flip?card.f:card.b):(flip?card.b:card.f);}
function draw(){
  if(!queue.length){
    if(known>=deck.length||!queue.length&&!cur){finish();return;}}
  cur=queue.shift();
  showingBack=false;
  $('side').textContent=L.side_front;
  $('face').textContent=faceOf(cur,false);
  $('yes').disabled=true;$('no').disabled=true;
  $('nleft').textContent=String(queue.length+1);
  $('nround').textContent=String(round);}
function finish(){
  $('face').textContent=L.done;$('side').textContent='';
  $('yes').disabled=true;$('no').disabled=true;$('flip').disabled=true;
  $('nleft').textContent='0';}
$('start').addEventListener('click',function(){
  refresh();if(!deck.length)return;
  queue=deck.map(function(c){return {f:c.f,b:c.b,r:Math.random()<0.5};});
  if($('shuffle').value==='1')shuffle(queue);
  known=0;round=1;$('nknown').textContent='0';
  $('stage').style.display='block';$('flip').disabled=false;draw();});
$('flip').addEventListener('click',function(){
  if(!cur)return;showingBack=!showingBack;
  $('side').textContent=showingBack?L.side_back:L.side_front;
  $('face').textContent=faceOf(cur,showingBack);
  $('yes').disabled=false;$('no').disabled=false;});
$('yes').addEventListener('click',function(){
  known++;$('nknown').textContent=String(known);
  if(queue.length)draw();else finish();});
$('no').addEventListener('click',function(){
  queue.push(cur);round++;draw();});
$('csv').addEventListener('click',function(){
  refresh();
  var rows=deck.map(function(c){
    return '"'+c.f.replace(/"/g,'""')+'","'+c.b.replace(/"/g,'""')+'"';});
  var b=new Blob([rows.join('\n')],{type:'text/csv;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download='flashcards.csv';a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);},4000);});
refresh();
"""

_WORDMATE_APP = {"app_key": "wordmatelite", "app_id": "6797601720", "app_name": "Wordmate Lite",
                 "category": "EducationalApplication"}


def spec_flashcards():
    spec = dict(_WORDMATE_APP)
    spec.update({
        "slug": "flashcard-maker",
        "body": FLASH_BODY,
        "script": FLASH_JS,
        "i18n": {
            "en": {
                "q": [("flashcard maker", "D2"), ("spaced repetition", "D2"), ("vocabulary app", "store-hint")],
                "title": "Flashcard Maker — Paste a List, Study It, Export CSV. Free, No Account.",
                "description": "Turn a pasted list into flashcards you can actually study: flip, mark known or not, and anything you missed comes back in the same session. Export to CSV. No sign-up.",
                "h1": "Flashcard maker",
                "eyebrow": "Paste · study · export · no account",
                "lead": "Most flashcard sites make you register before you can look at your own list. Paste it here, study it now, and take the CSV with you.",
                "badges": ["Any separator", "Missed cards repeat", "CSV export", "No account"],
                "features": ["Parses tab, dash, comma, semicolon, colon or pipe", "Front-to-back, back-to-front or mixed", "Missed cards return later in the session", "CSV export for other apps"],
                "how": [
                    "Every non-empty line is split at the first tab, spaced dash, comma, semicolon, colon or pipe. Anything after the separator becomes the back of the card.",
                    "Direction can be front-to-back, back-to-front, or mixed, which randomises per card so you cannot coast on position.",
                    "Cards you mark as not known go to the back of the queue and come round again in the same session — the honest minimum of spaced practice, done inside one sitting.",
                    "CSV export writes quoted two-column rows, the format most flashcard apps import.",
                ],
                "never": [
                    "It is not a spaced-repetition scheduler. There is no multi-day interval algorithm and no progress carried between visits — nothing is stored.",
                    "It does not translate or generate cards for you. What you paste is what you study.",
                    "No account, no paywall on your own list, no upload.",
                ],
                "faq": [
                    ("What format should my list be in?", "One card per line with a separator: a tab, a spaced dash, a comma, a semicolon, a colon or a pipe. Text after the first separator becomes the answer, so definitions containing commas still work if you use a dash or tab."),
                    ("Does it remember my progress?", "No, and it says so rather than pretending. Nothing is stored between visits; a session is a session. Export the CSV if you want your list to last."),
                    ("Is this spaced repetition?", "Only within a single sitting: missed cards come back before the session ends. Real spaced repetition schedules reviews across days and needs an app that can store your history."),
                ],
                "app_heading": "Want the reviews to carry across days?",
                "card": "Paste a list, study it as flashcards with missed cards repeating, and export CSV.",
                "ui": {
                    "h2": "Paste your list",
                    "intro": "One card per line: term, then a separator, then the answer.",
                    "v_src": "ubiquitous — found everywhere\nmeticulous — very careful about detail\ncandid — honest and direct\nresilient — recovers quickly\npragmatic — concerned with practical results",
                    "l_dir": "Direction", "d_ft": "Term → answer", "d_tf": "Answer → term", "d_mix": "Mixed",
                    "l_shuffle": "Shuffle", "on": "On", "off": "Off",
                    "b_start": "Start studying", "b_csv": "Export CSV",
                    "r_cards": "Cards", "r_round": "Pass", "r_known": "Known", "r_left": "Left in queue",
                    "b_flip": "Flip", "b_yes": "I knew it", "b_no": "Show me again",
                    "side_front": "Question", "side_back": "Answer",
                    "done": "Session finished",
                    "note": "Nothing is stored between visits. Export the CSV if you want to keep the deck.",
                },
            },
            "ja": {
                "q": [("単語カード", "D4"), ("英単語 アプリ", "store-hint")],
                "title": "単語カード作成 — 貼り付けてすぐ学習、CSV 書き出し。無料・登録不要",
                "description": "リストを貼り付けるだけで学習できる単語カードに。めくって「わかった／もう一度」を選ぶと、間違えたカードは同じセッション内でもう一度出ます。CSV 書き出し対応。",
                "h1": "単語カードを作る",
                "eyebrow": "貼り付け · 学習 · 書き出し · 登録不要",
                "lead": "自分のリストを見るのに会員登録を求められるのはおかしい。ここに貼って、いま覚えて、CSV で持ち出してください。",
                "badges": ["区切り文字は自由", "間違えたカードは再出題", "CSV 書き出し", "登録不要"],
                "features": ["タブ・ダッシュ・カンマ・セミコロン・コロン・縦棒に対応", "表→裏／裏→表／ランダム", "間違えたカードはセッション内で再出題", "他アプリ向けの CSV 書き出し"],
                "how": [
                    "空でない各行を、最初のタブ・前後に空白のあるダッシュ・カンマ・セミコロン・コロン・縦棒で分割します。区切り以降が裏面になります。",
                    "出題方向は「表→裏」「裏→表」「ランダム」から選べます。ランダムはカードごとに切り替わるので、位置で覚えてしまうのを防げます。",
                    "「もう一度」を選んだカードは列の最後に回り、同じセッション中にまた出ます。1回の学習の中でできる、誠実な最小限の反復です。",
                    "CSV は引用符つきの2列で書き出すので、多くの単語アプリがそのまま読み込めます。",
                ],
                "never": [
                    "間隔反復（SRS）のスケジューラではありません。日をまたぐ復習間隔の計算も、訪問をまたぐ進捗の保存もありません。",
                    "翻訳もカードの自動生成もしません。貼り付けたものがそのまま出題されます。",
                    "アカウント不要、自分のリストに課金の壁なし、アップロードなし。",
                ],
                "faq": [
                    ("どんな形式で貼ればよいですか？", "1行に1枚、間に区切り文字（タブ、前後に空白のあるダッシュ、カンマ、セミコロン、コロン、縦棒）を入れてください。最初の区切り以降が答えになるので、答えにカンマが含まれる場合はタブかダッシュを使ってください。"),
                    ("進捗は保存されますか？", "保存されません。そう書いてある通りで、ごまかしません。1回のセッションで完結します。残したい場合は CSV を書き出してください。"),
                    ("これは間隔反復ですか？", "1回の学習の中だけです。間違えたカードは終了前にもう一度出ますが、本当の間隔反復は日をまたいで復習日を決めるもので、履歴を保存できるアプリが必要です。"),
                ],
                "app_heading": "日をまたいで復習を続けたいですか？",
                "card": "リストを貼り付けて単語カードとして学習し、CSV に書き出せます。",
                "ui": {
                    "h2": "リストを貼り付ける",
                    "intro": "1行に1枚。単語、区切り文字、意味の順に書いてください。",
                    "v_src": "ubiquitous — どこにでもある\nmeticulous — 細部まで几帳面な\ncandid — 率直な\nresilient — 立ち直りが早い\npragmatic — 実用本位の",
                    "l_dir": "出題方向", "d_ft": "表 → 裏", "d_tf": "裏 → 表", "d_mix": "ランダム",
                    "l_shuffle": "順番をシャッフル", "on": "する", "off": "しない",
                    "b_start": "学習を始める", "b_csv": "CSV で書き出す",
                    "r_cards": "カード数", "r_round": "周回", "r_known": "わかった", "r_left": "残り",
                    "b_flip": "めくる", "b_yes": "わかった", "b_no": "もう一度",
                    "side_front": "問題", "side_back": "答え",
                    "done": "セッション終了",
                    "note": "訪問をまたいだ保存はしません。残したい場合は CSV を書き出してください。",
                },
            },
            "zh-Hant": {
                "q": [("英文單字卡", "D3"), ("背單字", "store-hint")],
                "title": "單字卡製作 — 貼上清單就能背，可匯出 CSV。免費、免註冊",
                "description": "把清單貼上就變成可以直接練的單字卡：翻面、標記記得或沒記得，沒記得的會在同一次練習裡再出現。可匯出 CSV，不用註冊。",
                "h1": "單字卡製作",
                "eyebrow": "貼上 · 練習 · 匯出 · 免註冊",
                "lead": "多數單字卡網站要先註冊才能看自己的清單。這裡貼上就能練，練完把 CSV 帶走。",
                "badges": ["分隔符號隨你用", "沒記得的會再出現", "匯出 CSV", "免註冊"],
                "features": ["支援 Tab、破折號、逗號、分號、冒號、直線", "正面→背面／背面→正面／隨機", "答錯的卡在同一次練習中重出", "可匯入其他 App 的 CSV"],
                "how": [
                    "每一非空白行會在第一個 Tab、前後有空白的破折號、逗號、分號、冒號或直線處切開，分隔符號之後的內容就是卡片背面。",
                    "出題方向可選正面→背面、背面→正面，或隨機（每張卡各自決定，避免你靠位置記答案）。",
                    "標記「再看一次」的卡片會排到隊伍尾端，在同一次練習中再出現一次——一次坐下能做到的、誠實的最小反覆。",
                    "CSV 以加引號的兩欄輸出，大多數單字卡 App 都能直接匯入。",
                ],
                "never": [
                    "這不是間隔重複（SRS）排程器。沒有跨天的複習間隔演算法，也不會保存跨次的進度。",
                    "不翻譯，也不會替你生成卡片。你貼什麼就練什麼。",
                    "不用帳號、你自己的清單不會被鎖在付費牆後、不上傳。",
                ],
                "faq": [
                    ("清單要用什麼格式？", "一行一張卡，中間放一個分隔符號：Tab、前後有空白的破折號、逗號、分號、冒號或直線。第一個分隔符號之後都算答案，所以答案裡有逗號時請改用 Tab 或破折號。"),
                    ("會記住我的進度嗎？", "不會，這裡直接說清楚而不是假裝有。一次練習就是一次，想留下清單請匯出 CSV。"),
                    ("這算間隔重複嗎？", "只在單次練習內：沒記得的卡在結束前會再出現一次。真正的間隔重複要跨天安排複習日，需要能保存歷史紀錄的 App。"),
                ],
                "app_heading": "想讓複習跨天延續下去嗎？",
                "card": "貼上清單就能當單字卡練習，答錯會重出，並可匯出 CSV。",
                "ui": {
                    "h2": "貼上你的清單",
                    "intro": "一行一張卡：單字、分隔符號、意思。",
                    "v_src": "ubiquitous — 到處都是的\nmeticulous — 一絲不苟的\ncandid — 直率坦白的\nresilient — 復原力強的\npragmatic — 講求實效的",
                    "l_dir": "出題方向", "d_ft": "正面 → 背面", "d_tf": "背面 → 正面", "d_mix": "隨機",
                    "l_shuffle": "打亂順序", "on": "開", "off": "關",
                    "b_start": "開始練習", "b_csv": "匯出 CSV",
                    "r_cards": "卡片數", "r_round": "第幾輪", "r_known": "記得", "r_left": "剩餘",
                    "b_flip": "翻面", "b_yes": "我記得", "b_no": "再看一次",
                    "side_front": "題目", "side_back": "答案",
                    "done": "這輪練習結束",
                    "note": "不會跨次保存任何資料。想留著清單請匯出 CSV。",
                },
            },
        },
    })
    return spec


SPEC_BUILDERS = [
    spec_image_compressor,
    spec_white_noise,
    spec_sleep_cycles,
    spec_packing_list,
    spec_travel_budget,
    spec_voice_to_text,
    spec_photo_sharpen,
    spec_film_filter,
    spec_redact_pdf,
    spec_math_worksheet,
    spec_reward_chart,
    spec_letter_tracing,
    spec_duplicate_photos,
    spec_flashcards,
]

INDEX_CARDS = {
    "passport-photo-checker": "Check a passport/ID photo against 10 official sizes and download a centered crop — nothing uploaded.",
    "currency-converter": "Convert 30 currencies on dated ECB reference rates that always show their source.",
    "paycheck-budget-calculator": "Split each paycheck into needs, wants and savings with editable, transparent math.",
    "resume-template-maker": "Type, preview an ATS-safe template and print to PDF — no sign-up, no watermark.",
    "jpg-to-pdf": "Combine photos or scans into one PDF entirely in your browser — no upload, no watermark.",
    "photo-mosaic-blur": "Pixelate, blur or black out parts of a photo before sharing — with honest limits.",
}


def tools_dir(lang):
    return TOOLS if lang == "en" else PAGES / lang / "tools"


def update_index(tools, lang="en"):
    index = tools_dir(lang) / "index.html"
    if not index.exists():
        return 0
    text = index.read_text(encoding="utf-8")
    marker = "</section></main>"
    if marker not in text:
        raise RuntimeError(f"{index} missing grid marker")
    added = 0
    for tool in tools:
        slug = tool["slug"]
        if f'href="{slug}.html"' in text:
            continue
        blurb = tool.get("card") or INDEX_CARDS[slug]
        title = tool["h1"]
        if lang == "en":
            title = title[0].upper() + title[1:]
        card = (
            f'<article class="card third" data-tool="{slug}">'
            f'<h2><a href="{slug}.html">{esc(title)}</a></h2>'
            f"<p>{esc(blurb)}</p></article>"
        )
        text = text.replace(marker, card + marker, 1)
        added += 1
    if added:
        index.write_text(text, encoding="utf-8")
    return added


# Legacy English-only tools worth linking from the new pages (they exist and
# are demand-backed too).  Slug -> English label; localized pages fall back to
# the English page when no localized sibling exists, which is honest and
# still useful.
FALLBACK_RELATED = {
    "currency-converter": "Currency converter",
    "passport-photo-checker": "Passport photo checker",
    "paycheck-budget-calculator": "Paycheck budget calculator",
    "jpg-to-pdf": "JPG to PDF converter",
    "resume-template-maker": "Resume template maker",
    "photo-mosaic-blur": "Photo mosaic & blur",
}


def fill_related(new_tools):
    """Cross-link the new tools inside their own locale, then top up with the
    English classics.  Every href is verified against a page we actually
    generate or a file already on disk."""
    by_lang = {}
    for tool in new_tools:
        by_lang.setdefault(tool["lang"], []).append(tool)
    for lang, group in by_lang.items():
        slugs = [t["slug"] for t in group]
        for i, tool in enumerate(group):
            related = []
            for step in range(1, len(group)):
                sib = group[(i + step) % len(group)]
                if sib["slug"] == tool["slug"]:
                    continue
                related.append((f"{sib['slug']}.html", sib["h1"]))
                if len(related) >= 3:
                    break
            for slug, label in FALLBACK_RELATED.items():
                if len(related) >= 4:
                    break
                if slug in slugs:
                    continue
                target = tools_dir(lang) / f"{slug}.html"
                href = (
                    f"{slug}.html" if target.exists()
                    else f"{SITE}/tools/{slug}.html"
                )
                related.append((href, label))
            tool["related"] = related


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


def check_app_pairing(spec):
    """Free-version-first rule + live App Store id, enforced at build time.

    30-day ASC data: paid siblings convert at 0–2.7% product-page→download,
    free/Lite siblings at 10.9–64.3%.  A tool page is a category-demand context,
    so it must point at the free-first key from geo/app_pairs.py.
    """
    try:
        from app_pairs import free_first_key  # noqa: PLC0415
        import sys as _sys  # noqa: PLC0415
        root = str(HERE.parent)
        if f"{root}/social" not in _sys.path:
            _sys.path.insert(0, f"{root}/social")
        from videogen.registry import APPSTORE  # noqa: PLC0415
    except Exception as exc:  # registry unavailable -> skip, do not break build
        print(f"app pairing check skipped: {exc}")
        return
    key = spec["app_key"]
    want = free_first_key(key)
    if want != key:
        raise RuntimeError(
            f"{spec['slug']}: app_key {key!r} is the paid sibling; use {want!r}"
        )
    real = APPSTORE.get(key)
    if real and str(real) != str(spec["app_id"]):
        raise RuntimeError(
            f"{spec['slug']}: app_id {spec['app_id']} != registry {real} for {key}"
        )


def build_new_tools():
    tools = []
    for spec in (builder() for builder in SPEC_BUILDERS):
        check_app_pairing(spec)
        for lang in spec["i18n"]:
            if lang not in CHROME:
                raise RuntimeError(f"{spec['slug']}: no chrome for {lang}")
            missing = [
                k for k in ("q", "title", "description", "h1", "lead", "eyebrow",
                            "badges", "features", "how", "never", "faq",
                            "app_heading", "card", "ui")
                if k not in spec["i18n"][lang]
            ]
            if missing:
                raise RuntimeError(f"{spec['slug']}/{lang}: missing {missing}")
            if not spec["i18n"][lang]["q"]:
                raise RuntimeError(
                    f"{spec['slug']}/{lang}: no verified query — do not ship the page"
                )
            tools.append(make_tool(spec, lang))
    fill_related(tools)
    return tools


def demand_report(tools):
    """slug -> {locale: [(query, level)]} — why each page exists."""
    out = {}
    for tool in tools:
        out.setdefault(tool["slug"], {})[tool["lang"]] = tool["demand"]
    return out


def main():
    TOOLS.mkdir(parents=True, exist_ok=True)
    refresh_rates()
    legacy = [build() for build in TOOL_BUILDERS]
    fresh = build_new_tools()
    written = 0
    for tool in legacy + fresh:
        lang = tool.get("lang", "en")
        target = tools_dir(lang)
        target.mkdir(parents=True, exist_ok=True)
        out = target / f"{tool['slug']}.html"
        page = render_page(tool)
        if not out.exists() or out.read_text(encoding="utf-8") != page:
            out.write_text(page, encoding="utf-8")
            written += 1
    added = 0
    for lang in LOCALES:
        group = [t for t in legacy + fresh if t.get("lang", "en") == lang]
        if group:
            added += update_index(group, lang)
    count = write_tools_sitemap()
    langs = sorted({t.get("lang", "en") for t in fresh})
    print(
        f"demand_tools: {len(legacy)} legacy + {len(fresh)} demand pages "
        f"({len(SPEC_BUILDERS)} tools × {langs}), {written} written, "
        f"{added} new index cards, sitemap {count} urls"
    )


if __name__ == "__main__":
    main()
