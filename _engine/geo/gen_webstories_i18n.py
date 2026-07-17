#!/usr/bin/env python3
"""Generate strict 50-locale Web Stories and discovery indexes for live apps."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402

from appstore_live import live_app_keys  # noqa: E402
from build_pages_i18n import (  # noqa: E402
    RTL,
    base_lang,
    get_ui,
    load_app_locales,
)
from gen_webstories import AMP_BOILER, PUBLISHER, palette_for  # noqa: E402
from gen_mobile_app_identity import mobile_app_schema  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    require_official_locale_coverage,
)

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
REQUIRED_FIELDS = ("name", "subtitle", "description", "keywords", "promotionalText")
ALT_LINK_RE = re.compile(
    r'\s*<link\s+rel=["\']alternate["\'][^>]*>\s*',
    re.IGNORECASE,
)


def story_url(key, locale=None):
    prefix = f"/{locale}" if locale else ""
    return f"{SITE}{prefix}/stories/{key}.html"


def index_url(locale=None):
    prefix = f"/{locale}" if locale else ""
    return f"{SITE}{prefix}/stories/"


def alternate_links(path_for_locale, root_path):
    links = [
        f'<link rel="alternate" hreflang="x-default" href="{SITE}{root_path}">',
        f'<link rel="alternate" hreflang="en" href="{SITE}{root_path}">',
    ]
    links.extend(
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{SITE}/{locale}{path_for_locale(locale)}">'
        for locale in OFFICIAL_LOCALES
    )
    return "\n".join(links)


def story_alternate_links(key):
    return alternate_links(
        lambda _locale: f"/stories/{key}.html",
        f"/stories/{key}.html",
    )


def index_alternate_links():
    return alternate_links(lambda _locale: "/stories/", "/stories/")


def replace_alternate_links(path, links):
    if not path.exists():
        raise FileNotFoundError(f"Missing English Web Story surface: {path}")
    document = ALT_LINK_RE.sub("", path.read_text(encoding="utf-8"))
    if "</head>" not in document:
        raise ValueError(f"Missing </head> in {path}")
    document = document.replace("</head>", f"{links}\n</head>", 1)
    path.write_text(document, encoding="utf-8")


def validated_localizations(key):
    localizations = load_app_locales(key)
    require_official_locale_coverage(key, localizations)
    for locale in OFFICIAL_LOCALES:
        missing = [
            field
            for field in REQUIRED_FIELDS
            if not str(localizations[locale].get(field) or "").strip()
        ]
        if missing:
            raise ValueError(
                f"{key}/{locale} has empty Web Story fields: {','.join(missing)}"
            )
    return localizations


def feature_points(localization):
    keywords = [
        value.strip()
        for value in re.split(r"[,，、؛]+", localization["keywords"])
        if value.strip()
    ]
    return keywords[:4] or [localization["subtitle"].strip()]


def story_html(key, locale, localization):
    escape = html.escape
    name = localization["name"].strip()
    subtitle = localization["subtitle"].strip()
    promotional_text = localization["promotionalText"].strip()
    points = feature_points(localization)
    ui = get_ui(locale)
    palette = palette_for(key)
    color1 = "#%02x%02x%02x" % palette[0]
    color2 = "#%02x%02x%02x" % palette[1]
    app_url = appstore_url(key, "iag_story") or SITE
    canonical = story_url(key, locale)
    direction = "rtl" if base_lang(locale) in RTL else "ltr"
    app_id = APPSTORE[key]
    identity = mobile_app_schema(
        app_id,
        name,
        APPS[key].get("category", "utility"),
        canonical,
    )
    identity["description"] = promotional_text
    identity_json = json.dumps(identity, ensure_ascii=False).replace("</", "<\\/")

    def gradient(start, end):
        return f"background:linear-gradient(160deg,{start},{end})"

    bullets = "".join(
        f'<p class="bullet">{escape(point)}</p>' for point in points
    )
    pages = f"""
  <amp-story-page id="hook">
    <amp-story-grid-layer template="fill"><div class="page" style="{gradient(color1, color2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <div class="kicker">iOS</div>
      <h1>{escape(name)}</h1><p class="lead">{escape(subtitle)}</p>
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="what">
    <amp-story-grid-layer template="fill"><div class="page" style="{gradient(color2, color1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <h2>{escape(subtitle)}</h2><p class="lead">{escape(promotional_text)}</p>
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="features">
    <amp-story-grid-layer template="fill"><div class="page" style="{gradient(color1, color2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad">
      <h2>{escape(ui["feat"])}</h2>{bullets}
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="cta">
    <amp-story-grid-layer template="fill"><div class="page" style="{gradient(color2, color1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <h2>{escape(name)}</h2><p class="lead">{escape(ui["dl"])}</p>
    </amp-story-grid-layer>
    <amp-story-cta-layer>
      <a href="{escape(app_url, quote=True)}" class="cta">{escape(ui["get"].format(name=name))} →</a>
    </amp-story-cta-layer>
  </amp-story-page>"""
    css = (
        'h1{font:800 46px/1.15 -apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;color:#fff;margin:0 0 12px}'
        'h2{font:800 34px/1.25 -apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;color:#fff;margin:0 0 16px}'
        '.lead{font:500 22px/1.45 -apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;color:#fff;opacity:.96;margin:0}'
        '.kicker{font:800 15px/1 -apple-system,BlinkMacSystemFont,sans-serif;letter-spacing:.12em;color:#fff;opacity:.85;margin-bottom:14px}'
        '.bullet{font:650 22px/1.4 -apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;color:#fff;margin:8px 0;padding-inline-start:24px;position:relative}'
        '.bullet:before{content:"\\2713";position:absolute;inset-inline-start:0;font-weight:800}'
        '.page{width:100%;height:100%}.pad{padding:52px 40px}.center{justify-content:center;align-items:flex-start}'
        '.cta{background:#fff;color:#111;font:800 17px/1.2 -apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;padding:14px 22px;border-radius:999px;text-decoration:none}'
    )
    return f"""<!DOCTYPE html>
<html amp lang="{locale}" dir="{direction}">
<head>
<meta charset="utf-8">
<script async src="https://cdn.ampproject.org/v0.js"></script>
<script async custom-element="amp-story" src="https://cdn.ampproject.org/v0/amp-story-1.0.js"></script>
<title>{escape(name)}: {escape(subtitle)}</title>
<link rel="canonical" href="{canonical}">
{story_alternate_links(key)}
<meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1">
<meta name="description" content="{escape(promotional_text, quote=True)}">
<meta name="apple-itunes-app" content="app-id={app_id}, app-argument={escape(app_url, quote=True)}">
<script type="application/ld+json">{identity_json}</script>
{AMP_BOILER}
<style amp-custom>{css}</style>
</head>
<body>
<amp-story standalone title="{escape(name, quote=True)}: {escape(subtitle, quote=True)}" publisher="{PUBLISHER}"
  publisher-logo-src="{SITE}/stories/img/publisher-logo.jpg"
  poster-portrait-src="{SITE}/stories/img/{key}-poster.jpg">
{pages}
</amp-story>
</body>
</html>"""


def localized_index_html(locale, keys, localizations_by_key):
    escape = html.escape
    ui = get_ui(locale)
    direction = "rtl" if base_lang(locale) in RTL else "ltr"
    cards = "".join(
        f'<a class="card" href="{story_url(key, locale)}">'
        f'<img src="{SITE}/stories/img/{key}-poster.jpg" '
        f'alt="{escape(localizations_by_key[key][locale]["name"], quote=True)}" loading="lazy">'
        f'<span><strong>{escape(localizations_by_key[key][locale]["name"])}</strong>'
        f'<small>{escape(localizations_by_key[key][locale]["subtitle"])}</small></span></a>'
        for key in keys
    )
    return f"""<!DOCTYPE html>
<html lang="{locale}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(ui["dir_dir"])} — Web Stories</title>
<meta name="description" content="{escape(ui["dir_lead"], quote=True)}">
<link rel="canonical" href="{index_url(locale)}">
{index_alternate_links()}
<style>
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans",sans-serif;background:#f7f7fb;color:#17171c}}
.wrap{{max-width:1120px;margin:auto;padding:28px 20px 44px}}h1{{font-size:clamp(1.7rem,4vw,2.5rem);margin:0 0 8px}}
.lead{{color:#5a5a66;margin:0 0 24px;max-width:780px}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:16px}}
.card{{position:relative;border-radius:20px;overflow:hidden;text-decoration:none;aspect-ratio:3/4;display:block;box-shadow:0 8px 28px #25254a18}}
.card img{{width:100%;height:100%;object-fit:cover}}.card span{{position:absolute;inset-inline:0;bottom:0;padding:42px 14px 14px;color:#fff;background:linear-gradient(transparent,rgba(0,0,0,.78))}}
.card strong,.card small{{display:block}}.card strong{{font-size:1rem}}.card small{{font-size:.78rem;margin-top:4px;opacity:.9}}
</style>
</head>
<body><main class="wrap"><h1>{escape(ui["dir_dir"])}</h1><p class="lead">{escape(ui["dir_lead"])}</p><div class="grid">{cards}</div></main></body>
</html>"""


def build_sitemap(keys):
    lastmod = time.strftime("%Y-%m-%d", time.gmtime())
    rows = []
    for key in keys:
        image = f"{SITE}/stories/img/{key}-poster.jpg"
        for locale in (None, *OFFICIAL_LOCALES):
            rows.append(
                f"  <url><loc>{story_url(key, locale)}</loc><lastmod>{lastmod}</lastmod>"
                f"<image:image><image:loc>{image}</image:loc></image:image></url>"
            )
    for locale in (None, *OFFICIAL_LOCALES):
        rows.append(
            f"  <url><loc>{index_url(locale)}</loc><lastmod>{lastmod}</lastmod></url>"
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    (PAGES / "sitemap_stories.xml").write_text(document, encoding="utf-8")


def cleanup_stale_stories(keys):
    expected = set(keys)
    for stories_dir in PAGES.glob("*/stories"):
        locale = stories_dir.parent.name
        if locale not in OFFICIAL_LOCALES:
            continue
        for page in stories_dir.glob("*.html"):
            if page.name != "index.html" and page.stem not in expected:
                page.unlink()


def main():
    live_keys = live_app_keys(APPSTORE, str(PAGES), refresh=False)
    keys = [key for key in APPS if key in live_keys and appstore_url(key)]
    if not keys:
        raise RuntimeError("No publicly available apps found for Web Stories")
    localizations_by_key = {
        key: validated_localizations(key)
        for key in keys
    }

    cleanup_stale_stories(keys)
    for key in keys:
        replace_alternate_links(
            PAGES / "stories" / f"{key}.html",
            story_alternate_links(key),
        )
    replace_alternate_links(PAGES / "stories" / "index.html", index_alternate_links())

    for locale in OFFICIAL_LOCALES:
        stories_dir = PAGES / locale / "stories"
        stories_dir.mkdir(parents=True, exist_ok=True)
        for key in keys:
            (stories_dir / f"{key}.html").write_text(
                story_html(key, locale, localizations_by_key[key][locale]),
                encoding="utf-8",
            )
        (stories_dir / "index.html").write_text(
            localized_index_html(locale, keys, localizations_by_key),
            encoding="utf-8",
        )

    build_sitemap(keys)
    print(
        f"✓ {len(keys) * len(OFFICIAL_LOCALES)} localized Web Stories "
        f"+ {len(OFFICIAL_LOCALES)} locale indexes → {PAGES}"
    )


if __name__ == "__main__":
    main()
