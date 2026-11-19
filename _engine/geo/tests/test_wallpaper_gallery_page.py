import html
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parent
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(ROOT / "agent"))

from PIL import Image  # noqa: E402

import android_play  # noqa: E402
try:  # agent/ is not mirrored to the Guide's _engine
    import ct_codes  # noqa: E402
except ImportError:  # pragma: no cover
    ct_codes = None
import gen_store_attribution as attribution  # noqa: E402
import web_hook_pages as hooks  # noqa: E402

PROVIDER = "118326163"
APP_ID = "6824946559"
TOKEN = "os_wpgallery_web"
INDEX = '<html><body><section class="wrap grid"><article class="card third"><h2><a href="x.html">X</a></h2></article></section></body></html>'
PRICE_WORDS_RE = re.compile(
    r"\bfree\b|免費|免费|無料|무료|gratis|grátis|gratuit|kostenlos|\bpro\b|lifetime|\$\s?\d|NT\$|¥|￥|€|\d\s?円|\d\s?元"
    r"|trial|試用|试用|お試し|체험|subscription|訂閱|订阅|サブスク|구독|abonnement|assinatura|Abo\b",
    re.IGNORECASE,
)
GALLERY = hooks.WALLPAPER_GALLERY
STORE = json.loads((ROOT / "data" / "duowallpaperstudio_full.json").read_text(encoding="utf-8"))
STORE_LOCALE = {"en": "en-US", "ja": "ja", "ko": "ko", "zh-Hant": "zh-Hant",
                "de-DE": "de-DE", "fr-FR": "fr-FR", "pt-BR": "pt-BR"}


def visible_text(page: str) -> str:
    body = page.split("<body>", 1)[1]
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


class WallpaperGalleryPageTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get("APP_STORE_PROVIDER_TOKEN")
        os.environ["APP_STORE_PROVIDER_TOKEN"] = PROVIDER
        self.android = android_play.load_snapshot()

    def tearDown(self):
        if self._env is None:
            os.environ.pop("APP_STORE_PROVIDER_TOKEN", None)
        else:
            os.environ["APP_STORE_PROVIDER_TOKEN"] = self._env

    def tree(self, *, originals=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pages = Path(tmp.name)
        for locale in GALLERY["locales"]:
            index = pages / ("" if locale == "en" else locale) / "tools" / "index.html"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(INDEX, encoding="utf-8")
        if originals:
            folder = pages / hooks.GALLERY_ASSET_DIR
            folder.mkdir(parents=True, exist_ok=True)
            for pair in GALLERY["pairs"]:
                Image.new("RGB", (1398, 2034), (40, 80, 120)).save(folder / pair["cover"], "JPEG")
                Image.new("RGB", (2853, 2007), (120, 80, 40)).save(folder / pair["inner"], "JPEG")
        return pages

    def build(self, pages, live=("duowallpaperstudio",), android="snapshot"):
        apps = self.android if android == "snapshot" else android
        return hooks.build(pages, live_keys=set(live), android_apps=apps)

    def page(self, pages, locale):
        return (pages / hooks.page_path(GALLERY["slug"], locale)).read_text(encoding="utf-8")

    def test_seven_locales_with_hreflang_and_index_cards(self):
        pages = self.tree()
        outputs = self.build(pages)
        gallery = [u for u in outputs if GALLERY["slug"] in u]
        self.assertEqual(7, len(gallery))
        self.assertEqual("en", GALLERY["locales"][0])
        for locale in GALLERY["locales"]:
            page = self.page(pages, locale)
            self.assertIn(f'<link rel="canonical" href="{hooks.canonical(GALLERY["slug"], locale)}">', page)
            self.assertIn(f'<html lang="{locale}">', page)
            for code in GALLERY["locales"]:
                self.assertIn(f'hreflang="{code}" href="{hooks.canonical(GALLERY["slug"], code)}"', page)
            index = (pages / ("" if locale == "en" else locale) / "tools" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count(f'href="{GALLERY["slug"]}.html"'))
        self.build(pages)
        index = (pages / "tools" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(1, index.count(f'href="{GALLERY["slug"]}.html"'))

    def test_images_have_keyword_files_alt_and_image_objects(self):
        pages = self.tree()
        self.build(pages)
        for locale in GALLERY["locales"]:
            page = self.page(pages, locale)
            keyword = GALLERY["copy"][locale]["keyword"]
            imgs = re.findall(r'<img src="([^"]+)" alt="([^"]+)" width="(\d+)" height="(\d+)"', page)
            self.assertEqual(14, len(imgs))  # 7 pairs x cover/inner
            for src, alt, width, height in imgs:
                self.assertRegex(src, r"/[a-z-]+-foldable-wallpaper-(cover|inner)-screen\.jpg$")
                self.assertIn(html.escape(keyword, quote=True), alt)
            data = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
            gallery = [d for d in data if d.get("@type") == "ImageGallery"]
            self.assertEqual(1, len(gallery))
            media = gallery[0]["associatedMedia"]
            self.assertEqual(14, len(media))
            for item in media:
                self.assertEqual("ImageObject", item["@type"])
                relative = item["contentUrl"].split(hooks.SITE.rstrip("/") + "/", 1)[1]
                with Image.open(pages / relative) as image:
                    self.assertEqual((item["width"], item["height"]), image.size)
                self.assertTrue(item["creditText"])
            self.assertNotIn('"offers"', page)
            self.assertNotIn("license", page.lower().replace("licensed", ""))

    def test_every_pair_has_app_store_and_play_with_one_app_bound_campaign(self):
        pages = self.tree()
        self.build(pages)
        entry = self.android["duowallpaperstudio"]
        self.assertTrue(attribution.app_bound_campaign(TOKEN, APP_ID))
        if ct_codes is not None:
            self.assertEqual("image_gallery", ct_codes.channel_for_ct(TOKEN))
            self.assertEqual([], ct_codes.ct_problems(TOKEN))
        for locale in GALLERY["locales"]:
            page = self.page(pages, locale)
            links = [html.unescape(u) for u in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)]
            self.assertEqual(8, len(links))  # hero + one per pair (7 pairs)
            for link in links:
                self.assertIn(f"/id{APP_ID}?", link)
                self.assertIn(f"pt={PROVIDER}&ct={TOKEN}&mt=8", link)
                again = attribution.final_store_url(link, "geo_learn", PROVIDER,
                                                    locale=hooks.STAMP_LOCALE[locale], app_id=APP_ID)
                self.assertIn(f"ct={TOKEN}&", again)
            for pair in GALLERY["pairs"]:
                section = page.split(f'id="{pair["id"]}"', 1)[1].split("</section>", 1)[0]
                self.assertIn("apps.apple.com", section)
                self.assertIn(entry["package"], section)
                self.assertIn(f"utm_source%3D{TOKEN}%26utm_campaign%3Dduowallpaperstudio", section)
            self.assertEqual(page, android_play.inject_html(page, self.android))

    def test_no_price_free_pro_trial_words_and_trademark_note(self):
        pages = self.tree()
        self.build(pages)
        for locale in GALLERY["locales"]:
            text = visible_text(self.page(pages, locale))
            self.assertIsNone(PRICE_WORDS_RE.search(text), (locale, PRICE_WORDS_RE.search(text)))
            self.assertIn("Apple Inc.", text)
            # 4 of the 7 pairs are paid in the app: the page must say so (2026-11-19 review).
            self.assertIn(html.escape(GALLERY["copy"][locale]["paid_note"], quote=True), self.page(pages, locale))
        blob = json.dumps(GALLERY, ensure_ascii=False)
        self.assertIsNone(PRICE_WORDS_RE.search(blob), PRICE_WORDS_RE.search(blob))

    def test_claims_restate_the_store_description(self):
        for locale, store_locale in STORE_LOCALE.items():
            description = STORE[store_locale]["description"]
            copy = GALLERY["copy"][locale]
            for fact in ("300", "1398 x 2034", "2853 x 2007"):
                self.assertIn(fact, description, (locale, fact))
            self.assertIn("1398 x 2034", " ".join(copy["answer"]))
            self.assertIn("300", copy["hero_text"])

    def test_fail_closed(self):
        for kwargs, originals in (({"android": {}}, True), ({"live": ()}, True), ({}, False)):
            pages = self.tree(originals=originals)
            outputs = self.build(pages, **kwargs)
            self.assertFalse([u for u in outputs if GALLERY["slug"] in u], kwargs)
            for locale in GALLERY["locales"]:
                self.assertFalse((pages / hooks.page_path(GALLERY["slug"], locale)).exists())
                index = (pages / ("" if locale == "en" else locale) / "tools" / "index.html").read_text(encoding="utf-8")
                self.assertNotIn(GALLERY["slug"], index)

    def test_image_sitemap_entries(self):
        pages = self.tree()
        self.build(pages)
        entries = hooks.image_sitemap_entries(pages, "https://example.test/guide")
        self.assertEqual(7, len(entries))
        for page_url, images in entries:
            self.assertTrue(page_url.endswith(f"/tools/{GALLERY['slug']}.html"))
            self.assertEqual(14, len(images))
            for url in images:
                self.assertTrue(url.startswith(f"https://example.test/guide/{hooks.GALLERY_WEB_DIR}/"))


if __name__ == "__main__":
    unittest.main()
