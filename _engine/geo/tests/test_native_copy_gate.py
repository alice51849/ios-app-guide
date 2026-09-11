#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""母語外宣文案的閘門測試(Indic 10 語)。

守的是 2026-09-11 稽核抓到的三類真實缺陷:
* 整段英文 fallback 直接變成當地讀者看到的價值訴求(P0-3)。
* 機器翻譯把英文塞進母語詞中間,真機上渲染成破字(P0-6)。
* paid_upfront 的 App 在母語頁寫「免費試用」(P0-7)。

同時釘住「不可以誤判」的正確正字法:字尾 virama、danda、`स्क्रीन-फ्री`
這類複合詞,以及 `ଏକ iOS ଆପ୍` 這種正常的產品詞。
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))
SOCIAL = GEO.parent / "social"
if str(SOCIAL) not in sys.path:
    sys.path.insert(0, str(SOCIAL))

import native_copy_gate as gate  # noqa: E402
import build_pages_i18n as pages  # noqa: E402
from videogen.registry import APPS  # noqa: E402

PACK_PATH = GEO / "native_copy_packs" / "indic_native_copy.json"
WAIVER_PATH = GEO / "native_copy_waivers.json"


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class ScriptRatioTests(unittest.TestCase):
    def test_brand_links_and_hashtags_do_not_count_as_english(self):
        text = (
            "Aim990 https://apps.apple.com/in/app/id6784974530 #TOEIC "
            "தினமும் சிறு பயிற்சி"
        )
        ratio, _native, latin = gate.script_ratio(text, "ta-IN", brand="Aim990")
        self.assertEqual(0, latin)
        self.assertEqual(1.0, ratio)

    def test_whole_english_body_is_detected(self):
        text = (
            "Unlock your potential with Aim990! A comprehensive 30-day TOEIC "
            "study plan designed to boost your listening and reading skills."
        )
        ratio, _native, _latin = gate.script_ratio(text, "kn-IN", brand="Aim990")
        self.assertLess(ratio, gate.NATIVE_RATIO_FLOOR)


class ShapingFalsePositiveTests(unittest.TestCase):
    """這些全部是正確的寫法,任何一條被判為缺陷都代表閘門會誤改文案。"""

    CLEAN = [
        ("ta-IN", "உங்கள் குழந்தைகள் மகிழ்ச்சியுடன் கற்றுக்கொள்ளலாம்."),
        ("kn-IN", "ಆಫ್‌ಲೈನ್ ಸ್ಕ್ಯಾನ್ ಮತ್ತು ಪ್ರಿಂಟ್ ಬೆಂಬಲ."),
        ("te-IN", "ట్రాకర్ ప్రతిరోజూ మీ పురోగతిని చూపుతుంది."),
        ("or-IN", "ଏହା ଏକ iOS ଆପ୍। ୱିଜେଟ୍ ମଧ୍ୟ ଅଛି।"),
        ("hi", "यह ऐप स्क्रीन-फ्री समय बढ़ाता है।"),
        ("mr-IN", "impulse buying थांबवा. goals व खर्च एकाच ठिकाणी."),
        ("bn-BD", "অ্যাপটি সম্পূর্ণ বিজ্ঞাপনমুক্ত। কোনো সাইন-আপ নেই।"),
    ]

    def test_correct_orthography_is_never_flagged(self):
        for locale, text in self.CLEAN:
            with self.subTest(locale=locale, text=text):
                self.assertEqual([], gate.shaping_defects(text, locale))


class ShapingDefectTests(unittest.TestCase):
    def test_english_token_inside_native_word(self):
        defects = gate.shaping_defects("ଟ୍ରିପ୍ ପ୍ଲାନେଟ୍‌ରେ କ ads ଣସି ବିଜ୍ଞାପନ ନାହିଁ", "or-IN")
        self.assertTrue(any(d.startswith("latin_inside_word") for d in defects), defects)

    def test_broken_conjunct_with_orphan_matra(self):
        defects = gate.shaping_defects("ଡିଜାଇନ୍ ଦ୍ SA ାରା ସୁରକ୍ଷିତ", "or-IN")
        self.assertTrue(any(d.startswith("orphan_combining_mark") for d in defects), defects)
        self.assertTrue(any(d.startswith("latin_inside_word") for d in defects), defects)

    def test_foreign_indic_script_mixed_into_tamil(self):
        defects = gate.shaping_defects('புதிய "இன்றைய பணிப்பत्रம்" PDF', "ta-IN")
        self.assertIn("foreign_script:Devanagari", defects)

    def test_danda_shared_across_scripts_is_not_foreign(self):
        self.assertEqual([], gate.shaping_defects("ଏହା ଏକ ପରୀକ୍ଷା ଅଟେ।", "or-IN"))

    def test_dotted_circle_is_a_defect(self):
        self.assertIn("dotted_circle", gate.shaping_defects("क\u25ccि", "hi"))


class PurchaseModelTests(unittest.TestCase):
    def test_paid_upfront_must_not_promise_a_free_trial(self):
        hard, _soft = gate.purchase_model_defects(
            "• मुफ़्त आज़माएँ, एक बार अनलॉक करें", "hi", "paid_upfront"
        )
        self.assertTrue(hard)

    def test_screen_free_compound_is_not_a_price_claim(self):
        hard, _soft = gate.purchase_model_defects(
            "बच्चों के लिए स्क्रीन-फ्री समय बढ़ाएँ", "hi", "paid_upfront"
        )
        self.assertEqual([], hard)

    def test_negated_free_wording_is_not_a_price_claim(self):
        hard, _soft = gate.purchase_model_defects(
            "இது இலவசம் இல்லை; ஒரு முறை மட்டும் பணம் செலுத்துங்கள்.",
            "ta-IN",
            "paid_upfront",
        )
        self.assertEqual([], hard)

    def test_free_to_start_copy_should_say_so(self):
        _hard, soft = gate.purchase_model_defects(
            "30 ದಿನಗಳ ಯೋಜನೆ.", "kn-IN", "free_with_lifetime_unlock",
            require_free_signal=True,
        )
        self.assertIn("free_to_start_without_free_signal", soft)


class PriceLiteralTests(unittest.TestCase):
    def test_currency_amounts_are_detected(self):
        for text in ("₹599 में खरीदें", "Rs. 599", "$4.99 one-time"):
            with self.subTest(text=text):
                self.assertTrue(gate.price_literal_defects(text))

    def test_plain_numbers_are_not_price_literals(self):
        self.assertEqual([], gate.price_literal_defects("30 நாள் திட்டம், 37 நண்பர்கள்"))


class NativeCopyPackTests(unittest.TestCase):
    """文案包本身就是 source of truth,必須自己先過閘門。"""

    @classmethod
    def setUpClass(cls):
        cls.pack = _load(PACK_PATH)

    def test_only_official_indic_locales(self):
        for app, locales in self.pack["apps"].items():
            for locale in locales:
                with self.subTest(app=app, locale=locale):
                    self.assertIn(locale, gate.INDIC_LOCALES)

    def test_apps_exist_in_the_registry(self):
        for app in self.pack["apps"]:
            with self.subTest(app=app):
                self.assertIn(app, APPS)

    def test_every_pack_string_is_native_clean_and_priceless(self):
        for app, locales in sorted(self.pack["apps"].items()):
            brand = APPS[app].get("name") or app
            model = APPS[app].get("purchase_model") or ""
            for locale, surfaces in sorted(locales.items()):
                for surface, fields in sorted(surfaces.items()):
                    for field, text in sorted(fields.items()):
                        with self.subTest(app=app, locale=locale, field=field):
                            verdict = gate.evaluate(
                                text,
                                locale,
                                brand=brand,
                                purchase_model=model if field != "keywords" else "",
                                check_price_literals=True,
                            )
                            self.assertEqual([], verdict["failures"], f"{surface}/{field}")

    def test_pack_is_wired_into_the_page_overrides(self):
        import external_app_locales

        for app, locales in self.pack["apps"].items():
            for locale, surfaces in locales.items():
                for field, text in (surfaces.get("geo") or {}).items():
                    with self.subTest(app=app, locale=locale, field=field):
                        self.assertEqual(
                            text,
                            external_app_locales.EXTERNAL_APP_LOCALE_OVERRIDES
                            [app][locale][field],
                        )


class IndicMatrixTests(unittest.TestCase):
    """每一支 App × 10 個 Indic locale 的組裝文案都要是母語且沒有破字。"""

    @classmethod
    def setUpClass(cls):
        cls.waivers = _load(WAIVER_PATH)
        cls.waived = {
            (cell["app"], cell["locale"]) for cell in cls.waivers["cells"]
        }
        cls.verdicts = {}
        for key in sorted(APPS):
            try:
                localizations = pages.load_app_locales(key)
            except Exception:  # 沒有策展資料的 App 不在這個矩陣裡
                continue
            model = APPS[key].get("purchase_model") or ""
            for locale in gate.INDIC_LOCALES:
                if locale not in localizations:
                    continue
                try:
                    values = pages.external_localized_values(key, locale, localizations)
                except ValueError as error:
                    cls.verdicts[(key, locale)] = {
                        "ok": False,
                        "failures": [f"build_error:{error}"],
                        "ratio": 0.0,
                    }
                    continue
                name, subtitle, description, keywords = pages._meta_from(
                    values, APPS[key]
                )
                description = pages.sanitize_description(key, locale, description)
                chips = pages.native_first_keywords(keywords, locale)[:8]
                assembled = "\n".join(
                    [subtitle, description, *chips, pages.pricing_text_for(key, locale)]
                )
                cls.verdicts[(key, locale)] = gate.evaluate(
                    assembled, locale, brand=name, purchase_model=model
                )

    def test_matrix_is_not_empty(self):
        self.assertGreaterEqual(len(self.verdicts), 300)

    def test_scope_apps_are_fully_native(self):
        for app in ("aim990", "lumibopomofo", "lumiletterspro", "lumimissionpro",
                    "tripplanet"):
            for locale in gate.INDIC_LOCALES:
                verdict = self.verdicts.get((app, locale))
                if verdict is None:
                    continue
                with self.subTest(app=app, locale=locale):
                    self.assertEqual([], verdict["failures"])
                    self.assertGreaterEqual(verdict["ratio"], gate.NATIVE_RATIO_FLOOR)

    def test_no_unwaived_cell_fails(self):
        unexpected = {
            cell: verdict["failures"]
            for cell, verdict in self.verdicts.items()
            if not verdict["ok"] and cell not in self.waived
        }
        self.assertEqual({}, unexpected)

    def test_waiver_ledger_only_lists_cells_that_still_fail(self):
        """修好的 cell 必須從 ledger 移除,否則債務清單會永遠不縮。"""
        stale = [
            cell
            for cell in sorted(self.waived)
            if cell in self.verdicts and self.verdicts[cell]["ok"]
        ]
        self.assertEqual([], stale)

    def test_paid_upfront_pages_never_promise_free(self):
        for (app, locale), verdict in self.verdicts.items():
            if (APPS[app].get("purchase_model") or "") not in gate.PAID_UPFRONT_MODELS:
                continue
            with self.subTest(app=app, locale=locale):
                self.assertEqual(
                    [],
                    [f for f in verdict["failures"] if "implies_free" in f],
                )


class PricingTextTests(unittest.TestCase):
    def test_paid_upfront_pricing_sentence_never_hardcodes_a_price(self):
        for locale in gate.INDIC_LOCALES:
            with self.subTest(locale=locale):
                text = pages.pricing_text_for("lumimissionpro", locale)
                self.assertEqual([], gate.price_literal_defects(text))
                self.assertEqual(
                    [], gate.shaping_defects(text, locale)
                )
                hard, _soft = gate.purchase_model_defects(text, locale, "paid_upfront")
                self.assertEqual([], hard)


class KeywordOrderingTests(unittest.TestCase):
    def test_native_keywords_are_shown_first(self):
        keywords = ["zhuyin", "bopomofo", "चीनी सीखें", "उच्चारण"]
        self.assertEqual(
            ["चीनी सीखें", "उच्चारण", "zhuyin", "bopomofo"],
            pages.native_first_keywords(keywords, "hi"),
        )

    def test_latin_locales_keep_their_order(self):
        keywords = ["to do list", "checklist"]
        self.assertEqual(keywords, pages.native_first_keywords(keywords, "en-US"))


if __name__ == "__main__":
    unittest.main()
