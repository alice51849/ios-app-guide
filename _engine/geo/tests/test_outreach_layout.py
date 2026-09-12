from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gen_app_decision_cards
import gen_app_store_facts
import gen_app_store_qr_ctas
import gen_guide_design
import gen_mobile_store_ctas
import gen_outreach_layout
from outreach_bidi import isolate_document, isolate_text, transparent_bidi


class BidiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.isolates = []

    def handle_starttag(self, tag, attrs):
        if tag == "bdi":
            self.isolates.append(dict(attrs))


class OutreachLayoutTests(unittest.TestCase):
    def test_external_ctas_and_captions_wrap_without_hidden_text(self):
        for css in (
            gen_guide_design.STYLESHEET,
            gen_app_decision_cards.STYLESHEET,
            gen_app_store_qr_ctas.CSS,
            gen_app_store_facts.ASSET_SOURCE,
        ):
            self.assertNotIn("white-space: nowrap", css)
            self.assertNotIn("white-space:nowrap", css)
            self.assertNotIn("text-overflow: ellipsis", css)
            if css != gen_guide_design.STYLESHEET:
                self.assertNotIn("overflow-x: auto", css)
            self.assertRegex(css, r"overflow-wrap:\s*anywhere")
        self.assertIn("min-block-size: 3rem", gen_guide_design.STYLESHEET)
        self.assertIn("min-block-size: 2.75rem", gen_app_decision_cards.STYLESHEET)
        self.assertIn("min-height:44px", gen_app_store_facts.ASSET_SOURCE)
        self.assertIn("min-height:48px", gen_mobile_store_ctas.SCRIPT)
        # Existing wide data tables retain their deliberate scroll surface.
        self.assertIn("overflow-x: auto", gen_guide_design.STYLESHEET)

    def test_script_leading_is_native_and_latin_defaults_are_preserved(self):
        self.assertIn("var(--guide-heading-leading, 1.14)", gen_guide_design.STYLESHEET)
        self.assertIn("var(--guide-cta-leading, 1.2)", gen_guide_design.STYLESHEET)
        self.assertIn("--guide-heading-leading: 1.5", gen_guide_design.STYLESHEET)
        self.assertIn("--guide-card-copy-leading: 1.7", gen_guide_design.STYLESHEET)
        for locale in ("th", "ar", "ur"):
            self.assertIn(f"html:lang({locale})", gen_guide_design.STYLESHEET)
        self.assertIn("letter-spacing: normal", gen_guide_design.STYLESHEET)

    def test_mixed_direction_changes_markup_not_content_or_price(self):
        for language in ("ar-SA", "ur-PK", "he"):
            source = (
                f'<html lang="{language}" dir="ltr"><head><title>App 37</title>'
                '<script type="application/ld+json">{"name":"ABC","price":"5.99"}</script>'
                '<style>.sample{content:"ABC 37"}</style></head><body>'
                '<main><h1>العنوان App &amp; More: 37</h1>'
                '<p>ٹیسٹ A&amp;B و ۲۶ نام</p><p>בדיקה App Store כאן</p>'
                '<a href="https://apps.apple.com/sa/app/id6775773117?pt=1&amp;ct=kept" title="ABC 37">تحميل App 37</a>'
                '<data value="19.99">١٩٫٩٩ ر.س.</data><pre>do not wrap ABC</pre>'
                '<p><bdi dir="ltr">Existing ABC</bdi></p></main></body></html>'
            )
            result = isolate_document(source)
            self.assertIn('dir="rtl"', result)
            self.assertEqual(gen_outreach_layout.content_signature(source), gen_outreach_layout.content_signature(result))
            self.assertIn('<title>App 37</title>', result)
            self.assertIn('{"name":"ABC","price":"5.99"}', result)
            self.assertIn("<pre>do not wrap ABC</pre>", result)
            self.assertEqual(result, isolate_document(result))
            parser = BidiParser()
            parser.feed(result)
            self.assertTrue(parser.isolates)
            self.assertTrue(all(row["dir"] == "ltr" for row in parser.isolates))

    def test_ltr_and_market_availability_markup_stays_identical(self):
        for locale in ("bn-BD", "ca", "de-DE", "ja", "ko", "zh-Hant", "th"):
            source = (
                f'<html lang="{locale}"><body><main>'
                '<p data-market-state="not_available">Unchanged label ABC 37</p>'
                '<a href="/alternatives/">Existing fallback</a>'
                "</main></body></html>"
            )
            self.assertEqual(source, isolate_document(source))

    def test_entities_comments_and_inline_punctuation_are_lossless(self):
        for text in ("A&amp;B 37", "App&#32;Store 26", "&#x41;BC", "未知 &unknown; اختبار", "בדיקה App\u00a0Store 26"):
            result = isolate_text(text)
            self.assertEqual(text, transparent_bidi(result))
        source = '<html lang="ar"><body><!-- App 26 --><p>اختبار <em>App</em>: 26.</p></body></html>'
        result = isolate_document(source)
        self.assertIn("<!-- App 26 -->", result)
        self.assertEqual(gen_outreach_layout.content_signature(source), gen_outreach_layout.content_signature(result))

    def test_existing_text_extractors_do_not_insert_spaces_at_bidi_boundaries(self):
        source = 'الفئة <bdi dir="ltr">AI Brief</bdi>: اختبار'
        self.assertEqual("الفئة AI Brief: اختبار", gen_app_decision_cards._plain_text(source))
        self.assertEqual("الفئة AI Brief: اختبار", gen_mobile_store_ctas._plain_label(source))
        source = "A<bdi dir=\"ltr\">&amp;B</bdi>"
        self.assertEqual("A&B", gen_mobile_store_ctas._plain_label(source))

    def test_asset_regeneration_is_idempotent_and_preserves_all_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for locale in ("ar-SA", "ur-PK", "he", "th", "de-DE"):
                relative = Path(locale) / "test.html"
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text(f'<html lang="{locale}"><body><main><p>متن App 26</p></main></body></html>')
                paths.append(relative)
            signatures = {relative: gen_outreach_layout.content_signature((root / relative).read_text()) for relative in paths}
            first = gen_outreach_layout.generate(root, paths)
            before = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
            second = gen_outreach_layout.generate(root, paths)
            self.assertEqual(5, first["assets"])
            self.assertEqual(0, first["copy_changes"])
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(before, {path: path.stat().st_mtime_ns for path in before})
            for relative in paths:
                self.assertEqual(signatures[relative], gen_outreach_layout.content_signature((root / relative).read_text()))
            with self.assertRaises(ValueError):
                gen_outreach_layout.generate(root, ["../outside.html"])

    def test_sticky_bar_reserves_actual_height_and_honours_reduced_motion(self):
        script = gen_mobile_store_ctas.SCRIPT
        self.assertIn("ResizeObserver", script)
        self.assertIn("--mobile-store-cta-height", script)
        self.assertIn("height !== measuredHeight", script)
        self.assertIn("white-space:normal", script)
        self.assertIn("prefers-reduced-motion:reduce", script)
        self.assertIn("transition:none", script)
        self.assertNotIn("setInterval", script)
        self.assertNotIn("fontSize =", script)
        self.assertIn("transform: none", gen_guide_design.STYLESHEET)
        self.assertIn("transform: none", gen_app_decision_cards.STYLESHEET)


if __name__ == "__main__":
    unittest.main()
