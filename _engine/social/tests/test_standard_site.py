#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
import io
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest import mock
import urllib.error
import uuid


SOCIAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOCIAL))

import gen_standard_site as generator  # noqa: E402
import standard_site_publish as publisher  # noqa: E402


class FakeRepoClient:
    def __init__(self, did: str = "did:plc:testpublisher") -> None:
        self.did = did
        self.records: dict[tuple[str, str], dict[str, object]] = {}
        self.puts: list[tuple[str, str, dict[str, object], str | None]] = []
        self.gets: list[tuple[str, str]] = []
        self.fail_next_document = False

    def get_record(
        self, collection: str, rkey: str
    ) -> dict[str, object] | None:
        self.gets.append((collection, rkey))
        value = self.records.get((collection, rkey))
        return deepcopy(value) if value is not None else None

    def list_records(self, collection: str) -> list[dict[str, object]]:
        return [
            deepcopy(record)
            for (record_collection, _rkey), record in self.records.items()
            if record_collection == collection
        ]

    def put_record(
        self,
        collection: str,
        rkey: str,
        record: dict[str, object],
        *,
        swap_record: str | None = None,
    ) -> dict[str, object]:
        if (
            collection == publisher.DOCUMENT_COLLECTION
            and self.fail_next_document
        ):
            self.fail_next_document = False
            raise OSError("simulated network failure")
        key = (collection, rkey)
        previous = self.records.get(key)
        if previous is not None and swap_record != previous["cid"]:
            raise AssertionError("missing or wrong swapRecord")
        cid = f"bafyreitest{len(self.puts) + 1:04d}"
        uri = f"at://{self.did}/{collection}/{rkey}"
        value = {"uri": uri, "cid": cid, "value": deepcopy(record)}
        self.records[key] = value
        self.puts.append(
            (collection, rkey, deepcopy(record), swap_record)
        )
        return {"uri": uri, "cid": cid}


def fixture_manifest(
    app_documents: dict[str, int] | None = None,
) -> dict[str, object]:
    app_documents = app_documents or {"alpha": 1, "beta": 1, "gamma": 1}
    documents: list[dict[str, object]] = []
    for app_key, count in app_documents.items():
        name = app_key.title()
        for index in range(1, count + 1):
            canonical = (
                "https://alice51849.github.io/ios-app-guide/"
                f"answers/{app_key}-{index}.html"
            )
            disclosure = generator.DISCLOSURE_TEMPLATE.format(name=name)
            substantive = (
                f"This original first-party guide explains how to evaluate "
                f"{name} for a concrete workflow without inventing scores, "
                "ratings, downloads, or comparative claims. Start with the "
                "outcome you need, list the device and privacy constraints, "
                "test one non-critical example, and compare every required "
                "step with the current listing. "
            )
            text = "\n\n".join(
                [
                    disclosure,
                    f"{name} decision guide {index}",
                    "Context",
                    substantive * 5,
                    "What to verify",
                    (
                        "Confirm compatibility, the current regional offer, "
                        "the exact feature list, data handling, offline "
                        "behaviour, export needs, and the purchase model."
                    ),
                    "Limits",
                    generator.AVAILABILITY_NOTE,
                ]
            )
            document: dict[str, object] = {
                "app_key": app_key,
                "canonical_url": canonical,
                "path": f"/answers/{app_key}-{index}.html",
                "title": f"{name} decision guide {index}",
                "description": (
                    f"First-party publisher guidance for evaluating {name}."
                ),
                "text_content": text,
                "tags": [
                    app_key,
                    name,
                    "iOS",
                    "publisher-authored",
                    "first-party",
                ],
                "source_query": f"How should I evaluate {name}?",
                "editorial_kind": "guide",
            }
            document["content_hash"] = generator.document_content_hash(
                document
            )
            documents.append(document)
    manifest: dict[str, object] = {
        "schema_version": generator.MANIFEST_VERSION,
        "generated_at": "2026-07-27T14:00:00.000Z",
        "source": {
            "app_registry": "fixture",
            "live_catalog": "fixture",
            "live_catalog_sha256": "a" * 64,
            "editorial_catalog": "fixture",
            "live_app_keys": sorted(app_documents),
            "live_app_count": len(app_documents),
            "policy": "publisher-authored",
        },
        "publication": {
            "url": "https://alice51849.github.io/ios-app-guide",
            "name": "Lumi Studio App Guides",
            "description": (
                "First-party commercial publisher guidance; not an "
                "independent review or ranking."
            ),
            "preferences": {"showInDiscover": True},
        },
        "documents": documents,
    }
    generator.validate_manifest(manifest)
    return manifest


class ProjectScratchCase(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parent / ".standard_site_test_runs"
        root.mkdir(exist_ok=True)
        self.scratch = root / f"{self.__class__.__name__}-{uuid.uuid4().hex}"
        self.scratch.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.scratch)
        try:
            self.scratch.parent.rmdir()
        except OSError:
            pass

    def paths(self) -> tuple[Path, Path, Path]:
        return (
            self.scratch / "state.json",
            self.scratch / "contract.json",
            self.scratch / "site.standard.publication",
        )


class StandardSiteGeneratorTests(ProjectScratchCase):
    def _canonical(self, pages: Path, relative: str, site: str) -> None:
        path = pages / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        canonical = f"{site}/{relative}"
        path.write_text(
            f'<html><head><link rel="canonical" href="{canonical}"></head></html>',
            encoding="utf-8",
        )

    def test_manifest_uses_verified_live_catalog_and_substantive_disclosure(
        self,
    ) -> None:
        pages = self.scratch / "pages"
        pages.mkdir()
        (pages / generator.LIVE_STATE_NAME).write_text(
            json.dumps({"live_ids": ["101", "202"]}),
            encoding="utf-8",
        )
        site = "https://example.com/guide"
        query = "How can Alpha solve a careful real-world workflow?"
        slug = generator.slugify(query)
        self._canonical(pages, f"answers/{slug}.html", site)
        self._canonical(pages, "en-US/beta.html", site)
        apps = {
            "alpha": {
                "name": "Alpha",
                "category": "productivity",
                "sub": "Organize a careful workflow",
                "cta_bullets": ["No account", "Offline"],
                "purchase_model": "paid_upfront",
            },
            "beta": {
                "name": "Beta",
                "category": "utility",
                "sub": "Complete a focused utility task",
                "cta_bullets": ["Private", "Pay once"],
                "purchase_model": "free_with_lifetime_unlock",
            },
            "not-live": {"name": "Not Live"},
        }
        deep = [
            {
                "app_key": "alpha",
                "kind": "scenario",
                "query": query,
                "lead": "Begin with the real outcome and its constraints.",
                "detail": (
                    "A careful evaluation compares required inputs, device "
                    "support, privacy boundaries, failure recovery, and the "
                    "final output before adopting a tool. "
                )
                * 4,
                "bullets": [
                    "Write down the required outcome",
                    "Test a non-critical example first",
                    "Verify the current listing",
                ],
                "where_app_fits": (
                    "Alpha is optional and should be considered only after "
                    "the workflow checklist matches the user's needs."
                ),
                "faq": [
                    {
                        "q": "Is this an independent ranking?",
                        "a": (
                            "No. It is a first-party explanation from the "
                            "publisher."
                        ),
                    }
                ],
            }
        ]
        manifest = generator.build_manifest(
            pages=pages,
            site=site,
            apps=apps,
            appstore={"alpha": "101", "beta": "202", "not-live": "303"},
            deep_items=deep,
            max_per_app=1,
            now=datetime(2026, 7, 27, 14, tzinfo=timezone.utc),
        )
        self.assertEqual(["alpha", "beta"], manifest["source"]["live_app_keys"])
        self.assertEqual(
            {"alpha", "beta"},
            {document["app_key"] for document in manifest["documents"]},
        )
        self.assertNotIn(
            "not-live",
            {document["app_key"] for document in manifest["documents"]},
        )
        for document in manifest["documents"]:
            lowered = document["text_content"].casefold()
            self.assertGreaterEqual(len(document["text_content"]), 800)
            self.assertIn("publisher disclosure:", lowered)
            self.assertIn("not an independent review", lowered)
            self.assertNotIn("utm_", document["canonical_url"])

    def test_check_only_main_writes_nothing(self) -> None:
        output = self.scratch / "manifest.json"
        pages = self.scratch / "pages"
        pages.mkdir()
        with mock.patch.object(generator, "build_manifest", return_value=fixture_manifest()):
            result = generator.main(
                [
                    "--check-only",
                    "--pages",
                    str(pages),
                    "--output",
                    str(output),
                ]
            )
        self.assertEqual(0, result)
        self.assertFalse(output.exists())


class StandardSiteTIDTests(unittest.TestCase):
    def test_tid_matches_official_syntax_and_is_monotonic(self) -> None:
        generator = publisher.TIDGenerator(
            clock_us=lambda: 1_800_000_000_000_000,
            random_clock_id=lambda: 7,
        )
        first = generator.new()
        second = generator.new([first])
        third = generator.new([first, second])
        self.assertRegex(first, publisher.TID_RE)
        self.assertEqual(13, len(first))
        self.assertLess(
            publisher.decode_tid(first), publisher.decode_tid(second)
        )
        self.assertLess(
            publisher.decode_tid(second), publisher.decode_tid(third)
        )
        timestamp_us = publisher.decode_tid(first) >> 10
        self.assertEqual(1_800_000_000_000_000, timestamp_us)

    def test_invalid_tid_is_rejected(self) -> None:
        for value in ("url-hash-value", "1abcdefabcdef", "3abc-defghijk"):
            with self.assertRaises(ValueError):
                publisher.decode_tid(value)


class StandardSiteReadRetryTests(unittest.TestCase):
    DID = "did:plc:testpublisher"
    RKEY = "3lwafzkjqm25s"

    @staticmethod
    def http_error(
        code: int,
        *,
        retry_after: str | None = None,
        body: bytes = b'{"error":"UpstreamFailure"}',
    ) -> urllib.error.HTTPError:
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        return urllib.error.HTTPError(
            "https://bsky.social/xrpc/test",
            code,
            "test error",
            headers,
            io.BytesIO(body),
        )

    def client(
        self,
        request: mock.Mock,
        sleeps: list[float],
    ) -> publisher.ExistingBlueskyRepoClient:
        client = object.__new__(publisher.ExistingBlueskyRepoClient)
        client._module = SimpleNamespace(
            _req=request,
            _err=lambda error: error.read().decode("utf-8"),
        )
        client._client = SimpleNamespace(_headers=lambda: {"Auth": "test"})
        client.did = self.DID
        client.pds_xrpc = "https://bsky.social/xrpc"
        client._read_sleeper = sleeps.append
        return client

    def remote_record(self) -> dict[str, object]:
        return {
            "uri": (
                f"at://{self.DID}/{publisher.DOCUMENT_COLLECTION}/{self.RKEY}"
            ),
            "cid": "bafyreiretrytest",
            "value": {"$type": publisher.DOCUMENT_COLLECTION},
        }

    def test_list_records_retries_500_then_succeeds(self) -> None:
        sleeps: list[float] = []
        request = mock.Mock(
            side_effect=[
                self.http_error(500),
                {"records": []},
            ]
        )
        client = self.client(request, sleeps)

        self.assertEqual([], client.list_records(publisher.DOCUMENT_COLLECTION))
        self.assertEqual(2, request.call_count)
        self.assertEqual([publisher.READ_RETRY_BASE_SECONDS], sleeps)

    def test_get_record_honors_429_retry_after(self) -> None:
        sleeps: list[float] = []
        request = mock.Mock(
            side_effect=[
                self.http_error(429, retry_after="3"),
                self.remote_record(),
            ]
        )
        client = self.client(request, sleeps)

        result = client.get_record(
            publisher.DOCUMENT_COLLECTION, self.RKEY
        )
        self.assertEqual(self.remote_record(), result)
        self.assertEqual(2, request.call_count)
        self.assertEqual([3.0], sleeps)

    def test_permanent_4xx_read_fails_without_retry(self) -> None:
        sleeps: list[float] = []
        request = mock.Mock(side_effect=self.http_error(403))
        client = self.client(request, sleeps)

        with self.assertRaises(urllib.error.HTTPError) as raised:
            client.list_records(publisher.DOCUMENT_COLLECTION)
        self.assertEqual(403, raised.exception.code)
        raised.exception.close()
        self.assertEqual(1, request.call_count)
        self.assertEqual([], sleeps)

    def test_transport_retries_share_a_bounded_total_wait(self) -> None:
        sleeps: list[float] = []
        operation = mock.Mock(
            side_effect=urllib.error.URLError("temporarily offline")
        )

        with self.assertRaises(urllib.error.URLError):
            publisher.read_with_retry(
                operation,
                sleeper=sleeps.append,
                attempts=10,
                base_delay=4,
                max_delay=4,
                max_total_wait=5,
            )
        self.assertEqual([4], sleeps)
        self.assertLessEqual(sum(sleeps), 5)
        self.assertEqual(2, operation.call_count)

    def test_mutation_never_uses_read_retry(self) -> None:
        sleeps: list[float] = []
        request = mock.Mock(side_effect=self.http_error(500))
        client = self.client(request, sleeps)

        with self.assertRaises(urllib.error.HTTPError) as raised:
            client.put_record(
                publisher.DOCUMENT_COLLECTION,
                self.RKEY,
                {"$type": publisher.DOCUMENT_COLLECTION},
            )
        raised.exception.close()
        self.assertEqual(1, request.call_count)
        self.assertEqual([], sleeps)


class StandardSiteSelectionTests(unittest.TestCase):
    def test_daily_cap_dedup_and_cross_app_round_robin(self) -> None:
        manifest = fixture_manifest(
            {"alpha": 2, "beta": 2, "gamma": 2, "delta": 2}
        )
        state = publisher.empty_state()
        publisher.allocate_rkeys(
            state,
            manifest,
            publisher.TIDGenerator(
                clock_us=lambda: 1_800_000_000_000_000,
                random_clock_id=lambda: 1,
            ),
        )
        first = publisher.reserve_daily_batch(
            state,
            manifest,
            day="2026-07-27",
            limit=2,
            now="2026-07-27T14:00:00.000Z",
        )
        retry = publisher.reserve_daily_batch(
            state,
            manifest,
            day="2026-07-27",
            limit=4,
            now="2026-07-27T15:00:00.000Z",
        )
        self.assertEqual(
            [item["canonical_url"] for item in first],
            [item["canonical_url"] for item in retry],
        )
        self.assertEqual(["alpha", "beta"], [item["app_key"] for item in first])
        for document in first:
            entry = state["documents"][document["canonical_url"]]
            entry["published"] = True
            entry["published_hash"] = document["content_hash"]
        second = publisher.reserve_daily_batch(
            state,
            manifest,
            day="2026-07-28",
            limit=2,
            now="2026-07-28T14:00:00.000Z",
        )
        self.assertEqual(["delta", "gamma"], sorted(
            item["app_key"] for item in second
        ))
        self.assertEqual(
            len(second), len({item["app_key"] for item in second})
        )
        self.assertLessEqual(len(second), 2)
        with self.assertRaises(publisher.ConfigurationError):
            publisher.reserve_daily_batch(
                state,
                manifest,
                day="2026-07-29",
                limit=5,
                now="2026-07-29T14:00:00.000Z",
            )

    def test_no_pending_documents_does_not_create_empty_daily_state(self) -> None:
        manifest = fixture_manifest({"alpha": 1})
        state = publisher.empty_state()
        publisher.allocate_rkeys(
            state,
            manifest,
            publisher.TIDGenerator(
                clock_us=lambda: 1_800_000_000_000_000,
                random_clock_id=lambda: 1,
            ),
        )
        document = manifest["documents"][0]
        state["documents"][document["canonical_url"]].update(
            {
                "published": True,
                "published_hash": document["content_hash"],
            }
        )

        selected = publisher.reserve_daily_batch(
            state,
            manifest,
            day="2026-07-27",
            limit=2,
            now="2026-07-27T14:00:00.000Z",
        )

        self.assertEqual([], selected)
        self.assertEqual({}, state["daily"])

    def test_duplicate_canonical_is_rejected(self) -> None:
        manifest = fixture_manifest()
        manifest["documents"][1]["canonical_url"] = (
            manifest["documents"][0]["canonical_url"]
        )
        with self.assertRaisesRegex(
            generator.ManifestError, "Duplicate canonical"
        ):
            generator.validate_manifest(manifest)


class StandardSitePublisherTests(ProjectScratchCase):
    DID = "did:plc:testpublisher"
    NOW = datetime(2026, 7, 27, 14, tzinfo=timezone.utc)
    ENV = {
        "BSKY_HANDLE": "publisher.example",
        "BSKY_APP_PASSWORD": "xxxx-xxxx-xxxx-xxxx",
    }

    @staticmethod
    def deterministic_tids() -> publisher.TIDGenerator:
        return publisher.TIDGenerator(
            clock_us=lambda: 1_800_000_000_000_000,
            random_clock_id=lambda: 2,
        )

    def test_upserts_are_idempotent_and_rkeys_stay_stable(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest()
        first = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=2,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state_before = json.loads(state_path.read_text(encoding="utf-8"))
        rkeys_before = {
            canonical: entry["rkey"]
            for canonical, entry in state_before["documents"].items()
        }
        puts_before = len(client.puts)
        second = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=4,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state_after = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(2, first["documents_changed"])
        self.assertEqual(0, second["documents_changed"])
        self.assertEqual(puts_before, len(client.puts))
        publication_put = next(
            item
            for item in client.puts
            if item[0] == publisher.PUBLICATION_COLLECTION
        )
        self.assertEqual(
            {
                "$type",
                "url",
                "name",
                "description",
                "preferences",
            },
            set(publication_put[2]),
        )
        for collection, rkey, record, _swap in client.puts:
            self.assertRegex(rkey, publisher.TID_RE)
            if collection == publisher.DOCUMENT_COLLECTION:
                self.assertEqual(
                    publisher.DOCUMENT_COLLECTION, record["$type"]
                )
                self.assertEqual(
                    first["publication_at_uri"], record["site"]
                )
                self.assertTrue(record["path"].startswith("/"))
                publisher.parse_timestamp(record["publishedAt"])
        self.assertEqual(
            rkeys_before,
            {
                canonical: entry["rkey"]
                for canonical, entry in state_after["documents"].items()
            },
        )
        self.assertTrue(state_after["publication"]["published"])
        self.assertTrue(contract_path.exists())
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        body = well_known_path.read_text(encoding="utf-8")
        publisher.validate_guide_contract(contract, body)
        self.assertEqual(
            "/.well-known/site.standard.publication/ios-app-guide",
            contract["publication"]["well_known"]["request_path"],
        )
        self.assertEqual(2, len(contract["documents"]))

    def test_failed_document_keeps_rkey_but_is_not_marked_published(
        self,
    ) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        client.fail_next_document = True
        manifest = fixture_manifest({"alpha": 1})
        first = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        canonical = manifest["documents"][0]["canonical_url"]
        assigned = state["documents"][canonical]["rkey"]
        self.assertEqual(1, len(first["errors"]))
        self.assertFalse(state["documents"][canonical].get("published", False))

        second = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=datetime(2026, 7, 27, 15, tzinfo=timezone.utc),
        )
        recovered = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual([], second["errors"])
        self.assertTrue(recovered["documents"][canonical]["published"])
        self.assertEqual(assigned, recovered["documents"][canonical]["rkey"])

    def test_changed_document_updates_same_record_with_swap(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        canonical = manifest["documents"][0]["canonical_url"]
        original_rkey = state["documents"][canonical]["rkey"]
        first_document_put = [
            item
            for item in client.puts
            if item[0] == publisher.DOCUMENT_COLLECTION
        ][0]

        updated = deepcopy(manifest)
        updated_document = updated["documents"][0]
        updated_document["text_content"] += (
            "\n\nUpdate note\n\nThe maintained workflow guidance was "
            "clarified without changing the canonical article."
        )
        updated_document["content_hash"] = generator.document_content_hash(
            updated_document
        )
        generator.validate_manifest(updated)
        result = publisher.run(
            updated,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=datetime(2026, 7, 28, 14, tzinfo=timezone.utc),
        )
        final_state = json.loads(state_path.read_text(encoding="utf-8"))
        document_puts = [
            item
            for item in client.puts
            if item[0] == publisher.DOCUMENT_COLLECTION
        ]
        self.assertEqual(1, result["documents_changed"])
        self.assertEqual(2, len(document_puts))
        self.assertEqual(original_rkey, document_puts[1][1])
        self.assertEqual(first_document_put[1], document_puts[1][1])
        self.assertIsNotNone(document_puts[1][3])
        self.assertIn("updatedAt", document_puts[1][2])
        self.assertEqual(
            original_rkey, final_state["documents"][canonical]["rkey"]
        )

    def test_missing_state_recovers_remote_rkeys_without_duplicate_records(
        self,
    ) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        original_state = json.loads(state_path.read_text(encoding="utf-8"))
        original_rkey = next(iter(original_state["documents"].values()))["rkey"]
        puts_before = len(client.puts)
        state_path.unlink()
        contract_path.unlink()
        well_known_path.unlink()

        result = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=publisher.TIDGenerator(
                clock_us=lambda: 1_900_000_000_000_000,
                random_clock_id=lambda: 9,
            ),
            now=datetime(2026, 7, 28, 14, tzinfo=timezone.utc),
        )

        recovered = json.loads(state_path.read_text(encoding="utf-8"))
        recovered_rkey = next(iter(recovered["documents"].values()))["rkey"]
        self.assertEqual(puts_before, len(client.puts))
        self.assertEqual([], result["selected_urls"])
        self.assertEqual(original_rkey, recovered_rkey)
        self.assertTrue(next(iter(recovered["documents"].values()))["published"])

    def test_remote_document_mutation_is_repaired_on_the_same_rkey(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        canonical = manifest["documents"][0]["canonical_url"]
        rkey = state["documents"][canonical]["rkey"]
        key = (publisher.DOCUMENT_COLLECTION, rkey)
        client.records[key]["value"]["textContent"] = "tampered remotely"
        puts_before = len(client.puts)

        result = publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=datetime(2026, 7, 28, 14, tzinfo=timezone.utc),
        )

        self.assertEqual(puts_before + 1, len(client.puts))
        self.assertEqual(1, result["documents_changed"])
        self.assertEqual(rkey, client.puts[-1][1])
        self.assertIsNotNone(client.puts[-1][3])
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(contract["documents"]))

    def test_deleted_remote_document_is_recreated_on_the_same_rkey(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        canonical = manifest["documents"][0]["canonical_url"]
        rkey = state["documents"][canonical]["rkey"]
        del client.records[(publisher.DOCUMENT_COLLECTION, rkey)]
        puts_before = len(client.puts)

        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=datetime(2026, 7, 28, 14, tzinfo=timezone.utc),
        )

        self.assertEqual(puts_before + 1, len(client.puts))
        self.assertEqual(rkey, client.puts[-1][1])
        self.assertIsNone(client.puts[-1][3])

    def test_duplicate_remote_publication_fails_closed(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        publisher.run(
            manifest,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=1,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=self.NOW,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        publication_rkey = state["publication"]["rkey"]
        duplicate_rkey = publisher.TIDGenerator(
            clock_us=lambda: 1_900_000_000_000_000,
            random_clock_id=lambda: 9,
        ).new([publication_rkey])
        record = publisher.publication_record(manifest)
        client.records[(publisher.PUBLICATION_COLLECTION, duplicate_rkey)] = {
            "uri": (
                f"at://{self.DID}/{publisher.PUBLICATION_COLLECTION}/"
                f"{duplicate_rkey}"
            ),
            "cid": "bafyreiduplicate",
            "value": record,
        }
        puts_before = len(client.puts)

        with self.assertRaisesRegex(
            publisher.StateError, "Multiple remote records"
        ):
            publisher.run(
                manifest,
                state_path=state_path,
                contract_path=contract_path,
                well_known_path=well_known_path,
                limit=1,
                publish=True,
                environment=self.ENV,
                client_factory=lambda _handle, _password: client,
                expected_did=self.DID,
                tid_generator=self.deterministic_tids(),
                now=datetime(2026, 7, 28, 14, tzinfo=timezone.utc),
            )
        self.assertEqual(puts_before, len(client.puts))

    def test_concurrent_publisher_is_rejected_before_network_login(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        called = False

        def factory(_handle: str, _password: str) -> object:
            nonlocal called
            called = True
            return FakeRepoClient(self.DID)

        with publisher.publisher_lock(state_path):
            with self.assertRaisesRegex(
                publisher.StateError, "already running"
            ):
                publisher.run(
                    fixture_manifest({"alpha": 1}),
                    state_path=state_path,
                    contract_path=contract_path,
                    well_known_path=well_known_path,
                    limit=1,
                    publish=True,
                    environment=self.ENV,
                    client_factory=factory,
                    expected_did=self.DID,
                    now=self.NOW,
                )
        self.assertFalse(called)

    def test_publisher_lock_keeps_one_stable_inode_between_runs(self) -> None:
        state_path, _contract_path, _well_known_path = self.paths()
        lock_path = state_path.with_name(
            state_path.name + publisher.LOCK_SUFFIX
        )

        with publisher.publisher_lock(state_path):
            first_inode = lock_path.stat().st_ino

        self.assertTrue(lock_path.exists())
        with publisher.publisher_lock(state_path):
            self.assertEqual(first_inode, lock_path.stat().st_ino)

    def test_missing_secret_fails_closed_before_state_or_network(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        called = False

        def factory(_handle: str, _password: str) -> object:
            nonlocal called
            called = True
            raise AssertionError("network client must not be created")

        with self.assertRaisesRegex(
            publisher.ConfigurationError, "BSKY_HANDLE"
        ):
            publisher.run(
                fixture_manifest(),
                state_path=state_path,
                contract_path=contract_path,
                well_known_path=well_known_path,
                publish=True,
                environment={},
                client_factory=factory,
                expected_did=self.DID,
                now=self.NOW,
            )
        self.assertFalse(called)
        self.assertFalse(state_path.exists())
        self.assertFalse(contract_path.exists())
        self.assertFalse(well_known_path.exists())

    def test_dry_run_has_zero_side_effects_and_no_login(self) -> None:
        state_path, contract_path, well_known_path = self.paths()

        def factory(_handle: str, _password: str) -> object:
            raise AssertionError("dry-run must not create a network client")

        result = publisher.run(
            fixture_manifest(),
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=3,
            publish=False,
            environment={},
            client_factory=factory,
            expected_did=self.DID,
            now=self.NOW,
        )
        self.assertEqual("check-only", result["mode"])
        self.assertLessEqual(len(result["selected_urls"]), 3)
        self.assertFalse(state_path.exists())
        self.assertFalse(contract_path.exists())
        self.assertFalse(well_known_path.exists())

    def test_atomic_failure_preserves_previous_healthy_state(self) -> None:
        state_path, _, _ = self.paths()
        original = publisher.empty_state()
        publisher.atomic_write_json(state_path, original)
        original_bytes = state_path.read_bytes()
        changed = deepcopy(original)
        changed["rotation"]["last_app"] = "alpha"
        with mock.patch.object(
            generator.os,
            "replace",
            side_effect=OSError("simulated atomic replace failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated"):
                publisher.atomic_write_json(state_path, changed)
        self.assertEqual(original_bytes, state_path.read_bytes())
        self.assertEqual(
            [],
            list(state_path.parent.glob(f".{state_path.name}.*.tmp")),
        )

    def test_unchanged_guide_contract_preserves_original_bytes(self) -> None:
        _, contract_path, well_known_path = self.paths()
        manifest = fixture_manifest({"alpha": 1})
        state = publisher.empty_state()
        publisher.allocate_rkeys(
            state,
            manifest,
            self.deterministic_tids(),
        )
        state["publication"].update(
            {
                "did": self.DID,
                "published": True,
            }
        )
        document = manifest["documents"][0]
        state["documents"][document["canonical_url"]]["published"] = True
        first, body = publisher.build_guide_contract(
            manifest,
            state,
            generated_at="2026-07-27T14:00:00.000Z",
        )
        publisher.write_guide_artifacts(
            contract_path,
            well_known_path,
            first,
            body,
        )
        original = contract_path.read_bytes()
        second, second_body = publisher.build_guide_contract(
            manifest,
            state,
            generated_at="2026-07-28T14:00:00.000Z",
        )

        publisher.write_guide_artifacts(
            contract_path,
            well_known_path,
            second,
            second_body,
        )

        self.assertEqual(original, contract_path.read_bytes())

    def test_state_write_failure_prevents_network_login(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        called = False

        def factory(_handle: str, _password: str) -> object:
            nonlocal called
            called = True
            return FakeRepoClient(self.DID)

        with mock.patch.object(
            publisher,
            "atomic_write_json",
            side_effect=OSError("disk unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "disk unavailable"):
                publisher.run(
                    fixture_manifest(),
                    state_path=state_path,
                    contract_path=contract_path,
                    well_known_path=well_known_path,
                    publish=True,
                    environment=self.ENV,
                    client_factory=factory,
                    expected_did=self.DID,
                    now=self.NOW,
                )
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
