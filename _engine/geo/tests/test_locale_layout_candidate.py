"""The release composer must retain reviewed source and stamp every store CTA."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import build_pages_i18n as pages
import locale_layout_candidate as candidate
import publisher_intent_catalog as publisher


class LocaleLayoutCandidateTests(unittest.TestCase):
    def test_preferred_app_page_keeps_new_copy_instead_of_old_persona_answer(self):
        key = "aibriefpack"
        app_id = str(pages.APPSTORE[key])
        app = {"app_store_id": app_id, "purchase_model": "free_with_lifetime_unlock", "one_time_option": True}
        slug = publisher.slugify(publisher.PERSONAS[key][0]["query"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "en-US/answers").mkdir(parents=True)
            def source(relative, heading):
                return (
                    '<html lang="en-US"><head>'
                    f'<title>{heading}</title><meta name="description" content="Reviewed useful product information for this exact app.">'
                    f'<link rel="canonical" href="{pages.SITE}/{relative}">'
                    '<script type="application/ld+json">'
                    + json.dumps({"@type": "MobileApplication", "name": "AI Brief",
                                  "url": f"https://apps.apple.com/app/id{app_id}",
                                  "description": "Reviewed useful product information for this exact app."})
                    + '</script></head><body><h1>' + heading + '</h1>'
                    f'<p><a href="https://apps.apple.com/app/id{app_id}">View AI Brief on the App Store</a></p>'
                    '<footer class="footer"><div class="wrap">First-party publisher guide.</div></footer></body></html>'
                )
            (root / "en-US/aibriefpack.html").write_text(source("en-US/aibriefpack.html", "New reviewed app copy"))
            (root / "en-US/answers" / f"{slug}.html").write_text(source(f"en-US/answers/{slug}.html", "Existing persona answer"))
            before = {path: path.read_bytes() for path in root.rglob("*.html")}
            with mock.patch.object(publisher, "_decision_context", return_value="Reviewed useful product information."):
                ordinary = publisher._page_record(root, "en-US", key, app, {}, "First-party publisher guide.")
                reviewed = publisher._page_record(root, "en-US", key, app, {}, "First-party publisher guide.", prefer_app_page=True)
            self.assertIn("/answers/", ordinary["canonical_guide_url"])
            self.assertEqual(f"{pages.SITE}/en-US/aibriefpack.html", reviewed["canonical_guide_url"])
            self.assertEqual("New reviewed app copy", reviewed["publisher_query"])
            self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_stamp_includes_the_facts_anchor_without_changing_visible_copy(self):
        key = "aibriefpack"
        app_id = str(pages.APPSTORE[key])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "en-US" / f"{key}.html"
            path.parent.mkdir()
            original = (
                '<html lang="en-US"><head></head><body><main>'
                f'<p><a href="https://apps.apple.com/app/id{app_id}">Native CTA</a></p>'
                f'<aside><a class="iag-store-facts__link" href="https://apps.apple.com/us/app/id{app_id}">App Store · Free</a></aside>'
                '</main></body></html>'
            )
            path.write_text(original)
            with mock.patch.object(candidate.storefronts, "resolve_provider_token", return_value="118326163"):
                candidate._stamp(path, root, "en-US", {"us": frozenset({app_id})})
            rendered = path.read_text()
            self.assertIn("Native CTA", rendered)
            self.assertIn("App Store · Free", rendered)
            import re, html
            urls = re.findall(r'href="([^"]+)"', rendered)
            self.assertEqual(2, len(urls))
            for url in urls:
                params = parse_qs(urlsplit(html.unescape(url)).query)
                self.assertEqual(["118326163"], params["pt"])
                self.assertTrue(params["ct"])

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                candidate.generate(root, root, root / "unread.json")

    def test_raw_truth_must_have_the_complete_field_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            truth = root / "truth.json"
            truth.write_text("[]")
            with self.assertRaises(ValueError):
                candidate.generate(root, root / "candidate", truth)


if __name__ == "__main__":
    unittest.main()
