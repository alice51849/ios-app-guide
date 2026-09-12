"""Exact9 product truth without new URLs, false availability or sales claims."""
import copy
import html
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import aeo_answers
import aeo_answers_i18n
import app_store_storefronts as stores
import build_pages_i18n
import gen_review_pages
import market_availability as market
from official_locales import OFFICIAL_LOCALES
import paid_upfront_surfaces as repairs
from videogen.registry import APPSTORE


PAGES = Path(os.environ.get("GEO_PAGES", repairs.HERE / "pages")).resolve()


def schemas(source):
    return [
        node for match in repairs.JSON_RE.finditer(source)
        for node in repairs._nodes(json.loads(match[2]))
    ]


class PaidUpfrontSurfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = repairs.targets()
        cls.availability = stores.load_storefront_availability(PAGES)

    def rendered(self, relative):
        before = (PAGES / relative).read_text()
        row = self.targets[relative]
        if row["kind"] == "review":
            review = next(item for item in gen_review_pages.REVIEWS if item["key"] == row["key"])
            after = gen_review_pages.render(review, pages=PAGES)
        else:
            after = repairs.rewrite(before, relative, PAGES, availability=self.availability)
        return before, after

    def test_exact9_thirteen_existing_surfaces_and_public_evidence(self):
        self.assertEqual(9, len(repairs.contract()["apps"]))
        self.assertEqual(13, len(self.targets))
        self.assertEqual(set(repairs.EXACT_IDS), {row["key"] for row in self.targets.values()})
        for key, row in repairs.contract()["apps"].items():
            with self.subTest(key=key):
                self.assertEqual(APPSTORE[key], row["app_id"])
                self.assertEqual("paid_upfront", row["business_model"])
                self.assertRegex(row["description_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(all((PAGES / relative).is_file() for relative in self.targets))

    def test_unverified_storefronts_fail_closed(self):
        for relative, row in self.targets.items():
            with self.subTest(path=relative):
                with self.assertRaisesRegex(ValueError, "Unverified"):
                    repairs.require_available(row["key"], row["locale"], PAGES, {})
                if row["kind"] != "review":
                    with self.assertRaisesRegex(ValueError, "Unverified"):
                        repairs.rewrite((PAGES / relative).read_text(), relative, PAGES, availability={})
        with self.assertRaises(ValueError):
            repairs.require_available("wordmate", "bn-BD", PAGES, self.availability)

    def test_page_identity_and_output_idempotence(self):
        for relative, row in self.targets.items():
            with self.subTest(path=relative):
                before, after = self.rendered(relative)
                self.assertIn(f'rel="canonical" href="{repairs.PUBLIC_SITE}/{relative}"', after)
                self.assertIn(f'id{repairs.EXACT_IDS[row["key"]]}', after)
                if row["kind"] != "review":
                    self.assertEqual(after, repairs.rewrite(after, relative, PAGES, availability=self.availability))
                    before_ids = re.findall(r'href="https://apps\.apple\.com/[^"]*id(\d+)[^"]*"', before)
                    after_ids = re.findall(r'href="https://apps\.apple\.com/[^"]*id(\d+)[^"]*"', after)
                    self.assertEqual(before_ids, after_ids)

    def test_wrong_page_or_app_identity_is_rejected(self):
        relative = "ja/answers/best-offline-english-listening-and-reading-exam-trainer-for-iphone.html"
        source = (PAGES / relative).read_text()
        with self.assertRaisesRegex(ValueError, "canonical"):
            repairs.rewrite(source.replace(f"{repairs.PUBLIC_SITE}/{relative}", f"{repairs.PUBLIC_SITE}/wrong.html"), relative, PAGES)
        with self.assertRaisesRegex(ValueError, "App ID"):
            repairs.rewrite(source.replace("id6792483140", "id1234567890"), relative, PAGES)

    def test_ctas_use_verified_local_markets_and_preserve_campaigns(self):
        import gen_store_attribution as attribution
        for relative, row in self.targets.items():
            with self.subTest(path=relative):
                before, source = self.rendered(relative)
                old_links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', before)
                new_links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', source)
                self.assertEqual(len(old_links), len(new_links))
                for old, new in zip(old_links, new_links):
                    old, new = urlsplit(html.unescape(old)), urlsplit(html.unescape(new))
                    self.assertEqual(parse_qs(old.query), parse_qs(new.query))
                    self.assertEqual(
                        f'/'+stores.LOCALE_STOREFRONTS[row["locale"]]+f'/app/id{repairs.EXACT_IDS[row["key"]]}',
                        new.path,
                    )
                self.assertIsNone(attribution.qr_card_desync(source))

    def test_four_reviews_are_disclosed_articles_not_self_ratings(self):
        for relative, key in repairs.contract()["reviews"].items():
            with self.subTest(key=key):
                _, source = self.rendered(relative)
                self.assertIn("First-party product guide by Lumi Studio", source)
                self.assertIn("Paid download · One upfront purchase", source)
                self.assertNotIn("reviewRating", source)
                self.assertNotIn("aggregateRating", source)
                self.assertNotIn("<span>4/5</span>", source)
                self.assertNotIn('<span class="badge">Free', source)
                self.assertNotIn('"@type": "Offer"', source)
                self.assertNotIn('"@type": "Review"', source)
                self.assertIn('"@type": "Article"', source)
                links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', source)
                self.assertEqual(1, len(links))
                url = urlsplit(html.unescape(links[0]))
                self.assertEqual(f"/us/app/id{repairs.EXACT_IDS[key]}", url.path)
                self.assertEqual(
                    {"pt": ["118326163"], "ct": ["geo_pick"], "mt": ["8"]},
                    parse_qs(url.query),
                )

    def test_daily_mate_retains_phrases_and_watch_not_habits(self):
        _, source = self.rendered("reviews/dailymate-habit-tracker-review-2026.html")
        for required in ("8,400", "47 learning languages", "84 situations", "complete phrases", "Apple Watch", "system voice"):
            self.assertIn(required, source)
        for forbidden in ("No Apple Watch companion", "Clean, clutter-free habit logging", "logs recurring daily tasks", "Streaks subscription"):
            self.assertNotIn(forbidden, source)
        self.assertIn("not live translation", source)

    def test_hours_tag_preserves_original_history_categories_goals_and_backup(self):
        _, source = self.rendered("reviews/hourstag-review-2026-is-it-worth-it.html")
        for required in ("Saved records", "category insights", "goals", "back up and restore", "illustrative inputs"):
            self.assertIn(required, source)
        self.assertNotIn("doesn't track spending history", source)
        self.assertNotIn("No. HoursTag converts prices in the moment", source)

    def test_gmoney_is_a_daily_ledger_not_a_lite_upgrade(self):
        _, source = self.rendered("reviews/gmoney-travel-budget-app-review-2026.html")
        for required in ("daily", "CSV", "custom categories", "iPhone and iPad", "optional", "manually"):
            self.assertIn(required, source)
        for forbidden in ("as a one-time paid upgrade", "not granular category analysis", "runs on iPad in compatibility mode"):
            self.assertNotIn(forbidden, source)

    def test_snapport_separates_outputs_from_authority_acceptance(self):
        for relative in self.targets:
            if self.targets[relative]["key"] != "snapport":
                continue
            with self.subTest(path=relative):
                _, source = self.rendered(relative)
                for required in ("JPEG", "PNG", "PDF", "4×6", "2×2", "authority", "digital"):
                    self.assertIn(required, source)
                for forbidden in ("Most users find", "take a compliant photo", "30 seconds"):
                    self.assertNotIn(forbidden, source)
                self.assertIn("does not guarantee", source)

    def test_aim990plus_has_native_adult_timed_loop_and_limits(self):
        _, source = self.rendered("ja/answers/best-offline-english-listening-and-reading-exam-trainer-for-iphone.html")
        for required in ("8問", "20問", "15分", "630問", "大人", "有料ダウンロード", "保証", "ETS"):
            self.assertIn(required, source)
        self.assertNotIn("Build calm, accurate decisions", source)
        self.assertNotIn(">best offline English listening", source)
        self.assertNotIn("無料枠の上限を比べ", source)

    def test_hours_tag_native_answers_do_not_keep_english_fallback(self):
        for locale in ("zh-Hant", "ko"):
            _, source = self.rendered(f"{locale}/answers/best-app-to-track-where-my-money-goes-and-save-more.html")
            self.assertNotIn("If saving feels abstract", source)
            self.assertNotIn("Set savings targets", source)
            self.assertNotIn("Goals/wishlist tracked", source)
            self.assertNotIn(">best app to track where", source)
            self.assertIn("CSV", source)

    def test_math_pro_adds_parent_outputs_without_shrinking_the_app(self):
        relative = "zh-Hant/answers/best-complete-math-learning-app-for-preschool-and-early-grades.html"
        before, source = self.rendered(relative)
        for required in ("20題", "家長閘門", "14個星球", "46種題型", "弱項", "PDF", "本機匯出"):
            self.assertIn(required, source)
        self.assertEqual(
            len(re.findall(r'href="[^"]*id6776958488[^"]*"', before)),
            len(re.findall(r'href="[^"]*id6776958488[^"]*"', source)),
        )

    def test_wordmate_is_a_small_clarification_and_keeps_existing_faqs(self):
        relative = "zh-Hant/answers/best-vocabulary-app-for-busy-commuters-with-apple-watch.html"
        before, source = self.rendered(relative)
        old = next(node for node in schemas(before) if node.get("@type") == "FAQPage")
        new = next(node for node in schemas(source) if node.get("@type") == "FAQPage")
        self.assertEqual(old["mainEntity"][1:], new["mainEntity"][1:])
        self.assertEqual(1, source.count("<!-- paid-upfront-clarification:start -->"))
        for required in ("44個學習語言", "切換", "收藏", "相符系統語音", "50個內容語系"):
            self.assertIn(required, source)

    def test_visible_faq_and_schema_are_the_same_claims(self):
        for relative in self.targets:
            with self.subTest(path=relative):
                _, source = self.rendered(relative)
                visible = repairs.JSON_RE.sub("", source)
                faq = [node for node in schemas(source) if node.get("@type") == "FAQPage"]
                self.assertEqual(1, len(faq))
                for item in faq[0]["mainEntity"]:
                    self.assertIn(html.escape(item["name"]), visible)
                    self.assertIn(html.escape(item["acceptedAnswer"]["text"]), visible)

    def test_landings_and_catalog_share_owned_not_asc_copy(self):
        for row in repairs.contract()["landings"]:
            relative = f'{row["locale"]}/{row["key"]}.html'
            _, source = self.rendered(relative)
            values = build_pages_i18n.load_app_locales(row["key"])[row["locale"]]
            self.assertTrue(values["description"].startswith(row["intro"]))
            self.assertIn(html.escape(row["intro"]), source)
            if row["key"] == "lumimissionpro":
                self.assertNotIn("Gratis proberen", source)
                self.assertIn("onbeperkt eigen missies", source)
                self.assertIn("oudercontrole", source)
            else:
                body = source.split("<body", 1)[1]
                self.assertLess(body.index("paid-upfront-intro:start"), body.index("家庭带宽需求表"))
                self.assertIn("最可能", source)
                self.assertIn("RSSI", source)
                self.assertIn("不保证", source)

    def test_description_override_does_not_mutate_metadata_or_other_locales(self):
        values = {"nl-NL": {"description": "original ASC text"}, "en-US": {"description": "keep"}}
        before = copy.deepcopy(values)
        changed = repairs.localized_descriptions("lumimissionpro", values)
        self.assertEqual(before, values)
        self.assertEqual(before["en-US"], changed["en-US"])
        self.assertNotEqual(before["nl-NL"], changed["nl-NL"])
        self.assertEqual(values, repairs.localized_descriptions("dailymate", values))

    def test_generator_hooks_restore_the_same_copy(self):
        relative = "ja/answers/best-offline-english-listening-and-reading-exam-trainer-for-iphone.html"
        before, expected = self.rendered(relative)
        with patch.object(aeo_answers_i18n, "ROOT", PAGES):
            result = aeo_answers_i18n.finalize_html(before, "ja", Path(relative).stem)
        self.assertIn(html.escape(self.targets[relative]["lead"]), result)
        self.assertIn(html.escape(self.targets[relative]["heading"]), expected)
        question = "best passport photo app for babies and toddlers at home"
        source = aeo_answers.render_page(question, "snapport", aeo_answers.default_content(question, "snapport"), pages_root=PAGES)
        self.assertIn("4×6", source)
        self.assertNotIn("take a compliant photo", source)

    def test_47_by_50_floor_bn_content_only_and_four_unknowns_are_untouched(self):
        catalog = json.loads((PAGES / "data/verified-ios-app-finder-catalog.json").read_text())
        self.assertEqual(47, len(catalog["apps"]))
        self.assertEqual(50, len(OFFICIAL_LOCALES))
        for row in catalog["apps"]:
            key = row["key"]
            self.assertTrue(all((PAGES / locale / f"{key}.html").is_file() for locale in OFFICIAL_LOCALES))
            relative = f"bn-BD/{key}.html"
            before = (PAGES / relative).read_text()
            self.assertEqual(before, repairs.rewrite(before, relative, PAGES, availability={}))
            self.assertNotIn("apps.apple.com", before)
        for key, locale in (
            ("lumibopomofo", "zh-Hans"), ("lumibopomofopro", "zh-Hans"),
            ("lumiletterspro", "zh-Hans"), ("zipbox", "fr-FR"),
        ):
            self.assertNotIn(APPSTORE[key], self.availability.get(stores.LOCALE_STOREFRONTS[locale], ()))
            self.assertFalse(market.is_unavailable(locale, APPSTORE[key]))


if __name__ == "__main__":
    unittest.main()
