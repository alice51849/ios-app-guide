#!/usr/bin/env python3
"""Add Apple Smart App Banners to app guides and single-app buyer pages."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import urllib.parse


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from appstore_live import live_app_keys  # noqa: E402
import gen_linkset  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
BLOCK_START = "<!-- smart-app-banner:start -->"
BLOCK_END = "<!-- smart-app-banner:end -->"
FREE_RESOURCE_FIRST_META = (
    '<meta name="iag-free-resource-first" content="true">'
)
BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*",
    flags=re.DOTALL,
)
MOBILE_CTA_BLOCK_START = "<!-- mobile-store-cta:start -->"
MOBILE_CTA_BLOCK_END = "<!-- mobile-store-cta:end -->"
MOBILE_CTA_BLOCK_RE = re.compile(
    rf"\s*{re.escape(MOBILE_CTA_BLOCK_START)}.*?"
    rf"{re.escape(MOBILE_CTA_BLOCK_END)}\s*",
    flags=re.DOTALL,
)
APP_STORE_QR_BLOCK_START = "<!-- app-store-qr:start -->"
APP_STORE_QR_BLOCK_END = "<!-- app-store-qr:end -->"
APP_STORE_QR_STYLE_BLOCK_START = "<!-- app-store-qr-style:start -->"
APP_STORE_QR_STYLE_BLOCK_END = "<!-- app-store-qr-style:end -->"
APP_STORE_QR_BLOCK_RE = re.compile(
    rf"\s*{re.escape(APP_STORE_QR_BLOCK_START)}.*?"
    rf"{re.escape(APP_STORE_QR_BLOCK_END)}\s*",
    flags=re.DOTALL,
)
APP_STORE_SHARE_BLOCK_START = "<!-- app-store-share:start -->"
APP_STORE_SHARE_BLOCK_END = "<!-- app-store-share:end -->"
APP_STORE_SHARE_BLOCK_RE = re.compile(
    rf"\s*{re.escape(APP_STORE_SHARE_BLOCK_START)}.*?"
    rf"{re.escape(APP_STORE_SHARE_BLOCK_END)}\s*",
    flags=re.DOTALL,
)
APP_DECISION_CARD_BLOCK_RE = re.compile(
    r"\s*<!-- app-decision-card:start -->.*?"
    r"<!-- app-decision-card:end -->\s*",
    flags=re.DOTALL,
)
MOBILE_APP_IDENTITY_BLOCK_RE = re.compile(
    r'\s*<script\b(?=[^>]*\bdata-mobile-app-(?:identity|webpage)="1")'
    r"[^>]*>.*?</script>\s*",
    flags=re.IGNORECASE | re.DOTALL,
)
APP_STORE_LINK_RE = re.compile(
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/id(\d+)",
    flags=re.IGNORECASE,
)
APP_STORE_ANCHOR_RE = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*(?P<quote>[\"'])"
    r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/id(?P<id>\d+)"
    r"[^\"']*(?P=quote)",
    flags=re.IGNORECASE | re.DOTALL,
)
LOCALE_DIRECTORY_RE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?")
RESERVED_TOP_LEVEL_DIRS = {"api"}
BUYER_INTENT_SECTIONS = ("answers", "alternatives", "hubs")


def _app_id(store_url: str) -> str:
    parsed = urllib.parse.urlsplit(store_url)
    match = re.fullmatch(r"/app/id(\d+)", parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or not match
    ):
        raise ValueError(f"Invalid Smart App Banner App Store URL: {store_url}")
    return match.group(1)


def banner_block(app_id: str) -> str:
    if not re.fullmatch(r"\d+", app_id):
        raise ValueError(f"Invalid Smart App Banner app ID: {app_id}")
    return "\n".join(
        (
            BLOCK_START,
            f'<meta name="apple-itunes-app" content="app-id={app_id}">',
            BLOCK_END,
        )
    )


def _unmanaged_source(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    for pattern in (
        APP_DECISION_CARD_BLOCK_RE,
        MOBILE_APP_IDENTITY_BLOCK_RE,
        APP_STORE_SHARE_BLOCK_RE,
        APP_STORE_QR_BLOCK_RE,
        MOBILE_CTA_BLOCK_RE,
        BLOCK_RE,
    ):
        source = pattern.sub("\n", source)
    return source


def _add_single_app_targets(
    targets: dict[Path, str],
    paths: set[Path],
    live_ids: set[str],
) -> None:
    for path in paths:
        source = _unmanaged_source(path)
        if FREE_RESOURCE_FIRST_META in source:
            continue
        app_ids = {
            match.group("id") for match in APP_STORE_ANCHOR_RE.finditer(source)
        }
        if len(app_ids) != 1:
            continue
        app_id = next(iter(app_ids))
        if app_id not in live_ids:
            continue
        existing = targets.get(path)
        if existing and existing != app_id:
            raise ValueError(
                f"Conflicting buyer-intent app IDs for {path}: "
                f"{existing}, {app_id}"
            )
        targets[path] = app_id


def build_targets(
    pages: Path, live_keys: set[str], site: str = SITE
) -> tuple[dict[Path, str], int]:
    document, records = gen_linkset.build_document(pages, live_keys, site)
    contexts = document["linkset"][1:]
    if len(contexts) != len(records):
        raise ValueError("Smart App Banner Linkset context/record count mismatch")

    targets: dict[Path, str] = {}
    for context, record in zip(contexts, records):
        if context["anchor"] != record["guide"]:
            raise ValueError(
                f"Smart App Banner guide context mismatch for {record['key']}"
            )
        app_id = _app_id(record["store"])
        app_paths: set[Path] = set()
        for alternate in context["alternate"]:
            path = gen_linkset._owned_path(alternate["href"], pages, site)
            if path.name != f"{record['key']}.html" or path.parent.name != "guides":
                raise ValueError(
                    f"Unexpected Smart App Banner guide target: {path}"
                )
            existing = targets.get(path)
            if existing and existing != app_id:
                raise ValueError(
                    f"Conflicting Smart App Banner app IDs for {path}: "
                    f"{existing}, {app_id}"
                )
            targets[path] = app_id
            app_paths.add(path)
        if not app_paths:
            raise ValueError(
                f"Public app has no Smart App Banner guide pages: {record['key']}"
            )

    for path in _localized_app_pages(pages, live_keys):
        app_id = APPSTORE[path.stem]
        existing = targets.get(path)
        if existing and existing != app_id:
            raise ValueError(
                f"Conflicting Smart App Banner app IDs for {path}: "
                f"{existing}, {app_id}"
            )
        targets[path] = app_id

    _add_single_app_targets(
        targets,
        _answer_pages(pages),
        {APPSTORE[key] for key in live_keys},
    )
    return targets, len(records)


def build_install_targets(
    pages: Path, live_keys: set[str], site: str = SITE
) -> tuple[dict[Path, str], int]:
    targets, app_count = build_targets(pages, live_keys, site)
    _add_single_app_targets(
        targets,
        _alternative_pages(pages) | _hub_pages(pages),
        {APPSTORE[key] for key in live_keys},
    )
    return targets, app_count


def ensure_banner(path: Path, app_id: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Smart App Banner guide has no closing head: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    if FREE_RESOURCE_FIRST_META in cleaned:
        return _write_if_changed(path, cleaned)
    linkset_match = gen_linkset.DISCOVERY_RE.search(cleaned)
    social_index = cleaned.find("<!-- social-preview:start -->")
    feed_match = gen_linkset.FEED_DISCOVERY_RE.search(cleaned)
    identity_match = MOBILE_APP_IDENTITY_BLOCK_RE.search(cleaned)
    head_indices = [
        index
        for index in (
            linkset_match.start() if linkset_match else -1,
            social_index,
            feed_match.start() if feed_match else -1,
            identity_match.start() if identity_match else -1,
            cleaned.find(APP_STORE_QR_STYLE_BLOCK_START),
            cleaned.index("</head>"),
        )
        if index >= 0
    ]
    insert_index = min(head_indices)
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + banner_block(app_id)
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def _localized_app_pages(pages: Path, app_keys: set[str]) -> set[Path]:
    paths: set[Path] = set()
    for child in pages.iterdir():
        if (
            not child.is_dir()
            or child.name in RESERVED_TOP_LEVEL_DIRS
            or not LOCALE_DIRECTORY_RE.fullmatch(child.name)
        ):
            continue
        for key in app_keys:
            path = child / f"{key}.html"
            if path.is_file():
                paths.add(path.resolve())
    return paths


def _guide_pages(pages: Path) -> set[Path]:
    paths = {path.resolve() for path in (pages / "guides").glob("*.html")}
    for child in pages.iterdir():
        if child.name == "_engine" or not child.is_dir():
            continue
        guides = child / "guides"
        if guides.is_dir():
            paths.update(path.resolve() for path in guides.glob("*.html"))
    paths.update(_localized_app_pages(pages, set(APPSTORE)))
    return paths


def _section_pages(pages: Path, section: str) -> set[Path]:
    if section not in BUYER_INTENT_SECTIONS:
        raise ValueError(f"Unsupported buyer-intent section: {section}")
    paths = {
        path.resolve()
        for path in (pages / section).glob("*.html")
        if path.name != "index.html"
    }
    for child in pages.iterdir():
        if child.name == "_engine" or not child.is_dir():
            continue
        localized_section = child / section
        if localized_section.is_dir():
            paths.update(
                path.resolve()
                for path in localized_section.glob("*.html")
                if path.name != "index.html"
            )
    return paths


def _answer_pages(pages: Path) -> set[Path]:
    return _section_pages(pages, "answers")


def _alternative_pages(pages: Path) -> set[Path]:
    return _section_pages(pages, "alternatives")


def _hub_pages(pages: Path) -> set[Path]:
    return _section_pages(pages, "hubs")


def _buyer_intent_pages(pages: Path) -> set[Path]:
    pages_by_section = (
        _section_pages(pages, section) for section in BUYER_INTENT_SECTIONS
    )
    return set().union(*pages_by_section)


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _page_language(path: Path, pages: Path) -> str:
    pages_root = pages.resolve()
    if path.parent.name in {"guides", *BUYER_INTENT_SECTIONS}:
        container = path.parent.parent
        return "en" if container == pages_root else container.name
    return path.parent.name


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = build_install_targets(pages, set(live_keys), site)
    guide_pages = _guide_pages(pages)
    answer_pages = _answer_pages(pages)
    buyer_intent_pages = _buyer_intent_pages(pages)
    changed = 0
    for path in sorted(targets):
        changed += int(ensure_banner(path, targets[path]))

    for path in sorted((guide_pages | buyer_intent_pages) - set(targets)):
        source = path.read_text(encoding="utf-8")
        if BLOCK_RE.search(source):
            changed += int(_write_if_changed(path, BLOCK_RE.sub("\n", source)))

    languages = {_page_language(path, pages) for path in targets}
    return {
        "apps": app_count,
        "guide_pages": len(set(targets) & guide_pages),
        "answer_pages": len(set(targets) & answer_pages),
        "buyer_intent_pages": len(set(targets) & buyer_intent_pages),
        "languages": len(languages),
        "changed_files": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=Path, default=PAGES, help="Alternate Pages checkout."
    )
    args = parser.parse_args()
    result = generate(args.pages)
    print(
        "Apple Smart App Banners: "
        f"{result['apps']} apps, {result['guide_pages']} guide pages, "
        f"{result['buyer_intent_pages']} single-app buyer-intent pages, "
        f"{result['languages']} languages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
