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


if __name__ == "__main__":
    unittest.main()
