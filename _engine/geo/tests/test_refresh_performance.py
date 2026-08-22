import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_publisher_disclosures  # noqa: E402
import gen_app_store_conversion_surfaces  # noqa: E402
import gen_app_store_qr_ctas  # noqa: E402
import gen_app_store_share_ctas  # noqa: E402
import gen_guide_design  # noqa: E402
import gen_mobile_store_ctas  # noqa: E402
import gen_smart_app_banners  # noqa: E402
import reconcile_answer_semantics  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


def guide_workflow() -> str:
    root = Path(os.environ.get("GEO_GUIDE_ROOT", GEO.parents[1]))
    path = root / ".github" / "workflows" / "geo-daily.yml"
    if not path.is_file():
        raise unittest.SkipTest("materialized Guide workflow is unavailable")
    return path.read_text(encoding="utf-8")


class RefreshPerformanceTests(unittest.TestCase):
    def test_combined_conversion_pass_is_byte_equivalent(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            root = Path(directory)
            sequential = root / "sequential"
            combined = root / "combined"
            app_id = str(next(iter(APPSTORE.values())))
            site = "https://example.test/site"
            source = (
                '<html lang="en"><head><meta name="viewport" '
                'content="width=device-width"><link rel="canonical" '
                f'href="{site}/guides/app.html"></head><body><main><p>'
                f'<a href="https://apps.apple.com/app/id{app_id}">'
                "Get the app</a></p></main></body></html>"
            )
            for pages in (sequential, combined):
                for section in ("guides", "answers"):
                    page = pages / section / "app.html"
                    page.parent.mkdir(parents=True)
                    page.write_text(source, encoding="utf-8")

            def inventory(pages):
                guide = (pages / "guides" / "app.html").resolve()
                answer = (pages / "answers" / "app.html").resolve()
                return gen_smart_app_banners.SurfaceInventory(
                    targets={guide: app_id, answer: app_id},
                    app_count=1,
                    guide_pages=frozenset({guide}),
                    answer_pages=frozenset({answer}),
                    buyer_intent_pages=frozenset(),
                )

            sequential_inventory = inventory(sequential)
            gen_smart_app_banners.generate(
                sequential,
                site=site,
                inventory=sequential_inventory,
            )
            gen_mobile_store_ctas.generate(
                sequential,
                site=site,
                inventory=sequential_inventory,
            )
            gen_app_store_qr_ctas.generate(
                sequential,
                site=site,
                inventory=sequential_inventory,
            )
            gen_app_store_share_ctas.generate(
                sequential,
                site=site,
                inventory=sequential_inventory,
            )

            with mock.patch.object(
                gen_smart_app_banners,
                "build_surface_inventory",
                return_value=inventory(combined),
            ) as build_inventory:
                gen_app_store_conversion_surfaces.generate(
                    combined,
                    live_keys={"app"},
                    site=site,
                )

            def manifest(pages):
                return {
                    path.relative_to(pages).as_posix(): path.read_bytes()
                    for path in pages.rglob("*")
                    if path.is_file()
                }

            sequential_manifest = manifest(sequential)
            combined_manifest = manifest(combined)
            combined_answer = (
                combined / "answers" / "app.html"
            ).read_text(encoding="utf-8")

        build_inventory.assert_called_once()
        self.assertEqual(sequential_manifest, combined_manifest)
        self.assertIsNotNone(
            gen_smart_app_banners.BLOCK_RE.search(combined_answer)
        )
        self.assertIsNone(
            gen_mobile_store_ctas.BLOCK_RE.search(combined_answer)
        )
        self.assertIsNone(
            gen_app_store_qr_ctas.CARD_BLOCK_RE.search(combined_answer)
        )
        self.assertIsNone(
            gen_app_store_share_ctas.BLOCK_RE.search(combined_answer)
        )

    def test_workflow_uses_shared_conversion_inventory_three_times(self):
        workflow = guide_workflow()
        sequence = (
            "          python3 cleanup_localized_assets.py --cached-live\n"
            "          python3 gen_app_store_conversion_surfaces.py"
        )
        self.assertEqual(3, workflow.count(sequence))
        self.assertEqual(
            3,
            workflow.count("gen_app_store_conversion_surfaces.py"),
        )
        for legacy_cli in (
            "gen_smart_app_banners.py",
            "gen_mobile_store_ctas.py",
            "gen_app_store_qr_ctas.py",
            "gen_app_store_share_ctas.py",
        ):
            self.assertNotIn(legacy_cli, workflow)
        for module in (
            gen_smart_app_banners,
            gen_mobile_store_ctas,
            gen_app_store_qr_ctas,
            gen_app_store_share_ctas,
        ):
            self.assertTrue(callable(module.generate))
            self.assertTrue(callable(module.main))

    def test_unchanged_write_check_reuses_loaded_source(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            page = Path(directory) / "guide.html"
            page.write_text(
                '<html><head><meta name="viewport" content="width=device-width">'
                "</head><body></body></html>",
                encoding="utf-8",
            )
            reads = 0
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                nonlocal reads
                reads += int(path == page)
                return original_read_text(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", counted_read_text):
                gen_guide_design.ensure_design(page, "/assets/guide.css")

        self.assertEqual(1, reads)

    def test_single_app_target_reads_each_page_once(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            live_id = str(next(iter(APPSTORE.values())))
            eligible = pages / "eligible.html"
            redirect = pages / "redirect.html"
            eligible.write_text(
                f'<a href="https://apps.apple.com/app/id{live_id}">App</a>',
                encoding="utf-8",
            )
            redirect.write_text(
                '<meta http-equiv="refresh" content="0;url=/">'
                '<meta name="robots" content="noindex">'
                f'<a href="https://apps.apple.com/app/id{live_id}">App</a>',
                encoding="utf-8",
            )
            reads = []
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                reads.append(path)
                return original_read_text(path, *args, **kwargs)

            targets = {}
            with mock.patch.object(Path, "read_text", counted_read_text):
                gen_smart_app_banners._add_single_app_targets(
                    targets,
                    {eligible, redirect},
                    {live_id},
                )

        self.assertEqual({eligible: live_id}, targets)
        self.assertEqual(1, reads.count(eligible))
        self.assertEqual(1, reads.count(redirect))

    def test_semantic_repair_reuses_source_for_repair_and_audit(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            page = pages / "answers" / "sample.html"
            page.parent.mkdir()
            page.write_text("source", encoding="utf-8")
            reads = 0
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                nonlocal reads
                reads += int(path == page)
                return original_read_text(path, *args, **kwargs)

            with (
                mock.patch.object(
                    reconcile_answer_semantics,
                    "_english_answer_paths",
                    return_value=[page],
                ),
                mock.patch.object(
                    reconcile_answer_semantics,
                    "_localized_answer_dirs",
                    return_value=[],
                ),
                mock.patch.object(
                    reconcile_answer_semantics,
                    "refresh_cross_topic_page",
                    return_value=False,
                ),
                mock.patch.object(
                    reconcile_answer_semantics,
                    "planned_page_metadata_repair",
                    return_value=None,
                ),
                mock.patch.object(
                    reconcile_answer_semantics,
                    "_audit_english_source",
                ),
                mock.patch.object(Path, "read_text", counted_read_text),
            ):
                reconcile_answer_semantics.repair(pages)

        self.assertEqual(1, reads)

    def test_disclosure_candidates_include_tracked_and_untracked_pages(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            answers = pages / "answers"
            localized = pages / "ja" / "answers"
            answers.mkdir(parents=True)
            localized.mkdir(parents=True)
            tracked = answers / "tracked.html"
            clean = answers / "clean.html"
            untracked = localized / "untracked.html"
            tracked.write_text(
                gen_publisher_disclosures.OLD_NOTICE,
                encoding="utf-8",
            )
            clean.write_text("No disclosure marker", encoding="utf-8")
            untracked.write_text(
                gen_publisher_disclosures.NEW_NOTICE,
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "init", "--quiet", str(pages)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(pages), "add", str(tracked), str(clean)],
                check=True,
            )

            all_pages = gen_publisher_disclosures._answer_pages(pages)
            candidates = gen_publisher_disclosures._git_candidate_pages(
                pages,
                all_pages,
            )

        self.assertIsNotNone(candidates)
        self.assertEqual(
            {"answers/tracked.html", "ja/answers/untracked.html"},
            {
                path.relative_to(pages).as_posix()
                for path in candidates or ()
            },
        )

    def test_disclosure_scan_count_still_reports_full_locale_coverage(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = Path(directory)
            answers = pages / "answers"
            localized = pages / "ja" / "answers"
            translations = pages / "translations"
            answers.mkdir(parents=True)
            localized.mkdir(parents=True)
            translations.mkdir()
            (answers / "clean.html").write_text(
                "No disclosure marker",
                encoding="utf-8",
            )
            legacy = localized / "legacy.html"
            legacy.write_text(
                gen_publisher_disclosures.OLD_NOTICE,
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "init", "--quiet", str(pages)],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(pages), "add", "."],
                check=True,
            )

            stats = gen_publisher_disclosures.migrate(
                pages,
                translations_dir=translations,
            )
            rendered = legacy.read_text(encoding="utf-8")

        self.assertEqual(2, stats["scanned_files"])
        self.assertEqual(1, stats["changed_files"])
        self.assertNotIn(
            gen_publisher_disclosures.OLD_NOTICE,
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
