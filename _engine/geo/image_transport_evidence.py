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
import re
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
    "x-correlation-key", "x-apple-jingle-correlation-key",
)
CORRELATION = re.compile(r"[A-Z2-7]{26}")
APPLE_COMMENT_TRANSFORM = "apple-daiquiri-user-comment-v1"
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


def apple_correlation_comment(body: bytes) -> tuple[int, str]:
    """Locate one ExifIFD UserComment structurally, never scan/strip arbitrary metadata."""
    if not body.startswith(b"\xff\xd8"):
        raise ValueError("Correlation transport requires a JPEG")
    cursor, exif = 2, None
    while cursor + 4 <= len(body):
        if body[cursor] != 0xFF:
            raise ValueError("Invalid JPEG marker before image data")
        marker = body[cursor + 1]
        if marker in {0xDA, 0xD9}:
            break
        length = int.from_bytes(body[cursor + 2:cursor + 4], "big")
        end = cursor + 2 + length
        if length < 2 or end > len(body):
            raise ValueError("Truncated JPEG metadata")
        start = cursor + 4
        if marker == 0xE1 and body[start:start + 6] == b"Exif\0\0":
            if exif is not None:
                raise ValueError("Multiple EXIF segments are ambiguous")
            exif = (start + 6, end)
        cursor = end
    if exif is None:
        raise ValueError("Missing source-bound EXIF correlation comment")
    base, end = exif
    order = {b"II": "little", b"MM": "big"}.get(body[base:base + 2])
    if order is None:
        raise ValueError("Invalid TIFF byte order")

    def integer(offset: int, count: int) -> int:
        if offset < base or offset + count > end:
            raise ValueError("EXIF offset escapes its APP1 segment")
        return int.from_bytes(body[offset:offset + count], order)

    def entries(offset: int) -> dict[int, tuple[int, int, int]]:
        if offset < base + 8:
            raise ValueError("Invalid EXIF directory offset")
        count = integer(offset, 2)
        if count > 128 or offset + 2 + count * 12 + 4 > end:
            raise ValueError("Invalid bounded EXIF directory")
        result = {}
        for index in range(count):
            entry = offset + 2 + index * 12
            tag = integer(entry, 2)
            if tag in result:
                raise ValueError("Duplicate EXIF tag")
            result[tag] = (integer(entry + 2, 2), integer(entry + 4, 4),
                           integer(entry + 8, 4))
        return result

    if integer(base + 2, 2) != 42:
        raise ValueError("Invalid TIFF signature")
    pointer = entries(base + integer(base + 4, 4)).get(0x8769)
    if pointer is None or pointer[:2] != (4, 1):
        raise ValueError("Missing unique ExifIFD pointer")
    comment = entries(base + pointer[2]).get(0x9286)
    if comment is None or comment[:2] != (7, 34):
        raise ValueError("Not a fixed ASCII Apple correlation comment")
    offset = base + comment[2]
    integer(offset, 34)
    if body[offset:offset + 8] != b"ASCII\0\0\0":
        raise ValueError("Unexpected EXIF UserComment encoding")
    key = body[offset + 8:offset + 34].decode("ascii")
    if CORRELATION.fullmatch(key) is None:
        raise ValueError("Not an Apple correlation key")
    return offset, key


def canonical_asset_bytes(entity: bytes, asset: dict, headers: dict) -> tuple[bytes, dict]:
    """Reverse only a header-bound CDN trace key, then require the original full SHA."""
    wire_digest = sha256(entity)
    contract = asset.get("transport_reversal")
    if contract is None:
        if wire_digest != asset["sha256"]:
            raise ValueError("public image SHA-256 drift")
        return entity, {}
    if (
        not isinstance(contract, dict)
        or set(contract) != {"algorithm", "source_correlation_key", "comment_offset", "evidence_ref"}
        or contract["algorithm"] != APPLE_COMMENT_TRANSFORM
        or CORRELATION.fullmatch(str(contract["source_correlation_key"])) is None
        or type(contract["comment_offset"]) is not int
        or not contract["evidence_ref"]
    ):
        raise ValueError("Invalid source-bound correlation transport contract")
    offset, observed_key = apple_correlation_comment(entity)
    if offset != contract["comment_offset"]:
        raise ValueError("Source-bound EXIF correlation offset drift")
    source_key = contract["source_correlation_key"]
    if wire_digest == asset["sha256"]:
        if observed_key != source_key:
            raise ValueError("Canonical source correlation binding drift")
        return entity, {}
    if (
        headers.get("server") != "daiquiri/5"
        or headers.get("x-correlation-key") != observed_key
        or headers.get("x-apple-jingle-correlation-key") != observed_key
    ):
        raise ValueError("CDN correlation comment is not bound to both Apple response headers")
    start = offset + 8
    canonical = entity[:start] + source_key.encode("ascii") + entity[start + 26:]
    restored = canonical[:start] + observed_key.encode("ascii") + canonical[start + 26:]
    if restored != entity or sha256(canonical) != asset["sha256"]:
        raise ValueError("public image SHA-256 drift outside the reversible CDN correlation")
    return canonical, {
        "transport_transform": APPLE_COMMENT_TRANSFORM,
        "observed_correlation_key": observed_key,
        "source_correlation_key": source_key,
        "comment_offset": offset, "roundtrip_verified": True,
    }


def verify_decoded_evidence(entity: bytes, canonical: bytes, asset: dict) -> dict:
    expected = asset.get("decoded_evidence")
    canonical_pixels = pixel_evidence(canonical)
    actual = pixel_evidence(entity)
    if canonical_pixels != expected:
        raise ValueError("Source-bound decoded pixel or metadata evidence drift")
    if any(actual[key] != expected[key] for key in expected if key != "exif_sha256"):
        raise ValueError("Decoded image pixels, dimensions or color interpretation drift")
    return actual


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
        if asset.get("decoded_evidence"):
            canonical, reversal = canonical_asset_bytes(entity, asset, result["headers"])
            result.update(
                canonical_sha256=sha256(canonical), canonical_source_verified=True,
                decoded_verified=verify_decoded_evidence(entity, canonical, asset), **reversal,
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
    parser.add_argument("--require-source-evidence", action="store_true")
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
    if args.require_source_evidence and any(
        row.get("canonical_source_verified") is not True or not row.get("decoded_verified")
        for row in rows
    ):
        raise ValueError("Cloud image observation did not satisfy canonical SHA and decoded evidence")


if __name__ == "__main__":
    main()
