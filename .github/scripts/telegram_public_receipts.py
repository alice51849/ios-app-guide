#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-app public exposure receipts for the organic Telegram portfolio digest.

A Telegram digest only counts as public exposure when every one of these can be
proved after the fact, from evidence anybody can re-fetch:

* the publication came from a natural GitHub Actions ``schedule`` run
  (``workflow_dispatch`` is never countable, even when the post is public);
* the exact public ``t.me`` message still renders the exact campaign App Store
  URL and publisher entry for that app;
* the same public message carries the first-party commercial disclosure;
* the public read happened inside a 24h freshness window of the publication.

Anything that cannot be proved is recorded as a *non-countable* failure with a
reason instead of being silently downgraded to a success.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import hashlib
import html as html_module
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from social_post_common import (
    DEFAULT_UA,
    HTTPStatusError,
    RequestError,
    TELEGRAM_PUBLIC_CHANNEL,
    canonical_app_store_url,
    coverage_diff,
    request_text,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
STORE_PATH = REPO_ROOT / "data" / "telegram-public-receipts.json"
SCHEMA_PATH = REPO_ROOT / "data" / "telegram-public-receipts.schema.json"
PUBLIC_STORE_URL = (
    "https://alice51849.github.io/ios-app-guide"
    "/data/telegram-public-receipts.json"
)
PUBLIC_SCHEMA_URL = (
    "https://alice51849.github.io/ios-app-guide"
    "/data/telegram-public-receipts.schema.json"
)
STORE_NOTE = (
    "Each receipt proves one app was publicly exposed in one exact Telegram "
    "message published by a natural GitHub Actions schedule run, re-verified "
    "with a public GET. workflow_dispatch runs are never countable."
)

SCHEMA_VERSION = 1
CONTRACT_ID = "telegram-public-organic-exposure"
GENERATOR = "telegram_public_receipts.py"
PUBLISHER_WORKFLOW = "portfolio-daily.yml"

# Only a genuinely natural trigger can mint a countable receipt. Manual
# dispatches, re-runs chained off another workflow, pushes and API dispatches
# all stay non-countable even when they do publish a real public message.
COUNTABLE_EVENTS = frozenset({"schedule"})

FRESHNESS_WINDOW = dt.timedelta(hours=24)
# A public message that predates this process cannot have been published by it.
SOURCE_START_SLACK = dt.timedelta(minutes=5)
# Bounded history: the store is committed back to a public repo.
MAX_PUBLICATION_DAYS = 14
MAX_RECEIPTS = 1500
MAX_FAILURES = 60

PUBLIC_MESSAGE_URL = "https://t.me/{channel}/{message_id}"
PUBLIC_EVIDENCE_URL = "https://t.me/{channel}/{message_id}?embed=1&mode=tme"
CHANNEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")

# Digest body language. The digest is authored in Traditional Chinese, so the
# locale recorded on a receipt is only ever the one we can actually prove from
# the public message body.
DIGEST_LOCALE = "zh-Hant"

# First-party commercial disclosure. It uses the same publisher vocabulary as
# the on-site disclosures (_engine/geo/gen_publisher_disclosures.py): we are the
# developer, this is a first-party catalogue, and it is not a ranking.
DISCLOSURE_LINES = (
    "📣 Lumi Studio 官方頻道發布：以下每一款都是我們自行開發並發行的 App，"
    "屬於第一方產品清單，不是第三方評比或排行榜。",
    "📣 Posted by Lumi Studio, the app developer: every app below is our own "
    "first-party product. This is a publisher catalog, not an independent "
    "ranking.",
)

_MESSAGE_BLOCK_RE = re.compile(
    r'<div class="tgme_widget_message(?:\s[^"]*)?"[^>]*'
    r'data-post="(?P<post>[^"]+)"(?P<attrs>[^>]*)>(?P<body>.*?)'
    r'(?=<div class="tgme_widget_message(?:\s|")|\Z)',
    re.S,
)
_MESSAGE_TEXT_RE = re.compile(
    r'<div class="tgme_widget_message_text(?:\s[^"]*)?"[^>]*>(?P<text>.*?)'
    r"</div>",
    re.S,
)
_DATETIME_RE = re.compile(r'datetime="(?P<value>[^"]+)"')
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")


class ReceiptError(RuntimeError):
    """Raised when a public exposure receipt cannot be proved."""


class NonCountableSource(ReceiptError):
    """Raised when the triggering event can never mint a countable receipt."""


class PublicEvidenceError(ReceiptError):
    """Raised when re-fetched public evidence does not back the claim."""


@dataclasses.dataclass(frozen=True)
class PublicMessage:
    channel: str
    message_id: int
    evidence_url: str
    status: int
    text: str
    published_at: dt.datetime
    body_sha256: str


@dataclasses.dataclass(frozen=True)
class DigestEntry:
    """One publisher-reviewed app as it must appear in the public message."""

    app_key: str
    app_store_id: str
    app_name: str
    category: str
    canonical_app_store_url: str
    campaign_app_store_url: str
    entry_text: str


def disclosure_block() -> str:
    return "\n".join(DISCLOSURE_LINES)


def verify_disclosure(text: str) -> bool:
    """Every countable message must carry the full first-party disclosure."""
    if not isinstance(text, str):
        return False
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return all(line in normalized for line in DISCLOSURE_LINES)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _as_utc(value, label):
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = dt.datetime.fromisoformat(
                value.strip().replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ReceiptError(f"{label} is not an ISO-8601 instant") from error
    else:
        raise ReceiptError(f"{label} is missing")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _sha256(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def workflow_content_digest(paths=None, root=None) -> str:
    """Digest the exact publisher code + workflow that produced a receipt."""
    root = REPO_ROOT if root is None else Path(root)
    if paths is None:
        paths = (
            Path(".github") / "workflows" / PUBLISHER_WORKFLOW,
            Path(".github") / "scripts" / "portfolio_daily.py",
            Path(".github") / "scripts" / "telegram_public_receipts.py",
            Path(".github") / "scripts" / "social_post_common.py",
        )
    digest = hashlib.sha256()
    for relative in sorted(Path(item).as_posix() for item in paths):
        path = root / relative
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise ReceiptError(
                f"workflow content digest is missing {relative}"
            ) from error
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return f"sha256:{digest.hexdigest()}"


def source_context(env=None, *, content_digest=None):
    """Bind a receipt to a durable, re-checkable GitHub Actions source run.

    Raises ``NonCountableSource`` for any event that must never be counted,
    including a ``workflow_dispatch`` that really did publish a public message.
    """
    env = os.environ if env is None else env
    event = str(env.get("GITHUB_EVENT_NAME", "")).strip()
    if not event:
        raise NonCountableSource("no GITHUB_EVENT_NAME: not a workflow run")
    if event not in COUNTABLE_EVENTS:
        raise NonCountableSource(
            f"event {event!r} is never countable "
            f"(countable events: {sorted(COUNTABLE_EVENTS)})"
        )
    repository = str(env.get("GITHUB_REPOSITORY", "")).strip()
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is None:
        raise NonCountableSource(f"invalid GITHUB_REPOSITORY: {repository!r}")
    run_id = str(env.get("GITHUB_RUN_ID", "")).strip()
    if re.fullmatch(r"[0-9]{1,20}", run_id) is None:
        raise NonCountableSource(f"invalid GITHUB_RUN_ID: {run_id!r}")
    run_attempt = str(env.get("GITHUB_RUN_ATTEMPT", "")).strip() or "1"
    if re.fullmatch(r"[0-9]{1,6}", run_attempt) is None:
        raise NonCountableSource(
            f"invalid GITHUB_RUN_ATTEMPT: {run_attempt!r}"
        )
    workflow_sha = str(env.get("GITHUB_SHA", "")).strip()
    if re.fullmatch(r"[0-9a-f]{40}", workflow_sha) is None:
        raise NonCountableSource(f"invalid GITHUB_SHA: {workflow_sha!r}")
    workflow_ref = str(env.get("GITHUB_WORKFLOW_REF", "")).strip()
    server = str(
        env.get("GITHUB_SERVER_URL", "https://github.com")
    ).strip().rstrip("/")
    if not server.startswith("https://"):
        raise NonCountableSource(f"invalid GITHUB_SERVER_URL: {server!r}")
    if workflow_ref and not workflow_ref.startswith(f"{repository}/"):
        raise NonCountableSource(
            f"GITHUB_WORKFLOW_REF does not belong to {repository}"
        )
    if content_digest is None:
        content_digest = workflow_content_digest()
    return {
        "provider": "github_actions",
        "repository": repository,
        "workflow": PUBLISHER_WORKFLOW,
        "workflow_ref": workflow_ref or None,
        "event_name": event,
        "countable_event": True,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_url": f"{server}/{repository}/actions/runs/{run_id}",
        "run_attempt_url": (
            f"{server}/{repository}/actions/runs/{run_id}"
            f"/attempts/{run_attempt}"
        ),
        "workflow_sha": workflow_sha,
        "workflow_content_digest": content_digest,
    }


def public_message_url(channel, message_id):
    channel, message_id = _validate_target(channel, message_id)
    return PUBLIC_MESSAGE_URL.format(channel=channel, message_id=message_id)


def public_evidence_url(channel, message_id):
    channel, message_id = _validate_target(channel, message_id)
    return PUBLIC_EVIDENCE_URL.format(channel=channel, message_id=message_id)


def _validate_target(channel, message_id):
    channel = str(channel or "").strip()
    if CHANNEL_RE.fullmatch(channel) is None:
        raise ReceiptError(f"invalid public Telegram channel: {channel!r}")
    try:
        message_id = int(message_id)
    except (TypeError, ValueError) as error:
        raise ReceiptError(
            f"invalid public Telegram message id: {message_id!r}"
        ) from error
    if message_id <= 0:
        raise ReceiptError(
            f"invalid public Telegram message id: {message_id!r}"
        )
    return channel, message_id


def _plain_text(fragment: str) -> str:
    text = _BR_RE.sub("\n", fragment)
    text = _TAG_RE.sub("", text)
    return html_module.unescape(text).replace("\r\n", "\n").replace("\r", "\n")


def parse_public_message(body, channel, message_id, *, status=200,
                         evidence_url=None):
    """Extract the one public message we asked for, or fail closed."""
    channel, message_id = _validate_target(channel, message_id)
    evidence_url = evidence_url or public_evidence_url(channel, message_id)
    if not isinstance(body, str) or not body.strip():
        raise PublicEvidenceError(f"{evidence_url}: empty public body")
    if status != 200:
        raise PublicEvidenceError(
            f"{evidence_url}: unexpected public status {status}"
        )
    wanted = f"{channel}/{message_id}"
    blocks = [
        match
        for match in _MESSAGE_BLOCK_RE.finditer(body)
        if match.group("post") == wanted
    ]
    if len(blocks) != 1:
        raise PublicEvidenceError(
            f"{evidence_url}: expected exactly one {wanted} block, "
            f"found {len(blocks)}"
        )
    block = blocks[0]
    text_match = _MESSAGE_TEXT_RE.search(block.group("body"))
    if text_match is None:
        raise PublicEvidenceError(
            f"{evidence_url}: {wanted} has no public message text"
        )
    published = _DATETIME_RE.search(block.group("body"))
    if published is None:
        raise PublicEvidenceError(
            f"{evidence_url}: {wanted} has no public publication time"
        )
    return PublicMessage(
        channel=channel,
        message_id=message_id,
        evidence_url=evidence_url,
        status=status,
        text=_plain_text(text_match.group("text")).strip(),
        published_at=_as_utc(published.group("value"), "published_at"),
        body_sha256=_sha256(body),
    )


def fetch_public_message(
    channel,
    message_id,
    *,
    opener=None,
    sleeper=None,
    timeout=20,
    attempts=4,
    retry_delays=(3, 8, 15),
):
    """Re-fetch the public page. POST responses are never accepted as proof."""
    channel, message_id = _validate_target(channel, message_id)
    url = public_evidence_url(channel, message_id)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    try:
        response = request_text(
            request,
            label=f"Telegram public receipt {channel}/{message_id}",
            timeout=timeout,
            attempts=attempts,
            opener=opener,
            sleeper=sleeper,
            retry_delays=retry_delays,
        )
    except (HTTPStatusError, RequestError) as error:
        raise PublicEvidenceError(f"{url}: {error}") from error
    return parse_public_message(
        response.text,
        channel,
        message_id,
        status=response.status,
        evidence_url=url,
    )


def _validate_entries(entries):
    entries = list(entries)
    if not entries:
        raise ReceiptError("digest contains no publisher-reviewed apps")
    for entry in entries:
        if not isinstance(entry, DigestEntry):
            raise ReceiptError("digest entry has an unsupported type")
        if re.fullmatch(r"[0-9]{4,20}", entry.app_store_id) is None:
            raise ReceiptError(f"invalid App Store id: {entry.app_store_id!r}")
        if not entry.app_key.strip() or not entry.app_name.strip():
            raise ReceiptError(
                f"app {entry.app_store_id} has no publisher identity"
            )
        canonical = canonical_app_store_url(entry.canonical_app_store_url)
        if canonical != f"https://apps.apple.com/app/id{entry.app_store_id}":
            raise ReceiptError(
                f"canonical App Store URL mismatch for {entry.app_store_id}"
            )
        if not entry.campaign_app_store_url.startswith(f"{canonical}?"):
            raise ReceiptError(
                f"campaign App Store URL mismatch for {entry.app_store_id}"
            )
        if entry.campaign_app_store_url not in entry.entry_text:
            raise ReceiptError(
                f"digest entry for {entry.app_store_id} omits its own link"
            )
    return entries


def verify_publication(
    shards,
    *,
    expected_entries,
    channel=TELEGRAM_PUBLIC_CHANNEL,
    source,
    observed_at=None,
    source_started_at=None,
    fetcher=None,
):
    """Prove every app of a multi-message digest from public evidence only.

    ``shards`` maps a public message id to the ordered entries claimed for it.
    """
    expected_entries = _validate_entries(expected_entries)
    if not isinstance(source, dict) or not source.get("countable_event"):
        raise NonCountableSource("receipt source is not a countable event")
    observed_at = utc_now() if observed_at is None else _as_utc(
        observed_at, "observed_at"
    )
    source_started_at = (
        observed_at
        if source_started_at is None
        else _as_utc(source_started_at, "source_started_at")
    )
    fetcher = fetch_public_message if fetcher is None else fetcher

    by_id = {entry.app_store_id: entry for entry in expected_entries}
    if len(by_id) != len(expected_entries):
        raise ReceiptError("digest claims the same App Store id twice")
    if not shards:
        raise ReceiptError("digest published no public messages")

    ordered_ids = sorted(shards)
    claimed = [
        entry.app_store_id
        for message_id in ordered_ids
        for entry in shards[message_id]
    ]
    missing, unexpected, duplicated = coverage_diff(list(by_id), claimed)
    if missing or unexpected or duplicated:
        raise ReceiptError(
            "digest shards do not cover every app exactly once: "
            f"missing={missing}, unexpected={unexpected}, "
            f"duplicated={duplicated}"
        )

    message_count = len(ordered_ids)
    receipts = []
    proved = []
    for index, message_id in enumerate(ordered_ids, start=1):
        message = fetcher(channel, message_id)
        if message.status != 200:
            raise PublicEvidenceError(
                f"{message.evidence_url}: status {message.status}"
            )
        if message.published_at > observed_at:
            raise PublicEvidenceError(
                f"{message.evidence_url}: publication time is in the future"
            )
        if observed_at - message.published_at > FRESHNESS_WINDOW:
            raise PublicEvidenceError(
                f"{message.evidence_url}: publication is older than "
                f"{FRESHNESS_WINDOW}"
            )
        if message.published_at < source_started_at - SOURCE_START_SLACK:
            raise PublicEvidenceError(
                f"{message.evidence_url}: publication predates source run "
                f"{source.get('run_id')}"
            )
        if not verify_disclosure(message.text):
            raise PublicEvidenceError(
                f"{message.evidence_url}: first-party commercial disclosure "
                "is missing from the public message"
            )
        for entry in shards[message_id]:
            if entry.entry_text not in message.text:
                raise PublicEvidenceError(
                    f"{message.evidence_url}: public body does not contain "
                    f"the exact entry for {entry.app_store_id}"
                )
            if message.text.count(entry.campaign_app_store_url) != 1:
                raise PublicEvidenceError(
                    f"{message.evidence_url}: campaign URL for "
                    f"{entry.app_store_id} is missing or repeated"
                )
            proved.append(entry.app_store_id)
            receipts.append(
                _build_receipt(
                    entry=entry,
                    message=message,
                    message_index=index,
                    message_count=message_count,
                    source=source,
                    observed_at=observed_at,
                )
            )
    missing, unexpected, duplicated = coverage_diff(list(by_id), proved)
    if missing or unexpected or duplicated:
        raise PublicEvidenceError(
            "public evidence does not prove every app exactly once: "
            f"missing={missing}, unexpected={unexpected}, "
            f"duplicated={duplicated}"
        )
    return receipts


def _receipt_id(channel, message_id, app_store_id, source):
    seed = "|".join(
        (
            CONTRACT_ID,
            str(SCHEMA_VERSION),
            channel,
            str(message_id),
            app_store_id,
            str(source.get("repository")),
            str(source.get("run_id")),
            str(source.get("run_attempt")),
        )
    )
    return _sha256(seed)


def _build_receipt(*, entry, message, message_index, message_count, source,
                   observed_at):
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_ID,
        "receipt_id": _receipt_id(
            message.channel, message.message_id, entry.app_store_id, source
        ),
        "countable": True,
        "app": {
            "app_key": entry.app_key,
            "app_store_id": entry.app_store_id,
            "app_name": entry.app_name,
            "canonical_app_store_url": entry.canonical_app_store_url,
            "campaign_app_store_url": entry.campaign_app_store_url,
            "locale": DIGEST_LOCALE,
            "intent": entry.category,
        },
        "publication": {
            "network": "telegram",
            "channel": message.channel,
            "message_id": message.message_id,
            "message_url": public_message_url(
                message.channel, message.message_id
            ),
            "message_index": message_index,
            "message_count": message_count,
            "published_at": _iso(message.published_at),
            "publication_day": message.published_at.date().isoformat(),
        },
        "source": copy.deepcopy(source),
        "public_check": {
            "method": "GET",
            "url": message.evidence_url,
            "status": message.status,
            "observed_at": _iso(observed_at),
            "freshness_seconds": int(
                (observed_at - message.published_at).total_seconds()
            ),
            "body_sha256": message.body_sha256,
            "app_entry_verified": True,
            "campaign_url_verified": True,
            "disclosure_verified": True,
        },
    }


def _failure_record(*, reason, source, observed_at, channel, message_ids):
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_ID,
        "countable": False,
        "reason": str(reason)[:500],
        "observed_at": _iso(observed_at),
        "channel": channel,
        "message_ids": [int(item) for item in sorted(message_ids)],
        "source": copy.deepcopy(source) if isinstance(source, dict) else None,
    }


def dump_pending(path, receipts_batch, failures=(), *, now=None, env=None):
    """Persist newly minted proof outside the repo tree for the commit step.

    The commit step merges this into the store *after* every remote-first
    integration, so a concurrent writer on ``main`` can never silently drop a
    receipt through a ``-X theirs`` conflict resolution.
    """
    now = utc_now() if now is None else _as_utc(now, "now")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_ID,
        "created_at": _iso(now),
        "receipts": list(receipts_batch),
        "non_countable": list(failures),
    }
    path = Path(path)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    assert_no_credentials(encoded, env=env)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(encoded + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


def load_pending(path):
    path = Path(path)
    if not path.is_file():
        return {"receipts": [], "non_countable": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReceiptError(f"pending receipts are unreadable: {path}") from error
    if not isinstance(payload, dict):
        raise ReceiptError(f"pending receipts are not an object: {path}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ReceiptError(
            f"unsupported pending schema_version "
            f"{payload.get('schema_version')!r}"
        )
    if payload.get("contract") != CONTRACT_ID:
        raise ReceiptError(f"pending receipts are not {CONTRACT_ID}")
    for field in ("receipts", "non_countable"):
        if not isinstance(payload.get(field), list):
            raise ReceiptError(f"pending receipts have an invalid {field}")
    return payload


def merge_pending(store_path, pending_path, *, now=None, env=None):
    """Idempotently fold a pending batch into the committed public store."""
    pending = load_pending(pending_path)
    store = load_store(store_path)
    merged = merge_receipts(
        store,
        pending.get("receipts", []),
        failures=pending.get("non_countable", []),
        now=now,
    )
    write_store(merged, store_path, env=env)
    return merged


def empty_store(now=None):
    now = utc_now() if now is None else _as_utc(now, "now")
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_ID,
        "generator": GENERATOR,
        "public_url": PUBLIC_STORE_URL,
        "schema_url": PUBLIC_SCHEMA_URL,
        "note": STORE_NOTE,
        "countable_events": sorted(COUNTABLE_EVENTS),
        "freshness_window_hours": int(
            FRESHNESS_WINDOW.total_seconds() // 3600
        ),
        "retention": {
            "max_publication_days": MAX_PUBLICATION_DAYS,
            "max_receipts": MAX_RECEIPTS,
            "max_failures": MAX_FAILURES,
        },
        "updated_at": _iso(now),
        "receipts": [],
        "non_countable": [],
    }


def load_store(path=STORE_PATH):
    path = Path(path)
    if not path.is_file():
        return empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReceiptError(f"receipt store is unreadable: {path}") from error
    if not isinstance(payload, dict):
        raise ReceiptError(f"receipt store is not an object: {path}")
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ReceiptError(
            f"unsupported receipt schema_version {version!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if payload.get("contract") != CONTRACT_ID:
        raise ReceiptError(f"receipt store is not {CONTRACT_ID}")
    for field in ("receipts", "non_countable"):
        if not isinstance(payload.get(field), list):
            raise ReceiptError(f"receipt store has an invalid {field} array")
    return payload


def _prune(receipts):
    days = sorted(
        {
            str(item.get("publication", {}).get("publication_day"))
            for item in receipts
        },
        reverse=True,
    )
    keep_days = set(days[:MAX_PUBLICATION_DAYS])
    kept = [
        item
        for item in receipts
        if str(item.get("publication", {}).get("publication_day")) in keep_days
    ]
    kept.sort(
        key=lambda item: (
            str(item.get("publication", {}).get("published_at")),
            int(item.get("publication", {}).get("message_id") or 0),
            str(item.get("app", {}).get("app_store_id")),
        )
    )
    return kept[-MAX_RECEIPTS:]


def merge_receipts(store, receipts, *, failures=(), now=None):
    """Idempotently fold new receipts into the bounded store."""
    now = utc_now() if now is None else _as_utc(now, "now")
    merged = copy.deepcopy(store)
    merged["schema_version"] = SCHEMA_VERSION
    merged["contract"] = CONTRACT_ID
    merged["generator"] = GENERATOR
    merged["public_url"] = PUBLIC_STORE_URL
    merged["schema_url"] = PUBLIC_SCHEMA_URL
    merged["note"] = STORE_NOTE
    merged["countable_events"] = sorted(COUNTABLE_EVENTS)
    merged["freshness_window_hours"] = int(
        FRESHNESS_WINDOW.total_seconds() // 3600
    )
    merged["retention"] = {
        "max_publication_days": MAX_PUBLICATION_DAYS,
        "max_receipts": MAX_RECEIPTS,
        "max_failures": MAX_FAILURES,
    }

    existing = {
        str(item.get("receipt_id")): item
        for item in merged.get("receipts", [])
    }
    added = 0
    for receipt in receipts:
        receipt_id = str(receipt.get("receipt_id"))
        if not receipt_id or receipt_id == "None":
            raise ReceiptError("receipt is missing a receipt_id")
        # A re-run must not restate an existing proof with a fresher timestamp,
        # otherwise every replay would rewrite the public store.
        if receipt_id in existing:
            continue
        existing[receipt_id] = receipt
        added += 1
    merged["receipts"] = _prune(list(existing.values()))

    if failures:
        history = list(merged.get("non_countable", []))
        known = {json.dumps(item, sort_keys=True) for item in history}
        for failure in failures:
            encoded = json.dumps(failure, sort_keys=True)
            if encoded in known:
                continue
            known.add(encoded)
            history.append(failure)
        merged["non_countable"] = history[-MAX_FAILURES:]
    else:
        merged["non_countable"] = list(merged.get("non_countable", []))[
            -MAX_FAILURES:
        ]

    merged["countable_receipt_count"] = len(merged["receipts"])
    merged["countable_app_count"] = len(
        {
            str(item.get("app", {}).get("app_store_id"))
            for item in merged["receipts"]
        }
    )
    if added or failures or not store.get("updated_at"):
        merged["updated_at"] = _iso(now)
    return merged


def assert_no_credentials(payload, env=None, channel=TELEGRAM_PUBLIC_CHANNEL):
    """A public receipt store must never leak the bot token or chat id."""
    env = os.environ if env is None else env
    encoded = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, ensure_ascii=False)
    )
    # TELEGRAM_CHAT_ID is often the already-public @handle. The handle is
    # published verbatim on the site, so only a genuinely private chat id
    # (a numeric peer id) counts as a credential leak.
    public_aliases = {channel.casefold(), f"@{channel}".casefold()}
    for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GITHUB_TOKEN"):
        secret = str(env.get(name, "")).strip()
        if not secret or len(secret) < 8 or secret.casefold() in public_aliases:
            continue
        if secret in encoded:
            raise ReceiptError(
                f"receipt store would publish the {name} secret"
            )
    if re.search(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b", encoded):
        raise ReceiptError("receipt store contains a Telegram bot token")
    return True


def serialize(store):
    return json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_store(store, path=STORE_PATH, *, env=None):
    """Atomically replace the store; a torn file must never become evidence."""
    path = Path(path)
    payload = serialize(store)
    assert_no_credentials(payload, env=env)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return path


def record_publication(
    shards,
    *,
    expected_entries,
    channel=TELEGRAM_PUBLIC_CHANNEL,
    env=None,
    store_path=STORE_PATH,
    pending_path=None,
    observed_at=None,
    source_started_at=None,
    fetcher=None,
    now=None,
):
    """Verify a fresh publication publicly and durably store its receipts.

    Returns ``(store, receipts)``. Raises ``NonCountableSource`` when the
    trigger can never count, and ``PublicEvidenceError`` when public evidence
    is unavailable or does not match — never a partial success.
    """
    env = os.environ if env is None else env
    observed_at = utc_now() if observed_at is None else _as_utc(
        observed_at, "observed_at"
    )
    if pending_path is None:
        pending_path = str(env.get("TELEGRAM_RECEIPT_PENDING", "")).strip() or None
    source = source_context(env)
    store = load_store(store_path)
    try:
        receipts = verify_publication(
            shards,
            expected_entries=expected_entries,
            channel=channel,
            source=source,
            observed_at=observed_at,
            source_started_at=source_started_at,
            fetcher=fetcher,
        )
    except ReceiptError as error:
        failure = _failure_record(
            reason=error,
            source=source,
            observed_at=observed_at,
            channel=channel,
            message_ids=list(shards),
        )
        if pending_path:
            dump_pending(
                pending_path, [], [failure], now=now or observed_at, env=env
            )
        write_store(
            merge_receipts(store, [], failures=[failure], now=now or observed_at),
            store_path,
            env=env,
        )
        raise
    if pending_path:
        dump_pending(
            pending_path, receipts, (), now=now or observed_at, env=env
        )
    merged = merge_receipts(store, receipts, now=now or observed_at)
    write_store(merged, store_path, env=env)
    return merged, receipts


def _cli_summary(store):
    receipts = store.get("receipts", [])
    days = sorted(
        {
            str(item.get("publication", {}).get("publication_day"))
            for item in receipts
        }
    )
    print(
        "TELEGRAM_PUBLIC_RECEIPTS "
        f"receipts={len(receipts)} "
        f"apps={store.get('countable_app_count', 0)} "
        f"days={len(days)} "
        f"latest_day={days[-1] if days else 'none'} "
        f"non_countable={len(store.get('non_countable', []))}"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or re-verify the public Telegram exposure receipt store."
        )
    )
    parser.add_argument("--store", default=str(STORE_PATH))
    parser.add_argument(
        "--merge-pending",
        default=None,
        help=(
            "Fold a run-scoped pending batch into the committed store. Safe to "
            "repeat after every remote-first integration attempt."
        ),
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a machine-readable one-line summary and exit.",
    )
    parser.add_argument(
        "--require-fresh-day",
        action="store_true",
        help=(
            "Exit non-zero unless a countable receipt exists for every app "
            "inside the freshness window."
        ),
    )
    parser.add_argument(
        "--expected-apps",
        type=int,
        default=0,
        help="Expected number of distinct apps for --require-fresh-day.",
    )
    args = parser.parse_args(argv)
    try:
        store = load_store(args.store)
        assert_no_credentials(store)
        if args.merge_pending:
            store = merge_pending(args.store, args.merge_pending)
        _cli_summary(store)
        if args.require_fresh_day:
            now = utc_now()
            fresh = {
                str(item.get("app", {}).get("app_store_id"))
                for item in store.get("receipts", [])
                if item.get("countable")
                and now - _as_utc(
                    item.get("publication", {}).get("published_at"),
                    "published_at",
                )
                <= FRESHNESS_WINDOW
            }
            if args.expected_apps and len(fresh) != args.expected_apps:
                print(
                    "no fresh countable Telegram exposure for every app: "
                    f"{len(fresh)}/{args.expected_apps}",
                    file=sys.stderr,
                )
                return 1
        return 0
    except ReceiptError as error:
        print(f"Telegram public receipts failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
