#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bn-BD 市場可用性契約測試(全離線,不連網)。

這些是 2026-09-12 以 Apple 一手證據定下的界線。任何人想「讓 bn-BD 也有連結」,
都會在這裡失敗,而不是靜悄悄把孟加拉讀者送進美國商店。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, GEO / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover
        raise unittest.SkipTest(f"{name}.py 不在此 checkout")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


market = _load("market_availability")
APP_ID = "6785004775"
FIFTY = [f"l{i}" for i in range(50)]


class EvidenceTest(unittest.TestCase):
    def test_bn_bd_is_recorded_unavailable_with_country_level_reason(self) -> None:
        self.assertTrue(market.is_unavailable("bn-BD"))
        self.assertEqual(market.market_state("bn-BD"),
                         market.MARKET_UNAVAILABLE_OR_UNVERIFIED)
        self.assertEqual(market.unavailable_reason("bn-BD"),
                         market.REASON_NOT_IN_APPLE_MEDIA_SERVICES)

    def test_evidence_names_every_independent_source(self) -> None:
        evidence = market.market_evidence("bn-BD")["evidence"]
        for needle in ("support.apple.com/en-us/118205", "resultCount=0",
                       "WhatsApp", "search", "HTTP 400", "/bd/", "/us/"):
            with self.subTest(needle):
                self.assertIn(needle, evidence)

    def test_evidence_is_dated(self) -> None:
        self.assertEqual(market.market_evidence("bn-BD")["observed_at"], "2026-09-12")

    def test_three_states_are_distinct(self) -> None:
        reasons = {market.REASON_NOT_IN_APPLE_MEDIA_SERVICES,
                   market.REASON_APP_NOT_SOLD,
                   market.REASON_LOOKUP_UNSUPPORTED}
        self.assertEqual(len(reasons), 3, "國家層級/App 層級/端點層級不可混為一談")


class NoSubstitutionTest(unittest.TestCase):
    def test_url_is_none_even_if_a_storefront_is_declared(self) -> None:
        """就算對照表宣告了 bd,也不得產生連結 —— 那個 storefront 不存在。"""
        self.assertIsNone(market.canonical_app_store_url_for(APP_ID, "bn-BD", "bd"))

    def test_never_falls_back_to_us(self) -> None:
        url = market.canonical_app_store_url_for(APP_ID, "bn-BD", "us")
        self.assertIsNone(url, "bn-BD 絕不可被導向美國商店")

    def test_never_falls_back_to_india(self) -> None:
        url = market.canonical_app_store_url_for(APP_ID, "bn-BD", "in")
        self.assertIsNone(url, "bn-BD 絕不可被導向印度商店")

    def test_never_falls_back_to_countryless(self) -> None:
        """countryless 也是 301 到 /us/,且沒有 Apple 一手證據能證明對 BD 使用者正確。"""
        url = market.canonical_app_store_url_for(APP_ID, "bn-BD", None)
        self.assertIsNone(url)

    def test_forbidden_substitutions_are_declared(self) -> None:
        self.assertEqual(set(market.FORBIDDEN_SUBSTITUTIONS), {"us", "in", "countryless"})

    def test_available_locale_still_gets_its_storefront_url(self) -> None:
        url = market.canonical_app_store_url_for(APP_ID, "ja", "jp")
        self.assertEqual(url, f"https://apps.apple.com/jp/app/id{APP_ID}")


class CtaTest(unittest.TestCase):
    def test_bn_bd_cta_is_null_and_not_renderable(self) -> None:
        cta = market.cta_for(APP_ID, "bn-BD", "bd")
        self.assertIsNone(cta["url"])
        self.assertFalse(cta["renderable_link"])
        self.assertEqual(cta["state"], market.MARKET_UNAVAILABLE_OR_UNVERIFIED)
        self.assertEqual(cta["reason"], market.REASON_NOT_IN_APPLE_MEDIA_SERVICES)

    def test_available_locale_cta_is_renderable(self) -> None:
        cta = market.cta_for(APP_ID, "de-DE", "de")
        self.assertTrue(cta["renderable_link"])
        self.assertIsNotNone(cta["url"])
        self.assertIsNone(cta["reason"])

    def test_cta_never_returns_a_us_or_in_url_for_bn_bd(self) -> None:
        for storefront in ("us", "in", "bd", None):
            with self.subTest(storefront=storefront):
                url = market.cta_for(APP_ID, "bn-BD", storefront)["url"]
                self.assertIsNone(url)


class ContentAndFactsTest(unittest.TestCase):
    def test_content_is_retained_for_unavailable_market(self) -> None:
        cell = market.distribution_cell(APP_ID, "bn-BD", "bd")
        self.assertTrue(cell["content_retained"], "內容不得因市場問題被刪")
        self.assertFalse(cell["publishable"])
        self.assertEqual(cell["value"], "N/A")
        self.assertEqual(cell["blocked_reason"], market.REASON_NOT_IN_APPLE_MEDIA_SERVICES)

    def test_facts_are_not_allowed_without_a_verifiable_market(self) -> None:
        self.assertFalse(market.distribution_cell(APP_ID, "bn-BD", "bd")["facts_allowed"])

    def test_facts_allowed_where_market_is_verifiable(self) -> None:
        self.assertTrue(market.distribution_cell(APP_ID, "ja", "jp")["facts_allowed"])

    def test_blocked_cell_always_states_a_reason(self) -> None:
        cell = market.distribution_cell(APP_ID, "bn-BD", "bd")
        self.assertTrue(str(cell["blocked_reason"]).strip())


class DenominatorAndCoverageTest(unittest.TestCase):
    def test_publisher_denominator_excludes_only_unavailable_locales(self) -> None:
        locales = FIFTY[:49] + ["bn-BD"]
        publishable = market.publishable_locales(locales)
        self.assertEqual(len(publishable), 49)
        self.assertNotIn("bn-BD", publishable)

    def test_locale_set_itself_is_unchanged(self) -> None:
        """50 locale 的內容覆蓋不縮減 —— 只有發佈分母變 49。"""
        locales = FIFTY[:49] + ["bn-BD"]
        self.assertEqual(len(locales), 50)
        retained = [l for l in locales
                    if market.distribution_cell(APP_ID, l, "xx")["content_retained"]]
        self.assertEqual(len(retained), 50)

    def test_other_locales_are_untouched(self) -> None:
        for locale in ("ja", "de-DE", "ar-SA", "zh-Hant", "hi"):
            with self.subTest(locale):
                self.assertFalse(market.is_unavailable(locale))

    def test_only_evidence_backed_locales_are_listed(self) -> None:
        for locale, entry in market.UNAVAILABLE_MARKETS.items():
            with self.subTest(locale):
                self.assertTrue(entry["evidence"].strip())
                self.assertTrue(entry["observed_at"].strip())
                self.assertIn(entry["reason"],
                              {market.REASON_NOT_IN_APPLE_MEDIA_SERVICES,
                               market.REASON_APP_NOT_SOLD,
                               market.REASON_LOOKUP_UNSUPPORTED})

    def test_all_47_apps_stay_addressable_in_bn_bd(self) -> None:
        """47 支 App 的 bn-BD 內容都還在,只是不可發佈。"""
        cells = [market.distribution_cell(str(i), "bn-BD", "bd") for i in range(47)]
        self.assertEqual(len(cells), 47)
        self.assertTrue(all(c["content_retained"] for c in cells))
        self.assertTrue(all(not c["publishable"] for c in cells))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
