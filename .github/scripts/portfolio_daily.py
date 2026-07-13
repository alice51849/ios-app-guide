#!/usr/bin/env python3
"""Publish an auditable daily digest covering every publicly available app."""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import dataclasses
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

from social_post_common import (
    HTTPStatusError,
    RequestError,
    canonical_app_store_url,
    validate_url,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ENGINE_SOCIAL = REPO_ROOT / "_engine" / "social"
if str(ENGINE_SOCIAL) not in sys.path:
    sys.path.insert(0, str(ENGINE_SOCIAL))

from videogen.registry import APPS, APPSTORE  # noqa: E402

import telegram_post  # noqa: E402
import threads_post  # noqa: E402

DEVELOPER_URL = "https://apps.apple.com/developer/id1136144960"
SITE_URL = "https://alice51849.github.io/ios-app-guide"
LINKSET_PATH = REPO_ROOT / "linkset.json"
TELEGRAM_LIMIT = 3900
THREADS_LIMIT = threads_post.MAX_POST_CHARS

CATEGORY_ORDER = {
    "kids": 0,
    "education": 0,
    "photo-utility": 1,
    "productivity": 2,
    "finance": 3,
    "health": 4,
    "sleep-sound": 4,
    "travel": 5,
    "lifestyle": 6,
    "other": 7,
}
CATEGORY_ZH = {
    "kids": "親子學習",
    "education": "親子學習",
    "photo-utility": "相片工具",
    "productivity": "效率工具",
    "finance": "財務管理",
    "health": "健康生活",
    "sleep-sound": "健康生活",
    "travel": "旅行規劃",
    "lifestyle": "生活工具",
    "other": "更多工具",
}


class CoverageError(RuntimeError):
    """Raised when a daily digest cannot prove complete public-app coverage."""


@dataclasses.dataclass(frozen=True)
class PublicApp:
    key: str
    app_id: str
    name: str
    category: str

    def appstore_url(self):
        return canonical_app_store_url(
            f"https://apps.apple.com/app/id{self.app_id}"
        )


@dataclasses.dataclass(frozen=True)
class DigestMessage:
    text: str
    app_ids: tuple[str, ...]


def _title(item):
    titles = item.get("title*") if isinstance(item, dict) else None
    if not isinstance(titles, list):
        raise CoverageError("Live guide is missing title metadata")
    values = [
        str(title.get("value") or "").strip()
        for title in titles
        if isinstance(title, dict)
    ]
    values = [value for value in values if value]
    if not values:
        raise CoverageError("Live guide has an empty title")
    return values[0]


def _guide_slug(href):
    parsed = urllib.parse.urlsplit(href) if isinstance(href, str) else None
    prefix = "/ios-app-guide/guides/"
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.netloc != "alice51849.github.io"
        or not parsed.path.startswith(prefix)
        or parsed.query
        or parsed.fragment
    ):
        raise CoverageError(f"Invalid live guide URL: {href!r}")
    relative = parsed.path[len(prefix) :]
    if "/" in relative or not re.fullmatch(r"[a-z0-9-]+\.html", relative):
        raise CoverageError(f"Invalid live guide path: {href}")
    return relative[:-5]


def _related_app_url(entry):
    related = entry.get("related") if isinstance(entry, dict) else None
    if not isinstance(related, list):
        raise CoverageError("Live guide is missing related links")
    app_urls = []
    for relation in related:
        href = relation.get("href") if isinstance(relation, dict) else None
        parsed = urllib.parse.urlsplit(href) if isinstance(href, str) else None
        if not parsed or parsed.netloc != "apps.apple.com":
            continue
        if parsed.scheme != "https" or parsed.fragment:
            raise CoverageError(f"Invalid App Store relation: {href}")
        bare_url = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, "", "")
        )
        try:
            app_urls.append(canonical_app_store_url(bare_url))
        except ValueError as error:
            raise CoverageError(f"Invalid App Store relation: {href}") from error
    if len(app_urls) != 1:
        raise CoverageError(
            "Each live guide must have exactly one App Store related link"
        )
    return app_urls[0]


def parse_public_apps(payload, apps=APPS, appstore=APPSTORE):
    entries = payload.get("linkset") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise CoverageError("linkset.json has an invalid top-level structure")
    root_anchors = {f"{SITE_URL}/", f"{SITE_URL}/index.html"}
    roots = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("anchor") in root_anchors
        and isinstance(entry.get("item"), list)
    ]
    if len(roots) != 1:
        raise CoverageError("linkset.json must contain one portfolio guide entry")

    registry_by_id = collections.defaultdict(list)
    for key, app_id in appstore.items():
        registry_by_id[str(app_id)].append(key)
    guide_entries = collections.defaultdict(list)
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("anchor"), str):
            guide_entries[entry["anchor"]].append(entry)

    selected = []
    seen_slugs = set()
    seen_ids = set()
    for item in roots[0]["item"]:
        href = item.get("href") if isinstance(item, dict) else None
        slug = _guide_slug(href)
        if slug in seen_slugs:
            raise CoverageError(f"Duplicate live guide slug: {slug}")
        matches = guide_entries[href]
        if len(matches) != 1:
            raise CoverageError(
                f"Live guide must have exactly one linkset context: {href}"
            )
        app_url = _related_app_url(matches[0])
        app_id = urllib.parse.urlsplit(app_url).path.rsplit("id", 1)[1]
        if app_id in seen_ids:
            raise CoverageError(f"Duplicate live App Store ID: {app_id}")
        registry_keys = registry_by_id.get(app_id, [])
        key = slug if slug in apps else (registry_keys[0] if registry_keys else slug)
        metadata = apps.get(key, {})
        selected.append(
            PublicApp(
                key=key,
                app_id=app_id,
                name=_title(item),
                category=str(metadata.get("category") or "other"),
            )
        )
        seen_slugs.add(slug)
        seen_ids.add(app_id)
    if not selected:
        raise CoverageError("linkset.json contains no live apps")
    return sorted(
        selected,
        key=lambda app: (
            CATEGORY_ORDER.get(app.category, CATEGORY_ORDER["other"]),
            app.name.casefold(),
            app.app_id,
        ),
    )


def load_public_apps(path=LINKSET_PATH):
    with open(path, encoding="utf-8") as linkset_file:
        return parse_public_apps(json.load(linkset_file))


def filter_reachable_apps(apps, validator=validate_url, max_workers=8):
    apps = list(apps)
    if not apps:
        raise CoverageError("Public app registry is empty")
    worker_count = max(1, min(max_workers, len(apps)))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        futures = {
            app.app_id: executor.submit(
                validator,
                app.appstore_url(),
                timeout=10,
                attempts=3,
                retry_delays=(1, 2),
            )
            for app in apps
        }
        reachable = []
        for app in apps:
            if futures[app.app_id].result():
                reachable.append(app)
            else:
                print(
                    f"Daily portfolio: excluding confirmed dead URL "
                    f"{app.appstore_url()}",
                    file=sys.stderr,
                )
    if not reachable:
        raise CoverageError("Every public App Store URL returned 404/410")
    return reachable


def _pack_apps(apps, entry_text, separator, capacity):
    batches = []
    current = []
    current_size = 0
    for app in apps:
        entry_size = len(entry_text(app))
        added_size = entry_size + (len(separator) if current else 0)
        if current and current_size + added_size > capacity:
            batches.append(current)
            current = []
            current_size = 0
            added_size = entry_size
        if added_size > capacity:
            raise CoverageError(f"Digest entry is too long for {app.name}")
        current.append(app)
        current_size += added_size
    if current:
        batches.append(current)
    return batches


def telegram_messages(apps):
    total = len(apps)
    footer = f"\n\n完整開發者頁：{DEVELOPER_URL}"
    reserved_header = (
        f"✨ 每日全 App 精選｜{total} 款｜第 99/99 則\n\n"
        "今天已公開的 App 一次看，依需求挑選：\n"
    )

    def entry(app):
        category = CATEGORY_ZH.get(app.category, CATEGORY_ZH["other"])
        return (
            f"• {category}｜{app.name}\n"
            f"  {app.appstore_url()}"
        )

    batches = _pack_apps(
        apps,
        entry,
        "\n",
        TELEGRAM_LIMIT - len(reserved_header) - len(footer),
    )
    if len(batches) > 99:
        raise CoverageError("Telegram digest requires more than 99 messages")

    messages = []
    for index, batch in enumerate(batches, start=1):
        part = "" if len(batches) == 1 else f"｜第 {index}/{len(batches)} 則"
        header = (
            f"✨ 每日全 App 精選｜{total} 款{part}\n\n"
            "今天已公開的 App 一次看，依需求挑選：\n"
        )
        text = header + "\n".join(entry(app) for app in batch) + footer
        if len(text) > TELEGRAM_LIMIT:
            raise CoverageError(f"Telegram digest is too long: {len(text)}")
        messages.append(DigestMessage(text, tuple(app.app_id for app in batch)))
    return messages


def threads_messages(apps):
    total = len(apps)
    footer = f"\n\nAll apps: {DEVELOPER_URL}"
    reserved_header = (
        f"Daily portfolio 99/99 — {total} live apps, all included today.\n\n"
    )
    def entry(app):
        return f"{app.name}\n{app.appstore_url()}"

    batches = _pack_apps(
        apps,
        entry,
        "\n",
        THREADS_LIMIT - len(reserved_header) - len(footer),
    )
    if len(batches) > 99:
        raise CoverageError("Threads digest requires more than 99 posts")

    messages = []
    for index, batch in enumerate(batches, start=1):
        if len(batches) == 1:
            header = (
                f"Today's complete {total}-app lineup — "
                "every live app, every day.\n\n"
            )
        else:
            header = (
                f"Daily portfolio {index}/{len(batches)} — {total} live apps, "
                "all included today.\n\n"
            )
        text = header + "\n".join(entry(app) for app in batch) + footer
        if len(text) > THREADS_LIMIT:
            raise CoverageError(f"Threads digest is too long: {len(text)}")
        messages.append(DigestMessage(text, tuple(app.app_id for app in batch)))
    return messages


def validate_coverage(platform, apps, messages):
    expected = [app.app_id for app in apps]
    observed = [
        app_id for message in messages for app_id in message.app_ids
    ]
    counts = collections.Counter(observed)
    missing = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    duplicates = sorted(app_id for app_id, count in counts.items() if count != 1)
    if missing or unexpected or duplicates:
        raise CoverageError(
            f"{platform} coverage invalid: missing={missing}, "
            f"unexpected={unexpected}, duplicate_or_repeated={duplicates}"
        )
    by_id = {app.app_id: app for app in apps}
    link_pattern = re.compile(r"https?://apps\.apple\.com/app/id\d+\S*")
    for message in messages:
        expected_urls = [by_id[app_id].appstore_url() for app_id in message.app_ids]
        observed_urls = link_pattern.findall(message.text)
        if observed_urls != expected_urls:
            raise CoverageError(
                f"{platform} direct links invalid: "
                f"expected={expected_urls}, observed={observed_urls}"
            )
        for url in observed_urls:
            if canonical_app_store_url(url) != url:
                raise CoverageError(
                    f"{platform} App Store URL is not canonical: {url}"
                )


def report_coverage(platform, apps, messages):
    by_id = {app.app_id: app for app in apps}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    print(
        f"DAILY_COVERAGE date={today} platform={platform} "
        f"apps={len(apps)} batches={len(messages)}"
    )
    report_lines = [
        f"## Daily portfolio coverage — {today}",
        "",
        f"**Platform:** {platform} · **Public apps:** {len(apps)} · "
        f"**Batches:** {len(messages)}",
        "",
        "| Batch | App Store ID | App |",
        "|---:|---|---|",
    ]
    for batch_index, message in enumerate(messages, start=1):
        for app_id in message.app_ids:
            app = by_id[app_id]
            print(f"  batch={batch_index} app_id={app_id} app={app.name}")
            report_lines.append(f"| {batch_index} | {app_id} | {app.name} |")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("\n".join(report_lines) + "\n")


def publish(platform, messages):
    if platform == "telegram":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat:
            raise CoverageError(
                "Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID"
            )
        for message in messages:
            result = telegram_post._send_message(token, chat, message.text)
            if not result.get("ok") or not result.get("result", {}).get("message_id"):
                raise RequestError("Telegram sendMessage returned no message_id")
            print(
                "telegram portfolio posted, message_id:",
                result["result"]["message_id"],
            )
        return

    token = os.environ.get("THREADS_TOKEN", "").strip()
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    if not token or not user_id:
        raise CoverageError("Missing THREADS_TOKEN / THREADS_USER_ID")
    for message in messages:
        post_id = threads_post.publish_text(token, user_id, message.text)
        print("threads portfolio posted, id:", post_id)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--platform", required=True, choices=("telegram", "threads")
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        apps = filter_reachable_apps(load_public_apps())
        messages = (
            telegram_messages(apps)
            if args.platform == "telegram"
            else threads_messages(apps)
        )
        validate_coverage(args.platform, apps, messages)
        if args.dry_run:
            report_coverage(args.platform, apps, messages)
            for index, message in enumerate(messages, start=1):
                print(f"\n--- {args.platform} batch {index} ---\n{message.text}")
        else:
            publish(args.platform, messages)
            report_coverage(args.platform, apps, messages)
        return 0
    except (
        CoverageError,
        HTTPStatusError,
        RequestError,
        json.JSONDecodeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(f"Daily portfolio coverage failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
