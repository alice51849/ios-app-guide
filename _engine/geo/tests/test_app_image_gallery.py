import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app_image_gallery as gallery  # noqa: E402
import gen_store_attribution as attribution  # noqa: E402

SITE = "https://example.test/guide"
APP_ID = "6824946559"
PAGE = """<!doctype html><html lang="en-US"><head></head><body><main>
<a class="cta" href="https://apps.apple.com/us/app/id{app_id}?action=write-review">Review</a>
<a class="cta" href="https://apps.apple.com/us/app/id{app_id}?pt=1&amp;ct=geo_pick&amp;mt=8">Get</a>
<!-- app-store-qr:start -->
<section>qr</section>
<!-- app-store-qr:end -->
<!-- app-hook-clip:start -->
<figure>clip</figure>
<!-- app-hook-clip:end -->
<h2>What is it?</h2>
</main></body></html>
"""


def config(**copy_overrides):
    copy = {
        "heading": "Wallpaper pairs", "intro": "Cut from one artwork.",
        "cover": "cover screen", "inner": "inner screen",
        "app_store": "Open on the App Store", "play": "Get it on Google Play",
    }
    copy.update(copy_overrides)
    return {
        "demo": {
            "app_id": APP_ID, "campaign": "duo_img", "asset_dir": "assets/g/demo",
            "locales": ["en-US"], "copy": {"en-US": copy},
            "pairs": [{
                "name": {"en-US": "Railway"},
                "cover": {"file": "a_outer.jpg", "width": 10, "height": 20},
                "inner": {"file": "a_inner.jpg", "width": 20, "height": 10},
            }],
        }
    }


def write_config(root: Path, apps: dict) -> Path:
    path = root / "gallery.json"
    path.write_text(json.dumps({"schema": gallery.SCHEMA, "apps": apps}), encoding="utf-8")
    return path


class AppImageGalleryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self.tmp.name)
        (self.pages / "en-US").mkdir()
        (self.pages / "assets/g/demo").mkdir(parents=True)
        for name in ("a_outer.jpg", "a_inner.jpg"):
            (self.pages / "assets/g/demo" / name).write_bytes(b"jpeg")
        self.page = self.pages / "en-US" / "demo.html"
        self.page.write_text(PAGE.format(app_id=APP_ID), encoding="utf-8")
        self.android = {"demo": {"play_url": "https://play.google.com/store/apps/details?id=com.example.demo"}}

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, apps=None, android=None):
        apps = gallery.load_config(write_config(self.pages, apps or config()))
        return gallery.build(self.pages, SITE, config=apps,
                             android=self.android if android is None else android)

    def test_block_after_clip_with_campaign_links_and_idempotent(self):
        stats = self.build()
        self.assertEqual({"pages": 1, "changed": 1, "removed": 0}, stats)
        text = self.page.read_text(encoding="utf-8")
        self.assertLess(text.index("app-hook-clip:end"), text.index(gallery.START))
        self.assertLess(text.index(gallery.END), text.index("<h2>What is it?"))
        self.assertIn(f"https://apps.apple.com/us/app/id{APP_ID}?pt=1&amp;ct=duo_img&amp;mt=8", text)
        self.assertIn("utm_source%3Dduo_img%26utm_campaign%3Ddemo", text)
        self.assertEqual(2, text.count('loading="lazy"'))
        self.assertIn('src="/guide/assets/g/demo/a_outer.jpg"', text)
        self.assertEqual(0, self.build()["changed"])
        self.assertEqual(1, self.page.read_text(encoding="utf-8").count(gallery.START))

    def test_no_play_link_when_not_on_play_and_no_block_when_android_unknown(self):
        self.build(android={})
        self.assertNotIn("play.google.com", self.page.read_text(encoding="utf-8"))
        apps = gallery.load_config(write_config(self.pages, config()))
        with mock.patch.object(gallery, "_load_android", return_value=None):  # snapshot unreadable
            stats = gallery.build(self.pages, SITE, config=apps)
        self.assertEqual(1, stats["removed"])
        self.assertNotIn(gallery.START, self.page.read_text(encoding="utf-8"))

    def test_page_without_download_cta_gets_no_block(self):
        self.page.write_text(PAGE.format(app_id="1234567890"), encoding="utf-8")
        self.assertEqual(0, self.build()["pages"])
        self.assertNotIn(gallery.START, self.page.read_text(encoding="utf-8"))

    def test_dropped_locale_loses_block(self):
        self.build()
        apps = config()
        apps["demo"]["locales"] = []
        self.assertEqual(1, self.build(apps)["removed"])
        self.assertNotIn(gallery.START, self.page.read_text(encoding="utf-8"))

    def test_forbidden_copy_and_missing_image_fail_closed(self):
        for word in ("Free download", "Pro pairs", "only $1", "kostenlos", "무료"):
            with self.subTest(word=word), self.assertRaises(gallery.GalleryError):
                gallery.load_config(write_config(self.pages, config(heading=word)))
        (self.pages / "assets/g/demo/a_inner.jpg").unlink()
        with self.assertRaises(gallery.GalleryError):
            self.build()

    def test_shipped_data_is_valid_and_limited_to_the_pilot(self):
        apps = gallery.load_config()
        self.assertEqual({"duowallpaperstudio"}, set(apps))
        app = apps["duowallpaperstudio"]
        self.assertEqual(APP_ID, app["app_id"])
        self.assertEqual(["en-US", "ko", "de-DE"], app["locales"])
        self.assertEqual(6, 2 * len(app["pairs"]))
        self.assertEqual(APP_ID, attribution.APP_BOUND_CAMPAIGNS[app["campaign"]])

    def test_image_sitemap_groups_gallery_images_under_one_page(self):
        import gen_image_sitemap

        apps = gallery.load_config(write_config(self.pages, config()))
        entries = [(page, image) for page, images in gallery.page_entries(self.pages, SITE, apps)
                   for image in images]
        root = ET.fromstring(gen_image_sitemap.render([("https://example.test/guide/s.html",
                                                        "https://example.test/guide/p.jpg")] + entries))
        ns = {"s": gen_image_sitemap.SITEMAP_NS, "i": gen_image_sitemap.IMAGE_NS}
        urls = root.findall("s:url", ns)
        self.assertEqual(2, len(urls))
        self.assertEqual(
            [f"{SITE}/assets/g/demo/a_outer.jpg", f"{SITE}/assets/g/demo/a_inner.jpg"],
            [node.text for node in urls[1].findall("i:image/i:loc", ns)],
        )

    def test_app_bound_campaign_only_for_its_app(self):
        self.assertTrue(attribution.app_bound_campaign("duo_img", APP_ID))
        self.assertFalse(attribution.app_bound_campaign("duo_img", "1234567890"))
        self.assertFalse(attribution.app_bound_campaign("geo_pick", APP_ID))
        self.assertFalse(attribution.app_bound_campaign(None, APP_ID))


if __name__ == "__main__":
    unittest.main()
