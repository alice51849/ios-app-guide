#!/usr/bin/env python3
"""「最適合」欄的購買模式標籤要跟著頁面語系,而且不能把免費門頁寫成付費。

在地化答案頁的「最適合」欄是 aeo_answers.feature_list 以 "; " 串起的
`Paid download; Pay once; No subscription`。多數語系字典沒有逐字條目,
zh-Hant 等語系上線頁就留著英文;--refresh 又因整頁覆蓋率門檻不重產,
這一欄永遠不會被修到。
"""

from __future__ import annotations

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
import gen_free_first_links  # noqa: E402

LABEL = "Paid download; Pay once; No subscription"


def _page(app_id: str, label: str = LABEL) -> str:
    return (
        "<html><head><title>t</title></head><body>"
        f'<a href="https://apps.apple.com/app/id{app_id}">get</a>'
        f'<h2>最適合</h2><p class="muted">{label}</p>'
        "<p>Paid download</p></body></html>"
    )


class PurchaseLabelListTests(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.localized_purchase_label_list.cache_clear()

    def test_zh_hant_uses_native_wording(self) -> None:
        self.assertEqual(
            "付費下載；一次買斷；無訂閱",
            i18n.localized_purchase_label_list("zh-Hant"),
        )

    def test_label_comes_from_existing_longer_dictionary_entry(self) -> None:
        # ja 字典只有 `…; Home Screen widget` 長版條目:取前三段、沿用其分隔符。
        self.assertEqual(
            "有料ダウンロード、買い切り、サブスクなし",
            i18n.localized_purchase_label_list("ja"),
        )

    def test_english_locales_are_left_alone(self) -> None:
        for lang in ("en-US", "en-GB", ""):
            self.assertIsNone(i18n.localized_purchase_label_list(lang))

    def test_label_the_free_door_rewriter_cannot_undo_stays_english(self) -> None:
        with mock.patch.object(
            i18n, "_purchase_label_from_dictionary",
            return_value="Untranslatable paid; A; B",
        ):
            i18n.localized_purchase_label_list.cache_clear()
            self.assertIsNone(i18n.localized_purchase_label_list("zh-Hant"))

    def test_localized_label_is_still_rewritten_on_a_free_door(self) -> None:
        for lang in ("zh-Hant", "ja", "ko", "de-DE", "fr-FR"):
            label = i18n.localized_purchase_label_list(lang)
            if label is None:
                continue
            rewritten = label
            for paid, free in gen_free_first_links.purchase_model_rewrites(lang):
                rewritten = rewritten.replace(paid, free)
            self.assertNotEqual(label, rewritten, lang)

    def test_override_fills_untranslated_label_only(self) -> None:
        out = i18n.apply_locale_text_overrides({LABEL: LABEL}, "zh-Hant")
        self.assertEqual("付費下載；一次買斷；無訂閱", out[LABEL])
        kept = i18n.apply_locale_text_overrides({LABEL: "既有譯文"}, "zh-Hant")
        self.assertEqual("既有譯文", kept[LABEL])
        english = i18n.apply_locale_text_overrides({LABEL: LABEL}, "en-US")
        self.assertEqual(LABEL, english[LABEL])


class RelabelExistingPageTests(unittest.TestCase):
    def test_paid_door_page_label_is_localized_in_place(self) -> None:
        paid_id = sorted(gen_free_first_links.paid_door_ids())[0]
        page = _page(paid_id)
        out, count = i18n.relabel_purchase_label_lists(page, "zh-Hant")
        self.assertEqual(1, count)
        self.assertIn('<p class="muted">付費下載；一次買斷；無訂閱</p>', out)
        # 只換整段等於標籤的文字,其他字不動
        self.assertIn("<p>Paid download</p>", out)
        self.assertEqual(page.replace(LABEL, "付費下載；一次買斷；無訂閱"), out)

    def test_free_door_page_is_not_touched(self) -> None:
        _paid, free_id = gen_free_first_links.free_door_pair_ids()[0]
        page = _page(free_id)
        self.assertTrue(gen_free_first_links.is_free_door_page(page))
        self.assertEqual(
            (page, 0), i18n.relabel_purchase_label_lists(page, "zh-Hant")
        )

    def test_locale_without_safe_wording_is_not_touched(self) -> None:
        paid_id = sorted(gen_free_first_links.paid_door_ids())[0]
        page = _page(paid_id)
        self.assertEqual((page, 0), i18n.relabel_purchase_label_lists(page, "en-US"))

    def test_refresh_relabels_stale_page_without_rerendering(self) -> None:
        paid_id = sorted(gen_free_first_links.paid_door_ids())[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "answers").mkdir()
            (root / "zh-Hant" / "answers").mkdir(parents=True)
            slug = "stale-label"
            (root / "answers" / f"{slug}.html").write_text(
                _page(paid_id, "Free to start; One-time unlock; No subscription"),
                encoding="utf-8",
            )
            target = root / "zh-Hant" / "answers" / f"{slug}.html"
            target.write_text(_page(paid_id), encoding="utf-8")
            with mock.patch.object(i18n, "ROOT", root), mock.patch.object(
                i18n, "ANSWERS", root / "answers"
            ):
                i18n.run_refresh(
                    ["zh-Hant"], str(GEO / "i18n_trans"),
                    min_gain=1.0, slugs=[slug],
                )
            self.assertEqual(
                _page(paid_id, "付費下載；一次買斷；無訂閱"),
                target.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
