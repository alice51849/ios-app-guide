#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persona-based app discovery pages — "Best iPhone apps for [profession]".
Targets profession/lifestyle search intent and groups our apps by who benefits most.
Schema: ItemList + FAQPage. Honest developer disclosure.
"""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).parent
PAGES = HERE / "pages"
sys.path.insert(0, str(HERE / ".." / "social"))
from videogen.registry import APPS, APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

GEO_SITE = os.getenv("GEO_SITE", PUBLIC_SITE)
DISCLAIMER = "All apps on this page are published by the same independent developer. App names are trademarks of their respective owners."

PERSONAS = [
    {
        "slug": "best-iphone-apps-for-frequent-travellers-2026",
        "title": "Best iPhone Apps for Frequent Travellers in 2026 (Pay Once, No Subscription)",
        "desc": "Honest app picks for frequent travellers: passport photos, travel budgets, offline scanning, WiFi diagnostics and noise for sleep — all buy-once.",
        "persona": "frequent travellers",
        "apps": ["snapport", "gmoney", "gmoneylite", "tripbee", "scanto", "wifiaid", "sereno"],
        "intro": "Frequent travellers need tools that work offline, respect privacy and don't add recurring costs to an already expensive lifestyle. These apps cover the most common travel pain points — none require subscriptions.",
        "faqs": [
            ("What is the best passport photo app for travellers?", "Snapport guides you through official biometric requirements for different countries and lets you download or print a compliant photo without a pharmacy visit."),
            ("How do I track spending in multiple currencies while travelling?", "G+Money tracks expenses in your home currency with automatic conversion. G+Money Lite is the free version with the core features."),
            ("Is there a good offline document scanner for travel?", "ScanTo Pro scans to PDF fully offline — no account, no cloud upload. Useful for scanning boarding passes, insurance documents and receipts securely."),
            ("How do I diagnose slow hotel WiFi?", "WiFi Aid runs DNS, TCP and TLS checks independently to identify whether slow WiFi is a router issue, ISP problem or remote server — without technical knowledge."),
        ],
    },
    {
        "slug": "best-iphone-apps-for-remote-workers-2026",
        "title": "Best iPhone Apps for Remote Workers and Freelancers in 2026",
        "desc": "Honest picks for remote workers and freelancers: voice notes, document scanning, AI context briefing, resume building and focus — all pay-once.",
        "persona": "remote workers and freelancers",
        "apps": ["sononote", "scanto", "aibriefpack", "cvdesk", "lockhour", "hourstag", "hourstaglite"],
        "intro": "Remote workers deal with scattered information, client documents, endless meetings and the constant temptation of home distractions. These apps target the specific workflows where remote workers lose the most time.",
        "faqs": [
            ("What is the best offline voice notes app for remote workers?", "Sono Note records and transcribes voice notes on-device. No cloud upload means client conversations stay private."),
            ("How do I organise context before an AI meeting summary?", "AI Brief lets you collect screenshots, documents and notes into a structured brief to paste into ChatGPT, Claude or any AI tool for a better summary."),
            ("Is there a free app that shows the real hourly cost of purchases?", "HoursTag Lite is free and converts any price into hours of your own work — useful for freelancers evaluating tool costs against their billable rate."),
            ("How do I block distractions while working from home?", "LockHour Pro lets you set timed focus sessions that block social apps so you can do deep work without willpower alone."),
        ],
    },
    {
        "slug": "best-iphone-apps-for-parents-with-young-children-2026",
        "title": "Best iPhone Apps for Parents with Young Children in 2026",
        "desc": "Honest picks for parents: kids learning apps for Zhuyin, phonics and maths, plus daily routine and chore trackers — all pay-once, no subscriptions.",
        "persona": "parents with young children",
        "apps": ["lumibopomofo", "lumiletters", "lumimath", "lumimission", "mochidonestamp", "dailymate", "sereno"],
        "intro": "Parents juggle their children's learning, their own household and their own wellbeing. These apps cover kids education (Zhuyin, phonics, maths), daily routines and household memory — without ongoing subscription costs.",
        "faqs": [
            ("What is the best Zhuyin learning app for children?", "Lumi Bopomofo teaches all 37 Zhuyin symbols through stroke-by-stroke tracing with audio, designed for Taiwanese children aged 4–8."),
            ("Is there a phonics app for young children without a subscription?", "Lumi Letters Pro teaches 44 English phonics sounds through play-based forest adventures. One-time purchase, no subscription."),
            ("How do I help children build morning and bedtime routines?", "Lumi Mission Planet gives children a visual mission board for daily routines — breakfast, brush teeth, pack bag — with fun stamps for completing tasks."),
            ("How do I track recurring household chores with my partner?", "Mochi DoneStamp records when each task was last done. Tap once when complete, and the app shows how long since each chore was done."),
        ],
    },
    {
        "slug": "best-iphone-apps-for-privacy-conscious-users-2026",
        "title": "Best iPhone Apps for Privacy-Conscious Users in 2026",
        "desc": "Honest picks for privacy-focused iPhone users: private photo vaults, secure offline scanning, file redaction and on-device health tracking.",
        "persona": "privacy-conscious iPhone users",
        "apps": ["zafe", "maskmyfile", "scanto", "cyca", "sononote", "picclear"],
        "intro": "Privacy-conscious users want apps that keep data on-device, require no account sign-up and let them control what is shared and what is deleted. These apps are designed around offline-first, no-cloud principles.",
        "faqs": [
            ("What is the safest way to hide photos on iPhone without a subscription?", "Zafe: Private Photo Vault stores photos in an encrypted, Face ID-protected vault separate from your camera roll. One-time purchase, no account required."),
            ("How do I share a document without leaking personal information?", "Mask My File scans for phone numbers, emails, IDs and addresses in a document and masks them before export. All processing is on-device."),
            ("Is there a period tracker that doesn't send data to a server?", "Cyca: Period & Cycle Tracker stores all cycle data on your device only. No cloud sync, no account, no data shared."),
            ("What is the best offline voice notes app that doesn't upload to the cloud?", "Sono Note records and transcribes on-device. Nothing leaves your iPhone unless you actively share it."),
        ],
    },
    {
        "slug": "best-iphone-apps-for-students-studying-english-2026",
        "title": "Best iPhone Apps for Students Studying English and TOEIC in 2026",
        "desc": "Honest picks for English learners and TOEIC test-takers: score-targeted practice, voice notes for study and resume building for job applications.",
        "persona": "students studying English and TOEIC",
        "apps": ["aim990", "aim990plus", "sononote", "cvdesk"],
        "intro": "English learners preparing for TOEIC or job applications need focused practice tools, not broad language-learning platforms with expensive subscriptions. These apps target the specific study and career preparation tasks that matter most.",
        "faqs": [
            ("What is the best TOEIC practice app for iPhone?", "Aim990 provides daily Listening & Reading plans, weak-spot drills and real-test simulations aimed at reaching a 990 score. Aim990 Plus adds advanced tracks for students targeting above 900."),
            ("How do I practise English listening on iPhone without a subscription?", "Aim990 includes structured listening practice as a one-time purchase. No ongoing fee is required to access the study content."),
            ("Is there a resume builder for iPhone that helps pass ATS systems?", "CV Desk gives your resume an instant ATS score, highlights what filters reject and exports a clean PDF — one-time purchase with no subscription."),
            ("How can I record and review English pronunciation practice on iPhone?", "Sono Note records voice memos with on-device transcription so you can listen back and review pronunciation at any time, without uploading audio to any server."),
        ],
    },
    {
        "slug": "best-iphone-apps-for-mindful-spending-2026",
        "title": "Best iPhone Apps for Mindful Spending and Financial Awareness in 2026",
        "desc": "Honest picks for spending awareness: hourly wage cost conversion, daily habit tracking, focus apps and travel budget tools — all pay-once.",
        "persona": "people focused on mindful spending",
        "apps": ["hourstag", "hourstaglite", "lockhour", "dailymate", "gmoney", "gmoneylite", "mochidonestamp"],
        "intro": "Mindful spending is not about cutting everything — it's about knowing the real cost of each purchase before you commit. These apps address impulse buying, habit tracking and budget awareness from different angles.",
        "faqs": [
            ("What app converts prices to hours of work before I buy?", "HoursTag converts any price into hours of your own time based on your hourly wage. HoursTag Lite is the free version with the core conversion feature."),
            ("How do I track daily habits and spending together?", "DailyMate helps you log daily habits and recurring tasks, while HoursTag shows the time cost of each purchase. Used together they give you a complete view of how you spend your time and money."),
            ("Is there a free travel budget app?", "G+Money Lite tracks trip expenses with live currency conversion for free. G+Money adds offline rates and more detailed reporting."),
        ],
    },
]


def app_card(key, localized=None):
    if localized is not None:
        from html import escape

        row = localized[key]
        return f"""<div class="app-card">
  <strong>{escape(row["app_name"])}</strong>
  <p class="sub">{escape(row["decision_context"])}</p>
  <p class="badge">{escape(row["purchase_label"])}</p>
  <a href="{escape(row["app_store_url"], quote=True)}" class="cta" rel="noopener">{escape(row["app_store_cta_label"])}</a>
</div>"""
    a = APPS.get(key)
    if not a:
        return ""
    aid = APPSTORE.get(key, "")
    name = a.get("name", key)
    sub = (a.get("sub") or "")[:100]
    url = f"https://apps.apple.com/app/id{aid}?ct=iag_persona" if aid else "#"
    price = a.get("price_usd", 0)
    badge = "Free" if not price else f"${price:.2f} · pay once"
    return f"""<div class="app-card">
  <strong>{name}</strong>
  <p class="sub">{sub}</p>
  <p class="badge">{badge}</p>
  <a href="{url}" class="cta" rel="noopener">View on App Store →</a>
</div>"""


def render(p, *, locale=None, localized=None):
    from html import escape

    if locale is not None:
        import western_romance_surface_copy

        meta = western_romance_surface_copy.for_locale(locale)
        if localized is None or set(p["apps"]) - set(localized):
            raise ValueError("Localized personas need a record for every app")
    else:
        meta = None
    apps_with_store = [k for k in p["apps"] if APPS.get(k) and APPSTORE.get(k)]
    if not apps_with_store:
        return None

    cards = "\n".join(app_card(k, localized) for k in apps_with_store)
    faqs_html = ""
    faqs_ld = []
    for q, a in p["faqs"]:
        q_html, a_html = (escape(q), escape(a)) if locale else (q, a)
        faqs_html += f'<details class="faq"><summary><strong>{q_html}</strong></summary><p>{a_html}</p></details>\n'
        faqs_ld.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})

    items = [{"@type": "ListItem", "position": i + 1, "name": APPS[k].get("name", k),
              "url": f"https://apps.apple.com/app/id{APPSTORE[k]}?ct=iag_persona"}
             for i, k in enumerate(apps_with_store)]
    if locale:
        items = [
            {"@type": "ListItem", "position": i + 1, "name": localized[k]["app_name"],
             "url": localized[k]["app_store_url"]}
            for i, k in enumerate(apps_with_store)
        ]

    ld = json.dumps([
        {"@context": "https://schema.org", "@type": "ItemList",
         "name": p["title"], "description": p["desc"], "itemListElement": items},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs_ld}
    ], ensure_ascii=False)
    if locale:
        ld = ld.replace("<", "\\u003c").replace(">", "\\u003e")
        p = {**p, **{field: escape(p[field]) for field in ("title", "desc", "intro")}}
    language = locale or "en"
    route_prefix = f"{locale}/" if locale else ""
    back_url = f"{GEO_SITE}/{locale or 'en-US'}/"
    back_label = escape(meta["back"]) if meta else "App Guide"
    faq_title = escape(meta["faq"]) if meta else "Frequently asked questions"
    disclosure = escape(meta["disclosure"]) if meta else DISCLAIMER

    html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<title>{p['title']}</title>
<meta name="description" content="{p['desc']}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{GEO_SITE}/{route_prefix}persona/{p['slug']}.html">
<style>
body{{font-family:system-ui,sans-serif;max-width:700px;margin:2rem auto;padding:0 1rem;color:#222}}
h1{{font-size:1.45rem;line-height:1.3}}
.intro{{background:#f5f5f5;border-radius:8px;padding:1rem;margin:1.5rem 0;font-size:.95rem}}
.app-card{{border:1px solid #e0e0e0;border-radius:8px;padding:1rem;margin:1rem 0}}
.app-card strong{{font-size:1.05rem}}.sub{{color:#555;font-size:.9rem;margin:.4rem 0}}
.badge{{font-size:.85rem;color:#007aff;margin:.3rem 0}}
.cta{{display:inline-block;margin-top:.5rem;color:#007aff;text-decoration:none;font-weight:600}}
.faq{{border:1px solid #e8e8e8;border-radius:6px;padding:.75rem 1rem;margin:.75rem 0}}
.faq summary{{cursor:pointer;font-size:.95rem}}
.faq p{{margin:.5rem 0 0;color:#444;font-size:.9rem}}
.disclaimer{{font-size:.8rem;color:#888;margin-top:2rem;border-top:1px solid #eee;padding-top:1rem}}
</style>
<script type="application/ld+json">{ld}</script>
</head>
<body>
<p><a href="{back_url}">← {back_label}</a></p>
<h1>{p['title']}</h1>
<div class="intro">{p['intro']}</div>
{cards}
<h2>{faq_title}</h2>
{faqs_html}
<p class="disclaimer">{disclosure}</p>
</body>
</html>"""
    return html


def main():
    out = PAGES / "persona"
    out.mkdir(exist_ok=True)
    created = []
    for p in PERSONAS:
        html = render(p)
        if not html:
            continue
        path = out / f"{p['slug']}.html"
        path.write_text(html, encoding="utf-8")
        created.append(p["slug"])

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(f'<url><loc>{GEO_SITE}/persona/{s}.html</loc></url>' for s in created)
    sitemap += "\n</urlset>\n"
    (PAGES / "sitemap_persona.xml").write_text(sitemap, encoding="utf-8")
    print(json.dumps({"persona_pages": len(created), "slugs": created}))


if __name__ == "__main__":
    main()
