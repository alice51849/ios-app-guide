from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parents[1]
sys.path.insert(0, str(GEO))

import add_related_tools  # noqa: E402
import aeo_answers_i18n  # noqa: E402
import build_pages_i18n  # noqa: E402
import i18n_harvest_existing  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402


def guide_workflow() -> str:
    root = Path(os.environ.get("GEO_GUIDE_ROOT", ROOT))
    path = root / ".github" / "workflows" / "geo-daily.yml"
    if not path.is_file():
        raise unittest.SkipTest("materialized Guide workflow is unavailable")
    return path.read_text(encoding="utf-8")


class PipelineAccelerationTests(unittest.TestCase):
    def test_missing_app_materialization_keeps_all_locale_coverage(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as temporary:
            pages = Path(temporary)
            for locale in ("en-US", "ja"):
                (pages / locale).mkdir()
                (pages / locale / "complete.html").write_text(
                    "complete",
                    encoding="utf-8",
                )
            (pages / "en-US" / "partial.html").write_text(
                "partial",
                encoding="utf-8",
            )
            with (
                mock.patch.object(build_pages_i18n, "PAGES", str(pages)),
                mock.patch.object(
                    build_pages_i18n,
                    "all_locales_for",
                    return_value=["en-US", "ja"],
                ),
            ):
                missing = build_pages_i18n.missing_page_keys(
                    ["complete", "partial", "new"]
                )
            self.assertEqual(["partial", "new"], missing)

    def test_materialization_rejects_empty_live_registry(self):
        with self.assertRaisesRegex(
            SystemExit,
            "No verified publicly available apps",
        ):
            build_pages_i18n.materialization_plan([], [], [], True)

    def test_missing_apps_rejects_positional_locale_filter(self):
        with self.assertRaisesRegex(
            SystemExit,
            "cannot be combined with positional locales",
        ):
            build_pages_i18n.materialization_plan(
                ["app"],
                [],
                ["ja"],
                True,
            )

    def test_publication_locales_stay_at_official_fifty(self):
        with (
            mock.patch.object(
                build_pages_i18n,
                "master_locales_for",
                return_value=list(OFFICIAL_LOCALES),
            ),
            mock.patch.object(
                build_pages_i18n,
                "missing_page_keys",
                return_value=[],
            ),
        ):
            keys, publication_locales, render_locales = (
                build_pages_i18n.materialization_plan(
                    ["app"],
                    [],
                    [],
                    True,
                )
            )
        self.assertEqual([], keys)
        self.assertEqual(list(OFFICIAL_LOCALES), publication_locales)
        self.assertEqual(list(OFFICIAL_LOCALES), render_locales)
        self.assertEqual(50, len(publication_locales))

    def test_positional_locale_only_limits_rendering_not_publication(self):
        with mock.patch.object(
            build_pages_i18n,
            "master_locales_for",
            return_value=list(OFFICIAL_LOCALES),
        ):
            keys, publication_locales, render_locales = (
                build_pages_i18n.materialization_plan(
                    ["app"],
                    [],
                    ["ja"],
                    False,
                )
            )
        self.assertEqual(["app"], keys)
        self.assertEqual(list(OFFICIAL_LOCALES), publication_locales)
        self.assertEqual(["ja"], render_locales)

    def test_write_if_changed_preserves_unchanged_file(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as temporary:
            path = Path(temporary) / "page.html"
            path.write_text("same", encoding="utf-8")
            before = path.stat().st_mtime_ns
            self.assertFalse(
                build_pages_i18n.write_text_if_changed(path, "same")
            )
            self.assertEqual(before, path.stat().st_mtime_ns)
            self.assertTrue(
                build_pages_i18n.write_text_if_changed(path, "changed")
            )
            self.assertEqual("changed", path.read_text(encoding="utf-8"))

    def test_new_page_source_is_extracted_once_for_all_locales(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as temporary:
            root = Path(temporary)
            answers = root / "answers"
            translations = root / "trans"
            answers.mkdir()
            translations.mkdir()
            source = "<main>Hello source</main>"
            (answers / "sample.html").write_text(
                source,
                encoding="utf-8",
            )
            actual_extract = aeo_answers_i18n.extract_strings
            strings = actual_extract(source)[0]
            for locale in OFFICIAL_LOCALES:
                (translations / f"{locale}.json").write_text(
                    json.dumps(
                        {
                            value: f"{locale} translation {index}"
                            for index, value in enumerate(strings)
                        }
                    ),
                    encoding="utf-8",
                )
            with (
                mock.patch.object(aeo_answers_i18n, "ROOT", root),
                mock.patch.object(aeo_answers_i18n, "ANSWERS", answers),
                mock.patch.object(
                    aeo_answers_i18n,
                    "extract_strings",
                    wraps=actual_extract,
                ) as extracted,
                mock.patch.object(
                    aeo_answers_i18n,
                    "apply_locale_text_overrides",
                    side_effect=lambda mapping, _lang: mapping,
                ),
                mock.patch.object(
                    aeo_answers_i18n,
                    "require_complete_mapping",
                ),
                mock.patch.object(
                    aeo_answers_i18n,
                    "require_translation_quality",
                ),
                mock.patch.object(
                    aeo_answers_i18n,
                    "finalize_html",
                    side_effect=lambda rendered, _lang, _slug: rendered,
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "aeo_answers_i18n.py",
                        "sample",
                        "--langs",
                        " ".join(OFFICIAL_LOCALES),
                        "--trans",
                        str(translations),
                        "--defer-shared-refresh",
                    ],
                ),
            ):
                self.assertEqual(0, aeo_answers_i18n.main())
            self.assertEqual(1, extracted.call_count)
            generated = list(root.glob("*/answers/sample.html"))
            self.assertEqual(50, len(generated))
            self.assertEqual(
                "<main>ja translation 0</main>",
                (root / "ja" / "answers" / "sample.html").read_text(),
            )

    def test_harvest_reuses_english_parse_across_locales(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as temporary:
            pages = Path(temporary)
            (pages / "answers").mkdir()
            for locale, text in (
                ("ja", "translated Japanese text"),
                ("ko", "translated Korean text"),
            ):
                (pages / locale / "answers").mkdir(parents=True)
                (pages / locale / "answers" / "sample.html").write_text(
                    text,
                    encoding="utf-8",
                )
            (pages / "answers" / "sample.html").write_text(
                "English source phrase",
                encoding="utf-8",
            )

            def extracted(source):
                return [], [(0, len(source), source, "text")], []

            cache = {}
            parser = mock.Mock(side_effect=extracted)
            with (
                mock.patch.object(i18n_harvest_existing, "PAGES", pages),
                mock.patch.object(
                    i18n_harvest_existing._i18n,
                    "extract_strings",
                    parser,
                ),
                mock.patch.object(
                    i18n_harvest_existing,
                    "validate",
                    return_value=None,
                ),
            ):
                i18n_harvest_existing.harvest(
                    "ja",
                    link_labels=set(),
                    english_cache=cache,
                )
                i18n_harvest_existing.harvest(
                    "ko",
                    link_labels=set(),
                    english_cache=cache,
                )
            self.assertEqual(3, parser.call_count)
            self.assertEqual(["sample.html"], list(cache))

    def test_related_tools_batches_all_locales_in_one_process(self):
        canonical = [("tool", "source", ("123",), "Tool")]
        with (
            mock.patch.object(
                add_related_tools,
                "load_canonical_tools",
                return_value=canonical,
            ) as load,
            mock.patch.object(add_related_tools, "apply_locale") as apply,
            mock.patch.object(
                sys,
                "argv",
                [
                    "add_related_tools.py",
                    "--all-official-locales",
                    "--dry-run",
                ],
            ),
        ):
            self.assertEqual(0, add_related_tools.main())
        load.assert_called_once_with()
        self.assertEqual(1 + len(OFFICIAL_LOCALES), apply.call_count)
        self.assertEqual(
            ["", *OFFICIAL_LOCALES],
            [call.args[0] for call in apply.call_args_list],
        )
        self.assertTrue(
            all(call.kwargs["dry"] for call in apply.call_args_list)
        )

    def test_workflow_uses_incremental_and_batched_modes(self):
        workflow = guide_workflow()
        self.assertIn(
            "build_pages_i18n.py --cached-live --missing-apps",
            workflow,
        )
        self.assertEqual(
            2,
            workflow.count(
                "add_related_tools.py --all-official-locales"
            ),
        )
        self.assertNotIn(
            "add_related_tools.py --locale \"$locale\"",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
