"""Cloudflare's documented source opt-out must keep the real contact readable."""

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import result_image_index as images


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


if __name__ == "__main__":
    unittest.main()
