import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bopomofo_education_qa as education_qa  # noqa: E402
import bopomofo_flashcards as base  # noqa: E402
import education_qa_experiment as experiment  # noqa: E402


def _json_ld(page):
    return [
        json.loads(payload)
        for payload in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            page,
            re.DOTALL,
        )
    ]


def _visible_pairs(page):
    body = page.split(education_qa.BODY_START, 1)[1].split(
        education_qa.BODY_END,
        1,
    )[0]
    questions = [
        html.unescape(value)
        for value in re.findall(
            r'<p class="education-qa-question">(.*?)</p>',
            body,
            re.DOTALL,
        )
    ]
    answers = [
        html.unescape(value)
        for value in re.findall(
            r'<span class="education-qa-answer-text">(.*?)</span>',
            body,
            re.DOTALL,
        )
    ]
    return list(zip(questions, answers, strict=True))


def _quiz(page):
    quizzes = [item for item in _json_ld(page) if item.get("@type") == "Quiz"]
    if len(quizzes) != 1:
        raise AssertionError(f"expected one Quiz, found {len(quizzes)}")
    return quizzes[0]


class EducationQACanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = experiment.build()
        cls.pages = {
            locale: (
                experiment.OUTPUT
                / experiment.candidate_relative_path(locale)
            ).read_text(encoding="utf-8")
            for locale in education_qa.CANARY_LOCALES
        }

    def test_control_is_a_real_leaf_flashcard_page_before_schema(self):
        for locale in education_qa.CANARY_LOCALES:
            with self.subTest(locale=locale):
                control = base.render_page(
                    locale,
                    app_public=True,
                    alternate_locales=education_qa.CANARY_LOCALES,
                )
                self.assertIn('id="bopomofo-flashcard-planner"', control)
                self.assertIn('id="symbol-picker"', control)
                self.assertIn('"maxItems":37', control)
                self.assertNotIn('"@type":"Quiz"', control)
                self.assertNotIn(education_qa.BODY_START, control)
                self.assertIn("<h1>", control)

    def test_candidate_questions_and_answers_are_static_and_immediate(self):
        for locale, page in self.pages.items():
            with self.subTest(locale=locale):
                body = page.split(education_qa.BODY_START, 1)[1].split(
                    education_qa.BODY_END,
                    1,
                )[0]
                self.assertEqual(
                    len(education_qa.FLASHCARD_ORDERS),
                    body.count('class="education-qa-card"'),
                )
                self.assertNotIn("<script", body.lower())
                self.assertNotIn("<details", body.lower())
                self.assertNotIn(" hidden", body.lower())
                self.assertNotIn("aria-hidden", body.lower())
                self.assertNotIn("display:none", body.lower())
                self.assertNotIn("paywall", body.lower())
                self.assertLess(
                    page.index(education_qa.BODY_START),
                    page.index("https://apps.apple.com/"),
                )

    def test_all_37_source_rows_are_deterministically_correct(self):
        self.assertEqual(37, len(education_qa.CANONICAL_ROWS))
        self.assertEqual(
            set(range(0x3105, 0x312A)),
            {ord(row["symbol"]) for row in education_qa.CANONICAL_ROWS},
        )
        for expected_order, row in enumerate(
            education_qa.CANONICAL_ROWS,
            start=1,
        ):
            with self.subTest(order=expected_order, symbol=row["symbol"]):
                self.assertEqual(expected_order, row["order"])
                self.assertEqual(
                    f"U+{ord(row['symbol']):04X}",
                    row["unicode"],
                )
                self.assertIn(
                    row["category"],
                    {"initial", "medial", "final"},
                )
                self.assertTrue(
                    row["concept_uri"].lower().endswith(
                        row["symbol_id"].lower()
                    )
                )

    def test_72_visible_pairs_match_quiz_byte_for_byte_semantically(self):
        for locale, page in self.pages.items():
            cards = education_qa.flashcards(locale)
            visible = _visible_pairs(page)
            schema = _quiz(page)
            schema_pairs = [
                (
                    question["text"],
                    question["acceptedAnswer"]["text"],
                )
                for question in schema["hasPart"]
            ]
            self.assertEqual(
                [(card["question"], card["answer"]) for card in cards],
                visible,
            )
            self.assertEqual(visible, schema_pairs)
            for card, visible_pair, schema_pair in zip(
                cards,
                visible,
                schema_pairs,
                strict=True,
            ):
                with self.subTest(locale=locale, card=card["id"]):
                    self.assertEqual(card["question"], visible_pair[0])
                    self.assertEqual(card["answer"], visible_pair[1])
                    self.assertEqual(visible_pair, schema_pair)
                    self.assertIn(card["concept_uri"], page)

    def test_selected_cards_are_unique_and_cover_all_three_groups(self):
        cards = education_qa.flashcards("en")
        self.assertEqual(18, len(cards))
        self.assertEqual(18, len({card["answer"] for card in cards}))
        self.assertEqual(
            {"initial": 6, "medial": 3, "final": 9},
            {
                category: sum(
                    card["category"] == category for card in cards
                )
                for category in ("initial", "medial", "final")
            },
        )

    def test_72_html_escaping_round_trips_without_schema_drift(self):
        for locale, page in self.pages.items():
            cards = education_qa.flashcards(locale)
            body = page.split(education_qa.BODY_START, 1)[1].split(
                education_qa.BODY_END,
                1,
            )[0]
            for card in cards:
                with self.subTest(locale=locale, card=card["id"]):
                    escaped = html.escape(card["question"])
                    self.assertIn(
                        f'<p class="education-qa-question">{escaped}</p>',
                        body,
                    )
                    self.assertEqual(
                        card["question"],
                        html.unescape(escaped),
                    )

    def test_adversarial_html_and_script_escaping_is_safe(self):
        locale = "en"
        copy = education_qa.EDUCATION_COPY[locale]
        hostile = (
            'Which <symbol> & "group" closes </script> at {unicode} '
            'inside {category}?'
        )
        with mock.patch.dict(copy, {"question": hostile}, clear=False):
            page = education_qa.render_candidate_page(locale)
            pairs = _visible_pairs(page)
            schema = _quiz(page)
            self.assertIn("&lt;symbol&gt;", page)
            self.assertIn("&lt;/script&gt;", page)
            self.assertIn("<\\/script>", page)
            self.assertEqual(
                pairs,
                [
                    (
                        item["text"],
                        item["acceptedAnswer"]["text"],
                    )
                    for item in schema["hasPart"]
                ],
            )

    def test_quiz_uses_only_google_required_flashcard_properties(self):
        for locale, page in self.pages.items():
            with self.subTest(locale=locale):
                schema = _quiz(page)
                self.assertEqual("Quiz", schema["@type"])
                self.assertNotIn("educationalAlignment", schema)
                self.assertEqual(
                    len(education_qa.FLASHCARD_ORDERS),
                    len(schema["hasPart"]),
                )
                for question in schema["hasPart"]:
                    self.assertEqual("Question", question["@type"])
                    self.assertEqual("Flashcard", question["eduQuestionType"])
                    self.assertIsInstance(question["text"], str)
                    self.assertTrue(question["text"])
                    self.assertEqual(
                        {"@type", "text"},
                        set(question["acceptedAnswer"]),
                    )
                    self.assertEqual(
                        "Answer",
                        question["acceptedAnswer"]["@type"],
                    )

    def test_supported_locale_rule_is_exact(self):
        self.assertEqual(
            (
                "en-AU",
                "en-CA",
                "en-GB",
                "en-US",
                "es-MX",
                "pt-BR",
                "pt-PT",
                "vi",
            ),
            education_qa.GOOGLE_ELIGIBLE_OFFICIAL_LOCALES,
        )
        for locale in (
            "en",
            "en-ZA",
            "pt-BR",
            "pt-PT",
            "pt-AO",
            "es-MX",
            "vi",
            "vi-VN",
        ):
            with self.subTest(locale=locale):
                self.assertTrue(
                    education_qa.google_education_qa_supported(locale)
                )
        for locale in (
            "es-ES",
            "es-AR",
            "de-DE",
            "fr-FR",
            "ja",
            "ko",
            "zh-Hant",
            "zh-Hans",
        ):
            with self.subTest(locale=locale):
                self.assertFalse(
                    education_qa.google_education_qa_supported(locale)
                )
                self.assertIsNone(education_qa.quiz_schema(locale))

    def test_provenance_covers_canonical_qti_oer_moe_and_unicode(self):
        urls = [item["url"] for item in education_qa.SOURCE_PROVENANCE]
        self.assertEqual(5, len(urls))
        self.assertIn("zhuyin-bopomofo.json", urls[0])
        self.assertIn("language.moe.gov.tw", urls[1])
        self.assertIn("unicode.org", urls[2])
        self.assertIn("lms-question-bank", urls[3])
        self.assertIn("oer-repository-metadata", urls[4])
        self.assertEqual(
            education_qa.SOURCE_DIGEST,
            hashlib.sha256(
                json.dumps(
                    education_qa.CANONICAL_ROWS,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        )

    def test_canonical_hreflang_robots_and_candidate_sitemap(self):
        for locale, page in self.pages.items():
            with self.subTest(locale=locale):
                self.assertIn(
                    f'<link rel="canonical" href="{base.canonical(locale)}">',
                    page,
                )
                for alternate in education_qa.CANARY_LOCALES:
                    self.assertIn(
                        f'hreflang="{alternate}" '
                        f'href="{base.canonical(alternate)}"',
                        page,
                    )
        robots = (base.PAGES / "robots.txt").read_text(encoding="utf-8")
        googlebot = robots.split("User-agent: Googlebot", 1)[1].split(
            "User-agent:",
            1,
        )[0]
        self.assertIn("Allow: /", googlebot)
        self.assertNotIn("Disallow:", googlebot)
        root = ET.parse(experiment.SITEMAP_PATH).getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        self.assertEqual(
            [
                base.canonical(locale)
                for locale in education_qa.CANARY_LOCALES
            ],
            [
                node.text
                for node in root.findall("sm:url/sm:loc", namespace)
            ],
        )

    def test_first_party_disclosure_and_only_related_app_cta(self):
        for locale, page in self.pages.items():
            with self.subTest(locale=locale):
                disclosure = page.index(
                    'data-first-party-disclosure="true"'
                )
                app_links = re.findall(
                    r'https://apps\.apple\.com/[^"\s<]+',
                    page,
                )
                self.assertTrue(app_links)
                self.assertTrue(
                    all(f"id{base.APP_ID}" in link for link in app_links)
                )
                self.assertLess(disclosure, page.index(app_links[0]))

    def test_non_managed_control_content_is_preserved_exactly(self):
        for locale, page in self.pages.items():
            with self.subTest(locale=locale):
                control = base.render_page(
                    locale,
                    app_public=True,
                    alternate_locales=education_qa.CANARY_LOCALES,
                )
                self.assertEqual(
                    control,
                    education_qa.strip_managed_blocks(page),
                )

    def test_manifest_is_fail_closed_and_has_rc_d_e_c_dl_gates(self):
        manifest = self.manifest
        self.assertEqual(
            education_qa.EXPERIMENT_SCHEMA,
            manifest["$schema"],
        )
        self.assertEqual(
            "BLOCKED_NOT_DEPLOYABLE",
            manifest["generation_status"],
        )
        self.assertGreaterEqual(
            manifest["deterministic_validation_case_count"],
            100,
        )
        self.assertEqual(
            {"RC", "D", "E", "C", "DL"},
            set(manifest["layers"]),
        )
        self.assertFalse(manifest["layers"]["RC"]["counts_as_exposure"])
        self.assertIn(
            "never counts as exposure",
            manifest["measurement_gates"]["exposure_definition"],
        )
        self.assertEqual(
            "BLOCK",
            manifest["gates"]["exact_50_locale_deployment_gate"],
        )
        self.assertEqual(
            40,
            len(
                manifest["supported_locale_roster"][
                    "missing_exact_50_locales"
                ]
            ),
        )
        forbidden = set(
            manifest["measurement_gates"]["forbidden_actions"]
        )
        self.assertTrue(
            {
                "URL Inspection",
                "IndexNow",
                "Search Console write",
                "HTTP POST",
                "deploy",
                "push",
            }.issubset(forbidden)
        )

    def test_generation_is_byte_identical_across_two_runs(self):
        first_manifest = experiment.build()
        first = {
            path.relative_to(experiment.OUTPUT): path.read_bytes()
            for path in experiment.OUTPUT.rglob("*")
            if path.is_file()
        }
        second_manifest = experiment.build()
        second = {
            path.relative_to(experiment.OUTPUT): path.read_bytes()
            for path in experiment.OUTPUT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first, second)

    def test_generator_contains_no_network_or_publish_primitive(self):
        source = Path(experiment.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "urllib.request",
            "import requests",
            "from requests",
            "requests.post(",
            "httpx.",
            "subprocess.",
            "urlopen(",
            ".post(",
            "searchconsole.",
            "urlinspection.",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source, forbidden)


if __name__ == "__main__":
    unittest.main()
