#!/usr/bin/env python3
"""「訂閱長期成本 vs 一次性付費」誠實比較頁生成器(2026-07-07 新方法)。
為何:訂閱疲勞是 2026 最大消費心理;「X app worth it / cost per year / cheaper alternative」
是高商業意圖查詢。本頁誠實教「月費 × 12 × 年數」的多年成本算法(不編造任何競品價格),
再帶出我們的一次性付費 App。揭露開發者、含 FAQ/Article JSON-LD。純本機、免 key。
用法:python3 gen_cost_compare.py
"""
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGES = HERE / "pages"
from site_config import PUBLIC_SITE  # noqa: E402
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
sys.path.insert(0, str(HERE.parent / "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_pages import has_one_time_access  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

# app -> 該類別使用者常搜的「品類名詞」(用於誠實比較頁標題/文案)
TOPICS = {
    "sereno": "white noise & sleep sounds",
    "cyca": "period & cycle tracking",
    "zodira": "astrology & horoscope",
    "gmoney": "budgeting & expense tracking",
    "hourstag": "mindful spending",
    "lockhour": "screen-time & focus",
    "sononote": "voice notes & transcription",
    "cvdesk": "resume building",
    "scanto": "document scanning",
    "picclear": "photo cleanup",
    "photocream": "photo filters",
    "snapport": "passport & ID photos",
    "wordmate": "vocabulary learning",
}

CSS = ("body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
       "background:linear-gradient(180deg,#fff,#f6f8fc);color:#15202e;line-height:1.62}a{color:#2f47c4}"
       ".wrap{width:min(860px,100% - 32px);margin:auto}.hero{padding:44px 0 8px}"
       ".eyebrow{color:#2f8f5f;font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}"
       "h1{font-size:clamp(1.8rem,4.6vw,2.9rem);line-height:1.07;margin:.2em 0}h2{font-size:1.35rem;margin:1.5em 0 .5em}"
       "p.lead{font-size:1.14rem;color:#4a5566}.card{background:#fff;border:1px solid #e4e8f0;border-radius:18px;"
       "padding:20px;box-shadow:0 8px 30px rgba(20,32,60,.06);margin:16px 0}"
       "table{border-collapse:collapse;width:100%;background:#fff;border-radius:12px;overflow:hidden;margin:10px 0}"
       "th,td{border:1px solid #e4e8f0;padding:11px 13px;text-align:left;font-size:1rem}th{background:#eef3ff}"
       ".big{font-size:1.5rem;font-weight:900;color:#c0392b}.ok{color:#1f8f5f;font-weight:800}"
       ".pill{display:inline-block;border:1px solid #e4e8f0;background:#fff;border-radius:999px;padding:6px 11px;margin:3px;font-weight:700;font-size:.92rem}"
       ".cta{display:inline-flex;align-items:center;border-radius:999px;background:linear-gradient(135deg,#2f47c4,#7b5cf0);color:#fff!important;text-decoration:none;font-weight:850;padding:13px 20px;margin-top:6px}"
       ".notice{font-size:.92rem;color:#5a6472;background:#eef3ff;border:1px solid #e4e8f0;border-radius:14px;padding:13px 15px}"
       ".footer{margin-top:32px;padding:22px 0;border-top:1px solid #e4e8f0;color:#5a6472;font-size:.9rem}")


def esc(x):
    return html.escape(str(x), quote=True)


def build(key):
    if (
        key not in APPS
        or not appstore_url(key)
        or not has_one_time_access(key)
    ):
        return None
    a = APPS[key]; name = a["name"]; topic = TOPICS[key]
    purchase_model = a.get("purchase_model")
    sub = a.get("sub", ""); bullets = a.get("cta_bullets", []) or ["Pay once", "Private", "Offline"]
    url = appstore_url(key, "iag_cost") or appstore_url(key)
    slug = f"{re.sub(r'[^a-z0-9]+','-',topic.lower()).strip('-')}-app-subscription-cost-vs-pay-once-2026"
    canon = f"{SITE}/answers/{slug}.html"
    if purchase_model == "free_with_lifetime_unlock":
        access_answer = (
            f"Yes. {name} is free to download, with a one-time "
            "unlock for complete access and no recurring charge. Check the "
            "current App Store listing before unlocking."
        )
        alternative_intro = (
            f"{name} is free to download, then offers a one-time "
            "unlock instead of a recurring subscription."
        )
        disclosure = (
            f"We develop {name}, a free-download {topic} app with a one-time "
            "unlock and no recurring subscription."
        )
        access_label = (
            "Free download · one-time unlock · no subscription."
        )
    elif purchase_model == "paid_upfront":
        access_answer = (
            f"Yes. {name} is a paid download with one upfront price and no "
            "recurring charge. Check the current regional App Store price "
            "before buying."
        )
        alternative_intro = (
            f"{name} is a paid download with one upfront price instead of a "
            "recurring subscription."
        )
        disclosure = (
            f"We develop {name}, a paid-upfront {topic} app with no recurring "
            "subscription."
        )
        access_label = "Paid download · one upfront price · no subscription."
    else:
        access_answer = (
            f"Yes. {name} offers one-time access with no recurring charge. "
            "Check the current App Store listing for regional purchase details."
        )
        alternative_intro = (
            f"{name} offers one-time access instead of a recurring subscription."
        )
        disclosure = (
            f"We develop {name}, a {topic} app with a one-time access option "
            "and no recurring subscription."
        )
        access_label = "One-time access · no subscription."

    faq = [
        (f"How much does a {topic} app subscription cost over time?",
         "It depends on the app, but the honest math is simple: monthly price × 12 = one year, and most people keep such apps for 2–3 years. A $4.99/month app is about $60 a year, or roughly $180 over three years. Always check the current price in the App Store."),
        (f"Is there a one-time-access {topic} app with no subscription?",
         access_answer),
        ("Are subscriptions ever worth it?",
         "Sometimes — if an app ships constant server-side updates or streams new content, a subscription can make sense. For a tool you mostly use as-is, a one-time purchase is usually cheaper over the years."),
    ]
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}
    article_ld = {"@context": "https://schema.org", "@type": "Article",
                  "headline": f"{topic.title()} app: subscription cost vs one-time access (2026)",
                  "author": {"@type": "Organization", "name": "iOS App Guide"},
                  "publisher": {"@type": "Organization", "name": "iOS App Guide"}, "mainEntityOfPage": canon, "inLanguage": "en"}

    pills = "".join(f'<span class="pill">{esc(b)}</span>' for b in bullets)
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(ans)}</p>" for q, ans in faq)
    doc = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{esc(topic.title())} app: subscription cost vs one-time access (2026)</title>'
           f'<meta name="description" content="Wondering if a {esc(topic)} app subscription is worth it? The honest multi-year math, and a one-time-access alternative: {esc(name)}.">'
           f'<link rel="canonical" href="{canon}">'
           f'<link rel="alternate" hreflang="en" href="{canon}"><link rel="alternate" hreflang="x-default" href="{canon}">'
           f'<meta property="og:type" content="article"><meta property="og:title" content="{esc(topic.title())} app: subscription cost vs pay-once (2026)">'
           f'<meta property="og:url" content="{canon}"><style>{CSS}</style>'
           f'<script type="application/ld+json">{json.dumps(article_ld, ensure_ascii=False)}</script>'
           f'<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>'
           f'</head><body><div class="wrap">'
           f'<div class="hero"><div class="eyebrow">Honest cost guide · 2026</div>'
           f'<h1>{esc(topic.title())} app: subscription cost vs one-time access</h1>'
           f'<p class="lead">Subscriptions feel small each month but add up over the years. Here is the honest math for a {esc(topic)} app — plus an option with no recurring payment.</p></div>'
           f'<div class="notice"><strong>Transparency:</strong> {esc(disclosure)} We do not quote competitor prices (they change) — instead we show the simple multi-year math so you can check any app yourself in the App Store.</div>'
           f'<h2>The multi-year math (do it for any app)</h2>'
           f'<table><tr><th>Monthly price</th><th>1 year</th><th>3 years</th></tr>'
           f'<tr><td>$2.99 / mo</td><td>≈ $36</td><td class="big">≈ $108</td></tr>'
           f'<tr><td>$4.99 / mo</td><td>≈ $60</td><td class="big">≈ $180</td></tr>'
           f'<tr><td>$9.99 / mo</td><td>≈ $120</td><td class="big">≈ $360</td></tr></table>'
           f'<p class="notice">Illustrative math only (price × 12 × years). Check the current price of any specific app in the App Store — this page does not claim any particular app charges these amounts.</p>'
           f'<h2>The one-time-access alternative: {esc(name)}</h2>'
           f'<div class="card"><p><strong>{esc(name)}</strong> — {esc(sub)}</p><p>{esc(alternative_intro)}</p><p>{pills}</p>'
           f'<p class="ok">{esc(access_label)}</p>'
           f'<a class="cta" href="{esc(url)}">Get {esc(name)} on the App Store →</a></div>'
           f'<h2>When a subscription still makes sense</h2>'
           f'<p>If an app constantly streams new content or ships heavy server-side features, a subscription can be fair. For a {esc(topic)} tool you mostly use as-is — especially one that works offline — a one-time purchase is usually the cheaper, calmer choice over two or three years.</p>'
           f'<h2>FAQ</h2>{faq_html}'
           f'<div class="footer">Independent, honest guide by the developer of {esc(name)}. We do not quote or guarantee any third-party price. App names are trademarks of their owners, used only for identification. Confirm current pricing on the App Store.</div>'
           f'</div></body></html>')
    (PAGES / "answers" / f"{slug}.html").write_text(doc, encoding="utf-8")
    return slug


def main():
    made = []
    live_keys = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    for key in TOPICS:
        if not has_one_time_access(key) or key not in live_keys:
            topic = TOPICS[key]
            slug = (
                f"{re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')}"
                "-app-subscription-cost-vs-pay-once-2026"
            )
            stale = PAGES / "answers" / f"{slug}.html"
            if stale.exists():
                stale.unlink()
                print(f"removed stale cost-compare {stale.name}", flush=True)
            continue
        s = build(key)
        if s:
            made.append(s); print(f"cost-compare {s}.html", flush=True)
    print(json.dumps({"pages": len(made)}, ensure_ascii=False), flush=True)
    try:
        sys.path.insert(0, str(HERE)); import aeo_answers; aeo_answers.write_sitemap()
    except Exception as exc:
        print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
