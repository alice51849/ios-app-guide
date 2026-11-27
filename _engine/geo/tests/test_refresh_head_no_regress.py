#!/usr/bin/env python3
"""--refresh 重產時,已翻好的頁首欄位(h1/title/導言/App Store 按鈕/揭露)不可退回英文。

重產從英文原頁＋共用字典整頁重寫;字典永遠學不到 <h1>/<title>
(i18n_harvest_existing.page_link_labels 刻意排除),所以整頁覆蓋率提升時
已上線的 h1 會被寫回英文,目錄 publisher_query 就變成英文而被
alternatives_i18n.load_catalog 擋下。
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

GEO = Path(__file__).resolve().parent.parent
for extra in (GEO, GEO.parent / "social"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import aeo_answers_i18n as i18n  # noqa: E402

SLUG = "best-quiet-checklist-app"
APP_ID = "1000000001"
H1_EN = "best quiet checklist app"
TITLE_EN = "best quiet checklist app: honest iPhone app buying guide"
BODY_EN = [
    "A checklist should open instantly and stay out of the way.",
    "Reminders arrive at the time you set, nothing more.",
    "Lists sync between your devices without an account.",
    "There are no streaks, badges or productivity scores.",
]
H1_ZH = "最安靜的待辦清單 App"
TITLE_ZH = "最安靜的待辦清單 App：誠實的 iPhone App 選購指南"
BODY_ZH = [
    "待辦清單應該一打開就能用，而且不打擾你。",
    "提醒只會在你設定的時間出現。",
    "清單在你的裝置之間同步，不需要帳號。",
    "沒有連續天數、徽章或生產力分數。",
]
LEAD_EN = "Pick the list that does less, on purpose."
LEAD_ZH = "選一個刻意少做一點的清單。"


def _jsonld(app_id: str) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "MobileApplication",
                "identifier": {
                    "@type": "PropertyValue",
                    "propertyID": "Apple App Store ID",
                    "value": app_id,
                },
            }
        )
        + "</script>"
    )


def _page(
    lang: str,
    title: str,
    h1: str,
    lead: str,
    body: list[str],
    *,
    app_id: str = APP_ID,
    h1_markup: str | None = None,
) -> str:
    paragraphs = "".join(f"<p>{x}</p>" for x in body)
    return (
        f'<!doctype html><html lang="{lang}"><head><title>{title}</title>'
        f'<meta property="og:title" content="{title}">'
        f"{_jsonld(app_id)}</head><body><main>"
        f'<h1 class="p-name">{h1_markup or h1}</h1>'
        f'<p class="lead p-summary">{lead}</p>'
        f'<p><a class="cta" href="https://apps.apple.com/us/app/id{app_id}">Get it</a></p>'
        f"{paragraphs}</main></body></html>"
    )


class RefreshHeadNoRegressTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.trans = self.root / "_trans"
        self.trans.mkdir()
        (self.root / "answers").mkdir()
        self.source = _page("en", TITLE_EN, H1_EN, LEAD_EN, BODY_EN)
        (self.root / "answers" / f"{SLUG}.html").write_text(self.source, encoding="utf-8")
        patches = [
            mock.patch.object(i18n, "ROOT", self.root),
            mock.patch.object(i18n, "ANSWERS", self.root / "answers"),
            # The site-wide paid-upfront pass needs the real inventory; it
            # is not what this test is about.
            mock.patch.object(
                i18n.paid_upfront_surfaces, "rewrite", side_effect=lambda s, *_a, **_k: s
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self._tmp.cleanup)

    def _existing(self, lang: str, page: str) -> Path:
        path = self.root / lang / "answers" / f"{SLUG}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding="utf-8")
        return path

    def _dictionary(self, lang: str, entries: dict[str, str]) -> None:
        (self.trans / f"{lang}.json").write_text(
            json.dumps(entries, ensure_ascii=False), encoding="utf-8"
        )

    def _refresh(self, langs: list[str]) -> dict:
        out = io.StringIO()
        self.report = self.root / "_report" / "refresh_guarded.json"
        with redirect_stdout(out):
            i18n.run_refresh(
                langs, str(self.trans), slugs=[SLUG], guarded_report=self.report
            )
        self.stdout = out.getvalue()
        return json.loads(self.stdout.strip().splitlines()[-1])

    def _set_source(self, page: str) -> None:
        self.source = page
        (self.root / "answers" / f"{SLUG}.html").write_text(page, encoding="utf-8")

    def _published_zh(self, **kwargs) -> str:
        # Head translated, body still half English: the shape of the live
        # mochi catalog page before the failed geo-daily run.
        return _page(
            "zh-Hant", TITLE_ZH, H1_ZH, LEAD_ZH, BODY_ZH[:1] + BODY_EN[1:], **kwargs
        )

    def _body_dictionary(self) -> dict[str, str]:
        return dict(zip(BODY_EN, BODY_ZH))

    def test_translated_h1_and_title_survive_a_body_refresh(self) -> None:
        target = self._existing("zh-Hant", self._published_zh())
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(1, summary["refreshed"])
        page = target.read_text(encoding="utf-8")
        for text in BODY_ZH:
            self.assertIn(text, page)  # body coverage really improved
        self.assertIn(f"<title>{TITLE_ZH}</title>", page)
        self.assertIn(f'content="{TITLE_ZH}"', page)  # og:title too
        self.assertIn(f">{H1_ZH}</h1>", page)
        self.assertIn(f">{LEAD_ZH}</p>", page)
        self.assertNotIn(H1_EN, page)

    def test_dictionary_translation_still_replaces_the_published_one(self) -> None:
        target = self._existing("zh-Hant", self._published_zh())
        newer = "最安靜、最好用的待辦清單 App"
        self._dictionary("zh-Hant", {**self._body_dictionary(), H1_EN: newer})
        self._refresh(["zh-Hant"])
        page = target.read_text(encoding="utf-8")
        self.assertIn(f">{newer}</h1>", page)
        self.assertNotIn(f">{H1_ZH}</h1>", page)

    def test_no_gain_still_means_no_rewrite(self) -> None:
        published = self._published_zh()
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", {})
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(0, summary["refreshed"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))

    def test_gain_gate_ignores_units_kept_from_the_published_page(self) -> None:
        # Preservation must not turn a below-threshold page into a rewrite.
        mapping = {x: x for x in i18n.extract_strings(self.source)[0]}
        published = self._published_zh()
        before = i18n._untranslated_ratio(list(mapping), mapping)
        kept, fields, conflicts = i18n.preserve_localized_head_fields(
            self.source, published, mapping, lang="zh-Hant", slug=SLUG
        )
        self.assertEqual([], conflicts)
        self.assertEqual({"h1", "lead", "title"}, set(fields))
        self.assertLess(i18n._untranslated_ratio(list(mapping), kept), before)
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", {})
        self.assertEqual(0, self._refresh(["zh-Hant"])["refreshed"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))

    def test_unpairable_head_keeps_the_whole_page(self) -> None:
        # Published <h1> is split by markup: no positional pairing is safe,
        # so the backstop keeps the page instead of writing English.
        published = self._published_zh(h1_markup="最安靜的<em>待辦清單</em> App")
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(0, summary["refreshed"])
        self.assertEqual(1, summary["guarded"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))

    def test_page_promoting_another_app_is_not_reassigned(self) -> None:
        published = self._published_zh(app_id="1000000002")
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(1, summary["guarded"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))

    def test_english_published_head_is_not_invented(self) -> None:
        # Nothing to preserve: an English h1 stays English, body refreshes.
        target = self._existing(
            "zh-Hant",
            _page("zh-Hant", TITLE_EN, H1_EN, LEAD_EN, BODY_ZH[:1] + BODY_EN[1:]),
        )
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(1, summary["refreshed"])
        page = target.read_text(encoding="utf-8")
        self.assertIn(f">{H1_EN}</h1>", page)
        self.assertIn(BODY_ZH[-1], page)

    def test_english_locale_and_other_locales_are_independent(self) -> None:
        english = _page("en-GB", TITLE_EN, H1_EN, LEAD_EN, BODY_EN)
        en_target = self._existing("en-GB", english)
        zh_target = self._existing("zh-Hant", self._published_zh())
        ja_published = _page("ja", TITLE_EN, H1_EN, LEAD_EN, BODY_EN)
        ja_target = self._existing("ja", ja_published)
        self._dictionary("zh-Hant", self._body_dictionary())
        self._dictionary("ja", {})
        self._refresh(["en-GB", "zh-Hant", "ja"])
        self.assertEqual(english, en_target.read_text(encoding="utf-8"))
        self.assertEqual(ja_published, ja_target.read_text(encoding="utf-8"))
        # zh-Hant head never leaks into another locale's mapping.
        self.assertIn(f">{H1_ZH}</h1>", zh_target.read_text(encoding="utf-8"))
        self.assertNotIn(H1_ZH, ja_target.read_text(encoding="utf-8"))

    def test_dictionary_mapping_to_older_english_is_not_a_translation(self) -> None:
        # Harvest can pair the new English lead with the older English lead
        # still on the en-US page; that is English, so the published
        # translation must stay (the catalog compares against en-US).
        older = "Pick the list that does less."
        self._existing("en-US", _page("en-US", TITLE_EN, H1_EN, older, BODY_EN))
        target = self._existing("zh-Hant", self._published_zh())
        self._dictionary("zh-Hant", {**self._body_dictionary(), LEAD_EN: older})
        self.assertEqual(1, self._refresh(["zh-Hant"])["refreshed"])
        page = target.read_text(encoding="utf-8")
        self.assertIn(f">{LEAD_ZH}</p>", page)
        self.assertNotIn(older, page)

    def test_changed_price_never_leaves_an_old_price_in_the_head(self) -> None:
        # English lead moved $2.99 -> $3.99 and the dictionary has no entry for
        # the new sentence: keeping the old translation would print the old
        # price next to fresh body copy, so the whole page is kept instead.
        self._set_source(
            _page("en", TITLE_EN, H1_EN, "Pick the list for $3.99.", BODY_EN)
        )
        published = _page(
            "zh-Hant", TITLE_ZH, H1_ZH, "選一個 $2.99 的清單。",
            BODY_ZH[:1] + BODY_EN[1:],
        )
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(0, summary["refreshed"])
        self.assertEqual(1, summary["guarded"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(1, report["guarded"])
        self.assertEqual(
            {"locale": "zh-Hant", "slug": SLUG, "reasons": ["lead"],
             "conflicts": ["lead:price_or_number"]},
            report["pages"][0],
        )

    def test_unpinned_purchase_wording_is_never_kept(self) -> None:
        # "one-time"/"subscription" cannot be compared across languages.
        lead = "One-time unlock, no subscription."
        self._set_source(_page("en", TITLE_EN, H1_EN, lead, BODY_EN))
        published = _page(
            "zh-Hant", TITLE_ZH, H1_ZH, "一次買斷，沒有訂閱。",
            BODY_ZH[:1] + BODY_EN[1:],
        )
        target = self._existing("zh-Hant", published)
        self._dictionary("zh-Hant", self._body_dictionary())
        summary = self._refresh(["zh-Hant"])
        self.assertEqual(1, summary["guarded"])
        self.assertIn("lead:purchase_wording", self.stdout)
        self.assertEqual(published, target.read_text(encoding="utf-8"))

    def test_claim_tokens_compare_numbers_currency_and_free_pro(self) -> None:
        conflict = i18n._keep_conflict
        self.assertIsNone(conflict("lead", "Lists for 2 devices.", "兩台裝置的 2 份清單。", None))
        self.assertEqual("price_or_number", conflict("lead", "Works on 3 devices.", "支援 2 台裝置。", None))
        self.assertEqual("price_or_number", conflict("lead", "Costs €3", "售價 $3", None))
        self.assertIsNone(conflict("app_store_cta", "Pay 2.99", "ادفع ٢٫٩٩", None))
        self.assertEqual("free_pro", conflict("lead", "Pro tips inside.", "內有 Free 技巧。", None))
        # A pinned h1 query may translate its own "free"/"subscription".
        self.assertIsNone(
            conflict("h1", "best free app no subscription", "最佳免費無訂閱 App",
                     "best free app no subscription")
        )
        self.assertIsNotNone(
            conflict("h1", "best free app no subscription", "最佳免費無訂閱 App", None)
        )
        self.assertEqual(
            "purchase_wording",
            conflict("h1", "best app no subscription", "最佳無訂閱 App", None),
        )

    def test_locale_meta_frame_quoting_the_pinned_query_is_kept(self) -> None:
        q = H1_EN
        frame = f"«{q}» — 實用解答與選購前要確認的事。"
        self.assertIsNone(
            i18n._keep_conflict("meta:description", "Pick a list for $3.99 today.", frame, q)
        )
        # ...but a frame that adds its own number or Free/Pro claim is not.
        self.assertEqual(
            "price_or_number",
            i18n._keep_conflict("meta:description", "Pick a list.", f"«{q}» 只要 3 元", q),
        )
        self.assertEqual(
            "free_pro",
            i18n._keep_conflict("meta:description", "Pick a list.", f"«{q}» Free", q),
        )
        # Without a pinned query a frame is compared like any translation.
        self.assertIsNotNone(
            i18n._keep_conflict("meta:description", "Pick a list for $3.99.", frame, None)
        )

    def test_catalog_field_never_becomes_byte_equal_to_en_us(self) -> None:
        # The published ja lead is an older English wording (not a
        # translation, so nothing is kept) -- but re-rendering it to the
        # current en-US lead would trip the catalog's English-fallback check,
        # so the page stays as published.
        self._existing("en-US", _page("en-US", TITLE_EN, H1_EN, LEAD_EN, BODY_EN))
        published = _page(
            "ja", "静かなチェックリスト", "静かなチェックリストアプリ",
            "An older English lead.", BODY_EN,
        )
        target = self._existing("ja", published)
        self._dictionary("ja", dict(zip(BODY_EN, (
            "チェックリストはすぐ開くべきです。",
            "リマインダーは設定した時刻に届きます。",
            "アカウントなしで端末間で同期します。",
            "連続記録やバッジ、生産性スコアはありません。",
        ))))
        summary = self._refresh(["ja"])
        self.assertEqual(1, summary["guarded"])
        self.assertEqual(published, target.read_text(encoding="utf-8"))
        self.assertEqual(["lead"], json.loads(self.report.read_text())["pages"][0]["reasons"])

    def test_ad_free_is_not_a_free_claim(self) -> None:
        self.assertEqual([], i18n._latin_claims("Ad-free, sugar-free lists"))
        self.assertEqual(["free", "pro"], i18n._latin_claims("Free to start, Pro later"))

    def test_case_only_english_h1_is_not_kept(self) -> None:
        target = self._existing(
            "zh-Hant",
            _page("zh-Hant", TITLE_ZH, "Best  Quiet Checklist App", LEAD_ZH,
                  BODY_ZH[:1] + BODY_EN[1:]),
        )
        self._dictionary("zh-Hant", self._body_dictionary())
        self.assertEqual(1, self._refresh(["zh-Hant"])["refreshed"])
        page = target.read_text(encoding="utf-8")
        self.assertIn(f">{H1_EN}</h1>", page)
        self.assertNotIn("Best  Quiet Checklist App", page)

    def test_latin_only_head_on_native_script_locale_is_english(self) -> None:
        # ja page whose h1 is some other English wording: not a translation.
        old_h1 = "Quiet checklist app for iPhone"
        target = self._existing(
            "ja",
            _page("ja", TITLE_EN, old_h1, LEAD_EN, BODY_EN),
        )
        self._dictionary("ja", {BODY_EN[0]: "チェックリストはすぐ開くべきです。",
                                BODY_EN[1]: "リマインダーは設定した時刻に届きます。"})
        self.assertEqual(1, self._refresh(["ja"])["refreshed"])
        page = target.read_text(encoding="utf-8")
        self.assertIn(f">{H1_EN}</h1>", page)
        self.assertNotIn(old_h1, page)
        self.assertTrue(i18n._is_english(old_h1, set(), "ja"))
        self.assertFalse(i18n._is_english(old_h1, set(), "de-DE"))

    def test_many_guarded_pages_raise_a_warning(self) -> None:
        out = io.StringIO()
        pages = [
            {"locale": "ja", "slug": f"s{i}", "reasons": ["app_owner"], "conflicts": []}
            for i in range(i18n.GUARDED_WARN_COUNT)
        ]
        with redirect_stdout(out):
            i18n._report_guarded(pages, 1000, None)
        self.assertTrue(out.getvalue().startswith("::warning::"))
        out = io.StringIO()
        with redirect_stdout(out):
            i18n._report_guarded(pages[:1], 1000, None)
        self.assertFalse(out.getvalue().startswith("::warning::"))

    def test_regression_detector_flags_framed_english_title(self) -> None:
        published = self._published_zh()
        rendered = published.replace(
            f"<title>{TITLE_ZH}</title>", f"<title>{H1_EN}｜選購指南</title>"
        )
        self.assertEqual(
            ["title"], i18n.regressed_head_fields(self.source, published, rendered)
        )
        self.assertEqual(
            [], i18n.regressed_head_fields(self.source, published, published)
        )


if __name__ == "__main__":
    unittest.main()
