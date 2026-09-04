#!/usr/bin/env python3
"""Verify deployed feeds and notify their advertised WebSub hubs."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from official_locales import OFFICIAL_LOCALES
from websub_config import WEBSUB_HUBS

# pages.yml copies this file alone into RUNNER_TEMP, without its siblings,
# so it cannot import site_config. The workflow pins GEO_SITE to the same
# host site_config.PUBLIC_SITE declares; this literal is only the fallback.
SITE = os.environ.get(
    "GEO_SITE", "https://open.cait518.cc/ios-app-guide"
).rstrip("/")
FEED_FILES = (
    "feed.xml",
    "rss.xml",
    "feed.json",
    "data/high-intent-decision-routes/feed.json",
)
TOPICS = tuple(f"{SITE}/{filename}" for filename in FEED_FILES)
LOCALIZED_ATOM_DIR = Path("data") / "app-install-decision-routes" / "feeds"
VERIFY_WORKERS = 6
USER_AGENT = "iOS-App-Guide-WebSub-Publisher/2.0"


def discover_topics(feed_dir):
    root = Path(feed_dir)
    expected_paths = tuple(
        root / LOCALIZED_ATOM_DIR / f"{locale}.atom.xml"
        for locale in OFFICIAL_LOCALES
    )
    actual_paths = set((root / LOCALIZED_ATOM_DIR).glob("*.atom.xml"))
    expected_set = set(expected_paths)
    missing = sorted(path.name for path in expected_set - actual_paths)
    unexpected = sorted(path.name for path in actual_paths - expected_set)
    missing_feeds = [
        filename for filename in FEED_FILES if not (root / filename).is_file()
    ]
    if missing_feeds or missing or unexpected:
        details = []
        if missing_feeds:
            details.append(f"missing feeds={','.join(missing_feeds)}")
        if missing:
            details.append(f"missing localized={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected localized={','.join(unexpected)}")
        raise RuntimeError("invalid WebSub feed inventory: " + "; ".join(details))
    localized_topics = tuple(
        f"{SITE}/{path.relative_to(root).as_posix()}" for path in expected_paths
    )
    return TOPICS + localized_topics


def _local_feed_path(feed_dir, topic):
    root = Path(feed_dir).resolve()
    site = urllib.parse.urlsplit(SITE)
    parsed = urllib.parse.urlsplit(topic)
    prefix = site.path.rstrip("/") + "/"
    if (
        parsed.scheme != site.scheme
        or parsed.netloc != site.netloc
        or not parsed.path.startswith(prefix)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"WebSub topic is outside {SITE}: {topic}")
    relative = urllib.parse.unquote(parsed.path[len(prefix) :])
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"WebSub topic escapes feed directory: {topic}")
    return candidate


def _request(url, data=None):
    headers = {
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": USER_AGENT,
    }
    if data is not None:
        headers["Content-Type"] = (
            "application/x-www-form-urlencoded; charset=utf-8"
        )
    return urllib.request.Request(url, data=data, headers=headers)


def wait_until_deployed(
    feed_dir,
    topics=None,
    attempts=6,
    timeout=20,
    delay=5,
    workers=VERIFY_WORKERS,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    topics = discover_topics(feed_dir) if topics is None else tuple(topics)
    if not topics:
        raise ValueError("at least one WebSub topic is required")
    expected = {
        topic: _local_feed_path(feed_dir, topic).read_bytes()
        for topic in topics
    }

    pending_topics = set(topics)
    pending = []
    for attempt in range(1, attempts + 1):
        failures = {}

        def check(topic):
            try:
                with urllib.request.urlopen(
                    _request(topic), timeout=timeout
                ) as response:
                    deployed = response.read()
                if deployed != expected[topic]:
                    return f"{topic}: content mismatch"
            except urllib.error.HTTPError as error:
                return f"{topic}: HTTP {error.code}"
            except (urllib.error.URLError, OSError) as error:
                return f"{topic}: {error}"
            return None

        with ThreadPoolExecutor(
            max_workers=min(workers, len(pending_topics))
        ) as executor:
            futures = {
                executor.submit(check, topic): topic
                for topic in pending_topics
            }
            for future in as_completed(futures):
                failure = future.result()
                if failure:
                    failures[futures[future]] = failure
        pending_topics = set(failures)
        pending = sorted(failures.values())
        if not pending:
            print(f"WebSub deployment verified: {len(topics)} feeds")
            return
        if attempt < attempts:
            print(
                f"WebSub deploy check {attempt}/{attempts}: "
                + "; ".join(pending)
            )
            time.sleep(delay)
    raise RuntimeError(
        "deployed feeds did not match this release: " + "; ".join(pending)
    )


def notify(
    topics=TOPICS,
    hub=WEBSUB_HUBS[0],
    attempts=3,
    timeout=20,
    delay=2,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    fields = [("hub.mode", "publish")]
    fields.extend(("hub.url", topic) for topic in topics)
    payload = urllib.parse.urlencode(fields).encode("ascii")
    last_error = "unknown error"
    completed_attempts = 0
    for attempt in range(1, attempts + 1):
        completed_attempts = attempt
        try:
            with urllib.request.urlopen(
                _request(hub, payload), timeout=timeout
            ) as response:
                status = response.status
            if 200 <= status < 300:
                print(
                    f"WebSub hub notified: {hub} HTTP {status}, "
                    f"{len(topics)} topics"
                )
                return status
            last_error = f"HTTP {status}"
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code} {error.reason}"
            if 400 <= error.code < 500 and error.code != 429:
                break
        except (urllib.error.URLError, OSError) as error:
            last_error = str(error)
        if attempt < attempts:
            print(
                f"WebSub notify {attempt}/{attempts} failed: {last_error}"
            )
            time.sleep(delay)
    raise RuntimeError(
        f"WebSub hub notification failed after {completed_attempts} attempts: "
        f"{last_error}"
    )


def notify_all(
    hubs=WEBSUB_HUBS,
    topics=TOPICS,
    attempts=3,
    timeout=20,
    delay=2,
):
    if not hubs:
        raise ValueError("at least one WebSub hub is required")
    results = {}
    failures = []
    for hub in hubs:
        try:
            results[hub] = notify(
                topics=topics,
                hub=hub,
                attempts=attempts,
                timeout=timeout,
                delay=delay,
            )
        except RuntimeError as error:
            failures.append(f"{hub}: {error}")
    if failures:
        raise RuntimeError(
            "one or more WebSub hub notifications failed: "
            + "; ".join(failures)
        )
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feed-dir",
        default=os.getcwd(),
        help="Directory containing the deployed feed files",
    )
    parser.add_argument("--deploy-attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    topics = discover_topics(args.feed_dir)
    wait_until_deployed(
        args.feed_dir,
        topics=topics,
        attempts=args.deploy_attempts,
        timeout=args.timeout,
        delay=args.delay,
    )
    notify_all(
        topics=topics,
        timeout=max(args.timeout, 20),
        delay=min(args.delay, 2),
    )


if __name__ == "__main__":
    main()
