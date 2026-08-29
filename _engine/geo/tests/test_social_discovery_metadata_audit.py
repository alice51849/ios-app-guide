#!/usr/bin/env python3
"""Hermetic tests for the install-decision social metadata gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import struct
import sys
import unittest
from unittest import mock
import uuid


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import app_install_decision_routes
import social_discovery_metadata_audit


class SocialDiscoveryMetadataAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = (
            Path(__file__).parent
            / ".social-discovery-test-work"
            / f"{os.getpid()}-{uuid.uuid4().hex}"
        )
        self.root.mkdir(parents=True)
        self.locales = ("en-US", "ar-SA")
        self.records = [
            self._record(
                "en-US",
                "best private notes app for iphone",
                "Keep private notes available without sending the text away.",
                "Free",
                "USD",
            ),
            self._record(
                "ar-SA",
                "أفضل تطبيق ملاحظات خاصة على iPhone",
                "احتفظ بالملاحظات الخاصة من دون إرسال النص إلى جهة أخرى.",
                "مجاني",
                "SAR",
            ),
        ]
        catalogue = {
            "record_count": 1,
            "apps": [
                {
                    "key": "fixture",
                    "app_store_id": "1234567890",
                    "name": "Fixture Notes",
                    "one_time_option": True,
                }
            ],
        }
        dataset = {
            "locale_count": len(self.locales),
            "record_count": len(self.records),
            "locales": list(self.locales),
            "records": self.records,
        }
        data = self.root / "data"
        data.mkdir()
        (data / "verified-ios-app-finder-catalog.json").write_text(
            json.dumps(catalogue),
            encoding="utf-8",
        )
        (data / "app-install-decision-routes.json").write_text(
            json.dumps(dataset),
            encoding="utf-8",
        )
        image = self.root / "social/img/fixture-share.jpg"
        image.parent.mkdir(parents=True)
        image.write_bytes(
            b"\xff\xd8\xff\xc0\x00\x08\x08"
            + struct.pack(">HH", 675, 1200)
            + b"\x03\xff\xd9"
        )
        with mock.patch.object(
            app_install_decision_routes,
            "OFFICIAL_LOCALES",
            self.locales,
        ), mock.patch.dict(
            app_install_decision_routes.gen_social_previews.APPSTORE,
            {"fixture": "1234567890"},
        ):
            for record in self.records:
                page = (
                    self.root
                    / app_install_decision_routes.decision_page_relative(
                        "fixture",
                        record["locale"],
                    )
                )
                page.parent.mkdir(parents=True)
                page.write_text(
                    app_install_decision_routes.render_page(
                        record,
                        "2026-08-29",
                        "Fixture feed",
                    ),
                    encoding="utf-8",
                )

    def tearDown(self) -> None:
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def _record(
        self,
        locale: str,
        query: str,
        context: str,
        formatted_price: str,
        currency: str,
    ) -> dict[str, object]:
        page = (
            f"{social_discovery_metadata_audit.SITE}/apps/fixture/"
            f"decision/l/{locale}/index.html"
        )
        store = (
            "https://apps.apple.com/app/id1234567890"
            f"?pt=118326163&ct=fixture_{locale.lower()}&mt=8"
        )
        return {
            "record_id": f"{locale}:fixture",
            "locale": locale,
            "app_key": "fixture",
            "app_name": "Fixture Notes",
            "publisher_query": query,
            "decision_context": context,
            "category": "productivity",
            "purchase_label": "Lifetime unlock",
            "badge_labels": ["Private notes", formatted_price],
            "decision_page_url": page,
            "canonical_guide_url": (
                f"{social_discovery_metadata_audit.SITE}/{locale}/fixture.html"
            ),
            "locale_index_url": (
                f"{social_discovery_metadata_audit.SITE}/data/"
                f"app-install-decision-routes/locales/{locale}.json"
            ),
            "canonical_app_store_url": (
                "https://apps.apple.com/app/id1234567890"
            ),
            "app_store_url": store,
            "app_store_id": "1234567890",
            "app_store_cta_label": "Open App Store",
            "guide_cta_label": "Read guide",
            "publisher_disclosure": (
                "First-party decision support from the app developer."
            ),
            "oembed_url": (
                f"{social_discovery_metadata_audit.SITE}/oembed/decision/"
                f"{locale}/fixture.json"
            ),
            "storefront_facts": {
                "price": "0",
                "currency": currency,
                "formatted_price": formatted_price,
            },
        }

    def _audit(self) -> dict[str, object]:
        return social_discovery_metadata_audit.audit_site(
            self.root,
            expected_app_count=1,
            expected_locales=self.locales,
        )

    def test_generated_pages_pass_structural_gate(self) -> None:
        report = self._audit()
        self.assertEqual("pass", report["result"], report["issue_counts"])
        self.assertEqual(2, report["scope"]["parsed_pages"])
        self.assertEqual(
            2,
            report["checks"]["json_ld_software_application"]["passed"],
        )
        self.assertEqual(2, report["checks"]["json_ld_product"]["passed"])
        self.assertEqual(2, report["checks"]["json_ld_faq"]["passed"])
        self.assertEqual(2, report["checks"]["json_ld_breadcrumb"]["passed"])
        self.assertEqual(2, report["checks"]["og_locale_alternates"]["passed"])

    def test_gate_detects_missing_open_graph_locale_alternate(self) -> None:
        path = (
            self.root
            / "apps/fixture/decision/l/ar-SA/index.html"
        )
        source = path.read_text(encoding="utf-8")
        source = source.replace(
            '<meta property="og:locale:alternate" content="en_US">\n',
            "",
            1,
        )
        path.write_text(source, encoding="utf-8")
        report = self._audit()
        self.assertEqual("fail", report["result"])
        self.assertEqual(
            1,
            report["issue_counts"]["invalid_og_locale_alternates"],
        )

    def test_private_report_writer_uses_mode_0600(self) -> None:
        report = self.root / "private/report.json"
        social_discovery_metadata_audit._write_private_json(
            report,
            {"result": "pass"},
        )
        self.assertEqual(0o600, report.stat().st_mode & 0o777)
        self.assertEqual(
            {"result": "pass"},
            json.loads(report.read_text(encoding="utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
