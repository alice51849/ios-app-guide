#!/usr/bin/env python3
"""Add Apple Smart App Banners to public app guides and buyer-intent answers."""

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


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
BLOCK_START = "<!-- smart-app-banner:start -->"
BLOCK_END = "<!-- smart-app-banner:end -->"
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
APP_STORE_LINK_RE = re.compile(
    r"https://apps\.apple\.com/app/id(\d+)",
    flags=re.IGNORECASE,
)


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

    live_ids = {APPSTORE[key] for key in live_keys}
    for path in _answer_pages(pages):
        source = APP_STORE_SHARE_BLOCK_RE.sub(
            "\n",
            APP_STORE_QR_BLOCK_RE.sub(
                "\n",
                MOBILE_CTA_BLOCK_RE.sub(
                    "\n", BLOCK_RE.sub("\n", path.read_text(encoding="utf-8"))
                ),
            ),
        )
        app_ids = set(APP_STORE_LINK_RE.findall(source))
        if len(app_ids) != 1:
            continue
        app_id = next(iter(app_ids))
        if app_id in live_ids:
            targets[path] = app_id
    return targets, len(records)


def ensure_banner(path: Path, app_id: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source:
        raise ValueError(f"Smart App Banner guide has no closing head: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    linkset_match = gen_linkset.DISCOVERY_RE.search(cleaned)
    social_index = cleaned.find("<!-- social-preview:start -->")
    feed_match = gen_linkset.FEED_DISCOVERY_RE.search(cleaned)
    insert_index = (
        linkset_match.start()
        if linkset_match
        else social_index
        if social_index >= 0
        else feed_match.start()
        if feed_match
        else cleaned.index("</head>")
    )
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + banner_block(app_id)
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def _guide_pages(pages: Path) -> set[Path]:
    paths = {path.resolve() for path in (pages / "guides").glob("*.html")}
    for child in pages.iterdir():
        if child.name == "_engine" or not child.is_dir():
            continue
        guides = child / "guides"
        if guides.is_dir():
            paths.update(path.resolve() for path in guides.glob("*.html"))
    return paths


def _answer_pages(pages: Path) -> set[Path]:
    paths = {
        path.resolve()
        for path in (pages / "answers").glob("*.html")
        if path.name != "index.html"
    }
    for child in pages.iterdir():
        if child.name == "_engine" or not child.is_dir():
            continue
        answers = child / "answers"
        if answers.is_dir():
            paths.update(
                path.resolve()
                for path in answers.glob("*.html")
                if path.name != "index.html"
            )
    return paths


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = build_targets(pages, set(live_keys), site)
    guide_pages = _guide_pages(pages)
    answer_pages = _answer_pages(pages)
    changed = 0
    for path in sorted(targets):
        changed += int(ensure_banner(path, targets[path]))

    for path in sorted((guide_pages | answer_pages) - set(targets)):
        source = path.read_text(encoding="utf-8")
        if BLOCK_RE.search(source):
            changed += int(_write_if_changed(path, BLOCK_RE.sub("\n", source)))

    pages_root = pages.resolve()
    languages = {
        "en" if path.parent.parent == pages_root else path.parent.parent.name
        for path in targets
    }
    return {
        "apps": app_count,
        "guide_pages": len(set(targets) & guide_pages),
        "answer_pages": len(set(targets) & answer_pages),
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
        f"{result['answer_pages']} buyer-intent answer pages, "
        f"{result['languages']} languages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
