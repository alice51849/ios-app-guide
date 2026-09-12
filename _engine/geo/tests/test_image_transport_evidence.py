"""Byte identity, decoded pixels and HTTP transport are independent evidence."""

import gzip
import io
import copy
import os
import struct
from pathlib import Path
import sys
import unittest
import zlib

from PIL import Image

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import image_transport_evidence as transport


def png(color="white"):
    output = io.BytesIO()
    Image.new("RGB", (3, 2), color).save(output, "PNG")
    return output.getvalue()


class ImageTransportEvidenceTests(unittest.TestCase):
    def test_cloud_observation_artifact_is_visible_and_never_deploys(self):
        guide = Path(os.environ.get("GEO_GUIDE_ROOT", GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages"))
        workflow = (guide / ".github/workflows/result-image-transport-audit.yml").read_text()
        self.assertIn("--output-dir image-transport-observations", workflow)
        self.assertIn("path: image-transport-observations", workflow)
        self.assertIn("--require-source-evidence", workflow)
        self.assertNotIn("pages: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("actions/deploy-pages", workflow)

    def test_reversible_transport_preserves_exact_entity_and_pixels(self):
        source = png()
        expected = transport.pixel_evidence(source)
        for encoding, wire in (
            ("identity", source), ("gzip", gzip.compress(source)),
            ("deflate", zlib.compress(source)),
        ):
            with self.subTest(encoding=encoding):
                entity = transport.decode_content(wire, encoding)
                self.assertEqual(source, entity)
                self.assertEqual(expected, transport.pixel_evidence(entity))

    def test_pixel_mutation_cannot_hide_behind_the_same_dimensions(self):
        before = transport.pixel_evidence(png())
        after = transport.pixel_evidence(png("black"))
        self.assertEqual((3, 2), (before["width"], before["height"]))
        self.assertEqual((before["width"], before["height"]), (after["width"], after["height"]))
        self.assertNotEqual(before["pixels_sha256"], after["pixels_sha256"])

    def test_unsupported_or_ambiguous_codings_fail_closed(self):
        for encoding in ("br", "gzip, identity", "unknown"):
            with self.subTest(encoding=encoding), self.assertRaises(ValueError):
                transport.decode_content(png(), encoding)
        wire = gzip.compress(png())
        for body in (wire[:-2], wire + b"extra", wire + wire):
            with self.subTest(body=body), self.assertRaises(ValueError):
                transport.decode_content(body, "gzip")

    def test_bounded_decoding_rejects_expansion(self):
        with self.assertRaisesRegex(ValueError, "Decoded image exceeds"):
            transport.decode_content(gzip.compress(b"x" * 200), "gzip", limit=100)

    def test_pixels_are_not_a_substitute_for_source_bytes(self):
        source = png()
        altered = source + b"metadata"
        self.assertEqual(
            transport.pixel_evidence(source)["pixels_sha256"],
            transport.pixel_evidence(altered)["pixels_sha256"],
        )
        self.assertNotEqual(transport.sha256(source), transport.sha256(altered))


def traced_jpeg(key="A" * 26, color="white"):
    output = io.BytesIO()
    Image.new("RGB", (3, 2), color).save(output, "JPEG")
    jpeg = output.getvalue()
    tiff = (
        b"MM\0\x2a\0\0\0\x08"
        + struct.pack(">HHHIII", 1, 0x8769, 4, 1, 26, 0)
        + struct.pack(">H", 4)
        + struct.pack(">HHII", 0x9286, 7, 34, 80)
        + struct.pack(">HHII", 0xA001, 3, 1, 1 << 16)
        + struct.pack(">HHII", 0xA002, 4, 1, 3)
        + struct.pack(">HHII", 0xA003, 4, 1, 2)
        + b"\0\0\0\0ASCII\0\0\0" + key.encode()
    )
    payload = b"Exif\0\0" + tiff
    segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    app0_end = 4 + int.from_bytes(jpeg[4:6], "big")
    return jpeg[:app0_end] + segment + jpeg[app0_end:]


class CorrelationTransportTests(unittest.TestCase):
    def setUp(self):
        self.source = traced_jpeg()
        self.offset, key = transport.apple_correlation_comment(self.source)
        self.asset = {
            "sha256": transport.sha256(self.source),
            "decoded_evidence": transport.pixel_evidence(self.source),
            "transport_reversal": {
                "algorithm": transport.APPLE_COMMENT_TRANSFORM,
                "source_correlation_key": key,
                "comment_offset": self.offset, "evidence_ref": "offline-fixture",
            },
        }
        self.headers = {
            "server": "daiquiri/5",
            "x-correlation-key": "B" * 26,
            "x-apple-jingle-correlation-key": "B" * 26,
        }
        self.wire = traced_jpeg("B" * 26)

    def test_only_header_bound_trace_replacement_restores_the_full_source_sha(self):
        canonical, proof = transport.canonical_asset_bytes(self.wire, self.asset, self.headers)
        self.assertEqual(self.source, canonical)
        self.assertNotEqual(transport.sha256(self.wire), self.asset["sha256"])
        self.assertEqual(transport.sha256(canonical), self.asset["sha256"])
        self.assertTrue(proof["roundtrip_verified"])
        actual = transport.verify_decoded_evidence(self.wire, canonical, self.asset)
        self.assertEqual(self.asset["decoded_evidence"]["pixels_sha256"], actual["pixels_sha256"])

    def test_canonical_source_requires_its_own_pinned_trace_key(self):
        canonical, proof = transport.canonical_asset_bytes(self.source, self.asset, {})
        self.assertEqual(self.source, canonical)
        self.assertEqual({}, proof)
        changed = copy.deepcopy(self.asset)
        changed["transport_reversal"]["source_correlation_key"] = "C" * 26
        with self.assertRaises(ValueError):
            transport.canonical_asset_bytes(self.source, changed, {})

    def test_missing_or_disagreeing_apple_headers_are_not_a_hash_waiver(self):
        for headers in (
            {}, {**self.headers, "server": "other"},
            {**self.headers, "x-correlation-key": "C" * 26},
            {**self.headers, "x-apple-jingle-correlation-key": ""},
        ):
            with self.subTest(headers=headers), self.assertRaises(ValueError):
                transport.canonical_asset_bytes(self.wire, self.asset, headers)

    def test_pixel_and_other_metadata_changes_still_fail_the_full_digest(self):
        metadata = bytearray(self.wire)
        metadata[14] ^= 1
        self.assertEqual(
            transport.pixel_evidence(self.wire)["pixels_sha256"],
            transport.pixel_evidence(bytes(metadata))["pixels_sha256"],
        )
        for body in (traced_jpeg("B" * 26, "black"), bytes(metadata), self.wire + b"extra"):
            with self.subTest(body=transport.sha256(body)), self.assertRaisesRegex(
                ValueError, "SHA-256 drift outside",
            ):
                transport.canonical_asset_bytes(body, self.asset, self.headers)

    def test_new_byte_hash_does_not_implicitly_reapprove_changed_pixels(self):
        changed = traced_jpeg("A" * 26, "black")
        with self.assertRaisesRegex(ValueError, "decoded pixel"):
            transport.verify_decoded_evidence(changed, changed, self.asset)

    def test_unbound_offset_or_arbitrary_user_comment_is_rejected(self):
        asset = copy.deepcopy(self.asset)
        asset["transport_reversal"]["comment_offset"] += 1
        with self.assertRaisesRegex(ValueError, "offset drift"):
            transport.canonical_asset_bytes(self.wire, asset, self.headers)
        arbitrary = self.wire[:self.offset] + b"UTF8\0\0\0\0" + self.wire[self.offset + 8:]
        with self.assertRaisesRegex(ValueError, "UserComment encoding"):
            transport.canonical_asset_bytes(arbitrary, self.asset, self.headers)


if __name__ == "__main__":
    unittest.main()
