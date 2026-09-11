import copy
from email.message import Message
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest import mock
import urllib.parse
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import owned_app_feeds as feeds
import owned_feed_delivery as delivery

PRODUCTION_FIXTURE = Path(__file__).parent / "fixtures/owned_feed_production_kn_IN.json"
KANNADA_SUMMARY = "Lumi ಕರಡಿಯೊಂದಿಗೆ ಗಣಿತದ ಲೋಕವನ್ನು ಅನ್ವೇಷಿಸಿ."


class OwnedAppFeedsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(__file__).resolve().parents[2] / ".growth-runtime" / "owned-feed-tests"
        cls.workspace.mkdir(parents=True, exist_ok=True)
        cls.template = cls.workspace / str(uuid.uuid4())
        cls.template.mkdir()
        cls.roster = feeds.canonical_manifest()["apps"]
        cls.copies = feeds._copy(feeds.HERE)
        (cls.template / "index.html").write_text(
            '<html lang="en"><head><title>Index</title></head><body>Original</body></html>',
            encoding="utf-8",
        )
        (cls.template / "sitemap.xml").write_text(
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://example.invalid/existing.xml</loc></sitemap>'
            '</sitemapindex>', encoding="utf-8",
        )
        for locale in feeds.OFFICIAL_LOCALES:
            (cls.template / locale).mkdir()
            (cls.template / locale / "index.html").write_text(
                f'<html lang="{locale}"><head><title>{locale}</title></head>'
                '<body>Original directory content</body></html>', encoding="utf-8",
            )
            page = cls.template / locale / "index.html"
            existing_links = "".join(
                f'<link rel="alternate" type="{media}" href="{feeds.SITE}/{filename}">'
                for filename, media in feeds.FORMATS.values()
            )
            page.write_text(page.read_text().replace("</head>", existing_links + "</head>"),
                            encoding="utf-8")
            records = []
            for key, app in cls.roster.items():
                records.append({
                    "key": key, "app_store_id": app["app_id"], "name": app["name"],
                    "summary": cls.copies[locale]["disclosure"] + " " + locale + " " + app["name"],
                    "purchase_model": feeds.APPS[key]["purchase_model"],
                    "one_time_option": True,
                    "app_store_url": (
                        f"https://apps.apple.com/us/app/id{app['app_id']}"
                        "?pt=118326163&ct=geo_pick&mt=8"
                    ),
                    "guide_url": f"{feeds.SITE}/{locale}/{key}.html",
                })
            feeds.write_if_changed(
                cls.template / feeds.CATALOG / "locales" / f"{locale}.json",
                feeds.json_bytes({"locale": locale, "record_count": len(records), "apps": records}),
            )
            feeds.write_if_changed(
                cls.template / feeds.CATALOG / "feeds" / f"{locale}.json",
                feeds.json_bytes({"language": locale, "title": locale + " · Lumi Studio"}),
            )
        feeds.build(cls.template, now="2026-09-01T00:00:00Z")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.template)
        if not any(cls.workspace.iterdir()):
            cls.workspace.rmdir()

    def setUp(self):
        self.root = self.workspace / str(uuid.uuid4())
        shutil.copytree(self.template, self.root)
        self.addCleanup(shutil.rmtree, self.root)

    def source(self, locale="fr-FR"):
        return self.root / feeds.CATALOG / "locales" / f"{locale}.json"

    def change_source(self, callback, locale="fr-FR"):
        path = self.source(locale)
        data = feeds.read_json(path)
        callback(data)
        path.write_bytes(feeds.json_bytes(data))

    def test_exact_47_by_50_and_three_formats(self):
        result = feeds.build(self.root, check=True, now="2026-09-02T00:00:00Z")
        self.assertEqual((47, 50, 2350, 150, 0), (
            result["apps"], result["locales"], result["app_locale_pairs"],
            result["feeds"], result["changed_files"],
        ))
        self.assertEqual({"paid_upfront": 13, "free_with_lifetime_unlock": 34},
                         result["purchase_models"])
        ids = []
        for locale in feeds.OFFICIAL_LOCALES:
            data = feeds.read_json(self.root / feeds.relative(locale, "json_feed"))
            ids.extend(i["id"] for i in data["items"])
            self.assertEqual(locale, data["language"])
            for item in data["items"]:
                self.assertEqual(locale, item["language"])
                facts = item["_owned_app"]
                self.assertEqual(
                    facts["purchase_model"] == "free_with_lifetime_unlock",
                    facts["free_core_available"],
                )
                self.assertIn(facts["publisher_disclosure"], item["content_text"])
                self.assertIn(item["external_url"], item["content_text"])
        self.assertEqual(2350, len(set(ids)))

    def test_noop_regeneration_preserves_bytes_dates_and_mtimes(self):
        index = feeds.read_json(self.root / feeds.INDEX)
        paths = [self.root / feeds.INDEX, self.root / feeds.SITEMAP,
                 self.root / feeds.DIRECTORY, self.root / "index.html"]
        paths += [self.root / feeds.relative(locale, fmt)
                  for locale in feeds.OFFICIAL_LOCALES for fmt in feeds.FORMATS]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        result = feeds.build(self.root, now="2026-09-10T00:00:00Z")
        self.assertEqual(0, result["changed_files"])
        self.assertEqual(index["generation_digest"], result["generation_digest"])
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})

    def test_single_source_change_only_revises_one_item_and_one_locale(self):
        before = {loc: feeds.read_json(self.root / feeds.relative(loc, "json_feed"))
                  for loc in feeds.OFFICIAL_LOCALES}
        self.change_source(lambda c: c["apps"][0].update(summary="Une nouvelle description complète."))
        feeds.build(self.root, now="2026-09-02T00:00:00Z")
        after = {loc: feeds.read_json(self.root / feeds.relative(loc, "json_feed"))
                 for loc in feeds.OFFICIAL_LOCALES}
        self.assertEqual(["fr-FR"], [loc for loc in before if before[loc] != after[loc]])
        changed = [(a, b) for a, b in zip(before["fr-FR"]["items"], after["fr-FR"]["items"])
                   if a != b]
        self.assertEqual(1, len(changed))
        old, new = changed[0]
        self.assertEqual(old["id"], new["id"])
        self.assertEqual(old["date_published"], new["date_published"])
        self.assertEqual("2026-09-02T00:00:00Z", new["date_modified"])

    def test_source_reordering_and_evidence_timestamps_do_not_republish(self):
        def mutate(catalog):
            catalog["apps"].reverse()
            catalog["date_modified"] = "2099-01-01"
            catalog["content_digest"] = "different snapshot"
            for app in catalog["apps"]:
                app["storefront_facts"] = {"price": "999", "currency": "USD"}
        self.change_source(mutate)
        self.assertEqual(0, feeds.build(self.root, now="2026-09-10T00:00:00Z")["changed_files"])

    def test_source_and_format_drift_are_blocking_without_writes(self):
        self.change_source(lambda c: c["apps"][0].update(summary="Description mise à jour."))
        before = (self.root / feeds.INDEX).read_bytes()
        with self.assertRaisesRegex(feeds.FeedError, "contract drift"):
            feeds.build(self.root, check=True, now="2026-09-02T00:00:00Z")
        self.assertEqual(before, (self.root / feeds.INDEX).read_bytes())

    def test_missing_extra_and_duplicate_sources_are_rejected(self):
        path = self.source()
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "50 official locales"):
            feeds.build(self.root)
        path.write_bytes(original)
        extra = self.source("en")
        extra.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "50 official locales"):
            feeds.build(self.root)
        extra.unlink()
        self.change_source(lambda c: c["apps"].__setitem__(0, copy.deepcopy(c["apps"][1])))
        with self.assertRaisesRegex(feeds.FeedError, "Duplicate"):
            feeds.build(self.root)

    def test_duplicate_json_fields_are_rejected(self):
        self.source().write_text('{"locale":"fr-FR","locale":"en-US"}', encoding="utf-8")
        with self.assertRaisesRegex(feeds.FeedError, "Duplicate JSON field"):
            feeds.build(self.root)

    def test_root_english_cannot_stand_in_for_a_locale(self):
        self.change_source(lambda c: c.update(locale="en"))
        with self.assertRaisesRegex(feeds.FeedError, "Locale/catalog"):
            feeds.build(self.root)

    def test_english_body_fallback_is_rejected(self):
        english = feeds.read_json(self.source("en-US"))["apps"][0]["summary"]
        self.change_source(lambda c: c["apps"][0].update(summary=english))
        with self.assertRaisesRegex(feeds.FeedError, "English summary fallback"):
            feeds.build(self.root)

    def test_purchase_contract_cannot_swap_paid_and_free_apps(self):
        def mutate(catalog):
            paid = next(a for a in catalog["apps"] if a["purchase_model"] == "paid_upfront")
            free = next(a for a in catalog["apps"] if a["purchase_model"] != "paid_upfront")
            paid["purchase_model"], free["purchase_model"] = free["purchase_model"], paid["purchase_model"]
        self.change_source(mutate)
        with self.assertRaisesRegex(feeds.FeedError, "purchase model drift"):
            feeds.build(self.root)

    def test_native_free_claim_on_paid_download_is_rejected(self):
        def mutate(catalog):
            paid = next(a for a in catalog["apps"] if a["purchase_model"] == "paid_upfront")
            paid["summary"] = "Cette application est gratuite."
        self.change_source(mutate)
        with self.assertRaisesRegex(feeds.FeedError, "Free claim on paid download"):
            feeds.build(self.root)

    def test_prices_and_invalid_apple_links_cannot_enter_feed(self):
        original = self.source().read_bytes()
        for mutation, expected in (
            ({"summary": "Achetez maintenant pour $4.99."}, "Literal price"),
            ({"app_store_url": "https://apps.apple.com.evil.invalid/app/id123"}, "App Store URL"),
            ({"guide_url": f"{feeds.SITE}/en-US/wrong.html"}, "Canonical locale"),
        ):
            with self.subTest(mutation=mutation):
                self.change_source(lambda c: c["apps"][0].update(mutation))
                with self.assertRaisesRegex(feeds.FeedError, expected):
                    feeds.build(self.root)
                self.source().write_bytes(original)

    def test_unicode_html_escaping_and_full_content_survive_all_formats(self):
        native = 'Lumi 照片、文字 & <隱私>：「一行」 — 👩🏽‍💻'
        self.change_source(lambda c: c["apps"][0].update(summary=native), "zh-Hant")
        feeds.build(self.root, now="2026-09-02T00:00:00Z")
        data = feeds.read_json(self.root / feeds.relative("zh-Hant", "json_feed"))
        item = next(i for i in data["items"] if i["summary"] == native)
        self.assertIn("&lt;隱私&gt;", item["content_html"])
        for fmt in ("atom", "rss"):
            ET.fromstring((self.root / feeds.relative("zh-Hant", fmt)).read_bytes())
        feeds.validate(self.root)

    def test_real_production_kannada_catalog_rejects_pollution_and_accepts_source_fix(self):
        catalog = feeds.read_json(PRODUCTION_FIXTURE)["catalog"]
        path = self.source("kn-IN")
        path.write_bytes(feeds.json_bytes(catalog))
        with self.assertRaisesRegex(feeds.FeedError, "Foreign script in kn-IN/lumimathpro"):
            feeds.load_sources(self.root)
        row = next(a for a in catalog["apps"] if a["key"] == "lumimathpro")
        row["summary"] = KANNADA_SUMMARY
        path.write_bytes(feeds.json_bytes(catalog))
        _, channels = feeds.load_sources(self.root)
        result = next(i for i in channels["kn-IN"]["items"]
                      if i["_owned_app"]["app_key"] == "lumimathpro")
        self.assertEqual(KANNADA_SUMMARY, result["summary"])
        self.assertEqual(47, len(channels["kn-IN"]["items"]))

    def test_catalog_changes_once_then_two_generations_and_notifications_are_noops(self):
        initial = delivery.inventory(self.root)
        baseline = {url: spec["sha256"] for url, spec in initial["topics"].items()}
        self.change_source(lambda c: c["apps"][0].update(summary="Une description vraiment nouvelle."))
        feeds.build(self.root, now="2026-09-02T00:00:00Z")
        materialized = {
            p.relative_to(self.root): p.read_bytes()
            for p in self.root.rglob("*") if p.is_file()
        }
        modified = {
            locale: [i["date_modified"] for i in feeds.read_json(
                self.root / feeds.relative(locale, "json_feed"))["items"]]
            for locale in feeds.OFFICIAL_LOCALES
        }
        state = self.root / ".outbox/state.json"
        source_sha = "a" * 40
        plan = delivery.prepare(self.root, state, source_sha, baseline=baseline)
        self.assertEqual(7, plan["pending_notifications"])

        def acknowledge(*, receipt_sink, topics=None, topic=None, **kwargs):
            fields = ([("hub.mode", "publish")] + [("hub.url", t) for t in topics]
                      if topics is not None else [("url", topic)])
            request = urllib.parse.urlencode(fields).encode("ascii")
            receipt_sink({
                "http_status": 200, "accepted_at": "2026-09-02T00:00:00Z",
                "request_sha256": hashlib.sha256(request).hexdigest(),
                "response_sha256": hashlib.sha256(b"accepted").hexdigest(),
            })

        with (
            mock.patch.object(delivery.notify_websub, "notify", side_effect=acknowledge) as web,
            mock.patch.object(delivery.notify_rsscloud, "ping", side_effect=acknowledge) as rss,
        ):
            opener = lambda req, timeout: self.response(req)
            for protocol in ("websub", "rsscloud"):
                self.assertEqual(0, delivery.deliver(
                    self.root, state, source_sha, protocol, opener=opener)["pending"])
            current = delivery.inventory(self.root)
            accepted = feeds.read_json(state)["accepted"]
            self.assertEqual(7, len(accepted))
            for receipt in accepted.values():
                self.assertEqual(source_sha, receipt["source_sha"])
                self.assertEqual(current["topics"][receipt["topic"]]["sha256"],
                                 receipt["content_sha256"])
            for day, new_sha in ((3, "b" * 40), (4, "c" * 40)):
                result = feeds.build(self.root, now=f"2026-09-{day:02d}T00:00:00Z")
                self.assertEqual(0, result["changed_files"])
                self.assertEqual(materialized, {
                    relative: (self.root / relative).read_bytes()
                    for relative in materialized
                })
                self.assertEqual(modified, {
                    locale: [i["date_modified"] for i in feeds.read_json(
                        self.root / feeds.relative(locale, "json_feed"))["items"]]
                    for locale in feeds.OFFICIAL_LOCALES
                })
                same = {url: spec["sha256"] for url, spec in current["topics"].items()}
                self.assertEqual(0, delivery.prepare(
                    self.root, state, new_sha, baseline=same)["pending_notifications"])
                for protocol in ("websub", "rsscloud"):
                    result = delivery.deliver(self.root, state, new_sha, protocol, opener=opener)
                    self.assertTrue(result["unchanged"])
                    self.assertEqual(0, result["accepted"])
            self.assertEqual(2, web.call_count)
            self.assertEqual(1, rss.call_count)

    def test_discovery_and_sitemap_are_idempotent_without_changing_buyer_pages(self):
        buyer = self.root / "fr-FR" / "wordmate.html"
        buyer.write_text("Do not change this buyer page.", encoding="utf-8")
        feeds.build(self.root)
        feeds.build(self.root)
        self.assertEqual("Do not change this buyer page.", buyer.read_text())
        root = (self.root / "index.html").read_text()
        self.assertEqual(1, root.count('data-owned-app-feeds="directory"'))
        self.assertIn("Original", root)
        for locale in feeds.OFFICIAL_LOCALES:
            page = (self.root / locale / "index.html").read_text()
            self.assertEqual(1, page.count(feeds.HEAD_START))
            self.assertIn("Original directory content", page)
            for fmt in feeds.FORMATS:
                self.assertIn(feeds.feed_url(locale, fmt), page)
        index = (self.root / "sitemap.xml").read_text()
        self.assertIn("https://example.invalid/existing.xml", index)
        self.assertEqual(1, index.count(str(feeds.SITEMAP)))

    def test_flat_sitemap_is_untouched_when_site_has_separate_sitemap_index(self):
        (self.root / "sitemap_index.xml").write_bytes((self.root / "sitemap.xml").read_bytes())
        flat = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        (self.root / "sitemap.xml").write_bytes(flat)
        feeds.build(self.root)
        self.assertEqual(flat, (self.root / "sitemap.xml").read_bytes())
        self.assertEqual(1, (self.root / "sitemap_index.xml").read_text().count(str(feeds.SITEMAP)))

    def test_every_locale_is_the_first_autodiscovery_choice_not_english_root(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.first = {}
            def handle_starttag(self, tag, attrs):
                data = dict(attrs)
                if tag == "link" and data.get("rel") == "alternate":
                    self.first.setdefault(data.get("type"), data.get("href"))
        for locale in feeds.OFFICIAL_LOCALES:
            parser = Links()
            page = (self.root / locale / "index.html").read_text()
            parser.feed(page)
            for fmt, (_, media) in feeds.FORMATS.items():
                self.assertEqual(feeds.feed_url(locale, fmt), parser.first[media])
            self.assertIn(f'href="{feeds.SITE}/rss.xml"', page)

    def test_old_end_of_head_discovery_block_is_migrated_once(self):
        path = self.root / "fr-FR/index.html"
        raw = path.read_text()
        pattern = re.escape(feeds.HEAD_START) + r".*?" + re.escape(feeds.HEAD_END)
        block = re.search(pattern, raw, re.S).group()
        moved = re.sub(pattern, "", raw, flags=re.S).replace("</head>", block + "</head>")
        path.write_text(moved, encoding="utf-8")
        self.assertEqual(1, feeds.build(self.root)["changed_files"])
        self.assertLess(path.read_text().index(feeds.feed_url("fr-FR", "rss")),
                        path.read_text().index(f'href="{feeds.SITE}/rss.xml"'))
        self.assertEqual(0, feeds.build(self.root)["changed_files"])

    def test_unowned_existing_feed_is_not_overwritten(self):
        path = self.root / feeds.relative("fr-FR", "json_feed")
        path.write_text('{"language":"fr-FR","items":[]}', encoding="utf-8")
        with self.assertRaisesRegex(feeds.FeedError, "unowned feed"):
            feeds.build(self.root)

    def test_damaged_old_feed_cannot_supply_a_forged_timestamp(self):
        path = self.root / feeds.relative("fr-FR", "json_feed")
        old = feeds.read_json(path)
        old["items"][0]["title"] = "Unbound mutation"
        path.write_bytes(feeds.json_bytes(old))
        with self.assertRaisesRegex(feeds.FeedError, "Previous item content digest"):
            feeds.build(self.root)

    def response(self, request, *, bad_type=False, bad_charset=False, bad_body=False):
        rel = request.full_url.removeprefix(feeds.SITE + "/")
        raw = (self.root / rel).read_bytes()
        headers = Message()
        content_type = "application/json" if rel.endswith(".json") else "application/xml"
        if bad_type:
            content_type = "text/html"
        headers["Content-Type"] = content_type + ("; charset=iso-8859-1" if bad_charset else "; charset=utf-8")
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers = headers
        response.read.return_value = b"wrong" if bad_body else raw
        return response

    def test_public_readback_accepts_real_pages_mime_and_utf8(self):
        opener = mock.Mock(side_effect=lambda req, timeout: self.response(req))
        result = feeds.verify_deployed(self.root, opener=opener)
        self.assertEqual({"verified_feeds": 150, "app_locale_pairs": 2350}, result)
        self.assertEqual(150, opener.call_count)
        self.assertTrue(all(c.args[0].get_method() == "GET" for c in opener.call_args_list))

    def test_public_readback_rejects_html_wrong_charset_and_stale_content(self):
        for kwargs in ({"bad_type": True}, {"bad_charset": True}, {"bad_body": True}):
            with self.subTest(kwargs=kwargs):
                opener = mock.Mock(side_effect=lambda req, timeout: self.response(req, **kwargs))
                with self.assertRaises(feeds.FeedError):
                    feeds.verify_deployed(self.root, opener=opener)

    def test_western_readback_only_resolves_actual_failed_cells(self):
        matrix = self.root / "western-cells.json"
        key = next(iter(self.roster))
        matrix.write_bytes(feeds.json_bytes([
            {"app": key, "locale": "fr-FR", "surface": "rss_owned", "status": "FAIL"},
            {"app": key, "locale": "en-US", "surface": "rss_owned", "status": "FAIL"},
            {"app": key, "locale": "fr-CA", "surface": "rss_owned", "status": "N/A"},
            {"app": key, "locale": "fr-FR", "surface": "geo_persona", "status": "FAIL"},
        ]))
        self.assertEqual({"baseline_rss_owned_failures": 2, "resolved": 2, "remaining": 0},
                         feeds.western_readback(self.root, matrix))


class ProductionCatalogScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = feeds.read_json(PRODUCTION_FIXTURE)
        cls.roster = feeds.canonical_manifest()["apps"]

    def test_fixture_is_real_47_record_production_catalog_not_synthetic_copy(self):
        catalog = self.fixture["catalog"]
        self.assertEqual("1ebc4bc2ae0ebe9b9103bf8eb76aba5548ee1ee4",
                         self.fixture["source_guide_commit"])
        self.assertEqual("api/v1/ios-app-catalog/locales/kn-IN.json",
                         self.fixture["source_path"])
        self.assertEqual(set(self.roster), {a["key"] for a in catalog["apps"]})
        failures = []
        for app in catalog["apps"]:
            try:
                feeds.require_locale_script(
                    app["summary"], "kn-IN", app["key"],
                    brands=(self.roster[app["key"]]["name"], app["name"]),
                )
            except feeds.FeedError:
                failures.append(app["key"])
        self.assertEqual(["lumimathpro"], failures)
        bad = next(a for a in catalog["apps"] if a["key"] == "lumimathpro")
        self.assertEqual("Lumi ಕರಡಿ与你一起探索数学的宇宙。", bad["summary"])

    def test_canonical_source_first_paragraph_is_native_kannada(self):
        source = feeds.read_json(feeds.HERE.parent / "data/math_pro_full.json")
        paragraph = source["kn-IN"]["description"].split("\n\n")[0]
        self.assertEqual(KANNADA_SUMMARY, paragraph)
        self.assertEqual(1.0, feeds.require_locale_script(paragraph, "kn-IN", "source"))

    def test_latin_brand_exception_does_not_exempt_english_body(self):
        value = "Lumi Math Pro ಗಣಿತ ಕಲಿಕೆ"
        with self.assertRaisesRegex(feeds.FeedError, "Native script ratio"):
            feeds.require_locale_script(value, "kn-IN", "brand")
        self.assertEqual(1.0, feeds.require_locale_script(
            value, "kn-IN", "brand", brands=("Lumi Math Pro",)))
        with self.assertRaisesRegex(feeds.FeedError, "Native script ratio"):
            feeds.require_locale_script(
                "Lumi Math Pro is the best way to explore fun mathematics ಗಣಿತ.",
                "kn-IN", "english body", brands=("Lumi Math Pro",))
        with self.assertRaisesRegex(feeds.FeedError, "Foreign script"):
            feeds.require_locale_script(
                value + " 数学", "kn-IN", "brand injection",
                brands=(value + " 数学",))

    def test_production_chinese_phonetics_and_japanese_scripts_are_native(self):
        for app in self.fixture["native_multi_script_examples"]:
            with self.subTest(locale=app["locale"], key=app["app_key"]):
                ratio = feeds.require_locale_script(
                    app["summary"], app["locale"], app["app_key"],
                    brands=(self.roster[app["app_key"]]["name"], app["name"]),
                )
                self.assertGreaterEqual(ratio, feeds.MIN_NATIVE_SCRIPT_RATIO)
        for value in ("ಗಣಿತ ಕಲಿಕೆ 中文", "ಗಣಿತ ಕಲಿಕೆ Ж", "ಗಣಿತ ಕಲಿಕೆ ㄅ"):
            with self.subTest(value=value), self.assertRaisesRegex(feeds.FeedError, "Foreign script"):
                feeds.require_locale_script(value, "kn-IN", "foreign")
        with self.assertRaisesRegex(feeds.FeedError, "Foreign script"):
            feeds.require_locale_script("French text 與", "fr-FR", "foreign")


if __name__ == "__main__":
    unittest.main()
