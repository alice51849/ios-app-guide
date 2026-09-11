import json
import html
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from external_app_identity import (
    INDIC_LOCALES, SOURCE_HEADLINES, TRIP_PLANET_ID, TRIP_PLANET_NAME,
    external_identity, registry_name,
)
from regen_indic_identity import STORE_URL, path_locale, repair_document, repair_text
from app_store_storefronts import LOCALE_STOREFRONTS


class _PageIdentity(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.locale = None
        self.canonicals = []
        self.hreflangs = []
        self.ctas = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "html":
            self.locale = attributes.get("lang")
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonicals.append(attributes.get("href"))
        if tag == "link" and "hreflang" in attributes:
            self.hreflangs.append(attributes["hreflang"])
        if tag == "a" and str(attributes.get("href", "")).startswith("https://apps.apple.com/"):
            self.ctas.append(attributes["href"])


class IndicIdentityTests(unittest.TestCase):
    def test_countryless_identity_generator_is_aligned_before_strict_validation(self):
        import gen_store_attribution as attribution

        for prefix in ("", "in/"):
            result = attribution.final_store_url(
                f"https://apps.apple.com/{prefix}app/id{TRIP_PLANET_ID}",
                "geo_pick", "118326163", locale="bn-BD",
                availability={"in": frozenset({TRIP_PLANET_ID})},
                app_id=TRIP_PLANET_ID,
            )
            self.assertEqual(
                urlsplit(result).path, f"/bd/app/id{TRIP_PLANET_ID}"
            )
        with self.assertRaises(ValueError):
            attribution.final_store_url(
                f"https://apps.apple.com/xx/app/id{TRIP_PLANET_ID}",
                "geo_pick", "118326163", locale="bn-BD",
            )
        with self.assertRaises(ValueError):
            attribution.final_store_url(
                f"https://apps.apple.com/app/id{TRIP_PLANET_ID}",
                "geo_pick", "118326163", locale="bn-BD",
                app_id="1234567890",
            )

    def test_every_bangladesh_qr_encodes_its_download_cta(self):
        import gen_store_attribution as attribution
        import gen_app_store_qr_ctas as qr

        pages = Path(os.environ.get("GEO_PAGES", Path(__file__).resolve().parents[1] / "pages"))
        checked = 0
        for path in (pages / "bn-BD").rglob("*.html"):
            source = path.read_text()
            link = attribution.QR_CARD_LINK_RE.search(source)
            if link is None:
                continue
            with self.subTest(page=str(path)):
                self.assertIsNone(attribution.qr_card_desync(source))
                image = attribution.QR_CARD_IMAGE_RE.search(source)
                href = html.unescape(link["href"])
                self.assertIn("apps.apple.com/bd/app/", href)
                asset = pages / qr.qr_asset_relative(image["app"], href)
                svg = asset.read_text()
                self.assertEqual(ET.fromstring(svg).find("{http://www.w3.org/2000/svg}desc").text, href)
                self.assertEqual(svg, qr.qr_svg(image["app"], href))
                checked += 1
        self.assertGreaterEqual(checked, 146)

    def test_api_feed_identity_changes_advance_only_the_changed_timestamp(self):
        import portfolio_app_catalog_api as api

        app = {
            "app_store_id": TRIP_PLANET_ID,
            "name": TRIP_PLANET_NAME,
            "guide_url": f"https://open.cait518.cc/ios-app-guide/bn-BD/tripplanet.html",
            "app_store_url": f"https://apps.apple.com/bd/app/id{TRIP_PLANET_ID}",
            "summary": "ভ্রমণে শিশুদের সঙ্গে মজার ছোট কাজ।",
            "search_terms": ["ভ্রমণ"],
        }
        first = api.feed_payload("bn-BD", "Apps", [app], "2026-09-10", "a" * 64, timestamp="2026-09-10T00:00:00Z")
        previous = first["items"]
        previous[0]["title"] = "Lumi Trip Planet"
        second = api.feed_payload("bn-BD", "Apps", [app], "2026-09-11", "b" * 64, previous_items=previous, timestamp="2026-09-11T00:00:00Z")
        self.assertEqual(second["items"][0]["date_modified"], "2026-09-11T00:00:00Z")
        self.assertEqual(second["items"][0]["id"], f"https://apps.apple.com/bd/app/id{TRIP_PLANET_ID}")
        third = api.feed_payload("bn-BD", "Apps", [app], "2026-09-11", "b" * 64, previous_items=second["items"], timestamp="2026-09-11T01:00:00Z")
        self.assertEqual(second["items"], third["items"])

    def test_47_by_10_geo_owned_feed_cta_storefront_app_id_and_brand(self):
        pages = Path(os.environ.get("GEO_PAGES", Path(__file__).resolve().parents[1] / "pages"))
        finder = json.loads((pages / "data/verified-ios-app-finder-catalog.json").read_text())
        apps = {row["key"]: str(row["app_store_id"]) for row in finder["apps"]}
        self.assertEqual(len(apps), 47)
        rows = json.loads((pages / "data/app-install-decision-routes.json").read_text())["records"]
        owned = {(row["app_key"], row["locale"]): row for row in rows}
        feeds = {
            locale: [
                (pages / f"data/app-install-decision-routes/feeds/{locale}.{suffix}").read_text()
                for suffix in ("atom.xml", "rss.xml", "feed.json")
            ]
            for locale in INDIC_LOCALES
        }
        api_feeds = {
            locale: json.loads((pages / f"api/v1/ios-app-catalog/feeds/{locale}.json").read_text())
            for locale in INDIC_LOCALES
        }
        checked = 0
        for key, app_id in apps.items():
            for locale in INDIC_LOCALES:
                with self.subTest(app=key, locale=locale):
                    expected_store = f"https://apps.apple.com/{LOCALE_STOREFRONTS[locale]}/app/id{app_id}"
                    record = owned[(key, locale)]
                    self.assertEqual(record["app_store_id"], app_id)
                    self.assertTrue(record["app_store_url"].startswith(expected_store + "?"))
                    if locale == "bn-BD":
                        self.assertEqual(record["canonical_app_store_url"], expected_store)
                    api_item = next(
                        item for item in api_feeds[locale]["items"]
                        if item["id"].endswith(f"/id{app_id}")
                    )
                    self.assertEqual(urlsplit(api_item["external_url"]).path, urlsplit(expected_store).path)
                    if locale == "bn-BD":
                        self.assertEqual(api_item["id"], expected_store)
                        self.assertGreaterEqual(api_item["date_modified"][:10], "2026-09-11")
                    if key == "tripplanet":
                        self.assertEqual(api_item["title"], TRIP_PLANET_NAME)
                        self.assertGreaterEqual(api_item["date_modified"][:10], "2026-09-11")
                    for relative in (
                        f"{locale}/{key}.html",
                        f"apps/{key}/decision/l/{locale}/index.html",
                    ):
                        source = (pages / relative).read_text()
                        parsed = _PageIdentity(source)
                        self.assertEqual(parsed.locale, locale)
                        self.assertEqual(len(parsed.canonicals), 1)
                        self.assertTrue(urlsplit(parsed.canonicals[0]).path.endswith("/" + relative))
                        self.assertFalse({"gu", "kn", "ml"} & set(parsed.hreflangs))
                        own_ctas = [
                            url for url in parsed.ctas
                            if re.search(rf"/id{app_id}(?:[/?#]|$)", url)
                        ]
                        self.assertTrue(own_ctas)
                        self.assertIn(urlsplit(expected_store).path, [urlsplit(url).path for url in own_ctas])
                        for url in own_ctas:
                            allowed = {urlsplit(expected_store).path}
                            # Only bn-BD has the strict no-countryless override;
                            # retain other locales' pre-existing canonical references.
                            if locale != "bn-BD":
                                allowed.add(f"/app/id{app_id}")
                            self.assertIn(urlsplit(url).path, allowed)
                        if locale == "bn-BD":
                            for url in STORE_URL.finditer(source):
                                if url["id"] in apps.values():
                                    self.assertIn("apps.apple.com/bd/app/", url.group())
                        if key == "tripplanet":
                            self.assertIn(TRIP_PLANET_NAME, source)
                            self.assertNotIn("Lumi Trip Planet", source)
                            self.assertEqual(record["app_name"], TRIP_PLANET_NAME)
                    for feed in feeds[locale]:
                        self.assertIn(expected_store, feed)
                        if locale == "bn-BD":
                            self.assertNotRegex(feed, r"apps\.apple\.com/(?:in/)?app/id")
                    checked += 1
        self.assertEqual(checked, 470)

    def test_trip_planet_identity_is_exact_in_all_ten_locales(self):
        for locale in INDIC_LOCALES:
            source = {
                "name": "Lumi Trip Planet: World Travel",
                "subtitle": "Native subtitle",
                "description": "Lumi Trip Planet · ₹299 · ৳৫৯৯ · native copy",
            }
            with self.subTest(locale=locale):
                result = external_identity("tripplanet", locale, source)
                self.assertEqual(result["name"], TRIP_PLANET_NAME)
                self.assertEqual(result["subtitle"], source["subtitle"])
                self.assertEqual(
                    result["description"],
                    source["description"].replace("Lumi Trip Planet", TRIP_PLANET_NAME),
                )
                self.assertEqual(external_identity("tripplanet", locale, result), result)
                self.assertEqual(source["name"], "Lumi Trip Planet: World Travel")

    def test_complete_source_headlines_do_not_rewrite_value_copy(self):
        for key, locales in SOURCE_HEADLINES.items():
            for locale, fields in locales.items():
                with self.subTest(key=key, locale=locale):
                    source = {
                        "name": "Original", "subtitle": "Original",
                        "description": "₹499 · reviewed body",
                        "promotionalText": "৳৫৯৯ · reviewed value",
                    }
                    result = external_identity(key, locale, source)
                    for field, expected in fields.items():
                        self.assertEqual(result[field], expected)
                    self.assertEqual(result["description"], source["description"])
                    self.assertEqual(result["promotionalText"], source["promotionalText"])

    def test_registry_brand_rejects_wrong_app_id(self):
        import gen_webstories
        import aso_evidence_contract

        self.assertEqual(gen_webstories.APPS["tripplanet"]["name"], TRIP_PLANET_NAME)
        self.assertEqual(str(gen_webstories.APPSTORE["tripplanet"]), TRIP_PLANET_ID)
        self.assertEqual(aso_evidence_contract.live_roster()["tripplanet"]["name"], TRIP_PLANET_NAME)
        self.assertEqual(registry_name("tripplanet", TRIP_PLANET_ID, "old"), TRIP_PLANET_NAME)
        with self.assertRaises(ValueError):
            registry_name("tripplanet", "1234567890", "old")

    def test_url_refresh_preserves_query_and_currency(self):
        source = (
            "মূল্য ₹299 বা ৳৫৯৯। "
            f"https://apps.apple.com/in/app/kids/id{TRIP_PLANET_ID}"
            "?pt=118326163&ct=geo_pick&mt=8"
        )
        result = repair_text(source, "bn-BD", {TRIP_PLANET_ID})
        self.assertEqual(
            result, source.replace("/in/app/kids/", "/bd/app/")
        )
        self.assertEqual(repair_text(result, "bn-BD", {TRIP_PLANET_ID}), result)

    def test_headline_repair_is_idempotent_and_does_not_extend_complete_words(self):
        for key, locale, field in (
            ("lumimission", "bn-BD", "subtitle"),
            ("lumimission", "or-IN", "name"),
            ("gmoney", "or-IN", "subtitle"),
        ):
            text = SOURCE_HEADLINES[key][locale][field]
            self.assertEqual(repair_text(text, locale, set()), text)

    def test_proof_is_not_relabelled_as_bangladesh_pricing(self):
        facts = {
            "price": "299", "currency": "INR", "formatted_price": "₹299",
            "storefront_url": f"https://apps.apple.com/in/app/id{TRIP_PLANET_ID}",
        }
        record = {
            "locale": "bn-BD", "storefront_facts": facts,
            "canonical_app_store_url": f"https://apps.apple.com/app/id{TRIP_PLANET_ID}",
        }
        result = repair_document(record, {TRIP_PLANET_ID})
        self.assertEqual(result["storefront_facts"], facts)
        self.assertIn("/bd/", result["canonical_app_store_url"])

    def test_product_locale_detection_never_introduces_bare_codes(self):
        for locale in INDIC_LOCALES:
            self.assertEqual(path_locale(f"apps/tripplanet/decision/l/{locale}/index.html"), locale)
            self.assertEqual(path_locale(f"feeds/{locale}.rss.xml"), locale)
        for locale in ("gu", "kn", "ml"):
            self.assertIsNone(path_locale(f"{locale}/tripplanet.html"))

    def test_other_locale_copy_remains_byte_identical(self):
        source = "Lumi Trip Planet ₹299 https://apps.apple.com/app/id6787193643"
        self.assertEqual(repair_text(source, "en-US", {TRIP_PLANET_ID}), source)
