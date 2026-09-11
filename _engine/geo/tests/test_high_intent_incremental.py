"""Bounded, offline regressions for manifest-only conversion publication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from . import test_high_intent_decision_routes as fixtures


routes = fixtures.routes
GEO = fixtures.GEO


class HighIntentIncrementalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = routes.release_expectations(routes.load_route_source())

    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix=".incremental-test-", dir=GEO / "tests")
        self.addCleanup(scratch.cleanup)
        self.pages = Path(scratch.name)
        self.inventory = fixtures.write_contracted_guide_inventory(
            self.pages, self.release["app_keys"],
        )
        self.unrelated = self.pages / "en-US/untouched.html"
        self.unrelated.parent.mkdir()
        self.unrelated.write_text("<b>Do not index, parse or rewrite this page.</b>")
        self.existing = self.pages / "sitemap-existing.xml"
        self.existing.write_text(self.sitemap(f"{routes.SITE}/en-US/untouched.html"))
        self.index = self.pages / routes.SITEMAP_INDEX_RELATIVE
        self.index.write_text(
            f'<sitemapindex xmlns="{routes.SITEMAP_NAMESPACE}">'
            f"<sitemap><loc>{routes.SITE}/sitemap-existing.xml</loc></sitemap>"
            "</sitemapindex>\n"
        )

    @staticmethod
    def sitemap(url):
        return (
            f'<urlset xmlns="{routes.SITEMAP_NAMESPACE}">'
            f"<url><loc>{url}</loc></url></urlset>\n"
        )

    def materialize(self, changed_paths=()):
        return routes.materialize_incremental(
            self.pages, inventory_path=self.inventory,
            provider_token=fixtures.TEST_PROVIDER_TOKEN, changed_paths=changed_paths,
        )

    def test_exact_outputs_and_idempotent_index_without_a_site_scan(self):
        untouched = self.unrelated.read_bytes(), self.existing.read_bytes()
        with (
            mock.patch.object(fixtures.close_sitemap_graph, "close_graph",
                              side_effect=AssertionError("full closer called")),
            mock.patch("site_tree_index.SiteTreeIndex.scan",
                       side_effect=AssertionError("site inventory scanned")),
            mock.patch.object(Path, "rglob", side_effect=AssertionError("recursive scan")),
        ):
            result = self.materialize(["sitemap-existing.xml", "_engine/geo/publish.py"])
            index = self.index.read_bytes()
            second = self.materialize(["sitemap-existing.xml"])
        self.assertFalse(result["site_scan"])
        self.assertEqual(self.release["managed_output_count"], result["managed_outputs"])
        self.assertEqual(self.release["route_count"], result["canonical_routes"])
        self.assertGreater(result["hreflang_routes"], 0)
        self.assertEqual([], second["updated_fragments"])
        self.assertEqual(index, self.index.read_bytes())
        self.assertEqual(untouched, (self.unrelated.read_bytes(), self.existing.read_bytes()))
        manifest = json.loads((self.pages / routes.MANIFEST_RELATIVE).read_text())
        for output in manifest["expected_outputs"]:
            self.assertEqual(
                output["generated_sha256"],
                hashlib.sha256((self.pages / output["relative_path"]).read_bytes()).hexdigest(),
            )

    def test_changed_and_deleted_sitemap_fragments_preserve_other_entries(self):
        changed = self.pages / "sitemap-changed.xml"
        changed.write_text(self.sitemap(f"{routes.SITE}/en-US/untouched.html"))
        self.index.write_text(self.index.read_text().replace(
            "</sitemapindex>",
            f"<sitemap><loc>{routes.SITE}/sitemap-removed.xml</loc></sitemap></sitemapindex>",
        ))
        self.materialize(["sitemap-changed.xml", "sitemap-removed.xml"])
        index = self.index.read_text()
        self.assertIn("/sitemap-existing.xml", index)
        self.assertIn("/sitemap-changed.xml", index)
        self.assertNotIn("/sitemap-removed.xml", index)
        self.assertIn(f"/{routes.SITEMAP_RELATIVE}", index)

    def test_foreign_fragment_is_rejected_before_managed_mutation(self):
        self.existing.write_text(self.sitemap("https://elsewhere.example/private.html"))
        original = self.index.read_bytes()
        with self.assertRaisesRegex(ValueError, "outside the canonical site"):
            self.materialize(["sitemap-existing.xml"])
        self.assertEqual(original, self.index.read_bytes())
        self.assertFalse((self.pages / routes.MANIFEST_RELATIVE).exists())

    def test_missing_unrelated_sitemap_is_not_silently_pruned(self):
        self.existing.unlink()
        original = self.index.read_bytes()
        with self.assertRaisesRegex(ValueError, "Missing incremental sitemap target"):
            self.materialize()
        self.assertEqual(original, self.index.read_bytes())
        self.assertFalse((self.pages / routes.MANIFEST_RELATIVE).exists())

    def test_missing_index_cannot_replace_the_unrelated_site_inventory(self):
        self.index.unlink()
        with self.assertRaisesRegex(ValueError, "existing sitemap index"):
            self.materialize()
        self.assertFalse(self.index.exists())
        self.assertFalse((self.pages / routes.MANIFEST_RELATIVE).exists())

    def test_unsafe_paths_and_symlinks_fail_closed(self):
        for invalid in ("../sitemap.xml", "/sitemap.xml"):
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                self.materialize([invalid])
        link = self.pages / "sitemap-link.xml"
        link.symlink_to(self.existing)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.materialize(["sitemap-link.xml"])
        self.assertFalse((self.pages / routes.MANIFEST_RELATIVE).exists())

    def test_renderer_canonical_and_hreflang_drift_are_rejected_before_writes(self):
        original = routes.render_html
        for field in ("canonical", "hreflang"):
            def drift(record):
                text = original(record)
                if field == "canonical":
                    return text.replace('rel="canonical" href="', 'rel="canonical" href="bad')
                return text.replace('hreflang="en-US"', 'hreflang="invalid-locale"')

            with self.subTest(field=field), mock.patch.object(routes, "render_html", drift):
                with self.assertRaisesRegex(ValueError, "canonical/hreflang drift"):
                    self.materialize()
            self.assertFalse((self.pages / routes.MANIFEST_RELATIVE).exists())

    def test_changed_index_canonical_and_hreflang_are_verified(self):
        index = self.pages / "en-US/index.html"
        index.write_text(
            f'<link rel="canonical" href="{routes.SITE}/en-US/">'
            f'<link rel="alternate" hreflang="en-US" href="{routes.SITE}/en-US/">'
        )
        result = self.materialize(["en-US/index.html"])
        self.assertEqual(1, result["index_fragments"])
        index.write_text(index.read_text().replace('hreflang="en-US"', 'hreflang="bad-locale"'))
        with self.assertRaisesRegex(ValueError, "index hreflang drift"):
            self.materialize(["en-US/index.html"])

    def test_base_english_index_uses_the_existing_indexation_locale_contract(self):
        index = self.pages / "api/index.html"
        index.parent.mkdir()
        index.write_text(
            f'<link rel="canonical" href="{routes.SITE}/api/">'
            f'<link rel="alternate" hreflang="en" href="{routes.SITE}/api/">'
        )
        self.assertEqual(1, self.materialize(["api/index.html"])["index_fragments"])
        index.write_text(index.read_text().replace('hreflang="en"', 'hreflang="en-ZW"'))
        with self.assertRaisesRegex(ValueError, "index hreflang drift"):
            self.materialize(["api/index.html"])

    def test_incremental_prepare_preserves_the_source_bound_release_chain(self):
        source = self.pages / "current-source"
        for relative in (*routes.SYNC_ENGINE_FILES,
                         Path("data/high_intent_guide_sync_contract.json")):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(GEO / relative, target)
        with mock.patch.object(
            fixtures.close_sitemap_graph, "close_graph",
            side_effect=AssertionError("full closer called"),
        ):
            result = routes.prepare_pages_deployment(
                self.pages, inventory_path=self.inventory, source_path=routes.SOURCE_PATH,
                provider_token=fixtures.TEST_PROVIDER_TOKEN, source_commit="1" * 40,
                current_source_root=source, engine_source_revision="2" * 40,
                incremental=True, changed_paths=["sitemap-existing.xml"],
            )
        self.assertEqual(self.release["managed_output_count"], result["managed_outputs"])
        deployment = json.loads((self.pages / routes.DEPLOYMENT_RELATIVE).read_text())
        self.assertEqual("1" * 40, deployment["source_commit"])
        self.assertEqual("2" * 40, deployment["engine_source_revision"])
        self.assertEqual(result["manifest_digest"], deployment["route_manifest_digest"])


if __name__ == "__main__":
    unittest.main()
