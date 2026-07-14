#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_sitemap_lastmod  # noqa: E402


SITE = "https://alice51849.github.io/ios-app-guide"


def urlset(*entries: str) -> str:
    rows = "\n".join(f"  <url>{entry}</url>" for entry in entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</urlset>\n"
    )


def sitemap_index(*locations: str) -> str:
    rows = "\n".join(
        f"  <sitemap><loc>{location}</loc></sitemap>"
        for location in locations
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n"
        "</sitemapindex>\n"
    )


class TruthfulSitemapLastmodTests(unittest.TestCase):
    def test_git_history_dates_normalizes_commit_timestamp_to_utc(self) -> None:
        timestamp = int(
            datetime(
                2026,
                7,
                13,
                18,
                tzinfo=timezone.utc,
            ).timestamp()
        )
        with mock.patch.object(
            gen_sitemap_lastmod,
            "_run_git",
            return_value=f"@@{timestamp}\nanswers/example.html\n",
        ) as run_git:
            dates = gen_sitemap_lastmod.git_history_dates(
                Path("/tmp/site"),
                {"answers/example.html"},
            )

        self.assertEqual(
            {"answers/example.html": "2026-07-13"},
            dates,
        )
        self.assertIn("--format=@@%ct", run_git.call_args.args[1])

    def test_history_bootstrap_hash_changes_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            (pages / "answers").mkdir()
            guide = pages / "guides/app.html"
            answer = pages / "answers/question.html"
            guide.write_text("<h1>Guide v1</h1>", encoding="utf-8")
            answer.write_text("<h1>Answer v1</h1>", encoding="utf-8")

            root_sitemap = pages / "sitemap.xml"
            guide_sitemap = pages / "sitemap_guides.xml"
            answer_sitemap = pages / "sitemap_answers.xml"
            root_sitemap.write_text(
                urlset(
                    f"<loc>{SITE}/guides/app.html</loc>",
                ),
                encoding="utf-8",
            )
            guide_sitemap.write_text(
                urlset(
                    f"<loc>{SITE}/guides/app.html</loc>",
                ),
                encoding="utf-8",
            )
            answer_sitemap.write_text(
                urlset(
                    f"<loc>{SITE}/answers/question.html</loc>"
                    "<lastmod>2026-01-01</lastmod>",
                ),
                encoding="utf-8",
            )
            pages.joinpath("sitemap_index.xml").write_text(
                sitemap_index(
                    f"{SITE}/sitemap.xml",
                    f"{SITE}/sitemap_guides.xml",
                    f"{SITE}/sitemap_answers.xml",
                ),
                encoding="utf-8",
            )
            state = pages / "lastmod-state.json"
            history = {
                "guides/app.html": "2026-06-01",
                "answers/question.html": "2026-06-02",
                "sitemap.xml": "2026-06-03",
                "sitemap_guides.xml": "2026-06-04",
                "sitemap_answers.xml": "2026-06-05",
            }

            first = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-14",
                history_dates=history,
                dirty_paths=set(),
            )
            self.assertEqual(3, first["entries"])
            self.assertEqual(2, first["mapped_urls"])
            self.assertEqual(0, first["excluded_entries"])
            self.assertEqual(3, first["index_entries"])
            self.assertIn(
                "<lastmod>2026-06-01</lastmod>",
                root_sitemap.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "<lastmod>2026-06-01</lastmod>",
                guide_sitemap.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "<lastmod>2026-06-02</lastmod>",
                answer_sitemap.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                3,
                pages.joinpath("sitemap_index.xml")
                .read_text(encoding="utf-8")
                .count("<lastmod>2026-07-14</lastmod>"),
            )

            mtimes = {
                path: path.stat().st_mtime_ns
                for path in (
                    root_sitemap,
                    guide_sitemap,
                    answer_sitemap,
                    pages / "sitemap_index.xml",
                    state,
                )
            }
            second = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-15",
                history_dates=history,
                dirty_paths=set(),
            )
            self.assertEqual(0, second["changed_dates"])
            self.assertEqual(0, second["changed_files"])
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

            guide.write_text("<h1>Guide v2</h1>", encoding="utf-8")
            third = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-16",
                history_dates=history,
                dirty_paths={"guides/app.html"},
            )
            self.assertGreater(third["changed_dates"], 0)
            self.assertIn(
                "<lastmod>2026-07-16</lastmod>",
                root_sitemap.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "<lastmod>2026-07-16</lastmod>",
                guide_sitemap.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "<lastmod>2026-06-02</lastmod>",
                answer_sitemap.read_text(encoding="utf-8"),
            )
            index_source = pages.joinpath("sitemap_index.xml").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                2,
                index_source.count("<lastmod>2026-07-16</lastmod>"),
            )
            self.assertEqual(
                1,
                index_source.count("<lastmod>2026-07-14</lastmod>"),
            )
            state_document = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(
                "2026-07-16",
                state_document["urls"][
                    f"{SITE}/guides/app.html"
                ]["lastmod"],
            )

    def test_out_of_scope_preserved_and_bad_urls_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            pages.joinpath("guides/app.html").write_text(
                "<h1>Guide</h1>",
                encoding="utf-8",
            )
            sitemap = pages / "sitemap_resourcesync.xml"
            sitemap.write_text(
                urlset(
                    f"<loc>{SITE}/guides/app.html</loc>",
                    "<loc>https://alice51849.github.io/"
                    ".well-known/resourcesync</loc>"
                    "<lastmod>2026-06-01</lastmod>",
                ),
                encoding="utf-8",
            )
            pages.joinpath("sitemap_index.xml").write_text(
                sitemap_index(f"{SITE}/sitemap_resourcesync.xml"),
                encoding="utf-8",
            )
            stats = gen_sitemap_lastmod.generate(
                pages,
                state_path=pages / "state.json",
                today="2026-07-14",
                history_dates={
                    "guides/app.html": "2026-06-02",
                    "sitemap_resourcesync.xml": "2026-06-03",
                },
                dirty_paths=set(),
            )
            self.assertEqual(1, stats["excluded_entries"])
            source = sitemap.read_text(encoding="utf-8")
            self.assertIn(
                ".well-known/resourcesync</loc>"
                "<lastmod>2026-06-01</lastmod>",
                source,
            )

            bad_cases = (
                f"{SITE}/missing.html",
                f"{SITE}/%2e%2e/private.html",
                "https://example.com/app.html",
            )
            for bad_url in bad_cases:
                with self.subTest(url=bad_url):
                    sitemap.write_text(
                        urlset(f"<loc>{bad_url}</loc>"),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ValueError):
                        gen_sitemap_lastmod.generate(
                            pages,
                            state_path=pages / "state.json",
                            today="2026-07-14",
                            history_dates={},
                            dirty_paths=set(),
                        )

    def test_future_or_corrupt_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            page = pages / "guides/app.html"
            page.write_text("<h1>Guide</h1>", encoding="utf-8")
            pages.joinpath("sitemap.xml").write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            state = pages / "state.json"
            gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-14",
                history_dates={"guides/app.html": "2026-06-01"},
                dirty_paths=set(),
            )
            document = json.loads(state.read_text(encoding="utf-8"))
            document["urls"][f"{SITE}/guides/app.html"][
                "lastmod"
            ] = "2099-01-01"
            state.write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "Invalid sitemap lastmod state record",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today="2026-07-14",
                    history_dates={},
                    dirty_paths=set(),
                )

    def test_clean_target_without_history_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            pages.joinpath("guides/app.html").write_text(
                "<h1>Guide</h1>",
                encoding="utf-8",
            )
            pages.joinpath("sitemap.xml").write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "No Git history date for clean sitemap target",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=pages / "state.json",
                    today="2026-07-14",
                    history_dates={},
                    dirty_paths=set(),
                )

            stats = gen_sitemap_lastmod.generate(
                pages,
                state_path=pages / "state.json",
                today="2026-07-14",
                history_dates={},
                dirty_paths={"guides/app.html"},
            )
            self.assertEqual(1, stats["mapped_urls"])
            self.assertIn(
                "<lastmod>2026-07-14</lastmod>",
                pages.joinpath("sitemap.xml").read_text(encoding="utf-8"),
            )

    def test_intermediate_state_cannot_pollute_final_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            page = pages / "guides/app.html"
            page.write_text("<h1>Stable</h1>", encoding="utf-8")
            sitemap = pages / "sitemap.xml"
            sitemap.write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            persistent = pages / "persistent.json"
            intermediate = pages / "intermediate.json"
            gen_sitemap_lastmod.generate(
                pages,
                state_path=persistent,
                today="2026-07-13",
                history_dates={"guides/app.html": "2026-06-01"},
                dirty_paths=set(),
            )
            stable_state = persistent.read_text(encoding="utf-8")
            intermediate.write_text(stable_state, encoding="utf-8")

            page.write_text("<h1>Temporary English stage</h1>", encoding="utf-8")
            gen_sitemap_lastmod.generate(
                pages,
                state_path=intermediate,
                today="2026-07-14",
                history_dates={},
                dirty_paths={"guides/app.html"},
            )
            self.assertIn(
                "<lastmod>2026-07-14</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                stable_state,
                persistent.read_text(encoding="utf-8"),
            )

            page.write_text("<h1>Stable</h1>", encoding="utf-8")
            restored = gen_sitemap_lastmod.generate(
                pages,
                state_path=persistent,
                today="2026-07-14",
                history_dates={},
                dirty_paths=set(),
            )
            self.assertGreater(restored["changed_dates"], 0)
            self.assertIn(
                "<lastmod>2026-06-01</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                stable_state,
                persistent.read_text(encoding="utf-8"),
            )
            idempotent = gen_sitemap_lastmod.generate(
                pages,
                state_path=persistent,
                today="2026-07-15",
                history_dates={},
                dirty_paths=set(),
            )
            self.assertEqual(0, idempotent["changed_files"])

    def test_clean_committed_change_recovers_git_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            (pages / "guides").mkdir()
            page = pages / "guides/app.html"
            page.write_text("<h1>Version one</h1>", encoding="utf-8")
            sitemap = pages / "sitemap.xml"
            sitemap.write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            state = pages / "state.json"
            gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-10",
                history_dates={"guides/app.html": "2026-07-01"},
                dirty_paths=set(),
            )

            page.write_text(
                "<h1>Committed while prior run stopped</h1>",
                encoding="utf-8",
            )
            gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today="2026-07-14",
                history_dates={"guides/app.html": "2026-07-12"},
                dirty_paths=set(),
            )
            self.assertIn(
                "<lastmod>2026-07-12</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
