from email.message import Message
import io
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
import urllib.error
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import owned_feed_delivery as delivery


class OwnedFeedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.root = (Path(__file__).resolve().parents[2] / ".growth-runtime"
                     / "owned-feed-delivery-tests" / str(uuid.uuid4()))
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.state = self.root / "state.json"
        self.sha = "a" * 40
        self.rss = delivery.SITE + "/fr-FR/rss.xml"
        self.atom = delivery.SITE + "/fr-FR/feed.xml"
        self.current = {
            "generation_digest": "b" * 64,
            "topics": {
                self.rss: {"sha256": "c" * 64, "format": "rss", "rsscloud": True},
                self.atom: {"sha256": "d" * 64, "format": "atom", "rsscloud": False},
            },
        }
        self.patch_inventory = mock.patch.object(delivery, "inventory", return_value=self.current)
        self.patch_inventory.start()
        self.addCleanup(self.patch_inventory.stop)
        self.patch_verify = mock.patch.object(delivery, "verify")
        self.verify = self.patch_verify.start()
        self.addCleanup(self.patch_verify.stop)
        self.web = mock.patch.object(delivery.notify_websub, "notify", side_effect=self.ack)
        self.web_call = self.web.start()
        self.addCleanup(self.web.stop)
        self.rss_mock = mock.patch.object(delivery.notify_rsscloud, "ping", side_effect=self.ack)
        self.rss_call = self.rss_mock.start()
        self.addCleanup(self.rss_mock.stop)

    @staticmethod
    def ack(*args, receipt_sink=None, **kwargs):
        receipt_sink({
            "http_status": 200, "accepted_at": "2026-09-11T00:00:00Z",
            "request_sha256": "e" * 64, "response_sha256": "f" * 64,
        })

    def prepare(self, baseline=None, sha=None):
        return delivery.prepare(
            self.root, self.state, sha or self.sha,
            baseline=baseline or {topic: None for topic in self.current["topics"]},
        )

    def test_only_changed_content_is_enqueued(self):
        same = {topic: spec["sha256"] for topic, spec in self.current["topics"].items()}
        result = self.prepare(same)
        self.assertEqual(0, result["pending_notifications"])
        result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertTrue(result["unchanged"])
        self.web_call.assert_not_called()
        self.verify.assert_not_called()

    def test_first_deployment_receipts_are_content_addressed_and_private(self):
        self.assertEqual(5, self.prepare()["pending_notifications"])
        web = delivery.deliver(self.root, self.state, self.sha, "websub")
        rss = delivery.deliver(self.root, self.state, self.sha, "rsscloud")
        self.assertEqual((4, 1), (web["accepted"], rss["accepted"]))
        state = delivery._decode(self.state.read_bytes())
        self.assertEqual(5, len(state["accepted"]))
        self.assertEqual({}, state["pending"])
        self.assertEqual(0o600, self.state.stat().st_mode & 0o777)
        for receipt in state["accepted"].values():
            self.assertEqual(self.sha, receipt["source_sha"])
            self.assertEqual(self.current["topics"][receipt["topic"]]["sha256"],
                             receipt["content_sha256"])
        self.assertEqual(2, self.web_call.call_count)
        self.assertEqual(1, self.rss_call.call_count)

    def test_new_source_commit_or_retry_does_not_repeat_accepted_content(self):
        self.prepare()
        for protocol in ("websub", "rsscloud"):
            delivery.deliver(self.root, self.state, self.sha, protocol)
        new_sha = "b" * 40
        self.assertEqual(0, self.prepare(sha=new_sha)["pending_notifications"])
        for protocol in ("websub", "rsscloud"):
            result = delivery.deliver(self.root, self.state, new_sha, protocol)
            self.assertEqual(0, result["accepted"])
        self.assertEqual(2, self.web_call.call_count)
        self.assertEqual(1, self.rss_call.call_count)

    def test_only_a_changed_topic_gets_a_new_notification(self):
        self.prepare()
        for protocol in ("websub", "rsscloud"):
            delivery.deliver(self.root, self.state, self.sha, protocol)
        baseline = {topic: spec["sha256"] for topic, spec in self.current["topics"].items()}
        self.current["topics"][self.atom]["sha256"] = "e" * 64
        self.current["generation_digest"] = "f" * 64
        self.assertEqual(2, self.prepare(baseline)["pending_notifications"])
        result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertEqual(2, result["accepted"])
        self.assertEqual((self.atom,), self.web_call.call_args.kwargs["topics"])
        result = delivery.deliver(self.root, self.state, self.sha, "rsscloud")
        self.assertEqual(0, result["accepted"])

    def test_provider_failure_preserves_pending_and_does_not_retry_successes(self):
        self.prepare()
        calls = []
        def reject_first(*args, **kwargs):
            calls.append(True)
            if len(calls) == 1:
                raise RuntimeError("transient provider failure")
            self.ack(*args, **kwargs)
        self.web_call.side_effect = reject_first
        result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertEqual((2, 2, 1), (result["accepted"], result["pending"], result["failed_batches"]))
        current_baseline = {topic: spec["sha256"] for topic, spec in self.current["topics"].items()}
        self.prepare(current_baseline)
        self.web_call.side_effect = self.ack
        result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertEqual((2, 0), (result["accepted"], result["pending"]))
        self.assertEqual(3, self.web_call.call_count)

    def test_superseded_failed_generation_cannot_be_published(self):
        self.prepare()
        self.current["topics"][self.atom]["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "not bound"):
            delivery.deliver(self.root, self.state, self.sha, "websub")
        self.web_call.assert_not_called()

    def test_204_topics_reach_healthy_hub_within_one_failed_batch_budget(self):
        self.current["topics"] = {
            f"{delivery.SITE}/en-US/feed-{i}.xml": {
                "sha256": "c" * 64, "format": "atom", "rsscloud": False,
            }
            for i in range(204)
        }
        self.prepare()
        failed, healthy = delivery.WEBSUB_HUBS
        elapsed = [0]
        calls = {failed: 0, healthy: 0}
        def one_hub_down(*args, hub, **kwargs):
            calls[hub] += 1
            if hub == failed:
                elapsed[0] += 49
                raise RuntimeError("three timed-out 15-second requests plus backoff")
            self.assertLess(elapsed[0], 360)
            elapsed[0] += 1
            self.ack(*args, **kwargs)
        self.web_call.side_effect = one_hub_down
        result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertEqual((204, 204, 1),
                         (result["accepted"], result["pending"], result["failed_batches"]))
        self.assertEqual({failed: 1, healthy: 9}, calls)
        self.assertLess(elapsed[0], 360)

    def test_single_bad_rss_topic_cannot_permanently_starve_other_topics(self):
        bad = delivery.SITE + "/ar-SA/rss.xml"
        self.current["topics"][bad] = {"sha256": "e" * 64, "format": "rss", "rsscloud": True}
        self.prepare()
        def reject_one(*args, topic, **kwargs):
            if topic == bad:
                raise RuntimeError("provider rejects only this topic")
            self.ack(*args, **kwargs)
        self.rss_call.side_effect = reject_one
        first = delivery.deliver(self.root, self.state, self.sha, "rsscloud")
        self.assertEqual((0, 2), (first["accepted"], first["pending"]))
        same = {topic: spec["sha256"] for topic, spec in self.current["topics"].items()}
        self.prepare(same)
        second = delivery.deliver(self.root, self.state, self.sha, "rsscloud")
        self.assertEqual((1, 1), (second["accepted"], second["pending"]))
        state = delivery._decode(self.state.read_bytes())
        rejected = [t for t in state["pending"].values() if t["protocol"] == "rsscloud"]
        self.assertEqual(bad, rejected[0]["topic"])
        self.assertEqual(2, rejected[0]["attempt_count"])

    def test_slow_successful_provider_cannot_consume_the_other_hub_budget(self):
        self.current["topics"] = {
            f"{delivery.SITE}/en-US/feed-{i}.xml": {
                "sha256": "c" * 64, "format": "atom", "rsscloud": False,
            }
            for i in range(204)
        }
        self.prepare()
        slow, healthy = delivery.WEBSUB_HUBS
        elapsed = [0]
        calls = {slow: 0, healthy: 0}
        def slow_ack(*args, hub, **kwargs):
            calls[hub] += 1
            elapsed[0] += 49 if hub == slow else 1
            self.ack(*args, **kwargs)
        self.web_call.side_effect = slow_ack
        with mock.patch.object(delivery.time, "monotonic", side_effect=lambda: elapsed[0]):
            result = delivery.deliver(self.root, self.state, self.sha, "websub")
        self.assertEqual({slow: 2, healthy: 9}, calls)
        self.assertEqual(254, result["accepted"])
        self.assertEqual(154, result["pending"])
        self.assertEqual(7, result["deferred_batches"])
        self.assertLess(elapsed[0], 360)

    def test_wrong_source_and_unprepared_outbox_fail_before_external_post(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "not bound"):
            delivery.deliver(self.root, self.state, "c" * 40, "websub")
        self.web_call.assert_not_called()
        self.state.unlink()
        with self.assertRaisesRegex(ValueError, "not bound"):
            delivery.deliver(self.root, self.state, self.sha, "websub")
        self.web_call.assert_not_called()

    def test_missing_acknowledgement_is_not_recorded_as_delivered(self):
        self.prepare()
        self.rss_call.side_effect = None
        result = delivery.deliver(self.root, self.state, self.sha, "rsscloud")
        self.assertEqual((0, 1, 1), (result["accepted"], result["pending"], result["failed_batches"]))

    def test_readback_failure_blocks_all_provider_posts(self):
        self.prepare()
        self.verify.side_effect = ValueError("wrong deployed digest")
        with self.assertRaisesRegex(ValueError, "wrong deployed"):
            delivery.deliver(self.root, self.state, self.sha, "websub")
        self.web_call.assert_not_called()
        self.rss_call.assert_not_called()

    def test_pending_topic_tampering_is_rejected(self):
        self.prepare()
        state = delivery._decode(self.state.read_bytes())
        next(iter(state["pending"].values()))["topic"] = "https://example.invalid/"
        delivery.save_state(self.state, state)
        with self.assertRaisesRegex(ValueError, "not source-bound"):
            delivery.deliver(self.root, self.state, self.sha, "websub")
        self.web_call.assert_not_called()

    def test_parallel_owner_and_symlink_state_are_rejected(self):
        self.prepare()
        with delivery.locked_state(self.state):
            with self.assertRaisesRegex(RuntimeError, "Another owner"):
                delivery.prepare(self.root, self.state, self.sha,
                                 baseline={topic: None for topic in self.current["topics"]})
        link = self.root / "linked.json"
        link.symlink_to(self.state)
        with self.assertRaisesRegex(ValueError, "symlink"):
            with delivery.locked_state(link):
                pass

    def test_topic_path_cannot_escape_owned_site(self):
        for topic in (
            "https://example.invalid/rss.xml",
            delivery.SITE + "/%2e%2e/secret",
            delivery.SITE + "/en-US/feed.json?outside=1",
        ):
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                delivery._local(self.root, topic)

    def test_fetch_only_accepts_real_404_as_a_new_surface(self):
        missing = urllib.error.HTTPError(self.rss, 404, "not found", {}, io.BytesIO(b""))
        opener = mock.Mock(side_effect=missing)
        self.assertIsNone(delivery._fetch(self.rss, opener=opener, missing_ok=True))
        denied = urllib.error.HTTPError(self.rss, 403, "forbidden", {}, io.BytesIO(b""))
        opener.side_effect = denied
        with self.assertRaises(urllib.error.HTTPError):
            delivery._fetch(self.rss, opener=opener, missing_ok=True)
        self.assertEqual(2, opener.call_count)

    def test_transient_get_failure_has_bounded_backoff(self):
        error = urllib.error.URLError("connection error")
        opener = mock.Mock(side_effect=error)
        with mock.patch.object(delivery.time, "sleep") as sleep:
            with self.assertRaises(urllib.error.URLError):
                delivery._fetch(self.atom, opener=opener)
        self.assertEqual(3, opener.call_count)
        self.assertEqual([mock.call(1), mock.call(2)], sleep.call_args_list)

    def test_fetch_rejects_html_charset_and_oversized_content(self):
        for content_type, body in (
            ("text/html; charset=utf-8", b"<html>error</html>"),
            ("application/xml; charset=iso-8859-1", b"<?xml?>"),
            ("application/xml; charset=utf-8", b"x" * (delivery.MAX_BYTES + 1)),
        ):
            with self.subTest(content_type=content_type, bytes=len(body)):
                headers = Message()
                headers["Content-Type"] = content_type
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.status = 200
                response.headers = headers
                response.read.return_value = body
                with self.assertRaises(ValueError):
                    delivery._fetch(self.atom, opener=lambda *a, **k: response,
                                    content_types=delivery.CONTENT_TYPES["atom"])


if __name__ == "__main__":
    unittest.main()
