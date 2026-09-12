"""Exact Indic content/purchase/script regressions; all fixtures are local."""
import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qsl, urlsplit

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import build_pages_i18n as pages
import indic_native_copy as native
import indic_native_candidates as candidates
import indic_text_gate as gate
import market_availability as market
from official_locales import OFFICIAL_LOCALES
from market_contract_assertions import assert_blocked_page, assert_blocked_record

EXPECTED_LOCALES = ("bn-BD", "gu-IN", "hi", "kn-IN", "ml-IN", "mr-IN", "or-IN", "pa-IN", "ta-IN", "te-IN")


class Visible(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.hidden = 0
        self.text = []
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden -= 1

    def handle_data(self, value):
        if not self.hidden:
            self.text.append(value)


class IndicNativePurchaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = Path(os.environ.get("GEO_PAGES", pages.PAGES))
        cls.apps = candidates.load_apps(cls.pages)
        cls.availability = candidates.stores.load_storefront_availability(cls.pages)
        cls.rows = candidates.inventory(cls.apps, cls.availability)
        cls.by_cell = {(row["app_key"], row["locale"]): row for row in cls.rows}
        cls.scratch = tempfile.TemporaryDirectory(prefix=".indic-native-", dir=os.environ.get("TMPDIR"))
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.output = Path(cls.scratch.name) / "candidate"
        cls.generated = candidates.generate(cls.pages, cls.output)

    def test_exact_47_by_10_inventory_never_drops_blocked_content(self):
        self.assertEqual(native.LOCALES, EXPECTED_LOCALES)
        self.assertEqual(len(self.apps), 47)
        self.assertEqual(len(self.rows), 470)
        self.assertEqual(set(self.by_cell), {(key, locale) for key in self.apps for locale in EXPECTED_LOCALES})
        self.assertEqual(self.generated["html_candidates"], 470)
        self.assertEqual(self.generated["blocked_bn_bd"], 47)
        self.assertEqual(self.generated["verified_india_ctas"], 423)
        self.assertEqual(self.generated["published"], 0)

    def test_source_delta_is_exact_49_cells_66_fields(self):
        observed = {}
        for key in self.apps:
            for locale in EXPECTED_LOCALES:
                current = pages.external_localized_values(key, locale)
                with mock.patch.object(native, "reviewed_values", side_effect=lambda key, locale, values, **facts: dict(values)):
                    baseline = pages.external_localized_values(key, locale)
                fields = {field for field in native.FIELDS if current[field] != baseline[field]}
                if fields:
                    observed[(key, locale)] = frozenset(fields)
        self.assertEqual(len(observed), 49)
        self.assertEqual(sum(map(len, observed.values())), 66)
        self.assertEqual(observed, native.TARGET_FIELDS)
        self.assertEqual(set(observed), native.TARGET_CELLS)
        self.assertEqual(
            sum("description" in values for values in observed.values()), 23
        )
        self.assertEqual(sum("promotionalText" in values for values in observed.values()), 7)
        self.assertEqual(sum("keywords" in values for values in observed.values()), 36)

    def test_other_40_locales_and_non_target_cells_are_unchanged(self):
        untouched = 0
        for key in self.apps:
            raw = pages.load_app_locales(key)
            snapshot = copy.deepcopy(raw)
            for locale in OFFICIAL_LOCALES:
                current = pages.external_localized_values(key, locale, raw)
                with mock.patch.object(native, "reviewed_values", side_effect=lambda key, locale, values, **facts: dict(values)):
                    baseline = pages.external_localized_values(key, locale, raw)
                if (key, locale) not in native.TARGET_CELLS:
                    self.assertEqual(current, baseline, (key, locale))
                    untouched += 1
            self.assertEqual(raw, snapshot, key)
        self.assertEqual(untouched, 2301)

    def test_every_repaired_field_has_at_least_95_percent_native_script(self):
        ratios = []
        for cell, fields in native.TARGET_FIELDS.items():
            row = self.by_cell[cell]
            for field in fields:
                with self.subTest(cell=cell, field=field):
                    value = row["content"][field]
                    ratio = gate.native_ratio(value, row["locale"])
                    ratios.append(ratio)
                    self.assertGreaterEqual(ratio, 0.95)
                    gate.validate(value, row["locale"], purchase_model=row["purchase_model"], minimum_ratio=0.95)
        self.assertEqual(len(ratios), 66)

    def test_all_470_cells_reject_cross_script_english_fallback_and_paid_trial_claims(self):
        for row in self.rows:
            for field in native.FIELDS:
                with self.subTest(app=row["app_key"], locale=row["locale"], field=field):
                    gate.validate(row["content"][field], row["locale"], purchase_model=row["purchase_model"])

    def test_aim990_six_languages_describe_practice_not_guaranteed_results(self):
        self.assertEqual(set(native.AIM_COPY), {"gu-IN", "kn-IN", "ml-IN", "or-IN", "ta-IN", "te-IN"})
        for locale in native.AIM_COPY:
            row = self.by_cell[("aim990", locale)]
            self.assertEqual(row["app_id"], "6784974530")
            self.assertEqual(row["purchase_model"], "free_with_lifetime_unlock")
            self.assertIn("TOEIC", row["content"]["description"])
            self.assertNotRegex(row["content"]["description"], r"Listening|Reading|Unlock your potential|score improvement")
            self.assertNotIn("English exam", row["content"]["keywords"])
            self.assertGreater(gate.native_ratio(row["content"]["keywords"], locale), 0.95)

    def test_bopomofo_keywords_are_native_in_all_ten_markets(self):
        for locale in EXPECTED_LOCALES:
            row = self.by_cell[("lumibopomofo", locale)]
            self.assertEqual(row["app_id"], "6773017109")
            self.assertEqual(row["content"]["keywords"], native.BOPOMOFO_KEYWORDS[locale])
            self.assertNotRegex(row["content"]["keywords"], r"[A-Za-z]")
            self.assertNotIn("注音", row["content"]["description"])

    def test_pro_hindi_is_paid_upfront_and_has_no_english_edition_paragraph(self):
        for key, app_id in (
            ("lumiletterspro", "6778491147"), ("lumibopomofopro", "6775773117"),
            ("lumimissionpro", "6779745474"),
        ):
            row = self.by_cell[(key, "hi")]
            self.assertEqual(row["app_id"], app_id)
            self.assertEqual(row["purchase_model"], "paid_upfront")
            self.assertIn("Pro", row["content"]["name"])
            self.assertNotRegex(row["content"]["description"], r"Pro edition|मुफ़्त आज़माएँ|मुफ्त आजमाएँ")
            self.assertIn("डाउनलोड", row["content"]["description"])
            self.assertNotRegex(row["content"]["keywords"], r"[\u3400-\u9fff]")
        self.assertIn("मुफ़्त परीक्षण नहीं", self.by_cell[("lumimissionpro", "hi")]["content"]["description"])

    def test_kannada_never_contains_chinese_or_other_indic_script(self):
        for row in (row for row in self.rows if row["locale"] == "kn-IN"):
            for field in native.FIELDS:
                self.assertFalse(gate.foreign_letters(row["content"][field], "kn-IN"), (row["app_key"], field))
                self.assertNotRegex(row["content"][field], r"[\u3400-\u9fff]")
        self.assertIn("ದುಡುಕಿನ ಖರೀದಿ", self.by_cell[("hourstag", "kn-IN")]["content"]["description"])
        self.assertIn("ಸಾಂಪ್ರದಾಯಿಕ ಚೀನೀ", self.by_cell[("lumimathpro", "kn-IN")]["content"]["description"])

    def test_odia_replaces_actual_bad_tokens_not_valid_halants(self):
        text = self.by_cell[("tripplanet", "or-IN")]["content"]["description"]
        self.assertIn("Trip Planet: Kids Quest", text)
        self.assertIn("ଦ୍ୱାରା", text)
        self.assertIn("ମିଶନ୍", text)
        self.assertIn("ପ୍ୟାକ୍", text)
        self.assertNotRegex(text, r"\b(?:SA|ads|third|external|venture|ONCE|OF)\b")
        self.assertEqual(gate.shaping_issues(text, "or-IN"), [])
        with self.assertRaises(ValueError):
            gate.validate("ଡିଜାଇନ୍ ଦ୍ SA ାରା ସୁରକ୍ଷିତ", "or-IN")

    def test_normal_virama_danda_joiners_and_loanwords_are_not_modified(self):
        for locale, value in (
            ("bn-BD", "অফলাইন।"), ("gu-IN", "અભ્યાસ।"),
            ("hi", "अभ्यास।"), ("kn-IN", "ಸ್ಕ್ಯಾನ್।"),
            ("ml-IN", "ഓഫ്‌ലൈൻ।"), ("mr-IN", "अभ्यास।"),
            ("or-IN", "ୱିଜେଟ୍ ଅଫ୍‌ଲାଇନ୍।"), ("pa-IN", "ਅਭਿਆਸ।"),
            ("ta-IN", "பிரிண்ட்।"), ("te-IN", "ట్రాకర్।"),
        ):
            snapshot = value.encode()
            gate.validate(value, locale)
            self.assertEqual(value.encode(), snapshot)
            self.assertEqual(gate.shaping_issues(value, locale), [])

    def test_tamil_worksheet_and_routine_copy_have_no_foreign_tokens(self):
        letters = self.by_cell[("lumiletterspro", "ta-IN")]["content"]["description"]
        mission = self.by_cell[("lumimission", "ta-IN")]["content"]["description"]
        self.assertIn("இன்றைய பணித்தாள்", letters)
        self.assertNotIn("पत्र", letters)
        self.assertIn("கூடையில்", mission)
        self.assertNotIn("корз", mission)
        math = self.by_cell[("lumimath", "ta-IN")]["content"]["promotionalText"]
        self.assertIn("மாண்டிசோரி", math)
        self.assertNotIn("\u0d3f", math)

    def test_identity_and_purchase_drift_fail_closed(self):
        source = pages.external_localized_values("lumimissionpro", "hi")
        for app_id, purchase_model in (("1234567890", "paid_upfront"), ("6779745474", "free_with_lifetime_unlock")):
            with self.assertRaises(ValueError):
                native.reviewed_values("lumimissionpro", "hi", source, app_id=app_id, purchase_model=purchase_model)
        sample = {"description": "മാറ്റമില്ല"}
        self.assertEqual(native.reviewed_values("unknown", "ja", sample, app_id=None, purchase_model=None), sample)

    def test_candidate_bn_bd_has_zero_url_cta_qr_facts_and_full_evidence(self):
        rows = [row for row in self.rows if row["locale"] == "bn-BD"]
        self.assertEqual(len(rows), 47)
        for row in rows:
            assert_blocked_record(self, row, ("app_store_url",))
            source = (self.output / row["locale"] / f"{row['app_key']}.html").read_text()
            assert_blocked_page(self, source)
            self.assertNotIn('"offers"', source)
            self.assertNotIn('"aggregateRating"', source)
            self.assertIn(native.DISCLOSURES["bn-BD"], "".join(Visible(source).text))

    def test_all_other_423_candidates_have_exact_india_identity_and_attribution(self):
        checked = 0
        for row in self.rows:
            if row["locale"] == "bn-BD":
                continue
            source = (self.output / row["locale"] / f"{row['app_key']}.html").read_text()
            links = [link for link in Visible(source).links if "apps.apple.com" in link]
            self.assertTrue(links)
            for link in links:
                parsed = urlsplit(link)
                self.assertEqual(parsed.netloc, "apps.apple.com")
                self.assertEqual(parsed.path, f"/in/app/id{row['app_id']}")
                pairs = parse_qsl(parsed.query)
                self.assertEqual([key for key, _ in pairs], ["pt", "ct", "mt"])
                self.assertEqual(pairs[0][1], "118326163")
                self.assertEqual(pairs[-1][1], "8")
                self.assertLessEqual(len(pairs[1][1]), 30)
                self.assertEqual(link, row["app_store_url"])
            checked += 1
        self.assertEqual(checked, 423)

    def test_every_candidate_is_first_party_and_never_a_social_receipt(self):
        for row in self.rows:
            self.assertEqual(row["publication_state"], "unpublished_candidate")
            self.assertIsNone(row["social_receipt"])
            self.assertEqual(row["publisher_disclosure"], native.DISCLOSURES[row["locale"]])
            source = (self.output / row["locale"] / f"{row['app_key']}.html").read_text()
            self.assertIn(row["publisher_disclosure"], "".join(Visible(source).text))
            self.assertEqual(row["purchase_model"], self.apps[row["app_key"]]["purchase_model"])
            self.assertEqual(row["one_time_option"], self.apps[row["app_key"]]["one_time_option"])

    def test_new_copy_has_no_fixed_unlock_prices_or_score_promises(self):
        values = [value for fields in native.AIM_COPY.values() for value in fields.values()]
        values += list(native.DESCRIPTIONS.values()) + list(native.KEYWORDS.values()) + list(native.DISCLOSURES.values())
        for value in values:
            self.assertNotRegex(value, r"(?:[$₹৳]|USD|INR)\s*[0-9]")
            self.assertNotRegex(value, r"guaranteed|guarantee(?:d)? score|990 points|competitor test results")

    def test_read_only_gate_rejects_independent_negative_counterexamples(self):
        for text, locale in (
            ("ಪಠ್ಯ 冲动", "kn-IN"), ("பணிப்பत्रம்", "ta-IN"),
            ("ಕ\u0bbe", "kn-IN"),
            ("ମୁଖ୍ୟ \u25cc", "or-IN"), ("\u0b3e", "or-IN"),
            ("Pro edition includes the full calm ABC journey", "hi"),
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                gate.validate(text, locale)
        with self.assertRaises(ValueError):
            gate.validate("मुफ़्त आज़माएँ, एक बार अनलॉक करें", "hi", purchase_model="paid_upfront")
        gate.validate("मुफ़्त परीक्षण नहीं है। विज्ञापन रहित।", "hi", purchase_model="paid_upfront")

    def test_candidate_stage_and_source_hook_are_idempotent(self):
        for cell in native.TARGET_CELLS:
            key, locale = cell
            value = pages.external_localized_values(key, locale)
            self.assertEqual(
                value,
                native.reviewed_values(key, locale, value, app_id=pages.APPSTORE[key], purchase_model=pages.APPS[key]["purchase_model"]),
            )
            source = (self.output / locale / f"{key}.html").read_text()
            rendered, _ = candidates.finalize_page(source, key, locale, self.availability)
            self.assertEqual(source, rendered)

    def test_output_guards_protect_metadata_and_existing_guide(self):
        for target in (self.pages, Path(pages.DATA), self.output):
            with self.subTest(target=target), self.assertRaises(ValueError):
                candidates.generate(self.pages, target)

    def test_market_and_identity_failures_cannot_fall_back_to_another_country(self):
        app_id = "6784974530"
        self.assertIsNone(candidates.destination(app_id, "bn-BD", self.availability, "bn-BD/aim990.html"))
        for locale in EXPECTED_LOCALES[1:]:
            with self.subTest(locale=locale), self.assertRaises(ValueError):
                candidates.destination(app_id, locale, {}, f"{locale}/aim990.html")
        with self.assertRaises(ValueError):
            candidates.destination(app_id, "gu", self.availability, "gu/aim990.html")
        wrong = '<html><body><main><a href="https://apps.apple.com/in/app/id1234567890">Get</a></main></body></html>'
        with self.assertRaises(ValueError):
            candidates.finalize_page(wrong, "aim990", "gu-IN", self.availability)


if __name__ == "__main__":
    unittest.main()
