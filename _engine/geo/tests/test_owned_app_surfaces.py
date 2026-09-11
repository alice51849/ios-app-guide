from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import io
from pathlib import Path
import shutil
import sys
import tarfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "geo"))
import owned_app_surfaces as owned
import owned_app_surfaces_deploy as deploy

SITE = "https://example.com/guide"
NATIVE = {
    "cs": "Uspořádejte si každodenní úkoly a přehledně sledujte své poznámky.",
    "hu": "Rendezze mindennapi feladatait, és tartsa áttekinthetően a jegyzeteit.",
    "pl": "Uporządkuj codzienne zadania i wygodnie przeglądaj swoje notatki.",
    "ro": "Organizează sarcinile zilnice și păstrează notițele la îndemână.",
    "ru": "Упорядочивайте повседневные задачи и просматривайте свои заметки.",
    "sk": "Usporiadajte si každodenné úlohy a prehľadne sledujte svoje poznámky.",
    "sl-SI": "Uredite vsakodnevne naloge in imejte svoje zapiske vedno pri roki.",
    "tr": "Günlük görevlerinizi düzenleyin ve notlarınızı kolayca takip edin.",
    "uk": "Упорядковуйте щоденні завдання та зручно переглядайте свої нотатки.",
    "he": "אפשר לארגן את המשימות היומיות ולעיין בהערות בצורה נוחה וברורה.",
}
ENGLISH = "Organize your everyday tasks and keep track of all your notes."


class PureChecks(unittest.TestCase):
    def test_exact_and_embedded_english_fallback(self):
        self.assertIn("english_fallback", owned.text_issues(ENGLISH, ENGLISH, "cs"))
        mixed = NATIVE["cs"] + " " + ENGLISH
        self.assertIn("english_sentence_leak", owned.text_issues(mixed, ENGLISH, "cs"))

    def test_identity_words_do_not_hide_sentence_leak(self):
        text = "My App " + ENGLISH
        self.assertIn("english_fallback", owned.text_issues(text, text, "cs", ("My App", "")))

    def test_hebrew_script_and_proof_are_independent(self):
        self.assertIn("missing_native_script", owned.text_issues(ENGLISH, "", "he"))
        self.assertEqual(owned.text_issues(NATIVE["he"], ENGLISH, "he"), [])
        self.assertIn("unsupported_outcome_claim", owned.text_issues("תוכל להשיג את המטרה שלך תוך 30 ימים", "", "he"))

    def test_third_party_and_traversal_do_not_count(self):
        for url in (
            "https://dev.to/author/guide",
            "https://example.com.evil.invalid/guide/cs/app.html",
            f"{SITE}/%2e%2e/other.json",
            f"{SITE}/cs/../other.json",
            f"{SITE}/cs/app.html?locale=he",
            f"{SITE}/cs/app.html#fake-locale",
        ):
            with self.subTest(url=url), self.assertRaises(owned.SurfaceError):
                owned._url_path(url, SITE)

    def test_hebrew_page_has_real_rtl_not_only_language(self):
        page = owned.Page('<html lang="he"><script>English ignored</script><p>שלום</p></html>')
        self.assertEqual(page.direction, "")
        self.assertNotIn("English ignored", page.text)

    def test_wrong_storefront_and_missing_attribution_fail(self):
        record = {"app_store_url": "https://apps.apple.com/us/app/id123?ct=test"}
        self.assertEqual(
            owned._store_issues(record, "123", "he"),
            ["wrong_app_store_identity_or_market", "missing_campaign_attribution"],
        )

    def test_only_known_cloudflare_email_rewrites_are_normalized(self):
        address = "hourstag.app@gmail.com"
        encoded = bytes([42, *(ord(char) ^ 42 for char in address)]).hex()
        original = f'<a href="mailto:{address}">{address}</a></body>'.encode()
        public = (
            f'<a href="/cdn-cgi/l/email-protection#{encoded}">'
            f'<span class="__cf_email__" data-cfemail="{encoded}">[email&#160;protected]</span></a>'
            '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script></body>'
        ).encode()
        self.assertEqual(owned.normalize_public_html(public), original)
        self.assertNotEqual(owned.normalize_public_html(public + b"<p>unrelated edit</p>"), original)
        for skill in ("lumi-app-finder@v1.3.0", "skills@1.5.19"):
            encoded_skill = bytes([42, *(ord(char) ^ 42 for char in skill)]).hex()
            public_skill = (
                f'<a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="{encoded_skill}">'
                "[email&#160;protected]</a>"
            ).encode()
            self.assertEqual(owned.normalize_public_html(public_skill), skill.encode())

    def test_failed_post_deploy_run_cannot_be_skipped_for_an_older_success(self):
        deployments = [{"id": 3}, {"id": 2}, {"id": 1}]
        histories = {
            3: [{"state": "in_progress", "log_url": "https://github.com/owner/site/actions/runs/300/job/3"}],
            2: [{"state": "failure", "log_url": "https://github.com/owner/site/actions/runs/200/job/2"}],
            1: [{"state": "success", "log_url": "https://github.com/owner/site/actions/runs/100/job/1"}],
        }
        with self.assertRaisesRegex(owned.SurfaceError, "may already be live"):
            deploy.current_baseline(deployments, histories.get, repository="owner/site", expected_run="100", current_run="300")
        histories[2][0]["state"] = "success"
        with self.assertRaisesRegex(owned.SurfaceError, "baseline changed"):
            deploy.current_baseline(deployments, histories.get, repository="owner/site", expected_run="100", current_run="300")
        self.assertEqual(
            deploy.current_baseline(deployments, histories.get, repository="owner/site", expected_run="200", current_run="300"), 2,
        )


class DiscoveryChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / ".local" / f"owned-test-{uuid.uuid4().hex}"
        cls.directory.mkdir(parents=True)
        cls.keys = [f"app{index:02}" for index in range(47)]
        apps = {
            key: {"app_id": str(10000 + index), "name": f"Product {index}"}
            for index, key in enumerate(cls.keys)
        }
        cls.roster = {
            "schema": "lumi.live-app-roster/v1", "version": 1, "revision": 1,
            "apps": apps, "roster_digest": owned.roster_digest(apps),
        }
        cls.finder = {
            "apps": [
                {"key": key, "app_store_id": app["app_id"],
                 "purchase_model": "paid_upfront", "one_time_option": True}
                for key, app in apps.items()
            ],
        }
        records = []
        sitemap = []
        for locale in owned.OFFICIAL_LOCALES:
            text = NATIVE.get(locale, ENGLISH)
            for key, app in apps.items():
                records.append({
                    "locale": locale, "app_key": key, "app_name": app["name"],
                    "app_store_id": app["app_id"], "verified_live": True,
                    "publisher_query": text, "decision_context": text,
                    "publisher_disclosure": text, "app_store_cta_label": text,
                    "is_ranking": False, "measured_search_volume": False,
                    "query_origin": "publisher_authored_editorially_localized",
                    "purchase_model": "paid_upfront", "one_time_option": True,
                    "app_store_url": f"https://apps.apple.com/{owned.COUNTRIES.get(locale, 'us')}/app/id{app['app_id']}?pt=123&ct=test",
                    "canonical_guide_url": f"{SITE}/{locale}/{key}.html",
                })
            if locale not in (*owned.LOCALES, "en-US"):
                continue
            api = {
                "locale": locale, "record_count": 47, "apps": [
                    {
                        "key": key, "name": app["name"], "app_store_id": app["app_id"],
                        "summary": text, "verified_live": True,
                        "purchase_model": "paid_upfront", "one_time_option": True,
                        "app_store_url": f"https://apps.apple.com/{owned.COUNTRIES.get(locale, 'us')}/app/id{app['app_id']}?pt=123&ct=test",
                        "guide_url": f"{SITE}/{locale}/{key}.html",
                        "storefront_facts": {"price": "4.99", "currency": "EUR"},
                    }
                    for key, app in apps.items()
                ],
            }
            owned.write_json(cls.directory / owned.API / f"{locale}.json", api)
            for key in apps:
                path = cls.directory / locale / f"{key}.html"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'<html lang="{locale}"><p>{text}</p></html>', encoding="utf-8")
                sitemap.append(f"{SITE}/{locale}/{key}.html")
            if locale in owned.LOCALES:
                relative = f"{locale}/{owned.CATALOG_PAGE}"
                path = cls.directory / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                alternates = "".join(
                    f'<link rel="alternate" hreflang="{other}" href="{SITE}/{other}/{owned.CATALOG_PAGE}">'
                    for other in owned.LOCALES
                )
                rtl = ' dir="rtl"' if locale == "he" else ""
                path.write_text(
                    f'<html lang="{locale}"{rtl}><head><link rel="canonical" href="{SITE}/{relative}">'
                    f'{alternates}</head><body><p>{text}</p>'
                    f'<a href="{SITE}/{owned.CATALOG}">JSON</a>'
                    + "".join(f'<a href="{SITE}/{locale}/{key}.html">{key}</a>' for key in apps)
                    + "</body></html>",
                    encoding="utf-8",
                )
                sitemap.append(f"{SITE}/{relative}")
        owned.write_json(cls.directory / owned.CATALOG, {
            "app_count": 47, "locale_count": 50, "record_count": 2350,
            "publisher_disclosure": "First-party publisher catalog.",
            "is_ranking": False, "measured_search_volume": False,
            "records": records,
        })
        owned.write_json(cls.directory / owned.FINDER, cls.finder)
        owned.write_json(cls.directory / "api/v1/ios-app-catalog/index.json", {
            "record_count": 47,
            "locales": [
                {"locale": locale, "url": f"{SITE}/{owned.API}/{locale}.json"}
                for locale in owned.OFFICIAL_LOCALES
            ],
        })
        cls.sitemap = (
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{url}</loc></url>" for url in sitemap)
            + "</urlset>"
        )
        (cls.directory / "sitemap.xml").write_text(cls.sitemap, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory)

    @contextmanager
    def replace_json(self, relative, transform):
        path = self.directory / relative
        original = path.read_bytes()
        value = json.loads(original)
        transform(value)
        owned.write_json(path, value)
        try:
            yield
        finally:
            path.write_bytes(original)

    def run_discovery(self, **kwargs):
        return owned.discover(self.directory, roster=self.roster, site=SITE, **kwargs)

    def test_470_existing_records_without_copies_or_fake_receipts(self):
        before = {p.relative_to(self.directory): p.read_bytes() for p in self.directory.rglob("*") if p.is_file()}
        result, packet = self.run_discovery()
        self.assertEqual(len(packet), 470)
        self.assertEqual(result["coverage"]["source_checks_passed"], 470)
        self.assertEqual(result["coverage"]["devto_eligible_cells"], 0)
        self.assertEqual(result["coverage"]["devto_na_cells"], 470)
        self.assertEqual(result["coverage"]["new_task_pages"], 0)
        self.assertEqual(result["coverage"]["new_native_catalogs"], 0)
        self.assertTrue(all(c["owned_native"] == "NOT_REVIEWED" for c in result["cells"]))
        self.assertTrue(all(c["owned_public_readback"] == "NOT_VERIFIED" for c in result["cells"]))
        after = {p.relative_to(self.directory): p.read_bytes() for p in self.directory.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result, self.run_discovery()[0])

    def test_duplicate_and_missing_roster_cells_fail_closed(self):
        for transform in (
            lambda value: value["apps"].pop(),
            lambda value: value["apps"].append(copy.deepcopy(value["apps"][0])),
        ):
            with self.replace_json(f"{owned.API}/cs.json", transform), self.assertRaises(owned.SurfaceError):
                self.run_discovery()

    def test_task_english_fallback_can_use_existing_native_api(self):
        def corrupt(value):
            next(r for r in value["records"] if r["locale"] == "cs")["decision_context"] = ENGLISH
        with self.replace_json(owned.CATALOG, corrupt):
            result, _ = self.run_discovery()
            cell = next(c for c in result["cells"] if c["locale"] == "cs" and c["app_key"] == self.keys[0])
            self.assertEqual(cell["selected_asset"]["kind"], "app_catalog_record")
            self.assertTrue(any("english_fallback" in issue for issue in cell["candidates"][0]["issues"]))

    def test_both_english_candidates_stay_blocked(self):
        def corrupt_task(value):
            next(r for r in value["records"] if r["locale"] == "cs")["decision_context"] = ENGLISH
        def corrupt_api(value):
            value["apps"][0]["summary"] = ENGLISH
        with self.replace_json(owned.CATALOG, corrupt_task), self.replace_json(f"{owned.API}/cs.json", corrupt_api):
            result, _ = self.run_discovery()
            self.assertEqual(result["coverage"]["source_checks_blocked"], 1)

    def test_paid_upfront_cannot_turn_into_a_free_download(self):
        def corrupt(value):
            value["apps"][0]["storefront_facts"]["price"] = "0"
        with self.replace_json(f"{owned.API}/cs.json", corrupt):
            result, _ = self.run_discovery()
            candidate = result["cells"][0]["candidates"][1]
            self.assertIn("apple_price_model_mismatch", candidate["issues"])

    def test_review_is_content_bound_not_presence_bound(self):
        result, packet = self.run_discovery()
        review = {
            "schema": "lumi.owned-native-review/v1", "model": owned.MODEL,
            "reasoning_effort": "max", "roster_digest": self.roster["roster_digest"],
            "packet_digest": owned.digest(packet), "reviewed_cells": 470,
            "verdict": "PASS", "findings": [],
        }
        self.assertEqual(self.run_discovery(review=review)[0]["coverage"]["native_reviewed_cells"], 470)
        for field, value in (("packet_digest", "stale"), ("model", "other"), ("reviewed_cells", 469)):
            stale = {**review, field: value}
            self.assertEqual(self.run_discovery(review=stale)[0]["coverage"]["native_reviewed_cells"], 0)

    def test_canonical_hreflang_and_rtl_are_blocking(self):
        relative = f"he/{owned.CATALOG_PAGE}"
        path = self.directory / relative
        original = path.read_text()
        for old, new in (
            ('dir="rtl"', 'dir="ltr"'),
            ('rel="canonical"', 'rel="alternate"'),
            ('hreflang="cs"', 'hreflang="en-US"'),
        ):
            try:
                path.write_text(original.replace(old, new), encoding="utf-8")
                result, _ = self.run_discovery()
                self.assertEqual(result["coverage"]["source_checks_blocked"], 47)
            finally:
                path.write_text(original, encoding="utf-8")

    def test_robots_advertised_sitemap_is_discovered(self):
        root = self.directory / "sitemap.xml"
        extra = self.directory / "sitemap_data.xml"
        robots = self.directory / "robots.txt"
        try:
            extra.write_text(self.sitemap, encoding="utf-8")
            root.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>', encoding="utf-8")
            robots.write_text(f"Sitemap: {SITE}/sitemap_data.xml\n", encoding="utf-8")
            self.assertEqual(self.run_discovery()[0]["coverage"]["source_checks_passed"], 470)
            robots.write_text("", encoding="utf-8")
            self.assertEqual(self.run_discovery()[0]["coverage"]["source_checks_blocked"], 470)
        finally:
            root.write_text(self.sitemap, encoding="utf-8")
            extra.unlink()
            robots.unlink()

    def test_audit_adapter_preserves_rss_social_and_geo(self):
        result, _ = self.run_discovery()
        original = {"rows": [
            {"app_key": cell["app_key"], "app_id": cell["app_id"], "locale": cell["locale"],
             "rss_native": "BLOCKED", "social_receipt": "BLOCKED", "geo_proof": "FAIL"}
            for cell in result["cells"]
        ]}
        after = owned.update_audit(original, result)
        for old, row in zip(original["rows"], after["rows"]):
            self.assertEqual({k: row[k] for k in old}, old)
            self.assertEqual(row["devto_applicability"], "N/A")
            self.assertEqual(row["owned_native"], "NOT_REVIEWED")
        self.assertNotIn("owned_discovery", original)

    def test_internal_api_links_are_not_inferred_from_file_presence(self):
        def corrupt(value):
            next(row for row in value["locales"] if row["locale"] == "he")["url"] = f"{SITE}/{owned.API}/en-US.json"
        with self.replace_json("api/v1/ios-app-catalog/index.json", corrupt):
            result, _ = self.run_discovery()
            cell = next(c for c in result["cells"] if c["locale"] == "he")
            self.assertIn("missing_internal_api_link", cell["candidates"][1]["issues"])

    def test_public_readback_is_digest_bound_and_never_calls_devto(self):
        discovery, _ = self.run_discovery()
        calls = []
        def fetch(url):
            calls.append(url)
            path = self.directory / owned._url_path(url, SITE)
            return {"http_status": 200, "body": path.read_bytes(), "final_url": url}
        result = owned.readback(discovery, fetch=fetch)
        self.assertEqual(result["verified_cells"], 470)
        self.assertTrue(all(url.startswith(SITE + "/") for url in calls))
        self.assertEqual(len(calls), len(discovery["source_sha256"]))
        self.assertEqual(result["devto_eligible_cells"], 0)
        def changed_html(url):
            value = fetch(url)
            if url.endswith(".html"):
                value["body"] += b'<script src="https://static.cloudflareinsights.com/beacon.min.js"></script>'
            return value
        separated = owned.readback(discovery, fetch=changed_html)
        self.assertEqual(separated["verified_cells"], 470)
        self.assertEqual(separated["verified_catalog_pages"], 0)
        self.assertTrue(all(row["catalog_page_public_readback"] == "BLOCKED" for row in separated["cells"]))
        def stale(url):
            value = fetch(url)
            if url.endswith(owned.CATALOG):
                value["body"] = b"stale body"
            return value
        self.assertEqual(owned.readback(discovery, fetch=stale)["verified_cells"], 0)

    def test_artifact_overlay_preserves_every_feed_and_other_owner_file(self):
        discovery, packet = self.run_discovery()
        review = {
            "schema": "lumi.owned-native-review/v1", "model": owned.MODEL,
            "reasoning_effort": "max", "roster_digest": self.roster["roster_digest"],
            "packet_digest": owned.digest(packet), "reviewed_cells": 470,
            "verdict": "PASS", "findings": [],
        }
        discovery = self.run_discovery(review=review)[0]
        scratch = self.directory / "overlay-fixture"
        scratch.mkdir()
        try:
            archive, manifest = scratch / "artifact.tar", scratch / "manifest.json"
            owned.write_json(manifest, discovery)
            protected = {
                "index.html": b"unchanged homepage",
                "robots.txt": b"unchanged robots",
                "rss.xml": b"RSS belongs to another owner",
                "api/v1/feeds/he.json": b"exact50 feed owner",
                "apps/decision.html": b"conversion owner",
            }
            with tarfile.open(archive, "w") as bundle:
                for name, body in protected.items():
                    item = tarfile.TarInfo(name)
                    item.size = len(body)
                    bundle.addfile(item, io.BytesIO(body))
                for source in sorted(self.directory.rglob("*")):
                    if source.is_file() and scratch not in source.parents:
                        bundle.add(source, arcname=source.relative_to(self.directory))
            output = scratch / "site"
            evidence = deploy.overlay(archive, manifest, output, roster=self.roster, site=SITE)
            self.assertEqual(evidence["added_files"], [owned.OUTPUT])
            self.assertEqual(evidence["updated_files"], [])
            self.assertEqual(evidence["removed_files"], [])
            for name, body in protected.items():
                self.assertEqual((output / name).read_bytes(), body)
            discovery["source_sha256"][owned.CATALOG] = "changed"
            owned.write_json(manifest, discovery)
            with self.assertRaisesRegex(owned.SurfaceError, "Deployed source changed"):
                deploy.overlay(archive, manifest, scratch / "stale-site", roster=self.roster, site=SITE)
            discovery["source_sha256"][owned.CATALOG] = hashlib.sha256(
                (self.directory / owned.CATALOG).read_bytes()
            ).hexdigest()
            owned.write_json(manifest, discovery)
            missing = f"cs/{self.keys[0]}.html"
            incomplete = scratch / "missing-task.tar"
            with tarfile.open(archive) as source, tarfile.open(incomplete, "w") as target:
                for member in source.getmembers():
                    if member.name != missing:
                        target.addfile(member, source.extractfile(member) if member.isfile() else None)
            with self.assertRaisesRegex(owned.SurfaceError, "sitemap/task-page discovery differs"):
                deploy.overlay(incomplete, manifest, scratch / "missing-site", roster=self.roster, site=SITE)
        finally:
            shutil.rmtree(scratch)

    def test_artifact_overlay_rejects_unreviewed_and_traversal_inputs(self):
        discovery, _ = self.run_discovery()
        scratch = self.directory / "unsafe-overlay-fixture"
        scratch.mkdir()
        try:
            manifest, archive = scratch / "manifest.json", scratch / "artifact.tar"
            owned.write_json(manifest, discovery)
            with self.assertRaisesRegex(owned.SurfaceError, "independently reviewed"):
                deploy.overlay(archive, manifest, scratch / "site")
            discovery["coverage"]["native_reviewed_cells"] = 470
            for cell in discovery["cells"]:
                cell["owned_native"] = "PASS_REVIEWED"
            owned.write_json(manifest, discovery)
            with tarfile.open(archive, "w") as bundle:
                item = tarfile.TarInfo("../escaped.txt")
                item.size = 1
                bundle.addfile(item, io.BytesIO(b"x"))
            with self.assertRaisesRegex(owned.SurfaceError, "Unsafe"):
                deploy.overlay(archive, manifest, scratch / "site")
            self.assertFalse((scratch / "escaped.txt").exists())
        finally:
            shutil.rmtree(scratch)


if __name__ == "__main__":
    unittest.main()
