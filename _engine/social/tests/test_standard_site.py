#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
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
from urllib.parse import urlsplit
import uuid


SOCIAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOCIAL))

import gen_standard_site as generator  # noqa: E402
import standard_site_attribution as attribution  # noqa: E402
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
    for app_number, (app_key, count) in enumerate(
        app_documents.items(), start=1
    ):
        name = app_key.title()
        app_id = str(1_000_000 + app_number)
        primary_url = attribution.attributed_app_store_url(
            f"https://apps.apple.com/us/app/{app_key}/id{app_id}"
        )
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
                    "Open in the App Store",
                    primary_url,
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
                "app_store_id": app_id,
                "primary_app_store_url": primary_url,
                "legacy_app_store_link": attribution.LEGACY_BARE_URL,
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
        by_app = {
            document["app_key"]: document
            for document in manifest["documents"]
        }
        self.assertEqual(
            attribution.LEGACY_ABSENT_URL,
            by_app["alpha"]["legacy_app_store_link"],
        )
        self.assertEqual(
            attribution.LEGACY_BARE_URL,
            by_app["beta"]["legacy_app_store_link"],
        )
        self.assertEqual(
            [],
            attribution.direct_app_store_urls(
                attribution.legacy_text_content(
                    by_app["alpha"]["text_content"],
                    app_id=by_app["alpha"]["app_store_id"],
                    mode=by_app["alpha"]["legacy_app_store_link"],
                )
            ),
        )
        for document in manifest["documents"]:
            lowered = document["text_content"].casefold()
            self.assertGreaterEqual(len(document["text_content"]), 800)
            self.assertIn("publisher disclosure:", lowered)
            self.assertIn("not an independent review", lowered)
            self.assertNotIn("utm_", document["canonical_url"])
            primary = attribution.validate_primary_app_store_url(
                document["text_content"],
                app_id=document["app_store_id"],
                expected_url=document["primary_app_store_url"],
            )
            self.assertEqual(
                attribution.PRIMARY_QUERY,
                urlsplit(primary).query,
            )

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


class StandardSiteAttributionTests(unittest.TestCase):
    def test_native_rtl_markdown_cta_and_percent_encoded_route_are_preserved(
        self,
    ) -> None:
        base = (
            "https://apps.apple.com/ae/app/"
            "%D8%AA%D8%B7%D8%A8%D9%8A%D9%82/id1234567890"
        )
        text = f"\u200fنزّل الآن: [افتح التطبيق]({base}) \u200f"

        updated, primary, legacy_mode = (
            attribution.ensure_primary_app_store_url(
                text,
                app_id="1234567890",
                fallback_route="https://apps.apple.com/app/id1234567890",
            )
        )

        self.assertIn("\u200fنزّل الآن: [افتح التطبيق](", updated)
        self.assertIn("%D8%AA%D8%B7%D8%A8%D9%8A%D9%82", primary)
        self.assertEqual(
            base + "?" + attribution.PRIMARY_QUERY,
            primary,
        )
        self.assertEqual(attribution.LEGACY_BARE_URL, legacy_mode)
        self.assertEqual(1, len(attribution.direct_app_store_urls(updated)))

    def test_card_wrapper_alone_is_not_a_primary_direct_url(self) -> None:
        wrapper = (
            "https://cards.example/open?target="
            "https%3A%2F%2Fapps.apple.com%2Fapp%2Fid1234567890"
            "%3Fpt%3D118326163%26ct%3Dstandard_site%26mt%3D8"
        )
        with self.assertRaisesRegex(
            attribution.AttributionError, "exactly one"
        ):
            attribution.validate_primary_app_store_url(
                f"Open the enhanced card: {wrapper}",
                app_id="1234567890",
            )

    def test_duplicate_direct_urls_fail_closed(self) -> None:
        primary = attribution.attributed_app_store_url(
            "https://apps.apple.com/app/id1234567890"
        )
        with self.assertRaisesRegex(
            attribution.AttributionError, "exactly one"
        ):
            attribution.validate_primary_app_store_url(
                f"{primary} {primary}",
                app_id="1234567890",
            )

    def test_apple_redirect_may_drop_mt_but_not_source_campaign(self) -> None:
        source = attribution.attributed_app_store_url(
            "https://apps.apple.com/us/app/id1234567890"
        )
        self.assertTrue(
            attribution.redirect_preserves_attribution(
                source,
                (
                    "https://apps.apple.com/us/app/example/id1234567890"
                    "?pt=118326163&ct=standard_site"
                ),
            )
        )
        self.assertFalse(
            attribution.redirect_preserves_attribution(
                source,
                (
                    "https://apps.apple.com/us/app/example/id1234567890"
                    "?ct=standard_site"
                ),
            )
        )


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
            for field in publisher.ORDINARY_REPUBLISH_FIELDS:
                entry.pop(field, None)
            entry.pop(publisher.PENDING_WINDOW_FIELD, None)
            entry.pop(publisher.PENDING_LIFECYCLE_FIELD, None)
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


class StandardSitePendingWindowTests(unittest.TestCase):
    @staticmethod
    def _allocated(
        app_documents: dict[str, int],
    ) -> tuple[dict[str, object], dict[str, object]]:
        manifest = fixture_manifest(app_documents)
        state = publisher.empty_state()
        publisher.allocate_rkeys(
            state,
            manifest,
            publisher.TIDGenerator(
                clock_us=lambda: 1_800_000_000_000_000,
                random_clock_id=lambda: 1,
            ),
        )
        return state, manifest

    @staticmethod
    def _mark_apps(
        state: dict[str, object],
        manifest: dict[str, object],
        apps: set[str],
        timestamp: str,
    ) -> None:
        day = timestamp[:10]
        for document in manifest["documents"]:
            if document["app_key"] not in apps:
                continue
            entry = state["documents"][document["canonical_url"]]
            entry["published_at"] = timestamp
            publisher._mark_ordinary_republish_pending(
                entry,
                detected_at=timestamp,
                republish_after_day=day,
            )

    @staticmethod
    def _complete(
        state: dict[str, object],
        document: dict[str, object],
    ) -> None:
        entry = state["documents"][document["canonical_url"]]
        entry["published"] = True
        entry["published_hash"] = document["content_hash"]
        for field in (
            *publisher.ATTRIBUTION_REPAIR_FIELDS,
            publisher.ATTRIBUTION_REPAIR_BACKLOG_FIELD,
            *publisher.ORDINARY_REPUBLISH_FIELDS,
            publisher.PENDING_WINDOW_FIELD,
            publisher.PENDING_LIFECYCLE_FIELD,
        ):
            entry.pop(field, None)

    def test_round_robin_bound_uses_app_cycles_for_all_limits(self) -> None:
        entries = [
            {"app_key": "alpha"},
            {"app_key": "alpha"},
            {"app_key": "beta"},
            {"app_key": "gamma"},
            {"app_key": "delta"},
        ]

        self.assertEqual(
            {1: 8, 2: 4, 4: 2},
            {
                limit: publisher.pending_state.backlog_drain_days(
                    entries, limit
                )
                for limit in (1, 2, 4)
            },
        )

    def test_cohort_additions_widen_without_cross_midnight_starvation(
        self,
    ) -> None:
        state, manifest = self._allocated(
            {
                "alpha": 2,
                "beta": 1,
                "gamma": 1,
                "delta": 1,
                "epsilon": 1,
            }
        )
        self._mark_apps(
            state,
            manifest,
            {"alpha"},
            "2026-07-28T10:00:00.000Z",
        )
        publisher._finalize_pending_backlogs(
            state,
            manifest,
            limit=2,
            updated_at="2026-07-28T10:00:00.000Z",
        )
        alpha_urls = [
            document["canonical_url"]
            for document in manifest["documents"]
            if document["app_key"] == "alpha"
        ]
        self.assertEqual(
            {2},
            {
                state["documents"][url]["republish_backlog_days"]
                for url in alpha_urls
            },
        )

        observed = []
        for hour, app in enumerate(("beta", "gamma", "delta"), start=11):
            timestamp = f"2026-07-28T{hour:02d}:00:00.000Z"
            self._mark_apps(state, manifest, {app}, timestamp)
            publisher._finalize_pending_backlogs(
                state,
                manifest,
                limit=2,
                updated_at=timestamp,
            )
            observed.append(
                state["documents"][alpha_urls[0]][
                    "republish_backlog_days"
                ]
            )
        self.assertEqual([2, 4, 4], observed)
        alpha_window = state["documents"][alpha_urls[0]][
            publisher.PENDING_WINDOW_FIELD
        ]
        self.assertEqual(1, alpha_window["version"])
        self.assertEqual(2, alpha_window["effective_daily_limit"])
        self.assertEqual(5, alpha_window["pending_documents"])
        self.assertEqual(4, alpha_window["pending_apps"])
        self.assertEqual(2, alpha_window["max_per_app"])
        self.assertEqual(4, alpha_window["computed_days"])
        self.assertEqual(
            {
                "version": 1,
                "effective_daily_limit": 2,
                "revision_at": "2026-07-28T13:00:00.000Z",
            },
            state[publisher.PENDING_POLICY_FIELD],
        )

        self._mark_apps(
            state,
            manifest,
            {"epsilon"},
            "2026-07-29T00:01:00.000Z",
        )
        publisher._finalize_pending_backlogs(
            state,
            manifest,
            limit=2,
            updated_at="2026-07-29T00:01:00.000Z",
        )
        epsilon_url = next(
            document["canonical_url"]
            for document in manifest["documents"]
            if document["app_key"] == "epsilon"
        )
        self.assertEqual(
            4,
            state["documents"][alpha_urls[0]][
                "republish_backlog_days"
            ],
        )
        self.assertEqual(
            5,
            state["documents"][epsilon_url][
                "republish_backlog_days"
            ],
        )
        selected = publisher.reserve_daily_batch(
            state,
            manifest,
            day="2026-07-29",
            limit=2,
            now="2026-07-29T00:02:00.000Z",
        )
        self.assertTrue(selected)
        self.assertNotIn(
            "epsilon", {document["app_key"] for document in selected}
        )

        reduced = deepcopy(manifest)
        reduced["documents"] = [
            document
            for document in reduced["documents"]
            if document["app_key"] in {"alpha", "epsilon"}
        ]
        publisher._finalize_pending_backlogs(
            state,
            reduced,
            limit=2,
            updated_at="2026-07-29T00:03:00.000Z",
        )
        audit = publisher.pending_state.audit_pending_documents(
            state,
            reduced,
            now=datetime(2026, 7, 29, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(3, audit["counts"]["ordinary_republish"])
        self.assertEqual(
            4,
            state["documents"][alpha_urls[0]][
                "republish_backlog_days"
            ],
        )

    def test_limit_changes_only_widen_and_clock_rollback_fails(self) -> None:
        state, manifest = self._allocated(
            {"alpha": 2, "beta": 1, "gamma": 1, "delta": 1}
        )
        self._mark_apps(
            state,
            manifest,
            {"alpha", "beta", "gamma", "delta"},
            "2026-07-28T10:00:00.000Z",
        )
        publisher._finalize_pending_backlogs(
            state,
            manifest,
            limit=4,
            updated_at="2026-07-28T10:00:00.000Z",
        )
        entries = state["documents"].values()
        self.assertEqual(
            {2},
            {entry["republish_backlog_days"] for entry in entries},
        )
        with self.assertRaisesRegex(
            publisher.StateError, "newer revision"
        ):
            publisher._finalize_pending_backlogs(
                state,
                manifest,
                limit=1,
                updated_at="2026-07-28T10:00:00.000Z",
            )

        publisher._finalize_pending_backlogs(
            state,
            manifest,
            limit=1,
            updated_at="2026-07-28T11:00:00.000Z",
        )
        self.assertEqual(
            {8},
            {
                entry["republish_backlog_days"]
                for entry in state["documents"].values()
            },
        )
        self.assertEqual(
            1,
            state[publisher.PENDING_POLICY_FIELD][
                "effective_daily_limit"
            ],
        )

        publisher._finalize_pending_backlogs(
            state,
            manifest,
            limit=4,
            updated_at="2026-07-28T12:00:00.000Z",
        )
        self.assertEqual(
            {8},
            {
                entry["republish_backlog_days"]
                for entry in state["documents"].values()
            },
        )
        self.assertEqual(
            4,
            state[publisher.PENDING_POLICY_FIELD][
                "effective_daily_limit"
            ],
        )
        with self.assertRaisesRegex(
            publisher.StateError, "clock moved backwards"
        ):
            publisher._finalize_pending_backlogs(
                state,
                manifest,
                limit=4,
                updated_at="2026-07-28T11:59:59.000Z",
            )
        for invalid in (True, 0, 5):
            with self.subTest(limit=invalid), self.assertRaises(
                publisher.StateError
            ):
                publisher._finalize_pending_backlogs(
                    state,
                    manifest,
                    limit=invalid,
                    updated_at="2026-07-28T12:01:00.000Z",
                )

    def test_legacy_three_document_migration_drains_without_deadline_shrink(
        self,
    ) -> None:
        state, manifest = self._allocated({"alpha": 2, "beta": 1})
        anchor = "2026-07-28T10:00:00.000Z"
        for entry in state["documents"].values():
            entry["published"] = False
            entry["published_at"] = anchor

        changed = publisher.pending_state.migrate_legacy_pending_windows(
            state,
            manifest,
            daily_limit=1,
            migrated_at=anchor,
        )

        self.assertTrue(changed)
        self.assertEqual(
            {
                "version": 1,
                "completed_at": anchor,
                "document_count": 3,
                "effective_daily_limit": 1,
                "max_computed_days": 4,
            },
            state[publisher.PENDING_MIGRATION_FIELD],
        )
        deadlines: dict[str, str] = {}
        documents = {
            document["canonical_url"]: document
            for document in manifest["documents"]
        }
        start = datetime(2026, 7, 28, 10, tzinfo=timezone.utc)
        for offset in range(3):
            audit = publisher.pending_state.audit_pending_documents(
                state,
                manifest,
                now=start + timedelta(days=offset),
            )
            for detail in audit["documents"]:
                canonical = detail["canonical_url"]
                previous = deadlines.get(canonical)
                if previous is not None:
                    self.assertGreaterEqual(
                        detail["deadline_day"], previous
                    )
                deadlines[canonical] = detail["deadline_day"]
            selected = publisher.reserve_daily_batch(
                state,
                manifest,
                day=(start + timedelta(days=offset)).date().isoformat(),
                limit=1,
                now=publisher.utc_timestamp(
                    start + timedelta(days=offset)
                ),
            )
            self.assertEqual(1, len(selected))
            self._complete(state, dict(selected[0]))

        final_audit = publisher.pending_state.audit_pending_documents(
            state,
            manifest,
            now=start + timedelta(days=3),
        )
        self.assertEqual(0, final_audit["counts"]["total"])
        self.assertTrue(
            all(
                entry["published"] is True
                for entry in state["documents"].values()
            )
        )

    def test_legacy_migration_is_transactional_idempotent_and_anchored(
        self,
    ) -> None:
        state, manifest = self._allocated({"alpha": 2, "beta": 1})
        recent_anchor = "2026-07-28T10:00:00.000Z"
        for entry in state["documents"].values():
            entry["published"] = False
            entry["published_at"] = recent_anchor
        original = deepcopy(state)
        real_activate = publisher.pending_state.activate_pending_entry
        activation_calls = 0

        def fail_during_classification(*args, **kwargs):
            nonlocal activation_calls
            activation_calls += 1
            if activation_calls == 2:
                raise RuntimeError("simulated classification crash")
            return real_activate(*args, **kwargs)

        with mock.patch.object(
            publisher.pending_state,
            "activate_pending_entry",
            side_effect=fail_during_classification,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated classification crash"
            ):
                publisher.pending_state.migrate_legacy_pending_windows(
                    state,
                    manifest,
                    daily_limit=2,
                    migrated_at=recent_anchor,
                )
        self.assertEqual(original, state)
        self.assertNotIn(publisher.PENDING_MIGRATION_FIELD, state)
        with mock.patch.object(
            publisher.pending_state,
            "finalize_pending_windows",
            side_effect=RuntimeError("simulated migration crash"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "simulated migration crash"
            ):
                publisher.pending_state.migrate_legacy_pending_windows(
                    state,
                    manifest,
                    daily_limit=2,
                    migrated_at=recent_anchor,
                )
        self.assertEqual(original, state)
        self.assertNotIn(publisher.PENDING_MIGRATION_FIELD, state)

        publisher.pending_state.migrate_legacy_pending_windows(
            state,
            manifest,
            daily_limit=2,
            migrated_at=recent_anchor,
        )
        migrated = deepcopy(state)
        self.assertFalse(
            publisher.pending_state.migrate_legacy_pending_windows(
                state,
                manifest,
                daily_limit=2,
                migrated_at=recent_anchor,
            )
        )
        self.assertEqual(migrated, state)
        unclassified = deepcopy(state)
        broken = next(iter(unclassified["documents"].values()))
        for field in (
            *publisher.ORDINARY_REPUBLISH_FIELDS,
            publisher.PENDING_WINDOW_FIELD,
            publisher.PENDING_LIFECYCLE_FIELD,
        ):
            broken.pop(field, None)
        with self.assertRaisesRegex(
            publisher.pending_state.PendingStateError,
            "unclassified row",
        ):
            publisher.pending_state.validate_pending_state(
                unclassified,
                require_finalized=True,
            )
        for entry in state["documents"].values():
            self.assertEqual(
                recent_anchor, entry["republish_detected_at"]
            )
            self.assertIsNotNone(entry[publisher.PENDING_WINDOW_FIELD])
        initial_audit = publisher.pending_state.audit_pending_documents(
            state,
            manifest,
            now=datetime(2026, 7, 29, 10, tzinfo=timezone.utc),
        )
        initial_deadlines = {
            item["canonical_url"]: item["deadline_day"]
            for item in initial_audit["documents"]
        }
        reduced = deepcopy(manifest)
        reduced["documents"] = reduced["documents"][:1]
        publisher.pending_state.audit_pending_documents(
            state,
            reduced,
            now=datetime(2026, 7, 29, 10, tzinfo=timezone.utc),
        )
        regrown = publisher.pending_state.audit_pending_documents(
            state,
            manifest,
            now=datetime(2026, 7, 29, 10, tzinfo=timezone.utc),
        )
        self.assertEqual(
            initial_deadlines,
            {
                item["canonical_url"]: item["deadline_day"]
                for item in regrown["documents"]
            },
        )

        old_state, old_manifest = self._allocated(
            {"alpha": 2, "beta": 1}
        )
        old_anchor = "2026-07-01T10:00:00.000Z"
        for entry in old_state["documents"].values():
            entry["published"] = False
            entry["published_at"] = old_anchor
        publisher.pending_state.migrate_legacy_pending_windows(
            old_state,
            old_manifest,
            daily_limit=2,
            migrated_at="2026-07-28T10:00:00.000Z",
        )
        old_entry = next(iter(old_state["documents"].values()))
        self.assertEqual(
            old_anchor, old_entry["republish_detected_at"]
        )
        self.assertEqual(
            "2026-07-28T10:00:00.000Z",
            old_entry[publisher.PENDING_LIFECYCLE_FIELD][
                "window_started_at"
            ],
        )
        for offset in (0, 1):
            publisher.pending_state.audit_pending_documents(
                old_state,
                old_manifest,
                now=datetime(2026, 7, 28, 10, tzinfo=timezone.utc)
                + timedelta(days=offset),
            )
        with self.assertRaisesRegex(
            publisher.pending_state.PendingStateError,
            "exceeded its bounded backlog window",
        ):
            publisher.pending_state.audit_pending_documents(
                old_state,
                old_manifest,
                now=datetime(2026, 7, 31, 10, tzinfo=timezone.utc),
            )

    def test_dormant_legacy_rows_reactivate_after_long_manifest_gaps(
        self,
    ) -> None:
        state, full_manifest = self._allocated(
            {"alpha": 1, "hourstag": 2}
        )
        active_manifest = deepcopy(full_manifest)
        active_manifest["documents"] = [
            document
            for document in active_manifest["documents"]
            if document["app_key"] == "alpha"
        ]
        provenance = "2026-08-04T08:10:51.673Z"
        for entry in state["documents"].values():
            entry["published"] = False
            entry["published_at"] = provenance
        migration_at = "2026-08-29T00:00:00.000Z"
        publisher.pending_state.migrate_legacy_pending_windows(
            state,
            active_manifest,
            daily_limit=2,
            migrated_at=migration_at,
        )
        self.assertEqual(
            3,
            state[publisher.PENDING_MIGRATION_FIELD][
                "document_count"
            ],
        )
        dormant_urls = [
            document["canonical_url"]
            for document in full_manifest["documents"]
            if document["app_key"] == "hourstag"
        ]
        for canonical in dormant_urls:
            entry = state["documents"][canonical]
            self.assertEqual(
                publisher.pending_state.PENDING_DORMANT,
                entry[publisher.PENDING_LIFECYCLE_FIELD]["state"],
            )
            self.assertNotIn(publisher.PENDING_WINDOW_FIELD, entry)
            self.assertEqual(provenance, entry["republish_detected_at"])
        alpha_document = next(
            document
            for document in full_manifest["documents"]
            if document["app_key"] == "alpha"
        )
        self._complete(state, dict(alpha_document))

        for delay in (1, 30, 100):
            candidate = deepcopy(state)
            activated = datetime(
                2026, 8, 29, tzinfo=timezone.utc
            ) + timedelta(days=delay)
            timestamp = publisher.utc_timestamp(activated)
            publisher.pending_state.migrate_legacy_pending_windows(
                candidate,
                full_manifest,
                daily_limit=2,
                migrated_at=timestamp,
            )
            for canonical in dormant_urls:
                entry = candidate["documents"][canonical]
                lifecycle = entry[publisher.PENDING_LIFECYCLE_FIELD]
                self.assertEqual(
                    publisher.pending_state.PENDING_ACTIVE,
                    lifecycle["state"],
                )
                self.assertEqual(timestamp, lifecycle["window_started_at"])
                self.assertEqual(1, lifecycle["activation_count"])
                self.assertEqual(provenance, lifecycle["provenance_at"])
                self.assertIn(publisher.PENDING_WINDOW_FIELD, entry)
            publisher.pending_state.audit_pending_documents(
                candidate,
                full_manifest,
                now=activated,
            )

        cycled = deepcopy(state)
        first_activation = datetime(2026, 8, 30, tzinfo=timezone.utc)
        publisher.pending_state.migrate_legacy_pending_windows(
            cycled,
            full_manifest,
            daily_limit=2,
            migrated_at=publisher.utc_timestamp(first_activation),
        )
        publisher.pending_state.migrate_legacy_pending_windows(
            cycled,
            active_manifest,
            daily_limit=2,
            migrated_at=publisher.utc_timestamp(
                first_activation + timedelta(days=1)
            ),
        )
        for canonical in dormant_urls:
            paused = cycled["documents"][canonical]
            self.assertEqual(
                publisher.pending_state.PENDING_DORMANT,
                paused[publisher.PENDING_LIFECYCLE_FIELD]["state"],
            )
            self.assertNotIn(publisher.PENDING_WINDOW_FIELD, paused)
        second_activation = first_activation + timedelta(days=30)
        publisher.pending_state.migrate_legacy_pending_windows(
            cycled,
            full_manifest,
            daily_limit=2,
            migrated_at=publisher.utc_timestamp(second_activation),
        )
        for canonical in dormant_urls:
            lifecycle = cycled["documents"][canonical][
                publisher.PENDING_LIFECYCLE_FIELD
            ]
            self.assertEqual(2, lifecycle["activation_count"])
            self.assertEqual(provenance, lifecycle["provenance_at"])
            self.assertEqual(
                publisher.utc_timestamp(second_activation),
                lifecycle["window_started_at"],
            )

        continuously_eligible = deepcopy(state)
        activated = datetime(2026, 8, 30, tzinfo=timezone.utc)
        publisher.pending_state.migrate_legacy_pending_windows(
            continuously_eligible,
            full_manifest,
            daily_limit=2,
            migrated_at=publisher.utc_timestamp(activated),
        )
        initial_starts = {
            canonical: continuously_eligible["documents"][canonical][
                publisher.PENDING_LIFECYCLE_FIELD
            ]["window_started_at"]
            for canonical in dormant_urls
        }
        for offset in (1, 2):
            publisher.pending_state.migrate_legacy_pending_windows(
                continuously_eligible,
                full_manifest,
                daily_limit=2,
                migrated_at=publisher.utc_timestamp(
                    activated + timedelta(days=offset)
                ),
            )
        self.assertEqual(
            initial_starts,
            {
                canonical: continuously_eligible["documents"][canonical][
                    publisher.PENDING_LIFECYCLE_FIELD
                ]["window_started_at"]
                for canonical in dormant_urls
            },
        )
        with self.assertRaisesRegex(
            publisher.pending_state.PendingStateError,
            "exceeded its bounded backlog window",
        ):
            publisher.pending_state.audit_pending_documents(
                continuously_eligible,
                full_manifest,
                now=activated + timedelta(days=3),
            )

    def test_priority_fill_uses_spare_slots_across_large_cohorts(
        self,
    ) -> None:
        cases = (
            (3, 77, 1, 2),
            (3, 77, 1, 4),
            (20, 80, 2, 4),
            (40, 80, 2, 4),
        )
        for old_count, new_count, old_apps, limit in cases:
            with self.subTest(
                old=old_count,
                new=new_count,
                limit=limit,
            ):
                app_documents: dict[str, int] = {}
                base, remainder = divmod(old_count, old_apps)
                for index in range(old_apps):
                    app_documents[f"old-{index}"] = (
                        base + int(index < remainder)
                    )
                for index in range(new_count):
                    app_documents[f"new-{index:03d}"] = 1
                state, full_manifest = self._allocated(app_documents)
                old_manifest = deepcopy(full_manifest)
                old_manifest["documents"] = [
                    document
                    for document in old_manifest["documents"]
                    if str(document["app_key"]).startswith("old-")
                ]
                provenance = "2026-08-01T00:00:00.000Z"
                for entry in state["documents"].values():
                    entry["published"] = False
                    entry["published_at"] = provenance
                start = datetime(2026, 8, 29, tzinfo=timezone.utc)
                publisher.pending_state.migrate_legacy_pending_windows(
                    state,
                    old_manifest,
                    daily_limit=limit,
                    migrated_at=publisher.utc_timestamp(start),
                )
                publisher.pending_state.migrate_legacy_pending_windows(
                    state,
                    full_manifest,
                    daily_limit=limit,
                    migrated_at=publisher.utc_timestamp(
                        start + timedelta(days=1)
                    ),
                )
                documents = {
                    document["canonical_url"]: document
                    for document in full_manifest["documents"]
                }
                now = start + timedelta(days=1)
                days = 0
                while True:
                    pending_urls = [
                        canonical
                        for canonical, entry in state["documents"].items()
                        if entry.get("published") is not True
                    ]
                    if not pending_urls:
                        break
                    pending_apps = {
                        state["documents"][canonical]["app_key"]
                        for canonical in pending_urls
                    }
                    old_pending_apps = {
                        app
                        for app in pending_apps
                        if str(app).startswith("old-")
                    }
                    new_pending = any(
                        str(app).startswith("new-")
                        for app in pending_apps
                    )
                    publisher.pending_state.audit_pending_documents(
                        state,
                        full_manifest,
                        now=now,
                    )
                    selected = publisher.reserve_daily_batch(
                        state,
                        full_manifest,
                        day=now.date().isoformat(),
                        limit=limit,
                        now=publisher.utc_timestamp(now),
                    )
                    self.assertEqual(
                        min(limit, len(pending_apps)),
                        len(selected),
                    )
                    selected_apps = {
                        document["app_key"] for document in selected
                    }
                    self.assertEqual(
                        min(limit, len(old_pending_apps)),
                        len(selected_apps & old_pending_apps),
                    )
                    if (
                        new_pending
                        and len(old_pending_apps) < limit
                    ):
                        self.assertTrue(
                            any(
                                str(app).startswith("new-")
                                for app in selected_apps
                            )
                        )
                    for document in selected:
                        self._complete(
                            state,
                            dict(documents[document["canonical_url"]]),
                        )
                    days += 1
                    now += timedelta(days=1)
                expected_days = (
                    old_count + new_count + limit - 1
                ) // limit
                self.assertEqual(expected_days, days)


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
            now=self.NOW + timedelta(minutes=1),
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
                direct = attribution.direct_app_store_urls(
                    record["textContent"]
                )
                self.assertEqual(1, len(direct))
                self.assertEqual(
                    attribution.PRIMARY_QUERY, direct[0].query
                )
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

    def test_legacy_published_record_is_stable_for_thirty_days(self) -> None:
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
        document = manifest["documents"][0]
        canonical = document["canonical_url"]
        entry = state["documents"][canonical]
        key = (publisher.DOCUMENT_COLLECTION, entry["rkey"])
        legacy_text = attribution.legacy_text_content(
            document["text_content"],
            app_id=document["app_store_id"],
            mode=document["legacy_app_store_link"],
        )
        client.records[key]["value"]["textContent"] = legacy_text
        entry["record_hash"] = publisher.record_hash(
            client.records[key]["value"]
        )
        entry["published_hash"] = (
            attribution.legacy_document_content_hash(document)
        )
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        ledger_before = deepcopy(state["daily"])
        rotation_before = deepcopy(state["rotation"])
        puts_before = len(client.puts)

        result: dict[str, object] = {}
        for offset in range(1, 31):
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
                now=self.NOW + timedelta(days=offset),
            )
            self.assertEqual([], result["selected_urls"])

        final_state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(puts_before, len(client.puts))
        self.assertEqual([canonical], result["legacy_unattributed"])
        self.assertEqual([], result["selected_urls"])
        self.assertEqual(ledger_before, final_state["daily"])
        self.assertEqual(rotation_before, final_state["rotation"])
        self.assertEqual(
            legacy_text, client.records[key]["value"]["textContent"]
        )
        self.assertEqual(
            attribution.legacy_document_content_hash(document),
            final_state["documents"][canonical]["published_hash"],
        )

    def test_remote_attribution_strip_waits_for_next_daily_slot(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest({"alpha": 1})
        day_28 = datetime(2026, 7, 28, 14, tzinfo=timezone.utc)
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
            now=day_28,
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        document = manifest["documents"][0]
        canonical = document["canonical_url"]
        entry = state["documents"][canonical]
        key = (publisher.DOCUMENT_COLLECTION, entry["rkey"])
        client.records[key]["value"]["textContent"] = (
            attribution.legacy_text_content(
                document["text_content"],
                app_id=document["app_store_id"],
                mode=document["legacy_app_store_link"],
            )
        )
        document_puts_before = len(
            [
                item
                for item in client.puts
                if item[0] == publisher.DOCUMENT_COLLECTION
            ]
        )

        same_day = publisher.run(
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
            now=day_28 + timedelta(hours=1),
        )

        pending = json.loads(state_path.read_text(encoding="utf-8"))
        pending_entry = pending["documents"][canonical]
        self.assertEqual([], same_day["selected_urls"])
        self.assertFalse(pending_entry["published"])
        self.assertEqual(document["content_hash"], pending_entry["published_hash"])
        self.assertEqual(
            publisher.ATTRIBUTION_REPAIR_REASON,
            pending_entry["repair_reason"],
        )
        self.assertEqual("2026-07-28", pending_entry["repair_after_day"])
        self.assertNotIn("at_uri", pending_entry)
        self.assertEqual(
            document_puts_before,
            len(
                [
                    item
                    for item in client.puts
                    if item[0] == publisher.DOCUMENT_COLLECTION
                ]
            ),
        )

        next_day = publisher.run(
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
            now=day_28 + timedelta(days=1),
        )
        stable = publisher.run(
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
            now=day_28 + timedelta(days=2),
        )

        repaired = json.loads(state_path.read_text(encoding="utf-8"))
        repaired_entry = repaired["documents"][canonical]
        document_puts = [
            item
            for item in client.puts
            if item[0] == publisher.DOCUMENT_COLLECTION
        ]
        self.assertEqual([canonical], next_day["selected_urls"])
        self.assertEqual(1, next_day["documents_changed"])
        self.assertEqual([], stable["selected_urls"])
        self.assertEqual(document_puts_before + 1, len(document_puts))
        self.assertEqual(entry["rkey"], document_puts[-1][1])
        self.assertTrue(repaired_entry["published"])
        self.assertEqual(document["content_hash"], repaired_entry["published_hash"])
        self.assertNotIn("repair_reason", repaired_entry)
        self.assertEqual(
            attribution.PRIMARY_QUERY,
            attribution.direct_app_store_urls(
                client.records[key]["value"]["textContent"]
            )[0].query,
        )

    def test_four_stripped_documents_drain_two_per_day(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest(
            {"alpha": 1, "beta": 1, "gamma": 1, "delta": 1}
        )
        day_28 = datetime(2026, 7, 28, 14, tzinfo=timezone.utc)
        for offset in (0, 1):
            publisher.run(
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
                now=day_28 + timedelta(days=offset),
            )

        state = json.loads(state_path.read_text(encoding="utf-8"))
        for document in manifest["documents"]:
            entry = state["documents"][document["canonical_url"]]
            key = (publisher.DOCUMENT_COLLECTION, entry["rkey"])
            client.records[key]["value"]["textContent"] = (
                attribution.legacy_text_content(
                    document["text_content"],
                    app_id=document["app_store_id"],
                    mode=document["legacy_app_store_link"],
                )
            )
        document_puts_before = len(
            [
                item
                for item in client.puts
                if item[0] == publisher.DOCUMENT_COLLECTION
            ]
        )

        deferred = publisher.run(
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
            now=day_28 + timedelta(days=1, hours=1),
        )
        pending = json.loads(state_path.read_text(encoding="utf-8"))
        pending_audit = publisher.pending_state.audit_pending_documents(
            pending,
            manifest,
            now=day_28 + timedelta(days=1, hours=1),
        )

        self.assertEqual([], deferred["selected_urls"])
        self.assertEqual(
            4, pending_audit["counts"]["attribution_repair_deferred"]
        )
        self.assertEqual(
            {2},
            {
                entry[publisher.ATTRIBUTION_REPAIR_BACKLOG_FIELD]
                for entry in pending["documents"].values()
            },
        )
        self.assertEqual(
            document_puts_before,
            len(
                [
                    item
                    for item in client.puts
                    if item[0] == publisher.DOCUMENT_COLLECTION
                ]
            ),
        )

        first_drain = publisher.run(
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
            now=day_28 + timedelta(days=2),
        )
        half_drained = json.loads(state_path.read_text(encoding="utf-8"))
        half_audit = publisher.pending_state.audit_pending_documents(
            half_drained,
            manifest,
            now=day_28 + timedelta(days=2),
        )
        second_drain = publisher.run(
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
            now=day_28 + timedelta(days=3),
        )
        final_state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(2, len(first_drain["selected_urls"]))
        self.assertEqual(2, half_audit["counts"]["attribution_repair_pending"])
        self.assertEqual(2, len(second_drain["selected_urls"]))
        self.assertTrue(
            all(
                entry["published"] is True
                for entry in final_state["documents"].values()
            )
        )
        self.assertTrue(
            all(
                publisher.pending_state.pending_kind(entry) is None
                for entry in final_state["documents"].values()
            )
        )
        self.assertEqual(
            document_puts_before + 4,
            len(
                [
                    item
                    for item in client.puts
                    if item[0] == publisher.DOCUMENT_COLLECTION
                ]
            ),
        )

    def test_four_ordinary_republishes_drain_two_per_day(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        client = FakeRepoClient(self.DID)
        manifest = fixture_manifest(
            {"alpha": 1, "beta": 1, "gamma": 1, "delta": 1}
        )
        day_28 = datetime(2026, 7, 28, 14, tzinfo=timezone.utc)
        for offset in (0, 1):
            publisher.run(
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
                now=day_28 + timedelta(days=offset),
            )
        updated = deepcopy(manifest)
        for document in updated["documents"]:
            document["description"] += " Updated."
            document["content_hash"] = generator.document_content_hash(
                document
            )
        document_puts_before = len(
            [
                item
                for item in client.puts
                if item[0] == publisher.DOCUMENT_COLLECTION
            ]
        )

        first_drain = publisher.run(
            updated,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=2,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=day_28 + timedelta(days=2),
        )
        half_drained = json.loads(state_path.read_text(encoding="utf-8"))
        half_audit = publisher.pending_state.audit_pending_documents(
            half_drained,
            updated,
            now=day_28 + timedelta(days=2),
        )
        second_drain = publisher.run(
            updated,
            state_path=state_path,
            contract_path=contract_path,
            well_known_path=well_known_path,
            limit=2,
            publish=True,
            environment=self.ENV,
            client_factory=lambda _handle, _password: client,
            expected_did=self.DID,
            tid_generator=self.deterministic_tids(),
            now=day_28 + timedelta(days=3),
        )
        final_state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(2, len(first_drain["selected_urls"]))
        self.assertEqual(2, half_audit["counts"]["ordinary_republish"])
        self.assertIn(
            publisher.PENDING_MIGRATION_FIELD, half_drained
        )
        self.assertTrue(
            all(
                publisher.pending_state.pending_kind(entry)
                == "ordinary_republish"
                and publisher.PENDING_WINDOW_FIELD in entry
                and entry[publisher.PENDING_LIFECYCLE_FIELD]["state"]
                == publisher.pending_state.PENDING_ACTIVE
                for entry in half_drained["documents"].values()
                if entry.get("published") is not True
            )
        )
        self.assertEqual(
            {2},
            {
                entry["republish_backlog_days"]
                for entry in half_drained["documents"].values()
                if entry.get("published") is not True
            },
        )
        self.assertEqual(2, len(second_drain["selected_urls"]))
        self.assertTrue(
            all(
                entry["published"] is True
                for entry in final_state["documents"].values()
            )
        )
        self.assertEqual(
            document_puts_before + 4,
            len(
                [
                    item
                    for item in client.puts
                    if item[0] == publisher.DOCUMENT_COLLECTION
                ]
            ),
        )

    def test_live_108_document_republish_drains_for_all_limits(self) -> None:
        manifest = generator.build_manifest(
            pages=SOCIAL.parents[1],
            site=generator.DEFAULT_SITE,
            max_per_app=3,
            now=self.NOW,
        )
        self.assertEqual(46, manifest["source"]["live_app_count"])
        self.assertEqual(108, len(manifest["documents"]))
        base_dir = self.scratch / "live-base"
        base_dir.mkdir()
        base_state = base_dir / "state.json"
        base_contract = base_dir / "contract.json"
        base_well_known = base_dir / "publication.txt"
        base_client = FakeRepoClient(self.DID)
        current = datetime(2026, 1, 1, 14, tzinfo=timezone.utc)
        for _ in range(40):
            result = publisher.run(
                manifest,
                state_path=base_state,
                contract_path=base_contract,
                well_known_path=base_well_known,
                limit=4,
                publish=True,
                environment=self.ENV,
                client_factory=lambda _handle, _password: base_client,
                expected_did=self.DID,
                tid_generator=self.deterministic_tids(),
                now=current,
            )
            current += timedelta(days=1)
            if not result["selected_urls"]:
                break
        else:
            self.fail("live fixture did not finish its initial publication")
        seeded_state = json.loads(base_state.read_text(encoding="utf-8"))
        self.assertTrue(
            all(
                entry.get("published") is True
                for entry in seeded_state["documents"].values()
            )
        )

        updated = deepcopy(manifest)
        for document in updated["documents"]:
            document["description"] += " Cohort refresh."
            document["content_hash"] = generator.document_content_hash(
                document
            )
        base_state_bytes = base_state.read_bytes()
        base_client_snapshot = deepcopy(base_client)
        start = current + timedelta(days=1)
        for limit in (1, 2, 4):
            case_dir = self.scratch / f"live-limit-{limit}"
            case_dir.mkdir()
            state_path = case_dir / "state.json"
            state_path.write_bytes(base_state_bytes)
            contract_path = case_dir / "contract.json"
            well_known_path = case_dir / "publication.txt"
            client = deepcopy(base_client_snapshot)
            now = start
            deadlines: dict[str, str] = {}
            for _ in range(160):
                before = json.loads(
                    state_path.read_text(encoding="utf-8")
                )
                pending_apps = {
                    document["app_key"]
                    for document in updated["documents"]
                    if (
                        before["documents"][
                            document["canonical_url"]
                        ].get("published")
                        is not True
                        or publisher.attribution_status(
                            document,
                            before["documents"][
                                document["canonical_url"]
                            ].get("published_hash"),
                        )
                        == "stale"
                    )
                }
                if not pending_apps:
                    break
                result = publisher.run(
                    updated,
                    state_path=state_path,
                    contract_path=contract_path,
                    well_known_path=well_known_path,
                    limit=limit,
                    publish=True,
                    environment=self.ENV,
                    client_factory=lambda _handle, _password: client,
                    expected_did=self.DID,
                    tid_generator=self.deterministic_tids(),
                    now=now,
                )
                self.assertEqual([], result["errors"])
                self.assertEqual(
                    min(limit, len(pending_apps)),
                    len(result["selected_urls"]),
                )
                state = json.loads(
                    state_path.read_text(encoding="utf-8")
                )
                audit = publisher.pending_state.audit_pending_documents(
                    state,
                    updated,
                    now=now,
                )
                self.assertEqual(limit, audit["daily_limit"])
                for detail in audit["documents"]:
                    canonical = detail["canonical_url"]
                    previous = deadlines.get(canonical)
                    if previous is not None:
                        self.assertGreaterEqual(
                            detail["deadline_day"], previous
                        )
                    deadlines[canonical] = detail["deadline_day"]
                now += timedelta(days=1)
            else:
                self.fail(f"live fixture did not drain at limit {limit}")
            final = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertTrue(
                all(
                    entry.get("published") is True
                    and entry.get("published_hash")
                    == document["content_hash"]
                    for document in updated["documents"]
                    for entry in [
                        final["documents"][document["canonical_url"]]
                    ]
                )
            )

    def test_remote_legacy_without_matching_state_hash_fails_closed(self) -> None:
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
        document = manifest["documents"][0]
        canonical = document["canonical_url"]
        entry = state["documents"][canonical]
        key = (publisher.DOCUMENT_COLLECTION, entry["rkey"])
        client.records[key]["value"]["textContent"] = (
            attribution.legacy_text_content(
                document["text_content"],
                app_id=document["app_store_id"],
                mode=document["legacy_app_store_link"],
            )
        )
        puts_before = len(client.puts)
        for label, published_hash in (
            ("missing", None),
            ("mismatch", "f" * 64),
        ):
            candidate = deepcopy(state)
            candidate_entry = candidate["documents"][canonical]
            if published_hash is None:
                candidate_entry.pop("published_hash", None)
            else:
                candidate_entry["published_hash"] = published_hash
            state_path.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.subTest(label=label), self.assertRaisesRegex(
                publisher.StateError,
                "lacks explicit durable migration evidence",
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
                    now=self.NOW + timedelta(days=1),
                )

        self.assertEqual(puts_before, len(client.puts))

    def test_migrated_legacy_remote_is_republished_without_downgrade(
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
        state = json.loads(state_path.read_text(encoding="utf-8"))
        document = manifest["documents"][0]
        canonical = document["canonical_url"]
        entry = state["documents"][canonical]
        key = (publisher.DOCUMENT_COLLECTION, entry["rkey"])
        client.records[key]["value"]["textContent"] = (
            attribution.legacy_text_content(
                document["text_content"],
                app_id=document["app_store_id"],
                mode=document["legacy_app_store_link"],
            )
        )
        for field in (
            "at_uri",
            "cid",
            "record_hash",
            "published_hash",
            "last_verified_at",
            "updated_at",
            *publisher.ATTRIBUTION_REPAIR_FIELDS,
            publisher.ATTRIBUTION_REPAIR_BACKLOG_FIELD,
            *publisher.ORDINARY_REPUBLISH_FIELDS,
            publisher.PENDING_WINDOW_FIELD,
            publisher.PENDING_LIFECYCLE_FIELD,
        ):
            entry.pop(field, None)
        entry["published"] = False
        state.pop(publisher.PENDING_MIGRATION_FIELD, None)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

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
            now=self.NOW + timedelta(days=1),
        )
        repaired = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual([canonical], result["selected_urls"])
        self.assertEqual(1, result["documents_changed"])
        self.assertTrue(repaired["documents"][canonical]["published"])
        self.assertEqual(
            document["content_hash"],
            repaired["documents"][canonical]["published_hash"],
        )
        self.assertEqual(
            attribution.PRIMARY_QUERY,
            attribution.direct_app_store_urls(
                client.records[key]["value"]["textContent"]
            )[0].query,
        )

    def test_prepared_future_record_keeps_reservation_and_full_query(self) -> None:
        state_path, contract_path, well_known_path = self.paths()
        manifest = fixture_manifest({"alpha": 1})
        prepared, selected, _plan = publisher._prepare_plan(
            publisher.empty_state(),
            manifest,
            generator=self.deterministic_tids(),
            day="2026-07-27",
            limit=1,
            timestamp="2026-07-27T14:00:00.000Z",
            publish=False,
        )
        state_path.write_text(
            json.dumps(prepared, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        ledger_before = deepcopy(prepared["daily"])
        rotation_before = deepcopy(prepared["rotation"])
        client = FakeRepoClient(self.DID)

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
            now=self.NOW,
        )

        document_puts = [
            item
            for item in client.puts
            if item[0] == publisher.DOCUMENT_COLLECTION
        ]
        final_state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["canonical_url"] for item in selected],
            result["selected_urls"],
        )
        self.assertEqual(ledger_before, final_state["daily"])
        self.assertEqual(rotation_before, final_state["rotation"])
        self.assertEqual(1, len(document_puts))
        direct = attribution.direct_app_store_urls(
            document_puts[0][2]["textContent"]
        )
        self.assertEqual(1, len(direct))
        self.assertEqual(attribution.PRIMARY_QUERY, direct[0].query)

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
        with self.assertRaises(publisher.ConfigurationError):
            publisher.run(
                fixture_manifest(),
                state_path=state_path,
                contract_path=contract_path,
                well_known_path=well_known_path,
                limit=True,
                publish=False,
                now=self.NOW,
            )

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
