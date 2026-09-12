from __future__ import annotations

import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_pages_i18n as pages
import cee_content_candidates as candidates
from cee_locale_copy import (
    CEE_LOCALES, COPY, HEBREW_KEYWORDS, IDENTITIES, PAID_UPFRONT,
    PURCHASE_NOTES, reviewed_values,
)
from hebrew_bidi import LRI, PDI, html_text, plain_text
from official_locales import OFFICIAL_LOCALES


class TextDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.isolates = []
        self.html = {}
        self.scripts = []
        self.in_script = False
        self.script = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.html = attrs
        if tag == "bdi":
            self.isolates.append(attrs)
        if tag == "script":
            self.in_script = True
            self.script = []

    def handle_data(self, value):
        if self.in_script:
            self.script.append(value)
        else:
            self.text.append(value)

    def handle_endtag(self, tag):
        if tag == "script":
            self.scripts.append("".join(self.script))
            self.in_script = False


class CEELocaleContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        live_path = Path(pages.PAGES) / ".appstore_live_state.json"
        cls.live_ids = json.loads(live_path.read_text())["live_ids"]
        cls.keys = candidates.keys_from_live_ids(cls.live_ids)
        cls.inventory = candidates.build_inventory(cls.keys)

    def test_exact_47_by_10_inventory_and_devto_na(self):
        self.assertEqual(47, len(self.keys))
        self.assertEqual(470, len(self.inventory))
        cells = {(row["app_key"], row["locale"]) for row in self.inventory}
        self.assertEqual(
            {(key, locale) for key in self.keys for locale in CEE_LOCALES},
            cells,
        )
        self.assertEqual({str(i) for i in self.live_ids}, {r["app_id"] for r in self.inventory})
        for row in self.inventory:
            self.assertEqual("N/A (non-en-US)", row["devto"])
            self.assertEqual("unpublished_candidate", row["publication_state"])
            self.assertIsNone(row["social_receipt"])

    def test_full_product_fixes_have_exact_ten_locales(self):
        for key in IDENTITIES:
            self.assertEqual(set(CEE_LOCALES), set(COPY[key]), key)
        self.assertNotIn("bn-BD", CEE_LOCALES)

    def test_other_40_locales_and_metadata_are_unchanged(self):
        unaffected = set(OFFICIAL_LOCALES) - set(CEE_LOCALES)
        self.assertEqual(40, len(unaffected))
        for key in self.keys:
            source = pages.load_app_locales(key)
            snapshot = copy.deepcopy(source)
            for locale in unaffected:
                values = pages.external_localized_values(key, locale, source)
                with mock.patch.object(pages, "cee_reviewed_values", side_effect=lambda k, l, v: v):
                    baseline = pages.external_localized_values(key, locale, source)
                self.assertEqual(baseline, values, (key, locale))
                sample = {"name": "same", "subtitle": "same", "description": "same"}
                self.assertEqual(sample, reviewed_values(key, locale, sample))
                self.assertEqual("&lt;&amp;&gt;", html_text("<&>", locale))
                self.assertEqual("App 123", plain_text("App 123", locale))
            self.assertEqual(snapshot, source, key)

    def test_native_scripts_and_no_english_fallback(self):
        for row in self.inventory:
            key, locale = row["app_key"], row["locale"]
            source = pages.load_app_locales(key)
            for field in ("subtitle", "description", "promotionalText"):
                text = row[field]
                self.assertTrue(text.strip(), (key, locale, field))
                self.assertTrue(
                    pages._is_native_copy(locale, field, text, source),
                    (key, locale, field),
                )
            text = "\n".join(row[field] for field in candidates.FIELDS)
            for forbidden in (
                "ABC phonics, letter sounds and tracing for ages",
                "Full Pro edition, offline",
                "Pro edition unlocks the full",
                "Master Your TOEIC Skills",
                "Unlock your potential with Aim990",
                "Timed practice",
            ):
                self.assertNotIn(forbidden, text, (key, locale))
            if locale in {"he", "ru", "uk"}:
                pattern = r"[\u0590-\u05ff]" if locale == "he" else r"[\u0400-\u04ff]"
                for field in ("subtitle", "description", "promotionalText"):
                    self.assertGreaterEqual(len(re.findall(pattern, row[field])), 5, (key, locale, field))
        for key in HEBREW_KEYWORDS:
            keywords = pages.external_localized_values(key, "he")["keywords"]
            self.assertNotRegex(keywords, r"[a-zA-Z]")
        ukrainian = pages.external_localized_values("aim990", "uk")
        self.assertNotRegex(ukrainian["keywords"], r"\b(?:English|exam|prep|study|coach|practice|score)\b")
        slovene = pages.external_localized_values("wifiaidlite", "sl-SI")
        self.assertNotRegex(slovene["description"], r"Deep Check|Direct IP|Jitter")

    def test_brand_and_paid_pro_identity(self):
        for key, name in IDENTITIES.items():
            for locale in CEE_LOCALES:
                values = pages.external_localized_values(key, locale)
                self.assertEqual(name, values["name"])
                if key in PAID_UPFRONT:
                    self.assertIn("Pro", values["description"])
                if key == "tripplanet":
                    self.assertIn("Trip Planet: Kids Quest", values["description"])
                    self.assertNotIn("Lumi Trip", json.dumps(values, ensure_ascii=False))
        self.assertEqual("6779745474", str(pages.APPSTORE["lumimissionpro"]))
        self.assertEqual("6787193643", str(pages.APPSTORE["tripplanet"]))

    def test_purchase_model_is_registry_backed_and_never_priced(self):
        for key, translations in COPY.items():
            expected = "paid_upfront" if key in PAID_UPFRONT else "free_with_lifetime_unlock"
            self.assertEqual(expected, pages.APPS[key]["purchase_model"], key)
            for locale in translations:
                values = pages.external_localized_values(key, locale)
                note = PURCHASE_NOTES[locale][0 if key in PAID_UPFRONT else 1]
                self.assertTrue(values["description"].endswith(note))
                self.assertNotRegex(
                    " ".join(values[field] for field in candidates.FIELDS),
                    r"(?:US\$|\$\s*\d|€\s*\d|₪\s*\d|\d+[.,]\d+\s*(?:USD|EUR|Kč|zł|lei|₽|₺))",
                )
        for locale in CEE_LOCALES:
            mission = pages.external_localized_values("lumimissionpro", locale)
            self.assertNotRegex(mission["description"], r"Zdarma|Zdarma k|Gratuit|Бесплатно|Безкоштовно|בחינם")
            self.assertNotRegex(pages.external_localized_values("shotinbox", locale)["description"], r"US\s*\$")
        hungarian = pages.external_localized_values("unblurry", "hu")["description"]
        self.assertIn("Nincs előfizetés és nincs reklám.", hungarian)
        self.assertNotIn("Nincs egyszeri vásárlás", hungarian)
        self.assertIn("egyszeri alkalmazáson belüli vásárlással", hungarian)

    def test_aim990_has_no_deadline_or_score_guarantee(self):
        for locale in CEE_LOCALES:
            values = pages.external_localized_values("aim990", locale)
            text = " ".join(values[field] for field in candidates.FIELDS)
            self.assertNotRegex(text, r"\b30\b|\b990\b|guaranteed|guarantee")
            self.assertIn("ETS", values["description"])
        hebrew = pages.external_localized_values("aim990", "he")
        self.assertIn("אינה מבטיחה ציון", hebrew["description"])
        ukrainian = pages.external_localized_values("aim990", "uk")
        self.assertIn("не обіцяє певного бала", ukrainian["description"])

    def test_slovak_diacritics_and_complete_headlines(self):
        for key in ("lockhour", "lumiletters", "lumibopomofo", "sereno"):
            values = pages.external_localized_values(key, "sk")
            self.assertRegex(values["description"], r"[áäčďéíĺľňóôŕšťúýž]")
            self.assertNotRegex(values["description"], r"\bpomaha\b|\bdetom\b|\bsustredenej\b|\bChrante\b")
        expected = {
            ("sereno", "cs"): "soustředění",
            ("sereno", "sk"): "sústredenie",
            ("sereno", "sl-SI"): "zbranost",
            ("sereno", "tr"): "gürültü",
        }
        for (key, locale), ending in expected.items():
            self.assertTrue(pages.external_localized_values(key, locale)["subtitle"].endswith(ending))
        self.assertNotIn("Otroška Matemat", pages.external_localized_values("lumimathpro", "sl-SI")["name"])
        self.assertNotIn("To n.", pages.external_localized_values("lumiletterspro", "sl-SI")["subtitle"])

    def test_hebrew_plaintext_base_direction_and_isolates(self):
        for row in self.inventory:
            if row["locale"] != "he":
                continue
            text = row["social_preview"]
            first = next(unicodedata.bidirectional(c) for c in text if unicodedata.bidirectional(c) in {"L", "R", "AL"})
            self.assertEqual("R", first, row["app_key"])
            self.assertEqual(text.count(LRI), text.count(PDI))
            self.assertIn(LRI, text)
        self.assertEqual(
            'הקישור ל-<bdi dir="ltr">App Store</bdi> כאן:',
            html_text("הקישור ל-App Store כאן:", "he"),
        )
        self.assertEqual(
            '<bdi dir="ltr">A&amp;B 37</bdi> &lt;בדיקה&gt;',
            html_text("A&B 37 <בדיקה>", "he"),
        )
        self.assertNotIn("<script>", html_text("<script>alert(1)</script>", "he"))

    def test_generated_hebrew_dom_and_jsonld(self):
        with tempfile.TemporaryDirectory() as output, mock.patch.object(pages, "PAGES", output):
            for key in self.keys:
                path = pages.build_one(key, "he", pages.all_locales_for(key))
                dom = TextDOM()
                dom.feed(Path(path).read_text())
                self.assertEqual("he", dom.html.get("lang"))
                self.assertEqual("rtl", dom.html.get("dir"))
                self.assertTrue(dom.isolates, key)
                self.assertTrue(all(attrs.get("dir") == "ltr" for attrs in dom.isolates))
                values = pages.external_localized_values(key, "he")
                self.assertIn(values["name"], "".join(dom.text))
                for script in dom.scripts:
                    payload = json.loads(script)
                    self.assertNotIn("<bdi", json.dumps(payload))
                    self.assertEqual("he", payload["inLanguage"])

    def test_unpublished_candidate_writer_cannot_target_live_or_metadata(self):
        for target in (Path(pages.PAGES), Path(pages.PAGES) / "he", Path(pages.DATA) / "candidate.json"):
            with self.assertRaises(ValueError):
                candidates._candidate_path(target)
        with self.assertRaises(ValueError):
            candidates.keys_from_live_ids([self.live_ids[0], self.live_ids[0]])
        with self.assertRaises(ValueError):
            candidates.keys_from_live_ids(["0"])

    def test_candidate_writer_rejects_wrong_locale_identity_and_partial_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [
                [],
                self.inventory[:1],
                [dict(self.inventory[0], locale="bn-BD")],
                [dict(self.inventory[0], app_id="0")],
                self.inventory + [self.inventory[0]],
            ]
            for records in cases:
                with self.assertRaises(ValueError):
                    candidates.write_candidates(records, Path(directory) / "candidates")
            self.assertFalse((Path(directory) / "candidates").exists())


if __name__ == "__main__":
    unittest.main()
