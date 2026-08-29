#!/usr/bin/env python3
"""Tests for the deployed 46-App x 50-locale public coverage gate."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import public_market_coverage as coverage


SITE = coverage.DEFAULT_SITE
DIGEST = "a" * 64
COMMIT = "b" * 40


def app(locale: str, key: str, app_id: str, summary: str) -> dict:
    slug = locale.lower().replace("-", "_")
    country = "us" if locale == "en-US" else "tw"
    return {
        "key": key,
        "app_store_id": app_id,
        "name": key.title(),
        "summary": summary,
        "app_store_url": (
            f"https://apps.apple.com/{country}/app/id{app_id}"
            f"?pt=118326163&ct=iag_api_{slug}&mt=8"
        ),
        "guide_url": f"{SITE}/{locale}/{key}.html",
        "verified_live": True,
    }


def fixture() -> dict[str, dict]:
    locales = ("en-US", "zh-Hant")
    summaries = {
        "en-US": ("Private notes", "Safer files"),
        "zh-Hant": ("私密筆記", "安全檔案"),
    }
    app_rows = {
        locale: [
            app(locale, "notes", "1234567", summaries[locale][0]),
            app(locale, "files", "7654321", summaries[locale][1]),
        ]
        for locale in locales
    }
    documents: dict[str, dict] = {
        f"{SITE}/.well-known/deployment.json": {
            "version": 1,
            "source_commit": COMMIT,
        },
        f"{SITE}/api/v1/ios-app-catalog/index.json": {
            "record_count": 2,
            "locale_count": 2,
            "content_digest": DIGEST,
            "locales": [
                {
                    "locale": locale,
                    "url": (
                        f"{SITE}/api/v1/ios-app-catalog/locales/{locale}.json"
                    ),
                    "feed": (
                        f"{SITE}/api/v1/ios-app-catalog/feeds/{locale}.json"
                    ),
                }
                for locale in locales
            ],
        },
    }
    for locale in locales:
        slug = locale.lower().replace("-", "_")
        documents[
            f"{SITE}/api/v1/ios-app-catalog/locales/{locale}.json"
        ] = {
            "locale": locale,
            "record_count": 2,
            "content_digest": DIGEST,
            "apps": app_rows[locale],
        }
        documents[f"{SITE}/api/v1/ios-app-catalog/feeds/{locale}.json"] = {
            "language": locale,
            "_lumi_catalog": {
                "recordCount": 2,
                "contentDigest": DIGEST,
            },
            "items": [
                {
                    "id": f"https://apps.apple.com/app/id{row['app_store_id']}",
                    "url": row["guide_url"],
                    "external_url": (
                        "https://apps.apple.com/"
                        f"{'us' if locale == 'en-US' else 'tw'}"
                        f"/app/id{row['app_store_id']}"
                        f"?pt=118326163&ct=iag_feed_{slug}&mt=8"
                    ),
                    "title": row["name"],
                    "content_text": row["summary"],
                    "language": locale,
                }
                for row in app_rows[locale]
            ],
        }
    return documents


class PublicMarketCoverageTests(unittest.TestCase):
    def audit(self, documents: dict[str, dict]) -> dict:
        return coverage.audit_public_market_coverage(
            expected_apps=2,
            expected_locales=2,
            workers=2,
            fetcher=lambda url: copy.deepcopy(documents[url]),
        )

    def test_exact_native_public_matrix_is_ready(self):
        report = self.audit(fixture())
        self.assertEqual("READY", report["status"])
        self.assertEqual(4, report["native_public_cells"])
        self.assertEqual(6, report["verified_public_endpoints"])
        self.assertEqual(COMMIT, report["deployment_source_commit"])

    def test_missing_feed_cell_fails_closed(self):
        documents = fixture()
        feed = documents[
            f"{SITE}/api/v1/ios-app-catalog/feeds/zh-Hant.json"
        ]
        feed["items"].pop()
        with self.assertRaisesRegex(coverage.CoverageError, "incomplete"):
            self.audit(documents)

    def test_wrong_app_identity_fails_closed(self):
        documents = fixture()
        feed = documents[
            f"{SITE}/api/v1/ios-app-catalog/feeds/zh-Hant.json"
        ]
        feed["items"][0]["external_url"] = (
            "https://apps.apple.com/tw/app/id9999999"
            "?pt=118326163&ct=iag_feed_zh_hant&mt=8"
        )
        with self.assertRaisesRegex(
            coverage.CoverageError,
            "identity is missing or repeated",
        ):
            self.audit(documents)

    def test_english_fallback_in_non_english_cell_fails_closed(self):
        documents = fixture()
        feed = documents[
            f"{SITE}/api/v1/ios-app-catalog/feeds/zh-Hant.json"
        ]
        feed["items"][0]["content_text"] = "Private notes"
        with self.assertRaisesRegex(
            coverage.CoverageError,
            "native script",
        ):
            self.audit(documents)

    def test_cross_origin_catalog_url_fails_before_fetch(self):
        documents = fixture()
        documents[
            f"{SITE}/api/v1/ios-app-catalog/index.json"
        ]["locales"][0]["url"] = "https://attacker.example/catalog.json"
        with self.assertRaisesRegex(coverage.CoverageError, "untrusted"):
            self.audit(documents)

    def test_locale_app_denominators_cannot_diverge(self):
        documents = fixture()
        catalog = documents[
            f"{SITE}/api/v1/ios-app-catalog/locales/zh-Hant.json"
        ]
        catalog["apps"][0]["key"] = "other"
        catalog["apps"][0]["guide_url"] = f"{SITE}/zh-Hant/other.html"
        documents[
            f"{SITE}/api/v1/ios-app-catalog/feeds/zh-Hant.json"
        ]["items"][0]["url"] = f"{SITE}/zh-Hant/other.html"
        with self.assertRaisesRegex(
            coverage.CoverageError,
            "reviewed App denominator",
        ):
            self.audit(documents)


if __name__ == "__main__":
    unittest.main()
