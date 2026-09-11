#!/usr/bin/env python3
"""Remove non-live store promotions without retiring verified live apps."""

from __future__ import annotations

import argparse
from functools import lru_cache
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from app_store_storefronts import APP_STORE_PATH_RE


APP_ID_RE = re.compile(r"(?:app-id=|/id)(\d{8,})", re.IGNORECASE)
ROBOTS_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*>',
    re.IGNORECASE,
)
SMART_BANNER_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']apple-itunes-app["\'])[^>]*>',
    re.IGNORECASE,
)
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
JSON_SCRIPT_RE = re.compile(
    r'<script\b[^>]*type=["\']application/(?:ld\+)?json["\'][^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
APP_IDENTITY_META_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']application-id["\'])[^>]*>',
    re.IGNORECASE,
)
APP_ID_LABEL_RE = re.compile(
    r'<(?P<tag>p|span)\b[^>]*>\s*App ID\s+\d+\s*</(?P=tag)>',
    re.IGNORECASE,
)
APP_STORE_ANCHOR_RE = re.compile(
    r'<a\b(?=[^>]*\bhref=["\'][^"\']*apps\.apple\.com[^"\']*["\'])'
    r"[^>]*>.*?</a>",
    re.IGNORECASE | re.DOTALL,
)
STORE_URL_RE = re.compile(
    r'(?:https?://|itms-apps://|//|https?:\\/\\/|itms-apps:\\/\\/)'
    r'apps\.apple\.com[^\s"\'<>]*',
    re.IGNORECASE,
)
STORE_ACTION_RE = re.compile(
    r'<(?P<tag>button|a)\b(?=[^>]*\bdata-app-store-url=)[^>]*>'
    r'.*?</(?P=tag)>',
    re.IGNORECASE | re.DOTALL,
)
STORE_ID_ATTRIBUTE_RE = re.compile(
    r'\s+data-app(?:-store)?-id=["\'][^"\']*["\']',
    re.IGNORECASE,
)
HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
QUARANTINE_META = '<meta name="iag-nonlive" content="true">'
EXCLUDED_PARTS = {".git", "_engine", "node_modules", "__pycache__"}


def live_apps() -> dict[str, str]:
    from live_app_manifest import load_manifest, require_public_inventory

    manifest = require_public_inventory(load_manifest())
    apps = {
        key: app["app_id"]
        for key, app in manifest["apps"].items()
    }
    if not apps:
        raise RuntimeError("Verified live inventory contains no eligible App Store IDs")
    return apps


@lru_cache(maxsize=8192)
def _url_app_id(url: str) -> str | None:
    parsed = urlsplit(url)
    match = APP_STORE_PATH_RE.fullmatch(parsed.path)
    return match["app_id"] if parsed.hostname == "apps.apple.com" and match else None


def _store_ids(source: str) -> set[str]:
    urls = (
        match.group().replace("\\/", "/")
        for match in STORE_URL_RE.finditer(html.unescape(source))
    )
    ids = set()
    for url in urls:
        app_id = _url_app_id(url.split("?", 1)[0].split("#", 1)[0])
        if app_id:
            ids.add(app_id)
    for banner in SMART_BANNER_RE.finditer(source):
        ids.update(APP_ID_RE.findall(banner.group()))
    return ids


def _contains_ids(source: str, app_ids: set[str]) -> bool:
    return any(re.search(rf"(?<!\d){re.escape(app_id)}(?!\d)", source) for app_id in app_ids)


def _primary_app_ids(source: str) -> set[str]:
    banners = {
        app_id
        for banner in SMART_BANNER_RE.finditer(source)
        for app_id in APP_ID_RE.findall(banner.group())
    }
    if banners:
        return banners
    owners = set()
    for match in JSON_LD_RE.finditer(source):
        block = match.group(0)
        try:
            payload = json.loads(block[block.index(">") + 1:block.rfind("</")])
        except ValueError:
            continue
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            if not isinstance(record, dict):
                continue
            if record.get("@type") in ("SoftwareApplication", "MobileApplication"):
                owners.update(_store_ids(json.dumps(record)))
            elif record.get("@type") == "Review":
                owners.update(_store_ids(json.dumps(record.get("itemReviewed", {}))))
    return owners


def _sanitize_html(source: str, app_ids: set[str]) -> str:
    """Keep the legacy archive representation accepted by static-site validators."""
    replacement = '<meta name="robots" content="noindex,nofollow">'
    if ROBOTS_RE.search(source):
        source = ROBOTS_RE.sub(replacement, source, count=1)
    elif "<head>" in source:
        source = source.replace("<head>", f"<head>{replacement}", 1)
    else:
        raise RuntimeError("Static app page has no <head>")
    source = SMART_BANNER_RE.sub("", source)
    source = JSON_LD_RE.sub(
        lambda match: "" if any(
            marker in match.group()
            for marker in ("SoftwareApplication", "MobileApplication", "InstallAction", *app_ids)
        ) else match.group(),
        source,
    )
    source = APP_STORE_ANCHOR_RE.sub("", source)
    for app_id in app_ids:
        source = re.sub(
            rf"https://apps\.apple\.com/[^\"'<\s]*id{re.escape(app_id)}[^\"'<\s]*",
            "", source, flags=re.IGNORECASE,
        )
    return re.sub(r"[ \t]+\n", "\n", source)


def _sanitize_promotions(source: str, app_ids: set[str], *, quarantine: bool) -> str:
    removed = object()

    def blocked(fragment: str) -> bool:
        return _contains_ids(fragment, app_ids)

    def prune(value):
        if isinstance(value, dict):
            if any(
                isinstance(item, (str, int)) and blocked(str(item))
                for item in value.values()
            ) or (
                quarantine
                and value.get("@type") in ("SoftwareApplication", "MobileApplication", "InstallAction")
            ):
                return removed
            result = {}
            for key, item in value.items():
                kept = prune(item)
                if kept is not removed:
                    result[key] = kept
            items = result.get("itemListElement")
            if isinstance(items, list) and items != value.get("itemListElement"):
                for position, item in enumerate(items, 1):
                    if isinstance(item, dict) and "position" in item:
                        item["position"] = position
                if "numberOfItems" in result:
                    result["numberOfItems"] = len(items)
            return result
        if isinstance(value, list):
            return [kept for item in value if (kept := prune(item)) is not removed]
        return value

    def remove_app_schema(match: re.Match[str]) -> str:
        block = match.group()
        if not blocked(block) and not (
            quarantine and any(kind in block for kind in (
                "SoftwareApplication", "MobileApplication", "InstallAction",
            ))
        ):
            return block
        start, end = block.index(">") + 1, block.rfind("</")
        payload = json.loads(block[start:end])
        kept = prune(payload)
        if kept is removed or not kept:
            return ""
        if kept != payload:
            return block[:start] + json.dumps(kept, ensure_ascii=False, separators=(",", ":")) + block[end:]
        return block

    source = JSON_SCRIPT_RE.sub(remove_app_schema, source)
    for pattern in (
        SMART_BANNER_RE, APP_IDENTITY_META_RE, APP_ID_LABEL_RE,
        APP_STORE_ANCHOR_RE, STORE_ACTION_RE, STORE_ID_ATTRIBUTE_RE,
    ):
        source = pattern.sub(
            lambda match: "" if quarantine or blocked(match.group()) else match.group(),
            source,
        )
    source = STORE_URL_RE.sub(
        lambda match: "" if quarantine or blocked(match.group()) else match.group(),
        source,
    )
    if blocked(source):
        raise RuntimeError("Unresolved non-live App Store ID in generated HTML")
    if quarantine:
        if not HEAD_RE.search(source):
            raise RuntimeError("Static app page has no <head>")
        source = ROBOTS_RE.sub("", source).replace(QUARANTINE_META, "")
        source = HEAD_RE.sub(
            lambda match: match.group() + QUARANTINE_META
            + '<meta name="robots" content="noindex,nofollow">',
            source,
            count=1,
        )
    return re.sub(r"[ \t]+\n", "\n", source)


def sanitize_nonlive_html(source: str, live_ids: set[str], *, quarantine: bool = False) -> str:
    ids = _store_ids(source)
    blocked = ids - live_ids
    marked = QUARANTINE_META in source
    if not blocked and not marked and not quarantine:
        return source
    primary = _primary_app_ids(source)
    quarantine = (
        quarantine or marked or not ids & live_ids
        or bool(primary and not primary & live_ids)
    )
    return _sanitize_promotions(source, blocked, quarantine=quarantine)


def _public_files(site_root: Path):
    for directory, dirs, files in os.walk(site_root, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if name not in EXCLUDED_PARTS
            and (not name.startswith(".") or name == ".well-known")
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(directory) / name
            if not name.startswith(".") and not path.is_symlink():
                yield path


def _remove_sitemap_urls(source: str, paths: set[str], *, public_paths: set[str]) -> str:
    targets = {"/" + path for path in paths}
    targets.update(path[:-10] for path in tuple(targets) if path.endswith("/index.html"))

    def quarantined(url: str) -> bool:
        path = unquote(urlsplit(html.unescape(url.strip())).path)
        for index, char in enumerate(path):
            if char == "/" and (candidate := path[index:]) in public_paths:
                return candidate in targets
        return False

    def prune_url(match: re.Match[str]) -> str:
        block = match.group()
        location = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.IGNORECASE | re.DOTALL)
        if location and quarantined(location.group(1)):
            return ""
        return re.sub(
            r'<xhtml:link\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*/?>',
            lambda link: "" if quarantined(link.group(1)) else link.group(),
            block,
            flags=re.IGNORECASE,
        )

    updated = re.sub(r"<url\b[^>]*>.*?</url>", prune_url, source, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"(?m)^[ \t]+$", "", updated) if updated != source else source


def quarantine_nonlive_pages(
    site_root: Path, *, apply: bool, live_ids: set[str] | None = None,
) -> dict[str, int]:
    site_root = site_root.resolve()
    if not site_root.is_dir():
        raise RuntimeError(f"Missing generated pages directory: {site_root}")
    if live_ids is None:
        live_ids = set(live_apps().values())
    if not live_ids:
        raise RuntimeError("Refusing cleanup with an empty verified live inventory")
    files = list(_public_files(site_root))
    app_roots = {}
    for primary in sorted((site_root / "apps").glob("*/index.html")):
        if primary.is_symlink() or primary.parent.is_symlink():
            continue
        source = primary.read_text(encoding="utf-8")
        ids = _primary_app_ids(source) or _store_ids(source)
        if QUARANTINE_META in source or ids and not ids & live_ids:
            app_roots[primary.parent] = ids

    blocked_ids: set[str] = set()
    quarantined: set[str] = set()
    html_changes: dict[Path, str] = {}
    for page in files:
        if page.suffix.lower() not in {".html", ".htm", ".xhtml"}:
            continue
        source = page.read_text(encoding="utf-8")
        blocked_ids.update(_store_ids(source) - live_ids)
        try:
            sanitized = sanitize_nonlive_html(
                source, live_ids, quarantine=any(root in page.parents for root in app_roots),
            )
        except (ValueError, RuntimeError) as error:
            raise RuntimeError(f"{page.relative_to(site_root)}: {error}") from error
        if QUARANTINE_META in sanitized:
            quarantined.add(page.relative_to(site_root).as_posix())
        if sanitized != source:
            html_changes[page] = sanitized

    sitemap_changes: dict[Path, str] = {}
    if quarantined:
        public_paths = {"/" + path.relative_to(site_root).as_posix() for path in files}
        public_paths.update(path[:-10] for path in tuple(public_paths) if path.endswith("/index.html"))
        for sitemap in files:
            if "sitemap" not in sitemap.name or sitemap.suffix != ".xml":
                continue
            source = sitemap.read_text(encoding="utf-8")
            sanitized = _remove_sitemap_urls(source, quarantined, public_paths=public_paths)
            if sanitized != source:
                sitemap_changes[sitemap] = sanitized

    if apply:
        for path, content in {**html_changes, **sitemap_changes}.items():
            path.write_text(content, encoding="utf-8")
    return {
        "apps": len(blocked_ids),
        "html": len(html_changes),
        "sitemaps": len(sitemap_changes),
        "quarantined_pages": len(quarantined),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = quarantine_nonlive_pages(args.site_root, apply=not args.check)
    print(
        "Non-live app guard: "
        f"{result['apps']} apps, {result['html']} HTML, "
        f"{result['sitemaps']} sitemaps"
    )
    if args.check and (result["html"] or result["sitemaps"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
