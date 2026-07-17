from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_webmcp_install_tools as tools
from official_locales import OFFICIAL_LOCALES
from videogen.registry import APPS, APPSTORE


def _page(site: str, locale: str, key: str, description: str) -> str:
    canonical = f"{site}/{locale}/{key}.html"
    return (
        "<!doctype html>\n"
        f'<html lang="{locale}"><head>'
        f'<meta name="description" content="{description}">'
        f'<link rel="canonical" href="{canonical}">'
        "</head><body><main>Verified app</main></body></html>\n"
    )


def _payload(source: str) -> dict[str, str]:
    match = re.search(
        rf'<script type="application/json" id="{tools.DATA_ID}">'
        r"(.*?)</script>",
        source,
        flags=re.DOTALL,
    )
    if not match:
        raise AssertionError("Missing WebMCP install payload")
    return json.loads(match.group(1))


class WebMcpInstallToolsTests(unittest.TestCase):
    def test_generate_covers_locales_with_verified_storefronts(self):
        key = "lumibopomofo"
        app_id = str(APPSTORE[key])
        site = "https://example.com/guide"
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            for locale, description in (
                ("en-US", "A private learning app."),
                ("fr-FR", "Une app éducative privée."),
            ):
                path = pages / locale / f"{key}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    _page(site, locale, key, description),
                    encoding="utf-8",
                )
            (pages / ".appstore_storefront_state.json").write_text(
                json.dumps(
                    {
                        "countries": {
                            "us": [app_id],
                            "fr": [app_id],
                        }
                    }
                ),
                encoding="utf-8",
            )

            first = tools.generate(
                pages,
                live_keys={key},
                locales=("en-US", "fr-FR"),
                site=site,
            )
            second = tools.generate(
                pages,
                live_keys={key},
                locales=("en-US", "fr-FR"),
                site=site,
            )

            self.assertEqual(
                {
                    "apps": 1,
                    "locales": 2,
                    "pages": 2,
                    "localized_storefronts": 2,
                    "fallbacks": 0,
                    "changed": 2,
                    "asset_changed": 1,
                },
                first,
            )
            self.assertEqual(0, second["changed"])
            self.assertEqual(0, second["asset_changed"])
            for locale, country in (("en-US", "us"), ("fr-FR", "fr")):
                source = (
                    pages / locale / f"{key}.html"
                ).read_text(encoding="utf-8")
                self.assertEqual(1, source.count(tools.BLOCK_START))
                self.assertEqual(1, source.count(tools.BLOCK_END))
                payload = _payload(source)
                self.assertEqual(locale, payload["page_language"])
                self.assertEqual(
                    f"https://apps.apple.com/{country}/app/id{app_id}",
                    payload["app_store_url"],
                )
                self.assertEqual(
                    f"{site}/{locale}/{key}.html",
                    payload["page_url"],
                )
            asset = (
                pages / "assets" / tools.ASSET_NAME
            ).read_text(encoding="utf-8")
            self.assertIn(
                "get_verified_ios_app_install_link",
                asset,
            )
            self.assertIn(
                "open_verified_ios_app_store_listing",
                asset,
            )
            self.assertIn(
                "window.location.assign(data.app_store_url)",
                asset,
            )
            self.assertNotIn("fetch(", asset)
            self.assertNotIn("localStorage", asset)

    def test_unverified_storefront_uses_direct_canonical_fallback(self):
        key = "lumibopomofo"
        app_id = str(APPSTORE[key])
        site = "https://example.com/guide"
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            path = pages / "bn-BD" / f"{key}.html"
            path.parent.mkdir(parents=True)
            path.write_text(
                _page(site, "bn-BD", key, "শিশুদের শেখার অ্যাপ।"),
                encoding="utf-8",
            )
            (pages / ".appstore_storefront_state.json").write_text(
                '{"countries":{"bd":[]}}\n',
                encoding="utf-8",
            )

            stats = tools.generate(
                pages,
                live_keys={key},
                locales=("bn-BD",),
                site=site,
            )

            self.assertEqual(1, stats["fallbacks"])
            self.assertEqual(
                f"https://apps.apple.com/app/id{app_id}",
                _payload(path.read_text(encoding="utf-8"))[
                    "app_store_url"
                ],
            )

    def test_missing_locale_page_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                FileNotFoundError,
                "Missing localized app page",
            ):
                tools.generate(
                    Path(tmp),
                    live_keys={"lumibopomofo"},
                    locales=("en-US",),
                    site="https://example.com/guide",
                )

    def test_unknown_live_app_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Unknown live apps"):
                tools.generate(
                    Path(tmp),
                    live_keys={"not-in-registry"},
                    locales=("en-US",),
                    site="https://example.com/guide",
                )

    def test_localized_tool_description_never_ends_mid_sentence(self):
        self.assertEqual(
            "Une app éducative privée.",
            tools._localized_tool_description(
                "Une app éducative privée. Tous les outils"
            ),
        )
        self.assertEqual(
            "শিশুদের শেখার অ্যাপ…",
            tools._localized_tool_description("শিশুদের শেখার অ্যাপ"),
        )
        self.assertEqual(
            "A complete description!",
            tools._localized_tool_description("A complete description!"),
        )

    def test_every_official_locale_and_live_app_has_one_tool(self):
        pages = tools.PAGES
        if not (pages / "en-US").is_dir():
            self.skipTest("Generated Pages tree is not linked")
        live = {
            key
            for key in APPSTORE
            if (pages / "en-US" / f"{key}.html").is_file()
        }
        if not live:
            self.skipTest("Generated localized app pages are unavailable")
        self.assertEqual(26, len(live))
        for locale in OFFICIAL_LOCALES:
            for key in live:
                with self.subTest(locale=locale, app=key):
                    source = (
                        pages / locale / f"{key}.html"
                    ).read_text(encoding="utf-8")
                    self.assertEqual(
                        1,
                        source.count(tools.BLOCK_START),
                    )
                    payload = _payload(source)
                    self.assertEqual(locale, payload["page_language"])
                    self.assertEqual(
                        str(APPSTORE[key]),
                        payload["app_store_id"],
                    )
                    self.assertEqual(
                        str(APPS[key]["name"]),
                        payload["app_name"],
                    )
                    self.assertRegex(
                        payload["app_store_url"],
                        r"^https://apps\.apple\.com/"
                        r"(?:[a-z]{2}/)?app/id[0-9]{9,12}$",
                    )


if __name__ == "__main__":
    unittest.main()
