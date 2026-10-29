#!/usr/bin/env python3
"""下載按鈕匿名點擊計數:共用區塊與指南站部署前注入。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.parse
from pathlib import Path
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import click_beacon as cb  # noqa: E402

PAGE = (
    '<!doctype html>\n<html lang="en"><head><title>S</title>\n</head><body>'
    '<a href="https://apps.apple.com/app/id111111111?pt=1&amp;ct=geo_x&amp;mt=8">Get</a>'
    "</body></html>\n"
)
CSP = ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
       "script-src 'self'; connect-src 'none'\">")


def _write(root: Path, relative: str, body: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


class BlockTests(unittest.TestCase):
    def test_payload_is_anonymous_and_safe(self):
        block = cb.click_beacon_block()
        self.assertTrue(block.startswith(cb.CLICK_START + "\n<script>"))
        self.assertTrue(block.endswith("</script>\n" + cb.CLICK_END))
        self.assertIn("navigator.sendBeacon", block)
        self.assertIn("'https://office.cait518.cc/api/click'", block)
        self.assertNotIn("cookie", block.lower())
        self.assertNotIn("localStorage", block)
        self.assertNotIn("preventDefault", block)
        self.assertNotIn("Blob", block)  # 字串 body = text/plain,不觸發 CORS 預檢
        # 不得被當成商店連結(各閘門的 href="https://apps.apple.com/... 檢查)
        self.assertNotIn("https://apps.apple.com", block)
        self.assertNotIn("https://play.google.com", block)
        self.assertNotIn("@", block)  # 不會被 public_email 當成 email／套件版本
        self.assertEqual(1, block.count("</"))
        self.assertEqual(1, len(cb.CLICK_RE.findall(block + "\n")))


class InjectHtmlTests(unittest.TestCase):
    def test_added_once_before_head_close_and_idempotent(self):
        once, status = cb.inject_html(PAGE)
        self.assertEqual(cb.ADDED, status)
        self.assertEqual(1, once.count(cb.CLICK_START))
        self.assertIn(cb.click_beacon_block() + "\n</head>", once)
        again, status = cb.inject_html(once)
        self.assertEqual((once, cb.UNCHANGED), (again, status))
        self.assertEqual(PAGE, cb.CLICK_RE.sub("", once))

    def test_correct_block_elsewhere_is_left_in_place(self):
        page = PAGE.replace("<body>", "<body>" + cb.click_beacon_block() + "\n")
        self.assertEqual((page, cb.UNCHANGED), cb.inject_html(page))

    def test_stale_or_duplicate_blocks_are_replaced_by_one(self):
        stale = cb.CLICK_START + "\n<script>old()</script>\n" + cb.CLICK_END + "\n"
        for page in (PAGE.replace("</head>", stale + "</head>"),
                     PAGE.replace("</head>", stale + stale + "</head>")):
            fixed, status = cb.inject_html(page)
            self.assertEqual(cb.ADDED, status)
            self.assertNotIn("old()", fixed)
            self.assertEqual(cb.inject_html(PAGE)[0], fixed)

    def test_csp_and_amp_pages_never_carry_it(self):
        amp_story = PAGE.replace("<body>", "<body><amp-story standalone>")
        cases = {
            cb.SKIP_CSP: PAGE.replace("<title>", CSP + "<title>"),
            cb.SKIP_AMP: PAGE.replace('<html lang="en">', '<html ⚡ lang="en">'),
        }
        for expected, page in cases.items():
            self.assertEqual((page, expected), cb.inject_html(page))
            with_block = page.replace("</head>", cb.click_beacon_block() + "\n</head>")
            self.assertEqual((page, cb.REMOVED), cb.inject_html(with_block))
        self.assertEqual((amp_story, cb.SKIP_AMP), cb.inject_html(amp_story))
        amp_attr = PAGE.replace('<html lang="en">', '<html lang="en" amp>')
        self.assertEqual(cb.SKIP_AMP, cb.inject_html(amp_attr)[1])
        # class／data 屬性裡的 amp 字樣不是 AMP 文件
        not_amp = PAGE.replace('<html lang="en">', '<html lang="en" class="amp-x" data-amp="1">')
        self.assertEqual(cb.ADDED, cb.inject_html(not_amp)[1])

    def test_ambiguous_head_or_markers_are_not_guessed(self):
        for page in (PAGE.replace("</head>", ""), PAGE.replace("</head>", "</head></head>")):
            self.assertEqual((page, cb.SKIP_HEAD), cb.inject_html(page))
        broken = PAGE.replace("</head>", cb.CLICK_START + "</head>")
        self.assertEqual((broken, cb.SKIP_MALFORMED), cb.inject_html(broken))

    def test_store_links_are_untouched(self):
        once, _ = cb.inject_html(PAGE)
        anchor = '<a href="https://apps.apple.com/app/id111111111?pt=1&amp;ct=geo_x&amp;mt=8">Get</a>'
        self.assertEqual(1, once.count(anchor))


class InjectTreeTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_tree_pass_skips_pinned_engine_and_symlinked_pages(self):
        root = self.root
        plain = _write(root, "en-US/answers/a.html", PAGE)
        top = _write(root, "index.html", PAGE)
        hero = _write(root, "en-US/tools/h.html", PAGE)
        route = _write(root, "en-US/decide/x/r.html", PAGE)
        gallery = _write(root, "en-US/results/index.html", PAGE)
        retired = _write(root, "ja/results/index.html", PAGE)
        engine = _write(root, "_engine/geo/x.html", PAGE)
        github = _write(root, ".github/x.html", PAGE)
        _write(root, "data/hero-tasks/manifest.json",
               json.dumps({"outputs": {"en-US/tools/h.html": "0" * 64}}))
        _write(root, "data/high-intent-decision-routes/expected-output-manifest.json",
               json.dumps({"expected_outputs": [
                   {"relative_path": "en-US/decide/x/r.html", "generated_sha256": "0" * 64}]}))
        _write(root, "data/result-image-coverage.json",
               json.dumps({"pages": {"en-US/results/index.html": {}},
                           "retired_pages": {"ja/results/index.html": {}}}))
        link = root / "en-US/link.html"
        link.symlink_to(plain)
        stats = cb.inject_tree(root)
        self.assertEqual(2, stats[cb.ADDED])
        self.assertEqual(2, stats["with_beacon"])
        self.assertEqual(4, stats["pinned"])
        for path in (plain, top):
            self.assertEqual(1, path.read_text().count(cb.CLICK_START), path)
        for path in (hero, route, gallery, retired, engine, github):
            self.assertEqual(PAGE, path.read_text(), path)
        again = cb.inject_tree(root)
        self.assertEqual((0, 2), (again[cb.ADDED], again[cb.UNCHANGED]))

    def test_relative_pages_dir_like_the_workflow(self):
        _write(self.root, "index.html", PAGE)
        _write(self.root, "data/hero-tasks/manifest.json",
               json.dumps({"outputs": {"index.html": "0" * 64}}))
        _write(self.root, "fr-FR/index.html", PAGE)
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            stats = cb.inject_tree(Path("."))
        finally:
            os.chdir(cwd)
        self.assertEqual(1, stats[cb.ADDED])
        self.assertEqual(PAGE, (self.root / "index.html").read_text())

    def test_missing_or_broken_manifests_pin_nothing(self):
        _write(self.root, "a.html", PAGE)
        _write(self.root, "data/hero-tasks/manifest.json", "{not json")
        self.assertEqual(1, cb.inject_tree(self.root)[cb.ADDED])


DUO_ID = cb.AICT_APPS["duowallpaperstudio"]
DUO_LINK = f"https://apps.apple.com/jp/app/id{DUO_ID}?pt=118326163&amp;ct=geo_pick&amp;mt=8"
DUO_PAGE = (
    '<!doctype html>\n<html lang="ja"><head><title>D</title>\n</head><body>'
    f'<a id="duo" href="{DUO_LINK}">Get</a>'
    f'<a id="rev" href="https://apps.apple.com/jp/app/id{DUO_ID}?action=write-review">Rate</a>'
    '<a id="other" href="https://apps.apple.com/jp/app/id111111111?pt=1&amp;ct=geo_x&amp;mt=8">Other</a>'
    '<a id="play" href="https://play.google.com/store/apps/details?id=com.example.duo&amp;referrer='
    'utm_source%3Dgeo_pick%26utm_campaign%3Dduowallpaperstudio">Play</a>'
    '<a id="oplay" href="https://play.google.com/store/apps/details?id=com.example.x&amp;referrer='
    'utm_source%3Dgeo_x%26utm_campaign%3Dmochi">Play2</a>'
    "</body></html>\n"
)


class AiCtBlockTests(unittest.TestCase):
    """人工智慧來源追蹤碼:只放雙螢幕桌布自己的頁面,碼合規,非人工智慧來源時連結不變。"""

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_tokens_are_registered_campaigns(self):
        agent = GEO.parent / "agent"
        if not (agent / "ct_codes.py").is_file():
            self.skipTest("agent/ct_codes.py lives only in 00_GrowthEngine")
        if str(agent) not in sys.path:
            sys.path.insert(0, str(agent))
        try:
            import ct_codes
        except ImportError:
            self.skipTest("agent/ct_codes.py lives only in 00_GrowthEngine")
        tokens = {ct for _, ct in cb.AICT_ENGINES} | set(cb.AICT_NAMES.values())
        self.assertEqual({"ai_chatgpt", "ai_perplexity", "ai_gemini", "ai_copilot"}, tokens)
        for token in tokens:
            self.assertEqual([], ct_codes.ct_problems(token), token)
            self.assertEqual("ai_referral", ct_codes.channel_for_ct(token))

    def test_scope_is_only_the_apps_own_pages(self):
        self.assertEqual({"duowallpaperstudio": "6824946559"}, cb.AICT_APPS)
        for rel in ("ja/duowallpaperstudio.html", "hubs/duowallpaperstudio.html",
                    "apps/duowallpaperstudio/decision/l/ja/index.html",
                    "alternatives/duowallpaperstudio-vs-x.html", "guides/duowallpaperstudio.html"):
            self.assertEqual("duowallpaperstudio", cb.ai_ct_app(rel, DUO_PAGE), rel)
        self.assertIsNone(cb.ai_ct_app("en-US/answers/foldable.html", DUO_PAGE))
        self.assertIsNone(cb.ai_ct_app("ja/mochi.html", DUO_PAGE))
        self.assertIsNone(cb.ai_ct_app("ja/duowallpaperstudiox.html", DUO_PAGE))
        self.assertIsNone(cb.ai_ct_app("ja/duowallpaperstudio.html", PAGE))

    def test_tree_pass_adds_only_to_duo_pages_and_is_idempotent(self):
        root = self.root
        duo = _write(root, "ja/duowallpaperstudio.html", DUO_PAGE)
        answer = _write(root, "en-US/answers/a.html", DUO_PAGE)
        other = _write(root, "ja/mochi.html", PAGE)
        pinned = _write(root, "en-US/decide/duowallpaperstudio/r.html", DUO_PAGE)
        amp = _write(root, "stories/duowallpaperstudio.html",
                     DUO_PAGE.replace('<html lang="ja">', '<html amp lang="ja">'))
        _write(root, "data/high-intent-decision-routes/expected-output-manifest.json",
               json.dumps({"expected_outputs": [
                   {"relative_path": "en-US/decide/duowallpaperstudio/r.html"}]}))
        stats = cb.inject_tree(root)
        self.assertEqual((1, 1), (stats["ai_ct_pages"], stats["ai_ct_skipped"]))
        text = duo.read_text()
        self.assertEqual(1, text.count(cb.AICT_START))
        self.assertLess(text.index(cb.AICT_END), text.index("</head>"))
        self.assertIn(DUO_LINK, text)  # 靜態連結不改
        for path in (answer, other, amp):
            self.assertNotIn(cb.AICT_START, path.read_text(), path)
        self.assertEqual(DUO_PAGE, pinned.read_text())
        again = cb.inject_tree(root)
        self.assertEqual(text, duo.read_text())
        self.assertEqual(1, again["ai_ct_pages"])

    def test_stale_block_is_removed_from_out_of_scope_pages(self):
        stale = PAGE.replace("</head>", cb.ai_ct_block() + "\n</head>")
        path = _write(self.root, "ja/mochi.html", stale)
        cb.inject_tree(self.root)
        self.assertNotIn(cb.AICT_START, path.read_text())
        self.assertIn(cb.CLICK_START, path.read_text())

    def _run_js(self, url: str, referrer: str) -> dict:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        anchors = {}
        for anchor_id in ("duo", "rev", "other", "play", "oplay"):
            start = DUO_PAGE.index(f'id="{anchor_id}" href="') + len(f'id="{anchor_id}" href="')
            anchors[anchor_id] = DUO_PAGE[start:DUO_PAGE.index('"', start)].replace("&amp;", "&")
        js = cb.ai_ct_block().split("<script>", 1)[1].split("</script>", 1)[0]
        harness = (
            "const A=" + json.dumps(anchors) + ";"
            "const els=Object.entries(A).map(([id,href])=>({id,href}));"
            "globalThis.location=new URL(" + json.dumps(url) + ");"
            "globalThis.document={referrer:" + json.dumps(referrer) + ",readyState:'complete',"
            "querySelectorAll:()=>els,addEventListener:()=>{}};"
            + js +
            "process.stdout.write(JSON.stringify(Object.fromEntries(els.map(e=>[e.id,e.href]))));"
        )
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
        return {"before": anchors, "after": json.loads(out.stdout)}

    def test_runtime_leaves_links_alone_without_ai_source(self):
        page = "https://guide.example/ja/duowallpaperstudio.html"
        for url, ref in ((page, ""), (page, "https://www.google.com/"),
                         (page + "?utm_source=newsletter", "https://bing.com/"),
                         (page + "?utm_source=constructor", ""),
                         (page, "https://notchatgpt.com/")):
            run = self._run_js(url, ref)
            self.assertEqual(run["before"], run["after"], (url, ref))

    def test_runtime_swaps_only_the_apps_tracked_links(self):
        page = "https://guide.example/ja/duowallpaperstudio.html"
        cases = (
            (page, "https://chatgpt.com/", "ai_chatgpt"),
            (page + "?utm_source=chatgpt.com", "", "ai_chatgpt"),
            (page, "https://www.perplexity.ai/search", "ai_perplexity"),
            (page + "?utm_source=perplexity", "", "ai_perplexity"),
            (page, "https://gemini.google.com/", "ai_gemini"),
            (page, "https://copilot.microsoft.com/", "ai_copilot"),
        )
        for url, ref, token in cases:
            run = self._run_js(url, ref)
            before, after = run["before"], run["after"]
            duo = urllib.parse.urlsplit(after["duo"])
            query = dict(urllib.parse.parse_qsl(duo.query))
            self.assertEqual(token, query["ct"], (url, ref))
            self.assertEqual(("apps.apple.com", f"/jp/app/id{DUO_ID}"), (duo.netloc, duo.path))
            self.assertEqual({"pt": "118326163", "mt": "8"}, {k: query[k] for k in ("pt", "mt")})
            for unchanged in ("rev", "other", "oplay"):
                self.assertEqual(before[unchanged], after[unchanged], unchanged)
            play = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(after["play"]).query))
            referrer = dict(urllib.parse.parse_qsl(play["referrer"]))
            self.assertEqual({"utm_source": token, "utm_campaign": "duowallpaperstudio"}, referrer)
            self.assertEqual("com.example.duo", play["id"])


class PagesWorkflowTests(unittest.TestCase):
    """指南站部署:兩種發布模式都放計數,而且在封存頁面位元組的閘門之前。"""

    def setUp(self):
        default = GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages"
        guide = Path(os.environ.get("GEO_PAGES") or default)
        workflow = guide / ".github/workflows/pages.yml"
        if not workflow.is_file():
            self.skipTest("Guide pages.yml is not checked out next to this engine")
        self.source = workflow.read_text(encoding="utf-8")

    def test_inject_runs_in_both_modes_after_html_writers_before_seals(self):
        source = self.source
        name = "- name: Add the anonymous download-click counter"
        step = source.split(name, 1)[1].split("- name:", 1)[0]
        self.assertIn("python3 _engine/geo/click_beacon.py inject --pages .", step)
        self.assertNotIn("incremental_high_intent", step)
        at = source.index(name)
        for before in ("deployment_generation.py prepare",
                       "name: Require complete local-only hero results before upload",
                       "name: Gate evidenced native result images"):
            self.assertLess(source.index(before), at, before)
        for after in ("name: Re-render public email protection after deployment preparation",
                      "name: Require all production HTML email protection",
                      "owned_feed_release.py seal",
                      "rm -rf _engine",
                      "actions/upload-pages-artifact@"):
            self.assertLess(at, source.index(after), after)


if __name__ == "__main__":
    unittest.main()
