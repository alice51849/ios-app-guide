#!/usr/bin/env python3
"""Regression tests for the first-party publisher intent catalog."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from unittest import mock
import urllib.error
import urllib.request
from urllib.parse import urlparse


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

from app_store_storefronts import validated_app_store_url
import publisher_intent_catalog as catalog
from aeo_answers_i18n import require_translation_quality
from official_locales import OFFICIAL_LOCALES


def normalized_digits(value: str) -> str:
    result = ""
    for char in value:
        try:
            result += str(unicodedata.digit(char))
        except (TypeError, ValueError):
            continue
    return result


def mcp_distribution_fixture(
    version: str,
) -> tuple[dict[str, object], dict[str, bytes]]:
    mcpb = b"verified mcpb"
    npx = b"verified npx"
    mcpb_sha256 = hashlib.sha256(mcpb).hexdigest()
    npx_sha256 = hashlib.sha256(npx).hexdigest()
    release_base = (
        f"{catalog.MCP_REPOSITORY_URL}/releases/download/v{version}"
    )
    registry = {
        "server": {
            "name": catalog.MCP_SERVER_NAME,
            "version": version,
            "repository": {
                "url": catalog.MCP_REPOSITORY_URL,
                "source": "github",
            },
            "packages": [
                {
                    "registryType": "mcpb",
                    "identifier": f"{release_base}/lumi-app-finder.mcpb",
                    "fileSha256": mcpb_sha256,
                    "transport": {"type": "stdio"},
                }
            ],
        },
        "_meta": {
            "io.modelcontextprotocol.registry/official": {
                "status": "active",
                "isLatest": True,
            }
        },
    }
    checksums = (
        f"{mcpb_sha256}  lumi-app-finder.mcpb\n"
        f"{npx_sha256}  lumi-app-finder-npx.tgz\n"
    ).encode("ascii")
    distribution = catalog._validated_mcp_distribution(
        {
            "schema_version": 1,
            "server_name": catalog.MCP_SERVER_NAME,
            "version": version,
            "registry_url": (
                f"{catalog.MCP_REGISTRY_BASE_URL}/{version}"
            ),
            "registry_latest_url": catalog.MCP_REGISTRY_LATEST_URL,
            "repository_url": catalog.MCP_REPOSITORY_URL,
            "mcpb_url": f"{release_base}/lumi-app-finder.mcpb",
            "mcpb_sha256": mcpb_sha256,
            "npx_url": f"{release_base}/lumi-app-finder-npx.tgz",
            "npx_sha256": npx_sha256,
            "checksums_url": f"{release_base}/SHA256SUMS",
        }
    )
    responses = {
        catalog.MCP_REGISTRY_LATEST_URL: json.dumps(registry).encode("utf-8"),
        str(distribution["checksums_url"]): checksums,
        str(distribution["mcpb_url"]): mcpb,
        str(distribution["npx_url"]): npx,
    }
    return distribution, responses


def write_mcp_distribution_state(
    pages: Path,
    distribution: dict[str, object],
) -> Path:
    path = pages / "data" / catalog.MCP_DISTRIBUTION_STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(distribution, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def registry_then_http_error(
    responses: dict[str, bytes],
    status: int,
):
    def urlopen(
        request: urllib.request.Request,
        **_kwargs: object,
    ) -> io.BytesIO:
        url = request.full_url
        if url == catalog.MCP_REGISTRY_LATEST_URL:
            return io.BytesIO(responses[url])
        raise urllib.error.HTTPError(
            url,
            status,
            "temporary upstream failure",
            hdrs=None,
            fp=None,
        )

    return urlopen


class PublisherIntentLocalizationTests(unittest.TestCase):
    def test_purchase_labels_exist_in_i18n_strings(self) -> None:
        payload = json.loads(catalog.I18N_PATH.read_text(encoding="utf-8"))
        missing = set(catalog.PURCHASE_LABELS.values()) - set(payload["strings"])
        self.assertEqual(set(), missing)

    def test_truncated_finder_dataset_fails_closed(self) -> None:
        # The 50-locale catalog is derived from the finder dataset. If a
        # partial finder run ever writes fewer apps than the portfolio owns,
        # this must stop the build instead of publishing a shrunken catalog.
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "data").mkdir(parents=True)
            keys = sorted(catalog.PERSONAS)[:2]
            (
                pages / "data" / catalog.FINDER_DATASET
            ).write_text(
                json.dumps({"apps": [{"key": key} for key in keys]}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as caught:
                catalog.build(pages)
            message = str(caught.exception)
            self.assertIn("coverage differs", message)
            for key in sorted(set(catalog.PERSONAS) - set(keys))[:1]:
                self.assertIn(key, message)
            self.assertFalse(
                (pages / "data" / f"{catalog.SLUG}.json").exists()
            )

    def test_ui_localizations_cover_all_official_locales(self) -> None:
        payload = json.loads(catalog.I18N_PATH.read_text(encoding="utf-8"))
        localizations = catalog.load_ui_i18n()
        ordinary_english = (
            "first-party",
            "publisher",
            "locale",
            "locales",
            "live",
            "listing",
            "unlock",
            "flexible",
            "query",
            "queries",
            "search",
            "intent",
            "catalog",
            "decision",
            "context",
            "download",
            "records",
            "paid",
            "check",
            "current",
            "ranking",
            "rankings",
            "review",
            "reviews",
            "endorsement",
            "endorsements",
            "persona",
        )
        self.assertEqual(set(OFFICIAL_LOCALES), set(localizations))
        self.assertEqual(50, len(localizations))
        self.assertEqual(34, len(payload["strings"]))
        for locale, mapping in localizations.items():
            self.assertEqual(set(payload["strings"]), set(mapping))
            for source, target in mapping.items():
                self.assertEqual(target, target.strip())
                self.assertNotRegex(target, r"[\r\n]")
                for token in (
                    "Lumi Studio",
                    "iOS",
                    "App Store",
                    "Apple",
                    "JSON",
                    "JSONL",
                    "CSV",
                    "CC BY 4.0",
                ):
                    if token in source:
                        self.assertIn(token, target, (locale, source))
                digits = normalized_digits(target)
                for number in ("26", "50", "1300"):
                    if number in source.replace(",", ""):
                        self.assertIn(number, digits, (locale, source))
                if not locale.startswith("en-"):
                    for word in ordinary_english:
                        self.assertNotRegex(
                            target,
                            (
                                rf"(?i)(?<![A-Za-z])"
                                rf"{re.escape(word)}"
                                rf"(?![A-Za-z])"
                            ),
                            (locale, source),
                        )
            if not locale.startswith("en-"):
                long_sources = [
                    source
                    for source in payload["strings"]
                    if len(source) >= 12
                    and not source.startswith(("JSON,", "CC BY"))
                ]
                require_translation_quality(
                    long_sources,
                    {source: mapping[source] for source in long_sources},
                    "publisher-intent-ui",
                    locale,
                )

    def test_campaign_tokens_are_unique_and_app_store_safe(self) -> None:
        tokens = [catalog.campaign_token(locale) for locale in OFFICIAL_LOCALES]
        self.assertEqual(len(tokens), len(set(tokens)))
        for token in tokens:
            self.assertLessEqual(len(token), 30)
            self.assertRegex(token, r"^[a-z0-9_]+$")

    def test_plain_native_app_store_cta_keeps_the_verified_owner(self) -> None:
        app_id = "6792483140"
        source = (
            '<meta name="description" content="تدريب أصلي يعمل بلا اتصال">'
            f'<p><a href="https://apps.apple.com/app/id{app_id}">'
            "احصل على Aim990 Plus من App Store</a></p>"
        )
        self.assertEqual(
            "احصل على Aim990 Plus من App Store",
            catalog._app_store_cta_label(source, app_id),
        )
        with self.assertRaisesRegex(ValueError, "Missing App Store CTA"):
            catalog._app_store_cta_label(source, "6784974530")
        self.assertEqual(
            "تدريب أصلي يعمل بلا اتصال",
            catalog._decision_context(source, False),
        )
        localized_disclosure = catalog.dynamic_ui(
            catalog.load_ui_i18n()["ar-SA"]
        )[catalog.DISCLOSURE]
        self.assertEqual(
            localized_disclosure,
            catalog._publisher_disclosure(
                source,
                False,
                localized_disclosure,
            ),
        )
        with self.assertRaisesRegex(ValueError, "Missing publisher disclosure"):
            catalog._publisher_disclosure(
                source,
                True,
                localized_disclosure,
            )

    def test_answer_disclosure_accepts_the_migration_marker(self) -> None:
        source = (
            '<footer class="footer">'
            '<data class="p-author h-card vcard" value="Lumi Studio"></data>'
            '<div class="wrap" data-publisher-disclosure="true">'
            "Publisher-authored guide from Lumi Studio."
            "</div></footer>"
        )
        self.assertEqual(
            "Publisher-authored guide from Lumi Studio.",
            catalog._publisher_disclosure(source, True, "unused fallback"),
        )

    def test_short_meta_uses_the_localized_app_description(self) -> None:
        app_id = "6791658210"
        source = (
            '<meta name="description" content="短い説明。">'
            '<script type="application/ld+json">'
            + json.dumps(
                {
                    "@type": "SoftwareApplication",
                    "url": f"https://apps.apple.com/app/id{app_id}",
                    "description": (
                        "短い説明。\n\n"
                        "複数の資料を確認できる一つの明確な文脈に整理します。"
                    ),
                },
                ensure_ascii=False,
            )
            + "</script>"
        )
        self.assertEqual(
            "短い説明。 複数の資料を確認できる一つの明確な文脈に整理します。",
            catalog._decision_context(source, False, app_id),
        )

    def test_dynamic_counts_preserve_localized_numerals(self) -> None:
        arabic_digits = str.maketrans("0123456789,", "٠١٢٣٤٥٦٧٨٩٬")
        record_count = f"{catalog.EXPECTED_RECORD_COUNT:,}".translate(
            arabic_digits
        )
        app_count = str(catalog.EXPECTED_APP_COUNT).translate(arabic_digits)
        self.assertEqual(
            f"{record_count} سجل: {app_count} تطبيقًا × ٥٠ إعدادًا.",
            catalog._replace_localized_number(
                catalog._replace_localized_number(
                    "١٬٣٠٠ سجل: ٢٦ تطبيقًا × ٥٠ إعدادًا.",
                    1300,
                    catalog.EXPECTED_RECORD_COUNT,
                ),
                26,
                catalog.EXPECTED_APP_COUNT,
            ),
        )

    def test_live_mcp_distribution_is_exact_and_hash_verified(self) -> None:
        version = "9.8.7"
        expected, responses = mcp_distribution_fixture(version)
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)
        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            state_path = (
                Path(directory)
                / "data"
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            )
            state_path.parent.mkdir(parents=True)
            state_path.write_text('{"truncated":', encoding="utf-8")
            with mock.patch.object(
                catalog,
                "_fetch_bytes",
                side_effect=lambda url, _limit: responses[url],
            ) as fetch:
                distribution = catalog.refresh_live_mcp_distribution(
                    Path(directory)
                )
            self.assertEqual(4, fetch.call_count)
            self.assertEqual(version, distribution["version"])
            self.assertEqual(
                f"{catalog.MCP_REGISTRY_BASE_URL}/{version}",
                distribution["registry_url"],
            )
            self.assertEqual(expected, distribution)
            self.assertEqual(version, catalog.MCP_VERSION)
            self.assertEqual(version, catalog.AGENT_SKILL_VERSION)
            self.assertIn(f"/tree/v{version}/", catalog.AGENT_SKILL_URL)
            for key in catalog.AGENT_SKILL_HOSTS:
                command = catalog.AGENT_SKILL_INSTALL_COMMANDS[key]
                self.assertIn(f"@v{version}", command)
            self.assertIn(
                f"/tree/v{version}/",
                catalog.AGENT_SKILL_INSTALL_COMMANDS["vercel_skills"],
            )
            self.assertNotIn("/latest/", catalog.MCP_NPX_URL)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(distribution, state)
            self.assertEqual(
                [],
                list(
                    state_path.parent.glob(
                        f".{state_path.name}.*.tmp"
                    )
                ),
            )

    def test_live_hash_mismatch_does_not_fall_back_to_frozen_state(
        self,
    ) -> None:
        frozen, _ = mcp_distribution_fixture("8.7.6")
        expected_live, responses = mcp_distribution_fixture("9.8.7")
        responses[str(expected_live["npx_url"])] = b"tampered"
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)
        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            pages = Path(directory)
            state_path = write_mcp_distribution_state(pages, frozen)
            stderr = io.StringIO()
            with mock.patch.object(
                catalog,
                "_fetch_bytes",
                side_effect=lambda url, _limit: responses[url],
            ) as fetch, mock.patch.object(catalog.sys, "stderr", stderr):
                with self.assertRaisesRegex(
                    ValueError,
                    "asset hash mismatch",
                ):
                    catalog.refresh_live_mcp_distribution(pages)
            self.assertEqual(4, fetch.call_count)
            self.assertEqual(
                frozen,
                json.loads(state_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(original, catalog.MCP_DISTRIBUTION)
            self.assertNotIn(
                "MCP_DISTRIBUTION_FROZEN_FALLBACK",
                stderr.getvalue(),
            )

    def test_mcp_fetch_retry_limit_is_bounded(self) -> None:
        for error in (
            TimeoutError("temporary timeout"),
            urllib.error.URLError("temporary resolver failure"),
        ):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(
                    catalog.urllib.request,
                    "urlopen",
                    side_effect=error,
                ) as urlopen, mock.patch.object(
                    catalog.time,
                    "sleep",
                ) as sleep:
                    with self.assertRaises(
                        catalog._MCPTransientFetchError
                    ) as caught:
                        catalog._fetch_bytes(
                            "https://example.invalid/state",
                            1024,
                        )
                self.assertIsInstance(caught.exception.__cause__, type(error))
                self.assertEqual(
                    catalog.MCP_FETCH_MAX_ATTEMPTS,
                    caught.exception.attempts,
                )
                self.assertEqual(
                    catalog.MCP_FETCH_MAX_ATTEMPTS,
                    urlopen.call_count,
                )
                self.assertEqual(
                    list(catalog.MCP_FETCH_RETRY_DELAYS_SECONDS),
                    [call.args[0] for call in sleep.call_args_list],
                )

    def test_http_4xx_does_not_retry_or_use_frozen_state(self) -> None:
        frozen, _ = mcp_distribution_fixture("8.7.6")
        _, responses = mcp_distribution_fixture("9.8.7")
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)
        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            pages = Path(directory)
            state_path = write_mcp_distribution_state(pages, frozen)
            stderr = io.StringIO()
            with mock.patch.object(
                catalog.urllib.request,
                "urlopen",
                side_effect=registry_then_http_error(responses, 404),
            ) as urlopen, mock.patch.object(
                catalog.time,
                "sleep",
            ) as sleep, mock.patch.object(catalog.sys, "stderr", stderr):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    catalog.refresh_live_mcp_distribution(pages)
            self.assertEqual(404, caught.exception.code)
            self.assertEqual(2, urlopen.call_count)
            self.assertEqual(0, sleep.call_count)
            self.assertEqual(
                frozen,
                json.loads(state_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(original, catalog.MCP_DISTRIBUTION)
            self.assertNotIn(
                "MCP_DISTRIBUTION_FROZEN_FALLBACK",
                stderr.getvalue(),
            )

    def test_invalid_registry_identity_does_not_use_frozen_state(self) -> None:
        frozen, _ = mcp_distribution_fixture("8.7.6")
        _, responses = mcp_distribution_fixture("9.8.7")
        registry = json.loads(
            responses[catalog.MCP_REGISTRY_LATEST_URL].decode("utf-8")
        )
        registry["server"]["name"] = "invalid.example/server"
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)
        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            pages = Path(directory)
            state_path = write_mcp_distribution_state(pages, frozen)
            stderr = io.StringIO()
            with mock.patch.object(
                catalog,
                "_fetch_bytes",
                return_value=json.dumps(registry).encode("utf-8"),
            ) as fetch, mock.patch.object(catalog.sys, "stderr", stderr):
                with self.assertRaisesRegex(
                    ValueError,
                    "Registry latest identity is invalid",
                ):
                    catalog.refresh_live_mcp_distribution(pages)
            self.assertEqual(1, fetch.call_count)
            self.assertEqual(
                frozen,
                json.loads(state_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(original, catalog.MCP_DISTRIBUTION)
            self.assertNotIn(
                "MCP_DISTRIBUTION_FROZEN_FALLBACK",
                stderr.getvalue(),
            )

    def test_persistent_5xx_rejects_missing_or_corrupt_frozen_state(
        self,
    ) -> None:
        _, responses = mcp_distribution_fixture("9.8.7")
        cases = (
            (
                "missing",
                None,
                FileNotFoundError,
                "Frozen MCP distribution state is missing",
            ),
            (
                "corrupt",
                '{"truncated":',
                ValueError,
                "Frozen MCP distribution state is invalid",
            ),
        )
        for name, content, error_type, message in cases:
            with self.subTest(state=name):
                with tempfile.TemporaryDirectory(dir=GEO) as directory:
                    pages = Path(directory)
                    if content is not None:
                        state_path = (
                            pages
                            / "data"
                            / catalog.MCP_DISTRIBUTION_STATE_FILENAME
                        )
                        state_path.parent.mkdir(parents=True)
                        state_path.write_text(content, encoding="utf-8")
                    stderr = io.StringIO()
                    with mock.patch.object(
                        catalog.urllib.request,
                        "urlopen",
                        side_effect=registry_then_http_error(
                            responses,
                            500,
                        ),
                    ) as urlopen, mock.patch.object(
                        catalog.time,
                        "sleep",
                    ), mock.patch.object(catalog.sys, "stderr", stderr):
                        with self.assertRaisesRegex(error_type, message):
                            catalog.refresh_live_mcp_distribution(pages)
                    self.assertEqual(
                        catalog.MCP_FETCH_MAX_ATTEMPTS + 1,
                        urlopen.call_count,
                    )
                    self.assertNotIn(
                        "MCP_DISTRIBUTION_FROZEN_FALLBACK",
                        stderr.getvalue(),
                    )

    def test_persistent_5xx_uses_validated_frozen_state(self) -> None:
        frozen, _ = mcp_distribution_fixture("8.7.6")
        _, responses = mcp_distribution_fixture("9.8.7")
        original = dict(catalog.MCP_DISTRIBUTION)
        self.addCleanup(catalog._configure_mcp_distribution, original)

        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            pages = Path(directory)
            state_path = write_mcp_distribution_state(pages, frozen)
            stderr = io.StringIO()
            with mock.patch.object(
                catalog.urllib.request,
                "urlopen",
                side_effect=registry_then_http_error(responses, 500),
            ) as urlopen, mock.patch.object(
                catalog.time,
                "sleep",
            ) as sleep, mock.patch.object(catalog.sys, "stderr", stderr):
                distribution = catalog.refresh_live_mcp_distribution(pages)
            self.assertEqual(frozen, distribution)
            self.assertEqual("8.7.6", catalog.MCP_VERSION)
            self.assertEqual(
                catalog.MCP_FETCH_MAX_ATTEMPTS + 1,
                urlopen.call_count,
            )
            self.assertEqual(
                len(catalog.MCP_FETCH_RETRY_DELAYS_SECONDS),
                sleep.call_count,
            )
            self.assertEqual(
                frozen,
                json.loads(state_path.read_text(encoding="utf-8")),
            )
            warning = stderr.getvalue()
            self.assertIn(
                "WARNING MCP_DISTRIBUTION_FROZEN_FALLBACK",
                warning,
            )
            self.assertIn("source=validated_frozen", warning)
            self.assertIn("http_status=500", warning)
            self.assertIn(
                f"attempts={catalog.MCP_FETCH_MAX_ATTEMPTS}",
                warning,
            )

    def test_frozen_mcp_distribution_rejects_corrupt_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=GEO) as directory:
            path = (
                Path(directory)
                / "data"
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            )
            path.parent.mkdir(parents=True)
            path.write_text('{"truncated":', encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "run publisher_intent_catalog.py first",
            ):
                catalog.use_frozen_mcp_distribution(Path(directory))


class PublisherIntentOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        possible_pages = []
        configured = os.environ.get("GEO_PAGES")
        if configured:
            possible_pages.append(Path(configured))
        possible_pages.extend((GEO / "pages", GEO.parents[1]))
        cls.pages = next(
            (
                path
                for path in possible_pages
                if (
                    path
                    / "data"
                    / f"{catalog.SLUG}.json"
                ).exists()
            ),
            None,
        )
        if cls.pages is None:
            raise unittest.SkipTest("Generated Pages catalog is not present")
        cls.data_dir = cls.pages / "data"
        cls.payload = json.loads(
            (
                cls.data_dir
                / f"{catalog.SLUG}.json"
            ).read_text(encoding="utf-8")
        )
        cls.records = cls.payload["records"]
        cls.availability = catalog.load_storefront_availability(cls.pages)

    def test_records_cover_every_app_and_locale_truthfully(self) -> None:
        self.assertEqual(
            catalog.EXPECTED_APP_COUNT,
            self.payload["app_count"],
        )
        self.assertEqual(50, self.payload["locale_count"])
        self.assertEqual(
            catalog.EXPECTED_RECORD_COUNT,
            self.payload["record_count"],
        )
        self.assertEqual(list(OFFICIAL_LOCALES), self.payload["locales"])
        self.assertFalse(self.payload["measured_search_volume"])
        self.assertFalse(self.payload["is_ranking"])
        self.assertIn("Lumi Studio", self.payload["publisher_disclosure"])

        finder = json.loads(
            (
                self.data_dir
                / catalog.FINDER_DATASET
            ).read_text(encoding="utf-8")
        )
        expected_ids = {
            app["key"]: str(app["app_store_id"])
            for app in finder["apps"]
        }
        self.assertEqual(catalog.EXPECTED_APP_COUNT, len(expected_ids))
        per_app: dict[str, set[str]] = {
            key: set() for key in expected_ids
        }
        record_ids: set[str] = set()
        for record in self.records:
            record_ids.add(record["record_id"])
            key = record["app_key"]
            locale = record["locale"]
            per_app[key].add(locale)
            app_id = expected_ids[key]
            self.assertEqual(app_id, record["app_store_id"])
            self.assertEqual(
                f"https://apps.apple.com/app/id{app_id}",
                record["canonical_app_store_url"],
            )
            parsed = urlparse(record["app_store_url"])
            self.assertEqual("apps.apple.com", parsed.netloc)
            expected_store = catalog.verified_app_store_url(
                record["canonical_app_store_url"],
                locale,
                self.availability,
            )
            self.assertEqual(urlparse(expected_store).path, parsed.path)
            # Campaign attribution is stamped when a provider token exists;
            # the validator still rejects any partial or foreign query.
            self.assertEqual(
                record["app_store_url"],
                validated_app_store_url(record["app_store_url"]),
            )
            self.assertFalse(record["measured_search_volume"])
            self.assertFalse(record["is_ranking"])
            self.assertTrue(record["verified_live"])
            self.assertEqual(
                "publisher_authored_editorially_localized",
                record["query_origin"],
            )
            self.assertGreaterEqual(
                len(record["publisher_disclosure"]),
                20,
            )
            self.assertNotRegex(
                " ".join(
                    str(record[field])
                    for field in (
                        "app_name",
                        "publisher_query",
                        "decision_context",
                        "publisher_disclosure",
                    )
                ),
                r"[\r\n]",
            )
            guide_path = self.pages / urlparse(
                record["canonical_guide_url"]
            ).path.removeprefix("/ios-app-guide/")
            self.assertTrue(guide_path.is_file(), guide_path)
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(record_ids))
        for locales in per_app.values():
            self.assertEqual(set(OFFICIAL_LOCALES), locales)

    def test_mcp_distribution_state_matches_exact_generated_links(self) -> None:
        state = json.loads(
            (
                self.data_dir
                / catalog.MCP_DISTRIBUTION_STATE_FILENAME
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(catalog.MCP_DISTRIBUTION, state)
        self.assertEqual(catalog.MCP_VERSION, state["version"])
        self.assertEqual(catalog.MCP_REGISTRY_URL, state["registry_url"])
        self.assertEqual(catalog.MCP_BUNDLE_URL, state["mcpb_url"])
        self.assertEqual(catalog.MCP_NPX_URL, state["npx_url"])
        self.assertNotIn("/latest/", state["mcpb_url"])
        self.assertNotIn("/latest/", state["npx_url"])
        client_config = json.loads(
            (
                self.data_dir
                / catalog.MCP_CLIENT_CONFIG_FILENAME
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            catalog.mcp_client_config_payload(),
            client_config,
        )
        self.assertEqual(
            ["-y", catalog.MCP_NPX_URL],
            client_config["mcpServers"]["lumi-app-finder"]["args"],
        )

    def test_json_jsonl_and_csv_have_the_same_records(self) -> None:
        jsonl_records = [
            json.loads(line)
            for line in (
                self.data_dir / f"{catalog.SLUG}.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertEqual(self.records, jsonl_records)

        with (
            self.data_dir / f"{catalog.SLUG}.csv"
        ).open(encoding="utf-8", newline="") as handle:
            csv_records = list(csv.DictReader(handle))
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(csv_records))
        self.assertEqual(
            [record["record_id"] for record in self.records],
            [record["record_id"] for record in csv_records],
        )
        for source, exported in zip(self.records, csv_records):
            for field in catalog.CSV_FIELDS:
                expected = (
                    str(source[field]).lower()
                    if isinstance(source[field], bool)
                    else str(source[field])
                )
                self.assertEqual(expected, exported[field])

    def test_schema_declares_non_ranking_non_measured_contract(self) -> None:
        from jsonschema import Draft202012Validator, FormatChecker

        schema = json.loads(
            (
                self.data_dir / f"{catalog.SLUG}.schema.json"
            ).read_text(encoding="utf-8")
        )
        properties = schema["properties"]
        self.assertEqual(False, properties["measured_search_volume"]["const"])
        self.assertEqual(False, properties["is_ranking"]["const"])
        self.assertEqual(
            catalog.EXPECTED_APP_COUNT,
            properties["app_count"]["const"],
        )
        self.assertEqual(50, properties["locale_count"]["const"])
        self.assertEqual(
            catalog.EXPECTED_RECORD_COUNT,
            properties["record_count"]["const"],
        )
        record_properties = properties["records"]["items"]["properties"]
        self.assertEqual(
            False,
            record_properties["measured_search_volume"]["const"],
        )
        self.assertEqual(False, record_properties["is_ranking"]["const"])
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(self.payload)

    def test_croissant_metadata_exposes_all_locales_and_direct_store_fields(
        self,
    ) -> None:
        path = self.data_dir / catalog.CROISSANT_FILENAME
        metadata = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(catalog.CROISSANT_CONTEXT, metadata["@context"])
        self.assertEqual("sc:Dataset", metadata["@type"])
        self.assertEqual(catalog.CROISSANT_SPEC, metadata["conformsTo"])
        self.assertEqual(set(OFFICIAL_LOCALES), set(metadata["name"]))
        self.assertEqual(set(OFFICIAL_LOCALES), set(metadata["description"]))
        self.assertEqual(list(OFFICIAL_LOCALES), metadata["inLanguage"])
        self.assertFalse(metadata["isLiveDataset"])
        self.assertTrue(metadata["isAccessibleForFree"])

        distributions = {
            item["@id"]: item for item in metadata["distribution"]
        }
        expected_files = {
            f"{catalog.SLUG}.json",
            f"{catalog.SLUG}.jsonl",
            f"{catalog.SLUG}.csv",
        }
        self.assertEqual(expected_files, set(distributions))
        record_count_label = f"{catalog.EXPECTED_RECORD_COUNT:,} records"
        for filename, distribution in distributions.items():
            source = self.data_dir / filename
            if filename.endswith((".json", ".jsonl")):
                self.assertIn(
                    record_count_label,
                    distribution["description"],
                )
                self.assertNotIn(
                    "1,400 records",
                    distribution["description"],
                )
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                distribution["sha256"],
            )
            self.assertEqual(
                f"{source.stat().st_size} B",
                distribution["contentSize"],
            )

        record_set = metadata["recordSet"][0]
        self.assertEqual("publisher_intents", record_set["@id"])
        self.assertEqual(
            {"@id": "publisher_intents/record_id"},
            record_set["key"],
        )
        expected_examples = [
            {
                f"publisher_intents/{field}": record[field]
                for field in catalog.CSV_FIELDS
            }
            for record in self.records[:2]
        ]
        self.assertEqual(expected_examples, record_set["examples"])
        self.assertNotIn(
            "publisher_intents/app_store_cta_label",
            record_set["examples"][0],
        )
        fields = {
            field["name"]: field for field in record_set["field"]
        }
        self.assertEqual(set(catalog.CSV_FIELDS), set(fields))
        self.assertEqual(
            "sc:URL",
            fields["app_store_url"]["dataType"],
        )
        self.assertEqual(
            "https://schema.org/downloadUrl",
            fields["app_store_url"]["equivalentProperty"],
        )
        for field in fields.values():
            self.assertEqual(
                {"@id": f"{catalog.SLUG}.csv"},
                field["source"]["fileObject"],
            )
            self.assertEqual(
                {"column": field["name"]},
                field["source"]["extract"],
            )

    @unittest.skipUnless(
        importlib.util.find_spec("mlcroissant"),
        "Official Croissant validation dependency is installed in CI",
    )
    def test_croissant_loads_all_records_with_official_reader(self) -> None:
        import mlcroissant

        metadata_path = self.data_dir / catalog.CROISSANT_FILENAME
        dataset = mlcroissant.Dataset(
            jsonld=metadata_path,
            mapping={
                f"{catalog.SLUG}.csv": (
                    self.data_dir / f"{catalog.SLUG}.csv"
                ),
            },
        )
        loaded = list(dataset.records(record_set="publisher_intents"))
        self.assertEqual(catalog.EXPECTED_RECORD_COUNT, len(loaded))
        self.assertEqual(
            {
                f"publisher_intents/{field}"
                for field in catalog.CSV_FIELDS
            },
            set(loaded[0]),
        )
        validator = Path(sys.executable).with_name("mlcroissant")
        result = subprocess.run(
            [
                str(validator),
                "validate",
                "--jsonld",
                str(metadata_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            result.stdout + result.stderr,
        )

    def test_root_and_all_localized_landings_are_complete(self) -> None:
        pages = [
            ("en", self.data_dir / f"{catalog.SLUG}.html"),
            *[
                (
                    locale,
                    self.pages
                    / locale
                    / "data"
                    / f"{catalog.SLUG}.html",
                )
                for locale in OFFICIAL_LOCALES
            ],
        ]
        self.assertEqual(51, len(pages))
        for locale, path in pages:
            source = path.read_text(encoding="utf-8")
            self.assertIn('white-space:nowrap', source)
            self.assertEqual(
                52,
                len(re.findall(r'<link rel="alternate" hreflang=', source)),
            )
            for media_type in (
                "application/atom+xml",
                "application/rss+xml",
                "application/feed+json",
            ):
                self.assertIn(
                    f'<link rel="alternate" type="{media_type}"',
                    source,
                )
            table_body = re.search(
                r"<tbody>(.*?)</tbody>",
                source,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(table_body)
            self.assertEqual(
                catalog.EXPECTED_APP_COUNT,
                table_body.group(1).count("<tr>"),
            )
            store_urls = re.findall(
                r'href="(https://apps\.apple\.com/'
                r'(?:[a-z]{2}/)?app/id[0-9]+(?:\?[^"]*)?)"',
                table_body.group(1),
            )
            self.assertEqual(catalog.EXPECTED_APP_COUNT, len(store_urls))
            for url in store_urls:
                decoded = html.unescape(url)
                self.assertEqual(decoded, validated_app_store_url(decoded))
            visual_locale = "" if locale == "en" else f"/{locale}"
            self.assertEqual(
                1,
                source.count(
                    f'href="{catalog.SITE}{visual_locale}/visuals/"'
                ),
            )
            if locale in catalog.RTL_LOCALES:
                self.assertRegex(
                    source,
                    rf'<html lang="{re.escape(locale)}" dir="rtl">',
                )
            schema_match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                source,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(schema_match)
            schema = json.loads(html.unescape(schema_match.group(1)))
            self.assertEqual("Dataset", schema["@type"])
            self.assertEqual(catalog.CROISSANT_SPEC, schema["conformsTo"])
            self.assertEqual("Lumi Studio", schema["creator"]["name"])
            subjects = schema["subjectOf"]
            self.assertEqual(2, len(subjects))
            mcp = next(
                subject
                for subject in subjects
                if subject["@id"].endswith("#mcp-server")
            )
            skill = next(
                subject
                for subject in subjects
                if subject["@id"].endswith("#agent-skill")
            )
            self.assertEqual("SoftwareApplication", mcp["@type"])
            self.assertEqual(catalog.MCP_REPOSITORY_URL, mcp["url"])
            self.assertEqual(catalog.MCP_REGISTRY_URL, mcp["sameAs"])
            self.assertEqual(catalog.MCP_BUNDLE_URL, mcp["downloadUrl"])
            self.assertEqual(catalog.MCP_NPX_URL, mcp["installUrl"])
            self.assertEqual(catalog.MCP_VERSION, mcp["softwareVersion"])
            self.assertEqual(
                {
                    "Install in VS Code": catalog.MCP_VSCODE_INSTALL_URL,
                    "Install in Cursor": catalog.MCP_CURSOR_INSTALL_URL,
                },
                {
                    action["name"]: action["target"]
                    for action in mcp["potentialAction"]
                    if action["@type"] == "InstallAction"
                },
            )
            self.assertEqual("SoftwareApplication", skill["@type"])
            self.assertEqual(catalog.AGENT_SKILL_URL, skill["url"])
            self.assertEqual(
                catalog.AGENT_SKILL_VERSION,
                skill["softwareVersion"],
            )
            self.assertEqual(
                catalog.AGENT_SKILL_URL,
                skill["potentialAction"]["target"],
            )
            self.assertIn(
                f'href="{html.escape(catalog.MCP_REGISTRY_URL, quote=True)}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_REPOSITORY_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_BUNDLE_URL}"',
                source,
            )
            self.assertIn(
                (
                    f'href="{html.escape(catalog.MCP_VSCODE_INSTALL_URL, quote=True)}"'
                ),
                source,
            )
            self.assertIn(
                (
                    f'href="{html.escape(catalog.MCP_CURSOR_INSTALL_URL, quote=True)}"'
                ),
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_CHECKSUMS_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.MCP_CLIENT_CONFIG_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.AGENT_SKILL_URL}"',
                source,
            )
            for command in catalog.MCP_INSTALL_COMMANDS.values():
                self.assertIn(html.escape(command), source)
            for command in catalog.AGENT_SKILL_INSTALL_COMMANDS.values():
                self.assertIn(html.escape(command), source)
            self.assertEqual(4, len(schema["distribution"]))
            self.assertEqual(
                {
                    "application/json",
                    "application/x-ndjson",
                    "text/csv",
                    catalog.CROISSANT_MEDIA_TYPE,
                },
                {
                    distribution["encodingFormat"]
                    for distribution in schema["distribution"]
                },
            )
            self.assertIn(
                f'rel="describedby" type="application/ld+json" '
                f'href="{catalog.CROISSANT_URL}"',
                source,
            )
            self.assertIn(
                f'href="{catalog.CROISSANT_URL}">Croissant 1.1</a>',
                source,
            )

    def test_data_hub_and_sitemap_discover_every_landing(self) -> None:
        index = (self.data_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn(catalog.NAME, index)
        self.assertIn(f"{catalog.SLUG}.jsonl", index)
        self.assertIn(f"{catalog.SLUG}.csv", index)
        self.assertIn(catalog.CROISSANT_FILENAME, index)
        self.assertIn("white-space:nowrap", index)
        sitemap = (self.pages / "sitemap_data.xml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(51, sitemap.count(f"/{catalog.SLUG}.html"))
        self.assertIn(catalog.CROISSANT_URL, sitemap)
        feed = json.loads(
            (self.pages / "feed.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            f"{catalog.SITE}/data/{catalog.SLUG}.html",
            {item["url"] for item in feed["items"]},
        )
        self.assertIn(
            "publisher-disclosed",
            feed["description"],
        )
        for filename in ("llms.txt", "llms-full.txt"):
            llms = (self.pages / filename).read_text(encoding="utf-8")
            self.assertIn(f"{catalog.SLUG}.json", llms)
            self.assertIn(f"{catalog.SLUG}.jsonl", llms)
            self.assertIn(f"{catalog.SLUG}.csv", llms)
            self.assertIn(f"{catalog.SLUG}.schema.json", llms)
            self.assertIn(catalog.CROISSANT_FILENAME, llms)

    def test_generated_outputs_are_content_stable(self) -> None:
        digest = hashlib.sha256(
            json.dumps(
                self.records,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(digest, self.payload["content_digest"])
        rebuilt, _ = catalog.build_records(self.pages)
        self.assertEqual(self.records, rebuilt)


if __name__ == "__main__":
    unittest.main()
