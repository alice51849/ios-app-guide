from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest


GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parent

import sys

sys.path.insert(0, str(GEO))

import pages_stage  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402


def html_page(
    relative: str,
    *,
    body: str = "Guide",
    links: tuple[str, ...] = (),
    hreflang: tuple[tuple[str, str], ...] = (),
    noindex: bool = False,
) -> str:
    url = f"{pages_stage.SITE}/{relative}"
    alternates = "".join(
        f'<link rel="alternate" hreflang="{locale}" href="{target}">\n'
        for locale, target in hreflang
    )
    anchors = "".join(f'<a href="{link}">next</a>' for link in links)
    robots = (
        '<meta name="robots" content="noindex,follow">'
        if noindex
        else '<meta name="robots" content="index,follow">'
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
{robots}
<link rel="canonical" href="{url}">
{alternates}
<link rel="alternate" type="application/epub+zip" hreflang="en"
 href="{pages_stage.SITE}/reference.epub">
<link rel="alternate" type="text/markdown"
 href="{pages_stage.SITE}/guide.md">
<style>
body {{
  color: #123;
}}
</style>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "url": "{url}",
  "name": "Guide"
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Lumi Studio",
  "url": "{pages_stage.SITE}"
}}
</script>
</head><body><main><h1>{body}</h1>{anchors}
<svg><stop offset="0" stop-color="#ffc44d"/></svg>
<amp-story publisher-logo-src="{pages_stage.SITE}/logo.jpg"
 poster-portrait-src="{pages_stage.SITE}/poster.jpg"></amp-story>
</main></body></html>
"""


class PagesStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.output = self.base / "output"
        self.source.mkdir()
        (self.source / ".well-known").mkdir()
        (self.source / ".well-known/publish-inventory.json").write_text(
            json.dumps(
                {
                    "excluded": [{"path": "guide.md"}],
                    "version": 1,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (self.source / ".nojekyll").write_text("", encoding="utf-8")
        (self.source / "sitemap_index.xml").write_text(
            (
                '<?xml version="1.0"?>'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/'
                'sitemap/0.9"><sitemap><loc>'
                f"{pages_stage.SITE}/sitemap.xml"
                "</loc></sitemap><sitemap><loc>"
                f"{pages_stage.SITE}/sitemap-extra.xml"
                "</loc></sitemap><sitemap><loc>"
                f"{pages_stage.SITE}/sitemap-linked.xml"
                "</loc></sitemap></sitemapindex>"
            ),
            encoding="utf-8",
        )
        (self.source / "sitemap.xml").write_text(
            (
                '<?xml version="1.0"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{pages_stage.SITE}/index.html</loc></url>"
                "</urlset>"
            ),
            encoding="utf-8",
        )
        (self.source / "sitemap-extra.xml").write_text(
            (
                '<?xml version="1.0"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + (" " * 5_000)
                + f"<url><loc>{pages_stage.SITE}/index.html</loc></url>"
                + "</urlset>"
            ),
            encoding="utf-8",
        )
        (self.source / "sitemap-linked.xml").write_text(
            (
                '<?xml version="1.0"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                + (" " * 5_000)
                + f"<url><loc>{pages_stage.SITE}/index.html</loc></url>"
                + "</urlset>"
            ),
            encoding="utf-8",
        )
        hreflang = (
            ("en-US", f"{pages_stage.SITE}/en-US/index.html"),
            ("ar-SA", f"{pages_stage.SITE}/ar-SA/index.html"),
            ("x-default", f"{pages_stage.SITE}/index.html"),
        )
        (self.source / "index.html").write_text(
            html_page(
                "index.html",
                body="دليل मार्गदर्शिका",
                links=(
                    "/ios-app-guide/en-US/index.html",
                    "/ios-app-guide/guide.md",
                    "/ios-app-guide/sitemap-linked.xml",
                ),
                hreflang=hreflang,
            ),
            encoding="utf-8",
        )
        (self.source / "noindex.html").write_text(
            html_page(
                "noindex.html",
                hreflang=hreflang,
                noindex=True,
            ),
            encoding="utf-8",
        )
        (self.source / "guide.html").write_text(
            html_page("guide.html"),
            encoding="utf-8",
        )
        for locale in OFFICIAL_LOCALES:
            target = self.source / locale / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                html_page(
                    f"{locale}/index.html",
                    links=("/ios-app-guide/index.html",),
                ),
                encoding="utf-8",
            )
        (self.source / "logo.jpg").write_bytes(b"logo")
        (self.source / "poster.jpg").write_bytes(b"poster")
        (self.source / "reference.epub").write_bytes(b"epub")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_stage_is_deterministic_and_semantically_equivalent(self) -> None:
        first = pages_stage.build_stage(
            self.source,
            self.output,
            max_unpacked_bytes=10_000_000,
        )
        self.assertLessEqual(
            first["unpacked_bytes"],
            first["max_unpacked_bytes"],
        )
        self.assertGreater(first["public_url_count"], 0)
        self.assertEqual(64, len(first["public_url_sha256"]))
        self.assertEqual(64, len(first["file_inventory_sha256"]))
        staged = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<style", staged)
        self.assertEqual(1, staged.count("hreflang"))
        self.assertIn("application/epub+zip", staged)
        self.assertNotIn("guide.md", staged)
        self.assertIn("guide.html", staged)
        self.assertNotIn("text/markdown", staged)
        self.assertIn("دليل मार्गदर्शिका", staged)
        self.assertEqual(
            1,
            staged.count("<script type=application/ld+json>"),
        )
        self.assertIn("assets/stage-jsonld/", staged)
        self.assertTrue(list((self.output / "assets/stage-css").glob("*.css")))
        json_ld_assets = list(
            (self.output / "assets/stage-jsonld").glob("*.js")
        )
        self.assertTrue(json_ld_assets)
        loader = json_ld_assets[0].read_text(encoding="utf-8")
        payload = re.search(
            r"n\.textContent=(.+);document\.currentScript",
            loader,
        )
        self.assertIsNotNone(payload)
        rendered_schema = json.loads(json.loads(payload.group(1)))
        self.assertEqual("https://schema.org", rendered_schema["@context"])
        shards = list((self.output / "sitemaps").glob("*.xml.gz"))
        self.assertTrue(shards)
        self.assertIn(
            b"hreflang",
            gzip.decompress(shards[0].read_bytes()),
        )
        self.assertNotIn(
            b"noindex.html",
            b"".join(gzip.decompress(path.read_bytes()) for path in shards),
        )
        self.assertTrue(
            (self.output / pages_stage.STAGE_MANIFEST).is_file()
        )
        self.assertFalse(
            (self.output / pages_stage.SOURCE_INVENTORY).exists()
        )
        self.assertTrue(
            (self.output / pages_stage.SOURCE_INVENTORY_GZIP).is_file()
        )
        self.assertFalse((self.output / "sitemap-extra.xml").exists())
        self.assertTrue((self.output / "sitemap-extra.xml.gz").is_file())
        self.assertTrue((self.output / "sitemap-linked.xml").is_file())
        self.assertFalse((self.output / "sitemap-linked.xml.gz").exists())
        manifest = json.loads(
            gzip.decompress(
                (self.output / pages_stage.STAGE_MANIFEST).read_bytes()
            )
        )
        self.assertGreater(
            manifest["hreflang"]["removed_noindex_relations"],
            0,
        )
        self.assertGreater(
            manifest["minification"]["markdown_links_rewritten_to_html"],
            0,
        )
        self.assertGreater(
            manifest["minification"][
                "missing_markdown_alternates_removed"
            ],
            0,
        )
        self.assertGreater(manifest["sitemaps"]["saved_bytes"], 0)

        second_output = self.base / "output-two"
        second = pages_stage.build_stage(
            self.source,
            second_output,
            max_unpacked_bytes=10_000_000,
        )
        self.assertEqual(first, second)
        first_files = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second_output).as_posix(): path.read_bytes()
            for path in second_output.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)

    def test_final_unpacked_limit_fails_and_removes_partial_output(self) -> None:
        with self.assertRaisesRegex(
            pages_stage.StageError,
            "unpacked regular-file bytes exceed 1",
        ):
            pages_stage.build_stage(
                self.source,
                self.output,
                max_unpacked_bytes=1,
            )
        self.assertFalse(self.output.exists())

    def test_path_symlink_hardlink_and_closure_fail_closed(self) -> None:
        with self.assertRaisesRegex(pages_stage.StageError, "outside"):
            pages_stage.build_stage(
                self.source,
                self.source / "nested-output",
            )

        target = self.source / "index.html"
        link = self.source / "linked.html"
        link.symlink_to(target.name)
        with self.assertRaisesRegex(pages_stage.StageError, "symlink"):
            pages_stage.build_stage(self.source, self.output)
        link.unlink()

        os.link(target, link)
        with self.assertRaisesRegex(pages_stage.StageError, "hard-linked"):
            pages_stage.build_stage(self.source, self.output)
        link.unlink()

        target.write_text(
            html_page(
                "index.html",
                links=("/ios-app-guide/missing.html",),
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(pages_stage.StageError, "URL closure"):
            pages_stage.build_stage(self.source, self.output)
        self.assertFalse(self.output.exists())

        target.write_text(
            html_page("index.html"),
            encoding="utf-8",
        )
        (self.source / "feed.xml").write_text(
            (
                "<feed><link>"
                f"{pages_stage.SITE}/missing.html"
                "</link></feed>"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(pages_stage.StageError, "feed"):
            pages_stage.build_stage(self.source, self.output)
        self.assertFalse(self.output.exists())

        (self.source / "feed.xml").unlink()
        target.write_text(
            html_page("index.html").replace(
                f"{pages_stage.SITE}/index.html",
                f"{pages_stage.SITE}/missing.html",
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(pages_stage.StageError, "canonical"):
            pages_stage.build_stage(self.source, self.output)
        self.assertFalse(self.output.exists())

        target.write_text(
            html_page(
                "index.html",
                hreflang=(
                    ("en-US", f"{pages_stage.SITE}/missing.html"),
                ),
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(pages_stage.StageError, "hreflang"):
            pages_stage.build_stage(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_hash_pinned_json_is_copied_and_unpinned_json_is_minified(
        self,
    ) -> None:
        pinned = b'{\n  "value": 1\n}\n'
        pinned_path = self.source / "data" / "pinned.json"
        pinned_path.parent.mkdir()
        pinned_path.write_bytes(pinned)
        digest = hashlib.sha256(pinned).hexdigest()
        (self.source / "checksums-sha256.txt").write_text(
            f"{digest}  data/pinned.json\n",
            encoding="utf-8",
        )
        unpinned = self.source / "data" / "unpinned.json"
        unpinned.write_text('{\n  "z": 2,\n  "a": 1\n}\n', encoding="utf-8")
        pages_stage.build_stage(
            self.source,
            self.output,
            max_unpacked_bytes=10_000_000,
        )
        self.assertEqual(pinned, (self.output / "data/pinned.json").read_bytes())
        self.assertEqual(
            b'{"a":1,"z":2}\n',
            (self.output / "data/unpinned.json").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
