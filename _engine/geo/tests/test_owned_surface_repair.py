"""Edition identity and app-specific storefront regressions; no network."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import app_store_storefronts as stores
import market_availability as market
import market_surface_policy as policy
import portfolio_app_catalog_api as catalog
import gen_store_attribution as attribution
import gen_social_previews as social
import publisher_intent_visuals as visuals
import app_install_decision_feeds as install_feeds
import queries
from official_locales import OFFICIAL_LOCALES

TARGET_IDS = {"6778748533", "6778269699", "6776958488", "6787193643"}
CONTROL_ID = "6791658210"


class AppMarketContract(unittest.TestCase):
    def test_cn_exceptions_are_exactly_the_four_observed_apps(self):
        self.assertEqual(TARGET_IDS, market.UNAVAILABLE_APP_MARKETS["zh-Hans"])
        self.assertFalse(market.is_unavailable("zh-Hans"))
        self.assertFalse(market.is_unavailable("zh-Hans", CONTROL_ID))
        self.assertEqual(50, len(OFFICIAL_LOCALES))
        self.assertEqual("cn", stores.LOCALE_STOREFRONTS["zh-Hans"])

    def test_all_four_cn_cells_keep_content_without_a_fallback(self):
        for app_id in TARGET_IDS:
            with self.subTest(app_id=app_id):
                fields = market.record_fields("zh-Hans", app_id)
                state = fields["market_availability"]
                self.assertEqual("N/A", state["value"])
                self.assertTrue(state["content_retained"])
                self.assertFalse(state["publishable"])
                self.assertFalse(state["facts_allowed"])
                self.assertEqual(0, state["outbox_count"])
                self.assertEqual(app_id, state["evidence"]["app_store_id"])
                self.assertEqual(0, state["evidence"]["lookup_app_results"])
                self.assertEqual(1, state["evidence"]["lookup_control_results"])
                direct = f"https://apps.apple.com/app/id{app_id}"
                self.assertIsNone(stores.verified_app_store_url(direct, "zh-Hans", {}))
                self.assertIsNone(stores.canonical_app_store_url_for(app_id, "zh-Hans"))
                for country in ("cn", "us", "in", None):
                    self.assertIsNone(
                        market.canonical_app_store_url_for(app_id, "zh-Hans", country)
                    )
                record = {
                    "locale": "zh-Hans", "app_store_id": app_id,
                    "app_store_url": None, **fields,
                }
                self.assertFalse(market.validate_record(record, url_fields=("app_store_url",)))
                for prefix in ("", "cn/", "us/"):
                    url = f"https://apps.apple.com/{prefix}app/id{app_id}"
                    with self.assertRaises(market.MarketUnavailable):
                        stores.validated_app_store_url(
                            url, expected_app_id=app_id, expected_locale="zh-Hans"
                        )

    def test_available_cn_control_uses_cn_and_other_locales_are_unchanged(self):
        availability = {"cn": frozenset({CONTROL_ID}), "us": frozenset(TARGET_IDS)}
        self.assertEqual(
            f"https://apps.apple.com/cn/app/id{CONTROL_ID}",
            stores.verified_app_store_url(
                f"https://apps.apple.com/app/id{CONTROL_ID}", "zh-Hans", availability
            ),
        )
        for app_id in TARGET_IDS:
            self.assertEqual(
                f"https://apps.apple.com/us/app/id{app_id}",
                stores.verified_app_store_url(
                    f"https://apps.apple.com/app/id{app_id}", "en-US", availability
                ),
            )
            self.assertIsNone(stores.verified_app_store_url(
                f"https://apps.apple.com/app/id{app_id}", "bn-BD", availability
            ))

    def test_stamper_localizes_verified_countryless_ctas_without_changing_app(self):
        for locale, country, app_id in [
            ("en-US", "us", "6776958488"),
            ("en-US", "us", "6778269699"),
            ("zh-Hans", "cn", CONTROL_ID),
        ]:
            source = f"https://apps.apple.com/app/id{app_id}?pt=118326163&ct=geo_ask&mt=8"
            self.assertEqual(
                source.replace("/app/", f"/{country}/app/"),
                attribution.final_store_url(
                    source, "geo_ask", "118326163", locale=locale,
                    availability={country: frozenset({app_id})}, app_id=app_id,
                ),
            )

    def test_na_requires_exact_evidence_not_an_unexplained_null(self):
        for app_id in TARGET_IDS:
            with self.assertRaises(ValueError):
                market.validate_record({
                    "locale": "zh-Hans", "app_store_id": app_id, "app_store_url": None
                }, url_fields=("app_store_url",))


class ExistingSurfaceContract(unittest.TestCase):
    def test_na_feed_xml_does_not_depend_on_global_namespace_registration(self):
        for format_name, source in (
            ("atom", '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'),
            ("rss", "<rss><channel></channel></rss>"),
        ):
            with self.subTest(format=format_name), patch.dict(ET._namespace_map):
                ET.register_namespace("first", "http://www.w3.org/2005/Atom")
                first = install_feeds._market_xml(source, "bn-BD", format_name)
                ET.register_namespace("second", "http://www.w3.org/2005/Atom")
                second = install_feeds._market_xml(source, "bn-BD", format_name)
                self.assertEqual(first, second)
                root = ET.fromstring(second)
                entries = root.findall(".//{" + install_feeds.SITE + "/market-availability}availability")
                self.assertEqual(1, len(entries))
                self.assertEqual("N/A", json.loads(entries[0].text)["value"])

    def test_gallery_date_changes_only_when_that_gallery_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.html"

            def render(locale, records, ui, modified, site):
                return f'<meta name="content-modified" content="{modified}">{records[0]}'

            previous = render("en-US", ["unchanged"], {}, "2026-09-11", "")
            path.write_text(previous)
            with patch.object(visuals, "render_gallery", side_effect=render), patch.object(
                visuals, "_final_gallery_content", side_effect=lambda path, source: source
            ):
                self.assertEqual("2026-09-11", visuals._gallery_modified(
                    path, "en-US", ["unchanged"], {}, "2026-09-12", ""
                ))
                self.assertEqual("2026-09-12", visuals._gallery_modified(
                    path, "en-US", ["changed"], {}, "2026-09-12", ""
                ))

    def test_cn_oembed_retains_preview_without_an_install_link(self):
        for app_id in TARGET_IDS:
            with self.subTest(app_id=app_id):
                document = social.oembed_document(
                    "数学学习", "https://open.cait518.cc/ios-app-guide/image.png",
                    "https://open.cait518.cc/ios-app-guide/zh-Hans/lumimathpro.html",
                    None, "zh-Hans", app_store_id=app_id,
                    buyer_intent_url="https://open.cait518.cc/ios-app-guide/preview.png",
                )
                self.assertEqual("rich", document["type"])
                self.assertIsNone(document["_lumi_app_store_url"])
                self.assertNotIn("apps.apple.com", document["html"])
                self.assertIn("preview.png", document["html"])
                self.assertFalse(document["market_availability"]["publishable"])

    def page(self, app_id):
        software = {
            "@type": "SoftwareApplication", "name": "数学学习",
            "url": f"https://apps.apple.com/app/id{app_id}",
            "offers": {"price": "4.99"},
        }
        return (
            '<html lang="zh-Hans"><head>'
            '<link rel="canonical" href="https://open.cait518.cc/ios-app-guide/zh-Hans/lumimathpro.html">'
            '<script type="application/ld+json">' + json.dumps(software) +
            '</script></head><body><main><p>保留完整的数学课程介绍。</p>'
            f'<a href="https://apps.apple.com/app/id{app_id}">下载</a>'
            '</main></body></html>'
        )

    def test_unavailable_single_app_html_is_idempotent_and_keeps_identity(self):
        for app_id in TARGET_IDS:
            with self.subTest(app_id=app_id):
                fixed = policy.enforce_html(self.page(app_id), "zh-Hans")
                self.assertIn("保留完整的数学课程介绍。", fixed)
                self.assertNotIn("apps.apple.com", fixed)
                self.assertNotIn('"offers"', fixed)
                self.assertIn(market.REASON_APP_NOT_SOLD, fixed)
                self.assertEqual({app_id}, policy.application_ids(fixed))
                self.assertEqual(fixed, policy.enforce_html(fixed, "zh-Hans"))

    def test_available_cn_page_is_not_quarantined(self):
        source = self.page(CONTROL_ID)
        self.assertEqual(source, policy.enforce_html(source, "zh-Hans"))

    def test_catalog_feed_retains_na_guid_content_and_date(self):
        app_id = "6776958488"
        app = {
            "app_store_id": app_id, "name": "数学学习", "summary": "完整的数学课程介绍。",
            "guide_url": "https://open.cait518.cc/ios-app-guide/zh-Hans/lumimathpro.html",
            "search_terms": ["数学"], "app_store_url": None,
            **market.record_fields("zh-Hans", app_id),
        }
        first = catalog.feed_payload(
            "zh-Hans", "目录", [app], "2026-09-12", "a" * 64,
            timestamp="2026-09-12T12:00:00Z",
        )
        second = catalog.feed_payload(
            "zh-Hans", "目录", [app], "2026-09-12", "a" * 64,
            previous_items=first["items"], timestamp="2026-09-13T12:00:00Z",
        )
        self.assertEqual(first, second)
        self.assertEqual(1, len(first["items"]))
        item = first["items"][0]
        self.assertEqual(f"https://apps.apple.com/app/id{app_id}", item["id"])
        self.assertNotIn("external_url", item)
        self.assertIn(app["summary"], item["content_text"])
        self.assertEqual(app["market_availability"], item["_market_availability"])

    def test_math_complete_is_not_skipped_as_free_inheritance(self):
        question = "best complete math learning app for preschool and early grades"
        self.assertFalse(queries.is_inherited_query(
            "lumimathpro", question, {"lumimathpro", "lumimath"}
        ))


if __name__ == "__main__":
    unittest.main()
