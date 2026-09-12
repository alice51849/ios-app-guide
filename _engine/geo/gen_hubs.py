#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Topic hub / pillar pages — 每個 App 一頁,把它的所有內容內部串起來。

集中主題權威度 + 加速爬蟲索引全站(內部連結是排名/被引用的關鍵因子)。
純本機、無 OpenAI、無 App/App Store 變更。輸出 geo/pages/hubs/<key>.html + sitemap_hubs.xml。
"""
import html
import hashlib
import json
import market_availability as market
import market_surface_policy
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from app_store_storefronts import (  # noqa: E402
    PROVIDER_TOKEN_ENV,
    PROVIDER_TOKEN_RE,
    campaign_app_store_url,
    load_storefront_availability,
    resolve_provider_token,
    verified_app_store_url,
)
from appstore_live import live_app_keys  # noqa: E402,F401 - legacy test API only
from live_app_manifest import canonical_manifest  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    OFFICIAL_LOCALE_SET,
    open_graph_locale,
)
from portfolio_app_finder import RTL_LOCALES, UI  # noqa: E402
import gen_mobile_app_identity  # noqa: E402
import gen_store_attribution  # noqa: E402
import queries  # noqa: E402
import rank_opportunity_pages  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
from outreach_bidi import isolate_document

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
HUBS = os.path.join(PAGES, "hubs")
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
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
HTML_LANG_RE = re.compile(
    r'<html\b[^>]*\blang\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE | re.DOTALL,
)
LINK_TAG_RE = re.compile(r"<link\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
REL_ATTR_RE = re.compile(
    r'\brel\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE | re.DOTALL,
)
SOURCE_DIGEST_META = "iag-hub-source-sha256"
SOURCE_DIGEST_RE = re.compile(
    rf'<meta name="{SOURCE_DIGEST_META}" content="(?P<digest>[0-9a-f]{{64}})">\n'
)
LASTMOD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})


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


def authority_apps():
    """Return the canonical live roster and reject registry drift."""
    apps = canonical_manifest()["apps"]
    if apps.get("zipbox", {}).get("app_id") != "6806776579":
        raise ValueError("Canonical live_app_manifest must include verified Zipbox")
    missing_apps = sorted(set(apps) - set(APPS))
    missing_ids = sorted(set(apps) - set(APPSTORE))
    extra_details = []
    for key, app in apps.items():
        registry_id = str(APPSTORE.get(key) or "")
        registry_name = str(APPS.get(key, {}).get("name") or "").strip()
        if registry_id and registry_id != app["app_id"]:
            extra_details.append(
                f"{key}:manifest_id={app['app_id']},registry_id={registry_id}"
            )
        if registry_name and registry_name != app["name"]:
            extra_details.append(
                f"{key}:manifest_name={app['name']!r},registry_name={registry_name!r}"
            )
    if missing_apps or missing_ids or extra_details:
        details = []
        if missing_apps:
            details.append(f"missing APPS={','.join(missing_apps)}")
        if missing_ids:
            details.append(f"missing APPSTORE={','.join(missing_ids)}")
        details.extend(extra_details)
        raise ValueError(
            "Canonical live_app_manifest and registry disagree: "
            + "; ".join(details)
        )
    return apps


def official_locales():
    """Return the exact canonical locale sequence, never a discovered subset."""
    locales = tuple(OFFICIAL_LOCALES)
    if (
        len(locales) != 50
        or len(OFFICIAL_LOCALE_SET) != 50
        or len(locales) != len(OFFICIAL_LOCALE_SET)
        or len(locales) != len(set(locales))
        or frozenset(locales) != OFFICIAL_LOCALE_SET
    ):
        raise ValueError("Topic hubs require the exact official locale roster")
    return locales


def _canonical_link(source, path):
    values = []
    for match in LINK_TAG_RE.finditer(source):
        attrs = match.group("attrs")
        rel = REL_ATTR_RE.search(attrs)
        href = HREF_ATTR_RE.search(attrs)
        if (
            rel is not None
            and "canonical" in rel.group("value").casefold().split()
            and href is not None
        ):
            values.append(html.unescape(href.group("value")).strip())
    if len(values) != 1:
        raise ValueError(f"Expected one canonical link in localized hub source: {path}")
    return values[0]


def _looks_like_english_fallback(localized, english):
    if localized.strip() != english.strip():
        return False
    return len(english.strip()) >= 24 and len(re.findall(r"[A-Za-z]+", english)) >= 4


def _localized_page_copy(key, locale):
    path = Path(PAGES) / locale / f"{key}.html"
    source = _page_source(path)
    language = HTML_LANG_RE.search(source)
    if language is None or language.group("value") != locale:
        raise ValueError(
            f"Localized hub source has wrong language ownership: {path}"
        )
    expected_canonical = f"{SITE}/{locale}/{key}.html"
    if _canonical_link(source, path) != expected_canonical:
        raise ValueError(
            f"Localized hub source has wrong canonical ownership: {path}"
        )
    name = _text_match(source, r"<h1[^>]*>(.*?)</h1>", "app heading", path)
    description = _text_match(
        source,
        r'<meta\s+name="description"\s+content="([^"]*)"',
        "app description",
        path,
    )
    return name, description


def preflight_localized_sources(keys, locales):
    """Read every owned locale source before any public hub is mutated."""
    copies = {}
    for locale in locales:
        for ui_key in ("faq_title", "guide", "why", "store"):
            _ui_text(locale, ui_key)
        for key in keys:
            copies[(key, locale)] = _localized_page_copy(key, locale)
    for key in keys:
        english = copies[(key, "en-US")]
        for locale in locales:
            if locale in ENGLISH_LOCALES:
                continue
            localized = copies[(key, locale)]
            if _looks_like_english_fallback(localized[1], english[1]):
                raise ValueError(
                    f"English fallback in localized hub source: {locale}/{key}.html"
                )
    return copies


def _stamp_source_digest(source):
    if SOURCE_DIGEST_META in source or "</head>" not in source:
        raise ValueError("Hub output cannot be content-stamped safely")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    marker = f'<meta name="{SOURCE_DIGEST_META}" content="{digest}">\n'
    return source.replace("</head>", marker + "</head>", 1)


def embedded_source_digest(source):
    matches = list(SOURCE_DIGEST_RE.finditer(source))
    if len(matches) != 1:
        raise ValueError("Hub page must contain exactly one source digest")
    match = matches[0]
    unstamped = source[:match.start()] + source[match.end():]
    actual = hashlib.sha256(unstamped.encode("utf-8")).hexdigest()
    if match.group("digest") != actual:
        raise ValueError("Generated hub source digest does not match its source")
    return actual


def _existing_source_digest(path):
    try:
        source = Path(path).read_text(encoding="utf-8")
        match = SOURCE_DIGEST_RE.search(source)
        return match.group("digest") if match else None
    except (OSError, UnicodeError):
        return None


def _bound_build_date():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        try:
            seconds = int(epoch)
            if seconds < 0 or str(seconds) != epoch.strip():
                raise ValueError
        except ValueError as error:
            raise ValueError("SOURCE_DATE_EPOCH must be a non-negative integer") from error
        return datetime.fromtimestamp(seconds, timezone.utc).date().isoformat()
    configured = os.environ.get("GEO_BUILD_DATE")
    if configured is not None:
        try:
            return date.fromisoformat(configured).isoformat()
        except ValueError as error:
            raise ValueError("GEO_BUILD_DATE must be YYYY-MM-DD") from error
    completed = subprocess.run(
        ["git", "-C", ROOT, "show", "-s", "--format=%ct", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        seconds = int(completed.stdout.strip())
    except ValueError as error:
        raise ValueError(
            "Set SOURCE_DATE_EPOCH or GEO_BUILD_DATE outside a Git checkout"
        ) from error
    if completed.returncode != 0 or seconds < 0:
        raise ValueError("Unable to derive a deterministic hub build date")
    return datetime.fromtimestamp(seconds, timezone.utc).date().isoformat()


def _previous_lastmods(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ElementTree.ParseError) as error:
        raise ValueError(f"Invalid existing hub sitemap: {path}") from error
    values = {}
    for node in root:
        loc = node.findtext("{*}loc")
        lastmod = node.findtext("{*}lastmod")
        if not loc or not lastmod or LASTMOD_RE.fullmatch(lastmod) is None:
            raise ValueError(f"Invalid existing hub sitemap row: {path}")
        try:
            date.fromisoformat(lastmod)
        except ValueError as error:
            raise ValueError(f"Invalid existing hub sitemap lastmod: {lastmod}") from error
        if loc in values:
            raise ValueError(f"Duplicate existing hub sitemap URL: {loc}")
        values[loc] = lastmod
    return values


def _atomic_write_text(path, source):
    path = Path(path)
    data = source.encode("utf-8")
    try:
        if path.read_bytes() == data:
            return False
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return True


def _sync_directories(paths):
    for path in sorted({Path(value).parent for value in paths}):
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


STYLE = (":root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2}"
         "*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
         "background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);line-height:1.6}a{color:#3840d0}"
         ".wrap{width:min(1040px,100% - 32px);margin:auto}.top{padding:16px 0;border-bottom:1px solid var(--line);"
         "background:rgba(255,255,255,.86);backdrop-filter:blur(12px);position:sticky;top:0;z-index:3}.nav{display:flex;gap:16px}"
         ".nav{flex-wrap:wrap;min-inline-size:0}.nav a{display:inline-block;min-block-size:44px;text-decoration:none;font-weight:700;white-space:normal;overflow-wrap:anywhere}.hero{padding:40px 0 16px}"
         "h1{font-size:clamp(1.8rem,5vw,3rem);margin:.2em 0}h1,h2,p.lead{white-space:normal;overflow-wrap:anywhere;overflow:visible}"
         "h2{font-size:1.3rem;margin:1.4em 0 .5em}p.lead{font-size:1.12rem;color:var(--muted);max-width:100%}"
         ".card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0;box-shadow:0 8px 30px rgba(31,34,78,.06)}"
         ".ll a{display:block;min-block-size:44px;padding:9px 0;border-bottom:1px solid var(--line);text-decoration:none;font-weight:600;"
         "white-space:normal;overflow-wrap:anywhere;overflow:visible}"
         ".cta{display:inline-block;border-radius:999px;background:linear-gradient(135deg,#5b5ff2,#8b5cf6);color:#fff!important;"
         "text-decoration:none;font-weight:800;min-block-size:44px;padding:12px 20px;margin-top:8px;white-space:normal;max-width:100%;overflow-wrap:anywhere;overflow:visible}"
         ".hub-preview{display:block;margin:0 0 24px;border-radius:24px;overflow:hidden;box-shadow:0 18px 50px rgba(31,34,78,.14)}"
         ".hub-preview__image{display:block;width:100%;height:auto}"
         ".pill{display:inline-block;max-inline-size:100%;min-block-size:44px;border:1px solid var(--line);white-space:normal;overflow-wrap:anywhere;"
         "background:#fff;border-radius:999px;padding:6px 12px;margin:3px;font-weight:700;text-decoration:none}"
         ".footer{margin-top:36px;padding:24px 0;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem;"
         "white-space:normal;overflow-wrap:anywhere;overflow:visible}")


def regenerate_layout(source):
    """Use the normal hub stylesheet without rebuilding editorial content."""
    if 'name="iag-hub-app"' not in source:
        return source
    styles = list(re.finditer(r"<style>(.*?)</style>", source, re.S))
    matches = [match for match in styles if ".hub-preview__image" in match[1] and ".ll a{" in match[1]]
    if len(matches) != 1:
        raise ValueError("Hub layout must have exactly one owned stylesheet")
    match = matches[0]
    return source[:match.start(1)] + STYLE + source[match.end(1):]


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
    return _localized_page_copy(key, locale)


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


def build_localized_hub(key, locale, availability=None, page_copy=None):
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported hub locale: {locale}")
    e = html.escape
    name, description = page_copy or localized_page_copy(key, locale)
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
    # gen_app_store_qr_ctas.py hashes this page's first App Store link into the
    # QR image file name, and gen_store_attribution.py rewrites that link
    # afterwards, so a token minted here that the attribution pass disagrees
    # with silently makes the QR code scan to a different campaign than the
    # button beside it.  Mint the final token from the same authority instead.
    store_href = None if market.is_unavailable(locale) else campaign_app_store_url(
        store_url,
        gen_store_attribution.campaign_token(f"{locale}/hubs/{key}.html"),
    )
    section_label = questions_label if answers else why_label
    title = f"{name} · {section_label}"
    # 母語搜尋詞一行散文(見 rank_opportunity_pages):該語言有專用標籤且有詞
    # 才輸出,不影響 title/canonical/hreflang。
    searched_as = rank_opportunity_pages.searched_as_block(
        locale,
        rank_opportunity_pages.phrases_for(key, locale),
        compact=True,
    )
    searched_as_css = rank_opportunity_pages.CSS_TAG if searched_as else ""
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
    store_action = (
        market.note_html(locale, name) if store_href is None else
        f'<a class="cta" href="{e(store_href)}" rel="nofollow noopener">{e(store_label)}</a>'
    )
    document = f'''<!DOCTYPE html>
<html lang="{locale}"{dir_attr}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="iag-hub-app" content="{e(key)}">
<meta name="iag-hub-locale" content="{e(locale)}">
<meta name="iag-hub-source" content="{e(locale)}/{e(key)}.html">
<link rel="canonical" href="{canon}">
{hreflang_links(key)}
{social_metadata}
<style>{STYLE}</style>{searched_as_css}
<script type="application/ld+json">{_schema_json(schema)}</script>
</head><body>
<header class="top"><div class="wrap nav"><a href="{e(guide_url)}">{e(guide_label)}</a></div></header>
<main class="wrap">
<section class="hero">{_preview_html(key, store_href or guide_url, store_label, name)}<h1>{e(name)}</h1><p class="lead">{e(description)}</p>{store_action}</section>
<section class="card"><h2>{e(section_label)}</h2><div class="ll">{resources_html}</div></section>{searched_as}
</main>
<footer class="footer"><div class="wrap"><a href="{e(guide_url)}">{e(name)}</a></div></footer>
</body></html>'''
    return isolate_document(market_surface_policy.enforce_html(document, locale))


def build_hub(key):
    a = APPS[key]
    e = html.escape
    name = a["name"]
    sub = (a.get("sub") or a.get("tag") or "").strip()
    # gen_app_store_qr_ctas.py hashes this page's first App Store link into the
    # QR image file name, and gen_store_attribution.py rewrites that link
    # afterwards, so a token minted here that the attribution pass disagrees
    # with silently makes the QR code scan to a different campaign than the
    # button beside it.  Mint the final token from the same authority instead.
    url = appstore_url(
        key, gen_store_attribution.campaign_token(f"hubs/{key}.html")
    ) or f"{SITE}/en-US/{key}.html"
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
<meta name="iag-hub-app" content="{e(key)}">
<meta name="iag-hub-locale" content="x-default">
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


def _render_outputs(apps, locales, copies, availability):
    keys = tuple(apps)
    outputs = {}
    for key in keys:
        outputs[Path(HUBS, f"{key}.html")] = _stamp_source_digest(
            build_hub(key)
        )
    for locale in locales:
        for key in keys:
            outputs[Path(PAGES, locale, "hubs", f"{key}.html")] = (
                _stamp_source_digest(
                    build_localized_hub(
                        key,
                        locale,
                        availability,
                        page_copy=copies[(key, locale)],
                    )
                )
            )
    e = html.escape
    cards = "".join(
        f'<a class="pill" href="{SITE}/hubs/{key}.html">'
        f'{e(apps[key]["name"])}</a>'
        for key in keys
    )
    idx = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>iOS App Guides — topic hubs</title><meta name="iag-hub-index" content="canonical-live-app-manifest">'
           f'<link rel="canonical" href="{SITE}/hubs/">'
           f'<style>{STYLE}</style></head><body><main class="wrap"><h1 style="margin-top:30px">App topic hubs</h1>'
           f'<div style="margin-top:16px">{cards}</div></main></body></html>')
    outputs[Path(HUBS, "index.html")] = _stamp_source_digest(idx)
    expected_count = len(apps) * (len(locales) + 1) + 1
    if len(outputs) != expected_count:
        raise ValueError(
            f"Hub render set is incomplete: {len(outputs)} != {expected_count}"
        )
    return outputs


def _sitemap_targets(apps, locales, outputs):
    targets = []
    for key in apps:
        targets.append((hub_url(key), Path(HUBS, f"{key}.html")))
    for locale in locales:
        for key in apps:
            targets.append(
                (
                    hub_url(key, locale),
                    Path(PAGES, locale, "hubs", f"{key}.html"),
                )
            )
    targets.append((f"{SITE}/hubs/", Path(HUBS, "index.html")))
    if {path for _, path in targets} != set(outputs):
        raise ValueError("Hub sitemap and rendered output sets disagree")
    return targets


def _render_sitemap(apps, locales, outputs, previous, build_date):
    rows = []
    for url, path in _sitemap_targets(apps, locales, outputs):
        digest = embedded_source_digest(outputs[path])
        unchanged = _existing_source_digest(path) == digest
        lastmod = previous.get(url) if unchanged else None
        if lastmod is None:
            lastmod = build_date
        rows.append(
            f"  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>"
        )
    expected_count = len(apps) * (len(locales) + 1) + 1
    if len(rows) != expected_count or len({url for url, _ in _sitemap_targets(apps, locales, outputs)}) != expected_count:
        raise ValueError("Hub sitemap must contain the exact rendered URL set")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def _prune_stale(apps, locales):
    expected_root = {f"{key}.html" for key in apps} | {"index.html"}
    directories = [(Path(HUBS), expected_root)]
    expected_localized = {f"{key}.html" for key in apps}
    directories.extend(
        (Path(PAGES, locale, "hubs"), expected_localized)
        for locale in locales
    )
    directories.extend(
        (directory, set())
        for directory in Path(PAGES).glob("*/hubs")
        if directory.parent.name not in locales
    )
    removed = 0
    for directory, expected in directories:
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.glob("*.html"):
            if path.name not in expected:
                path.unlink()
                removed += 1
    return removed


def _require_attribution_provider():
    provider = resolve_provider_token()
    if PROVIDER_TOKEN_RE.fullmatch(provider) is None:
        raise ValueError(
            f"{PROVIDER_TOKEN_ENV} must be configured for topic hub attribution"
        )
    os.environ[PROVIDER_TOKEN_ENV] = provider
    return provider


def _generate(apps, locales):
    _require_attribution_provider()
    copies = preflight_localized_sources(tuple(apps), locales)
    availability = load_storefront_availability(Path(PAGES))
    outputs = _render_outputs(apps, locales, copies, availability)
    sitemap_path = Path(PAGES, "sitemap_hubs.xml")
    previous = _previous_lastmods(sitemap_path)
    sitemap = _render_sitemap(
        apps,
        locales,
        outputs,
        previous,
        _bound_build_date(),
    )
    for path in sorted(outputs, key=lambda value: value.as_posix()):
        _atomic_write_text(path, outputs[path])
    removed = _prune_stale(apps, locales)
    _atomic_write_text(sitemap_path, sitemap)
    _sync_directories((*outputs, sitemap_path))
    localized_count = len(apps) * len(locales)
    print(
        f"\u2713 {len(apps)} topic hubs + {localized_count} localized hubs "
        f"+ index + sitemap_hubs.xml; pruned={removed}"
    )


def regenerate_unavailable_hubs():
    """Use the ordinary renderer/digests while preserving published available markets."""
    apps, locales = authority_apps(), official_locales()
    blocked = tuple(locale for locale in locales if market.is_unavailable(locale))
    _require_attribution_provider()
    copies = preflight_localized_sources(tuple(apps), tuple(dict.fromkeys(("en-US", *blocked))))
    availability = load_storefront_availability(Path(PAGES))
    outputs = {}
    for key in apps:
        path = Path(HUBS, f"{key}.html")
        outputs[path] = path.read_text(encoding="utf-8")
    for locale in locales:
        for key in apps:
            path = Path(PAGES, locale, "hubs", f"{key}.html")
            outputs[path] = (
                _stamp_source_digest(build_localized_hub(key, locale, availability, copies[(key, locale)]))
                if locale in blocked else path.read_text(encoding="utf-8")
            )
    index = Path(HUBS, "index.html")
    outputs[index] = index.read_text(encoding="utf-8")
    sitemap_path = Path(PAGES, "sitemap_hubs.xml")
    previous = _previous_lastmods(sitemap_path)
    targets = _sitemap_targets(apps, locales, outputs)
    if set(previous) != {url for url, _ in targets}:
        raise ValueError("Market-only regeneration requires the complete existing hub sitemap")
    rows = []
    for url, path in targets:
        lastmod = previous[url]
        if path.parent.parent.name in blocked:
            generated = embedded_source_digest(outputs[path])
            if _existing_source_digest(path) != generated:
                lastmod = _bound_build_date()
        rows.append(f"  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>")
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows) + "\n</urlset>\n"
    )
    for path, source in outputs.items():
        if path.parent.parent.name in blocked:
            _atomic_write_text(path, source)
    _atomic_write_text(sitemap_path, sitemap)
    return {"apps": len(apps), "blocked_locales": len(blocked), "regenerated": len(apps) * len(blocked)}


def main():
    _generate(authority_apps(), official_locales())


if __name__ == "__main__":
    main()
