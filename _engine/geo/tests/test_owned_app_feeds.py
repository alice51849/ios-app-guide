from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import (
    FeedFixture, GEO, OLD, NEW, build_pages_i18n, feeds, market,
    OFFICIAL_LOCALES, reseal_catalog, write_json,
)
import owned_feed_locale_gate as locale_gate


class LocaleGateTests(unittest.TestCase):
    def test_every_official_locale_has_an_explicit_script_contract(self):
        self.assertEqual(set(OFFICIAL_LOCALES), set(locale_gate.SCRIPTS))
        copy = feeds.load_copy(GEO)
        for locale in OFFICIAL_LOCALES:
            with self.subTest(locale=locale):
                locale_gate.validate_text(locale, copy[locale]["disclosure"], "native")
                foreign = "中" if locale not in {"zh-Hans", "zh-Hant", "ja"} else "ಕ"
                with self.assertRaisesRegex(ValueError, "Cross-script"):
                    locale_gate.validate_text(locale, copy[locale]["disclosure"] + foreign, "mixed")

    def test_kannada_source_is_not_the_old_simplified_chinese_sentence(self):
        value = build_pages_i18n.external_localized_values("lumimathpro", "kn-IN")
        locale_gate.validate_summary("kn-IN", value["description"], "paid_upfront")
        self.assertNotIn("与你", value["description"])
        with self.assertRaisesRegex(ValueError, "Cross-script"):
            locale_gate.validate_summary("kn-IN", "Lumi ಕರಡಿ与你一起探索数学的宇宙。", "paid_upfront")

    def test_english_fallback_and_literal_prices_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing native"):
            locale_gate.validate_text("bn-BD", "Explore mathematical adventures", "summary")
        for price in ("$4.99", "₹999", "৳300", "9.99 EUR", "9,99 €", "99 kr", "9.99 PKR"):
            with self.subTest(price=price), self.assertRaisesRegex(ValueError, "Literal price"):
                locale_gate.validate_summary("en-US", "Buy now for " + price, "paid_upfront")

    def test_paid_free_claims_are_rejected_in_all_locales(self):
        self.assertEqual(
            {loc.split("-")[0] for loc in OFFICIAL_LOCALES}, set(locale_gate.FREE_TERMS)
        )
        for locale, claim in (("en-US", "Free math puzzles"), ("kn-IN", "ಉಚಿತ ಗಣಿತ ಆಟಗಳು"),
                              ("zh-Hant", "免費數學遊戲")):
            with self.subTest(locale=locale), self.assertRaisesRegex(ValueError, "Free claim"):
                locale_gate.validate_summary(locale, claim, "paid_upfront")
        locale_gate.validate_summary("en-US", "Ad-free math puzzles", "paid_upfront")


class OwnedFeedTests(FeedFixture):
    def test_exact_150_feeds_2350_records_and_cross_format_identity(self):
        manifest = feeds.read_manifest(self.pages)
        self.assertEqual((47, 50, 2350, 150, 147), tuple(manifest[k] for k in (
            "app_count", "locale_count", "record_count", "feed_count", "notification_feed_count"
        )))
        self.assertEqual({"paid_upfront": 13, "free_with_lifetime_unlock": 34},
                         manifest["purchase_models"])
        paths, pairs = set(), set()
        for locale in OFFICIAL_LOCALES:
            document = feeds.read_json(self.pages / feeds.feed_path(locale, "json_feed"))
            atom = ET.parse(self.pages / feeds.feed_path(locale, "atom"))
            rss = ET.parse(self.pages / feeds.feed_path(locale, "rss"))
            ids = [i["id"] for i in document["items"]]
            self.assertEqual(ids, [n.text for n in atom.findall(f"{{{feeds.ATOM}}}entry/{{{feeds.ATOM}}}id")])
            self.assertEqual(ids, [n.text for n in rss.findall("channel/item/guid")])
            for item in document["items"]:
                self.assertIn("<p>", item["content_html"])
                self.assertIn(item["_owned_app"]["publisher_disclosure"], item["content_text"])
                self.assertNotIn("price", item["_owned_app"])
                pairs.add((locale, item["_owned_app"]["app_store_id"]))
            paths.update(feeds.feed_path(locale, fmt) for fmt in feeds.FORMATS)
        actual = {p.relative_to(self.pages) for locale in OFFICIAL_LOCALES
                  for p in (self.pages / locale).iterdir()
                  if p.name in {spec[0] for spec in feeds.FORMATS.values()}}
        self.assertEqual(paths, actual)
        self.assertEqual(2350, len(pairs))

    def test_normal_generator_twice_and_next_day_are_byte_and_mtime_identical(self):
        before = self.fingerprints()
        for now in (OLD, NEW):
            result = feeds.build(self.pages, now=now)
            self.assertEqual(0, result["changed_files"])
            self.assertEqual(before, self.fingerprints())
        self.assertEqual(0, feeds.build(self.pages, now=NEW, check=True)["changed_files"])

    def test_unchanged_catalog_clock_does_not_change_any_owned_output(self):
        path = self.pages / feeds.CATALOG / "index.json"
        index = feeds.read_json(path)
        index.update(date_modified="2026-09-02", generated_at=NEW)
        write_json(path, index)
        for locale in OFFICIAL_LOCALES:
            p = self.pages / feeds.CATALOG / "locales" / f"{locale}.json"
            d = feeds.read_json(p)
            d.update(date_modified="2026-09-02", generated_at=NEW)
            write_json(p, d)
        before = self.fingerprints()
        self.assertEqual(0, feeds.build(self.pages, now=NEW)["changed_files"])
        self.assertEqual(before, self.fingerprints())

    def test_only_a_true_content_change_advances_one_item_date(self):
        path, document, app = self.catalog_app()
        app["summary"] += " Practice number patterns."
        desired = app["summary"]
        write_json(path, document)
        reseal_catalog(self.pages)
        original = build_pages_i18n.external_localized_values
        def values(key, locale, *args, **kwargs):
            result = original(key, locale, *args, **kwargs)
            if key == "lumimathpro" and locale == "en-US":
                result = {**result, "description": desired}
            return result
        with patch.object(build_pages_i18n, "external_localized_values", side_effect=values):
            result = feeds.build(self.pages, now=NEW)
            self.assertGreater(result["changed_files"], 0)
            self.assertEqual(0, feeds.build(self.pages, now=NEW)["changed_files"])
        updated = []
        for locale in OFFICIAL_LOCALES:
            for item in feeds.read_json(self.pages / feeds.feed_path(locale, "json_feed"))["items"]:
                self.assertEqual(OLD, item["date_published"])
                if item["date_modified"] == NEW:
                    updated.append((locale, item["_owned_app"]["app_key"]))
        self.assertEqual([("en-US", "lumimathpro")], updated)

    def test_all_bengali_content_is_retained_without_any_store_url_or_facts(self):
        for fmt in feeds.FORMATS:
            raw = (self.pages / feeds.feed_path("bn-BD", fmt)).read_text()
            self.assertNotIn("apps.apple.com", raw)
            self.assertNotIn("storefront_facts", raw)
            self.assertNotIn("formatted_price", raw)
            self.assertNotIn('rel="hub"', raw)
            self.assertNotIn("<cloud", raw)
        document = feeds.read_json(self.pages / "bn-BD/feed.json")
        self.assertEqual(47, len(document["items"]))
        for item in document["items"]:
            self.assertNotIn("external_url", item)
            self.assertEqual(
                market.record_fields("bn-BD")["market_availability"],
                item["_owned_app"]["market_availability"],
            )

    def test_null_store_url_is_allowed_only_with_the_exact_bengali_contract(self):
        for locale in ("bn-BD", "en-US"):
            path, doc, app = self.catalog_app(locale)
            app["app_store_url"] = None
            app.pop("market_availability", None)
            write_json(path, doc)
        with self.assertRaisesRegex(ValueError, "market state|requires App Store"):
            feeds.build(self.pages, now=NEW)

    def test_bengali_fallback_urls_and_storefront_facts_fail_closed(self):
        path, original, _ = self.catalog_app("bn-BD")
        for value in (
            {"app_store_url": "https://apps.apple.com/us/app/id6776958488"},
            {"app_store_url": "https://apps.apple.com/in/app/id6776958488"},
            {"app_store_url": "https://apps.apple.com/app/id6776958488"},
            {"app_store_url": "https://apps.apple.com/bd/app/id6776958488"},
            {"storefront_facts": {"price": 0}},
        ):
            with self.subTest(value=value):
                doc = copy.deepcopy(original)
                app = next(a for a in doc["apps"] if a["key"] == "lumimathpro")
                app.update(value)
                write_json(path, doc)
                with self.assertRaises(ValueError):
                    feeds.build(self.pages, now=NEW)

    def test_mutated_identity_purchase_canonical_and_duplicate_apps_are_rejected(self):
        path, original, _ = self.catalog_app()
        mutations = (
            {"app_store_id": "123"}, {"purchase_model": "free_with_lifetime_unlock"},
            {"one_time_option": False}, {"guide_url": "https://example.org/"},
            {"app_store_url": "https://apps.apple.com/jp/app/id6776958488?pt=118326163&ct=bad&mt=8"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                doc = copy.deepcopy(original)
                next(a for a in doc["apps"] if a["key"] == "lumimathpro").update(mutation)
                write_json(path, doc)
                with self.assertRaises(ValueError):
                    feeds.build(self.pages, now=NEW)
        doc = copy.deepcopy(original)
        doc["apps"][-1] = doc["apps"][0]
        write_json(path, doc)
        with self.assertRaises(ValueError):
            feeds.build(self.pages, now=NEW)

    def test_foreign_script_is_rejected_even_when_declared_catalog_digest_is_resealed(self):
        path, doc, app = self.catalog_app("kn-IN")
        app["summary"] = "Lumi ಕರಡಿ与你一起探索数学的宇宙。"
        write_json(path, doc)
        reseal_catalog(self.pages)
        with self.assertRaisesRegex(ValueError, "Cross-script"):
            feeds.build(self.pages, now=NEW)

    def test_catalog_content_drift_and_mixed_generations_fail_closed(self):
        path, doc, app = self.catalog_app()
        app["untracked_fact"] = "changed"
        write_json(path, doc)
        with self.assertRaisesRegex(ValueError, "Catalog content digest"):
            feeds.build(self.pages, now=NEW)
        doc["content_digest"] = "0" * 64
        write_json(path, doc)
        with self.assertRaisesRegex(ValueError, "Mixed catalog generation"):
            feeds.build(self.pages, now=NEW)

    def test_native_source_drift_is_rejected_without_regenerating_catalog(self):
        original = build_pages_i18n.external_localized_values
        def values(key, locale, *args, **kwargs):
            result = original(key, locale, *args, **kwargs)
            if key == "lumimathpro" and locale == "en-US":
                result = {**result, "description": "New number practice with Lumi Math Pro."}
            return result
        with patch.object(build_pages_i18n, "external_localized_values", side_effect=values):
            with self.assertRaisesRegex(ValueError, "Stale catalog localization"):
                feeds.build(self.pages, now=NEW, check=True)

    def test_partial_output_fails_closed_before_publication(self):
        path = self.pages / "kn-IN/rss.xml"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Partial or mixed"):
            feeds.read_manifest(self.pages)
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "source/output drift"):
            feeds.build(self.pages, now=NEW, check=True)
        self.assertEqual(before, self.fingerprints())

    def test_duplicate_json_keys_are_never_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            feeds.decode(b'{"locale":"en-US","locale":"kn-IN"}')

    def test_an_extra_locale_feed_cannot_be_hidden_outside_the_manifest(self):
        path = self.pages / "xx" / "feed.json"
        write_json(path, {"items": []})
        with self.assertRaisesRegex(ValueError, "exact 150-path set"):
            feeds.read_manifest(self.pages)
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "exact 150-path set"):
            feeds.build(self.pages, now=NEW)
        self.assertEqual(before, self.fingerprints())

    def test_sitemap_and_discovery_are_scoped_and_do_not_rewrite_foreign_dates(self):
        root = ET.parse(self.pages / feeds.SITEMAP)
        locations = {n.text for n in root.findall(f"{{{feeds.SITEMAP_NS}}}url/{{{feeds.SITEMAP_NS}}}loc")}
        expected = {feeds.url(feeds.DIRECTORY)} | {
            feeds.url(feeds.feed_path(loc, fmt)) for loc in OFFICIAL_LOCALES for fmt in feeds.FORMATS
        }
        self.assertEqual(expected, locations)
        global_index = (self.pages / "sitemap_index.xml").read_text()
        self.assertIn("<lastmod>2026-08-01</lastmod>", global_index)
        self.assertEqual(1, global_index.count(feeds.url(feeds.SITEMAP)))
        for locale in OFFICIAL_LOCALES:
            source = (self.pages / locale / "index.html").read_text()
            self.assertEqual(1, source.count(feeds.HEAD_START))
            for fmt, (_, mime) in feeds.FORMATS.items():
                self.assertIn(f'type="{mime}"', source)
                self.assertIn(feeds.url(feeds.feed_path(locale, fmt)), source)

    def test_broken_previous_dates_or_digests_cannot_silently_reset_ids(self):
        path = self.pages / "en-US/feed.json"
        doc = feeds.read_json(path)
        doc["items"][0]["date_published"] = NEW
        write_json(path, doc)
        with self.assertRaisesRegex(ValueError, "Reversed"):
            feeds.build(self.pages, now=NEW)

    def test_pair_source_gate_rejects_a_single_drifted_mirror(self):
        reference = self.root / "reference" / "geo"
        for name in feeds.SOURCE_FILES:
            target = reference / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(GEO / name, target)
        feeds.require_parity(GEO, reference)
        path = reference / "market_availability.py"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Paired source drift"):
            feeds.require_parity(GEO, reference)


class PipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = Path(os.environ.get(
            "OWNED_FEED_GUIDE_ROOT",
            GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages",
        ))

    def test_regular_catalog_main_generates_owned_feeds_after_catalog(self):
        import portfolio_app_catalog_api as api
        calls = []
        with patch.object(api, "live_app_keys", return_value={"lumimathpro"}), \
             patch.object(api, "build", side_effect=lambda **kw: calls.append("catalog") or []), \
             patch.object(feeds, "build", side_effect=lambda *a, **kw: calls.append("feeds")):
            api.main()
        self.assertEqual(["catalog", "feeds"], calls)

    def test_both_daily_commits_and_both_rebase_paths_require_catalog_feed_closure(self):
        workflow = (self.guide / ".github/workflows/geo-daily.yml").read_text()
        english = workflow.split("- name: Commit English content first", 1)[1].split("git add -A", 1)[0]
        localized = workflow.split("- name: Verify localized output before commit", 1)[1].split("git add -A", 1)[0]
        for segment in (english, localized):
            self.assertIn("owned_app_feeds.py", segment)
            self.assertIn("--refresh-catalog", segment)
            self.assertIn("--check", segment)
        for function in ("reconcile_english_phase()", "reconcile_localized_phase()"):
            segment = workflow.split(function, 1)[1].split("parallel_unittest.py", 1)[0]
            self.assertIn("owned_app_feeds.py", segment)
            self.assertIn("--refresh-catalog", segment)
            self.assertIn("--check", segment)

    def test_upload_gate_binds_external_source_and_notifiers_use_durable_state(self):
        workflow = (self.guide / ".github/workflows/pages.yml").read_text()
        before_upload = workflow.split("actions/upload-pages-artifact@", 1)[0]
        self.assertIn('--reference-source "$source_dir/geo"', before_upload)
        self.assertIn("owned_feed_delivery.py prepare", before_upload)
        self.assertIn("actions/cache/restore@", before_upload)
        self.assertIn("--include-legacy", before_upload)
        for protocol in ("websub", "rsscloud"):
            self.assertIn(f"--protocol {protocol} --execute", workflow)
            self.assertNotIn(f'python3 "$RUNNER_TEMP/notify_{protocol}.py"', workflow)
        self.assertIn("if: always() && steps.prepare_owned_feeds.outcome == 'success'", workflow)
        self.assertIn("actions/cache/save@", workflow)
        self.assertIn("branches: [main]", workflow)

    def test_global_lastmod_stamper_leaves_owned_feed_dates_to_their_generator(self):
        import gen_sitemap_lastmod
        with patch.object(Path, "glob", return_value=[
            Path("sitemap_owned_feeds.xml"), Path("sitemap_apps.xml")
        ]):
            self.assertEqual([Path("sitemap_apps.xml")], gen_sitemap_lastmod._sitemap_paths(Path(".")))

    def test_pair_gate_rejects_backward_or_sideways_guide_gitlinks(self):
        import owned_feed_pair_gate as pair
        with patch.object(pair.subprocess, "run") as run:
            run.return_value.returncode = 1
            with self.assertRaisesRegex(ValueError, "backwards or sideways"):
                pair.require_ancestor(Path("guide"), "a" * 40, "b" * 40)
            run.return_value.returncode = 0
            pair.require_ancestor(Path("guide"), "a" * 40, "b" * 40)
        with patch.object(pair, "git", return_value="100644 blob abc geo/pages"):
            with self.assertRaisesRegex(ValueError, "canonical Guide gitlink"):
                pair.gitlink(Path("growth"), "HEAD")


if __name__ == "__main__":
    unittest.main()
