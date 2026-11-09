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
ROOT = GEO.parent
sys.path.insert(0, str(GEO))

import android_play  # noqa: E402
import click_beacon  # noqa: E402
import gen_store_attribution as attribution  # noqa: E402
import web_hook_pages as hooks  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PROVIDER = "118326163"
INDEX = '<html><body><section class="wrap grid"><article class="card third"><h2><a href="x.html">X</a></h2></article></section></body></html>'
NETWORK_RE = re.compile(r"\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|<form\b|\.submit\(")
CSP_RE = re.compile(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">')
PRICE_WORDS_RE = re.compile(
    r"\bfree\b|免費|免费|無料|\bpro\b|lifetime|\$\s?\d|NT\$|¥|￥|\d\s?円|\d\s?元|trial|試用|试用|お試し|subscription|訂閱|订阅|サブスク",
    re.IGNORECASE,
)
OTHER_BRANDS_RE = re.compile(r"fliqlo|flipclock\.(?:tv|online|app|us)|days\.to|lddgo|timeonline|bauhaus", re.IGNORECASE)
STORE = json.loads((ROOT / "data" / "stayclock_full.json").read_text(encoding="utf-8"))
STORE_LOCALE = {"en": "en-US", "ja": "ja", "zh-Hant": "zh-Hant", "zh-Hans": "zh-Hans"}
FC = hooks.FLIPCLOCK


def visible_text(page: str) -> str:
    body = page.split("<body>", 1)[1]
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def token(locale: str, position: str) -> str:
    return f"web_flipclock_{locale.replace('-', '_').lower()}_{position}"


class WebHookPagesTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.get("APP_STORE_PROVIDER_TOKEN")
        os.environ["APP_STORE_PROVIDER_TOKEN"] = PROVIDER

    def tearDown(self):
        if self._env is None:
            os.environ.pop("APP_STORE_PROVIDER_TOKEN", None)
        else:
            os.environ["APP_STORE_PROVIDER_TOKEN"] = self._env

    def build(self, live=("stayclock",), android=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pages = Path(tmp.name)
        for locale in FC["locales"]:
            index = pages / ("" if locale == "en" else locale) / "tools" / "index.html"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(INDEX, encoding="utf-8")
        outputs = hooks.build(pages, live_keys=set(live), android_apps=android)
        return pages, outputs

    def pages(self, root):
        for locale in FC["locales"]:
            yield locale, (root / hooks.page_path(FC["slug"], locale)).read_text(encoding="utf-8")

    def test_four_locales_indexable_with_hreflang(self):
        root, outputs = self.build()
        self.assertEqual(("en", "ja", "zh-Hant", "zh-Hans"), FC["locales"])
        self.assertEqual(4, len(outputs))
        for locale, page in self.pages(root):
            url = hooks.canonical(FC["slug"], locale)
            self.assertTrue(url.startswith(PUBLIC_SITE.rstrip("/") + "/"))
            self.assertIn(f'<link rel="canonical" href="{url}">', page)
            self.assertIn(f'<html lang="{locale}">', page)
            self.assertIn('<meta name="robots" content="index,follow">', page)
            for code in FC["locales"]:
                self.assertIn(f'hreflang="{code}" href="{hooks.canonical(FC["slug"], code)}"', page)
            self.assertIn('hreflang="x-default"', page)
        self.assertEqual(Path("zh-Hans/tools/flip-clock.html"), hooks.page_path("flip-clock", "zh-Hans"))

    def test_clock_features_present(self):
        root, _ = self.build()
        for _locale, page in self.pages(root):
            script = "".join(re.findall(r"<script>(.*?)</script>", page, flags=re.S))
            for needle in ("requestFullscreen", "webkitRequestFullscreen", "exitFullscreen",
                           "wakeLock", 'id="h24"', 'id="sec"', 'id="theme"', "prefers-reduced-motion"):
                self.assertIn(needle, page, needle)
            for theme in ("dark", "light", "night"):
                self.assertIn(f'<option value="{theme}">', page)
            self.assertIn("getHours", script)

    def test_only_network_call_is_the_click_counter(self):
        root, _ = self.build(android=android_play.load_snapshot())
        block = click_beacon.click_beacon_block()
        for _locale, page in self.pages(root):
            self.assertEqual(1, page.count(block))
            self.assertIsNone(NETWORK_RE.search(page.replace(block, "")))
            policy = {}
            for part in html.unescape(CSP_RE.findall(page)[0]).split(";"):
                words = part.split()
                if words:
                    policy[words[0]] = words[1:]
            self.assertEqual(["'none'"], policy["default-src"])
            self.assertEqual([click_beacon.CLICK_BEACON_URL], policy["connect-src"])
            bodies = re.findall(r"<script>(.*?)</script>", page, flags=re.S)
            hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(b.encode()).digest()).decode() + "'"
                      for b in bodies]
            self.assertEqual(sorted(hashes), sorted(policy["script-src"]))
            self.assertEqual((page, click_beacon.UNCHANGED), click_beacon.inject_html(page))

    def test_no_price_free_pro_trial_or_other_brand(self):
        root, _ = self.build(android=android_play.load_snapshot())
        for _locale, page in self.pages(root):
            text = visible_text(page)
            self.assertIsNone(PRICE_WORDS_RE.search(text), PRICE_WORDS_RE.search(text))
            self.assertIsNone(OTHER_BRANDS_RE.search(page))
            self.assertNotIn('"offers"', page)
            self.assertNotIn("isAccessibleForFree", page)
        for copy in FC["copy"].values():
            blob = json.dumps(copy, ensure_ascii=False)
            self.assertIsNone(PRICE_WORDS_RE.search(blob))
            self.assertIsNone(OTHER_BRANDS_RE.search(blob))

    def test_app_sentences_restate_store_copy(self):
        """Each App sentence names the App as its store name and only claims
        features the store description states for that locale."""
        claims = {
            "en": ("while charging", "dim red", "true black", "pixel shifting", "StandBy",
                   "Lock Screen", "Apple Watch", "across the room"),
            "ja": ("充電中", "赤い", "真っ黒", "ピクセル", "StandBy", "ロック画面", "Apple Watch", "部屋の隅"),
            "zh-Hant": ("充電時", "柔和紅", "純黑", "像素偏移", "StandBy", "鎖定畫面", "Apple Watch", "隔著房間"),
            "zh-Hans": ("充电时", "柔和红", "纯黑", "像素偏移", "StandBy", "锁定屏幕", "Apple Watch", "隔着房间"),
        }
        for locale, words in claims.items():
            store = STORE[STORE_LOCALE[locale]]
            copy = FC["copy"][locale]
            self.assertIn(store["name"], copy["fs_text"] + copy["bottom_text"])
            for word in words:
                self.assertIn(word, store["description"], (locale, word))
                self.assertIn(word, copy["fs_text"] + copy["bottom_text"], (locale, word))

    def test_two_placements_with_distinct_app_bound_campaigns(self):
        root, _ = self.build()
        for locale, page in self.pages(root):
            links = [html.unescape(u) for u in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)]
            expected = [token(locale, "fs"), token(locale, "bottom")]
            self.assertEqual(2, len(links))
            for want, link in zip(expected, links, strict=True):
                self.assertLessEqual(len(want), 30)
                self.assertTrue(attribution.app_bound_campaign(want, "6814035888"))
                self.assertIn("/id6814035888?", link)
                self.assertIn(f"pt={PROVIDER}&", link)
                self.assertIn(f"ct={want}&", link)
                self.assertRegex(link, r"^https://apps\.apple\.com/([a-z]{2}/)?app/id\d+\?pt=\d+&ct=[A-Za-z0-9_]{1,40}&mt=8$")
                again = attribution.final_store_url(link, "geo_learn", PROVIDER,
                                                    locale=hooks.STAMP_LOCALE[locale], app_id="6814035888")
                self.assertIn(f"ct={want}&", again)
            self.assertLess(page.index('id="fs"'), page.index('id="app-fs"'))
            self.assertLess(page.index('id="tool"'), page.index(hooks.BOTTOM_BLOCK))
        self.assertFalse(attribution.app_bound_campaign(token("en", "fs"), "6824946559"))
        self.assertEqual(8, len(attribution.WEB_HOOK_CAMPAIGNS))

    def test_google_play_links_carry_each_placement_referrer(self):
        android = android_play.load_snapshot()
        self.assertIn("stayclock", android)
        root, _ = self.build(android=android)
        for locale, page in self.pages(root):
            self.assertIn(android["stayclock"]["package"], page)
            bottom = page.split(f"<!-- {hooks.BOTTOM_BLOCK}:start -->")[1]
            top = page.split(f"<!-- {hooks.BOTTOM_BLOCK}:start -->")[0]
            self.assertIn(f"utm_source%3D{token(locale, 'bottom')}%26", bottom)
            self.assertIn(f"utm_source%3D{token(locale, 'fs')}%26", top)
            self.assertEqual(page, android_play.inject_html(page, android))

    def test_no_store_link_when_app_not_live(self):
        root, _ = self.build(live=())
        block = click_beacon.click_beacon_block()
        for _locale, page in self.pages(root):
            self.assertNotIn("apps.apple.com", page.replace(block, ""))

    def test_tools_index_cards_are_idempotent(self):
        root, _ = self.build()
        hooks.build(root, live_keys={"stayclock"})
        for locale in FC["locales"]:
            index = (root / ("" if locale == "en" else locale) / "tools" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(1, index.count('href="flip-clock.html"'))

    def test_clock_script_runs(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        root, _ = self.build()
        page = dict(self.pages(root))["en"]
        script = re.findall(r"<script>(.*?)</script>", page, flags=re.S)[-1]
        harness = r"""
const els={};function el(id){if(!els[id])els[id]={id,hidden:false,checked:id==="sec",value:"dark",dataset:{},textContent:"",children:[],
appendChild(c){this.children.push(c);c.parentNode=this;},addEventListener(){},classList:{add(){},remove(){}},
querySelector(sel){return all(this).find(x=>x.className===sel.slice(1))||null;},
querySelectorAll(sel){return all(this).filter(x=>sel==='.digit span'?x.tag==='span'&&x.parentNode.className==='digit':x.className===sel.slice(1));}};return els[id];}
function all(n){let out=[];for(const c of n.children||[]){out.push(c);out=out.concat(all(c));}return out;}
Object.defineProperty(el("clock"),"textContent",{set(v){this.children=[];},get(){return "";}});
globalThis.document={getElementById:el,addEventListener(){},fullscreenEnabled:true,
createElement(tag){return {tag,className:"",textContent:"",children:[],appendChild(c){this.children.push(c);c.parentNode=this;},classList:{add(){},remove(){}}};}};
globalThis.localStorage={getItem(){return null;},setItem(){}};
globalThis.setTimeout=()=>0;
""" + script + r"""
const digits=all(el("clock")).filter(x=>x.tag==="span"&&x.parentNode.className==="digit").map(x=>x.textContent).join("");
const ampm=all(el("clock")).filter(x=>x.className==="ampm").map(x=>x.textContent).join("");
process.stdout.write(JSON.stringify({digits,ampm}));
"""
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
        result = json.loads(out.stdout)
        self.assertRegex(result["digits"], r"^\d{6}$")
        self.assertIn(result["ampm"], ("AM", "PM"))


if __name__ == "__main__":
    unittest.main()
