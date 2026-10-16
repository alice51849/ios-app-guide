#!/usr/bin/env python3
"""Daily IndexNow push of every App homepage: coverage, cap and once-a-day."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import indexnow_app_pages as pages  # noqa: E402

SITE = "https://open.cait518.cc/ios-app-guide"
LOCALES = pages.OFFICIAL_LOCALES
NOW = dt.datetime(2026, 10, 16, 4, 50, tzinfo=dt.timezone.utc)


def build_site(root: Path, keys=("alpha", "beta"), extra_records=()):
    (root / "data").mkdir()
    records = [
        {"key": key, "app_store_id": str(7000000000 + index), "verified_live": True}
        for index, key in enumerate(keys)
    ] + list(extra_records)
    (root / "data" / "verified-ios-app-finder-catalog.json").write_text(
        json.dumps({"apps": records}), encoding="utf-8")
    locs = [f"{SITE}/{locale}/{key}.html" for key in keys for locale in LOCALES]
    locs += [f"{SITE}/guides/{key}.html" for key in keys]
    locs += [f"{SITE}/en-US/answers/unrelated.html", f"{SITE}/en-US/lensafe.html"]
    (root / "sitemap.xml").write_text(
        "<urlset>" + "".join(f"<url><loc>{loc}</loc></url>" for loc in locs) + "</urlset>",
        encoding="utf-8")
    (root / "linkset.json").write_text(json.dumps({"linkset": [{
        "anchor": f"{SITE}/index.html",
        "item": [{"href": f"{SITE}/guides/{key}.html"} for key in (*keys, "lensafe")],
    }]}), encoding="utf-8")
    key_file = root / ("a" * 32 + ".txt")
    key_file.write_text("a" * 32, encoding="utf-8")
    return key_file


class Sender:
    def __init__(self):
        self.payloads = []

    def __call__(self, endpoint, payload):
        self.payloads.append((endpoint, json.loads(payload)))
        return 200


class IndexNowAppPagesTests(unittest.TestCase):
    def test_every_live_app_homepage_in_every_locale_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_site(root, extra_records=[
                {"key": "lensafe", "app_store_id": "7100000000", "verified_live": True},
                {"key": "gone", "app_store_id": "7100000001", "verified_live": False},
            ])
            urls = pages.app_page_urls(root, SITE, pages.indexnow.read_urls(root, SITE))
        self.assertEqual(2 * len(LOCALES) + 2, len(urls))
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn(f"{SITE}/zh-Hant/alpha.html", urls)
        self.assertIn(f"{SITE}/guides/beta.html", urls)
        self.assertFalse(any("lensafe" in url or "gone" in url for url in urls))
        self.assertFalse(any("/answers/" in url for url in urls))

    def test_url_outside_the_deployed_sitemap_is_never_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_site(root)
            sitemap = [f"{SITE}/en-US/alpha.html"]
            self.assertEqual(sitemap, pages.app_page_urls(root, SITE, sitemap))

    def test_daily_cap_stays_far_below_indexnow_limit(self):
        self.assertLessEqual(pages.MAX_DAILY_URLS, pages.indexnow.DEFAULT_BATCH_SIZE // 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = tuple(f"app{index:03d}" for index in range(110))
            build_site(root, keys=keys)
            with self.assertRaisesRegex(ValueError, "daily cap"):
                pages.app_page_urls(root, SITE, pages.indexnow.read_urls(root, SITE))

    def test_real_repository_daily_total_is_bounded(self):
        root = HERE.parents[1]
        urls = pages.app_page_urls(root, SITE, pages.indexnow.read_urls(root, SITE))
        live = pages.live_app_keys(root)
        self.assertNotIn("lensafe", live)
        self.assertGreaterEqual(len(urls), len(live) * len(LOCALES))
        self.assertLessEqual(len(urls), pages.MAX_DAILY_URLS)

    def test_submits_once_per_utc_day_to_every_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_file = build_site(root)
            state = root / ".indexnow-state" / "app-pages.json"
            sender = Sender()
            accepted = pages.run(root, SITE, key_file, state_file=state,
                                 sender=sender, clock=lambda: NOW)
            self.assertEqual(2 * len(LOCALES) + 2, accepted)
            self.assertEqual(set(pages.indexnow.ENDPOINTS), {e for e, _ in sender.payloads})
            for _, payload in sender.payloads:
                self.assertEqual("open.cait518.cc", payload["host"])
                self.assertEqual(accepted, len(payload["urlList"]))
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual("2026-10-16", saved["date"])

            # Same day (retry, second schedule, dispatch): nothing is resent.
            again = Sender()
            later = NOW + dt.timedelta(hours=12)
            self.assertEqual(0, pages.run(root, SITE, key_file, state_file=state,
                                          sender=again, clock=lambda: later))
            self.assertEqual([], again.payloads)

            # Next UTC day: the full set goes out again.
            tomorrow = Sender()
            next_day = NOW + dt.timedelta(days=1)
            self.assertEqual(accepted, pages.run(root, SITE, key_file, state_file=state,
                                                 sender=tomorrow, clock=lambda: next_day))

    def test_urls_the_incremental_step_sent_today_are_not_resent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_file = build_site(root)
            receipt = root / "accepted-receipt.json"
            receipt.write_text(json.dumps({
                "kind": "indexnow_submission_receipt",
                "semantics": "accepted_by_endpoints_not_indexed",
                "accepted_at": "2026-10-16T04:49:00+00:00",
                "urls": [f"{SITE}/en-US/alpha.html", f"{SITE}/ja/beta.html"],
            }), encoding="utf-8")
            sender = Sender()
            accepted = pages.run(root, SITE, key_file, state_file=root / "s.json",
                                 incremental_receipt=receipt, sender=sender,
                                 clock=lambda: NOW)
            self.assertEqual(2 * len(LOCALES), accepted)
            sent = sender.payloads[0][1]["urlList"]
            self.assertNotIn(f"{SITE}/en-US/alpha.html", sent)

            # Yesterday's receipt does not suppress today's push.
            receipt.write_text(json.dumps({
                "kind": "indexnow_submission_receipt",
                "semantics": "accepted_by_endpoints_not_indexed",
                "accepted_at": "2026-10-15T16:49:00+00:00",
                "urls": [f"{SITE}/en-US/alpha.html"],
            }), encoding="utf-8")
            self.assertEqual(set(), pages.already_sent_today(receipt, NOW.date()))

    def test_rejected_endpoint_fails_and_keeps_the_day_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_file = build_site(root)
            state = root / "s.json"

            def reject(endpoint, payload):
                raise pages.indexnow.SubmissionError(f"{endpoint} returned HTTP 403")

            with self.assertRaises(pages.indexnow.SubmissionError):
                pages.run(root, SITE, key_file, state_file=state,
                          sender=reject, clock=lambda: NOW)
            self.assertFalse(state.exists())

    def test_workflow_runs_daily_after_incremental_and_saves_state(self):
        # Plain-text checks: the runner's system python may lack PyYAML.
        path = HERE.parents[1] / ".github" / "workflows" / "indexnow-daily.yml"
        text = path.read_text(encoding="utf-8")
        incremental = text.index("- name: Submit changed public URLs to IndexNow")
        daily = text.index("- name: Submit every App homepage (once per UTC day)")
        save = text.index("- name: Save durable IndexNow state")
        self.assertLess(incremental, daily)
        self.assertLess(daily, save)
        step = text[daily:text.index("- name:", daily + 1)]
        self.assertIn("continue-on-error: true", step)
        self.assertIn("test_indexnow_app_pages.py", step)
        self.assertIn("indexnow_app_pages.py", step)
        self.assertIn('--state-file ".indexnow-state/app-pages-daily.json"', step)
        self.assertIn('--incremental-receipt ".indexnow-state/accepted-receipt.json"', step)

if __name__ == "__main__":
    unittest.main()
