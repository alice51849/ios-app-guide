from __future__ import annotations

import sys
import unittest
from pathlib import Path


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import reconcile_answer_semantics as reconciliation
from official_locales import OFFICIAL_LOCALE_SET


def answer_page(app_id: str, body: str) -> str:
    return (
        '<html lang="en"><head>'
        '<meta name="apple-itunes-app" '
        f'content="app-id={app_id}, app-argument=https://example.com">'
        "</head><body><!-- answer-content:start --><main>"
        f"<h1>Project ledger</h1>{body}</main>"
        "<!-- answer-content:end --></body></html>"
    )


class MoneyTagPrivacyReconciliationTests(unittest.TestCase):
    def test_missing_boundary_is_added_visibly_and_once(self) -> None:
        path = Path("answers/project-ledger.html")
        source = answer_page(
            reconciliation.MONEYTAG_APP_ID,
            "<p>Track income and expenses by project.</p>",
        )

        repaired = reconciliation.planned_moneytag_privacy_repair(
            path,
            source,
        )

        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertEqual(
            (),
            reconciliation.missing_moneytag_privacy_disclosures(repaired),
        )
        self.assertEqual(1, repaired.count("moneytag-network-boundary"))
        self.assertLess(
            repaired.index("moneytag-network-boundary"),
            repaired.index("</main>"),
        )
        self.assertIsNone(
            reconciliation.planned_moneytag_privacy_repair(path, repaired)
        )

    def test_non_moneytag_answer_is_unchanged(self) -> None:
        source = answer_page(
            "6780575828",
            "<p>Prepare a passport photo.</p>",
        )

        self.assertIsNone(
            reconciliation.planned_moneytag_privacy_repair(
                Path("answers/passport-photo.html"),
                source,
            )
        )

    def test_exact_50_localized_boundaries_come_from_reviewed_metadata(
        self,
    ) -> None:
        disclosures = (
            reconciliation.moneytag_localized_privacy_disclosures()
        )

        self.assertEqual(OFFICIAL_LOCALE_SET, set(disclosures))
        for locale, disclosure in disclosures.items():
            with self.subTest(locale=locale):
                self.assertIn("Frankfurter", disclosure)
                self.assertIn("ExchangeRate-API", disclosure)
                self.assertIn("Cloudflare", disclosure)
                self.assertIn("api.frankfurter.dev", disclosure)
                self.assertIn("open.er-api.com", disclosure)

    def test_localized_boundary_is_added_visibly_and_once(self) -> None:
        locale = "zh-Hant"
        path = Path(locale) / "answers" / "project-ledger.html"
        source = answer_page(
            reconciliation.MONEYTAG_APP_ID,
            "<p>依專案追蹤收入與支出。</p>",
        )
        disclosure = (
            reconciliation.moneytag_localized_privacy_disclosure(locale)
        )

        repaired = reconciliation.planned_moneytag_privacy_repair(
            path,
            source,
            locale,
        )

        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertIn(disclosure, reconciliation.answer_content_text(repaired))
        self.assertEqual(
            (),
            reconciliation.missing_moneytag_privacy_disclosures(
                repaired,
                locale,
            ),
        )
        self.assertEqual(1, repaired.count("moneytag-network-boundary"))
        self.assertIsNone(
            reconciliation.planned_moneytag_privacy_repair(
                path,
                repaired,
                locale,
            )
        )
