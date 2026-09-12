"""Exact18 existing-surface replay; public listing evidence is not a sale."""
from __future__ import annotations

from collections import Counter
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit

import app_store_storefronts as stores
import gen_app_store_qr_ctas as qr
import gen_publisher_disclosures as disclosures
import gen_store_attribution as attribution
import market_availability as market
from official_locales import OFFICIAL_LOCALES
from videogen.registry import APPSTORE

APPS = {
    "caldaily": ("6794178671", "best-calculator-app-iphone-that-saves-history-you-can-name-and-search"),
    "cvdesk": ("6781337213", "best-resume-builder-app-for-career-changers-2026"),
    "dailymate": ("6790418321", "best-practical-language-phrase-app-for-travelers-with-apple-watch"),
    "dailymatelite": ("6794725568", "best-free-travel-phrasebook-app-with-real-dialogues-for-iphone"),
    "gmoney": ("6755782939", "best-travel-budget-tracker-app-no-subscription-iphone"),
    "hourstag": ("6754218117", "best-app-to-track-where-my-money-goes-and-save-more"),
    "lumimissionpro": ("6779745474", "best-complete-morning-and-bedtime-routine-app-for-kids"),
    "moneytag": ("6801956402", "best-income-and-expense-tracker-for-freelance-projects-no-subscription"),
    "photocream": ("6781808054", "best-pay-once-film-photo-editor-for-travel-creators-on-iphone"),
    "sereno": ("6788236641", "best-white-noise-app-for-falling-asleep-no-subscription"),
    "shotinbox": ("6802166527", "best-app-to-sort-screenshots-on-iphone-offline"),
    "snapport": ("6780575828", "best-passport-photo-app-for-babies-and-toddlers-at-home"),
    "snapportlite": ("6792856304", "best-free-passport-photo-app-for-iphone-that-works-offline"),
    "sononote": ("6782139553", "best-voice-notes-app-that-summarizes-meetings-on-iphone"),
    "tripbeelite": ("6791299610", "best-simple-trip-planner-app-for-one-upcoming-trip-iphone"),
    "wifiaid": ("6790467886", "best-wifi-troubleshooting-app-for-remote-workers-with-connected-but-no-internet"),
    "wordmate": ("6789917808", "best-vocabulary-app-for-busy-commuters-with-apple-watch"),
    "wordmatelite": ("6797601720", "best-free-vocabulary-app-for-adults-one-minute-a-day-no-flashcard-decks"),
}
ROLES = {
    "landing-download": ("geo_pick", 1),
    "root-answer": ("geo_ask", 2),
    "localized-answer": ("geo_ask", 2),
    "guide-editorial": ("geo_learn", 2),
    "guide-preview": ("geo_learn", 1),
    "guide-qr": ("geo_learn", 1),
    "guide-mobile": ("geo_learn", 1),
}
UNKNOWN = {
    ("lumibopomofo", "zh-Hans"), ("lumibopomofopro", "zh-Hans"),
    ("lumiletterspro", "zh-Hans"), ("zipbox", "fr-FR"),
}
PAGES = Path(os.environ.get("GEO_PAGES", attribution.PAGES))


def target_paths(key):
    slug = APPS[key][1]
    paths = [
        f"en-US/{key}.html", f"answers/{slug}.html",
        f"en-US/answers/{slug}.html", f"guides/{key}.html",
    ]
    if key == "cvdesk":
        paths.append("answers/best-ats-resume-app.html")
    return paths


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links, self.active = [], None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.active = {"attrs": dict(attrs), "label": ""}
            self.links.append(self.active)

    def handle_endtag(self, tag):
        if tag == "a":
            self.active = None

    def handle_data(self, data):
        if self.active is not None:
            self.active["label"] += data


class ShortZeroSurfaceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.availability = stores.load_storefront_availability(PAGES)
        cls.copies = disclosures.load_landing_disclosures()

    def test_exact18_ids_and_existing_path_denominators(self):
        self.assertEqual(18, len(APPS))
        for key, (app_id, _) in APPS.items():
            self.assertEqual(APPSTORE[key], app_id)
            self.assertIn(app_id, self.availability["us"])
        paths = {path for key in APPS for path in target_paths(key)}
        self.assertEqual(73, len(paths))
        self.assertEqual(91, len(paths | {f"bn-BD/{key}.html" for key in APPS}))
        self.assertTrue(all((PAGES / path).is_file() for path in paths))

    def test_all183_vectors_keep_app_campaign_and_html_escaping(self):
        counts, roles = Counter(), Counter()
        for key, (app_id, _) in APPS.items():
            groups = list(ROLES.items())
            if key == "cvdesk":
                groups += [("root-answer", ("geo_ask", 2)), ("source-citation", ("geo_ask", 1))]
            for role, (campaign, count) in groups:
                for _ in range(count):
                    before = f"https://apps.apple.com/app/id{app_id}?pt=118326163&ct={campaign}&mt=8"
                    expected = before.replace("/app/", "/us/app/")
                    with self.subTest(key=key, role=role):
                        updated = attribution.final_store_url(
                            before, campaign, "118326163", locale="en-US",
                            availability=self.availability, app_id=app_id,
                        )
                        self.assertEqual(expected, updated)
                        self.assertEqual(updated, attribution.final_store_url(
                            updated, campaign, "118326163", locale="en-US",
                            availability=self.availability, app_id=app_id,
                        ))
                        parsed = urlsplit(updated)
                        self.assertEqual(f"/us/app/id{app_id}", parsed.path)
                        self.assertEqual(
                            {"pt": ["118326163"], "ct": [campaign], "mt": ["8"]},
                            parse_qs(parsed.query),
                        )
                        self.assertEqual(updated, html.unescape(html.escape(updated, quote=True)))
                    counts[key] += 1
                    roles[role] += 1
        self.assertEqual(183, sum(counts.values()))
        self.assertEqual(13, counts.pop("cvdesk"))
        self.assertEqual({10}, set(counts.values()))
        self.assertEqual({
            "landing-download": 18, "root-answer": 38, "localized-answer": 36,
            "guide-editorial": 36, "guide-preview": 18, "guide-qr": 18,
            "guide-mobile": 18, "source-citation": 1,
        }, roles)

    def test_root_en_uses_declared_policy_not_an_unknown_locale_guess(self):
        direct = "https://apps.apple.com/app/id6794178671"
        source = f'<html lang="en"><body><a href="{direct}">Get it</a></body></html>'
        updated, count = attribution.rewrite(
            source, "geo_ask", "118326163", availability=self.availability
        )
        self.assertIn("/us/app/id6794178671?", updated)
        self.assertEqual(1, count)
        for locale in ("xx", ""):
            self.assertNotIn(locale, stores.LOCALE_STOREFRONTS)
        self.assertNotIn("6794178671", {}.get("us", ()))

    def test_unknowns_are_not_promoted_to_available_or_fabricated_na(self):
        for key, locale in UNKNOWN:
            with self.subTest(key=key, locale=locale):
                app_id = APPSTORE[key]
                country = stores.LOCALE_STOREFRONTS[locale]
                self.assertNotIn(app_id, self.availability.get(country, ()))
                self.assertFalse(market.is_unavailable(locale, app_id))
        with self.assertRaises(ValueError):
            stores.validated_app_store_url(
                "https://apps.apple.com/us/app/id6794178671",
                expected_app_id="6794178671", expected_locale="zh-Hans",
            )
        with self.assertRaises(ValueError):
            stores.validated_app_store_url(
                "https://apps.apple.com/us/app/id6781337213",
                expected_app_id="6794178671", expected_locale="en-US",
            )

    def test_all73_pages_have_no_countryless_links_and_are_idempotent(self):
        for relative in sorted({path for key in APPS for path in target_paths(key)}):
            with self.subTest(path=relative):
                source = (PAGES / relative).read_text()
                for link in Links(source).links:
                    self.assertIsNone(re.match(
                        r"https://apps\.apple\.com/app/id\d+",
                        link["attrs"].get("href", ""),
                    ))
                updated, count = attribution.rewrite(
                    source, attribution.page_token(relative, source), "118326163",
                    locale="en-US", availability=self.availability,
                )
                self.assertEqual(source, updated)
                self.assertEqual(0, count)
                self.assertIsNone(attribution.qr_card_desync(source))

    def test_36_visible_disclosures_are_exact_native_and_bn_stays_content_only(self):
        for key in APPS:
            for locale in ("en-US", "bn-BD"):
                with self.subTest(key=key, locale=locale):
                    source = (PAGES / locale / f"{key}.html").read_text()
                    parsed = disclosures._LandingDisclosureAnchors(source)
                    self.assertEqual(1, len(parsed.markers))
                    self.assertFalse(parsed.markers[0]["hidden"])
                    self.assertIn(html.escape(self.copies[locale], quote=False), source)
                    self.assertEqual(source, disclosures.ensure_landing_disclosure(
                        source, locale, copy_by_locale=self.copies
                    ))
                    if locale == "bn-BD":
                        self.assertNotIn("apps.apple.com", source)
                        self.assertNotIn("InstallAction", source)
                        self.assertNotIn("app-store-qr-card", source)
                        self.assertIn("MARKET_NOT_IN_APPLE_MEDIA_SERVICES", source)

    def test_18_qr_payloads_card_links_and_mobile_actions_are_one_generation(self):
        for key, (app_id, _) in APPS.items():
            with self.subTest(key=key):
                source = (PAGES / "guides" / f"{key}.html").read_text()
                expected = f"https://apps.apple.com/us/app/id{app_id}?pt=118326163&ct=geo_learn&mt=8"
                relative = qr.qr_asset_relative(app_id, expected)
                raw = (PAGES / relative).read_bytes()
                self.assertEqual(qr.qr_svg(app_id, expected).encode(), raw)
                self.assertIn(hashlib.sha256(expected.encode()).hexdigest()[:20], relative.name)
                self.assertEqual(expected, html.unescape(attribution.QR_CARD_LINK_RE.search(source)["href"]))
                self.assertIn(relative.as_posix(), source)
                self.assertIsNone(attribution.qr_card_desync(source))
                apple = [
                    link for link in Links(source).links
                    if f"/id{app_id}" in link["attrs"].get("href", "")
                ]
                self.assertGreaterEqual(len(apple), 5)
                self.assertTrue(all(link["attrs"]["href"] == expected for link in apple))
                for link in apple:
                    self.assertTrue(link["label"].strip() or link["attrs"].get("aria-label"))

    def test_identity_and_schema_samples_are_not_stamped_as_ctas(self):
        app_id = APPS["caldaily"][0]
        identity = f"https://apps.apple.com/app/id{app_id}"
        payload = {
            "@type": "SoftwareApplication", "@id": identity, "sameAs": [identity],
            "installUrl": identity,
        }
        source = '<script type="application/ld+json">' + json.dumps(payload) + "</script>"
        updated, _ = attribution.rewrite(
            source, "geo_pick", "118326163", locale="en-US",
            availability=self.availability,
        )
        value = json.loads(updated.split(">", 1)[1].rsplit("</", 1)[0])
        self.assertEqual(identity, value["@id"])
        self.assertEqual([identity], value["sameAs"])
        self.assertIn(f"/us/app/id{app_id}?", value["installUrl"])

    def test_previous_paid_math_answer_keeps_its_five_pro_ctas(self):
        relative = "answers/best-complete-math-learning-app-for-preschool-and-early-grades.html"
        source = (PAGES / relative).read_text()
        links = [
            link["attrs"]["href"] for link in Links(source).links
            if "apps.apple.com/" in link["attrs"].get("href", "")
        ]
        self.assertEqual(5, len(links))
        self.assertTrue(all("/us/app/id6776958488?" in link for link in links))
        self.assertNotIn("6778269699", source)
        self.assertIn("paid-upfront", source.lower())

    def test_47_apps_50_locales_150_feeds_and_na_items_stay_in_denominator(self):
        import owned_app_feeds as feeds

        self.assertEqual(50, len(OFFICIAL_LOCALES))
        self.assertEqual(150, len(feeds.present_feed_paths(PAGES)))
        cells = set()
        for locale in OFFICIAL_LOCALES:
            document = json.loads((PAGES / locale / "feed.json").read_text())
            self.assertEqual(47, len(document["items"]))
            for item in document["items"]:
                owned = item["_owned_app"]
                cells.add((owned["app_store_id"], locale))
                self.assertEqual(self.copies[locale], owned["publisher_disclosure"])
                self.assertFalse(owned["independent_ranking"])
                if market.is_unavailable(locale, owned["app_store_id"]):
                    self.assertNotIn("external_url", item)
                    self.assertFalse(owned["market_availability"]["publishable"])
                    self.assertFalse(owned["market_availability"]["facts_allowed"])
                    self.assertEqual(0, owned["market_availability"]["outbox_count"])
            if locale == "bn-BD":
                self.assertNotIn("apps.apple.com", json.dumps(document))
        self.assertEqual(2350, len(cells))


if __name__ == "__main__":
    unittest.main()
