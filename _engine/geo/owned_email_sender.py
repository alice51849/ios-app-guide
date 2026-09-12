#!/usr/bin/env python3
"""Consent and eligibility only. There is deliberately no send or subscribe API."""
from __future__ import annotations

from collections import Counter
import hashlib
import hmac
import os
from pathlib import Path
import re
import sqlite3

import owned_email_contract as contract
from owned_email_readback import API, ID, checked_get

PENDING = "lumi.owned-email-pending/v1"
CONSENT = "lumi.owned-email-confirmed-consent/v1"
STATE = "lumi.owned-email-sender-state/v1"
COOLDOWN_SECONDS = 7 * 86400
DAILY_CAP = 100
RECIPIENT_DAILY_CAP = 1
MAX_PENDING_AGE = 7 * 86400
MAX_STATE_AGE = 300


def _key(value):
    if not isinstance(value, bytes) or len(value) < 32:
        raise contract.ContractError("a private signing key of at least 32 bytes is required")
    return value


def seal(payload, key):
    raw = contract.json_bytes(payload)
    signature = hmac.new(_key(key), b"owned-email-receipt/v1\0" + raw, hashlib.sha256).hexdigest()
    return {"payload": payload, "signature": signature}


def unseal(receipt, key, schema):
    if (
        not isinstance(receipt, dict) or set(receipt) != {"payload", "signature"}
        or not isinstance(receipt.get("signature"), str)
        or not contract.HEX.fullmatch(receipt["signature"])
        or not isinstance(receipt.get("payload"), dict)
    ):
        raise contract.ContractError("missing authenticated private receipt")
    expected = seal(receipt["payload"], key)["signature"]
    if not hmac.compare_digest(expected, receipt["signature"]):
        raise contract.ContractError("receipt signature mismatch")
    if receipt["payload"].get("schema") != schema:
        raise contract.ContractError("receipt type mismatch")
    return receipt["payload"]


def email_hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise contract.ContractError("invalid subscriber address")
    return contract.digest(value.strip().casefold().encode())


def _subscriber(subscriber_id, row, api_get, now, *, expected_type):
    if not isinstance(subscriber_id, str) or not ID.fullmatch(subscriber_id):
        raise contract.ContractError("invalid provider subscriber ID")
    raw, observation = checked_get(f"{API}/subscribers/{subscriber_id}", api_get, now, authenticated=True)
    subscriber = contract.parse_json(raw)
    if (
        not isinstance(subscriber, dict) or subscriber.get("id") != subscriber_id
        or subscriber.get("type") != expected_type
        or subscriber.get("source") != "organic"
        or subscriber.get("subscriber_import_id") is not None
        or subscriber.get("purchased_by") is not None
        or subscriber.get("unsubscription_date") is not None
        or subscriber.get("bounce_date") is not None
        or subscriber.get("undeliverability_date") is not None
        or subscriber.get("email_transitions") not in ([], None)
        or subscriber.get("metadata") != contract.capture_metadata(row)
    ):
        raise contract.ContractError("subscriber is unconfirmed, suppressed, imported or outside consent scope")
    if contract.timestamp(subscriber.get("creation_date")) > (now() if callable(now) else now):
        raise contract.ContractError("subscriber is future-dated")
    return subscriber, observation


def observe_pending(row, subscriber_id, *, api_get, receipt_key, now=None):
    """Observe actual unactivated form signups; never create subscribers."""
    clock = contract.utcnow if now is None else lambda: now
    now = now or contract.utcnow()
    contract.validate_row(row)
    subscriber, observation = _subscriber(subscriber_id, row, api_get, clock, expected_type="unactivated")
    return seal({
        "schema": PENDING, "subscriber_id": subscriber_id,
        "email_sha256": email_hash(subscriber["email_address"]),
        "scope": contract.scope(row), "consent_digest": row["consent_digest"],
        "metadata": contract.capture_metadata(row),
        "observed_at": clock().isoformat(), "provider_get": observation,
    }, receipt_key)


def confirm_pending(
    row, pending, raw_body, signature, *, newsletter_id, webhook_key, receipt_key,
    seen_event_ids, api_get, now=None,
):
    """A signed subscriber.confirmed webhook plus pre-confirmation scope and a fresh GET."""
    clock = contract.utcnow if now is None else lambda: now
    now = now or contract.utcnow()
    contract.validate_row(row)
    saved = unseal(pending, receipt_key, PENDING)
    contract.fresh(saved.get("observed_at"), now, MAX_PENDING_AGE)
    if (
        not isinstance(raw_body, bytes) or not 0 < len(raw_body) <= 65536
        or not isinstance(signature, str) or not signature.startswith("sha256=")
    ):
        raise contract.ContractError("raw Buttondown signed confirmation is required")
    expected = "sha256=" + hmac.new(_key(webhook_key), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise contract.ContractError("Buttondown confirmation signature mismatch")
    event = contract.parse_json(raw_body)
    data = event.get("data") if isinstance(event, dict) else None
    event_id = event.get("id") if isinstance(event, dict) else None
    if (
        not isinstance(event, dict) or event.get("event_type") != "subscriber.confirmed"
        or not isinstance(event_id, str) or not ID.fullmatch(event_id)
        or not isinstance(data, dict) or data.get("newsletter") != newsletter_id
        or not isinstance(newsletter_id, str) or not ID.fullmatch(newsletter_id)
        or data.get("subscriber") != saved.get("subscriber_id")
        or event_id in seen_event_ids
        or saved.get("scope") != contract.scope(row)
        or saved.get("consent_digest") != row["consent_digest"]
        or saved.get("metadata") != contract.capture_metadata(row)
    ):
        raise contract.ContractError("confirmation event is replayed or not bound to the pending scope")
    subscriber, observation = _subscriber(
        saved["subscriber_id"], row, api_get, clock, expected_type="regular",
    )
    if email_hash(subscriber["email_address"]) != saved["email_sha256"]:
        raise contract.ContractError("the confirmed address differs from the pending address")
    result = seal({
        "schema": CONSENT, "subscriber_id": saved["subscriber_id"],
        "email_sha256": saved["email_sha256"], "scope": saved["scope"],
        "consent_digest": saved["consent_digest"], "metadata": saved["metadata"],
        "pending_observed_at": saved["observed_at"], "confirmed_at": clock().isoformat(),
        "newsletter_id": newsletter_id, "confirmation_event_id": event_id,
        "confirmation_body_sha256": contract.digest(raw_body),
        "pending_receipt_sha256": contract.digest(pending), "provider_get": observation,
    }, receipt_key)
    return result


class ConfirmationLedger:
    """Private, transactional replay protection; no raw addresses or credentials."""
    def __init__(self, path):
        path = Path(path)
        if path.is_symlink():
            raise contract.ContractError("confirmation ledger cannot be a symlink")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(path, 0o600)
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS confirmations "
            "(event_id TEXT PRIMARY KEY, body_digest TEXT NOT NULL, receipt BLOB NOT NULL)"
        )
        self.db.commit()

    def close(self):
        self.db.close()

    def confirm(self, row, pending, raw_body, signature, **kwargs):
        expected = "sha256=" + hmac.new(_key(kwargs["webhook_key"]), raw_body, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise contract.ContractError("Buttondown confirmation signature mismatch")
        event = contract.parse_json(raw_body)
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            raise contract.ContractError("missing confirmation event identity")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute(
                "SELECT body_digest, receipt FROM confirmations WHERE event_id=?", (event["id"],),
            ).fetchone()
            if existing:
                saved = contract.parse_json(existing[1])
                receipt = unseal(saved, kwargs["receipt_key"], CONSENT)
                if (
                    existing[0] != contract.digest(raw_body)
                    or receipt["scope"] != contract.scope(row)
                    or receipt["consent_digest"] != row["consent_digest"]
                ):
                    raise contract.ContractError("confirmation replay changed its scope")
                return saved
            result = confirm_pending(
                row, pending, raw_body, signature, seen_event_ids=frozenset(), **kwargs,
            )
            self.db.execute(
                "INSERT INTO confirmations VALUES(?,?,?)",
                (event["id"], contract.digest(raw_body), contract.json_bytes(result)),
            )
            return result


def _valid_scope(value):
    apps = contract.roster()["apps"]
    return (
        isinstance(value, dict) and set(value) == {"app_key", "app_id", "locale", "campaign"}
        and isinstance(value["app_key"], str) and value["app_key"] in apps
        and value["app_id"] == apps[value["app_key"]]["app_id"]
        and value["locale"] in contract.OFFICIAL_LOCALES
        and isinstance(value["campaign"], str) and re.fullmatch(r"[a-z0-9_]{1,64}", value["campaign"])
    )


def _state(receipt, key, now):
    state = unseal(receipt, key, STATE)
    contract.fresh(state.get("observed_at"), now, MAX_STATE_AGE)
    if state.get("complete") is not True:
        raise contract.ContractError("incomplete suppression or sending history")
    for field in ("suppressed_subscriber_ids", "suppressed_email_hashes", "scope_suppressions", "attempts"):
        if not isinstance(state.get(field), list):
            raise contract.ContractError("missing suppression or cooldown history")
    if any(not isinstance(value, str) or not ID.fullmatch(value)
           for value in state["suppressed_subscriber_ids"]):
        raise contract.ContractError("invalid suppressed subscriber")
    if any(not isinstance(value, str) or not contract.HEX.fullmatch(value)
           for value in state["suppressed_email_hashes"]):
        raise contract.ContractError("invalid suppressed address fingerprint")
    seen = set()
    for attempt in state["attempts"]:
        if (
            not isinstance(attempt, dict) or attempt.get("status") not in {"reserved", "attempted", "sent", "unknown"}
            or not isinstance(attempt.get("attempt_id"), str) or not attempt["attempt_id"]
            or attempt["attempt_id"] in seen or not _valid_scope(attempt.get("scope"))
            or not isinstance(attempt.get("subscriber_ids"), list) or not attempt["subscriber_ids"]
            or any(not isinstance(value, str) or not ID.fullmatch(value) for value in attempt["subscriber_ids"])
            or len(set(attempt["subscriber_ids"])) != len(attempt["subscriber_ids"])
            or not isinstance(attempt.get("email_sha256s"), list)
            or len(attempt["email_sha256s"]) != len(attempt["subscriber_ids"])
            or any(not isinstance(value, str) or not contract.HEX.fullmatch(value) for value in attempt["email_sha256s"])
        ):
            raise contract.ContractError("invalid or ambiguous sending history")
        if contract.timestamp(attempt.get("attempted_at")) > now:
            raise contract.ContractError("future-dated sending history")
        seen.add(attempt["attempt_id"])
    for suppression in state["scope_suppressions"]:
        if (
            not isinstance(suppression, dict)
            or not isinstance(suppression.get("subscriber_id"), str)
            or not ID.fullmatch(suppression["subscriber_id"])
            or not _valid_scope(suppression.get("scope"))
        ):
            raise contract.ContractError("invalid scoped suppression")
    return state


def plan(
    inventory, availability, app_key, locale, consents, *, state_receipt=None,
    receipt_key=None, api_get=None, now=None,
):
    """Read-only planning cannot reserve, create, send or count a delivered email."""
    result = {
        "action": "no_op", "reason": "zero_verified_audience",
        "eligible_subscriber_ids": [], "eligible_count": 0,
        "send_allowed": False, "send_requests": 0, "native_email_count": 0,
        "app_store_url": None, "conversion_campaign": "N/A" if locale == "bn-BD" else None,
    }
    if not isinstance(consents, list) or len(consents) > 10000:
        raise contract.ContractError("audience must be an explicit list of verified consent receipts")
    if not consents:
        return result
    clock = contract.utcnow if now is None else lambda: now
    now = now or contract.utcnow()
    contract.validate_inventory(inventory, availability, now=now)
    row = contract.inventory_row(inventory, app_key, locale)
    result.update(app_store_url=row["app_store_url"], conversion_campaign=row["conversion_campaign"])
    if row["app_store_url"] is None:
        return {**result, "action": "not_applicable", "reason": "market_unavailable"}
    if row["app_id"] not in availability["countries"][row["storefront"]]["app_ids"]:
        return {**result, "reason": "app_storefront_unverified"}
    state = _state(state_receipt, receipt_key, now)
    if api_get is None:
        raise contract.ContractError("fresh Buttondown subscriber GET is required")
    today = [entry for entry in state["attempts"]
             if contract.timestamp(entry["attempted_at"]).date() == now.date()]
    remaining = DAILY_CAP - sum(len(entry["subscriber_ids"]) for entry in today)
    if remaining <= 0:
        return {**result, "reason": "daily_cap"}
    if any(
        entry["scope"] == contract.scope(row)
        and (now - contract.timestamp(entry["attempted_at"])).total_seconds() < COOLDOWN_SECONDS
        for entry in state["attempts"]
    ):
        return {**result, "reason": "app_locale_campaign_cooldown"}
    sent_today = Counter(subscriber for entry in today for subscriber in entry["subscriber_ids"])
    addresses_today = Counter(address for entry in today for address in entry["email_sha256s"])
    denied = Counter()
    eligible = {}
    checked_ids = set()
    for receipt in consents:
        try:
            consent = unseal(receipt, receipt_key, CONSENT)
            if (
                consent.get("scope") != contract.scope(row)
                or consent.get("consent_digest") != row["consent_digest"]
                or consent.get("metadata") != contract.capture_metadata(row)
                or not isinstance(consent.get("confirmation_event_id"), str)
                or not ID.fullmatch(consent["confirmation_event_id"])
                or not isinstance(consent.get("confirmation_body_sha256"), str)
                or not contract.HEX.fullmatch(consent["confirmation_body_sha256"])
                or contract.timestamp(consent.get("confirmed_at")) > now
                or contract.timestamp(consent.get("pending_observed_at")) > contract.timestamp(consent["confirmed_at"])
            ):
                raise contract.ContractError("unverified double opt-in or consent scope mismatch")
            subscriber_id = consent["subscriber_id"]
            if subscriber_id in checked_ids:
                continue
            checked_ids.add(subscriber_id)
            if (
                subscriber_id in state["suppressed_subscriber_ids"]
                or consent["email_sha256"] in state["suppressed_email_hashes"]
                or any(item["subscriber_id"] == subscriber_id and item["scope"] == contract.scope(row)
                       for item in state["scope_suppressions"])
            ):
                denied["suppressed"] += 1
                continue
            if (
                sent_today[subscriber_id] >= RECIPIENT_DAILY_CAP
                or addresses_today[consent["email_sha256"]] >= RECIPIENT_DAILY_CAP
            ):
                denied["recipient_daily_cap"] += 1
                continue
            subscriber, _ = _subscriber(subscriber_id, row, api_get, clock, expected_type="regular")
            address = email_hash(subscriber["email_address"])
            if address != consent["email_sha256"]:
                raise contract.ContractError("confirmed address changed")
            eligible[address] = subscriber_id
        except (contract.ContractError, KeyError, TypeError, OSError):
            denied["unverified_or_out_of_scope"] += 1
    selected = sorted(eligible.values())[:remaining]
    return {
        **result, "action": "plan_only" if selected else "no_op",
        "reason": "read_only_no_send_authorization" if selected else "zero_verified_audience",
        "eligible_subscriber_ids": selected, "eligible_count": len(selected),
        "rejected": dict(denied), "daily_capacity_remaining": remaining,
    }
