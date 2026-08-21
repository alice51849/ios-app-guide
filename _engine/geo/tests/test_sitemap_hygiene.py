#!/usr/bin/env python3
"""Regression tests for crawl-budget sitemap hygiene."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import aeo_answers  # noqa: E402
import gen_llms  # noqa: E402
import gen_locale_indexation  # noqa: E402


def urlset(*urls: str) -> str:
    body = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</urlset>"
    )


def sitemap_index(*names: str) -> str:
    body = "".join(
        "<sitemap><loc>"
        f"{gen_locale_indexation.SITE}/{name}"
        "</loc></sitemap>"
        for name in names
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{body}</sitemapindex>"
    )


class SitemapHygieneTests(unittest.TestCase):
    def test_generated_index_excludes_empty_sitemaps(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "sitemap.xml").write_text(
                urlset(),
                encoding="utf-8",
            )
            (pages / "sitemap_answers.xml").write_text(
                urlset(f"{gen_llms.SITE}/answers/useful.html"),
                encoding="utf-8",
            )
            with mock.patch.object(gen_llms, "PAGES", str(pages)):
                index = gen_llms.build_sitemap_index()

        self.assertNotIn(f"{gen_llms.SITE}/sitemap.xml", index)
        self.assertIn(f"{gen_llms.SITE}/sitemap_answers.xml", index)

    def test_locale_hygiene_prunes_noindex_and_unhooks_empty_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            answers = pages / "answers"
            answers.mkdir()
            live = answers / "live.html"
            hidden = answers / "hidden.html"
            live.write_text("<html><head></head></html>", encoding="utf-8")
            hidden.write_text(
                '<html><head><meta name="robots" '
                'content="noindex,follow"></head></html>',
                encoding="utf-8",
            )
            live_url = f"{gen_locale_indexation.SITE}/answers/live.html"
            hidden_url = f"{gen_locale_indexation.SITE}/answers/hidden.html"
            (pages / "sitemap_answers.xml").write_text(
                urlset(live_url, hidden_url),
                encoding="utf-8",
            )
            (pages / "sitemap_empty.xml").write_text(
                urlset(),
                encoding="utf-8",
            )
            (pages / "sitemap_unhooked.xml").write_text(
                urlset(f"{gen_locale_indexation.SITE}/answers/live.html"),
                encoding="utf-8",
            )
            index_path = pages / "sitemap_index.xml"
            index_path.write_text(
                sitemap_index(
                    "sitemap_answers.xml",
                    "sitemap_empty.xml",
                ),
                encoding="utf-8",
            )

            stats = gen_locale_indexation.prune_sitemaps(
                pages,
                set(),
                False,
            )
            dropped = gen_locale_indexation.update_sitemap_index(
                pages,
                stats["_emptied"],
                False,
                False,
            )

            answers_sitemap = (
                pages / "sitemap_answers.xml"
            ).read_text(encoding="utf-8")
            updated_index = index_path.read_text(encoding="utf-8")

        self.assertEqual(1, stats["urls_dropped_noindex"])
        self.assertIn(live_url, answers_sitemap)
        self.assertNotIn(hidden_url, answers_sitemap)
        self.assertEqual(1, dropped)
        self.assertIn("sitemap_answers.xml", updated_index)
        self.assertIn("sitemap_unhooked.xml", updated_index)
        self.assertNotIn("sitemap_empty.xml", updated_index)

    def test_index_discovers_nested_nonempty_sitemaps(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            nested = pages / "apps" / "alpha"
            nested.mkdir(parents=True)
            index_path = pages / "sitemap_index.xml"
            index_path.write_text(sitemap_index(), encoding="utf-8")
            (nested / "sitemap-localized.xml").write_text(
                urlset(f"{gen_locale_indexation.SITE}/apps/alpha/"),
                encoding="utf-8",
            )

            gen_locale_indexation.update_sitemap_index(
                pages, set(), False, False
            )
            updated = index_path.read_text(encoding="utf-8")

        self.assertIn(
            "apps/alpha/sitemap-localized.xml",
            updated,
        )

    def test_nested_index_and_orphan_maps_are_always_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            nested = pages / "apps" / "alpha"
            nested.mkdir(parents=True)
            index_path = pages / "sitemap_index.xml"
            index_path.write_text(sitemap_index(), encoding="utf-8")
            live_url = f"{gen_locale_indexation.SITE}/apps/alpha/"
            regular = nested / "sitemap-localized.xml"
            regular.write_text(urlset(live_url), encoding="utf-8")
            (nested / "sitemap_index.xml").write_text(
                sitemap_index("sitemap-localized.xml"),
                encoding="utf-8",
            )
            (nested / gen_locale_indexation.ORPHAN_SITEMAP).write_text(
                urlset(live_url),
                encoding="utf-8",
            )

            candidates = {
                path.relative_to(pages).as_posix()
                for path in gen_locale_indexation.sitemap_candidates(pages)
            }
            gen_locale_indexation.update_sitemap_index(
                pages, set(), False, False
            )
            updated = index_path.read_text(encoding="utf-8")

        self.assertEqual(
            {"apps/alpha/sitemap-localized.xml"},
            candidates,
        )
        self.assertIn("apps/alpha/sitemap-localized.xml", updated)
        self.assertNotIn("apps/alpha/sitemap_index.xml", updated)
        self.assertNotIn(
            f"apps/alpha/{gen_locale_indexation.ORPHAN_SITEMAP}",
            updated,
        )

    def test_nested_sitemaps_share_hygiene_and_canonical_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            live = pages / "apps" / "alpha"
            hidden = pages / "apps" / "hidden"
            live.mkdir(parents=True)
            hidden.mkdir(parents=True)
            (live / "index.html").write_text(
                "<html><head></head></html>",
                encoding="utf-8",
            )
            (hidden / "index.html").write_text(
                '<html><head><meta name="robots" '
                'content="noindex,follow"></head></html>',
                encoding="utf-8",
            )
            nested = live / "sitemap-localized.xml"
            nested.write_text(
                urlset(
                    f"{gen_locale_indexation.SITE}/apps/alpha/",
                    f"{gen_locale_indexation.SITE}/apps/hidden/",
                ),
                encoding="utf-8",
            )

            stats = gen_locale_indexation.prune_sitemaps(
                pages, set(), False
            )
            kept = {
                gen_locale_indexation.url_to_content_relative(url)
                for url in stats["_kept"]
            }
            updated = nested.read_text(encoding="utf-8")

        self.assertEqual(1, stats["urls_dropped_noindex"])
        self.assertIn("/apps/alpha/", updated)
        self.assertNotIn("/apps/hidden/", updated)
        self.assertIn("apps/alpha/index.html", kept)

    def test_orphan_sitemap_emits_canonical_urls_and_deduplicates_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            canonical = (
                f"{gen_locale_indexation.SITE}/apps/alpha/"
            )
            app = pages / "apps" / "alpha"
            app.mkdir(parents=True)
            (app / "index.html").write_text(
                f'<link href="{canonical}" rel="canonical">',
                encoding="utf-8",
            )
            alias = pages / "find-app.html"
            alias.write_text(
                f'<link rel="canonical" href="{canonical}">',
                encoding="utf-8",
            )
            unique = pages / "unique.html"
            unique_url = f"{gen_locale_indexation.SITE}/unique.html"
            unique.write_text(
                f'<link rel="canonical" href="{unique_url}">',
                encoding="utf-8",
            )

            count = gen_locale_indexation.write_orphan_sitemap(
                pages,
                [
                    "apps/alpha/index.html",
                    "find-app.html",
                    "unique.html",
                ],
                False,
            )
            sitemap = (
                pages / gen_locale_indexation.ORPHAN_SITEMAP
            ).read_text(encoding="utf-8")

        self.assertEqual(2, count)
        self.assertEqual(1, sitemap.count(canonical))
        self.assertIn(unique_url, sitemap)
        self.assertNotIn("apps/alpha/index.html", sitemap)
        self.assertNotIn("find-app.html", sitemap)

    def test_orphan_sitemap_omits_alias_of_covered_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            canonical = (
                f"{gen_locale_indexation.SITE}/apps/alpha/"
            )
            alias = pages / "find-app.html"
            alias.write_text(
                f'<link rel="canonical" href="{canonical}">',
                encoding="utf-8",
            )

            count = gen_locale_indexation.write_orphan_sitemap(
                pages,
                ["find-app.html"],
                False,
                {canonical},
            )

        self.assertEqual(0, count)

    def test_answer_sitemap_excludes_every_noindex_page(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            answers = pages / "answers"
            answers.mkdir()
            (answers / "live.html").write_text(
                "<html><head></head></html>",
                encoding="utf-8",
            )
            (answers / "hidden.html").write_text(
                '<html><head><meta content="noindex,follow" '
                'name="robots"></head></html>',
                encoding="utf-8",
            )

            aeo_answers.write_sitemap(pages)
            sitemap = (pages / "sitemap_answers.xml").read_text(
                encoding="utf-8"
            )

        self.assertIn("/answers/live.html", sitemap)
        self.assertNotIn("/answers/hidden.html", sitemap)

    def test_deployed_tree_has_a_closed_sitemap_union(self):
        pages = Path(gen_locale_indexation.PAGES)
        index_path = pages / "sitemap_index.xml"
        if not pages.is_dir() or not index_path.is_file():
            self.skipTest("materialized Pages tree is unavailable")

        referenced: list[Path] = []
        referenced_relatives: set[str] = set()
        for url in gen_locale_indexation.LOC_RE.findall(
            index_path.read_text(encoding="utf-8")
        ):
            relative = gen_locale_indexation.url_to_relative(url)
            if relative is None or not relative.endswith(".xml"):
                continue
            sitemap = pages / relative
            self.assertTrue(sitemap.is_file(), relative)
            self.assertTrue(
                gen_locale_indexation.sitemap_has_entries(sitemap),
                relative,
            )
            referenced.append(sitemap)
            referenced_relatives.add(relative)

        discovered = {
            sitemap.relative_to(pages).as_posix()
            for sitemap in gen_locale_indexation.sitemap_candidates(pages)
            if gen_locale_indexation.sitemap_has_entries(sitemap)
        }
        self.assertEqual(set(), discovered - referenced_relatives)

        listed: set[str] = set()
        listed_urls: set[str] = set()
        for sitemap in referenced:
            for url in gen_locale_indexation.LOC_RE.findall(
                sitemap.read_text(encoding="utf-8")
            ):
                relative = (
                    gen_locale_indexation.url_to_content_relative(url)
                )
                if relative and relative.endswith(".html"):
                    listed.add(relative)
                    listed_urls.add(url)

        dead = gen_locale_indexation.non_store_locales(pages)
        indexable = gen_locale_indexation.indexable_pages(pages, dead)
        indexable_urls = {
            gen_locale_indexation.canonical_url_for_html(
                pages / relative,
                f"{gen_locale_indexation.SITE}/{relative}",
                gen_locale_indexation.SITE,
            )
            for relative in indexable
        }
        ghosts = {
            relative
            for relative in listed
            if not (pages / relative).is_file()
        }
        noindex = {
            relative
            for relative in listed
            if gen_locale_indexation.is_noindex_html(pages / relative)
        }
        self.assertEqual(set(), indexable_urls - listed_urls)
        self.assertEqual(set(), ghosts)
        self.assertEqual(set(), noindex)


if __name__ == "__main__":
    unittest.main()
