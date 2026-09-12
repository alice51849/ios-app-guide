#!/usr/bin/env python3
"""Buttondown GET-only adapters. A form or workflow is never native email evidence."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import ipaddress
import os
from pathlib import Path
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

import owned_email_contract as contract

API = "https://api.buttondown.com/v1"
MAX_BODY = 2 * 1024 * 1024
ID = re.compile(r"(?:[a-z]+_[a-z0-9]{26}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})")
ARCHIVE = re.compile(r"/hourstag/archive/[A-Za-z0-9][A-Za-z0-9_-]*/")
HARD_PRICE = re.compile(r"[$€£₹¥]\s*\d|\b(?:USD|EUR|GBP|JPY|TWD|INR|CAD|AUD)\s*\d", re.I)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _allowed_url(url, authenticated=False):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        raise contract.ContractError("invalid readback URL")
    try:
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment
        ):
            raise ValueError("unsafe URL")
    except ValueError as error:
        raise contract.ContractError("readback requires credential-free HTTPS") from error
    if authenticated:
        if parsed.netloc != "api.buttondown.com":
            raise contract.ContractError("credentials are restricted to exact Buttondown API GETs")
        parts = parsed.path.split("/")
        if len(parts) not in (3, 4) or parts[1] != "v1" or parts[2] not in {
            "subscribers", "emails", "events",
        } or (len(parts) == 4 and not ID.fullmatch(parts[3])):
            raise contract.ContractError("read-only API route is not allowlisted")
        if parsed.query and (
            parsed.path != "/v1/subscribers" or not re.fullmatch(r"page=[1-9][0-9]{0,3}", parsed.query)
        ):
            raise contract.ContractError("only bounded subscriber GET pagination is allowed")
    else:
        public = urllib.parse.urlsplit(contract.PUBLIC_SITE)
        allowed = (
            parsed.netloc == "buttondown.com" and not parsed.query
            and (ARCHIVE.fullmatch(parsed.path) or parsed.path == "/hourstag/archive/")
            or parsed.netloc == public.netloc and not parsed.query
            and parsed.path.startswith(public.path + "/")
            or parsed.netloc == "itunes.apple.com" and parsed.path == "/lookup"
        )
        if not allowed:
            raise contract.ContractError("public readback route is not allowlisted")
    return parsed


def http_get(url, *, api_key=None, timeout=20):
    parsed = _allowed_url(url, authenticated=api_key is not None)
    if api_key is not None and (
        not isinstance(api_key, str) or not api_key.strip()
        or any(c.isspace() for c in api_key)
    ):
        raise contract.ContractError("Buttondown authentication is unavailable")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise contract.ContractError("readback DNS must resolve to public addresses")
    headers = {"User-Agent": "LumiOwnedEmail-ReadOnly/1", "Cache-Control": "no-cache"}
    if api_key is not None:
        headers["Authorization"] = f"Token {api_key}"
    request = urllib.request.Request(url, method="GET", headers=headers)
    with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise contract.ContractError("readback body exceeds limit")
        return {
            "method": "GET", "url": url, "final_url": response.geturl(),
            "http_status": response.status, "body": body,
            "observed_at": contract.utcnow().isoformat(),
        }


class ButtondownReadOnly:
    def __init__(self, api_key):
        self._api_key = api_key

    def request(self, method, url):
        if method != "GET":
            raise contract.ContractError("no subscription, draft, email or provider mutations")
        return http_get(url, api_key=self._api_key)

    def get(self, url):
        return self.request("GET", url)


def checked_get(url, fetch, now, *, authenticated=False):
    _allowed_url(url, authenticated)
    response = fetch(url)
    if (
        not isinstance(response, dict) or response.get("method") != "GET"
        or response.get("url") != url or response.get("final_url") != url
        or type(response.get("http_status")) is not int or response["http_status"] != 200
        or not isinstance(response.get("body"), bytes)
        or not 0 < len(response["body"]) <= MAX_BODY
    ):
        raise contract.ContractError("exact fresh GET body and HTTP 200 are required")
    contract.fresh(response.get("observed_at"), now() if callable(now) else now, 300)
    observation = {
        key: response[key] for key in ("method", "url", "final_url", "http_status", "observed_at")
    }
    observation["body_sha256"] = contract.digest(response["body"])
    return response["body"], observation


class Body(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.text = []
        self.links = []
        self.canonicals = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = (
            any(value for _, value in self.stack)
            or tag in {"script", "style", "template"}
            or "hidden" in attrs or attrs.get("aria-hidden") == "true"
            or bool(re.search(r"display\s*:\s*none|visibility\s*:\s*hidden", attrs.get("style") or "", re.I))
        )
        if not hidden and tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(value for _, value in self.stack):
            self.text.append(data)

    def visible(self):
        return " ".join(" ".join(self.text).split())


def binding_text(row):
    return f"owned-email/v1/{row['app_id']}/{row['locale']}/{row['campaign']}/{row['consent_digest']}"


def capture_readback(row, *, public_get=http_get, now=None):
    clock = contract.utcnow if now is None else lambda: now
    contract.validate_row(row)
    body, observation = checked_get(row["capture_url"], public_get, clock)
    if contract.digest(body) != row.get("content_sha256"):
        raise contract.ContractError("published capture does not match source content")
    return {
        "level": "content_ready_not_subscriber_or_delivery", **contract.scope(row),
        "content_get": observation, "verified_subscribers": 0,
        "subscriber_count": "UNKNOWN", "native_email_count": 0,
    }


def native_readback(row, reference, *, api_get, public_get=http_get, now=None):
    """Always re-GET both provider ID and archive; never trust a stored success flag."""
    clock = contract.utcnow if now is None else lambda: now
    now = now or contract.utcnow()
    contract.validate_row(row)
    if not isinstance(reference, dict) or set(reference) != {"email_id", "url", "body_sha256"}:
        raise contract.ContractError("native reference requires exact email ID, archive URL and body digest")
    email_id, url = reference["email_id"], reference["url"]
    if (
        not isinstance(email_id, str) or not ID.fullmatch(email_id)
        or not isinstance(reference["body_sha256"], str)
        or not contract.HEX.fullmatch(reference["body_sha256"])
    ):
        raise contract.ContractError("invalid native email identity")
    parsed = _allowed_url(url)
    if parsed.netloc != "buttondown.com" or not ARCHIVE.fullmatch(parsed.path):
        raise contract.ContractError("native evidence must be an individual Buttondown public archive")
    api_body, api_observation = checked_get(f"{API}/emails/{email_id}", api_get, clock, authenticated=True)
    email = contract.parse_json(api_body)
    if (
        not isinstance(email, dict) or email.get("id") != email_id
        or email.get("absolute_url") != url or email.get("status") != "sent"
        or email.get("archival_mode") != "enabled" or email.get("suppression_reason") is not None
        or email.get("metadata") != contract.capture_metadata(row)
        or not isinstance(email.get("body"), str) or not email["body"].strip()
        or contract.digest(email["body"].encode()) != reference["body_sha256"]
    ):
        raise contract.ContractError("native email GET does not bind sent content to this exact scope")
    published = contract.timestamp(email.get("publish_date"))
    if published > now:
        raise contract.ContractError("scheduled/future email is not published evidence")
    email_dom = Body(email["body"])
    marker = binding_text(row)
    if (
        marker not in email_dom.visible() or row["capture_url"] not in email_dom.links
        or HARD_PRICE.search(email_dom.visible())
        or (row["app_store_url"] and row["app_store_url"] not in email_dom.links)
        or any(("apps.apple.com" in link or "itunes.apple.com" in link)
               and link != row["app_store_url"] for link in email_dom.links)
    ):
        raise contract.ContractError("email body is not App/locale/campaign-bound")
    public_body, public_observation = checked_get(url, public_get, clock)
    archive = Body(public_body.decode("utf-8", errors="strict"))
    if (
        archive.canonicals != [url] or marker not in archive.visible()
        or row["capture_url"] not in archive.links
        or email_dom.visible() not in archive.visible()
        or (row["app_store_url"] and row["app_store_url"] not in archive.links)
        or any(("apps.apple.com" in link or "itunes.apple.com" in link)
               and link != row["app_store_url"] for link in archive.links)
    ):
        raise contract.ContractError("HTTP 200 archive body does not match the native email")
    return {
        "level": "buttondown_public_archive_verified_not_recipient_delivery",
        **contract.scope(row), "email_id": email_id, "url": url,
        "published_at": published.isoformat(), "body_sha256": reference["body_sha256"],
        "provider_get": api_observation, "public_get": public_observation,
        "native_email_count": 1, "delivered_subscribers": "UNKNOWN",
    }


def subscriber_census(*, api_get, now=None):
    """A complete provider GET census is not proof of consent, even for regular subscribers."""
    clock = contract.utcnow if now is None else lambda: now
    seen, observations, regular = set(), [], 0
    total = None
    for page in range(1, 101):
        url = f"{API}/subscribers" + (f"?page={page}" if page > 1 else "")
        body, observation = checked_get(url, api_get, clock, authenticated=True)
        payload = contract.parse_json(body)
        if (
            not isinstance(payload, dict) or type(payload.get("count")) is not int
            or not 0 <= payload["count"] <= 10000
            or not isinstance(payload.get("results"), list)
            or (total is not None and payload["count"] != total)
        ):
            raise contract.ContractError("incomplete or inconsistent subscriber census")
        total = payload["count"]
        observations.append(observation)
        for row in payload["results"]:
            if (
                not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not ID.fullmatch(row["id"]) or row["id"] in seen
            ):
                raise contract.ContractError("duplicate or invalid provider subscriber ID")
            seen.add(row["id"])
            regular += row.get("type") == "regular"
        if len(seen) > total or not payload["results"] and len(seen) != total:
            raise contract.ContractError("subscriber pagination count mismatch")
        if len(seen) == total:
            return {
                "subscriber_count": total, "provider_regular_count": regular,
                "verified_double_opt_in_count": 0, "native_email_count": 0,
                "level": "provider_census_not_verified_consent_or_delivery",
                "observations": observations,
            }
    raise contract.ContractError("subscriber census exceeded bounded pagination")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subscriber-count", action="store_true")
    parser.add_argument("--pages-dir", type=Path)
    parser.add_argument("--app")
    parser.add_argument("--locale")
    parser.add_argument("--native-reference", type=Path)
    args = parser.parse_args(argv)
    api_key = os.environ.get("BUTTONDOWN_API_KEY") or os.environ.get("BUTTONDOWN_API_TOKEN")
    client = ButtondownReadOnly(api_key) if api_key else None
    if args.subscriber_count:
        result = subscriber_census(api_get=client.get) if client else {
            "subscriber_count": "UNKNOWN", "verified_double_opt_in_count": 0,
            "native_email_count": 0, "reason": "no_authenticated_provider_census",
        }
    else:
        if not all((args.pages_dir, args.app, args.locale)):
            parser.error("capture readback requires --pages-dir, --app and --locale")
        inventory = contract.parse_json((args.pages_dir / contract.INVENTORY).read_bytes())
        availability = contract.parse_json((args.pages_dir / contract.AVAILABILITY).read_bytes())
        contract.validate_inventory(inventory, availability)
        row = contract.inventory_row(inventory, args.app, args.locale)
        if args.native_reference:
            if client is None:
                raise contract.ContractError("native email ID verification requires authenticated GET")
            result = native_readback(
                row, contract.parse_json(args.native_reference.read_bytes()), api_get=client.get,
            )
        else:
            result = capture_readback(row)
    print(contract.json_bytes(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
