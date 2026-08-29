#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
GEO = HERE.parent
ROOT = GEO.parent
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(ROOT / "social"))

import aeo_answers  # noqa: E402
import aeo_answers_i18n  # noqa: E402
import answer_hreflang  # noqa: E402
import fix_en_hreflang  # noqa: E402


QUESTION = "how to choose a unblur photo app"
SLUG = "how-to-choose-a-unblur-photo-app"
LOCALES = [
    "ar-SA",
    "de-DE",
    "es-ES",
    "fr-FR",
    "id",
    "ja",
    "ko",
    "ms",
    "pt-BR",
    "pt-PT",
    "th",
    "tr",
    "vi",
    "zh-Hant",
]


def localized_document(root: Path, locale: str) -> str:
    canonical = answer_hreflang.page_url(SLUG, locale)
    alternates = answer_hreflang.build_block(root, SLUG, locale)
    return (
        f'<html lang="{locale}"><head>'
        f'<link rel="canonical" href="{canonical}">\n'
        f"{alternates}\n"
        "</head><body></body></html>"
    )


class AnswerHreflangContractTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        (root / "answers").mkdir(parents=True)
        english = root / "answers" / f"{SLUG}.html"
        english.touch()
        for locale in LOCALES:
            path = root / locale / "answers" / f"{SLUG}.html"
            path.parent.mkdir(parents=True)
            path.touch()
        for locale in LOCALES:
            path = root / locale / "answers" / f"{SLUG}.html"
            path.write_text(
                localized_document(root, locale), encoding="utf-8"
            )
        raw = aeo_answers.default_content(QUESTION, "unblurry")
        content = aeo_answers.normalized_content(
            raw, QUESTION, "unblurry"
        )
        with mock.patch.object(
            aeo_answers, "extract_style", return_value="body{}"
        ):
            rendered = aeo_answers.render_page(
                QUESTION, "unblurry", content, pages_root=root
            )
        english.write_text(rendered, encoding="utf-8")
        return english

    def test_render_and_reconciler_share_one_idempotent_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            english = self.fixture(root)
            expected = answer_hreflang.build_block(root, SLUG)
            self.assertIn(expected, english.read_text(encoding="utf-8"))
            first = fix_en_hreflang.run(
                root, slugs={SLUG}
            )
            self.assertEqual(0, first["changed"])

            before = english.read_bytes()
            raw = aeo_answers.default_content(QUESTION, "unblurry")
            content = aeo_answers.normalized_content(
                raw, QUESTION, "unblurry"
            )
            with mock.patch.object(
                aeo_answers, "extract_style", return_value="body{}"
            ):
                rerendered = aeo_answers.render_page(
                    QUESTION, "unblurry", content, pages_root=root
                )
            english.write_text(rerendered, encoding="utf-8")
            self.assertEqual(before, english.read_bytes())
            second = fix_en_hreflang.run(
                root, slugs={SLUG}
            )
            self.assertEqual(0, second["changed"])
            self.assertEqual(
                len(LOCALES) + 1,
                answer_hreflang.validate_cluster(root, SLUG),
            )

    def test_localized_generator_uses_the_shared_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with mock.patch.object(
                aeo_answers_i18n, "ROOT", root
            ), mock.patch.object(
                aeo_answers_i18n, "ANSWERS", root / "answers"
            ):
                self.assertEqual(
                    answer_hreflang.build_block(root, SLUG, "fr-FR"),
                    aeo_answers_i18n.alternates_html(SLUG, "fr-FR"),
                )

    def test_missing_or_en_us_self_alternate_fails_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            english = self.fixture(root)
            source = english.read_text(encoding="utf-8")
            missing = answer_hreflang.ALTERNATE_BLOCK_RE.sub(
                "", source, count=1
            )
            with self.assertRaises(
                answer_hreflang.HreflangContractError
            ):
                answer_hreflang.validate_document(
                    missing, root, SLUG
                )

            wrong_self = source.replace(
                'hreflang="en"', 'hreflang="en-US"', 1
            )
            with self.assertRaises(
                answer_hreflang.HreflangContractError
            ):
                answer_hreflang.validate_document(
                    wrong_self, root, SLUG
                )


if __name__ == "__main__":
    unittest.main()
