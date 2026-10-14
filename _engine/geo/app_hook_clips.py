#!/usr/bin/env python3
"""Embed each App's 7-second hook clip on its localized App guide pages.

Source: ``.github/growth/clips.json`` in the Pages tree (planned by
shorts/scripts/schedule_posts.py; one MP4 per App and clip locale).  Every
official-locale App page ``<locale>/<key>.html`` gets the clip in its own
language when one exists, otherwise the English clip, as a lightweight
``<video preload="none">`` plus a schema.org ``VideoObject``.  Pages that are
``noindex`` or canonicalise elsewhere still get the player but stay out of the
video sitemap.

Outputs (all idempotent):

* a managed ``app-hook-clip`` block in each App page;
* ``data/app-hook-clips.json`` — public manifest that also pins each clip
  URL's first-seen date, so ``uploadDate`` never drifts between runs;
* ``sitemap_hook_clips.xml`` — Google video sitemap, registered in
  ``sitemap_index.xml`` and ``llms.txt`` by gen_llms.py.

Posters: ``assets/hook-clips/<clip id>.jpg`` (first frame, made by
``--posters`` where curl + ffmpeg are available); until a poster exists the App's
share image is used, which is the same thumbnail the walkthrough videos use.

Runs after live_app_guard.py (final noindex state) in publish.py and
geo-daily, before close_sitemap_graph.py / gen_llms.py.
"""

from __future__ import annotations

import argparse
from datetime import date
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE  # noqa: E402

HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
CLIPS_RELATIVE = Path(".github") / "growth" / "clips.json"
MANIFEST_RELATIVE = Path("data") / "app-hook-clips.json"
POSTER_RELATIVE = Path("assets") / "hook-clips"
SITEMAP_NAME = "sitemap_hook_clips.xml"
DURATION_SECONDS = 7
START = "<!-- app-hook-clip:start -->"
END = "<!-- app-hook-clip:end -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
QR_END = "<!-- app-store-qr:end -->"
CLIP_URL_RE = re.compile(r"https://files\.catbox\.moe/([a-z0-9]+)\.mp4")
KEY_RE = re.compile(r"[a-z0-9]+")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
VIDEO_NS = "http://www.google.com/schemas/sitemap-video/1.1"
CSS = (
    "margin:18px 0;max-width:300px",
    "display:block;width:100%;aspect-ratio:9/16;border-radius:18px;"
    "background:#111;object-fit:contain",
    "margin-top:6px;font-size:14px;color:#6b6257",
)


def _base(locale: str) -> str:
    return {"nb": "no"}.get(locale.split("-")[0], locale.split("-")[0])


def clip_for_locale(clips: dict[str, dict], locale: str) -> dict | None:
    """Exact locale, then same language without region, then English."""
    if locale in clips:
        return clips[locale]
    if not locale.startswith("zh"):
        for clip_locale, clip in sorted(clips.items()):
            if "-" not in clip_locale and _base(clip_locale) == _base(locale):
                return clip
    return clips.get("en")


def load_clips(pages: Path) -> dict[str, dict[str, dict]]:
    path = pages / CLIPS_RELATIVE
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_app: dict[str, dict[str, dict]] = {}
    for clip in (payload.get("clips") or {}).values():
        app, locale, url = clip.get("app"), clip.get("locale"), clip.get("url")
        if not (isinstance(app, str) and KEY_RE.fullmatch(app)):
            continue
        if not (isinstance(url, str) and CLIP_URL_RE.fullmatch(url)):
            continue
        hook = " ".join(str(clip.get("hook") or "").split())
        name = " ".join(str(clip.get("name") or "").split())
        if not hook or not name or not isinstance(locale, str):
            continue
        by_app.setdefault(app, {})[locale] = {
            "locale": locale, "url": url, "hook": hook, "name": name,
        }
    return by_app


def _meta(source: str, attr: str, value: str) -> str | None:
    match = re.search(
        rf'<meta {attr}="{re.escape(value)}" content="([^"]*)"', source
    )
    return html.unescape(match.group(1)) if match else None


def _indexable(source: str, page_url: str) -> bool:
    robots = _meta(source, "name", "robots") or ""
    if "noindex" in robots.lower():
        return False
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', source)
    return not canonical or html.unescape(canonical.group(1)) == page_url


def poster_url(pages: Path, clip: dict, fallback: str | None) -> str | None:
    clip_id = CLIP_URL_RE.fullmatch(clip["url"]).group(1)
    if (pages / POSTER_RELATIVE / f"{clip_id}.jpg").is_file():
        return f"{SITE}/{POSTER_RELATIVE.as_posix()}/{clip_id}.jpg"
    return fallback


def make_posters(pages: Path, by_app: dict[str, dict[str, dict]]) -> int:
    """Grab the first frame of every clip that has no poster yet (ffmpeg)."""
    if not (shutil.which("ffmpeg") and shutil.which("curl")):
        print("app_hook_clips: ffmpeg/curl missing, posters skipped")
        return 0
    out_dir = pages / POSTER_RELATIVE
    out_dir.mkdir(parents=True, exist_ok=True)
    made = 0
    for clips in by_app.values():
        for clip in clips.values():
            clip_id = CLIP_URL_RE.fullmatch(clip["url"]).group(1)
            target = out_dir / f"{clip_id}.jpg"
            if target.is_file():
                continue
            with tempfile.TemporaryDirectory() as tmp:
                local = Path(tmp) / "clip.mp4"
                fetched = subprocess.run(
                    ["curl", "-sSLf", "--retry", "3", "--max-time", "90",
                     "-o", str(local), clip["url"]],
                    capture_output=True, text=True, timeout=120,
                )
                result = subprocess.run(
                    ["ffmpeg", "-v", "error", "-y", "-i", str(local),
                     "-frames:v", "1", "-vf", "scale=405:-2", "-q:v", "6",
                     str(target)],
                    capture_output=True, text=True, timeout=120,
                ) if fetched.returncode == 0 else fetched
            if result.returncode == 0 and target.is_file():
                made += 1
            else:
                target.unlink(missing_ok=True)
                print(f"app_hook_clips: poster failed for {clip['url']}")
    return made


def _json_ld(payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def render_block(record: dict) -> str:
    figure, video, caption = CSS
    lang = (
        f' lang="{html.escape(record["clip_locale"])}"'
        if record["clip_locale"] != record["page_locale"] else ""
    )
    poster = (
        f' poster="{html.escape(record["thumbnail_url"])}"'
        if record["thumbnail_url"] else ""
    )
    data = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": record["title"],
        "description": record["description"],
        "thumbnailUrl": [record["thumbnail_url"]],
        "uploadDate": record["upload_date"] + "T00:00:00+00:00",
        "contentUrl": record["clip_url"],
        "duration": f"PT{DURATION_SECONDS}S",
        "inLanguage": record["clip_locale"],
    }
    return (
        f"{START}\n"
        f'<figure class="app-hook-clip" data-app-key="{record["app_key"]}"'
        f'{lang} style="{figure}">\n'
        f'<video controls playsinline muted loop preload="none"{poster} '
        f'width="1080" height="1920" style="{video}" '
        f'aria-label="{html.escape(record["title"])}">'
        f'<source src="{html.escape(record["clip_url"])}" type="video/mp4">'
        f"</video>\n"
        f'<figcaption style="{caption}">{html.escape(record["hook"])}</figcaption>\n'
        f"</figure>\n"
        f'<script type="application/ld+json">{_json_ld(data)}</script>\n'
        f"{END}\n"
    )


def inject(source: str, block: str | None) -> str:
    cleaned = BLOCK_RE.sub("", source)
    if block is None:
        return cleaned
    if QR_END in cleaned:
        anchor = cleaned.index(QR_END) + len(QR_END)
        if cleaned[anchor:anchor + 1] == "\n":
            anchor += 1
        return cleaned[:anchor] + block + cleaned[anchor:]
    main = cleaned.find("<main")
    heading = cleaned.find("<h2", main) if main >= 0 else -1
    if heading < 0:
        return cleaned
    return cleaned[:heading] + block + cleaned[heading:]


def load_upload_dates(pages: Path) -> dict[str, str]:
    path = pages / MANIFEST_RELATIVE
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(clip["url"]): str(clip["upload_date"])
        for clip in payload.get("clips", [])
        if clip.get("url") and clip.get("upload_date")
    }


def render_sitemap(records: list[dict]) -> str:
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("video", VIDEO_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for record in records:
        if not record["indexable"] or not record["thumbnail_url"]:
            continue
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = record["page_url"]
        video = ET.SubElement(url, f"{{{VIDEO_NS}}}video")
        for tag, value in (
            ("thumbnail_loc", record["thumbnail_url"]),
            ("title", record["title"]),
            ("description", record["description"]),
            ("content_loc", record["clip_url"]),
            ("duration", str(DURATION_SECONDS)),
            ("publication_date", record["upload_date"] + "T00:00:00+00:00"),
            ("family_friendly", "yes"),
        ):
            ET.SubElement(video, f"{{{VIDEO_NS}}}{tag}").text = value
        uploader = ET.SubElement(video, f"{{{VIDEO_NS}}}uploader", {"info": SITE})
        uploader.text = "Lumi Studio"
        ET.SubElement(video, f"{{{VIDEO_NS}}}live").text = "no"
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def _write(path: Path, text: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build(pages: Path = PAGES, *, today: str | None = None,
          posters: bool = False) -> list[dict]:
    today = today or date.today().isoformat()
    by_app = load_clips(pages)
    if posters:
        make_posters(pages, by_app)
    dates = load_upload_dates(pages)
    records: list[dict] = []
    changed = 0
    keys = set(by_app)
    for locale in OFFICIAL_LOCALES:
        locale_dir = pages / locale
        if not locale_dir.is_dir():
            continue
        for page in sorted(locale_dir.glob("*.html")):
            key = page.stem
            source = page.read_text(encoding="utf-8")
            if key not in keys:
                if START in source:
                    changed += _write(page, inject(source, None))
                continue
            clip = clip_for_locale(by_app[key], locale)
            if clip is None:
                changed += _write(page, inject(source, None))
                continue
            page_url = f"{SITE}/{locale}/{key}.html"
            share = _meta(source, "property", "og:image")
            dates.setdefault(clip["url"], today)
            record = {
                "app_key": key,
                "page_locale": locale,
                "page_url": page_url,
                "clip_locale": clip["locale"],
                "clip_url": clip["url"],
                "hook": clip["hook"],
                "title": f"{clip['hook']} | {clip['name']}",
                "description": (
                    _meta(source, "name", "description") or clip["hook"]
                ),
                "thumbnail_url": poster_url(pages, clip, share),
                "upload_date": dates[clip["url"]],
                "indexable": _indexable(source, page_url),
            }
            records.append(record)
            changed += _write(page, inject(source, render_block(record)))
    used = {record["clip_url"] for record in records}
    manifest = {
        "name": "Lumi Studio App hook clips",
        "description": (
            "7-second App Store hook clips embedded on the localized App "
            "guide pages; uploadDate is the first day each clip URL was seen."
        ),
        "video_sitemap": f"{SITE}/{SITEMAP_NAME}",
        "clip_count": len(used),
        "app_count": len({record["app_key"] for record in records}),
        "page_count": len(records),
        "clips": [
            {
                "app_key": clip_app,
                "locale": clip["locale"],
                "url": clip["url"],
                "upload_date": dates[clip["url"]],
            }
            for clip_app, clips in sorted(by_app.items())
            for clip in sorted(clips.values(), key=lambda c: c["locale"])
            if clip["url"] in used
        ],
    }
    _write(
        pages / MANIFEST_RELATIVE,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    _write(pages / SITEMAP_NAME, render_sitemap(records))
    indexed = sum(1 for r in records if r["indexable"] and r["thumbnail_url"])
    print(
        f"APP_HOOK_CLIPS apps={manifest['app_count']} clips={len(used)} "
        f"pages={len(records)} sitemap={indexed} changed={changed}",
        flush=True,
    )
    return records


def llms_lines(*, full: bool) -> list[str]:
    path = PAGES / MANIFEST_RELATIVE
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        "",
        "## App hook clips (7-second previews)",
        f"- Video sitemap: {SITE}/{SITEMAP_NAME}",
        f"- Manifest: {SITE}/{MANIFEST_RELATIVE.as_posix()}",
        f"- Coverage: {payload['clip_count']} clips for {payload['app_count']} "
        f"apps, embedded on {payload['page_count']} localized App pages "
        "(own-language clip where one exists, else English)",
    ]
    if full:
        lines.append(
            "- Each App page carries a schema.org VideoObject with contentUrl, "
            "thumbnailUrl, uploadDate and duration PT7S"
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--today", help="Stable build date (YYYY-MM-DD).")
    parser.add_argument(
        "--posters", action="store_true",
        help="Extract missing first-frame posters with ffmpeg (network).",
    )
    args = parser.parse_args()
    build(args.pages.resolve(), today=args.today, posters=args.posters)


if __name__ == "__main__":
    main()
