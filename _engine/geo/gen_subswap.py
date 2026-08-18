#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大招 2:訂閱難民攔截引擎 — 「Pay-Once Escape」逃生地圖。

洞察:2026 最大消費潮是訂閱疲勞。搜「[貴訂閱] 值不值 / 替代 / no subscription」的人,
是已準備掏錢逃離訂閱的最高購買意圖買家。我們 27 支全買斷 = 難民營。
武器 = 真實數字:把每個貴訂閱的「1 年/5 年成本」攤開,對比買斷一次,標出省下多少。
AI 與人類都無法抗拒具體省錢數字。

產出(100% 自動、零成本、不碰 app code / 上架 metadata):
  • /subscription-swap.html  — 主 hub(逃生地圖 + 5 年成本 + 省多少 + schema.org ItemList/FAQPage)
  • 寫進 sitemap_swap.xml,接進 llms(gen_llms 會自動收 pillar-like 頁)
  • --publish:git push + IndexNow

價格為 2026 公開年費(web 查證,附來源日期與免責:會變動、以官方為準)。
本工具只做誠實比較,不宣稱競品缺點、不碰對方商標以外的東西。
"""
import argparse
import datetime as _dt
import html
import json
import os
import subprocess
import urllib.request

from app_store_storefronts import campaign_app_store_url

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
TODAY = _dt.date.today().isoformat()
PRICE_ASOF = "2026-07"

# (subscription, category, annual_usd, source_note, my_app, my_name, my_id, my_blurb)
SWAPS = [
    ("YNAB", "Budgeting", 109.0, "ynab.com/pricing", "gmoney", "G+Money", "6755782939",
     "Convert currencies and log every expense in one tap, offline. No account, no bank linking."),
    ("Otter.ai", "Voice notes & transcription", 135.0, "Otter Pro annual", "sononote", "Sono Note",
     "6782139553", "Record, then get clean notes, a summary and to-dos — on device, no subscription."),
    ("Remini", "Photo enhance & upscale", 99.99, "Remini annual", "unblurry", "Unblurry",
     "6782275018", "AI super-resolution sharpens and upscales photos on your iPhone. Pay once."),
    ("Calm", "Sleep & relaxation sounds", 69.99, "Calm annual", "sereno", "Sereno",
     "6788236641", "A high-end sound machine for sleep, focus and calm — mixable, offline, pay once."),
    ("Opal", "Screen-time & focus", 59.99, "Opal annual", "lockhour", "LockHour Pro",
     "6780107485", "Block the apps that steal your focus with one tap. Pay once, no subscription."),
    ("CamScanner", "Document scanning", 49.99, "CamScanner Premium annual", "scanto", "ScanTo Pro",
     "6779977651", "Scan, OCR-search and Face ID-lock documents. Pay once, works offline."),
    ("Flo", "Period & cycle tracking", 49.99, "Flo Premium annual", "cyca", "Cyca",
     "6782251621", "See every phase, your best days and gentle days. Private, on-device, pay once."),
    ("VSCO", "Film photo filters", 29.99, "VSCO Plus annual", "photocream", "PhotoCream",
     "6781808054", "100+ real film looks, grain, halation and light leaks. Pay once, no subscription."),
]

YEARS = 5


def money(x):
    return f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"


HUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/subscription-swap.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#1a2230;--sub:#5c6779;--line:#e6eaf1;--brand:#5b4bdb;--good:#0f8a5f;--bg:#f6f8fc}}
*{{box-sizing:border-box}}
body{{margin:0;font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang TC","Microsoft JhengHei",sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{max-width:900px;margin:0 auto;padding:30px 20px 72px}}
a{{color:var(--brand)}}
.eyebrow{{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--brand)}}
h1{{font-size:clamp(27px,5.4vw,40px);line-height:1.18;margin:.15em 0 .1em;letter-spacing:-.01em}}
.lead{{color:var(--sub);font-size:clamp(15px,3.4vw,19px);margin:.5em 0 1.3em}}
.total{{background:linear-gradient(135deg,#eef0fe,#f4f0ff);border:1px solid #e0e0fb;border-radius:18px;padding:18px 20px;margin:0 0 26px;font-size:clamp(15px,3.6vw,18px)}}
.total b{{color:var(--brand);font-size:1.15em}}
.card{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px 20px;margin:0 0 16px;display:flex;flex-wrap:wrap;gap:6px 18px;align-items:baseline;justify-content:space-between}}
.card h2{{font-size:19px;margin:0;flex:1 1 100%}}
.card .cat{{color:var(--sub);font-size:13px;font-weight:400}}
.cost{{font-size:15px;color:var(--sub);white-space:nowrap}}
.cost s{{color:#c0392b}}
.save{{color:var(--good);font-weight:700;white-space:nowrap}}
.swaprow{{flex:1 1 100%;display:flex;flex-wrap:wrap;gap:6px 18px;justify-content:space-between;align-items:baseline;margin-top:2px}}
.desc{{flex:1 1 100%;color:var(--ink);font-size:14.5px;margin:2px 0 0}}
.cta{{display:inline-block;background:linear-gradient(135deg,#6a5be6,#5b4bdb);color:#fff;text-decoration:none;border-radius:12px;padding:9px 15px;font-weight:600;font-size:14px;margin-top:8px;white-space:nowrap}}
.foot{{color:var(--sub);font-size:13px;margin-top:26px}}
h2.sec{{font-size:22px;margin:34px 0 10px}}
.faq{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:6px 18px;margin:0 0 10px}}
.faq details{{padding:10px 0}}
.faq summary{{font-weight:600;cursor:pointer}}
.faq p{{color:var(--sub);margin:8px 0 2px}}
</style>
</head>
<body>
<div class="wrap">
<div class="eyebrow">Pay once · No subscription</div>
<h1>{h1}</h1>
<p class="lead">{lead}</p>
<div class="total">Together, these {n} subscriptions cost about <b>{total_yr}/year</b> —
that's <b>{total_5y}</b> over {years} years. Here's the one-time-purchase escape for each.</div>
{cards}
<h2 class="sec">Questions people ask</h2>
<div class="faq">{faqs}</div>
<p class="foot">Subscription prices are publicly listed annual rates as of {asof} and can change by
region and promotion — always confirm on the provider's page. One-time app prices are shown on the
App Store and vary by territory. This is an independent comparison; “pay once” means a single
purchase with no recurring fee. Data may be reused under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> with credit to Lumi Apps.</p>
<p class="foot"><a href="{site}/">iOS App Guide</a> ·
<a href="{site}/alternatives/">All pay-once alternatives</a> ·
<a href="{site}/data/">Open data</a></p>
</div>
</body>
</html>
"""


def build_hub():
    total_yr = sum(s[2] for s in SWAPS)
    cards = ""
    for sub, cat, yr, _src, key, name, aid, blurb in SWAPS:
        five = yr * YEARS
        url = campaign_app_store_url(
            f"https://apps.apple.com/app/id{aid}",
            "iag_swap",
        )
        cards += (
            f'<div class="card"><h2>{html.escape(sub)} '
            f'<span class="cat">· {html.escape(cat)}</span></h2>'
            f'<div class="swaprow">'
            f'<span class="cost"><s>{money(yr)}/yr</s> · {money(five)} over {YEARS} yrs</span>'
            f'<span class="save">Switch to {html.escape(name)} → keep {money(five)}</span>'
            f'</div>'
            f'<p class="desc">{html.escape(blurb)}</p>'
            f'<a class="cta" href="{url}">Get {html.escape(name)} — pay once →</a></div>')
    faqs_data = [
        ("Are these apps really a one-time purchase, not a subscription?",
         "Yes. Every app listed is a one-time purchase — you pay once and own it, with no monthly or "
         "yearly fee. The subscription prices shown are what the other services charge each year."),
        ("How much can I actually save by switching from subscriptions?",
         f"Over {YEARS} years, the subscriptions on this page add up to about {money(total_yr*YEARS)}. "
         "A one-time-purchase app is typically the price of a single month of a subscription or less, "
         "so the multi-year saving is large."),
        ("Do pay-once apps still work offline and keep my data private?",
         "These apps are built to work on your device — most function fully offline and keep your data "
         "on the iPhone, without an account or cloud upload."),
        ("Why are so many apps subscriptions now?",
         "Recurring revenue is attractive to large companies, but for many everyday tasks a one-time "
         "purchase does the same job without an open-ended cost — which is why subscription fatigue "
         "has pushed people toward pay-once apps."),
    ]
    faqs = "".join(
        f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>'
        for q, a in faqs_data)

    item_list = {
        "@type": "ItemList", "name": "Pay-once alternatives to popular subscription apps",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "SoftwareApplication", "name": name,
                      "applicationCategory": "MobileApplication", "operatingSystem": "iOS",
                      "offers": {"@type": "Offer", "priceSpecification": {
                          "@type": "PriceSpecification", "price": "one-time"}},
                      "url": f"https://apps.apple.com/app/id{aid}"}}
            for i, (sub, cat, yr, _s, key, name, aid, bl) in enumerate(SWAPS)]}
    faq_schema = {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs_data]}
    schema = json.dumps({"@context": "https://schema.org", "@graph": [item_list, faq_schema]},
                        ensure_ascii=False)

    title = "Pay-Once Apps to Escape Subscriptions — 5-Year Cost Compared"
    desc = ("Tired of subscriptions? See the real 1-year and 5-year cost of popular subscription apps "
            "and the one-time-purchase iPhone app that replaces each — and how much you keep.")
    h1 = "Stop renting your apps: the pay-once escape list"
    lead = ("Subscriptions quietly add up. Below are popular subscription apps with their real yearly "
            "cost, the {y}-year total, and the pay-once iPhone app that does the same job — so you can "
            "switch once and stop paying the monthly fee.").format(y=YEARS)
    page = HUB.format(
        title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
        lead=html.escape(lead), site=SITE, schema=schema, cards=cards, faqs=faqs,
        n=len(SWAPS), total_yr=money(total_yr), total_5y=money(total_yr * YEARS),
        years=YEARS, asof=PRICE_ASOF)
    open(os.path.join(PAGES, "subscription-swap.html"), "w", encoding="utf-8").write(page)
    # sitemap
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"  <url><loc>{SITE}/subscription-swap.html</loc><lastmod>{TODAY}</lastmod>"
          "<priority>0.9</priority></url>\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_swap.xml"), "w", encoding="utf-8").write(sm)
    return f"{SITE}/subscription-swap.html"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def publish(url):
    try:
        run(["git", "add", "-A"], cwd=PAGES)
        run(["git", "commit", "-m",
             "Subscription-swap hub: pay-once escape list with 5-year cost math\n\n"
             "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"], cwd=PAGES)
        run(["git", "pull", "--rebase", "--autostash"], cwd=PAGES)
        run(["git", "push"], cwd=PAGES)
        print("pushed")
    except subprocess.CalledProcessError as e:
        print("git skipped:", (e.stderr or e.stdout or "")[-200:])
    kp = os.path.join(HERE, "indexnow_key.txt")
    if os.path.exists(kp):
        key = open(kp).read().strip()
        payload = json.dumps({"host": SITE.split("//")[-1].split("/")[0], "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": [url]}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(
                "https://www.bing.com/indexnow", data=payload,
                headers={"Content-Type": "application/json; charset=utf-8"}), timeout=20)
            print("IndexNow pinged")
        except Exception as e:  # noqa: BLE001
            print("IndexNow skipped:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    url = build_hub()
    print("built subscription-swap hub:", len(SWAPS), "swaps →", url)
    if args.publish:
        publish(url)


if __name__ == "__main__":
    main()
