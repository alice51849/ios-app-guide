#!/usr/bin/env python3
"""Workflow wiring checks for Standard.site Guide reconciliation."""

import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/geo-daily.yml"
MIRROR_SHA256 = {
    "_engine/social/gen_standard_site.py": (
        "2e0e0ad340cb716001bcc467c5ad396b363e2882c1eb3025606bc97998b843cf"
    ),
    "_engine/social/standard_site_publish.py": (
        "5a5082ed531619afe83031daa0826843e0a558733f5caa948099844ea00193cd"
    ),
    "_engine/social/tests/test_standard_site.py": (
        "1e227c1918982d631d5fa24c1fc94c24b70c65a83a3a70b7fa5d5c420e54fe16"
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
