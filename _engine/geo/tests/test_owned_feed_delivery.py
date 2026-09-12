from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import (
    FeedFixture, Response, SOURCE, feeds, make_deployment, write_json,
)
import owned_feed_delivery as delivery
from websub_config import WEBSUB_HUBS


class DeliveryTests(FeedFixture):
    def setUp(self):
        super().setUp()
        self.current = delivery.inventory(self.pages)
        self.baseline = dict.fromkeys(self.current["topics"], None)
        self.sent = []
        self.time = 1788264000.0

    def prepare(self, **kwargs):
        return delivery.prepare(
            self.pages, self.state, SOURCE, baseline=self.baseline, **kwargs
        )

    def sender(self, protocol, endpoint, topics):
        self.sent.extend((protocol, endpoint, topic) for topic in topics)
        return delivery.response_record(
            protocol, endpoint, topics, 204 if protocol == "websub" else 200,
            "" if protocol == "websub" else '{"success":true}',
            observed_at=datetime.fromtimestamp(self.time, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def advance(self, seconds):
        self.time += seconds

    def deliver(self, protocol="websub", **kwargs):
        self.advance(600)
        return delivery.deliver(
            self.pages, self.state, SOURCE, protocol,
            opener=kwargs.pop("opener", self.opener),
            sender=kwargs.pop("sender", self.sender), clock=lambda: self.time,
            sleeper=self.advance, **kwargs,
        )

    def test_initial_notifications_cover_49_markets_but_never_bengali(self):
        result = self.prepare()
        self.assertEqual(147 * len(WEBSUB_HUBS) + 49, result["pending_notifications"])
        self.deliver()
        self.deliver("rsscloud")
        self.assertEqual(343, len(self.sent))
        self.assertFalse(any("/bn-BD/" in topic for _, _, topic in self.sent))
        state = feeds.read_json(self.state)
        self.assertEqual({}, state["pending"])
        self.assertEqual(0o600, self.state.stat().st_mode & 0o777)

    def test_acknowledged_content_is_not_resent_on_reentry_or_new_source_commit(self):
        self.prepare()
        self.deliver()
        self.deliver("rsscloud")
        before = list(self.sent)
        self.assertEqual(0, self.prepare()["pending_notifications"])
        self.assertEqual(0, self.deliver()["accepted"])
        new_source = "f" * 40
        make_deployment(self.pages, new_source, run="2")
        result = delivery.prepare(
            self.pages, self.state, new_source, baseline=self.baseline
        )
        self.assertEqual(0, result["pending_notifications"])
        for protocol in ("websub", "rsscloud"):
            result = delivery.deliver(
                self.pages, self.state, new_source, protocol,
                opener=Mock(side_effect=AssertionError("Unchanged feeds need no readback")),
                sender=self.sender,
            )
            self.assertEqual(0, result["accepted"])
        self.assertEqual(before, self.sent)

    def test_unchanged_deployed_bytes_do_not_seed_new_notifications(self):
        result = delivery.prepare(
            self.pages, self.state, SOURCE,
            baseline={url: item["sha256"] for url, item in self.current["topics"].items()},
        )
        self.assertEqual(0, result["pending_notifications"])
        self.assertEqual(0, self.deliver()["accepted"])
        self.assertEqual([], self.sent)

    def test_prepare_retry_retains_unacknowledged_content_after_it_is_live(self):
        self.prepare()
        result = delivery.prepare(
            self.pages, self.state, SOURCE,
            baseline={url: item["sha256"] for url, item in self.current["topics"].items()},
        )
        self.assertEqual(343, result["pending_notifications"])
        self.assertEqual(294, self.deliver()["accepted"])

    def test_partial_deployment_in_an_unnotified_bengali_feed_blocks_all_posts(self):
        self.prepare()
        def incomplete(request, timeout=0):
            if request.full_url == feeds.url("bn-BD/feed.xml"):
                return Response(b"<stale/>", "application/xml")
            return self.opener(request, timeout)
        with self.assertRaisesRegex(ValueError, "Partial/stale"):
            self.deliver(opener=incomplete)
        self.assertEqual([], self.sent)
        self.assertEqual(343, len(feeds.read_json(self.state)["pending"]))

    def test_wrong_live_manifest_or_content_type_blocks_all_posts(self):
        self.prepare()
        for wrong in ("manifest", "html", "charset"):
            def bad(request, timeout=0):
                if request.full_url == feeds.url(feeds.INDEX):
                    if wrong == "manifest":
                        return Response(b"{}")
                    if wrong == "html":
                        return Response(b"<html>error</html>", "text/html")
                    return Response((self.pages / feeds.INDEX).read_bytes(), "application/json; charset=iso-8859-1")
                return self.opener(request, timeout)
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                self.deliver(opener=bad)
        self.assertEqual([], self.sent)

    def test_previous_or_changed_execution_generation_cannot_authorize_posts(self):
        self.prepare()
        make_deployment(self.pages, SOURCE, run="2")
        with self.assertRaisesRegex(ValueError, "Outbox source/generation drift"):
            self.deliver()
        self.assertEqual([], self.sent)
        self.prepare()
        self.assertEqual(294, self.deliver()["accepted"])

    def test_local_source_bytes_drift_after_prepare_blocks_every_provider(self):
        self.prepare()
        path = self.pages / "en-US/rss.xml"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Partial or mixed"):
            self.deliver()
        self.assertEqual([], self.sent)

    def test_live_generation_switch_during_readback_blocks_posts(self):
        self.prepare()
        observations = 0
        def switched(request, timeout=0):
            nonlocal observations
            if request.full_url == feeds.url(delivery.DEPLOYMENT):
                observations += 1
                if observations > 1:
                    return Response(b'{"generation":"different"}')
            return self.opener(request, timeout)
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.deliver(opener=switched)
        self.assertEqual([], self.sent)

    def test_a_failed_hub_does_not_block_the_other_hub_or_duplicate_its_ack(self):
        self.prepare()
        failed = WEBSUB_HUBS[0]
        def one_failure(protocol, endpoint, topics):
            if endpoint == failed:
                raise RuntimeError("Fixture hub is unavailable")
            return self.sender(protocol, endpoint, topics)
        with self.assertRaisesRegex(RuntimeError, "remain pending"):
            self.deliver(sender=one_failure)
        self.assertEqual(147, len(self.sent))
        self.assertTrue(all(endpoint == WEBSUB_HUBS[1] for _, endpoint, _ in self.sent))
        self.prepare()
        self.assertEqual(147, self.deliver()["accepted"])
        self.assertEqual(49, self.deliver("rsscloud")["accepted"])
        self.assertEqual(343, len(set(self.sent)))
        self.assertEqual(343, len(self.sent))

    def test_receipts_are_saved_before_the_next_batch_can_fail(self):
        self.prepare()
        calls = 0
        def intermittent(protocol, endpoint, topics):
            nonlocal calls
            calls += 1
            if calls > 1:
                saved = feeds.read_json(self.state)
                self.assertEqual(25, len(saved["accepted"]))
                raise RuntimeError("Fixture transport failed")
            return self.sender(protocol, endpoint, topics)
        with self.assertRaises(RuntimeError):
            self.deliver(sender=intermittent)
        self.assertEqual(25, len(feeds.read_json(self.state)["accepted"]))
        self.prepare()
        self.assertEqual(269, self.deliver()["accepted"])
        self.assertEqual(294, len(set(self.sent)))

    def test_unacknowledged_provider_response_is_not_counted_as_success(self):
        self.prepare()
        with self.assertRaisesRegex(RuntimeError, "remain pending"):
            self.deliver(sender=lambda *args: {"http_status": 500})
        state = feeds.read_json(self.state)
        self.assertFalse(state["accepted"])
        self.assertEqual(343, len(state["pending"]))

    def test_reentrant_owner_and_corrupt_state_fail_closed(self):
        self.prepare()
        with delivery.locked_state(self.state):
            with self.assertRaisesRegex(RuntimeError, "already has an owner"):
                self.prepare()
        write_json(self.state, {"schema": delivery.SCHEMA, "accepted": [], "pending": {}})
        with self.assertRaisesRegex(ValueError, "Invalid durable"):
            self.prepare()

    def test_prepare_requires_valid_deployment_binding_and_full_baseline(self):
        with self.assertRaisesRegex(ValueError, "full source SHA"):
            delivery.prepare(self.pages, self.state, "short", baseline=self.baseline)
        with self.assertRaisesRegex(ValueError, "paired source"):
            delivery.prepare(self.pages, self.state, "b" * 40, baseline=self.baseline)
        self.baseline.pop(next(iter(self.baseline)))
        with self.assertRaisesRegex(ValueError, "exact current topics"):
            self.prepare()

    def test_manifest_readback_baseline_is_get_only_and_content_addressed(self):
        actual = delivery.baseline_hashes(self.current, opener=self.opener)
        self.assertEqual(
            {url: item["sha256"] for url, item in self.current["topics"].items()}, actual
        )
        def missing(request, timeout=0):
            raise urllib.error.HTTPError(request.full_url, 404, "Fixture absent", {}, None)
        self.assertTrue(all(value is None for value in delivery.baseline_hashes(
            self.current, opener=missing
        ).values()))

    def test_legacy_feeds_share_deduplication_and_bengali_is_still_excluded(self):
        import notify_websub
        for relative in notify_websub.FEED_FILES:
            path = self.pages / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}" if path.suffix == ".json" else "<feed/>")
        for locale in feeds.OFFICIAL_LOCALES:
            path = self.pages / notify_websub.LOCALIZED_ATOM_DIR / f"{locale}.atom.xml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<feed/>")
        current = delivery.inventory(self.pages, include_legacy=True)
        self.assertEqual(204, len(current["topics"]))
        wanted = delivery.tasks(current)
        self.assertEqual(450, len(wanted))
        self.assertFalse(any("bn-BD" in item["topic"] for item in wanted.values()))
        same = {url: item["sha256"] for url, item in current["topics"].items()}
        self.assertEqual(0, delivery.prepare(
            self.pages, self.state, SOURCE, include_legacy=True, baseline=same
        )["pending_notifications"])

    def test_notify_cli_needs_explicit_execute_and_never_defaults_to_a_post(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            delivery.main([
                "notify", "--pages-dir", str(self.pages), "--state", str(self.state),
                "--source-sha", SOURCE, "--protocol", "websub",
            ])
        self.assertFalse(self.state.exists())

    def test_unowned_topics_and_path_escape_are_rejected(self):
        for topic in (
            "https://example.org/feed.json",
            feeds.SITE + "/%2e%2e/%2e%2e/secret",
            feeds.SITE + "/en-US/feed.json?track=1",
        ):
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                delivery.local_path(self.pages, topic)


if __name__ == "__main__":
    unittest.main()
