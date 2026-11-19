"""組合包連結（業主 11-20 組合包強力宣傳令）：app-bundle 網址放行、bundle_ 碼不重蓋成 geo_pick。"""
from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import app_store_storefronts as S  # noqa: E402
import audit_store_attribution as A  # noqa: E402
import gen_store_attribution as G  # noqa: E402
import market_availability  # noqa: E402

P = "118326163"
TRAVEL = "https://apps.apple.com/us/app-bundle/id6836190125"
LUMI = "https://apps.apple.com/{cc}/app-bundle/id6835757004"


def link(base: str, ct: str) -> str:
    return f"{base}?pt={P}&ct={ct}&mt=8"


def page(*hrefs: str) -> str:
    anchors = "".join(f'<a href="{h.replace("&", "&amp;")}">x</a>' for h in hrefs)
    return f'<!doctype html><html lang="en"><body>{anchors}</body></html>'


class BundleUrlContractTest(unittest.TestCase):
    def test_complete_bundle_link_is_accepted(self):
        url = link(TRAVEL, "bundle_travel_tblhome")
        self.assertTrue(S.is_app_bundle_url(url))
        self.assertEqual(url, S.validated_app_bundle_url(url, expected_locale="en-US", provider_token=P))

    def test_bundle_links_fail_closed(self):
        bad = (
            TRAVEL,                                                    # 沒有 pt/ct/mt
            link(TRAVEL, "geo_pick"),                                  # 不是 bundle_ 碼
            link(TRAVEL, "bundle_x_home"),                             # 不存在的包
            link(TRAVEL, "bundle_travel_this_code_is_far_too_long_x"), # 超過 30 字
            link("https://apps.apple.com/us/app-bundle/id1234567890", "bundle_travel_x"),  # 未讀回的包
            link("https://apps.apple.com/zz/app-bundle/id6836190125", "bundle_travel_x"),  # 不存在的店面
            link(TRAVEL, "bundle_travel_x") + "#top",
            link("http://apps.apple.com/us/app-bundle/id6836190125", "bundle_travel_x"),
        )
        for url in bad:
            with self.assertRaises(ValueError, msg=url):
                S.validated_app_bundle_url(url)
        with self.assertRaises(ValueError):
            S.validated_app_bundle_url(link(TRAVEL, "bundle_travel_x"), expected_locale="ja")
        with self.assertRaises(ValueError):
            S.validated_app_bundle_url(link(TRAVEL, "bundle_travel_x"), provider_token="999")

    def test_lumi_bundle_never_in_china(self):
        with self.assertRaises(market_availability.MarketUnavailable):
            S.validated_app_bundle_url(link(LUMI.format(cc="cn"), "bundle_lumi_home"))
        with self.assertRaises(market_availability.MarketUnavailable):
            S.validated_app_bundle_url(
                link("https://apps.apple.com/app-bundle/id6835757004", "bundle_lumi_home"), expected_locale="zh-Hans")
        with self.assertRaises(market_availability.MarketUnavailable):  # 判不出語系就擋
            S.validated_app_bundle_url(link("https://apps.apple.com/app-bundle/id6835757004", "bundle_lumi_home"))
        S.validated_app_bundle_url(
            link("https://apps.apple.com/app-bundle/id6835757004", "bundle_lumi_home"), expected_locale="en-US")
        S.validated_app_bundle_url(link("https://apps.apple.com/app-bundle/id6836190125", "bundle_travel_home"))
        S.validated_app_bundle_url(link(LUMI.format(cc="tw"), "bundle_lumi_home"), expected_locale="zh-Hant")

    def test_member_campaign_is_bound_to_its_bundle(self):
        self.assertTrue(S.bundle_member_campaign("bundle_travel_snapport_us", "6780575828"))
        self.assertTrue(S.bundle_member_campaign("bundle_lumi_home", "6779745474"))
        self.assertFalse(S.bundle_member_campaign("bundle_lang_home", "6780575828"))   # 別包的碼
        self.assertFalse(S.bundle_member_campaign("bundle_travel_home", "6779552704"))  # 非成員款
        self.assertFalse(S.bundle_member_campaign("geo_pick", "6780575828"))
        self.assertFalse(S.bundle_member_campaign("bundle_travel_home", None))
        for package, members in S.APP_BUNDLE_MEMBERS.items():
            self.assertTrue(members, package)


class BundleStampAndAuditTest(unittest.TestCase):
    def test_stamper_keeps_bundle_codes_and_restamps_others(self):
        bundle = link(TRAVEL, "bundle_travel_tblhome")
        member = link("https://apps.apple.com/us/app/id6780575828", "bundle_travel_snapport_us")
        outsider = link("https://apps.apple.com/us/app/id6779552704", "bundle_travel_snapport_us")
        out, _ = G.rewrite(page(bundle, member, outsider), "geo_pick", P, locale="en-US")
        self.assertIn("ct=bundle_travel_tblhome&amp;", out)
        self.assertIn("id6780575828?pt=118326163&amp;ct=bundle_travel_snapport_us&amp;", out)
        self.assertIn("id6779552704?pt=118326163&amp;ct=geo_pick&amp;", out)
        refs = A.audit_source(out, "en-US/bundles/travel.html", provider=P)
        self.assertEqual(3, len(refs))

    def test_stamper_blocks_bad_bundle_link(self):
        with self.assertRaises(ValueError):
            G.rewrite(page(link(TRAVEL, "geo_pick")), "geo_pick", P, locale="en-US")
        with self.assertRaises(ValueError):
            G.rewrite(page(link(TRAVEL, "bundle_travel_x")), "geo_pick", P, locale="ja")

    def test_audit_rejects_bad_bundle_link(self):
        for href, rel in ((link(TRAVEL, "geo_pick"), "en-US/bundles/a.html"),
                          (link(TRAVEL, "bundle_travel_x"), "ja/bundles/a.html"),
                          (TRAVEL, "en-US/bundles/a.html")):
            with self.assertRaises(ValueError, msg=href):
                A.audit_source(page(href, link("https://apps.apple.com/us/app/id6780575828", "geo_pick")),
                               rel, provider=P)


if __name__ == "__main__":
    unittest.main()
