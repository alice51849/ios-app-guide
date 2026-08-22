#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QR 圖檔必須永遠編碼它旁邊那條連結 —— 產生器不可鑄造過時的 campaign token。

背景(2026-08-20):`gen_app_store_qr_ctas.py` 依「URL 的 sha256」命名 SVG,所以
一張 QR 只對它當下那條 URL 有效。同一條鏈裡 `gen_store_attribution.py` 跑在最後
並重寫所有商店連結;那天 `gen_app_decision_cards.py` 仍鑄造分類收斂前的舊
token `iag_decision`,於是 QR 圖鎖在 `ct=iag_decision`、按鈕卻被改成
`ct=geo_pick`。使用者掃碼與點擊會被歸到不同 campaign,而唯一的症狀是
`test_growth_infra` 吐出 2,100 條看不出原因的 assertion,整條雲端鏈卡兩天。

守兩件事(fail-closed):
1. 任何寫進頁面的 campaign token 都必須等於 `campaign_token()` 對該頁算出的值,
   也就是 attribution 之後不會再變 —— 這裡以 decision card 為代表;
2. 萬一又有人鑄造出會被改寫的 token,`gen_store_attribution` 必須在**製造出
   失步的當下**就炸掉並指名頁面,而不是留給下游閘門去猜。
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
ROOT = os.path.dirname(GEO)
sys.path.insert(0, GEO)
sys.path.insert(0, os.path.join(ROOT, "social"))

import gen_app_decision_cards  # noqa: E402
import gen_app_store_qr_ctas  # noqa: E402
import gen_store_attribution  # noqa: E402


def _page(href: str, digest: str) -> str:
    return (
        "<html><head></head><body>"
        f'<a class="app-store-qr-card__link" href="{href}" '
        'rel="nofollow noopener">'
        '<img class="app-store-qr-card__image" '
        f'src="/ios-app-guide/assets/app-store-qr/id6791658210-{digest}.svg" '
        'width="164" height="164" alt="" decoding="async">'
        "</a></body></html>"
    )


def _digest(url: str) -> str:
    relative = gen_app_store_qr_ctas.qr_asset_relative("6791658210", url)
    return relative.stem.split("-", 1)[1]


class DecisionCardCampaignTests(unittest.TestCase):
    def test_decision_cards_mint_the_token_attribution_would_produce(self):
        """Decision cards 不可鑄造 attribution 會再改掉的 token。"""
        import pathlib

        pages = pathlib.Path("/pages")
        for relative, expected in (
            ("ar-SA/aibriefpack.html", "geo_pick"),
            ("ar-SA/answers/best-productivity-app.html", "geo_ask"),
            ("ja/guides/how-to.html", "geo_learn"),
            ("aibriefpack.html", "geo_pick"),
        ):
            with self.subTest(page=relative):
                minted = gen_app_decision_cards.page_campaign(
                    pages / relative, pages
                )
                self.assertEqual(expected, minted)
                self.assertEqual(
                    gen_store_attribution.campaign_token(relative), minted
                )
                self.assertFalse(
                    minted.startswith("iag_"),
                    "legacy iag_* tokens get rewritten by the attribution "
                    "pass, which outdates every QR image minted from them",
                )


class QrCardDesyncGuardTests(unittest.TestCase):
    STORE = "https://apps.apple.com/sa/app/id6791658210"

    def test_matching_card_is_not_flagged(self):
        href = f"{self.STORE}?pt=118326163&amp;ct=geo_pick&amp;mt=8"
        url = f"{self.STORE}?pt=118326163&ct=geo_pick&mt=8"
        self.assertIsNone(
            gen_store_attribution.qr_card_desync(_page(href, _digest(url)))
        )

    def test_stale_image_is_reported_with_both_digests(self):
        href = f"{self.STORE}?pt=118326163&amp;ct=geo_pick&amp;mt=8"
        stale = _digest(f"{self.STORE}?pt=118326163&ct=iag_decision&mt=8")
        found = gen_store_attribution.qr_card_desync(_page(href, stale))
        self.assertIsNotNone(found)
        self.assertEqual(stale, found[1])
        self.assertEqual(
            _digest(f"{self.STORE}?pt=118326163&ct=geo_pick&mt=8"), found[2]
        )

    def test_page_without_a_qr_card_is_ignored(self):
        self.assertIsNone(
            gen_store_attribution.qr_card_desync(
                f'<html><body><a href="{self.STORE}">x</a></body></html>'
            )
        )

    def test_generate_fails_closed_when_it_would_outdate_a_qr_image(self):
        """製造出失步的當下就要炸,不可留給下游閘門。"""
        import pathlib
        import tempfile

        legacy = f"{self.STORE}?pt=118326163&ct=iag_decision&mt=8"
        page = _page(legacy.replace("&", "&amp;"), _digest(legacy))
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "ar-SA").mkdir()
            (root / "ar-SA" / "aibriefpack.html").write_text(
                page, encoding="utf-8"
            )
            previous = os.environ.get(
                gen_store_attribution.PROVIDER_TOKEN_ENV
            )
            os.environ[gen_store_attribution.PROVIDER_TOKEN_ENV] = "118326163"
            try:
                with self.assertRaises(
                    gen_store_attribution.QrCardDesyncError
                ) as caught:
                    gen_store_attribution.generate(root, check=True)
            finally:
                if previous is None:
                    os.environ.pop(
                        gen_store_attribution.PROVIDER_TOKEN_ENV, None
                    )
                else:
                    os.environ[
                        gen_store_attribution.PROVIDER_TOKEN_ENV
                    ] = previous
        message = str(caught.exception)
        self.assertIn("ar-SA/aibriefpack.html", message)
        self.assertIn("campaign_token()", message)


if __name__ == "__main__":
    unittest.main()
