#!/usr/bin/env python3
"""Read-only HTTP readback of every published hero-task artifact."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import time
from urllib.parse import urlsplit
import urllib.request


def fetch(url: str) -> bytes:
    error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=20) as response:
                accepted = {
                    ".html": {"text/html"}, ".js": {"text/javascript", "application/javascript"},
                    ".css": {"text/css"}, ".csv": {"text/csv", "application/octet-stream"},
                    ".json": {"application/json", "application/feed+json"},
                    ".xml": {"application/xml", "text/xml"},
                }.get(PurePosixPath(urlsplit(url).path).suffix)
                if accepted and response.headers.get_content_type() not in accepted:
                    raise ValueError("Incorrect published artifact media type")
                payload = response.read(2_000_001)
                if len(payload) > 2_000_000:
                    raise ValueError("Artifact exceeds the readback size limit")
                return payload
        except (OSError, ValueError) as exc:
            error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Unable to read published artifact: {url}") from error


def verify(manifest_path: Path, base_url: str, *, fetcher=fetch) -> dict:
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("An HTTPS deployment base URL is required")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("schema_version") != 1 or manifest.get("locale_count") != 50:
        raise ValueError("Partial or unknown hero-task manifest")
    outputs = dict(manifest["outputs"])
    outputs["data/hero-tasks/manifest.json"] = hashlib.sha256(raw).hexdigest()
    for relative, expected in outputs.items():
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative or not isinstance(expected, str):
            raise ValueError("Unsafe manifest path")

    def check(item):
        relative, expected = item
        actual = hashlib.sha256(fetcher(f"{base_url}/{relative}")).hexdigest()
        if actual != expected:
            raise ValueError(f"Published artifact digest mismatch: {relative}")
        return relative

    with ThreadPoolExecutor(max_workers=4) as pool:
        verified = list(pool.map(check, sorted(outputs.items())))
    return {"verified_artifacts": len(verified), "locales": 50, "content_digest": manifest["content_digest"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest, args.base_url), sort_keys=True))


if __name__ == "__main__":
    main()
