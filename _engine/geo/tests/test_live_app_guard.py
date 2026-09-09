#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import live_app_guard
from live_app_manifest import canonical_manifest


class LiveAppGuardTests(unittest.TestCase):
    def test_nonlive_pages_lose_indexing_install_schema_and_dead_cta(self):
        with tempfile.TemporaryDirectory() as root:
            site = Path(root)
            (site / "apps.json").write_text(
                json.dumps([
                    {
                        "name": "Live",
                        "appStoreUrl": "https://apps.apple.com/app/id1234567890",
                    }
                ]),
                encoding="utf-8",
            )
            dead = site / "apps" / "dead"
            live = site / "apps" / "live"
            dead.mkdir(parents=True)
            live.mkdir(parents=True)
            dead_page = (
                '<html><head><meta name="robots" content="index,follow">'
                '<meta name="apple-itunes-app" content="app-id=9999999999">'
                '<script type="application/ld+json">'
                '{"@type":"SoftwareApplication","downloadUrl":'
                '"https://apps.apple.com/app/id9999999999"}</script></head>'
                '<body><a href="https://apps.apple.com/app/id9999999999">'
                "Get</a></body></html>"
            )
            live_page = (
                '<html><head><meta name="robots" content="index,follow"></head>'
                '<body><a href="https://apps.apple.com/app/id1234567890">'
                "Get</a></body></html>"
            )
            (dead / "index.html").write_text(dead_page, encoding="utf-8")
            (live / "index.html").write_text(live_page, encoding="utf-8")
            sitemap = site / "sitemap_apps.xml"
            sitemap.write_text(
                '<?xml version="1.0"?><urlset>'
                "<url><loc>https://example.com/apps/dead/</loc></url>"
                "<url><loc>https://example.com/apps/live/</loc></url>"
                "</urlset>",
                encoding="utf-8",
            )

            result = live_app_guard.quarantine_nonlive_pages(
                site, apply=True, live_ids={"1234567890"},
            )

            sanitized = (dead / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, result["apps"])
            self.assertIn("noindex,nofollow", sanitized)
            self.assertNotIn("apple-itunes-app", sanitized)
            self.assertNotIn("SoftwareApplication", sanitized)
            self.assertNotIn("apps.apple.com", sanitized)
            self.assertEqual(
                live_page,
                (live / "index.html").read_text(encoding="utf-8"),
            )
            sitemap_content = sitemap.read_text(encoding="utf-8")
            self.assertNotIn("/apps/dead/", sitemap_content)
            self.assertIn("/apps/live/", sitemap_content)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=GEO)
        self.addCleanup(self.directory.cleanup)
        self.site = Path(self.directory.name)
        self.live = {app["app_id"] for app in canonical_manifest()["apps"].values()}
        self.live_id = next(iter(sorted(self.live)))
        self.dead_id = "6787344033"

    def page(self, path, body, head=""):
        target = self.site / path
        target.parent.mkdir(parents=True, exist_ok=True)
        source = f"<html><head>{head}</head><body>{body}</body></html>"
        target.write_text(source, encoding="utf-8")
        return target

    def link(self, app_id):
        return f'<a href="https://apps.apple.com/app/id{app_id}">Get</a>'

    def test_manifest_not_generated_catalogue_or_partial_legacy_state_is_authority(self):
        (self.site / "apps.json").write_text(json.dumps([
            {"appStoreUrl": f"https://apps.apple.com/app/id{self.dead_id}"}
        ]))
        (self.site / ".appstore_live_state.json").write_text(json.dumps({
            "live_ids": [self.dead_id], "miss_counts": {},
        }))
        live_pages = {
            self.page(f"guides/{key}.html", self.link(app["app_id"]))
            for key, app in canonical_manifest()["apps"].items()
        }
        before = {path: path.read_bytes() for path in live_pages}
        dead = self.page("abr/reviews/zafe.html", self.link(self.dead_id))
        roster_before = canonical_manifest()
        # A missing/unknown availability observation retains versioned identity;
        # it must not turn the 47-app roster into an older generated subset.
        with mock.patch.dict(os.environ, {
            "GROWTH_LIVE_MANIFEST": str(self.site / "missing-runtime-manifest.json"),
        }):
            self.assertEqual(self.live, set(live_app_guard.live_apps().values()))
            live_app_guard.quarantine_nonlive_pages(self.site, apply=True)
        self.assertNotIn(self.dead_id, dead.read_text())
        self.assertIn("noindex,nofollow", dead.read_text())
        self.assertEqual(before, {path: path.read_bytes() for path in live_pages})
        self.assertEqual(roster_before, canonical_manifest())
        self.assertNotIn(self.dead_id, self.live)
        self.assertGreaterEqual(len(self.live), 47)

    def test_mixed_pages_keep_live_links_and_schema_items(self):
        for family in ("best-for", "seasonal", "persona", "workflow", "vs", "tutorials"):
            with self.subTest(family=family):
                items = [
                    {"@type": "ListItem", "position": index, "name": name,
                     "url": f"https://apps.apple.com/app/id{app_id}", "offers": None}
                    for index, (name, app_id) in enumerate(
                        (("Zafe", self.dead_id), ("Live", self.live_id)), 1
                    )
                ]
                schema = [{"@type": "ItemList", "numberOfItems": 2, "itemListElement": items},
                          {"@type": "FAQPage", "mainEntity": []}]
                path = self.page(
                    f"aa/{family}/mixed.html",
                    self.link(self.dead_id) + self.link(self.live_id),
                    '<meta name="robots" content="index,follow">'
                    f'<script type="application/ld+json">{json.dumps(schema)}</script>',
                )
                live_app_guard.quarantine_nonlive_pages(
                    self.site, apply=True, live_ids=self.live,
                )
                updated = path.read_text()
                self.assertNotIn(self.dead_id, updated)
                self.assertIn(self.link(self.live_id), updated)
                self.assertIn('content="index,follow"', updated)
                self.assertNotIn(live_app_guard.QUARANTINE_META, updated)
                block = live_app_guard.JSON_LD_RE.search(updated).group()
                data = json.loads(block[block.index(">") + 1:block.rfind("</")])
                self.assertEqual(1, data[0]["numberOfItems"])
                self.assertEqual([{**items[1], "position": 1}], data[0]["itemListElement"])
                self.assertEqual(schema[1], data[1])

    def test_primary_nonlive_app_is_quarantined_even_with_live_recommendations(self):
        dead = self.page(
            "apps/dead/index.html", self.link(self.dead_id) + self.link(self.live_id),
            f'<meta content="app-id={self.dead_id}" name="apple-itunes-app">',
        )
        child = self.page("apps/dead/help.html", "Archived help.")
        live = self.page(
            "apps/live/index.html", self.link(self.live_id) + self.link(self.dead_id),
            f'<meta name="apple-itunes-app" content="app-id={self.live_id}">',
        )
        live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        for path in (dead, child):
            self.assertIn("noindex,nofollow", path.read_text())
            self.assertNotIn("apps.apple.com", path.read_text())
        self.assertIn(self.link(self.live_id), live.read_text())
        self.assertNotIn(self.dead_id, live.read_text())
        self.assertNotIn("noindex", live.read_text())

    def test_all_single_app_families_are_quarantined_and_sitemaps_stay_pruned(self):
        dead = self.page("en/reviews/zafe.html", self.link(self.dead_id))
        live = self.page("en/reviews/live.html", self.link(self.live_id))
        source = (
            '<urlset xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            '<url><loc>https://example.com/site/en/reviews/zafe.html</loc></url>'
            '<url><loc>https://example.com/site/en/reviews/live.html</loc>'
            '<xhtml:link rel="alternate" hreflang="en" '
            'href="https://example.com/site/en/reviews/zafe.html"/></url></urlset>'
        )
        sitemap = self.site / "sitemap_reviews.xml"
        sitemap.write_text(source)
        before = {path: path.read_bytes() for path in (dead, live, sitemap)}
        check = live_app_guard.quarantine_nonlive_pages(self.site, apply=False, live_ids=self.live)
        self.assertEqual(1, check["html"])
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        first = live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual(1, first["quarantined_pages"])
        self.assertNotIn("/zafe.html", sitemap.read_text())
        self.assertIn("/live.html", sitemap.read_text())
        second = live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual((0, 0), (second["html"], second["sitemaps"]))
        sitemap.write_text(source)
        repaired = live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual((0, 1), (repaired["html"], repaired["sitemaps"]))
        self.assertNotIn("/zafe.html", sitemap.read_text())

    def test_excludes_sources_and_symlinks_and_fails_before_partial_writes(self):
        source = self.page("_engine/fixture.html", self.link(self.dead_id))
        linked = self.site / "linked.html"
        linked.symlink_to(source)
        good = self.page("a.html", self.link(self.dead_id))
        bad = self.page(
            "z.html", self.link(self.dead_id),
            '<script type="application/ld+json">{"id":"'
            + self.dead_id + '",BROKEN}</script>',
        )
        before = {path: path.read_bytes() for path in (source, good, bad)}
        with self.assertRaisesRegex(RuntimeError, "z.html"):
            live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        with self.assertRaisesRegex(RuntimeError, "empty verified"):
            live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=set())
        bad.unlink()
        live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual(before[source], source.read_bytes())
        self.assertNotIn(self.dead_id, good.read_text())

    def test_cleanup_does_not_delete_a_live_answer_with_repeated_stale_recommendations(self):
        import cleanup_localized_assets as cleanup

        page = self.page(
            "answers/mixed.html",
            self.link(self.live_id) + self.link(self.dead_id) * 2,
        )
        self.assertFalse(cleanup.owns_unlisted_app(page, {self.dead_id}, {"Zafe"}))
        result = cleanup.cleanup(self.site, set(canonical_manifest()["apps"]))
        self.assertGreater(result["nonlive_html"], 0)
        self.assertTrue(page.is_file())
        self.assertIn(self.link(self.live_id), page.read_text())
        self.assertNotIn(self.dead_id, page.read_text())

    def test_developer_identity_is_not_an_unlisted_app(self):
        page = self.page(
            "publisher.html",
            '<a href="https://apps.apple.com/developer/id123456789">Publisher</a>',
        )
        before = page.read_bytes()
        result = live_app_guard.quarantine_nonlive_pages(
            self.site, apply=True, live_ids=self.live,
        )
        self.assertEqual(0, result["html"])
        self.assertEqual(before, page.read_bytes())

    def test_encoded_localized_sitemap_paths_are_pruned_without_whitespace_debris(self):
        from urllib.parse import quote

        relative = "zh-Hant/reviews/隱私.html"
        self.page(relative, self.link(self.dead_id))
        self.page(".well-known/archived.html", self.link(self.dead_id))
        sitemap = self.site / "sitemap_reviews.xml"
        sitemap.write_text(
            "<urlset>\n  <url><loc>https://example.com/"
            + quote(relative) + "</loc></url>\n</urlset>\n"
        )
        live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertEqual("<urlset>\n\n</urlset>\n", sitemap.read_text())
        self.assertNotIn(self.dead_id, (self.site / ".well-known/archived.html").read_text())

    def test_url_identity_cache_never_caches_live_eligibility(self):
        live_app_guard._url_app_id.cache_clear()
        for campaign in ("one", "two"):
            source = f'https://apps.apple.com/app/id{self.live_id}?ct={campaign}'
            self.assertEqual({self.live_id}, live_app_guard._store_ids(source))
        self.assertEqual(1, live_app_guard._url_app_id.cache_info().misses)
        page = self.page("live.html", self.link(self.live_id))
        self.assertEqual(page.read_text(), live_app_guard.sanitize_nonlive_html(page.read_text(), self.live))
        archived = live_app_guard.sanitize_nonlive_html(page.read_text(), self.live - {self.live_id})
        self.assertIn("noindex,nofollow", archived)
        self.assertNotIn(self.live_id, archived)

    def test_missing_output_tree_is_not_a_successful_guard(self):
        with self.assertRaisesRegex(RuntimeError, "Missing generated pages directory"):
            live_app_guard.quarantine_nonlive_pages(
                self.site / "missing", apply=True, live_ids=self.live,
            )

    def test_root_quarantine_does_not_prune_a_live_localized_page_with_the_same_slug(self):
        self.page("reviews/choice.html", self.link(self.dead_id))
        self.page("en/reviews/choice.html", self.link(self.live_id))
        sitemap = self.site / "sitemap_reviews.xml"
        sitemap.write_text(
            '<urlset><url><loc>https://example.com/site/reviews/choice.html</loc></url>'
            '<url><loc>https://example.com/site/en/reviews/choice.html</loc></url></urlset>'
        )
        live_app_guard.quarantine_nonlive_pages(self.site, apply=True, live_ids=self.live)
        self.assertNotIn("/site/reviews/choice.html", sitemap.read_text())
        self.assertIn("/site/en/reviews/choice.html", sitemap.read_text())


class LiveAppPublicationOrderTests(unittest.TestCase):
    def test_catchup_publish_and_rebase_quarantine_before_final_tree_seal(self):
        import app_store_storefronts
        import publish

        for phase in ("main", "rebase"):
            with self.subTest(phase=phase):
                commands = []
                with (
                    mock.patch.object(publish, "require", side_effect=lambda command, **_: commands.append(command) or ""),
                    mock.patch.object(publish, "run", return_value=(0, "")),
                    mock.patch.object(publish, "sync_standard_site"),
                    mock.patch.object(app_store_storefronts, "resolve_provider_token", return_value="123456789"),
                    mock.patch.object(sys, "argv", ["publish.py", "--no-push"]),
                    mock.patch("builtins.print"),
                ):
                    if phase == "main":
                        publish.main()
                    else:
                        publish.reconcile_lastmod_after_rebase({})
                names = [Path(command[1]).name for command in commands]
                guard = names.index("live_app_guard.py")
                self.assertLess(guard, names.index("close_sitemap_graph.py"))
                self.assertLess(guard, names.index("gen_store_attribution.py"))
                self.assertLess(guard, names.index("gen_sitemap_lastmod.py"))
                self.assertLess(guard, names.index("audit_store_attribution.py"))
                if phase == "main":
                    self.assertLess(names.index("cleanup_localized_assets.py"), guard)
                    self.assertLess(names.index("dedupe_locale_meta.py"), guard)

    def test_daily_geo_reconciles_nonlive_pages_after_dedupe_and_before_closure(self):
        candidates = [Path(os.environ.get("GEO_GUIDE_ROOT", GEO / "pages")), GEO.parents[1]]
        path = next((
            root / ".github/workflows/geo-daily.yml" for root in candidates
            if (root / ".github/workflows/geo-daily.yml").is_file()
        ), None)
        if path is None:
            self.skipTest("materialized Guide workflow is unavailable")
        source = path.read_text()
        blocks = [
            source.split("Final link and availability cleanup", 1)[1].split("Seal complete", 1)[0],
            *(
                source.split(f"{phase}() {{", 1)[1].split("remote_first_publish", 1)[0]
                for phase in ("reconcile_english_phase", "reconcile_localized_phase")
            ),
        ]
        for block in blocks:
            guard = block.index("python3 live_app_guard.py --site-root pages")
            self.assertLess(block.index("python3 dedupe_locale_meta.py"), guard)
            self.assertLess(guard, block.index("python3 close_sitemap_graph.py"))
            self.assertLess(guard, block.index("python3 gen_store_attribution.py", guard))


if __name__ == "__main__":
    unittest.main()
