#!/usr/bin/env python3
"""Regression tests for the institutional procurement release candidate."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import institutional_procurement as procurement
from official_locales import OFFICIAL_LOCALES


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonicals: list[str] = []
        self.alternates: list[tuple[str, str]] = []
        self.json_alternates: list[str] = []
        self.links: list[str] = []
        self.script_sources: list[str] = []
        self.copy_buttons = 0
        self.article_ids: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href", ""))
        if tag == "link" and values.get("rel") == "alternate":
            if values.get("hreflang"):
                self.alternates.append(
                    (values["hreflang"], values.get("href", ""))
                )
            if values.get("type") == "application/json":
                self.json_alternates.append(values.get("href", ""))
        if tag == "a":
            self.links.append(values.get("href", ""))
            if values.get("target"):
                raise AssertionError("Procurement links must not auto-open a tab")
        if tag == "script" and values.get("src"):
            self.script_sources.append(values["src"])
        if tag == "button" and values.get("data-copy"):
            self.copy_buttons += 1
        if tag == "article" and values.get("id"):
            self.article_ids.append(values["id"])


class InstitutionalProcurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pages = Path(os.environ.get("GEO_PAGES", GEO.parents[1]))
        cls.manifest = json.loads(
            procurement.MANIFEST_PATH.read_text(encoding="utf-8")
        )
        cls.i18n = json.loads(
            procurement.I18N_PATH.read_text(encoding="utf-8")
        )["localizations"]
        cls.root_data = json.loads(
            (cls.pages / procurement.data_relative(None)).read_text(
                encoding="utf-8"
            )
        )
        source_paths = procurement._source_paths(cls.pages, cls.manifest)
        cls.finder = json.loads(
            source_paths["verified_catalog"].read_text(encoding="utf-8")
        )
        cls.lookup = json.loads(
            source_paths["public_lookup"].read_text(encoding="utf-8")
        )
        cls.intent_source = json.loads(
            source_paths["publisher_intent"].read_text(encoding="utf-8")
        )
        cls.intent_overrides = json.loads(
            source_paths["intent_overrides"].read_text(encoding="utf-8")
        )

    def test_generated_tree_is_current(self) -> None:
        summary = procurement.build(self.pages, check=True)
        self.assertEqual(46, summary["apps"])
        self.assertEqual(50, summary["locales"])
        self.assertEqual(204, summary["html_pages"])
        self.assertEqual(51, summary["localized_roster_json"])
        self.assertEqual(56, summary["json_files"])
        self.assertEqual(3, summary["canary"])

    def test_source_sha_pins_and_release_status(self) -> None:
        self.assertEqual("CANDIDATE_NOT_DEPLOYED", self.manifest["release_status"])
        self.assertEqual(46, self.manifest["expected_app_count"])
        self.assertEqual(50, self.manifest["expected_locale_count"])
        self.assertEqual(
            "BLOCKED_PENDING_ADMIN_VERIFICATION",
            self.manifest["canary"]["status"],
        )
        self.assertEqual(3, len(self.manifest["canary"]["app_keys"]))
        for record in self.manifest["source_files"].values():
            path = self.pages / record["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(record["sha256"], actual, path)
        procurement._validate_official_source_expiry(self.manifest)

    def test_official_source_expiry_fails_closed(self) -> None:
        with mock.patch.object(
            procurement,
            "_today",
            return_value=date(2026, 9, 14),
        ):
            with self.assertRaisesRegex(
                procurement.BlockedNotDeployable,
                "Official source expired",
            ):
                procurement._validate_official_source_expiry(self.manifest)

    def test_public_lookup_expiry_fails_closed(self) -> None:
        with mock.patch.object(
            procurement,
            "_today",
            return_value=date(2026, 9, 3),
        ):
            with self.assertRaisesRegex(
                procurement.BlockedNotDeployable,
                "Expired or future-dated evidence: public lookup",
            ):
                procurement._validate_evidence_freshness(
                    self.manifest,
                    self.lookup,
                    json.loads(
                        (
                            self.pages
                            / self.manifest["source_files"]["storefront_state"]["path"]
                        ).read_text(encoding="utf-8")
                    ),
                )

    def test_source_sha_drift_fails_closed(self) -> None:
        scratch = self.pages / "_engine" / "geo" / "tests" / ".institutional-scratch"
        if scratch.exists():
            for path in sorted(scratch.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
        scratch.mkdir(parents=True)
        try:
            (scratch / "source.json").write_text("{}\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "release_status": "CANDIDATE_NOT_DEPLOYED",
                "source_files": {
                    "source": {
                        "path": "source.json",
                        "sha256": "0" * 64,
                    }
                },
            }
            path = scratch / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(procurement, "MANIFEST_PATH", path):
                with self.assertRaisesRegex(
                    procurement.BlockedNotDeployable,
                    "Source SHA drift",
                ):
                    procurement._load_manifest(scratch)
        finally:
            for path in sorted(scratch.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            scratch.rmdir()

    def test_exact_46_app_roster_and_digest(self) -> None:
        apps = self.root_data["apps"]
        self.assertEqual(46, len(apps))
        ids = [app["app_store_id"] for app in apps]
        self.assertEqual(46, len(set(ids)))
        expected_ids = {
            str(app["app_store_id"]) for app in self.finder["apps"]
        }
        self.assertEqual(expected_ids, set(ids))
        lookup = {
            item["app_store_id"]: item for item in self.lookup["records"]
        }
        for app in apps:
            evidence = lookup[app["app_store_id"]]
            self.assertEqual(evidence["bundle_id"], app["bundle_id"])
            self.assertEqual(evidence["public_name"], app["public_name"])
            self.assertEqual(
                evidence["canonical_app_store_url"],
                app["canonical_app_store_url"],
            )
            self.assertEqual(evidence["support_url"], app["support_url"])
            self.assertEqual(evidence["privacy_url"], app["privacy_url"])
            self.assertEqual(evidence["platforms"], app["platforms"])
            self.assertTrue(app["verified_live"])
        self.assertEqual(
            "sha256:fea82924a4facecbf07394ed7e86d966970b2ba8db1fa21110d5debbde6a8f18",
            self.root_data["roster_digest"],
        )

    def test_purchase_groups_and_iap_boundary(self) -> None:
        apps = self.root_data["apps"]
        paid = [app for app in apps if app["purchase_model"] == "paid_upfront"]
        free_iap = [
            app
            for app in apps
            if app["purchase_model"] == "free_with_lifetime_unlock"
        ]
        self.assertEqual(12, len(paid))
        self.assertEqual(34, len(free_iap))
        self.assertEqual(0, self.root_data["counts"]["fully_free"])
        self.assertEqual(3, self.root_data["counts"]["canary"])
        self.assertEqual(
            {"notesstudio100", "aim990plus", "wifiaid"},
            {app["app_key"] for app in apps if app["canary"]},
        )
        for app in paid:
            self.assertEqual("paid_download", app["download_model"])
            self.assertEqual(
                "included_in_paid_download",
                app["unlock_model"],
            )
            self.assertEqual(
                "asm_apps_and_books_paid_candidate",
                app["deployment_class"],
            )
            self.assertTrue(
                app["institutional_policy"][
                    "device_assignment_language_allowed"
                ]
            )
            self.assertTrue(
                app["institutional_policy"][
                    "volume_procurement_language_allowed"
                ]
            )
        for app in free_iap:
            self.assertEqual("free_download", app["download_model"])
            self.assertEqual(
                "optional_one_time_iap_individual_purchase",
                app["unlock_model"],
            )
            self.assertEqual(
                "intune_direct_store_free_tier_evaluation",
                app["deployment_class"],
            )
            self.assertIn(
                "in-app purchases are incompatible",
                app["limitation"],
            )
            self.assertFalse(
                app["institutional_policy"][
                    "device_assignment_language_allowed"
                ]
            )
            self.assertFalse(
                app["institutional_policy"][
                    "volume_procurement_language_allowed"
                ]
            )
            self.assertEqual(
                "NOT_APPLICABLE_REQUIRES_INDIVIDUAL_PERSONAL_APPLE_ACCOUNT",
                app["institutional_policy"]["full_unlock_distribution"],
            )
        for app in apps:
            self.assertFalse(app["institutional_exposure_verified"])
            self.assertFalse(app["institutional_approval_verified"])
            self.assertFalse(app["discount_verified"])

    def test_platform_and_ipad_truth_come_from_public_lookup(self) -> None:
        self.assertEqual(46, self.root_data["counts"]["ipad_supported"])
        for app in self.root_data["apps"]:
            self.assertEqual(["iPhone", "iPad"], app["platforms"])
            self.assertTrue(app["ipad_supported"])
            self.assertEqual("public_get", app["lookup_provenance"]["method"])
            self.assertEqual(self.lookup["checked_at"], app["last_checked"])

    def test_support_privacy_and_store_urls_are_exact_https(self) -> None:
        for app in self.root_data["apps"]:
            app_id = app["app_store_id"]
            self.assertEqual(
                f"https://apps.apple.com/app/id{app_id}",
                app["canonical_app_store_url"],
            )
            for field in (
                "canonical_app_store_url",
                "campaign_app_store_url",
                "support_url",
                "privacy_url",
            ):
                self.assertTrue(app[field].startswith("https://"), (app_id, field))
            self.assertRegex(app["bundle_id"], r"^[A-Za-z0-9][A-Za-z0-9.-]+$")
            self.assertNotIn(procurement.OLD_EMAIL, json.dumps(app).casefold())

    def test_campaign_attribution_is_exact_first_party_catalog_data(self) -> None:
        intents = {
            (record["locale"], record["app_key"]): record
            for record in self.intent_source["records"]
        }
        for locale in OFFICIAL_LOCALES:
            payload = json.loads(
                (
                    self.pages / procurement.data_relative(locale)
                ).read_text(encoding="utf-8")
            )
            for app in payload["apps"]:
                expected = intents[(locale, app["app_key"])]["app_store_url"]
                self.assertEqual(expected, app["campaign_app_store_url"])
                query = parse_qs(urlsplit(expected).query)
                self.assertEqual(
                    query["pt"][0],
                    app["campaign_attribution"]["provider_token"],
                )
                self.assertEqual(
                    query["ct"][0],
                    app["campaign_attribution"]["campaign_token"],
                )
                self.assertEqual(["8"], query["mt"])

    def test_related_fit_uses_evidence_and_omits_weak_matches(self) -> None:
        apps = {
            app["app_key"]: app for app in self.root_data["apps"]
        }
        self.assertEqual(10, self.root_data["counts"]["school_related"])
        self.assertEqual(7, self.root_data["counts"]["business_related"])
        self.assertEqual(["school"], apps["aim990plus"]["related_fit"])
        self.assertEqual(["business"], apps["wifiaid"]["related_fit"])
        for key in (
            "battai",
            "caldaily",
            "cvdesk",
            "dailymate",
            "gmoney",
            "snapport",
            "tripbee",
        ):
            self.assertEqual([], apps[key]["related_fit"], key)

    def test_only_three_evidence_bounded_canary_pages_exist(self) -> None:
        expected = set(self.manifest["canary"]["app_keys"])
        all_keys = {app["app_key"] for app in self.root_data["apps"]}
        for route in [None, *OFFICIAL_LOCALES]:
            directory = (
                self.pages / procurement.APP_DIR
                if route is None
                else self.pages / route / procurement.APP_DIR
            )
            actual = {path.stem for path in directory.glob("*.html")}
            self.assertEqual(expected, actual, route)
        self.assertTrue(expected < all_keys)
        iap = next(
            app
            for app in self.root_data["apps"]
            if app["app_key"] == "notesstudio100"
        )
        self.assertEqual(
            "BLOCKED_FREE_TIER_ONLY_IAP_NOT_DISTRIBUTABLE",
            iap["canary_status"],
        )
        for key in {"aim990plus", "wifiaid"}:
            paid = next(
                app for app in self.root_data["apps"] if app["app_key"] == key
            )
            self.assertEqual(
                "BLOCKED_PORTAL_VISIBILITY_UNVERIFIED",
                paid["canary_status"],
            )

    def test_all_50_locale_routes_have_native_copy_and_no_fallback(self) -> None:
        finder_keys = {app["key"] for app in self.finder["apps"]}
        records = procurement._intent_records(
            self.intent_source,
            finder_keys,
        )
        records = procurement._apply_intent_overrides(
            records,
            self.intent_overrides,
            finder_keys,
        )
        procurement._validate_no_intent_fallback(records, finder_keys)
        for locale in OFFICIAL_LOCALES:
            page = self.pages / procurement.page_relative(locale)
            data = self.pages / procurement.data_relative(locale)
            self.assertTrue(page.is_file(), locale)
            self.assertTrue(data.is_file(), locale)
            payload = json.loads(data.read_text(encoding="utf-8"))
            self.assertEqual(locale, payload["locale"])
            self.assertEqual(46, len(payload["apps"]))
            self.assertEqual(
                self.manifest["canary"]["app_keys"],
                payload["canary"]["app_keys"],
            )
            by_key = {app["app_key"]: app for app in payload["apps"]}
            for key in finder_keys:
                self.assertEqual(
                    records[(locale, key)]["publisher_query"],
                    by_key[key]["publisher_query"],
                )
                self.assertEqual(
                    records[(locale, key)]["decision_context"],
                    by_key[key]["decision_context"],
                )
            for key in self.manifest["canary"]["app_keys"]:
                app_page = self.pages / procurement.app_page_relative(
                    locale,
                    key,
                )
                self.assertTrue(app_page.is_file(), f"{locale}/{key}")
                source = app_page.read_text(encoding="utf-8")
                self.assertIn(by_key[key]["bundle_id"], source)
                self.assertIn(by_key[key]["app_store_id"], source)
                self.assertIn(
                    f'download={by_key[key]["download_model"]}',
                    source,
                )
                self.assertIn(
                    f'unlock={by_key[key]["unlock_model"]}',
                    source,
                )
                self.assertIn(by_key[key]["campaign_attribution"]["campaign_token"], source)
                self.assertIn(procurement.ALLOWED_EMAIL, source)
                self.assertIn("BLOCKED", source)

    def test_deep_workflows_and_locale_quality_gate(self) -> None:
        self.assertEqual(set(OFFICIAL_LOCALES), set(self.i18n))
        for locale, mapping in self.i18n.items():
            expected = 5 if locale in procurement.DEEP_WORKFLOW_LOCALES else 3
            self.assertGreaterEqual(len(mapping["steps"]), expected, locale)
            self.assertEqual(procurement.SOURCE_FIELDS, set(mapping))
            self.assertEqual(procurement.LABEL_FIELDS, set(mapping["labels"]))
        procurement._load_i18n()

    def test_root_and_localized_hreflang_are_complete(self) -> None:
        routes = [None, *OFFICIAL_LOCALES]
        for route in routes:
            parser = PageParser()
            parser.feed(
                (self.pages / procurement.page_relative(route)).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual([procurement.page_url(route)], parser.canonicals)
            expected = {
                (locale, procurement.page_url(locale))
                for locale in OFFICIAL_LOCALES
            }
            expected.add(("x-default", procurement.page_url(None)))
            self.assertEqual(expected, set(parser.alternates))
            self.assertEqual(
                [procurement.data_url(route)],
                parser.json_alternates,
            )
            self.assertEqual(15, parser.copy_buttons, route)
            self.assertEqual(3, len(parser.article_ids), route)
            self.assertEqual([], parser.script_sources)
            for app_key in self.manifest["canary"]["app_keys"]:
                app_parser = PageParser()
                app_parser.feed(
                    (
                        self.pages
                        / procurement.app_page_relative(route, app_key)
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    [procurement.app_page_url(route, app_key)],
                    app_parser.canonicals,
                )
                app_expected = {
                    (
                        locale,
                        procurement.app_page_url(locale, app_key),
                    )
                    for locale in OFFICIAL_LOCALES
                }
                app_expected.add(
                    ("x-default", procurement.app_page_url(None, app_key))
                )
                self.assertEqual(app_expected, set(app_parser.alternates))
                self.assertEqual(5, app_parser.copy_buttons)
                self.assertEqual(1, len(app_parser.article_ids))
                self.assertEqual([], app_parser.script_sources)

    def test_pages_have_no_tracking_or_automatic_external_open(self) -> None:
        banned = re.compile(
            r"(?i)<script[^>]+src=|<iframe|fetch\s*\(|XMLHttpRequest|"
            r"sendBeacon|localStorage|sessionStorage|document\.cookie"
        )
        for route in [None, *OFFICIAL_LOCALES]:
            paths = [self.pages / procurement.page_relative(route)]
            paths.extend(
                self.pages / procurement.app_page_relative(route, app_key)
                for app_key in self.manifest["canary"]["app_keys"]
            )
            for path in paths:
                source = path.read_text(encoding="utf-8")
                self.assertIsNone(banned.search(source), path)
                self.assertIn("navigator.clipboard.writeText", source)
                self.assertNotIn('target="_blank"', source)

    def test_content_digests_validate_for_every_json_output(self) -> None:
        paths = [
            self.pages / procurement.data_relative(None),
            *[
                self.pages / procurement.data_relative(locale)
                for locale in OFFICIAL_LOCALES
            ],
            *[
                self.pages / procurement.ROOT_DIR / name
                for name in procurement.SCORECARD_NAMES.values()
            ],
            self.pages / procurement.STATE_PATH,
        ]
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            digest = payload.pop("content_digest")
            self.assertEqual(
                f"sha256:{procurement._canonical_digest(payload)}",
                digest,
                path,
            )

    def test_scorecards_keep_unobserved_stages_at_zero(self) -> None:
        expected_stages = [
            "inventory",
            "deployed",
            "http_get",
            "qualified_click",
            "institutional_download",
        ]
        self.assertEqual(expected_stages, self.manifest["measurement"]["stages"])
        for days, name in procurement.SCORECARD_NAMES.items():
            payload = json.loads(
                (self.pages / procurement.ROOT_DIR / name).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(days, payload["window_days"])
            self.assertEqual(expected_stages, [
                metric["stage"] for metric in payload["metrics"]
            ])
            self.assertEqual(46, payload["metrics"][0]["value"])
            self.assertEqual("VERIFIED", payload["metrics"][0]["status"])
            for metric in payload["metrics"][1:]:
                self.assertEqual(0, metric["value"])
                self.assertEqual("PENDING", metric["status"])
            self.assertIn(
                "ordinary_asc_downloads_excluded",
                payload["metrics"][-1]["source"],
            )
            self.assertEqual(5, payload["privacy_rule"]["threshold"])
            self.assertEqual(
                "report_as_range_1_to_4_or_PENDING",
                payload["privacy_rule"]["values_1_to_4"],
            )

    def test_sitemap_covers_51_pages_and_hreflang(self) -> None:
        root = ET.parse(self.pages / procurement.SITEMAP_NAME).getroot()
        namespace = f"{{{procurement.SITEMAP_NS}}}"
        xhtml = f"{{{procurement.XHTML_NS}}}"
        urls = root.findall(f"{namespace}url")
        self.assertEqual(204, len(urls))
        expected_locations = {
            procurement.page_url(None),
            *(
                procurement.page_url(locale)
                for locale in OFFICIAL_LOCALES
            ),
        }
        for app_key in self.manifest["canary"]["app_keys"]:
            expected_locations.add(procurement.app_page_url(None, app_key))
            expected_locations.update(
                procurement.app_page_url(locale, app_key)
                for locale in OFFICIAL_LOCALES
            )
        self.assertEqual(
            expected_locations,
            {
                node.findtext(f"{namespace}loc")
                for node in urls
            },
        )
        for node in urls:
            alternates = node.findall(f"{xhtml}link")
            self.assertEqual(51, len(alternates))
            self.assertEqual(
                set(OFFICIAL_LOCALES) | {"x-default"},
                {alternate.attrib["hreflang"] for alternate in alternates},
            )
            location = node.findtext(f"{namespace}loc") or ""
            matching_keys = [
                key
                for key in self.manifest["canary"]["app_keys"]
                if f"/apps/{key}.html" in location
            ]
            if matching_keys:
                key = matching_keys[0]
                expected_hrefs = {
                    procurement.app_page_url(locale, key)
                    for locale in OFFICIAL_LOCALES
                } | {procurement.app_page_url(None, key)}
            else:
                expected_hrefs = {
                    procurement.page_url(locale)
                    for locale in OFFICIAL_LOCALES
                } | {procurement.page_url(None)}
            self.assertEqual(
                expected_hrefs,
                {alternate.attrib["href"] for alternate in alternates},
            )

    def test_crawl_registration_and_existing_content_preservation(self) -> None:
        shared = {
            "apps-index": Path("apps/index.html"),
            "robots": Path("robots.txt"),
            "sitemap-index": Path("sitemap_index.xml"),
        }
        for name, relative in shared.items():
            current = (self.pages / relative).read_text(encoding="utf-8")
            block = procurement._extract_block(current, name)
            self.assertIsNotNone(block, name)
            base = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.pages),
                    "show",
                    f"origin/main:{relative.as_posix()}",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if name == "robots":
                restored = current.replace(f"{block}\n", "", 1)
            else:
                restored = current.replace(f"{block}\n", "", 1)
            self.assertEqual(base, restored, relative)
        self.assertIn(
            "../institutional/ios-procurement.html",
            (self.pages / "apps/index.html").read_text(encoding="utf-8"),
        )
        self.assertIn(
            procurement.sitemap_url(),
            (self.pages / "robots.txt").read_text(encoding="utf-8"),
        )
        self.assertIn(
            procurement.sitemap_url(),
            (self.pages / "sitemap_index.xml").read_text(encoding="utf-8"),
        )

    def test_marker_upsert_is_idempotent_and_preserves_surroundings(self) -> None:
        source = "<main>existing</main>\n"
        block = procurement._managed_block(
            "apps-index",
            "<section>candidate</section>",
        )
        first = procurement._upsert_block(
            source,
            "apps-index",
            block,
            "</main>",
        )
        second = procurement._upsert_block(
            first,
            "apps-index",
            block,
            "</main>",
        )
        self.assertEqual(first, second)
        self.assertEqual(
            source,
            first.replace(f"{block}\n", "", 1),
        )

    def test_full_generator_is_idempotent_on_two_runs(self) -> None:
        first = procurement.build(self.pages)
        second = procurement.build(self.pages)
        self.assertEqual(0, first["changed_files"])
        self.assertEqual(0, second["changed_files"])
        self.assertEqual(first["roster_digest"], second["roster_digest"])

    def test_claim_email_price_and_rating_gates(self) -> None:
        files = [
            self.pages / procurement.page_relative(None),
            self.pages / procurement.data_relative(None),
            *[
                self.pages / procurement.page_relative(locale)
                for locale in OFFICIAL_LOCALES
            ],
            *[
                self.pages / procurement.data_relative(locale)
                for locale in OFFICIAL_LOCALES
            ],
        ]
        for route in [None, *OFFICIAL_LOCALES]:
            files.extend(
                self.pages / procurement.app_page_relative(route, app_key)
                for app_key in self.manifest["canary"]["app_keys"]
            )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertNotIn(procurement.OLD_EMAIL.casefold(), combined.casefold())
        self.assertIn(procurement.ALLOWED_EMAIL, combined)
        for email in procurement.EMAIL_RE.findall(combined):
            self.assertEqual(procurement.ALLOWED_EMAIL, email.casefold())
        for fragment in self.manifest["prohibited_claim_fragments"]:
            self.assertNotIn(fragment.casefold(), combined.casefold())
        self.assertIsNone(
            re.search(
                r'(?i)"(?:price|rating|review_count|institutional_price)"\s*:',
                combined,
            )
        )

    def test_schema_files_are_versioned_and_strict_at_root(self) -> None:
        primary = json.loads(
            (
                self.pages
                / procurement.ROOT_DIR
                / procurement.SCHEMA_NAME
            ).read_text(encoding="utf-8")
        )
        scorecard = json.loads(
            (
                self.pages
                / procurement.ROOT_DIR
                / procurement.SCORECARD_SCHEMA_NAME
            ).read_text(encoding="utf-8")
        )
        for schema in (primary, scorecard):
            self.assertEqual(
                "https://json-schema.org/draft/2019-09/schema",
                schema["$schema"],
            )
            self.assertEqual(1, schema["x-schema-version"])
            self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
