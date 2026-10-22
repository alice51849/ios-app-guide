#!/usr/bin/env python3
"""Read-only HTTP readback of every published hero-task artifact."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import http.client
import json
from pathlib import Path, PurePosixPath
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from deployment_generation import GenerationError, READBACK_USER_AGENT, verify_output_bytes

_CLIENTS = threading.local()


def _close_client():
    client = getattr(_CLIENTS, "client", None)
    if client is not None:
        client.close()
    _CLIENTS.client = None


def fetch(url: str) -> bytes:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.fragment
        or parsed.username is not None or parsed.password is not None
    ):
        raise ValueError("Artifact GET requires a credential-free HTTPS URL")
    authority = (parsed.hostname, parsed.port or 443)
    target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    error = None
    for attempt in range(3):
        try:
            if (
                getattr(_CLIENTS, "client", None) is None
                or getattr(_CLIENTS, "authority", None) != authority
            ):
                _close_client()
                _CLIENTS.client = http.client.HTTPSConnection(*authority, timeout=20)
                _CLIENTS.authority = authority
            _CLIENTS.client.request("GET", target, headers={
                "Cache-Control": "no-cache",
                "User-Agent": READBACK_USER_AGENT,
                "Accept-Encoding": "identity",
            })
            with _CLIENTS.client.getresponse() as response:
                if response.status != 200:
                    raise ValueError("Published artifact HTTP status or endpoint differs")
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
        except (OSError, ValueError, http.client.HTTPException) as exc:
            _close_client()
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
        try:
            return verify_output_bytes(
                fetcher(f"{base_url}/{relative}"),
                site=base_url, relative=relative, expected_sha256=expected,
            )
        except GenerationError as error:
            raise ValueError(f"Published artifact digest mismatch: {relative}") from error

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(check, item) for item in sorted(outputs.items())]
        try:
            verified = [future.result() for future in as_completed(futures)]
        except Exception:
            for future in futures:
                future.cancel()
            raise
    return {
        "verified_artifacts": len(verified), "locales": 50,
        "content_digest": manifest["content_digest"],
        "pinned_edge_transform_count": sum("edge_transform" in row for row in verified),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest, args.base_url), sort_keys=True))


if __name__ == "__main__":
    main()
