#!/usr/bin/env python3
"""GET-only image transport observations; a matching pixel hash is not a SHA waiver."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zlib

from PIL import Image, features


MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 20_000_000
HEADERS = (
    "content-type", "content-encoding", "content-length", "transfer-encoding",
    "cache-control", "vary", "etag", "last-modified", "date", "age", "server",
    "via", "x-cache", "x-cdn", "x-served-by", "cf-cache-status", "cf-polished",
    "cf-resized", "cf-mirage", "accept-ranges",
)
VARIANTS = {
    "production": {"Accept-Encoding": "identity"},
    "no-cache": {"Accept-Encoding": "identity", "Cache-Control": "no-cache"},
    "gzip": {"Accept-Encoding": "gzip", "Cache-Control": "no-cache"},
    "jpeg": {"Accept-Encoding": "identity", "Accept": "image/jpeg"},
}


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def decode_content(body: bytes, encoding: str, *, limit: int = MAX_BYTES) -> bytes:
    if len(body) > limit:
        raise ValueError("Encoded image exceeds its byte limit")
    encoding = encoding.strip().lower()
    if encoding in {"", "identity"}:
        return body
    if encoding not in {"gzip", "deflate"}:
        raise ValueError(f"Unsupported reversible Content-Encoding: {encoding}")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == "gzip" else zlib.MAX_WBITS)
    try:
        decoded = decoder.decompress(body, limit + 1)
    except zlib.error as error:
        raise ValueError("Invalid encoded image transport") from error
    if len(decoded) > limit or decoder.unconsumed_tail:
        raise ValueError("Decoded image exceeds its byte limit")
    if not decoder.eof or decoder.unused_data:
        raise ValueError("Truncated or trailing encoded image transport")
    return decoded


def pixel_evidence(body: bytes) -> dict:
    with Image.open(io.BytesIO(body)) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ValueError("Image exceeds its bounded pixel limit")
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError("A screenshot must have exactly one frame")
        image.verify()
    with Image.open(io.BytesIO(body)) as image:
        image.load()
        pixels = image.convert("RGBA")
        descriptor = f"rgba8:{image.width}x{image.height}:".encode()
        return {
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "pixel_algorithm": "sha256-rgba8-dimensions-v1",
            "pixels_sha256": sha256(descriptor + pixels.tobytes()),
            "rgb_sha256": sha256(image.convert("RGB").tobytes()),
            "exif_sha256": sha256(image.info.get("exif", b"")),
            "icc_sha256": sha256(image.info.get("icc_profile", b"")),
            "orientation": image.getexif().get(274, 1),
        }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def observe(asset: dict, variant: str, output: Path) -> dict:
    url = asset["canonical_asset_url"]
    headers = {"User-Agent": "Lumi-Public-Image-Check/1.0", **VARIANTS[variant]}
    request = Request(url, method="GET", headers=headers)
    try:
        response = build_opener(NoRedirect()).open(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(MAX_BYTES + 1)
        result = {
            "asset_id": asset["id"], "variant": variant, "url": url,
            "final_url": response.geturl(), "status": response.status,
            "request_headers": headers,
            "headers": {key: ", ".join(response.headers.get_all(key)) for key in HEADERS
                        if response.headers.get(key) is not None},
            "raw_headers": [[key.lower(), value] for key, value in response.headers.raw_items()
                            if key.lower() in HEADERS],
            "source_sha256": asset["sha256"], "wire_sha256": sha256(body),
            "wire_bytes": len(body),
        }
    if len(body) > MAX_BYTES:
        raise ValueError("Public image response exceeds its byte limit")
    prefix = output / f"{asset['id']}-{variant}"
    prefix.with_suffix(".wire.bin").write_bytes(body)
    try:
        entity = decode_content(body, result["headers"].get("content-encoding", ""))
        prefix.with_suffix(".entity.bin").write_bytes(entity)
        result.update(
            entity_sha256=sha256(entity), entity_bytes=len(entity),
            source_bytes_match=sha256(entity) == asset["sha256"],
            decoded=pixel_evidence(entity),
        )
    except (OSError, ValueError, zlib.error) as error:
        result["decode_error"] = str(error)
    return result


def main() -> None:
    from result_image_index import MANIFEST, validate_manifest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    body = args.manifest.read_bytes()
    manifest = json.loads(body)
    validate_manifest(manifest)
    if args.output_dir.is_symlink():
        raise ValueError("Observation output cannot be a symlink")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for asset in manifest["images"]:
        for variant in VARIANTS:
            row = observe(asset, variant, args.output_dir)
            rows.append(row)
            print(json.dumps({
                key: row.get(key) for key in
                ("asset_id", "variant", "source_bytes_match", "entity_sha256", "decode_error")
            }), flush=True)
    report = {
        "schema_version": 1, "context": args.context,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256(body),
        "source_sha": subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD"],
            text=True, timeout=15,
        ).strip(),
        "generator_sha256": sha256(Path(__file__).read_bytes()),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "python": sys.version, "platform": platform.platform(),
        "pillow": Image.__version__, "jpeg_decoder": features.version("jpg"),
        "proxy_environment_present": any(os.environ.get(key) for key in
                                         ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")),
        "observations": rows,
        "scope": "transport_observation_not_publication_or_indexing",
    }
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
