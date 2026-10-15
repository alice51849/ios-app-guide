import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app_hook_clips  # noqa: E402

PAGE = """<!doctype html><html><head>
<meta name="description" content="Plan &amp; count days.">
<link rel="canonical" href="{canonical}">
<meta property="og:image" content="https://example.test/social/img/demo-share.jpg">
{robots}</head><body><main>
<h1>Demo</h1>
<!-- app-store-qr:start -->
<section>qr</section>
<!-- app-store-qr:end -->
<h2>What is Demo?</h2>
</main></body></html>
"""


def clip(app, locale, cid, hook="Hook </script> text"):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{cid}.mp4",
            "hook": hook, "name": "Demo App"}


class AppHookClipsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self.tmp.name)
        growth = self.pages / ".github" / "growth"
        growth.mkdir(parents=True)
        (growth / "clips.json").write_text(json.dumps({"clips": {
            "demo/en": clip("demo", "en", "aaa111"),
            "demo/ja": clip("demo", "ja", "bbb222", "日本語のフック"),
            "demo/de": {**clip("demo", "de", "ccc333", "Deutscher Hook"), "duration": 13.0},
            "bad/en": {"app": "bad", "locale": "en", "url": "https://evil.test/x.mp4",
                       "hook": "x", "name": "x"},
        }}), encoding="utf-8")
        site = app_hook_clips.SITE
        for locale, robots in (("en-US", ""), ("ja", ""), ("de-DE", ""),
                               ("fr-FR", '<meta name="robots" content="noindex,follow">')):
            folder = self.pages / locale
            folder.mkdir()
            (folder / "demo.html").write_text(PAGE.format(
                canonical=f"{site}/{locale}/demo.html", robots=robots), encoding="utf-8")
            (folder / "other.html").write_text("<main><h2>x</h2></main>", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_locale_matching(self):
        clips = {"en": {"locale": "en"}, "de": {"locale": "de"}, "zh-Hant": {"locale": "zh-Hant"},
                 "nb": {"locale": "nb"}}
        self.assertEqual(app_hook_clips.clip_for_locale(clips, "de-DE")["locale"], "de")
        self.assertEqual(app_hook_clips.clip_for_locale(clips, "no")["locale"], "nb")
        self.assertEqual(app_hook_clips.clip_for_locale(clips, "zh-Hans")["locale"], "en")
        self.assertEqual(app_hook_clips.clip_for_locale(clips, "en-GB")["locale"], "en")
        self.assertEqual(app_hook_clips.clip_for_locale(clips, "fr-FR")["locale"], "en")

    def test_build_embeds_video_and_sitemap_idempotently(self):
        records = app_hook_clips.build(self.pages, today="2026-10-14")
        self.assertEqual(len(records), 4)
        ja = (self.pages / "ja" / "demo.html").read_text(encoding="utf-8")
        self.assertIn("bbb222.mp4", ja)
        self.assertIn('preload="none"', ja)
        self.assertIn("playsinline muted loop", ja)
        self.assertIn('"@type":"VideoObject"', ja)
        self.assertIn('"duration":"PT7S"', ja)
        self.assertIn('"uploadDate":"2026-10-14T00:00:00+00:00"', ja)
        self.assertLess(ja.index("app-store-qr:end"), ja.index("app-hook-clip:start"))
        self.assertLess(ja.index("app-hook-clip:end"), ja.index("<h2>"))
        fr = (self.pages / "fr-FR" / "demo.html").read_text(encoding="utf-8")
        self.assertIn('lang="en"', fr)
        self.assertNotIn("</script> text", fr.split("application/ld+json")[1].split("</script>")[0])
        self.assertNotIn("app-hook-clip", (self.pages / "ja" / "other.html").read_text(encoding="utf-8"))
        sitemap = (self.pages / app_hook_clips.SITEMAP_NAME).read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("<url>"), 3)  # noindex fr-FR stays out
        self.assertNotIn("fr-FR", sitemap)
        self.assertIn("<video:duration>7</video:duration>", sitemap)
        # An owner-approved longer cut declares its own length (clips.json "duration").
        de = (self.pages / "de-DE" / "demo.html").read_text(encoding="utf-8")
        self.assertIn('"duration":"PT13S"', de)
        self.assertIn("<video:duration>13</video:duration>", sitemap)
        before = {p: p.read_text(encoding="utf-8") for p in self.pages.rglob("*.html")}
        app_hook_clips.build(self.pages, today="2027-01-01")
        after = {p: p.read_text(encoding="utf-8") for p in self.pages.rglob("*.html")}
        self.assertEqual(before, after)  # first-seen date is pinned by the manifest
        self.assertEqual(ja.count("app-hook-clip:start"), 1)

    def test_clip_removed_when_source_drops_it(self):
        app_hook_clips.build(self.pages, today="2026-10-14")
        (self.pages / ".github" / "growth" / "clips.json").write_text('{"clips": {}}', encoding="utf-8")
        app_hook_clips.build(self.pages, today="2026-10-14")
        self.assertNotIn("app-hook-clip", (self.pages / "ja" / "demo.html").read_text(encoding="utf-8"))

    def test_poster_used_when_present(self):
        posters = self.pages / app_hook_clips.POSTER_RELATIVE
        posters.mkdir(parents=True)
        (posters / "bbb222.jpg").write_bytes(b"jpg")
        app_hook_clips.build(self.pages, today="2026-10-14")
        ja = (self.pages / "ja" / "demo.html").read_text(encoding="utf-8")
        self.assertIn("assets/hook-clips/bbb222.jpg", ja)
        en = (self.pages / "en-US" / "demo.html").read_text(encoding="utf-8")
        self.assertIn("social/img/demo-share.jpg", en)


if __name__ == "__main__":
    unittest.main()
