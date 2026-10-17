#!/usr/bin/env python3
"""The first-party disclosure is localized, visible before the first
recommendation, idempotent, and never touches store links."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import first_party_disclosure as F  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from owned_feed_locale_gate import validate_text  # noqa: E402

STORE = "https://apps.apple.com/jp/app/id6778748533?pt=118326163&amp;ct=geo_ask&amp;mt=8"
ORG = F.ORGANIZATION_ID


def page(*, lang="ja", main=True, body_extra="", head_extra="", ld=None):
    ld_block = (
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
        if ld is not None else ""
    )
    content = (
        f'<section class="hero"><h1>T</h1><p class="lead">Lead.</p>'
        f'<a class="cta" href="{STORE}">Get</a></section>{body_extra}'
    )
    inner = f"<main>{content}</main>" if main else content
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        f'<link rel="canonical" href="{F.PUBLIC_SITE}/{lang}/answers/x.html">'
        f"{ld_block}{head_extra}</head>"
        f'<body><header class="top"><nav><a href="/">Home</a></nav></header>'
        f"{inner}<footer>f</footer></body></html>"
    )


class CopyTests(unittest.TestCase):
    def test_every_official_locale_has_native_single_line_copy(self) -> None:
        for locale in OFFICIAL_LOCALES:
            for name, text in (
                ("banner", F.banner_text(locale)),
                ("faq", F.faq_answer(locale)),
            ):
                with self.subTest(locale=locale, field=name):
                    validate_text(locale, text, name)
                    self.assertIn(F.DEVELOPER, text)
                    self.assertNotIn("\n", text)
                    if not locale.startswith("en-"):
                        self.assertNotEqual(text, F._localized(
                            F.BANNER if name == "banner" else F.FAQ_ANSWER, "en-US"))

    def test_japanese_copy_follows_stealth_marketing_guidance(self) -> None:
        banner = F.banner_text("ja")
        for word in ("当サイト", "開発者", "運営", "自社アプリ"):
            self.assertIn(word, banner)
        self.assertTrue(F.faq_answer("ja").startswith("いいえ。"))

    def test_locale_resolution(self) -> None:
        cases = {
            "ja": "ja", "ja-JP": "ja", "en": "en-US", "en-GB": "en-GB",
            "zh-TW": "zh-Hant", "zh-CN": "zh-Hans", "yue": "zh-Hant",
            "nb-NO": "no", "es-ES": "es-ES", "es-419": "es-MX",
            "pt-PT": "pt-PT", "pt": "pt-BR", "acm": "ar-SA", "bho": "hi",
            "fr-CA": "fr-CA", "sot": None,
        }
        for lang, expected in cases.items():
            with self.subTest(lang=lang):
                self.assertEqual(expected, F.resolve_locale(lang))


class TransformTests(unittest.TestCase):
    def test_banner_sits_between_header_and_main_once(self) -> None:
        source = page()
        updated = F.transform(source, "ja", {})
        banner = updated.find('data-first-party-disclosure="banner"')
        self.assertGreater(banner, updated.find("</header>"))
        self.assertLess(banner, updated.find("<main>"))
        self.assertLess(banner, updated.find("apps.apple.com"))
        self.assertIn(F.banner_text("ja"), updated)
        self.assertEqual(updated, F.transform(updated, "ja", {}))
        self.assertEqual(1, updated.count('data-first-party-disclosure="banner"'))

    def test_page_without_main_gets_banner_right_after_body(self) -> None:
        source = page(main=False).replace('<header class="top"><nav><a href="/">Home</a></nav></header>', "")
        updated = F.ensure_banner(source, "de-DE")
        self.assertRegex(updated, r"<body><p class=\"first-party-disclosure\"")

    def test_fallback_banner_is_marked_english(self) -> None:
        updated = F.transform(page(lang="sot"), "en-US", {}, fallback=True)
        self.assertIn('lang="en"', updated)
        self.assertIn(F.banner_text("en-US"), updated)

    def test_banner_copy_update_replaces_old_line(self) -> None:
        stale = F.ensure_banner(page(), "ja").replace(F.banner_text("ja"), "old")
        updated = F.ensure_banner(stale, "ja")
        self.assertNotIn(">old<", updated)
        self.assertEqual(1, updated.count('data-first-party-disclosure="banner"'))

    def test_store_links_and_app_copy_are_untouched(self) -> None:
        source = page(body_extra='<p class="price">¥300 one-time</p>')
        updated = F.transform(source, "ja", {})
        self.assertEqual(
            re.findall(r'href="([^"]+)"', source),
            re.findall(r'href="([^"]+)"', updated),
        )
        self.assertIn('<p class="price">¥300 one-time</p>', updated)

    def test_site_organization_becomes_the_developer(self) -> None:
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "Organization", "@id": ORG, "name": "iOSアプリガイド", "url": F.PUBLIC_SITE},
            {"@type": "WebSite", "@id": f"{F.PUBLIC_SITE}/#website", "publisher": {"@id": ORG}},
        ]}
        updated = F.ensure_publisher(page(ld=ld))
        payload = re.search(r'<script type="application/ld\+json">(.*?)</script>', updated).group(1)
        graph = json.loads(payload)["@graph"]
        self.assertEqual("Lumi Studio", graph[0]["name"])
        self.assertNotIn('data-first-party-disclosure="publisher"', updated)

    def test_offsets_survive_text_whose_lowercase_changes_length(self) -> None:
        source = page(lang="tr").replace("<head>", "<head><title>İİİ İstanbul</title>")
        updated = F.transform(source, "tr", {})
        self.assertIn("</script>\n</head>", updated)
        self.assertIn('<p class="first-party-disclosure"', updated)
        self.assertLess(updated.find("<body"), updated.find('data-first-party-disclosure="banner"'))
        self.assertEqual(
            re.sub(r"<(p|script)[^>]*data-first-party-disclosure[^>]*>.*?</\1>\n?", "", updated, flags=re.S)
            .replace('"name": "Lumi Studio"', ""),
            source.replace('"name": "Lumi Studio"', ""),
        )

    def test_page_without_publisher_gets_developer_publisher_block(self) -> None:
        updated = F.ensure_publisher(page(ld={"@type": "FAQPage"}))
        block = re.search(
            r'<script type="application/ld\+json" data-first-party-disclosure="publisher">(.*?)</script>',
            updated,
        )
        data = json.loads(block.group(1))
        self.assertEqual("WebSite", data["@type"])  # never a second WebPage
        self.assertEqual(f"{F.PUBLIC_SITE}/#website", data["@id"])
        self.assertEqual("Lumi Studio", data["publisher"]["name"])
        self.assertEqual(ORG, data["publisher"]["@id"])
        self.assertEqual(updated, F.ensure_publisher(updated))
        self.assertLess(block.start(), updated.find("</head>"))

    def test_legacy_independence_claims_are_corrected(self) -> None:
        legacy = {"ja": "はい。本ページは購入ガイドであり、各アプリ名や商標は、それぞれの所有者に帰属します。"}
        faq = (
            '<h3 itemprop="name">このページは独立していますか?</h3>'
            f'<p itemprop="text">{legacy["ja"]}</p>'
            f'<p itemprop="text">{F.LEGACY_FAQ_ANSWER}</p>'
            "<p><small>独立した比較です。アプリ名は各所有者の商標であり、識別のためにのみ使用しています。</small></p>"
            '<footer class="footer"><div class="wrap">独立した比較です。アプリ名は各所有者の商標です。</div></footer>'
        )
        ld = {"@type": "FAQPage", "mainEntity": [{"acceptedAnswer": {"text": legacy["ja"]}}]}
        source = page(body_extra=faq, ld=ld)
        updated = F.fix_legacy_claims(source, "ja", legacy)
        self.assertNotIn(legacy["ja"], updated)
        self.assertNotIn(F.LEGACY_FAQ_ANSWER, updated)
        self.assertNotIn("独立した比較です", updated)
        self.assertEqual(2, updated.count(F.faq_answer("ja")))
        self.assertIn(F.FAQ_ANSWER["en-US"], updated)
        self.assertIn(
            "<p><small>掲載アプリの開発者であるLumi Studioによる比較です。"
            "アプリ名は各所有者の商標であり、識別のためにのみ使用しています。</small></p>",
            updated,
        )
        self.assertIn('<div class="wrap">掲載アプリの開発者であるLumi Studioによる比較です。アプリ名は', updated)

    def test_ascii_escaped_json_ld_answer_is_corrected(self) -> None:
        old = "はい。本ページは購入ガイドです。"
        ld = json.dumps({"@type": "FAQPage", "text": old})  # \\uXXXX escapes
        source = page().replace("</head>", f'<script type="application/ld+json">{ld}</script></head>')
        updated = F.fix_legacy_claims(source, "ja", {"ja": old})
        self.assertNotIn(json.dumps(old)[1:-1], updated)
        self.assertIn(json.dumps(F.faq_answer("ja"))[1:-1], updated)


class TreeTests(unittest.TestCase):
    def test_run_skips_pinned_amp_redirect_and_non_promotional_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "ja/answers/a.html": page(),
                "answers/b.html": page(lang="en"),
                "ja/tools/hero.html": page(),
                "de-DE/decide/x/route.html": page(lang="de-DE"),
                "ja/data/catalog.html": page(),
                "ja/stories/s.html": page().replace("<html ", "<html amp "),
                "ja/old.html": page().replace("<head>", '<head><meta http-equiv="refresh" content="0;url=a">'),
                "ja/plain.html": "<html lang=\"ja\"><body><main><p>no store</p></main></body></html>",
                "_engine/geo/x.html": page(),
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            hero = root / "data/hero-tasks/manifest.json"
            hero.parent.mkdir(parents=True)
            hero.write_text(json.dumps({"outputs": {"ja/tools/hero.html": "x"}}))
            routes = root / "data/high-intent-decision-routes/expected-output-manifest.json"
            routes.parent.mkdir(parents=True)
            routes.write_text(json.dumps({
                "expected_outputs": [{"kind": "route_html", "relative_path": "de-DE/decide/x/route.html"}],
                "routes": [],
            }))
            before = {p: (root / p).read_text(encoding="utf-8") for p in files}

            check = F.run(root, check=True)
            self.assertEqual(2, check["changed"])
            self.assertEqual(before, {p: (root / p).read_text(encoding="utf-8") for p in files})

            first = F.run(root)
            second = F.run(root)
            self.assertEqual(2, first["changed"])
            self.assertEqual(3, first["pinned_skipped"])
            self.assertEqual(0, second["changed"])
            self.assertIn(F.banner_text("ja"), (root / "ja/answers/a.html").read_text(encoding="utf-8"))
            self.assertIn(F.banner_text("en-US"), (root / "answers/b.html").read_text(encoding="utf-8"))
            for untouched in (
                "ja/tools/hero.html", "de-DE/decide/x/route.html", "ja/data/catalog.html",
                "ja/stories/s.html", "ja/old.html", "ja/plain.html", "_engine/geo/x.html",
            ):
                with self.subTest(page=untouched):
                    self.assertEqual(before[untouched], (root / untouched).read_text(encoding="utf-8"))
            self.assertEqual(0, F.main(["--pages", str(root), "--check"]))


if __name__ == "__main__":
    unittest.main()
