#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

import answer_facts
import aeo_answers_i18n
import queries
from answer_personas import PERSONAS, persona_meta_description
from official_locales import OFFICIAL_LOCALES


CURRENT_LIVE_APPS = {
    "aim990",
    "aim990plus",
    "cvdesk",
    "cyca",
    "dailymate",
    "gmoney",
    "hourstag",
    "lockhour",
    "lumibopomofo",
    "lumibopomofopro",
    "lumiletters",
    "lumiletterspro",
    "lumimath",
    "lumimathpro",
    "lumimission",
    "lumimissionpro",
    "lumiweather",
    "maskmyfile",
    "mochi",
    "mochidonestamp",
    "photocream",
    "picclear",
    "scanto",
    "sereno",
    "snapport",
    "sononote",
    "tripbee",
    "tripbeelite",
    "tripplanet",
    "unblurry",
    "wifiaid",
    "wordmate",
}


class PersonaLocaleCoverageTests(unittest.TestCase):
    def test_every_live_app_has_a_persona_workflow(self):
        self.assertEqual(CURRENT_LIVE_APPS, set(PERSONAS))
        self.assertTrue(all(PERSONAS[key] for key in CURRENT_LIVE_APPS))

    def test_shared_persona_query_stays_with_its_free_app(self):
        query = PERSONAS["lumimission"][0]["query"]
        selected = {"lumimission", "lumimissionpro"}
        self.assertTrue(
            queries.is_inherited_query(
                "lumimissionpro",
                query,
                selected,
            )
        )
        self.assertFalse(
            queries.is_inherited_query(
                "lumimission",
                query,
                selected,
            )
        )
        self.assertFalse(
            queries.is_inherited_query(
                "lumimissionpro",
                query,
                {"lumimissionpro"},
            )
        )

    def test_social_media_query_does_not_trigger_oci_passport_facts(self):
        query = PERSONAS["lockhour"][0]["query"]
        self.assertIsNone(answer_facts._detect_passport(query))
        for alias, expected in answer_facts._COUNTRY_ALIASES.items():
            self.assertEqual(
                expected,
                answer_facts._detect_passport(
                    f"{alias.strip()} passport photo requirements"
                ),
                alias,
            )
        facts = answer_facts.topic_facts(
            query,
            "lockhour",
            {"name": "LockHour Pro", "cta_bullets": []},
        )
        self.assertIsNotNone(facts)
        self.assertIn("social media", str(facts).lower())
        self.assertNotIn("passport", str(facts).lower())

    def test_answer_localizer_covers_all_official_locales(self):
        self.assertEqual(50, len(aeo_answers_i18n.ALL_LANGS))
        self.assertEqual(
            set(OFFICIAL_LOCALES),
            set(aeo_answers_i18n.ALL_LANGS),
        )

    def test_answer_discovery_only_targets_requested_locales(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers"
            answers.mkdir()
            for slug in ("missing-french", "missing-japanese"):
                (answers / f"{slug}.html").write_text(
                    "<html><body>Guide</body></html>",
                    encoding="utf-8",
                )
            french = root / "fr-FR" / "answers"
            french.mkdir(parents=True)
            (french / "missing-japanese.html").write_text(
                "localized",
                encoding="utf-8",
            )
            japanese = root / "ja" / "answers"
            japanese.mkdir(parents=True)
            (japanese / "missing-french.html").write_text(
                "localized",
                encoding="utf-8",
            )

            with (
                patch.object(aeo_answers_i18n, "ROOT", root),
                patch.object(aeo_answers_i18n, "ANSWERS", answers),
            ):
                self.assertEqual(
                    ["missing-french"],
                    aeo_answers_i18n.discover_slugs(
                        langs=["fr-FR"],
                    ),
                )
                self.assertEqual(
                    ["missing-japanese"],
                    aeo_answers_i18n.discover_slugs(
                        langs=["ja"],
                    ),
                )

    def test_curated_discovery_prioritizes_pages_that_can_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers"
            answers.mkdir()
            (answers / "blocked.html").write_text(
                "<html><body><h1>Blocked</h1></body></html>",
                encoding="utf-8",
            )
            (answers / "ready.html").write_text(
                "<html><body><h1>Ready</h1></body></html>",
                encoding="utf-8",
            )

            with (
                patch.object(aeo_answers_i18n, "ROOT", root),
                patch.object(aeo_answers_i18n, "ANSWERS", answers),
            ):
                self.assertEqual(
                    ["ready", "blocked"],
                    aeo_answers_i18n.prioritize_translatable_slugs(
                        ["blocked", "ready"],
                        ["fr-FR"],
                        {"fr-FR": {"Ready": "Prêt"}},
                    ),
                )

    def test_curated_main_prioritizes_progress_before_applying_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers"
            answers.mkdir()
            (answers / "blocked.html").write_text(
                "<html><body><h1>Blocked</h1></body></html>",
                encoding="utf-8",
            )
            (answers / "ready.html").write_text(
                "<html><body><h1>Ready</h1></body></html>",
                encoding="utf-8",
            )
            translations = root / "translations"
            translations.mkdir()
            (translations / "fr-FR.json").write_text(
                '{"Ready": "Prêt"}',
                encoding="utf-8",
            )
            argv = [
                "aeo_answers_i18n.py",
                "--langs",
                "fr-FR",
                "--trans",
                str(translations),
                "--limit",
                "1",
                "--defer-shared-refresh",
            ]

            with (
                patch.object(aeo_answers_i18n, "ROOT", root),
                patch.object(aeo_answers_i18n, "ANSWERS", answers),
                patch.object(sys, "argv", argv),
            ):
                self.assertEqual(0, aeo_answers_i18n.main())

            localized = root / "fr-FR" / "answers"
            self.assertTrue((localized / "ready.html").exists())
            self.assertFalse((localized / "blocked.html").exists())

    def test_translation_mapping_must_be_complete(self):
        with self.assertRaisesRegex(ValueError, "missing=1"):
            aeo_answers_i18n.require_complete_mapping(
                ["translated", "missing"],
                {"translated": "traduit"},
                "example",
                "fr-CA",
            )

    def test_translation_quality_rejects_long_english_fallback(self):
        source = "Lumi Mission Planet Pro app guide"
        with self.assertRaisesRegex(ValueError, "English fallback"):
            aeo_answers_i18n.require_translation_quality(
                [source],
                {source: source},
                "example",
                "da",
            )

    def test_translation_quality_rejects_native_script_code_switching(self):
        source = "Best vocabulary app for busy commuters"
        with self.assertRaisesRegex(ValueError, "native-script ratio"):
            aeo_answers_i18n.require_translation_quality(
                [source],
                {source: "busy commuters ਲਈ vocabulary app"},
                "example",
                "pa-IN",
            )

    def test_translation_quality_accepts_native_script_copy(self):
        source = "Best vocabulary app for busy commuters"
        aeo_answers_i18n.require_translation_quality(
            [source],
            {source: "ਰੁੱਝੇ ਯਾਤਰੀਆਂ ਲਈ ਸਭ ਤੋਂ ਵਧੀਆ ਸ਼ਬਦਾਵਲੀ ਐਪ"},
            "example",
            "pa-IN",
        )

    def test_reviewed_locale_override_replaces_model_copy(self):
        source, reviewed = next(
            iter(aeo_answers_i18n.LOCALE_TEXT_OVERRIDES["ro"].items())
        )
        self.assertEqual(
            {source: reviewed},
            aeo_answers_i18n.apply_locale_text_overrides(
                {source: "unreviewed"},
                "ro",
            ),
        )

    def test_publisher_brand_is_never_translated(self):
        self.assertEqual(
            {"Lumi Studio": "Lumi Studio"},
            aeo_answers_i18n.apply_locale_text_overrides(
                {"Lumi Studio": "露米工作室"},
                "zh-Hant",
            ),
        )

    def test_unblurry_personas_do_not_claim_to_recreate_missing_detail(self):
        copy = str(PERSONAS["unblurry"]).lower()
        for claim in (
            "recover detail",
            "rebuild real detail",
            "add genuine detail",
        ):
            self.assertNotIn(claim, copy)
        self.assertIn("doesn't invent detail", copy)

    def test_mochi_done_stamp_persona_is_not_a_todo_list(self):
        copy = str(PERSONAS["mochidonestamp"]).lower()
        self.assertIn("life-event memory", copy)
        self.assertIn("actual completion", copy)
        self.assertIn("one lifetime pro purchase", copy)
        self.assertNotIn("project management", copy)

    def test_reviewed_tripbee_subtitle_overrides_translate_generic_copy(self):
        source = "TripBee Pro: Trip Planner"
        for locale in (
            "el",
            "id",
            "ja",
            "ml-IN",
            "mr-IN",
            "or-IN",
            "pa-IN",
            "th",
            "ur-PK",
        ):
            translated = aeo_answers_i18n.apply_locale_text_overrides(
                {source: source},
                locale,
            )[source]
            self.assertTrue(translated.startswith("TripBee Pro: "))
            self.assertNotEqual(source, translated)

    def test_reviewed_target_terms_avoid_tracking_and_regional_spanish(self):
        self.assertEqual(
            "skriveøving",
            aeo_answers_i18n.apply_locale_target_replacements(
                "streksporing",
                "no",
            ),
        )

    def test_reviewed_asian_terms_remove_non_brand_english(self):
        cases = (
            ("id", "Prompt tanpa watermark dan light leak", "Petunjuk tanpa tanda air dan kebocoran cahaya"),
            ("ms", "Pencipta travel tanpa watermark", "Pencipta kandungan pelancongan tanpa tanda air"),
            ("vi", "Widget offline tanpa watermark", "Tiện ích ngoại tuyến tanpa hình mờ"),
            ("zh-Hant", "最佳旅遊應用", "最佳旅遊App"),
            ("zh-Hant", "最佳旅遊應用程式", "最佳旅遊應用程式"),
        )
        for locale, source, expected in cases:
            self.assertEqual(
                expected,
                aeo_answers_i18n.apply_locale_target_replacements(
                    source,
                    locale,
                ),
            )

    def test_reviewed_asian_replacements_are_complete_and_idempotent(self):
        cases = (
            (
                "zh-Hans",
                "在无数据国家离线可用；无推送你使用云账户；Home Screen",
                "在无移动数据的国家也能离线可用；也不会迫使你注册云账户；主屏幕",
            ),
            (
                "zh-Hant",
                "身份證保存在裝置內；Home Screen 小工具；提前退出；無數據；每日計劃",
                "身分證儲存在裝置內；主畫面小工具；提前結束；沒有網路；每日計畫",
            ),
            (
                "id",
                "Pelacakan goresan melalui pelacakan dan permainan; Widget Home "
                "Screen; white noise; timer; unlock",
                "Menebalkan goresan melalui menelusuri dan permainan; Widget "
                "Layar Utama; derau putih; pengatur waktu; buka kunci",
            ),
            (
                "ms",
                "ubah peluru anda; gambar letusan; mata wang rumah; Widget",
                "ubah butiran anda; gambar rentetan; mata wang negara asal; Widjet",
            ),
            (
                "th",
                "แอป Zhuyin และเรียน Zhuyin; ลองใช้ Auto Clear แล้วตามด้วย Sharpen",
                "แอปจู้ยิน (Zhuyin) และเรียนจู้ยิน (Zhuyin); "
                "ลองใช้ล้างภาพอัตโนมัติ (Auto Clear) แล้วตามด้วยเพิ่มความคมชัด "
                "(Sharpen)",
            ),
            (
                "vi",
                "Theo dõi nét; phonics; checklist; cabin",
                "Tô nét chữ; đánh vần; danh sách kiểm tra; nhà gỗ",
            ),
        )
        for locale, source, expected in cases:
            replaced = aeo_answers_i18n.apply_locale_target_replacements(
                source,
                locale,
            )
            self.assertEqual(expected, replaced)
            self.assertEqual(
                replaced,
                aeo_answers_i18n.apply_locale_target_replacements(
                    replaced,
                    locale,
                ),
            )

    def test_japanese_publisher_notice_identifies_the_app_developer(self):
        source = (
            "Publisher-authored guide from Lumi Studio, the app developer. App "
            "names are trademarks of their owners and are used only for "
            "identification. For documents, health, school, and productivity "
            "decisions, verify official requirements where relevant."
        )
        self.assertIn(
            "アプリ開発者",
            aeo_answers_i18n.LOCALE_TEXT_OVERRIDES["ja"][source],
        )

    def test_japanese_tripbee_override_preserves_itinerary_categories(self):
        source, translated = next(
            (source, translated)
            for source, translated in aeo_answers_i18n.LOCALE_TEXT_OVERRIDES[
                "ja"
            ].items()
            if source.startswith("A good itinerary app")
        )
        self.assertIn("flights, hotels, activities", source)
        self.assertIn("フライト、ホテル、アクティビティ", translated)
        self.assertEqual(
            "kalkering",
            aeo_answers_i18n.apply_locale_target_replacements(
                "streckspårning",
                "sv",
            ),
        )
        self.assertEqual(
            "Kalkering",
            aeo_answers_i18n.apply_locale_target_replacements(
                "Streckspårning",
                "sv",
            ),
        )
        self.assertEqual(
            "Ingen spårning",
            aeo_answers_i18n.apply_locale_target_replacements(
                "Ingen spårning",
                "sv",
            ),
        )
        self.assertEqual(
            "celular",
            aeo_answers_i18n.apply_locale_target_replacements(
                "móvil",
                "es-MX",
            ),
        )

    def test_north_american_english_uses_summarize(self):
        source = "Capture and summarise the meeting."
        for locale in ("en-US", "en-CA"):
            self.assertEqual(
                "Capture and summarize the meeting.",
                aeo_answers_i18n.english_mapping([source], locale)[source],
            )

    def test_reviewed_target_terms_replace_brand_and_meaning_errors(self):
        self.assertEqual(
            "iPhone‌ನಲ್ಲಿ ಪ್ರಾಮಾಣಿಕ ಮಾರ್ಗದರ್ಶಿ",
            aeo_answers_i18n.apply_locale_target_replacements(
                "ಐಫೋನ್‌ನಲ್ಲಿ ನಿಷ್ಠ ಮಾರ್ಗದರ್ಶಿ",
                "kn-IN",
            ),
        )
        self.assertEqual(
            "પ્રામાણિક iPhone એપ્લિકેશન",
            aeo_answers_i18n.apply_locale_target_replacements(
                "નિષ્ઠાવાન iPhone એપ્લિકેશન",
                "gu-IN",
            ),
        )

    def test_local_translation_batches_preserve_order_and_size(self):
        strings = ["a" * 2000, "b" * 1500, "c"]
        self.assertEqual(
            [[strings[0]], [strings[1], strings[2]]],
            aeo_answers_i18n.string_batches(strings, max_chars=3200),
        )

    def test_github_translation_batches_preserve_all_strings(self):
        strings = ["a" * 16000, "b" * 9000, "c"]
        batches = aeo_answers_i18n.github_translation_batches(
            strings,
            max_chars=24000,
        )
        self.assertEqual([[strings[0]], [strings[1], strings[2]]], batches)

    def test_github_translation_cache_resumes_completed_batches(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            aeo_answers_i18n.subprocess,
            "run",
        ) as run:
            run.return_value.stdout = "token"
            first = aeo_answers_i18n.GithubModelsTranslator(
                ["Hello"],
                cache_dir=Path(tmp),
            )
            with patch.object(
                first,
                "_translate_batch",
                return_value={"Hello": "Bonjour"},
            ) as translate:
                self.assertEqual(
                    {"Hello": "Bonjour"},
                    first.translate(["Hello"], "fr-FR"),
                )
                translate.assert_called_once()

            second = aeo_answers_i18n.GithubModelsTranslator(
                ["Hello"],
                cache_dir=Path(tmp),
            )
            with patch.object(second, "_translate_batch") as translate:
                self.assertEqual(
                    {"Hello": "Bonjour"},
                    second.translate(["Hello"], "fr-FR"),
                )
                translate.assert_not_called()

    def test_us_english_uses_local_spelling_without_changing_brands(self):
        mapping = aeo_answers_i18n.english_mapping(
            ["Practise recognising colour while travelling with Apple Watch."],
            "en-US",
        )
        self.assertEqual(
            "Practice recognizing color while traveling with Apple Watch.",
            mapping[
                "Practise recognising colour while travelling with Apple Watch."
            ],
        )

    def test_persona_meta_description_truncates_with_an_ellipsis(self):
        description = persona_meta_description(
            "A long buyer-intent sentence " * 12,
            "Wordmate: Learn 44 Languages",
        )
        self.assertLessEqual(len(description), 160)
        self.assertIn("… — Wordmate: Learn 44 Languages.", description)

    def test_reconcile_all_alternates_updates_every_existing_variant(self):
        slug = "buyer-guide"
        initial = (
            '<link rel="alternate" hreflang="en" href="old">\n'
            '<link rel="alternate" hreflang="x-default" href="old">\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers"
            paths = [
                answers / f"{slug}.html",
                root / "en-US" / "answers" / f"{slug}.html",
                root / "fr-FR" / "answers" / f"{slug}.html",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(initial, encoding="utf-8")

            with (
                patch.object(aeo_answers_i18n, "ROOT", root),
                patch.object(aeo_answers_i18n, "ANSWERS", answers),
            ):
                self.assertEqual(
                    3,
                    aeo_answers_i18n.reconcile_all_alternates(slug),
                )

            expected = {"en", "en-US", "fr-FR", "x-default"}
            for path in paths:
                content = path.read_text(encoding="utf-8")
                actual = {
                    line.split('hreflang="', 1)[1].split('"', 1)[0]
                    for line in content.splitlines()
                    if 'hreflang="' in line
                }
                self.assertEqual(expected, actual)

    def test_deferred_refresh_allows_parallel_locale_generation(self):
        slug = "buyer-guide"
        source = (
            '<html lang="en"><head>'
            '<link rel="canonical" href="old">'
            '<link rel="alternate" hreflang="en" href="old">'
            '<meta property="og:url" content="old">'
            "</head><body><h1>Hello</h1></body></html>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answers = root / "answers"
            answers.mkdir()
            (answers / f"{slug}.html").write_text(source, encoding="utf-8")
            argv = [
                "aeo_answers_i18n.py",
                slug,
                "--langs",
                "en-US",
                "--trans",
                tmp,
                "--defer-shared-refresh",
            ]
            with (
                patch.object(aeo_answers_i18n, "ROOT", root),
                patch.object(aeo_answers_i18n, "ANSWERS", answers),
                patch.object(sys, "argv", argv),
                patch.object(
                    aeo_answers_i18n,
                    "reconcile_all_alternates",
                ) as reconcile,
            ):
                self.assertEqual(0, aeo_answers_i18n.main())
            self.assertTrue(
                (root / "en-US" / "answers" / f"{slug}.html").exists()
            )
            reconcile.assert_not_called()


if __name__ == "__main__":
    unittest.main()
