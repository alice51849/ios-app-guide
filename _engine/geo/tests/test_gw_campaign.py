#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""意圖頁追蹤碼（款 × 國家 × 詞群 的 gw 階梯碼）：形狀、階梯、每日改寫保留、稽核、QR 同步、每週開格。

背景：2026-10-23 一億品質監督第 1 次報告 3.1。意圖頁一律被每日改寫蓋成 geo_ask／geo_pick，
蘋果報表分不出詞群與國家；一頁一碼又永遠過不了蘋果 5 次下載的顯示門檻。
"""
from __future__ import annotations

import collections
import datetime as dt
import os
from pathlib import Path
import sys
import unittest
import urllib.parse

GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parent
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(ROOT / "social"))

import gw_campaign as gw  # noqa: E402
import gen_store_attribution  # noqa: E402
from audit_store_attribution import AttributionError, Reference, validate_reference  # noqa: E402

PROVIDER = "118326163"
MOCHI_ID = "6785004775"
AIBRIEF_ID = "6791658210"
PLAN = {"schema": gw.SCHEMA, "generated_at": "2026-10-23T00:00:00Z", "min_weekly_downloads": 5.0,
        "apps": {"mochi": {"cells": [["sr", "us"], ["all", "jp"], ["ss", "ww"]]}}}


def ct_of(url: str) -> str:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))["ct"]


class ShapeAndLadderTests(unittest.TestCase):
    def test_default_plan_is_one_code_per_app(self):
        empty = {"schema": gw.SCHEMA, "apps": {}}
        self.assertEqual("ln_mochi_all_ww_gw", gw.campaign("mochi", "sr", "us", empty))
        self.assertEqual("ln_mochi_all_ww_gw", gw.campaign("mochi", "ss", None, empty))

    def test_ladder_opens_only_planned_cells_country_before_group(self):
        self.assertEqual("ln_mochi_sr_us_gw", gw.campaign("mochi", "sr", "us", PLAN))
        self.assertEqual("ln_mochi_all_jp_gw", gw.campaign("mochi", "ss", "jp", PLAN))   # 國家優先
        self.assertEqual("ln_mochi_ss_ww_gw", gw.campaign("mochi", "ss", "de", PLAN))
        self.assertEqual("ln_mochi_all_ww_gw", gw.campaign("mochi", "alt", "de", PLAN))
        self.assertEqual("ln_scanto_all_ww_gw", gw.campaign("scanto", "sr", "us", PLAN))

    def test_long_key_uses_short_code_and_parses_back_to_the_roster_key(self):
        value = gw.token("duowallpaperstudio", "alt", "ww")
        self.assertEqual("ln_duowallpaper_alt_ww_gw", value)
        self.assertEqual("duowallpaperstudio", gw.parse(value)["app"])
        self.assertEqual([], gw.link_problems(value, app_key="duowallpaperstudio", storefront="us"))
        self.assertTrue(gw.link_problems(value, app_key="mochi", storefront="us"))

    def test_longest_roster_key_fits_the_30_character_limit_without_a_date(self):
        from live_app_manifest import canonical_manifest

        for key in canonical_manifest()["apps"]:
            for group in gw.GROUPS:
                value = gw.token(key, group, "ww")
                self.assertLessEqual(len(value), gw.MAX_TOKEN, value)
                self.assertNotRegex(value, r"_\d{4}$")

    def test_bad_inputs_fail_closed(self):
        for args in (("Mochi", "sr", "us"), ("mochi", "seo", "us"), ("mochi", "sr", "usa")):
            with self.subTest(args=args), self.assertRaises(gw.GwCampaignError):
                gw.campaign(*args, plan=PLAN)
        with self.assertRaises(gw.GwCampaignError):
            gw.validate_plan({"schema": gw.SCHEMA, "apps": {"mochi": {"cells": [["all", "ww"]]}}})
        with self.assertRaises(gw.GwCampaignError):
            gw.page_group('<meta name="growth-attribution-group" content="seo">')

    def test_channel_reader_files_gw_codes_under_geo_pages(self):
        try:
            sys.path.insert(0, str(ROOT / "agent"))
            import ct_codes  # 00_GrowthEngine only; the Guide mirror has no agent/
        except ImportError:
            self.skipTest("agent/ct_codes.py not in this tree")
        for value in ("ln_mochi_all_ww_gw", "ln_mochi_sr_us_gw", "ln_lumibopomofopro_alt_ww_gw"):
            self.assertEqual("geo_pages", ct_codes.channel_for_ct(value))
            self.assertEqual([], ct_codes.ct_problems(value))

    def test_link_problems_check_app_and_storefront(self):
        self.assertEqual([], gw.link_problems("ln_mochi_sr_us_gw", app_key="mochi", storefront="us"))
        self.assertEqual([], gw.link_problems("ln_mochi_all_ww_gw", app_key="mochi", storefront="jp"))
        self.assertTrue(gw.link_problems("ln_mochi_sr_us_gw", app_key="mochi", storefront="jp"))
        self.assertTrue(gw.link_problems("ln_mochi_sr_us_gw", app_key="scanto", storefront="us"))
        self.assertTrue(gw.link_problems("ln_mochi_sr_us_gw_1023", app_key="mochi", storefront="us"))


class DailyRewriteTests(unittest.TestCase):
    """每日改寫（gen_store_attribution）不再把意圖頁蓋成 geo_*。"""

    def setUp(self):
        os.environ["GW_CAMPAIGN_PLAN"] = str(GEO / "tests" / "_no_such_gw_plan.json")  # 讀不到 → 預設計畫（每款一碼）

    def tearDown(self):
        os.environ.pop("GW_CAMPAIGN_PLAN", None)

    def page(self, href: str, group: str | None = None) -> str:
        meta = gw.meta_tag(group) if group else ""
        return (f"<html lang=\"en\"><head>{meta}</head><body>"
                f'<a class="cta" href="{href}">Get</a></body></html>')

    def rewrite(self, text: str, rel: str = "seasonal/x.html", locale: str | None = "en-US"):
        token = gen_store_attribution.page_token(rel, text)
        return gen_store_attribution.rewrite(text, token, PROVIDER, locale=locale)[0]

    def test_page_with_group_marker_gets_per_link_gw_code(self):
        href = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt={PROVIDER}&amp;ct=geo_pick&amp;mt=8"
        text = self.page(href, "ss")
        self.assertEqual("gw:ss:geo_pick", gen_store_attribution.page_token("seasonal/x.html", text))
        updated = self.rewrite(text)
        self.assertIn("ct=ln_mochi_all_ww_gw", updated)
        self.assertNotIn("geo_pick", updated)
        self.assertEqual(updated, self.rewrite(updated))  # 冪等

    def test_valid_gw_code_is_kept_without_marker_and_legacy_codes_are_rewritten(self):
        keep = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt={PROVIDER}&amp;ct=ln_mochi_sr_us_gw&amp;mt=8"
        self.assertIn("ct=ln_mochi_sr_us_gw&amp;", self.rewrite(self.page(keep)))
        for bad in ("ln_mochi_sr_us_gw_1023", "ln_scanto_sr_us_gw", "ln_mochi_sr_jp_gw"):
            href = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt={PROVIDER}&amp;ct={bad}&amp;mt=8"
            with self.subTest(ct=bad):
                updated = self.rewrite(self.page(href))
                self.assertIn("ct=geo_pick", updated)

    def test_final_store_url_is_the_same_for_qr_cards_and_anchors(self):
        text = self.page(f"https://apps.apple.com/us/app/id{MOCHI_ID}", "sr")
        token = gen_store_attribution.page_token("answers/x.html", text)
        url = gen_store_attribution.final_store_url(
            f"https://apps.apple.com/app/id{MOCHI_ID}", token, PROVIDER, locale="en-US", app_id=MOCHI_ID)
        self.assertEqual("ln_mochi_all_ww_gw", ct_of(url))
        anchor = self.rewrite(text, rel="answers/x.html")
        self.assertIn(f"ct={ct_of(url)}", anchor)

    def test_unknown_app_falls_back_to_the_page_bucket(self):
        self.assertEqual("geo_ask", gw.stamp_campaign("gw:sr:geo_ask", None,
                                                      "https://apps.apple.com/us/app/id1234567890", "1234567890"))


class RankedAnswersRetagTests(unittest.TestCase):
    """第 1、2、4 組（在榜詞母語答案頁）：補詞群標記、連結改 gw 碼、QR 圖跟著重算。"""

    def setUp(self):
        import tempfile

        import gen_app_store_qr_ctas as qr
        import gen_ranked_query_answers as ranked

        os.environ["GW_CAMPAIGN_PLAN"] = str(GEO / "tests" / "_no_such_gw_plan.json")
        self.tmp = tempfile.TemporaryDirectory()
        self.ranked, self.qr = ranked, qr
        self.saved = ranked.PAGES
        ranked.PAGES = Path(self.tmp.name)
        old = f"https://apps.apple.com/jp/app/id{MOCHI_ID}?pt={PROVIDER}&ct=geo_ask&mt=8"
        digest = qr.qr_asset_relative(MOCHI_ID, old).stem.split("-", 1)[1]
        esc = old.replace("&", "&amp;")
        self.page = (
            '<html lang="ja"><head>'
            f'<meta name="apple-itunes-app" content="app-id={MOCHI_ID}, affiliate-data=pt={PROVIDER}&amp;ct=geo_ask&amp;mt=8">'
            "</head><body>"
            f'<a class="cta" href="{esc}">App Store</a>'
            f'<a class="app-store-qr-card__link" href="{esc}" rel="nofollow noopener">'
            f'<img class="app-store-qr-card__image" src="/ios-app-guide/assets/app-store-qr/id{MOCHI_ID}-{digest}.svg"'
            ' width="164" height="164" alt="" decoding="async"></a></body></html>')

    def tearDown(self):
        self.ranked.PAGES = self.saved
        self.ranked.PENDING_QR_ASSETS.clear()
        os.environ.pop("GW_CAMPAIGN_PLAN", None)
        self.tmp.cleanup()

    def test_retag_moves_every_surface_to_the_gw_code_and_keeps_qr_in_sync(self):
        out = self.ranked.apply_gw_attribution(self.page, "ja/answers/x.html")
        self.assertIn(gw.meta_tag("sr"), out)
        self.assertNotIn("geo_ask", out)
        self.assertEqual(3, out.count("ct=ln_mochi_all_ww_gw"))
        self.assertIsNone(gen_store_attribution.qr_card_desync(out))
        (asset, svg), = self.ranked.PENDING_QR_ASSETS.items()
        self.assertIn(asset.name, out)
        self.assertIn("ln_mochi_all_ww_gw", svg)
        self.assertEqual(1, self.ranked.write_qr_assets())
        self.assertTrue((Path(self.tmp.name) / asset).is_file())
        # 再跑一次不變（每日改寫也不會再改它）
        self.assertEqual(out, self.ranked.apply_gw_attribution(out, "ja/answers/x.html"))
        token = gen_store_attribution.page_token("ja/answers/x.html", out)
        self.assertEqual(out, gen_store_attribution.rewrite(out, token, PROVIDER, locale="ja")[0])


class AuditTests(unittest.TestCase):
    def ref(self, url: str) -> Reference:
        return Reference(url, "href", "en-US", None, False, "html")

    def test_audit_accepts_valid_gw_and_rejects_mismatched_ones(self):
        ok = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt={PROVIDER}&ct=ln_mochi_sr_us_gw&mt=8"
        self.assertEqual("ln_mochi_sr_us_gw", validate_reference(self.ref(ok), provider=PROVIDER))
        for bad in ("ln_aibriefpack_sr_us_gw", "ln_mochi_sr_jp_gw", "ln_mochi_sr_us_gw_1023"):
            url = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt={PROVIDER}&ct={bad}&mt=8"
            with self.subTest(ct=bad), self.assertRaises(AttributionError):
                validate_reference(self.ref(url), provider=PROVIDER)


class WeeklyPlanTests(unittest.TestCase):
    KEYS = {MOCHI_ID: "mochi", AIBRIEF_ID: "aibriefpack"}

    def test_feedback_is_turned_into_weekly_web_referrer_by_country(self):
        feedback = {"window_days": 28, "apps": [{
            "app_id": MOCHI_ID,
            "by_source": [{"name": "Web Referrer", "first_time_downloads": 40},
                          {"name": "App Store Search", "first_time_downloads": 900}],
            "by_territory_source": [{"source": "WEB_REFERRER", "territory": "US", "first_time_downloads": 28},
                                    {"source": "web referrer", "territory": "JP", "first_time_downloads": 8}]}]}
        web = gw.web_referrer_weekly(feedback, self.KEYS)
        self.assertEqual({"*": 10.0, "us": 7.0, "jp": 2.0}, web["mochi"])

    def test_cells_open_only_when_expected_weekly_downloads_reach_five(self):
        web = {"mochi": {"*": 12.0, "us": 10.0, "jp": 2.0}, "aibriefpack": {"*": 1.0}}
        clicks = {"mochi": collections.Counter({("sr", "us"): 60, ("ss", "us"): 40, ("ss", "jp"): 20})}
        doc = gw.build_plan(web, clicks, dt.datetime(2026, 10, 23, tzinfo=dt.timezone.utc))
        cells = {tuple(c) for c in doc["apps"]["mochi"]["cells"]}
        # us: 10/週 → 國家格開；sr 占 us 的 60% → 6 ≥ 5 開；ss 占 40% → 4 不開；jp 2/週不開
        # 全球：sr 60/120×12=6 開；ss 60/120×12=6 開
        self.assertEqual({("all", "us"), ("sr", "us"), ("sr", "ww"), ("ss", "ww")}, cells)
        self.assertNotIn("aibriefpack", doc["apps"])
        self.assertEqual("ln_mochi_sr_us_gw", gw.campaign("mochi", "sr", "us", doc))
        self.assertEqual("ln_mochi_all_us_gw", gw.campaign("mochi", "ss", "us", doc))
        self.assertEqual("ln_mochi_ss_ww_gw", gw.campaign("mochi", "ss", "jp", doc))

    def test_click_cells_read_group_from_page_marker_and_country_from_locale(self):
        rows = [
            {"date": "2026-10-22", "page": "/ios-app-guide/ja/seasonal/a.html", "app": MOCHI_ID,
             "ct": "ln_mochi_all_ww_gw", "store": "apple", "clicks": "3"},
            {"date": "2026-10-22", "page": "/ios-app-guide/answers/b.html", "app": MOCHI_ID,
             "ct": "ln_mochi_all_ww_gw", "store": "apple", "clicks": "2"},
            {"date": "2026-10-22", "page": "/ios-app-guide/answers/c.html", "app": MOCHI_ID,
             "ct": "geo_ask", "store": "apple", "clicks": "9"},          # 沒有詞群標記的頁不算
            {"date": "2026-10-22", "page": "/ios-app-guide/ja/seasonal/a.html", "app": "com.x",
             "ct": "ln_mochi_all_ww_gw", "store": "play", "clicks": "5"},  # Play 點擊不算
        ]
        groups = {"/ios-app-guide/ja/seasonal/a.html": "ss", "/ios-app-guide/answers/b.html": "sr"}
        cells = gw.click_cells(rows, groups, self.KEYS, today=dt.date(2026, 10, 23))
        self.assertEqual(collections.Counter({("ss", "jp"): 3, ("sr", "us"): 2}), cells["mochi"])

    def test_plan_changes_at_most_weekly(self):
        now = dt.datetime(2026, 10, 23, tzinfo=dt.timezone.utc)
        self.assertTrue(gw.plan_due({"generated_at": None}, now))
        self.assertFalse(gw.plan_due({"generated_at": "2026-10-20T00:00:00Z"}, now))
        self.assertTrue(gw.plan_due({"generated_at": "2026-10-16T00:00:00Z"}, now))

    def test_committed_plan_is_valid(self):
        gw.validate_plan(gw.load_plan(gw.PLAN))


if __name__ == "__main__":
    unittest.main()
