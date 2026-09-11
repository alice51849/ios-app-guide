"""Public root identities must not inherit an origin hostname or escape the audit."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import gen_llms
import public_origin_audit
import site_config
import static_api_catalog
import sync_standard_site
import zhuyin_resourcesync
from . import test_sync_standard_site as contract_tests


class PublicRootDiscoveryTests(unittest.TestCase):
    def test_root_discovery_identifiers_use_the_authoritative_public_root(self):
        self.assertEqual(site_config.PUBLIC_ROOT + "/.well-known/resourcesync",
                         gen_llms.RESOURCE_SYNC_SOURCE)
        self.assertEqual(gen_llms.RESOURCE_SYNC_SOURCE, zhuyin_resourcesync.SOURCE_DESCRIPTION_URL)
        self.assertEqual(site_config.PUBLIC_ROOT + "/.well-known/api-catalog",
                         static_api_catalog.ROOT_API_CATALOG)
        self.assertEqual(site_config.PUBLIC_SITE, sync_standard_site.PUBLICATION_URL)
        self.assertEqual(site_config.PUBLIC_ROOT + sync_standard_site.WELL_KNOWN_PATH,
                         sync_standard_site.WELL_KNOWN_URL)

    def test_root_and_guide_paths_follow_public_site_overrides(self):
        code = (
            "import json,site_config,gen_llms,zhuyin_resourcesync,static_api_catalog,sync_standard_site;"
            "print(json.dumps([gen_llms.RESOURCE_SYNC_SOURCE,zhuyin_resourcesync.CAPABILITY_LIST_URL,"
            "static_api_catalog.ROOT_API_CATALOG,sync_standard_site.PUBLICATION_URL,"
            "sync_standard_site.WELL_KNOWN_URL]))"
        )
        env = dict(os.environ, GEO_PUBLIC_SITE="https://public.example.test/catalog", GEO_SITE="https://public.example.test/catalog")
        result = subprocess.run([sys.executable, "-c", code], cwd=GEO, env=env,
                                capture_output=True, text=True, check=True)
        self.assertEqual([
            "https://public.example.test/.well-known/resourcesync",
            "https://public.example.test/catalog/resourcesync/capabilitylist.xml",
            "https://public.example.test/.well-known/api-catalog",
            "https://public.example.test/catalog",
            "https://public.example.test/.well-known/site.standard.publication/ios-app-guide",
        ], json.loads(result.stdout))

    def test_root_extensionless_well_known_is_not_an_audit_blind_spot(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as work:
            root = Path(work)
            (root / ".well-known").mkdir()
            (root / ".well-known/resourcesync").write_text(
                f'<loc>{site_config.ORIGIN_ROOT}/.well-known/resourcesync</loc>'
            )
            result = public_origin_audit.audit_public_artifacts(root)
            self.assertFalse(result["passed"])
            self.assertEqual(".well-known/resourcesync", result["findings"][0]["path"])
            self.assertEqual(1, result["origin_occurrences"])

    def test_all_public_formats_are_checked_without_a_content_allowlist(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as work:
            root = Path(work)
            for name in ("llms.txt", "catalog.json", "sitemap.xml", "index.html", "README.md"):
                (root / name).write_text(site_config.ORIGIN_ROOT)
            result = public_origin_audit.audit_public_artifacts(root)
            self.assertEqual(5, len(result["findings"]))
            (root / "_engine").mkdir()
            (root / "_engine/verify.py").write_text(site_config.ORIGIN_ROOT)
            self.assertEqual(5, public_origin_audit.audit_public_artifacts(root)["files_checked"])

    def test_root_export_has_no_origin_and_second_generation_is_a_noop(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as work:
            root = Path(work)
            first = zhuyin_resourcesync.export_root_discovery(root)
            target = root / first["path"]
            original, timestamp = target.read_bytes(), target.stat().st_mtime_ns
            second = zhuyin_resourcesync.export_root_discovery(root)
            self.assertEqual(first, second)
            self.assertEqual(original, target.read_bytes())
            self.assertEqual(timestamp, target.stat().st_mtime_ns)
            self.assertTrue(public_origin_audit.audit_public_artifacts(root)["passed"])
            self.assertIn(zhuyin_resourcesync.CAPABILITY_LIST_URL.encode(), original)

    def test_public_projection_preserves_external_urls_and_non_url_text(self):
        origin = site_config.ORIGIN_ROOT
        source = f"Policy {origin}/100notes-support/privacy.html. External https://example.org/a?q=1#x"
        expected = f"Policy {site_config.PUBLIC_ROOT}/100notes-support/privacy.html. External https://example.org/a?q=1#x"
        self.assertEqual(expected, site_config.public_reference_text(source))
        self.assertEqual(site_config.PUBLIC_SITE + "/en-US/zipbox.html",
                         site_config.public_reference_url(site_config.ORIGIN_SITE + "/en-US/zipbox.html"))

    def test_partial_normal_generators_preserve_all_non_host_bytes(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as work:
            pages = Path(work)
            (pages / "api").mkdir()
            texts = {
                "llms.txt": "Catalog\n" + site_config.ORIGIN_ROOT + "/.well-known/resourcesync\n",
                "llms-full.txt": "Library " + site_config.ORIGIN_ROOT + "/library/\n",
                "api/index.html": (
                    '<head><link rel="site.standard.publication" href="at://unchanged">'
                    '<link rel="api-catalog" href="' + site_config.ORIGIN_ROOT +
                    '/.well-known/api-catalog"></head><body><nav>Keep this</nav></body>'
                ),
            }
            for relative, text in texts.items():
                (pages / relative).write_text(text)
            gen_llms.refresh_public_roots(pages)
            static_api_catalog.refresh_public_roots(pages)
            timestamps = {}
            for relative, original in texts.items():
                path = pages / relative
                self.assertEqual(site_config.public_reference_text(original), path.read_text())
                timestamps[relative] = path.stat().st_mtime_ns
            self.assertEqual([], gen_llms.refresh_public_roots(pages))
            self.assertFalse(static_api_catalog.refresh_public_roots(pages))
            self.assertEqual(timestamps, {relative: (pages / relative).stat().st_mtime_ns
                                          for relative in texts})


class CanonicalStandardContractTests(contract_tests.ProjectScratchCase):
    def test_legacy_origin_contract_fails_closed_after_the_explicit_unfreeze(self):
        payload = json.loads(self.contract())
        payload["publication"]["url"] = site_config.ORIGIN_SITE
        with self.assertRaisesRegex(sync_standard_site.SyncError, "does not match"):
            sync_standard_site.validate_contract(json.dumps(payload).encode(), self.site)

    def test_public_contract_is_accepted_without_rewriting_remote_records(self):
        payload = self.contract()
        with mock.patch.object(sync_standard_site, "urlopen", side_effect=AssertionError("network forbidden")):
            result = sync_standard_site.validate_contract(payload, self.site)
        self.assertEqual(contract_tests.PUBLICATION_URI, result.publication_at_uri)


if __name__ == "__main__":
    unittest.main()
