#!/usr/bin/env python3
"""Serial vs process fan-out equivalence for whole-tree page generators."""

from __future__ import annotations

from concurrent.futures.process import BrokenProcessPool
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import gen_app_store_conversion_surfaces  # noqa: E402
import gen_mobile_app_identity  # noqa: E402
import gen_publisher_disclosures  # noqa: E402
import gen_smart_app_banners  # noqa: E402
import live_app_guard  # noqa: E402
import parallel_pages  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


SITE = "https://example.test/site"
KEYS = ("gmoney", "cyca", "aim990")


def _square(value: int) -> int:
    return value * value


def _fail_on_seven(value: int) -> int:
    if value == 7:
        raise ValueError(f"boom {value}")
    return value


def _manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class _Modes:
    """Run the same callable serially and with a forced process fan-out."""

    serial = {parallel_pages.WORKERS_ENV: "1"}
    parallel = {parallel_pages.WORKERS_ENV: "2"}

    @staticmethod
    def forced():
        # Tiny fixtures must still fan out and cross batch boundaries.
        return mock.patch.multiple(
            parallel_pages, MIN_ITEMS=1, CHUNK_ITEMS=1, BATCH_ITEMS=3,
        )


class OrderedMapTests(unittest.TestCase):
    def test_parallel_results_keep_input_order_across_batches(self):
        items = list(range(20))
        with _Modes.forced(), mock.patch.dict(os.environ, _Modes.parallel):
            self.assertEqual(
                [value * value for value in items],
                list(parallel_pages.ordered_map(_square, items)),
            )

    def test_worker_failure_replays_the_genuine_exception_in_order(self):
        items = list(range(12))
        for env in (_Modes.serial, _Modes.parallel):
            with self.subTest(env=env), _Modes.forced(), mock.patch.dict(os.environ, env):
                seen = []
                with self.assertRaisesRegex(ValueError, r"^boom 7$"):
                    for value in parallel_pages.ordered_map(_fail_on_seven, items):
                        seen.append(value)
                self.assertEqual(list(range(7)), seen)

    def test_broken_pool_degrades_to_in_process_evaluation(self):
        items = list(range(10))
        with _Modes.forced(), mock.patch.dict(os.environ, _Modes.parallel), mock.patch.object(
            parallel_pages.ProcessPoolExecutor, "map", side_effect=BrokenProcessPool("gone"),
        ):
            self.assertEqual(
                [value * value for value in items],
                list(parallel_pages.ordered_map(_square, items)),
            )

    def test_small_inputs_and_non_linux_default_stay_in_process(self):
        with mock.patch.dict(os.environ, {parallel_pages.WORKERS_ENV: ""}), mock.patch.object(
            parallel_pages.sys, "platform", "darwin",
        ):
            self.assertEqual(1, parallel_pages.workers())
        with mock.patch.dict(os.environ, _Modes.parallel), mock.patch.object(
            parallel_pages, "ProcessPoolExecutor",
        ) as pool:
            self.assertEqual([0, 1, 4], list(parallel_pages.ordered_map(_square, range(3))))
        pool.assert_not_called()

    def test_invalid_worker_setting_fails_closed(self):
        for value in ("0", "two", "-1"):
            with self.subTest(value=value), mock.patch.dict(
                os.environ, {parallel_pages.WORKERS_ENV: value},
            ):
                with self.assertRaises(ValueError):
                    parallel_pages.workers()


class GeneratorEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=GEO / "tests")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        env = mock.patch.dict(os.environ, {"APP_STORE_PROVIDER_TOKEN": "118326163"})
        env.start()
        self.addCleanup(env.stop)

    def run_both(self, build, run):
        """Build two identical trees, run serially and fanned out, return both."""
        outcomes = []
        for name, env in (("serial", _Modes.serial), ("parallel", _Modes.parallel)):
            pages = self.root / name
            build(pages)
            with _Modes.forced(), mock.patch.dict(os.environ, env):
                try:
                    result, error = run(pages), None
                except Exception as caught:  # compared across modes below
                    result, error = None, caught
            message = (
                None if error is None
                else (type(error), str(error).replace(str(pages.resolve()), "<pages>").replace(str(pages), "<pages>"))
            )
            outcomes.append((result, message, _manifest(pages)))
        return outcomes

    # -- gen_smart_app_banners._add_single_app_targets -------------------
    def build_answers(self, pages):
        for index in range(9):
            key = KEYS[index % len(KEYS)]
            page = pages / "answers" / f"answer-{index}.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            head = (
                '<meta http-equiv="refresh" content="0;url=/">'
                '<meta name="robots" content="noindex">'
                if index == 4 else ""
            )
            links = (
                f'<a href="https://apps.apple.com/app/id{APPSTORE[key]}">A</a>'
                + (
                    f'<a href="https://apps.apple.com/app/id{APPSTORE["hourstag"]}">B</a>'
                    if index == 6 else ""
                )
            )
            page.write_text(
                f'<html lang="en"><head>{head}</head><body>{links}</body></html>',
                encoding="utf-8",
            )

    def test_single_app_targets_match_serial_including_conflicts(self):
        # Read-only: both modes classify the very same set object, so the
        # merged insertion order must match exactly.
        live_ids = {APPSTORE[key] for key in (*KEYS, "hourstag")}
        pages = self.root / "answers-tree"
        self.build_answers(pages)
        paths = set((pages / "answers").glob("*.html"))
        conflict_path = pages / "answers" / "answer-2.html"

        def run(env, preset):
            targets = dict(preset)
            with _Modes.forced(), mock.patch.dict(os.environ, env):
                try:
                    gen_smart_app_banners._add_single_app_targets(targets, paths, live_ids)
                except ValueError as error:
                    return str(error)
            return list(targets.items())

        for preset in ({}, {conflict_path: APPSTORE["hourstag"]}):
            with self.subTest(conflict=bool(preset)):
                serial = run(_Modes.serial, preset)
                self.assertEqual(serial, run(_Modes.parallel, preset))
                if preset:
                    self.assertIn("Conflicting buyer-intent app IDs", serial)
                else:
                    self.assertEqual(7, len(serial))

    # -- gen_app_store_conversion_surfaces.generate -----------------------
    def conversion_pages(self, pages, *, broken=None):
        written = {}
        for section, locale in (
            ("guides", ""), ("guides", "de-DE"), ("guides", "ja"),
            ("answers", ""), ("answers", "bn-BD"), ("tools", "fr-FR"),
        ):
            for key in KEYS:
                relative = "/".join(part for part in (locale, section, f"{key}.html") if part)
                page = pages / relative
                page.parent.mkdir(parents=True, exist_ok=True)
                lang = locale or "en"
                head = "" if relative == broken else "</head>"
                page.write_text(
                    f'<html lang="{lang}"><head><meta name="viewport" '
                    f'content="width=device-width"><link rel="canonical" '
                    f'href="{SITE}/{relative}">{head}<body><main><p>'
                    f'<a href="https://apps.apple.com/app/id{APPSTORE[key]}">'
                    "Get the app</a></p></main></body></html>",
                    encoding="utf-8",
                )
                written[relative] = (page, key)
        # A buyer-intent page that lost its target still carries old blocks.
        stale = pages / "tools" / "stale.html"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(
            '<html lang="en"><head>\n'
            + gen_smart_app_banners.banner_block(APPSTORE["gmoney"])
            + "\n</head><body></body></html>",
            encoding="utf-8",
        )
        return written, stale

    def conversion_run(self, pages, written, stale):
        def resolved(relatives):
            return frozenset(written[relative][0].resolve() for relative in relatives)

        guides = [r for r in written if "/guides/" in f"/{r}"]
        answers = [r for r in written if "/answers/" in f"/{r}"]
        tools = [r for r in written if "/tools/" in f"/{r}"]
        targets = {
            written[relative][0].resolve(): APPSTORE[written[relative][1]]
            for relative in (*guides, *answers, *tools)
        }
        inventory = gen_smart_app_banners.SurfaceInventory(
            targets=targets,
            app_count=len(KEYS),
            guide_pages=resolved(guides),
            answer_pages=resolved(answers),
            buyer_intent_pages=resolved(tools) | {stale.resolve()},
        )
        with mock.patch.object(
            gen_smart_app_banners, "build_surface_inventory", return_value=inventory,
        ):
            return gen_app_store_conversion_surfaces.generate(pages, set(KEYS), SITE)

    def test_conversion_surfaces_are_byte_identical(self):
        trees = {}

        def build(pages):
            trees[pages] = self.conversion_pages(pages)

        serial, parallel = self.run_both(build, lambda pages: self.conversion_run(pages, *trees[pages]))
        self.assertIsNone(serial[1], serial[1])
        self.assertEqual(serial, parallel)
        stats = serial[0]
        self.assertGreater(stats["app_store_qr_ctas"]["qr_assets"], 0)
        self.assertGreater(stats["smart_app_banners"]["changed_files"], 0)
        self.assertNotIn("apple-itunes-app", serial[2]["tools/stale.html"].decode())
        self.assertNotIn("apps.apple.com", serial[2]["bn-BD/answers/gmoney.html"].decode())

    def test_conversion_failure_leaves_the_serial_disk_state(self):
        trees = {}

        def build(pages):
            trees[pages] = self.conversion_pages(pages, broken="de-DE/guides/cyca.html")

        serial, parallel = self.run_both(build, lambda pages: self.conversion_run(pages, *trees[pages]))
        self.assertEqual(ValueError, serial[1][0])
        self.assertIn("no closing head", serial[1][1])
        self.assertEqual(serial, parallel)
        before = serial[2]["bn-BD/answers/aim990.html"].decode()
        self.assertNotIn("apps.apple.com", before)
        self.assertNotIn("apple-itunes-app", serial[2]["ja/guides/cyca.html"].decode())

    # -- gen_mobile_app_identity.generate ---------------------------------
    def identity_pages(self, pages, *, broken=None):
        targets = {}
        for locale in ("", "de-DE", "ja", "bn-BD"):
            for key in KEYS:
                relative = "/".join(part for part in (locale, "guides", f"{key}.html") if part)
                page = pages / relative
                page.parent.mkdir(parents=True, exist_ok=True)
                body = "{not json" if relative == broken else '{"@context":"https://schema.org","@type":"Article","headline":"Guide"}'
                page.write_text(
                    f'<html lang="{locale or "en"}"><head>'
                    f'<link rel="canonical" href="{SITE}/{relative}">'
                    f'<script type="application/ld+json">{body}</script>'
                    f"</head><body><a href=\"https://apps.apple.com/app/id{APPSTORE[key]}\">Get</a>"
                    "</body></html>",
                    encoding="utf-8",
                )
                targets[page.resolve()] = APPSTORE[key]
        # A guide no longer targeted still carries a managed identity block.
        stale = pages / "guides" / "retired.html"
        template = pages / "guides" / "gmoney.html"
        stale_text, *_ = gen_mobile_app_identity._mobile_identity_update(
            template, APPSTORE["gmoney"], "G+Money", "finance", SITE,
        )
        stale.write_text(stale_text, encoding="utf-8")
        return targets

    def identity_run(self, pages, targets):
        with mock.patch.object(
            gen_smart_app_banners, "build_install_targets",
            return_value=(targets, len(KEYS)),
        ):
            return gen_mobile_app_identity.generate(pages, set(KEYS), SITE)

    def test_mobile_identity_is_byte_identical(self):
        trees = {}

        def build(pages):
            trees[pages] = self.identity_pages(pages)

        serial, parallel = self.run_both(build, lambda pages: self.identity_run(pages, trees[pages]))
        self.assertIsNone(serial[1], serial[1])
        self.assertEqual(serial, parallel)
        self.assertGreater(serial[0]["changed"], 0)
        self.assertNotIn(
            f"id{APPSTORE['gmoney']}", serial[2]["guides/retired.html"].decode().split("</head>")[0],
        )

    def test_mobile_identity_failure_leaves_the_serial_disk_state(self):
        trees = {}

        def build(pages):
            trees[pages] = self.identity_pages(pages, broken="guides/cyca.html")

        serial, parallel = self.run_both(build, lambda pages: self.identity_run(pages, trees[pages]))
        self.assertEqual(ValueError, serial[1][0])
        self.assertIn("Invalid JSON-LD", serial[1][1])
        self.assertEqual(serial, parallel)

    # -- live_app_guard.quarantine_nonlive_pages ---------------------------
    def quarantine_pages(self, site):
        live = APPSTORE["gmoney"]
        dead = "9999999999"
        for index in range(8):
            app_id = dead if index % 3 == 0 else live
            page = site / "apps" / f"app-{index}" / "index.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                '<html><head><meta name="robots" content="index,follow">'
                f'<meta name="apple-itunes-app" content="app-id={app_id}"></head>'
                f'<body><a href="https://apps.apple.com/app/id{app_id}">Get</a></body></html>',
                encoding="utf-8",
            )
            mixed = site / "answers" / f"mixed-{index}.html"
            mixed.parent.mkdir(parents=True, exist_ok=True)
            mixed.write_text(
                '<html><head></head><body>'
                f'<a href="https://apps.apple.com/app/id{live}">Live</a>'
                f'<a href="https://apps.apple.com/app/id{dead}">Dead</a>'
                "</body></html>",
                encoding="utf-8",
            )
        (site / "sitemap_apps.xml").write_text(
            '<?xml version="1.0"?><urlset>'
            + "".join(
                f"<url><loc>https://example.com/apps/app-{index}/</loc></url>"
                for index in range(8)
            )
            + "</urlset>",
            encoding="utf-8",
        )

    def test_quarantine_scan_is_byte_identical(self):
        live_ids = {APPSTORE["gmoney"]}
        serial, parallel = self.run_both(
            self.quarantine_pages,
            lambda site: live_app_guard.quarantine_nonlive_pages(site, apply=True, live_ids=live_ids),
        )
        self.assertIsNone(serial[1], serial[1])
        self.assertEqual(serial, parallel)
        self.assertEqual(3, serial[0]["quarantined_pages"])
        self.assertEqual(1, serial[0]["sitemaps"])


class DisclosureCacheTests(unittest.TestCase):
    def test_each_locale_dictionary_and_target_table_load_once(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            root = Path(directory)
            pages = root / "pages"
            translations = root / "translations"
            translations.mkdir()
            (translations / "de-DE.json").write_text(
                json.dumps({gen_publisher_disclosures.NEW_FOOTER: "Von Lumi Studio verfasst."}),
                encoding="utf-8",
            )
            for locale in ("de-DE", "ja"):
                for index in range(4):
                    page = pages / locale / "answers" / f"a{index}.html"
                    page.parent.mkdir(parents=True, exist_ok=True)
                    page.write_text(
                        f"<p>{gen_publisher_disclosures.OLD_NOTICE}</p>"
                        f"<footer>{gen_publisher_disclosures.OLD_FOOTER}</footer>",
                        encoding="utf-8",
                    )
            real_loader = gen_publisher_disclosures._translations
            real_tables = gen_publisher_disclosures._targets_for_locale
            from_migrate = {"translations": [], "tables": []}

            def caller():
                frame = sys._getframe(2)
                while frame is not None:
                    if frame.f_globals.get("__name__") == gen_publisher_disclosures.__name__:
                        return frame.f_code.co_name
                    frame = frame.f_back
                return None

            def loader(locale, directory):
                if caller() == "migrate":
                    from_migrate["translations"].append(locale)
                return real_loader(locale, directory)

            def tables(locale, translations, structural):
                if caller() == "migrate":
                    from_migrate["tables"].append(locale)
                return real_tables(locale, translations, structural)

            with mock.patch.object(
                gen_publisher_disclosures, "_translations", side_effect=loader,
            ), mock.patch.object(
                gen_publisher_disclosures, "_targets_for_locale", side_effect=tables,
            ):
                stats = gen_publisher_disclosures.migrate(pages, translations_dir=translations)
            self.assertEqual(8, stats["changed_files"])
            self.assertEqual(["de-DE", "ja"], sorted(from_migrate["translations"]))
            self.assertEqual(["de-DE", "ja"], sorted(from_migrate["tables"]))


if __name__ == "__main__":
    unittest.main()
