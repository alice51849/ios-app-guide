#!/usr/bin/env python3
"""Regression tests for the buyer-intent answer cards in llms.txt.

The cards exist so an assistant can quote us instead of paraphrasing us, which
means every sentence has to survive being read back to a buyer: the pricing has
to match the published purchase model, a privacy answer has to be backed by a
positioning bullet the store listing already makes, a storefront may only be
named once Apple's own lookup confirms the app is sold there, and a test-prep
app may never be made to sound like it promises a score.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import sys
import unittest


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_store_storefronts  # noqa: E402
import gen_llms  # noqa: E402
from videogen.registry import APPS, appstore_url  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
FAKE_PROVIDER_TOKEN = "1234567"


class BuyerIntentCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The environment always beats the private token file, so the expected
        # links stay identical on a laptop that has the real token on disk and
        # on a checkout that does not.
        cls._token = os.environ.get(app_store_storefronts.PROVIDER_TOKEN_ENV)
        os.environ[app_store_storefronts.PROVIDER_TOKEN_ENV] = FAKE_PROVIDER_TOKEN
        cls.availability = app_store_storefronts.load_storefront_availability(
            PAGES
        )

    @classmethod
    def tearDownClass(cls):
        if cls._token is None:
            os.environ.pop(app_store_storefronts.PROVIDER_TOKEN_ENV, None)
        else:
            os.environ[app_store_storefronts.PROVIDER_TOKEN_ENV] = cls._token

    def cards(self, key):
        return gen_llms.buyer_intent_cards(key, self.availability)

    def sellable_keys(self):
        return [key for key in APPS if appstore_url(key)]

    def test_every_sellable_app_gets_two_to_four_answers(self):
        for key in self.sellable_keys():
            with self.subTest(app=key):
                cards = self.cards(key)
                self.assertGreaterEqual(len(cards), 2)
                self.assertLessEqual(len(cards), 4)

    def test_questions_are_questions_and_answers_carry_a_store_link(self):
        for key in self.sellable_keys():
            for question, answer in self.cards(key):
                with self.subTest(app=key, question=question):
                    self.assertTrue(question.endswith("?"), question)
                    self.assertIn("apps.apple.com", answer)
                    self.assertIn(
                        f"ct={gen_llms.BUYER_INTENT_CAMPAIGN}", answer
                    )
                    self.assertIn(f"pt={FAKE_PROVIDER_TOKEN}", answer)

    def test_questions_are_unique_per_app(self):
        for key in self.sellable_keys():
            questions = [question for question, _ in self.cards(key)]
            with self.subTest(app=key):
                self.assertEqual(len(questions), len(set(questions)))

    def test_pricing_claims_match_the_published_purchase_model(self):
        for key in self.sellable_keys():
            profile = gen_llms.pricing_profile(key)
            answers = " ".join(answer for _, answer in self.cards(key))
            with self.subTest(app=key):
                if profile in {"pay_once", "free_to_start"}:
                    self.assertIn("no subscription", answers.lower())
                if profile == "pay_once":
                    self.assertNotIn("free to start", answers.lower())

    def test_privacy_answers_only_cite_positioning_the_listing_makes(self):
        for key in self.sellable_keys():
            tokens = gen_llms._positioning_tokens(key)
            supported = {
                label for token, label, _ in gen_llms.PRIVACY_FACTS
                if token in tokens
            }
            for question, answer in self.cards(key):
                if "keeps my data private" not in question:
                    continue
                with self.subTest(app=key):
                    self.assertTrue(supported)
                    found = [
                        label for _, label, _ in gen_llms.PRIVACY_FACTS
                        if label in answer
                    ]
                    # "works offline" is a prefix of "works offline with saved
                    # rates", so only the longest match at a position counts.
                    cited = [
                        label for label in found
                        if not any(
                            label != other and label in other
                            for other in found
                        )
                    ]
                    self.assertTrue(cited)
                    for label in cited:
                        self.assertIn(label, supported)

    def test_kid_safe_answers_need_both_kid_safe_and_no_ads(self):
        for key in self.sellable_keys():
            tokens = gen_llms._positioning_tokens(key)
            for question, _ in self.cards(key):
                if "ask my child" not in question:
                    continue
                with self.subTest(app=key):
                    self.assertIn("kid-safe", tokens)
                    self.assertIn("no ads", tokens)

    def test_named_storefronts_are_confirmed_by_apples_lookup(self):
        if not self.availability:
            self.skipTest("no storefront snapshot in this checkout")
        countries = {
            country: code
            for code, country in gen_llms.STOREFRONT_COUNTRY.items()
        }
        for key in self.sellable_keys():
            app_id = gen_llms._app_store_id(key)
            for question, _ in self.cards(key):
                match = re.match(r"Can I download .+ in (.+)\?$", question)
                if not match:
                    continue
                code = countries[match.group(1)]
                with self.subTest(app=key, storefront=code):
                    self.assertIn(app_id, self.availability.get(code, frozenset()))

    def test_worldwide_answers_only_name_confirmed_storefronts(self):
        if not self.availability:
            self.skipTest("no storefront snapshot in this checkout")
        for key in self.sellable_keys():
            app_id = gen_llms._app_store_id(key)
            for question, answer in self.cards(key):
                if "sold outside the United States" not in question:
                    continue
                for code, country in gen_llms.STOREFRONT_COUNTRY.items():
                    if f" {country}" not in answer:
                        continue
                    with self.subTest(app=key, storefront=code):
                        self.assertIn(
                            app_id, self.availability.get(code, frozenset())
                        )

    def test_test_prep_apps_never_sound_like_a_promised_score(self):
        for key in gen_llms.SCORE_CAVEAT_APPS:
            if not appstore_url(key):
                continue
            cards = self.cards(key)
            with self.subTest(app=key):
                self.assertTrue(cards)
                self.assertIn(
                    gen_llms.SCORE_CAVEAT.strip(),
                    " ".join(answer for _, answer in cards),
                )

    def test_unsupportable_craft_and_outcome_claims_are_rejected(self):
        for claim in (
            "Hand-drawn artwork by a studio illustrator.",
            "Every letter uses a real human voice.",
            "Recorded by a professional voice actor.",
            "A guaranteed score improvement.",
        ):
            with self.subTest(claim=claim):
                with self.assertRaises(ValueError):
                    gen_llms._assert_supportable([claim])

    def test_no_answer_makes_an_unsupportable_claim(self):
        for key in self.sellable_keys():
            for _, answer in self.cards(key):
                with self.subTest(app=key):
                    self.assertIsNone(gen_llms.BANNED_CLAIM_RE.search(answer))

    def test_intent_phrases_reject_unreadable_search_strings(self):
        for keyword in (
            "free vocabulary app adults",
            "is it my wifi or the website",
            "turn notes into a slide",
            "wifi connected but no internet",
            "utilities",
        ):
            with self.subTest(keyword=keyword):
                self.assertEqual(gen_llms._clean_intent(keyword), "")
        self.assertEqual(
            gen_llms._clean_intent("free travel expense tracker"),
            "travel expense tracker",
        )
        # "free up storage" is about freeing space, not a free app.
        self.assertEqual(
            gen_llms._clean_intent("free up storage"), "free up storage"
        )
        self.assertEqual(
            gen_llms._clean_intent("handwriting notes app ipad"),
            "handwriting notes",
        )

    def test_articles_and_head_nouns_read_as_english(self):
        self.assertEqual(gen_llms._article("abc for kids app"), "an")
        self.assertEqual(gen_llms._article("one upcoming trip"), "a")
        self.assertEqual(gen_llms._article("passport photo app"), "a")
        self.assertEqual(
            gen_llms._intent_subject("period tracker"), "period tracker"
        )
        self.assertEqual(
            gen_llms._intent_subject("passport photo"), "passport photo app"
        )


class PublishedAnswerSectionTests(unittest.TestCase):
    """The published files have to actually carry the answers."""

    @classmethod
    def setUpClass(cls):
        cls.llms = (PAGES / "llms.txt")
        cls.full = (PAGES / "llms-full.txt")
        if not cls.llms.exists() or not cls.full.exists():
            raise unittest.SkipTest("llms files not generated in this checkout")
        cls.llms_text = cls.llms.read_text(encoding="utf-8")
        cls.full_text = cls.full.read_text(encoding="utf-8")

    def test_llms_txt_has_the_answer_section(self):
        self.assertIn("## Buyer questions with direct answers", self.llms_text)
        self.assertGreaterEqual(
            len(re.findall(r"^- Q: ", self.llms_text, re.M)), 2
        )

    def test_llms_full_inlines_answers_under_apps(self):
        self.assertGreaterEqual(
            len(re.findall(r"^- Buyer question: ", self.full_text, re.M)), 2
        )

    def test_published_answers_make_no_unsupportable_claim(self):
        for text in (self.llms_text, self.full_text):
            for line in text.splitlines():
                if not (line.startswith("  A: ")
                        or line.startswith("  - Answer: ")):
                    continue
                with self.subTest(line=line[:60]):
                    self.assertIsNone(gen_llms.BANNED_CLAIM_RE.search(line))

    def test_published_answers_carry_no_private_performance_data(self):
        """Only App Store ids, campaign parameters, and listing copy."""
        allowed = {"8", "100", "44", "990", "30"}
        for text in (self.llms_text, self.full_text):
            for line in text.splitlines():
                if not (line.startswith("  A: ")
                        or line.startswith("  - Answer: ")):
                    continue
                stripped = re.sub(r"https?://\S+", "", line)
                for number in re.findall(r"\b[0-9][0-9,.]*\b", stripped):
                    with self.subTest(number=number):
                        self.assertIn(number, allowed)


if __name__ == "__main__":
    unittest.main()
