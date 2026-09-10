#!/usr/bin/env python3
"""Focused tests for the canonical topic-hub publication contract."""
from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest import mock
import uuid


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
sys.path.insert(0, str(GEO))

import check_hub_coverage as coverage  # noqa: E402
import gen_hubs  # noqa: E402


class CanonicalAuthorityTests(unittest.TestCase):
    def test_authority_is_the_47_app_manifest_and_includes_zipbox(self):
        apps = gen_hubs.authority_apps()
        self.assertEqual(47, len(apps))
        self.assertEqual("6806776579", apps["zipbox"]["app_id"])
        self.assertEqual(
            len(apps) * (len(gen_hubs.official_locales()) + 1) + 1,
            2398,
        )

    def test_main_never_uses_generated_site_inventory_as_its_denominator(self):
        source = inspect.getsource(gen_hubs.main)
        self.assertIn("authority_apps()", source)
        self.assertNotIn("live_app_keys", source)
        self.assertNotIn("apps.json", source)

    def test_registry_drift_fails_closed(self):
        with mock.patch.dict(
            gen_hubs.APPSTORE,
            {"zipbox": "0000000000"},
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "registry disagree"):
                gen_hubs.authority_apps()

    def test_missing_zipbox_or_locale_fails_closed(self):
        apps = dict(gen_hubs.canonical_manifest()["apps"])
        apps.pop("zipbox")
        with mock.patch.object(
            gen_hubs,
            "canonical_manifest",
            return_value={"apps": apps},
        ):
            with self.assertRaisesRegex(ValueError, "Zipbox"):
                gen_hubs.authority_apps()
        with mock.patch.object(
            gen_hubs,
            "OFFICIAL_LOCALES",
            gen_hubs.OFFICIAL_LOCALES[:-1],
        ):
            with self.assertRaisesRegex(ValueError, "exact official locale"):
                gen_hubs.official_locales()

    def test_source_date_epoch_is_the_deterministic_date_authority(self):
        with mock.patch.dict(
            os.environ,
            {"SOURCE_DATE_EPOCH": "0", "GEO_BUILD_DATE": "2099-12-31"},
            clear=False,
        ):
            self.assertEqual("1970-01-01", gen_hubs._bound_build_date())

    def test_atomic_write_failure_preserves_last_good_bytes(self):
        directory = (
            HERE
            / ".topic-hub-atomic-artifacts"
            / uuid.uuid4().hex
        )
        directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, directory.parent, True)
        target = directory / "hub.html"
        target.write_bytes(b"last-good")
        with mock.patch.object(
            gen_hubs.os,
            "replace",
            side_effect=OSError("simulated replacement failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated"):
                gen_hubs._atomic_write_text(target, "new")
        self.assertEqual(b"last-good", target.read_bytes())
        self.assertEqual([], list(directory.glob(".hub.html.*.tmp")))


class FullHubCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = (
            HERE
            / ".topic-hub-contract-artifacts"
            / uuid.uuid4().hex
        )
        cls.workspace.mkdir(parents=True)
        cls.addClassCleanup(shutil.rmtree, cls.workspace.parent, True)
        cls.old_pages = gen_hubs.PAGES
        cls.old_hubs = gen_hubs.HUBS
        cls.old_provider = os.environ.get(gen_hubs.PROVIDER_TOKEN_ENV)
        cls.old_build_date = os.environ.get("GEO_BUILD_DATE")
        cls.old_epoch = os.environ.pop("SOURCE_DATE_EPOCH", None)
        cls.addClassCleanup(cls._restore_globals)
        gen_hubs.PAGES = str(cls.workspace)
        gen_hubs.HUBS = str(cls.workspace / "hubs")
        os.environ[gen_hubs.PROVIDER_TOKEN_ENV] = "118326163"
        os.environ["GEO_BUILD_DATE"] = "2026-09-10"
        cls.fast_patches = (
            mock.patch.object(
                gen_hubs.rank_opportunity_pages,
                "searched_as_block",
                return_value="",
            ),
            mock.patch.object(
                gen_hubs.rank_opportunity_pages,
                "phrases_for",
                return_value=[],
            ),
            mock.patch.object(
                gen_hubs,
                "localized_answer_links",
                return_value=[],
            ),
            mock.patch.object(
                gen_hubs,
                "_owned_answer_link",
                return_value=None,
            ),
        )
        for patcher in cls.fast_patches:
            patcher.start()
            cls.addClassCleanup(patcher.stop)
        cls.apps = gen_hubs.authority_apps()
        cls.locales = gen_hubs.official_locales()
        cls._write_source_fixture()
        gen_hubs.main()

    @classmethod
    def _restore_globals(cls):
        gen_hubs.PAGES = cls.old_pages
        gen_hubs.HUBS = cls.old_hubs
        if cls.old_provider is None:
            os.environ.pop(gen_hubs.PROVIDER_TOKEN_ENV, None)
        else:
            os.environ[gen_hubs.PROVIDER_TOKEN_ENV] = cls.old_provider
        if cls.old_build_date is None:
            os.environ.pop("GEO_BUILD_DATE", None)
        else:
            os.environ["GEO_BUILD_DATE"] = cls.old_build_date
        if cls.old_epoch is None:
            os.environ.pop("SOURCE_DATE_EPOCH", None)
        else:
            os.environ["SOURCE_DATE_EPOCH"] = cls.old_epoch

    @classmethod
    def _write_source_fixture(cls):
        for locale in cls.locales:
            directory = cls.workspace / locale
            directory.mkdir()
            for key, app in cls.apps.items():
                if locale == "en-US":
                    description = (
                        f"Verified English product guide for {app['name']} "
                        "with features and App Store access."
                    )
                else:
                    description = (
                        f"{locale} localized product guide for {app['name']} "
                        "with reviewed native ownership."
                    )
                (directory / f"{key}.html").write_text(
                    (
                        f'<!DOCTYPE html><html lang="{locale}"><head>'
                        f'<meta name="description" content="{description}">'
                        f'<link rel="canonical" '
                        f'href="{gen_hubs.SITE}/{locale}/{key}.html">'
                        f"</head><body><h1>{app['name']}</h1></body></html>"
                    ),
                    encoding="utf-8",
                )

    @classmethod
    def _managed_paths(cls):
        paths = [
            cls.workspace / "hubs" / f"{key}.html"
            for key in cls.apps
        ]
        paths.extend(
            cls.workspace / locale / "hubs" / f"{key}.html"
            for locale in cls.locales
            for key in cls.apps
        )
        paths.extend(
            (
                cls.workspace / "hubs" / "index.html",
                cls.workspace / "sitemap_hubs.xml",
            )
        )
        return paths

    @classmethod
    def _snapshot(cls):
        digest = hashlib.sha256()
        for path in cls._managed_paths():
            digest.update(path.relative_to(cls.workspace).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _restamp(source):
        match = gen_hubs.SOURCE_DIGEST_RE.search(source)
        if match is None:
            raise AssertionError("fixture hub has no digest")
        raw = source[:match.start()] + source[match.end():]
        return gen_hubs._stamp_source_digest(raw)

    def test_exact_collection_determinism_lastmod_pruning_and_quality_gates(self):
        result = coverage.audit(self.workspace)
        self.assertEqual(
            {
                "apps": 47,
                "locales": 50,
                "root_hubs": 47,
                "localized_hubs": 2350,
                "index_pages": 1,
                "sitemap_urls": 2398,
                "provider_token": "118326163",
            },
            result,
        )
        self.assertTrue((self.workspace / "hubs" / "zipbox.html").is_file())
        self.assertTrue(
            all(
                (self.workspace / locale / "hubs" / "zipbox.html").is_file()
                for locale in self.locales
            )
        )

        initial = self._snapshot()
        selected = self.workspace / "fr-FR" / "hubs" / "zipbox.html"
        initial_mtime = selected.stat().st_mtime_ns
        os.environ["GEO_BUILD_DATE"] = "2026-09-11"
        gen_hubs.main()
        self.assertEqual(initial, self._snapshot())
        self.assertEqual(initial_mtime, selected.stat().st_mtime_ns)

        before_lastmods = dict(
            coverage._sitemap_rows(self.workspace / "sitemap_hubs.xml")
        )
        source_path = self.workspace / "fr-FR" / "zipbox.html"
        original_source = source_path.read_text(encoding="utf-8")
        source_path.write_text(
            original_source.replace(
                "fr-FR localized product guide",
                "fr-FR revised localized product guide",
            ),
            encoding="utf-8",
        )
        os.environ["GEO_BUILD_DATE"] = "2026-09-12"
        gen_hubs.main()
        after_lastmods = dict(
            coverage._sitemap_rows(self.workspace / "sitemap_hubs.xml")
        )
        changed = {
            url
            for url in before_lastmods
            if before_lastmods[url] != after_lastmods[url]
        }
        self.assertEqual(
            {gen_hubs.hub_url("zipbox", "fr-FR")},
            changed,
        )
        self.assertEqual(
            "2026-09-12",
            after_lastmods[gen_hubs.hub_url("zipbox", "fr-FR")],
        )

        source_path.write_text(original_source, encoding="utf-8")
        os.environ["GEO_BUILD_DATE"] = "2026-09-13"
        gen_hubs.main()
        restored = self._snapshot()
        os.environ["GEO_BUILD_DATE"] = "2026-09-14"
        gen_hubs.main()
        self.assertEqual(restored, self._snapshot())

        stale_root = self.workspace / "hubs" / "retired-app.html"
        stale_locale = self.workspace / "fr-FR" / "hubs" / "retired-app.html"
        stale_supplemental = self.workspace / "bg" / "hubs" / "retired-app.html"
        stale_supplemental.parent.mkdir(parents=True)
        stale_root.write_text("stale", encoding="utf-8")
        stale_locale.write_text("stale", encoding="utf-8")
        stale_supplemental.write_text("stale", encoding="utf-8")
        gen_hubs.main()
        self.assertFalse(stale_root.exists())
        self.assertFalse(stale_locale.exists())
        self.assertFalse(stale_supplemental.exists())
        coverage.audit(self.workspace)

        missing_source = self.workspace / "ja" / "zipbox.html"
        held_source = missing_source.with_suffix(".held")
        os.replace(missing_source, held_source)
        before_failure = self._snapshot()
        try:
            with self.assertRaisesRegex(ValueError, "Missing localized hub source"):
                gen_hubs.main()
            self.assertEqual(before_failure, self._snapshot())
        finally:
            os.replace(held_source, missing_source)

        target = self.workspace / "fr-FR" / "hubs" / "zipbox.html"
        original = target.read_bytes()
        try:
            text = original.decode("utf-8")
            broken = text.replace(
                gen_hubs.hub_url("zipbox", "de-DE"),
                gen_hubs.hub_url("zipbox", "fr-FR"),
                1,
            )
            target.write_text(self._restamp(broken), encoding="utf-8")
            with self.assertRaisesRegex(
                coverage.HubContractError,
                "hreflang",
            ):
                coverage._validate_hub(
                    self.workspace,
                    "zipbox",
                    self.apps["zipbox"],
                    self.locales,
                    locale="fr-FR",
                )
        finally:
            target.write_bytes(original)

        try:
            text = original.decode("utf-8")
            broken = text.replace("?pt=", "?missing_pt=", 1)
            target.write_text(self._restamp(broken), encoding="utf-8")
            with self.assertRaisesRegex(
                coverage.HubContractError,
                "attribution",
            ):
                coverage._validate_hub(
                    self.workspace,
                    "zipbox",
                    self.apps["zipbox"],
                    self.locales,
                    locale="fr-FR",
                )
        finally:
            target.write_bytes(original)

        try:
            text = original.decode("utf-8")
            english = (
                self.workspace
                / "en-US"
                / "hubs"
                / "zipbox.html"
            ).read_text(encoding="utf-8")
            localized_description = re.search(
                r'<meta name="description" content="([^"]+)">',
                text,
            ).group(1)
            english_description = re.search(
                r'<meta name="description" content="([^"]+)">',
                english,
            ).group(1)
            broken = text.replace(
                localized_description,
                english_description,
                1,
            )
            target.write_text(self._restamp(broken), encoding="utf-8")
            with self.assertRaisesRegex(
                coverage.HubContractError,
                "English fallback",
            ):
                coverage.audit(self.workspace)
        finally:
            target.write_bytes(original)
        coverage.audit(self.workspace)


if __name__ == "__main__":
    unittest.main()
