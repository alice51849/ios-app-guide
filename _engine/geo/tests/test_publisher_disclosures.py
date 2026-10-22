#!/usr/bin/env python3
"""Regression tests for truthful publisher disclosure migration."""

from __future__ import annotations

import html
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gen_publisher_disclosures as disclosures


class PublisherDisclosureTests(unittest.TestCase):
    def test_migration_is_localized_truthful_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pages = root / "pages"
            translations = root / "translations"
            translations.mkdir()
            translated_notice = "Vom App-Entwickler verfasster Kaufratgeber."
            translated_footer = "Von Lumi Studio als App-Entwickler verfasst."
            (translations / "de-DE.json").write_text(
                json.dumps(
                    {
                        disclosures.NEW_NOTICE: translated_notice,
                        disclosures.NEW_FOOTER: translated_footer,
                    }
                ),
                encoding="utf-8",
            )
            sources = {
                "answers/root.html": (
                    f"<p>{disclosures.OLD_NOTICE}</p>"
                    f"<footer>{disclosures.OLD_FOOTER}</footer>"
                ),
                "de-DE/answers/localized.html": (
                    f"<p>{disclosures.OLD_NOTICE}</p>"
                    f"<footer>{disclosures.NEW_FOOTER}</footer>"
                ),
                "pa-IN/answers/fallback.html": (
                    f"<p>{disclosures.OLD_NOTICE}</p>"
                    f"<footer>{disclosures.OLD_FOOTER}</footer>"
                ),
            }
            for relative, content in sources.items():
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            first = disclosures.migrate(
                pages,
                translations_dir=translations,
            )
            tracked = list(pages.rglob("*.html"))
            mtimes = {path: path.stat().st_mtime_ns for path in tracked}
            second = disclosures.migrate(
                pages,
                translations_dir=translations,
            )

            self.assertEqual(3, first["changed_files"])
            self.assertEqual(6, first["replacements"])
            self.assertEqual(["pa-IN"], first["fallback_locales"])
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(0, second["replacements"])
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in tracked},
            )
            combined = "\n".join(
                path.read_text(encoding="utf-8") for path in tracked
            )
            self.assertNotIn(disclosures.OLD_NOTICE, combined)
            self.assertNotIn(disclosures.OLD_FOOTER, combined)
            self.assertIn(translated_notice, combined)
            self.assertIn(translated_footer, combined)
            self.assertIn(disclosures.NEW_NOTICE, combined)
            self.assertIn(disclosures.NEW_FOOTER, combined)

    def test_structural_migration_repairs_localized_answers_guides_and_hubs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pages = root / "pages"
            translations = root / "translations"
            translations.mkdir()
            translated_notice = "Guide rédigé par le développeur."
            translated_footer = "Guide publié par Lumi Studio."
            (translations / "fr-FR.json").write_text(
                json.dumps(
                    {
                        disclosures.NEW_NOTICE: translated_notice,
                        disclosures.NEW_FOOTER: translated_footer,
                    }
                ),
                encoding="utf-8",
            )
            legacy_notice = (
                "Guide indépendant. Les fonctions et prix peuvent changer."
            )
            legacy_footer = (
                "Guide indépendant. Vérifiez les exigences officielles."
            )
            sources = {
                "fr-FR/answers/example.html": (
                    '<article class="card two answer">'
                    f"<p>{legacy_notice}</p>"
                    f'<p class="notice">{legacy_notice}</p></article>'
                    '<footer class="footer">'
                    f'<div class="wrap">{legacy_footer}</div></footer>'
                ),
                "fr-FR/guides/example.html": (
                    "<main><h1>Guide</h1><hr><p><small>"
                    "Ancienne déclaration indépendante."
                    "</small></p><!-- app-store-qr:start -->"
                    '<section class="app-store-qr-card"></section>'
                    '<p data-publisher-disclosure="true"><small>'
                    f"{translated_footer}</small></p></main>"
                ),
                "fr-FR/hubs/index.html": (
                    "<main><h1>Hub</h1></main></body>"
                ),
            }
            for relative, content in sources.items():
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            first = disclosures.migrate(
                pages,
                translations_dir=translations,
            )
            tracked = list(pages.rglob("*.html"))
            mtimes = {path: path.stat().st_mtime_ns for path in tracked}
            second = disclosures.migrate(
                pages,
                translations_dir=translations,
            )

            self.assertEqual(3, first["changed_files"])
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in tracked},
            )
            combined = "\n".join(
                path.read_text(encoding="utf-8") for path in tracked
            )
            self.assertNotIn(legacy_notice, combined)
            self.assertNotIn(legacy_footer, combined)
            self.assertNotIn("Ancienne déclaration indépendante.", combined)
            self.assertIn(translated_notice, combined)
            self.assertEqual(3, combined.count(disclosures.PUBLISHER_MARKER))
            self.assertEqual(0, first["legacy_claims"])

    def test_reuses_verified_translation_without_doubled_notice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            translations = Path(directory)
            translated_notice = (
                "Guide rédigé par le développeur. Les prix peuvent changer."
            )
            translated_legal = (
                "TOEIC est une marque déposée. Aim990 est indépendant."
            )
            (translations / "fr-FR.json").write_text(
                json.dumps(
                    {
                        disclosures.LEGACY_DOUBLED_AIM990_NOTICE: (
                            f"{translated_notice} Les prix peuvent changer. "
                            f"{translated_legal}"
                        ),
                        disclosures.NEW_AIM990_NOTICE: (
                            f"{translated_notice} Les prix peuvent changer. "
                            f"{translated_legal}"
                        ),
                        disclosures.NEW_FOOTER: "Guide publié par Lumi Studio.",
                    }
                ),
                encoding="utf-8",
            )

            loaded = disclosures._translations("fr-FR", translations)

            self.assertEqual(translated_notice, loaded[disclosures.NEW_NOTICE])
            self.assertEqual(
                f"{translated_notice} {translated_legal}",
                loaded[disclosures.NEW_AIM990_NOTICE],
            )

    def test_localized_aim990_notice_is_selected_by_app_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pages = root / "pages"
            translations = root / "translations"
            translations.mkdir()
            notice = "앱 개발자가 직접 작성한 구매 가이드입니다."
            aim990_notice = (
                f"{notice} 토익은 ETS의 등록 상표이며 Aim990은 ETS와 "
                "제휴하거나 승인받지 않은 독립 학습 도구입니다."
            )
            footer = "Lumi Studio가 직접 작성한 가이드입니다."
            (translations / "ko.json").write_text(
                json.dumps(
                    {
                        disclosures.NEW_NOTICE: notice,
                        disclosures.NEW_AIM990_NOTICE: aim990_notice,
                        disclosures.NEW_FOOTER: footer,
                    }
                ),
                encoding="utf-8",
            )
            path = pages / "ko" / "answers" / "best-toeic-app.html"
            path.parent.mkdir(parents=True)
            path.write_text(
                '<article class="card two answer">'
                f'<p class="notice">{aim990_notice}</p></article>'
                '<a href="https://apps.apple.com/kr/app/id6784974530">'
                "App Store</a>"
                '<footer class="footer">'
                f'<div class="wrap">{footer}</div></footer>',
                encoding="utf-8",
            )

            first = disclosures.migrate(
                pages,
                translations_dir=translations,
            )
            second = disclosures.migrate(
                pages,
                translations_dir=translations,
            )

            source = path.read_text(encoding="utf-8")
            self.assertIn(f'<p class="notice">{aim990_notice}</p>', source)
            self.assertNotIn(f'<p class="notice">{notice}</p>', source)
            self.assertEqual(1, first["changed_files"])
            self.assertEqual(0, second["changed_files"])

    def test_canadian_french_disclosures_never_fall_back_to_english(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            loaded = disclosures._translations(
                "fr-CA",
                Path(directory),
            )

        for source in (
            disclosures.NEW_NOTICE,
            disclosures.NEW_FOOTER,
            disclosures.NEW_AIM990_NOTICE,
        ):
            localized, fallback = disclosures._localized(
                source,
                "fr-CA",
                loaded,
            )
            self.assertFalse(fallback)
            self.assertNotEqual(source, localized)

    def test_generators_do_not_reintroduce_independence_claims(self) -> None:
        geo = Path(disclosures.__file__).resolve().parent
        for name in (
            "aeo_guide.py",
            "aeo_guide_i18n.py",
            "ensure_live_guides.py",
            "gen_roundups.py",
            "zhuyin_readiness_tool.py",
        ):
            source = (geo / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("independent guide", source, name)
            self.assertNotIn("independent buying guide", source, name)

    def test_daily_geo_regenerates_tool_before_disclosure_gate(self) -> None:
        engine_root = Path(disclosures.__file__).resolve().parents[1]
        pages_root = (
            engine_root.parent
            if engine_root.name == "_engine"
            else engine_root / "geo" / "pages"
        )
        workflow = (
            pages_root / ".github" / "workflows" / "geo-daily.yml"
        ).read_text(encoding="utf-8")
        materialize = workflow.split(
            "- name: Materialize newly live app surfaces",
            1,
        )[1].split(
            "- name: Reconcile verified Standard.site discovery links",
            1,
        )[0]
        self.assertLess(
            materialize.index("python3 zhuyin_readiness_tool.py"),
            materialize.index("python3 gen_publisher_disclosures.py"),
        )


class LandingDisclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copies = disclosures.load_landing_disclosures()

    def document(self):
        return {
            "schema_version": 1,
            "localizations": {
                locale: {disclosures.LANDING_DISCLOSURE: value}
                for locale, value in self.copies.items()
            },
        }

    def load_document(self, document):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "copy.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            return disclosures.load_landing_disclosures(path)

    def test_exact50_copy_is_native_single_line_and_immutable(self):
        self.assertEqual(set(disclosures.OFFICIAL_LOCALES), set(self.copies))
        self.assertEqual(50, len(self.copies))
        with self.assertRaises(TypeError):
            self.copies["en-US"] = "changed"
        for locale, value in self.copies.items():
            with self.subTest(locale=locale):
                disclosures._validate_landing_disclosure(locale, value)
                self.assertEqual([value], value.splitlines())
                if not locale.startswith("en-"):
                    self.assertNotEqual(disclosures.LANDING_DISCLOSURE, value)

    def test_invalid_copy_fails_closed(self):
        for kind in ("schema", "missing-locale", "extra-locale", "missing-key",
                     "empty", "fallback", "linebreak", "foreign-script"):
            with self.subTest(kind=kind):
                document = self.document()
                localized = document["localizations"]
                if kind == "schema":
                    document["schema_version"] = 2
                elif kind == "missing-locale":
                    localized.pop("bn-BD")
                elif kind == "extra-locale":
                    localized["xx"] = localized["en-US"]
                elif kind == "missing-key":
                    localized["fr-FR"] = {}
                else:
                    localized["fr-FR"][disclosures.LANDING_DISCLOSURE] = {
                        "empty": "",
                        "fallback": disclosures.LANDING_DISCLOSURE,
                        "linebreak": self.copies["fr-FR"] + "\n",
                        "foreign-script": "這不是法文。",
                    }[kind]
                with self.assertRaises(ValueError):
                    self.load_document(document)

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "copy.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                disclosures.load_landing_disclosures(path)

    def test_all50_insertions_are_exact_visible_idempotent_and_body_preserving(self):
        source = (
            '<!doctype html><html><head><link rel="canonical" href="https://example.test/">'
            '</head><body><main><h1>Product</h1><p>Unchanged &amp; complete.</p>\n'
            '</main></body></html>'
        )
        for locale, value in self.copies.items():
            with self.subTest(locale=locale):
                updated = disclosures.ensure_landing_disclosure(
                    source, locale, copy_by_locale=self.copies
                )
                expected = (
                    f'<p class="publisher-disclosure" {disclosures.PUBLISHER_MARKER}>'
                    f"<small>{html.escape(value, quote=False)}</small></p>\n"
                )
                self.assertEqual(1, updated.count(expected))
                self.assertEqual(source, updated.replace(expected, "", 1))
                self.assertLess(updated.index(expected), updated.index("</main>"))
                self.assertEqual(updated, disclosures.ensure_landing_disclosure(
                    updated, locale, copy_by_locale=self.copies
                ))
                self.assertNotIn("apps.apple.com", updated)

    def test_wrong_locale_updates_only_its_managed_paragraph(self):
        source = "<main><p>Product remains.</p></main>"
        english = disclosures.ensure_landing_disclosure(
            source, "en-US", copy_by_locale=self.copies
        )
        bengali = disclosures.ensure_landing_disclosure(
            english, "bn-BD", copy_by_locale=self.copies
        )
        self.assertEqual(english.replace(self.copies["en-US"], self.copies["bn-BD"]), bengali)
        self.assertEqual(1, bengali.count(disclosures.PUBLISHER_MARKER))

    def test_ambiguous_missing_hidden_or_duplicate_markers_fail_closed(self):
        paragraph = (
            f'<p class="publisher-disclosure" {disclosures.PUBLISHER_MARKER}>'
            "<small>Wrong locale.</small></p>"
        )
        invalid = [
            "<body>No main.</body>",
            "<main>Unclosed",
            "<main/>",
            "<main></main><main></main>",
            "<main hidden></main>",
            '<div style="display: none"><main></main></div>',
            f"<main>{paragraph}{paragraph}</main>",
            f"{paragraph}<main></main>",
            f'<main>{paragraph.replace("<p ", "<p hidden ")}</main>',
            f'<main>{paragraph.replace("<small>", "<small hidden>")}</main>',
            f'<main>{paragraph.replace("</p>", "")}</main>',
            f'<main>{paragraph.replace("publisher-disclosure", "other", 1)}</main>',
        ]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(ValueError):
                disclosures.ensure_landing_disclosure(
                    source, "en-US", copy_by_locale=self.copies
                )
        with self.assertRaises(ValueError):
            disclosures.ensure_landing_disclosure(
                "<main></main>", "xx", copy_by_locale=self.copies
            )

    def test_builder_preserves_bn_content_without_purchase_actions(self):
        import build_pages_i18n as builder

        with tempfile.TemporaryDirectory() as directory, patch.object(
            builder, "PAGES", directory
        ), patch.object(builder, "load_landing_disclosures", side_effect=AssertionError):
            for locale in ("en-US", "bn-BD"):
                path = Path(builder.build_one(
                    "caldaily", locale, disclosures.OFFICIAL_LOCALES,
                    copy_by_locale=self.copies,
                ))
                content = path.read_text(encoding="utf-8")
                self.assertEqual(1, content.count(disclosures.PUBLISHER_MARKER))
                self.assertIn(html.escape(self.copies[locale], quote=False), content)
                if locale == "bn-BD":
                    self.assertNotIn("apps.apple.com", content)
                    self.assertNotIn("InstallAction", content)
                    self.assertIn("MARKET_NOT_IN_APPLE_MEDIA_SERVICES", content)


if __name__ == "__main__":
    unittest.main()
