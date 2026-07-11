#!/usr/bin/env python3
"""Publish an auditable daily digest covering every publicly available app."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import json
import os
import sys
from pathlib import Path

from social_post_common import HTTPStatusError, RequestError

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ENGINE_SOCIAL = REPO_ROOT / "_engine" / "social"
if str(ENGINE_SOCIAL) not in sys.path:
    sys.path.insert(0, str(ENGINE_SOCIAL))

from videogen.registry import APPS, APPSTORE  # noqa: E402

import telegram_post  # noqa: E402
import threads_post  # noqa: E402

DEVELOPER_URL = "https://apps.apple.com/developer/id1136144960"
LIVE_STATE_PATH = REPO_ROOT / ".appstore_live_state.json"
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

    def appstore_url(self, campaign):
        return f"https://apps.apple.com/app/id{self.app_id}?ct={campaign}"


@dataclasses.dataclass(frozen=True)
class DigestMessage:
    text: str
    app_ids: tuple[str, ...]


def load_live_ids(path=LIVE_STATE_PATH):
    with open(path, encoding="utf-8") as state_file:
        payload = json.load(state_file)
    live_ids = payload.get("live_ids")
    if not isinstance(live_ids, list) or not live_ids:
        raise CoverageError(f"Missing non-empty live_ids in {path}")
    normalized = [str(app_id) for app_id in live_ids]
    if len(normalized) != len(set(normalized)):
        raise CoverageError(f"Duplicate app IDs in {path}")
    return set(normalized)


def select_public_apps(apps, appstore, live_ids):
    registry_ids = collections.defaultdict(list)
    for key, app_id in appstore.items():
        registry_ids[str(app_id)].append(key)
    duplicate_ids = {
        app_id: keys for app_id, keys in registry_ids.items() if len(keys) > 1
    }
    if duplicate_ids:
        raise CoverageError(f"Duplicate App Store IDs in registry: {duplicate_ids}")

    unknown_ids = set(live_ids) - set(registry_ids)
    if unknown_ids:
        raise CoverageError(
            "Live App Store IDs are missing from the registry: "
            + ", ".join(sorted(unknown_ids))
        )

    selected = []
    for app_id in live_ids:
        key = registry_ids[app_id][0]
        app = apps.get(key)
        if not app or not str(app.get("name", "")).strip():
            raise CoverageError(f"Registry metadata is incomplete for {key}")
        selected.append(
            PublicApp(
                key=key,
                app_id=app_id,
                name=str(app["name"]).strip(),
                category=str(app.get("category", "other")),
            )
        )
    return sorted(
        selected,
        key=lambda app: (
            CATEGORY_ORDER.get(app.category, CATEGORY_ORDER["other"]),
            app.name.casefold(),
            app.app_id,
        ),
    )


def load_public_apps():
    return select_public_apps(APPS, APPSTORE, load_live_ids())


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
            f"  {app.appstore_url('daily_portfolio_telegram')}"
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
    batches = _pack_apps(
        apps,
        lambda app: app.name,
        " · ",
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
        text = header + " · ".join(app.name for app in batch) + footer
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
        apps = load_public_apps()
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
