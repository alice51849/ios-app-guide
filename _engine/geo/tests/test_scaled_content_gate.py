#!/usr/bin/env python3
"""Scaled-content gate: localized copies of an indexable English page leave the index."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_locale_indexation  # noqa: E402
import scaled_content_gate as gate  # noqa: E402

SITE = gen_locale_indexation.SITE
ENGLISH = [
    "How to keep a private budget on iPhone without a subscription",
    "Track spending offline: every entry stays on the device and nothing is uploaded.",
    "Pick a category once and the app remembers it for the next purchase you log.",
    "Export a CSV whenever you want to move your records into a spreadsheet.",
    "Multiple currencies are converted with the rate you enter, not a live feed.",
    "Is there an account? No, the budget works without signing in to anything.",
    "Does it sync? Only through your own iCloud backup, never a third-party server.",
]
GERMAN = [
    "So führen Sie ein privates Budget auf dem iPhone ohne Abo",
    "Ausgaben offline erfassen: Jeder Eintrag bleibt auf dem Gerät, nichts wird hochgeladen.",
    "Wählen Sie einmal eine Kategorie, die App merkt sie sich für den nächsten Kauf.",
    "Exportieren Sie jederzeit eine CSV-Datei, um Ihre Daten in eine Tabelle zu übernehmen.",
    "Mehrere Währungen werden mit dem eingegebenen Kurs umgerechnet, nicht live.",
    "Gibt es ein Konto? Nein, das Budget funktioniert ohne Anmeldung.",
    "Wird synchronisiert? Nur über Ihr eigenes iCloud-Backup, nie über fremde Server.",
]
JAPANESE = [
    "サブスクなしで iPhone の家計簿を非公開で付ける方法",
    "オフラインで支出を記録：すべての記録は端末に残り、アップロードされません。",
    "カテゴリを一度選べば、次の買い物を記録するときにアプリが覚えています。",
    "スプレッドシートに移したいときは、いつでも CSV を書き出せます。",
    "複数通貨は入力したレートで換算され、ライブ取得はしません。",
    "アカウントは必要？いいえ、サインインなしで使えます。",
    "同期は？自分の iCloud バックアップだけで、外部サーバーは使いません。",
]
HUB_EN = [f"Hub entry number {n} explains one more way to use the budget app" for n in range(24)]


def page(lang: str, url: str, blocks: list[str], *, robots: str | None = None,
         alternates: dict[str, str] | None = None, title: str = "Budget") -> str:
    head = [f'<html lang="{lang}"><head><title>{title}</title>']
    if robots is not None:
        head.append(f'<meta name="robots" content="{robots}">')
    head.append(f'<link rel="canonical" href="{url}">')
    for hreflang, href in (alternates or {}).items():
        head.append(f'<link rel="alternate" hreflang="{hreflang}" href="{href}">')
    head.append('<link rel="alternate" type="application/rss+xml" title="Feed" '
                f'href="{SITE}/rss.xml">')
    body = "".join(f"<p>{block}</p>" for block in blocks)
    return "".join(head) + f"</head><body><nav>Home</nav><main>{body}</main></body></html>"


def url(relative: str) -> str:
    return f"{SITE}/{relative}"


class SiteFixture:
    """A miniature Guide: one English answer page and its localized copies."""

    LOCALIZED = {
        "en-US/answers/budget.html": ("en-US", ENGLISH),
        "en-GB/answers/budget.html": ("en-GB", ENGLISH),
        "de-DE/answers/budget.html": ("de-DE", GERMAN),
        "ja/answers/budget.html": ("ja", ["ホーム", "回答"] + ENGLISH),
        "pt-BR/answers/budget.html": ("pt-BR", ["Início"] + ENGLISH),
    }

    def __init__(self, root: Path) -> None:
        self.root = root
        alternates = {"en": url("answers/budget.html"), "x-default": url("answers/budget.html")}
        for relative, (locale, _) in self.LOCALIZED.items():
            alternates[locale] = url(relative)
        self.alternates = alternates
        self.write("answers/budget.html", page("en", url("answers/budget.html"), ENGLISH,
                                               robots="index,follow", alternates=alternates))
        for relative, (locale, blocks) in self.LOCALIZED.items():
            self.write(relative, page(locale, url(relative), blocks,
                                      robots="index,follow,max-image-preview:large",
                                      alternates=alternates))
        # Thin localized hub stub vs a full English hub.
        self.write("hubs/budget.html", page("en", url("hubs/budget.html"), HUB_EN))
        self.write("fr-FR/hubs/budget.html", page("fr-FR", url("fr-FR/hubs/budget.html"),
                                                  ["Budget", "Voir sur l'App Store", "Guide"]))
        # Locale-only page and a page whose English original is noindex.
        self.write("ko/answers/only-korean.html", page("ko", url("ko/answers/only-korean.html"),
                                                       ["한국 전용 답변"] + ENGLISH))
        self.write("answers/retired.html", page("en", url("answers/retired.html"), ENGLISH,
                                                robots="noindex,follow"))
        self.write("es-ES/answers/retired.html", page("es-ES", url("es-ES/answers/retired.html"),
                                                      ["Inicio"] + ENGLISH))
        urls = [url("answers/budget.html"), url("hubs/budget.html"),
                url("fr-FR/hubs/budget.html"), url("ko/answers/only-korean.html"),
                url("es-ES/answers/retired.html")]
        urls += [url(relative) for relative in self.LOCALIZED]
        entries = "".join(
            f"<url><loc>{u}</loc>"
            + "".join(f'<xhtml:link rel="alternate" hreflang="{h}" href="{a}"/>'
                      for h, a in alternates.items())
            + "</url>"
            for u in urls
        )
        (root / "sitemap_answers.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + entries + "</urlset>",
            encoding="utf-8",
        )
        (root / "sitemap_index.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<sitemap><loc>{SITE}/sitemap_answers.xml</loc></sitemap></sitemapindex>",
            encoding="utf-8",
        )

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")


class ScaledContentGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.site = SiteFixture(self.root)
        self.canaries = mock.patch.object(gate, "canary_slugs", return_value=frozenset())
        self.canaries.start()

    def tearDown(self) -> None:
        self.canaries.stop()
        self.tmp.cleanup()

    def verdicts(self, **policy_overrides):
        policy = dataclasses.replace(gate.load_policy(), **policy_overrides)
        return gate.evaluate(self.root, policy=policy, site=SITE)

    def test_rules_gate_only_copies_of_an_indexable_english_page(self):
        result = self.verdicts()
        reasons = {rel: v.reason for rel, v in result.verdicts.items()}
        self.assertEqual("same-storefront-copy", reasons["en-US/answers/budget.html"])
        self.assertEqual("untranslated-core", reasons["ja/answers/budget.html"])
        self.assertEqual("untranslated-core", reasons["pt-BR/answers/budget.html"])
        self.assertEqual("thin-stub", reasons["fr-FR/hubs/budget.html"])
        # Real translation, own-storefront regional variant, locale-only page and
        # a page whose English original is not indexable all stay indexable.
        self.assertIsNone(reasons["de-DE/answers/budget.html"])
        self.assertIsNone(reasons["en-GB/answers/budget.html"])
        self.assertEqual(
            "regional-copy-own-storefront",
            result.verdicts["en-GB/answers/budget.html"].category,
        )
        self.assertIsNone(reasons["ko/answers/only-korean.html"])
        self.assertEqual("no-english-counterpart",
                         result.verdicts["ko/answers/only-korean.html"].exempt)
        self.assertEqual("english-counterpart-noindex",
                         result.verdicts["es-ES/answers/retired.html"].exempt)
        self.assertEqual(
            {"en-US/answers/budget.html", "ja/answers/budget.html",
             "pt-BR/answers/budget.html", "fr-FR/hubs/budget.html"},
            set(result.gated),
        )

    def test_search_console_evidence_and_canaries_keep_pages_indexed(self):
        evidence = self.root / "evidence.json"
        evidence.write_text(json.dumps({"pages": {
            url("pt-BR/answers/budget.html"): {"impressions": 3, "clicks": 0},
            url("ja/answers/budget.html"): {"impressions": 0, "clicks": 0},
        }}), encoding="utf-8")
        with mock.patch.object(gate, "canary_slugs", return_value=frozenset({"budget"})):
            result = self.verdicts(search_evidence_path=str(evidence))
        self.assertTrue(result.evidence_loaded)
        # Canary answers are exempt in every locale; the hub stub is not a canary.
        self.assertEqual({"fr-FR/hubs/budget.html"}, set(result.gated))
        self.assertEqual("index-entry-canary", result.verdicts["ja/answers/budget.html"].exempt)
        result = self.verdicts(search_evidence_path=str(evidence))
        self.assertEqual("search-console-evidence",
                         result.verdicts["pt-BR/answers/budget.html"].exempt)
        self.assertIn("ja/answers/budget.html", result.gated)

    def test_indexation_noindexes_prunes_sitemaps_and_hreflang(self):
        stats = gen_locale_indexation.run_indexation(self.root)
        self.assertEqual(4, len(stats.scaled_gated))
        self.assertEqual(4, stats.page_stats["scaled_noindexed"])
        for relative in stats.scaled_gated:
            text = self.site.read(relative)
            self.assertIn(gate.MARK, text)
            self.assertIn('<meta name="robots" content="noindex,follow">', text)
        self.assertEqual(1, self.site.read("ja/answers/budget.html").count('name="robots"'))
        english = self.site.read("answers/budget.html")
        for gated in ("en-US", "ja", "pt-BR"):
            self.assertNotIn(f'hreflang="{gated}"', english)
            self.assertNotIn(f'hreflang="{gated}"', self.site.read("de-DE/answers/budget.html"))
        for kept in ("en", "x-default", "de-DE", "en-GB"):
            self.assertIn(f'hreflang="{kept}"', english)
        self.assertIn('type="application/rss+xml"', english)
        sitemap = self.site.read("sitemap_answers.xml")
        for relative in stats.scaled_gated:
            self.assertNotIn(url(relative), sitemap)
        self.assertIn(f"<loc>{url('de-DE/answers/budget.html')}</loc>", sitemap)
        self.assertIn(f"<loc>{url('en-GB/answers/budget.html')}</loc>", sitemap)
        self.assertIn(f'href="{url("de-DE/answers/budget.html")}"', sitemap)
        self.assertFalse((self.root / gen_locale_indexation.ORPHAN_SITEMAP).exists())

        again = gen_locale_indexation.run_indexation(self.root)
        self.assertEqual(stats.scaled_gated, again.scaled_gated)
        self.assertEqual(0, again.page_stats["scaled_noindexed"])
        self.assertEqual(0, again.page_stats["scaled_reindexed"])
        self.assertEqual(0, again.page_stats["alternates_cleaned"])

    def test_gate_is_reversed_when_the_page_gets_a_real_translation(self):
        gen_locale_indexation.run_indexation(self.root)
        marked = self.site.read("ja/answers/budget.html")
        translated = marked.replace(
            "".join(f"<p>{b}</p>" for b in ["ホーム", "回答"] + ENGLISH),
            "".join(f"<p>{b}</p>" for b in JAPANESE),
        )
        self.assertNotEqual(marked, translated)
        self.site.write("ja/answers/budget.html", translated)
        stats = gen_locale_indexation.run_indexation(self.root)
        self.assertNotIn("ja/answers/budget.html", stats.scaled_gated)
        self.assertEqual(1, stats.page_stats["scaled_reindexed"])
        text = self.site.read("ja/answers/budget.html")
        self.assertNotIn(gate.MARK, text)
        self.assertIn('<meta name="robots" content="index,follow,max-image-preview:large">', text)

    def test_noindex_stamp_round_trips_the_prior_directive(self):
        for source in (
            '<html><head><meta name="robots" content="index,follow"></head><body></body></html>',
            "<html><head><title>x</title></head><body></body></html>",
        ):
            stamped = gate.apply_noindex(source)
            self.assertEqual(stamped, gate.apply_noindex(stamped))
            self.assertIn('content="noindex,follow"', stamped)
            self.assertEqual(source, gate.remove_noindex(stamped))

    def test_policy_floors_refuse_aggressive_thresholds(self):
        policy = json.loads(gate.POLICY_PATH.read_text(encoding="utf-8"))
        for key, value in (
            ("untranslated_min_identity", 0.5),
            ("same_storefront_min_identity", 0.7),
            ("thin_max_ratio", 0.5),
            ("thin_max_segments", 40),
            ("untranslated_min_core_chars", 50),
        ):
            loose = dict(policy, **{key: value})
            path = self.root / "policy.json"
            path.write_text(json.dumps(loose), encoding="utf-8")
            with self.assertRaises(ValueError, msg=key):
                gate.load_policy(path)
        # A regional variant with its own storefront is not a same-storefront copy.
        loose = dict(policy, same_storefront_copies={"en-GB": ""})
        path = self.root / "policy.json"
        path.write_text(json.dumps(loose), encoding="utf-8")
        with self.assertRaises(ValueError):
            gate.load_policy(path)

    def test_report_lists_every_gated_path(self):
        result = self.verdicts()
        report = gate.report(result)
        self.assertEqual(sorted(result.gated), report["gated_paths"])
        self.assertEqual(4, report["gated"])
        self.assertEqual({"same-storefront-copy": 1, "untranslated-core": 2, "thin-stub": 1},
                         report["gated_by_reason"])


if __name__ == "__main__":
    unittest.main()
