#!/usr/bin/env python3
"""publish.py 提交前必須把 data/ 鏡像到 Guide _engine/data，並用部署閘門同一條檢查。

2026-10-30 Guide 87626c42e：目錄 API 用 00_GrowthEngine data/ 重產，_engine/data
卻停在舊版，pages.yml 報 Stale catalog localization source: ar-SA/cyca。
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "geo"))

import publish  # noqa: E402


class MirrorCatalogSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.data = root / "data"
        self.pages = root / "pages"
        self.target = self.pages / "_engine" / "data"
        self.data.mkdir()
        self.target.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_updates_stale_tracked_mirror_byte_for_byte(self):
        (self.data / "cyca_full.json").write_bytes(b'{"ar-SA": {"description": "new"}}\n')
        (self.target / "cyca_full.json").write_bytes(b'{"ar-SA": {"description": "old"}}\n')
        changed = publish.mirror_catalog_sources(str(self.pages), str(self.data))
        self.assertEqual(changed, ["cyca_full.json"])
        self.assertEqual(
            (self.target / "cyca_full.json").read_bytes(),
            (self.data / "cyca_full.json").read_bytes(),
        )

    def test_identical_mirror_is_untouched(self):
        for folder in (self.data, self.target):
            (folder / "scanto_full.json").write_bytes(b"{}\n")
        self.assertEqual(
            publish.mirror_catalog_sources(str(self.pages), str(self.data)), []
        )

    def test_does_not_add_untracked_apps_or_delete_mirror_only_files(self):
        (self.data / "brandnew_full.json").write_bytes(b"{}\n")
        (self.target / "legacy_full.json").write_bytes(b"{}\n")
        self.assertEqual(
            publish.mirror_catalog_sources(str(self.pages), str(self.data)), []
        )
        self.assertFalse((self.target / "brandnew_full.json").exists())
        self.assertTrue((self.target / "legacy_full.json").exists())

    def test_reconcile_runs_guide_gate_after_mirror(self):
        engine_geo = self.pages / "_engine" / "geo"
        engine_geo.mkdir(parents=True)
        (engine_geo / "owned_app_feeds.py").write_text("", encoding="utf-8")
        calls = []
        with mock.patch.object(publish, "PAGES", str(self.pages)), \
                mock.patch.object(publish, "mirror_catalog_sources", return_value=[]), \
                mock.patch.object(publish, "require", side_effect=lambda cmd, **_: calls.append(cmd)):
            publish.reconcile_owned_feeds({})
        self.assertEqual(calls[-1], publish.guide_owned_feeds_check_command(str(self.pages)))
        self.assertIn("--check", calls[-1])
        self.assertTrue(calls[-1][1].endswith("_engine/geo/owned_app_feeds.py"))

    def test_gate_failure_aborts_before_commit(self):
        engine_geo = self.pages / "_engine" / "geo"
        engine_geo.mkdir(parents=True)
        (engine_geo / "owned_app_feeds.py").write_text("", encoding="utf-8")

        def fake_require(cmd, **_):
            if "_engine" in cmd[1]:
                raise RuntimeError("Stale catalog localization source: ar-SA/cyca")

        with mock.patch.object(publish, "PAGES", str(self.pages)), \
                mock.patch.object(publish, "mirror_catalog_sources", return_value=[]), \
                mock.patch.object(publish, "require", side_effect=fake_require):
            with self.assertRaises(RuntimeError):
                publish.reconcile_owned_feeds({})


if __name__ == "__main__":
    unittest.main()
