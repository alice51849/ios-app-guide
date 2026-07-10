#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AEO 購買意圖落地頁生成器 — 把 aeo_sov.py 的「攻擊清單」變成會被 Google/AI 引用的頁。

策略(打購買當下、非散播):
  aeo_sov.py 量到「有人問 AI 要用哪個 app」時,AI 都推哪些競品、你在哪些問句缺席。
  這支就針對那些競品 + 缺口問句,自動產「pay-once / no-subscription 替代方案」比較頁:
    • <app>-vs-<competitor>.html  → 鎖定「[競品] alternative」這種最高購買意圖的搜尋/AI 問句
    • <app>-no-subscription.html  → 鎖定「免訂閱的 X app」hub 頁
  每頁含 SoftwareApplication + FAQPage JSON-LD(LLM/Google 最愛的結構化來源)+ 誠實比較表
  (只主張「你的 app」可驗證屬性:一次付費/離線/無廣告/無浮水印;競品欄用「typical apps」中性敘述)。

  誠信原則:不對具名競品做不實宣稱;競品僅作為使用者搜尋的參照點(nominative use)。

用法:
  python geo/aeo_pages.py                 # 依 reports/aeo_sov.json 產頁(不部署)
  python geo/aeo_pages.py --publish       # 並 git push + IndexNow 推送
  python geo/aeo_pages.py scanto cvdesk   # 只產指定 app
  python geo/aeo_pages.py --top 4         # 每 app 取前 N 個競品(預設 4)
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

PAGES = os.path.join(HERE, "pages")
ALT = os.path.join(PAGES, "alternatives")
REPORTS = os.path.join(HERE, "reports")
SOV = os.path.join(REPORTS, "aeo_sov.json")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")

# Aim990 同時提供一次解鎖與可選訂閱；所有外宣必須清楚呈現兩種選項。
FLEXIBLE_PRICING = {"aim990"}

# 類別 → 給人看的名詞 + schema 類別
CAT_NOUN = {
    "photo-utility": ("photo app", "PhotoApplication"),
    "productivity": ("productivity app", "BusinessApplication"),
    "finance": ("finance app", "FinanceApplication"),
    "health": ("health app", "HealthApplication"),
    "education": ("English test-prep app", "EducationalApplication"),
    "kids": ("kids learning app", "EducationalApplication"),
    "lifestyle": ("astrology app", "LifestyleApplication"),
    "travel": ("travel planner", "TravelApplication"),
}

# 常見競品正規化名 → 正式顯示名(其餘自動 Title Case)
BRAND = {
    "camscanner pdf scanner app": "CamScanner", "adobe scan pdf scanner ocr": "Adobe Scan",
    "scanbot pdf document scanner": "Scanbot", "genius scan": "Genius Scan",
    "microsoft lens": "Microsoft Lens", "tiny scanner": "Tiny Scanner",
    "visualcv resume builder": "VisualCV", "zety resume builder": "Zety",
    "resume builder cv maker": "Resume Builder", "canva": "Canva", "indeed": "Indeed",
    "snapseed": "Snapseed", "fotor photo editor": "Fotor", "remini ai photo enhancer": "Remini",
    "remini": "Remini", "lightroom": "Lightroom", "vsco": "VSCO", "picsart": "PicsArt",
    "flo period ovulation tracker": "Flo", "ovia fertility cycle tracker": "Ovia",
    "my calendar period tracker": "My Calendar", "clue period cycle tracker": "Clue",
    "flo": "Flo", "clue": "Clue", "natural cycles": "Natural Cycles",
    # 從 20-app 全掃補進的常見競品
    "microsoft office lens": "Microsoft Office Lens", "microsoft onenote": "Microsoft OneNote",
    "otter transcribe voice notes": "Otter", "google keep": "Google Keep",
    "passport photo maker": "Passport Photo Maker", "passport photo booth": "Passport Photo Booth",
    "id photo passport photo": "ID Photo", "resume star pro cv maker": "Resume Star Pro",
    "gemini photos gallery cleaner": "Gemini Photos", "duplicate photos fixer": "Duplicate Photos Fixer",
    "smart cleaner clean storage": "Smart Cleaner", "ynab you need a budget": "YNAB",
    "currency converter plus": "Currency Converter Plus", "spendee budget expense tracker": "Spendee",
    "everydollar budgeting app": "EveryDollar", "forest stay focused": "Forest",
    "focus will": "Focus@Will", "stay focused app blocker": "Stay Focused",
    "adobe lightroom": "Adobe Lightroom", "endless alphabet": "Endless Alphabet",
    "abcmouse com": "ABCmouse", "starfall abcs": "Starfall", "reading eggs": "Reading Eggs",
    "endless numbers": "Endless Numbers", "todo math": "Todo Math",
    "math kids add subtract count and learn": "Math Kids", "prodigy math game": "Prodigy",
    "ourhome": "OurHome", "choremonster": "ChoreMonster", "cozi family organizer": "Cozi",
    "the weather channel": "The Weather Channel", "weather wiz kids": "Weather Wiz Kids",
    "kid weather": "Kid Weather", "hellochinese": "HelloChinese",
    "hellochinese learn chinese": "HelloChinese", "chineseskill": "ChineseSkill",
    "chineseskill learn chinese": "ChineseSkill", "fun chinese by studycat": "Fun Chinese by Studycat",
}

ATTRS = [  # (顯示, cta_bullets 命中關鍵詞)
    ("Pay once", ("pay once", "one-time", "everything unlocked")),
    ("No subscription", ("no subscription",)),
    ("Works offline / on-device", ("on-device", "offline", "on device")),
    ("No ads", ("no ads",)),
    ("No watermark", ("no watermark",)),
    ("Private (no account)", ("private", "no account", "no tracking")),
]


def e(s):
    return html.escape(str(s or ""))


def disp(norm):
    if norm in BRAND:
        return BRAND[norm]
    return " ".join(w.capitalize() for w in norm.split())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70] or "x"


def app_attrs(key):
    b = [x.lower() for x in APPS[key].get("cta_bullets", [])]
    out = {}
    for label, keys in ATTRS:
        out[label] = any(any(k in bb for bb in b) for k in keys)
    return out


def pricing_profile(key):
    if key in FLEXIBLE_PRICING:
        return "flexible"
    app = APPS[key]
    facts = " · ".join([app.get("tag", "")] + app.get("cta_bullets", [])).lower()
    if "free to start" in facts:
        return "free_to_start"
    if re.search(r"\bfree\b", facts) and "pay once" not in facts:
        return "free"
    if "pay once" in facts or "one-time" in facts or "everything unlocked" in facts:
        return "pay_once"
    if "no subscription" in facts:
        return "no_subscription"
    return "neutral"


def positioning(key, noun):
    app = APPS[key]
    name = app["name"]
    profile = pricing_profile(key)
    if profile == "pay_once":
        return {
            "suffix": "pay once, no subscription",
            "description": f"{name} is a pay-once {noun} with no recurring subscription.",
            "intro": f"{name} is a one-time-purchase {noun} for iPhone.",
            "heading": f"Why people choose a pay-once {noun}",
            "cta": f"Try {name} — one-time purchase on the App Store",
            "hub_title": f"Best no-subscription {noun} for iPhone — {name} (pay once)",
            "hub_heading": f"The pay-once {noun} for iPhone: {name}",
            "hub_section": "What you get (no subscription)",
            "slug": f"{key}-no-subscription",
        }
    if profile == "no_subscription":
        return {
            "suffix": "no subscription",
            "description": f"{name} is a no-subscription {noun} for iPhone.",
            "intro": f"{name} is a {noun} with no recurring subscription.",
            "heading": f"Why people choose a no-subscription {noun}",
            "cta": f"View {name} on the App Store",
            "hub_title": f"No-subscription {noun} for iPhone — {name}",
            "hub_heading": f"A no-subscription {noun} for iPhone: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-no-subscription",
        }
    if profile == "free_to_start":
        return {
            "suffix": "free to start, no subscription",
            "description": f"{name} is free to start and has no recurring subscription.",
            "intro": f"{name} is a {noun} that is free to start, with no recurring subscription.",
            "heading": f"Why people choose a free-to-start {noun}",
            "cta": f"Try {name} free on the App Store",
            "hub_title": f"Free-to-start {noun} for iPhone — {name}",
            "hub_heading": f"A free-to-start {noun} for iPhone: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-free-to-start",
        }
    if profile == "free":
        return {
            "suffix": "free, no ads",
            "description": f"{name} is a free {noun} with no ads.",
            "intro": f"{name} is a free {noun} for iPhone with no ads.",
            "heading": f"Why people choose this free {noun}",
            "cta": f"Get {name} free on the App Store",
            "hub_title": f"Free, ad-free {noun} for iPhone — {name}",
            "hub_heading": f"A free, ad-free {noun} for iPhone: {name}",
            "hub_section": "What the app includes",
            "slug": f"{key}-free-no-ads",
        }
    return {
        "suffix": "private, on-device option",
        "description": f"{name} is a privacy-focused {noun} for iPhone.",
        "intro": f"{name} is a privacy-focused {noun} that works on your iPhone.",
        "heading": f"What to compare in a private {noun}",
        "cta": f"View {name} on the App Store",
        "hub_title": f"Private {noun} for iPhone — {name}",
        "hub_heading": f"A privacy-focused {noun} for iPhone: {name}",
        "hub_section": "What the app includes",
        "slug": f"{key}-private-alternative",
    }


def alternative_hub_slug(key):
    if pricing_profile(key) == "flexible":
        return f"{key}-flexible-unlock"
    noun, _ = cat_noun(key)
    return positioning(key, noun)["slug"]


def cat_noun(key):
    return CAT_NOUN.get(APPS[key].get("category", "productivity"), ("app", "MobileApplication"))


def landing_url(key):
    """Use the live App Store URL when known; otherwise link to the generated web page."""
    return appstore_url(key, "iag_alt") or f"{SITE}/alternatives/{key}-no-subscription.html"


def page_shell(title, desc, canonical, schemas, body):
    ld = "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title[:65])}</title>
<meta name="description" content="{e(desc[:155])}">
<link rel="canonical" href="{canonical}">
{ld}
</head>
<body>
<main>
{body}
<hr>
<p><small>Independent comparison. App names are trademarks of their owners and are used
for identification only.</small></p>
</main>
</body>
</html>
"""


def comparison_table(key, comp_name):
    a = APPS[key]
    attrs = app_attrs(key)
    profile = pricing_profile(key)
    rows = []
    for label, _ in ATTRS:
        if profile == "flexible" and label == "No subscription":
            continue
        shown_label = label
        if "Pay once" in label:
            shown_label = "Pricing"
            yours = {
                "flexible": "✅ One-time unlock option; optional subscriptions",
                "pay_once": "✅ One-time purchase; no subscription",
                "no_subscription": "✅ No subscription",
                "free_to_start": "✅ Free to start; no subscription",
                "free": "✅ Free",
                "neutral": "Check current App Store listing",
            }[profile]
        else:
            yours = "✅ Yes" if attrs[label] else "—"
        # 競品欄:中性、可辯護(對「typical apps」而非具名不實宣稱)
        typical = "Often subscription" if "Pay once" in label else "Varies"
        rows.append(f"    <tr><td>{e(shown_label)}</td><td><strong>{yours}</strong></td>"
                    f"<td>{e(typical)}</td></tr>")
    return (f'  <table>\n    <thead><tr><th>Feature</th><th>{e(a["name"])}</th>'
            f'<th>Typical {e(comp_name)}-style apps</th></tr></thead>\n    <tbody>\n'
            + "\n".join(rows) + "\n    </tbody>\n  </table>")


def faq_for(key, comp_name, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    profile = pricing_profile(key)
    if profile == "flexible":
        qa = [
            ("Can I unlock Aim990 with one payment?",
             "Yes. Aim990 offers a one-time unlock option alongside optional subscription plans. "
             f"Check the current choices on the App Store: {url}"),
            ("Does Aim990 only use a subscription?",
             "No. A one-time unlock option is available, and users may instead choose an optional "
             "subscription plan. Pricing can vary by storefront."),
        ]
    elif profile == "pay_once":
        qa = [
            (f"What is a good pay-once alternative to {comp_name} on iPhone?",
             f"{a['name']} is a one-time-purchase {noun} for iPhone — {a.get('sub','').replace(chr(10),' ')}. "
             f"You unlock everything with a single payment, with no recurring subscription."),
            (f"Is there a {noun} with no subscription?",
             f"Yes. {a['name']} is a pay-once {noun}: buy it once and keep it. "
             f"Get it on the App Store: {url}"),
        ]
    elif profile == "no_subscription":
        qa = [
            (f"Does {a['name']} require a subscription?",
             f"No. {a['name']} has no recurring subscription. Check the current App Store "
             f"listing for pricing and availability: {url}"),
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} is a no-subscription {noun} for iPhone with a focus on "
             f"{a.get('sub', '').replace(chr(10), ' ')}."),
        ]
    elif profile == "free_to_start":
        qa = [
            (f"Can I try {a['name']} for free?",
             f"Yes. {a['name']} is free to start and has no recurring subscription. "
             f"See the current App Store listing: {url}"),
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} is a free-to-start {noun} for iPhone with no ads."),
        ]
    elif profile == "free":
        qa = [
            (f"Is {a['name']} free?",
             f"Yes. {a['name']} is a free {noun} with no ads. Get it on the App Store: {url}"),
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} offers a simple, ad-free {noun} experience on iPhone."),
        ]
    else:
        qa = [
            (f"What makes {a['name']} an alternative to {comp_name}?",
             f"{a['name']} is a privacy-focused {noun} for iPhone — "
             f"{a.get('sub', '').replace(chr(10), ' ')}."),
            (f"How much does {a['name']} cost?",
             f"Pricing can vary by storefront. Check the current App Store listing: {url}"),
        ]
    if app_attrs(key).get("Works offline / on-device"):
        qa.append((f"Does {a['name']} work offline / on device?",
                   f"Yes, {a['name']} runs on your iPhone and processes your data on-device for privacy."))
    for q in (gap_queries or [])[:3]:
        q_lower = q.lower()
        pay_once_query = any(
            phrase in q_lower
            for phrase in ("pay once", "one-time purchase", "buy once")
        )
        no_subscription_query = any(
            phrase in q_lower
            for phrase in ("no subscription", "subscription-free")
        )
        if pay_once_query and profile != "pay_once":
            continue
        if no_subscription_query and profile not in {
            "pay_once",
            "no_subscription",
            "free_to_start",
        }:
            continue
        if profile == "flexible":
            answer = (
                "Aim990 is an independent study aid with daily L&R plans, weak-spot drills and "
                f"progress tracking. It offers a one-time unlock option and optional subscriptions. "
                f"It is not affiliated with or endorsed by ETS and does not guarantee a score. Learn more: {url}"
            )
        elif profile == "pay_once":
            answer = f"{a['name']} is a strong pay-once option. Learn more on the App Store: {url}"
        else:
            answer = f"{a['name']} is a practical {noun} option. Check current details on the App Store: {url}"
        qa.append((q[0].upper() + q[1:] + ("" if q.endswith("?") else "?"), answer))
    # 去重
    seen, out = set(), []
    for q, ans in qa:
        if q.lower() in seen:
            continue
        seen.add(q.lower()); out.append((q, ans))
    return out


def app_schema(key, desc):
    a = APPS[key]
    _, scat = cat_noun(key)
    url = landing_url(key)
    return {"@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": a["name"], "operatingSystem": "iOS", "applicationCategory": scat,
            "url": url, "installUrl": url, "description": desc,
            "featureList": [l for l, ok in app_attrs(key).items() if ok] or a.get("keywords", [])[:5]}


def faq_schema(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}


def alt_page(key, comp_norm, gap_queries):
    a = APPS[key]
    comp = disp(comp_norm)
    noun, _ = cat_noun(key)
    url = landing_url(key)
    flexible = pricing_profile(key) == "flexible"
    position = None if flexible else positioning(key, noun)
    if flexible:
        title = f"{comp} alternative for iPhone — {a['name']} (one-time unlock option)"
        desc = (f"Looking for a {comp} alternative on iPhone? Aim990 combines daily L&R plans, "
                "weak-spot drills and progress tracking, with a one-time unlock option and optional subscriptions.")
    else:
        title = f"{comp} alternative for iPhone — {a['name']} ({position['suffix']})"
        desc = f"Looking for a {comp} alternative on iPhone? {position['description']}"
    faq = faq_for(key, comp, gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    if flexible:
        body = f"""  <h1>{e(comp)} alternative for iPhone: {e(a['name'])}</h1>
  <p><strong>{e(a['name'])}</strong> is an independent TOEIC study aid with daily L&amp;R plans,
  weak-spot drills and progress tracking. It offers a <strong>one-time unlock option</strong>
  alongside optional subscription plans, so users can choose the current App Store option that fits them.</p>
  <p>Aim990 is not affiliated with or endorsed by ETS. TOEIC is a trademark of ETS, and no score is guaranteed.</p>
  <p><a href="{e(url)}"><strong>View {e(a['name'])} on the App Store →</strong></a></p>

  <h2>What to compare with {e(comp)}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(a['name'])} vs typical {e(comp)}-style apps</h2>
{comparison_table(key, comp)}

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Explore {e(a['name'])} and its current unlock options →</strong></a></p>"""
    else:
        body = f"""  <h1>{e(comp)} alternative for iPhone: {e(a['name'])}</h1>
  <p><strong>{e(position['intro'])}</strong> {e((a.get('sub') or '').replace(chr(10),' '))}</p>
  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>

  <h2>{e(position['heading'])}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(a['name'])} vs typical {e(comp)}-style apps</h2>
{comparison_table(key, comp)}

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>"""
    slug = f"{key}-vs-{slugify(comp)}"
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def hub_page(key, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    flexible = pricing_profile(key) == "flexible"
    position = None if flexible else positioning(key, noun)
    if flexible:
        title = "Aim990 pricing and study options for iPhone — one-time unlock available"
        desc = ("Aim990 offers daily L&R plans, weak-spot drills and progress tracking, with "
                "a one-time unlock option and optional subscription plans.")
    else:
        title = position["hub_title"]
        desc = position["description"]
    faq = faq_for(key, noun.split()[0], gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    if flexible:
        body = f"""  <h1>Aim990 unlock and study options for iPhone</h1>
  <p><strong>Aim990</strong> combines daily L&amp;R plans, weak-spot drills and progress tracking.
  It offers a <strong>one-time unlock option</strong> alongside optional subscription plans.</p>
  <p>Aim990 is an independent study aid, is not affiliated with or endorsed by ETS, and does not guarantee a score.
  TOEIC is a trademark of ETS.</p>
  <p><a href="{e(url)}"><strong>View current Aim990 options on the App Store →</strong></a></p>

  <h2>What Aim990 includes</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Explore Aim990 on the App Store →</strong></a></p>"""
    else:
        body = f"""  <h1>{e(position['hub_heading'])}</h1>
  <p><strong>{e(position['intro'])}</strong> {e((a.get('sub') or '').replace(chr(10),' '))}</p>
  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>

  <h2>{e(position['hub_section'])}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>{e(position['cta'])} →</strong></a></p>"""
    slug = alternative_hub_slug(key)
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def build_index(files):
    items = []
    for f in sorted(files):
        m = re.search(r"<h1>([^<]+)</h1>", open(os.path.join(ALT, f), encoding="utf-8").read())
        items.append(f'    <li><a href="{f}">{e(m.group(1) if m else f)}</a></li>')
    idx = (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f'<title>iPhone app alternatives — privacy and flexible pricing</title>\n'
           f'<meta name="description" content="Independent iPhone app alternatives with privacy-first, free, pay-once and flexible unlock options.">\n'
           f'<link rel="canonical" href="{SITE}/alternatives/index.html"></head><body><main>\n'
           f'  <h1>Independent iPhone app alternatives</h1>\n  <ul>\n'
           + "\n".join(items) + "\n  </ul>\n</main></body></html>\n")
    open(os.path.join(ALT, "index.html"), "w", encoding="utf-8").write(idx)


def write_sitemap(files):
    urls = [f"  <url><loc>{SITE}/alternatives/index.html</loc></url>"]
    urls += [f"  <url><loc>{SITE}/alternatives/{f}</loc></url>" for f in sorted(files)]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_alternatives.xml"), "w", encoding="utf-8").write(xml)


def prune_stale_pages(managed_keys, expected_files):
    """Remove generated alternatives that are no longer eligible or accurate."""
    removed = []
    for filename in os.listdir(ALT):
        if not filename.endswith(".html") or filename == "index.html":
            continue
        key = next(
            (candidate for candidate in managed_keys if filename.startswith(f"{candidate}-")),
            None,
        )
        if key and filename not in expected_files:
            os.remove(os.path.join(ALT, filename))
            removed.append(filename)
    return removed


def publish(new_urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-600:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更,略過部署。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add pay-once alternative landing pages (AEO)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": new_urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            req = urllib.request.Request(ep, data=payload,
                                         headers={"Content-Type": "application/json; charset=utf-8"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--top", type=int, default=4, help="每 app 取前 N 個競品")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(SOV):
        print(f"找不到 {SOV},請先跑 python geo/aeo_sov.py", file=sys.stderr); sys.exit(1)
    data = json.load(open(SOV, encoding="utf-8"))
    by_key = {r["key"]: r for r in data["results"]}

    public_keys = live_app_keys(APPSTORE, PAGES)
    requested = args.apps or list(by_key)
    managed_keys = {k for k in (args.apps or APPS) if k in APPS}
    keys = [k for k in requested if k in by_key and k in APPS and k in public_keys]
    os.makedirs(ALT, exist_ok=True)
    written, urls = [], []
    for k in keys:
        r = by_key[k]
        gaps = r.get("gap_queries", [])
        comps = [c for c, _ in r.get("top_competitors", [])][:args.top]
        for c in comps:
            slug, html_doc = alt_page(k, c, gaps)
            open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
            written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        slug, html_doc = hub_page(k, gaps)
        open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
        written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        print(f"  ✓ {APPS[k]['name']}: {len(comps)} 競品頁 + 1 hub")

    removed = prune_stale_pages(managed_keys, set(written))
    all_files = [f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html"]
    build_index(all_files)
    write_sitemap(all_files)
    urls.append(f"{SITE}/alternatives/index.html")
    print(f"\n共產出 {len(written)} 頁 → {ALT}")
    print(f"清除 {len(removed)} 個過期或不適用頁面")
    print(f"index + sitemap_alternatives.xml 已更新")
    if args.publish:
        publish(urls)
    else:
        print("（加 --publish 可 git push + IndexNow 推送)")


if __name__ == "__main__":
    main()
