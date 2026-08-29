#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hermetic tests for per-app public Telegram exposure receipts.

Nothing here touches the network: every "public GET" is a fake fetcher and no
Telegram POST is ever issued. The real published messages 204/205 are only used
as a recorded HTML shape fixture, never as the production source of truth.
"""

import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import portfolio_daily
import social_post_common as common
import telegram_public_receipts as receipts


CHANNEL = common.TELEGRAM_PUBLIC_CHANNEL
RUN_ID = "33249592430"
SHA = "a" * 40
PUBLISHED_AT = dt.datetime(2026, 8, 29, 11, 15, 29, tzinfo=dt.timezone.utc)
OBSERVED_AT = dt.datetime(2026, 8, 29, 11, 16, 0, tzinfo=dt.timezone.utc)


def schedule_env(**overrides):
    env = {
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_REPOSITORY": "alice51849/ios-app-guide",
        "GITHUB_RUN_ID": RUN_ID,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": SHA,
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_WORKFLOW_REF": (
            "alice51849/ios-app-guide/.github/workflows/"
            "portfolio-daily.yml@refs/heads/main"
        ),
    }
    env.update(overrides)
    return {key: value for key, value in env.items() if value is not None}


def sample_apps(count=46):
    categories = ("kids", "photo-utility", "productivity", "finance", "travel")
    return [
        portfolio_daily.PublicApp(
            key=f"sample{index}",
            app_id=str(7000000000 + index),
            name=f"Sample App {index:02d}",
            category=categories[index % len(categories)],
        )
        for index in range(1, count + 1)
    ]


def message_html(channel, message_id, text, published_at=PUBLISHED_AT,
                 extra_blocks=0):
    body = text.replace("\n", "<br/>")
    block = (
        '<div class="tgme_widget_message text_not_supported_wrap '
        f'js-widget_message" data-post="{channel}/{message_id}" '
        f'data-post-id="{message_id}">'
        '<div class="tgme_widget_message_bubble">'
        f'<div class="tgme_widget_message_text js-message_text" dir="auto">'
        f"{body}</div>"
        '<div class="tgme_widget_message_info">'
        f'<time datetime="{published_at.isoformat()}"></time></div>'
        "</div>"
    )
    duplicate = block * extra_blocks
    return f"<html><body>{block}{duplicate}</body></html>"


class FakeTelegram:
    """A recorded public channel: GET only, never a POST."""

    def __init__(self, pages, published_at=PUBLISHED_AT):
        self.pages = dict(pages)
        self.published_at = published_at
        self.calls = []

    def fetcher(self, channel, message_id):
        self.calls.append((channel, int(message_id)))
        entry = self.pages.get(int(message_id))
        if entry is None:
            raise receipts.PublicEvidenceError(
                f"https://t.me/{channel}/{message_id}: HTTP 404"
            )
        text, published_at, status = entry
        return receipts.parse_public_message(
            message_html(channel, message_id, text, published_at),
            channel,
            message_id,
            status=status,
        )


def publication(apps=None, channel=CHANNEL, published_at=PUBLISHED_AT,
                status=200, mutate=None):
    """Build a faithful digest plus the public pages that would prove it."""
    apps = sample_apps() if apps is None else apps
    messages = portfolio_daily.telegram_messages(apps)
    published = [
        portfolio_daily.PublishedMessage(200 + index, message)
        for index, message in enumerate(messages, start=1)
    ]
    pages = {}
    for index, item in enumerate(published):
        text = item.message.text
        if mutate is not None:
            text = mutate(index, text)
        pages[item.message_id] = (text, published_at, status)
    return apps, published, FakeTelegram(pages, published_at)


class DisclosureContractTests(unittest.TestCase):
    def test_every_digest_message_carries_the_first_party_disclosure(self):
        apps = sample_apps()
        messages = portfolio_daily.telegram_messages(apps)
        self.assertGreater(len(messages), 1)
        for message in messages:
            self.assertTrue(receipts.verify_disclosure(message.text))
            for line in receipts.DISCLOSURE_LINES:
                self.assertIn(line, message.text)

    def test_disclosure_is_first_party_and_not_an_independent_ranking(self):
        block = receipts.disclosure_block()
        self.assertIn("Lumi Studio", block)
        self.assertIn("自行開發並發行", block)
        self.assertIn("the app developer", block)
        self.assertIn("not an independent ranking", block)
        self.assertIn("不是第三方評比或排行榜", block)

    def test_digest_never_invents_price_rank_rating_or_downloads(self):
        combined = "\n".join(
            message.text
            for message in portfolio_daily.telegram_messages(sample_apps())
        )
        for claim in (
            "★",
            "⭐",
            "$",
            "免費下載排行",
            "第一名",
            "#1",
            "best app",
            "downloads",
            "評價",
        ):
            self.assertNotIn(claim, combined)

    def test_missing_disclosure_is_rejected(self):
        self.assertFalse(receipts.verify_disclosure("no disclosure here"))
        self.assertFalse(
            receipts.verify_disclosure(receipts.DISCLOSURE_LINES[0])
        )


class CountableSourceTests(unittest.TestCase):
    def test_natural_schedule_run_is_countable(self):
        source = receipts.source_context(
            schedule_env(), content_digest="sha256:" + "0" * 64
        )
        self.assertTrue(source["countable_event"])
        self.assertEqual("schedule", source["event_name"])
        self.assertEqual(RUN_ID, source["run_id"])
        self.assertEqual(
            f"https://github.com/alice51849/ios-app-guide/actions/runs/{RUN_ID}",
            source["run_url"],
        )

    def test_manual_dispatch_is_never_countable(self):
        for event in (
            "workflow_dispatch",
            "workflow_run",
            "repository_dispatch",
            "push",
            "pull_request",
            "",
        ):
            with self.subTest(event=event):
                with self.assertRaises(receipts.NonCountableSource):
                    receipts.source_context(
                        schedule_env(GITHUB_EVENT_NAME=event),
                        content_digest="sha256:" + "0" * 64,
                    )

    def test_manual_dispatch_cannot_mint_a_receipt_even_when_public(self):
        apps, published, telegram = publication()
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "receipts.json"
            pending_path = Path(directory) / "pending.json"
            with self.assertRaises(receipts.NonCountableSource):
                portfolio_daily.record_public_receipts(
                    apps,
                    published,
                    env=schedule_env(GITHUB_EVENT_NAME="workflow_dispatch"),
                    store_path=store_path,
                    pending_path=pending_path,
                    observed_at=OBSERVED_AT,
                    source_started_at=PUBLISHED_AT,
                    fetcher=telegram.fetcher,
                )
            # A non-countable trigger must not even open the public channel.
            self.assertEqual([], telegram.calls)
            self.assertFalse(store_path.exists())
            self.assertFalse(pending_path.exists())

    def test_incomplete_source_identity_is_rejected(self):
        for override in (
            {"GITHUB_REPOSITORY": "not-a-repo"},
            {"GITHUB_RUN_ID": ""},
            {"GITHUB_RUN_ID": "abc"},
            {"GITHUB_SHA": "short"},
            {"GITHUB_RUN_ATTEMPT": "x"},
            {"GITHUB_SERVER_URL": "http://evil.example"},
            {"GITHUB_WORKFLOW_REF": "someone-else/repo/.github/x.yml@main"},
        ):
            with self.subTest(override=override):
                with self.assertRaises(receipts.NonCountableSource):
                    receipts.source_context(
                        schedule_env(**override),
                        content_digest="sha256:" + "0" * 64,
                    )

    def test_workflow_content_digest_tracks_publisher_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "a.py"
            target.write_text("one", encoding="utf-8")
            first = receipts.workflow_content_digest(["a.py"], root=root)
            target.write_text("two", encoding="utf-8")
            second = receipts.workflow_content_digest(["a.py"], root=root)
        self.assertNotEqual(first, second)
        self.assertRegex(first, r"^sha256:[0-9a-f]{64}$")

    def test_missing_publisher_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(receipts.ReceiptError):
                receipts.workflow_content_digest(
                    ["absent.py"], root=Path(directory)
                )


class PublicEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store_path = Path(self.directory.name) / "receipts.json"

    def record(self, apps, published, telegram, **kwargs):
        params = {
            "env": schedule_env(),
            "store_path": self.store_path,
            "observed_at": OBSERVED_AT,
            "source_started_at": PUBLISHED_AT,
            "fetcher": telegram.fetcher,
        }
        params.update(kwargs)
        return portfolio_daily.record_public_receipts(
            apps, published, **params
        )

    def test_schedule_success_mints_one_receipt_per_app(self):
        apps, published, telegram = publication()
        store, minted = self.record(apps, published, telegram)
        self.assertEqual(46, len(minted))
        self.assertEqual(46, store["countable_app_count"])
        self.assertEqual(46, store["countable_receipt_count"])
        self.assertEqual(
            {app.app_id for app in apps},
            {item["app"]["app_store_id"] for item in minted},
        )
        self.assertEqual(
            [(CHANNEL, 201), (CHANNEL, 202)], telegram.calls
        )
        by_id = {item["app"]["app_store_id"]: item for item in minted}
        sample = by_id[apps[0].app_id]
        self.assertTrue(sample["countable"])
        self.assertEqual("schedule", sample["source"]["event_name"])
        self.assertEqual(RUN_ID, sample["source"]["run_id"])
        self.assertEqual(SHA, sample["source"]["workflow_sha"])
        self.assertRegex(
            sample["source"]["workflow_content_digest"],
            r"^sha256:[0-9a-f]{64}$",
        )
        self.assertEqual(200, sample["public_check"]["status"])
        self.assertEqual("GET", sample["public_check"]["method"])
        self.assertEqual(
            "2026-08-29T11:16:00Z", sample["public_check"]["observed_at"]
        )
        self.assertTrue(sample["public_check"]["disclosure_verified"])
        self.assertEqual(31, sample["public_check"]["freshness_seconds"])
        self.assertEqual(
            f"https://t.me/{CHANNEL}/201",
            sample["publication"]["message_url"],
        )
        self.assertEqual(2, sample["publication"]["message_count"])
        self.assertEqual("2026-08-29", sample["publication"]["publication_day"])
        self.assertEqual("zh-Hant", sample["app"]["locale"])
        self.assertEqual(apps[0].category, sample["app"]["intent"])
        self.assertEqual(apps[0].key, sample["app"]["app_key"])
        self.assertIn("?pt=", sample["app"]["campaign_app_store_url"])

    def test_receipts_bind_every_dynamic_app_identity_without_hardcoding(self):
        apps = sample_apps(11)
        apps, published, telegram = publication(apps=apps)
        _, minted = self.record(apps, published, telegram)
        self.assertEqual(11, len(minted))
        self.assertEqual(
            {app.app_id for app in apps},
            {item["app"]["app_store_id"] for item in minted},
        )
        self.assertEqual(
            {app.key for app in apps},
            {item["app"]["app_key"] for item in minted},
        )

    def test_two_shards_lose_and_repeat_no_app(self):
        apps, published, telegram = publication()
        self.assertEqual(2, len(published))
        _, minted = self.record(apps, published, telegram)
        observed = [item["app"]["app_store_id"] for item in minted]
        self.assertEqual(len(observed), len(set(observed)))
        self.assertEqual(
            sorted(app.app_id for app in apps), sorted(observed)
        )
        first = {
            item["app"]["app_store_id"]
            for item in minted
            if item["publication"]["message_id"] == 201
        }
        second = {
            item["app"]["app_store_id"]
            for item in minted
            if item["publication"]["message_id"] == 202
        }
        self.assertEqual(set(), first & second)
        self.assertEqual({app.app_id for app in apps}, first | second)

    def test_dropped_shard_fails_closed(self):
        apps, published, telegram = publication()
        with self.assertRaises(receipts.ReceiptError):
            self.record(apps, published[:1], telegram)
        self.assertFalse(
            json.loads(self.store_path.read_text(encoding="utf-8"))["receipts"]
        )

    def test_repeated_shard_fails_closed(self):
        apps, published, telegram = publication()
        duplicated = list(published) + [
            portfolio_daily.PublishedMessage(203, published[0].message)
        ]
        telegram.pages[203] = telegram.pages[201]
        with self.assertRaises(receipts.ReceiptError):
            self.record(apps, duplicated, telegram)

    def test_public_404_fails_closed(self):
        apps, published, telegram = publication()
        telegram.pages.pop(202)
        with self.assertRaises(receipts.PublicEvidenceError):
            self.record(apps, published, telegram)
        store = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual([], store["receipts"])
        self.assertEqual(1, len(store["non_countable"]))
        self.assertFalse(store["non_countable"][0]["countable"])
        self.assertIn("404", store["non_countable"][0]["reason"])

    def test_public_timeout_fails_closed(self):
        apps, published, _ = publication()

        def fetcher(channel, message_id):
            raise receipts.PublicEvidenceError("timed out after 4 attempts")

        with self.assertRaises(receipts.PublicEvidenceError):
            portfolio_daily.record_public_receipts(
                apps,
                published,
                env=schedule_env(),
                store_path=self.store_path,
                observed_at=OBSERVED_AT,
                source_started_at=PUBLISHED_AT,
                fetcher=fetcher,
            )
        store = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual([], store["receipts"])
        self.assertIn("timed out", store["non_countable"][0]["reason"])

    def test_non_200_status_fails_closed(self):
        apps, published, telegram = publication(status=302)
        with self.assertRaises(receipts.PublicEvidenceError):
            self.record(apps, published, telegram)

    def test_body_missing_one_app_link_fails_closed(self):
        apps, _, _ = publication()
        victim = apps[0].appstore_url(
            portfolio_daily.PLATFORM_CAMPAIGNS["telegram"]
        )
        apps, published, telegram = publication(
            apps=apps,
            mutate=lambda index, text: text.replace(victim, "https://example.com"),
        )
        with self.assertRaises(receipts.PublicEvidenceError):
            self.record(apps, published, telegram)

    def test_body_renaming_an_app_fails_closed(self):
        apps, _, _ = publication()
        apps, published, telegram = publication(
            apps=apps,
            mutate=lambda index, text: text.replace(
                apps[0].name, "Somebody Else App"
            ),
        )
        with self.assertRaises(receipts.PublicEvidenceError):
            self.record(apps, published, telegram)

    def test_body_repeating_a_campaign_url_fails_closed(self):
        apps, _, _ = publication()
        victim = apps[0].appstore_url(
            portfolio_daily.PLATFORM_CAMPAIGNS["telegram"]
        )
        apps, published, telegram = publication(
            apps=apps,
            mutate=lambda index, text: (
                text + f"\n{victim}" if index == 0 else text
            ),
        )
        with self.assertRaises(receipts.PublicEvidenceError):
            self.record(apps, published, telegram)

    def test_missing_disclosure_in_public_body_fails_closed(self):
        apps, published, telegram = publication(
            mutate=lambda index, text: text.replace(
                receipts.DISCLOSURE_LINES[1], ""
            )
        )
        with self.assertRaises(receipts.PublicEvidenceError) as caught:
            self.record(apps, published, telegram)
        self.assertIn("disclosure", str(caught.exception))

    def test_future_publication_fails_closed(self):
        future = OBSERVED_AT + dt.timedelta(minutes=5)
        apps, published, telegram = publication(published_at=future)
        with self.assertRaises(receipts.PublicEvidenceError) as caught:
            self.record(apps, published, telegram, source_started_at=future)
        self.assertIn("future", str(caught.exception))

    def test_stale_publication_outside_freshness_window_fails_closed(self):
        stale = OBSERVED_AT - dt.timedelta(hours=25)
        apps, published, telegram = publication(published_at=stale)
        with self.assertRaises(receipts.PublicEvidenceError) as caught:
            self.record(apps, published, telegram, source_started_at=stale)
        self.assertIn("older than", str(caught.exception))

    def test_message_from_an_earlier_run_fails_closed(self):
        apps, published, telegram = publication(
            published_at=OBSERVED_AT - dt.timedelta(hours=6)
        )
        with self.assertRaises(receipts.PublicEvidenceError) as caught:
            self.record(
                apps,
                published,
                telegram,
                source_started_at=OBSERVED_AT - dt.timedelta(minutes=2),
            )
        self.assertIn("predates source run", str(caught.exception))

    def test_wrong_channel_block_fails_closed(self):
        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.parse_public_message(
                message_html("SomeoneElse", 201, "hello"), CHANNEL, 201
            )

    def test_duplicate_public_blocks_fail_closed(self):
        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.parse_public_message(
                message_html(CHANNEL, 201, "hello", extra_blocks=1),
                CHANNEL,
                201,
            )

    def test_public_body_without_a_timestamp_fails_closed(self):
        body = message_html(CHANNEL, 201, "hello").replace(
            f'<time datetime="{PUBLISHED_AT.isoformat()}"></time>', ""
        )
        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.parse_public_message(body, CHANNEL, 201)

    def test_empty_public_body_fails_closed(self):
        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.parse_public_message("", CHANNEL, 201)


class IdempotencyAndRetentionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store_path = Path(self.directory.name) / "receipts.json"

    def record(self, apps, published, telegram, **kwargs):
        params = {
            "env": schedule_env(),
            "store_path": self.store_path,
            "observed_at": OBSERVED_AT,
            "source_started_at": PUBLISHED_AT,
            "fetcher": telegram.fetcher,
        }
        params.update(kwargs)
        return portfolio_daily.record_public_receipts(
            apps, published, **params
        )

    def test_replaying_the_same_run_is_byte_identical(self):
        apps, published, telegram = publication()
        self.record(apps, published, telegram)
        first = self.store_path.read_bytes()
        self.record(
            apps,
            published,
            telegram,
            observed_at=OBSERVED_AT + dt.timedelta(minutes=3),
        )
        self.assertEqual(first, self.store_path.read_bytes())
        store = json.loads(first.decode("utf-8"))
        self.assertEqual(46, store["countable_receipt_count"])

    def test_a_second_run_attempt_adds_distinct_receipts(self):
        apps, published, telegram = publication()
        self.record(apps, published, telegram)
        store, minted = self.record(
            apps,
            published,
            telegram,
            env=schedule_env(GITHUB_RUN_ATTEMPT="2"),
        )
        self.assertEqual(46, len(minted))
        self.assertEqual(92, store["countable_receipt_count"])
        self.assertEqual(46, store["countable_app_count"])

    def test_receipt_ids_are_deterministic_and_unique(self):
        apps, published, telegram = publication()
        _, minted = self.record(apps, published, telegram)
        ids = [item["receipt_id"] for item in minted]
        self.assertEqual(len(ids), len(set(ids)))
        for value in ids:
            self.assertRegex(value, r"^sha256:[0-9a-f]{64}$")

    def test_history_is_bounded_by_publication_day(self):
        store = receipts.empty_store(now=OBSERVED_AT)
        for day in range(receipts.MAX_PUBLICATION_DAYS + 6):
            published_at = PUBLISHED_AT - dt.timedelta(days=day)
            batch = [
                {
                    "receipt_id": f"sha256:{day:064d}"[:71] + str(index % 10),
                    "countable": True,
                    "app": {"app_store_id": str(index)},
                    "publication": {
                        "message_id": 200 + index,
                        "published_at": receipts._iso(published_at),
                        "publication_day": published_at.date().isoformat(),
                    },
                }
                for index in range(3)
            ]
            store = receipts.merge_receipts(store, batch, now=OBSERVED_AT)
        days = {
            item["publication"]["publication_day"]
            for item in store["receipts"]
        }
        self.assertEqual(receipts.MAX_PUBLICATION_DAYS, len(days))
        self.assertLessEqual(len(store["receipts"]), receipts.MAX_RECEIPTS)

    def test_failure_history_is_bounded(self):
        store = receipts.empty_store(now=OBSERVED_AT)
        for index in range(receipts.MAX_FAILURES + 20):
            failure = receipts._failure_record(
                reason=f"reason {index}",
                source=None,
                observed_at=OBSERVED_AT,
                channel=CHANNEL,
                message_ids=[index],
            )
            store = receipts.merge_receipts(
                store, [], failures=[failure], now=OBSERVED_AT
            )
        self.assertEqual(
            receipts.MAX_FAILURES, len(store["non_countable"])
        )

    def test_store_is_written_atomically(self):
        apps, published, telegram = publication()
        real_replace = os.replace
        seen = {}

        def replace(source, target):
            seen["source"] = str(source)
            seen["target"] = str(target)
            seen["existed_before"] = Path(target).exists()
            return real_replace(source, target)

        with mock.patch.object(receipts.os, "replace", replace):
            self.record(apps, published, telegram)
        self.assertTrue(seen["source"].endswith(".json.tmp"))
        self.assertEqual(str(self.store_path), seen["target"])
        self.assertFalse(seen["existed_before"])
        self.assertFalse(Path(f"{self.store_path}.tmp").exists())

    def test_store_never_publishes_credentials(self):
        apps, published, telegram = publication()
        secret_env = schedule_env()
        secret_env["TELEGRAM_BOT_TOKEN"] = "123456:" + "A" * 35
        secret_env["TELEGRAM_CHAT_ID"] = "-1004337848676"
        store, _ = self.record(apps, published, telegram, env=secret_env)
        encoded = receipts.serialize(store)
        self.assertNotIn("123456:", encoded)
        self.assertNotIn("-1004337848676", encoded)
        receipts.assert_no_credentials(encoded, env=secret_env)

    def test_a_leaked_credential_blocks_the_write(self):
        env = schedule_env()
        env["TELEGRAM_BOT_TOKEN"] = "123456:" + "A" * 35
        store = receipts.empty_store(now=OBSERVED_AT)
        store["note"] = "token 123456:" + "A" * 35
        with self.assertRaises(receipts.ReceiptError):
            receipts.write_store(store, self.store_path, env=env)
        self.assertFalse(self.store_path.exists())

    def test_public_channel_handle_is_not_treated_as_a_credential(self):
        env = schedule_env()
        env["TELEGRAM_CHAT_ID"] = f"@{CHANNEL}"
        store = receipts.empty_store(now=OBSERVED_AT)
        self.assertTrue(receipts.assert_no_credentials(store, env=env))

    def test_unsupported_schema_version_is_rejected(self):
        self.store_path.write_text(
            json.dumps({"schema_version": 99, "contract": receipts.CONTRACT_ID}),
            encoding="utf-8",
        )
        with self.assertRaises(receipts.ReceiptError):
            receipts.load_store(self.store_path)


class PublicFetchTransportTests(unittest.TestCase):
    def test_404_is_not_retried_and_fails_closed(self):
        calls = []

        def opener(request, timeout=None):
            calls.append(request.full_url)
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", {}, io.BytesIO(b"gone")
            )

        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.fetch_public_message(
                CHANNEL, 201, opener=opener, sleeper=lambda _: None
            )
        self.assertEqual(1, len(calls))

    def test_timeout_is_retried_then_fails_closed(self):
        calls = []

        def opener(request, timeout=None):
            calls.append(request.full_url)
            raise urllib.error.URLError(TimeoutError("timed out"))

        with self.assertRaises(receipts.PublicEvidenceError):
            receipts.fetch_public_message(
                CHANNEL,
                201,
                opener=opener,
                sleeper=lambda _: None,
                attempts=3,
                retry_delays=(0, 0),
            )
        self.assertEqual(3, len(calls))

    def test_successful_public_get_uses_the_embed_url(self):
        text = "\n".join(receipts.DISCLOSURE_LINES)
        payload = message_html(CHANNEL, 201, text).encode("utf-8")
        seen = {}

        class Response:
            status = 200
            url = f"https://t.me/{CHANNEL}/201"

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size=None):
                return payload

        def opener(request, timeout=None):
            seen["url"] = request.full_url
            seen["method"] = request.get_method()
            return Response()

        message = receipts.fetch_public_message(
            CHANNEL, 201, opener=opener, sleeper=lambda _: None
        )
        self.assertEqual(
            f"https://t.me/{CHANNEL}/201?embed=1&mode=tme", seen["url"]
        )
        self.assertEqual("GET", seen["method"])
        self.assertEqual(200, message.status)
        self.assertTrue(receipts.verify_disclosure(message.text))

    def test_no_telegram_post_is_ever_issued_by_verification(self):
        apps, published, telegram = publication()
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(
                urllib.request, "urlopen", side_effect=AssertionError("network")
            ):
                portfolio_daily.record_public_receipts(
                    apps,
                    published,
                    env=schedule_env(),
                    store_path=Path(directory) / "receipts.json",
                    observed_at=OBSERVED_AT,
                    source_started_at=PUBLISHED_AT,
                    fetcher=telegram.fetcher,
                )


class RecordedRealMessageShapeTests(unittest.TestCase):
    """The published 204/205 shape is a fixture, never a production source."""

    RECORDED = (
        '<div class="tgme_widget_message text_not_supported_wrap '
        'js-widget_message" data-post="LumiApps2026/204" '
        'data-view="eyJjIjotNDMzNzg0ODY3NiwicCI6MjA0fQ" '
        'data-post-id="204">'
        '<div class="tgme_widget_message_bubble">'
        '<div class="tgme_widget_message_text js-message_text" dir="auto">'
        "✨ 每日全 App 精選｜46 款｜第 1/2 則<br/><br/>"
        "今天已公開的 App 一次看，依需求挑選：<br/>"
        "• 親子學習｜Aim990<br/>  "
        '<a href="https://apps.apple.com/app/id6784974530?pt=118326163&amp;'
        'ct=soc_tg_guide&amp;mt=8" target="_blank" rel="noopener">'
        "https://apps.apple.com/app/id6784974530?pt=118326163&amp;"
        "ct=soc_tg_guide&amp;mt=8</a></div>"
        '<div class="tgme_widget_message_footer">'
        '<time datetime="2026-08-29T11:15:29+00:00"></time></div>'
        "</div></div>"
    )

    def test_recorded_public_html_parses_into_verifiable_text(self):
        message = receipts.parse_public_message(
            self.RECORDED, "LumiApps2026", 204
        )
        self.assertEqual(204, message.message_id)
        self.assertEqual(
            dt.datetime(2026, 8, 29, 11, 15, 29, tzinfo=dt.timezone.utc),
            message.published_at,
        )
        self.assertIn(
            "• 親子學習｜Aim990\n  https://apps.apple.com/app/id6784974530"
            "?pt=118326163&ct=soc_tg_guide&mt=8",
            message.text,
        )

    def test_already_published_digests_are_not_countable_evidence(self):
        # 204/205 predate the disclosure contract, so they must stay
        # non-countable instead of being grandfathered into the contract.
        message = receipts.parse_public_message(
            self.RECORDED, "LumiApps2026", 204
        )
        self.assertFalse(receipts.verify_disclosure(message.text))

    def test_shipped_store_starts_empty_and_awaits_a_natural_receipt(self):
        store = receipts.load_store(receipts.STORE_PATH)
        self.assertEqual(receipts.SCHEMA_VERSION, store["schema_version"])
        self.assertEqual(["schedule"], store["countable_events"])
        self.assertEqual([], store["receipts"])
        self.assertEqual(0, store["countable_receipt_count"])
        self.assertTrue(receipts.SCHEMA_PATH.is_file())

    def test_receipt_store_stays_separate_from_the_intent_catalog(self):
        catalog = receipts.REPO_ROOT / (
            "data/lumi-studio-publisher-search-intent-catalog.json"
        )
        self.assertTrue(catalog.is_file())
        self.assertNotEqual(catalog, receipts.STORE_PATH)
        payload = json.loads(catalog.read_text(encoding="utf-8"))
        self.assertNotIn("receipts", payload)
        store = receipts.load_store(receipts.STORE_PATH)
        self.assertNotIn("records", store)

    def test_intent_catalog_cells_are_planned_coverage_not_exposure(self):
        catalog = json.loads(
            (
                receipts.REPO_ROOT
                / "data/lumi-studio-publisher-search-intent-catalog.json"
            ).read_text(encoding="utf-8")
        )
        # 46 apps x 50 locales of planned catalogue coverage must never be
        # mistaken for observed public exposure.
        self.assertEqual(50, len(catalog["locales"]))
        self.assertEqual(
            len(catalog["records"]),
            len(catalog["locales"])
            * len({record["app_store_id"] for record in catalog["records"]}),
        )
        for record in catalog["records"][:5]:
            self.assertNotIn("message_url", record)
            self.assertNotIn("public_check", record)

    def test_receipt_store_is_not_listed_in_the_open_data_catalog(self):
        index = (receipts.REPO_ROOT / "data" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("telegram-public-receipts", index)


class PendingBatchAndCommitPathTests(unittest.TestCase):
    """The committed store must survive a concurrent writer on main."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.store_path = root / "data" / "telegram-public-receipts.json"
        self.pending_path = root / "runner-temp" / "pending.json"

    def mint(self, **kwargs):
        apps, published, telegram = publication()
        params = {
            "env": schedule_env(),
            "store_path": self.store_path,
            "pending_path": self.pending_path,
            "observed_at": OBSERVED_AT,
            "source_started_at": PUBLISHED_AT,
            "fetcher": telegram.fetcher,
        }
        params.update(kwargs)
        return portfolio_daily.record_public_receipts(apps, published, **params)

    def test_pending_batch_is_written_for_the_commit_step(self):
        self.mint()
        pending = receipts.load_pending(self.pending_path)
        self.assertEqual(46, len(pending["receipts"]))
        self.assertEqual([], pending["non_countable"])
        self.assertEqual(receipts.SCHEMA_VERSION, pending["schema_version"])

    def test_pending_path_is_taken_from_the_workflow_environment(self):
        env = schedule_env(
            TELEGRAM_RECEIPT_PENDING=str(self.pending_path)
        )
        self.mint(env=env, pending_path=None)
        self.assertTrue(self.pending_path.is_file())

    def test_merge_pending_recovers_a_receipt_clobbered_by_remote_main(self):
        self.mint()
        # Simulate `git merge -X theirs` restoring the remote store.
        receipts.write_store(
            receipts.empty_store(now=OBSERVED_AT), self.store_path
        )
        merged = receipts.merge_pending(self.store_path, self.pending_path)
        self.assertEqual(46, merged["countable_receipt_count"])
        self.assertEqual(46, merged["countable_app_count"])

    def test_merge_pending_is_idempotent_across_retry_attempts(self):
        self.mint()
        first = receipts.merge_pending(self.store_path, self.pending_path)
        first_bytes = self.store_path.read_bytes()
        second = receipts.merge_pending(self.store_path, self.pending_path)
        self.assertEqual(first_bytes, self.store_path.read_bytes())
        self.assertEqual(
            first["countable_receipt_count"],
            second["countable_receipt_count"],
        )

    def test_failed_verification_still_records_a_pending_reason(self):
        apps, published, telegram = publication()
        telegram.pages.pop(202)
        with self.assertRaises(receipts.PublicEvidenceError):
            portfolio_daily.record_public_receipts(
                apps,
                published,
                env=schedule_env(),
                store_path=self.store_path,
                pending_path=self.pending_path,
                observed_at=OBSERVED_AT,
                source_started_at=PUBLISHED_AT,
                fetcher=telegram.fetcher,
            )
        pending = receipts.load_pending(self.pending_path)
        self.assertEqual([], pending["receipts"])
        self.assertEqual(1, len(pending["non_countable"]))
        merged = receipts.merge_pending(self.store_path, self.pending_path)
        self.assertEqual(0, merged["countable_receipt_count"])
        self.assertEqual(1, len(merged["non_countable"]))

    def test_corrupt_pending_batch_fails_closed(self):
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(receipts.ReceiptError):
            receipts.merge_pending(self.store_path, self.pending_path)

    def test_cli_merge_pending_reports_a_summary(self):
        self.mint()
        receipts.write_store(
            receipts.empty_store(now=OBSERVED_AT), self.store_path
        )
        exit_code = receipts.main(
            [
                "--store",
                str(self.store_path),
                "--merge-pending",
                str(self.pending_path),
            ]
        )
        self.assertEqual(0, exit_code)
        store = receipts.load_store(self.store_path)
        self.assertEqual(46, store["countable_receipt_count"])

    def test_cli_require_fresh_day_fails_without_proof(self):
        self.assertEqual(
            1,
            receipts.main(
                [
                    "--store",
                    str(receipts.STORE_PATH),
                    "--require-fresh-day",
                    "--expected-apps",
                    "46",
                ]
            ),
        )


class WorkflowContractTests(unittest.TestCase):
    WORKFLOW = (
        receipts.REPO_ROOT / ".github" / "workflows" / "portfolio-daily.yml"
    )

    @classmethod
    def setUpClass(cls):
        cls.text = cls.WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_keeps_a_natural_schedule_trigger(self):
        self.assertIn("schedule:", self.text)
        self.assertIn("cron:", self.text)

    def test_receipt_commit_is_restricted_to_schedule_events(self):
        self.assertIn(
            "if: always() && github.event_name == 'schedule'", self.text
        )

    def test_receipt_commit_uses_the_existing_remote_first_merge(self):
        self.assertIn(".github/scripts/remote-first-publish.sh", self.text)
        self.assertIn("remote_first_publish reconcile_public_receipts", self.text)
        self.assertIn("--merge-pending", self.text)

    def test_receipt_commit_cleans_the_tree_before_merging_origin(self):
        # `git merge` refuses to integrate origin on a dirty tree, so the
        # store written during publishing must be committed first.
        commit_at = self.text.index('git add -- "$TELEGRAM_RECEIPT_STORE"')
        merge_at = self.text.index("source .github/scripts/remote-first-publish.sh")
        self.assertLess(commit_at, merge_at)

    def test_workflow_runs_the_fail_closed_receipt_tests(self):
        self.assertIn(
            "python3 .github/scripts/test_telegram_public_receipts.py",
            self.text,
        )

    def test_receipt_batch_path_is_resolved_at_runtime_outside_the_repo(self):
        # `runner.temp` is unavailable to job-level env, so the batch path must
        # be exported from $RUNNER_TEMP at runtime instead.
        self.assertIn(
            'echo "TELEGRAM_RECEIPT_PENDING=$RUNNER_TEMP/', self.text
        )
        self.assertNotIn("TELEGRAM_RECEIPT_PENDING: ${{ runner.temp", self.text)

    def test_receipt_commit_fetches_real_history_for_the_merge(self):
        self.assertIn("fetch-depth: 0", self.text)

    def test_workflow_can_write_the_public_receipt_store(self):
        self.assertIn("contents: write", self.text)

    def test_publisher_digest_is_covered_by_the_content_digest(self):
        digest = receipts.workflow_content_digest()
        self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")


class SchemaConformanceTests(unittest.TestCase):
    """The shipped schema and the minted receipts must never drift apart.

    Deliberately dependency-free: the publisher workflow runs on a bare
    interpreter, so a skipped `jsonschema` test would be no gate at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            receipts.SCHEMA_PATH.read_text(encoding="utf-8")
        )

    def resolve(self, node):
        ref = node.get("$ref")
        if not ref:
            return node
        target = self.schema
        for part in ref.lstrip("#/").split("/"):
            target = target[part]
        return target

    def check(self, node, value, path="$"):
        import re as _re

        node = self.resolve(node)
        types = node.get("type")
        if types is not None:
            allowed = [types] if isinstance(types, str) else list(types)
            python_types = {
                "object": dict,
                "array": list,
                "string": str,
                "integer": int,
                "boolean": bool,
                "null": type(None),
            }
            self.assertTrue(
                any(
                    isinstance(value, python_types[name])
                    and not (name == "integer" and isinstance(value, bool))
                    for name in allowed
                ),
                f"{path}: {value!r} is not {allowed}",
            )
        if "const" in node:
            self.assertEqual(node["const"], value, f"{path}: const mismatch")
        if "enum" in node:
            self.assertIn(value, node["enum"], f"{path}: enum mismatch")
        if "pattern" in node and isinstance(value, str):
            self.assertIsNotNone(
                _re.search(node["pattern"], value),
                f"{path}: {value!r} does not match {node['pattern']}",
            )
        if isinstance(value, str) and "minLength" in node:
            self.assertGreaterEqual(len(value), node["minLength"], path)
        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in node:
                self.assertGreaterEqual(value, node["minimum"], path)
            if "maximum" in node:
                self.assertLessEqual(value, node["maximum"], path)
        if isinstance(value, dict):
            for key in node.get("required", []):
                self.assertIn(key, value, f"{path}: missing {key}")
            properties = node.get("properties", {})
            if node.get("additionalProperties") is False:
                self.assertEqual(
                    set(),
                    set(value) - set(properties),
                    f"{path}: unexpected properties",
                )
            for key, child in value.items():
                if key in properties:
                    self.check(properties[key], child, f"{path}.{key}")
        if isinstance(value, list) and "items" in node:
            for index, child in enumerate(value):
                self.check(node["items"], child, f"{path}[{index}]")

    def test_shipped_store_conforms_to_the_shipped_schema(self):
        self.check(
            self.schema, receipts.load_store(receipts.STORE_PATH), "store"
        )

    def test_minted_receipts_conform_to_the_shipped_schema(self):
        apps, published, telegram = publication()
        with tempfile.TemporaryDirectory() as directory:
            store, minted = portfolio_daily.record_public_receipts(
                apps,
                published,
                env=schedule_env(),
                store_path=Path(directory) / "receipts.json",
                observed_at=OBSERVED_AT,
                source_started_at=PUBLISHED_AT,
                fetcher=telegram.fetcher,
            )
        self.assertEqual(46, len(minted))
        self.check(self.schema, store, "store")

    def test_failure_records_conform_to_the_shipped_schema(self):
        apps, published, telegram = publication()
        telegram.pages.pop(202)
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "receipts.json"
            with self.assertRaises(receipts.PublicEvidenceError):
                portfolio_daily.record_public_receipts(
                    apps,
                    published,
                    env=schedule_env(),
                    store_path=store_path,
                    observed_at=OBSERVED_AT,
                    source_started_at=PUBLISHED_AT,
                    fetcher=telegram.fetcher,
                )
            store = receipts.load_store(store_path)
        self.assertEqual(1, len(store["non_countable"]))
        self.check(self.schema, store, "store")

    def test_schema_only_allows_the_schedule_event(self):
        event = self.schema["$defs"]["receipt"]["properties"]["source"][
            "properties"
        ]["event_name"]
        self.assertEqual(["schedule"], event["enum"])
        self.assertEqual(
            sorted(receipts.COUNTABLE_EVENTS),
            self.schema["properties"]["countable_events"]["items"]["enum"],
        )


class SharedCoverageHelperTests(unittest.TestCase):

    def test_coverage_diff_reports_missing_unexpected_and_duplicates(self):
        self.assertEqual(
            (["a"], ["c"], ["b"]),
            common.coverage_diff(["a", "b"], ["b", "b", "c"]),
        )

    def test_portfolio_and_receipts_share_one_coverage_rule(self):
        self.assertIs(portfolio_daily.coverage_diff, common.coverage_diff)
        self.assertIs(receipts.coverage_diff, common.coverage_diff)


if __name__ == "__main__":
    unittest.main()
