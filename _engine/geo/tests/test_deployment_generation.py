#!/usr/bin/env python3
"""Deterministic, offline regressions for deployment generation boundaries."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from http.client import IncompleteRead
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))
import deployment_generation as generation


NOW = datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)
SITES = ["https://origin.example.test/guide", "https://public.example.test/guide"]


def _write(root: Path, relative: str, body: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Generation Test",
         "-c", "user.email=generation@example.test", *args],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "固定測試來源")


class DeploymentGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(
            prefix=".generation-test-", dir=Path(__file__).parent,
        )
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source, self.site = self.root / "source", self.root / "guide"
        for root in (self.source, self.site):
            root.mkdir()
            _git(root, "init", "--quiet")
        for name, body in {
            "deployment_generation.py": b"# generation verifier\n",
            "high_intent_decision_routes.py": b"# route generator\n",
            "requirements-validation.txt": b"example==1.0\n",
            "data/routes.json": b'{"routes": ["one"]}\n',
        }.items():
            _write(self.source, f"geo/{name}", body)
            _write(self.site, f"_engine/geo/{name}", body)
        _write(self.source, "README.md", b"Canonical source\n")
        _write(self.site, ".github/workflows/pages.yml", b"name: Pages\n")
        _write(self.site, "_engine/geo/i18n_trans/en-US.json", b'{"cache": 1}\n')
        _commit(self.source)
        _commit(self.site)
        self.identity = self.build_identity()
        self.bodies = {
            "en-US/decide/test/route.html": b"<!doctype html><p>route</p>\n",
            "data/high-intent-decision-routes/feed.json": b'{"items": []}\n',
        }
        for path, body in self.bodies.items():
            _write(self.site, path, body)
        self.manifest = {
            "expected_outputs": [
                {"kind": "test", "relative_path": path,
                 "generated_sha256": hashlib.sha256(body).hexdigest()}
                for path, body in sorted(self.bodies.items())
            ],
        }
        self.manifest["manifest_digest"] = generation.digest(self.manifest)
        _write(self.site, generation.MANIFEST_PATH,
               json.dumps(self.manifest, sort_keys=True).encode())
        _write(self.site, generation.CATALOG_PATH, b'{"apps": ["test"]}\n')
        self.outputs = generation.output_identity(self.site)
        self.proof = generation.seal_generation(self.identity, self.outputs)
        self.deployment = {
            "version": 4, "deployment_id": "legacy-route-identity",
            "generated_at": "2026-09-05T06:00:00Z",
            "source_commit": self.identity["pages_source_sha"],
            "engine_source_revision": self.identity["source_sha"],
            "route_manifest_digest": self.manifest["manifest_digest"],
            "generation": self.proof,
        }
        _write(self.site, generation.DEPLOYMENT_PATH,
               json.dumps(self.deployment, sort_keys=True).encode())
        for relative in (generation.DEPLOYMENT_PATH, generation.MANIFEST_PATH,
                         generation.CATALOG_PATH):
            self.bodies[relative] = (self.site / relative).read_bytes()
        self.calls: list[str] = []

    def build_identity(self, *, run_id="123456", attempt="1"):
        return generation.build_identity(
            self.source, self.site, run_id=run_id, run_attempt=attempt,
            settings={"GEO_SITE": SITES[1]},
        )

    def fetch(self, url, *, timeout, maximum):
        self.assertEqual(timeout, 20)
        self.assertEqual(maximum, generation.MAX_BYTES)
        self.calls.append(url)
        relative = urlsplit(url).path.removeprefix("/guide/")
        return self.bodies[relative], url, 200

    def readback(self, **kwargs):
        return generation.live_readback(
            self.deployment, sites=SITES, now=NOW,
            fetch=kwargs.pop("fetch", self.fetch),
            source_root=self.source, **kwargs,
        )

    def test_generation_is_deterministic_and_keeps_legacy_aliases(self):
        self.assertEqual(self.identity, self.build_identity())
        self.assertEqual(self.proof, generation.seal_generation(self.identity, self.outputs))
        self.assertEqual(self.proof, generation.validate_binding(self.deployment))
        self.assertEqual(4, self.deployment["version"])

    def test_every_run_and_attempt_has_a_distinct_generation(self):
        for identity in (
            self.build_identity(run_id="next-run"),
            self.build_identity(attempt="2"),
        ):
            with self.subTest(identity=identity["run_id"]):
                proof = generation.seal_generation(identity, self.outputs)
                self.assertNotEqual(self.proof["generation_id"], proof["generation_id"])
                self.assertEqual(self.proof["manifest_digest"], proof["manifest_digest"])

    def test_uncommitted_modified_added_and_deleted_sources_invalidate(self):
        target = self.source / "geo/high_intent_decision_routes.py"
        original = target.read_bytes()
        for action in ("modify", "delete", "add"):
            with self.subTest(action=action):
                extra = self.source / "geo/new_generator.py"
                try:
                    if action == "modify":
                        target.write_bytes(b"# changed\n")
                    elif action == "delete":
                        target.unlink()
                    else:
                        extra.write_bytes(b"# untracked\n")
                    with self.assertRaisesRegex(generation.GenerationError, "dirty"):
                        generation.validate_current_source(self.proof, self.source)
                finally:
                    target.write_bytes(original)
                    extra.unlink(missing_ok=True)

    def test_even_an_unrelated_source_commit_invalidates_old_evidence(self):
        (self.source / "README.md").write_bytes(b"New source commit\n")
        _commit(self.source)
        with self.assertRaisesRegex(generation.GenerationError, "source changed"):
            generation.validate_current_source(self.proof, self.source)

    def test_generator_and_dependency_digests_follow_exact_bytes(self):
        _write(self.source, "geo/high_intent_decision_routes.py", b"# new generator\n")
        _write(self.source, "geo/requirements-validation.txt", b"example==2.0\n")
        _commit(self.source)
        current = generation.source_identity(self.source)
        for key in ("source_sha", "source_tree", "generator_digest", "dependency_lock_digest"):
            self.assertNotEqual(self.proof[key], current[key], key)

    def test_mirror_drift_is_not_hidden_by_its_own_committed_hash(self):
        _write(self.site, "_engine/geo/high_intent_decision_routes.py", b"# stale mirror\n")
        _commit(self.site)
        with self.assertRaisesRegex(generation.GenerationError, "mirror drift"):
            self.build_identity()

    def test_dirty_mirror_and_workflow_are_not_accepted(self):
        for relative in ("_engine/geo/high_intent_decision_routes.py",
                         ".github/workflows/pages.yml"):
            with self.subTest(path=relative):
                original = (self.site / relative).read_bytes()
                try:
                    _write(self.site, relative, b"dirty\n")
                    with self.assertRaisesRegex(generation.GenerationError, "committed source"):
                        self.build_identity()
                finally:
                    _write(self.site, relative, original)

    def test_runtime_cache_is_bound_without_pretending_to_be_a_source_mirror(self):
        _write(self.site, "_engine/geo/i18n_trans/en-US.json", b'{"cache": 2}\n')
        _commit(self.site)
        current = self.build_identity()
        self.assertEqual(self.identity["mirror_digest"], current["mirror_digest"])
        self.assertNotEqual(self.identity["mirror_inputs_digest"], current["mirror_inputs_digest"])
        self.assertNotEqual(self.identity["build_config_digest"], current["build_config_digest"])

    def test_configuration_changes_invalidate_generation(self):
        _write(self.site, ".github/workflows/pages.yml", b"name: New Pages\n")
        _commit(self.site)
        current = self.build_identity()
        self.assertNotEqual(self.identity["build_config_digest"], current["build_config_digest"])
        self.assertNotEqual(self.identity["pages_source_sha"], current["pages_source_sha"])

    def test_resolved_dependencies_cannot_change_behind_an_unchanged_lock(self):
        with mock.patch.object(generation, "dependency_environment_digest",
                               return_value="f" * 64):
            current = self.build_identity()
        self.assertEqual(self.identity["dependency_lock_digest"], current["dependency_lock_digest"])
        self.assertNotEqual(
            self.identity["dependency_environment_digest"],
            current["dependency_environment_digest"],
        )

    def test_prepare_wraps_the_legacy_generator_and_seals_only_after_rechecking(self):
        import high_intent_decision_routes as routes
        legacy = {key: value for key, value in self.deployment.items() if key != "generation"}
        def generate(*args, **kwargs):
            _write(self.site, generation.DEPLOYMENT_PATH, json.dumps(legacy).encode())
        with mock.patch.object(routes, "prepare_pages_deployment", side_effect=generate):
            sealed = generation.prepare(
                source_root=self.source, site_root=self.site,
                inventory=self.site / generation.CATALOG_PATH,
                source_commit=self.identity["pages_source_sha"],
                engine_source_revision=self.identity["source_sha"],
                run_id="wrapper-test", run_attempt="1",
            )
        self.assertEqual(4, sealed["version"])
        self.assertEqual("wrapper-test", generation.validate_binding(sealed)["run_id"])
        self.assertEqual(
            sealed, generation.parse_json((self.site / generation.DEPLOYMENT_PATH).read_bytes()),
        )

    def test_prepare_never_seals_a_source_changed_during_generation(self):
        import high_intent_decision_routes as routes
        def generate(*args, **kwargs):
            (self.source / "README.md").write_bytes(b"changed while building")
        with mock.patch.object(routes, "prepare_pages_deployment", side_effect=generate):
            with self.assertRaisesRegex(generation.GenerationError, "dirty"):
                generation.prepare(
                    source_root=self.source, site_root=self.site,
                    inventory=self.site / generation.CATALOG_PATH,
                    source_commit=self.identity["pages_source_sha"],
                    engine_source_revision=self.identity["source_sha"],
                    run_id="wrapper-test", run_attempt="1",
                )

    def test_seal_rejects_missing_and_malformed_provenance(self):
        for key in sorted(generation.GENERATION_FIELDS):
            with self.subTest(key=key):
                value = deepcopy(self.proof)
                value.pop(key)
                with self.assertRaises(generation.GenerationError):
                    generation.validate_generation(value)
        for key in sorted(generation.DIGEST_FIELDS):
            with self.subTest(key=key):
                value = {**self.proof, key: "not-a-digest"}
                with self.assertRaises(generation.GenerationError):
                    generation.validate_generation(value)

    def test_legacy_deployment_is_readable_but_never_verified(self):
        legacy = {key: value for key, value in self.deployment.items() if key != "generation"}
        self.assertEqual(legacy, generation.parse_json(json.dumps(legacy).encode()))
        with self.assertRaisesRegex(generation.GenerationError, "generation"):
            generation.validate_binding(legacy)

    def test_source_and_manifest_alias_splicing_is_rejected(self):
        for key in ("source_commit", "engine_source_revision", "route_manifest_digest"):
            with self.subTest(key=key):
                value = {**self.deployment, key: "f" * (64 if key.endswith("digest") else 40)}
                with self.assertRaisesRegex(generation.GenerationError, "aliases"):
                    generation.validate_binding(value)

    def test_output_bytes_must_match_the_manifest_before_sealing(self):
        _write(self.site, "en-US/decide/test/route.html", b"stale output")
        with self.assertRaisesRegex(generation.GenerationError, "output bytes"):
            generation.output_identity(self.site)

    def test_manifest_rejects_traversal_duplicates_and_symlinks(self):
        for path in ("../escape", "/absolute", "a/../escape", "a\\escape"):
            with self.subTest(path=path):
                document = deepcopy(self.manifest)
                document["expected_outputs"][0]["relative_path"] = path
                document["manifest_digest"] = generation.digest({
                    key: value for key, value in document.items() if key != "manifest_digest"
                })
                with self.assertRaisesRegex(generation.GenerationError, "unsafe"):
                    generation.manifest_outputs(document)
        document = deepcopy(self.manifest)
        document["expected_outputs"].append(document["expected_outputs"][0])
        document["manifest_digest"] = generation.digest({
            key: value for key, value in document.items() if key != "manifest_digest"
        })
        with self.assertRaisesRegex(generation.GenerationError, "duplicate"):
            generation.manifest_outputs(document)
        path = self.site / "en-US/decide/test/route.html"
        path.unlink()
        path.symlink_to(self.source / "README.md")
        with self.assertRaisesRegex(generation.GenerationError, "symlink"):
            generation.output_identity(self.site)

    def test_exact_gets_cover_both_hosts_all_outputs_and_catalog(self):
        receipt = self.readback()
        self.assertEqual("verified", receipt["status"])
        self.assertEqual(self.proof, generation.validate_receipt(
            receipt, self.deployment, source_root=self.source,
        ))
        self.assertEqual(2, len(receipt["observations"]))
        self.assertTrue(all(len(row["checks"]) == 3 for row in receipt["observations"]))
        self.assertTrue(all("generation=" in url for url in self.calls))

    def test_http_errors_and_redirects_never_count_as_live(self):
        for status, final in ((503, None), (304, None), (200, "https://other.example.test/")):
            with self.subTest(status=status, final=final):
                def fetch(url, **kwargs):
                    body, _, _ = self.fetch(url, **kwargs)
                    return body, final or url, status
                with self.assertRaisesRegex(generation.GenerationError, "endpoint drift"):
                    self.readback(fetch=fetch)

    def test_mixed_live_manifest_output_and_catalog_are_rejected(self):
        for relative in (generation.MANIFEST_PATH, generation.CATALOG_PATH,
                         "en-US/decide/test/route.html"):
            with self.subTest(path=relative):
                original = self.bodies[relative]
                try:
                    self.bodies[relative] = b"stale generation"
                    with self.assertRaises(generation.GenerationError):
                        self.readback()
                finally:
                    self.bodies[relative] = original

    def test_manifest_rolling_over_during_gets_is_rejected(self):
        calls = 0
        def fetch(url, **kwargs):
            nonlocal calls
            body, final, status = self.fetch(url, **kwargs)
            if generation.MANIFEST_PATH in url:
                calls += 1
                if calls > 1:
                    body += b"\n"
            return body, final, status
        with self.assertRaisesRegex(generation.GenerationError, "rolled over"):
            self.readback(fetch=fetch)

    def test_rollover_between_origin_and_public_host_is_rejected(self):
        def fetch(url, **kwargs):
            body, final, status = self.fetch(url, **kwargs)
            if ("origin.example.test" in url and generation.DEPLOYMENT_PATH in url
                    and "phase=final" in url):
                document = deepcopy(self.deployment)
                document["generated_at"] = "2026-09-05T06:01:00Z"
                body = json.dumps(document).encode()
            return body, final, status
        with self.assertRaisesRegex(generation.GenerationError, "between origins"):
            self.readback(fetch=fetch)

    def test_manifest_rollover_after_the_other_host_was_checked_is_rejected(self):
        def fetch(url, **kwargs):
            body, final, status = self.fetch(url, **kwargs)
            if ("origin.example.test" in url and generation.MANIFEST_PATH in url
                    and "phase=final" in url):
                body += b"\n"
            return body, final, status
        with self.assertRaisesRegex(generation.GenerationError, "manifest rolled over between"):
            self.readback(fetch=fetch)

    def test_trailing_slash_does_not_turn_one_origin_into_two(self):
        with self.assertRaisesRegex(generation.GenerationError, "distinct endpoints"):
            generation.live_readback(
                self.deployment, sites=[SITES[0], SITES[0] + "/"],
                now=NOW, fetch=self.fetch,
            )
        self.assertEqual([], self.calls)

    def test_source_mutation_during_readback_invalidates_every_get(self):
        def fetch(url, **kwargs):
            result = self.fetch(url, **kwargs)
            if generation.CATALOG_PATH in url:
                (self.source / "README.md").write_bytes(b"changed during GET\n")
            return result
        with self.assertRaisesRegex(generation.GenerationError, "dirty"):
            self.readback(fetch=fetch)

    def test_receipt_cannot_mix_observations_from_another_generation(self):
        receipt = self.readback()
        receipt["observations"][1]["generation_id"] = "f" * 64
        receipt["receipt_digest"] = generation.digest({
            key: value for key, value in receipt.items() if key != "receipt_digest"
        })
        with self.assertRaisesRegex(generation.GenerationError, "mix generations"):
            generation.validate_receipt(receipt, self.deployment)

    def test_failure_replaces_stale_success_receipt_with_blocked(self):
        receipt_path = self.root / "receipt.json"
        generation.atomic_json(receipt_path, self.readback())
        with mock.patch.object(generation, "live_readback",
                               side_effect=generation.GenerationError("stale")):
            with self.assertRaises(SystemExit) as result:
                generation.main([
                    "verify-live", "--deployment", str(self.site / generation.DEPLOYMENT_PATH),
                    "--receipt", str(receipt_path), "--site", SITES[0],
                ])
        self.assertEqual(1, result.exception.code)
        self.assertEqual("blocked", generation.parse_json(receipt_path.read_bytes())["status"])
        self.assertEqual(0o600, receipt_path.stat().st_mode & 0o777)

    def test_transport_is_get_only_bounded_and_uncached(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"body"
        response.geturl.return_value = SITES[0]
        response.status = 200
        with mock.patch.object(generation, "urlopen", return_value=response) as open_url:
            self.assertEqual((b"body", SITES[0], 200),
                             generation.get_bytes(SITES[0], timeout=7, maximum=10))
        request = open_url.call_args.args[0]
        self.assertEqual("GET", request.method)
        self.assertIsNone(request.data)
        self.assertEqual("no-cache", request.get_header("Cache-control"))
        self.assertEqual(7, open_url.call_args.kwargs["timeout"])
        response.read.assert_called_once_with(11)

    def test_interrupted_http_body_invalidates_an_existing_success_receipt(self):
        receipt_path = self.root / "interrupted-receipt.json"
        generation.atomic_json(receipt_path, self.readback())
        with mock.patch.object(generation, "urlopen", side_effect=IncompleteRead(b"partial")):
            with self.assertRaises(SystemExit):
                generation.main([
                    "verify-live", "--deployment", str(self.site / generation.DEPLOYMENT_PATH),
                    "--receipt", str(receipt_path), "--site", SITES[0],
                ])
        self.assertEqual("blocked", generation.parse_json(receipt_path.read_bytes())["status"])

    def test_duplicate_json_keys_are_not_evidence(self):
        with self.assertRaisesRegex(generation.GenerationError, "duplicate"):
            generation.parse_json(b'{"generation_id": "a", "generation_id": "b"}')


class DeploymentWorkflowGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pages = GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages"
        cls.workflow = (pages / ".github/workflows/pages.yml").read_text(encoding="utf-8")

    def test_prepare_pins_both_sources_and_the_exact_workflow_attempt(self):
        prepare = self.workflow.index("deployment_generation.py prepare")
        upload = self.workflow.index("actions/upload-pages-artifact@")
        self.assertLess(prepare, upload)
        for field in ("--current-source-root", "--source-commit",
                      "--engine-source-revision", "--run-id", "--run-attempt"):
            self.assertIn(field, self.workflow[prepare:upload])

    def test_readback_is_exact_on_origin_and_public_host_and_keeps_the_receipt(self):
        self.assertIn('"$RUNNER_TEMP/deployment_generation.py" verify-live', self.workflow)
        self.assertIn('--site "${DEPLOYMENT_MANIFEST_URL%/.well-known/deployment.json}"', self.workflow)
        self.assertIn('--site "$GEO_SITE"', self.workflow)
        self.assertIn("deployment-readback-${{ github.run_id }}-${{ github.run_attempt }}", self.workflow)
        self.assertIn("steps.verify_live.outcome == 'success'", self.workflow)
        self.assertNotIn('fields=\'{version,deployment_id', self.workflow)

    def test_verifier_survives_pruning_but_is_not_uploaded_in_the_site(self):
        self.assertLess(
            self.workflow.index('cp _engine/geo/deployment_generation.py'),
            self.workflow.index('rm -rf _engine'),
        )


if __name__ == "__main__":
    unittest.main()
