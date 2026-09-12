#!/usr/bin/env python3
"""Generation-bound feed outbox; notification requires an explicit execute flag."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from deployment_generation import validate_binding
import market_availability as market
import notify_rsscloud
import notify_websub
import owned_app_feeds as feeds
from official_locales import OFFICIAL_LOCALES
from rsscloud_config import RSSCLOUD_PING_URL
from websub_config import WEBSUB_HUBS

SCHEMA = "lumi.owned-feed-delivery/v2"
SHA = re.compile(r"[0-9a-f]{40}")
DEPLOYMENT = Path(".well-known/deployment.json")
PROVIDER_BUDGET = 90


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
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Owned-feed outbox already has an owner") from error
        if path.is_symlink():
            raise ValueError("Outbox state must not be a symlink")
        state = feeds.read_json(path) if path.exists() else {
            "schema": SCHEMA, "accepted": {}, "pending": {},
        }
        if (
            state.get("schema") != SCHEMA
            or not isinstance(state.get("accepted"), dict)
            or not isinstance(state.get("pending"), dict)
        ):
            raise ValueError("Invalid durable outbox")
        yield state
    finally:
        os.close(fd)


def save_state(path: Path, state: dict) -> None:
    staged = path.with_name(path.name + f".writing-{os.getpid()}")
    fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(feeds.json_bytes(state))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    finally:
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


def prepare(pages: Path, state_path: Path, source_sha: str, *,
            include_legacy: bool = False, baseline: dict | None = None, opener=None) -> dict:
    proof = deployment_digest(pages, source_sha)
    current = inventory(pages, include_legacy=include_legacy)
    if baseline is None:
        baseline = baseline_hashes(current, opener=opener)
    if set(baseline) != set(current["topics"]) or any(
        value is not None and (not isinstance(value, str) or not feeds.SHA256.fullmatch(value))
        for value in baseline.values()
    ):
        raise ValueError("Baseline does not cover the exact current topics")
    wanted = tasks(current)
    with locked_state(state_path) as state:
        pending = {}
        for key, task in wanted.items():
            previous = state["pending"].get(key, {})
            content = task["content_sha256"]
            if state["accepted"].get(key, {}).get("content_sha256") == content:
                continue
            if baseline[task["topic"]] == content and previous.get("content_sha256") != content:
                continue
            attempts = previous.get("attempt_count", 0) if previous.get("content_sha256") == content else 0
            if type(attempts) is not int or attempts < 0:
                raise ValueError("Invalid outbox attempt counter")
            pending[key] = {
                **task, "attempt_count": attempts,
                "source_sha": source_sha, "generation_digest": current["generation_digest"],
            }
        state["pending"] = pending
        state["accepted"] = {k: v for k, v in state["accepted"].items() if k in wanted}
        state["prepared"] = {
            "source_sha": source_sha, "inventory_digest": feeds.digest(current),
            "deployment_sha256": proof, "include_legacy": include_legacy,
        }
        save_state(state_path, state)
    return {"pending_notifications": len(pending), "topics": len(current["topics"])}


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


def send_batch(protocol: str, endpoint: str, topics: list[str]) -> dict:
    receipts = []
    if protocol == "websub":
        notify_websub.notify(
            topics=topics, hub=endpoint, attempts=3, timeout=15,
            receipt_sink=receipts.append,
        )
    elif protocol == "rsscloud" and len(topics) == 1:
        notify_rsscloud.ping(
            topic=topics[0], endpoint=endpoint, attempts=3, timeout=15,
            receipt_sink=receipts.append,
        )
    else:
        raise ValueError("Invalid syndication batch")
    if not receipts:
        raise RuntimeError("Provider did not return an acknowledgement")
    return receipts[-1]


def deliver(pages: Path, state_path: Path, source_sha: str, protocol: str, *,
            opener=None, sender=None) -> dict:
    if protocol not in ("websub", "rsscloud"):
        raise ValueError("Unsupported notification protocol")
    sender = sender or send_batch
    with locked_state(state_path) as state:
        prepared = state.get("prepared", {})
        current = inventory(pages, include_legacy=prepared.get("include_legacy", False))
        proof = deployment_digest(pages, source_sha)
        if (
            prepared.get("source_sha") != source_sha
            or prepared.get("inventory_digest") != feeds.digest(current)
            or prepared.get("deployment_sha256") != proof
        ):
            raise ValueError("Outbox source/generation drift")
        wanted, selected = tasks(current), {}
        for key, task in state["pending"].items():
            expected = wanted.get(key)
            if (
                expected is None or any(task.get(k) != v for k, v in expected.items())
                or task.get("source_sha") != source_sha
                or task.get("generation_digest") != current["generation_digest"]
            ):
                raise ValueError("Pending task is not generation-bound")
            if task["protocol"] == protocol:
                selected[key] = task
        if not selected:
            return {"accepted": 0, "pending": 0, "protocol": protocol}
        verify_live(pages, current, proof, opener=opener)
        ordered = sorted(selected.items(), key=lambda pair: (
            pair[1]["attempt_count"], pair[1]["topic"],
        ))
        endpoints = list(dict.fromkeys(task["endpoint"] for _, task in ordered))
        batches = {}
        size = 25 if protocol == "websub" else 1
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
                for _, task in batch:
                    task["attempt_count"] += 1
                save_state(state_path, state)
                started = time.monotonic()
                try:
                    receipt = sender(protocol, endpoint, [task["topic"] for _, task in batch])
                    if not isinstance(receipt, dict) or not 200 <= receipt.get("http_status", 0) < 300:
                        raise RuntimeError("Missing positive provider acknowledgement")
                    for key, task in batch:
                        state["accepted"][key] = {
                            "content_sha256": task["content_sha256"],
                            "accepted_at": datetime.now(timezone.utc).isoformat(),
                            "receipt": receipt,
                        }
                        state["pending"].pop(key)
                        accepted += 1
                    save_state(state_path, state)
                except (RuntimeError, OSError, ValueError):
                    failed.add(endpoint)
                finally:
                    spent[endpoint] += time.monotonic() - started
        pending = sum(task["protocol"] == protocol for task in state["pending"].values())
        if pending:
            raise RuntimeError(f"Notifications remain pending: {protocol}={pending}, accepted={accepted}")
    return {"accepted": accepted, "pending": 0, "protocol": protocol}


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
