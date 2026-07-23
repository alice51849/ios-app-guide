#!/usr/bin/env python3
"""Quarantine static App Store pages whose app is not in the live catalogue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


APP_ID_RE = re.compile(r"(?:app-id=|/id)(\d{8,})", re.IGNORECASE)
ROBOTS_RE = re.compile(
    r'<meta\s+name=["\']robots["\'][^>]*>',
    re.IGNORECASE,
)
SMART_BANNER_RE = re.compile(
    r'<meta\s+name=["\']apple-itunes-app["\'][^>]*>',
    re.IGNORECASE,
)
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
APP_STORE_ANCHOR_RE = re.compile(
    r'<a\b(?=[^>]*\bhref=["\'][^"\']*apps\.apple\.com[^"\']*["\'])'
    r"[^>]*>.*?</a>",
    re.IGNORECASE | re.DOTALL,
)


def _live_app_ids(site_root: Path) -> set[str]:
    catalogue_path = site_root / "apps.json"
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    if isinstance(catalogue, dict):
        records = catalogue.values()
    elif isinstance(catalogue, list):
        records = catalogue
    else:
        raise RuntimeError(f"Unsupported live catalogue: {catalogue_path}")
    live_ids = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        for value in record.values():
            if not isinstance(value, str):
                continue
            live_ids.update(APP_ID_RE.findall(value))
    if not live_ids:
        raise RuntimeError(f"Live catalogue contains no App Store IDs: {catalogue_path}")
    return live_ids


def _sanitize_html(source: str, app_ids: set[str]) -> str:
    replacement = '<meta name="robots" content="noindex,nofollow">'
    if ROBOTS_RE.search(source):
        source = ROBOTS_RE.sub(replacement, source, count=1)
    elif "<head>" in source:
        source = source.replace("<head>", f"<head>{replacement}", 1)
    else:
        raise RuntimeError("Static app page has no <head>")
    source = SMART_BANNER_RE.sub("", source)

    def remove_app_schema(match: re.Match[str]) -> str:
        block = match.group(0)
        if (
            "SoftwareApplication" in block
            or "MobileApplication" in block
            or "InstallAction" in block
            or any(app_id in block for app_id in app_ids)
        ):
            return ""
        return block

    source = JSON_LD_RE.sub(remove_app_schema, source)
    source = APP_STORE_ANCHOR_RE.sub("", source)
    for app_id in app_ids:
        source = re.sub(
            rf"https://apps\.apple\.com/[^\"'<\s]*id{re.escape(app_id)}[^\"'<\s]*",
            "",
            source,
            flags=re.IGNORECASE,
        )
    return re.sub(r"[ \t]+\n", "\n", source)


def _remove_sitemap_urls(source: str, app_slugs: set[str]) -> str:
    markers = tuple(f"/apps/{slug}/" for slug in app_slugs)
    for tag in ("url", "sitemap"):
        block_re = re.compile(
            rf"<{tag}>.*?</{tag}>",
            re.IGNORECASE | re.DOTALL,
        )
        source = block_re.sub(
            lambda match: (
                ""
                if any(marker in match.group(0) for marker in markers)
                else match.group(0)
            ),
            source,
        )
    return source


def quarantine_nonlive_pages(site_root: Path, *, apply: bool) -> dict[str, int]:
    site_root = site_root.resolve()
    apps_root = site_root / "apps"
    live_ids = _live_app_ids(site_root)
    quarantined: dict[str, set[str]] = {}
    html_changes: dict[Path, str] = {}
    for app_root in sorted(path for path in apps_root.iterdir() if path.is_dir()):
        pages = sorted(app_root.rglob("*.html"))
        if not pages:
            continue
        primary = app_root / "index.html"
        if not primary.is_file():
            primary = pages[0]
        app_ids = set(
            APP_ID_RE.findall(primary.read_text(encoding="utf-8"))
        )
        if not app_ids or app_ids & live_ids:
            continue
        quarantined[app_root.name] = app_ids
        for page in pages:
            source = page.read_text(encoding="utf-8")
            sanitized = _sanitize_html(source, app_ids)
            if sanitized != source:
                html_changes[page] = sanitized

    sitemap_changes: dict[Path, str] = {}
    slugs = set(quarantined)
    if slugs:
        for sitemap in site_root.rglob("*sitemap*.xml"):
            source = sitemap.read_text(encoding="utf-8")
            sanitized = _remove_sitemap_urls(source, slugs)
            if sanitized != source:
                sitemap_changes[sitemap] = sanitized

    if apply:
        for path, content in {**html_changes, **sitemap_changes}.items():
            path.write_text(content, encoding="utf-8")
    return {
        "apps": len(quarantined),
        "html": len(html_changes),
        "sitemaps": len(sitemap_changes),
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
