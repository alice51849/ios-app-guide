#!/usr/bin/env python3
"""Low-frequency, GET-only exact-150 public capture without following redirects."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from deployment_generation import validate_binding
import owned_app_feeds as feeds


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def capture(pages: Path, output: Path, *, interval=1.05, opener=None, sleeper=time.sleep) -> dict:
    if interval < 1:
        raise ValueError("Public capture is limited to at most one GET per second")
    candidate = feeds.read_manifest(pages)
    output.mkdir(parents=True, exist_ok=True)
    (output / "bodies").mkdir(exist_ok=True)
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    last = 0.0
    def get(url):
        nonlocal last
        sleeper(max(0, interval - (time.monotonic() - last)))
        last = time.monotonic()
        row = {"url": url, "method": "GET", "observed_at": datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "Lumi-Owned-Feed-Reconciliation/1.0",
                "Cache-Control": "no-cache", "Accept": "*/*",
            })
            try:
                response = opener(request, timeout=15)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                raw = response.read(feeds.MAX_BYTES + 1)
                digest = feeds.sha256(raw)
                path = output / "bodies" / digest
                if not path.exists():
                    path.write_bytes(raw)
                    path.chmod(0o600)
                row.update({
                    "http_status": response.status, "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type", ""),
                    "location": response.headers.get("Location"),
                    "body_sha256": digest, "body_path": f"bodies/{digest}", "bytes": len(raw),
                })
                if len(raw) > feeds.MAX_BYTES:
                    row["error"] = "oversized_body"
        except (urllib.error.URLError, OSError) as error:
            row.update(http_status=None, error=type(error).__name__)
        return row
    before = get(feeds.url(".well-known/deployment.json"))
    if before.get("http_status") != 200 or before.get("final_url") != before["url"]:
        raise ValueError("Production deployment cannot be bound")
    document = feeds.decode((output / before["body_path"]).read_bytes())
    generation = validate_binding(document)
    public_manifest = get(feeds.url(feeds.INDEX))
    rows = []
    for locale, row in candidate["feeds"].items():
        for fmt, spec in row["formats"].items():
            observation = get(spec["url"])
            observation.update(locale=locale, format=fmt)
            rows.append(observation)
    after = get(feeds.url(".well-known/deployment.json"))
    result = {
        "schema": "lumi.owned-feed-public-capture/v1", "site": feeds.SITE,
        "generation": generation, "deployment": document,
        "deployment_before": before, "deployment_after": after,
        "public_manifest": public_manifest, "endpoints": rows,
        "stable_generation": before["body_sha256"] == after.get("body_sha256"),
        "network_method": "GET", "notification_requests": 0,
    }
    result["capture_digest"] = feeds.digest(result)
    path = output / "capture.json"
    path.write_bytes(feeds.json_bytes(result))
    path.chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    result = capture(args.pages_dir, args.output_dir)
    print(json.dumps({"endpoints": len(result["endpoints"]), "stable_generation": result["stable_generation"],
                      "notification_requests": 0}))


if __name__ == "__main__":
    main()
