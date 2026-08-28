from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


GEO = Path(__file__).resolve().parent.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))
SOCIAL = GEO.parent / "social"
if str(SOCIAL) not in sys.path:
    sys.path.insert(0, str(SOCIAL))

from appstore_live import live_app_keys  # noqa: E402
import close_sitemap_graph  # noqa: E402
import gen_link_hubs  # noqa: E402
import gen_locale_indexation  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
import parallel_unittest  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402
import verified_tree  # noqa: E402


SITE = "https://example.test/site"


def page(lang: str, title: str, body: str = "") -> str:
    return (
        f'<!doctype html><html lang="{lang}"><head>'
        f"<title>{title}</title></head><body><main>{body}</main>"
        "</body></html>"
    )


def urlset(*urls: str) -> str:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</urlset>"
    )


def sitemap_index(*urls: str) -> str:
    entries = "".join(
        f"<sitemap><loc>{url}</loc></sitemap>" for url in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</sitemapindex>"
    )


class SharedClosureTests(unittest.TestCase):
    def build_site(self, root: Path) -> Path:
        pages = root / "pages"
        locale = pages / "ja"
        locale.mkdir(parents=True)
        (pages / "index.html").write_text(
            page("en", "Home"),
            encoding="utf-8",
        )
        (locale / "index.html").write_text(
            page("ja", "Japanese"),
            encoding="utf-8",
        )
        (locale / "alpha.html").write_text(
            page("ja", "Alpha"),
            encoding="utf-8",
        )
        (locale / "beta.html").write_text(
            page("ja", "Beta"),
            encoding="utf-8",
        )
        urls = (
            f"{SITE}/index.html",
            f"{SITE}/ja/index.html",
            f"{SITE}/ja/alpha.html",
            f"{SITE}/ja/beta.html",
        )
        (pages / "sitemap.xml").write_text(
            urlset(*urls),
            encoding="utf-8",
        )
        (pages / "sitemap_index.xml").write_text(
            sitemap_index(f"{SITE}/sitemap.xml"),
            encoding="utf-8",
        )
        (pages / "robots.txt").write_text(
            f"Sitemap: {SITE}/sitemap_index.xml\n",
            encoding="utf-8",
        )
        return pages

    def test_hub_only_changes_skip_second_sitemap_pass_and_converge(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = self.build_site(Path(directory))
            with (
                mock.patch.object(gen_link_hubs, "SITE", SITE),
                mock.patch.object(gen_locale_indexation, "SITE", SITE),
            ):
                first = close_sitemap_graph.close_graph(pages)
                second = close_sitemap_graph.close_graph(pages)

            self.assertEqual(0, first["second_indexation"])
            self.assertGreater(first["hub_changes"], 0)
            self.assertEqual(0, first["verification_changes"])
            self.assertEqual(0, second["second_indexation"])
            self.assertEqual(0, second["hub_changes"])
            browse = pages / "ja" / "browse.html"
            self.assertIn(
                'name="robots" content="noindex,follow"',
                browse.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "/ja/browse.html",
                (pages / "sitemap.xml").read_text(encoding="utf-8"),
            )

    def test_indexable_hub_drift_runs_second_sitemap_pass(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            pages = self.build_site(Path(directory))
            calls = 0

            def mutate(pages_arg, *, check, tree):
                nonlocal calls
                calls += 1
                if not check:
                    relative = "new-indexable.html"
                    source = page("en", "New")
                    (Path(pages_arg) / relative).write_text(
                        source,
                        encoding="utf-8",
                    )
                    tree.update_source(relative, source)
                    return {
                        "parents": 0,
                        "changed": [relative],
                        "tree": tree,
                    }
                return {"parents": 0, "changed": [], "tree": tree}

            with (
                mock.patch.object(gen_link_hubs, "SITE", SITE),
                mock.patch.object(gen_locale_indexation, "SITE", SITE),
                mock.patch.object(
                    gen_link_hubs,
                    "run_link_hubs",
                    side_effect=mutate,
                ),
            ):
                result = close_sitemap_graph.close_graph(pages)

            self.assertEqual(2, calls)
            self.assertEqual(1, result["second_indexation"])
            self.assertIn(
                "new-indexable.html",
                (pages / "sitemap_orphans.xml").read_text(
                    encoding="utf-8"
                ),
            )


class PublishedMatrixTests(unittest.TestCase):
    def test_every_live_app_has_all_50_localized_guide_pages(self):
        pages = Path(gen_locale_indexation.PAGES)
        if not pages.is_dir() or not (pages / "en-US").is_dir():
            self.skipTest("materialized Pages tree is unavailable")
        keys = sorted(
            live_app_keys(
                APPSTORE,
                str(pages),
                refresh=False,
            )
        )
        # A floor, not an exact count. The real assertion is the one below --
        # every live app carries all 50 locales -- and this only guards against
        # the live set collapsing to a handful and making that pass vacuously.
        # Pinning the exact number meant every launch failed the daily run:
        # ShotInbox AI shipping on 2026-08-24 took it from 43 to 44.
        self.assertGreaterEqual(len(keys), len(APPSTORE) - 3)
        self.assertEqual(50, len(OFFICIAL_LOCALES))
        missing = [
            f"{locale}/{key}.html"
            for locale in OFFICIAL_LOCALES
            for key in keys
            if not (pages / locale / f"{key}.html").is_file()
        ]
        self.assertEqual([], missing)


class VerifiedTreeTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def repository(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.name", "Test")
        self.git(repo, "config", "user.email", "test@example.com")
        (repo / "page.html").write_text("v1", encoding="utf-8")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", "initial")
        return repo

    def test_exact_committed_tree_reuses_full_suite_attestation(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            root = Path(directory)
            repo = self.repository(root)
            attestation = root / "verified.json"
            (repo / "page.html").write_text("v2", encoding="utf-8")

            verified_tree.prepare(repo, attestation, "full-suite")
            verified_tree.seal(repo, attestation, "full-suite")
            self.git(repo, "commit", "-q", "-m", "tested")
            self.assertTrue(
                verified_tree.matches_head(
                    repo,
                    attestation,
                    "full-suite",
                )
            )

            (repo / "page.html").write_text("drift", encoding="utf-8")
            self.assertFalse(
                verified_tree.matches_head(
                    repo,
                    attestation,
                    "full-suite",
                )
            )
            (repo / "page.html").write_text("v2", encoding="utf-8")
            attestation.write_text("{}", encoding="utf-8")
            self.assertFalse(
                verified_tree.matches_head(
                    repo,
                    attestation,
                    "full-suite",
                )
            )

    def test_seal_rejects_test_side_effects(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            root = Path(directory)
            repo = self.repository(root)
            attestation = root / "verified.json"
            verified_tree.prepare(repo, attestation, "full-suite")
            (repo / "page.html").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "changed the candidate tree",
            ):
                verified_tree.seal(repo, attestation, "full-suite")

    def test_attestation_cannot_be_written_into_tested_tree(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            repo = self.repository(Path(directory))
            with self.assertRaisesRegex(
                ValueError,
                "must be outside the repo",
            ):
                verified_tree.prepare(
                    repo,
                    repo / "verified.json",
                    "full-suite",
                )


class ParallelSuiteTests(unittest.TestCase):
    def test_partition_runs_every_test_once_and_isolates_heavy_gates(self):
        heavy = ("suite.heavy_one", "suite.heavy_two")
        tests = [
            "suite.fast_a",
            heavy[0],
            "suite.fast_b",
            heavy[1],
            "suite.fast_c",
        ]
        lanes = parallel_unittest.partition_tests(
            tests,
            3,
            heavy,
        )
        flattened = [test for lane in lanes for test in lane.tests]
        self.assertEqual(set(tests), set(flattened))
        self.assertEqual(len(tests), len(flattened))
        self.assertEqual((heavy[0],), lanes[0].tests)
        self.assertEqual((heavy[1],), lanes[1].tests)

    def test_partition_fails_closed_when_a_heavy_gate_disappears(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "Required heavy gate was not discovered",
        ):
            parallel_unittest.partition_tests(
                ["suite.fast"],
                2,
                ("suite.missing",),
            )

    def test_discovery_rejects_duplicate_test_ids(self):
        duplicate = unittest.FunctionTestCase(lambda: None)
        suite = unittest.TestSuite((duplicate, duplicate))
        with (
            mock.patch.object(
                unittest.defaultTestLoader,
                "discover",
                return_value=suite,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "no tests or duplicates",
            ),
        ):
            parallel_unittest.discover_tests(GEO / "tests")

    def test_parallel_matches_serial_ids_and_failure_propagation(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as directory:
            fixture = Path(directory)
            for module in (
                "test_parallel_fixture_alpha",
                "test_parallel_fixture_beta",
            ):
                self.addCleanup(sys.modules.pop, module, None)
            (fixture / "test_parallel_fixture_alpha.py").write_text(
                "import unittest\n\n"
                "class AlphaTests(unittest.TestCase):\n"
                "    def test_alpha(self):\n"
                "        pass\n\n"
                "    def test_failure(self):\n"
                "        self.fail('fixture failure')\n",
                encoding="utf-8",
            )
            (fixture / "test_parallel_fixture_beta.py").write_text(
                "import unittest\n\n"
                "class BetaTests(unittest.TestCase):\n"
                "    def test_beta(self):\n"
                "        pass\n",
                encoding="utf-8",
            )
            serial_suite = unittest.defaultTestLoader.discover(
                str(fixture),
                pattern="test_*.py",
                top_level_dir=str(fixture),
            )
            serial_ids = sorted(parallel_unittest._test_ids(serial_suite))
            parallel_ids = parallel_unittest.discover_tests(fixture)
            self.assertEqual(serial_ids, parallel_ids)
            self.assertEqual(3, len(parallel_ids))

            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(fixture)
            serial = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(fixture),
                    "-p",
                    "test_*.py",
                    "-q",
                    "-b",
                ],
                cwd=GEO.parents[1],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            heavy = (parallel_ids[0], parallel_ids[-1])
            fixture_lanes = parallel_unittest.partition_tests(
                parallel_ids,
                3,
                heavy,
            )
            with (
                mock.patch.object(
                    parallel_unittest,
                    "partition_tests",
                    return_value=fixture_lanes,
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                parallel_rc = parallel_unittest.run_all(
                    parallel_ids,
                    3,
                    start_dir=fixture,
                )
            self.assertEqual(1, serial.returncode)
            self.assertEqual(serial.returncode, parallel_rc)


if __name__ == "__main__":
    unittest.main()
