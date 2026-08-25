#!/usr/bin/env python3
"""The three surfaces added on top of the JSONL feed.

Directories and answer engines read the feed, so an invented number here
travels further than one on a page nobody visits. These pin the two rules that
matter: no rating is ever published (the source rows carry none), and the
markup stays well-formed when an app name contains characters that would
otherwise break it.
"""
import json
import unittest
import xml.etree.ElementTree as ET

import agent_product_feed as F


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
