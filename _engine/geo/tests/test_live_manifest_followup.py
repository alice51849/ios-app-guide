from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT, ROOT / "geo", ROOT / "social"):
    sys.path.insert(0, str(directory))
import live_app_manifest as manifest
import outreach_scorecard
import publish
import new_app_catchup
from videogen.registry import APPS, APPSTORE


class AvailabilityFollowupTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.roster = manifest.canonical_manifest()
        self.app_count = len(self.roster["apps"])
        self.roster_path = self.root / "roster.json"
        self.roster_path.write_text(json.dumps(self.roster), encoding="utf-8")
        self.runtime = self.root / "private" / "live.json"
        self.stack.enter_context(mock.patch.object(manifest, "DEFAULT_ROSTER", self.roster_path))
        self.stack.enter_context(mock.patch.dict(os.environ, {"GROWTH_LIVE_MANIFEST": str(self.runtime)}))
        self.now = datetime(2026, 9, 5, 6, tzinfo=timezone.utc)
        clock = self.stack.enter_context(mock.patch.object(manifest, "datetime", wraps=datetime))
        clock.now.return_value = self.now
        self.ids = {app["app_id"] for app in self.roster["apps"].values()}
        self.original = self.roster_path.read_bytes()

    def seed(self):
        previous = manifest.create_manifest(self.roster["apps"], now=self.now - timedelta(hours=1))
        manifest.write_manifest(self.runtime, previous, private=True)
        return previous

    def refresh(self, lookup, *, adopt=False, appstore=APPSTORE, registry=APPS):
        return manifest.refresh_manifest(
            appstore, registry, now=self.now, lookup_country=lookup,
            previous_path=self.runtime, adopt=adopt,
        )

    def rename_identity(self, key="battai"):
        roster = deepcopy(self.roster)
        roster["apps"][key] = {**roster["apps"].pop("battai"), "name": "BattAI Updated"}
        roster["revision"] += 1
        roster["roster_digest"] = manifest.roster_digest(roster["apps"])
        self.roster_path.write_text(json.dumps(roster), encoding="utf-8")
        appstore = dict(APPSTORE)
        appstore[key] = appstore.pop("battai")
        registry = deepcopy(APPS)
        registry[key] = {**registry.pop("battai"), "name": "BattAI Updated"}
        return appstore, registry

    def test_consistent_identity_update_discards_cache_and_rebuilds(self):
        previous = self.seed()
        previous["observations"]["battai"].update(
            status="unknown", reason="Two clean misses", consecutive_misses=2,
            last_verified_at=previous["generated_at"],
        )
        previous = manifest.create_manifest(
            previous["apps"], now=self.now - timedelta(hours=1),
            observations=previous["observations"],
        )
        for key in ("battai", "battaiupdated"):
            appstore, registry = self.rename_identity(key)
            roster_bytes = self.roster_path.read_bytes()
            for outcome in ("live", "missing", "outage"):
                with self.subTest(key=key, outcome=outcome):
                    self.runtime.write_text(json.dumps(previous), encoding="utf-8")
                    cache_bytes = self.runtime.read_bytes()
                    with self.assertRaisesRegex(manifest.ManifestError, "roster drift"):
                        manifest.load_manifest(self.runtime, now=self.now)
                    lookup = mock.Mock(
                        return_value=self.ids if outcome == "live" else self.ids - {APPSTORE["battai"]},
                        side_effect=TimeoutError("Lookup unavailable") if outcome == "outage" else None,
                    )
                    errors = io.StringIO()
                    with redirect_stderr(errors):
                        result = self.refresh(lookup, appstore=appstore, registry=registry)
                    self.assertEqual(len(manifest.LOOKUP_COUNTRIES), lookup.call_count)
                    self.assertRegex(errors.getvalue(), "Availability advisory:.*stale.*identity")
                    self.assertEqual(manifest.canonical_manifest()["apps"], result["apps"])
                    row = result["observations"][key]
                    self.assertEqual("live" if outcome == "live" else "unknown", row["status"])
                    self.assertEqual(1 if outcome == "missing" else 0, row["consecutive_misses"])
                    self.assertEqual(self.now.isoformat() if outcome == "live" else None, row["last_verified_at"])
                    self.assertEqual(cache_bytes, self.runtime.read_bytes())
                    self.assertEqual(roster_bytes, self.roster_path.read_bytes())
                    manifest.write_manifest(self.runtime, result, private=True)
                    self.assertEqual(result, manifest.load_manifest(self.runtime, now=self.now))

    def test_refresh_cli_rebuilds_identity_cache_with_advisory(self):
        self.seed()
        appstore, registry = self.rename_identity()
        errors = io.StringIO()
        with (
            mock.patch.object(manifest, "_registry", return_value=(appstore, registry)),
            mock.patch.object(manifest, "_lookup_results", return_value={
                country: self.ids for country in manifest.LOOKUP_COUNTRIES
            }),
            redirect_stdout(io.StringIO()), redirect_stderr(errors),
        ):
            self.assertEqual(0, manifest.main(["--refresh", "--output", str(self.runtime)]))
        self.assertRegex(errors.getvalue(), "Availability advisory:.*stale.*identity")
        rebuilt = manifest.load_manifest(self.runtime, now=self.now)
        self.assertEqual("BattAI Updated", rebuilt["apps"]["battai"]["name"])
        self.assertEqual("live", rebuilt["observations"]["battai"]["status"])

    def test_roster_identity_never_expires_and_missing_snapshot_is_unknown(self):
        future = self.now + timedelta(days=365)
        self.assertEqual(manifest.ROSTER_SCHEMA, self.roster["schema"])
        self.assertNotIn("ttl_seconds", self.roster)
        self.assertNotIn("generated_at", self.roster)
        document = manifest.load_manifest(now=future, require_fresh=False)
        states = manifest.app_statuses(document, now=future)
        self.assertEqual(set(self.roster["apps"]), set(states))
        self.assertEqual({"unknown"}, {row["inventory_status"] for row in states.values()})
        self.assertTrue(all(row["public_eligible"] for row in states.values()))
        self.assertEqual(self.original, self.roster_path.read_bytes())
        self.assertFalse(self.runtime.exists())

    def test_one_failed_storefront_does_not_abort_refresh_or_erase_other_evidence(self):
        previous = self.seed()

        def lookup(ids, country):
            if country == "tw":
                raise TimeoutError("temporary lookup failure")
            return self.ids - {APPSTORE["battai"]}

        document = self.refresh(lookup)
        battai = document["observations"]["battai"]
        self.assertEqual("unknown", battai["status"])
        self.assertEqual(0, battai["consecutive_misses"])
        self.assertEqual(previous["observations"]["battai"]["checked_at"], battai["last_verified_at"])
        self.assertEqual("live", document["observations"]["snapport"]["status"])
        self.assertEqual(self.original, self.roster_path.read_bytes())
        with (
            mock.patch.object(manifest, "_lookup_results", return_value={country: None for country in manifest.LOOKUP_COUNTRIES}),
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(0, manifest.main(["--refresh", "--output", str(self.runtime)]))
        self.assertEqual(self.roster["apps"], json.loads(self.runtime.read_text())["apps"])

    def test_three_clean_misses_retire_eligibility_but_never_delete_identity(self):
        self.seed()
        missing = self.ids - {APPSTORE["battai"]}
        for count in (1, 2, 3):
            document = self.refresh(lambda ids, country: missing)
            manifest.write_manifest(self.runtime, document, private=True)
            row = manifest.app_statuses(document, now=self.now)["battai"]
            self.assertEqual(count, row["consecutive_misses"])
            self.assertEqual(count < 3, row["public_eligible"])
            self.assertEqual(self.roster["apps"], document["apps"])
        self.assertEqual("unavailable", row["inventory_status"])
        self.assertEqual(self.original, self.roster_path.read_bytes())

    def test_transient_between_clean_misses_does_not_increment_or_reset_counter(self):
        self.seed()
        missing = self.ids - {APPSTORE["battai"]}
        first = self.refresh(lambda ids, country: missing)
        manifest.write_manifest(self.runtime, first, private=True)

        def transient(ids, country):
            if country == "tw":
                raise OSError("transport unavailable")
            return missing

        second = self.refresh(transient)
        self.assertEqual(1, second["observations"]["battai"]["consecutive_misses"])
        self.assertEqual(first["observations"]["battai"]["last_verified_at"], second["observations"]["battai"]["last_verified_at"])

    def test_implausibly_empty_lookup_cannot_retire_whole_portfolio(self):
        self.seed()
        for _ in range(3):
            document = self.refresh(lambda ids, country: set())
            manifest.write_manifest(self.runtime, document, private=True)
        self.assertTrue(all(row["consecutive_misses"] == 0 for row in document["observations"].values()))
        self.assertTrue(all(row["public_eligible"] for row in manifest.app_statuses(document).values()))

    def test_schema_digest_and_roster_corruption_remain_hard_failures(self):
        valid = self.seed()
        corrupt = deepcopy(valid)
        corrupt["apps"]["battai"]["app_id"] = "9999999999"
        corrupt["roster_digest"] = manifest.roster_digest(corrupt["apps"])
        altered = deepcopy(valid)
        altered["apps"]["battai"]["name"] = "Corrupted without resealing"
        cases = (
            ({"version": 1, "apps": [{}] * 45}, "schema"),
            ({**valid, "roster_digest": "f" * 64}, "roster digest"),
            (altered, "roster digest"),
            ({**valid, "observations": {}}, "exact roster"),
            ({**valid, "generated_at": (self.now + timedelta(seconds=1)).isoformat()}, "future"),
            (corrupt, "Unregistered"),
            ({**valid, "pending_adoptions": [{
                "key": "unregistered", "app_id": "9999999999",
                "name": "Unknown App", "sources": ["us", "tw"],
            }]}, "Unregistered"),
        )
        for identity in ("unchanged", "renamed"):
            appstore, registry = (APPSTORE, APPS) if identity == "unchanged" else self.rename_identity()
            roster_bytes = self.roster_path.read_bytes()
            for invalid, message in cases:
                with self.subTest(identity=identity, error=message):
                    self.runtime.write_text(json.dumps(invalid), encoding="utf-8")
                    cache_bytes = self.runtime.read_bytes()
                    lookup = mock.Mock(return_value=self.ids)
                    errors = io.StringIO()
                    with redirect_stderr(errors), self.assertRaisesRegex(manifest.ManifestError, message):
                        self.refresh(lookup, appstore=appstore, registry=registry)
                    lookup.assert_not_called()
                    self.assertEqual("", errors.getvalue())
                    self.assertEqual(cache_bytes, self.runtime.read_bytes())
                    self.assertEqual(roster_bytes, self.roster_path.read_bytes())

    def test_registry_inconsistency_still_blocks_identity_refresh(self):
        self.seed()
        appstore, registry = self.rename_identity()
        roster_bytes = self.roster_path.read_bytes()
        cache_bytes = self.runtime.read_bytes()
        for invalid_appstore, invalid_registry, message in (
            (appstore, APPS, "Registry roster drift: battai"),
            ({**appstore, "battai": "9999999999"}, registry, "Registry roster drift: battai"),
            ({**appstore, "battai": APPSTORE["savetag"]}, registry, "unique numeric IDs"),
        ):
            with self.subTest(error=message):
                lookup = mock.Mock(return_value=self.ids)
                errors = io.StringIO()
                with redirect_stderr(errors), self.assertRaisesRegex(manifest.ManifestError, message):
                    self.refresh(lookup, appstore=invalid_appstore, registry=invalid_registry)
                lookup.assert_not_called()
                self.assertEqual("", errors.getvalue())
                self.assertEqual(cache_bytes, self.runtime.read_bytes())
                self.assertEqual(roster_bytes, self.roster_path.read_bytes())

    def test_registered_new_app_adopts_atomically_with_two_sources_and_is_idempotent(self):
        self.seed()
        candidate = APPSTORE["zafe"]
        result = self.refresh(
            lambda ids, country: self.ids | ({candidate} if country in ("us", "tw") else set()),
            adopt=True,
        )
        roster = manifest.canonical_manifest()
        expected_apps = {
            **self.roster["apps"],
            "zafe": {"app_id": candidate, "name": APPS["zafe"]["name"]},
        }
        self.assertEqual(expected_apps, roster["apps"])
        self.assertEqual(candidate, roster["apps"]["zafe"]["app_id"])
        self.assertEqual(self.roster["revision"] + 1, roster["revision"])
        self.assertEqual(manifest.roster_digest(roster["apps"]), roster["roster_digest"])
        self.assertEqual(expected_apps, result["apps"])
        self.assertEqual([], result["pending_adoptions"])
        adopted = self.roster_path.read_bytes()
        manifest.write_manifest(self.runtime, result, private=True)
        self.refresh(lambda ids, country: self.ids | {candidate}, adopt=True)
        self.assertEqual(adopted, self.roster_path.read_bytes())

    def test_adopted_roster_keeps_subset_snapshot_history(self):
        previous = self.seed()
        previous["observations"]["battai"].update(
            status="unknown", reason="Two clean misses", consecutive_misses=2,
            last_verified_at=previous["generated_at"],
        )
        previous["pending_adoptions"] = [{
            "key": "zafe", "app_id": APPSTORE["zafe"], "name": APPS["zafe"]["name"],
            "sources": ["us"],
        }]
        manifest.write_manifest(self.runtime, previous, private=True)
        observed = self.ids | {APPSTORE["zafe"]}
        manifest.adopt_registered_live_apps(
            {"us": observed, "tw": observed}, appstore=APPSTORE, registry=APPS,
        )
        adopted = self.roster_path.read_bytes()
        errors = io.StringIO()
        with redirect_stderr(errors):
            result = self.refresh(lambda ids, country: observed - {APPSTORE["battai"]}, adopt=True)
        self.assertEqual("", errors.getvalue())
        self.assertEqual({
            **self.roster["apps"],
            "zafe": {"app_id": APPSTORE["zafe"], "name": APPS["zafe"]["name"]},
        }, result["apps"])
        row = result["observations"]["battai"]
        self.assertEqual("unavailable", row["status"])
        self.assertEqual(3, row["consecutive_misses"])
        self.assertEqual(previous["generated_at"], row["last_verified_at"])
        self.assertEqual("live", result["observations"]["zafe"]["status"])
        self.assertEqual(adopted, self.roster_path.read_bytes())

    def test_one_source_or_aggregate_is_pending_not_automatic_adoption(self):
        candidate = APPSTORE["zafe"]
        result = self.refresh(
            lambda ids, country: self.ids | ({candidate} if country == "us" else set()),
            adopt=True,
        )
        self.assertEqual(self.original, self.roster_path.read_bytes())
        self.assertEqual(["zafe"], [row["key"] for row in result["pending_adoptions"]])
        manifest.adopt_registered_live_apps(
            {"us": self.ids | {candidate}, "aggregate": self.ids | {candidate}},
            appstore=APPSTORE, registry=APPS,
        )
        self.assertEqual(self.original, self.roster_path.read_bytes())

    def test_unknown_or_not_fully_registered_identity_is_never_adopted(self):
        with self.assertRaisesRegex(manifest.ManifestError, "Unregistered"):
            self.refresh(lambda ids, country: self.ids | {"9999999999"}, adopt=True)
        incomplete_registry = {key: app for key, app in APPS.items() if key != "zafe"}
        with self.assertRaisesRegex(manifest.ManifestError, "both APPSTORE and APPS"):
            manifest.adopt_registered_live_apps(
                {"us": self.ids | {APPSTORE["zafe"]}, "tw": self.ids | {APPSTORE["zafe"]}},
                appstore=APPSTORE, registry=incomplete_registry,
            )
        self.assertEqual(self.original, self.roster_path.read_bytes())

    def test_failed_atomic_adoption_does_not_leave_half_updated_roster(self):
        with mock.patch.object(manifest.os, "replace", side_effect=OSError("disk write failed")):
            with self.assertRaises(OSError):
                manifest.adopt_registered_live_apps(
                    {"us": self.ids | {APPSTORE["zafe"]}, "tw": self.ids | {APPSTORE["zafe"]}},
                    appstore=APPSTORE, registry=APPS,
                )
        self.assertEqual(self.original, self.roster_path.read_bytes())
        self.assertFalse(list(self.root.glob("*.part")))

    def test_legacy_environment_is_never_used_as_a_manifest_fallback(self):
        legacy = self.root / "apps.json"
        legacy.write_text(json.dumps([{}] * 45), encoding="utf-8")
        reports = self.root / "reports"
        with (
            mock.patch.dict(os.environ, {"GEO_PUBLIC_INVENTORY_BASELINE": str(legacy)}) as environment,
            mock.patch.object(manifest, "runtime_manifest_path", return_value=self.runtime),
            mock.patch.object(outreach_scorecard, "REPORTS", str(reports)),
            mock.patch.object(outreach_scorecard, "JSON_OUT", str(reports / "coverage.json")),
            mock.patch.object(outreach_scorecard, "MD_OUT", str(reports / "coverage.md")),
            mock.patch.object(outreach_scorecard, "_social_posts", return_value=[]),
            mock.patch.object(outreach_scorecard, "_exists", return_value=False),
            mock.patch("urllib.request.urlopen", side_effect=AssertionError("No network")),
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
        ):
            environment.pop("GROWTH_LIVE_MANIFEST", None)
            self.assertEqual(0, outreach_scorecard.main([]))
        document = json.loads((reports / "coverage.json").read_text())
        self.assertEqual(self.app_count, document["live_app_count"])
        self.assertEqual(self.app_count, document["public_apps"])
        self.assertCountEqual(
            self.roster["apps"],
            [row["key"] for row in document["rows"] if row["in_live_roster"]],
        )
        outside = [row for row in document["rows"] if not row["in_live_roster"]]
        self.assertCountEqual(
            set(outreach_scorecard.APPS) - set(self.roster["apps"]),
            [row["key"] for row in outside],
        )
        self.assertTrue(all(not row["public"] for row in outside))
        self.assertEqual(0, document["verified_public_apps"])
        self.assertTrue(document["inventory_complete"])
        self.assertFalse(document["availability_complete"])

    def test_publisher_keeps_snapshot_and_embedded_evidence_outside_pages(self):
        with (
            mock.patch.object(publish, "PAGES", str(self.root / "site")),
            mock.patch.object(sys, "argv", ["publish.py", "--no-push"]),
            mock.patch.object(publish, "require", side_effect=RuntimeError("stop before rebuild")) as require,
            mock.patch.dict(os.environ, {"GROWTH_MANIFEST_PREPARED": ""}),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop before rebuild"):
                publish.main()
        command = require.call_args.args[0]
        output = Path(command[command.index("--output") + 1])
        self.assertEqual(self.runtime, output)
        self.assertFalse(output.is_relative_to(self.root / "site"))
        self.assertFalse(Path(require.call_args.kwargs["env"]["GEO_REPORTS"]).is_relative_to(self.root / "site"))

    def test_legacy_membership_output_has_no_timestamp_churn(self):
        output = self.root / "site" / ".appstore_live_state.json"
        first = manifest.create_manifest(self.roster["apps"], now=self.now - timedelta(hours=1))
        second = manifest.create_manifest(self.roster["apps"], now=self.now)
        manifest.write_legacy_live_state(output, first)
        before = output.read_bytes()
        manifest.write_legacy_live_state(output, second)
        self.assertEqual(before, output.read_bytes())
        self.assertNotIn("generated_at", json.loads(before))

    def test_catchup_uses_durable_registry_and_explicit_adoption_api(self):
        document = manifest.create_manifest(self.roster["apps"], now=self.now)
        observation = {"generated_at": self.now.isoformat()}
        with (
            mock.patch.object(
                new_app_catchup.catchup_health, "observe_apple", return_value=observation,
            ) as observe,
            mock.patch.object(new_app_catchup.catchup_health, "write_observation") as write,
            mock.patch.object(new_app_catchup, "refresh_manifest", return_value=document) as refresh,
        ):
            changed, returned = new_app_catchup.refresh_registered_inventory()
        self.assertEqual([], changed)
        self.assertEqual(document, returned)
        self.assertTrue(refresh.call_args.kwargs["adopt"])
        self.assertEqual(APPSTORE["battai"], refresh.call_args.args[0]["battai"])
        self.assertEqual(APPS["battai"]["name"], refresh.call_args.args[1]["battai"]["name"])
        observe.assert_called_once_with(refresh.call_args.args[0])
        self.assertEqual(self.now, refresh.call_args.kwargs["now"])
        write.assert_called_once_with(observation, document, root=new_app_catchup.PRIVATE_ROOT)

    def test_catchup_repins_alternatives_authority_when_the_roster_grows(self):
        # 2026-11-05: Meow Party joined the roster but the alternatives pin stayed
        # at 58 Apps, so the Guide Deploy preflight held every paired release.
        document = manifest.create_manifest(self.roster["apps"], now=self.now)
        observation = {"generated_at": self.now.isoformat()}
        import alternatives_i18n

        with (
            mock.patch.object(new_app_catchup.catchup_health, "observe_apple", return_value=observation),
            mock.patch.object(new_app_catchup.catchup_health, "write_observation"),
            mock.patch.object(new_app_catchup, "refresh_manifest", return_value=document),
            mock.patch.object(new_app_catchup, "canonical_manifest",
                              return_value={"roster_digest": "before-new-app"}),
            mock.patch.object(alternatives_i18n, "repin_authority", return_value=True) as repin,
            mock.patch.object(alternatives_i18n, "load_manifest") as load,
        ):
            changed, _ = new_app_catchup.refresh_registered_inventory()
        self.assertEqual(
            [new_app_catchup.DEFAULT_ROSTER, new_app_catchup.ALTERNATIVES_MANIFEST], changed
        )
        repin.assert_called_once_with(new_app_catchup.ALTERNATIVES_MANIFEST)
        load.assert_called_once_with(new_app_catchup.ALTERNATIVES_MANIFEST)
        self.assertIn("alternatives_route_manifest_v1.json", new_app_catchup.MIRROR_GEO_FILENAMES)

    def test_smaller_public_catalog_never_becomes_the_private_inventory_baseline(self):
        inventory = manifest.create_manifest(self.roster["apps"], now=self.now)
        inventory["observations"]["battai"].update(
            status="unavailable", consecutive_misses=3, reason="Three clean misses",
        )
        manifest.write_manifest(self.runtime, inventory, private=True)
        private = self.root / "coverage"
        destination = private / "owned.json"

        def scorecard(command, *, cwd, env):
            payload = {
                "schema": "lumi.outreach-scorecard/v2",
                "generated_at": self.now.isoformat(), "live_inventory": inventory,
                "live_app_count": self.app_count, "public_apps": self.app_count - 1,
                "rows": [
                    {
                        "key": key, **app, "in_live_roster": True,
                        "public": key != "battai", "coverage_score": 0,
                        "inventory_status": "unavailable" if key == "battai" else "live",
                    }
                    for key, app in self.roster["apps"].items()
                ],
            }
            (Path(env["GEO_REPORTS"]) / "outreach_coverage.json").write_text(json.dumps(payload), encoding="utf-8")

        with (
            mock.patch.object(new_app_catchup, "PRIVATE_ROOT", private),
            mock.patch.object(new_app_catchup, "PRIVATE_OUTREACH_COVERAGE", destination),
            mock.patch.object(new_app_catchup, "run", side_effect=scorecard),
        ):
            new_app_catchup.refresh_private_outreach_coverage(
                {app["app_id"]: key for key, app in self.roster["apps"].items()},
                self.ids - {APPSTORE["battai"]},
            )
        report = json.loads(destination.read_text())
        self.assertEqual(self.app_count, report["live_app_count"])
        self.assertCountEqual(self.roster["apps"], [row["key"] for row in report["rows"]])


if __name__ == "__main__":
    unittest.main()
