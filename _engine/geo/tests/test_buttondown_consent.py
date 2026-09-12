import copy
from datetime import timedelta
import hashlib
import hmac
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
import uuid

GEO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GEO), str(GEO / "tests")]

import buttondown_consent_evaluator as evaluator
import buttondown_consent_policy as policy
import gen_owned_email_capture as capture
import owned_email_contract as c
import owned_email_readback as readback
import owned_email_sender as legacy
from test_owned_email import NOW, KEY, WEBHOOK_KEY, SUBSCRIBER, NEWSLETTER, EVENT, EMAIL, PROVIDER
from test_owned_email import availability, sources, subscriber, state


class Provider:
    def __init__(self, row):
        self.now = NOW
        self.row = row
        self.calls = []
        self.authenticated = True
        self.account = {"username": "hourstag-operator", "email_address": "private-account@example.invalid"}
        self.newsletter = {
            "id": NEWSLETTER, "username": "hourstag", "api_key": "DO-NOT-SERIALIZE-THIS-TEST-SECRET",
            "should_require_double_optin": True,
            "custom_subscription_confirmation_email_text": (
                '<p>{{ subscriber.metadata.owned_app_id }} / {{ subscriber.metadata.owned_locale }} / '
                '{{ subscriber.metadata.owned_campaign }}</p><a href="{{ confirmation_url }}">Confirm</a>'
            ),
            "footer": '<a href="{{ unsubscribe_url }}">Unsubscribe</a>',
            "custom_email_template": None, "custom_subscription_confirmation_email_template": None,
            "enabled_features": ["metadata", "webhooks"], "from_name": "Lumi Studio",
            "email_address": "news@mail.publisher.example", "email_domain": "mail.publisher.example",
            "reply_to_address": "hourstag.app@gmail.com", "sending_domain_status": "valid", "test_mode": False,
        }
        self.domain = {
            "domain": "mail.publisher.example", "status": "valid", "warnings": [],
            "requirements": [{"is_valid": True}], "is_checking": False,
            "checked_date": (NOW - timedelta(hours=1)).isoformat(),
        }
        self.subscriber = {**subscriber(row), "transitions": []}
        self.census = {"count": 1, "results": [{"id": SUBSCRIBER, "type": "regular"}]}
        self.email = None
        self.archive_body = b"public archive only"
        self.overrides = {}

    def get(self, url):
        self.calls.append(url)
        authenticated = url.startswith(policy.API) and self.authenticated
        status = 200
        if url in self.overrides:
            return self.overrides[url]
        if url == c.ENDPOINT:
            body, status = b"redirect to public form", 302
        elif url == "https://buttondown.com/hourstag":
            body = b"<form>Public form exists; not DOI configuration</form>"
        elif url.startswith("https://buttondown.com/hourstag/archive/"):
            body = self.archive_body
        elif url == policy.API + "/accounts/me":
            body, status = (self.account, 200) if self.authenticated else ({"detail": "Unauthorized"}, 401)
        elif url == policy.API + "/newsletters":
            body = {"count": 1, "results": [self.newsletter]}
        elif url == f"{policy.API}/newsletters/{NEWSLETTER}":
            body = self.newsletter
        elif url == f"{policy.API}/newsletters/{NEWSLETTER}/sending-domain":
            body = self.domain
        elif url == f"{policy.API}/subscribers/{SUBSCRIBER}":
            body = self.subscriber
        elif url.startswith(policy.API + "/subscribers"):
            body = self.census
        elif url == f"{policy.API}/emails/{EMAIL}":
            body = self.email
        else:
            raise AssertionError("unexpected provider request: " + url)
        return {
            "method": "GET", "url": url, "final_url": url, "http_status": status,
            "authenticated": authenticated, "body": body if isinstance(body, bytes) else c.json_bytes(body),
            "observed_at": self.now.isoformat(),
        }


class ButtondownConsentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.git = mock.patch.object(c, "committed_source_files", return_value=c.source_files())
        cls.git.start()
        cls.availability = availability()
        cls.inventory, _ = capture.build(PROVIDER, sources(), cls.availability, now=NOW)
        cls.row = c.inventory_row(cls.inventory, "aibriefpack", "zh-Hant")

    @classmethod
    def tearDownClass(cls):
        cls.git.stop()

    def setUp(self):
        self.server = Provider(self.row)
        self.server.now = NOW - timedelta(minutes=2)
        self.snapshot = policy.collect(self.server.get, now=self.server.now)
        self.server.now = NOW

    def revocations(self, entries=None):
        return legacy.seal({
            "schema": evaluator.REVOCATIONS, "account_binding": self.snapshot["binding_digest"],
            "observed_at": self.server.now.isoformat(), "complete": True, "entries": entries or [],
        }, KEY)

    def sender_state(self, **changes):
        payload = copy.deepcopy(state()["payload"])
        payload.update(account_binding=self.snapshot["binding_digest"],
                       observed_at=self.server.now.isoformat(), **changes)
        return legacy.seal(payload, KEY)

    def event(self, kind="subscriber.confirmed", event_id=EVENT, **data):
        body = c.json_bytes({
            "id": event_id, "event_type": kind,
            "data": {"newsletter": NEWSLETTER, "subscriber": SUBSCRIBER, **data},
        })
        signature = "sha256=" + hmac.new(WEBHOOK_KEY, body, hashlib.sha256).hexdigest()
        return body, signature

    def proof(self):
        self.server.now = NOW - timedelta(minutes=1)
        self.server.subscriber["type"] = "unactivated"
        pending = evaluator.pending(
            self.snapshot, self.row, SUBSCRIBER, get=self.server.get, receipt_key=KEY,
            revocations=self.revocations(), now=self.server.now,
        )
        self.server.now = NOW
        self.server.subscriber["type"] = "regular"
        body, signature = self.event()
        confirmed = evaluator.confirmed(
            self.snapshot, self.row, pending, body, signature, get=self.server.get,
            receipt_key=KEY, webhook_key=WEBHOOK_KEY, revocations=self.revocations(),
            processed_event_ids=set(), now=self.server.now,
        )
        return pending, confirmed

    def evaluate(self, proofs, *, snapshot=None, revocations=None, state_receipt=None):
        return evaluator.evaluate(
            snapshot or self.snapshot, self.inventory, self.availability, self.row["app_key"], self.row["locale"],
            proofs, get=self.server.get, receipt_key=KEY, state_receipt=state_receipt or self.sender_state(),
            revocations=revocations or self.revocations(), now=self.server.now,
        )

    def test_public_200_and_default_documentation_do_not_prove_doi(self):
        self.server.newsletter.pop("should_require_double_optin")
        snapshot = policy.collect(self.server.get, now=NOW)
        self.assertEqual(snapshot["public_gets"]["public_profile_url"]["http_status"], 200)
        self.assertEqual(snapshot["checks"]["double_opt_in"], "UNKNOWN")
        self.assertEqual(snapshot["status"], "BLOCKED")
        with self.assertRaises(c.ContractError):
            policy.validate(snapshot, now=NOW)

    def test_confirmed_event_with_doi_disabled_cannot_qualify_a_subscriber(self):
        _, genuinely_signed_proof = self.proof()
        self.server.newsletter["should_require_double_optin"] = False
        snapshot = policy.collect(self.server.get, now=NOW)
        self.assertEqual(snapshot["checks"]["double_opt_in"], "BLOCKED")
        result = self.evaluate([genuinely_signed_proof], snapshot=snapshot)
        self.assertEqual(result["verified_audience_count"], 0)
        self.assertIn("configuration", result["reason"])

    def test_unauthenticated_account_is_unknown_not_zero_subscribers(self):
        self.server.authenticated = False
        snapshot = policy.collect(self.server.get, now=NOW)
        self.assertEqual(snapshot["api_gets"]["account"]["http_status"], 401)
        self.assertIsNone(snapshot["binding"]["account"])
        self.assertEqual(snapshot["subscriber_count"], "UNKNOWN")
        self.assertEqual(evaluator.named_census(snapshot, self.server.get, now=NOW)["subscriber_count"], "UNKNOWN")

    def test_api_keys_and_private_account_addresses_are_not_serialized(self):
        source = c.json_bytes(self.snapshot).decode()
        self.assertNotIn("DO-NOT-SERIALIZE", source)
        self.assertNotIn("private-account@example.invalid", source)
        self.assertIn("account_binding", source)
        self.assertTrue(self.snapshot["binding"]["account"]["email_sha256"])

    def test_policy_snapshot_binds_exact_account_form_and_configuration(self):
        policy.validate(self.snapshot, now=NOW)
        self.assertEqual(self.snapshot["status"], "VERIFIED_CONFIGURATION")
        self.assertEqual(self.snapshot["binding"]["newsletter_id"], NEWSLETTER)
        self.assertEqual(self.snapshot["binding"]["public_form_url"], c.ENDPOINT)
        for key in policy.CHECKS:
            self.assertEqual(self.snapshot["checks"][key], "VERIFIED")

    def test_snapshot_stale_ttl_and_source_digest_fail_closed(self):
        with self.assertRaises(c.ContractError):
            policy.validate(self.snapshot, now=NOW + timedelta(minutes=10))
        for key, value in (("source_digest", "0" * 64), ("local_config_digest", "0" * 64), ("ttl_seconds", 9999)):
            changed = copy.deepcopy(self.snapshot)
            changed[key] = value
            changed["digest"] = c.digest({k: v for k, v in changed.items() if k != "digest"})
            with self.assertRaises(c.ContractError):
                policy.validate(changed, now=NOW)

    def test_forged_ready_flags_cannot_override_get_settings(self):
        changed = copy.deepcopy(self.snapshot)
        changed["configuration"]["newsletter"]["double_opt_in"] = False
        changed["configuration_digest"] = policy.configuration_digest(changed["configuration"])
        changed["digest"] = c.digest({k: v for k, v in changed.items() if k != "digest"})
        with self.assertRaises(c.ContractError):
            policy.validate(changed, now=NOW)

    def test_missing_scoped_confirmation_and_unsubscribe_template_block(self):
        for field in ("custom_subscription_confirmation_email_text", "footer"):
            original = self.server.newsletter.pop(field)
            snapshot = policy.collect(self.server.get, now=NOW)
            self.assertEqual(snapshot["status"], "BLOCKED")
            self.server.newsletter[field] = original
        self.server.newsletter["custom_subscription_confirmation_email_text"] = (
            '<!-- {{ subscriber.metadata.owned_app_id }} {{ subscriber.metadata.owned_locale }} '
            '{{ subscriber.metadata.owned_campaign }} --><a href="{{ confirmation_url }}">Confirm</a>'
        )
        self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["scoped_confirmation"], "UNKNOWN")

    def test_template_overrides_cannot_hide_scope_or_unsubscribe_and_still_pass(self):
        for field, check in (
            ("custom_email_template", "unsubscribe_configuration"),
            ("custom_subscription_confirmation_email_template", "scoped_confirmation"),
        ):
            self.server.newsletter[field] = "unknown-custom-template"
            self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"][check], "UNKNOWN")
            self.server.newsletter[field] = None
            value = self.server.newsletter.pop(field)
            self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"][check], "UNKNOWN")
            self.server.newsletter[field] = value

    def test_non_boolean_doi_and_forged_named_account_url_fail_closed(self):
        self.server.newsletter["should_require_double_optin"] = "true"
        self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["double_opt_in"], "UNKNOWN")
        changed = copy.deepcopy(self.snapshot)
        changed["api_gets"]["account"]["url"] = policy.API + "/newsletters"
        changed["api_gets"]["account"]["final_url"] = policy.API + "/newsletters"
        changed["digest"] = c.digest({k: v for k, v in changed.items() if k != "digest"})
        with self.assertRaises(c.ContractError):
            policy.validate(changed, now=NOW)

    def test_tracking_enabled_or_unexposed_settings_are_not_assumed_disabled(self):
        for change in (None, ["tracking"], ["webhooks", "tracking"]):
            self.server.newsletter["enabled_features"] = change
            self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["tracking_disabled"], "UNKNOWN")

    def test_sender_identity_pending_stale_or_wrong_reply_to_is_blocking(self):
        for status in ("none", "invalid", "awaiting_ssl", "failing", "deliberately_cold"):
            self.server.domain["status"] = status
            self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["sender_identity"], "UNKNOWN")
        self.server.domain["status"] = "valid"
        self.server.domain["checked_date"] = (NOW - timedelta(days=2)).isoformat()
        self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["sender_identity"], "UNKNOWN")
        self.server.domain["checked_date"] = NOW.isoformat()
        self.server.newsletter["reply_to_address"] = "wrong@example.invalid"
        self.assertEqual(policy.collect(self.server.get, now=NOW)["checks"]["sender_identity"], "UNKNOWN")

    def test_dns_observation_refresh_is_not_a_consent_scope_change(self):
        before = self.snapshot["configuration_digest"]
        self.server.domain["checked_date"] = NOW.isoformat()
        refreshed = policy.refresh_match(self.snapshot, self.server.get, now=NOW)
        self.assertEqual(refreshed["configuration_digest"], before)

    def test_pending_is_not_verified_audience_and_confirmed_is_plan_only(self):
        pending, proof = self.proof()
        self.assertEqual(self.evaluate([pending])["verified_audience_count"], 0)
        result = self.evaluate([proof])
        self.assertEqual(result["verified_audience_count"], 1)
        self.assertEqual(result["action"], "plan_only")
        self.assertFalse(result["send_allowed"])
        self.assertEqual(result["post_requests"], 0)
        self.assertEqual(result["subscriber_count"], "UNKNOWN")

    def test_zero_audience_is_noop_without_get_or_credentials(self):
        get = mock.Mock(side_effect=AssertionError("no GET for empty audience"))
        result = evaluator.evaluate(None, None, None, "aibriefpack", "zh-Hant", [], get=get)
        self.assertEqual(result["verified_audience_count"], 0)
        self.assertEqual(result["action"], "no_op")
        get.assert_not_called()

    def test_missing_policy_or_global_history_is_zero_audience(self):
        _, proof = self.proof()
        for snapshot, state_receipt, revocations in (
            (None, self.sender_state(), self.revocations()),
            (self.snapshot, None, self.revocations()), (self.snapshot, self.sender_state(), None),
        ):
            result = evaluator.evaluate(
                snapshot, self.inventory, self.availability, self.row["app_key"], self.row["locale"], [proof],
                get=self.server.get, receipt_key=KEY, state_receipt=state_receipt, revocations=revocations, now=NOW,
            )
            self.assertEqual(result["verified_audience_count"], 0)

    def test_missing_subscriber_fields_are_not_assumed_unsuppressed(self):
        _, proof = self.proof()
        for field in ("unsubscription_date", "bounce_date", "undeliverability_date", "email_transitions", "transitions"):
            original = self.server.subscriber.pop(field)
            self.assertEqual(self.evaluate([proof])["verified_audience_count"], 0)
            self.server.subscriber[field] = original

    def test_scope_and_confirmation_timestamp_are_mandatory(self):
        _, original = self.proof()
        for field, value in (
            ("confirmed_at", None), ("confirmed_at", (NOW + timedelta(seconds=1)).isoformat()),
            ("generation", None), ("newsletter_id", SUBSCRIBER), ("account_binding", "0" * 64),
        ):
            body = copy.deepcopy(original["payload"])
            body[field] = value
            self.assertEqual(self.evaluate([legacy.seal(body, KEY)])["verified_audience_count"], 0)
        for field in ("app_id", "locale", "campaign"):
            body = copy.deepcopy(original["payload"])
            body["scope"][field] = "wrong_scope"
            self.assertEqual(self.evaluate([legacy.seal(body, KEY)])["verified_audience_count"], 0)

    def test_account_change_and_live_config_change_block_old_proof(self):
        _, proof = self.proof()
        self.server.account["username"] = "different-account"
        self.assertEqual(self.evaluate([proof])["verified_audience_count"], 0)
        self.server.account["username"] = "hourstag-operator"
        self.server.newsletter["footer"] += "new policy"
        self.assertEqual(self.evaluate([proof])["verified_audience_count"], 0)

    def test_current_unsubscribe_and_suppression_always_block(self):
        _, proof = self.proof()
        for kind in ("unsubscribed", "complained", "blocked", "undeliverable", "removed", "unactivated"):
            self.server.subscriber["type"] = kind
            self.assertEqual(self.evaluate([proof])["verified_audience_count"], 0)
        self.server.subscriber["type"] = "regular"
        self.assertEqual(self.evaluate([proof], state_receipt=self.sender_state(
            suppressed_subscriber_ids=[SUBSCRIBER],
        ))["verified_audience_count"], 0)

    def test_unsubscribe_then_resubscribe_requires_a_new_scoped_confirmation(self):
        _, old = self.proof()
        self.server.now = NOW + timedelta(minutes=1)
        self.server.subscriber.update(type="unsubscribed", unsubscription_date=self.server.now.isoformat())
        body, signature = self.event("subscriber.unsubscribed", str(uuid.UUID(int=20)))
        revoked = evaluator.revoked(
            self.snapshot, self.revocations(), body, signature, get=self.server.get,
            receipt_key=KEY, webhook_key=WEBHOOK_KEY, now=self.server.now,
        )
        self.assertEqual(self.evaluate([old], revocations=revoked)["verified_audience_count"], 0)
        self.server.now = NOW + timedelta(minutes=2)
        self.server.subscriber["type"] = "regular"
        self.snapshot = policy.collect(self.server.get, now=self.server.now)
        self.assertEqual(self.evaluate([old], revocations=revoked)["verified_audience_count"], 0)
        self.server.subscriber["type"] = "unactivated"
        pending = evaluator.pending(
            self.snapshot, self.row, SUBSCRIBER, get=self.server.get, receipt_key=KEY,
            revocations=revoked, now=self.server.now,
        )
        self.server.now = NOW + timedelta(minutes=3)
        self.server.subscriber["type"] = "regular"
        body, signature = self.event(event_id=str(uuid.UUID(int=21)))
        proof = evaluator.confirmed(
            self.snapshot, self.row, pending, body, signature, get=self.server.get,
            receipt_key=KEY, webhook_key=WEBHOOK_KEY, revocations=revoked,
            processed_event_ids={EVENT}, now=self.server.now,
        )
        self.assertNotEqual(old["payload"]["generation"], proof["payload"]["generation"])
        self.assertEqual(self.evaluate([proof], revocations=revoked)["verified_audience_count"], 1)

    def test_webhook_spoof_account_mismatch_and_replay_are_rejected(self):
        pending, _ = self.proof()
        for body, signature, processed in (
            (*self.event(), {EVENT}),
            (self.event()[0], "sha256=" + "0" * 64, set()),
            (*self.event(newsletter=SUBSCRIBER), set()),
            (*self.event("subscriber.created"), set()),
        ):
            with self.assertRaises(c.ContractError):
                evaluator.confirmed(
                    self.snapshot, self.row, pending, body, signature, get=self.server.get,
                    receipt_key=KEY, webhook_key=WEBHOOK_KEY, revocations=self.revocations(),
                    processed_event_ids=processed, now=NOW,
                )

    def test_atomic_ledger_retries_are_idempotent_and_cannot_bind_new_generation(self):
        pending, _ = self.proof()
        body, signature = self.event()
        folder = GEO / "tests" / (".owned-email-policy-" + uuid.uuid4().hex)
        ledger = evaluator.ConsentLedger(folder / "consent.sqlite")
        try:
            kwargs = dict(get=self.server.get, receipt_key=KEY, webhook_key=WEBHOOK_KEY,
                          revocations=self.revocations(), now=NOW)
            first = ledger.accept(self.snapshot, self.row, pending, body, signature, **kwargs)
            self.assertEqual(first, ledger.accept(self.snapshot, self.row, pending, body, signature, **kwargs))
            altered = {**pending["payload"], "generation": str(uuid.uuid4())}
            with self.assertRaises(c.ContractError):
                ledger.accept(self.snapshot, self.row, legacy.seal(altered, KEY), body, signature, **kwargs)
            self.assertEqual(ledger.db.execute("SELECT count(*) FROM account_confirmations").fetchone()[0], 1)
            self.assertNotIn(b"consenting-reader@", (folder / "consent.sqlite").read_bytes())
        finally:
            ledger.close()
            shutil.rmtree(folder)

    def test_named_api_census_only_and_privacy_threshold_unknown(self):
        result = evaluator.named_census(self.snapshot, self.server.get, now=NOW)
        self.assertEqual(result["subscriber_count"], 1)
        self.assertEqual(result["newsletter_id"], NEWSLETTER)
        self.assertEqual(result["verified_audience_count"], 0)
        for payload in (
            {"count": None, "results": []}, {"count": 0, "results": [], "privacy_threshold": True},
            {"count": 0, "results": [], "redacted": True}, {"results": []},
        ):
            self.server.census = payload
            self.assertEqual(evaluator.named_census(self.snapshot, self.server.get, now=NOW)["subscriber_count"], "UNKNOWN")
        self.server.census = {"count": 0, "results": []}
        self.assertEqual(evaluator.named_census(self.snapshot, self.server.get, now=NOW)["subscriber_count"], 0)

    def test_census_failure_never_falls_back_to_zero(self):
        self.server.overrides[policy.API + "/subscribers"] = {
            "method": "GET", "url": policy.API + "/subscribers", "final_url": policy.API + "/subscribers",
            "authenticated": True, "http_status": 403, "body": b"privacy restricted", "observed_at": NOW.isoformat(),
        }
        self.assertEqual(evaluator.named_census(self.snapshot, self.server.get, now=NOW)["subscriber_count"], "UNKNOWN")

    def test_native_still_requires_named_account_email_id_url_and_get_body(self):
        url = "https://buttondown.com/hourstag/archive/verified-app-update/"
        body = (
            f'<p>{readback.binding_text(self.row)}</p><a href="{self.row["capture_url"]}">App</a>'
            f'<a href="{self.row["app_store_url"]}">App Store</a>'
        )
        self.server.email = {
            "id": EMAIL, "absolute_url": url, "status": "sent", "archival_mode": "enabled",
            "suppression_reason": None, "metadata": c.capture_metadata(self.row), "body": body,
            "publish_date": (NOW - timedelta(minutes=1)).isoformat(),
        }
        self.server.archive_body = f'<link rel="canonical" href="{url}">{body}'.encode()
        reference = {"email_id": EMAIL, "url": url, "body_sha256": c.digest(body.encode())}
        result = evaluator.native_evidence(self.snapshot, self.row, reference, self.server.get, now=NOW)
        self.assertEqual(result["native_email_count"], 1)
        self.server.archive_body = b"<form>HTTP 200 is not native</form>"
        with self.assertRaises(c.ContractError):
            evaluator.native_evidence(self.snapshot, self.row, reference, self.server.get, now=NOW)

    def test_no_post_put_patch_delete_or_force_get_escape(self):
        client = policy.ReadOnlyClient("test-only-api-key")
        for method in ("POST", "PATCH", "PUT", "DELETE", "HEAD"):
            with self.assertRaises(c.ContractError):
                client.request(method, policy.API + "/newsletters")
        for url in (
            f"{policy.API}/newsletters/{NEWSLETTER}/sending-domain?force=true",
            f"{c.ENDPOINT}?email=person@example.invalid",
            "https://buttondown.com/unsubscribe/secret",
            "https://api.buttondown.com/v1/emails/send",
            "https://api.appstoreconnect.apple.com/v1/apps",
        ):
            with self.assertRaises(c.ContractError):
                policy.allowed_url(url)

    def test_snapshot_file_is_private_and_contains_no_credentials(self):
        folder = GEO / "tests" / (".owned-email-policy-" + uuid.uuid4().hex)
        target = folder / "policy.json"
        try:
            policy.write_private(target, self.snapshot)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(b"DO-NOT-SERIALIZE", target.read_bytes())
        finally:
            shutil.rmtree(folder)


if __name__ == "__main__":
    unittest.main()
