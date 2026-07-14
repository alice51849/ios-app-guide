#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Web Stories (AMP Story) generator — 全自動、進 Google Discover。

每個 App 產一個有效 AMP Story(海報 + 5 頁 + App Store CTA,帶 ct=iag_story 歸因)。
輸出 geo/pages/stories/<key>.html + stories/img/*.jpg + stories/index.html + sitemap_stories.xml。
純本機生成(PIL 海報 + registry 文案),不改 App、不改 App Store 內容。
"""
import hashlib
import html
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402

PAGES = os.path.join(HERE, "pages")
STORIES = os.path.join(PAGES, "stories")
IMG = os.path.join(STORIES, "img")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
PUBLISHER = "iOS App Guide"

PALETTES = [((91, 95, 242), (139, 92, 246)), ((15, 143, 95), (5, 150, 105)),
            ((236, 72, 153), (168, 85, 247)), ((14, 165, 233), (59, 130, 246)),
            ((245, 158, 11), (239, 68, 68)), ((20, 184, 166), (6, 148, 162))]
LEGACY_PALETTE_INDEX = {
    "aim990": 4,
    "cvdesk": 4,
    "cyca": 5,
    "gmoney": 3,
    "hourstag": 0,
    "lockhour": 3,
    "lumibopomofo": 5,
    "lumibopomofopro": 0,
    "lumiletters": 0,
    "lumiletterspro": 3,
    "lumimath": 1,
    "lumimathpro": 5,
    "lumimission": 1,
    "lumimissionpro": 0,
    "lumiweather": 5,
    "mochi": 1,
    "photocream": 0,
    "picclear": 2,
    "scanto": 5,
    "sereno": 0,
    "snapport": 3,
    "sononote": 0,
    "tripbee": 3,
    "tripplanet": 0,
    "unblurry": 5,
}

FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_BLK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
FONT_R = "/System/Library/Fonts/Supplemental/Arial.ttf"

AMP_BOILER = ('<style amp-boilerplate>body{-webkit-animation:-amp-start 8s steps(1,end) 0s 1 normal both;'
              '-moz-animation:-amp-start 8s steps(1,end) 0s 1 normal both;-ms-animation:-amp-start 8s steps(1,end) 0s 1 normal both;'
              'animation:-amp-start 8s steps(1,end) 0s 1 normal both}@-webkit-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}'
              '@-moz-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}@-ms-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}'
              '@-o-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}@keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}</style>'
              '<noscript><style amp-boilerplate>body{-webkit-animation:none;-moz-animation:none;-ms-animation:none;animation:none}</style></noscript>')


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_poster(key, name, tagline, pal):
    W, H = 720, 960
    c1, c2 = pal
    img = Image.new("RGB", (W, H), c1)
    top = Image.new("RGB", (W, H), c1)
    px = top.load()
    for y in range(H):
        t = y / H
        for x in range(W):
            px[x, y] = (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t),
                        int(c1[2] + (c2[2] - c1[2]) * t))
    img = top
    d = ImageDraw.Draw(img)
    # app icon
    icon_path = os.path.expanduser(APPS[key].get("icon", ""))
    if icon_path and os.path.exists(icon_path):
        try:
            ic = Image.open(icon_path).convert("RGB").resize((260, 260))
            mask = Image.new("L", (260, 260), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, 260, 260], radius=58, fill=255)
            img.paste(ic, (W // 2 - 130, 150), mask)
        except Exception:  # noqa: BLE001
            pass
    # name
    fn = _font(FONT_BLK, 72)
    lines = _wrap(d, name, fn, W - 100)
    y = 470
    for ln in lines:
        w = d.textlength(ln, font=fn)
        d.text(((W - w) / 2, y), ln, font=fn, fill="white")
        y += 82
    # tagline
    ft = _font(FONT_R, 38)
    for ln in _wrap(d, tagline, ft, W - 120)[:3]:
        w = d.textlength(ln, font=ft)
        d.text(((W - w) / 2, y + 14), ln, font=ft, fill=(255, 255, 255))
        y += 50
    # footer
    ff = _font(FONT_B, 34)
    foot = "Get it on the App Store"
    w = d.textlength(foot, font=ff)
    d.text(((W - w) / 2, H - 90), foot, font=ff, fill="white")
    os.makedirs(IMG, exist_ok=True)
    p = os.path.join(IMG, f"{key}-poster.jpg")
    img.save(p, "JPEG", quality=82)
    return p


def make_logo():
    """One shared 128x128 publisher logo."""
    img = Image.new("RGB", (128, 128), (91, 95, 242))
    d = ImageDraw.Draw(img)
    f = _font(FONT_BLK, 74)
    d.text((30, 20), "iA", font=f, fill="white")
    os.makedirs(IMG, exist_ok=True)
    p = os.path.join(IMG, "publisher-logo.jpg")
    img.save(p, "JPEG", quality=85)
    return p


def palette_for(key):
    palette_index = LEGACY_PALETTE_INDEX.get(key)
    if palette_index is None:
        palette_index = int.from_bytes(
            hashlib.sha256(key.encode("utf-8")).digest()[:4], "big"
        ) % len(PALETTES)
    return PALETTES[palette_index]


def story_html(key):
    a = APPS[key]
    e = html.escape
    name = a["name"]
    tagline = (a.get("sub") or a.get("tag") or "").strip()
    kicker = (a.get("kicker") or "").strip()
    title = (a.get("title") or tagline).strip()
    bullets = a.get("cta_bullets", [])[:4]
    pal = palette_for(key)
    make_poster(key, name, tagline, pal)
    url = appstore_url(key, "iag_story") or SITE
    canon = f"{SITE}/stories/{key}.html"
    c1 = "#%02x%02x%02x" % pal[0]
    c2 = "#%02x%02x%02x" % pal[1]

    def grad(a1, a2):
        return f"background:linear-gradient(160deg,{a1},{a2})"

    bullets_html = "".join(f'<p class="b">{e(b)}</p>' for b in bullets) or f'<p class="b">{e(tagline)}</p>'
    pages = f'''
  <amp-story-page id="hook">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c1, c2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <div class="kick">{e(kicker or "iOS App")}</div>
      <h1>{e(name)}</h1><p class="lead">{e(tagline)}</p>
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="what">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c2, c1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <h2>{e(title)}</h2>
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="feat">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c1, c2)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad">
      <h2>Why people pick it</h2>{bullets_html}
    </amp-story-grid-layer>
  </amp-story-page>
  <amp-story-page id="cta">
    <amp-story-grid-layer template="fill"><div class="pg" style="{grad(c2, c1)}"></div></amp-story-grid-layer>
    <amp-story-grid-layer template="vertical" class="pad center">
      <h2>{e(name)}</h2><p class="lead">Download on the App Store</p>
    </amp-story-grid-layer>
    <amp-story-cta-layer>
      <a href="{e(url)}" class="cta">Get it on the App Store →</a>
    </amp-story-cta-layer>
  </amp-story-page>'''

    css = ('h1{font:800 46px/1.1 Arial,sans-serif;color:#fff;margin:0 0 12px}'
           'h2{font:800 34px/1.2 Arial,sans-serif;color:#fff;margin:0 0 16px}'
           '.lead{font:500 22px/1.4 Arial,sans-serif;color:#fff;opacity:.95;margin:0}'
           '.kick{font:800 15px/1 Arial;letter-spacing:.12em;text-transform:uppercase;color:#fff;opacity:.85;margin-bottom:14px}'
           '.b{font:600 22px/1.35 Arial,sans-serif;color:#fff;margin:8px 0;padding-left:20px;position:relative}'
           '.b:before{content:"\\2713";position:absolute;left:0;font-weight:800}'
           '.pg{width:100%;height:100%}.pad{padding:52px 40px}.center{justify-content:center;align-items:flex-start}'
           '.cta{background:#fff;color:#111;font:800 18px Arial;padding:14px 22px;border-radius:999px;text-decoration:none}')

    return f'''<!DOCTYPE html>
<html amp lang="en">
<head>
<meta charset="utf-8">
<script async src="https://cdn.ampproject.org/v0.js"></script>
<script async custom-element="amp-story" src="https://cdn.ampproject.org/v0/amp-story-1.0.js"></script>
<title>{e(name)}: {e(tagline)}</title>
<link rel="canonical" href="{canon}">
<meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1">
<meta name="description" content="{e(name)} — {e(tagline)}">
{AMP_BOILER}
<style amp-custom>{css}</style>
</head>
<body>
<amp-story standalone title="{e(name)}: {e(tagline)}" publisher="{PUBLISHER}"
  publisher-logo-src="{SITE}/stories/img/publisher-logo.jpg"
  poster-portrait-src="{SITE}/stories/img/{key}-poster.jpg">
{pages}
</amp-story>
</body>
</html>'''


def build_index(keys):
    e = html.escape
    cards = "".join(
        f'<a class="c" href="{SITE}/stories/{k}.html"><img src="{SITE}/stories/img/{k}-poster.jpg" '
        f'alt="{e(APPS[k]["name"])}" loading="lazy"><span>{e(APPS[k]["name"])}</span></a>' for k in keys)
    doc = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>iOS App Web Stories</title><meta name="description" content="Visual web stories for iOS apps.">
<link rel="canonical" href="{SITE}/stories/">
<style>body{{margin:0;font-family:Arial,sans-serif;background:#f7f7fb}}.wrap{{max-width:1040px;margin:auto;padding:24px}}
h1{{font-size:1.6rem}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}}
.c{{position:relative;border-radius:16px;overflow:hidden;text-decoration:none;aspect-ratio:3/4;display:block}}
.c img{{width:100%;height:100%;object-fit:cover}}.c span{{position:absolute;left:0;right:0;bottom:0;padding:10px;color:#fff;
font-weight:800;background:linear-gradient(transparent,rgba(0,0,0,.6))}}</style></head>
<body><div class="wrap"><h1>iOS App Web Stories</h1><div class="grid">{cards}</div></div></body></html>'''
    open(os.path.join(STORIES, "index.html"), "w", encoding="utf-8").write(doc)


def build_sitemap(keys):
    import time
    lm = time.strftime("%Y-%m-%d", time.gmtime())
    rows = []
    for k in keys:
        rows.append(f'  <url><loc>{SITE}/stories/{k}.html</loc><lastmod>{lm}</lastmod>'
                    f'<image:image><image:loc>{SITE}/stories/img/{k}-poster.jpg</image:loc></image:image></url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' + "\n".join(rows) + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_stories.xml"), "w", encoding="utf-8").write(xml)


def main():
    os.makedirs(IMG, exist_ok=True)
    make_logo()
    live_keys = live_app_keys(APPSTORE, PAGES, refresh=False)
    keys = [k for k in APPS if k in live_keys and appstore_url(k)]
    expected = set(keys)
    for stale in Path(STORIES).glob("*.html"):
        if stale.name != "index.html" and stale.stem not in expected:
            stale.unlink()
    for stale in Path(IMG).glob("*-poster.jpg"):
        if stale.name.removesuffix("-poster.jpg") not in expected:
            stale.unlink()
    for k in keys:
        open(os.path.join(STORIES, f"{k}.html"), "w", encoding="utf-8").write(story_html(k))
    build_index(keys)
    build_sitemap(keys)
    print(f"\u2713 {len(keys)} web stories + posters \u2192 {STORIES}")


if __name__ == "__main__":
    main()
