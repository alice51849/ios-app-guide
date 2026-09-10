"""Offline attribution matrix: full live roster × 50 locales × public formats."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse
import zipfile


GEO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GEO), str(GEO.parent / "social")]

import app_store_storefronts as stores
import audit_store_attribution as audit
import gen_app_store_qr_ctas as qr
import gen_store_attribution as attribution
from live_app_manifest import canonical_manifest
from official_locales import OFFICIAL_LOCALES
from videogen.registry import APPSTORE


PROVIDER = "123456789"
# Availability below is synthetic test data, never a new Apple availability claim.
LIVE_APPS = {
    key: app["app_id"] for key, app in canonical_manifest()["apps"].items()
}
APP_LOCALE_COUNT = len(LIVE_APPS) * len(OFFICIAL_LOCALES)
AVAILABILITY = {
    country: frozenset(LIVE_APPS.values())
    for country in stores.LOCALE_STOREFRONTS.values()
}
APP_ID = LIVE_APPS["lumibopomofo"]


def store_url(app_id=APP_ID, locale="en-US", campaign="geo_pick"):
    return stores.required_campaign_app_store_url(
        stores.localized_app_store_url(f"https://apps.apple.com/app/id{app_id}", locale),
        campaign, provider_token=PROVIDER, expected_locale=locale,
        expected_app_id=app_id, availability=AVAILABILITY,
    )


def record(app_id=APP_ID, locale="en-US"):
    return {
        "app_store_id": app_id, "locale": locale,
        "canonical_app_store_url": f"https://apps.apple.com/app/id{app_id}",
        "app_store_url": store_url(app_id, locale),
    }


def document(url, locale="en-US", key="app"):
    canonical = f"https://example.com/{locale}/{key}.html"
    return (
        f'<html lang="{locale}"><head><link rel="canonical" href="{canonical}">'
        f'<link rel="alternate" hreflang="{locale}" href="{canonical}"></head>'
        f'<body><a href="{html.escape(url, quote=True)}">App Store</a></body></html>'
    )


class AttributionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.environment = mock.patch.dict(os.environ, {stores.PROVIDER_TOKEN_ENV: PROVIDER})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        (GEO / "pages").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="attribution-test-", dir=GEO / "pages")
        self.addCleanup(self.directory.cleanup)
        self.pages = Path(self.directory.name)

    def audit(self, source, relative, **kwargs):
        return audit.audit_source(
            source, relative, provider=PROVIDER, availability=AVAILABILITY, **kwargs
        )

    def test_croissant_qualified_identity_stays_clean_but_cta_is_required(self):
        canonical = f"https://apps.apple.com/app/id{APP_ID}"
        example = {
            "publisher_intents/canonical_app_store_url": canonical,
            "publisher_intents/app_store_url": store_url(),
        }
        payload = {"recordSet": [{"examples": [example]}]}
        relative = "data/publisher.croissant.jsonld"
        self.audit(json.dumps(payload), relative)
        example["publisher_intents/app_store_url"] = canonical
        with self.assertRaises(ValueError):
            self.audit(json.dumps(payload), relative)
        example["publisher_intents/app_store_url"] = store_url()
        example["publisher_intents/canonical_app_store_url"] = store_url()
        with self.assertRaises(ValueError):
            self.audit(json.dumps(payload), relative)

    def test_zhuyin_dataset_related_app_has_real_campaign_attribution(self):
        import gen_data_hub

        payload = gen_data_hub.zhuyin_json()
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(payload["relatedApp"]).query)
        self.assertEqual([PROVIDER], query["pt"])
        self.assertEqual(["geo_pick"], query["ct"])
        self.audit(json.dumps(payload), "data/zhuyin-bopomofo.json")

    def test_full_live_roster_50_locales_across_all_text_delivery_formats(self):
        import portfolio_app_catalog_api as api
        import gen_github_discovery_readmes as discovery

        self.assertEqual({
            key: str(APPSTORE[key]) for key in canonical_manifest()["apps"]
        }, LIVE_APPS)
        self.assertIn("zipbox", LIVE_APPS)
        self.assertEqual(len(LIVE_APPS), len(set(LIVE_APPS.values())))
        self.assertEqual(50, len(OFFICIAL_LOCALES))
        cells = 0
        for key, app_id in LIVE_APPS.items():
            for locale in OFFICIAL_LOCALES:
                payload = record(app_id, locale)
                url = payload["app_store_url"]
                canonical = payload["canonical_app_store_url"]
                escaped = html.escape(url, quote=True)
                csv_file = io.StringIO()
                writer = csv.DictWriter(csv_file, fieldnames=list(payload))
                writer.writeheader()
                writer.writerow(payload)
                app = {**payload, "key": key, "name": key, "summary": "Verified app.",
                       "search_terms": ["app"], "guide_url": f"https://example.com/{locale}/{key}.html"}
                feed = api.feed_payload(
                    locale, "Catalog", [app], "2026-09-05", "a" * 64,
                    timestamp="2026-09-05T00:00:00Z",
                )
                documents = {
                    f"{locale}/apps/app.html": document(url, locale),
                    f"api/v1/catalog/locales/{locale}.json": json.dumps(api.catalog_payload(locale, [app], "2026-09-05", "a" * 64)),
                    f"api/v1/catalog/feeds/{locale}.json": json.dumps(feed),
                    f"{locale}/feed.jsonl": json.dumps(payload) + "\n",
                    f"{locale}/feed.csv": csv_file.getvalue(),
                    f"{locale}/feed.xml": (
                        f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{locale}">'
                        f"<entry><id>{canonical}</id><link rel=\"enclosure\" href=\"{escaped}\"/>"
                        f'<content type="html">{html.escape(f"<a href={chr(34)}{escaped}{chr(34)}>Get</a>")}</content>'
                        "</entry></feed>"
                    ),
                    f"{locale}/rss.xml": (
                        f"<rss><channel><item><guid>{canonical}</guid><link>{escaped}</link>"
                        f"<description>{html.escape(f'<a href={chr(34)}{escaped}{chr(34)}>Get</a>')}</description>"
                        "</item></channel></rss>"
                    ),
                    f"{locale}/downloads/plan.txt": f"App Store: {url}\n",
                    f"{locale}/downloads/plan.md": f"[App Store]({url})\n",
                    f"{locale}/README.md": f"[App Store]({discovery.github_store_url(payload)})\n",
                    f"{locale}/downloads/plan.ics": f"BEGIN:VCALENDAR\nURL:{url}\nEND:VCALENDAR\n",
                    f"{locale}/tools/result.js": "const result=" + json.dumps(payload).replace("&", r"\u0026") + ";",
                }
                for relative, source in documents.items():
                    with self.subTest(app=app_id, locale=locale, output=relative):
                        refs = self.audit(source, relative)
                        self.assertTrue(any(not ref.identity for ref in refs))
                        for ref in refs:
                            if not ref.identity:
                                self.assertEqual(url, ref.url)
                cells += 1
        self.assertEqual(APP_LOCALE_COUNT, cells)

    def test_qr_urls_cover_all_app_locale_pairs(self):
        for app_id in LIVE_APPS.values():
            for locale in OFFICIAL_LOCALES:
                with self.subTest(app=app_id, locale=locale):
                    url = store_url(app_id, locale)
                    relative = qr.qr_asset_relative(app_id, url)
                    digest = hashlib.sha256(url.encode()).hexdigest()[:20]
                    self.assertEqual(f"id{app_id}-{digest}.svg", relative.name)
                    source = (
                        f'<a class="app-store-qr-card__link" href="{html.escape(url)}">'
                        f'<img class="app-store-qr-card__image" src="/{relative}"></a>'
                    )
                    self.audit(source, f"{locale}/apps/app.html")

    def test_required_helper_rejects_missing_provider_or_invalid_destinations(self):
        with mock.patch.dict(os.environ, {stores.PROVIDER_TOKEN_ENV: ""}):
            with self.assertRaisesRegex(ValueError, "Missing App Store campaign"):
                stores.required_campaign_app_store_url(
                    f"https://apps.apple.com/app/id{APP_ID}", "geo_pick"
                )
        for value in (
            "", "https://example.com/app/id" + APP_ID,
            f"https://apps.apple.com.evil/app/id{APP_ID}",
            f"http://apps.apple.com/us/app/id{APP_ID}",
            f"https://apps.apple.com/bd/app/id{APP_ID}",
            store_url().replace("/us/", "/jp/"),
            store_url().replace("mt=8", "mt=9"),
            store_url() + "&ct=geo_ask",
            store_url() + "&unknown=value",
            store_url().replace(APP_ID, "1111111111"),
        ):
            with self.subTest(url=value), self.assertRaises(ValueError):
                stores.required_campaign_app_store_url(
                    value, "geo_pick", provider_token=PROVIDER,
                    expected_locale="en-US", expected_app_id=APP_ID,
                    availability=AVAILABILITY,
                )

    def test_partial_or_foreign_provider_never_passes_read_only_audit(self):
        complete = store_url()
        for invalid in (
            complete.split("?")[0],
            complete.replace("&ct=geo_pick", ""),
            complete.replace("&mt=8", ""),
            complete.replace(f"pt={PROVIDER}&", ""),
            complete.replace(PROVIDER, "987654321"),
            complete.replace("geo_pick", "iag_api_en_us"),
        ):
            with self.subTest(url=invalid), self.assertRaises(ValueError):
                self.audit(document(invalid), "apps/app.html")

    def test_missing_record_and_cta_links_fail_closed(self):
        cases = (
            ("api/v1/catalog/en-US.json", json.dumps({"apps": [{"app_store_id": APP_ID}]})),
            ("api/v1/catalog/en-US.json", json.dumps({**record(), "app_store_url": ""})),
            ("api/v1/catalog/en-US.json", json.dumps({**record(), "app_store_url": None})),
            ("api/v1/feed/en-US.json", json.dumps({"items": [{"id": f"https://apps.apple.com/app/id{APP_ID}"}]})),
            ("en-US/app.html", '<a class="app-store-cta">App Store</a>'),
            ("en-US/app.html", '<button data-app-store-url="">Share</button>'),
            ("en-US/app.html", '<button data-app-store-url="https://example.com">Share</button>'),
            ("en-US/app.html", '<button data-app-store-url="https://apps.apple.com/developer/id1136144960">Share</button>'),
            ("en-US/app.html", '<section class="app-store-qr-card"></section>'),
            ("en-US/tools/result.js", 'const data={"app_store_url":""};'),
        )
        for relative, source in cases:
            with self.subTest(output=relative), self.assertRaises(ValueError):
                self.audit(source, relative)

    def test_wrong_storefront_and_wrong_feed_app_fail_closed(self):
        payload = record(locale="ja")
        payload["app_store_url"] = store_url(locale="zh-Hant")
        with self.assertRaisesRegex(ValueError, "storefront mismatch"):
            self.audit(json.dumps(payload), "api/v1/catalog/ja.json")
        payload = {"items": [{"id": f"https://apps.apple.com/app/id{APP_ID}", "external_url": store_url().replace(APP_ID, "1111111111")}]}
        with self.assertRaises(ValueError):
            self.audit(json.dumps(payload), "api/v1/feed/en-US.json")

    def test_canonical_hreflang_and_entity_identifiers_are_never_tracked(self):
        for source in (
            '<link rel="canonical" href="https://example.com/app?ct=geo_pick">',
            '<link rel="alternate" hreflang="ja" href="https://example.com/ja?utm_source=geo">',
            f'<script type="application/ld+json">{json.dumps({"@id": store_url()})}</script>',
            f'<script type="application/ld+json">{json.dumps({"sameAs": store_url()})}</script>',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.audit(source, "en-US/app.html")

    def test_developer_identity_is_clean_but_cannot_replace_an_app_cta(self):
        developer = "https://apps.apple.com/developer/id1136144960"
        source = f'<a href="{developer}">Publisher</a>' + document(store_url())
        updated, changes = attribution.rewrite(source, "geo_pick", PROVIDER)
        self.assertEqual(0, changes)
        refs = self.audit(updated, "en-US/app.html")
        self.assertEqual(1, sum(ref.identity for ref in refs))
        self.assertIn(f'href="{developer}"', updated)
        self.assertEqual([True], [
            ref.identity for ref in self.audit(f"[Publisher]({developer})", "llms.txt")
        ])
        with self.assertRaisesRegex(ValueError, "developer profile"):
            self.audit(json.dumps({**record(), "app_store_url": developer}), "api/app.json")
        self.audit(json.dumps({
            "id": f"https://apps.apple.com/app/id{APP_ID}", "app_store_url": store_url()
        }), "api/app.json")

    def test_non_cta_manifest_feed_metadata_and_runtime_selectors_are_distinguished(self):
        manifest = {
            "schemaVersion": "1", "appStoreId": APP_ID,
            "urlPattern": "https://example.com/{locale}/", "pagesPerLocale": 2,
        }
        self.assertEqual([], self.audit(json.dumps(manifest), "apps/app/site-manifest.json"))
        item = {
            "id": "https://example.com/guide", "external_url": store_url(locale="ar-SA"),
            "content_text": "Verified app.",
            "_lumi_install": {"app_store_id": APP_ID},
        }
        refs = self.audit(
            json.dumps({"language": "ar-SA", "items": [item]}),
            "data/feeds/ar-SA.feed.json",
        )
        self.assertEqual([store_url(locale="ar-SA")], [ref.url for ref in refs])
        item.pop("external_url")
        with self.assertRaisesRegex(ValueError, "Missing App Store link"):
            self.audit(json.dumps({"items": [item]}), "data/feeds/ar-SA.feed.json")
        source = (
            'const selector=\'main a[href^="https://apps.apple.com/"]\';'
            'if (href.startsWith("https://apps.apple.com/")) show();'
        )
        self.assertEqual([], self.audit(source, "assets/cta.js"))
        script = f"<script>{source}</script>"
        self.assertEqual((script, 0), attribution.rewrite(script, "geo_pick", PROVIDER))
        with self.assertRaises(ValueError):
            self.audit('const data={app_store_url:"https://apps.apple.com/"};', "assets/cta.js")

    def test_stamper_moves_foreign_storefront_links_onto_the_page_locale(self):
        foreign = f"https://apps.apple.com/tw/app/id{APP_ID}"
        source = f'<html lang="en"><body><a href="{foreign}">Get</a></body></html>'
        updated, changes = attribution.rewrite(
            source, "geo_pick", PROVIDER, locale="en-US", availability=AVAILABILITY
        )
        self.assertEqual(1, changes)
        self.assertIn(f"https://apps.apple.com/us/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8", updated)
        self.assertNotIn("/tw/app/", updated)
        self.assertEqual(1, sum(not ref.identity for ref in self.audit(updated, "answers/compare.html")))
        self.assertEqual((updated, 0), attribution.rewrite(
            updated, "geo_pick", PROVIDER, locale="en-US", availability=AVAILABILITY
        ))
        # Not verified on the page storefront: fall back to the global link.
        limited = {"tw": frozenset({APP_ID})}
        fallback, _ = attribution.rewrite(
            source, "geo_pick", PROVIDER, locale="en-US", availability=limited
        )
        self.assertIn(f"https://apps.apple.com/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8", fallback)
        # The page's own storefront and supplemental-language pages are untouched.
        own, _ = attribution.rewrite(
            source.replace('lang="en"', 'lang="zh-Hant"'), "geo_pick", PROVIDER,
            locale="zh-Hant", availability=AVAILABILITY,
        )
        self.assertIn(f"https://apps.apple.com/tw/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8", own)
        self.assertEqual(foreign, attribution.align_storefront(foreign, None, AVAILABILITY))
        # Root pages (no locale directory) declare their locale on <html lang>.
        root_page, root_changes = attribution.rewrite(
            source, "geo_pick", PROVIDER, locale=None, availability=AVAILABILITY
        )
        self.assertEqual(1, root_changes)
        self.assertIn(f"https://apps.apple.com/us/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8", root_page)
        self.audit(root_page, "answers/compare.html")
        self.assertEqual(foreign, attribution.align_storefront(foreign, "aa", AVAILABILITY))

    def test_supplemental_languages_use_only_global_verified_app_fallback(self):
        global_url = f"https://apps.apple.com/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8"
        source = f'<html lang="aa"><a href="{html.escape(global_url)}">Get</a></html>'
        self.audit(source, "aa/app.html")
        with self.assertRaisesRegex(ValueError, "Unsupported App Store locale"):
            self.audit(source.replace(global_url.split("?")[0], store_url().split("?")[0]), "aa/app.html")
        self.assertEqual("ar-SA", audit.locale_of("data/feeds/ar-SA.rss.xml"))
        self.audit(
            f'<rss><channel><language>ar-SA</language><item><link>{html.escape(store_url(locale="ar-SA"))}</link></item></channel></rss>',
            "data/feeds/ar-SA.rss.xml",
        )
        with self.assertRaisesRegex(ValueError, "storefront mismatch"):
            self.audit(document(store_url(), "en"), "ar-SA/app.html")

    def test_stamper_handles_single_unquoted_entities_json_and_download_scripts(self):
        canonical = f"https://apps.apple.com/app/id{APP_ID}"
        payload = {"app_store_id": APP_ID, "app_store_url": canonical, "canonical_app_store_url": canonical}
        source = (
            '<html lang="en-US"><head><link rel="canonical" href="https://example.com/app">'
            '<link rel="alternate" hreflang="ja" href="https://example.com/ja">'
            f'<meta name="apple-itunes-app" content="app-id={APP_ID}"></head><body>'
            f"<a href='{canonical}'>Get</a><a href={canonical}>Get</a>"
            f'<button data-app-store-url="{canonical}">Share</button>'
            f'<script type="application/json">{json.dumps(payload)}</script>'
            f'<script>const result={json.dumps(payload)};const output=new Blob([result.app_store_url]);</script>'
            f'<script type="application/ld+json">{json.dumps({"@type": "SoftwareApplication", "sameAs": canonical, "url": canonical, "installUrl": canonical})}</script>'
            "</body></html>"
        )
        updated, changes = attribution.rewrite(source, "geo_pick", PROVIDER)
        self.assertGreater(changes, 5)
        refs = self.audit(updated, "en-US/app.html")
        self.assertTrue(any(ref.surface == "tool" for ref in refs))
        self.assertTrue(any(ref.field == "Smart App Banner" for ref in refs))
        for ref in refs:
            self.assertEqual(not ref.identity, bool(urllib.parse.urlsplit(ref.url).query))
        self.assertEqual((updated, 0), attribution.rewrite(updated, "geo_pick", PROVIDER))
        self.assertIn('rel="canonical" href="https://example.com/app"', updated)

    def test_stories_keep_one_protected_campaign_and_visuals_stay_untouched(self):
        clean = f"https://apps.apple.com/app/id{APP_ID}"
        story_cta = f"{clean}?pt={PROVIDER}&ct=iag_story&mt=8"
        story = (
            '<html lang="en-US"><body>'
            f'<a href="{html.escape(story_cta)}">Get</a>'
            '<script type="application/ld+json">'
            + json.dumps({"@type": "MobileApplication", "@id": clean, "url": clean,
                          "installUrl": clean, "downloadUrl": clean})
            + "</script></body></html>"
        )
        (self.pages / "stories").mkdir()
        (self.pages / "stories" / "app.html").write_text(story)
        visual = f'<html lang="en-US"><body><a href="{html.escape(clean)}?pt={PROVIDER}&amp;ct=iag_visual_en_us&amp;mt=8">Get</a></body></html>'
        (self.pages / "visuals").mkdir()
        (self.pages / "visuals" / "app.html").write_text(visual)
        with mock.patch.object(attribution, "load_storefront_availability", return_value=AVAILABILITY):
            stats = attribution.generate(self.pages, check=False)
        stamped = (self.pages / "stories" / "app.html").read_text()
        self.assertEqual(4, stamped.count("ct=iag_story"))
        banner = (
            f'<meta name="apple-itunes-app" content="app-id={APP_ID}, '
            f'app-argument={html.escape(story_cta)}">'
        )
        attributed = banner.replace('">', f', affiliate-data=pt={PROVIDER}&amp;ct=iag_story&amp;mt=8">')
        for meta in (banner, attributed):
            healed, _ = attribution.rewrite(
                f'<html lang="en-US"><head>{meta}</head><body><a href="{html.escape(story_cta)}">Get</a></body></html>',
                attribution.STORY_CAMPAIGN, PROVIDER, locale="en-US", availability=AVAILABILITY,
            )
            self.assertIn(attributed, healed)
            self.assertEqual(1, sum(ref.field == "Smart App Banner" for ref in self.audit(healed, "stories/app.html")))
        self.assertIn(f'"@id":"{clean}"', stamped)
        self.assertNotIn("ct=geo_", stamped)
        self.assertEqual(visual, (self.pages / "visuals" / "app.html").read_text())
        self.assertEqual({"iag_story": 4, "iag_visual_en_us": 1}, {k: v for k, v in stats["links_by_campaign"].items()})
        self.assertIsNone(attribution.page_token("visuals/app.html", visual))
        self.assertEqual("iag_story", attribution.page_token("ja/stories/app.html", story))

    def test_qr_cards_are_minted_from_the_final_stamped_link(self):
        foreign = f"https://apps.apple.com/tw/app/id{APP_ID}"
        final = attribution.final_store_url(
            foreign, "geo_pick", PROVIDER, locale="en-US", availability=AVAILABILITY, app_id=APP_ID
        )
        self.assertEqual(f"https://apps.apple.com/us/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8", final)
        relative = qr.qr_asset_relative(APP_ID, final)
        card = (
            f'<html lang="en-US"><body><a class="app-store-qr-card__link" href="{html.escape(foreign)}">'
            f'<img class="app-store-qr-card__image" src="/{relative}"></a></body></html>'
        )
        stamped, changes = attribution.rewrite(
            card, "geo_pick", PROVIDER, locale="en-US", availability=AVAILABILITY
        )
        self.assertEqual(1, changes)
        self.assertIsNone(attribution.qr_card_desync(stamped))
        self.assertEqual(final, attribution.final_store_url(
            final, "geo_pick", PROVIDER, locale="en-US", availability=AVAILABILITY, app_id=APP_ID
        ))

    def test_invalid_input_never_partially_rewrites_the_tree(self):
        first = self.pages / "a.html"
        original = document(f"https://apps.apple.com/app/id{APP_ID}")
        first.write_text(original)
        # A known foreign storefront (/jp/) is re-homed by align_storefront, so
        # the poison page must carry an unknown storefront, which stays invalid.
        (self.pages / "z.html").write_text(document(store_url().replace("/us/", "/xx/")))
        with self.assertRaises(ValueError):
            attribution.generate(self.pages, check=False)
        self.assertEqual(original, first.read_text())

    def test_preexisting_stale_or_missing_qr_is_blocking(self):
        href = store_url()
        relative = qr.qr_asset_relative(APP_ID, href)
        source = (
            f'<a class="app-store-qr-card__link" href="{html.escape(href)}">'
            f'<img class="app-store-qr-card__image" src="/{relative}"></a>'
        )
        for invalid in (
            source.replace(relative.stem.split("-")[-1], "0" * 20),
            source.replace(f'<img class="app-store-qr-card__image" src="/{relative}">', ""),
        ):
            with self.subTest(source=invalid), self.assertRaises(ValueError):
                self.audit(invalid, "en-US/app.html")
        with self.assertRaisesRegex(ValueError, "Missing QR asset"):
            self.audit(source, "en-US/app.html", root=self.pages)
        asset = self.pages / relative
        asset.parent.mkdir(parents=True)
        asset.write_text(qr.qr_svg(APP_ID, href))
        self.audit(source, "en-US/app.html", root=self.pages)
        asset.write_text(asset.read_text().replace('stroke="#000"', 'stroke="#fff"'))
        with self.assertRaisesRegex(ValueError, "QR pixels"):
            self.audit(source, "en-US/app.html", root=self.pages)

    def test_publishable_tree_requires_every_surface_and_app_locale(self):
        (self.pages / stores.STATE_FILE).write_text(json.dumps({
            "countries": {key: sorted(value) for key, value in AVAILABILITY.items()}
        }))
        for locale in OFFICIAL_LOCALES:
            payload = {"locale": locale, "apps": [record(app_id, locale) for app_id in LIVE_APPS.values()]}
            path = self.pages / "api" / "v1" / "ios-app-catalog" / "locales" / f"{locale}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "Missing attribution surfaces"):
            audit.audit_tree(self.pages, provider=PROVIDER, expected_app_ids=set(LIVE_APPS.values()))
        self.assertEqual(APP_LOCALE_COUNT, audit.audit_tree(
            self.pages, provider=PROVIDER, expected_app_ids=set(LIVE_APPS.values()),
            required_surfaces=frozenset({"api"}),
        )["app_locale_cells"])
        url = store_url()
        relative = qr.qr_asset_relative(APP_ID, url)
        asset = self.pages / relative
        asset.parent.mkdir(parents=True)
        asset.write_text(qr.qr_svg(APP_ID, url))
        (self.pages / "app.html").write_text(
            f'<a class="app-store-qr-card__link" href="{html.escape(url)}">'
            f'<img class="app-store-qr-card__image" src="/{relative}"></a>'
        )
        (self.pages / "feed.jsonl").write_text(json.dumps(record()) + "\n")
        (self.pages / "tool.js").write_text("const result=" + json.dumps(record()) + ";")
        (self.pages / "download.txt").write_text(url)
        report = audit.audit_tree(self.pages, provider=PROVIDER, expected_app_ids=set(LIVE_APPS.values()))
        self.assertEqual(audit.REQUIRED_SURFACES, set(report["links_by_surface"]))
        self.assertEqual(APP_LOCALE_COUNT, report["app_locale_cells"])
        self.assertEqual(report, audit.audit_tree(
            self.pages, provider=PROVIDER, expected_app_ids=set(LIVE_APPS.values()), workers=2,
        ))
        (self.pages / "api/v1/ios-app-catalog/locales/ja.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing App/locale CTA coverage"):
            audit.audit_tree(self.pages, provider=PROVIDER, expected_app_ids=set(LIVE_APPS.values()),
                             required_surfaces=frozenset({"api"}))

    def test_check_mode_and_missing_provider_return_failure_without_writing(self):
        path = self.pages / "app.html"
        source = document(f"https://apps.apple.com/app/id{APP_ID}")
        path.write_text(source)
        for provider in (PROVIDER, ""):
            env = {**os.environ, stores.PROVIDER_TOKEN_ENV: provider}
            result = subprocess.run(
                [sys.executable, str(GEO / "gen_store_attribution.py"),
                 "--check", "--pages-dir", str(self.pages)],
                env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(source, path.read_text())

    def test_unexpected_checker_failure_cannot_leave_a_stale_pass_report(self):
        report = self.pages / "audit.json"
        report.write_text('{"status":"PASS"}')
        with (
            mock.patch.object(sys, "argv", ["audit", "--pages-dir", str(self.pages), "--report", str(report)]),
            mock.patch.object(audit, "audit_tree", side_effect=TypeError("malformed record")),
            mock.patch.object(sys, "stderr", io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            audit.main()
        self.assertEqual(1, caught.exception.code)
        self.assertEqual("FAIL", json.loads(report.read_text())["status"])

    def test_pdf_and_epub_download_links_are_verified_without_extraction(self):
        from pypdf import PdfWriter
        from pypdf.annotations import Link

        path = self.pages / "plan.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_annotation(page_number=0, annotation=Link(rect=(0, 0, 100, 100), url=store_url()))
        writer.write(path)
        refs = list(audit._download_references(path, "en-US/plan.pdf", PROVIDER, AVAILABILITY, self.pages))
        self.assertEqual([store_url()], [ref.url for ref in refs])
        epub = self.pages / "plan.epub"
        with zipfile.ZipFile(epub, "w") as archive:
            archive.writestr("book.xhtml", document(store_url()))
        refs = list(audit._download_references(epub, "en-US/plan.epub", PROVIDER, AVAILABILITY, self.pages))
        self.assertEqual([store_url()], [ref.url for ref in refs if not ref.identity])
        bundle = self.pages / "plan.zip"
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("result.json", json.dumps(record()))
            archive.write(path, "plan.pdf")
        refs = list(audit._download_references(bundle, "en-US/plan.zip", PROVIDER, AVAILABILITY, self.pages))
        self.assertEqual(2, len([ref for ref in refs if not ref.identity]))
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("result.json", json.dumps({**record(), "app_store_url": ""}))
        with self.assertRaisesRegex(ValueError, "Missing App Store link"):
            list(audit._download_references(bundle, "en-US/plan.zip", PROVIDER, AVAILABILITY, self.pages))

    def test_legacy_json_pwa_and_well_known_api_links_remain_attributed(self):
        import portfolio_app_finder as finder

        key = "lumibopomofo"
        directory = self.pages / "en-US"
        directory.mkdir()
        (directory / f"{key}.html").write_text("<html></html>")
        app = {
            "key": key, "name": key, "purchase_labels": {"en": "Pay once"},
            "features": [], "capabilities": {}, "summaries": {"en": "Verified app."},
            "category_labels": {"en": "Education"},
            "canonical_app_store_url": f"https://apps.apple.com/app/id{APP_ID}",
        }
        payload = json.loads(finder.legacy_apps_json([app], self.pages))
        self.assertEqual(
            f"https://apps.apple.com/app/id{APP_ID}?pt={PROVIDER}&ct=geo_pick&mt=8",
            payload[0]["appStoreUrl"],
        )
        self.audit(json.dumps(payload), "apps.json")
        pwa = {"related_applications": [{"platform": "itunes", "id": APP_ID, "url": store_url()}]}
        self.audit(json.dumps(pwa), "en-US/tools/app.webmanifest")
        pwa["related_applications"][0]["url"] = ""
        with self.assertRaisesRegex(ValueError, "Missing PWA"):
            self.audit(json.dumps(pwa), "en-US/tools/app.webmanifest")
        self.assertEqual(
            {"api"},
            {ref.surface for ref in self.audit(json.dumps(record()), ".well-known/api-catalog")},
        )
        with self.assertRaisesRegex(ValueError, "Missing App Store campaign"):
            self.audit(f'<button data-store-url="https://apps.apple.com/app/id{APP_ID}">Get</button>', "en-US/tool.html")

    def test_api_finder_and_publisher_campaigns_do_not_fragment_by_app_or_locale(self):
        import portfolio_app_catalog_api as api
        import portfolio_app_finder as finder
        import publisher_intent_catalog as publisher

        self.assertEqual({"geo_pick"}, {api._campaign(locale) for locale in OFFICIAL_LOCALES})
        self.assertEqual({"geo_pick"}, {api._feed_campaign(locale) for locale in OFFICIAL_LOCALES})
        self.assertEqual({"geo_pick"}, {publisher.campaign_token(locale) for locale in OFFICIAL_LOCALES})
        self.assertEqual({"geo_learn"}, {finder.finder_campaign_token(locale) for locale in OFFICIAL_LOCALES})
        self.assertEqual({"geo_learn"}, {
            urllib.parse.parse_qs(urllib.parse.urlsplit(finder._campaign_url(key)).query)["ct"][0]
            for key in LIVE_APPS
        })

    def test_decision_matrix_keeps_identity_clean_and_install_links_attributed(self):
        import app_decision_matrix as matrix

        row = {
            "app_key": "lumibopomofo", "app_name": "Lumi", "purchase_model": "free_with_iap",
            "one_time_option": True, "choose_when": "Learning", "consider_instead_when": "Other needs",
            "verified_storefront_count": 1, "guide_url": "https://example.com/app",
            "app_store_url": store_url(), "category_label": "EducationApplication",
            "decision_context": "Verified app.", "us_price": "0", "us_price_currency": "USD",
            "free_to_download": True,
        }
        source = json.dumps(matrix.jsonld_payload([row], "2026-09-05"))
        refs = self.audit(source, "data/ios-app-decision-matrix.jsonld")
        self.assertEqual([store_url().split("?")[0]], [ref.url for ref in refs if ref.identity])
        self.assertEqual({store_url()}, {ref.url for ref in refs if not ref.identity})

    def test_public_finder_dataset_exposes_an_attributed_link_separate_from_identity(self):
        import portfolio_app_finder as finder
        from jsonschema import Draft202012Validator, FormatChecker

        # Finder v1 has its own versioned persona roster, not an implicit adoption of new apps.
        roster = finder.contract.live_roster()
        finder_apps = {key: app["track_id"] for key, app in roster.items()}
        self.assertEqual({key: LIVE_APPS[key] for key in roster}, finder_apps)
        records = [
            {
                "key": key, "app_store_id": app_id, "name": key, "category": "education",
                "category_labels": {"en": "Education", "zh-Hant": "教育"},
                "summaries": {"en": "Verified fixture.", "zh-Hant": "已驗證測試資料。"},
                "purchase_model": "paid_upfront",
                "purchase_labels": {"en": "Pay once", "zh-Hant": "一次付費"},
                "one_time_option": True, "features": [], "keywords": [],
                "capabilities": {name: False for name in (
                    "offline", "no_account", "no_ads", "no_tracking",
                    "private_or_on_device", "widget", "apple_watch",
                )},
                "canonical_app_store_url": f"https://apps.apple.com/app/id{app_id}",
                "verified_live": True,
            }
            for key, app_id in finder_apps.items()
        ]
        payload = finder.dataset_payload(records, roster=roster)
        schema = json.loads(finder.dataset_schema())
        self.assertEqual(len(roster), schema["properties"]["record_count"]["const"])
        self.assertEqual(len(roster), schema["properties"]["apps"]["minItems"])
        self.assertEqual(len(roster), schema["properties"]["apps"]["maxItems"])
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
        refs = self.audit(json.dumps(payload), "data/verified-ios-app-finder-catalog.json")
        self.assertEqual(len(roster), sum(not ref.identity for ref in refs))
        self.assertCountEqual(roster, [app["key"] for app in payload["apps"]])
        self.assertTrue(all("app_store_url" not in record for record in records))
        for app in payload["apps"]:
            self.assertNotIn("?", app["canonical_app_store_url"])
            self.assertIn(f"?pt={PROVIDER}&ct=geo_learn&mt=8", app["app_store_url"])
        for key in set(LIVE_APPS) - set(roster):
            unreviewed = {
                **records[0], "key": key, "name": key, "app_store_id": LIVE_APPS[key],
                "canonical_app_store_url": f"https://apps.apple.com/app/id{LIVE_APPS[key]}",
            }
            with self.subTest(unreviewed=key), self.assertRaisesRegex(
                finder.contract.ContractError, "finder_producer_roster_invalid",
            ):
                finder.dataset_payload([*records, unreviewed], roster=roster)
        with mock.patch.dict(os.environ, {stores.PROVIDER_TOKEN_ENV: ""}):
            with self.assertRaisesRegex(ValueError, "Missing App Store campaign"):
                finder.dataset_payload(records, roster=roster)

    def test_all_live_apps_50_locales_have_working_attributed_browser_tools(self):
        import gen_webmcp_install_tools as tools

        (self.pages / stores.STATE_FILE).write_text(json.dumps({
            "countries": {key: sorted(value) for key, value in AVAILABILITY.items()}
        }))
        for locale in OFFICIAL_LOCALES:
            directory = self.pages / locale
            directory.mkdir()
            for key in LIVE_APPS:
                (directory / f"{key}.html").write_text(
                    f'<html lang="{locale}"><head><meta name="description" content="Verified app.">'
                    f'<link rel="canonical" href="https://example.com/{locale}/{key}.html">'
                    "</head><body></body></html>"
                )
        stats = tools.generate(self.pages, live_keys=set(LIVE_APPS), site="https://example.com")
        self.assertEqual(APP_LOCALE_COUNT, stats["pages"])
        self.assertEqual(0, stats["fallbacks"])
        payloads = []
        for locale in OFFICIAL_LOCALES:
            for key, app_id in LIVE_APPS.items():
                source = (self.pages / locale / f"{key}.html").read_text()
                refs = self.audit(source, f"{locale}/{key}.html")
                self.assertEqual([store_url(app_id, locale)], [ref.url for ref in refs])
                payloads.append({
                    "app_store_id": app_id, "app_name": key,
                    "page_language": locale, "app_store_url": refs[0].url,
                    "page_url": f"https://example.com/{locale}/{key}.html",
                    "localized_description": "Verified app.",
                })
        invalid = []
        for bad_url in (
            store_url().split("?")[0],
            store_url().replace("&ct=geo_pick", ""),
            store_url().replace("&mt=8", ""),
            store_url() + "&ct=geo_ask",
            store_url().replace("/us/", "/jp/"),
            store_url().replace("apps.apple.com", "apps.apple.com.evil"),
        ):
            invalid.append({**payloads[0], "app_store_id": APP_ID, "page_language": "en-US", "app_store_url": bad_url})
        harness = r"""
const fs = require("node:fs"), vm = require("node:vm"), assert = require("node:assert/strict");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const script = new vm.Script(input.source);
(async () => {
  let verified = 0;
  for (const [shouldPass, rows] of [[true, input.valid], [false, input.invalid]]) {
    for (const data of rows) {
      const registered = [];
      const context = {
        URL, console: {error() {}},
        document: {
          currentScript: {dataset: {webmcpInstall: "payload"}},
          getElementById: () => ({textContent: JSON.stringify(data)}),
          modelContext: {registerTool: tool => registered.push(tool)}
        },
        window: {location: {assign() {throw new Error("No navigation during tests");}}}
      };
      script.runInNewContext(context);
      await new Promise(resolve => setImmediate(resolve));
      assert.equal(registered.length, shouldPass ? 2 : 0);
      if (shouldPass) {
        const tool = registered.find(tool => tool.name === "get_verified_ios_app_install_link");
        const output = await tool.execute({});
        assert.ok(JSON.stringify(output).includes(data.app_store_url));
        verified++;
      }
    }
  }
  process.stdout.write(String(verified));
})().catch(error => {console.error(error); process.exitCode = 1;});
"""
        result = subprocess.run(
            ["node", "-e", harness],
            input=json.dumps({"source": tools.ASSET_SOURCE, "valid": payloads, "invalid": invalid}),
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(str(APP_LOCALE_COUNT), result.stdout)

    def test_xml_language_inheritance_calendar_folding_and_template_literals(self):
        with self.assertRaisesRegex(ValueError, "storefront mismatch"):
            self.audit(
                f'<feed xml:lang="ja"><entry><link href="{html.escape(store_url())}"/></entry></feed>',
                "feed.xml",
            )
        url = store_url()
        split = url.index("&ct=")
        refs = self.audit(f"URL:{url[:split]}\r\n {url[split:]}\r\n", "en-US/plan.ics")
        self.assertEqual([url], [ref.url for ref in refs])
        self.assertEqual([url], [
            ref.url for ref in self.audit(f"const link=`{url}`;", "en-US/tools/result.js")
        ])
        with self.assertRaisesRegex(ValueError, "dynamic interpolation"):
            self.audit(f"const link=`{url}&extra=${{unverified}}`;", "en-US/tools/result.js")

    def test_install_decision_feed_contract_covers_all_apps_and_locales(self):
        import app_install_decision_feeds as feeds

        records = [
            {
                **record(app_id, locale), "app_key": key, "app_name": key,
                "record_id": f"{locale}:{key}",
                "decision_page_url": f"https://example.com/{locale}/{key}.html",
                "verified_live": True, "is_ranking": False, "measured_search_volume": False,
                "publisher_query": "Find an app", "decision_context": "A reviewed workflow",
                "app_store_cta_label": "App Store", "publisher_disclosure": "First-party catalog",
            }
            for locale in OFFICIAL_LOCALES for key, app_id in LIVE_APPS.items()
        ]
        grouped = feeds._group_records(records)
        self.assertEqual(set(OFFICIAL_LOCALES), set(grouped))
        for locale, rows in grouped.items():
            with self.subTest(locale=locale):
                self.assertCountEqual(LIVE_APPS, [row["app_key"] for row in rows])
        country = stores.LOCALE_STOREFRONTS[records[0]["locale"]]
        other = "jp" if country != "jp" else "tw"
        for bad in (
            "", records[0]["app_store_url"].split("?")[0],
            records[0]["app_store_url"].replace(f"/{country}/", f"/{other}/"),
            records[0]["app_store_url"] + "&mt=8",
        ):
            with self.subTest(url=bad), self.assertRaises(ValueError):
                feeds._group_records([{**records[0], "app_store_url": bad}, *records[1:]])

    def test_final_gate_runs_after_late_generators_and_before_publication(self):
        source = (GEO / "publish.py").read_text()
        main = source[source.index("def main():"):]
        gate = main.index('"audit_store_attribution.py"')
        self.assertGreater(gate, main.index('"gen_feed.py"'))
        self.assertGreater(gate, main.index('"publisher_intent_visuals.py"'))
        self.assertLess(gate, main.index('if "--no-push" in sys.argv:'))

    def test_text_boundaries_keep_cjk_thai_and_sentence_marks_out_of_the_link(self):
        clean = f"https://apps.apple.com/app/id{APP_ID}"
        stamped = store_url()
        for text, expected in (
            (f"下載：{stamped}。之後", stamped),
            (f"ดาวน์โหลด {stamped}ครับ", stamped),
            (f"Install {stamped}.", stamped),
            (f"Install ({stamped})!", stamped),
            (f"Really? {stamped}?", stamped),
            (f'"{clean}"', clean),
            (f"{clean}\\n", clean),
        ):
            with self.subTest(text=text):
                self.assertEqual([expected], audit.STORE_TEXT_RE.findall(text))
        # Read-only audit: prose around a campaign link in JSON, JS, Markdown and
        # calendar text must not turn a complete link into a broken one.
        payload = {
            "app_store_id": APP_ID, "app_store_url": stamped,
            "note": f"請到 App Store 下載：{stamped}。ดาวน์โหลดได้ที่ {stamped}ครับ",
        }
        refs = self.audit(json.dumps(payload, ensure_ascii=False), "zh-Hant/data.json".replace("zh-Hant", "en-US"))
        self.assertEqual({stamped}, {ref.url for ref in refs})
        self.assertEqual(3, len(refs))
        self.audit(f"安裝請至 {stamped}。", "en-US/notes.md")
        self.audit(f"BEGIN:VCALENDAR\nDESCRIPTION:下載 {stamped}。\nEND:VCALENDAR\n", "en-US/plan.ics")
        # Stamper: the token is rewritten in place and the neighbouring prose,
        # full-width punctuation and Thai letters survive untouched.
        source = (
            '<html lang="en-US"><head><link rel="canonical" href="https://example.com/a"></head><body>'
            f'<a href="{clean}">Get</a>'
            f'<script type="application/json">{json.dumps({"app_store_id": APP_ID, "app_store_url": clean, "note": f"下載：{clean}。ครับ"}, ensure_ascii=False)}</script>'
            f'<script>const hint = "安裝：{clean}。";</script>'
            "</body></html>"
        )
        updated, changes = attribution.rewrite(source, "geo_pick", PROVIDER)
        # A global (country-less) link stays global; only the campaign is added.
        restamped = f"{clean}?pt={PROVIDER}&ct=geo_pick&mt=8"
        self.assertEqual(4, changes)
        self.assertIn(f"下載：{restamped}。ครับ", updated)
        self.assertIn(f"安裝：{restamped}。", updated)
        self.assertNotIn(f'{clean}"', updated)
        self.assertEqual((updated, 0), attribution.rewrite(updated, "geo_pick", PROVIDER))
        self.assertEqual({restamped}, {ref.url for ref in self.audit(updated, "en-US/app.html") if not ref.identity})

    def test_provenance_fields_are_identity_and_never_require_a_campaign(self):
        clean = f"https://apps.apple.com/app/id{APP_ID}"
        record = {
            "app_store_id": APP_ID, "app_store_url": store_url(),
            "source_url": clean, "isBasedOn": [clean], "mainEntityOfPage": clean,
            "dc:source": clean, "dcterms:source": clean,
        }
        payload = {"license": "https://creativecommons.org/licenses/by/4.0/", "source_url": clean, "records": [record]}
        refs = self.audit(json.dumps(payload), "data/dataset.json")
        self.assertEqual(6, sum(ref.identity for ref in refs))
        self.assertEqual([store_url()], [ref.url for ref in refs if not ref.identity])
        for field in ("source_url", "isBasedOn", "mainEntityOfPage", "dc:source", "dcterms:source"):
            tracked = {**record, field: store_url()}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Tracking parameters"):
                self.audit(json.dumps({"records": [tracked]}), "data/dataset.json")
        # The stamper mirrors the audit: provenance stays a clean canonical URL.
        script = f'<script type="application/ld+json">{json.dumps(record | {"app_store_url": clean})}</script>'
        updated, changes = attribution.rewrite(
            f'<html lang="en-US"><body><a href="{clean}">Get</a>{script}</body></html>', "geo_pick", PROVIDER
        )
        self.assertEqual(2, changes)
        self.assertEqual(5, updated.count(f'"{clean}"'))
        # Exactly the anchor and the JSON-LD app_store_url carry the campaign.
        self.assertEqual(2, updated.count("&ct=geo_pick&mt=8\""))

    def test_schema_sample_and_pattern_keywords_are_opaque_but_records_are_not(self):
        clean = f"https://apps.apple.com/app/id{APP_ID}"
        pattern = r"^https://apps\\.apple\\.com/[a-z]{2}/app/id\\d{9,12}\\?pt=\\d+&ct=[a-z_]+&mt=8$"
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
            "properties": {
                "source_url": {"const": clean},
                "app_store_url": {
                    "type": "string", "pattern": pattern, "default": clean,
                    "examples": [clean, f"https://apps.apple.com/us/app/id{APP_ID}?ct=iag_pick"],
                    "enum": [clean, "https://apps.apple.com/jp/app/id000000001?pt=1&ct=x&mt=8"],
                },
                "records": {"type": "array", "items": {"$ref": "#/$defs/record"}},
            },
            "$defs": {"record": {"type": "object", "properties": {"app_store_url": {"example": clean}}}},
        }
        openapi = {"openapi": "3.1.0", "components": {"schemas": {"App": {"type": "object", "properties": {"install": {"example": f"https://apps.apple.com/us/app/id{APP_ID}?ct=iag_pick"}}}}}}
        for relative, document in (("api/v1/x/catalog.schema.json", schema), ("api/v1/x/openapi.json", openapi)):
            with self.subTest(relative=relative):
                self.assertEqual([], self.audit(json.dumps(document), relative))
                source = f'<script type="application/json">{json.dumps(document)}</script>'
                self.assertEqual((source, 0), attribution.rewrite(source, "geo_pick", PROVIDER))
        # Outside a schema node the same key names are ordinary data and a bare
        # App Store link there is still an unattributed CTA.
        plain = {"app_store_id": APP_ID, "app_store_url": store_url(), "default": clean}
        with self.assertRaisesRegex(ValueError, "Missing App Store campaign"):
            self.audit(json.dumps(plain), "data/plain.json")
        plain_source = f'<script type="application/json">{json.dumps(plain)}</script>'
        updated, changes = attribution.rewrite(plain_source, "geo_pick", PROVIDER)
        self.assertEqual(1, changes)
        self.assertNotIn(f'"{clean}"', updated)

    def test_generate_failures_name_the_relative_page_and_write_nothing(self):
        page = self.pages / "en-US" / "tool.html"
        page.parent.mkdir()
        original = (
            '<html lang="en-US"><body>'
            f'<a href="https://apps.apple.com/app/id{APP_ID}">Get</a>'
            '<script>const link = `https://apps.apple.com/app/id${appId}`;</script>'
            "</body></html>"
        )
        page.write_text(original)
        with self.assertRaisesRegex(ValueError, r"^en-US/tool\.html: .*dynamic interpolation"):
            attribution.generate(self.pages, check=False)
        self.assertEqual(original, page.read_text())
        bad_card = (
            f'<a class="app-store-qr-card__link" href="https://apps.apple.com/app/id{APP_ID}"></a>'
        )
        page.write_text(f'<html lang="en-US"><body>{bad_card}</body></html>')
        with self.assertRaisesRegex(attribution.QrCardDesyncError, r"^en-US/tool\.html: "):
            attribution.generate(self.pages, check=False)

    def test_generate_refuses_to_overwrite_a_page_changed_after_preflight(self):
        page = self.pages / "en-US" / "app.html"
        page.parent.mkdir()
        page.write_text(document(f"https://apps.apple.com/app/id{APP_ID}"))
        real = attribution.qr_card_desync

        def racing(text):
            page.write_text(page.read_text() + "<!-- edited concurrently -->")
            return real(text)

        with mock.patch.object(attribution, "qr_card_desync", side_effect=racing):
            with self.assertRaisesRegex(ValueError, r"^Page changed during attribution preflight: en-US/app\.html$"):
                attribution.generate(self.pages, check=False)
        self.assertNotIn("pt=", page.read_text())
        result = attribution.generate(self.pages, check=False)
        self.assertEqual(1, result["pages_changed"])
        self.assertEqual(result | {"anchors_stamped": 0, "pages_changed": 0}, attribution.generate(self.pages, check=False))

    def test_legacy_page_families_cannot_reintroduce_nonlive_ctas_through_attribution(self):
        import live_app_guard

        # These persisted page shapes come from the old full-coverage writers,
        # which intentionally are no longer shipped in the cloud engine.
        def legacy_page(app_ids, *, review=False):
            items = [
                {"@type": "ListItem", "position": position,
                 "url": f"https://apps.apple.com/app/id{app_id}?ct=iag_bf_aa"}
                for position, app_id in enumerate(app_ids, 1)
            ]
            schema = (
                {"@type": "Review", "itemReviewed": {
                    "@type": "SoftwareApplication", "name": "Zafe",
                }}
                if review else {"@type": "ItemList", "itemListElement": items}
            )
            return (
                '<html lang="aa"><head><meta name="robots" content="index,follow">'
                f'<script type="application/ld+json">{json.dumps(schema)}</script>'
                '</head><body>'
                + "".join(f'<a href="{item["url"]}">Get</a>' for item in items)
                + "</body></html>"
            )

        mixed = ["6787344033", LIVE_APPS["maskmyfile"]]
        rendered = {
            "aa/best-for/mixed.html": legacy_page(mixed),
            "aa/best-for/dead.html": legacy_page(["6787344033"]),
            "aa/reviews/dead.html": legacy_page(["6787344033"], review=True),
            "aa/seasonal/mixed.html": legacy_page(mixed + [LIVE_APPS["scanto"]]),
        }
        for relative, source in rendered.items():
            self.assertIn("6787344033", source)
            path = self.pages / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
        before = {relative: (self.pages / relative).read_bytes() for relative in rendered}
        with mock.patch.object(attribution, "load_storefront_availability", return_value=AVAILABILITY):
            checked = attribution.generate(self.pages, check=True)
            self.assertEqual(4, checked["pages_changed"])
            self.assertEqual(before, {
                relative: (self.pages / relative).read_bytes() for relative in rendered
            })
            applied = attribution.generate(self.pages, check=False)
            self.assertEqual(4, applied["pages_changed"])
            self.assertEqual(0, attribution.generate(self.pages, check=False)["pages_changed"])
        for relative in rendered:
            source = (self.pages / relative).read_text()
            self.assertNotIn("6787344033", source)
            refs = self.audit(source, relative)
            self.assertTrue(all(
                stores.APP_STORE_PATH_RE.fullmatch(urllib.parse.urlsplit(ref.url).path)["app_id"]
                in LIVE_APPS.values() for ref in refs if not ref.identity
            ))
            if "dead.html" in relative:
                self.assertIn(live_app_guard.QUARANTINE_META, source)
                self.assertIn("noindex,nofollow", source)
                self.assertEqual([], refs)
            else:
                self.assertNotIn(live_app_guard.QUARANTINE_META, source)
                self.assertGreater(len(refs), 0)
        # Legacy templates can be replayed indefinitely; the common producer
        # must converge again rather than rely on a one-off generated edit.
        for relative, source in rendered.items():
            (self.pages / relative).write_text(source)
        with mock.patch.object(attribution, "load_storefront_availability", return_value=AVAILABILITY):
            self.assertEqual(4, attribution.generate(self.pages, check=False)["pages_changed"])


if __name__ == "__main__":
    unittest.main()
