import json
import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import k9_first_screen as K9  # noqa: E402

PAGE = """<html lang="en"><head>
<meta name="apple-itunes-app" content="app-id=1, affiliate-data=pt=118326163&amp;ct=geo_ask&amp;mt=8">
</head><body><h1 class="p-name entry-title">best cv maker app</h1>
<p class="lead">Old lead.</p>
<a href="https://apps.apple.com/gb/app/id1?pt=118326163&amp;ct=geo_ask&amp;mt=8">Get</a>
<a href="https://apps.apple.com/gb/app/id1?action=write-review">Review</a>
<a href="https://play.google.com/store/apps/details?id=com.x.y&amp;referrer=utm_source%3Dgeo_ask%26utm_campaign%3Dcvdesk">Play</a>
<a href="https://play.google.com/store/apps/details?id=com.x.y&amp;showAllReviews=true">Reviews</a>
</body></html>"""

SPEC = {"batch_ct": K9.BATCH_CT, "pages": {"en-GB/answers/best-cv-maker-app.html": {"replace": [
    {"old": '<h1 class="p-name entry-title">best cv maker app</h1>',
     "new": '<h1 class="p-name entry-title">Best CV Maker App for iPhone</h1>'},
    {"old": "Old lead.</p>", "new": "Old lead. Appended.</p>"},
    {"old": "not on the page", "new": "Nowhere Else"}]}}}


class K9FirstScreenTest(unittest.TestCase):
    def test_batch_ct_and_text(self):
        out, stats = K9.apply_html(PAGE, SPEC["pages"]["en-GB/answers/best-cv-maker-app.html"])
        self.assertIn("Best CV Maker App for iPhone</h1>", out)
        self.assertIn("Old lead. Appended.</p>", out)
        self.assertNotIn("geo_ask", out)
        self.assertEqual(3, out.count("k9top50_1121"))  # banner, App Store link, Play referrer
        self.assertIn("id1?action=write-review", out)  # review links untouched
        self.assertIn("showAllReviews=true", out)
        self.assertIn("utm_campaign%3Dcvdesk", out)
        self.assertEqual((2, 1), (stats["text_applied"], stats["text_missing"]))

    def test_idempotent_and_contained_replacement(self):
        page = SPEC["pages"]["en-GB/answers/best-cv-maker-app.html"]
        once, _ = K9.apply_html(PAGE, page)
        twice, stats = K9.apply_html(once, page)
        self.assertEqual(once, twice)
        self.assertEqual(0, stats["text_applied"])
        shorter = {"replace": [{"old": "App Store สหรัฐฯ", "new": "App Store", "all": True}]}
        out, _ = K9.apply_html("a App Store สหรัฐฯ b App Store สหรัฐฯ", shorter)
        self.assertEqual("a App Store b App Store", out)

    def test_tree_skips_pinned_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "en-GB/answers/best-cv-maker-app.html"
            page.parent.mkdir(parents=True)
            page.write_text(PAGE, encoding="utf-8")
            pinned = root / "apps/x/decision/l/cs/index.html"
            pinned.parent.mkdir(parents=True)
            pinned.write_text(PAGE, encoding="utf-8")
            (root / "data/hero-tasks").mkdir(parents=True)
            (root / "data/hero-tasks/manifest.json").write_text(
                json.dumps({"outputs": {"apps/x/decision/l/cs/index.html": "sha"}}), encoding="utf-8")
            spec = {"pages": dict(SPEC["pages"], **{"apps/x/decision/l/cs/index.html": {}, "gone.html": {}})}
            stats = K9.apply_tree(root, spec)
            self.assertEqual((3, 1, 1, 1), (stats["listed"], stats["changed"], stats["pinned"], stats["missing_page"]))
            self.assertEqual(PAGE, pinned.read_text(encoding="utf-8"))

    def test_shipped_spec_is_well_formed(self):
        spec = K9.load_spec()
        self.assertEqual(K9.BATCH_CT, spec["batch_ct"])
        self.assertLessEqual(len(spec["pages"]), 50)
        for relative, page in spec["pages"].items():
            self.assertTrue(relative.endswith(".html") and not relative.startswith("/"), relative)
            for row in page["replace"]:
                self.assertTrue(row["old"] and row["new"] and row["old"] != row["new"], relative)
                self.assertNotRegex(row["new"], r"(?i)free trial|\$\d|€\d", relative)


if __name__ == "__main__":
    unittest.main()
