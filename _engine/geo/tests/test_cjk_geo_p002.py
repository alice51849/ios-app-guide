from __future__ import annotations

import copy
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_pages_i18n as pages
import cjk_geo_p002 as repair
import cjk_geo_p002_candidates as candidates
from official_locales import OFFICIAL_LOCALES

EXPECTED_CELLS = {
    ("lumibopomofopro", "zh-Hans"), ("lumibopomofopro", "id"),
    ("lumibopomofopro", "ms"), ("lumibopomofopro", "th"),
    ("lumibopomofopro", "vi"), ("lumibopomofopro", "ar-SA"),
    ("lumiletterspro", "zh-Hans"), ("lumiletterspro", "id"),
    ("lumiletterspro", "ms"), ("lumiletterspro", "th"),
    ("lumiletterspro", "vi"), ("lumiletterspro", "ar-SA"),
}
TERM = re.compile(
    r"Lumi Bopomofo Pro(?:: Zhuyin)?|Lumi Letters Pro(?:: ABC Phonics)?|"
    r"Lumi Studio|Bopomofo|Zhuyin|Montessori|Lumi|ABC|Pro|注音|ㄅㄆㄇㄈ"
)


def script_ratio(text, locale):
    text = TERM.sub("", text)
    letters = [character for character in text if character.isalpha()]
    patterns = {
        "zh-Hans": r"[\u3400-\u9fff]", "zh-Hant": r"[\u3400-\u9fff]",
        "ja": r"[\u3040-\u30ff\u3400-\u9fff]",
        "ko": r"[\uac00-\ud7af\u1100-\u11ff]",
        "th": r"[\u0e00-\u0e7f]",
        "ar-SA": r"[\u0600-\u06ff]", "ur-PK": r"[\u0600-\u06ff]",
    }
    if locale in patterns:
        count = sum(bool(re.fullmatch(patterns[locale], character)) for character in letters)
    else:
        count = sum("LATIN" in unicodedata.name(character, "") for character in letters)
    return count / max(1, len(letters))


class PageDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {}
        self.links = []
        self.isolates = []
        self.text = []
        self.jsonld = []
        self.script = None

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "html":
            self.root = attributes
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if tag == "bdi":
            self.isolates.append(attributes)
        if tag == "script":
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)
        else:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.jsonld.append(json.loads("".join(self.script)))
            self.script = None


class CJKP002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live_state = Path(pages.PAGES) / ".appstore_live_state.json"
        cls.keys = candidates.live_keys(json.loads(cls.live_state.read_text())["live_ids"])
        cls.inventory = candidates.inventory(cls.keys)
        cls.work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        cls.output = Path(cls.work.name) / "candidate"
        cls.generation = candidates.generate(cls.live_state, cls.output)

    def test_exact_twelve_independent_counterexamples(self):
        self.assertEqual(EXPECTED_CELLS, repair.TARGET_CELLS)
        self.assertEqual(12, len(EXPECTED_CELLS))
        for key, locale in EXPECTED_CELLS:
            raw = pages.load_app_locales(key)[locale]
            self.assertEqual(1, raw["description"].count(repair.ENGLISH_PARAGRAPHS[key]))
            translated = pages.external_localized_values(key, locale)
            self.assertNotIn("Pro edition", translated["description"])
            self.assertIn(repair.NATIVE_PARAGRAPHS[key][locale], translated["description"])

    def test_exact_47_by_10_inventory_and_only_twelve_pages(self):
        self.assertEqual(470, len(self.inventory))
        cells = {(row["app_key"], row["locale"]) for row in self.inventory}
        self.assertEqual({(key, locale) for key in self.keys for locale in repair.AUDIT_LOCALES}, cells)
        changed = {(row["app_key"], row["locale"]) for row in self.inventory if row["repair_scope"] == "P0-02"}
        self.assertEqual(EXPECTED_CELLS, changed)
        files = {str(path.relative_to(self.output)) for path in self.output.rglob("*.html")}
        self.assertEqual({f"{locale}/{key}.html" for key, locale in EXPECTED_CELLS}, files)
        self.assertEqual(12, self.generation["generated_pages"])
        self.assertEqual(458, self.generation["unchanged_cells"])
        self.assertTrue(all(row["social_receipt"] is None for row in self.inventory))

    def test_only_description_changes_and_no_source_mutation(self):
        actual = set()
        for key in self.keys:
            source = pages.load_app_locales(key)
            snapshot = copy.deepcopy(source)
            for locale in OFFICIAL_LOCALES:
                values = pages.external_localized_values(key, locale, source)
                with mock.patch.object(repair, "external_values", side_effect=lambda k, l, v, **kw: v):
                    baseline = pages.external_localized_values(key, locale, source)
                changed = {field for field in set(values) | set(baseline) if values.get(field) != baseline.get(field)}
                if changed:
                    actual.add((key, locale))
                    self.assertEqual({"description"}, changed, (key, locale))
            self.assertEqual(snapshot, source)
        self.assertEqual(EXPECTED_CELLS, actual)

    def test_native_script_ratio_and_no_cross_script_contamination(self):
        for key, locale in EXPECTED_CELLS:
            description = pages.external_localized_values(key, locale)["description"]
            self.assertGreater(script_ratio(description, locale), 0.90, (key, locale))
            self.assertNotIn("\ufffd", description)
            self.assertNotRegex(description, r"one purchase|privacy-first learning|offline play|Pro edition")
            self.assertNotRegex(description, r"[\u202a-\u202e]")
            if locale in {"id", "ms", "vi"}:
                self.assertNotRegex(TERM.sub("", description), r"[\u3400-\u9fff\u0e00-\u0e7f\u0600-\u06ff]")
            if locale == "ar-SA":
                self.assertNotRegex(TERM.sub("", description), r"[\u0e00-\u0e7f\uac00-\ud7af\u3400-\u9fff]")

    def test_id_ms_and_chinese_variants_are_not_interchanged(self):
        for key in repair.APP_IDS:
            indonesian = pages.external_localized_values(key, "id")["description"]
            malay = pages.external_localized_values(key, "ms")["description"]
            self.assertIn("mengunduh", indonesian)
            self.assertIn("pengembang", indonesian)
            self.assertNotRegex(indonesian, r"kanak-kanak|memuat turun|pembangun")
            self.assertIn("memuat turun", malay)
            self.assertIn("pembangun", malay)
            self.assertNotRegex(malay, r"mengunduh|pengembang|bahasa Inggris")
            simplified = pages.external_localized_values(key, "zh-Hans")["description"]
            traditional = pages.external_localized_values(key, "zh-Hant")["description"]
            self.assertIn("下载时一次付费", simplified)
            self.assertNotRegex(simplified, r"[學習發購買廣與訂閱開編獨]")
            self.assertNotEqual(simplified, traditional)
            self.assertIn("學", traditional)
            self.assertGreater(script_ratio(traditional, "zh-Hant"), 0.70)

    def test_ja_ko_urdu_remain_native_and_unchanged(self):
        for key in repair.APP_IDS:
            for locale in ("ja", "ko", "ur-PK"):
                source = pages.load_app_locales(key)[locale]
                values = pages.external_localized_values(key, locale)
                self.assertEqual(source["description"], values["description"])
                self.assertGreater(script_ratio(values["description"], locale), 0.70, (key, locale))
                self.assertNotIn("Pro edition", values["description"])
            self.assertRegex(pages.external_localized_values(key, "ur-PK")["description"], r"[ٹڈڑںھہۂے]")

    def test_paid_upfront_identity_disclosure_and_no_hard_prices_or_guarantees(self):
        wrong_unlocks = (
            "pembuka kunci dalam app", "buka kunci dalam app",
            "ซื้อครั้งเดียวเพื่อปลดล็อกในแอป", "Mua một lần để mở khóa trong ứng dụng",
            "شراء لمرة واحدة مع فتح داخل التطبيق",
        )
        for key, locale in EXPECTED_CELLS:
            values = pages.external_localized_values(key, locale)
            self.assertEqual(repair.APP_IDS[key], str(pages.APPSTORE[key]))
            self.assertEqual("paid_upfront", pages.APPS[key]["purchase_model"])
            self.assertIn("Pro", values["name"])
            self.assertEqual(1, values["description"].count(repair.DISCLOSURES[locale]))
            self.assertIn("Lumi Studio", values["description"])
            self.assertIn("37" if key == "lumibopomofopro" else "26", values["description"])
            for phrase in wrong_unlocks:
                self.assertNotIn(phrase, values["description"])
            self.assertNotRegex(values["description"], r"US\s*\$|[$€£]\s*\d|guaranteed|保证|保證|รับประกัน|đảm bảo|يضمن")

    def test_html_app_id_cta_attribution_and_storefront_do_not_change(self):
        expected_storefronts = {"zh-Hans": "cn", "id": "id", "ms": "my", "th": "th", "vi": "vn", "ar-SA": "sa"}
        with tempfile.TemporaryDirectory() as baseline_dir, mock.patch.object(pages, "PAGES", baseline_dir):
            for key, locale in EXPECTED_CELLS:
                after = PageDOM()
                after.feed((self.output / locale / f"{key}.html").read_text())
                with mock.patch.object(repair, "external_values", side_effect=lambda k, l, v, **kw: v):
                    before_path = pages.build_one(key, locale, pages.all_locales_for(key))
                before = PageDOM()
                before.feed(Path(before_path).read_text())
                self.assertEqual(before.links, after.links)
                self.assertEqual(expected_storefronts[locale], pages.LOCALE_STOREFRONTS[locale])
                store_links = [url for url in after.links if urlsplit(url).netloc == "apps.apple.com"]
                self.assertTrue(store_links)
                for url in store_links:
                    self.assertIn(f"id{repair.APP_IDS[key]}", url)
                    query = parse_qs(urlsplit(url).query)
                    self.assertTrue(query.get("pt"))
                    self.assertTrue(query.get("ct"))
                    self.assertLessEqual(len(query["ct"][0]), 30)
                    path = urlsplit(url).path
                    self.assertTrue(path.startswith("/app/") or path.startswith(f"/{expected_storefronts[locale]}/app/"))
                self.assertEqual(locale, after.root["lang"])
                for schema in after.jsonld:
                    self.assertEqual(locale, schema["inLanguage"])
                    self.assertNotIn("<bdi", json.dumps(schema))

    def test_arabic_isolates_are_dom_nodes_not_css_or_json(self):
        for key, locale in EXPECTED_CELLS:
            source = (self.output / locale / f"{key}.html").read_text()
            dom = PageDOM()
            dom.feed(source)
            if locale == "ar-SA":
                self.assertEqual("rtl", dom.root.get("dir"))
                self.assertTrue(dom.isolates)
                self.assertTrue(all(node.get("dir") == "ltr" for node in dom.isolates))
                self.assertIn(f'<bdi dir="ltr">{pages.external_localized_values(key, locale)["name"]}</bdi>', source)
            else:
                self.assertFalse(dom.isolates)
            self.assertNotIn("unicode-bidi:", source)
            self.assertNotIn("direction:", source)
            self.assertNotIn("Pro edition", " ".join(dom.text))

    def test_rtl_helper_is_strictly_limited_and_html_safe(self):
        for key in self.keys:
            for locale in OFFICIAL_LOCALES:
                if (key, locale) in EXPECTED_CELLS and locale == "ar-SA":
                    continue
                self.assertEqual(html.escape("ABC 37 <نص> &"), repair.html_text(key, locale, "ABC 37 <نص> &"))
        result = repair.html_text("lumiletterspro", "ar-SA", "<script>ABC & 26</script>")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;", result)
        self.assertIn("&amp;", result)

    def test_repeat_render_is_idempotent_and_unknown_sources_fail_closed(self):
        key, locale = "lumibopomofopro", "ar-SA"
        source = pages.load_app_locales(key)[locale]
        kwargs = {"app_id": repair.APP_IDS[key], "purchase_model": "paid_upfront"}
        first = repair.external_values(key, locale, source, **kwargs)
        self.assertEqual(first, repair.external_values(key, locale, first, **kwargs))
        for description in ("", "Unreviewed English marketing copy.", source["description"] + repair.ENGLISH_PARAGRAPHS[key]):
            with self.assertRaises(ValueError):
                repair.external_values(key, locale, {**source, "description": description}, **kwargs)
        with self.assertRaises(ValueError):
            repair.external_values(key, locale, source, app_id="0", purchase_model="paid_upfront")
        with self.assertRaises(ValueError):
            repair.external_values(key, locale, source, app_id=repair.APP_IDS[key], purchase_model="free_with_lifetime_unlock")

    def test_candidate_writer_cannot_overwrite_existing_pages(self):
        for path in (self.output, Path(pages.PAGES), Path(pages.DATA)):
            with self.assertRaises(ValueError):
                candidates.generate(self.live_state, path)
        with self.assertRaises(ValueError):
            candidates.live_keys(["0"] * 47)


if __name__ == "__main__":
    unittest.main()
