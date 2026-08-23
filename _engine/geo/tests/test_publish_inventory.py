#!/usr/bin/env python3
"""Blocking tests for the reversible Pages publish inventory."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
GUIDE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(GEO))

import publish_inventory  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402


SHA = "a" * 40
SITE = "https://alice51849.github.io/ios-app-guide"


def page(*links: str, noindex: bool = False) -> str:
    robots = (
        '<meta name="robots" content="noindex,follow">'
        if noindex
        else '<meta name="robots" content="index,follow">'
    )
    anchors = "".join(f'<a href="{link}">link</a>' for link in links)
    return (
        "<!doctype html><html><head>"
        f"{robots}<title>Fixture</title></head>"
        f"<body>{anchors}</body></html>"
    )


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


class PublishInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        self.policy = copy.deepcopy(
            publish_inventory.load_policy(
                GEO / "publish_inventory_policy.json"
            )
        )
        self.policy["budgets"].update(
            {
                "max_publish_files": 1000,
                "max_publish_bytes": 10_000_000,
                "max_publish_html_files": 1000,
            }
        )
        self.policy_path = self.base / "policy.json"
        self._write_required_tree()
        self._write_policy()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_policy(self) -> None:
        self.policy_path.write_text(
            json.dumps(self.policy, sort_keys=True),
            encoding="utf-8",
        )

    def _write_required_tree(self) -> None:
        protected_pages = [
            "answers/keep.html",
            "guides/keep.html",
            "hubs/keep.html",
            "tools/keep.html",
        ]
        official_pages = [
            f"{locale}/index.html" for locale in OFFICIAL_LOCALES
        ]
        links = [
            *(f"/ios-app-guide/{path}" for path in protected_pages),
            *(f"/ios-app-guide/{path}" for path in official_pages),
            "/ios-app-guide/misc/a-original.html",
            "/ios-app-guide/misc/reachable-noindex.html",
        ]
        write(self.source / "index.html", page(*links))
        for relative in protected_pages:
            write(self.source / relative, page())
        for relative in official_pages:
            write(self.source / relative, page())
        write(self.source / "assets/site.css", "body{}")
        write(self.source / ".well-known/api-catalog", "catalog\n")
        write(self.source / ".nojekyll", "")
        write(self.source / "feed.xml", "<feed />\n")
        write(self.source / "rss.xml", "<rss />\n")
        write(self.source / "feed.json", "{}\n")
        write(
            self.source / "robots.txt",
            f"Sitemap: {SITE}/sitemap_index.xml\n",
        )
        write(
            self.source / "sitemap.xml",
            (
                '<?xml version="1.0"?><urlset>'
                f"<url><loc>{SITE}/index.html</loc></url>"
                "</urlset>"
            ),
        )
        write(
            self.source / "sitemap_index.xml",
            (
                '<?xml version="1.0"?><sitemapindex>'
                f"<sitemap><loc>{SITE}/sitemap.xml</loc></sitemap>"
                "</sitemapindex>"
            ),
        )
        for locale in OFFICIAL_LOCALES:
            write(
                self.source
                / "data/app-install-decision-routes/feeds"
                / f"{locale}.atom.xml",
                "<feed />\n",
            )
        duplicate = page()
        write(self.source / "misc/a-original.html", duplicate)
        write(self.source / "misc/z-copy.html", duplicate)
        write(
            self.source / "misc/reachable-noindex.html",
            page(noindex=True),
        )
        write(self.source / "micro/dead.html", page(noindex=True))
        write(self.source / "README.md", "not part of Pages\n" + ("x" * 50000))
        write(self.source / ".github/workflows/pages.yml", "private\n")
        write(self.source / "_engine/private.py", "private\n")

    def _run(self, *, source_commit: str = SHA, **kwargs) -> dict:
        return publish_inventory.run(
            self.source,
            policy_path=self.policy_path,
            source_commit=source_commit,
            **kwargs,
        )

    def test_safe_exclusion_preserves_every_protected_surface(self) -> None:
        manifest = self._run()
        included = set(manifest["included"])
        excluded = {
            item["path"]: item["reasons"]
            for item in manifest["excluded"]
        }
        self.assertIn("micro/dead.html", excluded)
        self.assertEqual(
            ["orphan", "noindex"],
            excluded["micro/dead.html"],
        )
        self.assertIn("misc/z-copy.html", excluded)
        self.assertEqual(
            ["orphan", "duplicate"],
            excluded["misc/z-copy.html"],
        )
        self.assertIn("misc/reachable-noindex.html", included)
        for locale in OFFICIAL_LOCALES:
            self.assertIn(f"{locale}/index.html", included)
        for prefix in (
            ".well-known/",
            "answers/",
            "assets/",
            "guides/",
            "hubs/",
            "tools/",
        ):
            self.assertTrue(any(path.startswith(prefix) for path in included))
        self.assertEqual(0, manifest["safety"]["excluded_protected_files"])
        self.assertFalse(manifest["safety"]["source_content_deleted"])
        self.assertTrue((self.source / "micro/dead.html").is_file())

    def test_manifest_and_materialized_tree_are_deterministic(self) -> None:
        first = self.base / "first.json"
        second = self.base / "second.json"
        self._run(manifest_out=first)
        self._run(manifest_out=second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

        output = self.base / "publish"
        manifest = self._run(output=output)
        self.assertEqual(
            first.read_bytes(),
            (output / ".well-known/publish-inventory.json").read_bytes(),
        )
        expected_deployment = publish_inventory.deployment_bytes(SHA)
        self.assertEqual(
            expected_deployment,
            (output / ".well-known/deployment.json").read_bytes(),
        )
        self.assertFalse((output / "micro/dead.html").exists())
        self.assertFalse((output / "README.md").exists())
        self.assertFalse((output / ".github").exists())
        self.assertFalse((output / "_engine").exists())
        actual_files = sum(
            item.is_file() for item in output.rglob("*")
        )
        self.assertEqual(manifest["publish"]["files"], actual_files)

    def test_sparse_git_tree_dry_run_matches_worktree_inventory(self) -> None:
        subprocess.run(
            ["git", "init", "--quiet", str(self.source)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.source), "add", "-A"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=Inventory Test",
                "-c",
                "user.email=inventory@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            ],
            check=True,
        )
        commit = subprocess.run(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        worktree = self._run(source_commit=commit)
        tree = self._run(source_commit=commit, tree_ref="HEAD")
        self.assertEqual(
            worktree["inventory_sha256"],
            tree["inventory_sha256"],
        )
        self.assertEqual(worktree["legacy"], tree["legacy"])
        self.assertEqual(worktree["publish"], tree["publish"])
        self.assertEqual(worktree["analysis"], tree["analysis"])

    def test_git_source_commit_mismatch_blocks_publication(self) -> None:
        subprocess.run(
            ["git", "init", "--quiet", str(self.source)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.source), "add", "-A"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "-c",
                "user.name=Inventory Test",
                "-c",
                "user.email=inventory@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            ],
            check=True,
        )
        with self.assertRaisesRegex(
            publish_inventory.InventoryError,
            "source commit mismatch",
        ):
            self._run(tree_ref="HEAD")

    def test_sitemap_to_noindex_page_blocks_publication(self) -> None:
        write(
            self.source / "sitemap.xml",
            (
                '<?xml version="1.0"?><urlset>'
                f"<url><loc>{SITE}/index.html</loc></url>"
                f"<url><loc>{SITE}/micro/dead.html</loc></url>"
                "</urlset>"
            ),
        )
        with self.assertRaisesRegex(
            publish_inventory.InventoryError,
            "sitemap noindex HTML targets 1",
        ):
            self._run()

    def test_missing_official_feed_blocks_publication(self) -> None:
        (
            self.source
            / "data/app-install-decision-routes/feeds/en-US.atom.xml"
        ).unlink()
        with self.assertRaisesRegex(
            publish_inventory.InventoryError,
            "missing required localized feed: .*en-US",
        ):
            self._run()

    def test_file_budget_blocks_publication_without_output(self) -> None:
        self.policy["budgets"]["max_publish_files"] = 1
        self._write_policy()
        output = self.base / "blocked-output"
        with self.assertRaisesRegex(
            publish_inventory.InventoryError,
            "publish files",
        ):
            self._run(output=output)
        self.assertFalse(output.exists())

    def test_pages_and_indexnow_workflows_use_same_inventory_gate(self) -> None:
        pages = (
            GUIDE_ROOT / ".github/workflows/pages.yml"
        ).read_text(encoding="utf-8")
        indexnow = (
            GUIDE_ROOT / ".github/workflows/indexnow-daily.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("publish_inventory.py", pages)
        self.assertIn(
            "python3 -m unittest -v "
            "_engine.geo.tests.test_publish_inventory",
            pages,
        )
        self.assertIn('path: ${{ runner.temp }}/pages-publish', pages)
        self.assertIn(
            '--feed-dir "${{ runner.temp }}/pages-publish"',
            pages,
        )
        self.assertIn("publish_inventory.py", indexnow)
        self.assertIn('--source-commit "$DEPLOYED_SHA"', indexnow)
        self.assertIn(".well-known/deployment.json", indexnow)


if __name__ == "__main__":
    unittest.main()
