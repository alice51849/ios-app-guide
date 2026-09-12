from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import GEO, Response, SOURCE, make_deployment, write_json
import owned_app_feeds as feeds
import owned_feed_delivery as delivery
import owned_feed_receipts as receipts
from websub_config import WEBSUB_HUBS


def fixture_record(protocol):
    topic = feeds.url("en-US/rss.xml" if protocol == "rsscloud" else "en-US/feed.xml")
    endpoint = delivery.RSSCLOUD_PING_URL if protocol == "rsscloud" else WEBSUB_HUBS[0]
    task = {
        **{key: "a" * (40 if key in {"source_sha", "engine_source_sha"} else 64)
           for key in receipts.BINDING_FIELDS},
        "protocol": protocol, "endpoint": endpoint, "topic": topic, "content_sha256": "b" * 64,
    }
    body = receipts.request_body(protocol, [topic])
    attempt = {
        "attempt_id": "c" * 32, "started_at": "2026-09-01T00:00:00Z", "topics": [topic],
        "request_body": body, "request_sha256": feeds.sha256(body.encode("ascii")),
    }
    response = delivery.response_record(
        protocol, endpoint, [topic], 204 if protocol == "websub" else 200,
        "" if protocol == "websub" else '{"success":true,"msg":"fixture ACK only"}',
        observed_at="2026-09-01T00:00:01Z",
    )
    record = receipts.make_receipt(task, attempt, response)
    record["fixture"] = True
    record["receipt_id"] = feeds.digest({k: v for k, v in record.items() if k != "receipt_id"})
    return record


class ReceiptSchemaTests(unittest.TestCase):
    def test_versioned_json_schema_and_fixtures_are_valid(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = feeds.read_json(GEO / "owned_feed_receipt.schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for protocol, name in (("websub", "websub-204"), ("rsscloud", "rsscloud-200")):
            record = feeds.read_json(GEO / "tests/fixtures/owned_feed_receipts" / f"{name}.json")
            self.assertEqual(fixture_record(protocol), record)
            validator.validate(record)
            receipts.validate_receipt(record)
            self.assertFalse(record["subscriber_delivery_verified"])
            self.assertFalse(record["indexing_verified"])

    def test_workflow_success_cannot_replace_missing_http_observation(self):
        record = fixture_record("websub")
        record.pop("response")
        record["workflow_success"] = True
        with self.assertRaises(ValueError):
            receipts.validate_receipt(record)

    def test_ack_body_or_generation_tampering_is_rejected(self):
        for target, field, value in (
            ("response", "ack_body", "wrong"),
            ("response", "ack_body_sha256", "0" * 64),
            ("request", "source_sha", "0" * 40),
            ("request", "deployment_sha256", "0" * 64),
            ("request", "feed_sha256", "0" * 64),
        ):
            record = fixture_record("websub")
            record[target][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                receipts.validate_receipt(record)

    def test_fixtures_are_never_real_ack_authorization(self):
        record = fixture_record("websub")
        task = {
            **record["request"], "content_sha256": record["request"]["feed_sha256"],
            **{name: record[name] for name in ("protocol", "endpoint", "topic")},
        }
        self.assertFalse(receipts.is_current(record, task))
        self.assertFalse(receipts.same_content(record, task))

    def test_every_source_deployment_generation_and_feed_binding_is_required(self):
        record = fixture_record("websub")
        record.pop("fixture")
        record["receipt_id"] = feeds.digest({k: v for k, v in record.items() if k != "receipt_id"})
        task = {
            **record["request"], "content_sha256": record["request"]["feed_sha256"],
            **{name: record[name] for name in ("protocol", "endpoint", "topic")},
        }
        self.assertTrue(receipts.is_current(record, task))
        for name in (*receipts.BINDING_FIELDS, "content_sha256"):
            changed = {**task, name: "0" * len(task[name])}
            with self.subTest(binding=name):
                self.assertFalse(receipts.is_current(record, changed))

    def test_false_delivery_or_index_claim_is_invalid_even_with_a_new_checksum(self):
        for name in ("subscriber_delivery_verified", "indexing_verified"):
            record = fixture_record("websub")
            record[name] = True
            record["receipt_id"] = feeds.digest({k: v for k, v in record.items() if k != "receipt_id"})
            with self.subTest(claim=name), self.assertRaises(ValueError):
                receipts.validate_receipt(record)


class ReceiptOutboxTests(unittest.TestCase):
    def setUp(self):
        self.root = GEO / ".owned-feed-test-work" / uuid.uuid4().hex
        self.pages = self.root / "site"
        self.pages.mkdir(parents=True)
        self.state = self.root / "state.json"
        make_deployment(self.pages)
        self.payloads = {
            feeds.url("en-US/feed.xml"): b"<feed>one</feed>",
            feeds.url("en-US/rss.xml"): b"<rss>one</rss>",
            feeds.url("bn-BD/feed.xml"): b"<feed>retained content</feed>",
        }
        self.index_raw = b'{"fixture":true}'
        self.current = {
            "generation_digest": "d" * 64, "manifest_sha256": feeds.sha256(self.index_raw),
            "topics": {
                topic: {
                    "sha256": feeds.sha256(raw), "format": "rss" if topic.endswith("rss.xml") else "atom",
                    "locale": "bn-BD" if "bn-BD" in topic else "en-US",
                    "notification_eligible": "bn-BD" not in topic, "rsscloud": topic.endswith("rss.xml"),
                }
                for topic, raw in self.payloads.items()
            },
        }
        self.baseline = dict.fromkeys(self.current["topics"], None)
        self.time = 1788264000.0
        self.sleeps, self.posts, self.responses = [], [], []
        self.inventory_patch = patch.object(delivery, "inventory", side_effect=lambda *a, **kw: copy.deepcopy(self.current))
        self.inventory_patch.start()
        self.network = patch("socket.create_connection", side_effect=AssertionError("Real network forbidden")).start()
        self.transport_patch = patch("urllib.request.urlopen", side_effect=self.post)
        self.transport_patch.start()

    def tearDown(self):
        self.network.assert_not_called()
        self.transport_patch.stop()
        self.inventory_patch.stop()
        patch.stopall()
        shutil.rmtree(self.root)
        if self.root.parent.exists() and not any(self.root.parent.iterdir()):
            self.root.parent.rmdir()

    def post(self, request, timeout=0):
        self.assertEqual("POST", request.get_method())
        self.posts.append((request.full_url, request.data))
        if self.responses:
            result = self.responses.pop(0)
            if isinstance(result, BaseException):
                raise result
            status, body, retry = result
        else:
            status, body, retry = (
                (200, b'{"success":true}', None)
                if request.full_url == delivery.RSSCLOUD_PING_URL else (204, b"", None)
            )
        response = Response(body)
        response.status = status
        response.geturl = lambda: request.full_url
        if retry is not None:
            response.headers["Retry-After"] = retry
        return response

    def get(self, request, timeout=0):
        self.assertEqual("GET", request.get_method())
        if request.full_url == feeds.url(delivery.DEPLOYMENT):
            return Response((self.pages / delivery.DEPLOYMENT).read_bytes())
        if request.full_url == feeds.url(feeds.INDEX):
            return Response(self.index_raw)
        return Response(self.payloads[request.full_url], "application/xml")

    def advance(self, value):
        self.sleeps.append(value)
        self.time += value

    def prepare(self, source=SOURCE):
        return delivery.prepare(self.pages, self.state, source, baseline=self.baseline)

    def deliver(self, protocol="websub", source=SOURCE, **kwargs):
        return delivery.deliver(
            self.pages, self.state, source, protocol, opener=self.get,
            clock=lambda: self.time, sleeper=self.advance, **kwargs,
        )

    def test_204_and_200_are_observed_ack_only_and_reentrant_intents_are_zero(self):
        self.assertEqual(5, self.prepare()["pending_notifications"])
        self.assertEqual(4, self.deliver()["accepted"])
        self.assertEqual(1, self.deliver("rsscloud")["accepted"])
        state = delivery.read_state(self.state)
        self.assertEqual(5, len(state["records"]))
        for record in state["records"].values():
            self.assertEqual("accepted_ack", record["outcome"])
            self.assertFalse(record["subscriber_delivery_verified"])
            self.assertFalse(record["indexing_verified"])
            self.assertEqual(SOURCE, record["request"]["source_sha"])
            self.assertIn("deployment_sha256", record["request"])
            self.assertIn("ack_body", record["response"])
            self.assertEqual(204 if record["protocol"] == "websub" else 200, record["response"]["http_status"])
        count = len(self.posts)
        self.assertEqual(0, self.prepare()["pending_notifications"])
        self.assertEqual(0, self.deliver()["accepted"])
        self.assertEqual(count, len(self.posts))
        self.assertEqual(0o600, self.state.stat().st_mode & 0o777)

    def test_new_source_and_deployment_invalidate_receipts_without_resending_content(self):
        self.prepare()
        self.deliver()
        self.deliver("rsscloud")
        history = copy.deepcopy(delivery.read_state(self.state)["records"])
        source = "f" * 40
        make_deployment(self.pages, source, run="2")
        with self.assertRaisesRegex(ValueError, "source/generation drift"):
            self.deliver(source=source)
        self.assertFalse(delivery.read_state(self.state)["accepted"])
        self.assertEqual(history, delivery.read_state(self.state)["records"])
        result = self.prepare(source)
        self.assertEqual(0, result["pending_notifications"])
        self.assertEqual(0, result["current_generation_acks"])
        self.assertEqual(5, result["historical_content_deduplicated"])
        self.assertEqual(0, result["new_notification_intents"])
        count = len(self.posts)
        self.assertEqual(0, self.deliver(source=source)["accepted"])
        self.assertEqual(count, len(self.posts))

    def test_new_feed_only_creates_missing_topic_intents_and_retains_old_receipts(self):
        self.prepare()
        self.deliver()
        self.deliver("rsscloud")
        old = copy.deepcopy(delivery.read_state(self.state)["records"])
        self.baseline = {url: item["sha256"] for url, item in self.current["topics"].items()}
        topic = feeds.url("en-US/feed.xml")
        self.payloads[topic] = b"<feed>new content</feed>"
        self.current["topics"][topic]["sha256"] = feeds.sha256(self.payloads[topic])
        prepared = self.prepare()
        self.assertEqual(2, prepared["pending_notifications"])
        self.assertEqual(2, prepared["new_notification_intents"])
        before = len(self.posts)
        self.assertEqual(2, self.deliver()["accepted"])
        self.assertEqual(2, len(self.posts) - before)
        self.assertTrue(all(record == delivery.read_state(self.state)["records"][key] for key, record in old.items()))

    def test_partial_live_feed_and_body_mismatch_never_become_ack(self):
        self.prepare()
        self.payloads[feeds.url("bn-BD/feed.xml")] = b"<stale/>"
        with self.assertRaisesRegex(ValueError, "Partial/stale"):
            self.deliver()
        self.assertEqual([], self.posts)
        self.payloads[feeds.url("bn-BD/feed.xml")] = b"<feed>retained content</feed>"
        self.responses = [(204, b"not empty", None)]
        with self.assertRaises(RuntimeError):
            self.deliver()
        state = delivery.read_state(self.state)
        self.assertTrue(any(r["outcome"] == "body_mismatch" for r in state["records"].values()))
        self.assertEqual(2, len(state["accepted"]))

    def test_rsscloud_200_false_or_malformed_body_is_not_accepted(self):
        for body in (
            b'{"success":false}', b'{"success":"true"}', b"not JSON or XML",
            b'{"success":false,"success":true}',
            b'{"success":true,"url":"https://example.org/wrong-topic"}',
        ):
            self.state.unlink(missing_ok=True)
            self.responses = [(200, body, None)]
            self.prepare()
            with self.assertRaises(RuntimeError):
                self.deliver("rsscloud")
            self.assertFalse(delivery.read_state(self.state)["accepted"])

    def test_429_and_500_backoff_is_bounded_and_preserves_http_body(self):
        self.prepare()
        self.responses = [(429, b"rate limited", "2"), (500, b"server error", None), (204, b"", None)]
        self.assertEqual(4, self.deliver()["accepted"])
        self.assertEqual([2, 2], self.sleeps)
        records = list(delivery.read_state(self.state)["records"].values())
        self.assertEqual({429, 500, 204}, {r["response"]["http_status"] for r in records})
        self.assertTrue(any(r["response"]["ack_body"] == "rate limited" for r in records))
        count = len(self.posts)
        self.deliver()
        self.assertEqual(count, len(self.posts))

    def test_timeout_retries_only_missing_provider_and_topic_after_recovery(self):
        self.prepare()
        self.responses = [TimeoutError("mock timeout")] * 3
        with self.assertRaises(RuntimeError):
            self.deliver()
        state = delivery.read_state(self.state)
        self.assertEqual(2, len(state["accepted"]))
        acknowledged = {r["endpoint"] for r in state["records"].values() if r["accepted_ack"]}
        count = len(self.posts)
        self.advance(600)
        prepared = self.prepare()
        self.assertEqual(0, prepared["new_notification_intents"])
        self.assertEqual(3, prepared["retry_intents"])
        self.assertEqual(2, self.deliver()["accepted"])
        self.assertTrue(all(endpoint not in acknowledged for endpoint, _ in self.posts[count:]))

    def test_request_body_hash_mismatch_is_recorded_but_not_authorization(self):
        self.prepare()
        def forged(protocol, endpoint, topics):
            result = delivery.response_record(protocol, endpoint, topics, 204, "")
            result["request_sha256"] = "0" * 64
            return result
        with self.assertRaises(RuntimeError):
            self.deliver(sender=forged)
        state = delivery.read_state(self.state)
        self.assertFalse(state["accepted"])
        self.assertEqual({"body_mismatch"}, {r["outcome"] for r in state["records"].values()})

    def test_crash_after_durable_ack_write_recovers_without_resending_that_batch(self):
        self.prepare()
        replace = delivery.os.replace
        crashed = False
        def crash(source, target):
            nonlocal crashed
            candidate = feeds.read_json(Path(source))
            if candidate["accepted"] and not crashed:
                crashed = True
                raise OSError("mock crash before atomic rename")
            return replace(source, target)
        with patch.object(delivery.os, "replace", side_effect=crash):
            with self.assertRaises(OSError):
                self.deliver()
        self.assertEqual(1, len(self.posts))
        self.assertTrue(list(self.root.glob(".state.json.writing-*")))
        self.prepare()
        self.assertEqual(2, len(delivery.read_state(self.state)["accepted"]))
        self.assertEqual(2, self.deliver()["accepted"])
        self.assertEqual(2, len(self.posts))

    def test_crash_without_persisted_ack_is_indeterminate_not_fabricated_delivery(self):
        self.prepare()
        self.responses = [KeyboardInterrupt("mock process crash")]
        with self.assertRaises(KeyboardInterrupt):
            self.deliver()
        self.assertTrue(delivery.read_state(self.state)["in_flight"])
        self.prepare()
        state = delivery.read_state(self.state)
        self.assertFalse(state["accepted"])
        self.assertEqual({"indeterminate"}, {r["outcome"] for r in state["records"].values()})
        self.assertEqual(4, self.deliver()["accepted"])

    def test_unbound_v2_receipts_are_preserved_as_history_not_new_generation_acks(self):
        write_json(self.state, {
            "schema": "lumi.owned-feed-delivery/v2",
            "accepted": {"old": {"content_sha256": "a" * 64, "receipt": {"http_status": 204}}},
            "pending": {},
        })
        self.assertEqual(5, self.prepare()["pending_notifications"])
        state = delivery.read_state(self.state)
        self.assertEqual(1, len(state["legacy_history"]))
        self.assertFalse(state["accepted"])
        self.assertFalse(state["records"])

    def test_concurrent_process_is_blocked_by_single_flight_owner(self):
        self.prepare()
        with delivery.locked_state(self.state):
            code = (
                "import sys; from pathlib import Path; import owned_feed_delivery as d\n"
                "try:\n with d.locked_state(Path(sys.argv[1])): pass\n"
                "except RuntimeError:\n sys.exit(77)\n"
            )
            child = subprocess.run(
                [sys.executable, "-c", code, str(self.state)],
                env={**__import__("os").environ, "PYTHONPATH": str(GEO)},
                capture_output=True, timeout=30,
            )
        self.assertEqual(77, child.returncode, child.stderr.decode())
        self.assertEqual([], self.posts)

    def test_private_state_corruption_fails_closed_without_rewriting_history(self):
        self.prepare()
        self.deliver()
        raw = self.state.read_bytes()
        state = feeds.decode(raw)
        record = next(iter(state["records"].values()))
        record["response"]["ack_body"] = "corrupted"
        self.state.write_bytes(feeds.json_bytes(state))
        corrupt = self.state.read_bytes()
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(corrupt, self.state.read_bytes())


if __name__ == "__main__":
    unittest.main()
