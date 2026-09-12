from __future__ import annotations

import copy
from difflib import SequenceMatcher
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app_install_decision_feeds as feeds
import app_install_decision_routes as decisions
import build_pages_i18n as pages
import gen_hubs
import queries
from official_locales import OFFICIAL_LOCALES
import western_bopomofo_titles as resource_titles
import western_romance_candidates as candidates
import western_romance_copy as native
import western_romance_surface_copy as framing

BR_ONLY = re.compile(
    r"\b(?:celular(?:es)?|tela(?:s)?|assinatura(?:s)?|você(?:s)?|baixar|baixe|"
    r"aplicativo(?:s)?|rastreamento|planilha|planejamento|salvar)\b",
    re.I,
)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.text = []
        self.language = ""

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "html":
            self.language = dict(attrs).get("lang", "")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


class WesternRomanceContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(pages.PAGES)
        cls.apps, cls.sources = candidates.load_sources(cls.source)
        cls.inventory = candidates.build_inventory(cls.apps, cls.sources)
        cls.by_cell = {(cell["app_key"], cell["locale"]): cell for cell in cls.inventory}
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        cls.output = Path(cls.work.name) / "candidate"
        cls.result = candidates.generate(cls.source, cls.output, modified="2026-09-12")

    def test_exact_47_by_10_and_all_surfaces(self):
        self.assertEqual(470, len(self.inventory))
        self.assertEqual(
            {(key, locale) for key in self.apps for locale in native.LOCALES},
            set(self.by_cell),
        )
        self.assertEqual(set(self.apps), set(native.PT_PT_COPY))
        self.assertEqual(set(self.apps), set(framing.METHOD_BY_APP))
        self.assertEqual(2350, self.result["html_candidates"])
        for cell in self.inventory:
            self.assertEqual(set(candidates.SURFACES), set(cell["surfaces"]))
            self.assertEqual("unpublished_candidate", cell["publication_state"])
            self.assertIsNone(cell["social_receipt"])
            self.assertEqual(cell["locale"] != "en-US", cell["devto"].startswith("N/A"))

    def test_no_empty_fields_and_native_language_signals(self):
        markers = {
            "fr": r"\b(?:les|des|une|avec|sans|pour|dans|votre|toutes)\b",
            "es": r"\b(?:los|las|una|con|sin|para|todas|del)\b",
            "pt": r"\b(?:uma|com|sem|para|todos|todas|seu|sua|que)\b",
            "en": r"\b(?:the|your|with|without|for|and|all|one)\b",
        }
        for cell in self.inventory:
            key, locale = cell["app_key"], cell["locale"]
            content, record = cell["content"], cell["record"]
            for field in candidates.FIELDS:
                self.assertTrue(isinstance(content[field], str) and content[field].strip(), (key, locale, field))
                self.assertNotIn("\ufffd", content[field])
                non_latin = {
                    character for character in content[field]
                    if character.isalpha()
                    and not any(script in unicodedata.name(character, "") for script in ("LATIN", "GREEK"))
                }
                allowed = set("注音ㄅ") if key == "lumibopomofo" else set()
                self.assertFalse(non_latin - allowed, (key, locale, field, non_latin))
            self.assertRegex(content["description"], re.compile(markers[locale.split("-")[0]], re.I))
            self.assertTrue(pages._is_native_copy(locale, "description", content["description"], pages.load_app_locales(key)))
            for field in ("publisher_query", "decision_context", "purchase_label", "app_store_cta_label", "publisher_disclosure"):
                self.assertTrue(record[field].strip(), (key, locale, field))
                self.assertNotIn("\n", record[field])
            for field in ("subtitle", "description", "promotionalText"):
                text = content[field]
                latin = sum("LATIN" in unicodedata.name(char, "") for char in text)
                letters = sum(char.isalpha() for char in text)
                self.assertGreater(latin / max(1, letters), 0.9, (key, locale, field))
            if locale not in native.ENGLISH_LOCALES:
                self.assertNotRegex(content["description"], r"Pro edition unlocks|Master Your|Unlock your potential")

    def test_portuguese_variants_are_distinct_for_all_47_apps(self):
        self.assertEqual("Descarregar", pages.get_ui("pt-PT")["dl"])
        self.assertEqual("Baixar", pages.get_ui("pt-BR")["dl"])
        for key in self.apps:
            pt = self.by_cell[(key, "pt-PT")]["content"]
            br = self.by_cell[(key, "pt-BR")]["content"]
            for field in ("subtitle", "description", "promotionalText", "keywords"):
                self.assertNotRegex(pt[field], BR_ONLY, (key, field))
            # A short headline can be valid in both variants; the editorial
            # body must not be a Brazilian copy with a locale label changed.
            self.assertLess(SequenceMatcher(None, pt["description"], br["description"]).ratio(), 0.95, key)
            self.assertNotEqual(pt["promotionalText"], br["promotionalText"], key)
            self.assertIn("subscrição", pt["description"])
            self.assertEqual(self.by_cell[(key, "pt-PT")]["app_id"], self.by_cell[(key, "pt-BR")]["app_id"])
        signature = {"description": "A sua assinatura manuscrita fica no documento."}
        rewritten = native.external_values("scanto", "pt-BR", signature, pages.APPS["scanto"])
        self.assertEqual(signature["description"], rewritten["description"])

    def test_identity_purchase_model_and_no_hardcoded_unlock_price(self):
        self.assertEqual(13, sum(app["purchase_model"] == "paid_upfront" for app in self.apps.values()))
        paid_false = re.compile(r"free to try|free to start|free download|gratuit à essayer|gratis para probar|grátis para (?:testar|experimentar)", re.I)
        for cell in self.inventory:
            key, locale, record = cell["app_key"], cell["locale"], cell["record"]
            self.assertEqual(str(pages.APPSTORE[key]), cell["app_id"])
            self.assertEqual(pages.APPS[key]["purchase_model"], record["purchase_model"])
            self.assertIn(native.purchase_note(locale, record["purchase_model"]), record["decision_context"])
            self.assertNotRegex(record["purchase_label"], r"\d|[$€£]")
            self.assertNotRegex(record["decision_context"], r"US\s*\$\s*5[.,]99")
            if record["purchase_model"] == "paid_upfront":
                self.assertNotRegex(cell["content"]["description"], paid_false)
            if key in native.IDENTITIES:
                self.assertEqual(native.IDENTITIES[key], record["app_name"])
            if key == "tripplanet":
                self.assertNotIn("Lumi Trip Planet", record["decision_context"])
            self.assertIn(f"id{cell['app_id']}", record["app_store_url"])
            query = parse_qs(urlsplit(record["app_store_url"]).query)
            self.assertTrue(query.get("pt"))
            self.assertTrue(query.get("ct"))
            self.assertLessEqual(len(query["ct"][0]), 30)

    def test_no_score_guarantees_and_honest_photo_limits(self):
        for locale in native.LOCALES:
            aim = self.by_cell[("aim990", locale)]["content"]
            self.assertNotRegex(" ".join(aim.values()), r"\b30\b|Domine o TOEIC")
            self.assertIn("ETS", aim["description"])
            unblur = self.by_cell[("unblurry", locale)]["content"]["description"]
            limits = {
                "en": "depends on the original",
                "fr": "dépend de l'image",
                "es": "depende de la imagen",
                "pt": "depende da",
            }
            self.assertIn(limits[locale.split("-")[0]], unblur)

    def test_english_copy_does_not_claim_independent_regional_research(self):
        for key in self.apps:
            for locale in native.ENGLISH_LOCALES:
                cell = self.by_cell[(key, locale)]
                self.assertEqual("shared_English_product_copy_not_local_market_research", cell["editorial_scope"])
                self.assertEqual("global_live_roster_not_local_availability", cell["storefront_verification"])
                self.assertIn("not an independent ranking", cell["record"]["publisher_disclosure"])
                self.assertIn("shared across English variants", cell["record"]["publisher_disclosure"])
                self.assertEqual(locale, cell["record"]["locale"])

    def test_zipbox_keeps_all_ten_nonempty_surfaces(self):
        for locale in native.LOCALES:
            cell = self.by_cell[("zipbox", locale)]
            self.assertEqual("6806776579", cell["app_id"])
            self.assertEqual("paid_upfront", cell["record"]["purchase_model"])
            self.assertTrue((self.output / locale / "zipbox.html").is_file())
            self.assertTrue((self.output / locale / "hubs/zipbox.html").is_file())
            self.assertTrue((self.output / decisions.decision_page_relative("zipbox", locale)).is_file())

    def test_all_generated_html_native_identity_no_empty_or_brazilian_pt(self):
        for cell in self.inventory:
            key, locale, name = cell["app_key"], cell["locale"], cell["record"]["app_name"]
            paths = [
                Path(locale) / f"{key}.html",
                Path(locale) / "hubs" / f"{key}.html",
                decisions.decision_page_relative(key, locale),
                Path(locale) / "persona" / f"{key}-for-your-workflow.html",
                Path(locale) / "alternatives" / f"{key}-vs-existing-workflow.html",
            ]
            for relative in paths:
                parser = VisibleText()
                source = (self.output / relative).read_text()
                parser.feed(source)
                visible = " ".join(parser.text)
                self.assertEqual(locale, parser.language, relative)
                self.assertIn(name, visible, relative)
                self.assertGreater(len(visible.strip()), 100, relative)
                self.assertNotRegex(visible, r"US\s*\$\s*5[.,]99")
                if locale == "pt-PT":
                    self.assertNotRegex(visible, BR_ONLY, relative)
            for folder, suffix in (("persona", "for-your-workflow"), ("alternatives", "vs-existing-workflow")):
                source = (self.output / locale / folder / f"{key}-{suffix}.html").read_text()
                self.assertIn(html.escape(framing.for_locale(locale)["disclosure"]), source)
            alternative = (self.output / locale / "alternatives" / f"{key}-vs-existing-workflow.html").read_text()
            self.assertEqual(11, alternative.count('rel="alternate" hreflang='))
            self.assertIn("lumi-western-workflow-alternatives-v1", alternative)
            self.assertNotIn("bn-BD", alternative)

    def test_native_rss_and_json_feed_preserve_47_ids_and_disclosure(self):
        for locale in native.LOCALES:
            rss = ET.parse(self.output / locale / "rss.xml").getroot()
            self.assertEqual(locale, rss.findtext("channel/language"))
            items = rss.findall("channel/item")
            self.assertEqual(47, len(items))
            descriptions = "".join(item.findtext("description") for item in items)
            self.assertIn(framing.for_locale(locale)["disclosure"], html.unescape(descriptions))
            for app in self.apps.values():
                self.assertIn(f'id{app["app_store_id"]}', descriptions)
            document = json.loads((self.output / locale / "feed.json").read_text())
            self.assertEqual(locale, document["language"])
            self.assertEqual(47, len(document["items"]))
            self.assertEqual(
                {str(app["app_store_id"]) for app in self.apps.values()},
                {item["_meta"]["app_store_id"] for item in document["items"]},
            )
            self.assertFalse(document["_meta"]["is_ranking"])
            self.assertFalse(document["_meta"]["measured_search_volume"])
            self.assertEqual("Lumi Studio", document["authors"][0]["name"])
            if locale == "pt-PT":
                self.assertNotRegex(descriptions, BR_ONLY)
            self.assertEqual(
                (self.output / locale / "rss.xml").read_bytes(),
                (self.output / feeds.feed_relative(locale, "rss")).read_bytes(),
            )

    def test_current_bopomofo_titles_are_native_and_other_locales_untouched(self):
        slugs = {gen_hubs.slugify(question) for question in queries.ALL["lumibopomofo"]}
        self.assertTrue(slugs.issubset(resource_titles.TITLES))
        for locale in ("fr-CA", "fr-FR", "pt-PT"):
            for slug in slugs:
                title = resource_titles.resource_title("lumibopomofo", locale, slug, "English question")
                self.assertGreater(len(title), 15)
                self.assertNotIn("English question", title)
        for locale in set(OFFICIAL_LOCALES) - {"fr-CA", "fr-FR", "pt-PT"}:
            self.assertEqual("unchanged", resource_titles.resource_title("lumibopomofo", locale, "new", "unchanged"))

    def test_sources_and_other_40_locales_are_not_mutated(self):
        before = copy.deepcopy(self.sources)
        candidates.build_inventory(self.apps, self.sources)
        self.assertEqual(before, self.sources)
        others = set(OFFICIAL_LOCALES) - set(native.LOCALES)
        self.assertEqual(40, len(others))
        for key in self.apps:
            source = pages.load_app_locales(key)
            snapshot = copy.deepcopy(source)
            for locale in others:
                values = pages.external_localized_values(key, locale)
                with mock.patch.object(native, "external_values", side_effect=lambda k, l, v, a: v):
                    baseline = pages.external_localized_values(key, locale)
                self.assertEqual(baseline, values, (key, locale))
            self.assertEqual(snapshot, source)

    def test_candidates_fail_closed_on_missing_identity_or_existing_output(self):
        with self.assertRaises(ValueError):
            candidates.generate(self.source, self.source)
        with self.assertRaises(ValueError):
            candidates.generate(self.source, self.output)
        app = self.apps["zipbox"]
        source = self.sources[("zipbox", "pt-PT")]
        with self.assertRaises(ValueError):
            candidates.native_record("zipbox", "pt-PT", {**app, "app_store_id": "0"}, source)
        with self.assertRaises(ValueError):
            candidates.native_record("zipbox", "pt-PT", {**app, "purchase_model": "free_with_lifetime_unlock"}, source)
        with self.assertRaises(ValueError):
            candidates.native_record("zipbox", "bn-BD", app, source)
        with self.assertRaises(ValueError):
            candidates.native_record("zipbox", "pt-PT", app, {**source, "app_key": "tripbee"})
        with self.assertRaises(ValueError):
            candidates.native_record("zipbox", "pt-PT", app, {**source, "locale": "pt-BR"})


if __name__ == "__main__":
    unittest.main()
