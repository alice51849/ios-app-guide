#!/usr/bin/env python3
"""「Best X app (2026)」誠實榜單頁生成器(2026-07-07 新方法)。
為何:AI 問答引擎(ChatGPT/Perplexity/Google AI Overviews)最常被問「best X app / 最好的 X app」,
但站上只有單一 App 買家指南與 1v1 比較頁,沒有榜單型頁面來接這種最高流量的查詢。
誠實原則:①明確揭露這是我們自家 App ②依實際定價模式寫文案 ③公平點名熱門競品
④不捏造「排名全部 App」⑤只用 registry 既有事實。純本機、免 key。
用法:python3 gen_roundups.py
"""
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGES = HERE / "pages"
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$")
sys.path.insert(0, str(HERE.parent / "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_pages import pricing_profile  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

# 每個 App 的榜單主題名詞(人們搜「best <topic> apps」用語)。
TOPICS = {
    "snapport": "passport & ID photo",
    "scanto": "PDF scanner & OCR",
    "picclear": "photo cleaner & storage",
    "unblurry": "photo enhancer & unblur",
    "photocream": "film camera & filter",
    "zafe": "private photo vault",
    "sononote": "voice note & transcription",
    "cvdesk": "resume & CV maker",
    "gmoney": "budget & expense",
    "hourstag": "mindful spending",
    "lockhour": "screen time & app blocker",
    "cyca": "period & cycle tracker",
    "zodira": "astrology & tarot",
    "tripbee": "trip planner",
    "sereno": "sleep & white noise",
    "aim990": "TOEIC test prep",
    "lumiletterspro": "kids ABC phonics",
    "lumimathpro": "kids early math",
    "lumimissionpro": "kids routine chart",
    "lumibopomofo": "kids zhuyin bopomofo",
    "mochi": "to-do list & checklist",
    "lumiweather": "family weather",
}


def load_competitors():
    try:
        data = json.load(open(HERE / "reports" / "aeo_sov.json", encoding="utf-8"))
        return {r["key"]: [c for c, _ in r.get("top_competitors", [])][:3] for r in data.get("results", [])}
    except Exception:
        return {}


COMP = load_competitors()

# Fallback competitors for topics not yet in aeo_sov.json (real, verified App
# Store apps; used only for fair "for example" naming, not ranking claims).
EXTRA_COMP = {
    "aim990": ["santa toeic", "abceed", "ets toeic"],
    "lumiletterspro": ["duolingo abc", "endless alphabet", "khan academy kids"],
    "lumimathpro": ["todo math", "moose math", "khan academy kids"],
    "lumimissionpro": ["tiimo", "brili routines", "first then visual schedule"],
    "lumibopomofo": ["bopomofo master", "let's zhuyin", "chinese zhuyin bopomo fun"],
    "mochi": ["todoist", "ticktick", "any.do"],
    "lumiweather": ["carrot weather", "weather line", "hello weather"],
}
CSS = ("body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
       "background:linear-gradient(180deg,#fff,#f7f7fb);color:#161622;line-height:1.62}a{color:#3840d0}"
       ".wrap{width:min(880px,100% - 32px);margin:auto}.hero{padding:42px 0 8px}"
       ".eyebrow{color:#5b5ff2;font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}"
       "h1{font-size:clamp(1.9rem,5vw,3rem);line-height:1.06;margin:.2em 0}h2{font-size:1.4rem;margin:1.4em 0 .5em}"
       "p.lead{font-size:1.14rem;color:#5d6370}.card{background:#fff;border:1px solid #e6e7ef;border-radius:20px;"
       "padding:22px;box-shadow:0 8px 30px rgba(31,34,78,.06);margin:16px 0}.pill{display:inline-block;border:1px solid #e6e7ef;"
       "background:#fff;border-radius:999px;padding:6px 11px;margin:3px;font-weight:700;font-size:.92rem}"
       ".cta{display:inline-flex;align-items:center;border-radius:999px;background:linear-gradient(135deg,#5b5ff2,#8b5cf6);"
       "color:#fff!important;text-decoration:none;font-weight:850;padding:13px 20px;margin-top:8px}"
       "ul{margin:.4em 0}li{margin:.35em 0}.notice{font-size:.92rem;color:#626875;background:#f2f5ff;border:1px solid #e6e7ef;"
       "border-radius:14px;padding:14px 16px}.footer{margin-top:34px;padding:24px 0;border-top:1px solid #e6e7ef;color:#5d6370;font-size:.9rem}")


def esc(x):
    return html.escape(str(x), quote=True)


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def legacy_slug(topic):
    return f"best-pay-once-{slugify(topic)}-app-2026"


def answer_hreflang_block(slug, canonical):
    filename = f"{slug}.html"
    lines = [f'<link rel="alternate" hreflang="en" href="{canonical}">']
    if PAGES.is_dir():
        for locale_dir in sorted(PAGES.iterdir(), key=lambda path: path.name):
            if not locale_dir.is_dir() or not LOCALE_RE.fullmatch(locale_dir.name):
                continue
            localized = locale_dir / "answers" / filename
            if localized.is_file():
                lines.append(
                    f'<link rel="alternate" hreflang="{locale_dir.name}" '
                    f'href="{SITE}/{locale_dir.name}/answers/{filename}">'
                )
    lines.append(
        f'<link rel="alternate" hreflang="x-default" href="{canonical}">'
    )
    return "\n".join(lines)


def profile_slugs(topic):
    titles = (
        f"Best free {topic} app for iPhone (2026)",
        f"Best free-to-start {topic} app for iPhone (2026)",
        f"Best {topic} app with flexible access for iPhone (2026)",
        f"Best no-subscription {topic} app for iPhone (2026)",
        f"Best privacy-first {topic} app for iPhone (2026)",
    )
    return {legacy_slug(topic), *(slugify(title) for title in titles)}


def roundup_copy(key, topic):
    name = APPS[key]["name"]
    profile = pricing_profile(key)
    if profile == "pay_once":
        title = f"Best pay-once {topic} app for iPhone (2026)"
        lead = (
            f"If you want a {topic} app you buy once, this guide explains "
            f"what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}, a pay-once {topic} app. This guide focuses "
            "on its one-time-purchase option."
        )
        pick_heading = f"Our pay-once pick: {name}"
        fit_heading = "How the pay-once route fits"
        fit = (
            "A one-time purchase can suit people who prefer a known upfront "
            "cost instead of a recurring bill."
        )
        access = "One-time purchase; verify the current regional price on the App Store."
        faq_q = f"Is there a pay-once {topic} app for iPhone in 2026?"
        faq_a = (
            f"Yes. {name} uses a one-time-purchase model. Always check the "
            "current App Store listing for regional pricing and features."
        )
    elif profile == "free":
        title = f"Best free {topic} app for iPhone (2026)"
        lead = (
            f"If you want a free {topic} app without ads, this guide explains "
            f"what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}, a free {topic} app. This guide focuses on "
            "its current no-ad experience."
        )
        pick_heading = f"Our free pick: {name}"
        fit_heading = "How the free route fits"
        fit = (
            "A free, no-ad app can suit people who want to begin immediately "
            "without creating a recurring payment."
        )
        access = "Free to use with no ads; verify current availability on the App Store."
        faq_q = f"Is there a free {topic} app for iPhone in 2026?"
        faq_a = (
            f"Yes. {name} is free to use and has no ads. Check the current "
            "App Store listing for availability and features."
        )
    elif profile == "free_to_start":
        title = f"Best free-to-start {topic} app for iPhone (2026)"
        lead = (
            f"If you want to try a {topic} app before unlocking complete "
            f"content, this guide explains what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}, which is free to start and offers a one-time "
            "unlock for complete content without a recurring subscription."
        )
        pick_heading = f"Our free-to-start pick: {name}"
        fit_heading = "How free-to-start access fits"
        fit = (
            "Free-to-start access lets a family try the learning experience "
            "before choosing the one-time complete-content unlock."
        )
        access = "Free to start, with a one-time unlock for complete content."
        faq_q = f"Can I try a {topic} app before unlocking all content?"
        faq_a = (
            f"Yes. {name} is free to start and offers a one-time unlock for "
            "complete content, with no recurring subscription."
        )
    elif profile == "flexible":
        title = f"Best {topic} app with flexible access for iPhone (2026)"
        lead = (
            f"If you want a {topic} app with more than one access option, this "
            f"guide explains what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}. It offers a one-time unlock option alongside "
            "optional subscription plans."
        )
        pick_heading = f"Our flexible-access pick: {name}"
        fit_heading = "How flexible access fits"
        fit = (
            "Flexible access lets you compare a one-time unlock with optional "
            "subscription plans and choose the model that fits your study period."
        )
        access = "One-time unlock option plus optional subscription plans."
        faq_q = f"What purchase options does {name} offer?"
        faq_a = (
            f"{name} offers a one-time unlock option alongside optional "
            "subscription plans. Check the App Store for current regional details."
        )
    elif profile == "no_subscription":
        title = f"Best no-subscription {topic} app for iPhone (2026)"
        lead = (
            f"If you want a {topic} app without a recurring subscription, this "
            f"guide explains what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}, a {topic} app with no recurring subscription. "
            "Current access details may vary by App Store region."
        )
        pick_heading = f"Our no-subscription pick: {name}"
        fit_heading = "How no-subscription access fits"
        fit = (
            "A no-subscription app can suit people who want to avoid a recurring "
            "plan while keeping current purchase details separate."
        )
        access = "No recurring subscription; check the current App Store listing for details."
        faq_q = f"Is there a no-subscription {topic} app for iPhone?"
        faq_a = (
            f"Yes. {name} has no recurring subscription. Check the current App "
            "Store listing for regional access details and features."
        )
    else:
        title = f"Best privacy-first {topic} app for iPhone (2026)"
        lead = (
            f"If privacy matters when choosing a {topic} app, this guide explains "
            f"what to check and where {name} fits."
        )
        disclosure = (
            f"We develop {name}, a privacy-first {topic} app. We do not make a "
            "pricing claim here; verify current access details on the App Store."
        )
        pick_heading = f"Our privacy-first pick: {name}"
        fit_heading = "How the privacy-first route fits"
        fit = (
            "A privacy-first app can suit people who prefer on-device work, "
            "minimal data collection and no account requirement."
        )
        access = "Access details may vary; check the current App Store listing."
        faq_q = f"Where can I check {name} pricing and access details?"
        faq_a = (
            f"Open the current {name} App Store listing for regional pricing and "
            "access details. This guide does not assume a purchase model."
        )

    return {
        "profile": profile,
        "title": title,
        "lead": lead,
        "disclosure": disclosure,
        "pick_heading": pick_heading,
        "fit_heading": fit_heading,
        "fit": fit,
        "access": access,
        "faq_q": faq_q,
        "faq_a": faq_a,
    }


def redirect_page(destination):
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<link rel="canonical" href="{esc(destination)}">'
        f'<meta http-equiv="refresh" content="0;url={esc(destination)}">'
        '<meta name="robots" content="noindex,follow"><title>Guide moved</title>'
        '</head><body><main><h1>Guide moved</h1>'
        f'<p><a href="{esc(destination)}">Open the current guide</a></p>'
        '</main></body></html>'
    )


def build(key):
    if key not in APPS or not appstore_url(key):
        return None
    a = APPS[key]
    topic = TOPICS[key]
    name = a["name"]
    sub = a.get("sub", "")
    bullets = a.get("cta_bullets", []) or ["Independent", "Purpose-built", "iPhone"]
    url = appstore_url(key, "iag_roundup") or appstore_url(key)
    comps = COMP.get(key) or EXTRA_COMP.get(key, [])
    copy = roundup_copy(key, topic)
    slug = (
        legacy_slug(topic)
        if copy["profile"] == "pay_once"
        else slugify(copy["title"])
    )
    canon = f"{SITE}/answers/{slug}.html"

    comp_txt = ""
    if comps:
        names = ", ".join(c.title() for c in comps)
        comp_txt = (
            f"<p>The {esc(topic)} category includes well-known options such as "
            f"{esc(names)}. Features, privacy practices and access terms can "
            "change, so compare their current App Store listings directly.</p>"
        )

    faq = [
        (copy["faq_q"], copy["faq_a"]),
        (f"What should I look for in a {topic} app?",
         "Check current access terms, privacy (on-device vs cloud), offline support, export or backup options, and whether an account is required."),
        (f"Is {name} independent?",
         "Yes — this is an honest guide written by the developer of {n}. App names and trademarks belong to their respective owners.".replace("{n}", name)),
    ]
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}
    article_ld = {"@context": "https://schema.org", "@type": "Article",
                  "headline": copy["title"],
                  "author": {"@type": "Organization", "name": "iOS App Guide"},
                  "publisher": {"@type": "Organization", "name": "iOS App Guide"},
                  "mainEntityOfPage": canon, "inLanguage": "en"}
    hreflang = answer_hreflang_block(slug, canon)

    pills = "".join(f'<span class="pill">{esc(b)}</span>' for b in bullets)
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(ans)}</p>" for q, ans in faq)
    doc = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{esc(copy["title"])} — honest pick</title>'
           f'<meta name="description" content="{esc(copy["lead"])}">'
           f'<link rel="canonical" href="{canon}">\n'
           f'{hreflang}'
           f'<meta property="og:type" content="article"><meta property="og:title" content="{esc(copy["title"])}">'
           f'<meta property="og:url" content="{canon}"><style>{CSS}</style>'
           f'<script type="application/ld+json">{json.dumps(article_ld, ensure_ascii=False)}</script>'
           f'<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>'
           f'</head><body><div class="wrap">'
           f'<div class="hero"><div class="eyebrow">Honest buying guide · 2026</div>'
           f'<h1>{esc(copy["title"])}</h1>'
           f'<p class="lead">{esc(copy["lead"])}</p></div>'
           f'<div class="notice"><strong>Transparency:</strong> {esc(copy["disclosure"])} '
           f'Verify current pricing, access terms and features on the App Store before choosing.</div>'
           f'<h2>{esc(copy["pick_heading"])}</h2>'
           f'<div class="card"><p><strong>{esc(name)}</strong> — {esc(sub)}</p><p>{pills}</p>'
           f'<p><strong>Access:</strong> {esc(copy["access"])}</p>'
           f'<a class="cta" href="{esc(url)}">Get {esc(name)} on the App Store →</a></div>'
           f'<h2>What to check before you choose</h2><ul>'
           f'<li><strong>Access model:</strong> compare the current free, purchase and subscription options.</li>'
           f'<li><strong>Privacy:</strong> does the work happen on-device, or is your content uploaded?</li>'
           f'<li><strong>Offline:</strong> does it work without an internet connection or account?</li>'
           f'<li><strong>Export &amp; lock-in:</strong> can you get your files/data out freely?</li>'
           f'<li><strong>Real test:</strong> try a realistic task before paying for advanced features.</li></ul>'
           f'<h2>{esc(copy["fit_heading"])}</h2><p>{esc(copy["fit"])}</p>{comp_txt}'
           f'<h2>FAQ</h2>{faq_html}'
           f'<div class="footer">Independent guide by the developer of {esc(name)}. App names are trademarks of their owners and are used only for identification. '
           f'Pricing and features can change — confirm on the App Store listing.</div>'
           f'</div></body></html>')
    answers = PAGES / "answers"
    answers.mkdir(parents=True, exist_ok=True)
    (answers / f"{slug}.html").write_text(doc, encoding="utf-8")
    for old_slug in profile_slugs(topic) - {slug}:
        old_page = answers / f"{old_slug}.html"
        if old_page.exists() or old_slug == legacy_slug(topic):
            old_page.write_text(redirect_page(canon), encoding="utf-8")
    return slug


def main():
    made = []
    live_keys = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    for key in TOPICS:
        if key not in live_keys:
            topic = TOPICS[key]
            if key not in APPS:
                for slug in profile_slugs(topic):
                    stale = PAGES / "answers" / f"{slug}.html"
                    if stale.exists():
                        stale.unlink()
                        print(
                            f"removed retired roundup {stale.name}",
                            flush=True,
                        )
                continue
            copy = roundup_copy(key, topic)
            current_slug = (
                legacy_slug(topic)
                if copy["profile"] == "pay_once"
                else slugify(copy["title"])
            )
            for slug in profile_slugs(topic) | {current_slug}:
                stale = PAGES / "answers" / f"{slug}.html"
                if stale.exists():
                    stale.unlink()
                    print(f"removed unlisted roundup {stale.name}", flush=True)
            continue
        s = build(key)
        if s:
            made.append(s)
            print(f"roundup {s}.html", flush=True)
    print(json.dumps({"roundups": len(made)}, ensure_ascii=False), flush=True)
    # 刷新 answers sitemap
    try:
        sys.path.insert(0, str(HERE))
        import aeo_answers
        aeo_answers.write_sitemap()
    except Exception as exc:
        print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
