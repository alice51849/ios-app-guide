from __future__ import annotations

import base64
import copy
import html
import json
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import owned_search_gap_content as subject


class OwnedContentTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((GEO / "data/owned_search_gap_enrichment_v1.json").read_text())
        self.root = GEO / ".test-artifacts" / ("owned-content-" + uuid4().hex)
        self.root.mkdir(parents=True)
        self.queries = {}
        for item in self.plan["classifications"]:
            key, market, _, number = item["query_id"].split("-")
            self.queries[item["query_id"]] = {
                "id": item["query_id"], "app_key": key, "app_id": subject.APPS[key],
                "country": market, "term": "fixture query " + number, "high_intent": True,
                "group": "NON_BRAND", "visibility": "ABSENT_IN_SAMPLE", "fresh": True,
            }
        self.snapshot = {
            "metric": "PUBLIC_ITUNES_SEARCH_SAMPLE_ONLY", "queries": list(self.queries.values()),
            "recommendations": [{"evidence_query_id": key} for key in self.queries],
        }
        self.corpus = {
            "guide_commit": self.plan["guide_base"],
            "pages": [{"path": page["path"], "visible_text": "A previously published, unrelated fixture answer."}
                      for page in self.plan["pages"]],
        }
        self.proof = {"apps": {
            "aim990": {"app_id": subject.APPS["aim990"], "localized": {"en-US": {
                "result": "Practise offline with original TOEIC-style exercises.",
                "limitations": ["Original practice, not official"]}}},
            "cyca": {"app_id": subject.APPS["cyca"], "localized": {"en-US": {
                "result": "Forecasts are estimates, not contraception.",
                "free": "Start without creating an account"}}},
            "lumibopomofo": {"app_id": subject.APPS["lumibopomofo"], "localized": {"en-US": {
                "free": "Try the sound and tracing activities for ㄅ.",
                "limitations": ["not Latin-letter Hanyu Pinyin"]}}},
            "mochi": {"app_id": subject.APPS["mochi"], "localized": {"en-US": {
                "free": "Checklists and Home Screen check-offs are free.",
                "paid": "Premium skins are optional"}}},
        }}
        raw = subject.canonical(self.proof)
        self.plan["product_source"]["sha256"] = subject.sha(raw)
        self.git = mock.patch.object(subject, "git", return_value=raw)
        self.git.start()

    def tearDown(self):
        self.git.stop()
        shutil.rmtree(self.root)

    def fixture(self, page):
        page = copy.deepcopy(page)
        canonical = "https://open.cait518.cc/ios-app-guide/" + page["path"]
        store = f"https://apps.apple.com/app/id{page['app_id']}?pt=118326163&ct=geo_ask&mt=8"
        text = (f'<html lang="{page["locale"]}"><head><title>Existing title</title>'
                f'<meta name="description" content="Original metadata"><link rel="canonical" href="{canonical}">'
                '<script type="application/ld+json">{"@type":"Article","headline":"Unchanged"}</script></head>'
                '<body><main><section><h2>Existing useful answer</h2><p>Keep this existing paragraph intact.</p></section>'
                f'<section class="card"><h2>{page["before_heading"]}</h2><p>Existing FAQ stays.</p></section>'
                f'<a href="{store}">App Store</a><a href="/ios-app-guide/guides/existing.html">Existing link</a>'
                '<img class="app-store-qr-card__image" src="/ios-app-guide/assets/existing.svg" width="164" height="164">'
                '</main></body></html>')
        raw = text.encode()
        page["base_sha256"] = subject.sha(raw)
        return page, raw

    def test_all_19_gaps_classified_and_only_six_selected_for_five_existing_pages(self):
        subject.validate_plan(self.plan, self.snapshot, self.corpus, GEO.parent)
        counts = {label: sum(item["classification"] == label for item in self.plan["classifications"]) for label in subject.CLASSES}
        self.assertEqual({"OWNED_CONTENT_MATCH": 6, "ASC_ONLY_NOT_ACTIONABLE": 13, "NO_PRODUCT_FIT": 0}, counts)
        self.assertEqual(5, len(self.plan["pages"]))
        self.assertEqual(6, sum(item["selected"] for item in self.plan["classifications"]))
        selected = {item["query_id"] for item in self.plan["classifications"] if item["selected"]}
        self.assertTrue({"aim990-JP-intent-1", "aim990-JP-intent-2"} <= selected)

    def test_every_unselected_gap_is_brief_only(self):
        for item in self.plan["classifications"]:
            if not item["selected"]:
                self.assertNotIn("page", item)
                self.assertGreater(len(item["brief"]), 25)

    def test_cannot_select_asc_only_or_more_than_eight_queries(self):
        self.plan["classifications"][3].update(selected=True, page=self.plan["pages"][1]["path"])
        with self.assertRaises(ValueError):
            subject.validate_plan(self.plan, self.snapshot, self.corpus, GEO.parent)

    def test_brand_or_stale_or_visible_sample_never_creates_an_owned_gap(self):
        for field, value in (("group", "BRAND_CONTROL"), ("fresh", False), ("visibility", "VISIBLE")):
            snapshot = copy.deepcopy(self.snapshot)
            snapshot["queries"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                subject.validate_plan(self.plan, snapshot, self.corpus, GEO.parent)

    def test_unknown_product_id_fails_before_rendering(self):
        self.plan["pages"][0]["app_id"] = "1234567890"
        with self.assertRaisesRegex(ValueError, "intended App ID"):
            subject.validate_plan(self.plan, self.snapshot, self.corpus, GEO.parent)

    def test_feature_claim_requires_exact_committed_proof(self):
        self.proof["apps"]["mochi"]["localized"]["en-US"]["free"] = "Widget completion is paid."
        raw = subject.canonical(self.proof)
        self.plan["product_source"]["sha256"] = subject.sha(raw)
        with mock.patch.object(subject, "git", return_value=raw), self.assertRaisesRegex(ValueError, "material feature"):
            subject.validate_plan(self.plan, self.snapshot, self.corpus, GEO.parent)

    def test_page_source_and_signal_digests_cannot_be_swapped(self):
        path = self.root / "source.json"
        path.write_text('{"real":true}')
        with self.assertRaisesRegex(ValueError, "digest"):
            subject.pinned(path, "0" * 64)
        self.plan["guide_base"] = "main"
        with self.assertRaisesRegex(ValueError, "immutable"):
            subject.validate_plan(self.plan, self.snapshot, self.corpus, GEO.parent)

    def test_four_native_scripts_have_substantive_faqs_and_disclosure(self):
        for page in self.plan["pages"]:
            with self.subTest(locale=page["locale"], app=page["app_key"]):
                subject.validate_copy(page, self.queries)
                self.assertEqual(3, len(page["faqs"]))
                self.assertIn("Lumi Studio", page["disclosure"])

    def test_translated_placeholder_wrong_script_is_blocked(self):
        page = copy.deepcopy(self.plan["pages"][0])
        page["paragraphs"] = ["English only content " + str(i) for i in range(3)]
        page["faqs"] = [{"q": "Question " + str(i), "a": "Answer " + str(i)} for i in range(3)]
        page["heading"] = "English heading"
        page["disclosure"] = "Lumi Studio"
        page["limitations"] = "English limitation"
        with self.assertRaisesRegex(ValueError, "Japanese"):
            subject.validate_copy(page, self.queries)

    def test_fixed_prices_ratings_and_rank_claims_are_blocked(self):
        for claim in ("Only $4.99", "5 stars", "#1 in Japan", "guaranteed score", "保證排名"):
            page = copy.deepcopy(self.plan["pages"][1])
            page["paragraphs"][0] = claim
            with self.subTest(claim=claim), self.assertRaisesRegex(ValueError, "Fixed prices"):
                subject.validate_copy(page, self.queries)

    def test_keyword_stuffing_is_not_information_gain(self):
        page = copy.deepcopy(self.plan["pages"][1])
        query = self.queries[page["query_ids"][0]]["term"]
        page["paragraphs"][0] += " " + " ".join([query] * 3)
        with self.assertRaisesRegex(ValueError, "stuffing"):
            subject.validate_copy(page, self.queries)

    def test_no_new_links_or_html_in_editorial_copy(self):
        for text in ("Read https://example.invalid", "<a href='x'>new link</a>"):
            page = copy.deepcopy(self.plan["pages"][1])
            page["paragraphs"][0] += text
            with self.assertRaisesRegex(ValueError, "text only"):
                subject.validate_copy(page, self.queries)

    def test_existing_duplicate_content_is_rejected(self):
        page = self.plan["pages"][1]
        corpus = copy.deepcopy(self.corpus)
        corpus["pages"].append({"path": "answers/other-existing.html", "visible_text": page["paragraphs"][0]})
        with self.assertRaisesRegex(ValueError, "duplicated"):
            subject.block(page, self.queries, corpus)

    def test_all_target_pages_preserve_head_canonical_links_and_app_id(self):
        for entry in self.plan["pages"]:
            page, raw = self.fixture(entry)
            updated, metrics = subject.render(raw, page, self.queries, self.corpus)
            self.assertTrue(metrics["head_byte_identical"])
            self.assertGreater(metrics["shingle_novelty_fraction"], 0.35)
            before, after = subject.Page(raw.decode()), subject.Page(updated.decode())
            self.assertEqual(before.canonicals, after.canonicals)
            self.assertEqual(before.language, after.language)
            self.assertEqual(len(before.links), len(after.links))
            stores = [url for url in after.links if "apps.apple.com" in url]
            self.assertEqual(1, len(stores))
            parsed = urlsplit(stores[0])
            self.assertEqual(f'/{page["country"]}/app/id{page["app_id"]}', parsed.path)
            self.assertEqual({"pt": ["118326163"], "ct": ["geo_ask"], "mt": ["8"]}, parse_qs(parsed.query))
            self.assertIn(b"Keep this existing paragraph intact.", updated)
            self.assertIn(b"Existing FAQ stays.", updated)
            self.assertEqual(1, updated.count(subject.MARKER.encode()))

    def test_qr_and_cta_match_without_a_new_asset_url(self):
        page, raw = self.fixture(self.plan["pages"][0])
        updated, metrics = subject.render(raw, page, self.queries, self.corpus)
        match = re.search(rb'src="data:image/svg\+xml;base64,([^"]+)"', updated)
        self.assertIsNotNone(match)
        svg = ET.fromstring(base64.b64decode(match.group(1)))
        desc = svg.find("{http://www.w3.org/2000/svg}desc")
        self.assertEqual(metrics["qr_payload"], desc.text)
        self.assertEqual("jp", urlsplit(desc.text).path.split("/")[1])
        self.assertNotIn(b"/assets/app-store-qr/id", updated)

    def test_wrong_existing_cta_attribution_fails_instead_of_being_replaced(self):
        page, raw = self.fixture(self.plan["pages"][1])
        raw = raw.replace(b"pt=118326163", b"pt=999")
        page["base_sha256"] = subject.sha(raw)
        with self.assertRaisesRegex(ValueError, "attribution"):
            subject.render(raw, page, self.queries, self.corpus)

    def test_wrong_canonical_or_preimage_cannot_create_a_new_url(self):
        page, raw = self.fixture(self.plan["pages"][1])
        with self.assertRaisesRegex(ValueError, "baseline"):
            subject.render(raw + b"drift", page, self.queries, self.corpus)
        raw = raw.replace(page["path"].encode(), b"new-unreviewed-route.html")
        page["base_sha256"] = subject.sha(raw)
        with self.assertRaisesRegex(ValueError, "canonical"):
            subject.render(raw, page, self.queries, self.corpus)

    def test_render_is_deterministic_and_does_not_duplicate_the_section(self):
        page, raw = self.fixture(self.plan["pages"][1])
        first, _ = subject.render(raw, page, self.queries, self.corpus)
        second, _ = subject.render(raw, page, self.queries, self.corpus)
        self.assertEqual(first, second)
        page["base_sha256"] = subject.sha(first)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            subject.render(first, page, self.queries, self.corpus)

    def test_apply_refuses_wip_and_rolls_back_only_own_changes(self):
        one, two = self.root / "one.html", self.root / "two.html"
        one.write_bytes(b"before-one")
        two.write_bytes(b"before-two")
        changes = [(one, b"before-one", b"after-one"), (two, b"before-two", b"after-two")]
        actual = subject.atomic
        def fail_second(path, raw):
            if path == two and raw == b"after-two":
                raise OSError("synthetic write error")
            actual(path, raw)
        with mock.patch.object(subject, "atomic", side_effect=fail_second), self.assertRaises(OSError):
            subject.apply_changes(changes)
        self.assertEqual(b"before-one", one.read_bytes())
        self.assertEqual(b"before-two", two.read_bytes())
        two.write_bytes(b"someone else's WIP")
        with self.assertRaisesRegex(ValueError, "WIP"):
            subject.apply_changes(changes)
        self.assertEqual(b"before-one", one.read_bytes())
        self.assertEqual(b"someone else's WIP", two.read_bytes())

    def test_path_traversal_and_outside_urls_are_not_target_pages(self):
        for path in ("../App/metadata.json", "/Users/other/file", "foo\\bar"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                subject.safe_path(path)


if __name__ == "__main__":
    unittest.main()
