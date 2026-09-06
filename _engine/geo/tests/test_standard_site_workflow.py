#!/usr/bin/env python3
"""Workflow wiring checks for Standard.site Guide reconciliation."""

import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
import unittest


def _deployed_site_root() -> Path | None:
    """The published site checkout this file is deployed inside, if any.

    Unlike the other mirrored tests this one cannot be made layout-agnostic:
    it pins sha256 digests of ``_engine/social/*`` and imports the engine from
    ``ROOT/_engine``. Pointed at ``geo/pages`` from the 00_GrowthEngine
    checkout it would build a hybrid import graph (canon modules already on
    ``sys.path``, mirror data under ROOT) and fail for reasons that say
    nothing about the site. So it asserts only where it is deployed — the
    pages repo — and skips elsewhere, while the file itself stays
    byte-identical on both sides so the mirror audit keeps covering it.
    """
    root = Path(__file__).resolve().parents[3]
    if (root / ".github/workflows/geo-daily.yml").is_file():
        return root
    return None


DEPLOYED_ROOT = _deployed_site_root()
IS_DEPLOYED = DEPLOYED_ROOT is not None
# Placeholder keeps the module importable (and the engine resolvable) in the
# 00_GrowthEngine checkout; every assertion is skipped there.
ROOT = DEPLOYED_ROOT or Path(__file__).resolve().parents[1] / "pages"
WORKFLOW = ROOT / ".github/workflows/geo-daily.yml"
os.environ.setdefault("STANDARD_SITE_ENGINE_ROOT", str(ROOT / "_engine"))
os.environ.setdefault("GEO_PAGES", str(ROOT))
sys.path.insert(0, str(ROOT / "_engine/social"))
sys.path.insert(0, str(ROOT / "_engine/geo"))

from app_store_storefronts import (  # noqa: E402
    validated_app_store_url,
)
import gen_standard_site as generator  # noqa: E402


MIRROR_SHA256 = {
    "_engine/social/gen_standard_site.py": (
        "bb5360a9861abe6e20d49b65b2501a2317ec4ffac6178d7246e827c13f75a95a"
    ),
    "_engine/social/standard_site_publish.py": (
        "393067b95201a7b671ea5127d31ce0e489085ea0e4794d647615d461e872d30f"
    ),
    "_engine/social/tests/test_standard_site.py": (
        "a0e6d8f7bc870d98ec9fb96a7a428660bc37a5cb5d3f0391f438e9974fe49274"
    ),
}


@unittest.skipUnless(
    IS_DEPLOYED, "runs from the deployed pages checkout (<site>/_engine/geo/tests)"
)
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
            # hero result tools are extra Standard.site documents, not deep answers
            and document.get("editorial_kind") != "tool"
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
            # hero result tools are extra Standard.site documents, not deep answers
            and document.get("editorial_kind") != "tool"
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
        self.assertIn("one optional purchase", combined)
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
            # hero result tools are extra Standard.site documents, not deep answers
            and document.get("editorial_kind") != "tool"
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
        self.assertIn("one optional purchase", combined)
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
            # hero result tools are extra Standard.site documents, not deep answers
            and document.get("editorial_kind") != "tool"
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
        self.assertIn("requires the optional one-time unlock", packing)
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

    def test_wifi_aid_has_three_deployed_deep_documents(self):
        manifest = generator.build_manifest(
            pages=ROOT,
            max_per_app=3,
            now=datetime(2026, 7, 30, tzinfo=timezone.utc),
        )
        documents = [
            document
            for document in manifest["documents"]
            if document["app_key"] == "wifiaid"
            # hero result tools are extra Standard.site documents, not deep answers
            and document.get("editorial_kind") != "tool"
        ]
        self.assertEqual(3, len(documents))
        self.assertEqual(
            {
                "/answers/"
                "how-to-troubleshoot-wi-fi-connected-but-no-internet-on-"
                "iphone.html",
                "/answers/"
                "how-to-tell-if-one-website-is-down-or-my-whole-internet-"
                "connection-on-iphone.html",
                "/answers/"
                "how-to-document-intermittent-internet-problems-on-iphone-"
                "for-isp-support.html",
            },
            {document["path"] for document in documents},
        )
        by_path = {
            document["path"]: document["text_content"].casefold()
            for document in documents
        }
        connected = by_path[
            "/answers/"
            "how-to-troubleshoot-wi-fi-connected-but-no-internet-on-"
            "iphone.html"
        ]
        self.assertIn("most likely explanation with confidence", connected)
        self.assertIn(
            "bounded tcp stability samples with variation",
            connected,
        )
        self.assertIn("numeric-ip tcp observation only", connected)
        self.assertIn("not a packet capture", connected)
        self.assertIn("no iap, subscription, trial", connected)

        destination = by_path[
            "/answers/"
            "how-to-tell-if-one-website-is-down-or-my-whole-internet-"
            "connection-on-iphone.html"
        ]
        self.assertIn("dns, tcp, tls, ttfb and http", destination)
        self.assertIn(
            "only a bounded numeric-ip tcp observation",
            destination,
        )
        self.assertIn("does not inspect the server", destination)
        self.assertIn("prove the site is globally down", destination)

        intermittent = by_path[
            "/answers/"
            "how-to-document-intermittent-internet-problems-on-iphone-"
            "for-isp-support.html"
        ]
        self.assertIn("bounded series of tcp samples", intermittent)
        self.assertIn("not icmp packet-loss measurement", intermittent)
        self.assertIn("not packet loss or rssi", intermittent)
        self.assertIn("numeric-ip tcp direct ip", intermittent)
        self.assertIn("private history stored on the device", intermittent)
        index = (ROOT / "answers/index.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "sitemap_answers.xml").read_text(encoding="utf-8")
        self.assertIn(
            'title="iOS App Guide — latest answers &amp; guides (Atom)"',
            index,
        )
        for document in documents:
            path = document["path"]
            html = (ROOT / path.removeprefix("/")).read_text(encoding="utf-8")
            self.assertIn(path, index)
            self.assertEqual(
                1,
                sitemap.count(
                    f"https://open.cait518.cc/ios-app-guide{path}"
                ),
            )
            self.assertIn(
                "publisher disclosure:",
                document["text_content"].casefold(),
            )
            self.assertIn(
                f'<link rel="canonical" href="'
                f'https://open.cait518.cc/ios-app-guide{path}">',
                html,
            )
            # The Standard.site document carries the paid edition's editorial
            # copy, so its own link stays on the paid App. The *page* may have
            # been re-rendered on the free door by free-first ownership (its
            # copy then describes Lite), in which case its Smart App Banner
            # must open the same door the page's direct links open — never a
            # banner for one edition above copy and links for the other.
            page_ids = re.findall(r"apps\.apple\.com/(?:[a-z]{2}/)?app/id(\d{9,12})", html)
            door = max(set(page_ids), key=page_ids.count)
            self.assertIn(door, {"6790467886", "6793414462"})
            self.assertIn(f'content="app-id={door},', html)
            # Direct Apple links only; they carry this site's own campaign
            # attribution once a provider token is configured, so match the
            # target app and let the validator reject anything malformed.
            store_urls = re.findall(
                r'href="(https://apps\.apple\.com/'
                rf'(?:[a-z]{{2}}/)?app/id{door}(?:\?[^"]*)?)"',
                html,
            )
            self.assertTrue(store_urls)
            for url in store_urls:
                # "html" is the page source here, so unescape by hand.
                decoded = url.replace("&amp;", "&")
                self.assertEqual(decoded, validated_app_store_url(decoded))
            edition = "WiFi Aid Lite" if door == "6793414462" else "WiFi Aid"
            self.assertRegex(
                html,
                r'<a class="cta" href="https://apps\.apple\.com/app/'
                rf'id{door}(?:\?[^"]*)?" rel="nofollow noopener">'
                rf"Get {edition} on the App Store →</a>",
            )
            self.assertIn(
                "This is a publisher-authored buying guide from the app "
                "developer.",
                html,
            )
            self.assertNotIn(
                "Try WiFi Aid on a real example first",
                html,
            )
            if door == "6790467886":
                # Only the paid door states its own pricing model; the free
                # door page describes Lite and must not carry paid copy.
                self.assertIn("paid download with no free trial", html)
            else:
                self.assertNotIn("paid download with no free trial", html)
            self.assertNotIn(
                "alternatives/wifiaid-no-subscription.html",
                html,
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

    def test_sync_runs_after_generation_and_each_remote_integration(self):
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

        phases = ("reconcile_english_phase", "reconcile_localized_phase")
        for phase in phases:
            start = self.source.index(f"{phase}()")
            end = self.source.index(
                f"remote_first_publish {phase} origin main 5",
                start,
            )
            with self.subTest(phase=phase):
                self.assertGreater(end, start)
                self.assertIn(
                    "python3 _engine/geo/sync_standard_site.py",
                    self.source[start:end],
                )

        helper = (
            ROOT / ".github/scripts/remote-first-publish.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("git fetch --no-tags", helper)
        self.assertIn("git merge --no-edit -X theirs", helper)
        self.assertIn("git merge-base --is-ancestor", helper)
        self.assertIn(
            'git push "$remote" "HEAD:refs/heads/${branch}"',
            helper,
        )
        for forbidden in ("rebase", "reset --hard", "--force"):
            self.assertNotIn(forbidden, helper)


if __name__ == "__main__":
    unittest.main()
