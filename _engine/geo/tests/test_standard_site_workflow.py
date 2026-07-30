#!/usr/bin/env python3
"""Workflow wiring checks for Standard.site Guide reconciliation."""

import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/geo-daily.yml"
os.environ.setdefault("STANDARD_SITE_ENGINE_ROOT", str(ROOT / "_engine"))
os.environ.setdefault("GEO_PAGES", str(ROOT))
sys.path.insert(0, str(ROOT / "_engine/social"))

import gen_standard_site as generator  # noqa: E402


MIRROR_SHA256 = {
    "_engine/social/gen_standard_site.py": (
        "2e0e0ad340cb716001bcc467c5ad396b363e2882c1eb3025606bc97998b843cf"
    ),
    "_engine/social/standard_site_publish.py": (
        "6328db1b26d87c9ceda5dd13cd7db2a9f3c07ac65962dfce0ba3bebc14b3b246"
    ),
    "_engine/social/tests/test_standard_site.py": (
        "245a747da439929ebd0c862ed0180232a41e7737d889f09810569baae6ad8a59"
    ),
}


class StandardSiteWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_fixed_configurable_threads_contract_url(self):
        self.assertIn(
            "STANDARD_SITE_GUIDE_CONTRACT_URL: "
            "https://raw.githubusercontent.com/alice51849/alice51849.github.io/"
            "main/standard_site_guide_contract.json",
            self.source,
        )
        self.assertNotIn("github.event.inputs", self.source.split(
            "STANDARD_SITE_GUIDE_CONTRACT_URL:", 1
        )[1].splitlines()[0])

    def test_growth_candidate_is_published_as_byte_exact_mirror(self):
        for relative, expected in MIRROR_SHA256.items():
            with self.subTest(relative=relative):
                self.assertEqual(
                    expected,
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                )
        generator = (
            ROOT / "_engine/social/gen_standard_site.py"
        ).read_text(encoding="utf-8")
        self.assertIn('os.environ.get("STANDARD_SITE_ENGINE_ROOT", ROOT)', generator)
        self.assertIn(
            'STANDARD_SITE_ENGINE_ROOT="$GITHUB_WORKSPACE/_engine"',
            self.source,
        )
        self.assertIn(
            '-s _engine/social/tests \\\n'
            '              -p "test_standard_site.py"',
            self.source,
        )

    def test_ai_brief_has_three_deployed_deep_documents(self):
        manifest = generator.build_manifest(
            pages=ROOT,
            max_per_app=3,
            now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
        documents = [
            document
            for document in manifest["documents"]
            if document["app_key"] == "aibriefpack"
        ]
        self.assertEqual(3, len(documents))
        self.assertEqual(
            {
                "/answers/"
                "best-private-app-to-organize-screenshots-and-documents-"
                "into-context-before-using-ai.html",
                "/answers/best-organize-context-for-ai-app.html",
                "/answers/best-turn-screenshots-into-ai-brief-app.html",
            },
            {document["path"] for document in documents},
        )
        combined = " ".join(
            document["text_content"] for document in documents
        ).casefold()
        self.assertIn("source and confidence", combined)
        self.assertIn("never removed automatically", combined)
        self.assertIn("does not promise anonymity", combined)
        self.assertIn("publisher disclosure:", combined)

    def test_gmoney_lite_has_three_deployed_deep_documents(self):
        manifest = generator.build_manifest(
            pages=ROOT,
            max_per_app=3,
            now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
        documents = [
            document
            for document in manifest["documents"]
            if document["app_key"] == "gmoneylite"
        ]
        self.assertEqual(3, len(documents))
        self.assertEqual(
            {
                "/answers/"
                "best-free-travel-expense-tracker-with-currency-conversion-"
                "for-iphone.html",
                "/answers/"
                "travel-expense-tracker-with-saved-or-manual-exchange-rates-"
                "offline.html",
                "/answers/"
                "travel-budget-app-with-category-statistics-and-one-time-"
                "lifetime-unlock.html",
            },
            {document["path"] for document in documents},
        )
        combined = " ".join(
            document["text_content"] for document in documents
        ).casefold()
        self.assertIn("one trip and up to three saved expenses", combined)
        self.assertIn("saved or manually set exchange rate", combined)
        self.assertIn("category statistics remain available", combined)
        self.assertIn("one optional lifetime purchase", combined)
        self.assertIn("publisher disclosure:", combined)

    def test_mask_my_file_has_three_deployed_deep_documents(self):
        manifest = generator.build_manifest(
            pages=ROOT,
            max_per_app=3,
            now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
        documents = [
            document
            for document in manifest["documents"]
            if document["app_key"] == "maskmyfile"
        ]
        self.assertEqual(3, len(documents))
        self.assertEqual(
            {
                "/answers/"
                "best-on-device-file-redaction-app-for-freelancers-sharing-"
                "client-documents.html",
                "/answers/"
                "how-to-permanently-redact-a-pdf-on-iphone-and-verify-the-"
                "protected-copy.html",
                "/answers/"
                "batch-redact-the-same-private-text-from-up-to-100-files-on-"
                "iphone.html",
            },
            {document["path"] for document in documents},
        )
        combined = " ".join(
            document["text_content"] for document in documents
        ).casefold()
        self.assertIn("processed on the device", combined)
        self.assertIn("new protected copy", combined)
        self.assertIn("up to 100 files", combined)
        self.assertIn("one optional lifetime purchase", combined)
        self.assertIn("publisher disclosure:", combined)

    def test_tripbee_lite_has_three_deployed_deep_documents(self):
        manifest = generator.build_manifest(
            pages=ROOT,
            max_per_app=3,
            now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
        documents = [
            document
            for document in manifest["documents"]
            if document["app_key"] == "tripbeelite"
        ]
        self.assertEqual(3, len(documents))
        self.assertEqual(
            {
                "/answers/"
                "best-simple-trip-planner-app-for-one-upcoming-trip-iphone"
                ".html",
                "/answers/"
                "free-travel-planner-for-one-journey-with-a-packing-list"
                ".html",
                "/answers/"
                "travel-itinerary-app-with-a-one-time-unlock-instead-of-a-"
                "subscription.html",
            },
            {document["path"] for document in documents},
        )
        by_path = {
            document["path"]: document["text_content"].casefold()
            for document in documents
        }
        one_trip = by_path[
            "/answers/"
            "best-simple-trip-planner-app-for-one-upcoming-trip-iphone.html"
        ]
        self.assertIn("one complete journey", one_trip)
        self.assertIn("without a time limit", one_trip)
        self.assertIn("edited or replaced", one_trip)
        self.assertIn(
            "no account and has no ads, analytics or tracking",
            one_trip,
        )

        packing = by_path[
            "/answers/"
            "free-travel-planner-for-one-journey-with-a-packing-list.html"
        ]
        self.assertIn("packing workflow remains visible", packing)
        self.assertIn("requires the optional lifetime unlock", packing)
        self.assertIn("sharing, backup and restore", packing)

        sharing = by_path[
            "/answers/"
            "travel-itinerary-app-with-a-one-time-unlock-instead-of-a-"
            "subscription.html"
        ]
        self.assertIn("interactive single-day switch", sharing)
        self.assertIn("offline content and compact controls", sharing)
        self.assertIn("zip containing the html", sharing)
        self.assertIn(
            "other supported destinations receive the original html",
            sharing,
        )
        self.assertIn(
            "does not claim real-time collaborative itinerary editing",
            sharing,
        )
        for document in documents:
            self.assertIn(
                "publisher disclosure:",
                document["text_content"].casefold(),
            )

    def test_every_sync_has_timeout_retry_and_initial_404_policy(self):
        commands = re.findall(
            r"python3 _engine/geo/sync_standard_site\.py \\\n"
            r"(?P<arguments>(?:\s+--[^\n]+\n?)+)",
            self.source,
        )
        self.assertGreaterEqual(len(commands), 5)
        for arguments in commands:
            with self.subTest(arguments=arguments):
                self.assertIn('--site-root "$GITHUB_WORKSPACE"', arguments)
                self.assertIn(
                    '--contract-url "$STANDARD_SITE_GUIDE_CONTRACT_URL"',
                    arguments,
                )
                self.assertIn("--allow-initial-404", arguments)
                self.assertIn("--timeout 10", arguments)
                self.assertIn("--retries 3", arguments)
                self.assertIn("--retry-delay 2", arguments)

    def test_sync_runs_after_each_generation_and_after_each_rebase(self):
        first_generation = self.source.index("python3 gen_feed.py")
        first_sync = self.source.index(
            "python3 _engine/geo/sync_standard_site.py", first_generation
        )
        first_test = self.source.index(
            "Verify zero-cost growth infrastructure", first_sync
        )
        self.assertLess(first_generation, first_sync)
        self.assertLess(first_sync, first_test)

        refresh = self.source.index("Refresh AI indexes + hubs")
        english_commit = self.source.index("Commit English content first", refresh)
        self.assertIn(
            "python3 _engine/geo/sync_standard_site.py",
            self.source[refresh:english_commit],
        )

        final_cleanup = self.source.index("Final link and availability cleanup")
        localized_commit = self.source.index(
            "Commit localized pages if any", final_cleanup
        )
        self.assertIn(
            "python3 _engine/geo/sync_standard_site.py",
            self.source[final_cleanup:localized_commit],
        )

        for marker in (
            'git pull --rebase --autostash -X theirs',
        ):
            starts = [match.start() for match in re.finditer(re.escape(marker), self.source)]
            self.assertEqual(2, len(starts))
            for start in starts:
                end = self.source.find("git push", start)
                self.assertGreater(end, start)
                self.assertIn(
                    "python3 _engine/geo/sync_standard_site.py",
                    self.source[start:end],
                )


if __name__ == "__main__":
    unittest.main()
