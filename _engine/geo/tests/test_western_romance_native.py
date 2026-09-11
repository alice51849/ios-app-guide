from __future__ import annotations

import html
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import bopomofo_hub_titles
import build_pages_i18n as pages
import gen_hubs
import gen_store_attribution
from live_app_manifest import canonical_manifest
import pt_pt_outreach_copy
from videogen.registry import APPS, APPSTORE

LOCALES = (
    "en-US", "en-GB", "en-AU", "en-CA", "fr-FR",
    "fr-CA", "es-ES", "es-MX", "pt-BR", "pt-PT",
)
BRAZILIAN = re.compile(
    r"\b(?:sem|não uma)\s+assinaturas?\b|"
    r"\b(?:celular|tela|baixar|baixe|rastreamento|registros|"
    r"compartilhamento|compartilhar|planejador)\b|Recursos principais",
    re.I,
)


class WesternRomanceNativeTests(unittest.TestCase):
    def test_exact_47_by_10_generated_matrix_keeps_identity_and_attribution(self):
        apps = canonical_manifest()["apps"]
        self.assertEqual(47, len(apps))
        rendered = 0
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            pages, "PAGES", directory
        ):
            for key, app in apps.items():
                for locale in LOCALES:
                    with self.subTest(app=key, locale=locale):
                        output = pages.build_one(key, locale, pages.all_locales_for(key))
                        source = Path(output).read_text()
                        self.assertIn(f'<html lang="{locale}"', source)
                        self.assertIn(f"id{app['app_id']}", source)
                        self.assertEqual(str(app["app_id"]), str(APPSTORE[key]))
                        schemas = re.findall(
                            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
                            source, re.S,
                        )
                        application = json.loads(schemas[0])
                        self.assertEqual("SoftwareApplication", application["@type"])
                        self.assertEqual(locale, application["inLanguage"])
                        self.assertTrue(application["name"])
                        attributed, _ = gen_store_attribution.rewrite(
                            source,
                            gen_store_attribution.campaign_token(f"{locale}/{key}.html"),
                            "123456789", locale=locale, availability={},
                        )
                        store_links = re.findall(
                            r'<a\b[^>]*href="(https://apps\.apple\.com/[^"]+)"',
                            attributed,
                        )
                        self.assertTrue(store_links)
                        for url in store_links:
                            query = parse_qs(urlsplit(html.unescape(url)).query)
                            self.assertEqual(["123456789"], query.get("pt"))
                            self.assertEqual(1, len(query.get("ct", [])))
                            self.assertLessEqual(len(query["ct"][0]), 30)
                        if locale == "pt-PT":
                            self.assertNotRegex(source, BRAZILIAN)
                            self.assertIn("Funcionalidades principais", source)
                            pricing = pages.pricing_text_for(key, locale)
                            self.assertIn("subscri", pricing)
                            if APPS[key].get("purchase_model") == "paid_upfront":
                                self.assertIn("pagamento inicial", pricing)
                                self.assertNotIn("gratuit", pricing)
                        rendered += 1
        self.assertEqual(470, rendered)

    def test_region_specific_ui_does_not_change_brazilian_portuguese(self):
        self.assertEqual("Baixar", pages.get_ui("pt-BR")["dl"])
        self.assertIn("Sem assinatura", pages.get_ui("pt-BR")["ptxt"])
        self.assertEqual("Descarregar", pages.get_ui("pt-PT")["dl"])
        self.assertIn("Sem subscrição", pages.get_ui("pt-PT")["ptxt"])
        questions = pages.build_faq("pt-PT", "Sample", "Descrição", ["fotografias"])
        self.assertEqual(
            "Que aplicação escolher para fotografias?", questions[0][0]
        )

    def test_external_overrides_do_not_mutate_asc_source_or_price_literals(self):
        source = {
            "description": "Acesso vitalício US$5.99 · Sem assinatura.",
            "promotionalText": "Sem assinatura.",
        }
        reviewed = pt_pt_outreach_copy.external_values("shotinbox", "pt-PT", source)
        self.assertIn("Sem subscrição.", reviewed["description"])
        self.assertIn("US$5.99", reviewed["description"])
        self.assertIn("Sem assinatura.", source["description"])
        self.assertIs(
            source, pt_pt_outreach_copy.external_values("shotinbox", "pt-BR", source)
        )
        self.assertEqual(
            reviewed, pt_pt_outreach_copy.external_values("shotinbox", "pt-PT", reviewed)
        )

    def test_legitimate_handwritten_signatures_are_not_subscriptions(self):
        source = {"description": "Digitalize contratos e assinaturas."}
        self.assertEqual(
            source, pt_pt_outreach_copy.external_values("scanto", "pt-PT", source)
        )
        self.assertNotRegex(source["description"], BRAZILIAN)

    def test_native_purchase_copy_still_obeys_verified_flexible_models(self):
        source = "Exercícios de estudo.\n\nUm pagamento. Sem subscrições."
        with mock.patch.object(pages, "pricing_profile", return_value="flexible"):
            result = pages.sanitize_description("aim990", "pt-PT", source)
        self.assertIn("Exercícios de estudo.", result)
        self.assertNotIn("Sem subscrições", result)
        self.assertIn("ou por uma subscrição", result)

    def test_all_83_bopomofo_resource_titles_are_reviewed_for_both_locales(self):
        self.assertEqual(83, len(bopomofo_hub_titles.TITLES))
        english = re.compile(r"\b(?:free|printable|best|how|where|why|my child)\b", re.I)
        for slug in bopomofo_hub_titles.TITLES:
            for locale in ("fr-FR", "pt-PT"):
                title = bopomofo_hub_titles.resource_title(
                    "lumibopomofo", locale, slug, "English fallback"
                )
                self.assertNotRegex(title, english)
                self.assertNotEqual("English fallback", title)
        with self.assertRaisesRegex(ValueError, "Missing reviewed"):
            bopomofo_hub_titles.resource_title(
                "lumibopomofo", "fr-FR", "new-resource", "English fallback"
            )
        self.assertEqual(
            "Original",
            bopomofo_hub_titles.resource_title(
                "lumibopomofo", "pt-BR", "new-resource", "Original"
            ),
        )

    def test_hub_title_override_keeps_owned_answer_url(self):
        question = "best app to learn zhuyin bopomofo for kids"
        url = f"{gen_hubs.SITE}/pt-PT/answers/{gen_hubs.slugify(question)}.html"
        with mock.patch.dict(gen_hubs.queries.ALL, {"lumibopomofo": [question]}):
            with mock.patch.object(
                gen_hubs, "_owned_answer_link", return_value=(url, question)
            ):
                links = gen_hubs.localized_answer_links("lumibopomofo", "pt-PT")
        self.assertEqual(url, links[0][0])
        self.assertIn("crianças", links[0][1])

    def test_european_portuguese_tracking_copy_stays_contextual(self):
        slug = "best-period-tracker-app-no-account-required-iphone"
        title = pt_pt_outreach_copy.answer_title("cyca", "pt-PT", slug, "Old")
        self.assertIn("acompanhar o ciclo", title)
        self.assertEqual(
            "Original", pt_pt_outreach_copy.answer_title("cyca", "pt-BR", slug, "Original")
        )
        locale_pack = json.loads(
            (GEO / "portfolio_app_finder_i18n.json").read_text()
        )["localizations"]
        self.assertEqual("Sem rastreio", locale_pack["pt-PT"]["No tracking"])
        self.assertEqual("Sem rastreamento", locale_pack["pt-BR"]["No tracking"])


if __name__ == "__main__":
    unittest.main()
