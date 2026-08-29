#!/usr/bin/env python3

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_sitemap_lastmod  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402


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
                GEO,
                {"answers/example.html"},
                validation_time=datetime(
                    2026,
                    7,
                    14,
                    tzinfo=timezone.utc,
                ),
            )

        self.assertEqual(
            {"answers/example.html": "2026-07-13"},
            dates,
        )
        self.assertIn("--format=@@%ct", run_git.call_args.args[1])
        self.assertIn(
            "answers/example.html",
            run_git.call_args.args[1],
        )

    def test_cross_midnight_reference_uses_current_utc_instant(self) -> None:
        reference = gen_sitemap_lastmod._validation_reference(
            "2026-08-28T23:59:00Z",
            validation_time=datetime(
                2026,
                8,
                29,
                0,
                1,
                tzinfo=timezone.utc,
            ),
        )

        self.assertEqual(
            datetime(2026, 8, 29, 0, 1, tzinfo=timezone.utc),
            reference,
        )

    def test_validation_reference_normalizes_non_utc_host_time(self) -> None:
        reference = gen_sitemap_lastmod._validation_reference(
            "2026-08-28T23:59:00Z",
            validation_time=datetime(
                2026,
                8,
                28,
                17,
                1,
                tzinfo=timezone(timedelta(hours=-7)),
            ),
        )

        self.assertEqual(
            datetime(2026, 8, 29, 0, 1, tzinfo=timezone.utc),
            reference,
        )

    def test_workflow_clock_skew_beyond_contract_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Workflow start time exceeds clock-skew contract",
        ):
            gen_sitemap_lastmod._validation_reference(
                "2026-08-29T00:05:01Z",
                validation_time=datetime(
                    2026,
                    8,
                    29,
                    tzinfo=timezone.utc,
                ),
            )

    def test_git_history_clock_skew_beyond_contract_fails_closed(self) -> None:
        reference = datetime(2026, 8, 28, 23, 58, tzinfo=timezone.utc)
        workflow_floor = reference + gen_sitemap_lastmod.MAX_CLOCK_SKEW
        future = reference + gen_sitemap_lastmod.MAX_CLOCK_SKEW + timedelta(
            seconds=1
        )
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            page = pages / "answers" / "example.html"
            page.parent.mkdir()
            page.write_text("<h1>Example</h1>", encoding="utf-8")
            pages.joinpath("sitemap.xml").write_text(
                urlset(f"<loc>{SITE}/answers/example.html</loc>"),
                encoding="utf-8",
            )
            with mock.patch.object(
                gen_sitemap_lastmod,
                "_run_git",
                return_value=(
                    f"@@{int(future.timestamp())}\n"
                    "answers/example.html\n"
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "Git commit timestamp exceeds clock-skew contract",
                ):
                    gen_sitemap_lastmod.generate(
                        pages,
                        state_path=pages / "state.json",
                        today="2026-08-28",
                        workflow_started_at=workflow_floor,
                        validation_time=reference,
                        dirty_paths=set(),
                    )

    def test_git_history_clock_skew_at_contract_limit_is_accepted(self) -> None:
        reference = datetime(2026, 8, 28, 23, 58, tzinfo=timezone.utc)
        limit = reference + gen_sitemap_lastmod.MAX_CLOCK_SKEW
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            page = pages / "answers" / "example.html"
            page.parent.mkdir()
            page.write_text("<h1>Example</h1>", encoding="utf-8")
            sitemap = pages / "sitemap.xml"
            sitemap.write_text(
                urlset(f"<loc>{SITE}/answers/example.html</loc>"),
                encoding="utf-8",
            )
            with mock.patch.object(
                gen_sitemap_lastmod,
                "_run_git",
                return_value=(
                    f"@@{int(limit.timestamp())}\n"
                    "answers/example.html\n"
                ),
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=pages / "state.json",
                    today="2026-08-28",
                    workflow_started_at=limit,
                    validation_time=reference,
                    dirty_paths=set(),
                )
            self.assertIn(
                "<lastmod>2026-08-29</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )

    def test_malformed_git_history_timestamp_fails_closed(self) -> None:
        with mock.patch.object(
            gen_sitemap_lastmod,
            "_run_git",
            return_value="@@not-a-timestamp\nanswers/example.html\n",
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Malformed Git commit timestamp",
            ):
                gen_sitemap_lastmod.git_history_dates(
                    GEO,
                    {"answers/example.html"},
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        tzinfo=timezone.utc,
                    ),
                )

    def test_current_day_commit_survives_stale_build_date_and_rerun(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            guide = pages / "guides" / "app.html"
            guide.parent.mkdir()
            guide.write_text(
                "<h1>Committed after midnight</h1>",
                encoding="utf-8",
            )
            sitemap = pages / "sitemap.xml"
            sitemap.write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            state = pages / "state.json"
            clock = {
                "today": "2026-08-28",
                "workflow_started_at": "2026-08-28T23:59:00Z",
            }

            commit_time = datetime(
                2026,
                8,
                29,
                0,
                0,
                30,
                tzinfo=timezone.utc,
            )
            with mock.patch.object(
                gen_sitemap_lastmod,
                "_run_git",
                return_value=(
                    f"@@{int(commit_time.timestamp())}\n"
                    "guides/app.html\n"
                ),
            ):
                first = gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        1,
                        tzinfo=timezone.utc,
                    ),
                    dirty_paths=set(),
                    **clock,
                )
            self.assertGreater(first["changed_files"], 0)
            self.assertIn(
                "<lastmod>2026-08-29</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )
            mtimes = {
                path: path.stat().st_mtime_ns for path in (sitemap, state)
            }

            rerun = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                validation_time=datetime(
                    2026,
                    8,
                    29,
                    0,
                    2,
                    tzinfo=timezone.utc,
                ),
                history_dates={},
                dirty_paths=set(),
                **clock,
            )
            self.assertEqual(0, rerun["changed_files"])
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

    def test_true_future_day_fails_closed_after_midnight(self) -> None:
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            guide = pages / "guides" / "app.html"
            guide.parent.mkdir()
            guide.write_text("<h1>Guide</h1>", encoding="utf-8")
            pages.joinpath("sitemap.xml").write_text(
                urlset(f"<loc>{SITE}/guides/app.html</loc>"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "Invalid Git history date",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=pages / "state.json",
                    today="2026-08-28",
                    workflow_started_at="2026-08-28T23:59:00Z",
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        1,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={"guides/app.html": "2026-08-30"},
                    dirty_paths=set(),
                )

    def test_future_build_date_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            with self.assertRaisesRegex(ValueError, "Invalid --today date"):
                gen_sitemap_lastmod.generate(
                    Path(directory),
                    state_path=Path(directory) / "state.json",
                    today="2026-08-30",
                    workflow_started_at="2026-08-28T23:59:00Z",
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        1,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={},
                    dirty_paths=set(),
                )

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

    def test_managed_visual_sitemap_tracks_git_date_and_exact_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            locales = list(OFFICIAL_LOCALES)
            self.assertEqual(50, len(locales))
            gallery_locales = ("en", *locales)
            modified = "2026-08-28"

            def gallery_url(locale: str) -> str:
                return (
                    f"{SITE}/visuals/"
                    if locale == "en"
                    else f"{SITE}/{locale}/visuals/"
                )

            def gallery_path(locale: str) -> Path:
                return (
                    pages / "visuals" / "index.html"
                    if locale == "en"
                    else pages / locale / "visuals" / "index.html"
                )

            def gallery_source(locale: str, marker: str) -> str:
                return (
                    '<html><script type="application/ld+json">'
                    f'{{"dateModified":"{modified}"}}'
                    "</script>"
                    f'<main data-locale="{locale}">{marker}</main></html>'
                )

            for locale in gallery_locales:
                target = gallery_path(locale)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    gallery_source(locale, "baseline"),
                    encoding="utf-8",
                )
            for locale in locales:
                image = pages / "visuals" / locale / "sample.svg"
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_text(
                    f'<svg data-locale="{locale}"></svg>',
                    encoding="utf-8",
                )

            source_dataset = (
                pages / gen_sitemap_lastmod.PUBLISHER_VISUAL_SOURCE_DATASET
            )
            source_dataset.parent.mkdir(parents=True, exist_ok=True)
            source_dataset.write_text(
                '{"records":"synthetic"}\n',
                encoding="utf-8",
            )
            managed = pages / gen_sitemap_lastmod.PUBLISHER_VISUAL_SITEMAP
            managed.write_text(
                urlset(
                    *(
                        f"<loc>{gallery_url(locale)}</loc>"
                        "<lastmod>2026-01-01</lastmod>"
                        for locale in gallery_locales
                    )
                ),
                encoding="utf-8",
            )
            manifest = pages / gen_sitemap_lastmod.PUBLISHER_VISUAL_MANIFEST

            def manifest_document() -> dict[str, object]:
                return {
                    "url": f"{SITE}/visuals/",
                    "dateModified": modified,
                    "source_dataset": (
                        f"{SITE}/"
                        f"{gen_sitemap_lastmod.PUBLISHER_VISUAL_SOURCE_DATASET}"
                    ),
                    "source_sha256": gen_sitemap_lastmod._sha256(
                        source_dataset
                    ),
                    "content_digest": "a" * 64,
                    "generation_digest": "b" * 64,
                    "app_count": 1,
                    "locale_count": len(locales),
                    "image_count": len(locales),
                    "gallery_count": len(gallery_locales),
                    "galleries": [
                        {
                            "locale": locale,
                            "gallery_url": gallery_url(locale),
                            "sha256": gen_sitemap_lastmod._sha256(
                                gallery_path(locale)
                            ),
                        }
                        for locale in gallery_locales
                    ],
                    "records": [
                        {
                            "locale": locale,
                            "app_key": "sample",
                            "app_store_id": "1",
                            "image_url": (
                                f"{SITE}/visuals/{locale}/sample.svg"
                            ),
                            "gallery_url": gallery_url(locale),
                            "canonical_guide_url": (
                                f"{SITE}/apps/sample.html"
                            ),
                            "app_store_url": (
                                "https://apps.apple.com/app/id1"
                            ),
                            "sha256": gen_sitemap_lastmod._sha256(
                                pages
                                / "visuals"
                                / locale
                                / "sample.svg"
                            ),
                        }
                        for locale in locales
                    ],
                }

            def write_manifest() -> None:
                manifest.write_text(
                    json.dumps(
                        manifest_document(),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            write_manifest()

            def git(*args: str, stamp: str | None = None) -> str:
                env = os.environ.copy()
                if stamp is not None:
                    env["GIT_AUTHOR_DATE"] = stamp
                    env["GIT_COMMITTER_DATE"] = stamp
                result = subprocess.run(
                    ["git", *args],
                    cwd=pages,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return result.stdout

            git("init", "--quiet", "--initial-branch=main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            git("config", "commit.gpgsign", "false")
            git("add", ".")
            git(
                "commit",
                "--quiet",
                "-m",
                "baseline",
                stamp="2026-08-28T23:40:00Z",
            )
            git("branch", "remote")

            conflicted_locale = "de-DE"
            conflicted_gallery = gallery_path(conflicted_locale)
            conflicted_gallery.write_text(
                gallery_source(conflicted_locale, "local version"),
                encoding="utf-8",
            )
            git("add", conflicted_gallery.relative_to(pages).as_posix())
            git(
                "commit",
                "--quiet",
                "-m",
                "local gallery",
                stamp="2026-08-28T23:58:00Z",
            )

            git("checkout", "--quiet", "remote")
            conflicted_gallery.write_text(
                gallery_source(conflicted_locale, "remote version"),
                encoding="utf-8",
            )
            git("add", conflicted_gallery.relative_to(pages).as_posix())
            git(
                "commit",
                "--quiet",
                "-m",
                "remote gallery",
                stamp="2026-08-29T00:05:00Z",
            )
            git("checkout", "--quiet", "main")
            git(
                "merge",
                "--quiet",
                "--no-edit",
                "-X",
                "theirs",
                "remote",
                stamp="2026-08-29T00:10:00Z",
            )
            self.assertIn(
                "remote version",
                conflicted_gallery.read_text(encoding="utf-8"),
            )

            state = pages / "state.json"
            with self.assertRaisesRegex(
                ValueError,
                "gallery digest does not match manifest",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today=modified,
                    workflow_started_at="2026-08-28T23:05:00Z",
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        20,
                        tzinfo=timezone.utc,
                    ),
                )

            write_manifest()
            git("add", manifest.relative_to(pages).as_posix())
            git(
                "commit",
                "--quiet",
                "-m",
                "regenerate visual manifest",
                stamp="2026-08-29T00:15:00Z",
            )
            stats = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today=modified,
                workflow_started_at="2026-08-28T23:05:00Z",
                validation_time=datetime(
                    2026,
                    8,
                    29,
                    0,
                    20,
                    tzinfo=timezone.utc,
                ),
            )
            self.assertEqual(51, stats["mapped_urls"])
            root = ET.parse(managed).getroot()
            namespace = {"s": gen_sitemap_lastmod.SITEMAP_NS}
            lastmods = {
                str(entry.findtext("s:loc", namespaces=namespace)): str(
                    entry.findtext("s:lastmod", namespaces=namespace)
                )
                for entry in root.findall("s:url", namespace)
            }
            self.assertEqual(51, len(lastmods))
            self.assertEqual(
                "2026-08-29",
                lastmods[gallery_url(conflicted_locale)],
            )
            self.assertEqual(
                "2026-08-28",
                lastmods[gallery_url("en")],
            )
            state_document = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(
                "2026-08-29",
                state_document["urls"][
                    gallery_url(conflicted_locale)
                ]["lastmod"],
            )

            mtimes = {
                path: path.stat().st_mtime_ns for path in (managed, state)
            }
            rerun = gen_sitemap_lastmod.generate(
                pages,
                state_path=state,
                today=modified,
                workflow_started_at="2026-08-28T23:05:00Z",
                validation_time=datetime(
                    2026,
                    8,
                    29,
                    0,
                    21,
                    tzinfo=timezone.utc,
                ),
            )
            self.assertEqual(0, rerun["changed_files"])
            self.assertEqual(
                mtimes,
                {path: path.stat().st_mtime_ns for path in mtimes},
            )

            manifest_source = manifest.read_text(encoding="utf-8")
            bad_count = json.loads(manifest_source)
            bad_count["gallery_count"] = 50
            manifest.write_text(json.dumps(bad_count), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "Invalid publisher visual manifest contract",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today=modified,
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        21,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={},
                    dirty_paths=set(),
                )
            manifest.write_text(manifest_source, encoding="utf-8")

            source_document = source_dataset.read_text(encoding="utf-8")
            source_dataset.write_text('{"records":"wrong"}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "source digest does not match manifest",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today=modified,
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        21,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={},
                    dirty_paths=set(),
                )
            source_dataset.write_text(source_document, encoding="utf-8")

            image = pages / "visuals" / conflicted_locale / "sample.svg"
            image_document = image.read_text(encoding="utf-8")
            image.write_text("<svg>wrong</svg>", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "Invalid publisher visual manifest record",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today=modified,
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        21,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={},
                    dirty_paths=set(),
                )
            image.write_text(image_document, encoding="utf-8")

            gallery_document = conflicted_gallery.read_text(encoding="utf-8")
            conflicted_gallery.write_text(
                gallery_document.replace(
                    f'"dateModified":"{modified}"',
                    '"dateModified":"2026-08-27"',
                ),
                encoding="utf-8",
            )
            write_manifest()
            with self.assertRaisesRegex(
                ValueError,
                "gallery date does not match manifest",
            ):
                gen_sitemap_lastmod.generate(
                    pages,
                    state_path=state,
                    today=modified,
                    validation_time=datetime(
                        2026,
                        8,
                        29,
                        0,
                        21,
                        tzinfo=timezone.utc,
                    ),
                    history_dates={},
                    dirty_paths={
                        conflicted_gallery.relative_to(pages).as_posix()
                    },
                )
            conflicted_gallery.write_text(
                gallery_document,
                encoding="utf-8",
            )
            manifest.write_text(manifest_source, encoding="utf-8")

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

            # A later final pass can reuse the committed English-stage digest
            # without consulting its next-day Git commit timestamp.
            gen_sitemap_lastmod.generate(
                pages,
                state_path=persistent,
                fallback_state_path=intermediate,
                today="2026-07-14",
                history_dates={},
                dirty_paths=set(),
            )
            self.assertIn(
                "<lastmod>2026-07-14</lastmod>",
                sitemap.read_text(encoding="utf-8"),
            )
            persistent.write_text(stable_state, encoding="utf-8")

            page.write_text("<h1>Stable</h1>", encoding="utf-8")
            restored = gen_sitemap_lastmod.generate(
                pages,
                state_path=persistent,
                fallback_state_path=intermediate,
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
