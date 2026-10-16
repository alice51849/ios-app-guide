#!/usr/bin/env python3
"""每天把每一款上架 App 的主頁網址送一次 IndexNow。

增量通知（_engine/geo/indexnow_submit.py --git-since）只送內容真的變了的頁，
全量盤點一個月才一次；App 主頁因此可能好幾週都沒被通知。這裡每天固定送：

* 每款 verified-live App 在 50 個官方語系的主頁 ``<site>/<locale>/<key>.html``
* 每款 App 在 linkset 入口列出的指南頁 ``<site>/guides/<slug>.html``

只送已部署 sitemap 裡真的有的網址；同一個 UTC 日只送一次（durable state），
同一次 workflow 裡增量步驟剛送過的網址不重送。送出與失敗判定沿用
indexnow_submit 的嚴格檢查（每個 endpoint 都要 200/202）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "_engine" / "geo"
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import indexnow_submit as indexnow  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402

STATE_VERSION = 1
STATE_KIND = "indexnow_daily_app_pages"
# 53 款 × 50 語系 + 53 指南頁約 2,700；上限留在 IndexNow 單批 10,000 的一半。
MAX_DAILY_URLS = 5_000
# 業主已放棄的 App，即使資料檔還留著也絕不送。
ABANDONED_APP_KEYS = frozenset({"lensafe"})
KEY_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
SLUG_RE = re.compile(r"[a-z0-9-]+")


def live_app_keys(pages_dir: Path) -> list[str]:
    path = pages_dir / indexnow.FINDER_CATALOG_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    records = document.get("apps")
    if not isinstance(records, list) or not records:
        raise ValueError("verified App catalog has no apps")
    keys = []
    for record in records:
        if not isinstance(record, dict) or record.get("verified_live") is not True:
            continue
        key = str(record.get("key") or "").strip()
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"verified App catalog has an invalid key: {key!r}")
        if key in ABANDONED_APP_KEYS or key in keys:
            continue
        keys.append(key)
    if not keys:
        raise ValueError("verified App catalog has no live apps")
    return keys


def guide_urls(pages_dir: Path, site: str) -> list[str]:
    """Guide pages the portfolio linkset lists, one per live App."""
    path = pages_dir / "linkset.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    prefix = f"{site}/guides/"
    urls = []
    for entry in payload.get("linkset") or []:
        if not isinstance(entry, dict) or entry.get("anchor") not in {
            f"{site}/", f"{site}/index.html",
        }:
            continue
        for item in entry.get("item") or []:
            href = item.get("href") if isinstance(item, dict) else None
            if not isinstance(href, str) or not href.startswith(prefix):
                continue
            slug = href[len(prefix):].removesuffix(".html")
            if (
                SLUG_RE.fullmatch(slug)
                and slug not in ABANDONED_APP_KEYS
                and href not in urls
            ):
                urls.append(href)
    return urls


def app_page_urls(pages_dir: Path, site: str, sitemap_urls: list[str]) -> list[str]:
    site = site.rstrip("/")
    wanted = [
        f"{site}/{locale}/{key}.html"
        for key in live_app_keys(pages_dir)
        for locale in OFFICIAL_LOCALES
    ] + guide_urls(pages_dir, site)
    # 只送已部署 sitemap 列出的網址：不送不存在或 noindex 的頁。
    published = set(sitemap_urls)
    urls = []
    seen = set()
    for url in wanted:
        if url in published and url not in seen:
            indexnow.validate_public_url(url, site)
            seen.add(url)
            urls.append(url)
    if not urls:
        raise ValueError("no App homepage URL is in the deployed sitemap")
    if len(urls) > MAX_DAILY_URLS:
        raise ValueError(
            f"{len(urls)} App homepage URLs exceed the daily cap {MAX_DAILY_URLS}"
        )
    return urls


def read_state(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if (
        not isinstance(state, dict)
        or state.get("version") != STATE_VERSION
        or state.get("kind") != STATE_KIND
    ):
        return {}
    return state


def already_sent_today(receipt_file: Path | None, today: dt.date) -> set[str]:
    """URLs the incremental step already got accepted today (no double send)."""
    if receipt_file is None or not receipt_file.is_file():
        return set()
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        accepted_at = dt.datetime.fromisoformat(
            str(receipt.get("accepted_at") or "").replace("Z", "+00:00")
        ).astimezone(dt.timezone.utc).date()
    except (json.JSONDecodeError, OSError, ValueError, TypeError, AttributeError):
        return set()
    if (
        not isinstance(receipt, dict)
        or receipt.get("kind") != "indexnow_submission_receipt"
        or receipt.get("semantics") != "accepted_by_endpoints_not_indexed"
        or accepted_at != today
        or not isinstance(receipt.get("urls"), list)
    ):
        return set()
    return {url for url in receipt["urls"] if isinstance(url, str)}


def run(
    pages_dir: Path,
    site: str,
    key_file: Path,
    *,
    state_file: Path,
    incremental_receipt: Path | None = None,
    key_location: str | None = None,
    sender=indexnow.submit_endpoint,
    clock=lambda: dt.datetime.now(dt.timezone.utc),
) -> int:
    site = site.rstrip("/")
    now = clock().astimezone(dt.timezone.utc)
    today = now.date()
    state = read_state(state_file)
    if state.get("date") == today.isoformat():
        print(f"App homepages already submitted on {today}; nothing to do")
        return 0
    urls = app_page_urls(pages_dir, site, indexnow.read_urls(pages_dir, site))
    recent = already_sent_today(incremental_receipt, today)
    pending = [url for url in urls if url not in recent]
    print(
        f"app_homepage_urls={len(urls)} "
        f"already_sent_today_by_incremental={len(urls) - len(pending)} "
        f"submitting={len(pending)}"
    )
    accepted = 0
    if pending:
        key = indexnow.read_key(key_file)
        accepted = indexnow.submit_all(
            pending,
            key,
            site,
            sender=sender,
            key_location=indexnow.key_location_for(site, key, key_location),
        )
        if accepted != len(pending):
            raise indexnow.SubmissionError(
                f"Only {accepted}/{len(pending)} App homepage URLs were accepted"
            )
    state_file.parent.mkdir(parents=True, exist_ok=True)
    indexnow.write_private_json(state_file, {
        "version": STATE_VERSION,
        "kind": STATE_KIND,
        "semantics": "accepted_by_endpoints_not_indexed",
        "date": today.isoformat(),
        "accepted_at": now.isoformat(),
        "app_homepage_url_count": len(urls),
        "submitted_url_count": accepted,
        "url_set_sha256": indexnow.url_set_digest(urls),
    })
    print(f"Accepted {accepted}/{len(pending)} App homepage URLs by every IndexNow endpoint")
    return accepted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--key-location")
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument(
        "--incremental-receipt", type=Path,
        help="accepted-receipt.json of the incremental step; its URLs are not resent today",
    )
    args = parser.parse_args(argv)
    from notification_release import held_result

    held = held_result("indexnow")
    if held:
        print(json.dumps(held, sort_keys=True))
        return 0
    run(
        args.pages_dir,
        args.site,
        args.key_file,
        state_file=args.state_file,
        incremental_receipt=args.incremental_receipt,
        key_location=args.key_location,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
