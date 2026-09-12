import copy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import io
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
import uuid

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import gen_owned_email_capture as capture
import gen_tool_email_capture as legacy
import owned_email_contract as c
import owned_email_readback as readback
import owned_email_sender as sender

NOW = datetime(2026, 9, 12, 6, 0, tzinfo=timezone.utc)
KEY = b"test-only-private-receipt-key-0001"
WEBHOOK_KEY = b"test-only-buttondown-webhook-key-1"
SUBSCRIBER = str(uuid.UUID(int=1))
NEWSLETTER = str(uuid.UUID(int=2))
EVENT = str(uuid.UUID(int=3))
EMAIL = str(uuid.UUID(int=4))
PROVIDER = "118326163"


def response(url, body, now=NOW, status=200):
    return {
        "method": "GET", "url": url, "final_url": url, "http_status": status,
        "body": body if isinstance(body, bytes) else c.json_bytes(body),
        "observed_at": now.isoformat(),
    }


def sources():
    files = c.source_files()
    return {
        key: {"repository": repository, "revision": revision * 40, "prefix": prefix,
              "files": files, "digest": c.digest(files)}
        for key, repository, revision, prefix in (
            ("growth", "alice51849/00_GrowthEngine", "a", "geo"),
            ("guide", "alice51849/ios-app-guide", "b", "_engine/geo"),
        )
    }


def availability():
    return {
        "schema": "lumi.owned-email-availability/v1", "source": "Apple iTunes Lookup API",
        "generated_at": (NOW - timedelta(minutes=5)).isoformat(), "ttl_seconds": 86400,
        "roster_digest": c.roster()["roster_digest"],
        "countries": {
            country: {
                "url": c.lookup_url(country), "final_url": c.lookup_url(country), "http_status": 200,
                "observed_at": (NOW - timedelta(minutes=6)).isoformat(),
                "app_ids": sorted(app["app_id"] for app in c.roster()["apps"].values()),
                "body_sha256": "a" * 64,
            }
            for country in set(c.LOCALE_STOREFRONTS.values()) - {"bd"}
        },
    }


def subscriber(row, kind="regular"):
    return {
        "id": SUBSCRIBER, "email_address": "consenting-reader@example.invalid",
        "creation_date": (NOW - timedelta(hours=1)).isoformat(),
        "type": kind, "source": "organic", "metadata": c.capture_metadata(row),
        "subscriber_import_id": None, "purchased_by": None, "email_transitions": [],
        "unsubscription_date": None, "bounce_date": None, "undeliverability_date": None,
    }


def state(**updates):
    return sender.seal({
        "schema": sender.STATE, "observed_at": NOW.isoformat(), "complete": True,
        "suppressed_subscriber_ids": [], "suppressed_email_hashes": [],
        "scope_suppressions": [], "attempts": [], **updates,
    }, KEY)


def resign(inventory):
    inventory["content_digest"] = c.digest({
        key: value for key, value in inventory.items() if key != "content_digest"
    })
    return inventory


class Form(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.forms, self.inputs, self.labels = [], [], []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            self.forms.append(dict(attrs))
        if tag == "input":
            self.inputs.append(dict(attrs))
        if tag == "label":
            self.labels.append(dict(attrs))


class OwnedEmailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_committed_source_files = staticmethod(c.committed_source_files)
        cls.git_fixture = mock.patch.object(c, "committed_source_files", return_value=c.source_files())
        cls.git_fixture.start()
        cls.availability = availability()
        cls.inventory, cls.outputs = capture.build(PROVIDER, sources(), cls.availability, now=NOW)
        cls.row = c.inventory_row(cls.inventory, "aibriefpack", "zh-Hant")
        cls.bn = c.inventory_row(cls.inventory, "aibriefpack", "bn-BD")
        cls.subscriber = subscriber(cls.row)
        pending_now = NOW - timedelta(minutes=1)
        cls.pending = sender.observe_pending(
            cls.row, SUBSCRIBER, receipt_key=KEY, now=pending_now,
            api_get=lambda url: response(url, subscriber(cls.row, "unactivated"), pending_now),
        )
        cls.event = c.json_bytes({
            "id": EVENT, "event_type": "subscriber.confirmed",
            "data": {"newsletter": NEWSLETTER, "subscriber": SUBSCRIBER},
        })
        cls.signature = "sha256=" + hmac.new(WEBHOOK_KEY, cls.event, hashlib.sha256).hexdigest()
        cls.consent = sender.confirm_pending(
            cls.row, cls.pending, cls.event, cls.signature,
            newsletter_id=NEWSLETTER, webhook_key=WEBHOOK_KEY, receipt_key=KEY,
            seen_event_ids=set(), now=NOW,
            api_get=lambda url: response(url, cls.subscriber),
        )

    @classmethod
    def tearDownClass(cls):
        cls.git_fixture.stop()

    def do_plan(self, *, proofs=None, state_receipt=None, current=None, row=None):
        row = row or self.row
        current = current or self.subscriber
        return sender.plan(
            self.inventory, self.availability, row["app_key"], row["locale"],
            proofs if proofs is not None else [self.consent],
            state_receipt=state_receipt or state(), receipt_key=KEY, now=NOW,
            api_get=lambda url: response(url, current),
        )

    def native_fixtures(self, row=None):
        row = row or self.row
        url = "https://buttondown.com/hourstag/archive/test-app-news/"
        body = (
            f'<p>{readback.binding_text(row)}</p>'
            f'<p>{c.consent_copy(row)["disclosure"]}</p>'
            f'<a href="{row["capture_url"]}">{row["app_name"]}</a>'
        )
        if row["app_store_url"]:
            body += f'<a href="{row["app_store_url"]}">App Store</a>'
        email = {
            "id": EMAIL, "absolute_url": url, "status": "sent", "archival_mode": "enabled",
            "metadata": c.capture_metadata(row), "body": body, "suppression_reason": None,
            "publish_date": (NOW - timedelta(minutes=2)).isoformat(),
        }
        reference = {"email_id": EMAIL, "url": url, "body_sha256": c.digest(body.encode())}
        archive = f'<html><head><link rel="canonical" href="{url}"></head><body>{body}</body></html>'.encode()
        return reference, email, archive

    def test_copy_exact_official_50_and_legacy_scope_remains_separate(self):
        copies = c.load_copy()
        self.assertEqual(set(copies), set(c.OFFICIAL_LOCALES))
        self.assertEqual(len(legacy._load_config()["copy"]), 50)
        for locale in c.OFFICIAL_LOCALES:
            block = legacy._block(legacy._load_config(), locale)
            self.assertIn(copies[locale]["email_label"], block)
            self.assertIn('name="metadata__owned_campaign" value="new_free_tools_v1"', block)
            self.assertNotIn(c.CAMPAIGN, block)
            self.assertIn(copies[locale]["tools_consent"], readback.Body(block).visible())

    def test_missing_or_unofficial_copy_never_falls_back_to_english(self):
        config = legacy._load_config()
        for locale in ("zz", "bn", "fr-BE", "zh", "pt", "bg", "sr"):
            self.assertEqual(legacy._copy_for(config, locale), {})
            self.assertEqual(legacy._block(config, locale), "")
        self.assertEqual(legacy._copy_for(config, "en"), config["copy"]["en-US"])

    def test_legacy_capture_is_idempotent_and_disabled_removes_old_form(self):
        config = legacy._load_config()
        page = '<html lang="bn-BD"><body><main>Existing tool</main></body></html>'
        updated = legacy.apply_capture(page, config)
        self.assertEqual(updated, legacy.apply_capture(updated, config))
        self.assertEqual(page, legacy.apply_capture(updated, {**config, "enabled": False}))
        with self.assertRaises(ValueError):
            legacy._block({**config, "endpoint": "https://example.invalid/subscribe"}, "en-US")

    def test_all_2350_real_forms_have_explicit_consent_and_native_disclosure(self):
        self.assertEqual(len(self.inventory["rows"]), 2350)
        self.assertEqual(len({(r["app_id"], r["locale"]) for r in self.inventory["rows"]}), 2350)
        copies = c.load_copy()
        for row in self.inventory["rows"]:
            with self.subTest(app=row["app_key"], locale=row["locale"]):
                source = self.outputs[row["capture_path"]].decode()
                form = Form(source)
                self.assertEqual(len(form.forms), 1)
                self.assertEqual(form.forms[0]["action"], c.ENDPOINT)
                self.assertEqual(form.forms[0]["method"], "post")
                fields = {field["name"]: field for field in form.inputs}
                self.assertEqual(fields["email"]["type"], "email")
                self.assertIn("required", fields["email"])
                consent = fields["metadata__owned_consent"]
                self.assertEqual(consent["type"], "checkbox")
                self.assertIn("required", consent)
                self.assertNotIn("checked", consent)
                for key, value in c.capture_metadata(row).items():
                    self.assertEqual(fields["metadata__" + key]["value"], value)
                for text in c.consent_copy(row, copies).values():
                    self.assertIn(text, readback.Body(source).visible())
                self.assertNotIn("<script", source)
                self.assertNotIn("requestSubmit", source)
                self.assertEqual(c.digest(self.outputs[row["capture_path"]]), row["content_sha256"])

    def test_other_49_storefront_pt_ct_exact_and_bn_null_without_fallback(self):
        for row in self.inventory["rows"]:
            if row["locale"] == "bn-BD":
                self.assertIsNone(row["app_store_url"])
                self.assertEqual(row["conversion_campaign"], "N/A")
                self.assertNotIn(b"apps.apple.com", self.outputs[row["capture_path"]])
                self.assertNotIn(b"itunes.apple.com", self.outputs[row["capture_path"]])
                self.assertFalse(row["market_availability"]["publishable"])
            else:
                url = urlsplit(row["app_store_url"])
                self.assertEqual(url.netloc, "apps.apple.com")
                self.assertEqual(url.path, f'/{c.LOCALE_STOREFRONTS[row["locale"]]}/app/id{row["app_id"]}')
                params = parse_qs(url.query)
                self.assertEqual(params, {"pt": [PROVIDER], "ct": [row["conversion_campaign"]], "mt": ["8"]})
                self.assertLessEqual(len(params["ct"][0]), 30)
            self.assertNotRegex(self.outputs[row["capture_path"]].decode(), r"[$€£₹¥]\s*\d")
        self.assertEqual(self.inventory["conversion_cells"], 47 * 49)

    def test_missing_provider_token_is_blocking_not_untracked_fallback(self):
        for token in ("", "None", None, "1&ct=spoof"):
            with self.assertRaises(c.ContractError):
                c.rows(token)

    def test_copy_missing_locale_is_blocking(self):
        raw = c.parse_json((GEO / "owned_email_copy.json").read_bytes())
        raw["locales"].pop("ur-PK")
        with mock.patch.object(Path, "read_bytes", return_value=c.json_bytes(raw)):
            with self.assertRaises(ValueError):
                c.load_copy()

    def test_source_digest_and_parity_fail_closed(self):
        for side in ("growth", "guide"):
            document = copy.deepcopy(self.inventory)
            document["sources"][side]["files"]["owned_email_sender.py"] = "0" * 64
            resign(document)
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)

    def test_source_revision_and_repository_are_required(self):
        for field, value in (("revision", "main"), ("repository", "other/repo"), ("prefix", "wrong")):
            document = copy.deepcopy(self.inventory)
            document["sources"]["growth"][field] = value
            resign(document)
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)

    def test_full_length_fake_git_sha_is_not_provenance(self):
        document = copy.deepcopy(self.inventory)
        local = "growth" if c.git_context(str(GEO))[1] == "geo" else "guide"
        document["sources"][local]["revision"] = "0" * 40
        resign(document)
        with mock.patch.object(c, "committed_source_files", side_effect=self.real_committed_source_files):
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)

    def test_inventory_or_availability_stale_future_and_wrong_digest_fail_closed(self):
        for delta in (timedelta(days=-2), timedelta(seconds=1)):
            document = copy.deepcopy(self.inventory)
            document["generated_at"] = (NOW + delta).isoformat()
            resign(document)
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)
        changed = copy.deepcopy(self.availability)
        changed["countries"]["tw"]["body_sha256"] = "b" * 64
        with self.assertRaises(c.ContractError):
            c.validate_inventory(self.inventory, changed, now=NOW)
        with self.assertRaises(c.ContractError):
            c.validate_inventory(self.inventory, self.availability, now=NOW + timedelta(days=2))

    def test_incomplete_or_redirected_storefront_source_is_blocking(self):
        for change in ("app", "country", "redirect", "source", "status"):
            changed = copy.deepcopy(self.availability)
            if change == "app":
                changed["countries"]["us"]["app_ids"].pop()
            elif change == "country":
                changed["countries"].pop("tw")
            elif change == "redirect":
                changed["countries"]["tw"]["final_url"] = c.lookup_url("us")
            elif change == "source":
                changed["source"] = "workflow_success"
            else:
                changed["countries"]["tw"]["http_status"] = True
            with self.assertRaises(c.ContractError):
                c.validate_availability(changed, NOW)

    def test_one_unverified_app_market_retains_content_but_blocks_sender(self):
        av = copy.deepcopy(self.availability)
        av["countries"]["tw"]["app_ids"].remove(self.row["app_id"])
        inventory, outputs = capture.build(PROVIDER, sources(), av, now=NOW)
        self.assertEqual(inventory["capture_count"], 2350)
        self.assertEqual(inventory["unverified_conversion_cells"], 1)
        self.assertIn(self.row["capture_path"], outputs)
        fetch = mock.Mock(side_effect=AssertionError("no recipient lookup for unverified app market"))
        result = sender.plan(
            inventory, av, self.row["app_key"], self.row["locale"], [self.consent],
            api_get=fetch, now=NOW,
        )
        self.assertEqual(result["reason"], "app_storefront_unverified")
        self.assertFalse(result["send_allowed"])
        fetch.assert_not_called()

    def test_counts_cannot_promote_content_to_subscribers_or_delivery(self):
        for field, value in (("verified_subscribers", 1), ("native_email_count", 1), ("subscriber_count", 2350)):
            document = copy.deepcopy(self.inventory)
            document[field] = value
            resign(document)
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)

    def test_duplicate_missing_wrong_scope_and_bn_fallback_inventory_are_blocked(self):
        for mutation in ("missing", "duplicate", "scope", "bn"):
            document = copy.deepcopy(self.inventory)
            if mutation == "missing":
                document["rows"].pop()
            elif mutation == "duplicate":
                document["rows"][1] = document["rows"][0]
            elif mutation == "scope":
                document["rows"][0]["campaign"] = "new_free_tools_v1"
            else:
                next(r for r in document["rows"] if r["locale"] == "bn-BD")["app_store_url"] = self.row["app_store_url"]
            resign(document)
            with self.assertRaises(c.ContractError):
                c.validate_inventory(document, self.availability, now=NOW)

    def test_zero_audience_is_noop_without_auth_get_state_or_send(self):
        fetch = mock.Mock(side_effect=AssertionError("no network allowed"))
        result = sender.plan(None, None, "aibriefpack", "en-US", [], api_get=fetch)
        self.assertEqual(result["action"], "no_op")
        self.assertEqual(result["eligible_count"], 0)
        self.assertFalse(result["send_allowed"])
        self.assertEqual(result["send_requests"], 0)
        fetch.assert_not_called()

    def test_bn_sender_is_na_and_never_gets_a_fallback_cta(self):
        fetch = mock.Mock(side_effect=AssertionError("no recipient lookup for N/A market"))
        for proofs in ([], [self.consent]):
            result = sender.plan(
                self.inventory, self.availability, self.bn["app_key"], "bn-BD",
                proofs, api_get=fetch, now=NOW,
            )
            self.assertIsNone(result["app_store_url"])
            self.assertEqual(result["conversion_campaign"], "N/A")
            self.assertFalse(result["send_allowed"])
        fetch.assert_not_called()

    def test_verified_double_opt_in_produces_plan_only_never_a_send(self):
        result = self.do_plan()
        self.assertEqual(result["eligible_subscriber_ids"], [SUBSCRIBER])
        self.assertEqual(result["action"], "plan_only")
        self.assertFalse(result["send_allowed"])
        self.assertEqual(result["send_requests"], 0)
        self.assertEqual(result["native_email_count"], 0)

    def test_regular_status_or_caller_verified_boolean_is_not_double_opt_in(self):
        for fake in (
            {"verified": True, "double_opt_in": True, "subscriber_id": SUBSCRIBER},
            {"payload": {"schema": sender.CONSENT}, "signature": "0" * 64},
            self.pending,
        ):
            self.assertEqual(self.do_plan(proofs=[fake])["eligible_count"], 0)

    def test_pending_must_be_real_unactivated_organic_signup(self):
        with self.assertRaises(c.ContractError):
            sender.observe_pending(
                self.row, SUBSCRIBER, receipt_key=KEY, now=NOW,
                api_get=lambda url: response(url, self.subscriber),
            )

    def test_confirmation_requires_signed_provider_event_and_no_replay(self):
        for signature, event, seen in (
            ("sha256=" + "0" * 64, self.event, set()),
            (self.signature, self.event, {EVENT}),
            (self.signature, self.event.replace(b"subscriber.confirmed", b"subscriber.created"), set()),
        ):
            with self.assertRaises(c.ContractError):
                sender.confirm_pending(
                    self.row, self.pending, event, signature, newsletter_id=NEWSLETTER,
                    webhook_key=WEBHOOK_KEY, receipt_key=KEY, seen_event_ids=seen, now=NOW,
                    api_get=lambda url: response(url, self.subscriber),
                )

    def test_confirmation_cannot_change_scope_after_the_first_opt_in(self):
        current = copy.deepcopy(self.subscriber)
        current["metadata"]["owned_locale"] = "en-US"
        with self.assertRaises(c.ContractError):
            sender.confirm_pending(
                self.row, self.pending, self.event, self.signature,
                newsletter_id=NEWSLETTER, webhook_key=WEBHOOK_KEY, receipt_key=KEY,
                seen_event_ids=set(), now=NOW, api_get=lambda url: response(url, current),
            )

    def test_persistent_confirmation_ledger_deduplicates_retries(self):
        directory = GEO / "tests" / (".owned-email-" + uuid.uuid4().hex)
        path = directory / "consents.sqlite"
        ledger = sender.ConfirmationLedger(path)
        try:
            kwargs = dict(
                newsletter_id=NEWSLETTER, webhook_key=WEBHOOK_KEY, receipt_key=KEY, now=NOW,
                api_get=lambda url: response(url, self.subscriber),
            )
            first = ledger.confirm(self.row, self.pending, self.event, self.signature, **kwargs)
            self.assertEqual(first, ledger.confirm(self.row, self.pending, self.event, self.signature, **kwargs))
            self.assertEqual(ledger.db.execute("SELECT count(*) FROM confirmations").fetchone()[0], 1)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(b"consenting-reader@", path.read_bytes())
        finally:
            ledger.close()
            shutil.rmtree(directory)

    def test_app_locale_campaign_consent_must_all_match(self):
        for field, value in (("app_id", "1234567890"), ("locale", "ja"), ("campaign", "new_free_tools_v1")):
            receipt = copy.deepcopy(self.consent)
            receipt["payload"]["scope"][field] = value
            receipt = sender.seal(receipt["payload"], KEY)
            self.assertEqual(self.do_plan(proofs=[receipt])["eligible_count"], 0)

    def test_unsubscribe_suppression_bounce_import_and_auto_subscription_deny(self):
        for field, value in (
            ("type", "unactivated"), ("type", "unsubscribed"), ("type", "blocked"),
            ("type", "complained"), ("type", "undeliverable"), ("type", "removed"),
            ("unsubscription_date", NOW.isoformat()), ("bounce_date", NOW.isoformat()),
            ("undeliverability_date", NOW.isoformat()), ("source", "api"), ("source", "import"),
            ("subscriber_import_id", "import1"), ("purchased_by", "list@example.invalid"),
            ("email_address", "different@example.invalid"), ("email_transitions", [{"from": "old"}]),
        ):
            with self.subTest(field=field, value=value):
                current = {**self.subscriber, field: value}
                self.assertEqual(self.do_plan(current=current)["eligible_count"], 0)

    def test_current_scope_changes_cannot_reuse_old_consent(self):
        for field in ("owned_app", "owned_app_id", "owned_locale", "owned_campaign", "owned_consent", "owned_consent_digest"):
            current = copy.deepcopy(self.subscriber)
            current["metadata"][field] = "changed"
            self.assertEqual(self.do_plan(current=current)["eligible_count"], 0)

    def test_suppression_works_by_id_address_and_exact_scope(self):
        for changes in (
            {"suppressed_subscriber_ids": [SUBSCRIBER]},
            {"suppressed_email_hashes": [sender.email_hash(self.subscriber["email_address"])]},
            {"scope_suppressions": [{"subscriber_id": SUBSCRIBER, "scope": c.scope(self.row)}]},
        ):
            result = self.do_plan(state_receipt=state(**changes))
            self.assertEqual(result["eligible_count"], 0)
            self.assertEqual(result["rejected"], {"suppressed": 1})

    def test_sender_requires_fresh_complete_authenticated_state(self):
        for changes in (
            {"observed_at": (NOW - timedelta(minutes=6)).isoformat()},
            {"complete": False}, {"attempts": None},
        ):
            with self.assertRaises(c.ContractError):
                self.do_plan(state_receipt=state(**changes))
        bad = state()
        bad["payload"]["complete"] = False
        with self.assertRaises(c.ContractError):
            self.do_plan(state_receipt=bad)

    def test_cooldown_is_per_app_locale_campaign_and_counts_ambiguous_attempts(self):
        original = {
            "attempt_id": "attempt-1", "scope": c.scope(self.row),
            "attempted_at": (NOW - timedelta(days=1)).isoformat(),
            "subscriber_ids": [SUBSCRIBER], "status": "unknown",
            "email_sha256s": [sender.email_hash(self.subscriber["email_address"])],
        }
        result = self.do_plan(state_receipt=state(attempts=[original]))
        self.assertEqual(result["reason"], "app_locale_campaign_cooldown")
        other_key, other_app = next((key, app) for key, app in c.roster()["apps"].items()
                                   if key != self.row["app_key"])
        for scope_update in (
            {"app_key": other_key, "app_id": other_app["app_id"]},
            {"locale": "ja"}, {"campaign": "another_campaign"},
        ):
            attempt = copy.deepcopy(original)
            attempt["scope"].update(scope_update)
            self.assertEqual(self.do_plan(state_receipt=state(attempts=[attempt]))["eligible_count"], 1)
        attempt = copy.deepcopy(original)
        attempt["scope"]["app_id"] = "wrong_id"
        with self.assertRaises(c.ContractError):
            self.do_plan(state_receipt=state(attempts=[attempt]))

    def test_daily_global_cap_and_per_recipient_cap(self):
        attempt = {
            "attempt_id": "other-campaign", "scope": {**c.scope(self.row), "campaign": "another"},
            "attempted_at": (NOW - timedelta(minutes=1)).isoformat(),
            "subscriber_ids": [SUBSCRIBER], "status": "reserved",
            "email_sha256s": [sender.email_hash(self.subscriber["email_address"])],
        }
        result = self.do_plan(state_receipt=state(attempts=[attempt]))
        self.assertEqual(result["rejected"], {"recipient_daily_cap": 1})
        attempt["subscriber_ids"] = [NEWSLETTER]
        self.assertEqual(self.do_plan(state_receipt=state(attempts=[attempt]))["rejected"], {"recipient_daily_cap": 1})
        attempt["subscriber_ids"] = [str(uuid.UUID(int=i)) for i in range(100, 200)]
        attempt["email_sha256s"] = [c.digest(str(i)) for i in range(100, 200)]
        self.assertEqual(self.do_plan(state_receipt=state(attempts=[attempt]))["reason"], "daily_cap")

    def test_duplicate_receipts_do_not_expand_audience(self):
        self.assertEqual(self.do_plan(proofs=[self.consent] * 4)["eligible_count"], 1)

    def test_capture_http200_is_only_content_not_subscriber_or_native(self):
        row = self.row
        result = readback.capture_readback(
            row, public_get=lambda url: response(url, self.outputs[row["capture_path"]]), now=NOW,
        )
        self.assertEqual(result["native_email_count"], 0)
        self.assertEqual(result["verified_subscribers"], 0)
        self.assertEqual(result["subscriber_count"], "UNKNOWN")
        with self.assertRaises(c.ContractError):
            readback.capture_readback(row, public_get=lambda url: response(url, b"generic HTTP 200"), now=NOW)

    def test_native_requires_email_id_and_public_get_body_bound_to_scope(self):
        reference, email, archive = self.native_fixtures()
        result = readback.native_readback(
            self.row, reference, api_get=lambda url: response(url, email),
            public_get=lambda url: response(url, archive), now=NOW,
        )
        self.assertEqual(result["native_email_count"], 1)
        self.assertEqual(result["delivered_subscribers"], "UNKNOWN")
        self.assertEqual(result["app_id"], self.row["app_id"])
        self.assertEqual(result["locale"], self.row["locale"])

    def test_native_rejects_workflow_queue_receipt_spoof_and_form_index(self):
        reference, email, archive = self.native_fixtures()
        for fake in (
            {"success": True, "http_status": 200, "native_email_count": 2350},
            {**reference, "queue_status": "sent"},
            {**reference, "url": "https://buttondown.com/hourstag/archive/"},
            {**reference, "url": "https://buttondown.com/api/emails/embed-subscribe/hourstag"},
            {**reference, "url": self.row["capture_url"]},
            {**reference, "url": "https://buttondown.com.attacker.invalid/hourstag/archive/news/"},
        ):
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, fake, api_get=lambda url: response(url, email),
                    public_get=lambda url: response(url, archive), now=NOW,
                )

    def test_native_404_and_http200_unrelated_body_are_not_delivery(self):
        reference, email, archive = self.native_fixtures()
        for api_status, public_status, body in (
            (404, 200, archive), (200, 404, archive), (200, 200, b"<form>Subscribe</form>"),
            (200, 200, b"<h1>Workflow completed successfully</h1>"),
        ):
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, reference, api_get=lambda url: response(url, email, status=api_status),
                    public_get=lambda url: response(url, body, status=public_status), now=NOW,
                )

    def test_native_sent_state_and_metadata_cannot_be_spoofed(self):
        reference, original, archive = self.native_fixtures()
        mutations = [
            ("id", SUBSCRIBER), ("status", "draft"), ("status", "scheduled"),
            ("archival_mode", "disabled"), ("absolute_url", self.row["capture_url"]),
            ("suppression_reason", "no_recipients"), ("body", "unrelated content"),
            ("publish_date", (NOW + timedelta(hours=1)).isoformat()),
        ]
        for field, value in mutations:
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, reference, api_get=lambda url: response(url, {**original, field: value}),
                    public_get=lambda url: response(url, archive), now=NOW,
                )
        for field in ("owned_app_id", "owned_locale", "owned_campaign", "owned_consent_digest"):
            email = copy.deepcopy(original)
            email["metadata"][field] = "spoof"
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, reference, api_get=lambda url: response(url, email),
                    public_get=lambda url: response(url, archive), now=NOW,
                )

    def test_native_hidden_marker_redirect_stale_readback_are_blocked(self):
        reference, email, archive = self.native_fixtures()
        for body, final_url, observed in (
            (archive.replace(b"<body>", b"<body><script>").replace(b"</body>", b"</script></body>"),
             reference["url"], NOW),
            (archive, "https://buttondown.com/hourstag/archive/another/", NOW),
            (archive, reference["url"], NOW - timedelta(minutes=6)),
        ):
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, reference, api_get=lambda url: response(url, email),
                    public_get=lambda url: {**response(url, body, observed), "final_url": final_url}, now=NOW,
                )

    def test_native_bn_content_can_exist_but_no_storefront_link_is_accepted(self):
        reference, email, archive = self.native_fixtures(self.bn)
        result = readback.native_readback(
            self.bn, reference, api_get=lambda url: response(url, email),
            public_get=lambda url: response(url, archive), now=NOW,
        )
        self.assertEqual(result["native_email_count"], 1)
        email["body"] += f'<a href="{self.row["app_store_url"]}">App Store</a>'
        reference["body_sha256"] = c.digest(email["body"].encode())
        with self.assertRaises(c.ContractError):
            readback.native_readback(
                self.bn, reference, api_get=lambda url: response(url, email),
                public_get=lambda url: response(url, archive), now=NOW,
            )

    def test_native_hard_price_and_extra_wrong_storefront_are_blocked(self):
        for addition in (
            "<p>Only $4.99</p>",
            '<a href="https://apps.apple.com/us/app/id1234567890?pt=1&ct=wrong&mt=8">Other store</a>',
        ):
            reference, email, _ = self.native_fixtures()
            email["body"] += addition
            reference["body_sha256"] = c.digest(email["body"].encode())
            archive = (
                f'<link rel="canonical" href="{reference["url"]}">' + email["body"]
            ).encode()
            with self.assertRaises(c.ContractError):
                readback.native_readback(
                    self.row, reference, api_get=lambda url: response(url, email),
                    public_get=lambda url: response(url, archive), now=NOW,
                )

    def test_http200_subscriber_census_is_not_double_opt_in_or_native(self):
        fetch = mock.Mock(side_effect=lambda url: response(url, {
            "count": 1, "results": [{"id": SUBSCRIBER, "type": "regular"}],
        }))
        census = readback.subscriber_census(api_get=fetch, now=NOW)
        self.assertEqual(census["subscriber_count"], 1)
        self.assertEqual(census["provider_regular_count"], 1)
        self.assertEqual(census["verified_double_opt_in_count"], 0)
        self.assertEqual(census["native_email_count"], 0)
        self.assertEqual(fetch.call_count, 1)

    def test_subscriber_census_zero_and_complete_pagination(self):
        empty = readback.subscriber_census(
            api_get=lambda url: response(url, {"count": 0, "results": []}), now=NOW,
        )
        self.assertEqual(empty["subscriber_count"], 0)
        seen = []

        def fetch(url):
            seen.append(url)
            return response(url, {
                "count": 2, "results": [{"id": SUBSCRIBER if len(seen) == 1 else NEWSLETTER}],
            })

        self.assertEqual(readback.subscriber_census(api_get=fetch, now=NOW)["subscriber_count"], 2)
        self.assertEqual(seen[-1], readback.API + "/subscribers?page=2")

    def test_census_duplicate_truncation_and_forged_count_fail_closed(self):
        for payload in (
            {"count": True, "results": []}, {"count": 1, "results": []},
            {"count": 1, "results": [{"id": SUBSCRIBER}, {"id": SUBSCRIBER}]},
        ):
            with self.assertRaises(c.ContractError):
                readback.subscriber_census(api_get=lambda url: response(url, payload), now=NOW)

    def test_census_without_credentials_is_unknown_and_never_makes_a_request(self):
        output = io.StringIO()
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            readback, "http_get", side_effect=AssertionError("no authentication")
        ) as fetch, mock.patch("sys.stdout", output):
            self.assertEqual(readback.main(["--subscriber-count"]), 0)
        self.assertEqual(json.loads(output.getvalue())["subscriber_count"], "UNKNOWN")
        fetch.assert_not_called()

    def test_live_readback_clock_is_checked_after_the_get_not_before(self):
        later = NOW + timedelta(seconds=2)
        url = self.row["capture_url"]
        body, _ = readback.checked_get(
            url, lambda value: response(value, b"body", later), lambda: later,
        )
        self.assertEqual(body, b"body")
        with self.assertRaises(c.ContractError):
            readback.checked_get(url, lambda value: response(value, b"body", later), NOW)

    def test_transport_has_no_mutation_or_auto_subscribe_escape(self):
        client = readback.ButtondownReadOnly("test-only-api-key")
        with mock.patch.object(readback, "http_get") as fetch:
            for method in ("POST", "PATCH", "PUT", "DELETE"):
                with self.assertRaises(c.ContractError):
                    client.request(method, readback.API + "/subscribers")
            fetch.assert_not_called()
        for url in (
            "http://api.buttondown.com/v1/subscribers",
            "https://api.buttondown.com/v1/subscribers?type=regular",
            "https://api.buttondown.com/v1/emails/send",
            "https://api.buttondown.com/v1/subscribers/../emails",
            "https://api.appstoreconnect.apple.com/v1/apps",
        ):
            with self.assertRaises(c.ContractError):
                readback._allowed_url(url, authenticated=True)

    def test_local_generation_roundtrip_and_stale_file_rejection(self):
        directory = GEO / "tests" / (".owned-email-" + uuid.uuid4().hex)
        try:
            capture.write(directory, self.inventory, self.availability, self.outputs)
            checked = capture.check(directory, now=NOW)
            self.assertEqual(checked["content_digest"], self.inventory["content_digest"])
            target = directory / self.row["capture_path"]
            target.write_bytes(target.read_bytes().replace(b"metadata__owned_app", b"metadata__wrong_app", 1))
            with self.assertRaises(c.ContractError):
                capture.check(directory, now=NOW)
        finally:
            if directory.exists():
                shutil.rmtree(directory)


if __name__ == "__main__":
    unittest.main()
