"""Immutable publisher ACK evidence; never evidence of subscriber delivery."""
from __future__ import annotations

from datetime import datetime, timezone
import re
import urllib.parse
import xml.etree.ElementTree as ET

import owned_app_feeds as feeds

SCHEMA = "lumi.owned-feed-receipt/v1"
STATE_SCHEMA = "lumi.owned-feed-delivery/v3"
MAX_ACK_BYTES = 65536
BINDING_FIELDS = (
    "generation_id", "feed_generation_sha256", "inventory_sha256",
    "source_sha", "engine_source_sha", "deployment_sha256",
)
OUTCOMES = {
    "accepted_ack", "retryable_error", "rejected", "body_mismatch", "indeterminate",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def request_body(protocol: str, topics: list[str]) -> str:
    if not topics or len(topics) != len(set(topics)):
        raise ValueError("Request topics must be unique and nonempty")
    if protocol == "websub":
        fields = [("hub.mode", "publish"), *[("hub.url", topic) for topic in topics]]
    elif protocol == "rsscloud" and len(topics) == 1:
        fields = [("url", topics[0])]
    else:
        raise ValueError("Invalid notification request")
    return urllib.parse.urlencode(fields).encode("ascii").decode("ascii")


def response_outcome(protocol: str, response: dict, request: dict, endpoint: str) -> str:
    status, body = response["http_status"], response["ack_body"]
    if response["transport_error"] in {"crash_recovery", "interrupted"}:
        return "indeterminate"
    if response["transport_error"]:
        return "retryable_error"
    if (
        response["endpoint"] != endpoint or response["final_url"] != endpoint
        or response["request_sha256"] != request["request_sha256"]
        or response["topics"] != request["topics"]
    ):
        return "body_mismatch"
    if status == 429 or status is not None and 500 <= status <= 599:
        return "retryable_error"
    if protocol == "websub":
        if status == 204 and body:
            return "body_mismatch"
        return "accepted_ack" if status in {200, 202, 204} else "rejected"
    if status != 200:
        return "rejected"
    try:
        payload = feeds.decode(body.encode("utf-8"))
        if isinstance(payload, dict) and any(
            payload[name] != request["topics"][0] for name in ("url", "topic") if name in payload
        ):
            return "body_mismatch"
        accepted = isinstance(payload, dict) and payload.get("success") is True
    except (ValueError, TypeError):
        try:
            attributes = ET.fromstring(body).attrib
            if any(attributes[name] != request["topics"][0] for name in ("url", "topic") if name in attributes):
                return "body_mismatch"
            accepted = attributes.get("success", "").lower() == "true"
        except ET.ParseError:
            return "body_mismatch"
    if accepted:
        return "accepted_ack"
    if "error reading the resource at url" in body.casefold():
        return "retryable_error"
    return "rejected"


def make_receipt(task: dict, attempt: dict, response: dict) -> dict:
    raw_body = response.get("ack_body", "")
    if not isinstance(raw_body, str) or len(raw_body.encode("utf-8")) > MAX_ACK_BYTES:
        raise ValueError("Invalid or oversized publisher ACK body")
    request = {
        **{name: task[name] for name in BINDING_FIELDS},
        "feed_sha256": task["content_sha256"], "method": "POST",
        "content_type": "application/x-www-form-urlencoded; charset=utf-8",
        "topics": attempt["topics"], "request_body": attempt["request_body"],
        "request_sha256": attempt["request_sha256"], "started_at": attempt["started_at"],
    }
    recorded = {
        "http_status": response.get("http_status"),
        "ack_body": raw_body, "ack_body_sha256": feeds.sha256(raw_body.encode("utf-8")),
        "observed_at": response.get("observed_at", utc_now()),
        "endpoint": response.get("endpoint"),
        "final_url": response.get("final_url", response.get("endpoint")),
        "topics": response.get("topics"),
        "request_sha256": response.get("request_sha256"),
        "retry_after_seconds": response.get("retry_after_seconds"),
        "transport_error": response.get("transport_error"),
    }
    outcome = response_outcome(task["protocol"], recorded, request, task["endpoint"])
    receipt = {
        "schema": SCHEMA, "attempt_id": attempt["attempt_id"],
        "intent_id": feeds.digest([task[name] for name in ("protocol", "endpoint", "topic", "content_sha256")]),
        "protocol": task["protocol"], "endpoint": task["endpoint"], "topic": task["topic"],
        "request": request, "response": recorded, "outcome": outcome,
        "accepted_ack": outcome == "accepted_ack",
        "subscriber_delivery_verified": False, "indexing_verified": False,
    }
    receipt["receipt_id"] = feeds.digest(receipt)
    validate_receipt(receipt)
    return receipt


def validate_receipt(receipt: dict) -> None:
    required = {
        "schema", "receipt_id", "attempt_id", "intent_id", "protocol", "endpoint", "topic",
        "request", "response", "outcome", "accepted_ack",
        "subscriber_delivery_verified", "indexing_verified",
    }
    if (
        not isinstance(receipt, dict) or set(receipt) - {"fixture"} != required
        or receipt.get("schema") != SCHEMA or receipt.get("protocol") not in {"websub", "rsscloud"}
        or receipt.get("outcome") not in OUTCOMES
        or type(receipt.get("accepted_ack")) is not bool
        or receipt.get("subscriber_delivery_verified") is not False
        or receipt.get("indexing_verified") is not False
        or not re.fullmatch(r"[0-9a-f]{32}", str(receipt.get("attempt_id", "")))
        or ("fixture" in receipt and receipt["fixture"] is not True)
    ):
        raise ValueError("Invalid publisher ACK receipt envelope")
    for name in ("endpoint", "topic"):
        parsed = urllib.parse.urlsplit(receipt[name])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Invalid receipt endpoint/topic")
    request, response = receipt["request"], receipt["response"]
    if set(request) != set(BINDING_FIELDS) | {
        "feed_sha256", "method", "content_type", "topics", "request_body",
        "request_sha256", "started_at",
    }:
        raise ValueError("Missing generation-bound request fields")
    for name in (*BINDING_FIELDS, "feed_sha256", "request_sha256"):
        size = 40 if name in {"source_sha", "engine_source_sha"} else 64
        if not re.fullmatch(rf"[0-9a-f]{{{size}}}", str(request[name])):
            raise ValueError(f"Invalid receipt binding: {name}")
    if receipt["intent_id"] != feeds.digest([
        receipt["protocol"], receipt["endpoint"], receipt["topic"], request["feed_sha256"]
    ]):
        raise ValueError("Invalid stable notification intent identity")
    if (
        request["method"] != "POST"
        or request["content_type"] != "application/x-www-form-urlencoded; charset=utf-8"
        or not isinstance(request["topics"], list)
        or any(not isinstance(topic, str) for topic in request["topics"])
        or receipt["topic"] not in request["topics"]
        or request["request_body"] != request_body(receipt["protocol"], request["topics"])
        or request["request_sha256"] != feeds.sha256(request["request_body"].encode("ascii"))
    ):
        raise ValueError("Receipt request/body mismatch")
    if set(response) != {
        "http_status", "ack_body", "ack_body_sha256", "observed_at", "endpoint",
        "final_url", "topics", "request_sha256", "retry_after_seconds", "transport_error",
    }:
        raise ValueError("Incomplete response observation")
    status, body = response["http_status"], response["ack_body"]
    if status is not None and (type(status) is not int or not 100 <= status <= 599):
        raise ValueError("Invalid HTTP status")
    if (
        not isinstance(body, str) or len(body.encode("utf-8")) > MAX_ACK_BYTES
        or response["ack_body_sha256"] != feeds.sha256(body.encode("utf-8"))
    ):
        raise ValueError("Receipt ACK body/hash mismatch")
    retry = response["retry_after_seconds"]
    if retry is not None and (type(retry) not in {int, float} or not 0 <= retry <= 300):
        raise ValueError("Invalid bounded Retry-After")
    feeds.timestamp(request["started_at"])
    feeds.timestamp(response["observed_at"])
    if response["observed_at"] < request["started_at"]:
        raise ValueError("Receipt observation precedes its request")
    outcome = response_outcome(receipt["protocol"], response, request, receipt["endpoint"])
    if outcome != receipt["outcome"] or receipt["accepted_ack"] is not (outcome == "accepted_ack"):
        raise ValueError("HTTP response does not prove the claimed ACK")
    if receipt["receipt_id"] != feeds.digest({k: v for k, v in receipt.items() if k != "receipt_id"}):
        raise ValueError("Receipt checksum mismatch")


def is_current(receipt: dict, task: dict) -> bool:
    validate_receipt(receipt)
    return (
        receipt["accepted_ack"] and not receipt.get("fixture", False)
        and all(receipt.get(name) == task.get(name) for name in ("protocol", "endpoint", "topic"))
        and receipt["request"]["feed_sha256"] == task["content_sha256"]
        and all(receipt["request"][name] == task[name] for name in BINDING_FIELDS)
    )


def same_content(receipt: dict, task: dict) -> bool:
    validate_receipt(receipt)
    return (
        receipt["accepted_ack"] and not receipt.get("fixture", False)
        and all(receipt[name] == task[name] for name in ("protocol", "endpoint", "topic"))
        and receipt["request"]["feed_sha256"] == task["content_sha256"]
    )


def new_state() -> dict:
    return {
        "schema": STATE_SCHEMA, "revision": 0, "previous_state_sha256": None,
        "prepared": {}, "pending": {}, "accepted": {}, "records": {},
        "in_flight": {}, "legacy_history": [],
    }


def validate_state(state: dict, *, sealed: bool = True) -> None:
    if (
        state.get("schema") != STATE_SCHEMA or type(state.get("revision")) is not int
        or state["revision"] < 0 or not isinstance(state.get("legacy_history"), list)
        or any(not isinstance(state.get(name), dict) for name in (
            "pending", "accepted", "records", "in_flight", "prepared"
        ))
    ):
        raise ValueError("Invalid durable receipt state")
    if sealed and state.get("state_digest") != feeds.digest({
        k: v for k, v in state.items() if k != "state_digest"
    }):
        raise ValueError("Receipt state checksum mismatch")
    for receipt_id, receipt in state["records"].items():
        validate_receipt(receipt)
        if receipt_id != receipt["receipt_id"]:
            raise ValueError("Invalid immutable receipt identity")
    for receipt_id in state["accepted"].values():
        if receipt_id not in state["records"] or not state["records"][receipt_id]["accepted_ack"]:
            raise ValueError("ACK pointer has no valid observed receipt")
