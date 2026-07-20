#!/usr/bin/env python3
"""Regression tests for localized publisher buyer-intent visuals."""

from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

from official_locales import OFFICIAL_LOCALES
import publisher_intent_catalog as catalog
import publisher_intent_visuals as visuals


class PublisherIntentVisualUnitTests(unittest.TestCase):
    def test_campaign_tokens_are_unique_and_app_store_safe(self) -> None:
        tokens = [
            visuals.visual_campaign_token(locale)
            for locale in OFFICIAL_LOCALES
        ]
        self.assertEqual(len(tokens), len(set(tokens)))
        for token in tokens:
            self.assertLessEqual(len(token), 30)
            self.assertRegex(token, r"^[a-z0-9_]+$")

    def test_svg_is_single_line_rtl_safe_and_truthful(self) -> None:
        record = {
            "locale": "ar-SA",
            "app_key": "sample",
            "app_name": "Sample App",
            "app_store_id": "1234567890",
            "publisher_query": "تطبيق خاص لإنجاز مهمة يومية",
            "decision_context": "اختره عندما تريد مسارًا مباشرًا وواضحًا.",
            "purchase_model": "paid_upfront",
            "app_store_url": (
                "https://apps.apple.com/sa/app/id1234567890"
                "?ct=iag_data_ar_sa"
            ),
        }
        svg = visuals.render_svg(record, "تنزيل مدفوع")
        root = ET.fromstring(svg)
        namespace = "{http://www.w3.org/2000/svg}"
        self.assertEqual(f"{namespace}svg", root.tag)
        self.assertEqual("rtl", root.attrib["direction"])
        self.assertEqual("ar-SA", root.attrib["{http://www.w3.org/XML/1998/namespace}lang"])
        self.assertEqual(
            record["publisher_query"],
            root.findtext(f"{namespace}title"),
        )
        self.assertIn(
            record["decision_context"],
            root.findtext(f"{namespace}desc"),
        )
        self.assertNotIn("<script", svg)
        self.assertIn(
            f"{visuals.SITE}/stories/img/sample-icon.jpg",
            svg,
        )
        query = next(
            element
            for element in root.findall(f"{namespace}text")
            if element.attrib.get("class") == "query"
        )
        app_name = next(
            element
            for element in root.findall(f"{namespace}text")
            if element.attrib.get("class") == "app-name"
        )
        self.assertEqual("start", query.attrib["text-anchor"])
        self.assertEqual("1100", query.attrib["x"])
        self.assertEqual("end", app_name.attrib["text-anchor"])
        self.assertEqual("ltr", app_name.attrib["direction"])
        store = visuals.visual_store_url(record)
        self.assertEqual(
            "https://apps.apple.com/sa/app/id1234567890",
            store,
        )

    def test_gallery_hreflang_covers_root_and_official_locales(self) -> None:
        alternates = visuals._alternates()
        self.assertEqual(
            len(OFFICIAL_LOCALES) + 2,
            alternates.count('rel="alternate" hreflang='),
        )
        self.assertIn('hreflang="en"', alternates)
        self.assertIn('hreflang="x-default"', alternates)
        for locale in OFFICIAL_LOCALES:
            self.assertIn(f'hreflang="{locale}"', alternates)

    def test_near_capacity_text_uses_horizontal_fit_transform(self) -> None:
        value = "ನರ್ಸುಗಳಿಗೆ ಕ್ಲೌಡ್ ಇಲ್ಲದ ಉತ್ತಮ ಆಫ್‌ಲೈನ್ ಡಾಕ್ಯುಮೆಂಟ್ ಸ್ಕ್ಯಾನರ್ ಆಪ್"
        size = visuals._fitted_size(
            value,
            maximum=54,
            minimum=24,
            width=1000,
        )
        node = visuals._text_node(
            value,
            x=100,
            y=392,
            size=size,
            width=1000,
            anchor="start",
            css_class="query",
        )
        self.assertIn('transform="translate(100 0) scale(', node)
        self.assertNotIn("textLength", node)

    def test_icon_gate_rejects_missing_or_empty_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            icon_dir = pages / "stories" / "img"
            icon_dir.mkdir(parents=True)
            (icon_dir / "empty-icon.jpg").touch()
            with self.assertRaisesRegex(
                ValueError,
                "empty-icon.jpg.*missing-icon.jpg",
            ):
                visuals.validate_icons(pages, ("missing", "empty"))
            (icon_dir / "empty-icon.jpg").write_bytes(b"jpeg")
            (icon_dir / "missing-icon.jpg").write_bytes(b"jpeg")
            visuals.validate_icons(pages, ("missing", "empty"))


class PublisherIntentVisualOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidates = []
        configured = os.environ.get("GEO_PAGES")
        if configured:
            candidates.append(Path(configured))
        candidates.extend((GEO / "pages", GEO.parents[1]))
        cls.pages = next(
            (
                path
                for path in candidates
                if (path / "data" / visuals.MANIFEST_NAME).is_file()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated visual manifest is not present")
        cls.manifest = json.loads(
            (
                cls.pages / "data" / visuals.MANIFEST_NAME
            ).read_text(encoding="utf-8")
        )
        cls.records = cls.manifest["records"]

    def _local_path(self, url: str) -> Path:
        parsed = urlparse(url)
        self.assertEqual("https", parsed.scheme)
        self.assertEqual("alice51849.github.io", parsed.netloc)
        prefix = "/ios-app-guide/"
        self.assertTrue(parsed.path.startswith(prefix), parsed.path)
        return self.pages / parsed.path.removeprefix(prefix)

    def test_manifest_covers_every_app_and_locale(self) -> None:
        self.assertEqual(catalog.EXPECTED_APP_COUNT, self.manifest["app_count"])
        self.assertEqual(50, self.manifest["locale_count"])
        self.assertEqual(visuals.EXPECTED_IMAGE_COUNT, self.manifest["image_count"])
        self.assertEqual(51, self.manifest["gallery_count"])
        self.assertTrue(self.manifest["publisher_authored"])
        self.assertFalse(self.manifest["measured_search_volume"])
        self.assertFalse(self.manifest["is_ranking"])
        self.assertEqual(
            {
                "default": "clean_direct",
                "campaign_requires": ["pt", "ct", "mt=8"],
            },
            self.manifest["app_store_link_policy"],
        )
        self.assertRegex(self.manifest["content_digest"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.manifest["generation_digest"], r"^[0-9a-f]{64}$")

        by_locale: dict[str, list[dict[str, object]]] = {}
        image_urls = set()
        app_pairs = set()
        for record in self.records:
            locale = str(record["locale"])
            key = str(record["app_key"])
            by_locale.setdefault(locale, []).append(record)
            app_pairs.add((locale, key))
            image_url = str(record["image_url"])
            image_urls.add(image_url)
            image_path = self._local_path(image_url)
            self.assertTrue(image_path.is_file(), image_path)
            content = image_path.read_text(encoding="utf-8")
            self.assertEqual(
                record["sha256"],
                hashlib.sha256(content.encode("utf-8")).hexdigest(),
            )
            root = ET.fromstring(content)
            namespace = "{http://www.w3.org/2000/svg}"
            self.assertEqual(f"{namespace}svg", root.tag)
            self.assertEqual(locale, root.attrib["{http://www.w3.org/XML/1998/namespace}lang"])
            expected_direction = (
                "rtl" if locale in catalog.RTL_LOCALES else "ltr"
            )
            self.assertEqual(expected_direction, root.attrib["direction"])
            self.assertTrue(root.findtext(f"{namespace}title"))
            self.assertTrue(root.findtext(f"{namespace}desc"))
            self.assertNotIn("<script", content)
            parsed_store = urlparse(str(record["app_store_url"]))
            self.assertEqual("apps.apple.com", parsed_store.netloc)
            self.assertIn(
                f"id{record['app_store_id']}",
                parsed_store.path,
            )
            self.assertEqual("", parsed_store.query)
            self.assertEqual(
                visuals.gallery_url(locale),
                record["gallery_url"],
            )

        self.assertEqual(set(OFFICIAL_LOCALES), set(by_locale))
        self.assertEqual(visuals.EXPECTED_IMAGE_COUNT, len(app_pairs))
        self.assertEqual(visuals.EXPECTED_IMAGE_COUNT, len(image_urls))
        for localized in by_locale.values():
            self.assertEqual(catalog.EXPECTED_APP_COUNT, len(localized))

    def test_galleries_are_complete_localized_and_direct(self) -> None:
        page_locales = ("en", *OFFICIAL_LOCALES)
        self.assertEqual(51, len(page_locales))
        for locale in page_locales:
            path = self.pages / visuals.gallery_relative_path(locale)
            source = path.read_text(encoding="utf-8")
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT,
                source.count('<article class="visual-card">'),
            )
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT,
                source.count("<img "),
            )
            self.assertEqual(
                len(OFFICIAL_LOCALES) + 2,
                source.count('<link rel="alternate" hreflang='),
            )
            self.assertIn("white-space:nowrap", source)
            store_urls = re.findall(
                r'href="(https://apps\.apple\.com/'
                r'(?:[a-z]{2}/)?app/id[0-9]+)"',
                source,
            )
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT * 2,
                len(store_urls),
            )
            self.assertTrue(
                all(not urlparse(html.unescape(url)).query for url in store_urls)
            )
            schema_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                source,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(schema_match)
            schema = json.loads(html.unescape(schema_match.group(1)))
            self.assertEqual("ImageGallery", schema["@type"])
            self.assertEqual(locale, schema["inLanguage"])
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT,
                schema["mainEntity"]["numberOfItems"],
            )
            for item in schema["mainEntity"]["itemListElement"]:
                application = item["item"]["about"]
                self.assertNotIn("offers", application)
                purchase = application["additionalProperty"]
                self.assertEqual("PropertyValue", purchase["@type"])
                self.assertTrue(purchase["name"])
                self.assertTrue(purchase["value"])
            if locale in catalog.RTL_LOCALES:
                self.assertIn(f'<html lang="{locale}" dir="rtl">', source)

    def test_image_sitemap_and_discovery_cover_every_visual(self) -> None:
        sitemap = ET.parse(self.pages / visuals.SITEMAP_NAME).getroot()
        sitemap_ns = f"{{{visuals.SITEMAP_NS}}}"
        image_ns = f"{{{visuals.IMAGE_NS}}}"
        urls = sitemap.findall(f"{sitemap_ns}url")
        self.assertEqual(51, len(urls))
        self.assertTrue(
            all(
                url.findtext(f"{sitemap_ns}lastmod")
                == self.manifest["dateModified"]
                for url in urls
            )
        )
        image_locations = [
            image.findtext(f"{image_ns}loc")
            for url in urls
            for image in url.findall(f"{image_ns}image")
        ]
        self.assertEqual(
            visuals.EXPECTED_IMAGE_COUNT + catalog.EXPECTED_APP_COUNT,
            len(image_locations),
        )
        self.assertEqual(
            visuals.EXPECTED_IMAGE_COUNT,
            len(set(image_locations)),
        )
        manifest_urls = {str(record["image_url"]) for record in self.records}
        self.assertEqual(manifest_urls, set(image_locations))

        robots = (self.pages / "robots.txt").read_text(encoding="utf-8")
        sitemap_index = (
            self.pages / "sitemap_index.xml"
        ).read_text(encoding="utf-8")
        llms = (self.pages / "llms.txt").read_text(encoding="utf-8")
        llms_full = (self.pages / "llms-full.txt").read_text(encoding="utf-8")
        for source in (robots, sitemap_index, llms, llms_full):
            self.assertIn(visuals.SITEMAP_NAME, source)
        for locale in OFFICIAL_LOCALES:
            self.assertIn(f"{visuals.SITE}/{locale}/visuals/", llms)
        self.assertIn(f"{visuals.SITE}/visuals/", llms)
        self.assertIn(
            f"{visuals.SITE}/data/{visuals.MANIFEST_NAME}",
            llms,
        )


if __name__ == "__main__":
    unittest.main()
