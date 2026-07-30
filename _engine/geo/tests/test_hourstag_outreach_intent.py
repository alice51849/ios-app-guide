#!/usr/bin/env python3

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import answer_deep  # noqa: E402
import answer_facts  # noqa: E402
import answer_personas  # noqa: E402
import app_install_decision_routes  # noqa: E402
import build_pages_i18n  # noqa: E402
import cleanup_localized_assets  # noqa: E402
import gen_smart_app_banners  # noqa: E402
import queries  # noqa: E402


class HoursTagOutreachIntentTests(unittest.TestCase):
    @staticmethod
    def _literal_assignment(path: Path, name: str):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
        raise AssertionError(f"{name} not found in {path}")

    def test_original_hourstag_never_targets_timesheets_or_purchase_before(self):
        corpus = "\n".join(queries.ALL["hourstag"]).lower()
        for mismatched_intent in (
            "timesheet",
            "work hours tracker app for freelancers",
            "before buying",
            "before you buy",
        ):
            self.assertNotIn(mismatched_intent, corpus)
        self.assertIn(
            "best app to track where my money goes and save more",
            corpus,
        )
        self.assertIn(
            "app that shows purchases in hours of work",
            corpus,
        )

    def test_original_and_lite_personas_remain_distinct(self):
        original = json.dumps(
            answer_personas.PERSONAS["hourstag"],
            ensure_ascii=False,
        ).lower()
        lite = json.dumps(
            answer_personas.PERSONAS["hourstaglite"],
            ensure_ascii=False,
        ).lower()
        self.assertNotIn("before buying", original)
        self.assertNotIn("purchase-before", original)
        self.assertIn("purchase-before", lite)

    def test_original_deep_answers_do_not_claim_purchase_before_workflow(self):
        original = json.dumps(
            [
                item
                for item in answer_deep.DEEP_ITEMS
                if item["app_key"] == "hourstag"
            ],
            ensure_ascii=False,
        ).lower()
        self.assertNotIn("before buying", original)
        self.assertNotIn("before you buy", original)
        self.assertNotIn("purchase decision", original)

    def test_hourstag_spending_facts_never_use_travel_currency_or_checkout(self):
        facts = answer_facts._scenario_facts(
            "simple private expense awareness app no subscription",
            "hourstag",
            "HoursTag",
            ["Pay once", "Private", "No tracking"],
        )
        serialized = json.dumps(facts, ensure_ascii=False).lower()
        self.assertIn("record and review existing spending", serialized)
        self.assertIn("log a completed expense", serialized)
        self.assertNotIn("travel currenc", serialized)
        self.assertNotIn("before impulse", serialized)
        self.assertNotIn("before you buy", serialized)

    def test_guides_routes_and_social_keep_existing_spending_contract(self):
        guide_copy = self._literal_assignment(
            GEO / "aeo_guide_free_batch2.py",
            "C",
        )["hourstag"]
        serialized = json.dumps(guide_copy, ensure_ascii=False).lower()
        self.assertIn("completed expenses", serialized)
        self.assertIn("record completed expenses", serialized)
        self.assertNotIn("before you buy", serialized)
        self.assertIn(
            "hourstag",
            app_install_decision_routes.INTENT_CONTEXT_ONLY_KEYS,
        )

        social_path = (
            GEO.parent / "social" / "videogen" / "captions.py"
        )
        if social_path.exists():
            social_copy = self._literal_assignment(
                social_path,
                "THREADS_PROMPTS",
            )["hourstag"].lower()
            self.assertIn("completed expense", social_copy)
            self.assertNotIn("before you buy", social_copy)

    def test_web_description_and_cta_pipeline_preserve_truthful_redirects(self):
        for locale in ("en-AU", "en-CA", "en-GB"):
            description = build_pages_i18n.sanitize_description(
                "hourstag",
                locale,
                "Set your pay once and see the real hours before you buy.",
            ).lower()
            self.assertIn("record completed expenses", description)
            self.assertNotIn("before you buy", description)

        with tempfile.TemporaryDirectory() as directory:
            redirect = Path(directory) / "hourstag.html"
            redirect.write_text(
                '<meta name="robots" content="noindex,follow">'
                '<meta http-equiv="refresh" content="0;url=/guides/hourstag.html">',
                encoding="utf-8",
            )
            self.assertTrue(
                gen_smart_app_banners._is_noindex_redirect(redirect)
            )

    def test_retired_mismatched_pages_redirect_to_existing_spending_workflow(self):
        destination_slug = (
            "best-app-to-track-where-my-money-goes-and-save-more"
        )
        retired_slug = "simple-timesheet-app-to-log-work-hours"
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            root_answers = pages / "answers"
            localized_answers = pages / "zh-Hant" / "answers"
            root_answers.mkdir(parents=True)
            localized_answers.mkdir(parents=True)
            for answers in (root_answers, localized_answers):
                (answers / f"{destination_slug}.html").write_text(
                    "current",
                    encoding="utf-8",
                )
                (answers / f"{retired_slug}.html").write_text(
                    "mismatched",
                    encoding="utf-8",
                )

            changed = (
                cleanup_localized_assets.reconcile_retired_answer_redirects(
                    pages,
                    [pages / "zh-Hant"],
                )
            )

            root_redirect = (
                root_answers / f"{retired_slug}.html"
            ).read_text(encoding="utf-8")
            localized_redirect = (
                localized_answers / f"{retired_slug}.html"
            ).read_text(encoding="utf-8")

        self.assertEqual(2, changed)
        self.assertIn("noindex,follow", root_redirect)
        self.assertIn(
            f"/answers/{destination_slug}.html",
            root_redirect,
        )
        self.assertIn(
            f"/zh-Hant/answers/{destination_slug}.html",
            localized_redirect,
        )

    def test_retired_page_uses_localized_app_when_answer_is_not_localized(self):
        retired_slug = "simple-timesheet-app-to-log-work-hours"
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "answers").mkdir()
            (pages / "zh-Hant" / "answers").mkdir(parents=True)
            (pages / "answers" / "best-app-to-track-where-my-money-goes-and-save-more.html").write_text(
                "current",
                encoding="utf-8",
            )
            (pages / "zh-Hant" / "hourstag.html").write_text(
                "localized app",
                encoding="utf-8",
            )
            retired = (
                pages / "zh-Hant" / "answers" / f"{retired_slug}.html"
            )
            retired.write_text("mismatched", encoding="utf-8")

            cleanup_localized_assets.reconcile_retired_answer_redirects(
                pages,
                [pages / "zh-Hant"],
            )
            rendered = retired.read_text(encoding="utf-8")

        self.assertIn("/zh-Hant/hourstag.html", rendered)
        self.assertNotIn(
            "/answers/best-app-to-track-where-my-money-goes-and-save-more.html",
            rendered,
        )

    def test_localized_hourstag_guides_redirect_to_verified_english_guide(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            localized = pages / "zh-Hant"
            guide = localized / "guides" / "hourstag.html"
            guide.parent.mkdir(parents=True)
            guide.write_text("stale localized guide", encoding="utf-8")

            changed = (
                cleanup_localized_assets.reconcile_hourstag_guide_redirects(
                    pages,
                    [localized],
                )
            )
            rendered = guide.read_text(encoding="utf-8")

        self.assertEqual(1, changed)
        self.assertIn("noindex,follow", rendered)
        self.assertIn("/guides/hourstag.html", rendered)

    def test_retired_references_choose_existing_locale_safe_destination(self):
        destination_slug = (
            "best-app-to-track-where-my-money-goes-and-save-more"
        )
        retired_slug = "simple-timesheet-app-to-log-work-hours"
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "answers").mkdir()
            (pages / "zh-Hant").mkdir()
            (pages / "de-DE" / "answers").mkdir(parents=True)
            (pages / "answers" / f"{destination_slug}.html").write_text(
                "current",
                encoding="utf-8",
            )
            (pages / "zh-Hant" / "hourstag.html").write_text(
                "localized app",
                encoding="utf-8",
            )
            (
                pages
                / "de-DE"
                / "answers"
                / f"{destination_slug}.html"
            ).write_text("localized answer", encoding="utf-8")
            source = "\n".join(
                (
                    f"{cleanup_localized_assets.SITE}/answers/{retired_slug}.html",
                    f"{cleanup_localized_assets.SITE}/zh-Hant/answers/{retired_slug}.html",
                    f"{cleanup_localized_assets.SITE}/de-DE/answers/{retired_slug}.html",
                )
            )

            rendered = cleanup_localized_assets.replace_retired_answer_slugs(
                source,
                pages,
            )

        self.assertNotIn(retired_slug, rendered)
        self.assertIn(f"/answers/{destination_slug}.html", rendered)
        self.assertIn("/zh-Hant/hourstag.html", rendered)
        self.assertIn(
            f"/de-DE/answers/{destination_slug}.html",
            rendered,
        )
        self.assertNotIn(
            f"/zh-Hant/answers/{destination_slug}.html",
            rendered,
        )

    def test_retired_references_are_rewritten_in_public_data_formats(self):
        destination_slug = (
            "best-app-to-track-where-my-money-goes-and-save-more"
        )
        retired_slug = "simple-timesheet-app-to-log-work-hours"
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "answers").mkdir()
            (pages / "zh-Hant").mkdir()
            (pages / "data").mkdir()
            (pages / "_engine").mkdir()
            (pages / "answers" / f"{destination_slug}.html").write_text(
                "current",
                encoding="utf-8",
            )
            (pages / "zh-Hant" / "hourstag.html").write_text(
                "localized app",
                encoding="utf-8",
            )
            retired_url = (
                f"{cleanup_localized_assets.SITE}/zh-Hant/answers/"
                f"{retired_slug}.html"
            )
            output_paths = (
                pages / "data" / "routes.json",
                pages / "sitemap.xml",
                pages / "README.md",
            )
            for path in output_paths:
                path.write_text(retired_url, encoding="utf-8")
            engine_fixture = pages / "_engine" / "fixture.md"
            engine_fixture.write_text(retired_url, encoding="utf-8")
            topic_page = pages / "topic.html"
            topic_page.write_text(
                '<script type="application/ld+json">'
                '{"@type":"ItemList","numberOfItems":2,'
                '"itemListElement":['
                '{"@type":"ListItem","position":1,'
                f'"url":"{retired_url}"'
                "},"
                '{"@type":"ListItem","position":2,'
                f'"url":"{cleanup_localized_assets.SITE}/zh-Hant/hourstag.html"'
                "}]}</script>",
                encoding="utf-8",
            )

            changed = (
                cleanup_localized_assets.reconcile_retired_answer_references(
                    pages
                )
            )

            rendered = [
                path.read_text(encoding="utf-8") for path in output_paths
            ]
            untouched = engine_fixture.read_text(encoding="utf-8")
            topic = topic_page.read_text(encoding="utf-8")

        self.assertEqual(4, changed)
        self.assertTrue(
            all("/zh-Hant/hourstag.html" in item for item in rendered)
        )
        self.assertTrue(all(retired_slug not in item for item in rendered))
        self.assertIn('"numberOfItems":1', topic)
        self.assertEqual(1, topic.count("/zh-Hant/hourstag.html"))
        self.assertIn(retired_slug, untouched)


if __name__ == "__main__":
    unittest.main()
