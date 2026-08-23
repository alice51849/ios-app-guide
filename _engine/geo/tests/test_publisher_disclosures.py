#!/usr/bin/env python3
"""Regression tests for truthful publisher disclosure migration."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

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
        root = Path(disclosures.__file__).resolve().parents[2]
        workflow = (
            root / ".github" / "workflows" / "geo-daily.yml"
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


if __name__ == "__main__":
    unittest.main()
