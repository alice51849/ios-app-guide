#!/usr/bin/env python3
"""Verify the deployed RSS feed and notify its advertised rssCloud server."""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from rsscloud_config import RSSCLOUD_PING_URL

SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
RSS_FILE = "rss.xml"
TOPIC = f"{SITE}/{RSS_FILE}"
USER_AGENT = "iOS-App-Guide-rssCloud-Publisher/1.0"


def _request(url, data=None):
    headers = {
        "Accept": "application/json" if data is not None else "*/*",
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
    topic=TOPIC,
    attempts=6,
    timeout=10,
    delay=5,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    with open(os.path.join(feed_dir, RSS_FILE), "rb") as handle:
        expected = handle.read()
    last_error = "unknown error"
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(
                _request(topic), timeout=timeout
            ) as response:
                deployed = response.read()
            if deployed == expected:
                print("rssCloud deployment verified: 1 RSS feed")
                return
            last_error = "content mismatch"
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code}"
        except (urllib.error.URLError, OSError) as error:
            last_error = str(error)
        if attempt < attempts:
            print(
                f"rssCloud deploy check {attempt}/{attempts} failed: "
                f"{last_error}"
            )
            time.sleep(delay)
    raise RuntimeError(
        f"deployed RSS feed did not match this release: {last_error}"
    )


def _parse_result(body):
    try:
        payload = json.loads(body.decode("utf-8"))
        return payload.get("success") is True, str(payload.get("msg", ""))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        try:
            root = ET.fromstring(body)
        except ET.ParseError as error:
            raise ValueError("rssCloud returned an invalid response") from error
        return (
            root.attrib.get("success", "").lower() == "true",
            root.attrib.get("msg", ""),
        )


def ping(
    topic=TOPIC,
    endpoint=RSSCLOUD_PING_URL,
    attempts=3,
    timeout=20,
    delay=2,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    payload = urllib.parse.urlencode({"url": topic}).encode("ascii")
    last_error = "unknown error"
    completed_attempts = 0
    for attempt in range(1, attempts + 1):
        completed_attempts = attempt
        try:
            with urllib.request.urlopen(
                _request(endpoint, payload), timeout=timeout
            ) as response:
                status = response.status
                body = response.read()
            if 200 <= status < 300:
                success, message = _parse_result(body)
                if success:
                    print(
                        f"rssCloud notified: HTTP {status}, {message or topic}"
                    )
                    return message
                last_error = f"service rejected ping: {message or 'unknown'}"
                break
            last_error = f"HTTP {status}"
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code} {error.reason}"
            if 400 <= error.code < 500 and error.code != 429:
                break
        except (urllib.error.URLError, OSError, ValueError) as error:
            last_error = str(error)
        if attempt < attempts:
            print(
                f"rssCloud ping {attempt}/{attempts} failed: {last_error}"
            )
            time.sleep(delay)
    raise RuntimeError(
        f"rssCloud notification failed after {completed_attempts} attempts: "
        f"{last_error}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feed-dir",
        default=os.getcwd(),
        help="Directory containing the deployed RSS feed",
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
    ping(timeout=max(args.timeout, 20), delay=min(args.delay, 2))


if __name__ == "__main__":
    main()
