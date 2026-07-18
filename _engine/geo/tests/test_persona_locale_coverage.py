#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aeo_answers_i18n
import queries
from answer_personas import PERSONAS, persona_meta_description
from official_locales import OFFICIAL_LOCALES


CURRENT_LIVE_APPS = {
    "aim990",
    "cvdesk",
    "cyca",
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
    "mochi",
    "photocream",
    "picclear",
    "scanto",
    "sereno",
    "snapport",
    "sononote",
    "tripbee",
    "tripplanet",
    "unblurry",
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

    def test_answer_localizer_covers_all_official_locales(self):
        self.assertEqual(50, len(aeo_answers_i18n.ALL_LANGS))
        self.assertEqual(
            set(OFFICIAL_LOCALES),
            set(aeo_answers_i18n.ALL_LANGS),
        )

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


if __name__ == "__main__":
    unittest.main()
