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
import pathlib
import sys
import tempfile
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


def _module_source(module_name: str) -> str:
    with open(
        os.path.join(GEO, module_name + ".py"), encoding="utf-8"
    ) as handle:
        return handle.read()


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


class QrEligiblePageFamilyTests(unittest.TestCase):
    """QR 卡只長在這五個頁面家族;每個家族的產生器都必須用最終 token。

    2026-08-20 第二次踩到同一顆雷:decision card 修好之後,`gen_hubs.py`
    (`iag_hub`)與 `aeo_pages.py`(`iag_alt`)還在自己鑄 token,雲端鏈就
    卡在 `alternatives/gmoneylite-vs-tricount.html`。QR 卡的連結取自頁面
    「第一條」商店連結(`gen_mobile_store_ctas.app_store_cta`),所以只要
    任何一個家族的產生器鑄出 attribution 會再改掉的 token,那一頁的 QR 圖
    就會過期。這裡把家族與其擁有者釘住,讓下一個犯規在單元測試就現形,
    不必等雲端跑 40 分鐘才炸一頁。
    """

    # section -> (module name, expected bucket token)
    FAMILIES = {
        "answers": ("aeo_answers", "geo_ask"),
        "guides": ("aeo_guide", "geo_learn"),
        "hubs": ("gen_hubs", "geo_pick"),
        "alternatives": ("aeo_pages", "geo_pick"),
    }

    def test_sections_match_the_qr_eligible_surface(self):
        """家族清單必須跟 QR 產生器實際掛卡的地方一致。"""
        import gen_smart_app_banners

        self.assertEqual(
            set(gen_smart_app_banners.BUYER_INTENT_SECTIONS)
            | {"guides"},
            set(self.FAMILIES),
        )

    def test_each_family_generator_mints_the_final_token(self):
        for section, (module_name, expected) in self.FAMILIES.items():
            with self.subTest(section=section):
                self.assertEqual(
                    expected,
                    gen_store_attribution.campaign_token(
                        f"{section}/page.html"
                    ),
                )
                text = _module_source(module_name)
                self.assertNotIn(
                    '"iag_',
                    text,
                    f"{module_name}.py mints a legacy campaign token; the "
                    "attribution pass rewrites it after gen_app_store_qr_ctas "
                    "has already hashed it into the QR image name",
                )

    def test_localized_app_pages_use_the_final_token(self):
        """`<locale>/<app>.html` 也掛 QR 卡(_guide_pages 收了它)。"""
        import build_pages_i18n

        self.assertEqual(
            "geo_pick",
            gen_store_attribution.campaign_token("ja/lumibopomofo.html"),
        )
        text = _module_source("build_pages_i18n")
        self.assertNotIn('"iag_', text)
        self.assertTrue(hasattr(build_pages_i18n, "gen_store_attribution"))

    def test_campaign_constants_agree_with_the_attribution_authority(self):
        import aeo_answers
        import aeo_guide
        import gen_roundups

        for module, constant, relative in (
            (aeo_answers, "ANSWER_CAMPAIGN", "answers/page.html"),
            (aeo_guide, "GUIDE_CAMPAIGN", "guides/page.html"),
            # roundups are published into answers/, so they share ASK
            (gen_roundups, "ROUNDUP_CAMPAIGN", "answers/page.html"),
        ):
            with self.subTest(module=module.__name__):
                minted = getattr(module, constant)
                self.assertEqual(
                    gen_store_attribution.campaign_token(relative), minted
                )
                self.assertFalse(minted.startswith("iag_"))

    def test_alternatives_landing_url_survives_the_attribution_pass(self):
        """landing_url() 產出的連結,attribution 必須一個字都不用改。"""
        import aeo_pages

        previous = os.environ.get(gen_store_attribution.PROVIDER_TOKEN_ENV)
        os.environ[gen_store_attribution.PROVIDER_TOKEN_ENV] = "118326163"
        try:
            key = next(
                k
                for k in aeo_pages.APPS
                if aeo_pages.APPSTORE.get(k)
            )
            url = aeo_pages.landing_url(key)
            self.assertIn("ct=geo_pick", url)
            anchor = f'<a class="app-store-qr-card__link" href="{url}">x</a>'
            _, changes = gen_store_attribution.rewrite(
                anchor,
                gen_store_attribution.campaign_token(
                    "alternatives/page.html"
                ),
                "118326163",
            )
            self.assertEqual(0, changes)
        finally:
            if previous is None:
                os.environ.pop(
                    gen_store_attribution.PROVIDER_TOKEN_ENV, None
                )
            else:
                os.environ[
                    gen_store_attribution.PROVIDER_TOKEN_ENV
                ] = previous

    def test_publisher_visual_campaigns_are_not_restamped(self):
        visual_url = (
            "https://apps.apple.com/us/app/id6791658210"
            "?pt=118326163&amp;ct=iag_visual_en_us&amp;mt=8"
        )
        guide_url = "https://apps.apple.com/us/app/id6791658210"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            visual_paths = (
                root / "visuals" / "index.html",
                root / "ja" / "visuals" / "index.html",
            )
            for path in visual_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f'<a href="{visual_url}">Visual</a>',
                    encoding="utf-8",
                )
            guide = root / "guides" / "page.html"
            guide.parent.mkdir()
            guide.write_text(
                f'<a href="{guide_url}">Guide</a>',
                encoding="utf-8",
            )

            previous = os.environ.get(
                gen_store_attribution.PROVIDER_TOKEN_ENV
            )
            os.environ[
                gen_store_attribution.PROVIDER_TOKEN_ENV
            ] = "118326163"
            try:
                result = gen_store_attribution.generate(root, check=False)
            finally:
                if previous is None:
                    os.environ.pop(
                        gen_store_attribution.PROVIDER_TOKEN_ENV, None
                    )
                else:
                    os.environ[
                        gen_store_attribution.PROVIDER_TOKEN_ENV
                    ] = previous

            for path in visual_paths:
                self.assertIn(
                    "ct=iag_visual_en_us",
                    path.read_text(encoding="utf-8"),
                )
            self.assertIn(
                "ct=geo_learn",
                guide.read_text(encoding="utf-8"),
            )
            self.assertEqual(1, result["pages_with_store_anchors"])


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
