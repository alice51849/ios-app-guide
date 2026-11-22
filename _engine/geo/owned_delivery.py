#!/usr/bin/env python3
"""GET-only, content-bound receipts for owned/passive distribution routes."""
from __future__ import annotations

import copy
import base64
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET

KINDS = frozenset({
    "pages", "rss", "atom", "json_feed", "websub", "rsscloud",
    "standard_site", "appview", "indexnow",
})
LEVELS = {
    "pages": "public_content_verified",
    "rss": "public_feed_verified",
    "atom": "public_feed_verified",
    "json_feed": "public_feed_verified",
    "websub": "hub_accepted_not_subscriber_delivery",
    "rsscloud": "server_accepted_not_subscriber_delivery",
    "standard_site": "pds_record_verified_not_appview_delivery",
    "appview": "appview_record_verified",
    "indexnow": "endpoint_accepted_not_indexed",
}
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
AT_URI = re.compile(r"at://(did:[a-z]+:[A-Za-z0-9:._%-]+)/"
                    r"(site\.standard\.(?:publication|document))/([A-Za-z0-9._~:-]+)")
MAX_BODY = 8 * 1024 * 1024
MAX_ACK_AGE = 36 * 3600
INDEXNOW_ENDPOINTS = {
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
}


class ReceiptError(ValueError):
    pass


def now_utc():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value, str):
        raise ReceiptError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReceiptError("invalid timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReceiptError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def fresh(value, now, maximum=MAX_ACK_AGE):
    age = (now - timestamp(value)).total_seconds()
    if age < -60 or age > maximum:
        raise ReceiptError("evidence is future-dated or stale")


def sha256(body):
    return hashlib.sha256(body).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError("duplicate JSON key")
        result[key] = value
    return result


def parse_json(body):
    def invalid_constant(_value):
        raise ReceiptError("non-finite JSON number")

    try:
        return json.loads(body, object_pairs_hook=_pairs,
                          parse_constant=invalid_constant)
    except (UnicodeError, ValueError, TypeError) as error:
        raise ReceiptError("invalid JSON evidence") from error


def public_url(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise ReceiptError("invalid public URL")
    try:
        parsed = urllib.parse.urlsplit(value)
        invalid = (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.fragment
            or parsed.port not in (None, 443)
            or any(character.isspace() or ord(character) < 32 for character in value)
            or parsed.hostname.lower().endswith((".local", ".localhost", ".internal"))
            or parsed.hostname.lower() == "localhost"
        )
    except ValueError as error:
        raise ReceiptError("invalid public URL") from error
    if invalid:
        raise ReceiptError("only public, credential-free HTTPS URLs are allowed")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ReceiptError("non-public network address")
    keys = {key.lower() for key, _ in urllib.parse.parse_qsl(parsed.query)}
    if keys & {"token", "access_token", "password", "key", "auth", "hub.mode"}:
        raise ReceiptError("credentials or mutation parameters in public URL")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def get(url, *, timeout=20):
    """No authentication, redirects, POST, conditional-cache hits or local fallback."""
    public_url(url)
    parsed = urllib.parse.urlsplit(url)
    endpoint = f"https://{parsed.hostname.lower()}{parsed.path.rstrip('/').lower()}"
    if (
        endpoint in INDEXNOW_ENDPOINTS
        or (parsed.hostname == "rpc.rsscloud.io"
            and parsed.path.rstrip("/").lower() in {"/ping", "/pleasenotify", "/websub"})
        or parsed.path in {
            "/xrpc/com.atproto.repo.createRecord", "/xrpc/com.atproto.repo.putRecord",
            "/xrpc/com.atproto.repo.deleteRecord", "/xrpc/com.atproto.repo.applyWrites",
        }
    ):
        raise ReceiptError("notification endpoints are not GET readback evidence")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global
                            for row in addresses):
        raise ReceiptError("readback DNS resolved to a non-public address")
    request = urllib.request.Request(
        url, method="GET",
        headers={"User-Agent": "GrowthOwned-Receipt/1",
                 "Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    with urllib.request.build_opener(_NoRedirect()).open(
        request, timeout=timeout
    ) as response:
        body = response.read(MAX_BODY + 1)
        result = {
            "url": url, "final_url": response.geturl(),
            "http_status": response.status, "body": body,
            "observed_at": now_utc().isoformat(),
        }
    if len(body) > MAX_BODY:
        raise ReceiptError("readback exceeds size limit")
    return result


def readback(url, fetch, now):
    public_url(url)
    result = fetch(url)
    if (
        not isinstance(result, dict)
        or result.get("url") != url or result.get("final_url") != url
        or type(result.get("http_status")) is not int
        or result["http_status"] != 200
        or not isinstance(result.get("body"), bytes)
        or not result["body"] or len(result["body"]) > MAX_BODY
    ):
        raise ReceiptError("live GET must return exact URL, HTTP 200 and bounded bytes")
    fresh(result.get("observed_at"), now, 300)
    evidence = {key: result[key] for key in
                ("url", "final_url", "http_status", "observed_at")}
    evidence["sha256"] = sha256(result["body"])
    return result["body"], evidence


def _source(contract, fetch, now, observations):
    source = contract.get("source")
    if not isinstance(source, dict):
        raise ReceiptError("immutable source contract is missing")
    sha = source.get("sha")
    digest = source.get("sha256")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ReceiptError("source requires a full Git SHA")
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ReceiptError("source requires a SHA-256 content digest")
    url = public_url(source.get("url"))
    if not re.search(r"(?<![0-9a-f])" + sha + r"(?![0-9a-f])", url):
        raise ReceiptError("source URL must be pinned to its full SHA")
    body, evidence = readback(url, fetch, now)
    observations["source_get"] = evidence
    if sha256(body) != digest:
        raise ReceiptError("immutable source digest mismatch")
    return body, evidence


def _feed(body, kind):
    try:
        if kind == "json_feed":
            value = parse_json(body)
            valid = (isinstance(value, dict)
                     and str(value.get("version", "")).startswith(
                         "https://jsonfeed.org/version/")
                     and isinstance(value.get("items"), list) and value["items"])
        else:
            root = ET.fromstring(body)
            valid = (
                root.tag == "rss" and root.find("channel/item") is not None
                if kind == "rss" else
                root.tag == "{http://www.w3.org/2005/Atom}feed"
                and root.find("{http://www.w3.org/2005/Atom}entry") is not None
            )
    except (ET.ParseError, ValueError):
        valid = False
    if not valid:
        raise ReceiptError("live feed is malformed or contains no entries")


def _notification(contract, document, now):
    if not isinstance(document, dict) or document.get("kind") != (
        "owned_notification_acknowledgements"
    ) or type(document.get("version")) is not int or document["version"] != 1:
        raise ReceiptError("missing remote notification acknowledgements")
    expected = contract.get("endpoints")
    if (not isinstance(expected, list) or not expected
            or len(set(expected)) != len(expected)):
        raise ReceiptError("all expected notification endpoints must be explicit")
    for endpoint in expected:
        public_url(endpoint)
    receipts = document.get("receipts")
    if not isinstance(receipts, list):
        raise ReceiptError("invalid notification receipt list")
    verified = []
    for endpoint in expected:
        candidates = [
            item for item in receipts if isinstance(item, dict)
            and item.get("route") == contract["kind"]
            and item.get("endpoint") == endpoint
            and isinstance(item.get("content_sha256"), dict)
            and contract["public_url"] in item["content_sha256"]
        ]
        if len(candidates) != 1:
            raise ReceiptError("missing or ambiguous acknowledgement for endpoint")
        item = candidates[0]
        contents = item.get("content_sha256")
        if (
            item.get("source_sha") != contract["source"]["sha"]
            or contents.get(contract["public_url"]) != contract["source"]["sha256"]
            or item.get("method") != "POST"
            or type(item.get("http_status")) is not int
            or not 200 <= item["http_status"] < 300
            or item.get("semantics") != LEVELS[contract["kind"]]
        ):
            raise ReceiptError("notification ack is not bound to this source/content")
        fresh(item.get("accepted_at"), now)
        urls = item.get("public_urls")
        if (not isinstance(urls, list) or not urls or len(set(urls)) != len(urls)
                or set(urls) != set(contents)):
            raise ReceiptError("notification request URL inventory mismatch")
        for url in urls:
            public_url(url)
            if not isinstance(contents[url], str) or not DIGEST.fullmatch(contents[url]):
                raise ReceiptError("invalid notification content digest")
        if contract["kind"] == "websub":
            fields = [("hub.mode", "publish"), *(("hub.url", url) for url in urls)]
        else:
            if len(urls) != 1:
                raise ReceiptError("rssCloud ping must name exactly one feed")
            fields = [("url", urls[0])]
        request = urllib.parse.urlencode(fields).encode("ascii")
        body = item.get("response_body")
        if (
            not isinstance(body, str) or len(body.encode("utf-8")) > 65536
            or item.get("request_sha256") != sha256(request)
            or item.get("response_sha256") != sha256(body.encode("utf-8"))
        ):
            raise ReceiptError("notification request/response digest mismatch")
        if contract["kind"] == "rsscloud":
            from notify_rsscloud import _parse_result
            if not _parse_result(body.encode("utf-8"))[0]:
                raise ReceiptError("rssCloud returned a service-level rejection")
        verified.append(copy.deepcopy(item))
    return verified


def _indexnow(contract, document, now):
    if (
        not isinstance(document, dict) or type(document.get("version")) is not int
        or document["version"] != 1
        or document.get("kind") != "indexnow_submission_receipt"
        or document.get("semantics") != "accepted_by_endpoints_not_indexed"
        or document.get("disposition") != "accepted"
        or document.get("pages_sha") != contract["source"]["sha"]
    ):
        raise ReceiptError("IndexNow requires an actual source-bound acceptance, not noop")
    fresh(document.get("accepted_at"), now)
    urls = document.get("urls")
    if (
        not isinstance(urls, list) or not urls or len(set(urls)) != len(urls)
        or contract["public_url"] not in urls
        or type(document.get("url_count")) is not int
        or document["url_count"] != len(urls)
        or document.get("url_set_sha256") != sha256(
            json.dumps(sorted(urls), ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8"))
    ):
        raise ReceiptError("IndexNow URL inventory/digest mismatch")
    for url in urls:
        public_url(url)
    endpoints = document.get("endpoints")
    if (not isinstance(endpoints, list) or len(endpoints) != len(INDEXNOW_ENDPOINTS)
            or {item.get("url") for item in endpoints if isinstance(item, dict)}
            != INDEXNOW_ENDPOINTS):
        raise ReceiptError("IndexNow must have every endpoint acknowledgement")
    for endpoint in endpoints:
        batches = endpoint.get("batches")
        if (
            not isinstance(batches, list) or not batches
            or type(endpoint.get("accepted_batch_count")) is not int
            or endpoint["accepted_batch_count"] != len(batches)
        ):
            raise ReceiptError("IndexNow batch acknowledgements are incomplete")
        total = 0
        for number, batch in enumerate(batches, 1):
            if (
                not isinstance(batch, dict) or type(batch.get("batch")) is not int
                or batch["batch"] != number
                or type(batch.get("http_status")) is not int
                or batch["http_status"] not in {200, 202}
                or type(batch.get("url_count")) is not int
                or not 1 <= batch["url_count"] <= 10000
            ):
                raise ReceiptError("IndexNow batch has no successful remote ack")
            total += batch["url_count"]
        if total != len(urls):
            raise ReceiptError("IndexNow endpoint accepted only part of the URL set")
    return {
        "semantics": document["semantics"],
        "pages_sha": document["pages_sha"],
        "accepted_at": document["accepted_at"],
        "public_url": contract["public_url"],
        "url_count": document["url_count"],
        "url_set_sha256": document["url_set_sha256"],
        "endpoints": copy.deepcopy(endpoints),
    }


def _record(contract, source, live):
    platform_id = contract.get("platform_id")
    match = AT_URI.fullmatch(platform_id or "")
    if not match:
        raise ReceiptError("Standard.site/AppView requires an exact AT record identity")
    expected = parse_json(source)
    actual = parse_json(live)
    path = contract.get("record_path", [])
    if not isinstance(path, list) or any(not isinstance(key, str) for key in path):
        raise ReceiptError("AppView record_path must be an explicit key list")
    for key in path:
        actual = actual.get(key) if isinstance(actual, dict) else None
    if (
        not isinstance(expected, dict) or not isinstance(actual, dict)
        or expected.get("uri") != platform_id or actual.get("uri") != platform_id
        or not _record_cid(expected.get("cid"))
        or actual.get("cid") != expected["cid"]
        or not isinstance(expected.get("value"), dict)
        or not isinstance(actual.get("value"), dict)
        or expected["value"].get("$type") != match[2]
        or json_bytes(actual["value"]) != json_bytes(expected["value"])
    ):
        raise ReceiptError("record identity, CID or content differs from the source")
    if contract["kind"] == "standard_site":
        parsed = urllib.parse.urlsplit(contract["public_url"])
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if (
            not parsed.path.endswith("/xrpc/com.atproto.repo.getRecord")
            or query != {"repo": [match[1]], "collection": [match[2]], "rkey": [match[3]]}
        ):
            raise ReceiptError("PDS readback URL does not identify the expected record")
    elif urllib.parse.urlsplit(contract["public_url"]).path.startswith("/xrpc/com.atproto.repo."):
        raise ReceiptError("PDS availability is not AppView delivery")
    return {"uri": platform_id, "cid": actual["cid"],
            "record_sha256": sha256(json_bytes(actual["value"]))}


def _record_cid(value):
    if not isinstance(value, str) or not re.fullmatch(r"b[a-z2-7]{58}", value):
        return False
    encoded = value[1:].upper()
    raw = base64.b32decode(encoded + "=" * (-len(encoded) % 8))
    return (len(raw) == 36 and raw[:4] == b"\x01\x71\x12\x20"
            and "b" + base64.b32encode(raw).decode().lower().rstrip("=") == value)


def _pds_endpoint(platform_id, fetch, now, observations):
    match = AT_URI.fullmatch(platform_id or "")
    if not match:
        raise ReceiptError("missing Standard.site AT record identity")
    did = match[1]
    if did.startswith("did:plc:"):
        url = f"https://plc.directory/{did}"
    elif did.startswith("did:web:"):
        parts = [urllib.parse.unquote(part) for part in did.split(":")[2:]]
        if (not parts or any(part in {"", ".", ".."} for part in parts)
                or any(character in parts[0] for character in "/?#@")):
            raise ReceiptError("invalid did:web authority")
        path = ("/".join(urllib.parse.quote(part, safe="") for part in parts[1:])
                if len(parts) > 1 else ".well-known")
        url = f"https://{parts[0]}/{path}/did.json"
    else:
        raise ReceiptError("unsupported DID authority")
    body, evidence = readback(url, fetch, now)
    observations["did_get"] = evidence
    document = parse_json(body)
    if not isinstance(document, dict) or document.get("id") != did:
        raise ReceiptError("DID authority returned the wrong identity")
    services = document.get("service")
    if not isinstance(services, list):
        raise ReceiptError("DID has no authoritative PDS service")
    services = [
        service for service in services if isinstance(service, dict)
        and service.get("id") in {"#atproto_pds", f"{did}#atproto_pds"}
        and service.get("type") == "AtprotoPersonalDataServer"
    ]
    if len(services) != 1:
        raise ReceiptError("DID PDS service is missing or ambiguous")
    endpoint = public_url(services[0].get("serviceEndpoint"))
    if urllib.parse.urlsplit(endpoint).query:
        raise ReceiptError("PDS service endpoint must not include a query")
    return endpoint.rstrip("/") + "/xrpc/com.atproto.repo.getRecord?" + urllib.parse.urlencode(
        {"repo": did, "collection": match[2], "rkey": match[3]}
    )


def _same_endpoint(actual, expected):
    actual = urllib.parse.urlsplit(public_url(actual))
    expected = urllib.parse.urlsplit(expected)
    return (
        actual.hostname.lower() == expected.hostname.lower()
        and (actual.port or 443) == (expected.port or 443) and actual.path == expected.path
        and urllib.parse.parse_qs(actual.query, keep_blank_values=True)
        == urllib.parse.parse_qs(expected.query, keep_blank_values=True)
    )


def verify(contract, *, fetch=get, now=None, observations=None):
    now = now or now_utc()
    observations = {} if observations is None else observations
    if (not isinstance(contract, dict) or not isinstance(contract.get("kind"), str)
            or contract["kind"] not in KINDS):
        raise ReceiptError("unknown owned route")
    if contract.get("blocked_reason"):
        raise ReceiptError(str(contract["blocked_reason"]))
    if not isinstance(contract.get("id"), str) or not contract["id"]:
        raise ReceiptError("route must have a stable identity")
    kind = contract["kind"]
    source, source_get = _source(contract, fetch, now, observations)
    platform_get = None
    if kind in {"standard_site", "appview"}:
        endpoint = _pds_endpoint(contract.get("platform_id"), fetch, now, observations)
        if kind == "standard_site" and not _same_endpoint(contract.get("public_url"), endpoint):
            raise ReceiptError("PDS URL does not match the authoritative DID service")
        if kind == "appview":
            platform_body, platform_get = readback(endpoint, fetch, now)
            observations["pds_get"] = platform_get
            _record({**contract, "kind": "standard_site", "public_url": endpoint,
                     "record_path": []}, source, platform_body)
    live, live_get = readback(contract.get("public_url"), fetch, now)
    observations["live_get"] = live_get
    receipt = {
        "version": 1, "kind": kind, "route_id": contract["id"],
        "public_url": contract["public_url"],
        "platform_id": contract.get("platform_id"),
        "source_sha": contract["source"]["sha"],
        "source_sha256": contract["source"]["sha256"],
        "observed_at": live_get["observed_at"],
        "source_get": source_get, "live_get": live_get,
        "evidence_level": LEVELS[kind],
        "audience_delivery_confirmed": False,
        "indexed_confirmed": False,
    }
    if kind in {"standard_site", "appview"}:
        receipt["record"] = _record(contract, source, live)
        receipt["did_get"] = observations["did_get"]
        if platform_get is not None:
            receipt["pds_get"] = platform_get
    else:
        if live != source:
            raise ReceiptError("live content does not match the immutable source")
        if kind in {"rss", "atom", "json_feed"}:
            _feed(live, kind)
        if kind == "pages" and b"<html" not in live.lower():
            raise ReceiptError("Pages readback is not an HTML document")
    if kind in {"websub", "rsscloud", "indexnow"}:
        body, ack_get = readback(contract.get("ack_url"), fetch, now)
        observations["ack_get"] = ack_get
        document = parse_json(body)
        receipt["remote_ack"] = (
            _indexnow(contract, document, now) if kind == "indexnow"
            else _notification(contract, document, now)
        )
        receipt["ack_get"] = ack_get
    receipt["receipt_sha256"] = sha256(json_bytes(receipt))
    return receipt


def _valid_saved(receipt, route_id, kind):
    if not isinstance(receipt, dict):
        return False
    value = dict(receipt)
    digest = value.pop("receipt_sha256", None)
    return (
        type(value.get("version")) is int and value["version"] == 1
        and value.get("route_id") == route_id
        and value.get("kind") == kind and digest == sha256(json_bytes(value))
    )


def _expected(contract):
    source = contract.get("source")
    source = source if isinstance(source, dict) else {}
    result = {
        "source_sha": source.get("sha") if SHA.fullmatch(str(source.get("sha") or "")) else None,
        "source_sha256": source.get("sha256") if DIGEST.fullmatch(str(source.get("sha256") or "")) else None,
        "platform_id": contract.get("platform_id") if AT_URI.fullmatch(
            str(contract.get("platform_id") or "")) else None,
    }
    for key, value in (("public_url", contract.get("public_url")),
                       ("source_url", source.get("url")), ("ack_url", contract.get("ack_url"))):
        try:
            result[key] = public_url(value)
        except ReceiptError:
            result[key] = None
    return result


def audit(contracts, *, previous=None, fetch=get, now=None):
    now = now or now_utc()
    previous = {"version": 1, "routes": {}} if previous is None else previous
    if (not isinstance(previous, dict) or type(previous.get("version")) is not int
            or previous["version"] != 1
            or not isinstance(previous.get("routes"), dict)):
        raise ReceiptError("invalid previous receipt journal; refusing to overwrite")
    if not isinstance(contracts, list) or not contracts:
        raise ReceiptError("owned route inventory must not be empty")
    identities = [row.get("id") for row in contracts if isinstance(row, dict)]
    if (len(identities) != len(contracts) or any(not isinstance(key, str) or not key
                                              for key in identities)
            or len(set(identities)) != len(identities)):
        raise ReceiptError("owned route inventory has invalid or duplicate identities")
    if any(not isinstance(row.get("kind"), str) or row["kind"] not in KINDS
           for row in contracts):
        raise ReceiptError("owned route inventory contains an unknown kind")
    for key, old in previous["routes"].items():
        if (not isinstance(key, str) or not key or not isinstance(old, dict)
                or not isinstance(old.get("kind"), str)
                or old["kind"] not in KINDS):
            raise ReceiptError("invalid previous route journal")
        if (old.get("last_good") is not None
                and not _valid_saved(old["last_good"], key, old["kind"])):
            raise ReceiptError("invalid last-good receipt; refusing to overwrite")
    routes = {}
    for contract in contracts:
        key, kind = contract["id"], contract.get("kind")
        old = previous["routes"].get(key) or {}
        if old and old["kind"] != kind:
            raise ReceiptError("a durable route identity cannot change kind")
        last_good = old.get("last_good")
        row = {
            "kind": kind, "checked_at": now.isoformat(), "verdict": "FAIL",
            "receipt": None, "last_good": copy.deepcopy(last_good), "problems": [],
            "expected": _expected(contract), "attempt": {},
        }
        try:
            receipt = verify(contract, fetch=fetch, now=now, observations=row["attempt"])
            row.update(verdict="OK", receipt=receipt, last_good=copy.deepcopy(receipt))
        except (ValueError, OSError, RuntimeError, TypeError, KeyError) as error:
            row["problems"] = [f"{type(error).__name__}: {str(error)[:300]}"]
        routes[key] = row
    # Disappearing contracts are failures, not a way to make the dashboard green.
    for key, old in previous["routes"].items():
        if key not in routes:
            routes[key] = {
                **copy.deepcopy(old), "checked_at": now.isoformat(),
                "verdict": "FAIL", "receipt": None,
                "problems": ["route disappeared from the expected inventory"],
            }
    return {"version": 1, "checked_at": now.isoformat(),
            "healthy": all(row["verdict"] == "OK" for row in routes.values()),
            "routes": routes}


def atomic_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ReceiptError("refusing to replace a symlink receipt journal")
    payload = json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pending")
    try:
        descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        pending.unlink(missing_ok=True)


def notification_document(route, source_sha, feeds, responses):
    """Publisher-side capture of real HTTP acks; never called by the GET auditor."""
    if route not in {"websub", "rsscloud"} or not SHA.fullmatch(source_sha or ""):
        raise ReceiptError("notification export requires a route and full source SHA")
    if not feeds or not responses:
        raise ReceiptError("empty notification export is not a receipt")
    contents = {public_url(url): sha256(body) for url, body in feeds.items()}
    rows = []
    for response in responses:
        row = dict(response)
        row.update(
            route=route, source_sha=source_sha, public_urls=list(feeds),
            content_sha256=contents, semantics=LEVELS[route], method="POST",
        )
        rows.append(row)
    document = {"version": 1, "kind": "owned_notification_acknowledgements",
                "receipts": rows}
    endpoints = [row.get("endpoint") for row in rows]
    for url, digest in contents.items():
        _notification({"kind": route, "public_url": url, "endpoints": endpoints,
                       "source": {"sha": source_sha, "sha256": digest}},
                      document, now_utc())
    return document
