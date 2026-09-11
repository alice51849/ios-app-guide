"""Byte identity, decoded pixels and HTTP transport are independent evidence."""

import gzip
import io
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
        guide = GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages"
        workflow = (guide / ".github/workflows/result-image-transport-audit.yml").read_text()
        self.assertIn("--output-dir image-transport-observations", workflow)
        self.assertIn("path: image-transport-observations", workflow)
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


if __name__ == "__main__":
    unittest.main()
