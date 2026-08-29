#!/usr/bin/env python3
"""Publish an auditable daily digest covering every publicly available app."""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from social_post_common import (
    HTTPStatusError,
    RequestError,
    campaign_app_store_url,
    canonical_app_store_url,
    coverage_diff,
    request_json,
    validate_url,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
ENGINE_SOCIAL = REPO_ROOT / "_engine" / "social"
if str(ENGINE_SOCIAL) not in sys.path:
    sys.path.insert(0, str(ENGINE_SOCIAL))

from videogen.registry import APPS, APPSTORE  # noqa: E402

import telegram_post  # noqa: E402
import telegram_public_receipts as receipts  # noqa: E402
import threads_post  # noqa: E402

DEVELOPER_URL = "https://apps.apple.com/developer/id1136144960"
SITE_URL = "https://alice51849.github.io/ios-app-guide"
LINKSET_PATH = REPO_ROOT / "linkset.json"
TELEGRAM_LIMIT = 3900
THREADS_LIMIT = threads_post.MAX_POST_CHARS
THREADS_LINK_LIMIT = 5
PORTFOLIO_WORKFLOW = "portfolio-daily.yml"
TELEGRAM_PUBLICATION_STATE_CONTRACT = "telegram-portfolio-publication-state"
TELEGRAM_PUBLICATION_STATE_VERSION = 1
TELEGRAM_PUBLICATION_PHASES = ("prepare", "publish", "verify")
PLATFORM_CAMPAIGNS = {
    "telegram": "soc_tg_guide",
    "threads": "soc_th_guide",
}

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

    def appstore_url(self, campaign=None):
        canonical = canonical_app_store_url(
            f"https://apps.apple.com/app/id{self.app_id}"
        )
        return (
            canonical
            if campaign is None
            else campaign_app_store_url(canonical, campaign)
        )


@dataclasses.dataclass(frozen=True)
class DigestMessage:
    text: str
    app_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class PublishedMessage:
    """A public message id paired with the digest batch it published."""

    message_id: int
    message: DigestMessage


def _as_utc(value, label):
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = dt.datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            )
        except ValueError as error:
            raise CoverageError(f"{label} is not an ISO-8601 instant") from error
    else:
        raise CoverageError(f"{label} is missing")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _iso(value):
    return _as_utc(value, "timestamp").isoformat().replace("+00:00", "Z")


def _sha256(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _require_scheduled_telegram_event(env=None):
    env = os.environ if env is None else env
    event = str(env.get("GITHUB_EVENT_NAME", "")).strip()
    if event != "schedule":
        raise CoverageError(
            f"Telegram publication is schedule-only; refusing event {event!r}"
        )


def _publication_state_path(path=None, env=None):
    env = os.environ if env is None else env
    value = path or str(env.get("TELEGRAM_PUBLICATION_STATE", "")).strip()
    if not value:
        raise CoverageError("TELEGRAM_PUBLICATION_STATE is required")
    return Path(value)


def _publication_day(now=None):
    now = dt.datetime.now(dt.timezone.utc) if now is None else _as_utc(
        now, "now"
    )
    return now.date().isoformat()


def _publication_digest(messages):
    payload = [
        {"text": message.text, "app_ids": list(message.app_ids)}
        for message in messages
    ]
    return _sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _publication_app_ids(messages):
    return [
        app_id
        for message in messages
        for app_id in message.app_ids
    ]


def write_publication_state(state, path, *, env=None):
    """Atomically checkpoint the private at-most-once publication state."""
    path = Path(path)
    encoded = json.dumps(
        state, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    receipts.assert_no_credentials(encoded, env=env)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


def load_publication_state(path):
    path = Path(path)
    if not path.is_file():
        raise CoverageError(f"Telegram publication state is missing: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CoverageError(
            f"Telegram publication state is unreadable: {path}"
        ) from error
    if not isinstance(state, dict):
        raise CoverageError("Telegram publication state is not an object")
    return state


def _apps_from_publication_state(apps, state):
    expected = state.get("expected_app_ids")
    if (
        not isinstance(expected, list)
        or not expected
        or len(expected) != len(set(expected))
        or any(not isinstance(app_id, str) for app_id in expected)
    ):
        raise CoverageError("Telegram publication state has invalid app ids")
    by_id = {app.app_id: app for app in apps}
    missing = [app_id for app_id in expected if app_id not in by_id]
    if missing:
        raise CoverageError(
            f"Telegram publication state references missing apps: {missing}"
        )
    return [by_id[app_id] for app_id in expected]


def validate_publication_state(state, messages, *, now=None):
    """Bind restored private state to this exact digest and UTC day."""
    messages = list(messages)
    required = {
        "schema_version",
        "contract",
        "publication_day",
        "status",
        "digest_sha256",
        "expected_message_count",
        "expected_app_count",
        "expected_app_ids",
        "source",
        "source_started_at",
        "created_at",
        "updated_at",
        "messages",
    }
    if set(state) != required:
        raise CoverageError("Telegram publication state fields are incomplete")
    if (
        state.get("schema_version") != TELEGRAM_PUBLICATION_STATE_VERSION
        or state.get("contract") != TELEGRAM_PUBLICATION_STATE_CONTRACT
    ):
        raise CoverageError("Telegram publication state contract is invalid")
    day = _publication_day(now)
    if state.get("publication_day") != day:
        raise CoverageError(
            "Telegram publication state is not for the current UTC day"
        )
    if not messages:
        raise CoverageError("Telegram publication plan has no messages")
    expected_app_ids = _publication_app_ids(messages)
    if (
        state.get("digest_sha256") != _publication_digest(messages)
        or state.get("expected_message_count") != len(messages)
        or state.get("expected_app_count") != len(expected_app_ids)
        or state.get("expected_app_ids") != expected_app_ids
    ):
        raise CoverageError(
            "Telegram publication state does not match the current digest"
        )
    source = receipts.validate_source_context(state.get("source"))
    started_at = _as_utc(state.get("source_started_at"), "source_started_at")
    if started_at.date().isoformat() != day:
        raise CoverageError(
            "Telegram publication source is not from the current UTC day"
        )
    _as_utc(state.get("created_at"), "created_at")
    _as_utc(state.get("updated_at"), "updated_at")
    posted = state.get("messages")
    if not isinstance(posted, list) or len(posted) > len(messages):
        raise CoverageError("Telegram publication message state is invalid")
    seen_ids = set()
    for index, (record, message) in enumerate(
        zip(posted, messages), start=1
    ):
        if not isinstance(record, dict) or set(record) != {
            "message_index",
            "message_id",
            "app_ids",
            "text_sha256",
        }:
            raise CoverageError("Telegram publication message is invalid")
        message_id = record.get("message_id")
        if (
            record.get("message_index") != index
            or not isinstance(message_id, int)
            or isinstance(message_id, bool)
            or message_id <= 0
            or message_id in seen_ids
            or record.get("app_ids") != list(message.app_ids)
            or record.get("text_sha256") != _sha256(message.text)
        ):
            raise CoverageError(
                f"Telegram publication message {index} does not match"
            )
        seen_ids.add(message_id)
    expected_status = (
        "reserved"
        if not posted
        else "complete"
        if len(posted) == len(messages)
        else "partial"
    )
    if state.get("status") != expected_status:
        raise CoverageError("Telegram publication status is inconsistent")
    state["source"] = source
    return state


def prepare_telegram_publication(messages, *, path=None, env=None, now=None):
    """Create a durable reservation before the first Telegram POST."""
    env = os.environ if env is None else env
    _require_scheduled_telegram_event(env)
    path = _publication_state_path(path, env)
    messages = list(messages)
    if path.exists():
        state = validate_publication_state(
            load_publication_state(path), messages, now=now
        )
        if state["status"] != "complete":
            raise CoverageError(
                "An incomplete durable Telegram publication marker exists; "
                "refusing to POST or guess a safe continuation"
            )
        return state, False
    if str(env.get("TELEGRAM_PUBLICATION_CACHE_MATCHED", "")).strip():
        raise CoverageError(
            "Telegram publication cache matched but its state file is missing"
        )
    now = dt.datetime.now(dt.timezone.utc) if now is None else _as_utc(
        now, "now"
    )
    source = receipts.source_context(env)
    app_ids = _publication_app_ids(messages)
    if not messages or not app_ids or len(app_ids) != len(set(app_ids)):
        raise CoverageError("Telegram publication plan is incomplete")
    state = {
        "schema_version": TELEGRAM_PUBLICATION_STATE_VERSION,
        "contract": TELEGRAM_PUBLICATION_STATE_CONTRACT,
        "publication_day": now.date().isoformat(),
        "status": "reserved",
        "digest_sha256": _publication_digest(messages),
        "expected_message_count": len(messages),
        "expected_app_count": len(app_ids),
        "expected_app_ids": app_ids,
        "source": source,
        "source_started_at": _iso(now),
        "created_at": _iso(now),
        "updated_at": _iso(now),
        "messages": [],
    }
    validate_publication_state(state, messages, now=now)
    write_publication_state(state, path, env=env)
    return state, True


def published_messages_from_state(state, messages, *, now=None):
    state = validate_publication_state(state, messages, now=now)
    if state["status"] != "complete":
        raise CoverageError(
            "Telegram publication is incomplete; public verification blocked"
        )
    return [
        PublishedMessage(record["message_id"], message)
        for record, message in zip(state["messages"], messages)
    ]


def publish_telegram_once(
    messages,
    *,
    path=None,
    env=None,
    sender=None,
    now=None,
):
    """POST a reserved digest once, checkpointing every accepted message."""
    env = os.environ if env is None else env
    _require_scheduled_telegram_event(env)
    path = _publication_state_path(path, env)
    messages = list(messages)
    state = validate_publication_state(
        load_publication_state(path), messages, now=now
    )
    if state["status"] == "complete":
        print("Telegram digest already POSTed; reusing durable message ids")
        return published_messages_from_state(state, messages, now=now)
    if state["status"] != "reserved":
        raise CoverageError(
            "A partial Telegram digest already exists; refusing duplicate POST"
        )
    current_source = receipts.source_context(env)
    if state["source"] != current_source:
        raise CoverageError(
            "Telegram reservation belongs to an earlier run; refusing POST"
        )
    if (
        str(
            env.get("TELEGRAM_PUBLICATION_RESERVATION_PERSISTED", "")
        ).casefold()
        != "true"
    ):
        raise CoverageError(
            "Telegram reservation was not durably persisted before POST"
        )
    token = str(env.get("TELEGRAM_BOT_TOKEN", "")).strip()
    chat = str(env.get("TELEGRAM_CHAT_ID", "")).strip()
    if not token or not chat:
        raise CoverageError("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    if sender is None:
        def send_message(token, chat, text):
            # An ambiguous POST timeout cannot be retried safely: the bot API
            # has no idempotency key, so the durable reservation must block.
            return telegram_post._send_message(
                token, chat, text, attempts=1
            )
    else:
        send_message = sender
    for index, message in enumerate(messages, start=1):
        result = send_message(token, chat, message.text)
        message_id = (
            result.get("result", {}).get("message_id")
            if isinstance(result, dict)
            else None
        )
        if (
            not isinstance(result, dict)
            or result.get("ok") is not True
            or not isinstance(message_id, int)
            or isinstance(message_id, bool)
            or message_id <= 0
            or message_id in {
                item["message_id"] for item in state["messages"]
            }
        ):
            raise RequestError(
                "Telegram sendMessage returned no unique message_id"
            )
        state["messages"].append(
            {
                "message_index": index,
                "message_id": message_id,
                "app_ids": list(message.app_ids),
                "text_sha256": _sha256(message.text),
            }
        )
        state["status"] = (
            "complete"
            if len(state["messages"]) == len(messages)
            else "partial"
        )
        checkpoint_at = (
            dt.datetime.now(dt.timezone.utc)
            if now is None
            else _as_utc(now, "now")
        )
        state["updated_at"] = _iso(checkpoint_at)
        write_publication_state(state, path, env=env)
        print("telegram portfolio posted, message_id:", message_id)
    return published_messages_from_state(state, messages, now=now)


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


def _github_json(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ios-app-guide-portfolio-coverage",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return request_json(
        urllib.request.Request(url, headers=headers),
        label="GitHub Actions coverage history",
        timeout=30,
        attempts=3,
        retry_delays=(1, 2),
    )


def _github_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(dt.timezone.utc)


def already_published_today(
    platform,
    *,
    now=None,
    repository=None,
    current_run_id=None,
    token=None,
    fetcher=_github_json,
):
    if str(platform).casefold() == "telegram":
        raise CoverageError(
            "Telegram idempotence requires durable publication state, "
            "not successful-job history"
        )
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    today = now.astimezone(dt.timezone.utc).date()
    repository = (
        os.environ.get("GITHUB_REPOSITORY", "")
        if repository is None
        else repository
    )
    current_run_id = (
        os.environ.get("GITHUB_RUN_ID", "")
        if current_run_id is None
        else current_run_id
    )
    token = (
        os.environ.get("GITHUB_TOKEN", "")
        if token is None
        else token
    )
    if not repository or not current_run_id:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise CoverageError(f"Invalid GITHUB_REPOSITORY: {repository!r}")

    base = f"https://api.github.com/repos/{repository}"
    query = urllib.parse.urlencode(
        {"status": "completed", "per_page": "30"}
    )
    history = fetcher(
        f"{base}/actions/workflows/{PORTFOLIO_WORKFLOW}/runs?{query}",
        token,
    )
    runs = history.get("workflow_runs") if isinstance(history, dict) else None
    if not isinstance(runs, list):
        raise CoverageError("GitHub Actions history has no workflow_runs")
    for run in runs:
        if (
            not isinstance(run, dict)
            or run.get("event") != "schedule"
            or str(run.get("id")) == str(current_run_id)
        ):
            continue
        created = _github_time(run.get("created_at"))
        if created and created.date() < today - dt.timedelta(days=1):
            continue
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        jobs_payload = fetcher(
            f"{base}/actions/runs/{run_id}/jobs?filter=all&per_page=100",
            token,
        )
        jobs = (
            jobs_payload.get("jobs")
            if isinstance(jobs_payload, dict)
            else None
        )
        if not isinstance(jobs, list):
            raise CoverageError(
                f"GitHub Actions run {run_id} has no jobs array"
            )
        for job in jobs:
            if (
                isinstance(job, dict)
                and str(job.get("name") or "").casefold()
                == platform.casefold()
                and job.get("conclusion") == "success"
            ):
                completed = _github_time(job.get("completed_at"))
                if completed is None:
                    raise CoverageError(
                        f"Successful {platform} job in run {run_id} "
                        "has no valid completed_at"
                    )
                if completed.date() == today:
                    print(
                        f"{platform} portfolio already published today "
                        f"by run {run_id}; skipping"
                    )
                    return True
    return False


def filter_reachable_apps(apps, validator=validate_url, max_workers=3):
    # 這一步會對 apps.apple.com 連打整個 portfolio(40+ 個 URL)。原本 8 條
    # 併發 + 3 次重試(1s、2s)對 Apple 來說是一陣突刺,GitHub-hosted runner
    # 的共用出口 IP 很容易被回 HTTP 429,整個 Telegram 日報就 fail 掉 ——
    # 2026-08-18 連續兩次都是這樣掛的,而它一天只跑一次、掛了就等於當天沒發。
    # 降低併發並改用較長的指數退避:對 Apple 更客氣,對我們更不容易整批失敗。
    # 這裡只影響「發文前的 URL 可達性檢查」,不改變任何發文頻率或配額。
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
                attempts=6,
                retry_delays=(2, 5, 10, 20, 40),
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


def _pack_apps(
    apps, entry_text, separator, capacity, max_items=None
):
    batches = []
    current = []
    current_size = 0
    for app in apps:
        entry_size = len(entry_text(app))
        added_size = entry_size + (len(separator) if current else 0)
        if current and (
            current_size + added_size > capacity
            or (max_items is not None and len(current) >= max_items)
        ):
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


def telegram_entry_text(app):
    """The exact line a public Telegram message must contain for this app."""
    category = CATEGORY_ZH.get(app.category, CATEGORY_ZH["other"])
    return (
        f"• {category}｜{app.name}\n"
        f"  {app.appstore_url(PLATFORM_CAMPAIGNS['telegram'])}"
    )


def telegram_messages(apps):
    total = len(apps)
    footer = f"\n\n完整開發者頁：{DEVELOPER_URL}"
    disclosure = receipts.disclosure_block()
    reserved_header = (
        f"✨ Lumi Studio 自家 App 每日總覽｜{total} 款｜第 99/99 則\n\n"
        f"{disclosure}\n\n"
        "今天已公開的 App 一次看，依需求挑選：\n"
    )

    batches = _pack_apps(
        apps,
        telegram_entry_text,
        "\n",
        TELEGRAM_LIMIT - len(reserved_header) - len(footer),
    )
    if len(batches) > 99:
        raise CoverageError("Telegram digest requires more than 99 messages")

    messages = []
    for index, batch in enumerate(batches, start=1):
        part = "" if len(batches) == 1 else f"｜第 {index}/{len(batches)} 則"
        header = (
            f"✨ Lumi Studio 自家 App 每日總覽｜{total} 款{part}\n\n"
            f"{disclosure}\n\n"
            "今天已公開的 App 一次看，依需求挑選：\n"
        )
        text = (
            header
            + "\n".join(telegram_entry_text(app) for app in batch)
            + footer
        )
        if len(text) > TELEGRAM_LIMIT:
            raise CoverageError(f"Telegram digest is too long: {len(text)}")
        if not receipts.verify_disclosure(text):
            raise CoverageError(
                "Telegram digest is missing its first-party disclosure"
            )
        messages.append(DigestMessage(text, tuple(app.app_id for app in batch)))
    return messages


def threads_messages(apps):
    total = len(apps)
    campaign = PLATFORM_CAMPAIGNS["threads"]
    footer = ""
    reserved_header = (
        f"Daily portfolio 99/99 — {total} live apps, all included today.\n\n"
    )
    def entry(app):
        return f"{app.name}\n{app.appstore_url(campaign)}"

    batches = _pack_apps(
        apps,
        entry,
        "\n",
        THREADS_LIMIT - len(reserved_header) - len(footer),
        max_items=THREADS_LINK_LIMIT,
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
    campaign = PLATFORM_CAMPAIGNS.get(platform)
    if campaign is None:
        raise CoverageError(f"Unsupported platform: {platform}")
    expected = [app.app_id for app in apps]
    observed = [
        app_id for message in messages for app_id in message.app_ids
    ]
    missing, unexpected, duplicates = coverage_diff(expected, observed)
    if missing or unexpected or duplicates:
        raise CoverageError(
            f"{platform} coverage invalid: missing={missing}, "
            f"unexpected={unexpected}, duplicate_or_repeated={duplicates}"
        )
    by_id = {app.app_id: app for app in apps}
    link_pattern = re.compile(r"https?://apps\.apple\.com/app/id\d+\S*")
    for message in messages:
        expected_urls = [
            by_id[app_id].appstore_url(campaign)
            for app_id in message.app_ids
        ]
        observed_urls = link_pattern.findall(message.text)
        if observed_urls != expected_urls:
            raise CoverageError(
                f"{platform} direct links invalid: "
                f"expected={expected_urls}, observed={observed_urls}"
            )
        for url in observed_urls:
            parsed = urllib.parse.urlsplit(url)
            bare = urllib.parse.urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, "", "")
            )
            if campaign_app_store_url(bare, campaign) != url:
                raise CoverageError(
                    f"{platform} App Store URL attribution is invalid: {url}"
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
        raise CoverageError(
            "Telegram publishing requires the durable phased publisher"
        )

    token = os.environ.get("THREADS_TOKEN", "").strip()
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    if not token or not user_id:
        raise CoverageError("Missing THREADS_TOKEN / THREADS_USER_ID")
    for message in messages:
        post_id = threads_post.publish_text(token, user_id, message.text)
        print("threads portfolio posted, id:", post_id)
    return []


def digest_entries(apps):
    """Publisher-reviewed identities exactly as the digest renders them."""
    campaign = PLATFORM_CAMPAIGNS["telegram"]
    return {
        app.app_id: receipts.DigestEntry(
            app_key=app.key,
            app_store_id=app.app_id,
            app_name=app.name,
            category=app.category,
            canonical_app_store_url=app.appstore_url(),
            campaign_app_store_url=app.appstore_url(campaign),
            entry_text=telegram_entry_text(app),
        )
        for app in apps
    }


def record_public_receipts(apps, published, **kwargs):
    """Prove the just-published digest from public evidence, or fail closed."""
    entries = digest_entries(apps)
    shards = {
        item.message_id: [entries[app_id] for app_id in item.message.app_ids]
        for item in published
    }
    if len(shards) != len(published):
        raise CoverageError("Telegram returned a duplicate public message id")
    return receipts.record_publication(
        shards,
        expected_entries=list(entries.values()),
        **kwargs,
    )


def verify_telegram_publication(
    apps,
    messages,
    *,
    path=None,
    env=None,
    now=None,
    **kwargs,
):
    """Verify a complete durable POST state without ever posting again."""
    env = os.environ if env is None else env
    _require_scheduled_telegram_event(env)
    path = _publication_state_path(path, env)
    state = validate_publication_state(
        load_publication_state(path), messages, now=now
    )
    published = published_messages_from_state(state, messages, now=now)
    return record_public_receipts(
        apps,
        published,
        env=env,
        source=state["source"],
        source_started_at=state["source_started_at"],
        **kwargs,
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--platform", required=True, choices=("telegram", "threads")
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--telegram-phase", choices=TELEGRAM_PUBLICATION_PHASES
    )
    args = parser.parse_args(argv)
    try:
        if args.telegram_phase and args.platform != "telegram":
            raise CoverageError(
                "--telegram-phase is only valid for Telegram"
            )
        if args.telegram_phase and args.dry_run:
            raise CoverageError(
                "--telegram-phase cannot be combined with --dry-run"
            )
        if args.platform == "telegram" and not args.dry_run:
            _require_scheduled_telegram_event()
            if not args.telegram_phase:
                raise CoverageError(
                    "Telegram requires --telegram-phase "
                    "prepare, publish, or verify"
                )
            state_path = _publication_state_path()
            all_apps = load_public_apps()
            if args.telegram_phase == "prepare" and not state_path.exists():
                apps = filter_reachable_apps(all_apps)
            else:
                state = load_publication_state(state_path)
                apps = _apps_from_publication_state(all_apps, state)
            messages = telegram_messages(apps)
            validate_coverage("telegram", apps, messages)
            if args.telegram_phase == "prepare":
                state, created = prepare_telegram_publication(
                    messages, path=state_path
                )
                print(
                    "TELEGRAM_PUBLICATION_STATE "
                    f"status={state['status']} created={str(created).lower()}"
                )
            elif args.telegram_phase == "publish":
                published = publish_telegram_once(
                    messages, path=state_path
                )
                print(
                    "TELEGRAM_PUBLICATION_POST "
                    f"messages={len(published)} status=complete"
                )
            else:
                store, minted = verify_telegram_publication(
                    apps, messages, path=state_path
                )
                report_coverage("telegram", apps, messages)
                print(
                    "TELEGRAM_PUBLIC_RECEIPTS minted="
                    f"{len(minted)} stored="
                    f"{store.get('countable_receipt_count', 0)} apps="
                    f"{store.get('countable_app_count', 0)}"
                )
            return 0
        # Telegram intentionally never reaches this job-history heuristic:
        # its private reservation/result state survives failed verification.
        if not args.dry_run and already_published_today(args.platform):
            return 0
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
        receipts.ReceiptError,
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
