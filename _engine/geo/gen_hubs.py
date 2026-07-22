#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Topic hub / pillar pages — 每個 App 一頁,把它的所有內容內部串起來。

集中主題權威度 + 加速爬蟲索引全站(內部連結是排名/被引用的關鍵因子)。
純本機、無 OpenAI、無 App/App Store 變更。輸出 geo/pages/hubs/<key>.html + sitemap_hubs.xml。
"""
import html
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from app_store_storefronts import (  # noqa: E402
    load_storefront_availability,
    verified_app_store_url,
)
from appstore_live import live_app_keys  # noqa: E402
from official_locales import OFFICIAL_LOCALES, open_graph_locale  # noqa: E402
from portfolio_app_finder import RTL_LOCALES, UI  # noqa: E402
import gen_mobile_app_identity  # noqa: E402
import queries  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
HUBS = os.path.join(PAGES, "hubs")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
APP_STORE_ID_RE = re.compile(
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/id(?P<id>[0-9]{9,12})",
    re.IGNORECASE,
)
ANCHOR_TAG_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
CLASS_ATTR_RE = re.compile(
    r'\bclass\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE | re.DOTALL,
)
HREF_ATTR_RE = re.compile(
    r'\bhref\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE | re.DOTALL,
)


def slugify(q):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", q.lower())).strip("-")


def page_title(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"<title>([^<]+)</title>", f.read(2000))
        if m:
            return html.unescape(m.group(1)).split(":")[0].split("|")[0].strip()
    except OSError:
        pass
    return fallback


def exists(rel):
    return os.path.exists(os.path.join(PAGES, rel))


STYLE = (":root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2}"
         "*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
         "background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);line-height:1.6}a{color:#3840d0}"
         ".wrap{width:min(1040px,100% - 32px);margin:auto}.top{padding:16px 0;border-bottom:1px solid var(--line);"
         "background:rgba(255,255,255,.86);backdrop-filter:blur(12px);position:sticky;top:0;z-index:3}.nav{display:flex;gap:16px}"
         ".nav{overflow-x:auto}.nav a{text-decoration:none;font-weight:700;white-space:nowrap}.hero{padding:40px 0 16px}"
         "h1{font-size:clamp(1.8rem,5vw,3rem);margin:.2em 0}h1,h2,p.lead{white-space:nowrap;overflow-x:auto}"
         "h2{font-size:1.3rem;margin:1.4em 0 .5em}p.lead{font-size:1.12rem;color:var(--muted);max-width:100%}"
         ".card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0;box-shadow:0 8px 30px rgba(31,34,78,.06)}"
         ".ll a{display:block;padding:9px 0;border-bottom:1px solid var(--line);text-decoration:none;font-weight:600;"
         "white-space:nowrap;overflow-x:auto}"
         ".cta{display:inline-block;border-radius:999px;background:linear-gradient(135deg,#5b5ff2,#8b5cf6);color:#fff!important;"
         "text-decoration:none;font-weight:800;padding:12px 20px;margin-top:8px;white-space:nowrap;max-width:100%;overflow-x:auto}"
         ".hub-preview{display:block;margin:0 0 24px;border-radius:24px;overflow:hidden;box-shadow:0 18px 50px rgba(31,34,78,.14)}"
         ".hub-preview__image{display:block;width:100%;height:auto}"
         ".pill{display:inline-block;border:1px solid var(--line);white-space:nowrap;"
         "background:#fff;border-radius:999px;padding:6px 12px;margin:3px;font-weight:700;text-decoration:none}"
         ".footer{margin-top:36px;padding:24px 0;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem;"
         "white-space:nowrap;overflow-x:auto}")


def hub_url(key, locale=None):
    if locale is None:
        return f"{SITE}/hubs/{key}.html"
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported hub locale: {locale}")
    return f"{SITE}/{locale}/hubs/{key}.html"


def hreflang_links(key):
    links = [
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{hub_url(key, locale)}">'
        for locale in OFFICIAL_LOCALES
    ]
    links.append(
        f'<link rel="alternate" hreflang="x-default" href="{hub_url(key)}">'
    )
    return "\n".join(links)


def _page_source(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Missing localized hub source: {path}") from error


def _text_match(source, pattern, label, path):
    match = re.search(pattern, source, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(f"Missing {label} in {path}")
    value = re.sub(r"<[^>]+>", "", match.group(1))
    value = html.unescape(value).strip()
    if not value:
        raise ValueError(f"Empty {label} in {path}")
    return value


def localized_page_copy(key, locale):
    path = Path(PAGES) / locale / f"{key}.html"
    source = _page_source(path)
    name = _text_match(source, r"<h1[^>]*>(.*?)</h1>", "app heading", path)
    description = _text_match(
        source,
        r'<meta\s+name="description"\s+content="([^"]*)"',
        "app description",
        path,
    )
    return name, description


def _primary_answer_app_ids(source):
    app_ids = set()
    for anchor in ANCHOR_TAG_RE.finditer(source):
        attrs = anchor.group("attrs")
        class_match = CLASS_ATTR_RE.search(attrs)
        href_match = HREF_ATTR_RE.search(attrs)
        if class_match is None or href_match is None:
            continue
        classes = html.unescape(class_match.group("value")).split()
        if "cta" not in classes:
            continue
        store_match = APP_STORE_ID_RE.fullmatch(
            html.unescape(href_match.group("value")).split("?", 1)[0]
        )
        if store_match is not None:
            app_ids.add(store_match.group("id"))
    return app_ids


def _owned_answer_link(key, rel, fallback_title):
    if not exists(rel):
        return None
    path = os.path.join(PAGES, rel)
    source = _page_source(path)
    app_ids = {
        match.group("id") for match in APP_STORE_ID_RE.finditer(source)
    }
    primary_ids = _primary_answer_app_ids(source)
    owner_ids = primary_ids or app_ids
    if owner_ids != {str(APPSTORE[key])}:
        return None
    return f"{SITE}/{rel}", page_title(path, fallback_title)


def localized_answer_links(key, locale, required=True):
    answers = []
    for question in queries.ALL.get(key, []):
        slug = slugify(question)
        rel = f"{locale}/answers/{slug}.html"
        answer = _owned_answer_link(key, rel, question)
        if answer is not None:
            answers.append(answer)
    unique = list(dict(answers).items())
    if required and not unique:
        raise ValueError(f"No localized answers for {key} in {locale}")
    return unique


def _ui_text(locale, key):
    value = UI.get(locale, {}).get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing localized hub UI text: {locale}.{key}")
    return value.strip()


def _schema_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")


def _app_unfurl_url(key):
    if key not in APPSTORE:
        raise ValueError(f"Unknown app key: {key}")
    return f"{SITE}/social/img/{key}-unfurl.jpg"


def _primary_image_schema(key, caption):
    image_url = _app_unfurl_url(key)
    return {
        "@type": "ImageObject",
        "@id": f"{image_url}#primaryimage",
        "contentUrl": image_url,
        "url": image_url,
        "width": 1200,
        "height": 630,
        "encodingFormat": "image/jpeg",
        "caption": caption,
        "creditText": "Lumi Studio",
        "creator": {
            "@type": "Organization",
            "name": "Lumi Studio",
            "url": SITE,
        },
        "representativeOfPage": True,
    }


def _preview_html(key, store_url, store_label, image_alt):
    e = html.escape
    return (
        f'<a class="hub-preview" href="{e(store_url)}" '
        f'aria-label="{e(store_label)}" rel="nofollow noopener">'
        f'<img class="hub-preview__image" src="{e(_app_unfurl_url(key))}" '
        f'width="1200" height="630" alt="{e(image_alt)}" '
        'decoding="async" fetchpriority="high"></a>'
    )


def _mobile_app_schema(key, name, image_reference, store_url=None):
    app_id = str(APPSTORE[key])
    schema = gen_mobile_app_identity.mobile_app_schema(
        app_id,
        name,
        APPS[key].get("category", "utility"),
    )
    schema.pop("@context")
    schema["image"] = image_reference
    canonical_store_url = gen_mobile_app_identity.canonical_store_url(app_id)
    if store_url and store_url != canonical_store_url:
        schema["sameAs"] = store_url
    return schema


def _social_metadata(key, title, description, canonical, image_alt, locale):
    e = html.escape
    image_url = _app_unfurl_url(key)
    return "\n".join(
        (
            (
                '<meta name="robots" content="index,follow,'
                'max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
            ),
            '<meta property="og:type" content="website">',
            f'<meta property="og:title" content="{e(title)}">',
            f'<meta property="og:description" content="{e(description)}">',
            f'<meta property="og:url" content="{e(canonical)}">',
            f'<meta property="og:image" content="{e(image_url)}">',
            f'<meta property="og:image:secure_url" content="{e(image_url)}">',
            '<meta property="og:image:type" content="image/jpeg">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{e(image_alt)}">',
            f'<meta property="og:locale" content="{open_graph_locale(locale)}">',
            '<meta property="og:site_name" content="iOS App Guide">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{e(title)}">',
            f'<meta name="twitter:description" content="{e(description)}">',
            f'<meta name="twitter:image" content="{e(image_url)}">',
            f'<meta name="twitter:image:alt" content="{e(image_alt)}">',
        )
    )


def build_localized_hub(key, locale, availability=None):
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported hub locale: {locale}")
    e = html.escape
    name, description = localized_page_copy(key, locale)
    answers = localized_answer_links(key, locale, required=False)
    questions_label = _ui_text(locale, "faq_title")
    guide_label = _ui_text(locale, "guide")
    why_label = _ui_text(locale, "why")
    store_label = _ui_text(locale, "store")
    canon = hub_url(key, locale)
    guide_url = f"{SITE}/{locale}/{key}.html"
    if availability is None:
        availability = load_storefront_availability(Path(PAGES))
    store_url = verified_app_store_url(
        f"https://apps.apple.com/app/id{APPSTORE[key]}",
        locale,
        availability,
    )
    section_label = questions_label if answers else why_label
    title = f"{name} · {section_label}"
    social_metadata = _social_metadata(
        key,
        title,
        description,
        canon,
        name,
        locale,
    )
    resources = answers or [(guide_url, guide_label)]
    resources_html = "".join(
        f'<a href="{e(url)}">{e(resource_title)}</a>'
        for url, resource_title in resources
    )
    primary_image = _primary_image_schema(key, name)
    image_reference = {"@id": primary_image["@id"]}
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{canon}#webpage",
        "name": title,
        "description": description,
        "url": canon,
        "inLanguage": locale,
        "primaryImageOfPage": primary_image,
        "image": image_reference,
        "about": _mobile_app_schema(
            key,
            name,
            image_reference,
            store_url,
        ),
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(resources),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": url,
                    "name": answer_title,
                }
                for position, (url, answer_title) in enumerate(resources, 1)
            ],
        },
    }
    dir_attr = ' dir="rtl"' if locale in RTL_LOCALES else ""
    return f'''<!DOCTYPE html>
<html lang="{locale}"{dir_attr}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canon}">
{hreflang_links(key)}
{social_metadata}
<style>{STYLE}</style>
<script type="application/ld+json">{_schema_json(schema)}</script>
</head><body>
<header class="top"><div class="wrap nav"><a href="{e(guide_url)}">{e(guide_label)}</a></div></header>
<main class="wrap">
<section class="hero">{_preview_html(key, store_url, store_label, name)}<h1>{e(name)}</h1><p class="lead">{e(description)}</p><a class="cta" href="{e(store_url)}" rel="nofollow noopener">{e(store_label)}</a></section>
<section class="card"><h2>{e(section_label)}</h2><div class="ll">{resources_html}</div></section>
</main>
<footer class="footer"><div class="wrap"><a href="{e(guide_url)}">{e(name)}</a></div></footer>
</body></html>'''


def build_hub(key):
    a = APPS[key]
    e = html.escape
    name = a["name"]
    sub = (a.get("sub") or a.get("tag") or "").strip()
    url = appstore_url(key, "iag_hub") or f"{SITE}/en-US/{key}.html"
    canon = hub_url(key)
    title = f"{name}: guides, answers & alternatives | iOS App Guide"
    description = (
        f"Everything about {name} — {sub}. Buying guides, answers to common "
        "questions, comparisons and the App Store link."
    )
    social_metadata = _social_metadata(
        key,
        title,
        description,
        canon,
        name,
        "en-US",
    )
    store_label = f"Get {name} on the App Store"
    primary_image = _primary_image_schema(key, name)
    image_reference = {"@id": primary_image["@id"]}

    # answer pages (this app), existing only, with titles
    ans = []
    for q in queries.ALL.get(key, []):
        s = slugify(q)
        rel = f"answers/{s}.html"
        answer = _owned_answer_link(key, rel, q)
        if answer is not None:
            ans.append(answer)
    ans_html = "".join(f'<a href="{e(u)}">{e(t)}</a>' for u, t in dict((u, t) for u, t in ans).items()) or "<p>Coming soon.</p>"

    # other resources
    res = []
    if exists(f"en-US/{key}.html"):
        res.append((f"{SITE}/en-US/{key}.html", f"{name} — overview & FAQ"))
    if exists(f"guides/{key}.html"):
        res.append((f"{SITE}/guides/{key}.html", f"How to choose: {name} guide"))
    if exists(f"stories/{key}.html"):
        res.append((f"{SITE}/stories/{key}.html", f"{name} — visual story"))
    for f in sorted(os.listdir(os.path.join(PAGES, "alternatives"))) if os.path.isdir(os.path.join(PAGES, "alternatives")) else []:
        if f.startswith(key + "-") and f.endswith(".html"):
            res.append((f"{SITE}/alternatives/{f}", page_title(os.path.join(PAGES, "alternatives", f), f)))
    res_html = "".join(f'<a href="{e(u)}">{e(t)}</a>' for u, t in res) or ""
    resources = list(dict([*ans, *res]).items())
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{canon}#webpage",
        "name": f"{name} resources",
        "description": description,
        "url": canon,
        "inLanguage": "en",
        "primaryImageOfPage": primary_image,
        "image": image_reference,
        "about": _mobile_app_schema(
            key,
            name,
            image_reference,
        ),
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(resources),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": position,
                    "url": resource_url,
                    "name": resource_title,
                }
                for position, (resource_url, resource_title) in enumerate(
                    resources, 1
                )
            ],
        },
    }

    # Language pills point to app-specific localized resource hubs.
    langs_html = "".join(
        f'<a class="pill" href="{hub_url(key, locale)}" '
        f'hreflang="{locale}">{locale}</a>'
        for locale in OFFICIAL_LOCALES
    )

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canon}">
{hreflang_links(key)}
{social_metadata}
<style>{STYLE}</style>
<script type="application/ld+json">{_schema_json(schema)}</script>
</head><body>
<header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><a href="{SITE}/answers/">Answers</a><a href="{SITE}/stories/">Stories</a></div></header>
<main class="wrap">
<section class="hero">{_preview_html(key, url, store_label, name)}<h1>{e(name)}</h1><p class="lead">{e(sub)}</p><a class="cta" href="{e(url)}">{e(store_label)} →</a></section>
<section class="card"><h2>Answers to common questions</h2><div class="ll">{ans_html}</div></section>
{"<section class='card'><h2>Guides, comparisons & more</h2><div class='ll'>" + res_html + "</div></section>" if res_html else ""}
{"<section class='card'><h2>Available in your language</h2>" + langs_html + "</section>" if langs_html else ""}
</main>
<footer class="footer"><div class="wrap">Independent iOS app guide. <a href="{e(url)}">{e(name)} on the App Store</a>.</div></footer>
</body></html>'''


def main():
    os.makedirs(HUBS, exist_ok=True)
    live_keys = live_app_keys(APPSTORE, PAGES, refresh=False)
    keys = [k for k in APPS if k in live_keys]
    expected = set(keys)
    for filename in os.listdir(HUBS):
        if (
            filename.endswith(".html")
            and filename != "index.html"
            and filename.removesuffix(".html") not in expected
        ):
            os.remove(os.path.join(HUBS, filename))
    for k in keys:
        Path(HUBS, f"{k}.html").write_text(
            build_hub(k),
            encoding="utf-8",
        )
    localized_count = 0
    availability = load_storefront_availability(Path(PAGES))
    for locale in OFFICIAL_LOCALES:
        localized_dir = os.path.join(PAGES, locale, "hubs")
        os.makedirs(localized_dir, exist_ok=True)
        for filename in os.listdir(localized_dir):
            if (
                filename.endswith(".html")
                and filename != "index.html"
                and filename.removesuffix(".html") not in expected
            ):
                os.remove(os.path.join(localized_dir, filename))
        for key in keys:
            target = Path(localized_dir, f"{key}.html")
            target.write_text(
                build_localized_hub(key, locale, availability),
                encoding="utf-8",
            )
            localized_count += 1
    # index
    e = html.escape
    cards = "".join(f'<a class="pill" href="{SITE}/hubs/{k}.html">{e(APPS[k]["name"])}</a>' for k in keys)
    idx = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>iOS App Guides — topic hubs</title><link rel="canonical" href="{SITE}/hubs/">'
           f'<style>{STYLE}</style></head><body><main class="wrap"><h1 style="margin-top:30px">App topic hubs</h1>'
           f'<div style="margin-top:16px">{cards}</div></main></body></html>')
    Path(HUBS, "index.html").write_text(idx, encoding="utf-8")
    # sitemap
    lm = time.strftime("%Y-%m-%d", time.gmtime())
    rows = [f'  <url><loc>{SITE}/hubs/{k}.html</loc><lastmod>{lm}</lastmod></url>' for k in keys]
    rows.extend(
        f'  <url><loc>{hub_url(key, locale)}</loc><lastmod>{lm}</lastmod></url>'
        for locale in OFFICIAL_LOCALES
        for key in keys
    )
    rows.append(f'  <url><loc>{SITE}/hubs/</loc><lastmod>{lm}</lastmod></url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    Path(PAGES, "sitemap_hubs.xml").write_text(xml, encoding="utf-8")
    print(
        f"\u2713 {len(keys)} topic hubs + {localized_count} localized hubs "
        "+ index + sitemap_hubs.xml"
    )


if __name__ == "__main__":
    main()
