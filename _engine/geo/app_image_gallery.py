#!/usr/bin/env python3
"""Owned in-app wallpaper previews on a few localized App guide pages (pilot).

Source: ``geo/data/app_image_gallery.json`` (one entry per App: the locales that
get a gallery, the image files under the Pages tree and the localized copy).
Every listed ``<locale>/<key>.html`` gets a managed ``app-image-gallery`` block
right after the hook clip (or the App Store QR card): the App's own wallpaper
pairs as lazy ``<img>`` tiles plus one App Store link carrying the gallery's own
campaign (``ct=<campaign>``) and, when the App is on Google Play, a Play link with
the same install referrer.  ``gen_image_sitemap.py`` lists the same images under
those pages in the existing ``sitemap_images.xml``.

Fail closed, block removed instead of published:
  * an image file is missing or empty in the Pages tree;
  * the copy says a price, "free" or "Pro" (``FORBIDDEN_RE``);
  * the page carries no App Store download CTA for the App (not live there);
  * the Google Play snapshot cannot be read (Android status unknown).

Called at the end of ``app_hook_clips.build`` so every pipeline step that
re-injects the hook clip after a page rebuild also re-injects the gallery.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import urllib.parse

from site_config import PUBLIC_SITE  # noqa: E402

HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
CONFIG_PATH = HERE / "data" / "app_image_gallery.json"
SCHEMA = "lumi.app-image-gallery/v1"
START = "<!-- app-image-gallery:start -->"
END = "<!-- app-image-gallery:end -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
AFTER_MARKERS = ("<!-- app-hook-clip:end -->", "<!-- app-store-qr:end -->")
CAMPAIGN_RE = re.compile(r"^[a-z0-9_]{1,40}$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:jpe?g|png|webp)$")
# Store-review truthfulness: no price, no "free", no "Pro" on images or their text.
FORBIDDEN_RE = re.compile(
    r"[$€£¥₩]|\bfree\b|\bpro\b|\bprice\b|gratis|kostenlos|preis|무료|가격|프로|免費|免费|價格",
    re.IGNORECASE,
)
STORE_HREF_RE = re.compile(r'href="(https://apps\.apple\.com/[^"]*?/id(\d{9,12})\?[^"]*)"')
CSS = (
    "margin:18px 0",
    "display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));"
    "gap:10px;margin:10px 0",
    "margin:0",
    "display:block;width:100%;height:auto;border-radius:12px;background:#111",
    "margin-top:4px;font-size:13px;color:#6b6257",
)


class GalleryError(ValueError):
    """The gallery data cannot be published as is."""


def load_config(path: Path = CONFIG_PATH) -> dict[str, dict]:
    if not Path(path).exists():
        return {}
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise GalleryError(f"unexpected gallery schema: {document.get('schema')!r}")
    apps = document.get("apps") or {}
    for key, app in apps.items():
        if not CAMPAIGN_RE.fullmatch(str(app.get("campaign", ""))):
            raise GalleryError(f"{key}: invalid campaign {app.get('campaign')!r}")
        if not re.fullmatch(r"\d{9,12}", str(app.get("app_id", ""))):
            raise GalleryError(f"{key}: invalid app_id")
        for locale in app.get("locales", []):
            copy = app.get("copy", {}).get(locale)
            if not copy:
                raise GalleryError(f"{key}: no copy for {locale}")
            texts = list(copy.values()) + [pair["name"].get(locale, "") for pair in app["pairs"]]
            for text in texts:
                if not text or FORBIDDEN_RE.search(text):
                    raise GalleryError(f"{key}/{locale}: empty or forbidden copy {text!r}")
        for pair in app.get("pairs", []):
            for side in ("cover", "inner"):
                if not FILE_RE.fullmatch(str(pair[side]["file"])) or FORBIDDEN_RE.search(pair[side]["file"]):
                    raise GalleryError(f"{key}: invalid image file {pair[side]['file']!r}")
    return apps


def _site_path(site: str = SITE) -> str:
    return urllib.parse.urlsplit(site).path.rstrip("/")


def image_records(app: dict, locale: str, pages: Path = PAGES, site: str = SITE) -> list[dict]:
    """The gallery images for one page; raises when any file is missing."""
    copy = app["copy"][locale]
    records = []
    for pair in app["pairs"]:
        for side in ("cover", "inner"):
            image = pair[side]
            relative = f"{app['asset_dir'].strip('/')}/{image['file']}"
            target = pages / relative
            if not target.is_file() or target.stat().st_size == 0:
                raise GalleryError(f"gallery image is missing or empty: {target}")
            records.append({
                "relative": relative,
                "url": f"{site}/{relative}",
                "src": f"{_site_path(site)}/{relative}",
                "alt": f"{pair['name'][locale]} – {copy[side]}",
                "width": int(image["width"]),
                "height": int(image["height"]),
            })
    return records


def store_url(source: str, app_id: str, campaign: str) -> str | None:
    """The page's own stamped App Store CTA for ``app_id`` with ``ct`` swapped to ``campaign``."""
    for match in STORE_HREF_RE.finditer(source):
        if match.group(2) != app_id:
            continue
        url = html.unescape(match.group(1))
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        names = [name for name, _ in query]
        if "action" in names or "ct" not in names:
            continue
        query = [(name, campaign if name == "ct" else value) for name, value in query]
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
    return None


def render_block(key: str, app: dict, locale: str, images: list[dict],
                 app_store: str, play: str | None) -> str:
    section, grid, figure, img, caption = CSS
    copy = app["copy"][locale]
    tiles = "".join(
        f'<figure style="{figure}"><img src="{html.escape(record["src"])}" '
        f'alt="{html.escape(record["alt"])}" width="{record["width"]}" '
        f'height="{record["height"]}" loading="lazy" decoding="async" style="{img}">'
        f'<figcaption style="{caption}">{html.escape(record["alt"])}</figcaption></figure>\n'
        for record in images
    )
    links = (
        f'<a class="cta" href="{html.escape(app_store)}" rel="noopener">'
        f"{html.escape(copy['app_store'])}</a>"
    )
    if play:
        links += (
            f' · <a class="android-play-gallery" href="{html.escape(play)}" rel="noopener">'
            f"{html.escape(copy['play'])}</a>"
        )
    return (
        f"{START}\n"
        f'<section class="app-image-gallery" data-app-key="{key}" '
        f'data-campaign="{app["campaign"]}" style="{section}">\n'
        f"<h2>{html.escape(copy['heading'])}</h2>\n"
        f"<p>{html.escape(copy['intro'])}</p>\n"
        f'<div style="{grid}">\n{tiles}</div>\n'
        f"<p>{links}</p>\n"
        f"</section>\n"
        f"{END}\n"
    )


def inject(source: str, block: str | None) -> str:
    cleaned = BLOCK_RE.sub("", source)
    if block is None:
        return cleaned
    for marker in AFTER_MARKERS:
        if marker in cleaned:
            anchor = cleaned.index(marker) + len(marker)
            if cleaned[anchor:anchor + 1] == "\n":
                anchor += 1
            return cleaned[:anchor] + block + cleaned[anchor:]
    return cleaned


def _play_url(key: str, campaign: str, android: dict[str, dict] | None) -> str | None:
    import android_play

    entry = (android or {}).get(key)
    if not entry:
        return None
    return android_play.tracked_play_url(entry["play_url"], campaign, key)


def _load_android() -> dict[str, dict] | None:
    import android_play

    try:
        return android_play.load_snapshot()
    except (OSError, ValueError):
        return None


def page_entries(pages: Path = PAGES, site: str = SITE,
                 config: dict[str, dict] | None = None) -> list[tuple[str, list[str]]]:
    """(page URL, image URLs) for every configured page that exists; for the image sitemap."""
    apps = load_config() if config is None else config
    entries = []
    for key, app in sorted(apps.items()):
        for locale in app["locales"]:
            if not (pages / locale / f"{key}.html").is_file():
                continue
            images = image_records(app, locale, pages, site)
            entries.append((f"{site}/{locale}/{key}.html", [record["url"] for record in images]))
    return entries


def build(pages: Path = PAGES, site: str = SITE, *,
          config: dict[str, dict] | None = None,
          android: dict[str, dict] | None = None) -> dict[str, int]:
    apps = load_config() if config is None else config
    android = _load_android() if android is None else android
    stats = {"pages": 0, "changed": 0, "removed": 0}
    wanted = {(locale, key) for key, app in apps.items() for locale in app["locales"]}
    for key, app in sorted(apps.items()):
        for locale in app["locales"]:
            page = pages / locale / f"{key}.html"
            if not page.is_file():
                continue
            source = page.read_text(encoding="utf-8")
            block = None
            app_store = store_url(source, app["app_id"], app["campaign"])
            if app_store is not None and android is not None:
                images = image_records(app, locale, pages, site)
                play = _play_url(key, app["campaign"], android)
                block = render_block(key, app, locale, images, app_store, play)
                stats["pages"] += 1
            updated = inject(source, block)
            if updated != source:
                page.write_text(updated, encoding="utf-8")
                stats["changed"] += 1
                stats["removed"] += block is None
    # A locale dropped from an App's list loses its block on the next pass (to
    # retire an App, keep its key with "locales": [] for one run).
    for key in sorted(apps):
        for page in sorted(pages.glob(f"*/{key}.html")):
            if (page.parent.name, key) in wanted:
                continue
            source = page.read_text(encoding="utf-8")
            if START in source:
                page.write_text(inject(source, None), encoding="utf-8")
                stats["changed"] += 1
                stats["removed"] += 1
    return stats


def main() -> None:
    stats = build()
    print("APP_IMAGE_GALLERY " + " ".join(f"{k}={v}" for k, v in stats.items()), flush=True)


if __name__ == "__main__":
    main()
