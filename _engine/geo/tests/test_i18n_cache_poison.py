#!/usr/bin/env python3
"""A poisoned shared dictionary must be dropped at load, never fail the run.

2026-08-30: one misaligned GitHub Models batch cached, under an unrelated
English source, an ar-SA sentence naming CV Desk. Every nightly run after
that died in require_no_cross_app_translation during the refresh pass, so
the whole GEO publish stalled. The cache loaders now drop such pairs (the
slot counts as untranslated again) while the page-level gate stays strict.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import aeo_answers_i18n as i18n  # noqa: E402


NAMES = i18n.portfolio_app_names()


class DropCrossAppCachePoisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(NAMES, "portfolio registry must expose app names")
        self.name = NAMES[0]

    def test_drops_pair_that_injects_an_unrelated_app(self) -> None:
        mapping = {
            "No app can guarantee that. Keep the structure simple.":
                f"{self.name} keeps a clean structure the systems can read.",
        }
        dropped = i18n.drop_cross_app_cache_poison(mapping, "unit")
        self.assertEqual(1, dropped)
        self.assertEqual({}, mapping)

    def test_keeps_pair_whose_source_already_names_the_app(self) -> None:
        source = f"{self.name} keeps exports simple."
        mapping = {source: f"{self.name} garde les exports simples."}
        dropped = i18n.drop_cross_app_cache_poison(mapping, "unit")
        self.assertEqual(0, dropped)
        self.assertIn(source, mapping)

    def test_keeps_plain_pairs_without_app_names(self) -> None:
        mapping = {"How do I export a PDF?": "Comment exporter un PDF ?"}
        dropped = i18n.drop_cross_app_cache_poison(mapping, "unit")
        self.assertEqual(0, dropped)
        self.assertEqual(1, len(mapping))

    def test_refresh_loader_sanitizes_dictionaries(self) -> None:
        # The refresh path loads DIR/<lang>.json straight into global maps;
        # a poisoned entry there must vanish before any page is rendered.
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            poison = {
                "A neutral sentence about backups.":
                    f"{self.name} est le meilleur choix.",
                "How do I export a PDF?": "Comment exporter un PDF ?",
            }
            path = Path(tmp) / "fr-FR.json"
            path.write_text(
                json.dumps(poison, ensure_ascii=False), encoding="utf-8"
            )
            loaded = json.loads(path.read_text(encoding="utf-8"))
            i18n.drop_cross_app_cache_poison(loaded, path.name)
            self.assertEqual(
                {"How do I export a PDF?": "Comment exporter un PDF ?"},
                loaded,
            )


if __name__ == "__main__":
    unittest.main()
