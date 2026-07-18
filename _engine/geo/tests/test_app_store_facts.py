from __future__ import annotations

import html
import json
from pathlib import Path
import sys
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_store_storefronts
import gen_app_store_facts as facts
import gen_mobile_app_identity
from official_locales import OFFICIAL_LOCALES
from videogen.registry import APPSTORE


def _page(site: str, locale: str, key: str, app_id: str) -> str:
    canonical = f"{site}/{locale}/{key}.html"
    schema = {
        "@context": "https://schema.org",
        "@type": "MobileApplication",
        "@id": f"https://apps.apple.com/app/id{app_id}",
        "name": key,
        "operatingSystem": "iOS",
        "url": f"https://apps.apple.com/app/id{app_id}",
    }
    return (
        "<!doctype html>\n"
        f'<html lang="{locale}"><head>'
        f'<link rel="canonical" href="{canonical}">'
        '<script type="application/ld+json">'
        f"{json.dumps(schema)}</script>"
        "</head><body><main>Verified app</main></body></html>\n"
    )


def _mobile_schema(source: str) -> dict[str, object]:
    for match in gen_mobile_app_identity.JSON_LD_RE.finditer(source):
        document = json.loads(match.group("body"))
        for node in gen_mobile_app_identity._iter_nodes(document):
            if (
                "MobileApplication"
                in gen_mobile_app_identity._schema_types(node)
            ):
                return node
    raise AssertionError("Missing MobileApplication")


def _state(
    app_id: str,
    *,
    include_detail: bool = True,
    include_rating: bool = True,
) -> dict[str, object]:
    detail: dict[str, object] = {
        "price": "0",
        "currency": "USD",
        "formatted_price": "Free",
    }
    if include_rating:
        detail.update({"rating_value": 4.8, "rating_count": 12})
    return {
        "version": 2,
        "countries": {"us": [app_id], "bd": []},
        "details": {
            "us": {app_id: detail} if include_detail else {},
            "bd": {},
        },
    }


class AppStoreFactsTests(unittest.TestCase):
    def test_zero_price_labels_cover_every_official_locale(self):
        self.assertEqual(
            set(OFFICIAL_LOCALES),
            set(app_store_storefronts.FREE_LABELS),
        )
        raw = {
            "price": "0",
            "currency": "CAD",
            "formatted_price": "Free",
        }
        self.assertEqual(
            "Gratuit",
            app_store_storefronts.localized_storefront_detail(
                raw,
                "fr-CA",
            )["formatted_price"],
        )
        paid = {
            "price": "6.99",
            "currency": "CAD",
            "formatted_price": "$6.99",
        }
        self.assertEqual(
            paid,
            app_store_storefronts.localized_storefront_detail(
                paid,
                "fr-CA",
            ),
        )

    def test_generate_adds_visible_facts_and_matching_schema(self):
        key = "lumibopomofo"
        app_id = str(APPSTORE[key])
        site = "https://example.com/guide"
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            for locale in ("en-US", "bn-BD"):
                path = pages / locale / f"{key}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    _page(site, locale, key, app_id),
                    encoding="utf-8",
                )
            (
                pages / app_store_storefronts.STATE_FILE
            ).write_text(
                json.dumps(_state(app_id)),
                encoding="utf-8",
            )

            first = facts.generate(
                pages,
                live_keys={key},
                locales=("en-US", "bn-BD"),
                site=site,
            )
            second = facts.generate(
                pages,
                live_keys={key},
                locales=("en-US", "bn-BD"),
                site=site,
            )

            self.assertEqual(
                {
                    "apps": 1,
                    "locales": 2,
                    "pages": 2,
                    "facts": 1,
                    "rated": 1,
                    "without_facts": 1,
                    "changed": 1,
                    "asset_changed": 1,
                },
                first,
            )
            self.assertEqual(0, second["changed"])
            self.assertEqual(0, second["asset_changed"])
            source = (
                pages / "en-US" / f"{key}.html"
            ).read_text(encoding="utf-8")
            self.assertEqual(1, source.count(facts.FACT_START))
            self.assertIn(">Free</data>", source)
            self.assertIn('value="4.8">4.8</data>/5', source)
            self.assertIn('value="12">12</data>', source)
            schema = _mobile_schema(source)
            self.assertEqual(
                {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                    "url": (
                        "https://apps.apple.com/us/app/"
                        f"id{app_id}"
                    ),
                    "availability": "https://schema.org/InStock",
                },
                schema["offers"],
            )
            self.assertEqual(4.8, schema["aggregateRating"]["ratingValue"])
            self.assertEqual(12, schema["aggregateRating"]["ratingCount"])

            fallback = (
                pages / "bn-BD" / f"{key}.html"
            ).read_text(encoding="utf-8")
            self.assertNotIn(facts.FACT_START, fallback)
            self.assertNotIn("offers", _mobile_schema(fallback))

    def test_removed_public_detail_removes_managed_facts(self):
        key = "lumibopomofo"
        app_id = str(APPSTORE[key])
        site = "https://example.com/guide"
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            path = pages / "en-US" / f"{key}.html"
            path.parent.mkdir(parents=True)
            path.write_text(
                _page(site, "en-US", key, app_id),
                encoding="utf-8",
            )
            state = pages / app_store_storefronts.STATE_FILE
            state.write_text(
                json.dumps(_state(app_id)),
                encoding="utf-8",
            )
            facts.generate(
                pages,
                live_keys={key},
                locales=("en-US",),
                site=site,
            )
            state.write_text(
                json.dumps(
                    _state(app_id, include_detail=False),
                ),
                encoding="utf-8",
            )

            result = facts.generate(
                pages,
                live_keys={key},
                locales=("en-US",),
                site=site,
            )

            self.assertEqual(1, result["changed"])
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(facts.FACT_START, source)
            schema = _mobile_schema(source)
            self.assertNotIn("offers", schema)
            self.assertNotIn("aggregateRating", schema)

    def test_every_verified_generated_fact_matches_schema(self):
        pages = facts.PAGES
        details = app_store_storefronts.load_storefront_details(pages)
        if not details:
            self.skipTest("Storefront detail snapshot is not generated")
        live = {
            key
            for key in APPSTORE
            if (pages / "en-US" / f"{key}.html").is_file()
        }
        verified = set(
            facts.live_app_keys(APPSTORE, str(pages), refresh=False)
        )
        self.assertEqual(verified, live)
        checked = 0
        for locale in OFFICIAL_LOCALES:
            country = app_store_storefronts.LOCALE_STOREFRONTS[locale]
            for key in live:
                app_id = str(APPSTORE[key])
                source = (
                    pages / locale / f"{key}.html"
                ).read_text(encoding="utf-8")
                detail = details.get(country, {}).get(app_id)
                schema = _mobile_schema(source)
                if detail is None:
                    self.assertNotIn(facts.FACT_START, source)
                    continue
                detail = (
                    app_store_storefronts.localized_storefront_detail(
                        detail,
                        locale,
                    )
                )
                checked += 1
                with self.subTest(locale=locale, app=key):
                    self.assertEqual(1, source.count(facts.FACT_START))
                    self.assertEqual(
                        detail["price"],
                        schema["offers"]["price"],
                    )
                    self.assertEqual(
                        detail["currency"],
                        schema["offers"]["priceCurrency"],
                    )
                    self.assertIn(
                        f">{html.escape(str(detail['formatted_price']))}</data>",
                        source,
                    )
                    if "rating_value" in detail:
                        self.assertEqual(
                            detail["rating_count"],
                            schema["aggregateRating"]["ratingCount"],
                        )
                        rating_value = f"{float(detail['rating_value']):.1f}"
                        self.assertIn(
                            f'value="{rating_value}">{rating_value}</data>/5',
                            source,
                        )
                        self.assertIn(
                            f'value="{detail["rating_count"]}">'
                            f'{detail["rating_count"]}</data>',
                            source,
                        )
                    else:
                        self.assertNotIn("aggregateRating", schema)
        self.assertGreater(checked, 1200)


if __name__ == "__main__":
    unittest.main()
