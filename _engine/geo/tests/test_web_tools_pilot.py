import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import android_play  # noqa: E402
import click_beacon  # noqa: E402
import gen_store_attribution as attribution  # noqa: E402
import web_tools_pilot as pilot  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PROVIDER = "118326163"
INDEX = '<html><body><section class="wrap grid"><article class="card third"><h2><a href="x.html">X</a></h2></article></section></body></html>'
NETWORK_RE = re.compile(r"\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|<form\b|\.submit\(")
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")
CSP_RE = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')
PRICE_WORDS_RE = re.compile(r"\bfree\b|免費|無料|\bpro\b|\$\s?\d|NT\$|¥|\d\s?円", re.IGNORECASE)


def without_counter(page: str) -> str:
    """The page minus the one shared download-click counter block."""
    block = click_beacon.click_beacon_block()
    assert page.count(block) == 1
    return page.replace(block, "")


def csp(page: str) -> dict:
    found = CSP_RE.findall(page)
    assert len(found) == 1
    out = {}
    for part in html.unescape(found[0]).split(";"):
        words = part.split()
        if words:
            out[words[0]] = words[1:]
    return out


def visible_text(page: str) -> str:
    body = page.split("<body>", 1)[1]
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


class WebToolsPilotTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get("APP_STORE_PROVIDER_TOKEN")
        os.environ["APP_STORE_PROVIDER_TOKEN"] = PROVIDER

    def tearDown(self):
        if self._env is None:
            os.environ.pop("APP_STORE_PROVIDER_TOKEN", None)
        else:
            os.environ["APP_STORE_PROVIDER_TOKEN"] = self._env

    def build(self, live=("duowallpaperstudio", "snapport"), android=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pages = Path(tmp.name)
        for locale in pilot.LOCALES:
            index = pages / ("" if locale == "en" else locale) / "tools" / "index.html"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(INDEX, encoding="utf-8")
        outputs = pilot.build(pages, live_keys=set(live), android_apps=android)
        return pages, outputs

    def pages(self, root):
        for tool in pilot.TOOLS:
            for locale in pilot.LOCALES:
                yield tool, locale, (root / pilot.page_path(tool["slug"], locale)).read_text(encoding="utf-8")

    def test_two_tools_three_locales_indexable_under_public_site(self):
        root, outputs = self.build()
        self.assertEqual(6, len(outputs))
        self.assertEqual(("en", "zh-Hant", "ja"), pilot.LOCALES)
        for tool, locale, page in self.pages(root):
            url = pilot.canonical(tool["slug"], locale)
            self.assertTrue(url.startswith(PUBLIC_SITE.rstrip("/") + "/"))
            self.assertIn(f'<link rel="canonical" href="{url}">', page)
            self.assertIn('<meta name="robots" content="index,follow">', page)
            self.assertNotIn("noindex", page)
            self.assertIn(f'<html lang="{locale}">', page)
            for code in pilot.LOCALES:
                self.assertIn(
                    f'hreflang="{code}" href="{pilot.canonical(tool["slug"], code)}"', page
                )
            self.assertIn('hreflang="x-default"', page)

    def test_pages_never_send_images_anywhere(self):
        """No network call anywhere except the shared download-click counter."""
        root, _ = self.build()
        for _tool, _locale, page in self.pages(root):
            tool_page = without_counter(page)
            scripts = "".join(re.findall(r"<script>(.*?)</script>", tool_page, flags=re.S))
            self.assertTrue(scripts)
            self.assertIsNone(NETWORK_RE.search(tool_page))
            self.assertIn("createObjectURL", scripts)
            # The counter block is the only network code on the page.
            block = click_beacon.click_beacon_block()
            self.assertEqual(len(NETWORK_RE.findall(block)), len(NETWORK_RE.findall(page)))
            self.assertIn("sendBeacon", click_beacon.click_beacon_block())

    def test_csp_allows_only_the_counter_endpoint(self):
        root, _ = self.build(android=android_play.load_snapshot())
        for _tool, _locale, page in self.pages(root):
            policy = csp(page)
            self.assertEqual(["'none'"], policy["default-src"])
            self.assertEqual([click_beacon.CLICK_BEACON_URL], policy["connect-src"])
            self.assertEqual(["'none'"], policy["form-action"])
            for directive in ("img-src", "style-src", "script-src"):
                for source in policy[directive]:
                    self.assertFalse(source.startswith("http"), (directive, source))
            # Exactly the page's own inline scripts run, the counter included.
            bodies = re.findall(r"<script>(.*?)</script>", page, flags=re.S)
            hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'"
                      for b in bodies]
            self.assertEqual(sorted(hashes), sorted(policy["script-src"]))
            self.assertIn(click_beacon.click_beacon_script_hash(), policy["script-src"])
            self.assertTrue(click_beacon.csp_allows_beacon(page))
            # The deploy-time pass keeps the counter on these pages unchanged.
            self.assertEqual((page, click_beacon.UNCHANGED), click_beacon.inject_html(page))
            # Every URL in executable code is the counter endpoint.
            code = "".join(bodies)
            endpoints = {u for u in URL_RE.findall(code) if "apps.apple.com" not in u}
            self.assertEqual({click_beacon.CLICK_BEACON_URL}, endpoints)

    def test_counter_sends_only_page_app_ct_store_never_file_data(self):
        block = click_beacon.click_beacon_block()
        js = block.split("<script>", 1)[1].split("</script>", 1)[0]
        for banned in ("FileReader", "files", "toBlob", "toDataURL", "getImageData",
                       "canvas", "document.cookie", "localStorage", "blob:"):
            self.assertNotIn(banned, js, banned)
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        link = "https://apps.apple.com/us/app/id6780575828?pt=1&ct=tool_passport_crop_en&mt=8"
        harness = (
            "const sent=[];let h;"
            "globalThis.location=new URL('https://guide.example/tools/passport-photo-crop.html');"
            "Object.defineProperty(globalThis,'navigator',{configurable:true,"
            "value:{sendBeacon:(u,b)=>{sent.push([u,b]);return true}}});"
            "globalThis.document={addEventListener:(t,f)=>{if(t==='click')h=f}};"
            + js +
            "h({target:{closest:()=>({href:" + json.dumps(link) + "})}});"
            "h({target:{closest:()=>({href:'https://example.com/x'})}});"
            "h({target:{closest:()=>null}});"
            "process.stdout.write(JSON.stringify(sent));"
        )
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
        sent = json.loads(out.stdout)
        self.assertEqual(1, len(sent))
        url, body = sent[0]
        self.assertEqual(click_beacon.CLICK_BEACON_URL, url)
        payload = json.loads(body)
        self.assertEqual({"p", "a", "ct", "s"}, set(payload))
        self.assertEqual({"p": "/tools/passport-photo-crop.html", "a": "6780575828",
                          "ct": "tool_passport_crop_en", "s": "apple"}, payload)

    def test_privacy_badge_says_only_clicks_are_counted(self):
        root, _ = self.build()
        wanted = {"en": "only download-button clicks are counted",
                  "zh-Hant": "只計算下載鈕點擊次數",
                  "ja": "ダウンロードボタンのクリック数だけを数えます"}
        for tool, locale, page in self.pages(root):
            badge = tool["copy"][locale]["privacy"]
            self.assertIn(wanted[locale], badge)
            self.assertIn(html.escape(badge, quote=True), page)

    def test_answer_engine_elements(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            t = tool["copy"][locale]
            self.assertEqual(2, len(t["answer"]))
            self.assertIn(f'<p class="lead">{html.escape(" ".join(t["answer"]), quote=True)}</p>', page)
            self.assertIn('id="sizes"', page)
            self.assertNotIn("試用", page)
            self.assertNotIn("trial", page.lower())
            self.assertNotIn("dual screen wallpaper", page.lower())
            self.assertNotIn("samsung", page.lower())
            self.assertNotIn("三星", page)
            if tool is pilot.DUO:
                self.assertTrue(t["title"].startswith(("Cover Screen Wallpaper", "外螢幕桌布", "外画面")))
                for w, h in pilot.DUO_SCREENS.values():
                    self.assertIn(f"{w} x {h}", page)
                self.assertNotIn('id="faq"', page)
            else:
                for url in (pilot.US_SOURCE, pilot.TW_SOURCE, pilot.JP_SOURCE):
                    self.assertIn(f'href="{url}"', page)
                self.assertEqual(locale == "en", 'id="faq"' in page)
                self.assertEqual(locale == "en", '"FAQPage"' in page)
        questions = [q for q, _a in pilot.PASSPORT["copy"]["en"]["faq"]]
        self.assertEqual(["Can you wear glasses in a passport photo?",
                          "Can you smile in a passport photo?",
                          "Why do passport photos get rejected?"], questions)

    def test_no_price_free_or_pro_wording(self):
        root, _ = self.build()
        for _tool, _locale, page in self.pages(root):
            self.assertIsNone(PRICE_WORDS_RE.search(visible_text(page)))
            self.assertNotIn('"offers"', page)
            self.assertNotIn("isAccessibleForFree", page)

    def test_passport_pages_state_photo_only_disclaimer(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            if tool is not pilot.PASSPORT:
                continue
            self.assertIn(html.escape(tool["copy"][locale]["disclaimer"], quote=True), page)
            for key in ("us", "tw", "jp"):
                self.assertIn(f'<option value="{key}">', page)
        presets = pilot.PASSPORT_PRESETS
        self.assertEqual((50.8, 50.8), (presets["us"]["w"], presets["us"]["h"]))
        self.assertEqual((35.0, 45.0), (presets["tw"]["w"], presets["tw"]["h"]))
        self.assertEqual((35.0, 45.0), (presets["jp"]["w"], presets["jp"]["h"]))

    def test_app_store_cta_keeps_app_bound_campaign(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            token = f'{tool["campaign"]}_{locale.replace("-", "_").lower()}'
            app_id = attribution.APP_BOUND_CAMPAIGNS[token]
            self.assertTrue(attribution.app_bound_campaign(token, app_id))
            links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)
            # DUO: page-top button (<token>_top) first, result CTA (<token>) last.
            tokens = [f"{token}_top", token] if tool is pilot.DUO else [token]
            self.assertEqual(len(tokens), len(links))
            for expected, raw in zip(tokens, links, strict=True):
                self.assertTrue(attribution.app_bound_campaign(expected, app_id))
                link = html.unescape(raw)
                self.assertIn(f"/id{app_id}?", link)
                self.assertIn(f"ct={expected}&", link)
                again = attribution.final_store_url(
                    link, "geo_learn", PROVIDER, locale=pilot.STAMP_LOCALE[locale], app_id=app_id
                )
                self.assertIn(f"ct={expected}&", again)
        self.assertFalse(attribution.app_bound_campaign("tool_duo_pair_en", "6780575828"))

    def test_duo_top_cta_only_on_duo_and_before_tool(self):
        root, _ = self.build()
        for tool, _locale, page in self.pages(root):
            if tool is pilot.DUO:
                self.assertEqual(1, page.count(f"<!-- {pilot.TOP_CTA_BLOCK}:start -->"))
                self.assertLess(page.index(pilot.TOP_CTA_BLOCK), page.index('id="tool"'))
            else:
                self.assertNotIn(pilot.TOP_CTA_BLOCK, page)

    def test_cta_hidden_when_app_not_live(self):
        root, _ = self.build(live=())
        for _tool, _locale, page in self.pages(root):
            # The shared counter names the store hosts in code; no link is shown.
            self.assertNotIn("apps.apple.com", without_counter(page))

    def test_google_play_link_added_with_matching_referrer(self):
        android = android_play.load_snapshot()
        self.assertIn("duowallpaperstudio", android)
        root, _ = self.build(android=android)
        for tool, locale, page in self.pages(root):
            if tool["app"] not in android:
                continue
            token = f'{tool["campaign"]}_{locale.replace("-", "_").lower()}'
            self.assertIn(android[tool["app"]]["package"], page)
            self.assertIn(f"utm_source%3D{token}%26", page)
            if tool is pilot.DUO:
                # Top block carries its own _top referrer; the result CTA keeps
                # the injected Play link, and a second pass changes nothing.
                top = page.split(f"<!-- {pilot.TOP_CTA_BLOCK}:end -->")[0]
                self.assertIn(f"utm_source%3D{token}_top%26", top)
                self.assertNotIn(f"utm_source%3D{token}%26", top)
                self.assertEqual(page, android_play.inject_html(page, android))

    def test_tools_index_cards_are_idempotent(self):
        root, _ = self.build()
        pilot.build(root, live_keys={"duowallpaperstudio", "snapport"})
        for locale in pilot.LOCALES:
            index = (root / ("" if locale == "en" else locale) / "tools" / "index.html").read_text(encoding="utf-8")
            for tool in pilot.TOOLS:
                self.assertEqual(1, index.count(f'href="{tool["slug"]}.html"'))

    def test_duo_samples_are_relative_same_site_files(self):
        root, _ = self.build()
        for tool, locale, page in self.pages(root):
            if tool is not pilot.DUO:
                continue
            depth = "../" if locale == "en" else "../../"
            for key in pilot.SAMPLES:
                self.assertIn(f'"{depth}{pilot.SAMPLE_DIR}/{key}-outer.jpg"', page)


if __name__ == "__main__":
    unittest.main()
