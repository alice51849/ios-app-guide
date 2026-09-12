#!/usr/bin/env python3
"""Policy-bound consent/withdrawal evaluation. All outcomes remain no-send."""
from __future__ import annotations

from collections import Counter
import hashlib
import hmac
import os
from pathlib import Path
import sqlite3
import uuid

import buttondown_consent_policy as policy
import owned_email_contract as c
import owned_email_readback as readback
import owned_email_sender as legacy

PENDING = "lumi.buttondown-account-pending/v1"
CONFIRMED = "lumi.buttondown-account-confirmed/v1"
REVOCATIONS = "lumi.buttondown-account-revocations/v1"
REQUIRED_SUBSCRIBER_FIELDS = {
    "id", "email_address", "creation_date", "type", "source", "metadata",
    "subscriber_import_id", "purchased_by", "unsubscription_date", "bounce_date",
    "undeliverability_date", "email_transitions", "transitions",
}
PERMANENT = {"subscriber.complained", "subscriber.deleted", "subscriber.type.changed"}


def zero(reason):
    return {
        "action": "no_op", "status": "BLOCKED", "reason": reason, "eligible_subscriber_ids": [],
        "verified_audience_count": 0, "subscriber_count": "UNKNOWN", "native_count": 0,
        "send_allowed": False, "post_requests": 0,
    }


def verify_event(body, signature, webhook_key, snapshot, expected_type=None):
    if not isinstance(body, bytes) or not 0 < len(body) <= 65536:
        raise c.ContractError("raw signed webhook bytes are required")
    expected = "sha256=" + hmac.new(legacy._key(webhook_key), body, hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
        raise c.ContractError("webhook spoof or signature mismatch")
    event = c.parse_json(body)
    if (
        not isinstance(event, dict) or not isinstance(event.get("id"), str)
        or not readback.ID.fullmatch(event["id"]) or not isinstance(event.get("data"), dict)
        or event["data"].get("newsletter") != snapshot["binding"]["newsletter_id"]
        or not isinstance(event["data"].get("subscriber"), str)
        or not readback.ID.fullmatch(event["data"]["subscriber"])
        or (expected_type is not None and event.get("event_type") != expected_type)
    ):
        raise c.ContractError("webhook event/account/newsletter identity mismatch")
    return event


def revocation_state(receipt, key, snapshot, now):
    value = legacy.unseal(receipt, key, REVOCATIONS)
    if value.get("account_binding") != snapshot["binding_digest"] or value.get("complete") is not True:
        raise c.ContractError("account-bound complete revocation history is required")
    c.fresh(value.get("observed_at"), now, 300)
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise c.ContractError("revocation history is unknown")
    seen = set()
    for entry in entries:
        if (
            not isinstance(entry, dict) or not isinstance(entry.get("event_id"), str)
            or not readback.ID.fullmatch(entry["event_id"]) or entry["event_id"] in seen
            or entry.get("event_type") not in {"subscriber.unsubscribed", *PERMANENT}
            or not isinstance(entry.get("subscriber_id"), str) or not readback.ID.fullmatch(entry["subscriber_id"])
            or not isinstance(entry.get("email_sha256"), str) or not c.HEX.fullmatch(entry["email_sha256"])
            or c.timestamp(entry.get("revoked_at")) > now
        ):
            raise c.ContractError("invalid or replayed revocation history")
        seen.add(entry["event_id"])
    return value


def prior_revocations(state, subscriber_id, email_sha256):
    return [entry for entry in state["entries"]
            if entry["subscriber_id"] == subscriber_id or entry["email_sha256"] == email_sha256]


def subscriber_get(subscriber_id, row, get, now, *, allowed_types):
    if not isinstance(subscriber_id, str) or not readback.ID.fullmatch(subscriber_id):
        raise c.ContractError("named subscriber ID required")
    value, observation, _ = policy.observe(
        f"{policy.API}/subscribers/{subscriber_id}", get, now, require_authenticated=True,
    )
    if (
        not isinstance(value, dict) or not REQUIRED_SUBSCRIBER_FIELDS <= set(value)
        or value.get("id") != subscriber_id or value.get("type") not in allowed_types
        or value.get("source") != "organic" or value.get("subscriber_import_id") is not None
        or value.get("purchased_by") is not None or value.get("bounce_date") is not None
        or value.get("undeliverability_date") is not None or value.get("email_transitions") != []
        or not isinstance(value.get("transitions"), list)
        or value.get("metadata") != c.capture_metadata(row)
    ):
        raise c.ContractError("subscriber status/scope/suppression fields are missing or unsafe")
    legacy.email_hash(value["email_address"])
    if c.timestamp(value["creation_date"]) > (now() if callable(now) else now):
        raise c.ContractError("future subscriber creation timestamp")
    if value["unsubscription_date"] is not None:
        c.timestamp(value["unsubscription_date"])
    return value, observation


def pending(
    snapshot, row, subscriber_id, *, get, receipt_key, revocations, now=None,
):
    current = policy.refresh_match(snapshot, get, now=now)
    clock = c.utcnow if now is None else lambda: now
    now = clock()
    c.validate_row(row)
    state = revocation_state(revocations, receipt_key, current, now)
    value, observation = subscriber_get(subscriber_id, row, get, clock, allowed_types={"unactivated"})
    address = legacy.email_hash(value["email_address"])
    prior = prior_revocations(state, subscriber_id, address)
    if any(entry["event_type"] in PERMANENT for entry in prior):
        raise c.ContractError("complaint/deletion/blocked suppression cannot be cleared by signup")
    last = max((c.timestamp(entry["revoked_at"]) for entry in prior), default=None)
    if value["unsubscription_date"]:
        observed = c.timestamp(value["unsubscription_date"])
        last = max(last, observed) if last else observed
    if last and last >= now:
        raise c.ContractError("new opt-in must follow the latest unsubscribe")
    return legacy.seal({
        "schema": PENDING, "account_binding": current["binding_digest"],
        "configuration_digest": current["configuration_digest"],
        "newsletter_id": current["binding"]["newsletter_id"], "subscriber_id": subscriber_id,
        "email_sha256": address, "scope": c.scope(row), "consent_digest": row["consent_digest"],
        "metadata": c.capture_metadata(row), "generation": str(uuid.uuid4()),
        "observed_at": clock().isoformat(), "subscriber_created_at": value["creation_date"],
        "last_revocation_at": last.isoformat() if last else None, "provider_get": observation,
    }, receipt_key)


def confirmed(
    snapshot, row, pending_receipt, body, signature, *, get, receipt_key, webhook_key,
    revocations, processed_event_ids, now=None,
):
    current = policy.refresh_match(snapshot, get, now=now)
    clock = c.utcnow if now is None else lambda: now
    now = clock()
    saved = legacy.unseal(pending_receipt, receipt_key, PENDING)
    c.fresh(saved.get("observed_at"), now, legacy.MAX_PENDING_AGE)
    if (
        saved.get("account_binding") != current["binding_digest"]
        or saved.get("configuration_digest") != current["configuration_digest"]
        or saved.get("scope") != c.scope(row) or saved.get("metadata") != c.capture_metadata(row)
        or saved.get("consent_digest") != row["consent_digest"]
    ):
        raise c.ContractError("pending account/configuration/scope changed")
    event = verify_event(body, signature, webhook_key, current, "subscriber.confirmed")
    if event["id"] in processed_event_ids or event["data"]["subscriber"] != saved.get("subscriber_id"):
        raise c.ContractError("confirmation replay or subscriber mismatch")
    state = revocation_state(revocations, receipt_key, current, now)
    value, observation = subscriber_get(saved["subscriber_id"], row, get, clock, allowed_types={"regular"})
    address = legacy.email_hash(value["email_address"])
    if address != saved["email_sha256"] or value["creation_date"] != saved["subscriber_created_at"]:
        raise c.ContractError("subscriber address or identity generation changed")
    prior = prior_revocations(state, saved["subscriber_id"], address)
    if any(
        entry["event_type"] in PERMANENT or c.timestamp(entry["revoked_at"]) >= c.timestamp(saved["observed_at"])
        for entry in prior
    ) or value["unsubscription_date"] and c.timestamp(value["unsubscription_date"]) >= c.timestamp(saved["observed_at"]):
        raise c.ContractError("unsubscribe after pending invalidates this confirmation")
    return legacy.seal({
        **saved, "schema": CONFIRMED, "confirmed_at": clock().isoformat(),
        "confirmation_timestamp_kind": "verified_event_observed_at_not_provider_click_time",
        "confirmation_event_id": event["id"], "confirmation_body_sha256": c.digest(body),
        "pending_receipt_sha256": c.digest(pending_receipt), "provider_get": observation,
    }, receipt_key)


class ConsentLedger:
    """Atomic event replay protection; only hashes and scoped sealed receipts are stored."""
    def __init__(self, path):
        path = Path(path)
        if path.is_symlink():
            raise c.ContractError("consent ledger cannot be a symlink")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        path.chmod(0o600)
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS account_confirmations "
            "(event_id TEXT PRIMARY KEY, binding TEXT NOT NULL, body_digest TEXT NOT NULL, receipt BLOB NOT NULL)"
        )
        self.db.commit()

    def close(self):
        self.db.close()

    def accept(self, snapshot, row, pending_receipt, body, signature, **kwargs):
        policy.validate(snapshot, now=kwargs.get("now"))
        event = verify_event(body, signature, kwargs["webhook_key"], snapshot, "subscriber.confirmed")
        pending_value = legacy.unseal(pending_receipt, kwargs["receipt_key"], PENDING)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute(
                "SELECT binding,body_digest,receipt FROM account_confirmations WHERE event_id=?", (event["id"],),
            ).fetchone()
            if existing:
                receipt = c.parse_json(existing[2])
                value = legacy.unseal(receipt, kwargs["receipt_key"], CONFIRMED)
                if (
                    existing[0] != snapshot["binding_digest"] or existing[1] != c.digest(body)
                    or value["scope"] != c.scope(row)
                    or value["configuration_digest"] != snapshot["configuration_digest"]
                    or value["generation"] != pending_value["generation"]
                ):
                    raise c.ContractError("old confirmation event cannot authorize a new account/scope/generation")
                return receipt
            receipt = confirmed(
                snapshot, row, pending_receipt, body, signature, processed_event_ids=frozenset(), **kwargs,
            )
            self.db.execute(
                "INSERT INTO account_confirmations VALUES(?,?,?,?)",
                (event["id"], snapshot["binding_digest"], c.digest(body), c.json_bytes(receipt)),
            )
            return receipt


def revoked(
    snapshot, state_receipt, body, signature, *, get, receipt_key, webhook_key, now=None,
):
    current = policy.refresh_match(snapshot, get, now=now, require_verified=False)
    if not current["binding"].get("account") or not current["binding"].get("newsletter_id"):
        raise c.ContractError("named account evidence is required even for revocation")
    clock = c.utcnow if now is None else lambda: now
    now = clock()
    state = revocation_state(state_receipt, receipt_key, current, now)
    event = verify_event(body, signature, webhook_key, current)
    if event.get("event_type") not in {"subscriber.unsubscribed", *PERMANENT}:
        raise c.ContractError("event is not an unsubscribe or suppression")
    if any(entry["event_id"] == event["id"] for entry in state["entries"]):
        return state_receipt
    subscriber_id = event["data"]["subscriber"]
    value, _, _ = policy.observe(f"{policy.API}/subscribers/{subscriber_id}", get, clock, require_authenticated=True)
    expected = {
        "subscriber.unsubscribed": {"unsubscribed"}, "subscriber.complained": {"complained"},
        "subscriber.deleted": {"removed", "blocked"},
        "subscriber.type.changed": {"blocked", "undeliverable", "removed"},
    }[event["event_type"]]
    if not isinstance(value, dict) or value.get("id") != subscriber_id or value.get("type") not in expected:
        raise c.ContractError("revocation requires matching current provider GET, not webhook flags alone")
    when = value.get("unsubscription_date") if event["event_type"] == "subscriber.unsubscribed" else now.isoformat()
    if c.timestamp(when) > now:
        raise c.ContractError("invalid revocation timestamp")
    entry = {
        "event_id": event["id"], "event_type": event["event_type"], "subscriber_id": subscriber_id,
        "email_sha256": legacy.email_hash(value.get("email_address")), "revoked_at": when,
        "body_sha256": c.digest(body),
    }
    return legacy.seal({**state, "observed_at": clock().isoformat(), "entries": [*state["entries"], entry]}, receipt_key)


def evaluate(
    snapshot, inventory, availability, app_key, locale, consents, *, get=None,
    receipt_key=None, state_receipt=None, revocations=None, now=None,
):
    if not isinstance(consents, list) or len(consents) > 10000:
        return zero("invalid_audience_input")
    if not consents:
        return zero("zero_verified_audience")
    clock = c.utcnow if now is None else lambda: now
    now = clock()
    try:
        if get is None:
            raise c.ContractError("authenticated GET transport unavailable")
        current = policy.refresh_match(snapshot, get, now=now)
        c.validate_inventory(inventory, availability, now=now)
        row = c.inventory_row(inventory, app_key, locale)
        if row["app_store_url"] is None:
            return {**zero("market_not_applicable"), "app_store_url": None, "conversion_campaign": "N/A"}
        if row["app_id"] not in availability["countries"][row["storefront"]]["app_ids"]:
            return zero("app_storefront_unverified")
        state = legacy._state(state_receipt, receipt_key, now)
        if state.get("account_binding") != current["binding_digest"]:
            raise c.ContractError("suppression/cooldown state belongs to another account")
        revoked_state = revocation_state(revocations, receipt_key, current, now)
        today = [entry for entry in state["attempts"] if c.timestamp(entry["attempted_at"]).date() == now.date()]
        remaining = legacy.DAILY_CAP - sum(len(entry["subscriber_ids"]) for entry in today)
        if remaining <= 0:
            return zero("daily_cap")
        if any(entry["scope"] == c.scope(row) and (now - c.timestamp(entry["attempted_at"])).total_seconds()
               < legacy.COOLDOWN_SECONDS for entry in state["attempts"]):
            return zero("app_locale_campaign_cooldown")
    except (c.ContractError, OSError, TypeError, KeyError, ValueError) as error:
        return zero(str(error))
    rejected, eligible, used_ids = Counter(), {}, set()
    daily_ids = Counter(value for entry in today for value in entry["subscriber_ids"])
    daily_addresses = Counter(value for entry in today for value in entry["email_sha256s"])
    for receipt in consents:
        try:
            proof = legacy.unseal(receipt, receipt_key, CONFIRMED)
            if (
                proof.get("account_binding") != current["binding_digest"]
                or proof.get("configuration_digest") != current["configuration_digest"]
                or proof.get("newsletter_id") != current["binding"]["newsletter_id"]
                or proof.get("scope") != c.scope(row) or proof.get("consent_digest") != row["consent_digest"]
                or proof.get("metadata") != c.capture_metadata(row)
                or not isinstance(proof.get("generation"), str) or not readback.ID.fullmatch(proof["generation"])
                or not isinstance(proof.get("confirmation_event_id"), str) or not readback.ID.fullmatch(proof["confirmation_event_id"])
                or not isinstance(proof.get("confirmation_body_sha256"), str) or not c.HEX.fullmatch(proof["confirmation_body_sha256"])
                or proof.get("confirmation_timestamp_kind") != "verified_event_observed_at_not_provider_click_time"
            ):
                raise c.ContractError("account/config/scope/confirmation proof is incomplete")
            confirmed_at, pending_at = c.timestamp(proof.get("confirmed_at")), c.timestamp(proof.get("observed_at"))
            if not pending_at <= confirmed_at <= now:
                raise c.ContractError("confirmation timestamp is invalid")
            subscriber_id, address = proof["subscriber_id"], proof["email_sha256"]
            if subscriber_id in used_ids:
                continue
            used_ids.add(subscriber_id)
            history = prior_revocations(revoked_state, subscriber_id, address)
            if any(entry["event_type"] in PERMANENT or c.timestamp(entry["revoked_at"]) >= pending_at for entry in history):
                raise c.ContractError("old proof cannot survive unsubscribe/resubscribe")
            if (
                subscriber_id in state["suppressed_subscriber_ids"] or address in state["suppressed_email_hashes"]
                or any(item["subscriber_id"] == subscriber_id and item["scope"] == c.scope(row)
                       for item in state["scope_suppressions"])
                or daily_ids[subscriber_id] >= legacy.RECIPIENT_DAILY_CAP
                or daily_addresses[address] >= legacy.RECIPIENT_DAILY_CAP
            ):
                raise c.ContractError("subscriber suppressed or daily cap reached")
            value, _ = subscriber_get(subscriber_id, row, get, clock, allowed_types={"regular"})
            if legacy.email_hash(value["email_address"]) != address or value["creation_date"] != proof.get("subscriber_created_at"):
                raise c.ContractError("subscriber identity changed")
            if value["unsubscription_date"] and c.timestamp(value["unsubscription_date"]) >= pending_at:
                raise c.ContractError("new scope confirmation is required after unsubscribe")
            eligible[address] = subscriber_id
        except (c.ContractError, OSError, TypeError, KeyError, ValueError) as error:
            rejected[str(error)] += 1
    chosen = sorted(eligible.values())[:remaining]
    return {
        **zero("zero_verified_audience"), "action": "plan_only" if chosen else "no_op",
        "status": "VERIFIED_CANDIDATES_NO_SEND" if chosen else "BLOCKED",
        "reason": "read_only_no_send_authorization" if chosen else "zero_verified_audience",
        "eligible_subscriber_ids": chosen, "verified_audience_count": len(chosen),
        "rejected": dict(rejected), "account_binding": current["binding_digest"],
        "app_store_url": row["app_store_url"], "conversion_campaign": row["conversion_campaign"],
    }


def named_census(snapshot, get, *, now=None):
    unknown = {"subscriber_count": "UNKNOWN", "verified_audience_count": 0, "native_count": 0}
    try:
        current = policy.refresh_match(snapshot, get, now=now, require_verified=False)
        if not current["binding"].get("account") or not current["binding"].get("newsletter_id"):
            return {**unknown, "reason": "named_account_unverified"}

        def strict_get(url):
            response = get(url)
            payload = c.parse_json(response.get("body"))
            if (
                response.get("authenticated") is not True or not isinstance(payload, dict)
                or not {"count", "results"} <= set(payload) <= {"count", "results", "next", "previous"}
            ):
                raise c.ContractError("redacted, privacy-threshold or unnamed subscriber count")
            return response

        result = readback.subscriber_census(api_get=strict_get, now=now)
        return {
            "subscriber_count": result["subscriber_count"], "verified_audience_count": 0, "native_count": 0,
            "account_binding": current["binding_digest"], "newsletter_id": current["binding"]["newsletter_id"],
            "newsletter_username": current["binding"]["newsletter_username"],
            "api_gets": result["observations"], "evidence_level": "named_API_census_not_double_opt_in",
        }
    except (c.ContractError, OSError, TypeError, KeyError, ValueError) as error:
        return {**unknown, "reason": str(error)}


def native_evidence(snapshot, row, reference, get, *, now=None):
    current = policy.refresh_match(snapshot, get, now=now, require_verified=False)
    if not current["binding"].get("account") or not current["binding"].get("newsletter_id"):
        raise c.ContractError("native email evidence requires named account GET")
    result = readback.native_readback(row, reference, api_get=get, public_get=get, now=now)
    return {**result, "account_binding": current["binding_digest"]}
