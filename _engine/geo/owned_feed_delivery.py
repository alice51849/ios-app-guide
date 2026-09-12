#!/usr/bin/env python3
"""Generation-bound feed outbox; notification requires an explicit execute flag."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from deployment_generation import validate_binding
import market_availability as market
import notify_rsscloud
import notify_websub
import owned_app_feeds as feeds
import owned_feed_receipts as receipts
from official_locales import OFFICIAL_LOCALES
from rsscloud_config import RSSCLOUD_PING_URL
from websub_config import WEBSUB_HUBS

SCHEMA = receipts.STATE_SCHEMA
SHA = re.compile(r"[0-9a-f]{40}")
DEPLOYMENT = Path(".well-known/deployment.json")
PROVIDER_BUDGET = 90
MAX_RETRIES = 3
MAX_BACKOFF = 300


def local_path(pages: Path, topic: str) -> Path:
    site, parsed = urllib.parse.urlsplit(feeds.SITE), urllib.parse.urlsplit(topic)
    prefix = site.path.rstrip("/") + "/"
    if (
        parsed.scheme != "https" or parsed.netloc != site.netloc
        or not parsed.path.startswith(prefix) or parsed.query or parsed.fragment
    ):
        raise ValueError("Unowned feed topic")
    relative = urllib.parse.unquote(parsed.path[len(prefix):])
    path, root = (pages / relative).resolve(), pages.resolve()
    if root not in path.parents:
        raise ValueError("Feed topic escapes its directory")
    return path


def inventory(pages: Path, *, include_legacy: bool = False) -> dict:
    manifest = feeds.read_manifest(pages)
    topics = {}
    for locale, row in manifest["feeds"].items():
        for fmt, spec in row["formats"].items():
            topics[spec["url"]] = {
                "sha256": spec["sha256"], "format": fmt, "locale": locale,
                "notification_eligible": row["notification_eligible"],
                "rsscloud": fmt == "rss",
            }
    if include_legacy:
        for topic in notify_websub.discover_topics(pages):
            path = local_path(pages, topic)
            raw = path.read_bytes()
            if len(raw) > feeds.MAX_BYTES:
                raise ValueError("Legacy feed exceeds readback budget")
            raw.decode("utf-8", errors="strict")
            locale = market.locale_from_path(path.relative_to(pages.resolve()))
            fmt = (
                "json_feed" if path.suffix == ".json"
                else "rss" if topic == notify_rsscloud.TOPIC else "atom"
            )
            topics[topic] = {
                "sha256": feeds.sha256(raw), "format": fmt, "locale": locale,
                "notification_eligible": not market.is_unavailable(locale),
                "rsscloud": topic == notify_rsscloud.TOPIC,
            }
    return {
        "generation_digest": manifest["generation_digest"],
        "manifest_sha256": feeds.sha256((pages / feeds.INDEX).read_bytes()),
        "topics": topics,
    }


def fetch(url: str, *, opener=None, allowed_types=None, missing_ok=False) -> bytes | None:
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={
        "User-Agent": "Lumi-Owned-Feed-Delivery/2.0",
        "Accept": "*/*", "Cache-Control": "no-cache",
    })
    for attempt in range(3):
        try:
            with opener(request, timeout=15) as response:
                if response.status != 200:
                    raise ValueError(f"Feed readback HTTP {response.status}")
                if allowed_types and response.headers.get_content_type() not in allowed_types:
                    raise ValueError("Unexpected feed Content-Type")
                charset = response.headers.get_content_charset()
                if charset and charset.lower() not in ("utf-8", "utf8"):
                    raise ValueError("Feed readback is not UTF-8")
                raw = response.read(feeds.MAX_BYTES + 1)
                if len(raw) > feeds.MAX_BYTES:
                    raise ValueError("Feed readback exceeds byte budget")
                raw.decode("utf-8", errors="strict")
                return raw
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
            if missing_ok and status == 404:
                return None
            if attempt == 2 or (400 <= status < 500 and status != 429):
                raise
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Feed readback exhausted retries")


def baseline_hashes(current: dict, *, opener=None) -> dict:
    raw = fetch(feeds.url(feeds.INDEX), opener=opener, missing_ok=True,
                allowed_types={"application/json"})
    baseline = {}
    previous = feeds.decode(raw) if raw is not None else None
    if previous is not None:
        if (
            previous.get("schema") != feeds.SCHEMA
            or set(previous.get("feeds", {})) != set(OFFICIAL_LOCALES)
            or previous.get("generation_digest") != feeds.digest({
                k: v for k, v in previous.items() if k != "generation_digest"
            })
        ):
            raise ValueError("Malformed prior deployment; refusing to assume new content")
        for locale, row in previous["feeds"].items():
            for fmt in feeds.FORMATS:
                spec = row["formats"][fmt]
                topic = feeds.url(feeds.feed_path(locale, fmt))
                if spec.get("url") != topic or not feeds.SHA256.fullmatch(spec.get("sha256", "")):
                    raise ValueError("Invalid previous feed identity/hash")
                baseline[topic] = spec["sha256"]
    else:
        baseline = {
            feeds.url(feeds.feed_path(locale, fmt)): None
            for locale in OFFICIAL_LOCALES for fmt in feeds.FORMATS
        }

    def legacy_hash(topic):
        raw = fetch(topic, opener=opener, missing_ok=True,
                    allowed_types=feeds.CONTENT_TYPES[current["topics"][topic]["format"]])
        return topic, feeds.sha256(raw) if raw is not None else None

    with ThreadPoolExecutor(max_workers=6) as pool:
        baseline.update(pool.map(legacy_hash, sorted(set(current["topics"]) - set(baseline))))
    return baseline


@contextmanager
def locked_state(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Owned-feed outbox already has an owner") from error
        if path.is_symlink():
            raise ValueError("Outbox state must not be a symlink")
        recover_staged_state(path)
        state = read_state(path)
        if state["in_flight"]:
            for flight in list(state["in_flight"].values()):
                for key, task in flight["tasks"].items():
                    response = response_record(
                        task["protocol"], task["endpoint"], flight["attempt"]["topics"],
                        None, "", transport_error="crash_recovery",
                    )
                    record = receipts.make_receipt(task, flight["attempt"], response)
                    state["records"][record["receipt_id"]] = record
                    if key in state["pending"]:
                        state["pending"][key]["next_attempt_at"] = 0
            state["in_flight"] = {}
            save_state(path, state)
        yield state
    finally:
        os.close(fd)


def read_state(path: Path) -> dict:
    if not path.exists():
        return receipts.new_state()
    if path.is_symlink():
        raise ValueError("Outbox state must not be a symlink")
    os.chmod(path, 0o600)
    state = feeds.read_json(path)
    if state.get("schema") == "lumi.owned-feed-delivery/v2":
        if not isinstance(state.get("accepted"), dict) or not isinstance(state.get("pending"), dict):
            raise ValueError("Invalid legacy outbox")
        migrated = receipts.new_state()
        migrated["legacy_history"].append(state)
        migrated["pending"] = state["pending"]
        return migrated
    receipts.validate_state(state)
    return state


def recover_staged_state(path: Path) -> None:
    current = path.read_bytes() if path.exists() else None
    previous = feeds.sha256(current) if current is not None else None
    revision = feeds.decode(current).get("revision", 0) if current else 0
    candidates = {}
    for staged in path.parent.glob(f".{path.name}.writing-*"):
        if staged.is_symlink() or staged.stat().st_mode & 0o777 != 0o600:
            raise ValueError("Unsafe staged receipt state")
        try:
            candidate = feeds.read_json(staged)
            receipts.validate_state(candidate)
        except (ValueError, OSError):
            continue
        if candidate["revision"] == revision + 1 and candidate["previous_state_sha256"] == previous:
            candidates.setdefault(candidate["state_digest"], []).append(staged)
    if len(candidates) > 1:
        raise ValueError("Conflicting receipt recovery candidates")
    if candidates:
        staged = next(iter(candidates.values()))[0]
        os.replace(staged, path)
        fsync_directory(path.parent)


def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_state(path: Path, state: dict) -> None:
    previous = path.read_bytes() if path.exists() else None
    revision = feeds.decode(previous).get("revision", 0) if previous else 0
    if state["revision"] != revision:
        raise ValueError("Concurrent/stale receipt state write")
    state["revision"] = revision + 1
    state["previous_state_sha256"] = feeds.sha256(previous) if previous else None
    state["state_digest"] = feeds.digest({k: v for k, v in state.items() if k != "state_digest"})
    staged = path.with_name(f".{path.name}.writing-{uuid.uuid4().hex}")
    fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    durable = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(feeds.json_bytes(state))
            handle.flush()
            os.fsync(handle.fileno())
            durable = True
        os.replace(staged, path)
        fsync_directory(path.parent)
    finally:
        if not durable:
            staged.unlink(missing_ok=True)


def tasks(current: dict) -> dict:
    wanted = {}
    for topic, spec in sorted(current["topics"].items()):
        if not spec["notification_eligible"]:
            continue
        endpoints = [("websub", hub) for hub in WEBSUB_HUBS]
        if spec["rsscloud"]:
            endpoints.append(("rsscloud", RSSCLOUD_PING_URL))
        for protocol, endpoint in endpoints:
            key = feeds.digest([protocol, endpoint, topic])
            wanted[key] = {
                "protocol": protocol, "endpoint": endpoint, "topic": topic,
                "content_sha256": spec["sha256"],
            }
    return wanted


def deployment_digest(pages: Path, source_sha: str) -> str:
    if not SHA.fullmatch(source_sha):
        raise ValueError("Outbox requires a full source SHA")
    raw = (pages / DEPLOYMENT).read_bytes()
    document = feeds.decode(raw)
    generation = validate_binding(document)
    if generation["pages_source_sha"] != source_sha:
        raise ValueError("Deployment proof is not bound to this paired source generation")
    return feeds.sha256(raw)


def binding(pages: Path, current: dict, source_sha: str) -> dict:
    proof = deployment_digest(pages, source_sha)
    generation = validate_binding(feeds.read_json(pages / DEPLOYMENT))
    return {
        "generation_id": generation["generation_id"],
        "feed_generation_sha256": current["generation_digest"],
        "inventory_sha256": feeds.digest(current), "source_sha": source_sha,
        "engine_source_sha": generation["source_sha"], "deployment_sha256": proof,
    }


def prepare(pages: Path, state_path: Path, source_sha: str, *,
            include_legacy: bool = False, baseline: dict | None = None, opener=None) -> dict:
    deployment_digest(pages, source_sha)
    current = inventory(pages, include_legacy=include_legacy)
    context = binding(pages, current, source_sha)
    if baseline is None:
        baseline = baseline_hashes(current, opener=opener)
    if set(baseline) != set(current["topics"]) or any(
        value is not None and (not isinstance(value, str) or not feeds.SHA256.fullmatch(value))
        for value in baseline.values()
    ):
        raise ValueError("Baseline does not cover the exact current topics")
    wanted = tasks(current)
    with locked_state(state_path) as state:
        pending, accepted, historical, new_intents, retry_intents = {}, {}, 0, 0, 0
        by_content = {}
        for record in state["records"].values():
            if record["accepted_ack"] and not record.get("fixture"):
                index = (record["protocol"], record["endpoint"], record["topic"], record["request"]["feed_sha256"])
                by_content.setdefault(index, []).append(record)
        for key, task in wanted.items():
            task = {**task, **context}
            previous = state["pending"].get(key, {})
            content = task["content_sha256"]
            matches = by_content.get((task["protocol"], task["endpoint"], task["topic"], content), [])
            exact = [record for record in matches if receipts.is_current(record, task)]
            if exact:
                accepted[key] = exact[-1]["receipt_id"]
                continue
            if matches:
                historical += 1
                continue
            if baseline[task["topic"]] == content and previous.get("content_sha256") != content:
                continue
            attempts = previous.get("attempt_count", 0) if previous.get("content_sha256") == content else 0
            if type(attempts) is not int or attempts < 0:
                raise ValueError("Invalid outbox attempt counter")
            pending[key] = {
                **task, "attempt_count": attempts,
                "retryable": True,
                "next_attempt_at": previous.get("next_attempt_at", 0) if previous.get("content_sha256") == content else 0,
            }
            if previous.get("content_sha256") == content:
                retry_intents += 1
            else:
                new_intents += 1
        state["pending"] = pending
        state["accepted"] = accepted
        state["prepared"] = {**context, "include_legacy": include_legacy}
        save_state(state_path, state)
    return {
        "pending_notifications": len(pending), "topics": len(current["topics"]),
        "current_generation_acks": len(accepted), "historical_content_deduplicated": historical,
        "new_notification_intents": new_intents, "retry_intents": retry_intents,
    }


def verify_live(pages: Path, current: dict, proof: str, *, opener=None) -> None:
    checks = [
        (feeds.url(DEPLOYMENT), proof, {"application/json"}),
        (feeds.url(feeds.INDEX), current["manifest_sha256"], {"application/json"}),
        *[
            (topic, spec["sha256"], feeds.CONTENT_TYPES[spec["format"]])
            for topic, spec in current["topics"].items()
        ],
    ]
    def check(spec):
        topic, expected, allowed = spec
        raw = fetch(topic, opener=opener, allowed_types=allowed)
        if feeds.sha256(raw) != expected:
            raise ValueError(f"Partial/stale deployed feed generation: {topic}")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(check, checks))
    # A deployment changing during the readback cannot authorize a notification.
    if feeds.sha256(fetch(feeds.url(DEPLOYMENT), opener=opener,
                          allowed_types={"application/json"})) != proof:
        raise ValueError("Deployment generation changed during feed readback")


def response_record(protocol, endpoint, topics, status, body, **extra) -> dict:
    return {
        "http_status": status, "ack_body": body, "observed_at": receipts.utc_now(),
        "endpoint": endpoint, "final_url": endpoint, "topics": list(topics),
        "request_sha256": feeds.sha256(receipts.request_body(protocol, topics).encode("ascii")),
        **extra,
    }


def send_batch(protocol: str, endpoint: str, topics: list[str]) -> dict:
    body = receipts.request_body(protocol, topics).encode("ascii")
    request = urllib.request.Request(endpoint, body, headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "User-Agent": "Lumi-Owned-Feed-Delivery/3.0",
    })
    try:
        response = urllib.request.urlopen(request, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(receipts.MAX_ACK_BYTES + 1)
        if len(raw) > receipts.MAX_ACK_BYTES:
            raise ValueError("Publisher ACK exceeds byte budget")
        retry_after = response.headers.get("Retry-After")
        retry = None
        if retry_after:
            try:
                retry = float(retry_after)
            except ValueError:
                try:
                    retry = parsedate_to_datetime(retry_after).timestamp() - time.time()
                except (ValueError, TypeError, OverflowError):
                    retry = 0
            retry = min(MAX_BACKOFF, max(0, retry))
        return response_record(
            protocol, endpoint, topics, response.status, raw.decode("utf-8"),
            final_url=response.geturl(), retry_after_seconds=retry,
        )


def deliver(pages: Path, state_path: Path, source_sha: str, protocol: str, *,
            opener=None, sender=None, sleeper=time.sleep, clock=time.time,
            batch_size=25, max_retries=MAX_RETRIES) -> dict:
    if protocol not in ("websub", "rsscloud"):
        raise ValueError("Unsupported notification protocol")
    sender = sender or send_batch
    if not 1 <= batch_size <= 25 or not 1 <= max_retries <= MAX_RETRIES:
        raise ValueError("Invalid bounded notification batch/retry budget")
    def stamp():
        return datetime.fromtimestamp(clock(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with locked_state(state_path) as state:
        prepared = state.get("prepared", {})
        try:
            current = inventory(pages, include_legacy=prepared.get("include_legacy", False))
            context = binding(pages, current, source_sha)
        except (OSError, ValueError):
            state["accepted"] = {}
            save_state(state_path, state)
            raise
        if any(prepared.get(name) != context[name] for name in receipts.BINDING_FIELDS):
            state["accepted"] = {}
            save_state(state_path, state)
            raise ValueError("Outbox source/generation drift")
        wanted, selected = tasks(current), {}
        for key, task in state["pending"].items():
            expected = wanted.get(key)
            if (
                expected is None or any(task.get(k) != v for k, v in expected.items())
                or any(task.get(name) != context[name] for name in receipts.BINDING_FIELDS)
            ):
                raise ValueError("Pending task is not generation-bound")
            if key in state["accepted"] and receipts.is_current(state["records"][state["accepted"][key]], task):
                continue
            if task["protocol"] == protocol:
                selected[key] = task
        if not selected:
            return {"accepted": 0, "accepted_ack": 0, "pending": 0, "protocol": protocol,
                    "subscriber_delivery_verified": False, "indexing_verified": False}
        verify_live(pages, current, context["deployment_sha256"], opener=opener)
        ordered = sorted(selected.items(), key=lambda pair: (
            pair[1]["attempt_count"], pair[1]["topic"],
        ))
        endpoints = list(dict.fromkeys(task["endpoint"] for _, task in ordered))
        batches = {}
        size = batch_size if protocol == "websub" else 1
        for endpoint in endpoints:
            members = [(key, task) for key, task in ordered if task["endpoint"] == endpoint]
            batches[endpoint] = [members[n:n + size] for n in range(0, len(members), size)]
        failed, spent, accepted = set(), dict.fromkeys(endpoints, 0.0), 0
        for position in range(max(map(len, batches.values()))):
            for endpoint in endpoints:
                if endpoint in failed or position >= len(batches[endpoint]):
                    continue
                if spent[endpoint] >= PROVIDER_BUDGET:
                    failed.add(endpoint)
                    continue
                batch = batches[endpoint][position]
                if any(not task.get("retryable", True) or task.get("next_attempt_at", 0) > clock() for _, task in batch):
                    continue
                started = time.monotonic()
                for retry in range(max_retries):
                    topics = [task["topic"] for _, task in batch]
                    body = receipts.request_body(protocol, topics)
                    attempt = {
                        "attempt_id": uuid.uuid4().hex, "started_at": stamp(),
                        "topics": topics, "request_body": body,
                        "request_sha256": feeds.sha256(body.encode("ascii")),
                    }
                    for _, task in batch:
                        task["attempt_count"] += 1
                    state["in_flight"][attempt["attempt_id"]] = {
                        "attempt": attempt, "tasks": dict(batch),
                    }
                    save_state(state_path, state)
                    try:
                        response = sender(protocol, endpoint, topics)
                    except (RuntimeError, OSError, ValueError) as error:
                        response = response_record(
                            protocol, endpoint, topics, None, "", observed_at=stamp(),
                            transport_error="timeout" if isinstance(error, TimeoutError) else "transport_error",
                        )
                    response.setdefault("observed_at", stamp())
                    results = [receipts.make_receipt(task, attempt, response) for _, task in batch]
                    acked = all(record["accepted_ack"] for record in results)
                    retryable = all(record["outcome"] in {"retryable_error", "indeterminate"} for record in results)
                    delay = min(MAX_BACKOFF, max(
                        2 ** min(max(task["attempt_count"] for _, task in batch) - 1, 8),
                        response.get("retry_after_seconds") or 0,
                    ))
                    for (key, task), record in zip(batch, results, strict=True):
                        state["records"][record["receipt_id"]] = record
                        if record["accepted_ack"]:
                            state["accepted"][key] = record["receipt_id"]
                            state["pending"].pop(key)
                            accepted += 1
                        else:
                            task["retryable"] = retryable
                            task["next_attempt_at"] = clock() + delay
                    state["in_flight"].pop(attempt["attempt_id"])
                    # Persistence failures must propagate, never be mistaken for a retryable HTTP failure.
                    save_state(state_path, state)
                    if acked:
                        break
                    if not retryable or retry == max_retries - 1 or spent[endpoint] + time.monotonic() - started + delay >= PROVIDER_BUDGET:
                        failed.add(endpoint)
                        break
                    sleeper(delay)
                spent[endpoint] += time.monotonic() - started
        pending = sum(task["protocol"] == protocol for task in state["pending"].values())
        if pending:
            raise RuntimeError(f"Notifications remain pending: {protocol}={pending}, accepted={accepted}")
    return {"accepted": accepted, "accepted_ack": accepted, "pending": 0, "protocol": protocol,
            "subscriber_delivery_verified": False, "indexing_verified": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "notify"))
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--include-legacy", action="store_true")
    parser.add_argument("--protocol", choices=("websub", "rsscloud"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.operation == "prepare":
        result = prepare(
            args.pages_dir, args.state, args.source_sha, include_legacy=args.include_legacy,
        )
    else:
        if not args.execute or not args.protocol:
            parser.error("notify requires --execute and --protocol after exact live verification")
        result = deliver(args.pages_dir, args.state, args.source_sha, args.protocol)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
