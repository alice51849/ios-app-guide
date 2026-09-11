#!/usr/bin/env python3
"""Durable, content-addressed WebSub/rssCloud outbox for owned feeds."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import notify_rsscloud
import notify_websub
from official_locales import OFFICIAL_LOCALES
from rsscloud_config import RSSCLOUD_PING_URL
from websub_config import WEBSUB_HUBS

SITE = os.environ.get("GEO_SITE", "https://open.cait518.cc/ios-app-guide").rstrip("/")
INDEX = Path("feeds/owned-apps.json")
SCHEMA = "lumi.owned-feed-delivery/v1"
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 2_000_000
PROVIDER_BUDGET_SECONDS = 90
FORMATS = {"atom": "feed.xml", "rss": "rss.xml", "json_feed": "feed.json"}
CONTENT_TYPES = {
    "atom": {"application/atom+xml", "application/xml", "text/xml"},
    "rss": {"application/rss+xml", "application/xml", "text/xml"},
    "json_feed": {"application/feed+json", "application/json"},
}


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate delivery JSON field: {key}")
        result[key] = value
    return result


def _decode(raw: bytes) -> dict:
    result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    if not isinstance(result, dict):
        raise ValueError("Delivery document must be an object")
    return result


def _local(pages: Path, topic: str) -> Path:
    site, url = urllib.parse.urlsplit(SITE), urllib.parse.urlsplit(topic)
    prefix = site.path.rstrip("/") + "/"
    if (url.scheme != "https" or url.netloc != site.netloc
            or not url.path.startswith(prefix) or url.query or url.fragment):
        raise ValueError("Feed topic is outside the owned site")
    relative = urllib.parse.unquote(url.path[len(prefix):])
    root, path = pages.resolve(), (pages / relative).resolve()
    if root not in path.parents:
        raise ValueError("Feed topic escapes its site directory")
    return path


def inventory(pages: Path, include_legacy: bool = False) -> dict:
    index = _decode((pages / INDEX).read_bytes())
    if (index.get("schema") != "lumi.owned-app-feeds/v1"
            or set(index.get("feeds", {})) != set(OFFICIAL_LOCALES)
            or not HASH.fullmatch(index.get("generation_digest", ""))):
        raise ValueError("Invalid owned-feed generation")
    topics = {}
    for locale in OFFICIAL_LOCALES:
        row = index["feeds"][locale]
        if row.get("language") != locale:
            raise ValueError("Owned-feed language differs from its path")
        for fmt, filename in FORMATS.items():
            topic = f"{SITE}/{locale}/{filename}"
            spec = row["formats"][fmt]
            raw = _local(pages, topic).read_bytes()
            raw.decode("utf-8", errors="strict")
            if (spec["url"] != topic or len(raw) > MAX_BYTES
                    or spec["sha256"] != _hash(raw)):
                raise ValueError("Feed bytes differ from the bound generation")
            topics[topic] = {"sha256": _hash(raw), "format": fmt,
                             "rsscloud": fmt == "rss"}
    if include_legacy:
        for topic in notify_websub.discover_topics(pages):
            raw = _local(pages, topic).read_bytes()
            if len(raw) > MAX_BYTES:
                raise ValueError("Legacy feed exceeds readback bound")
            raw.decode("utf-8", errors="strict")
            fmt = ("json_feed" if topic.endswith(".json")
                   else "rss" if topic == notify_rsscloud.TOPIC else "atom")
            topics[topic] = {
                "sha256": _hash(raw), "format": fmt,
                "rsscloud": topic == notify_rsscloud.TOPIC,
            }
    return {"generation_digest": index["generation_digest"], "topics": topics}


def _request(topic: str):
    return urllib.request.Request(topic, headers={
        "User-Agent": "Lumi-Owned-Feed-Delivery/1.0",
        "Accept": "*/*", "Cache-Control": "no-cache",
    })


def _fetch(topic: str, *, opener=urllib.request.urlopen, timeout=15,
           missing_ok=False, content_types=None) -> bytes | None:
    for attempt in range(3):
        try:
            with opener(_request(topic), timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"Feed HTTP status {response.status}")
                charset = response.headers.get_content_charset()
                if charset is not None and charset.casefold() not in {"utf-8", "utf8"}:
                    raise ValueError("Feed is not served as UTF-8")
                if content_types and response.headers.get_content_type() not in content_types:
                    raise ValueError("Feed has the wrong Content-Type")
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError("Feed exceeds readback bound")
                body.decode("utf-8", errors="strict")
                return body
        except urllib.error.HTTPError as error:
            if error.code == 404 and missing_ok:
                error.close()
                return None
            if attempt == 2 or 400 <= error.code < 500 and error.code != 429:
                error.close()
                raise
            error.close()
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Feed readback exhausted retries")


def baseline_hashes(current: dict, *, opener=urllib.request.urlopen) -> dict:
    raw = _fetch(f"{SITE}/{INDEX}", opener=opener, missing_ok=True,
                 content_types={"application/json"})
    previous = _decode(raw) if raw is not None else None
    if previous is not None and (
        previous.get("schema") != "lumi.owned-app-feeds/v1"
        or set(previous.get("feeds", {})) != set(OFFICIAL_LOCALES)
    ):
        raise ValueError("Malformed deployed feed index; refusing to assume a change")
    baseline = {}
    for locale in OFFICIAL_LOCALES:
        for fmt, filename in FORMATS.items():
            topic = f"{SITE}/{locale}/{filename}"
            value = None
            if previous is not None:
                entry = previous["feeds"][locale]["formats"][fmt]
                value = entry.get("sha256")
                if entry.get("url") != topic or not HASH.fullmatch(value or ""):
                    raise ValueError("Invalid deployed feed topic/hash")
            baseline[topic] = value
    legacy = sorted(set(current["topics"]) - set(baseline))

    def fetch(topic):
        raw = _fetch(topic, opener=opener, missing_ok=True,
                     content_types=CONTENT_TYPES[current["topics"][topic]["format"]])
        return topic, _hash(raw) if raw is not None else None

    with ThreadPoolExecutor(max_workers=6) as pool:
        baseline.update(pool.map(fetch, legacy))
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
            raise RuntimeError("Another owner is delivering this outbox") from error
        if path.is_symlink():
            raise ValueError("Delivery state must not be a symlink")
        state = _decode(path.read_bytes()) if path.exists() else {
            "schema": SCHEMA, "accepted": {}, "pending": {},
        }
        if (state.get("schema") != SCHEMA
                or not isinstance(state.get("accepted"), dict)
                or not isinstance(state.get("pending"), dict)):
            raise ValueError("Invalid durable delivery state")
        yield state
    finally:
        os.close(fd)


def save_state(path: Path, state: dict):
    staging = path.with_name(path.name + f".writing-{os.getpid()}")
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write((json.dumps(state, sort_keys=True, ensure_ascii=False, indent=2)
                          + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def tasks(current: dict) -> dict:
    result = {}
    for topic, spec in sorted(current["topics"].items()):
        endpoints = [("websub", hub) for hub in WEBSUB_HUBS]
        if spec["rsscloud"]:
            endpoints.append(("rsscloud", RSSCLOUD_PING_URL))
        for protocol, endpoint in endpoints:
            key = _digest([protocol, endpoint, topic])
            result[key] = {
                "protocol": protocol, "endpoint": endpoint, "topic": topic,
                "content_sha256": spec["sha256"],
            }
    return result


def prepare(pages: Path, state_path: Path, source_sha: str, *,
            include_legacy=False, baseline=None, opener=urllib.request.urlopen) -> dict:
    if not SHA.fullmatch(source_sha):
        raise ValueError("Delivery requires a full source commit")
    current = inventory(pages, include_legacy)
    baseline = baseline_hashes(current, opener=opener) if baseline is None else baseline
    if set(baseline) != set(current["topics"]):
        raise ValueError("Previous deployment does not cover the feed inventory")
    wanted = tasks(current)
    with locked_state(state_path) as state:
        pending = {}
        for key, task in wanted.items():
            accepted = state["accepted"].get(key, {})
            previous = state["pending"].get(key, {})
            same_content = task["content_sha256"]
            if accepted.get("content_sha256") == same_content:
                continue
            if (baseline[task["topic"]] != same_content
                    or previous.get("content_sha256") == same_content):
                attempts = (previous.get("attempt_count", 0)
                            if previous.get("content_sha256") == same_content else 0)
                if type(attempts) is not int or attempts < 0:
                    raise ValueError("Invalid pending attempt counter")
                pending[key] = {
                    **task, "source_sha": source_sha,
                    "generation_digest": current["generation_digest"],
                    "attempt_count": attempts,
                }
        state["pending"] = pending
        state["accepted"] = {k: v for k, v in state["accepted"].items() if k in wanted}
        state["prepared"] = {
            "source_sha": source_sha, "inventory_digest": _digest(current),
            "include_legacy": include_legacy,
        }
        save_state(state_path, state)
    return {"pending_notifications": len(pending), "topics": len(current["topics"])}


def verify(current: dict, topics=None, *, opener=urllib.request.urlopen):
    selected = set(current["topics"]) if topics is None else set(topics)
    if not selected.issubset(current["topics"]):
        raise ValueError("Unbound feed verification topic")

    def check(topic):
        spec = current["topics"][topic]
        raw = _fetch(topic, opener=opener, content_types=CONTENT_TYPES[spec["format"]])
        if _hash(raw) != spec["sha256"]:
            raise ValueError(f"Feed has not reached the bound generation: {topic}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(check, sorted(selected)))


def deliver(pages: Path, state_path: Path, source_sha: str, protocol: str, *,
            opener=urllib.request.urlopen) -> dict:
    if protocol not in {"websub", "rsscloud"} or not SHA.fullmatch(source_sha):
        raise ValueError("Invalid delivery protocol/source commit")
    with locked_state(state_path) as state:
        prepared = state.get("prepared", {})
        current = inventory(pages, prepared.get("include_legacy", False))
        if (prepared.get("source_sha") != source_sha
                or prepared.get("inventory_digest") != _digest(current)):
            raise ValueError("Outbox is not bound to this source and content generation")
        wanted = tasks(current)
        selected = {}
        for key, task in state["pending"].items():
            expected = wanted.get(key)
            if (expected is None or any(task.get(k) != v for k, v in expected.items())
                    or task.get("source_sha") != source_sha
                    or task.get("generation_digest") != current["generation_digest"]):
                raise ValueError("Pending notification is not source-bound")
            if task["protocol"] == protocol:
                selected[key] = task
        if not selected:
            return {"protocol": protocol, "accepted": 0, "pending": 0, "unchanged": True}
        verify(current, [task["topic"] for task in selected.values()], opener=opener)
        ordered = sorted(selected.items(), key=lambda pair: (
            pair[1].get("attempt_count", 0), pair[1]["topic"],
        ))
        groups = []
        if protocol == "rsscloud":
            groups = [[(key, task)] for key, task in ordered]
        else:
            by_hub = []
            for hub in WEBSUB_HUBS:
                members = [(key, task) for key, task in ordered
                           if task["endpoint"] == hub]
                by_hub.append([members[i:i + 25] for i in range(0, len(members), 25)])
            groups = [batches[i] for i in range(max(map(len, by_hub), default=0))
                      for batches in by_hub if i < len(batches)]
        accepted = 0
        failures = []
        failed_endpoints = set()
        elapsed_by_endpoint = {}
        deferred = 0
        for group in groups:
            endpoint = group[0][1]["endpoint"]
            if endpoint in failed_endpoints:
                continue
            if elapsed_by_endpoint.get(endpoint, 0) >= PROVIDER_BUDGET_SECONDS:
                deferred += 1
                continue
            receipts = []
            started = time.monotonic()
            try:
                if protocol == "websub":
                    notify_websub.notify(
                        topics=tuple(task["topic"] for _, task in group),
                        hub=group[0][1]["endpoint"], attempts=3, timeout=15,
                        receipt_sink=receipts.append,
                    )
                else:
                    notify_rsscloud.ping(
                        topic=group[0][1]["topic"], endpoint=group[0][1]["endpoint"],
                        attempts=3, timeout=15, receipt_sink=receipts.append,
                    )
                if len(receipts) != 1:
                    raise ValueError("Provider acknowledgement missing")
                receipt = receipts[0]
                if (not 200 <= receipt.get("http_status", 0) < 300
                        or not HASH.fullmatch(receipt.get("response_sha256", ""))
                        or not HASH.fullmatch(receipt.get("request_sha256", ""))):
                    raise ValueError("Invalid provider acknowledgement")
                for key, task in group:
                    state["accepted"][key] = {
                        **task, "accepted_at": receipt["accepted_at"],
                        "request_sha256": receipt["request_sha256"],
                        "response_sha256": receipt["response_sha256"],
                        "http_status": receipt["http_status"],
                    }
                    state["pending"].pop(key)
                    accepted += 1
                save_state(state_path, state)
            except (RuntimeError, ValueError, OSError, KeyError) as error:
                failures.append(type(error).__name__)
                failed_endpoints.add(endpoint)
                for key, _ in group:
                    state["pending"][key]["attempt_count"] = (
                        state["pending"][key].get("attempt_count", 0) + 1
                    )
                save_state(state_path, state)
            finally:
                elapsed_by_endpoint[endpoint] = (
                    elapsed_by_endpoint.get(endpoint, 0) + time.monotonic() - started
                )
        return {
            "protocol": protocol, "accepted": accepted,
            "pending": sum(t["protocol"] == protocol for t in state["pending"].values()),
            "failed_batches": len(failures),
            "deferred_batches": deferred,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify", "notify"))
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--include-legacy", action="store_true")
    parser.add_argument("--protocol", choices=("websub", "rsscloud"))
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.pages_dir, args.state, args.source_sha,
                             include_legacy=args.include_legacy)
        elif args.action == "verify":
            with locked_state(args.state) as state:
                prepared = state.get("prepared", {})
                current = inventory(args.pages_dir, prepared.get("include_legacy", False))
                if (prepared.get("source_sha") != args.source_sha
                        or prepared.get("inventory_digest") != _digest(current)):
                    raise ValueError("Readback is not bound to this source")
            verify(current)
            result = {"verified_topics": len(current["topics"])}
        else:
            if not args.protocol:
                parser.error("notify requires --protocol")
            result = deliver(args.pages_dir, args.state, args.source_sha, args.protocol)
    except (ValueError, RuntimeError, KeyError, OSError) as error:
        print(f"Owned feed delivery failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get("failed_batches") or result.get("pending") else 0


if __name__ == "__main__":
    raise SystemExit(main())
