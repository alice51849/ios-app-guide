"""Declared locale routing must not be replaced by lookup/cache fallbacks."""

import json
from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import app_store_storefronts as storefronts
from official_locales import OFFICIAL_LOCALE_SET


class StorefrontValidityTest(unittest.TestCase):
    def test_mapping_uses_authoritative_json(self):
        self.assertEqual(
            storefronts.LOCALE_STOREFRONTS,
            json.loads((GEO / "locale_storefronts.json").read_text()),
        )
        self.assertEqual(set(storefronts.LOCALE_STOREFRONTS), OFFICIAL_LOCALE_SET)

    def test_bengali_is_not_reassigned_to_india(self):
        self.assertEqual(storefronts.LOCALE_STOREFRONTS["bn-BD"], "bd")
        self.assertEqual(storefronts.FREE_LABELS["bn-BD"], "বিনামূল্যে")

    def test_bengali_keeps_declared_route_with_empty_or_india_cache(self):
        canonical = "https://apps.apple.com/app/id6798814385"
        expected = "https://apps.apple.com/bd/app/id6798814385"
        for availability in ({}, {"in": frozenset({"6798814385"})}):
            with self.subTest(availability=availability):
                self.assertEqual(
                    storefronts.verified_app_store_url(canonical, "bn-BD", availability),
                    expected,
                )
                self.assertEqual(
                    storefronts.validated_app_store_url(
                        expected, "6798814385", expected_locale="bn-BD",
                        availability=availability,
                    ),
                    expected,
                )

    def test_bengali_rejects_countryless_and_india_urls(self):
        for prefix in ("", "in/"):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                storefronts.validated_app_store_url(
                    f"https://apps.apple.com/{prefix}app/id6798814385",
                    expected_locale="bn-BD",
                )

    def test_other_markets_retain_verified_fallback_behavior(self):
        canonical = "https://apps.apple.com/app/id6798814385"
        self.assertEqual(storefronts.verified_app_store_url(canonical, "hi", {}), canonical)
        with self.assertRaises(ValueError):
            storefronts.validated_app_store_url(
                "https://apps.apple.com/in/app/id6798814385",
                expected_locale="hi", availability={},
            )

    def test_bare_indic_locales_are_not_product_locales(self):
        for locale in ("gu", "kn", "ml"):
            with self.subTest(locale=locale), self.assertRaises(ValueError):
                storefronts.localized_app_store_url(
                    "https://apps.apple.com/app/id6798814385", locale
                )
