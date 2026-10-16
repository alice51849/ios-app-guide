"""Existing-user App Store review links (BM-13 / BM-47).

``https://apps.apple.com/[cc/]app/id<N>?action=write-review`` is a narrow,
attribution-free link class: the stamper keeps it clean, the audit accepts it
only for live roster Apps, and every other non-campaign query stays rejected.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GEO), str(GEO.parent / "social")]

import answer_app_store_links  # noqa: E402
import check_hub_coverage  # noqa: E402
import app_store_storefronts as stores  # noqa: E402
import audit_store_attribution as audit  # noqa: E402
import gen_app_store_conversion_surfaces as surfaces  # noqa: E402
import gen_app_store_review_ctas as review  # noqa: E402
import gen_mobile_store_ctas  # noqa: E402
import gen_smart_app_banners  # noqa: E402
import gen_store_attribution as attribution  # noqa: E402
import hero_task_html  # noqa: E402
import market_availability as market  # noqa: E402
import normalize_app_store_links  # noqa: E402
from live_app_manifest import canonical_manifest  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PROVIDER = "123456789"
LIVE_APPS = {key: app["app_id"] for key, app in canonical_manifest()["apps"].items()}
AVAILABILITY = {
    country: frozenset(LIVE_APPS.values())
    for country in stores.LOCALE_STOREFRONTS.values()
}
USAGENOW = str(APPSTORE["claudeusagemini"])
REVIEW = f"https://apps.apple.com/app/id{USAGENOW}?action=write-review"
US_REVIEW = f"https://apps.apple.com/us/app/id{USAGENOW}?action=write-review"


def cta(locale="en-US", app_id=USAGENOW, campaign="geo_learn"):
    return stores.required_campaign_app_store_url(
        stores.localized_app_store_url(f"https://apps.apple.com/app/id{app_id}", locale),
        campaign, provider_token=PROVIDER, expected_locale=locale,
        expected_app_id=app_id, availability=AVAILABILITY,
    )


def page(review_href, *, locale="en", download=None):
    download = cta() if download is None else download
    return (
        f'<html lang="{locale}"><head></head><body><main>'
        f'<a class="cta" href="{html.escape(download, quote=True)}">Get</a>'
        "</main>"
        f'<p><a href="{html.escape(review_href, quote=True)}">Review</a></p>'
        "</body></html>"
    )


class ReviewUrlContractTests(unittest.TestCase):
    def test_only_the_exact_shape_is_a_review_link(self):
        self.assertEqual(REVIEW, stores.app_store_review_url(USAGENOW))
        self.assertTrue(stores.is_app_store_review_url(REVIEW))
        self.assertTrue(stores.is_app_store_review_url(US_REVIEW))
        for value in (
            f"{REVIEW}&ct=geo_ask",
            f"https://apps.apple.com/app/id{USAGENOW}?pt=1&ct=x&mt=8&action=write-review",
            f"https://apps.apple.com/app/id{USAGENOW}?action=write-review#x",
            f"https://apps.apple.com/app/id{USAGENOW}/?action=write-review",
            f"http://apps.apple.com/app/id{USAGENOW}?action=write-review",
            f"https://apps.apple.com/app/id{USAGENOW}?action=WRITE-REVIEW",
            f"https://apps.apple.com/app/id{USAGENOW}?action=open",
            f"https://apps.apple.com/US/app/id{USAGENOW}?action=write-review",
            f"https://apps.apple.com/app/usagenow/id{USAGENOW}?action=write-review",
            f" {REVIEW}",
            None,
        ):
            with self.subTest(value=value):
                self.assertFalse(stores.is_app_store_review_url(value))
        with self.assertRaises(ValueError):
            stores.app_store_review_url("not-an-id")

    def test_campaign_validators_still_fail_closed_on_review_queries(self):
        for value in (REVIEW, f"{REVIEW}&ct=geo_ask"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    stores.validated_app_store_url(value)
                with self.assertRaises(ValueError):
                    stores.normalize_app_store_campaign_url(value)

    def test_review_validator_applies_storefront_rules(self):
        self.assertEqual(US_REVIEW, stores.validated_app_store_review_url(
            US_REVIEW, USAGENOW, expected_locale="en-US", availability=AVAILABILITY,
        ))
        with self.assertRaisesRegex(ValueError, "storefront mismatch"):
            stores.validated_app_store_review_url(US_REVIEW, USAGENOW, expected_locale="ja")
        with self.assertRaises(ValueError):
            stores.validated_app_store_review_url(US_REVIEW, "6700000001")
        with self.assertRaises(ValueError):
            stores.validated_app_store_review_url(
                f"https://apps.apple.com/zz/app/id{USAGENOW}?action=write-review"
            )
        with self.assertRaisesRegex(ValueError, "Invalid App Store review URL"):
            stores.validated_app_store_review_url(f"{REVIEW}&ct=geo_ask")


class ReviewStamperAndAuditTests(unittest.TestCase):
    def setUp(self):
        environment = mock.patch.dict(os.environ, {stores.PROVIDER_TOKEN_ENV: PROVIDER})
        environment.start()
        self.addCleanup(environment.stop)

    def audit(self, source, relative):
        return audit.audit_source(
            source, relative, provider=PROVIDER, availability=AVAILABILITY,
        )

    def test_stamper_aligns_storefront_but_never_attributes_a_review_link(self):
        source = page(REVIEW)
        updated, changes = attribution.rewrite(
            source, "geo_learn", PROVIDER, locale="en-US", availability=AVAILABILITY,
        )
        self.assertEqual(1, changes)
        self.assertIn(f'href="{US_REVIEW}"', updated)
        self.assertNotIn("action=write-review&", updated)
        self.assertEqual((updated, 0), attribution.rewrite(
            updated, "geo_learn", PROVIDER, locale="en-US", availability=AVAILABILITY,
        ))
        self.assertEqual(US_REVIEW, attribution.final_store_url(
            REVIEW, "geo_learn", PROVIDER, locale="en-US",
            availability=AVAILABILITY, app_id=USAGENOW,
        ))
        # Supplemental-language pages keep the global link, like a CTA does.
        self.assertEqual(REVIEW, attribution.final_store_url(
            REVIEW, "geo_learn", PROVIDER, locale=None, availability=AVAILABILITY,
        ))

    def test_stamper_rejects_review_links_where_a_download_url_is_required(self):
        share = (
            f'<script src="/x.js" data-app-store-share="{USAGENOW}" '
            f'data-app-store-url="{REVIEW}" defer></script>'
        )
        with self.assertRaisesRegex(ValueError, "share URL cannot be a review link"):
            attribution.rewrite(share, "geo_learn", PROVIDER, locale="en-US")
        with self.assertRaises(ValueError):
            attribution.final_store_url(
                REVIEW, "geo_learn", PROVIDER, locale="en-US", app_id="6700000001",
            )

    def test_unavailable_market_drops_the_review_link(self):
        locale, app_ids = next(iter(market.UNAVAILABLE_APP_MARKETS.items()))
        app_id = sorted(app_ids)[0]
        self.assertIsNone(attribution.final_store_url(
            stores.app_store_review_url(app_id), "geo_learn", PROVIDER,
            locale=locale, availability=AVAILABILITY, app_id=app_id,
        ))

    def test_audit_accepts_review_link_as_non_download_identity(self):
        stamped, _ = attribution.rewrite(
            page(REVIEW), "geo_learn", PROVIDER, locale="en-US", availability=AVAILABILITY,
        )
        refs = self.audit(stamped, "guides/claudeusagemini.html")
        review_refs = [ref for ref in refs if stores.is_app_store_review_url(ref.url)]
        self.assertEqual([US_REVIEW], [ref.url for ref in review_refs])
        self.assertTrue(all(ref.identity for ref in review_refs))
        self.assertEqual([USAGENOW], [ref.app_id for ref in review_refs])
        self.assertEqual(1, sum(not ref.identity for ref in refs))

    def test_audit_rejects_every_malformed_or_misplaced_review_link(self):
        cases = {
            "campaign on review": page(f"{US_REVIEW}&ct=geo_learn"),
            "foreign storefront": page(US_REVIEW.replace("/us/", "/jp/")),
            "unknown storefront": page(US_REVIEW.replace("/us/", "/zz/")),
            "non-roster app": page("https://apps.apple.com/us/app/id6700000001?action=write-review"),
            "review only": (
                f'<html lang="en"><body><a href="{US_REVIEW}">Review</a></body></html>'
            ),
        }
        for name, source in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self.audit(source, "guides/claudeusagemini.html")
        with self.assertRaisesRegex(ValueError, "review action"):
            self.audit(
                '{"app_store_url": "%s", "app_store_id": "%s"}' % (US_REVIEW, USAGENOW),
                "api/app.json",
            )
        share = page(US_REVIEW).replace(
            "</body>",
            f'<script src="/x.js" data-app-store-share="{USAGENOW}" '
            f'data-app-store-url="{US_REVIEW}" defer></script></body>',
        )
        with self.assertRaisesRegex(ValueError, "review action"):
            self.audit(share, "guides/claudeusagemini.html")

    def test_tree_audit_requires_review_apps_to_be_verified_live(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            target = pages / "guides" / "claudeusagemini.html"
            target.parent.mkdir()
            stamped, _ = attribution.rewrite(
                page(REVIEW), "geo_learn", PROVIDER, locale="en-US", availability=AVAILABILITY,
            )
            target.write_text(stamped, encoding="utf-8")
            result = audit._audit_file(
                target, pages, PROVIDER, AVAILABILITY, {USAGENOW}, set(),
            )
            self.assertIsNone(result[-1])
            other = str(APPSTORE["mochi"])
            target.write_text(stamped.replace(
                f'href="{html.escape(cta(), quote=True)}"',
                f'href="{html.escape(cta(app_id=other), quote=True)}"',
            ), encoding="utf-8")
            result = audit._audit_file(
                target, pages, PROVIDER, AVAILABILITY, {other}, set(),
            )
            self.assertIn("outside the verified live inventory", result[-1])

    def test_hub_gate_skips_only_the_hubs_own_review_link(self):
        relative = "hubs/claudeusagemini.html"
        stamped = attribution.campaign_token(relative)
        download = cta(campaign=stamped)
        parser = types.SimpleNamespace(anchors=[download, download, US_REVIEW])
        self.assertEqual(
            {PROVIDER},
            check_hub_coverage._attributed_store_links(parser, USAGENOW, relative),
        )
        other = US_REVIEW.replace(USAGENOW, str(APPSTORE["mochi"]))
        with self.assertRaisesRegex(check_hub_coverage.HubContractError, "review link"):
            check_hub_coverage._attributed_store_links(
                types.SimpleNamespace(anchors=[download, download, other]), USAGENOW, relative,
            )
        with self.assertRaisesRegex(check_hub_coverage.HubContractError, "at least two"):
            check_hub_coverage._attributed_store_links(
                types.SimpleNamespace(anchors=[download, US_REVIEW]), USAGENOW, relative,
            )
        with self.assertRaisesRegex(check_hub_coverage.HubContractError, "incomplete"):
            check_hub_coverage._attributed_store_links(
                types.SimpleNamespace(anchors=[download, download, f"{US_REVIEW}&ct=x"]),
                USAGENOW, relative,
            )

    def test_normalizer_keeps_exact_review_links_and_rejects_variants(self):
        source = page(US_REVIEW, download=cta())
        self.assertEqual((source, 0), normalize_app_store_links.normalize_source(source))
        normalize_app_store_links.assert_no_partial_campaigns(source, Path("x.html"))
        with self.assertRaises(ValueError):
            normalize_app_store_links.assert_no_partial_campaigns(
                page(f"{US_REVIEW}&ct=geo_learn"), Path("x.html"),
            )


class ReviewBlockTests(unittest.TestCase):
    def test_focus_apps_and_labels_are_complete_and_neutral(self):
        self.assertEqual(len(APPSTORE), len(review.REVIEW_APP_IDS))
        self.assertIn(USAGENOW, review.REVIEW_APP_IDS)
        self.assertEqual(USAGENOW, "6818607603")
        self.assertEqual(set(OFFICIAL_LOCALES), set(review.REVIEW_LABELS))
        for locale, label in review.REVIEW_LABELS.items():
            with self.subTest(locale=locale):
                # Czech declines the brand ("v App Storu").
                self.assertIn("App Stor", label)
                self.assertIsNone(review.INCENTIVE_RE.search(label))
                self.assertNotRegex(label, r"\d")

    def test_focus_apps_include_recent_paying_apps(self):
        """Every live roster App gets the review link (benchmark_top1 section 3,
        lever 1), in particular the Apps that paid in the last 30 days but had
        no link at all (reports/conversion_focus_2026-10-16.md)."""
        for key, app_id in LIVE_APPS.items():
            with self.subTest(app=key):
                self.assertIn(key, review.REVIEW_APP_KEYS)
                self.assertTrue(review.is_review_app(app_id))
        for key in ("unblurry", "onepageppt", "wordmate", "snapport", "gmoney"):
            with self.subTest(app=key):
                self.assertIn(key, review.REVIEW_APP_KEYS)
                self.assertTrue(review.is_review_app(APPSTORE[key]))
        self.assertEqual(set(review.REVIEW_APP_KEYS), set(APPSTORE))
        self.assertFalse(review.is_review_app("6700000001"))

    def test_block_is_placed_under_the_qr_card_and_is_idempotent(self):
        source = (
            '<html lang="ja"><head></head><body><main><p>x</p>\n'
            "<!-- app-store-qr:start -->\n<div>qr</div>\n<!-- app-store-qr:end -->\n"
            "</main>\n<!-- mobile-store-cta:start -->m<!-- mobile-store-cta:end -->\n"
            "</body></html>"
        )
        href = "https://apps.apple.com/jp/app/id6818607603?action=write-review"
        once = review.render_review(Path("ja/claudeusagemini.html"), source, USAGENOW, href, "ja")
        self.assertEqual(once, review.render_review(Path("x"), once, USAGENOW, href, "ja"))
        self.assertEqual(1, once.count(review.BLOCK_START))
        self.assertLess(once.index("<!-- app-store-qr:end -->"), once.index(review.BLOCK_START))
        self.assertLess(once.index(review.BLOCK_END), once.index("</main>"))
        self.assertIn(review.REVIEW_LABELS["ja"], once)
        self.assertIn(f'href="{href}"', once)
        # Removing the App from the roster (or a blocked market) self-heals.
        self.assertNotIn(review.BLOCK_START, review.render_review(Path("x"), once, USAGENOW, None, "ja"))
        retired = "6700000001"
        self.assertNotIn(retired, review.REVIEW_APP_IDS)
        self.assertNotIn(review.BLOCK_START, review.render_review(
            Path("x"), once, retired, href.replace(USAGENOW, retired), "ja",
        ))
        with self.assertRaises(ValueError):
            review.review_block(USAGENOW, f"{href}&ct=x", "ja")
        with self.assertRaises(ValueError):
            review.review_block(USAGENOW, href.replace(USAGENOW, str(APPSTORE["mochi"])), "ja")

    def test_review_link_is_not_a_primary_action_for_supplemental_resources(self):
        intro = "<main><h1>UsageNow</h1><p>Intro.</p>"
        review_block = review.review_block(USAGENOW, US_REVIEW, "en-US")
        source = f"<html><body>{intro}\n{review_block}\n</main></body></html>"
        block = "<!-- hero-task-resources-v1:start --><section>x</section><!-- hero-task-resources-v1:end -->"
        updated = hero_task_html.insert_resource(source, block, "hero-task-resources-v1")
        self.assertEqual(source.replace(intro, intro + block, 1), updated)

    def test_single_app_buyer_sections_get_banner_and_review(self):
        """best-for, vs and reviews single-App pages carry the Smart App Banner
        and the review link; a multi-App page in the same family and a Web
        Story (AMP, protected story campaign) get neither."""
        app_id = USAGENOW
        other = str(APPSTORE["mochi"])

        def body(*ids):
            return "".join(
                f'<p><a href="https://apps.apple.com/app/id{value}">Get</a></p>'
                for value in ids
            )

        def document(lang, *ids):
            return (
                f'<html lang="{lang}"><head><meta charset="utf-8"></head>'
                f"<body><main>{body(*ids)}</main></body></html>"
            )

        story = (
            '<html amp lang="ja"><head><meta charset="utf-8"></head><body>'
            '<amp-story><amp-story-page id="cta"><amp-story-cta-layer>'
            f'<a href="https://apps.apple.com/app/id{app_id}">Get</a>'
            "</amp-story-cta-layer></amp-story-page></amp-story></body></html>"
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            os.environ, {stores.PROVIDER_TOKEN_ENV: PROVIDER},
        ):
            pages = Path(directory)
            guide = pages / "guides" / "claudeusagemini.html"
            single = {
                "ja/best-for/usagenow-best.html": document("ja", app_id),
                "ja/vs/usagenow-vs-other.html": document("ja", app_id),
                "reviews/usagenow-review-2026.html": document("en", app_id),
                "de-DE/reviews/usagenow-review-2026.html": document("de-DE", app_id),
            }
            excluded = {
                "ja/best-for/two-apps.html": document("ja", app_id, other),
                "ja/vs/usagenow-vs-mochi.html": document("ja", app_id, other),
                "ja/reviews/two-apps.html": document("ja", app_id, other),
                "ja/stories/claudeusagemini.html": story,
                "stories/claudeusagemini.html": story,
                # Non-store-locale mirrors keep the global link: no surface.
                "aa/best-for/usagenow-best.html": document("aa", app_id),
            }
            for relative, source in {**single, **excluded}.items():
                path = pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            guide.parent.mkdir()
            guide.write_text(document("en", app_id), encoding="utf-8")
            with mock.patch.object(
                gen_smart_app_banners, "build_targets",
                return_value=({guide.resolve(): app_id}, 1),
            ):
                inventory = gen_smart_app_banners.build_surface_inventory(
                    pages, {"claudeusagemini"}, "https://example.test/site",
                )
                self.assertEqual(
                    {guide.resolve(), *(
                        (pages / relative).resolve() for relative in single
                    )},
                    set(inventory.targets),
                )
                self.assertEqual(
                    {(pages / relative).resolve() for relative in single},
                    set(inventory.buyer_intent_pages) & set(inventory.targets),
                )
                with mock.patch.object(
                    gen_smart_app_banners, "build_surface_inventory",
                    return_value=inventory,
                ):
                    result = surfaces.generate(
                        pages, {"claudeusagemini"}, "https://example.test/site",
                    )
            self.assertEqual(len(single), result["smart_app_banners"]["buyer_intent_pages"])
            self.assertEqual(len(single), result["app_store_review_ctas"]["buyer_intent_pages"])
            self.assertEqual(len(single) + 1, result["app_store_review_ctas"]["pages"])
            banner = gen_smart_app_banners.banner_block(app_id)
            for relative in single:
                with self.subTest(page=relative):
                    source = (pages / relative).read_text(encoding="utf-8")
                    self.assertEqual(1, source.count(banner))
                    self.assertEqual(1, source.count(review.BLOCK_START))
                    locale = relative.split("/")[0] if relative.count("/") == 2 else "en-US"
                    self.assertIn(html.escape(review.REVIEW_LABELS[locale]), source)
                    # No storefront snapshot in the fixture, so the link stays
                    # global; the stamper aligns it once availability is known.
                    self.assertIn(
                        f'href="https://apps.apple.com/app/id{app_id}?action=write-review"',
                        source,
                    )
            for relative, original in excluded.items():
                with self.subTest(page=relative):
                    self.assertEqual(original, (pages / relative).read_text(encoding="utf-8"))

    def test_cta_selectors_never_pick_the_review_link(self):
        download = f"https://apps.apple.com/us/app/id{USAGENOW}"
        source = review.render_review(
            Path("x"),
            '<html><body><main></main>'
            f'<a class="cta" href="{download}">Get UsageNow</a></body></html>',
            USAGENOW, US_REVIEW, "en-US",
        )
        self.assertEqual(
            (download, "Get UsageNow"), gen_mobile_store_ctas.app_store_cta(source, USAGENOW),
        )
        self.assertNotIn("write-review", answer_app_store_links.unmanaged_app_store_source(source))


if __name__ == "__main__":
    unittest.main()
