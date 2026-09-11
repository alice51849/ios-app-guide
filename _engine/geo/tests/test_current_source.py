from copy import deepcopy
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "geo"), str(ROOT / "social")]
import appstore_live
import current_source
import live_app_guard
import live_app_manifest as manifest
import sync_current_source
from videogen.registry import APPS, APPSTORE


class CurrentSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = current_source.load_source()
        self.now = datetime.now(timezone.utc)
        self.document = manifest.create_manifest(self.source["apps"], now=self.now)

    def test_exact_47_ids_50_locales_2350_pairs_match_same_run_apple_evidence(self):
        evidence = json.loads(
            (Path(__file__).parent / "fixtures/live47_observation_20260911.json").read_text()
        )
        ids = set(APPSTORE.values())
        self.assertEqual((47, 50, 2350), (
            self.source["app_count"], self.source["locale_count"], self.source["pair_count"],
        ))
        self.assertEqual(self.source["source_sha256"], evidence["source_sha256"])
        self.assertEqual(
            hashlib.sha256(current_source.MANIFEST_PATH.read_bytes()).hexdigest(),
            self.source["source_sha256"],
        )
        self.assertEqual(set(self.source["apps"]), set(APPS))
        self.assertEqual(current_source.appstore_ids(), APPSTORE)
        pairs = current_source.campaign_pairs()
        self.assertEqual(2350, len(pairs))
        self.assertEqual(2350, len(set(pairs)))
        for country, lookup in evidence["lookups"].items():
            with self.subTest(country=country):
                self.assertEqual("GET", lookup["method"])
                self.assertEqual(ids, set(lookup["app_ids"]))
                self.assertEqual([], lookup["removed_ids_present"])
        self.assertIsNotNone(manifest.timestamp(evidence["observed_at"]).tzinfo)
        self.assertTrue({"zipbox", "battai"} <= set(APPS))
        self.assertFalse({"zodira", "zafe"} & set(APPS))
        for key in ("zipbox", "battai"):
            self.assertEqual(50, sum(app == key for app, _ in pairs))

    def test_every_copy_is_derived_from_the_same_current_source(self):
        with tempfile.TemporaryDirectory() as directory:
            for layout in ("guide", "social", "owned"):
                target = Path(directory) / layout
                result = sync_current_source.synchronize(target, layout=layout)
                self.assertEqual(self.source["source_sha256"], result["source_sha256"])
                sync_current_source.synchronize(target, layout=layout, check=True)
                prefix = {"guide": "_engine/geo", "social": ".", "owned": "geo"}[layout]
                (target / prefix / "live_app_manifest.json").write_text("{}")
                with self.assertRaisesRegex(ValueError, "mirror drift"):
                    sync_current_source.synchronize(target, layout=layout, check=True)

    def test_missing_duplicate_resealed_or_legacy_source_is_not_a_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            with self.assertRaisesRegex(current_source.SourceError, "unavailable"):
                current_source.load_source(path)
            source = json.loads(current_source.MANIFEST_PATH.read_text())
            source["apps"].pop("zipbox")
            source["roster_digest"] = current_source._digest(source["apps"])
            path.write_text(json.dumps(source))
            with self.assertRaisesRegex(current_source.SourceError, "exactly 47"):
                current_source.load_source(path)
            path.write_text('{"schema": 1, "schema": 2}')
            with self.assertRaisesRegex(current_source.SourceError, "Duplicate"):
                current_source.load_source(path)
        for key in ("battai", "zipbox"):
            ids = dict(APPSTORE)
            ids.pop(key)
            with self.assertRaisesRegex(current_source.SourceError, "identity drift"):
                current_source.validate_consumer(ids)
        replaced = dict(APPSTORE, zipbox="6783609555")
        with self.assertRaisesRegex(current_source.SourceError, "identity drift"):
            current_source.validate_consumer(replaced)

    def test_observation_binds_source_sha_same_run_time_and_pair_denominator(self):
        for field, value in (
            ("source_sha256", "f" * 64),
            ("locale_roster_sha256", "f" * 64),
            ("observed_at", (self.now - timedelta(seconds=1)).isoformat()),
            ("observed_at", None),
            ("locale_count", 49),
            ("pair_count", 2300),
        ):
            with self.subTest(field=field):
                changed = deepcopy(self.document)
                changed[field] = value
                with self.assertRaises(manifest.ManifestError):
                    manifest.require_public_inventory(changed, now=self.now)
        accepted = manifest.require_public_inventory(self.document, now=self.now)
        self.assertEqual(self.now.isoformat(), accepted["observed_at"])
        self.assertEqual(self.source["source_sha256"], accepted["source_sha256"])

    def test_stale_missing_and_partial_observations_fail_before_any_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = Path(directory)
            snapshot = pages / "observation.json"
            old_state = pages / appstore_live.STATE_FILE
            old_state.write_text(json.dumps({"live_ids": list(APPSTORE.values())[:-2]}))
            before = old_state.read_bytes()
            stale = manifest.create_manifest(
                self.source["apps"], now=self.now - timedelta(days=2),
            )
            partial = deepcopy(self.document)
            partial["observations"]["battai"].update(
                status="unknown", checked_at=None, reason="Apple lookup is incomplete",
            )
            with (
                mock.patch.dict(os.environ, {"GROWTH_LIVE_MANIFEST": str(snapshot)}),
                mock.patch.object(manifest, "refresh_manifest", side_effect=AssertionError("No fallback GET")),
            ):
                for document in (None, stale, partial):
                    if document is not None:
                        snapshot.write_text(json.dumps(document))
                    for consume in (
                        lambda: appstore_live.live_app_keys(APPSTORE, pages, refresh=False),
                        lambda: appstore_live.live_app_keys(APPSTORE, pages, refresh=True),
                        live_app_guard.live_apps,
                    ):
                        with self.subTest(document=document is None, consumer=consume):
                            with self.assertRaises(manifest.ManifestError):
                                consume()
                    self.assertEqual(before, old_state.read_bytes())
                snapshot.write_text(json.dumps(self.document))
                self.assertEqual(
                    set(APPSTORE), appstore_live.live_app_keys(APPSTORE, pages, refresh=False),
                )
                self.assertEqual(APPSTORE, live_app_guard.live_apps())

    def test_legacy_state_and_unusable_lookup_never_replace_current_identity(self):
        source_before = current_source.MANIFEST_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / appstore_live.STATE_FILE
            path.write_text(json.dumps({"live_ids": list(APPSTORE.values()), "miss_counts": {}}))
            before = path.read_bytes()
            with mock.patch.dict(os.environ, {"GROWTH_LIVE_MANIFEST": ""}):
                with self.assertRaisesRegex(RuntimeError, "legacy snapshot"):
                    appstore_live.live_app_keys(APPSTORE, directory, refresh=False)
                partial = deepcopy(self.document)
                partial["observations"]["zipbox"].update(status="unknown", reason="Not observed")
                with mock.patch.object(manifest, "refresh_manifest", return_value=partial):
                    with self.assertRaisesRegex(manifest.ManifestError, "denominator drift"):
                        appstore_live.live_app_keys(APPSTORE, directory)
                self.assertEqual(before, path.read_bytes())
        self.assertEqual(source_before, current_source.MANIFEST_PATH.read_bytes())

    def test_migrated_state_is_exact_source_bound_and_expires(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / appstore_live.STATE_FILE
            manifest.write_legacy_live_state(path, self.document)
            state = appstore_live._read_state(path, now=self.now)
            self.assertEqual(set(APPSTORE.values()), state["live_ids"])
            self.assertEqual(self.document["observed_at"], state["observed_at"])
            self.assertEqual(self.document["source_sha256"], state["source_sha256"])
            with self.assertRaisesRegex(RuntimeError, "stale"):
                appstore_live._read_state(path, now=self.now + timedelta(days=1))
            data = json.loads(path.read_text())
            data["source_sha256"] = "f" * 64
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError, "identity drift"):
                appstore_live._read_state(path, now=self.now)

    def test_refresh_discards_history_bound_to_a_different_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.json"
            for field in ("source_sha256", "locale_roster_sha256"):
                previous = deepcopy(self.document)
                previous[field] = "f" * 64
                previous["observations"]["battai"].update(
                    status="unknown", reason="Prior misses", consecutive_misses=2,
                    last_verified_at=previous["observed_at"],
                )
                path.write_text(json.dumps(previous))
                before = path.read_bytes()
                with redirect_stderr(io.StringIO()):
                    refreshed = manifest.refresh_manifest(
                        now=self.now, previous_path=path,
                        lookup_country=lambda ids, country: set(ids) - {APPSTORE["battai"]},
                    )
                row = refreshed["observations"]["battai"]
                self.assertEqual(1, row["consecutive_misses"])
                self.assertIsNone(row["last_verified_at"])
                self.assertEqual(before, path.read_bytes())
                with self.assertRaisesRegex(manifest.ManifestError, "denominator drift"):
                    manifest.require_public_inventory(refreshed, now=self.now)

    def test_every_snapshot_writer_protects_canonical_source_and_symlink_aliases(self):
        original = manifest.DEFAULT_ROSTER.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "source-link.json"
            alias.symlink_to(manifest.DEFAULT_ROSTER)
            for target in (manifest.DEFAULT_ROSTER, alias):
                with mock.patch.object(manifest.os, "replace", side_effect=AssertionError("No source mutation")):
                    for write in (
                        lambda: manifest.write_manifest(target, self.document),
                        lambda: manifest.write_legacy_live_state(target, self.document),
                        lambda: appstore_live._write_state(
                            target, set(APPSTORE.values()), {},
                            observed_at=self.document["observed_at"],
                            source_sha256=self.document["source_sha256"],
                        ),
                    ):
                        with self.assertRaisesRegex(manifest.ManifestError, "cannot overwrite"):
                            write()
                with (
                    mock.patch.object(manifest, "refresh_manifest", side_effect=AssertionError("No GET")),
                    redirect_stderr(io.StringIO()),
                ):
                    self.assertEqual(1, manifest.main([
                        "--refresh", "--output", str(Path(directory) / "observation.json"),
                        "--live-state-output", str(target),
                    ]))
            self.assertEqual(original, manifest.DEFAULT_ROSTER.read_bytes())

    def test_reviewed_app_id_replacement_can_refresh_without_old_cache_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            roster = json.loads(manifest.DEFAULT_ROSTER.read_text())
            roster["apps"]["battai"]["app_id"] = "9999999999"
            roster["revision"] += 1
            roster["roster_digest"] = manifest.roster_digest(roster["apps"])
            source_path = Path(directory) / "source.json"
            source_path.write_text(json.dumps(roster))
            previous_path = Path(directory) / "previous.json"
            previous_path.write_text(json.dumps(self.document))
            appstore = {**APPSTORE, "battai": "9999999999"}
            lookup = mock.Mock(return_value=set(appstore.values()))
            with (
                mock.patch.object(manifest, "DEFAULT_ROSTER", source_path),
                redirect_stderr(io.StringIO()),
            ):
                refreshed = manifest.refresh_manifest(
                    appstore, APPS, now=self.now, previous_path=previous_path,
                    lookup_country=lookup,
                )
                manifest.require_public_inventory(refreshed, now=self.now)
            self.assertEqual(4, lookup.call_count)
            self.assertEqual("9999999999", refreshed["apps"]["battai"]["app_id"])
            self.assertEqual(47, len(refreshed["apps"]))


if __name__ == "__main__":
    unittest.main()
