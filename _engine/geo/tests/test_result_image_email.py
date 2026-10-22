"""Cloudflare's documented source opt-out must keep the real contact readable."""

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import result_image_index as images
import deployment_generation as generation


class Contact(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.visible = []
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a":
            self.links.append(values.get("href"))

    def handle_data(self, data):
        self.visible.append(data)


class ResultImageEmailTests(unittest.TestCase):
    def test_reviewed_and_quarantined_pages_keep_the_documented_opt_out(self):
        manifest = json.loads(images.MANIFEST.read_text())
        apps = {row["key"]: row for row in manifest["apps"]}
        for assets in (manifest["images"], []):
            with self.subTest(ready=bool(assets)):
                source = images.render_gallery(
                    "en-US", assets, manifest["labels"]["en-US"], apps, images.PUBLIC_SITE,
                )
                protected = (
                    '<!--email_off--><a href="mailto:hourstag.app@gmail.com">'
                    'hourstag.app@gmail.com</a><!--/email_off-->'
                )
                self.assertIn(protected, source)
                contact = Contact(source)
                self.assertIn("mailto:hourstag.app@gmail.com", contact.links)
                self.assertIn("hourstag.app@gmail.com", contact.visible)
                for forbidden in ("__cf_email__", "data-cfemail", "email-decode.min.js",
                                  "display:none", "visibility:hidden", "alice51849@hotmail.com"):
                    self.assertNotIn(forbidden, source)

    def source(self):
        manifest = json.loads(images.MANIFEST.read_text())
        return images.render_gallery(
            "en-US", [], manifest["labels"]["en-US"],
            {row["key"]: row for row in manifest["apps"]}, images.PUBLIC_SITE,
        )

    def test_directive_consumption_has_separate_source_and_exact_canonical_hashes(self):
        source = self.source()
        canonical = images.canonical_gallery_source(source)
        self.assertNotEqual(source, canonical)
        self.assertEqual(source.replace("<!--email_off-->", "").replace("<!--/email_off-->", ""),
                         canonical)
        body = canonical.encode().replace(
            b"</body>", generation.EDGE_BEACON + b"\n</body>",
        )
        url = images.gallery_url("en-US", images.PUBLIC_SITE)

        def get(target, limit):
            if target.endswith("/robots.txt"):
                return images.Response(200, target, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n")
            return images.Response(200, target, {"content-type": "text/html"}, body)

        result = images.PublicVerifier(get).landing(url, source, indexable=False)
        self.assertEqual(images.digest(canonical.encode()), result["sha256"])
        self.assertEqual(images.digest(source.encode()), result["source_sha256"])
        self.assertEqual("cloudflare-email-off-v1", result["source_directive"])
        self.assertEqual(generation.EDGE_TRANSFORM, result["edge_transform"])

    def test_obfuscation_and_unrelated_html_edits_are_never_normalized(self):
        source = self.source()
        canonical = images.canonical_gallery_source(source)
        url = images.gallery_url("en-US", images.PUBLIC_SITE)
        for body in (
            canonical.replace("hourstag.app@gmail.com", "[email protected]"),
            canonical.replace("</main>", "<script>bad()</script></main>"),
            canonical.replace("noindex,follow", "index,follow"),
        ):
            def get(target, limit):
                if target.endswith("/robots.txt"):
                    return images.Response(200, target, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /\n")
                return images.Response(200, target, {"content-type": "text/html"}, body.encode())
            with self.subTest(body=body), self.assertRaises(ValueError):
                images.PublicVerifier(get).landing(url, source, indexable=False)

    def test_source_directive_must_be_unique_and_bound_to_the_visible_contact(self):
        source = self.source()
        for changed in (
            source.replace("hourstag.app@gmail.com", "other@example.com"),
            source.replace("<!--/email_off-->", ""),
            source + "<!--email_off-->unrelated<!--/email_off-->",
        ):
            with self.subTest(source=changed), self.assertRaises(ValueError):
                images.canonical_gallery_source(changed)


class ImageGenerationBindingTests(unittest.TestCase):
    def test_old_generation_or_different_verifier_source_cannot_be_reused(self):
        document = {"source_commit": "1" * 40, "engine_source_revision": "2" * 40}
        binding = {"pages_source_sha": "1" * 40, "source_sha": "2" * 40}
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as root:
            pages = Path(root)
            (pages / ".well-known").mkdir()
            (pages / ".well-known/deployment.json").write_text(json.dumps(document))
            with patch.object(images, "validate_binding", return_value=binding):
                with patch.object(images.subprocess, "check_output", return_value="3" * 40 + "\n"):
                    with self.assertRaisesRegex(ValueError, "older deployment"):
                        images.image_readback_generation(pages, images.MANIFEST)
                with patch.object(images.subprocess, "check_output", side_effect=["1" * 40 + "\n", b"other source"]):
                    with self.assertRaisesRegex(ValueError, "not the sealed generation"):
                        images.image_readback_generation(pages, images.MANIFEST)


if __name__ == "__main__":
    unittest.main()
