#!/usr/bin/env python3
"""indexnow_support_sites：支援站頁面送 IndexNow（不連網，全部用假回應）。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import indexnow_support_sites as sup  # noqa: E402

SITE = "https://open.cait518.cc"
DAY1 = dt.datetime(2026, 10, 17, 5, tzinfo=dt.timezone.utc)
DAY2 = DAY1 + dt.timedelta(days=1)
DAY3 = DAY1 + dt.timedelta(days=2)
KEY = "0123456789abcdef0123456789abcdef"
ROBOTS = (
    "User-agent: *\nAllow: /\n\n"
    f"Sitemap: {SITE}/sitemap.xml\n"
    f"Sitemap: {SITE}/ios-app-guide/sitemap.xml\n"
    f"Sitemap: {SITE}/mochitodo-support/sitemap.xml\n"
    f"Sitemap: {SITE}/lensafe-support/sitemap.xml\n"
    f"Sitemap: https://example.com/other-support/sitemap.xml\n"
    f"Sitemap: {SITE}/awesome-zhuyin-bopomofo-apps/sitemap.xml\n"
)


def page(url, *, canonical=None, robots=None, text="hello"):
    head = f'<link rel="canonical" href="{canonical or url}">'
    if robots:
        head += f'<meta name="robots" content="{robots}">'
    return f"<!DOCTYPE html><html><head>{head}<style>x{{}}</style></head><body><p>{text}</p></body></html>"


def urlset(*urls):
    rows = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>'


class FakeWeb:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        value = self.routes.get(url)
        if value is None:
            return 404, url, ""
        if isinstance(value, tuple):
            return value
        return 200, url, value


def base_routes():
    m = f"{SITE}/mochitodo-support"
    u = f"{SITE}/usagenow-support"
    return {
        f"{SITE}/robots.txt": ROBOTS,
        f"{m}/sitemap.xml": urlset(f"{m}/", f"{m}/help.html", f"{m}/data.json", f"{SITE}/ios-app-guide/x.html",
                                   f"{m}/help.html?x=1"),
        f"{m}/bm-sitemap.xml": urlset(f"{m}/qaimat.ar-SA.html", f"{m}/help.html", f"{m}/moved.html",
                                      f"{m}/noindex.html", f"{m}/dupe.html", f"{m}/gone.html"),
        f"{m}/": page(f"{m}/"),
        f"{m}/help.html": page(f"{m}/help.html"),
        f"{m}/qaimat.ar-SA.html": page(f"{m}/qaimat.ar-SA.html", text="مرحبا"),
        f"{m}/moved.html": (200, f"{SITE}/elsewhere.html", page(f"{SITE}/elsewhere.html")),
        f"{m}/noindex.html": page(f"{m}/noindex.html", robots="noindex, follow"),
        f"{m}/dupe.html": page(f"{m}/dupe.html", canonical=f"{m}/help.html"),
        f"{u}/sitemap.xml": urlset(f"{u}/claude-usage-limit.html"),
        f"{u}/claude-usage-limit.html": page(f"{u}/claude-usage-limit.html"),
    }


def args_for(tmp, **over):
    key_file = Path(tmp) / f"{KEY}.txt"
    key_file.write_text(KEY + "\n", encoding="utf-8")
    values = dict(site=SITE, key_file=str(key_file), key_location=None, extra_site=["usagenow-support"],
                  state_file=str(Path(tmp) / "state.json"), receipt_file=str(Path(tmp) / "receipt.json"),
                  all=False, dry_run=False, workers=2, sitemaps="all")
    values.update(over)
    return argparse.Namespace(**values)


class SupportIndexNowTest(unittest.TestCase):
    def test_robots_parsing_keeps_only_support_dirs_on_the_host(self):
        self.assertEqual(["mochitodo-support", "lensafe-support"], sup.support_dirs_from_robots(ROBOTS, SITE))

    def test_scope_filter(self):
        m = f"{SITE}/mochitodo-support"
        self.assertTrue(sup.in_scope(f"{m}/a.html", SITE, "mochitodo-support"))
        self.assertTrue(sup.in_scope(f"{m}/ar-SA/", SITE, "mochitodo-support"))
        for bad in (f"{m}/a.json", f"{m}/a.html?x=1", f"{m}/a.html#top", f"{SITE}/ios-app-guide/a.html",
                    f"{SITE}/mochitodo-supportx/a.html"):
            self.assertFalse(sup.in_scope(bad, SITE, "mochitodo-support"), bad)

    def test_run_submits_only_live_canonical_pages_with_the_root_key(self):
        web = FakeWeb(base_routes())
        sent = []

        def sender(endpoint, payload):
            sent.append((endpoint, json.loads(payload)))
            return 202

        with tempfile.TemporaryDirectory() as tmp:
            receipt = sup.run(args_for(tmp), fetcher=web, sender=sender, now=DAY1)
            m = f"{SITE}/mochitodo-support"
            expected = sorted([f"{m}/", f"{m}/help.html", f"{m}/qaimat.ar-SA.html",
                               f"{SITE}/usagenow-support/claude-usage-limit.html"])
            self.assertEqual(len(sup.indexnow.ENDPOINTS), len(sent))
            for endpoint, payload in sent:
                self.assertIn(endpoint, sup.indexnow.ENDPOINTS)
                self.assertEqual("open.cait518.cc", payload["host"])
                self.assertEqual(f"{SITE}/{KEY}.txt", payload["keyLocation"])
                self.assertEqual(expected, payload["urlList"])
            self.assertEqual({"redirected": 1, "noindex": 1, "canonical_elsewhere": 1, "http_404": 1},
                             receipt["skipped"])
            self.assertEqual({"skipped": "abandoned"}, receipt["sitemap_reads"]["lensafe-support"])
            self.assertNotIn(f"{SITE}/lensafe-support/sitemap.xml", web.calls)
            on_disk = json.loads(Path(tmp, "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(4, on_disk["selected"])

            # 第二次：內容沒變就不送；改了一頁就只送那一頁。
            sent.clear()
            again = sup.run(args_for(tmp), fetcher=FakeWeb(base_routes()), sender=sender, now=DAY2)
            self.assertEqual(0, again["selected"])
            self.assertEqual([], sent)
            routes = base_routes()
            routes[f"{m}/help.html"] = page(f"{m}/help.html", text="changed")
            third = sup.run(args_for(tmp), fetcher=FakeWeb(routes), sender=sender, now=DAY3)
            self.assertEqual(1, third["selected"])
            self.assertEqual([[f"{m}/help.html"]] * len(sup.indexnow.ENDPOINTS),
                             [p["urlList"] for _, p in sent])

    def test_second_trigger_on_the_same_utc_day_is_skipped_without_fetching(self):
        with tempfile.TemporaryDirectory() as tmp:
            sup.run(args_for(tmp), fetcher=FakeWeb(base_routes()), sender=lambda e, p: 202, now=DAY1)
            web = FakeWeb(base_routes())
            later = DAY1 + dt.timedelta(hours=11)
            receipt = sup.run(args_for(tmp), fetcher=web, sender=lambda e, p: self.fail("must not send"), now=later)
            self.assertEqual("already_checked_today", receipt["skipped"])
            self.assertEqual([], web.calls)
            # --all 不受同日限制。
            forced = sup.run(args_for(tmp, all=True), fetcher=FakeWeb(base_routes()), sender=lambda e, p: 202,
                             now=later)
            self.assertEqual(4, forced["selected"])

    def test_head_markup_changes_do_not_trigger_a_resubmit(self):
        body = page("https://x/a.html")
        self.assertEqual(sup.visible_digest(body),
                         sup.visible_digest(body.replace("<style>x{}</style>", "<style>y{}</style>")))

    def test_rejected_endpoint_fails_closed_and_keeps_state(self):
        def sender(endpoint, payload):
            raise sup.indexnow.SubmissionError(f"{endpoint} returned HTTP 403: key not found")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sup.indexnow.SubmissionError):
                sup.run(args_for(tmp), fetcher=FakeWeb(base_routes()), sender=sender)
            self.assertFalse(Path(tmp, "state.json").exists())

    def test_missing_robots_or_sitemap_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            routes = base_routes()
            routes[f"{SITE}/robots.txt"] = (500, f"{SITE}/robots.txt", "")
            with self.assertRaises(sup.SupportIndexNowError):
                sup.run(args_for(tmp), fetcher=FakeWeb(routes), sender=lambda e, p: 202)
            routes = base_routes()
            del routes[f"{SITE}/usagenow-support/sitemap.xml"]
            with self.assertRaises(sup.SupportIndexNowError):
                sup.run(args_for(tmp), fetcher=FakeWeb(routes), sender=lambda e, p: 202)

    def test_key_location_must_stay_on_the_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                sup.run(args_for(tmp, key_location="https://example.com/k.txt"), fetcher=FakeWeb(base_routes()),
                        sender=lambda e, p: 202)

    def test_dry_run_sends_nothing_and_writes_no_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = sup.run(args_for(tmp, dry_run=True), fetcher=FakeWeb(base_routes()),
                              sender=lambda e, p: self.fail("dry run must not send"))
            self.assertEqual(4, receipt["selected"])
            self.assertFalse(Path(tmp, "state.json").exists())

    def test_workflow_step_uses_the_root_key_and_saves_state(self):
        # Plain-text checks: the runner's system python may lack PyYAML.
        text = (HERE.parents[1] / ".github" / "workflows" / "indexnow-daily.yml").read_text(encoding="utf-8")
        daily = text.index("- name: Submit every App homepage (once per UTC day)")
        support = text.index("- name: Submit support-site pages (EXP-03)")
        save = text.index("- name: Save durable IndexNow state")
        self.assertLess(daily, support)
        self.assertLess(support, save)
        step = text[support:text.index("- name:", support + 1)]
        self.assertIn("continue-on-error: true", step)
        self.assertIn("test_indexnow_support_sites.py", step)
        self.assertIn("--site https://open.cait518.cc \\", step)
        self.assertIn('--key-location "https://open.cait518.cc/$(basename "$keyfile")"', step)
        self.assertIn('--state-file ".indexnow-state/support-sites.json"', step)
        for site in ("usagenow-support", "zipbox-support"):
            self.assertIn(f"--extra-site {site}", step)
        self.assertNotIn("lensafe", step)

    def test_bm_only_mode_reads_only_intent_sitemaps(self):
        web = FakeWeb(base_routes())
        with tempfile.TemporaryDirectory() as tmp:
            receipt = sup.run(args_for(tmp, sitemaps="bm", dry_run=True), fetcher=web,
                              sender=lambda e, p: self.fail("dry run must not send"))
            m = f"{SITE}/mochitodo-support"
            self.assertNotIn(f"{m}/sitemap.xml", web.calls)
            self.assertEqual(2, receipt["selected"])  # qaimat + help（moved／noindex／dupe／gone 都被擋）
            self.assertEqual("no_bm_sitemap", receipt["sitemap_reads"]["usagenow-support"]["skipped"])

    def test_extra_site_must_be_a_support_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sup.SupportIndexNowError):
                sup.run(args_for(tmp, extra_site=["../etc"]), fetcher=FakeWeb(base_routes()),
                        sender=lambda e, p: 202)


if __name__ == "__main__":
    unittest.main()
