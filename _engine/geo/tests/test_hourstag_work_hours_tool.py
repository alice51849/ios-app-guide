from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import hourstag_work_hours_tool as tool  # noqa: E402


class HoursTagWorkHoursToolTests(unittest.TestCase):
    def test_every_declared_locale_has_complete_native_copy(self):
        self.assertEqual(set(tool.ALT_LOCALES), set(tool.COPY))
        english_keys = set(tool.COPY["en"])
        headings = set()
        for locale, copy in tool.COPY.items():
            self.assertEqual(english_keys, set(copy), locale)
            self.assertEqual(set(tool.INCOME_MODES), set(copy["income_modes"]), locale)
            self.assertEqual(set(tool.DECISION_TAGS), set(copy["decision_tags"]), locale)
            self.assertEqual(set(tool.DECISION_TAGS), set(copy["decision_prompt"]), locale)
            self.assertEqual(4, len(copy["faq"]), locale)
            headings.add(copy["heading"])
        self.assertEqual(len(tool.COPY), len(headings))
        self.assertNotIn("Calculadora", tool.COPY["ja"]["title"])
        self.assertNotIn("Calculadora", tool.COPY["ko"]["title"])
        self.assertNotIn("Calculadora", tool.COPY["de-DE"]["title"])
        self.assertNotIn(
            "上载",
            json.dumps(tool.COPY["zh-Hans"], ensure_ascii=False),
        )
        for locale in (
            "en",
            "zh-Hant",
            "zh-Hans",
            "ja",
            "ko",
            "fr-FR",
            "de-DE",
            "es-ES",
            "pt-BR",
        ):
            description = tool.COPY[locale]["description"].casefold()
            self.assertTrue(
                any(
                    phrase in description
                    for phrase in (
                        "financial advice",
                        "理財建議",
                        "理财建议",
                        "金融助言",
                        "금융 조언",
                        "conseil financier",
                        "finanzberatung",
                        "asesoramiento financiero",
                        "orientação financeira",
                    )
                ),
                locale,
            )

    def test_pages_are_private_bilingual_and_ai_callable(self):
        english = tool.render_page("en", app_public=False)
        chinese = tool.render_page("zh-Hant", app_public=False)
        for page in (english, chinese):
            self.assertIn('"@type":"WebApplication"', page)
            self.assertIn('"dateModified":"2026-07-17"', page)
            self.assertIn("document.modelContext?.registerTool", page)
            self.assertIn('name: "calculate_purchase_work_time"', page)
            self.assertIn(
                "annotations: {readOnlyHint: true, untrustedContentHint: false}",
                page,
            )
            self.assertIn("local_only_calculation: true", page)
            self.assertIn(
                "no_purchase_recommendation_or_savings_promise: true",
                page,
            )
            self.assertIn(tool.APP_STORE_SOURCE, page)
            self.assertIn(tool.WEBMCP_SOURCE, page)
            self.assertNotIn('"@type":"MobileApplication"', page)
            self.assertNotIn(f"id{tool.APP_ID}?ct=iag_hours_", page)
            self.assertNotIn('type="file"', page)
            self.assertNotIn("<textarea", page)
            self.assertNotIn("fetch(", page)
            self.assertNotIn("XMLHttpRequest", page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("sessionStorage", page)
            self.assertNotIn("navigator.modelContext", page)
            self.assertIn("config.validationError", page)
            self.assertIn("required>", page)
            for locale in tool.ALT_LOCALES:
                self.assertIn(f'hreflang="{locale}"', page)
        self.assertIn("never decides whether you should buy", english)
        self.assertIn("不替你決定該不該買", chinese)

    def test_public_pages_use_clean_direct_app_store_links(self):
        for locale in tool.COPY:
            page = tool.render_page(locale, app_public=True)
            # Direct Apple link only. It carries this page's own campaign
            # token when a provider token is configured, and nothing else:
            # no redirector, no affiliate, no third-party tracker.
            direct = tool.appstore_url(
                tool.APP_KEY,
                f"iag_hours_{locale.lower().replace('-', '_')}",
            )
            self.assertIn(f"id{tool.APP_ID}", page)
            self.assertIn(
                f'<meta name="apple-itunes-app" content="app-id={tool.APP_ID}">',
                page,
            )
            self.assertIn(f'href="{html.escape(direct, quote=True)}"', page)
            schemas = [
                json.loads(payload)
                for payload in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>',
                    page,
                    re.S,
                )
            ]
            mobile = next(
                item for item in schemas if item["@type"] == "MobileApplication"
            )
            self.assertEqual(tool.appstore_url(tool.APP_KEY), mobile["installUrl"])
            self.assertNotIn("aggregateRating", mobile)
            self.assertNotIn("offers", mobile)

    def test_webmcp_schema_is_strict_bounded_and_side_effect_free(self):
        schema = tool.webmcp_input_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(list(tool.INCOME_MODES), schema["properties"]["income_mode"]["enum"])
        self.assertEqual(
            list(tool.DECISION_TAGS),
            schema["properties"]["decision_tag"]["enum"],
        )
        self.assertEqual(
            set(schema["properties"]),
            set(schema["required"]),
        )
        self.assertEqual(
            744,
            schema["properties"]["paid_hours_per_month"]["maximum"],
        )
        self.assertEqual(
            24,
            schema["properties"]["workday_hours"]["maximum"],
        )
        self.assertEqual(
            100,
            schema["properties"]["saving_rate_percent"]["maximum"],
        )
        self.assertEqual(1, tool.SCRIPT.count("function calculate(input)"))
        self.assertIn("const result = calculate(readForm());", tool.SCRIPT)
        self.assertIn(
            "if (!(error instanceof TypeError || error instanceof RangeError))",
            tool.SCRIPT,
        )
        execute = tool.SCRIPT.split(
            "execute: async (input) => {",
            1,
        )[1].split("return JSON.stringify(result);", 1)[0]
        for mutation in (
            "textContent",
            "innerHTML",
            "appendChild",
            "replaceChildren",
            "scroll",
            "fetch(",
            "localStorage",
        ):
            self.assertNotIn(mutation, execute)

    def test_builds_all_locale_pages_updates_indexes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            anchor = (
                '<article class="card third" data-tool="'
                'private-daily-checklist-planner"><h2><a href="'
                'private-daily-checklist-planner.html">Daily plan</a></h2>'
                "<p>Planner.</p></article>"
            )
            indexes = []
            for locale in tool.COPY:
                tools = pages / "tools"
                if locale != "en":
                    tools = pages / locale / "tools"
                tools.mkdir(parents=True)
                index = tools / "index.html"
                index.write_text(
                    f'<main><section class="wrap grid">{anchor}</section></main>',
                    encoding="utf-8",
                )
                indexes.append(index)
            urls = tool.build(pages, app_public=False)
            self.assertEqual(len(tool.COPY), len(urls))
            english = pages / "tools" / f"{tool.SLUG}.html"
            self.assertTrue(english.exists())
            for locale in tool.COPY:
                page = pages / "tools" / f"{tool.SLUG}.html"
                if locale != "en":
                    page = pages / locale / "tools" / f"{tool.SLUG}.html"
                self.assertTrue(page.exists(), locale)
                self.assertIn(
                    f'<html lang="{locale}">',
                    page.read_text(encoding="utf-8"),
                )
            for index in indexes:
                self.assertEqual(
                    1,
                    index.read_text(encoding="utf-8").count(
                        f"{tool.SLUG}.html"
                    ),
                )
            stable_mtime = 1_700_000_000_000_000_000
            os.utime(english, ns=(stable_mtime, stable_mtime))
            first_bytes = english.read_bytes()
            tool.build(pages, app_public=False)
            self.assertEqual(first_bytes, english.read_bytes())
            self.assertEqual(stable_mtime, english.stat().st_mtime_ns)

    def test_automation_wiring_is_persistent_when_pages_are_available(self):
        publish = (GEO / "publish.py").read_text(encoding="utf-8")
        self.assertEqual(1, publish.count("hourstag_work_hours_tool.py"))
        workflow = GEO / "pages" / ".github" / "workflows" / "geo-daily.yml"
        if not workflow.exists():
            self.skipTest("Pages worktree is not linked in this checkout")
        self.assertEqual(
            1,
            workflow.read_text(encoding="utf-8").count(
                "hourstag_work_hours_tool.py"
            ),
        )


if __name__ == "__main__":
    unittest.main()
