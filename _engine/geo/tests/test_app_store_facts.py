from __future__ import annotations

import datetime as dt
import html
import json
import re
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
import market_availability
from official_locales import OFFICIAL_LOCALES
from videogen.registry import APPSTORE
from market_contract_assertions import assert_blocked_page
from live_app_manifest import canonical_manifest

# Derived from the canonical roster, not spelled out: a new App changes this
# count the day it ships, and a hand-written number silently goes stale.
BLOCKED_CELL_COUNT = sum(
    market_availability.is_unavailable(locale, app["app_id"])
    for locale in OFFICIAL_LOCALES
    for app in canonical_manifest()["apps"].values()
)


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


_HIDDEN_RE = re.compile(
    r"<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->",
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]*>")


def _visible_text(source: str) -> str:
    """Reader-visible text: drop scripts, styles, comments and tags."""
    return html.unescape(_TAG_RE.sub(" ", _HIDDEN_RE.sub(" ", source)))


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
        # Live readback confirmed the zero price in this and the prior run.
        "price_readback": "0",
        "currency_readback": "USD",
        "zero_since": "2026-01-01T00:00:00Z",
    }
    if include_rating:
        detail.update({"rating_value": 4.8, "rating_count": 12})
    return {
        "version": 2,
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "countries": {"us": [app_id], "bd": []},
        "details": {
            "us": {app_id: detail} if include_detail else {},
            "bd": {},
        },
    }


class HiddenVisiblePriceTests(unittest.TestCase):
    """Ruling 2026-11-21_rescue item 112 point 27: no visible price for Snapport."""

    URL = "https://apps.apple.com/tw/app/id6780575828"

    def test_snapport_is_hidden_and_others_are_not(self):
        self.assertFalse(facts.shows_visible_price(APPSTORE["snapport"]))
        self.assertTrue(facts.shows_visible_price(APPSTORE["snapportlite"]))

    def test_hidden_price_without_rating_drops_the_block(self):
        detail = {"price": "190", "formatted_price": "$190.00", "currency": "TWD"}
        self.assertIsNone(facts._fact_block(detail, self.URL, show_price=False))
        shown = facts._fact_block(detail, self.URL)
        self.assertIn("$190.00", shown)

    def test_hidden_price_keeps_rating_only(self):
        import gen_app_decision_cards as cards
        detail = {
            "price": "190", "formatted_price": "$190.00", "currency": "TWD",
            "rating_value": 4.9, "rating_count": 12,
        }
        block = facts._fact_block(detail, self.URL, show_price=False)
        self.assertNotIn("190", block)
        self.assertIn('<data value="4.9">4.9</data>', block)
        parsed = cards._storefront_fact(block, False)
        self.assertTrue(parsed is None or "formatted_price" not in parsed)


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
                    "changed": 2,
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
            # Visible above, structured never: see the note in
            # test_every_verified_generated_fact_matches_schema.
            self.assertNotIn("aggregateRating", schema)

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
        blocked = 0
        for locale in OFFICIAL_LOCALES:
            country = app_store_storefronts.LOCALE_STOREFRONTS[locale]
            for key in live:
                app_id = str(APPSTORE[key])
                source = (
                    pages / locale / f"{key}.html"
                ).read_text(encoding="utf-8")
                if market_availability.is_unavailable(locale, app_id):
                    assert_blocked_page(self, source, locale)
                    self.assertNotIn('"offers"', source)
                    self.assertNotIn('"aggregateRating"', source)
                    blocked += 1
                    continue
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
                    # JSON-LD offers stay exact in both branches: hiding the
                    # visible price never drops the structured price.
                    self.assertEqual(
                        detail["price"],
                        schema["offers"]["price"],
                    )
                    self.assertEqual(
                        detail["currency"],
                        schema["offers"]["priceCurrency"],
                    )
                    formatted_price = html.escape(
                        str(detail["formatted_price"])
                    )
                    if facts.shows_visible_price(app_id):
                        self.assertEqual(
                            1, source.count(facts.FACT_START)
                        )
                        self.assertIn(
                            f">{formatted_price}</data>",
                            source,
                        )
                    else:
                        # gen_app_store_facts.HIDE_VISIBLE_PRICE_APP_IDS:
                        # the fact block exists only to carry a rating, and
                        # the price must not leak anywhere a reader sees it.
                        self.assertEqual(
                            1 if "rating_value" in detail else 0,
                            source.count(facts.FACT_START),
                        )
                        self.assertNotIn(
                            f">{formatted_price}</data>",
                            source,
                        )
                        self.assertNotIn(
                            str(detail["formatted_price"]),
                            _visible_text(source),
                        )
                    # The visible rating stays -- it is a real fact a reader
                    # can check on the listing. The structured
                    # aggregateRating never does: publisher-authored ratings
                    # for one's own app are a self-serving rich-snippet
                    # signal, which gen_app_store_facts strips on purpose.
                    # Asserting it in both branches is what keeps the split
                    # honest once an app finally earns its first review.
                    self.assertNotIn("aggregateRating", schema)
                    if "rating_value" in detail:
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
        self.assertGreater(checked, 1200)
        self.assertEqual(blocked, BLOCKED_CELL_COUNT)

    def test_hidden_visible_price_list_is_only_snapport(self):
        # Guard against the hide-price switch turning into a blanket
        # exemption: only Snapport (id 6780575828) may hide its price.
        self.assertEqual(
            frozenset({"6780575828"}),
            facts.HIDE_VISIBLE_PRICE_APP_IDS,
        )
        self.assertEqual("6780575828", str(APPSTORE["snapport"]))
        self.assertFalse(facts.shows_visible_price("6780575828"))
        self.assertFalse(facts.shows_visible_price(6780575828))
        for key, app_id in APPSTORE.items():
            if key != "snapport":
                self.assertTrue(
                    facts.shows_visible_price(app_id),
                    key,
                )


if __name__ == "__main__":
    unittest.main()
