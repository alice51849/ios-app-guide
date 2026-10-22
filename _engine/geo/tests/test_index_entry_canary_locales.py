"""index-entry canary 語系紀錄：補語系自動更新且維持綠燈，少掉 entry 一定紅燈。

全部用暫存站台樹，不需要真的 Guide checkout，兩個 repo 都會真的跑。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import index_entry_canary_locales as canary  # noqa: E402

SITE = "https://example.test/guide"
SLUG = "best-app-to-sort-screenshots-on-iphone-offline"


def english_page(locales, *, overrides=None):
    overrides = overrides or {}
    english = f"{SITE}/answers/{SLUG}.html"
    targets = {"en": english}
    targets.update(
        {locale: f"{SITE}/{locale}/answers/{SLUG}.html" for locale in locales}
    )
    targets["x-default"] = english
    targets.update(overrides)
    links = "\n".join(
        f'<link rel="alternate" hreflang="{hreflang}" href="{href}">'
        for hreflang, href in targets.items()
    )
    return (
        f'<html lang="en"><head><link rel="canonical" href="{english}">\n'
        f"{links}\n</head><body></body></html>\n"
    )


def localized_page(locale, canonical_locale=None):
    canonical_locale = canonical_locale or locale
    return (
        f'<html lang="{locale}"><head><link rel="canonical" '
        f'href="{SITE}/{canonical_locale}/answers/{SLUG}.html"></head>'
        "<body></body></html>\n"
    )


class CanaryLocaleRecordTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.pages = Path(self._directory.name)
        (self.pages / "answers").mkdir()
        (self.pages / "_engine" / "geo").mkdir(parents=True)

    def tearDown(self):
        self._directory.cleanup()

    def publish(self, locales, *, declared=None, overrides=None):
        for locale in locales:
            page = self.pages / locale / "answers" / f"{SLUG}.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(localized_page(locale), encoding="utf-8")
        (self.pages / "answers" / f"{SLUG}.html").write_text(
            english_page(locales if declared is None else declared, overrides=overrides),
            encoding="utf-8",
        )

    def refresh(self, **kwargs):
        return canary.refresh(self.pages, slugs=(SLUG,), **kwargs)

    def recorded(self):
        return canary.load_state(self.pages)["canaries"][SLUG]

    def problems(self, locales):
        return canary.hreflang_problems(self.pages, SLUG, locales, SITE)

    def test_new_locale_version_stays_green_and_updates_the_record(self):
        self.publish(["en-US", "ja"])
        self.refresh()
        self.assertEqual(["en-US", "ja"], self.recorded())

        # Someone adds a zh-Hant version (page + English hreflang) and touches
        # nothing else: the record follows the site and every check stays green.
        page = self.pages / "zh-Hant" / "answers" / f"{SLUG}.html"
        page.parent.mkdir(parents=True)
        page.write_text(localized_page("zh-Hant"), encoding="utf-8")
        self.publish(["en-US", "ja", "zh-Hant"])
        self.assertFalse(canary.check(self.pages, (SLUG,)))
        summary = self.refresh()
        self.assertTrue(summary["changed"])
        self.assertEqual({SLUG: ["zh-Hant"]}, summary["added"])
        self.assertEqual(["en-US", "ja", "zh-Hant"], self.recorded())
        self.assertTrue(canary.check(self.pages, (SLUG,)))
        self.assertEqual([], self.problems(self.recorded()))
        self.assertFalse(self.refresh()["changed"])

    def test_deleting_a_recorded_locale_version_is_red(self):
        self.publish(["ja", "zh-Hant"])
        self.refresh()
        before = canary.state_path(self.pages).read_bytes()
        (self.pages / "zh-Hant" / "answers" / f"{SLUG}.html").unlink()
        self.publish(["ja"])
        # The record still claims zh-Hant, which no longer exists.
        self.assertFalse(canary.check(self.pages, (SLUG,)))
        with self.assertRaisesRegex(canary.CanaryLocaleRemoval, "zh-Hant"):
            self.refresh()
        self.assertEqual(before, canary.state_path(self.pages).read_bytes())

    def test_only_an_explicit_approval_can_shrink_the_record(self):
        self.publish(["ja", "zh-Hant"])
        self.refresh()
        (self.pages / "zh-Hant" / "answers" / f"{SLUG}.html").unlink()
        self.publish(["ja"])
        summary = self.refresh(allow_removals={(SLUG, "zh-Hant")})
        self.assertEqual({SLUG: ["zh-Hant"]}, summary["removed"])
        self.assertEqual(["ja"], self.recorded())

    def test_dropping_a_canary_from_the_manifest_is_red(self):
        self.publish(["ja"])
        self.refresh()
        with self.assertRaisesRegex(canary.CanaryLocaleRemoval, SLUG):
            canary.refresh(self.pages, slugs=("another-canary",))

    def test_missing_hreflang_entry_is_red(self):
        self.publish(["ja", "zh-Hant"], declared=["ja"])
        self.assertEqual(
            [f"{SLUG}: missing hreflang zh-Hant"],
            self.problems(["ja", "zh-Hant"]),
        )

    def test_hreflang_pointing_at_the_wrong_locale_is_red(self):
        wrong = f"{SITE}/ko/answers/{SLUG}.html"
        self.publish(["ja"], overrides={"ja": wrong})
        self.assertEqual(
            [f"{SLUG}: hreflang ja points to {wrong}"],
            self.problems(["ja"]),
        )

    def test_hreflang_without_a_localized_page_is_red(self):
        self.publish(["ja"], declared=["ja", "fr-FR"])
        self.assertEqual(
            [f"{SLUG}: hreflang fr-FR has no localized page"],
            self.problems(["ja"]),
        )

    def test_localized_canonical_must_be_its_own_url(self):
        self.publish(["ja"])
        (self.pages / "ja" / "answers" / f"{SLUG}.html").write_text(
            localized_page("ja", canonical_locale="ko"), encoding="utf-8",
        )
        self.assertEqual(
            [f"{SLUG}: ja canonical is not its own URL"],
            self.problems(["ja"]),
        )

    def test_record_is_sorted_stable_json(self):
        self.publish(["zh-Hant", "ja"])
        self.refresh()
        text = canary.state_path(self.pages).read_text(encoding="utf-8")
        self.assertEqual(canary.render(json.loads(text)), text)
        self.assertEqual(["ja", "zh-Hant"], self.recorded())


if __name__ == "__main__":
    unittest.main()
