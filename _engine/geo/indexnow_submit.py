#!/usr/bin/env python3
"""Submit every public GEO sitemap URL to IndexNow with strict delivery checks."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


HERE = Path(__file__).resolve().parent
DEFAULT_SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
ENDPOINTS = (
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
)
ACCEPTED_STATUSES = {200, 202}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
KEY_RE = re.compile(r"[A-Za-z0-9_-]{8,128}")


class SubmissionError(RuntimeError):
    """Raised when an IndexNow endpoint does not accept a batch."""


def sitemap_locations(path: Path) -> list[str]:
    if not path.is_file():
        raise ValueError(f"Missing sitemap: {path}")
    content = path.read_text(encoding="utf-8")
    return [
        html.unescape(value.strip())
        for value in re.findall(r"<loc>([^<]+)</loc>", content)
        if value.strip()
    ]


def validate_public_url(url: str, site: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(site)
    base_path = expected.path.rstrip("/") + "/"
    if (
        parsed.scheme != "https"
        or parsed.netloc != expected.netloc
        or not parsed.path.startswith(base_path)
        or parsed.query
        or parsed.fragment
        or len(url) > 2048
        or any(character.isspace() for character in url)
    ):
        raise ValueError(f"Invalid IndexNow URL for {site}: {url}")


def is_same_host_out_of_scope(url: str, site: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(site)
    base_path = expected.path.rstrip("/") + "/"
    return (
        parsed.scheme == "https"
        and parsed.netloc == expected.netloc
        and not parsed.path.startswith(base_path)
        and not parsed.query
        and not parsed.fragment
        and len(url) <= 2048
        and not any(character.isspace() for character in url)
    )


def read_urls(pages_dir: Path, site: str) -> list[str]:
    sitemap_index = pages_dir / "sitemap_index.xml"
    sitemap_paths: list[Path] = []
    if sitemap_index.is_file():
        for location in sitemap_locations(sitemap_index):
            validate_public_url(location, site)
            name = Path(urllib.parse.urlsplit(location).path).name
            candidate = pages_dir / name
            if name.endswith(".xml") and candidate.is_file():
                sitemap_paths.append(candidate)
    if not sitemap_paths:
        sitemap_paths = [pages_dir / "sitemap.xml"]

    urls: list[str] = []
    seen: set[str] = set()
    excluded_out_of_scope = 0
    for sitemap_path in sitemap_paths:
        for url in sitemap_locations(sitemap_path):
            try:
                validate_public_url(url, site)
            except ValueError:
                if is_same_host_out_of_scope(url, site):
                    excluded_out_of_scope += 1
                    continue
                raise
            if url not in seen:
                seen.add(url)
                urls.append(url)
    print(f"excluded_out_of_scope={excluded_out_of_scope}")
    if not urls:
        raise ValueError("IndexNow sitemap collection returned zero URLs")
    return urls


def read_key(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Missing IndexNow key file: {path}")
    key = path.read_text(encoding="utf-8").strip()
    if not KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key must be 8-128 URL-safe characters")
    return key


def payload_for(urls: list[str], key: str, site: str) -> bytes:
    host = urllib.parse.urlsplit(site).netloc
    return json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": f"{site}/{key}.txt",
            "urlList": urls,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def submit_endpoint(
    endpoint: str,
    payload: bytes,
    *,
    opener=None,
    sleeper=time.sleep,
) -> None:
    opener = urllib.request.urlopen if opener is None else opener
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "ios-app-guide-indexnow/2.0",
            },
        )
        try:
            with opener(request, timeout=90) as response:
                body = response.read(1000).decode("utf-8", "replace").strip()
                if response.status not in ACCEPTED_STATUSES:
                    raise SubmissionError(
                        f"{endpoint} returned HTTP {response.status}: {body}"
                    )
                print(f"  {endpoint} -> HTTP {response.status}")
                return
        except urllib.error.HTTPError as error:
            body = error.read(1000).decode("utf-8", "replace").strip()
            last_error = SubmissionError(
                f"{endpoint} returned HTTP {error.code}: {body}"
            )
            if error.code not in RETRYABLE_STATUSES:
                raise last_error from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
        if attempt < 3:
            sleeper(2 ** (attempt - 1))
    raise SubmissionError(
        f"{endpoint} failed after 3 attempts: {last_error}"
    ) from last_error


def submit(
    urls: list[str],
    key: str,
    site: str = DEFAULT_SITE,
    *,
    endpoints: tuple[str, ...] = ENDPOINTS,
    sender=submit_endpoint,
) -> bool:
    """Compatibility helper that reports failure after trying every endpoint."""
    payload = payload_for(urls, key, site)
    accepted = True
    for endpoint in endpoints:
        try:
            sender(endpoint, payload)
        except SubmissionError as error:
            print(error)
            accepted = False
    return accepted


def submit_all(
    urls: list[str],
    key: str,
    site: str,
    *,
    batch_size: int = 1000,
    endpoints: tuple[str, ...] = ENDPOINTS,
    sender=submit_endpoint,
) -> int:
    if not 1 <= batch_size <= 10_000:
        raise ValueError("IndexNow batch size must be between 1 and 10000")
    accepted = 0
    for offset in range(0, len(urls), batch_size):
        chunk = urls[offset : offset + batch_size]
        print(
            f"batch {offset // batch_size + 1}: "
            f"{len(chunk)} URLs"
        )
        payload = payload_for(chunk, key, site)
        for endpoint in endpoints:
            sender(endpoint, payload)
        accepted += len(chunk)
    return accepted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=HERE / "pages")
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument(
        "--key-file", type=Path, default=HERE / "indexnow_key.txt"
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    site = args.site.rstrip("/")
    key = read_key(args.key_file)
    urls = read_urls(args.pages_dir, site)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("IndexNow limit must be positive")
        urls = urls[: args.limit]
    print(
        f"host={urllib.parse.urlsplit(site).netloc} "
        f"key={key[:8]}... urls={len(urls)}"
    )
    accepted = submit_all(
        urls,
        key,
        site,
        batch_size=args.batch_size,
    )
    print(f"Accepted {accepted}/{len(urls)} URLs by every IndexNow endpoint")
    if accepted != len(urls):
        raise SubmissionError(
            f"Only {accepted}/{len(urls)} IndexNow URLs were accepted"
        )


if __name__ == "__main__":
    main()
