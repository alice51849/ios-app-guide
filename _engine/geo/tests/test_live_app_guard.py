#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import live_app_guard


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

            result = live_app_guard.quarantine_nonlive_pages(site, apply=True)

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


if __name__ == "__main__":
    unittest.main()
