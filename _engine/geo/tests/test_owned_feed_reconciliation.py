from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import FeedFixture, SOURCE, feeds, make_deployment
import owned_feed_delivery as delivery
import owned_feed_receipts as receipts
import owned_feed_reconciliation as reconciliation
from deployment_generation import validate_binding


class ReconciliationTests(FeedFixture):
    def setUp(self):
        super().setUp()
        self.capture = self.root / "capture"
        (self.capture / "bodies").mkdir(parents=True)
        manifest = feeds.read_manifest(self.pages)
        before = self.observation(feeds.url(delivery.DEPLOYMENT), (self.pages / delivery.DEPLOYMENT).read_bytes())
        endpoints = []
        for locale, row in manifest["feeds"].items():
            for fmt, spec in row["formats"].items():
                observation = self.observation(spec["url"], (self.pages / spec["path"]).read_bytes(),
                                               content_type="application/json" if fmt == "json_feed" else "application/xml")
                observation.update(locale=locale, format=fmt)
                endpoints.append(observation)
        doc = feeds.read_json(self.pages / delivery.DEPLOYMENT)
        self.snapshot = {
            "schema": "lumi.owned-feed-public-capture/v1", "site": feeds.SITE,
            "generation": validate_binding(doc), "deployment": doc,
            "deployment_before": before, "deployment_after": copy.deepcopy(before),
            "public_manifest": self.observation(feeds.url(feeds.INDEX), (self.pages / feeds.INDEX).read_bytes()),
            "endpoints": endpoints, "stable_generation": True,
            "network_method": "GET", "notification_requests": 0,
        }
        self.seal()

    def observation(self, url, raw, *, content_type="application/json"):
        digest = feeds.sha256(raw)
        (self.capture / "bodies" / digest).write_bytes(raw)
        return {
            "url": url, "final_url": url, "method": "GET", "observed_at": "2026-09-12T00:00:00Z",
            "http_status": 200, "content_type": content_type, "location": None,
            "body_sha256": digest, "body_path": f"bodies/{digest}", "bytes": len(raw),
        }

    def seal(self):
        self.snapshot["capture_digest"] = feeds.digest({
            k: v for k, v in self.snapshot.items() if k != "capture_digest"
        })
        (self.capture / "capture.json").write_bytes(feeds.json_bytes(self.snapshot))

    def plan(self, history=()):
        return reconciliation.reconcile(self.pages, self.capture, list(history))

    def history(self, count=2, *, stale=False):
        path = self.root / "history.json"
        current = delivery.inventory(self.pages)
        binding = delivery.binding(self.pages, current, SOURCE)
        if stale:
            binding["source_sha"] = "e" * 40
        state = receipts.new_state()
        state["prepared"] = {**binding, "include_legacy": False}
        for key, task in list(delivery.tasks(current).items())[:count]:
            task.update(binding)
            body = receipts.request_body(task["protocol"], [task["topic"]])
            attempt = {
                "attempt_id": "1" * 32, "topics": [task["topic"]], "request_body": body,
                "request_sha256": feeds.sha256(body.encode("ascii")), "started_at": "2026-09-01T00:00:00Z",
            }
            response = delivery.response_record(
                task["protocol"], task["endpoint"], [task["topic"]],
                200 if task["protocol"] == "rsscloud" else 204,
                '{"success":true}' if task["protocol"] == "rsscloud" else "",
                observed_at="2026-09-01T00:00:01Z",
            )
            record = receipts.make_receipt(task, attempt, response)
            state["records"][record["receipt_id"]] = record
            state["accepted"][key] = record["receipt_id"]
        delivery.save_state(path, state)
        return path

    def test_public_hash_match_without_provider_ack_is_missing_ack_not_changed_or_acked(self):
        plan = self.plan()
        self.assertEqual(150, plan["public_coverage"]["valid"])
        self.assertEqual(343, plan["classifications"]["missing_ack"])
        self.assertEqual(0, plan["classifications"]["content_changed"])
        self.assertEqual(0, plan["classifications"]["already_acked_current"])
        self.assertEqual(343, plan["pending_intents"])
        self.assertEqual(0, plan["dispatchable_intents"])
        self.assertTrue(all(p["equivalent"] and not p["provider_ack_proven"] for p in plan["semantic_proofs"].values()))

    def test_absent_public_endpoints_are_not_343_content_changes(self):
        for row in self.snapshot["endpoints"]:
            row.update(http_status=404, content_type="text/html")
        self.snapshot["public_manifest"]["http_status"] = 404
        self.seal()
        plan = self.plan()
        self.assertEqual(0, plan["public_coverage"]["valid"])
        self.assertEqual(343, plan["classifications"]["endpoint_not_live"])
        self.assertEqual(0, plan["new_content_intents"])
        self.assertEqual(0, plan["pending_intents"])

    def test_partial_durable_history_migrates_only_exact_current_provider_topic_acks(self):
        history = self.history()
        plan = self.plan([history])
        self.assertEqual(2, plan["classifications"]["already_acked_current"])
        self.assertEqual(341, plan["classifications"]["missing_ack"])
        result = reconciliation.import_state(self.pages, self.capture, [history], self.state)
        state = delivery.read_state(self.state)
        self.assertEqual(2, len(state["accepted"]))
        self.assertEqual(2, len(state["records"]))
        self.assertEqual(341, result["pending_intents"])
        self.assertTrue(result["release_hold"])

    def test_stale_source_receipt_is_retained_but_cannot_migrate_as_current(self):
        history = self.history(stale=True)
        plan = self.plan([history])
        self.assertEqual(2, plan["classifications"]["stale_generation"])
        self.assertEqual(0, plan["classifications"]["already_acked_current"])
        reconciliation.import_state(self.pages, self.capture, [history], self.state)
        state = delivery.read_state(self.state)
        self.assertFalse(state["accepted"])
        self.assertEqual(2, len(state["records"]))

    def test_forged_receipt_and_workflow_summary_never_prove_ack(self):
        history = self.history()
        state = feeds.read_json(history)
        record = next(iter(state["records"].values()))
        record["response"]["ack_body"] = "forged"
        state["state_digest"] = feeds.digest({k: v for k, v in state.items() if k != "state_digest"})
        history.write_bytes(feeds.json_bytes(state))
        summary = self.root / "workflow.json"
        summary.write_bytes(feeds.json_bytes({"workflow_success": True, "http_status": 204}))
        summary.chmod(0o600)
        plan = self.plan([history, summary])
        self.assertEqual(2, len(plan["rejected_history"]))
        self.assertEqual(343, plan["classifications"]["missing_ack"])

    def test_redirect_wrong_content_type_or_hash_are_endpoint_not_live(self):
        row = self.snapshot["endpoints"][0]
        original = copy.deepcopy(row)
        for mutation in (
            {"http_status": 302, "location": "https://example.org/"},
            {"content_type": "text/html"},
            {"body_sha256": "0" * 64},
        ):
            row.clear()
            row.update(original)
            row.update(mutation)
            self.seal()
            with self.subTest(mutation=mutation):
                plan = self.plan()
                self.assertEqual(149, plan["public_coverage"]["valid"])
                self.assertGreater(plan["classifications"]["endpoint_not_live"], 0)

    def test_dates_only_difference_needs_and_has_explicit_semantic_equivalence_proof(self):
        row = next(r for r in self.snapshot["endpoints"] if r["locale"] == "en-US" and r["format"] == "json_feed")
        doc = feeds.decode((self.capture / row["body_path"]).read_bytes())
        doc["items"][0]["date_modified"] = "2026-09-02T00:00:00Z"
        updated = self.observation(row["url"], feeds.json_bytes(doc))
        updated.update(locale="en-US", format="json_feed")
        row.update(updated)
        self.seal()
        plan = self.plan()
        proof = plan["semantic_proofs"][row["url"]]
        self.assertNotEqual(proof["production_body_sha256"], proof["candidate_body_sha256"])
        self.assertEqual(proof["production_semantic_sha256"], proof["candidate_semantic_sha256"])
        self.assertTrue(proof["equivalent"])
        self.assertFalse(proof["provider_ack_proven"])
        self.assertEqual(0, plan["new_content_intents"])

    def test_modified_public_content_is_classified_as_content_changed(self):
        row = next(r for r in self.snapshot["endpoints"] if r["locale"] == "en-US" and r["format"] == "json_feed")
        doc = feeds.decode((self.capture / row["body_path"]).read_bytes())
        doc["items"][0]["summary"] += " Additional native content."
        updated = self.observation(row["url"], feeds.json_bytes(doc))
        updated.update(locale="en-US", format="json_feed")
        row.update(updated)
        self.seal()
        self.assertEqual(2, self.plan()["classifications"]["content_changed"])

    def test_guid_date_and_canonical_failures_are_not_valid_public_coverage(self):
        row = next(r for r in self.snapshot["endpoints"] if r["locale"] == "en-US" and r["format"] == "json_feed")
        original = feeds.decode((self.capture / row["body_path"]).read_bytes())
        for field, value in (("id", "wrong"), ("url", "https://example.org/"), ("date_modified", "yesterday")):
            document = copy.deepcopy(original)
            document["items"][0][field] = value
            updated = self.observation(row["url"], feeds.json_bytes(document))
            updated.update(locale="en-US", format="json_feed")
            row.update(updated)
            self.seal()
            self.assertEqual(149, self.plan()["public_coverage"]["valid"])

    def test_migration_is_atomic_0600_and_replay_is_a_byte_noop(self):
        first = reconciliation.import_state(self.pages, self.capture, [], self.state)
        before = self.state.read_bytes(), self.state.stat().st_mtime_ns
        second = reconciliation.import_state(self.pages, self.capture, [], self.state)
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(before, (self.state.read_bytes(), self.state.stat().st_mtime_ns))
        self.assertEqual(0o600, self.state.stat().st_mode & 0o777)

    def test_migration_crash_recovers_once_and_preserves_imported_history(self):
        history = self.history()
        with patch.object(delivery.os, "replace", side_effect=OSError("crash before rename")):
            with self.assertRaises(OSError):
                reconciliation.import_state(self.pages, self.capture, [history], self.state)
        result = reconciliation.import_state(self.pages, self.capture, [history], self.state)
        self.assertTrue(result["replayed"])
        self.assertEqual(2, len(delivery.read_state(self.state)["records"]))

    def test_migrated_pending_cannot_notify_before_locale_layout_release(self):
        reconciliation.import_state(self.pages, self.capture, [], self.state)
        with patch.object(delivery, "inventory", side_effect=AssertionError("Hold must precede readback")):
            with self.assertRaisesRegex(ValueError, "held"):
                delivery.deliver(self.pages, self.state, SOURCE, "websub")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            delivery.main(["notify", "--pages-dir", str(self.pages), "--state", str(self.state),
                           "--source-sha", SOURCE, "--protocol", "websub", "--execute"])
        self.assertTrue(json.loads(output.getvalue())["notification_release_hold"])

    def test_lost_local_cache_cannot_bootstrap_343_intents_via_cli(self):
        with patch("notification_release.held_result", return_value=None), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            delivery.main(["prepare", "--pages-dir", str(self.pages),
                           "--state", str(self.state), "--source-sha", SOURCE])
        self.assertFalse(self.state.exists())

    def test_generation_change_during_capture_fails_closed(self):
        make_deployment(self.pages, SOURCE, run="2")
        self.snapshot["deployment_after"] = self.observation(
            feeds.url(delivery.DEPLOYMENT), (self.pages / delivery.DEPLOYMENT).read_bytes()
        )
        self.seal()
        with self.assertRaisesRegex(ValueError, "generation changed"):
            self.plan()
