#!/usr/bin/env python3
"""The Guide's public host must come from one constant, not 400 literals.

The Pages origin (``alice51849.github.io``) and the owned public host are two
different things that happen to serve the same bytes. Only the origin may appear
in deployment verification; every public identifier -- canonical, hreflang,
sitemap, feed, catalog, IndexNow submission -- has to name the public host.
Memory of this repo is that a rule nobody can fail is a rule that drifts back,
so this test fails instead of trusting anyone to remember.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
GEO = HERE.parent
ROOT = GEO.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import site_config  # noqa: E402

ORIGIN_GUIDE_URL = "https://alice51849.github.io/ios-app-guide"

# Byte-frozen by geo/data/high_intent_guide_sync_contract.json: the Pages deploy
# hashes these against 00_GrowthEngine main, so a byte change here breaks the
# deploy until both repositories land the same wave. They all read GEO_SITE from
# the environment and the Guide workflows pin it, so their literal default never
# reaches a published page.
SYNC_CONTRACT_FROZEN = {
    "geo/high_intent_decision_routes.py",
}
# Standard.site was explicitly migrated in the paired public-root contract wave;
# its consumer no longer receives an origin-literal exemption.
KNOWN_ORIGIN_LITERALS = SYNC_CONTRACT_FROZEN | {
    # site_config declares both hosts; this test names the origin on purpose.
    "geo/site_config.py",
    "geo/tests/test_public_host_single_source.py",
    # The index-reality probe compares the public host against the Pages
    # origin on purpose; its fixtures name the origin as a probe target.
    "agent/test_index_reality_probe.py",
    # The preserved E0 watcher verifies a deployment on both hosts; these are
    # evidence bindings, never emitted public canonicals or submission URLs.
    "agent/gsc_e0_watcher.py",
    "agent/test_gsc_e0_watcher.py",
}


def _python_sources() -> list[Path]:
    paths = []
    for base in ("geo", "agent"):
        for path in sorted((ROOT / base).rglob("*.py")):
            relative = path.relative_to(ROOT)
            if "pages" in relative.parts:
                continue
            paths.append(path)
    return paths


class PublicHostSingleSourceTest(unittest.TestCase):
    def test_public_and_origin_hosts_are_distinct_and_owned(self):
        self.assertEqual(
            site_config.DEFAULT_PUBLIC_SITE,
            "https://open.cait518.cc/ios-app-guide",
        )
        self.assertEqual(site_config.DEFAULT_ORIGIN_SITE, ORIGIN_GUIDE_URL)
        self.assertNotEqual(site_config.PUBLIC_HOST, site_config.ORIGIN_HOST)
        self.assertTrue(site_config.PUBLIC_SITE.startswith("https://"))
        self.assertFalse(site_config.PUBLIC_SITE.endswith("/"))

    def test_environment_can_repoint_the_public_host(self):
        original = os.environ.get("GEO_PUBLIC_SITE")
        try:
            os.environ["GEO_PUBLIC_SITE"] = "https://example.test/guide/"
            import importlib

            reloaded = importlib.reload(site_config)
            self.assertEqual(reloaded.PUBLIC_SITE, "https://example.test/guide")
            self.assertEqual(reloaded.PUBLIC_HOST, "example.test")
            os.environ["GEO_PUBLIC_SITE"] = "http://example.test/guide"
            with self.assertRaises(ValueError):
                importlib.reload(site_config)
        finally:
            if original is None:
                os.environ.pop("GEO_PUBLIC_SITE", None)
            else:
                os.environ["GEO_PUBLIC_SITE"] = original
            import importlib

            importlib.reload(site_config)

    def test_no_generator_hardcodes_the_origin_guide_host(self):
        offenders = []
        for path in _python_sources():
            relative = path.relative_to(ROOT).as_posix()
            if relative in KNOWN_ORIGIN_LITERALS:
                continue
            text = path.read_text(encoding="utf-8")
            if ORIGIN_GUIDE_URL in text:
                offenders.append(relative)
        self.assertEqual(
            offenders,
            [],
            "These files name the Pages origin where a public URL belongs; "
            "import PUBLIC_SITE from site_config instead: "
            f"{offenders}",
        )

    def test_frozen_contract_files_still_read_the_environment(self):
        """The frozen files may keep their literal only because GEO_SITE wins."""
        for relative in sorted(SYNC_CONTRACT_FROZEN):
            with self.subTest(relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                if ORIGIN_GUIDE_URL not in text:
                    continue
                self.assertIn(
                    "GEO_SITE",
                    text,
                    f"{relative} pins the origin host with no way to override "
                    "it; the Guide workflows can no longer move the host.",
                )

    def test_every_public_site_user_imports_the_constant(self):
        missing = []
        for path in _python_sources():
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            if (
                "PUBLIC_SITE" not in text
                or path.name == "site_config.py"
                or relative == "geo/tests/test_public_host_single_source.py"
            ):
                continue
            tree = ast.parse(text)
            # Only a real reference counts; a comment explaining why a file
            # cannot import the constant must not be read as using it.
            referenced = any(
                isinstance(node, ast.Name) and node.id == "PUBLIC_SITE"
                for node in ast.walk(tree)
            )
            if not referenced:
                continue
            imported = any(
                isinstance(node, ast.ImportFrom)
                and node.module == "site_config"
                and any(alias.name == "PUBLIC_SITE" for alias in node.names)
                for node in ast.walk(tree)
            )
            if not imported:
                missing.append(relative)
        self.assertEqual(missing, [], f"PUBLIC_SITE used without importing it: {missing}")


class GuideWorkflowHostTest(unittest.TestCase):
    """The Guide workflows are what actually pin the host in the cloud."""

    def setUp(self):
        pages = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
        self.workflows = pages / ".github" / "workflows"
        if not self.workflows.is_dir():
            self.skipTest("Guide checkout unavailable")

    def _read(self, name: str) -> str:
        return (self.workflows / name).read_text(encoding="utf-8")

    def test_content_workflows_pin_the_public_host(self):
        for name in ("geo-daily.yml", "pages.yml"):
            with self.subTest(name):
                text = self._read(name)
                for line in text.splitlines():
                    if "GEO_SITE:" in line:
                        self.assertIn(site_config.DEFAULT_PUBLIC_SITE, line)

    def test_indexnow_submits_the_public_host(self):
        text = self._read("indexnow-daily.yml")
        self.assertIn(f"--site {site_config.DEFAULT_PUBLIC_SITE}", text)
        self.assertNotIn(f"--site {ORIGIN_GUIDE_URL}", text)

    def test_deployment_verification_still_reads_the_origin(self):
        """Origin and public host serve identical bytes; only the origin proves
        which commit GitHub Pages actually published."""
        for name in ("indexnow-daily.yml", "pages.yml"):
            with self.subTest(name):
                text = self._read(name)
                self.assertIn(
                    f"{ORIGIN_GUIDE_URL}/.well-known/deployment.json", text
                )


if __name__ == "__main__":
    unittest.main()
