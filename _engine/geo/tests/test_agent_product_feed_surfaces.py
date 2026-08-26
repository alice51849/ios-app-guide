#!/usr/bin/env python3
"""The three surfaces added on top of the JSONL feed.

Directories and answer engines read the feed, so an invented number here
travels further than one on a page nobody visits. These pin the two rules that
matter: no rating is ever published (the source rows carry none), and the
markup stays well-formed when an app name contains characters that would
otherwise break it.
"""
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

# The cloud runs `unittest discover` from the workspace root, so the engine
# directory is not on sys.path the way it is when running from inside geo/.
HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import agent_product_feed as F  # noqa: E402


def _row(**overrides):
    base = {
        "id": "demo-en-US",
        "item_group_id": "demo",
        "title": "Demo App",
        "description": "Does one thing.",
        "link": "https://example.invalid/answers/demo.html",
        "image_link": "https://example.invalid/demo.jpg",
        "price": "0 USD",
        "price_value": "0",
        "price_currency": "USD",
        "availability": "in_stock",
        "condition": "new",
        "brand": F.BRAND,
        "product_type": "Productivity",
        "content_language": "en-US",
        "app_store_id": "1",
        "app_store_url": "https://apps.apple.com/us/app/id1?pt=9&ct=x&mt=8",
        "one_time_purchase": True,
    }
    base.update(overrides)
    return base


class OneRowPerApp(unittest.TestCase):
    def test_jsonld_collapses_locales_into_one_entry_per_app(self):
        rows = [_row(), _row(id="demo-ja", content_language="ja")]
        doc = F.jsonld_payload(rows, "2026-08-26")
        self.assertEqual(doc["numberOfItems"], 1)
        self.assertEqual(
            doc["itemListElement"][0]["item"]["inLanguage"], ["en-US", "ja"]
        )

    def test_base_locale_wins_when_choosing_the_representative_row(self):
        rows = [_row(id="demo-ja", content_language="ja", title="デモ"), _row()]
        self.assertEqual(F._apps_in_base_locale(rows)[0]["title"], "Demo App")

    def test_xml_keeps_every_locale_row(self):
        rows = [_row(), _row(id="demo-ja", content_language="ja")]
        root = ET.fromstring(F.xml_text(rows, "2026-08-26"))
        self.assertEqual(len(root.findall("./channel/item")), 2)


class NoInventedRatings(unittest.TestCase):
    def test_jsonld_publishes_no_rating(self):
        doc = F.jsonld_payload([_row()], "2026-08-26")
        self.assertNotIn("aggregateRating", doc["itemListElement"][0]["item"])

    def test_page_publishes_no_rating(self):
        page = F.page_text([_row()], "2026-08-26")
        self.assertNotIn("aggregateRating", page)
        self.assertNotIn("ratingValue", page)


class WellFormed(unittest.TestCase):
    def test_xml_survives_ampersands_and_angle_brackets(self):
        xml = F.xml_text([_row(title="Ink & Paper <Pro>")], "2026-08-26")
        ET.fromstring(xml)
        self.assertIn("Ink &amp; Paper &lt;Pro&gt;", xml)

    def test_page_escapes_app_copy(self):
        page = F.page_text([_row(title="Ink & Paper")], "2026-08-26")
        self.assertIn("Ink &amp; Paper", page)
        self.assertNotIn("<td><a href=\"https://apps.apple.com/us/app/id1?pt=9&ct=",
                         page)

    def test_page_embeds_the_same_jsonld(self):
        rows = [_row()]
        page = F.page_text(rows, "2026-08-26")
        block = page.split('<script type="application/ld+json">')[1]
        block = block.split("</script>")[0]
        self.assertEqual(
            json.loads(block), F.jsonld_payload(rows, "2026-08-26")
        )

    def test_sitemap_lists_every_published_artifact(self):
        xml = F.sitemap_text("2026-08-26")
        root = ET.fromstring(xml)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = {node.text for node in root.findall(".//s:loc", ns)}
        self.assertEqual(
            locs,
            {
                F.page_url(), F.jsonld_url(), F.xml_url(),
                F.csv_url(), F.feed_url(), F.index_url(),
            },
        )


if __name__ == "__main__":
    unittest.main()


class RealBuildPath(unittest.TestCase):
    """The tests above run on a hand-made row, which is how two live defects got
    through: the feed shipped without image_link on any of 2,143 rows, and it
    shipped one app short of the catalog. A fabricated row has an image and one
    app, so neither could ever fail. These read what build_rows actually
    produces.
    """

    @classmethod
    def setUpClass(cls):
        pages = Path(F.PAGES)
        if not (pages / ".appstore_storefront_state.json").is_file():
            raise unittest.SkipTest("materialized Pages tree is unavailable")
        cls.rows, cls.modified = F.build_rows(pages)

    def test_every_row_carries_an_image(self):
        missing = [r["id"] for r in self.rows if not r.get("image_link")]
        self.assertEqual([], missing[:20], f"{len(missing)} rows without an image")

    def test_no_rating_reaches_any_published_surface(self):
        blob = "".join((
            F.feed_text(self.rows),
            F.csv_text(self.rows),
            F.xml_text(self.rows, self.modified),
            json.dumps(F.jsonld_payload(self.rows, self.modified)),
            F.page_text(self.rows, self.modified),
        )).lower()
        for banned in ("aggregaterating", "ratingvalue", "reviewcount", "starrating"):
            self.assertNotIn(banned, blob)

    def test_catalog_covers_every_app_the_registry_calls_live(self):
        import json as _json
        live = set(_json.loads(
            (Path(F.PAGES) / ".appstore_live_state.json").read_text(encoding="utf-8")
        )["live_ids"])
        in_feed = {str(r["app_store_id"]) for r in self.rows}
        self.assertEqual(set(), live - in_feed, "live apps missing from the feed")

    def test_csv_and_jsonl_agree_on_their_columns(self):
        import csv as _csv
        import io as _io
        csv_cols = set(next(_csv.reader(_io.StringIO(F.csv_text(self.rows)))))
        jsonl_keys = set()
        for row in self.rows:
            jsonl_keys |= set(row)
        self.assertEqual(set(), csv_cols - jsonl_keys,
                         "CSV declares columns the JSONL rows do not carry")

    def test_rss_items_are_readable_without_the_merchant_namespace(self):
        root = ET.fromstring(F.xml_text(self.rows[:50], self.modified))
        items = root.findall("./channel/item")
        self.assertTrue(items)
        for item in items:
            self.assertTrue((item.findtext("title") or "").strip())
            self.assertTrue((item.findtext("guid") or "").strip())

    def test_last_build_date_is_rfc822(self):
        import email.utils as _eu
        root = ET.fromstring(F.xml_text(self.rows[:5], self.modified))
        stamp = root.findtext("./channel/lastBuildDate")
        self.assertIsNotNone(_eu.parsedate_tz(stamp or ""), stamp)

    def test_application_category_is_a_schema_org_value(self):
        doc = F.jsonld_payload(self.rows, self.modified)
        for entry in doc["itemListElement"]:
            category = entry["item"].get("applicationCategory")
            self.assertTrue(
                category and category.endswith("Application"),
                f"{entry['item']['name']}: {category!r}",
            )

    def test_store_links_carry_attribution_within_apples_limits(self):
        import urllib.parse as _up
        for row in self.rows:
            query = _up.parse_qs(_up.urlparse(row["app_store_url"]).query)
            self.assertIn("pt", query, row["id"])
            self.assertLessEqual(len(query.get("ct", [""])[0]), 30, row["id"])
