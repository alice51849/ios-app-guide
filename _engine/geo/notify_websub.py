#!/usr/bin/env python3
"""Verify deployed feeds and notify their advertised WebSub hub."""
from __future__ import annotations

import argparse
import os
import time
import urllib.error
import urllib.parse
import urllib.request

SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
HUB = os.environ.get(
    "WEBSUB_HUB", "https://pubsubhubbub.appspot.com/"
)
FEED_FILES = ("feed.xml", "rss.xml", "feed.json")
TOPICS = tuple(f"{SITE}/{filename}" for filename in FEED_FILES)
USER_AGENT = "iOS-App-Guide-WebSub-Publisher/1.0"


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
    topics=TOPICS,
    attempts=6,
    timeout=10,
    delay=5,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    expected = {}
    for topic in topics:
        filename = os.path.basename(urllib.parse.urlsplit(topic).path)
        with open(os.path.join(feed_dir, filename), "rb") as handle:
            expected[topic] = handle.read()

    pending = []
    for attempt in range(1, attempts + 1):
        pending = []
        for topic in topics:
            try:
                with urllib.request.urlopen(
                    _request(topic), timeout=timeout
                ) as response:
                    deployed = response.read()
                if deployed != expected[topic]:
                    pending.append(f"{topic}: content mismatch")
            except urllib.error.HTTPError as error:
                pending.append(f"{topic}: HTTP {error.code}")
            except (urllib.error.URLError, OSError) as error:
                pending.append(f"{topic}: {error}")
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
    hub=HUB,
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
                    f"WebSub hub notified: HTTP {status}, "
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feed-dir",
        default=os.getcwd(),
        help="Directory containing the deployed feed files",
    )
    parser.add_argument("--deploy-attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    wait_until_deployed(
        args.feed_dir,
        attempts=args.deploy_attempts,
        timeout=args.timeout,
        delay=args.delay,
    )
    notify(timeout=max(args.timeout, 20), delay=min(args.delay, 2))


if __name__ == "__main__":
    main()
