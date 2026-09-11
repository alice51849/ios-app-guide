#!/usr/bin/env python3
"""Regression tests for source-bound high-intent decision routes."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qsl, urlsplit


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import high_intent_decision_routes as routes  # noqa: E402
import close_sitemap_graph  # noqa: E402
import portfolio_app_finder as finder  # noqa: E402
import publish as geo_publish  # noqa: E402
import sync_standard_site  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from videogen.registry import APPS  # noqa: E402


SOURCE_PATH = GEO / "data" / "high_intent_decision_routes_v2.json"
TEST_PROVIDER_TOKEN = "118326163"
CURRENT_SOURCE_ROOT = (
    Path(os.environ["HIGH_INTENT_CURRENT_SOURCE_ROOT"])
    if os.environ.get("HIGH_INTENT_CURRENT_SOURCE_ROOT")
    else None
)
RELEASE_CARDINALITY_SYMBOLS = (
    "EXPECTED_APP_COUNT",
    "EXPECTED_ROUTE_COUNT",
    "EXPECTED_PAIR_COUNT",
    "EXPECTED_ABSTAINED_PAIR_COUNT",
    "EXPECTED_LIVE_APP_COUNT",
    "EXPECTED_APP_LOCALE_PAIRS",
    "EXPECTED_ABSTAINED_PAIRS",
    "EXPECTED_LIVE_APP_KEYS_SHA256",
)


def git_repository_root(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def deployed_guide_repository() -> Path | None:
    repository = git_repository_root(GEO)
    if repository is None:
        return None
    if GEO.resolve() != (repository / "_engine" / "geo").resolve():
        return None
    workflow = repository / ".github" / "workflows" / "geo-daily.yml"
    if not workflow.is_file():
        raise AssertionError("Deployed Guide checkout is missing geo-daily.yml")
    return repository


DEPLOYED_GUIDE_REPOSITORY = deployed_guide_repository()
GUIDE_REPOSITORY = DEPLOYED_GUIDE_REPOSITORY or Path(
    os.environ.get(
        "HIGH_INTENT_GUIDE_REPOSITORY",
        Path.home() / "00_GrowthEngine" / "geo" / "pages",
    )
)
GUIDE_WORKFLOW = GUIDE_REPOSITORY / ".github" / "workflows" / "geo-daily.yml"
GROWTH_REPOSITORY = Path(
    os.environ.get("HIGH_INTENT_GROWTH_REPOSITORY", GEO.parent)
)


def current_guide_inventory_path() -> Path:
    repository = DEPLOYED_GUIDE_REPOSITORY or GUIDE_REPOSITORY
    canonical = repository / "data" / routes.INVENTORY_FILENAME
    override = os.environ.get("HIGH_INTENT_TEST_INVENTORY")
    if override and Path(override).resolve() != canonical.resolve():
        raise AssertionError(
            "HIGH_INTENT_TEST_INVENTORY cannot override canonical Guide inventory"
        )
    return canonical


def guide_gitlink_revision() -> str:
    result = subprocess.run(
        ["git", "-C", str(GROWTH_REPOSITORY), "ls-files", "--stage", "geo/pages"],
        capture_output=True, text=True, check=False,
    )
    fields = result.stdout.strip().split()
    if (
        result.returncode != 0
        or len(fields) != 4
        or fields[0] != "160000"
        or len(fields[1]) != 40
        or fields[2:] != ["0", "geo/pages"]
    ):
        raise AssertionError("GrowthEngine must pin one resolved geo/pages gitlink")
    return fields[1]


def write_contracted_guide_inventory(
    root: Path,
    app_keys: tuple[str, ...],
) -> Path:
    if DEPLOYED_GUIDE_REPOSITORY is not None:
        # The workflow rebuilds this canonical file before running tests.
        inventory = json.loads(
            current_guide_inventory_path().read_text(encoding="utf-8")
        )
    else:
        revision = guide_gitlink_revision()
        result = subprocess.run(
            [
                "git",
                "-C",
                str(GUIDE_REPOSITORY),
                "show",
                f"{revision}:data/{routes.INVENTORY_FILENAME}",
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"Unable to read Guide inventory at {revision}: "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        inventory = json.loads(result.stdout)

    expected = set(app_keys)
    missing = sorted(expected - {app["key"] for app in inventory["apps"]})
    if missing:
        raise AssertionError(
            f"Guide inventory is missing expected release app keys: {missing}"
        )
    inventory["apps"] = [
        app for app in inventory["apps"] if app["key"] in expected
    ]
    if len(inventory["apps"]) != len(expected):
        raise AssertionError("Guide inventory repeats expected release app keys")
    inventory["record_count"] = len(inventory["apps"])
    inventory_path = root / "inventory-contracted.json"
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False),
        encoding="utf-8",
    )
    return inventory_path


class HighIntentInventoryContextTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(
            prefix=".high-intent-context-test-",
            dir=GEO / "tests",
        )
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.guide = self.root / "guide"
        self.growth = self.root / "growth"
        self.inventory_path = self.guide / "data" / routes.INVENTORY_FILENAME
        self.inventory_path.parent.mkdir(parents=True)
        self.output = self.root / "output"
        self.output.mkdir()
        self.app_keys = ("reviewed-one", "reviewed-two")
        self.inventory = {
            "record_count": 2,
            "apps": [
                {"key": key, "name": key} for key in self.app_keys
            ],
        }
        self.write_current_inventory(self.inventory)
        context = mock.patch.dict(
            globals(),
            {
                "DEPLOYED_GUIDE_REPOSITORY": self.guide,
                "GUIDE_REPOSITORY": self.root / "unrelated-guide",
                "GROWTH_REPOSITORY": self.growth,
            },
        )
        context.start()
        self.addCleanup(context.stop)
        environment = mock.patch.dict(
            os.environ, {"HIGH_INTENT_TEST_INVENTORY": ""}
        )
        environment.start()
        self.addCleanup(environment.stop)

    def write_current_inventory(self, inventory: dict) -> None:
        self.inventory_path.write_text(
            json.dumps(inventory), encoding="utf-8"
        )

    @staticmethod
    def git(repository: Path, *arguments: str) -> str:
        return subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "user.name=Inventory Fixture",
                "-c",
                "user.email=inventory-fixture@example.invalid",
                "-c",
                "commit.gpgSign=false",
                "-c",
                "core.hooksPath=/dev/null",
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def pin_committed_inventory(self) -> str:
        self.git(self.guide, "init", "--quiet")
        self.git(self.guide, "add", "data")
        self.git(self.guide, "commit", "--quiet", "-m", "Inventory fixture")
        revision = self.git(self.guide, "rev-parse", "HEAD")
        self.growth.mkdir()
        self.git(self.growth, "init", "--quiet")
        self.git(
            self.growth,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},geo/pages",
        )
        context = mock.patch.dict(
            globals(),
            {
                "DEPLOYED_GUIDE_REPOSITORY": None,
                "GUIDE_REPOSITORY": self.guide,
            },
        )
        context.start()
        self.addCleanup(context.stop)
        return revision

    def test_deployed_missing_expected_app_fails_before_writing_fixture(self):
        for apps in (
            self.inventory["apps"][:1],
            [self.inventory["apps"][0], {"key": "new-live-app"}],
        ):
            with self.subTest(keys=[app["key"] for app in apps]):
                self.write_current_inventory(
                    {"record_count": len(apps), "apps": apps}
                )
                with self.assertRaisesRegex(
                    AssertionError,
                    "missing expected release app keys.*reviewed-two",
                ):
                    write_contracted_guide_inventory(self.output, self.app_keys)
                self.assertEqual([], list(self.output.iterdir()))

    def test_deployed_extra_app_does_not_pollute_exact_fixture(self):
        inventory = deepcopy(self.inventory)
        inventory["apps"].append({"key": "new-live-app"})
        inventory["record_count"] = len(inventory["apps"])
        self.write_current_inventory(inventory)
        original = self.inventory_path.read_bytes()

        fixture = write_contracted_guide_inventory(self.output, self.app_keys)

        self.assertEqual(self.inventory, json.loads(fixture.read_text()))
        self.assertEqual(original, self.inventory_path.read_bytes())
        self.assertIn(
            "new-live-app",
            {app["key"] for app in json.loads(original)["apps"]},
        )

    def test_deployed_duplicate_expected_app_fails_closed(self):
        inventory = deepcopy(self.inventory)
        inventory["apps"].append(deepcopy(inventory["apps"][0]))
        inventory["record_count"] = len(inventory["apps"])
        self.write_current_inventory(inventory)
        with self.assertRaisesRegex(
            AssertionError, "repeats expected release app keys"
        ):
            write_contracted_guide_inventory(self.output, self.app_keys)
        self.assertEqual([], list(self.output.iterdir()))

    def test_deployed_env_path_cannot_bypass_missing_expected_app(self):
        override = self.root / "override.json"
        override.write_bytes(self.inventory_path.read_bytes())
        self.write_current_inventory(
            {"record_count": 1, "apps": self.inventory["apps"][:1]}
        )
        with mock.patch.dict(
            os.environ, {"HIGH_INTENT_TEST_INVENTORY": str(override)}
        ):
            with self.assertRaisesRegex(
                AssertionError, "HIGH_INTENT_TEST_INVENTORY.*canonical"
            ):
                write_contracted_guide_inventory(self.output, self.app_keys)
        self.assertEqual([], list(self.output.iterdir()))

    def test_deployed_canonical_inventory_never_consults_git_head(self):
        with (
            mock.patch.dict(
                os.environ,
                {"HIGH_INTENT_TEST_INVENTORY": str(self.inventory_path)},
            ),
            mock.patch.object(subprocess, "run") as run,
        ):
            self.assertEqual(
                self.inventory_path, current_guide_inventory_path()
            )
            fixture = write_contracted_guide_inventory(
                self.output, self.app_keys
            )
            run.assert_not_called()
        self.assertEqual(self.inventory, json.loads(fixture.read_text()))

    def test_deployed_missing_canonical_inventory_has_no_fallback(self):
        self.inventory_path.unlink()
        with mock.patch.object(subprocess, "run") as run:
            with self.assertRaises(FileNotFoundError):
                write_contracted_guide_inventory(self.output, self.app_keys)
            run.assert_not_called()
        self.assertEqual([], list(self.output.iterdir()))

    def test_growth_fixture_reads_real_gitlink_blob_not_mutable_inventory(self):
        inventory = deepcopy(self.inventory)
        inventory["apps"].append({"key": "new-live-app"})
        inventory["record_count"] = len(inventory["apps"])
        self.write_current_inventory(inventory)
        revision = self.pin_committed_inventory()
        self.write_current_inventory(
            {"record_count": 1, "apps": [{"key": "mutable-current-app"}]}
        )

        self.assertEqual(revision, guide_gitlink_revision())
        fixture = write_contracted_guide_inventory(self.output, self.app_keys)

        self.assertEqual(self.inventory, json.loads(fixture.read_text()))
        self.assertEqual(
            ["mutable-current-app"],
            [
                app["key"]
                for app in json.loads(self.inventory_path.read_text())["apps"]
            ],
        )

    def test_growth_missing_expected_app_in_committed_blob_fails_closed(self):
        self.write_current_inventory(
            {"record_count": 1, "apps": self.inventory["apps"][:1]}
        )
        self.pin_committed_inventory()
        self.write_current_inventory(self.inventory)
        with self.assertRaisesRegex(
            AssertionError, "missing expected release app keys.*reviewed-two"
        ):
            write_contracted_guide_inventory(self.output, self.app_keys)
        self.assertEqual([], list(self.output.iterdir()))

    def test_growth_missing_committed_blob_cannot_use_current_inventory(self):
        self.pin_committed_inventory()
        self.git(self.guide, "rm", "--quiet", str(self.inventory_path))
        self.git(self.guide, "commit", "--quiet", "-m", "Remove fixture")
        revision = self.git(self.guide, "rev-parse", "HEAD")
        self.git(
            self.growth,
            "update-index",
            "--cacheinfo",
            f"160000,{revision},geo/pages",
        )
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.write_current_inventory(self.inventory)
        with self.assertRaisesRegex(AssertionError, "Unable to read Guide inventory"):
            write_contracted_guide_inventory(self.output, self.app_keys)
        self.assertEqual([], list(self.output.iterdir()))

    def test_growth_rejects_regular_file_instead_of_gitlink(self):
        self.pin_committed_inventory()
        blob = self.git(
            self.guide, "rev-parse", f"HEAD:data/{routes.INVENTORY_FILENAME}"
        )
        self.git(
            self.growth,
            "update-index",
            "--cacheinfo",
            f"100644,{blob},geo/pages",
        )
        with self.assertRaisesRegex(AssertionError, "resolved geo/pages gitlink"):
            write_contracted_guide_inventory(self.output, self.app_keys)
        self.assertEqual([], list(self.output.iterdir()))


class HighIntentRouteSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    def test_deployment_identity_is_content_bound(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            f"{routes.DEPLOYMENT_ID_PREFIX}:{digest}",
            routes.deployment_identity(digest),
        )
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            routes.deployment_identity("a" * 40)

    def test_source_maps_every_contracted_app_to_one_primary_route(self) -> None:
        source_routes = self.source["routes"]
        release = routes.release_expectations(self.source)
        self.assertEqual(release["app_count"], len(source_routes))
        self.assertEqual(
            release["app_count"],
            len({route["app_key"] for route in source_routes}),
        )
        self.assertTrue(all(route["primary"] is True for route in source_routes))
        self.assertEqual(
            release["app_count"],
            len({route["route_slug"] for route in source_routes}),
        )

    def test_zipbox_route_preserves_paid_archive_boundaries(self) -> None:
        route = next(
            route
            for route in self.source["routes"]
            if route["app_key"] == "zipbox"
        )
        copy = route["locales"]["en-US"]
        joined = " ".join(
            [
                copy["query"],
                copy["buyer_problem"],
                copy["decision_rule"],
                copy["alternative_lens"],
                *copy["workflow_checks"],
                *copy["verify_before_install"],
            ]
        )

        self.assertEqual("privacy_pay_once", route["intent_type"])
        self.assertIn("pay-once", joined)
        self.assertIn("encrypted", joined)
        self.assertIn("split", joined)
        self.assertIn("RAR and RAR5 are extraction-only", joined)
        self.assertIn("standalone Zstandard (.zst)", joined)
        self.assertIn("capability.no_ads", copy["evidence_refs"])

    def test_zipbox_registry_facts_keep_positional_evidence_stable(
        self,
    ) -> None:
        app = APPS["zipbox"]
        self.assertEqual(
            [
                "13 archive formats",
                "Encrypted + split archives",
                "Create ZIP + 7z",
                "On-device",
                "Offline",
                "No account",
                "No ads",
                "No tracking",
            ],
            app["cta_bullets"],
        )
        self.assertNotIn(
            "free",
            " ".join(app["keywords"]).casefold().split(),
        )
        capabilities = finder.explicit_capabilities(app)
        self.assertTrue(capabilities["offline"])
        self.assertTrue(capabilities["no_tracking"])

    def test_source_uses_all_four_decision_intents_without_one_template(self) -> None:
        source_routes = self.source["routes"]
        counts = {
            intent: sum(
                route["intent_type"] == intent for route in source_routes
            )
            for intent in routes.INTENT_TYPES
        }
        self.assertEqual(set(routes.INTENT_TYPES), set(counts))
        self.assertTrue(all(count > 0 for count in counts.values()), counts)
        self.assertLessEqual(max(counts.values()), 26, counts)
        english_queries = [
            route["locales"]["en-US"]["query"] for route in source_routes
        ]
        self.assertEqual(len(english_queries), len(set(english_queries)))

    def test_locale_copy_is_explicit_and_never_declares_fallback(self) -> None:
        for route in self.source["routes"]:
            with self.subTest(app_key=route["app_key"]):
                self.assertIn("en-US", route["locales"])
                self.assertNotIn("fallback_locale", route)
                for locale, copy in route["locales"].items():
                    self.assertIn(locale, OFFICIAL_LOCALES)
                    self.assertIn(locale, routes.LOCALE_LANGUAGE)
                    self.assertEqual(
                        routes.LOCALE_LANGUAGE[locale],
                        copy["language"],
                    )
                    self.assertGreaterEqual(
                        len(copy["culture_route"]),
                        45,
                    )

    def test_generator_has_no_ai_or_network_dependency(self) -> None:
        source = (GEO / "high_intent_decision_routes.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("import openai", source.casefold())
        self.assertNotIn("from openai", source.casefold())
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.request", source)

    def test_release_cardinality_is_not_hardcoded_in_producer(self):
        producer = (GEO / "high_intent_decision_routes.py").read_text(
            encoding="utf-8"
        )
        for symbol in RELEASE_CARDINALITY_SYMBOLS:
            self.assertNotIn(symbol, producer)

    def test_controller_keys_are_not_hardcoded(self):
        controller_path = (
            GROWTH_REPOSITORY
            / "agent"
            / "organic_experiment_controller.py"
        )
        if not controller_path.is_file():
            if DEPLOYED_GUIDE_REPOSITORY is not None:
                self.skipTest("Growth-only controller is not deployed to Guide")
            self.fail(f"GrowthEngine controller is missing: {controller_path}")
        controller = controller_path.read_text(encoding="utf-8")
        for symbol in RELEASE_CARDINALITY_SYMBOLS:
            self.assertNotIn(symbol, controller)
        self.assertNotIn(
            self.source["inventory_contract"]["app_keys_sha256"],
            controller,
        )

    def test_official_locale_digest_drift_fails_closed(self) -> None:
        changed = deepcopy(self.source)
        changed["inventory_contract"]["official_locales_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "OFFICIAL_LOCALES drifted"):
            routes.release_expectations(changed)

    def test_intents_use_the_single_authoritative_campaign_contract(self) -> None:
        self.assertEqual("geo_ask", routes.campaign_token("problem_aware"))
        self.assertEqual("geo_pick", routes.campaign_token("alternative"))
        self.assertEqual("geo_learn", routes.campaign_token("workflow"))
        self.assertEqual("geo_pick", routes.campaign_token("privacy_pay_once"))
        self.assertTrue(
            all(
                len(routes.campaign_token(intent)) <= 30
                for intent in routes.INTENT_TYPES
            )
        )
        self.assertNotIn("iag_h2_", (GEO / "high_intent_decision_routes.py").read_text())

    def test_sync_contract_exactly_identifies_the_production_mirror(self) -> None:
        contract = routes.validate_sync_contract()
        self.assertEqual(routes.build_sync_contract(), contract)
        self.assertEqual(
            [
                "_engine/geo/high_intent_decision_routes.py",
                "_engine/geo/data/high_intent_decision_routes_v2.json",
                "_engine/geo/conversion_route_contract.py",
                "_engine/geo/data/high_intent_conversion_contracts_v1.json",
                "_engine/geo/gen_store_attribution.py",
                "_engine/geo/market_availability.py",
                "_engine/geo/market_surface_policy.py",
                "_engine/geo/gen_market_availability.py",
                "_engine/geo/official_locales.py",
                "_engine/geo/publish.py",
                "_engine/geo/sync_standard_site.py",
                "_engine/geo/site_config.py",
                "_engine/geo/websub_config.py",
            ],
            [entry["target_path"] for entry in contract["files"]],
        )

    @unittest.skipUnless(
        CURRENT_SOURCE_ROOT is not None,
        "Separate current GrowthEngine source checkout is not mounted",
    )
    def test_review_repro_mirror_matches_separate_current_source(self) -> None:
        contract = routes.validate_sync_contract(
            current_source_root=CURRENT_SOURCE_ROOT,
            require_external_source=True,
        )
        self.assertEqual(
            routes.build_sync_contract(),
            contract,
        )

    def test_review_repro_external_source_digest_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-source-drift-test-",
            dir=GEO / "tests",
        ) as scratch:
            source_root = Path(scratch) / "geo"
            for relative in routes.SYNC_ENGINE_FILES:
                target = source_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(GEO / relative, target)
            contract_target = (
                source_root
                / "data"
                / routes.SYNC_CONTRACT_PATH.name
            )
            contract_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(routes.SYNC_CONTRACT_PATH, contract_target)
            (source_root / routes.SYNC_ENGINE_FILES[0]).write_text(
                "# drift\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                "Current GrowthEngine source digest drift",
            ):
                routes.validate_sync_contract(
                    current_source_root=source_root,
                    require_external_source=True,
                )

    def test_daily_pipeline_executes_materialization_closure(self) -> None:
        commands: list[tuple[str, ...]] = []

        def record(command, cwd=None, env=None):
            del cwd, env
            commands.append(tuple(command))
            return ""

        with mock.patch.object(geo_publish, "require", side_effect=record), (
            mock.patch.object(sys, "argv", ["publish.py", "--no-push"])
        ):
            geo_publish.main()

        scripts = [
            next(
                (
                    Path(argument).name
                    for argument in command
                    if argument.endswith(".py")
                ),
                command[0],
            )
            for command in commands
        ]
        generated = scripts.index("high_intent_decision_routes.py")
        normalized = scripts.index("normalize_app_store_links.py")
        graph = scripts.index("close_sitemap_graph.py")
        attribution = scripts.index("gen_store_attribution.py")
        feed = scripts.index("gen_feed.py")
        audit = scripts.index("audit_link_depth.py")
        closure = len(scripts) - 1 - scripts[::-1].index(
            "high_intent_decision_routes.py"
        )
        self.assertLess(generated, graph)
        self.assertLess(generated, normalized)
        self.assertLess(graph, attribution)
        self.assertLess(attribution, feed)
        self.assertLess(feed, audit)
        self.assertLess(audit, closure)
        self.assertIn("--output-dir", commands[generated])
        self.assertIn("--materialize-current-inventory", commands[generated])
        self.assertIn("--check-materialization-closure", commands[closure])
        self.assertNotIn("--check-production-closure", commands[closure])

    @unittest.skipUnless(
        GUIDE_WORKFLOW.is_file(),
        "Guide production workflow is not present in the source repository",
    )
    def test_guide_daily_runs_each_generator_through_full_closure(self) -> None:
        source = GUIDE_WORKFLOW.read_text(encoding="utf-8")

        def workflow_step(name: str, next_name: str) -> str:
            return source.split(f"- name: {name}", 1)[1].split(
                f"- name: {next_name}",
                1,
            )[0]

        def python_commands(segment: str) -> list[str]:
            lines = segment.splitlines()
            commands: list[str] = []
            position = 0
            while position < len(lines):
                stripped = lines[position].strip()
                if not stripped.startswith("python3 "):
                    position += 1
                    continue
                parts = [stripped.removesuffix("\\").strip()]
                while lines[position].rstrip().endswith("\\"):
                    position += 1
                    if position >= len(lines):
                        raise AssertionError(
                            "unterminated multiline Python command"
                        )
                    parts.append(
                        lines[position].strip().removesuffix("\\").strip()
                    )
                commands.append(" ".join(parts))
                position += 1
            return commands

        segments = (
            workflow_step(
                "Materialize newly live app surfaces",
                "Verify zero-cost growth infrastructure",
            ),
            workflow_step(
                "Commit English content first (fast, before slow localization)",
                "Localize from curated dictionaries (zero-cost, no API)",
            ),
            workflow_step(
                "Final link and availability cleanup",
                "Verify localized output before commit",
            ),
            workflow_step(
                "Commit localized pages if any",
                "Unlink site dir",
            ),
        )
        self.assertEqual(5, source.count("--materialize-current-inventory"))
        self.assertEqual(4, source.count("--check-materialization-closure"))
        for segment in segments:
            commands = python_commands(segment)
            generators = [
                index for index, command in enumerate(commands)
                if "--materialize-current-inventory" in command
            ]
            closures = [
                index for index, command in enumerate(commands)
                if "--check-materialization-closure" in command
            ]
            self.assertGreaterEqual(len(generators), 1)
            self.assertEqual(1, len(closures))
            generator = generators[-1]
            closure = closures[0]
            self.assertLess(generator, closure)

            def next_command(name: str, after: int) -> int:
                return next(
                    index
                    for index in range(after + 1, closure)
                    if name in commands[index]
                )

            graph = next_command("close_sitemap_graph.py", generator)
            attribution = next_command("gen_store_attribution.py", graph)
            feed = next_command("gen_feed.py", attribution)
            audit = next_command("audit_link_depth.py", feed)
            self.assertLess(audit, closure)

    @unittest.skipUnless(
        (GUIDE_REPOSITORY / ".github" / "workflows").is_dir(),
        "Guide Pages workflows are not present in the source repository",
    )
    def test_every_pages_upload_is_preceded_by_the_hard_gate(self) -> None:
        workflows = GUIDE_REPOSITORY / ".github" / "workflows"
        upload_count = 0
        for path in sorted(
            [*workflows.glob("*.yml"), *workflows.glob("*.yaml")]
        ):
            source = path.read_text(encoding="utf-8")
            cursor = 0
            marker = "actions/upload-pages-artifact@"
            while (upload := source.find(marker, cursor)) >= 0:
                upload_count += 1
                prepare = source.rfind(
                    "- name: Prepare externally bound high-intent deployment",
                    0,
                    upload,
                )
                gate = source.rfind("--prepare-pages-deployment", 0, upload)
                self.assertGreater(
                    gate,
                    prepare,
                    f"{path.name} can upload Pages without the hard gate",
                )
                guarded = source[prepare:upload]
                self.assertNotIn(
                    "continue-on-error: true",
                    source[gate:upload],
                    f"{path.name} makes the pre-upload gate bypassable",
                )
                self.assertIn(
                    "--current-source-root",
                    guarded,
                )
                self.assertIn(
                    "--engine-source-revision",
                    guarded,
                )
                self.assertIn(
                    "GROWTH_ENGINE_DEPLOY_KEY: "
                    "${{ secrets.GROWTH_ENGINE_DEPLOY_KEY }}",
                    guarded,
                )
                self.assertIn(
                    "git@github.com:alice51849/00_GrowthEngine.git",
                    guarded,
                )
                self.assertIn("StrictHostKeyChecking=yes", guarded)
                self.assertIn('rm -f "$key_file" "$known_hosts"', guarded)
                self.assertIn('rm -rf "$source_dir"', guarded)
                self.assertNotIn("uses: actions/checkout@", guarded)
                cursor = upload + len(marker)
        self.assertGreater(upload_count, 0)


class HighIntentManagedOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(
            prefix=".high-intent-output-test-",
            dir=GEO / "tests",
        )
        self.pages = Path(self.scratch.name)

    def tearDown(self) -> None:
        self.scratch.cleanup()

    def record(
        self,
        app: str,
        *,
        intent: str = "problem_aware",
        slug: str = "primary",
    ) -> dict:
        campaign = routes.campaign_token(intent)
        relative = Path("en-US") / "decide" / app / f"{slug}.html"
        value = {
            "route_id": f"en-US:{app}:{slug}",
            "app_key": app,
            "app_name": app.title(),
            "app_store_id": "1234567890",
            "category": "productivity",
            "purchase_model": "free_with_lifetime_unlock",
            "one_time_option": True,
            "locale": "en-US",
            "language": "en",
            "market": "United States",
            "intent_type": intent,
            "campaign_token": campaign,
            "primary": True,
            "route_slug": slug,
            "query": f"Which {app} workflow should I choose?",
            "culture_route": "A United States workflow with explicit trade-offs.",
            "buyer_problem": "Choose a focused workflow without hidden claims.",
            "decision_rule": "Verify the documented workflow before installing.",
            "workflow_checks": [
                "Does it fit the task?",
                "Is the purchase model clear?",
                "Can the workflow be verified?",
            ],
            "alternative_lens": "Choose another route when the task differs.",
            "verify_before_install": [
                "Confirm current App Store availability.",
                "Confirm the documented purchase model.",
            ],
            "evidence": [
                {
                    "reference": "feature.0",
                    "inventory_pointer": f"/apps/{app}/features/0",
                    "source_value": "Workflow",
                    "text": "Workflow",
                }
            ],
            "source_vocabulary": ["workflow", "private"],
            "inventory_source": f"{routes.SITE}/data/{routes.INVENTORY_FILENAME}",
            "canonical_url": f"{routes.SITE}/{relative.as_posix()}",
            "app_store_url": (
                "https://apps.apple.com/app/id1234567890"
                f"?pt={TEST_PROVIDER_TOKEN}&ct={campaign}&mt=8"
            ),
            "publisher": "Lumi Studio",
            "publisher_relationship": "app_developer",
            "publisher_disclosure": (
                "This guide is published by Lumi Studio, the app developer."
            ),
            "is_independent_review": False,
            "is_ranking": False,
            "content_units": 200,
        }
        value["creative_id"], value["creative_digest"] = (
            routes._creative_identity(
                app,
                slug,
                intent,
                campaign,
            )
        )
        return value

    @staticmethod
    def report(count: int) -> dict:
        return {
            "schema_version": 1,
            "dataset": "test",
            "release_state": routes.RELEASE_STATE_EXACT,
            "release_contract_digest": "c" * 64,
            "inventory": {
                "relative_path": f"data/{routes.INVENTORY_FILENAME}",
                "public_apps": count,
                "app_keys_sha256": "a" * 64,
                "copy_sha256": "b" * 64,
                "official_locales_sha256": "d" * 64,
            },
            "current_inventory": {
                "public_apps": count,
                "app_keys_sha256": "a" * 64,
                "copy_sha256": "b" * 64,
                "missing_route_app_keys": [],
                "missing_route_app_keys_sha256": routes._sha256_json([]),
            },
            "coverage": {
                "mapped_apps": count,
                "current_public_apps": count,
                "missing_route_apps": 0,
                "missing_route_app_keys": [],
                "candidate_app_locale_pairs": count,
                "fallback_records": 0,
                "abstained_pairs": 0,
            },
            "quality": {"all_gates_passed": True},
        }

    def test_old_manifest_upgrades_without_weakening_current_release_contract(self):
        record = self.record("alpha")
        routes.write_outputs([record], self.report(1), self.pages)
        path = self.pages / routes.MANIFEST_RELATIVE
        legacy = json.loads(path.read_text())
        added = set(routes.FIXED_MANAGED_OUTPUTS) - set(routes.LEGACY_FIXED_MANAGED_OUTPUTS)
        legacy["expected_outputs"] = [
            row for row in legacy["expected_outputs"] if row["relative_path"] not in added
        ]
        legacy["manifest_digest"] = routes._sha256_json(routes._manifest_without_digest(legacy))
        for relative in added:
            (self.pages / relative).unlink()
        path.write_text(json.dumps(legacy))
        with self.assertRaisesRegex(ValueError, "fixed outputs"):
            routes._validate_manifest(legacy)
        result = routes.write_outputs([record], self.report(1), self.pages)
        self.assertEqual(0, result["stale_routes_removed"])
        routes._validate_manifest(json.loads(path.read_text()))
        self.assertTrue(all((self.pages / relative).is_file() for relative in added))

    def assert_manifest_rejected_before_output_io(
        self,
        mutate,
    ) -> None:
        record = self.record("alpha")
        routes.write_outputs([record], self.report(1), self.pages)
        manifest_path = self.pages / routes.MANIFEST_RELATIVE
        valid_manifest_text = manifest_path.read_text(encoding="utf-8")
        baseline = json.loads(valid_manifest_text)
        mutate(baseline)
        baseline["manifest_digest"] = routes._sha256_json(
            routes._manifest_without_digest(baseline)
        )
        for strict_release, provide_expected in (
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ):
            with self.subTest(
                strict_release=strict_release,
                expected_manifest=provide_expected,
            ):
                manifest_path.write_text(
                    json.dumps(baseline),
                    encoding="utf-8",
                )
                expected = deepcopy(baseline) if provide_expected else None
                with (
                    mock.patch.object(
                        Path,
                        "is_file",
                        side_effect=AssertionError(
                            "output is_file reached before manifest rejection"
                        ),
                    ) as is_file,
                    mock.patch.object(
                        Path,
                        "read_bytes",
                        side_effect=AssertionError(
                            "output read_bytes reached before manifest rejection"
                        ),
                    ) as read_bytes,
                ):
                    with self.assertRaises(ValueError):
                        routes.verify_production_closure(
                            self.pages,
                            strict_release=strict_release,
                            expected_manifest=expected,
                        )
                is_file.assert_not_called()
                read_bytes.assert_not_called()
        manifest_path.write_text(valid_manifest_text, encoding="utf-8")

    def test_regeneration_preserves_and_seals_standard_site_links(self) -> None:
        record = self.record("alpha")
        report = self.report(1)
        routes.write_outputs([record], report, self.pages)
        target = self.pages / routes.route_relative(record)
        rendered = sync_standard_site.render_html(
            target.read_text(encoding="utf-8"),
            publication_link_tag=(
                f'<link rel="{sync_standard_site.PUBLICATION_COLLECTION}" '
                'href="https://standard.site/publications/lumi">'
            ),
            document_link_tag=(
                f'<link rel="{sync_standard_site.DOCUMENT_COLLECTION}" '
                'href="https://standard.site/documents/alpha">'
            ),
            label=target.name,
        )
        target.write_text(rendered, encoding="utf-8")

        routes.write_outputs([record], report, self.pages)

        final = target.read_text(encoding="utf-8")
        self.assertIn(
            f'rel="{sync_standard_site.PUBLICATION_COLLECTION}"',
            final,
        )
        self.assertIn(
            f'rel="{sync_standard_site.DOCUMENT_COLLECTION}"',
            final,
        )
        manifest = json.loads(
            (self.pages / routes.MANIFEST_RELATIVE).read_text(
                encoding="utf-8"
            )
        )
        route = manifest["routes"][0]
        output = next(
            entry
            for entry in manifest["expected_outputs"]
            if entry["relative_path"] == route["relative_path"]
        )
        digest = routes._sha256_text(final)
        self.assertEqual(digest, route["output_sha256"])
        self.assertEqual(digest, output["generated_sha256"])

    def _assert_public_closure_rejects_unsafe_output_contracts_before_io(
        self,
    ) -> None:
        def route_output(document: dict) -> dict:
            return next(
                entry
                for entry in document["expected_outputs"]
                if entry.get("kind") == "route_html"
            )

        def fixed_output(document: dict) -> dict:
            return next(
                entry
                for entry in document["expected_outputs"]
                if entry.get("kind") == "coverage_report"
            )

        cases = {
            "missing_kind": lambda document: route_output(document).pop(
                "kind"
            ),
            "null_kind": lambda document: route_output(document).__setitem__(
                "kind",
                None,
            ),
            "empty_kind": lambda document: route_output(document).__setitem__(
                "kind",
                "",
            ),
            "unknown_kind": lambda document: route_output(
                document
            ).__setitem__("kind", "unmanaged"),
            "fixed_kind_mismatch": lambda document: fixed_output(
                document
            ).__setitem__("kind", "json_feed"),
            "null_path": lambda document: route_output(document).__setitem__(
                "relative_path",
                None,
            ),
            "non_string_path": lambda document: route_output(
                document
            ).__setitem__("relative_path", 7),
            "absolute_path": lambda document: route_output(
                document
            ).__setitem__("relative_path", "/etc/hosts"),
            "empty_path": lambda document: route_output(
                document
            ).__setitem__("relative_path", ""),
            "empty_segment": lambda document: route_output(
                document
            ).__setitem__(
                "relative_path",
                "en-US//decide/alpha/primary.html",
            ),
            "dot_segment": lambda document: route_output(
                document
            ).__setitem__(
                "relative_path",
                "en-US/./decide/alpha/primary.html",
            ),
            "dotdot_traversal": lambda document: route_output(
                document
            ).__setitem__("relative_path", "../../etc/hosts"),
            "backslash": lambda document: route_output(document).__setitem__(
                "relative_path",
                r"en-US\decide\alpha\primary.html",
            ),
            "control_character": lambda document: route_output(
                document
            ).__setitem__(
                "relative_path",
                "en-US/decide/alpha/primary\u0000.html",
            ),
            "percent_encoded_traversal": lambda document: route_output(
                document
            ).__setitem__(
                "relative_path",
                "en-US/decide/%2e%2e/primary.html",
            ),
            "percent_confusable": lambda document: route_output(
                document
            ).__setitem__(
                "relative_path",
                "en-US/decide/\uff052e\uff052e/primary.html",
            ),
            "null_digest": lambda document: route_output(
                document
            ).__setitem__("generated_sha256", None),
            "non_string_digest": lambda document: route_output(
                document
            ).__setitem__("generated_sha256", 7),
            "short_digest": lambda document: route_output(
                document
            ).__setitem__("generated_sha256", "0" * 63),
            "uppercase_digest": lambda document: route_output(
                document
            ).__setitem__("generated_sha256", "A" * 64),
            "missing_fixed_output": lambda document: document[
                "expected_outputs"
            ].remove(fixed_output(document)),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                self.assert_manifest_rejected_before_output_io(mutate)

    def _assert_public_closure_rejects_resolved_output_escape_before_io(
        self,
    ) -> None:
        record = self.record("alpha")
        routes.write_outputs([record], self.report(1), self.pages)
        shutil.rmtree(self.pages / "en-US")
        (self.pages / "en-US").symlink_to(
            self.pages.parent,
            target_is_directory=True,
        )
        with (
            mock.patch.object(
                Path,
                "is_file",
                side_effect=AssertionError(
                    "output is_file reached before containment rejection"
                ),
            ) as is_file,
            mock.patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError(
                    "output read_bytes reached before containment rejection"
                ),
            ) as read_bytes,
        ):
            with self.assertRaisesRegex(ValueError, "escapes output directory"):
                routes.verify_production_closure(
                    self.pages,
                    strict_release=False,
                    expected_manifest=None,
                )
        is_file.assert_not_called()
        read_bytes.assert_not_called()

    def test_manifest_is_deterministic_and_closes_feed_sitemap_attribution(self):
        records = [
            self.record("alpha"),
            self.record("beta", intent="workflow"),
        ]
        (self.pages / "index.html").write_text(
            (
                '<!doctype html><html lang="en"><head><title>Home</title>'
                "</head><body><main></main></body></html>"
            ),
            encoding="utf-8",
        )
        (self.pages / "sitemap.xml").write_text(
            (
                '<?xml version="1.0"?><urlset '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{routes.SITE}/index.html</loc></url></urlset>"
            ),
            encoding="utf-8",
        )
        (self.pages / "sitemap_index.xml").write_text(
            (
                '<?xml version="1.0"?><sitemapindex '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<sitemap><loc>{routes.SITE}/sitemap.xml</loc></sitemap>"
                "</sitemapindex>"
            ),
            encoding="utf-8",
        )
        (self.pages / "robots.txt").write_text(
            f"Sitemap: {routes.SITE}/sitemap_index.xml\n",
            encoding="utf-8",
        )
        first = routes.write_outputs(records, self.report(2), self.pages)
        manifest_path = self.pages / routes.MANIFEST_RELATIVE
        first_manifest = manifest_path.read_bytes()
        second = routes.write_outputs(records, self.report(2), self.pages)
        self.assertEqual(first_manifest, manifest_path.read_bytes())
        self.assertEqual(first["manifest_digest"], second["manifest_digest"])
        feed = json.loads(
            (self.pages / routes.FEED_RELATIVE).read_text(encoding="utf-8")
        )
        self.assertEqual(
            [
                {"type": "WebSub", "url": hub}
                for hub in routes.WEBSUB_HUBS
            ],
            feed["hubs"],
        )
        self.assertEqual(
            {"en-US:alpha:primary", "en-US:beta:primary"},
            {item["id"] for item in feed["items"]},
        )

        graph = close_sitemap_graph.close_graph(self.pages)
        self.assertGreater(graph["hub_changes"], 0)
        closure = routes.verify_production_closure(
            self.pages,
            strict_release=False,
        )
        self.assertEqual(2, closure["routes"])
        alpha_page = (
            self.pages / routes.route_relative(records[0])
        ).read_text(encoding="utf-8")
        self.assertEqual(
            "geo_ask",
            routes.gen_store_attribution.campaign_token(
                routes.route_relative(records[0]).as_posix(),
                alpha_page,
            ),
        )
        with mock.patch.dict(
            os.environ,
            {
                routes.gen_store_attribution.PROVIDER_TOKEN_ENV:
                    TEST_PROVIDER_TOKEN
            },
        ), mock.patch(
            "live_app_guard.live_apps",
            return_value={"fixture": "1234567890"},
        ):
            stamped = routes.gen_store_attribution.generate(
                self.pages,
                check=True,
            )
        self.assertEqual(0, stamped["pages_changed"])

    def test_closure_rejects_generated_digest_and_app_id_drift(self):
        record = self.record("alpha")
        (self.pages / "sitemap_index.xml").write_text(
            (
                '<?xml version="1.0"?><sitemapindex '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<sitemap><loc>{routes.SITE}/"
                f"{routes.SITEMAP_RELATIVE.as_posix()}</loc></sitemap>"
                "</sitemapindex>"
            ),
            encoding="utf-8",
        )
        routes.write_outputs([record], self.report(1), self.pages)
        page = self.pages / routes.route_relative(record)
        page.write_text(
            page.read_text(encoding="utf-8").replace(
                "id1234567890",
                "id9999999999",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "output digest drift"):
            routes.verify_production_closure(
                self.pages,
                strict_release=False,
            )
        self._assert_public_closure_rejects_unsafe_output_contracts_before_io()
        self._assert_public_closure_rejects_resolved_output_escape_before_io()

    def test_strict_release_rejects_nonproduction_cardinality(self):
        record = self.record("alpha")
        routes.write_outputs([record], self.report(1), self.pages)
        with self.assertRaisesRegex(ValueError, "versioned route source"):
            routes.verify_production_closure(
                self.pages,
                strict_release=True,
                expected_manifest=json.loads(
                    (self.pages / routes.MANIFEST_RELATIVE).read_text(
                        encoding="utf-8"
                    )
                ),
            )

    def test_only_prior_manifest_owned_stale_route_is_removed(self):
        alpha = self.record("alpha")
        beta = self.record("beta", intent="alternative")
        routes.write_outputs([alpha, beta], self.report(2), self.pages)
        beta_path = self.pages / routes.route_relative(beta)
        foreign = self.pages / "en-US" / "decide" / "foreign" / "keep.html"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("formal asset", encoding="utf-8")
        source = self.pages / "data" / "source.json"
        source.write_text("source", encoding="utf-8")

        stats = routes.write_outputs([alpha], self.report(1), self.pages)
        self.assertEqual(1, stats["stale_routes_removed"])
        self.assertFalse(beta_path.exists())
        self.assertTrue(foreign.exists())
        self.assertTrue(source.exists())

    def test_failed_generation_keeps_old_manifest_and_routes(self):
        alpha = self.record("alpha")
        beta = self.record("beta", intent="alternative")
        routes.write_outputs([alpha, beta], self.report(2), self.pages)
        manifest = (self.pages / routes.MANIFEST_RELATIVE).read_bytes()
        beta_path = self.pages / routes.route_relative(beta)
        broken = dict(alpha)
        broken.pop("query")
        with self.assertRaises(KeyError):
            routes.write_outputs([broken], self.report(1), self.pages)
        self.assertEqual(
            manifest,
            (self.pages / routes.MANIFEST_RELATIVE).read_bytes(),
        )
        self.assertTrue(beta_path.exists())


class HighIntentRouteInventoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory_path = current_guide_inventory_path()
        if not cls.inventory_path.is_file():
            raise AssertionError(
                f"Current Guide inventory mount is required: {cls.inventory_path}"
            )
        cls.apps = routes.load_inventory(cls.inventory_path)
        cls.source = routes.load_route_source(SOURCE_PATH)
        cls.release = routes.release_expectations(cls.source)
        cls.records, cls.report = routes.build(
            inventory_path=cls.inventory_path,
            source_path=SOURCE_PATH,
            provider_token=TEST_PROVIDER_TOKEN,
            allow_new_live_app_gaps=True,
        )

    @classmethod
    def write_guide_inventory(cls, root: Path) -> Path:
        return write_contracted_guide_inventory(root, cls.release["app_keys"])

    def exact_contracted_inventory(self, root: Path) -> Path:
        return self.write_guide_inventory(root)

    def expanded_contract_fixture(
        self,
        root: Path,
        *,
        extra_apps: int,
        include_route_copy: bool,
    ) -> tuple[Path, Path, list[str]]:
        inventory = json.loads(
            self.write_guide_inventory(root).read_text(encoding="utf-8")
        )
        source = deepcopy(self.source)
        new_keys: list[str] = []
        for offset in range(extra_apps):
            app_template = deepcopy(inventory["apps"][offset])
            route_template = deepcopy(source["routes"][offset])
            key = f"futurefixture{offset + 1}"
            app_id = str(9900000000 + offset)
            app_template.update(
                {
                    "key": key,
                    "name": f"Future Fixture {offset + 1}",
                    "app_store_id": app_id,
                    "canonical_app_store_url": (
                        f"https://apps.apple.com/app/id{app_id}"
                    ),
                    "verified_live": True,
                }
            )
            inventory["apps"].append(app_template)
            new_keys.append(key)
            if include_route_copy:
                route_template.pop("conversion_contract", None)
                route_template["app_key"] = key
                route_template["route_slug"] = (
                    f"future-fixture-workflow-{offset + 1}"
                )
                route_template["locales"] = {
                    "en-US": route_template["locales"]["en-US"]
                }
                copy = route_template["locales"]["en-US"]
                themes = (
                    (
                        "bird migration field survey",
                        "wetland transects, binocular observations, species "
                        "codes, weather notes, acoustic timestamps, and habitat "
                        "photographs",
                        "ornithology flyway plumage roosting banding warbler "
                        "shorebird estuary reedbed migration radar dawn chorus "
                        "nesting molt flock waypoint marsh ecology",
                    ),
                    (
                        "textile conservation intake",
                        "weave diagrams, dye samples, provenance cards, fiber "
                        "microscopy, humidity readings, and restoration ledgers",
                        "selvedge warp weft mordant loom brocade tapestry linen "
                        "silk pigment swatch embroidery patina spindle bobbin "
                        "crease abrasion gallery conservation",
                    ),
                    (
                        "community seed library rotation",
                        "germination batches, cultivar envelopes, lending "
                        "labels, harvest calendars, plot maps, and viability "
                        "checks",
                        "heirloom pollination seedling compost trellis orchard "
                        "legume tuber rhizome greenhouse allotment mulch frost "
                        "sowing threshing nursery biodiversity",
                    ),
                )
                workflow, vocabulary, distinctive_terms = themes[offset]
                copy.update(
                    {
                        "language": "en",
                        "market": "United States",
                        "culture_route": (
                            f"US teams coordinating a {workflow} often combine "
                            f"{vocabulary} across volunteers, specialists, and "
                            "offline locations where a deliberate handoff "
                            "matters more than instant collaboration. Domain "
                            f"signals include {distinctive_terms}."
                        ),
                        "query": (
                            f"How should I organize a {workflow} on iPhone "
                            f"without losing its review trail?"
                        ),
                        "buyer_problem": (
                            f"A {workflow} becomes unreliable when {vocabulary} "
                            "are separated from the person, place, and decision "
                            "that produced them. The purchase question is "
                            "whether one traceable offline workflow can reduce "
                            "reconstruction, ambiguity, and duplicate entry. "
                            f"Its specialist vocabulary includes "
                            f"{distinctive_terms}."
                        ),
                        "decision_rule": (
                            "Prefer a focused workspace when ownership, source "
                            "context, repeatable review, and offline continuity "
                            "are the binding constraints. Prefer a broad team "
                            "platform when simultaneous editing and enterprise "
                            "administration outweigh field simplicity."
                        ),
                        "workflow_checks": [
                            (
                                f"Can {vocabulary.split(',')[0]} remain linked "
                                "to the correct field session?"
                            ),
                            (
                                "Can a reviewer reconstruct who observed, "
                                "classified, and approved each item?"
                            ),
                            (
                                "Can the complete handoff remain usable when "
                                "connectivity is intermittent?"
                            ),
                        ],
                        "alternative_lens": (
                            "Compare a shared spreadsheet when rows and simple "
                            "status fields are sufficient. Compare a specialist "
                            "desktop archive when calibrated instruments, "
                            "institutional retention, or regulated custody "
                            "controls define the work."
                        ),
                        "verify_before_install": [
                            (
                                f"Run one small {workflow} from capture through "
                                "review before moving active records."
                            ),
                            (
                                "Confirm current export, backup, device, and "
                                "purchase terms on the App Store listing."
                            ),
                        ],
                    }
                )
                route_template["locales"]["en-US"] = copy
                source["routes"].append(route_template)
        inventory["record_count"] = len(inventory["apps"])
        app_keys_digest, copy_digest = routes._inventory_digests(
            inventory["apps"]
        )
        source["inventory_contract"].update(
            {
                "expected_app_count": len(inventory["apps"]),
                "app_keys_sha256": app_keys_digest,
                "copy_sha256": copy_digest,
            }
        )
        inventory_path = root / "inventory.json"
        source_path = root / "routes.json"
        inventory_path.write_text(
            json.dumps(inventory, ensure_ascii=False),
            encoding="utf-8",
        )
        source_path.write_text(
            json.dumps(source, ensure_ascii=False),
            encoding="utf-8",
        )
        return inventory_path, source_path, new_keys

    @staticmethod
    def write_sitemap_index(root: Path) -> None:
        (root / "sitemap_index.xml").write_text(
            (
                '<?xml version="1.0"?><sitemapindex '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<sitemap><loc>{routes.SITE}/"
                f"{routes.SITEMAP_RELATIVE.as_posix()}</loc></sitemap>"
                "</sitemapindex>"
            ),
            encoding="utf-8",
        )

    @staticmethod
    def copy_current_source(root: Path) -> Path:
        current_source = root / ".current-growth-source"
        for relative in routes.SYNC_ENGINE_FILES:
            target = current_source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(GEO / relative, target)
        contract_target = (
            current_source / "data" / routes.SYNC_CONTRACT_PATH.name
        )
        contract_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(routes.SYNC_CONTRACT_PATH, contract_target)
        return current_source

    def test_context_inventory_recomputes_the_reviewed_contract(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-gitlink-base-test-",
            dir=GEO / "tests",
        ) as scratch:
            inventory_path = self.write_guide_inventory(Path(scratch))
            apps = routes.load_inventory(inventory_path)
            expected_keys = set(self.release["app_keys"])
            contracted_apps = [apps[key] for key in self.release["app_keys"]]
            app_keys_sha256, copy_sha256 = routes._inventory_digests(
                contracted_apps
            )
            self.assertEqual(self.release["app_count"], len(apps))
            self.assertEqual(expected_keys, set(apps))
            self.assertEqual(len(expected_keys), self.release["app_count"])
            self.assertGreaterEqual(
                self.release["route_count"],
                self.release["app_count"],
            )
            self.assertEqual(
                app_keys_sha256,
                self.source["inventory_contract"]["app_keys_sha256"],
            )
            self.assertEqual(
                copy_sha256,
                self.source["inventory_contract"]["copy_sha256"],
            )
            self.assertEqual("HoursTag: Hours to Buy", apps["hourstag"]["name"])

            records, report = routes.build(
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
                allow_new_live_app_gaps=True,
            )
            self.assertEqual(self.release["route_count"], len(records))
            self.assertEqual([], report["coverage"]["missing_route_app_keys"])
            self.assertEqual(routes.RELEASE_STATE_EXACT, report["release_state"])

    def test_real_inventory_copy_drift_still_fails_closed(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-real-copy-drift-test-",
            dir=GEO / "tests",
        ) as scratch:
            root = Path(scratch)
            inventory_path = self.write_guide_inventory(root)
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            hourstag = next(
                app for app in inventory["apps"] if app["key"] == "hourstag"
            )
            hourstag["name"] = "HoursTag"
            inventory_path.write_text(
                json.dumps(inventory, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "inventory/copy drifted"):
                routes.build(
                    inventory_path=inventory_path,
                    source_path=SOURCE_PATH,
                    provider_token=TEST_PROVIDER_TOKEN,
                    allow_new_live_app_gaps=True,
                )

    def test_daily_publish_materializes_current_inventory_and_keeps_running(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-daily-materialization-test-",
            dir=GEO / "tests",
        ) as scratch:
            pages = Path(scratch)
            inventory_target = pages / "data" / routes.INVENTORY_FILENAME
            inventory_target.parent.mkdir(parents=True)
            shutil.copy2(self.inventory_path, inventory_target)
            self.write_sitemap_index(pages)
            commands: list[tuple[str, ...]] = []
            run_commands: list[tuple[str, ...]] = []

            def execute(command, cwd=None, env=None):
                commands.append(tuple(command))
                if command == ["git", "branch", "--show-current"]:
                    return "main\n"
                if command == ["git", "status", "--porcelain"]:
                    return " M data/current-generator-output.json\n"
                script = next(
                    (
                        Path(argument).name
                        for argument in command
                        if argument.endswith(".py")
                    ),
                    "",
                )
                if script != "high_intent_decision_routes.py":
                    return ""
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        (result.stdout + result.stderr)[-3000:]
                    )
                return result.stdout + result.stderr

            def fake_run(command, cwd=None, env=None):
                del cwd, env
                run_commands.append(tuple(command))
                return 0, ""

            with (
                mock.patch.object(geo_publish, "require", side_effect=execute),
                mock.patch.object(geo_publish, "run", side_effect=fake_run),
                mock.patch.object(geo_publish, "PAGES", str(pages)),
                mock.patch.object(sys, "argv", ["publish.py"]),
                mock.patch.dict(
                    os.environ,
                    {
                        "GEO_PAGES": str(pages),
                        "APP_STORE_PROVIDER_TOKEN": TEST_PROVIDER_TOKEN,
                    },
                ),
            ):
                geo_publish.main()

            scripts = [
                next(
                    (
                        Path(argument).name
                        for argument in command
                        if argument.endswith(".py")
                    ),
                    "",
                )
                for command in commands
            ]
            generated = scripts.index("high_intent_decision_routes.py")
            normalized = scripts.index("normalize_app_store_links.py")
            feed = scripts.index("gen_feed.py")
            closure = len(scripts) - 1 - scripts[::-1].index(
                "high_intent_decision_routes.py"
            )
            self.assertLess(generated, normalized)
            self.assertLess(normalized, feed)
            self.assertLess(feed, closure)
            self.assertIn(
                "--materialize-current-inventory",
                commands[generated],
            )
            self.assertIn(
                "--check-materialization-closure",
                commands[closure],
            )
            self.assertTrue(
                any("push" in command for command in run_commands),
                run_commands,
            )
            coverage = json.loads(
                (pages / routes.COVERAGE_RELATIVE).read_text(
                    encoding="utf-8"
                )
            )
            expected_gaps = sorted(
                set(self.apps) - set(self.release["app_keys"])
            )
            self.assertEqual(
                expected_gaps,
                coverage["coverage"]["missing_route_app_keys"],
            )
            self.assertEqual(
                bool(expected_gaps),
                not coverage["publication"]["deployment_eligible"],
            )

    def test_current_inventory_report_is_exact_or_explicitly_degraded(self):
        coverage = self.report["coverage"]
        self.assertEqual(self.release["app_count"], coverage["mapped_apps"])
        self.assertEqual(self.release["app_count"], coverage["primary_routes"])
        self.assertEqual(
            len(OFFICIAL_LOCALES),
            coverage["official_locales_considered"],
        )
        self.assertEqual(
            self.release["route_count"],
            coverage["native_locale_records"],
        )
        self.assertEqual(
            self.release["candidate_app_locale_pairs"],
            coverage["candidate_app_locale_pairs"],
        )
        self.assertEqual(
            self.release["abstained_pairs"],
            coverage["abstained_pairs"],
        )
        self.assertEqual(0, coverage["fallback_records"])
        self.assertEqual(
            {
                "missing_curated_native_copy":
                    self.release["abstained_pairs"]
            },
            coverage["abstention_reasons"],
        )
        expected_gaps = sorted(set(self.apps) - set(self.release["app_keys"]))
        self.assertEqual(expected_gaps, coverage["missing_route_app_keys"])
        self.assertTrue(self.report["quality"]["materialization_safe"])
        if expected_gaps:
            self.assertEqual(
                routes.RELEASE_STATE_INVENTORY_GAP,
                self.report["release_state"],
            )
            self.assertFalse(self.report["quality"]["all_gates_passed"])
            self.assertFalse(
                self.report["quality"]["gates"][
                    "current_inventory_coverage"
                ]["passed"]
            )
            self.assertLess(coverage["app_coverage_percent"], 100.0)
        else:
            self.assertEqual(
                routes.RELEASE_STATE_EXACT,
                self.report["release_state"],
            )
            self.assertEqual(100.0, coverage["app_coverage_percent"])
            self.assertTrue(self.report["quality"]["all_gates_passed"])
            self.assertTrue(
                all(
                    gate["passed"]
                    for gate in self.report["quality"]["gates"].values()
                )
            )

    def test_missing_native_locale_copy_abstains_instead_of_falling_back(self) -> None:
        expected_pairs = {
            (locale, route["app_key"])
            for route in self.source["routes"]
            for locale in route["locales"]
        }
        actual_pairs = {
            (record["locale"], record["app_key"])
            for record in self.records
        }
        self.assertEqual(expected_pairs, actual_pairs)
        for locale in routes.OFFICIAL_LOCALES:
            native_count = sum(
                locale in route["locales"] for route in self.source["routes"]
            )
            with self.subTest(locale=locale):
                self.assertEqual(
                    self.release["app_count"] - native_count,
                    self.report["locales"][locale]["abstained"],
                )
                self.assertEqual(native_count, self.report["locales"][locale]["emitted"])

    def test_product_evidence_resolves_only_from_inventory(self) -> None:
        for record in self.records:
            app = self.apps[record["app_key"]]
            with self.subTest(route_id=record["route_id"]):
                self.assertGreaterEqual(len(record["evidence"]), 3)
                for evidence in record["evidence"]:
                    reference = evidence["reference"]
                    if reference.startswith("summary."):
                        key = reference.split(".", 1)[1]
                        self.assertEqual(
                            app["summaries"][key],
                            evidence["source_value"],
                        )
                    elif reference.startswith("feature."):
                        index = int(reference.rsplit(".", 1)[1])
                        self.assertEqual(
                            app["features"][index],
                            evidence["source_value"],
                        )
                    elif reference == "fact.purchase_model":
                        self.assertEqual(
                            app["purchase_model"],
                            evidence["source_value"],
                        )
                    elif reference == "fact.one_time_option":
                        self.assertIs(app["one_time_option"], True)
                        self.assertIs(evidence["source_value"], True)
                    elif reference.startswith("capability."):
                        capability = reference.split(".", 1)[1]
                        self.assertIs(app["capabilities"][capability], True)
                        self.assertIs(evidence["source_value"], True)
                    else:
                        self.fail(f"Unrecognized evidence reference: {reference}")

    def test_every_direct_cta_has_legal_pt_ct_mt_order(self) -> None:
        tokens: set[str] = set()
        for record in self.records:
            with self.subTest(route_id=record["route_id"]):
                parsed = urlsplit(record["app_store_url"])
                parameters = parse_qsl(parsed.query)
                self.assertEqual(["pt", "ct", "mt"], [key for key, _ in parameters])
                values = dict(parameters)
                self.assertEqual(TEST_PROVIDER_TOKEN, values["pt"])
                self.assertEqual("8", values["mt"])
                self.assertRegex(
                    values["ct"],
                    routes.app_store_storefronts.CAMPAIGN_TOKEN_RE,
                )
                tokens.add(values["ct"])
                self.assertEqual(
                    routes.campaign_token(record["intent_type"]),
                    values["ct"],
                )
                self.assertLessEqual(len(values["ct"]), 30)
                self.assertFalse(values["ct"].startswith("iag_h2_"))
                self.assertEqual("apps.apple.com", parsed.netloc)
                self.assertIn(f"id{record['app_store_id']}", parsed.path)
        self.assertLessEqual(tokens, {"geo_ask", "geo_pick", "geo_learn"})

    def test_disclosure_truthfully_identifies_the_developer(self) -> None:
        for record in self.records:
            with self.subTest(route_id=record["route_id"]):
                self.assertEqual("Lumi Studio", record["publisher"])
                self.assertEqual(
                    "app_developer",
                    record["publisher_relationship"],
                )
                self.assertFalse(record["is_independent_review"])
                self.assertIn("Lumi Studio", record["publisher_disclosure"])
        zh_records = [
            record for record in self.records if record["locale"] == "zh-Hant"
        ]
        self.assertEqual(
            sum("zh-Hant" in route["locales"] for route in self.source["routes"]),
            len(zh_records),
        )
        self.assertTrue(
            all("開發者" in record["publisher_disclosure"] for record in zh_records)
        )

    def test_localized_feature_evidence_never_falls_back_to_english(self) -> None:
        for locale, ui in routes.UI.items():
            if locale != "en-US":
                for label in ui["feature_labels"].values():
                    with self.subTest(locale=locale, label=label):
                        routes._validate_native_text(locale, label)
        localized_features = [
            (record["locale"], evidence)
            for record in self.records
            if record["locale"] != "en-US"
            for evidence in record["evidence"]
            if evidence["reference"].startswith("feature.")
        ]
        self.assertEqual(
            sum(
                ref.startswith("feature.")
                for route in self.source["routes"]
                for locale, copy in route["locales"].items()
                if locale != "en-US"
                for ref in copy["evidence_refs"]
            ),
            len(localized_features),
        )
        for locale, evidence in localized_features:
            self.assertNotEqual(
                str(evidence["source_value"]).casefold(),
                str(evidence["text"]).casefold(),
            )
            routes._validate_native_text(locale, evidence["text"])
        for record in self.records:
            for evidence in record["evidence"]:
                with self.subTest(route=record["route_id"], reference=evidence["reference"]):
                    routes._validate_native_text(record["locale"], evidence["text"])

    def test_native_text_validator_rejects_english_fallback(self) -> None:
        native = {
            "en-US": "Free to start",
            "zh-Hant": "可免費開始使用",
            "ja": "無料で始められます",
            "fr-FR": "Vous pouvez commencer gratuitement",
        }
        for locale, text in native.items():
            with self.subTest(locale=locale):
                routes._validate_native_text(locale, text)
                if locale != "en-US":
                    with self.assertRaisesRegex(ValueError, "not substantively native"):
                        routes._validate_native_text(locale, "Start with free access")

    def test_english_feature_labels_fail_closed_in_source_validator(self) -> None:
        fallbacks = {
            "Free to start": "Start with free access",
            "One-time unlock": "Unlock with a single payment",
            "No subscription": "No recurring payment plan",
        }
        for locale in ("zh-Hant", "ja", "fr-FR"):
            for label, fallback in fallbacks.items():
                with self.subTest(locale=locale, label=label):
                    with mock.patch.dict(routes.UI[locale]["feature_labels"], {label: fallback}):
                        with self.assertRaisesRegex(ValueError, "not substantively native"):
                            routes._validate_source_binding(
                                self.source, self.apps, allow_new_live_apps=True,
                            )

    def test_localized_evidence_english_fallback_fails_closed(self) -> None:
        fallback = "Start with free access"
        for locale, key in (("zh-Hant", "lumibopomofo"), ("ja", "lumiweather"), ("fr-FR", "aim990")):
            app = deepcopy(self.apps[key])
            summary = routes.LOCALE_LANGUAGE[locale]
            app["summaries"][summary] = "A useful published description of the app."
            with self.subTest(locale=locale, reference="summary"):
                with self.assertRaisesRegex(ValueError, "not substantively native"):
                    routes._evidence(app, locale, f"summary.{summary}")
            feature = len(app["features"])
            app["features"].append("Free to start")
            app["capabilities"]["offline"] = True
            mutations = (
                (f"feature.{feature}", routes.UI[locale]["feature_labels"], app["features"][feature]),
                ("fact.purchase_model", routes.UI[locale]["purchase_model"], app["purchase_model"]),
                ("fact.one_time_option", routes.UI[locale], "one_time_option"),
                ("capability.offline", routes.UI[locale]["capabilities"], "offline"),
            )
            for reference, labels, label in mutations:
                with self.subTest(locale=locale, reference=reference):
                    with mock.patch.dict(labels, {label: fallback}):
                        with self.assertRaisesRegex(ValueError, "not substantively native"):
                            routes._evidence(app, locale, reference)

    def test_routes_are_substantive_and_editorially_distinct(self) -> None:
        self.assertGreaterEqual(
            self.report["quality"]["minimum_content_units"],
            routes.MIN_CONTENT_UNITS,
        )
        self.assertLessEqual(
            self.report["quality"]["maximum_editorial_jaccard"],
            routes.MAX_EDITORIAL_JACCARD,
        )
        self.assertEqual(
            len(self.records),
            len({record["query"] for record in self.records}),
        )
        for record in self.records:
            self.assertEqual(3, len(record["workflow_checks"]))
            self.assertEqual(2, len(record["verify_before_install"]))
            self.assertGreaterEqual(record["content_units"], 180)

    def test_rendered_page_keeps_evidence_disclosure_and_direct_cta(self) -> None:
        record = next(
            candidate
            for candidate in self.records
            if candidate["app_key"] == "maskmyfile"
        )
        rendered = routes.render_html(record)
        self.assertIn('data-publisher-disclosure="true"', rendered)
        self.assertIn(record["publisher_disclosure"], rendered)
        self.assertIn(record["app_store_url"].replace("&", "&amp;"), rendered)
        self.assertIn(
            '"publisher":{"@type":"Organization","name":"Lumi Studio"',
            rendered,
        )
        for evidence in record["evidence"]:
            self.assertIn(evidence["text"], rendered)
            self.assertIn(evidence["inventory_pointer"], rendered)

    def test_inventory_copy_drift_and_bad_refs_fail_closed(self) -> None:
        changed_apps = deepcopy(self.apps)
        changed_apps["maskmyfile"]["features"][0] = "Invented claim"
        with self.assertRaisesRegex(ValueError, "inventory/copy drifted"):
            routes.validate_inventory_binding(self.source, changed_apps)

        changed_source = deepcopy(self.source)
        target = next(
            route
            for route in changed_source["routes"]
            if route["app_key"] == "maskmyfile"
        )
        target["locales"]["en-US"]["evidence_refs"][0] = "feature.99"
        validated, _, _ = routes._validate_source_binding(
            changed_source,
            self.apps,
            allow_new_live_apps=True,
        )
        with self.assertRaisesRegex(ValueError, "missing feature.99"):
            routes._build_record(
                self.apps["maskmyfile"],
                validated["maskmyfile"],
                "en-US",
                TEST_PROVIDER_TOKEN,
                self.source["publisher"]["disclosures"]["en-US"],
            )

    def test_empty_provider_token_fails_closed(self) -> None:
        app = self.apps["maskmyfile"]
        with self.assertRaisesRegex(ValueError, "provider token is required"):
            routes._campaign_url(app, "en-US", "problem_aware", "")

    def test_next_app_materializes_explicit_gap_but_pages_gate_fails(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-next-app-test-",
            dir=GEO / "tests",
        ) as scratch:
            root = Path(scratch)
            inventory_path = self.write_guide_inventory(root)
            inventory = json.loads(
                inventory_path.read_text(encoding="utf-8")
            )
            future_app = deepcopy(inventory["apps"][0])
            future_app.update(
                {
                    "key": "futureapp",
                    "name": "Future App",
                    "app_store_id": "6999999999",
                    "canonical_app_store_url": (
                        "https://apps.apple.com/app/id6999999999"
                    ),
                }
            )
            inventory["apps"].append(future_app)
            inventory["record_count"] = len(inventory["apps"])
            inventory_path.write_text(
                json.dumps(inventory, ensure_ascii=False),
                encoding="utf-8",
            )
            new_keys = ["futureapp"]
            records, report = routes.build(
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
                allow_new_live_app_gaps=True,
            )
            self.assertEqual(
                self.release["route_count"],
                len(records),
            )
            self.assertEqual(
                routes.RELEASE_STATE_INVENTORY_GAP,
                report["release_state"],
            )
            self.assertEqual(new_keys, report["coverage"]["missing_route_app_keys"])
            other_surface = root / "other-generator-surface.json"
            other_surface.write_text('{"status":"ok"}\n', encoding="utf-8")
            routes.write_outputs(records, report, root)
            self.write_sitemap_index(root)
            closure = routes.verify_materialization_closure(
                root,
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
            )
            self.assertFalse(closure["deployment_eligible"])
            self.assertEqual(new_keys, closure["missing_route_app_keys"])
            self.assertEqual('{"status":"ok"}\n', other_surface.read_text())

            current_source = self.copy_current_source(root)
            with self.assertRaisesRegex(
                ValueError,
                "needs reviewed native route copy",
            ):
                routes.prepare_pages_deployment(
                    root,
                    inventory_path=inventory_path,
                    source_path=SOURCE_PATH,
                    provider_token=TEST_PROVIDER_TOKEN,
                    source_commit="1" * 40,
                    current_source_root=current_source,
                    engine_source_revision="2" * 40,
                )
            self.assertFalse((root / routes.DEPLOYMENT_RELATIVE).exists())

    def test_contracted_inventory_passes_strict_pages_closure(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-gitlink-exact-test-",
            dir=GEO / "tests",
        ) as scratch:
            root = Path(scratch)
            inventory_path = self.write_guide_inventory(root)
            records, report = routes.build(
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
                allow_new_live_app_gaps=True,
            )
            routes.write_outputs(records, report, root)
            self.write_sitemap_index(root)
            materialization = routes.verify_materialization_closure(
                root,
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
            )
            self.assertEqual(0, materialization["missing_route_apps"])
            self.assertTrue(materialization["deployment_eligible"])
            closure = routes.verify_production_closure(
                root,
                strict_release=True,
                expected_manifest=json.loads(
                    (root / routes.MANIFEST_RELATIVE).read_text(
                        encoding="utf-8"
                    )
                ),
                source_path=SOURCE_PATH,
            )
            self.assertEqual(self.release["route_count"], closure["routes"])

    def test_expanded_route_source_derives_dynamic_exact_release(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-expanded-app-test-",
            dir=GEO / "tests",
        ) as scratch:
            root = Path(scratch)
            inventory_path, source_path, _ = self.expanded_contract_fixture(
                root,
                extra_apps=3,
                include_route_copy=True,
            )
            records, report = routes.build(
                inventory_path=inventory_path,
                source_path=source_path,
                provider_token=TEST_PROVIDER_TOKEN,
            )
            release = routes.release_expectations(
                routes.load_route_source(source_path)
            )
            self.assertEqual(self.release["app_count"] + 3, release["app_count"])
            self.assertEqual(release["route_count"], len(records))
            self.assertEqual(
                release["candidate_app_locale_pairs"],
                release["app_count"] * len(OFFICIAL_LOCALES),
            )
            self.assertEqual(
                release["abstained_pairs"],
                release["candidate_app_locale_pairs"]
                - release["route_count"],
            )
            self.assertEqual(routes.RELEASE_STATE_EXACT, report["release_state"])
            routes.write_outputs(records, report, root)
            self.write_sitemap_index(root)
            manifest = json.loads(
                (root / routes.MANIFEST_RELATIVE).read_text(encoding="utf-8")
            )
            closure = routes.verify_production_closure(
                root,
                strict_release=True,
                expected_manifest=manifest,
                source_path=source_path,
            )
            self.assertEqual(release["route_count"], closure["routes"])

    def test_preupload_gate_regenerates_drift_and_writes_bound_deployment(self):
        with tempfile.TemporaryDirectory(
            prefix=".high-intent-preupload-test-",
            dir=GEO / "tests",
        ) as scratch:
            pages = Path(scratch)
            inventory_path = self.exact_contracted_inventory(pages)
            current_source = pages / ".current-growth-source"
            for relative in routes.SYNC_ENGINE_FILES:
                target = current_source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(GEO / relative, target)
            contract_target = (
                current_source
                / "data"
                / routes.SYNC_CONTRACT_PATH.name
            )
            contract_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(routes.SYNC_CONTRACT_PATH, contract_target)
            (pages / "sitemap_index.xml").write_text(
                (
                    '<?xml version="1.0"?><sitemapindex '
                    'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f"<sitemap><loc>{routes.SITE}/"
                    f"{routes.SITEMAP_RELATIVE.as_posix()}</loc></sitemap>"
                    "</sitemapindex>"
                ),
                encoding="utf-8",
            )
            first = routes.prepare_pages_deployment(
                pages,
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
                source_commit="1" * 40,
                current_source_root=current_source,
                engine_source_revision="2" * 40,
            )
            self.assertEqual(self.release["route_count"], first["routes"])
            manifest = json.loads(
                (pages / routes.MANIFEST_RELATIVE).read_text(encoding="utf-8")
            )
            self.assertEqual(self.release["route_count"], manifest["route_count"])
            self.assertEqual(self.release["app_count"], manifest["app_count"])
            self.assertEqual(
                self.release["creative_count"],
                manifest["creative_count"],
            )
            self.assertEqual(
                self.release["candidate_app_locale_pairs"],
                manifest["candidate_app_locale_pairs"],
            )
            self.assertEqual(
                self.release["abstained_pairs"],
                manifest["abstained_pairs"],
            )
            self.assertEqual(0, manifest["fallback_records"])
            self.assertEqual(
                self.release["managed_output_count"],
                len(manifest["expected_outputs"]),
            )
            self.assertTrue(
                all(
                    route["app_store_url"].endswith("mt=8")
                    and "?pt=" in route["app_store_url"]
                    and "&ct=" in route["app_store_url"]
                    and route["output_sha256"]
                    for route in manifest["routes"]
                )
            )
            target = pages / manifest["routes"][0]["relative_path"]
            expected = target.read_bytes()
            target.write_text("drift", encoding="utf-8")
            second = routes.prepare_pages_deployment(
                pages,
                inventory_path=inventory_path,
                source_path=SOURCE_PATH,
                provider_token=TEST_PROVIDER_TOKEN,
                source_commit="1" * 40,
                current_source_root=current_source,
                engine_source_revision="2" * 40,
            )
            self.assertTrue(second["regenerated_for_source_drift"])
            self.assertEqual(expected, target.read_bytes())
            deployment = json.loads(
                (pages / routes.DEPLOYMENT_RELATIVE).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                self.release["route_count"],
                deployment["route_count"],
            )
            self.assertEqual(
                self.release["app_count"],
                deployment["app_count"],
            )
            self.assertEqual(
                self.release["candidate_app_locale_pairs"],
                deployment["candidate_app_locale_pairs"],
            )
            self.assertEqual(
                self.release["abstained_pairs"],
                deployment["abstained_pairs"],
            )
            self.assertEqual(0, deployment["fallback_records"])
            self.assertEqual(
                routes.DEPLOYMENT_SCHEMA_VERSION,
                deployment["version"],
            )
            self.assertEqual(
                routes.deployment_identity(manifest["manifest_digest"]),
                deployment["deployment_id"],
            )
            self.assertEqual("2" * 40, deployment["engine_source_revision"])
            self.assertEqual(
                manifest["source_contract_digest"],
                deployment["source_contract_digest"],
            )
            self.assertEqual(
                manifest["manifest_digest"],
                deployment["route_manifest_digest"],
            )


if __name__ == "__main__":
    unittest.main()
