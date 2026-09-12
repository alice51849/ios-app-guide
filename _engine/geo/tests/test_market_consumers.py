import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import alternatives_i18n as alternatives
import gen_market_availability as boundary
import market_availability as market
import market_surface_policy as policy
from official_locales import OFFICIAL_LOCALES
from market_contract_assertions import assert_blocked_page, assert_blocked_record


class MarketConsumerTests(unittest.TestCase):
    def setUp(self):
        self.cell = {
            "locale": "bn-BD", "app_store_id": "6779977651",
            "canonical_app_store_url": None, "app_store_url": None,
            **market.record_fields("bn-BD"),
        }

    def test_null_requires_exact_state_reason_evidence_and_false_publishability(self):
        assert_blocked_record(self, self.cell)
        self.assertFalse(market.validate_record(self.cell))
        for field in self.cell["market_availability"]:
            with self.subTest(missing=field):
                bad = copy.deepcopy(self.cell)
                del bad["market_availability"][field]
                with self.assertRaises(ValueError):
                    market.validate_record(bad)
        for field, value in (
            ("state", "MARKET_AVAILABLE"), ("reason", "MARKET_APP_NOT_SOLD"),
            ("publishable", True), ("publishable", 0), ("outbox_count", 1),
            ("facts_allowed", True), ("content_retained", False),
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.cell)
                bad["market_availability"][field] = value
                with self.assertRaises(ValueError):
                    market.validate_record(bad)

    def test_missing_or_forged_evidence_fails_closed(self):
        for field in self.cell["market_availability"]["evidence"]:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.cell)
                del bad["market_availability"]["evidence"][field]
                with self.assertRaises(ValueError):
                    market.validate_record(bad)

    def test_all_fallbacks_and_missing_null_fields_are_rejected(self):
        for field in ("canonical_app_store_url", "app_store_url"):
            for destination in ("us/", "in/", "bd/", "", "jp/"):
                with self.subTest(field=field, destination=destination):
                    bad = {**self.cell, field: f"https://apps.apple.com/{destination}app/id6779977651"}
                    with self.assertRaises(ValueError):
                        market.validate_record(bad)
            for value in ("", "None", "null", False):
                with self.assertRaises(ValueError):
                    market.validate_record({**self.cell, field: value})
            bad = dict(self.cell)
            del bad[field]
            with self.assertRaises(ValueError):
                market.validate_record(bad)

    def test_all_other_49_locales_still_require_both_real_urls(self):
        available = [locale for locale in OFFICIAL_LOCALES if locale != "bn-BD"]
        self.assertEqual(len(available), 49)
        for locale in available:
            record = {
                "locale": locale, "app_store_url": "https://apps.apple.com/app/id6779977651",
                "canonical_app_store_url": "https://apps.apple.com/app/id6779977651",
            }
            self.assertTrue(market.validate_record(record))
            self.assertEqual(market.record_fields(locale), {})
            for field in ("app_store_url", "canonical_app_store_url"):
                with self.subTest(locale=locale, field=field), self.assertRaises(ValueError):
                    market.validate_record({**record, field: None})
            with self.assertRaises(ValueError):
                market.validate_record({**record, **market.record_fields("bn-BD")})

    def test_schema_accepts_only_evidence_backed_null(self):
        import jsonschema
        schema = market.add_schema_contract({
            "type": "object",
            "properties": {
                "locale": {"enum": list(OFFICIAL_LOCALES)},
                "canonical_app_store_url": {"type": "string", "format": "uri"},
                "app_store_url": {"type": "string", "format": "uri"},
            },
            "required": ["locale", "canonical_app_store_url", "app_store_url"],
        })
        jsonschema.validate(self.cell, schema)
        for bad in ({**self.cell, "locale": "hi"}, {**self.cell, "market_availability": {}}, {**self.cell, "app_store_url": ""}):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(bad, schema)

    def test_html_preserves_content_owner_and_blocks_every_url_form(self):
        source = (
            '<html lang="bn-BD"><head><script type="application/ld+json">'
            '{"@type":"SoftwareApplication","name":"ScanTo","@id":"https://apps.apple.com/app/id6779977651",'
            '"installUrl":"https://apps.apple.com/us/app/id6779977651","offers":{"price":"5"}}'
            '</script></head><body><h1>ডকুমেন্ট স্ক্যান</h1><p>মূল তথ্য</p>'
            '<a href="https://apps.apple.com/bd/app/id6779977651">ScanTo</a>'
            '<a href="https://apps.apple.com/in/app/id6779977651">ScanTo</a>'
            '<a href="https://apps.apple.com/app/id6779977651">ScanTo</a>'
            '</body></html>'
        )
        result = policy.enforce_html(source, "bn-BD")
        assert_blocked_page(self, result)
        self.assertIn("মূল তথ্য", result)
        self.assertEqual(policy.application_ids(result), {"6779977651"})
        self.assertNotIn('"offers"', result)
        self.assertEqual(policy.enforce_html(result, "bn-BD"), result)
        self.assertEqual(policy.enforce_html(source, "hi"), source)

    def test_non_app_download_and_offline_web_tool_facts_are_preserved(self):
        schema = {
            "@type": "SoftwareApplication", "name": "MCP",
            "downloadUrl": "https://github.com/example/adapter/releases/latest/download/adapter.mcpb",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        }
        self.assertEqual(policy.unavailable_json(schema, "bn-BD"), schema)

    def test_surface_boundary_is_idempotent_and_other_locale_bytes_unchanged(self):
        scratch = tempfile.TemporaryDirectory(prefix=".market-consumer-", dir=GEO / "tests")
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        for locale in ("bn-BD", "hi"):
            path = root / locale / "index.html"
            path.parent.mkdir()
            path.write_text('<html><head></head><body><h1>Content</h1>'
                            '<a href="https://apps.apple.com/in/app/id6779977651">Get</a></body></html>')
        before = (root / "hi/index.html").read_bytes()
        first = boundary.generate(root)
        self.assertEqual(first["changed"], 1)
        self.assertEqual(boundary.generate(root)["changed"], 0)
        self.assertEqual((root / "hi/index.html").read_bytes(), before)
        assert_blocked_page(self, (root / "bn-BD/index.html").read_text())

    def test_publisher_feed_keeps_content_catalog_but_outbox_empty(self):
        import portfolio_app_catalog_api as api
        app = {
            **self.cell, "key": "scanto", "name": "ScanTo",
            "guide_url": "https://example.com/bn-BD/scanto.html",
            "summary": "বাংলা তথ্য", "search_terms": ["স্ক্যান"],
        }
        feed = api.feed_payload("bn-BD", "অ্যাপ", [app], "2026-09-12", "a" * 64)
        self.assertEqual(feed["items"], [])
        self.assertEqual(feed["_lumi_catalog"]["recordCount"], 1)
        self.assertEqual(feed["_lumi_catalog"]["market_availability"]["outbox_count"], 0)
        self.assertNotIn("apps.apple.com", json.dumps(feed))

    def test_directory_retains_every_app_as_a_blocked_content_card(self):
        import os
        import build_pages_i18n as primary
        pages = Path(os.environ.get("GEO_PAGES", primary.PAGES))
        apps = json.loads((pages / "data/verified-ios-app-finder-catalog.json").read_text())["apps"]
        records = primary.localized_directory_records("bn-BD", [app["key"] for app in apps])
        self.assertEqual(len(records), 47)
        self.assertEqual({record["app_id"] for record in records}, {str(app["app_store_id"]) for app in apps})
        source = (pages / "bn-BD/index.html").read_text()
        assert_blocked_page(self, source)
        self.assertEqual(source.count('class="app-card"'), 47)
        for record in records:
            assert_blocked_record(self, record, ("canonical_store", "store_url"))
            self.assertIsNone(record["storefront"])
            self.assertFalse(record["storefront_verified"])
            self.assertIn(f'href="{record["key"]}.html"', source)
            schema = primary.localized_directory_schema_item(record)
            self.assertNotIn("installUrl", schema)
            self.assertNotIn("offers", schema)
            self.assertNotIn("apps.apple.com", json.dumps(schema))

    def test_llms_retains_native_content_without_a_fallback_listing(self):
        import os
        import gen_llms
        pages = Path(os.environ["GEO_PAGES"])
        source = gen_llms.build_localized_llms("bn-BD", ["scanto"], pages)
        self.assertIn("ScanTo", source)
        self.assertNotIn("apps.apple.com", source)
        self.assertNotIn("App Store: None", source)
        self.assertIn("MARKET_UNAVAILABLE_OR_UNVERIFIED", source)
        self.assertIn("https://support.apple.com/en-us/118205", source)

    def test_shopping_ingestion_excludes_blocked_market_without_losing_apps(self):
        import os
        import agent_product_feed as feed
        pages = Path(os.environ["GEO_PAGES"])
        rows, modified = feed.build_rows(pages)
        self.assertEqual({row["item_group_id"] for row in rows}, {
            row["key"] for row in json.loads(
                (pages / "data/verified-ios-app-finder-catalog.json").read_text()
            )["apps"]
        })
        self.assertFalse(any(row["content_language"] == "bn-BD" for row in rows))
        metadata = feed.index_payload(rows, modified)
        self.assertEqual(metadata["official_locale_count"], 50)
        self.assertEqual(metadata["locale_count"], 49)
        self.assertEqual(metadata["blocked_markets"]["bn-BD"]["outbox_count"], 0)

    def test_finder_webmcp_runtime_preserves_blocked_evidence_in_every_match(self):
        import os
        import re
        import subprocess
        import portfolio_app_finder as finder
        pages = Path(os.environ["GEO_PAGES"])
        catalog = json.loads((pages / "data/verified-ios-app-finder-catalog.json").read_text())
        records = finder.localized_page_records(finder.verified_records(catalog["apps"]), pages)
        source = finder.render_page("bn-BD", records)
        assert_blocked_page(self, source)
        data = json.loads(re.search(r"const WEBMCP_RECORDS=(.*);\n", source)[1])
        context = json.loads(re.search(r"const WEBMCP_MARKET_FIELDS=(.*);\n", source)[1])
        self.assertEqual(len(data), 47)
        expression = re.search(
            r"return JSON.stringify\((\{.*?\})\);\s*\}",
            source[source.index("async function registerWebMcp"):],
            re.S,
        )[1]
        runner = """
const fs=require('node:fs'),vm=require('node:vm');
const x=JSON.parse(fs.readFileSync(0,'utf8'));
const result=vm.runInNewContext('('+x.expression+')',{matches:x.records,WEBMCP_MARKET_FIELDS:x.market});
process.stdout.write(JSON.stringify(result));
"""
        result = subprocess.run(
            ["node", "-e", runner],
            input=json.dumps({"expression": expression, "records": data, "market": context}),
            text=True, capture_output=True, timeout=30, check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["match_count"], 47)
        self.assertEqual(payload["market_availability"]["outbox_count"], 0)
        for match in payload["matches"]:
            assert_blocked_record(self, match, ("app_store_url",))
        self.assertNotIn("apps.apple.com", result.stdout)

    def test_alternatives_loader_rejects_forged_or_absent_market_exception(self):
        fixture = GEO / "tests/fixtures/alternatives_exact50"
        manifest = alternatives.load_manifest(fixture / "manifest.json")
        inventory = alternatives.load_inventory(fixture / "inventory.json", manifest)
        records = alternatives.load_catalog(fixture / "catalog.json", manifest, inventory, alternatives.PUBLIC_SITE)
        assert_blocked_record(self, records[("scanto", "bn-BD")])
        scratch = tempfile.TemporaryDirectory(prefix=".market-catalog-", dir=GEO / "tests")
        self.addCleanup(scratch.cleanup)
        payload = json.loads((fixture / "catalog.json").read_text())
        row = next(r for r in payload["records"] if r["locale"] == "bn-BD")
        del row["market_availability"]
        path = Path(scratch.name) / "invalid.json"
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "state/reason/evidence"):
            alternatives.load_catalog(path, manifest, inventory, alternatives.PUBLIC_SITE)

    def test_browse_regeneration_preserves_blocked_evidence_and_navigation(self):
        import gen_link_hubs
        page = gen_link_hubs.render_browse(
            "bn-BD", "bn-BD", [("apps", [("bn-BD/scanto.html", "ScanTo")])], 1,
            ["https://example.com/bn-BD/browse.html"], "https://example.com/bn-BD/index.html",
        )
        assert_blocked_page(self, page)
        self.assertIn("scanto.html", page)
        self.assertIn('content="noindex,follow"', page)
        self.assertIn('href="https://example.com/bn-BD/browse.html"', page)

    def test_published_hub_gate_requires_exact_attribution_and_rejects_wrong_provider(self):
        import os
        import gen_hubs
        import check_hub_coverage as hubs
        pages = Path(os.environ["GEO_PAGES"])
        app = gen_hubs.authority_apps()["scanto"]
        locales = gen_hubs.official_locales()
        source, _, providers = hubs._validate_hub(
            pages, "scanto", app, locales, provider_token="118326163", attributed=True
        )
        self.assertEqual(providers, {"118326163"})
        scratch = tempfile.TemporaryDirectory(prefix=".published-hub-", dir=GEO / "tests")
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        (root / "hubs").mkdir()
        (root / "hubs/scanto.html").write_text(source.replace("pt=118326163", "pt=999999999"))
        with self.assertRaises(hubs.HubContractError):
            hubs._validate_hub(
                root, "scanto", app, locales, provider_token="118326163", attributed=True
            )


if __name__ == "__main__":
    unittest.main()
