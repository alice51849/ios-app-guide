#!/usr/bin/env python3
"""Stale App Store names and competitor-led titles must not survive regeneration.

tripplanet-04: localized answer pages written before the Trip Planet rename
kept "Lumi Trip Planet" because brands pass through translation verbatim and
--refresh only rewrites a page when the dictionary localizes more of it.
lumibopomofopro-07: the 8 legacy localized lumibopomofopro-vs-* pages led with
the competitor's name; aeo_pages now retitles them with the use-case lead.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import aeo_answers_i18n as i18n  # noqa: E402
import aeo_pages  # noqa: E402


class RenamedBrandTests(unittest.TestCase):
    ENGLISH = "<p>Get Trip Planet: Kids Quest on the App Store</p>"

    def test_old_brand_is_swapped_when_english_uses_new_name(self) -> None:
        page = "<p>لهذا وُجد Lumi Trip Planet.</p>"
        self.assertEqual(
            "<p>لهذا وُجد Trip Planet: Kids Quest.</p>",
            i18n.apply_brand_renames(page, self.ENGLISH),
        )

    def test_long_old_name_is_replaced_whole(self) -> None:
        page = "Lumi Trip Planet: World Travel"
        self.assertEqual(
            "Trip Planet: Kids Quest",
            i18n.apply_brand_renames(page, self.ENGLISH),
        )

    def test_page_is_untouched_while_english_still_has_old_name(self) -> None:
        page = "<p>Lumi Trip Planet</p>"
        english = "<p>Lumi Trip Planet</p>"
        self.assertEqual(page, i18n.apply_brand_renames(page, english))

    def test_korean_particles_follow_the_new_final_sound(self) -> None:
        page = "아니요 — Lumi Trip Planet은 광고가 없고 Lumi Trip Planet과 함께"
        self.assertEqual(
            "아니요 — Trip Planet: Kids Quest는 광고가 없고 "
            "Trip Planet: Kids Quest와 함께",
            i18n.apply_brand_renames(page, self.ENGLISH, "ko"),
        )

    def test_new_name_is_a_brand(self) -> None:
        self.assertIn("Trip Planet: Kids Quest", i18n.BRANDS)


class LocalizedUseCaseTitleTests(unittest.TestCase):
    SLUG = "lumibopomofopro-vs-hellochinese"
    OLD = "iPhone 上 HelloChinese 的替代方案：Lumi Bopomofo Pro"

    def _page(self, root: Path, locale: str, extra: str = "") -> Path:
        path = root / locale / "alternatives" / f"{self.SLUG}.html"
        path.parent.mkdir(parents=True)
        path.write_text(
            f'<html{extra}><head><title>{self.OLD}</title>'
            f'<meta property="og:title" content="{self.OLD}">'
            f'<script type="application/ld+json">{{"name": "{self.OLD}"}}'
            f"</script></head><body><h1>{self.OLD}</h1></body></html>",
            encoding="utf-8",
        )
        return path

    def test_title_leads_with_use_case_and_app_everywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._page(root, "zh-Hant")
            changed = aeo_pages.retitle_localized_alternatives(
                "lumibopomofopro", self.SLUG, "HelloChinese", pages=root
            )
            self.assertEqual([path], changed)
            doc = path.read_text(encoding="utf-8")
            new = "一次買斷的注音 App：Lumi Bopomofo Pro 與 HelloChinese 比較"
            self.assertNotIn(self.OLD, doc)
            self.assertEqual(4, doc.count(new))
            self.assertFalse(new.startswith("HelloChinese"))
            # Idempotent: a second run changes nothing.
            self.assertEqual(
                [],
                aeo_pages.retitle_localized_alternatives(
                    "lumibopomofopro", self.SLUG, "HelloChinese", pages=root
                ),
            )

    def test_every_template_leads_with_app_or_intent(self) -> None:
        for locale in aeo_pages.LOCALIZED_USE_CASE_TITLES["lumibopomofopro"]:
            title = aeo_pages.localized_use_case_title(
                "lumibopomofopro", locale, "ChineseSkill"
            )
            self.assertIn("Lumi Bopomofo Pro", title)
            self.assertFalse(title.startswith("ChineseSkill"), locale)
            self.assertLess(
                title.index("Lumi Bopomofo Pro"), title.index("ChineseSkill")
            )

    def test_pages_owned_by_alternatives_i18n_are_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._page(
                root, "ja", ' data-alternatives-owner="lumi-alternatives-exact50-v1"'
            )
            before = path.read_text(encoding="utf-8")
            self.assertEqual(
                [],
                aeo_pages.retitle_localized_alternatives(
                    "lumibopomofopro", self.SLUG, "HelloChinese", pages=root
                ),
            )
            self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_apps_without_use_case_lead_are_not_retitled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [],
                aeo_pages.retitle_localized_alternatives(
                    "mochi", "mochi-vs-todoist", "Todoist", pages=Path(tmp)
                ),
            )


if __name__ == "__main__":
    unittest.main()
