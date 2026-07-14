#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Localized Google Web Stories — 用 data/*_full.json 的多語 ASO 文案,產各語言版 Web Story。

零 OpenAI、零帳號。海報沿用英文版(品牌一致),故事文字在地化。輸出 <locale>/stories/<key>.html。
擴大非英語 Google Discover 觸及。不改 App、不改 App Store 內容。
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
sys.path.insert(0, HERE)
import gen_webstories as gw  # noqa: E402
from build_pages_i18n import sanitize_description  # noqa: E402
from gen_webstories import APPS, appstore_url, AMP_BOILER, PALETTES, SITE, PAGES, STORIES  # noqa: E402

DATA = os.path.join(ROOT, "data")
KEY2DATA = {
    "snapport": "snapport_full.json", "sononote": "sono_full.json", "cvdesk": "cv_full.json",
    "picclear": "picclear_full.json", "scanto": "scanto_full.json", "cyca": "cyca_full.json",
    "gmoney": "gmoney_full.json", "hourstag": "hourstag_full.json", "lockhour": "lockhour_full.json",
    "unblurry": "unblurry_full.json", "photocream": "photocream_full.json",
    "lumiletters": "letters_lite_full.json", "lumimath": "math_planet_full.json",
    "lumimission": "mission_routines_full.json", "lumiweather": "weather_full.json",
    "lumiletterspro": "letters_pro_full.json", "lumimathpro": "math_pro_full.json",
    "lumimissionpro": "mission_pro_full.json", "lumibopomofo": "bopomofo_full.json",
    "lumibopomofopro": "bopomofo_pro_full.json", "zodira": "zodira_full.json",
    "aim990": "aim990_full.json", "wordmate": "wordmate_full.json",
}


def load_locales(key):
    fn = KEY2DATA.get(key)
    if not fn:
        return {}
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def hreflang_block(key, locales):
    out = [f'<link rel="alternate" hreflang="en" href="{SITE}/stories/{key}.html">']
    for lc in locales:
        out.append(f'<link rel="alternate" hreflang="{lc}" href="{SITE}/{lc}/stories/{key}.html">')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/stories/{key}.html">')
    return "\n".join(out)


def update_english_hreflang(key, locales):
    path = Path(STORIES) / f"{key}.html"
    text = path.read_text(encoding="utf-8")
    block = hreflang_block(key, locales)
    pattern = re.compile(
        r'(?:\s*<link\b[^>]*\brel="alternate"[^>]*'
        r'\bhreflang="[^"]+"[^>]*>)+',
        re.IGNORECASE,
    )
    if pattern.search(text):
        updated = pattern.sub("\n" + block, text, count=1)
    else:
        canonical = re.search(
            r'<link rel="canonical" href="[^"]+">', text
        )
        if not canonical:
            raise ValueError(f"Missing canonical link in {path}")
        updated = (
            text[: canonical.end()]
            + "\n"
            + block
            + text[canonical.end() :]
        )
    path.write_text(updated, encoding="utf-8")


def localized_story(key, locale, d, all_locales):
    e = html.escape
    a = APPS[key]
    name = (d.get("name") or a["name"]).strip()
    tagline = (d.get("subtitle") or "").strip()
    promo = (d.get("promotionalText") or tagline).strip()
    tagline = sanitize_description(key, locale, tagline)
    promo = sanitize_description(key, locale, promo)
    kws = [k.strip() for k in (d.get("keywords") or "").split(",") if k.strip()][:4]
    pal = gw.palette_for(key)
    c1 = "#%02x%02x%02x" % pal[0]
    c2 = "#%02x%02x%02x" % pal[1]
    url = appstore_url(key, "iag_story") or SITE
    canon = f"{SITE}/{locale}/stories/{key}.html"
    poster = f"{SITE}/stories/img/{key}-poster.jpg"

    def grad(x, y):
        return f"background:linear-gradient(160deg,{x},{y})"

    bullets_html = "".join(f'<p class="b">{e(b)}</p>' for b in kws) or f'<p class="b">{e(tagline)}</p>'
    pages = f'''
  <amp-story-page id="hook">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c1, c2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <h1>{e(name)}</h1><p class="lead">{e(tagline)}</p>
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="what">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c2, c1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center"><h2>{e(promo[:120])}</h2></amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="feat">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c1, c2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad">{bullets_html}</amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="cta">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c2, c1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center"><h2>{e(name)}</h2><p class="lead">App Store</p></amp-story-grid-layer>
    <amp-story-cta-layer><a href="{e(url)}" class="cta">Get it on the App Store →</a></amp-story-cta-layer>
  </amp-story-page>'''

    css = ('h1{font:800 46px/1.1 Arial,sans-serif;color:#fff;margin:0 0 12px}'
           'h2{font:800 32px/1.25 Arial,sans-serif;color:#fff;margin:0}'
           '.lead{font:500 22px/1.4 Arial,sans-serif;color:#fff;opacity:.95;margin:0}'
           '.b{font:600 22px/1.35 Arial,sans-serif;color:#fff;margin:8px 0;padding-left:20px;position:relative}'
           '.b:before{content:"\\2713";position:absolute;left:0;font-weight:800}'
           '.pg{width:100%;height:100%}.pad{padding:52px 40px}.center{justify-content:center;align-items:flex-start}'
           '.cta{background:#fff;color:#111;font:800 18px Arial;padding:14px 22px;border-radius:999px;text-decoration:none}')
    return f'''<!DOCTYPE html>
<html amp lang="{locale}">
<head>
<meta charset="utf-8">
<script async src="https://cdn.ampproject.org/v0.js"></script>
<script async custom-element="amp-story" src="https://cdn.ampproject.org/v0/amp-story-1.0.js"></script>
<title>{e(name)}: {e(tagline)}</title>
<link rel="canonical" href="{canon}">
{hreflang_block(key, all_locales)}
<meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1">
<meta name="description" content="{e(name)} — {e(tagline)}">
{AMP_BOILER}
<style amp-custom>{css}</style>
</head>
<body>
<amp-story standalone title="{e(name)}: {e(tagline)}" publisher="{gw.PUBLISHER}"
  publisher-logo-src="{SITE}/stories/img/publisher-logo.jpg" poster-portrait-src="{poster}">
{pages}
</amp-story>
</body>
</html>'''


def main():
    en_keys = [k for k in APPS if appstore_url(k) and os.path.exists(os.path.join(STORIES, f"{k}.html"))]
    made = 0
    story_urls = [f"{SITE}/stories/{k}.html" for k in en_keys]
    expected_localized = set()
    for key in en_keys:
        locs = load_locales(key)
        locales = [lc for lc in locs if lc not in ("en-US", "en-GB", "en-CA", "en-AU") and locs[lc].get("subtitle")]
        update_english_hreflang(key, locales)
        for lc in locales:
            d = os.path.join(PAGES, lc, "stories")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{key}.html"), "w", encoding="utf-8").write(
                localized_story(key, lc, locs[lc], locales))
            expected_localized.add(Path(d, f"{key}.html").resolve())
            story_urls.append(f"{SITE}/{lc}/stories/{key}.html")
            made += 1
    for stale in Path(PAGES).glob("*/stories/*.html"):
        if stale.resolve() not in expected_localized:
            stale.unlink()
    # rebuild unified sitemap_stories (EN + localized)
    lm = time.strftime("%Y-%m-%d", time.gmtime())
    rows = [f'  <url><loc>{u}</loc><lastmod>{lm}</lastmod></url>' for u in story_urls]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_stories.xml"), "w", encoding="utf-8").write(xml)
    print(f"\u2713 {made} localized web stories; sitemap_stories has {len(story_urls)} urls")


if __name__ == "__main__":
    main()
