"""gen_app_page_consolidation -> gen_social_previews must not crash.

publish.py marks near-duplicate single-app answers pages (ShotInbox, see
app_page_consolidation_policy.json) ``noindex,follow``.  The next
gen_social_previews pass used to run the guide robots check on them and abort
the whole publish with "conflicting robots rules".  noindex answers pages are
not social-preview targets: they are skipped and left untouched (their robots
meta sits inside the managed preview block, so rewriting or removing the block
would drop the noindex), and gen_image_sitemap leaves them out as well.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aeo_answers  # noqa: E402
import gen_app_page_consolidation  # noqa: E402
import gen_image_sitemap  # noqa: E402
import gen_social_previews  # noqa: E402

SITE = gen_image_sitemap.SITE


def _document(name: str, app_id: str, extra_link: str = "") -> str:
    canonical = f"{SITE}/answers/{name}.html"
    return (
        "<html><head>"
        f"<title>{name}</title>"
        f'<meta name="description" content="{name} guide.">'
        '<meta name="robots" content="index,follow,max-image-preview:large">'
        f'<link rel="canonical" href="{canonical}">'
        '<meta name="twitter:card" content="summary">'
        "<style></style></head><body><main>"
        f'<a href="https://apps.apple.com/us/app/id{app_id}?pt=1&ct=geo_ask&mt=8">App</a>'
        f"{extra_link}"
        "</main></body></html>"
    )


class NoindexAnswerSocialPreviewTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self._tmp.name)
        self.answers = self.pages / "answers"
        self.answers.mkdir()
        image = self.pages / "social" / "img" / "snapport-share.jpg"
        image.parent.mkdir(parents=True)
        Image.new("RGB", gen_image_sitemap.ANSWER_IMAGE_SIZE, (42, 67, 101)).save(
            image, "JPEG"
        )
        self.app_id = str(aeo_answers.APPSTORE["snapport"])
        self.other_id = str(aeo_answers.APPSTORE["scanto"])
        self.keep = self.answers / "best-keep-app.html"
        self.dup = self.answers / "best-dup-app.html"
        self.mixed = self.answers / "best-mixed-app.html"
        self.keep.write_text(_document("best-keep-app", self.app_id), encoding="utf-8")
        self.dup.write_text(_document("best-dup-app", self.app_id), encoding="utf-8")
        self.mixed.write_text(
            _document(
                "best-mixed-app",
                self.app_id,
                f'<a href="https://apps.apple.com/app/id{self.other_id}">Other</a>',
            ),
            encoding="utf-8",
        )
        self.policy = {
            "snapport": {"store_id": self.app_id, "keep": ["best-keep-app"]}
        }
        self.live_keys = {"snapport", "scanto"}
        self.names = {key: aeo_answers.APPS[key]["name"] for key in self.live_keys}

    def tearDown(self):
        self._tmp.cleanup()

    def _reconcile(self):
        return gen_social_previews.reconcile_answer_metadata(
            self.pages, self.live_keys, self.names
        )

    def _consolidate(self):
        with mock.patch.object(
            gen_app_page_consolidation, "prune_sitemaps", return_value=0
        ):
            return gen_app_page_consolidation.run(self.pages, self.policy, apply=True)

    def test_consolidation_noindexes_only_duplicates(self):
        stats = self._consolidate()
        self.assertEqual(stats["apps"]["snapport"]["newly_noindexed"], 1)
        self.assertIn("noindex,follow", self.dup.read_text(encoding="utf-8"))
        self.assertNotIn("noindex", self.keep.read_text(encoding="utf-8"))
        self.assertNotIn("noindex", self.mixed.read_text(encoding="utf-8"))

    def test_social_previews_skip_noindex_answers_after_consolidation(self):
        self.assertEqual(self._reconcile()["answer_metadata_pages"], 2)
        self._consolidate()
        before = self.dup.read_text(encoding="utf-8")
        self.assertIn("noindex,follow", before)
        result = self._reconcile()  # used to raise "conflicting robots rules"
        self.assertEqual(result["answer_metadata_pages"], 1)
        self.assertEqual(self.dup.read_text(encoding="utf-8"), before)
        self.assertIn(
            gen_social_previews.ANSWER_BLOCK_START,
            self.keep.read_text(encoding="utf-8"),
        )
        self.assertEqual(self._reconcile()["changed_files"], 0)

    def test_noindex_answers_leave_image_sitemap(self):
        self._reconcile()
        self._consolidate()
        self._reconcile()
        pages = [
            gen_image_sitemap._answer_entry(path, self.pages, SITE)
            for path in sorted(self.answers.glob("*.html"))
        ]
        urls = {entry[0] for entry in pages if entry is not None}
        self.assertEqual(urls, {f"{SITE}/answers/best-keep-app.html"})

    def test_is_noindex_page(self):
        self._consolidate()
        self.assertTrue(gen_social_previews.is_noindex_page(self.dup))
        self.assertFalse(gen_social_previews.is_noindex_page(self.keep))

    def test_indexable_guide_with_noindex_still_fails_loudly(self):
        self.keep.write_text(
            self.keep.read_text(encoding="utf-8").replace(
                "index,follow,max-image-preview:large", "nosnippet"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "conflicting robots rules"):
            self._reconcile()


if __name__ == "__main__":
    unittest.main()
