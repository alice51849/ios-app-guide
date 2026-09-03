#!/usr/bin/env python3
"""Build and validate ShotInbox's localized public support site."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

from official_locales import (
    OFFICIAL_LOCALES,
    open_graph_locale,
    require_official_locale_coverage,
)
import live_app_guard
from site_config import PUBLIC_SITE  # noqa: E402


APP_NAME = "ShotInbox"
APP_STORE_ID = "6802166527"
APP_SLUG = "shotinbox"
BASE_URL = (
    f"{PUBLIC_SITE}/apps/shotinbox/"
)
SUPPORT_EMAIL = "hourstag.app@gmail.com"
POLICY_VERSION = "2026-08-17"
PAGES = ("index.html", "support.html", "privacy.html", "contact.html")
FIELDS = (
    "overview",
    "support",
    "privacy",
    "contact",
    "tagline",
    "album",
    "analysis",
    "limits_alerts",
    "privacy_data",
    "sensitive",
    "extensions_backup",
    "deletion_storekit",
    "contact_intro",
    "contact_safety",
)
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})
EMAIL_RE = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"
)
STANDARD_SITE_LINK_RE = re.compile(
    r'\s*<link rel="site\.standard\.publication"[^>]*>\s*',
    re.IGNORECASE,
)

SITE_CSS = r"""
:root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light dark;--ink:#24152f;--muted:#66536f;--line:#ffffffc9;--glass:#ffffffc4;--card:#fffafde0;--accent:#704bc7}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 10% 5%,#f7a6ce 0,transparent 31rem),radial-gradient(circle at 92% 12%,#78bde8 0,transparent 34rem),linear-gradient(145deg,#fbe7f2,#fcf9ff 48%,#eef2ff 74%,#eff9fc);color:var(--ink)}main{width:min(1160px,96vw);margin:auto;padding:clamp(22px,5vw,70px) 0}.glass{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:32px;background:var(--glass);box-shadow:0 24px 75px #5c357d25;backdrop-filter:blur(24px);padding:clamp(20px,4vw,46px)}.brand{display:flex;align-items:center;gap:14px}.mark{position:relative;width:68px;height:68px;border-radius:22px;background:linear-gradient(145deg,#f263a0,#9b6fe3 40%,#5b8def 72%,#58afd5);box-shadow:inset 0 1px #fff9,0 16px 40px #794ba650}.mark:before,.mark:after{content:"";position:absolute;left:15px;width:38px;height:21px;border:2px solid #fff;border-radius:7px;background:#ffffff21;box-shadow:inset 0 1px #fff8}.mark:before{top:13px;transform:rotate(-5deg)}.mark:after{top:31px;transform:rotate(4deg)}.wordmark{font-size:14px;font-weight:700;letter-spacing:.19em}.eyebrow{margin:4px 0 0;color:var(--muted);font-size:13px}h1{font-size:clamp(38px,6vw,72px);letter-spacing:-.055em;line-height:.98;margin:30px 0 16px}.lead{max-width:900px;font-size:clamp(18px,2vw,23px);line-height:1.55;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;margin:30px 0}.card{padding:clamp(18px,2.5vw,27px);border:1px solid #d8bce75c;border-radius:24px;background:var(--card);box-shadow:inset 0 1px #fff,0 12px 30px #5d3d7610}.card h2{font-size:clamp(18px,2vw,23px);letter-spacing:-.02em;margin:0 0 9px}.card p{font-size:clamp(15px,1.45vw,18px);line-height:1.66;margin:0}.email{display:inline-flex;margin-top:14px;padding:13px 17px;border:1px solid #ffffffd6;border-radius:16px;background:linear-gradient(135deg,#f263a0,#9b6fe3,#5b8def);color:#fff;font-weight:750;overflow-wrap:anywhere;box-shadow:0 12px 28px #704bc733}nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:28px}a{color:var(--accent);font-weight:750;text-decoration:none}nav a,.language summary{padding:11px 15px;border:1px solid #d8bce777;border-radius:999px;background:#ffffff9e}.language{margin-top:18px}.language summary{display:inline-flex;cursor:pointer;color:var(--accent);font-size:20px;font-weight:750;list-style:none}.language summary::-webkit-details-marker{display:none}.locale-list{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.locale-list a{padding:7px 10px;border-radius:10px;background:#ffffff8f;font-size:13px}.version{margin-top:22px;color:var(--muted);font-size:13px}@media(max-width:720px){main{width:min(100% - 24px,1160px)}.grid{grid-template-columns:1fr}.glass{border-radius:25px}.mark{width:60px;height:60px}.mark:before,.mark:after{left:13px;width:34px}}@media(prefers-color-scheme:dark){:root{--ink:#fff8ff;--muted:#dfcfe5;--line:#ffffff22;--glass:#21152dcc;--card:#301f3cdb;--accent:#dfb7ff}body{background:radial-gradient(circle at 8% 4%,#6e1948 0,transparent 31rem),radial-gradient(circle at 92% 12%,#174d76 0,transparent 34rem),#100d1b}.card,nav a,.language summary,.locale-list a{border-color:#ffffff1d}.email{color:#fff}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
""".strip() + "\n"


def default_site_root() -> Path:
    here = Path(__file__).resolve().parent
    direct = here / "pages"
    if direct.is_dir():
        return direct
    if here.parent.name == "_engine":
        return here.parents[1]
    raise RuntimeError(f"Could not locate the GEO pages repository from {here}")


def copy_path() -> Path:
    return Path(__file__).with_name("shotinbox_site_locales.json")


def site_root_for(root: Path | None) -> Path:
    return (root or default_site_root()).resolve()


def app_root_for(root: Path | None) -> Path:
    return site_root_for(root) / "apps" / APP_SLUG


def load_localized_copy() -> dict[str, dict[str, str]]:
    data = json.loads(copy_path().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ShotInbox locale source must be a JSON object")
    require_official_locale_coverage(APP_SLUG, data)
    expected_fields = set(FIELDS)
    for locale in OFFICIAL_LOCALES:
        values = data[locale]
        if not isinstance(values, dict):
            raise ValueError(f"{locale}: localized copy must be an object")
        actual_fields = set(values)
        if actual_fields != expected_fields:
            missing = sorted(expected_fields - actual_fields)
            extra = sorted(actual_fields - expected_fields)
            raise ValueError(
                f"{locale}: invalid fields; missing={missing}, extra={extra}"
            )
        for key, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{locale}.{key}: value must be non-empty")
            if "<" in value or ">" in value:
                raise ValueError(f"{locale}.{key}: raw HTML is not allowed")
            if EMAIL_RE.search(value):
                raise ValueError(
                    f"{locale}.{key}: email must come from the central constant"
                )
    english = data["en-US"]
    for locale in OFFICIAL_LOCALES:
        if locale in ENGLISH_LOCALES:
            continue
        for key in FIELDS[4:]:
            if data[locale][key] == english[key]:
                raise ValueError(f"{locale}.{key}: untranslated English fallback")
    return data


def page_url(locale: str, page: str) -> str:
    suffix = "" if page == "index.html" else page
    return f"{BASE_URL}l/{locale}/{suffix}"


def page_title(values: dict[str, str], page: str) -> str:
    if page == "index.html":
        return APP_NAME
    key = page.removesuffix(".html")
    return f"{APP_NAME} · {values[key]}"


def alternate_links(locale: str, page: str) -> str:
    links = [
        (
            f'<link rel="alternate" hreflang="{html.escape(item)}" '
            f'href="{html.escape(page_url(item, page), quote=True)}">'
        )
        for item in OFFICIAL_LOCALES
    ]
    links.append(
        '<link rel="alternate" hreflang="x-default" '
        f'href="{html.escape(page_url("en-US", page), quote=True)}">'
    )
    return "".join(links)


def navigation(values: dict[str, str]) -> str:
    return (
        "<nav>"
        f'<a href="./">{html.escape(values["overview"])}</a>'
        f'<a href="support.html">{html.escape(values["support"])}</a>'
        f'<a href="privacy.html">{html.escape(values["privacy"])}</a>'
        f'<a href="contact.html">{html.escape(values["contact"])}</a>'
        "</nav>"
    )


def language_links(locale: str, page: str) -> str:
    links = ""
    for item in OFFICIAL_LOCALES:
        current = ' aria-current="page"' if item == locale else ""
        links += (
            f'<a href="{html.escape(page_url(item, page), quote=True)}"'
            f' hreflang="{html.escape(item)}"{current}>'
            f"{html.escape(item)}</a>"
        )
    return (
        '<details class="language"><summary>🌐</summary>'
        f'<div class="locale-list">{links}</div></details>'
    )


def card(title: str, text: str) -> str:
    return (
        f'<article class="card"><h2>{html.escape(title)}</h2>'
        f"<p>{html.escape(text)}</p></article>"
    )


def email_card(values: dict[str, str]) -> str:
    return (
        f'<article class="card"><h2>{html.escape(values["contact"])}</h2>'
        f'<p>{html.escape(values["contact_intro"])}</p>'
        f'<a class="email" href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>'
        "</article>"
    )


def page_cards(values: dict[str, str], page: str) -> str:
    if page == "index.html":
        cards = (
            card("Photos · ShotInbox", values["album"]),
            card("Vision · NaturalLanguage", values["analysis"]),
            card(values["privacy"], values["privacy_data"]),
            card("Widget · Share · App Group", values["extensions_backup"]),
        )
    elif page == "support.html":
        cards = (
            card("Photos · ShotInbox", values["album"]),
            card("ShotInbox · BGAppRefresh", values["limits_alerts"]),
            card("Widget · Share · App Group", values["extensions_backup"]),
            email_card(values),
        )
    elif page == "privacy.html":
        cards = (
            card(values["privacy"], values["privacy_data"]),
            card("Vision · NaturalLanguage", values["analysis"]),
            card("Face ID · Sensitive", values["sensitive"]),
            card("Widget · Share · App Group", values["extensions_backup"]),
            card("PhotoKit · StoreKit", values["deletion_storekit"]),
            email_card(values),
        )
    else:
        cards = (
            email_card(values),
            card(values["support"], values["contact_safety"]),
            card(values["privacy"], values["privacy_data"]),
        )
    return '<section class="grid">' + "".join(cards) + "</section>"


def render_page(
    localized: dict[str, dict[str, str]],
    locale: str,
    page: str,
) -> str:
    values = localized[locale]
    title = page_title(values, page)
    canonical = page_url(locale, page)
    description = " ".join(
        (
            values["contact_intro"]
            if page == "contact.html"
            else values["tagline"]
        ).split()
    )
    direction = "rtl" if locale in RTL_LOCALES else "ltr"
    page_type = "ContactPage" if page == "contact.html" else "WebPage"
    structured = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "SoftwareApplication",
                    "@id": f"{BASE_URL}#app",
                    "name": APP_NAME,
                    "identifier": APP_STORE_ID,
                    "operatingSystem": "iOS, iPadOS",
                    "applicationCategory": "UtilitiesApplication",
                    "description": values["tagline"],
                },
                {
                    "@type": page_type,
                    "@id": canonical,
                    "url": canonical,
                    "name": title,
                    "description": description,
                    "inLanguage": locale,
                    "about": {"@id": f"{BASE_URL}#app"},
                },
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return (
        "<!doctype html>"
        f'<html lang="{html.escape(locale)}" dir="{direction}"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="index,follow,max-image-preview:large">'
        f'<meta name="apple-itunes-app" content="app-id={APP_STORE_ID}">'
        f'<meta name="application-id" content="{APP_STORE_ID}">'
        '<meta name="theme-color" content="#9b6fe3">'
        f'<meta name="description" content="{html.escape(description, quote=True)}">'
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">'
        f'<meta property="og:description" content="{html.escape(description, quote=True)}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{APP_NAME}">'
        f'<meta property="og:locale" content="{open_graph_locale(locale)}">'
        f'<meta property="og:url" content="{html.escape(canonical, quote=True)}">'
        f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">'
        '<link rel="sitemap" type="application/xml" href="../../sitemap.xml">'
        f"{alternate_links(locale, page)}"
        '<link rel="stylesheet" href="../../site.css">'
        f"<title>{html.escape(title)}</title>"
        f'<script type="application/ld+json">{structured}</script>'
        "</head><body><main><div class=\"glass\">"
        '<header class="brand"><div class="mark" aria-hidden="true"></div>'
        '<div><div class="wordmark">SHOTINBOX</div>'
        f'<p class="eyebrow">App ID {APP_STORE_ID}</p></div></header>'
        f"<h1>{html.escape(title)}</h1>"
        f'<p class="lead">{html.escape(description)}</p>'
        f"{page_cards(values, page)}"
        f"{navigation(values)}"
        f"{language_links(locale, page)}"
        f'<p class="version">{POLICY_VERSION}</p>'
        "</div></main></body></html>\n"
    )


def expected_pages(
    localized: dict[str, dict[str, str]],
    root: Path | None = None,
) -> dict[Path, str]:
    app_root = app_root_for(root)
    return {
        app_root / "l" / locale / page: render_page(
            localized,
            locale,
            page,
        )
        for locale in OFFICIAL_LOCALES
        for page in PAGES
    }


def sitemap_content() -> str:
    body = "".join(
        f"<url><loc>{html.escape(page_url(locale, page))}</loc></url>"
        for locale in OFFICIAL_LOCALES
        for page in PAGES
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</urlset>\n"
    )


def manifest_content() -> str:
    return json.dumps(
        {
            "schemaVersion": 1,
            "app": APP_NAME,
            "appStoreId": APP_STORE_ID,
            "supportEmail": SUPPORT_EMAIL,
            "policyVersion": POLICY_VERSION,
            "localeCount": len(OFFICIAL_LOCALES),
            "locales": list(OFFICIAL_LOCALES),
            "pagesPerLocale": list(PAGES),
            "pageCount": len(OFFICIAL_LOCALES) * len(PAGES),
            "urlPattern": f"{BASE_URL}l/{{locale}}/{{page}}",
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def normalized_html(source: str) -> str:
    return STANDARD_SITE_LINK_RE.sub("", source)


def sitemap_urls(source: str) -> set[str]:
    if "<urlset" not in source or "</urlset>" not in source:
        raise ValueError("sitemap must contain one urlset")
    return {
        html.unescape(value.strip())
        for value in re.findall(r"<loc>(.*?)</loc>", source, re.DOTALL)
    }


def expected_url_set() -> set[str]:
    return {
        page_url(locale, page)
        for locale in OFFICIAL_LOCALES
        for page in PAGES
    }


def validate_site(root: Path | None = None) -> dict[str, int]:
    localized = load_localized_copy()
    app_root = app_root_for(root)
    expected = expected_pages(localized, root)
    errors: list[str] = []

    actual_dirs = (
        {item.name for item in (app_root / "l").iterdir() if item.is_dir()}
        if (app_root / "l").is_dir()
        else set()
    )
    if actual_dirs != set(OFFICIAL_LOCALES):
        errors.append("locale directory set does not match the official 50")

    actual_pages = (
        set((app_root / "l").rglob("*.html"))
        if (app_root / "l").is_dir()
        else set()
    )
    if actual_pages != set(expected):
        errors.append(
            f"page set is stale: expected={len(expected)}, actual={len(actual_pages)}"
        )

    for path, content in expected.items():
        if not path.is_file():
            errors.append(f"missing page: {path}")
            continue
        actual = path.read_text(encoding="utf-8")
        normalized_actual = normalized_html(actual)
        quarantined = live_app_guard._sanitize_html(
            content,
            {APP_STORE_ID},
        )
        if normalized_actual not in {content, quarantined}:
            errors.append(f"stale page: {path}")
        if actual.count('rel="alternate"') != len(OFFICIAL_LOCALES) + 1:
            errors.append(f"invalid hreflang count: {path}")
        emails = set(EMAIL_RE.findall(actual))
        if emails and emails != {SUPPORT_EMAIL}:
            errors.append(f"unexpected public email in {path}: {sorted(emails)}")

    sitemap = app_root / "sitemap.xml"
    if not sitemap.is_file():
        errors.append(f"missing sitemap: {sitemap}")
    else:
        try:
            actual_urls = sitemap_urls(sitemap.read_text(encoding="utf-8"))
        except ValueError as error:
            errors.append(f"invalid sitemap XML: {error}")
        else:
            actual_url_set = frozenset(actual_urls)
            if actual_url_set not in {
                frozenset(),
                frozenset(expected_url_set()),
            }:
                errors.append(
                    "sitemap URL set is stale: "
                    f"expected={len(expected_url_set())}, actual={len(actual_urls)}"
                )

    css = app_root / "site.css"
    if not css.is_file() or css.read_text(encoding="utf-8") != SITE_CSS:
        errors.append(f"missing or stale stylesheet: {css}")

    manifest = app_root / "site-manifest.json"
    if (
        not manifest.is_file()
        or manifest.read_text(encoding="utf-8") != manifest_content()
    ):
        errors.append(f"missing or stale site manifest: {manifest}")

    if app_root.is_dir():
        public_emails = set()
        for path in app_root.rglob("*"):
            if path.is_file() and path.suffix in {".html", ".json", ".xml"}:
                public_emails.update(
                    EMAIL_RE.findall(path.read_text(encoding="utf-8"))
                )
        if public_emails != {SUPPORT_EMAIL}:
            errors.append(
                "public contact email contract failed: "
                f"{sorted(public_emails)}"
            )

    if errors:
        raise RuntimeError("\n".join(errors))
    return {
        "locales": len(OFFICIAL_LOCALES),
        "pages": len(expected),
        "page_types": len(PAGES),
    }


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(content, encoding="utf-8")
    pending.replace(path)


def build_site(root: Path | None = None) -> dict[str, int]:
    localized = load_localized_copy()
    app_root = app_root_for(root)
    pages = expected_pages(localized, root)
    for path, content in pages.items():
        atomic_write(path, content)
    atomic_write(app_root / "site.css", SITE_CSS)
    atomic_write(app_root / "sitemap.xml", sitemap_content())
    atomic_write(app_root / "site-manifest.json", manifest_content())
    return validate_site(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--site-root", type=Path)
    args = parser.parse_args()
    result = (
        validate_site(args.site_root)
        if args.check
        else build_site(args.site_root)
    )
    action = "Verified" if args.check else "Generated"
    print(
        f"{action} {result['pages']} ShotInbox pages: "
        f"{result['locales']} locales x {result['page_types']} page types"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
