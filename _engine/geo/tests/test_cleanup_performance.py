from collections import Counter
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import cleanup_localized_assets  # noqa: E402


class CleanupPerformanceTests(unittest.TestCase):
    def test_legacy_slug_regex_is_byte_equivalent_to_replacement_loop(self):
        source = "\n".join(
            (
                f"https://example.test/alternatives/{slug}.html"
                f"?source={index}#details"
            )
            for index, slug in enumerate(
                cleanup_localized_assets.LEGACY_ALT_SLUGS
            )
        )
        expected = source
        for old, new in cleanup_localized_assets.LEGACY_ALT_SLUGS.items():
            expected = expected.replace(
                f"/alternatives/{old}.html",
                f"/alternatives/{new}.html",
            )

        self.assertEqual(
            expected,
            cleanup_localized_assets.replace_legacy_slugs(source),
        )

    def test_cleanup_builds_one_shared_recursive_tree_index(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            (pages / "answers").mkdir()
            (pages / "answers" / "index.html").write_text(
                "<html><head></head><body></body></html>",
                encoding="utf-8",
            )
            calls = []
            original_rglob = Path.rglob

            def counted_rglob(path, pattern, *args, **kwargs):
                calls.append((path, pattern))
                return original_rglob(path, pattern, *args, **kwargs)

            with mock.patch.object(Path, "rglob", counted_rglob):
                cleanup_localized_assets.cleanup(
                    pages,
                    set(cleanup_localized_assets.APPSTORE),
                )

        self.assertEqual([(pages, "*")], calls)

    def test_canonical_lookup_reads_each_sibling_once(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            answer = pages / "answers" / "sample.html"
            answer.parent.mkdir()
            answer.write_text(
                '<link rel="canonical" href="https://example.test/sample">',
                encoding="utf-8",
            )
            tree = cleanup_localized_assets.SiteTreeIndex(pages)
            reads = Counter()
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                reads[path] += 1
                return original_read_text(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", counted_read_text):
                first = cleanup_localized_assets.indexable_canonical_url(
                    answer,
                    "https://fallback.test/one",
                    tree,
                )
                second = cleanup_localized_assets.indexable_canonical_url(
                    answer,
                    "https://fallback.test/two",
                    tree,
                )

        self.assertEqual("https://example.test/sample", first)
        self.assertEqual(first, second)
        self.assertEqual(1, reads[answer])

    def test_hreflang_repair_reads_each_locale_sibling_once(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            paths = [
                pages / "answers" / "sample.html",
                pages / "ja" / "answers" / "sample.html",
                pages / "ko" / "answers" / "sample.html",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                relative = path.relative_to(pages).as_posix()
                path.write_text(
                    '<html><head><link rel="canonical" href="'
                    f'{cleanup_localized_assets.SITE}/{relative}">'
                    "</head><body></body></html>",
                    encoding="utf-8",
                )
            sources = {
                path: path.read_text(encoding="utf-8") for path in paths
            }
            tree = cleanup_localized_assets.SiteTreeIndex(pages)
            reads = Counter()
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                reads[path] += 1
                return original_read_text(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", counted_read_text):
                for path in paths:
                    cleanup_localized_assets.repair_html_hreflang(
                        path,
                        sources[path],
                        pages,
                        {"ja", "ko"},
                        tree,
                    )

        self.assertEqual(3, sum(reads.values()))
        self.assertTrue(all(reads[path] == 1 for path in paths))


if __name__ == "__main__":
    unittest.main()
