#!/usr/bin/env python3
"""Regression tests for locale-scoped install-decision feeds."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_install_decision_feeds
import app_install_decision_routes
from official_locales import OFFICIAL_LOCALES


class AppInstallDecisionFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        possible_pages = []
        configured = os.environ.get("GEO_PAGES")
        if configured:
            possible_pages.append(Path(configured))
        possible_pages.extend((GEO / "pages", GEO.parents[1]))
        cls.pages = next(
            (
                path
                for path in possible_pages
                if (path / app_install_decision_routes.DATA_RELATIVE).exists()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated install-decision feeds are absent")
        cls.payload = json.loads(
            (
                cls.pages / app_install_decision_routes.DATA_RELATIVE
            ).read_text(encoding="utf-8")
        )
        cls.records = cls.payload["records"]
        cls.by_locale = {
            locale: [
                record
                for record in cls.records
                if record["locale"] == locale
            ]
            for locale in OFFICIAL_LOCALES
        }

    def test_every_locale_has_three_valid_complete_feeds(self) -> None:
        atom_ns = "{http://www.w3.org/2005/Atom}"
        atom_link = f"{atom_ns}link"
        rss_atom_link = "{http://www.w3.org/2005/Atom}link"
        media_ns = f"{{{app_install_decision_feeds.gen_feed.MEDIA_NS}}}"
        for locale in OFFICIAL_LOCALES:
            records = self.by_locale[locale]
            records_by_page = {
                record["decision_page_url"]: record for record in records
            }
            expected_pages = {
                record["decision_page_url"] for record in records
            }
            expected_store_urls = {
                record["app_store_url"] for record in records
            }

            atom_path = (
                self.pages
                / app_install_decision_feeds.feed_relative(locale, "atom")
            )
            rss_path = (
                self.pages
                / app_install_decision_feeds.feed_relative(locale, "rss")
            )
            json_path = (
                self.pages
                / app_install_decision_feeds.feed_relative(
                    locale,
                    "json_feed",
                )
            )
            for path in (atom_path, rss_path, json_path):
                self.assertTrue(path.is_file(), path)

            atom = ET.parse(atom_path).getroot()
            atom_entries = atom.findall(f"{atom_ns}entry")
            self.assertEqual(len(records), len(atom_entries))
            self.assertEqual(
                expected_pages,
                {
                    entry.find(f"{atom_ns}id").text
                    for entry in atom_entries
                },
            )
            self.assertEqual(
                expected_store_urls,
                {
                    link.attrib["href"]
                    for entry in atom_entries
                    for link in entry.findall(atom_link)
                    if link.attrib.get("rel") == "related"
                },
            )
            for entry in atom_entries:
                page_url = entry.find(f"{atom_ns}id").text
                record = records_by_page[page_url]
                image_url = (
                    f"{app_install_decision_feeds.SITE}/social/img/"
                    f"{record['app_key']}-share.jpg"
                )
                image_path = (
                    self.pages
                    / "social"
                    / "img"
                    / f"{record['app_key']}-share.jpg"
                )
                enclosure = entry.find(
                    f"{atom_ns}link[@rel='enclosure']"
                )
                self.assertEqual(
                    {
                        "rel": "enclosure",
                        "type": "image/jpeg",
                        "href": image_url,
                        "length": str(image_path.stat().st_size),
                        "title": record["publisher_query"],
                    },
                    enclosure.attrib,
                )
                content_html = entry.find(f"{atom_ns}content").text
                self.assertIn(
                    f'<a href="{record["app_store_url"]}"><img ',
                    content_html,
                )
                self.assertIn(f'src="{image_url}"', content_html)
                self.assertIn('width="1200" height="675"', content_html)

            rss = ET.parse(rss_path).getroot()
            rss_items = rss.findall("./channel/item")
            self.assertEqual(len(records), len(rss_items))
            self.assertEqual(
                expected_pages,
                {item.find("link").text for item in rss_items},
            )
            self.assertEqual(
                expected_store_urls,
                {
                    link.attrib["href"]
                    for item in rss_items
                    for link in item.findall(rss_atom_link)
                    if link.attrib.get("rel") == "related"
                },
            )
            for item in rss_items:
                page_url = item.find("link").text
                record = records_by_page[page_url]
                image_url = (
                    f"{app_install_decision_feeds.SITE}/social/img/"
                    f"{record['app_key']}-share.jpg"
                )
                image_path = (
                    self.pages
                    / "social"
                    / "img"
                    / f"{record['app_key']}-share.jpg"
                )
                media = item.find(f"{media_ns}content")
                self.assertEqual(
                    {
                        "url": image_url,
                        "fileSize": str(image_path.stat().st_size),
                        "type": "image/jpeg",
                        "medium": "image",
                        "isDefault": "true",
                        "expression": "full",
                        "width": "1200",
                        "height": "675",
                    },
                    media.attrib,
                )
                self.assertEqual(
                    record["publisher_query"],
                    media.findtext(f"{media_ns}title"),
                )
                self.assertEqual(
                    {
                        "url": image_url,
                        "width": "1200",
                        "height": "675",
                    },
                    item.find(f"{media_ns}thumbnail").attrib,
                )
                self.assertIn(
                    f'href="{record["app_store_url"]}"><img ',
                    item.find("description").text,
                )

            json_feed = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "https://jsonfeed.org/version/1.1",
                json_feed["version"],
            )
            self.assertEqual(locale, json_feed["language"])
            self.assertEqual(len(records), len(json_feed["items"]))
            self.assertEqual(
                expected_pages,
                {item["url"] for item in json_feed["items"]},
            )
            self.assertEqual(
                expected_store_urls,
                {item["external_url"] for item in json_feed["items"]},
            )
            self.assertFalse(json_feed["_meta"]["is_ranking"])
            self.assertFalse(
                json_feed["_meta"]["measured_search_volume"]
            )
            records_by_id = {
                record["record_id"]: record for record in records
            }
            for item in json_feed["items"]:
                self.assertIn(item["external_url"], item["content_text"])
                self.assertNotIn("\n", item["content_text"])
                record = records_by_id[item["id"]]
                image_url = (
                    f"{app_install_decision_feeds.SITE}/social/img/"
                    f"{record['app_key']}-share.jpg"
                )
                image_path = (
                    self.pages
                    / "social"
                    / "img"
                    / f"{record['app_key']}-share.jpg"
                )
                self.assertEqual(image_url, item["image"])
                self.assertEqual(image_url, item["banner_image"])
                self.assertEqual(
                    [
                        {
                            "url": image_url,
                            "mime_type": "image/jpeg",
                            "title": record["publisher_query"],
                            "size_in_bytes": image_path.stat().st_size,
                        }
                    ],
                    item["attachments"],
                )
                self.assertIn(
                    f'<a href="{record["app_store_url"]}"><img ',
                    item["content_html"],
                )
                storefront_facts = record["storefront_facts"]
                if storefront_facts is not None:
                    formatted_price = str(
                        storefront_facts["formatted_price"]
                    )
                    self.assertIn(formatted_price, item["content_text"])
                    self.assertIn(formatted_price, item["content_html"])
                self.assertRegex(
                    item["_meta"]["content_digest"],
                    r"^[0-9a-f]{64}$",
                )

    def test_only_changed_item_advances_its_timestamp(self) -> None:
        locale = "en-US"
        records = self.by_locale[locale]
        path = (
            self.pages
            / app_install_decision_feeds.feed_relative(
                locale,
                "json_feed",
            )
        )
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing_dates = {
            item["id"]: item["date_modified"]
            for item in existing["items"]
        }
        changed_records = [dict(record) for record in records]
        changed_records[0]["decision_context"] += " Updated."
        changed_at = "2099-01-02T03:04:05Z"
        previews = app_install_decision_feeds._preview_images(
            self.pages,
            changed_records,
        )
        state = app_install_decision_feeds._item_state(
            path,
            changed_records,
            self.payload["dateModified"],
            changed_at,
            previews,
        )
        changed_id = changed_records[0]["record_id"]
        self.assertEqual(changed_at, state[changed_id]["date_modified"])
        for record in changed_records[1:]:
            record_id = record["record_id"]
            self.assertEqual(
                existing_dates[record_id],
                state[record_id]["date_modified"],
            )

        backwards_state = app_install_decision_feeds._item_state(
            path,
            changed_records,
            self.payload["dateModified"],
            "2000-01-01T00:00:00Z",
            previews,
        )
        self.assertGreater(
            datetime.fromisoformat(
                backwards_state[changed_id]["date_modified"].replace(
                    "Z",
                    "+00:00",
                )
            ),
            datetime.fromisoformat(
                existing_dates[changed_id].replace("Z", "+00:00")
            ),
        )

    def test_item_digest_tracks_visual_attachment_metadata(self) -> None:
        record = self.by_locale["en-US"][0]
        preview = app_install_decision_feeds._preview_images(
            self.pages,
            [record],
        )[record["record_id"]]
        changed_preview = dict(preview)
        changed_preview["length"] += 1
        self.assertNotEqual(
            app_install_decision_feeds._record_digest(record, preview),
            app_install_decision_feeds._record_digest(
                record,
                changed_preview,
            ),
        )

    def test_dataset_sitemap_and_pages_discover_every_feed(self) -> None:
        expected = set(app_install_decision_feeds.all_feed_urls())
        self.assertEqual(
            expected,
            {
                url
                for feeds in self.payload["syndication"][
                    "locale_feeds"
                ].values()
                for url in feeds.values()
            },
        )
        sitemap_entries = set(
            app_install_decision_routes.sitemap_entries(self.records)
        )
        self.assertTrue(expected <= sitemap_entries)

        for locale in OFFICIAL_LOCALES:
            sample = self.by_locale[locale][0]
            page = (
                self.pages
                / app_install_decision_routes.decision_page_relative(
                    sample["app_key"],
                    locale,
                )
            ).read_text(encoding="utf-8")
            for url in app_install_decision_feeds.feed_urls(locale).values():
                self.assertIn(url, page)


if __name__ == "__main__":
    unittest.main()
