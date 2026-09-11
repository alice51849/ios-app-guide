"""Targeted contract and actual HTTP GET tests; no App/ASC writes or live posting."""

from copy import deepcopy
import html
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
from threading import Thread
import unittest
from urllib.parse import parse_qsl, urlsplit
from urllib.request import urlopen


GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import conversion_route_contract as conversion  # noqa: E402
import high_intent_decision_routes as routes  # noqa: E402

IDS = {
    "mochi": "6785004775", "lumibopomofo": "6773017109", "scanto": "6779977651",
    "aim990": "6784974530", "lumiweather": "6779552704", "mochidonestamp": "6790800323",
    "cyca": "6782251621", "unblurry": "6782275018", "battai": "6802423998",
    "notesstudio100": "6798813048", "onepageppt": "6798814385",
}
PRICES = {
    "mochi": ("3.99", "120"), "lumibopomofo": ("8.99", "290"), "scanto": ("2.99", "90"),
    "aim990": ("5.99", "190"), "lumiweather": ("3.99", "120"), "mochidonestamp": ("3.99", "120"),
    "cyca": ("4.99", "150"), "unblurry": ("2.99", "90"), "battai": ("5.99", "190"),
    "notesstudio100": ("5.99", "190"), "onepageppt": ("5.99", "190"),
}


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.anchors, self.images, self.visible = [], [], [], []
        self.hidden = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"head", "script", "style"}:
            self.hidden += 1
        if tag == "link":
            self.links.append(attrs)
        elif tag == "a":
            self.anchors.append(attrs)
        elif tag == "img":
            self.images.append(attrs)

    def handle_endtag(self, tag):
        if tag in {"head", "script", "style"}:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.visible.append(data)


class ConversionRouteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        default_pages = GEO.parent.parent if GEO.parent.name == "_engine" else GEO / "pages"
        cls.pages = Path(os.environ.get("HIGH_INTENT_GUIDE_REPOSITORY", default_pages))
        cls.inventory = cls.pages / "data" / routes.INVENTORY_FILENAME
        cls.source = routes.load_route_source()
        cls.apps = routes.load_inventory(cls.inventory)
        cls.contracts = conversion.load_contracts()
        cls.raw_routes = {row["app_key"]: row for row in cls.source["routes"]}
        cls.records, cls.report = routes.build(inventory_path=cls.inventory, provider_token="118326163")
        cls.converted = [row for row in cls.records if row.get("conversion_contract")]
        cls.html = {row["route_id"]: routes.render_html(row) for row in cls.converted}

    def validate(self, key, contracts=None, raw=None, app=None):
        return conversion.validate(
            raw or self.raw_routes[key], app or self.apps[key], contracts or self.contracts,
        )

    def test_stable_ids_and_source_derived_native_routes(self):
        self.assertEqual(IDS, {key: row["app_id"] for key, row in self.contracts.items()})
        self.assertEqual(sum(len(row["localized"]) for row in self.contracts.values()), len(self.converted))
        self.assertEqual(47, len(self.source["routes"]))
        self.assertEqual(2350, self.report["coverage"]["candidate_app_locale_pairs"])
        self.assertEqual(0, self.report["coverage"]["fallback_records"])
        for key in IDS:
            self.assertEqual(IDS[key], self.apps[key]["app_store_id"])
            self.assertTrue(self.validate(key))

    def test_required_primary_and_secondary_locales(self):
        for key, locale in {"lumibopomofo": "zh-Hant", "aim990": "fr-FR", "lumiweather": "ja"}.items():
            self.assertEqual(locale, self.contracts[key]["primary_locale"])
            self.assertIn(locale, self.raw_routes[key]["locales"])
        for key in ("mochi", "mochidonestamp", "battai"):
            self.assertIn("zh-Hant", self.contracts[key]["localized"])
        self.assertIn("ja", self.contracts["unblurry"]["localized"])
        self.assertIn("zh-Hant", self.contracts["cyca"]["localized"])
        self.assertIn("de-DE", self.contracts["mochidonestamp"]["localized"])

    def test_existing_47_by_50_install_decision_baseline_is_intact(self):
        baseline = json.loads((self.pages / "data/app-install-decision-routes.json").read_text())
        self.assertEqual((47, 50, 2350), (
            baseline["app_count"], baseline["locale_count"], baseline["record_count"],
        ))
        self.assertEqual(2350, len(baseline["records"]))
        self.assertEqual(50, len(set(baseline["locales"])))

    def test_missing_reference_and_wrong_app_id_fail_closed(self):
        raw = deepcopy(self.raw_routes["mochi"])
        raw.pop("conversion_contract")
        with self.assertRaisesRegex(ValueError, "reference"):
            self.validate("mochi", raw=raw)
        changed = deepcopy(self.contracts)
        changed["aim990"]["app_id"] = "6792483140"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.validate("aim990", changed)

    def test_pending_aim_version_and_cross_version_proof_are_rejected(self):
        changed = deepcopy(self.contracts)
        changed["aim990"]["live_app_version"] = "1.4.3"
        with self.assertRaisesRegex(ValueError, "shipping 1.4.2"):
            self.validate("aim990", changed)
        changed = deepcopy(self.contracts)
        changed["mochi"]["proofs"][0]["live_app_version"] = "future"
        with self.assertRaisesRegex(ValueError, "cross-version"):
            self.validate("mochi", changed)

    def test_free_paid_overlap_and_model_drift_are_rejected(self):
        changed = deepcopy(self.contracts)
        changed["mochi"]["paid_feature_ids"].append("home_screen_checkoff")
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.validate("mochi", changed)
        app = deepcopy(self.apps["mochi"])
        app["purchase_model"] = "paid_upfront"
        with self.assertRaisesRegex(ValueError, "purchase model"):
            self.validate("mochi", app=app)

    def test_body_cannot_disagree_about_the_free_paid_boundary(self):
        raw = deepcopy(self.raw_routes["mochi"])
        raw["locales"]["en-US"]["decision_rule"] = "Home Screen widgets require Premium."
        with self.assertRaisesRegex(ValueError, "free/paid boundary disagree"):
            self.validate("mochi", raw=raw)

    def test_battai_unknown_scope_cannot_be_marked_verified(self):
        self.assertEqual("BLOCKED_EVIDENCE", self.contracts["battai"]["paid_scope_status"])
        self.assertEqual([], self.contracts["battai"]["paid_feature_ids"])
        changed = deepcopy(self.contracts)
        changed["battai"]["paid_scope_status"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "unverified paid scope"):
            self.validate("battai", changed)

    def test_blocked_proofs_cannot_support_published_claims(self):
        for key in ("lumibopomofo", "scanto", "aim990", "lumiweather", "battai", "notesstudio100", "onepageppt"):
            for field in ("published_claim_ids", "free_feature_ids", "paid_feature_ids"):
                for also_supported in (False, True):
                    with self.subTest(key=key, field=field, also_supported=also_supported):
                        changed = deepcopy(self.contracts)
                        blocked = next(p for p in changed[key]["proofs"] if p["status"] == "BLOCKED_EVIDENCE")
                        claim = blocked["claim_ids"][0]
                        if also_supported:
                            supported = next(p for p in changed[key]["proofs"] if p["status"] in conversion.VERIFIED)
                            supported["claim_ids"].append(claim)
                        changed[key][field].append(claim)
                        with self.assertRaisesRegex(ValueError, "BLOCKED_EVIDENCE"):
                            self.validate(key, changed)

    def test_unapproved_asset_host_and_unbound_thumbnail_are_rejected(self):
        changed = deepcopy(self.contracts)
        asset = next(p for p in changed["unblurry"]["proofs"] if p["asset"])
        asset["source_url"] = "https://example.com/invented-result.jpg"
        with self.assertRaisesRegex(ValueError, "approved public source"):
            self.validate("unblurry", changed)
        changed = deepcopy(self.contracts)
        asset = next(p for p in changed["unblurry"]["proofs"] if p["asset"])
        asset["asset"]["reviewed_thumbnail_sha256"] = "unknown"
        with self.assertRaisesRegex(ValueError, "thumbnail binding"):
            self.validate("unblurry", changed)
        changed = deepcopy(self.contracts)
        changed["mochi"]["proofs"][0]["source_url"] = "https://apps.apple.com/us/app/id6798814385"
        with self.assertRaisesRegex(ValueError, "same stable App"):
            self.validate("mochi", changed)

    def test_english_fallback_is_not_native_copy(self):
        for key, locale in (("aim990", "fr-FR"), ("lumiweather", "ja"), ("lumibopomofo", "zh-Hant")):
            changed = deepcopy(self.contracts)
            native = changed[key]["localized"][locale]
            english = changed[key]["localized"]["en-US"]
            for field in ("task", "result", "free", "paid", "proof_note", "limitations", "queries"):
                native[field] = deepcopy(english[field])
            native["asset_captions"] = {name: "Published example" for name in native["asset_captions"]}
            with self.subTest(locale=locale), self.assertRaisesRegex(ValueError, "fallback"):
                self.validate(key, changed)

    def test_missing_locale_does_not_silently_remove_primary(self):
        raw = deepcopy(self.raw_routes["aim990"])
        raw["locales"].pop("fr-FR")
        with self.assertRaisesRegex(ValueError, "native locale"):
            self.validate("aim990", raw=raw)

    def test_native_inventory_evidence_does_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, "fell back"):
            routes._evidence(self.apps["aim990"], "fr-FR", "summary.en")

    def test_no_global_price_or_invented_result_claim(self):
        for key, bad in (("mochi", "Unlock everything for $4.99."),
                         ("cyca", "Clinical accuracy for guaranteed fertile days."),
                         ("unblurry", "Rescue every photo."),
                         ("battai", "Read battery temperature and repair your battery.")):
            changed = deepcopy(self.contracts)
            changed[key]["localized"]["en-US"]["result"] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(key, changed)
        for text in self.html.values():
            visible = " ".join(Page(text).visible)
            self.assertIsNone(conversion.PRICE_RE.search(visible))
            self.assertNotIn('"offers":', text)

    def test_observed_offers_keep_market_and_readback_not_runtime_success(self):
        for key, (us, tw) in PRICES.items():
            offer = self.contracts[key]["offer_readback"]
            self.assertEqual(us, offer["storefronts"]["USA"]["amount"])
            self.assertEqual(tw, offer["storefronts"]["TWN"]["amount"])
            self.assertEqual("unknown", offer["runtime_purchase"])
            self.assertEqual("NON_CONSUMABLE", offer["type"])
        for row in self.converted:
            value = row["conversion_contract"]
            self.assertEqual("unknown", value["effective_at_utc"])
            self.assertEqual("unknown", value["outcome"])
            self.assertFalse(value["scaling_allowed"])
            self.assertTrue(all(v == "unknown" for v in value["attribution"].values()))
            if row["locale"] in {"fr-FR", "ja"}:
                self.assertEqual("unknown", value["offer_readback"]["observed_price"])

    def test_known_exclusion_intents_and_honest_limits_remain(self):
        required = {
            "lumibopomofo": "Latin-letter Hanyu Pinyin",
            "aim990": "guaranteed 990 in 30 days",
            "cyca": "pregnancy prevention",
            "battai": "real battery temperature",
            "notesstudio100": "line-by-line audio synchronisation",
            "onepageppt": "whole pitch deck",
        }
        for key, intent in required.items():
            self.assertIn(intent, self.contracts[key]["exclude_intents"])
        for row in self.converted:
            contract = row["conversion_contract"]
            self.assertGreaterEqual(len(contract["exclude_intents"]), 3)
            self.assertTrue(contract["copy"]["limitations"])
            self.assertIn('data-publisher-disclosure="true"', self.html[row["route_id"]])
        one = self.contracts["onepageppt"]["localized"]["en-US"]
        self.assertIn("16:9", one["task"])
        self.assertIn("not a whole deck", one["result"])
        self.assertIn("not contraception", self.contracts["cyca"]["localized"]["en-US"]["result"])
        self.assertIn("Full-resolution, watermark-free", self.contracts["unblurry"]["localized"]["en-US"]["paid"])

    def test_visible_assets_are_native_and_bad_battai_caption_is_not_reused(self):
        for row in self.converted:
            expected = {
                proof["source_url"] for proof in row["conversion_contract"]["proofs"]
                if proof["asset"] and proof["asset"]["locale"] == row["locale"]
            }
            page = Page(self.html[row["route_id"]])
            self.assertEqual(expected, {asset["src"] for asset in page.images})
            if (row["app_key"], row["locale"]) in {("aim990", "fr-FR"), ("lumiweather", "ja")}:
                self.assertFalse(page.images)
                self.assertIn('data-evidence-status="BLOCKED_EVIDENCE"', self.html[row["route_id"]])
        self.assertEqual(
            {"battai-readings", "battai-readings-tw"},
            {p["id"] for p in self.contracts["battai"]["proofs"] if p["asset"]},
        )

    def test_candidate_queries_do_not_replace_published_catalog_vocabulary(self):
        headings = {
            "en-US": "Task search phrases under testing",
            "zh-Hant": "正在測試的任務搜尋語句",
            "fr-FR": "Requêtes liées à ces tâches en cours de test",
            "ja": "検証中のタスク検索フレーズ",
        }
        for row in self.converted:
            with self.subTest(route=row["route_id"]):
                raw = self.raw_routes[row["app_key"]]
                keywords = [
                    self.apps[row["app_key"]]["keywords"][index]
                    for index in raw["keyword_refs"]
                ] if row["locale"] == "en-US" else []
                self.assertEqual(keywords, row["source_vocabulary"])
                text = self.html[row["route_id"]]
                published_heading = f"<h2>{html.escape(routes.UI[row['locale']]['vocabulary'])}</h2>"
                if keywords:
                    published = re.search(re.escape(published_heading) + r"\s*<ul>(.*?)</ul>", text, re.S)
                    self.assertIsNotNone(published)
                    self.assertEqual(keywords, Page(published.group(1)).visible)
                else:
                    self.assertNotIn(published_heading, text)
                candidate = re.search(
                    r'<section[^>]*data-query-status="candidate"[^>]*data-query-verification="unverified"[^>]*>(.*?)</section>',
                    text, re.S,
                )
                self.assertIsNotNone(candidate)
                self.assertIn(f"<h2>{html.escape(routes.UI[row['locale']]['candidate_queries'])}</h2>", candidate.group(1))
                queries = re.search(r"<ul>(.*?)</ul>", candidate.group(1), re.S)
                self.assertIsNotNone(queries)
                self.assertEqual(
                    row["conversion_contract"]["copy"]["queries"],
                    Page(queries.group(1)).visible,
                )

    def test_schema_and_public_observation_artifact(self):
        data = json.loads(conversion.render_document(self.records, routes.SITE))
        schema = json.loads(conversion.render_schema())
        self.assertEqual(len(self.converted), len(data["routes"]))
        required = schema["properties"]["routes"]["items"]["required"]
        query_evidence = {
            "status": "candidate",
            "verification_status": "unverified",
            "search_volume": "unknown",
            "ranking": "unknown",
            "published_source": "unknown",
        }
        self.assertIn("query_evidence", required)
        self.assertEqual(
            query_evidence,
            schema["properties"]["routes"]["items"]["properties"]["query_evidence"]["const"],
        )
        for row in data["routes"]:
            self.assertTrue(set(required) <= set(row))
            self.assertEqual(query_evidence, row["query_evidence"])
        self.assertTrue(data["measurement_policy"]["unknown_is_not_zero"])
        self.assertFalse(data["measurement_policy"]["automatic_scale"])
        self.assertEqual("generated_not_deployed", data["state"])

    def test_actual_route_get_contract_and_single_consistent_cta(self):
        payloads = {urlsplit(row["canonical_url"]).path: self.html[row["route_id"]].encode() for row in self.converted}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                content = payloads.get(self.path)
                self.send_response(200 if content else 404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if content:
                    self.wfile.write(content)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for row in self.converted:
                with self.subTest(route=row["route_id"]):
                    url = f"http://127.0.0.1:{server.server_port}{urlsplit(row['canonical_url']).path}"
                    with urlopen(url, timeout=5) as response:
                        self.assertEqual(200, response.status)
                        text = response.read().decode()
                    page = Page(text)
                    store = [a for a in page.anchors if urlsplit(a.get("href", "")).hostname == "apps.apple.com"]
                    self.assertEqual(1, len(store))
                    self.assertEqual(row["app_store_url"], store[0]["href"])
                    self.assertEqual("conversion-offer", store[0]["aria-describedby"])
                    params = parse_qsl(urlsplit(store[0]["href"]).query)
                    self.assertEqual(["pt", "ct", "mt"], [k for k, _ in params])
                    self.assertEqual("118326163", dict(params)["pt"])
                    self.assertIn(dict(params)["ct"], {"geo_ask", "geo_pick", "geo_learn"})
                    self.assertIn(f"id{IDS[row['app_key']]}", urlsplit(store[0]["href"]).path)
                    self.assertEqual(
                        [row["canonical_url"]],
                        [link["href"] for link in page.links if link.get("rel") == "canonical"],
                    )
                    alternates = {link["hreflang"]: link["href"] for link in page.links if link.get("hreflang")}
                    self.assertEqual({**row["alternates"], "x-default": row["alternates"]["en-US"]}, alternates)
                    hero = text.split('data-conversion-hero="true">', 1)[1].split("</section>", 1)[0]
                    hero_text = " ".join(Page(hero).visible)
                    for field in ("task", "result", "free", "paid"):
                        self.assertIn(row["conversion_contract"]["copy"][field], hero_text)
                    self.assertEqual(1, hero.count('data-app-store-cta="true"'))
                    embedded = json.loads(re.search(r'id="conversion-route-contract">(.*?)</script>', text, re.S).group(1))
                    self.assertEqual(row["conversion_contract"], embedded)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
