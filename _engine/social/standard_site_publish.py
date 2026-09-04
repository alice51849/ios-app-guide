#!/usr/bin/env python3
"""Idempotently publish a low-frequency Standard.site AT Protocol index.

The default is check-only: no authentication, network request, state write, or
artifact write occurs. ``--publish`` is the only mode that mutates anything.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any, Callable, Iterator, Mapping, MutableMapping, Sequence
import urllib.error
from urllib.parse import urlencode, urlsplit

from gen_standard_site import (
    DEFAULT_OUTPUT as DEFAULT_MANIFEST,
    ManifestError,
    PRIVATE_DIR,
    atomic_write_text,
    validate_manifest,
)
from standard_site_attribution import (
    attribution_status,
    legacy_document_content_hash,
    legacy_text_content,
)
import standard_site_pending as pending_state


STATE_VERSION = 1
PUBLICATION_COLLECTION = "site.standard.publication"
DOCUMENT_COLLECTION = "site.standard.document"
TID_ALPHABET = "234567abcdefghijklmnopqrstuvwxyz"
TID_RE = re.compile(r"^[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}$")
AT_URI_RE = re.compile(
    r"^at://(did:[a-z0-9]+:[A-Za-z0-9._:%-]+)/"
    r"(site\.standard\.(?:publication|document))/"
    r"([234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12})$"
)
EXPECTED_PUBLISHER_DID = "did:plc:kboucnzkxzmqmatvhes4xlt4"
PUBLICATION_URL_MIGRATIONS = {
    "https://alice51849.github.io/ios-app-guide": (
        "https://open.cait518.cc/ios-app-guide"
    ),
}
DEFAULT_STATE = PRIVATE_DIR / "standard-site-state.json"
DEFAULT_CONTRACT = PRIVATE_DIR / "standard-site-guide-contract.json"
DEFAULT_WELL_KNOWN = PRIVATE_DIR / "site.standard.publication"
DEFAULT_DAILY_LIMIT = int(os.environ.get("STANDARD_SITE_DAILY_LIMIT", "2"))
LOCK_SUFFIX = ".lock"
MAX_REMOTE_RECORDS = 5_000
READ_RETRY_ATTEMPTS = 4
READ_RETRY_BASE_SECONDS = 1.0
READ_RETRY_MAX_SECONDS = 8.0
READ_RETRY_TOTAL_WAIT_SECONDS = 20.0
ATTRIBUTION_REPAIR_REASON = pending_state.ATTRIBUTION_REPAIR_REASON
ATTRIBUTION_REPAIR_FIELDS = pending_state.ATTRIBUTION_REPAIR_FIELDS
ATTRIBUTION_REPAIR_BACKLOG_FIELD = (
    pending_state.ATTRIBUTION_REPAIR_BACKLOG_FIELD
)
ORDINARY_REPUBLISH_REASON = pending_state.ORDINARY_REPUBLISH_REASON
ORDINARY_REPUBLISH_FIELDS = pending_state.ORDINARY_REPUBLISH_FIELDS
PENDING_POLICY_FIELD = pending_state.PENDING_POLICY_FIELD
PENDING_MIGRATION_FIELD = pending_state.PENDING_MIGRATION_FIELD
PENDING_WINDOW_FIELD = pending_state.PENDING_WINDOW_FIELD
PENDING_LIFECYCLE_FIELD = pending_state.PENDING_LIFECYCLE_FIELD


class ConfigurationError(RuntimeError):
    """Publishing configuration is missing or points at the wrong identity."""


class StateError(RuntimeError):
    """Durable publisher state is corrupt or inconsistent."""


class PublishError(RuntimeError):
    """An AT Protocol record could not be safely reconciled."""


def _transient_read_error(error: BaseException) -> bool:
    if isinstance(error, urllib.error.HTTPError):
        return error.code in {408, 429} or 500 <= error.code <= 599
    return isinstance(
        error,
        (urllib.error.URLError, TimeoutError, OSError),
    )


def _retry_after_seconds(
    error: BaseException,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> float | None:
    if not isinstance(error, urllib.error.HTTPError):
        return None
    headers = getattr(error, "headers", None)
    raw = headers.get("Retry-After") if headers is not None else None
    if raw is None:
        return None
    try:
        seconds = float(str(raw).strip())
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at - now().astimezone(timezone.utc)).total_seconds()
    return max(0.0, seconds)


def read_with_retry(
    operation: Callable[[], Any],
    *,
    sleeper: Callable[[float], None] = time.sleep,
    attempts: int = READ_RETRY_ATTEMPTS,
    base_delay: float = READ_RETRY_BASE_SECONDS,
    max_delay: float = READ_RETRY_MAX_SECONDS,
    max_total_wait: float = READ_RETRY_TOTAL_WAIT_SECONDS,
    wait_budget: list[float] | None = None,
) -> Any:
    """Retry a pure ATProto read only, within one shared bounded wait budget."""
    if (
        attempts < 1
        or base_delay < 0
        or max_delay < 0
        or max_total_wait < 0
    ):
        raise ValueError("Invalid ATProto read retry policy")
    budget = wait_budget if wait_budget is not None else [0.0]
    if len(budget) != 1 or budget[0] < 0:
        raise ValueError("Invalid ATProto read retry budget")
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:
            if attempt + 1 >= attempts or not _transient_read_error(error):
                raise
            remaining = max_total_wait - budget[0]
            if remaining <= 0:
                raise
            backoff = min(base_delay * (2**attempt), max_delay)
            retry_after = _retry_after_seconds(error)
            requested = max(backoff, retry_after or 0.0)
            if requested <= 0 or requested > remaining:
                raise
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            sleeper(requested)
            budget[0] += requested
    raise AssertionError("ATProto read retry loop exited unexpectedly")


def utc_timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (
        current.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def parse_timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise StateError(f"Invalid RFC 3339 timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise StateError(f"Timestamp must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def encode_tid(value: int) -> str:
    if not 0 <= value < (1 << 63):
        raise ValueError("TID integer must fit in 63 bits")
    characters = []
    for _ in range(13):
        characters.append(TID_ALPHABET[value & 0x1F])
        value >>= 5
    tid = "".join(reversed(characters))
    if not TID_RE.fullmatch(tid):
        raise ValueError(f"Generated invalid TID: {tid}")
    return tid


def decode_tid(value: str) -> int:
    if not TID_RE.fullmatch(value):
        raise ValueError(f"Invalid TID: {value!r}")
    decoded = 0
    for character in value:
        decoded = (decoded << 5) | TID_ALPHABET.index(character)
    if decoded >= (1 << 63):
        raise ValueError(f"TID has its top bit set: {value!r}")
    return decoded


class TIDGenerator:
    """Generate legal, monotonic timestamp identifiers without URL hashing."""

    def __init__(
        self,
        *,
        clock_us: Callable[[], int] | None = None,
        random_clock_id: Callable[[], int] | None = None,
    ) -> None:
        self.clock_us = clock_us or (lambda: time.time_ns() // 1_000)
        self.random_clock_id = random_clock_id or (
            lambda: secrets.randbelow(1 << 10)
        )

    def new(self, existing: Sequence[str] = ()) -> str:
        floor = max((decode_tid(value) for value in existing), default=-1)
        timestamp_us = int(self.clock_us())
        if not 0 <= timestamp_us < (1 << 53):
            raise ValueError("TID timestamp is outside the 53-bit range")
        clock_id = int(self.random_clock_id())
        if not 0 <= clock_id < (1 << 10):
            raise ValueError("TID clock identifier is outside the 10-bit range")
        candidate = (timestamp_us << 10) | clock_id
        if candidate <= floor:
            candidate = floor + 1
        return encode_tid(candidate)


def empty_state() -> dict[str, object]:
    return {
        "version": STATE_VERSION,
        "publication": {},
        "documents": {},
        "daily": {},
        "rotation": {"last_app": ""},
    }


def validate_state(state: Mapping[str, object]) -> None:
    if state.get("version") != STATE_VERSION:
        raise StateError("Unsupported Standard.site state version")
    for field in ("publication", "documents", "daily", "rotation"):
        if not isinstance(state.get(field), Mapping):
            raise StateError(f"State field must be an object: {field}")
    try:
        pending_state.validate_pending_policy(state)
    except pending_state.PendingStateError as error:
        raise StateError(str(error)) from error
    publication = state["publication"]
    if publication.get("rkey") and not TID_RE.fullmatch(
        str(publication["rkey"])
    ):
        raise StateError("Publication state contains an invalid TID")
    documents = state["documents"]
    for canonical, entry in documents.items():
        if not isinstance(canonical, str) or not canonical.startswith("https://"):
            raise StateError("Document state contains an invalid canonical URL")
        if not isinstance(entry, Mapping):
            raise StateError(f"Invalid document state for {canonical}")
        if entry.get("rkey") and not TID_RE.fullmatch(str(entry["rkey"])):
            raise StateError(f"Document state contains an invalid TID: {canonical}")
        if entry.get("published_at"):
            parse_timestamp(entry["published_at"])
        try:
            pending_state.validate_pending_entry(
                entry, label=canonical
            )
        except pending_state.PendingStateError as error:
            raise StateError(str(error)) from error
    try:
        pending_state.validate_pending_state(
            state, require_finalized=False
        )
    except pending_state.PendingStateError as error:
        raise StateError(str(error)) from error
    for day_value, entry in state["daily"].items():
        try:
            date.fromisoformat(str(day_value))
        except ValueError as error:
            raise StateError(f"Invalid daily state date: {day_value}") from error
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("selected_urls"), list)
            or len(entry["selected_urls"]) > 4
            or len(entry["selected_urls"]) != len(set(entry["selected_urls"]))
        ):
            raise StateError(f"Invalid daily selection state: {day_value}")


def load_state(path: Path) -> dict[str, object]:
    path = Path(path)
    if not path.exists():
        return empty_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StateError(f"Cannot read healthy state: {path}") from error
    if not isinstance(payload, dict):
        raise StateError("Standard.site state root must be an object")
    validate_state(payload)
    return payload


def atomic_write_json(
    path: Path, payload: Mapping[str, object], mode: int = 0o600
) -> None:
    validate_state(payload)
    atomic_write_text(
        Path(path),
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        mode=mode,
    )


@contextmanager
def publisher_lock(state_path: Path) -> Iterator[None]:
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(state_path.name + LOCK_SUFFIX)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise StateError("Another Standard.site publisher is already running") from error
        acquired = True
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _all_rkeys(state: Mapping[str, object]) -> list[str]:
    result: list[str] = []
    publication = state["publication"]
    if publication.get("rkey"):
        result.append(str(publication["rkey"]))
    for entry in state["documents"].values():
        if isinstance(entry, Mapping) and entry.get("rkey"):
            result.append(str(entry["rkey"]))
    return result


def migrate_publication_origin(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
) -> str | None:
    """Move the one approved origin without changing AT record identities."""
    validate_state(state)
    publication = state["publication"]
    target = str(manifest["publication"]["url"])
    configured = str(publication.get("canonical_url") or "")
    if not configured or configured == target:
        return None
    if PUBLICATION_URL_MIGRATIONS.get(configured) != target:
        raise StateError(
            "Publication URL changed; explicit migration is required"
        )

    def remap(canonical: object, label: str) -> str:
        value = str(canonical)
        if value.startswith(configured + "/"):
            return target + value[len(configured) :]
        if value.startswith(target + "/"):
            return value
        raise StateError(
            f"{label} is outside the approved publication migration"
        )

    remapped_documents: dict[str, object] = {}
    for canonical, entry in state["documents"].items():
        migrated = remap(canonical, "Document canonical URL")
        if migrated in remapped_documents:
            raise StateError(
                "Publication migration would collide document identities"
            )
        remapped_documents[migrated] = entry

    remapped_daily: dict[str, object] = {}
    for day, raw_entry in state["daily"].items():
        if not isinstance(raw_entry, Mapping):
            raise StateError(f"Invalid daily selection state: {day}")
        selected = raw_entry.get("selected_urls")
        if not isinstance(selected, list):
            raise StateError(f"Invalid daily selection state: {day}")
        migrated_urls = [
            remap(canonical, "Daily canonical URL") for canonical in selected
        ]
        if len(migrated_urls) != len(set(migrated_urls)):
            raise StateError(
                f"Publication migration would collide daily URLs: {day}"
            )
        entry = dict(raw_entry)
        entry["selected_urls"] = migrated_urls
        remapped_daily[str(day)] = entry

    state["documents"] = remapped_documents
    state["daily"] = remapped_daily
    publication["canonical_url"] = target
    validate_state(state)
    return configured


def allocate_rkeys(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    generator: TIDGenerator,
) -> bool:
    """Persistently map the publication and every canonical URL to first TIDs."""
    changed = False
    migrated_from = migrate_publication_origin(state, manifest)
    changed = migrated_from is not None
    publication = state["publication"]
    publication_url = str(manifest["publication"]["url"])
    configured_url = publication.get("canonical_url")
    if configured_url and configured_url != publication_url:
        raise StateError(
            "Publication URL changed; explicit migration is required"
        )
    if not publication.get("rkey"):
        publication["rkey"] = generator.new(_all_rkeys(state))
        changed = True
    if publication.get("canonical_url") != publication_url:
        publication["canonical_url"] = publication_url
        changed = True

    documents = state["documents"]
    for document in manifest["documents"]:
        canonical = str(document["canonical_url"])
        entry = documents.setdefault(canonical, {})
        if not isinstance(entry, MutableMapping):
            raise StateError(f"Invalid document state for {canonical}")
        configured_app = entry.get("app_key")
        if configured_app and configured_app != document["app_key"]:
            raise StateError(
                f"Canonical URL moved between apps: {canonical}"
            )
        if not entry.get("rkey"):
            entry["rkey"] = generator.new(_all_rkeys(state))
            changed = True
        if entry.get("app_key") != document["app_key"]:
            entry["app_key"] = document["app_key"]
            changed = True
    validate_state(state)
    return changed


def _document_map(
    manifest: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    return {
        str(document["canonical_url"]): document
        for document in manifest["documents"]
    }


def _pending(
    document: Mapping[str, object], state: Mapping[str, object]
) -> bool:
    entry = state["documents"].get(document["canonical_url"], {})
    if not entry.get("published"):
        return True
    return attribution_status(
        document, entry.get("published_hash")
    ) == "stale"


def _repair_deferred(entry: Mapping[str, object], day: str) -> bool:
    repair_after_day = entry.get("repair_after_day")
    return (
        entry.get("repair_reason") == ATTRIBUTION_REPAIR_REASON
        and repair_after_day is not None
        and day <= str(repair_after_day)
    )


def _pending_priority(
    entry: Mapping[str, object], canonical_url: str
) -> tuple[str, str, str]:
    detected_at = pending_state.pending_detected_at(entry)
    return (
        str(pending_state.pending_cohort_day(entry) or ""),
        str(detected_at or entry.get("published_at") or ""),
        canonical_url,
    )


def _finalize_pending_backlogs(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    *,
    limit: int,
    updated_at: str,
) -> None:
    try:
        pending_state.finalize_pending_windows(
            state,
            manifest,
            daily_limit=limit,
            updated_at=updated_at,
        )
    except pending_state.PendingStateError as error:
        raise StateError(str(error)) from error


def _migrate_legacy_pending_state(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    *,
    limit: int,
    migrated_at: str,
) -> None:
    try:
        pending_state.migrate_legacy_pending_windows(
            state,
            manifest,
            daily_limit=limit,
            migrated_at=migrated_at,
        )
    except pending_state.PendingStateError as error:
        raise StateError(str(error)) from error


def reserve_daily_batch(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    *,
    day: str,
    limit: int,
    now: str,
) -> list[Mapping[str, object]]:
    """Reserve at most one document per app and reuse it on same-day retries."""
    if type(limit) is not int or not 1 <= limit <= 4:
        raise ConfigurationError("Daily document limit must be between 1 and 4")
    try:
        current_day = date.fromisoformat(day)
    except ValueError as error:
        raise ConfigurationError(f"Invalid publishing date: {day}") from error
    documents = _document_map(manifest)
    daily = state["daily"]
    existing = daily.get(day)
    if existing is not None:
        urls = existing["selected_urls"]
        missing = [url for url in urls if url not in documents]
        if missing:
            raise StateError(
                f"Reserved documents disappeared from manifest: {missing}"
            )
        selected = [
            documents[url]
            for url in urls
            if attribution_status(
                documents[url],
                state["documents"][url].get("published_hash"),
            )
            != "legacy_unattributed"
            and not _repair_deferred(state["documents"][url], day)
        ]
    else:
        eligible: list[Mapping[str, object]] = []
        for document in manifest["documents"]:
            entry = state["documents"][document["canonical_url"]]
            if _pending(document, state) and not _repair_deferred(entry, day):
                eligible.append(document)
        cohorts: dict[str, list[Mapping[str, object]]] = {}
        for document in eligible:
            entry = state["documents"][document["canonical_url"]]
            cohort = (
                pending_state.pending_cohort_day(entry)
                if pending_state.pending_kind(entry) is not None
                else None
            )
            cohorts.setdefault(str(cohort or "~new"), []).append(document)
        last_app = str(state["rotation"].get("last_app") or "")
        selected = []
        selected_apps: set[str] = set()
        for cohort in sorted(cohorts):
            pending: dict[str, list[Mapping[str, object]]] = {}
            for document in cohorts[cohort]:
                app_key = str(document["app_key"])
                if app_key not in selected_apps:
                    pending.setdefault(app_key, []).append(document)
            app_keys = sorted(pending)
            if last_app in app_keys:
                split = app_keys.index(last_app) + 1
                app_keys = app_keys[split:] + app_keys[:split]
            for app_key in app_keys:
                candidates = sorted(
                    pending[app_key],
                    key=lambda value: _pending_priority(
                        state["documents"][value["canonical_url"]],
                        str(value["canonical_url"]),
                    ),
                )
                selected.append(candidates[0])
                selected_apps.add(app_key)
                if len(selected) >= limit:
                    break
            if len(selected) >= limit:
                break
        urls = [str(document["canonical_url"]) for document in selected]
        if selected:
            daily[day] = {"selected_urls": urls, "created_at": now}
            state["rotation"]["last_app"] = selected[-1]["app_key"]

    for document in selected:
        entry = state["documents"][document["canonical_url"]]
        entry.setdefault("published_at", now)
        if (
            entry.get("published") is not True
            and pending_state.pending_kind(entry) is None
        ):
            _mark_ordinary_republish_pending(
                entry,
                detected_at=now,
                republish_after_day=day,
            )

    cutoff = current_day - timedelta(days=90)
    for old_day in list(daily):
        if date.fromisoformat(old_day) < cutoff:
            del daily[old_day]
    _finalize_pending_backlogs(
        state, manifest, limit=limit, updated_at=now
    )
    validate_state(state)
    return selected


def publication_at_uri(did: str, rkey: str) -> str:
    uri = f"at://{did}/{PUBLICATION_COLLECTION}/{rkey}"
    validate_at_uri(uri, PUBLICATION_COLLECTION)
    return uri


def document_at_uri(did: str, rkey: str) -> str:
    uri = f"at://{did}/{DOCUMENT_COLLECTION}/{rkey}"
    validate_at_uri(uri, DOCUMENT_COLLECTION)
    return uri


def validate_at_uri(uri: str, collection: str) -> None:
    match = AT_URI_RE.fullmatch(uri)
    if not match or match.group(2) != collection:
        raise StateError(f"Invalid {collection} AT-URI: {uri!r}")


def publication_record(manifest: Mapping[str, object]) -> dict[str, object]:
    source = manifest["publication"]
    return {
        "$type": PUBLICATION_COLLECTION,
        "url": source["url"],
        "name": source["name"],
        "description": source["description"],
        "preferences": dict(source.get("preferences") or {}),
    }


def document_record(
    document: Mapping[str, object],
    publication_uri: str,
    entry: Mapping[str, object],
) -> dict[str, object]:
    published_at = str(entry.get("published_at") or "")
    parse_timestamp(published_at)
    return {
        "$type": DOCUMENT_COLLECTION,
        "site": publication_uri,
        "path": document["path"],
        "title": document["title"],
        "description": document["description"],
        "textContent": document["text_content"],
        "tags": list(document["tags"]),
        "publishedAt": published_at,
    }


def legacy_document_record(
    document: Mapping[str, object],
    publication_uri: str,
    entry: Mapping[str, object],
) -> dict[str, object]:
    record = document_record(document, publication_uri, entry)
    record["textContent"] = legacy_text_content(
        str(document["text_content"]),
        app_id=str(document["app_store_id"]),
        mode=str(document["legacy_app_store_link"]),
    )
    return record


def record_hash(record: Mapping[str, object]) -> str:
    encoded = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ExistingBlueskyRepoClient:
    """Generic repo writes over the already-maintained Bluesky login helper."""

    def __init__(
        self,
        handle: str,
        password: str,
        helper_path: Path,
        *,
        read_sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        helper_path = Path(helper_path)
        parent = str(helper_path.parent)
        module_name = "_growth_standard_site_multi_post"
        spec = importlib.util.spec_from_file_location(module_name, helper_path)
        if spec is None or spec.loader is None:
            raise ConfigurationError(
                f"Cannot load Bluesky login helper: {helper_path}"
            )
        inserted = parent not in sys.path
        if inserted:
            sys.path.insert(0, parent)
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as error:
            raise ConfigurationError(
                f"Cannot load Bluesky login helper: {helper_path}"
            ) from error
        finally:
            if inserted:
                sys.path.remove(parent)
        if not hasattr(module, "Bluesky") or not hasattr(module, "_req"):
            raise ConfigurationError(
                "Existing Bluesky helper does not expose Bluesky/_req"
            )
        self._module = module
        self._client = module.Bluesky(handle, password)
        self.did = str(self._client.did)
        self.pds_xrpc = str(self._client.BASE)
        self._read_sleeper = read_sleeper

    def _read(
        self,
        operation: Callable[[], Any],
        *,
        wait_budget: list[float] | None = None,
    ) -> Any:
        return read_with_retry(
            operation,
            sleeper=self._read_sleeper,
            wait_budget=wait_budget,
        )

    def get_record(
        self, collection: str, rkey: str
    ) -> dict[str, object] | None:
        query = urlencode(
            {
                "repo": self.did,
                "collection": collection,
                "rkey": rkey,
            }
        )

        def fetch() -> dict[str, object] | None:
            try:
                return self._module._req(
                    f"{self.pds_xrpc}/com.atproto.repo.getRecord?{query}",
                    headers=self._client._headers(),
                )
            except urllib.error.HTTPError as error:
                if error.code == 400:
                    detail = self._module._err(error)
                    error.close()
                    if '"RecordNotFound"' in detail:
                        return None
                    raise PublishError(
                        f"PDS record lookup failed: HTTP 400: {detail}"
                    ) from error
                raise

        result = self._read(fetch)
        if result is None:
            return None
        return _validate_remote(result, collection, rkey)

    def list_records(self, collection: str) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        cursor = ""
        seen_cursors: set[str] = set()
        wait_budget = [0.0]
        while True:
            query: dict[str, str] = {
                "repo": self.did,
                "collection": collection,
                "limit": "100",
            }
            if cursor:
                query["cursor"] = cursor
            url = (
                f"{self.pds_xrpc}/com.atproto.repo.listRecords?"
                f"{urlencode(query)}"
            )
            result = self._read(
                lambda: self._module._req(
                    url,
                    headers=self._client._headers(),
                ),
                wait_budget=wait_budget,
            )
            if not isinstance(result, Mapping) or not isinstance(
                result.get("records"), list
            ):
                raise PublishError("PDS returned an invalid record listing")
            page = result["records"]
            if len(records) + len(page) > MAX_REMOTE_RECORDS:
                raise PublishError("PDS record listing exceeds the safety limit")
            records.extend(page)
            next_cursor = result.get("cursor")
            if next_cursor is None:
                return records
            if (
                not isinstance(next_cursor, str)
                or not next_cursor
                or next_cursor in seen_cursors
            ):
                raise PublishError("PDS returned an invalid record cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def put_record(
        self,
        collection: str,
        rkey: str,
        record: Mapping[str, object],
        *,
        swap_record: str | None = None,
    ) -> dict[str, object]:
        """Make exactly one mutation attempt; callers reconcile uncertain results."""
        payload: dict[str, object] = {
            "repo": self.did,
            "collection": collection,
            "rkey": rkey,
            "record": dict(record),
        }
        if swap_record:
            payload["swapRecord"] = swap_record
        result = self._module._req(
            f"{self.pds_xrpc}/com.atproto.repo.putRecord",
            payload,
            headers=self._client._headers(),
        )
        if (
            not isinstance(result, dict)
            or not result.get("uri")
            or not result.get("cid")
        ):
            raise PublishError("PDS did not confirm putRecord")
        return result


def find_bluesky_helper(
    explicit: Path | None = None,
) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    configured = os.environ.get("THREADS_AUTOPILOT_DIR", "").strip()
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path(__file__).resolve().parents[1]
            / "workspaces"
            / "threads-autopilot",
            Path("~/00_GrowthEngine/workspaces/threads-autopilot").expanduser(),
        ]
    )
    for candidate in candidates:
        path = candidate
        if path.is_dir():
            path /= "multi_post.py"
        if path.is_file():
            return path
    raise ConfigurationError(
        "Existing Bluesky login helper not found; set THREADS_AUTOPILOT_DIR"
    )


def existing_client_factory(
    handle: str, password: str
) -> ExistingBlueskyRepoClient:
    return ExistingBlueskyRepoClient(
        handle, password, find_bluesky_helper()
    )


def credentials(
    environment: Mapping[str, str],
) -> tuple[str, str]:
    handle = str(environment.get("BSKY_HANDLE", "")).strip()
    password = str(environment.get("BSKY_APP_PASSWORD", "")).strip()
    if not handle or not password:
        raise ConfigurationError(
            "BSKY_HANDLE and BSKY_APP_PASSWORD are required for --publish"
        )
    return handle, password


def _validate_remote(
    result: object, collection: str, rkey: str
) -> dict[str, object]:
    if not isinstance(result, Mapping):
        raise PublishError("PDS returned a non-object record")
    value = result.get("value")
    if (
        not isinstance(value, Mapping)
        or not result.get("cid")
        or not result.get("uri")
    ):
        raise PublishError("PDS returned an incomplete record")
    expected_suffix = f"/{collection}/{rkey}"
    if not str(result["uri"]).endswith(expected_suffix):
        raise PublishError("PDS returned a record for the wrong collection/key")
    return dict(result)


def _remote_record_map(
    client: object,
    *,
    collection: str,
    did: str,
) -> dict[str, dict[str, object]]:
    list_records = getattr(client, "list_records", None)
    if not callable(list_records):
        raise PublishError("PDS client does not support bounded record listing")
    raw_records = list_records(collection)
    if not isinstance(raw_records, list) or len(raw_records) > MAX_REMOTE_RECORDS:
        raise PublishError("PDS returned an invalid bounded record listing")
    records: dict[str, dict[str, object]] = {}
    for raw in raw_records:
        if not isinstance(raw, Mapping):
            raise PublishError("PDS record listing contains a non-object")
        uri = str(raw.get("uri") or "")
        match = AT_URI_RE.fullmatch(uri)
        if (
            not match
            or match.group(1) != did
            or match.group(2) != collection
        ):
            raise PublishError("PDS record listing contains an invalid AT-URI")
        rkey = match.group(3)
        if rkey in records:
            raise PublishError("PDS record listing contains a duplicate rkey")
        records[rkey] = _validate_remote(raw, collection, rkey)
    return records


def _clear_publication_confirmation(
    publication: MutableMapping[str, object],
) -> None:
    publication["published"] = False
    for key in (
        "at_uri",
        "cid",
        "record_hash",
        "last_verified_at",
    ):
        publication.pop(key, None)


def _clear_document_confirmation(entry: MutableMapping[str, object]) -> None:
    entry["published"] = False
    for key in (
        "at_uri",
        "cid",
        "record_hash",
        "published_hash",
        "last_verified_at",
        "updated_at",
        *ATTRIBUTION_REPAIR_FIELDS,
        ATTRIBUTION_REPAIR_BACKLOG_FIELD,
        *ORDINARY_REPUBLISH_FIELDS,
        PENDING_WINDOW_FIELD,
        PENDING_LIFECYCLE_FIELD,
    ):
        entry.pop(key, None)


def _mark_ordinary_republish_pending(
    entry: MutableMapping[str, object],
    *,
    detected_at: str,
    republish_after_day: str,
) -> None:
    existing_kind = pending_state.pending_kind(entry)
    existing = {
        field: entry.get(field)
        for field in ORDINARY_REPUBLISH_FIELDS
    }
    existing_window = (
        entry.get(PENDING_WINDOW_FIELD)
        if existing_kind == "ordinary_republish"
        else None
    )
    existing_lifecycle = (
        entry.get(PENDING_LIFECYCLE_FIELD)
        if existing_kind == "ordinary_republish"
        and pending_state.pending_is_active(entry)
        else None
    )
    _clear_document_confirmation(entry)
    entry["republish_reason"] = ORDINARY_REPUBLISH_REASON
    entry["republish_detected_at"] = (
        existing["republish_detected_at"] or detected_at
    )
    entry["republish_after_day"] = (
        existing["republish_after_day"] or republish_after_day
    )
    if existing["republish_backlog_days"] is not None:
        entry["republish_backlog_days"] = existing[
            "republish_backlog_days"
        ]
    if existing_window is not None:
        entry[PENDING_WINDOW_FIELD] = existing_window
    if existing_lifecycle is not None:
        entry[PENDING_LIFECYCLE_FIELD] = existing_lifecycle
    else:
        pending_state.activate_pending_entry(
            entry,
            activated_at=detected_at,
            provenance_at=entry["republish_detected_at"],
        )


def _mark_attribution_repair_pending(
    entry: MutableMapping[str, object],
    document: Mapping[str, object],
    *,
    detected_at: str,
    repair_after_day: str,
) -> None:
    existing_kind = pending_state.pending_kind(entry)
    existing_detected_at = entry.get("repair_detected_at")
    existing_after_day = entry.get("repair_after_day")
    existing_backlog_days = entry.get(
        ATTRIBUTION_REPAIR_BACKLOG_FIELD
    )
    existing_window = (
        entry.get(PENDING_WINDOW_FIELD)
        if existing_kind == "attribution_repair"
        else None
    )
    existing_lifecycle = (
        entry.get(PENDING_LIFECYCLE_FIELD)
        if existing_kind == "attribution_repair"
        and pending_state.pending_is_active(entry)
        else None
    )
    _clear_document_confirmation(entry)
    entry["published_hash"] = document["content_hash"]
    entry["repair_reason"] = ATTRIBUTION_REPAIR_REASON
    entry["repair_detected_at"] = existing_detected_at or detected_at
    entry["repair_after_day"] = existing_after_day or repair_after_day
    if existing_backlog_days is not None:
        entry[ATTRIBUTION_REPAIR_BACKLOG_FIELD] = existing_backlog_days
    if existing_window is not None:
        entry[PENDING_WINDOW_FIELD] = existing_window
    if existing_lifecycle is not None:
        entry[PENDING_LIFECYCLE_FIELD] = existing_lifecycle
    else:
        pending_state.activate_pending_entry(
            entry,
            activated_at=detected_at,
            provenance_at=entry["repair_detected_at"],
        )


def _remote_document_canonical(
    value: Mapping[str, object],
    publication_url: str,
) -> str:
    path = value.get("path")
    if not isinstance(path, str):
        raise PublishError("Remote Standard.site document has no path")
    parsed = urlsplit(path)
    if (
        not path.startswith("/")
        or path.startswith("//")
        or not path.endswith(".html")
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or "%" in path
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path[1:].split("/"))
    ):
        raise PublishError("Remote Standard.site document has an unsafe path")
    return publication_url.rstrip("/") + path


def reconcile_remote_state(
    state: MutableMapping[str, object],
    manifest: Mapping[str, object],
    *,
    client: object,
    did: str,
    verified_at: str,
    repair_after_day: str,
    daily_limit: int = DEFAULT_DAILY_LIMIT,
) -> None:
    """Recover stable identities and invalidate stale local confirmations."""
    validate_state(state)
    migrate_publication_origin(state, manifest)
    _migrate_legacy_pending_state(
        state,
        manifest,
        limit=daily_limit,
        migrated_at=verified_at,
    )
    publication_url = str(manifest["publication"]["url"])
    manifest_documents = _document_map(manifest)
    publication_records = _remote_record_map(
        client,
        collection=PUBLICATION_COLLECTION,
        did=did,
    )
    document_records = _remote_record_map(
        client,
        collection=DOCUMENT_COLLECTION,
        did=did,
    )

    publication_candidates = []
    for rkey, record in publication_records.items():
        value = record["value"]
        remote_url = str(value.get("url") or "")
        if (
            remote_url == publication_url
            or PUBLICATION_URL_MIGRATIONS.get(remote_url) == publication_url
        ):
            publication_candidates.append((rkey, record))
    if len(publication_candidates) > 1:
        raise StateError("Multiple remote records claim the Standard.site publication")
    if publication_candidates and (
        publication_candidates[0][1]["value"].get("$type")
        != PUBLICATION_COLLECTION
    ):
        raise StateError("Remote publication claim has the wrong record type")

    publication = state["publication"]
    configured_rkey = str(publication.get("rkey") or "")
    remote_publication: dict[str, object] | None = None
    if publication_candidates:
        remote_rkey, remote_publication = publication_candidates[0]
        if configured_rkey and configured_rkey != remote_rkey:
            raise StateError(
                "Durable publication rkey conflicts with the remote publication"
            )
        publication["rkey"] = remote_rkey
        configured_rkey = remote_rkey
    elif configured_rkey:
        occupying = publication_records.get(configured_rkey)
        if occupying is not None:
            raise StateError(
                "Durable publication rkey is occupied by another record"
            )
        else:
            _clear_publication_confirmation(publication)

    if remote_publication is not None:
        _mark_publication(
            state,
            remote_publication,
            remote_publication["value"],
            did=did,
            verified_at=verified_at,
        )

    active_site_uri = (
        publication_at_uri(did, configured_rkey) if configured_rkey else ""
    )
    active_documents: dict[str, tuple[str, dict[str, object]]] = {}
    for rkey, remote in document_records.items():
        value = remote["value"]
        if value.get("$type") != DOCUMENT_COLLECTION:
            raise PublishError("Remote document collection contains a wrong record type")
        if value.get("site") != active_site_uri:
            continue
        canonical = _remote_document_canonical(value, publication_url)
        if canonical in active_documents:
            raise StateError(
                f"Multiple remote documents claim one canonical URL: {canonical}"
            )
        active_documents[canonical] = (rkey, remote)

    documents = state["documents"]
    for canonical, document in manifest_documents.items():
        entry = documents.setdefault(canonical, {})
        if not isinstance(entry, MutableMapping):
            raise StateError(f"Invalid document state for {canonical}")
        prior_published_hash = str(entry.get("published_hash") or "")
        configured_document_rkey = str(entry.get("rkey") or "")
        active = active_documents.get(canonical)
        if active is None:
            if configured_document_rkey:
                occupying = document_records.get(configured_document_rkey)
                if occupying is not None:
                    raise StateError(
                        f"Durable document rkey is occupied by another record: "
                        f"{canonical}"
                    )
            kind = pending_state.pending_kind(entry)
            if kind is None and entry.get("published_at"):
                _mark_ordinary_republish_pending(
                    entry,
                    detected_at=verified_at,
                    republish_after_day=repair_after_day,
                )
            elif kind is None:
                _clear_document_confirmation(entry)
            continue

        remote_rkey, remote = active
        if configured_document_rkey and configured_document_rkey != remote_rkey:
            raise StateError(
                f"Durable document rkey conflicts with remote canonical: {canonical}"
            )
        entry["rkey"] = remote_rkey
        entry["app_key"] = document["app_key"]
        remote_record = dict(remote["value"])
        published_at = remote_record.get("publishedAt")
        parse_timestamp(published_at)
        entry["published_at"] = published_at
        desired = document_record(document, active_site_uri, entry)
        if _document_semantics(remote_record) == _document_semantics(desired):
            _mark_document(
                state,
                document,
                remote,
                remote_record,
                verified_at=verified_at,
            )
        elif _document_semantics(remote_record) == _document_semantics(
            legacy_document_record(document, active_site_uri, entry)
        ):
            legacy_hash = legacy_document_content_hash(document)
            if prior_published_hash == legacy_hash:
                _mark_document(
                    state,
                    document,
                    remote,
                    remote_record,
                    verified_at=verified_at,
                    published_hash=legacy_hash,
                )
            elif prior_published_hash == str(document["content_hash"]):
                _mark_attribution_repair_pending(
                    entry,
                    document,
                    detected_at=verified_at,
                    repair_after_day=repair_after_day,
                )
            elif (
                pending_state.pending_kind(entry)
                == "ordinary_republish"
                and pending_state.pending_is_active(entry)
            ):
                _mark_ordinary_republish_pending(
                    entry,
                    detected_at=verified_at,
                    republish_after_day=repair_after_day,
                )
            elif (
                configured_document_rkey == remote_rkey
                and entry.get("published") is True
                and entry.get("at_uri") == remote.get("uri")
                and entry.get("record_hash") == record_hash(remote_record)
            ):
                _mark_attribution_repair_pending(
                    entry,
                    document,
                    detected_at=verified_at,
                    repair_after_day=repair_after_day,
                )
            else:
                raise StateError(
                    "Remote legacy Standard.site content lacks explicit "
                    f"durable migration evidence: {canonical}"
                )
        else:
            _mark_ordinary_republish_pending(
                entry,
                detected_at=verified_at,
                republish_after_day=repair_after_day,
            )
    _finalize_pending_backlogs(
        state,
        manifest,
        limit=daily_limit,
        updated_at=verified_at,
    )
    validate_state(state)


def _document_semantics(record: Mapping[str, object]) -> dict[str, object]:
    result = dict(record)
    result.pop("updatedAt", None)
    return result


def upsert_record(
    client: object,
    *,
    collection: str,
    rkey: str,
    desired: Mapping[str, object],
    now: str,
) -> tuple[dict[str, object], dict[str, object], bool]:
    existing_raw = client.get_record(collection, rkey)
    existing = (
        _validate_remote(existing_raw, collection, rkey)
        if existing_raw is not None
        else None
    )
    record = dict(desired)
    if existing is not None:
        current_value = dict(existing["value"])
        if collection == DOCUMENT_COLLECTION:
            if current_value.get("publishedAt"):
                parse_timestamp(current_value["publishedAt"])
                record["publishedAt"] = current_value["publishedAt"]
            if _document_semantics(current_value) == _document_semantics(record):
                return existing, current_value, False
            record["updatedAt"] = now
        elif current_value == record:
            return existing, current_value, False
    result = client.put_record(
        collection,
        rkey,
        record,
        swap_record=str(existing["cid"]) if existing else None,
    )
    confirmed = {
        "uri": result.get("uri"),
        "cid": result.get("cid"),
        "value": record,
    }
    return (
        _validate_remote(confirmed, collection, rkey),
        record,
        True,
    )


def well_known_endpoint(publication_url: str) -> tuple[str, str]:
    parsed = urlsplit(publication_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise StateError("Publication verification requires a clean HTTPS URL")
    publication_path = parsed.path.rstrip("/")
    endpoint_path = (
        "/.well-known/site.standard.publication" + publication_path
    )
    return f"{parsed.scheme}://{parsed.netloc}{endpoint_path}", endpoint_path


def build_guide_contract(
    manifest: Mapping[str, object],
    state: Mapping[str, object],
    *,
    generated_at: str,
) -> tuple[dict[str, object], str]:
    publication = state["publication"]
    if (
        not publication.get("published")
        or not publication.get("did")
        or not publication.get("rkey")
    ):
        raise StateError("Publication must be confirmed before Guide integration")
    at_uri = publication_at_uri(
        str(publication["did"]), str(publication["rkey"])
    )
    publication_url = str(manifest["publication"]["url"])
    endpoint_url, endpoint_path = well_known_endpoint(publication_url)
    body = at_uri + "\n"
    document_map = _document_map(manifest)
    documents: list[dict[str, str]] = []
    for canonical, entry in sorted(state["documents"].items()):
        if (
            canonical not in document_map
            or not isinstance(entry, Mapping)
            or not entry.get("published")
        ):
            continue
        uri = document_at_uri(
            str(publication["did"]), str(entry["rkey"])
        )
        documents.append(
            {
                "canonical_url": canonical,
                "app_key": str(document_map[canonical]["app_key"]),
                "at_uri": uri,
                "link_tag": (
                    f'<link rel="site.standard.document" href="{uri}">'
                ),
            }
        )
    contract: dict[str, object] = {
        "contract_version": 1,
        "generated_at": generated_at,
        "publication": {
            "url": publication_url,
            "at_uri": at_uri,
            "well_known": {
                "request_url": endpoint_url,
                "request_path": endpoint_path,
                "content_type": "text/plain; charset=utf-8",
                "body": body,
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "deploy_at_origin_root": True,
            },
            "discovery_link_tag": (
                f'<link rel="site.standard.publication" href="{at_uri}">'
            ),
        },
        "documents": documents,
    }
    validate_guide_contract(contract, body)
    return contract, body


def validate_guide_contract(
    contract: Mapping[str, object], well_known_body: str
) -> None:
    if contract.get("contract_version") != 1:
        raise StateError("Unsupported Guide contract version")
    publication = contract.get("publication")
    if not isinstance(publication, Mapping):
        raise StateError("Guide contract publication is missing")
    at_uri = str(publication.get("at_uri") or "")
    validate_at_uri(at_uri, PUBLICATION_COLLECTION)
    well_known = publication.get("well_known")
    if not isinstance(well_known, Mapping):
        raise StateError("Guide contract well-known data is missing")
    expected_url, expected_path = well_known_endpoint(str(publication["url"]))
    if (
        well_known.get("request_url") != expected_url
        or well_known.get("request_path") != expected_path
        or well_known.get("content_type") != "text/plain; charset=utf-8"
        or well_known.get("body") != at_uri + "\n"
        or well_known_body != at_uri + "\n"
        or well_known.get("sha256")
        != hashlib.sha256(well_known_body.encode("utf-8")).hexdigest()
        or well_known.get("deploy_at_origin_root") is not True
    ):
        raise StateError("Guide well-known artifact contract is inconsistent")
    documents = contract.get("documents")
    if not isinstance(documents, list):
        raise StateError("Guide contract documents must be an array")
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, Mapping):
            raise StateError("Guide contract document must be an object")
        canonical = str(document.get("canonical_url") or "")
        uri = str(document.get("at_uri") or "")
        if canonical in seen or not canonical.startswith(
            str(publication["url"]) + "/"
        ):
            raise StateError("Guide contract has an invalid document canonical")
        seen.add(canonical)
        validate_at_uri(uri, DOCUMENT_COLLECTION)
        if document.get("link_tag") != (
            f'<link rel="site.standard.document" href="{uri}">'
        ):
            raise StateError("Guide document verification link is inconsistent")


def write_guide_artifacts(
    contract_path: Path,
    well_known_path: Path,
    contract: Mapping[str, object],
    body: str,
) -> None:
    validate_guide_contract(contract, body)
    contract_path = Path(contract_path)
    well_known_path = Path(well_known_path)
    try:
        existing = json.loads(contract_path.read_text(encoding="utf-8"))
        existing_body = well_known_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        existing = None
        existing_body = None
    if isinstance(existing, Mapping) and existing_body == body:
        current = dict(contract)
        previous = dict(existing)
        current.pop("generated_at", None)
        previous.pop("generated_at", None)
        if current == previous:
            return
    atomic_write_text(
        contract_path,
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        mode=0o644,
    )
    atomic_write_text(well_known_path, body, mode=0o644)


def _mark_publication(
    state: MutableMapping[str, object],
    remote: Mapping[str, object],
    record: Mapping[str, object],
    *,
    did: str,
    verified_at: str,
) -> None:
    publication = state["publication"]
    publication.update(
        {
            "did": did,
            "at_uri": remote["uri"],
            "cid": remote["cid"],
            "record_hash": record_hash(record),
            "published": True,
            "last_verified_at": verified_at,
        }
    )


def _mark_document(
    state: MutableMapping[str, object],
    document: Mapping[str, object],
    remote: Mapping[str, object],
    record: Mapping[str, object],
    *,
    verified_at: str,
    published_hash: str | None = None,
) -> None:
    entry = state["documents"][document["canonical_url"]]
    entry.update(
        {
            "at_uri": remote["uri"],
            "cid": remote["cid"],
            "record_hash": record_hash(record),
            "published": True,
            "published_hash": (
                published_hash
                if published_hash is not None
                else document["content_hash"]
            ),
            "published_at": record["publishedAt"],
            "last_verified_at": verified_at,
        }
    )
    if record.get("updatedAt"):
        entry["updated_at"] = record["updatedAt"]
    for field in (
        *ATTRIBUTION_REPAIR_FIELDS,
        ATTRIBUTION_REPAIR_BACKLOG_FIELD,
        *ORDINARY_REPUBLISH_FIELDS,
        PENDING_WINDOW_FIELD,
        PENDING_LIFECYCLE_FIELD,
    ):
        entry.pop(field, None)


def _prepare_plan(
    state: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    generator: TIDGenerator,
    day: str,
    limit: int,
    timestamp: str,
    publish: bool,
) -> tuple[
    dict[str, object],
    list[Mapping[str, object]],
    dict[str, object],
]:
    working = deepcopy(state)
    _migrate_legacy_pending_state(
        working,
        manifest,
        limit=limit,
        migrated_at=timestamp,
    )
    allocate_rkeys(working, manifest, generator)
    selected = reserve_daily_batch(
        working,
        manifest,
        day=day,
        limit=limit,
        now=timestamp,
    )
    plan: dict[str, object] = {
        "mode": "publish" if publish else "check-only",
        "day": day,
        "selected_urls": [
            str(document["canonical_url"]) for document in selected
        ],
        "selected_apps": [
            str(document["app_key"]) for document in selected
        ],
        "publication_changed": False,
        "documents_changed": 0,
        "documents_verified": 0,
        "legacy_unattributed": sorted(
            str(document["canonical_url"])
            for document in manifest["documents"]
            if (
                state["documents"]
                .get(document["canonical_url"], {})
                .get("published")
                and attribution_status(
                    document,
                    state["documents"][document["canonical_url"]].get(
                        "published_hash"
                    ),
                )
                == "legacy_unattributed"
            )
        ),
        "errors": [],
    }
    return working, selected, plan


def run(
    manifest: Mapping[str, object],
    *,
    state_path: Path = DEFAULT_STATE,
    contract_path: Path = DEFAULT_CONTRACT,
    well_known_path: Path = DEFAULT_WELL_KNOWN,
    limit: int = DEFAULT_DAILY_LIMIT,
    publish: bool = False,
    environment: Mapping[str, str] | None = None,
    client_factory: Callable[[str, str], object] = existing_client_factory,
    expected_did: str = EXPECTED_PUBLISHER_DID,
    tid_generator: TIDGenerator | None = None,
    now: datetime | None = None,
    today: str | None = None,
) -> dict[str, object]:
    validate_manifest(manifest)
    if type(limit) is not int or not 1 <= limit <= 4:
        raise ConfigurationError("Daily document limit must be between 1 and 4")
    current = now or datetime.now(timezone.utc)
    timestamp = utc_timestamp(current)
    day = today or current.astimezone(timezone.utc).date().isoformat()
    generator = tid_generator or TIDGenerator()
    if not publish:
        _, _, plan = _prepare_plan(
            load_state(Path(state_path)),
            manifest,
            generator=generator,
            day=day,
            limit=limit,
            timestamp=timestamp,
            publish=False,
        )
        return plan

    handle, password = credentials(environment or os.environ)
    state_path = Path(state_path)
    with publisher_lock(state_path):
        state = load_state(state_path)
        atomic_write_json(state_path, state)
        client = client_factory(handle, password)
        did = str(getattr(client, "did", ""))
        if did != expected_did:
            raise ConfigurationError(
                "Bluesky credentials resolved to an unexpected DID"
            )
        configured_did = str(state["publication"].get("did") or "")
        if configured_did and configured_did != did:
            raise ConfigurationError(
                "Durable publication state belongs to a different DID"
            )

        recovered = deepcopy(state)
        reconcile_remote_state(
            recovered,
            manifest,
            client=client,
            did=did,
            verified_at=timestamp,
            repair_after_day=day,
            daily_limit=limit,
        )
        working, selected, plan = _prepare_plan(
            recovered,
            manifest,
            generator=generator,
            day=day,
            limit=limit,
            timestamp=timestamp,
            publish=True,
        )
        publication_state = working["publication"]
        publication_state["did"] = did
        publication_state["at_uri"] = publication_at_uri(
            did, str(publication_state["rkey"])
        )
        atomic_write_json(state_path, working)

        desired_publication = publication_record(manifest)
        remote, confirmed_record, changed = upsert_record(
            client,
            collection=PUBLICATION_COLLECTION,
            rkey=str(publication_state["rkey"]),
            desired=desired_publication,
            now=timestamp,
        )
        _mark_publication(
            working,
            remote,
            confirmed_record,
            did=did,
            verified_at=timestamp,
        )
        atomic_write_json(state_path, working)
        plan["publication_changed"] = changed

        site_uri = publication_at_uri(did, str(publication_state["rkey"]))
        for document in selected:
            entry = working["documents"][document["canonical_url"]]
            desired_document = document_record(document, site_uri, entry)
            try:
                remote, confirmed_record, changed = upsert_record(
                    client,
                    collection=DOCUMENT_COLLECTION,
                    rkey=str(entry["rkey"]),
                    desired=desired_document,
                    now=timestamp,
                )
                _mark_document(
                    working,
                    document,
                    remote,
                    confirmed_record,
                    verified_at=timestamp,
                )
                atomic_write_json(state_path, working)
                plan["documents_verified"] += 1
                plan["documents_changed"] += int(changed)
            except Exception as error:  # Keep other apps moving; never mark success.
                plan["errors"].append(
                    {
                        "canonical_url": document["canonical_url"],
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

        reconcile_remote_state(
            working,
            manifest,
            client=client,
            did=did,
            verified_at=timestamp,
            repair_after_day=day,
            daily_limit=limit,
        )
        atomic_write_json(state_path, working)
        contract, body = build_guide_contract(
            manifest, working, generated_at=timestamp
        )
        write_guide_artifacts(
            Path(contract_path),
            Path(well_known_path),
            contract,
            body,
        )
        plan["publication_at_uri"] = site_uri
        plan["contract_path"] = str(contract_path)
        plan["well_known_path"] = str(well_known_path)
        return plan


def load_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ManifestError(
            f"Manifest is missing; run gen_standard_site.py --write: {path}"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestError(f"Cannot read manifest: {path}") from error
    if not isinstance(payload, dict):
        raise ManifestError("Manifest root must be an object")
    validate_manifest(payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or publish Standard.site records. Default: check-only "
            "with no auth, network calls, or filesystem changes."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--well-known", type=Path, default=DEFAULT_WELL_KNOWN
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_DAILY_LIMIT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--publish",
        action="store_true",
        help="authenticate and upsert records",
    )
    mode.add_argument(
        "--check-only",
        action="store_true",
        help="validate and plan only (the default)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = load_manifest(args.manifest)
    result = run(
        manifest,
        state_path=args.state,
        contract_path=args.contract,
        well_known_path=args.well_known,
        limit=args.limit,
        publish=args.publish,
    )
    print(
        f"Standard.site {result['mode']}: "
        f"{len(result['selected_urls'])} document(s), "
        f"{result['documents_changed']} changed, "
        f"{len(result['legacy_unattributed'])} legacy unattributed, "
        f"{len(result['errors'])} error(s)"
    )
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
