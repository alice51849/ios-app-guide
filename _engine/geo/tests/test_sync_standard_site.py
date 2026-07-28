#!/usr/bin/env python3
"""Regression tests for fail-closed Standard.site Guide reconciliation."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
import uuid
from urllib.error import URLError


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import sync_standard_site as sync  # noqa: E402


PUBLICATION_URI = (
    "at://did:plc:kboucnzkxzmqmatvhes4xlt4/"
    "site.standard.publication/3mabcde234567"
)
DOCUMENT_URI = (
    "at://did:plc:kboucnzkxzmqmatvhes4xlt4/"
    "site.standard.document/3mabcdef23456"
)


class ProjectScratchCase(unittest.TestCase):
    def setUp(self) -> None:
        root = HERE / ".standard_site_sync_test_runs"
        root.mkdir(exist_ok=True)
        self.scratch = root / f"{self.__class__.__name__}-{uuid.uuid4().hex}"
        self.scratch.mkdir()
        self.site = self.scratch / "site"
        self.site.mkdir()
        self.state = self.site / "_engine/geo/standard_site_sync_state.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.scratch, ignore_errors=True)

    def write_html(self, relative: str, source: str) -> Path:
        path = self.site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def contract(
        self,
        documents: list[tuple[str, str, str]] | None = None,
        **publication_overrides: object,
    ) -> bytes:
        body = PUBLICATION_URI + "\n"
        publication: dict[str, object] = {
            "url": sync.PUBLICATION_URL,
            "at_uri": PUBLICATION_URI,
            "well_known": {
                "request_url": sync.WELL_KNOWN_URL,
                "request_path": sync.WELL_KNOWN_PATH,
                "content_type": "text/plain; charset=utf-8",
                "body": body,
                "sha256": hashlib.sha256(body.encode()).hexdigest(),
                "deploy_at_origin_root": True,
            },
            "discovery_link_tag": (
                f'<link rel="{sync.PUBLICATION_COLLECTION}" '
                f'href="{PUBLICATION_URI}">'
            ),
        }
        publication.update(publication_overrides)
        records = []
        for relative, app_key, uri in documents or []:
            records.append(
                {
                    "canonical_url": f"{sync.PUBLICATION_URL}/{relative}",
                    "app_key": app_key,
                    "at_uri": uri,
                    "link_tag": (
                        f'<link rel="{sync.DOCUMENT_COLLECTION}" href="{uri}">'
                    ),
                }
            )
        records.sort(key=lambda value: value["canonical_url"])
        return (
            json.dumps(
                {
                    "contract_version": 1,
                    "generated_at": "2026-07-28T00:00:00.000Z",
                    "publication": publication,
                    "documents": records,
                },
                separators=(",", ":"),
            )
            + "\n"
        ).encode()


class ContractSyncTests(ProjectScratchCase):
    def test_applies_publication_to_all_html_and_document_to_published_page(self):
        guide = self.write_html(
            "guides/demo.html",
            "<!doctype html>\n<html><head>\n"
            '<link rel="stylesheet" href="/assets/site.css">\n'
            "</head><body>Guide</body></html>\n",
        )
        other = self.write_html(
            "index.html",
            "<html><head><title>Home</title></head><body>Home</body></html>\n",
        )
        result = sync.synchronize_payload(
            self.contract([("guides/demo.html", "demo", DOCUMENT_URI)]),
            site_root=self.site,
            state_path=self.state,
        )
        self.assertEqual("applied", result.status)
        self.assertEqual(2, result.html_files)
        self.assertEqual(2, result.html_changed)
        guide_source = guide.read_text(encoding="utf-8")
        other_source = other.read_text(encoding="utf-8")
        self.assertIn(f'href="{PUBLICATION_URI}"', guide_source)
        self.assertIn(f'href="{DOCUMENT_URI}"', guide_source)
        self.assertIn('rel="stylesheet"', guide_source)
        self.assertIn(f'href="{PUBLICATION_URI}"', other_source)
        self.assertNotIn(sync.DOCUMENT_COLLECTION, other_source)
        self.assertTrue(self.state.is_file())

    def test_second_run_is_byte_identical_and_preserves_unmanaged_standard_tag(self):
        page = self.write_html(
            "index.html",
            "<html><head>\n"
            '<link rel="site.standard.graph.subscription" href="at://example">\n'
            "</head><body>Home</body></html>\n",
        )
        payload = self.contract()
        sync.synchronize_payload(
            payload, site_root=self.site, state_path=self.state
        )
        first_page = page.read_bytes()
        first_state = self.state.read_bytes()
        result = sync.synchronize_payload(
            payload, site_root=self.site, state_path=self.state
        )
        self.assertEqual(0, result.html_changed)
        self.assertFalse(result.state_changed)
        self.assertEqual(first_page, page.read_bytes())
        self.assertEqual(first_state, self.state.read_bytes())
        self.assertIn(b"site.standard.graph.subscription", first_page)

    def test_contract_removes_only_stale_managed_document_tag(self):
        page = self.write_html(
            "index.html",
            "<html><head>\n"
            f'<link rel="{sync.PUBLICATION_COLLECTION}" href="{PUBLICATION_URI}">\n'
            f'<link rel="{sync.DOCUMENT_COLLECTION}" href="{DOCUMENT_URI}">\n'
            '<link rel="alternate" href="/feed.xml">\n'
            "</head><body>Home</body></html>\n",
        )
        sync.synchronize_payload(
            self.contract(), site_root=self.site, state_path=self.state
        )
        source = page.read_text(encoding="utf-8")
        self.assertNotIn(sync.DOCUMENT_COLLECTION, source)
        self.assertIn('rel="alternate"', source)

    def test_multi_head_document_receives_hints_in_each_real_head(self):
        page = self.write_html(
            "bundle.html",
            "<html><head><title>One</title></head><body></body></html>\n"
            "<html><head><title>Two</title></head><body></body></html>\n",
        )
        sync.synchronize_payload(
            self.contract([("bundle.html", "demo", DOCUMENT_URI)]),
            site_root=self.site,
            state_path=self.state,
        )
        source = page.read_text(encoding="utf-8")
        self.assertEqual(
            2, source.count(f'rel="{sync.PUBLICATION_COLLECTION}"')
        )
        self.assertEqual(2, source.count(f'rel="{sync.DOCUMENT_COLLECTION}"'))

    def test_invalid_contract_leaves_every_file_untouched(self):
        first = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        second = self.write_html(
            "guides/demo.html", "<html><head></head><body>Guide</body></html>\n"
        )
        baseline = {path: path.read_bytes() for path in (first, second)}
        payload = json.loads(self.contract().decode())
        payload["publication"]["url"] = "https://attacker.example"
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                json.dumps(payload).encode(),
                site_root=self.site,
                state_path=self.state,
            )
        self.assertEqual(baseline, {path: path.read_bytes() for path in baseline})
        self.assertFalse(self.state.exists())

    def test_missing_document_file_leaves_every_file_untouched(self):
        page = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        baseline = page.read_bytes()
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                self.contract([("missing.html", "demo", DOCUMENT_URI)]),
                site_root=self.site,
                state_path=self.state,
            )
        self.assertEqual(baseline, page.read_bytes())
        self.assertFalse(self.state.exists())

    def test_unsafe_canonical_paths_are_rejected_without_changes(self):
        page = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        baseline = page.read_bytes()
        payload = json.loads(self.contract().decode())
        payload["documents"] = [
            {
                "canonical_url": f"{sync.PUBLICATION_URL}/../index.html",
                "app_key": "demo",
                "at_uri": DOCUMENT_URI,
                "link_tag": (
                    f'<link rel="{sync.DOCUMENT_COLLECTION}" '
                    f'href="{DOCUMENT_URI}">'
                ),
            }
        ]
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                json.dumps(payload).encode(),
                site_root=self.site,
                state_path=self.state,
            )
        self.assertEqual(baseline, page.read_bytes())

    def test_wrong_did_or_collection_is_rejected(self):
        self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        for uri in (
            PUBLICATION_URI.replace(sync.EXPECTED_DID, "did:plc:attacker"),
            PUBLICATION_URI.replace(
                sync.PUBLICATION_COLLECTION, sync.DOCUMENT_COLLECTION
            ),
        ):
            payload = json.loads(self.contract().decode())
            payload["publication"]["at_uri"] = uri
            with self.subTest(uri=uri), self.assertRaises(sync.SyncError):
                sync.synchronize_payload(
                    json.dumps(payload).encode(),
                    site_root=self.site,
                    state_path=self.state,
                )

    def test_well_known_root_endpoint_and_hash_are_required(self):
        self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        mutations = (
            ("request_path", "/ios-app-guide/.well-known/site.standard.publication"),
            (
                "request_url",
                f"{sync.PUBLICATION_URL}/.well-known/site.standard.publication",
            ),
            ("sha256", "0" * 64),
        )
        for field, value in mutations:
            payload = json.loads(self.contract().decode())
            payload["publication"]["well_known"][field] = value
            with self.subTest(field=field), self.assertRaises(sync.SyncError):
                sync.synchronize_payload(
                    json.dumps(payload).encode(),
                    site_root=self.site,
                    state_path=self.state,
                )

    def test_duplicate_json_key_is_rejected(self):
        page = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        baseline = page.read_bytes()
        payload = self.contract().replace(
            b'"contract_version":1,',
            b'"contract_version":1,"contract_version":1,',
            1,
        )
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                payload, site_root=self.site, state_path=self.state
            )
        self.assertEqual(baseline, page.read_bytes())

    def test_ambiguous_managed_rel_does_not_get_deleted(self):
        page = self.write_html(
            "index.html",
            "<html><head>\n"
            '<link rel="site.standard.document alternate" href="at://example">\n'
            "</head><body>Home</body></html>\n",
        )
        baseline = page.read_bytes()
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                self.contract(), site_root=self.site, state_path=self.state
            )
        self.assertEqual(baseline, page.read_bytes())

    def test_invalid_late_html_file_causes_no_partial_update(self):
        first = self.write_html(
            "a.html", "<html><head></head><body>First</body></html>\n"
        )
        second = self.write_html(
            "z.html", "<html><body>Missing head</body></html>\n"
        )
        baseline = {path: path.read_bytes() for path in (first, second)}
        with self.assertRaises(sync.SyncError):
            sync.synchronize_payload(
                self.contract(), site_root=self.site, state_path=self.state
            )
        self.assertEqual(baseline, {path: path.read_bytes() for path in baseline})
        self.assertFalse(self.state.exists())

    def test_install_failure_rolls_back_all_replaced_files(self):
        first = self.write_html(
            "a.html", "<html><head></head><body>First</body></html>\n"
        )
        second = self.write_html(
            "b.html", "<html><head></head><body>Second</body></html>\n"
        )
        baseline = {path: path.read_bytes() for path in (first, second)}
        real_install = sync._install_stage
        calls = 0

        def failing_install(stage: Path, target: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected replacement failure")
            real_install(stage, target)

        with mock.patch.object(sync, "_install_stage", side_effect=failing_install):
            with self.assertRaises(sync.SyncError):
                sync.synchronize_payload(
                    self.contract(), site_root=self.site, state_path=self.state
                )
        self.assertEqual(baseline, {path: path.read_bytes() for path in baseline})
        self.assertFalse(self.state.exists())
        self.assertFalse(
            (self.state.parent / sync.TRANSACTION_NAME).exists()
        )

    def test_contending_process_cannot_remove_active_lock(self):
        self.state.parent.mkdir(parents=True)
        lock_path = self.state.parent / sync.LOCK_NAME
        with sync._exclusive_lock(self.state):
            with self.assertRaises(sync.SyncError):
                with sync._exclusive_lock(self.state):
                    self.fail("contending lock unexpectedly succeeded")
            self.assertTrue(lock_path.is_file())
        self.assertFalse(lock_path.exists())


class ContractSourceTests(ProjectScratchCase):
    class FetchHTTPError(Exception):
        def __init__(self, code: int) -> None:
            self.code = code

    def test_initial_remote_404_skips_only_before_activation(self):
        page = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        baseline = page.read_bytes()
        with mock.patch.object(sync, "fetch_contract", return_value=None):
            result = sync.synchronize_source(
                site_root=self.site,
                state_path=self.state,
                contract_url="https://raw.githubusercontent.com/example/contract.json",
                allow_initial_404=True,
            )
        self.assertEqual("initial-contract-not-published", result.status)
        self.assertEqual(baseline, page.read_bytes())
        self.assertFalse(self.state.exists())

        sync.synchronize_payload(
            self.contract(), site_root=self.site, state_path=self.state
        )
        activated = page.read_bytes()
        with mock.patch.object(sync, "fetch_contract", return_value=None):
            with self.assertRaises(sync.ContractUnavailable):
                sync.synchronize_source(
                    site_root=self.site,
                    state_path=self.state,
                    contract_url=(
                        "https://raw.githubusercontent.com/example/contract.json"
                    ),
                    allow_initial_404=True,
                )
        self.assertEqual(activated, page.read_bytes())

    def test_local_fixture_source_is_supported(self):
        page = self.write_html(
            "index.html", "<html><head></head><body>Home</body></html>\n"
        )
        fixture = self.scratch / "contract.json"
        fixture.write_bytes(self.contract())
        result = sync.synchronize_source(
            site_root=self.site,
            state_path=self.state,
            contract_file=fixture,
        )
        self.assertEqual("applied", result.status)
        self.assertIn(
            sync.PUBLICATION_COLLECTION, page.read_text(encoding="utf-8")
        )

    def test_remote_fetch_retries_transient_errors_and_uses_timeout(self):
        payload = self.contract()
        calls: list[float] = []
        sleeps: list[float] = []

        class Response:
            headers = {"Content-Length": str(len(payload))}

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def geturl(self) -> str:
                return "https://example.com/contract.json"

            def read(self, limit: int) -> bytes:
                self.limit = limit
                return payload

        attempts = iter(
            (
                URLError("temporary"),
                self.FetchHTTPError(503),
                Response(),
            )
        )

        def opener(request: object, *, timeout: float) -> object:
            calls.append(timeout)
            result = next(attempts)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            mock.patch.object(sync, "HTTPError", self.FetchHTTPError),
            mock.patch.object(
                sync.socket,
                "getaddrinfo",
                return_value=[(None, None, None, None, ("93.184.216.34", 443))],
            ),
        ):
            result = sync.fetch_contract(
                "https://example.com/contract.json",
                timeout=2.5,
                retries=2,
                retry_delay=0.25,
                opener=opener,
                sleeper=sleeps.append,
            )
        self.assertEqual(payload, result)
        self.assertEqual([2.5, 2.5, 2.5], calls)
        self.assertEqual([0.25, 0.5], sleeps)

    def test_remote_fetch_never_retries_404(self):
        calls = 0

        def opener(request: object, *, timeout: float) -> object:
            nonlocal calls
            calls += 1
            raise self.FetchHTTPError(404)

        with (
            mock.patch.object(sync, "HTTPError", self.FetchHTTPError),
            mock.patch.object(
                sync.socket,
                "getaddrinfo",
                return_value=[(None, None, None, None, ("93.184.216.34", 443))],
            ),
        ):
            self.assertIsNone(
                sync.fetch_contract(
                    "https://example.com/contract.json",
                    retries=3,
                    opener=opener,
                    sleeper=lambda _: None,
                )
            )
        self.assertEqual(1, calls)

    def test_non_https_and_local_contract_urls_are_rejected(self):
        for url in (
            "http://example.com/contract.json",
            "https://localhost/contract.json",
            "https://127.0.0.1/contract.json",
            "https://user@example.com/contract.json",
        ):
            with self.subTest(url=url), self.assertRaises(sync.SyncError):
                sync.fetch_contract(url, retries=0)

    def test_remote_fetch_rejects_invalid_content_length(self):
        class Response:
            headers = {"Content-Length": "not-an-integer"}

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def geturl(self) -> str:
                return "https://example.com/contract.json"

            def read(self, limit: int) -> bytes:
                return b"{}"

        with (
            mock.patch.object(
                sync.socket,
                "getaddrinfo",
                return_value=[(None, None, None, None, ("93.184.216.34", 443))],
            ),
            self.assertRaises(sync.SyncError),
        ):
            sync.fetch_contract(
                "https://example.com/contract.json",
                retries=0,
                opener=lambda request, timeout: Response(),
            )


if __name__ == "__main__":
    unittest.main()
