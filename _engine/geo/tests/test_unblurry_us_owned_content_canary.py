#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import os
import re
import sys
import unittest
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
ROOT = os.path.dirname(GEO)
sys.path.insert(0, GEO)
sys.path.insert(0, os.path.join(ROOT, "social"))

import aeo_answers  # noqa: E402
import answer_hreflang  # noqa: E402
import gen_store_attribution  # noqa: E402


QUESTION = "how to choose a unblur photo app"
SLUG = "how-to-choose-a-unblur-photo-app"
RELATIVE = f"answers/{SLUG}.html"
TOKEN = "geo_unb_us_choose_260830"


def json_ld(document: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        document,
        flags=re.DOTALL,
    )
    return [json.loads(block) for block in blocks]


class UnblurryQueryCampaignTests(unittest.TestCase):
    def test_us_query_tokens_are_legal_unique_and_reversible(self):
        tokens = list(gen_store_attribution.US_QUERY_CAMPAIGNS.values())
        self.assertEqual(1, len(tokens))
        self.assertEqual(len(tokens), len(set(tokens)))
        for token in tokens:
            self.assertLessEqual(len(token), gen_store_attribution.MAX_TOKEN)
            self.assertRegex(token, r"^[A-Za-z0-9_]+$")
            self.assertEqual(
                (gen_store_attribution.ASK, "us"),
                gen_store_attribution.parse_campaign_token(token),
            )

    def test_only_exact_us_routes_receive_query_tokens(self):
        self.assertEqual(
            TOKEN, gen_store_attribution.campaign_token(RELATIVE)
        )
        unchanged = (
            "answers/can-you-actually-unblur-a-photo.html",
            "answers/is-a-pay-once-photo-enhancer-worth-it-vs-remini.html",
            f"fr-FR/{RELATIVE}",
        )
        for route in unchanged:
            with self.subTest(route=route):
                self.assertEqual(
                    "geo_ask",
                    gen_store_attribution.campaign_token(route),
                )

    def test_unregistered_pages_remain_byte_identical_to_remote_base(self):
        expected = {
            "can-you-actually-unblur-a-photo.html": (
                "bfd383881a58e609b491dd76274b9379ed79aded2e6796415085cb3bd00e0c03"
            ),
            "is-a-pay-once-photo-enhancer-worth-it-vs-remini.html": (
                "abf00c83a12a5b4cc1d28cfded734793997b637150f6cb7c1f922b95a9f81fb6"
            ),
        }
        for name, digest in expected.items():
            with self.subTest(page=name):
                data = (
                    aeo_answers.PAGES_ROOT / "answers" / name
                ).read_bytes()
                self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        qr = (
            aeo_answers.PAGES_ROOT
            / "assets/app-store-qr/id6782275018-25eda57cdbabc587dca5.svg"
        ).read_bytes()
        self.assertEqual(
            "0b7bf33f7494d743da72a1f8f246b31f91061705be51ef764c044bd8b6e10123",
            hashlib.sha256(qr).hexdigest(),
        )


class UnblurryDecisionPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = aeo_answers.default_content(QUESTION, "unblurry")
        cls.content = aeo_answers.normalized_content(
            raw, QUESTION, "unblurry"
        )
        cls.document = aeo_answers.render_page(
            QUESTION, "unblurry", cls.content
        )

    def test_first_party_non_ranking_and_honest_limits_are_visible(self):
        self.assertIn("not an independent ranking", self.document)
        self.assertIn("does not guarantee restoration", self.document)
        self.assertIn("cannot recreate detail that was not captured", self.document)
        self.assertIn("1280 px", self.document)
        self.assertIn("two regular saves per day", self.document)
        self.assertIn("one AI Clarity trial", self.document)

    def test_deprecated_answer_schemas_are_not_emitted(self):
        types = {
            node.get("@type")
            for node in json_ld(self.document)
            if isinstance(node, dict)
        }
        self.assertIn("Article", types)
        self.assertNotIn("FAQPage", types)
        self.assertNotIn("HowTo", types)
        self.assertNotIn("https://schema.org/Question", self.document)
        self.assertIn("<h2>Decision checks</h2>", self.document)

    def test_en_us_identity_and_campaign_url_are_separate(self):
        self.assertIn('<html lang="en-US">', self.document)
        self.assertNotIn('hreflang="en-US"', self.document)
        self.assertIn(
            '<link rel="canonical" '
            'href="https://alice51849.github.io/ios-app-guide/'
            f'{RELATIVE}">',
            self.document,
        )
        pairs = answer_hreflang.extract_pairs(self.document)
        self.assertEqual("en", pairs[0][0])
        self.assertEqual("x-default", pairs[-1][0])
        self.assertEqual(
            ["en"]
            + answer_hreflang.existing_locales(
                aeo_answers.PAGES_ROOT, SLUG
            )
            + ["x-default"],
            [locale for locale, _ in pairs],
        )
        tracked = {
            url
            for url in re.findall(
                r'href="([^"]*apps\.apple\.com[^"]*)"', self.document
            )
            if "id6782275018" in url and "ct=" in url
        }
        self.assertTrue(tracked)
        for url in tracked:
            parsed = urlparse(url.replace("&amp;", "&"))
            self.assertEqual("apps.apple.com", parsed.netloc)
            self.assertTrue(parsed.path.endswith("/id6782275018"))
            query = parse_qs(parsed.query)
            self.assertEqual(["118326163"], query.get("pt"))
            self.assertEqual([TOKEN], query.get("ct"))
            self.assertEqual(["8"], query.get("mt"))

        software = next(
            node
            for node in json_ld(self.document)
            if node.get("@type") == "SoftwareApplication"
        )
        self.assertEqual(
            "https://apps.apple.com/app/id6782275018", software["url"]
        )
        self.assertEqual(software["url"], software["installUrl"])

    def test_verified_feature_rows_survive_normalization(self):
        self.assertEqual(4, len(self.content["comparison_rows"]))
        self.assertEqual(
            "Severe smear or missing text",
            self.content["comparison_rows"][2]["need"],
        )
        self.assertEqual(3, len(self.content["sources"]))

    def test_render_is_deterministic(self):
        rerendered = aeo_answers.render_page(
            QUESTION, "unblurry", self.content
        )
        self.assertEqual(self.document, rerendered)

    def test_schema_flags_do_not_change_other_pages(self):
        question = "can you actually unblur a photo"
        content = aeo_answers.normalized_content(
            aeo_answers.default_content(question, "unblurry"),
            question,
            "unblurry",
        )
        document = aeo_answers.render_page(
            question, "unblurry", content
        )
        types = {
            node.get("@type")
            for node in json_ld(document)
            if isinstance(node, dict)
        }
        self.assertIn("FAQPage", types)
        self.assertIn("HowTo", types)


if __name__ == "__main__":
    unittest.main()
