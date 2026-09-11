from copy import deepcopy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import buyer_job_guides as guides
import gen_app_page_related


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.images = []
        self.alternates = []
        self.faqs = []
        self.in_details = False
        self.capture = None
        self.question = ""
        self.answer = ""
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "img":
            self.images.append(attrs)
        if tag == "link":
            self.alternates.append(attrs)
        if tag == "details":
            self.in_details = True
            self.question, self.answer = "", ""
        if self.in_details:
            if tag == "summary":
                self.capture = "q"
            elif tag == "p":
                self.capture = "a"

    def handle_data(self, value):
        if self.capture == "q":
            self.question += value
        elif self.capture == "a":
            self.answer += value

    def handle_endtag(self, tag):
        if tag in {"summary", "p"}:
            self.capture = None
        if tag == "details":
            self.faqs.append({"q": self.question, "a": self.answer})
            self.in_details = False


class BuyerGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = guides.PAGES.resolve()
        cls.config, cls.copies, cls.evidence, _ = guides.load_contract(cls.pages)
        cls.baseline = json.loads((cls.pages / guides.BASELINE).read_text())

    def rejected(self, change):
        config, copies, evidence, baseline = deepcopy(
            (self.config, self.copies, self.evidence, self.baseline)
        )
        change(config, copies, evidence, baseline)
        with self.assertRaises(guides.ContractError):
            guides.validate(config, copies, evidence, baseline)

    def test_nine_apps_preserve_exact_47_by_50_and_13_by_34(self):
        indexed = guides.validate(self.config, self.copies, self.evidence, self.baseline)
        self.assertEqual(47, len(indexed))
        self.assertTrue(all(len(rows) == 50 for rows in indexed.values()))
        self.assertEqual(9, len(self.config["apps"]))
        self.assertFalse(
            set(app["key"] for app in self.config["apps"])
            & set(self.config["excluded_conversion_apps"])
        )

    def test_both_native_copies_are_complete(self):
        for locale in ("en-US", "zh-Hant"):
            self.assertEqual(9, len(self.copies[locale]["apps"]))
            for app in self.config["apps"]:
                copy = self.copies[locale]["apps"][app["key"]]
                self.assertGreater(len(copy["steps"]), 2)
                self.assertGreater(len(copy["limits"]), 1)
                self.assertGreater(len(copy["faq"]), 1)

    def test_general_information_traffic_is_not_an_allowed_scope(self):
        self.rejected(lambda c, l, e, b: c.update(traffic_scope="general_information"))

    def test_each_app_has_explicit_excluded_information_intents(self):
        self.rejected(lambda c, l, e, b: c["apps"][0].update(exclude_intents=[]))

    def test_generic_titles_cannot_replace_buying_decisions(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["gmoney"].update(title="How to save more money"))

    def test_brand_without_purchase_intent_is_not_enough(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["gmoney"].update(title="G+Money currency tips"))

    def test_generic_queries_cannot_enter_the_feed(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["gmoney"]["queries"].append("currency rates today"))

    def test_missing_baseline_locale_is_blocking(self):
        self.rejected(lambda c, l, e, b: b["records"].pop())

    def test_duplicate_baseline_locale_is_blocking(self):
        self.rejected(lambda c, l, e, b: b["records"].append(deepcopy(b["records"][0])))

    def test_model_drift_is_blocking(self):
        self.rejected(lambda c, l, e, b: b["records"][0].update(purchase_model="subscription"))

    def test_known_conversion_app_cannot_enter_increment(self):
        self.rejected(lambda c, l, e, b: c["excluded_conversion_apps"].append("gmoney"))

    def test_missing_native_page_cannot_fall_back_to_english(self):
        self.rejected(lambda c, l, e, b: l["zh-Hant"]["apps"].pop("gmoney"))

    def test_english_title_cannot_masquerade_as_traditional_chinese(self):
        self.rejected(lambda c, l, e, b: l["zh-Hant"]["apps"]["gmoney"].update(title="English fallback"))

    def test_english_ui_cannot_masquerade_as_traditional_chinese(self):
        self.rejected(lambda c, l, e, b: l["zh-Hant"]["ui"].update(rss="Read more"))

    def test_paid_app_cannot_acquire_free_core(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["gmoney"].update(free_core="Start free"))

    def test_paid_app_cannot_acquire_in_app_unlock(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["hourstag"].update(unlock="Upgrade once"))

    def test_paid_app_cannot_claim_a_free_trial_in_body(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["gmoney"]["steps"].append("Start a free trial."))

    def test_paid_app_cannot_claim_a_free_trial_in_chinese(self):
        self.rejected(lambda c, l, e, b: l["zh-Hant"]["apps"]["gmoney"]["steps"].append("可以免費試用。"))

    def test_freemium_needs_explicit_unlock(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["maskmyfile"].update(unlock=None))

    def test_hardcoded_price_is_blocking(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["photocream"]["steps"].append("Buy for $2.99."))

    def test_local_currency_prices_are_also_blocking(self):
        for price in ["只要 299 元。", "只要 NT$299。", "只要 ¥900。", "售價 9.99 EUR。"]:
            with self.subTest(price=price):
                self.rejected(lambda c, l, e, b: l["zh-Hant"]["apps"]["photocream"]["steps"].append(price))

    def test_rating_ranking_and_search_volume_claims_in_body_are_blocking(self):
        for claim in ["The #1 app.", "A 5-star choice.", "10,000 monthly searches."]:
            with self.subTest(claim=claim):
                self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["caldaily"]["steps"].append(claim))

    def test_actual_free_boundaries_remain_explicit(self):
        expected = {
            "maskmyfile": {"en-US": "first real cleaned-file export is free", "zh-Hant": "第一次真實檔案清理匯出也免費"},
            "photocream": {"en-US": "editing and look-preview", "zh-Hant": "照片編輯與風格預覽"},
            "tripplanet": {"en-US": "one trip", "zh-Hant": "一趟旅程"},
            "lumimath": {"en-US": "first planets and daily challenge", "zh-Hant": "入門星球與每日挑戰"},
            "caldaily": {"en-US": "three successful free uses", "zh-Hant": "三次成功計算"},
        }
        for key, locales in expected.items():
            for locale, phrase in locales.items():
                self.assertIn(phrase, self.copies[locale]["apps"][key]["free_core"])
        self.assertIn("watermark", self.copies["en-US"]["apps"]["photocream"]["unlock"])
        self.assertIn("浮水印", self.copies["zh-Hant"]["apps"]["photocream"]["unlock"])

    def test_ranking_and_review_fields_are_not_accepted(self):
        self.rejected(lambda c, l, e, b: l["en-US"]["apps"]["caldaily"].update(aggregateRating=5))

    def test_unrelated_internal_link_is_blocking(self):
        self.rejected(lambda c, l, e, b: c["apps"][0]["related"].append("mochi"))

    def test_path_traversal_is_blocking(self):
        self.rejected(lambda c, l, e, b: c["apps"][0].update(job="../../outside"))

    def test_missing_localized_proof_is_blocking(self):
        self.rejected(lambda c, l, e, b: e["apps"]["gmoney"].pop("zh-Hant"))

    def test_proof_app_identity_cannot_be_swapped(self):
        self.rejected(lambda c, l, e, b: e["apps"]["gmoney"]["en-US"].update(app_store_id="6754218117"))

    def test_proof_model_must_match_live_download_model(self):
        self.rejected(lambda c, l, e, b: e["apps"]["gmoney"]["en-US"].update(download_is_free=True))

    def test_proof_needs_a_sha256(self):
        self.rejected(lambda c, l, e, b: e["apps"]["gmoney"]["en-US"].update(screenshot_sha256="unknown"))

    def test_proof_cannot_be_a_generated_or_arbitrary_image(self):
        self.rejected(lambda c, l, e, b: e["apps"]["gmoney"]["en-US"].update(screenshot_url="https://example.com/fake.png"))

    def test_asc_cannot_be_a_public_evidence_endpoint(self):
        self.rejected(lambda c, l, e, b: e["lookup_receipts"]["en-US"].update(url="https://api.appstoreconnect.apple.com/v1/apps"))

    def test_cta_keeps_existing_provider_and_campaign_tokens(self):
        indexed = guides.validate(self.config, self.copies, self.evidence, self.baseline)
        for app in self.config["apps"]:
            for locale in self.config["locales"]:
                row = indexed[app["key"]][locale]
                value = guides.store_url(row, app, locale)
                self.assertEqual(row["app_store_url"], value)
                self.assertEqual({"pt", "ct", "mt"}, set(parse_qs(urlsplit(value).query)))

    def test_missing_provider_token_is_blocking(self):
        def change(c, l, e, baseline):
            row = next(row for row in baseline["records"] if row["app_key"] == "gmoney" and row["locale"] == "en-US")
            row["app_store_url"] = "https://apps.apple.com/us/app/id6755782939?ct=geo_pick&mt=8"
        self.rejected(change)

    def test_wrong_storefront_is_blocking(self):
        def change(c, l, e, baseline):
            row = next(row for row in baseline["records"] if row["app_key"] == "gmoney" and row["locale"] == "zh-Hant")
            row["app_store_url"] = row["app_store_url"].replace("/tw/", "/us/")
        self.rejected(change)

    def test_all_visible_faq_answers_equal_the_schema(self):
        generated, _ = guides.build_outputs(self.pages)
        for app in self.config["apps"]:
            for locale in self.config["locales"]:
                body = generated[guides.guide_path(app, locale)]
                page = Page(body)
                graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)[1])["@graph"]
                faq = next(node for node in graph if node["@type"] == "FAQPage")
                self.assertEqual(page.faqs, [
                    {"q": item["name"], "a": item["acceptedAnswer"]["text"]}
                    for item in faq["mainEntity"]
                ])
                application = next(node for node in graph if node["@type"] == "SoftwareApplication")
                self.assertEqual(app["app_store_id"], application["identifier"])
                self.assertEqual(
                    app["purchase_model"] == "free_with_lifetime_unlock",
                    application["isAccessibleForFree"],
                )
                self.assertNotIn("offers", application)
                self.assertNotIn("aggregateRating", application)
                self.assertNotIn("review", application)
                self.assertEqual(1, len([link for link in page.links if "apps.apple.com/" in link]))
                self.assertEqual(1, len(page.images))
                self.assertIn(self.copies[locale]["ui"]["disclosure"], body)

    def test_real_evidence_precedes_the_single_purchase_action(self):
        generated, _ = guides.build_outputs(self.pages)
        for app in self.config["apps"]:
            for locale in self.config["locales"]:
                body = generated[guides.guide_path(app, locale)]
                self.assertLess(body.index('<figure class="hero-proof">'), body.index('<a class="cta"'))
                self.assertLess(body.index('<img '), body.index('<a class="cta"'))
                self.assertIn('loading="eager"', body)
                self.assertIn(self.copies[locale]["apps"][app["key"]]["purchase_summary"], body)
                self.assertIn(self.copies[locale]["ui"]["proof_badge"], body)
                md = generated[guides.guide_path(app, locale)[:-5] + ".md"]
                self.assertLess(md.index("!["), md.index("https://apps.apple.com/"))

    def test_standalone_surface_never_mutates_portfolio_or_old_devto_queue(self):
        catalog_root = self.fixture()
        output = catalog_root / "standalone-site"
        output.mkdir()
        before = (catalog_root / "en-US/gmoney.html").read_bytes()
        site = "https://alice51849.github.io/awesome-ios-pay-once"
        generated, backlinks = guides.build_outputs(output, site=site, catalog_pages=catalog_root, standalone=True)
        self.assertFalse(backlinks)
        self.assertNotIn(guides.DEVTO_QUEUE, generated)
        self.assertIn("index.html", generated)
        body = generated[guides.guide_path(self.config["apps"][0], "en-US")]
        self.assertIn(f'{guides.PUBLIC_SITE}/en-US/gmoney.html', body)
        self.assertIn(f'{site}/buyer-guides/style.css', body)
        guides.materialize(output, site=site, catalog_pages=catalog_root, standalone=True)
        result = guides.materialize(output, check=True, site=site, catalog_pages=catalog_root, standalone=True)
        self.assertFalse(result["changed"])
        self.assertEqual(0, result["devto_drafts"])
        self.assertEqual(before, (catalog_root / "en-US/gmoney.html").read_bytes())

    def test_standalone_cannot_overwrite_its_source_catalog(self):
        with self.assertRaises(guides.ContractError):
            guides.build_outputs(self.pages, site="https://example.com/topic", catalog_pages=self.pages, standalone=True)

    def test_standalone_cannot_impersonate_the_portfolio_origin(self):
        root = self.fixture()
        output = root / "standalone-site"
        with self.assertRaises(guides.ContractError):
            guides.build_outputs(output, site=guides.PUBLIC_SITE, catalog_pages=root, standalone=True)

    def test_hreflang_advertises_only_authored_pages(self):
        generated, _ = guides.build_outputs(self.pages)
        for app in self.config["apps"]:
            for locale in self.config["locales"]:
                page = Page(generated[guides.guide_path(app, locale)])
                alternatives = {
                    row["hreflang"]: row["href"]
                    for row in page.alternates if "hreflang" in row
                }
                self.assertEqual({"en-US", "zh-Hant", "x-default"}, set(alternatives))
                for target in alternatives.values():
                    relative = target.removeprefix(guides.SITE + "/")
                    self.assertIn(relative, generated)

    def test_rss_and_json_feed_keep_native_bodies_and_payment_boundaries(self):
        generated, _ = guides.build_outputs(self.pages)
        feed = json.loads(generated[guides.JSON_FEED])
        self.assertEqual(18, len(feed["items"]))
        for locale in self.config["locales"]:
            root = ET.fromstring(generated[f"{guides.ROOT}/{locale}/feed.xml"])
            items = root.findall("./channel/item")
            self.assertEqual(9, len(items))
            self.assertEqual(locale, root.findtext("./channel/language"))
            for item in items:
                expected = next(row for row in feed["items"] if row["url"] == item.findtext("link"))
                self.assertEqual(expected["content_text"], item.findtext("description"))
                self.assertEqual(locale, expected["language"])
                self.assertIsNone(item.find("pubDate"))

    def test_devto_draft_is_bound_to_exact_canonical_html(self):
        generated, _ = guides.build_outputs(self.pages)
        drafts = json.loads(generated[guides.DEVTO_QUEUE])
        self.assertEqual(1, len(drafts))
        draft = drafts[0]
        path = draft["canonical_url"].removeprefix(guides.SITE + "/")
        self.assertEqual(guides.digest(generated[path]), draft["source_sha256"])
        self.assertEqual(generated[path[:-5] + ".md"], draft["body"])
        self.assertIn("maskmyfile", path)
        self.assertNotIn("published", draft)

    def test_only_independent_owned_surfaces_and_eighteen_app_links_change(self):
        generated, backlinks = guides.build_outputs(self.pages)
        self.assertEqual(18, len(backlinks))
        self.assertTrue(all(guides.owned(path) for path in generated))
        for path, output in backlinks.items():
            before = (self.pages / path).read_text()
            self.assertEqual(guides.BLOCK.sub("", before), guides.BLOCK.sub("", output))
        self.assertNotIn(guides.BASELINE, generated)
        catalog = json.loads(generated[guides.CATALOG])
        self.assertEqual("not_asserted_by_generator", catalog["publication_status"])
        self.assertTrue(all(row["measured_search_volume"] is None and row["is_ranking"] is False for row in catalog["items"]))

    def fixture(self):
        parent = GEO / "tests" / ".buyer-job-test-work"
        root = parent / uuid4().hex
        root.mkdir(parents=True)
        def cleanup():
            shutil.rmtree(root)
            try:
                parent.rmdir()
            except OSError:
                pass
        self.addCleanup(cleanup)
        (root / "data").mkdir()
        (root / guides.BASELINE).write_text(guides.json_text(self.baseline))
        for app in self.config["apps"]:
            for locale in self.config["locales"]:
                folder = root / locale
                folder.mkdir(exist_ok=True)
                (folder / f"{app['key']}.html").write_text(
                    '<html><body><main>'
                    f'<a href="https://apps.apple.com/app/id{app["app_store_id"]}">App</a>'
                    '</main>\n<!--iag-app-related--><section>Existing links</section>'
                    '<!--/iag-app-related-->\n<footer>Keep me</footer></body></html>'
                )
        (root / "en-US/mochi.html").write_text("Unrelated conversion app: do not modify")
        (root / ".appstore_live_state.json").write_text("Do not mutate")
        return root

    def test_materialization_is_idempotent_and_does_not_touch_baseline(self):
        root = self.fixture()
        baseline = (root / guides.BASELINE).read_bytes()
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
            first = guides.materialize(root)
            second = guides.materialize(root, check=True)
        self.assertEqual(18, first["guide_count"])
        self.assertGreater(len(first["changed"]), 18)
        self.assertEqual([], second["changed"])
        self.assertEqual([], second["removed"])
        self.assertEqual(baseline, (root / guides.BASELINE).read_bytes())
        self.assertEqual("Do not mutate", (root / ".appstore_live_state.json").read_text())
        self.assertEqual("Unrelated conversion app: do not modify", (root / "en-US/mochi.html").read_text())

    def test_check_mode_does_not_write(self):
        root = self.fixture()
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = guides.materialize(root, check=True)
        self.assertGreater(len(result["changed"]), 0)
        after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_modified_former_output_is_not_deleted(self):
        root = self.fixture()
        guides.materialize(root)
        old = root / "buyer-guides/old.html"
        old.write_text("Human changes")
        manifest = json.loads((root / guides.MANIFEST).read_text())
        manifest["generated"]["buyer-guides/old.html"] = guides.digest("Old generated content")
        (root / guides.MANIFEST).write_text(guides.json_text(manifest))
        with self.assertRaises(guides.ContractError):
            guides.materialize(root)
        self.assertEqual("Human changes", old.read_text())

    def test_verified_former_owned_output_is_removed(self):
        root = self.fixture()
        guides.materialize(root)
        old = root / "buyer-guides/old.html"
        old.write_text("Old generated content")
        manifest = json.loads((root / guides.MANIFEST).read_text())
        manifest["generated"]["buyer-guides/old.html"] = guides.digest(old.read_text())
        (root / guides.MANIFEST).write_text(guides.json_text(manifest))
        result = guides.materialize(root)
        self.assertEqual(["buyer-guides/old.html"], result["removed"])
        self.assertFalse(old.exists())

    def test_unowned_manifest_path_is_rejected(self):
        root = self.fixture()
        guides.materialize(root)
        manifest = json.loads((root / guides.MANIFEST).read_text())
        manifest["generated"]["en-US/mochi.html"] = guides.digest("Unrelated conversion app: do not modify")
        (root / guides.MANIFEST).write_text(guides.json_text(manifest))
        with self.assertRaises(guides.ContractError):
            guides.materialize(root)
        self.assertTrue((root / "en-US/mochi.html").exists())

    def test_backlink_placement_is_stable_beside_existing_related_links(self):
        app = self.config["apps"][0]
        copy = self.copies["en-US"]["apps"][app["key"]]
        ui = self.copies["en-US"]["ui"]
        original = "<main>App</main>\n<!--iag-app-related--><section>Existing</section><!--/iag-app-related-->\n<footer>End</footer>"
        once = guides.backlink(original, app, "en-US", copy, ui, guides.SITE)
        twice = guides.backlink(once, app, "en-US", copy, ui, guides.SITE)
        self.assertEqual(once, twice)
        self.assertEqual(original, guides.BLOCK.sub("", once))
        self.assertLess(once.index("<!--/iag-app-related-->"), once.index("<!--iag-buyer-job-->"))

    def test_all_locale_producer_invokes_increment_without_touching_single_locale_mode(self):
        with (
            mock.patch.object(gen_app_page_related, "process_locale"),
            mock.patch.object(gen_app_page_related, "process_hubs"),
            mock.patch.object(guides, "materialize", return_value={"changed": [], "removed": []}) as build,
            mock.patch.object(sys, "argv", ["gen_app_page_related.py"]),
        ):
            self.assertEqual(0, gen_app_page_related.main())
            build.assert_called_once()
        with (
            mock.patch.object(gen_app_page_related, "process_locale"),
            mock.patch.object(guides, "materialize") as build,
            mock.patch.object(sys, "argv", ["gen_app_page_related.py", "--locale", "zh-Hant"]),
        ):
            self.assertEqual(0, gen_app_page_related.main())
            build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
